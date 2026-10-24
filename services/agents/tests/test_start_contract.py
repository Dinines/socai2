"""M8a4.1 operation identity/terms separation, no storage or real auth."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.start_contract import (StartBudgetPolicy, normalize_alert_start, replay_decision,
    REQUEST_VERSION, INTENT_SCHEMA)
from app.investigation_v2.execution_state import ExecutionRejected
from app.investigation_v2.execution_store import canonical_json, content_hash
from app.investigation_v2.scope import TenantPrincipal, UTCWindow

TENANT, ACTOR, KEY, ALERT = (UUID(int=value) for value in (11, 22, 33, 44))
NOW = datetime(2026, 10, 25, tzinfo=timezone.utc)


def policy(**changes):
    return StartBudgetPolicy(**{**dict(max_model_calls=0, max_tool_calls=1, max_tokens=0, max_cost_microusd=0,
        max_unsettled=1, duration_seconds=120, config_ref="test-fixed-start-120s.v1",
        legacy_model_limit_mapping="No model calls; fixed program query only"), **changes})


class StartContractTests(unittest.TestCase):
    def intent(self, **changes):
        return normalize_alert_start(**{**dict(principal=TenantPrincipal(frozenset({TENANT, UUID(int=99)}), "current-actor", False),
            tenant_id=TENANT, actor_id=ACTOR, operation_key=KEY, alert_id=ALERT, window=UTCWindow(NOW, NOW+timedelta(minutes=5)),
            budget_policy=policy(), profile="alert_recon", trigger="manual", request_version=REQUEST_VERSION), **changes})

    def rehash(self, intent):
        intent["request_hash"] = content_hash(canonical_json(intent["request"]))
        intent["intent_ref"] = "alert-start-intent:" + content_hash(canonical_json({key: value for key, value in intent.items() if key != "intent_ref"}))

    def test_stable_normalized_intent_has_no_clock_or_execution_authority(self):
        first = self.intent();self.assertEqual(first, self.intent())
        self.assertEqual(first["schema"], INTENT_SCHEMA)
        self.assertEqual(first["request"]["target"], {"type": "alert", "id": str(ALERT)})
        self.assertEqual(first["request"]["budget_policy"]["duration_seconds"], 120)
        self.assertNotIn("deadline", canonical_json(first))
        decision = replay_decision(first)
        self.assertEqual(decision["decision"], "requires_atomic_admission")
        self.assertFalse(decision["may_begin"]);self.assertFalse(decision["external_call_authorized"])
        self.assertEqual(decision["persistence_status"], "not_verified_by_pure_contract")

    def test_equivalent_uuid_and_utc_offset_inputs_have_same_request_and_ids(self):
        offset = timezone(timedelta(hours=8))
        first = self.intent()
        other = self.intent(tenant_id=str(TENANT).upper(), actor_id=str(ACTOR), operation_key=str(KEY), alert_id=str(ALERT),
            window=UTCWindow(NOW.astimezone(offset), (NOW+timedelta(minutes=5)).astimezone(offset)))
        self.assertEqual(first, other)

    def test_only_another_tenant_or_operation_key_changes_the_run_identity(self):
        first = self.intent()
        for changed in (self.intent(operation_key=UUID(int=55)), self.intent(tenant_id=UUID(int=99))):
            self.assertNotEqual(first["run_id"], changed["run_id"])
            self.assertNotEqual(first["executor_id"], changed["executor_id"])
            with self.assertRaisesRegex(ExecutionRejected, "identity differs"): replay_decision(changed, first)

    def test_same_key_changed_actor_target_window_or_budget_conflicts_without_new_run(self):
        original = self.intent()
        for changes in (dict(actor_id=UUID(int=55)), dict(alert_id=UUID(int=55)),
                        dict(window=UTCWindow(NOW, NOW+timedelta(minutes=4))),
                        dict(budget_policy=policy(duration_seconds=60)), dict(budget_policy=policy(max_tool_calls=0)),
                        dict(budget_policy=policy(config_ref="another-explicit-policy.v1"))):
            current = self.intent(**changes)
            self.assertEqual((current["run_id"], current["executor_id"]), (original["run_id"], original["executor_id"]))
            self.assertNotEqual(current["request_hash"], original["request_hash"])
            with self.subTest(changes=changes), self.assertRaisesRegex(ExecutionRejected, "different start request"): replay_decision(current, original)

    def test_reauthenticated_same_actor_can_only_read_original_operation(self):
        original = self.intent()
        current = self.intent(principal=TenantPrincipal(frozenset({TENANT}), "another-current-credential-for-same-actor", True))
        self.assertEqual(original, current)
        decision = replay_decision(current, deepcopy(original))
        self.assertEqual(decision["decision"], "read_existing_only")
        self.assertEqual(decision["run_id"], original["run_id"])
        self.assertFalse(decision["may_begin"]);self.assertFalse(decision["external_call_authorized"])

    def test_empty_or_foreign_current_scope_is_refused_even_with_a_valid_old_intent(self):
        original = self.intent()
        for principal in (TenantPrincipal(), TenantPrincipal(frozenset({UUID(int=100)}), "foreign", False), None):
            with self.subTest(principal=principal), self.assertRaises(ExecutionRejected): self.intent(principal=principal)
        self.assertEqual(original, self.intent())

    def test_nonnil_typed_identity_is_required_for_all_four_ids(self):
        for name in ("tenant_id", "actor_id", "operation_key", "alert_id"):
            for value in (UUID(int=0), "not-a-uuid", True, 1, None):
                with self.subTest(name=name, value=value), self.assertRaises(ExecutionRejected): self.intent(**{name: value})

    def test_only_explicit_supported_manual_profile_and_request_version(self):
        for changes in (dict(profile="case_investigation"), dict(profile="all"), dict(trigger="automatic"), dict(trigger=""),
                        dict(request_version="alert_recon_start_request.v2"), dict(request_version=True)):
            with self.subTest(changes=changes), self.assertRaises(ExecutionRejected): self.intent(**changes)

    def test_window_is_revalidated_and_never_exceeds_existing_five_minute_policy(self):
        with self.assertRaises(ExecutionRejected): self.intent(window=UTCWindow(NOW, NOW+timedelta(minutes=5, microseconds=1)))
        with self.assertRaises(ExecutionRejected): self.intent(window={"start": NOW, "end": NOW})
        for start, end in ((NOW, NOW), (NOW.replace(tzinfo=None), NOW+timedelta(minutes=5))):
            forged = UTCWindow(NOW, NOW+timedelta(minutes=5));object.__setattr__(forged, "start", start);object.__setattr__(forged, "end", end)
            with self.assertRaises(ExecutionRejected): self.intent(window=forged)

    def test_budget_is_explicit_strict_bounded_and_only_the_current_fixed_path(self):
        for field, value in (("duration_seconds", 0), ("duration_seconds", 181), ("duration_seconds", True), ("duration_seconds", 1.0),
                             ("max_tool_calls", True), ("max_tool_calls", 2), ("max_model_calls", 1), ("max_tokens", 1),
                             ("max_cost_microusd", None), ("max_cost_microusd", 1), ("max_unsettled", 2), ("config_ref", "")):
            with self.subTest(field=field, value=value), self.assertRaises(ExecutionRejected): policy(**{field: value})
        for seconds in (1, 180): self.intent(budget_policy=policy(duration_seconds=seconds))
        with self.assertRaises(ExecutionRejected): self.intent(budget_policy=None)
        forged = policy();object.__setattr__(forged, "max_tool_calls", 2)
        with self.assertRaises(ExecutionRejected): self.intent(budget_policy=forged)

    def test_corrupt_retained_ref_hash_identity_or_extra_fields_are_refused(self):
        original = self.intent()
        for field, value in (("intent_ref", "alert-start-intent:" + "0" * 64), ("request_hash", "0" * 64),
                             ("run_id", str(UUID(int=55))), ("executor_id", str(UUID(int=55))), ("unexpected", "extra")):
            retained = deepcopy(original);retained[field] = value
            with self.subTest(field=field), self.assertRaises(ExecutionRejected): replay_decision(original, retained)
        for retained in ({}, [], {"request": None}):
            with self.assertRaises(ExecutionRejected): replay_decision(original, retained)

    def test_rehashed_self_consistent_forgery_still_must_match_supported_complete_structure(self):
        original = self.intent()
        for field, value in (("target", {"type": "case", "id": str(ALERT)}), ("objective", "full_case_judgment"),
                             ("profile_version", "investigation_profiles.v2"), ("runtime_version", "wrong.v1"),
                             ("extra_scope", "all")):
            retained = deepcopy(original);retained["request"][field] = value;self.rehash(retained)
            with self.subTest(field=field), self.assertRaises(ExecutionRejected): replay_decision(original, retained)
        retained = deepcopy(original);retained["request"]["budget_policy"]["max_tool_calls"] = True;self.rehash(retained)
        with self.assertRaises(ExecutionRejected): replay_decision(original, retained)

    def test_inputs_and_previous_policy_remain_unchanged_after_decisions_and_conflicts(self):
        original = self.intent();before = deepcopy(original)
        replay_decision(original);replay_decision(original, original)
        with self.assertRaises(ExecutionRejected): replay_decision(self.intent(budget_policy=policy(duration_seconds=60)), original)
        self.assertEqual(original, before)
        detached = replay_decision(original, original);detached["run_id"] = "changed"
        self.assertEqual(original, before)


if __name__ == "__main__": unittest.main()
