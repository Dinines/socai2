"""D1 independent replay: current builders/policy, frozen r3 data, no I/O services.

This tests new request construction, not old wire scans or model output quality.
Optional SOCAI2_D1_EVIDENCE_DIR stores the newly constructed request and checks.
"""

import copy
import hashlib
import json
import os
import socket
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.socai2 import (
    alert_model_boundary,
    alert_output_adapter,
    case_followup_input,
    case_followup_output,
    case_model_boundary,
    case_output_adapter,
    incident_model_boundary,
    incident_output_adapter,
    runtime_policy,
)
from app.socai2.baseline_context import Context
from app.socai2.baseline_store import digest
from app.socai2.model_protocol import prepare_request

ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "deploy/aisoc21/streaming-release-20261116-02/analysis/investigation-policy.toml"
SNAPSHOT = ROOT / "docs/operations/evidence/streaming-fullflow-20261116-01/final-pg.json"
RUNS = {
    "A": "7e2f68f4-393f-5dde-ab74-36ac0f866e65",
    "I": "015358ab-c7f4-576e-b67d-9c57b7cfb07e",
    "Case": "f21248be-39eb-4832-8d87-866d7f62d40d",
}
STAGES = ["A", "I", "C3", "Deep", "C6"]
BUSINESS = {
    "source": "business-origin-kept",
    "id": "business-object-kept",
    "tenant_uid": "business-cloud-tenant-kept",
    "unknown_amount": 0,
    "unknown_authorized": False,
    "unknown_permissions": [],
    "unknown_detail": "test/source/id/tenant_uid 是业务原文，不应按词删除。",
}


@pytest.fixture
def selected_policy(monkeypatch):
    # Fail closed on accidental network use, including a tokenizer request.
    def forbidden(*_args, **_kwargs):
        raise AssertionError("D1 is offline; no socket connection is permitted")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(POLICY))
    runtime_policy.active_policy.cache_clear()
    policy = runtime_policy.active_policy()
    assert policy.model.output_tokens["A"] == 8192
    assert policy.model.output_tokens["C3"] == 16384
    yield policy
    runtime_policy.active_policy.cache_clear()


def probe(material, variant):
    """Mutate only a derived in-memory fixture; originals stay immutable."""
    if variant == "r3":
        return []
    markers = []
    for index, event in enumerate((material["ocsf_json"], material["raw_json"]["raw_event"]["ocsf_event"])):
        marker = f"backend-tenant-only-{index}"
        event["tenant_uid"] = marker
        markers.append(marker)
        event["business_extension"] = copy.deepcopy(BUSINESS)
    if variant == "structured":
        envelope = material["raw_json"]["raw_event"]
        envelope["telemetry"] = []
        for index in range(2):
            record = {key: f"backend-{key}-only-{index}" for key in ("source", "event_id", "tenant_id", "connector_id")}
            markers.extend(record.values())
            record["business_extension"] = copy.deepcopy(BUSINESS)
            envelope["telemetry"].append(record)
        # A wildcard for list indices must not scrub a separate business object.
        envelope["other"] = {"source": "other-source-kept", "tenant_id": "other-tenant-kept"}
        material["raw_text"] = BUSINESS["unknown_detail"]
    elif variant == "serialized":
        body = {"class_uid": 6003, "tenant_uid": "backend-serialized-tenant-only", "business_extension": copy.deepcopy(BUSINESS)}
        markers.append(body["tenant_uid"])
        raw = json.dumps(body, ensure_ascii=False)
        material["raw_text"] = raw
        material["ocsf_json"]["raw_data"] = raw
        material["raw_json"]["raw_event"]["ocsf_event"]["raw_data"] = raw
    return markers


def wire(policy, stage, messages, output):
    gateway = SimpleNamespace(provider=policy.model.protocol, schema_profile=policy.model.schema_profile)
    return prepare_request(gateway, {
        "model": policy.model.alias, "messages": messages,
        "max_tokens": policy.model.output_tokens[stage], "temperature": 0,
        "response_format": output,
    })


