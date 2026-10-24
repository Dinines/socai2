"""Bounded, explicit dual-version result protocol; ownership stays with Agents.

This module deliberately has no Agents imports. Hashes check transmission and
version consistency, not the truth of source records or Markdown semantics.
"""
from __future__ import annotations

from datetime import datetime
import json
import os
import re
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from fastapi import HTTPException

from .result_gateway import MAX_BYTES, _canonical, _sha, _require, _uuid

URL_ENV = "AISOC_INVESTIGATION_COMPAT_READ_URL"
TOKEN_ENV = "AISOC_INVESTIGATION_COMPAT_READ_TOKEN"
OBJECTIVE = "verify_source_network_observation"
PROGRAM_VERSIONS = {
    "execution_schema": "investigation_execution.v1",
    "runtime_version": "program_alert_recon_runtime.v1",
    "state_schema": "program_recon_runtime_state.v1",
    "plan_schema": "program_recon_plan.v1",
    "material_schema": "network_program_material.v1",
    "material_policy_ref": "network_program_material_policy.v1",
    "fact_policy_ref": "finite_network_program_fields.v1",
    "completion_policy_ref": "bounded_full_window_program_fields.v1",
    "preparation_schema": "program_alert_recon_preparation.v1",
    "result_schema": "program_alert_recon.v1",
    "handoff_schema": "program_recon_runtime_handoff.v1",
    "unadopted_result_schema": "program_runtime_unadopted_result.v1",
}
_FAMILIES = {
    "owned_fixed_recon_result.v1": dict(
        runtime="fixed_alert_recon_runtime.v1", plan="fixed-recon-plan:",
        manifest="fixed_recon_result_manifest.v1", manifest_ref="recon-manifest:",
        execution="fixed_recon_publication_execution.v1", mapping="fixed_recon_publication_state.v1",
        renderer="fixed_recon_markdown.v1", sections="fixed_recon_handoff_sections.v1",
        handoff="fixed_recon_runtime_handoff.v1", handoff_ref="fixed-runtime-handoff:",
        completion="bounded_full_window_source_check.v1", program=False),
    "owned_program_recon_result.v1": dict(
        runtime="program_alert_recon_runtime.v1", plan="program-recon-plan:",
        manifest="program_recon_result_manifest.v1", manifest_ref="program-recon-manifest:",
        execution="program_recon_publication_execution.v1", mapping="program_recon_publication_state.v1",
        renderer="program_recon_markdown.v1", sections="program_recon_handoff_sections.v1",
        handoff="program_recon_runtime_handoff.v1", handoff_ref="program-runtime-handoff:",
        completion="bounded_full_window_program_fields.v1", program=True),
}
# prefix -> (result schema, preparation state, published evidence path)
_RESULTS = {
    False: {"fixed-recon:": ("fixed_alert_recon.v1", "view_ready", "/preparation/evidence_document"),
            "blocked-recon:": ("blocked_alert_recon.v1", "material_projection_blocked", None),
            "unadopted-recon:": ("fixed_runtime_unadopted_result.v1", "not_adopted", None)},
    True: {"program-recon:": ("program_alert_recon.v1", "program_material_validated", "/preparation/program_material_document"),
           "program-runtime-unadopted:": ("program_runtime_unadopted_result.v1", "not_adopted", None)},
}


def _keys(value, names):
    _require(type(value) is dict and set(value) == set(names.split()))


def _same(left, right):
    _require(_canonical(left) == _canonical(right))


def _int(value, minimum=0):
    _require(type(value) is int and value >= minimum)


def _text(value):
    _require(type(value) is str and bool(value))


def _hash(value):
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None)


def _ref(value, prefix):
    _require(type(value) is str and value.startswith(prefix))
    _hash(value[len(prefix):])


def _self_ref(value, key, prefix):
    _ref(value[key], prefix)
    _require(value[key] == prefix + _sha(_canonical({k: v for k, v in value.items() if k != key})))


def _artifact(value, extra="", expected=None):
    _keys(value, "artifact_id sha256 " + extra)
    _require(type(value["artifact_id"]) is str)
    _uuid(value["artifact_id"])
    _hash(value["sha256"])
    if expected is not None:
        _require(value["sha256"] == expected)


def _urn(value):
    _require(type(value) is str and value.startswith("urn:uuid:"))
    _uuid(value[9:])


def _strings(value):
    _require(type(value) is list and all(type(v) is str for v in value))
    _require(len(value) == len(set(value)))


def _target(value, owned=False):
    _keys(value, "type id" + (" record_ref ownership_check_ref" if owned else ""))
    _require(value["type"] == "alert" and type(value["id"]) is str)
    _uuid(value["id"])
    if owned:
        _text(value["record_ref"]); _text(value["ownership_check_ref"])


def _versions(value, family):
    if family["program"]:
        _same(value["policy_versions"], PROGRAM_VERSIONS)


