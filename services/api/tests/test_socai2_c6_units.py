"""C6 closed-unit reception and publication use frozen real response values."""
import copy
import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from app.socai2 import case_c6_delivery as receiver
from app.socai2.baseline_context import Context
from app.socai2.baseline_delivery_contract import Delivery
from app.socai2.baseline_delivery_projection import make_publication
from app.socai2.case_followup_output import parse_final
from app.socai2.citation_quality import new_review

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "docs/operations/evidence/c6-unit-continuation-d5b-20261118-01/fixtures-01"


@pytest.fixture
def mother():
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    source = json.loads((ROOT / manifest["source"]).read_text())
    artifacts = {a["id"]: a["content_json"] or {} for a in source["artifacts"]}
    prepared = copy.deepcopy(artifacts[manifest["request_artifact_id"]]["payload"])
    prepared["coverage"] = {aid: {"included": sum(aid in row["alert_ids"] for row in prepared["source_map"].values())}
                            for aid in prepared["case_boundary"]["member_aliases"]}
    context = Context.model_validate(next(v for v in artifacts.values() if "case_input_profile" in v))
    report = next(v for v in artifacts.values() if v.get("type") == "delivery_report")
    text = (FIXTURES / "mother.txt").read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == manifest["mother_sha256"]
    return text, prepared, context, report["comparison"]


def receive(mother, text=None, **options):
    raw, prepared, context, comparison = mother
    return receiver.receive(raw if text is None else text, prepared, context, comparison, uuid4(), **options)


def test_new_severity_missing_keeps_existing_independent_final_core(mother):
    from app.socai2.severity_opinion import VERSION
    mother[1]["severity_opinion_version"] = VERSION
    received = receive(mother)
    assert received["full_delivery"] is None
    assert received["delivery"]["state"] == "partial"
    assert received["use"]["adoption_eligible"]
    assert any(unit["path"] == "$.severity_opinion" for unit in received["missing_units"])
    assert publish(mother, received).validation_state == "accepted"


def publish(mother, received):
    _, prepared, context, comparison = mother
    prepared = {**prepared, "c6_delivery": received}
    value = Delivery.model_validate(received["full_delivery"]) if received["full_delivery"] else (
        receiver.RetainedFinal(received["retained_output"]["fields"]) if received["retained_units"] else None)
    members = {UUID(aid): {"read_state": "read", "analysis_state": "analyzed"} for aid in context.alerts}
    return make_publication(value, context, members, prepared, comparison,
        {"delivery_state": "complete", "graph_artifact_id": uuid4()}, uuid4(), "final_output_no_usable_units")[0]


@pytest.mark.parametrize("name", ["complete-stop", "complete-length", "core-tail-cut", "analysis-only", "empty"])
def test_independent_source_spans_and_publication(mother, name):
    text = (FIXTURES / (name + ".txt")).read_text()
    expected = json.loads((FIXTURES / (name + ".expected.json")).read_text())
    received = receive(mother, text, finish_reason=expected["finish_reason"])
    want = expected["lexically_complete_original_units"]
    fields = ("path", "value_span", "value_sha256", "value")
    assert sorted([tuple(str(u[k]) for k in fields) for u in received["retained_units"]]) == sorted([
        tuple(str(u[k]) for k in fields) for u in want])
    assert received["invalid_units"] == []
    assert received["delivery"]["state"] == expected["delivery_state"]
    assert received["use"]["dispatch_paths"] == []
    result = publish(mother, received)
    assert result.validation_state == expected["validation_state"]
    assert result.terminal_state == expected["terminal_state"]
    assert result.conclusion == (expected["core"]["text"] if expected["core"] else None)
    assert len(result.members) == len(mother[2].alerts)
    if not expected["core"]:
        assert result.conclusion_state == "unavailable" and not any(m.conclusion_covered for m in result.members)
    if name == "core-tail-cut":
        assert result.delivery_state == "partial" and result.case_impact.summary is None
        assert received["full_delivery"] is None and "closing_note" not in received["retained_output"]["fields"]


@pytest.mark.parametrize("change", ["missing-member", "partial-core", "unknown-member", "not-analyzed"])
def test_partial_scope_never_qualifies(mother, change):
    raw = json.loads(mother[0])
    raw.pop("impact")
    if change == "missing-member":
        raw["analysis"]["members"].pop()
    elif change == "partial-core":
        raw["conclusion"]["alert_ids"].pop()
    elif change == "unknown-member":
        raw["analysis"]["members"][-1]["alert_id"] = "A999"
    else:
        raw["analysis"]["members"][-1].update(state="not_analyzed", evidence_ids=[])
    received = receive(mother, json.dumps(raw, ensure_ascii=False))
    assert not received["use"]["adoption_eligible"]
    result = publish(mother, received)
    assert result.validation_state == "rejected" and result.terminal_state == "failed"
    assert result.conclusion == raw["conclusion"]["text"]
    if change in {"missing-member", "unknown-member"}:
        missing = [m for m in result.members if m.assessment_state == "not_analyzed"]
        assert len(missing) == 1 and missing[0].assessment is None and not missing[0].conclusion_covered


