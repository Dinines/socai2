"""Direct business-change boundaries; no network or model."""
from copy import deepcopy
from types import SimpleNamespace

import pytest
from app.socai2.case_update_inputs import business_view, unchanged


def context():
    assessment = {"id": "a-result-1", "source_run_id": "a-run-1", "input_material_id": "material-1",
        "verdict": "needs_review", "rationale": "需要核实授权。", "confidence": None,
        "score_state": "not_scored", "recommendations": []}
    return SimpleNamespace(update_context=None,
        alerts={"a": SimpleNamespace(alert={"latest_material_id": "material-1"},
            triage=assessment, triage_usable=True, feedback=None)},
        incidents={"i": SimpleNamespace(diagnosis_usable=True, member_ids=["a", "b"], case_member_ids=["a"],
            diagnosis_scope={"input_selection": {"selected_alert_ids": ["a", "b"]}, "case_covered_alert_ids": ["a"]},
            diagnosis={"id": "i-result-1", "source_run_id": "i-run-1", "summary": "两条告警存在关联。",
                "diagnosis": {"conclusion": "授权待核实。", "findings": [], "source_refs": [], "limitations": []},
                "open_questions": []})},
        tasks={"h": SimpleNamespace(usable_feedback=True,
            revision={"id": "h-v1", "result_text": "已确认指定主机上的操作。",
                "result_scope": {"alert_ids": ["a"], "object_keys": []}, "source_refs": []})})


def test_same_business_new_versions_or_metadata_do_not_trigger():
    original, updated = context(), context()
    updated.alerts["a"].triage.update(id="a-result-2", source_run_id="a-run-2", assessed_at="later")
    updated.incidents["i"].diagnosis.update(id="i-result-2", source_run_id="i-run-2", generated_at="later")
    updated.tasks["h"].revision.update(id="h-v2", title="改标题", changed_at="later", assignee_id="different")
    assert unchanged(original, business_view(updated))


@pytest.mark.parametrize("change", ["member", "a", "late_a", "feedback", "i", "i_scope", "i_coverage", "h", "h_scope", "h_reference", "withdraw_h"])
def test_effective_material_changes_are_detected(change):
    original, updated = context(), context()
    if change == "member":
        updated.alerts["b"] = deepcopy(updated.alerts["a"])
    elif change == "a":
        updated.alerts["a"].triage["rationale"] = "发现新的进程依据。"
    elif change == "late_a":
        original.alerts["a"].triage_usable = False
    elif change == "feedback":
        updated.alerts["a"].feedback = {**updated.alerts["a"].triage, "rationale": "人工确认来源。"}
    elif change == "i":
        updated.incidents["i"].diagnosis["diagnosis"]["conclusion"] = "新的事件结论。"
    elif change == "i_scope":
        updated.incidents["i"].diagnosis_scope["input_selection"]["selected_alert_ids"].append("c")
    elif change == "i_coverage":
        updated.incidents["i"].diagnosis["diagnosis"]["delivery_assessment"] = {
            "member_coverage": {"analyzed_alert_ids": ["a"], "unresolved_alert_ids": ["b"]}}
    elif change == "h":
        updated.tasks["h"].revision["result_text"] += "补充说明。"
    elif change == "h_scope":
        updated.tasks["h"].revision["result_scope"]["object_keys"] = ["host:one"]
    elif change == "h_reference":
        updated.tasks["h"].revision["source_refs"] = [{"type": "artifact", "id": "evidence-2"}]
    else:
        updated.tasks["h"].usable_feedback = False
    assert not unchanged(original, business_view(updated))


def test_inactive_incident_change_only_triggers_manual_check():
    original, updated = context(), context()
    updated.incidents["i"].diagnosis["diagnosis"]["conclusion"] = "新的诊断。"
    assert unchanged(original, business_view(updated), set())
    assert not unchanged(original, business_view(updated), {"i"})
    assert not unchanged(original, business_view(updated))


def test_unusable_incident_and_reordered_scope_are_not_new_business():
    original, updated = context(), context()
    original.incidents["i"].diagnosis_usable = updated.incidents["i"].diagnosis_usable = False
    updated.incidents["i"].diagnosis["summary"] = "未完成草稿"
    original.tasks["h"].revision["result_scope"]["object_keys"] = ["first", "second"]
    updated.tasks["h"].revision["result_scope"]["object_keys"] = ["second", "first"]
    assert unchanged(original, business_view(updated))


@pytest.mark.parametrize("change", ["member", "late_a", "feedback", "stale_i", "case_overlap"])
def test_automatic_case_changes_wait_for_usable_incident_business(change):
    original, updated = context(), context()
    if change == "member":
        updated.alerts["b"] = deepcopy(updated.alerts["a"])
    elif change == "late_a":
        original.alerts["a"].triage_usable = False
    elif change == "feedback":
        updated.alerts["a"].feedback = {**updated.alerts["a"].triage, "rationale": "新增人工告警反馈"}
    elif change == "stale_i":
        updated.incidents["i"].diagnosis_usable = False
    else:
        updated.incidents["i"].diagnosis_scope["case_covered_alert_ids"].append("b")
    assert unchanged(original, business_view(updated), {"i"})
    assert not unchanged(original, business_view(updated))


def test_effective_case_H_still_updates_automatically_without_events():
    original, updated = context(), context()
    updated.tasks["h"].revision["result_text"] = "新的人工调查结论"
    assert not unchanged(original, business_view(updated), set())
