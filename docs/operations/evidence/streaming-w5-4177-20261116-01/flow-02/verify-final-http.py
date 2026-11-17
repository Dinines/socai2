"""Direct actual entry/version/assets and post-reset emptiness."""
import hashlib,json,urllib.request
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[4]
profile=json.loads((ROOT/'deploy/investigation-test/release-4177.json').read_text())
base=profile['local_entry'];opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));rows=[]
for path in ['/','/index.html','/test-api/v1/capabilities','/viewer/config.json','/test-api/v1/batches','/api/v1/socai2/alerts','/api/v1/socai2/incidents','/api/v1/socai2/cases','/viewer/assets/viewer.js','/viewer/assets/execution_flow.mjs']:
    with opener.open(base+path,timeout=30) as r:
        body=r.read();row={'path':path,'final_url':r.url,'status':r.status,'sha256':hashlib.sha256(body).hexdigest()}
        assert r.status==200
    if path in ['/','/index.html']:assert row['final_url']==base+'/viewer/'
    elif path.startswith('/viewer/assets/'):
        assert body==(ROOT/'services/investigation_test/web'/path.rsplit('/',1)[1]).read_bytes()
    else:
        value=json.loads(body);row['body']=value
        if path.endswith('/capabilities'):assert value['service_version']==value['viewer_version']=='0.6.0' and value['read_only']
        elif path.endswith('/config.json'):assert value['viewer_version']=='0.6.0'
        else:assert value['items']==[]
    rows.append(row)
result={'status':'passed','actual_entry':base+'/viewer/','service_version':'0.6.0','checks':rows,'gets':len(rows),'all_only_get':True,'model_calls':0,'business_writes':0,'active_batches':0}
with (P/'http-final-03.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
