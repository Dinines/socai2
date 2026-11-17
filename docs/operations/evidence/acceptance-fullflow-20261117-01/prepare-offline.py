"""Use the delivered Docker CLI to prepare this material batch, without execution."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def main(config_path):
    config = json.loads(config_path.read_text())
    out = config_path.parent.parent
    material, selected, results = out/'materials', out/'config', out/'results'
    before = tree(material)
    prefix = ['docker', 'compose', '--env-file', str(config_path.parent/'offline.env'),
              '-f', config['compose'], 'run', '--rm', '-T', 'acceptance']
    receipts = []
    calls = [
        ['inspect', '--materials', '/materials', '--profile', '/run/acceptance-config/profile.json',
         '--report', '/results/inspection.json'],
        ['prepare', '--materials', '/materials', '--profile', '/run/acceptance-config/profile.json',
         '--execution', '/run/acceptance-config/execution.json', '--output', '/results/prepared'],
        ['status', '--prepared', '/results/prepared', '--report', '/results/status.json'],
        ['session', '--prepared', '/results/prepared', '--output', '/results/console01'],
        ['report', '--prepared', '/results/prepared', '--output', '/results/report01'],
    ]
    for index, args in enumerate(calls, 1):
        result = subprocess.run([*prefix, *args], input='', text=True, capture_output=True,
                                timeout=config['timeout_seconds'])
        receipt = {'command': [*prefix, *args], 'exit_code': result.returncode,
                   'stdout': result.stdout, 'stderr': result.stderr}
        (out/f'offline-command-{index:02d}.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
        receipts.append({'index': index, 'exit_code': result.returncode})
        assert result.returncode == 0, 'see preserved command receipt; do not overwrite prepared'
    session = json.loads((results/'prepared/session.json').read_text())
    status = json.loads((results/'status.json').read_text())
    end = json.loads((results/'console01/end.json').read_text())
    report = json.loads((results/'report01/report.json').read_text())
    manifest = json.loads((results/'report01/manifest.json').read_text())
    assert len(session['identities']) == 5 and session['source_directory'] == '/materials'
    assert session['profile'] == json.loads((selected/'profile.json').read_text())
    assert status['state'] == 'ready' and status['next_part'] == 'part1' and not status['live_state_verified']
    assert end['reason'] == 'eof' and end['execution_attempts'] == 0 and not end['permanently_closed']
    assert not (results/'prepared/runs').exists()
    assert all(v == 0 for v in report['counts'].values()) and not report['all_parts_completed']
    for item in manifest['files']:
        assert sha(results/'report01'/item['path']) == item['sha256']
    assert tree(material) == before
    originals = {p: json.loads((material/p).read_text()) for p in session['source_material_sha256']}
    wires = {p: json.loads((results/'prepared/wire'/p).read_text()) for p in session['wire_sha256']}
    changes = []
    def differences(a, b, path):
        if type(a) is not type(b):
            changes.append(path)
        elif isinstance(a, dict):
            assert set(a) == set(b)
            for key in a:
                differences(a[key], b[key], path+'.'+key)
        elif isinstance(a, list):
            assert len(a) == len(b)
            for index, value in enumerate(a):
                differences(value, b[index], path+f'.{index}')
        elif isinstance(a, str) and a.lstrip().startswith('{'):
            differences(json.loads(a), json.loads(b), path+'.raw_json')
        elif a != b:
            changes.append(path)
    for p, original in originals.items():
        differences(original, wires[p], p)
    assert all(any(piece in path for piece in ('.id', '.uid', '.event_id', '.source_alert_id',
                                               '.source_event_ids.', '.identity_event_id')) for path in changes)
    for value in wires.values():
        event = value.get('ocsf_event') or value['raw_event']['ocsf_event']
        assert event['tenant_uid'] == session['profile']['tenant_id']
    new_context = {v['event_id']: v for p, v in wires.items() if '/context/' in p}
    for p, alert in wires.items():
        if '/alerts/' in p:
            assert alert['source_event_ids'][0] in new_context
            assert alert['raw_event']['ocsf_event'] == new_context[alert['source_event_ids'][0]]['ocsf_event']
    proof = {'status': 'passed_offline_preparation', 'execution_id': session['execution']['execution_id'],
             'records': 5, 'parts': [{k: p[k] for k in ('id', 'counts', 'case_actions')} for p in session['plan']['parts']],
             'new_identity_changes': changes, 'business_fields_and_times_preserved': True,
             'material_before_after': before, 'prepared_sha256': tree(results/'prepared'),
             'session_sha256': sha(results/'prepared/session.json'), 'commands': receipts,
             'source_link_readback': 'passed', 'tenant_association_preserved': True,
             'local_saved_state': status['state'], 'ready_to_execute_on_21': False,
             'reason': 'Target version, final container connectivity and workbench handoff are separate pending steps.',
             'runs_created': False, 'kafka_sends': 0, 'model_calls': 0}
    (out/'offline-preparation.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: proof[k] for k in ('status', 'records', 'parts', 'ready_to_execute_on_21')}, ensure_ascii=False))


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
