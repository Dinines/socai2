"""Automatic 100+1 allocation with service actor; new isolated PG fixtures, no consumer or model."""
import argparse
import asyncio
import json
import sys
import traceback
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "services/api"), str(ROOT / "services/api/tests"),
    str(HERE.parent / "case-initial-20261115-01")]
import validate as initial_fixture
from controlled import Gateway, Lake, empty_query

save, environment = initial_fixture.save, initial_fixture.environment


async def run(args, config):
    from app.models import socai2 as m
    from app.socai2 import baseline_enrichment_sources
    from app.socai2.analysis_case_executor import executors
    from app.socai2.analysis_dispatch_config import DispatchPolicy
    from app.socai2.analysis_dispatch_redis import AnalysisQueues
    from app.socai2.analysis_dispatch_store import DispatchRepository
    from app.socai2.analysis_dispatcher import AnalysisDispatcher
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from datetime import timedelta
    from app.socai2.baseline_contracts import Actor, Scope
    from app.socai2.baseline_context import reference
    from app.socai2.analysis_task_store import S
    from app.socai2.stage_results import StageResultService
    from app.socai2.stage_result_contracts import AlertOutput, IncidentOutput
    from app.socai2.runtime_policy import active_policy
    from app.socai2.case_management import manage_case
    from app.socai2.case_management_contracts import CaseCloseRequest
    from app.socai2.baseline_store import digest
    from app.socai2.case_contracts import CaseCreate
    from app.socai2.case_service import CaseService
    from app.socai2.human_task_contracts import TaskCreate, TaskEdit
    from app.socai2.human_task_service import HumanTaskService
    from redis.asyncio import Redis
    from sqlalchemy import insert, select, text, update
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    out = HERE / args.batch
    out.mkdir(exist_ok=False)
    initial_fixture.HERE = HERE
    await initial_fixture.main(SimpleNamespace(batch=args.batch + "-sources", seed_only=True), config)
    seed = json.loads((HERE / (args.batch + "-sources") / "result.json").read_text())
    tenant, actor = UUID(seed["tenant_id"]), Actor(user_id=seed["actor_id"], name="Case updates synthetic verification")
    cfg = json.loads(Path(config["database_profile"]).read_text())
    assert cfg["processing_database"] == "v12_upgrade_dev"
    engine = create_async_engine(URL.create("postgresql+psycopg", username=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), host=cfg["host"], port=cfg["port"], database=cfg["processing_database"]),
        hide_parameters=True, connect_args={"sslmode": config["sslmode"], "options": "-c role=" + cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cases, human = CaseService(sessions), HumanTaskService(sessions)
    tasks = AnalysisTaskService(sessions, AnalysisTaskPolicy.load())
    handlers = executors({key: config[key] for key in ("investigation_policy_file", "incident", "case")}, tasks)
    result = {"state": "running", "tenant_id": tenant, "actor_id": actor.user_id, "checks": [],
              "real_model_calls": 0, "database": cfg["processing_database"], "tasks": []}

    try:
        from app.socai2.case_update_scanner import follow_current
        executor = handlers["case_investigation"]
        aids = [UUID(v) for v in seed["alert_ids"]]
        extra = [uuid4() for _ in range(99)]
        iid = uuid4()
        async with cases.transaction(tenant) as store:
            await store.db.execute(insert(m.Alerts), [dict(id=aid,tenant_id=tenant,source_namespace="case-initial-fixture",
                source_identity_key=str(aid),title="Synthetic member for automatic capacity") for aid in extra])
            await store.db.execute(insert(m.Incidents).values(id=iid,tenant_id=tenant,source_namespace="case-initial-fixture",
                source_incident_id=str(iid),title="Automatic capacity synthetic event"))
            await store.db.execute(insert(m.IncidentAlerts), [dict(id=uuid4(),tenant_id=tenant,incident_id=iid,alert_id=aid,
                membership_source="fusion",correlation_basis={},basis_version="step7.fixture",source_operation_id=uuid4()) for aid in aids+extra[:-1]])
        first = await cases.create_case(tenant,CaseCreate(operation_key=uuid4(),title="100 member automatic receiver",incident_ids=[iid]),actor=actor)
        async with cases.transaction(tenant) as store:
            await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(),tenant_id=tenant,incident_id=iid,alert_id=extra[-1],
                membership_source="fusion",correlation_basis={},basis_version="step7.fixture",source_operation_id=uuid4()))
        receipts = await follow_current(executor,tenant,first.primary_case_id)
        assert len(receipts) == 1
        receipt = receipts[0]
        child = receipt.receiving_case_id
        assert child != first.primary_case_id
        assert (await cases.read_case(tenant,first.primary_case_id))["member_count"] == 100
        view = await cases.read_case(tenant,child)
        assert view["member_count"] == 1
        async with cases.transaction(tenant,readonly=True) as store:
            event = (await store.db.execute(select(m.Incidents.__table__).where(m.Incidents.id == iid))).mappings().one()
            task = (await store.db.execute(select(m.AnalysisTasks.__table__).where(m.AnalysisTasks.subject_id == child))).mappings().one()
            case = await store.case(child,lock=False)
        assert event["active_case_id"] == child and case["created_by"] is None
        assert case["previous_case_id"] == first.primary_case_id
        assert task["intent"] == "initial" and task["submitted_by"] is None and task["state"] == "accepted"
        assert await follow_current(executor,tenant,child) == []
        result.update(state="passed",case_ids=[first.primary_case_id,child],receipt=receipt.model_dump(mode="json"),
            checks=["service_actor_auto_100_plus_1_successor_task_and_unique_receiver", "no_new_members_no_allocation_activity"],
            real_model_calls=0,substitute_model_calls=0,case_execution_calls=0)
    except Exception as exc:
        result.update(state="failed",error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
        raise
    finally:
        save(out / "result.json",result)
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config",type=Path,required=True)
    parser.add_argument("--batch",required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    environment(config)
    asyncio.run(run(args,config))