def _timestamp(value):
    _text(value)
    result = datetime.fromisoformat(value)
    _require(result.tzinfo is not None and result.utcoffset() is not None)
    return result


def _window(value):
    _keys(value, "start end")
    start, end = _timestamp(value["start"]), _timestamp(value["end"])
    _require(0 < (end - start).total_seconds() <= 300)
    return start, end


def _coverage(value):
    _keys(value, "basis target_window query_window covered_window uncovered_windows full_window_queried")
    _require(value["basis"] == "confirmed_bounded_source_query_only" and type(value["full_window_queried"]) is bool)
    start, end = _window(value["target_window"])
    for key in ("query_window", "covered_window"):
        if value[key] is not None:
            a, b = _window(value[key]); _require(start <= a < b <= end)
    if value["covered_window"] is not None:
        _same(value["covered_window"], value["query_window"])
    _require(type(value["uncovered_windows"]) is list)
    for window in value["uncovered_windows"]:
        a, b = _window(window); _require(start <= a < b <= end)
    full = value["covered_window"] is not None and _canonical(value["covered_window"]) == _canonical(value["target_window"])
    _require(value["full_window_queried"] is full)
    if full:
        _same(value["uncovered_windows"], [])


def _usage(stage, total):
    common = "cost_complete known_cost_microusd known_tokens model_calls tokens_complete tool_calls total_cost_microusd total_tokens "
    _keys(stage, common + "reserved_cost_microusd reserved_tokens unknown_attempts unpriced_attempts unsettled_attempts")
    _keys(total, common + "unknown_calls unpriced_calls unsettled_attempts")
    for body in (stage, total):
        for key, value in body.items():
            if key.endswith("_complete"):
                _require(type(value) is bool)
            elif key.startswith("total_"):
                if value is not None: _int(value)
            else:
                _int(value)
        for flag, aggregate, known in (("tokens_complete", "total_tokens", "known_tokens"),
                                       ("cost_complete", "total_cost_microusd", "known_cost_microusd")):
            _same(body[aggregate], body[known] if body[flag] else None)
    for key in ("model_calls", "tool_calls", "known_tokens", "known_cost_microusd", "unsettled_attempts"):
        _require(total[key] >= stage[key])
    _require(total["unknown_calls"] >= stage["unknown_attempts"] and total["unpriced_calls"] >= stage["unpriced_attempts"])


def _result_kind(reference, family):
    _text(reference)
    for prefix, values in _RESULTS[family["program"]].items():
        if reference.startswith(prefix):
            _ref(reference, prefix)
            return prefix, values
    raise ValueError("unknown result version")


def _profile(profile, payload, candidate, family):
    _keys(profile, "schema profile_version profile trigger tenant_id run_id target objective policy_ref scope_hash scope_revision completion_basis delivery_target member_coverage binding_ref")
    _require(profile["schema"] == profile["profile_version"] == "investigation_profiles.v1")
    for key in ("tenant_id", "run_id", "profile", "objective"):
        _same(profile[key], payload[key])
    _require(profile["policy_ref"] == "network_observation.v1" and profile["completion_basis"] == "target_alert")
    _require(profile["trigger"] in ({"manual"} if family["program"] else {"manual", "automatic"}))
    _target(profile["target"], True)
    _same({k: profile["target"][k] for k in ("id", "type")}, payload["target"])
    _same(profile["delivery_target"], payload["target"])
    _same(profile["scope_hash"], candidate["scope_hash"]); _int(profile["scope_revision"], 1)
    _self_ref(profile, "binding_ref", "profile:")
    coverage = profile["member_coverage"]
    _keys(coverage, "all_member_ids selected_member_ids omitted_members membership_revision source_ref selection_covers_target evidence_coverage investigated_members view_limitations")
    for key in ("all_member_ids", "selected_member_ids"):
        _same(coverage[key], [payload["target"]["id"]])
    _same(coverage["omitted_members"], []); _same(coverage["view_limitations"], [])
    _require(coverage["membership_revision"] is None and coverage["selection_covers_target"] is True
             and coverage["evidence_coverage"] == "not_started")
    _same(coverage["investigated_members"], 0); _text(coverage["source_ref"])


