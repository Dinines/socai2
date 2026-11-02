"""Direct Alert/Incident examples using the actual ASGI and summary protocol."""
from datetime import timedelta
import json
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import httpx
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

import test_investigation_incident_api as fixtures
from app.api.v1.deps import CurrentUser, get_current_user
from app.db.rls import get_tenant_db
from app.investigation_v2.application import create_app
from app.investigation_v2 import incident_summary as summaries
from app.services.llm_resolver import LlmConfig
from app.services.llm_safety import safe_chat_completions_request

TENANT, INCIDENT, NOW = fixtures.TENANT, fixtures.INCIDENT, fixtures.NOW
CASE, RUN = UUID(int=30), UUID(int=1000)


def result(one=None, rows=()):
    value = MagicMock()
    value.scalar_one_or_none.return_value = one
    value.all.return_value = list(rows)
    value.scalars.return_value.all.return_value = list(rows)
    value.mappings.return_value.all.return_value = list(rows)
    return value


def run_row(number=1000, members=(1, 2), *, status="completed"):
    return {"run_id": UUID(int=number), "case_id": str(CASE), "status": status,
            "started_at": NOW - timedelta(minutes=number - 1000), "completed_at": NOW if status == "completed" else None,
            "scope": {"selected_member_ids": [str(UUID(int=i)) for i in members],
                      "read_member_ids": [str(UUID(int=i)) for i in members], "all_member_ids": [str(UUID(int=i)) for i in (1, 2, 3)],
                      "start": (NOW - timedelta(hours=1)).isoformat(), "end": NOW.isoformat()},
            "previous_run_id": None, "source_incident_ids": [str(INCIDENT)],
            "result_available": status == "completed", "stop_reason": "analysis_complete" if status == "completed" else None,
            "completion": "partial" if status == "completed" else None,
            "summary": "进程与外联同时出现，缺少父进程链。" if status == "completed" else None,
            "summary_truncated": False}


