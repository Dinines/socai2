"""Read broker offsets through deployed TLS settings; group-state CLI is metadata only."""
import datetime
import json
import subprocess
import sys

cfg = json.load(sys.stdin)
source = r'''
import asyncio,json,os,sys
from aiokafka import AIOKafkaConsumer,TopicPartition
from app.core.kafka_security import kafka_client_kwargs
cfg=json.load(sys.stdin)
async def main():
    result={'topics':{},'groups':[],'security_protocol':os.environ['KAFKA_SECURITY_PROTOCOL']}
    for group in cfg['groups']:
        c=AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],group_id=group,
            enable_auto_commit=False,auto_offset_reset='none',request_timeout_ms=15000,
            **kafka_client_kwargs(environment='production'))
        await c.start()
        try:
            metadata=await c._client.fetch_all_metadata()
            parts=[TopicPartition(t,p) for t in cfg['topics'] for p in sorted(metadata.partitions_for_topic(t) or [])]
            starts,ends=await asyncio.gather(c.beginning_offsets(parts),c.end_offsets(parts))
            result['topics']={t:[{'partition':p.partition,'begin':starts[p],'end':ends[p]} for p in parts if p.topic==t] for t in cfg['topics']}
            offsets=[]
            for p in parts:
                offset=await c.committed(p)
                if offset is not None:
                    offsets.append({'topic':p.topic,'partition':p.partition,'committed':offset,'end':ends[p],'lag':ends[p]-offset})
            result['groups'].append({'group':group,'offsets':offsets,'subscription':None,'auto_commit':False})
        finally:
            await c.stop()
    print(json.dumps(result))
asyncio.run(main())
'''
out = {'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'mode': 'read_only', 'target': cfg['target']}
p = subprocess.run(['docker', 'exec', '-i', 'socai2-investigation-projection', 'python', '-B', '-c', source],
    input=json.dumps(cfg), text=True, capture_output=True, timeout=35)
out['offsets'] = json.loads(p.stdout) if p.returncode == 0 else {'state': 'probe_error', 'exit_code': p.returncode,
    'error_class': p.stderr.splitlines()[-1].split(':')[0] if p.stderr else 'no_stderr'}
out['group_states'] = []
for group in cfg['groups']:
    p = subprocess.run(['docker', 'exec', 'sting-infra21-kafka-1', 'kafka-consumer-groups',
        '--bootstrap-server', cfg['kafka_internal_metadata_endpoint'], '--describe', '--state', '--group', group],
        text=True, capture_output=True, timeout=15)
    out['group_states'].append({'group': group, 'exit_code': p.returncode, 'stdout': p.stdout.strip()})
print(json.dumps(out, ensure_ascii=False, indent=2))
