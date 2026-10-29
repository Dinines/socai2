#!/usr/bin/env python3
"""Project existing alert-flow receipts into V2; never queries or writes services."""
import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


BLOCKED = {'prompt', 'prompt_block', 'messages', 'reasoning_content', 'reasoning',
           'api_key', 'authorization', 'password', 'access_token', 'secret', 'token'}
GRAPH_FIELDS = {'verdict', 'confidence', 'confidence_basis', 'findings', 'status',
                'budget_exhausted', 'budget_exhausted_reason', 'error', 'investigation_depth',
                'proposed_actions', 'executed_actions', 'ioc_enrichments', 'mitre_mappings',
                'context_bundle', 'started_at', 'completed_at', 'model_used', 'iteration_count'}
CALL_FIELDS = {'agent', 'model', 'purpose', 'timestamp', 'duration_ms', 'input_hash',
               'output_hash', 'prompt_truncated', 'response_truncated'}


def public(value):
    if isinstance(value, dict):
        return {k: public(v) for k, v in value.items() if k.lower() not in BLOCKED}
    if isinstance(value, list):
        return [public(v) for v in value]
    return value


def artifact_body(row):
    kind, content = row['kind'], row['content']
    if kind == 'llm_prompt':
        return {'mode': 'metadata', 'note': '此材料保留目录与原件标识，本页未载入提示词正文。'}
    if kind in {'report_md', 'report_html'}:
        return {'mode': 'full', 'format': 'text', 'content': content}
    value = json.loads(content)
    if kind == 'graph_llm_exchanges':
        value = [{k: v for k, v in call.items() if k in CALL_FIELDS} for call in value]
        return {'mode': 'excerpt', 'format': 'json', 'content': value,
                'note': '调用元数据；未包含提示词或回复正文。原件哈希对应完整保存材料。'}
    if kind == 'graph_result':
        value = public({k: v for k, v in value.items() if k in GRAPH_FIELDS})
        return {'mode': 'excerpt', 'format': 'json', 'content': value,
                'note': '调查结果节选；原件哈希对应完整保存材料。'}
    filtered = public(value)
    return {'mode': 'full' if filtered == value else 'excerpt', 'format': 'json',
            'content': filtered, 'note': '' if filtered == value else '读取结果节选；未包含提示词正文，原件哈希对应完整保存材料。'}


