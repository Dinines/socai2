"""One source-fixture action; existing invocation receipts forbid replay."""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

folder = Path(__file__).resolve().parent
action = sys.argv[1]
if action not in {"install", "readback"}:
    raise SystemExit("unknown action")
plan = json.loads((folder / "sources-plan.json").read_text())
identity = json.loads((folder / "source-target.json").read_text())
config = json.loads((folder / "source-runtime.json").read_text())
assert plan["candidate_id"] == identity["candidate_id"] == config["candidate_id"]
assert plan["target"]["database"] == identity["postgres"]["database"] == config["database"]
assert plan["target"]["installer_role"] == identity["postgres"]["admin_role"]
receipt = folder / ("source-" + action + "-invocation-02.json")
record = {"action": action, "status": "started", "started_at": datetime.now(timezone.utc).isoformat(),
          "sources_plan_sha256": hashlib.sha256((folder / "sources-plan.json").read_bytes()).hexdigest()}
with receipt.open("x") as stream:
    json.dump(record, stream, indent=2)
if action == "install":
    args = ["docker", "exec", "-i", identity["postgres"]["container"], "psql", "--no-psqlrc",
            "--quiet", "--no-align", "--tuples-only", "--username", plan["target"]["installer_role"],
            "--dbname", plan["target"]["database"], "--set", "ON_ERROR_STOP=1",
            "--set", "source_plan=" + json.dumps(plan)]
    stdin = (folder / "source-import.sql").read_text()
else:
    imported = json.loads((folder / "source-install-invocation-02.json").read_text())
    assert imported["status"] == "passed"
    private = config["private_http_source"]
    args = ["docker", "run", "--rm", "--network", config["network"],
            "--user", str(os.getuid()) + ":" + str(os.getgid()),
            "--volume", str(folder) + ":/batch", "--volume", private + ":" + private + ":ro",
            "--entrypoint", "python", config["image"], "/batch/source-readback.py", "/batch"]
    stdin = None
record["command"] = args
try:
    process = subprocess.run(args, input=stdin, capture_output=True, text=True,
                             timeout=config["command_timeout_seconds"], check=False)
    record.update(status="passed" if process.returncode == 0 else "failed", returncode=process.returncode)
    if process.stdout:
        try:
            record["result"] = json.loads(process.stdout)
        except ValueError:
            record["stdout_sha256"] = hashlib.sha256(process.stdout.encode()).hexdigest()
            record["status"] = "unparsed_result"
    if process.stderr:
        error_path = Path(config["root"]) / "private" / ("test-ai-source-" + action + "-stderr-02.log")
        with error_path.open("x") as stream:
            stream.write(process.stderr)
        error_path.chmod(0o600)
        record["stderr_private_path"] = str(error_path)
        record["stderr_sha256"] = hashlib.sha256(process.stderr.encode()).hexdigest()
except Exception as exc:  # noqa: BLE001 -- record uncertainty; never repeat the insertion
    record.update(status="unknown", error_type=type(exc).__name__)
record["ended_at"] = datetime.now(timezone.utc).isoformat()
receipt.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({key: value for key, value in record.items() if key != "command"}))
raise SystemExit(0 if record["status"] == "passed" else 1)
