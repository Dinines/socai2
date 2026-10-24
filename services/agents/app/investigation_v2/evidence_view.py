"""M4.1a: a bounded, immutable model view of retained M2 source material.

This pure builder checks attribution and content, not whether an artifact was
really committed. The trusted caller must verify that claim before supplying a
CommittedMaterial. Its sha256 hashes canonical_json(query_result); a different
stored byte representation can be identified separately by stored_sha256.
No source JSON, credentials, expected answers or model summaries enter the view.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from typing import Any
from uuid import UUID

from app.llm.contract_rules import LLMContractViolation, LLMInputContract
from app.investigation_v2.activity_records import _time, _validate_response
from .execution_store import canonical_json, content_hash, scope_fingerprint
from .network_identity import same_network_filter
from .scope import CAPABILITY, POLICY_REF, QueryRequest, ScopeContext, UTCWindow, admit_query

MAX_MODEL_BYTES = 12 * 1024
MAX_EXCERPT_BYTES = 512
NAMESPACE = "clickhouse.aisoc.raw_events"
_HASH = re.compile(r"^[0-9a-f]{64}$")
_FILTERS = ("hostname", "source_ip", "dest_ip", "dst_port", "protocol")
_FIELDS = ("event_id", "tenant_id", "event_time", "class_uid", "category_uid", "activity_id",
           "action", "outcome", "src_hostname", "source_ip", "dest_ip", "dst_port", "protocol", "connector_type")
_VISIBLE = {"observed_at": "event_time", "hostname": "src_hostname", "source_ip": "source_ip",
            "dest_ip": "dest_ip", "dst_port": "dst_port", "protocol": "protocol",
            "action": "action", "outcome": "outcome"}


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def _digest(value: Any) -> str:
    _require(isinstance(value, str) and bool(_HASH.fullmatch(value)), "invalid_content_hash")
    return value


@dataclass(frozen=True)
class CommittedMaterial:
    tenant_id: UUID
    source_run_id: UUID | None
    artifact_id: UUID
    sha256: str
    retention: str = "committed"
    provenance_kind: str = "retained_tool_output"
    derived_from: str | None = None
    stored_sha256: str | None = None

    def __post_init__(self) -> None:
        for name in ("tenant_id", "source_run_id", "artifact_id"):
            value = getattr(self, name)
            if name == "source_run_id" and value is None:
                continue
            value = UUID(str(value))
            _require(value.int != 0, "nonnil_material_identity_required")
            object.__setattr__(self, name, value)
        _digest(self.sha256)
        if self.stored_sha256 is not None:
            _digest(self.stored_sha256)
        _require(self.retention == "committed", "material_not_committed")
        _require(self.provenance_kind in {"retained_tool_output", "derived_fixture"}, "unsupported_material_provenance")
        if self.provenance_kind == "derived_fixture":
            _require(isinstance(self.derived_from, str) and bool(self.derived_from.strip()), "derived_source_ref_required")
        else:
            _require(self.derived_from is None, "unexpected_derived_source_ref")


@dataclass(frozen=True)
class EvidenceView:
    canonical_doc: str

    @property
    def snapshot_ref(self) -> str:
        return json.loads(self.canonical_doc)["model_view"]["snapshot_ref"]

    @property
    def scope_hash(self) -> str:
        return json.loads(self.canonical_doc)["scope_hash"]

    @property
    def revision(self) -> int:
        return json.loads(self.canonical_doc)["revision"]

    @property
    def model_view(self) -> dict:
        return json.loads(self.canonical_doc)["model_view"]

    @property
    def index(self) -> dict:
        return json.loads(self.canonical_doc)["index"]


class EvidenceProjectionBlocked(ValueError):
    """Required material checks passed; no consumable EvidenceView was made."""

    def __init__(self, reason: str, receipt: dict) -> None:
        super().__init__(reason)
        self._canonical_receipt = canonical_json(receipt)

    @property
    def receipt(self) -> dict:
        return json.loads(self._canonical_receipt)


def _material_dict(material: CommittedMaterial) -> dict:
    result = json.loads(canonical_json(asdict(material)))
    result["artifact_ref"] = "urn:uuid:" + str(material.artifact_id)
    result["stored_sha256"] = material.stored_sha256 or material.sha256
    return result


def _source_version(row: dict) -> str:
    """Recheck the API's complete projection, independent of retained prefixes."""
    _require(all(key in row for key in _FIELDS), "source_projection_incomplete")
    _require(all(type(row[key]) is int for key in ("class_uid", "category_uid", "activity_id", "dst_port")),
             "invalid_source_integer")
    _require(all(isinstance(row[key], str) for key in _FIELDS if key not in
                 {"class_uid", "category_uid", "activity_id", "dst_port"}), "invalid_source_string")
    _require(type(row.get("outcome_provided")) is bool and bool(row["outcome"]), "invalid_outcome_provenance")
    _require(row["outcome_provided"] or row["outcome"] == "unknown", "invalid_outcome_default")
    _require(type(row.get("duplicate_count")) is int and row["duplicate_count"] >= 1, "invalid_duplicate_count")
    projection = {key: row[key] for key in _FIELDS}
    projection.update(namespace=row["namespace"], outcome_provided=row["outcome_provided"])
    for name in ("raw_payload", "ocsf_json"):
        projection[name] = {key: row[name][key] for key in ("sha256", "original_bytes")}
    version = content_hash(canonical_json(projection))
    _require(version == _digest(row.get("content_hash")), "source_content_hash_mismatch")
    return version


