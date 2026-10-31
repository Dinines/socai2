"""One-time provisioning of the two user-authorized development credentials.

Run on host21 only; defaults to dry run. Raw keys never leave its private file.
This does not dispatch investigation POSTs or change the completed r3 batch.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from uuid import uuid4

RELEASE = Path('/opt/sting-aisoc-socai2/investigation-v2/20261031-r3')
PRIVATE = Path('/opt/sting-aisoc-socai2/private/investigation-dev-keys.json')
NAME = 'investigation-development-20261031'
SCOPES = ['*']
TENANTS = {'53824f24-d1d4-5820-8147-f6cfda8a1247', 'f6a5c700-69b8-44fc-8238-609362fb1a9f'}


def main():
    if sys.argv[1:] != ['--execute']:
        print(json.dumps({'execute': False, 'tenants': sorted(TENANTS), 'scopes': SCOPES, 'valid_days': 365}))
        return
    os.umask(0o077)
    assert not PRIVATE.exists() and not PRIVATE.is_symlink()
    assert PRIVATE.parent.resolve() == Path('/opt/sting-aisoc-socai2/private')
    assert PRIVATE.parent.stat().st_mode & 0o777 == 0o700
    operator = RELEASE / 'retest/operate.py'
    assert hashlib.sha256(operator.read_bytes()).hexdigest() == '29a52a2b3b22952aab544abd31b6ba2689dff881b9a7ac6cc40a34c1064bfafa'
    spec = importlib.util.spec_from_file_location('batch_operator', operator)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pg = module.pg
    assert pg(f"SELECT count(*) FROM api_keys WHERE name='{NAME}';") == '0'
    plan = json.loads((RELEASE / 'retest/plan.json').read_text())
    steps = [s for s in plan['steps'] if s['stage'] == 'main']
    assert {s['tenant_id'] for s in steps} == TENANTS
    baseline_sql = f"SELECT COALESCE(json_agg(to_jsonb(k) ORDER BY id),'[]'::json) FROM (SELECT id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,is_active,expires_at,created_at FROM api_keys WHERE name<>'{NAME}') k;"
    baseline_hash = hashlib.sha256(pg(baseline_sql).encode()).hexdigest()
    planned = ','.join("'" + s['planned_run_id'] + "'" for s in plan['steps'])
    count_sql = f'SELECT count(*) FROM investigation_runs WHERE id IN ({planned});'
    before_count = pg(count_sql)
    assert before_count == '3'
    now = datetime.now(UTC)
    expiry = (now + timedelta(days=365)).isoformat()
    keys = {tenant: 'aisoc_' + secrets.token_hex(24) for tenant in sorted(TENANTS)}
    records = [{'id': str(uuid4()), 'tenant_id': tenant, 'name': NAME,
                'scopes': SCOPES, 'expires_at': expiry} for tenant in sorted(TENANTS)]
    ids = ','.join("'" + r['id'] + "'" for r in records)
    receipt = {'created_at': now.isoformat(),
               'authorization': '用户在一年有效、两个现有租户含生产租户的范围确认问题后回复：这不重要 目前权限无所谓的 给你完整的全部的',
               'valid_days': 365, 'keys': records, 'private_file': str(PRIVATE),
               'secret_in_receipt': False, 'http': [], 'investigation_posts': 0,
               'new_runs': 0, 'model_calls': 0, 'existing_keys_changed': False}
    receipt_path = Path(__file__).with_name('receipt.json')
    assert not receipt_path.exists()
    try:
        with PRIVATE.open('x', encoding='utf-8') as stream:
            json.dump(keys, stream)
        PRIVATE.chmod(0o600)
        statements = []
        for r in records:
            raw = keys[r['tenant_id']]
            statements.append("INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,is_active,expires_at,created_at) "
                f"VALUES ('{r['id']}','{r['tenant_id']}',NULL,'{NAME}','{raw[:12]}',"
                f"'{hashlib.sha256(raw.encode()).hexdigest()}','{json.dumps(SCOPES)}'::jsonb,true,'{expiry}',now());")
        pg('BEGIN;' + ''.join(statements) + 'COMMIT;')
        for tenant in sorted(TENANTS):
            step = next(s for s in steps if s['tenant_id'] == tenant)
            case_id = step['path'].split('/')[5]
            for path in (f'/api/v1/cases/{case_id}', f'/api/v2/investigation/cases/{case_id}/investigations?limit=1'):
                response = subprocess.run([sys.executable, '-B', str(RELEASE / 'scripts/investigation_client.py'),
                    'GET', path, '--timeout', '15'], capture_output=True, timeout=20,
                    env={**os.environ, 'AISOC_API_TOKEN': keys[tenant]})
                match = re.search(rb'HTTP (\d+)', response.stderr)
                status = int(match.group(1)) if match else None
                receipt['http'].append({'tenant_id': tenant, 'method': 'GET', 'path': path,
                    'status': status, 'response_sha256': hashlib.sha256(response.stdout).hexdigest()})
                assert status == 200 and response.returncode == 0, 'authenticated_read_failed'
        receipt['metadata'] = json.loads(pg(f"SELECT json_agg(json_build_object('id',id,'tenant_id',tenant_id,'scopes',scopes,'active',is_active,'expires_at',expires_at,'last_used_at',last_used_at) ORDER BY tenant_id) FROM api_keys WHERE id IN ({ids});"))
        assert len(receipt['metadata']) == 2
        assert all(r['active'] and r['scopes'] == SCOPES for r in receipt['metadata'])
        assert hashlib.sha256(pg(baseline_sql).encode()).hexdigest() == baseline_hash
        assert pg(count_sql) == before_count
        receipt['other_key_metadata_unchanged'] = True
        receipt['private_mode'] = oct(PRIVATE.stat().st_mode & 0o777)
        receipt['private_owner_uid'] = PRIVATE.stat().st_uid
        receipt['finished_at'] = datetime.now(UTC).isoformat()
        receipt['status'] = 'active_and_read_verified'
    except Exception as exc:
        pg(f"UPDATE api_keys SET is_active=false WHERE id IN ({ids}) AND name='{NAME}';")
        if PRIVATE.exists():
            PRIVATE.unlink()
        receipt['status'] = 'failed_and_revoked'
        receipt['error_type'] = type(exc).__name__
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        raise RuntimeError('credential_provision_failed_see_metadata_receipt') from None
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
