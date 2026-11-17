"""Direct checks of this frozen real Case snapshot; no database or model calls."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

folder = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


checks = []


def check(ok, label, identity=None):
    checks.append({"passed": bool(ok), "check": label, "id": identity})


cfg, expected, snapshot, source = (read(folder / name) for name in
    ("capture-config.json", "expected.json", "case-pg-01.json", "source-acceptance-01.json"))
prior = read(folder / cfg["prior_AI_snapshot"])["rows"]
rows = snapshot["rows"]
indexes = {table: {row["id"]: row for row in values} for table, values in rows.items()
           if table != "analysis_subject_state"}
artifacts, runs, steps, attempts = (indexes[k] for k in ("artifacts", "runs", "run_steps", "analysis_attempts"))
case_ids = set(cfg["case_ids"])
case_runs = {k: v for k, v in runs.items() if v["case_id"] in case_ids}
case_artifacts = {k: v for k, v in artifacts.items() if v["case_id"] in case_ids}
check(snapshot["identity"]["database"] == cfg["database"] and snapshot["identity"]["role"] == cfg["reader"]
      and snapshot["identity"]["ssl"] and snapshot["identity"]["readonly"] == "on", "ordinary_reader_current_candidate_tls")
check(snapshot["tenant_case_count"] == 2 and set(indexes["cases"]) == case_ids, "only_two_expected_cases")
check(len(case_runs) == 2, "two_initial_runs_no_retry_or_extra_run")
for table in ("alert_materials", "alert_source_refs", "alert_objects", "alert_assessments", "incident_alerts",
              "incident_diagnoses", "runs", "run_steps", "analysis_attempts", "artifacts"):
    for old in prior[table]:
        if old["id"] in indexes[table]:
            check(indexes[table][old["id"]] == old, "upstream_preserved_" + table, old["id"])
for aid, value in expected["prior_materials"].items():
    check(indexes["alerts"][aid]["latest_material_id"] == value["id"]
          and indexes["alert_materials"][value["id"]]["sha256"] == value["sha256"], "original_material_pointer", aid)
check(indexes["incidents"][cfg["incident_ids"][0]]["active_case_id"] == cfg["cases"]["event_case"]["case_id"],
      "single_case_did_not_steal_incident_receiver")
for f in case_artifacts.values():
    if f["content_json"] is not None:
        body = encoded(f["content_json"])
    elif f["content_text"] is not None:
        body = f["content_text"].encode()
    else:
        check(False, "artifact_has_saved_body", f["id"])
        continue
    check(hashlib.sha256(body).hexdigest() == f["sha256"] and len(body) == f["size_bytes"]
          and f["material_state"] == "complete", "artifact_hash_size_and_complete", f["id"])

run_map, model_usage, queries = [], [], []
for name, case in cfg["cases"].items():
    cid, members = case["case_id"], set(case["alert_ids"])
    check({r["alert_id"] for r in rows["case_alerts"] if r["case_id"] == cid} == members, "exact_case_members", cid)
    check({r["incident_id"] for r in rows["case_incidents"] if r["case_id"] == cid}
          == set(case["explicit_incident_ids"]), "exact_explicit_incidents", cid)
    task = indexes["analysis_tasks"][case["task_id"]]
    linked = [a for a in attempts.values() if a["task_id"] == task["id"]]
    check(task["state"] == "completed" and task["intent"] == "initial" and task["source"] == "case_create"
          and len(linked) == 1 and task["retry_count"] == 0, "initial_task_completed_without_retry", cid)
    attempt = linked[0]
    run = runs[attempt["run_id"]]
    rid = run["id"]
    check(run["case_id"] == cid and run["state"] == "completed" and attempt["outcome"] == "completed",
          "attempt_run_completed_and_bound", rid)
    saved = [f for f in case_artifacts.values() if f["run_id"] == rid]
    policy = artifacts[attempt["policy_artifact_id"]]["content_json"]
    check(policy["sha256"] == cfg["policy_sha256"], "current_case_policy_frozen", rid)
    contexts = [f for f in saved if f["schema_version"] == "socai2.baseline-context.v1"]
    check(len(contexts) == 1, "single_C1_context", rid)
    context = contexts[0]["content_json"]
    check(set(context["alerts"]) == members and set(context["scope"]["alert_ids"]) == members,
          "C1_exact_selected_members", rid)
    check(attempt["input_digest"] == digest(context["update_context"]["business_view"]), "attempt_frozen_business_digest", rid)
    comparison = context["update_context"]["comparison_context"]
    check(comparison["state"] == "initial" and comparison["previous_run_id"] is None
          and comparison["comparison_result_id"] is None and run["comparison_result_id"] is None,
          "initial_comparison_no_foreign_or_upstream_baseline", rid)
    for aid, item in context["alerts"].items():
        check(item["triage_usable"] is True and item["triage_freshness"] == "current"
              and item["triage"] == indexes["alert_assessments"][item["triage"]["id"]], "C1_usable_original_triage", aid)
        check(len(item["queries"]) == 3 and all(q["id"] in artifacts for q in item["queries"]), "C1_three_paired_A_receipts", aid)
    incident = context["incidents"][cfg["incident_ids"][0]]
    scope = incident["diagnosis_scope"]
    check(incident["linked_from_case"] == expected["cases"][name]["C1_incident_linked_from_case"]
          and incident["diagnosis_usable"], "C1_incident_context_and_link_role", rid)
    check(set(scope["input_selection"]["selected_alert_ids"]) == set(cfg["alert_ids"])
          and set(scope["analysis_coverage"]["covered_alert_ids"]) == set(cfg["alert_ids"])
          and set(scope["case_selected_alert_ids"]) == members
          and set(scope["case_covered_alert_ids"]) == members, "C1_original_I_scope_and_case_intersection", rid)
    if name == "single_A01_case":
        check("diagnosis_scope_extends_beyond_case" in incident["limitations"], "single_case_retains_scope_limitation", rid)
    run_steps = sorted([s for s in steps.values() if s["run_id"] == rid], key=lambda s: s["seq"])
    check(len(run_steps) == 17 and all(s["state"] in {"completed", "skipped"} for s in run_steps), "all_saved_steps_terminal", rid)
    models = [s for s in run_steps if s["kind"] == "model"]
    check([s["stage_code"] for s in models] == ["C3", "C6"], "actual_C3_C6_real_model_path", rid)
    for step in models:
        req, resp = (artifacts[step[k]]["content_json"] for k in ("input_artifact_id", "output_artifact_id"))
        originals = [f for f in saved if f["step_id"] == step["id"]
                     and (f.get("content_json") or {}).get("type") == "model_original_response"]
        check(len(originals) == 1 and originals[0]["content_json"]["raw"] == resp["payload"]["raw"], "model_raw_preserved_before_validation", step["id"])
        check(resp["payload"]["validation_error"] is None and resp["usage"]["usage_state"] == "reported", "model_structure_and_reported_usage", step["id"])
        sent = json.dumps(req["payload"]["body"], ensure_ascii=False)
        knowledge_in_body = [d["logical_id"] for d in read(folder / "knowledge-documents.json")["documents"] if d["request"]["content"] in sent]
        if step["stage_code"] == "C3":
            check(set(knowledge_in_body) == {"K1", "K2"}, "C3_received_actual_knowledge_texts", rid)
        model_usage.append({"run_id": rid, "step_id": step["id"], "stage": step["stage_code"],
                            "request_artifact_id": step["input_artifact_id"], "response_artifact_id": step["output_artifact_id"],
                            "original_artifact_id": originals[0]["id"], "knowledge_texts_in_body": knowledge_in_body,
                            "usage": resp["usage"], "finish_reasons": [x["finish_reason"] for x in resp["payload"]["raw"]["choices"]]})
    tool_receipts = [f for f in saved if f["kind"] == "tool_response"]
    knowledge = next(f["content_json"] for f in tool_receipts if f["content_json"]["tool_name"] == "knowledge")
    check(knowledge["state"] == "completed" and knowledge["returned_rows"] == (4 if name == "event_case" else 2), "Case_C2_actual_knowledge_nonempty", rid)
    for item in knowledge["rows"]:
        check(item["record_id"] in source["document_ids"].values() and set(item["query_alert_ids"]) <= members
              and item["applicability"]["state"] == "applicable", "C2_knowledge_document_and_scope", rid)
    selected_queries = []
    for f in tool_receipts:
        c = f["content_json"]
        if f["schema_version"] != "socai2.baseline-evidence.v1":
            continue
        args, wanted = c["actual_args"], expected["query_cases"][name]
        logical = wanted["included"][c["tool_name"]]
        check(c["state"] == "completed" and not c["truncated"] and c["returned_rows"] == 3
              and {r["event_id"] for r in c["rows"]} == {expected["event_ids"][v] for v in logical}, "C4_exact_selected_hits_and_exclusions", f["id"])
        check(args["parameters"]["tenant_id"] == cfg["tenant_id"] and args["parameters"]["hostname"] == wanted["hostname"]
              and set(args["parameters"]["alert_ids"]) == members, "C4_binding_tenant_host_members", f["id"])
        check(all(datetime.fromisoformat(args["scope"][k]) == datetime.fromisoformat(wanted[k])
                  for k in ("window_start", "window_end")), "C4_actual_member_window", f["id"])
        for item in c["rows"]:
            if item["event_id"] == expected["event_ids"]["E07"]:
                original = json.loads(item["ocsf_json"])
                check(original["traffic"]["bytes_out"] == 0 and original["sensor_observation"]["connection_reset"] is False
                      and original["sensor_observation"]["dns_answers"] == [], "C4_preserves_zero_false_empty", f["id"])
        selected_queries.append(c["tool_name"])
        queries.append({"run_id": rid, "artifact_id": f["id"], "tool_name": c["tool_name"], "query_id": c["query_id"],
                        "logical_events": logical, "actual_args": args, "returned_rows": c["returned_rows"]})
    results = [r for r in rows["results"] if r["source_run_id"] == rid]
    check(len(results) == 1, "one_saved_result_per_initial_run", rid)
    result = results[0]
    result_members = [r for r in rows["result_members"] if r["result_id"] == result["id"]]
    check({r["alert_id"] for r in result_members} == members and all(r["run_id"] == rid for r in result_members), "result_exact_members_and_run", rid)
    report = artifacts[result["report_artifact_id"]]
    check(report["run_id"] == rid and report["case_id"] == cid and report["content_json"]["result_id"] == result["id"]
          and report["content_json"]["conclusion"] == result["conclusion"], "report_result_same_run_and_conclusion", rid)
    check(artifacts[result["graph_artifact_id"]]["run_id"] == rid, "graph_same_run", rid)
    assessment = indexes["case_assessments"][indexes["cases"][cid]["current_assessment_id"]]
    check(assessment["conclusion"] == result["conclusion"] and assessment["origin"] == result["conclusion_origin"]
          and any(s["assessment_id"] == assessment["id"] and s["result_id"] == result["id"] for s in rows["case_assessment_sources"]), "adopted_assessment_matches_result", rid)
    check({m["alert_id"] for m in rows["case_assessment_members"] if m["assessment_id"] == assessment["id"]} == members, "adopted_assessment_exact_scope", rid)
    run_map.append({"label": name, "case_id": cid, "task_id": task["id"], "attempt_id": attempt["id"], "run_id": rid,
                    "result_id": result["id"], "assessment_id": assessment["id"], "member_ids": sorted(members),
                    "execution_state": run["state"], "delivery_state": result["delivery_state"],
                    "conclusion_state": result["conclusion_state"], "validation_state": result["validation_state"],
                    "C1_artifact_id": contexts[0]["id"], "input_artifact_id": run["input_artifact_id"],
                    "report_artifact_id": result["report_artifact_id"], "graph_artifact_id": result["graph_artifact_id"],
                    "step_ids": [s["id"] for s in run_steps], "artifact_ids": [f["id"] for f in saved],
                    "C4_selected_tools": selected_queries, "comparison_context": comparison})

failed = [c for c in checks if not c["passed"]]
summary = {"status": "passed" if not failed else "failed", "check_count": len(checks), "failed": failed,
           "snapshot_sha256": hashlib.sha256((folder / "case-pg-01.json").read_bytes()).hexdigest(), "checks": checks}
outputs = {"case-validation-01.json": summary,
           "actual-case-run-map-01.json": {"source": "real_postgres_snapshot", "cases": run_map},
           "case-model-usage-01.json": {"generation_calls": len(model_usage), "calls": model_usage, "cost": None},
           "case-log-queries-01.json": {"source": "actual_C4_saved_tool_receipts", "queries": queries}}
for name, value in outputs.items():
    with (folder / name).open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
print(json.dumps({k: v for k, v in summary.items() if k != "checks"}, ensure_ascii=False))