def _excerpt(text: str) -> str:
    _require(len(text.encode("utf-8")) <= MAX_EXCERPT_BYTES, "data_only_excerpt_exceeds_byte_limit")
    # Validate the actual text too, so wrapping it in JSON cannot hide a raw-log
    # signature from the existing contract's string scan.
    LLMInputContract.validate([{"role": "user", "content": text}])
    return text


def _message(body: dict) -> tuple[str | None, str]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict:
        result = {}
        for key, value in pairs:
            _require(key not in result, "ambiguous_source_json_keys")
            result[key] = value
        return result

    if body["truncated"]:
        return None, "not_extractable"
    try:
        parsed = json.loads(body["text"], object_pairs_hook=unique_object)
    except json.JSONDecodeError:
        return None, "not_json"
    except RecursionError:
        return None, "json_nesting_limit"
    except ValueError:
        return None, "ambiguous_json"
    if not isinstance(parsed, dict):
        return None, "unsupported_body_shape"
    if "message" not in parsed:
        return None, "absent"
    if not isinstance(parsed["message"], str):
        return None, "unsupported_type"
    try:
        message_bytes = len(parsed["message"].encode("utf-8"))
    except UnicodeEncodeError:
        return None, "invalid_unicode"
    if message_bytes > MAX_EXCERPT_BYTES:
        return None, "over_limit"
    try:
        return _excerpt(parsed["message"]), "present"
    except LLMContractViolation:
        return None, "input_contract_rejected"


def _parameters(context: ScopeContext, member: Any, values: dict) -> dict:
    _require(isinstance(values, dict), "query_parameters_missing")
    _require(set(values) == {*_FILTERS, "start", "end", "limit", "tenant_id"}, "query_parameters_incomplete")
    _require(values["tenant_id"] == str(context.tenant_id), "query_tenant_mismatch")
    for key in _FILTERS:
        _require(same_network_filter(key, values[key], getattr(member, key)),
                 "query_field_outside_scope")
    request = QueryRequest(context.tenant_id, context.run_id, context.revision, member.alert_id,
                           UTCWindow(_time(values["start"]), _time(values["end"])), member.fields,
                           limit=values["limit"])
    _require(admit_query(context, request).allowed, "query_outside_current_scope")
    return values


