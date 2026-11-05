"""Read three sealed local exports; verify the chain and retain quality failures.

Offline only. No service, database, model, or business-record writes.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".local/local-investigation/validation"
OUT = ROOT / "docs/operations/evidence/investigation-repair-20261105/local-comparison-summary.json"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(index):
    batch = f"local-eval-20261105-{index:02d}"
    folder = BASE / batch
    exported = max((folder / "exports").iterdir())
    plan, oracle = read(folder / "plan.json"), read(folder / "expected.json")
    manifest, data = read(exported / "manifest.json"), read(exported / "database.json")
    for source in manifest["sources"]:
        assert sha(exported / source["file"]) == source["sha256"]
    assert len(data) == 29
    assert len(data["alerts"]) == len(data["alert_materials"]) == 2
    expected = {a["source_alert_id"]: a for a in plan["case"]["alerts"]}
    for material in data["alert_materials"]:
        raw = material["raw_json"]
        source = expected[raw["source_alert_id"]]
        assert raw["raw_event"] == source["raw_event"]
        assert material["ocsf_json"] == source["raw_event"]["ocsf_event"]
        assert material["retention"]["truncated"] is False
        assert material["source_scope"]["complete"] is True
    lake = read(folder / "lake-readback.json")
    assert lake["passed"] and len(lake["rows"]) == 2
    case, assessment, result = (data[k][0] for k in ("cases", "case_assessments", "results"))
    assert case["current_assessment_id"] == assessment["id"]
    assert case["description"] == plan["case"]["description"]
    assert assessment["conclusion"] == result["conclusion"]
    assert assessment["origin"] == result["conclusion_origin"] == "model"
    assert assessment["validity"] == result["validation_state"] == "accepted"
    assert len(data["case_assessment_members"]) == len(data["result_members"]) == 2
    api = read(exported / "api-responses.json")
    assert all(r["status"] == 200 for r in api)
    current = api[0]["body"]["current_assessment"]
    assert current["value"]["conclusion"] == assessment["conclusion"]
    assert current["covers_current_members"] and current["input_freshness"]["state"] == "current"
    artifacts = {a["id"]: a for a in data["artifacts"]}
    graph = artifacts[result["graph_artifact_id"]]["content_json"]
    models, queries = [], []
    for step in data["run_steps"]:
        if step["kind"] == "model":
            response = artifacts[step["output_artifact_id"]]["content_json"]
            payload = response.get("payload") or response
            assert payload["raw"]["status"] == "completed"
            models.append({"stage": step["stage_code"], "step_id": step["id"], "state": step["state"],
                "provider_status": payload["raw"]["status"], "validation_error": payload.get("validation_error"),
                "response_artifact_id": step["output_artifact_id"], "usage": step["usage"]})
        if step["stage_code"] == "C4.query":
            output = artifacts[step["output_artifact_id"]]["content_json"]
            ids = sorted(row["event_id"] for row in output["rows"])
            assert ids == sorted(oracle["tool_expected_event_ids"][output["tool_name"]])
            queries.append({"tool": output["tool_name"], "rows": output["returned_rows"], "event_ids": ids,
                "ids_match_frozen_oracle": True, "artifact_id": step["output_artifact_id"]})
    assert len(models) == 5
    assert next(m for m in models if m["stage"] == "C6")["state"] == "completed"
    baseline = next(r for r in data["runs"] if r["kind"] == "baseline")
    assert baseline["state"] == "completed"
    return {"batch": batch, "scenario": plan["case"]["scenario"], "expected_intent": oracle["behavior_truth"],
        "expected_scope": oracle["truth_scope"], "case_id": case["id"],
        "page": "http://127.0.0.1:4174/#/cases/" + "!".join(("socai2", "local-standalone", batch,
            plan["tenant_id"], "case", case["id"])) + "/case-info",
        "export": str(exported.relative_to(ROOT)), "database_sha256": manifest["source_sha256"],
        "plan_sha256": sha(folder / "plan.json"), "table_counts": manifest["table_counts"],
        "input_originals_exact": True, "lake_rows": 2, "queries": queries,
        "models": models, "baseline_run_id": baseline["id"], "conclusion": assessment["conclusion"],
        "result_validation": result["validation_state"], "conclusion_state": result["conclusion_state"],
        "delivery_state": result["delivery_state"], "current_member_coverage": 2,
        "input_freshness": current["input_freshness"],
        "graph": {"nodes": len(graph["nodes"]), "edges": len(graph["edges"])},
        "c2_sources": [{"name": s["name"], "state": s["state"], "rows": s["returned_rows"], "error": s["error"]}
            for s in data["run_steps"] if s["stage_code"] == "C2" and s["kind"] == "tool"]}


def main():
    cases = [inspect(i) for i in (1, 2, 3)]
    result = {
        "scope": "Frozen synthetic scenario comparison; real local Kafka/Fusion/PG/CH and DeepSeek, original page template",
        "new_model_attempts": 15, "previous_model_attempts": 33, "global_attempts": 48, "global_cap": 50,
        "protocol": "deepseek_responses", "model": "deepseek-flash", "remote_deployed_model_tested": False,
        "all_provider_responses_complete": True, "all_three_model_case_conclusions_saved": True,
        "overall_quality_passed": False, "human_followup_tested_this_batch": False,
        "source_format": "Fusion source-v1 and existing normalized envelope; not full OCSF specification certification",
        "cases": cases,
        "quality_findings": [
            {"case": "01", "severity": "medium", "finding": "Routine intent produced needs_review/uncertain; missing authorization/completion makes abstention permissible, not a correct-benign measurement."},
            {"case": "01", "severity": "high", "finding": "A1 describes actual copying from process_start only. C6 main conclusion narrows this, but insider domain incorrectly calls an unverified/internal-labelled UNC destination external."},
            {"case": "02", "severity": "medium", "finding": "Dump-and-archive pattern recognized as sensitive, still uncertain. PID 688 identity and dump contents absent; lsass naming cannot establish successful credential theft. Risk prioritization remains weak."},
            {"case": "03", "severity": "high", "finding": "Accepted C6 falsely claims successful shadow deletion, encryption and note creation. Source proves process start and one file rename only. Output validation failed to block factual inflation."},
            {"case": "03", "severity": "medium", "finding": "A1 direct-basis role, I F5 member-scope coverage and C3 observed/source-label checks rejected responses. Provider returned completed; no retry. C6 still executed and was adopted."},
            {"case": "01/02", "severity": "medium", "finding": "Cloud/phishing marked not_applicable from missing source coverage; should remain undetermined under current guidance."},
            {"case": "all", "severity": "medium", "finding": "Asset/SOP seeds and PG title search verified, but C2 knowledge skipped to reserve evidence-tool budget. Do not claim these runs consumed SOP."},
            {"case": "all", "severity": "medium", "finding": "Case severity/classification/management status remain unrecorded/unset/new; narrative model conclusion does not automatically populate management fields."},
        ],
        "checks": {"driver_and_backend_offline": 30, "original_readback_tests": 31,
            "readback_first_run": "30 passed, 1 failed because old test assumed every A result had a saved explanation. Updated to require the actual saved pointer and verify absence after rejection; rerun 31 passed.",
            "rendered": ["three Case info pages", "02 and 03 graph", "03 original alert", "three filtered Case list"],
            "screenshot": "docs/operations/evidence/investigation-repair-20261105/local-comparison-cases.png"},
        "limitations": ["Three constructed two-alert examples do not measure population accuracy.",
            "Same username and sequential ingestion allow earlier synthetic history to appear in later A-stage context; no oracle was sent.",
            "01 queries network/authentication (empty); 02 queries process (2 rows) and network (empty); 03 has no C4 queries after rejected C3.",
            "Initial 01 sandbox preflight connection permission failure preceded any mutation; approved local-network preflight passed with zero model calls.",
            "No original model answer, prior sealed batch or business assessment has been rewritten to improve the comparison."]}
    with OUT.open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"receipt": str(OUT), "cases": len(cases), "model_attempts": 15, "quality_passed": False}))


if __name__ == "__main__":
    main()
