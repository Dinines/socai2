"""One frozen 1-alert/3-context release batch; preserves the existing CLI guards."""
import asyncio, hashlib, importlib.util, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools/testdata'))
from alert_kafka import kafka_config, load_wire, send_records
from alert_scenarios import _without_answers, sha256

def load(phase):
 assert phase in {'context','alert'}
 manifest=json.loads((ROOT/'manifest.json').read_text());profile=json.loads((ROOT/'profile.json').read_text())
 for name,digest in manifest['files'].items():assert sha256((ROOT/name).read_bytes())==digest,'frozen_file_changed:'+name
 assert profile['batch_id']==manifest['batch_id'] and profile['tenant_id']==manifest['tenant_id']
 assert profile['counts']=={'context':3,'alert':1}
 stage=manifest['phases'][phase];assert stage['topic']==profile['topics'][phase]
 values=[(ROOT/r['wire']).read_bytes() for r in stage['records']]
 for record,value in zip(stage['records'],values):
  payload=json.loads(value);_without_answers(payload)
  assert sha256(value)==record['wire_sha256'] and payload['tenant_id']==profile['tenant_id']
 assert len(values)==profile['counts'][phase]
 if phase=='alert':
  _,validated=load_wire(ROOT/'prepared-alert',profile['tenant_id']);assert values==validated
 else:
  spec=importlib.util.spec_from_file_location('minimal_event_schema',ROOT/'services/fusion/app/services/event_schema.py')
  module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
  assert all(module.validate_event(stage['topic'],json.loads(value),raw_events_topic=profile['topics']['context'],alerts_raw_topic=profile['topics']['alert']).ok for value in values)
 return profile,manifest,stage,values

def gates(profile,manifest,phase):
 digest=sha256((ROOT/'manifest.json').read_bytes())
 gate=json.loads((ROOT/'out/preflight.json').read_text())
 assert gate['status']=='passed' and gate['source']=='actual_release_preflight'
 assert gate['prepared_manifest_sha256']==digest and gate['batch_id']==profile['batch_id'] and gate['tenant_id']==profile['tenant_id']
 assert gate['fusion_ready'] and gate['unique_execution_services'] and not any(gate['business_counts'].values())
 if phase=='alert':
  ack=json.loads((ROOT/'out/send-context.json').read_text());read=json.loads((ROOT/'out/context-readback.json').read_text())
  assert ack['status']=='accepted_only' and ack['accepted']==3 and ack['not_attempted']==0 and not ack['cleanup_errors']
  assert ack['topic']==profile['topics']['context'] and ack['prepared_manifest_sha256']==digest
  assert read['status']=='passed' and read['source']=='real_lake_readback' and read['prepared_manifest_sha256']==digest
  assert read['tenant_id']==profile['tenant_id'] and read['batch_id']==profile['batch_id']
  assert read['context_receipt_sha256']==sha256((ROOT/'out/send-context.json').read_bytes())
  assert sorted(read['event_ids'])==sorted(r['source_event_id'] for r in manifest['phases']['context']['records'])
  assert not any(read['business_counts'].values())
 return digest

async def send(phase,producer_factory=None,transport=None):
 profile,manifest,stage,values=load(phase);digest=gates(profile,manifest,phase)
 result=await send_records(records=stage['records'],values=values,tenant=profile['tenant_id'],topic=stage['topic'],receipt=ROOT/'out'/('send-'+phase+'.json'),config=transport or kafka_config(Path(profile['kafka_env_file'])),timeout=profile['timeout_seconds'],request_timeout_ms=profile['request_timeout_ms'],identity={'schema_version':'socai2.release-smoke-send.v1','phase':phase,'batch_id':profile['batch_id'],'prepared_manifest_sha256':digest},producer_factory=producer_factory)
 return result

if __name__=='__main__':
 phase=sys.argv[1]
 if phase=='validate':
  for stage in ('context','alert'):load(stage)
  print(json.dumps({'status':'offline_validated','alerts':1,'context_events':3,'kafka_messages':0,'model_calls':0}))
 else:
  result=asyncio.run(send(phase));print(json.dumps(result,ensure_ascii=False,indent=2))
  assert result['status']=='accepted_only' and not result['cleanup_errors']
