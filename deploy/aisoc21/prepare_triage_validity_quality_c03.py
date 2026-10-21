"""Freeze/provision C03-02D-02; never sends an alert or calls a model.

freeze: read-only baseline and project backup, private staged identities.
provision: after independent source review, add only three expiring keys and
three extra A policy calls; B uses its one old unused slot. Topic creation is a separate phase.
No automatic rollback, retry, reservation refund, or service restart occurs.
"""
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import uuid

import configure_triage_admission_3a as base
from prepare_identity_read_3a import lit
from shared_1b import SharedBatch, PG_CONTAINER

R = Path('/opt/sting-aisoc-socai2')
S = R / 'source'
B = 'c03-triage-validity-quality-20261021'
E = R / 'evidence' / B
P = R / 'private/completion-c03-validity-quality'
G = R / 'private/completion-c03-validity-quality-grading'
AUDIT_GATES = R / 'private/completion-c03-validity-quality-gates'
POLICY = R / 'private/triage-budget-3a/policy.json'
INPUT = S / 'docs/operations/c03-triage-validity-quality-inputs.json'
PLAN = S / 'docs/operations/c03-triage-validity-quality-plan.md'
INSIDE = S / 'deploy/aisoc21/acceptance_triage_validity_quality_c03.py'
INPUT_SHA = 'e80c04a5e9d2bc18b526c197af9b6e9ab8cbc5966e2615dca274e12b3949e3c2'
RUBRIC_SHA = '07e944d4c43d7d93ef1968a4316f74efc20565aa1c2b406202b9aa92797443b1'
IMAGE = 'sha256:9cb719ff55d772ebf047f87a06863ae7102feb5be3b9471610113dd9d85728fd'
PARENT_ACCEPTANCE_SHA = '3999189db4c42b0ca9a7d54e59a049996030a7744c8e15c63f02848deadc355f'
LOCK = 'services/agents/app/llm/prompts.lock.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, value, *, container_readable=False):
    with path.open('x') as f:
        json.dump(value, f, indent=2, default=str)
        f.write('\n')
    path.chmod(0o600)
    if container_readable:
        os.chown(path, 10001, 10001)


def copy_private(source, target, *, container_readable=False):
    with target.open('xb') as f:
        f.write(source.read_bytes())
    target.chmod(0o600)
    if container_readable:
        os.chown(target, 10001, 10001)


assert base.OFFSET_CODE.count(';c.assign([tp])') == 1
OFFSET_CODE = base.OFFSET_CODE.replace(';c.assign([tp])', '')

INPUT_AND_SCOPE_FROZEN = True


def require_bound_parent():
    if not INPUT_AND_SCOPE_FROZEN or not re.fullmatch(r'sha256:[0-9a-f]{64}', IMAGE) or not re.fullmatch(r'[0-9a-f]{64}', PARENT_ACCEPTANCE_SHA):
        raise RuntimeError('D2 draft is unbound: root must freeze independent criteria and actual D1 image/seal before any phase or observer hook')


# Fail before installing any counter hook or creating evidence directories.
require_bound_parent()

_read_pg = base.pg
PHASE = 'unselected'


def http_start(*, path='/metrics', host='127.0.0.1', port=4000, method='GET', historical=False):
    """Reserve one shared operator HTTP slot; never serializes headers/body.

    All shared counter files must be readable by the UID10001 inside
    observer. Historical backfills are explicit caller actions, not inferred
    from the current gateway count. A slot is not proof a request was sent.
    """
    directory = E / 'http-events'
    directory.mkdir(mode=0o700, exist_ok=True)
    os.chown(directory, 10001, 10001)
    prior = [read(p) for p in directory.glob('*-started.json')]
    assert sum(not row['synthetic_model_transport'] for row in prior) < 240
    sequence = len(prior) + 1
    save(directory / f'{sequence:04d}-started.json', {
        'case': 'host-observation', 'phase': PHASE, 'sequence': sequence,
        'method': method, 'scheme': 'http', 'host': host, 'port': port, 'path': path,
        'query_sha256': hashlib.sha256(b'').hexdigest(), 'synthetic_model_transport': False,
        'host_http_slot_reserved': True, 'host_metrics_slot_reserved': path == '/metrics',
        'historical_backfill': historical, 'actual_network_acceptance': 'not_observed_yet'},
        container_readable=True)
    return sequence