def _candidate_result(result, payload, candidate, family):
    prefix, (schema, availability, path) = _result_kind(result["result_ref"], family)
    base = "authorization binding_ref blocking_gaps completion_basis completion_policy_ref coverage coverage_gaps delivery_target execution_stop facts handoff held_refs nature profile questions result_ref revision run_id schema scope_readiness snapshot_ref status stop_reason tenant_id"
    extra = ""
    if family["program"]:
        extra = " execution_state fact_policy_ref free_text_semantics material_policy_ref material_schema model_projection program_material_state source_available source_state"
    if availability == "not_adopted":
        extra += " validated_source_refs" + (" material_adoption_reason" if family["program"] else " source_state")
    elif availability == "material_projection_blocked":
        extra += " source_state source_available execution_state"
    _keys(result, base + extra)
    _require(result["schema"] == schema and result["completion_policy_ref"] == family["completion"])
    _self_ref(result, "result_ref", prefix)
    for key in ("tenant_id", "run_id", "profile"):
        _same(result[key], payload[key])
    _same(result["delivery_target"], payload["target"])
    _same(result["binding_ref"], candidate["business_profile"]["binding_ref"])
    _require(result["nature"] == "unresolved" and result["authorization"] == "unknown" and result["status"] == "stopped")
    _require(result["completion_basis"] == ("bounded_structured_source_fields_only" if family["program"] else "limited_source_observation_only"))
    _require(result["scope_readiness"] in {"ready", "partial"})
    _require(result["execution_stop"] is None or result["execution_stop"] in {"budget_limit", "deadline", "unknown_attempt", "retention_gap", "cancelled"})
    _text(result["stop_reason"]); _coverage(result["coverage"])
    for key in ("blocking_gaps", "coverage_gaps", "held_refs"): _strings(result[key])
    handoff = result["handoff"]
    _keys(handoff, "review_required automatic_query automatic_model case_action run_completion"
          + (" next_step" if availability in {"not_adopted", "material_projection_blocked"} else "")
          + (" delivery_status" if availability == "material_projection_blocked" else ""))
    _require(type(handoff["review_required"]) is bool and handoff["automatic_query"] is False
             and handoff["automatic_model"] is False and handoff["case_action"] == "not_requested"
             and handoff["run_completion"] == "not_published")
    _require(handoff["review_required"] is (result["scope_readiness"] != "ready"))
    if path is None:
        _require(result["scope_readiness"] == "partial" and result["facts"] == [] and result["snapshot_ref"] is None)
    if availability == "not_adopted":
        _require(result["revision"] is None); _same(result["validated_source_refs"], [])
        _require(result["source_state"] == ("not_confirmed" if family["program"] else "unverified"))
        if family["program"]:
            _text(result["material_adoption_reason"])
            _require(result["source_available"] is None and result["execution_state"] == "unknown")
    else:
        _int(result["revision"], 1); _same(result["revision"], candidate["business_profile"]["scope_revision"])
    if family["program"]:
        for key in ("fact_policy_ref", "material_schema", "material_policy_ref"): _same(result[key], PROGRAM_VERSIONS[key])
        _same(result["model_projection"], {"status": "not_requested", "eligible_for_model": False})
        _require(result["free_text_semantics"] == "not_assessed_by_program_material")
        _require(result["program_material_state"] == ("missing" if availability == "not_adopted" else availability))
    if "source_available" in result:
        _require(result["source_available"] is None or type(result["source_available"]) is bool)
        _text(result["source_state"]); _text(result["execution_state"])
    _facts_and_questions(result, family, availability)
    if result["scope_readiness"] == "ready":
        _require(result["execution_stop"] is None and not result["blocking_gaps"]
                 and result["coverage"]["full_window_queried"] is True
                 and all(q["status"] == "supported" for q in result["questions"] if q["decision_dependency"]))
    return availability, path


