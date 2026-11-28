"""Pure existing-alert selection from durable lake versions; never dispatches."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from app.services.lake_ingress import ABSENT, BLOCKED, decode, json_text, nested

LEGACY_VERSION = "socai2.lake-alert-selection.v1"
VERSION = "socai2.lake-alert-selection.v2"
CANDIDATES = {"new_alert_candidate", "update_candidate", "close_candidate"}
REF_FIELDS = ("tenant_id", "source_namespace", "mapping_version", "event_id", "source_version", "event_time", "class_uid")
SCOPE_PATHS = {"metadata.product.vendor_name", "metadata.product.name", "metadata.product.uid"}


def integers(value):
    return isinstance(value, list) and all(type(n) is int and 0 <= n < 2**32 for n in value) and len(set(value)) == len(value)


def validate_read_limits(limits):
    if not isinstance(limits, dict) or set(limits) != {
        "max_records", "max_result_bytes", "query_timeout_seconds",
        "connect_timeout_seconds", "send_receive_timeout_seconds",
    }:
        raise ValueError("explicit_read_limits_required")
    if any(type(value) is not int or value <= 0 for value in limits.values()):
        raise ValueError("invalid_read_limits")


@dataclass(frozen=True)
class SelectionPolicy:
    body: dict
    digest: str

    @classmethod
    def load(cls, path):
        raw = Path(path).read_bytes()
        body = json.loads(raw)
        keys = {"version", "database", "tenant_id", "source_namespace", "mapping_version", "ocsf_version",
                "identity_scope_paths", "rules", "read_limits"}
        if body.get("version") == VERSION:
            keys |= {"identity_scope", "alert_lifecycle"}
        if set(body) != keys or body["version"] not in {LEGACY_VERSION, VERSION}:
            raise ValueError("invalid_selection_policy_shape")
        immutable = body["version"] == VERSION
        if immutable and (body["identity_scope"] != "global" or body["alert_lifecycle"] != "immutable"):
            raise ValueError("invalid_immutable_source_contract")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", body["database"]):
            raise ValueError("invalid_selection_database")
        body["tenant_id"] = str(UUID(body["tenant_id"]))
        if (not isinstance(body["source_namespace"], str) or not body["source_namespace"].strip()
                or body["mapping_version"] != "spirithub-ocsf-lake-v1" or body["ocsf_version"] != "1.9.0"):
            raise ValueError("invalid_selection_source_contract")
        paths = body["identity_scope_paths"]
        if (immutable and paths != [] or not immutable and (
                not isinstance(paths, list) or not paths or len(set(paths)) != len(paths) or set(paths) - SCOPE_PATHS)):
            raise ValueError("invalid_identity_scope")
        if not isinstance(body["rules"], dict) or not body["rules"]:
            raise ValueError("selection_rules_required")
        common = {"mode", "category_uid", "activity_ids", "identity_path", "identity_semantics_confirmed"}
        finding = {"create_activity_ids", "update_activity_ids", "close_activity_ids", "status_ids", "inactive_status_ids"}
        for key, rule in body["rules"].items():
            if not re.fullmatch(r"[1-9][0-9]*", key) or int(key) >= 2**32 or not isinstance(rule, dict):
                raise ValueError("invalid_class_rule")
            mode = rule.get("mode")
            optional_initial = {"initial_activity_ids"} if immutable and mode == "finding" and "initial_activity_ids" in rule else set()
            if mode not in {"finding", "atomic"} or set(rule) != common | (finding if mode == "finding" else set()) | optional_initial:
                raise ValueError("invalid_class_rule_shape")
            if (type(rule["category_uid"]) is not int or not 0 <= rule["category_uid"] < 2**32
                    or type(rule["identity_semantics_confirmed"]) is not bool
                    or rule["identity_path"] != ("finding_info.uid" if mode == "finding" and not immutable else "metadata.uid")
                    or not integers(rule["activity_ids"]) or not rule["activity_ids"]):
                raise ValueError("invalid_class_rule_values")
            if mode == "finding":
                if any(not integers(rule[n]) for n in finding):
                    raise ValueError("invalid_lifecycle_values")
                activities = [n for name in ("create_activity_ids", "update_activity_ids", "close_activity_ids") for n in rule[name]]
                if (len(set(activities)) != len(activities) or not set(activities) <= set(rule["activity_ids"])
                        or not set(rule["inactive_status_ids"]) <= set(rule["status_ids"])):
                    raise ValueError("conflicting_lifecycle_rules")
                if optional_initial:
                    initial = rule["initial_activity_ids"]
                    if (not integers(initial) or not initial or not set(initial) <= set(rule["activity_ids"])
                            or set(initial) & set(rule["update_activity_ids"] + rule["close_activity_ids"])):
                        raise ValueError("invalid_immutable_initial_activities")
        validate_read_limits(body["read_limits"])
        return cls(body, hashlib.sha256(raw).hexdigest())

    def scope(self):
        return {k: self.body[k] for k in ("tenant_id", "source_namespace", "mapping_version")}

    @property
    def immutable(self):
        return self.body["version"] == VERSION


def ref_value(row):
    result = {k: row[k] for k in REF_FIELDS}
    for name in ("tenant_id", "event_id"):
        result[name] = str(UUID(str(result[name])))
    when = result["event_time"]
    if isinstance(when, str):
        when = datetime.fromisoformat(when)
    if isinstance(when, datetime):
        result["event_time"] = when.replace(tzinfo=UTC).isoformat() if when.tzinfo is None else when.astimezone(UTC).isoformat()
    return result


def field(document, path, *, partial):
    """Absent root may fall back; null/invalid ancestors cannot be hidden."""
    root = nested(document, tuple(path.split(".")))
    fallback = nested(document, ("unmapped", "spirithub", "partial_fields", *path.split("."))) if partial else ABSENT
    if root is not ABSENT:
        conflict = fallback is not ABSENT and fallback is not BLOCKED and (
            type(root) is not type(fallback) or root != fallback)
        return root, "$." + path, conflict
    if fallback is not ABSENT:
        return fallback, "$.unmapped.spirithub.partial_fields." + path, False
    return ABSENT, None, False


def valid_id(value):
    return isinstance(value, str) and bool(value.strip())


def identity(document, policy, rule, *, partial):
    problems, scope = [], []
    for path in policy.body["identity_scope_paths"]:
        value = nested(document, tuple(path.split(".")))
        if not valid_id(value):
            problems.append("identity_scope_missing_or_invalid")
        else:
            scope.append([path, value])
    log_id = nested(document, ("metadata", "uid"))
    if not valid_id(log_id):
        problems.append("source_record_id_missing_or_invalid")
    source_id, path, conflict = field(document, rule["identity_path"], partial=partial)
    if policy.immutable:
        # Only the root metadata.uid owns the confirmed global identity.
        # Retain that identity on a partial conflict for batch reconciliation,
        # but never let a partial field supply a missing root ID.
        source_id = log_id
        path = "$.metadata.uid" if log_id is not ABSENT and log_id is not BLOCKED else None
    if conflict:
        problems.append("subject_id_conflict")
    if not valid_id(source_id):
        problems.append("subject_id_missing_or_invalid")
    if not rule["identity_semantics_confirmed"]:
        problems.append("producer_identity_semantics_unconfirmed")
    subject_id = None
    if valid_id(source_id) and len(scope) == len(policy.body["identity_scope_paths"]) and (policy.immutable or not conflict):
        identity_parts = (["socai2.source-subject.v2", "global", "metadata.uid", source_id] if policy.immutable else
            ["socai2.source-subject.v1", policy.body["tenant_id"], policy.body["source_namespace"], scope, rule["identity_path"], source_id])
        subject_id = str(uuid5(NAMESPACE_URL, json_text(identity_parts)))
    return {"source_subject_id": subject_id, "source_id_path": path, "scope_paths": list(policy.body["identity_scope_paths"]),
            "semantics_confirmed": rule["identity_semantics_confirmed"], "ready": not problems, "blockers": sorted(set(problems))}


def select_alert(row, policy):
    ref = ref_value(row)
    if any(ref[k] != value for k, value in policy.scope().items()):
        raise ValueError("lake_record_outside_selection_scope")
    delivery_key = str(uuid5(NAMESPACE_URL, json_text(["socai2.lake-alert-delivery.v1", ref])))
    result = {"schema_version": policy.body["version"], "policy_digest": policy.digest,
        "decision_id": str(uuid5(UUID(delivery_key), policy.digest)), "delivery_key": delivery_key,
        "lake_ref": ref, "action": "review", "reasons": [], "reported_class_uid": row["class_uid"],
        "target_class_uid": None, "class_path": None, "activity_id": None, "is_alert": None,
        "is_alert_path": None, "quality": row["parse_status"], "identity": None, "execution": "not_dispatched"}
    if policy.immutable:
        result.update(identity_scope="global", alert_lifecycle="immutable")

    def finish(action, *reasons):
        result.update(action=action, reasons=list(reasons))
        return result

    document, _, _, version = decode(row["ocsf_json"].encode("utf-8")) if row["ocsf_json"] else (None, None, None, None)
    if document is None:
        return finish("review", "no_parseable_ocsf_object")
    if version != row["source_version"]:
        raise ValueError("lake_original_version_mismatch")
    if policy.immutable:
        # Keep the global identity even on a later validation failure so a
        # conflicting version cannot hide behind a different class/flag.
        result["identity"] = identity(document, policy, {
            "identity_path": "metadata.uid",
            "identity_semantics_confirmed": all(r["identity_semantics_confirmed"] for r in policy.body["rules"].values()),
        }, partial=False)
    if nested(document, ("metadata", "version")) != policy.body["ocsf_version"]:
        return finish("review", "ocsf_version_missing_or_unsupported")
    partial = nested(document, ("unmapped", "spirithub", "mapping_status")) == "partial"
    classification, class_path = document, "$.class_uid"
    cls = document.get("class_uid")
    if type(cls) is not int or not 0 <= cls < 2**32 or cls != row["class_uid"]:
        return finish("review", "reported_class_invalid")
    stated_target = nested(document, ("unmapped", "spirithub", "classification", "class_uid"))
    if partial and cls != 0 and stated_target is not ABSENT and stated_target != cls:
        return finish("review", "reported_partial_class_conflict")
    if cls == 0:
        if not partial:
            return finish("review", "unclassified_record")
        classification = nested(document, ("unmapped", "spirithub", "classification"))
        if not isinstance(classification, dict):
            return finish("review", "partial_target_class_missing")
        cls = classification.get("class_uid")
        class_path = "$.unmapped.spirithub.classification.class_uid"
        if type(cls) is not int or not 0 < cls < 2**32:
            return finish("review", "partial_target_class_invalid")
    result.update(target_class_uid=cls, class_path=class_path)
    flag, flag_path, flag_conflict = field(document, "is_alert", partial=partial)
    result["is_alert_path"] = flag_path
    if flag_conflict:
        return finish("review", "alert_flag_conflict")
    if flag is not ABSENT and type(flag) is not bool:
        return finish("review", "alert_flag_invalid")
    result["is_alert"] = flag if type(flag) is bool else None
    rule = policy.body["rules"].get(str(cls))
    if rule is None:
        return finish("review", "alert_class_rule_missing") if flag is True else finish("lake_only", "explicit_non_alert" if flag is False else "unmarked_activity")
    activity, category, typ = (classification.get(k) for k in ("activity_id", "category_uid", "type_uid"))
    if (any(type(v) is not int for v in (activity, category, typ)) or category != rule["category_uid"]
            or activity not in rule["activity_ids"] or typ != cls*100+activity):
        return finish("review", "class_activity_contract_invalid")
    result["activity_id"] = activity
    result["identity"] = identity(document, policy, rule, partial=partial)
    if rule["mode"] == "finding":
        status, _, conflict = field(document, "status_id", partial=partial)
        if conflict or status is not ABSENT and (type(status) is not int or status not in rule["status_ids"]):
            return finish("review", "finding_status_invalid_or_conflicting")
        if policy.immutable and (activity in rule["close_activity_ids"] or activity in rule["update_activity_ids"]
                                 or status in rule["inactive_status_ids"]):
            return finish("review", "immutable_source_lifecycle_conflict")
        if activity in rule["close_activity_ids"]:
            return finish("close_candidate", "source_finding_close_not_local_business_close")
        if activity in rule["update_activity_ids"] or status in rule["inactive_status_ids"]:
            return finish("update_candidate", "source_finding_update_existing_only")
        initial = rule.get("initial_activity_ids", rule["create_activity_ids"]) if policy.immutable else rule["create_activity_ids"]
        if activity not in initial:
            return finish("review", "finding_activity_semantics_unmapped")
        if flag is ABSENT:
            return finish("review", "finding_alert_flag_missing")
    if flag is True:
        return finish("new_alert_candidate", "explicit_alert_signal")
    return finish("lake_only", "explicit_non_alert" if flag is False else "unmarked_activity")


def reconcile_immutable_versions(decisions):
    """Hold every candidate in a conflicting group; never pick by row order."""
    versions = {}
    for decision in decisions:
        identity = (decision.get("identity") or {}).get("source_subject_id")
        if decision.get("alert_lifecycle") == "immutable" and identity:
            versions.setdefault(identity, set()).add(decision["lake_ref"]["source_version"])
    for decision in decisions:
        identity = (decision.get("identity") or {}).get("source_subject_id")
        if decision.get("alert_lifecycle") == "immutable" and len(versions.get(identity, ())) > 1:
            if decision["action"] in CANDIDATES:
                decision["action"] = "review"
            decision["reasons"] = list(dict.fromkeys([*decision["reasons"], "immutable_subject_content_conflict"]))
    return decisions


def delivery_effect(decision, *, subject_exists, delivered_keys, subject_version=None):
    """Prospective transaction effect. No lookup, write, publish, or model call."""
    if decision.get("alert_lifecycle") != "immutable" and decision["delivery_key"] in delivered_keys:
        return "duplicate_version"
    action = decision["action"]
    if action not in CANDIDATES:
        return action
    if not decision["identity"] or not decision["identity"]["ready"]:
        return "hold_identity"
    if decision.get("alert_lifecycle") == "immutable":
        if subject_exists:
            if not subject_version:
                return "hold_existing_version_unproven"
            if subject_version != decision["lake_ref"]["source_version"]:
                return "hold_immutable_content_conflict"
            return "duplicate_version"
        if decision["delivery_key"] in delivered_keys:
            return "hold_existing_subject_unproven"
        return "create_alert_and_initial_task" if action == "new_alert_candidate" else "review"
    if action == "new_alert_candidate":
        return "append_material" if subject_exists else "create_alert_and_initial_task"
    if not subject_exists:
        return "hold_unlinked_lifecycle"
    return "append_source_close" if action == "close_candidate" else "append_source_update"