def http_finish(sequence, *, status=None, error_type=None, confirmed=False, historical=False):
    save(E / 'http-events' / f'{sequence:04d}-finished.json', {
        'status': status, 'error_type': error_type,
        'actual_network_request_confirmed': confirmed, 'historical_confirmation': historical,
        'slot_still_counts_toward_cap': True}, container_readable=True)


_read_check_output = subprocess.check_output


def traced_check_output(command, *args, **kwargs):
    # The existing observer calls exactly this script once, after its SQL
    # checks. Count at that invocation rather than claiming an early observer
    # failure already sent its later metrics request.
    if command != ['docker', 'exec', 'socai2-litellm-1', 'python', '-c', base.METRICS]:
        return _read_check_output(command, *args, **kwargs)
    sequence = http_start()
    try:
        output = _read_check_output(command, *args, **kwargs)
    except BaseException as error:
        http_finish(sequence, error_type=type(error).__name__)
        raise
    http_finish(sequence, status=200, confirmed=True)
    return output


subprocess.check_output = traced_check_output


def trace_sql(sql, mode):
    """Counts explicit host helper calls, not internal API/worker SQL."""
    directory = E / 'host-sql-attempts'
    directory.mkdir(mode=0o700, exist_ok=True)
    number = len(list(directory.glob('*.json'))) + 1
    save(directory / f'{number:04d}.json', {'phase': PHASE, 'mode': mode,
         'sql_sha256': hashlib.sha256(sql.encode()).hexdigest(), 'internal_service_sql_included': False})


def readonly_pg(sql):
    trace_sql(sql, 'read-only transaction')
    return _read_pg(sql)


def write_pg(batch, sql):
    trace_sql(sql, 'explicit bounded write')
    return batch.pg(sql)


base.pg = readonly_pg


def readable_inside():
    """Read-only precondition: the public operator must be readable by UID10001."""
    info = INSIDE.lstat()
    assert stat.S_ISREG(info.st_mode) and info.st_mode & 0o777 == 0o644


BASELINE_FILES = (
    'before-closure-qa.json', 'before-extra-tables.json',
    'fusion-raw-metadata-before.json', 'main-fused-metadata-before.json',
    'fusion-metrics-before.json', 'inside-readable-before-business.json',
    'old-quality-metadata-before.json', 'old-recheck-quality-metadata-before.json',
    'old-authorization-quality-metadata-before.json',
    'before.json', 'private-input-hashes-before.json', 'resident-before.json',
    'old-budget-offsets-before.json', 'prompt-before.json', 'backup-created.json',
    'prepared.json', 'provision-intent.json', 'scope-before.md',
)


def baseline_hashes():
    """Bind fresh, separately observed new-E baselines; never copy old observations."""
    readable_inside()
    paths = {name: E / name for name in BASELINE_FILES}
    paths.update({'private/' + name: P / name for name in
                  ('policy-before.json', 'agents-before.json', 'inputs.json',
                   'probe.env', 'state-draft.json', 'before.dump')})
    assert all(stat.S_ISREG(path.lstat().st_mode) for path in paths.values())
    backup = read(E / 'backup-created.json')
    assert sha(P / 'before.dump') == backup['sha256']
    assert (P / 'before.dump').stat().st_size == backup['bytes']
    assert sha(P / 'policy-before.json') == read(E / 'before.json')['policy_sha256']
    probe = read(E / 'inside-readable-before-business.json')
    assert probe['image_id'] == IMAGE and probe['operator_sha256'] == sha(INSIDE)
    assert probe['uid'] == 10001 and probe['network'] == 'none'
    assert probe['readable'] is True and probe['exit_code'] == 0
    return {name: sha(path) for name, path in paths.items()}


