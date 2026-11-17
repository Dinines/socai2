"""Read the actual HTTP empty state and local service restoration."""
import json,socket,subprocess,urllib.request
from pathlib import Path
from datetime import datetime,timezone
P=Path(__file__).resolve().parent
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));requests=[]
for suffix in ['/test-api/v1/batches','/api/v1/socai2/alerts','/api/v1/socai2/incidents','/api/v1/socai2/cases']:
    with opener.open('http://127.0.0.1:4177'+suffix,timeout=30) as response:
        body=json.load(response);requests.append({'path':suffix,'status':response.status,'body':body})
    assert body['items']==[],body
names=['socai2-case-initial-20261115','socai2-incident-auto-20261115','socai2-alert-auto-20261115','socai2-local-investigation-redis-1','socai2-local-investigation-clickhouse-1','socai2-local-investigation-kafka-1','socai2-local-investigation-zookeeper-1','socai2-local-investigation-postgres-1']
rows=json.loads(subprocess.check_output(['docker','inspect',*names],text=True))
state=[{'name':r['Name'],'state':r['State']['Status']} for r in rows]
assert all(r['state']=='exited' for r in state)
with socket.socket() as s:
    s.settimeout(1);preview_closed=s.connect_ex(('127.0.0.1',58477))!=0
assert preview_closed
r={'status':'passed','observed_at':datetime.now(timezone.utc).isoformat(),'http':requests,'local_temporarily_started_services_restored':state,'preview_58477_closed':preview_closed,'new_model_calls':0,'business_writes':0}
with (P/'final-readback-01.json').open('x') as f:json.dump(r,f,ensure_ascii=False,indent=2)
print(json.dumps({'status':'passed','empty_HTTP_lists':len(requests),'local_services_restored':len(state),'preview_closed':preview_closed}))
