"""Offline comparison of the one real Run; does not alter original summaries."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def read(path):
    return json.loads(path.read_text())


folder = HERE / "flow/R01"
summary, db = read(folder / "summary.json"), read(folder / "export/database.json")
artifacts = {a["id"]: a for a in db["artifacts"] if a["run_id"] == summary["run_id"]}
c2 = next(a["content_json"] for a in artifacts.values() if a["schema_version"] == "socai2.baseline-enrichment.v1"
          and a["kind"] == "source_snapshot")
knowledge = next(s for s in c2["sources"] if s["source"] == "knowledge")
assert knowledge["outcome"] == "data" and knowledge["returned_rows"] == 2
assert all(c["http_status"] == 200 for c in knowledge["source_metadata"]["calls"])
answers = [read(folder / f"calls/call-{n}-receipt.json")["raw"]["choices"][0]["message"]["content"] for n in (1, 2, 3)]
values = [json.loads(a) for a in answers]


def refs(value):
    result = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"support_ids", "counter_ids", "evidence_ids", "source_ids"}:
                result.extend(child)
            else:
                result.extend(refs(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(refs(child))
    return result


def differences(left, right, path=()):
    if left == right:
        return []
    if isinstance(left, dict) and isinstance(right, dict) and left.keys() == right.keys():
        return [p for key in left for p in differences(left[key], right[key], (*path, key))]
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        return [p for index, (a, b) in enumerate(zip(left, right, strict=True))
                for p in differences(a, b, (*path, index))]
    return [list(path)]


changed = differences(values[1], values[2])
assert changed == [["analysis", "questions", 4, "answer"], ["impact", "alert_ids"]]
calls = []
for call, value in zip(summary["calls"], values, strict=True):
    payload = artifacts[call["request_artifact_id"]]["content_json"]["payload"]
    records = payload.get("followup_boundary", {}).get("records")
    if records is None:
        records = next(a["content_json"]["input_ledger"]["records"] for a in artifacts.values()
            if a["schema_version"] == "socai2.case-model-input.v1")
    card = next(r for r in records if r.get("knowledge", {}).get("part") == "card")
    content = card["value"]["record"]["content"]
    assert len(content) == 448 and payload["body"]["messages"][1]["content"].count(content) == 1
    used = sorted(set(refs(value)) & set(call["knowledge_source_ids"]))
    calls.append({"stage": call["stage"], "number": call["number"], "validation_error": call["validation_error"],
        "knowledge_source_ids": call["knowledge_source_ids"], "knowledge_cited_ids": used,
        "knowledge_characters": len(content), "knowledge_body_occurrences": 1})
old = read(HERE / "flow/plan.json")["original_flow_sha256"]
assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == value for p, value in old.items())
result = {"real_generation_calls": 3, "real_embedding_calls": 1, "known_usage": summary["known_usage"], "cost": None,
    "result": summary["results"][0], "current_assessment_id": summary["current_assessment"]["value"]["id"],
    "calls": calls, "knowledge_receipt": knowledge, "correction_changed_fields": changed,
    "impact_members_before": values[1]["impact"]["alert_ids"], "impact_members_after": values[2]["impact"]["alert_ids"],
    "correction_characters": len(read(folder / "calls/call-3-intent.json")["body"]["messages"][-1]["content"]),
    "Deep": "not_dispatched_no_followups_requested", "old_06_flow_files_unchanged": len(old),
    "requests_answers_and_GETs_equal_database": True, "quality": "NOT_PASSED",
    "quality_findings": [
        {"path": ["conclusion", "text"], "issue": "Names and command type still used to infer automation."},
        {"path": ["conclusion", "limitations"], "issue": "Threat intelligence is not_attempted_budget but described as no results."},
        {"path": ["comparison", "summary"], "issue": "not_comparable summary claims agreement with current intermediate judgments."}],
    "comparison_fix": "../case-fixed-comparison-20261113-01/README.md",
    "limits": ["single_new_run_not_controlled_AB", "original_AI_and_H_reused", "synthetic_materials_no_accuracy_claim",
               "accepted_is_structure_and_reference_acceptance_not_prose_truth", "no_new_sampling_after_this_run"]}
body = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
target = HERE / "review.json"
if target.exists():
    assert target.read_text() == body
else:
    target.write_text(body)
print(json.dumps({"calls": calls, "changed": changed, "quality": result["quality"]}, ensure_ascii=False))
