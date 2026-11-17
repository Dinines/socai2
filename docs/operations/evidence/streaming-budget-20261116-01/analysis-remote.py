"""Run the single authorized read-only S04 capture in the existing image."""
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

folder = Path(__file__).resolve().parent
config = json.loads((folder / "capture-runtime.json").read_text())
private = config["private_http_source"]
state = subprocess.run(["docker", "inspect", "--format", "{{.State.Status}}", config["dispatcher_container"]], capture_output=True, text=True, check=True).stdout.strip()
assert state == "exited", "final_snapshot_requires_stopped_dispatcher"
args = ["docker", "run", "--rm", "--network", config["network"],
        "--user", str(os.getuid()) + ":" + str(os.getgid()),
        "--volume", str(folder) + ":/batch", "--volume", private + ":" + private + ":ro",
        "--entrypoint", "python", config["image"], "/batch/analysis-capture.py", "/batch"]
receipt = folder / "analysis-capture-invocation-01.json"
record = {"status": "started", "started_at": datetime.now(timezone.utc).isoformat(), "command_sha256": hashlib.sha256(json.dumps(args).encode()).hexdigest(), "image": config["image"]}
with receipt.open("x") as stream:
    json.dump(record, stream, indent=2)
try:
    process = subprocess.run(args, capture_output=True, text=True, timeout=config["command_timeout_seconds"], check=False)
    record.update(status="passed" if process.returncode == 0 else "failed", returncode=process.returncode)
    if process.stdout:
        record["result"] = json.loads(process.stdout)
    if process.stderr:
        path = Path(config["root"]) / "private" / "test-s04-capture-stderr-01.log"
        with path.open("x") as stream:
            stream.write(process.stderr)
        path.chmod(0o600)
        record.update(stderr_private_path=str(path), stderr_sha256=hashlib.sha256(process.stderr.encode()).hexdigest())
except Exception as exc:  # noqa: BLE001 -- preserve failure without database recapture
    record.update(status="failed", error_type=type(exc).__name__)
record["ended_at"] = datetime.now(timezone.utc).isoformat()
receipt.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({k: v for k, v in record.items() if k != "command"}))
raise SystemExit(0 if record["status"] == "passed" else 1)
