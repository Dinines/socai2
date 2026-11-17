"""Verify actual S04 failure preservation and stopping; never claim the success path passed."""
import hashlib
import json
from pathlib import Path

folder = Path(__file__).resolve().parent
read = lambda n: json.loads((folder / n).read_text())
def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()
checks = []
def check(ok, label, identity=None):
    checks.append({"passed": bool(ok), "check": label, "id": identity})

snap, base, cfg, mapping, ingress = (read(n) for n in
    ("analysis-pg-01.json", "case-initial-pg.json", "capture-config.json", "actual-analysis-map-01.json", "readback/identity-map.json"))
r, old = snap["rows"], base["rows"]
idx = {t:{v["id"]:v for v in x} for t,x in r.items() if t != "analysis_subject_state"}
oldids = {t:{v["id"] for v in x} for t,x in old.items() if t != "analysis_subject_state"}
new = {t:[v for v in x if v["id"] not in oldids.get(t,set())] for t,x in r.items() if t != "analysis_subject_state"}
aid, iid = ingress["A04"]["alert_id"], ingress["A04"]["incident_id"]
sha = hashlib.sha256((folder/"analysis-pg-01.json").read_bytes()).hexdigest()
check(mapping["snapshot_sha256"] == sha, "actual_map_same_final_snapshot")
check(hashlib.sha256((folder/"case-initial-pg.json").read_bytes()).hexdigest() == cfg["prior_case_snapshot_sha256"], "original_snapshot_digest_unchanged")
who = snap["identity"]
check(who["database"] == cfg["database"] and who["role"] == cfg["reader"] and who["readonly"] == "on" and who["ssl"], "real_candidate_ordinary_reader_TLS_readonly")
check(set(idx["alerts"]) == set(cfg["alert_ids"]) and set(idx["incidents"]) == {iid}, "only_expected_subjects")
check(snap["tenant_case_count"] == 2 and set(idx["cases"]) == set(cfg["case_ids"]), "no_new_case")

preserved = {}
for t in oldids:
    if t in {"incidents", "alerts"}:
        continue
    missing = [v["id"] for v in old[t] if v["id"] not in idx[t]]
    changed = [v["id"] for v in old[t] if v["id"] in idx[t] and idx[t][v["id"]] != v]
    preserved[t] = {"original_count":len(old[t]),"missing":missing,"changed":changed}
    check(not missing and not changed, "all_original_records_preserved_"+t)
check(all(idx["alerts"][v["id"]] == v for v in old["alerts"]), "original_three_alert_rows_unchanged")
check(idx["incidents"][iid]["latest_diagnosis_id"] == old["incidents"][0]["latest_diagnosis_id"], "old_I_pointer_retained_not_replaced_by_failure")
check({v["alert_id"] for v in r["incident_alerts"]} == set(cfg["alert_ids"]), "I_four_actual_members")
for table in ("cases", "case_alerts", "case_incidents", "case_assessments", "case_assessment_sources", "case_assessment_members", "results", "result_members", "run_members"):
    check(r[table] == old[table], "entire_two_Case_table_unchanged_"+table)
check(not any(v["case_id"] for v in new["runs"]) and not any(v["subject_type"] == "case" for v in new["analysis_tasks"]), "no_Case_task_run_or_comparison_after_failed_I")
for subject in old["analysis_subject_state"]:
    if subject["subject_type"] != "case":
        continue
    current = next(v for v in r["analysis_subject_state"] if v["subject_id"] == subject["subject_id"])
    check({k:v for k,v in current.items() if k != "next_check_at"} == {k:v for k,v in subject.items() if k != "next_check_at"}, "Case_only_periodic_clock_changed", subject["subject_id"])

# The source material and direct reference are the actual ingress records, not reconstructed results.
ingress_rows = read("readback/alerts-pg.json")["rows"]
for table in ("alert_materials", "alert_source_refs", "alert_objects", "incident_alerts"):
    selected = [v for v in ingress_rows[table] if v.get("alert_id") == aid]
    check(all(idx[table].get(v["id"]) == v for v in selected) and bool(selected), "A04_ingress_original_preserved_"+table)
