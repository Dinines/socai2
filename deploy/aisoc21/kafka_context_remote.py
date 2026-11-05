"""Fixed k4 context batch; separate write and read diagnostics, no models."""
import hashlib
import importlib.util
import json
import secrets
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID, uuid5

ROOT = Path('/opt/sting-aisoc-socai2/evidence/next-kafka-k4-context-20261105')
p = Path('/opt/sting-aisoc-socai2/evidence/next-kafka-k2-20261105/kafka_chain_remote.py')
spec = importlib.util.spec_from_file_location('k2', p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def save(name, value):
    with (ROOT / (name + '.json')).open('x') as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
    (ROOT / (name + '.json')).chmod(0o600)


def pg_state():
    return {t: m.service.pg(m.service.DATABASE,
        'SELECT count(*) FROM socai2.' + t + ' WHERE tenant_id=' + m.service.literal(m.service.TENANT))
        for t in ('alerts', 'cases', 'runs', 'results', 'case_assessments')}


def seed(packet):
    ROOT.mkdir(mode=0o700, exist_ok=False)
    events = packet['events']
    ids = [e['event_id'] for c in events['cases'] for e in c['events']]
    assert events['tenant_id'] == m.service.TENANT and len(ids) == len(set(ids)) == 40
    assert all(not c['alerts'] and all(e['tenant_id'] == m.service.TENANT for e in c['events']) for c in events['cases'])
    before, pg_before = m.service.protected_model_config(), pg_state()
    save('intent', {'event_ids': ids, 'model_calls': 0, 'source_hashes': {
        k: hashlib.sha256(v.encode()).hexdigest() for k, v in packet['sources'].items()},
        'new_lake_only_writer': True, 'manifest': packet['manifest']})
    save('events', events)
    files = {p.relative_to(m.RELEASE / 'fusion').as_posix(): p.read_text()
        for p in (m.RELEASE / 'fusion/app').rglob('*.py')}
    files['app/services/lake_writer.py'] = packet['sources']['writer']
    old, new = m.service.environment('socai2-fusion-1'), m.service.environment(m.service.NEW)
    env = {k: v for k, v in old.items() if k.startswith('KAFKA_')}
    prefix = 'socai2.validation.k4.20261105'
    user, password = 'socai2_kafka_k4_writer_20261105', secrets.token_hex(32)
    env.update({'KAFKA_TOPIC_ALERTS_RAW': prefix + '.alerts.raw', 'KAFKA_TOPIC_RAW_EVENTS': prefix + '.raw_events',
        'KAFKA_TOPIC_ALERTS_FUSED': prefix + '.alerts.fused', 'KAFKA_CONSUMER_GROUP': 'socai2-validation-k4-20261105',
        'KAFKA_SSL_CAFILE': '/run/certs/ca.crt', 'DATABASE_URL': new['DATABASE_URL'],
        'REDIS_URL': urlunsplit(urlsplit(new['REDIS_URL'])._replace(path='/13')), 'ENVIRONMENT': 'production',
        'AISOC_ALERT_STORE_SCHEMA': 'socai2', 'AISOC_EVENT_PROMOTION_ENABLED': 'false', 'AISOC_UEBA_FUSION_ENABLED': 'false',
        'AISOC_DETECTION_ENGINE_ENABLED': 'false', 'AISOC_WINDOWED_DETECTION_ENABLED': 'false',
        'CLICKHOUSE_DATABASE': m.service.LAKE, 'CLICKHOUSE_HOST': old['CLICKHOUSE_HOST'],
        'CLICKHOUSE_PORT': old['CLICKHOUSE_PORT'], 'CLICKHOUSE_USER': user, 'CLICKHOUSE_PASSWORD': password})
    where = 'tenant_id=' + m.service.literal(m.service.TENANT) + ' AND event_id IN (' + ','.join(m.service.literal(i) for i in ids) + ')'
    for db in ('aisoc', m.service.LAKE):
        assert m.service.lake('SELECT count() FROM ' + db + '.raw_events WHERE ' + where) == '0'
    m.service.lake('CREATE USER ' + user + ' IDENTIFIED WITH sha256_password BY ' + m.service.literal(password)
        + '; GRANT INSERT ON ' + m.service.LAKE + '.raw_events TO ' + user)
    try:
        body = {'environment': env, 'files': files, 'cases': events['cases'], 'topic_prefix': prefix,
            'replay_alert': False, 'expected_fused': 0, 'expected_lake': 40}
        output = m.service.command(['docker', 'exec', '-i', m.service.NEW, 'python', '-c', packet['sources']['consumer']],
            body=json.dumps(body).encode(), timeout=180)
        records = [json.loads(line.removeprefix('K1_RESULT=')) for line in output.splitlines() if line.startswith('K1_RESULT=')]
        assert len(records) == 1
        save('consumer', records[0])
        rows = [json.loads(line) for line in m.service.lake('SELECT toString(event_id) AS event_id,count() AS rows FROM '
            + m.service.LAKE + '.raw_events WHERE ' + where + ' GROUP BY event_id ORDER BY event_id FORMAT JSONEachRow').splitlines()]
        save('readback', {'rows': rows, 'all_40_exactly_once': len(rows) == 40 and all(int(r['rows']) == 1 for r in rows),
            'old_lake_rows': int(m.service.lake('SELECT count() FROM aisoc.raw_events WHERE ' + where)),
            'pg_counts_unchanged': pg_before == pg_state(), 'protected_unchanged': before == m.service.protected_model_config()})
    finally:
        m.service.lake('DROP USER ' + user)
        save('cleanup', {'temporary_writer_removed': m.service.lake(
            'SELECT count() FROM system.users WHERE name=' + m.service.literal(user)) == '0'})


def query(packet):
    assert ROOT.exists()
    save('query-intent', {'model_calls': 0, 'new_runs': 0, 'mode': 'actual deployed LakeGateway with candidate semantic projection in diagnostic process',
        'source_hashes': {k: hashlib.sha256(v.encode()).hexdigest() for k, v in packet['sources'].items()}})
    contexts = []
    plan = json.loads((p.parent / 'plan.json').read_text())
    for case in plan['cases']:
        cid = str(uuid5(UUID(m.service.TENANT), 'socai2.case.create:' + m.uid(case['key'] + '-case')))
        sql = "SELECT content_json FROM socai2.artifacts WHERE tenant_id=" + m.service.literal(m.service.TENANT)
        sql += " AND schema_version='socai2.baseline-context.v1' AND run_id=(SELECT id FROM socai2.runs WHERE tenant_id="
        sql += m.service.literal(m.service.TENANT) + ' AND case_id=' + m.service.literal(cid) + ' ORDER BY requested_at LIMIT 1)'
        contexts.append({'key': case['key'], 'context': json.loads(m.service.pg(m.service.DATABASE, sql))})
    output = m.service.command(['docker', 'exec', '-i', m.service.NEW, 'python', '-c', packet['sources']['query']],
        body=json.dumps({'contexts': contexts, 'semantics': packet['sources']['semantics']}).encode(), timeout=180)
    save('tools', json.loads(output))


if __name__ == '__main__':
    packet = json.load(sys.stdin)
    {'seed': seed, 'query': query}[packet['phase']](packet)
    print(json.dumps({name: json.loads((ROOT / (name + '.json')).read_text()) for name in
        (('intent', 'consumer', 'readback', 'cleanup') if packet['phase'] == 'seed' else ('query-intent', 'tools'))}))
