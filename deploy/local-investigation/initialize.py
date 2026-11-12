"""Initialize only the dedicated loopback services; no old data or model calls."""
import argparse
import ast
import asyncio
import hashlib
import json
import re
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from config import (
    API_ROLE,
    CH_READER,
    CH_WRITER,
    DATABASE,
    FUSION_ROLE,
    LAKE,
    PORTS,
    ROOT,
    STATE,
    TENANT,
    TOPIC,
    USER,
    read_private,
)
from schema import CONTEXT_TABLES, MIGRATIONS

MARKER = "socai2-local-investigation:20261105"


def safe_error(exc, values):
    # Prefer the server's primary message, omitting SQL/detail/parameter dumps.
    message = str(getattr(exc, "message", None) or str(exc))
    for value in sorted((v for v in values.values() if v), key=len, reverse=True):
        message = message.replace(value, "[redacted]")
    message = re.sub(r"(?:postgres(?:ql)?(?:\+\w+)?|redis|https?)://\S+", "[redacted-url]", message)
    message = re.sub(r"\b[a-fA-F0-9]{32,}\b", "[redacted-value]", message)
    message = re.sub(r"aisoc_[A-Za-z0-9_-]+", "[redacted-key]", message)
    return message.split("Stack trace:", 1)[0][:800]


def literal(value):
    return "'" + value.replace("'", "''") + "'"


def schemas():
    manifest = json.loads((STATE / "manifest.json").read_text())
    assert manifest["database"] == DATABASE and manifest["lake_database"] == LAKE
    result = {}
    for name, digest in manifest["schema_files"].items():
        assert "/" not in name and name.endswith(".sql")
        body = (STATE / "schema" / name).read_text()
        assert hashlib.sha256(body.encode()).hexdigest() == digest, "prepared schema changed"
        result[name] = body
    return result


async def pg_connect(values, *, database=DATABASE, role="postgres", password_key="PG_ADMIN_PASSWORD"):
    import asyncpg
    return await asyncpg.connect(host="127.0.0.1", port=PORTS["postgres"], database=database,
        user=role, password=values[password_key], ssl=False, timeout=10, command_timeout=90)


async def postgres(values, sql):
    conn = await pg_connect(values, database="postgres")
    try:
        exists = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=$1)", DATABASE)
        if not exists:
            await conn.execute(f"CREATE DATABASE {DATABASE}")
            await conn.execute(f"COMMENT ON DATABASE {DATABASE} IS {literal(MARKER)}")
        assert await conn.fetchval("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=$1", DATABASE) == MARKER, "unowned database"
        for role, password in ((API_ROLE, values["API_DB_PASSWORD"]), (FUSION_ROLE, values["FUSION_DB_PASSWORD"])):
            row = await conn.fetchrow("SELECT oid FROM pg_roles WHERE rolname=$1", role)
            if row is None:
                await conn.execute(f"CREATE ROLE {role} LOGIN PASSWORD {literal(password)} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS")
                await conn.execute(f"COMMENT ON ROLE {role} IS {literal(MARKER)}")
            assert await conn.fetchval("SELECT shobj_description(oid,'pg_authid') FROM pg_roles WHERE rolname=$1", role) == MARKER, "unowned runtime role"
    finally:
        await conn.close()
    conn = await pg_connect(values)
    applied = []
    try:
        assert await conn.fetchval("SELECT current_database()") == DATABASE
        await conn.execute("SELECT pg_advisory_lock(20261105,18020)")
        await conn.execute(sql["support.sql"])
        for name in MIGRATIONS:
            if not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM public.aisoc_schema_migrations WHERE name=$1)", name):
                await conn.execute(sql[name])
                await conn.execute("INSERT INTO public.aisoc_schema_migrations(name) VALUES($1) ON CONFLICT DO NOTHING", name)
                applied.append(name)
        await conn.execute(sql["grants.sql"])
        async with conn.transaction():
            await conn.execute("""INSERT INTO public.tenants
                (id,name,slug,plan,is_active,settings,limits,created_at,updated_at)
                VALUES($1,'Local investigation','socai2-local-20261105','enterprise',true,'{}','{}',now(),now())
                ON CONFLICT(id) DO NOTHING""", UUID(TENANT))
            await conn.execute("""INSERT INTO public.users
                (id,tenant_id,email,username,hashed_password,role,is_active,is_verified,preferences,created_at,updated_at)
                VALUES($1,$2,'investigator@local.invalid','Local investigator','!api-key-only','soc_admin',true,true,'{}',now(),now())
                ON CONFLICT(id) DO NOTHING""", UUID(USER), UUID(TENANT))
            for key_name, scopes in (("API_KEY", ["alerts:read", "alerts:write", "cases:read", "cases:write"]),
                                     ("READ_API_KEY", ["alerts:read", "cases:read"])):
                key = values[key_name]
                key_id = uuid5(NAMESPACE_URL, MARKER + ":" + key_name)
                digest = hashlib.sha256(key.encode()).hexdigest()
                await conn.execute("""INSERT INTO public.api_keys
                    (id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,is_active,created_at)
                    VALUES($1,$2,$3,$4,$5,$6,$7::jsonb,true,now()) ON CONFLICT(id) DO NOTHING""",
                    key_id, UUID(TENANT), UUID(USER), "Local " + key_name, key[:12], digest, json.dumps(scopes))
                assert await conn.fetchval("SELECT hashed_key FROM public.api_keys WHERE id=$1", key_id) == digest, "existing local key differs"
        verified = await verify_postgres(conn)
        return {"applied_migrations": applied, **verified}
    finally:
        await conn.close()


