"""M6.2a uses actual M3 pure accounting without authorizing any I/O."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.execution_state import BudgetLimits, OpeningUsage, ExecutionRejected, initial_state, reserve, settle
from app.investigation_v2.execution_store import canonical_json, content_hash, scope_snapshot
from app.investigation_v2.recon_runtime_state import (RUNTIME_VERSION, SUBTASK, make_recon_plan, install_recon,
    claim_recon, validate_recon_reservation, observed_recon_stop, cancel_recon, finish_recon)
from test_business_profile_contract import bind, case_context
from test_evidence_view_contract import START, scope

OWNER = UUID(int=800)
HANDOFF = UUID(int=801)


def managed(*, limit_changes=None, opening_changes=None):
    request = bind(scope())
    controls, _ = scope_snapshot(request.context)
    limits = dict(max_model_calls=0, max_tool_calls=1, max_tokens=0, max_cost_microusd=0,
                  max_unsettled=1, deadline=START + timedelta(seconds=30), config_ref="pure-runtime-test",
                  legacy_model_limit_mapping="model cap=0; one fixed source query")
    limits.update(limit_changes or {})
    opening = dict(model_calls=0, known_tokens=0, known_cost_microusd=0, unknown_calls=0,
                   unpriced_calls=0, source_ref="pure-opening-no-prior-model")
    opening.update(opening_changes or {})
    state = initial_state(scope=controls, input_snapshot_ref="urn:uuid:" + str(UUID(int=799)),
                          input_hash="a" * 64, limits=BudgetLimits(**limits), opening=OpeningUsage(**opening),
                          executor_id=OWNER, now=START)
    return install_recon(state, request, now=START), request


def reservation(state):
    plan = state["recon"]["plan"]
    return dict(step_id=plan["step_id"], attempt_id=plan["attempt_id"], subtask_id=SUBTASK, question_id="Q1",
                kind="tool", reserve_tokens=0, reserve_cost_microusd=0, retry_of=None)


def actual_reservation(state):
    plan = state["recon"]["plan"]
    args = reservation(state)
    validate_recon_reservation(state, input_data=plan["query_input"], request=args, now=START)
    return reserve(state, **args, input_snapshot_ref="urn:uuid:" + str(UUID(int=802)),
                   input_hash=content_hash(canonical_json(plan["query_input"])), now=START)[0]


class ReconRuntimeStateContractTests(unittest.TestCase):
    def test_plan_is_versioned_deterministic_full_window_and_detached(self):
        state, request = managed()
        with patch("socket.socket", side_effect=AssertionError("pure runtime state")):
            plan = make_recon_plan(request)
        self.assertEqual(plan, state["recon"]["plan"])
        self.assertEqual(plan["runtime_version"], RUNTIME_VERSION)
        self.assertEqual(plan["completion_policy_ref"], "bounded_full_window_source_check.v1")
        self.assertEqual(plan["query_input"]["parameters"]["start"], "2026-10-23T10:00:00.000000+00:00")
        self.assertEqual(plan["query_input"]["parameters"]["end"], "2026-10-23T10:05:00.000000+00:00")
        plan["query_input"]["parameters"]["dest_ip"] = "192.0.2.99"
        self.assertNotEqual(plan, make_recon_plan(request))

    def test_install_refuses_case_scope_mismatch_prior_attempt_and_reset(self):
        state, request = managed()
        with self.assertRaisesRegex(ExecutionRejected, "already installed"):
            install_recon(state, request, now=START)
        other = replace(request.context, run_id=UUID(int=900))
        with self.assertRaises(ExecutionRejected):
            bare = {k: v for k, v in state.items() if k not in {"runtime_version", "recon"}}
            install_recon(bare, bind(other), now=START)
        context, target = case_context()
        with self.assertRaisesRegex(ExecutionRejected, "alert profile"):
            make_recon_plan(bind(context, target, profile="case_investigation"))
        claimed, _ = claim_recon(state, now=START)
        used = actual_reservation(claimed)
        bare = {k: v for k, v in used.items() if k not in {"runtime_version", "recon"}}
        with self.assertRaisesRegex(ExecutionRejected, "before attempts"):
            install_recon(bare, request, now=START)

    def test_claim_preflight_changes_no_budget_and_is_not_dispatch_permission(self):
        state, _ = managed()
        original = deepcopy(state)
        claimed, decision = claim_recon(state, now=START)
        self.assertEqual(state, original)
        self.assertEqual(claimed["attempts"], {})
        self.assertEqual(claimed["stage_usage"], state["stage_usage"])
        self.assertEqual(decision["action"], "dispatch_after_commit")
        self.assertTrue(decision["needs_commit"])
        self.assertTrue(decision["m3_reservation_required"])
        self.assertFalse(decision["external_call_authorized"])

    def test_deadline_cap_and_breach_map_only_known_admission_stops(self):
        for case in ("deadline", "tool_limit", "breach"):
            state, _ = managed(limit_changes={"max_tool_calls": 0} if case == "tool_limit" else {})
            now = START + timedelta(seconds=31) if case == "deadline" else START
            if case == "breach": state.update(budget_breached=True, breach_reasons=["explicit-existing-breach"])
            stopped, decision = claim_recon(state, now=now)
            with self.subTest(case=case):
                self.assertEqual(stopped["recon"]["stop_reason"], "deadline" if case == "deadline" else "budget_limit")
                self.assertEqual(decision["action"], "finalize_blocked")
                self.assertEqual(stopped["attempts"], {})

    def test_opening_unknown_never_dispatches_or_releases_history(self):
        state, _ = managed(opening_changes={"model_calls": 1, "unknown_calls": 1, "known_cost_microusd": None})
        stopped, decision = claim_recon(state, now=START)
        self.assertEqual(stopped["recon"]["stop_reason"], "unknown_attempt")
        self.assertEqual(stopped["opening_usage"], state["opening_usage"])
        self.assertEqual(stopped["run_total"]["unknown_calls"], 1)
        self.assertFalse(decision["m3_reservation_required"])

    def test_repeated_claim_does_not_take_over_and_blocked_only_finalizes(self):
        state, _ = managed()
        claimed, _ = claim_recon(state, now=START)
        same, decision = claim_recon(claimed, now=START + timedelta(seconds=1))
        self.assertEqual(same, claimed)
        self.assertEqual(decision["action"], "in_progress_or_interrupted")
        self.assertFalse(decision["needs_commit"])
        blocked, _ = claim_recon(managed(limit_changes={"max_tool_calls": 0})[0], now=START)
        _, decision = claim_recon(blocked, now=START)
        self.assertEqual(decision["action"], "finalize_blocked")
        self.assertFalse(decision["needs_commit"])

    def test_only_the_frozen_tool_input_and_attempt_can_be_reserved(self):
        state, _ = managed()
        claimed, _ = claim_recon(state, now=START)
        plan = claimed["recon"]["plan"]
        for key, value in (("kind", "model"), ("question_id", "Q2"), ("attempt_id", str(UUID(int=123))),
                           ("retry_of", plan["attempt_id"]), ("reserve_tokens", False)):
            args = reservation(claimed); args[key] = value
            with self.subTest(key=key), self.assertRaises(ExecutionRejected):
                validate_recon_reservation(claimed, input_data=plan["query_input"], request=args, now=START)
        data = deepcopy(plan["query_input"]);data["parameters"]["dest_ip"] = "192.0.2.99"
        with self.assertRaisesRegex(ExecutionRejected, "input differs"):
            validate_recon_reservation(claimed, input_data=data, request=reservation(claimed), now=START)
        self.assertEqual(actual_reservation(claimed)["stage_usage"]["tool_calls"], 1)

    def test_state_errors_and_policy_changes_are_not_swallowed_as_budget_stops(self):
        state, _ = managed()
        for kind in ("scope", "plan", "policy", "phase", "backwards"):
            changed = deepcopy(state); now = START
            if kind == "scope": changed["scope"]["revision"] = 99
            if kind == "plan": changed["recon"]["plan"]["attempt_id"] = str(UUID(int=100))
            if kind == "policy": changed["runtime_version"] = "unapproved-runtime"
            if kind == "phase": changed["recon"].update(phase="blocked", stop_reason=None)
            if kind == "backwards": now -= timedelta(seconds=1)
            with self.subTest(kind=kind), self.assertRaises(ExecutionRejected):
                claim_recon(changed, now=now)

    def test_exactly_used_cap_is_not_an_after_call_budget_failure(self):
        state, _ = managed();claimed, _ = claim_recon(state, now=START)
        reserved = actual_reservation(claimed)
        attempt = reserved["recon"]["plan"]["attempt_id"]
        settled, _ = settle(reserved, attempt_id=attempt, outcome="responded", actual_tokens=0,
                            actual_cost_microusd=0, usage_source_ref="pure-query-response", now=START)
        self.assertEqual(settled["stage_usage"]["tool_calls"], settled["limits"]["max_tool_calls"])
        self.assertIsNone(observed_recon_stop(settled, now=START))
        closed, repeated = finish_recon(settled, artifact_id=HANDOFF, body_hash="f" * 64, execution_stop=None, now=START)
        self.assertFalse(repeated)
        self.assertEqual(closed["stage_usage"], settled["stage_usage"])
        self.assertEqual(claim_recon(closed, now=START)[1]["action"], "read_handoff")

    def test_unsettled_and_unknown_require_explicit_handoff_and_keep_reservations(self):
        state, _ = managed();claimed, _ = claim_recon(state, now=START);reserved = actual_reservation(claimed)
        self.assertEqual(observed_recon_stop(reserved, now=START), "unknown_attempt")
        with self.assertRaisesRegex(ExecutionRejected, "observed state"):
            finish_recon(reserved, artifact_id=HANDOFF, body_hash="f" * 64, execution_stop=None, now=START)
        unknown, _ = settle(reserved, attempt_id=reserved["recon"]["plan"]["attempt_id"], outcome="unknown",
                            actual_tokens=None, actual_cost_microusd=None, usage_source_ref="pure-unknown", now=START)
        closed, _ = finish_recon(unknown, artifact_id=HANDOFF, body_hash="f" * 64,
                                 execution_stop="unknown_attempt", now=START)
        self.assertEqual(closed["attempts"], unknown["attempts"])
        self.assertEqual(closed["stage_usage"]["unsettled_attempts"], 1)

    def test_finishing_cannot_omit_a_real_deadline_or_invent_a_budget_stop(self):
        state, _ = managed();claimed, _ = claim_recon(state, now=START);reserved = actual_reservation(claimed)
        settled, _ = settle(reserved, attempt_id=reserved["recon"]["plan"]["attempt_id"], outcome="responded",
                            actual_tokens=0, actual_cost_microusd=0, usage_source_ref="pure-known", now=START)
        for stop, now in ((None, START + timedelta(seconds=31)), ("budget_limit", START)):
            with self.subTest(stop=stop), self.assertRaisesRegex(ExecutionRejected, "observed state"):
                finish_recon(settled, artifact_id=HANDOFF, body_hash="f" * 64, execution_stop=stop, now=now)
        stopped, _ = finish_recon(settled, artifact_id=HANDOFF, body_hash="f" * 64, execution_stop="deadline",
                                  now=START + timedelta(seconds=31))
        self.assertEqual(stopped["recon"]["stop_reason"], "deadline")

    def test_cancellation_and_idempotent_finish_never_overwrite_a_handoff(self):
        state, _ = managed();claimed, _ = claim_recon(state, now=START)
        cancelled = cancel_recon(claimed, now=START)
        self.assertEqual(observed_recon_stop(cancelled, now=START), "cancelled")
        closed, _ = finish_recon(cancelled, artifact_id=HANDOFF, body_hash="f" * 64, execution_stop="cancelled", now=START)
        same, repeated = finish_recon(closed, artifact_id=HANDOFF, body_hash="f" * 64, execution_stop="cancelled", now=START)
        self.assertTrue(repeated);self.assertEqual(same, closed)
        with self.assertRaisesRegex(ExecutionRejected, "overwrite"):
            finish_recon(closed, artifact_id=HANDOFF, body_hash="e" * 64, execution_stop="cancelled", now=START)


if __name__ == "__main__":
    unittest.main()
