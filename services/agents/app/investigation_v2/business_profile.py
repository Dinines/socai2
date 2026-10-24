"""M1 pure business binding on top of the existing checked network scope.

Target authentication, ownership and consistent Case pagination are caller
preconditions. This contract verifies their structural binding, never reads a
Case, starts a Run, changes the explicit_set scope or grants execution rights.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import json
from uuid import UUID

from .execution_store import canonical_json, content_hash, scope_fingerprint
from .scope import POLICY_REF, ScopeContext, TenantPrincipal, initialize_scope

PROFILE_VERSION = "investigation_profiles.v1"
OBJECTIVE = "verify_source_network_observation"
_TARGETS = {"alert_recon": "alert", "case_investigation": "case"}


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def _identity(value) -> UUID:
    try:
        identity = UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        raise ValueError("nonnil_business_identity_required") from None
    _require(identity.int != 0, "nonnil_business_identity_required")
    return identity


def _reference(value, reason: str) -> None:
    _require(isinstance(value, str) and bool(value.strip()), reason)


@dataclass(frozen=True)
class CheckedBusinessTarget:
    tenant_id: UUID
    kind: str
    target_id: UUID
    record_ref: str
    ownership_check_ref: str
    member_source_ref: str
    member_ids: tuple[UUID, ...]
    membership_revision: str | None = None

    def __post_init__(self) -> None:
        for name in ("tenant_id", "target_id"):
            object.__setattr__(self, name, _identity(getattr(self, name)))
        _require(self.kind in ("alert", "case"), "unsupported_business_target")
        for name in ("record_ref", "ownership_check_ref", "member_source_ref"):
            _reference(getattr(self, name), "checked_target_reference_required")
        object.__setattr__(self, "member_ids", tuple(_identity(item) for item in self.member_ids))
        _require(bool(self.member_ids) and len(set(self.member_ids)) == len(self.member_ids),
                 "complete_unique_target_members_required")
        if self.kind == "alert":
            _require(self.member_ids == (self.target_id,), "alert_target_must_be_its_only_member")
            _require(self.membership_revision is None, "alert_has_no_case_membership_revision")
        else:
            _reference(self.membership_revision, "case_membership_revision_required")


def _check_scope(context: ScopeContext) -> None:
    _require(isinstance(context, ScopeContext), "checked_scope_required")
    _identity(context.tenant_id)
    _identity(context.run_id)
    _require(type(context.revision) is int and context.revision >= 1, "positive_scope_revision_required")
    try:
        expected = initialize_scope(
            principal=TenantPrincipal(context.principal.tenant_ids, context.principal.subject, context.principal.delegated),
            tenant_id=context.tenant_id, run_id=context.run_id, snapshot=context.member_snapshot,
            window=context.query_scope.window, policy_ref=context.policy_ref)
    except (AttributeError, TypeError, ValueError):
        raise ValueError("scope_differs_from_checked_M1_contract") from None
    _require(context == replace(expected, revision=context.revision), "scope_differs_from_checked_M1_contract")


@dataclass(frozen=True)
class BusinessProfileRequest:
    context: ScopeContext
    target: CheckedBusinessTarget
    profile: str
    trigger: str
    objective: str
    policy_ref: str
    profile_version: str = PROFILE_VERSION

    def __post_init__(self) -> None:
        _check_scope(self.context)
        _require(isinstance(self.target, CheckedBusinessTarget), "checked_business_target_required")
        _require(isinstance(self.profile, str) and self.profile in _TARGETS, "unsupported_business_profile")
        _require(self.profile_version == PROFILE_VERSION, "unsupported_profile_version")
        _require(self.trigger in ("manual", "automatic"), "explicit_trigger_required")
        _require(self.target.kind == _TARGETS[self.profile], "profile_target_mismatch")
        _require(self.target.tenant_id == self.context.tenant_id, "target_tenant_mismatch")
        _require(self.policy_ref == self.context.policy_ref == POLICY_REF, "business_policy_mismatch")
        _require(self.objective == self.context.conclusion_scope.objective == OBJECTIVE,
                 "business_objective_exceeds_current_policy")
        snapshot = self.context.member_snapshot
        _require(self.target.member_source_ref == snapshot.source_ref, "target_member_source_mismatch")
        selected = tuple(item.alert_id for item in snapshot.selected)
        omitted = tuple(item.alert_id for item in snapshot.omitted)
        _require(snapshot.total_members == len(self.target.member_ids)
                 and snapshot.unlisted_members == 0
                 and set(selected + omitted) == set(self.target.member_ids), "target_members_not_fully_bound")
        if self.profile == "alert_recon":
            _require(selected == (self.target.target_id,) and not omitted, "alert_scope_must_select_target")
            member = snapshot.selected[0]
            _require((self.target.record_ref, self.target.ownership_check_ref)
                     == (member.record_ref, member.ownership_check_ref), "alert_target_provenance_mismatch")

    @property
    def descriptor(self) -> dict:
        snapshot, target = self.context.member_snapshot, self.target
        selected = [str(item.alert_id) for item in snapshot.selected]
        body = {
            "schema": PROFILE_VERSION, "profile": self.profile, "profile_version": self.profile_version,
            "tenant_id": str(self.context.tenant_id), "run_id": str(self.context.run_id),
            "target": {"type": target.kind, "id": str(target.target_id), "record_ref": target.record_ref,
                       "ownership_check_ref": target.ownership_check_ref},
            "objective": self.objective, "policy_ref": self.policy_ref, "trigger": self.trigger,
            "scope_hash": scope_fingerprint(self.context), "scope_revision": self.context.revision,
            "delivery_target": {"type": target.kind, "id": str(target.target_id)},
            "completion_basis": "target_alert" if self.profile == "alert_recon" else "frozen_case_members",
            "member_coverage": {
                "source_ref": target.member_source_ref, "membership_revision": target.membership_revision,
                "all_member_ids": [str(item) for item in target.member_ids], "selected_member_ids": selected,
                "omitted_members": [{"id": str(item.alert_id), "reason": item.reason} for item in snapshot.omitted],
                "view_limitations": list(snapshot.view_limitations),
                "selection_covers_target": len(selected) == len(target.member_ids),
                "investigated_members": 0, "evidence_coverage": "not_started"},
        }
        body["binding_ref"] = "profile:" + content_hash(canonical_json(body))
        return json.loads(canonical_json(body))
