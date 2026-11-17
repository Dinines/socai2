"""Prepare this one local two-part batch; no business material is published here."""
import argparse
import asyncio
import json
import os
import re
import secrets
import subprocess
import sys
import tomllib
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/testdata"))
from acceptance_contract import Profile, Recipe
from acceptance_materials import control, convert_package, read_json
from acceptance_runtime_contract import Execution
from acceptance_session import prepare_execution
from alert_scenarios import json_bytes


def write(path, value, private=False):
    with path.open("xb") as stream:
        stream.write(value.encode() if isinstance(value, str) else json_bytes(value))
    if private:
        path.chmod(0o600)


async def main(config_path, resume_after_credentials=False):
    config = read_json(config_path)
    private, out = config_path.parent, Path(__file__).parent
    old = Path(config["previous_local_configuration"])
    db = read_json(private / "database.json")
    tenant, actor = config["tenant_id"], config["actor_id"]
    role = config["runtime_role"]
    assert re.fullmatch("[a-z_][a-z0-9_]*", role)
    runtime_password = secrets.token_hex(24)
    install = tomllib.loads((private / "install.toml").read_text())
    command = install["psql_argv"] + ["-U", install["admin_role"], "-v", "ON_ERROR_STOP=1", "-d", db["processing_database"]]
    def sql(body):
        r = subprocess.run(command, input=body, text=True, capture_output=True, timeout=install["timeout_seconds"])
        if r.returncode:
            (private / "setup-error.log").write_text(r.stderr)
            raise RuntimeError("local_setup_sql_failed_see_private_log")
        return r.stdout
    if not resume_after_credentials:
        sql(f"CREATE ROLE {role} LOGIN PASSWORD '{runtime_password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; "
        f"GRANT CONNECT ON DATABASE {db['processing_database']} TO {role}; GRANT USAGE ON SCHEMA socai2,public TO {role}; "
        f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA socai2 TO {role}; "
        f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA socai2 TO {role}; GRANT SELECT ON ALL TABLES IN SCHEMA public TO {role};")
    from sqlalchemy.engine import URL
    url = URL.create("postgresql+asyncpg", username=role, password=runtime_password,
                     host=db["host"], port=db["port"], database=db["processing_database"])
    if resume_after_credentials:
        from sqlalchemy.engine import make_url
        dsn = (private / "database-url").read_text().strip()
        existing = make_url(dsn)
        assert (existing.username, existing.database) == (role, db["processing_database"])
    else:
        dsn = url.render_as_string(hide_password=False)
        write(private / "database-url", dsn + "\n", True)
        write(private / "redis-url", f"redis://{config['bind']}:{config['redis_port']}/0\n", True)
    profile = read_json(ROOT / "tools/testdata/acceptance-examples/profile.json")
    profile.update(profile_id="local-append", environment_label="本机独立追加验证", tenant_id=tenant,
                   connection_files={name: str(private / (name + ".json")) for name in ("http", "kafka", "postgres", "lake")})
    profile["timing"].update(send_interval_seconds=0.25, poll_interval_seconds=config["poll_interval_seconds"],
                             part_timeout_seconds=config["part_timeout_seconds"])
    selected_profile = control(Profile, profile, "profile")
    recipe = control(Recipe, read_json(ROOT / "tools/testdata/acceptance-examples/streaming-conversion.json"), "recipe")
    materials = out / "materials"
    convert_package(Path(config["material_source"]), recipe, selected_profile, materials)
    for folder, keep in ((materials / "part1/alerts", {"001.json"}),
                         (materials / "part1/context", {"001.json", "002.json"})):
        for p in folder.glob("*.json"):
            if p.name not in keep:
                p.unlink()  # Only this new, unsent conversion is reduced to the explicit small plan.
    initial = read_json(materials / "part1/alerts/001.json")
    connector = initial["connector_id"]
    source_name = initial["connector_type"]
    assert re.fullmatch("[a-z0-9_-]+", source_name)
    sql(f"INSERT INTO public.tenants(id,name,slug,plan,is_active,settings,limits,created_at,updated_at) "
        f"VALUES('{tenant}','Operations','operations','enterprise',true,'{{}}','{{}}',now(),now()); "
        f"INSERT INTO public.users(id,tenant_id,email,username,hashed_password,role,is_active,is_verified,preferences,created_at,updated_at) "
        f"VALUES('{actor}','{tenant}','analyst@example.invalid','Operations analyst','!','soc_analyst',true,false,'{{}}',now(),now()); "
        f"INSERT INTO public.connectors(id,tenant_id,name,connector_type,category,is_enabled,auth_config,connector_config,health_status,"
        f"events_ingested,events_dropped,error_count,oauth_provisioned,oauth_refresh_failures,tags,created_at,updated_at) "
        f"VALUES('{connector}','{tenant}','{source_name}','{source_name}','telemetry',true,'{{}}','{{}}','unknown',0,0,0,false,0,'[]',now(),now());")
    write(private / "profile.json", profile)
    prepared = out / "prepared"
    session = prepare_execution(materials, selected_profile, Execution(schema_version="socai2.acceptance-execution.v1",
        execution_id=config["execution_id"], time_policy="preserve"), prepared)
    write(out / "material-plan.json", session["plan"])
    lifecycle = ROOT / "deploy/local-investigation/analysis-tasks.json"
    allocation = ROOT / "deploy/local-investigation/case-allocation.json"
    policy_dir = private / "analysis"
    policy_dir.mkdir()
    original_policy = (old / "analysis/investigation-policy.toml").read_text()
    token_endpoint = tomllib.loads(original_policy)["model"]["tokenizer"]["endpoint"]
    write(policy_dir / "investigation-policy.toml", original_policy.replace(token_endpoint,
          f"http://{config['bind']}:{config['tokenizer_port']}/tokenize"))
    policy = policy_dir / "investigation-policy.toml"
    model = read_json(old / "model-environment.json")
    parsed = urlsplit(model["OPENAI_BASE_URL"])
    model["OPENAI_BASE_URL"] = urlunsplit((parsed.scheme, f"{config['bind']}:{config['model_gateway_port']}", parsed.path, "", ""))
    write(private / "model-environment.json", model, True)
    runtime = read_json(old / "environment.json")
    runtime.update(model)
    runtime.update(DATABASE_URL=dsn + "?sslmode=" + config["database_ssl"], SOCAI2_CASE_DATABASE_URL=dsn + "?sslmode=" + config["database_ssl"],
        SOCAI2_SERVICE_DATABASE_NAME=db["processing_database"], SOCAI2_CASE_API_ENABLED="true", SOCAI2_PAGE_READ_ENABLED="true",
        SOCAI2_HTTP_CONTEXT_FILE=str(private / "http-context.json"), SOCAI2_INVESTIGATION_POLICY=str(policy),
        SOCAI2_ANALYSIS_TASKS_CONFIG_FILE=str(lifecycle), SOCAI2_CASE_ALLOCATION_CONFIG_FILE=str(allocation),
        SOCAI2_RUN_RECORDS_CONFIG_FILE=str(old / "run-records.json"), SOCAI2_EXPORT_CONFIG_FILE=str(ROOT / "services/api/app/socai2/list_export.json"),
        SOCAI2_SOURCE_UEBA_ENABLED="false", SOCAI2_SOURCE_KNOWLEDGE_ENABLED="false", SOCAI2_SOURCE_GRAPH_ENABLED="false",
        AISOC_DISABLE_CLICKHOUSE="false", CLICKHOUSE_HOST=config["bind"], CLICKHOUSE_PORT=str(config["lake_port"]),
        CLICKHOUSE_DATABASE=config["lake_database"], SOCAI2_LAKE_DATABASE=config["lake_database"], CLICKHOUSE_USER="local_admin",
        CLICKHOUSE_PASSWORD=(private / "lake-password").read_text().strip(),
        PYTHONPATH=str(ROOT / "services/api"), PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1")
    runtime.pop("SOCAI2_INVESTIGATION_POLICY_SHA256", None)
    write(private / "api-environment.json", runtime, True)
    write(private / "http-context.json", {"tenant_id":tenant,"actor_id":actor,"actor_name":"Operations analyst"})
    # Normal core executors and one configured queue owner; no result or model substitutes.
    old_validation = read_json(old / "verification-03.json")
    executor = {k:old_validation[k] for k in ("case","incident")}
    executor["investigation_policy_file"] = str(policy)
    write(private / "executors.json", executor)
    dispatch = dict(old_validation["dispatch"])
    dispatch.update(namespace=config["execution_id"], poll_interval_seconds=config["poll_interval_seconds"],
        receipt_directory=str(private / "completion-receipts"),lock_file=str(private / "dispatch.lock"))
    write(private / "dispatcher.json", {"enabled":True,"tenant_id":tenant,"database_url_file":str(private / "database-url"),
        "database_connect_args":{"ssl":False if config["database_ssl"] == "disable" else config["database_ssl"],"timeout":10,"command_timeout":60},"database_pool_size":5,
        "redis_url_file":str(private / "redis-url"),"redis_socket_timeout_seconds":5,"redis_connect_timeout_seconds":5,
        "lifecycle_policy_file":str(lifecycle),"executor_factory":"app.socai2.analysis_case_executor:executors",
        "executor_config_file":str(private / "executors.json"),"dispatch":dispatch})
    prefix = config["topic_prefix"]
    kafka_address = f"{config['bind']}:{config['kafka_port']}"
    write(private / "producer.env", f"KAFKA_BOOTSTRAP_SERVERS={kafka_address}\nKAFKA_SECURITY_PROTOCOL=PLAINTEXT\n")
    write(private / "http.json", {"base_url":f"http://{config['bind']}:{config['http_port']}","tenant_id":tenant,
        "timeout_seconds":config["http_timeout_seconds"],"page_size":5,"fusion_ready_url":f"http://{config['bind']}:{config['fusion_port']}/readyz"})
    write(private / "kafka.json", {"producer_env_file":str(private / "producer.env"),"expected_bootstrap_servers":kafka_address,
        "security_protocol":"PLAINTEXT","topics":{"alert":prefix+".alerts.raw","context":prefix+".raw_events"},
        "timeout_seconds":30,"request_timeout_ms":30000})
    write(private / "postgres.json", {"database_url_file":str(private / "database-url"),"expected_database":db["processing_database"],
        "expected_user":role,"schema_name":"socai2","ssl":config["database_ssl"],"connect_timeout_seconds":10,"query_timeout_seconds":60})
    lake = {"host":config["bind"],"port":config["lake_port"],"database":config["lake_database"],"table":"raw_events",
        "user":"local_admin","password_file":str(private / "lake-password"),"secure":False,"verify":False,"ca_certs":None,
        "connect_timeout_seconds":10,"read_timeout_seconds":30,"query_timeout_seconds":30}
    write(private / "lake.json",lake)
    from clickhouse_driver import Client
    client=Client(host=lake["host"],port=lake["port"],user=lake["user"],password=runtime["CLICKHOUSE_PASSWORD"])
    source=(ROOT / "services/api/clickhouse/001_init.sql").read_text()
    start=source.index("CREATE TABLE IF NOT EXISTS aisoc.raw_events");end=source.index("SETTINGS index_granularity = 8192;",start)+len("SETTINGS index_granularity = 8192;")
    ddl=source[start:end].replace("aisoc.raw_events",lake["database"]+".raw_events")
    client.execute("CREATE DATABASE "+lake["database"]);client.execute(ddl);client.disconnect()
    from aiokafka.admin import AIOKafkaAdminClient,NewTopic
    admin=AIOKafkaAdminClient(bootstrap_servers=kafka_address)
    await admin.start()
    try:
        await admin.create_topics([NewTopic(prefix+suffix,1,1) for suffix in (".alerts.raw",".alerts.fused",".raw_events")])
    finally:
        await admin.close()
    fusion={"DATABASE_URL":dsn+"?sslmode="+config["database_ssl"],"AISOC_ALERT_STORE_SCHEMA":"socai2","AISOC_ALERT_SINK_ENABLED":"true",
        "SOCAI2_ANALYSIS_TASKS_CONFIG_FILE":str(lifecycle),"REDIS_URL":(private / "redis-url").read_text().strip(),
        "KAFKA_BOOTSTRAP_SERVERS":kafka_address,"KAFKA_SECURITY_PROTOCOL":"PLAINTEXT","KAFKA_CONSUMER_GROUP":prefix+".fusion",
        "KAFKA_TOPIC_ALERTS_RAW":prefix+".alerts.raw","KAFKA_TOPIC_ALERTS_FUSED":prefix+".alerts.fused","KAFKA_TOPIC_RAW_EVENTS":prefix+".raw_events",
        "AISOC_EVENT_PROMOTION_ENABLED":"false","AISOC_DETECTION_ENGINE_ENABLED":"false","AISOC_WINDOWED_DETECTION_ENABLED":"false",
        "AISOC_UEBA_FUSION_ENABLED":"false","AISOC_ATTACK_CHAIN_GROUPING_ENABLED":"false","AISOC_FUSE_ENRICHMENT":"false",
        "AISOC_LAKE_WRITER_ENABLED":"true","AISOC_LAKE_BATCH_SIZE":"1","AISOC_LAKE_BATCH_MAX_AGE_SECONDS":"1",
        "CLICKHOUSE_HOST":lake["host"],"CLICKHOUSE_PORT":str(lake["port"]),"CLICKHOUSE_DATABASE":lake["database"],
        "CLICKHOUSE_USER":lake["user"],"CLICKHOUSE_PASSWORD":runtime["CLICKHOUSE_PASSWORD"],
        "PYTHONPATH":os.pathsep.join([str(ROOT / "services/fusion"),str(out)]),"PYTHONDONTWRITEBYTECODE":"1","PYTHONUNBUFFERED":"1"}
    write(private / "fusion-environment.json",fusion,True)
    write(out / "setup-receipt.json",{"status":"passed","execution_id":config["execution_id"],"database":db["processing_database"],
        "parts":[{"id":p["id"],"counts":p["counts"]} for p in session["plan"]["parts"]],"case_scopes":[c.scope for c in recipe.scenario.cases],
        "historical_business_rows_copied":0,"new_business_messages":0,"model_calls":0,"dispatch_max_running_tasks":dispatch["max_running_tasks"]})
    print("New local batch prepared: 1+1 alerts, two Case scopes; no business messages or model calls")


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--config",type=Path,required=True)
    parser.add_argument("--resume-after-credentials", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.config.resolve(), args.resume_after_credentials))