def frozen_inputs():
    readable_inside()
    assert sha(INPUT) == INPUT_SHA and sha(G / 'rubric.json') == RUBRIC_SHA
    assert sha(PLAN) == sha(E / 'scope-before.md')
    assert sha(P / 'inputs.json') == INPUT_SHA
    assert read(INPUT)['batch'] == B and len(read(INPUT)['cases']) == 4


def old_state_unchanged(*, policy_changed=False):
    now, before = base.observation(), read(E / 'before.json')
    if policy_changed:
        assert now['policy_sha256'] == read(E / 'provision-intent.json')['policy_after_sha256']
        now['policy_sha256'] = before['policy_sha256']
    assert now == before, 'State drift: inspect; never replay a provision or model attempt'
    expected = read(E / 'private-input-hashes-before.json')
    if policy_changed:
        expected['private/triage-budget-3a/policy.json'] = read(E / 'provision-intent.json')['policy_after_sha256']
    assert base.private_hashes() == expected


def freeze():
    readable_inside()
    assert not E.exists() and not P.exists() and not AUDIT_GATES.exists()
    assert sha(INPUT) == INPUT_SHA and sha(G / 'rubric.json') == RUBRIC_SHA
    inputs = read(INPUT)
    assert inputs['batch'] == B and inputs['max_real_model_requests'] == 4
    prior = R / 'evidence/c03-triage-detection-validity-20261021'
    assert sha(prior / 'acceptance.json') == PARENT_ACCEPTANCE_SHA
    parent = read(prior / 'acceptance.json')
    assert parent['change'] == 'C03-02D-01' and parent['bounded_accepted'] is True
    assert parent['image_id'] == IMAGE and parent['triage_prompt']['version'] == '5'
    assert parent['runtime_source_layers'] == 24 and parent['compose_layers'] == 27
    assert parent['real_models'] == 0 and parent['worker_enabled'] is False
    for name in ('predeploy-independent-audit.json', 'independent-audit.json', 'closeout-independent-audit.json'):
        audit = read(prior / name)
        assert audit['accepted'] is True and audit['image_id'] == IMAGE
    assert parent['independent_audit_sha256'] == sha(prior / 'independent-audit.json')
    E.mkdir(mode=0o700)
    P.mkdir(mode=0o700)
    AUDIT_GATES.mkdir(mode=0o700)
    os.chown(E, 10001, 10001)
    os.chown(AUDIT_GATES, 10001, 10001)
    before = base.observation()
    assert before == read(prior / 'after.json')
    assert len(before['budget']) == 10 and sum(x['settled_at'] is None for x in before['budget']) == 3
    assert sum(x['charged_tokens'] for x in before['budget']) == 200000
    save(E / 'before.json', before)
    save(E / 'private-input-hashes-before.json', base.private_hashes())
    save(P / 'agents-before.json', base.inspect('socai2-agents-1'))
    assert read(P / 'agents-before.json')['Image'] == IMAGE
    copy_private(PLAN, E / 'scope-before.md')
    copy_private(INPUT, P / 'inputs.json', container_readable=True)
    copy_private(POLICY, P / 'policy-before.json')
    old = read(R / 'private/app-triage-budget-3a.json')
    aliases = {a: old['identities'][a]['tenant_id'] for a in ('a', 'b')}
    flags = base.container_json(base.FLAGS_CODE, payload=list(aliases.values()))
    assert flags['reader_maps_resolve'] and flags['uid'] == 10001
    assert all(flags[k] is False for k in ['worker', 'escalation', 'memory_writeback', 'approvals', 'alert_graph'])
    local = {str(p.relative_to(S)): sha(p) for p in (S / 'services/agents/app').rglob('*.py')}
    assert flags['source'] == local and len(local) == 184
    assert sum(row['tenant_id'] == aliases['a'] for row in before['budget']) == 7
    assert sum(row['tenant_id'] == aliases['b'] for row in before['budget']) == 3
    assert sum(row['tenant_id'] == aliases['a'] and row['settled_at'] is None for row in before['budget']) == 2
    assert sum(row['tenant_id'] == aliases['b'] and row['settled_at'] is None for row in before['budget']) == 1
    save(E / 'resident-before.json', flags)
    save(E / 'old-budget-offsets-before.json', base.container_json(OFFSET_CODE))
    prompt = base.container_json("from app.llm.prompt_registry import default_registry,load_lock;from pathlib import Path;import hashlib,json;r=default_registry();assert not r.verify_against_lock(load_lock());p=r.get('triage.system');print(json.dumps({'version':p.version,'sha256':p.sha256,'lock_sha256':hashlib.sha256(Path('/app/app/llm/prompts.lock.json').read_bytes()).hexdigest()}))")
    assert prompt['version'] == '5' and prompt['lock_sha256'] == sha(S / LOCK)
    save(E / 'prompt-before.json', prompt)
    policy = read(POLICY)
    assert set(policy['tenants']) == set(aliases.values())
    initial = {
        'a': {'window_seconds': 86400, 'max_calls': 7, 'max_reserved_tokens': 140000, 'max_unsettled': 3},
        'b': {'window_seconds': 86400, 'max_calls': 4, 'max_reserved_tokens': 80000, 'max_unsettled': 2},
    }
    assert all(policy['tenants'][aliases[a]] == initial[a] for a in ('a', 'b'))
    target = json.loads(json.dumps(policy))
    target['tenants'][aliases['a']].update(max_calls=10, max_reserved_tokens=200000, max_unsettled=3)
    assert target['tenants'][aliases['b']] == policy['tenants'][aliases['b']]
    save(P / 'policy-for-this-batch.json', target, container_readable=True)
    now = datetime.fromisoformat(base.pg('SELECT now()::text;').stdout.strip())
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, 'socai2/' + B)
    identities = {}
    for alias in ['a', 'b', 'denied']:
        parent = old['identities']['a' if alias == 'denied' else alias]
        identities[alias] = {'tenant_id': parent['tenant_id'], 'user_id': parent['user_id'],
             'key_id': str(uuid.uuid5(namespace, 'key/' + alias)), 'key': 'aisoc_' + secrets.token_hex(24),
             'scopes': ['settings:read'] if alias == 'denied' else ['alerts:read', 'alerts:write', 'cases:read'],
             'expires_at': (now + timedelta(hours=3)).isoformat()}
    broker = {'quality_topic': 'socai2.c03.triage-validity-quality.20261021',
              'dlq_topic': 'socai2.c03.triage-validity-quality.20261021.dlq', 'group': 'socai2-c03-triage-validity-quality-20261021'}
    state = {'batch': B, 'execution_authorized': False, 'image_id': IMAGE, 'source_sha256': local,
             'prompt_lock_sha256': prompt['lock_sha256'], 'inputs_sha256': INPUT_SHA,
             'plan_sha256': sha(PLAN), 'identities': identities, 'broker': broker,
             'policy_sha256': sha(P / 'policy-for-this-batch.json')}
    save(P / 'state-draft.json', state, container_readable=True)
    env = base.env(base.inspect('socai2-agents-1'))
    assert env['AISOC_AGENT_KAFKA_DISABLE'] == '1'
    assert all('\n' not in k + v and '\r' not in k + v for k, v in env.items())
    with (P / 'probe.env').open('x') as f:
        f.write(''.join(k + '=' + v + '\n' for k, v in sorted(env.items())))
    (P / 'probe.env').chmod(0o600)
    batch = SharedBatch(R)
    backup = subprocess.check_output(['docker', 'exec', PG_CONTAINER, 'pg_dump', '-U', batch.pg_admin, '-d', 'aisoc', '-Fc'])
    with (P / 'before.dump').open('xb') as f:
        f.write(backup)
    (P / 'before.dump').chmod(0o600)
    save(E / 'backup-created.json', {'project_database': 'aisoc', 'private_path': str(P / 'before.dump'),
         'sha256': sha(P / 'before.dump'), 'bytes': len(backup), 'format': 'pg_dump custom', 'restore_tested_this_batch': False})
    save(E / 'provision-intent.json', {'operation_keys': [{k: v for k, v in value.items() if k != 'key'} for value in identities.values()],
         'policy_before_sha256': sha(POLICY), 'policy_after_sha256': state['policy_sha256'],
         'new_policy': target, 'broker': broker, 'rubric_sha256': RUBRIC_SHA, 'inputs_sha256': INPUT_SHA,
         'old_reservations_refunded_or_replayed': False, 'real_models': 0, 'new_business_rows': 0})
    old_state_unchanged()
    save(E / 'prepared.json', {'batch': B, 'image_id': IMAGE, 'plan_sha256': sha(PLAN),
         'inputs_sha256': INPUT_SHA, 'rubric_sha256': RUBRIC_SHA, 'source_count': 184,
         'prompt_lock_sha256': prompt['lock_sha256'], 'max_real_models': 4, 'max_new_reservations': 4,
         'max_new_reserved_units': 80000, 'max_send_attempts': 12, 'normal_and_max_deliveries': 12,
         'operator_http_attempt_cap': 240, 'compose_layers': 27, 'source_layers': 24,
         'parent_acceptance_sha256': sha(prior / 'acceptance.json'),
         'parent_runtime_audit_sha256': sha(prior / 'independent-audit.json'),
         'parent_closeout_audit_sha256': sha(prior / 'closeout-independent-audit.json'), 'old_state_preserved': True, 'new_db_keys': 0, 'policy_installed': False})
    print(json.dumps({'prepared': True, 'batch': B, 'new_db_keys': 0, 'policy_installed': False, 'real_models': 0}))


