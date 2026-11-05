"""Read closed m2 evidence; local counterexamples are never model/business results."""
import ast
import copy
import hashlib
import json
from pathlib import Path

from app.socai2 import baseline_analysis_contract as analysis
from app.socai2 import incident_diagnosis_contract as incident
from app.socai2.baseline_context import Context, feedback_validity
from app.socai2.model_input_view import items

ROOT = Path(__file__).resolve().parents[2]
M2 = ROOT / "docs/operations/evidence/socai2-model-comparison-20261104/m2"
OUT = ROOT / "docs/operations/evidence/socai2-semantic-boundaries-20261105/local-audit.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text("utf-8"))


def main():
    if OUT.exists():
        raise RuntimeError("fixed audit already exists; do not overwrite")
    originals = {p: sha(p) for p in M2.rglob("*") if p.is_file()}
    bundle = read(M2 / "plan-and-packets.json")
    packets = {p["id"]: p for p in bundle["packets"]}
    received = {r["cell"]: r for r in read(M2 / "parsed-results.json")["cells"]}
    for row in received.values():
        assert sha(M2 / "remote" / (row["cell"] + "-result.json")) == row["result_sha256"]
    ip, cp = packets["I-current"], packets["C3-current"]
    ia = received["I-current-deepseek"]["answer"]
    ca = received["C3-current-deepseek"]["answer"]
    ctx = Context.model_validate(cp["context"])
    incident.parse(json.dumps(ia), ip["source_map"], ip["data"])

    def check(value):
        try:
            analysis.parse(json.dumps(value), cp["source_map"], ctx, cp["coverage"])
        except analysis.AnalysisRejected as exc:
            return {"accepted": False, "reason": str(exc)}
        return {"accepted": True, "reason": None}

    assert check(ca)["accepted"]
    human_index = next(i for i, f in enumerate(ca["followups"]) if f["mode"] == "human")
    human = ca["followups"][human_index]
    a0 = human["alert_ids"][0]
    a1 = next(a for a in ctx.alerts if a != a0)
    visible = items(ip["data"])
    selected = {i["field"]: i for i in visible if i["alert_ids"] == [a0]}
    action, outcome = [selected["$.ocsf_json.activity." + k] for k in ("action", "outcome")]
    assert action["value"] == "process_start" and outcome["value"] == "success"
    findings = {f["id"]: f for f in ia["findings"]}
    assert {action["id"], outcome["id"]} <= set(findings["F2"]["source_ids"])
    assert "脚本执行成功" in findings["F2"]["statement"]
    assert "进程启动成功" in ca["findings"][0]["statement"]
    assert "出站连接" in human["objective"] and human["alert_ids"] == [a0]

    experiments = []
    for name, field, value, expected in [
        ("formal_source_from_other_member", "source_ids", [next(k for k, v in cp["source_map"].items()
            if v["alert_ids"] == [a1])], "source_member_mismatch"),
        ("object_outside_whole_case", "object_keys", ['["host","outside-frozen-case"]'], "followup_objects_outside_run"),
        ("object_of_other_case_member", "object_keys", ['["ip","198.51.100.20"]'], None),
        ("objective_only_narrowed_to_declared_member", "objective", "确认synthetic-operator执行inventory.ps1是否获授权。", None),
    ]:
        value_copy = copy.deepcopy(ca)
        value_copy["followups"][human_index][field] = value
        result = check(value_copy)
        assert result["reason"] == expected, (name, result)
        experiments.append({"name": name, "changed_field": field, "value": value, **result,
            "kind": "synthetic_counterexample_not_a_model_answer_or_adoption"})
    assert all(q.scope.kind == "whole_case" and set(map(str, q.scope.alert_ids)) == set(ctx.alerts)
        for q in ctx.questions)

    # Inspect the actual C6 projection, rather than assuming which route fields survive.
    path = ROOT / "services/api/app/socai2/baseline_delivery.py"
    tree = ast.parse(path.read_text("utf-8"))
    routes_expr = next(v for node in ast.walk(tree) if isinstance(node, ast.Dict)
        for k, v in zip(node.keys, node.values, strict=True)
        if isinstance(k, ast.Constant) and k.value == "followup_execution")
    keys = ast.literal_eval(routes_expr.body.elt.generators[0].iter)
    assert keys == ("question_id", "mode", "state", "reason")
    examples = [{"followup_index": i, "question_id": "authorization", "mode": "human",
        "state": "handoff", "reason": "human_confirmation_required_no_task_created"} for i in (0, 1)]
    reduced = [{k: r[k] for k in keys} for r in examples]
    assert reduced[0] == reduced[1]
    scope = ctx.scope.model_dump(mode="json")
    scope.update(alert_ids=[a0], object_keys=[])
    feedback = {"state": "completed", "result_text": "仅确认inventory.ps1获授权；未确认网络连接。", "result_scope": scope}
    assert feedback_validity(feedback, list(ctx.alerts)) == (True, [])
    assert feedback["result_scope"]["alert_ids"] == [a0]
    invalid, reasons = feedback_validity({**feedback, "result_scope": None}, list(ctx.alerts))
    assert not invalid and "feedback_scope_not_provided_or_invalid" in reasons
    assert originals == {p: sha(p) for p in originals}
    code_names = ["baseline_semantics", "incident_diagnosis_contract", "baseline_analysis_contract",
        "baseline_context", "baseline_deep", "baseline_evidence", "baseline_executor",
        "baseline_reanalysis", "baseline_reasoning", "baseline_delivery", "human_task_service", "human_task_contracts"]
    code = [ROOT / f"services/api/app/socai2/{name}.py" for name in code_names]
    result = {
        "status": "local_analysis_only_no_business_changes",
        "date": "2026-11-05",
        "original_m2_files_unchanged": len(originals),
        "evidence_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): h for p, h in originals.items()},
        "code_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in code},
        "script_sha256": sha(Path(__file__)),
        "actual_answers": {"I_parser_accepts": True, "C3_parser_accepts": True,
            "I_action_and_outcome": [action, outcome], "I_F2": findings["F2"],
            "C3_F1": ca["findings"][0], "C3_F2": ca["findings"][1], "C3_human_followup": human,
            "C3_insider": next(d for d in ca["domains"] if d["name"] == "insider")},
        "interpretation_limits": ["parser acceptance is not semantic entailment",
            "I and C3 used frozen historical priors, not a new I-to-C3 chain",
            "no independent benign/malicious ground truth; no misclassification rate",
            "C6 projection ambiguity is a local design observation, not a witnessed m2 final-report error"],
        "counterexamples": experiments,
        "deep_question_scope": {"all_frozen_questions_whole_case": True,
            "followup_member_focus_does_not_override_question_or_binding_scope": True},
        "C6_projection": {"kept_fields": keys, "dropped_followup_index": True,
            "synthetic_original_routes": examples, "synthetic_visible_routes": reduced,
            "full_dispatch_retained_by_source_code": True,
            "reanalysis_followups_are_optional_candidates": True},
        "human_feedback": {"historical_whole_case_members_remain_literal": True,
            "missing_result_scope_rejected_as_feedback": True,
            "formal_task_creation_or_database_writes_performed": False},
        "new_real_model_calls": 0, "new_business_runs": 0, "deployments": 0,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"saved": str(OUT.relative_to(ROOT)), "original_files_verified": len(originals),
        "original_answers_checked": 2, "synthetic_counterexamples": len(experiments),
        "real_calls": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
