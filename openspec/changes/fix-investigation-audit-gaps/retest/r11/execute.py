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
RELEASE = Path('/opt/sting-aisoc-socai2/investigation-v2/20261101-r11')


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    fixture = json.loads((ROOT / 'fixture.json').read_text())
    seed = json.loads((ROOT / 'seed-result.json').read_text())
    assert seed['batch'] == fixture['batch'] and seed['new_alerts'] == seed['new_lake_events'] == 2
    assert all(r['available'] and r['returned_count'] == 1 for r in seed['preflight_queries'].values())
    plan = {'batch': fixture['batch'], 'credentials_file': '/opt/sting-aisoc-socai2/private/investigation-dev-keys.json'}
    steps = []
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
        # Preserve the prior r10 report through the same authenticated read API.
        old_step = {'tenant_id': 'f6a5c700-69b8-44fc-8238-609362fb1a9f'}
        old_run = '/api/v2/investigation/cases/be4aeda2-a89b-47e6-a6f9-285b1a7e8723/investigations/4f094ed4-b4f9-5db9-8cc2-b5f8c781858e'
        old_result, _ = request(old_step, 'GET', old_run, 'old-r10-result')
        old_report, old_report_bytes = request(old_step, 'GET', old_result['report_url'], 'old-r10-report-before')
        step = {'tenant_id': fixture['tenant_id'], 'case': 'synthetic-full-raw', 'stage': 'main',
                'body_file': '01-synthetic-main.json', 'planned_run_id': fixture['planned_run_id']}
        for index, expected in enumerate(fixture['alerts']):
            observed, _ = request(step, 'GET', '/api/v1/alerts/'+expected['id'], f'seed-alert-{index}')
            assert observed['raw_event'] == expected['raw_event']
            assert observed['affected_hosts'] == expected['affected_hosts']
        save(ROOT / 'case-link.json', fixture['case_link_request'])
        link, _ = request(step, 'POST', '/api/v2/investigation/case-links', 'create-case', ROOT/'case-link.json', expected=201)
        assert link['case_action'] == 'created' and set(link['selected_member_ids']) == set(fixture['investigation_body']['selected_member_ids'])
        step['path'] = link['investigate_url']
        step['readback_path'] = '/api/v2/investigation/cases/'+link['case_id']+'/investigations/'+step['planned_run_id']
        save(ROOT / step['body_file'], fixture['investigation_body'])
        step['body_sha256'] = hashlib.sha256((ROOT/step['body_file']).read_bytes()).hexdigest()
        steps = [step]
        plan.update(steps=steps, scope=fixture['scope'], retry_policy='One Case POST and one investigation POST; no retry.')
        save(ROOT / 'plan.json', plan)
        state['case_id'] = link['case_id']
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
        _, old_after = request(old_step, 'GET', old_result['report_url'], 'old-r10-report-after')
        assert old_after == old_report_bytes, 'old_report_changed'
        state['old_report_unchanged'] = True
    except Exception as exc:
        state['errors'].append({'type': type(exc).__name__, 'message': str(exc)})
    finally:
        state['finished_at'] = datetime.now(UTC).isoformat()
        save(output / 'summary.json', state)
    print(json.dumps({'finished': True, 'runs': len(state['runs']), 'skipped': state['skipped'], 'errors': state['errors']}))
    return int(bool(state['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
