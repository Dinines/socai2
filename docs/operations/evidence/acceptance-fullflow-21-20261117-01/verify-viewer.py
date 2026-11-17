"""Read the published ledger and both C6 originals through the existing 4177 tunnel."""
import hashlib
import json
import urllib.request
from pathlib import Path
from investigation_test.models import Document

ROOT=Path(__file__).resolve().parent
config=json.loads((ROOT/'viewer-readback-config.json').read_text())
document=Document.model_validate_json((ROOT/'viewer-input-02/document.json').read_text()).model_dump(mode='json')
reads=[]


def get(path,raw=False):
    with urllib.request.urlopen(config['base_url']+path,timeout=config['timeout_seconds']) as response:
        body=response.read()
        assert response.status==200
        reads.append({'path':path,'status':response.status,'sha256':hashlib.sha256(body).hexdigest()})
    return body if raw else json.loads(body)


caps=get('/test-api/v1/capabilities')
assert caps['environment_label']==document['batch']['environment']
page=get('/test-api/v1/batches?limit='+str(config['page_size']))
assert page['total']==1 and page['items'][0]['batch']['id']==document['batch']['id']
batch=get(page['items'][0]['detail_url'])
assert batch['batch']==document['batch']
root='/test-api/v1/batches/'+document['batch']['id']
for kind in ['cases','operations','quality-issues']:
    actual=get(root+'/'+kind+'?limit='+str(config['page_size']))
    assert actual['next_cursor'] is None
    assert {item['id']:item for item in actual['items']}=={item['id']:item for item in document[kind.replace('-','_')]}
for evidence in batch['evidence']:
    raw=get(evidence['content_url'],True)
    source=next(item for item in document['evidence'] if item['id']==evidence['id'])
    assert raw==(ROOT/'viewer-input-02'/source['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==evidence['sha256']
snapshot=json.loads((ROOT/'results/prepared/runs/part2/saved-records.json').read_text())
steps={step['id']:step for step in snapshot['run_steps']}
selected=[artifact for artifact in snapshot['artifacts'] if isinstance(artifact.get('content_json'),dict)
          and 'raw' in artifact['content_json'] and steps.get(artifact['step_id'],{}).get('stage_code')=='C6']
receipts=[json.loads(path.read_text()) for path in (ROOT/'results/prepared/runs/part2/http').glob('*.json')
          if not path.name.endswith('.intent.json')]
originals=[]
for artifact in selected:
    paths=[]
    for receipt in receipts:
        body=receipt.get('response',{}).get('body')
        if isinstance(body,dict) and body.get('availability')=='available' and (body.get('artifact') or body.get('metadata') or {}).get('id')==artifact['id']:
            paths.append(receipt['request']['path'])
    assert paths
    actual=get(paths[0])
    assert actual['content_json']==artifact['content_json'] and actual['content_text']==artifact['content_text']
    originals.append({'artifact_id':artifact['id'],'run_id':artifact['run_id'],'path':paths[0],'identical':True})
result={'status':'passed','environment':caps['environment_label'],'batch_id':document['batch']['id'],
        'revision':batch['revision'],'operations':len(document['operations']),'quality_issues':len(document['quality_issues']),
        'evidence_files':len(batch['evidence']),'model_originals':originals,'http_gets':len(reads),'reads':reads,
        'new_business_posts':0,'new_model_calls':0}
with (ROOT/'viewer-http-verification.json').open('x') as out:
    json.dump(result,out,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='reads'},ensure_ascii=False))
