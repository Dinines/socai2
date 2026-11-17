"""One explicitly named KB phase using the root's actual container profile."""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

folder = Path(__file__).resolve().parent
cfg = json.loads((folder / "runtime.json").read_text())
action = sys.argv[1]
assert action in {"ingest_K1", "ingest_K2", "index", "readback", "retrieve"}
suffix = "02" if action == "readback" else "01"
receipt = folder / ("knowledge-" + action + "-" + suffix + ".json")
record = {"status": "started", "action": action, "started_at": datetime.now(timezone.utc).isoformat()}
with receipt.open("x") as stream:
    json.dump(record, stream, indent=2)
base = json.loads((Path(cfg["root"]) / "analysis/docker-base.json").read_text())
args = [*base, "--rm", "-i", "--volume", str(folder) + ":/source-batch:ro"]
if action == "readback":
    private = cfg["reader_private_path"]
    args += ["--user", str(os.getuid()) + ":" + str(os.getgid()), "--volume", private + ":" + private + ":ro"]
args += ["--entrypoint", "python", cfg["image"], "/source-batch/knowledge_actions.py", "/source-batch", action]
record["command_sha256"] = hashlib.sha256(json.dumps(args).encode()).hexdigest()
record["docker_base_sha256"] = hashlib.sha256((Path(cfg["root"]) / "analysis/docker-base.json").read_bytes()).hexdigest()
record["image"] = cfg["image"]
try:
    run = subprocess.run(args, capture_output=True, text=True, timeout=cfg["phase_timeout_seconds"], check=False)
    record.update(status="passed" if run.returncode == 0 else "failed", returncode=run.returncode)
    if run.stdout:
        record["result"] = json.loads(run.stdout.splitlines()[-1])
    if run.stderr:
        path = Path(cfg["root"]) / "private" / ("test-case-knowledge-" + action + "-stderr-" + suffix + ".log")
        with path.open("x") as stream:
            stream.write(run.stderr)
        path.chmod(0o600)
        record.update(stderr_private_path=str(path), stderr_sha256=hashlib.sha256(run.stderr.encode()).hexdigest())
except Exception as exc:  # noqa: BLE001 -- intent remains, no automatic replay
    record.update(status="unknown_inspect_before_retry", error_type=type(exc).__name__)
record["ended_at"] = datetime.now(timezone.utc).isoformat()
receipt.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: v for k, v in record.items() if k not in {"command", "result"}}))
raise SystemExit(0 if record["status"] == "passed" else 1)
