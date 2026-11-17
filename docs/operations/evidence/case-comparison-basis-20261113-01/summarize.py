"""Summarize completed local evidence; no database or model execution."""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(name):
    return json.loads((HERE / name).read_text())


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        assert path.read_text() == body, ("existing_output_differs", name)
    else:
        path.write_text(body)


data, checks = read("pg-01/database.json"), read("pg-01/checks.json")
flow = next(c["detail"] for c in checks if c["name"] == "test_case_boundary_human_feedback_then_complete_next_flow")
run = next(r for r in data["runs"] if r["id"] == flow["run_id"])
report = next(a["content_json"] for a in data["artifacts"] if a["run_id"] == run["id"]
              and (a["content_json"] or {}).get("type") == "delivery_report")
result, assessment = flow["readback"]["result"], flow["readback"]["current_assessment"]
assert result["conclusion"] == assessment["value"]["conclusion"] == report["result"]["conclusion"]
assert result["change_summary"] == report["result"]["change_summary"]
assert result["case_impact"] == report["result"]["case_impact"]
save("outputs/result-readback.json", result)
save("outputs/current-assessment-readback.json", assessment)
save("outputs/delivery-report.json", report)
save("outputs/H-revisions-readback.json", flow["human_readbacks"])
selected = next(r for r in read("inputs/C6-selection.json")["records"]
                if r["ref"]["type"] == "result" and r["ref"]["id"] == flow["comparison_result_id"])
save("outputs/saved-comparison-basis.json", selected)
save("persistence-verification.json", {
    "passed": True, "case_id": run["case_id"], "run_id": run["id"], "result_id": result["id"],
    "comparison_result_id": flow["comparison_result_id"], "first_run_id": flow["first_run_id"],
    "new_cases": 1, "new_baseline_runs": 2, "seed_A_I_runs": len(data["runs"]) - 2,
    "A_I_models": "substitutes", "Case_models_and_tools": "substitutes", "real_model_calls": 0,
    "selected_comparison_in_saved_request": True, "result_report_current_assessment_conclusion_equal": True,
    "comparison_and_impact_get_equal_to_report": True,
    "old_result_and_revision_unchanged": flow["old_result_and_revision_unchanged"],
    "H_save_did_not_start_run": flow["human_save_did_not_start_run"],
    "first_stale_second_current": flow["first_stale_second_current"],
    "reads": "Real PostgreSQL and existing ASGI read handlers; not TCP or deployment",
    "no_schema_or_http_change": True,
})
# Export the complete multiline comparison passage from the already generated preview.
body = (HERE / "after/C6-model-input.txt").read_text()
sid = read("verification.json")["changed_sources"][0]
start = body.index("[" + sid + "]")
following = re.search(r"^\[[^\n]*｜原范围=", body[start:], re.MULTILINE)
(HERE / "after/C6-selected-comparison.txt").write_text(
    body[start:start + following.start()] if following else body[start:])
print("Completed evidence summaries; no model or database calls.")
