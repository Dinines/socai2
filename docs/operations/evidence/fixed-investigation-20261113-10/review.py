"""Verify the recorded fixed Run; no model, database writes or prose edits."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "services/api"))
from app.socai2.case_program_output import coverage_question, initial_coverage


def read(path):
    return json.loads(path.read_text())


folder = HERE / "flow/R01"
plan, summary = read(HERE / "flow/plan.json"), read(folder / "summary.json")
db, before = read(folder / "export/database.json"), read(ROOT / plan["config"]["snapshot"])
old_rows = {}
for table in ("runs", "results", "case_assessments", "tasks", "task_revisions", "alerts", "alert_materials",
              "incidents", "incident_alerts", "case_alerts", "case_incidents"):
    after = {row["id"]: row for row in db[table]}
    for row in before[table]:
        assert after[row["id"]] == row, ("old_row_changed", table, row["id"])
    old_rows[table] = len(before[table])
assert any(row["case_id"] == summary["case_id"] and row["incident_id"] == plan["incident_id"]
           for row in db["case_incidents"])
artifacts = {a["id"]: a for a in db["artifacts"] if a["run_id"] == summary["run_id"]}
base = next(a["content_json"] for a in artifacts.values() if a["schema_version"] == "socai2.case-model-input.v1")
context = next(a["content_json"] for a in artifacts.values() if a["schema_version"] == "socai2.baseline-context.v1")
assert context["incidents"][plan["incident_id"]]["diagnosis_usable"]
initial = [a for a in artifacts.values() if (a["content_json"] or {}).get("analysis")
           and a["schema_version"].startswith("socai2.baseline-analysis.")]
assert len(initial) == 1
analysis = initial[0]["content_json"]["analysis"]
assert len(analysis["questions"]) == 6
coverage = next(q for q in analysis["questions"] if q["id"] == "coverage")
# PostgreSQL JSONB does not preserve dict key order. Rebuild with the actual
# C3 field selector, checking every frozen value before rendering its text.
facts = initial_coverage(base["input_ledger"], len(context["alerts"]))
assert facts == base["case_boundary"]["coverage_facts"]
assert coverage == coverage_question(analysis, {**base["case_boundary"], "coverage_facts": facts})
assert {row["id"] for row in base["input_ledger"]["records"] if row["block"] == "background_query"
        and row["ref"]["role"] == "execution_receipt"} == set(coverage["evidence_ids"])
calls = []
for call in summary["calls"]:
    payload = artifacts[call["request_artifact_id"]]["content_json"]["payload"]
    answer = json.loads(read(folder / call["reply_file"])["raw"]["choices"][0]["message"]["content"])
    root = answer.get("analysis", answer)
    if call["stage"] == "C3":
        assert len(root["questions"]) == 5 and all(q["id"] != "coverage" for q in root["questions"])
        assert all(q["question_id"] != "coverage" for q in root["followups"])
        assert "coverage：" not in payload["body"]["messages"][1]["content"]
        schema = payload["body"]["response_format"]["json_schema"]["schema"]
        assert schema["properties"]["questions"]["minItems"] == schema["properties"]["questions"]["maxItems"] == 5
    if call["stage"] == "C4.deep":
        assert "coverage_facts" not in payload["case_boundary"]
    calls.append({"number": call["number"], "stage": call["stage"],
        "full_message_characters": sum(len(m["content"]) for m in payload["body"]["messages"]),
        "model_question_count": len(root.get("questions", [])) if call["stage"] in {"C3", "C6"} else None,
        "validation_error": call["validation_error"],
        "correction_codes": [e["code"] for e in (payload.get("correction") or {}).get("errors", [])]})
http = read(folder / "export/http-readback.json")
assert all(value["status"] == 200 for value in http.values())
transport = read(folder / "transport-result.json")
assert transport["ready"] and transport["owned_forward_closed"]
verification = read(folder / "verification.json")
result = {"scope": "One actual fixed Run and isolated PostgreSQL save/read; synthetic materials/H; no quality acceptance.",
    "run_id": summary["run_id"], "result": summary["results"], "real_model_calls": summary["real_model_calls"],
    "known_usage": summary["known_usage"], "cost": None, "old_database_rows_unchanged": old_rows,
    "explicit_event_link_and_usable_I": True, "old_files_unchanged": verification["old_files_unchanged"],
    "C3_model_business_questions": 5, "C3_saved_questions": 6, "C3_coverage_equals_frozen_program_assembly": True,
    "C3_program_coverage": coverage, "calls": calls, "ASGI_GETs": len(http),
    "actual_requests_raw_answers_and_GETs_equal_database": True,
    "knowledge_receipt": verification["knowledge_receipt"], "owned_forward_closed": True,
    "current_assessment": summary["current_assessment"], "prose_quality": "NOT_PASSED"}
with (HERE / "review.json").open("x") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print("Recorded five-to-six assembly, event link, unchanged originals and save/read verified.")
