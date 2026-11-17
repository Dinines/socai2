"""Compare the three saved scenarios and verify their actual replay plans offline."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    path = HERE / name
    body = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        assert path.read_text() == body, "saved_comparison_differs:" + str(path)
    else:
        with path.open("x") as file:
            file.write(body)


rows, plans = [], []
drivers = {"B01": "run-v1.py.txt", "H01": "run-v2.py.txt", "H02": "run-v3.py.txt"}
for key, driver in drivers.items():
    folder = HERE / "flow" / key
    summary = read(folder / "summary.json")
    intent = read(folder / "execute-intent.json")
    # B01 predates versioned plans; its saved hash still pins plan.json.
    plan_path = HERE / "flow" / intent.get("plan_file", "plan.json")
    assert sha(plan_path) == intent["plan_sha256"]
    plan = read(plan_path)
    plans.append(plan)
    driver_key = str((HERE / "run.py").relative_to(ROOT))
    assert sha(HERE / driver) == plan["source_sha256"][driver_key]
    assert summary["requests_and_raw_replies_equal_database"] and summary["result_H_and_current_GETs_equal_database"]
    db = read(folder / "export/database.json")
    snapshot = next(a for a in db["artifacts"] if a["run_id"] == summary["run_id"]
                    and a["kind"] == "source_snapshot" and a["schema_version"] == "socai2.baseline-enrichment.v1")
    sources = [{"source": s["source"], "outcome": s["outcome"], "reason": s["reason"],
                "returned_rows": s["returned_rows"], "source_metadata": s["source_metadata"]}
               for s in snapshot["content_json"]["sources"]]
    rows.append({**{k: summary[k] for k in ("scenario", "case_id", "run_id", "run_state", "stop_reason",
        "results", "current_assessment", "real_model_calls", "known_usage", "usage_unknown", "cost")},
        "actual_plan_file": str(plan_path.relative_to(HERE)), "actual_plan_sha256": intent["plan_sha256"],
        "driver_snapshot": driver, "summary_original_baseline_plan_sha256": summary["plan_sha256"],
        "calls": [{k: call[k] for k in ("number", "stage", "characters", "validation_error", "input_file", "answer_file")}
                  for call in summary["calls"]], "sources": sources,
        "request_reply_GET_snapshot_verified": True, "driver_execution": read(folder / "execution.json")})

for other in plans[1:]:
    for field in ("members", "scope", "prior_stage_run_ids", "expected_alert_pointers", "expected_incident_pointers"):
        assert plans[0][field] == other[field], "changed_comparison_condition:" + field
    assert {k: v for k, v in plans[0]["source_sha256"].items() if k.startswith("services/api/app/socai2/")} == {
        k: v for k, v in other["source_sha256"].items() if k.startswith("services/api/app/socai2/")}
usage = {k: sum(row["known_usage"][k] for row in rows) for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
save("comparison.json", {"kind": "saved_three_scenario_functional_comparison_not_pure_H_AB", "scenarios": rows,
    "real_model_calls": sum(r["real_model_calls"] for r in rows), "known_usage": usage, "cost": None,
    "same_alerts_AI_and_model_application_sources": True, "budget_increased": False,
    "model_budget_exhausted": False, "generation_after_scenarios": 0, "current_assessment_adopted": False,
    "quality_review": "comparison.md", "actual_plan_mapping_note":
    "The per-scenario summaries retain the original baseline plan hash. Actual execution used the immutable plan in each execute-intent; the mapping above is authoritative.",
    "limits": ["H01_also_has_new_history_and_comparison_context", "source_queries_occur_at_different_times",
               "H02_simulation_is_not_a_positive_test_of_real_business_authorization",
               "knowledge_embedding_failed_in_all_three_runs", "no_independent_accuracy_or_causal_improvement_claim"]})
save("replay-manifest.json", {"kind": "immutable_request_and_snapshot_replay_manifest",
    "git_source": read(HERE / "source-replay.json"),
    "scenario_plans": [{k: row[k] for k in ("scenario", "actual_plan_file", "actual_plan_sha256", "driver_snapshot")} for row in rows],
    "files_sha256": {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob("*")) if p.is_file()
        and (p.is_relative_to(HERE / "flow") or p.name in {"config.json", "config-v2.json", "config-v3.json",
            "run-v1.py.txt", "run-v2.py.txt", "run-v3.py.txt", "model-source.patch", "model-route.json",
            "source-replay.json", "knowledge-readonly-diagnostic.json", "knowledge-query-diagnostic.json"})},
    "network_calls": 0, "database_calls": 0, "real_model_calls": 0})
print(json.dumps({"scenarios": len(rows), "real_model_calls": sum(r["real_model_calls"] for r in rows),
                  "known_usage": usage, "replay_files": len(read(HERE / "replay-manifest.json")["files_sha256"])}))
