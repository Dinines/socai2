"""Compare this part's saved PG records with the public HTTP read model."""
from __future__ import annotations

import json
from datetime import datetime

from acceptance_clients import require
from alert_scenarios import sha256

RESULT_TABLES = {"alert_assessment": "alert_assessments", "incident_diagnosis": "incident_diagnoses", "case_result": "results"}


def _equal(key, left, right):
    if key.endswith("_at") and isinstance(left, str) and isinstance(right, str):
        return datetime.fromisoformat(left.replace("Z", "+00:00")) == datetime.fromisoformat(right.replace("Z", "+00:00"))
    return left == right


def _result(kind, actual, stored):
    require(actual is not None and stored is not None, "saved_result_missing_from_pg_or_http")
    fields = {
        "alert_assessment": ("id", "input_material_id", "source_run_id", "verdict", "rationale", "confidence", "score_state", "recommendations", "producer", "actor", "assessed_at"),
        "incident_diagnosis": ("id", "source_run_id", "revision", "state", "summary", "diagnosis", "open_questions", "input_artifact_id", "source_fingerprint", "producer", "requested_at", "generated_at"),
        "case_result": ("id", "source_run_id", "comparison_result_id", "conclusion", "conclusion_state", "validation_state", "delivery_state", "findings", "questions"),
    }[kind]
    for key in fields:
        require(key in actual and key in stored and _equal(key, actual[key], stored[key]), "result_http_pg_mismatch:" + key)
    if kind == "incident_diagnosis":
        require(actual["error_code"] == (stored["error"] or {}).get("code"), "result_http_pg_mismatch:error_code")


def _result_refs(links, run_ids, rows):
    actual = [(x["result_type"], x["id"], x["source_run_id"]) for x in links]
    expected = {(kind, x["id"], x["source_run_id"]) for kind, table in RESULT_TABLES.items()
                for x in rows[table] if x["source_run_id"] in run_ids}
    require(len(actual) == len(set(actual)) and set(actual) == expected, "result_reference_set_mismatch")


