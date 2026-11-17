"""Single frozen four-phase batch; the existing ACK loop forbids unknown replay."""
import asyncio, importlib.util, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools/testdata'))
from alert_kafka import kafka_config, send_records, source_wire
from alert_scenarios import _without_answers, sha256

def load(phase):
    p=json.loads((ROOT/'profile.json').read_text());m=json.loads((ROOT/'manifest.json').read_text())
    for path,digest in m['files'].items():assert sha256((ROOT/path).read_bytes())==digest
    assert m['batch_id']==p['batch_id'] and m['tenant_id']==p['tenant_id']
    stage=m['phases'][phase];kind=stage['kind'];values=[]
    spec=importlib.util.spec_from_file_location('fullflow_event_schema',ROOT/'services/fusion/app/services/event_schema.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    for record in stage['records']:
        raw=(ROOT/record['wire']).read_bytes();payload=json.loads(raw);_without_answers(payload)
        assert sha256(raw)==record['wire_sha256'] and payload['tenant_id']==p['tenant_id']
        assert module.validate_event(p['topics'][kind],payload,raw_events_topic=p['topics']['context'],alerts_raw_topic=p['topics']['alert']).ok
        if kind=='alert':
            canonical,aid=source_wire(payload,p['tenant_id'])
            assert canonical==payload and aid==record['predicted_canonical_alert_id']
        values.append(raw)
    assert len(values)==p['counts'][phase]
    return p,m,stage,values

def gates(p,m,phase):
    digest=sha256((ROOT/'manifest.json').read_bytes())
    gate=json.loads((ROOT/'out/preflight.json').read_text())
    assert gate['source']=='actual_release_preflight' and gate['status']=='passed'
    assert gate['batch_id']==p['batch_id'] and gate['prepared_manifest_sha256']==digest
    assert gate['new_batch_alert_count']==0 and gate['new_batch_context_count']==0
    assert gate['fusion_ready'] and gate['unique_execution_services']
    if phase.startswith('S04'):
        first=json.loads((ROOT/'out/first-round-gate.json').read_text())
        assert first['source']=='actual_case_readback' and first['status']=='passed'
        assert first['batch_id']==p['batch_id'] and first['prepared_manifest_sha256']==digest
        assert len(first['case_ids'])==2 and len(first['result_ids'])==2
    if phase.endswith('alerts'):
        prefix=phase.split('-')[0];ackpath=ROOT/'out'/('send-'+prefix+'-context.json')
        ack=json.loads(ackpath.read_text());read=json.loads((ROOT/'out'/(prefix+'-context-readback.json')).read_text())
        assert ack['status']=='accepted_only' and ack['accepted']==p['counts'][prefix+'-context']
        assert ack['not_attempted']==0 and not ack['cleanup_errors']
        assert read['status']=='passed' and read['source']=='real_lake_readback'
        assert read['batch_id']==p['batch_id'] and read['prepared_manifest_sha256']==digest
        assert read['context_receipt_sha256']==sha256(ackpath.read_bytes())
        assert sorted(read['event_ids'])==sorted(r['source_event_id'] for r in m['phases'][prefix+'-context']['records'])
    return digest

async def send(phase,producer_factory=None,transport=None):
    p,m,stage,values=load(phase);digest=gates(p,m,phase)
    config=transport or kafka_config(Path(p['producer_env_file']))
    assert config['bootstrap_servers']==p['expected_bootstrap_servers'] and config['security_protocol']==p['security_protocol']
    return await send_records(records=stage['records'],values=values,tenant=p['tenant_id'],topic=p['topics'][stage['kind']],
        receipt=ROOT/'out'/('send-'+phase+'.json'),config=config,timeout=p['timeout_seconds'],
        request_timeout_ms=p['request_timeout_ms'],identity={'schema_version':'socai2.fullflow-send.v1','phase':phase,
        'batch_id':p['batch_id'],'prepared_manifest_sha256':digest},producer_factory=producer_factory)

if __name__=='__main__':
    if sys.argv[1]=='validate':
        for phase in json.loads((ROOT/'profile.json').read_text())['counts']:load(phase)
        print(json.dumps({'status':'offline_validated','model_calls':0,'kafka_messages':0}))
    else:
        result=asyncio.run(send(sys.argv[1]));print(json.dumps(result,indent=2));assert result['status']=='accepted_only' and not result['cleanup_errors']
