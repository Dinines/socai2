"""b2.3b program stores and M3 engine; SQL double, no real database or HTTP."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
import unittest
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.execution_state import ExecutionRejected, OpeningUsage
from app.investigation_v2.execution_store import ExecutionStore, ExecutionPersistenceError
from app.investigation_v2.execution_store import canonical_json, content_hash, scope_snapshot
from app.investigation_v2.program_runtime_state import make_program_recon_plan
from app.investigation_v2.program_runtime_store import ProgramReconExecutionStore, HANDOFF_KIND, OBSERVATION_KIND
from test_program_runtime_state_contract import managed, reservation, OWNER, START
from test_evidence_view_contract import query
from _program_memory_ledger import MemoryLedger
from test_alert_projection_contract import project, source


class ProgramRuntimeStoreContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pure, _ = managed()
        self.request = project()
        self.ledger = MemoryLedger(run_id=self.request.context.run_id, tenant_id=self.request.context.tenant_id, now=START)
        self.store = ProgramReconExecutionStore(self.ledger, tenant_id=self.request.context.tenant_id,
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
        self.assertEqual(len(saved["candidate"]["result"]["facts"]), 4)
        self.assertGreater(len(self.request.context.member_snapshot.selected[0].data_only_text.encode("utf-8")), 512)
        self.assertEqual(saved["candidate"]["result"]["model_projection"], {"status": "not_requested", "eligible_for_model": False})
        self.assertEqual((len(self.ledger.events), len(self.ledger.artifacts)), (5, 10))
        cold = ProgramReconExecutionStore(self.ledger, tenant_id=self.store.tenant_id, run_id=self.store.run_id, executor_id=OWNER)
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
        self.assertEqual(saved["candidate"]["preparation"]["program_material_document"]["query"]["execution_state"], "unknown")
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
        foreign = ProgramReconExecutionStore(self.ledger, tenant_id=self.store.tenant_id, run_id=self.store.run_id, executor_id=UUID(int=999))
        with self.assertRaisesRegex(ExecutionRejected, "owner"):
            await foreign.read_handoff(self.request)
        changed = replace(self.request, trigger="automatic")
        with self.assertRaisesRegex(ExecutionRejected, "manual alert"):
            await self.store.read_handoff(changed)

    def rewrite_current(self, change):
        """Rehash a hostile latest snapshot and its event, leaving begin intact."""
        event = self.ledger.events[-1]
        artifact = self.ledger.artifacts[UUID(event["payload"]["state_artifact_id"])]
        value = json.loads(artifact["content"]);change(value)
        self.rewrite_body(artifact, value)
        event["payload"]["state_hash"] = artifact["sha256"]

    @staticmethod
    def rewrite_body(artifact, value):
        artifact["content"] = canonical_json(value)
        artifact["sha256"] = content_hash(artifact["content"])
        artifact["size_bytes"] = len(artifact["content"].encode("utf-8"))

    async def test_all_control_and_public_read_paths_require_unchanged_original_limits(self):
        await self.begin();await self.store.claim(self.request)
        original = deepcopy((self.ledger.events, self.ledger.artifacts))
        for field in ("limits", "opening_usage"):
            self.ledger.events, self.ledger.artifacts = deepcopy(original)
            def change(value):
                if field == "limits": value[field]["deadline"] = (START+timedelta(days=1)).isoformat(timespec="microseconds")
                else: value[field]["source_ref"] = "self-rehashed-new-opening"
            self.rewrite_current(change)
            before = deepcopy((self.ledger.events, self.ledger.artifacts))
            for operation in (self.store.load, lambda:self.store.read_artifact(next(iter(self.ledger.artifacts))),
                              lambda:self.store.claim(self.request), self.reserve,
                              lambda:self.store.mark_cancelled(self.request),
                              lambda:self.store.mark_dispatch_block(self.request, persistence_failure=True),
                              lambda:self.store.finalize(self.request), lambda:self.store.read_handoff(self.request)):
                with self.subTest(field=field, operation=operation), self.assertRaisesRegex(ExecutionRejected, "origin"):
                    await operation()
                self.assertEqual((self.ledger.events, self.ledger.artifacts), before)

    async def test_self_consistent_changed_scope_request_and_plan_still_refuse_original_mismatch(self):
        await self.begin();await self.store.claim(self.request)
        row = source();row["raw_event"]["message"] = "a later fully consistent source document"
        changed_request = project(row)
        def change(state):
            state["scope"] = scope_snapshot(changed_request.context)[0]
            state["scope_hash"] = content_hash(canonical_json(state["scope"]))
            state["recon"]["plan"] = make_program_recon_plan(changed_request)
        self.rewrite_current(change)
        with self.assertRaisesRegex(ExecutionRejected, "origin scope changed"):
            await self.store.claim(changed_request)

    async def test_original_begin_event_identity_and_body_pins_cannot_be_skipped(self):
        await self.begin();await self.store.claim(self.request)
        original = deepcopy((self.ledger.events, self.ledger.artifacts))
        for change in (lambda e:e.update(agent="other"), lambda e:e.update(input_hash="0"*64),
                       lambda e:e.update(output_hash="0"*64)):
            self.ledger.events, self.ledger.artifacts = deepcopy(original)
            change(self.ledger.events[0])
            with self.assertRaises(ExecutionRejected): await self.store.load()
        self.ledger.events, self.ledger.artifacts = deepcopy(original)
        self.ledger.events.append(deepcopy(self.ledger.events[0]))
        with self.assertRaisesRegex(ExecutionRejected, "unique"): await self.store.load()

    async def test_cold_reads_pin_tool_event_even_when_source_content_was_rejected(self):
        invalid = self.payload();invalid["rows"][0]["raw_payload"]["sha256"] = "0"*64
        completion = await self.completed(output=invalid);await self.store.finalize(self.request)
        event = next(e for e in self.ledger.events if str(e["id"]) == completion["receipt"]["event_id"])
        original = deepcopy(event)
        for field, value in (("agent", "other"), ("kind", "unified_attempt_reserved"), ("output_hash", "0"*64)):
            event.clear();event.update(deepcopy(original));event[field] = value
            with self.subTest(field=field), self.assertRaises(ExecutionRejected): await self.store.read_handoff(self.request)
            with self.assertRaises(ExecutionRejected): await self.store.finalize(self.request)

    async def test_repeated_read_requires_every_retained_body_and_observer_without_new_input(self):
        await self.begin();await self.store.claim(self.request);await self.reserve()
        saved = await self.store.finalize(self.request, observed_tool_output=self.payload())
        original = deepcopy(self.ledger.artifacts)
        for reference in saved["candidate"]["retained_artifact_refs"]:
            self.ledger.artifacts = deepcopy(original)
            self.ledger.artifacts.pop(UUID(reference.removeprefix("urn:uuid:")))
            with self.subTest(reference=reference), self.assertRaises(ExecutionRejected):
                await self.store.read_handoff(self.request)
        self.ledger.artifacts = deepcopy(original)
        observer = self.ledger.artifacts[UUID(saved["candidate"]["unconfirmed_observation_ref"]["artifact_id"])]
        observer["content"] += "x"
        with self.assertRaisesRegex(ExecutionRejected, "integrity"): await self.store.finalize(self.request)

    async def test_handoff_rehash_cannot_add_validated_facts_or_omit_retained_source(self):
        await self.completed();saved = await self.store.finalize(self.request)
        original = deepcopy((self.ledger.events, self.ledger.artifacts))
        for kind in ("omit_source", "invent_result"):
            self.ledger.events, self.ledger.artifacts = deepcopy(original)
            artifact = self.ledger.artifacts[UUID(saved["receipt"]["body_artifact_id"])]
            candidate = json.loads(artifact["content"])
            if kind == "omit_source": candidate["retained_artifact_refs"].pop()
            else:
                result = candidate["result"];result["facts"] = []
                result["result_ref"] = "program-recon:" + content_hash(canonical_json({k:v for k,v in result.items() if k!="result_ref"}))
                candidate["preparation"]["result"] = deepcopy(result)
                preparation = candidate["preparation"]
                preparation["preparation_ref"] = "program-recon-preparation:" + content_hash(canonical_json({k:v for k,v in preparation.items() if k!="preparation_ref"}))
            candidate["handoff_ref"] = "program-runtime-handoff:" + content_hash(canonical_json({k:v for k,v in candidate.items() if k!="handoff_ref"}))
            self.rewrite_body(artifact, candidate)
            self.ledger.events[-1]["payload"]["body_hash"] = artifact["sha256"]
            def change(state):
                state["recon"]["handoff"]["sha256"] = artifact["sha256"]
                state["persistence"]["body_hash"] = artifact["sha256"]
            self.rewrite_current(change)
            with self.subTest(kind=kind), self.assertRaisesRegex(ExecutionRejected, "retained original"):
                await self.store.read_handoff(self.request)

    async def test_owned_nonobject_source_is_unadopted_and_late_completion_never_rewrites_handoff(self):
        await self.completed(output=["not a tool-result object"])
        saved = await self.store.finalize(self.request)
        self.assertIsNone(saved["candidate"]["preparation"])
        self.assertEqual((saved["candidate"]["result"]["source_state"], saved["candidate"]["result"]["source_available"],
                          saved["candidate"]["result"]["execution_state"]), ("not_confirmed", None, "unknown"))
        self.assertEqual((await self.store.read_handoff(self.request))["candidate"], saved["candidate"])

    async def test_late_actual_completion_preserves_unconfirmed_handoff_and_read_only_repeat(self):
        await self.begin();await self.store.claim(self.request);await self.reserve()
        saved = await self.store.finalize(self.request, observed_tool_output=self.payload())
        state = await self.store.load()
        await self.store.complete(attempt_id=state["recon"]["plan"]["attempt_id"], output_data=self.payload(), outcome="responded",
                                  actual_tokens=0, actual_cost_microusd=0, usage_source_ref="late-actual-no-model")
        current = await self.store.load()
        self.assertEqual(current["stage_usage"]["unsettled_attempts"], 0)
        self.assertEqual((await self.store.read_handoff(self.request))["candidate"], saved["candidate"])
        self.assertEqual((await self.store.finalize(self.request))["candidate"], saved["candidate"])
        self.assertEqual((len(self.ledger.events), len(self.ledger.artifacts)), (5,11))

    async def test_deadline_handoff_remains_partial_after_successful_query(self):
        await self.completed();self.ledger.now = START + timedelta(seconds=31)
        saved = await self.store.finalize(self.request)
        self.assertEqual(saved["candidate"]["result"]["stop_reason"], "deadline")
        self.assertEqual(saved["candidate"]["result"]["scope_readiness"], "partial")
        self.assertEqual(len(saved["candidate"]["result"]["facts"]), 4)
        self.assertEqual((await self.store.read_handoff(self.request))["candidate"], saved["candidate"])

    async def test_review_latest_control_agent_mismatch_must_refuse_reserve(self):
        await self.begin();await self.store.claim(self.request)
        self.ledger.events[-1]['agent']='wrong-runtime-agent'
        with self.assertRaises(ExecutionRejected): await self.reserve()

    async def test_latest_control_body_and_receipt_pins_are_checked_before_dispatch(self):
        await self.begin();await self.store.claim(self.request)
        original = deepcopy((self.ledger.events, self.ledger.artifacts))
        for case in ("body_content", "body_kind", "input_hash", "receipt_owner"):
            self.ledger.events, self.ledger.artifacts = deepcopy(original)
            event = self.ledger.events[-1]
            body = self.ledger.artifacts[UUID(event["payload"]["body_artifact_id"])]
            if case == "body_content": body["content"] += "x"
            elif case == "body_kind": body["kind"] = "unified_step_output"
            elif case == "input_hash": event["input_hash"] = "0"*64
            else:
                event["payload"]["tenant_id"] = str(UUID(int=999))
                self.rewrite_current(lambda state:state["persistence"].update(tenant_id=str(UUID(int=999))))
            with self.subTest(case=case), self.assertRaises(ExecutionRejected): await self.reserve()

    async def test_unknown_latest_managed_kind_cannot_expose_an_earlier_dispatchable_state(self):
        await self.begin();await self.store.claim(self.request)
        self.ledger.events[-1]["kind"] = "unified_future_program_claimed"
        with self.assertRaises(ExecutionRejected): await self.store.claim(self.request)
        self.assertEqual(len(self.ledger.events),2)

    async def test_handoff_cannot_reselect_an_earlier_owned_valid_source_state(self):
        begin = await self.begin();await self.store.claim(self.request);await self.reserve()
        state = await self.store.load()
        await self.store.complete(attempt_id=state["recon"]["plan"]["attempt_id"],output_data=self.payload(),outcome="responded",
                                  actual_tokens=0,actual_cost_microusd=0,usage_source_ref="actual-no-model")
        saved = await self.store.finalize(self.request)
        candidate = deepcopy(saved["candidate"])
        source = begin["state"]
        refs = ["urn:uuid:"+source["persistence"]["state_artifact_id"],source["input_snapshot_ref"]]
        candidate.update(preparation=None,result=self.store._without_source(self.request,stop=None,reason="query_not_started",references=refs),
            retained_artifact_refs=sorted(refs),execution={"source_state_artifact_ref":refs[0],"stage_usage":source["stage_usage"],
                "run_total":source["run_total"],"cancellation_observed_at":None})
        candidate["handoff_ref"] = "program-runtime-handoff:"+content_hash(canonical_json({k:v for k,v in candidate.items() if k!="handoff_ref"}))
        artifact = self.ledger.artifacts[UUID(saved["receipt"]["body_artifact_id"])]
        self.rewrite_body(artifact,candidate)
        self.ledger.events[-1]["payload"]["body_hash"] = artifact["sha256"]
        def change(value):
            value["recon"]["handoff"]["sha256"] = artifact["sha256"]
            value["persistence"]["body_hash"] = artifact["sha256"]
        self.rewrite_current(change)
        with self.assertRaisesRegex(ExecutionRejected,"pre-handoff source state mismatch"):
            await self.store.read_handoff(self.request)
    async def test_review_self_rehashed_current_stop_must_match_handoff(self):
        await self.completed();await self.store.finalize(self.request)
        self.rewrite_current(lambda state:state['recon'].update(stop_reason='deadline'))
        with self.assertRaises(ExecutionRejected): await self.store.read_handoff(self.request)
    async def test_review_late_completion_does_not_hide_missing_handoff_state(self):
        await self.begin();await self.store.claim(self.request);await self.reserve()
        saved=await self.store.finalize(self.request,observed_tool_output=self.payload())
        state=await self.store.load()
        await self.store.complete(attempt_id=state['recon']['plan']['attempt_id'],output_data=self.payload(),outcome='responded',actual_tokens=0,actual_cost_microusd=0,usage_source_ref='late-no-model')
        self.ledger.artifacts.pop(UUID(saved['receipt']['state_artifact_id']))
        with self.assertRaises(ExecutionRejected): await self.store.read_handoff(self.request)

if __name__ == "__main__":
    unittest.main()
