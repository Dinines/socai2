"""This batch's local proxy -> SSH forward -> real candidate GET checks."""
import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import httpx


def save(path, value):
    with path.open("x") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def tree(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()} if root.exists() else {}


def main(profile):
    c = json.loads(profile.read_text())
    out = Path(c["evidence_directory"])
    ledger = Path(c["ledger_root"])
    assert not ledger.exists(), "use a new absent ledger for this read-only batch"
    before = tree(ledger)
    ssh = service = None
    results = {"status": "running", "source": "real_candidate_tcp_via_local_proxy", "requests": [],
               "business_writes": 0, "model_calls": 0, "kafka_sends": 0,
               "nonempty_business_reads_verified": False, "viewer_verified": False}
    with (out / "ssh.log").open("x") as ssh_log, (out / "server.log").open("x") as service_log:
        try:
            ssh = subprocess.Popen([c["ssh_binary"], "-N", "-T", "-o", "BatchMode=yes", "-o",
                "ControlMaster=no", "-o", "ControlPath=none", "-o", "ExitOnForwardFailure=yes", "-o",
                f"ConnectTimeout={c['connect_timeout_seconds']}", "-L", c["forward_spec"], c["ssh_target"]],
                stdout=ssh_log, stderr=ssh_log)
            env = {**os.environ, "PYTHONPATH": str(Path(c["repository"]) / "services")}
            service = subprocess.Popen([c["python"], "-m", "investigation_test", "serve", "--config",
                c["service_config"], "--upstream-config", c["upstream_config"]], cwd=c["repository"],
                env=env, stdout=service_log, stderr=service_log)
            with httpx.Client(timeout=c["request_timeout_seconds"], trust_env=False) as client:
                deadline = time.monotonic() + c["startup_timeout_seconds"]
                while True:
                    assert ssh.poll() is None and service.poll() is None, "test process exited"
                    try:
                        cap = client.get(c["proxy_url"] + "/test-api/v1/capabilities")
                        upstream = client.get(c["forward_url"] + "/openapi.json")
                        if cap.status_code == upstream.status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    if time.monotonic() >= deadline:
                        raise TimeoutError("temporary proxy/forward did not become ready")
                    time.sleep(c["startup_poll_seconds"])
                assert cap.json()["investigation_http"]["get_operations"] == 55
                assert hashlib.sha256(upstream.content).hexdigest() == cap.json()["investigation_http"]["contract_sha256"]
                save(out / "capabilities.json", cap.json())
                for index, item in enumerate(c["requests"], 1):
                    reply = client.get(c["proxy_url"] + item["path"])
                    body = reply.json()
                    (out / f"response-{index:02d}.json").write_bytes(reply.content)
                    assert reply.status_code == item["status"], (item["path"], reply.status_code)
                    assert reply.headers["x-investigation-environment"] == c["environment_label"]
                    if item["empty_list"]:
                        assert body["items"] == [] and body.get("total", 0) == 0
                    results["requests"].append({"method": "GET", "path": item["path"], "status": reply.status_code,
                        "response": f"response-{index:02d}.json", "sha256": hashlib.sha256(reply.content).hexdigest()})
                # A real unknown object and invalid limit must preserve upstream bytes/status.
                for path in c["compare_paths"]:
                    direct = client.get(c["forward_url"] + path)
                    proxy = client.get(c["proxy_url"] + path)
                    assert proxy.status_code == direct.status_code and proxy.content == direct.content
                    results.setdefault("direct_error_comparisons", []).append({"path": path,
                        "status": proxy.status_code, "same_body_sha256": hashlib.sha256(proxy.content).hexdigest()})
                assert tree(ledger) == before and not ledger.exists()
                results.update(status="passed", ledger_unchanged=True, ledger_created=False)
        except BaseException as exc:
            results.update(status="failed", error_type=type(exc).__name__, error=str(exc))
            raise
        finally:
            for process in (service, ssh):
                if process is not None:
                    process.terminate()
                    try:
                        process.wait(timeout=c["stop_timeout_seconds"])
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=c["stop_timeout_seconds"])
            results["temporary_processes_stopped"] = all(p is None or p.poll() is not None for p in (service, ssh))
            save(out / "result.json", results)
    print(json.dumps({"status": results["status"], "requests": len(results["requests"]),
                      "temporary_processes_stopped": results["temporary_processes_stopped"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, required=True)
    main(parser.parse_args().profile)
