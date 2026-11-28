"""Known ingress administration stays backstage; fixtures are generated locally."""
import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest
from app.socai2 import case_followup_input, case_model_boundary, runtime_policy
from app.socai2.baseline_context import Context, reference
from app.socai2.baseline_store import encoded
from app.socai2.case_c3_input_selection import select_rows
from test_socai2_case_material_mirrors import context, entries, material
from test_socai2_case_material_mirrors import (
    profile as profile,  # noqa: PLC0414 -- expose the shared pytest fixture
)

BACKEND = "$.raw_json.field_metadata.lake_ingress"
METADATA = "$.raw_json.field_metadata"
SOURCE = "$.raw_json.source"


def ingress_material():
    aid, original = material()
    original["raw_json"]["field_metadata"] = {
        "lake_ingress": {"schema_version": "socai2.lake-alert-input.v1", "lake_database": uuid4().hex,
            "lake_ref": {"event_id": str(uuid4()), "source_version": uuid4().hex},
            "source_subject_id": str(uuid4()), "source_event_id": str(uuid4())},
        "business_extension": {"text": uuid4().hex, "count": 0, "enabled": False, "observations": []},
        "lake_ingress_note": uuid4().hex}
    original["raw_json"]["raw_event"]["lake_ingress"] = {"label": uuid4().hex}
    return aid, original


def backend(row):
    path = row["ref"]["source_path"] or ""
    return path == BACKEND or path.startswith(BACKEND + ".")


def select(profile, rows, aid, required=()):
    return select_rows(rows, {"alerts": {aid: {"alert": {}}}}, profile.config,
                       profile.business["render"], [], required_refs=required)


def test_backend_selection_survives_c3_json_storage_and_c6(profile, tmp_path):
    aid, original = ingress_material()
    frozen = context(profile, aid, original)
    before = encoded(original)
    base = case_model_boundary.build(frozen, uuid4(), [], [], {aid: original})
    assert base["ready"]
    saved = tmp_path / "generated-input.json"
    saved.write_bytes(encoded(base))
    base = json.loads(saved.read_bytes())
    final = case_followup_input.build("C6", frozen, base, {})
    assert final["ready"]
    rows = base["input_ledger"]["records"]
    selected = {row["ref"]["source_path"]: row for row in rows if row["ref"]["type"] == "alert_material"}
    assert selected[METADATA + ".business_extension.count"]["value"] == 0
    assert selected[METADATA + ".business_extension.enabled"]["value"] is False
    assert selected[METADATA + ".business_extension.observations"]["value"] == []
    assert METADATA + ".lake_ingress_note" in selected
    assert "$.raw_json.raw_event.lake_ingress.label" in selected
    for view in (base, final):
        assert not any(backend(row) for row in view["source_map"].values())
        prompt = "\n".join(message["content"] for message in view["messages"])
        assert original["raw_json"]["field_metadata"]["lake_ingress"]["lake_database"] not in prompt
        assert original["raw_json"]["field_metadata"]["business_extension"]["text"] in prompt
        assert original["raw_json"]["raw_event"]["lake_ingress"]["label"] in prompt
        assert any(row["reason"] == "configured_c3_material_backend_field" and backend(row)
                   for row in view["omissions"] if "ref" in row)
    for row in base["source_map"].values():
        if row["ref"]["type"] == "alert_material":
            assert any(source == row for source in final["source_map"].values())
    assert encoded(original) == before


@pytest.mark.parametrize("shape", ["unrecognized_envelope", "unaddressable_parent"])
def test_unrecognized_or_unsplittable_material_keeps_original_business_content(profile, shape):
    aid, original = ingress_material()
    if shape == "unrecognized_envelope":
        original["raw_json"].pop("identity_version")
    else:
        original["raw_json"]["field_metadata"]["unknown.business"] = uuid4().hex
    before = encoded(original)
    rows, _ = entries(profile, aid, original)
    selected = select(profile, rows, aid)
    if shape == "unrecognized_envelope":
        assert [row for row in selected if backend(row)] == [row for row in rows if backend(row)]
    else:
        parent = next(row for row in selected if row["ref"]["source_path"] == METADATA)
        assert parent["value"] == parent["original_value"] == original["raw_json"]["field_metadata"]
        assert parent["ref"]["role"] == "source_label"
        assert parent["alert_ids"] == [aid]
    assert encoded(original) == before