async def verify_postgres(conn):
    tables = await conn.fetch("""SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity,
        pg_get_userbyid(c.relowner) AS owner FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='socai2' AND c.relkind='r'""")
    columns = await conn.fetchval("SELECT count(*) FROM information_schema.columns WHERE table_schema='socai2'")
    cleaned = await conn.fetchval("SELECT EXISTS(SELECT FROM public.aisoc_schema_migrations WHERE name='127_socai2_remove_unused_graph_table.sql')")
    assert (len(tables), columns) == ((28, 450) if cleaned else (29, 462)), "unexpected investigation schema"
    assert (await conn.fetchval("SELECT to_regclass('socai2.graph_explorations')") is None) == cleaned
    assert all(t["relrowsecurity"] and t["relforcerowsecurity"] for t in tables)
    assert all(t["owner"] not in {API_ROLE, FUSION_ROLE} for t in tables)
    for role in (API_ROLE, FUSION_ROLE):
        row = await conn.fetchrow("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,rolreplication FROM pg_roles WHERE rolname=$1", role)
        assert row is not None and not any(row.values()), "runtime role is privileged"
        assert not await conn.fetchval("SELECT has_schema_privilege($1,'socai2','CREATE')", role)
    assert not await conn.fetchval("SELECT has_table_privilege($1,'socai2.cases','INSERT')", FUSION_ROLE)
    assert not await conn.fetchval("SELECT has_column_privilege($1,'socai2.alerts','title','UPDATE')", FUSION_ROLE)
    assert await conn.fetchval("SELECT has_column_privilege($1,'socai2.alerts','latest_material_id','UPDATE')", FUSION_ROLE)
    assert not await conn.fetchval("SELECT has_table_privilege($1,'socai2.artifacts','UPDATE')", API_ROLE)
    assert not await conn.fetchval("SELECT has_table_privilege($1,'public.users','UPDATE')", API_ROLE)
    assert await conn.fetchval("SELECT has_column_privilege($1,'public.api_keys','last_used_at','UPDATE')", API_ROLE)
    context = await conn.fetchval("""SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relname=ANY($1::text[]) AND c.relrowsecurity AND c.relforcerowsecurity""", sorted(CONTEXT_TABLES))
    assert context == len(CONTEXT_TABLES)
    # Execute the actual policy under the API role. Both probe rows roll back.
    transaction = conn.transaction()
    await transaction.start()
    try:
        ids = [uuid4(), uuid4()]
        await conn.executemany("INSERT INTO public.aisoc_kb_documents(id,tenant_id,title,content) VALUES($1,$2,'RLS probe','probe')",
                              [(ids[0], UUID(TENANT)), (ids[1], uuid4())])
        await conn.execute(f"SET LOCAL ROLE {API_ROLE}")
        await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", TENANT)
        assert await conn.fetchval("SELECT count(*) FROM public.aisoc_kb_documents WHERE id=ANY($1::uuid[])", ids) == 1
        await conn.execute("SELECT set_config('app.current_tenant_id','',true)")
        assert await conn.fetchval("SELECT count(*) FROM public.aisoc_kb_documents WHERE id=ANY($1::uuid[])", ids) == 0
    finally:
        await transaction.rollback()
    counts = {name: await conn.fetchval(f"SELECT count(*) FROM socai2.{name}")
              for name in ("alerts", "incidents", "cases", "runs", "artifacts", "tasks")}
    return {"tables": len(tables), "columns": columns, "forced_rls_tables": len(tables),
            "context_forced_rls_tables": context, "cross_tenant_probe": "passed_and_rolled_back",
            "runtime_roles_restricted": True, "business_counts": counts}


