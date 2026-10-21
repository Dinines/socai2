"""Stage, deploy and verify config only; never start a triage consumer.

Host21 one-shot phases: prepare, deploy, verify. Checkpoints prevent blind replay.
Rollback is a separate explicit operation using the private saved service definition.
"""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import os
import subprocess
import sys
import time

from deploy_triage_budget_3a import PARTS as PRIOR_PARTS
from deploy_triage_recovery_3a import inspect, describe
from prepare_2a import snapshot
from prepare_triage_request_3a import material, readers, SDK
from prepare_identity_read_3a import TABLES
from finish_model_triage_3a import METRICS

R = Path('/opt/sting-aisoc-socai2')
S = R / 'source'
B = '3a-triage-admission-config-20261020'
E = R / 'evidence' / B
P = R / 'private/triage-admission-config-3a'
PREVIOUS = R / 'evidence/3a-admission-review-20261020'
PARTS = PRIOR_PARTS + ['triage-admission-config-3a']
ADDED = {'AISOC_AGENT_RAISE_APPROVALS': '0', 'KAFKA_BOOTSTRAP_SERVERS': '192.168.1.21:19093',
         'KAFKA_SECURITY_PROTOCOL': 'SSL', 'KAFKA_SSL_CAFILE': '/run/certs/ca.crt'}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def save(directory, name, value):
    with (directory / name).open('x') as f:
        json.dump(value, f, indent=2, default=str)
        f.write('\n')
    (directory / name).chmod(0o600)


def compose(parts=PARTS):
    command = ['docker', 'compose', '--project-directory', str(R)]
    for part in parts:
        command += ['-f', str(S / f'deploy/aisoc21/compose.{part}.yml')]
    return command


def env(item):
    return dict(value.split('=', 1) for value in item['Config']['Env'])


