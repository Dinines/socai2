"""Read only the actual S01-r3 identities supplied by the independent test chat."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SUPPLY = ROOT / 'docs/operations/evidence/test-streaming-s01-ingress-20261115-02/readback'


def save(name, data):
    with (OUT / name).open('x') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def get_all(urls, name):
    code = '''import json,urllib.request,urllib.error
from datetime import datetime,timezone
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for url in URLS:
    result={"method":"GET","url":url,"at":datetime.now(timezone.utc).isoformat(),"authorization_header":False}
    try:
        with opener.open(url,timeout=30) as response:
            result.update(status=response.status,body=json.load(response))
    except urllib.error.HTTPError as error:
        result.update(status=error.code,body=error.read().decode())
    except Exception as error:
        result.update(status=None,error=type(error).__name__)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    if result["status"]!=200: break
'''.replace('URLS', repr(urls))
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
                             'sting-infra21', 'python3', '-'], input=code, text=True,
                            capture_output=True, timeout=180)
    receipts = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    save(name, {'ssh_exit': result.returncode, 'ssh_stderr': result.stderr, 'receipts': receipts})
    assert result.returncode == 0 and len(receipts) == len(urls), name
    assert all(r['status'] == 200 for r in receipts), name
    return {r['url']: r['body'] for r in receipts}


def normalized(value):
    if isinstance(value, dict):
        return {k: normalized(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalized(v) for v in value]
    if isinstance(value, str) and 'T' in value:
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).isoformat()
        except ValueError:
            pass
    return value


def main():
    mapping = json.loads((SUPPLY / 'identity-map.json').read_text())
    assert mapping['status'] == 'passed' and mapping['source'] == 'real_postgres_readback'
    assert mapping['postgres_snapshot_sha256'] == hashlib.sha256((SUPPLY / 'alerts-pg.json').read_bytes()).hexdigest()
    for name in ('context-readback.json', 'alerts-readback.json'):
        assert json.loads((SUPPLY / name).read_text())['status'] == 'passed'
    snapshot = json.loads((SUPPLY / 'alerts-pg.json').read_text())['rows']
    profile = json.loads((ROOT / 'deploy/http-service/streaming-20261115-01/profile.json').read_text())
    host = f"http://{profile['bind']}:{profile['port']}"
    base = host + '/api/v1/socai2'
    alerts = list(mapping['actual_mappings']['alerts'].values())
    incidents = list(mapping['actual_mappings']['incidents'].values())
    assert len(alerts) == 3 and len(incidents) == 1
    event = incidents[0]
    urls = []
    for a in alerts:
        root = f"{base}/alerts/{a['alert_id']}"
        urls += [root, root + '/materials/' + a['material_id'], root + '/records/sources',
                 root + '/records/source_artifacts', root + '/artifacts/' + a['artifact_id'],
                 root + '/records/incidents', root + '/analysis-tasks',
                 root + '/analysis-tasks/' + a['task_id'], root + '/analysis']
    incident_url = f"{base}/incidents/{event['incident_id']}"
    paged = [incident_url + '/records/members', incident_url + '/records/sources']
    urls += [incident_url, *(p + '?limit=2&offset=0' for p in paged),
             incident_url + '/analysis-tasks', incident_url + '/analysis-tasks/' + event['task_id'],
             incident_url + '/analysis']
    save('plan.json', {'batch_id': mapping['batch_id'], 'base_url': base,
                      'at': datetime.now(timezone.utc).isoformat(), 'method': 'GET', 'urls': urls,
                      'supplied_evidence': {name: hashlib.sha256((SUPPLY / name).read_bytes()).hexdigest()
                          for name in ('identity-map.json', 'alerts-pg.json', 'alerts-readback.json', 'context-readback.json')}})
    got = get_all(urls, 'get-01.json')
    next_urls = []
    for path in paged:
        first = got[path + '?limit=2&offset=0']
        assert first['total'] == 3 and len(first['items']) == 2 and first['next_offset'] == 2
        next_urls.append(path + '?limit=2&offset=' + str(first['next_offset']))
    got.update(get_all(next_urls, 'get-02.json'))
    for path in paged:
        second = got[path + '?limit=2&offset=2']
        assert second['total'] == 3 and len(second['items']) == 1 and second['next_offset'] is None
    members = [i for offset in (0, 2) for i in got[paged[0] + f'?limit=2&offset={offset}']['items']]
    sources = [i for offset in (0, 2) for i in got[paged[1] + f'?limit=2&offset={offset}']['items']]
    assert sorted(x['id'] for x in members) == sorted(event['members'])
    assert {x['source_event_id'] for x in sources} == {a['source_event_id'] for a in alerts}
    checked = []
    for kind, values in (('alerts', alerts), ('incidents', incidents)):
        for item in values:
            key = 'alert_id' if kind == 'alerts' else 'incident_id'
            identity = item[key]
            root = f'{base}/{kind}/{identity}'
            view = got[root]
            row = next(r for r in snapshot[kind] if r['id'] == identity)
            assert all(normalized(value) == normalized(row[k]) for k, value in view['facts'].items() if k in row)
            assert view['facts']['handling_status'] == 'new'
            tasks = got[root + '/analysis-tasks']
            assert tasks['subject_id'] == identity and tasks['total'] == 1 and tasks['next_cursor'] is None
            assert len(tasks['items']) == 1
            task = tasks['items'][0]
            assert task == got[root + '/analysis-tasks/' + item['task_id']]
            assert task['task_id'] == item['task_id'] and task['subject_id'] == identity
            assert host + task['status_url'] == root + '/analysis-tasks/' + item['task_id']
            assert task['status'] == 'accepted' and task['intent'] == 'initial' and task['source'] == 'ingress'
            assert task['started_at'] is None and task['latest_run_id'] is None and task['attempts'] == [] and task['results'] == []
            analysis = got[root + '/analysis']
            assert analysis['subject_id'] == identity and analysis['current_pointer_id'] is None
            assert analysis['current'] is None and analysis['entries'] == []
            if kind == 'alerts':
                material = next(r for r in snapshot['alert_materials'] if r['id'] == item['material_id'])
                content = got[root + '/materials/' + item['material_id']]
                assert content['metadata']['id'] == item['material_id'] and content['availability'] == 'available'
                assert content['content_text'] == material['raw_text']
                assert content['content_json'] == {k: material[k] for k in ('raw_json', 'ocsf_json', 'enrichment')}
                assert view['facts']['source_alert_id'] == item['source_alert_id'] and view['facts']['latest_material_id'] == item['material_id']
                refs = got[root + '/records/sources']
                assert refs['total'] == 1 and refs['next_offset'] is None and len(refs['items']) == 1
                assert refs['items'][0]['source_event_id'] == item['source_event_id']
                assert normalized(refs['items'][0]) == normalized(next(r for r in snapshot['alert_source_refs'] if r['alert_id'] == identity))
                relations = got[root + '/records/incidents']
                assert relations['total'] == 1 and [r['id'] for r in relations['items']] == [event['incident_id']]
                artifacts = got[root + '/records/source_artifacts']
                assert artifacts['total'] == 1 and [r['id'] for r in artifacts['items']] == [item['artifact_id']]
                assert host + artifacts['items'][0]['content_url'] == root + '/artifacts/' + item['artifact_id']
                original = got[root + '/artifacts/' + item['artifact_id']]
                artifact = next(r for r in snapshot['artifacts'] if r['id'] == item['artifact_id'])
                assert original['availability'] == 'available'
                assert original['content_json'] == artifact['content_json'] and original['content_text'] == artifact['content_text']
            else:
                assert view['derived']['member_count'] == 3
            checked.append({'kind': kind, 'id': identity, 'task_id': item['task_id'], 'status': 'accepted'})
    save('result.json', {'passed': True, 'batch_id': mapping['batch_id'], 'http_gets': len(got),
                         'authentication': 'none', 'subjects': checked, 'all_status_200': True,
                         'material_and_artifact_content_matches_test_snapshot': True,
                         'members_and_sources_pagination': {'pages_each': 2, 'rows_each': 3},
                         'writes': 0, 'database_queries': 0, 'dispatch_or_models_started': False,
                         'boundary': 'Real TCP ingress reads only. A/I execution, Case creation, real model chain remain pending.'})
    print(json.dumps({'passed': True, 'http_gets': len(got), 'alerts': 3, 'incidents': 1, 'accepted_tasks': 4}))


if __name__ == '__main__':
    main()
