"""Read the newly published ledger and one actual model original through 4177."""

import argparse
import importlib.util
import json
from pathlib import Path

from investigation_test.models import Document

E = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("batch_invoke", E / "invoke.py")
invoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(invoke)

CODE = r'''
import hashlib,json,sys,urllib.request
from pathlib import Path
from urllib.parse import urlencode
x=json.load(sys.stdin);p=x['profile'];root=Path(p['release_root']);c=json.loads((root/'config/release.json').read_text());base='http://'+c['viewer']['bind']+':'+str(c['viewer']['port']);doc=x['document'];reads=[]
def get(path,raw=False):
 with urllib.request.urlopen(base+path,timeout=p['timeouts']['http_seconds']) as r:
  data=r.read();assert r.status==200;reads.append({'path':path,'status':r.status,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 return data if raw else json.loads(data)
def pages(path):
 result=[];cursor=None;seen=set()
 while True:
  params={'limit':p['directory_page_size']}
  if cursor:params['cursor']=cursor
  page=get(path+'?'+urlencode(params));result.extend(page['items']);cursor=page['next_cursor']
  if cursor is None:assert len(result)==page['total'];return result
  assert cursor not in seen;seen.add(cursor)
caps=get('/test-api/v1/capabilities');assert caps['environment_label']==p['release'] and caps['service_version']=='0.6.0'
batches=pages('/test-api/v1/batches');assert [b['batch']['id'] for b in batches]==x['expected_batches']
batch=get(batches[0]['detail_url']);assert batch['batch']==doc['batch']
path='/test-api/v1/batches/'+doc['batch']['id'];assert get(path+'/preparation')['preparation']==doc['preparation']
for name in ['cases','operations','quality-issues']:
 actual=pages(path+'/'+name);expected=doc[name.replace('-','_')]
 assert {r['id']:r for r in actual}=={r['id']:r for r in expected},name
for e in batch['evidence']:
 metadata=get(e['metadata_url']);raw=get(metadata['content_url'],True)
 assert hashlib.sha256(raw).hexdigest()==metadata['sha256']==x['hashes'][e['id']+'.json']['sha256']
 assert len(raw)==metadata['size']
business=get('/api/v1/socai2/cases');assert {i['case']['id'] for i in business['items']}==set(x['case_ids'])
original=get(x['original']['path']);assert original==x['original']['body']
print(json.dumps({'status':'passed','batch_id':doc['batch']['id'],'revision':batch['revision'],'environment':caps['environment_label'],'cases':len(doc['cases']),'operations':len(doc['operations']),'quality_issues':len(doc['quality_issues']),'evidence_files':len(batch['evidence']),'http_gets':len(reads),'real_business_cases_via_proxy':business['total'],'model_original_via_proxy':x['original']['path'],'reads':reads},ensure_ascii=False))
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--preparation", default="ledger-preparation.json")
    args = parser.parse_args()
    assert args.label.replace("-", "").isalnum()
    p = json.loads((E / "batch/profile.json").read_text())
    invoke.require_ready(p)
    assert Path(args.preparation).name == args.preparation
    preparation = json.loads((E / args.preparation).read_text())
    doc = Document.model_validate_json((E / preparation.get("input_directory", "viewer-input") / "document.json").read_text()).model_dump(mode="json")
    index = json.loads((E / "model-io/index.json").read_text())
    original = next(r for r in reversed(index["requests"]) if r["stage"] == "C6")
    responses = json.loads((E / "final-http-01.json").read_text())["value"]["http"]
    reading = next(r for r in responses if isinstance(r["body"], dict) and r["body"].get("availability") == "available" and r["body"].get("artifact", r["body"].get("metadata", {})).get("id") == original["original_artifact_id"])
    payload = {"profile": p, "document": doc, "hashes": preparation["files"], "expected_batches": [doc["batch"]["id"], *preparation.get("preserve_batch_ids", [])], "case_ids": [r["case_id"] for r in json.loads((E / "case-mapping.json").read_text()).values()], "original": reading}
    value = invoke.remote(p, ["python3", "-c", CODE], json.dumps(payload), args.label)
    print(json.dumps({k: v for k, v in value.items() if k != "reads"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
