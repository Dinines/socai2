"""Read-only independent checks of the one completed D2 real-02 batch."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
BATCH = ROOT / "docs/operations/evidence/quality-continuation-d2-20261116-01/real-02"
SOURCE = ROOT / "docs/operations/evidence/streaming-fullflow-20261116-01/final-pg.json"


def read(path):
    return json.loads(path.read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def main():
    source = read(SOURCE)["rows"]
    saved, terminal, calls = read(BATCH / "database.json"), read(BATCH / "result.json"), read(BATCH / "calls.json")
    mapping = read(BATCH / "source-mapping.json")
    checks = []

    def check(name, condition):
        assert condition, name
        checks.append(name)

    check("original_fixture_bytes_unchanged", hashlib.sha256(SOURCE.read_bytes()).hexdigest() ==
          "e4c3bdd0bd21d1c7fd730ad484623224242be2dbee4c6d5d88d05ab8193bcdc5")
    check("snapshot_same_after_driver_error", saved == read(BATCH / "snapshot.json"))
    check("original_driver_failure_retained", terminal["state"] == "failed" and
          terminal["error_type"] == "KeyError" and terminal["error"] == "'delivery'")
    expected_files = read(HERE.parent / "attempt-02/source-manifest.json")
    check("all_24_tested_sources_unchanged", all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == sha
                                               for p, sha in expected_files.items()))
    check("exactly_one_case_task_attempt_run_result", all(len(saved[t]) == 1 for t in
          ("cases", "analysis_tasks", "analysis_attempts", "runs", "results")))
    run, result, attempt = saved["runs"][0], saved["results"][0], saved["analysis_attempts"][0]
    check("same_run_completed_and_attempt_ended", run["id"] == terminal["run_id"] == result["source_run_id"] ==
          attempt["run_id"] and run["state"] == "completed" and run["stop_reason"] == "final_delivery_saved" and
          attempt["local_state"] == "ended" and attempt["outcome"] == "completed")
    check("three_actual_model_responses_no_substitute", [c["stage"] for c in calls] == ["C3", "Deep", "C6"] and
          all(c["state"] == "responded" and c["response"]["choices"][0]["finish_reason"] == "stop" for c in calls) and
          terminal["real_model_calls"] == 3 and terminal["substitute_model_calls"] == 0)
    check("all_saved_rows_belong_to_new_tenant", all(row["tenant_id"] == terminal["tenant_id"]
                                                  for table in saved.values() for row in table))
    check("exact_fixture_counts", len(mapping) == len(saved["alerts"]) == len(saved["alert_materials"]) == 4
          and len(saved["alert_objects"]) == 14)
    material_fields = ("raw_text", "raw_json", "ocsf_json", "detection", "enrichment", "source_scope",
                       "material_state", "sha256", "retention")
    object_fields = ("object_key", "object_type", "source_type", "object_role", "namespace", "raw_value",
                     "normalized_value", "source_path", "attributes", "asset_match_state", "asset_ref", "match_basis")
    for index, item in enumerate(mapping):
        old = next(r for r in source["alert_materials"] if r["id"] == item["source_material_id"])
        new = next(r for r in saved["alert_materials"] if r["id"] == item["material_id"])
        alert = next(r for r in saved["alerts"] if r["id"] == item["alert_id"])
        check(f"material_{index}_original_fields_and_new_ownership", new["alert_id"] == alert["id"] and
              alert["latest_material_id"] == new["id"] and all(new[k] == old[k] for k in material_fields))
        old_objects = [r for r in source["alert_objects"] if r["alert_id"] == item["source_alert_id"]]
        new_objects = [r for r in saved["alert_objects"] if r["alert_id"] == item["alert_id"]]
        check(f"objects_{index}_original_fields_and_new_ownership", len(old_objects) == len(new_objects) and all(
            any(all(old_object[k] == new_object[k] for k in object_fields) for old_object in old_objects)
            and new_object["material_id"] == new["id"] for new_object in new_objects))
    check("object_nulls_preserved_without_inventing_asset_match", all(o["match_basis"] is None and
          o["asset_ref"] is None and o["asset_match_state"] == "not_checked" for o in saved["alert_objects"]))
    members = {r["alert_id"] for r in saved["run_members"]}
    check("four_mapped_members_in_run_and_result", members == {m["alert_id"] for m in mapping} ==
          {r["alert_id"] for r in saved["result_members"]})

    artifacts = {a["id"]: a for a in saved["artifacts"]}
    requests = sorted((a for a in artifacts.values() if a["kind"] == "model_request"), key=lambda a: a["captured_at"])
    responses = sorted((a for a in artifacts.values() if a["kind"] == "model_response"), key=lambda a: a["captured_at"])
    check("three_requests_and_three_responses_saved", len(requests) == len(responses) == len(calls))
    qualities = []
    for request, response, call in zip(requests, responses, calls, strict=True):
        stage = call["stage"]
        payload = response["content_json"]["payload"]
        quality = payload["citation_review"]
        original = artifacts[quality["original_response_artifact_id"]]["content_json"]
        check(stage + "_actual_request_response_equal_saved_originals", request["content_json"]["payload"]["body"] ==
              call["request"] and payload["raw"] == original["raw"] == call["response"])
        check(stage + "_quality_separate_and_original_hash_kept", quality["original_sha256"] ==
              digest(call["response"]["choices"][0]["message"]["content"]) and
              quality["prose_quality"] == "not_checked" and quality["conclusion_modified"] is False)
        check(stage + "_backend_tenant_not_sent", "tenant_uid" not in json.dumps(call["request"], ensure_ascii=False))
        qualities.append({"stage": stage, "state": quality["state"], "issues": quality["issues"],
                          "prose_quality": quality["prose_quality"]})

    full = next(a["content_json"] for a in artifacts.values()
                if (a["content_json"] or {}).get("type") == "delivery_report")
    core = artifacts[result["report_artifact_id"]]["content_json"]
    raw_final = json.loads(calls[-1]["response"]["choices"][0]["message"]["content"])
    derived = responses[-1]["content_json"]["payload"]["derived"]
    check("current_report_contract_keeps_full_and_core_separate", "delivery" in full and "delivery" not in core
          and core["result_id"] == full["result_id"] == result["id"])
    check("original_final_conclusion_state_and_limits_kept", result["conclusion"] == raw_final["conclusion"]["text"] ==
          derived["conclusion"]["text"] == full["delivery"]["conclusion"]["text"] == core["conclusion"] and
          result["conclusion_state"] == raw_final["conclusion"]["state"] == derived["conclusion"]["state"] and
          full["delivery"]["conclusion"]["limitations"] == derived["conclusion"]["limitations"] ==
          raw_final["conclusion"]["limitations"])
    for key in ("title", "conclusion", "closing_note", "findings", "questions", "recommendations", "case_impact"):
        check("report_core_matches_saved_" + key, core[key] == result[key] == full["result"][key])
    check("quality_records_same_in_response_full_report_core", core["citation_review"] == full["citation_review"] ==
          responses[-1]["content_json"]["payload"]["citation_review"])
    gaps = [i for i in qualities[-1]["issues"] if i["code"] == "unapplied_domain_needs_limitations"]
    check("real_final_two_explanation_gaps_retained", len(gaps) == 2 and all(
          i["category"] == "explanation_completeness" and i["action"] == "retain_judgment" for i in gaps))
    check("raw_domain_judgments_and_empty_limits_kept", all(
          (a["name"], a["applicability"], a["reason"], a["limitations"]) ==
          (b["name"], b["applicability"], b["reason"], b["limitations"])
          for a, b in zip(raw_final["analysis"]["domains"], full["delivery"]["analysis"]["domains"], strict=True)))
    aliases = requests[-1]["content_json"]["payload"]["case_boundary"]["member_aliases"]
    restored = {alias: aid for aid, alias in aliases.items()}
    check("final_scope_restored_from_same_request_without_expansion", derived["conclusion"]["alert_ids"] ==
          full["delivery"]["conclusion"]["alert_ids"] == [restored[a] for a in raw_final["conclusion"]["alert_ids"]])
    check("real_deep_and_final_inputs_keep_prior_quality_note", all(
          "其引用存在质量问题，不能视为已核实事实。" in "\n".join(
              m["content"] for m in call["request"]["messages"] if isinstance(m.get("content"), str))
          for call in calls[1:]))
    check("accepted_does_not_mean_quality_or_complete_delivery", result["validation_state"] == "accepted" and
          result["conclusion_state"] == "uncertain" and result["delivery_state"] == "partial")
    files = [BATCH / name for name in ("database.json", "snapshot.json", "calls.json", "result.json", "source-mapping.json")]
    review = {"status": "saved_model_and_database_evidence_passed", "checks": checks, "check_count": len(checks),
              "run_id": run["id"], "case_id": result["case_id"], "result_id": result["id"], "model_calls": 3,
              "quality": qualities, "artifact_count": len(artifacts), "step_count": len(saved["run_steps"]),
              "original_driver_result": "failed: KeyError delivery (retained)", "http_status": "separate_readback_required",
              "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
              "reviewer_network_calls": 0, "reviewer_database_calls": 0, "reviewer_model_calls": 0}
    (HERE / "database-review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": review["status"], "checks": len(checks), "model_calls": 3,
                      "quality_codes": {q["stage"]: [i["code"] for i in q["issues"]] for q in qualities}}))


if __name__ == "__main__":
    main()
