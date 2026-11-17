"""Prepared-size rejection retains business input without making it dispatchable."""
import test_socai2_case_model_boundary as base_tests
from app.socai2 import case_model_boundary as boundary
from app.socai2.baseline_capacity import capacity_failure
from app.socai2.baseline_context import Context

configured = base_tests.configured
sample = base_tests.sample


def test_oversized_initial_view_keeps_unsent_messages_and_all_members(sample, monkeypatch):
    context = Context.model_validate(sample["context"])
    monkeypatch.setattr(boundary, "draft_limit", lambda: 1)
    prepared = boundary.build(context, sample["context_id"], [], [], sample["materials"])
    assert prepared["ready"] is False and prepared["reason"] == "case_input_exceeds_prepared_limit"
    assert prepared["messages"] == [] and len(prepared["unsent_messages"]) == 2
    assert set(prepared["case_boundary"]["member_aliases"]) == set(context.alerts)
    assert prepared["source_map"] and prepared["input_ledger"]["records"]
    assert capacity_failure([{"error":{"code":prepared["reason"]}}]) == prepared["reason"]
