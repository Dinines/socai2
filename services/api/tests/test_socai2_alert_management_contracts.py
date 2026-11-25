"""Alert-only management boundary; incident request shape stays unchanged."""
from uuid import uuid4

import pytest
from app.socai2.subject_management_contracts import (
    AlertFeedback,
    AlertFeedbackBatch,
    AlertManagementBatch,
    AlertManagementUpdate,
    IncidentManagementBatch,
    IncidentManagementUpdate,
)
from pydantic import ValidationError


@pytest.mark.parametrize("tags", [["reviewed"], [], None])
def test_batch_alert_tags_are_rejected_even_with_another_change(tags):
    with pytest.raises(ValidationError, match="batch alert tags are not supported"):
        AlertManagementBatch(operation_key=uuid4(),
            items=[{"id": uuid4(), "expected_row_version": 1}],
            changes={"owner_id": None, "tags": tags})


def test_single_alert_tags_replace_clear_and_omit():
    common = {"operation_key": uuid4(), "expected_row_version": 1}
    assert AlertManagementUpdate(**common, tags=["reviewed"]).tags == ["reviewed"]
    assert AlertManagementUpdate(**common, tags=[]).model_dump(exclude_unset=True)["tags"] == []
    assert "tags" not in AlertManagementUpdate(**common, owner_id=None).model_dump(exclude_unset=True)


def test_alert_schema_explains_versions_and_hides_batch_tags_only():
    for model in (AlertManagementUpdate, AlertFeedback):
        field = model.model_json_schema()["properties"]["expected_row_version"]
        assert field["minimum"] == 1 and "旧版本不拒绝" in field["description"]
    for model in (AlertManagementBatch, AlertFeedbackBatch):
        schema = model.model_json_schema()
        selected = schema["$defs"]["SelectedAlert"]["properties"]["expected_row_version"]
        assert selected["minimum"] == 1 and "旧版本不拒绝" in selected["description"]
    assert "tags" not in AlertManagementBatch.model_json_schema()["$defs"]["AlertBatchManagementFields"]["properties"]
    assert "tags" in IncidentManagementBatch.model_json_schema()["$defs"]["IncidentManagementFields"]["properties"]
    assert "过期409" in IncidentManagementUpdate.model_json_schema()["properties"]["expected_row_version"]["description"]
