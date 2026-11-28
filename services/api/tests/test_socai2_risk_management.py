"""Public edit boundaries; PostgreSQL/TCP tests verify mutation and receipts."""
import json
from pathlib import Path
from uuid import uuid4

import pytest
from app.socai2.case_management_contracts import CaseManagementUpdate
from app.socai2.subject_management_contracts import IncidentManagementUpdate
from pydantic import ValidationError


def request(model, **fields):
    return model(operation_key=uuid4(), expected_row_version=1, **fields)


@pytest.mark.parametrize("model", [CaseManagementUpdate, IncidentManagementUpdate])
@pytest.mark.parametrize("fields", [
    {"priority_value": None, "priority_reason": "reviewed"},
    {"priority_value": -1, "priority_reason": "reviewed"},
    {"priority_value": 101, "priority_reason": "reviewed"},
    {"priority_value": True, "priority_reason": "reviewed"},
    {"priority_value": "60", "priority_reason": "reviewed"},
    {"priority_value": 60.005, "priority_reason": "reviewed"},
    {"priority_value": 0}, {"priority_value": 0, "priority_reason": " "},
    {"clear_priority_override": True}, {"clear_priority_override": False},
    {"priority_reason": "orphan"},
    {"priority_value": 0, "clear_priority_override": True, "priority_reason": "reviewed"},
    {"clear_priority_override": "true", "priority_reason": "reviewed"},
])
def test_invalid_priority_operations(model, fields):
    with pytest.raises(ValidationError):
        request(model, **fields)


@pytest.mark.parametrize("model", [CaseManagementUpdate, IncidentManagementUpdate])
def test_explicit_priority_boundaries_and_omission(model):
    for value in (0, 60.5, 100):
        assert request(model, priority_value=value, priority_reason="reviewed").priority_value == value
    assert request(model, clear_priority_override=True, priority_reason="restore").clear_priority_override
    patch = request(model, tags=[], clear_priority_override=False)
    assert "priority_value" not in patch.model_fields_set
    schema = model.model_json_schema()["properties"]
    assert "anyOf" not in schema["priority_value"]
    assert "default" not in schema["priority_value"]


@pytest.mark.parametrize("fields", [{"severity": None}, {"severity": "high"},
    {"severity": "high", "severity_reason": " "}, {"severity_reason": "orphan"}])
def test_case_grade_is_required_when_explicit(fields):
    with pytest.raises(ValidationError):
        request(CaseManagementUpdate, **fields)


def test_incident_restore_is_an_explicit_reasoned_action():
    for value in (None, "high"):
        with pytest.raises(ValidationError):
            request(IncidentManagementUpdate, severity_override=value)
        with pytest.raises(ValidationError):
            request(IncidentManagementUpdate, severity_override=value, severity_override_reason=" ")
        valid = request(IncidentManagementUpdate, severity_override=value, severity_override_reason="reviewed")
        assert "severity_override" in valid.model_fields_set
    assert request(CaseManagementUpdate, severity="low", severity_reason="reviewed").severity == "low"


def test_alert_contracts_keep_fields_outside_approved_management_changes():
    from investigation_http.main import app

    root = Path(__file__).resolve().parents[3]
    before = json.loads((root / "docs/operations/evidence/subject-risk-s1-20261120-01/candidate-openapi.json").read_text())
    after = app.openapi()
    assert set(before["paths"]) | {"/api/v1/socai2/people"} == set(after["paths"])
    old_schemas, schemas = (doc["components"]["schemas"] for doc in (before, after))
    assert old_schemas["AlertFacts"] == schemas["AlertFacts"]
    # The single-alert fields are now inlined; the batch references its own DTO.
    assert old_schemas["AlertManagementFields"]["properties"] == {
        name: field for name, field in schemas["AlertManagementUpdate"]["properties"].items()
        if name not in {"operation_key", "expected_row_version"}
    }
    # Alert writes now accept stale versions and batch tags are no longer writable.
    # Other existing fields/types and operation paths remain frozen.
    for name in ("AlertManagementUpdate", "AlertFeedback"):
        old, new = (json.loads(json.dumps(doc["components"]["schemas"][name])) for doc in (before, after))
        for schema in (old, new):
            schema["properties"]["expected_row_version"].pop("description")
        assert old == new
    for name in ("AlertManagementBatch", "AlertFeedbackBatch"):
        old, new = (json.loads(json.dumps(doc["components"]["schemas"][name])) for doc in (before, after))
        assert old["properties"]["items"]["items"]["$ref"] == "#/components/schemas/SelectedSubject"
        assert new["properties"]["items"]["items"]["$ref"] == "#/components/schemas/SelectedAlert"
        new["properties"]["items"]["items"]["$ref"] = old["properties"]["items"]["items"]["$ref"]
        if name == "AlertManagementBatch":
            assert old["properties"]["changes"]["$ref"] == "#/components/schemas/AlertManagementFields"
            assert new["properties"]["changes"]["$ref"] == "#/components/schemas/AlertBatchManagementFields"
            new["properties"]["changes"]["$ref"] = old["properties"]["changes"]["$ref"]
        for schema in (old, new):
            schema["properties"]["items"].pop("description")
            if name == "AlertManagementBatch":
                schema["properties"]["changes"].pop("description")
        assert old == new
    old = json.loads(json.dumps(old_schemas["SelectedSubject"]))
    new = json.loads(json.dumps(schemas["SelectedAlert"]))
    new["title"] = old["title"]
    for schema in (old, new):
        schema["properties"]["expected_row_version"].pop("description")
    assert old == new
    old = json.loads(json.dumps(old_schemas["AlertManagementFields"]))
    new = json.loads(json.dumps(schemas["AlertBatchManagementFields"]))
    new["title"] = old["title"]
    old["properties"].pop("tags")
    assert old == new
    assert old_schemas["FeedbackFields"] == schemas["FeedbackFields"]
    assert "anyOf" not in schemas["CaseManagementUpdate"]["properties"]["severity"]
    for name in ("CaseManagementUpdate", "IncidentManagementUpdate", "IncidentManagementFields"):
        assert {"priority_value", "priority_reason", "clear_priority_override"} <= set(schemas[name]["properties"])
