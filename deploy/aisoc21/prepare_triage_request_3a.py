"""Freeze the current environment; mint read-only, expiring operation keys."""
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json
import os
import secrets
import subprocess
import urllib.error
import urllib.request
import uuid

from shared_1b import SharedBatch
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
from prepare_identity_read_3a import TABLES, rows, lit
from prepare_triage_admission_3a import READERS, sha
from finish_model_triage_3a import METRICS

R = Path('/opt/sting-aisoc-socai2')
B = '3a-triage-request-20261020'
E = R / 'evidence' / B
STATE = R / 'private/app-triage-request-3a.json'


def save(name, data):
    with (E / name).open('x') as f:
        json.dump(data, f, indent=2, default=str)
    (E / name).chmod(0o600)


def material(batch, table):
    if table != 'alerts':
        return rows(batch, table)
    return json.loads(batch.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM (" + MATERIAL_SQL + ') t;').stdout)


def readers(batch):
    result = {}
    for stem, scope in READERS:
        path = R / ('private/app-' + stem + '-3a.json')
        keyfile = R / ('private/' + stem + '-3a/keys.json')
        state = json.loads(path.read_text())
        metadata = {}
        for alias in ['reader_a', 'reader_b']:
            key = state['identities'][alias]
            value = json.loads(batch.pg('SET ROLE aisoc; SELECT row_to_json(t) FROM (SELECT id,tenant_id,is_active,scopes,expires_at FROM api_keys WHERE id=' + lit(key['key_id']) + ') t;').stdout)
            assert value['is_active'] and value['scopes'] == [scope] and value['tenant_id'] == key['tenant_id']
            metadata[alias] = value
        result[stem] = {'state_sha256': sha(path), 'keys_sha256': sha(keyfile), 'metadata': metadata}
    return result


SDK = '''import json
from app.llm.factory import make_chat_model
m=make_chat_model('triage',max_tokens=512,json_output=True)
print(json.dumps({'max_retries':m.max_retries,'request_timeout':m.request_timeout,
 'root_max_retries':m.root_async_client.max_retries,'root_timeout':m.root_async_client.timeout,
 'max_tokens':m.max_tokens,'legacy_max_tokens':m.extra_body.get('max_tokens')}))'''


def request(ids, path, alias='a'):
    headers = {'Authorization': 'Bearer ' + ids[alias]['key']} if alias else {}
    try:
        with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18000' + path, headers=headers), timeout=15) as res:
            return res.status, json.load(res)
    except urllib.error.HTTPError as exc:
        return exc.code, json.load(exc)


def main():
    os.umask(0o077)
    assert not STATE.exists() and not (E / 'environment-before.json').exists()
    batch = SharedBatch(R)
    old = json.loads((R / 'private/app-triage-recovery-3a.json').read_text())
    expected = json.loads((R / 'source/docs/operations/3a-triage-recovery.json').read_text())['postconditions']['images']
    env = snapshot()
    assert len(env['containers']) == 36 and len(env['volumes']) == 18
    assert all(env['containers']['socai2-' + name + '-1']['image'] == image for name, image in expected.items())
    save('environment-before.json', env)
    (E / 'scope-plan-before.md').write_bytes((R / 'source/docs/operations/3a-triage-request-plan.md').read_bytes())
    (E / 'scope-plan-before.md').chmod(0o600)
    counts = {}
    for table in ['alerts'] + TABLES:
        data = material(batch, table)
        hashes = [hashlib.sha256(row['material'].encode()).hexdigest() for row in data]
        save('prior-' + table + '.json', hashes)
        counts[table] = len(data)
    assert [counts[n] for n in ['alerts','investigation_runs','investigation_events','investigation_artifacts','aisoc_run_costs']] == [61,32,83,92,21]
    assert batch.pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip() == '134'
    credentials = readers(batch)
    save('reader-credentials-before.json', credentials)
    save('gateway-before.json', json.loads(subprocess.check_output(['docker','exec','socai2-litellm-1','python','-c',METRICS])))
    sdk = json.loads(subprocess.check_output(['docker','exec','socai2-agents-1','python','-c',SDK]))
    assert sdk['root_max_retries'] == 2 and sdk['root_timeout'] is None
    save('sdk-before.json', sdk)
    now = datetime.fromisoformat(batch.pg('SELECT now()::text;').stdout.strip())
    ns = uuid.uuid5(uuid.NAMESPACE_URL, 'socai2/' + B)
    ids = {}
    for alias in ['a','b','denied']:
        prior = old['identities']['a' if alias == 'denied' else alias]
        ids[alias] = {'tenant_id':prior['tenant_id'], 'user_id':prior['user_id'],
                      'key_id':str(uuid.uuid5(ns, alias)), 'key':'aisoc_' + secrets.token_hex(24),
                      'scopes':['alerts:read'] if alias == 'denied' else ['cases:read'],
                      'expires_at':(now + timedelta(hours=3)).isoformat()}
    source_inputs = json.loads((R / 'evidence/3a-triage-recovery-20261020/inputs.json').read_text())
    namespace = uuid.uuid5(uuid.NAMESPACE_URL,'tryaisoc.com/agents/auto-triage')
    runs = {alias:str(uuid.uuid5(namespace, value['alert_row_id'] + ':auto-triage-v1')) for alias,value in source_inputs.items()}
    state = {'batch':B,'identities':ids,'runs':runs,'images':expected,'reader_credentials':credentials,
             'counts_before':counts,'graph_config_sha256':sha(R / 'private/identity-graph-3a/config.json')}
    with STATE.open('x') as f:
        json.dump(state,f,indent=2)
    sql = 'SET ROLE aisoc; BEGIN; '
    for alias, item in ids.items():
        fields = [lit(item[k]) for k in ['key_id','tenant_id','user_id']]
        fields += [lit('socai2-' + B + '-' + alias),lit(item['key'][:12]),lit(hashlib.sha256(item['key'].encode()).hexdigest()),lit(json.dumps(item['scopes']))+'::jsonb',lit(item['expires_at'])]
        sql += 'INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES (' + ','.join(fields) + '); '
    batch.pg(sql + 'COMMIT;')
    checks = []
    for path, expected_status in [('/api/v1/investigations/' + runs['unknown'] + '/events',200),
                                 ('/api/v1/investigations/' + runs['unknown'] + '/events?since=-1',422)]:
        status, data = request(ids,path)
        checks.append({'path':path,'status':status,'expected':expected_status})
        assert status == expected_status
        if status == 200:
            assert data['next_seq'] == -1 and [e['seq'] for e in data['items']] == [-1]
    save('http-before.json',checks)
    save('prepared.json',{'counts':counts,'operation_keys':3,'new_readers':0,'real_model_calls':0,'normal_ingress':0,'broker_publishes':0})
    print(json.dumps({'batch':B,'prepared':True,'sdk':sdk,'http_checks':len(checks),'operation_keys':3}))


if __name__ == '__main__':
    main()
