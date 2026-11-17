"""One explicitly selected S04 action in a disposable candidate-image process."""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

batch = Path(__file__).resolve().parent
cfg = json.loads((batch / "ingress.json").read_text())
action = sys.argv[1]
assert action == "send_context", "this recovery invocation is only for context before any send intent"
commands = {
    "validate": ["/work/tools/testdata/streaming_send.py", "validate", "--prepared", "/batch/prepared"],
    "preflight": ["/batch/readback.py", "/batch", "preflight"],
    "send_context": ["/work/tools/testdata/streaming_send.py", "send", "--prepared", "/batch/prepared", "--phase", "S04-context", "--preflight-readback", "/batch/readback/preflight-readback.json"],
    "context": ["/batch/readback.py", "/batch", "context"],
    "send_alerts": ["/work/tools/testdata/streaming_send.py", "send", "--prepared", "/batch/prepared", "--phase", "S04-alerts",
                    "--context-readback", "/batch/readback/context-readback.json"],
    "alerts": ["/batch/readback.py", "/batch", "alerts"],
}
command = commands[action]
for name, required in ((cfg["dispatch_container"], "exited"), (cfg["fusion_container"], "running")):
    observed = subprocess.run(["docker", "inspect", "--format", "{{.State.Status}}", name], capture_output=True, text=True, check=True).stdout.strip()
    assert observed == required, "runtime_state_changed_before_action"
receipt = batch / ("invocation-" + action + "-02.json")
if receipt.exists():
    raise SystemExit("action already has an invocation receipt")
private = Path(cfg["root"]) / "private"
args = ["docker", "run", "--rm", "--network", cfg["network"], "--workdir", "/work",
        "--user", str(os.getuid()) + ":" + str(os.getgid()),
        "--volume", str(batch / "sources") + ":/work:ro", "--volume", str(batch) + ":/batch"]
if action in ("send_context", "send_alerts"):
    args += ["--volume", str(private / "producer.env") + ":/run/private/producer.env:ro",
             "--volume", cfg["kafka"]["ca_source"] + ":" + cfg["kafka"]["ca_target"] + ":ro"]
elif action in ("preflight", "context", "alerts"):
    for kind in ("postgres", "clickhouse"):
        path = cfg[kind]["private_runtime"]
        args += ["--volume", path + ":" + path + ":ro"]
args += ["--entrypoint", "python", cfg["processing_image"], *command]
record = {"action": action, "status": "started", "started_at": datetime.now(timezone.utc).isoformat(), "command_sha256": hashlib.sha256(json.dumps(args).encode()).hexdigest()}
with receipt.open("x") as stream:
    json.dump(record, stream, indent=2)
try:
    process = subprocess.run(args, capture_output=True, text=True, timeout=cfg["timeout_seconds"] * 2, check=False)
    record.update(status="passed" if process.returncode == 0 else "failed", returncode=process.returncode)
    try:
        record["result"] = json.loads(process.stdout)
    except ValueError:
        record["stdout_sha256"] = hashlib.sha256(process.stdout.encode()).hexdigest()
    if process.stderr:
        error_path = private / ("s04-" + action + "-02-stderr.log")
        with error_path.open("x") as error_stream:
            error_stream.write(process.stderr)
        error_path.chmod(0o600)
        record["stderr_private_path"] = str(error_path)
        record["stderr_sha256"] = hashlib.sha256(process.stderr.encode()).hexdigest()
except Exception as exc:  # noqa: BLE001 -- never retry an uncertain send or print credentials
    record.update(status="unknown", error_type=type(exc).__name__)
record["ended_at"] = datetime.now(timezone.utc).isoformat()
receipt.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({key: value for key, value in record.items() if key != "command"}))
raise SystemExit(0 if record["status"] == "passed" else 1)
