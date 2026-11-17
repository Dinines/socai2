"""Prepare six clearly synthetic rows with the existing Fusion projection."""
import copy
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'services/fusion'))
from app.services.lake_writer import event_to_row

config = json.loads((HERE / 'config.json').read_text())
source = config['source']
data = json.loads((ROOT / config['source_export']).read_text())
packets = []
for material in data['alert_materials']:
    packets.append({'kind': 'original_alert_observation_copy', 'source_material_id': material['id'],
                    'ocsf_event': copy.deepcopy(material['ocsf_json'])})
user = next(row['ocsf_event']['actor']['user']['name'] for row in packets)
values = source['context_values']
context = [
    {'time': source['context_times']['authentication'], 'class_uid': 3002,
     'activity': {'action': 'logon', 'outcome': 'success', 'session': {'key': values['session_key']}},
     'src_endpoint': {'ip': '203.0.113.77'}},
    {'time': source['context_times']['process'], 'class_uid': 1007,
     'activity': {'action': 'process_start', 'outcome': 'success'},
     'process': {'name': values['child_process'], 'pid': values['child_pid'], 'cmd_line': values['command_line'],
                 'parent_process': {'name': values['parent_process'], 'pid': values['parent_pid']}}},
    {'time': source['context_times']['network'], 'class_uid': 4001,
     'activity': {'action': 'network_connection', 'outcome': 'success'},
     'src_endpoint': {'ip': '192.0.2.77'}, 'dst_endpoint': {'ip': '198.51.100.77', 'port': values['network_port']},
     'connection_info': {'protocol_name': 'TCP'}}]
for item in context:
    item.update(device={'name': source['hostname']}, actor={'user': {'name': user}},
                metadata={'product': {'name': source['synthetic_connector']},
                          'description': 'Synthetic context for stage1 followup verification; no authorization or verdict asserted.'})
    packets.append({'kind': 'authored_synthetic_context_only_in_lake', 'source_material_id': None, 'ocsf_event': item})
for index, packet in enumerate(packets):
    packet.update(event_id=str(uuid5(NAMESPACE_URL, config['batch'] + ':lake:' + str(index))),
                  tenant_id=source['tenant_id'], connector_type=source['synthetic_connector'])
    row = event_to_row(packet)
    assert row is not None and row['event_id'] == packet['event_id'] and row['src_hostname'] == source['hostname']
    assert datetime.fromisoformat(source['window_start']).replace(tzinfo=None) <= row['event_time'] < datetime.fromisoformat(source['window_end']).replace(tzinfo=None)
    row['event_time'] = row['event_time'].strftime('%Y-%m-%d %H:%M:%S.%f')
    packet['row'] = row
assert len(packets) == 6
with (HERE / 'lake-seed-plan.json').open('x') as stream:
    json.dump({'batch': config['batch'], 'authorization': 'user requested lake insertion and contextual query records',
               'source': source, 'rows': packets, 'production_business_truth': False,
               'mapper': 'services/fusion/app/services/lake_writer.py',
               'mapper_sha256': hashlib.sha256((ROOT / 'services/fusion/app/services/lake_writer.py').read_bytes()).hexdigest(),
               'source_export_sha256': hashlib.sha256((ROOT / config['source_export']).read_bytes()).hexdigest()},
              stream, ensure_ascii=False, indent=2)
print(json.dumps({'prepared_rows': len(packets), 'original_copies': 3, 'lake_only_context': 3, 'writes': 0}))
