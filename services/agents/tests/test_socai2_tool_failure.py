"""An actual failed enrichment must not be recorded as a successful tool call."""
import pytest
from app.investigator import recon_agent
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
