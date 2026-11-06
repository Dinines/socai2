"""Read saved test batches and optional local GETs; never dispatch or write business data."""
import argparse
import asyncio
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / '.local/local-investigation/validation'
OUT = ROOT / 'docs/operations/evidence/additional-tests-20261106'


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def normalized(v):
    if isinstance(v, str) and re.match(r'^\d{4}-\d\d-\d\d[T ]\d\d:', v):
        return datetime.fromisoformat(v.replace('Z', '+00:00')).astimezone(UTC).isoformat()
    if isinstance(v, list):
        return [normalized(x) for x in v]
    if isinstance(v, dict):
        return {k: normalized(x) for k, x in v.items()}
    return v


def inspect(folder):
    plan = read(folder / 'plan.json')
    candidates = sorted((folder / 'exports').glob('*/manifest.json'))
    if not candidates:
        return {'batch': folder.name, 'state': 'no_export', 'attempts': None}, None, None
    exp = candidates[-1].parent
    manifest, data = read(exp / 'manifest.json'), read(exp / 'database.json')
    for item in manifest['sources']:
        assert sha(exp / item['file']) == item['sha256'], (folder.name, item['file'])
    indexes = {t: {r['id']: r for r in rows} for t, rows in data.items()}
    violations, joins = [], {}
    # SQL foreign keys are not a substitute for checking the exported links.
    relationships = {
        'case_alerts': [('case_id', 'cases'), ('alert_id', 'alerts')],
        'case_incidents': [('case_id', 'cases'), ('incident_id', 'incidents')],
        'incident_alerts': [('incident_id', 'incidents'), ('alert_id', 'alerts')],
        'run_members': [('run_id', 'runs'), ('alert_id', 'alerts')],
        'results': [('source_run_id', 'runs'), ('case_id', 'cases')],
        'result_members': [('result_id', 'results'), ('run_id', 'runs'), ('alert_id', 'alerts')],
        'case_assessment_sources': [('assessment_id', 'case_assessments'), ('result_id', 'results'),
                                    ('artifact_id', 'artifacts'), ('task_revision_id', 'task_revisions')],
        'case_assessment_members': [('assessment_id', 'case_assessments'), ('alert_id', 'alerts')],
        'alert_objects': [('material_id', 'alert_materials'), ('alert_id', 'alerts')],
        'activity_targets': [('activity_id', 'activities')],
    }
    for table, fields in relationships.items():
        checked = 0
        for row in data[table]:
            for field, target in fields:
                if row.get(field) is None:
                    continue
                parent = indexes[target].get(row[field])
                if parent is None or parent['tenant_id'] != row['tenant_id']:
                    violations.append(f'{table}/{row["id"]}/{field}')
                checked += 1
        joins[table] = checked
    for step in data['run_steps']:
        for field in ('input_artifact_id', 'output_artifact_id'):
            if step.get(field):
                artifact = indexes['artifacts'].get(step[field])
                if not artifact or artifact['run_id'] != step['run_id'] or artifact['tenant_id'] != step['tenant_id']:
                    violations.append('run_steps/'+step['id']+'/'+field)
    expected = {a['source_alert_id']: a for a in plan['case']['alerts']}
    originals = []
    for material in data['alert_materials']:
        raw = material['raw_json']
        original = expected.get(raw.get('source_alert_id')) if isinstance(raw, dict) else None
        originals.append(bool(original and raw['raw_event'] == original['raw_event'] and
                              material['ocsf_json'] == original['raw_event']['ocsf_event']))
    attempts = [s for s in data['run_steps'] if s['kind'] == 'model' and s['state'] not in ('planned', 'skipped')]
    models = []
    for step in attempts:
        output = indexes['artifacts'].get(step['output_artifact_id']) or {}
        body = output.get('content_json') or {}
        payload = body.get('payload') or body
        models.append({'stage': step['stage_code'], 'run_id': step['run_id'], 'step_id': step['id'],
            'state': step['state'], 'error': step['error'], 'usage': step['usage'],
            'input_artifact_id': step['input_artifact_id'], 'output_artifact_id': step['output_artifact_id'],
            'provider_status': (payload.get('raw') or {}).get('status'),
            'validation_error': payload.get('validation_error')})
    cas = data['cases'][0] if data['cases'] else None
    assessment = indexes['case_assessments'].get(cas['current_assessment_id']) if cas else None
    selected = [s for s in data['case_assessment_sources'] if assessment and s['assessment_id'] == assessment['id']]
    results = [indexes['results'][s['result_id']] for s in selected if s.get('result_id')]
    if results and assessment['conclusion'] != results[0]['conclusion']:
        violations.append('adopted conclusion differs from selected result')
    graph = []
    for result in data['results']:
        if result.get('graph_artifact_id'):
            art = indexes['artifacts'].get(result['graph_artifact_id'])
            if not art or art['case_id'] != result['case_id'] or art['run_id'] != result['source_run_id']:
                violations.append('graph provenance')
            else:
                body = art['content_json'] or {}
                graph.append({'artifact_id': art['id'], 'nodes': len(body.get('nodes', [])), 'edges': len(body.get('edges', []))})
    queries = []
    for step in data['run_steps']:
        if step['kind'] == 'tool':
            queries.append({k: step.get(k) for k in ('stage_code', 'name', 'state', 'returned_rows', 'error', 'output_artifact_id')})
    lake = read(folder/'lake-readback.json') if (folder/'lake-readback.json').exists() else None
    report = {'batch': folder.name, 'scenario': plan['case'].get('scenario', 'maintenance'),
        'export': str(exp.relative_to(ROOT)), 'manifest_sha256': sha(exp/'manifest.json'),
        'database_sha256': sha(exp/'database.json'), 'plan_sha256': sha(folder/'plan.json'),
        'source_code_sha256': plan['source_sha256'], 'model_profile': plan.get('model_profile'),
        'attempts': len(attempts), 'table_counts': manifest['table_counts'],
        'runs': [{k: r.get(k) for k in ('id', 'kind', 'state', 'stop_reason', 'delivery_state')} for r in data['runs']],
        'models': models, 'queries': queries, 'case_id': cas['id'] if cas else None,
        'current_assessment': assessment, 'conclusion_sources': selected,
        'relations_checked': joins, 'relationship_violations': violations,
        'original_materials_exact': len(originals) == 2 and all(originals),
        'lake_originals_exact': bool(lake and lake.get('passed')), 'graph': graph,
        'page_url': 'http://127.0.0.1:4174/#/cases/'+'!'.join(('socai2','local-standalone',folder.name,plan['tenant_id'],'case',cas['id']))+'/case-info' if cas else None,
        'quality_status': 'requires_semantic_review', 'automatic_checks_are_not_quality_acceptance': True}
    return report, data, exp


