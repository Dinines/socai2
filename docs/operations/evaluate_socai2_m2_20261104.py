"""Eight fixed current-contract calls; reuse m1 transport, never its batch."""
import json
import sys
from types import SimpleNamespace

import evaluate_socai2_models_20261104 as base

BUILD = base.build_packets
BASE_RUNNER = base.RUNNER
base.OUT = base.ROOT / "docs/operations/evidence/socai2-model-comparison-20261104/m2"
base.REMOTE = "/opt/sting-aisoc-socai2/evidence/next-model-comparison-20261104-m2"
base.RUNNER = base.OUT / "runner.py"


def build():
    from app.socai2.baseline_store import encoded
    from app.socai2.model_protocol import prepare_request

    bundle = BUILD()
    bundle["batch"] = "m2"
    bundle["packets"] = [p for p in bundle["packets"] if p["variant"] == "current"]
    bundle["cells"] = []
    for packet in bundle["packets"]:
        for backend, model, protocol, profile in [
            ("small", "aisoc-investigation", "chat_completions", "vllm_grammar_v1"),
            ("deepseek", "deepseek-flash", "deepseek_responses", "standard"),
        ]:
            body = prepare_request(SimpleNamespace(provider=protocol, schema_profile=profile), {
                "model": model, "messages": packet["messages"], "response_format": packet["response_format"],
                "temperature": 0, "max_tokens": 3000})
            reservation = len(encoded(body)) + 3000 + 256
            assert reservation <= 24000
            bundle["cells"].append({"id": packet["id"] + "-" + backend, "packet_id": packet["id"],
                "backend": backend, "schema_profile": profile, "body": body,
                "body_sha256": base.sha(base.encode(body)), "reservation": reservation})
    assert len(bundle["packets"]) == 4 and len(bundle["cells"]) == 8
    bundle["plan"].update(max_model_calls=8, batch="m2", original_batch_not_retried=True,
        different_wire_schema_only_uniqueItems_for_small=True,
        actual_wire_and_canonical_schema_checked_separately=True)
    bundle["plan"]["limits"] = ["one_attempt_per_cell_not_statistical_accuracy",
        "different_provider_protocol_reasoning_policy_and_explicit_schema_profile",
        "I_C_frozen_priors_are_not_m2_A_outputs", "no_full_C_Deep_C6_H_end_to_end_acceptance"]
    return bundle


def review():
    import jsonschema
    from review_socai2_model_evaluation_20261104 import review as parse

    bundle = json.loads((base.OUT / "plan-and-packets.json").read_text("utf-8"))
    assert all(base.sha((base.ROOT / p).read_bytes()) == h for p, h in bundle["code_hashes"].items())
    packets = {p["id"]: p for p in bundle["packets"]}
    results = []
    for cell in bundle["cells"]:
        path = base.OUT / "remote" / (cell["id"] + "-result.json")
        result = json.loads(path.read_text("utf-8"))
        row = {"cell": cell["id"], "backend": cell["backend"], "schema_profile": cell["schema_profile"],
            "result_sha256": base.sha(path.read_bytes()), **parse(packets[cell["packet_id"]], result)}
        row["canonical_schema_valid"] = row.pop("schema_valid")
        row["wire_schema_valid"] = None
        if "answer" in row:
            body = cell["body"]
            schema = (body["response_format"]["json_schema"] if "response_format" in body else body["text"]["format"])["schema"]
            try:
                jsonschema.validate(row["answer"], schema)
                row["wire_schema_valid"] = True
            except jsonschema.ValidationError:
                row["wire_schema_valid"] = False
        results.append(row)
        print(json.dumps({k: row.get(k) for k in ("cell", "transport_state", "wire_schema_valid", "current_parser_accepts", "parse_error")}, ensure_ascii=False))
    base.write(base.OUT / "parsed-results.json", {"batch": "m2", "cells": results,
        "attempts": len(results), "responses": sum(r["transport_state"] == "response_received" for r in results),
        "known_total_tokens": sum((r.get("usage") or {}).get("total_tokens") or 0 for r in results),
        "business_adoptions": 0, "business_runs": 0, "tool_calls": 0,
        "parser_acceptance_is_not_semantic_acceptance": True})


def main():
    if sys.argv[1:] == ["review"]:
        review()
        return
    if sys.argv[1:] == ["prepare"]:
        base.OUT.mkdir(parents=True, exist_ok=True)
        source = BASE_RUNNER.read_text("utf-8")
        for old, new in [('len(bundle["cells"]) == 12', 'len(bundle["cells"]) == 8'),
                         ('"max_calls": 12', '"max_calls": 8'), ('"cells": 12', '"cells": 8')]:
            assert source.count(old) == 1
            source = source.replace(old, new)
        # Persist the exact runner separately; the closed m1 runner stays unchanged.
        with base.RUNNER.open("x", encoding="utf-8") as stream:
            stream.write(source)
    base.build_packets = build
    base.main()


if __name__ == "__main__":
    main()
