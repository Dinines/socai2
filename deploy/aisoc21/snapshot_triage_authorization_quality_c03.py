"""Fresh C03-02C-02 baselines after freeze, before provision; never replay.

One Fusion metrics HTTP request, read-only SQL and Kafka metadata only.
The disconnected probe reads/parses only the new public operator file.
No keys, policy, DDL, broker publication/commit or model/service changes.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess

import prepare_triage_authorization_quality_c03 as p

METADATA = '''import asyncio,json,os,sys
from aiokafka import AIOKafkaConsumer,TopicPartition
from app.core.kafka_security import kafka_client_kwargs
cfg=json.load(sys.stdin)
async def main():
 security=kafka_client_kwargs();assert security['security_protocol']=='SSL'
 if cfg['kind']=='raw':
  from app.core.config import settings
  rows={'raw':(settings.kafka_topic_alerts_raw,settings.kafka_consumer_group)}
 else:
  rows={'main':(os.getenv('KAFKA_TOPIC_ALERTS_FUSED','aisoc.alerts.fused'),os.getenv('KAFKA_CONSUMER_GROUP','aisoc-agents-triage')),
   'quality':('socai2.c03.triage-quality.20261021','socai2-c03-triage-quality-20261021'),
   'dlq':('socai2.c03.triage-quality.20261021.dlq',None),
   'recheck_quality':('socai2.c03.triage-quality-recheck.20261021','socai2-c03-triage-quality-recheck-20261021'),
   'recheck_dlq':('socai2.c03.triage-quality-recheck.20261021.dlq',None)}
 out={}
 for alias,(topic,group) in rows.items():
  c=AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],group_id=group,enable_auto_commit=False,**security)
  await c.start()
  try:
   await c._client.add_topic(topic);parts=c.partitions_for_topic(topic);assert parts
   tps=[TopicPartition(topic,n) for n in sorted(parts)]
   begins,ends=await c.beginning_offsets(tps),await c.end_offsets(tps)
   out[alias]={'topic':topic,'group':group,'partitions':[{'partition':tp.partition,'begin':begins[tp],
    'end':ends[tp],'committed':await c.committed(tp) if group else None} for tp in tps],
    'physical_record_reads':0,'polls':0,'assigns':0,'commits':0}
  finally:await c.stop()
 print(json.dumps(out))
asyncio.run(main())'''

METRICS = '''import json,urllib.request
from app.core.config import settings
with urllib.request.urlopen('http://127.0.0.1:'+str(settings.http_port)+'/metrics',timeout=10) as response:
 value=json.load(response);assert response.status==200 and value['status']=='ok'
 print(json.dumps(value))'''

READ_PROBE = '''from pathlib import Path
import ast,hashlib,json,os
b=Path('/operators/quality.py').read_bytes();ast.parse(b)
print(json.dumps({'operator_sha256':hashlib.sha256(b).hexdigest(),'uid':os.geteuid(),'readable':True,'ast_valid':True}))'''


def table_hashes(names):
    result = {}
    for name in names:
        exists = p.base.pg("SELECT to_regclass('public." + name + "') IS NOT NULL;").stdout.strip() == 't'
        rows = []
        if exists:
            values = json.loads(p.base.pg("SELECT COALESCE(json_agg(x),'[]'::json) FROM "
                '(SELECT row_to_json(t)::text AS material FROM public.' + name +
                ' t ORDER BY row_to_json(t)::text) x;').stdout)
            rows = sorted(hashlib.sha256(row['material'].encode()).hexdigest() for row in values)
        result[name] = {'exists': exists, 'row_sha256': rows}
    return {'tables': result}


def main():
    os.umask(0o077)
    p.PHASE = 'snapshot-before-provision'
    assert os.geteuid() == 0 and (p.E / 'prepared.json').is_file()
    assert not (p.E / 'provision-started.json').exists() and not (p.P / 'state-provisioned.json').exists()
    assert not (p.E / 'provisioned.json').exists() and not (p.P / 'state.json').exists() and not (p.E / 'cases').exists()
    assert p.read(p.P / 'state-draft.json')['execution_authorized'] is False
    assert p.sha(p.POLICY) == p.sha(p.P / 'policy-before.json') == p.read(p.E / 'before.json')['policy_sha256']
    p.frozen_inputs()
    started = p.E / 'snapshot-started.json'
    assert not started.exists()
    p.save(started, {'snapshot_operator_sha256': p.sha(Path(__file__)),
        'prepare_operator_sha256': p.sha(Path(p.__file__)), 'automatic_retry': False,
        'new_keys_or_policy_or_business_writes': 0})
    p.copy_private(Path(__file__), p.E / 'baseline-snapshot-operator.py')
    try:
        p.save(p.E / 'before-extra-tables.json', table_hashes(('incidents', 'aisoc_cases', 'alert_source_links')))
        p.save(p.E / 'before-closure-qa.json', table_hashes(('aisoc_closure_policies', 'aisoc_closure_qa_samples')))
        port = int(p.base.env(p.base.inspect('socai2-fusion-1')).get('HTTP_PORT', '8003'))
        sequence = p.http_start(path='/metrics', host='127.0.0.1', port=port)
        try:
            metrics = p.base.container_json(METRICS, service='fusion')
        except BaseException as error:
            p.http_finish(sequence, error_type=type(error).__name__)
            raise
        else:
            p.http_finish(sequence, status=200, confirmed=True)
        p.save(p.E / 'fusion-metrics-before.json', metrics)
        raw = p.base.container_json(METADATA, service='fusion', payload={'kind': 'raw'})['raw']
        agents = p.base.container_json(METADATA, payload={'kind': 'agents'})
        assert len(agents['quality']['partitions']) == len(agents['dlq']['partitions']) == 1
        assert agents['quality']['partitions'][0] == {'partition': 0, 'begin': 0, 'end': 1, 'committed': 1}
        assert agents['dlq']['partitions'][0] == {'partition': 0, 'begin': 0, 'end': 0, 'committed': None}
        assert agents['recheck_quality']['partitions'] == [{'partition': 0, 'begin': 0, 'end': 1, 'committed': 1}]
        assert agents['recheck_dlq']['partitions'] == [{'partition': 0, 'begin': 0, 'end': 0, 'committed': None}]
        p.save(p.E / 'fusion-raw-metadata-before.json', raw)
        p.save(p.E / 'main-fused-metadata-before.json', agents['main'])
        p.save(p.E / 'old-quality-metadata-before.json', {'quality': agents['quality'], 'dlq': agents['dlq']})
        p.save(p.E / 'old-recheck-quality-metadata-before.json', {'quality': agents['recheck_quality'], 'dlq': agents['recheck_dlq']})
        command = ['docker', 'run', '--rm', '--pull', 'never', '--network', 'none', '--user', '10001:10001',
            '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true',
            '--mount', 'type=bind,src=' + str(p.INSIDE) + ',dst=/operators/quality.py,readonly',
            p.IMAGE, 'python', '-I', '-B', '-c', READ_PROBE]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        p.save(p.E / 'inside-readable-probe-exit.json', {'argv': command, 'exit_code': result.returncode,
            'stdout_sha256': hashlib.sha256(result.stdout.encode()).hexdigest(),
            'stderr_sha256': hashlib.sha256(result.stderr.encode()).hexdigest(),
            'service_env_or_private_forwarded': False})
        assert result.returncode == 0
        assert json.loads(result.stdout) == {'operator_sha256': p.sha(p.INSIDE), 'uid': 10001,
                                          'readable': True, 'ast_valid': True}
        p.save(p.E / 'inside-readable-before-business.json', {'image_id': p.IMAGE,
            'operator_sha256': p.sha(p.INSIDE), 'uid': 10001, 'network': 'none', 'readable': True, 'exit_code': 0})
        assert not (p.E / 'provision-started.json').exists() and not (p.P / 'state-provisioned.json').exists()
        p.save(p.E / 'snapshot-completed.json', {'snapshot_operator_sha256': p.sha(Path(__file__)),
            'baseline_sha256': p.baseline_hashes(), 'old_quality_metadata_sha256': p.sha(p.E / 'old-quality-metadata-before.json'),
            'old_recheck_quality_metadata_sha256': p.sha(p.E / 'old-recheck-quality-metadata-before.json'),
            'read_probe_exit_sha256': p.sha(p.E / 'inside-readable-probe-exit.json'),
            'real_HTTP_requests': 1, 'broker_physical_reads_or_commits_or_publishes': 0,
            'read_probe_app_imports_or_service_env_or_private_mounts': 0, 'read_probe_AST_valid': True,
            'model_or_new_business_writes': 0, 'automatic_retry': False})
        print(json.dumps({'snapshot_completed': True, 'real_HTTP_requests': 1, 'model_or_business_actions': 0}))
    except BaseException as error:
        p.save(p.E / 'snapshot-failure.json', {'error_type': type(error).__name__, 'automatic_retry': False,
            'original_checkpoints_retained': True})
        raise


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        print(json.dumps({'snapshot_failed': True, 'error_type': type(error).__name__, 'locals_or_keys_recorded': False}))
        raise SystemExit(1) from None
