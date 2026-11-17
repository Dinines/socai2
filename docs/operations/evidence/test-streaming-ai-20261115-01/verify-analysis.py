"""Verify the saved real snapshot offline; never fetch, repair, or replay."""
import hashlib
import json
from pathlib import Path

folder = Path(__file__).resolve().parent
prior = folder.parent / "test-streaming-s01-ingress-20261115-02"


def read(path):
    return json.loads(path.read_text())


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


checks = []


def check(ok, label, identity=None):
    checks.append({"passed": bool(ok), "check": label, "id": identity})


cfg = read(folder / "capture-config.json")
plan = read(folder / "sources-plan.json")
baseline = read(prior / "readback/alerts-pg.json")["rows"]
mapping = read(prior / "readback/identity-map.json")["actual_mappings"]
snapshot = read(folder / "analysis-pg-01.json")
rows = snapshot["rows"]
indexes = {table: {r["id"]: r for r in values} for table, values in rows.items() if table != "analysis_subject_state"}
alerts = {value["alert_id"]: (name, value) for name, value in mapping["alerts"].items()}
incidents = {v["incident_id"]: v for v in mapping["incidents"].values()}
new_subjects = set(alerts) | set(incidents)
old_tasks = [t for t in baseline["analysis_tasks"] if t["subject_id"] not in new_subjects]
old_subjects = {t["subject_id"] for t in old_tasks}
artifacts, runs, attempts, steps = (indexes[k] for k in ("artifacts", "runs", "analysis_attempts", "run_steps"))
check(snapshot["identity"]["database"] == cfg["database"] and snapshot["identity"]["role"] == cfg["reader"]
      and snapshot["identity"]["readonly"] == "on" and snapshot["identity"]["ssl"], "ordinary_reader_same_database_tls")
check(snapshot["tenant_case_count"] == 0, "no_case_created")
for table in ("alert_materials", "alert_source_refs", "incident_alerts"):
    check(indexes[table] == {r["id"]: r for r in baseline[table]}, "immutable_baseline_" + table)
for row in baseline["artifacts"]:
    check(artifacts.get(row["id"]) == row, "original_ingress_artifact_preserved", row["id"])
for table in ("alerts", "incidents"):
    for old in baseline[table]:
        current = indexes[table].get(old["id"], {})
        allowed = {"latest_triage_id", "latest_explanation_id", "latest_diagnosis_id", "business_updated_at", "row_version"}
        if old["id"] in old_subjects:
            allowed = set()
        check({k: v for k, v in old.items() if k not in allowed}
              == {k: v for k, v in current.items() if k not in allowed}, "subject_preserved_outside_analysis", old["id"])
for old in baseline["analysis_tasks"]:
    current = indexes["analysis_tasks"].get(old["id"], {})
    fields = ("id", "tenant_id", "kind", "subject_type", "subject_id", "intent", "source", "operation_key",
              "request_hash", "request_payload", "retry_limit", "retry_delay_seconds")
    check(all(current.get(k) == old[k] for k in fields), "original_task_identity_and_frozen_retry", old["id"])
for old in old_tasks:
    current = indexes["analysis_tasks"].get(old["id"], {})
    check(current.get("state") == "skipped" and current.get("reason_code") == "closed_before_start"
          and not current.get("started_at"), "old_task_actually_skipped_before_start", old["id"])
    check(not any(a["task_id"] == old["id"] for a in attempts.values()), "old_task_has_no_attempt", old["id"])
check(not any(r.get("alert_id") in old_subjects or r.get("incident_id") in old_subjects for r in runs.values()),
      "old_subjects_have_no_run_or_model")
check(not any(r["alert_id"] in old_subjects for r in rows["alert_assessments"]), "old_alerts_have_no_new_result")
check(not any(r["incident_id"] in old_subjects for r in rows["incident_diagnoses"]), "old_incidents_have_no_new_result")
run_links = [a["run_id"] for a in attempts.values() if a["run_id"]]
check(len(run_links) == len(set(run_links)) and set(run_links) == set(runs), "attempt_run_bijection")
for a in artifacts.values():
    if a["run_id"] and a["content_json"] is not None:
        check(digest(a["content_json"]) == a["sha256"] and len(encoded(a["content_json"])) == a["size_bytes"]
              and a["material_state"] == "complete", "saved_artifact_hash_size_complete", a["id"])

