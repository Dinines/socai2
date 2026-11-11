"""Read-only audit probes: real production functions, frozen fixtures, no network/DB.
Run from repo root with PYTHONPATH=services/api:services/api/tests:docs/operations:.
"""
import asyncio
import copy
import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
import test_socai2_case_model_boundary as base
from app.socai2 import baseline_analysis_contract as contract, case_output_adapter
from app.socai2.baseline_analysis import budget_reason
from app.socai2.baseline_contracts import Limits
from app.socai2.baseline_dispatch import offered_bindings, dispatch_followups
from app.socai2.baseline_evidence_tools import catalog
from app.socai2.baseline_deep_contract import parse as parse_deep
from jsonschema import Draft202012Validator

configured, sample = base.configured, base.sample
# Replays must not overwrite the completed audit batch.
OUT = Path(tempfile.mkdtemp(prefix='socai2-audit-current-'))

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket
    def deny(*args, **kwargs):
        raise AssertionError('audit_network_not_allowed')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)

def options_for(context):
    now = datetime.now(UTC)
    limits = Limits(max_model_calls=6, max_tool_calls=4, max_tokens=131072,
                    max_rows_per_query=200, deadline_at=now+timedelta(seconds=1500), policy_version='audit')
    return offered_bindings(catalog(context, '00000000-0000-0000-0000-000000000001'),
                            limits, now, [], SimpleNamespace(configured=lambda:True))

def test_missing_entity_time_and_ambiguous_candidates(sample):
    context, prepared = base.prepared_sample(sample)
    original, mapping, _ = options_for(context)
    assert len(mapping) >= 3
    absent = context.model_copy(update={'alerts': {
        aid: a.model_copy(update={'objects': []}) for aid, a in context.alerts.items()}})
    assert options_for(absent)[0] == []
    missing = context.model_copy(update={'scope': context.scope.model_copy(
        update={'window_start': None, 'window_end': None})})
    options, _, excluded = options_for(missing)
    assert all(o['tool_name']=='product_host_details' for o in options)
    assert excluded and all(e['reason']=='query_window_unavailable' for e in excluded)
    two = context.model_copy(deep=True)
    member = next(a for a in two.alerts.values() if any(o['object_type']=='host' for o in a.objects))
    host = copy.deepcopy(next(o for o in member.objects if o['object_type']=='host'))
    host['normalized_value']='audit-second-host';host['object_key']='host:audit-second-host';member.objects.append(host)
    options,mapping,_=options_for(two)
    assert {'audit-second-host'} < {o['hostname'] for o in options}
    # Missing/unknown binding is rejected, never picked as the first option.
    for binding in (None,'outside-catalog'):
        with pytest.raises(contract.AnalysisRejected,match='unoffered_query'):
            parse_deep(json.dumps({'question_id':'q','action':'query','binding_id':binding,'reason':'audit','answer':None}),{},mapping,'q')

def test_c3_three_followups_pass_contract_and_are_dispatched(sample):
    context,prepared=base.prepared_sample(sample)
    options,bindings,_=options_for(context)
    assert '2个必要followups' in prepared['messages'][0]['content']
    answer=base.answer_for(prepared,context)
    boundary=prepared['case_boundary']
    answer['followups']=[{'question_id':q.id,'alert_ids':[boundary['member_aliases'][a] for a in b['alert_ids']],
        'mode':'query','objective':'Audit distinct query','required_evidence':'Audit raw observations',
        'source_ids':[], 'object_keys':[boundary['object_aliases'][o['object_key']] for o in b['objects']],
        'binding_id':alias,'priority':'decision_critical'}
        for q,(alias,b) in zip(context.questions,list(bindings.items())[:3])]
    Draft202012Validator(case_output_adapter.output_format(prepared,context,bindings)['json_schema']['schema']).validate(answer)
    parsed=case_output_adapter.parse(json.dumps(answer),prepared,context,bindings)
    calls=[]
    class Service:
        async def query_evidence(self,*args,**kwargs):
            calls.append({'binding':args[3],'question':args[4]})
            return {'reused':False,'result':{'state':'completed'},'projection':{'reason':None},'artifact_id':'audit','projection_id':'audit'}
    routes=asyncio.run(dispatch_followups(Service(),'t','c','r',[x.model_dump(mode='json') for x in parsed.followups],bindings,gateway=None,lake=None))
    assert len(calls)==len(routes)==3
    (OUT/'followup-limit.json').write_text(json.dumps({'prompt_max_followups':2,'schema_max_followups':12,
        'accepted':len(parsed.followups),'dispatcher_calls':calls,'scope':'real schema/parser/dispatcher, tool service spy; no DB or external query'},indent=2)+'\n')

def test_budget_unknown_and_mismatch_are_not_success(sample):
    now=datetime.now(UTC)
    limit=Limits(max_model_calls=2,max_tool_calls=1,max_tokens=100,max_rows_per_query=1,
                 deadline_at=now+timedelta(seconds=30),policy_version='audit')
    step={'kind':'model','state':'failed','usage':{'usage_state':'unknown','total_tokens':None}}
    assert budget_reason([step],limit,1,now)=='prior_model_usage_unknown'
    assert budget_reason([step,step],limit,1,now)=='model_call_budget_exhausted'
    assert budget_reason([],limit,1,now+timedelta(seconds=60))=='deadline_reached'
    assert budget_reason([],limit,1,now,measurement={'context_fits':True,'reserved_total_tokens':101})=='model_token_budget_insufficient'
    with pytest.raises(contract.AnalysisRejected,match='question_outside_frozen_scope'):
        parse_deep(json.dumps({'question_id':'wrong','action':'query','binding_id':'B1','reason':'audit','answer':None}),{}, {'B1':{}},'expected')
    with pytest.raises(contract.AnalysisRejected,match='deep_shape_invalid'):
        parse_deep(json.dumps({'question_id':'q','action':'query','binding_id':'B1','reason':'audit','answer':None,'sql':'outside'}),{}, {'B1':{}},'q')

def test_legal_reference_does_not_verify_statement_truth(sample):
    context,prepared=base.prepared_sample(sample)
    answer=base.answer_for(prepared,context)
    aid,alias=next(iter(prepared['case_boundary']['member_aliases'].items()))
    sid=next(s for s,v in prepared['source_map'].items() if v['alert_ids']==[aid] and v['ref']['role']=='observation')
    answer['findings']=[{'id':'audit-F','state':'observed','statement':'审计注入的无依据主张：已确认泄露全部数据库。',
        'alert_ids':[alias],'support_ids':[sid],'counter_ids':[],'alternatives':[],'limitations':[]}]
    parsed=case_output_adapter.parse(json.dumps(answer),prepared,context,{})
    assert parsed.findings[0].statement==answer['findings'][0]['statement']
    (OUT/'semantic-boundary.json').write_text(json.dumps({'accepted':True,'source':prepared['source_map'][sid],
        'synthetic_statement':answer['findings'][0]['statement'],'meaning':'Role/scope validation is not semantic truth validation; no live model was called.'},ensure_ascii=False,indent=2)+'\n')
