"""Offline new data + actual Fusion projections. No broker, database or model."""
import json,sys
from pathlib import Path
from uuid import NAMESPACE_URL,UUID,uuid5
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools/testdata'))
import streaming_fixture as fixture
import alert_scenarios as scenarios
from app.models.alert import RawAlert,FusedAlert
from app.services.socai2_projection import project,STORE_NAMESPACE

def identity(value):return str(uuid5(NAMESPACE_URL,'blind-data-20261116-01:'+value))
def save(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2,default=str)
with patch('socket.socket',side_effect=AssertionError('offline audit cannot use network')):
    config=json.loads((ROOT/'tools/testdata/streaming-fixture.example.json').read_text())
    generated=fixture.generate(config,OUT/'clean-data-01')
    _,manifest,inputs,_=fixture.build(config)
    all_alerts=[json.loads(line) for name,body in inputs.items() if name.endswith('alerts.jsonl') for line in body.splitlines()]
    projected=[]
    for wire in all_alerts:
        raw=RawAlert.model_validate(wire);aid=str(raw.deterministic_id());mid=identity(aid+':material')
        fused=FusedAlert(id=UUID(aid),tenant_id=raw.tenant_id,alert=raw,fusion_decision='new_alert')
        fields,material,refs,objects=project(fused,raw,UUID(identity(aid+':fusion')))
        alert={'id':aid,'source_namespace':STORE_NAMESPACE,'latest_material_id':mid,
               'latest_triage_id':None,'latest_feedback_id':None,'latest_explanation_id':None,**fields}
        projected.append({'alert':alert,'material':{'id':mid,'alert_id':aid,'revision':1,**material},
                          'objects':objects,'source_refs':refs,'triage':None,'feedback':None,'membership':{}})
    save('fusion-projected-materials.json',projected)
    templates=[s['template_id'] for s in scenarios._generator().generate_incidents(len(scenarios._generator().TEMPLATES))]
    batches=[]
    for offset in range(0,len(templates),20):
        target=OUT/('template-data-'+str(offset//20+1))
        batches.append(scenarios.generate_batch(run_id='blind-templates-'+str(offset//20+1),tenant=config['tenant_id'],
            event_time=config['base_time'],out=target,template_ids=templates[offset:offset+20]))
    save('generation.json',{'streaming':generated,'template_count':len(templates),
                           'template_batches':[{'run_id':b['run_id'],'count':b['count']} for b in batches],
                           'network_calls':0,'model_calls':0,'business_writes':0})
print(json.dumps({'alerts':len(projected),'context_events':13,'templates':len(templates),'offline':True}))
