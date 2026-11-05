"""m1 accounting plus explicitly reviewed conclusions; no model or DB calls."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/operations/evidence/socai2-model-comparison-20261104/m1"

REVIEW = {
    "A0-old-small": ("unsupported_benign", ["Used Synthetic/fixture/user/host labels as proof of controlled benign testing."]),
    "A0-current-small": ("unsupported_benign", ["Same error after compaction; asserted controlled non-production simulation without such evidence.", "Rendered the Windows script path without its backslashes."]),
    "A1-old-small": ("unsupported_benign", ["Used fixture/domain labels to exclude threat and advise no further investigation.", "Asserted a future timestamp and test-plan context without evidence."]),
    "A1-current-small": ("unsupported_benign", ["Used fixture/.invalid labels to assert normal testing, no real destination and no malicious characteristics."]),
    "A0-old-deepseek": ("appropriate_main_judgment_with_precision_issues", ["Retained needs_review and uncertainty; did not equate empty queries with safety.", "Said complete command-line parameters were missing although the supplied cmd_line value was present; should distinguish additional telemetry from received fields."]),
    "A0-current-deepseek": ("appropriate_main_judgment_but_requires_correction", ["Retained needs_review; current S20/S21/S27/S28 are visible real values but absent from evidence_ids.", "Called the host managed despite the empty asset lookup; that property is unproven."]),
    "A1-old-deepseek": ("appropriate_main_judgment_but_unsupported_protocol", ["Retained needs_review and no process-to-network causality.", "Called the connection HTTPS although only tcp and destination port 443 were provided."]),
    "A1-current-deepseek": ("appropriate_main_judgment_but_reference_failure", ["Retained needs_review, TCP and unknown process/user/authorization.", "Inline S20-S30 range is not paired with evidence_ids; current parser detects endpoints S20 and S30, not an expanded range."]),
    "I-current-small": ("pending_main_judgment_but_coverage_and_reference_failure", ["Kept pending and did not assert a proven process-to-network chain.", "Both members have analyzed prose and sources but state not_reviewed; summary references not paired.", "Used path without backslashes and described labels as an actual synthetic environment."]),
    "I-current-deepseek": ("parser_accepted_main_judgment_reasonable_with_precision_issue", ["Kept pending, separated members and distinguished TCP443 from HTTPS and temporal proximity from causality.", "Said no time window where membership fields were null; should say the merge window was not provided."]),
    "C3-current-small": ("no_answer_provider_schema_incompatibility", ["HTTP400 in 0.162 seconds; bounded gateway logs identify Grammar error: Unimplemented keys: uniqueItems.", "This is wire-schema compatibility, not a measured reasoning failure."]),
    "C3-current-deepseek": ("provisional_content_reasonable_but_contract_rejected", ["Covered two members, six questions, four undetermined domains; no HTTPS or proven causal chain; source states accurately distinguish budget skips from graph unavailable.", "Observed findings include source_label event timestamps S22/S23; parser refuses mixed evidence roles.", "Undetermined identity/insider domains link F1/F2, forbidden by local parser but permitted by sent schema."])
}


def main():
    parsed = json.loads((OUT / "parsed-results.json").read_text("utf-8"))
    plan = json.loads((OUT / "plan-and-packets.json").read_text("utf-8"))
    rows = {r["cell"]: r for r in parsed["cells"]}
    packets = {p["id"]: p for p in plan["packets"]}
    assert set(rows) == set(REVIEW) and len(rows) == 12
    completion = json.loads((OUT / "remote/completion.json").read_text("utf-8"))
    assert completion["protected_unchanged"]
    comparison = []
    for sample in ("A0", "A1"):
        result = {"sample": sample, "user_bytes_old": packets[sample + "-old"]["user_bytes"],
            "user_bytes_current": packets[sample + "-current"]["user_bytes"], "backends": {}}
        for backend in ("small", "deepseek"):
            old, new = [rows[f"{sample}-{version}-{backend}"] for version in ("old", "current")]
            result["backends"][backend] = {"verdict_old": old["answer"]["verdict"], "verdict_current": new["answer"]["verdict"],
                "confidence_old": old["answer"]["confidence"], "confidence_current": new["answer"]["confidence"],
                "input_tokens_old": old["usage"]["input_tokens"], "input_tokens_current": new["usage"]["input_tokens"],
                "parser_old": old["current_parser_accepts"], "parser_current": new["current_parser_accepts"]}
        comparison.append(result)
    summary = {"batch": "m1", "status": "ended_no_retry_quality_not_passed", "requested_cells": 12,
        "http_attempts": 12, "model_responses": parsed["response_received"], "provider_http_400": 1,
        "known_total_tokens": parsed["known_total_tokens"], "failed_request_usage": "not_reported",
        "cost_state": "unpriced", "all_11_received_answers_valid_against_sent_schema": all(r.get("schema_valid") is True for r in rows.values() if r["transport_state"] == "response_received"),
        "current_parser_acceptances": sum(r.get("current_parser_accepts") is True for r in rows.values()),
        "responses_truncated": sum(r.get("finish_reason") not in (None, "stop") for r in rows.values()),
        "business_runs": 0, "business_writes": 0, "business_adoptions": 0, "tool_calls": 0,
        "original_services_and_model_configs_unchanged": True, "new_deployment": False,
        "paired_A_comparison": comparison,
        "manual_review": [{"cell": name, "status": status, "findings": notes} for name, (status, notes) in REVIEW.items()],
        "design_findings": [
            {"id": "M1-D01", "finding": "Provider does not implement uniqueItems in grammar schema", "evidence": "remote-verification.json", "priority": 1},
            {"id": "M1-D02", "finding": "Duplicated inline and structured source lists fail even for visible correct facts", "evidence": "offline-diagnostics.json", "priority": 1},
            {"id": "M1-D03", "finding": "Old rationale aliases share the current namespace and also trigger the literal-name exception", "evidence": "offline-diagnostics.json", "priority": 1},
            {"id": "M1-D04", "finding": "Timestamp context and observation support share one list; accurate activity facts rejected for extra source_label time refs", "evidence": "offline-diagnostics.json", "priority": 1},
            {"id": "M1-D05", "finding": "Sent Domain schema permits finding links for undetermined domains, while the parser forbids them", "evidence": "offline-diagnostics.json", "priority": 1},
            {"id": "M1-D06", "finding": "Known source IDs and the presence of any observation do not prove a benign/authorized judgment; all four unsupported 9B benign answers passed", "evidence": "parsed-results.json", "priority": 1}
        ],
        "limits": ["two_synthetic_source_records_only", "one_trial_per_cell_not_general_accuracy",
            "I_and_C_priors_are_fixed_historical_DeepSeek_judgments_not_this_batch_A_outputs",
            "different_provider_protocols_and_reasoning_policies", "A_old_new_changes_projection_prompt_and_contract_not_only_grouping",
            "no_Deep_C6_H_second_C_or_final_case_judgment_comparison", "counterfactual_local_parses_never_adopted"],
        "evidence_sha256": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(OUT.rglob("*.json"))}}
    target = ROOT / "docs/operations/socai2-model-evaluation-m1-20261104.json"
    with target.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({k: summary[k] for k in ("status", "http_attempts", "model_responses", "known_total_tokens", "current_parser_acceptances", "responses_truncated")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
