"""Direct F2 examples: saved overview, manual refresh, failure and first generation."""
from datetime import timedelta
import json
from pathlib import Path
import sys
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import httpx
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_investigation_incident_api as fixtures
from app.api.v1.deps import CurrentUser, get_current_user
from app.db.rls import get_tenant_db
from app.investigation_v2 import incident_api, incident_summary as summaries, incident_summary_worker as worker
from app.investigation_v2.incident_reader import IncidentMember, IncidentOverview
from app.investigation_v2.program_start_api import create_app
from app.services.llm_resolver import LlmConfig
from app.services.llm_safety import safe_chat_completions_request

TENANT, INCIDENT, NOW = fixtures.TENANT, fixtures.INCIDENT, fixtures.NOW


def overview():
    return IncidentOverview(
        incident_id=INCIDENT, tenant_id=TENANT, title="Incident: script alert", severity="high",
        member_count=1, first_seen=NOW, last_seen=NOW, source_updated_at=NOW,
        by_status={"triaged": 1}, by_disposition={"needs_review": 1}, by_triage_verdict={},
        members_without_saved_triage=1, entities=[{"type": "host", "value": "host-01"}],
        mitre_tactics=[], mitre_techniques=[], members=[IncidentMember(
            alert_id=UUID(int=1), title="Script alert", severity="high", status="triaged",
            disposition="needs_review", event_time=NOW, updated_at=NOW, case_id=None,
            connector_id=None, source_alert_id="source-01", saved_analysis="Needs further evidence",
            triage=None, alert_url="/api/v1/alerts/example",
        )],
    )


def record_result(record):
    result = MagicMock()
    result.scalar_one_or_none.return_value = record
    return result


