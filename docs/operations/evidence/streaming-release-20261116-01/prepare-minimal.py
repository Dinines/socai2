"""Freeze this new v2 batch and its source on the local Python 3.12 runtime."""
import hashlib,json,shutil,sys
from datetime import datetime,timedelta,timezone
from pathlib import Path

REPO=Path(__file__).resolve().parents[4];E=Path(__file__).resolve().parent;OUT=E/'revision-02/smoke'
P=REPO/'deploy/aisoc21/streaming-release-20261116-02'
cfg=json.loads((P/'release.json').read_text());env=json.loads((P/'fusion-env.json').read_text())
sys.path.insert(0,str(REPO/'tools/testdata'))
from investigation_fixture import generate_fixture,load_fixture
from alert_kafka import prepare_kafka
from alert_scenarios import json_bytes,sha256

OUT.mkdir();(OUT/'out').mkdir()
batch='release-smoke-20261116-01';stamp=(datetime.now(timezone.utc)-timedelta(minutes=3)).replace(microsecond=0).isoformat()
sources=['tools/testdata/investigation_fixture.py','tools/testdata/alert_scenarios.py','tools/testdata/alert_kafka.py','tools/testdata/material-source.json','services/fusion/app/models/alert.py','services/fusion/app/core/kafka_security.py','services/fusion/app/services/event_schema.py']
for name in sources:
 dest=OUT/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/name,dest)
shutil.copy2(E/'send-minimal.py',OUT/'send-minimal.py')
manifest=generate_fixture(run_id=batch,tenant=cfg['identity']['tenant_id'],window_start=stamp,out=OUT/'fixture')
_,payloads,events=load_fixture(OUT/'fixture',tenant=cfg['identity']['tenant_id'])
wire=prepare_kafka(input_dir=OUT/'fixture',tenant=cfg['identity']['tenant_id'],out=OUT/'prepared-alert')
profile={'schema_version':'socai2.release-smoke-profile.v1','batch_id':batch,'release':cfg['release'],'tenant_id':cfg['identity']['tenant_id'],'counts':{'context':3,'alert':1},'topics':{'context':env['KAFKA_TOPIC_RAW_EVENTS'],'alert':env['KAFKA_TOPIC_ALERTS_RAW']},'timeout_seconds':20,'request_timeout_ms':10000,'kafka_env_file':'/run/producer.env','processing_image':'sha256:e95a878b8d1bed6a6639666d5e46215bd38f478a5bd46c9bee5e30992cc7669d','network':cfg['network'],'ca_source':cfg['fusion']['ca_source'],'ca_target':cfg['fusion']['ca_target'],'http_base':cfg['viewer']['upstream'],'connector':{'id':payloads[0]['connector_id'],'name':'Endpoint Collector','connector_type':payloads[0]['connector_type'],'category':'custom','is_enabled':False},'generation_runtime':sys.version.split()[0]}
(OUT/'profile.json').write_bytes(json_bytes(profile))
stages={'context':{'topic':profile['topics']['context'],'records':[{'source_event_id':r['event_id'],'wire':'fixture/'+r['event'],'wire_sha256':r['event_sha256'],'raw_payload_sha256':r['raw_payload_sha256']} for r in manifest['events']]},'alert':{'topic':profile['topics']['alert'],'records':[{**r,'wire':'prepared-alert/'+r['wire']} for r in wire['records']]}}
files={str(p.relative_to(OUT)):sha256(p.read_bytes()) for p in sorted(OUT.rglob('*')) if p.is_file() and '__pycache__' not in str(p) and '/expected/' not in str(p)}
# Expected assertions remain offline; they are not uploaded to the sender.
result={'schema_version':'socai2.release-smoke-prepared.v1','batch_id':batch,'tenant_id':profile['tenant_id'],'phases':stages,'files':files,'generator_source_files':sources,'source_fixture_manifest_sha256':sha256((OUT/'fixture/manifest.json').read_bytes()),'control_only_expectations':True,'status':'prepared_not_sent'}
(OUT/'manifest.json').write_bytes(json_bytes(result))
print(json.dumps({'status':'prepared_not_sent','directory':str(OUT),'batch_id':batch,'utc_start':stamp,'files':len(files),'alerts':1,'context_events':3,'manifest_sha256':sha256((OUT/'manifest.json').read_bytes())},indent=2))