def test_empty_management_container_uses_existing_optional_selection(profile):
    aid, original = ingress_material()
    original["raw_json"]["field_metadata"] = {}
    rows, omissions = entries(profile, aid, original)
    assert not any(row["ref"]["source_path"] == METADATA for row in rows)
    assert any(row.get("path") == METADATA and row["reason"] == "configured_material_wrapper" for row in omissions)
    assert original["raw_json"]["field_metadata"] == {}


@pytest.mark.parametrize(("path", "dependency"), [
    (BACKEND + ".lake_database", "required"), (BACKEND + ".lake_ref", "human"),
    (None, "prior"), (BACKEND + ".lake_database.child", "required")])
def test_backend_dependencies_keep_original_sources_without_restoring_old_source_field(profile, path, dependency):
    aid, original = ingress_material()
    rows, _ = entries(profile, aid, original)
    ref = reference("alert_material", original["id"], "source_label", path)
    required = [ref] if dependency == "required" else []
    if dependency != "required":
        value = {"source_refs": [ref]}
        rows.append({"id": "prior", "ref": reference("artifact", str(uuid4()), "prior_analysis"),
            "alert_ids": [aid], "value": copy.deepcopy(value), "original_value": value,
            "block": "triage" if dependency == "prior" else "background",
            **({"context_kind": "human_feedback"} if dependency == "human" else {})})
    selected = select(profile, rows, aid, required)
    expected = [row for row in rows if backend(row) and (path is None or row["ref"]["source_path"] == path
        or row["ref"]["source_path"].startswith(path + ".") or path.startswith(row["ref"]["source_path"] + "."))]
    assert expected
    assert [row for row in selected if backend(row)] == expected
    assert all(row["alert_ids"] == [aid] and row["ref"]["role"] == "source_label" for row in expected)
    assert not any(row["ref"]["source_path"] == SOURCE for row in selected)


def test_old_source_exact_reference_behavior_is_unchanged(profile):
    aid, original = ingress_material()
    rows, _ = entries(profile, aid, original)
    ref = reference("alert_material", original["id"], "source_label", SOURCE)
    selected = select(profile, rows, aid, [ref])
    assert any(row["ref"] == ref and row["value"] == original["raw_json"]["source"] for row in selected)
    assert not any(backend(row) for row in selected)


def test_human_dependency_survives_c3_json_storage_and_c6(profile, tmp_path):
    aid, original = ingress_material()
    before = encoded(original)
    raw = context(profile, aid, original).model_dump(mode="json")
    task_id = str(uuid4())
    ref = reference("alert_material", original["id"], "source_label", BACKEND + ".lake_database")
    raw["tasks"][task_id] = {"task_id": task_id, "usable_feedback": True, "limitations": [],
        "revision": {"result_text": uuid4().hex, "result_scope": copy.deepcopy(raw["scope"]),
            "result_source_refs": [ref]}}
    raw["citation_roles"][f"$.tasks.{task_id}.revision"] = "human_statement"
    frozen = Context.model_validate(raw)
    base = case_model_boundary.build(frozen, uuid4(), [], [], {aid: original})
    assert base["ready"]
    saved = tmp_path / "generated-human-input.json"
    saved.write_bytes(encoded(base))
    base = json.loads(saved.read_bytes())
    final = case_followup_input.build("C6", frozen, base, {})
    assert final["ready"]
    for view in (base, final):
        source = next(row for row in view["source_map"].values() if row["ref"] == ref)
        assert source["alert_ids"] == [aid]
        assert original["raw_json"]["field_metadata"]["lake_ingress"]["lake_database"] in "\n".join(
            message["content"] for message in view["messages"])
    assert encoded(original) == before


@pytest.mark.parametrize(("key", "paths"), [
    ("material_backend_paths", ["$.raw_json.field_metadata.*"]),
    ("material_backend_reference_paths", ["$.raw_json.field_metadata"])])
def test_profile_rejects_ambiguous_paths_and_unconfigured_reference_protection(profile, monkeypatch, key, paths):
    config = profile.config
    config["c3_input_selection"][key] = paths
    path = Path(runtime_policy.__file__).with_name("case-input-v1.json")
    read = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda file: encoded(config) if file == path else read(file))
    with pytest.raises(ValueError, match="case_material_backend_paths_invalid"):
        runtime_policy.load_case_profile({"profile": path.name})