def provision():
    frozen_inputs()
    assert not (E / 'provision-started.json').exists()
    review = read(E / 'provision-independent-review.json')
    assert review['accepted'] and review['prepare_operator_sha256'] == sha(Path(__file__))
    assert review['inside_operator_sha256'] == sha(INSIDE)
    assert review['baseline_sha256'] == baseline_hashes()
    old_state_unchanged()
    draft = read(P / 'state-draft.json')
    assert not draft['execution_authorized']
    batch = SharedBatch(R)
    ids = ','.join(lit(x['key_id']) for x in draft['identities'].values())
    assert base.pg('SELECT count(*) FROM api_keys WHERE id IN (' + ids + ');').stdout.strip() == '0'
    save(E / 'provision-started.json', {'new_keys': 3, 'policy_capacity_added_calls': 3,
         'prepare_operator_sha256': sha(Path(__file__)), 'inside_operator_sha256': sha(INSIDE)})
    sql = 'SET ROLE aisoc; BEGIN; '
    for alias, key in draft['identities'].items():
        fields = [lit(key[k]) for k in ['key_id', 'tenant_id', 'user_id']]
        fields += [lit(B + '-' + alias), lit(key['key'][:12]), lit(hashlib.sha256(key['key'].encode()).hexdigest()),
                   lit(json.dumps(key['scopes'])) + '::jsonb', lit(key['expires_at'])]
        sql += 'INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES (' + ','.join(fields) + '); '
    write_pg(batch, sql + 'COMMIT;')
    save(E / 'keys-insert-confirmed.json', {'keys': 3, 'raw_keys_in_public_evidence': False})
    replacement = POLICY.with_name('policy.c03-validity-quality-replacement')
    copy_private(P / 'policy-for-this-batch.json', replacement, container_readable=True)
    replacement.replace(POLICY)
    assert sha(POLICY) == draft['policy_sha256']
    draft['operator_sha256'] = sha(INSIDE)
    save(P / 'state-provisioned.json', draft, container_readable=True)
    old_state_unchanged(policy_changed=True)
    save(E / 'provisioned.json', {'operation_keys': 3, 'policy_sha256': sha(POLICY),
         'old_budget_rows': 10, 'old_unknown': 3, 'new_reservations': 0, 'models': 0,
         'prepare_operator_sha256': sha(Path(__file__)), 'inside_operator_sha256': sha(INSIDE)})
    print(json.dumps({'provisioned': True, 'keys': 3, 'old_reservations_preserved': True, 'real_models': 0}))


