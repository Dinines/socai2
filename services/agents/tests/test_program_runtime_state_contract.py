"""b2.3a closed program/manual policy reuses M3 without authorizing IO."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import UUID, NAMESPACE_URL, uuid5

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.execution_state import BudgetLimits, OpeningUsage, ExecutionRejected, initial_state, reserve, settle
from app.investigation_v2.execution_store import canonical_json, content_hash, scope_snapshot
from app.investigation_v2.program_runtime_state import (RUNTIME_VERSION, SUBTASK, policy_versions, make_program_recon_plan, install_program_recon,
    claim_program_recon, validate_program_reservation, observed_program_stop, cancel_program_recon, finish_program_recon)
from test_business_profile_contract import bind, case_context
from test_evidence_view_contract import START, scope
from test_alert_projection_contract import project
from app.investigation_v2 import recon_runtime_state as old_runtime

OWNER = UUID(int=800)
HANDOFF = UUID(int=801)


def managed(*, limit_changes=None, opening_changes=None):
    request = bind(scope(), trigger="manual")
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
    return install_program_recon(state, request, now=START), request


def reservation(state):
    plan = state["recon"]["plan"]
    return dict(step_id=plan["step_id"], attempt_id=plan["attempt_id"], subtask_id=SUBTASK, question_id="Q1",
                kind="tool", reserve_tokens=0, reserve_cost_microusd=0, retry_of=None)


def actual_reservation(state):
    plan = state["recon"]["plan"]
    args = reservation(state)
    validate_program_reservation(state, input_data=plan["query_input"], request=args, now=START)
    return reserve(state, **args, input_snapshot_ref="urn:uuid:" + str(UUID(int=802)),
                   input_hash=content_hash(canonical_json(plan["query_input"])), now=START)[0]


class ProgramRuntimeStateContractTests(unittest.TestCase):
    def rehash_plan(self, state, *, dispatch=False):
        plan = state["recon"]["plan"]
        profile = plan["business_profile"]
        profile["binding_ref"] = "profile:" + content_hash(canonical_json({k:v for k,v in profile.items() if k!="binding_ref"}))
        if dispatch:
            # An attacker can update all self hashes/UUIDs consistently; the
            # closed expected policy must still come from controlled code.
            fingerprint = content_hash(canonical_json([plan["policy_versions"], plan["scope_hash"], plan["query_input"]]))
            step = uuid5(NAMESPACE_URL, f"socai2:{plan['run_id']}:program-recon:{fingerprint}")
            plan.update(query_fingerprint=fingerprint, step_id=str(step), attempt_id=str(uuid5(step, "attempt-1")))
        plan["plan_ref"] = "program-recon-plan:" + content_hash(canonical_json({k:v for k,v in plan.items() if k!="plan_ref"}))

    def test_closed_version_combination_rejects_self_consistent_missing_extra_and_old_components(self):
        state, _ = managed();original = deepcopy(state)
        self.assertEqual(state["recon"]["plan"]["policy_versions"], policy_versions())
        for key in policy_versions():
            changed = deepcopy(state);changed["recon"]["plan"]["policy_versions"][key] = "unapproved-or-old.v1"
            self.rehash_plan(changed, dispatch=True)
            with self.subTest(key=key), self.assertRaises(ExecutionRejected): claim_program_recon(changed, now=START)
        for key, remove in (("material_schema", True), ("extra_policy", False)):
            changed = deepcopy(state);versions = changed["recon"]["plan"]["policy_versions"]
            if remove: versions.pop(key)
            else: versions[key] = "custom.v1"
            self.rehash_plan(changed, dispatch=True)
            with self.assertRaises(ExecutionRejected): claim_program_recon(changed, now=START)
        detached = policy_versions();detached.clear()
        self.assertEqual(state, original);self.assertTrue(policy_versions())

    def test_manual_trigger_is_fixed_authority_not_a_rehashed_profile_claim(self):
        state, request = managed()
        automatic = replace(request, trigger="automatic")
        with self.assertRaisesRegex(ExecutionRejected, "manual alert"): make_program_recon_plan(automatic)
        bare = {key:value for key,value in state.items() if key not in {"runtime_version", "recon"}}
        with self.assertRaises(ExecutionRejected): install_program_recon(bare, automatic, now=START)
        changed = deepcopy(state);changed["recon"]["plan"]["business_profile"]["trigger"] = "automatic"
        self.rehash_plan(changed)
        with self.assertRaises(ExecutionRejected): claim_program_recon(changed, now=START)

    def test_full_profile_is_rebuilt_from_scope_including_refs_coverage_and_exact_types(self):
        request = project();plan = make_program_recon_plan(request)
        self.assertEqual(plan["business_profile"], request.descriptor)
        state, _ = managed()
        for kind in ("target_ref", "coverage", "bool_revision", "profile_version", "extra"):
            changed = deepcopy(state);profile = changed["recon"]["plan"]["business_profile"]
            if kind == "target_ref": profile["target"]["record_ref"] = "different-ref"
            if kind == "coverage": profile["member_coverage"]["investigated_members"] = 1
            if kind == "bool_revision": profile["scope_revision"] = True
            if kind == "profile_version": profile["profile_version"] = "investigation_profiles.v2"
            if kind == "extra": profile["extra"] = "automatic"
            self.rehash_plan(changed)
            with self.subTest(kind=kind), self.assertRaises(ExecutionRejected): claim_program_recon(changed, now=START)

    def test_self_consistent_plan_query_step_attempt_schema_and_extra_keys_cannot_drift(self):
        state, _ = managed()
        for kind in ("query", "step", "attempt", "schema", "extra"):
            changed = deepcopy(state);plan = changed["recon"]["plan"]
            if kind == "query": plan["query_input"]["parameters"]["end"] = "2026-10-23T10:04:00.000000+00:00"
            if kind == "step": plan["step_id"] = str(UUID(int=99))
            if kind == "attempt": plan["attempt_id"] = str(UUID(int=99))
            if kind == "schema": plan["schema"] = "program_recon_plan.v2"
            if kind == "extra": plan["extra"] = "dispatch"
            self.rehash_plan(changed, dispatch=kind == "query")
            with self.subTest(kind=kind), self.assertRaises(ExecutionRejected): claim_program_recon(changed, now=START)

    def test_old_and_new_states_cannot_upgrade_or_share_dispatch_identities(self):
        state, request = managed();bare = {key:value for key,value in state.items() if key not in {"runtime_version", "recon"}}
        old = old_runtime.install_recon(bare, request, now=START)
        self.assertNotEqual(old["recon"]["plan"]["step_id"], state["recon"]["plan"]["step_id"])
        self.assertNotEqual(old["recon"]["plan"]["attempt_id"], state["recon"]["plan"]["attempt_id"])
        self.assertEqual(old["scope"], state["scope"])
        with self.assertRaises(ExecutionRejected): claim_program_recon(old, now=START)
        with self.assertRaises(ExecutionRejected): old_runtime.claim_recon(state, now=START)
        with self.assertRaises(ExecutionRejected): install_program_recon(old, request, now=START)

    def test_stopped_read_path_requires_a_well_formed_handoff_reference(self):
        state, _ = managed();state["recon"]["phase"] = "stopped"
        for reference in (None, {}, {"artifact_id": "bad-uuid", "sha256": "f"*64},
                          {"artifact_id": str(HANDOFF), "sha256": False}):
            changed = deepcopy(state);changed["recon"]["handoff"] = reference
            with self.subTest(reference=reference), self.assertRaises(ExecutionRejected): claim_program_recon(changed, now=START)

    def test_plan_is_versioned_deterministic_full_window_and_detached(self):
        state, request = managed()
        with patch("socket.socket", side_effect=AssertionError("pure runtime state")):
            plan = make_program_recon_plan(request)
        self.assertEqual(plan, state["recon"]["plan"])
        self.assertEqual(plan["runtime_version"], RUNTIME_VERSION)
        self.assertEqual(plan["completion_policy_ref"], "bounded_full_window_program_fields.v1")
        self.assertEqual(plan["query_input"]["parameters"]["start"], "2026-10-23T10:00:00.000000+00:00")
        self.assertEqual(plan["query_input"]["parameters"]["end"], "2026-10-23T10:05:00.000000+00:00")
        plan["query_input"]["parameters"]["dest_ip"] = "192.0.2.99"
        self.assertNotEqual(plan, make_program_recon_plan(request))

    def test_install_refuses_case_scope_mismatch_prior_attempt_and_reset(self):
        state, request = managed()
        with self.assertRaisesRegex(ExecutionRejected, "already installed"):
            install_program_recon(state, request, now=START)
        other = replace(request.context, run_id=UUID(int=900))
        with self.assertRaises(ExecutionRejected):
            bare = {k: v for k, v in state.items() if k not in {"runtime_version", "recon"}}
            install_program_recon(bare, bind(other, trigger="manual"), now=START)
        context, target = case_context()
        with self.assertRaisesRegex(ExecutionRejected, "manual alert profile"):
            make_program_recon_plan(bind(context, target, profile="case_investigation"))
        claimed, _ = claim_program_recon(state, now=START)
        used = actual_reservation(claimed)
        bare = {k: v for k, v in used.items() if k not in {"runtime_version", "recon"}}
        with self.assertRaisesRegex(ExecutionRejected, "before attempts"):
            install_program_recon(bare, request, now=START)

    def test_claim_preflight_changes_no_budget_and_is_not_dispatch_permission(self):
        state, _ = managed()
        original = deepcopy(state)
        claimed, decision = claim_program_recon(state, now=START)
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
            stopped, decision = claim_program_recon(state, now=now)
            with self.subTest(case=case):
                self.assertEqual(stopped["recon"]["stop_reason"], "deadline" if case == "deadline" else "budget_limit")
                self.assertEqual(decision["action"], "finalize_blocked")
                self.assertEqual(stopped["attempts"], {})

    def test_opening_unknown_never_dispatches_or_releases_history(self):
        state, _ = managed(opening_changes={"model_calls": 1, "unknown_calls": 1, "known_cost_microusd": None})
        stopped, decision = claim_program_recon(state, now=START)
        self.assertEqual(stopped["recon"]["stop_reason"], "unknown_attempt")
        self.assertEqual(stopped["opening_usage"], state["opening_usage"])
        self.assertEqual(stopped["run_total"]["unknown_calls"], 1)
        self.assertFalse(decision["m3_reservation_required"])

    def test_repeated_claim_does_not_take_over_and_blocked_only_finalizes(self):
        state, _ = managed()
        claimed, _ = claim_program_recon(state, now=START)
        same, decision = claim_program_recon(claimed, now=START + timedelta(seconds=1))
        self.assertEqual(same, claimed)
        self.assertEqual(decision["action"], "in_progress_or_interrupted")
        self.assertFalse(decision["needs_commit"])
        blocked, _ = claim_program_recon(managed(limit_changes={"max_tool_calls": 0})[0], now=START)
        _, decision = claim_program_recon(blocked, now=START)
        self.assertEqual(decision["action"], "finalize_blocked")
        self.assertFalse(decision["needs_commit"])

    def test_only_the_frozen_tool_input_and_attempt_can_be_reserved(self):
        state, _ = managed()
        claimed, _ = claim_program_recon(state, now=START)
        plan = claimed["recon"]["plan"]
        for key, value in (("kind", "model"), ("question_id", "Q2"), ("attempt_id", str(UUID(int=123))),
                           ("retry_of", plan["attempt_id"]), ("reserve_tokens", False)):
            args = reservation(claimed); args[key] = value
            with self.subTest(key=key), self.assertRaises(ExecutionRejected):
                validate_program_reservation(claimed, input_data=plan["query_input"], request=args, now=START)
        data = deepcopy(plan["query_input"]);data["parameters"]["dest_ip"] = "192.0.2.99"
        with self.assertRaisesRegex(ExecutionRejected, "input differs"):
            validate_program_reservation(claimed, input_data=data, request=reservation(claimed), now=START)
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
                claim_program_recon(changed, now=now)

    def test_exactly_used_cap_is_not_an_after_call_budget_failure(self):
        state, _ = managed();claimed, _ = claim_program_recon(state, now=START)
        reserved = actual_reservation(claimed)
        attempt = reserved["recon"]["plan"]["attempt_id"]
        settled, _ = settle(reserved, attempt_id=attempt, outcome="responded", actual_tokens=0,
                            actual_cost_microusd=0, usage_source_ref="pure-query-response", now=START)
        self.assertEqual(settled["stage_usage"]["tool_calls"], settled["limits"]["max_tool_calls"])
        self.assertIsNone(observed_program_stop(settled, now=START))
        closed, repeated = finish_program_recon(settled, artifact_id=HANDOFF, body_hash="f" * 64, execution_stop=None, now=START)
        self.assertFalse(repeated)
        self.assertEqual(closed["stage_usage"], settled["stage_usage"])
        self.assertEqual(claim_program_recon(closed, now=START)[1]["action"], "read_handoff")

    def test_unsettled_and_unknown_require_explicit_handoff_and_keep_reservations(self):
        state, _ = managed();claimed, _ = claim_program_recon(state, now=START);reserved = actual_reservation(claimed)
        self.assertEqual(observed_program_stop(reserved, now=START), "unknown_attempt")
        with self.assertRaisesRegex(ExecutionRejected, "observed state"):
            finish_program_recon(reserved, artifact_id=HANDOFF, body_hash="f" * 64, execution_stop=None, now=START)
        unknown, _ = settle(reserved, attempt_id=reserved["recon"]["plan"]["attempt_id"], outcome="unknown",
                            actual_tokens=None, actual_cost_microusd=None, usage_source_ref="pure-unknown", now=START)
        closed, _ = finish_program_recon(unknown, artifact_id=HANDOFF, body_hash="f" * 64,
                                 execution_stop="unknown_attempt", now=START)
        self.assertEqual(closed["attempts"], unknown["attempts"])
        self.assertEqual(closed["stage_usage"]["unsettled_attempts"], 1)

    def test_finishing_cannot_omit_a_real_deadline_or_invent_a_budget_stop(self):
        state, _ = managed();claimed, _ = claim_program_recon(state, now=START);reserved = actual_reservation(claimed)
        settled, _ = settle(reserved, attempt_id=reserved["recon"]["plan"]["attempt_id"], outcome="responded",
                            actual_tokens=0, actual_cost_microusd=0, usage_source_ref="pure-known", now=START)
        for stop, now in ((None, START + timedelta(seconds=31)), ("budget_limit", START)):
            with self.subTest(stop=stop), self.assertRaisesRegex(ExecutionRejected, "observed state"):
                finish_program_recon(settled, artifact_id=HANDOFF, body_hash="f" * 64, execution_stop=stop, now=now)
        stopped, _ = finish_program_recon(settled, artifact_id=HANDOFF, body_hash="f" * 64, execution_stop="deadline",
                                  now=START + timedelta(seconds=31))
        self.assertEqual(stopped["recon"]["stop_reason"], "deadline")

    def test_cancellation_and_idempotent_finish_never_overwrite_a_handoff(self):
        state, _ = managed();claimed, _ = claim_program_recon(state, now=START)
        cancelled = cancel_program_recon(claimed, now=START)
        self.assertEqual(observed_program_stop(cancelled, now=START), "cancelled")
        closed, _ = finish_program_recon(cancelled, artifact_id=HANDOFF, body_hash="f" * 64, execution_stop="cancelled", now=START)
        same, repeated = finish_program_recon(closed, artifact_id=HANDOFF, body_hash="f" * 64, execution_stop="cancelled", now=START)
        self.assertTrue(repeated);self.assertEqual(same, closed)
        with self.assertRaisesRegex(ExecutionRejected, "overwrite"):
            finish_program_recon(closed, artifact_id=HANDOFF, body_hash="e" * 64, execution_stop="cancelled", now=START)


if __name__ == "__main__":
    unittest.main()
