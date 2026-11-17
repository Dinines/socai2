"""Verify sealed real answers retain old behavior and new fixed values persist."""
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "services/api"), str(ROOT)]
from app.socai2.baseline_context import Context
from app.socai2.case_followup_output import parse_final


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    path = HERE / name
    body = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        assert path.read_text() == body
    else:
        with path.open("x") as file:
            file.write(body)


config = read(HERE / "preview-config.json")
original = ROOT / config["offline_source"]
db, summary = read(original / "export/database.json"), read(original / "summary.json")
artifacts = {a["id"]: a for a in db["artifacts"] if a["run_id"] == config["run_id"]}
context = Context.model_validate(next(a["content_json"] for a in artifacts.values()
    if a["schema_version"] == "socai2.baseline-context.v1"))
base = next(a["content_json"] for a in artifacts.values() if a["schema_version"] == "socai2.case-model-input.v1")
request = artifacts[summary["calls"][-1]["request_artifact_id"]]["content_json"]["payload"]
prepared = copy.deepcopy({**base, **request})
for aid, coverage in prepared["coverage"].items():
    coverage["included"] = sum(aid in r["alert_ids"] for r in prepared["followup_boundary"]["records"])
raw = read(original / "calls/call-3-receipt.json")["raw"]["choices"][0]["message"]["content"]
assert "fixed_comparison" not in prepared["case_boundary"]
parsed = parse_final(raw, prepared, context, summary["comparison"])
assert parsed.comparison.summary == summary["results"][0]["change_summary"]
save("legacy-answer-check.json", {"original_result_id": summary["result_ids"][0],
    "legacy_parse": "accepted_as_original", "comparison": parsed.comparison.model_dump(mode="json"),
    "prose_quality": "NOT_PASSED", "old_answer_and_Result_not_rewritten": True})
preview = read(HERE / "after/C6-request-preview.json")
assert "comparison" not in preview["response_format"]["json_schema"]["schema"]["properties"]
assert "本次没有可用的指定历史综合结论" in preview["messages"][1]["content"]
assert (HERE / "after/C3-model-input.txt").read_text() == (original / summary["calls"][0]["input_file"]).read_text()

pg = read(HERE / "pg-01/database.json")
checks = read(HERE / "pg-01/checks.json")
assert all(c["passed"] for c in checks)
outcome = checks[-1]["detail"]
rows = [a for a in pg["artifacts"] if a["run_id"] == outcome["run_id"]]
request = next(a for a in rows if a["kind"] == "model_request"
               and a["content_json"]["payload"]["case_boundary"].get("stage") == "C6")
payload = request["content_json"]["payload"]
response = next(a["content_json"]["payload"] for a in rows if a["kind"] == "model_response"
                and a["step_id"] == request["step_id"])
model_answer = json.loads(response["raw"]["choices"][0]["message"]["content"])
assert "comparison" not in model_answer
fixed = payload["case_boundary"]["fixed_comparison"]
result = next(r for r in pg["results"] if r["id"] == outcome["result_id"])
assert result["change_kind"] == fixed["value"]["kind"] == "not_comparable"
assert result["change_summary"] == fixed["value"]["summary"]
assert outcome["readback"]["result"]["change_summary"] == result["change_summary"]
assert outcome["readback"]["current_assessment"]["value"]["conclusion"] == result["conclusion"]
save("pg-C6-model-input.txt", payload["body"]["messages"][1]["content"])
save("pg-C6-request.json", payload)
save("pg-C6-raw-answer.json", response)
save("pg-comparison-readback.json", {"fixed_comparison": fixed, "raw_answer_omits_comparison": True,
    "result": {k: result[k] for k in ("id", "source_run_id", "change_kind", "change_summary", "validation_state")},
    "readback": outcome["readback"], "old_result_id": outcome["old_result_id"],
    "old_rejected_result_unchanged": outcome["old_rejected_result_unchanged"]})
before = read(original.parents[1] / "original-files-before-fix.json")
assert all(sha(ROOT / p) == value for p, value in before.items())
save("verification.json", {"state": "passed", "real_model_calls": 0, "network_calls": 0,
    "old_real_files_unchanged": len(before), "legacy_answer_behavior_unchanged": True,
    "C3_business_input_unchanged": True, "new_C6_comparison_slot_removed": True,
    "new_C6_business_characters": len(preview["messages"][1]["content"]),
    "fixed_comparison_saved_and_GET_equal": True, "current_assessment_conclusion_GET_equal": True,
    "real_model_quality": "NOT_PASSED", "new_fixed_boundary_generation_effect": "not_sampled",
    "snapshot_sha256": sha(HERE / "pg-01/database.json")})
print("Legacy answer preserved; new fixed comparison saved/read; no network or model calls.")