def _facts_and_questions(result, family, availability):
    facts, questions = result["facts"], result["questions"]
    _require(type(facts) is list and type(questions) is list and len(questions) == 6)
    ids = {}
    for fact in facts:
        _keys(fact, "assurance binding_ref dependency_refs evidence_refs fact id origin question revision snapshot_ref validity"
              + (" fact_policy_ref material_schema" if family["program"] else ""))
        _require(fact["origin"] == "program" and fact["assurance"] == "rule_checked" and fact["validity"] == "current")
        _require(fact["question"] in {"Q1", "Q2", "Q5"})
        data = fact["fact"]
        _require(type(data) is dict)
        predicate = data["predicate"]
        if predicate in {"network_observed", "outcome_unknown"}:
            _keys(data, "predicate conflict fields source_identity source_version")
            _require(fact["question"] == "Q1" and type(data["conflict"]) is bool)
            _network_fields(data["fields"]); _text(data["source_identity"]); _hash(data["source_version"])
        elif predicate == "source_versions_conflict":
            _keys(data, "predicate source_identity visible_versions missing_version_hashes")
            _require(fact["question"] == "Q1"); _text(data["source_identity"])
            for key in ("visible_versions", "missing_version_hashes"):
                _strings(data[key])
                for value in data[key]: _hash(value)
        elif predicate == "alert_linked":
            _keys(data, "predicate association event_id")
            _require(fact["question"] == "Q2" and data["association"] == "exact_declared_source_id_only"); _uuid(data["event_id"])
        else:
            _keys(data, "predicate coverage executed execution_state returned_count status truncated")
            _require(predicate in {"bounded_query", "query_empty", "source_unavailable"} and fact["question"] == "Q5"
                     and (data["executed"] is None or type(data["executed"]) is bool)
                     and type(data["truncated"]) is bool and data["status"] in {"ok", "empty", "unavailable", "error", "rejected"})
            if data["returned_count"] is None:
                _require(predicate == "source_unavailable" and data["status"] not in {"ok", "empty"})
            else:
                _int(data["returned_count"])
            _query_coverage(data["coverage"]); _text(data["execution_state"])
        for key in ("binding_ref", "snapshot_ref", "revision"): _same(fact[key], result[key])
        if family["program"]:
            for key in ("fact_policy_ref", "material_schema"): _same(fact[key], PROGRAM_VERSIONS[key])
        _strings(fact["evidence_refs"]); _require(set(fact["evidence_refs"]) <= set(result["held_refs"]))
        _same(fact["dependency_refs"], [result["snapshot_ref"], *fact["evidence_refs"]])
        body = {k: fact[k] for k in ("question", "fact", "evidence_refs", "snapshot_ref", "binding_ref")}
        if family["program"]:
            body.update({k: fact[k] for k in ("fact_policy_ref", "material_schema")})
        _require(fact["id"] == ("program-field-finding:" if family["program"] else "program-finding:") + _sha(_canonical(body)))
        _require(fact["id"] not in ids); ids[fact["id"]] = fact["question"]
    for question, expected in zip(questions, ("Q1", "Q2", "Q3a", "Q3b", "Q4", "Q5")):
        _keys(question, "capability_gaps critical decision_dependency finding_ids policy_reason question status"
              + (" material_gap" if availability == "material_projection_blocked" else ""))
        _require(question["question"] == expected and question["critical"] is (expected in {"Q1", "Q5"})
                 and question["decision_dependency"] is (expected in {"Q1", "Q5"}))
        _require(question["status"] in {"supported", "insufficient_evidence", "conflicting", "unassessed"})
        _strings(question["finding_ids"]); _strings(question["capability_gaps"])
        _require(type(question["policy_reason"]) is str)
        _require(set(question["finding_ids"]) == {key for key, value in ids.items() if value == expected})
        if expected in {"Q3a", "Q3b", "Q4"} or availability in {"not_adopted", "material_projection_blocked"}:
            _require(question["status"] == "unassessed" and question["finding_ids"] == [])


def _preparation(prep, result, candidate, family, availability, path):
    if availability == "not_adopted":
        _require(prep is None); return
    if family["program"]:
        _keys(prep, "schema completion_policy_ref fact_policy_ref material_policy_ref material material_state model_projection persistence_status preparation_ref program_material_document program_material_snapshot_ref result")
        _require(prep["schema"] == PROGRAM_VERSIONS["preparation_schema"])
        prefix, doc_key, snap_key = "program-recon-preparation:", "program_material_document", "program_material_snapshot_ref"
        for key in ("fact_policy_ref", "material_policy_ref"): _same(prep[key], PROGRAM_VERSIONS[key])
        _same(prep["model_projection"], result["model_projection"])
    else:
        _keys(prep, "schema completion_policy_ref evidence_document evidence_snapshot_ref material material_state persistence_status preparation_ref projection_block result")
        _require(prep["schema"] == "alert_recon_preparation.v1")
        prefix, doc_key, snap_key = "recon-preparation:", "evidence_document", "evidence_snapshot_ref"
        if path is None:
            _require(type(prep["projection_block"]) is dict and prep["projection_block"]["schema"] == "evidence_projection_block.v1")
        else:
            _require(prep["projection_block"] is None)
    _require(prep["material_state"] == availability and prep["persistence_status"] == "not_attempted"
             and prep["completion_policy_ref"] == family["completion"])
    _self_ref(prep, "preparation_ref", prefix); _same(prep["result"], result)
    material = prep["material"]
    _keys(material, "artifact_id artifact_ref sha256 stored_sha256 source_run_id tenant_id retention provenance_kind derived_from")
    _uuid(material["artifact_id"]); _hash(material["sha256"])
    _require(material["artifact_ref"] == "urn:uuid:" + material["artifact_id"]
             and material["stored_sha256"] == material["sha256"]
             and material["source_run_id"] == result["run_id"] and material["tenant_id"] == result["tenant_id"]
             and material["retention"] == "committed" and material["provenance_kind"] == "retained_tool_output"
             and material["derived_from"] is None and material["artifact_ref"] in candidate["retained_artifact_refs"])
    _same(prep[snap_key], result["snapshot_ref"])
    doc = prep[doc_key]
    if path is None:
        _require(doc is None); return
    if family["program"]:
        _keys(doc, "schema material_policy_ref scope_hash revision material scope_sources records alert query index model_projection free_text_semantics snapshot_ref")
        _require(doc["schema"] == PROGRAM_VERSIONS["material_schema"] and doc["material_policy_ref"] == PROGRAM_VERSIONS["material_policy_ref"])
        _self_ref(doc, "snapshot_ref", "program-material:"); _same(doc["snapshot_ref"], result["snapshot_ref"])
        _same(doc["model_projection"], result["model_projection"]); _same(doc["free_text_semantics"], result["free_text_semantics"])
    else:
        _keys(doc, "schema scope_hash revision material model_view index")
        _require(doc["schema"] == "network_evidence_view.v1")
        _keys(doc["model_view"], "alert events query questions snapshot_ref")
        _same(doc["model_view"]["snapshot_ref"], result["snapshot_ref"])
        body = {**doc, "model_view": {k: v for k, v in doc["model_view"].items() if k != "snapshot_ref"}}
        _require(result["snapshot_ref"] == "ev:" + _sha(_canonical(body)))
    _same(doc["scope_hash"], candidate["scope_hash"]); _same(doc["revision"], result["revision"])
    _same(doc["material"], prep["material"])
    _material_view(doc, result, family)


