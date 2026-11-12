"""Read committed Case records for the investigation workbench."""
import asyncio
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from urllib.parse import urlsplit
from uuid import UUID

import asyncpg
from capture_processing_case import RLS, SCOPE, TABLES, scoped_table_query

HANDOFF_TENANT = UUID("6aff0ef7-c670-5a84-a2ee-83d73e25b964")
DEFAULT_PRODUCTION_TENANT = UUID("00000000-0000-0000-0000-000000000001")
PAGE_SIZE = 5
ABSENT = "Case absent or not visible to this tenant"

LIST_QUERY = """
WITH case_updates AS (
  SELECT c.id AS case_id, c.title, greatest(c.business_updated_at,
    (SELECT max(greatest(r.requested_at,r.started_at,r.ended_at))
       FROM socai2.runs r WHERE r.tenant_id=c.tenant_id AND r.case_id=c.id),
    (SELECT max(greatest(s.started_at,s.ended_at)) FROM socai2.run_steps s JOIN socai2.runs r
       ON (s.tenant_id,s.run_id)=(r.tenant_id,r.id) WHERE r.tenant_id=c.tenant_id AND r.case_id=c.id),
    (SELECT max(a.captured_at) FROM socai2.artifacts a WHERE a.tenant_id=c.tenant_id AND a.case_id=c.id),
    (SELECT max(a.captured_at) FROM socai2.artifacts a JOIN socai2.runs r
       ON (a.tenant_id,a.run_id)=(r.tenant_id,r.id) WHERE r.tenant_id=c.tenant_id AND r.case_id=c.id)
  ) AS updated_at FROM socai2.cases c WHERE c.tenant_id=$1::uuid
), page AS (
  SELECT * FROM case_updates WHERE $2::timestamptz IS NULL OR (updated_at,case_id)<($2,$3::uuid)
  ORDER BY updated_at DESC,case_id DESC LIMIT 6
)
SELECT coalesce(jsonb_agg(to_jsonb(page) ORDER BY updated_at DESC,case_id DESC),'[]'::jsonb) FROM page"""


def detail_query():
    # MATERIALIZED scope is shared by the revision and optional full-body queries.
    # Reading id+xmin also detects edits/removals on tables without updated_at.
    versions = ",\n".join("(" + scoped_table_query(t, revision_only=True) + ")" for t in TABLES)
    tables = ",\n".join(f"'{t}',(" + scoped_table_query(t) + ")" for t in TABLES)
    return f"""
WITH subject AS MATERIALIZED ({SCOPE}),
scope AS MATERIALIZED (
  SELECT $1::uuid AS tenant, $2::uuid AS cid, alerts AS aids, incidents AS incident, stages, captured_at FROM subject
), version AS MATERIALIZED (
  SELECT encode(sha256(convert_to(concat_ws('|',{versions}),'UTF8')),'hex') AS revision FROM scope
)
SELECT jsonb_build_object('captured_at',scope.captured_at,'revision',version.revision,'data',
    CASE WHEN version.revision IS DISTINCT FROM $3::text THEN jsonb_build_object({tables}) END)
FROM scope CROSS JOIN version"""


def parse_cursor(cursor):
    if cursor is None:
        return None, None
    try:
        if not isinstance(cursor, str) or len(cursor) > 90:
            raise ValueError
        stamp, ident = cursor.split("|")
        timestamp = datetime.fromisoformat(stamp)
        if timestamp.tzinfo is None:
            raise ValueError
        return timestamp.astimezone(timezone.utc), UUID(ident)
    except (ValueError, OverflowError) as exc:
        raise ValueError("invalid cursor") from exc


