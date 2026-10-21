"""Direct result contracts from the controlled C2 observation; no live models."""
from __future__ import annotations

import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage

from app.agents import investigation_agent as investigation
from app.confidence.scoring import score_investigation, score_triage
from app.core.cost_governor import CostGovernor
from app.core.cost_telemetry import CostTracker, current_cost_tracker
from app.graph import runner
from app.investigator import deep_investigation as deep
from app.llm import tool_loop
from app.models.state import AgentStatus, InvestigationState
from app.orchestrator.report import render_router_report
from app.tools.registry import Tool, ToolRegistry


def case_state(risk=85):
    return InvestigationState(incident_id=uuid4(), tenant_id=uuid4(), verdict="needs_review",
        alert_summary="Repeated account failures followed by a successful session — derived priority rank 1.00; ML anomaly score 0.15",
        raw_alert={"title":"Repeated account failures followed by a successful session",
          "description":"Authentication audit records 23 failures followed by one success. Authorization and subsequent session activity remain unknown.",
          "username":"svc-ledger-sync", "src_ip":"192.0.2.83", "hostname":"identity-gateway-04",
          "risk_score":risk, "severity":"high", "mitre_techniques":["T1110"],
          "event_time":"2026-10-21T02:12:51.017257Z", "created_at":"2026-10-21T02:13:51Z",
          "raw_event":{"source_system":"authentication-audit","account":"svc-ledger-sync",
            "source_ip":"192.0.2.83","failure_count":23,"window_start_utc":"2026-10-21T02:09:51.017257Z",
            "window_end_utc":"2026-10-21T02:12:51.017257Z","final_result":"success","session_id":"session-1",
            "authorization_record":None,"post_login_activity":None}},mitre_mappings=["T1110"],
        findings=["First triage: needs_review; authorization and post-login activity unknown"])


@pytest.mark.parametrize(("risk","enrichments","expected"),[
    (85,{},"needs_review"),
    (None,{},"needs_review"),
    (None,{"ip":{"error":"timeout","threat_classification":"benign"}},"needs_review"),
    (85,{"ip":{"error":"timeout","threat_classification":"malicious"}},"needs_review"),
    (85,{"ip":{"available":False,"threat_classification":"malicious"}},"needs_review"),
    (85,{"ip":{"threat_classification":"malicious"}},"confirmed_incident"),
    (85,{"ip":{"threat_classification":"suspicious"}},"probable_incident"),
])
def test_incident_verdict_requires_successful_corroboration(risk,enrichments,expected):
    state=case_state(risk);state.ioc_enrichments=enrichments
    before=copy.deepcopy(state.raw_alert)
    confidence,basis,verdict=score_investigation(state)
    assert verdict==expected and basis and 0.05<=confidence<=0.95
    assert state.raw_alert==before
    if risk==85 and not enrichments:
        assert score_triage(state)[0]==pytest.approx(.94)
        assert confidence==pytest.approx(.94)  # Keep the prior; change its evidentiary meaning.


def test_low_score_needs_actual_benign_enrichment_for_false_positive():
    state=InvestigationState(incident_id=uuid4(),tenant_id=uuid4())
    assert score_investigation(state)[2]=="needs_review"
    state.ioc_enrichments={"ip":{"threat_classification":"benign"}}
    assert score_investigation(state)[2]=="likely_false_positive"
    state.ioc_enrichments["other"]={"error":"unavailable"}
    assert score_investigation(state)[2]=="needs_review"


def test_deep_prompt_preserves_source_v1_material_without_invented_time():
    state=case_state();before=state.to_dict()
    text=deep._summarise_alert(state)
    evidence=json.loads(text.split('<UNTRUSTED_DATA source="alert_source">\n',1)[1].split("\n</UNTRUSTED_DATA>",1)[0])
    assert evidence["raw_event"]==state.raw_alert["raw_event"]
    for field in ("description","username","src_ip","event_time","created_at"):
        assert evidence[field]==state.raw_alert[field]
    assert "derived priority" not in text
    assert "not independently observed" in text
    assert state.to_dict()==before
    del state.raw_alert["event_time"]
    text=deep._summarise_alert(state)
    assert "event_time" not in json.loads(text.split('<UNTRUSTED_DATA source="alert_source">\n',1)[1].split("\n</UNTRUSTED_DATA>",1)[0])


