"""Close the two-call m3 batch without rerunning models or changing raw evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/operations/evidence/socai2-schema-probe-20261104/m3"


def read(path):
    return json.loads(path.read_text("utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    prepared, plan = read(OUT / "preparation.json"), read(OUT / "plan-and-packets.json")
    assert sha(OUT / "plan-and-packets.json") == prepared["packet_sha256"]
    assert sha(OUT / "runner.py") == prepared["runner_sha256"]
    assert read(OUT / "user-authorization.json")["max_model_calls"] == 2
    remote = OUT / "remote"
    before, after = read(remote / "preflight.json"), read(remote / "completion.json")
    assert before["unchanged"] and before["before"] == before["after"]
    assert after["protected_unchanged"] and after["protected_after"] == before["after"]
    assert after["cells"] == 2 and after["business_writes"] == after["tools"] == 0
    intent = read(remote / "batch-intent.json")
    # SSH text upload normalizes CRLF to LF; account for this explicitly.
    normalized = (OUT / "plan-and-packets.json").read_text("utf-8").encode()
    assert hashlib.sha256(normalized).hexdigest() == intent["packets_sha256"]
    cells = []
    for cell in plan["cells"]:
        request = read(remote / (cell["id"] + "-intent.json"))
        response = read(remote / (cell["id"] + "-result.json"))
        assert request["attempt"] == 1 and request["body_sha256"] == cell["body_sha256"]
        assert response["http_status"] == 400 and response["transport_error"]["body_state"] == "selected_json_fields"
        assert not response["transport_error"]["truncated_fields"]
        cells.append({"id": cell["id"], "body_sha256": cell["body_sha256"],
            "http_status": response["http_status"], "elapsed_seconds": response["elapsed_seconds"],
            "error": response["transport_error"]["fields"], "usage": None})
    result = {"batch": "m3-schema-only", "status": "ended_no_retry", "authorized_calls": 2,
        "actual_http_attempts": 2, "model_answers": 0, "http400": 2, "failed_request_usage_unknown": 2,
        "cost_state": "unpriced", "business_materials": False, "business_runs": 0, "business_adoptions": 0,
        "tool_calls": 0, "deployments": 0, "protected_services_and_configs_unchanged": True,
        "cells": cells, "transport_file_note": "local CRLF normalized to LF; normalized packet hash equals remote dispatch intent",
        "findings": ["DeepSeek rejects anyOf branch with bare $ref: missing type",
            "DeepSeek rejects object in multi-type type array",
            "both failures are request-schema compatibility failures, not inference quality measurements"],
        "limits": ["not a business A/I/C run", "not a model quality or accuracy measurement",
            "corrected inline anyOf request has not yet been sent", "not all JSON Schema capabilities tested"],
        "evidence_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(OUT.rglob("*.json"))},
        "runner_sha256": prepared["runner_sha256"], "packet_sha256": prepared["packet_sha256"]}
    target = ROOT / "docs/operations/socai2-schema-probe-m3-20261104.json"
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"receipt": str(target), "attempts": 2, "errors": 2, "protected_unchanged": True}))


if __name__ == "__main__":
    main()
