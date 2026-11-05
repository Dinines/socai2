"""Summarize ended m2 with explicit human review; no remote or model calls."""
import json

from evaluate_socai2_models_20261104 import ROOT, sha, write

OUT = ROOT / "docs/operations/evidence/socai2-model-comparison-20261104/m2"

REVIEW = {
    "A0-current-small": {"quality": "unsupported_benign_rejected",
        "findings": ["benign/0.95 still relies on synthetic labels and host/user names as authorization",
            "new decision_basis gate rejects the label-plus-observation mixture; main references alone would meet the older direct-source gate"]},
    "A1-current-small": {"quality": "unsupported_benign_rejected",
        "findings": ["benign/0.95 still treats fixture/vendor labels as proof of harmless authorized traffic",
            "both main-direct-source and decision_basis gates reject these label-only references"]},
    "A0-current-deepseek": {"quality": "no_answer_http400_exact_reason_unknown",
        "findings": ["HTTP400 in 0.176s; no generated answer or usage; no retry",
            "request-error response body was not captured, so exact incompatible parameter is not established"]},
    "A1-current-deepseek": {"quality": "no_answer_http400_exact_reason_unknown",
        "findings": ["HTTP400 in 0.182s; same A output-contract change; I/C3 succeed on same endpoint",
            "nullable decision_basis is a compatibility hypothesis, not a proven cause"]},
    "I-current-small": {"quality": "pending_but_duplicate_reference_and_fact_errors",
        "findings": ["summary stays pending, but repeats N1_S14 in the network member source_ids; rejected",
            "incorrectly says both alerts share synthetic-operator although network actor is not supplied",
            "says command-line parameters are missing although PowerShell -File command is visible; network attribution remains unknown"]},
    "I-current-deepseek": {"quality": "parser_accepted_main_judgment_reasonable_precision_not_passed",
        "findings": ["keeps both members unresolved, TCP distinct from HTTPS, no proven process/network causality",
            "F2 describes script execution success while source proves process-start success, not script completion",
            "all formal references are current N-prefixed IDs; old rationale aliases remain untouched in input"]},
    "C3-current-small": {"quality": "no_answer_http408_timeout",
        "findings": ["HTTP408 after45.136s; bounded gateway window contains litellm.Timeout",
            "not the m1 immediate uniqueItems HTTP400; no complete response, no quality conclusion or full compatibility acceptance",
            "exact timeout owner/value remains unconfirmed; no settings changed or extra request"]},
    "C3-current-deepseek": {"quality": "parser_accepted_provisional_reasonable_followup_scope_issue",
        "findings": ["two members/six questions/four domains complete; no causal chain, HTTPS, or authorization asserted",
            "undetermined domains retain related findings and parse successfully; source-empty/budget-skip/unavailable remain distinct",
            "human followup declares only process alert but asks authorization for the network connection too; objective/scope mismatch needs correction",
            "insider reason says destination evidence is absent although connection endpoint is supplied; exfiltration destination versus connection endpoint needs precise wording",
            "observed findings here contain observation refs only; mixed event-time exception was exercised offline, not by this fresh output"]},
}