check(len(new["analysis_tasks"]) == 5 and len(new["analysis_attempts"]) == len(new["runs"]) == 2, "actual_five_tasks_two_attempts_runs")
check(all(v["retry_count"] == 0 and v["state"] in {"completed","failed","skipped"} for v in new["analysis_tasks"]), "all_terminal_zero_retries")
a_task = idx["analysis_tasks"][ingress["A04"]["task_id"]]
i_task = next(v for v in new["analysis_tasks"] if v["state"] == "failed")
check(a_task["state"] == "completed" and a_task["source"] == "ingress" and a_task["intent"] == "initial", "original_A04_initial_completed")
check(i_task["subject_id"] == iid and i_task["source"] == "periodic" and i_task["intent"] == "check"
      and i_task["reason_code"] == "model_response_not_complete", "natural_I_check_failed_explicitly")
skips = [v for v in new["analysis_tasks"] if v["state"] == "skipped"]
check(len(skips) == 3 and all(v["reason_code"] == "automatic_attempts_stopped" and v["started_at"] is None
      and not any(a["task_id"] == v["id"] for a in new["analysis_attempts"]) for v in skips), "three_waiting_checks_skipped_without_attempt")
state = next(v for v in r["analysis_subject_state"] if v["subject_id"] == iid)
check(state["automatic_stop_reason"] == "model_response_not_complete" and state["stopped_task_id"] == i_task["id"]
      and state["stopped_input_digest"] == i_task["observed_input_digest"], "I_same_input_automatic_stop_saved")
check(state["last_completed_attempt_id"] == next(v for v in old["analysis_subject_state"] if v["subject_id"] == iid)["last_completed_attempt_id"], "failed_attempt_did_not_replace_last_success")

artifacts = idx["artifacts"]
for f in new["artifacts"]:
    b = encoded(f["content_json"]) if f["content_json"] is not None else (f["content_text"] or "").encode()
    check(hashlib.sha256(b).hexdigest() == f["sha256"] and len(b) == f["size_bytes"] and f["material_state"] == "complete", "new_artifact_original_hash_size_complete", f["id"])
