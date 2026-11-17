"""Read only candidate name/port availability; no resource creation or service changes."""

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

cfg = json.load(sys.stdin)


def command(argv, body=None):
    result = subprocess.run(
        argv, input=body, text=True, capture_output=True,
        timeout=cfg["probe_timeout_seconds"], check=False,
    )
    if result.returncode:
        raise RuntimeError("metadata_command_exit_" + str(result.returncode))
    return result.stdout


def literal(value):
    return "'" + value.replace("'", "''") + "'"


directory = Path(cfg["candidate_directory"])
parent = directory
while not parent.exists():
    parent = parent.parent
usage = shutil.disk_usage(parent)
out = {
    "observed_at": datetime.now(timezone.utc).isoformat(),
    "target": cfg["target"], "mode": "read_only", "model_calls": 0,
    "remote_resources_created": 0,
    "directory": {"path": str(directory), "exists": directory.exists(),
                  "existing_parent": str(parent), "free_bytes": usage.free},
}
rows = json.loads(command(["docker", "inspect", *cfg["containers"]]))
out["containers"] = [
    {"name": d["Name"].lstrip("/"), "image": d["Config"]["Image"],
     "image_id": d["Image"], "running": d["State"]["Running"],
     "started_at": d["State"]["StartedAt"],
     "networks": sorted(d["NetworkSettings"]["Networks"])}
    for d in rows
]
listeners = command(["ss", "-H", "-lnt"]).splitlines()
out["ports"] = {
    label: {"port": port, "listening": any(
        line.split()[3].rsplit(":", 1)[-1] == str(port)
        for line in listeners if len(line.split()) >= 4
    )}
    for label, port in cfg["candidate_ports"].items()
}
query = (
    "BEGIN READ ONLY; SET LOCAL statement_timeout="
    + str(cfg["statement_timeout_ms"]) + ";\n"
    "SELECT json_build_object('database_exists', EXISTS(SELECT 1 FROM pg_database WHERE datname="
    + literal(cfg["candidate_database"]) + "), 'role_exists', EXISTS(SELECT 1 FROM pg_roles WHERE rolname="
    + literal(cfg["candidate_role"]) + "));\nROLLBACK;"
)
out["postgres"] = json.loads(command([
    "docker", "exec", "-i", cfg["postgres_container"], "psql", "-XwAtq",
    "-v", "ON_ERROR_STOP=1", "-U", cfg["postgres_admin"],
    "-d", cfg["metadata_database"],
], query))
topics = set(command([
    "docker", "exec", cfg["kafka_container"], "kafka-topics",
    "--bootstrap-server", cfg["kafka_metadata_endpoint"], "--list",
]).splitlines())
out["topics"] = [{"name": name, "exists": name in topics}
                 for name in cfg["candidate_topics"]]
out["available_at_observation"] = (
    not out["directory"]["exists"]
    and not any(item["listening"] for item in out["ports"].values())
    and not any(out["postgres"].values())
    and not any(item["exists"] for item in out["topics"])
)
print(json.dumps(out, ensure_ascii=False, indent=2))
