"""Baseline readers and claim protocol; model/lake/database are explicit substitutes."""
from datetime import timedelta
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch
from uuid import UUID

import test_case_analysis_api as examples
from app.investigation_v2 import case_analysis as analysis
from app.models.investigation import InvestigationRun
from sqlalchemy.dialects import postgresql

CASE, TENANT, NOW = examples.CASE, examples.TENANT, examples.NOW
BASELINE = UUID(int=700)


class BaselineAPIExamples(IsolatedAsyncioTestCase):
    asyncSetUp = examples.CaseAnalysisExamples.asyncSetUp
    add = examples.CaseAnalysisExamples.add
    report_provider = examples.CaseAnalysisExamples.report_provider

    async def execute(self, statement, params=None):
        values = statement.compile().params
        # The original fixture only looks up an id, so it would return the
        # excluded pending Run as an active result for an `id !=` query.
        if any(isinstance(v, (tuple, list)) and "running" in v for v in values.values()):
            self.statements.append(statement)
            active = next((run.id for run in self.runs.values()
                           if run.status in analysis.ACTIVE_STATUSES and run.id != values.get("id_1")
                           and run.tenant_id == TENANT and run.case_id == str(CASE)), None)
            return examples.result(active)
        return await examples.CaseAnalysisExamples.execute(self, statement, params)

    def pending(self, *, revision=2, members=None):
        members = [str(UUID(int=1))] if members is None else members
        run = InvestigationRun(id=BASELINE, tenant_id=TENANT, case_id=str(CASE),
            investigation_kind="baseline", scope_revision=revision, scope_updated_at=NOW,
            status="pending_update", started_at=None, created_at=NOW,
            raw_alert={"analysis_profile": analysis.PROFILE,
                "scope": {"all_member_ids": members, "selected_member_ids": members, "read_member_ids": []},
                "baseline": {"schema": "case.baseline.v1", "initial_member_ids": [],
                    "added_member_ids": members, "removed_member_ids": [],
                    "trigger": "members_changed", "requested_at": NOW.isoformat(), "updated_at": NOW.isoformat()}})
        self.runs[BASELINE] = run
        return run

    def body(self, revision=2):
        return {"expected_scope_revision": revision, "start": NOW.isoformat(),
                "end": (NOW + timedelta(minutes=5)).isoformat()}

    async def start_baseline(self, body=None, identity=BASELINE):
        return await self.client.post(self.path + f"/investigations/{identity}/start", json=body or self.body())

    async def test_pending_is_readable_without_execution_or_result(self):
        self.pending()
        response = await self.client.get(self.path + f"/investigations/{BASELINE}")
        self.assertEqual(response.status_code, 200, response.text)
        item = response.json()
        self.assertEqual(item["status"], "pending_update")
        self.assertEqual(item["scope_revision"], 2)
        self.assertIsNone(item["started_at"])
        self.assertIsNone(item["result"])
        self.assertTrue(item["can_start_baseline"])
        self.assertEqual(item["progress"], [])
        self.config.assert_not_awaited()
        self.lake.assert_not_awaited()
        self.db.commit.assert_not_awaited()

    async def test_stale_scope_revision_cannot_start_or_overwrite_pending(self):
        run = self.pending()
        response = await self.start_baseline(self.body(1))
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"], "baseline_scope_revision_conflict")
        self.assertEqual(run.status, "pending_update")
        self.assertIsNone(run.started_at)
        self.db.commit.assert_not_awaited()
        self.config.assert_not_awaited()
        statements = [str(s.compile(dialect=postgresql.dialect())) for s in self.statements]
        self.assertIn("aisoc_cases", statements[0])
        self.assertIn("FOR UPDATE", statements[0])
        self.assertIn("investigation_runs", statements[1])
        self.assertIn("FOR UPDATE", statements[1])

    async def test_starts_existing_identity_and_repeat_reads_same_execution(self):
        run = self.pending()
        original_baseline = dict(run.raw_alert["baseline"])
        response = await self.start_baseline()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["run_id"], str(BASELINE))
        self.assertEqual(set(self.runs), {BASELINE})
        self.assertIsNotNone(run.started_at)
        self.assertEqual(run.status, "completed")
        self.assertEqual(run.scope_revision, 2)
        self.assertEqual(run.raw_alert["baseline"], original_baseline)
        self.assertEqual(run.raw_alert["scope"]["read_member_ids"], [str(UUID(int=1))])
        calls, events = len(self.messages), len(self.events)
        again = await self.start_baseline()
        self.assertEqual(again.status_code, 200, again.text)
        self.assertEqual(again.json()["result"], response.json()["result"])
        self.assertEqual((len(self.messages), len(self.events)), (calls, events))
        self.assertEqual(run.created_at, NOW)

    async def test_started_record_rejects_different_start_parameters(self):
        self.pending()
        self.assertEqual((await self.start_baseline()).status_code, 200)
        body = self.body()
        body["question"] = "Different question"
        calls = len(self.messages)
        response = await self.start_baseline(body)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(len(self.messages), calls)

    async def test_running_claim_is_committed_before_executor_first_step(self):
        run = self.pending()

        async def before_first_step():
            self.db.commit.assert_awaited_once()
            self.assertEqual(run.status, "running")
            self.assertIsNotNone(run.started_at)
            self.assertEqual(run.raw_alert["scope"]["selected_member_ids"], [str(UUID(int=1))])
            self.config.assert_not_awaited()
            self.lake.assert_not_awaited()
            return {"run_id": str(run.id), "status": run.status}

        with patch.object(analysis.CaseAnalysis, "execute", AsyncMock(side_effect=before_first_step)) as executor:
            response = await self.start_baseline()
            self.assertEqual(response.status_code, 200, response.text)
            executor.assert_awaited_once()

    async def test_failed_claim_commit_never_calls_executor(self):
        self.pending()
        self.db.commit.side_effect = RuntimeError("test claim commit failed")
        with patch.object(analysis.CaseAnalysis, "execute", AsyncMock()) as executor:
            with self.assertRaisesRegex(RuntimeError, "test claim commit failed"):
                await self.start_baseline()
            executor.assert_not_awaited()
        self.config.assert_not_awaited()
        self.lake.assert_not_awaited()

    async def test_pending_scope_must_match_current_full_members(self):
        run = self.pending()
        self.case.alert_ids = [UUID(int=1), UUID(int=2)]
        response = await self.start_baseline()
        self.assertEqual(response.json()["detail"], "baseline_scope_membership_conflict")
        run.raw_alert["scope"]["selected_member_ids"] = [str(i) for i in self.case.alert_ids]
        response = await self.start_baseline({**self.body(), "selected_member_ids": [str(UUID(int=1))]})
        self.assertEqual(response.json()["detail"], "baseline_requires_full_prepared_scope")
        self.config.assert_not_awaited()
        self.db.commit.assert_not_awaited()

    async def test_empty_scope_is_visible_but_not_startable(self):
        self.pending(members=[])
        self.case.alert_ids = []
        response = await self.client.get(self.path + f"/investigations/{BASELINE}")
        self.assertFalse(response.json()["can_start_baseline"])
        response = await self.start_baseline()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "baseline_scope_empty")
        self.config.assert_not_awaited()

    async def test_baseline_cannot_be_claimed_through_another_case(self):
        run = self.pending()
        run.case_id = str(UUID(int=99))
        response = await self.start_baseline()
        self.assertEqual(response.status_code, 404)
        self.config.assert_not_awaited()
        self.db.commit.assert_not_awaited()

    async def test_an_active_case_execution_blocks_baseline_claim(self):
        run = self.pending()
        original = self.execute

        async def with_active(statement, params=None):
            compiled = statement.compile().params
            if any(isinstance(v, (tuple, list)) and "running" in v for v in compiled.values()):
                return examples.result(UUID(int=800))
            return await original(statement, params)

        self.db.execute.side_effect = with_active
        response = await self.start_baseline()
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"], "case_investigation_already_active")
        self.assertEqual(run.status, "pending_update")
        self.db.commit.assert_not_awaited()
        self.config.assert_not_awaited()

    async def test_start_requires_revision_and_execution_permission(self):
        self.pending()
        response = await self.start_baseline({"start": NOW.isoformat(), "end": (NOW + timedelta(minutes=5)).isoformat()})
        self.assertEqual(response.status_code, 422)
        from app.api.v1.deps import CurrentUser, get_current_user
        async def reader():
            return CurrentUser(UUID(int=1), TENANT, "analyst", "example@invalid.test", scopes=["cases:read", "alerts:read"])
        self.client._transport.app.dependency_overrides[get_current_user] = reader
        response = await self.start_baseline()
        self.assertEqual(response.status_code, 403)
        self.config.assert_not_awaited()
