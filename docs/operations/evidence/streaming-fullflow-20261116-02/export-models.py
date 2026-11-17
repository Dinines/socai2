"""Export each saved model request and its exact original; never invoke a model."""

import argparse
import hashlib
import json
from pathlib import Path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def export(snapshot, output, forbidden):
    data = json.loads(snapshot.read_text())
    rows = data.get("rows", data)
    output.mkdir(exist_ok=False)
    requests = {a["id"]: a for a in rows["artifacts"] if a["kind"] == "model_request"}
    originals = {}
    for a in rows["artifacts"]:
        content = a.get("content_json")
        if a["kind"] != "source_snapshot" or not isinstance(content, dict):
            continue
        request_id = content.get("request_artifact_id")
        if request_id in requests and isinstance(content.get("raw"), dict):
            originals.setdefault(request_id, []).append(a)
    steps = {s["id"]: s for s in rows["run_steps"]}
    summaries = []
    for request in sorted(requests.values(), key=lambda a: (a["captured_at"], a["id"])):
        rid = request["id"]
        step = steps[request["step_id"]]
        content = request["content_json"]
        payload = content.get("payload", content)
        body = payload["body"]
        assert isinstance(body["messages"], list)
        folder = output / (request["run_id"] + "-" + str(step["seq"]) + "-" + rid)
        folder.mkdir()
        original = originals.get(rid, [])
        assert len(original) <= 1, "ambiguous original response for request " + rid
        messages = "\n\n".join(
            "[" + m["role"] + "]\n" + m["content"] for m in body["messages"]
        )
        values = {"request.json": body, "request-artifact.json": request}
        texts = {"input.txt": messages}
        summary = {
            "run_id": request["run_id"],
            "step_id": step["id"],
            "stage": step["stage_code"],
            "request_artifact_id": rid,
            "step_state": step["state"],
            "step_error": step["error"],
            "state": "received_original" if original else "no_received_original",
            "input_observations": [
                token for token in forbidden if token.lower() in messages.lower()
            ],
        }
        if original:
            source = original[0]
            raw = source["content_json"]["raw"]
            values.update({"response.json": raw, "original-artifact.json": source})
            choice = raw.get("choices", [])
            if choice and isinstance(choice[0].get("message", {}).get("content"), str):
                texts["output.txt"] = choice[0]["message"]["content"]
            summary.update(
                original_artifact_id=source["id"],
                usage=raw.get("usage"),
                finish_reason=choice[0].get("finish_reason") if choice else None,
            )
        for name, value in values.items():
            (folder / name).write_text(
                json.dumps(value, ensure_ascii=False, indent=2) + "\n"
            )
        for name, value in texts.items():
            (folder / name).write_text(value)
        summary["files"] = {
            str(p.relative_to(output)): sha(p.read_bytes()) for p in folder.iterdir()
        }
        summaries.append(summary)
    result = {
        "source_snapshot_sha256": sha(snapshot.read_bytes()),
        "requests": summaries,
        "request_count": len(requests),
        "received_original_count": len(originals),
        "usage_unknown_requests": sum(not row.get("usage") for row in summaries),
        "cost": "unknown",
        "new_model_calls": 0,
        "note": "Request identity, not step or vendor response id, separates correction/supplement calls.",
    }
    (output / "index.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    value = export(
        args.snapshot,
        args.output,
        [
            "tenant_uid",
            "synthetic",
            "fixture",
            "is_test",
            "expected_verdict",
            config["batch_id"],
            config["fixture"]["source_namespace"],
        ],
    )
    print(json.dumps({k: v for k, v in value.items() if k != "requests"}))