def _source_ref(value):
    _keys(value, "ref sha256 size_bytes")
    _hash(value["sha256"]); _int(value["size_bytes"])
    _require(value["ref"] == "scope-source:" + value["sha256"])


def _query_coverage(value):
    _keys(value, "gaps limit queried_members selected_members total_members window")
    _strings(value["gaps"])
    if value["limit"] is None: _require(value["window"] is None)
    else: _int(value["limit"], 1)
    for key in ("queried_members", "selected_members"): _int(value[key])
    if value["total_members"] is not None:
        _int(value["total_members"]); _require(value["selected_members"] <= value["total_members"])
    _require(value["queried_members"] <= value["selected_members"])
    if value["window"] is not None: _window(value["window"])


def _network_fields(value):
    _keys(value, "action dest_ip dst_port hostname observed_at outcome protocol source_ip")
    for key in value:
        if key == "dst_port": _int(value[key]); _require(value[key] <= 65535)
        else: _require(type(value[key]) is str)
    _timestamp(value["observed_at"])


def _material_view(doc, result, family):
    # Typed public projections and their ref/index relationships only. Raw
    # source ownership, extraction and predicate truth remain owned-backend work.
    visible = doc if family["program"] else doc["model_view"]
    records = visible["records" if family["program"] else "events"]
    _require(type(records) is list and type(doc["index"]) is dict)
    query, alert = visible["query"], visible["alert"]
    _keys(query, "ref status executed execution_state returned_count truncated coverage source_run_id provenance_kind")
    _require(query["status"] in {"ok", "empty", "unavailable", "error", "rejected"}
             and (query["executed"] is None or type(query["executed"]) is bool)
             and type(query["truncated"]) is bool)
    if query["returned_count"] is None:
        _require(query["status"] not in {"ok", "empty"} and not records)
    else:
        _int(query["returned_count"]); _require(query["returned_count"] >= len(records))
    if query["status"] in {"ok", "empty"}: _require(query["executed"] is True)
    _query_coverage(query["coverage"]); _text(query["execution_state"])
    _require(query["source_run_id"] == result["run_id"] and query["provenance_kind"] == "retained_tool_output"
             and query["ref"] == "query:" + doc["material"]["artifact_id"])
    _keys(alert, "ref source_event_ids " + ("identity data_only_source free_text_semantics" if family["program"] else "data_only_text"))
    _ref(alert["ref"], "alert:"); _strings(alert["source_event_ids"])
    for value in alert["source_event_ids"]: _uuid(value)
    if family["program"]:
        _require(type(doc["scope_sources"]) is list)
        for value in doc["scope_sources"]: _source_ref(value)
        _source_ref(alert["data_only_source"])
        _require(alert["data_only_source"] in doc["scope_sources"] and alert["identity"] == result["delivery_target"]["id"]
                 and alert["free_text_semantics"] == "not_assessed_by_program_material")
    else:
        _require(type(alert["data_only_text"]) is str); _same(visible["questions"], ["Q1", "Q2", "Q5"])
    expected_refs = {alert["ref"], query["ref"]}
    for record in records:
        _keys(record, "ref identity version fields conflict missing_version_hashes"
              + (" data_only_excerpt" if "data_only_excerpt" in record else ""))
        _text(record["identity"]); _hash(record["version"]); _network_fields(record["fields"])
        _require(type(record["conflict"]) is bool)
        _strings(record["missing_version_hashes"])
        for value in record["missing_version_hashes"]: _hash(value)
        if "data_only_excerpt" in record: _require(type(record["data_only_excerpt"]) is str)
        _require(record["ref"] == "source:" + _sha(_canonical([record["identity"], record["version"]]))
                 and record["ref"] not in expected_refs)
        expected_refs.add(record["ref"])
        index = doc["index"][record["ref"]]
        digest_key = "program_record_sha256" if family["program"] else "model_visible_sha256"
        _keys(index, "kind identity version field_paths excerpt_path projection_hash conflict_version_hashes provenance retrievals " + digest_key)
        _require(index["kind"] == "source_event" and index[digest_key] == _sha(_canonical(record)))
        for key in ("identity", "version"): _same(index[key], record[key])
        _hash(index["projection_hash"]); _strings(index["conflict_version_hashes"])
        for value in index["conflict_version_hashes"]: _hash(value)
        _same(index["provenance"], doc["material"])
        _require(type(index["field_paths"]) is dict and all(type(v) is str for v in index["field_paths"].values()))
        _require(index["excerpt_path"] is None or type(index["excerpt_path"]) is str)
        _require(type(index["retrievals"]) is list)
        for retrieval in index["retrievals"]:
            _keys(retrieval, "source_path duplicate_count bodies message_extraction")
            _text(retrieval["source_path"]); _text(retrieval["message_extraction"]); _int(retrieval["duplicate_count"], 1)
            _keys(retrieval["bodies"], "raw_payload ocsf_json")
            for body in retrieval["bodies"].values():
                _keys(body, "full_sha256 original_bytes retained_sha256 retained_bytes truncated")
                _hash(body["full_sha256"]); _hash(body["retained_sha256"])
                _int(body["original_bytes"]); _int(body["retained_bytes"])
                _require(type(body["truncated"]) is bool and body["retained_bytes"] <= body["original_bytes"])
    _require(set(doc["index"]) == expected_refs)
    q_index = doc["index"][query["ref"]]
    _keys(q_index, "kind source_path receipt_sha256 parameters source_coverage declared_executed query_id caller_receipt_sha256 provenance")
    _require(q_index["kind"] == "query_receipt"); _same(q_index["provenance"], doc["material"])
    _require(q_index["declared_executed"] is None or type(q_index["declared_executed"]) is bool)
    if query["executed"] is not None: _same(q_index["declared_executed"], query["executed"])
    for key in ("receipt_sha256", "caller_receipt_sha256"):
        if q_index[key] is not None: _hash(q_index[key])
    if q_index["query_id"] is not None: _uuid(q_index["query_id"])
    if q_index["parameters"] is not None:
        params = q_index["parameters"]
        _keys(params, "tenant_id start end limit source_ip dest_ip dst_port hostname protocol")
        _int(params["limit"], 1); _int(params["dst_port"]); _window({k: params[k] for k in ("start", "end")})
        _require(params["tenant_id"] == result["tenant_id"])
    a_index = doc["index"][alert["ref"]]
    _keys(a_index, "kind identity record_ref ownership_check_ref field_paths "
          + ("data_only_source free_text_semantics" if family["program"] else "data_only_sha256 data_only_bytes"))
    _require(a_index["kind"] == "alert_claim" and a_index["identity"] == result["delivery_target"]["id"])
    _text(a_index["record_ref"]); _text(a_index["ownership_check_ref"])
    _require(type(a_index["field_paths"]) is dict)
    for value in a_index["field_paths"].values():
        _keys(value, "path record_ref"); _text(value["path"]); _same(value["record_ref"], a_index["record_ref"])
    if family["program"]:
        _same(a_index["data_only_source"], alert["data_only_source"]); _same(a_index["free_text_semantics"], alert["free_text_semantics"])
    else:
        _int(a_index["data_only_bytes"]); _require(a_index["data_only_bytes"] == len(alert["data_only_text"].encode("utf-8")))
        _require(a_index["data_only_sha256"] == _sha(alert["data_only_text"].encode("utf-8")))


