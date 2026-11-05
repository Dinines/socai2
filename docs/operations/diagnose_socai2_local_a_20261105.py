"""Read-only replay of local batch a; no services, models or response repairs."""
import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api"))

from app.socai2 import baseline_analysis_contract as analysis
from app.socai2 import baseline_delivery_contract as delivery
from app.socai2.baseline_capacity import final_wire_reason
from app.socai2.baseline_context import Context
from app.socai2.baseline_model_view import SYSTEM
from app.socai2.baseline_store import digest, encoded
from jsonschema import Draft202012Validator
from pydantic import ValidationError

BATCH = ROOT / ".local/local-investigation/validation/local-maintenance-20261105a"
DEFAULT_DB = BATCH / "exports/20261105T102314778605Z/database.json"
DEFAULT_OUT = ROOT / "docs/operations/evidence/investigation-repair-20261105/local-a-diagnosis.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def diagnose(path):
    original_hash = sha(path)
    db = json.loads(path.read_text())
    steps = {s["id"]: s for s in db["run_steps"]}

    def artifact(stage, kind):
        row = next(a for a in db["artifacts"] if a["kind"] == kind
            and steps.get(a["step_id"], {}).get("stage_code") == stage)
        assert digest(row["content_json"]) == row["sha256"]
        return row

    req, rsp = artifact("C6", "model_request"), artifact("C6", "model_response")
    request = req["content_json"]["payload"]
    body = request["body"]
    response = rsp["content_json"]["payload"]["raw"]
    response_text = response["output"][0]["content"][0]["text"]
    raw = json.loads(response_text)
    view = json.loads(body["input"][1]["content"])
    run = next(r for r in db["runs"] if r["id"] == req["run_id"])
    context = Context.model_validate(next(a["content_json"] for a in db["artifacts"]
        if a["run_id"] == run["id"] and a["schema_version"] == "socai2.baseline-context.v1"))
    schema = body["text"]["format"]["schema"]
    errors = [{"path": list(e.absolute_path), "schema_path": list(e.absolute_schema_path),
        "validator": e.validator, "message": e.message}
        for e in Draft202012Validator(schema).iter_errors(raw)]
    assert len(errors) == 1 and errors[0]["path"] == ["analysis"]
    assert errors[0]["validator"] == "required" and "followups" in errors[0]["message"]
    assert response["text"]["format"]["schema"] == schema
    assert response["status"] == "completed" and response["incomplete_details"] is None
    try:
        delivery.Delivery.model_validate(raw)
    except ValidationError as exc:
        shape_errors = [{"path": list(e["loc"]), "type": e["type"], "message": e["msg"]}
            for e in exc.errors(include_url=False, include_input=False)]
    else:
        raise AssertionError("original response unexpectedly accepted by shape validator")
    try:
        delivery.parse(response_text, request["source_map"], context, view["members"], view["comparison"])
    except analysis.AnalysisRejected as exc:
        rejection = str(exc)
    else:
        raise AssertionError("original response unexpectedly accepted")
    assert rejection == "delivery_shape_invalid"

    findings = {f["id"]: f for f in raw["analysis"]["findings"]}
    scope_errors = [{"path": ["analysis", "domains", i, "alert_ids"], "domain": d["name"],
        "finding_id": fid, "declared_alert_ids": d["alert_ids"],
        "finding_alert_ids": findings[fid]["alert_ids"],
        "missing_alert_ids": sorted(set(findings[fid]["alert_ids"]) - set(d["alert_ids"]))}
        for i, d in enumerate(raw["analysis"]["domains"]) for fid in d["finding_ids"]
        if not set(findings[fid]["alert_ids"]) <= set(d["alert_ids"])]
    assert len(scope_errors) == 1 and scope_errors[0]["domain"] == "identity"
    # Diagnose the masked second gate in memory only. This is never a provider
    # response, never persisted as an answer, and must still be rejected.
    diagnostic = copy.deepcopy(raw)
    diagnostic["analysis"]["followups"] = []
    try:
        delivery.parse(json.dumps(diagnostic), request["source_map"], context, view["members"], view["comparison"])
    except analysis.AnalysisRejected as exc:
        secondary_rejection = str(exc)
    else:
        raise AssertionError("diagnostic variant unexpectedly accepted")
    assert secondary_rejection == "domain_finding_scope_mismatch"
    assert "followups" not in raw["analysis"]

    c3req, c3rsp = artifact("C3", "model_request"), artifact("C3", "model_response")
    c3 = c3req["content_json"]["payload"]
    c3view = json.loads(c3["body"]["input"][1]["content"])
    c3answer = json.loads(c3rsp["content_json"]["payload"]["raw"]["output"][0]["content"][0]["text"])
    material = next(a["content_json"] for a in db["artifacts"]
        if a["run_id"] == run["id"] and (a.get("content_json") or {}).get("type") == "materials")
    trials = []
    for bid, binding in sorted(material["catalog"]["bindings"].items()):
        option = {"binding_id": "B1", "tool_name": binding["tool_name"], "hostname": binding["hostname"],
            "alert_ids": binding["alert_ids"], "object_keys": sorted({o["object_key"] for o in binding["objects"]})}
        candidate = {**c3view, "tool_options": [option]}
        candidate_messages = copy.deepcopy(c3["body"]["input"])
        candidate_messages[1]["content"] = encoded(candidate).decode()
        trials.append({"binding_id": bid, "tool_name": binding["tool_name"],
            "view_bytes_with_one_option": len(encoded(candidate)),
            "messages_bytes_with_one_option": len(encoded(candidate_messages))})
    assert c3view["tool_options"] == [] and c3["binding_map"] == {}
    assert all(x["reason"] == "binding_catalog_input_limit" for x in c3["unoffered_bindings"])
    assert all(x["view_bytes_with_one_option"] > 8192 or x["messages_bytes_with_one_option"] > 12288 for x in trials)
    query_steps = [s for s in steps.values() if s["run_id"] == run["id"] and s["stage_code"] == "C4.query"]
    deep_steps = [s for s in steps.values() if s["run_id"] == run["id"] and s["stage_code"] == "C4.deep"]
    assert not query_steps and all(s["state"] == "skipped" for s in deep_steps)

    # New prompt measurement only; no provider dispatch. Keep original user
    # data, schema, output limit, and persisted final reservation identical.
    candidate_body = copy.deepcopy(body)
    candidate_body["input"][0]["content"] = SYSTEM + "\n" + delivery.PROMPT
    reservation = c3["final_reservation"]
    assert candidate_body["input"][1] == body["input"][1]
    assert candidate_body["text"] == body["text"]
    assert len(encoded(candidate_body["input"])) <= 12288
    assert len(candidate_body["input"][1]["content"].encode()) <= 8192
    assert final_wire_reason(candidate_body, reservation) is None
    assert sha(path) == original_hash
    source_paths = [Path(__file__), ROOT / "services/api/app/socai2/baseline_delivery_contract.py",
        ROOT / "services/api/app/socai2/baseline_analysis_contract.py",
        ROOT / "services/api/app/socai2/structured_output.py", ROOT / "services/api/app/socai2/model_protocol.py"]
    return {"kind": "offline_original_response_diagnosis_not_acceptance", "created_at": datetime.now(timezone.utc).isoformat(),
        "command": ".local/conda-envs/socai2/bin/python docs/operations/diagnose_socai2_local_a_20261105.py",
        "database": {"path": str(path.relative_to(ROOT)), "sha256_before": original_hash,
            "sha256_after": sha(path), "tables": len(db)}, "run_id": run["id"], "case_id": run["case_id"],
        "original_state": {k: run[k] for k in ("state", "stop_reason", "delivery_state", "limits")},
        "classification": {"immediate_failure": "model_output_contract_violation",
            "service": "completed_response_received; no transport/truncation/capacity failure at C6",
            "input_data": "required followups field and domain link scope do not depend on missing case facts",
            "code": "schema required followups; unchanged validator correctly rejects; prompt clarification only",
            "independent_design_gap": "C3 input packing removed every available query option; Deep reservation then blocked dispatch"},
        "c6": {"request_artifact_id": req["id"], "response_artifact_id": rsp["id"],
            "request_content_sha256": req["sha256"], "response_content_sha256": rsp["sha256"],
            "status": response["status"], "incomplete_details": response["incomplete_details"],
            "usage": response["usage"], "max_output_tokens": body["max_output_tokens"],
            "strict": body["text"]["format"]["strict"], "provider_echoed_schema_identical": True,
            "schema_errors": errors, "pydantic_errors": shape_errors, "original_rejection": rejection,
            "domain_scope_errors": scope_errors,
            "diagnostic_only": {"change": "in-memory analysis.followups=[] only; never saved or adopted",
                "rejection": secondary_rejection},
            "prompt_adherence": {"finding_count": len(findings), "requested_finding_max": 3,
                "finding_limit_is_prompt_only_not_schema_max": True}},
        "c3": {"request_artifact_id": c3req["id"], "response_artifact_id": c3rsp["id"],
            "offered_binding_count": 0, "unoffered_bindings": c3["unoffered_bindings"],
            "view_bytes": len(c3["body"]["input"][1]["content"].encode()), "single_option_trials": trials,
            "followups": c3answer["followups"], "actual_lake_query_steps": len(query_steps),
            "deep_steps": [{"id": s["id"], "state": s["state"], "error": s["error"]} for s in deep_steps]},
        "new_prompt_only_candidate": {"original_wire_bytes": len(encoded(body)),
            "candidate_wire_bytes": len(encoded(candidate_body)),
            "original_messages_bytes": len(encoded(body["input"])),
            "candidate_messages_bytes": len(encoded(candidate_body["input"])),
            "wire_delta_bytes": len(encoded(candidate_body)) - len(encoded(body)),
            "user_data_schema_and_max_output_unchanged": True,
            "final_wire_admission": final_wire_reason(candidate_body, reservation),
            "canonical_delivery_schema_sha256": digest(delivery.Delivery.model_json_schema()),
            "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in source_paths}},
        "limitations": ["no service/database/model calls; original database hash unchanged",
            "original response remains rejected; diagnostic variant remains rejected",
            "prompt clarification is not proof of model reliability; new independent batch required",
            "batch a is closed; no H and no retry; its five model attempts remain counted",
            "human followup links network activity to operator-0 without direct network-user attribution; review separately",
            "cloud/phishing not_applicable without coverage and shared-user claims need separate semantic review"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = diagnose(args.database.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "rejection": result["c6"]["original_rejection"],
        "second_gate": result["c6"]["diagnostic_only"]["rejection"],
        "wire_delta_bytes": result["new_prompt_only_candidate"]["wire_delta_bytes"]}))


if __name__ == "__main__":
    main()
