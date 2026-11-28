"""Generated local structures only; no stored materials or model/network calls."""
import copy
import json
from uuid import uuid4

import pytest
from app.socai2 import case_followup_input, case_model_boundary, runtime_policy
from app.socai2.baseline_context import reference
from app.socai2.baseline_contracts import Question
from app.socai2.baseline_store import digest, encoded
from app.socai2.case_c3_input_selection import (
    UNMAPPED_REASON,
    select_rows,
    unmapped_material,
)
from app.socai2.case_program_output import restore_observed
from test_socai2_case_material_mirrors import context, entries, material
from test_socai2_case_material_mirrors import (
    profile as profile,  # noqa: PLC0414 -- shared pytest fixture
)

ROOTS = ("$.ocsf_json", "$.raw_json.raw_event.ocsf_event")


def generated(*, dotted=False):
    aid, original = material()
    kept, hidden, sibling = (uuid4().hex for _ in range(3))
    doc = {"mapped_fact": kept, "process": {"name": kept}, "zero": 0, "disabled": False, "empty": [],
           "unknown_extension": {"unmapped": sibling}, "unmapped": {"observation": hidden}}
    if dotted:
        doc["unknown.business"] = sibling
    else:
        # A raw_data key in a whole, unaddressable parent triggers the existing
        # original guard. Keep that independent check out of this representative.
        doc["raw_data"] = json.dumps(doc["unmapped"])
    original["ocsf_json"] = copy.deepcopy(doc)
    original["raw_json"]["raw_event"]["ocsf_event"] = copy.deepcopy(doc)
    original["raw_json"]["raw_event"]["source_ocsf_json"] = json.dumps(doc, indent=2)
    original["raw_text"] = json.dumps(doc)
    return aid, original, kept, hidden, sibling


@pytest.mark.parametrize("dotted", [False, True])
def test_selected_input_survives_json_and_all_case_stages(profile, tmp_path, dotted):
    aid, original, kept, hidden, sibling = generated(dotted=dotted)
    before = encoded(original)
    frozen = context(profile, aid, original)
    question = Question(id="detection_facts", text=uuid4().hex, scope=frozen.scope,
                        evidence_requirements=[], state="open", answer=None, evidence_refs=[], limitations=[])
    frozen = frozen.model_copy(update={"questions": [question]})
    base = case_model_boundary.build(frozen, uuid4(), [], [], {aid: original})
    assert base["ready"]
    saved = tmp_path / "generated-input.json"
    saved.write_bytes(encoded(base))
    restored = json.loads(saved.read_bytes())
    observation = next(r for r in restored["input_ledger"]["records"] if r["ref"]["type"] == "alert_material"
                       and r["ref"]["source_path"] == ("$.raw_text" if dotted else ROOTS[0] + ".process.name"))
    assert observation["ref"]["role"] == "observation"
    if dotted:
        assert hidden in observation["original_value"]
    assembled = {"findings": [{"state": "observed", "support_ids": [observation["id"]]}]}
    restore_observed(assembled, restored["case_boundary"])
    statement = assembled["findings"][0]["statement"]
    assert hidden not in statement and kept in statement
    prior = {"validation": "structure_scope_sources_checked", "source_map": restored["source_map"],
             "analysis": {"summary": uuid4().hex, "findings": [{"state": "observed", "statement": statement,
                 "support_ids": [observation["id"]], "alert_ids": [aid]}],
                 "questions": [{"id": question.id, "state": "unresolved", "source_ids": [observation["id"]]}],
                 "followups": []}}
    views = [restored, *[case_followup_input.build(stage, frozen, restored, {},
        previous=prior, prior_id=str(uuid4()), question_id=question.id if stage == "Deep" else None)
        for stage in ("Deep", "C6")]]
    for view in views:
        assert view["ready"]
        prompt = "\n".join(m["content"] for m in view["messages"])
        assert hidden not in prompt and kept in prompt and sibling in prompt
        records = view.get("input_ledger", view.get("followup_boundary"))["records"]
        for row in records:
            assert view["source_map"][row["id"]]["visible_value_sha256"] == digest(row["value"])
        materials = [r for r in records if r["ref"]["type"] == "alert_material"]
        assert materials and all(r["alert_ids"] == [aid] for r in materials)
        if dotted:
            parents = [r for r in materials if r["ref"]["source_path"] in ROOTS]
            assert parents and all("unmapped" not in r["value"] and "raw_data" not in r["value"] for r in parents)
            assert all(r["value"]["zero"] == 0 and r["value"]["disabled"] is False
                       and r["value"]["empty"] == [] for r in parents)
        else:
            assert any(r["ref"]["source_path"].endswith(".zero") and r["value"] == 0 for r in materials)
            assert any(r["ref"]["source_path"].endswith(".disabled") and r["value"] is False for r in materials)
            assert any(r["ref"]["source_path"].endswith(".empty") and r["value"] == [] for r in materials)
    assert encoded(original) == before
    assert any(o["reason"] == UNMAPPED_REASON for o in base["omissions"])


