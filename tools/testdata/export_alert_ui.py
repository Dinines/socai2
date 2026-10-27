"""Export a whitelisted, offline alert projection from recorded PostgreSQL/Explain reads.

Does not query or mutate services. The static prototype retains its original fixtures.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

TACTICS = {'Execution': '执行', 'Credential Access': '凭据访问', 'Lateral Movement': '横向移动',
           'Collection': '收集', 'Exfiltration': '数据外泄', 'Command and Control': '命令与控制',
           'Initial Access': '初始访问', 'Persistence': '持久化', 'Defense Evasion': '防御规避'}


def iso(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).isoformat() if value else None


def severity(value):
    return {'critical': '高', 'high': '高', 'medium': '中', 'low': '低',
            'inform': '低', 'informational': '低', 'info': '低'}.get(str(value).lower(), '—')


def status(value, investigation_started=False):
    if value in ('resolved', 'closed'):
        return 'Resolved'
    if value in ('investigating', 'in_progress') or investigation_started:
        return 'In progress'
    return 'New' if value in ('new', 'triaging', 'triaged') else value


def project(snapshot, explanations):
    result = {'alerts': [], 'assets': []}
    entities = {}
    for a in snapshot['alerts']:
        aid = a['id']
        runs = [r for r in snapshot['runs'] if r.get('raw_alert', {}).get('id') == aid]
        run_ids = {r['id'] for r in runs}
        events = sorted([e for e in snapshot['events'] if e['run_id'] in run_ids], key=lambda e: iso(e['ts']))
        fusion = (a.get('enrichment_data') or {}).get('socai2_fusion', {})
        incident_id = fusion.get('incident_id')
        if not incident_id:
            raise ValueError(f'Alert {aid} has no verified incident ID')
        entity_ids = []
        # Inventory associations are authoritative; raw entities never become invented asset IDs/tags.
        links = [x for x in snapshot.get('asset_links', []) if x.get('alert_id') == aid]
        for link in links:
            asset = next((x for x in snapshot.get('assets', []) if x['id'] == link['asset_id']), None)
            if asset:
                key = asset['id']
                entities[key] = {'id': key, 'type': 'device', 'name': asset['name'],
                                 'tags': asset.get('tags') or [], 'inventory': True}
                entity_ids.append(key)
        raw_entities = [(e.get('type'), e.get('value')) for e in a.get('entities') or []]
        raw_entities += [(e.get('type'), e.get('value')) for e in a.get('iocs') or []]
        for kind, value in raw_entities:
            if not value:
                continue
            kind = {'host': 'device', 'hostname': 'device', 'sha256': 'file', 'sha1': 'file', 'md5': 'file'}.get(kind, kind)
            key = f'raw:{a["tenant_id"]}:{kind}:{value}'
            entities[key] = {'id': key, 'type': kind, 'name': value, 'tags': [], 'inventory': False}
            if key not in entity_ids:
                entity_ids.append(key)
        owner = next((u for u in snapshot.get('owners', []) if u['id'] == a.get('assigned_to_id')), None)
        source = fusion.get('identity', {}).get('source') or '—'
        explanation = explanations.get(aid, {})
        history = [{'time': iso(a['event_time']), 'title': '告警发生', 'description': a['title']},
                   {'time': iso(a['created_at']), 'title': '告警入库', 'description': f'接收来自 {source} 的告警'}]
        names = {'triage_started': '自动分诊开始', 'triage_verdict': '自动分诊完成', 'graph_result': '调查结果交付'}
        for e in events:
            if e['kind'] in names:
                history.append({'time': iso(e['ts']), 'title': names[e['kind']], 'description': e['summary']})
        first_step = next((e for e in events if e['kind'] == 'graph_step'), None)
        if first_step:
            history.append({'time': iso(first_step['ts']), 'title': '调查步骤已记录', 'description': first_step['summary']})
        if a.get('assigned_at'):
            history.append({'time': iso(a['assigned_at']), 'title': '告警分配', 'description': (owner or {}).get('display_name') or a['assigned_to_id']})
        if a.get('resolved_at'):
            history.append({'time': iso(a['resolved_at']), 'title': '告警关闭', 'description': a.get('disposition') or a['status']})
        traces, responses = [], []
        for r in runs:
            re = [e for e in events if e['run_id'] == r['id']]
            artifacts = {x['kind']: x for x in snapshot['artifacts'] if x['run_id'] == r['id']}
            graph = json.loads(artifacts['graph_result']['content']) if 'graph_result' in artifacts else {}
            verdict = next((e['payload'] for e in re if e['kind'] == 'triage_verdict'), {})
            ge = next((e['payload'] for e in re if e['kind'] == 'graph_result'), {})
            completion = ge.get('completion', 'not_escalated' if verdict.get('auto_closed') else 'unknown')
            steps = []
            for e in re:
                if e['kind'] == 'triage_verdict':
                    steps.append({'name': '告警分诊', 'agent': e['agent'], 'status': 'Completed',
                                  'input': {'alert_id': aid}, 'output': {k: e['payload'].get(k) for k in ('verdict', 'confidence', 'rationale', 'auto_closed')}})
                if e['kind'] == 'graph_step':
                    steps.append({'name': e['payload']['node'], 'agent': e['agent'], 'status': 'Completed',
                                  'input': None, 'output': e['payload']})
            tools = [{'name': e['payload'].get('tool'), 'status': '已记录返回摘要（最多 200 字符）',
                      'args': e['payload'].get('args'), 'result': e['payload'].get('result_preview')}
                     for e in re if e['kind'] == 'tool_call']
            proposals = graph.get('proposed_actions') or []
            executed = graph.get('executed_actions') or []
            for action in proposals:
                responses.append({'action': action.get('description') or action.get('action_type'),
                                  'target': action.get('target') or '—', 'reason': action.get('rationale') or '',
                                  'approval': '需要审批' if action.get('requires_approval') else '无需审批',
                                  'execution': '有执行记录，需核对结果' if executed else '未执行'})
            calls = sum(c.get('call_count', 0) for c in snapshot['costs'] if c['run_id'] == r['id'])
            traces.append({'id': r['id'], 'time': iso(r.get('started_at') or r['created_at']),
                           'status': {'completed': 'Completed', 'failed': 'Failed', 'running': 'In progress'}.get(r['status'], r['status']),
                           'completion': completion, 'stop': graph.get('budget_exhausted_reason') or graph.get('error') or
                           ('自动分诊已关闭告警，未升级调查。' if verdict.get('auto_closed') else '未记录停止原因。'),
                           'steps': steps, 'tools': tools, 'findings': graph.get('findings') or verdict.get('findings') or [],
                           'actions': [x.get('description') or x.get('action_type') for x in proposals],
                           'calls': calls or None, 'tokens': r.get('total_tokens'),
                           'report': artifacts.get('report_md', {}).get('content')})
        raw_fields = ('id', 'tenant_id', 'title', 'description', 'severity', 'status', 'event_time', 'created_at',
                      'updated_at', 'resolved_at', 'source_event_ids', 'mitre_tactics', 'mitre_techniques', 'entities',
                      'iocs', 'raw_event', 'confidence', 'ai_score', 'disposition', 'case_id', 'assigned_to_id')
        result['alerts'].append({
            'id': aid, 'persistedRecord': True, 'title': a['title'], 'description': a.get('description') or '',
            'severity': severity(a['severity']), 'status': status(a['status'], bool(first_step)), 'investigation': 'Completed' if runs and all(r['status']=='completed' for r in runs) else 'Not started',
            'owner': ((owner or {}).get('display_name') or (owner or {}).get('email')) if owner else '未分配',
            'category': '、'.join(TACTICS.get(t, t) for t in (a.get('mitre_tactics') or [])) or '—',
            'source': source, 'entityIds': entity_ids, 'tags': [], 'classification': 'Not set',
            'event_time': iso(a['event_time']), 'first': iso(a['event_time']), 'last': iso(a.get('last_seen') or a['event_time']),
            'incidentId': incident_id, 'caseId': a.get('case_id'), 'comments': [], 'disposition': a.get('disposition'),
            'hostNames': a.get('affected_hosts') or [], 'tactics': a.get('mitre_tactics') or [],
            'iocKeys': [f'{x["type"]}:{x["value"]}' for x in a.get('iocs') or [] if x.get('type') in ('ip', 'sha256', 'sha1', 'md5')],
            'detailMaterial': {'timelineVersion': 2, 'history': history, 'runs': traces,
                'tenantName': snapshot['tenant_name'], 'techniques': a.get('mitre_techniques') or [],
                'explanation': {'generatedAt': explanation.get('generated_at'), 'summary': explanation.get('summary') or '',
                                'suggestedActions': explanation.get('suggested_actions') or [], 'llmUsed': explanation.get('llm_used')},
                'confidence': {'score': a.get('confidence')}, 'risk': round(a['ai_score']*100) if a.get('ai_score') is not None else None,
                'raw': {**{k: a.get(k) for k in raw_fields}, 'source': source, 'source_ref': fusion.get('identity', {}).get('source_alert_id'),
                        'incident_id': incident_id}, 'responseRecommendations': responses}
        })
    result['assets'] = list(entities.values())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', required=True, type=Path)
    parser.add_argument('--explain', required=True, nargs='+', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text())
    if not all(all(x[k] for k in ('present', 'bytes_match', 'hash_match')) for x in snapshot['integrity']):
        raise ValueError('Artifact integrity check failed')
    explanations = {}
    for path in args.explain:
        for line in path.read_text().splitlines():
            response = json.loads(line)
            if response['status'] != 200:
                raise ValueError('Explain response is not successful')
            explanations[response['alert_id']] = response['response']
    if {a['id'] for a in snapshot['alerts']} - explanations.keys():
        raise ValueError('Missing Explain response')
    data = json.dumps(project(snapshot, explanations), ensure_ascii=False, separators=(',', ':'))
    args.out.write_text("// Recorded service results; interactions remain browser-local. Generated by export_alert_ui.py.\n'use strict';\n(() => {\n const replay = " + data + ";\n const seed = window.makeDemoData;\n window.mergeReplayedAlerts = store => {\n  for (const key of ['alerts','assets']) {\n   const known = new Set(store[key].map(x=>x.id));\n   store[key].push(...structuredClone(replay[key].filter(x=>!known.has(x.id))));\n  }\n  return store;\n };\n window.makeDemoData = () => window.mergeReplayedAlerts(seed());\n})();\n")
    print(json.dumps({'alerts': len(snapshot['alerts']), 'bytes': args.out.stat().st_size}))


if __name__ == '__main__':
    main()