def test_process_event_projection_is_generic_bounded_and_preserves_null():
    state=case_state()
    state.raw_alert["raw_event"]={"process":{"name":"systemctl","command_line":"systemctl reload nginx","parent_pid":42},
       "event":{"timestamp":"2026-10-21T02:12:51Z"},"authorization":None}
    before=copy.deepcopy(state.raw_alert)
    text=deep._summarise_alert(state)
    source=json.loads(text.split('<UNTRUSTED_DATA source="alert_source">\n',1)[1].split("\n</UNTRUSTED_DATA>",1)[0])
    assert source["raw_event"]==state.raw_alert["raw_event"]
    assert "source_projection_truncated=false" in text and state.raw_alert==before
    state.raw_alert["raw_event"]["process"]["command_line"]="x"*10000
    text=deep._summarise_alert(state)
    assert "source_projection_truncated=true" in text and "[truncated]" in text
    assert "x"*10000 not in text and state.raw_alert["raw_event"]["process"]["command_line"]=="x"*10000


@pytest.mark.asyncio
async def test_six_tool_turns_return_partial_not_last_tool_json(monkeypatch):
    state=case_state();calls=[]
    async def invoke(*_):
        calls.append(1)
        return AIMessage(content="Need another lookup",tool_calls=[{"name":"read","args":{},"id":str(len(calls))}])
    monkeypatch.setattr(tool_loop,"safe_ainvoke",invoke)
    registry=ToolRegistry([Tool(name="read",description="read",parameters={"type":"object"},fn=lambda:{"ioc":"192.0.2.83"})])
    model=SimpleNamespace(bind_tools=lambda _:object())
    result=await tool_loop.run_with_tools(model,system="s",user="u",registry=registry,max_iters=6,on_exchange=state.record_llm_exchange)
    assert len(calls)==6 and len(result["tool_trace"])==6 and len(state.llm_exchanges)==6
    assert result["truncated"] and result["content"]=="" and result["stop_reason"]=="iteration cap (6)"
    assert "192.0.2.83" in result["tool_trace"][-1]["result_preview"]


@pytest.mark.parametrize(("token_cap","call_cap","reason"),[(100,None,"token budget exhausted (110 of 100)"),(None,2,"model-call budget exhausted (2 of 2)")])
@pytest.mark.asyncio
async def test_reply_crossing_budget_stops_immediately_and_keeps_receipt(monkeypatch,token_cap,call_cap,reason):
    state=case_state();calls=[];tools=[]
    async def invoke(*_):
        calls.append(1)
        current_cost_tracker().record(model="unpriced",prompt_tokens=50,completion_tokens=5,latency_ms=1)
        return AIMessage(content="Need another lookup",tool_calls=[{"name":"read","args":{},"id":str(len(calls))}])
    monkeypatch.setattr(tool_loop,"safe_ainvoke",invoke)
    registry=ToolRegistry([Tool(name="read",description="read",parameters={"type":"object"},fn=lambda:tools.append(1) or {"observed":True})])
    async with CostTracker(run_id=str(state.run_id),tenant_id=str(state.tenant_id),persist=False):
        result=await tool_loop.run_with_tools(SimpleNamespace(bind_tools=lambda _:object()),system="s",user="u",registry=registry,max_iters=6,
            max_tokens=token_cap,max_model_calls=call_cap,on_exchange=state.record_llm_exchange)
    assert len(calls)==2 and len(tools)==1 and len(state.llm_exchanges)==2
    assert result["truncated"] and result["stop_reason"]==reason and result["content"]==""


def isolate_deep(monkeypatch):
    monkeypatch.setattr(deep,"ENABLED",True)
    monkeypatch.setattr(deep,"_resolve_tenant_skill",AsyncMock(return_value=None))
    monkeypatch.setattr(deep,"scoped_customer_tools",AsyncMock(return_value=([],[])))
    monkeypatch.setattr(deep,"build_mcp_toolset",AsyncMock(return_value=SimpleNamespace(tools=[],refusals=[])))
    monkeypatch.setattr(deep,"default_registry",lambda _:ToolRegistry())
    monkeypatch.setattr(deep,"investigation_tools",lambda _:[])
    monkeypatch.setattr(deep,"_record_tool_calls",AsyncMock(return_value=0))


