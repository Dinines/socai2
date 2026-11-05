"""Offline diagnosis of immutable local batch b; no sockets, models or repairs."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api"))

from app.socai2 import baseline_analysis_contract as contract
from app.socai2.baseline_analysis import budget_reason
from app.socai2.baseline_context import Context
from app.socai2.baseline_contracts import Limits
from app.socai2.baseline_store import digest, encoded
from jsonschema import Draft202012Validator

BATCH = ROOT / ".local/local-investigation/validation/local-maintenance-20261105b"
DATABASE = BATCH / "exports/20261105T104937427659Z/database.json"
OUTPUT = ROOT / "docs/operations/evidence/investigation-repair-20261105/local-b-diagnosis.json"


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    before = {str(p.relative_to(ROOT)): file_sha(p) for p in [DATABASE, BATCH / "plan.json"]}
    db = json.loads(DATABASE.read_text())
    run = next(r for r in db["runs"] if r["kind"] == "baseline")
    steps = [s for s in db["run_steps"] if s["run_id"] == run["id"]]
    artifacts = [a for a in db["artifacts"] if a["run_id"] == run["id"]]
    request = next(a for a in artifacts if a["kind"] == "model_request")
    response = next(a for a in artifacts if a["kind"] == "model_response")
    for a in (request, response):
        assert digest(a["content_json"]) == a["sha256"]
    p = request["content_json"]["payload"]
    body = p["body"]
    view = json.loads(body["input"][1]["content"])
    catalog = json.loads(body["input"][2]["content"])
    raw = response["content_json"]["payload"]["raw"]
    content = raw["output"][0]["content"][0]["text"]
    value = json.loads(content)
    context = Context.model_validate(next(a["content_json"] for a in artifacts
        if a["schema_version"] == "socai2.baseline-context.v1"))
    assert raw["status"] == "completed" and raw["incomplete_details"] is None
    assert not list(Draft202012Validator(body["text"]["format"]["schema"]).iter_errors(value))
    assert raw["text"]["format"]["schema"] == body["text"]["format"]["schema"]
    contract.ExecutionAnalysis.model_validate(value)
    try:
        contract.parse(content, p["source_map"], context, view["members"], bindings=p["binding_map"])
    except contract.AnalysisRejected as exc:
        rejection = str(exc)
    else:
        raise AssertionError("original response unexpectedly accepted")
    assert rejection == "followup_binding_object_mismatch"
    groups = catalog["tool_option_groups"]
    options = {o["binding_id"]: {**g, **o} for g in groups for o in g["options"]}
    assert set(options) == set(p["binding_map"]) and p["unoffered_bindings"] == []
    mapping_checks, followups = [], []
    for bid, binding in p["binding_map"].items():
        objects = sorted({o["object_key"] for o in binding["objects"]})
        assert set(options[bid]["alert_ids"]) == set(binding["alert_ids"])
        assert set(options[bid]["object_keys"]) == set(objects)
        assert options[bid]["hostname"] == binding["hostname"]
        assert options[bid]["tool_name"] == binding["tool_name"]
        mapping_checks.append({"alias": bid, "tool_name": binding["tool_name"],
            "member_count": len(binding["alert_ids"]), "allowed_object_types": [json.loads(o)[0] for o in objects],
            "visible_group_and_server_binding_identical": True})
    for index, item in enumerate(value["followups"]):
        binding = p["binding_map"][item["binding_id"]]
        allowed = {o["object_key"] for o in binding["objects"]}
        extra = set(item["object_keys"]) - allowed
        followups.append({"index": index, "mode": item["mode"], "question_id": item["question_id"],
            "binding_id": item["binding_id"], "tool_name": binding["tool_name"], "priority": item["priority"],
            "member_scope_matches": set(item["alert_ids"]) == set(binding["alert_ids"]),
            "declared_object_types": [json.loads(o)[0] for o in item["object_keys"]],
            "unexpected_objects": [{"type": json.loads(o)[0], "object_key_sha256": digest(o),
                "is_visible_case_object": o in context.scope.object_keys,
                "is_allowed_binding_object": o in allowed} for o in sorted(extra)],
            "error_path": ["followups", index, "object_keys"] if extra else None})
    assert len(followups) == 2 and not followups[0]["unexpected_objects"]
    assert len(followups[1]["unexpected_objects"]) == 1
    c3model = next(s for s in steps if s["stage_code"] == "C3" and s["kind"] == "model")
    limits = Limits.model_validate(run["limits"])
    admission = budget_reason([], limits, len(encoded(body)), datetime.fromisoformat(c3model["started_at"]),
        reserve_calls=1, reservation=p["final_reservation"])
    assert admission is None
    c6 = [s for s in steps if s["stage_code"] == "C6"]
    assert len(c6) == 1 and c6[0]["kind"] == "stage" and c6[0]["state"] == "skipped"
    assert c6[0]["error"]["code"] == "no_accepted_main_analysis"
    assert not any(s["stage_code"] in {"C4.query", "C4.deep"} for s in steps)
    assert len([s for s in db["run_steps"] if s["kind"] == "model"]) == 4
    paths = [ROOT / "services/api/app/socai2" / name for name in (
        "baseline_analysis.py", "baseline_analysis_contract.py", "baseline_tool_catalog.py", "structured_output.py")]
    plan = json.loads((BATCH / "plan.json").read_text())
    source_hashes = {str(p.relative_to(ROOT)): {"current": file_sha(p),
        "frozen_in_plan": plan["source_sha256"][str(p.relative_to(ROOT))]} for p in paths}
    assert all(v["current"] == v["frozen_in_plan"] for v in source_hashes.values())
    after = {p: file_sha(ROOT / p) for p in before}
    assert before == after
    result = {"kind": "offline_original_response_diagnosis_not_acceptance", "created_at": datetime.now(timezone.utc).isoformat(),
        "command": ".local/conda-envs/socai2/bin/python docs/operations/diagnose_socai2_local_b_20261105.py",
        "input_kind": "synthetic", "redaction": "no credentials, full prompts, hostname or IP values copied; object types and hashes only",
        "source_sha256_before": before, "source_sha256_after": after, "source_code": source_hashes,
        "run_id": run["id"], "case_id": run["case_id"], "run_state": run["state"], "run_stop_reason": run["stop_reason"],
        "request_artifact_id": request["id"], "request_artifact_sha256": request["sha256"],
        "response_artifact_id": response["id"], "response_artifact_sha256": response["sha256"],
        "provider": {"status": raw["status"], "incomplete_details": raw["incomplete_details"],
            "usage": raw["usage"], "max_output_tokens": body["max_output_tokens"],
            "saved_and_echoed_schema_identical": True, "json_schema_errors": [], "pydantic_shape_valid": True},
        "original_parser_rejection": rejection, "followup_checks": followups,
        "catalog": {"message_count": len(body["input"]), "group_count": len(groups),
            "offered_binding_count": len(options), "unoffered": p["unoffered_bindings"], "mapping_checks": mapping_checks,
            "causal_conclusion": "catalog exposure succeeded; model chose visible query aliases; no group or server mapping corruption"},
        "budget": {"facts_bytes": len(body["input"][1]["content"].encode()),
            "catalog_bytes": len(body["input"][2]["content"].encode()), "messages_bytes": len(encoded(body["input"])),
            "wire_bytes": len(encoded(body)), "reserved_current_upper_bound": p["reserved_token_upper_bound"],
            "final_conservative_units": p["final_reservation"]["conservative_units"], "run_max_tokens": limits.max_tokens,
            "admission_replay": admission, "reported_c3_tokens": raw["usage"]["total_tokens"],
            "remaining_after_c3": limits.max_tokens - raw["usage"]["total_tokens"]},
        "execution": {"batch_model_attempts": 4, "a_plus_b_model_attempts": 9, "global_authorized_cap": 50,
            "baseline_model_attempts": 1, "c6_model_attempts": 0, "deep_model_attempts": 0, "lake_query_steps": 0,
            "case_assessments": len(db["case_assessments"]),
            "c6_stage": {"state": c6[0]["state"], "reason": c6[0]["error"]["code"]}},
        "classification": {"immediate": "model output violates per-binding object scope",
            "service": "complete response received; no service/transport/truncation failure",
            "data": "destination IP is a valid case fact, but not an allowed query selector for this host-only binding",
            "code": "unchanged runtime scope validator correctly rejects; generic wire schema does not express binding-specific cross-field constraint",
            "c6": "not dispatched because C3 was rejected, not due C6 prompt or budget"},
        "repair_options_not_applied": [
            "Minimal prompt clarification: query.object_keys must copy only selected group's keys or be []; observed destination IP may remain in objective/evidence but is not an executable selector.",
            "Add original-response regression proving rejection and explicit host-only/empty query scope positives; keep runtime scope validation and fixed budget unchanged.",
            "Stronger future contract: encode binding-specific selector constraints in supported output schema; verify DeepSeek compatibility and full-wire capacity before adoption.",
            "Do not rewrite/retry b; any model validation must use a newly sealed independent batch and count all previous attempts."],
        "semantic_limits": ["network endpoints/other connections cannot prove authorization; second followup is supporting evidence only",
            "C3 shape and basic narratives are not a full-case accuracy pass; no accepted C3, C6 or H here",
            "no source edits, database/model calls or stored response modifications during diagnosis"]}
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(OUTPUT.relative_to(ROOT)), "rejection": rejection,
        "budget": result["budget"], "execution": result["execution"]}))


if __name__ == "__main__":
    main()
