"""21 host entry point for explicitly requested production investigation jobs."""
import argparse
import base64
import fcntl
import getpass
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit, urlunsplit
from uuid import UUID

BASE = Path("/opt/sting-aisoc-socai2")
HERE = Path(__file__).resolve().parent
PRIVATE = BASE / "private/processing-production"
IMAGE = "sha256:7218b535ca88c17616f563aa1efb6935f8eedd89e5fed4140ea6c8e4949c0be7"
TAG = "socai2-processing:processing-20261106-r3"
PROCESSOR = "socai2_prod_processor"
INGRESS = "socai2_prod_ingress"
LAKE_READER = "socai2_prod_lake_reader"
DEFAULT_TENANT = UUID("00000000-0000-0000-0000-000000000001")
PG = "spirithub-postgres-1"
CH = "sting-infra21-clickhouse-1"
API = "socai2-api-1"
ACTIONS = ("alert", "incident", "case-create", "case-prepare", "case-start")


class SetupError(Exception):
    """Safe code for operator output."""


def need(ok, code):
    if not ok:
        raise SetupError(code)


def call(args, *, body=None, code):
    result = subprocess.run(args, input=body, text=True, capture_output=True, check=False, timeout=60)
    need(result.returncode == 0, code)
    return result.stdout.strip()


def image_check():
    info = json.loads(call(["docker", "image", "inspect", TAG], code="r3_image_missing"))[0]
    need(info["Id"] == IMAGE and info["Config"]["User"] == "10001:10001", "r3_image_changed")


def secure_file(path):
    need(path.is_file() and path.resolve() == path and path.stat().st_uid == 0
         and path.stat().st_mode & 0o077 == 0, "unsafe_private_file")


def secret(name):
    path = PRIVATE / name
    if not path.exists():
        with path.open("x") as f:
            f.write(secrets.token_hex(32) + "\n")
    secure_file(path)
    value = path.read_text().strip()
    need(re.fullmatch("[0-9a-f]{64}", value), "invalid_private_file")
    return value


def pg(sql):
    return call(["docker", "exec", "-i", PG, "psql", "-XAtq", "-v", "ON_ERROR_STOP=1",
                 "-U", "spirithub", "-d", "aisoc"], body=sql, code="pg_identity_setup_failed")


def scram(password, salt, iterations):
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    stored = hashlib.sha256(hmac.digest(key, b"Client Key", "sha256")).digest()
    server = hmac.digest(key, b"Server Key", "sha256")
    def b64(value):
        return base64.b64encode(value).decode()
    return f"SCRAM-SHA-256${iterations}:{b64(salt)}${b64(stored)}:{b64(server)}"


def pg_credential(role, filename):
    rows = pg(f"""SELECT COALESCE(rolpassword,'uninitialized') FROM pg_catalog.pg_authid
      WHERE rolname='{role}' AND shobj_description(oid,'pg_authid')='socai2:production:v1'
        AND rolcanlogin AND NOT (rolsuper OR rolinherit OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)
        AND NOT EXISTS (SELECT FROM pg_catalog.pg_auth_members WHERE member=pg_authid.oid);""")
    need(rows, "restricted_production_role_required")
    path = PRIVATE / filename
    need(rows == "uninitialized" or path.is_file(), "existing_pg_identity_requires_original_secret")
    password = secret(filename)
    if rows == "uninitialized":
        verifier = scram(password, secrets.token_bytes(16), 4096)
        pg(f"ALTER ROLE {role} PASSWORD '{verifier}';")
    else:
        match = re.fullmatch(r"SCRAM-SHA-256\$(\d+):([A-Za-z0-9+/=]+)\$[^\n]+", rows)
        need(match and 4096 <= int(match[1]) <= 1000000, "existing_pg_identity_mismatch")
        expect = scram(password, base64.b64decode(match[2], validate=True), int(match[1]))
        need(hmac.compare_digest(rows, expect), "existing_pg_identity_mismatch")
    return password


def lake_admin(sql):
    # Expand service credentials only inside the existing ClickHouse container.
    return call(["docker", "exec", "-i", CH, "sh", "-c",
                 'exec clickhouse-client --user "$CLICKHOUSE_USER" --password "$CLICKHOUSE_PASSWORD" --multiquery'],
                body=sql + "\n", code="lake_acl_setup_failed")


