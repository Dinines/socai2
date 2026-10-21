"""A model response observed by both contract and node must count only once."""
from types import SimpleNamespace
import pytest
from app.core.cost_telemetry import CostTracker,record_llm_call
from app.core.gateway_cost import extract_gateway_cost

def response():
    return SimpleNamespace(response_metadata={'token_usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12},'headers':{'x-litellm-call-id':'unique-test-call','x-litellm-response-cost-original':'0.0'}})

@pytest.mark.asyncio
async def test_contract_and_explicit_node_share_one_call():
    async with CostTracker(run_id='cost-test',tenant_id='test',persist=False) as tracker:
        value=response()
        first=record_llm_call(value,model='aisoc-recon',latency_ms=1)
        second=record_llm_call(value,model='aisoc-recon',latency_ms=2,step='recon',tool='llm.recon')
        assert tracker.calls_made==1 and tracker.total_tokens==12
        assert first is second and second.step=='recon'

def test_untrusted_self_hosted_price_remains_unknown(monkeypatch):
    monkeypatch.setenv('AISOC_GATEWAY_COST_TRUST','0')
    assert extract_gateway_cost(response()) is None
