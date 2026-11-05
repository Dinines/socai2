"""Read-only comparison of historical model requests; no new model evaluation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load(batch):
    summary = json.loads((ROOT / f"docs/operations/socai2-next-{batch}-validation-20261104.json").read_text("utf-8"))
    path = ROOT / summary["snapshot"]
    body = path.read_bytes()
    return json.loads(body), {"batch": batch, "path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(body).hexdigest()}


def extract(db):
    result = {}
    for run in db["runs"]:
        if run["kind"] != "alert_basic":
            continue
        artifacts = {a["kind"]: a for a in db["artifacts"] if a["run_id"] == run["id"]
            and a["kind"] in {"model_request", "model_response"}}
        request, response = [artifacts[k]["content_json"] for k in ("model_request", "model_response")]
        request, response = request.get("payload", request), response.get("payload", response)
        raw, body = response["raw"], request["body"]
        text = (raw["choices"][0]["message"]["content"] if "choices" in raw else next(
            c["text"] for o in raw["output"] if o["type"] == "message" for c in o["content"] if c["type"] == "output_text"))
        answer = json.loads(text)
        messages = body.get("messages", body.get("input"))
        schema = body["response_format"]["json_schema"] if "response_format" in body else body["text"]["format"]
        result[run["alert_id"]] = {"run_id": run["id"], "state": run["state"], "model": body["model"],
            "request_artifact_id": artifacts["model_request"]["id"], "response_artifact_id": artifacts["model_response"]["id"],
            "messages_sha256": digest(messages), "schema_sha256": digest(schema["schema"]),
            "strict": schema["strict"], "temperature": body["temperature"],
            "output_limit": body.get("max_tokens", body.get("max_output_tokens")),
            "protocol": "chat_completions_via_LiteLLM" if "messages" in body else "direct_responses",
            "reasoning": body.get("reasoning"), "verdict": answer["verdict"], "confidence": answer["confidence"],
            "rationale": answer["rationale"], "validation_error": response.get("validation_error")}
    return result


def main():
    batches, snapshots = {}, []
    for batch in ("r3", "r4", "r5", "r6"):
        db, snapshot = load(batch)
        batches[batch] = extract(db)
        snapshots.append(snapshot)
    pairs = []
    for aid, before in batches["r3"].items():
        after = batches["r4"][aid]
        checked = {key: before[key] == after[key] for key in (
            "messages_sha256", "schema_sha256", "strict", "temperature", "output_limit")}
        assert all(checked.values())
        pairs.append({"alert_id": aid, "equal_request_dimensions": checked,
            "small_backend": before, "deepseek": after, "trials_per_model": 1,
            "different_protocols_and_unverified_small_backend_reasoning_policy": True})
    output = {"scope": "historical_request_and_answer_comparison", "new_model_calls": 0,
        "small_backend_identity": "server_metadata_reports_Qwen3.5-9B_not_independent_weight_verification",
        "snapshots": snapshots, "same_message_and_schema_A_pairs": pairs,
        "latest_compaction_before_after_deepseek": [{"alert_id": aid, "before_r5": before,
            "after_r6": batches["r6"][aid]} for aid, before in batches["r5"].items()],
        "latest_small_model_retest_performed": False, "current_local_v3_real_model_evaluation_performed": False,
        "full_C_Deep_C6_H_second_C_model_comparison_completed": False,
        "limits": ["two_fixed_synthetic_alerts_only", "single_trial_each_not_general_accuracy",
            "I_and_C_prior_judgments_and_actual_inputs_differ_across_models",
            "confidence_is_model_report_not_measured_accuracy_or_risk",
            "parser_acceptance_and_semantic_correctness_are_separate"]}
    target = ROOT / "docs/operations/socai2-model-comparison-20261104.json"
    assert not target.exists(), "immutable comparison receipt"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({"receipt": str(target), "matched_A_pairs": len(pairs), "new_model_calls": 0,
        "latest_small_model_retest": False}))


if __name__ == "__main__":
    main()
