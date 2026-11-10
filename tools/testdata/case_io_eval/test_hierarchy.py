"""Direct nested-boundary checks using saved data, with no external execution."""
import copy
import json

import pytest
from app.socai2.baseline_store import digest, encoded

from .fixtures import load
from .hierarchy import enrichment, project, render, render_tools, translate
from .input_adapter import material_entries, prepare
from .output_adapter import tool_catalog
from .test_adapters import BUSINESS, CONFIG, ROOT


@pytest.fixture
def sample():
    return load(ROOT, CONFIG)


def test_nested_optional_rules_do_not_spread_to_unknown_business_fields():
    value = {"answer": None, "declared_scope": {"window_start": None, "window_end": None, "object_keys": []},
             "business": {"answer": None, "enabled": False, "count": 0, "items": [], "a.b/c": {"state": "open"}}}
    before, omissions = copy.deepcopy(value), []
    shown = project(value, "question", CONFIG, omissions, "test")
    assert value == before
    assert "answer" not in shown and shown["declared_scope"] == {}
    assert shown["business"] == value["business"]
    assert all(o["pointer"].startswith(("/answer", "/declared_scope")) for o in omissions)
    assert '"state":"open"' in render(shown, CONFIG)


@pytest.mark.parametrize("payload", [
    {"session_id": "actual-session", "session_key_kind": None, "originating_human": None},
    {"session_id": None, "session_key_kind": None, "originating_human": False},
    {"session_id": None, "session_key_kind": None, "originating_human": None, "future": []},
])
def test_nonempty_or_unknown_session_values_are_not_removed(payload):
    original = {"schema_version": "v1", "items": [{"kind": "fusion_session", "value": payload, "source": "fusion"}]}
    stripped = enrichment(original, CONFIG, [], "test")
    shown = project(stripped, "enrichment", CONFIG, [], "test")
    assert shown["items"][0]["value"] == payload
    assert "schema_version" in original


def test_only_recognized_empty_or_pointer_enrichment_envelopes_disappear():
    original = {"schema_version": "v1", "items": [
        {"kind": "fusion_session", "value": {"session_id": None, "originating_human": None}},
        {"kind": "first_fusion_result_reference", "value": {"artifact_id": "backend-id", "same_material_input": True}},
        {"kind": "future_business", "value": {"artifact_id": "business-id", "empty_observation": []}},
    ]}
    ledger = []
    shown = project(enrichment(original, CONFIG, ledger, "test"), "enrichment", CONFIG, ledger, "test")
    assert shown["items"] == original["items"][2:]
    assert len([o for o in ledger if o["pointer"].startswith("/items/")]) == 2


def test_different_fact_times_and_numeric_units_are_not_deduplicated(sample):
    member = sample["data"]["program_facts"]["members"][0]
    member["alert"]["event_time"] = "2026-01-02T03:04:05+00:00"
    member["activity_times"][0].update(unit="seconds", value=0)
    member["log_severity"] = [{"value": 0, "system": "custom-log-level"}]
    member["detection_labels"]["entries"] = [{"raw": "x123", "meaning": None, "mapping_state": "unknown"}]
    shown = prepare(sample, CONFIG, BUSINESS)
    fact = shown["presented_program_facts"]["members"][0]
    assert fact["alert"]["event_time"] == member["alert"]["event_time"]
    assert fact["activity_times"][0]["value"] == 0
    assert fact["activity_times"][0]["unit"] == "seconds"
    assert fact["log_severity"][0]["value"] == 0
    assert fact["detection_labels"]["entries"] == member["detection_labels"]["entries"]


def test_valid_facts_deduplicate_only_against_exact_visible_sources(sample):
    shown = prepare(sample, CONFIG, BUSINESS)
    for omission in shown["omissions"]:
        if omission.get("reason") != "same_fact_already_visible":
            continue
        row = next(r for r in shown["records"] if r["id"] == omission["source_id"])
        assert row["id"] in shown["user"]
        assert omission["value_sha256"]
    assert set(shown["presented_program_facts"]) == {"incident_severities"}
    assert next(iter(shown["presented_program_facts"]["incident_severities"].values()))["severity_source"] == "member_max"