def lake_credential():
    count = lake_admin(f"SELECT count() FROM system.users WHERE name='{LAKE_READER}'")
    need(count in {"0", "1"}, "lake_identity_lookup_failed")
    path = PRIVATE / "lake-password"
    need(count == "0" or path.exists(), "existing_lake_identity_requires_original_secret")
    password = secret("lake-password")
    if count == "0":
        lake_admin(f"CREATE USER {LAKE_READER} IDENTIFIED WITH sha256_password BY '{password}'")
    result = subprocess.run(
        ["docker", "exec", "-e", "PROD_CH_PASS", CH, "sh", "-c",
         f'exec clickhouse-client --user {LAKE_READER} --password "$PROD_CH_PASS" --query "SELECT currentUser()"'],
        env={**os.environ, "PROD_CH_PASS": password}, text=True, capture_output=True, check=False, timeout=60)
    need(result.returncode == 0 and result.stdout.strip() == LAKE_READER, "existing_lake_identity_mismatch")
    grant = f"GRANT SELECT ON aisoc.raw_events TO {LAKE_READER}"
    grants = lake_admin(f"SHOW GRANTS FOR {LAKE_READER}").splitlines()
    need(all(g == grant for g in grants), "unexpected_lake_privilege")
    if grant not in grants:
        lake_admin(grant)
    need(lake_admin(f"SHOW GRANTS FOR {LAKE_READER}") == grant, "lake_select_grant_missing")
    return password


def save_env(name, values):
    need(all("\n" not in v and "\r" not in v and "\x00" not in v for v in values.values()), "bad_env_value")
    next_path = PRIVATE / (name + ".next")
    next_path.write_text("".join(f"{k}={v}\n" for k, v in values.items()))
    os.chmod(next_path, 0o600)
    next_path.replace(PRIVATE / name)


def configure():
    transport_path = BASE / "private/processing-handoff/runtime.env"
    secure_file(transport_path)
    shared = dict(line.split("=", 1) for line in transport_path.read_text().splitlines() if "=" in line)
    live = json.loads(call(["docker", "inspect", API], code="production_service_settings_missing"))[0]
    live_env = dict(s.split("=", 1) for s in live["Config"]["Env"] if "=" in s)
    dsn = urlsplit(shared["DATABASE_URL"])
    need(dsn.hostname == "192.168.1.21" and (dsn.port or 5432) == 5432
         and parse_qs(dsn.query) == {"sslmode": ["verify-full"]}
         and shared["PGSSLROOTCERT"] == "/run/certs/ca.crt",
         "production_transport_mismatch")
    need(live_env["CLICKHOUSE_DATABASE"] == "aisoc" and live_env["CLICKHOUSE_HOST"] == "192.168.1.21"
         and live_env["CLICKHOUSE_PORT"] == "9000", "production_lake_endpoint_mismatch")
    need(shared["OPENAI_BASE_URL"] == "http://litellm:4000/v1" and shared["OPENAI_MODEL"] == "aisoc-investigation"
         and shared["OPENAI_API_KEY"], "internal_gateway_missing")
    def url(role, pwd):
        return urlunsplit((dsn.scheme, f"{role}:{pwd}@192.168.1.21:5432", "/aisoc", dsn.query, ""))
    processor_url = url(PROCESSOR, pg_credential(PROCESSOR, "db-password"))
    ingress_url = url(INGRESS, pg_credential(INGRESS, "ingress-password"))
    lake_password = lake_credential()
    env = {"PGSSLMODE": "verify-full", "PGSSLROOTCERT": shared["PGSSLROOTCERT"],
           "SSL_CERT_FILE": shared["PGSSLROOTCERT"]}
    save_env("ingress.env", {**env, "DATABASE_URL": ingress_url, "PYTHONPATH": "/opt/processor/smoke-fusion"})
    for k in ("SECRET_KEY", "JWT_SECRET", "REALTIME_INTERNAL_TOKEN", "AISOC_REALTIME_JWT_SECRET", "METRICS_TOKEN"):
        env[k] = secret(k.lower())
    for k in ("OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL"):
        env[k] = shared[k]
    # The job uses the internal gateway, can run without Redis, and has no need
    # to decrypt a production tenant's BYOK or connector credentials.
    env["AISOC_CREDENTIAL_KEY"] = base64.urlsafe_b64encode(bytes.fromhex(secret("credential-key"))).decode()
    for k in ("CLICKHOUSE_HOST", "CLICKHOUSE_PORT"):
        env[k] = live_env[k]
    env.update(DATABASE_URL=processor_url, SOCAI2_INGRESS_URL=ingress_url, ENVIRONMENT="production", ENV="production",
               DEBUG="false", AISOC_DEV_AUTH_BYPASS="false", CLICKHOUSE_DATABASE="aisoc", CLICKHOUSE_USER=LAKE_READER,
               CLICKHOUSE_PASSWORD=lake_password, SOCAI2_SERVICE_DATABASE_NAME="aisoc", SOCAI2_LAKE_DATABASE="aisoc",
               SOCAI2_PROCESSING_PROFILE="production21", SOCAI2_PROCESSING_DB_ROLE=PROCESSOR,
               SOCAI2_PROCESSING_API_KEY_FILE="/dev/stdin", SOCAI2_MODEL_PROTOCOL="chat_completions",
               SOCAI2_MODEL_SCHEMA_PROFILE="vllm_grammar_v1", AISOC_AIRGAPPED="true", AISOC_AIRGAP_ALLOWLIST='["litellm"]',
               SOCAI2_SOURCE_UEBA_ENABLED="true", SOCAI2_SOURCE_KNOWLEDGE_ENABLED="true",
               SOCAI2_SOURCE_GRAPH_ENABLED="false", SOCAI2_SOURCE_PRODUCT_HOST_ENABLED="false",
               DATABASE_POOL_SIZE="2", DATABASE_MAX_OVERFLOW="1")
    save_env("runtime.env", env)


