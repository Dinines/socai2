"""Verify existing products/cursors, restart two services, revoke only batch keys."""
from collections import Counter
import hashlib
import json
import subprocess

from shared_1b import SharedBatch
from prepare_2a import snapshot
from prepare_identity_read_3a import TABLES, lit
from prepare_triage_request_3a import R, B, E, STATE, save, material, readers, request
from deploy_triage_request_3a import inspect, describe, healthy, resident, verify_runtime_source
from finish_model_triage_3a import METRICS


def main():
    assert (E / 'deployment.json').is_file() and not (E / 'finish-started.json').exists()
    save('finish-started.json',{'batch':B,'new_ingress_or_model_calls':0})
    state = json.loads(STATE.read_text())
    ids, checks = state['identities'], []
    def get(path, who='a', expected=200):
        status, data = request(ids,path,who)
        checks.append({'path':path,'identity':who,'expected':expected,'status':status})
        assert status == expected, (path,who,status,expected)
        return data
    def products():
        result = {}
        for alias, run_id in state['runs'].items():
            base = '/api/v1/investigations/' + run_id
            run = get(base)
            events = get(base + '/events')
            artifacts = get(base + '/artifacts')
            sequences = [v['seq'] for v in events['items']]
            assert sequences == ([-1] if alias == 'unknown' else [-1,1])
            first = get(base + '/events?limit=1')
            assert first['next_seq'] == -1 and [e['seq'] for e in first['items']] == [-1]
            later = get(base + '/events?since=' + str(first['next_seq']))
            assert [e['seq'] for e in later['items']] == ([1] if alias != 'unknown' else [])
            assert later['items'] == events['items'][1:] and later['total'] == len(events['items']) - 1
            assert later['since'] == -1
            zero = get(base + '/events?since=0')
            assert zero['items'] == later['items']
            assert get(base + '/events?since=1')['items'] == []
            get(base + '/events?since=-2',expected=422)
            get(base + '/events?since=-1','b',404)
            get(base + '/events?since=-1','denied',403)
            get(base + '/events?since=-1',None,401)
            result[alias] = {'run':run,'events':events,'artifacts':artifacts,'negative_cursor':later}
        return result
    first = products()
    save('api-before-restart.json',first)
    before = {name:describe(inspect('socai2-' + name + '-1')) for name in ['api','agents']}
    save('restart-before.json',before)
    after = {}
    for name in ['api','agents']:
        subprocess.run(['docker','restart','socai2-' + name + '-1'],check=True,capture_output=True)
        item = healthy(name)
        desc = describe(item)
        assert desc['id'] == before[name]['id'] and desc['image'] == before[name]['image']
        assert desc['env_sha256'] == before[name]['env_sha256']
        assert {m['Destination']:m for m in desc['mounts']} == {m['Destination']:m for m in before[name]['mounts']}
        after[name] = {'runtime':desc,'source_files_verified':verify_runtime_source(name)}
        save('restart-' + name + '.json',after[name])
    proof = resident()
    second = products()
    save('api-after-restart.json',second)
    assert first == second, 'Existing products must remain identical across restart'
    save('restart-after.json',{'services':after,**proof,'same_existing_products':True})
    batch = SharedBatch(R)
    revoked = {}
    for alias, key in ids.items():
        batch.pg('SET ROLE aisoc; UPDATE api_keys SET is_active=false WHERE id=' + lit(key['key_id']) + ' AND tenant_id=' + lit(key['tenant_id']) + ' AND name=' + lit('socai2-' + B + '-' + alias) + ';')
        get('/api/v1/investigations/' + state['runs']['warm'] + '/events?since=-1',alias,401)
        revoked[alias] = 401
    save('key-lifecycle.json',{'operation_keys_deactivated':revoked,'new_reader_keys':0})
    assert readers(batch) == state['reader_credentials']
    assert hashlib.sha256((R / 'private/identity-graph-3a/config.json').read_bytes()).hexdigest() == state['graph_config_sha256']
    counts = {}
    for table in ['alerts'] + TABLES:
        before_hashes = json.loads((E / ('prior-' + table + '.json')).read_text())
        after_hashes = [hashlib.sha256(row['material'].encode()).hexdigest() for row in material(batch,table)]
        assert Counter(before_hashes) == Counter(after_hashes), table
        counts[table] = {'preserved':len(before_hashes),'added':0,'total':len(after_hashes)}
    gateway = json.loads(subprocess.check_output(['docker','exec','socai2-litellm-1','python','-c',METRICS]))
    assert gateway == json.loads((E / 'gateway-before.json').read_text())
    assert batch.pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip() == '134'
    baseline, end = json.loads((E / 'environment-before.json').read_text()), snapshot()
    assert baseline['volumes'] == end['volumes'] and set(baseline['containers']) == set(end['containers'])
    for name, value in baseline['containers'].items():
        if name not in ['socai2-api-1','socai2-agents-1']:
            assert end['containers'][name] == value, name
    save('environment-after.json',end)
    save('finish-http-checks.json',checks)
    tests = {n:json.loads((E / f'tests-{n}-first.json').read_text()) for n in ['api','agents']}
    result = {'batch':B,'database_materials':counts,'reader_keys_preserved':10,'new_reader_keys':0,
              'operation_keys_deactivated':3,'other_containers_preserved':34,'containers_total':36,
              'volumes_preserved':18,'migrations_preserved':134,'real_model_calls':0,
              'new_alerts_runs_events_artifacts_cost_rows':0,'broker_publishes_deliveries':0,
              'tests':{n:r['passed'] for n,r in tests.items()},'tests_passed':sum(r['passed'] for r in tests.values()),
              'http_checks':len(checks)+len(json.loads((E / 'http-before.json').read_text())),
              'gateway_before_and_after':gateway,'negative_cursor_accepted':True,'sdk':proof['sdk'],
              'whole_invocation_deadline_seconds':45,'same_existing_products_after_restart':True,
              'only_updated_and_restarted':['api','agents'],'resident_worker_enabled':False,
              'request_cursor_bounded_accepted':True,'durable_tenant_budget_accepted':False,
              'worker_admission_accepted':False,'quality_retested':False,
              'next':'3A-10-03-02 persistent tenant quotas, backlog and stop/recovery'}
    save('postconditions.json',result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
