"""Compare stored A/I runs with a historical reference; never call a model."""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

import jsonschema


def seconds(start, end):
    return (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() if start and end else None


def stages(data):
    alerts = {a['id']: a for a in data['alerts']}
    result = {}
    for run in data['runs']:
        if run['kind'] not in {'alert_basic', 'incident_diagnosis'}:
            continue
        alert = alerts.get(run.get('alert_id'))
        key = alert['title'] if alert else 'incident'
        artifacts = [a for a in data['artifacts'] if a.get('run_id') == run['id']]
        request = next(a['content_json'] for a in artifacts if a['kind'] == 'model_request')
        response = next(a['content_json'] for a in artifacts if a['kind'] == 'model_response')
        choice = response['raw']['choices'][0]
        content = choice['message']['content']
        parsed, schema_valid, parse_error = None, False, None
        try:
            parsed = json.loads(content)
            schema = request['body']['response_format']['json_schema']['schema']
            jsonschema.Draft202012Validator(schema).validate(parsed)
            schema_valid = True
        except (ValueError, jsonschema.ValidationError) as exc:
            parse_error = type(exc).__name__
        model = next(s for s in data['run_steps'] if s['run_id'] == run['id'] and s['kind'] == 'model')
        messages = request['body']['messages']
        query_results = [{k: a['content_json'].get(k) for k in ('tool_name', 'state', 'reason', 'returned_rows')}
                         for a in artifacts if a['kind'] == 'tool_response']
        result[key] = {'run_id': run['id'], 'state': run['state'], 'delivery_state': run['delivery_state'],
                       'stop_reason': run['stop_reason'], 'finish_reason': choice['finish_reason'],
                       'usage': response['usage'], 'model_step_seconds': seconds(model['started_at'], model['ended_at']),
                       'run_seconds': seconds(run['started_at'], run['ended_at']),
                       'user_bytes': len(messages[1]['content'].encode()), 'system_bytes': len(messages[0]['content'].encode()),
                       'output_bytes': len(content.encode()), 'wire_schema_valid': schema_valid, 'parse_error': parse_error,
                       'validation_error': response.get('validation_error'), 'judgment': (parsed or {}).get('verdict'),
                       'confidence': (parsed or {}).get('confidence'), 'query_results': query_results,
                       'alert_boundary': request.get('alert_boundary'), 'incident_boundary': request.get('incident_boundary'),
                       'request_artifact_id': next(a['id'] for a in artifacts if a['kind'] == 'model_request'),
                       'response_artifact_id': next(a['id'] for a in artifacts if a['kind'] == 'model_response')}
    return result


def compare(config_path):
    cfg = json.loads(config_path.read_text())
    root = config_path.parent
    old_path = Path(cfg['historical_comparator']['database'])
    new_path = max((root / 'exports').glob('*/database.json'))
    old, new = stages(json.loads(old_path.read_text())), stages(json.loads(new_path.read_text()))
    assert old.keys() == new.keys()
    comparisons = []
    for name in old:
        a, b = old[name], new[name]
        row = {'subject': name, 'old': a, 'new': b}
        row['changes_percent'] = {key: (b['usage'][key] / a['usage'][key] - 1) * 100
                                  for key in ('input_tokens', 'output_tokens', 'total_tokens')}
        row['changes_percent']['model_step_seconds'] = (b['model_step_seconds'] / a['model_step_seconds'] - 1) * 100
        comparisons.append(row)
    totals = {}
    for label, values in (('old', old), ('new', new)):
        totals[label] = {key: sum(r['usage'][key] for r in values.values())
                         for key in ('input_tokens', 'output_tokens', 'total_tokens')}
        totals[label]['model_step_seconds'] = sum(r['model_step_seconds'] for r in values.values())
        totals[label]['completed_runs'] = sum(r['state'] == 'completed' for r in values.values())
        totals[label]['wire_schema_valid'] = sum(r['wire_schema_valid'] for r in values.values())
    result = {'comparison': cfg['historical_comparator'], 'records': comparisons, 'totals': totals,
              'old_database_sha256': hashlib.sha256(old_path.read_bytes()).hexdigest(),
              'new_database_sha256': hashlib.sha256(new_path.read_bytes()).hexdigest(),
              'latency_measure': 'stored model step duration including local validation/persistence; not isolated HTTP latency',
              'not_accuracy_benchmark': True, 'model_calls_added_by_analysis': 0}
    path = root / 'comparison.json'
    with path.open('x') as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write('\n')
    print(json.dumps(totals))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    compare(parser.parse_args().config)