def build_packet(rows, policy, stage, variant):
    artifacts = {a["id"]: a for a in rows["artifacts"]}
    run = next(r for r in rows["runs"] if r["id"] == RUNS[stage if stage in {"A", "I"} else "Case"])
    if stage in {"A", "I"}:
        source = copy.deepcopy(artifacts[run["input_artifact_id"]]["content_json"])
        markers = []
        for member in source["members"]:
            markers.extend(probe(member["material"], variant))
        queries = [(a["id"], copy.deepcopy(a["content_json"])) for a in artifacts.values()
                   if a["run_id"] == run["id"] and a["kind"] == "tool_response"]
        frozen = digest([source, queries])
        if stage == "A":
            messages, mapping, _, prepared = alert_model_boundary.build(
                source, run["input_artifact_id"], queries, policy.alert_io, execution_time=run["started_at"])
            output = alert_output_adapter.schema(mapping)
        else:
            messages, mapping, _, prepared = incident_model_boundary.build(
                source, run["input_artifact_id"], policy.incident_io, execution_time=run["started_at"])
            output = {"type": "json_schema", "json_schema": {
                "name": "socai2_incident_boundary", "strict": True,
                "schema": incident_output_adapter.candidate_schema(prepared)}}
        original_unchanged = digest([source, queries]) == frozen
        members = {m["alert"]["id"] for m in source["members"]}
        material_ids = {m["material"]["id"] for m in source["members"]}
        alias_keys = set(prepared.get("member_aliases", {}))
    else:
        owned = [a for a in artifacts.values() if a["run_id"] == run["id"]]
        snapshot = next(a for a in owned if a["schema_version"] == "socai2.baseline-context.v1")
        raw_context = copy.deepcopy(snapshot["content_json"])
        # New offline construction uses the selected current profile, never
        # overwrites or reinterprets the historical C1 snapshot on disk.
        previous_profile = copy.deepcopy(raw_context["case_input_profile"])
        raw_context["case_input_profile"] = policy.case_io.identity
        materials, markers = {}, []
        for aid, member in raw_context["alerts"].items():
            material = copy.deepcopy(next(m for m in rows["alert_materials"] if m["id"] == member["material"]["id"]))
            assert material["alert_id"] == aid
            markers.extend(probe(material, variant))
            materials[aid] = material
        context = Context.model_validate(raw_context)
        enrichment = [(a["id"], copy.deepcopy(a["content_json"]), {}) for a in owned
                      if a["kind"] == "tool_response" and a["schema_version"] == "socai2.baseline-enrichment.v1"]
        frozen = digest([raw_context, materials, enrichment])
        base = case_model_boundary.build(context, snapshot["id"], enrichment, [], materials,
                                        execution_time=run["started_at"], run_id=run["id"])
        assert base["ready"], base["reason"]
        if stage == "C3":
            prepared = base
            messages, mapping = case_model_boundary.messages(base, context, [])
            output = case_output_adapter.output_format(base, context, {})
        else:
            previous = next(a for a in owned if isinstance(a.get("content_json"), dict)
                            and a["content_json"].get("analysis"))
            prior = copy.deepcopy(previous["content_json"])
            prior_hash = digest(prior)
            question_id = next(q.id for q in context.questions if q.id != "coverage")
            comparison = {"state": "initial", "result_id": None}
            prepared = case_followup_input.build(stage, context, base, {}, previous=prior,
                prior_id=previous["id"], question_id=question_id if stage == "Deep" else None,
                extra={"comparison": comparison} if stage == "C6" else None)
            assert prepared["ready"], prepared["reason"]
            assert digest(prior) == prior_hash
            messages, mapping = prepared["messages"], prepared["source_map"]
            output = (case_followup_output.deep_format(prepared) if stage == "Deep"
                      else case_followup_output.final_format(prepared, context, comparison))
        original_unchanged = digest([raw_context, materials, enrichment]) == frozen
        assert snapshot["content_json"]["case_input_profile"] == previous_profile
        members, material_ids = set(context.alerts), {m["id"] for m in materials.values()}
        alias_keys = set(prepared["case_boundary"]["member_aliases"])
    return {
        "wire": wire(policy, stage, messages, output), "source_map": mapping,
        "prepared": prepared, "markers": sorted(set(markers)),
        "members": sorted(members), "material_ids": sorted(material_ids),
        "alias_keys": sorted(alias_keys), "original_unchanged": original_unchanged,
        "fixture_sha256": frozen, "source_run_id": run["id"],
    }


def has_typed_leaf(value, name, expected):
    if isinstance(value, dict):
        field = value.get("field")
        if (isinstance(field, str) and field.endswith("." + name)
                and type(value.get("value")) is type(expected) and value["value"] == expected):
            return True
        return any((key == name or key.endswith("." + name)) and type(child) is type(expected) and child == expected
                   or has_typed_leaf(child, name, expected) for key, child in value.items())
    if isinstance(value, list):
        return any(has_typed_leaf(child, name, expected) for child in value)
    return False


