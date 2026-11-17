"""Read-only Kafka metadata, Redis counters, source catalogs and loaded config.

No subscription, message fetch, offset commit, model request, service start or cleanup.
Secrets are read only inside their existing container and never returned.
"""
import datetime
import json
import subprocess
import sys

cfg = json.load(sys.stdin)


def child(container, source):
    p = subprocess.run(['docker', 'exec', '-i', container, 'python', '-B', '-c', source],
        input=json.dumps(cfg), text=True, capture_output=True, timeout=35)
    if p.returncode:
        return {'state': 'probe_error', 'exit_code': p.returncode,
                'error_class': p.stderr.splitlines()[-1].split(':')[0] if p.stderr else 'no_stderr'}
    return json.loads(p.stdout)


out = {'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'target': cfg['target'], 'mode': 'read_only', 'model_calls': 0}
out['kafka'] = child('socai2-investigation-projection', r'''
import asyncio,json,os,sys
from aiokafka import AIOKafkaConsumer,TopicPartition
from aiokafka.admin import AIOKafkaAdminClient
from app.core.kafka_security import kafka_client_kwargs
cfg=json.load(sys.stdin)
async def main():
    security=kafka_client_kwargs(environment=os.environ.get('ENVIRONMENT','production'))
    args=dict(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],request_timeout_ms=8000,**security)
    c=AIOKafkaConsumer(group_id=None,enable_auto_commit=False,**args)
    a=AIOKafkaAdminClient(**args)
    await c.start()
    await a.start()
    try:
        metadata=await c._client.fetch_all_metadata()
        parts=[TopicPartition(t,p) for t in cfg['topics'] for p in sorted(metadata.partitions_for_topic(t) or [])]
        starts,ends=await asyncio.gather(c.beginning_offsets(parts),c.end_offsets(parts))
        result={'bootstrap':os.environ['KAFKA_BOOTSTRAP_SERVERS'],'security_protocol':security['security_protocol'],
                'topics':{t:[{'partition':p.partition,'begin':starts[p],'end':ends[p]} for p in parts if p.topic==t] for t in cfg['topics']},'groups':[]}
        descriptions=await a.describe_consumer_groups(cfg['groups'])
        for reply in descriptions:
            for group in reply.groups:
                offsets=await a.list_consumer_group_offsets(group[1])
                result['groups'].append({'group':group[1],'state':group[2],'member_count':len(group[5]),'error_code':group[0],
                    'offsets':[{'topic':p.topic,'partition':p.partition,'committed':o.offset,'end':ends.get(p),'lag':ends[p]-o.offset if p in ends and o.offset>=0 else None} for p,o in offsets.items() if p.topic in cfg['topics']]})
        print(json.dumps(result))
    finally:
        await c.stop()
        await a.close()
asyncio.run(main())
''')
out['redis'] = {}
for name in ['socai2-http-api', 'socai2-fusion-1', 'socai2-agents-1']:
    out['redis'][name] = child(name, r'''
import json,os,urllib.parse
import redis
u=urllib.parse.urlsplit(os.environ['REDIS_URL'])
r=redis.Redis.from_url(os.environ['REDIS_URL'],socket_timeout=5,socket_connect_timeout=5)
result={'host':u.hostname,'port':u.port,'database':u.path.lstrip('/'),'ping':r.ping(),'dbsize':r.dbsize(),
        'new_dispatch_namespace_configured':bool(os.environ.get('SOCAI2_ANALYSIS_DISPATCH_CONFIG_FILE'))}
# The default namespace is an observation only, not proof that every custom namespace is absent.
cursor=0;count=0;iterations=0;types={}
while True:
    cursor,keys=r.scan(cursor,match='socai2-analysis:*',count=100)
    count+=len(keys);iterations+=1
    for key in keys:
        kind=r.type(key).decode();types[kind]=types.get(kind,0)+1
    if cursor==0 or iterations>=100:break
result.update(default_namespace_match_count=count,scan_complete=cursor==0,key_types=types)
print(json.dumps(result))
''')
out['sources_and_config'] = child('socai2-http-api', r'''
import hashlib,json,os,pathlib,sys,tomllib,urllib.request,urllib.error
cfg=json.load(sys.stdin);out={}
for name in ['SOCAI2_INVESTIGATION_POLICY','SOCAI2_KNOWLEDGE_PROFILE','SOCAI2_ANALYSIS_DISPATCH_CONFIG_FILE','SOCAI2_ANALYSIS_TASKS_CONFIG_FILE','SOCAI2_CASE_ALLOCATION_CONFIG_FILE','SOCAI2_HTTP_CONTEXT_FILE']:
    value=os.environ.get(name);row={'configured':bool(value)}
    if value:
        p=pathlib.Path(value);row.update(path=value,exists=p.is_file())
        if p.is_file():
            body=p.read_bytes();row['sha256']=hashlib.sha256(body).hexdigest()
            if p.suffix=='.toml':
                policy=tomllib.loads(body.decode());row['section_names']=list(policy)
                row['limits']={k:v for k,v in policy.items() if k in ['budget','timeouts','limits','execution','model']}
    out[name]=row
for file in ['/app/investigation_http/main.py','/app/app/socai2/alert-input-v1.json','/app/app/socai2/incident-input-v1.json','/app/app/socai2/case-input-v1.json']:
    p=pathlib.Path(file);out[file]={'exists':p.is_file(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None}
try:
    from clickhouse_driver import Client
    c=Client(host=os.environ['CLICKHOUSE_HOST'],port=int(os.environ['CLICKHOUSE_PORT']),
        user=os.environ.get('CLICKHOUSE_USER','default'),password=os.environ.get('CLICKHOUSE_PASSWORD',''),
        database=os.environ['CLICKHOUSE_DATABASE'],connect_timeout=5,send_receive_timeout=5)
    out['lake']={'identity':c.execute('SELECT currentDatabase(),version()'),
        'tables':c.execute("SELECT name FROM system.tables WHERE database=currentDatabase() AND name IN ('raw_events','ueba_anomalies')"),
        'raw_event_columns':c.execute("SELECT name,type FROM system.columns WHERE database=currentDatabase() AND table='raw_events' ORDER BY position")}
except Exception as e:out['lake']={'state':'probe_error','error_class':type(e).__name__}
try:
    p=json.loads(pathlib.Path(os.environ['SOCAI2_KNOWLEDGE_PROFILE']).read_text());v=p['vector']
    req=urllib.request.Request(v['url']+'/collections/'+v['collection'],headers={'api-key':pathlib.Path(v['api_key_file']).read_text().strip()})
    with urllib.request.urlopen(req,timeout=5) as r:
        d=json.load(r)['result'];out['knowledge']={'http_status':r.status,'collection':v['collection'],
            'status':d.get('status'),'points_count':d.get('points_count'),'vectors_count':d.get('vectors_count'),
            'vectors_config':d.get('config',{}).get('params',{}).get('vectors'),
            'embedding_model':p['embedding']['model'],'embedding_dimension':p['embedding']['dimension'],'embedding_called':False}
except Exception as e:out['knowledge']={'state':'probe_error','error_class':type(e).__name__}
print(json.dumps(out))
''')
out['model_route_config_only'] = child('socai2-litellm-1', r'''
import json,pathlib,yaml
p=pathlib.Path('/etc/litellm/config.yaml');d=yaml.safe_load(p.read_text());print(json.dumps([
    {'alias':m.get('model_name'),'upstream_model':m.get('litellm_params',{}).get('model'),
     'upstream_base':m.get('litellm_params',{}).get('api_base')}
    for m in d.get('model_list',[]) if m.get('model_name')=='aisoc-investigation']))
''')
print(json.dumps(out, ensure_ascii=False, indent=2))
