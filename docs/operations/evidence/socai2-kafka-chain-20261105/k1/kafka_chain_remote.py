"""Fixed k1 real Kafka and HTTP acceptance. No production consumer/config changes."""
import argparse
import importlib.util
import json
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import NAMESPACE_URL, UUID, uuid5

HERE = Path(__file__).resolve().parent
RELEASE = Path('/opt/sting-aisoc-socai2/releases/next-20261104-n14')
spec = importlib.util.spec_from_file_location('service', RELEASE / 'next_service_remote.py')
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)
PLAN = json.loads((HERE / 'plan.json').read_text())
IDENTITY = json.loads((service.PRIVATE / 'identity.json').read_text())
assert PLAN['tenant_id'] == IDENTITY['tenant_id'] == service.TENANT


def uid(label):
    return str(uuid5(NAMESPACE_URL, 'socai2-kafka-k1-20261105:' + label))


def save(name, value):
    path = HERE / (name + '.json')
    assert not path.exists(), 'fixed phase already attempted; inspect, never retry'
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')
    path.chmod(0o600)


def read(name):
    return json.loads((HERE / (name + '.json')).read_text())


def http(label, method, path, body=None):
    assert path.startswith('/api/v1/socai2/')
    save(label + '-request', {'method': method, 'path': path, 'body': body})
    req = urllib.request.Request('http://127.0.0.1:18020' + path,
        data=json.dumps(body).encode() if body is not None else None, method=method,
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + IDENTITY['api_key']})
    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            status, raw = response.status, response.read().decode()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read().decode()
    result = {'status': status, 'body': json.loads(raw)}
    save(label + '-response', result)
    print(json.dumps({'call': label, 'status': status}), flush=True)
    return result


def ingest():
    save('ingest-intent', {'model_calls': 0, 'topics': PLAN['topic_prefix'], 'group': PLAN['group'],
        'protected_before': service.protected_model_config()})
    original = service.environment('socai2-fusion-1')
    independent = service.environment(service.NEW)
    env = {k: v for k, v in original.items() if k.startswith('KAFKA_')}
    prefix = PLAN['topic_prefix']
    redis = urlsplit(independent['REDIS_URL'])
    env.update({'KAFKA_TOPIC_ALERTS_RAW': prefix + '.alerts.raw', 'KAFKA_TOPIC_RAW_EVENTS': prefix + '.raw_events',
        'KAFKA_TOPIC_ALERTS_FUSED': prefix + '.alerts.fused', 'KAFKA_CONSUMER_GROUP': PLAN['group'],
        'KAFKA_SSL_CAFILE': '/run/certs/ca.crt', 'DATABASE_URL': independent['DATABASE_URL'],
        'REDIS_URL': urlunsplit(redis._replace(path='/13')), 'ENVIRONMENT': 'production',
        'AISOC_ALERT_STORE_SCHEMA': 'socai2', 'AISOC_EVENT_PROMOTION_ENABLED': 'false',
        'AISOC_UEBA_FUSION_ENABLED': 'false', 'AISOC_DETECTION_ENGINE_ENABLED': 'false',
        'AISOC_WINDOWED_DETECTION_ENABLED': 'false', 'CLICKHOUSE_DATABASE': service.LAKE,
        'CLICKHOUSE_HOST': original['CLICKHOUSE_HOST'], 'CLICKHOUSE_PORT': original['CLICKHOUSE_PORT'],
        'CLICKHOUSE_USER': original['CLICKHOUSE_USER'], 'CLICKHOUSE_PASSWORD': original['CLICKHOUSE_PASSWORD']})
    assert service.DATABASE in env['DATABASE_URL'] and env['CLICKHOUSE_DATABASE'] == 'socai2_next_validation'
    files = {p.relative_to(RELEASE / 'fusion').as_posix(): p.read_text() for p in (RELEASE / 'fusion/app').rglob('*.py')}
    packet = {'environment': env, 'files': files, 'cases': PLAN['cases']}
    output = service.command(['docker', 'exec', '-i', service.NEW, 'python', '-c',
        (HERE / 'kafka_chain_child.py').read_text()], body=json.dumps(packet).encode(), timeout=180)
    records = [json.loads(line.removeprefix('K1_RESULT=')) for line in output.splitlines() if line.startswith('K1_RESULT=')]
    assert len(records) == 1, 'no worker receipt'
    result = records[0]
    save('ingest-result', result)
    save('ingest-protection', {'unchanged': service.protected_model_config() == read('ingest-intent')['protected_before']})
    print(json.dumps({'ingested': result['passed'], 'fused': len(result.get('fused', [])),
        'lake': result.get('metrics', {}).get('laked'), 'error_type': result.get('error_type'),
        'frames': result.get('frames')}), flush=True)