def _candidate(candidate, payload, family):
    _keys(candidate, "schema business_profile completion_policy_ref execution handoff_ref preparation result retained_artifact_refs runtime_plan_ref runtime_version scope_hash unconfirmed_observation_ref"
          + (" policy_versions" if family["program"] else ""))
    _require(candidate["schema"] == family["handoff"] and candidate["runtime_version"] == family["runtime"]
             and candidate["completion_policy_ref"] == family["completion"])
    _versions(candidate, family); _self_ref(candidate, "handoff_ref", family["handoff_ref"])
    _ref(candidate["runtime_plan_ref"], family["plan"]); _hash(candidate["scope_hash"])
    _strings(candidate["retained_artifact_refs"])
    for value in candidate["retained_artifact_refs"]: _urn(value)
    _observer(candidate["unconfirmed_observation_ref"], family)
    _keys(candidate["execution"], "source_state_artifact_ref stage_usage run_total cancellation_observed_at")
    execution = candidate["execution"]
    _urn(execution["source_state_artifact_ref"])
    _require(execution["source_state_artifact_ref"] in candidate["retained_artifact_refs"])
    _usage(execution["stage_usage"], execution["run_total"])
    if execution["cancellation_observed_at"] is not None: _timestamp(execution["cancellation_observed_at"])
    _profile(candidate["business_profile"], payload, candidate, family)
    availability, path = _candidate_result(candidate["result"], payload, candidate, family)
    _preparation(candidate["preparation"], candidate["result"], candidate, family, availability, path)


