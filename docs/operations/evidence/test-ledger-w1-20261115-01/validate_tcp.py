"""W1 only: publish saved evidence and synthetic states, then read over local TCP."""
import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
API = "/test-api/v1"


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(path):
    return {str(p.relative_to(path)): sha(p) for p in path.rglob("*") if p.is_file()}


def build_documents(out):
    captured = datetime.now(timezone.utc).isoformat()
    f5 = ROOT / "docs/operations/evidence/execution-contract-fix-20261115-01/test-pg-01/result.json"
    admission = ROOT / "docs/operations/evidence/case-update-http-20261115-01/admission-pg-01.json"
    result, received = json.loads(f5.read_text()), json.loads(admission.read_text())
    assert result["state"] == "passed" and result["real_model_calls"] == 0
    accepted = received["checks"][0]["detail"]["calls"][0]["body"]["allocations"][0]["initial_task"]
    assert accepted["status"] == "accepted" and not accepted.get("run_id")
    originals = {str(p.relative_to(ROOT)): sha(p) for p in (f5, admission)}
    documents = []

    def document(name, title, provenance, source=None):
        directory = out / "inputs" / name
        directory.mkdir(parents=True)
        if source:
            shutil.copyfile(source, directory / "source.json")
        else:
            save(directory / "source.json", {"synthetic_fixture": True,
                "purpose": "W1 failed/unknown/quality display; not a real model defect"})
        data = {"schema_version": 1, "batch": {"id": name, "title": title,
            "environment": "local-archive" if source else "synthetic", "scenario_version": "w1.readback.v1",
            "execution_state": "finished", "mode": "archive", "provenance": provenance,
            "started_at": captured, "updated_at": captured, "quality_status": "not_assessed"},
            "cases": [], "operations": [], "quality_issues": [],
            "preparation": {"status": "prepared", "cleanup_mode": "no_cleanup",
                "summary": "Archived saved records only; no business connection or model request.",
                "observed_at": captured, "resources": ["new local W1 ledger"], "evidence_ids": ["source"]},
            "evidence": [{"id": "source", "path": "source.json", "label": title,
                "mime_type": "application/json", "visibility": "public",
                "source_ref": str(source.relative_to(ROOT)) if source else "synthetic_fixture"}]}
        return directory, data

    def case(data, identity, mapping, operation_state, actual, status="passed"):
        data["cases"].append({"id": identity, "use_case_id": "TC-V01", "scenario_id": "W1",
            "status": status, "expected": ["Preserve the supplied archive identity and state."],
            "actual": [actual], "operation_ids": [identity], "evidence_ids": ["source"]})
        data["operations"].append({"id": identity, "case_id": identity, "intent": "archive_readback",
            "execution_state": operation_state, "occurred_at": None,
            "mappings": [mapping], "evidence_ids": ["source"]})

    directory, data = document("w1-f5-archive", "Saved F5: 5 simulated model replies, zero real models", "saved_evidence", f5)
    for task in result["tasks"]:
        output = task["results"][0]
        case(data, task["subject_type"], {"subject_type": task["subject_type"], "subject_id": task["subject_id"],
            "task_id": task["task_id"], "run_id": task["latest_run_id"], "result_type": output["result_type"],
            "result_id": output["id"]}, task["status"], "Maps the original completed task/Run/result; no replay.")
    save(directory / "document.json", data)
    documents.append(directory / "document.json")
    directory, data = document("w1-admission-archive", "Historical admission: accepted with no Run at capture", "saved_evidence", admission)
    case(data, "waiting", {"subject_type": "case", "subject_id": accepted["subject_id"],
        "task_id": accepted["task_id"], "run_id": None}, "accepted", "Historical admission only, not its current live state.")
    save(directory / "document.json", data)
    documents.append(directory / "document.json")
    directory, data = document("w1-quality-fixture", "Synthetic failure/quality display only", "synthetic_fixture")
    run_id = str(uuid4())
    case(data, "failed", {"subject_type": "case", "subject_id": str(uuid4()), "task_id": str(uuid4()),
        "run_id": run_id}, "unknown", "Synthetic unknown outcome retained, not a business failure.", status="failed")
    data["batch"]["quality_status"] = "issues_recorded"
    data["quality_issues"] = [{"id": "synthetic-quality", "case_id": "failed", "run_id": run_id,
        "stage": "C6", "category": "synthetic_display", "description": "Display fixture, not a real model quality finding.",
        "status": "deferred", "affects_flow": False, "evidence_ids": ["source"]}]
    save(directory / "document.json", data)
    documents.append(directory / "document.json")
    return documents, originals


