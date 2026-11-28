"""Case mirror selection with generated structures only; no stored run samples."""
import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from app.socai2 import (
    case_followup_input,
    case_followup_selection,
    case_model_boundary,
    runtime_policy,
)
from app.socai2.baseline_context import Context, reference
from app.socai2.baseline_store import encoded
from app.socai2.case_c3_input_selection import select_rows
from app.socai2.case_input_text import material_entries

SOURCE = "$.raw_json.raw_event.source_ocsf_json"
OBJECT = "$.raw_json.raw_event.ocsf_event"
ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def profile(monkeypatch):
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(
        ROOT / "deploy/local-investigation/investigation-policy-case-v1.toml"))
    runtime_policy.active_policy.cache_clear()
    yield runtime_policy.active_policy().case_io
    runtime_policy.active_policy.cache_clear()


def material():
    aid = str(uuid4())
    document = {"tenant_uid": str(uuid4()), "process": {"name": uuid4().hex},
        "business_extension": {"extension": uuid4().hex, "enabled": False, "count": 0, "empty": []},
        "file": [{"name": uuid4().hex}, {"name": uuid4().hex}]}
    return aid, {"id": str(uuid4()), "alert_id": aid, "material_state": "complete",
        "raw_text": None, "ocsf_json": None, "detection": {}, "enrichment": {}, "source_scope": {},
        "raw_json": {"id": aid, "identity_version": "source-v1", "source": "lyc" + uuid4().hex,
            "tenant_id": str(uuid4()), "raw_event": {"ocsf_event": document,
                "source_ocsf_json": json.dumps(dict(reversed(list(document.items()))), indent=2)}}}


def entries(profile, aid, original, config=None):
    omissions = []
    rows = material_entries(aid, original, profile.business, omissions, profile.config if config is None else config)
    for index, row in enumerate(rows):
        row["id"] = f"S{index + 1}"
    return rows, omissions


def select(profile, rows, aid, omissions, required=()):
    return select_rows(rows, {"alerts": {aid: {"alert": {}}}}, profile.config,
                       profile.business["render"], omissions, required_refs=required)


def mirror(rows):
    return next((row for row in rows if row["ref"]["source_path"] == SOURCE), None)


def test_whole_mirror_is_omitted_without_reintroducing_metadata_or_changing_sources(profile):
    aid, original = material()
    before = encoded(original)
    rows, omissions = entries(profile, aid, original)
    without_mirrors = profile.config
    without_mirrors["c3_input_selection"]["material_mirrors"] = []
    baseline, _ = entries(profile, aid, original, without_mirrors)
    expected = [row for row in select(profile, baseline, aid, []) if row["ref"]["source_path"] != SOURCE]
    selected = select(profile, rows, aid, omissions)
    assert mirror(selected) is None
    assert selected == expected
    assert encoded(original) == before
    assert all(row["alert_ids"] == [aid] for row in selected)
    assert all(row["ref"]["source_path"] != OBJECT + ".tenant_uid" for row in selected)
    assert any(row["ref"]["source_path"] == OBJECT + ".business_extension.count" and type(row["value"]) is int
               and row["value"] == 0 for row in selected)
    assert any(row["ref"]["source_path"] == OBJECT + ".business_extension.enabled" and row["value"] is False
               for row in selected)
    assert any(row["ref"]["source_path"] == OBJECT + ".business_extension.empty" and row["value"] == [] for row in selected)
    omitted = next(row for row in omissions if row["reason"] == "same_material_serialized_mirror")
    assert omitted["ref"] == reference("alert_material", original["id"], "source_label", SOURCE)
    assert omitted["equivalent_ref"] == reference("alert_material", original["id"], "source_label", OBJECT)
    assert omitted["alert_ids"] == [aid]


@pytest.mark.parametrize("change", ["extra", "missing", "value", "bool_int", "int_float", "array_order",
    "invalid", "nested_duplicate", "overflow", "scalar"])
