"""M6.2b1 actual stores and M3 engine; SQL double, no real database or HTTP."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
import sys
import unittest
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.execution_state import ExecutionRejected, OpeningUsage
from app.investigation_v2.execution_store import ExecutionStore, ExecutionPersistenceError
from app.investigation_v2.recon_runtime_store import ReconExecutionStore, HANDOFF_KIND, OBSERVATION_KIND
from test_recon_runtime_state_contract import managed, reservation, OWNER, START
from test_evidence_view_contract import query
from _recon_memory_ledger import MemoryLedger


class ReconRuntimeStoreContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pure, self.request = managed()
        self.ledger = MemoryLedger(run_id=self.request.context.run_id, tenant_id=self.request.context.tenant_id, now=START)
        self.store = ReconExecutionStore(self.ledger, tenant_id=self.request.context.tenant_id,
                                         run_id=self.request.context.run_id, executor_id=OWNER)
        from app.investigation_v2.execution_state import BudgetLimits
        limits = dict(self.pure["limits"]);limits.pop("currency");limits["deadline"] = datetime.fromisoformat(limits["deadline"])
        self.limits = BudgetLimits(**limits)
        self.opening = OpeningUsage(**self.pure["opening_usage"])

    async def begin(self, **kwargs):
        return await self.store.begin_recon(request=self.request, limits=kwargs.get("limits", self.limits), opening=self.opening)

    async def reserve(self):
        state = await self.store.load()
        return await self.store.reserve(scope_hash=state["scope_hash"], input_data=state["recon"]["plan"]["query_input"],
                                        **reservation(state))

    def payload(self):
        value = query()
        value["caller_receipt"]["run_id"] = str(self.request.context.run_id)
        return value

    async def completed(self, *, outcome="responded", output=None):
        await self.begin();await self.store.claim(self.request);await self.reserve()
        state = await self.store.load()
        attempt = state["recon"]["plan"]["attempt_id"]
        return await self.store.complete(attempt_id=attempt, output_data=self.payload() if output is None else output,
                                         outcome=outcome, actual_tokens=None if outcome == "unknown" else 0,
                                         actual_cost_microusd=None if outcome == "unknown" else 0,
                                         usage_source_ref="synthetic-store-test-no-model")

    async def test_begin_freezes_input_and_refuses_reuse_or_generic_begin(self):
        saved = await self.begin()
        self.assertEqual((len(self.ledger.events), len(self.ledger.artifacts)), (1, 2))
        body = json.loads(self.ledger.artifacts[UUID(saved["receipt"]["body_artifact_id"])]["content"])
        self.assertEqual(body["input"]["runtime_plan"], saved["state"]["recon"]["plan"])
        with self.assertRaises(ExecutionRejected): await self.begin()
        with self.assertRaisesRegex(ExecutionRejected, "versioned begin"):
            await self.store.begin(scope=self.request.context, limits=self.limits, opening=self.opening, input_data={})

    async def test_two_claims_yield_only_one_first_dispatch_decision(self):
        import asyncio
        await self.begin()
        results = await asyncio.gather(self.store.claim(self.request), self.store.claim(self.request))
        self.assertEqual(sorted(x["decision"]["action"] for x in results), ["dispatch_after_commit", "in_progress_or_interrupted"])
        self.assertEqual((len(self.ledger.events), len(self.ledger.artifacts)), (2, 4))
        self.assertEqual((await self.store.load())["stage_usage"]["tool_calls"], 0)

    async def test_claim_rollback_or_lost_ack_never_returns_a_new_dispatch_decision(self):
        await self.begin()
        self.ledger.fail_kind = "unified_state_snapshot"
        with self.assertRaises(ExecutionPersistenceError): await self.store.claim(self.request)
        self.assertEqual((len(self.ledger.events), len(self.ledger.artifacts)), (1, 2))
        self.assertEqual((await self.store.load())["recon"]["phase"], "ready")
        self.ledger.fail_kind = None
        self.ledger.fail_after_commit = True
        with self.assertRaises(ExecutionPersistenceError): await self.store.claim(self.request)
        repeated = await self.store.claim(self.request)
        self.assertEqual(repeated["decision"]["action"], "in_progress_or_interrupted")
        self.assertFalse(repeated["decision"]["needs_commit"])

    async def test_finished_run_and_preexisting_generic_stage_cannot_be_adopted(self):
        self.ledger.run.update(status="completed", completed_at=START)
        with self.assertRaisesRegex(ExecutionRejected, "fresh running"):
            await self.begin()
        self.assertEqual(self.ledger.events, [])
        self.ledger.run.update(status="running", completed_at=None)
        generic = ExecutionStore(self.ledger, tenant_id=self.store.tenant_id, run_id=self.store.run_id, executor_id=OWNER)
        await generic.begin(scope=self.request.context, limits=self.limits, opening=self.opening, input_data={"synthetic": True})
        with self.assertRaisesRegex(ExecutionRejected, "runtime version"):
            await self.store.load()
        with self.assertRaisesRegex(ExecutionRejected, "already began"):
            await self.begin()

    async def test_zero_query_budget_yields_a_saved_stop_without_any_attempt(self):
        await self.begin(limits=replace(self.limits, max_tool_calls=0))
        claimed = await self.store.claim(self.request)
        self.assertEqual(claimed["decision"]["action"], "finalize_blocked")
        saved = await self.store.finalize(self.request)
        self.assertEqual(saved["candidate"]["result"]["stop_reason"], "budget_limit")
        self.assertEqual(saved["candidate"]["result"]["facts"], [])
        self.assertEqual(saved["state"]["attempts"], {})

    async def test_reservation_is_frozen_and_generic_store_cannot_take_over(self):
        await self.begin();await self.store.claim(self.request)
        state = await self.store.load();wrong = reservation(state);wrong["attempt_id"] = str(UUID(int=444))
        with self.assertRaises(ExecutionRejected):
            await self.store.reserve(scope_hash=state["scope_hash"], input_data=state["recon"]["plan"]["query_input"], **wrong)
        self.assertEqual(len(self.ledger.events), 2)
        await self.reserve()
        generic = ExecutionStore(self.ledger, tenant_id=self.store.tenant_id, run_id=self.store.run_id, executor_id=OWNER)
        with self.assertRaisesRegex(ExecutionRejected, "runtime version"):
            await generic.load()

    async def test_cold_read_and_repeated_finalize_keep_one_owned_handoff(self):
        baseline = deepcopy(self.ledger.run)
        await self.completed()
        saved = await self.store.finalize(self.request)
        self.assertEqual(saved["retention"], "committed")
        self.assertEqual(saved["candidate"]["result"]["scope_readiness"], "ready")
        self.assertEqual((len(self.ledger.events), len(self.ledger.artifacts)), (5, 10))
        cold = ReconExecutionStore(self.ledger, tenant_id=self.store.tenant_id, run_id=self.store.run_id, executor_id=OWNER)
        read = await cold.read_handoff(self.request)
        again = await cold.finalize(self.request)
        self.assertEqual(saved["candidate"], read["candidate"])
        self.assertEqual(saved["candidate"], again["candidate"])
        self.assertEqual((len(self.ledger.events), len(self.ledger.artifacts)), (5, 10))
        self.assertEqual(self.ledger.run, baseline)
        with self.assertRaises(ExecutionRejected): await cold.finalize(self.request, observed_tool_output={"changed": True})

    async def test_unknown_completion_keeps_its_budget_and_source_execution_state(self):
        output = dict(tool="activity_records", status="error", reason="dispatch_TimeoutError", caller_receipt={"http_attempted": None})
        await self.completed(outcome="unknown", output=output)
        saved = await self.store.finalize(self.request)
        self.assertEqual(saved["state"]["stage_usage"]["unsettled_attempts"], 1)
        self.assertEqual(saved["candidate"]["result"]["stop_reason"], "unknown_attempt")
        self.assertEqual(saved["candidate"]["preparation"]["evidence_document"]["model_view"]["query"]["execution_state"], "unknown")
        self.assertEqual((await self.store.claim(self.request))["decision"]["action"], "read_handoff")

    async def test_unconfirmed_observation_is_saved_but_not_adopted_as_completion(self):
        await self.begin();await self.store.claim(self.request);await self.reserve()
        saved = await self.store.finalize(self.request, observed_tool_output=self.payload())
        candidate = saved["candidate"]
        reference = candidate["unconfirmed_observation_ref"]
        artifact = self.ledger.artifacts[UUID(reference["artifact_id"])]
        self.assertEqual(artifact["kind"], OBSERVATION_KIND)
        self.assertEqual(json.loads(artifact["content"])["tool_result"], self.payload())
        self.assertIsNone(candidate["preparation"])
        self.assertEqual(candidate["result"]["facts"], [])
        self.assertEqual(candidate["result"]["validated_source_refs"], [])
        self.assertEqual(saved["state"]["stage_usage"]["unsettled_attempts"], 1)
        self.assertEqual((len(self.ledger.events), len(self.ledger.artifacts)), (4, 9))
        again = await self.store.finalize(self.request, observed_tool_output=self.payload())
        self.assertTrue(again["repeated"])

    async def test_semantically_rejected_source_keeps_owned_raw_artifact_without_facts(self):
        output = self.payload();output["rows"][0]["raw_payload"]["sha256"] = "0" * 64
        completed = await self.completed(output=output)
        saved = await self.store.finalize(self.request)
        result = saved["candidate"]["result"]
        self.assertEqual(result["facts"], [])
        self.assertIn("source_material_rejected", result["blocking_gaps"])
        self.assertIn("urn:uuid:" + completed["receipt"]["body_artifact_id"], result["held_refs"])
        self.assertEqual(result["validated_source_refs"], [])

    async def test_invalid_owned_artifact_integrity_refuses_finalization(self):
        completed = await self.completed()
        self.ledger.artifacts[UUID(completed["receipt"]["body_artifact_id"])]["content"] += "changed"
        with self.assertRaisesRegex(ExecutionRejected, "integrity"):
            await self.store.finalize(self.request)
        self.assertEqual((len(self.ledger.events), len(self.ledger.artifacts)), (4, 8))

    async def test_handoff_and_optional_observation_rollback_together(self):
        await self.begin();await self.store.claim(self.request);await self.reserve()
        self.ledger.fail_kind = OBSERVATION_KIND
        with self.assertRaises(ExecutionPersistenceError):
            await self.store.finalize(self.request, observed_tool_output=self.payload())
        self.assertEqual((len(self.ledger.events), len(self.ledger.artifacts)), (3, 6))
        self.assertEqual((await self.store.load())["recon"]["phase"], "claimed")

    async def test_lost_commit_ack_does_not_cause_another_query_or_handoff(self):
        await self.completed()
        self.ledger.fail_after_commit = True
        with self.assertRaises(ExecutionPersistenceError): await self.store.finalize(self.request)
        self.assertEqual((await self.store.claim(self.request))["decision"]["action"], "read_handoff")
        self.assertEqual((await self.store.read_handoff(self.request))["retention"], "committed")
        self.assertEqual((len(self.ledger.events), len(self.ledger.artifacts)), (5, 10))

    async def test_cancel_and_prequery_budget_stop_preserve_real_control_reason(self):
        await self.begin();await self.store.claim(self.request)
        await self.store.mark_cancelled(self.request)
        saved = await self.store.finalize(self.request)
        self.assertEqual(saved["candidate"]["result"]["stop_reason"], "cancelled")
        self.assertEqual(saved["state"]["stage_usage"]["tool_calls"], 0)
        self.assertIsNotNone(saved["candidate"]["execution"]["cancellation_observed_at"])

    async def test_read_requires_the_same_owner_and_frozen_business_request(self):
        await self.completed();await self.store.finalize(self.request)
        foreign = ReconExecutionStore(self.ledger, tenant_id=self.store.tenant_id, run_id=self.store.run_id, executor_id=UUID(int=999))
        with self.assertRaisesRegex(ExecutionRejected, "owner"):
            await foreign.read_handoff(self.request)
        changed = replace(self.request, trigger="manual")
        with self.assertRaisesRegex(ExecutionRejected, "frozen runtime"):
            await self.store.read_handoff(changed)


if __name__ == "__main__":
    unittest.main()
