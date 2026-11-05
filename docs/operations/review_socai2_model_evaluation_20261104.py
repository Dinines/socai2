"""Parse frozen model-evaluation responses without adopting any result."""
import hashlib
import json
from pathlib import Path

import jsonschema
from app.socai2 import (
    alert_basic_contract,
    baseline_analysis_contract,
    incident_diagnosis_contract,
)
from app.socai2.baseline_context import Context
from app.socai2.baseline_store import StoreError
from app.socai2.model_protocol import response_choices

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/operations/evidence/socai2-model-comparison-20261104/m1"


def review(packet, result):
    out = {"transport_state": result["state"], "usage": result.get("usage"),
        "elapsed_seconds": result.get("elapsed_seconds"), "schema_valid": None,
        "current_parser_accepts": None, "business_adopted": False,
        "semantic_review": "requires_explicit_review_against_frozen_sources"}
    if "raw" not in result:
        return {**out, "transport_error_type": result.get("error_type"), "http_status": result.get("http_status")}
    raw = result["raw"]
    out["provider_reported_model"] = raw.get("model")
    choices = response_choices(raw)
    if not choices or len(choices) != 1:
        return {**out, "protocol_error": "unexpected_response_shape"}
    choice = choices[0]
    out["finish_reason"] = choice.get("finish_reason")
    content = choice.get("message", {}).get("content")
    if not isinstance(content, str):
        return {**out, "protocol_error": "missing_content"}
    out["raw_text"] = content
    try:
        answer = json.loads(content)
        out["answer"] = answer
    except (ValueError, TypeError):
        return {**out, "schema_valid": False, "parse_error": "invalid_json"}
    try:
        jsonschema.validate(answer, packet["response_format"]["json_schema"]["schema"])
        out["schema_valid"] = True
    except jsonschema.ValidationError as exc:
        out["schema_valid"] = False
        out["schema_error"] = {"path": list(exc.absolute_path), "validator": exc.validator}
    if choice.get("finish_reason") != "stop":
        return {**out, "current_parser_accepts": False, "parse_error": "response_not_complete"}
    diagnostics = []
    try:
        if packet["stage"] == "A":
            alert_basic_contract.parse(content, packet["source_map"], packet["data"], diagnostics=diagnostics)
        elif packet["stage"] == "I":
            incident_diagnosis_contract.parse(content, packet["source_map"], packet["data"], diagnostics=diagnostics)
        else:
            baseline_analysis_contract.parse(content, packet["source_map"], Context.model_validate(packet["context"]), packet["coverage"])
        out["current_parser_accepts"] = True
    except (StoreError, baseline_analysis_contract.AnalysisRejected) as exc:
        out["current_parser_accepts"] = False
        out["parse_error"] = getattr(exc, "code", type(exc).__name__)
        if type(exc).__name__ == "AnalysisRejected":
            out["parse_error"] = str(exc)
    out["diagnostics"] = diagnostics
    return out


def main():
    bundle = json.loads((OUT / "plan-and-packets.json").read_text("utf-8"))
    for name, expected in bundle["code_hashes"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, "code changed after freeze: " + name
    packets = {p["id"]: p for p in bundle["packets"]}
    reviews = []
    for cell in bundle["cells"]:
        path = OUT / "remote" / (cell["id"] + "-result.json")
        result = json.loads(path.read_text("utf-8"))
        row = {"cell": cell["id"], "backend": cell["backend"], "packet_id": cell["packet_id"],
            "result_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), **review(packets[cell["packet_id"]], result)}
        reviews.append(row)
        print(json.dumps({k: row.get(k) for k in ("cell", "transport_state", "schema_valid", "current_parser_accepts", "parse_error")}, ensure_ascii=False))
    receipt = {"batch": "m1", "cells": reviews, "attempts": len(reviews),
        "response_received": sum(r["transport_state"] == "response_received" for r in reviews),
        "known_total_tokens": sum((r.get("usage") or {}).get("total_tokens") or 0 for r in reviews),
        "business_adoptions": 0, "business_runs": 0, "tool_calls": 0,
        "parser_version": "current_frozen_code_for_both_old_and_current_input_arms",
        "parser_acceptance_is_not_semantic_acceptance": True,
        "no_full_C_Deep_C6_H_or_second_C_execution": True}
    with (OUT / "parsed-results.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