def test_different_or_unparseable_mirrors_keep_exact_original_text_and_role(profile, change):
    aid, original = material()
    event = original["raw_json"]["raw_event"]
    value = copy.deepcopy(event["ocsf_event"])
    if change == "extra":
        value["unknown_business_field"] = uuid4().hex
    elif change == "missing":
        value.pop("process")
    elif change == "value":
        value["process"]["name"] = uuid4().hex
    elif change == "bool_int":
        value["business_extension"]["enabled"] = 0
    elif change == "int_float":
        value["business_extension"]["count"] = 0.0
    elif change == "array_order":
        value["file"].reverse()
    text = json.dumps(value)
    if change == "invalid":
        text = text[:-1]
    elif change == "nested_duplicate":
        repeated = json.dumps(value["process"]["name"])
        text = text.replace(json.dumps(value["process"]), '{"name":' + repeated + ',"name":' + repeated + '}')
    elif change == "overflow":
        text = text.replace('"count": 0', '"count": 1e9999')
    elif change == "scalar":
        text = json.dumps(uuid4().hex)
    event["source_ocsf_json"] = text
    before = encoded(original)
    rows, omissions = entries(profile, aid, original)
    selected = select(profile, rows, aid, omissions)
    row = mirror(selected)
    assert row["value"] == row["original_value"] == text
    assert row["ref"] == reference("alert_material", original["id"], "source_label", SOURCE)
    assert row["alert_ids"] == [aid]
    assert encoded(original) == before
    assert not any(item["reason"] == "same_material_serialized_mirror" for item in omissions)


@pytest.mark.parametrize("missing", ["envelope", "object", "rule"])
def test_mirror_requires_recognized_wrapper_same_material_object_and_explicit_rule(profile, missing):
    aid, original = material()
    config = profile.config
    if missing == "envelope":
        original["raw_json"].pop("identity_version")
    elif missing == "object":
        original["raw_json"]["raw_event"].pop("ocsf_event")
    else:
        config["c3_input_selection"]["material_mirrors"] = []
    rows = material_entries(aid, original, profile.business, [], config)
    for index, row in enumerate(rows):
        row["id"] = f"S{index + 1}"
    assert mirror(select(profile, rows, aid, []))["value"] == original["raw_json"]["raw_event"]["source_ocsf_json"]


@pytest.mark.parametrize(("path", "dependency"), [
    (SOURCE, "required"), (None, "human"), ("$.raw_json.raw_event", "prior"), (SOURCE + ".nested", "required")])
def test_exact_and_ancestor_dependencies_keep_mirror(profile, path, dependency):
    aid, original = material()
    rows, omissions = entries(profile, aid, original)
    ref = reference("alert_material", original["id"], "source_label", path)
    required = [ref] if dependency == "required" else []
    if dependency != "required":
        value = {"source_refs": [ref]}
        rows.append({"id": "prior", "ref": reference("artifact", str(uuid4()), "prior_analysis"),
            "alert_ids": [aid], "value": copy.deepcopy(value), "original_value": value,
            "block": "triage" if dependency == "prior" else "background",
            **({"context_kind": "human_feedback"} if dependency == "human" else {})})
    row = mirror(select(profile, rows, aid, omissions, required))
    assert row["value"] == row["original_value"] == original["raw_json"]["raw_event"]["source_ocsf_json"]
    assert row["ref"]["role"] == "source_label"


def test_other_material_cannot_supply_equivalence_or_reference_dependency(profile):
    aid, original = material()
    other_aid, other = material()
    original["raw_json"]["raw_event"]["source_ocsf_json"] = other["raw_json"]["raw_event"]["source_ocsf_json"]
    rows, omissions = entries(profile, aid, original)
    extra, _ = entries(profile, other_aid, other)
    for row in extra:
        row["id"] += "other"
    selected = select(profile, rows + extra, aid, omissions)
    mirrors = [row for row in selected if row["ref"]["source_path"] == SOURCE]
    assert len(mirrors) == 1
    assert mirrors[0]["ref"]["id"] == original["id"]
    assert mirrors[0]["alert_ids"] == [aid]


def test_unrelated_material_reference_does_not_keep_equivalent_mirror(profile):
    aid, original = material()
    rows, omissions = entries(profile, aid, original)
    selected = select(profile, rows, aid, omissions,
        [reference("alert_material", str(uuid4()), "source_label", SOURCE)])
    assert mirror(selected) is None


