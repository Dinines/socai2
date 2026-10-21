"""Freeze C01 state and create only two expiring keys for marked ingress.

No source deployment, shared service restart or existing-data mutation.
"""
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import os
import secrets
import subprocess
import uuid

from shared_1b import SharedBatch
from configure_triage_admission_3a import observation, inspect, describe, env, private_hashes
from prepare_identity_read_3a import lit

R = Path('/opt/sting-aisoc-socai2')
S = R / 'source'
B = 'c01-fusion-delivery-20261020'
E = R / 'evidence' / B
P = R / 'private/completion-c01'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(directory, name, value):
    with (directory / name).open('x') as f:
        json.dump(value, f, indent=2, default=str)
        f.write('\n')
    (directory / name).chmod(0o600)


def main():
    os.umask(0o077)
    E.mkdir(mode=0o700, exist_ok=False)
    P.mkdir(mode=0o700, exist_ok=False)
    before = observation()
    assert before == json.loads((R / 'evidence/3a-triage-admission-config-20261020/after.json').read_text())
    save(E, 'before.json', before)
    save(E, 'private-input-hashes.json', private_hashes())
    old = inspect('socai2-fusion-1')
    assert old['Image'] == 'sha256:9be177b961edd6bbc0951dbb92966aaccb53c81438f82e5677ede6ae47f2d07b'
    assert old['State']['Health']['Status'] == 'healthy'
    save(P, 'fusion-container-before.json', old)
    save(E, 'fusion-before.json', describe(old))
    code = "from pathlib import Path;import hashlib,json;print(json.dumps({'services/fusion/app/'+str(p.relative_to('/app/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/app').rglob('*.py')}))"
    parent_source = json.loads(subprocess.check_output(['docker', 'exec', 'socai2-fusion-1', 'python', '-c', code]))
    save(E, 'parent-source.json', parent_source)
    plan = S / 'docs/operations/c01-fusion-delivery-plan.md'
    (E / 'scope-before.md').write_bytes(plan.read_bytes())
    (E / 'scope-before.md').chmod(0o600)
    limits = {'new_alert_rows': 6, 'broker_test_publishes': 12, 'test_deliveries': 20,
              'real_models': 0, 'operation_keys': 2, 'new_test_topics': 12,
              'new_test_groups': 6, 'shared_service_restarts': 0, 'new_schema_objects': 0}
    save(E, 'limits.json', limits)
    batch = SharedBatch(R)
    prior = json.loads((R / 'private/app-triage-budget-3a.json').read_text())
    now = datetime.fromisoformat(batch.pg('SELECT now()::text;').stdout.strip())
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, 'socai2/' + B)
    identities = {}
    for alias in ['a', 'b']:
        inherited = prior['identities'][alias]
        identities[alias] = {'tenant_id': inherited['tenant_id'], 'user_id': inherited['user_id'],
                             'key_id': str(uuid.uuid5(namespace, 'key/' + alias)),
                             'key': 'aisoc_' + secrets.token_hex(24),
                             'scopes': ['alerts:read', 'alerts:write'],
                             'expires_at': (now + timedelta(hours=3)).isoformat()}
    state = {'batch': B, 'identities': identities, 'limits': limits, 'parent_image': old['Image']}
    save(P, 'state.json', state)
    sql = 'SET ROLE aisoc; BEGIN; '
    for alias, key in identities.items():
        fields = [lit(key[k]) for k in ['key_id', 'tenant_id', 'user_id']]
        fields += [lit('socai2-' + B + '-' + alias), lit(key['key'][:12]),
                   lit(hashlib.sha256(key['key'].encode()).hexdigest()),
                   lit(json.dumps(key['scopes'])) + '::jsonb', lit(key['expires_at'])]
        sql += 'INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES (' + ','.join(fields) + '); '
    batch.pg(sql + 'COMMIT;')
    values = env(old)
    # Dedicated probe containers use existing Fusion credentials and transport;
    # they cannot start a model or the Agents consumer.
    with (P / 'probe.env').open('x') as f:
        f.write(''.join(k + '=' + v + '\n' for k, v in values.items()))
    (P / 'probe.env').chmod(0o600)
    safe_ids = {a: {k: v for k, v in value.items() if k != 'key'} for a, value in identities.items()}
    save(E, 'prepared.json', {'batch': B, 'scope_before_sha256': sha(E / 'scope-before.md'),
         'operation_identities': safe_ids, 'runtime_unchanged': True, 'private_state_path': str(P / 'state.json'),
         'old_14_table_material_preserved': True, 'real_models': 0})
    # Only synthetic evidence goes in this directory. Permit the resident UID
    # to write probe products without adding capabilities or copying secrets.
    os.chown(E, 10001, 10001)
    print(json.dumps({'batch': B, 'prepared': True, 'operation_keys': 2, 'runtime_changes': 0, 'real_models': 0}))


if __name__ == '__main__':
    main()
