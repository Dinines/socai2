"""Offline replay of actual saved candidates after the final identity-only fix."""
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'services/api')]
from app.socai2.baseline_store import digest, encoded
from app.socai2.case_incident_material import freeze

BASE=Path(__file__).parent
OUT=BASE/'final-normalization-01'
OUT.mkdir(exist_ok=False)
checks=[]


def without_value_hash(value):
    if isinstance(value,dict):return {k:without_value_hash(v) for k,v in value.items() if k!='business_value_sha256'}
    if isinstance(value,list):return sorted([without_value_hash(v) for v in value],key=encoded)
    return value


for kind in ('complete','partial','none'):
    p=BASE/'final-readback-01'/kind
    db=json.loads((p/'database-readback.json').read_text());ctx=json.loads((p/'frozen-context-after-new-alert.json').read_text())
    old=next(iter(ctx['incidents'].values()))['analysis_material'];fs={f['id']:f for f in db['artifacts']}
    a=next(a for a in db['analysis_attempts'] if a['id']==old['attempt_id'])
    candidate={'attempt':a,'task':next(t for t in db['analysis_tasks'] if t['id']==a['task_id']),
        'run':next(r for r in db['runs'] if r['id']==old['source_run_id']), 'input':fs[old['input']['id']],
        'receipt':fs[old['receipt_source']['id']],'response':fs[old['response']['id']],
        'originals':[fs[o['id']] for o in old['originals']]}
    material,reasons=freeze(old['incident_id'],candidate,ctx['alerts'])
    assert material,reasons
    assert {k:v for k,v in material.items() if k!='business_view'}=={k:v for k,v in old.items() if k!='business_view'}
    assert without_value_hash(material['business_view'])==without_value_hash(old['business_view'])
    assert (material['business_view']==old['business_view']) is (kind!='complete')
    # Paired recommendation source IDs may change without changing the model's
    # preserved business result. This assertion exercises the whole selector.
    changed=copy.deepcopy(candidate)
    for member in changed['input']['content_json']['members']:
        if member.get('triage'):
            for recommendation in member['triage'].get('recommendations',[]):
                for ref in recommendation.get('source_refs',[]):ref['id']='11111111-1111-4111-8111-111111111111'
    changed['input']['sha256']=digest(changed['input']['content_json'])
    changed['input']['size_bytes']=len(encoded(changed['input']['content_json']))
    same,why=freeze(old['incident_id'],changed,ctx['alerts']);assert same,why
    assert same['business_view']==material['business_view']
    (OUT/(kind+'-projection.json')).write_text(json.dumps(material,ensure_ascii=False,indent=2)+'\n')
    checks.append({'scenario':kind,'all_saved_units_sources_receipt_identical':True,
        'business_identical_to_saved':kind!='complete','only_business_reference_value_hash_differs':kind=='complete',
        'paired_recommendation_execution_identity_ignored':True,
        'prior_business_digest':digest(old['business_view']),'current_business_digest':digest(material['business_view'])})
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'services/api/app/socai2/case_incident_material.py',Path(__file__)]}
(OUT/'result.json').write_text(json.dumps({'state':'passed','kind':'offline_reprojection_not_new_pg_capture',
    'checks':checks,'source_hashes':manifest,'pg_queries':0,'model_calls':0},indent=2)+'\n')
print('3 saved candidates passed; complete differs only by the intended reference-value normalization')
