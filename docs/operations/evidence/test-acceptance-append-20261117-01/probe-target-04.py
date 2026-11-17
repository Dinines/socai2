"""Controlled append preflight with changed connection identity; never publishes."""
import asyncio
import contextlib
import copy
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools/testdata'))
from acceptance_append import append_part
from acceptance_run import event_milliseconds


def load(path):
    return json.loads(path.read_text())


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def main():
    source = ROOT / 'docs/operations/evidence/acceptance-singlepart-20261117-02'
    before = {name: snapshot(source / name) for name in ('prepared', 'runs')}
    output = HERE / 'probe-target-04'
    output.mkdir(exist_ok=False)
    prepared = output / 'prepared'
    shutil.copytree(source / 'prepared', prepared)
    shutil.copytree(source / 'runs', prepared / 'runs')
    prior = snapshot(prepared / 'runs/part1')
    session = load(prepared / 'session.json')
    rows = load(prepared / 'runs/part1/saved-records.json')
    first_readiness = load(prepared / 'runs/part1/preflight.json')
    readiness = copy.deepcopy(first_readiness)
    readiness['connection_sha256']['kafka'] = hashlib.sha256(b'controlled different kafka target/topic config').hexdigest()
    old_alerts = {r['id'] for r in rows['alerts']}
    old_context = {}
    for path, identity in session['identities'].items():
        if identity['kind'] != 'context' or not path.startswith('part1/'):
            continue
        event = load(prepared / 'wire' / path)['ocsf_event']
        old_context[identity['event_id']] = {'event_id': identity['event_id'], 'tenant_id': session['profile']['tenant_id'],
            'class_uid': event['class_uid'], 'event_time_ms': event_milliseconds(event['time']), 'ocsf_json': event}
    reached_send = []

    class ControlledConnections:
        def __init__(self, *_):
            self.pg = SimpleNamespace(snapshot=self.read, preflight=self.registered)
            self.lake = SimpleNamespace(query=self.query, history_count=lambda *_: 0)

        async def read(self, alert_ids, *_args, **_kwargs):
            return copy.deepcopy(rows) if set(alert_ids) == old_alerts else {'alerts': []}

        async def registered(self, *_args, **_kwargs):
            return {'registered_connectors': [], 'matching_historical_members': 0, 'readonly': True}

        def query(self, identities):
            return copy.deepcopy([old_context[x] for x in identities if x in old_context])

        async def open(self):
            return copy.deepcopy(readiness)

        async def close(self):
            pass

        async def send(self, role, path, _payload):
            reached_send.append({'role': role, 'path': path})
            raise RuntimeError('controlled stop before real producer; no publication')

    console = io.StringIO()
    with contextlib.redirect_stdout(console), patch('socket.socket.connect', side_effect=AssertionError('external network prohibited')):
        state = asyncio.run(append_part(prepared, 'part2', clients_factory=ControlledConnections))
    assert state.get('error_code') == 'append_connection_configuration_changed'
    assert reached_send == []
    assert not (prepared / 'runs/part2/preflight.json').exists()
    new_readiness = readiness
    assert prior == snapshot(prepared / 'runs/part1')
    assert before == {name: snapshot(source / name) for name in before}
    result = {'scope': 'controlled clients with unchanged saved PG/lake identities and a changed Kafka configuration digest',
        'actual_connections': 0, 'actual_publications': 0, 'model_calls': 0,
        'original_kafka_config_sha256': first_readiness['connection_sha256']['kafka'],
        'observed_kafka_config_sha256': new_readiness['connection_sha256']['kafka'],
        'append_preflight_status': 'rejected_before_send', 'reached_send_stub': reached_send,
        'final_status': state['status'], 'final_error_type': state.get('error_type'), 'error_code': state.get('error_code'),
        'final_sent': state['sent'], 'historical_files_unchanged': True,
        'explanation': 'The changed configuration is rejected before the send stub is reached; no passed preflight is written.'}
    with (HERE / 'probe-target-results-04.json').open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