def main():
    def read(path):
        return json.loads(path.read_text("utf-8"))
    parsed = read(OUT / "parsed-results.json")
    rows = {r["cell"]: r for r in parsed["cells"]}
    assert set(rows) == set(REVIEW) and parsed["attempts"] == 8 and parsed["responses"] == 5
    completion = read(OUT / "remote/completion.json")
    assert completion["protected_unchanged"] and completion["cells"] == 8
    assert len(list((OUT / "remote").glob("*-intent.json"))) == 9  # eight plus batch-intent
    assert len(list((OUT / "remote").glob("*-result.json"))) == 8
    assert all(read(p)["attempt"] == 1 for p in (OUT / "remote").glob("*-intent.json") if p.name != "batch-intent.json")
    assert all(sha((OUT / "remote" / (r["cell"] + "-result.json")).read_bytes()) == r["result_sha256"] for r in rows.values())
    diagnostics = read(OUT / "offline-diagnostics.json")
    old = read(ROOT / "docs/operations/socai2-model-evaluation-m1-20261104.json")
    assert all(sha((ROOT / p).read_bytes()) == h for p, h in old["evidence_sha256"].items())
    transport = read(OUT / "remote-verification.json")
    assert transport["all_remote_requests_match_frozen_local_bodies"]
    comparisons = []
    old_rows = {r["cell"]: r for r in read(OUT.parent / "m1/parsed-results.json")["cells"]}
    for cid, row in rows.items():
        prior = old_rows[cid]
        comparisons.append({"cell": cid,
            "m1_verdict": prior.get("answer", {}).get("verdict"), "m2_verdict": row.get("answer", {}).get("verdict"),
            "m1_parser_accepted": prior.get("current_parser_accepts"), "m2_parser_accepted": row.get("current_parser_accepts"),
            "m1_http_status": prior.get("http_status"), "m2_http_status": row.get("http_status")})
    summary = {"batch": "m2", "status": "ended_no_retry_not_overall_accepted", "http_attempts": 8,
        "model_answers": 5, "http400": 2, "http408": 1, "known_total_tokens": parsed["known_total_tokens"],
        "failed_request_usage_unknown": 3, "cost_state": "unpriced",
        "received_answers_wire_and_canonical_schema_valid": all(r["wire_schema_valid"] and r["canonical_schema_valid"] for r in rows.values() if "answer" in r),
        "parser_acceptances": sum(r.get("current_parser_accepts") is True for r in rows.values()),
        "received_answer_truncations": sum(r.get("finish_reason") not in (None, "stop") for r in rows.values()),
        "manual_review": [{"cell": cid, **value} for cid, value in REVIEW.items()],
        "comparison_to_m1": comparisons,
        "new_findings": [
            {"id": "M2-D01", "finding": "DeepSeek A HTTP400; exact error reason lost by error capture path", "confirmed": True},
            {"id": "M2-D02", "finding": "role-only decision_basis is insufficient for authorization truth", "evidence": diagnostics["basis_gate_counterexample"]},
            {"id": "M2-D03", "finding": "I budget now omits network detection bundle while retaining extra class/time leaves", "evidence": diagnostics["visible_field_comparison_to_m1"]["I-current"]},
            {"id": "M2-O01", "finding": "small C3 HTTP408 at45.136s with correlated gateway Timeout; timeout source not identified", "confirmed": True},
            {"id": "M2-Q01", "finding": "accepted Deep I/C3 still have activity-success precision and human-followup scope issues", "confirmed": True}],
        "business_runs": 0, "business_adoptions": 0, "tool_calls": 0, "new_deployment": False,
        "protected_services_and_configs_unchanged": True, "m1_original_evidence_unchanged": True,
        "n10_and_r7": "local_candidate_only_held_after_failed_A_compatibility_and_remaining_quality_gaps",
        "limits": ["two_synthetic_alerts_only_one_attempt_per_condition",
            "I_C_priors_frozen_from_history_not_m2_A_outputs", "no_full_Deep_C6_H_or_second_C",
            "DeepSeek_A_has_no_answer_for_quality_comparison", "small_C3_has_no_answer_for_quality_comparison",
            "A_visible_values_unchanged_vs_m1_I_optional_projection_differs",
            "known_inline_reference_policy_not_exercised_by_fresh_Deep_A_due_HTTP400",
            "offline_counterfactual_only_no_original_answer_edit_or_adoption"],
        "evidence_sha256": {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in sorted(OUT.rglob("*")) if p.is_file()},
        "script_sha256": {p: sha((ROOT / p).read_bytes()) for p in [
            "docs/operations/evaluate_socai2_m2_20261104.py", "docs/operations/inspect_socai2_m2_20261104.py",
            "docs/operations/diagnose_socai2_m2_20261104.py", "docs/operations/summarize_socai2_m2_20261104.py"]}}
    write(ROOT / "docs/operations/socai2-model-evaluation-m2-20261104.json", summary)
    print(json.dumps({k: summary[k] for k in ["status", "http_attempts", "model_answers", "known_total_tokens", "parser_acceptances"]}))


if __name__ == "__main__":
    main()