@pytest.mark.parametrize("outcome",["success","error","timeout"])
@pytest.mark.asyncio
async def test_deep_charges_only_actual_new_tokens_once_even_when_incomplete(monkeypatch,outcome):
    isolate_deep(monkeypatch);state=case_state();gov=CostGovernor()
    gov.record_spend(str(state.tenant_id),usd=0.0,tokens=99)
    monkeypatch.setattr(deep,"get_governor",lambda:gov)
    async def loop(*_,**__):
        current_cost_tracker().record(model="unpriced",prompt_tokens=25,completion_tokens=6,latency_ms=1)
        if outcome=="error":raise ValueError("bounded failed response")
        if outcome=="timeout":raise TimeoutError()
        return {"content":"Bounded visible answer","tool_trace":[],"iterations":1,"truncated":False}
    monkeypatch.setattr(deep,"run_with_tools",loop)
    async with CostTracker(run_id=str(state.run_id),tenant_id=str(state.tenant_id),persist=False) as tracker:
        tracker.record(model="earlier",prompt_tokens=7,completion_tokens=2,latency_ms=1)
        result=await deep.run_deep_investigation(state,llm=object())
        assert len(tracker._records)==2 and tracker.tokens_used==40
    assert result.tokens==31 and result.usd_cost is None and result.as_dict()["usd_cost"] is None
    assert gov.spent_tokens(str(state.tenant_id))==130
    assert gov.state(str(state.tenant_id))["spent_usd"] is None
    assert gov.state(str(state.tenant_id))["unpriced_spend_events"]==1
    assert bool(result.error)==(outcome!="success")


@pytest.mark.asyncio
async def test_incomplete_investigation_does_not_claim_attack_or_confirmation(monkeypatch):
    state=case_state();raw_before=copy.deepcopy(state.raw_alert)
    monkeypatch.setattr(investigation,"collect_splunk_evidence",AsyncMock(return_value=SimpleNamespace(applicable=False,queried=False)))
    monkeypatch.setattr(investigation,"_perform_threat_actor_attribution",AsyncMock())
    monkeypatch.setattr(investigation,"run_deep_investigation",AsyncMock(return_value=deep.DeepInvestigationResult(
        strategy_id="identity-account-takeover",iterations=6,truncated=True,stop_reason="iteration cap (6)",tokens=20451)))
    result=await investigation.run_investigation(state)
    assert result.verdict=="needs_review" and result.status is AgentStatus.RUNNING
    assert result.raw_alert==raw_before
    text="\n".join(result.findings)
    assert "knowledge candidates: Credential Access" in text and "Investigation partial" in text
    assert "Attack stages observed" not in text and "single-stage attack" not in text
    assert "confirmed_incident" not in text and "Investigation complete." not in text


@pytest.mark.asyncio
async def test_runner_stops_after_partial_investigation_and_keeps_report_consistent():
    state=case_state();visited=[];budget=runner.InvestigationBudget(max_seconds=1,max_tokens=100,max_tool_calls=3)
    class Graph:
        async def astream(self,data):
            visited.append("investigation")
            assert runner.current_investigation_budget()==budget
            yield {"investigation":{**data,"investigation_depth":{"truncated":True},"verdict":"confirmed_incident","status":"completed"}}
            visited.append("attack_path")
            yield {"attack_path":{"status":"completed"}}
    result=await runner._run(Graph(),state,budget=budget,persist=False,seq_start=1)
    assert visited==["investigation"] and runner.current_investigation_budget() is None
    assert result.verdict=="needs_review" and result.status is AgentStatus.RUNNING
    md,_=render_router_report(result)
    assert "needs_review" in md and "confirmed_incident" not in md


