import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("coverage_inspector", Path(__file__).with_name("inspect_lake_tool_coverage.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_review_contains_only_allowlisted_paths_and_types():
    coverage = module.Coverage(["device.hostname", "file.path", "is_alert", "time"])
    coverage.add({"class_uid": 1001, "device": {"hostname": "PrivateHost"}, "file": {"path": "PrivatePath"},
                  "PrivateKey": "PrivateValue", "is_alert": False, "time": 123}, reliable_time=True)
    private, review = coverage.reports()
    text = json.dumps(review) + module.review_markdown(review)
    assert all(value not in text for value in ("PrivateHost", "PrivatePath", "PrivateKey", "PrivateValue", '"records"', '123'))
    assert private["groups"][0]["records"] == 1
    assert review["groups"][0]["same_record_conditions"]["root_object_and_reliable_event_time"] is True
    assert next(field for field in review["groups"][0]["fields"] if field["path"] == "is_alert")["has_nonempty_value"] is True


def test_joint_fields_are_not_combined_across_records():
    coverage = module.Coverage(["device.hostname", "time"])
    coverage.add({"class_uid": 4001, "device": {"hostname": "HostA"}}, reliable_time=False)
    coverage.add({"class_uid": 4001, "time": 123}, reliable_time=True)
    assert coverage.reports()[1]["groups"][0]["same_record_conditions"]["root_object_and_reliable_event_time"] is False


def test_partial_declaration_stays_distinct_from_root_and_field_values():
    coverage = module.Coverage(["device.hostname"])
    coverage.add({"class_uid": 0, "unmapped": {"spirithub": {"mapping_status": "partial",
        "classification": {"class_uid": 2004}, "partial_fields": {"device": {"hostname": "PrivateHost"}}}}}, reliable_time=True)
    group = coverage.reports()[1]["groups"][0]
    assert group["class_uid"] == 0 and group["declared_partial_class_uid"] == 2004
    assert group["fields"][0]["path"] == "unmapped.spirithub.partial_fields.device.hostname"
    assert group["same_record_conditions"]["root_object_and_reliable_event_time"] is False
    assert group["same_record_conditions"]["partial_object_and_reliable_event_time"] is True


def test_array_paths_do_not_emit_member_values_or_custom_keys():
    coverage = module.Coverage(["answers", "answers[].rdata", "file.size"])
    coverage.add({"class_uid": 4003, "answers": [{"rdata": "PrivateAnswer", "PrivateKey": 1}], "file": {"size": 0}}, reliable_time=False)
    _, review = coverage.reports()
    assert "Private" not in json.dumps(review)
    assert {field["path"]: field["observed_types"] for field in review["groups"][0]["fields"]} == {
        "answers": ["array"], "answers[].rdata": ["string"], "file.size": ["integer"]}


def test_invalid_class_cannot_export_an_identifier_and_unspecified_ip_is_not_a_selector():
    coverage = module.Coverage(["class_uid", "device.ip"])
    coverage.add({"class_uid": "PrivateClass", "device": {"ip": "::ffff:0.0.0.0"}}, reliable_time=True)
    group = coverage.reports()[1]["groups"][0]
    assert group["class_uid"] is None
    assert group["same_record_conditions"]["root_object_and_reliable_event_time"] is False
    assert "PrivateClass" not in json.dumps(group)


def test_empty_arrays_preserve_parent_type_without_inventing_leaf_presence():
    coverage = module.Coverage(["answers", "answers[].rdata"])
    coverage.add({"class_uid": 4003, "answers": []}, reliable_time=False)
    assert coverage.reports()[1]["groups"][0]["fields"] == [
        {"path": "answers", "observed_types": ["array"], "has_nonempty_value": False}]
