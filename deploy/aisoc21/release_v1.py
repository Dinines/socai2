#!/usr/bin/env python3
"""Scoped v1 operator, run on 21 beside the reviewed plan and overlays.

Never prints resolved Compose configuration, environment values or credentials.
Each mutation is a separate explicit command; offsets are initialized once.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path('/opt/sting-aisoc-socai2')
HERE = Path(__file__).resolve().parent
PRIVATE = ROOT / 'private/release-v1-20261022'
PLAN = json.loads((HERE / 'release-v1-plan.json').read_text())
LAYERS = '''services embedding gateway investigation correlation-2a identity-2a risk-2b policy-2b ioc-2c context-2c suppression-3a risk-score-3a org-memory-3a tenant-skill-3a kb-read-3a dispositions-3a identity-read-3a triage-durability-3a triage-recovery-3a triage-request-3a triage-budget-3a triage-admission-config-3a fusion-delivery-c01 triage-material-c02 triage-reasoning-c03 triage-authorization-c03 triage-detection-validity-c03 triage-review-only-c03 integrity full-support ueba enrichment threatintel'''.split()


def run(argv, stdin=None):
    r = subprocess.run(argv, input=stdin, text=True, capture_output=True)
    if r.returncode:
        # stderr may contain resolved credentials or database parameters.
        failure = HERE / 'operator-failure.stderr'
        fd = os.open(failure, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(r.stderr)
        raise RuntimeError('Command failed: ' + ' '.join(argv[:3]) + f' (exit {r.returncode}); inspect privately on 21')
    return r.stdout


def inspect(name):
    return json.loads(run(['docker', 'inspect', f'socai2-{name}-1']))[0]


def env_of(container):
    return dict(item.split('=', 1) for item in container['Config']['Env'] if '=' in item)


def model_hash(env):
    selected = {k: v for k, v in env.items() if 'MODEL' in k or k.startswith(('OPENAI_', 'LITELLM_', 'AISOC_LLM_', 'AISOC_INVESTIGATION_MAX', 'AISOC_INVESTIGATION_TIMEOUT'))}
    return hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest()


def compose(rollback=False):
    args = ['docker', 'compose', '--project-directory', str(ROOT), '-p', 'socai2']
    for layer in LAYERS:
        args += ['-f', str(ROOT / f'source/deploy/aisoc21/compose.{layer}.yml')]
    args += ['-f', str(HERE / 'compose.release-v1.yml')]
    if rollback:
        args += ['-f', str(HERE / 'compose.release-v1-rollback.yml')]
    return args


def save_private(name, value, uid=0):
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(PRIVATE, 0o700)
    path = PRIVATE / name
    # No secret file may be a symlink or be silently overwritten.
    if path.exists() or path.is_symlink():
        raise RuntimeError(f'Private file already exists: {name}')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    os.chown(path, uid, uid)


def inner(code, payload=None):
    prefix = 'PAYLOAD = ' + repr(payload) + '\n'
    return json.loads(run(['docker', 'exec', '-i', 'socai2-agents-1', 'python', '-B', '-'], prefix + code))


def preview():
    rendered = json.loads(run(compose() + ['config', '--format', 'json']))
    result = {}
    for name in ('api', 'agents'):
        old = inspect(name)
        oldenv = env_of(old)
        new = rendered['services'][name]
        newenv = {k: str(v) for k, v in new['environment'].items()}
        # Image-baked ENV is absent from Compose. Compare configured keys only.
        changed = sorted(k for k, v in newenv.items() if oldenv.get(k) != v)
        allowed = {'AISOC_ATTACK_CONTEXT_ENABLED'} if name == 'api' else {
            'AISOC_AGENT_KAFKA_DISABLE', 'AISOC_AGENT_ESCALATE_TO_GRAPH', 'AISOC_TRIAGE_ADMISSION_PROFILE',
            'KAFKA_CONSUMER_GROUP', 'AISOC_TRIAGE_CONCURRENCY', 'AISOC_ATTACK_CONTEXT_ENABLED',
            'API_SERVICE_URL', 'ENRICHMENT_SERVICE_URL', 'AISOC_INVESTIGATION_CONTEXT_KEYS_FILE',
            'AISOC_INVESTIGATION_PREPARE_KEYS_FILE', 'AISOC_ORG_MEMORY_KEYS_FILE', 'AISOC_TENANT_SKILLS_KEYS_FILE',
            'AISOC_TRIAGE_KB_KEYS_FILE', 'AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE', 'AISOC_TRIAGE_IDENTITY_KEYS_FILE',
            'AISOC_TRIAGE_BUDGET_POLICY_FILE', 'AISOC_AGENT_RAISE_APPROVALS', 'AISOC_AGENT_MEMORY_WRITEBACK',
            'AISOC_AGENT_MEMORY_SUPPRESSION', 'AISOC_SIEM_WRITEBACK_ENABLED', 'AISOC_ALERT_PLAYBOOKS_ENABLED'}
        unexpected = sorted(set(changed) - allowed)
        assert not unexpected, 'Unexpected configured environment keys: ' + ','.join(unexpected)
        assert model_hash({**oldenv, **newenv}) == model_hash(oldenv), 'Model configuration changed'
        assert new['user'] == old['Config']['User'] == '10001:10001'
        assert new['read_only'] and old['HostConfig']['ReadonlyRootfs']
        assert 'ALL' in [str(x).upper() for x in new['cap_drop']]
        oldmounts = {(m['Source'], m['Destination'], not m['RW']) for m in old['Mounts'] if m['Type'] == 'bind'}
        newmounts = {(m['source'], m['target'], m.get('read_only', False)) for m in new['volumes'] if m['type'] == 'bind'}
        assert oldmounts <= newmounts, 'Existing bind mount changed or missing'
        if name == 'agents':
            assert new['stop_grace_period'] == '1m0s'
            assert model_hash(oldenv) == PLAN['model_configuration_sha256']
        result[name] = {'current_image': old['Image'], 'target_tag': new['image'], 'changed_environment_keys': changed,
                        'old_bind_count': len(oldmounts), 'new_bind_count': len(newmounts),
                        'model_configuration_sha256': model_hash(oldenv), 'security_and_old_mounts_preserved': True}
    return {'stage': 'preview', 'layers': len(LAYERS) + 1, 'services': result}


PREPARE = r'''
import asyncio, hashlib, json, os, secrets, uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
import asyncpg
async def main():
    plan=PAYLOAD
    tenant=uuid.UUID(plan['tenant_id'])
    maps={}
    for env,name in [('AISOC_ORG_MEMORY_KEYS_FILE','org-memory.json'),('AISOC_TENANT_SKILLS_KEYS_FILE','tenant-skills.json'),('AISOC_TRIAGE_KB_KEYS_FILE','kb.json'),('AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE','dispositions.json'),('AISOC_TRIAGE_IDENTITY_KEYS_FILE','identity.json')]:
        maps[name]=json.loads(Path(os.environ[env]).read_text())
        assert isinstance(maps[name],dict) and str(tenant) not in maps[name]
    reader='aisoc_'+secrets.token_hex(24)
    writer='aisoc_'+secrets.token_hex(24)
    expires=datetime.now(timezone.utc)+timedelta(days=30)
    conn=await asyncpg.connect(os.environ['DATABASE_URL'].replace('postgresql+asyncpg://','postgresql://'),timeout=10)
    try:
        async with conn.transaction():
            await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)",str(tenant))
            assert not await conn.fetchval('SELECT EXISTS(SELECT 1 FROM tenants WHERE id=$1 OR slug=$2)',tenant,plan['tenant_slug']), 'Production tenant already exists; do not duplicate or regenerate keys'
            await conn.execute('INSERT INTO tenants(id,name,slug,plan,is_active,settings,limits,created_at,updated_at) VALUES($1,$2,$3,\'starter\',true,\'{}\'::jsonb,\'{}\'::jsonb,now(),now())',tenant,plan['tenant_name'],plan['tenant_slug'])
            for name,token,scopes in [('v1 production context reader',reader,plan['reader_scopes']),('v1 production graph writer',writer,plan['writer_scopes'])]:
                await conn.execute('INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,is_active,expires_at,created_at) VALUES($1,$2,NULL,$3,$4,$5,$6::jsonb,true,$7,now())',uuid.uuid4(),tenant,name,token[:12],hashlib.sha256(token.encode()).hexdigest(),json.dumps(scopes),expires)
        for mapping in maps.values(): mapping[str(tenant)]=reader
        maps['context-readers.json']={str(tenant):reader}
        maps['writers.json']={str(tenant):writer}
        maps['budget.json']={'schema_version':1,'tenants':{str(tenant):plan['budget']}}
        print(json.dumps({'files':maps,'expires_at':expires.isoformat(),'tenant_id':str(tenant)}))
    finally: await conn.close()
asyncio.run(main())
'''


STARTPOINT = r'''
import asyncio,json,os
from datetime import datetime,timezone
from aiokafka import AIOKafkaConsumer, TopicPartition
from aiokafka.admin import AIOKafkaAdminClient
from app.workers.fused_alert_consumer import kafka_client_kwargs
async def main():
    admin=AIOKafkaAdminClient(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],**kafka_client_kwargs())
    await admin.start()
    try:
        metadata=await admin.describe_topics([PAYLOAD['fused_topic']])
        assert len(metadata)==1 and not metadata[0]['error_code'], 'Fused topic metadata unavailable'
        ps=[p['partition'] for p in metadata[0]['partitions']]
        assert ps, 'Fused topic missing'
    finally: await admin.close()
    parts=[TopicPartition(PAYLOAD['fused_topic'],p) for p in sorted(ps)]
    c=AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],group_id=PAYLOAD['consumer_group'],enable_auto_commit=False,**kafka_client_kwargs())
    c.assign(parts)
    await c.start()
    try:
        assert all([await c.committed(tp) is None for tp in parts]), 'Group already initialized; refuse any offset reset'
        ends=await c.end_offsets(parts)
        await c.commit(ends)
        assert all([await c.committed(tp)==ends[tp] for tp in parts])
        print(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'group':PAYLOAD['consumer_group'],'topic':PAYLOAD['fused_topic'],'start_offsets':{str(tp.partition):value for tp,value in ends.items()}}))
    finally: await c.stop()
asyncio.run(main())
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['preview', 'prepare', 'startpoint', 'deploy-api', 'deploy-agents', 'verify', 'rollback'])
    args = ap.parse_args()
    if args.command == 'preview':
        result = preview()
    elif args.command == 'prepare':
        preview()
        assert inspect('agents')['Image'] == PLAN['agents_parent']
        assert env_of(inspect('agents')).get('AISOC_AGENT_KAFKA_DISABLE') == '1'
        assert not PRIVATE.exists(), 'Private release directory already exists; inspect rather than repeat tenant creation'
        data = inner(PREPARE, PLAN)
        # Save one recovery copy first; no credentials are sent to the caller.
        save_private('preparation-recovery.json', data)
        for name, value in data['files'].items():
            save_private(name, value, 10001)
        os.chown(PRIVATE, 10001, 10001)
        result = {'stage': 'prepared', 'tenant_id': data['tenant_id'], 'expires_at': data['expires_at'], 'private_files': sorted(data['files']), 'credentials_printed': False}
    elif args.command == 'startpoint':
        assert (PRIVATE / 'budget.json').exists(), 'Prepare tenant first'
        assert env_of(inspect('agents')).get('AISOC_AGENT_KAFKA_DISABLE') == '1'
        assert not (PRIVATE / 'startpoint.json').exists(), 'Startpoint recorded; refuse offset reset'
        result = inner(STARTPOINT, PLAN)
        save_private('startpoint.json', result)
    elif args.command.startswith('deploy-'):
        preview()
        assert (PRIVATE / 'startpoint.json').exists(), 'Explicit start offsets required'
        for service in ('api', 'agents'):
            image = json.loads(run(['docker', 'image', 'inspect', f'socai2-{service}:v1.0.0']))[0]
            assert image['Id'] == PLAN[f'{service}_image'] and image['Architecture'] == 'amd64'
        service = args.command.split('-', 1)[1]
        if service == 'agents':
            assert inspect('api')['Image'] == PLAN['api_image']
            assert inspect('api')['State']['Health']['Status'] == 'healthy'
        run(compose() + ['up', '-d', '--no-deps', '--pull', 'never', '--no-build', service])
        result = {'stage': args.command, 'image': inspect(service)['Image']}
    elif args.command == 'verify':
        result = {'stage': 'verify', 'tenant_id': PLAN['tenant_id'], 'consumer_group': PLAN['consumer_group'], 'services': {}}
        for name in ('api', 'agents'):
            d=inspect(name)
            env=env_of(d)
            assert d['Image'] == PLAN[f'{name}_image']
            assert d['State']['Status']=='running' and d['State'].get('Health',{}).get('Status')=='healthy'
            port=18000 if name=='api' else 18004
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/readyz',timeout=5) as response:
                assert response.status==200
                readiness=json.load(response)
            if name == 'agents':
                assert env['AISOC_AGENT_KAFKA_DISABLE']=='0' and env['AISOC_AGENT_ESCALATE_TO_GRAPH']=='1'
                assert env['KAFKA_CONSUMER_GROUP']==PLAN['consumer_group']
                assert model_hash(env)==PLAN['model_configuration_sha256']
            result['services'][name]={'image':d['Image'],'status':d['State']['Status'],'health':d['State'].get('Health',{}).get('Status'),'readiness':readiness,'model_configuration_sha256':model_hash(env)}
    else:
        run(compose(rollback=True) + ['up', '-d', '--no-deps', '--pull', 'never', '--no-build', 'api', 'agents'])
        result = {'stage': 'rollback', 'worker_disabled': env_of(inspect('agents'))['AISOC_AGENT_KAFKA_DISABLE'] == '1'}
    print(json.dumps({'at': datetime.now(timezone.utc).isoformat(), **result}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
