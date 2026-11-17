"""Deployment documentation metadata only; explicit safe fields, no credentials or writes."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit

cfg = json.load(sys.stdin)


def command(args, body=None):
    result = subprocess.run(args, input=body, text=True, capture_output=True,
        timeout=cfg["probe_timeout_seconds"], check=False)
    if result.returncode:
        raise RuntimeError("metadata_command_exit_" + str(result.returncode))
    return result.stdout


out = {"observed_at": datetime.now(timezone.utc).isoformat(), "mode": "read_only",
       "target": cfg["target"], "model_calls": 0, "services_changed": False, "containers": []}
allowed = set(cfg["safe_environment_names"])
for row in json.loads(command(["docker", "inspect", *cfg["containers"]])):
    env = dict(item.split("=", 1) for item in row["Config"]["Env"] if "=" in item)
    values = {key: value for key, value in env.items() if key in allowed}
    for key in ("DATABASE_URL", "SOCAI2_CASE_DATABASE_URL", "REDIS_URL", "NEO4J_URI", "QDRANT_URL", "OPENSEARCH_URL", "OPENAI_BASE_URL"):
        if env.get(key):
            url = urlsplit(env[key])
            values[key] = {"scheme": url.scheme, "host": url.hostname, "port": url.port,
                           "user": url.username, "path": url.path}
    host = row["HostConfig"]
    safe_args = {}
    argv = row["Config"].get("Cmd") or []
    for index, value in enumerate(argv[:-1]):
        if value in {"--appendonly", "--appendfsync", "--aclfile", "--maxmemory", "--maxmemory-policy", "--port", "--save"}:
            safe_args[value] = argv[index + 1]
    out["containers"].append({"name": row["Name"].lstrip("/"), "image": row["Config"]["Image"],
        "image_id": row["Image"], "running": row["State"]["Running"], "started_at": row["State"]["StartedAt"],
        "ports": row["NetworkSettings"]["Ports"], "networks": sorted(row["NetworkSettings"]["Networks"]),
        "environment_names": sorted(env), "safe_environment": values, "safe_startup_arguments": safe_args,
        "compose_files": row["Config"].get("Labels", {}).get("com.docker.compose.project.config_files"),
        "resources": {key: host.get(key) for key in ("Memory", "MemorySwap", "NanoCpus", "ShmSize", "Tmpfs", "ReadonlyRootfs", "StorageOpt")},
        "mounts": [{key: item.get(key) for key in ("Type", "Source", "Destination", "RW")} for item in row["Mounts"]]})
body = "BEGIN READ ONLY; SET LOCAL statement_timeout=" + str(cfg["statement_timeout_ms"]) + ";\n"
body += """SELECT json_build_object('version',current_setting('server_version'),'settings',
 (SELECT json_agg(t) FROM (SELECT name,setting,unit,context,pending_restart FROM pg_settings
 WHERE name IN ('data_directory','listen_addresses','port','ssl','ssl_cert_file','ssl_key_file','ssl_ca_file',
 'max_connections','shared_buffers','work_mem','maintenance_work_mem','max_wal_size','min_wal_size',
 'synchronous_commit','wal_level','archive_mode','timezone','statement_timeout','lock_timeout','idle_in_transaction_session_timeout')
 ORDER BY name) t));\nROLLBACK;"""
out["postgres"] = json.loads(command(["docker", "exec", "-i", cfg["postgres_container"], "psql", "-XwAtq",
    "-v", "ON_ERROR_STOP=1", "-U", cfg["postgres_admin"], "-d", cfg["metadata_database"]], body))
print(json.dumps(out, ensure_ascii=False, indent=2))