async def live_readback(folder, data, exp):
    sys.path.insert(0, str(ROOT/'deploy/local-investigation'))
    from config import read_private
    from validate_flow import Driver
    driver = Driver(folder, read_private())
    cas = data['cases'][0]
    requests = [(f'/alerts/{a["id"]}', 'alerts', a) for a in data['alerts']]
    requests += [(f'/incidents/{i["id"]}', 'incidents', i) for i in data['incidents']]
    requests += [(f'/cases/{cas["id"]}', 'cases', cas), (f'/cases/{cas["id"]}/page-data', 'page_data', None)]
    requests += [(f'/alerts/{m["alert_id"]}/materials/{m["id"]}', 'material', m) for m in data['alert_materials']]
    requests += [(f'/incidents/{i["id"]}/records/members', 'incident_members', i) for i in data['incidents']]
    saved, checks = [], []
    for path, table, row in requests:
        response = await driver.http(None, 'GET', '/api/v1/socai2'+path, record=False, require_success=False)
        saved.append(response)
        if response['status'] != 200:
            checks.append({'path': path, 'matched': False, 'status': response['status']})
            continue
        body = response['body']
        if table in ('alerts', 'incidents', 'cases'):
            fields = body['case'] if table == 'cases' else body['facts']
            for key, value in fields.items():
                checks.append({'path': path, 'field': key, 'storage': table+'.'+key,
                    'matched': key in row and normalized(value) == normalized(row[key]),
                    'value_state': 'saved_null' if value is None else 'saved_value'})
        elif table == 'page_data':
            original = next(p['page_data'] for p in read(exp/'case-page-data.json') if p['case_id'] == cas['id'])
            checks.append({'path': path, 'storage': 'current assessment + evidence index',
                           'matched': normalized(body) == normalized(original)})
        elif table == 'incident_members':
            # The actual collection keeps member Alert identity in alert_id.
            expected = {r['alert_id'] for r in data['incident_alerts'] if r['incident_id'] == row['id']}
            actual = {r.get('alert_id') or r.get('id') for r in body['items']}
            checks.append({'path': path, 'storage': 'incident_alerts.alert_id', 'matched': actual == expected})
        else:
            original = {k: row[k] for k in ('raw_json', 'ocsf_json', 'enrichment')}
            checks.append({'path': path, 'storage': 'alert_materials.raw_json/ocsf_json/enrichment/raw_text',
                'matched': body['metadata']['id'] == row['id'] and body['content_json'] == original
                    and body['content_text'] == row['raw_text'], 'availability': body['availability']})
    target = folder/'readback'/datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')
    target.mkdir(parents=True)
    (target/'page-get-originals.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2)+'\n')
    return {'saved_gets': str((target/'page-get-originals.json').relative_to(ROOT)),
        'sha256': sha(target/'page-get-originals.json'), 'get_count': len(saved),
        'checks': checks, 'mismatches': [c for c in checks if not c['matched']]}


async def main(batch, live):
    folder = BASE/batch
    assert folder.parent == BASE
    report, data, exp = inspect(folder)
    if live:
        report['live_readback'] = await live_readback(folder, data, exp)
    OUT.mkdir(parents=True,exist_ok=True)
    target = OUT/(batch+'.json')
    assert not target.exists(), 'preserve prior audit; choose a distinct output batch'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'report':str(target.relative_to(ROOT)), 'attempts':report['attempts'],
        'originals_exact':report['original_materials_exact'],'relationship_violations':report['relationship_violations'],
        'get_mismatches':report.get('live_readback',{}).get('mismatches')}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch',required=True);parser.add_argument('--live-readback',action='store_true')
    args=parser.parse_args()
    asyncio.run(main(args.batch,args.live_readback))
