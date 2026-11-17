"""Independent D4a saved-data review; no service requests or business replay."""
import hashlib
import json
import socket
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from app.socai2.baseline_store import digest
from app.socai2.stage_delivery import validate_sources

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "docs/operations/evidence/ai-unit-continuation-d4-20261116-01"
OUT = Path(__file__).parent / "saved-review-01"


def forbidden(*_args, **_kwargs):
    raise AssertionError("Saved evidence review must remain offline")


socket.socket.connect = forbidden
socket.create_connection = forbidden


def read(name):
    return json.loads((SOURCE / name).read_text())


checks = []


def check(name, value):
    checks.append({"name": name, "passed": bool(value)})
    assert value, name


def review():
    rows = read("readback-01/database.json")
    calls, tasks = read("real-01/calls.json"), read("real-01/tasks.json")
    http, readback = read("readback-01/http.json"), read("readback-01/result.json")
    check("same_business_snapshot_after_readback", rows == read("real-01/database.json"))
    check("five_tasks_attempts_runs", all(len(rows[k]) == 5 for k in ("analysis_tasks", "analysis_attempts", "runs")))
    check("two_real_three_controlled", [(c["stage"], c["mode"]) for c in calls]
          == [("A", "real"), ("I", "real"), ("I", "partial"), ("I", "empty"), ("A", "partial")])
    artifacts = {a["id"]: a for a in rows["artifacts"]}
    contents = {k: a["content_json"] or {} for k, a in artifacts.items()}
    check("all_saved_JSON_digests", all(digest(a["content_json"]) == a["sha256"]
          for a in artifacts.values() if a["content_json"] is not None))
    summaries, real_tokens, source_units = [], {}, 0
    real_mothers = {c["stage"]: c for c in calls if c["mode"] == "real"}
    for call, task in zip(calls, tasks):
        stage, mode, rid = call["stage"], call["mode"], call["run_id"]
        label = stage + "/" + mode
        run = next(r for r in rows["runs"] if r["id"] == rid)
        check(label + ":task_run_binding", task["run_id"] == rid and any(
            a["task_id"] == task["task_id"] and a["run_id"] == rid for a in rows["analysis_attempts"]))
        owned = [a for a in artifacts.values() if a["run_id"] == rid]
        receipts = [a for a in owned if (a["content_json"] or {}).get("type") == "stage_delivery"]
        check(label + ":one_stage_receipt", len(receipts) == 1)
        receipt_row = receipts[0]
        receipt = receipt_row["content_json"]
        validate_sources(receipt, contents)
        model = next(s for s in rows["run_steps"] if s["run_id"] == rid and s["kind"] == "model")
        request = contents[call["request_artifact_id"]]
        response = contents[model["output_artifact_id"]]
        source = contents[run["input_artifact_id"]]
        subject = "alert_id" if stage == "A" else "incident_id"
        check(label + ":real_subject_run_step_input", receipt_row[subject] == run[subject] and receipt_row["run_id"] == rid
              and receipt["run_id"] == rid and receipt["step_id"] == receipt_row["step_id"]
              and receipt["input_artifact_id"] == run["input_artifact_id"])
        check(label + ":actual_request_and_response", request["body"] == call["request"] and response["raw"] == call["response"])
        check(label + ":configured_output_and_no_tenant_metadata", request["body"]["max_tokens"] == 8192
              and "tenant_uid" not in json.dumps(request["body"]["messages"]))
        check(label + ":run_budget", run["limits"]["max_tokens"] == 131072)
        check(label + ":no_new_legacy_partial_DTO", response["partial_review"] is None)
        text = call["response"]["choices"][0]["message"]["content"]
        correct_sources = True
        for unit in receipt["retained_units"]:
            start, end = unit["value_span"]
            correct_sources &= json.loads(text[start:end]) == unit["value"]
            correct_sources &= hashlib.sha256(text[start:end].encode()).hexdigest() == unit["value_sha256"]
            correct_sources &= contents[unit["original_artifact_id"]]["raw"] == call["response"]
            for ref in unit["resolved_refs"]:
                actual = request["source_map"][ref["source_id"]]
                correct_sources &= ref["ref"] == actual["ref"] and ref["alert_ids"] == actual.get("alert_ids", [])
            source_units += 1
        check(label + ":exact_original_units_and_source_scopes", correct_sources)
        check(label + ":quality_not_truth_pass", receipt["quality"]["prose_quality"] == "not_checked"
              and not receipt["use"]["dispatch_paths"] and not receipt["use"]["adoption_eligible"])
        paths = [u["path"] for u in receipt["retained_units"]]
        if mode == "real":
            check(label + ":complete_stop", run["state"] == "completed" and run["delivery_state"] == "complete"
                  and receipt["delivery"]["state"] == "complete" and receipt["use"]["conclusion_available"]
                  and call["response"]["choices"][0]["finish_reason"] == "stop")
            tokens = call["response"]["usage"]
            check(label + ":reported_usage", tokens["total_tokens"] == tokens["prompt_tokens"] + tokens["completion_tokens"])
            real_tokens[stage] = {k: tokens[k] for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
            if stage == "I":
                check("I:one_usable_A_four_original_members", len(source["members"]) == 4
                      and sum(v["usable"] for v in source["triage_validation"].values()) == 1
                      and len(response["validated_members"]) == 4)
                diagnosis = next(d for d in rows["incident_diagnoses"] if d["source_run_id"] == rid)
                raw = json.loads(text)
                check("I:actual_final_summary_and_pointer", diagnosis["summary"] == raw["diagnosis"]["summary"]
                      and rows["incidents"][0]["latest_diagnosis_id"] == diagnosis["id"])
            else:
                raw = json.loads(text)
                saved = next(a for a in rows["alert_assessments"] if a["source_run_id"] == rid)
                check("A:saved_original_verdict_rationale", saved["verdict"] == raw["verdict"]
                      and saved["rationale"] == raw["rationale"] and saved["confidence"] == raw["confidence"])
        else:
            check(label + ":failed_without_fabricated_core", run["state"] == "failed"
                  and not receipt["use"]["conclusion_available"])
            mother = real_mothers[stage]["response"]["choices"][0]["message"]["content"]
            check(label + ":controlled_prefix_provenance", text == mother[:call["cut_offset"]]
                  and call["mother_request_artifact_id"] == real_mothers[stage]["request_artifact_id"]
                  and bool(call["usage_note"]))
            expected_paths = ([] if mode == "empty" else ["$.members[0]"] if stage == "I"
                              else ["$.verdict", "$.confidence", "$.rationale"])
            check(label + ":only_actual_units", paths == expected_paths
                  and receipt["delivery"]["state"] == ("none" if mode == "empty" else "partial"))
            if stage == "I":
                check(label + ":actual_member_coverage", len(response["validated_members"]) == (0 if mode == "empty" else 1)
                      and len(source["members"]) == 4)
            else:
                target = next(a for a in rows["alerts"] if a["id"] == run["alert_id"])
                check("A:partial_missing_evidence_does_not_publish", "evidence_ids" not in response["received_analysis"]
                      and target["latest_triage_id"] is None)
        summaries.append({"stage": stage, "mode": mode, "run_id": rid, "receipt_id": receipt_row["id"],
                          "state": run["state"], "delivery": receipt["delivery"]["state"], "retained_paths": paths})
    check("readback_is_only_read", len(http) == 77 and all(h["method"] == "GET" and h["status"] == 200 for h in http)
          and readback["before"] == readback["after"] and readback["model_calls"] == readback["business_writes"] == 0)
    content = [h["body"] for h in http if "content_json" in h["body"]]
    check("45_content_bodies_match_saved", len(content) == 45 and all(
        b["availability"] == "available" and b["content_json"] == artifacts[b["metadata"]["id"]]["content_json"] for b in content))
    for rid in [r["id"] for r in rows["runs"]]:
        for endpoint, table in (("steps", "run_steps"), ("artifacts", "artifacts")):
            pages = [h for h in http if f"/analysis-runs/{rid}/{endpoint}" == urlsplit(h["path"]).path]
            found, cursor, valid = [], None, True
            for page in pages:
                valid &= parse_qs(urlsplit(page["path"]).query).get("cursor", [None])[0] == cursor
                found.extend(page["body"]["items"])
                cursor = page["body"]["next_cursor"]
            expected = {r["id"] for r in rows[table] if r["run_id"] == rid}
            check(rid + ":full_" + endpoint + "_pagination", valid and cursor is None and len(found) == len(expected)
                  and {r["id"] for r in found} == expected)
    check("all_receipts_accessible_by_catalog", {s["receipt_id"] for s in summaries}
          <= {b["metadata"]["id"] for b in content})
    check("slot_released", readback["slots_used"] == 0)
    return {"runs": summaries, "real_usage": real_tokens, "real_model_calls_in_source": 2,
            "controlled_responses_in_source": 3, "original_units_checked": source_units,
            "saved_HTTP_GETs": 77, "saved_artifacts": 45, "saved_steps": 16,
            "quality": "not_checked", "D4b_D4c": "not_verified"}


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    names = ["real-01/" + n + ".json" for n in ("database", "calls", "tasks", "source-mapping")]
    names += ["readback-01/" + n + ".json" for n in ("result", "database", "http")]
    hashes = {n: hashlib.sha256((SOURCE / n).read_bytes()).hexdigest() for n in names}
    result = {"state": "failed", "network_calls": 0, "new_model_calls": 0, "business_writes": 0}
    try:
        result.update(review(), state="passed")
    except Exception as exc:
        result["error"] = type(exc).__name__ + ": " + str(exc)
        raise
    finally:
        result.update(check_count=len(checks), checks=checks, source_hashes=hashes,
            source_unchanged=all(hashlib.sha256((SOURCE / n).read_bytes()).hexdigest() == h for n, h in hashes.items()))
        (OUT / "review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({k: v for k, v in result.items() if k not in {"checks", "source_hashes", "runs"}}, ensure_ascii=False))