@pytest.mark.asyncio
async def test_runner_budget_reaches_deep_loop_without_changing_caps(monkeypatch):
    isolate_deep(monkeypatch);state=case_state();seen={}
    async def loop(*_,**kwargs):
        seen.update(kwargs)
        return {"content":"Unknown beyond supplied evidence","tool_trace":[],"iterations":1,"truncated":False}
    monkeypatch.setattr(deep,"run_with_tools",loop)
    class Graph:
        async def astream(self,data):
            await deep.run_deep_investigation(state,llm=object())
            yield {"investigation":{"status":"completed"}}
    budget=runner.InvestigationBudget(max_seconds=1,max_tokens=100,max_tool_calls=3)
    async with CostTracker(run_id=str(state.run_id),tenant_id=str(state.tenant_id),persist=False):
        await runner._run(Graph(),state,budget=budget,persist=False,seq_start=1)
    assert seen["max_tokens"]==100 and seen["max_model_calls"]==3 and seen["max_iters"]==6
    assert runner.current_investigation_budget() is None


@pytest.mark.asyncio
async def test_deep_without_tracker_reports_unmeasured_usage(monkeypatch):
    isolate_deep(monkeypatch);state=case_state();gov=CostGovernor()
    monkeypatch.setattr(deep,"get_governor",lambda:gov)
    async def loop(*_,**__):
        return {"content":"Unknown beyond supplied evidence","tool_trace":[],"iterations":1,"truncated":False}
    monkeypatch.setattr(deep,"run_with_tools",loop)
    assert current_cost_tracker() is None
    result=await deep.run_deep_investigation(state,llm=object())
    assert result.tokens is None and result.usd_cost is None
    assert result.as_dict()["tokens"] is None and not result.cost_capped
    assert gov.spent_tokens(str(state.tenant_id))==0


@pytest.mark.parametrize("failure",[ValueError,TimeoutError])
@pytest.mark.asyncio
async def test_tracker_without_response_usage_does_not_invent_zero(monkeypatch,failure):
    isolate_deep(monkeypatch);state=case_state();gov=CostGovernor()
    monkeypatch.setattr(deep,"get_governor",lambda:gov)
    async def loop(*_,**__):
        raise failure("request ended before usage arrived")
    monkeypatch.setattr(deep,"run_with_tools",loop)
    async with CostTracker(run_id=str(state.run_id),tenant_id=str(state.tenant_id),persist=False):
        result=await deep.run_deep_investigation(state,llm=object())
    assert result.error and result.tokens is None and result.usd_cost is None
    assert result.as_dict()["tokens"] is None and result.as_dict()["usd_cost"] is None
    assert gov._spend.get(str(state.tenant_id)) is None


def test_scalar_prefix_cannot_bypass_bounded_json_projection():
    state=case_state();state.raw_alert["username"]="u"*10000
    before=copy.deepcopy(state.raw_alert)
    text=deep._summarise_alert(state)
    assert "u"*10000 not in text and len(text)<9000
    assert "source_projection_truncated=true" in text and "[truncated]" in text
    assert state.raw_alert==before


@pytest.mark.asyncio
async def test_mixed_measured_and_unpriced_usage_preserves_known_governor_dollars(monkeypatch):
    from app.core.gateway_cost import GatewayCost
    isolate_deep(monkeypatch);state=case_state();gov=CostGovernor()
    monkeypatch.setattr(deep,"get_governor",lambda:gov)
    async def loop(*_,**__):
        current_cost_tracker().record(model="priced",prompt_tokens=10,completion_tokens=2,latency_ms=1,gateway_cost=GatewayCost(.625))
        current_cost_tracker().record(model="unpriced",prompt_tokens=20,completion_tokens=3,latency_ms=1)
        return {"content":"Evidence remains incomplete","tool_trace":[],"iterations":2,"truncated":False}
    monkeypatch.setattr(deep,"run_with_tools",loop)
    async with CostTracker(run_id=str(state.run_id),tenant_id=str(state.tenant_id),persist=False) as tracker:
        result=await deep.run_deep_investigation(state,llm=object())
        assert len(tracker._records)==2 and tracker.tokens_used==35
    assert result.tokens==35 and result.usd_cost is None
    assert gov.spent_tokens(str(state.tenant_id))==35 and gov.spent_usd(str(state.tenant_id))==.625
    summary=gov.state(str(state.tenant_id))
    assert summary["spent_usd"] is None and summary["known_spent_usd"]==.625 and summary["unpriced_spend_events"]==1
    assert len(gov._spend[str(state.tenant_id)])==2 and result.cost_capped
