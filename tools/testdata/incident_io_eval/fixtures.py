"""Read existing evidence; do not regenerate or modify the original batch."""
import hashlib
import json


def load(root, config):
    path = root / config["snapshot"]
    raw = path.read_bytes()
    database = json.loads(raw)
    run = next(r for r in database["runs"] if r["id"] == config["source_run_id"])
    if run["kind"] != "incident_diagnosis":
        raise ValueError("not_an_incident_run")
    artifacts = {a["id"]: a for a in database["artifacts"]}
    saved = [a for a in artifacts.values() if a["run_id"] == run["id"]]
    request = next(a["content_json"] for a in saved if a["kind"] == "model_request")
    response = next(a["content_json"] for a in saved if a["kind"] == "model_response")
    source = artifacts[run["input_artifact_id"]]["content_json"]
    content = response["raw"]["choices"][0]["message"]["content"]
    queries = []
    for member in source["members"]:
        triage = member.get("triage") or {}
        selected = [a for a in artifacts.values() if a["kind"] == "tool_response"
                    and a["run_id"] == triage.get("source_run_id") and a["alert_id"] == member["alert"]["id"]
                    and a["tenant_id"] == run["tenant_id"]]
        queries.append({"alert_id": member["alert"]["id"], "triage_id": triage.get("id"),
                        "source_run_id": triage.get("source_run_id"),
                        "receipts": [{"artifact_id": a["id"], "sha256": a["sha256"],
                                      "body": a["content_json"]} for a in selected],
                        "included_in_current_i_model_view": False})
    return {"run": run, "source": source, "request": request, "response": response,
            "data": json.loads(request["body"]["messages"][-1]["content"]),
            "source_map": request["source_map"], "raw_answer": content, "answer": json.loads(content),
            "saved_diagnosis": next(x for x in database["incident_diagnoses"] if x["source_run_id"] == run["id"]),
            "snapshot_sha256": hashlib.sha256(raw).hexdigest(), "queries": queries}
