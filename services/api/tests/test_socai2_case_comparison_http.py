"""Case comparison transport uses frozen identities; core reads are substitutes."""
import asyncio
import copy
import json
from pathlib import Path
from uuid import UUID

import pytest
from app.socai2.case_contracts import ResultView, RunView
from app.socai2.case_service import CaseService
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.identity import BusinessContext
from investigation_http.adapters.services import CaseBackend
from investigation_http.dependencies import case_service
from investigation_http.main import app

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / "docs/operations/evidence/case-initial-http-20261115-01/examples.json"
TENANT, ACTOR, PREVIOUS, RESULT = (UUID(int=i) for i in (7101, 7102, 7103, 7104))


@pytest.mark.parametrize("context", [
    None,
    {"previous_run_id": None, "comparison_result_id": None, "state": "initial", "reason_code": None},
    {"previous_run_id": str(PREVIOUS), "comparison_result_id": str(RESULT),
     "state": "eligible", "reason_code": None},
    *({"previous_run_id": str(PREVIOUS), "comparison_result_id": None,
       "state": "unavailable", "reason_code": reason} for reason in (
        "previous_result_unavailable", "previous_input_unavailable", "previous_scope_unavailable",
        "previous_scope_not_overlapping", "previous_conclusion_unusable")),
])
def test_case_detail_links_preserve_frozen_comparison(monkeypatch, context):
    # Reuse ended receipt shapes only; no database/task/model replay.
    examples = json.loads(EXAMPLES.read_text())
    run, result = (copy.deepcopy(examples[k]["body"]) for k in ("run", "result"))
    cid, rid, result_id = run["run"]["case_id"], run["run"]["id"], result["result"]["id"]
    comparison_result = context["comparison_result_id"] if context else None
    for row in (run["run"], result["run"], result["result"]):
        row["comparison_context"] = copy.deepcopy(context)
        row["comparison_result_id"] = comparison_result
    snapshots = copy.deepcopy((run, result))
    # The real reader returns nested contract objects, before JSON serialization.
    core_run = {**run, "run": RunView.model_validate(run["run"])}
    core_result = {**result, "run": RunView.model_validate(result["run"]),
        "result": ResultView.model_validate(result["result"])}
    core_snapshots = copy.deepcopy((core_run, core_result))
    calls = []

    async def read_run(self, tenant_id, case_id, run_id):
        calls.append(("run", tenant_id, case_id, run_id))
        return core_run

    async def read_result(self, tenant_id, case_id, identity):
        calls.append(("result", tenant_id, case_id, identity))
        return core_result

    monkeypatch.setattr(CaseService, "read_run", read_run)
    monkeypatch.setattr(CaseService, "read_result", read_result)
    monkeypatch.setattr(app.state, "business_context", BusinessContext(TENANT, ACTOR, "Comparison fixture"), raising=False)
    monkeypatch.setitem(app.dependency_overrides, case_service, lambda: CaseBackend(None))

    async def check():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            for suffix, body in ((f"runs/{rid}", run), (f"results/{result_id}", result)):
                response = await client.get(f"/api/v1/socai2/cases/{cid}/{suffix}")
                assert "authorization" not in response.request.headers
                assert response.status_code == 200, response.text
                value = response.json()
                previous_id = context["previous_run_id"] if context else None
                assert value.pop("previous_run_url") == (
                    f"/api/v1/socai2/cases/{cid}/runs/{previous_id}" if previous_id else None)
                assert value.pop("comparison_result_url") == (
                    f"/api/v1/socai2/cases/{cid}/results/{comparison_result}" if comparison_result else None)
                assert value == body
        assert (run, result) == snapshots, "HTTP must not modify core comparison or content"
        assert (core_run, core_result) == core_snapshots
        assert calls == [("run", TENANT, UUID(cid), UUID(rid)),
                         ("result", TENANT, UUID(cid), UUID(result_id))]

    asyncio.run(check())