async def direct_query(sql, tenant, args, *, production=False):
    dsn = os.environ.get("SOCAI2_AUDIT_DATABASE_URL", "")
    if not dsn.startswith(("postgresql://", "postgres://")):
        raise ValueError("SOCAI2_AUDIT_DATABASE_URL must be a PostgreSQL URL")
    if production and (urlsplit(dsn).path != "/aisoc" or urlsplit(dsn).username != "socai2_prod_reader"):
        raise ValueError("expected the aisoc production reader")
    connection = await asyncpg.connect(dsn, timeout=8, command_timeout=35)
    try:
        async with connection.transaction(isolation="repeatable_read", readonly=True):
            if production and not await connection.fetchval(
                "SELECT current_database()='aisoc' AND current_user='socai2_prod_reader'"
            ):
                raise ValueError("expected the aisoc production reader")
            await connection.execute("SET LOCAL TIME ZONE 'UTC'")
            await connection.execute("SET LOCAL jit=off")
            await connection.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(tenant))
            if not await connection.fetchval(RLS, tenant, list(TABLES)):
                raise ValueError("read-only tenant RLS is required on all configured investigation tables")
            value = await connection.fetchval(sql, tenant, *args)
            return json.loads(value) if value is not None else None
    finally:
        await connection.close(timeout=3)


def sql_argument(value):
    # Only canonical typed values reach EXECUTE. No browser text or identifiers enter SQL.
    if value is None:
        return "NULL"
    if isinstance(value, datetime):
        return "'" + value.isoformat() + "'"
    if isinstance(value, UUID) or (isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value)):
        return "'" + str(value) + "'"
    raise ValueError("unexpected workbench query argument")


def ssh_query(sql, tenant, args, *, production=False):
    if not production and tenant != HANDOFF_TENANT:
        raise ValueError("invalid handoff tenant")
    db_args = "-U socai2_prod_reader -d aisoc" if production else "-U socai2_processing_job -d socai2_processing_handoff"
    names = ",".join(f"'{name}'" for name in TABLES)
    params = ",".join(sql_argument(item) for item in (tenant, *args))
    script = rf"""BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL TIME ZONE 'UTC';
SET LOCAL jit=off;
SET LOCAL statement_timeout='35s';
SET LOCAL idle_in_transaction_session_timeout='45s';
SET LOCAL app.current_tenant_id={sql_argument(tenant)};
PREPARE wb_guard(uuid,text[]) AS SELECT ({RLS}) AS allowed;
EXECUTE wb_guard({sql_argument(tenant)}, ARRAY[{names}]) \gset check_
\if :check_allowed
PREPARE wb_read AS {sql};
EXECUTE wb_read({params});
\else
\echo SCOPE_DENIED
\endif
ROLLBACK;
"""
    command = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
               "-o", "ConnectTimeout=8", "sting-infra21",
               "docker exec -i spirithub-postgres-1 psql -wXAtq -v ON_ERROR_STOP=1 " + db_args]
    # stderr may include database details. Propagate only a fixed error message.
    proc = subprocess.run(command, input=script.encode("utf-8"), capture_output=True, timeout=48,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)
    if proc.returncode:
        raise RuntimeError("workbench source unavailable")
    body = proc.stdout.strip()
    if body == b"SCOPE_DENIED":
        raise ValueError("read-only tenant RLS is required on all configured investigation tables")
    return json.loads(body) if body else None


def query(source, sql, tenant, args):
    if source == "aisoc":
        if os.environ.get("SOCAI2_AUDIT_DATABASE_URL"):
            return asyncio.run(asyncio.wait_for(direct_query(sql, tenant, args, production=True), timeout=48))
        return ssh_query(sql, tenant, args, production=True)
    if source == "21":
        return ssh_query(sql, tenant, args)
    if source == "dsn":
        return asyncio.run(asyncio.wait_for(direct_query(sql, tenant, args), timeout=48))
    raise ValueError("invalid workbench source")


def list_cases(source, tenant, cursor=None):
    rows = query(source, LIST_QUERY, tenant, parse_cursor(cursor))
    page = rows[:PAGE_SIZE]
    next_cursor = None
    if len(rows) > PAGE_SIZE:
        last = page[-1]
        next_cursor = last["updated_at"] + "|" + last["case_id"]
    return {"cases": page, "next_cursor": next_cursor}


def read_case_if_changed(source, tenant, case_id, previous_revision=None):
    if previous_revision is not None and not re.fullmatch("[0-9a-f]{64}", previous_revision):
        raise ValueError("invalid revision")
    row = query(source, detail_query(), tenant, (case_id, previous_revision))
    if row is None:
        raise ValueError(ABSENT)
    return datetime.fromisoformat(row["captured_at"]), row["data"], row["revision"]


def read_case(source, tenant, case_id):
    at, data, _ = read_case_if_changed(source, tenant, case_id)
    return at, data