def context(profile, aid, original):
    case_id = uuid4()
    return Context(schema_version="socai2.baseline-context.v1", case_id=case_id,
        captured_at=datetime.now(UTC), scope={"kind": "whole_case", "alert_ids": [aid], "object_keys": [],
            "window_start": None, "window_end": None, "limitations": []},
        case={"id": str(case_id), "title": uuid4().hex},
        alerts={aid: {"alert": {"id": aid, "title": uuid4().hex, "latest_material_id": original["id"]},
            "membership": {}, "material": {"id": original["id"], "material_state": "complete"},
            "source_refs": [], "objects": [], "triage": None, "feedback": None, "limitations": []}},
        incidents={}, tasks={}, current_assessment=None, assessment_members=[], assessment_sources=[],
        prior_results={}, adopted_task_revisions={}, adopted_artifacts={}, questions=[], omissions=[],
        citation_roles={"$.case": "source_label", f"$.alerts.{aid}.alert": "source_label",
            f"$.alerts.{aid}.material": "source_label"}, query_receipts_version="socai2.case-queries.v1",
        case_input_profile=profile.identity)


@pytest.mark.parametrize("with_prior", [False, True], ids=["without_prior", "with_prior"])
def test_c3_saved_input_and_c6_share_selection_preserving_sources(profile, tmp_path, with_prior):
    aid, original = material()
    frozen = context(profile, aid, original)
    before = encoded(original)
    base = case_model_boundary.build(frozen, uuid4(), [], [], {aid: original})
    assert base["ready"]
    assert mirror(base["input_ledger"]["records"]) is None
    saved = tmp_path / "generated-input.json"
    saved.write_bytes(encoded(base))
    base = json.loads(saved.read_bytes())
    assert all(src["ref"]["source_path"] != SOURCE for src in base["source_map"].values())
    retained = {sid: src for sid, src in base["source_map"].items() if src["ref"]["type"] == "alert_material"}
    observed = next(sid for sid, src in retained.items() if src["ref"]["role"] == "observation")
    previous = {"validation": "structure_scope_sources_checked", "source_map": base["source_map"],
        "analysis": {"summary": uuid4().hex, "findings": [{"support_ids": [observed]}],
            "questions": [], "followups": []}} if with_prior else None
    final = case_followup_input.build("C6", frozen, base, {}, previous=previous, prior_id=str(uuid4()))
    assert final["ready"]
    for src in retained.values():
        assert any(row == src for row in final["source_map"].values())
    assert all(src["ref"]["source_path"] != SOURCE for src in final["source_map"].values())
    for view in (base, final):
        prompt = "\n".join(message["content"] for message in view["messages"])
        assert "source_ocsf_json" not in prompt
        assert original["raw_json"]["raw_event"]["ocsf_event"]["tenant_uid"] not in prompt
        assert any(row["reason"] == "same_material_serialized_mirror" for row in view["omissions"])
    assert encoded(original) == before


def test_c6_explicit_dependency_keeps_frozen_mirror(profile):
    aid, original = material()
    frozen = context(profile, aid, original)
    rows, _ = entries(profile, aid, original)
    base = json.loads(encoded({"input_ledger": {"records": rows}}))
    ref = reference("alert_material", original["id"], "source_label", SOURCE)
    selected = case_followup_selection.records(base, frozen, profile.config, profile.business, [ref], [])
    assert mirror(selected)["ref"] == ref
    assert mirror(selected)["value"] == original["raw_json"]["raw_event"]["source_ocsf_json"]


@pytest.mark.parametrize("invalid", [None, {}, [{}], [{"source_path": SOURCE}],
    [{"source_path": SOURCE, "object_path": SOURCE}],
    [{"source_path": SOURCE, "object_path": "$.raw_json.raw_event.*"}],
    [{"source_path": SOURCE, "object_path": OBJECT}] * 2])
def test_profile_loader_rejects_invalid_mirror_policy(profile, monkeypatch, invalid):
    config = profile.config
    config["c3_input_selection"]["material_mirrors"] = invalid
    path = Path(runtime_policy.__file__).with_name("case-input-v1.json")
    read = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda file: encoded(config) if file == path else read(file))
    with pytest.raises(ValueError, match="case_material_mirrors_invalid"):
        runtime_policy.load_case_profile({"profile": path.name})
