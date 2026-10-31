"""One fixed full-source main investigation through the existing HTTP client; no retries."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import UTC, datetime

ROOT = Path(__file__).resolve().parent
RELEASE = Path('/opt/sting-aisoc-socai2/investigation-v2/20261031-r10')


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    plan = json.loads((ROOT / 'plan.json').read_text())
    steps = plan['steps']
    assert len(steps) == 1
    for step in steps:
        assert hashlib.sha256((ROOT / step['body_file']).read_bytes()).hexdigest() == step['body_sha256']
    if sys.argv[1:] != ['--execute']:
        print(json.dumps({'batch': plan['batch'], 'max_new_runs': 1, 'executed': False}))
        return
    os.umask(0o077)
    output = ROOT / 'results'
    assert not output.exists(), 'batch_already_started'
    output.mkdir()
    private = Path(plan['credentials_file'])
    assert private.stat().st_mode & 0o777 == 0o600
    keys = json.loads(private.read_text())
    state = {'batch': plan['batch'], 'started_at': datetime.now(UTC).isoformat(), 'http': [],
             'runs': [], 'skipped': [], 'errors': [], 'functional_checks': []}

    def request(step, method, path, label, body=None, expected=200):
        prefix = output / f"{len(state['http'])+1:03d}-{label}"
        meta = {'method': method, 'path': path, 'tenant_id': step['tenant_id'],
                'started_at': datetime.now(UTC).isoformat(), 'attempt': 1}
        command = [sys.executable, '-B', str(RELEASE / 'scripts/investigation_client.py'), method, path, '--timeout', '150']
        if body:
            command += ['--body', str(body)]
            wire = json.dumps(json.loads(body.read_text()), ensure_ascii=False).encode()
            prefix.with_suffix('.body.json').write_bytes(wire)
            meta['body_sha256'] = hashlib.sha256(wire).hexdigest()
        save(prefix.with_suffix('.request.json'), meta)
        response = subprocess.run(command, capture_output=True, timeout=160,
                                  env={**os.environ, 'AISOC_API_TOKEN': keys[step['tenant_id']]})
        prefix.with_suffix('.response.txt').write_bytes(response.stdout)
        match = re.search(rb'HTTP (\d+)', response.stderr)
        meta.update(status=int(match.group(1)) if match else None, exit_code=response.returncode,
                    finished_at=datetime.now(UTC).isoformat(), response_sha256=hashlib.sha256(response.stdout).hexdigest())
        save(prefix.with_suffix('.request.json'), meta)
        state['http'].append(meta)
        save(output / 'summary.json', state)
        if expected is not None:
            assert meta['status'] == expected, f"{label}:http_{meta['status']}"
        try:
            parsed = json.loads(response.stdout)
        except (ValueError, UnicodeDecodeError):
            parsed = None
        return parsed, response.stdout

    try:
        for step in steps:
            request(step, 'GET', step['readback_path'], step['case']+'-absent', expected=404)
            case_id = step['path'].split('/')[5]
            case, _ = request(step, 'GET', f'/api/v1/cases/{case_id}', step['case']+'-case')
            body = json.loads((ROOT / step['body_file']).read_text())
            assert body['refresh_queries'] is True and 'previous_run_id' not in body
            assert body['required_tools'] == ['process_activity', 'network_connections']
            assert set(body['selected_member_ids']).issubset(case['alert_ids'])
            for index, alert_id in enumerate(body['selected_member_ids']):
                alert, _ = request(step, 'GET', f'/api/v1/alerts/{alert_id}', step['case']+f'-alert-{index}')
                assert alert.get('source_connector_id') is None, 'vendor_source_outside_batch'
                assert isinstance(alert.get('raw_event'), dict) and alert['raw_event'].get('full_log'), 'missing_full_raw_source'
        for step in steps:
            label = step['case'] + '-' + step['stage']
            print(json.dumps({'starting': label}), flush=True)
            first, _ = request(step, 'POST', step['path'], label, ROOT / step['body_file'], expected=None)
            result, _ = request(step, 'GET', step['readback_path'], label+'-result')
            assert result['run_id'] == step['planned_run_id'] and result['status'] != 'running'
            if isinstance(first, dict) and 'result' in first:
                assert first['result'] == result['result']
            request(step, 'GET', result['report_url'], label+'-report')
            listing, _ = request(step, 'GET', result['steps_url']+'?limit=50', label+'-steps')
            assert listing['next_after_seq'] is None
            for item in listing['items']:
                request(step, 'GET', item['detail_url'], label+f"-step-{item['seq']}")
            tool_results = [item for item in result['result']['evidence'] if item.get('kind') == 'tool']
            state['functional_checks'].append({'fresh_required_tools': all(
                any(item.get('tool') == name and item.get('available') is True and item.get('query_id')
                    and not item.get('reused_from') for item in tool_results)
                for name in ('process_activity', 'network_connections')),
                'history_evidence_count': sum(item.get('kind') == 'prior_analysis' for item in result['result']['evidence'])})
            state['runs'].append({'step': label, 'run_id': result['run_id'], 'status': result['status'],
                **{key: result['result'][key] for key in ('completion', 'stop_reason', 'usage')}, 'tools': tool_results})
            save(output / 'summary.json', state)
            print(json.dumps({key: state['runs'][-1][key] for key in ('step','status','stop_reason','usage')}), flush=True)
    except Exception as exc:
        state['errors'].append({'type': type(exc).__name__, 'message': str(exc)})
    finally:
        state['finished_at'] = datetime.now(UTC).isoformat()
        save(output / 'summary.json', state)
    print(json.dumps({'finished': True, 'runs': len(state['runs']), 'skipped': state['skipped'], 'errors': state['errors']}))
    return int(bool(state['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
