"""Read-only replay of saved C3/C6 role failures against the current adapters."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from app.socai2 import case_followup_output as c6
from app.socai2 import case_output_adapter as c3
from app.socai2.baseline_analysis_contract import time_context
from app.socai2.baseline_context import Context
from jsonschema import Draft202012Validator


def replay(database):
    original = database.read_bytes()
    data = json.loads(original)
    artifacts = {a["id"]: a for a in data["artifacts"]}
    context = Context.model_validate(next(a["content_json"] for a in artifacts.values()
        if a["schema_version"] == "socai2.baseline-context.v1"))
    coverage = next(a["content_json"]["coverage"] for a in artifacts.values()
        if a["schema_version"] == "socai2.case-model-input.v1")
    rows = []
    for step in sorted(data["run_steps"], key=lambda s: s["seq"]):
        stage = step["stage_code"]
        if step["kind"] != "model" or stage not in {"C3", "C6"}:
            continue
        prepared = copy.deepcopy(artifacts[step["input_artifact_id"]]["content_json"]["payload"])
        prepared["coverage"] = coverage
        response = next(a for a in artifacts.values()
            if a["step_id"] == step["id"] and a["kind"] == "model_response")
        content = response["content_json"]["payload"]["raw"]["choices"][0]["message"]["content"]
        raw, comparison = json.loads(content), {"state": "initial", "result_id": None}
        if stage == "C3":
            fmt = c3.output_format(prepared, context, prepared["binding_map"])
            review = c3.CaseReview(prepared, context, prepared["binding_map"])
        else:
            fmt = c6.final_format(prepared, context, comparison)
            review = c6.FinalReview(prepared, context, comparison)
        schema = fmt["json_schema"]["schema"]
        validator = Draft202012Validator(schema)
        finding_validator = Draft202012Validator({"$ref": "#/$defs/Finding", "$defs": schema["$defs"]})
        feedback, mixed = review.feedback(content), []
        for i, finding in enumerate(raw.get("analysis", raw)["findings"]):
            if finding["state"] != "observed":
                continue
            invalid = [{"id": sid, "ref": prepared["source_map"][sid]["ref"]}
                for sid in finding["support_ids"] if prepared["source_map"][sid]["ref"]["role"] != "observation"
                and not time_context(prepared["source_map"][sid]["ref"])]
            if invalid:
                mixed.append({"index": i, "id": finding["id"], "statement": finding["statement"],
                    "invalid_supports": invalid, "generation_accepts_finding": finding_validator.is_valid(finding)})
        try:
            if stage == "C3":
                c3.parse(content, prepared, context, prepared["binding_map"])
            else:
                c6.parse_final(content, prepared, context, comparison)
            rejection = None
        except ValueError as exc:
            rejection = str(exc)
        rows.append({"stage": stage, "step_id": step["id"], "seq": step["seq"],
            "request_artifact_id": step["input_artifact_id"], "response_artifact_id": response["id"],
            "raw_content_sha256": hashlib.sha256(content.encode()).hexdigest(),
            "full_schema_errors": [{"path": list(e.path), "validator": e.validator}
                for e in validator.iter_errors(raw)], "receiver_rejection": rejection,
            "feedback_errors": feedback["errors"] if feedback else [], "mixed_observed_findings": mixed})
    assert database.read_bytes() == original
    return {"source_database": str(database), "source_database_sha256": hashlib.sha256(original).hexdigest(),
        "model_calls": 0, "database_writes": 0, "original_unchanged": True, "replays": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = replay(args.database)
    with args.output.open("x") as out:
        json.dump(result, out, ensure_ascii=False, indent=2)
        out.write("\n")
    print(json.dumps({"replayed_responses": len(result["replays"]), "original_unchanged": True,
                      "output": str(args.output)}))
