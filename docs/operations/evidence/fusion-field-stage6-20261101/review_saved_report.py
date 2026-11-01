"""Extract report/source comparisons from existing r13 artifacts, without replay."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCE = HERE.parent / "investigation-r13-20261101"
files = {}


def read_text(relative):
    path = SOURCE / relative
    raw = path.read_bytes()
    files[str(path.relative_to(ROOT)).replace("\\", "/")] = hashlib.sha256(raw).hexdigest()
    return raw.decode("utf-8-sig")


def read(relative):
    return json.loads(read_text(relative))


a_text_copy = read_text("A-model-report-step-11.txt")
b_report = read("B-model-report-step-11.txt")
a_context = read("A/006-step-1.response.txt")["data"]
b_context = read("B/006-step-1.response.txt")["data"]
a_result = read("A/003-result.response.txt")
b_result = read("B/003-result.response.txt")
a_reply = read("A/016-step-11.response.txt")["data"]
a_text = a_reply["response"]["content"]
a_requests = [read(f"A/{name}")["data"] for name in (
    "007-step-2.response.txt", "011-step-6.response.txt", "015-step-10.response.txt")]
a_tools = [read(f"A/{name}")["data"]["evidence"] for name in (
    "010-step-5.response.txt", "014-step-9.response.txt")]
b_tools = [read(f"B/{name}")["data"]["evidence"] for name in (
    "010-step-5.response.txt", "014-step-9.response.txt")]
try:
    json.loads(a_text)
    a_valid = True
except json.JSONDecodeError:
    a_valid = False

b_alerts = {e["evidence_id"]: e["data"] for e in b_context["evidence"] if e["kind"] == "alert"}
b_triage = {e["evidence_id"]: e["data"] for e in b_context["evidence"] if e["kind"] == "triage"}
comparisons = {
    "scope": "existing saved evidence review, not a new validation run or proof of universal semantic checks",
    "A_truncation": {"characters": len(a_text), "utf8_bytes": len(a_text.encode()),
        "trailing_whitespace": len(a_text)-len(a_text.rstrip()), "valid_json": a_valid,
        "count_basis": "exact content string in saved model-response JSON; standalone text copy has CRLF checkout conversion",
        "standalone_copy_equal_after_crlf_normalization": a_text_copy.replace("\r\n", "\n") == a_text,
        "status": a_result["status"], "stop_reason": a_result["result"]["stop_reason"],
        "model_response_step_keys": sorted(a_reply), "usage": a_reply.get("usage"),
        "finish_reason_saved_separately": "finish_reason" in a_reply,
        "member_states": [m["status"] for m in a_result["result"]["report"]["member_assessments"]]},
    "A_source_attribution": {
        "confluence_in_each_model_request": ["confluence" in json.dumps(r, ensure_ascii=False).lower() for r in a_requests],
        "confluence_in_model_output": "confluence" in a_text.lower(),
        "pid_4200_in_original_alert_material": "4200" in json.dumps(a_context),
        "pid_field_in_tool_rows": any(key in {"pid", "process_id", "parent_pid"} for t in a_tools for row in t["rows"] for key in row),
        "tool_fields": {t["tool"]: [sorted(row) for row in t["rows"]] for t in a_tools},
        "limitation": "A is an incomplete draft rejected before semantic validation; no claim that these sentences passed the validator."},
    "B_empty_result_and_source_claims": {
        "saved_status": b_result["status"], "completion": b_result["result"]["completion"],
        "tool_available_and_rows": [{"id": t["evidence_id"], "tool": t["tool"], "available": t["available"], "rows": len(t["rows"])} for t in b_tools],
        "incorrect_inference": b_report["findings"][3],
        "approval_claim": b_report["findings"][0],
        "approval_source_description": b_alerts["A1"]["source_material"]["description"]["text"],
        "approval_source_raw": b_alerts["A1"]["source_material"]["raw_event"]["text"],
        "tool_name_id_claim": b_report["gaps"][0],
        "program_query_sources": b_result["result"]["report"]["query_sources"],
        "member_states": [m["status"] for m in b_result["result"]["report"]["member_assessments"]]},
    "B_prior_judgment_boundary": {
        "T1_rationale": b_triage["T1"]["rationale"],
        "T2_rationale": b_triage["T2"]["rationale"],
        "findings_referencing_T": [f for f in b_report["findings"] if any(ref.startswith("T") for ref in f["evidence_ids"])],
        "interpretation": "Prior judgment is available and includes stronger approval/risk claims; the report retells prior rationale while citing A/E. This identifies a source-type attribution risk, not proof of why the model generated it."},
    "new_runs": 0, "new_model_calls": 0, "new_lake_queries": 0,
    "source_files": [{"path": p, "sha256": h} for p, h in sorted(files.items())],
}
(HERE / "report-source-comparisons.json").write_text(json.dumps(comparisons, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps({"source_files": len(files), "A_valid_json": a_valid,
    "A_trailing_whitespace": comparisons["A_truncation"]["trailing_whitespace"],
    "A_finish_reason_saved": comparisons["A_truncation"]["finish_reason_saved_separately"],
    "A_confluence_in_inputs": comparisons["A_source_attribution"]["confluence_in_each_model_request"],
    "A_pid_in_tool_rows": comparisons["A_source_attribution"]["pid_field_in_tool_rows"],
    "B_tool_counts": [len(t["rows"]) for t in b_tools], "new_calls": 0}))
