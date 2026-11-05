"""New k3 Kafka batch verifies fixed writer with INSERT privilege only in new lake."""
import hashlib
import json
import shlex
import subprocess

from verify_socai2_store_20261103 import DEST, ROOT, SSH

CODE = r'''
import importlib.util,json,sys,secrets,hashlib
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
p=Path('/opt/sting-aisoc-socai2/evidence/next-kafka-k2-20261105/kafka_chain_remote.py')
s=importlib.util.spec_from_file_location('k2',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
root=Path('/opt/sting-aisoc-socai2/evidence/next-kafka-k3-lake-20261105');root.mkdir(mode=0o700,exist_ok=False)
source=json.load(sys.stdin)
def save(name,value):
 path=root/(name+'.json')
 with path.open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False)
 path.chmod(0o600)
before=m.service.protected_model_config()
cases=[]
for batch in ('k1','k2'):
 plan=json.loads(Path('/opt/sting-aisoc-socai2/evidence/next-kafka-'+batch+'-20261105/plan.json').read_text())
 cases.extend({'key':batch+'-'+c['key'],'events':c['events'],'alerts':[]} for c in plan['cases'])
ids=[e['event_id'] for c in cases for e in c['events']]
assert len(ids)==len(set(ids))==16
save('intent',{'source_hashes':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in source.items()},'event_ids':ids,'new_alerts':0,'models':0,'test_writer_new_lake_only':True})
for name,text in source.items():
 assert name in ('writer.py','child.py')
 (root/name).write_text(text);(root/name).chmod(0o600)
files={p.relative_to(m.RELEASE/'fusion').as_posix():p.read_text() for p in (m.RELEASE/'fusion/app').rglob('*.py')}
files['app/services/lake_writer.py']=source['writer.py']
old=m.service.environment('socai2-fusion-1');new=m.service.environment(m.service.NEW)
env={k:v for k,v in old.items() if k.startswith('KAFKA_')}
prefix='socai2.validation.k3.20261105'
user='socai2_kafka_k3_writer_20261105';password=secrets.token_hex(32)
env.update({'KAFKA_TOPIC_ALERTS_RAW':prefix+'.alerts.raw','KAFKA_TOPIC_RAW_EVENTS':prefix+'.raw_events',
 'KAFKA_TOPIC_ALERTS_FUSED':prefix+'.alerts.fused','KAFKA_CONSUMER_GROUP':'socai2-validation-k3-20261105',
 'KAFKA_SSL_CAFILE':'/run/certs/ca.crt','DATABASE_URL':new['DATABASE_URL'],
 'REDIS_URL':urlunsplit(urlsplit(new['REDIS_URL'])._replace(path='/13')),'ENVIRONMENT':'production',
 'AISOC_ALERT_STORE_SCHEMA':'socai2','AISOC_EVENT_PROMOTION_ENABLED':'false','AISOC_UEBA_FUSION_ENABLED':'false',
 'AISOC_DETECTION_ENGINE_ENABLED':'false','AISOC_WINDOWED_DETECTION_ENABLED':'false','CLICKHOUSE_DATABASE':m.service.LAKE,
 'CLICKHOUSE_HOST':old['CLICKHOUSE_HOST'],'CLICKHOUSE_PORT':old['CLICKHOUSE_PORT'],
 'CLICKHOUSE_USER':user,'CLICKHOUSE_PASSWORD':password})
where='tenant_id='+m.service.literal(m.service.TENANT)+' AND event_id IN ('+','.join(m.service.literal(i) for i in ids)+')'
assert m.service.lake('SELECT count() FROM aisoc.raw_events WHERE '+where)=='0'
assert m.service.lake('SELECT count() FROM socai2_next_validation.raw_events WHERE '+where)=='0'
m.service.lake('CREATE USER '+user+' IDENTIFIED WITH sha256_password BY '+m.service.literal(password)+'; GRANT INSERT, SELECT ON socai2_next_validation.raw_events TO '+user)
try:
 packet={'environment':env,'files':files,'cases':cases,'topic_prefix':prefix,'replay_alert':False,'expected_fused':0,'expected_lake':16}
 output=m.service.command(['docker','exec','-i',m.service.NEW,'python','-c',source['child.py']],body=json.dumps(packet).encode(),timeout=180)
 records=[json.loads(x.removeprefix('K1_RESULT=')) for x in output.splitlines() if x.startswith('K1_RESULT=')]
 assert len(records)==1
 save('consumer',records[0])
 sql='SELECT toString(event_id) AS event_id,count() AS rows FROM socai2_next_validation.raw_events WHERE '+where+' GROUP BY event_id ORDER BY event_id FORMAT JSONEachRow'
 rows=[json.loads(x) for x in m.service.lake(sql).splitlines()]
 old_count=m.service.lake('SELECT count() FROM aisoc.raw_events WHERE '+where)
 save('readback',{'rows':rows,'all_16_exactly_once':len(rows)==16 and all(int(r['rows'])==1 for r in rows),'old_lake_rows':int(old_count),'protected_unchanged':before==m.service.protected_model_config()})
finally:
 m.service.lake('DROP USER '+user)
 save('cleanup',{'temporary_writer_removed':m.service.lake('SELECT count() FROM system.users WHERE name='+m.service.literal(user))=='0'})
files={p.name:json.loads(p.read_text()) for p in root.glob('*.json')}
print(json.dumps({'export':files,'consumer_passed':records[0]['passed'],'new_lake_rows':len(rows),'old_lake_rows':int(old_count),'temporary_writer_removed':files['cleanup.json']['temporary_writer_removed']}))
'''

if __name__ == '__main__':
    target = ROOT / 'docs/operations/evidence/socai2-kafka-chain-20261105/k3-lake'
    target.mkdir(exist_ok=False)
    source = {'writer.py': (ROOT / 'services/fusion/app/services/lake_writer.py').read_text('utf-8'),
              'child.py': (ROOT / 'deploy/aisoc21/kafka_chain_child.py').read_text('utf-8')}
    for name, text in source.items():
        (target / name).write_text(text, 'utf-8')
    result = subprocess.run(SSH + [DEST, shlex.join(['python3', '-c', CODE])], input=json.dumps(source).encode(), capture_output=True, timeout=210, check=False)
    if result.returncode:
        (target / 'failure.json').write_text(json.dumps({'exit_code':result.returncode,'stderr_sha256':hashlib.sha256(result.stderr).hexdigest()}),'utf-8')
        raise RuntimeError('new k3 batch failed; inspect before any further action')
    data = json.loads(result.stdout)
    for name, value in data.pop('export').items():
        assert name in {'intent.json','consumer.json','readback.json','cleanup.json'}
        (target / name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n','utf-8')
    (target / 'receipt.json').write_text(json.dumps(data, indent=2)+'\n','utf-8')
    print(json.dumps(data))
