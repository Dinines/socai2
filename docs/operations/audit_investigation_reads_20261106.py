"""Additional read-only checks of saved results, traces and derived page fields."""
import asyncio
import json
import sys
from datetime import UTC, datetime

from audit_investigation_tests_20261106 import OUT, ROOT, normalized, read, sha


async def main():
    sys.path.insert(0, str(ROOT / 'deploy/local-investigation'))
    from config import read_private
    from validate_flow import Driver

    reports = []
    for n in ('01', '02', '03'):
        batch = 'local-eval-20261106-' + n
        receipt = read(OUT / (batch + '.json'))
        data = read(ROOT / receipt['export'] / 'database.json')
        folder = ROOT / '.local/local-investigation/validation' / batch
        driver = Driver(folder, read_private())
        cas, result = data['cases'][0], data['results'][0]
        baseline = next(r for r in data['runs'] if r['kind'] == 'baseline')
        saved, checks = [], []
        replay = None
        if '--saved' in sys.argv:
            previous = read(OUT / 'extended-readback-initial-numeric-encoding.json')
            record = next(r for r in previous['reports'] if r['batch'] == batch)
            replay = {r['path']: r for r in read(ROOT / record['originals'])}

        def check(name, actual, expected, checks=checks):
            checks.append({'field': name, 'matched': normalized(actual) == normalized(expected)})

        async def get(path, replay=replay, driver=driver, saved=saved, check=check):
            response = replay['/api/v1/socai2' + path] if replay is not None else await driver.http(None, 'GET', '/api/v1/socai2' + path, record=False, require_success=False)
            saved.append(response)
            check(path + ' HTTP', response['status'], 200)
            return response['body']

        prior = read(ROOT / receipt['live_readback']['saved_gets'])
        for response in prior[:3]:
            body = response['body']
            if body['kind'] == 'alerts':
                alert = next(a for a in data['alerts'] if a['id'] == body['facts']['id'])
                triage = next(a for a in data['alert_assessments'] if a['id'] == alert['latest_triage_id'])
                material = next(m for m in data['alert_materials'] if m['id'] == alert['latest_material_id'])
                for field, value in body['triage'].items():
                    if field in triage:
                        # These saved API/DB encoders use decimal strings and JSON
                        # numbers differently. Compare only this known numeric field by value.
                        actual = float(value) if field == 'confidence' and value is not None else value
                        expected = float(triage[field]) if field == 'confidence' and triage[field] is not None else triage[field]
                        check('triage/' + alert['id'] + '/' + field, actual, expected)
                for field, value in body['material'].items():
                    if field in material:
                        check('material/' + material['id'] + '/' + field, value, material[field])
                keys = {(o['namespace'], o['object_type'], o['object_key']) for o in data['alert_objects'] if o['alert_id'] == alert['id']}
                check('alert derived object count', body['derived']['object_count'], len(keys))
                check('triage verdict/score same record', body['triage']['confidence_percent'], float(triage['confidence']) * 100)
            else:
                derived = body['derived']
                check('incident member count', derived['member_count'], len(data['incident_alerts']))
                check('incident earliest activity', derived['first_activity_at'], min(a['event_time'] for a in data['alerts']))
                check('incident latest activity', derived['last_activity_at'], max(a['event_time'] for a in data['alerts']))
                keys = {(o['namespace'], o['object_type'], o['object_key']) for o in data['alert_objects']}
                check('incident distinct objects (not raw object rows)', derived['object_count'], len(keys))
        prefix = '/cases/' + cas['id']
        history = await get(prefix + '/history')
        check('Case history contains Case baseline only; A/I have subject traces', [x['run']['id'] for x in history.get('items', [])], [baseline['id']])
        detail = await get(prefix + '/runs/' + baseline['id'])
        check('baseline step identities', sorted(s['id'] for s in detail.get('steps', [])), sorted(s['id'] for s in data['run_steps'] if s['run_id'] == baseline['id']))
        for step in detail.get('steps', []):
            row = next(s for s in data['run_steps'] if s['id'] == step['id'])
            check('baseline step values/' + step['id'], step, {k: row[k] for k in step})
        delivered = await get(prefix + '/results/' + result['id'])
        check('all result fields exposed', delivered.get('result'), {k: result[k] for k in delivered.get('result', {})})
        check('result members', sorted(m['alert_id'] for m in delivered.get('members', [])), sorted(m['alert_id'] for m in data['result_members']))
        for run in data['runs']:
            if run['kind'] == 'baseline':
                continue
            subject = '/alerts/' + run['alert_id'] if run['kind'] == 'alert_basic' else '/incidents/' + run['incident_id']
            trace = await get(subject + '/analysis/runs/' + run['id'] + '/trace')
            check('subject trace step identities/' + run['id'], sorted(s['id'] for s in trace.get('steps', [])), sorted(s['id'] for s in data['run_steps'] if s['run_id'] == run['id']))
        c6 = next(s for s in data['run_steps'] if s['kind'] == 'model' and s['stage_code'] == 'C6')
        for art_id in (result['graph_artifact_id'], c6['output_artifact_id']):
            artifact = next(a for a in data['artifacts'] if a['id'] == art_id)
            body = await get(prefix + '/runs/' + baseline['id'] + '/artifacts/' + art_id)
            check('artifact availability/' + art_id, body.get('availability'), 'available')
            check('artifact body/' + art_id, [body.get('content_json'), body.get('content_text')], [artifact['content_json'], artifact['content_text']])
        target = folder / 'readback' / datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')
        target.mkdir(parents=True, exist_ok=True)
        originals = target / 'extended-get-originals.json'
        originals.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + '\n')
        reports.append({'batch': batch, 'get_count': len(saved), 'replayed_saved_gets': replay is not None, 'checks': checks,
            'mismatches': [c for c in checks if not c['matched']],
            'originals': str(originals.relative_to(ROOT)), 'sha256': sha(originals)})
    out = OUT / 'extended-readback.json'
    assert not out.exists(), 'preserve previous readback'
    out.write_text(json.dumps({'reports': reports}, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps([{'batch': r['batch'], 'gets': r['get_count'], 'checks': len(r['checks']), 'mismatches': r['mismatches']} for r in reports]))


if __name__ == '__main__':
    asyncio.run(main())
