"""I completeness, business uncertainty and execution state are independent."""
import copy
import json
from pathlib import Path

import jsonschema
import pytest
from app.socai2.baseline_store import StoreError
from app.socai2.incident_delivery import assess
from app.socai2.incident_diagnosis_contract import parse
from test_socai2_stage_partial_review import packet


def example():
    refs, data, _, answer = packet()
    result, members = parse(json.dumps(answer), refs, data)
    source = {"members": [{"alert": {"id": m["alert_id"]}} for m in members]}
    return source, result.model_dump(mode="json"), members


def test_complete_output_can_still_require_review():
    source, output, members = example()
    before = copy.deepcopy((source, output, members))
    members[0]["state"] = "unresolved"
    value = assess(source, output=output, members=members)
    assert value["state"] == "complete" and value["review_items"]["state"] == "required"
    assert value["review_items"]["unresolved_member_ids"] == [members[0]["alert_id"]]
    assert value["review_items"]["open_question_ids"] == ["Q1"] and not value["reasons"]
    assert source == before[0] and output == before[1]


def test_no_open_items_does_not_become_a_benign_verdict():
    source, output, members = example()
    output.update(findings=[], open_questions=[], conclusion="待复核只是原始正文，本函数不读取它。")
    value = assess(source, output=output, members=members)
    assert value["state"] == "complete" and value["review_items"]["state"] == "none_listed"
    assert "verdict" not in value


@pytest.mark.parametrize("change,reason", [("missing", "member_analysis_missing"), ("not_reviewed", "member_analysis_not_completed")])
def test_valid_global_output_with_unfinished_member_is_partial(change, reason):
    source, output, members = example()
    if change == "missing":
        members.pop()
    else:
        members[0].update(state="not_reviewed", source_ids=[])
    value = assess(source, output=output, members=members)
    assert value["state"] == "partial" and reason in value["reasons"]


def test_only_retained_valid_units_count_as_partial_delivery():
    source, output, members = example()
    review = {"retained_analysis": {"members": members[:1], "findings": output["findings"][:1], "open_questions": []}}
    value = assess(source, partial_review=review)
    assert value["state"] == "partial" and "invalid_response_units_excluded" in value["reasons"]
    assert value["member_coverage"]["missing_ids"] == [members[1]["alert_id"]]
    review["retained_analysis"] = {"members": [], "findings": [], "open_questions": []}
    assert assess(source, partial_review=review)["state"] == "none"


def test_not_reviewed_placeholder_does_not_count_as_delivered_analysis():
    source, output, members = example()
    for m in members:
        m.update(state="not_reviewed", source_ids=[])
    kept = {"members": members, "findings": [f for f in output["findings"] if f["id"].startswith("member:")], "open_questions": []}
    value = assess(source, partial_review={"retained_analysis": kept})
    assert value["state"] == "none" and value["review_items"]["state"] == "unknown"


def test_unknown_or_failed_execution_without_validated_content_has_no_delivery():
    source, _, _ = example()
    source["artifacts"] = [{"kind": "model_request"}, {"kind": "model_response", "raw": {"text": "unvalidated"}}]
    value = assess(source)
    assert value["state"] == "none" and value["review_items"]["state"] == "unknown"


def test_invalid_coverage_cannot_claim_complete():
    source, output, members = example()
    members.append(copy.deepcopy(members[0]))
    with pytest.raises(StoreError, match="incident_delivery_member_scope_invalid"):
        assess(source, output=output, members=members)


def test_optional_metadata_is_compatible_in_all_three_json_contracts():
    source, output, members = example()
    diagnosis = {k: output[k] for k in ("conclusion", "findings", "source_refs", "limitations")}
    diagnosis["validation_state"] = "accepted"
    root = Path(__file__).resolve().parents[3]
    runtime = json.loads((root / "services/api/app/socai2/contracts.schema.json").read_text())
    published = json.loads((root / "docs/design/socai2-json-contracts-20261103.schema.json").read_text())
    dictionary = json.loads((root / "docs/design/socai2-data-contract-20261103.json").read_text())
    assert runtime["$defs"]["diagnosis"] == published["$defs"]["diagnosis"] == dictionary["contracts"]["diagnosis"]["schema"]
    schema = {"$defs": runtime["$defs"], "$ref": "#/$defs/diagnosis"}
    jsonschema.validate(diagnosis, schema)  # Old stored JSON needs no rewriting.
    diagnosis["delivery_assessment"] = assess(source, output=output, members=members)
    jsonschema.validate(diagnosis, schema)
    diagnosis["delivery_assessment"]["state"] = "fabricated"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(diagnosis, schema)
