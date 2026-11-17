"""One zero-generation check of the early prepared-size failure boundary."""
import argparse
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

from consume import run as consume
from validate import HERE, environment, save


async def main(args, config):
    from app.models import socai2 as m
    from app.socai2 import case_model_boundary
    from app.socai2.baseline_contracts import Actor
    from app.socai2.case_contracts import CaseCreate
    from app.socai2.case_service import CaseService
    from sqlalchemy import select
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    seed = json.loads((HERE/args.source/"result.json").read_text())
    tenant, actor = UUID(seed["tenant_id"]), UUID(seed["actor_id"])
    cfg = json.loads(Path(config["database_profile"]).read_text())
    engine = create_async_engine(URL.create("postgresql+psycopg", username=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), host=cfg["host"], port=cfg["port"], database=cfg["processing_database"]),
        hide_parameters=True, connect_args={"sslmode":config["sslmode"], "options":"-c role="+cfg["processor"]})
    cases = CaseService(async_sessionmaker(engine, expire_on_commit=False))
    out = HERE/args.batch
    out.mkdir(exist_ok=False)
    result = {"state":"running", "tenant_id":str(tenant), "real_model_calls":0,
              "test_substitute":"prepared-byte limit forced to 1; runtime configuration unchanged"}
    try:
        receipt = await cases.create_case(tenant, CaseCreate(operation_key=uuid4(), title="Prepared byte capacity",
            alert_ids=[UUID(aid) for aid in seed["alert_ids"]]), actor=Actor(user_id=actor, name="Case initial fixture"))
        save(out/"admission.json", receipt)
        with patch.object(case_model_boundary, "draft_limit", lambda:1):
            await consume(SimpleNamespace(tenant=tenant, output=out/"consume.json"), config)
        snapshot = {}
        async with cases.transaction(tenant, readonly=True) as store:
            for model in (m.Cases, m.CaseAlerts, m.AnalysisTasks, m.AnalysisAttempts, m.Runs,
                          m.RunMembers, m.RunSteps, m.Artifacts, m.Results, m.ResultMembers):
                table = model.__table__
                snapshot[model.__tablename__] = [dict(r) for r in (await store.db.execute(select(table)
                    .where(table.c.tenant_id == tenant).order_by(*table.primary_key.columns))).mappings()]
        save(out/"snapshot.json", snapshot)
        run = snapshot["runs"][0]
        task = snapshot["analysis_tasks"][0]
        assert run["state"] == task["state"] == "failed" and run["stop_reason"] == "capacity_exceeded"
        assert task["next_retry_at"] is None and len(snapshot["analysis_attempts"]) == 1
        assert not [f for f in snapshot["artifacts"] if f["kind"] == "model_request"]
        prepared = next(f["content_json"] for f in snapshot["artifacts"]
            if (f["content_json"] or {}).get("reason") == "case_input_exceeds_prepared_limit"
            and (f["content_json"] or {}).get("unsent_messages"))
        assert set(prepared["case_boundary"]["member_aliases"]) == set(seed["alert_ids"])
        assert len(snapshot["results"]) == 1
        save(out/"readback.json", await cases.read_run(tenant, receipt.primary_case_id, run["id"]))
        result.update(state="passed", case_id=receipt.primary_case_id, task_id=task["id"], run_id=run["id"],
                      substitute_model_calls=0, checks=["prepared_size_failure_preserves_unsent_input_and_members",
                          "no_model_dispatch_no_retry_terminal_run_result_readable"])
    except Exception as exc:
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        save(out/"result.json", result)
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--batch", required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    environment(config)
    asyncio.run(main(args, config))
