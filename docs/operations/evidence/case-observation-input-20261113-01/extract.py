"""Export actual substitute requests and stored observations; offline only."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def save(name, value):
    path = HERE / "inputs" / name
    path.parent.mkdir(exist_ok=True)
    body = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        assert path.read_text() == body
    else:
        with path.open("x") as file:
            file.write(body)


checks = read(HERE / "pg-01/checks.json")
outcome = checks[-1]["detail"]
assert checks[-1]["passed"] and outcome["final_result_and_current_assessment_gets"]
db = read(HERE / "pg-01/database.json")
artifacts = [a for a in db["artifacts"] if a["run_id"] == outcome["run_id"]]
steps = {s["id"]: s for s in db["run_steps"]}
requests = sorted([a for a in artifacts if a["kind"] == "model_request"], key=lambda a: steps[a["step_id"]]["seq"])
inputs = []
for number, artifact in enumerate(requests, 1):
    payload = artifact["content_json"]["payload"]
    response = next(a for a in artifacts if a["kind"] == "model_response" and a["step_id"] == artifact["step_id"])
    stage = steps[artifact["step_id"]]["stage_code"]
    prefix = f"{number:02}-{stage.replace('.', '-')}"
    save(prefix + "-input.txt", payload["body"]["messages"][1]["content"])
    save(prefix + "-request.json", payload)
    save(prefix + "-answer.json", response["content_json"]["payload"])
    assert payload["case_boundary"]["program_output"] == "socai2.case-program-output.v2"
    inputs.append({"stage": stage, "request_artifact_id": artifact["id"], "response_artifact_id": response["id"],
        "input_file": prefix + "-input.txt", "input_characters": len(payload["body"]["messages"][1]["content"]),
        "validation_error": response["content_json"]["payload"]["validation_error"]})
result = next(row for row in db["results"] if row["id"] == outcome["result_id"])
assert result["validation_state"] == "accepted" and result["findings"]
assert result["findings"] == outcome["readback"]["result"]["findings"]
assert result["conclusion"] == outcome["readback"]["current_assessment"]["value"]["conclusion"]
save("stored-observations.json", result["findings"])
save("readback.json", outcome["readback"])
save("summary.json", {"kind": "actual_pg_substitute_requests_and_observations", "case_id": outcome["case_id"],
    "run_id": outcome["run_id"], "result_id": result["id"], "real_model_calls": 0, "case_substitute_requests": len(inputs),
    "inputs": inputs, "result": {key: result[key] for key in ("validation_state", "conclusion_state", "delivery_state")},
    "observations_refs_and_GETs_equal_database": True, "current_assessment_equal_result": True,
    "snapshot_sha256": hashlib.sha256((HERE / "pg-01/database.json").read_bytes()).hexdigest(),
    "limits": ["synthetic_model_and_tool_replies", "not_real_model_quality_or_TCP_verification"]})
print(json.dumps({"requests": len(inputs), "observations": len(result["findings"]),
                  "result": [result[k] for k in ("validation_state", "conclusion_state", "delivery_state")]}, ensure_ascii=False))