def test_only_proven_fixed_wrappers_are_projected(profile):
    _aid, original, kept, _hidden, sibling = generated()
    before = encoded(original)
    selected = unmapped_material(original, profile.config["c3_input_selection"], [])
    for path in (selected["raw_text"], selected["raw_json"]["raw_event"]["source_ocsf_json"]):
        doc = json.loads(path)
        assert "unmapped" not in doc and "raw_data" not in doc
        assert doc["mapped_fact"] == kept and doc["unknown_extension"]["unmapped"] == sibling
    assert encoded(original) == before
    unrelated = json.dumps({"unmapped": {"observation": uuid4().hex}, "unique": uuid4().hex})
    original["raw_text"] = unrelated
    original["ocsf_json"]["raw_data"] = "{"
    original["raw_json"]["raw_event"]["source_ocsf_json"] = "{"
    original["raw_json"]["unmapped"] = {"observation": sibling}
    selected = unmapped_material(original, profile.config["c3_input_selection"], [])
    assert selected["raw_text"] == unrelated
    assert selected["ocsf_json"]["raw_data"] == "{"
    assert selected["raw_json"]["raw_event"]["source_ocsf_json"] == "{"
    assert selected["raw_json"]["unmapped"] == original["raw_json"]["unmapped"]


def test_required_refs_and_frozen_artifacts_cannot_restore_unmapped(profile, tmp_path):
    aid, original, _kept, hidden, _sibling = generated()
    frozen = context(profile, aid, original)
    cid = str(uuid4())
    base = case_model_boundary.build(frozen, cid, [], [], {aid: original})
    assert base["ready"]
    saved = tmp_path / "generated-input.json"
    saved.write_bytes(encoded(base))
    base = json.loads(saved.read_bytes())
    paths = [ROOTS[0] + ".unmapped.observation", ROOTS[1] + ".unmapped", "$.raw_text"]
    refs = [reference("alert_material", original["id"], "observation", p) for p in paths]
    rows, omissions = entries(profile, aid, original)
    # Explicit references to descendants and their ancestors never exempt the
    # unmapped boundary, even when the selector receives an unselected row.
    rows.append({"id": "excluded", "ref": refs[0], "alert_ids": [aid], "block": "material",
                 "value": hidden, "original_value": hidden})
    required = [*refs, reference("alert_material", original["id"], "observation", ROOTS[0])]
    selected = select_rows(rows, frozen.model_dump(mode="json"), profile.config, profile.business["render"],
                           omissions, required_refs=required)
    assert not any(r["id"] == "excluded" for r in selected)
    assert hidden not in json.dumps([r["value"] for r in selected])
    fid = str(uuid4())
    fields = [{"name": uuid4().hex, "source_path": p, "value": hidden if i < 2 else original["raw_text"],
               "transform": "identity", "conflict": False} for i, p in enumerate(paths)]
    artifact = {"schema_version": case_followup_input.EVIDENCE_SCHEMA,
                "content_json": {"type": "materials", "members": {
                    aid: {"material_id": original["id"], "fields": fields}}}}
    payload = frozen.model_dump(mode="json")
    c1path = f"$.alerts.{aid}.material.ocsf_json.unmapped.observation"
    payload["alerts"][aid]["material"]["ocsf_json"] = original["ocsf_json"]
    payload["citation_roles"][c1path] = "observation"
    parent_id = str(uuid4())
    artifacts = {fid: artifact, cid: {"schema_version": "socai2.baseline-context.v1", "content_json": payload},
        parent_id: {"schema_version": "socai2.baseline-context.v1", "content_json": frozen.model_dump(mode="json")}}
    registry = case_followup_input.Sources(frozen, base, artifacts, [])
    source_refs = [*refs, reference("artifact", cid, "observation", c1path),
                  *[reference("artifact", fid, "observation", f"$.members.{aid}.fields.{i}") for i in range(len(fields))]]
    mapping = {str(i): {"ref": ref, "alert_ids": [aid]} for i, ref in enumerate(source_refs)}
    # raw_text can remain as a safely projected base source. Its value must stay
    # projected; direct unmapped and original C1/C4 dependencies are unavailable.
    rebound = registry.rebind({"support_ids": list(mapping)}, mapping, str(uuid4()))
    assert rebound["unavailable_prior_reference_count"] >= len(source_refs) - 1
    assert hidden not in json.dumps([r["value"] for r in registry.rows])
    parent = reference("artifact", parent_id, "source_label", f"$.alerts.{aid}.material")
    assert registry.resolve({"ref": parent, "alert_ids": [aid]})
    assert hidden not in json.dumps([r["value"] for r in registry.rows])


def test_unmapped_policy_rejects_ambiguous_or_unbound_paths(profile):
    policy = copy.deepcopy(profile.config["c3_input_selection"])
    policy["material_unmapped_paths"] = ["$.ocsf_json.*.unmapped"]
    with pytest.raises(ValueError, match="case_material_unmapped_paths_invalid"):
        runtime_policy.validate_material_unmapped_paths(policy)
    policy["material_unmapped_paths"] = []
    with pytest.raises(ValueError, match="case_material_unmapped_paths_invalid"):
        runtime_policy.validate_material_unmapped_paths(policy)
