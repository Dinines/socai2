"""M4.2 direct contracts: real safe_ainvoke, fake SDK and fake durable commits.

No HTTP, database or provider requests. Budget arithmetic/transactions belong
to the already tested M3 reducer/store; these tests observe the call boundary.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import HumanMessage, SystemMessage
from app.core import cost_telemetry
from app.investigation_v2.execution_state import ExecutionRejected
from app.investigation_v2.execution_store import ExecutionPersistenceError, canonical_json, scope_fingerprint
from app.investigation_v2.execution_models import DurableAnalysis, make_analysis_messages
from app.llm import contract, egress_privacy
from app.llm.contract_rules import LLMInputContract
from app.privacy.redactor import Pseudonymizer
from app.workers.triage_budget import current_invocation, invocation_scope
from test_analysis_adoption_contract import candidate
from test_evidence_view_contract import START, scope, view, query
from test_execution_tools_contract import FakeStore

STEP = UUID("66666666-6666-4666-8666-666666666666")
ATTEMPT = UUID("77777777-7777-4777-8777-777777777777")


class Reply(SimpleNamespace):
    def model_copy(self, *, update):
        result = deepcopy(self)
        result.__dict__.update(update)
        return result


class Model:
    """An SDK-shaped fake. Its only async invocation records, never sends."""

    def __init__(self, store, content):
        self.store = store
        self.model_name = "aisoc-investigation"
        self.max_tokens = 2048
        self.request_timeout = 45.0
        self.root_async_client = SimpleNamespace(max_retries=0, timeout=45.0)
        self.extra_body = {"max_tokens": 2048}
        self.base_url = "http://127.0.0.1/fake-no-network"
        self.aisoc_pseudonymize = False
        self.reply = Reply(content=content, usage_metadata={"total_tokens": 123}, response_metadata={})
        self.calls = []
        self.error = None
        self.entered = asyncio.Event()
        self.block = None

    async def ainvoke(self, messages, **kwargs):
        self.calls.append({"messages": deepcopy(LLMInputContract.validate(messages)), "kwargs": deepcopy(kwargs)})
        self.store.timeline.append("model")
        self.entered.set()
        if self.block is not None:
            await self.block.wait()
        if self.error is not None:
            raise self.error
        return self.reply


class Session:
    """Explicit egress/restore fault injection; the safe wrapper stays real."""

    def __init__(self, *, outbound=None, restored=None, restore_error=None):
        self.outbound, self.restored, self.restore_error = outbound, restored, restore_error

    def redact_messages(self, messages):
        return self.outbound if self.outbound is not None else messages

    def restore(self, reply):
        if self.restore_error is not None:
            raise self.restore_error
        return reply.model_copy(update={"content": self.restored}) if self.restored is not None else reply


class DurableAnalysisTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.context = scope()
        self.evidence = view(context=self.context)
        self.store = FakeStore()
        self.model = Model(self.store, canonical_json(candidate(self.evidence)))

    def gate(self, store=None, model=None):
        return DurableAnalysis(store or self.store, self.context, model or self.model)

    async def execute(self, gate=None, **kwargs):
        return await (gate or self.gate()).execute(
            self.evidence, mode="combined_analysis", step_id=STEP, attempt_id=ATTEMPT,
            subtask_id="model-contract-subtask", current_snapshot_ref=self.evidence.snapshot_ref, **kwargs)

    async def test_reservation_refusal_and_uncertain_commit_never_call_model(self):
        failures = [ExecutionRejected(reason) for reason in
                    ("durable begin required", "owner mismatch", "budget exhausted", "deadline reached", "cost estimate required")]
        failures.append(ExecutionPersistenceError("reservation commit outcome unknown"))
        for error in failures:
            with self.subTest(reason=str(error)):
                store = FakeStore()
                store.reserve_error = error
                model = Model(store, self.model.reply.content)
                result = await self.execute(self.gate(store, model))
                self.assertEqual(result["execution_status"], "blocked")
                self.assertEqual(result["retention"], "not_confirmed")
                self.assertFalse(result["dispatch_started"])
                self.assertIsNone(result["reservation"])
                self.assertEqual(model.calls, [])
                self.assertEqual(store.completions, [])

    async def test_existing_invocation_or_cost_tracker_is_not_overridden(self):
        old_invocation = object()
        with invocation_scope(old_invocation):
            result = await self.execute()
            self.assertEqual(result["execution_status"], "blocked")
            self.assertIs(current_invocation(), old_invocation)
        old_tracker = object()
        token = cost_telemetry._current_tracker.set(old_tracker)
        try:
            result = await self.execute()
            self.assertEqual(result["execution_status"], "blocked")
            self.assertIs(cost_telemetry.current_cost_tracker(), old_tracker)
        finally:
            cost_telemetry._current_tracker.reset(token)
        self.assertEqual(self.store.reserves, [])
        self.assertEqual(self.model.calls, [])
        self.assertIsNone(current_invocation())

    async def test_single_answer_reply_is_retained_without_inventing_missing_answers(self):
        # Regression from the real M4 batch: the provider emitted one answer
        # object. Neither parsing nor publication may silently complete it.
        for wrapped in (False, True):
            with self.subTest(wrapped=wrapped):
                proposed = candidate(self.evidence)
                answer = proposed["answers"][0]
                proposed["answers"] = [answer] if wrapped else answer
                text = canonical_json(proposed)
                store = FakeStore()
                model = Model(store, text)
                result = await self.execute(self.gate(store, model))
                self.assertEqual((result["execution_status"], result["retention"]),
                                 ("responded", "committed"))
                self.assertEqual(result["raw_reply"]["text"], text)
                self.assertEqual(result["restored_content"]["text"], text)
                self.assertEqual(len(model.calls), 1)
                self.assertIsNone(result["adoption"]["assessment"])
                self.assertFalse(result["readable"]["has_overall_candidate"])
                self.assertEqual([a["question"] for a in result["adoption"]["answers"]],
                                 ["Q1"] if wrapped else [])
                retained = {q["question"]: q["status"] for q in result["adoption"]["retained_questions"]}
                self.assertEqual((retained["Q2"], retained["Q5"]), ("unassessed", "unassessed"))
                if not wrapped:
                    self.assertEqual(result["adoption"]["status"], "rejected")
                    self.assertEqual(result["readable"]["facts"], [])

    async def test_missing_finding_dependency_is_not_created_or_silently_accepted(self):
        proposed = candidate(self.evidence)
        proposed["findings"].pop()  # Q5 still references the omitted query finding.
        text = canonical_json(proposed)
        model = Model(self.store, text)
        result = await self.execute(self.gate(model=model))
        self.assertEqual((result["execution_status"], result["retention"]), ("responded", "committed"))
        self.assertEqual(result["raw_reply"]["text"], text)
        self.assertEqual(result["adoption"]["status"], "partial")
        self.assertEqual([a["question"] for a in result["readable"]["answers"]], ["Q1", "Q2"])
        self.assertNotIn("bounded_query", [f["predicate"] for f in result["readable"]["facts"]])
        self.assertIsNone(result["adoption"]["assessment"])
        self.assertEqual(len(model.calls), 1)

    async def test_absent_events_keep_gap_answers_and_query_is_not_an_event_reference(self):
        for status, claim in (("empty", "query_empty"), ("unavailable", "source_unavailable")):
            self.evidence = view(query(status=status), self.context)
            visible = self.evidence.model_view
            proposed = dict(snapshot_ref=self.evidence.snapshot_ref, mode="combined_analysis",
                            findings=[dict(key="F1", question="Q5", claim=claim, refs=[visible["query"]["ref"]], rationale="Bounded source coverage.")],
                            answers=[dict(question=q, status="supported" if q == "Q5" else "insufficient_evidence",
                                          finding_keys=["F1"] if q == "Q5" else [], rationale="Available evidence only.") for q in ("Q1", "Q2", "Q5")],
                            assessment=dict(finding_keys=["F1"], nature="unresolved", authorization="unknown", rationale="Activity and authorization remain unresolved."),
                            proposals=[])
            for forge_link in (False, True):
                with self.subTest(status=status, forge_link=forge_link):
                    value = deepcopy(proposed)
                    if forge_link:
                        value["findings"].append(dict(key="F2", question="Q2", claim="alert_linked",
                                                     refs=[visible["alert"]["ref"], visible["query"]["ref"]], rationale="Invalid query-as-event reference."))
                        value["assessment"]["finding_keys"].append("F2")
                    store = FakeStore()
                    model = Model(store, canonical_json(value))
                    result = await self.execute(self.gate(store, model))
                    self.assertEqual((result["execution_status"], result["retention"]), ("responded", "committed"))
                    self.assertEqual(result["adoption"]["status"], "partial" if forge_link else "admitted")
                    self.assertEqual([f["predicate"] for f in result["readable"]["facts"]], [claim])
                    self.assertEqual(result["readable"]["facts"][0]["returned_count"], 0 if status == "empty" else None)
                    self.assertEqual(json.loads(model.calls[0]["messages"][1]["content"])["evidence"]["events"], [])
                    self.assertEqual(len(model.calls), 1)

    async def test_sdk_retry_timeout_and_output_bounds_are_checked_before_reserve(self):
        mutations = (
            lambda model: setattr(model.root_async_client, "max_retries", 1),
            lambda model: setattr(model.root_async_client, "timeout", 46.0),
            lambda model: setattr(model, "request_timeout", 46.0),
            lambda model: setattr(model, "max_tokens", 2049),
            lambda model: setattr(model, "extra_body", {"max_tokens": 4096}),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                store = FakeStore()
                model = Model(store, self.model.reply.content)
                mutate(model)
                result = await self.execute(self.gate(store, model))
                self.assertEqual(result["execution_status"], "blocked")
                self.assertFalse(result["dispatch_started"])
                self.assertEqual(store.reserves, [])
                self.assertEqual(model.calls, [])

    async def test_input_contract_and_initial_or_egress_byte_caps_prevent_dispatch(self):
        # Each message alone is below 12 KiB, their UTF-8 combined body exceeds
        # it. This catches checking only user content or counting characters.
        large = [SystemMessage(content="界" * 2300), HumanMessage(content="界" * 2300)]
        invalid = [HumanMessage(content='{"class_uid":4001}')]
        for messages in (large, invalid):
            with self.subTest(case="initial"):
                with patch("app.investigation_v2.execution_models.make_analysis_messages", return_value=messages):
                    result = await self.execute()
                self.assertEqual(result["execution_status"], "blocked")
                self.assertFalse(result["dispatch_started"])
        for messages in (large, invalid):
            with self.subTest(case="after-egress"):
                with patch.object(egress_privacy, "open_session", return_value=Session(outbound=messages)):
                    result = await self.execute()
                self.assertEqual(result["execution_status"], "blocked")
                self.assertFalse(result["dispatch_started"])
        self.assertEqual(self.store.reserves, [])
        self.assertEqual(self.model.calls, [])
        self.assertEqual(self.store.completions, [])

        boundary = [SystemMessage(content="界" * 2000), HumanMessage(content="")]
        remaining = 12 * 1024 - len(canonical_json(LLMInputContract.validate(boundary)).encode("utf-8"))
        boundary[1] = HumanMessage(content="x" * remaining)
        self.assertEqual(len(canonical_json(LLMInputContract.validate(boundary)).encode("utf-8")), 12 * 1024)
        with patch("app.investigation_v2.execution_models.make_analysis_messages", return_value=boundary):
            result = await self.execute()
        self.assertEqual(result["observed_outcome"], "responded")
        self.assertEqual(self.store.reserves[0]["reserve_tokens"], 12 * 1024 + 256 + 2048)

    async def test_actual_egress_is_committed_before_call_and_raw_reply_precedes_restore(self):
        self.store.release_commit = asyncio.Event()
        original = candidate(self.evidence)
        original["findings"][0]["rationale"] = "Source address 192.0.2.70 is observed only."
        restored_text = canonical_json(original)
        session = egress_privacy.EgressSession(Pseudonymizer(tenant_id=str(self.context.tenant_id)))
        provider_text = session.pseudonymizer.redact(restored_text)
        self.model.reply.content = provider_text
        cache = contract._RESPONSE_CACHE
        with patch.object(egress_privacy, "open_session", return_value=session), \
                patch.object(cache, "lookup", side_effect=AssertionError("cache must not replace model execution")), \
                patch.object(cache, "store", side_effect=AssertionError("durable model call is not response-cache traffic")):
            task = asyncio.create_task(self.execute())
            try:
                await asyncio.wait_for(self.store.reserve_entered.wait(), timeout=5)
                self.assertEqual(self.model.calls, [])
                self.assertEqual(self.store.completions, [])
                self.store.release_commit.set()
                result = await asyncio.wait_for(task, timeout=5)
            finally:
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
        self.assertEqual((result["execution_status"], result["retention"]), ("responded", "committed"))
        request = self.store.reserves[0]
        actual = self.model.calls[0]["messages"]
        saved = request["input_data"]
        self.assertEqual(saved["messages"], actual)
        self.assertNotEqual(saved["messages"], saved["pre_egress_messages"])
        self.assertNotIn("192.0.2.70", canonical_json(actual))
        self.assertIn("192.0.2.70", canonical_json(saved["pre_egress_messages"]))
        input_bytes = len(canonical_json(actual).encode("utf-8"))
        self.assertEqual((saved["input_bytes"], request["reserve_tokens"]), (input_bytes, input_bytes + 256 + 2048))
        self.assertEqual(request["scope_hash"], scope_fingerprint(self.context))
        self.assertEqual((request["kind"], request["question_id"]), ("model", "Q1"))
        self.assertIsNone(request["reserve_cost_microusd"])
        self.assertEqual(result["raw_reply"]["text"], provider_text)
        self.assertEqual(result["restored_content"]["text"], restored_text)
        self.assertEqual(result["adoption"]["status"], "admitted")
        self.assertTrue(result["readable"]["has_overall_candidate"])
        self.assertEqual(len(self.store.completions), 1)
        completed = self.store.completions[0]
        for field in ("raw_reply", "restored_content", "adoption", "readable"):
            self.assertEqual(completed["output_data"][field], result[field])
        self.assertEqual(completed["actual_tokens"], 123)
        self.assertIsNone(completed["actual_cost_microusd"])
        self.assertLess(self.store.timeline.index("reserve_committed"), self.store.timeline.index("model"))
        self.assertLess(self.store.timeline.index("model"), self.store.timeline.index("complete_entered"))
        self.assertEqual(self.model.calls[0]["kwargs"], {})
        self.assertIsNone(current_invocation())

    async def test_usage_comes_from_provider_metadata_missing_is_not_zero(self):
        cases = (
            (None, {}, None, None),
            ({"input_tokens": 20}, {"token_usage": {"total_tokens": 71}}, 71, None),
            ({"total_tokens": True}, {}, None, None),
            ({"total_tokens": -1}, {}, None, None),
            ({"total_tokens": 0}, {"headers": {"x-litellm-response-cost": "0"}}, 0, 0),
            ({"total_tokens": 77}, {"headers": {"x-litellm-response-cost": "0.0000011",
                                                 "x-litellm-model-name": "configured-provider-model"}}, 77, 2),
        )
        for usage, metadata, tokens, cost in cases:
            with self.subTest(usage=usage, metadata=metadata):
                store = FakeStore()
                model = Model(store, self.model.reply.content)
                model.reply.usage_metadata = usage
                model.reply.response_metadata = metadata
                result = await self.execute(self.gate(store, model))
                self.assertEqual(result["observed_outcome"], "responded")
                self.assertEqual(store.completions[0]["actual_tokens"], tokens)
                self.assertEqual(store.completions[0]["actual_cost_microusd"], cost)
                self.assertEqual(result["raw_reply"]["total_tokens"], tokens)
                self.assertEqual(result["raw_reply"]["cost_microusd"], cost)
                self.assertIsNone(store.reserves[0]["reserve_cost_microusd"])

    async def test_restore_and_parse_failures_keep_response_and_do_not_become_unknown(self):
        raw = self.model.reply.content
        for session, reply in ((Session(restore_error=ValueError("restoration failed")), raw),
                               (Session(), "not valid JSON"),
                               (Session(), '{"snapshot_ref":"one","snapshot_ref":"two"}')):
            with self.subTest(reply=reply[:40]):
                store = FakeStore()
                model = Model(store, reply)
                with patch.object(egress_privacy, "open_session", return_value=session):
                    result = await self.execute(self.gate(store, model))
                self.assertEqual(result["observed_outcome"], "responded")
                self.assertEqual(result["retention"], "committed")
                self.assertEqual(result["raw_reply"]["text"], reply)
                self.assertIsNone(result["adoption"])
                self.assertEqual(store.completions[0]["outcome"], "responded")
                self.assertEqual(store.completions[0]["actual_tokens"], 123)
                self.assertEqual(len(model.calls), 1)

    async def test_output_utf8_boundary_and_overflow_are_retained_without_adoption(self):
        base = self.model.reply.content
        boundary = base + " " * (32 * 1024 - len(base.encode("utf-8")))
        self.model.reply.content = boundary
        result = await self.execute()
        self.assertFalse(result["raw_reply"]["truncated"])
        self.assertEqual(result["raw_reply"]["original_bytes"], 32 * 1024)
        self.assertEqual(result["adoption"]["status"], "admitted")
        over = boundary[:-1] + "界"
        store = FakeStore()
        model = Model(store, over)
        result = await self.execute(self.gate(store, model))
        retained = result["raw_reply"]
        self.assertEqual(result["observed_outcome"], "responded")
        self.assertTrue(retained["truncated"])
        self.assertEqual(retained["original_bytes"], 32 * 1024 + 2)
        self.assertEqual(retained["retained_bytes"], 32 * 1024 - 1)
        self.assertEqual(retained["sha256"], hashlib.sha256(over.encode("utf-8")).hexdigest())
        self.assertEqual(retained["retained_bytes"], len(retained["text"].encode("utf-8")))
        self.assertNotIn("\ufffd", retained["text"])
        self.assertIsNone(result["adoption"])
        self.assertEqual(store.completions[0]["actual_tokens"], 123)
        self.assertEqual(len(model.calls), 1)

    async def test_complete_failure_returns_retention_gap_and_same_attempt_never_replays(self):
        self.store.complete_error = ExecutionPersistenceError("completion commit outcome unknown")
        gate = self.gate()
        result = await self.execute(gate)
        self.assertEqual((result["execution_status"], result["observed_outcome"], result["retention"]),
                         ("retention_gap", "responded", "gap"))
        self.assertEqual(result["raw_reply"]["text"], self.model.reply.content)
        self.assertEqual(result["adoption"]["status"], "admitted")
        self.assertIsNone(result["completion"])
        retry = await self.execute(gate)
        self.assertEqual(retry["execution_status"], "blocked")
        self.assertEqual(len(self.model.calls), 1)
        self.assertEqual(len(self.store.completions), 1)

    async def test_deadline_exhausted_during_commit_records_no_request(self):
        self.store.deadline = START - timedelta(seconds=1)
        result = await self.execute()
        self.assertEqual(result["observed_outcome"], "no_request")
        self.assertFalse(result["dispatch_started"])
        self.assertEqual(self.model.calls, [])
        self.assertEqual(len(self.store.reserves), 1)
        self.assertEqual(self.store.completions[0]["outcome"], "no_request")
        # The SDK's nominal 45 seconds must also be shortened while awaiting a
        # reply, using the authoritative remaining stage time returned by M3.
        store = FakeStore()
        store.deadline = START + timedelta(milliseconds=30)
        model = Model(store, self.model.reply.content)
        model.block = asyncio.Event()
        result = await asyncio.wait_for(self.execute(self.gate(store, model)), timeout=5)
        self.assertEqual(result["observed_outcome"], "unknown")
        self.assertEqual(len(model.calls), 1)
        self.assertEqual(store.completions[0]["outcome"], "unknown")
        self.assertIsNone(store.completions[0]["actual_tokens"])

    async def test_transport_error_and_cancellation_preserve_unknown_without_retry(self):
        self.model.error = TimeoutError("fake no response")
        result = await self.execute()
        self.assertEqual(result["observed_outcome"], "unknown")
        self.assertEqual(len(self.model.calls), 1)
        self.assertIsNone(result["raw_reply"])
        self.assertEqual(self.store.completions[0]["outcome"], "unknown")
        self.assertIsNone(self.store.completions[0]["actual_tokens"])
        self.assertIsNone(self.store.completions[0]["actual_cost_microusd"])
        for fail_retention in (False, True):
            store = FakeStore()
            if fail_retention:
                store.complete_error = ExecutionPersistenceError("unknown completion")
            model = Model(store, self.model.reply.content)
            model.block = asyncio.Event()
            task = asyncio.create_task(self.execute(self.gate(store, model)))
            try:
                await asyncio.wait_for(model.entered.wait(), timeout=5)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            finally:
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
            self.assertEqual(len(model.calls), 1)
            self.assertEqual(len(store.completions), 1)
            self.assertEqual(store.completions[0]["outcome"], "unknown")

    async def test_stale_snapshot_is_rejected_before_reservation(self):
        result = await self.gate().execute(
            self.evidence, mode="combined_analysis", step_id=STEP, attempt_id=ATTEMPT,
            subtask_id="stale", current_snapshot_ref="ev:previous")
        self.assertEqual(result["execution_status"], "blocked")
        self.assertEqual(self.model.calls, [])
        self.assertEqual(self.store.reserves, [])


if __name__ == "__main__":
    unittest.main()
