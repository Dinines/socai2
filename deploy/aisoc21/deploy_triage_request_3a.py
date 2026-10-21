"""Update only the two tested services, retaining their exact env and mounts."""
from pathlib import Path
import hashlib
import json
import subprocess
import time

from prepare_triage_request_3a import R, E, STATE, SDK, save
from deploy_triage_recovery_3a import PARTS as PRIOR_PARTS, inspect, describe
from test_triage_request_3a import sources, sha

PARTS = PRIOR_PARTS + ['triage-request-3a']


def compose():
    command = ['docker','compose','--project-directory',str(R)]
    for part in PARTS:
        command += ['-f',str(R / f'source/deploy/aisoc21/compose.{part}.yml')]
    return command


def healthy(service):
    for _ in range(45):
        item = inspect('socai2-' + service + '-1')
        if item['State'].get('Health',{}).get('Status') == 'healthy':
            return item
        time.sleep(1)
    raise RuntimeError('Inspect deployment checkpoint; no blind rebuild or restart')


def verify_runtime_source(service):
    code = "from pathlib import Path;import json,hashlib;print(json.dumps({'services/" + service + "/app/'+str(p.relative_to('/app/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/app').rglob('*.py')}))"
    actual = json.loads(subprocess.check_output(['docker','exec','socai2-' + service + '-1','python','-c',code]))
    assert actual == sources(service), service
    return len(actual)


def resident():
    state = json.loads(STATE.read_text())
    code = '''import json,os,inspect
from app.context.organisation_memory import _credential
from app.workers.fused_alert_consumer import worker_enabled
from app.agents.auto_triage_agent import run_auto_triage,TRIAGE_REQUEST_TIMEOUT_SECONDS
assert os.getuid()==10001 and not worker_enabled() and TRIAGE_REQUEST_TIMEOUT_SECONDS==45.0
assert 'asyncio.timeout(TRIAGE_REQUEST_TIMEOUT_SECONDS)' in inspect.getsource(run_auto_triage)
variables=['AISOC_ORG_MEMORY_KEYS_FILE','AISOC_TENANT_SKILLS_KEYS_FILE','AISOC_TRIAGE_KB_KEYS_FILE','AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE','AISOC_TRIAGE_IDENTITY_KEYS_FILE']
tenants=json.loads(__import__('sys').argv[1])
assert all(_credential(t,keys_file_env=v) for t in tenants for v in variables)
print(json.dumps({'worker_enabled':False,'uid':os.getuid(),'reader_maps':5,'tenants':len(tenants),'whole_invocation_deadline_seconds':TRIAGE_REQUEST_TIMEOUT_SECONDS}))'''
    proof = json.loads(subprocess.check_output(['docker','exec','socai2-agents-1','python','-c',code,
                         json.dumps([state['identities'][n]['tenant_id'] for n in ['a','b']])]))
    sdk = json.loads(subprocess.check_output(['docker','exec','socai2-agents-1','python','-c',SDK]))
    assert sdk == {'max_retries':0,'request_timeout':45.0,'root_max_retries':0,'root_timeout':45.0,'max_tokens':512,'legacy_max_tokens':512}
    return {'resident':proof,'sdk':sdk}


def main():
    assert (E / 'prepared.json').is_file() and not (E / 'deployment-before.json').exists()
    state = json.loads(STATE.read_text())
    tests = {name:json.loads((E / f'tests-{name}-first.json').read_text()) for name in ['api','agents']}
    for name, test in tests.items():
        assert test['exit_code'] == test['failed'] == test['errors'] == 0
        assert sources(name) == test['tested_runtime_source_sha256']
        assert all(sha(R / 'source' / p) == h for p,h in test['test_input_sha256'].items())
    before = {n:describe(inspect('socai2-' + n + '-1')) for n in ['api','agents','fusion','actions']}
    assert all(before[n]['image'] == image for n,image in state['images'].items())
    parents = {'agents':'socai2-agents:triage-recovery-3a-20261020','api':'socai2-api:identity-read-3a-20261020'}
    assert all(inspect(tag)['Id'] == before[n]['image'] for n,tag in parents.items())
    assert len(PARTS) == 20
    subprocess.run(compose() + ['config','--quiet'],check=True,capture_output=True)
    save('deployment-before.json',before)
    built = {}
    for name in ['api','agents']:
        image = f'socai2-{name}:triage-request-3a-20261020'
        log = E / f'build-{name}.log'
        with log.open('x') as f:
            result = subprocess.run(['docker','build','--pull=false','-f',f'deploy/aisoc21/build/Dockerfile.{name}-triage-request-3a','-t',image,'.'],cwd=R / 'source',stdout=f,stderr=subprocess.STDOUT)
        log.chmod(0o600)
        assert result.returncode == 0, 'Inspect build log; do not replay deploy blindly'
        built[name] = inspect(image)['Id']
        save('built-' + name + '.json',{'image':built[name],'parent':before[name]['image'],'log_sha256':sha(log)})
        subprocess.run(compose() + ['up','-d','--no-deps','--pull','never',name],check=True,capture_output=True)
        after = healthy(name)
        desc = describe(after)
        assert desc['id'] != before[name]['id'] and desc['image'] == built[name]
        assert desc['env_sha256'] == before[name]['env_sha256']
        assert {m['Destination']:m for m in desc['mounts']} == {m['Destination']:m for m in before[name]['mounts']}
        assert after['HostConfig']['ReadonlyRootfs']
        source_count = verify_runtime_source(name)
        save('deployed-' + name + '.json',{'runtime':desc,'source_files_verified':source_count})
    for name in ['fusion','actions']:
        assert describe(inspect('socai2-' + name + '-1')) == before[name]
    proof = resident()
    result = {'images':built,'previous_images':{n:before[n]['image'] for n in built},
              'only_updated':['api','agents'],'compose_layers':20,'env_and_mounts_preserved':True,
              'source_matches_tests':True,'no_dependencies_or_schema_changed':True,**proof}
    save('deployment.json',result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
