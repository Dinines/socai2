"""One new Case's management lifecycle over TCP; never starts a model/Run."""
import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cfg = json.loads(args.profile.read_text())
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[2]
    credentials = json.loads((root / cfg['credential']['file']).read_text())
    if cfg['credential']['kind'] == 'existing_login':
        req = urllib.request.Request(cfg['credential']['login_url'], method='POST',
            data=json.dumps({k: credentials[k] for k in ['email', 'password']}).encode(),
            headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=cfg['timeout_seconds']) as response:
            token = json.load(response)['access_token']
    else:
        token = credentials['api_key']
    receipts = []

    def request(method, path, body=None, code=200, save=True):
        if save:
            (out / f'{len(receipts)+1:02}-intent.json').write_text(json.dumps(
                {'method': method, 'path': path, 'input': body}, ensure_ascii=False, indent=2)+'\n')
        req = urllib.request.Request(cfg['base_url'] + path, method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Authorization': 'Bearer '+token, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=cfg['timeout_seconds']) as response:
                status, data = response.status, json.load(response)
        except urllib.error.HTTPError as error:
            status, data = error.code, json.load(error)
        if save:
            receipts.append({'method': method, 'path': path, 'status': status, 'body': data})
            (out / 'responses.json').write_text(json.dumps(receipts, ensure_ascii=False, indent=2)+'\n')
        assert status == code, (status, data)
        return data

    base = '/api/v1/socai2/cases'
    alert = cfg.get('source_alert_id')
    if not alert:
        alert = request('GET', base+'/'+cfg['source_case_id'], save=False)['members'][0]['alert_id']
    created = request('POST', base, {'operation_key': str(uuid4()), 'title': cfg['title'], 'alert_ids': [alert]})
    cid, rid = created['case_id'], created['pending_run_id']
    path = base+'/'+cid
    initial = request('GET', path+'/management')
    assert initial['can_close'] and not initial['can_reopen'] and initial['open_task_count'] == 0
    owner = initial['case']['created_by']
    patch = {'operation_key': str(uuid4()), 'expected_row_version': initial['case']['row_version'],
        'title': cfg['title']+'-已修改', 'description': '本批验证Case管理保存读回，不表示真实调查结论。',
        'owner_id': owner, 'severity': 'high', 'tags': ['接口验收'], 'handling_status': 'in_progress'}
    updated = request('PATCH', path+'/management', patch)
    assert updated['changed'] and updated['case']['severity_source'] == 'manual'
    assert request('PATCH', path+'/management', patch) == updated
    conflict = request('PATCH', path+'/management', dict(patch, operation_key=str(uuid4()), title='过期修改'), 409)
    assert conflict['detail'] == 'case_row_version_conflict'
    version = updated['case']['row_version']
    assert request('PATCH', path+'/management', {'operation_key': str(uuid4()),
        'expected_row_version': version, 'title': None}, 422)
    task = request('POST', path+'/tasks', {'operation_key': str(uuid4()), 'expected_scope_revision': 1,
        'title': '结案时保留的待办（验收）'})['task']
    view = request('GET', path+'/management')
    assert view['open_task_count'] == 1 and view['requires_open_task_confirmation']
    version = view['case']['row_version']
    close = {'operation_key': str(uuid4()), 'expected_row_version': version,
        'reason': '本批接口验收结束；待办保持原状，不构成安全判定。'}
    assert request('POST', path+'/close', close, 409)['detail'] == 'case_open_tasks_confirmation_required'
    assert request('POST', path+'/close', {'operation_key': str(uuid4()),
        'expected_row_version': version, 'acknowledge_open_tasks': True}, 409)['detail'] == 'case_open_tasks_confirmation_required'
    closed = request('POST', path+'/close', dict(close, acknowledge_open_tasks=True))
    assert closed['case']['handling_status'] == 'resolved' and closed['case']['resolution_note'] == close['reason']
    assert request('POST', path+'/close', dict(close, acknowledge_open_tasks=True)) == closed
    assert request('GET', path+'/tasks/'+task['id']) == task
    assert request('PATCH', path+'/management', {'operation_key': str(uuid4()),
        'expected_row_version': closed['case']['row_version'], 'handling_status': 'in_progress'}, 409)['detail'] == 'case_reopen_required'
    reopened = request('POST', path+'/reopen', {'operation_key': str(uuid4()),
        'expected_row_version': closed['case']['row_version'], 'reason': '继续验收读取，不启动调查。'})
    assert reopened['case']['handling_status'] == 'in_progress' and reopened['case']['reopened_at']
    assert reopened['case']['resolved_at'] is None and reopened['case']['resolution_note'] is None
    cleared = request('PATCH', path+'/management', {'operation_key': str(uuid4()),
        'expected_row_version': reopened['case']['row_version'], 'description': None, 'owner_id': None,
        'severity': None, 'tags': []})
    case = cleared['case']
    assert case['title'] == patch['title'] and case['handling_status'] == 'in_progress'
    assert case['owner_id'] is None and case['assignment_state'] == 'unassigned'
    assert case['severity'] is None and case['severity_source'] is None and case['tags'] == []
    detail = request('GET', path)
    assert detail['case'] == case and detail['member_count'] == 1
    assert detail['case']['scope_revision'] == 1 and detail['case']['current_assessment_id'] is None
    queue = request('GET', base+'?q='+cid)
    assert queue['total'] == 1 and queue['items'][0]['case'] == case
    run = request('GET', path+'/runs/'+rid)['run']
    assert run['state'] == 'pending_update' and run['started_at'] is None
    activities = request('GET', path+'/activities')
    actions = {r['action'] for r in activities['items']}
    assert {'case_management_updated', 'case_closed', 'case_reopened'} <= actions
    result = {'state': 'passed', 'case_id': cid, 'run_id': rid, 'task_id': task['id'],
        'requests': len(receipts), 'real_model_calls': 0, 'transport': 'TCP HTTP',
        'database_expected': cfg['database'], 'run_started': False,
        'checks': ['patch/read/list', 'idempotency', 'stale version', 'invalid null',
                   'open task confirmation and reason', 'close', 'task unchanged',
                   'explicit reopen', 'nullable clearing', 'history activities', 'pending Run unchanged']}
    (out / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
