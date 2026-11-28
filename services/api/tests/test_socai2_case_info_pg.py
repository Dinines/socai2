"""Direct Case info HTTP checks on the isolated synthetic Story fixture."""
from datetime import datetime
from uuid import uuid4

from app.models import socai2 as m
from app.socai2.baseline_service import BaselineService
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.case_investigations import CaseInvestigationBackend
from investigation_http.adapters.identity import BusinessContext
from investigation_http.adapters.services import CaseBackend
from investigation_http.dependencies import (
    case_investigation_history_service,
    case_service,
)
from investigation_http.main import app
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from test_socai2_case_story_related_pg import add, seed_story


async def seed_summary(fixture):
    async with BaselineService(fixture.sessions).transaction(fixture.tenant) as store:
        empty_case = await add(store, m.Cases, title="Empty fixture", scope_revision=1)
        materials = {}
        for alert_id in (fixture.first, fixture.peer):
            materials[alert_id] = await store.db.scalar(select(m.Alerts.latest_material_id).where(m.Alerts.id == alert_id))
        other_material = await add(store, m.AlertMaterials, alert_id=fixture.first, revision=2,
                                   detection={"tactics": ["Unselected label"]}, source_scope={},
                                   material_state="complete", retention={})
        for material_id, key in ((materials[fixture.first], "new-one"), (materials[fixture.first], "new-two"),
                                 (other_material, "unselected-object")):
            await add(store, m.AlertObjects, alert_id=fixture.first, material_id=material_id, object_type="host",
                      object_role="entity", namespace="net", object_key=key, raw_value=key,
                      normalized_value=key, source_path=f"/objects/{key}", attributes={})

        objects = m.AlertObjects.__table__
        keys = ("namespace", "object_type", "object_key")
        saved = (await store.db.execute(select(objects).where(
            objects.c.tenant_id == fixture.tenant, objects.c.material_id.in_(materials.values()),
        ).order_by(*(objects.c[key] for key in keys), objects.c.id))).mappings()
        groups = {}
        for row in saved:
            groups.setdefault(tuple(row[key] for key in keys), {
                "object_id": str(row["id"]), **{key: row[key] for key in keys}, "raw_value": row["raw_value"],
                "alert_id": str(row["alert_id"]), "material_id": str(row["material_id"]),
                "source_path": row["source_path"],
            })
    return empty_case, list(groups.values())


async def run_checks(engine, record):
    fixture = await seed_story(
        engine, first_detection={"tactics": ["Discovery", "Discovery", "Execution", "", " \t", None,
                                            1, {"label": "bad"}, ["bad"]]},
        peer_detection={"tactics": ["Discovery"]},
    )
    empty_case, groups = await seed_summary(fixture)
    prefix = "/api/v1/socai2/cases"
    case_path = f"{prefix}/{fixture.case_id}"
    overrides = dict(app.dependency_overrides)
    previous = getattr(app.state, "business_context", None)
    app.state.business_context = BusinessContext(tenant_id=fixture.tenant, user_id=fixture.actor, email="Fixture reader")
    app.dependency_overrides[case_service] = lambda: CaseBackend(fixture.sessions)
    app.dependency_overrides[case_investigation_history_service] = lambda: CaseInvestigationBackend(fixture.sessions)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            reply = await client.get(f"{case_path}/info-summary")
            assert reply.status_code == 200
            summary = reply.json()
            assert summary["case_id"] == str(fixture.case_id)
            assert summary["member_object_count"] == len(groups) == 5
            assert summary["object_preview"] == groups[:4]
            assert summary["members_without_current_material_count"] == 1
            assert datetime.fromisoformat(summary["activity_time_from"]) == fixture.at
            assert datetime.fromisoformat(summary["activity_time_to"]) == fixture.end
            assert summary["tactics"] == [
                {"label": "Discovery", "alert_count": 2}, {"label": "Execution", "alert_count": 1},
            ]
            history = await client.get(f"{case_path}/investigations", params={"limit": 1})
            assert history.status_code == 200 and summary["investigation_count"] == history.json()["total"] == 7

            reply = await client.get(f"{prefix}/{empty_case}/info-summary")
            assert reply.status_code == 200
            empty = reply.json()
            assert empty["member_object_count"] == empty["members_without_current_material_count"] == empty["investigation_count"] == 0
            assert empty["activity_time_from"] is empty["activity_time_to"] is None
            assert empty["object_preview"] == empty["tactics"] == []
            missing = await client.get(f"{prefix}/{uuid4()}/info-summary")
            assert missing.status_code == 404 and missing.json()["detail"]["code"] == "case_not_found"

            def unavailable_session():
                raise OperationalError(None, None, RuntimeError("Fixture read failure"))

            app.dependency_overrides[case_service] = lambda: CaseBackend(unavailable_session)
            unavailable = await client.get(f"{case_path}/info-summary")
            assert unavailable.status_code == 503 and unavailable.json()["detail"]["code"] == "service_unavailable"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = previous
    record("case_info_summary_http", {
        "state": "passed",
        "checks": ["current_objects_and_original_representatives", "source_tactics_distinct_members",
                   "history_total", "activity_range_and_missing_material", "empty_404_503"],
    })
