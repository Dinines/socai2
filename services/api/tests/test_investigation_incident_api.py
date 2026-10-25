"""Direct functional examples for incident membership and triage display."""
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import httpx
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.api.v1.deps import CurrentUser, get_current_user
from app.db.rls import get_tenant_db
from app.investigation_v2.program_start_api import create_app
from app.models.alert import Alert
from app.models.investigation import InvestigationEvent

TENANT, INCIDENT = UUID(int=10), UUID(int=20)
NOW = datetime(2026, 10, 25, 10, tzinfo=UTC)


def alert(number, *, status="triaged", disposition="needs_review", severity="high"):
    return Alert(
        id=UUID(int=number), tenant_id=TENANT, title=f"Alert {number}", severity=severity,
        status=status, disposition=disposition, event_time=NOW, first_seen=NOW, last_seen=NOW,
        updated_at=NOW, case_id=None, connector_id=None, external_id=f"source-{number}",
        ai_summary="Saved alert analysis", ai_recommendations=[],
        affected_hosts=["host-01"], affected_users=[], affected_ips=["192.0.2.1"],
        entities=[{"type": "host", "value": "host-01"}], mitre_tactics=["execution"],
        mitre_techniques=["T1059"], enrichment_data={"socai2_fusion": {"incident_id": str(INCIDENT)}},
    )


def verdict(number, reason, *, auto_closed=False, at=NOW, decision="needs_review"):
    return (str(UUID(int=number)), InvestigationEvent(
        id=UUID(int=100 + number), run_id=UUID(int=200 + number), tenant_id=TENANT,
        ts=at, kind="triage_verdict", agent="auto_triage:deterministic", summary=reason,
        payload={"verdict": decision, "rationale": reason, "auto_closed": auto_closed,
                 "findings": [reason], "proposed_actions": []},
    ))


class IncidentAPIExamples(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.app = create_app(start_gateway=object(), result_gateway=object())
        async def current_user():
            return CurrentUser(UUID(int=1), TENANT, "analyst", "example@invalid.test", scopes=["alerts:read"])
        async def session():
            yield self.db
        self.app.dependency_overrides[get_current_user] = current_user
        self.app.dependency_overrides[get_tenant_db] = session
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://incident.invalid")
        self.addAsyncCleanup(self.client.aclose)

    def rows(self, members, verdicts):
        alerts_result, triage_result = MagicMock(), MagicMock()
        alerts_result.scalars.return_value.all.return_value = members
        triage_result.all.return_value = verdicts
        self.db.execute.side_effect = [alerts_result, triage_result]

    async def get(self):
        return await self.client.get(f"/api/v2/investigation/incidents/{INCIDENT}",
                                     headers={"Authorization": "Bearer example-only"})

    async def test_pending_closed_and_in_progress_members_keep_their_own_reasons(self):
        self.rows([alert(1), alert(2, status="resolved", disposition="false_positive"),
                   alert(3, status="in_progress", disposition="true_positive", severity="critical")],
                  [verdict(1, "Needs more evidence"), verdict(2, "Approved test activity", auto_closed=True,
                   decision="false_positive"), verdict(3, "Investigating suspicious activity", decision="true_positive")])
        response = await self.get()
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["member_count"], 3)
        self.assertEqual(data["by_status"], {"triaged": 1, "resolved": 1, "in_progress": 1})
        self.assertEqual([row["alert_id"] for row in data["members"]], [str(UUID(int=n)) for n in (1, 2, 3)])
        self.assertEqual([row["triage"]["rationale"] for row in data["members"]],
                         ["Needs more evidence", "Approved test activity", "Investigating suspicious activity"])
        self.assertTrue(data["members"][1]["triage"]["auto_closed"])
        self.assertEqual(data["severity"], "critical")
        self.assertIsNone(data["handling_status"])
        self.assertIsNone(data["ai_overview"])
        self.assertEqual(data["entities"], [{"type": "host", "value": "host-01"}, {"type": "ip", "value": "192.0.2.1"}])
        statements = [call.args[0].compile(dialect=postgresql.dialect()) for call in self.db.execute.await_args_list]
        self.assertIn(str(INCIDENT), statements[0].params.values())
        for query in statements:
            self.assertIn(TENANT, query.params.values())
        self.assertIn("raw_alert", str(statements[1]))
        self.assertNotIn("case_id", str(statements[1]))
        self.db.commit.assert_not_awaited()

    async def test_new_read_shows_new_triage_and_current_disposition_separately(self):
        member = alert(1)
        self.rows([member], [verdict(1, "Initial assessment")])
        self.assertEqual((await self.get()).json()["members"][0]["triage"]["rationale"], "Initial assessment")
        member.disposition = "benign_true_positive"
        later = NOW + timedelta(minutes=2)
        self.rows([member], [verdict(1, "New evidence", at=later, decision="true_positive"),
                             verdict(1, "Initial assessment")])
        data = (await self.get()).json()
        self.assertEqual(data["members"][0]["disposition"], "benign_true_positive")
        self.assertEqual(data["members"][0]["triage"]["verdict"], "true_positive")
        self.assertEqual(data["source_updated_at"], later.isoformat().replace("+00:00", "Z"))
        self.assertEqual(data["by_triage_verdict"], {"true_positive": 1})

    async def test_saved_alert_analysis_does_not_invent_a_triage_or_run_link(self):
        self.rows([alert(1, status="new", disposition=None)], [])
        data = (await self.get()).json()
        self.assertEqual(data["members_without_saved_triage"], 1)
        self.assertEqual(data["members"][0]["saved_analysis"], "Saved alert analysis")
        self.assertIsNone(data["members"][0]["triage"])
        self.assertEqual(data["by_disposition"], {"unassessed": 1})

    async def test_no_persisted_members_returns_not_found(self):
        self.rows([], [])
        response = await self.get()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.db.execute.await_count, 1)
