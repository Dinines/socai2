"""Direct offline checks of the one-batch sender, using a fake Kafka producer."""
import asyncio,importlib.util,json,shutil,tempfile
from pathlib import Path
from types import SimpleNamespace
E=Path(__file__).resolve().parent;src=E/'revision-02/smoke'
spec=importlib.util.spec_from_file_location('minimal_driver',src/'send-minimal.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checks=[]
class Fake:
 calls=[]
 def __init__(self,**kwargs):assert kwargs['acks']=='all' and kwargs['enable_idempotence']
 async def start(self):pass
 async def stop(self):pass
 async def send_and_wait(self,topic,*,value,key):
  self.calls.append((topic,value,key));return SimpleNamespace(topic=topic,partition=0,offset=len(self.calls))
async def check():
 with tempfile.TemporaryDirectory() as td:
  tmp=Path(td)/'batch';shutil.copytree(src,tmp);m.ROOT=tmp
  p,b,_,_=m.load('context');m.load('alert');checks.append('both_frozen_stages_validate')
  try:m.gates(p,b,'context')
  except FileNotFoundError:checks.append('missing_live_preflight_rejected')
  else:raise AssertionError('missing preflight accepted')
  digest=m.sha256((tmp/'manifest.json').read_bytes())
  gate={'status':'passed','source':'actual_release_preflight','prepared_manifest_sha256':digest,'batch_id':p['batch_id'],'tenant_id':p['tenant_id'],'fusion_ready':True,'unique_execution_services':True,'business_counts':{'alerts':0,'tasks':0,'runs':0}}
  (tmp/'out/preflight.json').write_text(json.dumps(gate))
  try:m.gates(p,b,'alert')
  except FileNotFoundError:checks.append('alert_requires_context_ack_and_readback')
  else:raise AssertionError('missing context accepted')
  transport={'bootstrap_servers':'offline.invalid:9092','security_protocol':'SSL'}
  sent=await m.send('context',Fake,transport);assert sent['accepted']==3 and len(Fake.calls)==3
  read={'status':'passed','source':'real_lake_readback','prepared_manifest_sha256':digest,'batch_id':p['batch_id'],'tenant_id':p['tenant_id'],'event_ids':[r['source_event_id'] for r in b['phases']['context']['records']],'business_counts':gate['business_counts'],'context_receipt_sha256':'wrong'}
  (tmp/'out/context-readback.json').write_text(json.dumps(read))
  try:m.gates(p,b,'alert')
  except AssertionError:checks.append('wrong_context_receipt_digest_rejected')
  else:raise AssertionError('wrong digest accepted')
  read['context_receipt_sha256']=m.sha256((tmp/'out/send-context.json').read_bytes());(tmp/'out/context-readback.json').write_text(json.dumps(read))
  sent=await m.send('alert',Fake,transport);assert sent['accepted']==1 and len(Fake.calls)==4
  checks.append('three_context_then_one_alert_exact_bytes')
  try:await m.send('alert',Fake,transport)
  except FileExistsError:checks.append('existing_intent_prevents_resend')
  else:raise AssertionError('repeat accepted')
  assert len(Fake.calls)==4
  wire=tmp/b['phases']['alert']['records'][0]['wire'];wire.write_bytes(wire.read_bytes()+b' ')
  try:m.load('alert')
  except AssertionError:checks.append('changed_wire_rejected')
  else:raise AssertionError('changed wire accepted')
asyncio.run(check())
print(json.dumps({'status':'passed','checks':checks,'transport':'fake producer only','live_kafka_messages':0,'model_calls':0,'expected_directory_not_read_by_sender':True},indent=2))
