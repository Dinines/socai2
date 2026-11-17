"""Pause the explicitly selected old containers; keep identities/data for recovery."""

import json
import subprocess
import sys
from datetime import datetime, timezone

cfg = json.load(sys.stdin)


def run(argv):
    return subprocess.run(argv, text=True, capture_output=True,
                          timeout=cfg['command_timeout_seconds'], check=True).stdout


def snapshot():
    ids = run(['docker', 'ps', '-aq']).split()
    rows = json.loads(run(['docker', 'inspect', *ids]))
    return {d['Name'].lstrip('/'): {
        'id': d['Id'], 'image': d['Image'], 'running': d['State']['Running'],
        'status': d['State']['Status'], 'started_at': d['State']['StartedAt'],
        'finished_at': d['State']['FinishedAt'], 'exit_code': d['State']['ExitCode'],
        'restart_policy': d['HostConfig']['RestartPolicy'],
    } for d in rows}


before = snapshot()
selected = [name for group in cfg['stop_groups'] for name in group]
assert len(selected) == len(set(selected))
assert not set(selected) & set(cfg['keep_running'])
assert all(name in before for name in selected + cfg['keep_running'])
assert all(before[name]['running'] for name in cfg['keep_running'])
out = {'started_at': datetime.now(timezone.utc).isoformat(), 'target': cfg['ssh_target'],
       'before': before, 'groups': [], 'model_calls': 0, 'database_writes': 0,
       'containers_removed': 0, 'volumes_removed': 0}
try:
    for group in cfg['stop_groups']:
        ids = [before[name]['id'] for name in group if before[name]['running']]
        if ids:
            run(['docker', 'stop', '--time', str(cfg['stop_timeout_seconds']), *ids])
        out['groups'].append({'names': group, 'stopped': len(ids)})
    out['status'] = 'completed'
except (subprocess.SubprocessError, OSError) as exc:
    out['status'] = 'failed'
    out['error'] = type(exc).__name__
finally:
    after = snapshot()
    out['after'] = after
    out['selected_stopped'] = all(name in after and not after[name]['running'] for name in selected)
    out['selected_identity_and_restart_policy_preserved'] = all(
        name in after and all(before[name][key] == after[name][key]
                              for key in ('id', 'image', 'restart_policy'))
        for name in selected)
    out['other_containers_unchanged'] = all(
        name in after and before[name] == after[name] for name in before if name not in selected)
    out['kept_dependencies_running'] = all(after[name]['running'] for name in cfg['keep_running'])
    out['restore_commands'] = [['docker', 'start', *group] for group in reversed(cfg['stop_groups'])]
    out['finished_at'] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(out, ensure_ascii=False, indent=2))
raise SystemExit(0 if out['status'] == 'completed' and out['selected_stopped'] else 1)
