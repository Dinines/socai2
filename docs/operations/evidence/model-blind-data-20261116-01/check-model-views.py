"""Use current A/I/C3/Deep/C6 builders on the newly generated business materials."""
import copy,json,os
from pathlib import Path
from uuid import NAMESPACE_URL,UUID,uuid5
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
os.environ['SOCAI2_INVESTIGATION_POLICY']=str(ROOT/'deploy/local-investigation/investigation-policy-case-v1.toml')
from app.socai2 import alert_model_boundary,incident_model_boundary,case_model_boundary,case_followup_input,runtime_policy
from app.socai2.baseline_context import Context
from app.socai2 import case_query_snapshot
from app.socai2.stage_inputs import QUERY_RECEIPTS_VERSION
policy=runtime_policy.active_policy();members=json.loads((OUT/'fusion-projected-materials.json').read_text())
def identity(value):return str(uuid5(NAMESPACE_URL,'blind-data-20261116-01:'+value))
def write(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2,default=str)
stamp=members[-1]['alert']['event_time'];cid=identity('case');iid=identity('incident');messages={}
source={'parent':{'id':iid,'title':'主机活动调查'},'members':members,'triage_validation':{
    m['alert']['id']:{'usable':False} for m in members},'query_receipts_version':QUERY_RECEIPTS_VERSION,
    'triage_queries':{}}
with patch('socket.socket',side_effect=AssertionError('offline audit cannot use network')):
    for index,member in enumerate(members,1):
        single={**source,'parent':member['alert'],'members':[member]}
        value=alert_model_boundary.build(single,identity('A'+str(index)),[],policy.alert_io,execution_time=stamp)
        messages['A'+str(index)]=value[0]
    messages['I']=incident_model_boundary.build(source,identity('I'),policy.incident_io,execution_time=stamp)[0]
    scope={'kind':'whole_case','alert_ids':[m['alert']['id'] for m in members],'object_keys':[],
           'window_start':members[0]['alert']['event_time'],'window_end':stamp,'limitations':[]}
    roles={'$.case':'source_label'};alerts={}
    for member in members:
        aid=member['alert']['id'];alerts[aid]={**member,'limitations':[], 'triage_freshness':'unverified',
            'triage_usable':False,'triage_run_state':None,'queries':[]}
        for name in ('alert','alert.event_time','objects','material'):roles['$.alerts.'+aid+'.'+name]='source_label'
        roles['$.alerts.'+aid+'.membership']='execution_receipt'
    raw={'schema_version':'socai2.baseline-context.v1','case_id':cid,'captured_at':stamp,'scope':scope,
         'case':{'id':cid,'title':'主机活动调查','scope_revision':1,'state':'open'},'alerts':alerts,'incidents':{},'tasks':{},
         'current_assessment':None,'assessment_members':[],'assessment_sources':[],'prior_results':{},
         'adopted_task_revisions':{},'adopted_artifacts':{},'omissions':[],
         'questions':[{'id':'activity','text':'这些记录反映了哪些活动及其关联？','scope':scope,
             'evidence_requirements':['观察记录'],'state':'open','answer':None,'evidence_refs':[],'limitations':[]}],
         'citation_roles':roles,'query_receipts_version':case_query_snapshot.VERSION,'case_input_profile':policy.case_io.identity}
    context=Context.model_validate(raw)
    base=case_model_boundary.build(context,identity('context'),[],[],{m['alert']['id']:m['material'] for m in members},execution_time=stamp)
    assert base['ready'],base['reason'];messages['C3']=case_model_boundary.messages(base,context,[])[0]
    for stage in ('Deep','C6'):
        result=case_followup_input.build(stage,context,base,{},question_id='activity' if stage=='Deep' else None)
        assert result['ready'],result['reason'];messages[stage]=result['messages']
    checks=[]
    forbidden=['synthetic','fixture','model-blind','blind-templates','telemetry-channel-01','expected_disposition',
               'expected_verdict','decisive_evidence','s01-ingress','授权未知','program_classification']
    for stage,body in messages.items():
        visible='\n'.join(m['content'] for m in body)
        hits=[token for token in forbidden if token.lower() in visible.lower()]
        checks.append({'stage':stage,'characters':len(visible),'forbidden_hits':hits})
        write('model-view-'+stage+'.json',body)
    write('model-view-checks.json',{'checks':checks,'model_calls':0,'scope':'actual configured input builders; no fabricated prior model answer'})
    assert not any(row['forbidden_hits'] for row in checks),checks
print(json.dumps(checks,ensure_ascii=False))
