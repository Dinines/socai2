"""Summarize only fixed k2 exports; no model or database calls."""
import argparse
import json
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/operations/evidence/socai2-kafka-chain-20261105/k2'


def uid(label):
    return str(uuid5(NAMESPACE_URL, 'socai2-kafka-k2-20261105:' + label))


def parsed_response(content):
    raw = content.get('raw') or (content.get('payload') or {}).get('raw')
    if not isinstance(raw, dict):
        return None
    if 'choices' in raw:
        choices = raw['choices']
        text = choices[0]['message'].get('content') if len(choices) == 1 else None
    else:
        texts = [p.get('text', '') for o in raw.get('output', []) for p in o.get('content', []) if p.get('type') == 'output_text']
        text = ''.join(texts)
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return {'unparsed_content': text}


def analyze(directory):
    directory = directory.resolve()
    data = json.loads(max(directory.glob('database-*.json')).read_text('utf-8'))
    plan = json.loads((OUT / 'plan.json').read_text('utf-8'))
    cases = []
    for fixture in plan['cases']:
        key = fixture['key']
        cid = str(uuid5(UUID(plan['tenant_id']), 'socai2.case.create:' + uid(key + '-case')))
        stage_ids = [str(uuid5(UUID(plan['tenant_id']), 'socai2.stage:' + uid(key + '-' + label))) for label in ('A0', 'A1', 'I')]
        runs = [r for r in data['runs'] if r['case_id'] == cid or r['id'] in stage_ids]
        entries = []
        for run in sorted(runs, key=lambda r: r['requested_at']):
            steps = [s for s in data['run_steps'] if s['run_id'] == run['id']]
            artifacts = [a for a in data['artifacts'] if a['run_id'] == run['id']]
            models = []
            for a in artifacts:
                if a['kind'] != 'model_response':
                    continue
                c = a['content_json']
                s = next(s for s in steps if s['id'] == a['step_id'])
                models.append({'artifact_id': a['id'], 'stage': s['stage_code'], 'name': s['name'],
                    'state': s['state'], 'usage': c.get('usage'),
                    'validation_error': c.get('validation_error') or c.get('payload', {}).get('validation_error'),
                    'transport_error': c.get('payload', {}).get('transport_error') or c.get('transport_error'),
                    'seconds': s.get('duration_ms'), 'parsed': parsed_response(c)})
            routes = [a['content_json'] for a in artifacts if (a.get('content_json') or {}).get('type') == 'followup_dispatch']
            results = [r for r in data['results'] if r['source_run_id'] == run['id']]
            queries = [{'stage': s['stage_code'], 'name': s['name'], 'state': s['state'], 'error': s['error']}
                for s in steps if s['kind'] == 'tool']
            entries.append({'id': run['id'], 'kind': run['kind'], 'state': run['state'], 'stop_reason': run['stop_reason'],
                'model_requests': sum(a['kind'] == 'model_request' for a in artifacts), 'models': models,
                'routes': routes, 'tools': queries, 'results': results})
        cases.append({'case': key, 'case_id': cid, 'runs': entries})
    result = {'export': str(directory.relative_to(ROOT)), 'counts': {k: len(v) for k, v in data.items()}, 'cases': cases}
    target = directory / 'analysis.json'
    assert not target.exists()
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    for case in cases:
        print(case['case'], [(r['kind'], r['state'], r['stop_reason'], r['model_requests']) for r in case['runs']])
        for run in case['runs']:
            for model in run['models']:
                if model['transport_error']:
                    print('TRANSPORT', model['transport_error'])
    print('calls', sum(r['model_requests'] for c in cases for r in c['runs']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    analyze(parser.parse_args().directory)
