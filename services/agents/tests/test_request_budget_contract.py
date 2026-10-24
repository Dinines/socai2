"""I2 assembly and egress share one real message budget, fake dispatch only."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import NAMESPACE_URL, uuid5

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from langchain_core.messages import HumanMessage, SystemMessage
from app.investigation_v2.execution_models import DurableAnalysis, make_analysis_messages
from app.investigation_v2.execution_store import canonical_json
from app.investigation_v2.request_budget import MAX_INPUT_BYTES, RequestBudgetExceeded, checked_model_input, serialized_message_bytes
from app.llm import egress_privacy
from app.llm.contract_rules import LLMContractViolation
from test_evidence_view_contract import EVENT, query, record, scope, view
from test_execution_models_contract import ATTEMPT, STEP, Model, Session
from test_execution_tools_contract import FakeStore


def evidence_count(count):
    return view(query([record("x" * 128, event_id=EVENT if i == 0 else uuid5(NAMESPACE_URL, f"request-size-{i}"))
                       for i in range(count)]))


class RequestBudgetContractTests(unittest.IsolatedAsyncioTestCase):
    def test_ready_messages_fit_both_preparation_and_dispatch_measurement(self):
        for mode in ("focused_analysis", "combined_analysis"):
            for count in (1, 7):
                with self.subTest(mode=mode, count=count):
                    messages = make_analysis_messages(evidence_count(count), mode)
                    checked = checked_model_input(messages)
                    self.assertEqual(checked.input_bytes, serialized_message_bytes(messages))
                    self.assertLessEqual(checked.input_bytes, MAX_INPUT_BYTES)
                    detached = checked.messages
                    detached.clear()
                    self.assertEqual(len(checked.messages), 2)

    def test_eight_and_ten_records_are_rejected_during_assembly_with_exact_overhead(self):
        for mode in ("focused_analysis", "combined_analysis"):
            for count in (8, 10):
                evidence = evidence_count(count)
                before = evidence.canonical_doc
                with self.subTest(mode=mode, count=count), self.assertRaises(RequestBudgetExceeded) as caught:
                    make_analysis_messages(evidence, mode)
                detail = caught.exception.details
                self.assertGreater(detail["input_bytes"], detail["limit_bytes"])
                self.assertEqual(detail["fixed_message_bytes"] + detail["available_serialized_evidence_bytes"], MAX_INPUT_BYTES)
                self.assertEqual(detail["fixed_message_bytes"] + detail["serialized_evidence_bytes"], detail["input_bytes"])
                self.assertEqual(evidence.canonical_doc, before)
                self.assertEqual(len(evidence.model_view["events"]), count)
                if mode == "focused_analysis" and count == 10:
                    self.assertEqual(len(canonical_json(evidence.model_view).encode()), 7882)
                    self.assertEqual(detail["input_bytes"], 14194)

    def test_utf8_escaping_and_exact_complete_message_boundary(self):
        messages = [SystemMessage(content='界 "quoted" \\ text'), HumanMessage(content="")]
        remaining = MAX_INPUT_BYTES - serialized_message_bytes(messages)
        messages[1] = HumanMessage(content="x" * remaining)
        self.assertEqual(checked_model_input(messages).input_bytes, MAX_INPUT_BYTES)
        messages[1] = HumanMessage(content="x" * (remaining + 1))
        with self.assertRaises(RequestBudgetExceeded) as caught:
            checked_model_input(messages)
        self.assertEqual(caught.exception.details["excess_bytes"], 1)
        with self.assertRaises(LLMContractViolation):
            checked_model_input([HumanMessage(content='{"class_uid":4001}')])

    async def execute(self, evidence, *, outbound=None):
        store, context = FakeStore(), scope()
        model = Model(store, "{}")
        gate = DurableAnalysis(store, context, model)
        async def call():
            return await gate.execute(evidence, "focused_analysis", step_id=STEP, attempt_id=ATTEMPT,
                                      subtask_id="request-budget-contract", current_snapshot_ref=evidence.snapshot_ref)
        if outbound is None:
            result = await call()
        else:
            with patch.object(egress_privacy, "open_session", return_value=Session(outbound=outbound)):
                result = await call()
        self.assertEqual((len(store.reserves), len(store.completions), len(model.calls)), (0, 0, 0))
        self.assertEqual(result["observed_outcome"], "no_request")
        self.assertFalse(result["dispatch_started"])
        self.assertEqual(result["reason"], "analysis_input_exceeds_request_budget")
        return result

    async def test_executor_exposes_preparation_gap_without_reserve_or_dispatch(self):
        evidence = evidence_count(10)
        result = await self.execute(evidence)
        gap = result["input_budget_gap"]
        self.assertEqual(gap["stage"], "task_preparation")
        self.assertEqual(gap["input_bytes"], 14194)
        self.assertEqual(gap["affected_questions"], ["Q1", "Q2", "Q5"])
        self.assertEqual(gap["held_evidence_refs"], [item["ref"] for item in evidence.model_view["events"]])
        self.assertEqual(gap["held_alert_ref"], evidence.model_view["alert"]["ref"])
        self.assertEqual(gap["held_query_ref"], evidence.model_view["query"]["ref"])
        self.assertEqual(gap["omitted_evidence_refs"], [])
        self.assertFalse(gap["automatic_grouping"])

    async def test_egress_expansion_uses_the_same_limit_before_reservation(self):
        evidence = evidence_count(1)
        outbound = [SystemMessage(content="界" * 2300), HumanMessage(content="界" * 2300)]
        result = await self.execute(evidence, outbound=outbound)
        gap = result["input_budget_gap"]
        self.assertEqual(gap["stage"], "egress")
        self.assertEqual(gap["input_bytes"], serialized_message_bytes(outbound))
        self.assertEqual(gap["limit_bytes"], MAX_INPUT_BYTES)

    def test_conflicting_versions_are_not_removed_to_make_a_request_fit(self):
        rows = [record("a" * 512), record("b" * 512)]
        versions = sorted(item["content_hash"] for item in rows)
        for row in rows:
            row.update(identity_state="conflict", conflict_version_hashes=versions)
        rows += [record("c" * 512, event_id=uuid5(NAMESPACE_URL, f"conflict-budget-{i}")) for i in range(8)]
        evidence = view(query(rows))
        original = deepcopy(evidence.model_view)
        with self.assertRaises(RequestBudgetExceeded):
            make_analysis_messages(evidence, "focused_analysis")
        self.assertEqual(evidence.model_view, original)
        self.assertEqual(sum(item["conflict"] for item in evidence.model_view["events"]), 2)


if __name__ == "__main__":
    unittest.main()