def build_evidence_view(context: ScopeContext, query_result: dict,
                        artifact_ref: CommittedMaterial, revision: int) -> EvidenceView:
    """Bind one retained M2 response to the current checked scope; never query.

    Repeated retrievals retain stable event refs/versions, while their snapshots
    and retention provenance differ. A historical source Run is allowed and is
    explicitly named. A fixture derivation is never presented as a new query.
    """
    _require(isinstance(context, ScopeContext) and context.policy_ref == POLICY_REF, "trusted_scope_required")
    _require(isinstance(artifact_ref, CommittedMaterial), "committed_material_required")
    _require(type(revision) is int and revision > 0, "positive_view_revision_required")
    _require(artifact_ref.tenant_id == context.tenant_id, "material_tenant_mismatch")
    body = canonical_json(query_result)
    _require(content_hash(body) == artifact_ref.sha256, "material_payload_hash_mismatch")
    payload = json.loads(body)  # Detach every caller-owned nested value.
    _require(isinstance(payload, dict) and payload.get("tool") == CAPABILITY, "unexpected_tool_material")
    status = payload.get("status")
    _require(status in {"ok", "empty", "unavailable", "error", "rejected"}, "invalid_query_status")
    caller = payload.get("caller_receipt")
    _require(isinstance(caller, dict), "caller_receipt_required")
    for key, expected in (("tenant_id", str(context.tenant_id)), ("policy_ref", context.policy_ref)):
        _require(key not in caller or caller[key] == expected, "caller_identity_mismatch")
    if "run_id" in caller:
        _require(caller["run_id"] == str(artifact_ref.source_run_id), "source_run_mismatch")
    member_id = caller.get("member_id")
    members = context.query_scope.members
    member = next((m for m in members if str(m.alert_id) == member_id), None)
    if member_id is None and len(members) == 1 and status not in {"ok", "empty"}:
        member = members[0]
    _require(member is not None, "query_member_outside_scope")
    receipt = payload.get("query_receipt")
    params = None
    if receipt is not None:
        _require(isinstance(receipt, dict), "invalid_query_receipt")
        params = _parameters(context, member, receipt.get("parameters", {}))
        _validate_response(payload, params)
        _require(receipt.get("namespace") == NAMESPACE and type(receipt.get("executed")) is bool,
                 "query_execution_receipt_missing")
        if receipt["executed"]:
            _require(UUID(str(receipt.get("query_id"))).int != 0, "query_identity_missing")
        else:
            _require(receipt.get("query_id") is None, "unexecuted_query_has_identity")
        if "request_parameters" in caller:
            claimed = {"tenant_id": str(context.tenant_id), **caller["request_parameters"]}
            _parameters(context, member, claimed)
            for key in params:
                _require((_time(params[key]) == _time(claimed[key])) if key in {"start", "end"}
                         else same_network_filter(key, params[key], claimed[key]), "caller_query_parameter_mismatch")
    else:
        _require(status in {"unavailable", "error", "rejected"} and not payload.get("rows")
                 and payload.get("row_count", 0) == 0 and not payload.get("truncated", False)
                 and payload.get("available", False) is False, "missing_query_receipt_cannot_supply_evidence")
    if status in {"ok", "empty"}:
        _require(receipt["executed"] is True and caller.get("http_attempted") is True,
                 "successful_query_not_executed")
        _require(type(receipt.get("returned_count")) is int and receipt["returned_count"] == len(payload["rows"]),
                 "query_receipt_count_mismatch")
    material = _material_dict(artifact_ref)
    index: dict[str, dict] = {}
    events: dict[str, dict] = {}
    versions: dict[str, set[str]] = {}
    claims: dict[str, set[str]] = {}
    retained_prefixes: dict[str, dict[str, str]] = {}
    gaps = {"bounded_query_only", "no_global_identity_completeness", "no_authorization_source", "no_behavior_corroboration"}
    rows = payload.get("rows", [])
    for position, row in enumerate(rows):
        version = _source_version(row)
        identity = f"{NAMESPACE}:{context.tenant_id}:{UUID(row['event_id'])}"
        claimed = row.get("conflict_version_hashes")
        _require(isinstance(claimed, list) and len(claimed) == len(set(claimed)), "invalid_conflict_versions")
        for item in claimed:
            _digest(item)
        state = row.get("identity_state")
        _require(state in {"conflict", "single_version_observed"}, "invalid_source_identity_state")
        _require((state == "conflict" and len(claimed) >= 2 and version in claimed)
                 or (state == "single_version_observed" and not claimed), "inconsistent_conflict_versions")
        versions.setdefault(identity, set()).add(version)
        if identity in claims:
            _require(claims[identity] == set(claimed), "inconsistent_conflict_version_sets")
        claims[identity] = set(claimed)
        ref = "source:" + content_hash(canonical_json([identity, version]))
        fields = {name: row[source] for name, source in _VISIBLE.items()}
        event = {"ref": ref, "identity": identity, "version": version, "fields": fields,
                 "conflict": state == "conflict", "missing_version_hashes": []}
        excerpt, message_state = _message(row["raw_payload"])
        if excerpt is not None:
            event["data_only_excerpt"] = excerpt
        provenance = {"source_path": f"$.rows[{position}]", "duplicate_count": row["duplicate_count"],
                      "bodies": {name: {"full_sha256": row[name]["sha256"], "original_bytes": row[name]["original_bytes"],
                                        "retained_sha256": content_hash(row[name]["text"]),
                                        "retained_bytes": row[name]["retained_bytes"], "truncated": row[name]["truncated"]}
                                 for name in ("raw_payload", "ocsf_json")},
                      "message_extraction": message_state}
        if any(row[name]["truncated"] for name in ("raw_payload", "ocsf_json")):
            gaps.add("source_body_truncated")
        if ref in events:
            prior = events[ref]
            _require({k: v for k, v in prior.items() if k != "data_only_excerpt"}
                     == {k: v for k, v in event.items() if k != "data_only_excerpt"},
                     "same_source_version_has_inconsistent_visible_material")
            for name in ("raw_payload", "ocsf_json"):
                old, new = retained_prefixes[ref][name], row[name]["text"]
                _require(old.startswith(new) or new.startswith(old), "same_version_retained_prefix_mismatch")
                if len(new) > len(old):
                    retained_prefixes[ref][name] = new
            if excerpt is not None:
                _require("data_only_excerpt" not in prior or prior["data_only_excerpt"] == excerpt,
                         "same_version_message_mismatch")
                prior["data_only_excerpt"] = excerpt
                index[ref]["excerpt_path"] = "raw_payload.text:$.message"
            index[ref]["retrievals"].append(provenance)
            continue
        events[ref] = event
        retained_prefixes[ref] = {name: row[name]["text"] for name in ("raw_payload", "ocsf_json")}
        full_projection = {"identity": identity, "version": version, "fields": fields,
                           "body_hashes": {name: row[name]["sha256"] for name in ("raw_payload", "ocsf_json")}}
        index[ref] = {"kind": "source_event", "identity": identity, "version": version,
                      "projection_hash": content_hash(canonical_json(full_projection)), "provenance": material,
                      "field_paths": {name: source for name, source in _VISIBLE.items()},
                      "excerpt_path": "raw_payload.text:$.message" if excerpt is not None else None,
                      "retrievals": [provenance]}
    for event in events.values():
        states = {item["message_extraction"] for item in index[event["ref"]]["retrievals"]}
        if not states & {"present", "absent"}:
            event["excerpt_gaps"] = sorted(states)
            gaps.update("source_excerpt_" + state for state in states)
        identity = event["identity"]
        observed, declared = versions[identity], claims[identity]
        _require(not declared or observed.issubset(declared), "conflict_omits_delivered_version")
        # M2 must label every delivered version of an identity consistently.
        _require(len(observed) == 1 or event["conflict"], "unmarked_source_identity_conflict")
        _require(not declared or event["conflict"], "inconsistent_source_identity_conflict")
        missing = sorted(declared - observed)
        event["missing_version_hashes"] = missing
        index[event["ref"]]["conflict_version_hashes"] = sorted(declared)
        if event["conflict"]:
            gaps.add("source_identity_conflict")
        if missing:
            _require(payload["truncated"] is True, "undelivered_version_without_query_truncation")
            gaps.add("undelivered_conflict_versions")
        index[event["ref"]]["model_visible_sha256"] = content_hash(canonical_json(event))
    alert_bytes = len(member.data_only_text.encode("utf-8"))
    alert_digest = content_hash(member.data_only_text)
    alert_content = {"identity": str(member.alert_id), "source_event_ids": [str(v) for v in member.source_event_ids],
                     "data_only_text": member.data_only_text}
    # No oversized text needs to be copied into a projection or its receipt.
    # Valid existing views retain the same alert identity and document format.
    alert_identity = (alert_content if alert_bytes <= MAX_EXCERPT_BYTES else
                      {"identity": str(member.alert_id), "source_event_ids": alert_content["source_event_ids"],
                       "data_only_sha256": alert_digest, "data_only_bytes": alert_bytes})
    alert_ref = "alert:" + content_hash(canonical_json(alert_identity))
    alert = {"ref": alert_ref, "source_event_ids": alert_content["source_event_ids"],
             "data_only_text": alert_content["data_only_text"]}
    index[alert_ref] = {"kind": "alert_claim", "identity": str(member.alert_id), "record_ref": member.record_ref,
                        "ownership_check_ref": member.ownership_check_ref,
                        "field_paths": {f.parameter: {"record_ref": f.record_ref, "path": f.path} for f in member.fields},
                        "data_only_sha256": alert_digest, "data_only_bytes": alert_bytes}
    # M2 sets executed before its backend call: a failed/unconfigured source
    # cannot confirm SQL execution merely because that declaration is true.
    declared_executed = receipt["executed"] if receipt is not None else None
    if status in {"ok", "empty"}:
        executed, execution = True, "query_executed"
    elif receipt is not None and declared_executed:
        executed, execution = None, "query_attempted"
    else:
        executed = False if declared_executed is False or caller.get("http_attempted") is False else None
        execution = "not_attempted" if executed is False else "unknown"
    if status not in {"ok", "empty"}:
        gaps.update({"source_" + status, "query_execution_" + execution})
    if status == "empty":
        gaps.add("empty_within_query_only")
    if payload.get("truncated", False):
        gaps.add("query_rows_truncated")
    snapshot = context.member_snapshot
    if snapshot.total_members != 1 or len(snapshot.selected) != 1 or snapshot.view_limitations:
        gaps.add("member_coverage_incomplete")
    coverage = {"window": {key: params[key] for key in ("start", "end")} if params else None,
                "limit": params["limit"] if params else None, "gaps": sorted(gaps),
                "selected_members": len(snapshot.selected), "queried_members": 1 if params else 0,
                "total_members": snapshot.total_members}
    query_ref = "query:" + str(artifact_ref.artifact_id)
    query = {"ref": query_ref, "status": status, "executed": executed, "execution_state": execution,
             "returned_count": len(rows) if status in {"ok", "empty"} else None,
             "truncated": payload.get("truncated", False), "coverage": coverage,
             "source_run_id": material["source_run_id"], "provenance_kind": material["provenance_kind"]}
    index[query_ref] = {"kind": "query_receipt", "provenance": material, "source_path": "$.query_receipt",
                        "declared_executed": declared_executed,
                        "query_id": receipt.get("query_id") if receipt else None,
                        "receipt_sha256": content_hash(canonical_json(receipt)) if receipt else None,
                        "parameters": params, "source_coverage": receipt.get("coverage") if receipt else None,
                        "caller_receipt_sha256": content_hash(canonical_json(caller))}

    def block(reason: str, stage: str, *, observed_bytes: int | None = None, limit: int | None = None) -> None:
        # Called only after required material/provenance/version checks above.
        # Never echo a free-text input-contract diagnostic into this handoff.
        checked_index = json.loads(canonical_json(index))
        # The original query receipt remains hash-addressed in retained material;
        # its free-text coverage description is unnecessary in the block record.
        checked_index[query_ref].pop("source_coverage", None)
        raise EvidenceProjectionBlocked(reason, {
            "schema": "evidence_projection_block.v1", "scope_hash": scope_fingerprint(context),
            "revision": revision, "material": material, "held_refs": sorted(index), "index": checked_index,
            "query": query, "affected_questions": ["Q1", "Q2", "Q5"],
            "failure": {"code": reason, "stage": stage, "observed_bytes": observed_bytes, "limit": limit}})

    if alert_bytes > MAX_EXCERPT_BYTES:
        block("data_only_excerpt_exceeds_byte_limit", "alert_excerpt", observed_bytes=alert_bytes,
              limit=MAX_EXCERPT_BYTES)
    try:
        _excerpt(member.data_only_text)
    except LLMContractViolation:
        block("alert_input_contract_rejected", "alert_excerpt")
    model_view = {"questions": ["Q1", "Q2", "Q5"], "events": sorted(events.values(), key=lambda item: item["ref"]),
                  "alert": alert, "query": query}
    document = {"schema": "network_evidence_view.v1", "scope_hash": scope_fingerprint(context),
                "revision": revision, "material": material, "model_view": model_view, "index": index}
    model_view["snapshot_ref"] = "ev:" + content_hash(canonical_json(document))
    model_body = canonical_json(model_view)
    model_bytes = len(model_body.encode("utf-8"))
    if model_bytes >= MAX_MODEL_BYTES:
        block("complete_model_view_exceeds_byte_limit", "complete_model_view", observed_bytes=model_bytes,
              limit=MAX_MODEL_BYTES)
    try:
        LLMInputContract.validate([{"role": "user", "content": model_body}])
    except LLMContractViolation:
        block("model_view_input_contract_rejected", "complete_model_view")
    return EvidenceView(canonical_json(document))