queries, quality = [], []
for actual in mapping["runs"]:
    run = idx["runs"][actual["run_id"]]
    rid = run["id"]
    attempt = idx["analysis_attempts"][actual["attempt_id"]]
    source = artifacts[run["input_artifact_id"]]["content_json"]
    is_I = run["kind"] == "incident_diagnosis"
    wanted = set(cfg["alert_ids"]) if is_I else {aid}
    check(attempt["local_state"] == "ended" and attempt["attempt_no"] == 1 and not attempt["retryable"], "single_ended_nonretryable_attempt", rid)
    check(artifacts[attempt["policy_artifact_id"]]["content_json"]["sha256"] == cfg["policy_sha256"], "actual_current_policy_snapshot", rid)
    check(attempt["input_artifact_id"] == run["input_artifact_id"] and attempt["input_digest"] == digest(source.get("change_view", source)), "frozen_attempt_input_digest", rid)
    check({v["alert"]["id"] for v in source["members"]} == wanted, "actual_frozen_members", rid)
    for member in source["members"]:
        check(member["material"] == idx["alert_materials"][member["material"]["id"]], "frozen_original_material", member["alert"]["id"])
    check(len(actual["models"]) == 1, "one_real_generation_no_resampling", rid)
    for model in actual["models"]:
        req = artifacts[model["request_artifact_id"]]["content_json"]
        resp = artifacts[model["response_artifact_id"]]["content_json"]
        raw = resp["raw"]
        check(req["body"]["messages"] and req["body"]["response_format"] and req["body"]["max_tokens"] == 3000
              and req["model"] == "aisoc-investigation", "actual_request_prompt_schema_and_current_I_A_limit", model["step_id"])
        check(len(model["original_artifact_ids"]) == 1 and artifacts[model["original_artifact_ids"][0]]["content_json"]["raw"] == raw
              and bool(raw["id"]), "actual_provider_raw_unchanged", model["step_id"])
        check(model["usage"]["usage_state"] == "reported" and model["usage"]["cost"] is None, "usage_reported_unknown_cost_not_zero", model["step_id"])
        quality.append({"run_id":rid,"step_id":model["step_id"],"original_artifact_ids":model["original_artifact_ids"],
                        "finish_reasons":model["finish_reasons"],"citation_review":resp.get("citation_review"),"validation_error":resp["validation_error"],
                        "prose_quality":"NOT_PASSED", "no_resampling":True})
        if is_I:
            check(model["finish_reasons"] == ["length"] and model["usage"]["output_tokens"] == req["body"]["max_tokens"]
                  and resp["validation_error"] == "model_response_not_complete", "real_I_output_truncated_not_network_unknown")
            try:
                json.loads(raw["choices"][0]["message"]["content"])
                incomplete = False
            except json.JSONDecodeError:
                incomplete = True
            check(incomplete, "incomplete_raw_JSON_preserved_not_repaired")
        else:
            check(model["finish_reasons"] == ["stop"] and resp["validation_error"] is None, "A04_structure_completed_separate_from_quality")
    tool_steps = [v for v in new["run_steps"] if v["run_id"] == rid and v["kind"] == "tool"]
    if is_I:
        selection = source["input_selection"]
        check(set(selection["selected_alert_ids"]) == wanted and selection["selected_count"] == 4 and selection["omitted_count"] == 0, "I_four_selected_not_three_old_members")
        check(not tool_steps, "I_consumes_A_receipts_no_new_queries")
        for mid, receipts in source["triage_queries"].items():
            valid = source["triage_validation"][mid]
            triage = next(v["triage"] for v in source["members"] if v["alert"]["id"] == mid)
            check(valid["usable"] and valid["triage_id"] == triage["id"] and triage == idx["alert_assessments"][triage["id"]], "I_four_real_usable_triages", mid)
            check(len(receipts) == 3, "I_three_paired_A_queries", mid)
            for receipt in receipts:
                check(all(artifacts[receipt["id"]].get(k) == v for k,v in receipt.items()) and receipt["run_id"] == triage["source_run_id"], "I_query_receipt_same_saved_A_run", receipt["id"])
        diagnosis = idx["incident_diagnoses"][actual["result_ids"][0]]
        check(run["state"] == attempt["outcome"] == diagnosis["state"] == "failed" and run["delivery_state"] == "none"
              and run["stop_reason"] == attempt["error_code"] == diagnosis["error"]["code"] == "model_response_not_complete", "I_failure_consistent_task_attempt_run_diagnosis")
        check(diagnosis["diagnosis"] is None and diagnosis["summary"] is None and diagnosis["generated_at"] is None, "failed_I_no_fabricated_usable_conclusion")
    else:
        check(run["state"] == attempt["outcome"] == "completed" and run["delivery_state"] == "complete", "A04_real_flow_completed")
        result = idx["alert_assessments"][actual["result_ids"][0]]
        check(result["input_material_id"] == ingress["A04"]["material_id"] and idx["alerts"][aid]["latest_triage_id"] == result["id"], "A04_saved_triage_and_pointer")
        quality.append({"alert_id":aid,"assessment_id":result["id"],"rationale":result["rationale"],"rationale_quality":"NOT_PASSED_single_character","no_resampling":True})
        check({v["name"] for v in tool_steps} == {"assets","history","threat_intel"} and len(tool_steps) == 3, "A04_three_actual_queries")
        for step in tool_steps:
            f = artifacts[step["output_artifact_id"]];b = f["content_json"]
            check(b["state"] == "completed" and b["returned_rows"] == len(b["rows"])
                  and b["actual_args"]["scope"]["alert_ids"] == [aid], "A04_real_query_scope_and_count", f["id"])
            for value in b["rows"]:
                if b["tool_name"] == "history" and value["record"].get("triage"):
                    triage = value["record"]["triage"]
                    check(triage == idx["alert_assessments"].get(triage["id"]), "history_triage_actual_saved_record", f["id"])
            queries.append({"run_id":rid,"artifact_id":f["id"],"tool_name":b["tool_name"],"state":b["state"],"returned_rows":b["returned_rows"],"record_ids":[v["record_id"] for v in b["rows"]],"actual_args":b["actual_args"]})

failed = [v for v in checks if not v["passed"]]
summary = {"status":"passed" if not failed else "failed","meaning":"failure_record_and_stop_integrity_only","S04_success_path":"NOT_PASSED",
           "snapshot_sha256":sha,"check_count":len(checks),"failed_checks":failed,"checks":checks}
outputs = {"failure-record-validation-01.json":summary,
           "upstream-preservation-01.json":{"status":"passed" if all(not v["missing"] and not v["changed"] for v in preserved.values()) else "failed","snapshot_sha256":sha,"tables":preserved},
           "query-results-01.json":{"actual_queries":queries,"C4_queries":[],"reason":"no_Case_update_Run_after_failed_I"},
           "quality-findings-01.json":{"status":"NOT_PASSED","flow_blocker":"I_real_response_truncated","model_calls":2,"records":quality,
                                       "previous_quality_records_preserved":True,"no_resampling":True}}
for name, value in outputs.items():
    with (folder/name).open("x") as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write("\n")
print(json.dumps({k:v for k,v in summary.items() if k != "checks"},ensure_ascii=False))