def pg(sql):
    admin = env(inspect('spirithub-postgres-1'))['POSTGRES_USER']
    result = subprocess.run(['docker', 'exec', '-i', 'spirithub-postgres-1', 'psql',
                             '-X', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1', '-U', admin, '-d', 'aisoc'],
                            input='BEGIN READ ONLY;\n' + sql + '\nROLLBACK;', text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError('Read-only PG observation failed; no changes attempted')
    return result


def observation():
    db = SimpleNamespace(pg=pg)
    return {'environment': snapshot(),
            'materials': {t: [hashlib.sha256(row['material'].encode()).hexdigest() for row in material(db, t)]
                          for t in ['alerts'] + TABLES},
            'budget': json.loads(pg("SELECT COALESCE(json_agg(t),'[]'::json) FROM "
                                   "(SELECT * FROM socai2_triage_budget_reservations ORDER BY run_id) t;").stdout),
            'readers': readers(db), 'policy_sha256': sha(R / 'private/triage-budget-3a/policy.json'),
            'migrations': int(pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip()),
            'gateway': json.loads(subprocess.check_output(['docker', 'exec', 'socai2-litellm-1', 'python', '-c', METRICS]))}


def container_json(code, service='agents', payload=None):
    proc = subprocess.run(['docker', 'exec', '-i', 'socai2-' + service + '-1', 'python', '-c', code],
                          input=json.dumps(payload), text=True, capture_output=True)
    if proc.returncode:
        # Never serialize exception locals or raw environment values.
        raise RuntimeError('Container probe failed; stderr_sha256=' + hashlib.sha256(proc.stderr.encode()).hexdigest())
    return json.loads(proc.stdout.splitlines()[-1])


OFFSET_CODE = '''import asyncio,json,os
from aiokafka import AIOKafkaConsumer,TopicPartition
from app.core.kafka_security import kafka_client_kwargs
async def main():
 out={};security=kafka_client_kwargs();assert security['security_protocol']=='SSL'
 for alias in ['a_done','b_done','a_unknown','a_denied','b_denied','b_extra']:
  topic='socai2.test.3a-triage-budget-20261020.'+alias
  c=AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],group_id=topic+'.worker',enable_auto_commit=False,**security)
  await c.start();tp=TopicPartition(topic,0);c.assign([tp])
  try:out[alias]={'committed':await c.committed(tp),'end':(await c.end_offsets([tp]))[tp]}
  finally:await c.stop()
 print(json.dumps(out))
asyncio.run(main())'''

FLAGS_CODE = '''import os,json,hashlib
from pathlib import Path
from app.workers import fused_alert_consumer as w
from app.context.organisation_memory import _credential
tenants=json.load(__import__('sys').stdin)
variables=['AISOC_ORG_MEMORY_KEYS_FILE','AISOC_TENANT_SKILLS_KEYS_FILE','AISOC_TRIAGE_KB_KEYS_FILE','AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE','AISOC_TRIAGE_IDENTITY_KEYS_FILE']
print(json.dumps({'worker':w.worker_enabled(),'escalation':w._escalation_enabled(),'memory_writeback':w._memory_writeback_enabled(),'approvals':w._approvals_enabled(),'alert_graph':w.alert_trigger.deployment_enabled(),'uid':os.getuid(),'reader_maps_resolve':all(_credential(t,keys_file_env=v) for t in tenants for v in variables),'source':{'services/agents/app/'+str(p.relative_to('/app/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/app').rglob('*.py')}}))'''

TLS_CODE = '''import ssl,socket,os,json,hashlib
from pathlib import Path
from app.core.kafka_security import kafka_client_kwargs
k=kafka_client_kwargs();ctx=k['ssl_context'];assert k['security_protocol']=='SSL'
assert ctx.check_hostname and ctx.verify_mode==ssl.CERT_REQUIRED
assert not os.getenv('AISOC_ALLOW_CLEARTEXT_KAFKA')
host,port=os.environ['KAFKA_BOOTSTRAP_SERVERS'].split(':');port=int(port)
with socket.create_connection((host,port),timeout=10) as s:
 with ctx.wrap_socket(s,server_hostname=host) as t:
  peer=t.getpeercert();version=t.version();der=t.getpeercert(binary_form=True)
try:
 with socket.create_connection((host,port),timeout=10) as s:
  with ctx.wrap_socket(s,server_hostname='certificate-name-mismatch.invalid'):pass
except ssl.SSLCertVerificationError as exc:
 mismatch={'rejected':True,'verify_code':exc.verify_code}
else:raise AssertionError('Hostname mismatch accepted')
print(json.dumps({'uid':os.getuid(),'security_protocol':'SSL','check_hostname':ctx.check_hostname,'cert_required':ctx.verify_mode==ssl.CERT_REQUIRED,'ca_sha256':hashlib.sha256(Path(os.environ['KAFKA_SSL_CAFILE']).read_bytes()).hexdigest(),'peer_sha256':hashlib.sha256(der).hexdigest(),'peer_not_after':peer['notAfter'],'tls_version':version,'wrong_hostname':mismatch,'bootstrap':os.environ['KAFKA_BOOTSTRAP_SERVERS']}))'''


def private_hashes():
    paths = [R / 'private/agents-1g.env', R / 'private/triage-budget-3a/policy.json',
             R / 'certificates/socai2-ca.crt']
    for stem in ['org-memory', 'tenant-skill', 'kb-read', 'dispositions', 'identity-read']:
        paths += [R / f'private/{stem}-3a/keys.json']
    return {str(p.relative_to(R)): sha(p) for p in paths}


def frozen_receipts():
    names = ['3a-triage-admission', '3a-triage-budget', '3a-admission-review']
    output = {}
    for stem in names:
        receipt = S / f'docs/operations/{stem}.json'
        value = read(receipt)
        directory = R / 'evidence' / value['batch']
        assert all(sha(directory / row['path']) == row['sha256'] for row in value['raw_artifacts'])
        output[stem] = {'receipt_sha256': sha(receipt), 'raw_files_verified': len(value['raw_artifacts'])}
    return output


def prepare():
    E.mkdir(mode=0o700, exist_ok=False)
    P.mkdir(mode=0o700, exist_ok=False)
    save(E, 'scope.json', {'batch': B, 'plan_sha256': sha(S / 'docs/operations/3a-triage-admission-config-plan.md'),
         'only_recreate_service': 'agents', 'same_image': True, 'real_models': 0, 'new_messages': 0,
         'offset_commits': 0, 'new_credentials': 0, 'schema_changes': 0})
    (E / 'scope-before.md').write_bytes((S / 'docs/operations/3a-triage-admission-config-plan.md').read_bytes())
    (E / 'scope-before.md').chmod(0o600)
    before = observation()
    prior = read(PREVIOUS / 'after.json')
    assert before == {k: prior[k] for k in before}, 'State drift: review before deploying'
    save(E, 'before.json', before)
    save(E, 'private-input-hashes.json', private_hashes())
    old = inspect('socai2-agents-1')
    save(P, 'container-before.json', old)
    tenants = [v['metadata']['reader_a']['tenant_id'] for v in before['readers'].values()]
    tenants += [v['metadata']['reader_b']['tenant_id'] for v in before['readers'].values()]
    tenants = sorted(set(tenants))
    flags = container_json(FLAGS_CODE, payload=tenants)
    assert flags['approvals'] is True and all(flags[k] is False for k in ['worker', 'escalation', 'memory_writeback', 'alert_graph'])
    assert flags['source'] == read(PREVIOUS / 'runtime.json')['source']
    save(E, 'resident-before.json', flags)
    save(E, 'tenants.json', tenants)
    offsets = container_json(OFFSET_CODE, service='fusion')
    assert offsets == read(PREVIOUS / 'budget-and-offsets.json')['offsets']
    save(E, 'offsets-before.json', offsets)
    fe = env(inspect('socai2-fusion-1'))
    assert {k: fe[k] for k in ADDED if k != 'AISOC_AGENT_RAISE_APPROVALS'} == {k: v for k, v in ADDED.items() if k != 'AISOC_AGENT_RAISE_APPROVALS'}
    assert all(k not in env(old) for k in ADDED)
    mounts = [m for m in old['Mounts'] if m['Destination'] == '/run/certs/ca.crt']
    assert len(mounts) == 1 and mounts[0]['Source'] == str(R / 'certificates/socai2-ca.crt') and not mounts[0]['RW']
    assert len(PRIOR_PARTS) == 21 and len(PARTS) == 22
    configs = []
    for parts in [PRIOR_PARTS, PARTS]:
        proc = subprocess.run(compose(parts) + ['config', '--format', 'json'], text=True, capture_output=True)
        assert proc.returncode == 0, 'Compose render failed'
        configs.append(json.loads(proc.stdout))
    prior_config, desired = configs
    save(P, 'compose-before.json', prior_config)
    save(P, 'compose-desired.json', desired)
    old_agent, new_agent = prior_config['services']['agents'], desired['services']['agents']
    assert env(old)['AISOC_AGENT_KAFKA_DISABLE'] == new_agent['environment']['AISOC_AGENT_KAFKA_DISABLE'] == '1'
    delta = {k: v for k, v in new_agent['environment'].items() if old_agent['environment'].get(k) != v}
    assert delta == ADDED and not (set(old_agent['environment']) - set(new_agent['environment']))
    expected = json.loads(json.dumps(prior_config))
    expected['services']['agents']['environment'].update(ADDED)
    assert expected == desired, 'Unexpected service/config change'
    assert inspect(new_agent['image'])['Id'] == old['Image']
    rollback = {'name': 'socai2', 'services': {'agents': old_agent},
                'networks': {key: {'name': value['name'], 'external': True} for key, value in prior_config['networks'].items()}}
    assert not old_agent.get('depends_on')
    save(P, 'rollback.agents.json', rollback)
    rollback_command = ['docker', 'compose', '--project-directory', str(R), '-f', str(P / 'rollback.agents.json')]
    assert subprocess.run(rollback_command + ['config', '--quiet'], capture_output=True).returncode == 0
    save(E, 'rendered-diff.json', {'environment_added': ADDED, 'environment_values_changed_existing': 0,
         'other_services_equal': True, 'non_environment_config_equal': True, 'mounts_equal': True,
         'rollback_private_path': str(P / 'rollback.agents.json'), 'rollback_sha256': sha(P / 'rollback.agents.json'),
         'rollback_command': rollback_command + ['up', '-d', '--no-deps', '--pull', 'never', '--no-build', 'agents'],
         'rollback_render_valid': True, 'rollback_executed': False, 'render_sha256': [digest(v) for v in configs]})
    save(E, 'frozen-prior.json', frozen_receipts())
    save(E, 'layer-inputs.json', {f'deploy/aisoc21/compose.{part}.yml': sha(S / f'deploy/aisoc21/compose.{part}.yml') for part in PARTS})
    save(E, 'prepared.json', {'layers': 22, 'only_four_new_env_values': True, 'new_mounts': 0,
         'new_images': 0, 'new_credentials': 0, 'runtime_source_changes': 0})
    print(json.dumps({'batch': B, 'prepared': True, 'new_env_values': 4, 'new_mounts': 0, 'rollback_saved': True}))


def deploy():
    assert (E / 'prepared.json').is_file() and not (E / 'deploy-started.json').exists()
    assert observation() == read(E / 'before.json')
    assert private_hashes() == read(E / 'private-input-hashes.json')
    assert all(sha(S / p) == h for p, h in read(E / 'layer-inputs.json').items())
    old = read(P / 'container-before.json')
    assert describe(inspect('socai2-agents-1')) == describe(old)
    desired = read(P / 'compose-desired.json')
    actual = json.loads(subprocess.check_output(compose() + ['config', '--format', 'json']))
    assert actual == desired
    save(E, 'deploy-started.json', {'before': describe(old), 'command': compose() + ['up', '-d', '--no-deps', '--pull', 'never', '--no-build', 'agents']})
    with (E / 'compose-up.log').open('x') as f:
        proc = subprocess.run(compose() + ['up', '-d', '--no-deps', '--pull', 'never', '--no-build', 'agents'], stdout=f, stderr=subprocess.STDOUT)
    (E / 'compose-up.log').chmod(0o600)
    assert proc.returncode == 0, 'Inspect checkpoint; do not replay deployment'
    for _ in range(50):
        now = inspect('socai2-agents-1')
        if now['State'].get('Health', {}).get('Status') == 'healthy':
            break
        time.sleep(1)
    assert now['State']['Health']['Status'] == 'healthy'
    assert now['Image'] == old['Image'] and now['Id'] != old['Id']
    new_env = env(now)
    for k, v in ADDED.items():
        assert new_env.pop(k) == v
    assert new_env == env(old)
    assert now['Mounts'] == old['Mounts'] and now['HostConfig'] == old['HostConfig']
    for k in ['User', 'Cmd', 'Entrypoint', 'WorkingDir', 'ExposedPorts', 'Healthcheck']:
        assert now['Config'].get(k) == old['Config'].get(k)
    save(E, 'deployed.json', {'before': describe(old), 'after': describe(now), 'same_image': True,
         'host_config_and_mounts_equal': True, 'exactly_four_env_values_added': True})
    print(json.dumps({'batch': B, 'deployed': True, 'only_recreated': 'agents', 'same_image': True}))


def verify():
    assert (E / 'deployed.json').is_file() and not (E / 'acceptance.json').exists()
    flags = container_json(FLAGS_CODE, payload=read(E / 'tenants.json'))
    assert all(flags[k] is False for k in ['worker', 'escalation', 'memory_writeback', 'approvals', 'alert_graph'])
    assert flags['uid'] == 10001 and flags['reader_maps_resolve']
    assert flags['source'] == read(E / 'resident-before.json')['source']
    save(E, 'resident-after.json', flags)
    ready = container_json("import urllib.request,json;print(json.dumps(json.load(urllib.request.urlopen('http://127.0.0.1:8084/readyz',timeout=5))))")
    assert ready['status'] == 'ready' and not ready.get('subscriptions')
    running = inspect('socai2-agents-1')
    logs = subprocess.run(['docker', 'logs', '--since', running['State']['StartedAt'], 'socai2-agents-1'],
                          capture_output=True, check=True).stdout
    # Log bodies stay out of evidence; only the named startup marker is counted.
    stderr = subprocess.run(['docker', 'logs', '--since', running['State']['StartedAt'], 'socai2-agents-1'],
                            capture_output=True, check=True).stderr
    combined = logs + stderr
    assert b'auto_triage_worker.enabled' not in combined
    save(E, 'startup.json', {'readyz': ready, 'registered_subscriptions': [],
         'worker_enabled_log_markers': 0, 'startup_logs_sha256': hashlib.sha256(combined).hexdigest()})
    assert container_json(SDK) == read(PREVIOUS / 'runtime.json')['sdk']
    save(E, 'sdk.json', container_json(SDK))
    tls = container_json(TLS_CODE)
    assert tls['uid'] == 10001 and tls['ca_sha256'] == sha(R / 'certificates/socai2-ca.crt')
    save(E, 'tls.json', tls)
    offsets = container_json(OFFSET_CODE)
    assert offsets == read(E / 'offsets-before.json')
    save(E, 'offsets-after.json', offsets)
    api_source = container_json("from pathlib import Path;import hashlib,json;print(json.dumps({'services/api/app/'+str(p.relative_to('/app/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/app').rglob('*.py')}))", service='api')
    assert api_source == read(PREVIOUS / 'runtime.json')['api_source']
    assert all(sha(S / p) == h for p, h in {**flags['source'], **api_source}.items())
    save(E, 'api-source.json', api_source)
    before, after = read(E / 'before.json'), observation()
    old_agents = before['environment']['containers'].pop('socai2-agents-1')
    new_agents = after['environment']['containers'].pop('socai2-agents-1')
    assert before == after
    assert old_agents['image'] == new_agents['image'] and old_agents['id'] != new_agents['id']
    after['environment']['containers']['socai2-agents-1'] = new_agents
    save(E, 'after.json', after)
    assert private_hashes() == read(E / 'private-input-hashes.json')
    assert frozen_receipts() == read(E / 'frozen-prior.json')
    result = {'batch': B, 'config_bounded_accepted': True, 'compose_layers': 22, 'runtime_source_layers': 19,
         'new_environment_values': 4, 'explicit_worker_disabled_in_overlay': True, 'new_mounts': 0,
         'image_changed': False, 'agents_recreates': 1, 'other_containers_preserved': 35, 'volumes_preserved': 18,
         'runtime_source_counts': {'agents': len(flags['source']), 'api': len(api_source)},
         'all_14_material_tables_preserved': True, 'reader_keys_preserved': 10, 'budget_rows_preserved': 5,
         'unconfirmed_reservations_preserved': 3, 'reserved_admission_units': 100000, 'upstream_migrations': 134,
         'six_group_offsets_unchanged': True, 'a_denied_backlog': 'offset0/end1',
         'ssl_chain_and_hostname_verified': True, 'wrong_hostname_rejected': True, 'sdk_unchanged': True,
         'worker_enabled': False, 'approval_proposal_guard': False, 'real_models': 0, 'new_messages': 0,
         'offset_commits': 0, 'new_credentials': 0, 'schema_changes': 0, 'rollback_executed': False,
         'model_quality_retested': False, 'full_worker_admission_accepted': False}
    save(E, 'acceptance.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    os.umask(0o077)
    assert sys.argv[1:] in [['prepare'], ['deploy'], ['verify']]
    globals()[sys.argv[1]]()