def clickhouse(values, sql):
    from clickhouse_driver import Client
    admin = Client("127.0.0.1", port=PORTS["clickhouse_native"], user="local_admin",
        password=values["CH_ADMIN_PASSWORD"], connect_timeout=10, send_receive_timeout=30)
    try:
        # Only the first semicolon separates statements. The table's source
        # comments contain semicolons and must remain part of the intact DDL.
        database_ddl, separator, table_ddl = sql["lake.sql"].partition(";")
        assert separator and database_ddl == "CREATE DATABASE IF NOT EXISTS " + LAKE
        assert table_ddl.lstrip().startswith("CREATE TABLE IF NOT EXISTS " + LAKE + ".raw_events")
        admin.execute(database_ddl)
        admin.execute(table_ddl.strip().removesuffix(";"))
        for role, key, privilege in ((CH_READER, "CH_READER_PASSWORD", "SELECT"),
                                     (CH_WRITER, "CH_WRITER_PASSWORD", "INSERT")):
            admin.execute(f"CREATE USER IF NOT EXISTS {role} IDENTIFIED WITH sha256_password BY {literal(values[key])}")
            admin.execute(f"GRANT {privilege} ON {LAKE}.raw_events TO {role}")
        tree = ast.parse((ROOT / "services/fusion/app/services/lake_writer.py").read_text())
        expected = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == "_COLUMNS" for t in node.targets))
        actual = {r[0] for r in admin.execute(f"DESCRIBE TABLE {LAKE}.raw_events")}
        assert len(expected) == 47 and set(expected) <= actual, "lake writer/schema mismatch"
        grants = {}
        for role, privilege in ((CH_READER, "SELECT"), (CH_WRITER, "INSERT")):
            rows = [r[0] for r in admin.execute(f"SHOW GRANTS FOR {role}")]
            assert rows == [f"GRANT {privilege} ON {LAKE}.raw_events TO {role}"], "unexpected lake privileges"
            grants[role] = {"privilege": privilege, "table": LAKE + ".raw_events"}
        count = admin.execute(f"SELECT count() FROM {LAKE}.raw_events")[0][0]
        return {"database": LAKE, "writer_columns_verified": len(expected), "table_columns": len(actual),
                "runtime_grants": grants, "event_rows": count}
    finally:
        admin.disconnect()


async def kafka():
    from aiokafka.admin import AIOKafkaAdminClient, NewTopic
    client = AIOKafkaAdminClient(bootstrap_servers="127.0.0.1:19092", client_id="socai2-local-initialize")
    names = [TOPIC + suffix for suffix in (".alerts.raw", ".raw_events", ".alerts.fused")]
    await client.start()
    try:
        existing = set(await client.list_topics())
        new = [NewTopic(name, num_partitions=1, replication_factor=1) for name in names if name not in existing]
        if new:
            await client.create_topics(new)
        metadata = await client.describe_topics(names)
        assert len(metadata) == 3 and all(t["error_code"] == 0 and len(t["partitions"]) == 1
            and len(t["partitions"][0]["replicas"]) == 1 for t in metadata)
        return {"topics": names, "partitions_per_topic": 1, "replication_factor": 1, "messages_produced": 0}
    finally:
        await client.close()


async def run(phase):
    values, sql = read_private(), schemas()
    results = {}
    for name in ("postgres", "clickhouse", "kafka"):
        if phase not in {"all", name}:
            continue
        try:
            if name == "postgres":
                results[name] = await postgres(values, sql)
            elif name == "clickhouse":
                results[name] = await asyncio.to_thread(clickhouse, values, sql)
            else:
                results[name] = await kafka()
        except Exception as exc:  # noqa: BLE001 -- persist a sanitized initialization receipt
            return {"status": "failed", "failed_phase": name, "results": results,
                    "error_type": type(exc).__name__, "message": safe_error(exc, values)}
    return {"status": "passed", "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("all", "postgres", "clickhouse", "kafka"), default="all")
    args = parser.parse_args()
    receipt = {"phase": args.phase, "started_at": datetime.now(UTC).isoformat(), "model_calls": 0, "old_data_copied": False}
    try:
        receipt.update(asyncio.run(run(args.phase)))
    except Exception as exc:  # noqa: BLE001 -- never expose private configuration in a traceback
        # Never print a DSN, password, raw server error or a credential fingerprint.
        receipt.update(status="failed", failed_phase="configuration", error_type=type(exc).__name__)
    receipt["ended_at"] = datetime.now(UTC).isoformat()
    directory = STATE / "evidence"
    directory.mkdir(exist_ok=True)
    path = directory / (datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + "-initialize-" + args.phase + ".json")
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "receipt": str(path), "model_calls": 0,
                      **({"error_type": receipt["error_type"], "failed_phase": receipt["failed_phase"],
                          "message": receipt.get("message", "private configuration or schema validation failed")}
                         if "error_type" in receipt else {})}))
    raise SystemExit(0 if receipt["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