TOPICS_CODE = '''import asyncio,json,os,sys
from aiokafka import AIOKafkaConsumer,TopicPartition
from aiokafka.admin import AIOKafkaAdminClient,NewTopic
from aiokafka.structs import OffsetAndMetadata
from app.core.kafka_security import kafka_client_kwargs
cfg=json.load(sys.stdin)
async def main():
 kw=dict(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],**kafka_client_kwargs())
 admin=AIOKafkaAdminClient(**kw);await admin.start()
 try:
  names=[cfg['quality_topic'],cfg['dlq_topic']]
  assert not set(names).intersection(await admin.list_topics())
  await admin.create_topics([NewTopic(n,1,1,topic_configs={'retention.ms':'604800000'}) for n in names])
 finally:await admin.close()
 c=AIOKafkaConsumer(group_id=cfg['group'],enable_auto_commit=False,**kw);await c.start()
 try:
  tp=TopicPartition(cfg['quality_topic'],0);c.assign([tp])
  assert await c.committed(tp) is None and (await c.beginning_offsets([tp]))[tp]==(await c.end_offsets([tp]))[tp]==0
  await c.commit({tp:OffsetAndMetadata(0,'c03-validity-quality-new-empty-group')})
  assert await c.committed(tp)==0
 finally:await c.stop()
 print(json.dumps({'created_topics':names,'group':cfg['group'],'initial_commit':0,'physical_record_reads':0,'publications':0}))
asyncio.run(main())'''


