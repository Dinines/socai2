"""Direct four-phase wiring checks using a fake producer; no network."""
import asyncio,importlib.util,json,shutil,tempfile
from pathlib import Path
from types import SimpleNamespace
E=Path(__file__).resolve().parent;spec=importlib.util.spec_from_file_location('fullflow_sender',E/'batch/send-batch.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Producer:
    sent=[]
    def __init__(self,**kwargs):assert kwargs['acks']=='all' and kwargs['enable_idempotence']
    async def start(self):pass
    async def stop(self):pass
    async def send_and_wait(self,topic,*,value,key):
        self.sent.append((topic,value,key));return SimpleNamespace(topic=topic,partition=0,offset=len(self.sent))
checks=[]
async def main():
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp)/'batch';shutil.copytree(E/'batch',folder);m.ROOT=folder
        p,b,_,_=m.load('S01-context');digest=m.sha256((folder/'manifest.json').read_bytes())
        def save(name,value):(folder/'out'/name).write_text(json.dumps(value))
        try:m.gates(p,b,'S01-context')
        except FileNotFoundError:checks.append('requires_actual_preflight')
        else:raise AssertionError('missing preflight accepted')
        save('preflight.json',{'source':'actual_release_preflight','status':'passed','batch_id':p['batch_id'],
            'prepared_manifest_sha256':digest,'new_batch_alert_count':0,'new_batch_context_count':0,
            'fusion_ready':True,'unique_execution_services':True})
        transport={'bootstrap_servers':p['expected_bootstrap_servers'],'security_protocol':p['security_protocol']}
        try:m.gates(p,b,'S04-context')
        except FileNotFoundError:checks.append('addition_requires_two_saved_first_rounds')
        else:raise AssertionError('addition before first rounds accepted')
        for phase in ('S01','S04'):
            if phase=='S04':save('first-round-gate.json',{'source':'actual_case_readback','status':'passed',
                'batch_id':p['batch_id'],'prepared_manifest_sha256':digest,'case_ids':['one','two'],'result_ids':['one','two']})
            a=await m.send(phase+'-context',Producer,transport);assert a['accepted']==p['counts'][phase+'-context']
            save(phase+'-context-readback.json',{'source':'real_lake_readback','status':'passed','batch_id':p['batch_id'],
                'prepared_manifest_sha256':digest,'context_receipt_sha256':m.sha256((folder/'out'/('send-'+phase+'-context.json')).read_bytes()),
                'event_ids':[r['source_event_id'] for r in b['phases'][phase+'-context']['records']]})
            a=await m.send(phase+'-alerts',Producer,transport);assert a['accepted']==p['counts'][phase+'-alerts']
        assert len(Producer.sent)==17;checks.append('12_context_3_alert_then_1_context_1_alert_exact_wires')
        try:await m.send('S04-alerts',Producer,transport)
        except FileExistsError:checks.append('exclusive_receipt_blocks_replay')
        else:raise AssertionError('replay accepted')
        assert len(Producer.sent)==17
        path=folder/b['phases']['S01-alerts']['records'][0]['wire'];path.write_bytes(path.read_bytes()+b' ')
        try:m.load('S01-alerts')
        except AssertionError:checks.append('changed_frozen_bytes_rejected')
        else:raise AssertionError('changed bytes accepted')
asyncio.run(main())
print(json.dumps({'status':'passed','checks':checks,'transport':'fake producer','real_kafka_messages':0,'model_calls':0},indent=2))