@pytest.mark.parametrize("stage", STAGES)
@pytest.mark.parametrize("variant", ["r3", "structured", "serialized"])
def test_current_five_stage_wire_and_originals(selected_policy, stage, variant):
    original_bytes = SNAPSHOT.read_bytes()
    rows = json.loads(original_bytes)["rows"]
    before = digest(rows)
    backend = {m["id"]: {"tenant_id": m["tenant_id"], "alert_id": m["alert_id"],
                         "ocsf_tenant_uid": m["ocsf_json"].get("tenant_uid")}
               for m in rows["alert_materials"]}
    packet = build_packet(rows, selected_policy, stage, variant)
    sent = json.dumps(packet["wire"], ensure_ascii=False)
    refs = [item["ref"] for item in packet["source_map"].values()]
    prepared = packet["prepared"]
    if "selected_values" in prepared:
        selected = [{"field": packet["source_map"][sid]["ref"]["source_path"], "value": value}
                    for sid, value in prepared["selected_values"].items()]
    else:
        records = prepared.get("records") or (
            prepared.get("input_ledger") or prepared.get("followup_boundary") or {})["records"]
        selected = [{"field": row.get("field") or row.get("ref", {}).get("source_path"),
                     "value": row["value"]} for row in records]
    actual_backend = {m["id"]: {"tenant_id": m["tenant_id"], "alert_id": m["alert_id"],
                                "ocsf_tenant_uid": m["ocsf_json"].get("tenant_uid")}
                      for m in rows["alert_materials"]}
    checks = {
        "source_snapshot_bytes_unchanged": SNAPSHOT.read_bytes() == original_bytes,
        "loaded_historical_rows_unchanged": digest(rows) == before,
        "derived_inputs_unchanged_by_builders": packet["original_unchanged"],
        "original_backend_tenant_alert_and_ocsf_preserved": backend == actual_backend,
        "original_backend_ids_not_cleared": all(all(backend[mid].values()) for mid in packet["material_ids"]),
        "nonempty_wire_and_mapping": bool(packet["wire"]["messages"] and refs),
        "selected_output_budget": packet["wire"]["max_tokens"] == selected_policy.model.output_tokens[stage],
        "material_ids_resolve": all(ref["id"] in packet["material_ids"] for ref in refs if ref["type"] == "alert_material"),
        "material_refs_present": any(ref["type"] == "alert_material" for ref in refs),
        "material_ref_owners_preserved": all(
            (packet["members"] if stage == "A" else row.get("alert_ids"))
            == [backend[row["ref"]["id"]]["alert_id"]]
            for row in packet["source_map"].values() if row["ref"]["type"] == "alert_material"),
        "known_backend_sentinels_absent": all(v not in sent for v in packet["markers"]),
    }
    if variant == "r3":
        checks["r3_tenant_uid_not_sent"] = "tenant_uid" not in sent
    else:
        checks["business_text_and_same_named_ids_kept"] = all(BUSINESS[k] in sent for k in
            ("source", "id", "tenant_uid", "unknown_detail"))
        for key in ("unknown_amount", "unknown_authorized", "unknown_permissions"):
            checks[key + "_typed_value_kept"] = key in sent and has_typed_leaf(selected, key, BUSINESS[key])
        if variant == "structured":
            checks["other_business_branch_kept"] = all(v in sent for v in ("other-source-kept", "other-tenant-kept"))
    if stage in {"C3", "Deep", "C6"}:
        checks["frozen_member_aliases_kept"] = set(packet["members"]) <= set(packet["alias_keys"])
    output = os.environ.get("SOCAI2_D1_EVIDENCE_DIR")
    if output:
        target = Path(output)
        target.mkdir(parents=True, exist_ok=True)
        report = {"stage": stage, "variant": variant, "provenance": "offline_current_builder_replay",
            "policy": str(POLICY.relative_to(ROOT)), "policy_sha256": hashlib.sha256(POLICY.read_bytes()).hexdigest(),
            "input_profiles": {
                "A": {"version": selected_policy.alert_io.version, "sha256": selected_policy.alert_io.sha256},
                "I": {"version": selected_policy.incident_io.version, "sha256": selected_policy.incident_io.sha256},
                "Case": selected_policy.case_io.identity,
            },
            "source_snapshot_sha256": hashlib.sha256(original_bytes).hexdigest(),
            "original_backend": {mid: backend[mid] for mid in packet["material_ids"]},
            "network_calls": 0, "real_model_calls": 0, "checks": checks,
            **{k: v for k, v in packet.items() if k != "prepared"}}
        (target / f"{stage}-{variant}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    assert all(checks.values()), {key: value for key, value in checks.items() if not value}
