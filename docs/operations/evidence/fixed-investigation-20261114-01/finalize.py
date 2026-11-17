"""Read completed batch artifacts; export exact A/I inputs and a comparison receipt."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    body = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_text() == body, 'existing_evidence_differs:' + str(path)
    else:
        with path.open('x') as handle:
            handle.write(body)


data = read(HERE / 'demo-export/database.json')
runs = {r['id']: r for r in data['runs']}
usage = dict.fromkeys(('prompt_tokens', 'completion_tokens', 'total_tokens'), 0)
stage_summaries = []
for group in ('E01', 'E02'):
    for folder in sorted((HERE / 'flow' / group).iterdir()):
        if not folder.is_dir():
            continue
        execution = read(folder / 'execution.json')
        run = runs[execution['run_id']]
        artifacts = [a for a in data['artifacts'] if a['run_id'] == run['id']]
        calls = []
        for file in sorted((folder / 'calls').glob('call-*-intent.json')):
            number = int(file.name.split('-')[1])
            body = read(file)['body']
            matches = [a for a in artifacts if a['kind'] == 'model_request' and a['content_json']['body'] == body]
            assert len(matches) == 1
            request = matches[0]
            response = next(a for a in artifacts if a['kind'] == 'model_response' and a['step_id'] == request['step_id'])
            receipt = read(folder / 'calls' / f'call-{number}-receipt.json')
            assert receipt['state'] == 'response_received'
            assert response['content_json']['raw'] == receipt['raw']
            raw = receipt['raw']
            for field in usage:
                assert isinstance(raw['usage'][field], int)
                usage[field] += raw['usage'][field]
            prefix = f'call-{number:02}'
            save(folder / 'review' / (prefix + '-input.txt'), body['messages'][1]['content'])
            save(folder / 'review' / (prefix + '-full-input.txt'), '\n\n'.join(m['role'] + ':\n' + m['content'] for m in body['messages'])
                 + '\n\nresponse_format:\n' + json.dumps(body.get('response_format'), ensure_ascii=False, indent=2))
            save(folder / 'review' / (prefix + '-answer.txt'), raw['choices'][0]['message']['content'])
            calls.append({'number': number, 'input': 'review/' + prefix + '-input.txt',
                          'answer': 'review/' + prefix + '-answer.txt', 'usage': raw['usage'],
                          'validation_error': response['content_json'].get('validation_error'),
                          'requests_and_raw_replies_equal_database': True})
        assert len(calls) == execution['model_calls']
        summary = {'group': group, 'stage': folder.name, 'run_id': run['id'],
                   'state': run['state'], 'stop_reason': run['stop_reason'], 'calls': calls}
        save(folder / 'summary.json', summary)
        stage_summaries.append(summary)

cases = [read(HERE / 'flow' / key / 'summary.json') for key in ('C01', 'C02', 'C03')]
for case in cases:
    assert case['usage_unknown'] is False
    for field in usage:
        usage[field] += case['known_usage'][field]

cfg = read(HERE / 'demo-config.json')
site_config = read(HERE / 'site-config.json')
manifest = read(HERE / 'demo-export/manifest.json')
site = read(HERE / 'site-after-C03-remote.json')
links = []
for case in cases:
    identity = '!'.join(('socai2', cfg['source_environment'], cfg['batch'], data['cases'][0]['tenant_id'], 'case', case['case_id']))
    index = site['case_ids'].index(case['case_id'])
    links.append({'scenario': case['scenario'], 'case_id': case['case_id'],
                  'demo': cfg['preview_base_url'] + '/#/cases/' + identity + '/case-info',
                  'audit': site_config['deployment']['base_url'] + '/index.html#' + site['record_ids'][index]})

save(HERE / 'comparison.json', {
    'batch': cfg['batch'], 'input_kind': 'synthetic',
    'counts': {table: len(data[table]) for table in ('alerts', 'incidents', 'cases', 'runs', 'results', 'case_assessments')},
    'A_I': stage_summaries,
    'cases': [{k: c[k] for k in ('scenario', 'case_id', 'run_id', 'run_state', 'stop_reason', 'results', 'real_model_calls', 'known_usage')} for c in cases],
    'real_model_calls': sum(len(s['calls']) for s in stage_summaries) + sum(c['real_model_calls'] for c in cases),
    'usage': usage, 'cost': None, 'cost_state': 'unpriced',
    'source_snapshot_sha256': manifest['source_sha256'],
    'case_ASGI_GETs': sum(len(read(HERE / 'flow' / c['scenario'] / 'export/http-readback.json')) for c in cases),
    'case_GETs_and_raw_artifacts_equal_database': all(c['requests_and_raw_replies_equal_database'] and c['result_H_and_current_GETs_equal_database'] for c in cases),
    'quality': 'NOT_PASSED', 'links': links,
    'limitations': ['ASGI with explicit authentication/dependency overrides is not live TCP/auth acceptance.',
                    'C01/C02 share this batch A/I; background retrieval may change, so this is not controlled A/B.',
                    'No independent truth or accuracy claim. Model quality remains deferred; accepted is not quality passed.',
                    'Static demo snapshots; no production database insert, streaming execution or H-only C6 automation.'],
})
save(HERE / 'demo-export/ui-review.json', {
    'method': 'CUA browser inspection of rendered 4173 and 4177 pages',
    'observed': ['4177 lists exactly C01/C02/C03 and exposes the actual C03 C6 failure and raw step links.',
                 '4173 case list filtered by batch shows exactly three cases.',
                 'C01 shows the saved adopted assessment and three original members.',
                 'C02 and C03 show no current case judgment, matching their rejected/null results.',
                 'C02 completed human task displays the original text, version 1 and limited scope.',
                 'Alert list shows all four batch alerts; incident search shows both batch incidents.',
                 'C02 overview includes A/I results, partial Case delivery and the rejection stop reason.'],
    'model_calls': 0, 'business_writes': 0, 'browser_local_storage_cleared': False,
    'limitations': ['Direct viewing check only; no complete frontend regression or live service-mode acceptance.'],
})
print(json.dumps({'model_calls': read(HERE / 'comparison.json')['real_model_calls'], 'usage': usage,
                  'A_I_runs': len(stage_summaries), 'case_ASGI_GETs': read(HERE / 'comparison.json')['case_ASGI_GETs']}, ensure_ascii=False))
