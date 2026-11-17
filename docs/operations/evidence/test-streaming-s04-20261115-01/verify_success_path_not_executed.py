"""S04 saved-flow checks against one frozen snapshot; no service/model requests."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

folder = Path(__file__).resolve().parent

def read(name):
    return json.loads((folder / name).read_text())

def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()

def moment(value):
    return datetime.fromisoformat(value)

checks = []
def check(ok, label, identity=None):
    checks.append({"passed": bool(ok), "check": label, "id": identity})

cfg, expected, snap, baseline, ingress = (read(n) for n in
    ("capture-config.json", "expected.json", "analysis-pg-01.json", "case-initial-pg.json", "readback/identity-map.json"))
rows, old = snap["rows"], baseline["rows"]
idx = {t: {v["id"]: v for v in values} for t, values in rows.items() if t != "analysis_subject_state"}
old_ids = {t: {v["id"] for v in values} for t, values in old.items() if t != "analysis_subject_state"}
new = {t: [v for v in values if v["id"] not in old_ids.get(t, set())]
       for t, values in rows.items() if t != "analysis_subject_state"}
aid, iid = ingress["A04"]["alert_id"], expected["existing_incident_id"]
event_case, control = (v["case_id"] for v in expected["baseline_cases"])
members = set(cfg["alert_ids"])
artifacts, runs, steps = (idx[t] for t in ("artifacts", "runs", "run_steps"))
sha = hashlib.sha256((folder / "analysis-pg-01.json").read_bytes()).hexdigest()
check(snap["identity"]["database"] == cfg["database"] and snap["identity"]["role"] == cfg["reader"]
      and snap["identity"]["ssl"] and snap["identity"]["readonly"] == "on", "ordinary_reader_current_candidate_tls")
check(hashlib.sha256((folder / "case-initial-pg.json").read_bytes()).hexdigest() == cfg["prior_case_snapshot_sha256"], "frozen_initial_snapshot_unchanged")
check(snap["tenant_case_count"] == 2 and set(idx["cases"]) == {event_case, control}, "only_original_two_cases")
check(set(idx["alerts"]) == members and set(idx["incidents"]) == {iid}, "only_expected_subjects")
check({v["alert_id"] for v in rows["case_alerts"] if v["case_id"] == event_case} == members, "active_case_now_four_members")
check(idx["cases"][event_case]["scope_revision"] == 2 and idx["incidents"][iid]["active_case_id"] == event_case, "one_scope_extension_same_receiver")
check({v["alert_id"] for v in rows["incident_alerts"]} == members, "original_incident_four_members")

# Preserve every prior saved result, input, model raw and relationship, not only the latest pointer.
immutable = ("alert_materials", "alert_source_refs", "alert_objects", "alert_assessments", "incident_alerts",
             "incident_diagnoses", "case_alerts", "case_incidents", "case_assessments", "case_assessment_sources",
             "case_assessment_members", "analysis_tasks", "analysis_attempts", "runs", "run_steps", "run_members",
             "results", "result_members", "artifacts", "alerts")
preservation = {}
for table in immutable:
    missing, changed = [], []
    for before in old[table]:
        current = idx[table].get(before["id"])
        if current is None:
            missing.append(before["id"])
        elif current != before:
            changed.append(before["id"])
    preservation[table] = {"original_count": len(old[table]), "missing": missing, "changed": changed}
    check(not missing and not changed, "original_rows_preserved_" + table)
old_control = next(v for v in old["cases"] if v["id"] == control)
check(idx["cases"][control] == old_control, "single_A01_case_row_unchanged")
check(not any(t["subject_id"] == control for t in new["analysis_tasks"])
      and not any(r["case_id"] == control for r in new["runs"]), "single_A01_no_new_task_or_run")
for table in ("case_alerts", "case_incidents", "case_assessments"):
    check([v for v in rows[table] if v["case_id"] == control] == [v for v in old[table] if v["case_id"] == control], "control_unchanged_" + table)
for previous in old["analysis_subject_state"]:
    if previous["subject_id"] != control:
        continue
    current = next(v for v in rows["analysis_subject_state"] if v["subject_id"] == control)
    check({k:v for k,v in current.items() if k != "next_check_at"} == {k:v for k,v in previous.items() if k != "next_check_at"}, "control_only_periodic_clock_may_change")
for f in new["artifacts"]:
    body = encoded(f["content_json"]) if f["content_json"] is not None else (f["content_text"] or "").encode()
    check(hashlib.sha256(body).hexdigest() == f["sha256"] and len(body) == f["size_bytes"]
          and f["material_state"] == "complete", "new_artifact_hash_size_complete", f["id"])
for task in new["analysis_tasks"]:
    check(task["state"] in {"completed", "skipped", "merged"} and task["retry_count"] == 0,
          "natural_task_terminal_no_retry", task["id"])
    check(task["subject_id"] in {aid, iid, event_case}, "only_new_alert_original_I_active_Case_tasks", task["id"])
    check((task["source"], task["intent"]) == (("ingress", "initial") if task["subject_id"] == aid else ("periodic", "check")), "only_native_or_periodic_trigger", task["id"])
check(len([r for r in new["runs"] if r["alert_id"] == aid]) == 1, "one_A04_actual_analysis")
check(any(r["incident_id"] == iid for r in new["runs"]), "original_I_new_analysis_exists")
check(any(r["case_id"] == event_case for r in new["runs"]), "active_Case_new_analysis_exists")

run_map, model_calls, queries, quality, ordering = [], [], [], [], []
for run in sorted(new["runs"], key=lambda r: (r["started_at"] or "", r["id"])):
    rid = run["id"]
    attached = [a for a in rows["analysis_attempts"] if a["run_id"] == rid]
    check(len(attached) == 1, "one_attempt_per_run", rid)
    if not attached:
        continue
    attempt = attached[0]
    task = idx["analysis_tasks"][attempt["task_id"]]
    saved = [a for a in new["artifacts"] if a["run_id"] == rid]
    run_steps = sorted([s for s in rows["run_steps"] if s["run_id"] == rid], key=lambda s:s["seq"])
    source = artifacts[run["input_artifact_id"]]["content_json"]
    check(run["state"] == "completed" and attempt["outcome"] == "completed", "actual_run_and_attempt_completed", rid)
    check(all(s["state"] in {"completed", "skipped"} for s in run_steps), "saved_steps_terminal", rid)
    check(artifacts[attempt["policy_artifact_id"]]["content_json"]["sha256"] == cfg["policy_sha256"], "current_policy_frozen", rid)
    models = [s for s in run_steps if s["kind"] == "model"]
    check(bool(models), "real_model_step_exists", rid)
    for s in models:
        req, resp = (artifacts[s[k]]["content_json"] for k in ("input_artifact_id", "output_artifact_id"))
        request, response = req.get("payload", req), resp.get("payload", resp)
        raw = response.get("raw") or {}
        originals = [a for a in saved if a["step_id"] == s["id"] and
                     ((a.get("content_json") or {}).get("type") == "model_original_response"
                      or (a.get("content_json") or {}).get("artifact_role") == "model_original_response")]
        check(request.get("body", {}).get("messages") and request.get("body", {}).get("response_format")
              and bool(raw.get("id")), "real_request_schema_provider_response_saved", s["id"])
        check(len(originals) == 1 and originals[0]["content_json"]["raw"] == raw, "model_original_preserved", s["id"])
        check(response.get("validation_error") is None, "model_structure_accepted", s["id"])
        model_calls.append({"run_id":rid,"step_id":s["id"],"stage":s["stage_code"],"request_artifact_id":s["input_artifact_id"],
                            "response_artifact_id":s["output_artifact_id"],"original_artifact_ids":[v["id"] for v in originals],
                            "usage":s["usage"],"finish_reasons":[v.get("finish_reason") for v in raw.get("choices",[])]})
        quality.append({"run_id":rid,"step_id":s["id"],"response_artifact_id":s["output_artifact_id"],
                        "citation_review":response.get("citation_review"),"validation_error":response.get("validation_error"),
                        "prose_quality":"not_accepted_in_flow_test"})
    results = [v for t in ("alert_assessments", "incident_diagnoses", "results") for v in rows[t] if v.get("source_run_id") == rid]
    check(len(results) == 1, "one_saved_business_result", rid)
    record = {"run_id":rid,"task_id":task["id"],"attempt_id":attempt["id"],"kind":run["kind"],
              "subject_id":run["alert_id"] or run["incident_id"] or run["case_id"],"state":run["state"],
              "delivery_state":run["delivery_state"],"result_ids":[v["id"] for v in results],
              "input_artifact_id":run["input_artifact_id"],"policy_artifact_id":attempt["policy_artifact_id"],
              "step_ids":[v["id"] for v in run_steps],"artifact_ids":[v["id"] for v in saved]}
    if run["kind"] in {"alert_basic", "incident_diagnosis"}:
        expected_members = {aid} if run["alert_id"] else members
        check({m["alert"]["id"] for m in source["members"]} == expected_members, "AI_frozen_exact_members", rid)
        check(attempt["input_artifact_id"] == run["input_artifact_id"] and attempt["input_digest"] == digest(source.get("change_view",source)), "AI_frozen_input_pair", rid)
        for m in source["members"]:
            check(m["material"] == idx["alert_materials"][m["material"]["id"]], "AI_frozen_material_same_saved_original", rid)
        if run["incident_id"]:
            selection = source["input_selection"]
            check(set(selection["selected_alert_ids"]) == members and selection["selected_count"] == 4 and selection["omitted_count"] == 0, "I_actual_four_member_selection", rid)
            coverage = results[0]["diagnosis"]["delivery_assessment"]["member_coverage"] if results else {}
            check(set(coverage.get("expected_ids",[])) == members and set(coverage.get("analyzed_ids",[])) <= members, "I_coverage_not_expanded", rid)
            check(not any(s["kind"] == "tool" for s in run_steps), "I_consumes_A_receipts_no_new_query", rid)
            for mid, receipts in source.get("triage_queries",{}).items():
                valid = source["triage_validation"][mid]
                triage = next(m["triage"] for m in source["members"] if m["alert"]["id"] == mid)
                check(not valid["usable"] or (triage == idx["alert_assessments"].get(valid["triage_id"])), "I_usable_triage_matches_saved", mid)
                for receipt in receipts:
                    check(all(artifacts[receipt["id"]].get(k) == v for k,v in receipt.items())
                          and receipt["run_id"] == triage["source_run_id"], "I_paired_query_same_A_run", receipt["id"])
            record.update(selection=selection,triage_validation=source["triage_validation"],coverage=coverage)
        else:
            check(results and results[0]["input_material_id"] == ingress["A04"]["material_id"], "A04_triage_original_material", rid)
            tool_steps = [s for s in run_steps if s["kind"] == "tool"]
            check({s["name"] for s in tool_steps} == {"assets","history","threat_intel"} and len(tool_steps) == 3, "A04_three_real_query_steps", rid)
    else:
        check(run["kind"] == "baseline" and run["case_id"] == event_case, "only_active_Case_new_rounds", rid)
        contexts = [f for f in saved if f["schema_version"] == "socai2.baseline-context.v1"]
        check(len(contexts) == 1, "single_saved_C1", rid)
        if not contexts:
            continue
        context = contexts[0]["content_json"]
        check(set(context["alerts"]) == members and set(context["scope"]["alert_ids"]) == members, "C1_exact_four_members", rid)
        check(attempt["input_digest"] == digest(context["update_context"]["business_view"]), "C1_frozen_business_digest", rid)
        incident = context["incidents"][iid]
        diagnosis = incident["diagnosis"]
        scope = incident["diagnosis_scope"]
        check(incident["linked_from_case"] and incident["diagnosis_usable"] and incident["diagnosis_freshness"] == "current"
              and diagnosis == idx["incident_diagnoses"].get(diagnosis["id"]), "C1_current_usable_saved_new_I", rid)
        check(diagnosis["id"] not in old_ids["incident_diagnoses"] and set(scope["input_selection"]["selected_alert_ids"]) == members
              and aid in scope["analysis_coverage"]["covered_alert_ids"] and set(scope["case_selected_alert_ids"]) == members,
              "C1_uses_new_I_actual_scope_including_A04", rid)
        irun = runs[diagnosis["source_run_id"]]
        check(moment(run["started_at"]) >= moment(irun["ended_at"]) >= moment(diagnosis["generated_at"]), "I_saved_and_ended_before_Case_run", rid)
        earlier = sorted([r for r in runs.values() if r["case_id"] == event_case and r["id"] != rid and r["ended_at"]
                          and moment(r["ended_at"]) <= moment(run["started_at"])],key=lambda r:(r["started_at"],r["id"]))
        comp = context["update_context"]["comparison_context"]
        previous = earlier[-1]
        check(comp["previous_run_id"] == previous["id"], "comparison_own_immediate_previous_run", rid)
        previous_results = [v for v in rows["results"] if v["source_run_id"] == previous["id"]]
        check(comp["state"] == "eligible" and previous_results and comp["comparison_result_id"] == previous_results[0]["id"]
              and run["comparison_result_id"] == comp["comparison_result_id"]
              and source.get("comparison_context") == comp, "comparison_frozen_same_own_result", rid)
        previous_context = next(a["content_json"] for a in artifacts.values() if a["run_id"] == previous["id"] and a["schema_version"] == "socai2.baseline-context.v1")
        check(context["update_context"]["business_view"]["incidents"] != previous_context["update_context"]["business_view"]["incidents"], "new_I_business_view_changed", rid)
        check(results and results[0]["comparison_result_id"] == comp["comparison_result_id"], "result_saved_same_comparison", rid)
        for result in results:
            check({v["alert_id"] for v in rows["result_members"] if v["result_id"] == result["id"]} == members, "Case_result_four_members", rid)
            report = artifacts[result["report_artifact_id"]]
            check(report["run_id"] == rid and report["content_json"]["conclusion"] == result["conclusion"], "Case_report_same_run_conclusion", rid)
        record.update(C1_artifact_id=contexts[0]["id"],comparison_context=comp,incident_diagnosis_id=diagnosis["id"],
                      member_ids=sorted(members),result_states=[{k:v[k] for k in ("id","validation_state","conclusion_state","delivery_state","change_kind")} for v in results])
        ordering.append({"case_run_id":rid,"I_run_id":irun["id"],"I_diagnosis_id":diagnosis["id"],"I_generated_at":diagnosis["generated_at"],
                         "I_ended_at":irun["ended_at"],"Case_started_at":run["started_at"],"comparison":comp})
    for f in saved:
        if f["kind"] != "tool_response":
            continue
        c = f["content_json"]
        check(c["returned_rows"] == len(c.get("rows",[])), "query_actual_row_count", f["id"])
        entry = {"run_id":rid,"artifact_id":f["id"],"tool_name":c["tool_name"],"state":c["state"],"returned_rows":c["returned_rows"],"actual_args":c.get("actual_args")}
        if f["schema_version"] == "socai2.baseline-evidence.v1":
            args, wanted = c["actual_args"], expected["query_expectations"]["S04_full_host"]
            logical = read("dataset-manifest.json")["logical_ids"]
            check(set(args["parameters"]["alert_ids"]) == members, "C4_binding_selected_full_case", f["id"])
            check(all(moment(args["scope"][k]) == moment(wanted[k]) for k in ("window_start","window_end")), "C4_expanded_actual_window", f["id"])
            events = [v["event_id"] for v in c["rows"]]
            check(c["state"] == "completed" and not c["truncated"] and set(events) == {logical[e] for e in wanted["included"][c["tool_name"]]}, "C4_exact_expanded_hits_E11_E13_when_network_selected", f["id"])
            entry["event_ids"] = events
        queries.append(entry)
    run_map.append(record)

membership = [v for v in new["case_alerts"] if v["case_id"] == event_case and v["alert_id"] == aid]
check(len(membership) == 1, "one_A04_case_membership_added")
if membership:
    supporting = [v for v in new["incident_diagnoses"] if v["state"] == "completed"
                  and v["diagnosis"].get("validation_state") == "accepted"
                  and aid in v["diagnosis"]["delivery_assessment"]["member_coverage"].get("analyzed_ids",[])
                  and moment(v["generated_at"]) <= moment(membership[0]["added_at"])]
    check(bool(supporting), "A04_case_join_after_actual_usable_I_saved")
    ordering.append({"A04_case_added_at":membership[0]["added_at"],"preceding_usable_I_diagnosis_ids":[v["id"] for v in supporting]})
latest = idx["cases"][event_case]["current_assessment_id"]
assessment = idx["case_assessments"][latest]
check(latest not in old_ids["case_assessments"], "active_Case_adopted_new_assessment")
check({v["alert_id"] for v in rows["case_assessment_members"] if v["assessment_id"] == latest} == members, "adopted_assessment_four_member_scope")
sources = [v for v in rows["case_assessment_sources"] if v["assessment_id"] == latest]
check(len(sources) == 1 and idx["results"][sources[0]["result_id"]]["conclusion"] == assessment["conclusion"], "adopted_conclusion_matches_saved_result")
failed = [v for v in checks if not v["passed"]]
summary = {"status":"passed" if not failed else "failed","scope":"S04_real_saved_flow_only","snapshot_sha256":sha,
           "check_count":len(checks),"failed_checks":failed,"new_run_count":len(new["runs"]),"generation_calls":len(model_calls),"checks":checks}
outputs = {"analysis-validation-01.json":summary,"actual-analysis-map-01.json":{"status":summary["status"],"source":"real_saved_snapshot","snapshot_sha256":sha,
           "batch_id":cfg["batch_id"],"runs":run_map,"tasks":new["analysis_tasks"],"attempts":new["analysis_attempts"],"control_case_id":control},
           "upstream-preservation-01.json":{"status":"passed" if all(not v["missing"] and not v["changed"] for v in preservation.values()) else "failed","tables":preservation},
           "model-usage-01.json":{"generation_calls":len(model_calls),"calls":model_calls,"cost":None},
           "query-results-01.json":{"queries":queries},"ordering-and-comparison-01.json":{"records":ordering},
           "quality-findings-01.json":{"status":"quality_not_accepted","flow_only":True,"records":quality,"no_resampling":True}}
for name,value in outputs.items():
    with (folder/name).open("x") as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write("\n")
print(json.dumps({k:v for k,v in summary.items() if k != "checks"},ensure_ascii=False))
