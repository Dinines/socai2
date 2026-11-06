"""Host-side launcher for the isolated, on-demand processing module on 21."""
import argparse
import fcntl
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit
from uuid import NAMESPACE_URL, uuid5

BASE = Path("/opt/sting-aisoc-socai2")
HERE = Path(__file__).resolve().parent
PRIVATE = BASE / "private" / "processing-handoff"
PG = "spirithub-postgres-1"
DATABASE = "socai2_processing_handoff"
ROLE = "socai2_processing_job"
MARK = "socai2-processing-handoff"
TENANT = str(uuid5(NAMESPACE_URL, MARK + ":tenant"))
ACTOR = str(uuid5(NAMESPACE_URL, MARK + ":actor"))
BASE_TAG = "socai2-next-api:20261104-n15"
BASE_ID = "sha256:c78b01862896f966cf8f6901ad21baa941f35ebe6ec83a5894d17c97575a5795"
NETWORK = "socai2_default"
LAKE = "socai2_next_validation"


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def call(args, *, body=None, phase, timeout=90):
    result = subprocess.run(args, input=body, text=True, capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        # Do not propagate psql statements, container environments or DSNs into logs.
        raise RuntimeError(phase + " failed (exit " + str(result.returncode) + ")")
    return result.stdout.strip()


def docker(*args, phase="docker", timeout=90):
    return call(["docker", *args], phase=phase, timeout=timeout)


def pg(database, sql, phase):
    require(database in {"postgres", DATABASE}, "unexpected database")
    return call(["docker", "exec", "-i", PG, "psql", "-XAtq", "-v", "ON_ERROR_STOP=1",
                 "-U", "spirithub", "-d", database], body=sql, phase=phase)


def verified_release():
    require(HERE.parent == BASE / "releases" and re.fullmatch(r"processing-[0-9]{8}-r[1-9][0-9]*", HERE.name),
            "launcher must run inside an installed release")
    data = (HERE / "manifest.json").read_bytes()
    manifest = json.loads(data)
    require(manifest["release"] == HERE.name and manifest["database"] == DATABASE
            and manifest["job_role"] == ROLE, "incorrect release manifest")
    for name, desc in manifest["files"].items():
        p = HERE / name
        require(p.resolve().is_relative_to(HERE) and not p.is_symlink()
                and hashlib.sha256(p.read_bytes()).hexdigest() == desc["sha256"], "release checksum mismatch")
    return hashlib.sha256(data).hexdigest()


def image(release_hash, *, build=False):
    tag = "socai2-processing:" + HERE.name
    if build:
        require(docker("image", "inspect", "-f", "{{.Id}}", BASE_TAG) == BASE_ID, "dependency image changed")
        existing = docker("image", "ls", "-q", tag)
        if not existing:
            docker("build", "--network=none", "--pull=false", "--label", "socai2.processing.release=" + release_hash,
                   "--tag", tag, str(HERE), phase="processing image build", timeout=300)
    info = json.loads(docker("image", "inspect", tag))[0]
    config = info["Config"]
    require(config["Labels"].get("socai2.processing.release") == release_hash
            and config["Entrypoint"] == ["python", "-B", "/opt/processor/processing_job.py"]
            and config["User"] == "10001:10001", "processing image identity mismatch")
    return info["Id"]


def ensure_private():
    require(PRIVATE.parent.resolve() == PRIVATE.parent and PRIVATE.parent.is_dir(), "invalid private root")
    PRIVATE.mkdir(mode=0o700, exist_ok=True)
    require(PRIVATE.resolve() == PRIVATE and PRIVATE.stat().st_mode & 0o077 == 0, "unsafe private directory")


def owned(kind, name):
    table, field = ("pg_database", "datname") if kind == "database" else ("pg_authid", "rolname")
    return pg("postgres", f"SELECT coalesce(shobj_description(oid,'{table}'),'unmarked') "
              f"FROM {table} WHERE {field}='{name}';", "inspect ownership")


def secret_file(name, prefix=""):
    path = PRIVATE / name
    if not path.exists():
        with path.open("x") as f:
            f.write(prefix + secrets.token_hex(32) + "\n")
    require(path.resolve() == path and path.stat().st_mode & 0o077 == 0, "unsafe private file")
    value = path.read_text().strip()
    require(re.fullmatch(prefix + "[0-9a-f]{64}", value), "invalid local private file")
    return value


def schema_body(path):
    # Execute the repository's guarded migrations and their ledger entries as one
    # transaction in the newly created DB, including a rollback on any error.
    sql = path.read_text()
    sql, starts = re.subn(r"(?m)^BEGIN;[ \t]*$", "", sql)
    sql, ends = re.subn(r"(?m)^COMMIT;[ \t]*$", "", sql)
    require(starts == ends == 1, "unexpected migration transaction wrapper")
    return sql


def bootstrap():
    role_mark, db_mark = owned("role", ROLE), owned("database", DATABASE)
    require(role_mark in {"", MARK} and db_mark in {"", MARK}, "foreign database or role")
    if role_mark or db_mark:
        require(all((PRIVATE / n).is_file() for n in ["db-password", "job-key"]), "missing private identity")
    password = secret_file("db-password")
    key = secret_file("job-key", "aisoc_")
    # Only the unprivileged container uid can read this individual bind-mount.
    # The 0700 host directory stays root-owned.
    os.chown(PRIVATE / "job-key", 10001, 10001)
    if not role_mark:
        pg("postgres", f"BEGIN; CREATE ROLE {ROLE} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE "
           f"NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 12 PASSWORD '{password}'; "
           f"COMMENT ON ROLE {ROLE} IS '{MARK}'; COMMIT;", "create limited job role")
    if not db_mark:
        pg("postgres", f"CREATE DATABASE {DATABASE} TEMPLATE template0 ALLOW_CONNECTIONS false; "
           f"COMMENT ON DATABASE {DATABASE} IS '{MARK}'; REVOKE ALL ON DATABASE {DATABASE} FROM PUBLIC; "
           f"ALTER DATABASE {DATABASE} ALLOW_CONNECTIONS true;", "create dedicated database")
    applied = pg(DATABASE, "SELECT to_regclass('socai2.cases') IS NOT NULL;", "inspect schema")
    if applied == "f":
        root = HERE / "schema"
        migrations = sorted(root.glob("12[3-6]_*.sql"))
        require(len(migrations) == 4, "missing migrations")
        sql = [schema_body(root / "support.sql")]
        for p in migrations:
            sql.append(schema_body(p))
            sql.append(f"INSERT INTO public.aisoc_schema_migrations(name) VALUES ('{p.name}') ON CONFLICT (name) DO NOTHING;")
        sql.append(schema_body(root / "grants.sql"))
        pg(DATABASE, "BEGIN;\n" + "\n".join(sql) + f"""
INSERT INTO public.tenants(id,name,slug,plan,is_active,settings,limits,created_at,updated_at)
VALUES('{TENANT}','Processing handoff','processing-handoff','starter',true,'{{}}','{{}}',now(),now());
INSERT INTO public.users(id,tenant_id,email,username,hashed_password,role,is_active,is_verified,preferences,created_at,updated_at)
VALUES('{ACTOR}','{TENANT}','processing-handoff@example.invalid','processing-handoff','!scoped-key-only','soc_analyst',true,true,'{{}}',now(),now());
INSERT INTO public.api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,is_active,created_at)
VALUES('{uuid5(NAMESPACE_URL, MARK + ":key")}','{TENANT}','{ACTOR}','Internal investigation jobs','{key[:12]}',
'{hashlib.sha256(key.encode()).hexdigest()}','["alerts:write","cases:write","alerts:read","cases:read"]'::jsonb,true,now());
COMMIT;""", "initialize processing schema and scoped identity")
    state = pg(DATABASE, f"""BEGIN READ ONLY; SELECT current_database()='{DATABASE}' AND
    (SELECT count(*)=4 FROM public.aisoc_schema_migrations WHERE left(name,3) IN ('123','124','125','126')) AND
    (SELECT count(*)=29 FROM pg_class WHERE relnamespace='socai2'::regnamespace AND relkind='r' AND relforcerowsecurity)
    AND NOT has_schema_privilege('{ROLE}','socai2','CREATE') AND NOT has_table_privilege('{ROLE}','socai2.artifacts','UPDATE')
    AND EXISTS(SELECT FROM public.api_keys WHERE tenant_id='{TENANT}' AND user_id='{ACTOR}' AND is_active
         AND hashed_key='{hashlib.sha256(key.encode()).hexdigest()}'); COMMIT;""", "verify operational database")
    require(state == "t", "processing schema or scoped grants differ")


def configuration():
    # Only select the existing internal gateway/CA/infrastructure options. The
    # independent service's currently selected DeepSeek provider is never inherited.
    original = BASE / "private" / "next-20261104" / "api.env"
    values = dict(s.split("=", 1) for s in original.read_text().splitlines() if s and not s.startswith("#") and "=" in s)
    require(values["CLICKHOUSE_USER"] == "socai2_next_reader_20261104"
            and values["CLICKHOUSE_DATABASE"] == values["SOCAI2_LAKE_DATABASE"] == LAKE, "unexpected lake config")
    dsn = urlsplit(values["DATABASE_URL"])
    require(dsn.hostname == "192.168.1.21" and (dsn.port or 5432) == 5432, "unexpected PG endpoint")
    key = values.get("OPENAI_API_KEY") or values.get("LLM_GATEWAY_API_KEY") or values.get("LITELLM_MASTER_KEY")
    require(key, "internal gateway credential unavailable")
    names = ("CLICKHOUSE_HOST", "CLICKHOUSE_PORT", "CLICKHOUSE_USER", "CLICKHOUSE_PASSWORD", "CLICKHOUSE_DATABASE",
             "REDIS_URL", "SSL_CERT_FILE", "PGSSLROOTCERT", "PGSSLMODE", "REQUESTS_CA_BUNDLE",
             "AISOC_ALLOW_CLEARTEXT_DB", "PLUGIN_TRUST_MODE")
    env = {k: values[k] for k in names if k in values}
    # Dedicated application secrets, even for framework settings unused by this CLI.
    for name in ("SECRET_KEY", "JWT_SECRET", "REALTIME_INTERNAL_TOKEN", "AISOC_REALTIME_JWT_SECRET", "METRICS_TOKEN"):
        env[name] = secret_file(name.lower())
    if "AISOC_CREDENTIAL_KEY" in values:
        env["AISOC_CREDENTIAL_KEY"] = values["AISOC_CREDENTIAL_KEY"]
    authority = ROLE + ":" + quote(secret_file("db-password"), safe="") + "@" + dsn.hostname + ":5432"
    env.update(DATABASE_URL=urlunsplit((dsn.scheme, authority, "/" + DATABASE, dsn.query, "")),
               SOCAI2_SERVICE_DATABASE_NAME=DATABASE, SOCAI2_PROCESSING_DB_ROLE=ROLE, SOCAI2_PROCESSING_TENANT_ID=TENANT,
               SOCAI2_PROCESSING_ACTOR_ID=ACTOR, SOCAI2_PROCESSING_API_KEY_FILE="/run/processor/key",
               ENVIRONMENT="production", ENV="production", DEBUG="false", AISOC_DEV_AUTH_BYPASS="false",
               SOCAI2_MODEL_PROTOCOL="chat_completions", SOCAI2_MODEL_SCHEMA_PROFILE="vllm_grammar_v1",
               OPENAI_API_KEY=key, OPENAI_MODEL="aisoc-investigation", OPENAI_BASE_URL="http://litellm:4000/v1",
               AISOC_AIRGAPPED="true", AISOC_AIRGAP_ALLOWLIST='["litellm"]', SOCAI2_LAKE_DATABASE=LAKE,
               SOCAI2_SOURCE_UEBA_ENABLED="true", SOCAI2_SOURCE_KNOWLEDGE_ENABLED="true",
               SOCAI2_SOURCE_GRAPH_ENABLED="false", SOCAI2_SOURCE_PRODUCT_HOST_ENABLED="false", DATABASE_POOL_SIZE="2",
               DATABASE_MAX_OVERFLOW="1")
    require(not any("\n" in v or "\r" in v for v in env.values()), "multiline environment entry")
    path = PRIVATE / "config.next"
    path.write_text("".join(k + "=" + v + "\n" for k, v in env.items()))
    path.replace(PRIVATE / "runtime.env")


def run(image_id, args, *, smoke=False):
    invocation = ["docker", "run", "--rm", "--pull=never", "--network", NETWORK, "--read-only",
                  "--cap-drop=ALL", "--security-opt=no-new-privileges", "--memory=2g", "--pids-limit=128",
                  "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m,mode=1777", "--env-file", str(PRIVATE / "runtime.env"),
                  "--mount", "type=bind,src=" + str(PRIVATE / "job-key") + ",dst=/run/processor/key,readonly",
                  "--mount", "type=bind,src=" + str(BASE / "certificates/socai2-ca.crt") + ",dst=/run/certs/ca.crt,readonly"]
    if smoke:
        invocation += ["--entrypoint", "python", image_id, "-B", "/opt/processor/processing_smoke.py", *args]
    else:
        invocation += [image_id, *args]
    # Keep internal dependency logs (potentially including DSNs) off stdout.
    proc = subprocess.run(invocation, capture_output=True, text=True, check=False)
    for line in reversed(proc.stdout.splitlines()):
        if smoke and re.fullmatch(r"SMOKE_ERROR [a-zA-Z][a-zA-Z0-9_]{0,120}", line):
            print(json.dumps({"error": line.split(" ", 1)[1], "action": "smoke"}))
            return 1
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict) and set(value).intersection({
                "error", "check", "test", "phase", "case_id", "run_id", "source_run_id", "state"}):
            print(json.dumps(value, ensure_ascii=False))
            return proc.returncode
    if "--help" in args and proc.returncode == 0:
        print(proc.stdout.strip())
    else:
        print(json.dumps({"error": "processing_container_did_not_return_receipt", "exit": proc.returncode}))
    return proc.returncode or (0 if "--help" in args else 1)


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["install", "job", "smoke"])
    p.add_argument("args", nargs=argparse.REMAINDER)
    a = p.parse_args()
    release_hash = verified_release()
    if a.action == "install":
        ensure_private()
        with (PRIVATE / "install.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            image_id = image(release_hash, build=True)
            bootstrap()
            configuration()
        print(json.dumps({"release": HERE.name, "image_id": image_id, "manifest_sha256": release_hash,
                          "database": DATABASE, "mode": "on_demand", "published_ports": []}))
        return 0
    return run(image(release_hash), a.args or ["--help"], smoke=a.action == "smoke")


if __name__ == "__main__":
    sys.exit(main())
