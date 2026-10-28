"""Direct F4 examples: ASGI routes and SQL substitutes, no external services."""
from datetime import timedelta
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import httpx
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

import test_investigation_incident_api as fixtures
from app.api.v1.deps import CurrentUser, get_current_user
from app.db.rls import get_tenant_db
from app.investigation_v2.case_analysis import CaseAnalysisRequest, case_context
from app.investigation_v2.case_analysis_api import create_app
from app.investigation_v2.case_links import CaseLinkRecord
from app.investigation_v2.program_result_api import create_app as combined_app
from app.models.case import Case

TENANT, INCIDENT, NOW = fixtures.TENANT, fixtures.INCIDENT, fixtures.NOW
CASE = UUID(int=30)


def result(one=None, rows=()):
    value = MagicMock()
    value.scalar_one_or_none.return_value = one
    value.one_or_none.return_value = one
    value.scalars.return_value.all.return_value = list(rows)
    value.mappings.return_value.all.return_value = list(rows)
    value.all.return_value = list(rows)
    return value


class CaseLinkExamples(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = MagicMock(spec=AsyncSession)
        self.db.execute, self.db.commit = AsyncMock(), AsyncMock()
        self.saved = []
        self.db.add.side_effect = self.saved.append
        async def user():
            return CurrentUser(UUID(int=5), TENANT, "analyst", "example@invalid.test",
                               scopes=["cases:write", "cases:read", "alerts:read"])
        async def session():
            yield self.db
        self.apps = [create_app(), combined_app(gateway=object())]
        for app in self.apps:
            app.dependency_overrides[get_current_user] = user
            app.dependency_overrides[get_tenant_db] = session
        self.client = self.client_for(self.apps[0])
        self.path = "/api/v2/investigation/case-links"

    def client_for(self, app):
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://case.invalid",
                                   headers={"Authorization": "Bearer example-only"})
        self.addAsyncCleanup(client.aclose)
        return client

    def body(self, members=(1, 2, 3), *, mode="create"):
        return {"operation_key": str(UUID(int=100)),
                "source": {"type": "incident", "incident_id": str(INCIDENT),
                           "alert_ids": [str(UUID(int=i)) for i in members]},
                "target": {"mode": "create", "title": "Investigate host activity"} if mode == "create"
                          else {"mode": "attach", "case_id": str(CASE)}}

    async def test_create_all_and_repeat_preserves_original_case_and_receipt(self):
        alerts = [fixtures.alert(1), fixtures.alert(2, severity="critical"), fixtures.alert(3)]
        self.db.execute.side_effect = [result(), result(), result(rows=alerts),
                                       result(rows=[a.id for a in alerts]), result()]
        response = await self.client.post(self.path, json=self.body((3, 1, 2)))
        self.assertEqual(response.status_code, 201, response.text)
        receipt = response.json()
        self.assertEqual(receipt["selection_kind"], "all_current")
        self.assertEqual(receipt["selected_member_ids"], [str(a.id) for a in alerts])
        self.assertNotIn("run_id", receipt)
        self.assertEqual(len(self.saved), 1)
        self.assertIsInstance(self.saved[0], CaseLinkRecord)
        self.assertEqual(self.saved[0].receipt, receipt)
        self.db.commit.assert_awaited_once()
        insert, params = self.db.execute.await_args_list[-1].args
        self.assertIn("INSERT INTO aisoc_cases", str(insert))
        self.assertEqual(params["severity"], "critical")
        self.assertEqual(params["members"], [a.id for a in alerts])
        self.assertEqual(params["tenant"], TENANT)
        self.assertTrue(all(a.case_id is None for a in alerts))

        self.db.execute.side_effect = [result(), result(self.saved[0])]
        repeated = await self.client.post(self.path, json=self.body())
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.json(), receipt)
        self.assertEqual(len(self.saved), 1)
        changed = self.body()
        changed["target"]["title"] = "A different investigation"
        self.db.execute.side_effect = [result(), result(self.saved[0])]
        conflict = await self.client.post(self.path, json=changed)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["detail"], "case_link_operation_conflict")

    async def test_attach_subset_and_pass_only_selected_members_to_case_analysis(self):
        alerts = [fixtures.alert(1), fixtures.alert(2)]
        self.db.execute.side_effect = [result(), result(),
            result(SimpleNamespace(id=CASE, status="new", alert_ids=[UUID(int=2), UUID(int=3)])),
            result(rows=alerts), result(rows=[UUID(int=i) for i in (1, 2, 3, 4)]), result()]
        response = await self.client_for(self.apps[1]).post(self.path, json=self.body((1, 2), mode="attach"))
        self.assertEqual(response.status_code, 201, response.text)
        receipt = response.json()
        self.assertEqual(receipt["case_id"], str(CASE))
        self.assertEqual(receipt["selection_kind"], "subset")
        self.assertEqual(receipt["added_member_ids"], [str(UUID(int=1))])
        self.assertEqual(receipt["already_linked_member_ids"], [str(UUID(int=2))])
        self.assertEqual(self.db.execute.await_args_list[-1].args[1]["members"], [UUID(int=i) for i in (1, 2, 3)])
        # The next existing F3 context builder consumes the returned selection,
        # rather than silently investigating all members of the attached Case.
        self.db.execute.side_effect = [result(Case(id=CASE, title="Existing", alert_ids=[UUID(int=i) for i in (1, 2, 3)])),
                                       result(rows=alerts), result(rows=[])]
        context = await case_context(self.db, TENANT, CASE, CaseAnalysisRequest(
            operation_key=UUID(int=101), start=NOW, end=NOW + timedelta(minutes=5),
            selected_member_ids=receipt["selected_member_ids"]))
        self.assertEqual(context["selected_member_ids"], receipt["selected_member_ids"])
        self.assertEqual(context["read_member_ids"], receipt["selected_member_ids"])
        self.assertNotIn(str(UUID(int=4)), context["all_member_ids"])

    async def test_invalid_source_or_closed_case_does_not_write_members(self):
        other = fixtures.alert(2)
        other.enrichment_data = {}
        for body, responses, code in (
            (self.body((1, 2)), [result(), result(), result(rows=[fixtures.alert(1), other]),
                                result(rows=[UUID(int=1)])], "incident_membership_changed"),
            (self.body((1,), mode="attach"), [result(), result(),
                result(SimpleNamespace(status="closed", alert_ids=[]))], "case_not_open"),
            (self.body((1,)), [result(), result(), result(rows=[])], "alert_not_found"),
        ):
            self.db.execute.side_effect = responses
            response = await self.client.post(self.path, json=body)
            self.assertEqual(response.status_code, 404 if code == "alert_not_found" else 409, response.text)
            self.assertEqual(response.json()["detail"], code)
        duplicate = self.body((1, 1))
        self.assertEqual((await self.client.post(self.path, json=duplicate)).status_code, 422)
        self.assertEqual(self.saved, [])
        self.db.commit.assert_not_awaited()

    async def test_alert_entry_and_link_history_pagination_are_scoped_reads(self):
        body = self.body((1,))
        body["source"] = {"type": "alerts", "alert_ids": [str(UUID(int=1))]}
        self.db.execute.side_effect = [result(), result(), result(rows=[fixtures.alert(1)]), result()]
        created = await self.client.post(self.path, json=body)
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["selection_kind"], "explicit_alerts")
        self.assertEqual(created.json()["source_incident_ids"], [str(INCIDENT)])
        first = self.saved[0]
        second = CaseLinkRecord(link_id=UUID(int=600), case_id=CASE, created_at=NOW, receipt={
            **first.receipt, "link_id": str(UUID(int=600)), "case_id": str(CASE), "created_at": NOW.isoformat()})
        self.db.execute.side_effect = [result(rows=[first, second]), result(rows=[second])]
        page = await self.client.get(self.path, params={"incident_id": str(INCIDENT), "limit": 1})
        self.assertEqual(page.status_code, 200, page.text)
        self.assertEqual(page.json()["items"][0]["link_id"], str(first.link_id))
        cursor = page.json()["next_cursor"]
        next_page = await self.client.get(self.path, params={"incident_id": str(INCIDENT), "limit": 1, "cursor": cursor})
        self.assertEqual(next_page.json()["items"][0]["link_id"], str(second.link_id))
        self.assertIsNone(next_page.json()["next_cursor"])
        sql = self.db.execute.await_args_list[-1].args[0].compile(dialect=postgresql.dialect())
        self.assertIn(TENANT, sql.params.values())
        self.assertIn([INCIDENT], sql.params.values())
        self.assertIn("created_at, investigation_case_links.link_id) <", str(sql))
        self.assertEqual((await self.client.get(self.path)).status_code, 422)
        self.assertEqual((await self.client.get(self.path, params={"alert_id": str(UUID(int=1)), "cursor": cursor})).status_code, 422)
        self.db.execute.side_effect = [result(rows=[])]
        empty = await self.client.get(self.path, params={"alert_id": str(UUID(int=1))})
        self.assertEqual(empty.json(), {"items": [], "next_cursor": None})

    async def test_case_history_shows_running_and_finished_without_full_reports(self):
        rows = [{"run_id": UUID(int=700), "started_at": NOW, "completed_at": None, "status": "running",
                 "scope": {"selected_member_ids": [str(UUID(int=1))]}, "stop_reason": None, "completion": None},
                {"run_id": UUID(int=701), "started_at": NOW - timedelta(minutes=1), "completed_at": NOW,
                 "status": "completed", "scope": {}, "stop_reason": "analysis_complete", "completion": "partial"}]
        self.db.execute.side_effect = [result(CASE), result(rows=rows), result(CASE), result(rows=rows[1:])]
        path = f"/api/v2/investigation/cases/{CASE}/investigations"
        page = await self.client.get(path, params={"limit": 1})
        self.assertEqual(page.status_code, 200, page.text)
        self.assertIsNone(page.json()["items"][0]["completion"])
        next_page = await self.client.get(path, params={"limit": 1, "cursor": page.json()["next_cursor"]})
        self.assertEqual(next_page.json()["items"][0]["completion"], "partial")
        self.assertNotIn("markdown", next_page.json()["items"][0])
        sql = self.db.execute.await_args_list[-1].args[0].compile(dialect=postgresql.dialect())
        self.assertIn("case_analysis.v1", sql.params.values())
        self.assertIn(TENANT, sql.params.values())
        self.assertIn(str(CASE), sql.params.values())
        self.db.execute.side_effect = [result()]
        self.assertEqual((await self.client.get(path)).status_code, 404)
        self.db.commit.assert_not_awaited()