class IncidentSummaryExamples(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.db.__aenter__.return_value = self.db
        self.view = overview()
        self.record = summaries.IncidentSummaryRecord(tenant_id=TENANT, incident_id=INCIDENT)
        self.requests = []
        self.model_status = 200

        def provider(request):
            self.requests.append(json.loads(request.content))
            return httpx.Response(self.model_status, json={
                "choices": [{"message": {"content": f"Overview revision {len(self.requests)}"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 120, "completion_tokens": 20},
            })
        self.model_client = httpx.AsyncClient(transport=httpx.MockTransport(provider))
        self.addAsyncCleanup(self.model_client.aclose)
        async def complete(**kwargs):
            return await safe_chat_completions_request(**kwargs, client=self.model_client)
        self.config = patch.object(summaries, "resolve_llm_config", AsyncMock(return_value=LlmConfig(
            allowed=True, base_url="http://model.invalid/v1", model="example-summary-model",
            api_key="example-only", source="environment", reason="",
        )))
        self.model = patch.object(summaries, "safe_chat_completions_request", side_effect=complete)
        self.reader = patch.object(incident_api, "read_incident", AsyncMock(side_effect=lambda *a, **k: self.view))
        for patcher in (self.config, self.model, self.reader):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.app = create_app(start_gateway=object(), result_gateway=object())
        async def user():
            return CurrentUser(UUID(int=1), TENANT, "analyst", "example@invalid.test",
                               scopes=["alerts:read", "alerts:write"])
        async def session():
            yield self.db
        self.app.dependency_overrides[get_current_user] = user
        self.app.dependency_overrides[get_tenant_db] = session
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://incident.invalid",
                                        headers={"Authorization": "Bearer example-only"})
        self.addAsyncCleanup(self.client.aclose)
        self.path = f"/api/v2/investigation/incidents/{INCIDENT}"

    def generation_rows(self):
        self.db.execute.side_effect = [MagicMock(), record_result(self.record), MagicMock()]

    async def test_generate_read_stale_and_manual_refresh(self):
        self.generation_rows()
        response = await self.client.post(self.path + "/overview/refresh")
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["ai_overview"], "Overview revision 1")
        self.assertFalse(data["ai_overview_metadata"]["is_stale"])
        self.assertEqual(data["ai_overview_metadata"]["source_refs"]["member_ids"], [str(UUID(int=1))])
        self.assertTrue(data["ai_overview_metadata"]["last_usage"]["cost_recorded"])
        self.db.flush.assert_awaited()
        self.db.commit.assert_awaited_once()
        self.assertNotIn("tools", self.requests[0])
        material = json.loads(self.requests[0]["messages"][1]["content"])
        self.assertEqual(material["members"][0]["title"], "Script alert")
        self.assertEqual(material["investigation_results_status"], "not_linked")

        generated_at = data["ai_overview_metadata"]["generated_at"]
        self.view.members[0].disposition = "true_positive"
        self.view.source_updated_at = NOW + timedelta(minutes=3)
        self.db.execute.side_effect = [record_result(self.record)]
        data = (await self.client.get(self.path)).json()
        self.assertEqual(data["members"][0]["disposition"], "true_positive")
        self.assertEqual(data["ai_overview"], "Overview revision 1")
        self.assertEqual(data["ai_overview_metadata"]["generated_at"], generated_at)
        self.assertTrue(data["ai_overview_metadata"]["is_stale"])
        self.assertEqual(len(self.requests), 1)

        self.generation_rows()
        data = (await self.client.post(self.path + "/overview/refresh")).json()
        self.assertEqual(data["ai_overview"], "Overview revision 2")
        self.assertFalse(data["ai_overview_metadata"]["is_stale"])

    async def test_failed_refresh_preserves_old_text_and_initial_failure_is_visible(self):
        self.generation_rows()
        await self.client.post(self.path + "/overview/refresh")
        original_time = self.record.generated_at
        self.model_status = 500
        self.generation_rows()
        response = await self.client.post(self.path + "/overview/refresh")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["ai_overview"], "Overview revision 1")
        self.assertEqual(self.record.generated_at, original_time)
        self.assertEqual(data["ai_overview_metadata"]["last_attempt_status"], "failed")
        self.record = summaries.IncidentSummaryRecord(tenant_id=TENANT, incident_id=INCIDENT)
        self.generation_rows()
        data = (await self.client.post(self.path + "/overview/refresh")).json()
        self.assertIsNone(data["ai_overview"])
        self.assertEqual(data["ai_overview_metadata"]["last_error"], "model_call_failed")

    async def test_initial_job_finds_new_incident_and_does_not_regenerate(self):
        candidates = MagicMock()
        candidates.scalars.return_value.all.return_value = [str(INCIDENT)]
        self.db.execute.side_effect = [MagicMock(), candidates, MagicMock(), MagicMock(),
                                       record_result(self.record), MagicMock()]
        with patch.object(worker, "AsyncSessionLocal", return_value=self.db), \
             patch.object(worker, "read_incident", AsyncMock(return_value=self.view)):
            count = await worker.run_once(TENANT, NOW)
        self.assertEqual(count, 1)
        self.assertEqual(len(self.requests), 1)
        query = self.db.execute.await_args_list[1].args[0].compile(dialect=postgresql.dialect())
        self.assertIn(TENANT, query.params.values())
        self.assertIn(NOW, query.params.values())
        self.assertIn("min(alerts.created_at)", str(query))
        self.db.execute.side_effect = [MagicMock(), record_result(self.record)]
        await summaries.generate_summary(self.db, self.view, initial=True)
        self.assertEqual(len(self.requests), 1)

    async def test_material_exposes_partial_coverage(self):
        self.view.members = [self.view.members[0].model_copy(update={
            "alert_id": UUID(int=i + 1), "title": "Large title " * 1000,
        }) for i in range(60)]
        self.view.member_count = 60
        text, refs = summaries.summary_material(self.view)
        data = json.loads(text)
        self.assertLessEqual(len(text), summaries.MAX_MATERIAL_CHARS)
        self.assertGreater(refs["omitted_member_count"], 0)
        self.assertTrue(refs["fields_truncated"])
        self.assertEqual(refs["member_ids"], [member["alert_id"] for member in data["members"]])