def test_finding_nonempty_windows_objects_and_unknown_fields_survive(sample):
    finding = next(iter(sample["context"]["incidents"].values()))["diagnosis"]["diagnosis"]["findings"][0]
    finding["scope"].update(window_start="2026-01-01T00:00:00Z", window_end="2026-01-01T00:01:00Z",
                            object_keys=sample["context"]["scope"]["object_keys"][:1])
    finding["new_business"] = {"id": "actual-id", "no_result": [], "enabled": False}
    shown = prepare(sample, CONFIG, BUSINESS)
    row = next(r for r in shown["records"] if r["block"] == "finding")
    assert row["original_scope"] == finding["scope"]
    assert row["value"]["declared_scope"]["window_start"] == finding["scope"]["window_start"]
    assert row["value"]["declared_scope"]["object_keys"] == ["O1"]
    assert row["value"]["new_business"] == finding["new_business"]


def test_receipt_failure_and_truncation_never_become_empty_query():
    original = {"tool_name": "history", "state": "failed", "returned_rows": None, "outcome": "failed",
                "reason": "partial_response", "truncated": True, "truncation_reasons": ["timeout"],
                "scope": {"window_start": "start", "window_end": "end", "limitations": []},
                "other_parameters": {"offset": 0, "include_archived": False}, "selectors": []}
    shown = project(original, "receipt", CONFIG, [], "test")
    assert shown["state"] == "failed" and shown["returned_rows"] is None
    assert shown["truncation_reasons"] == ["timeout"] and shown["truncated"] is True
    assert shown["other_parameters"] == original["other_parameters"]
    assert shown["selectors"] == []
    assert shown["scope"]["window_start"] == "start"


def test_repeated_prior_prose_has_exact_target_without_merging_evidence(sample):
    shown = prepare(sample, CONFIG, BUSINESS)
    by_id = {r["id"]: r for r in shown["records"]}
    assert shown["prior_prose_references"]
    for source_id, fields in shown["prior_prose_references"].items():
        for name, target_id in fields.items():
            source, target = by_id[source_id], by_id[target_id]
            assert source["value"][name] == target["value"][name]
            assert source["ref"] != target["ref"]
            assert source["value"][name] in shown["user"]
            assert source["ref"]["role"] == target["ref"]["role"] == "prior_analysis"
    for row in shown["records"]:
        if row["block"] == "query" and row["ref"]["role"] != "execution_receipt":
            assert row["id"] in shown["user"]
    assert "的第 1 条返回" in shown["user"] and "返回记录" in shown["user"]


def test_shared_tool_fields_keep_capabilities_and_unavailable_tool(sample):
    prepared = prepare(sample, CONFIG, BUSINESS)
    catalog = tool_catalog(json.loads(sample["request"]["body"]["messages"][2]["content"]), prepared)
    original = copy.deepcopy(catalog)
    rendered = render_tools(catalog, CONFIG)
    assert catalog == original
    assert rendered["capabilities"] == catalog["capabilities"]
    for capability in catalog["capabilities"]:
        for key in ("purpose", "can_answer", "cannot_answer", "inputs"):
            assert capability[key] in rendered["text"]
        detail = next(r for r in rendered["ledger"] if r.get("tool_name") == capability["tool_name"]
                      and r["reason"] == "technical_fields_retained_in_backend")
        assert detail["returned_fields"] == capability["returned_fields"]
    assert "可用=false" in rendered["text"]


def test_same_material_observations_and_prior_prose_are_unchanged(sample):
    previous = json.loads((ROOT / CONFIG["comparison_candidate"] / "input-ledger.json").read_text())
    shown = prepare(sample, CONFIG, BUSINESS)
    by_ref = {encoded(r["ref"]): r for r in shown["records"]}
    for row in previous["records"]:
        if row["ref"]["role"] == "observation":
            new = by_ref[encoded(row["ref"])]
            assert new["value"] == row["value"] and new["alert_ids"] == row["alert_ids"]
        if row["ref"]["role"] == "prior_analysis":
            new = by_ref[encoded(row["ref"])]
            assert digest(new["original_value"]) == digest(row["original_value"])
    # The cross-type material check uses the same new recursive path.
    for relative in CONFIG["material_snapshots"]:
        for material in json.loads((ROOT / relative).read_text())["alert_materials"]:
            rows = material_entries(material["alert_id"], material, BUSINESS, [], CONFIG)
            assert rows and any(r["value"] == material["raw_text"] for r in rows)


def test_equal_field_presentation_keeps_different_values_and_types():
    shown = render({"event_time": "alert", "first_seen_at": "first", "last_seen_at": "alert",
                    "severity": 0, "severity_raw": False}, CONFIG)
    assert "告警时间/末次时间=alert" in shown and "首次时间=first" in shown
    assert "告警等级=0" in shown and "上游原始等级=false" in shown


