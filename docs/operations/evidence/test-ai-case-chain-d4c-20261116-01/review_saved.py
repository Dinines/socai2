"""Independent, offline review of the one frozen D4c task/PG/ASGI bundle."""
import argparse
import copy
import hashlib
import json
import re
import traceback
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import tomllib

ROOT = Path(__file__).resolve().parents[4]


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def at(value, path):
    for key in re.findall(r"[^.\[\]]+", path[2:]):
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def payload(artifact):
    content = artifact["content_json"]
    return content.get("payload", content)


def stamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def review(bundle, output):
    bundle, output = bundle.resolve(), output.resolve()
    files = {p.name: p for p in bundle.glob("*.json")}
    frozen = {name: sha(p.read_bytes()) for name, p in files.items()}
    data = {name: json.loads(p.read_text()) for name, p in files.items()}
    report = {"state": "reviewing", "bundle": str(bundle.relative_to(ROOT)),
              "source_files": frozen, "checks": [], "failures": [], "quality": [],
              "review_script_sha256": sha(Path(__file__).read_bytes()),
              "reviewer_model_calls": 0, "reviewer_HTTP_requests": 0,
              "reviewer_PG_Redis_executions": 0, "product_tests_run": 0,
              "not_covered": ["21/TCP/browser", "Kafka ingress", "configured vendor queries",
                              "D5 network failures", "natural model truncation", "ASGI POST"]}

    def check(group, name, condition):
        if not condition:
            raise AssertionError(group + ": " + name)
        report["checks"].append({"group": group, "name": name})

    try:
        final, db = data["result.json"], data["database.json"]
        calls, tasks, scans = (data[name + ".json"] for name in ("calls", "tasks", "scans"))
        arts = {a["id"]: a for a in db["artifacts"]}
        runs = {r["id"]: r for r in db["runs"]}
        entries = {t["label"]: t for t in tasks}
        dbtasks = {t["id"]: t for t in db["analysis_tasks"]}
        a1, i1, r1, a2, i2, r2 = (entries[label] for label in
            ("01-A1", "02-I1", "03-Case-R1", "05-A2", "06-I2", "07-Case-R2"))
        iid, cid, tenant = final["incident_id"], final["case_id"], final["tenant_id"]
        members = {a["id"] for a in db["alerts"]}

        def checkpoint(label):
            return data[label + ".json"]["rows"]

        def artifacts(rid, schema=None, kind=None):
            return [a for a in arts.values() if a["run_id"] == rid
                    and (schema is None or a["schema_version"] == schema)
                    and (kind is None or a["kind"] == kind)]

        def context(entry):
            selected = artifacts(entry["run_id"], "socai2.baseline-context.v1")
            assert len(selected) == 1
            return selected[0]

        def receipt(entry):
            selected = artifacts(entry["run_id"], "socai2.stage-delivery.v1")
            assert len(selected) == 1
            return selected[0]["content_json"]

        check("C01", "completed_unique_owner_bundle", final["state"] == "passed_within_D4c_scope"
              and not final["uncovered"] and len(members) == 4)
        seed = checkpoint("00-materials-before-analysis")
        check("C01", "seed_contains_raw_materials_without_analysis", len(seed["alerts"]) == 4
              and len(seed["alert_materials"]) == 4
              and all(not seed[k] for k in ("analysis_tasks", "analysis_attempts", "runs", "results",
                                             "artifacts", "alert_assessments", "incident_diagnoses")))
        check("C01", "source_material_identity_and_bytes_preserved", all(
            seed[k] == db[k] for k in ("alert_materials", "alert_objects", "incident_alerts")))
        check("C01", "A1_unavailable_I1_still_executed", a1["status"] == i1["status"] == "failed"
              and not next(a for a in db["alerts"] if a["id"] == a1["subject_id"])["latest_triage_id"]
              and len(arts[runs[i1["run_id"]]["input_artifact_id"]]["content_json"]["members"]) == 4)
        ai_receipts = {e["run_id"]: receipt(e) for e in (a1, i1, a2, i2)}
        check("C01", "actual_A1_closed_rationale_missing_evidence", receipt(a1)["delivery"]["state"] == "partial"
              and {u["path"] for u in receipt(a1)["retained_units"]} == {"$.verdict", "$.confidence", "$.rationale"}
              and not receipt(a1)["use"]["conclusion_available"])
        check("C01", "actual_I1_one_member_I2_none", receipt(i1)["delivery"]["state"] == "partial"
              and [u["path"] for u in receipt(i1)["retained_units"]] == ["$.members[0]"]
              and receipt(i2)["delivery"]["state"] == "none" and not receipt(i2)["retained_units"])

        injection_count = 0
        for call in calls:
            request = arts[call["request_artifact_id"]]
            check("C01", "wire_and_response_identity:" + request["id"],
                  payload(request)["body"] == call["request"] and request["run_id"] == call["run_id"]
                  and sha(encoded(call["real_response"])) == call["real_response_sha256"]
                  and sha(encoded(call["response"])) == call["received_response_sha256"])
            originals = [a for a in artifacts(call["run_id"], kind="source_snapshot")
                         if isinstance(a["content_json"], dict) and "raw" in a["content_json"]
                         and a["content_json"].get("request_artifact_id") == request["id"]]
            check("C01", "one_saved_actual_received_original:" + request["id"], len(originals) == 1
                  and originals[0]["content_json"]["raw"] == call["response"]
                  and originals[0]["step_id"] == request["step_id"])
            if "injection" not in call:
                check("C01", "unmodified_real_return:" + request["id"], call["mode"] == "real"
                      and call["response"] == call["real_response"])
                continue
            injection_count += 1
            cut = call["injection"]["character_cut_offset"]
            raw = call["real_response"]
            text = raw["choices"][0]["message"]["content"]
            derived = copy.deepcopy(raw)
            derived["choices"][0]["message"]["content"] = text[:cut]
            derived["choices"][0]["finish_reason"] = "length"
            full = arts[call["complete_response_artifact_id"]]
            check("C01", "prefix_only_separate_complete_original:" + call["mode"],
                  call["response"] == derived and full["content_json"]["real_response"] == raw
                  and full["schema_version"] == "socai2.verification.response-injection.v1"
                  and full["run_id"] == request["run_id"] and full["step_id"] == request["step_id"]
                  and call["injection"]["utf8_cut_offset"] == len(text[:cut].encode())
                  and call["injection"]["source_body_sha256"] == sha(text.encode())
                  and call["injection"]["delivered_body_sha256"] == sha(text[:cut].encode()))
            strict = ai_receipts[call["run_id"]]
            response_ref = next(x for x in strict["originals"] if x["kind"] == "response")
            check("C01", "strict_receipt_points_to_received_not_full:" + call["mode"],
                  response_ref["artifact_id"] == originals[0]["id"] != full["id"]
                  and response_ref["sha256"] == originals[0]["sha256"])
        check("C01", "exactly_three_labelled_injections", injection_count == 3)

        gate = checkpoint("02a-case-created-during-I")
        check("C02", "Case_created_with_four_members_while_I1_running", len(gate["cases"]) == 1
              and {a["alert_id"] for a in gate["case_alerts"]} == members
              and gate["incidents"][0]["active_case_id"] == cid
              and next(t for t in gate["analysis_tasks"] if t["id"] == i1["task_id"])["state"] == "running")
        check("C02", "initial_task_committed_without_Case_Run_or_attempt", r1["task_id"] in {t["id"] for t in gate["analysis_tasks"]}
              and not any(r["case_id"] == cid for r in gate["runs"])
              and not any(a["task_id"] == r1["task_id"] for a in gate["analysis_attempts"]))
        contexts = [context(e) for e in (r1, r2)]
        finals = []
        c6_checks = []
        for entry, frozen_context, upstream, state in zip((r1, r2), contexts, (i1, i2), ("partial", "none")):
            rid = entry["run_id"]
            ctx = frozen_context["content_json"]
            stage_codes = {s["stage_code"].split(".")[0] for s in db["run_steps"] if s["run_id"] == rid}
            own_calls = [c for c in calls if c["run_id"] == rid]
            result_rows = [r for r in db["results"] if r["source_run_id"] == rid]
            check("C02", "full_task_C1_C6_and_saved_Result:" + rid, runs[rid]["state"] == "completed"
                  and {"C1", "C2", "C3", "C4", "C5", "C6"} <= stage_codes and len(result_rows) == 1
                  and {"C3", "C6"} <= {c["stage"] for c in own_calls}
                  and all(c["mode"] == "real" for c in own_calls))
            result = result_rows[0]
            finals.append(result)
            c6 = [c for c in own_calls if c["stage"] == "C6"]
            check("C02", "C6_original_comparison_is_executed:" + rid, len(c6) == 1
                  and "real_response" in c6[0] and result["conclusion_origin"] == "model"
                  and result["conclusion_state"] != "unavailable")
            answer = json.loads(c6[0]["real_response"]["choices"][0]["message"]["content"])
            check("C02", "C6_conclusion_exact_saved_text:" + rid, answer["conclusion"]["text"] == result["conclusion"])
            c6_checks.append({"run_id": rid, "result_id": result["id"], "executed": True,
                              "text_sha256": sha(result["conclusion"].encode())})
            material = ctx["incidents"][iid]["analysis_material"]
            check("C05", "four_raw_members_current_I_scope:" + rid, set(ctx["scope"]["alert_ids"]) == members
                  and set(ctx["alerts"]) == members and material["source_run_id"] == upstream["run_id"]
                  and set(material["input_selection"]["selected_alert_ids"]) == members
                  and material["receipt"]["delivery"]["state"] == state
                  and not material["business_view"]["conclusion_available"])
            check("C05", "actual_retained_scope_not_expanded:" + rid,
                  (len(material["units"]) == 1 and len(material["units"][0]["scope"]["alert_ids"]) == 1)
                  if state == "partial" else not material["units"])
            upstream_refs = [material[k] for k in ("input", "response", "receipt_source")] + material["originals"]
            check("C05", "frozen_source_five_artifacts:" + rid, len(upstream_refs) == 5 and all(
                arts[ref["id"]]["run_id"] == upstream["run_id"] and arts[ref["id"]]["incident_id"] == iid
                and arts[ref["id"]]["sha256"] == ref["sha256"] for ref in upstream_refs))
            c3 = next(c for c in own_calls if c["stage"] == "C3")
            mapping = payload(arts[c3["request_artifact_id"]])["source_map"]
            for index, unit in enumerate(material["units"]):
                path = f"$.incidents.{iid}.analysis_material.units.{index}.value"
                refs = [v for v in mapping.values() if v["ref"].get("source_path") == path]
                check("C05", "C3_prior_analysis_original_scope:" + unit["path"], bool(refs) and all(
                    r["ref"]["role"] == "prior_analysis" and r["ref"]["id"] == frozen_context["id"]
                    and r["original_scope"] == unit["scope"] for r in refs)
                      and unit["value"]["assessment"] in json.dumps(c3["request"]["messages"], ensure_ascii=False))
        report["C6_exact_comparisons"] = c6_checks

        before_a2 = checkpoint("04-unchanged-R1")
        a2_task = dbtasks[a2["task_id"]]
        check("C03", "fresh_other_A2_after_R1_and_no_changes", a2["subject_id"] != a1["subject_id"]
              and a2_task["intent"] == "initial" and a2["status"] == "completed"
              and stamp(a2_task["submitted_at"]) > stamp(dbtasks[entries["04-unchanged-R1"]["task_id"]]["ended_at"]))
        input1, input2 = [arts[runs[e["run_id"]]["input_artifact_id"]]["content_json"] for e in (i1, i2)]
        check("C03", "usable_A2_actually_changes_business_input", input1["change_view"] != input2["change_view"]
              and input2["triage_validation"][a2["subject_id"]]["usable"])
        check("C03", "periodic_I2_then_periodic_R2", dbtasks[i2["task_id"]]["source"] == "periodic"
              and dbtasks[r2["task_id"]]["source"] == "periodic"
              and stamp(runs[r2["run_id"]]["started_at"]) >= stamp(runs[i2["run_id"]]["ended_at"]))
        scan_by_label = {s["label"]: s for s in scans}
        check("C03", "late_A_alone_no_case", scan_by_label["05a-A2-alone-does-not-trigger-Case"]["counts"]["submitted"] == 0
              and len(checkpoint("05-A2")["runs"]) == len(before_a2["runs"]) + 1)
        for label, prior in (("04-unchanged-R1", "03-Case-R1"), ("08-unchanged-R2", "07-Case-R2")):
            entry = entries[label]
            check("C04", "fresh_no_changes_without_Run:" + label, entry["status"] == "skipped"
                  and entry["task"]["reason_code"] == "no_changes" and not entry["task"]["attempts"]
                  and "run_id" not in entry and dbtasks[entry["task_id"]]["operation_key"] != dbtasks[entries[prior]["task_id"]]["operation_key"]
                  and checkpoint(label)["runs"] == checkpoint(prior)["runs"])
            scan = scan_by_label[label + "_periodic"]
            check("C04", "actual_next_check_clock_without_submission:" + label,
                  stamp(scan["controlled_scan_at"]) == stamp(scan["next_check_at_before"])
                  and scan["counts"]["submitted"] == 0 and not scan["new_tasks"])
        check("C04", "only_two_Case_Runs_no_feedback_cycle", len([r for r in db["runs"] if r["case_id"] == cid]) == 2
              and len({t["operation_key"] for t in db["analysis_tasks"]}) == len(db["analysis_tasks"]))
        prior_context = next(a for a in checkpoint("03-Case-R1")["artifacts"] if a["id"] == contexts[0]["id"])
        check("C05", "R1_context_unchanged_after_A2_and_R2", prior_context == contexts[0])
        comparison1, comparison2 = [c["content_json"]["update_context"]["comparison_context"] for c in contexts]
        check("C06", "initial_empty_comparison", comparison1["state"] == "initial"
              and comparison1["previous_run_id"] is None and comparison1["comparison_result_id"] is None)
        check("C06", "R2_previous_is_actual_R1", comparison2["previous_run_id"] == r1["run_id"]
              and comparison2["comparison_result_id"] in (None, finals[0]["id"])
              and finals[1]["comparison_result_id"] == comparison2["comparison_result_id"])
        report["comparison"] = comparison2

        replies, validation = data["http.json"], data["http-validation.json"]
        check("C07", "saved_actual_ASGI_GETs_all_200", len(replies) == final["http_gets"]
              and all(r["method"] == "GET" and r["status"] == 200 for r in replies)
              and validation["http_transport"] == "ASGITransport")
        by_path = {r["path"]: r["body"] for r in replies}
        directories = {}
        for response in replies:
            parsed = urlsplit(response["path"])
            body = response["body"]
            if parsed.path.endswith(("/steps", "/artifacts")) and "items" in body:
                directories.setdefault(parsed.path, []).append((parse_qs(parsed.query), body))
        seen_artifacts, seen_steps = set(), set()
        for url, pages in directories.items():
            next_cursor, ids = None, set()
            for params, body in pages:
                check("C07", "page_cursor:" + url + ":" + str(len(ids)), params.get("cursor", [None])[0] == next_cursor)
                page_ids = {row["id"] for row in body["items"]}
                check("C07", "page_unique:" + url + ":" + str(len(ids)), len(page_ids) == len(body["items"]) and not ids & page_ids)
                ids |= page_ids
                next_cursor = body["next_cursor"]
                for row in body["items"]:
                    if "content_url" not in row:
                        continue
                    stored = arts[row["id"]]
                    content = by_path[row["content_url"]]
                    meta = content.get("artifact", content.get("metadata"))
                    raw = encoded(stored["content_json"]) if stored["content_json"] is not None else stored["content_text"].encode()
                    check("C07", "directory_content_bytes:" + row["id"], content["availability"] == "available"
                          and meta["id"] == stored["id"] and meta["sha256"] == stored["sha256"] == sha(raw)
                          and meta["size_bytes"] == stored["size_bytes"] == len(raw)
                          and content["content_json"] == stored["content_json"] and content["content_text"] == stored["content_text"])
            check("C07", "directory_complete:" + url, next_cursor is None and len(ids) == pages[-1][1]["total"])
            (seen_artifacts if url.endswith("/artifacts") else seen_steps).update(ids)
        check("C07", "all_saved_steps_and_artifacts_reached_via_directories", seen_artifacts == set(arts)
              and seen_steps == {s["id"] for s in db["run_steps"]})
        for entry in tasks:
            path = f"/api/v1/socai2/{entry['subject_type']}s/{entry['subject_id']}/analysis-tasks/{entry['task_id']}"
            task = by_path[path]
            check("C07", "task_attempt_frozen_Run:" + entry["label"], task["status"] == entry["status"]
                  and ([a["run_id"] for a in task["attempts"]] == [entry["run_id"]] if "run_id" in entry else not task["attempts"]))
            for attempt in task["attempts"]:
                detail = by_path[attempt["run_url"]]
                check("C07", "actual_run_url:" + entry["label"], attempt["attempt_no"] == 1 and detail["run"]["id"] == entry["run_id"])
            for link in task.get("results", []):
                if link["result_type"] == "case_result":
                    actual = by_path[link["url"]]["result"]
                    stored = next(r for r in finals if r["id"] == actual["id"])
                    check("C07", "actual_Result_url_text_and_state:" + stored["id"], all(actual[k] == stored[k]
                          for k in ("conclusion", "conclusion_state", "validation_state", "findings", "questions", "delivery_state")))
        check("C07", "25_table_readonly_content_hashes", len(validation["before"]) == 25
              and validation["before"] == validation["after"] == data["database-hashes.json"])
        for a in arts.values():
            if a["schema_version"] != "socai2.stage-delivery.v1":
                continue
            for unit in a["content_json"]["retained_units"]:
                text = at(arts[unit["original_artifact_id"]]["content_json"], unit["original_content_path"])
                left, right = unit["value_span"]
                fragment = text[left:right]
                check("C07", "retained_unit_actual_raw_span:" + a["id"] + ":" + unit["path"],
                      0 <= left < right <= len(text) and sha(fragment.encode()) == unit["value_sha256"]
                      and json.loads(fragment) == unit["value"])

        check("C08", "all_attempts_terminal_slots_released", all(r["state"] in {"completed", "failed"} for r in db["runs"])
              and all(a["local_state"] == "ended" for a in db["analysis_attempts"])
              and all(t["state"] in {"completed", "failed", "skipped"} for t in db["analysis_tasks"])
              and final["final_slots"] == {"active": 0, "receipts": 0, "redis_running": 0})
        check("C08", "real_usage_counted_once_per_call", all(c["real_model_call"] and c["state"] == "responded" for c in calls)
              and final["real_model_calls"] == len(calls) and final["usage_missing_calls"] == 0
              and sum(c["real_response"]["usage"]["total_tokens"] for c in calls) == final["reported_total_tokens"])
        report["actual_calls"] = [{"stage": c["stage"], "mode": c["mode"], "run_id": c["run_id"],
                                   "usage": c["real_response"]["usage"]} for c in calls]
        report["usage_total"] = final["reported_total_tokens"]
        report["cost"] = "unknown"
        report["optional_branches"] = [{"run_id": e["run_id"], "steps": [
            {"stage_code": s["stage_code"], "state": s["state"], "error": s["error"]}
            for s in db["run_steps"] if s["run_id"] == e["run_id"]]} for e in (r1, r2)]
        check("C08", "source_and_profile_unchanged", data["source-before.json"] == data["source-after.json"]
              and all(sha((ROOT / p).read_bytes()) == digest for p, digest in data["source-after.json"].items()))

        for c in calls:
            visible = json.dumps(c["request"]["messages"], ensure_ascii=False)
            forbidden = ["tenant_uid", "D4c", "d4c-20261116", "受控回放", "fixture", "input_ledger",
                         "receipt_source", "local_ended_at", "attempt_id", c["task_id"], c["run_id"], tenant]
            check("C09", "actual_messages_no_batch_or_execution_identity:" + c["request_artifact_id"],
                  not any(token in visible for token in forbidden))
        public_policy = tomllib.loads((ROOT / "deploy/aisoc21/streaming-release-20261116-02/analysis/investigation-policy.toml").read_text())
        policy_artifacts = [a for a in arts.values() if a["schema_version"] == "socai2.runtime-policy.v1"]
        check("C08", "each_actual_Run_saved_current_runtime_policy", {a["run_id"] for a in policy_artifacts} == set(runs))
        for a in policy_artifacts:
            saved_policy = a["content_json"]
            policy = tomllib.loads(saved_policy["toml_text"])
            endpoint = policy["model"]["tokenizer"]["endpoint"]
            policy["model"]["tokenizer"]["endpoint"] = public_policy["model"]["tokenizer"]["endpoint"]
            check("C08", "current_policy_only_explicit_tokenizer_forward_differs:" + a["run_id"],
                  policy == public_policy and endpoint.startswith("http://127.0.0.1:")
                  and sha(saved_policy["toml_text"].encode()) == saved_policy["sha256"])
            for name, filename in (("alert_io", "alert-input-v1.json"), ("incident_io", "incident-input-v1.json"),
                                   ("case_io", "case-input-v1.json")):
                expected = (ROOT / "services/api/app/socai2" / filename).read_bytes()
                profile = saved_policy["profiles"][name]
                check("C08", "actual_profile_matches_current_file:" + a["run_id"] + ":" + name,
                      profile["sha256"] == sha(expected) and profile["json_text"].encode() == expected)
        disabled_tools = [a["content_json"] for a in arts.values() if a["kind"] == "tool_response"
                          and a["case_id"] == cid and a["content_json"].get("tool_name") in {"ueba", "knowledge", "graph"}]
        check("C08", "disabled_sources_remain_unqueried_not_empty_success", len(disabled_tools) == 6
              and all(t["state"] == "skipped" and t["error"]["code"] == "source_not_connected"
                      and t["rows"] is None for t in disabled_tools))
        check("C08", "actual_optional_Deep_branch", sum(c["stage"] == "Deep" and c["run_id"] == r1["run_id"] for c in calls) == 1
              and not any(c["stage"] == "Deep" and c["run_id"] == r2["run_id"] for c in calls))
        for e, ctx in zip((r1, r2), contexts):
            manifest = arts[runs[e["run_id"]]["input_artifact_id"]]["content_json"]
            material = ctx["content_json"]["incidents"][iid]["analysis_material"]
            required = {ctx["id"], *(material[k]["id"] for k in ("input", "response", "receipt_source")),
                        *(o["id"] for o in material["originals"])}
            check("C07", "actual_manifest_locates_C1_and_frozen_I_sources:" + e["run_id"],
                  required <= {r["id"] for r in manifest["source_materials"]}
                  and manifest["comparison_context"] == ctx["content_json"]["update_context"]["comparison_context"])
        c3_text = "\n".join(m["content"] for c in calls if c["stage"] == "C3" for m in c["request"]["messages"])
        check("C09", "actual_business_zero_false_and_empty_list_survive", "sensor_observation.connection_reset：false" in c3_text
              and "sensor_observation.dns_answers：[]" in c3_text and "activity_id：0" in c3_text)
        report["not_covered"].append("I2-running checker was not separately invoked in D4c; running/retry gates have D4b direct evidence")

        automatic = []
        for a in arts.values():
            j = a["content_json"]
            if not isinstance(j, dict):
                continue
            if a["schema_version"] == "socai2.stage-delivery.v1" and j["stage"] == "C3":
                stage, path, issues = "C3", "$.quality.issues", j["quality"]["issues"]
            elif "validation_review" in j and j.get("citation_review"):
                stage, path, issues = "C6", "$.citation_review.issues", j["citation_review"]["issues"]
            else:
                continue
            automatic.extend({"run_id": a["run_id"], "stage": stage, "artifact_id": a["id"],
                              "issues_path": path, "issue": issue} for issue in issues)
        check("C09", "four_actual_automatic_quality_diagnostics_retained", len(automatic) == 4
              and sum(x["issue"]["code"] == "same_source_as_support_and_counterevidence" for x in automatic) == 3
              and sum(x["issue"]["code"] == "delivery_source_coverage_missing" for x in automatic) == 1)
        report["automatic_quality"] = automatic

        # Concrete semantic defects are evidence records, not a quality pass/fail
        # threshold for the independently checked functional pipeline.
        for c6, result in zip([c for c in calls if c["stage"] == "C6"], finals):
            request = payload(arts[c6["request_artifact_id"]])
            aliases = {alias: aid for aid, alias in request["case_boundary"]["member_aliases"].items()}
            facts = {}
            for alias in ("A1", "A2", "A3", "A4"):
                alert = next(a for a in db["alerts"] if a["id"] == aliases[alias])
                material = next(m for m in db["alert_materials"] if m["id"] == alert["latest_material_id"])
                event = material["ocsf_json"]
                refs = [key for key, value in request["source_map"].items()
                        if value["ref"]["id"] == material["id"] and value["ref"]["source_path"] == "$.ocsf_json.time"]
                check("C09", "quality_fact_maps_to_actual_C6_input:" + c6["run_id"] + ":" + alias,
                      bool(refs) and stamp(alert["event_time"]) == stamp(event["time"])
                      and event["time"] in json.dumps(c6["request"]["messages"], ensure_ascii=False))
                facts[alias] = {"alert_id": alert["id"], "material_id": material["id"], "event_time": event["time"],
                                "action": event["activity"]["action"], "actual_C6_source_ids": refs}
            delta = (stamp(facts["A4"]["event_time"]) - stamp(facts["A2"]["event_time"])).total_seconds()
            assert facts["A2"]["action"] == "process_start" and facts["A4"]["action"] == "network_flow_observed"
            assert delta == 240 and "A4 流量时间早于 curl 进程启动" in result["conclusion"]
            report["quality"].append({"code": "manual_time_order_reversed", "state": "NOT_PASSED",
                "run_id": c6["run_id"], "request_artifact_id": c6["request_artifact_id"], "result_id": result["id"],
                "original_conclusion": result["conclusion"], "facts": facts, "A4_after_A2_seconds": delta,
                "source": "manual independent original-material comparison; not an automatic diagnostic",
                "action": "recorded_deferred; original response and Result unchanged; no resampling"})
        original_i1 = next(c for c in calls if c["mode"] == "I1_partial")
        full_i1 = json.loads(original_i1["real_response"]["choices"][0]["message"]["content"])
        assessment = full_i1["members"][1]["assessment"]
        i_aliases = payload(arts[original_i1["request_artifact_id"]])["incident_boundary"]["member_aliases"]
        check("C09", "I1_quality_observation_uses_same_actual_aliases", i_aliases[facts["A1"]["alert_id"]] == "A1"
              and i_aliases[facts["A2"]["alert_id"]] == full_i1["members"][1]["alert_ref"] == "A2")
        minutes = (stamp(facts["A2"]["event_time"]) - stamp(facts["A1"]["event_time"])).total_seconds() / 60
        assert "8 分钟" in assessment and minutes == 6
        report["quality"].append({"code": "manual_login_to_process_duration", "state": "NOT_PASSED",
            "run_id": i1["run_id"], "complete_response_artifact_id": original_i1["complete_response_artifact_id"],
            "original_assessment": assessment, "actual_minutes": minutes,
            "facts": {k: facts[k] for k in ("A1", "A2")}, "delivered_to_downstream": False,
            "reason": "I1 delivered only member[0]; inaccurate member[1] exists in separately stored complete response"})
        report["state"] = "passed_within_D4c_saved_flow_scope"
        report["business_quality"] = "not_passed; separate concrete observations"
        report["counts"] = {k: len(db[k]) for k in ("analysis_tasks", "runs", "run_steps", "artifacts", "results")}
    except (AssertionError, KeyError, ValueError, TypeError, StopIteration, OSError) as exc:
        report["state"] = "failed"
        report["failures"].append({"type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
    report["bundle_unchanged_during_review"] = frozen == {name: sha(p.read_bytes()) for name, p in files.items()}
    if not report["bundle_unchanged_during_review"]:
        report["state"] = "failed"
        report["failures"].append({"error": "source evidence changed during review"})
    with output.open("x") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"state": report["state"], "checks": len(report["checks"]), "failures": report["failures"]}, ensure_ascii=False))
    return report["state"] != "passed_within_D4c_saved_flow_scope"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(review(args.bundle, args.output))
