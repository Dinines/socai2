"""Missing score is not zero in worker/replay/model; arithmetic baseline stays internal."""
from uuid import UUID
import pytest
from app.score_input import supplied_risk_score
from app.workers.fused_alert_consumer import build_state, _hold_severe_for_review_after_llm_failure
from app.agents.auto_triage_agent import _build_alert_context
from app.agents.triage_agent import run_triage
from app.models.state import AgentStatus

BASE={'id':'22222222-2222-2222-2222-222222222222','tenant_id':'11111111-1111-1111-1111-111111111111','alert':{'title':'Account activity','severity':'critical'}}
@pytest.mark.parametrize('extra,value,text',[({},None,'not provided or unknown (not zero)'),({'risk_score':None},None,'not provided or unknown (not zero)'),({'risk_score':0},0.0,'0 (publisher supplied'),({'risk_score':.8},.8,'0.8 (publisher supplied')])
def test_worker_and_actual_prompt_preserve_presence(extra,value,text):
    state=build_state({**BASE,'alert':{**BASE['alert'],**extra}})
    assert state.raw_alert['risk_score']==value
    prompt=_build_alert_context(state,nonce='test')
    assert 'Provided alert risk score: '+text in prompt
    assert 'Risk Score (vendor)' not in prompt

@pytest.mark.parametrize('value',[None,'unknown','',True,float('nan'),float('inf'),{},[]])
def test_invalid_scores_remain_unknown(value):
    assert supplied_risk_score(value) is None

@pytest.mark.parametrize('value',[0,0.0,'0',.8,'0.8'])
def test_finite_supplied_numeric_values(value):
    assert supplied_risk_score(value)==float(value)

@pytest.mark.asyncio
async def test_unknown_fallback_runs_and_failed_model_holds_critical_for_review():
    state=build_state(BASE);state=await run_triage(state)
    assert state.raw_alert['risk_score'] is None
    assert any('heuristic risk_score' in x for x in state.findings)
    out=_hold_severe_for_review_after_llm_failure(state)
    assert out.verdict=='needs_review' and out.status is not AgentStatus.COMPLETED

@pytest.mark.parametrize('normalized,vendor,expected',[({}, {},None),({'risk_score':0},{'risk_score':.8},0.0),({}, {'risk_score':'0'},0.0),({}, {'risk_score':.8},.8)])
def test_replay_preserves_unknown_and_normalized_zero_before_vendor_fallback(normalized,vendor,expected):
    from datetime import datetime,timezone
    from app.replay.findings import HistoricalFinding
    from app.replay.normalize import to_fused_envelope
    finding=HistoricalFinding(vendor='test',finding_id='f1',title='Test',disposition='needs_review',vendor_disposition='unknown',closed_at=datetime.now(timezone.utc),raw=vendor)
    out=to_fused_envelope(finding,normalized,tenant_id=BASE['tenant_id'])
    assert out['alert']['risk_score']==expected
