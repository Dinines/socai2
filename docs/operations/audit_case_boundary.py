"""Read saved Case exchanges and replay only the pure material projection."""
import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads(path.read_text())


def size(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_snapshot(path):
    data = read(path)
    run_ids = {r['id'] for r in data['runs'] if r['kind'] == 'baseline'}
    steps = {r['id']: r for r in data['run_steps']}
    artifacts = {r['id']: r for r in data['artifacts']}
    requests = []
    for artifact in data['artifacts']:
        if artifact['run_id'] not in run_ids or artifact['kind'] != 'model_request':
            continue
        step = steps[artifact['step_id']]
        payload = artifact['content_json']['payload']
        messages = payload['body']['messages']
        user = json.loads(messages[1]['content'])
        visible = {item['id']: item['value'] for group in user.get('source_groups', [])
                   for item in group['items']}
        response = artifacts[step['output_artifact_id']]
        raw = response['content_json']['payload']['raw']['choices'][0]['message']['content']
        answer = json.loads(raw)
        incident_inputs = []
        for sid, source in payload['source_map'].items():
            ref = source['ref']
            if not re.fullmatch(r'\$\.incidents\.[0-9a-f-]{36}\.diagnosis', ref.get('source_path') or ''):
                continue
            iid = ref['source_path'].split('.')[2]
            context = artifacts[ref['id']]['content_json']
            diagnosis = context['incidents'][iid]['diagnosis']
            incident_inputs.append({'source_id': sid, 'incident_id': iid,
                                    'frozen_findings': len(diagnosis['diagnosis'].get('findings', [])),
                                    'frozen_open_questions': len(diagnosis.get('open_questions', [])),
                                    'visible_keys': sorted(visible[sid]),
                                    'source_role': ref['role']})
        requests.append({'run_id': artifact['run_id'], 'stage': step['stage_code'],
                         'request_id': artifact['id'], 'response_id': response['id'],
                         'input_tokens': step['usage']['input_tokens'],
                         'output_tokens': step['usage']['output_tokens'],
                         'messages': [{'role': m['role'], 'utf8_bytes': len(m['content'].encode())}
                                      for m in messages],
                         'input_sections_bytes': {k: size(v) for k, v in user.items()},
                         'source_count': len(payload['source_map']),
                         'source_roles': dict(Counter(s['ref']['role'] for s in payload['source_map'].values())),
                         'question_id': (user.get('question') or {}).get('id'),
                         'question_member_count': len((user.get('question') or {}).get('scope', {}).get('alert_ids', [])),
                         'incident_inputs': incident_inputs,
                         'output_sections_bytes': {k: size(v) for k, v in answer.items()},
                         'output_section_counts': {k: len(v) for k, v in answer.items() if isinstance(v, list)},
                         'output_analysis_counts': {k: len(v) for k, v in answer.get('analysis', {}).items() if isinstance(v, list)},
                         'output_utf8_bytes': len(raw.encode()), 'output_compact_utf8_bytes': size(answer),
                         'output_uuid_occurrences': len(re.findall(r'[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}', raw))})
    return sorted(requests, key=lambda r: r['stage'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--material-snapshot', type=Path, action='append', default=[])
    parser.add_argument('--runtime-config', type=Path, required=True)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('audit_receipt_exists')
    originals = {p: sha(p) for p in [args.snapshot, *args.material_snapshot]}
    sys.path.insert(0, str(ROOT))
    # Imports/configuration only: no prepare, connect, execute, or export call.
    from tools.testdata.incident_integration.run import initialize
    initialize(args.runtime_config)
    os.environ['SOCAI2_INVESTIGATION_POLICY'] = str(args.policy.resolve())
    from app.socai2.baseline_semantics import material_projection
    projections = []
    for path in args.material_snapshot:
        for material in read(path)['alert_materials']:
            projected = material_projection(material)
            projections.append({'snapshot': str(path), 'material_id': material['id'],
                                'raw_json_top_keys': sorted(material['raw_json'] or {}),
                                'material_state': material['material_state'],
                                'projected_fields': [{'name': f['name'], 'source_path': f['source_path']}
                                                     for f in projected['fields']],
                                'omission_reasons': dict(Counter(o['reason'] for o in projected['omissions'])),
                                'note': 'pure Case material projection, not a Case Run or whole prompt'})
    sources = [ROOT / 'services/api/app/socai2' / name for name in (
        'baseline_context.py', 'baseline_model_view.py', 'baseline_semantics.py', 'model_input_view.py',
        'baseline_analysis.py', 'baseline_analysis_contract.py', 'baseline_deep.py', 'baseline_deep_contract.py',
        'baseline_reanalysis.py', 'baseline_delivery.py', 'baseline_delivery_contract.py',
        'baseline_delivery_projection.py', 'baseline_executor.py')]
    result = {'captured_at': datetime.now(UTC).isoformat(),
              'mode': 'offline_saved_exchange_and_pure_projection', 'model_calls': 0,
              'database_connections': 0, 'created_cases': 0, 'remote_actions': 0,
              'snapshot_sha256': {str(p): h for p, h in originals.items()},
              'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in [*sources, Path(__file__).resolve(), args.policy.resolve()]},
              'requests': inspect_snapshot(args.snapshot), 'material_projection_replays': projections,
              'not_a_candidate_performance_test': True}
    assert all(sha(p) == h for p, h in originals.items())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'saved': str(args.output), 'requests_read': len(result['requests']),
                      'material_replays': len(projections), 'model_calls': 0, 'created_cases': 0}))


if __name__ == '__main__':
    main()
