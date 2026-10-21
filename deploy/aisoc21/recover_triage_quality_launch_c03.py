"""Recover one proven pre-execution file-permission failure; never send input.

prepare fixes only the public observer's read mode and runs a disconnected
UID10001 hash/AST probe. release requires independent proof of zero business
actions and archives every original failure file before clearing that launch
checkpoint. The original runner is invoked separately, once, afterwards.
"""
from pathlib import Path
import ast
import json
import os
import subprocess
import sys

import prepare_triage_quality_c03 as p

D = p.E / 'launch-recovery-case01'
OLD = p.E / 'host-phases/case01/ingress'
EXPECTED_LOG = "python: can't open file '/operators/quality.py': [Errno 13] Permission denied\n"


def initial_failure():
    assert not (p.E / 'cases').exists()
    assert p.read(OLD / 'exit.json')['exit_code'] == 2
    assert (OLD / 'container.log').read_text() == EXPECTED_LOG
    assert p.read(OLD / 'before.json') == p.read(OLD / 'after.json')
    assert not (OLD / 'accepted.json').exists()
    assert p.read(p.E / 'safety-stop.json')['phase'] == 'ingress'
    assert p.read(p.E / 'safety-stop.json')['case'] == 'case01'
    return {str(f.relative_to(p.E)): p.sha(f) for f in sorted(OLD.rglob('*')) if f.is_file()} | {
        'safety-stop.json': p.sha(p.E / 'safety-stop.json')}


def prepare():
    hashes = initial_failure()
    D.mkdir(mode=0o700, exist_ok=False)
    old_mode = p.INSIDE.stat().st_mode & 0o777
    assert old_mode == 0o600 and p.sha(p.INSIDE) == p.read(p.P / 'state.json')['operator_sha256']
    p.save(D / 'started.json', {'original_files': hashes, 'inside_sha256': p.sha(p.INSIDE),
           'old_mode': oct(old_mode), 'only_mode_change': '0o644', 'recovery_operator_sha256': p.sha(Path(__file__))})
    p.INSIDE.chmod(0o644)
    code = "from pathlib import Path;import hashlib,ast,json;p=Path('/operators/quality.py');b=p.read_bytes();ast.parse(b);print(json.dumps({'sha256':hashlib.sha256(b).hexdigest(),'ast_valid':True}))"
    command = ['docker', 'run', '--rm', '--pull', 'never', '--network', 'none', '--user', '10001:10001',
               '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true',
               '--mount', 'type=bind,src=' + str(p.INSIDE) + ',dst=/operators/quality.py,readonly',
               p.IMAGE, 'python', '-c', code]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0
    probe = json.loads(result.stdout)
    assert probe == {'sha256': p.sha(p.INSIDE), 'ast_valid': True}
    assert initial_failure() == hashes
    p.save(D / 'prepared.json', {'original_files': hashes, 'probe': probe, 'uid': 10001,
           'network': 'none', 'env_or_private_mounted': False, 'business_actions': 0,
           'inside_sha256': p.sha(p.INSIDE), 'inside_mode': oct(p.INSIDE.stat().st_mode & 0o777),
           'recovery_operator_sha256': p.sha(Path(__file__)), 'original_failure_preserved': True})
    print(json.dumps({'prepared': True, 'disconnected_read_probe_passed': True, 'business_actions': 0}))


def release():
    prepared = p.read(D / 'prepared.json')
    audit_path = p.E / 'ingress-launch-recovery-independent-audit.json'
    audit = p.read(audit_path)
    assert audit['accepted'] is True and audit['business_actions_before_recovery'] == 0
    assert audit['recovery_operator_sha256'] == p.sha(Path(__file__))
    assert audit['prepared_sha256'] == p.sha(D / 'prepared.json')
    assert initial_failure() == prepared['original_files']
    assert p.sha(p.INSIDE) == prepared['inside_sha256'] and p.INSIDE.stat().st_mode & 0o777 == 0o644
    archive = D / 'original-failed-launch'
    assert not archive.exists() and not (D / 'release-started.json').exists()
    archive.mkdir(mode=0o700)
    p.save(D / 'release-started.json', {'audit_sha256': p.sha(audit_path),
           'prepared_sha256': p.sha(D / 'prepared.json'), 'original_files': prepared['original_files'],
           'no_input_sent_by_recovery': True})
    OLD.rename(archive / 'host-ingress')
    (p.E / 'safety-stop.json').rename(archive / 'safety-stop.json')
    mapping = []
    for original, digest in prepared['original_files'].items():
        destination = archive / ('safety-stop.json' if original == 'safety-stop.json' else
                               'host-ingress/' + Path(original).name)
        assert p.sha(destination) == digest
        mapping.append({'original_path': original, 'preserved_path': str(destination.relative_to(p.E)), 'sha256': digest})
    p.save(D / 'released.json', {'original_files_preserved': mapping, 'audit_sha256': p.sha(audit_path),
           'operator_or_plan_bytes_changed': False, 'no_business_actions': True,
           'next': 'original runner ingress case01 once; its original HTTP checkpoint remains mandatory'})
    print(json.dumps({'released': True, 'original_failed_launch_preserved': True, 'business_actions': 0}))


if __name__ == '__main__':
    os.umask(0o077)
    assert len(sys.argv) == 2 and sys.argv[1] in {'prepare', 'release'}
    {'prepare': prepare, 'release': release}[sys.argv[1]]()
