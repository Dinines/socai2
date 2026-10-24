"""M3.1 direct contracts: fake usage only; no app, database or model startup."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import UUID

SOURCE = Path(__file__).resolve().parents[1] / "app/investigation_v2/execution_state.py"
SPEC = importlib.util.spec_from_file_location("execution_state_under_test", SOURCE)
execution = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = execution
SPEC.loader.exec_module(execution)

TENANT = "53824f24-d1d4-5820-8147-f6cfda8a1247"
RUN = "22222222-2222-4222-8222-222222222222"
OWNER = "33333333-3333-4333-8333-333333333333"
START = datetime(2026, 10, 23, 10, tzinfo=timezone.utc)
INPUT_HASH = "a" * 64


def uid(number):
    return str(UUID(int=number))


def limits(**changes):
    args = dict(max_model_calls=5, max_tool_calls=4, max_tokens=100, max_cost_microusd=1000,
                max_unsettled=4, deadline=START + timedelta(minutes=5), config_ref="test-policy-only",
                legacy_model_limit_mapping="legacy.max_tool_calls -> max_model_calls; explicit tool cap")
    args.update(changes)
    return execution.BudgetLimits(**args)


def opening(**changes):
    args = dict(model_calls=1, known_tokens=2000, known_cost_microusd=4000,
                unknown_calls=0, unpriced_calls=0, source_ref="triage-ledger-snapshot")
    args.update(changes)
    return execution.OpeningUsage(**args)


def scope():
    return dict(tenant_id=TENANT, run_id=RUN, revision=1, policy_ref="network_observation.v1",
                questions=[{"question_id": q} for q in ("Q1", "Q2", "Q3a", "Q3b", "Q4", "Q5")])


def initial(**changes):
    args = dict(scope=scope(), input_snapshot_ref="urn:uuid:" + uid(500), input_hash=INPUT_HASH,
                limits=limits(), opening=opening(), executor_id=OWNER, now=START)
    args.update(changes)
    return execution.initial_state(**args)


def reserve(state, number=1, **changes):
    args = dict(step_id=uid(number), attempt_id=uid(100 + number), subtask_id="subtask-" + str(number),
                question_id="Q1", kind="model", reserve_tokens=20, reserve_cost_microusd=100,
                input_snapshot_ref="urn:uuid:" + uid(500 + number), input_hash=INPUT_HASH, now=START)
    args.update(changes)
    return execution.reserve(state, **args)


def settle(state, number=1, **changes):
    args = dict(attempt_id=uid(100 + number), outcome="responded", actual_tokens=10,
                actual_cost_microusd=50, usage_source_ref="provider-response-usage", now=START)
    args.update(changes)
    return execution.settle(state, **args)


class ExecutionStateContractTest(unittest.TestCase):
    def test_explicit_typed_limits_reject_ambiguous_or_unbounded_policy(self):
        for changes in ({"max_model_calls": True}, {"max_tool_calls": -1}, {"max_tokens": 1.5},
                        {"max_cost_microusd": False}, {"max_unsettled": 0}, {"max_unsettled": 65},
                        {"max_model_calls": 64, "max_tool_calls": 1}, {"deadline": START.replace(tzinfo=None)},
                        {"config_ref": ""}, {"legacy_model_limit_mapping": ""}):
            with self.subTest(changes=changes), self.assertRaises(execution.ExecutionRejected):
                limits(**changes)
        for changes in ({"model_calls": True}, {"unknown_calls": 2}, {"unpriced_calls": 2},
                        {"known_cost_microusd": -1}, {"source_ref": ""}):
            with self.subTest(changes=changes), self.assertRaises(execution.ExecutionRejected):
                opening(**changes)
        with self.assertRaises(FrozenInstanceError):
            limits().max_tokens = 999
        self.assertEqual(limits(deadline=START.astimezone(timezone(timedelta(hours=8)))).deadline, START)

    def test_initial_scope_identity_and_opening_are_detached_json_with_no_io(self):
        supplied_scope = scope()
        with patch("socket.socket", side_effect=AssertionError("no IO")):
            state = initial(scope=supplied_scope)
        self.assertEqual(json.loads(json.dumps(state)), state)
        self.assertEqual(state["stage_id"], execution.stage_id_for(UUID(TENANT), UUID(RUN)))
        self.assertNotEqual(state["stage_id"], execution.stage_id_for(TENANT, uid(99)))
        self.assertEqual(state["executor_id"], OWNER)
        self.assertEqual(state["limits"]["currency"], "USD")
        self.assertEqual(state["stage_usage"]["known_tokens"], 0)
        self.assertEqual(state["run_total"]["total_tokens"], 2000)
        supplied_scope["questions"][0]["question_id"] = "changed"
        self.assertEqual(state["scope"]["questions"][0]["question_id"], "Q1")
        for invalid in (dict(scope(), revision=True), dict(scope(), policy_ref="model-policy"),
                        dict(scope(), questions=[]), dict(scope(), tenant_id="bad")):
            with self.subTest(invalid=invalid), self.assertRaises(execution.ExecutionRejected):
                initial(scope=invalid)
        with self.assertRaises(execution.ExecutionRejected):
            initial(input_hash="not-a-hash")

    def test_stage_does_not_charge_triage_and_real_overrun_is_retained(self):
        untouched = initial()
        state, receipt = reserve(untouched, reserve_tokens=60)
        self.assertEqual(untouched["attempts"], {})
        receipt["reserve_tokens"] = 1
        self.assertEqual(state["stage_usage"]["reserved_tokens"], 60)
        state, _ = settle(state, actual_tokens=70, actual_cost_microusd=80)
        self.assertEqual(state["stage_usage"]["known_tokens"], 70)
        self.assertEqual(state["run_total"]["total_tokens"], 2070)
        self.assertEqual(state["run_total"]["total_cost_microusd"], 4080)
        self.assertEqual(state["stage_usage"]["reserved_tokens"], 0)
        self.assertTrue(state["budget_breached"])
        self.assertIn(uid(101) + ":tokens_exceeded_reservation", state["breach_reasons"])
        with self.assertRaisesRegex(execution.ExecutionRejected, "breach"):
            reserve(state, 2)

    def test_children_share_slot_and_call_allowances_without_refunding_attempts(self):
        original = initial(limits=limits(max_model_calls=1, max_unsettled=1))
        state, _ = reserve(original)
        before = json.dumps(state, sort_keys=True)
        with self.assertRaises(execution.ExecutionRejected):
            reserve(state, 2, kind="tool", reserve_tokens=0)
        self.assertEqual(json.dumps(state, sort_keys=True), before)
        state, _ = settle(state, outcome="no_request", actual_tokens=None, actual_cost_microusd=None,
                          usage_source_ref="transport-proved-request-not-sent")
        self.assertEqual(state["stage_usage"]["model_calls"], 1)
        self.assertEqual(state["stage_usage"]["unsettled_attempts"], 0)
        with self.assertRaisesRegex(execution.ExecutionRejected, "model call"):
            reserve(state, 2)
        state, _ = reserve(state, 2, kind="tool", reserve_tokens=0)
        state, _ = settle(state, 2, actual_tokens=0, actual_cost_microusd=0)
        self.assertEqual((state["stage_usage"]["model_calls"], state["stage_usage"]["tool_calls"]), (1, 1))
        self.assertEqual(state["stage_usage"]["known_tokens"], 0)

    def test_tokens_and_cost_use_known_plus_outstanding_reservations(self):
        state, _ = reserve(initial(), reserve_tokens=60, reserve_cost_microusd=800)
        with self.assertRaisesRegex(execution.ExecutionRejected, "token budget"):
            reserve(state, 2, reserve_tokens=41, reserve_cost_microusd=0)
        with self.assertRaisesRegex(execution.ExecutionRejected, "cost budget"):
            reserve(state, 2, reserve_tokens=1, reserve_cost_microusd=201)
        state, _ = settle(state, actual_tokens=40, actual_cost_microusd=300)
        state, _ = reserve(state, 2, reserve_tokens=60, reserve_cost_microusd=700)
        self.assertEqual(state["stage_usage"]["known_tokens"] + state["stage_usage"]["reserved_tokens"], 100)
        with self.assertRaises(execution.ExecutionRejected):
            reserve(state, 3, reserve_tokens=1, reserve_cost_microusd=0)

    def test_explicit_retry_uses_same_step_new_attempt_and_auditable_input(self):
        state, _ = reserve(initial())
        with self.assertRaises(execution.ExecutionRejected):
            reserve(state, attempt_id=uid(202), retry_of=uid(101))
        state, _ = settle(state, outcome="no_request", actual_tokens=0, actual_cost_microusd=0)
        with self.assertRaisesRegex(execution.ExecutionRejected, "explicit retry"):
            reserve(state, attempt_id=uid(202))
        with self.assertRaises(execution.ExecutionRejected):
            reserve(state, attempt_id=uid(101), retry_of=uid(101))
        state, receipt = reserve(state, attempt_id=uid(202), retry_of=uid(101), input_hash="b" * 64,
                                 input_snapshot_ref="urn:uuid:" + uid(999))
        self.assertEqual((receipt["step_id"], receipt["attempt_number"], receipt["retry_of"]), (uid(1), 2, uid(101)))
        self.assertEqual(len(state["attempts"]), 2)
        self.assertEqual(state["stage_usage"]["model_calls"], 2)
        state, _ = settle(state, attempt_id=uid(202))
        with self.assertRaisesRegex(execution.ExecutionRejected, "latest"):
            reserve(state, attempt_id=uid(203), retry_of=uid(101))
        with self.assertRaisesRegex(execution.ExecutionRejected, "logical step"):
            reserve(state, attempt_id=uid(203), retry_of=uid(202), question_id="Q5")

    def test_unknown_outcome_retains_all_reservations_and_cannot_be_replayed(self):
        state, _ = reserve(initial(limits=limits(max_unsettled=1)), reserve_tokens=60, reserve_cost_microusd=900)
        state, receipt = settle(state, outcome="unknown", actual_tokens=None, actual_cost_microusd=None,
                                usage_source_ref="transport-outcome-unknown")
        self.assertIsNone(receipt["actual_tokens"])
        self.assertIsNone(receipt["actual_cost_microusd"])
        self.assertEqual((receipt["remaining_tokens"], receipt["remaining_cost_microusd"]), (60, 900))
        self.assertEqual(state["stage_usage"]["unknown_attempts"], 1)
        self.assertIsNone(state["run_total"]["total_tokens"])
        with self.assertRaisesRegex(execution.ExecutionRejected, "unsettled"):
            reserve(state, attempt_id=uid(202), retry_of=uid(101))
        with self.assertRaisesRegex(execution.ExecutionRejected, "unsettled"):
            reserve(state, 2)
        with self.assertRaisesRegex(execution.ExecutionRejected, "already completed"):
            settle(state, outcome="no_request", actual_tokens=0, actual_cost_microusd=0)

    def test_missing_usage_settles_only_known_dimensions_and_keeps_slot(self):
        state, _ = reserve(initial(), reserve_tokens=60, reserve_cost_microusd=900)
        state, receipt = settle(state, actual_tokens=None, actual_cost_microusd=300)
        self.assertEqual((receipt["remaining_tokens"], receipt["remaining_cost_microusd"]), (60, 0))
        self.assertEqual(state["stage_usage"]["known_cost_microusd"], 300)
        self.assertTrue(receipt["unsettled"])
        state, _ = reserve(initial(), reserve_tokens=60, reserve_cost_microusd=900)
        state, receipt = settle(state, actual_tokens=40, actual_cost_microusd=None)
        self.assertEqual((receipt["remaining_tokens"], receipt["remaining_cost_microusd"]), (0, 900))
        self.assertEqual(state["stage_usage"]["known_tokens"], 40)
        self.assertEqual(state["stage_usage"]["unpriced_attempts"], 1)
        self.assertEqual(state["stage_usage"]["unsettled_attempts"], 1)
        self.assertIsNone(state["run_total"]["total_cost_microusd"])
        with self.assertRaisesRegex(execution.ExecutionRejected, "unsettled"):
            reserve(state, attempt_id=uid(202), retry_of=uid(101))

    def test_unpriced_without_cost_cap_releases_slot_but_never_invents_price(self):
        state = initial(limits=limits(max_cost_microusd=None, max_unsettled=1),
                        opening=opening(known_cost_microusd=None, unpriced_calls=1))
        state, _ = reserve(state, reserve_cost_microusd=None)
        state, receipt = settle(state, actual_tokens=10, actual_cost_microusd=None)
        self.assertIsNone(receipt["actual_cost_microusd"])
        self.assertFalse(receipt["unsettled"])
        self.assertEqual(state["run_total"]["known_cost_microusd"], 0)
        self.assertFalse(state["run_total"]["cost_complete"])
        self.assertIsNone(state["run_total"]["total_cost_microusd"])
        self.assertEqual(state["run_total"]["unpriced_calls"], 2)
        state, _ = reserve(state, 2, reserve_cost_microusd=None)
        self.assertEqual(state["stage_usage"]["model_calls"], 2)
        unknown_opening = initial(opening=opening(unknown_calls=1, known_cost_microusd=None))
        self.assertEqual(unknown_opening["run_total"]["known_tokens"], 2000)
        self.assertIsNone(unknown_opening["run_total"]["total_tokens"])

    def test_cost_overrun_keeps_actuals_other_attempts_and_blocks_new_calls(self):
        state, _ = reserve(initial(), reserve_cost_microusd=600)
        state, _ = reserve(state, 2, reserve_cost_microusd=300)
        state, receipt = settle(state, actual_tokens=10, actual_cost_microusd=1100)
        self.assertEqual(receipt["actual_cost_microusd"], 1100)
        self.assertEqual(state["stage_usage"]["reserved_cost_microusd"], 300)
        self.assertEqual(state["run_total"]["known_cost_microusd"], 5100)
        self.assertIn("stage:cost_exceeded_limit", state["breach_reasons"])
        with self.assertRaises(execution.ExecutionRejected):
            reserve(state, 3)
        state, _ = settle(state, 2, actual_tokens=10, actual_cost_microusd=100)
        self.assertEqual(state["run_total"]["total_cost_microusd"], 5200)

    def test_deadline_is_injected_and_late_results_are_still_accounted(self):
        state = initial(limits=limits(deadline=START + timedelta(seconds=1)))
        state, _ = reserve(state)
        with self.assertRaisesRegex(execution.ExecutionRejected, "deadline"):
            reserve(state, 2, now=START + timedelta(seconds=1))
        state, _ = settle(state, now=START + timedelta(minutes=1))
        self.assertEqual(state["stage_usage"]["known_tokens"], 10)
        with self.assertRaises(execution.ExecutionRejected):
            reserve(state, 2, now=START)
        with self.assertRaises(execution.ExecutionRejected):
            initial(now=START.replace(tzinfo=None))
        with self.assertRaises(execution.ExecutionRejected):
            initial(limits=limits(deadline=START))

    def test_bad_identity_fake_model_usage_and_double_settlement_are_rejected(self):
        state = initial()
        for changes in ({"attempt_id": "bad"}, {"question_id": "invented"}, {"kind": "other"},
                        {"reserve_tokens": 0}, {"reserve_tokens": True},
                        {"reserve_cost_microusd": None}, {"kind": "tool", "reserve_tokens": 1}):
            with self.subTest(changes=changes), self.assertRaises(execution.ExecutionRejected):
                reserve(state, **changes)
        changed_scope = json.loads(json.dumps(state))
        changed_scope["scope"]["revision"] = 2
        with self.assertRaisesRegex(execution.ExecutionRejected, "scope"):
            reserve(changed_scope)
        state["persistence"] = {"begin_event_id": uid(700)}
        state, _ = reserve(state, kind="tool", reserve_tokens=0)
        self.assertEqual(state["persistence"]["begin_event_id"], uid(700))
        with self.assertRaises(execution.ExecutionRejected):
            settle(state, actual_tokens=1)
        state, _ = settle(state, actual_tokens=0, actual_cost_microusd=0)
        state["attempts"][uid(101)]["completion_signature"] = "b" * 64
        before = json.dumps(state, sort_keys=True)
        with self.assertRaisesRegex(execution.ExecutionRejected, "already completed"):
            settle(state, actual_tokens=0, actual_cost_microusd=0)
        self.assertEqual(json.dumps(state, sort_keys=True), before)
        state, _ = reserve(state, 2)
        self.assertEqual(state["attempts"][uid(101)]["completion_signature"], "b" * 64)


if __name__ == "__main__":
    unittest.main()
