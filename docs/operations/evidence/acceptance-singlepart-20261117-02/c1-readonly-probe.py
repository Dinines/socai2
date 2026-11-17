"""Compare old/fixed C1 SQL in an isolated process and read-only transactions."""
import asyncio
import hashlib
import json
import sys
import types
from pathlib import Path
from uuid import UUID, uuid4

from app.socai2 import baseline_context, case_incident_material
from app.socai2.baseline_contracts import Start
from app.socai2.baseline_service import BaselineService
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


async def main(payload):
    profile = json.loads(Path(payload["dispatcher_profile"]).read_text())
    engine = create_async_engine(Path(profile["database_url_file"]).read_text().strip(),
                                 connect_args=profile["database_connect_args"], hide_parameters=True)
    service = BaselineService(async_sessionmaker(engine, expire_on_commit=False))
    tenant = UUID(profile["tenant_id"])
    original = baseline_context.CAPTURE_SQL
    candidate = types.ModuleType("app.socai2._isolated_fixed_incident_material")
    candidate.__package__ = "app.socai2"
    exec(compile(payload["candidate_source"], "isolated-candidate.py", "exec"), candidate.__dict__)
    old_fragment = case_incident_material.source_sql()
    assert original.count(old_fragment) == 1
    fixed = original.replace(old_fragment, candidate.source_sql())
    outputs = []
    try:
        for label, sql in (("deployed", original), ("fixed_isolated_readonly", fixed)):
            baseline_context.CAPTURE_SQL = sql  # This short-lived process only; no worker change.
            for raw_id in payload["case_ids"]:
                item = {"version": label, "case_id": raw_id}
                try:
                    async with service.transaction(tenant, readonly=True) as store:
                        case = await store.case(UUID(raw_id), lock=False)
                        expected = {str(x) for x in await store.members(case["id"])}
                        context = await baseline_context.capture(store.db, tenant, case["id"],
                            Start(operation_key=uuid4(), expected_scope_revision=case["scope_revision"]))
                        assert set(context.alerts) == expected
                        checked = []
                        for iid, inc in context.incidents.items():
                            assert inc.incident["id"] == iid
                            material = inc.analysis_material
                            assert material is not None
                            source = (await store.db.execute(text("SELECT content_json FROM socai2.artifacts "
                                "WHERE tenant_id=:tenant AND id=:id AND incident_id=:incident"),
                                {"tenant": tenant, "id": UUID(material["input"]["id"]), "incident": UUID(iid)})).scalar_one()
                            assert source["parent"]["id"] == iid
                            assert set(source["input_selection"]["selected_alert_ids"]) == {m["alert"]["id"] for m in source["members"]}
                            assert set(material["case_selected_alert_ids"]) <= expected
                            checked.append({"incident_id": iid, "source_run_id": material["source_run_id"],
                                            "selected_alert_ids": source["input_selection"]["selected_alert_ids"]})
                        item.update(status="passed", readonly=(await store.db.execute(text("SHOW transaction_read_only"))).scalar_one() == "on",
                                    alert_ids=sorted(context.alerts), incidents=checked,
                                    context=context.model_dump(mode="json"))
                except Exception as exc:
                    cause = getattr(getattr(exc, "orig", None), "__cause__", None)
                    item.update(status="failed", exception_type=type(exc).__name__, database_type=type(cause).__name__,
                                sqlstate=getattr(cause, "sqlstate", None), database_message=str(getattr(cause, "message", "")))
                outputs.append(item)
        assert all(r["status"] == "failed" and r["sqlstate"] == "21000" for r in outputs if r["version"] == "deployed")
        assert all(r["status"] == "passed" and r["readonly"] for r in outputs if r["version"] == "fixed_isolated_readonly")
        return {"status": "passed", "candidate_sha256": hashlib.sha256(payload["candidate_source"].encode()).hexdigest(),
                "deployed_source_sha256": hashlib.sha256(Path(case_incident_material.__file__).read_bytes()).hexdigest(),
                "checks": outputs, "new_business_writes": 0, "new_model_calls": 0,
                "active_service_changed": False, "case_run_created": False}
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(main(json.load(sys.stdin))), ensure_ascii=False))
