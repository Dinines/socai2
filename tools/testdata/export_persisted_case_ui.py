#!/usr/bin/env python3
"""Export an existing historical Case receipt for V2, offline and read-only."""
import argparse
import hashlib
import json
from pathlib import Path


def project(root):
    sources = []

    def read(name, http=False):
        raw = (root / name).read_bytes()
        sources.append({'file': name, 'sha256': hashlib.sha256(raw).hexdigest()})
        value = json.loads(raw)
        if http:
            assert value['http_status'] in (200, 201)
            value = value['body']
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass
        return value

    # Tool records may contain metadata about prompting, but never export prompt bodies.
    def public(value):
        blocked = {'messages', 'prompt', 'prompt_block', 'response', 'reasoning_content',
                   'api_key', 'authorization', 'password', 'access_token'}
        if isinstance(value, dict):
            return {k: public(v) for k, v in value.items() if k.lower() not in blocked}
        if isinstance(value, list):
            return [public(v) for v in value]
        return value

    case = read('case-created.json', True)
    identity = read('active-case.json')
    run = read('run-detail.json', True)
    launch = read('investigation-launched.json', True)
    events = read('run-events.json', True)['items']
    directory = read('run-artifacts.json', True)
    state = read('observation/nodes/04-report_writer-output.json')
    assert case['id'] == identity['case_id'] == run['case_id'] == launch['case_id'] == state['case_id']
    assert run['id'] == identity['run_id'] == launch['run_id']
    # The Agent used an internal UUID. Bind its output to the persisted API Run
    # by the complete ordered ledger (including payload hashes), not that UUID.
    audit = state['audit_log']
    assert len(events) == len(audit) == 29
    for seq, (entry, event) in enumerate(zip(audit, events)):
        assert event['seq'] == seq and event['run_id'] == run['id']
        assert all(entry.get(k) == event.get(k) for k in
                   ('kind', 'agent', 'summary', 'input_hash', 'output_hash', 'duration_ms'))
        assert entry['metadata'] == event['payload']
    inputs = state['raw_alert']['alerts']
    assert set(case['alert_ids']) == {a['id'] for a in inputs} == set(identity['alert_ids'])
    tenant = identity['tenant_id']
    assert state['tenant_id'] == tenant
    artifacts, graphs, report = [], {}, None
    for row in directory:
        a = read(f'artifact-{row["kind"]}-{row["id"]}.json', True)
        assert a['id'] == row['id'] and a['kind'] == row['kind']
        content = a['content']
        assert hashlib.sha256(content.encode()).hexdigest() == a['sha256']
        assert len(content.encode()) == a['size_bytes']
        artifacts.append({k: a[k] for k in ('id', 'kind', 'sha256', 'size_bytes', 'event_id', 'created_at')})
        if a['kind'] == 'report_md':
            report = content
        else:
            c = json.loads(content)
            assert c['case_id'] == case['id'] and c['tenant_id'] == tenant
            graphs[a['kind']] = {**c[a['kind']], 'queried_at': c['queried_at']}
    report_file = (root / 'report.md').read_bytes()
    sources.append({'file': 'report.md', 'sha256': hashlib.sha256(report_file).hexdigest()})
    assert report_file.decode() == report == read('report-response.json', True) == state['report_md']
    phases = {'recon': state['recon'], 'forensic': state['forensic'], 'responder': state['responder']}
    # Keep the separate stage outputs as proof the final adopted data was not reconstructed.
    for name, key in [('01-recon-output', 'recon'), ('02-forensic-output', 'forensic'), ('03-responder-output', 'responder')]:
        stage = read('observation/nodes/' + name + '.json')
        assert stage['run_id'] == state['run_id'] and stage['case_id'] == case['id']
        assert stage[key] == phases[key]
    steps, tools = [], []
    allowed = {'tool', 'args', 'result', 'success', 'model', 'purpose', 'tokens_used', 'cost_source',
               'duration_ms', 'generation_status', 'report_hash', 'report_source', 'ref', 'evidence_kind',
               'weight', 'reason', 'decision', 'confidence', 'alternatives', 'enrichment', 'ioc_count',
               'input_hash', 'output_hash'}
    for e in events:
        assert e['run_id'] == run['id']
        payload = public({k: v for k, v in e['payload'].items() if k in allowed})
        step = {'seq': e['seq'], 'kind': e['kind'], 'name': e['agent'], 'time': e['ts'],
                'summary': e['summary'], 'payload': payload}
        if e['kind'] in phases:
            step['adopted'] = phases[e['kind']]
        steps.append(step)
        if e['kind'] == 'tool_call':
            tools.append({'name': payload['tool'], 'args': payload['args'], 'time': e['ts'],
                          'result': json.dumps(payload['result'], ensure_ascii=False, indent=2),
                          'resultFormat': 'saved_result', 'success': payload['success']})
    adopted = state['forensic']
    r = {'id': run['id'], 'agentRunId': state['run_id'], 'sourceCaseId': case['id'], 'sourceEnvironment': 'socai2-21',
         'sourceTenantId': tenant, 'title': case['title'], 'recorded': True,
         'alertIds': [a['id'] for a in inputs], 'input': state['raw_alert'], 'input_summary': run['alert_summary'],
         'status': run['status'], 'completion': None, 'verdict': None,
         'confidence': adopted['confidence'], 'confidenceLabel': '取证分析置信度',
         'findings': [state['recon']['summary'], adopted['summary'], state['responder']['summary']],
         'started': run['started_at'], 'ended': run['completed_at'], 'steps': steps, 'tools': tools,
         'graphs': graphs, 'artifacts': artifacts, 'report': report, 'stop': None,
         'calls': run['measured_call_count'] + run['estimated_call_count'] + run['unpriced_call_count'],
         'tokens': run['total_tokens'], 'unpriced': run['unpriced_call_count'],
         'actions': [{'description': a['action'], 'rationale': a['rationale'], 'priority': a['priority'],
                      'risk': a['risk']} for a in state['responder']['recommended_actions']],
         'executed': [], 'remediation': 'dry_run=true · 仅生成响应建议', 'triage': None,
         'timeNote': '过程记录的原始时间与 Run 起止时间存在 8 小时差异；按来源原值展示，未推测修正。'}
    assets, alerts = {}, []
    path = graphs['attack_path']['data']
    for a in inputs:
        ids = []
        for key, kind in [('affected_hosts', 'device'), ('affected_users', 'user'), ('affected_ips', 'ip')]:
            for value in a.get(key, []):
                aid = f'raw:{tenant}:{kind}:{value}'
                assets[aid] = {'id': aid, 'type': kind, 'name': value, 'tags': [], 'inventory': False,
                               'sourceEnvironment': 'socai2-21'}
                ids.append(aid)
        nodes = {n['id']: n for n in path['nodes']}
        techniques = [nodes[e['target']]['properties'].get('technique_id', e['target'])
                      for e in path['edges'] if e['source'] == a['id'] and e['type'] == 'MAPS_TO']
        alerts.append({'id': a['id'], 'title': a['title'], 'description': a['description'],
            'persistedRecord': True, 'sourceEnvironment': 'socai2-21', 'sourceTenantId': tenant,
            'severity': {'high': '高', 'medium': '中', 'low': '低'}.get(a['severity'], a['severity']),
            'status': 'Unknown', 'investigation': 'Completed', 'owner': '未分配', 'category': '—',
            'source': a['source'], 'entityIds': ids, 'tags': [], 'classification': 'Not set',
            'event_time': a['event_time'], 'first': a['event_time'], 'last': None,
            'incidentId': None, 'caseId': case['id'], 'comments': [], 'disposition': None,
            'hostNames': a['affected_hosts'], 'tactics': [], 'iocKeys': ['ip:' + ip for ip in a['affected_ips']],
            'detailMaterial': {'timelineVersion': 2, 'history': [{'time': a['event_time'], 'title': '告警发生', 'description': a['title']}],
                'runs': [], 'caseInvestigation': {'caseId': case['id'], 'runId': run['id'], 'inputCount': len(inputs)},
                'tenantName': tenant, 'techniques': techniques,
                'explanation': {'generatedAt': None, 'summary': '', 'suggestedActions': []},
                'confidence': {'score': None}, 'risk': None, 'raw': a, 'responseRecommendations': []}})
    result = {'cases': [{'id': case['id'], 'title': case['title'], 'description': case['description'],
                        'recordedCase': True, 'sourceEnvironment': 'socai2-21', 'sourceCaseId': case['id'],
                        'sourceTenantId': tenant, 'alertIds': case['alert_ids'], 'sourceRunIds': [run['id']],
                        'created': case['created_at'], 'updated': case['updated_at'], 'owner': case['assignee'] or '未分配',
                        'status': {'new': 'New'}[case['status']], 'severity': '高', 'priority': None,
                        'classification': 'Not set', 'tags': [], 'tasks': [], 'incidentId': None,
                        'due': case['sla_due_at'], 'sourceRecord': case}],
              'runs': [r], 'alerts': alerts, 'assets': list(assets.values())}
    return result, {'sources': sources, 'sourceRoot': '.local/aisoc21/attack-context-20261021/case-v2',
                    'caseId': case['id'], 'runId': run['id'], 'agentRunId': state['run_id'],
                    'identityVerification': '29 ordered audit entries and payloads match persisted Run events; report identical',
                    'inputKind': 'synthetic',
                    'environment': 'local API/Agents with 21 infrastructure; historical 2026-10-21 receipt',
                    'timeNote': r['timeNote'], 'completeness': 'not recorded; Run completed kept separate'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data, manifest = project(args.source)
    args.output.write_text('/* Historical persisted Case and joint Run; no live calls. */\n'
                          'window.persistedCaseData = ' + json.dumps(data, ensure_ascii=False, indent=2) + ';\n')
    args.output.with_suffix('.manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
