"""Direct E71 synthetic local HTTP/PG flow; one seed batch, then read only."""
import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('action', choices=['seed', 'verify'])
p.add_argument('--profile', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
cfg = json.loads(a.profile.read_text())
os.environ.update(json.loads((ROOT / cfg['environment']).read_text()))
sys.path.insert(0, cfg['runtime_directory'])
from app.models import socai2 as m
from app.socai2.baseline_service import BaselineService
from httpx import AsyncClient
from sqlalchemy import URL, insert, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def save(name, value):
    (a.output / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')


async def main():
    assert cfg['database'] == 'v12_upgrade_dev' and cfg['production_writes'] is False
    db = json.loads((ROOT / cfg['database_config']).read_text())
    assert (db['host'], db['port'], db['processing_database'], db['processor']) == (cfg['host'], cfg['port'], cfg['database'], cfg['role'])
    url = URL.create('postgresql+psycopg', username=db['admin'], password=Path(db['password_file']).read_text().strip(), host=cfg['host'], port=cfg['port'], database=cfg['database'])
    engine = create_async_engine(url, connect_args={'sslmode': cfg['sslmode'], 'options': '-c role=' + cfg['role']})
    svc = BaselineService(async_sessionmaker(engine, expire_on_commit=False))
    tenant = UUID(cfg['tenant_id'])
    a.output.mkdir(parents=True, exist_ok=True)
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text('select current_database(),current_user'))).one() == (cfg['database'], cfg['role'])
        if a.action == 'seed':
            assert not (a.output / 'fixture-intent.json').exists(), 'do_not_reseed'
            at = datetime(2026, 11, 12, tzinfo=UTC)
            source = 'synthetic-alert-host-' + str(uuid4())
            h = lambda value: ('host', value)
            data = {'seed': ([h('HOST-A'), h('HOST-A'), h('HOST-B'), ('ip', '192.0.2.15')], at)}
            for i in range(9):
                objects = [h('HOST-B')] if i == 6 else [h('HOST-A')]
                if i == 8:
                    objects = [h('HOST-A'), h('HOST-A'), h('HOST-B')]
                when = at + timedelta(days=1, minutes=min(i, 7)) if i else datetime(2020, 1, 1, tzinfo=UTC)
                data['m' + str(i)] = (objects, when)
            data.update({'wrong_namespace': ([h('HOST-A')], at), 'wrong_source': ([h('HOST-A')], at),
                'old_material': ([h('OTHER')], at), 'unknown_candidate': ([h('HOST-A')], None),
                'ip_only': ([('ip', '192.0.2.15')], at), 'case_different': ([h('host-a')], at),
                'unknown_seed': ([h('UNKNOWN-SOURCE')], None), 'unknown_seed_match': ([h('UNKNOWN-SOURCE')], at),
                'empty_seed': ([], at), 'no_material': ([], at)})
            ids = {name: str(uuid4()) for name in data}
            mids = {name: str(uuid4()) for name in data if name != 'no_material'}
            f = {'source_namespace': source, 'alerts': ids, 'materials': mids,
                'expected': sorted([ids['m' + str(i)] for i in range(9)], key=lambda v: (data[next(k for k in ids if ids[k] == v)][1], v), reverse=True)}
            save('fixture-intent', f)
            async with svc.transaction(tenant) as store:
                for name, (objects, when) in data.items():
                    aid = UUID(ids[name])
                    await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=tenant,
                        source_namespace=source + '-other' if name == 'wrong_source' else source,
                        source_identity_key=str(aid), title='SYNTHETIC same-host ' + name,
                        event_time=when, event_time_source='source' if when else 'unknown', severity='high',
                        handling_status='completed' if name == 'm7' else 'new',
                        disposition='false_positive' if name == 'm7' else None))
                    if name == 'no_material':
                        continue
                    mid = UUID(mids[name])
                    await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=tenant, alert_id=aid,
                        revision=2 if name == 'old_material' else 1,
                        raw_json={'synthetic': True, 'objects': [{'type': t, 'value': v} for t, v in objects]},
                        detection={'tactics': ['Execution'] if name == 'seed' else ['Persistence']},
                        source_scope={}, retention={}, material_state='complete'))
                    for index, (typ, value) in enumerate(objects):
                        await store.db.execute(insert(m.AlertObjects).values(id=uuid4(), tenant_id=tenant, alert_id=aid,
                            material_id=mid, object_type=typ, object_key=typ + ':' + value, object_role='entity',
                            namespace=source + '-other' if name == 'wrong_namespace' else source,
                            raw_value=value, normalized_value=value, source_path=f'$.raw_json.objects[{index}].value', attributes={}))
                    await store.db.execute(update(m.Alerts).where(m.Alerts.id == aid).values(latest_material_id=mid))
                    if name == 'old_material':
                        old = uuid4()
                        await store.db.execute(insert(m.AlertMaterials).values(id=old, tenant_id=tenant, alert_id=aid,
                            revision=1, raw_json={'host': 'HOST-A'}, detection={}, source_scope={}, retention={}, material_state='complete'))
                        await store.db.execute(insert(m.AlertObjects).values(id=uuid4(), tenant_id=tenant, alert_id=aid,
                            material_id=old, object_type='host', object_key='host:HOST-A', object_role='entity', namespace=source,
                            raw_value='HOST-A', normalized_value='HOST-A', source_path='$.raw_json.host', attributes={}))
            save('fixture', f)
            print(json.dumps({'seeded_alerts': len(ids), 'source_alert_id': ids['seed']}))
            return
        assert not (a.output / 'verify-http.json').exists(), 'preserve_completed_attempt'
        f = json.loads((a.output / 'fixture.json').read_text())
        ids = f['alerts']
        async def snapshot():
            out = {}
            async with svc.transaction(tenant, readonly=True) as store:
                for model in [m.Alerts, m.AlertMaterials, m.AlertObjects, m.AlertAssessments]:
                    t = model.__table__
                    key = t.c.id if model == m.Alerts else t.c.alert_id
                    out[t.name] = [dict(r) for r in (await store.db.execute(select(t).where(t.c.tenant_id == tenant,
                        key.in_([UUID(v) for v in ids.values()])).order_by(t.c.id))).mappings()]
            return json.loads(json.dumps(out, default=str))
        before = await snapshot()
        save('sql-before', before)
        receipts = []
        secret = json.loads((ROOT / cfg['credential']['file']).read_text())
        async with AsyncClient(base_url=cfg['base_url'], timeout=cfg['timeout_seconds'], headers={'Authorization': 'Bearer ' + secret['api_key']}) as http:
            async def get(path, expected=200):
                response = await http.get(path)
                value = response.json()
                receipts.append({'method': 'GET', 'path': path, 'status': response.status_code, 'body': value})
                save('verify-http', receipts)
                assert response.status_code == expected, (response.status_code, value)
                return value
            prefix = '/api/v1/socai2/alerts/'
            endpoint = prefix + ids['seed'] + '/same-host-alerts'
            page = await get(endpoint)
            assert page['limit'] == 7 and page['total'] == 9
            assert [x['alert']['id'] for x in page['items']] == f['expected'][:7]
            assert len(page['source_hosts']) == 3 and page['source_material_id'] == f['materials']['seed']
            multi = next(x for x in page['items'] if x['alert']['id'] == ids['m8'])
            assert len(multi['matches']) == 5
            assert next(x for x in page['items'] if x['alert']['id'] == ids['m7'])['alert']['disposition'] == 'false_positive'
            unknown = await get(prefix + ids['unknown_seed'] + '/same-host-alerts')
            assert [x['alert']['id'] for x in unknown['items']] == [ids['unknown_seed_match']]
            for name in ['ip_only', 'empty_seed', 'no_material']:
                empty = await get(prefix + ids[name] + '/same-host-alerts')
                assert empty['items'] == [] and empty['source_hosts'] == [] and empty['total'] == 0
            await get(endpoint + '?limit=2', 422)
            await get(prefix + str(uuid4()) + '/same-host-alerts', 404)
            await get(prefix + 'invalid-id/same-host-alerts', 422)
            for item in page['items']:
                assert (await get(prefix + item['alert']['id']))['facts'] == item['alert']
            # Independently compare every returned source object to original SQL, then read both original materials.
            objects = {o['id']: o for o in before['alert_objects']}
            pairs = 0
            for item in page['items']:
                for match in item['matches']:
                    for side in ['seed', 'candidate']:
                        view = match[side]
                        original = objects[view['id']]
                        assert all(view[k] == original[k] for k in view if k != 'algorithm')
                        assert view['algorithm'] is None
                    pairs += 1
            for view in [multi['matches'][0]['seed'], multi['matches'][0]['candidate']]:
                raw = await get(prefix + view['alert_id'] + '/materials/' + view['material_id'])
                assert view['raw_value'] in json.dumps(raw)
        after = await snapshot()
        save('sql-after', after)
        assert before == after
        save('summary', {'passed': True, 'http_gets': len(receipts), 'matched_pairs': pairs, 'returned': 7, 'total': 9,
            'source_alert_id': ids['seed'], 'readonly_tables': list(before), 'models': 0, 'production_writes': 0})
        print(json.dumps({'passed': True, 'http_gets': len(receipts), 'matched_pairs': pairs}))
    finally:
        await engine.dispose()

asyncio.run(main())