def topics():
    frozen_inputs()
    assert (E / 'provisioned.json').is_file() and not (E / 'topics-started.json').exists()
    old_state_unchanged(policy_changed=True)
    state = read(P / 'state-provisioned.json')
    save(E / 'topics-started.json', {'broker': state['broker'], 'new_only': True})
    result = base.container_json(TOPICS_CODE, payload=state['broker'])
    save(E / 'topics-ready.json', result)
    assert base.container_json(OFFSET_CODE) == read(E / 'old-budget-offsets-before.json')
    old_state_unchanged(policy_changed=True)
    print(json.dumps({'topics_ready': True, 'topics': 2, 'new_group_commits': 1, 'real_models': 0}))


def authorize():
    frozen_inputs()
    assert (E / 'topics-ready.json').is_file() and not (P / 'state.json').exists()
    review = read(E / 'pre-execution-independent-audit.json')
    assert review['accepted'] and review['image_id'] == IMAGE
    assert review['baseline_sha256'] == baseline_hashes()
    state = read(P / 'state-provisioned.json')
    assert review['inside_operator_sha256'] == state['operator_sha256'] == sha(INSIDE)
    old_state_unchanged(policy_changed=True)
    state['execution_authorized'] = True
    save(P / 'state.json', state, container_readable=True)
    save(E / 'execution-authorized.json', {'image_id': IMAGE, 'inside_operator_sha256': sha(INSIDE),
         'audit_sha256': sha(E / 'pre-execution-independent-audit.json'), 'real_models': 0})
    print(json.dumps({'execution_authorized': True, 'real_models': 0, 'resident_worker_enabled': False}))


if __name__ == '__main__':
    os.umask(0o077)
    assert len(sys.argv) == 2 and sys.argv[1] in {'freeze', 'provision', 'topics', 'authorize'}
    PHASE = sys.argv[1]
    {'freeze': freeze, 'provision': provision, 'topics': topics, 'authorize': authorize}[PHASE]()
