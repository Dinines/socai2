"""An actual failed enrichment must not be recorded as a successful tool call."""
import json

import httpx
import pytest
import respx

from app.investigator import recon_agent, tools as investigator_tools
from app.investigator.state import InvestigatorState

@pytest.mark.asyncio
@pytest.mark.parametrize("cached",[False,True])
async def test_enrichment_error_remains_failed_in_audit(monkeypatch,cached):
    async def recon(_):
        return {'iocs':[{'value':'198.18.0.1','type':'ip'}],'mitre_techniques':[],'summary':'test'}
    async def failed(*_):return {'error':'dependency unavailable','ioc':'198.18.0.1'}
    monkeypatch.setattr(recon_agent,'_llm_recon',recon)
    monkeypatch.setattr(recon_agent,'enrich_ioc',failed)
    state=InvestigatorState(case_id='baseline-test',alert_summary='marked test')
    if cached:state.enrichment_cache['198.18.0.1']={'error':'dependency unavailable','ioc':'198.18.0.1'}
    result=await recon_agent.run_recon(state.to_dict())
    tools=[e for e in result['audit_log'] if e['kind']=='tool_call' and e['metadata'].get('tool')=='enrich_ioc']
    assert len(tools)==1
    assert tools[0]['metadata']['success'] is False


@pytest.mark.asyncio
async def test_enrich_ioc_sends_service_ioc_type_contract(monkeypatch):
    monkeypatch.setattr(investigator_tools, "_ENRICHMENT_URL", "https://enrichment.example.invalid")
    expected_request = {"value": "enrichment-contract.example", "ioc_type": "domain"}
    source_response = {"value": "enrichment-contract.example", "ioc_type": "domain", "risk_score": 0.0, "sources": []}
    with respx.mock(assert_all_mocked=True, assert_all_called=True) as router:
        route = router.post("https://enrichment.example.invalid/enrich", json=expected_request).mock(
            return_value=httpx.Response(200, json=source_response)
        )
        result = await investigator_tools.enrich_ioc("enrichment-contract.example", "domain")

        assert route.call_count == 1
        assert json.loads(route.calls[0].request.content) == expected_request
        assert result == source_response
