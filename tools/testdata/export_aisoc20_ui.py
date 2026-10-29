#!/usr/bin/env python3
"""Offline, allowlisted projection of the saved 2026-10-24 AiSOC20 showcase.

No service access, data replay or model invocation. Source payloads remain local.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

TACTICS = {'Execution': '执行', 'Command and Control': '命令与控制',
           'Credential Access': '凭据访问', 'Lateral Movement': '横向移动',
           'Collection': '收集', 'Exfiltration': '数据外传'}
PAYLOAD_FIELDS = {'node', 'step_status', 'reason', 'workflow', 'completion',
                  'stop_reasons', 'args', 'tool', 'result_preview', 'verdict',
                  'confidence', 'rationale', 'auto_closed', 'findings',
                  'purpose', 'model', 'duration_ms', 'prompt_truncated', 'response_truncated'}


def iso(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).isoformat()


def project(source, evidence, collected_at):
    files = []

    def read(path):
        raw = path.read_bytes()
        files.append({'file': path.name, 'sha256': hashlib.sha256(raw).hexdigest()})
        return json.loads(raw)

    canonical = read(source)
    alerts_by_id = {a['id']: a for a in canonical['rows']}
    verification = read(evidence / 'final-read-verification.json')
    rows = {r['alert_id']: r for r in verification['rows']}
    graph = read(evidence / 'final-graph-overview.json')
    out = {'alerts': [], 'assets': [], 'cases': [], 'runs': [], 'graph': {},
           'provenance': {'environment': 'aisoc20', 'inputKind': 'synthetic',
                          'capturedAt': canonical['captured_at'], 'collectedAt': collected_at}}
    entities = {}
    for i in range(1, 4):
        scenario = read(evidence / f'final-{i}.json')
        case_id = f'local-aisoc20-{i}'
        for aid, original in zip(scenario['alert_ids'], scenario['inputs'], strict=True):
            a, row = alerts_by_id[aid], rows[aid]
            assert a['tenant_id'] == original['tenant_id']
            assert a['title'] == original['title']
            assert a['case_id'] is None and row['case_id'] is None
            d = read(evidence / f'final-{i}-{aid}-delivery.json')
            assert d['alert_id'] == aid and d['run_id'] == row['run_id'] and d['case_id'] is None
            steps = [{'seq': e['seq'], 'kind': e['kind'], 'name': e['agent'],
                      'time': iso(e['ts']), 'summary': e.get('summary'),
                      'payload': {k: v for k, v in (e.get('payload') or {}).items() if k in PAYLOAD_FIELDS}}
                     for e in d['audit_log']]
            triage = next((s['payload'] for s in steps if s['kind'] == 'triage_verdict'), None)
            costs = [c for c in verification['costs'] if c['run_id'] == d['run_id']]
            calls = sum(c['call_count'] for c in costs)
            tokens = sum(c['total_prompt_tokens'] + c['total_completion_tokens'] for c in costs)
            tools = [{'name': s['payload']['tool'], 'time': s['time'], 'args': s['payload']['args'],
                      'result': s['payload'].get('result_preview')} for s in steps if s['kind'] == 'tool_call']
            stop = '；'.join(d.get('stop_reasons') or [])
            r = {'id': d['run_id'], 'alertIds': [aid], 'title': a['title'], 'recorded': True,
                 'sourceEnvironment': 'aisoc20', 'sourceTenantId': a['tenant_id'], 'sourceCaseId': None,
                 'status': d['status'], 'started': iso(d.get('started_at')), 'ended': iso(d.get('completed_at')),
                 'completion': d['completion'], 'verdict': d.get('verdict') or (triage or {}).get('verdict'),
                 'confidence': d.get('confidence'), 'triage': triage, 'findings': d.get('findings') or [],
                 'steps': steps, 'tools': tools, 'depth': d.get('investigation_depth'), 'graphs': {},
                 'artifacts': [x for x in verification['artifacts'] if x['run_id'] == d['run_id']],
                 'actions': d.get('proposed_actions') or [], 'executed': d.get('executed_actions') or [],
                 'report': d.get('report_md'), 'stop': stop, 'rawStopReasons': d.get('raw_stop_reasons'),
                 'input': d.get('raw_alert'), 'input_summary': d.get('alert_summary'),
                 'calls': calls, 'tokens': tokens}
            if r['report']:
                report_path = evidence / f'final-{i}-{aid}-report.md'
                raw = report_path.read_bytes()
                assert raw.decode() == r['report']
                files.append({'file': report_path.name, 'sha256': hashlib.sha256(raw).hexdigest()})
            out['runs'].append(r)
            entity_ids = []
            for kind, value in [('device', original.get('hostname')), ('user', original.get('username')),
                                ('ip', original.get('src_ip')), ('ip', original.get('dst_ip'))]:
                if not value:
                    continue
                key = f'raw:aisoc20:{a["tenant_id"]}:{kind}:{value}'
                entities[key] = {'id': key, 'name': value, 'type': kind, 'inventory': False,
                                 'tags': [], 'sourceEnvironment': 'aisoc20'}
                if key not in entity_ids:
                    entity_ids.append(key)
            raw = {k: a[k] for k in ('id', 'tenant_id', 'title', 'description', 'severity', 'status',
                                    'event_time', 'case_id', 'confidence', 'ai_score', 'disposition')}
            for k in ('raw_event', 'entities', 'enrichment_data'):
                raw[k] = json.loads(a[k]) if isinstance(a[k], str) else a[k]
            raw['incident_id'] = row.get('incident_id')
            raw['original_input'] = original
            history = [{'time': iso(a['event_time']), 'title': '告警发生', 'description': a['title']}]
            history += [{'time': s['time'], 'title': '自动分诊完成' if s['kind'] == 'triage_verdict' else '调查结果交付',
                         'description': s['summary']} for s in steps if s['kind'] in ('triage_verdict', 'graph_result')]
            trace = {'id': r['id'], 'time': r['started'] or steps[0]['time'], 'status': 'Completed',
                     'completion': r['completion'], 'stop': stop, 'findings': r['findings'],
                     'calls': calls, 'tokens': tokens, 'report': r['report'],
                     'actions': [x['description'] for x in r['actions']],
                     'steps': [{'name': s['name'], 'agent': s['name'],
                                'status': '已跳过' if s['payload'].get('step_status') == 'skipped' else 'Completed',
                                'input': {}, 'output': s['payload']} for s in steps if s['kind'] != 'llm_call'],
                     'tools': [{**t, 'status': '已保存返回摘要'} for t in tools]}
            out['alerts'].append({
                'id': aid, 'persistedRecord': True, 'sourceEnvironment': 'aisoc20', 'sourceTenantId': a['tenant_id'],
                'title': a['title'], 'description': a['description'], 'severity': {'high': '高', 'critical': '高', 'medium': '中'}.get(a['severity'], '低'),
                'status': 'Resolved' if a['status'] in ('resolved', 'closed') else 'In progress' if r['completion'] != 'not_escalated' else 'New',
                'investigation': 'Completed', 'owner': '未分配', 'category': '、'.join(TACTICS.get(t, t) for t in original['mitre_tactics']) or '—',
                'source': original['source'], 'entityIds': entity_ids, 'tags': [], 'classification': 'Not set',
                'event_time': iso(a['event_time']), 'first': iso(a['event_time']), 'last': None,
                'incidentId': row.get('incident_id'), 'caseId': None, 'comments': [], 'disposition': a['disposition'],
                'hostNames': [original['hostname']], 'tactics': original['mitre_tactics'],
                'iocKeys': [f'ip:{original[k]}' for k in ('src_ip', 'dst_ip') if original.get(k)],
                'detailMaterial': {'timelineVersion': 2, 'history': history, 'runs': [trace],
                    'tenantName': a['tenant_id'], 'techniques': original['mitre_techniques'],
                    'explanation': {'generatedAt': None, 'summary': '', 'suggestedActions': []},
                    'confidence': {'score': a['confidence']}, 'risk': round(a['ai_score'] * 100) if a['ai_score'] is not None else None,
                    'raw': raw, 'responseRecommendations': [{'action': x['description'], 'target': x.get('target'),
                        'reason': x.get('rationale'), 'approval': '需要审批' if x.get('requires_approval') else '未记录',
                        'execution': '未执行' if not r['executed'] else '有执行记录，需核对'} for x in r['actions']]}})
        out['cases'].append({'id': case_id, 'title': scenario['scenario'] + '（本地整理）',
            'localCollection': True, 'sourceCaseId': None, 'sourceEnvironment': 'aisoc20',
            'alertIds': scenario['alert_ids'], 'created': collected_at, 'updated': collected_at,
            'owner': '未分配', 'status': 'New', 'severity': '高', 'priority': None, 'classification': 'Not set',
            'tags': [], 'tasks': [], 'incidentId': None,
            'description': '按 2026-10-24 AiSOC 演示场景整理的本地案件。输入是合成告警，分诊、查询与报告为当时实际运行结果；源系统未创建 Case。'})
    out['assets'] = list(entities.values())
    ids = {a['id'] for a in out['alerts']}
    edges = [e for e in graph['edges'] if e['source'] in ids or e['target'] in ids]
    node_ids = {v for e in edges for v in (e['source'], e['target'])}
    out['graph'] = {'generatedAt': graph['generatedAt'], 'edges': edges,
                    'nodes': [n for n in graph['nodes'] if n['id'] in node_ids]}
    return out, {'provenance': out['provenance'], 'sources': files,
                 'counts': {k: len(out[k]) for k in ('alerts', 'runs', 'cases', 'assets')},
                 'note': '仅离线白名单展示；无后端 Case，报告中的判断保留来源，不代表质量验收。'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--collected-at', required=True)
    args = parser.parse_args()
    data, manifest = project(args.source, args.evidence, iso(args.collected_at))
    args.output.write_text('/* Historical synthetic inputs; actual AiSOC20 runtime results. */\n'
                          'window.aisoc20RecordedData = ' + json.dumps(data, ensure_ascii=False, indent=2) + ';\n')
    args.output.with_suffix('.manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