def subjects(case):
    result = read('ingest-result')
    assert result['passed'], 'Kafka phase must pass first'
    fused = {x['value']['alert']['source_alert_id']: x['value'] for x in result['fused']}
    values = [fused[a['source_alert_id']] for a in case['alerts']]
    ids = [v['alert_row_id'] for v in values]
    incident_ids = list(dict.fromkeys(v['incident_id'] for v in values))
    assert len(incident_ids) == 1, 'fixture members must really correlate'
    return ids, incident_ids[0]


def check_model(case):
    env = service.environment(service.NEW)
    expected = 'deepseek-flash' if case['backend'] == 'deepseek' else 'aisoc-investigation'
    assert env['OPENAI_MODEL'] == expected
    return {'model': expected, 'protocol': env.get('SOCAI2_MODEL_PROTOCOL', 'chat_completions')}


def first(case):
    key = case['key']
    save(key + '-intent', {**check_model(case), 'max_model_calls': 7, 'max_runs': 4, 'retries': 0})
    aids, incident = subjects(case)
    for i, aid in enumerate(aids):
        http(key + '-A' + str(i), 'POST', f'/api/v1/socai2/alerts/{aid}/analyze', {'operation_key': uid(key + '-A' + str(i))})
    http(key + '-I', 'POST', f'/api/v1/socai2/incidents/{incident}/diagnose', {'operation_key': uid(key + '-I')})
    created = http(key + '-case', 'POST', '/api/v1/socai2/cases', {'operation_key': uid(key + '-case'),
        'title': 'Endpoint activity review', 'incident_ids': [incident], 'alert_ids': []})
    if created['status'] != 200:
        return
    body = created['body']
    start(case, 'C', body['case_id'], body['pending_run_id'], body['scope_revision'])


def start(case, label, cid, rid, revision, previous=None):
    label = case['key'] + '-' + label
    result = http(label, 'POST', f'/api/v1/socai2/cases/{cid}/runs/{rid}/start',
        {'operation_key': uid(label), 'expected_scope_revision': revision,
         'window_start': case['window_start'], 'window_end': case['window_end'], 'comparison_result_id': previous})
    if result['status'] == 200:
        for i, result_id in enumerate(result['body']['result_ids']):
            http(label + '-result-' + str(i), 'GET', f'/api/v1/socai2/cases/{cid}/results/{result_id}')
    http(label + '-case-read', 'GET', f'/api/v1/socai2/cases/{cid}')
    http(label + '-history', 'GET', f'/api/v1/socai2/cases/{cid}/history')


def second(case):
    assert case['scenario'] == 'maintenance'
    key = case['key']
    save(key + '-second-intent', {**check_model(case), 'max_model_calls': 4, 'max_runs': 1, 'retries': 0})
    created = read(key + '-case-response')['body']
    cid, revision = created['case_id'], created['scope_revision']
    aids, _ = subjects(case)
    previous = read(key + '-C-response')
    previous_ids = previous['body'].get('result_ids', []) if previous['status'] == 200 else []
    scope = {'kind': 'selected_alerts', 'alert_ids': [aids[0]], 'object_keys': [],
        'window_start': case['window_start'], 'window_end': case['window_end'],
        'limitations': ['Confirms only process-task authorization; network attribution and completion are unconfirmed.']}
    result = http(key + '-H', 'POST', f'/api/v1/socai2/cases/{cid}/tasks', {'operation_key': uid(key + '-H'),
        'expected_scope_revision': revision, 'title': 'Confirm maintenance authorization', 'state': 'completed',
        'assignee_id': service.USER, 'result_text': 'I authorized inventory.ps1 on k1-endpoint-0 during this window. I have not confirmed successful script completion or which process made the network connection.',
        'result_scope': scope})
    assert result['status'] == 200
    pending = http(key + '-prepare', 'POST', f'/api/v1/socai2/cases/{cid}/baseline/prepare',
        {'operation_key': uid(key + '-prepare'), 'expected_scope_revision': revision})
    assert pending['status'] == 200
    start(case, 'C2', cid, pending['body']['pending_run_id'], revision, previous_ids[0] if previous_ids else None)


