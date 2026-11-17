"""Compare task-selected frozen previews with originals; no external calls."""
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
REF_KEYS = {"source_refs", "result_source_refs", "support_ids", "counter_ids", "evidence_ids", "source_ids"}


def read(path):
    return json.loads(path.read_text())


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def canonical(value, sources):
    if isinstance(value, dict):
        return {k: [sources[s]["ref"] for s in child] if k in REF_KEYS else canonical(child, sources)
                for k, child in value.items()}
    if isinstance(value, list):
        return [canonical(child, sources) for child in value]
    return value


originals = read(HERE / "original-files-before.json")
assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha for path, sha in originals.items())
summary = []
for stage in ("C3", "C6"):
    before = read(HERE / f"before/{stage}-selection.json")
    after = read(HERE / f"after/{stage}-selection.json")
    old = {encoded(r["ref"]): r for r in before["records"]}
    new = {encoded(r["ref"]): r for r in after["records"]}
    assert set(new) <= set(old)
    for key, row in new.items():
        original = old[key]
        for field in ("ref", "alert_ids", "original_scope", "membership_basis", "record_alert_ids"):
            assert row.get(field) == original.get(field), (stage, field, row["id"])
        if "original_value" in row:
            assert row["original_value"] == original["original_value"]
    materials = {key: r for key, r in old.items() if r.get("business_block", r["block"]) == "material"}
    assert all(key in new and new[key]["value"] == row["value"] for key, row in materials.items())
    for key, row in new.items():
        if row["ref"]["role"] == "human_statement":
            assert canonical(row["value"], after["source_map"]) == canonical(old[key]["value"], before["source_map"])
        if row.get("knowledge"):
            assert row["value"] == old[key]["value"] and row["knowledge"] == old[key]["knowledge"]
    if stage == "C3":
        assert len(set(old) - set(new)) == 2
        assert {r["block"] for key, r in old.items() if key not in new} == {"incident", "background"}
        assert all(key in new for key, r in old.items() if r["block"] in {"finding", "question", "triage"})
    else:
        prior = next(r for r in after["records"] if r["block"] == "C3")
        old_prior = next(r for r in before["records"] if r["block"] == "C3")
        assert set(prior["value"]) == set(old_prior["value"]) - {"domains", "members"}
        for field, value in prior["value"].items():
            assert canonical(value, after["source_map"]) == canonical(old_prior["value"][field], before["source_map"]), field
        assert len([r for r in after["records"] if r["block"] == "graph"]) == 1
        assert not any(r["value"].get("relation") == "source_reports_object" for r in after["records"] if r["block"] == "graph")
    body = (HERE / f"after/{stage}-model-input.txt").read_text()
    assert read(HERE / f"after/{stage}-request-preview.json")["messages"][1]["content"] == body
    # Program facts must not resurrect administrative fields removed from alert rows.
    heading = "[补充业务事实｜程序提供]" if stage == "C3" else "[必要程序事实]"
    fact_block = body.split(heading, 1)[1].split("\n[", 1)[0]
    assert "上游厂商" not in fact_block and "来源域" not in fact_block
    summary.append({"stage": stage, "before_characters": len((HERE / f"before/{stage}-model-input.txt").read_text()),
        "after_characters": len(body), "before_sources": len(old), "after_sources": len(new),
        "member_material_fields_unchanged": len(materials),
        "removed_records": [{"ref": r["ref"], "block": r["block"], "value": r["value"]} for key, r in old.items() if key not in new],
        "new_selection_reasons": dict(Counter(o["reason"] for o in after["omissions"]) - Counter(o["reason"] for o in before["omissions"]))})
result = {"status": "passed", "kind": "offline_same_frozen_material_selection_not_new_generation",
          "original_files_unchanged": len(originals), "real_model_calls": 0, "database_calls": 0, "network_calls": 0,
          "prose_and_scope_preserved": True, "selected_C3_dependencies_preserved_in_C6": True,
          "program_fact_backfill_checked": True, "stages": summary,
          "quality": "NOT_PASSED_UNCHANGED_OLD_REPLIES", "no_new_Result_or_adoption": True}
body = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
target = HERE / "verification.json"
if target.exists():
    assert target.read_text() == body
else:
    target.write_text(body)
print(json.dumps({"status": result["status"], "original_files_unchanged": len(originals),
                  "stages": [{k: v for k, v in row.items() if k != "removed_records"} for row in summary]}, ensure_ascii=False))
