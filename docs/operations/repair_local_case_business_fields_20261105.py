"""Repair only the four named local synthetic Cases; retain every original Run/Result."""
import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4, uuid5

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / p) for p in ("deploy/local-investigation", "services/api")]

from app.models import socai2 as m
from app.socai2.baseline_closing import statement
from app.socai2.baseline_service import BaselineService
from app.socai2.baseline_store import digest
from config import API_ROLE, DATABASE, STATE, TENANT, read_private
from initialize import safe_error
from sqlalchemy import URL, func, insert, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

BATCHES = ["local-maintenance-20261105" + suffix for suffix in "defg"]


def json_value(value):
    return json.loads(json.dumps(value, default=str))


async def main(execute):
    values = read_private()
    engine = create_async_engine(URL.create("postgresql+asyncpg", username=API_ROLE,
        password=values["API_DB_PASSWORD"], host="127.0.0.1", port=15432, database=DATABASE),
        connect_args={"ssl": False}, hide_parameters=True)
    service, changes = BaselineService(async_sessionmaker(engine)), []
    actor = {"type": "service", "user_id": None, "name_snapshot": "调查系统",
        "service_name": "socai2.local-business-field-repair", "service_version": "v1"}
    try:
        for batch in BATCHES:
            root = STATE / "validation" / batch
            plan = json.loads((root / "plan.json").read_text())
            cid = UUID(json.loads((root / "case-create-response.json").read_text())["body"]["case_id"])
            operation = uuid5(cid, "case-business-fields-20261105-v1")
            async with service.transaction(UUID(TENANT)) as store:
                case = await store.case(cid)
                assert case["title"] == "Maintenance record review " + batch
                if await store.receipt(cid, operation, "case_business_fields_repaired"):
                    changes.append({"batch": batch, "state": "already_applied"})
                    continue
                # The background is the fixed input scenario, never a rejected model answer.
                description = "本案涉及主机 " + plan["case"]["host"] + " 的进程启动与网络连接记录，需核查行为关系、授权情况及影响范围。"
                members = await store.members(cid)
                assert set(map(str, members)) == set(plan["canonical_alert_ids"])
                artifacts, results = m.Artifacts.__table__, m.Results.__table__
                protected = []
                for table in (artifacts, results, m.CaseAssessments.__table__):
                    protected += list((await store.db.execute(select(table).where(*store.where(table,
                        table.c.case_id == cid)).order_by(table.c.id))).mappings().all())
                protected_hash = digest(json_value([dict(row) for row in protected]))
                update_values, replacement = {}, None
                if not case["description"]:
                    update_values["description"] = description
                assessment_table, sources = m.CaseAssessments.__table__, m.CaseAssessmentSources.__table__
                current = await store.one(select(assessment_table).where(*store.where(assessment_table,
                    assessment_table.c.id == case["current_assessment_id"]))) if case["current_assessment_id"] else None
                if current and current["origin"] == "system" and current["validity"] == "system_only":
                    assert current["conclusion"].startswith("系统收尾：") and "原因：" in current["conclusion"]
                    assert current["scope_revision"] == case["scope_revision"]
                    assert not await store.one(select(m.CaseAssessmentMembers.__table__).where(
                        *store.where(m.CaseAssessmentMembers.__table__,
                            m.CaseAssessmentMembers.assessment_id == current["id"])))
                    replacement = statement(len(members))
                change = {"batch": batch, "case_id": str(cid), "description_saved": bool(update_values),
                    "system_conclusion_revised": replacement is not None,
                    "existing_model_or_human_judgment_preserved": bool(current and replacement is None),
                    "protected_records_before_sha256": protected_hash, "model_calls": 0}
                if execute:
                    if replacement is not None:
                        new_id, now = uuid4(), await store.now()
                        revision = (await store.db.execute(select(func.max(assessment_table.c.revision)).where(
                            *store.where(assessment_table, assessment_table.c.case_id == cid)))).scalar_one() + 1
                        await store.db.execute(insert(assessment_table).values(**{
                            **dict(current), "id": new_id, "revision": revision, "conclusion": replacement,
                            "adopted_at": now, "actor": actor, "operation_key": str(operation),
                            "reason": "字段职责修正；业务判断未改变，执行原因保留在来源调查中。"}))
                        for source in (await store.db.execute(select(sources).where(*store.where(sources,
                                sources.c.assessment_id == current["id"])))).mappings().all():
                            await store.db.execute(insert(sources).values(**{
                                **dict(source), "id": uuid4(), "assessment_id": new_id}))
                        update_values["current_assessment_id"] = new_id
                    if update_values:
                        await store.db.execute(update(m.Cases.__table__).where(*store.where(m.Cases.__table__,
                            m.Cases.id == cid)).values(**update_values, row_version=case["row_version"] + 1,
                                business_updated_at=await store.now()))
                    # Check each protected identity again, including the historical assessment.
                    verified = []
                    for row in protected:
                        table = artifacts if "content_json" in row else results if "conclusion_origin" in row else assessment_table
                        verified.append(dict(await store.one(select(table).where(*store.where(table, table.c.id == row["id"])))))
                    assert digest(json_value(verified)) == protected_hash
                    await store.event(cid, operation, actor, "case_business_fields_repaired", {"outcome": change},
                        [("case_id", cid, json_value({k: case[k] for k in update_values}), json_value(update_values))])
                changes.append(change)
        result = {"executed": execute, "database": DATABASE, "changes": changes,
            "original_results_artifacts_assessments_verified_unchanged": execute, "model_calls": 0}
        path = ROOT / "docs/operations/evidence/investigation-repair-20261105" / (
            datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + "-case-business-fields.json")
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"receipt": str(path), **result}, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001 -- sanitize configuration secrets at the CLI boundary
        print(safe_error(exc, values))
        return 1
    finally:
        await engine.dispose()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    raise SystemExit(asyncio.run(main(parser.parse_args().execute)))
