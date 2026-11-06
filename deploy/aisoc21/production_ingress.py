"""Copy explicitly selected, authenticated production subjects into the V1 investigation schema.

Runs inside the r3 processing image after the caller's authorization. Production
Fusion already committed the canonical alert and incident. Preserve their IDs
and first delivery instead of performing a second round of fusion.
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

import asyncpg

ROLE = "socai2_prod_ingress"
SOURCE = """
SELECT id,tenant_id,source_incident_id,snapshot
FROM socai2_ops.prod_alert_sources($1::uuid,$2::uuid,$3::boolean)
ORDER BY id
"""


class IngressError(ValueError):
    def __init__(self, code, subject=None):
        super().__init__(code)
        self.receipt = {"error": code}
        if subject is not None:
            self.receipt["subject_id"] = str(subject)


def source_delivery(row, tenant, subject, by_incident):
    from app.models.alert import RawAlert
    from app.services.delivery_recovery import restore_snapshot

    value = row["snapshot"]
    if not value:
        raise IngressError("source_alert_snapshot_unavailable", row["id"])
    try:
        snapshot = json.loads(value) if isinstance(value, str) else value
        raw = RawAlert.model_validate(snapshot["fused"]["alert"])
        fused = restore_snapshot(snapshot, raw)
    except (ValueError, KeyError, TypeError, RuntimeError) as exc:
        raise IngressError("source_snapshot_invalid", row["id"]) from exc
    if (fused.tenant_id != tenant or row["tenant_id"] != tenant or fused.id != row["id"]
            or str(fused.incident_id) != row["source_incident_id"]
            or (fused.incident_id if by_incident else fused.id) != subject):
        raise IngressError("source_identity_mismatch", subject)
    return fused, snapshot


async def sync_subject(conn, sink, tenant, subject, by_incident, *, expected_incident=None):
    from app.services.alert_sink import PersistOutcome
    from app.services.socai2_projection import snapshot_id

    found = False
    projected = 0
    async for row in conn.cursor(SOURCE, tenant, subject, by_incident, prefetch=1):
        found = True
        fused, snapshot = source_delivery(row, tenant, subject, by_incident)
        if expected_incident is not None and fused.incident_id != expected_incident:
            raise IngressError("notification_incident_mismatch", subject)
        previous = await conn.fetchval("""
            SELECT content_json->>'sha256' FROM socai2.artifacts
            WHERE tenant_id=$1 AND alert_id=$2 AND id=$3""", tenant, fused.id, snapshot_id(fused.id))
        if previous is not None and previous != snapshot["sha256"]:
            raise IngressError("source_identity_mismatch", fused.id)
        # The native sink's transaction body also checks identity conflicts,
        # verifies connector tenancy, and deduplicates immutable material.
        outcome = await sink._write(conn, fused, fused.alert, snapshot)
        projected += int(outcome is PersistOutcome.INSERTED)
    if not found:
        if expected_incident is not None:
            raise IngressError("source_subject_absent", subject)
        # The native V1 writer may already own a subject without a public row.
        table = "incidents" if by_incident else "alerts"
        if not await conn.fetchval(f"SELECT EXISTS(SELECT FROM socai2.{table} WHERE tenant_id=$1 AND id=$2)",
                                   tenant, subject):
            raise IngressError("source_subject_absent", subject)
    return projected


def database_url():
    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlsplit(dsn)
    if (parsed.scheme, parsed.path, parsed.username) != ("postgresql", "/aisoc", ROLE):
        raise IngressError("invalid_ingress_database")
    return dsn


async def check_identity(conn, tenant):
    await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(tenant))
    ready = await conn.fetchval("""
        SELECT current_database()='aisoc' AND current_user=$1 AND public.current_tenant_id()=$2::uuid
         AND NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolbypassrls OR rolreplication)
         AND row_security_active('socai2.alerts'::regclass)
         AND has_function_privilege('socai2_ops.prod_alert_sources(uuid,uuid,boolean)','EXECUTE')
        FROM pg_catalog.pg_roles WHERE rolname=current_user""", ROLE, tenant)
    if ready is not True:
        raise IngressError("invalid_ingress_database")


async def project(tenant, alerts, incidents, *, expected_incident=None):
    from app.services.socai2_sink import Socai2AlertSink

    dsn = database_url()
    conn = await asyncpg.connect(dsn, timeout=10, command_timeout=60)
    try:
        # All requested members are visible together, or the transaction rolls back.
        async with conn.transaction():
            await check_identity(conn, tenant)
            await conn.execute("SET LOCAL lock_timeout='15s'")
            await conn.execute("SELECT pg_advisory_xact_lock(hashtext('socai2 production snapshot ingest'),hashtext($1))",
                               str(tenant))
            projected = 0
            sink = Socai2AlertSink(dsn)
            for by_incident, ids in ((False, alerts), (True, incidents)):
                for subject in sorted(set(ids)):
                    projected += await sync_subject(conn, sink, tenant, subject, by_incident,
                                                    expected_incident=expected_incident)
    finally:
        await conn.close()
    return {"status": "ready", "source": "aisoc", "alert_ids_requested": len(set(alerts)),
            "incident_ids_requested": len(set(incidents)), "projected": projected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", type=UUID, required=True)
    parser.add_argument("--alert-id", action="append", type=UUID, default=[])
    parser.add_argument("--incident-id", action="append", type=UUID, default=[])
    args = parser.parse_args()
    if not args.alert_id and not args.incident_id:
        parser.error("select one or more alerts or incidents")
    if Path("/opt/processor/smoke-fusion").is_dir():
        sys.path.insert(0, "/opt/processor/smoke-fusion")
    try:
        response = asyncio.run(project(args.tenant, args.alert_id, args.incident_id))
    except IngressError as exc:
        print(json.dumps(exc.receipt))
        return 1
    except Exception:  # noqa: BLE001 -- never expose connection strings, queries or source data
        print(json.dumps({"error": "ingress_unavailable"}))
        return 1
    print(json.dumps(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