def run(tenant, actor, args):
    secure_file(PRIVATE / "runtime.env")
    key = ""
    if actor:
        key = getpass.getpass("Scoped user API key: ") if sys.stdin.isatty() else sys.stdin.read(4096).strip()
        need(key.startswith("aisoc_") and not key.startswith("aisoc_wl_") and not any(c.isspace() for c in key),
             "user_api_key_required")
    argv = ["docker", "run", "--rm", "-i", "--pull=never", "--network", "socai2_default", "--read-only",
            "--cap-drop=ALL", "--security-opt=no-new-privileges", "--memory=2g", "--pids-limit=128",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m,mode=1777", "--env-file", str(PRIVATE / "runtime.env"),
            "-e", "SOCAI2_PROCESSING_TENANT_ID=" + str(tenant)]
    if actor:
        argv.extend(("-e", "SOCAI2_PROCESSING_ACTOR_ID=" + str(actor)))
    for local, remote in ((HERE / "processing_job.py", "/opt/processor/production_job.py"),
                          (HERE / "production_ingress.py", "/opt/processor/production_ingress.py"),
                          (BASE / "certificates/socai2-ca.crt", "/run/certs/ca.crt")):
        need(local.is_file(), "production_mount_missing")
        argv.extend(("--mount", "type=bind,src=" + str(local) + ",dst=" + remote + ",readonly"))
    argv.extend(("--entrypoint", "python", IMAGE, "-B", "/opt/processor/production_job.py", *args))
    proc = subprocess.run(argv, input=key, text=True, capture_output=True, check=False)
    for line in reversed(proc.stdout.splitlines()):
        try:
            result = json.loads(line)
        except ValueError:
            continue
        if isinstance(result, dict) and set(result).intersection({"error", "check", "case_id", "run_id", "source_run_id", "state"}):
            print(json.dumps(result, ensure_ascii=False))
            return proc.returncode
    raise SetupError("no_processing_receipt")


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="mode", required=True)
    actions.add_parser("install", help="configure service identities and credentials")
    check = actions.add_parser("check", help="read schema, lake permissions and local model catalog")
    check.add_argument("--tenant", type=UUID, default=DEFAULT_TENANT)
    job = actions.add_parser("job", help="run exactly one requested operation with the caller's key on stdin")
    job.add_argument("--tenant", type=UUID, required=True)
    job.add_argument("--actor", type=UUID, required=True)
    job.add_argument("action", choices=ACTIONS)
    job.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    need(os.geteuid() == 0, "root_required")
    image_check()
    if args.mode == "install":
        PRIVATE.mkdir(mode=0o700, exist_ok=True)
        need(PRIVATE.resolve() == PRIVATE and PRIVATE.stat().st_uid == 0
             and PRIVATE.stat().st_mode & 0o077 == 0, "unsafe_private_directory")
        with (PRIVATE / "install.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            configure()
        print(json.dumps({"mode": "on_demand", "database": "aisoc", "role": PROCESSOR, "image_id": IMAGE,
                          "ingress_role": INGRESS, "lake_role": LAKE_READER, "published_ports": []}))
        return 0
    if args.mode == "check":
        return run(args.tenant, None, ["check"])
    return run(args.tenant, args.actor, [args.action, *args.arguments])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 -- configuration and driver errors can contain private DSNs
        print(json.dumps({"error": str(exc) if isinstance(exc, SetupError) else type(exc).__name__}))
        sys.exit(1)