class RelatedInvestigationExamples(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = MagicMock(spec=AsyncSession)
        self.db.execute, self.db.commit, self.db.flush = AsyncMock(), AsyncMock(), AsyncMock()
        app = create_app()
        async def user():
            return CurrentUser(UUID(int=5), TENANT, "analyst", "example@invalid.test",
                               scopes=["alerts:read", "alerts:write", "cases:read"])
        async def session():
            yield self.db
        app.dependency_overrides[get_current_user] = user
        app.dependency_overrides[get_tenant_db] = session
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://investigation.invalid",
                                       headers={"Authorization": "Bearer example-only"})
        self.addAsyncCleanup(self.client.aclose)
        self.incident_path = f"/api/v2/investigation/incidents/{INCIDENT}"
        self.case = SimpleNamespace(id=CASE, title="Host activity", status="investigating",
                                    alert_ids=[UUID(int=i) for i in (1, 2, 3)])

    def relation_rows(self, rows=None, covered=(1, 2)):
        return [result(rows=[self.case]), result(rows=[run_row()] if rows is None else rows),
                result(rows=[str(UUID(int=i)) for i in covered])]

    def incident_rows(self, count=3):
        return [result(rows=[fixtures.alert(i) for i in range(1, count + 1)]),
                result(rows=[fixtures.verdict(1, "Needs more evidence")])]

    async def test_alert_distinguishes_related_case_from_actual_run_selection(self):
        path = "/api/v2/investigation/alerts/{}/investigation-context"
        self.db.execute.side_effect = [result(fixtures.alert(1)), result(rows=[fixtures.verdict(1, "Needs review")]),
                                       *self.relation_rows(covered=(1,))]
        response = await self.client.get(path.format(UUID(int=1)))
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertIsNone(data["source"]["source_alert_id"])
        self.assertEqual(data["source"]["external_id"], "source-1")
        self.assertEqual(data["incident_url"], self.incident_path)
        self.assertEqual(data["triage"]["rationale"], "Needs review")
        item = data["investigations"]["items"][0]
        self.assertEqual(item["matched_member_ids"], [str(UUID(int=1))])
        self.assertEqual(item["scope"]["selected_member_ids"], [str(UUID(int=i)) for i in (1, 2)])
        self.assertIn(str(RUN), item["report_url"])
        query = self.db.execute.await_args_list[3].args[0].compile(dialect=postgresql.dialect())
        self.assertIn(TENANT, query.params.values())
        self.assertIn("case_analysis.v1", query.params.values())
        self.assertIn("selected_member_ids", query.params.values())
        self.assertIn("?|", str(query))

        self.db.execute.side_effect = [result(fixtures.alert(3)), result(rows=[fixtures.verdict(3, "Only triaged")]),
                                       *self.relation_rows(rows=[], covered=())]
        data = (await self.client.get(path.format(UUID(int=3)))).json()
        self.assertEqual(data["investigations"]["cases"][0]["case_id"], str(CASE))
        self.assertEqual(data["investigations"]["items"], [])
        self.assertEqual(data["investigations"]["member_ids_without_runs"], [str(UUID(int=3))])
        self.db.commit.assert_not_awaited()

    async def test_incident_new_member_and_paging_preserve_run_scope_and_full_coverage(self):
        self.db.execute.side_effect = [*self.incident_rows(), *self.relation_rows()]
        data = (await self.client.get(self.incident_path + "/investigations")).json()
        self.assertEqual(data["member_ids_without_runs"], [str(UUID(int=3))])
        self.db.execute.side_effect = [*self.incident_rows(4), *self.relation_rows()]
        later = (await self.client.get(self.incident_path + "/investigations")).json()
        self.assertEqual(later["items"][0]["scope"], data["items"][0]["scope"])
        self.assertEqual(later["member_ids_without_runs"], [str(UUID(int=i)) for i in (3, 4)])

        older = run_row(1001, (3,), status="running")
        self.db.execute.side_effect = [*self.incident_rows(), *self.relation_rows([run_row(), older], covered=(1, 2, 3))]
        page = (await self.client.get(self.incident_path + "/investigations", params={"limit": 1})).json()
        self.assertEqual(len(page["items"]), 1)
        self.assertEqual(page["member_ids_without_runs"], [])  # Third member has a Run outside this page.
        self.db.execute.side_effect = [*self.incident_rows(), *self.relation_rows([older], covered=(1, 2, 3))]
        page2 = (await self.client.get(self.incident_path + "/investigations", params={"limit": 1, "cursor": page["next_cursor"]})).json()
        self.assertEqual(page2["items"][0]["status"], "running")
        self.assertFalse(page2["items"][0]["result_available"])
        self.assertIsNone(page2["items"][0]["summary"])
        self.assertIsNone(page2["next_cursor"])
        self.db.commit.assert_not_awaited()

    async def test_manual_overview_uses_saved_case_summary_then_get_only_marks_stale(self):
        record = summaries.IncidentSummaryRecord(tenant_id=TENANT, incident_id=INCIDENT)
        requests = []
        def provider(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={"choices": [{"message": {"content": "两条成员已有调查，其他成员尚待核对。"}, "finish_reason": "stop"}],
                                            "usage": {"prompt_tokens": 100, "completion_tokens": 30}})
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as model_client:
            async def complete(**kwargs):
                return await safe_chat_completions_request(**kwargs, client=model_client)
            with patch.object(summaries, "resolve_llm_config", AsyncMock(return_value=LlmConfig(
                True, "http://model.invalid/v1", "example-summary", "example-only", "environment", ""))), \
                 patch.object(summaries, "safe_chat_completions_request", side_effect=complete):
                self.db.execute.side_effect = [*self.incident_rows(), result(), result(record),
                                               *self.relation_rows(), result()]
                response = await self.client.post(self.incident_path + "/overview/refresh", params={"include_investigations": "true"})
                self.assertEqual(response.status_code, 200, response.text)
                data = response.json()
                self.assertFalse(data["ai_overview_metadata"]["is_stale"])
                refs = data["ai_overview_metadata"]["source_refs"]
                self.assertEqual(refs["investigation_run_ids"], [str(RUN)])
                self.assertEqual(refs["investigation_scopes"][str(RUN)], run_row()["scope"])
                material = json.loads(requests[0]["messages"][1]["content"])
                self.assertEqual(material["case_results"][0]["summary"], run_row()["summary"])
                self.assertEqual(material["case_results"][0]["matched_member_ids"], [str(UUID(int=i)) for i in (1, 2)])
                self.assertNotIn("tools", requests[0])
                self.assertNotIn("markdown", material["case_results"][0])
                self.db.execute.side_effect = [*self.incident_rows(4), result(record), *self.relation_rows()]
                later = (await self.client.get(self.incident_path)).json()
                self.assertEqual(later["ai_overview"], data["ai_overview"])
                self.assertTrue(later["ai_overview_metadata"]["is_stale"])
                self.assertEqual(later["investigations"]["member_ids_without_runs"], [str(UUID(int=i)) for i in (3, 4)])
                self.assertEqual(len(requests), 1)
