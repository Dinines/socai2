"""Freeze only business wire records and the bounded sender; expected answers stay local."""
import hashlib,json,shutil,sys
from pathlib import Path

E=Path(__file__).resolve().parent;R=E.parents[3];P=R/'deploy/aisoc21/streaming-release-20261116-03'
c=json.loads((P/'release.json').read_text());old=R/'deploy/aisoc21/streaming-release-20261116-02'
env=json.loads((old/'fusion-env.json').read_text());f=json.loads((E/'fixture-profile.json').read_text())
build=json.loads(next(E.glob('processing-build-*.json')).read_text());image=json.loads(build['stdout'])['image_id']
sys.path.insert(0,str(R/'tools/testdata'));from alert_kafka import source_wire
target=E/'batch';target.mkdir();(target/'out').mkdir()
sources=['tools/testdata/alert_kafka.py','tools/testdata/alert_scenarios.py','tools/testdata/material-source.json',
 'services/fusion/app/models/alert.py','services/fusion/app/services/event_schema.py','services/fusion/app/core/kafka_security.py']
for name in sources:
    dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/name,dest)
shutil.copy2(E/'send-batch.py',target/'send-batch.py')
phases={};alerts=[];events=[]
for phase,file,kind in [('S01-context','S01/context-events.jsonl','context'),('S01-alerts','S01/alerts.jsonl','alert'),
                        ('S04-context','S04/context-events.jsonl','context'),('S04-alerts','S04/alerts.jsonl','alert')]:
    records=[]
    for i,line in enumerate((E/'input/clean-data-01'/file).read_bytes().splitlines()):
        payload=json.loads(line);name='wire/'+phase+'/'+str(i)+'.json';dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(line)
        record={'wire':name,'wire_sha256':hashlib.sha256(line).hexdigest()}
        if kind=='alert':
            wire,aid=source_wire(payload,f['tenant_id']);assert wire==payload
            record.update(alert_id=payload['id'],predicted_canonical_alert_id=aid);alerts.append(aid)
        else:record['source_event_id']=payload['event_id'];events.append(payload['event_id'])
        records.append(record)
    phases[phase]={'kind':kind,'records':records}
sample=json.loads((target/phases['S01-alerts']['records'][0]['wire']).read_text())
profile={'batch_id':f['batch_id'],'tenant_id':f['tenant_id'],'release':c['release'],'release_root':c['root'],
 'prior_runtime_root':c['prior_runtime_root'],'remote_directory':c['root']+'/verification/'+f['batch_id'],
 'counts':{k:len(v['records']) for k,v in phases.items()},'topics':{'context':env['KAFKA_TOPIC_RAW_EVENTS'],'alert':env['KAFKA_TOPIC_ALERTS_RAW']},
 'expected_bootstrap_servers':env['KAFKA_BOOTSTRAP_SERVERS'],'security_protocol':env['KAFKA_SECURITY_PROTOCOL'],
 'producer_env_file':'/run/producer.env','timeout_seconds':20,'request_timeout_ms':10000,'processing_image':image,
 'network':c['network'],'user':c['user'],'http_base':c['viewer']['upstream'],'ssh_target':c['ssh_target'],
 'connector':{'id':sample['connector_id'],'name':'Endpoint Collector','connector_type':sample['connector_type'],'category':'custom','is_enabled':False},
 'alert_ids':alerts,'event_ids':events,'case_titles':{'whole':'主机活动关联调查','single':'登录活动调查'},
 'containers':{'fusion':c['fusion']['name'],'analysis':c['analysis']['name'],'http':'socai2-production-http-20261116'},
 'ca_source':c['fusion']['ca_source'],'ca_target':c['fusion']['ca_target']}
(target/'profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n')
files={str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest() for p in target.rglob('*') if p.is_file()}
m={'batch_id':f['batch_id'],'tenant_id':f['tenant_id'],'phases':phases,'files':files,'expected_answers_uploaded':False}
(target/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
print(json.dumps({'prepared':str(target),'counts':profile['counts'],'image':image,'files':len(files),'expected_answers_uploaded':False},indent=2))