def _observer(value, family):
    if value is not None:
        _artifact(value, "kind")
        _require(value["kind"] == ("program_recon_unconfirmed_observation" if family["program"] else "fixed_recon_unconfirmed_observation"))


def _published(payload, family):
    manifest, execution = payload["manifest"], payload["execution_snapshot"]
    _keys(manifest, "schema publication_state tenant_id run_id investigation_id profile objective target version previous_manifest_ref manifest_ref renderer_version mapping_version sections_version runtime_version runtime_plan_ref scope_hash scope_revision completion_policy_ref coverage handoff_ref result_ref retention snapshots source_state_ref stopped_state_ref"
          " report" + (" policy_versions" if family["program"] else ""))
    _keys(execution, "schema tenant_id run_id mapping_version runtime_version runtime_plan_ref scope_hash source_state_ref stopped_state_ref scope_readiness run_state investigation_completeness continuation human_acknowledged stage_usage run_total stop_reason"
          + (" policy_versions" if family["program"] else ""))
    _versions(manifest, family); _versions(execution, family)
    for key in ("tenant_id", "run_id", "profile", "objective"): _same(manifest[key], payload[key])
    for key in ("tenant_id", "run_id", "runtime_version", "runtime_plan_ref", "scope_hash", "source_state_ref", "stopped_state_ref", "mapping_version"):
        _same(execution[key], manifest[key])
    _target(manifest["target"], True)
    _same({k: manifest["target"][k] for k in ("type", "id")}, payload["target"])
    _require(manifest["schema"] == family["manifest"] and manifest["publication_state"] == "published"
             and execution["schema"] == family["execution"] and manifest["investigation_id"] == payload["run_id"]
             and manifest["previous_manifest_ref"] is None)
    _same(manifest["version"], 1); _int(manifest["scope_revision"], 1)
    for key in ("runtime", "renderer", "mapping", "sections"):
        _require(manifest[key + "_version"] == family[key])
    _require(manifest["completion_policy_ref"] == family["completion"])
    _ref(manifest["runtime_plan_ref"], family["plan"]); _hash(manifest["scope_hash"])
    _self_ref(manifest, "manifest_ref", family["manifest_ref"])
    _artifact(payload["manifest_artifact"], expected=_sha(_canonical(manifest)))
    for key in ("source_state_ref", "stopped_state_ref", "handoff_ref"): _artifact(manifest[key])
    _require(manifest["source_state_ref"]["artifact_id"] != manifest["stopped_state_ref"]["artifact_id"])
    _coverage(manifest["coverage"]); _usage(execution["stage_usage"], execution["run_total"])
    _require(execution["human_acknowledged"] is False); _text(execution["stop_reason"])
    ready = execution["scope_readiness"] == "ready"
    _require(execution["scope_readiness"] in {"ready", "partial"})
    _require((execution["run_state"], execution["investigation_completeness"], execution["continuation"])
             in ({("finished", "complete_for_scope", "none")} if ready else {("stopped", "partial", "awaiting_human"), ("cancelled", "partial", "awaiting_human")}))
    retention = manifest["retention"]
    _keys(retention, "publication_artifacts source_availability source_gaps blocking_gaps held_refs unknown_calls unpriced_attempts unsettled_attempts unconfirmed_observation_ref")
    _require(retention["publication_artifacts"] == "committed")
    for key in ("source_gaps", "blocking_gaps", "held_refs"): _strings(retention[key])
    for key, body, other in (("unknown_calls", execution["run_total"], "unknown_calls"),
                             ("unpriced_attempts", execution["stage_usage"], "unpriced_attempts"),
                             ("unsettled_attempts", execution["stage_usage"], "unsettled_attempts")):
        _int(retention[key]); _same(retention[key], body[other])
    _observer(retention["unconfirmed_observation_ref"], family)
    _, (_, availability, path) = _result_kind(manifest["result_ref"], family)
    _require(retention["source_availability"] == availability)
    if path is None: _require(not ready)
    if ready: _require(manifest["coverage"]["full_window_queried"] is True and not retention["blocking_gaps"])
    snapshots = manifest["snapshots"]
    _keys(snapshots, "questions analysis evidence execution")
    for key, section in (("questions", "/result/questions"), ("analysis", "/result"), ("evidence", path)):
        value = snapshots[key]
        if section is None:
            _require(value is None); continue
        _artifact(value, "artifact_schema sections_version section section_sha256")
        _same({k: value[k] for k in ("artifact_id", "sha256")}, manifest["handoff_ref"])
        _require(value["artifact_schema"] == family["handoff"] and value["sections_version"] == family["sections"] and value["section"] == section)
        _hash(value["section_sha256"])
    _artifact(snapshots["execution"], "artifact_schema", _sha(_canonical(execution)))
    _require(snapshots["execution"]["artifact_schema"] == family["execution"])
    markdown = payload["markdown"]
    _require(type(markdown) is str and len(markdown.encode("utf-8")) <= MAX_BYTES)
    _artifact(manifest["report"], "renderer_version media_type", _sha(markdown.encode("utf-8")))
    _require(manifest["report"]["renderer_version"] == family["renderer"] and manifest["report"]["media_type"] == "text/markdown")


