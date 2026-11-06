"""Read the installed page-facing services for the frozen audit IDs inside r3. No HTTP or writes."""
import asyncio
import json
import os
import sys
from uuid import UUID


async def main(plan):
    from app.db.database import AsyncSessionLocal, engine
    from app.socai2.case_contracts import RunDetail
    from app.socai2.case_service import CaseService
    from app.socai2.page_contracts import ContentView, RecordPage, SubjectView
    from app.socai2.page_reader import PageReadService
    from app.socai2.stage_reader import StageReadService
    from sqlalchemy import text

    assert os.environ["SOCAI2_SERVICE_DATABASE_NAME"] == "socai2_processing_handoff"
    tenant = UUID("6aff0ef7-c670-5a84-a2ee-83d73e25b964")
    cases = CaseService(AsyncSessionLocal)
    pages, analyses = PageReadService(AsyncSessionLocal), StageReadService(AsyncSessionLocal)
    assert plan["batch"] == "ie-audit-20261106-a1" and str(tenant) == plan["tenant_id"]
    result = {}
    try:
        async with cases.transaction(tenant, readonly=True) as store:
            pair = (await store.db.execute(text("SELECT current_database(),current_user"))).one()
            assert tuple(pair) == ("socai2_processing_handoff", "socai2_processing_job")
        for row in plan["cases"]:
            card = result[row["key"]] = {}
            for raw in row["alert_ids"]:
                aid = UUID(raw)
                detail = SubjectView.model_validate(await pages.read(tenant, "alerts", aid, "view"))
                card["alerts/" + raw] = detail.model_dump(mode="json")
                material = await pages.read(tenant, "alerts", aid, "material_content", material_id=detail.facts.latest_material_id)
                card["alerts/" + raw + "/material"] = ContentView.model_validate(material).model_dump(mode="json")
                entry = await analyses.read_page(tenant, "alert_basic", aid)
                card["alerts/" + raw + "/analysis"] = entry.model_dump(mode="json")
            iid, cid, rid = map(UUID, (row["incident_id"], row["case_id"], row["baseline_run_id"]))
            card["incident"] = SubjectView.model_validate(await pages.read(tenant, "incidents", iid, "view")).model_dump(mode="json")
            members = RecordPage.model_validate(await pages.read(tenant, "incidents", iid, "records", section="members"))
            assert {str(m["id"]) for m in members.items} == set(row["alert_ids"])
            card["incident/members"] = members.model_dump(mode="json")
            card["incident/analysis"] = (await analyses.read_page(tenant, "incident_diagnosis", iid)).model_dump(mode="json")
            card["case/page-data"] = (await cases.read_page_data(tenant, cid)).model_dump(mode="json")
            card["case/run"] = RunDetail.model_validate(await cases.read_run(tenant, cid, rid)).model_dump(mode="json")
        return result
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print("PAGE_OUTPUT=" + json.dumps(asyncio.run(main(json.load(sys.stdin))), ensure_ascii=False))
