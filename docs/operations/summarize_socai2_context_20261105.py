"""Independent fixed-ID and value comparison; no remote access or inference."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '.local/testdata/k4-context-20261105'


def main():
    oracle = json.loads((OUT / 'expected.json').read_text('utf-8'))['cases']
    expectations = {c['case_key']: c for c in oracle}
    old_plan = json.loads((ROOT / 'docs/operations/evidence/socai2-kafka-chain-20261105/k2/plan.json').read_text('utf-8'))
    previous = {c['key']: c['events'] for c in old_plan['cases']}
    queries = json.loads((OUT / 'tools.json').read_text('utf-8'))
    classes = {'network_connections': 4001, 'process_activity': 1007, 'authentication_activity': 3002}
    summary, checked_counters = [], 0
    for query in queries:
        key, tool = query['case_key'], query['tool_name']
        wanted = set(expectations[key]['included'][tool]) if key in expectations else set()
        wanted.update(e['event_id'] for e in previous[key] if e['ocsf_event']['class_uid'] == classes[tool])
        actual = {row['event_id'] for row in query['rows']}
        assert actual == wanted and len(actual) == len(query['rows']), (key, tool, actual ^ wanted)
        for row, projection in zip(query['rows'], query['projection'], strict=True):
            traffic = expectations.get(key, {}).get('traffic', {}).get(row['event_id'])
            if traffic is None:
                continue
            fields = {f['name']: f for f in projection['fields']}
            for name, number in traffic.items():
                f = fields['network_' + name]
                assert f['value'] == number and f['source_path'] == '$.ocsf_json.traffic.' + name
                assert f['conflict'] is False
                checked_counters += 1
        summary.append({'case_key': key, 'tool': tool, 'exact_event_set': True, 'rows': len(actual)})
    readback = json.loads((OUT / 'readback.json').read_text('utf-8'))
    consumer = json.loads((OUT / 'consumer.json').read_text('utf-8'))
    cleanup = json.loads((OUT / 'cleanup.json').read_text('utf-8'))
    assert consumer['passed'] and readback['all_40_exactly_once'] and readback['old_lake_rows'] == 0
    assert readback['pg_counts_unchanged'] and readback['protected_unchanged'] and cleanup['temporary_writer_removed']
    assert len(queries) == 18 and checked_counters == 96
    result = {'batch': 'k4-context-20261105', 'new_lake_rows': 40,
        'context_rows': 28, 'excluded_controls': 12, 'actual_queries': 18,
        'returned_rows_including_8_prior_source_events': sum(q['row_count'] for q in queries),
        'traffic_values_verified': checked_counters, 'all_exact_event_sets': True,
        'old_lake_new_rows': 0, 'new_alerts': 0, 'new_runs': 0, 'model_calls': 0,
        'temporary_writer_removed': True, 'pg_counts_unchanged': True, 'protected_unchanged': True,
        'scope': 'real Kafka/Fusion/new CH and deployed LakeGateway; candidate traffic projection loaded only in diagnostic process',
        'not_proven': ['C4 model chooses these tools', 'later model consumes/adopts all context rows', 'complete C6 quality'],
        'queries': summary, 'evidence_directory': '.local/testdata/k4-context-20261105'}
    target = ROOT / 'docs/operations/socai2-context-k4-20261105.json'
    with target.open('x', encoding='utf-8') as out:
        json.dump(result, out, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k != 'queries'}))


if __name__ == '__main__':
    main()
