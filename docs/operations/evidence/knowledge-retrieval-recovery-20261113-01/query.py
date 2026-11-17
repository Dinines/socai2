"""One read-only query through the configured C2 adapter; no Run redispatch."""
import asyncio
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "services/api")]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (HERE / name).open("x") as file:
        json.dump(value, file, ensure_ascii=False, indent=2, default=str)
        file.write("\n")


async def query(config):
    from app.socai2.baseline_optional_sources import SourceUnavailable
    from app.socai2.case_service import CaseService
    from app.socai2.knowledge_config import load
    from app.socai2.knowledge_source import query as retrieve
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tools.testdata.incident_integration.run import connect

    snapshot = read(ROOT / config["snapshot"])
    original = next(a for a in snapshot["artifacts"] if a["run_id"] == config["run_id"]
                    and a["kind"] == "tool_request" and a["content_json"].get("tool_name") == "knowledge")
    args = original["content_json"]
    profile, fingerprint = load()
    assert all(k["profile_sha256"] == fingerprint for k in args["parameters"]["selectors"])
    files = [HERE / "query.py", HERE / "config.json", ROOT / config["snapshot"],
             ROOT / config["knowledge_profile"], ROOT / config["local_services"],
             ROOT / "tools/testdata/incident_integration/run.py"]
    files.extend((ROOT / "services/api/app/socai2").glob("knowledge*.py"))
    original_files = {str(p.relative_to(ROOT)): sha(p) for p in
                      (ROOT / "docs/operations/evidence/fixed-investigation-20261113-06/flow").rglob("*")
                      if p.is_file()}
    save("query-intent.json", {"at": datetime.now(UTC), "kind": "read_only_new_query_no_run",
        "original_request_id": original["id"], "original_run_id": config["run_id"],
        "args": args, "profile_sha256": fingerprint, "model": profile.embedding.model,
        "dimension": profile.embedding.dimension, "collection": profile.vector.collection,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in files},
        "original_flow_sha256": original_files, "generation_calls": 0, "database_writes": 0})
    engine = await connect(config)
    try:
        service = CaseService(async_sessionmaker(engine, expire_on_commit=False))
        try:
            rows, captured, metadata = await retrieve(service, UUID(config["tenant_id"]), args)
            result = {"state": "completed", "rows": rows, "captured_at": captured, "metadata": metadata}
        except SourceUnavailable as exc:
            result = {"state": "failed", "code": str(exc), "metadata": getattr(exc, "metadata", None)}
        result.update(generation_calls=0, database_writes=0, new_runs=0)
        save("query-result.json", result)
        assert all(sha(ROOT / p) == value for p, value in original_files.items())
        save("preservation.json", {"original_flow_files_unchanged": len(original_files),
                                  "generation_calls": 0, "database_writes": 0})
        print(json.dumps({"state": result["state"], "rows": len(result.get("rows", [])),
                          "code": result.get("code"), "calls": result.get("metadata", {}).get("calls")}), flush=True)
    finally:
        await engine.dispose()


def main():
    import httpx

    config = read(HERE / "config.json")
    assert not (HERE / "query-intent.json").exists(), "recorded_query_not_redispatched"
    os.environ.update(read(ROOT / config["environment_file"]))
    os.environ.update(config["runtime_overrides"])
    os.environ["SOCAI2_KNOWLEDGE_PROFILE"] = str(ROOT / config["knowledge_profile"])
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])
    services = read(ROOT / config["local_services"])
    profile = read(ROOT / config["knowledge_profile"])
    port = services["embedding_host_port"]
    assert profile["embedding"]["url"] == f"http://127.0.0.1:{port}/api/embed"
    with socket.socket() as sock:
        assert sock.connect_ex(("127.0.0.1", port)) != 0, "existing_listener_not_owned_by_this_probe"
    argv = ["ssh", "-N", "-o", "BatchMode=yes", "-o", "ExitOnForwardFailure=yes",
            "-o", f"ConnectTimeout={config['ssh_connect_timeout_seconds']}",
            "-L", f"127.0.0.1:{port}:{services['embedding_target']}", services["ssh_host"]]
    save("transport-intent.json", {"at": datetime.now(UTC), "argv": argv,
        "listener_before": "absent", "scope": "temporary_owned_forward_only", "remote_service_restart": False})
    proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    receipt = {"pid": proc.pid, "state": "starting", "generation_calls": 0}
    try:
        deadline = time.monotonic() + config["tunnel_ready_timeout_seconds"]
        while time.monotonic() < deadline:
            assert proc.poll() is None, "ssh_exited_before_query"
            with socket.socket() as sock:
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.1)
        else:
            raise RuntimeError("tunnel_not_ready")
        url = profile["embedding"]["url"].rsplit("/", 1)[0] + "/version"
        response = httpx.get(url, timeout=config["version_timeout_seconds"])
        response.raise_for_status()
        receipt.update(state="forward_ready", version=response.json(), version_http_status=response.status_code)
        asyncio.run(query(config))
    finally:
        proc.terminate()
        try:
            _, stderr = proc.communicate(timeout=config["ssh_connect_timeout_seconds"])
        except subprocess.TimeoutExpired:
            proc.kill()
            _, stderr = proc.communicate()
        receipt.update(owned_forward_closed=True, returncode=proc.returncode,
                       stderr=stderr, finished_at=datetime.now(UTC))
        save("transport-result.json", receipt)


if __name__ == "__main__":
    main()
