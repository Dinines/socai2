"""A read-only observation of the current 21 services, not an execution gate."""
import json
import subprocess
import sys
from pathlib import Path


PROCESSING = r'''
import asyncio,hashlib,json,sys,tomllib
from pathlib import Path
from uuid import UUID
import asyncpg
from app.socai2 import case_incident_material

async def main(c):
 p=json.loads(Path(c['dispatcher_profile']).read_text())
 url=Path(p['database_url_file']).read_text().strip().replace('postgresql+asyncpg://','postgresql://',1)
 conn=await asyncpg.connect(url,**p['database_connect_args'])
 tenant=UUID(c['tenant_id'])
 try:
  async with conn.transaction(readonly=True):
   await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)",str(tenant))
   target=dict(await conn.fetchrow('SELECT current_database() AS database,current_user AS role'))
   row=await conn.fetchrow('SELECT id,tenant_id,connector_type,is_enabled FROM public.connectors WHERE tenant_id=$1 AND id=$2',tenant,UUID(c['connector_id']))
   connector=dict(row) if row else None
   counts={}
   counts['new_alert_ids_present']=await conn.fetchval('SELECT count(*) FROM socai2.alerts WHERE tenant_id=$1 AND id=ANY($2::uuid[])',tenant,[UUID(v) for v in c['alert_ids']])
   counts['new_source_ids_present']=await conn.fetchval('SELECT count(*) FROM socai2.alert_source_refs WHERE tenant_id=$1 AND source_event_id::text=ANY($2::text[])',tenant,c['source_event_ids'])
   counts['historical_correlation_members']=await conn.fetchval("SELECT count(*) FROM socai2.incident_alerts WHERE tenant_id=$1 AND correlation_basis->>'correlation_key'=ANY($2::text[])",tenant,c['correlation_keys'])
   in_flight=[dict(row) for row in await conn.fetch("SELECT state,count(*) AS count FROM socai2.analysis_tasks WHERE tenant_id=$1 AND state IN ('accepted','waiting','running') GROUP BY state",tenant)]
   readonly=await conn.fetchval('SHOW transaction_read_only')=='on'
  assert readonly
  assert target=={'database':c['expected_database'],'role':c['expected_database_user']}
  assert connector and connector['connector_type']==c['connector_type'] and connector['is_enabled']
  assert all(value==0 for value in counts.values())
  source=Path(case_incident_material.__file__)
  result={'status':'passed_current_target_readonly','target':target,'tenant_id':str(tenant),'connector':connector,
   'new_scope_collision_counts':counts,'in_flight_at_observation':in_flight,'transaction_read_only':readonly,
   'case_incident_material_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
   'dispatch_max_running_tasks':p['dispatch']['max_running_tasks'],
   'dispatcher_profile_sha256':hashlib.sha256(Path(c['dispatcher_profile']).read_bytes()).hexdigest(),
   'business_writes':0,'model_generation_calls':0}
  executor=json.loads(Path(p['executor_config_file']).read_text())
  policy_file=Path(executor['investigation_policy_file'])
  policy=tomllib.loads(policy_file.read_text())
  selected={}
  def numeric_limits(value,path=''):
   if isinstance(value,dict):
    for key,child in value.items(): numeric_limits(child,path+'.'+key if path else key)
   elif type(value) in (int,float) and any(word in path for word in ('token','context_window','max_output','max_input')):
    selected[path]=value
  numeric_limits(policy)
  result.update(policy_sha256=hashlib.sha256(policy_file.read_bytes()).hexdigest(),policy_numeric_token_limits=selected)
  print(json.dumps(result,default=str))
 finally: await conn.close()

try: asyncio.run(main(json.load(sys.stdin)))
except Exception as exc:
 print(json.dumps({'status':'failed_readonly_observation','error_type':type(exc).__name__,'detail':'No exception message or credential values are exported.'}))
 sys.exit(2)
'''

