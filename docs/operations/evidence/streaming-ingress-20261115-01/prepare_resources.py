"""One candidate preparation receipt. stdin carries explicit config and rendered SQL.

Run on the selected host. No business messages, models, cleanup or old service changes.
Passwords stay in the candidate private directory; only allowlisted metadata is printed.
"""
import hashlib
import json
import os
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

payload = json.load(sys.stdin)
c = payload["config"]
root = Path(c["root"])
private = root / "private"
out = {"candidate_id": c["candidate_id"], "status": "running", "steps": [],
       "started_at": datetime.now(timezone.utc).isoformat(), "model_calls": 0,
       "kafka_messages_sent": 0, "dispatcher_enabled": False}
stage = "preflight"


def private_file(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)


def run(args, body=None):
    r = subprocess.run(args, input=body, text=True, capture_output=True,
                       timeout=c["timeout_seconds"], check=False)
    if r.returncode:
        path = private / ("ingress-prepare-error-" + secrets.token_hex(4) + ".txt")
        private_file(path, r.stderr + "\n" + r.stdout)
        raise RuntimeError("command_exit_" + str(r.returncode) + "; private_detail=" + str(path))
    return r.stdout


def pg(sql):
    p = c["postgres"]
    return run(["docker", "exec", "-i", p["container"], "psql", "-XwAtq", "-v", "ON_ERROR_STOP=1",
                "-U", p["admin_role"], "-d", p["database"],
                "-v", "expected_database=" + p["database"], "-v", "function_owner=" + p["owner"],
                "-v", "reader_role=" + p["reader"], "-v", "analysis_ingress_role=" + p["writer"],
                "-v", "analysis_ingress_lock_timeout=" + str(p["lock_timeout_seconds"]) + "s", "-v", "analysis_ingress_statement_timeout=" + str(p["statement_timeout_seconds"]) + "s"], sql)


def ch(sql):
    return run(["docker", "exec", "-i", c["clickhouse"]["container"], "clickhouse-client", "--multiquery"], sql)


def kafka(args):
    k = c["kafka"]
    return run(["docker", "exec", k["container"], "kafka-topics", "--bootstrap-server", k["metadata_bootstrap"], *args])