def test_semantic_dictionary_only_changes_known_path_type_and_value():
    value = {"state": "completed", "reason": "new_reason", "future": {"state": "completed"}, "returned_rows": 0}
    ledger = []
    shown = translate(value, "receipt", CONFIG, ledger, "synthetic")
    assert shown["state"] == "已完成" and value["state"] == "completed"
    assert shown["future"] == value["future"] and shown["reason"] == "new_reason"
    assert shown["returned_rows"] == 0
    assert translate({"ocsf_class_uid": "3002"}, "detection", CONFIG, [], "test")["ocsf_class_uid"] == "3002"
    assert translate({"ocsf_class_uid": 9999}, "detection", CONFIG, [], "test")["ocsf_class_uid"] == 9999
    assert [row["pointer"] for row in ledger] == ["/state"]


@pytest.mark.parametrize("change", ["missing_business_description", "unknown_return_field"])
def test_tool_detail_falls_back_when_business_contract_is_incomplete(sample, change):
    prepared = prepare(sample, CONFIG, BUSINESS)
    catalog = tool_catalog(json.loads(sample["request"]["body"]["messages"][2]["content"]), prepared)
    capability = catalog["capabilities"][0]
    if change == "missing_business_description":
        capability["can_answer"] = ""
    else:
        capability["returned_fields"].append("new_business_evidence")
    rendered = render_tools(catalog, CONFIG)
    assert all(field in rendered["text"] for field in capability["returned_fields"])
    assert not any(row.get("tool_name") == capability["tool_name"] and row["reason"] == "technical_fields_retained_in_backend"
                   for row in rendered["ledger"])


def test_heading_keeps_external_finding_member_and_remaining_window(sample):
    finding = next(iter(sample["context"]["incidents"].values()))["diagnosis"]["diagnosis"]["findings"][0]
    finding["scope"]["alert_ids"].append("00000000-0000-0000-0000-000000999999")
    finding["scope"]["window_start"] = "2026-10-01T00:00:00Z"
    shown = prepare(sample, CONFIG, BUSINESS)
    row = next(r for r in shown["records"] if r["block"] == "finding")
    display = next(r for r in shown["presentation_ledger"] if r.get("source_id") == row["id"]
                   and r["reason"] == "scope_members_in_heading")
    assert display["heading_members"] == row["value"]["declared_scope"]["alert_ids"] == ["A1", "X1"]
    assert "原范围=A1、X1" in shown["user"]
    assert display["remaining_scope"]["window_start"] == "2026-10-01T00:00:00Z"
    assert row["original_scope"] == finding["scope"]


def test_material_dictionary_keeps_conflicting_class_and_unknown_values(sample):
    material = next(iter(sample["materials"].values()))
    material["ocsf_json"]["class_uid"] = 9999
    material["raw_json"]["future"] = {"class_uid": 3002, "action": "logon"}
    shown = prepare(sample, CONFIG, BUSINESS)
    unknown = next(r for r in shown["records"] if r["ref"]["id"] == material["id"] and r["ref"]["source_path"] == "$.ocsf_json.class_uid")
    assert unknown["value"] == 9999 and "记录类别：9999" in shown["user"]
    future = next(r for r in shown["records"] if r["ref"]["id"] == material["id"] and r["ref"]["source_path"] == "$.raw_json.future.class_uid")
    assert future["value"] == 3002
    assert not any(r.get("source_id") == future["id"] and r["reason"] == "existing_field_dictionary"
                   for r in shown["presentation_ledger"])
    groups = shown["presentation_ledger"][0]["groups"]
    assert next(g for g in groups if unknown["id"] in g) == [unknown["id"]]
    assert "记录类别：身份认证" in shown["user"]


def test_candidate_preserves_all_prior_records_and_explicit_prose(sample):
    previous = json.loads((ROOT / CONFIG["comparison_candidate"] / "input-ledger.json").read_text())
    shown = prepare(sample, CONFIG, BUSINESS)
    by_ref = {encoded(r["ref"]): r for r in shown["records"]}
    assert len(by_ref) == len(previous["records"])
    for old in previous["records"]:
        new = by_ref[encoded(old["ref"])]
        assert new["value"] == old["value"] and new["original_value"] == old["original_value"]
        assert new.get("original_scope") == old.get("original_scope")
        for key in ("rationale", "statement", "text"):
            if new["ref"]["role"] == "prior_analysis" and isinstance(new["value"], dict) and key in new["value"]:
                assert new["value"][key] in shown["user"]
