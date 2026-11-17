"""HTTP serialization only; core results are explicit substitutes, no PG/model."""
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from investigation_http.adapters.identity import (
    BusinessContext,
    configure_trusted_access,
)
from investigation_http.contracts import (
    IncidentStageEntry,
    IncidentStagePage,
    StageEntry,
    StagePage,
)
from investigation_http.dependencies import analysis_service
from investigation_http.external_routes.analysis import router

TENANT, SUBJECT, RUN = (UUID(int=n) for n in (1, 2, 3))
AT = "2026-11-15T00:00:00Z"


def entry_data(kind, *, historical=False):
    incident = kind == "incident_diagnosis"
    run_id = UUID(int=4) if historical else RUN
    data = {"run": {"id": run_id, "kind": kind, "state": "completed", "requested_at": AT,
        "requested_by": None, "started_at": AT, "ended_at": AT, "executor_version": "http-substitute",
        "input_artifact_id": UUID(int=5), "stop_reason": None, "delivery_state": "complete"},
        "freshness": "current", "is_current_pointer": not historical, "valid_for_current_input": not historical,
        "result": None, "explanation": None, "partial_analysis": None}
    if incident:
        data["result"] = {"id": UUID(int=6 if not historical else 7), "source_run_id": run_id,
            "revision": 2 if not historical else 1, "state": "completed", "summary": "HTTP serialization fixture",
            "diagnosis": {"validation_state": "accepted"}, "open_questions": [], "input_artifact_id": UUID(int=5),
            "source_fingerprint": "0" * 64, "producer": "http-substitute", "requested_at": AT,
            "generated_at": AT, "error_code": None}
        if not historical:
            selected = [UUID(int=n) for n in range(100, 200)]
            data.update(input_selection={"policy": "recently_linked", "limit": 100,
                "order": "linked_at_desc_alert_id_asc", "captured_at": AT,
                "total_member_count": 260, "selected_count": 100, "omitted_count": 160,
                "selected_alert_ids": selected, "input_artifact_id": UUID(int=5)},
                analysis_coverage={"state": "partial", "analyzed_count": 80, "unresolved_count": 20,
                    "not_analyzed_count": 0, "covered_alert_ids": selected, "limitations": ["members_omitted"]})
    return data


def client():
    class Reader:
        async def read_entry(self, tenant, kind, identity, run_id):
            assert tenant == TENANT and identity == SUBJECT
            model = IncidentStageEntry if kind == "incident_diagnosis" else StageEntry
            return model.model_validate(entry_data(kind, historical=run_id != RUN))

        async def read_page(self, tenant, kind, identity, **query):
            current = await self.read_entry(tenant, kind, identity, RUN)
            old = await self.read_entry(tenant, kind, identity, UUID(int=4))
            model = IncidentStagePage if kind == "incident_diagnosis" else StagePage
            return model(subject_id=identity, kind=kind, current_pointer_id=UUID(int=6),
                         current=current, entries=[current, old], current_unavailable_reason=None,
                         next_before_run_id=None)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    configure_trusted_access(app)
    app.state.business_context = BusinessContext(TENANT, UUID(int=9), "HTTP serialization check")
    app.dependency_overrides[analysis_service] = Reader
    return TestClient(app)


def test_event_fields_survive_list_and_detail_and_keep_historical_null():
    with client() as http:
        root = f"/api/v1/socai2/incidents/{SUBJECT}/analysis"
        response = http.get(root)
        assert response.status_code == 200
        assert "authorization" not in response.request.headers
        page = response.json()
        detail = http.get(root + f"/runs/{RUN}")
        assert detail.status_code == 200 and detail.json() == page["current"] == page["entries"][0]
        entry = detail.json()
        assert entry["input_selection"]["selected_count"] == 100
        assert entry["input_selection"]["omitted_count"] == 160
        assert entry["input_selection"]["total_member_count"] == 260
        assert entry["analysis_coverage"]["covered_alert_ids"] == entry["input_selection"]["selected_alert_ids"]
        assert entry["analysis_coverage"]["analyzed_count"] == 80
        assert entry["analysis_coverage"]["unresolved_count"] == 20
        assert entry["analysis_coverage"]["not_analyzed_count"] == 0
        assert entry["analysis_coverage"]["state"] == "partial" and entry["run"]["delivery_state"] == "complete"
        assert page["entries"][1]["input_selection"] is None
        assert page["entries"][1]["analysis_coverage"] is None


def test_alert_json_does_not_gain_event_fields():
    with client() as http:
        root = f"/api/v1/socai2/alerts/{SUBJECT}/analysis"
        response = http.get(root)
        assert response.status_code == 200
        detail = http.get(root + f"/runs/{RUN}")
        assert detail.status_code == 200
        page = response.json()
        for entry in [page["current"], *page["entries"], detail.json()]:
            assert not {"input_selection", "analysis_coverage"} & entry.keys()