def test_nested_duplicate_only_discards_affected_member(mother):
    raw = json.loads(mother[0])
    members = raw["analysis"]["members"]
    first = json.dumps(members[0], ensure_ascii=False)
    bad = json.dumps(members[1], ensure_ascii=False)[:-1] + ',"state":"unresolved"}'
    text = '{"analysis":{"summary":' + json.dumps(raw["analysis"]["summary"]) + ',"members":[' + first + ',' + bad
    received = receive(mother, text)
    assert {u["path"] for u in received["retained_units"]} == {"$.analysis.summary", "$.analysis.members[0]"}
    assert any(u["path"] == "$.analysis.members[1]" and u["reason_code"] == "duplicate_json_key" for u in received["invalid_units"])
    assert publish(mother, received).terminal_state == "failed"


def test_closed_bad_member_keeps_later_members_and_core(mother):
    raw = json.loads(mother[0])
    text = json.dumps(raw, ensure_ascii=False)
    member = json.dumps(raw["analysis"]["members"][1], ensure_ascii=False)
    assert text.count(member) == 1
    text = text.replace(member, member[:-1] + ',"state":"unresolved"}')
    received = receive(mother, text)
    kept = {u["path"] for u in received["retained_units"]}
    assert "$.analysis.members[1]" not in kept
    assert {"$.analysis.members[0]", "$.analysis.members[2]", "$.analysis.members[3]", "$.conclusion"} <= kept
    result = publish(mother, received)
    assert result.conclusion == raw["conclusion"]["text"] and result.validation_state == "rejected"
    assert sum(m.assessment is None for m in result.members) == 1


@pytest.mark.parametrize("key", ["analysis", "conclusion"])
def test_duplicate_whole_fields_exclude_both_definitions(mother, key):
    raw = json.loads(mother[0])
    text = json.dumps(raw, ensure_ascii=False)[:-1] + ',' + json.dumps(key) + ':' + json.dumps(raw[key], ensure_ascii=False) + '}'
    received = receive(mother, text)
    assert all(not u["path"].startswith("$." + key) for u in received["retained_units"])
    assert received["full_delivery"] is None and not received["use"]["adoption_eligible"]


def test_unknown_nested_duplicate_does_not_discard_sibling_units(mother):
    raw = json.loads(mother[0])
    analysis = json.dumps(raw["analysis"], ensure_ascii=False)
    text = json.dumps(raw, ensure_ascii=False).replace(analysis, analysis[:-1] + ',"unknown":{"x":1,"x":2}}')
    received = receive(mother, text)
    assert len(received["retained_output"]["fields"]["analysis"]["members"]) == 4
    assert received["use"]["adoption_eligible"] and received["full_delivery"] is None
    assert any(u["path"] == "$.analysis.unknown" for u in received["invalid_units"])


def test_wrong_optional_comparison_is_excluded_without_discarding_valid_core(mother):
    raw = json.loads(mother[0])
    raw["comparison"] = {"kind": "changed", "summary": "model comparison must be excluded", "support_ids": []}
    received = receive(mother, json.dumps(raw, ensure_ascii=False))
    assert received["full_delivery"] is None and received["delivery"]["state"] == "partial"
    assert any(u["reason_code"] == "model_must_not_supply_fixed_comparison" for u in received["invalid_units"])
    assert "$.comparison" in received["retained_output"]["program_fields"]
    assert all(u["path"] != "$.comparison" for u in received["retained_units"])
    result = publish(mother, received)
    assert result.validation_state == "accepted" and result.conclusion == raw["conclusion"]["text"]
    assert result.change_kind == "initial" and result.change_summary is None


def test_recommendation_ids_follow_original_indices_and_raw_is_immutable(mother):
    raw = json.loads(mother[0])
    recommendation = copy.deepcopy(raw["recommendations"][0])
    raw["recommendations"] = [{**recommendation, "object_keys": ["unknown-object"]}, recommendation]
    received = receive(mother, json.dumps(raw, ensure_ascii=False))
    assert received["retained_output"]["fields"]["recommendations"][0]["id"] == "R2"
    original = next(u for u in received["retained_units"] if u["path"] == "$.recommendations[1]")
    assert original["value"] == recommendation and "id" not in original["value"]
    assert received["delivery"]["state"] == "partial"


def test_original_null_conflicts_note_and_quality_are_kept_separate(mother):
    text = (FIXTURES / "original.txt").read_text()
    received = receive(mother, text)
    assert received["full_delivery"] is not None and received["quality"]["issues"]
    assert received["use"]["adoption_eligible"]
    review = new_review()
    parsed = parse_final(mother[0], mother[1], mother[2], mother[3], citation_review=review)
    complete = receive(mother)
    assert complete["full_delivery"] == parsed.model_dump(mode="json")
    for key in ("issues", "processing", "references"):
        assert complete["quality"][key] == review[key]
    assert len(complete["quality"]["issues"]) == 2
    raw = json.loads(mother[0])
    raw["analysis"]["conflicts_note"] = None
    received = receive(mother, json.dumps(raw, ensure_ascii=False))
    assert received["full_delivery"] is not None
    assert received["output_adapter"] is not None
    assert "conflicts_note" not in received["retained_output"]["fields"]["analysis"]
