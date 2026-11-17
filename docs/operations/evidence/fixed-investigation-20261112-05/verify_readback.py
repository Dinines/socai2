"""Check this saved batch and export exact first-request material, without dispatch."""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
FLOW = BASE / "flow"


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def reference_paths(value, sources, path="$", output=None):
    output = [] if output is None else output
    if isinstance(value, dict):
        for key, child in value.items():
            reference_paths(child, sources, path + "." + key, output)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reference_paths(child, sources, path + f"[{index}]", output)
    elif isinstance(value, str) and value in sources:
        output.append({"path": path, "source": value})
    return output


def main():
    db = read(FLOW / "export/database.json")
    created = read(FLOW / "created.json")
    execution = read(FLOW / "execution.json")
    run_id = created["pending_run_id"]
    run = next(r for r in db["runs"] if r["id"] == run_id)
    result = db["results"][0]
    api_result = read(FLOW / "http" / f"result-{result['id']}.json")["body"]
    api_case = read(FLOW / "http/case.json")["body"]
    fields = ["id", "source_run_id", "validation_state", "delivery_state", "conclusion",
              "conclusion_state", "findings", "questions", "recommendations", "case_impact",
              "closing_note", "source_answer_id", "report_artifact_id"]
    assert all(result[k] == api_result["result"][k] for k in fields)
    assert result["source_run_id"] == run_id
    assert result["conclusion"] is None and result["validation_state"] == "rejected"
    assert not db["case_assessments"] and db["cases"][0]["current_assessment_id"] is None
    assert api_case["current_assessment"] is None
    assert [r["incident_id"] for r in db["case_incidents"]] == created["linked_incident_ids"]
    assert execution["unknown"] is False
    requests = [a for a in db["artifacts"] if a["kind"] == "model_request"]
    inputs, totals = [], {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    labels = {("I", 1): "I", ("Case", 1): "C3", ("Case", 3): "Deep-1",
              ("Case", 4): "Deep-2", ("Case", 5): "C6"}
    knowledge_checks = []
    for stage in ("I", "Case"):
        for file in sorted((FLOW / stage / "calls").glob("call-*-intent.json")):
            number = int(file.name.split("-")[1])
            body = read(file)["body"]
            stored = [a for a in requests if a["content_json"].get(
                "payload", a["content_json"]).get("body") == body]
            assert len(stored) == 1, (stage, number, "request_not_saved_exactly")
            receipt = read(file.with_name(f"call-{number}-receipt.json"))
            assert receipt["state"] == "response_received" and receipt["http_status"] == 200
            totals["calls"] += 1
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                totals[key] += receipt["raw"]["usage"][key]
            label = labels.get((stage, number))
            if label:
                material = body["messages"][1]["content"]
                output = FLOW / (label + "-model-input-exact.txt")
                output.write_text(material)
                assert output.read_text() == material
                inputs.append({"stage": label, "characters": len(material),
                               "lines": len(material.splitlines()), "file": str(output.relative_to(BASE)),
                               "sha256": hashlib.sha256(material.encode()).hexdigest(),
                               "request_artifact_id": stored[0]["id"], "request_matches_database": True})
            if stage == "Case":
                source_map = stored[0]["content_json"]["payload"]["source_map"]
                knowledge = {key: value for key, value in source_map.items() if value.get("knowledge")}
                response = json.loads(receipt["raw"]["choices"][0]["message"]["content"])
                knowledge_checks.append({"call": number, "label": label or "correction",
                    "sources": {key: {"ref": value["ref"], "alert_ids": value["alert_ids"],
                        "purposes": [o["purpose"] for o in value["knowledge"]["origins"]]}
                        for key, value in knowledge.items()},
                    "response_references": reference_paths(response, knowledge)})
    knowledge_tool = next(a for a in db["artifacts"] if a["run_id"] == run_id
        and a["kind"] == "tool_response" and a["content_json"].get("tool_name") == "knowledge")
    rows = knowledge_tool["content_json"]["rows"]
    document_ids = read(FLOW / "knowledge-ready.json")["document_ids"]
    assert rows and all(row["record_id"] in document_ids for row in rows)
    delivery = next(a["content_json"] for a in db["artifacts"] if a["run_id"] == run_id
        and (a.get("content_json") or {}).get("type") == "delivery_report")
    save(FLOW / "input-summary.json", inputs)
    save(FLOW / "knowledge-use.json", {"tool_artifact_id": knowledge_tool["id"],
        "document_ids": document_ids, "retrieved_rows": len(rows),
        "retrieval_purposes": [r["purpose"] for r in rows], "requests": knowledge_checks,
        "F02": "NOT_PASSED", "boundary": "References prove consumption, not reasonable use or truth."})
    save(FLOW / "readback-checks.json", {"state": "checked", "case_id": created["case_id"],
        "run_id": run_id, "linked_incident_ids": created["linked_incident_ids"],
        "run_state": run["state"], "stop_reason": run["stop_reason"], "result_id": result["id"],
        "validation_state": result["validation_state"], "delivery_state": result["delivery_state"],
        "conclusion": result["conclusion"], "current_assessment": None,
        "result_http_sql_equal_fields": fields, "new_requests_saved_exactly": totals["calls"],
        "generation_usage": totals, "cost": None, "new_A_calls": 0,
        "unknown_dispatches": False, "validation_review": {key: value
            for key, value in delivery["validation_review"].items() if key != "retained_analysis"},
        "correction_result": delivery["correction_result"], "model_quality": "NOT_PASSED",
        "fixed_flow_complete": False, "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    print(json.dumps({"readback": "checked", "inputs": len(inputs), "generation_usage": totals,
                      "result": "rejected/partial", "conclusion": None}, ensure_ascii=False))


if __name__ == "__main__":
    main()
