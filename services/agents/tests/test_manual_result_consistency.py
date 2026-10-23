"""Four-stage manual investigation checks precede both downstream consumers.

The compiled graph is real; models, prefetch and storage are local doubles.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from app.investigator import orchestrator as manual
from app.investigator import report_writer_agent as reporter
from app.investigator import responder_agent as response_agent
from app.investigator.state import ForensicFindings, InvestigatorState, StepKind


class _Tracker:
    def __init__(self, **_kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        pass

    def summary(self):
        return {"total_tokens": 0, "measured_call_count": 0}


@pytest.fixture
def isolated_manual(monkeypatch):
    for key in ("DATABASE_URL", "DATABASE_DSN"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("AISOC_AGENT_GROUNDEDNESS_GATE", "1")
    monkeypatch.setenv("AISOC_AGENT_GROUNDEDNESS_FLOOR", "0.6")

    async def no_http(*_args, **_kwargs):
        pytest.fail("manual result contract unexpectedly attempted HTTP")

    monkeypatch.setattr(httpx.AsyncClient, "send", no_http)
    monkeypatch.setattr(manual, "_GRAPH", None)
    monkeypatch.setattr(manual, "prefetch_context_bundle_dict", AsyncMock(return_value={}))
    monkeypatch.setattr(manual, "CostTracker", _Tracker)
    tenant = uuid4()
    monkeypatch.setattr(manual.ledger, "start_run", AsyncMock(return_value=tenant))
    for name in ("record_event", "record_artifact", "complete_run"):
        monkeypatch.setattr(manual.ledger, name, AsyncMock())
    return tenant


@pytest.mark.asyncio
@pytest.mark.parametrize("surface", ["run", "stream"])
async def test_check_precedes_response_and_report_on_both_entry_points(isolated_manual, monkeypatch, surface):
    order = []
    observed = {}
    run_id = uuid4()

    async def recon(state_dict):
        order.append("recon")
        state = InvestigatorState.from_dict(state_dict)
        state.status = "running"
        state.log(StepKind.RECON, "ReconAgent", "Local evidence fixture")
        return state.to_dict()

    async def forensic(state_dict):
        order.append("forensic")
        state = InvestigatorState.from_dict(state_dict)
        state.forensic = ForensicFindings(
            root_cause_hypothesis="Compromise at 203.0.113.77 via c2.invalid and CVE-2024-99999.",
            summary="Compromise at 203.0.113.77 via c2.invalid and CVE-2024-99999.",
            confidence=0.95,
        )
        return state.to_dict()

    original_check = manual._apply_groundedness

    def check(state):
        order.append("check")
        original_check(state)

    async def responder(state_dict):
        order.append("responder")
        state = InvestigatorState.from_dict(state_dict)
        observed["responder"] = state.forensic.model_dump()
        assert state.forensic.confidence < 0.95
        assert "unverified" in state.forensic.summary
        assert state.run_id == run_id
        return state.to_dict()

    async def report(state_dict):
        order.append("report")
        state = InvestigatorState.from_dict(state_dict)
        observed["report"] = state.forensic.model_dump()
        state.report_md = state.forensic.summary
        state.status = "completed"
        return state.to_dict()

    monkeypatch.setattr(manual, "run_recon", recon)
    monkeypatch.setattr(manual, "run_forensic", forensic)
    monkeypatch.setattr(manual, "_apply_groundedness", check)
    monkeypatch.setattr(manual, "run_responder", responder)
    monkeypatch.setattr(manual, "run_report_writer", report)
    runner = manual.InvestigatorOrchestrator()
    args = dict(case_id="CASE-LOCAL", tenant_id=str(isolated_manual), run_id=run_id,
                alert_summary="Supplied source address", raw_alert={"src_ip": "10.1.2.3"})
    if surface == "run":
        final = await runner.run(**args)
        assert final.run_id == run_id
        result = final.to_dict()
    else:
        events = [event async for event in runner.stream(**args)]
        assert events[-1]["type"] == "done"
        assert events[-1]["run_id"] == str(run_id)
        result = events[-1]["state"]

    assert order == ["recon", "forensic", "check", "responder", "report"]
    assert result["forensic"] == observed["responder"] == observed["report"]
    reports = [call.kwargs for call in manual.ledger.record_artifact.await_args_list
               if call.kwargs["kind"] == "report_md"]
    assert len(reports) == 1
    assert reports[0]["content"] == result["report_md"] == result["forensic"]["summary"]
    assert reports[0]["run_id"] == run_id
    assert manual.ledger.start_run.await_args.kwargs["run_id"] == run_id
    assert manual.ledger.complete_run.await_args.kwargs["run_id"] == run_id


@pytest.mark.asyncio
@pytest.mark.parametrize("demoted, finish_reason", [(False, "stop"), (True, "stop"), (True, "length")])
async def test_downstream_adoption_obeys_check_and_preserves_model_audit(
    isolated_manual, monkeypatch, demoted, finish_reason,
):
    """Even a confident replacement model cannot undo the program decision."""
    model_calls = []
    prompts = []
    claimed_ip = "203.0.113.77" if demoted else "10.1.2.3"
    state = InvestigatorState(
        case_id="CASE-LOCAL", raw_alert={"src_ip": "10.1.2.3"},
        forensic=ForensicFindings(
            root_cause_hypothesis=f"Suspicious activity involving {claimed_ip}.",
            summary=f"Suspicious activity involving {claimed_ip}.", confidence=0.95,
        ),
    )
    manual._apply_groundedness(state)
    response_json = json.dumps({
        "recommended_actions": [{"priority": 1, "action": "ISOLATE_UNVERIFIED_HOST", "risk": "high"}],
        "containment_steps": ["ISOLATE_UNVERIFIED_HOST"],
        "eradication_steps": ["DELETE_UNVERIFIED_ARTEFACT"],
        "recovery_steps": ["RESTORE_UNVERIFIED_HOST"],
        "risk_level": "critical", "summary": "CONFIRMED_MODEL_CLAIM",
    })
    model_report = "# CONFIRMED_MODEL_REPORT\nThe invented attack is confirmed; isolation was completed."

    def make_model(alias, **kwargs):
        model_calls.append((alias, kwargs))
        return alias

    async def invoke(alias, messages):
        prompts.append((alias, messages[1].content))
        return SimpleNamespace(
            content=response_json if alias == "investigation" else model_report,
            response_metadata={"finish_reason": "stop" if alias == "investigation" else finish_reason},
        )

    for module in (response_agent, reporter):
        monkeypatch.setattr(module, "make_chat_model", make_model)
        monkeypatch.setattr(module, "resolve_model_alias", lambda alias: alias)
        monkeypatch.setattr(module, "safe_ainvoke", invoke)
        monkeypatch.setattr(module, "record_llm_call", lambda *_args, **_kwargs: None)

    response_state = InvestigatorState.from_dict(await response_agent.run_responder(state.to_dict()))
    final = InvestigatorState.from_dict(await reporter.run_report_writer(response_state.to_dict()))

    expected_status = "needs_review" if demoted else "indicator_check_passed"
    assert response_state.forensic.validation == final.forensic.validation == state.forensic.validation
    assert final.forensic.validation["status"] == expected_status
    assert all(expected_status in prompt for _, prompt in prompts)
    assert [alias for alias, _ in model_calls] == ["investigation", "report"]
    assert all(kwargs == {"temperature": 0, "max_tokens": response_agent.max_completion_tokens()}
               for _, kwargs in model_calls)
    original_outputs = [entry.metadata["response"] for entry in final.audit_log if entry.kind == StepKind.LLM_RESPONSE]
    assert original_outputs == [response_json, model_report]
    report_entry = next(entry for entry in final.audit_log if entry.kind == StepKind.REPORT)

    if demoted:
        assert final.responder.risk_level == "unknown"
        assert final.responder.dry_run is True
        assert final.responder.containment_steps == final.responder.eradication_steps == final.responder.recovery_steps == []
        assert "verify the unsupported indicators" in final.responder.recommended_actions[0]["action"]
        assert "CONFIRMED_MODEL_CLAIM" not in final.responder.summary
        assert "CONFIRMED_MODEL_REPORT" not in final.report_md
        assert "CONFIRMED_MODEL_REPORT" not in final.report_html
        assert "needs_review" in final.report_md
        assert "needs_review" in final.report_html
        assert "Forensic confidence after the check: 0%" in final.report_md
        assert report_entry.metadata["report_source"] == "review_handoff"
    else:
        # Indicator matching must not pretend to validate the report's semantics.
        # The un-demoted behavior remains unchanged in this limited repair.
        assert final.responder.summary == "CONFIRMED_MODEL_CLAIM"
        assert model_report in final.report_md
        assert report_entry.metadata["report_source"] == "model"

    assert final.status == ("failed" if finish_reason == "length" else "completed")
    if finish_reason == "length":
        assert "finish_reason=length" in final.error
        assert "finish_reason=length" in final.report_md
