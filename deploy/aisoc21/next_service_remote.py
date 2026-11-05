"""Run ON 21 from a verified candidate directory. Never exports credentials.

Default inspect is read-only. bootstrap/build/start are separate explicit steps.
No old container is recreated, stopped or reconfigured; no old business row is copied.
"""
import argparse
import base64
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit
from uuid import NAMESPACE_URL, uuid5

HERE = Path(__file__).resolve().parent
PRIVATE = Path("/opt/sting-aisoc-socai2/private/next-20261104")
DATABASE = "socai2_next_20261104"
ROLE = "socai2_next_app_20261104"
LAKE = "socai2_next_validation"
LAKE_USER = "socai2_next_reader_20261104"
PG = "spirithub-postgres-1"
CH = "sting-infra21-clickhouse-1"
NEW = "socai2-next-api"
OLD = ("socai2-api-1", "socai2-investigation-api", "socai2-fusion-1", "socai2-agents-1")
TENANT = str(uuid5(NAMESPACE_URL, "socai2-next-20261104:synthetic-tenant"))
USER = str(uuid5(NAMESPACE_URL, "socai2-next-20261104:synthetic-user"))


def command(args, *, body=None, timeout=30):
    try:
        result = subprocess.run(args, input=body, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("isolated service command could not complete: " + args[0]) from None
    if result.returncode:
        # stderr/arguments can contain connection strings or credentials.
        raise RuntimeError("isolated service command failed: " + args[0])
    return result.stdout.decode().strip()


def inspect(name):
    return json.loads(command(["docker", "inspect", name]))[0]


def environment(container):
    return dict(v.split("=", 1) for v in inspect(container)["Config"].get("Env", []) if "=" in v)


def pg(database, query):
    if database not in {"postgres", DATABASE}:
        raise ValueError("database outside isolated deployment")
    return command(["docker", "exec", "-i", PG, "psql", "-X", "-v", "ON_ERROR_STOP=1",
        "-U", "spirithub", "-d", database, "-A", "-t", "-q"], body=query.encode(), timeout=90)


def lake(query):
    env = environment(CH)
    return command(["docker", "exec", "-i", CH, "clickhouse-client",
        "--user", env.get("CLICKHOUSE_USER", "default"), "--password", env.get("CLICKHOUSE_PASSWORD", ""),
        "--multiquery"], body=query.encode(), timeout=60)


def literal(value):
    return "'"+str(value).replace("'", "''")+"'"


def secure_write(path, value):
    body = value if isinstance(value, bytes) else value.encode()
    temp = path.with_name(path.name+".new")
    with os.fdopen(os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as file:
        file.write(body)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temp, path)


def candidate():
    if not HERE.is_relative_to(Path("/opt/sting-aisoc-socai2/releases")) or not HERE.name.startswith("next-"):
        raise ValueError("candidate must be under the fixed next release directory")
    manifest = json.loads((HERE/"manifest.json").read_text())
    for name, info in manifest["files"].items():
        path = HERE/name
        if not path.resolve().is_relative_to(HERE) or path.is_symlink() or not path.is_file():
            raise ValueError("invalid candidate path")
        if hashlib.sha256(path.read_bytes()).hexdigest() != info["sha256"]:
            raise ValueError("candidate hash mismatch: " + name)
    image = inspect(manifest["base_image"])
    if image["Id"] != manifest["base_image_id"]:
        raise ValueError("base image changed")
    return manifest


def old_snapshot():
    return {name: {"id": item["Id"], "image": item["Image"], "started_at": item["State"]["StartedAt"]}
        for name in OLD for item in [inspect(name)]}


def protected_model_config():
    """Read-only fingerprints; never export original environment or secrets."""
    names = command(["docker", "ps", "--format", "{{.Names}}"] ).splitlines()
    gateways = [name for name in names if "litellm" in name.lower()]
    if not gateways:
        raise ValueError("existing LiteLLM gateway not found")
    result = {"original_api_env_sha256": hashlib.sha256((PRIVATE/"api.env").read_bytes()).hexdigest(),
        "original_containers": old_snapshot(), "gateways": {}}
    for name in gateways:
        item = inspect(name)
        config_files = {}
        for mount in item.get("Mounts", []):
            path = Path(mount["Source"])
            if path.is_file() and path.suffix in {".yaml", ".yml", ".json", ".env"}:
                config_files[mount["Destination"]] = hashlib.sha256(path.read_bytes()).hexdigest()
        result["gateways"][name] = {"id": item["Id"], "image": item["Image"],
            "started_at": item["State"]["StartedAt"], "config_files": config_files,
            "env_sha256": hashlib.sha256(json.dumps(sorted(item["Config"]["Env"])).encode()).hexdigest()}
    return result


def configure_deepseek():
    candidate()
    request = json.load(sys.stdin)
    token = request.get("token")
    if not isinstance(token, str) or not token or any(c.isspace() for c in token):
        raise ValueError("one credential value required")
    target, baseline = PRIVATE/"model.deepseek.env", PRIVATE/"before-deepseek.json"
    if target.exists() or baseline.exists():
        raise ValueError("DeepSeek profile already prepared; inspect before changing")
    before = protected_model_config()
    original = dict(line.split("=", 1) for line in (PRIVATE/"api.env").read_text().splitlines() if "=" in line)
    allowlist = json.loads(original.get("AISOC_AIRGAP_ALLOWLIST", "[]"))
    if not isinstance(allowlist, list) or not all(isinstance(v, str) for v in allowlist):
        raise ValueError("existing airgap allowlist has unsupported form")
    env = {"OPENAI_BASE_URL": "https://api.deepseek.com", "OPENAI_MODEL": "deepseek-flash",
        "OPENAI_API_KEY": token, "SOCAI2_MODEL_PROTOCOL": "deepseek_responses",
        "AISOC_AIRGAP_ALLOWLIST": json.dumps(sorted(set(allowlist + ["api.deepseek.com"])))}
    secure_write(baseline, json.dumps(before, indent=2)+"\n")
    secure_write(target, "\n".join(key+"="+value for key,value in sorted(env.items()))+"\n")
    if protected_model_config() != before:
        raise ValueError("original model configuration changed")
    print(json.dumps({"profile": "deepseek", "model": "deepseek-flash", "protocol": "responses",
        "existing_gateway_preserved": True, "original_api_env_preserved": True,
        "credential_file_mode": oct(target.stat().st_mode & 0o777), "model_calls": 0,
        "service_restart_performed": False, "credentials_exported": False}))


def bootstrap():
    candidate()
    print(json.dumps({"phase": "private_identity"}), flush=True)
    PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(PRIVATE, 0o700)
    baseline = PRIVATE/"original-containers.json"
    if baseline.exists():
        if json.loads(baseline.read_text()) != old_snapshot():
            raise ValueError("original container state changed; review before proceeding")
    else:
        secure_write(baseline, json.dumps(old_snapshot(), indent=2)+"\n")
    identity_path = PRIVATE/"identity.json"
    if not identity_path.exists():
        secure_write(identity_path, json.dumps({"tenant_id": TENANT, "user_id": USER,
            "database_password": secrets.token_hex(32), "lake_password": secrets.token_hex(32),
            "api_key": "aisoc_"+secrets.token_hex(32), "read_api_key": "aisoc_"+secrets.token_hex(32),
            "secret_key": secrets.token_hex(32), "jwt_secret": secrets.token_hex(32),
            "credential_key": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()}, indent=2)+"\n")
    identity = json.loads(identity_path.read_text())
    if (identity["tenant_id"], identity["user_id"]) != (TENANT, USER):
        raise ValueError("private identity differs")
    print(json.dumps({"phase": "new_postgres_space"}), flush=True)
    if pg("postgres", "SELECT count(*) FROM pg_roles WHERE rolname="+literal(ROLE)) == "0":
        pg("postgres", f"CREATE ROLE {ROLE} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION CONNECTION LIMIT 12 PASSWORD {literal(identity['database_password'])};")
    if pg("postgres", "SELECT count(*) FROM pg_database WHERE datname="+literal(DATABASE)) == "0":
        pg("postgres", f"CREATE DATABASE {DATABASE} OWNER spirithub;")
    if pg(DATABASE, "SELECT current_database();") != DATABASE:
        raise ValueError("database identity mismatch")
    print(json.dumps({"phase": "support_tables"}), flush=True)
    pg(DATABASE, (HERE/"support-schema.sql").read_text())
    print(json.dumps({"phase": "socai2_migrations"}), flush=True)
    if pg(DATABASE, "SELECT count(*) FROM public.aisoc_schema_migrations WHERE name='123_socai2_page_data_model.sql';") == "0":
        pg(DATABASE, (HERE/"migrations/123_socai2_page_data_model.sql").read_text())
    if pg(DATABASE, "SELECT count(*) FROM information_schema.columns WHERE table_schema='socai2' AND table_name='cases' AND column_name='source_namespace';") == "0":
        pg(DATABASE, (HERE/"migrations/124_socai2_case_source_binding.sql").read_text())
    if pg(DATABASE, "SELECT to_regprocedure('socai2.baseline_input_freshness(uuid,uuid)') IS NULL;") == "t":
        pg(DATABASE, (HERE/"migrations/125_socai2_baseline_input_freshness.sql").read_text())
    print(json.dumps({"phase": "synthetic_identity_and_grants"}), flush=True)
    pg(DATABASE, f"""BEGIN;
INSERT INTO public.tenants(id,name,slug,plan,is_active,settings,limits,created_at,updated_at)
VALUES('{TENANT}','SOCai2 next synthetic validation','socai2-next-validation','starter',true,'{{}}','{{}}',now(),now()) ON CONFLICT(id) DO NOTHING;
INSERT INTO public.users(id,tenant_id,email,username,hashed_password,role,is_active,is_verified,preferences,created_at,updated_at)
VALUES('{USER}','{TENANT}','next-validation@example.invalid','next-validation','!key-only-account','soc_admin',true,true,'{{}}',now(),now()) ON CONFLICT(id) DO NOTHING;
COMMIT;""")
    for label, scopes in [("api_key", ["alerts:read", "alerts:write", "cases:read", "cases:write"]), ("read_api_key", ["alerts:read", "cases:read"])]:
        key = identity[label]
        kid = str(uuid5(NAMESPACE_URL, "socai2-next-20261104:"+label))
        pg(DATABASE, f"""INSERT INTO public.api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,is_active,created_at)
VALUES('{kid}','{TENANT}','{USER}',{literal('synthetic '+label)},{literal(key[:12])},
{literal(hashlib.sha256(key.encode()).hexdigest())},{literal(json.dumps(scopes))}::jsonb,true,now()) ON CONFLICT(id) DO NOTHING;""")
    pg(DATABASE, f"""GRANT CONNECT ON DATABASE {DATABASE} TO {ROLE};
GRANT USAGE ON SCHEMA public,socai2 TO {ROLE};
GRANT SELECT ON ALL TABLES IN SCHEMA public TO {ROLE};
GRANT UPDATE(last_used_at) ON public.api_keys TO {ROLE};
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA socai2 TO {ROLE};
GRANT EXECUTE ON FUNCTION socai2.auto_adopt_baseline_result(uuid,uuid) TO {ROLE};""")
    print(json.dumps({"phase": "new_lake_space"}), flush=True)
    lake((HERE/"lake-schema.sql").read_text())
    lake(f"CREATE USER IF NOT EXISTS {LAKE_USER} IDENTIFIED WITH sha256_password BY {literal(identity['lake_password'])};\nGRANT SELECT ON {LAKE}.* TO {LAKE_USER};")
    print(json.dumps({"phase": "isolated_runtime_environment"}), flush=True)
    original = environment("socai2-investigation-api")
    allowed = {"OPENAI_MODEL", "OPENAI_BASE_URL", "OPENAI_API_KEY", "LLM_MODEL", "LLM_BASE_URL", "LLM_API_KEY",
        "LLM_GATEWAY_URL", "LLM_GATEWAY_API_KEY", "LITELLM_MASTER_KEY", "AISOC_LLM_MODEL", "AISOC_AIRGAPPED",
        "AISOC_AIRGAP_ALLOWLIST", "PGSSLROOTCERT", "PGSSLMODE", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"}
    env = {key: value for key, value in original.items() if key in allowed}
    dsn = urlsplit(original["DATABASE_URL"])
    host = dsn.hostname
    if not host or ":" in host:
        raise ValueError("unexpected PG endpoint format")
    authority = ROLE+":"+quote(identity["database_password"], safe="")+"@"+host+":"+str(dsn.port or 5432)
    env["DATABASE_URL"] = urlunsplit((dsn.scheme, authority, "/"+DATABASE, dsn.query, ""))
    redis = urlsplit(original["REDIS_URL"])
    env["REDIS_URL"] = urlunsplit((redis.scheme, redis.netloc, "/13", redis.query, ""))
    env.update({"ENVIRONMENT": "production", "DEBUG": "false", "AISOC_DEV_AUTH_BYPASS": "false",
        "SECRET_KEY": identity["secret_key"], "JWT_SECRET": identity["jwt_secret"],
        "AISOC_CREDENTIAL_KEY": identity["credential_key"], "REALTIME_INTERNAL_TOKEN": secrets.token_hex(32),
        "METRICS_TOKEN": secrets.token_hex(32),
        "AISOC_REALTIME_JWT_SECRET": secrets.token_hex(32), "SOCAI2_SERVICE_DATABASE_NAME": DATABASE,
        "SOCAI2_CASE_API_ENABLED": "true", "SOCAI2_ANALYSIS_READ_ENABLED": "true", "SOCAI2_PAGE_READ_ENABLED": "true",
        "SOCAI2_STAGE_EXECUTION_ENABLED": "true", "SOCAI2_SOURCE_UEBA_ENABLED": "true",
        "SOCAI2_SOURCE_KNOWLEDGE_ENABLED": "true", "SOCAI2_SOURCE_GRAPH_ENABLED": "false",
        "SOCAI2_SOURCE_PRODUCT_HOST_ENABLED": "false", "SOCAI2_LAKE_DATABASE": LAKE,
        "CLICKHOUSE_DATABASE": LAKE, "CLICKHOUSE_USER": LAKE_USER, "CLICKHOUSE_PASSWORD": identity["lake_password"],
        "CLICKHOUSE_HOST": original["CLICKHOUSE_HOST"], "CLICKHOUSE_PORT": original.get("CLICKHOUSE_PORT", "9000"),
        "KAFKA_BOOTSTRAP_SERVERS": "127.0.0.1:1", "KAFKA_BROKERS": "127.0.0.1:1",
        "DATABASE_POOL_SIZE": "4", "DATABASE_MAX_OVERFLOW": "2"})
    if any("\n" in value or "\r" in value for value in env.values()):
        raise ValueError("multiline environment value refused")
    secure_write(PRIVATE/"api.env", "\n".join(key+"="+value for key,value in sorted(env.items()))+"\n")
    print(json.dumps({"bootstrapped": True, "database": DATABASE, "tenant_id": TENANT, "user_id": USER,
        "public_tables": int(pg(DATABASE,"SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")),
        "socai2_columns": int(pg(DATABASE,"SELECT count(*) FROM information_schema.columns WHERE table_schema='socai2';")),
        "lake_database": LAKE, "redis_database": 13, "credentials_exported": False,
        "original_containers_unchanged": old_snapshot() == json.loads(baseline.read_text())}))


def verify():
    manifest = candidate()
    result = json.loads(urllib.request.urlopen("http://127.0.0.1:18020/readyz", timeout=5).read())
    original = old_snapshot() == json.loads((PRIVATE/"original-containers.json").read_text())
    if not original:
        raise ValueError("original container state changed")
    current = inspect(NEW)
    if current["Config"]["Image"] != manifest["image"]:
        raise ValueError("unexpected new image")
    openapi = json.loads(urllib.request.urlopen("http://127.0.0.1:18020/openapi.json", timeout=5).read())
    paths = openapi["paths"]
    if any(p in paths for p in ["/api/v1/alerts", "/api/v1/cases", "/api/v1/lake/sql"]):
        raise ValueError("legacy business routes present")
    check = """import hashlib,json,sys,pathlib
expected=json.load(sys.stdin)
root=pathlib.Path('/app')
actual={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
for p in (root/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
assert actual==expected,'running application differs from candidate'
print(len(actual))
"""
    expected = {name: item["sha256"] for name,item in manifest["files"].items() if name.startswith("app/")}
    checked = int(command(["docker", "exec", "-i", NEW, "python", "-c", check], body=json.dumps(expected).encode()))
    model_config_preserved = None
    model_environment = environment(NEW)
    expected_profile = "standard" if model_environment.get("SOCAI2_MODEL_PROTOCOL") == "deepseek_responses" else "vllm_grammar_v1"
    if model_environment.get("SOCAI2_MODEL_SCHEMA_PROFILE") != expected_profile:
        raise ValueError("independent model schema profile mismatch")
    if model_environment.get("SOCAI2_MODEL_PROTOCOL") == "deepseek_responses":
        model_config_preserved = protected_model_config() == json.loads((PRIVATE/"before-deepseek.json").read_text())
        if not model_config_preserved:
            raise ValueError("original model configuration changed")
        if model_environment.get("OPENAI_BASE_URL") != "https://api.deepseek.com" or model_environment.get("OPENAI_MODEL") != "deepseek-flash":
            raise ValueError("unexpected independent model configuration")
    print(json.dumps({"health": result, "container": NEW, "image_id": current["Image"],
        "port": 18020, "api_paths": len(paths), "application_files_hash_verified": checked,
        "original_containers_unchanged": original,
        "original_model_configuration_unchanged": model_config_preserved,
        "model_protocol": model_environment.get("SOCAI2_MODEL_PROTOCOL", "chat_completions"),
        "schema_profile": model_environment["SOCAI2_MODEL_SCHEMA_PROFILE"],
        "model": model_environment.get("OPENAI_MODEL"),
        "manifest_sha256": hashlib.sha256((HERE/"manifest.json").read_bytes()).hexdigest()}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["inspect", "bootstrap", "build", "start", "verify", "configure-deepseek"], default="inspect", nargs="?")
    parser.add_argument("--model-profile", choices=["original", "deepseek"], default="original")
    args = parser.parse_args()
    action = args.action
    if action == "inspect":
        print(json.dumps({"candidate": candidate()["image"], "original_containers": old_snapshot(), "target_database": DATABASE}))
    elif action == "bootstrap":
        bootstrap()
    elif action == "configure-deepseek":
        configure_deepseek()
    elif action == "build":
        manifest = candidate()
        command(["docker", "build", "--network=none", "-t", manifest["image"], str(HERE)], timeout=240)
        print(json.dumps({"built_image": manifest["image"], "image_id": inspect(manifest["image"])["Id"]}))
    elif action == "start":
        candidate()
        compose = ["docker", "compose", "-f", str(HERE/"compose.next-service.yml")]
        if args.model_profile == "deepseek":
            if not (PRIVATE/"model.deepseek.env").exists():
                raise ValueError("independent model profile missing")
            compose += ["-f", str(HERE/"compose.next-deepseek.yml")]
        command(compose + ["up", "-d", "--no-deps", "api"], timeout=90)
        for attempt in range(20):
            try:
                urllib.request.urlopen("http://127.0.0.1:18020/readyz", timeout=2)
                break
            except OSError:
                time.sleep(1)
        verify()
    else:
        verify()


if __name__ == "__main__":
    main()