def verify_readback(http, rows):
    runs = {r["id"]: r for r in rows["runs"]}
    artifacts = {a["id"]: a for a in rows["artifacts"]}
    results = {r["id"]: r for r in rows["results"]}
    details, missing, quality = {}, [], []
    for task in rows["analysis_tasks"]:
        path = f"/api/v1/socai2/{task['subject_type']}s/{task['subject_id']}/analysis-tasks/{task['id']}"
        actual = http.request("GET", path)
        require(actual["task_id"] == task["id"] and actual["subject_id"] == task["subject_id"]
                and actual["status"] == task["state"], "task_http_pg_mismatch")
        attempts = [a for a in rows["analysis_attempts"] if a["task_id"] == task["id"]]
        require(len(attempts) == len(actual["attempts"]), "attempt_count_mismatch")
        for observed in actual["attempts"]:
            stored = next((a for a in attempts if a["attempt_no"] == observed["attempt_no"]), None)
            require(stored and stored["run_id"] == observed["run_id"] and stored["outcome"] == observed["outcome"],
                    "attempt_identity_or_outcome_mismatch")
        _result_refs(actual["results"], {a["run_id"] for a in attempts if a["run_id"]}, rows)
        for link in actual["results"]:
            require(link["source_run_id"] in runs, "result_source_run_not_in_execution")
            result = http.request("GET", link["url"])["result"]
            stored = next((r for r in rows[RESULT_TABLES[link["result_type"]]] if r["id"] == link["id"]), None)
            _result(link["result_type"], result, stored)
    for kind, table in (("alert", "alerts"), ("incident", "incidents"), ("case", "cases")):
        for subject in rows[table]:
            entries = http.pages("/api/v1/socai2/analysis-runs",
                                 {"subject_type": kind, "subject_id": subject["id"]})
            require({entry["run_id"] for entry in entries} == {r["id"] for r in runs.values() if r[kind + "_id"] == subject["id"]},
                    "subject_run_directory_mismatch")
            for entry in entries:
                rid = entry["run_id"]
                detail = http.request("GET", entry["detail_url"])
                require(detail["run"]["id"] == rid and detail["run"]["state"] == runs[rid]["state"],
                        "run_http_pg_mismatch")
                _result_refs(entry["results"], {rid}, rows)
                if kind in {"alert", "incident"}:
                    result_kind = "alert_assessment" if kind == "alert" else "incident_diagnosis"
                    candidates = [r for r in rows[RESULT_TABLES[result_kind]] if r["source_run_id"] == rid]
                    require(len(candidates) <= 1, "ambiguous_stage_result")
                    if candidates:
                        _result(result_kind, detail["result"], candidates[0])
                    else:
                        require(detail["result"] is None, "unexpected_http_result")
                details[rid] = detail
                steps = http.pages(f"/api/v1/socai2/analysis-runs/{rid}/steps")
                available = http.pages(f"/api/v1/socai2/analysis-runs/{rid}/artifacts")
                stored_steps = {x["id"]: x for x in rows["run_steps"] if x["run_id"] == rid}
                require({s["id"] for s in steps} == set(stored_steps), "step_directory_mismatch")
                require({a["id"] for a in available} == {a["id"] for a in artifacts.values() if a["run_id"] == rid},
                        "artifact_directory_mismatch")
                for step in steps:
                    for key in ("run_id", "stage_code", "state", "actual_args", "error", "usage", "input_artifact_id", "output_artifact_id"):
                        require(step[key] == stored_steps[step["id"]][key], "step_http_pg_mismatch:" + key)
                    if step.get("error"):
                        quality.append({"run_id": rid, "step_id": step["id"], "stage": step["stage_code"], "error": step["error"]})
                for item in available:
                    content = http.request("GET", item["content_url"])
                    stored = artifacts[item["id"]]
                    metadata = content.get("artifact", content.get("metadata"))
                    require(metadata and metadata["id"] == stored["id"], "artifact_identity_mismatch")
                    if content["availability"] != "available":
                        missing.append({"run_id": rid, "artifact_id": item["id"], "availability": content["availability"]})
                        continue
                    require(content["content_json"] == stored["content_json"] and content["content_text"] == stored["content_text"],
                            "artifact_original_value_mismatch")
                    encoded = (json.dumps(stored["content_json"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
                               if stored["content_json"] is not None else stored["content_text"].encode())
                    require(metadata["sha256"] == stored["sha256"] == sha256(encoded)
                            and metadata["size_bytes"] == stored["size_bytes"] == len(encoded), "artifact_digest_mismatch")
                if kind == "incident" and detail.get("input_selection"):
                    selected = detail["input_selection"]
                    source = artifacts.get(runs[rid]["input_artifact_id"], {}).get("content_json")
                    require(source and source.get("input_selection"), "incident_frozen_selection_missing")
                    expected = {**source["input_selection"], "input_artifact_id": runs[rid]["input_artifact_id"]}
                    require(set(selected) == set(expected) and all(_equal(k, selected[k], v) for k, v in expected.items()),
                            "incident_frozen_selection_mismatch")
                    require(set(selected["selected_alert_ids"]) == {m["alert"]["id"] for m in source["members"]}
                            and selected["selected_count"] == len(source["members"])
                            and selected["total_member_count"] == selected["selected_count"] + selected["omitted_count"],
                            "incident_frozen_membership_mismatch")
                if kind == "case":
                    manifest = artifacts.get(runs[rid]["input_artifact_id"], {}).get("content_json")
                    if manifest:
                        c1 = [artifacts[r["id"]]["content_json"] for r in manifest.get("source_materials", [])
                              if r.get("type") == "artifact" and r.get("id") in artifacts
                              and artifacts[r["id"]]["schema_version"] == "socai2.baseline-context.v1"]
                        require(len(c1) == 1, "case_frozen_context_missing_or_ambiguous")
                        members = {m["alert_id"] for m in rows["run_members"] if m["run_id"] == rid}
                        require(set(c1[0]["alerts"]) == members, "case_frozen_member_mismatch")
                        if runs[rid]["scope_revision"] == subject["scope_revision"]:
                            require(members == {m["alert_id"] for m in rows["case_alerts"] if m["case_id"] == subject["id"]},
                                    "case_current_revision_scope_mismatch")
                        comparison = manifest.get("comparison_context")
                        require(comparison and detail["run"]["comparison_context"] == comparison
                                and c1[0].get("update_context", {}).get("comparison_context") == comparison
                                and runs[rid]["comparison_result_id"] == comparison["comparison_result_id"],
                                "case_frozen_comparison_mismatch")
                        previous, compared = comparison["previous_run_id"], comparison["comparison_result_id"]
                        require(not previous or (previous in runs and runs[previous]["case_id"] == subject["id"]),
                                "case_previous_run_identity_mismatch")
                        require(not compared or (compared in results and results[compared]["case_id"] == subject["id"]
                                and results[compared]["source_run_id"] == previous), "case_comparison_result_identity_mismatch")
                        base = f"/api/v1/socai2/cases/{subject['id']}"
                        require(detail["previous_run_url"] == (base + "/runs/" + previous if previous else None)
                                and detail["comparison_result_url"] == (base + "/results/" + compared if compared else None),
                                "case_comparison_url_mismatch")
    return {"status": "passed" if not missing else "incomplete_originals", "run_ids": list(details),
            "task_ids": [t["id"] for t in rows["analysis_tasks"]], "result_ids": list(results),
            "steps": len(rows["run_steps"]), "artifacts": len(artifacts), "missing_originals": missing,
            "recorded_step_issues": quality, "model_quality": "not_fully_evaluated"}

