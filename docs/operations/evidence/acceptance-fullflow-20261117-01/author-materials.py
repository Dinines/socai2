"""Author this new native material package; does not execute an acceptance part."""
import copy
import json
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'tools/testdata'))
from alert_scenarios import _without_answers, json_bytes, sha256
from streaming_fixture import build


def main(config_path):
    config = json.loads(config_path.read_text())
    output = config_path.parent.parent
    materials = output/'materials'
    materials.mkdir(exist_ok=False)
    socket.socket = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('offline authoring attempted a socket'))
    _, _, inputs, _ = build(config['generator_config'])
    (materials/'scenario.json').write_bytes(json_bytes(config['scenario']))
    origins, records = [], {}
    for entry in config['selection']:
        original = json.loads(inputs[entry['source']].splitlines()[entry['line']-1])
        value = copy.deepcopy(original)
        old_connector = value['connector_id']
        value['connector_id'] = config['registered_connector_id']
        _without_answers(value)
        encoded = json_bytes(value)
        for marker in (config['execution_id'], config['generator_config']['batch_id'],
                       'synthetic', 'fixture', 'is_test', 'expected_verdict', '测试'):
            assert marker.lower() not in encoded.decode().lower()
        target = materials/entry['target']
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(encoded)
        assert json.loads(target.read_text()) == value
        assert {k: v for k, v in value.items() if k != 'connector_id'} == {
            k: v for k, v in original.items() if k != 'connector_id'}
        origins.append({**entry, 'generator_record_sha256': sha256(json_bytes(original)),
                        'material_sha256': sha256(encoded), 'source_binding': {
                            'field': 'connector_id', 'from': old_connector,
                            'to': config['registered_connector_id'], 'target_registration': 'pending_readonly_check'}})
        records[entry['target']] = value
    contexts = {v['event_id']: v for k, v in records.items() if '/context/' in k}
    for relative, alert in records.items():
        if '/alerts/' not in relative:
            continue
        for event_id in alert['source_event_ids']:
            assert event_id in contexts
            assert alert['raw_event']['ocsf_event'] == contexts[event_id]['ocsf_event']
    parent = records['part1/context/001.json']['ocsf_event']['process']
    child = records['part1/context/002.json']['ocsf_event']['process']
    assert child['parent_process']['uid'] == parent['uid']
    network = records['part2/context/001.json']['ocsf_event']
    assert network['sensor_observation'] == {'connection_reset': False, 'dns_answers': []}
    hosts = {v.get('hostname') or v['ocsf_event']['device']['name'] for v in records.values()}
    assert len(hosts) == 1
    receipt = {'status': 'passed_offline', 'authoring_config_sha256': sha256(config_path.read_bytes()),
               'records': origins, 'business_observations_preserved': True, 'same_host': sorted(hosts),
               'source_links_verified': 2, 'parent_child_link_verified': True,
               'neutral_control_separation': 'passed_for_authored_materials_only',
               'backend_tenant_relationship_retained': True,
               'model_request_filtering': 'not_verified_until_actual_saved_requests',
               'business_connections': 0, 'kafka_sends': 0, 'model_calls': 0,
               'generator_sha256': sha256((ROOT/'tools/testdata/streaming_fixture.py').read_bytes())}
    with (output/'authoring-receipt.json').open('xb') as stream:
        stream.write(json_bytes(receipt))
    print(json.dumps({'status': receipt['status'], 'records': len(origins), 'host': sorted(hosts)}, ensure_ascii=False))


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
