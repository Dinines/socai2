"""Host21 C03-R01 candidate. Stdlib host only; each phase is an exclusive attempt.

NOT AUTHORIZED: the adjacent bindings must be independently reviewed and frozen.
No old operator is imported. No phase retries, rolls back, consumes Kafka records,
creates business fixtures, invokes a model, or enables a worker. Private inspect,
render and rollback files stay under P. Public evidence contains hashes/projections.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET

R = Path('/opt/sting-aisoc-socai2')
S = R / 'source'
BATCH = 'c03-triage-review-only-20261021'
ORIGINAL_E = R / 'evidence' / BATCH
E = ORIGINAL_E / 'observation-recovery-r02'
P = R / 'private/completion-c03-review-only'
PAYLOAD = P / 'payload'
PARENT_E = R / 'evidence/c03-triage-validity-quality-20261021'
AGENTS = 'socai2-agents-1'
PROFILE = 'review_only_v1'
PROFILE_ENV = 'AISOC_TRIAGE_ADMISSION_PROFILE'
TAG = 'socai2-agents:triage-review-only-c03-20261021'
BASE_TAG = 'socai2-agents:triage-detection-validity-c03-20261021'
BASE_IMAGE = 'sha256:9cb719ff55d772ebf047f87a06863ae7102feb5be3b9471610113dd9d85728fd'
TEST_TAG = 'socai2-agents-test:1g-20261020'
TEST_IMAGE = 'sha256:017598b8433ddc452524ea0818e9e4cae467bf7d44a735695adda41d12ef0b10'
MANIFEST = 'docs/handoff/c03-triage-detection-validity-source-manifest.json'
OVERLAY = 'deploy/aisoc21/compose.triage-review-only-c03.yml'
DOCKERFILE = 'deploy/aisoc21/build/Dockerfile.agents-triage-review-only-c03'
OPERATOR = 'deploy/aisoc21/operate_triage_review_only_c03.py'
RUNTIME = (
    'services/agents/app/models/state.py',
    'services/agents/app/agents/auto_triage_agent.py',
    'services/agents/app/workers/fused_alert_consumer.py',
    'services/agents/app/investigator/ledger.py',
    'services/agents/app/workers/triage_admission.py',
)
NEW_RUNTIME = RUNTIME[-1]
NEW_TESTS = (
    'tests/porting/test_triage_review_only_profile_c03.py',
    'tests/porting/test_triage_review_only_ledger_c03.py',
)
DIRECT_TESTS = (
    'tests/porting/test_triage_recovery_3a.py',
    'tests/porting/test_triage_durability_3a.py',
    'tests/porting/test_triage_delivery_3a.py',
    'tests/porting/test_triage_budget_3a.py',
    'services/agents/tests/test_auto_triage_ledger_records_the_prompt.py',
    'services/agents/tests/test_auto_triage_dispositions.py',
)
SUPPORT = (
    'services/agents/pyproject.toml', 'services/agents/tests/conftest.py',
    'services/agents/app/llm/prompts.lock.json',
    'tests/porting/reference/connectors/app/main.py',
    'tests/porting/reference/connectors/app/api/router.py',
)
TABLES = ('alerts', 'investigation_runs', 'investigation_events',
          'investigation_artifacts', 'aisoc_run_costs', 'aisoc_shadow_mode',
          'aisoc_shadow_decisions', 'aisoc_business_context_rule_sets',
          'aisoc_context_statements', 'aisoc_tenant_skills',
          'aisoc_tenant_skill_versions', 'aisoc_replay_evaluations',
          'aisoc_kb_documents', 'aisoc_analyst_feedback')
EXTRA_TABLES = ('incidents', 'aisoc_cases', 'alert_source_links',
                'aisoc_closure_policies', 'aisoc_closure_qa_samples')
READERS = (('org-memory', 'alerts:read'), ('tenant-skill', 'settings:read'),
           ('kb-read', 'knowledge_base:read'), ('dispositions', 'alerts:read'),
           ('identity-read', 'graph:read'))
OFF = {'AISOC_AGENT_KAFKA_DISABLE': '1', 'AISOC_AGENT_ESCALATE_TO_GRAPH': '0',
       'AISOC_AGENT_MEMORY_WRITEBACK': '0', 'AISOC_AGENT_RAISE_APPROVALS': '0',
       'AISOC_AGENT_MEMORY_SUPPRESSION': '0', 'AISOC_PLAYBOOK_SWEEPER_DISABLE': '1',
       'AISOC_INVESTIGATION_REAPER_DISABLE': '1'}
ALERT_MATERIAL = (
    'SELECT id,row_to_json(x)::text AS material FROM (SELECT id,tenant_id,title,'
    "description,event_time AT TIME ZONE 'UTC' AS event_time_utc,raw_event,"
    'source_event_ids,external_id,dedup_hash,enrichment_data FROM alerts) x ORDER BY id'
)

# Source-bounded, copied/adapted observation snippets; provenance is in the manifest.
# No app imports: source hashes + frozen code audit establish behavior; this checks
# actual process inputs/UID and installed SDK metadata without invoking model code.
FILES_CODE = r'''import hashlib,json,os,sys
from pathlib import Path
args=json.load(sys.stdin); out={}
for path in args['paths']:
 p=Path(path);s=p.stat();out[path]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'dev':s.st_dev,'inode':s.st_ino,'mode':s.st_mode&511,'uid':s.st_uid,'gid':s.st_gid,'size':s.st_size}
print(json.dumps({'uid':os.getuid(),'files':out}))'''
SOURCE_CODE = r'''import hashlib,json
from pathlib import Path
print(json.dumps({'app':{str(p.relative_to('/app/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('/app/app').rglob('*.py'))},'lock':hashlib.sha256(Path('/app/app/llm/prompts.lock.json').read_bytes()).hexdigest() if Path('/app/app/llm/prompts.lock.json').exists() else None}))'''
METRICS_CODE = r'''import json,urllib.request
from prometheus_client.parser import text_string_to_metric_families
with urllib.request.urlopen('http://127.0.0.1:4000/metrics',timeout=15) as f:
 assert f.status==200
 value=f.read(4194305);assert len(value)<=4194304
counts={}
for family in text_string_to_metric_families(value.decode()):
 for sample in family.samples:
  if sample.name=='litellm_proxy_total_requests_metric_total' and sample.labels.get('status_code')=='200':
   model=sample.labels['requested_model'];counts[model]=counts.get(model,0)+sample.value
print(json.dumps(counts))'''
METADATA_CODE = r'''import asyncio,json,os,ssl,sys
from aiokafka import AIOKafkaConsumer,TopicPartition
rows=json.load(sys.stdin)
async def main():
 assert os.environ['KAFKA_SECURITY_PROTOCOL']=='SSL'
 context=ssl.create_default_context(cafile=os.environ['KAFKA_SSL_CAFILE'])
 assert context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED
 if os.getenv('KAFKA_SSL_CERTFILE'):context.load_cert_chain(os.environ['KAFKA_SSL_CERTFILE'],os.getenv('KAFKA_SSL_KEYFILE') or None)
 out={}
 for alias,row in rows.items():
  client=AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],group_id=row['group'],enable_auto_commit=False,security_protocol='SSL',ssl_context=context,request_timeout_ms=15000)
  await client.start()
  try:
   assert row['topic'] in await client.topics()  # Metadata-only existence check; never request auto-creation.
   await client._client.add_topic(row['topic'])
   parts=client.partitions_for_topic(row['topic']);assert parts is not None
   tps=[TopicPartition(row['topic'],p) for p in sorted(parts)]
   begin=await client.beginning_offsets(tps);end=await client.end_offsets(tps)
   projection={str(tp.partition):{'begin':begin[tp],'end':end[tp],'committed':await client.committed(tp) if row['group'] else None} for tp in tps}
   out[alias]={'topic':row['topic'],'group':row['group'],'partitions':projection,'physical_record_reads':0,'polls':0,'assigns':0,'commits':0}
  finally:await client.stop()
 print(json.dumps(out))
asyncio.run(main())'''


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
    path.chmod(0o600)


def copy_once(src, dst):
    with Path(src).open('rb') as source, Path(dst).open('xb') as target:
        shutil.copyfileobj(source, target)
    Path(dst).chmod(0o600)


def command(argv, *, payload=None, timeout=60):
    result = subprocess.run(argv, input=payload, text=True, capture_output=True, timeout=timeout)
    require(result.returncode == 0, 'command failed: ' + Path(argv[0]).name +
            '; stdout_sha256=' + hashlib.sha256(result.stdout.encode()).hexdigest() +
            '; stderr_sha256=' + hashlib.sha256(result.stderr.encode()).hexdigest())
    return result.stdout


def inspect(name):
    return json.loads(command(['docker', 'inspect', name]))[0]


def env(item):
    return dict(value.split('=', 1) for value in item['Config']['Env'])


def container_json(code, payload=None, name=AGENTS):
    value = command(['docker', 'exec', '-i', name, 'python', '-c', code],
                    payload=json.dumps(payload), timeout=180)
    return json.loads(value.strip().splitlines()[-1])


def pg(sql):
    # Existing administrator/local psql READ ONLY observation; no SET ROLE/tenant GUC.
    # Cross-tenant preservation evidence only, not app-role/RLS/TLS qualification.
    directory = E / 'sql-events'
    directory.mkdir(mode=0o700, exist_ok=True)
    slots = len(list(directory.glob('*-started.json')))
    require(slots < 96, 'recovery PG cap 96 exhausted; prior4 + recovery <=100')
    save(directory / (f'{slots:03d}-started.json'), {'read_only_transaction': True,
                                                 'sql_sha256': hashlib.sha256(sql.encode()).hexdigest()})
    admin = env(inspect('spirithub-postgres-1'))['POSTGRES_USER']
    result = command(['docker', 'exec', '-i', 'spirithub-postgres-1', 'psql',
                      '-X', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1',
                      '-U', admin, '-d', 'aisoc'],
                     payload='BEGIN READ ONLY;\n' + sql + '\nROLLBACK;')
    value = json.loads(result.strip())
    save(directory / (f'{slots:03d}-finished.json'), {'read_only_transaction_completed': True})
    return value


def lit(value):
    return "'" + str(value).replace("'", "''") + "'"


def row_hashes(table, legacy=False):
    query = ALERT_MATERIAL if table == 'alerts' and legacy else (
        'SELECT row_to_json(t)::text AS material FROM ' + table + ' t ORDER BY row_to_json(t)::text')
    rows = pg("SELECT COALESCE(json_agg(x),'[]'::json) FROM (" + query + ') x;')
    return sorted(hashlib.sha256(row['material'].encode()).hexdigest() for row in rows)


def table_projection(table):
    exists = pg('SELECT to_json(to_regclass(' + lit('public.' + table) + ') IS NOT NULL);')
    return {'exists': exists, 'row_sha256': row_hashes(table) if exists else []}


def readers():
    result = {}
    for stem, scope in READERS:
        state_path = R / ('private/app-' + stem + '-3a.json')
        keys_path = R / ('private/' + stem + '-3a/keys.json')
        state_value = read(state_path)
        metadata = {}
        for alias in ('reader_a', 'reader_b'):
            identity = state_value['identities'][alias]
            uuid.UUID(identity['key_id'])
            value = pg('SELECT row_to_json(t) FROM (SELECT id,tenant_id,is_active,scopes,expires_at '
                       'FROM api_keys WHERE id=' + lit(identity['key_id']) + ') t;')
            require(value['is_active'] and value['tenant_id'] == identity['tenant_id'] and
                    value['scopes'] == [scope], 'reader metadata mismatch')
            metadata[alias] = value
        result[stem] = {'state_sha256': sha(state_path), 'keys_sha256': sha(keys_path), 'metadata': metadata}
    return result


def environment():
    ids = command(['docker', 'ps', '-aq']).split()
    full = json.loads(command(['docker', 'inspect', *ids]))
    projection = {}
    for item in full:
        projection[item['Name'].lstrip('/')] = {
            'id': item['Id'], 'image': item['Image'], 'started_at': item['State']['StartedAt'],
            'status': item['State']['Status'], 'restart_count': item['RestartCount'],
            'mounts': item['Mounts'],
        }
    return full, {'containers': projection, 'volumes': sorted(command(['docker', 'volume', 'ls', '-q']).split())}


def off_flags(item):
    values = env(item)
    require(all(values.get(name) == value for name, value in OFF.items()), 'worker/effects flag mismatch')
    require(values.get('AISOC_ALERT_PLAYBOOKS_ENABLED', '').lower() not in ('1', 'true', 'yes', 'on'), 'playbook effects enabled')
    require(values.get('AISOC_ALERT_PLAYBOOKS_LIVE', '').lower() not in ('1', 'true', 'yes', 'on'), 'live playbooks enabled')


def host_files(item):
    result = {}
    for mount in item['Mounts']:
        require(mount['Type'] == 'bind' and mount['RW'] is False, 'non-RO bind')
        source = Path(mount['Source'])
        require(not source.is_symlink(), 'symlink bind source unsupported')
        paths = [source] if source.is_file() else sorted(path for path in source.rglob('*') if path.is_file())
        require(paths, 'empty or missing host bind')
        for path in paths:
            require(not path.is_symlink(), 'symlink bind input unsupported')
            value = path.stat()
            result[str(path)] = {'sha256': sha(path), 'dev': value.st_dev, 'inode': value.st_ino,
                                 'mode': stat.S_IMODE(value.st_mode), 'uid': value.st_uid,
                                 'gid': value.st_gid, 'size': value.st_size}
    result[str(R / 'private/agents-1g.env')] = {'sha256': sha(R / 'private/agents-1g.env')}
    return result


def bind_files(item):
    paths = []
    for mount in item['Mounts']:
        source, destination = Path(mount['Source']), Path(mount['Destination'])
        files = [source] if source.is_file() else sorted(p for p in source.rglob('*') if p.is_file())
        paths.extend(str(destination if source.is_file() else destination / path.relative_to(source)) for path in files)
    return container_json(FILES_CODE, {'paths': paths})


def policy_match(host, actual, item):
    source = R / 'private/triage-budget-3a/policy.json'
    destination = '/run/secrets/triage-budget/policy.json'
    require(host[str(source)] == {k: actual['files'][destination][k] for k in host[str(source)]},
            'recreated container policy is not current host policy inode/bytes')
    require(env(item)['AISOC_TRIAGE_BUDGET_POLICY_FILE'] == destination, 'policy path drift')


def source_map():
    return {str(path.relative_to(S)): sha(path) for service in ('api', 'fusion', 'agents', 'actions')
            for path in sorted((S / 'services' / service / 'app').rglob('*.py'))}


def no_candidate_tag():
    tags = command(['docker', 'image', 'ls', '--format', '{{.Repository}}:{{.Tag}}']).splitlines()
    require(TAG not in tags, 'candidate tag already exists; do not overwrite an unknown previous build')


def parent_index_projection(bindings, staged=False):
    index = read(S / 'docs/handoff/handoff-manifest.json')
    require(len(index['new_documents']) == 573 and len(index['current_source_layers']) == 24,
            'parent index counts drift')
    stage = {**bindings['document_sha256'], **bindings['runtime_source_sha256'],
             **bindings['new_test_sha256']} if staged else {}
    actual = {}
    for row in index['new_documents']:
        path = row['path']
        require(not Path(path).is_absolute() and '..' not in Path(path).parts and not path.startswith('.local/'),
                'unsafe parent public index path')
        actual[path] = sha(S / path)
        require(actual[path] == stage.get(path, row['sha256']), 'parent indexed public input changed outside stage')
    return {'parent_handoff_sha256': bindings['parent_handoff_sha256'],
            'indexed_files': len(actual), 'actual_file_sha256': actual,
            'stage_allowed_paths': sorted(stage)}


def runtime_map():
    result, locks = {}, {}
    for service in ('api', 'fusion', 'agents', 'actions'):
        value = container_json(SOURCE_CODE, name='socai2-' + service + '-1')
        result.update({'services/' + service + '/app/' + name: checksum for name, checksum in value['app'].items()})
        if value['lock'] is not None:
            locks['services/' + service + '/app/llm/prompts.lock.json'] = value['lock']
    return result, locks


def compose(bindings, include_new=False):
    argv = ['docker', 'compose', '--project-directory', str(R)]
    for path in bindings['parent_compose_order']:
        argv.extend(['-f', str(S / path)])
    if include_new:
        argv.extend(['-f', str(S / OVERLAY)])
    return argv


def input_map(bindings):
    return {path: sha(S / path) for path in (*NEW_TESTS, *DIRECT_TESTS, *SUPPORT)}


def expected_sources(bindings):
    return {**bindings['parent_runtime_source_sha256'], **bindings['runtime_source_sha256']}


def gate(path, phase, bindings, image):
    value = read(path)
    require(value.get('accepted') is True and value.get('batch') == BATCH and value.get('phase') == phase,
            'independent audit not accepted for phase')
    require(value.get('operator_sha256') == sha(__file__) and value.get('bindings_sha256') == sha(bindings['_path']), 'audit operator/bindings mismatch')
    require(value.get('runtime_source_sha256') == expected_sources(bindings) and
            value.get('test_input_sha256') == input_map(bindings) and value.get('image_id') == image,
            'audit source/test/image mismatch')
    checkpoints = ('prepare', 'stage', 'test', 'build') + (('deploy', 'verify') if phase == 'postdeploy' else ())
    for name in checkpoints:
        require(value.get(name + '_completed_sha256') == sha(E / name / 'completed.json'), 'audit checkpoint mismatch')
    require(value.get('scope_sha256') == bindings['scope_sha256'], 'audit scope mismatch')
    return value


def metrics(which):
    directory = E / 'http-events'
    directory.mkdir(mode=0o700, exist_ok=True)
    require(len(list(directory.glob('*-started.json'))) < 2, 'HTTP cap 2 exhausted')
    start = directory / (which + '-started.json')
    save(start, {'batch': BATCH, 'purpose': 'gateway metrics only', 'method': 'GET',
                 'path': '/metrics', 'actual_attempt_reserved': True, 'real_model': False,
                 'started_at': datetime.now(timezone.utc).isoformat()})
    value = container_json(METRICS_CODE, name='socai2-litellm-1')
    save(directory / (which + '-finished.json'), {'started_sha256': sha(start), 'confirmed_status': 200,
                                                 'gateway_success_counts': value})
    return value


def observation(bindings, which):
    full, projected = environment()
    agent = next(item for item in full if item['Name'] == '/' + AGENTS)
    off_flags(agent)
    require(len(projected['containers']) == 36 and len(projected['volumes']) == 18, 'environment size drift')
    require(len(agent['Mounts']) == 7 and agent['Config']['StopTimeout'] == 60, 'bind/stop contract drift')
    require(agent['Config']['User'] in ('10001', '10001:10001'), 'unexpected UID configuration')
    budget = pg("SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT * FROM socai2_triage_budget_reservations ORDER BY run_id) t;")
    require(len(budget) == 12 and sum(row['charged_tokens'] for row in budget) == 240000 and
            sum(row['settled_at'] is None for row in budget) == 3, 'old budget/unknown counts drift')
    result = {'environment': projected,
              'materials': {table: row_hashes(table, legacy=True) for table in TABLES},
              'full_alert_rows': row_hashes('alerts'),
              'extra_tables': {table: table_projection(table) for table in EXTRA_TABLES},
              'budget': budget, 'readers': readers(), 'migrations': pg('SELECT count(*) FROM aisoc_schema_migrations;'),
              'migration_row_sha256': row_hashes('aisoc_schema_migrations'),
              'host_bind_files': host_files(agent), 'container_bind_files': bind_files(agent),
              'broker_metadata': container_json(METADATA_CODE, bindings['broker_metadata_selectors']),
              'gateway': metrics(which)}
    require(result['migrations'] == 134, 'migration count drift')
    require(result['container_bind_files']['uid'] == 10001, 'running UID mismatch')
    require(sha(R / 'private/triage-budget-3a/policy.json') == bindings['host_policy_sha256'], 'host policy drift')
    return result, full, agent


def original_failed_attempt(bindings, initial=False):
    recovery = bindings['observer_recovery']
    actual = {}
    for path in sorted(ORIGINAL_E.rglob('*')):
        if path == E or E in path.parents:
            continue
        require(not path.is_symlink(), 'original failed evidence symlink')
        if path.is_file():
            actual[str(path.relative_to(ORIGINAL_E))] = sha(path)
    require(actual == recovery['original_tree_sha256'] and len(actual) == 13,
            'original failed13-file tree changed; do not reuse or overwrite')
    require(not (ORIGINAL_E / 'prepare/completed.json').exists(), 'original prepare unexpectedly completed')
    for phase in ('stage', 'test', 'build', 'deploy', 'verify', 'finish'):
        require(not (ORIGINAL_E / phase).exists(), 'original downstream phase unexpectedly exists')
    failure = read(ORIGINAL_E / 'prepare/failure.json')
    require(failure['type'] == 'RuntimeError' and failure['phase'] == 'prepare' and
            failure['message_sha256'] == '117e56adc3c6715ce1cc5f65c5e32da994a7124d780d1e90672b1aa26db48271',
            'original failure is not the frozen budget observation guard')
    diagnosis_path = P / 'observation-recovery-diagnosis.json'
    require(sha(diagnosis_path) == recovery['diagnosis_sha256'], 'original diagnosis bytes mismatch')
    diagnosis = read(diagnosis_path)
    require(diagnosis['original_tree_sha256'] == actual and
            diagnosis['aggregate_read_only_PG_attempts_so_far'] == 4 and
            diagnosis['remaining_R01_PG_cap'] == 96, 'diagnosis/failure/cap binding mismatch')
    scope_bytes = recovery['scope_markdown'].encode()
    require(hashlib.sha256(scope_bytes).hexdigest() == recovery['scope_sha256'], 'recovery scope text/hash mismatch')
    if initial:
        for name in ('parent-inspect.json', 'parent-render.json', 'agents-rollback.json',
                     'candidate-render.json', 'candidate-inspect.json', 'build-context', 'test-results'):
            require(not (P / name).exists(), 'private downstream artifact already exists')
        require(source_map() == bindings['parent_runtime_source_sha256'] and len(source_map()) == 769,
                'parent769 source changed before observer recovery')
        require(inspect(AGENTS)['Image'] == BASE_IMAGE, 'parent9cb runtime changed before observer recovery')
        copy_once(diagnosis_path, E / 'observer-diagnosis.json')
        with (E / 'observation-recovery-scope-before.md').open('xb') as stream:
            stream.write(scope_bytes)
        (E / 'observation-recovery-scope-before.md').chmod(0o600)
        save(E / 'original-failure-preservation.json',
             {'original_tree_sha256': actual, 'diagnosis_sha256': recovery['diagnosis_sha256'],
              'recovery_scope_sha256': recovery['scope_sha256'], 'historical_PG_attempts': 4,
              'remaining_readonly_PG_cap': 96, 'original_failed_phase_reused': False,
              'operator_observer_error_not_upstream_budget_repair': True})
    return {'original_tree_sha256': actual, 'diagnosis_sha256': recovery['diagnosis_sha256'],
            'recovery_scope_sha256': recovery['scope_sha256'], 'historical_PG_attempts': 4,
            'remaining_readonly_PG_cap': 96}


def phase_prepare(bindings):
    original_failed_attempt(bindings, initial=True)
    copy_once(__file__, E / 'operator-source.py')
    copy_once(bindings['_path'], E / 'execution-bindings.json')
    no_candidate_tag()
    for path in (NEW_RUNTIME, *NEW_TESTS, OVERLAY, DOCKERFILE, bindings['scope_path'], OPERATOR):
        require(not (S / path).exists(), 'new input reached source before prepare')
    require(source_map() == bindings['parent_runtime_source_sha256'], 'parent source tree drift before snapshot')
    for path, checksum in bindings['parent_compose_sha256'].items():
        require(sha(S / path) == checksum, 'parent compose byte drift')
    require(sha(S / MANIFEST) == bindings['parent_source_manifest_sha256'], 'parent source manifest drift')
    require(sha(S / 'docs/handoff/handoff-manifest.json') == bindings['parent_handoff_sha256'], 'parent index drift')
    save(E / 'parent-index-before.json', parent_index_projection(bindings))
    for path, checksum in bindings['parent_public_sha256'].items():
        require(sha(S / path) == checksum, 'parent public receipt byte drift')
    parent = {}
    for name, checksum in bindings['parent_evidence_sha256'].items():
        path = PARENT_E / name
        require(sha(path) == checksum, 'parent gate hash mismatch')
        parent[name] = read(path)
    require(parent['acceptance.json']['four_case_model_quality_accepted'] is False and
            parent['acceptance.json']['resident_worker_enabled'] is False and
            parent['acceptance.json']['bounded_closeout_accepted'] is True, 'parent closeout/quality status drift')
    for name in ('finish-independent-audit.json', 'closeout-independent-audit.json', 'sealed-independent-audit.json'):
        require(parent[name]['accepted'] is True, 'parent independent gate not accepted')
    for name, checksum in bindings['parent_delivery_sha256'].items():
        path = PAYLOAD / name
        require(sha(path) == checksum, 'parent delivered evidence mismatch')
        copy_once(path, E / 'prepare' / name)
    require(read(PAYLOAD / 'parent-delivery-independent-audit.json')['accepted'] is True, 'parent delivery audit not accepted')
    for path, checksum in bindings['parent_document_sha256'].items():
        require(sha(S / path) == checksum, 'parent document byte drift')
    scope = PAYLOAD / bindings['scope_path']
    require(sha(scope) == bindings['scope_sha256'], 'payload scope hash mismatch')
    copy_once(scope, E / 'scope-before.md')
    require(sha(PAYLOAD / bindings['adoption_path']) == bindings['adoption_sha256'], 'root adoption hash mismatch')
    adoption = read(PAYLOAD / bindings['adoption_path'])
    require(adoption.get('accepted_scope_and_source_adopted') is True and
            adoption.get('source_manifest_sha256') == bindings['source_candidate_manifest_sha256'] and
            adoption.get('scope_manifest_sha256') == bindings['scope_candidate_manifest_sha256'] and
            adoption.get('files_sha256') == {**bindings['document_sha256'], **bindings['runtime_source_sha256'],
                                           **bindings['new_test_sha256']}, 'root adoption does not bind exact scope/source/tests')
    copy_once(PAYLOAD / bindings['adoption_path'], E / 'scope-adoption.json')
    review = PAYLOAD / bindings['source_review_path']
    require(sha(review) == bindings['source_review_sha256'], 'source review hash mismatch')
    reviewed = read(review)
    require(reviewed.get('accepted') is True and reviewed.get('source_manifest_sha256') == bindings['source_candidate_manifest_sha256'] and
            reviewed.get('scope_manifest_sha256') == bindings['scope_candidate_manifest_sha256'], 'source review not accepted for exact candidates')
    copy_once(review, E / 'source-independent-audit.json')
    operator_review = PAYLOAD / bindings['operator_review_path']
    require(sha(operator_review) == bindings['operator_review_sha256'], 'operator review hash mismatch')
    approved = read(operator_review)
    require(approved.get('accepted') is True and approved.get('operator_sha256') == sha(__file__) and
            approved.get('source_candidate_manifest_sha256') == bindings['source_candidate_manifest_sha256'] and
            approved.get('scope_candidate_manifest_sha256') == bindings['scope_candidate_manifest_sha256'],
            'operator independent review missing exact source/scope/operator binding')
    copy_once(operator_review, E / 'operator-independent-audit.json')
    before, full, agent = observation(bindings, 'before')
    require(agent['Image'] == BASE_IMAGE, 'parent image mismatch')
    parent_observation = parent['finish-after.json']['protected']['observation']
    for key in ('budget', 'readers', 'migrations', 'gateway'):
        require(before[key] == parent_observation[key], 'parent protected observation drift: ' + key)
    require(all(Counter(before['materials'][table]) == Counter(parent_observation['materials'][table])
                for table in TABLES), 'parent material projection changed')
    require(before['broker_metadata'] == bindings['parent_broker_metadata'], 'parent broker metadata drift')
    require(before['environment'] == bindings['parent_environment'], 'parent container/volume state drift')
    actual_source, locks = runtime_map()
    require(actual_source == bindings['parent_runtime_source_sha256'] and len(actual_source) == 769, 'parent runtime source drift')
    require(locks['services/agents/app/llm/prompts.lock.json'] == bindings['prompt_lock_sha256'], 'parent prompt lock drift')
    save(P / 'parent-inspect.json', full)
    rendered = json.loads(command(compose(bindings) + ['config', '--format', 'json']))
    save(P / 'parent-render.json', rendered)
    require(rendered['services']['agents']['image'] == BASE_TAG, 'rendered parent tag drift')
    rollback = {'command_for_separate_explicit_review_only': compose(bindings) +
                ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--force-recreate', 'agents'],
                'parent_full_render_private': str(P / 'parent-render.json'),
                'parent_full_render_sha256': sha(P / 'parent-render.json'),
                'parent_inspect_private': str(P / 'parent-inspect.json'),
                'runtime_image': BASE_IMAGE, 'worker_and_effects_must_remain_OFF': True,
                'does_not_restore_pre_atomic_replace_policy_inode': True,
                'separate_approval_and_readonly_reconciliation_required': True,
                'automatic_rollback_authorized': False}
    save(P / 'agents-rollback.json', rollback)
    for path in RUNTIME[:-1]:
        destination = E / 'parent-sources' / path
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        copy_once(S / path, destination)
    for path in bindings['parent_document_sha256']:
        destination = E / 'parent-sources' / path
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        copy_once(S / path, destination)
    # The parent may retain pre-atomic-replace policy bytes/inode. Record both;
    # only the freshly recreated candidate is required to match the host policy.
    save(E / 'before.json', before)
    return {'before_sha256': sha(E / 'before.json'), 'parent_source_count': 769,
            'host_and_parent_container_policy_are_separately_recorded': True,
            'parent_policy_inode_match_required': False, 'private_rollback_saved': True,
            'broker_physical_record_reads': 0, 'broker_assigns_polls_commits': 0, 'real_models': 0}


def phase_stage(bindings):
    require(source_map() == bindings['parent_runtime_source_sha256'], 'source changed after prepare')
    for path, checksum in bindings['parent_document_sha256'].items():
        require(sha(S / path) == checksum, 'parent document changed after prepare')
    paths = {**bindings['runtime_source_sha256'], **bindings['new_test_sha256'], **bindings['document_sha256'],
             OVERLAY: bindings['overlay_sha256'], DOCKERFILE: bindings['dockerfile_sha256']}
    require(set(paths) == set((*RUNTIME, *NEW_TESTS, *bindings['document_sha256'], OVERLAY, DOCKERFILE)), 'stage path set mismatch')
    for path, checksum in paths.items():
        require(sha(PAYLOAD / path) == checksum, 'payload byte mismatch')
        require(not (S / path).is_symlink(), 'stage destination symlink')
        if path not in RUNTIME[:-1] and path not in bindings['parent_document_sha256']:
            require(not (S / path).exists(), 'new input already exists')
    for path, checksum in paths.items():
        target = S / path
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + '.c03-r01-stage')
        copy_once(PAYLOAD / path, temporary)
        temporary.chmod(0o644)
        os.replace(temporary, target)
        require(sha(target) == checksum, 'staged byte mismatch')
    require(source_map() == expected_sources(bindings), 'staged runtime map mismatch')
    require(sha(S / 'docs/handoff/handoff-manifest.json') == bindings['parent_handoff_sha256'], 'stage changed old handoff index')
    parent_render = read(P / 'parent-render.json')
    expected_render = json.loads(json.dumps(parent_render))
    expected_render['services']['agents']['image'] = TAG
    expected_render['services']['agents']['environment'][PROFILE_ENV] = PROFILE
    rendered = json.loads(command(compose(bindings, True) + ['config', '--format', 'json']))
    require(rendered == expected_render, 'compose changes more than Agents image/profile')
    save(P / 'candidate-render.json', rendered)
    return {'staged_sha256': paths, 'source_count': len(source_map()),
            'rendered_parent_sha256': sha(P / 'parent-render.json'),
            'rendered_candidate_sha256': sha(P / 'candidate-render.json'),
            'render_changes': ['services.agents.image', 'services.agents.environment.' + PROFILE_ENV],
            'no_runtime_recreated': True}


def summary(log):
    status = r'(?:passed|failed|errors?|skipped|deselected|xfailed|xpassed|warnings?)'
    pattern = re.compile(r'^\s*(?:=+\s*)?(\d+ ' + status + r'(?:,\s*\d+ ' + status +
                         r')*)\s+in\s+\d+(?:\.\d+)?s(?:\s+\([^\r\n]*\))?\s*(?:=+\s*)?$')
    found = [match for line in log.splitlines() if (match := pattern.fullmatch(line))]
    require(found, 'pytest final summary missing')
    return {name: int(count) for count, name in re.findall(r'(\d+)\s+(' + status + ')', found[-1][1])}


def junit_projection(path):
    root = ET.fromstring(Path(path).read_bytes())
    rows = []
    for node in root.iter('testcase'):
        outcome = next((name for name in ('failure', 'error', 'skipped') if node.find(name) is not None), 'passed')
        rows.append({'file': node.get('file'), 'classname': node.get('classname'),
                     'name': node.get('name'), 'outcome': outcome})
    new_files = {}
    for test in NEW_TESTS:
        subset = [row for row in rows if row['file'] and row['file'].endswith(test)]
        new_files[test] = {'collected': len(subset), 'outcomes': dict(Counter(row['outcome'] for row in subset))}
    return {'collected': len(rows), 'outcomes': dict(Counter(row['outcome'] for row in rows)),
            'new_files': new_files, 'testcases': rows}


def phase_test(bindings):
    require(source_map() == expected_sources(bindings), 'test source changed')
    require(inspect(TEST_TAG)['Id'] == TEST_IMAGE, 'cached test image drift')
    before_inputs = input_map(bindings)
    require(before_inputs == {**bindings['parent_test_input_sha256'], **bindings['new_test_sha256']}, 'test inputs differ')
    name = 'socai2-c03-r01-unit-' + uuid.uuid4().hex[:12]
    results = P / 'test-results'
    results.mkdir(mode=0o700)
    os.chown(results, 10001, 10001)
    argv = ['docker', 'run', '--rm', '--pull', 'never', '--name', name, '--network', 'none',
            '--user', '10001:10001', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true']
    variables = {'PYTHONDONTWRITEBYTECODE': '1', 'ENVIRONMENT': 'production',
                 'AISOC_DEV_AUTH_BYPASS': 'false', 'DATABASE_DSN': '', 'DATABASE_URL': '',
                 'OPENAI_API_KEY': '', 'LLM_API_KEY': '', 'LITELLM_MASTER_KEY': '',
                 'KAFKA_BOOTSTRAP_SERVERS': '127.0.0.1:1', 'REDIS_URL': 'redis://127.0.0.1:1/0',
                 'OTEL_SDK_DISABLED': 'true', 'PYTHONPATH': '/source/services/agents'}
    for key, value in variables.items():
        argv.extend(['-e', key + '=' + value])
    argv.extend(['-v', str(S) + ':/source:ro', '-v', str(S / 'tests/porting/reference/connectors') +
                 ':/source/services/connectors:ro', '-v', str(results) + ':/results:rw',
                 '-w', '/source/services/agents', TEST_IMAGE,
                 'python', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--asyncio-mode=auto', '--tb=short',
                 '-o', 'junit_family=xunit1', '--junitxml=/results/junit.xml'])
    argv.extend('/source/' + path for path in (*NEW_TESTS, *DIRECT_TESTS))
    save(E / 'test' / 'inputs.json', {'image_id': TEST_IMAGE, 'source_sha256': source_map(),
                                     'test_input_sha256': before_inputs, 'network': 'none', 'real_models': 0})
    timed_out = False
    with (E / 'test' / 'pytest.log').open('x') as log:
        process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, text=True)
        try:
            exit_code = process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            timed_out = True
            cleanup = subprocess.run(['docker', 'rm', '-f', name], text=True, capture_output=True, timeout=30)
            process.kill()
            process.wait(timeout=30)
            exit_code = 124
            save(E / 'test' / 'timeout.json', {'named_container': name, 'cleanup_exit': cleanup.returncode,
                                              'only_this_container_removed': True})
    try:
        final_summary = summary((E / 'test' / 'pytest.log').read_text(errors='replace'))
    except RuntimeError:
        final_summary = None
    junit, junit_error = None, None
    if (results / 'junit.xml').is_file():
        copy_once(results / 'junit.xml', E / 'test' / 'junit.xml')
        try:
            junit = junit_projection(results / 'junit.xml')
        except (ET.ParseError, ValueError) as exc:
            junit_error = type(exc).__name__
    result = {'exit_code': exit_code, 'timed_out': timed_out, 'log_sha256': sha(E / 'test' / 'pytest.log'),
              'summary': final_summary, 'image_id': TEST_IMAGE,
              'source_sha256': source_map(), 'test_input_sha256': input_map(bindings),
              'junit': junit, 'junit_parse_error_type': junit_error}
    save(E / 'test' / 'result.json', result)
    require(result['source_sha256'] == expected_sources(bindings) and result['test_input_sha256'] == before_inputs,
            'test input changed during attempt')
    require(exit_code == 0 and not timed_out and result['summary'] is not None and result['summary'].get('failed', 0) == 0 and
            result['summary'].get('error', 0) == result['summary'].get('errors', 0) == 0 and
            result['summary'].get('passed', 0) > 0, 'offline tests failed; preserve attempt')
    require(junit is not None and all(row['collected'] > 0 and set(row['outcomes']) == {'passed'}
                                     for row in junit['new_files'].values()), 'new profile tests missing/skipped/not passed')
    return result


def phase_build(bindings):
    require(source_map() == expected_sources(bindings), 'build source mismatch')
    require(inspect(BASE_TAG)['Id'] == BASE_IMAGE, 'base tag changed')
    no_candidate_tag()
    require(read(E / 'test' / 'completed.json')['result']['exit_code'] == 0, 'test checkpoint missing')
    context = P / 'build-context'
    context.mkdir(mode=0o700)
    for path in RUNTIME:
        destination = context / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        copy_once(S / path, destination)
        require(sha(destination) == bindings['runtime_source_sha256'][path], 'build context mismatch')
    copy_once(S / DOCKERFILE, context / 'Dockerfile')
    require(sha(context / 'Dockerfile') == bindings['dockerfile_sha256'], 'Dockerfile mismatch')
    with (E / 'build' / 'build.log').open('x') as log:
        process = subprocess.run(['docker', 'build', '--network', 'none', '--pull=false',
                                  '-t', TAG, '-f', str(context / 'Dockerfile'), str(context)],
                                 stdout=log, stderr=subprocess.STDOUT, timeout=300)
    save(E / 'build' / 'exit.json', {'exit_code': process.returncode, 'log_sha256': sha(E / 'build' / 'build.log')})
    require(process.returncode == 0 and inspect(BASE_TAG)['Id'] == BASE_IMAGE, 'build failed or base tag changed')
    image = inspect(TAG)['Id']
    require(image != BASE_IMAGE, 'candidate image equals parent')
    probe_name = 'socai2-c03-r01-baked-' + uuid.uuid4().hex[:12]
    try:
        baked = json.loads(command(['docker', 'run', '--rm', '--pull', 'never', '--name', probe_name,
                                    '--network', 'none', '--read-only', '--user', '10001:10001',
                                    '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true',
                                    '-e', 'PYTHONDONTWRITEBYTECODE=1', '--entrypoint', 'python',
                                    image, '-c', SOURCE_CODE], timeout=60).strip().splitlines()[-1])
    except BaseException:
        cleanup = subprocess.run(['docker', 'rm', '-f', probe_name], text=True, capture_output=True, timeout=30)
        save(E / 'build' / 'baked-check-failure-cleanup.json', {'only_named_container': probe_name,
                                                             'cleanup_exit': cleanup.returncode})
        raise
    expected_agents = {path.removeprefix('services/agents/app/'): value for path, value in expected_sources(bindings).items()
                       if path.startswith('services/agents/app/')}
    require(baked['app'] == expected_agents and len(baked['app']) == 185 and
            baked['lock'] == bindings['prompt_lock_sha256'], 'baked source or lock differs')
    save(E / 'build' / 'baked-source.json', {'image_id': image, 'source_sha256': baked,
                                          'network': 'none', 'app_imports': 0, 'real_models': 0})
    result = {'image_id': image, 'base_image_id': BASE_IMAGE, 'runtime_source_sha256': expected_sources(bindings),
              'dockerfile_sha256': bindings['dockerfile_sha256'], 'baked_source_sha256': sha(E / 'build' / 'baked-source.json'),
              'max_builds': 1, 'dependency_changes': False}
    save(E / 'built-image.json', result)
    return result


def normalized_hostconfig(value):
    out = json.loads(json.dumps(value))
    if out.get('Binds') is not None:
        out['Binds'] = sorted(out['Binds'])
    return out


def same_parent_container(old, current):
    # Healthcheck logs and process runtime counters evolve without a recreate.
    keys = ('Id', 'Image', 'Config', 'HostConfig', 'Mounts', 'RestartCount')
    require(all(current[key] == old[key] for key in keys), 'parent container definition changed')
    require(current['State']['StartedAt'] == old['State']['StartedAt'] and
            current['State']['Status'] == old['State']['Status'] == 'running', 'parent lifecycle changed')


def agent_transition(old, current, image):
    old_env, actual_env = env(old), env(current)
    expected = {**old_env, PROFILE_ENV: PROFILE}
    require(actual_env == expected and current['Image'] == image, 'actual image/env transition mismatch')
    require(current['Mounts'] == old['Mounts'], 'mount contract changed')
    require(normalized_hostconfig(current['HostConfig']) == normalized_hostconfig(old['HostConfig']), 'HostConfig changed')
    allowed = {'Image', 'Env', 'Labels', 'Hostname'}
    require({k: v for k, v in old['Config'].items() if k not in allowed} ==
            {k: v for k, v in current['Config'].items() if k not in allowed}, 'other Config changed')
    require(current['Config']['Image'] == TAG, 'container tag differs')
    require(current['RestartCount'] == 0, 'candidate restarted unexpectedly')
    off_flags(current)


def phase_deploy(bindings):
    built = read(E / 'built-image.json')
    gate(E / 'predeploy-independent-audit.json', 'predeploy', bindings, built['image_id'])
    require(inspect(TAG)['Id'] == built['image_id'] and source_map() == expected_sources(bindings), 'candidate drift')
    old = next(row for row in read(P / 'parent-inspect.json') if row['Name'] == '/' + AGENTS)
    same_parent_container(old, inspect(AGENTS))
    desired = json.loads(command(compose(bindings, True) + ['config', '--format', 'json']))
    require(desired == read(P / 'candidate-render.json'), 'render changed after review')
    with (E / 'deploy' / 'compose.log').open('x') as log:
        process = subprocess.run(compose(bindings, True) + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--force-recreate', 'agents'],
                                 stdout=log, stderr=subprocess.STDOUT, timeout=180)
    save(E / 'deploy' / 'exit.json', {'exit_code': process.returncode, 'log_sha256': sha(E / 'deploy' / 'compose.log')})
    require(process.returncode == 0, 'compose exited nonzero; retain checkpoint, no second up')
    current = inspect(AGENTS)
    for _ in range(60):
        if current['State'].get('Health', {}).get('Status') == 'healthy':
            break
        require(current['State']['Running'], 'candidate not running')
        time.sleep(1)
        current = inspect(AGENTS)
    require(current['State'].get('Health', {}).get('Status') == 'healthy', 'candidate not healthy')
    agent_transition(old, current, built['image_id'])
    policy_match(host_files(current), bind_files(current), current)
    save(P / 'candidate-inspect.json', current)
    return {'image_id': built['image_id'], 'container_id': current['Id'], 'healthy': True,
            'agents_recreates': 1, 'profile': PROFILE, 'worker_and_selected_deployment_flags_off': True,
            'effects_blocked_by_review_profile': True,
            'siem_writeback_env_explicit_value': env(current).get('AISOC_SIEM_WRITEBACK_ENABLED'),
            'siem_default_is_on_but_selected_profile_forbids_call': True,
            'new_policy_inode_and_bytes_match_host': True, 'no_auto_rollback': True}


def phase_verify(bindings):
    before = read(E / 'before.json')
    after, _, current = observation(bindings, 'after')
    save(E / 'after.json', after)
    built = read(E / 'built-image.json')
    old = next(row for row in read(P / 'parent-inspect.json') if row['Name'] == '/' + AGENTS)
    agent_transition(old, current, built['image_id'])
    require(current['Id'] == read(E / 'deploy' / 'completed.json')['result']['container_id'], 'additional recreate')
    require(current['State']['StartedAt'] == read(P / 'candidate-inspect.json')['State']['StartedAt'], 'candidate process restarted')
    require(before['environment']['volumes'] == after['environment']['volumes'], 'volumes changed')
    for name, value in before['environment']['containers'].items():
        if name != AGENTS:
            require(after['environment']['containers'][name] == value, 'other container changed')
    for key in ('materials', 'full_alert_rows', 'extra_tables', 'budget', 'readers', 'migrations',
                'migration_row_sha256', 'host_bind_files', 'broker_metadata', 'gateway'):
        require(after[key] == before[key], 'protected observation changed: ' + key)
    policy_match(after['host_bind_files'], after['container_bind_files'], current)
    policy_path = '/run/secrets/triage-budget/policy.json'
    require({k: v for k, v in after['container_bind_files']['files'].items() if k != policy_path} ==
            {k: v for k, v in before['container_bind_files']['files'].items() if k != policy_path}, 'other bind bytes/stat changed')
    actual, locks = runtime_map()
    require(actual == source_map() == expected_sources(bindings) and len(actual) == 770, 'candidate runtime map mismatch')
    require(sum(path.startswith('services/agents/') for path in actual) == 185, 'Agents source count mismatch')
    require(locks['services/agents/app/llm/prompts.lock.json'] == bindings['prompt_lock_sha256'], 'prompt lock changed')
    require(len(bindings['parent_compose_sha256']) == 27, 'parent compose count mismatch')
    require(sha(S / 'docs/handoff/handoff-manifest.json') == bindings['parent_handoff_sha256'], 'handoff rewritten before finalizer')
    save(E / 'parent-index-after.json', parent_index_projection(bindings, staged=True))
    return {'image_id': built['image_id'], 'after_sha256': sha(E / 'after.json'), 'runtime_source_sha256': actual,
            'agents_python': 185, 'runtime_python': 770, 'non_python_prompt_lock_sha256': bindings['prompt_lock_sha256'],
            'effective_compose_layers': 28, 'planned_source_layers': 25, 'public_source_index_updated': False,
            'real_models': 0, 'business_writes': 0, 'HTTP_metrics_attempts': 2,
            'metadata_only_broker': True, 'resident_worker_enabled': False, 'quality_retested': False}


def phase_finish(bindings):
    preserved_failure = original_failed_attempt(bindings)
    built = read(E / 'built-image.json')
    value = gate(E / 'postdeploy-independent-audit.json', 'postdeploy', bindings, built['image_id'])
    for key, path in (('after_sha256', E / 'after.json'), ('verify_completed_sha256', E / 'verify' / 'completed.json')):
        require(value.get(key) == sha(path), 'postdeploy audit evidence mismatch')
    result = {'batch': BATCH, 'change': 'C03-R01', 'bounded_accepted': True,
              'R01_source_and_worker_off_deployment_only': True, 'R02_accepted': False,
              'autonomous_quality_passed': False, 'whole_C03_complete': False,
              'full_migration_complete': False, 'real_models': 0, 'worker_enabled': False,
              'profile': PROFILE, 'image_id': built['image_id'], 'source_sha256': expected_sources(bindings),
              'operator_sha256': sha(__file__), 'bindings_sha256': sha(bindings['_path']),
              'verify_completed_sha256': sha(E / 'verify' / 'completed.json'),
              'postdeploy_audit_sha256': sha(E / 'postdeploy-independent-audit.json'),
              'no_R02_business_or_budget_authorization_implied': True,
              'observer_recovery': preserved_failure}
    save(E / 'acceptance.json', result)
    return result


PHASES = {'prepare': phase_prepare, 'stage': phase_stage, 'test': phase_test,
          'build': phase_build, 'deploy': phase_deploy, 'verify': phase_verify, 'finish': phase_finish}


def load_bindings(path):
    value = read(path)
    require(value.get('execution_authorized') is True and value.get('batch') == BATCH and
            value.get('change') == 'C03-R01', 'candidate bindings are not authorized')
    require('UNBOUND' not in json.dumps(value), 'UNBOUND candidate must not execute')
    require(value['operator_sha256'] == sha(__file__), 'operator bytes do not match authorized bindings')
    require(set(value['runtime_source_sha256']) == set(RUNTIME) and set(value['new_test_sha256']) == set(NEW_TESTS), 'source/test path mismatch')
    require(len(value['parent_runtime_source_sha256']) == 769 and NEW_RUNTIME not in value['parent_runtime_source_sha256'], 'parent source map mismatch')
    require(len(value['parent_compose_sha256']) == 27, 'parent compose map mismatch')
    require(len(value['parent_compose_order']) == 27 and set(value['parent_compose_order']) == set(value['parent_compose_sha256']), 'parent compose order mismatch')
    value['_path'] = str(path)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=PHASES)
    parser.add_argument('--bindings', type=Path, required=True)
    args = parser.parse_args()
    # Authorization is checked before any mkdir, lock, subprocess, or observation.
    bindings = load_bindings(args.bindings)
    require(os.geteuid() == 0, 'host root required for bounded Docker/private evidence operations')
    os.umask(0o077)
    P.mkdir(mode=0o700, parents=True, exist_ok=True)
    E.mkdir(mode=0o700, parents=True, exist_ok=True)
    require(stat.S_IMODE(P.stat().st_mode) == stat.S_IMODE(E.stat().st_mode) == 0o700, 'private/evidence directory mode')
    with (P / 'phase.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        order = list(PHASES)
        for previous in order[:order.index(args.phase)]:
            checkpoint = E / previous / 'completed.json'
            require(checkpoint.is_file(), 'preceding phase not complete: ' + previous)
            prior = read(checkpoint)
            require(prior['operator_sha256'] == sha(__file__) and prior['bindings_sha256'] == sha(args.bindings),
                    'operator/bindings changed since preceding phase')
        directory = E / args.phase
        directory.mkdir(mode=0o700)  # Never remove or reuse a failed phase directory.
        save(directory / 'started.json', {'batch': BATCH, 'phase': args.phase,
                                         'started_at': datetime.now(timezone.utc).isoformat(),
                                         'operator_sha256': sha(__file__), 'bindings_sha256': sha(args.bindings)})
        try:
            for path, checksum in bindings['parent_compose_sha256'].items():
                require(sha(S / path) == checksum, 'frozen parent compose byte drift')
            require(sha(S / 'docs/handoff/handoff-manifest.json') == bindings['parent_handoff_sha256'], 'frozen parent index drift')
            require(sha(S / 'services/agents/app/llm/prompts.lock.json') == bindings['prompt_lock_sha256'], 'frozen prompt lock drift')
            expected = bindings['parent_runtime_source_sha256'] if args.phase in ('prepare', 'stage') else expected_sources(bindings)
            require(source_map() == expected, 'source differs at phase entry')
            if args.phase not in ('prepare', 'stage'):
                for path, checksum in bindings['document_sha256'].items():
                    require(sha(S / path) == checksum, 'adopted document changed during R01')
            result = PHASES[args.phase](bindings)
            save(directory / 'completed.json', {'batch': BATCH, 'phase': args.phase, 'result': result,
                                                'operator_sha256': sha(__file__), 'bindings_sha256': sha(args.bindings)})
            print(json.dumps({'batch': BATCH, 'phase': args.phase, 'completed': True,
                              'checkpoint_sha256': sha(directory / 'completed.json')}))
        except BaseException as exc:
            save(directory / 'failure.json', {'batch': BATCH, 'phase': args.phase,
                                             'type': type(exc).__name__, 'message_sha256': hashlib.sha256(str(exc).encode()).hexdigest(),
                                             'automatic_retry_or_rollback': False, 'preserve_phase_and_inspect': True})
            print(json.dumps({'batch': BATCH, 'phase': args.phase, 'completed': False,
                              'failure_type': type(exc).__name__, 'automatic_retry_or_rollback': False}))
            raise SystemExit(1) from None


if __name__ == '__main__':
    main()
