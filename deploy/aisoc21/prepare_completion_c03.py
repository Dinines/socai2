"""Freeze C03-01's zero-business-write scope before applying prompt and lock."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

from configure_triage_admission_3a import observation, private_hashes, inspect, describe, save, container_json, FLAGS_CODE, OFFSET_CODE

R = Path('/opt/sting-aisoc-socai2')
S = R / 'source'
E = R / 'evidence/c03-triage-reasoning-20261021'
P = R / 'private/completion-c03'
FILES = ['services/agents/app/llm/prompt_registry.py', 'services/agents/app/llm/prompts.lock.json']
PARENT = 'sha256:c9cf8920a8ac2a601acf6f8cab5033f448f22a4aec103f43e94ddfd707ce98d5'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    os.umask(0o077)
    E.mkdir(mode=0o700, exist_ok=False)
    P.mkdir(mode=0o700, exist_ok=False)
    before = observation()
    previous = R / 'evidence/c02-triage-material-cache-stop-20261020'
    assert json.loads((previous / 'closeout-independent-audit.json').read_text())['accepted']
    assert before == json.loads((previous / 'after.json').read_text())
    save(E, 'before.json', before)
    save(E, 'private-input-hashes.json', private_hashes())
    old = inspect('socai2-agents-1')
    assert old['Image'] == PARENT and old['State']['Health']['Status'] == 'healthy'
    assert old['Config']['StopTimeout'] == 60
    save(P, 'agents-container-before.json', old)
    save(E, 'agents-before.json', describe(old))
    plan = S / 'docs/operations/c03-triage-reasoning-plan.md'
    (E / 'scope-before.md').write_bytes(plan.read_bytes())
    (E / 'scope-before.md').chmod(0o600)
    limits = {'real_models': 0, 'new_broker_send_attempts': 0, 'new_broker_record_deliveries': 0,
              'broker_offset_commits': 0, 'business_pg_writes': 0, 'new_tenants': 0,
              'new_keys': 0, 'new_readers': 0, 'new_business_rows': 0, 'ddl': 0,
              'shared_service_restarts': 0, 'only_recreate': 'agents', 'max_recreates': 1,
              'test_timeout_seconds': 300, 'model_transport': 'offline synthetic httpx.MockTransport'}
    save(E, 'limits.json', limits)
    state = json.loads((R / 'private/app-triage-budget-3a.json').read_text())
    tenants = [state['identities'][a]['tenant_id'] for a in ['a', 'b']]
    flags = container_json(FLAGS_CODE, payload=tenants)
    assert flags['uid'] == 10001 and flags['reader_maps_resolve']
    assert all(flags[k] is False for k in ['worker', 'escalation', 'memory_writeback', 'approvals', 'alert_graph'])
    local = {str(p.relative_to(S)): sha(p) for p in (S / 'services/agents/app').rglob('*.py')}
    assert local == flags['source'] and len(local) == 184
    save(E, 'resident-before.json', flags)
    save(E, 'budget-group-offsets-before.json', container_json(OFFSET_CODE))
    originals = E / 'parent-sources'
    for name in FILES:
        path = originals / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        subprocess.run(['docker', 'cp', 'socai2-agents-1:/app/app/' + name.removeprefix('services/agents/app/'), str(path)],
                       check=True, capture_output=True)
        path.chmod(0o600)
        assert sha(path) == sha(S / name)
    save(E, 'prepared.json', {'batch': E.name, 'scope_sha256': sha(E / 'scope-before.md'),
         'parent_image': PARENT, 'parent_sources': {p: sha(S / p) for p in FILES},
         'full_parent_runtime_sources': local, 'limits': limits,
         'previous_change_closed': True, 'existing_business_data_unchanged': True})
    print(json.dumps({'batch': E.name, 'prepared': True, 'parent_sources': 184,
                      'new_keys': 0, 'new_data': 0, 'real_models': 0, 'runtime_changed': False}))


if __name__ == '__main__':
    main()