def export():
    # Strict list of new synthetic identities; no user/credential/settings rows.
    aids, incidents = [], []
    for case in PLAN['cases']:
        a, i = subjects(case)
        aids.extend(a)
        incidents.append(i)
    def sql_ids(values):
        return ','.join(service.literal(str(UUID(v))) for v in values)
    case_ids = [str(uuid5(UUID(service.TENANT), 'socai2.case.create:' + uid(c['key'] + '-case'))) for c in PLAN['cases']]
    stage_ids = [str(uuid5(UUID(service.TENANT), 'socai2.stage:' + uid(c['key'] + '-' + label)))
        for c in PLAN['cases'] for label in ('A0', 'A1', 'I')]
    runs = 'SELECT id FROM socai2.runs WHERE tenant_id=' + service.literal(service.TENANT) + ' AND (case_id IN (' + sql_ids(case_ids) + ') OR id IN (' + sql_ids(stage_ids) + '))'
    clauses = {t: 'id IN (' + sql_ids(aids) + ')' if t == 'alerts' else 'alert_id IN (' + sql_ids(aids) + ')'
        for t in ('alerts', 'alert_materials', 'alert_source_refs', 'alert_objects', 'alert_assessments')}
    clauses.update({t: ('id' if t == 'incidents' else 'incident_id') + ' IN (' + sql_ids(incidents) + ')'
        for t in ('incidents', 'incident_alerts', 'incident_diagnoses')})
    clauses.update({t: ('id' if t == 'cases' else 'case_id') + ' IN (' + sql_ids(case_ids) + ')'
        for t in ('cases', 'case_alerts', 'case_incidents', 'results', 'result_members', 'tasks', 'task_revisions',
                  'case_assessments', 'case_assessment_sources', 'case_assessment_members')})
    clauses.update({t: ('id' if t == 'runs' else 'run_id') + ' IN (' + runs + ')' for t in ('runs', 'run_members', 'run_steps')})
    clauses['artifacts'] = '(run_id IN (' + runs + ') OR (run_id IS NULL AND alert_id IN (' + sql_ids(aids) + ')))'
    clauses['activities'] = 'subject_case_id IN (' + sql_ids(case_ids) + ')'
    data = {table: json.loads(service.pg(service.DATABASE, "SELECT COALESCE(jsonb_agg(to_jsonb(t)),'[]'::jsonb) FROM socai2." + table +
        ' t WHERE tenant_id=' + service.literal(service.TENANT) + ' AND (' + clause + ')')) for table, clause in clauses.items()}
    # Separate immutable snapshots permit inspection during long model phases.
    from datetime import UTC, datetime
    stamp = datetime.now(UTC).strftime('%Y%m%dT%H%M%S')
    save('database-' + stamp, data)
    files = {p.name: json.loads(p.read_text()) for p in HERE.glob('*.json') if p.name != 'manifest.json'}
    print(json.dumps({'export': files, 'counts': {t: len(rows) for t, rows in data.items()},
        'protected_unchanged': service.protected_model_config() == read('ingest-intent')['protected_before']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['ingest', 'first', 'second', 'export'])
    parser.add_argument('--case')
    args = parser.parse_args()
    if args.phase in {'first', 'second'}:
        case = next(c for c in PLAN['cases'] if c['key'] == args.case)
        (first if args.phase == 'first' else second)(case)
    else:
        (ingest if args.phase == 'ingest' else export)()
