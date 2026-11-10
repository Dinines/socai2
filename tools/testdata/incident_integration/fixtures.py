"""Copy declared input fields; labels, explanations and expected verdicts stay out."""
import copy
import json
from uuid import NAMESPACE_URL, uuid5


def identity(batch, value):
    return str(uuid5(NAMESPACE_URL, batch + ':' + value))


def packets(root, config):
    database = json.loads((root / config['snapshot']).read_text())
    run = next(r for r in database['runs'] if r['id'] == config['source_incident_run'])
    source = next(a['content_json'] for a in database['artifacts'] if a['id'] == run['input_artifact_id'])
    corpus = {item['id']: item for item in json.loads((root / config['corpus']).read_text())['decisions']}
    samples = []
    for scenario in config['scenarios']:
        members = []
        if scenario['kind'] == 'recorded_materials':
            for member in source['members']:
                alert = {k: copy.deepcopy(member['alert'].get(k)) for k in
                    ('title', 'description', 'event_time', 'event_time_source', 'severity', 'original_vendor')}
                material = {k: copy.deepcopy(member['material'].get(k)) for k in
                    ('raw_text', 'raw_json', 'ocsf_json', 'detection', 'enrichment', 'source_scope', 'retention', 'material_state')}
                members.append({'alert': alert, 'material': material})
        else:
            for index, template in enumerate(scenario['templates']):
                item = corpus[template]
                evidence = copy.deepcopy(item['evidence'])
                material = {'raw_json': {scenario['block']: evidence}, 'raw_text': json.dumps(evidence, ensure_ascii=False),
                    'ocsf_json': None, 'detection': {'rule_id': item['rule_id'], 'rule_name': item['title']},
                    'enrichment': {}, 'source_scope': {'kind': 'synthetic_corpus', 'complete': True, 'truncated': False},
                    'retention': {}, 'material_state': 'complete'}
                members.append({'alert': {'title': item['title'], 'description': item['title'],
                    'event_time': None, 'event_time_source': 'unknown', 'severity': item['severity'], 'original_vendor': item['vendor']},
                    'material': material if index == 0 or scenario['material'] == 'all' else None})
        for index, member in enumerate(members):
            member['alert_id'] = identity(config['batch'], scenario['key'] + f':alert:{index}')
            member['material_id'] = identity(config['batch'], scenario['key'] + f':material:{index}') if member['material'] else None
        samples.append({'key': scenario['key'], 'title': scenario['title'], 'members': members,
            'incident_id': identity(config['batch'], scenario['key'] + ':incident'),
            'operation_key': identity(config['batch'], scenario['key'] + ':I')})
    return samples
