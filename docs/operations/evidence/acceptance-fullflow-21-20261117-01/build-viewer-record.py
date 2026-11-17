"""Derive this batch's existing display ledger from saved execution receipts."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from investigation_test.models import Document

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads((ROOT/path).read_text())


def main():
    final = read('results/prepared/runs/part2/saved-records.json')
    first = read('results/prepared/runs/part1/saved-records.json')
    report = read('results/report-01/report.json')
    validation = read('final-validation.json')
    assert validation['status'] == 'passed_for_business_flow'
    output = ROOT/'viewer-input-02'
    output.mkdir()
    evidence = []

    def save(identity, label, value, source):
        name = identity+'.json'
        (output/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
        evidence.append({'id': identity, 'path': name, 'label': label, 'mime_type': 'application/json',
                         'visibility': 'public', 'source_ref': source})

    save('session-report', '两段会话报告、实际轮次及问题', report, 'results/report-01/report.json')
    save('validation', '同案后轮、保存和读取核验', validation, 'final-validation.json')
    manual = read('manual-quality-review.json')
    save('manual-quality', '比较类型与正文一致性问题', manual, 'manual-quality-review.json')
    save('preparation', '最终容器准入与追加前关联检查',
         {'admission': read('admission-02.json'), 'ttl': read('ttl-01.json')}, 'admission-02.json')
    exchanges = []
    for path in sorted((ROOT/'results/prepared').glob('runs/*/http/*.json')):
        if path.name.endswith('.intent.json'):
            continue
        row = json.loads(path.read_text())
        if row.get('request', {}).get('method') != 'POST' or row.get('outcome') != 'returned':
            continue
        body = row['response']['body']
        task_ids = ([body['task_id']] if body.get('task_id') else
                    [a['initial_task']['task_id'] for a in body.get('allocations', []) if a.get('initial_task')])
        for tid in task_ids:
            task = next(t for t in final['analysis_tasks'] if t['id'] == tid)
            attempts = [a for a in final['analysis_attempts'] if a['task_id'] == tid]
            for attempt in attempts or [None]:
                exchanges.append({'subject_type': task['subject_type'], 'subject_id': task['subject_id'],
                    'task_id': tid, 'run_id': attempt['run_id'] if attempt else None,
                    'observed_at': row['ended_at'],
                    'request': {k: row['request'][k] for k in ('method', 'path', 'body')},
                    'response': {k: row['response'][k] for k in ('status', 'body')},
                    'sources': [{'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}]})
    save('http-exchanges', '真实HTTP请求及受理回执',
         {'schema': 'socai2.test-http-exchanges.v1', 'source_execution_batch_id': report['execution_id'],
          'new_business_calls': 0, 'new_model_calls': 0, 'exchanges': exchanges}, 'results/prepared/runs')
    cases = []
    for part in report['parts']:
        assert part['closure_verified']
        cases.append({'id': part['id'], 'use_case_id': part['id'], 'scenario_id': 'process-network-two-parts',
                      'status': 'passed', 'expected': ['本段输入、处理、保存和HTTP读取完整，保持同一事件和Case'],
                      'actual': [part['recorded_state'], '输入/输出/来源逐值读回通过；正文质量单独记录'],
                      'operation_ids': [], 'evidence_ids': ['session-report', 'validation']})
    case_map = {c['id']: c for c in cases}
    first_tasks = {t['id'] for t in first['analysis_tasks']}
    task_parts, operations = {}, []
    result_tables = {'alert': ('alert_assessments', 'alert_assessment'),
                     'incident': ('incident_diagnoses', 'incident_diagnosis'), 'case': ('results', 'case_result')}
    for task in sorted(final['analysis_tasks'], key=lambda t: (t['submitted_at'], t['id'])):
        part = 'part1' if task['id'] in first_tasks else 'part2'
        mappings = []
        attempts = [a for a in final['analysis_attempts'] if a['task_id'] == task['id']]
        for attempt in attempts or [None]:
            rid = attempt['run_id'] if attempt else None
            mapping = {'subject_type': task['subject_type'], 'subject_id': task['subject_id'],
                       'task_id': task['id'], 'run_id': rid}
            table, kind = result_tables[task['subject_type']]
            result = next((r for r in final[table] if r['source_run_id'] == rid), None) if rid else None
            if result:
                mapping.update(result_type=kind, result_id=result['id'])
            mappings.append(mapping)
            if rid:
                task_parts[rid] = part
        identity = 'task-'+task['id']
        operations.append({'id': identity, 'case_id': part, 'intent': task['subject_type']+' '+task['intent'],
                           'execution_state': task['state'], 'occurred_at': task['submitted_at'], 'mappings': mappings,
                           'evidence_ids': ['session-report', 'http-exchanges', 'validation']})
        case_map[part]['operation_ids'].append(identity)
    issues = [{'id': 'quality-'+str(i+1), 'case_id': task_parts[q['run_id']], 'run_id': q['run_id'],
               'stage': q['stage'], 'category': q['code'], 'description': q['code']+'：'+str(q['path'])+'；原答保留，质量问题不阻断后续流程。',
               'status': 'deferred', 'affects_flow': False, 'evidence_ids': ['session-report', 'validation']}
              for i, q in enumerate(report['quality']['issues'])]
    issues.extend({'id': q['id'], 'case_id': task_parts[q['run_id']], 'run_id': q['run_id'],
                   'stage': q['stage'], 'category': q['code'], 'description': q['description'],
                   'status': 'deferred', 'affects_flow': False, 'evidence_ids': ['manual-quality']}
                  for q in manual['issues'])
    document = {'schema_version': 1,
        'batch': {'id': report['execution_id'], 'environment': 'acceptance-release-20261117-01',
                  'title': '进程启动与后续外联：同案两段测试', 'scenario_version': 'socai2.acceptance-scenario.v1',
                  'execution_state': 'finished', 'mode': 'live', 'provenance': 'live_execution',
                  'started_at': read('results/prepared/runs/part1/state.json')['started_at'],
                  'updated_at': datetime.now(timezone.utc).isoformat(),
                  'quality_status': 'issues_recorded' if issues else 'not_assessed'},
        'cases': cases, 'operations': operations,
        'preparation': {'status': 'prepared', 'cleanup_mode': 'executed',
                        'summary': '21新版发布及授权历史清理后，最终Docker容器准入通过；先首段检查，再同案追加。',
                        'resources': ['PostgreSQL aisoc.socai2', 'Kafka', 'ClickHouse', 'Redis', '真实模型', '4177'],
                        'observed_at': read('admission-02.json')['ended_at'], 'evidence_ids': ['preparation']},
        'quality_issues': issues, 'evidence': evidence}
    raw = json.dumps(document, ensure_ascii=False, indent=2)+'\n'
    Document.model_validate_json(raw)
    (output/'document.json').write_text(raw)
    receipt = {'status': 'prepared_not_published', 'batch_id': report['execution_id'], 'http_exchanges': len(exchanges),
               'operations': len(operations), 'quality_issues': len(issues), 'automatic_4b_feature': False,
               'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()}}
    with (ROOT/'viewer-preparation-02.json').open('x') as out:
        json.dump(receipt, out, ensure_ascii=False, indent=2)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
