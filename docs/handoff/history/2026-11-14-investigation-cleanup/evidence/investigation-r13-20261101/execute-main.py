"""One fixed r13 A or B request through the existing client; no retries or data seeding."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import UTC, datetime

ROOT = Path('/opt/sting-aisoc-socai2/investigation-v2/20261101-r13')
LABEL = sys.argv[1]
assert LABEL in ('A', 'B')
plan = json.loads((ROOT / 'retest/plan.json').read_text())
step = next(s for s in plan['cases'] if s['label'] == LABEL)
body = ROOT / 'retest' / step['body_file']
assert hashlib.sha256(body.read_bytes()).hexdigest() == step['body_file_sha256']
output = ROOT / 'retest/results' / LABEL
output.mkdir(parents=True, exist_ok=False, mode=0o700)
state = {'label': LABEL, 'started_at': datetime.now(UTC).isoformat(), 'http': [], 'errors': []}
key_file = Path('/opt/sting-aisoc-socai2/private/investigation-dev-keys.json')
assert key_file.stat().st_mode & 0o777 == 0o600
token = json.loads(key_file.read_text())[step['tenant_id']]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def request(method, path, label, body_file=None, expected=200):
    assert path.startswith('/api/v2/investigation/cases/' + step['case_id'] + '/')
    prefix = output / f"{len(state['http'])+1:03d}-{label}"
    meta = {'method': method, 'path': path, 'tenant_id': step['tenant_id'], 'attempt': 1,
            'started_at': datetime.now(UTC).isoformat()}
    state['http'].append(meta)
    save(output / 'summary.json', state)
    command = [sys.executable, '-B', str(ROOT / 'scripts/investigation_client.py'), method, path,
               '--timeout', '150' if method == 'POST' else '20']
    if body_file:
        command += ['--body', str(body_file)]
        wire = json.dumps(json.loads(body_file.read_text()), ensure_ascii=False).encode()
        assert hashlib.sha256(wire).hexdigest() == step['client_wire_sha256']
        prefix.with_suffix('.body.json').write_bytes(wire)
        meta['body_sha256'] = hashlib.sha256(wire).hexdigest()
    save(prefix.with_suffix('.request.json'), meta)
    response = subprocess.run(command, capture_output=True, timeout=170,
                              env={**os.environ, 'AISOC_API_TOKEN': token})
    prefix.with_suffix('.response.txt').write_bytes(response.stdout)
    match = re.search(rb'HTTP (\d+)', response.stderr)
    meta.update(status=int(match.group(1)) if match else None, exit_code=response.returncode,
                finished_at=datetime.now(UTC).isoformat(),
                response_sha256=hashlib.sha256(response.stdout).hexdigest())
    save(prefix.with_suffix('.request.json'), meta)
    save(output / 'summary.json', state)
    if expected is not None:
        assert meta['status'] == expected, label + ':unexpected_status'
    try:
        parsed = json.loads(response.stdout)
    except (ValueError, UnicodeDecodeError):
        parsed = None
    return parsed, response.stdout


try:
    request('GET', step['readback_path'], 'planned-run-absent', expected=404)
    print(json.dumps({'starting': LABEL, 'planned_run_id': step['planned_run_id']}), flush=True)
    first, _ = request('POST', step['path'], 'investigate', body, expected=None)
    result, _ = request('GET', step['readback_path'], 'result')
    assert result['run_id'] == step['planned_run_id'] and result['status'] != 'running'
    if isinstance(first, dict) and 'result' in first:
        assert first['result'] == result['result'], 'post_get_result_mismatch'
    request('GET', result['report_url'], 'report')
    listing, _ = request('GET', result['steps_url'] + '?limit=50', 'steps')
    assert listing['next_after_seq'] is None
    for item in listing['items']:
        request('GET', item['detail_url'], f"step-{item['seq']}")
    state['run'] = {'run_id': result['run_id'], 'status': result['status'],
                    **{k: result['result'][k] for k in ('completion', 'stop_reason', 'usage')},
                    'tools': [e for e in result['result']['evidence'] if e.get('kind') == 'tool']}
except Exception as exc:
    state['errors'].append({'type': type(exc).__name__, 'message': str(exc)})
finally:
    state['finished_at'] = datetime.now(UTC).isoformat()
    save(output / 'summary.json', state)
print(json.dumps({k: state[k] for k in ('label', 'run', 'errors') if k in state}, ensure_ascii=False))
raise SystemExit(bool(state['errors']))
