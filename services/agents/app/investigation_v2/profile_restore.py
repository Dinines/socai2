"""Pure frozen alert read-context restoration; caller verifies owned artifacts.

Current authentication/permission checks precede this function. The frozen
principal is historical binding data, not authority for the current caller.
The returned request grants no dispatch, restart or unknown-Run takeover.
"""
from __future__ import annotations

from datetime import datetime
import json
from uuid import UUID

from .business_profile import BusinessProfileRequest, CheckedBusinessTarget
from .execution_state import ExecutionRejected
from .execution_store import canonical_json, content_hash, scope_snapshot
from .recon_runtime_state import make_recon_plan, _runtime_copy
from .scope import (CheckedAlert, CheckedMemberSnapshot, PrincipalScope, SourceField,
                    TenantPrincipal, UTCWindow, initialize_scope)


def _require(value: bool, reason: str) -> None:
    if not value:
        raise ExecutionRejected(reason)


def restore_alert_read_request(*, current_principal: TenantPrincipal, begin_input: dict,
                               begin_state: dict) -> BusinessProfileRequest:
    """Rebuild the original M1 contract without loading a mutable current Alert."""
    try:
        _require(isinstance(current_principal, TenantPrincipal), "current authenticated principal required")
        current = PrincipalScope(current_principal.tenant_ids, current_principal.subject, current_principal.delegated)
        _require(isinstance(begin_input, dict) and isinstance(begin_state, dict), "owned frozen begin objects required")
        state = json.loads(canonical_json(begin_state))
        tenant, run = UUID(state["tenant_id"]), UUID(state["run_id"])
        _require(tenant.int != 0 and run.int != 0 and tenant in current.tenant_ids, "current principal cannot read frozen tenant")
        original = json.loads(canonical_json(begin_input))
        _require(set(original) == {"input", "scope_sources", "scope_hash"}
                 and set(original["input"]) == {"business_profile", "runtime_plan"}, "unsupported frozen begin shape")
        _require(content_hash(canonical_json(original)) == state["input_hash"] == state["persistence"]["body_hash"],
                 "frozen input hash mismatch")
        _require(state["input_snapshot_ref"] == "urn:uuid:" + state["persistence"]["body_artifact_id"]
                 and (state["persistence"]["tenant_id"], state["persistence"]["run_id"], state["persistence"]["stage_id"])
                 == (str(tenant), str(run), state["stage_id"])
                 and state["persistence"]["attempt_id"] is None, "frozen begin receipt mismatch")
        for key in ("event_id", "state_artifact_id", "body_artifact_id"):
            _require(UUID(state["persistence"][key]).int != 0, "frozen begin receipt UUID required")
        _require(type(state["persistence"]["seq"]) is int and state["persistence"]["seq"] >= 1, "frozen begin sequence required")
        checked, _ = _runtime_copy(state, datetime.fromisoformat(state["updated_at"]))
        _require(checked == state and not state["attempts"] and state["recon"]["phase"] == "ready"
                 and state["recon"]["claimed_at"] is None, "initial managed begin state required")
        controls, sources = state["scope"], original["scope_sources"]
        _require(original["scope_hash"] == state["scope_hash"] == content_hash(canonical_json(controls)), "frozen scope hash mismatch")
        _require(isinstance(sources, dict) and all(isinstance(key, str) and isinstance(value, str) for key, value in sources.items()),
                 "frozen source text map required")
        frozen = controls["principal"]
        frozen_principal = PrincipalScope(frozenset(UUID(value) for value in frozen["tenant_ids"]), frozen["subject"], frozen["delegated"])
        members = controls["member_snapshot"]
        _require(len(members["selected"]) == 1 and not members["omitted"] and members["total_members"] == 1,
                 "only fixed single-alert reads are supported")
        raw = members["selected"][0]
        source = raw["data_only_source"]
        _require(type(source["size_bytes"]) is int and source["size_bytes"] >= 0, "frozen source integer byte size required")
        text = sources[source["ref"]]
        digest = content_hash(text)
        _require(source == {"ref": "scope-source:" + digest, "sha256": digest, "size_bytes": len(text.encode("utf-8"))},
                 "frozen source reference hash or byte size mismatch")
        fields = tuple(SourceField(item["parameter"], item["record_ref"], item["path"], item["value"]) for item in raw["fields"])
        member = CheckedAlert(UUID(raw["tenant_id"]), UUID(raw["alert_id"]), raw["record_ref"], raw["ownership_check_ref"],
            raw["hostname"], raw["source_ip"], raw["dest_ip"], raw["dst_port"], raw["protocol"],
            tuple(UUID(item) for item in raw["source_event_ids"]), fields, text)
        snapshot = CheckedMemberSnapshot(members["source_ref"], members["total_members"], (member,),
                                         view_limitations=tuple(members["view_limitations"]))
        window = controls["conclusion_scope"]["window"]
        context = initialize_scope(principal=TenantPrincipal(frozen_principal.tenant_ids, frozen_principal.subject, frozen_principal.delegated),
            tenant_id=tenant, run_id=run, snapshot=snapshot,
            window=UTCWindow(datetime.fromisoformat(window["start"]), datetime.fromisoformat(window["end"])),
            target_type=controls["target_type"], policy_ref=controls["policy_ref"], revision=controls["revision"])
        restored_controls, restored_sources = scope_snapshot(context)
        _require(restored_controls == controls and restored_sources == sources, "frozen controls or source set differ from M1")
        descriptor = original["input"]["business_profile"]
        _require(descriptor["profile"] == "alert_recon", "frozen alert profile required")
        target = descriptor["target"]
        coverage = descriptor["member_coverage"]
        checked_target = CheckedBusinessTarget(tenant, target["type"], UUID(target["id"]), target["record_ref"],
            target["ownership_check_ref"], coverage["source_ref"], tuple(UUID(item) for item in coverage["all_member_ids"]),
            coverage["membership_revision"])
        request = BusinessProfileRequest(context, checked_target, descriptor["profile"], descriptor["trigger"],
                                          descriptor["objective"], descriptor["policy_ref"], descriptor["profile_version"])
        _require(request.descriptor == descriptor and make_recon_plan(request) == original["input"]["runtime_plan"] == state["recon"]["plan"],
                 "restored frozen profile or runtime plan mismatch")
        return request
    except ExecutionRejected:
        raise
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ExecutionRejected("frozen read context contract rejected") from None