run_map = []
quality = []
for run in runs.values():
    rid = run["id"]
    linked = [a for a in attempts.values() if a["run_id"] == rid]
    check(len(linked) == 1, "one_attempt_per_run", rid)
    attempt = linked[0] if linked else {}
    frozen = artifacts.get(run["input_artifact_id"], {})
    source = frozen.get("content_json") or {}
    policy = artifacts.get(attempt.get("policy_artifact_id"), {}).get("content_json") or {}
    check(policy.get("sha256") == cfg["policy_sha256"], "actual_policy_snapshot_matches_preflight", rid)
    check(attempt.get("input_artifact_id") == run["input_artifact_id"]
          and attempt.get("input_digest") == digest(source.get("change_view", source)), "frozen_attempt_input_pair", rid)
    check(run["state"] == "completed" and attempt.get("outcome") == "completed", "run_execution_completed", rid)
    members = source.get("members", [])
    expected_ids = {run["alert_id"]} if run["kind"] == "alert_basic" else set(incidents[run["incident_id"]]["members"])
    check({m["alert"]["id"] for m in members} == expected_ids, "frozen_members_match_scope", rid)
    for member in members:
        material = member["material"]
        check(material == indexes["alert_materials"].get(material["id"]), "frozen_original_material", rid)
        actual_objects = sorted([o for o in rows["alert_objects"] if o["material_id"] == material["id"]], key=lambda o: o["id"])
        check(member["objects"] == actual_objects, "frozen_objects_match_saved_material", rid)
    run_steps = sorted([s for s in steps.values() if s["run_id"] == rid], key=lambda s: s["seq"])
    model_steps = [s for s in run_steps if s["kind"] == "model"]
    tool_steps = [s for s in run_steps if s["kind"] == "tool"]
    models = []
    for step in model_steps:
        request = artifacts.get(step["input_artifact_id"], {})
        response = artifacts.get(step["output_artifact_id"], {})
        req, resp = request.get("content_json") or {}, response.get("content_json") or {}
        originals = [a for a in artifacts.values() if a["run_id"] == rid and a["step_id"] == step["id"]
                     and (a.get("content_json") or {}).get("artifact_role") == "model_original_response"]
        check(request.get("kind") == "model_request" and response.get("kind") == "model_response"
              and req.get("model") == cfg["model_alias"] and req.get("body", {}).get("messages")
              and req.get("body", {}).get("response_format"), "model_request_response_and_schema_saved", step["id"])
        check(len(originals) == 1 and originals[0]["content_json"].get("raw") == resp.get("raw")
              and bool((resp.get("raw") or {}).get("id")), "real_provider_original_response_preserved", step["id"])
        usage = step.get("usage") or {}
        models.append({"step_id": step["id"], "state": step["state"], "request_artifact_id": request.get("id"),
                       "response_artifact_id": response.get("id"), "original_artifact_ids": [o["id"] for o in originals],
                       "usage": usage, "validation_error": resp.get("validation_error")})
        quality.append({"run_id": rid, "step_id": step["id"], "original_artifact_ids": [o["id"] for o in originals],
                        "validation_error": resp.get("validation_error"), "citation_review": resp.get("citation_review"),
                        "prose_quality": "NOT_PASSED_not_accepted_in_this_flow_test"})
    check(bool(model_steps), "real_model_step_exists", rid)
    query_map = []
    for step in tool_steps:
        a = artifacts.get(step["output_artifact_id"], {})
        body = a.get("content_json") or {}
        values = body.get("rows") or []
        check(a.get("kind") == "tool_response" and body.get("state") == "completed"
              and body.get("returned_rows") == len(values), "real_query_completed_and_count_saved", step["id"])
        check(body.get("actual_args", {}).get("scope", {}).get("alert_ids") == [run["alert_id"]], "query_scope_single_frozen_alert", step["id"])
        if body.get("tool_name") == "assets":
            check(len(values) == 2 and {v["record_id"] for v in values} == {plan["asset"]["id"]}
                  and {v["match_basis"] for v in values} == set(plan["expected_asset_hits"]["match_bases"]),
                  "asset_one_record_two_matches", step["id"])
        if body.get("tool_name") == "history":
            logical = alerts[run["alert_id"]][0]
            check({v["record_id"] for v in values} == set(plan["history"]["expected_distinct_alerts"][logical]),
                  "history_members_actual_namespace_and_window", step["id"])
            for v in values:
                prior_triage = v["record"].get("triage")
                check(prior_triage is None or prior_triage == indexes["alert_assessments"].get(prior_triage["id"]),
                      "history_triage_is_saved_actual_record", step["id"])
        if body.get("tool_name") == "threat_intel":
            check(values == [] and body.get("state") == "completed", "intelligence_real_empty_not_mock", step["id"])
        query_map.append({"step_id": step["id"], "artifact_id": a.get("id"), "source": body.get("tool_name"),
                          "state": body.get("state"), "returned_rows": body.get("returned_rows"),
                          "record_ids": sorted({v["record_id"] for v in values})})
    triages = [v for v in rows["alert_assessments"] if v["source_run_id"] == rid]
    diagnoses = [v for v in rows["incident_diagnoses"] if v["source_run_id"] == rid]
    coverage = None
    if run["kind"] == "alert_basic":
        check({s["name"] for s in tool_steps} == {"assets", "history", "threat_intel"} and len(tool_steps) == 3,
              "A_three_actual_query_steps", rid)
        check(len(triages) == 1 and triages[0]["input_material_id"] == alerts[run["alert_id"]][1]["material_id"],
              "A_triage_saved_with_original_material", rid)
        check(any(a["kind"] == "alert_explanation" and a["run_id"] == rid for a in artifacts.values()), "A_explanation_saved", rid)
    else:
        check(not tool_steps and run["limits"]["max_tool_calls"] == 0, "I_no_new_tool_queries", rid)
        selection = source.get("input_selection") or {}
        check(set(selection.get("selected_alert_ids", [])) == expected_ids and selection.get("selected_count") == 3
              and selection.get("omitted_count") == 0, "I_explicit_actual_selection", rid)
        check(len(diagnoses) == 1 and diagnoses[0]["state"] == run["state"], "I_diagnosis_saved", rid)
        for aid, receipts in source.get("triage_queries", {}).items():
            valid = source.get("triage_validation", {}).get(aid, {})
            member = next(m for m in members if m["alert"]["id"] == aid)
            triage = member.get("triage") or {}
            check(valid.get("usable") and valid.get("triage_id") == triage.get("id")
                  and valid.get("source_run_id") == triage.get("source_run_id"), "I_usable_triage_pair", rid)
            for receipt in receipts:
                saved = artifacts.get(receipt["id"], {})
                check(all(saved.get(k) == v for k, v in receipt.items())
                      and receipt["run_id"] == triage["source_run_id"], "I_receipt_matches_saved_A_run", receipt["id"])
        if diagnoses:
            coverage = (diagnoses[0].get("diagnosis") or {}).get("delivery_assessment")
            c = (coverage or {}).get("member_coverage", {})
            check(set(c.get("expected_ids", [])) == expected_ids
                  and set(c.get("analyzed_ids", [])) <= expected_ids, "I_result_coverage_not_expanded", rid)
    run_map.append({"run_id": rid, "task_id": attempt.get("task_id"), "attempt_id": attempt.get("id"),
                    "kind": run["kind"], "subject_id": run["alert_id"] or run["incident_id"], "state": run["state"],
                    "delivery_state": run["delivery_state"], "stop_reason": run["stop_reason"],
                    "input_artifact_id": run["input_artifact_id"], "policy_artifact_id": attempt.get("policy_artifact_id"),
                    "result_ids": [v["id"] for v in triages + diagnoses], "models": models, "queries": query_map,
                    "selection": source.get("input_selection"), "triage_validation": source.get("triage_validation"),
                    "coverage": coverage})