def project(source, organized_at):
    assert datetime.fromisoformat(organized_at.replace('Z', '+00:00')).tzinfo is not None
    raw = source.read_bytes()
    data = json.loads(raw)
    tenant = data['tenant_id']
    alerts = {a['id']: a for a in data['alerts']}
    groups = defaultdict(list)
    for alert in alerts.values():
        assert alert['tenant_id'] == tenant
        assert alert['case_id'] is None
        groups[alert['enrichment_data']['socai2_fusion']['incident_id']].append(alert)
    incidents = []
    levels = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1, 'info': 0}
    for identity, members in groups.items():
        members.sort(key=lambda a: (a['event_time'], a['id']))
        hosts = list(dict.fromkeys(h for a in members for h in a['affected_hosts']))
        peak = max(members, key=lambda a: levels.get(a['severity'], -1))['severity']
        incidents.append({
            'id': identity, 'recordedIncident': True, 'sourceEnvironment': 'socai2-21',
            'sourceTenantId': tenant, 'sourceCapturedAt': data['captured_at'],
            'sourceAlertIds': [a['id'] for a in members],
            'title': f'{"、".join(hosts) if hosts else "关联告警"} · {len(members)}条告警',
            'description': '成员告警：' + '；'.join(a['title'] for a in members),
            'severity': {'critical': '高', 'high': '高', 'medium': '中', 'low': '低', 'info': '低'}.get(peak, '未记录'),
            'status': 'Not set', 'classification': 'Not set', 'owner': '未记录',
            'priority': None, 'tags': [],
            'first': min(a['event_time'] for a in members),
            'last': max(a['event_time'] for a in members),
            'updated': max(a['updated_at'] for a in members),
        })
    runs = []
    for row in data['runs']:
        assert row['tenant_id'] == tenant and row['case_id'] in alerts
        events = [e for e in data['events'] if e['run_id'] == row['id']]
        events.sort(key=lambda e: (e['ts'], e['seq'], e['id']))
        steps = []
        for event in events:
            assert event['tenant_id'] == tenant
            payload = public(event['payload'])
            if event['kind'] == 'llm_call':
                payload = {k: v for k, v in payload.items() if k in CALL_FIELDS | {'response'}}
            steps.append({'id': event['id'], 'seq': event['seq'], 'name': event['agent'],
                          'kind': event['kind'], 'time': event['ts'], 'summary': event['summary'],
                          'payload': payload, 'duration_ms': event['duration_ms'] or None,
                          'input_hash': event['input_hash'], 'output_hash': event['output_hash']})
        bodies, directory = {}, []
        for artifact in data['artifacts']:
            if artifact['run_id'] != row['id']:
                continue
            assert artifact['tenant_id'] == tenant
            content = artifact['content'].encode()
            assert hashlib.sha256(content).hexdigest() == artifact['sha256']
            assert len(content) == artifact['size_bytes']
            assert any(e['id'] == artifact['event_id'] for e in events)
            bodies[artifact['id']] = artifact_body(artifact)
            directory.append({key: artifact[key] for key in
                              ('id', 'event_id', 'kind', 'created_at', 'sha256', 'size_bytes')})
        runs.append({'id': row['id'], 'sourceEnvironment': 'socai2-21', 'sourceTenantId': tenant,
                     'steps': steps, 'artifacts': directory, 'artifactBodies': bodies})
    cases = []
    for incident in incidents:
        members = incident['sourceAlertIds']
        cases.append({'id': 'local-socai2-' + incident['id'],
                      'title': incident['title'].split(' · ')[0] + ' 调查（本地整理）',
                      'localCollection': True, 'alertFlowCollection': True,
                      'sourceCaseId': None, 'sourceEnvironment': 'socai2-21',
                      'sourceTenantId': tenant, 'sourceCapturedAt': data['captured_at'],
                      'sourceAlertIds': members, 'alertIds': members,
                      'sourceRunIds': [r['id'] for r in data['runs'] if r['case_id'] in members],
                      'incidentId': incident['id'], 'created': organized_at, 'updated': organized_at,
                      'owner': '未分配', 'status': 'New', 'severity': incident['severity'],
                      'priority': None, 'classification': 'Not set', 'tags': [], 'tasks': [],
                      'description': '汇集同一事件的成员告警及已保存调查材料，供继续核查。' + incident['description']})
    output = {'capturedAt': data['captured_at'], 'tenantId': tenant, 'incidents': incidents,
              'runs': runs, 'cases': cases, 'organizedAt': organized_at}
    manifest = {'source': str(source), 'sha256': hashlib.sha256(raw).hexdigest(),
                'capturedAt': data['captured_at'], 'incidentCount': len(incidents),
                'alertCount': len(alerts), 'runCount': len(runs),
                'eventCount': sum(len(r['steps']) for r in runs),
                'artifactCount': sum(len(r['artifactBodies']) for r in runs),
                'localCaseCount': len(cases), 'organizedAt': organized_at,
                'bodyModes': {mode: sum(b['mode'] == mode for r in runs for b in r['artifactBodies'].values())
                              for mode in ['full', 'excerpt', 'metadata']}}
    return output, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--organized-at', required=True, help='Local collection time with explicit timezone; not backend Case creation time')
    args = parser.parse_args()
    output, manifest = project(args.source, args.organized_at)
    args.output.write_text('/* Saved alert-flow projection; no live calls. */\nwindow.alertFlowData = ' +
                           json.dumps(output, ensure_ascii=False, separators=(',', ':')) + ';\n')
    args.output.with_suffix('.manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
