"""Replay the frozen H01 answer through strict receipt and bounded feedback.

Offline only: no gateway, tokenizer, database, new answer or adoption.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "services/api"))

from app.socai2 import case_followup_output as output
from app.socai2.baseline_analysis_contract import AnalysisRejected
from app.socai2.baseline_context import Context
from app.socai2.baseline_delivery_compat import normalize
from app.socai2.baseline_store import encoded
from jsonschema import Draft202012Validator


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    path = HERE / "comparison-fix" / name
    path.parent.mkdir(exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        assert path.read_text() == text, "immutable_replay_differs:" + str(path)
    else:
        with path.open("x") as file:
            file.write(text)


frozen_files = {str(p.relative_to(HERE)): sha(p) for p in (HERE / "flow").rglob("*") if p.is_file()}
folder = HERE / "flow/H01"
summary = read(folder / "summary.json")
db = read(folder / "export/database.json")
artifacts = [a for a in db["artifacts"] if a["run_id"] == summary["run_id"]]
base = next(a["content_json"] for a in artifacts if a["schema_version"] == "socai2.case-model-input.v1")
context = Context.model_validate(next(a["content_json"] for a in artifacts
                                     if a["schema_version"] == "socai2.baseline-context.v1"))
call = next(c for c in summary["calls"] if c["stage"] == "C6")
request = next(a for a in artifacts if a["id"] == call["request_artifact_id"])
response = next(a for a in artifacts if a["step_id"] == request["step_id"] and a["kind"] == "model_response")
payload = request["content_json"]["payload"]
body = read(folder / call["request_file"])["body"]
assert payload["body"] == body
raw = read(folder / call["reply_file"])["raw"]
assert raw == response["content_json"]["payload"]["raw"]
content, adaptation = normalize(raw["choices"][0]["message"]["content"])
comparison = summary["comparison"]
assert comparison["state"] == "unavailable"
prepared = copy.deepcopy({**payload, "ready": True, "messages": body["messages"], "coverage": base["coverage"]})
for aid, coverage in prepared["coverage"].items():
    coverage["included"] = sum(aid in row["alert_ids"] for row in prepared["followup_boundary"]["records"])
before = copy.deepcopy(prepared)
try:
    output.parse_final(content, prepared, context, comparison)
except AnalysisRejected as exc:
    rejection = str(exc)
else:
    raise AssertionError("saved_invalid_answer_became_accepted")
assert rejection == response["content_json"]["payload"]["validation_error"] == "comparison_not_available"
review = output.FinalReview(prepared, context, comparison)
feedback = review.feedback(content)
assert feedback["errors"] == [{"path": ["comparison", "kind"], "code": "comparison_not_available",
    "subject_id": None, "comparison_state": "unavailable", "allowed_values": ["not_comparable"],
    "current_values": "unchanged"}]
assert feedback["allowed_sources"] == feedback["local_findings"] == feedback["observed_support_ids"] == []
assert review.partial(content) is None and review.details["conclusion_adoptable"] is False
assert len(review.details["retained_analysis"]["members"]) == len(context.alerts)
fmt = output.final_format(prepared, context, comparison)
value = json.loads(content)
old_errors = list(Draft202012Validator(body["response_format"]["json_schema"]["schema"]).iter_errors(value))
new_errors = list(Draft202012Validator(fmt["json_schema"]["schema"]).iter_errors(value))
assert not old_errors and [list(e.path) for e in new_errors] == [["comparison", "kind"]]
assert before == prepared  # Input, original source roles and scopes are unchanged.
messages = body["messages"] + [{"role": "assistant", "content": content},
                              {"role": "user", "content": encoded(feedback).decode()}]
save("C6-feedback.json", feedback)
save("C6-generation-format.json", fmt)
save("C6-correction-preview.json", {"kind": "offline_message_and_schema_preview_not_dispatched",
    "original_response_artifact_id": response["id"], "messages": messages, "response_format": fmt})
assert all(sha(HERE / name) == digest for name, digest in frozen_files.items())
tracked = [Path(__file__), ROOT / "services/api/tests/test_socai2_case_followup_boundary.py"]
tracked += [ROOT / "services/api/app/socai2" / name for name in (
    "baseline_delivery_contract.py", "case_followup_output.py", "case_citation_feedback.py")]
result = {"kind": "offline_frozen_H01_replay", "status": "passed", "real_model_calls": 0,
    "network_calls": 0, "database_calls": 0, "run_id": summary["run_id"],
    "request_artifact_id": request["id"], "response_artifact_id": response["id"],
    "strict_rejection_unchanged": rejection, "old_schema_errors": [],
    "new_schema_error_paths": [list(e.path) for e in new_errors],
    "new_feedback_errors": feedback["errors"], "feedback_characters": len(messages[-1]["content"]),
    "original_feedback": response["content_json"]["payload"].get("correction_feedback"),
    "response_adaptation": adaptation, "partial_review": review.details,
    "input_and_originals_unchanged": True, "original_files_sha256": frozen_files,
    "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in tracked},
    "limits": ["new_feedback_not_sent_to_real_model", "original_result_still_rejected",
               "schema_and_diagnostic_do_not_prove_model_quality"]}
save("summary.json", result)
print(json.dumps({k: result[k] for k in ("status", "strict_rejection_unchanged", "new_schema_error_paths",
                                        "feedback_characters", "real_model_calls")}, ensure_ascii=False))
