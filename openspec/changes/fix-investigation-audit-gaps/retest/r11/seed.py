"""One authorized synthetic fixture, run inside the investigation API container.

Fixture JSON is supplied as FIXTURE by the remote operator. This seeds storage;
it does not simulate endpoint execution, ingestion, detection or triage.
"""
import asyncio
import hashlib
import ipaddress
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from app.db.database import engine
from app.db.clickhouse import get_clickhouse_client
from app.investigation_v2.case_analysis_tools import CaseTools


async def main():
    f = FIXTURE
    assert f['tenant_id'] == '53824f24-d1d4-5820-8147-f6cfda8a1247'
    assert len(f['alerts']) == len(f['events']) == 2 and f['synthetic'] is True
    tenant = UUID(f['tenant_id'])
    aids = [UUID(a['id']) for a in f['alerts']]
    eids = [UUID(e['event_id']) for e in f['events']]
    ch = await get_clickhouse_client()
    params = {'tenant': str(tenant), 'ids': tuple(map(str, eids))}
    assert ch.execute('SELECT count() FROM aisoc.raw_events WHERE tenant_id=%(tenant)s AND event_id IN %(ids)s', params)[0][0] == 0
    async with engine.connect() as conn:
        assert (await conn.execute(text('SELECT count(*) FROM alerts WHERE id=ANY(:ids)'), {'ids': aids})).scalar_one() == 0
        old = (await conn.execute(text('SELECT to_jsonb(a) FROM alerts a WHERE tenant_id=:tenant ORDER BY id'), {'tenant': tenant})).scalars().all()
    old_hash = hashlib.sha256(json.dumps(old, sort_keys=True, default=str).encode()).hexdigest()
    # A single explicit INSERT per store; no UPDATE, UPSERT or historical backfill.
    async with engine.begin() as conn:
        for a, e in zip(f['alerts'], f['events'], strict=True):
            assert a['source_event_ids'] == [e['event_id']]
            assert a['raw_event'] == json.loads(e['raw_payload'])
            values = {**a, 'id': UUID(a['id']), 'tenant_id': tenant,
                      'event_time': datetime.fromisoformat(e['event_time'].replace('Z', '+00:00')),
                      'ocsf_class_uid': e['class_uid']}
            for key in ('raw_event', 'source_event_ids', 'affected_hosts', 'affected_users', 'tags'):
                values[key] = json.dumps(values[key], ensure_ascii=False)
            await conn.execute(text('''INSERT INTO alerts
              (id,tenant_id,title,description,severity,status,raw_event,source_event_ids,
               affected_hosts,affected_users,tags,connector_id,connector_type,ocsf_class_uid,
               event_time,first_seen,last_seen,is_synthetic,created_at,updated_at)
              VALUES (:id,:tenant_id,:title,:description,:severity,'new',CAST(:raw_event AS jsonb),
               CAST(:source_event_ids AS jsonb),CAST(:affected_hosts AS jsonb),CAST(:affected_users AS jsonb),
               CAST(:tags AS jsonb),NULL,'synthetic_fixture',:ocsf_class_uid,
               :event_time,:event_time,:event_time,true,now(),now())'''), values)
    columns = list(f['events'][0])
    rows = []
    for event in f['events']:
        row = dict(event)
        for key in ('tenant_id', 'event_id'):
            row[key] = UUID(row[key])
        row['event_time'] = datetime.fromisoformat(row['event_time'].replace('Z', '+00:00'))
        for key in ('source_ip', 'dest_ip'):
            ip = ipaddress.ip_address(row[key])
            row[key] = ipaddress.IPv6Address('::ffff:' + str(ip)) if ip.version == 4 else ip
        rows.append(tuple(row[key] for key in columns))
    ch.execute('INSERT INTO aisoc.raw_events (' + ','.join(columns) + ') VALUES', rows)
    async with engine.connect() as conn:
        alerts = (await conn.execute(text('SELECT to_jsonb(a) FROM alerts a WHERE id=ANY(:ids) ORDER BY id'), {'ids': aids})).scalars().all()
        old_after = (await conn.execute(text('SELECT to_jsonb(a) FROM alerts a WHERE tenant_id=:tenant AND NOT(id=ANY(:ids)) ORDER BY id'), {'tenant': tenant, 'ids': aids})).scalars().all()
    assert hashlib.sha256(json.dumps(old_after, sort_keys=True, default=str).encode()).hexdigest() == old_hash
    for a in f['alerts']:
        stored = next(x for x in alerts if x['id'] == a['id'])
        assert stored['is_synthetic'] and stored['raw_event'] == a['raw_event']
        assert stored['source_event_ids'] == a['source_event_ids']
    lake_rows, types = ch.execute('SELECT ' + ','.join(columns) + ' FROM aisoc.raw_events WHERE tenant_id=%(tenant)s AND event_id IN %(ids)s ORDER BY event_id', params, with_column_types=True)
    lake = [dict(zip([x[0] for x in types], row, strict=True)) for row in lake_rows]
    assert len(lake) == 2
    for e in f['events']:
        stored = next(x for x in lake if str(x['event_id']) == e['event_id'])
        assert stored['raw_payload'] == e['raw_payload']
        assert stored['class_uid'] == e['class_uid'] and stored['src_hostname'] == e['src_hostname']
    body = f['investigation_body']
    tool = CaseTools(tenant, f['alerts'][0]['affected_hosts'],
                     datetime.fromisoformat(body['start'].replace('Z', '+00:00')),
                     datetime.fromisoformat(body['end'].replace('Z', '+00:00')))
    queries = {}
    for name, eid in zip(('process_activity', 'network_connections'), map(str, eids), strict=True):
        result = await tool.execute(name, {'hostname': f['events'][0]['src_hostname'], 'limit': 20})
        assert result['available'] and result['returned_count'] == 1 and not result['truncated']
        assert result['rows'][0]['event_id'] == eid
        queries[name] = result
    print('FIXTURE_RESULT:' + json.dumps({'batch': f['batch'], 'alerts': alerts, 'events': lake,
          'preflight_queries': queries, 'old_alert_count': len(old), 'old_alerts_sha256': old_hash,
          'old_alerts_unchanged': True, 'new_alerts': 2, 'new_lake_events': 2,
          'scope': f['scope']}, ensure_ascii=False, default=str))
    await engine.dispose()


asyncio.run(main())
