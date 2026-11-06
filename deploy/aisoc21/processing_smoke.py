"""Seed one synthetic A/I/Case in the dedicated handoff database.

Run inside the processor image with its private runtime env and CA mounts:
    python /opt/processor/processing_smoke.py run
Use the returned Case ID, revision and prepare operation key twice with the
processor's case-prepare command, then run this read-only assertion:
    python /opt/processor/processing_smoke.py verify

The fixture is authored here and persisted through the Fusion writer. It has
no Kafka offset, lake source event, model output or completed investigation.
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

DB = "socai2_processing_handoff"
ROLE = "socai2_processing_job"
TENANT = uuid5(NAMESPACE_URL, "socai2-processing-handoff:tenant")
ACTOR = uuid5(NAMESPACE_URL, "socai2-processing-handoff:actor")
SOURCE = "synthetic-processing-handoff-v1"
SOURCE_ALERT = uuid5(TENANT, SOURCE + ":source-alert")
INCIDENT = uuid5(TENANT, SOURCE + ":incident")
CREATE = uuid5(TENANT, SOURCE + ":create")
PREPARE = uuid5(TENANT, SOURCE + ":prepare")
CASE = uuid5(TENANT, "socai2.case.create:" + str(CREATE))
FIXTURE = {"synthetic": True, "fixture": SOURCE, "purpose": "case-prepare handoff validation"}

# Recheck the actual server/role before any writes. Both packages connect to
# the same pinned DSN, but each process validates its own live connection.
TARGET = """SELECT current_database() = 'socai2_processing_handoff'
    AND current_user = 'socai2_processing_job'
    AND NOT (rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole)
    AND EXISTS (SELECT 1 FROM public.users WHERE tenant_id = CAST(:tenant AS uuid)
                AND id = CAST(:actor AS uuid) AND is_active IS TRUE)
    FROM pg_roles WHERE rolname = current_user"""


class SmokeError(RuntimeError):
    """A fixed, credential-free diagnostic for an expected check failure."""


def check(condition, code):
    if not condition:
        raise SmokeError(code)


async def persist_fixture():
    # The API and Fusion packages both use the top-level name "app".
    root = Path("/opt/processor/smoke-fusion")
    check((root / "app/services/socai2_sink.py").is_file(), "fusion_source_missing")
    sys.path.insert(0, str(root))
    from app.models.alert import FusedAlert, FusionDecision, RawAlert
    from app.services.delivery_recovery import make_snapshot
    from app.services.socai2_sink import Socai2AlertSink

    stamp = datetime(2026, 11, 6, tzinfo=UTC)
    alert = RawAlert(tenant_id=TENANT, identity_version="source-v1", source_alert_id=SOURCE_ALERT,
        source=SOURCE, title="合成告警：调查处理交接验证", description="由验收脚本构造的告警。",
        hostname="processing-handoff.example.invalid", severity="low", tags=["synthetic"],
        created_at=stamp, event_time=stamp, raw_event=FIXTURE)
    alert.id = alert.deterministic_id()
    fused = FusedAlert(id=alert.id, tenant_id=TENANT, incident_id=INCIDENT, alert=alert,
        fusion_decision=FusionDecision.NEW_INCIDENT, fused_at=stamp)
    sink = Socai2AlertSink(os.environ["DATABASE_URL"], pool_size=1)
    await sink.start()
    try:
        check(sink._pool is not None, "fixture_database_unavailable")
        async with sink._pool.acquire() as conn, conn.transaction(readonly=True):
            await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(TENANT))
            sql = TARGET.replace(":tenant", "$1").replace(":actor", "$2")
            check(await conn.fetchval(sql, TENANT, ACTOR), "fixture_identity_mismatch")
        prior = await sink.lookup_delivery(alert)
        if prior.exists:
            check(prior.snapshot == make_snapshot(fused), "fixture_snapshot_conflict")
        else:
            check((await sink.persist(fused)).durable, "fixture_persist_failed")
        confirmed = await sink.lookup_delivery(alert)
        check(confirmed.snapshot == make_snapshot(fused), "fixture_snapshot_unverified")
    finally:
        await sink.stop()


async def case_smoke(phase):
    from app.db.database import AsyncSessionLocal, engine
    from app.socai2.baseline_contracts import Actor
    from app.socai2.case_contracts import CaseCreate, RunDetail
    from app.socai2.case_service import CaseService
    from sqlalchemy import text

    service = CaseService(AsyncSessionLocal)
    try:
        async with service.transaction(TENANT, readonly=True) as store:
            ok = await store.db.scalar(text(TARGET), {"tenant": TENANT, "actor": ACTOR})
            check(ok, "case_identity_mismatch")
        if phase == "run":
            # Isolate the two Python import roots. Suppress driver logs that
            # could include connection details and report only the error code.
            child = await asyncio.to_thread(subprocess.run, [sys.executable, __file__, "_persist"],
                                            capture_output=True, timeout=90, check=False)
            if child.returncode:
                line = child.stdout.decode(errors="replace").splitlines()
                code = line[-1].removeprefix("SMOKE_ERROR ") if line else ""
                raise SmokeError(code if code.isascii() and code.isidentifier() else "fixture_process_failed")
            receipt = await service.create_case(TENANT, CaseCreate(operation_key=CREATE,
                title="合成调查：处理模块交接验证", tags=["synthetic"], incident_ids=[INCIDENT],
                description="单个合成告警通过 Fusion 存储模块直接写入，供准备调查和幂等读回。"),
                actor=Actor(user_id=ACTOR, name="Processing handoff validation"))
            check(receipt.case_id == CASE, "case_identity_conflict")

        async with service.transaction(TENANT, readonly=True) as store:
            stmt = """SELECT a.id, m.raw_json FROM socai2.alerts a
                JOIN socai2.incident_alerts ia ON ia.tenant_id=a.tenant_id AND ia.alert_id=a.id
                JOIN socai2.case_incidents ci ON ci.tenant_id=ia.tenant_id AND ci.incident_id=ia.incident_id
                JOIN socai2.alert_materials m ON m.tenant_id=a.tenant_id AND m.alert_id=a.id AND m.id=a.latest_material_id
                WHERE a.tenant_id=:tenant AND ci.case_id=:case AND ia.incident_id=:incident"""
            saved = (await store.db.execute(text(stmt), {"tenant": TENANT, "case": CASE, "incident": INCIDENT})).one()
            raw = saved.raw_json
            check(raw["source"] == SOURCE and raw["source_alert_id"] == str(SOURCE_ALERT)
                  and raw["raw_event"] == FIXTURE and raw["source_event_ids"] == [], "synthetic_source_mismatch")
            created = await store.receipt(CASE, CREATE, "case_created")
            check(created is not None, "case_creation_receipt_missing")
            run_id = UUID(created["outcome"]["pending_run_id"])
            prepared = await store.receipt(CASE, PREPARE, "baseline_prepared")
            run_count = await store.db.scalar(text("""SELECT count(*) FROM socai2.runs
                WHERE tenant_id=:tenant AND case_id=:case"""), {"tenant": TENANT, "case": CASE})
            check(run_count == 1, "unexpected_case_runs")
        detail = RunDetail.model_validate(await service.read_run(TENANT, CASE, run_id))
        check(detail.run.kind == "baseline" and detail.run.state == "pending_update" and detail.run.scope_revision == 1
              and detail.current_member_count == 1 and detail.input_member_count == 1
              and str(detail.members[0]["alert_id"]) == str(saved.id), "pending_fixture_scope_mismatch")
        check(not detail.steps and detail.usage["model_calls"] == detail.tool_calls == detail.result_count == 0,
              "unexpected_case_execution")
        if phase == "verify":
            check(prepared is not None and prepared["outcome"] == {"case_id": str(CASE), "scope_revision": 1,
                  "pending_run_id": str(run_id), "created": False}, "prepare_receipt_mismatch")
        return {"phase": phase, "synthetic": True, "source": SOURCE, "alert_id": str(saved.id),
                "incident_id": str(INCIDENT), "case_id": str(CASE), "scope_revision": 1,
                "pending_run_id": str(run_id), "prepare_operation_key": str(PREPARE),
                "prepare_receipt_found": prepared is not None, "case_runs": run_count,
                "state": detail.run.state, "model_calls": detail.usage["model_calls"], "tool_calls": detail.tool_calls}
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["run", "verify", "_persist"])
    phase = parser.parse_args().phase
    try:
        dsn = urlsplit(os.environ["DATABASE_URL"])
        check(dsn.scheme == "postgresql+asyncpg" and dsn.path == "/" + DB and dsn.username == ROLE,
              "refusing_unexpected_dsn")
        if phase == "_persist":
            asyncio.run(persist_fixture())
        else:
            print(json.dumps(asyncio.run(case_smoke(phase)), ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001 -- credentials and driver diagnostics stay inside the job.
        # Preserve diagnostic identity without returning driver messages or a DSN.
        code = str(exc) if isinstance(exc, SmokeError) else type(exc).__name__
        print("SMOKE_ERROR " + code, flush=True)
        sys.exit(1)
