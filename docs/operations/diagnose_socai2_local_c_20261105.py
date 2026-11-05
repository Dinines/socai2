"""Offline c diagnosis: response schema violation and final evidence visibility."""
import copy
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api"))

from app.socai2 import baseline_analysis_contract as analysis
from app.socai2 import baseline_delivery_contract as delivery
from app.socai2.baseline_context import Context
from app.socai2.baseline_store import digest, encoded
from app.socai2.model_protocol import prepare_request
from app.socai2.structured_output import response_format
from jsonschema import Draft202012Validator
from pydantic import ValidationError

BATCH = ROOT / ".local/local-investigation/validation/local-maintenance-20261105c"
DATABASE = BATCH / "exports/20261105T110746110174Z/database.json"
OUTPUT = ROOT / "docs/operations/evidence/investigation-repair-20261105/local-c-diagnosis.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    db_before, plan_before = sha(DATABASE), sha(BATCH / "plan.json")
    db = json.loads(DATABASE.read_text())
    run = next(r for r in db["runs"] if r["kind"] == "baseline")
    steps = {s["id"]: s for s in db["run_steps"] if s["run_id"] == run["id"]}
    artifacts = [a for a in db["artifacts"] if a["run_id"] == run["id"]]

    def model(stage, kind):
        a = next(a for a in artifacts if a["kind"] == kind and steps.get(a["step_id"], {}).get("stage_code") == stage)
        assert digest(a["content_json"]) == a["sha256"]
        return a

    req, rsp = model("C6", "model_request"), model("C6", "model_response")
    p = req["content_json"]["payload"]
    body = p["body"]
    raw = rsp["content_json"]["payload"]["raw"]
    text = raw["output"][0]["content"][0]["text"]
    value = json.loads(text)
    view = json.loads(body["input"][1]["content"])
    context = Context.model_validate(next(a["content_json"] for a in artifacts
        if a["schema_version"] == "socai2.baseline-context.v1"))
    schema = body["text"]["format"]["schema"]
    errors = [{"path": list(e.absolute_path), "schema_path": list(e.absolute_schema_path),
        "validator": e.validator, "message": e.message} for e in Draft202012Validator(schema).iter_errors(value)]
    assert len(errors) == 1 and errors[0]["validator"] == "additionalProperties"
    assert value["analysis"]["conflicts_note"] is None
    assert schema["$defs"]["Analysis"]["additionalProperties"] is False
    assert "conflicts_note" not in schema["$defs"]["Analysis"]["properties"]
    assert raw["status"] == "completed" and raw["incomplete_details"] is None
    assert raw["usage"]["output_tokens"] < body["max_output_tokens"]
    assert raw["text"]["format"]["schema"] == schema
    try:
        delivery.Delivery.model_validate(value)
    except ValidationError as exc:
        shape = [{"path": list(e["loc"]), "type": e["type"], "message": e["msg"]}
            for e in exc.errors(include_input=False, include_url=False)]
    else:
        raise AssertionError("original response unexpectedly shape-valid")
    try:
        delivery.parse(text, p["source_map"], context, view["members"], view["comparison"])
    except analysis.AnalysisRejected as exc:
        rejected = str(exc)
    else:
        raise AssertionError("original response unexpectedly accepted")
    assert rejected == "delivery_shape_invalid"
    reconstructed = prepare_request(SimpleNamespace(provider="deepseek_responses", schema_profile="standard"),
        {"model": body["model"], "messages": body["input"], "max_tokens": body["max_output_tokens"],
            "temperature": body["temperature"], "response_format": response_format(delivery.Delivery, p["source_map"],
                members=context.alerts, questions=[q.id for q in context.questions], objects=context.scope.object_keys)})
    assert reconstructed == body
    # Diagnostic only: confirms the single structural gate, never saves or
    # adopts a modified response. This says nothing about natural-language truth.
    probe = copy.deepcopy(value)
    del probe["analysis"]["conflicts_note"]
    delivery.parse(json.dumps(probe), p["source_map"], context, view["members"], view["comparison"])
    assert "conflicts_note" in value["analysis"]

    c3req, c3rsp = model("C3", "model_request"), model("C3", "model_response")
    c3p = c3req["content_json"]["payload"]
    c3raw = c3rsp["content_json"]["payload"]["raw"]
    c3value = json.loads(c3raw["output"][0]["content"][0]["text"])
    Draft202012Validator(c3p["body"]["text"]["format"]["schema"]).validate(c3value)
    analysis.parse(json.dumps(c3value), c3p["source_map"], context,
        json.loads(c3p["body"]["input"][1]["content"])["members"], bindings=c3p["binding_map"])
    queries = [a for a in artifacts if (a.get("content_json") or {}).get("type") == "query_projection"]
    qids = {a["id"] for a in queries}
    query_tools = []
    for a in artifacts:
        if a["kind"] == "tool_response" and steps.get(a["step_id"], {}).get("stage_code") == "C4.query":
            c = a["content_json"]
            assert digest(c) == a["sha256"]
            query_tools.append({"artifact_id": a["id"], "sha256": a["sha256"], "tool_name": c["tool_name"],
                "state": c["state"], "returned_rows": c["returned_rows"], "truncated": c["truncated"],
                "event_ids": [r["event_id"] for r in c["rows"]],
                "event_times": [r["event_time"] for r in c["rows"]], "limit": c["actual_args"]["limit"],
                "lake_database": c["actual_args"]["parameters"]["source_database"]})
    assert len(query_tools) == 2 and all(q["returned_rows"] == 1 and not q["truncated"] for q in query_tools)
    evidence_view = next(a for a in artifacts if (a.get("content_json") or {}).get("type") == "model_view"
        and any(s["ref"]["id"] in qids for s in a["content_json"]["source_map"].values()))
    c4_sources = [s for s in evidence_view["content_json"]["source_map"].values() if s["ref"]["id"] in qids]
    c6_sources = [s for s in p["source_map"].values() if s["ref"]["id"] in qids]
    c6_omissions = [o for o in p["omissions"] if o["ref"]["id"] in qids]
    assert len(c4_sources) == len(c6_omissions) == 9 and not c6_sources
    assert all(o["reason"] == "model_view_budget_exhausted" for o in c6_omissions)
    assert {q["artifact_id"] for q in view["queries"]} == qids
    assert {r["projection_id"] for r in view["followup_execution"]["routes"]} == qids
    assert all(r["state"] == "completed" and not r["reused"] for r in view["followup_execution"]["routes"])
    plan = json.loads((BATCH / "plan.json").read_text())
    source_names = ["baseline_analysis.py", "baseline_execution_schema.py", "baseline_delivery_contract.py",
        "baseline_reanalysis.py", "baseline_reasoning.py", "baseline_analysis_model.py", "model_protocol.py", "structured_output.py"]
    sources = {"services/api/app/socai2/" + n: sha(ROOT / "services/api/app/socai2" / n) for n in source_names}
    assert all(plan["source_sha256"][name] == value for name, value in sources.items())
    assert sha(DATABASE) == db_before and sha(BATCH / "plan.json") == plan_before
    result = {"kind": "offline_local_c_failure_diagnosis_not_adoption", "created_at": datetime.now(timezone.utc).isoformat(),
        "command": ".local/conda-envs/socai2/bin/python docs/operations/diagnose_socai2_local_c_20261105.py",
        "redaction": "synthetic identifiers only; no credentials, full prompts, raw answer or raw lake row copied",
        "database": {"path": str(DATABASE.relative_to(ROOT)), "sha256_before": db_before, "sha256_after": sha(DATABASE)},
        "frozen_plan_sha256": plan_before, "source_sha256_matching_plan": sources,
        "run_id": run["id"], "case_id": run["case_id"], "run_state": run["state"], "stop_reason": run["stop_reason"],
        "c6": {"request_id": req["id"], "request_sha256": req["sha256"], "response_id": rsp["id"],
            "response_sha256": rsp["sha256"], "provider_request_id": raw["id"], "model": raw["model"],
            "status": raw["status"], "incomplete_details": raw["incomplete_details"], "usage": raw["usage"],
            "max_output_tokens": body["max_output_tokens"], "strict_sent": body["text"]["format"]["strict"],
            "schema_sha256": digest(schema), "schema_errors": errors, "pydantic_errors": shape,
            "original_parse_rejection": rejected, "reconstructed_full_request_identical": True,
            "provider_echoed_schema_identical": True, "wire_bytes": len(encoded(body)),
            "messages_bytes": len(encoded(body["input"])), "view_bytes": len(body["input"][1]["content"].encode()),
            "diagnostic_only": "Removing only conflicts_note in memory passes existing parser; not saved/adopted and not a semantic quality pass"},
        "c3": {"request_id": c3req["id"], "response_id": c3rsp["id"], "actual_dynamic_wire_valid": True,
            "original_parse_valid": True, "usage": c3raw["usage"], "followups": [
                {"index": i, "mode": x["mode"], "binding_id": x["binding_id"], "priority": x["priority"],
                    "tool_name": c3p["binding_map"][x["binding_id"]]["tool_name"],
                    "object_types": [json.loads(o)[0] for o in x["object_keys"]]} for i, x in enumerate(c3value["followups"])],
            "limitation": "one real success demonstrates this response complied; no proof schema enforcement caused it"},
        "lake_tools": query_tools, "evidence_visibility": {"intermediate_view_artifact_id": evidence_view["id"],
            "intermediate_view_bytes": evidence_view["content_json"]["bytes"],
            "intermediate_query_fields": len(c4_sources),
            "intermediate_fields_by_projection": dict(Counter(s["ref"]["id"] for s in c4_sources)),
            "c6_query_fields": len(c6_sources), "c6_query_omissions": c6_omissions,
            "c6_queries_metadata_count": len(view["queries"]), "route_to_projection_links_preserved": True,
            "cause": "C6 second bounded_input prioritizes frozen required facts/plans and omits all nine optional lake fields at model_view_budget_exhausted",
            "cannot_claim": "model consumed returned lake row facts; completed queries only establish execution here"},
        "classification": {"immediate_failure": "provider response violates transmitted additionalProperties=false",
            "not_supported_as_cause": ["missing required field", "output truncation", "HTTP failure", "wrong schema assembly/transport", "total token budget exhaustion"],
            "provider_internal_cause": "unknown; black-box evidence establishes nonconforming output, not whether strict was ignored internally",
            "independent_own_code_gap": "C4 received row facts are absent from C6 model input despite completed metadata"},
        "execution": {"batch_model_attempts": 5, "a_b_c_model_attempts": 14, "authorized_cap": 50,
            "baseline_models": 2, "deep_models": 0, "baseline_tools": 4,
            "case_assessments": len(db["case_assessments"]), "H_executed": False},
        "official_docs_checked": [
            {"url": "https://api-docs.deepseek.com/api/create-response/", "claim": "Responses lists Flash/Pro and describes json_schema output as conforming to supplied schema"},
            {"url": "https://api-docs.deepseek.com/guides/responses_api/", "claim": "format is listed fully supported; guide does not separately promise strict flag behavior"},
            {"url": "https://api-docs.deepseek.com/api/create-chat-completion/", "claim": "Chat response_format documents text/json_object only, not an equivalent structured schema guarantee"},
            {"url": "https://api-docs.deepseek.com/guides/tool_calls/", "claim": "Beta strict function calling documents schema constraints, requires beta endpoint and strict tools"}],
        "provider_options_not_executed": [
            "Same-endpoint Responses with deepseek-v4-pro is the smallest official alternative, but current configure and complete_deepseek each hard-pin deepseek-flash; env-only replacement fails locally.",
            "Pro would require a narrowly reviewed model allowlist/config change, new frozen batch and actual protocol/capacity verification; no evidence yet that it fixes this violation.",
            "Do not simply switch to native Chat json_object: JSON validity is weaker than the current schema contract.",
            "Strict beta function output would require a dedicated output adapter and raw tool-call parsing; current response_choices rejects function_call outputs, so it is not a simple protocol toggle.",
            "Resolve final lake evidence visibility offline before more end-to-end calls; model replacement cannot restore omitted input.",
            "Stop prompt-only retries; keep a/b/c closed, retain actual usage and reject nonconforming originals."],
        "semantic_limits": ["cloud/phishing not_applicable inferred from absent evidence conflicts with undetermined guidance",
            "query did not provide relation fields cannot be a row-level claim when only query metadata was visible",
            "all structural gates passing on an in-memory diagnostic does not make those semantic claims correct"],
        "actions": "only offline original-file reads and official documentation browsing; no model/DB calls, no business source edits, no re-dispatch"}
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(OUTPUT.relative_to(ROOT)), "rejection": rejected,
        "schema_errors": errors, "query_row_fields_c4": len(c4_sources), "query_row_fields_c6": len(c6_sources)}))


if __name__ == "__main__":
    main()