def run(args):
    config = json.loads(args.config.read_text())
    out = HERE / args.batch
    out.mkdir(exist_ok=False)
    runtime = Path(config["runtime_root"]) / args.batch
    runtime.mkdir(exist_ok=False, parents=True)
    service = json.loads(Path(config["service_profile_template"]).read_text())
    assert service["host"] == "127.0.0.1"
    with socket.socket() as probe:
        probe.bind((service["host"], 0))
        service["port"] = probe.getsockname()[1]
    service["ledger_root"] = str(runtime / "ledger")
    service["default_limit"] = 1
    profile = runtime / "service.json"
    save(profile, service)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "services"), "PYTHONDONTWRITEBYTECODE": "1"}
    command = [sys.executable, "-m", "investigation_test"]
    paths = sorted((ROOT / "services/investigation_test").glob("*.py")) + [Path(config["service_profile_template"]), Path(__file__)]
    before = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    record = {"state": "running", "transport": "real_loopback_TCP", "target": {"host": service["host"], "port": service["port"]},
        "business_connections": 0, "model_calls": 0, "Kafka_messages": 0, "calls": [], "publications": [],
        "source_sha256_before": before, "profile_sha256": sha(profile), "checks": []}
    process = None
    server_log = (out / "server.log").open("x")

    def stop():
        nonlocal process
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=config["stop_timeout_seconds"])
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                raise AssertionError("read service did not stop normally") from None
            process = None

    def get(client, path, status=200, **params):
        response = client.get(path, params=params)
        entry = {"method": "GET", "path": path, "params": params, "status": response.status_code,
            "body_size": len(response.content), "body_sha256": hashlib.sha256(response.content).hexdigest()}
        if params.get("format") != "content":
            entry["body"] = response.json()
        record["calls"].append(entry)
        assert response.status_code == status, entry
        return response

    def start(client):
        nonlocal process
        process = subprocess.Popen([*command, "serve", "--config", str(profile)], cwd=ROOT, env=env,
            stdout=server_log, stderr=subprocess.STDOUT)
        until = time.monotonic() + config["start_timeout_seconds"]
        while time.monotonic() < until:
            assert process.poll() is None, "read service exited before readiness"
            try:
                if client.get(API + "/capabilities").status_code == 200:
                    return
            except httpx.TransportError:
                pass
            time.sleep(config["poll_interval_seconds"])
        raise AssertionError("read service startup timeout")

    try:
        documents, originals = build_documents(out)
        record["original_source_sha256_before"] = originals
        with httpx.Client(base_url=f"http://{service['host']}:{service['port']}",
                timeout=config["http_timeout_seconds"], trust_env=False) as client:
            start(client)
            assert get(client, API + "/batches").json()["total"] == 0
            assert not Path(service["ledger_root"]).exists()
            record["checks"].append("empty_start_and_GET_create_no_ledger")
            stop()
            for document in documents:
                run_command = [*command, "publish", "--config", str(profile), "--document", str(document), "--expected-revision", "0"]
                done = subprocess.run(run_command, cwd=ROOT, env=env, capture_output=True, text=True, check=False)
                record["publications"].append({"command": run_command, "exit_code": done.returncode,
                    "stdout": done.stdout, "stderr": done.stderr})
                assert done.returncode == 0
            before_reads = tree(Path(service["ledger_root"]))
            start(client)
            get(client, API + "/capabilities")
            batch_ids, cursor = [], None
            while True:
                page = get(client, API + "/batches", **({"cursor": cursor} if cursor else {})).json()
                batch_ids.extend(item["batch"]["id"] for item in page["items"])
                cursor = page["next_cursor"]
                if cursor is None:
                    break
            assert set(batch_ids) == {"w1-f5-archive", "w1-admission-archive", "w1-quality-fixture"}
            for batch_id in batch_ids:
                base = API + "/batches/" + batch_id
                detail = get(client, base).json()
                assert detail["batch"]["mode"] == "archive"
                for name in ("cases", "operations", "quality-issues"):
                    items, cursor = [], None
                    while True:
                        page = get(client, base + "/" + name, **({"cursor": cursor} if cursor else {})).json()
                        items.extend(page["items"])
                        cursor = page["next_cursor"]
                        if cursor is None:
                            break
                    assert len(items) == detail["counts"][name.replace("-", "_")]
                    if batch_id == "w1-admission-archive" and name == "operations":
                        assert items[0]["execution_state"] == "accepted" and items[0]["mappings"][0]["run_id"] is None
                    if batch_id == "w1-quality-fixture" and name == "quality-issues":
                        assert len(items) == 1 and items[0]["status"] == "deferred"
                get(client, base + "/preparation")
                for evidence in detail["evidence"]:
                    metadata = get(client, evidence["metadata_url"]).json()
                    content = get(client, evidence["metadata_url"], format="content")
                    assert len(content.content) == metadata["size"] and hashlib.sha256(content.content).hexdigest() == metadata["sha256"]
            get(client, API + "/batches/missing", status=404)
            get(client, API + "/batches", status=422, cursor="invalid")
            schema = get(client, "/openapi.json").json()
            assert len([p for p in schema["paths"] if p.startswith(API)]) == 8
            save(out / "openapi.json", schema)
            record["checks"].append("eight_GETs_pages_saved_Run_no_Run_quality_and_original_evidence")
            stop()
            assert tree(Path(service["ledger_root"])) == before_reads
            start(client)
            assert get(client, API + "/batches/w1-f5-archive").json()["counts"]["operations"] == 3
            stop()
            assert tree(Path(service["ledger_root"])) == before_reads
            assert {p: sha(ROOT / p) for p in originals} == originals
            record.update(ledger_sha256_before_reads=before_reads,
                ledger_sha256_after_restart=tree(Path(service["ledger_root"])), original_sources_unchanged=True)
            record["checks"].append("GET_and_restart_preserve_ledger_sources_and_no_business_execution")
            record["state"] = "passed"
    except Exception:
        record.update(state="failed", traceback=traceback.format_exc())
        raise
    finally:
        try:
            stop()
        except (OSError, AssertionError, subprocess.SubprocessError):
            record.update(state="failed", cleanup_error=traceback.format_exc())
        server_log.close()
        after = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        record.update(source_sha256_after=after, source_changed_during_run=before != after,
            profile_unchanged=record["profile_sha256"] == sha(profile), http_gets=len(record["calls"]))
        if before != after or not record["profile_unchanged"]:
            record["state"] = "failed"
        save(out / "result.json", record)
    assert record["state"] == "passed"
    print(json.dumps({k: record[k] for k in ["state", "checks", "http_gets", "model_calls", "business_connections"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--batch", required=True)
    run(parser.parse_args())