VIEWER = r'''
import hashlib,json
from pathlib import Path
import investigation_test
p=Path(investigation_test.__file__).parent/'web/viewer.js'
print(json.dumps({'viewer.js_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
'''

REMOTE = r'''
import datetime,json,subprocess,urllib.request

def metadata():
 result={}
 for role,name in cfg['containers'].items():
  row=json.loads(subprocess.run(['docker','inspect',name],capture_output=True,text=True,timeout=cfg['container_timeout_seconds'],check=True).stdout)[0]
  result[role]={'name':name,'id':row['Id'],'image':row['Image'],'running':row['State']['Running'],'started_at':row['State']['StartedAt'],'restart_count':row['RestartCount']}
 return result

def docker_json(name,script,body=None):
 r=subprocess.run(['docker','exec','-i',name,'python','-c',script],input=json.dumps(body or {}),capture_output=True,text=True,timeout=cfg['container_timeout_seconds'])
 try: value=json.loads(r.stdout.strip().splitlines()[-1])
 except Exception: value={'status':'unreadable_observation','detail':'Container stdout/stderr omitted to avoid credential exposure.'}
 return {'exit_code':r.returncode,'result':value}

before=metadata()
health={}
for name,url in cfg['health_urls'].items():
 try:
  with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url,timeout=cfg['connect_timeout_seconds']) as r:
   health[name]={'url':url,'status_code':r.status,'body':json.loads(r.read())}
 except Exception as e: health[name]={'url':url,'error_type':type(e).__name__}
processing=docker_json(cfg['containers']['processing'],PROCESSING,cfg)
viewer=docker_json(cfg['containers']['viewer'],VIEWER)
after=metadata()
print(json.dumps({'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':cfg['scope'],
 'services_before':before,'services_after':after,'service_lifecycle_unchanged':before==after,'health':health,
 'processing':processing,'viewer':viewer,'new_business_writes':0,'new_kafka_sends':0,'new_model_calls':0}))
'''


def main(config_path, output_path):
    cfg = json.loads(config_path.read_text())
    script = ('import json\n'+'cfg=json.loads('+repr(json.dumps(cfg))+')\n'+
              'PROCESSING='+repr(PROCESSING)+'\nVIEWER='+repr(VIEWER)+'\n'+REMOTE)
    command = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout='+str(cfg['connect_timeout_seconds']),
               cfg['ssh_target'], 'python3', '-']
    result = subprocess.run(command, input=script, text=True, capture_output=True,
                            timeout=cfg['command_timeout_seconds'])
    if result.returncode:
        value = {'status': 'transport_failed', 'exit_code': result.returncode,
                 'detail': 'Raw transport/provider errors omitted; no business write performed.'}
    else:
        value = json.loads(result.stdout)
        value['local_source_hashes'] = cfg['source_hashes']
        actual = {'case_incident_material': value['processing']['result'].get('case_incident_material_sha256'),
                  'viewer.js': value['viewer']['result'].get('viewer.js_sha256')}
        value['source_matches_local_candidate'] = {k: actual[k] == v for k, v in cfg['source_hashes'].items()}
        value['ready_to_execute'] = False
        value['not_verified'] = ['final acceptance container connections to HTTP/PG/lake/Kafka advertised brokers',
                                 'Redis/model live readiness in final target profile',
                                 'report deep links and automatic purple source registration',
                                 'candidate deployment and real first/append part']
    with output_path.open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    assert result.returncode == 0
    assert value['processing']['exit_code'] == 0 and value['viewer']['exit_code'] == 0
    assert value['service_lifecycle_unchanged'] and all(v['status_code'] == 200 for v in value['health'].values())
    assert value['health']['viewer']['body']['investigation_http']['tenant_id'] == cfg['tenant_id']
    print(json.dumps({'read_only_observation': 'passed', 'versions_match_local': value['source_matches_local_candidate'],
                      'ready_to_execute': False, 'new_scope_collisions': value['processing']['result']['new_scope_collision_counts']}, ensure_ascii=False))


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
