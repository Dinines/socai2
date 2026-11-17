"""Start only this batch's explicitly configured normal HTTP/Fusion/dispatcher."""
import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[4]


async def main(path, attempt):
    config = json.loads(path.read_text())
    private, out = path.parent, Path(__file__).parent
    pid_file = private / ("processes-" + attempt + ".json")
    assert not pid_file.exists(), "batch_process_manifest_already_exists"
    forward = config["model_forward"]
    command = ["ssh", "-M", "-S", forward["control_socket"], "-fnNT", "-o", "ExitOnForwardFailure=yes",
               "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=15",
               "-o", "ServerAliveCountMax=3"]
    for item in forward["forwards"]:
        command += ["-L", item]
    existing = subprocess.run(["ssh", "-S", forward["control_socket"], "-O", "check", forward["ssh_alias"]],
                              capture_output=True, text=True, timeout=15)
    result = existing if existing.returncode == 0 else subprocess.run(command + [forward["ssh_alias"]], capture_output=True, text=True, timeout=45)
    if result.returncode:
        (private / "forward-error.log").write_text(result.stderr)
        raise RuntimeError("dedicated_model_forward_failed_see_private_log")
    started, processes = {}, {}
    commands = {
        "api": ["-m", "uvicorn", "investigation_http.main:app", "--host", config["bind"], "--port", str(config["http_port"])],
        "fusion": ["-m", "uvicorn", "fusion_app:app", "--host", config["bind"], "--port", str(config["fusion_port"])],
        "dispatcher": ["-m", "app.socai2.analysis_dispatch_runtime", "--profile", str(private / "dispatcher.json")],
    }
    for name, argv in commands.items():
        environment = json.loads((private / ("fusion-environment.json" if name == "fusion" else "api-environment.json")).read_text())
        environment["APPEND_VALIDATION_CONFIG"] = str(path)
        with (private / (name + "-" + attempt + ".log")).open("xb") as log:
            process = subprocess.Popen([sys.executable, *argv], env={**os.environ, **environment},
                                       cwd=private, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        processes[name] = process
        started[name] = {"pid": process.pid, "argv": [sys.executable, *argv]}
        pid_file.write_text(json.dumps(started, indent=2) + "\n")
    checks = {"api": f"http://{config['bind']}:{config['http_port']}/readyz",
              "fusion": f"http://{config['bind']}:{config['fusion_port']}/readyz",
              "model": f"http://{config['bind']}:{config['model_gateway_port']}/v1/models"}
    ready = {}
    model = json.loads((private / "model-environment.json").read_text())
    headers = {"Authorization": "Bearer " + model["OPENAI_API_KEY"]} if model.get("OPENAI_API_KEY") else {}
    async with httpx.AsyncClient(timeout=config["http_timeout_seconds"], trust_env=False) as client:
        async with asyncio.timeout(config["startup_timeout_seconds"]):
            while len(ready) < len(checks):
                for name, process in processes.items():
                    assert process.poll() is None, "local_process_exited:" + name
                for name, url in checks.items():
                    if name in ready:
                        continue
                    try:
                        response = await client.get(url, headers=headers if name == "model" else {})
                        if response.status_code == 200:
                            ready[name] = {"status_code": 200, "response": response.json()}
                    except httpx.HTTPError:
                        pass
                if len(ready) < len(checks):
                    await asyncio.sleep(config["poll_interval_seconds"])
    (out / "local-readiness.json").write_text(json.dumps({"status": "passed", "checks": ready,
        "business_messages_sent": 0, "model_generation_calls": 0}, ensure_ascii=False, indent=2) + "\n")
    print("Local HTTP, Fusion and model route ready; dispatcher configured for one running task")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    asyncio.run(main(args.config.resolve(), args.attempt))