def checked_compatible_result(payload, *, tenant_id: UUID, run_id: UUID) -> dict:
    _require(type(payload) is dict)
    _canonical(payload)  # Bound the whole DTO and reject non-JSON/NaN values.
    _require(type(payload.get("schema")) is str and payload["schema"] in _FAMILIES)
    family = _FAMILIES[payload["schema"]]
    common = "publication_state manifest_artifact manifest markdown retention notification schema tenant_id run_id profile target objective legacy_run_status"
    publication = payload["publication_state"]
    _require(type(publication) is str and publication in {"published", "not_published"})
    _keys(payload, common + (" execution_snapshot" if publication == "published" else " candidate progress delivery_gap"))
    _require(payload["tenant_id"] == str(_uuid(tenant_id)) and payload["run_id"] == str(_uuid(run_id))
             and payload["profile"] == "alert_recon" and payload["objective"] == OBJECTIVE)
    _target(payload["target"]); _text(payload["legacy_run_status"])
    _require(payload["notification"] is None)
    if publication == "published":
        _require(payload["retention"] == "committed"); _published(payload, family)
    else:
        _require(payload["retention"] == "progress_only" and payload["delivery_gap"] == "result_not_published"
                 and payload["manifest"] is None and payload["manifest_artifact"] is None and payload["markdown"] is None)
        progress = payload["progress"]
        _keys(progress, "phase stage_usage run_total")
        _require(progress["phase"] in {"ready", "claimed", "blocked", "stopped"})
        _usage(progress["stage_usage"], progress["run_total"])
        _require((payload["candidate"] is not None) is (progress["phase"] == "stopped"))
        if payload["candidate"] is not None:
            # Historical handoff usage can precede a genuine late settlement.
            # Progress remains current; neither is a published same-version DTO.
            _candidate(payload["candidate"], payload, family)
    return payload


class CompatibleResultReadGateway:
    def __init__(self, *, backend_url: str, read_token: str, transport=None):
        try:
            parsed = urlsplit(backend_url)
            valid_url = (parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username
                         and not parsed.password and not parsed.query and not parsed.fragment
                         and parsed.path in {"", "/"} and not any(c.isspace() for c in backend_url))
            parsed.port
        except (ValueError, TypeError, AttributeError):
            valid_url = False
        if not valid_url:
            raise ValueError("explicit compatible read backend required") from None
        try:
            valid_token = (type(read_token) is str and 32 <= len(read_token.encode("ascii")) <= 256
                           and not any(c.isspace() for c in read_token))
        except UnicodeEncodeError:
            valid_token = False
        if not valid_token:
            raise ValueError("explicit compatible read token required") from None
        self._url, self._token, self._transport = backend_url.rstrip("/"), read_token, transport

    @classmethod
    def from_environment(cls):
        return cls(backend_url=os.getenv(URL_ENV) or "", read_token=os.getenv(TOKEN_ENV) or "")

    async def read(self, *, tenant_id: UUID, actor_id: UUID, run_id: UUID) -> dict:
        try:
            tenant, actor, run = _uuid(tenant_id), _uuid(actor_id), _uuid(run_id)
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(502, "investigation_compat_current_identity_invalid") from None
        headers = {"Authorization": "Bearer " + self._token, "X-AiSOC-Tenant-ID": str(tenant), "X-AiSOC-Actor-ID": str(actor)}
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=False, transport=self._transport) as client:
                async with client.stream("GET", self._url + "/internal/investigation-v2/runs/" + str(run), headers=headers) as response:
                    status = response.status_code
                    if status == 404: raise HTTPException(404, "investigation_compat_result_not_found")
                    if status == 409: raise HTTPException(409, "investigation_compat_result_integrity_or_version_unavailable")
                    if status in {500, 502, 503, 504}: raise HTTPException(503, "investigation_compat_result_backend_unavailable")
                    if status != 200: raise HTTPException(502, "investigation_compat_result_backend_response_invalid")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(body) + len(chunk) > MAX_BYTES:
                            raise ValueError("bounded backend result required")
                        body.extend(chunk)
            return checked_compatible_result(json.loads(body), tenant_id=tenant, run_id=run)
        except httpx.HTTPError:
            raise HTTPException(503, "investigation_compat_result_backend_unavailable") from None
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError):
            raise HTTPException(502, "investigation_compat_result_backend_response_invalid") from None
