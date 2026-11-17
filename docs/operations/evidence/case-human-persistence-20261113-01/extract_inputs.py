"""Export the exact stored substitute requests and their H/plan reference bindings."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
snapshot = HERE / "pg-02/database.json"
original_hash = hashlib.sha256(snapshot.read_bytes()).hexdigest()
data = json.loads(snapshot.read_text())
artifacts = {r["id"]: r for r in data["artifacts"]}
steps = {r["id"]: r for r in data["run_steps"]}
run = next(r for r in data["runs"] if r.get("comparison_result_id"))
current = [a for a in data["artifacts"] if a["run_id"] == run["id"]]
base = next(a["content_json"] for a in current if "input_ledger" in (a["content_json"] or {}))
context = next(a["content_json"] for a in current if a["schema_version"] == "socai2.baseline-context.v1")
h = next(iter(context["tasks"].values()))["revision"]
dispatch = next(a["content_json"] for a in current if (a["content_json"] or {}).get("type") == "followup_dispatch")
initial = artifacts[dispatch["initial_analysis_artifact_id"]]["content_json"]
folder = HERE / "inputs"
folder.mkdir(exist_ok=True)


def save(name, value):
    body = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with (folder / name).open("x") as file:
        file.write(body)


counts, outcomes = Counter(), []
for artifact in sorted(current, key=lambda a: a["captured_at"]):
    if artifact["kind"] != "model_request":
        continue
    payload = artifact["content_json"]["payload"]
    stage = {"C3": "C3", "C4.deep": "Deep", "C6": "C6"}[steps[artifact["step_id"]]["stage_code"]]
    counts[stage] += 1
    name = stage + (f"-{counts[stage]:02}" if stage == "Deep" else "")
    body = payload["body"]["messages"][1]["content"]
    rows = payload.get("followup_boundary", base["input_ledger"])["records"]
    human = next(r for r in rows if r.get("context_kind") == "human_feedback")
    assert human["value"]["result_text"] == h["result_text"] and body.count(h["result_text"]) == 1
    assert human["value"]["revision"] == h["revision"] == 2
    assert human["original_scope"] == h["result_scope"]
    resolved = [payload["source_map"][sid]["ref"] for sid in human["value"]["source_refs"]]
    assert {r["id"] for r in resolved} == {r["id"] for r in h["source_refs"]}
    assert all(r["role"] == "observation" and r["type"] == "alert_material" for r in resolved)
    save(name + "-request.json", payload["body"])
    save(name + "-model-input.txt", body)
    if stage in {"C3", "C6"}:
        chosen = {r["id"] for r in rows if r.get("context_kind") or r["block"] == "plan"}
        passages, copying = [], False
        for line in body.splitlines():
            if line.startswith("["):
                match = re.match(r"^\[([^\]]+)\]", line)
                copying = bool(match and set(match.group(1).split(",")) & chosen) or line == "[本次比较条件]"
            if copying:
                passages.append(line)
        save(name + "-H-comparison-plan.txt", "\n".join(passages) + "\n")
        save(name + "-selection.json", {"records": [r for r in rows if r["id"] in chosen],
            "source_map": payload["source_map"]})
    if stage == "C6":
        plans = [r for r in rows if r["block"] == "plan"]
        assert len(plans) == len(initial["analysis"]["followups"]) == 1
        plan, original = plans[0], initial["analysis"]["followups"][0]
        assert plan["ref"]["id"] == dispatch["initial_analysis_artifact_id"]
        assert all(plan["value"]["followup"][k] == original[k] for k in ("objective", "required_evidence", "question_id"))
        assert body.count(original["objective"]) == 1
        for old, new in zip(original["source_ids"], plan["value"]["followup"]["source_ids"], strict=True):
            assert initial["source_map"][old]["ref"] == payload["source_map"][new]["ref"]
        comparison = payload["followup_boundary"]["program_metadata"]["comparison"]
        assert comparison["state"] == "eligible" and comparison["result_id"] == run["comparison_result_id"]
    outcomes.append({"stage": name, "request_artifact_id": artifact["id"], "characters": len(body),
        "source_count": len(payload["source_map"]), "human_source_id": human["id"],
        "human_revision": h["revision"], "visible_attachment_fields": len(resolved),
        "body_sha256": hashlib.sha256(body.encode()).hexdigest()})
assert counts == {"C3": 1, "Deep": 2, "C6": 1}
assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == original_hash
save("summary.json", {"kind": "exact_stored_substitute_requests", "case_id": run["case_id"],
    "run_id": run["id"], "real_model_calls": 0, "database_calls": 0,
    "snapshot_sha256": original_hash, "human_revision_id": h["id"], "comparison_result_id": run["comparison_result_id"],
    "original_plan_artifact_id": dispatch["initial_analysis_artifact_id"],
    "H_scope_and_text_preserved": True, "original_plan_and_refs_preserved": True, "inputs": outcomes})
print(json.dumps(outcomes, ensure_ascii=False))