try:
    assert root.is_dir() and private.is_dir()
    names = set(run(["docker", "ps", "-a", "--format", "{{.Names}}"] ).splitlines())
    assert c["fusion_container"] not in names and c["redis"]["container"] not in names
    existing_topics = set(kafka(["--list"]).splitlines())
    assert not existing_topics.intersection(c["kafka"]["topics"].values())
    assert c["clickhouse"]["database"] not in ch("SHOW DATABASES;").splitlines()
    users = set(ch("SHOW USERS;").splitlines())
    assert not users.intersection([c["clickhouse"]["writer"], c["clickhouse"]["reader"]])
    assert not Path(c["redis"]["data_directory"]).exists()
    assert Path(c["kafka"]["ca_source"]).is_file()
    for path in ("fusion.env", "clickhouse-runtime.json", "producer.env", "redis-runtime.json"):
        assert not (private / path).exists()
    counts = json.loads(pg("SELECT json_build_object('alerts',(SELECT count(*) FROM socai2.alerts),'incidents',(SELECT count(*) FROM socai2.incidents),'cases',(SELECT count(*) FROM socai2.cases),'tasks',(SELECT count(*) FROM socai2.analysis_tasks),'runs',(SELECT count(*) FROM socai2.runs));"))
    assert not any(counts.values())
    out["empty_business_start"] = counts
    out["steps"].append("preflight_passed")

    stage = "postgres_support"
    pg(payload["support_sql"])
    out["support_sql_sha256"] = hashlib.sha256(payload["support_sql"].encode()).hexdigest()
    out["postgres_support"] = json.loads(pg("SELECT json_build_object('tables',(SELECT json_agg(tablename ORDER BY tablename) FROM pg_tables WHERE schemaname='public' AND tablename IN ('sessions','aisoc_dead_letters','aisoc_ai_assets')),'socai2_tables',(SELECT count(*) FROM information_schema.tables WHERE table_schema='socai2'),'socai2_columns',(SELECT count(*) FROM information_schema.columns WHERE table_schema='socai2'),'legacy_public_alerts',to_regclass('public.alerts'));"))
    assert out["postgres_support"]["socai2_tables"] == 32
    assert out["postgres_support"]["socai2_columns"] == 521
    assert len(out["postgres_support"]["tables"]) == 3
    assert out["postgres_support"]["legacy_public_alerts"] is None
    out["steps"].append("postgres_support_passed")

    stage = "clickhouse"
    lake = c["clickhouse"]
    creds = {"host": lake["host"], "port": lake["native_port"], "database": lake["database"],
             "writer": {"user": lake["writer"], "password": secrets.token_urlsafe(36)},
             "reader": {"user": lake["reader"], "password": secrets.token_urlsafe(36)}}
    private_file(Path(lake["private_runtime"]), json.dumps(creds, indent=2) + "\n")
    ch("CREATE DATABASE " + lake["database"] + ";\nCREATE TABLE " + lake["database"] + ".raw_events AS " + lake["schema_source"] + ";\n"
       + "\n".join("CREATE USER " + creds[k]["user"] + " IDENTIFIED WITH sha256_password BY '" + creds[k]["password"] + "';\nGRANT " + ("SELECT, INSERT" if k == "writer" else "SELECT") + " ON " + lake["database"] + ".raw_events TO " + creds[k]["user"] + ";" for k in ("writer", "reader")))
    schema = json.loads(ch("SELECT name,type FROM system.columns WHERE database='" + lake["database"] + "' AND table='raw_events' ORDER BY position FORMAT JSON;"))["data"]
    assert len(schema) == 48
    out["clickhouse"] = {"database": lake["database"], "table": "raw_events", "columns": schema,
                         "rows": int(ch("SELECT count(*) FROM " + lake["database"] + ".raw_events;"))}
    assert out["clickhouse"]["rows"] == 0
    out["steps"].append("clickhouse_created_empty")

    stage = "kafka_topics"
    k = c["kafka"]
    for name in k["topics"].values():
        kafka(["--create", "--topic", name, "--partitions", str(k["partitions"]),
               "--replication-factor", str(k["replication_factor"]), "--config", "retention.ms=" + str(k["retention_ms"])])
    out["topics"] = {label: kafka(["--describe", "--topic", name]).strip() for label, name in k["topics"].items()}
    out["steps"].append("four_topics_created")

    stage = "redis"
    redis = c["redis"]
    assert redis["password_required"]
    redis_password = secrets.token_urlsafe(36)
    private_file(Path(redis["private_runtime"]), json.dumps({"password": redis_password}) + "\n")
    Path(redis["data_directory"]).mkdir(parents=True, mode=0o755)
    redis_config = Path(redis["config_path"])
    redis_config.write_text("bind 0.0.0.0\nprotected-mode yes\nport " + str(redis["port"]) + "\ndir /data\nappendonly yes\nrequirepass " + redis_password + "\n")
    redis_uid = int(run(["docker", "run", "--rm", "--network", "none", "--entrypoint", "id", redis["image"], "-u", "redis"]))
    redis_config.chmod(0o600)
    os.chown(redis_config, redis_uid, -1)
    run(["docker", "run", "-d", "--name", redis["container"], "--network", c["network"],
         "--restart", "no", "--mount", "type=bind,src=" + redis["data_directory"] + ",dst=/data",
         "--mount", "type=bind,src=" + redis["config_path"] + ",dst=/usr/local/etc/redis/redis.conf,readonly",
         redis["image"], "redis-server", "/usr/local/etc/redis/redis.conf"])
    # Password is read over stdin inside the container, not exposed in argv.
    redis_query = "read -r REDISCLI_AUTH; export REDISCLI_AUTH; exec redis-cli -n \"$1\" DBSIZE"
    out["redis"] = {"container": redis["container"], "host_ports": [], "password_required": True,
                    "db0_size": int(run(["docker", "exec", "-i", redis["container"], "sh", "-c", redis_query, "sh", str(redis["fusion_db"])], redis_password + "\n")),
                    "db1_size": int(run(["docker", "exec", "-i", redis["container"], "sh", "-c", redis_query, "sh", str(redis["reserved_dispatch_db"])], redis_password + "\n"))}
    assert out["redis"]["db0_size"] == out["redis"]["db1_size"] == 0
    out["steps"].append("redis_started_empty")

    stage = "private_runtime"
    policy_path = root / "initial-task-policy.json"
    policy_path.write_text(json.dumps(c["initial_task_policy"], indent=2) + "\n")
    env = dict(c["fusion_env"])
    env.update({"HTTP_PORT": str(c["fusion_http_port"]), "DATABASE_URL": json.loads(Path(c["postgres"]["private_runtime"]).read_text())["SOCAI2_CASE_DATABASE_URL"],
                "KAFKA_BOOTSTRAP_SERVERS": k["bootstrap"], "KAFKA_SECURITY_PROTOCOL": k["security_protocol"],
                "KAFKA_SSL_CAFILE": k["ca_target"], "KAFKA_CONSUMER_GROUP": k["group"],
                "KAFKA_TOPIC_ALERTS_RAW": k["topics"]["raw"], "KAFKA_TOPIC_ALERTS_FUSED": k["topics"]["fused"],
                "KAFKA_TOPIC_RAW_EVENTS": k["topics"]["raw_events"],
                "REDIS_URL": "redis://:" + redis_password + "@" + redis["container"] + ":" + str(redis["port"]) + "/" + str(redis["fusion_db"]),
                "CLICKHOUSE_HOST": lake["host"], "CLICKHOUSE_PORT": str(lake["native_port"]),
                "CLICKHOUSE_DATABASE": lake["database"], "CLICKHOUSE_USER": creds["writer"]["user"],
                "CLICKHOUSE_PASSWORD": creds["writer"]["password"],
                "SOCAI2_ANALYSIS_TASKS_CONFIG_FILE": "/run/config/initial-task-policy.json",
                "PYTHONPATH": c["fusion_workdir"]})
    assert all("\n" not in v and "\r" not in v for v in env.values())
    private_file(private / "fusion.env", "\n".join(k + "=" + v for k,v in env.items()) + "\n")
    producer = {"ENVIRONMENT": "production", "KAFKA_BOOTSTRAP_SERVERS": k["bootstrap"],
                "KAFKA_SECURITY_PROTOCOL": k["security_protocol"], "KAFKA_SSL_CAFILE": k["ca_target"]}
    private_file(private / "producer.env", "\n".join(k + "=" + v for k,v in producer.items()) + "\n")
    out["private_files"] = [{"path": str(p), "mode": oct(p.stat().st_mode & 0o777)} for p in
                            (private / "fusion.env", private / "producer.env", Path(lake["private_runtime"]))]
    out["steps"].append("private_runtime_written")
    out["status"] = "passed"
except Exception as exc:  # noqa: BLE001 -- retain the failed candidate preparation receipt
    out["status"] = "failed"
    out["failure_stage"] = stage
    out["error"] = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
finally:
    out["ended_at"] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(out, ensure_ascii=False, indent=2))
    (root / "ingress-prepare-receipt.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
sys.exit(0 if out["status"] == "passed" else 1)
