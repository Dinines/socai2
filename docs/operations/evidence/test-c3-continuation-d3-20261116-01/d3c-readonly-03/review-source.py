"""Read saved D3c evidence only. Does not connect to services or replay a Run."""
import hashlib
import json
import os
import socket
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "docs/operations/evidence/c3-unit-continuation-d3-20261116-01/pg-http-01"
OUTPUT = Path(__file__).parent / "d3c-readonly-03"
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(
    ROOT / "deploy/aisoc21/streaming-release-20261116-02/analysis/investigation-policy.toml")


def forbidden(*_args, **_kwargs):
    raise AssertionError("D3c independent review is offline")


socket.socket.connect = forbidden
socket.create_connection = forbidden

from app.socai2.baseline_store import digest
from app.socai2.runtime_policy import active_policy
from app.socai2.stage_delivery import validate_sources


def read(name):
    return json.loads((SOURCE / name).read_text())


checks = []


def check(name, condition):
    checks.append({"check": name, "passed": bool(condition)})
    assert condition, name


def review():
    result, rows, calls, http = [read(n + ".json") for n in ("result", "database", "calls", "http")]
    artifacts = {r["id"]: r for r in rows["artifacts"]}
    contents = {k: r["content_json"] or {} for k, r in artifacts.items()}
    run, stored = rows["runs"][0], rows["results"][0]
    check("one_new_task_attempt_run_result", all(len(rows[k]) == 1 for k in (
        "analysis_tasks", "analysis_attempts", "runs", "results")))
    check("same_completed_run", run["id"] == stored["source_run_id"] == result["run_id"]
          and run["state"] == rows["analysis_tasks"][0]["state"] == "completed")
    check("controlled_only_C3_C3_C6", [c["stage"] for c in calls] == ["C3", "C3", "C6"]
          and result["real_model_calls"] == 0 and result["substitute_model_calls"] == 3
          and all(c["controlled_replay"] and c["usage_kind"] == "explicit_test_substitute" for c in calls))
    check("current_output_budget", all(c["request"]["max_tokens"] == 16384 for c in calls))
    check("current_run_budget", run["limits"]["max_tokens"] == 393216 and run["limits"]["max_model_calls"] == 6)
    original_rows = [a for a in contents.values() if a.get("type") == "model_original_response"]
    check("three_saved_originals_equal_controlled_responses", len(original_rows) == 3
          and all(any(a["raw"] == c["response"] for a in original_rows) for c in calls))
    check("saved_JSON_digests", all(digest(a["content_json"]) == a["sha256"] for a in artifacts.values()
          if a["content_json"] is not None))
    c3_step = next(s for s in rows["run_steps"] if s["stage_code"] == "C3" and s["kind"] == "stage")
    c3 = contents[c3_step["output_artifact_id"]]
    stage_rows = [a for a in artifacts.values() if (a["content_json"] or {}).get("type") == "stage_delivery"]
    check("one_C3_stage_receipt", len(stage_rows) == 1 and stage_rows[0]["step_id"] == c3_step["id"])
    receipt_row = stage_rows[0]
    receipt = receipt_row["content_json"]
    validate_sources(receipt, contents)
    check("receipt_same_run_and_step", receipt["run_id"] == run["id"] and receipt["step_id"] == c3_step["id"])
    check("receipt_partial_not_final_conclusion", receipt["delivery"]["state"] == "partial"
          and all(receipt["use"][k] is False for k in ("conclusion_available", "adoption_eligible", "comparison_eligible")))
    check("exact_six_initial_units", [u["path"] for u in receipt["retained_units"]]
          == ["$.summary", "$.members[0]", "$.members[1]", "$.members[2]", "$.members[3]", "$.findings[0]"])
    initial_text = calls[0]["response"]["choices"][0]["message"]["content"]
    check("truncated_derived_mother_prefix", initial_text == calls[0]["complete_derived_answer"][:calls[0]["cut_offset"]]
          and calls[0]["response"]["choices"][0]["finish_reason"] == "length")
    check("blank_supplement_preserved", calls[1]["response"]["choices"][0]["message"]["content"].strip() == "")
    check("initial_and_supplement_requests_and_originals", len(receipt["originals"]) == 4)
    for unit in receipt["retained_units"]:
        start, end = unit["value_span"]
        fragment = initial_text[start:end]
        check("raw_value_span:" + unit["path"], json.loads(fragment) == unit["value"]
              and hashlib.sha256(fragment.encode()).hexdigest() == unit["value_sha256"]
              and contents[unit["original_artifact_id"]]["raw"] == calls[0]["response"])
    check("original_F1_has_no_program_statement", "statement" not in receipt["retained_units"][-1]["value"])
    check("C3_preserves_only_actual_analysis", set(c3["analysis"]) == {"summary", "members", "findings"}
          and [f["id"] for f in c3["analysis"]["findings"]] == ["F1"])
    completion = c3["basis"]["section_completion"]
    check("one_incomplete_supplement_receipt", completion["attempts"] == 1 and completion["state"] == "incomplete"
          and completion["supplement_delivery"]["state"] == "none"
          and contents[completion["artifact_id"]]["final_delivery"] == completion["final_delivery"])
    check("basis_links_saved_delivery", c3["basis"]["stage_delivery"]["artifact_id"] == receipt_row["id"])
    check("no_C4_dispatch", not receipt["use"]["dispatch_paths"] and not next(
        c for c in contents.values() if c.get("type") == "followup_dispatch")["routes"])
    c6_step = next(s for s in rows["run_steps"] if s["stage_code"] == "C6" and s["kind"] == "model")
    request = contents[c6_step["input_artifact_id"]]["payload"]
    prior = next(r for r in request["followup_boundary"]["records"] if r["block"] == "C3")
    check("actual_C6_request_equal_dispatch", request["body"] == calls[2]["request"])
    check("C6_current_profile", request["case_boundary"]["profile"] == active_policy().case_io.identity)
    check("C6_prior_analysis_role_and_link", prior["ref"]["role"] == "prior_analysis"
          and prior["ref"]["source_path"] == "$.analysis" and prior["ref"]["id"] == c3_step["output_artifact_id"])
    check("C6_F1_exact_text_without_F2_or_invented_sections", [f["id"] for f in prior["value"]["findings"]] == ["F1"]
          and prior["value"]["findings"][0]["statement"] == c3["analysis"]["findings"][0]["statement"]
          and "questions" not in prior["value"] and "followups" not in prior["value"])
    message_text = json.dumps(request["body"]["messages"], ensure_ascii=False)
    check("C6_business_gap_without_receipt_ledger", "C3仅完成已列出的部分" in message_text and not any(
        s in message_text for s in ("value_span", "value_sha256", "original_artifact_id", receipt_row["id"])))
    check("three_actual_inputs_without_tenant_uid", all("tenant_uid" not in json.dumps(c["request"]["messages"]) for c in calls))
    final = json.loads(calls[2]["response"]["choices"][0]["message"]["content"])
    check("saved_C6_conclusion_exact", stored["conclusion"] == final["conclusion"]["text"]
          and stored["conclusion_state"] == final["conclusion"]["state"])
    check("accepted_uncertain_partial_not_quality_pass", [stored[k] for k in (
        "validation_state", "conclusion_state", "delivery_state")] == ["accepted", "uncertain", "partial"]
          and result["prose_quality"] == receipt["quality"]["prose_quality"] == "not_checked")
    mother_path = ROOT / result["source_snapshot"]
    check("D2_mother_hash_preserved", hashlib.sha256(mother_path.read_bytes()).hexdigest() == result["source_sha256"])
    mother = json.loads(mother_path.read_text())
    mother_artifacts = {a["id"]: a["content_json"] or {} for a in mother["artifacts"]}
    mother_body = mother_artifacts["c6791985-b981-4a6c-b12d-3a848d9fe845"]["raw"]["choices"][0]["message"]["content"]
    check("C3_real_mother_body_hash", hashlib.sha256(mother_body.encode()).hexdigest() == calls[0]["mother_content_sha256"])
    mother_f1 = json.loads(mother_body)["findings"][0]
    adapted_f1 = receipt["retained_units"][-1]["value"]
    mapping = calls[0]["mapping"]
    identity_fields = {"alert_ids", "support_ids", "counter_ids"}
    check("F1_business_fields_unchanged", {k: v for k, v in mother_f1.items() if k not in identity_fields}
          == {k: v for k, v in adapted_f1.items() if k not in identity_fields})
    check("F1_only_declared_identity_mapping", adapted_f1["alert_ids"] == [mapping["member_aliases"][a] for a in mother_f1["alert_ids"]]
          and all(adapted_f1[k] == [mapping["source_ids"][s] for s in mother_f1[k]] for k in ("support_ids", "counter_ids")))
    initial_request = next(c["payload"] for c in contents.values() if c.get("direction") == "request"
                           and c["payload"]["body"] == calls[0]["request"])
    old_map = mother_artifacts["fce85c99-eaa3-41fe-8e60-49d94131f87a"]["payload"]["source_map"]
    members = {r["source_alert_id"]: r["alert_id"] for r in read("source-mapping.json")}
    exact_sources = True
    for sid in mother_f1["support_ids"]:
        old = old_map[sid]
        new = initial_request["source_map"][mapping["source_ids"][sid]]
        path = old["ref"]["source_path"]
        for old_id, new_id in members.items():
            path = path.replace(old_id, new_id)
        exact_sources &= new["ref"]["source_path"] == path and new["ref"]["role"] == old["ref"]["role"]
        exact_sources &= sorted(new["alert_ids"]) == sorted(members[a] for a in old["alert_ids"])
    check("F1_sources_keep_actual_field_role_and_members", exact_sources)
    check("new_run_and_case_identities", run["id"] not in {r["id"] for r in mother["runs"]}
          and result["case_id"] not in {r["id"] for r in mother["cases"]})
    check("60_successful_readonly_HTTP_receipts", len(http) == 60 and all(
        r["method"] == "GET" and r["status"] == 200 for r in http))
    check("HTTP_before_after_no_business_writes", result["before_http"] == result["after_http"])
    for endpoint, expected in (("steps", rows["run_steps"]), ("artifacts", rows["artifacts"])):
        pages = [h for h in http if urlsplit(h["path"]).path.endswith("/" + endpoint)]
        found, cursor = [], None
        for page in pages:
            check(endpoint + ":cursor:" + str(len(found)), parse_qs(urlsplit(page["path"]).query).get("cursor", [None])[0] == cursor)
            found.extend(page["body"]["items"])
            cursor = page["body"]["next_cursor"]
        check(endpoint + ":complete_directory", cursor is None and len(found) == len(expected)
              and {r["id"] for r in found} == {r["id"] for r in expected})
    content_replies = [h["body"] for h in http if "content_json" in h["body"]]
    check("44_original_and_derived_bodies_equal_storage", len(content_replies) == 44 and all(
        body["content_json"] == artifacts[body["artifact"]["id"]]["content_json"]
        and body["content_text"] == artifacts[body["artifact"]["id"]]["content_text"] for body in content_replies))
    check("stage_delivery_discovered_via_directory", result["directory_discovered_stage_delivery"][0]["id"] == receipt_row["id"])
    check("ASGI_only_no_21_deployment", result["http_transport"] == "ASGITransport" and result["deployment"] is False)
    return {"run_id": run["id"], "stage_delivery_artifact_id": receipt_row["id"],
            "saved_steps": len(rows["run_steps"]), "saved_artifacts": len(artifacts), "recorded_HTTP_GETs": len(http)}


if __name__ == "__main__":
    OUTPUT.mkdir(exist_ok=True)
    frozen = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.glob("*.json")}
    outcome = {"state": "failed", "new_network_calls": 0, "new_model_calls": 0, "new_business_writes": 0}
    try:
        outcome.update(review(), state="passed")
    except Exception as exc:
        outcome["error"] = type(exc).__name__ + ": " + str(exc)
        raise
    finally:
        outcome.update(checks=checks, check_count=len(checks), source_hashes=frozen,
            source_files_unchanged=all(hashlib.sha256((SOURCE / n).read_bytes()).hexdigest() == h for n, h in frozen.items()))
        (OUTPUT / "review.json").write_text(json.dumps(outcome, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({k: v for k, v in outcome.items() if k not in {"checks", "source_hashes"}}, ensure_ascii=False))
