"""Normal report material, source failures and actual length finish reason."""
import hashlib
import json
from datetime import datetime
from types import SimpleNamespace

import pytest
import httpx

from app.investigator import forensic_agent as forensic
from app.investigator import report_writer_agent as report
from app.investigator.state import AuditEntry, ForensicFindings, InvestigatorState, ResponderPlan, StepKind
from app.llm.prompt_registry import default_registry, load_lock
from app.llm.factory import make_chat_model

NAMES = {"recon.system": "2", "forensic.system": "3", "responder.system": "2", "report_writer.system": "2"}
HEADINGS = ("Executive Summary", "Timeline of Events", "IOC Analysis", "MITRE ATT&CK Mapping",
            "Forensic Findings", "Response Plan", "Recommendations", "Appendix: Enrichment Data")


def test_only_four_prompts_change_with_versions_and_output_schemas_preserved():
    registry = default_registry()
    assert registry.verify_against_lock(load_lock()) == []
    assert {name: registry.get(name).version for name in NAMES} == NAMES
    other = {name: value for name, value in registry.as_lock().items() if name not in NAMES}
    assert len(other) == 18
    assert hashlib.sha256(json.dumps(other, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == "08c1dc53a11d976a70528002f5f2daecae72df05223d01a3b050fc353e9ad677"
    schemas = {"forensic.system": "26c7e764437533c48291cd77d118eeb2cdc7202fb31934aba5fb91e79adb43f5",
               "recon.system": "8d567707a4956187b1923cb0c44f0d5d5a70a3833a420c28d4b01abecb2962e7",
               "responder.system": "289cae425da2a305909ee501a148bbedb16253e564a3bf5107f7215a8bc70d4f"}
    for name, digest in schemas.items():
        value = registry.get(name).text
        assert hashlib.sha256(value[value.index("Respond ONLY"):].encode()).hexdigest() == digest
    assert registry.get("triage.system").version == "5"


def material_state():
    return InvestigatorState(case_id="marked-case", tenant_id="marked-tenant",
        alert_summary="Detector label, not proof of authorization",
        raw_alert={"alerts": [{"id": "source-alert", "title": "Failed authentication", "event_time": "2026-10-21T04:00:00+08:00",
                              "description": "Ten failed attempts; success is unknown.", "full_log": "outcome=failure"}]},
        forensic=ForensicFindings(timeline=[{"ts": "2026-10-21T04:00:00+08:00", "event": "Observed failed authentication", "src": "source-alert"}]),
        responder=ResponderPlan(recommended_actions=[{"action": "Review identity-provider records", "rationale": "Success is unknown", "priority": 1}]))


def stub_report(monkeypatch, *, finish="stop", content="# Marked report\nEvidence remains unknown.", error=None):
    calls = []
    def model(*args, **kwargs):
        assert kwargs["max_tokens"] == 2048
        return object()
    async def invoke(_model, messages):
        calls.append(messages)
        if error:
            raise error
        return SimpleNamespace(content=content, response_metadata={"finish_reason": finish, "token_usage": {"total_tokens": 17}})
    monkeypatch.delenv("AISOC_INVESTIGATOR_MAX_COMPLETION_TOKENS", raising=False)
    monkeypatch.setattr(report, "make_chat_model", model)
    monkeypatch.setattr(report, "safe_ainvoke", invoke)
    monkeypatch.setattr(report, "record_llm_call", lambda *args, **kwargs: None)
    return calls


@pytest.mark.asyncio
async def test_actual_report_message_contains_existing_timeline_actions_and_source_facts(monkeypatch):
    calls = stub_report(monkeypatch)
    result = await report.run_report_writer(material_state().to_dict())
    assert len(calls) == 1 and result["status"] == "completed"
    text = calls[0][1].content
    for value in ("2026-10-21T04:00:00+08:00", "Observed failed authentication", "source-alert",
                  "Review identity-provider records", "outcome=failure", "proposed/dry-run"):
        assert value in text
    assert "[Timestamp]" not in text


@pytest.mark.asyncio
async def test_report_keeps_prior_hypothesis_and_scope_claim_distinct_from_source_observations(monkeypatch):
    calls = stub_report(monkeypatch)
    state = material_state()
    state.forensic.root_cause_hypothesis = "A model hypothesis about a password dictionary"
    state.forensic.blast_radius = "A model assessment of incident scope"
    await report.run_report_writer(state.to_dict())
    message = calls[0][1].content
    assert "Prior-agent root-cause hypothesis/claim (unverified, not a source observation): " + state.forensic.root_cause_hypothesis in message
    assert "Prior-agent scope assessment (unverified): " + state.forensic.blast_radius in message
    assert "Observed scope is the provided source Alert fields above; wider extent remains unknown" in message
    assert "Source Alert time/facts" in message and "outcome=failure" in message


@pytest.mark.asyncio
async def test_failed_lookup_uses_existing_processing_audit_time_in_a_separate_coverage_section(monkeypatch):
    calls = stub_report(monkeypatch)
    state = material_state()
    audit_time = "2026-10-21T04:01:00+08:00"
    state.enrichment_cache = {"192.0.2.1": {"error": "Source unavailable"}}
    state.audit_log.append(AuditEntry(timestamp=datetime.fromisoformat(audit_time), kind=StepKind.TOOL_CALL,
        agent="ReconAgent", summary="enrich_ioc failed", metadata={"tool": "enrich_ioc", "success": False}))
    diagnostics = report._processing_diagnostics(state)
    assert audit_time in diagnostics and "investigation_processing" in diagnostics
    assert "timezone_status: explicit_offset" in diagnostics
    assert state.raw_alert["alerts"][0]["event_time"] not in diagnostics
    await report.run_report_writer(state.to_dict())
    message = calls[0][1].content
    coverage = message.index("=== INVESTIGATION COVERAGE / PROCESSING ACTIVITY (not incident events) ===")
    assert message.index(audit_time) > coverage
    assert message.index("2026-10-21T04:00:00+08:00") < coverage
    assert "Do not put them on the incident timeline using a source Alert event_time" in message
    assert "a lookup without such a timestamp has an unknown processing time" in message


@pytest.mark.asyncio
async def test_naive_processing_audit_time_keeps_original_stamp_and_explicit_unknown_zone(monkeypatch):
    calls = stub_report(monkeypatch)
    state = material_state()
    stamp = "2026-10-21T04:01:00"
    state.audit_log.append(AuditEntry(timestamp=datetime.fromisoformat(stamp), kind=StepKind.TOOL_CALL,
        agent="ReconAgent", summary="enrich_ioc failed", metadata={"tool": "enrich_ioc", "success": False}))
    diagnostics = report._processing_diagnostics(state)
    audit_line = next(line for line in diagnostics.splitlines() if ".audit_timestamp:" in line)
    assert audit_line.endswith(stamp) and "timezone_status: not_recorded_unknown" in diagnostics
    await report.run_report_writer(state.to_dict())
    message = calls[0][1].content
    assert "an individual naive stamp carries no recorded offset" in message
    assert "Never infer a missing audit offset from source-event or local time zones" in message
    assert state.audit_log[0].timestamp.isoformat() == stamp


@pytest.mark.asyncio
async def test_forensic_scope_presents_supplied_fields_and_unverified_assessment_while_retaining_raw_response(monkeypatch):
    claim = "The attack was limited to five accounts across the estate."
    original = json.dumps({"timeline": [], "artefacts": [], "root_cause_hypothesis": "A hypothesis",
        "blast_radius": claim, "confidence": 0.8, "summary": "Prior model analysis"})
    async def invoke(_model, _messages):
        return SimpleNamespace(content=original, response_metadata={"token_usage": {"total_tokens": 23}})
    monkeypatch.setattr(forensic, "make_chat_model", lambda *args, **kwargs: object())
    monkeypatch.setattr(forensic, "safe_ainvoke", invoke)
    monkeypatch.setattr(forensic, "record_llm_call", lambda *args, **kwargs: None)
    state = material_state()
    state.raw_alert["alerts"][0].update(affected_hosts=["host-from-supplied-alert"], affected_users=["named-user-only"])
    result = await forensic.run_forensic(state.to_dict())
    scope = result["forensic"]["blast_radius"]
    assert "Supplied-alert observed scope" in scope and "host-from-supplied-alert" in scope and "named-user-only" in scope
    assert "Unverified model scope assessment (a claim, not a confirmed scope boundary):\n" + claim in scope
    assert "Wider extent: unknown beyond supplied or separately verified observations" in scope
    response = next(row for row in result["audit_log"] if row["kind"] == "llm_response")
    assert response["metadata"]["response"] == original and response["metadata"]["tokens_used"] == 23
    assert result["forensic"]["confidence"] == 0.8


@pytest.mark.asyncio
async def test_length_keeps_actual_response_usage_and_delivers_failed_complete_fallback_without_retry(monkeypatch):
    original = "# Truncated model report\nUnfinished paragraph [KB1] CUT_END"
    calls = stub_report(monkeypatch, finish="length", content=original)
    result = await report.run_report_writer(material_state().to_dict())
    assert len(calls) == 1 and result["status"] == "failed" and "finish_reason=length" in result["error"]
    assert "Fallback report" in result["report_md"] and "No replacement model request" in result["report_md"]
    assert "CUT_END" not in result["report_md"] and "## Knowledge references" not in result["report_md"]
    assert all("## " + heading in result["report_md"] for heading in HEADINGS)
    response = next(row for row in result["audit_log"] if row["kind"] == "llm_response")
    assert response["metadata"]["response"] == original and response["metadata"]["tokens_used"] == 17
    done = next(row for row in result["audit_log"] if row["kind"] == "report")
    assert done["metadata"]["generation_status"] == "truncated" and done["metadata"]["report_source"] == "fallback"


@pytest.mark.asyncio
@pytest.mark.parametrize("cap", [1024, 2048])
async def test_native_sdk_length_metadata_reaches_the_truncation_branch(monkeypatch, cap):
    from app.llm import contract
    monkeypatch.setenv("OPENAI_BASE_URL", "http://report-synthetic.invalid/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-offline-no-credential")
    if cap == 2048:
        monkeypatch.delenv("AISOC_INVESTIGATOR_MAX_COMPLETION_TOKENS", raising=False)
    else:
        monkeypatch.setenv("AISOC_INVESTIGATOR_MAX_COMPLETION_TOKENS", str(cap))
    monkeypatch.setattr(contract, "_RESPONSE_CACHE_ENABLED", False)
    monkeypatch.setattr(contract.egress_privacy, "_FORCE", "0")
    requests = []
    def reply(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"id": "offline-report", "object": "chat.completion", "created": 1,
            "model": "offline-report", "choices": [{"index": 0, "message": {"role": "assistant", "content": "# Partial native output"}, "finish_reason": "length"}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
        model = make_chat_model("report", temperature=0, max_tokens=cap, http_async_client=client)
        def get_model(*args, **kwargs):
            assert kwargs["max_tokens"] == cap
            return model
        monkeypatch.setattr(report, "make_chat_model", get_model)
        result = await report.run_report_writer(material_state().to_dict())
    assert len(requests) == 1 and requests[0].get("max_completion_tokens", requests[0].get("max_tokens")) == cap
    assert result["status"] == "failed" and "finish_reason=length" in result["error"]
    assert "complete fallback supplied" in result["report_md"]
    response = next(row for row in result["audit_log"] if row["kind"] == "llm_response")
    assert response["metadata"]["response"] == "# Partial native output"
    assert response["metadata"]["tokens_used"] == 18


@pytest.mark.asyncio
async def test_stop_is_not_reclassified_by_guessing_from_report_text(monkeypatch):
    stub_report(monkeypatch, content="A short response with the literal word length.")
    result = await report.run_report_writer(material_state().to_dict())
    assert result["status"] == "completed" and result["report_md"].startswith("A short response")


@pytest.mark.asyncio
async def test_model_error_yields_explicit_failed_fallback(monkeypatch):
    calls = stub_report(monkeypatch, error=TimeoutError("offline boundary"))
    result = await report.run_report_writer(material_state().to_dict())
    assert len(calls) == 1 and result["status"] == "failed"
    assert "Report generation failed (TimeoutError)" in result["error"]
    assert all("## " + heading in result["report_md"] for heading in HEADINGS)


@pytest.mark.asyncio
async def test_error_only_enrichment_remains_visible_but_does_not_satisfy_forensic_evidence_gate(monkeypatch):
    prompts = []
    async def invoke(_model, messages):
        prompts.append(messages[1].content)
        return SimpleNamespace(content=json.dumps({"timeline": [{"ts": "invented", "event": "fiction"}],
            "artefacts": ["fiction.exe"], "root_cause_hypothesis": "unsupported", "blast_radius": "unsupported",
            "confidence": 0.9, "summary": "unsupported"}), response_metadata={})
    monkeypatch.setattr(forensic, "make_chat_model", lambda *args, **kwargs: object())
    monkeypatch.setattr(forensic, "safe_ainvoke", invoke)
    monkeypatch.setattr(forensic, "record_llm_call", lambda *args, **kwargs: None)
    state = InvestigatorState(case_id="no-primary", enrichment_cache={"192.0.2.1": {"error": "All connection attempts failed"}})
    result = await forensic.run_forensic(state.to_dict())
    assert "All connection attempts failed" in prompts[0] and "Usable enrichment records: 0" in prompts[0]
    assert "KB definitions" in prompts[0] and "only an inconclusive analysis" in prompts[0]
    assert result["enrichment_cache"] == state.enrichment_cache
    assert result["forensic"]["timeline"] == [] and result["forensic"]["artefacts"] == []
    assert result["forensic"]["confidence"] <= 0.1 and "INCONCLUSIVE" in result["forensic"]["root_cause_hypothesis"]


@pytest.mark.parametrize("row, usable", [({"error": "down"}, False), ({"available": False, "risk_score": 0}, False),
                                      ({"value": "192.0.2.1", "ioc_type": "ip"}, False),
                                      ({"value": "192.0.2.1", "risk_score": 0}, True)])
def test_usable_enrichment_distinguishes_failure_identity_echo_and_explicit_zero(row, usable):
    assert bool(forensic._usable_enrichments({"ioc": row})) is usable


def test_fallback_escapes_added_source_and_timeline_text():
    state = material_state()
    state.forensic.timeline[0]["event"] = "<script>alert(1)</script>"
    state.raw_alert["alerts"][0]["description"] = "[link](javascript:alert(1))"
    html = report._md_to_html(report._fallback_report(state), state.case_id)
    assert "<script>" not in html and 'href="javascript:' not in html
