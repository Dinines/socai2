"""Check saved previews and extract their exact H/comparison/plan passages."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
config = json.loads((HERE / "config.json").read_text())


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    content = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        assert path.read_text() == content, "immutable_evidence_changed: " + str(path)
    else:
        path.write_text(content)


snapshot = ROOT / config["snapshot"]
db = read(snapshot)
artifacts = {a["id"]: a for a in db["artifacts"] if a["run_id"] == config["run_id"]}
context = next(a["content_json"] for a in artifacts.values() if a["schema_version"] == "socai2.baseline-context.v1")
task = next(iter(context["tasks"].values()))["revision"]
before, after = [read(HERE / name / "summary.json") for name in ("before", "after")]
assert sha(snapshot) == before["snapshot_sha256"] == after["snapshot_sha256"]
dispatch = next(a["content_json"] for a in artifacts.values()
                if (a["content_json"] or {}).get("type") == "followup_dispatch")
initial = artifacts[dispatch["initial_analysis_artifact_id"]]["content_json"]
outcomes = []
for stage in ("C3", "C6"):
    old, new = [read(HERE / name / (stage + "-selection.json")) for name in ("before", "after")]
    assert old["source_map"].keys() == new["source_map"].keys()
    for sid, source in old["source_map"].items():
        assert all(new["source_map"][sid][key] == source[key] for key in ("ref", "alert_ids"))
    previous = {r["id"]: r for r in old["records"]}
    for row in new["records"]:
        if not row.get("context_kind"):
            assert row["value"] == previous[row["id"]]["value"], (stage, row["id"])
    h = next(r for r in new["records"] if r.get("context_identity") == task["id"])
    assert h["value"]["result_text"] == task["result_text"] and h["original_scope"] == task["result_scope"]
    assert h["value"]["revision"] == task["revision"] and h["ref"]["role"] == "human_statement"
    refs = h["value"]["source_refs"]
    assert len(refs) == len(set(refs)) == 53 and h["value"]["unavailable_prior_reference_count"] == 7
    original_materials = {r["id"] for r in task["source_refs"] if r["type"] == "alert_material"}
    assert {new["source_map"][s]["ref"]["id"] for s in refs} == original_materials
    assert all(new["source_map"][s]["ref"]["role"] == "observation" for s in refs)
    prior = next(r for r in new["records"] if r.get("context_kind") == "prior_result")
    assert prior["value"]["conclusion_state"] == "unavailable" and "conclusion" not in prior["value"]
    text = (HERE / "after" / (stage + "-model-input.txt")).read_text()
    chosen = {r["id"] for r in new["records"] if r.get("context_kind") or r["block"] == "plan"}
    passages, copying = [], False
    for line in text.splitlines():
        if line.startswith("["):
            citation = re.match(r"^\[([^\]]+)\]", line)
            ids = set(citation.group(1).split(",")) if citation else set()
            copying = bool(ids & chosen) or line == "[本次比较条件]"
        if copying:
            passages.append(line)
    if stage == "C6":
        assert after["comparison"]["state"] == "unavailable"
        assert len(initial["analysis"]["followups"]) == 1
        plan = next(r for r in new["records"] if r["block"] == "plan")
        original = initial["analysis"]["followups"][0]
        assert plan["ref"]["id"] == dispatch["initial_analysis_artifact_id"]
        assert all(plan["value"]["followup"][key] == original[key] for key in ("objective", "required_evidence", "question_id"))
        assert text.count(original["objective"]) == 1
        assert not {"mode", "priority", "binding_id"} & plan["value"]["followup"].keys()
        assert "execution_plan_index" not in plan["value"]
        for old_id, new_id in zip(original["source_ids"], plan["value"]["followup"]["source_ids"], strict=True):
            assert initial["source_map"][old_id]["ref"] == new["source_map"][new_id]["ref"]
    save(HERE / "after" / (stage + "-H-comparison-plan.txt"), "\n".join(passages) + "\n")
    outcomes.append({"stage": stage, "before_characters": next(s["characters"] for s in before["stages"] if s["stage"] == stage),
        "after_characters": len(text), "sources_unchanged": len(new["source_map"]), "original_refs_and_scopes_unchanged": True,
        "other_business_values_unchanged": True, "H_text_and_scope_unchanged": True,
        "H_attachments": len(task["source_refs"]), "visible_material_attachments": len(original_materials),
        "visible_material_fields": len(refs), "unavailable_attachments": 7,
        "selected_historical_conclusion": "unavailable_preserved"})
sources = [ROOT / "services/api/app/socai2" / name for name in (
    "case_context_input.py", "case_model_boundary.py", "case_input_text.py", "case_c3_input_selection.py",
    "case_followup_input.py", "case-input-v1.json")]
sources += [ROOT / "services/api/tests/test_socai2_case_followup_boundary.py", HERE / "rebuild.py", Path(__file__),
            HERE / "config.json", ROOT / config["policy"]]
save(HERE / "verification.json", {"status": "passed", "kind": "offline_saved_input_projection", "outcomes": outcomes,
    "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sources},
    "snapshot_sha256": sha(snapshot), "real_model_calls": 0, "database_calls": 0, "network_calls": 0,
    "quality": "NOT_EVALUATED; prior answers and failures unchanged"})
print(json.dumps(outcomes, ensure_ascii=False))
