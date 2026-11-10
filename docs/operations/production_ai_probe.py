"""Run one configured A/I batch and export existing fields, without creating a Case."""
import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from production_case_probe import query, remote, save

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'deploy/local-investigation'))
from flow_export import TABLES, query_for


def now():
    return datetime.now(UTC).isoformat()


def subjects(cfg, root):
    aids = [str(UUID(json.loads((root / f'ingress-{i}-receipt.json').read_text())['body']['canonical_alert_id']))
            for i in range(1, cfg['execution_bounds']['alert_attempts'] + 1)]
    literals = ','.join("'" + v + "'::uuid" for v in aids)
    rows = query(cfg, f"SELECT coalesce(jsonb_agg(to_jsonb(t)),'[]'::jsonb) FROM socai2.incident_alerts t WHERE alert_id IN ({literals});")
    incidents = {row['incident_id'] for row in rows}
    if len(rows) != len(aids) or len(incidents) != 1 or {r['alert_id'] for r in rows} != set(aids):
        raise ValueError('expected new alerts to be correlated into one incident')
    return aids, str(UUID(incidents.pop()))


def execute(cfg, root):
    bounds = cfg['execution_bounds']
    assert bounds['case_baseline_runs'] == 0 and bounds['manual_retries'] == 0
    assert bounds['incident_attempts'] == 1
    aids, iid = subjects(cfg, root)
    sequence = [(f'A{i}', 'alert', aid) for i, aid in enumerate(aids, 1)] + [('I', 'incident', iid)]
    assert len(sequence) == bounds['model_calls_max_by_policy']
    for name, _, _ in sequence:
        assert not (root / (name + '-intent.json')).exists(), 'closed or uncertain attempt cannot be replayed'
    save(root / 'execution-start.json', {'at': now(), 'alerts': aids, 'incident': iid, 'case_jobs': 0})
    for name, kind, identity in sequence:
        arguments = [kind, '--subject', identity, '--operation-key', str(UUID(cfg['operation_keys'][name]))]
        save(root / (name + '-intent.json'), {'at': now(), 'arguments': arguments})
        started = time.monotonic()
        response = remote(cfg, {'mode': 'job', 'tenant': cfg['target']['tenant_id'],
                               'actor': cfg['target']['actor_id'], 'arguments': arguments}, job=True)
        save(root / (name + '-receipt.json'), {'at': now(), 'elapsed_seconds': time.monotonic() - started, **response})
        result = response.get('receipt', {})
        print(json.dumps({'stage': name, 'exit_code': response.get('exit_code'), 'receipt': result}), flush=True)
        if result.get('state') not in {'completed', 'failed', 'cancelled'}:
            raise ValueError('uncertain execution; inspect stored Run before any further dispatch')
    save(root / 'execution-closed.json', {'at': now(), 'stage_attempts': len(sequence), 'case_jobs': 0, 'retries': 0})


def export(cfg, root):
    aids, iid = subjects(cfg, root)
    literal_aids = 'ARRAY[' + ','.join("'" + v + "'" for v in aids) + ']::uuid[]'
    runs = query(cfg, "SELECT coalesce(jsonb_agg(id),'[]'::jsonb) FROM socai2.runs WHERE "
                 f"alert_id=ANY({literal_aids}) OR incident_id='{iid}'::uuid;")
    replacements = {'$1::uuid': "'" + str(UUID(cfg['target']['tenant_id'])) + "'::uuid",
                    '$2::uuid[]': literal_aids, '$3::uuid': "'" + iid + "'::uuid", '$4::uuid': 'NULL::uuid',
                    '$5::uuid[]': 'ARRAY[' + ','.join("'" + str(UUID(r)) + "'" for r in runs) + ']::uuid[]'}
    clauses = []
    for table in TABLES:
        sql = query_for(table)
        for key, value in replacements.items():
            sql = sql.replace(key, value)
        clauses += ["'" + table + "'", '(' + sql + ')']
    snapshot = query(cfg, "SELECT jsonb_build_object('captured_at',now(),'data',jsonb_build_object(" + ','.join(clauses) + "));")
    data = snapshot['data']
    assert not data['cases'] and not any(r.get('case_id') for r in data['runs'])
    folder = root / 'exports' / datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True, exist_ok=False)
    save(folder / 'database.json', data)
    paths = []
    for subject in ('alerts', 'incidents'):
        for row in data[subject]:
            base = '/' + subject + '/' + row['id']
            paths += [base, base + '/analysis']
    paths += [f"/alerts/{r['alert_id']}/materials/{r['id']}" for r in data['alert_materials']]
    for row in data['runs']:
        subject = 'alerts' if row.get('alert_id') else 'incidents'
        identity = row.get('alert_id') or row['incident_id']
        base = f"/{subject}/{identity}/analysis/runs/{row['id']}"
        paths += [base, base + '/trace']
        paths += [base + '/artifacts/' + a['id'] for a in data['artifacts'] if a['run_id'] == row['id']]
    responses = []
    for index, path in enumerate(paths):
        path = '/api/v1/socai2' + path
        response = remote(cfg, {'mode': 'http', 'method': 'GET', 'path': path, 'body': None})
        item = {'method': 'GET', 'path': path, **response}
        responses.append(item)
        save(folder / f'get-{index:03d}.json', item)
    save(folder / 'api-responses.json', responses)
    manifest = {'schema_version': 'socai2.page-export.v1', 'batch_id': cfg['batch_id'],
                'source_environment': 'production21', 'input_kind': cfg['input_kind'],
                'exported_at': snapshot['captured_at'], 'database': cfg['target']['database'],
                'tenant_id': cfg['target']['tenant_id'], 'case_id': None, 'incident_id': iid,
                'database_snapshot': 'single_readonly_repeatable_read', 'api_observations': 'separate_later_GETs',
                'sources': [{'file': name, 'sha256': hashlib.sha256((folder / name).read_bytes()).hexdigest()}
                            for name in ('database.json', 'api-responses.json')],
                'table_counts': {k: len(v) for k, v in data.items()}}
    save(folder / 'manifest.json', manifest)
    result = {'folder': str(folder), 'incident_id': iid, 'runs': len(runs), 'case_jobs': 0,
              'gets': len(responses), 'errors': [r['path'] for r in responses if r['status'] != 200]}
    save(root / ('readback-receipt-' + folder.name + '.json'), result)
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('mode', choices=('execute', 'export'))
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    (execute if args.mode == 'execute' else export)(config, args.config.parent)