for row in rows["analysis_tasks"]:
    if row["subject_id"] in new_subjects:
        check(row["state"] in {"completed", "skipped", "merged"}, "new_task_terminal_without_failure", row["id"])
for aid in alerts:
    row = indexes["alerts"][aid]
    check(row["latest_triage_id"] in indexes["alert_assessments"]
          and row["latest_explanation_id"] in artifacts, "A_latest_result_and_explanation_readable", aid)
for iid in incidents:
    row = indexes["incidents"][iid]
    check(row["latest_diagnosis_id"] in indexes["incident_diagnoses"], "I_latest_result_readable", iid)

failed = [v for v in checks if not v["passed"]]
result = {"status": "passed" if not failed else "failed", "scope": "A_I_real_saved_flow_not_model_quality_or_HTTP",
          "batch_id": cfg["batch_id"], "snapshot_sha256": hashlib.sha256((folder / "analysis-pg-01.json").read_bytes()).hexdigest(),
          "checks": checks, "failed_checks": failed, "run_count": len(run_map),
          "model_step_count": sum(len(r["models"]) for r in run_map), "quality": "NOT_PASSED_separate_record"}
for filename, value in [("analysis-validation-01.json", result), ("actual-analysis-map-01.json",
        {"status": result["status"], "source": "real_saved_snapshot", "batch_id": cfg["batch_id"],
         "snapshot_sha256": result["snapshot_sha256"], "runs": run_map,
         "tasks": rows["analysis_tasks"], "attempts": rows["analysis_attempts"], "old_task_ids": [t["id"] for t in old_tasks]}),
        ("model-quality-record-01.json", {"status": "NOT_PASSED", "acceptance_scope": "flow_only", "records": quality})]:
    with (folder / filename).open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
print(json.dumps({k: result[k] for k in ("status", "run_count", "model_step_count", "failed_checks")}))
