"""Fresh synthetic native-ingress fixtures; separate Fusion import namespace."""
import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import asyncpg

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "services/fusion"), str(ROOT / "services/fusion/tests")]
from app.models.alert import FusedAlert
from app.services import socai2_analysis_tasks, socai2_sink
from app.services.socai2_analysis_tasks import load_policy
from test_socai2_sink_postgres import sample


async def run(args):
    cfg = json.loads(args.config.read_text())
    pool = await asyncpg.create_pool(host=cfg["host"], port=cfg["port"], database=cfg["processing_database"],
        user=cfg["admin"], password=Path(cfg["password_file"]).read_text().strip(),
        server_settings={"role": cfg["processor"]}, min_size=1, max_size=1)
    sink = socai2_sink.Socai2AlertSink("unused", analysis_policy=load_policy(args.policy))
    sink._pool = pool
    try:
        if args.replay:
            fused = FusedAlert.model_validate(json.loads(args.replay.read_text())["fused"])
        else:
            now = datetime.now(UTC)
            fused = sample(tenant=args.tenant, incident=args.incident, event_time=now,
                hostname="step4-synthetic-host", title="Synthetic account inventory command",
                raw_event={"original_vendor": "synthetic", "ocsf_event": {"class_uid": 1007,
                    "time": now.isoformat(), "process": {"pid": 42,
                        "cmd_line": "powershell.exe -NoProfile -Command Get-LocalUser"},
                    "raw_data": "Synthetic process-start observation; authorization unknown."}})
        original = socai2_analysis_tasks.register_initial
        if args.fail_registration:
            async def fail(*_):
                raise RuntimeError("controlled initial task registration failure")
            socai2_analysis_tasks.register_initial = fail
        try:
            result = await sink.persist(fused)
        finally:
            socai2_analysis_tasks.register_initial = original
        async with pool.acquire() as conn, conn.transaction():
            await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(args.tenant))
            alert = await conn.fetchrow("SELECT * FROM socai2.alerts WHERE id=$1", fused.id)
            tasks = await conn.fetch("SELECT * FROM socai2.analysis_tasks WHERE subject_id=$1", fused.id)
            materials = await conn.fetch("SELECT * FROM socai2.alert_materials WHERE alert_id=$1", fused.id)
        body = {"fused": fused.model_dump(mode="json"), "outcome": result.outcome,
            "alert": dict(alert) if alert else None, "tasks": [dict(x) for x in tasks],
            "materials": [dict(x) for x in materials]}
        args.output.write_text(json.dumps(body, default=str, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"alert_id": str(fused.id), "outcome": result.outcome,
            "tasks": len(tasks), "materials": len(materials)}))
        if args.fail_registration:
            assert not result.durable and alert is None and not tasks and not materials
        else:
            assert result.durable and len(tasks) == 1 and len(materials) == 1
    finally:
        await pool.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--tenant", type=UUID, required=True)
    p.add_argument("--incident", type=UUID, default=None)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--replay", type=Path)
    p.add_argument("--fail-registration", action="store_true")
    asyncio.run(run(p.parse_args()))
