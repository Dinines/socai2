"""Replay the actual leaking material; preserve unknown business fields and raw originals."""
import copy
import json
from pathlib import Path

import pytest
from app.socai2 import alert_model_boundary, incident_model_boundary, runtime_policy
from app.socai2.case_input_text import material_entries

ROOT = Path(__file__).resolve().parents[3]
SAVED = ROOT / 'docs/operations/evidence/streaming-release-20261116-01/revision-02/smoke'


@pytest.mark.parametrize('stage', ['A', 'I', 'C3'])
def test_actual_nested_routing_metadata_is_omitted_without_mutating_original(stage, monkeypatch):
    rows = json.loads((SAVED / 'out/ai-pg-01.json').read_text())['rows']
    kind = 'alert_basic' if stage == 'A' else 'incident_diagnosis'
    run = next(r for r in rows['runs'] if r['kind'] == kind)
    source = next(a['content_json'] for a in rows['artifacts'] if a['id'] == run['input_artifact_id'])
    policy_path = ROOT / 'deploy/aisoc21/streaming-release-20261116-02/analysis/investigation-policy.toml'
    policy = runtime_policy.load_policy(policy_path)
    monkeypatch.setenv('SOCAI2_INVESTIGATION_POLICY', str(policy_path))
    monkeypatch.setattr(runtime_policy, 'active_policy', lambda: policy)
    material = source['members'][0]['material']
    record = material['raw_json']['raw_event']['telemetry'][0]
    record.update(packet_count=0, connection_reset=False, dns_answers=[],
                  business={'source': 'business-source-kept', 'id': 'business-id-kept', 'note': '原文照录。'})
    material['raw_json']['raw_event']['telemetry'].append(copy.deepcopy(record))
    # The wildcard must only match list indices, not similarly named business branches.
    material['raw_json']['raw_event']['other'] = {'source': 'other-business-source-kept', 'tenant_id': 'business-tenant-kept'}
    # This old routing fixture has no OCSF body; add a controlled counterpart.
    material['ocsf_json'] = copy.deepcopy(material.get('ocsf_json') or {})
    material['ocsf_json']['tenant_uid'] = 'program-tenant-route-only'
    material['ocsf_json']['cloud'] = {'tenant_uid': 'business-cloud-tenant-kept',
                                    'source': 'cloud-source-kept', 'id': 'cloud-id-kept',
                                    'count': 0, 'enabled': False, 'items': []}
    material['raw_json']['raw_event']['ocsf_event'] = copy.deepcopy(material['ocsf_json'])
    material['raw_json']['raw_event']['ocsf_event']['tenant_uid'] = 'program-nested-tenant-route-only'
    before = copy.deepcopy(source)
    if stage == 'A':
        queries = [(a['id'], a['content_json']) for a in rows['artifacts']
                   if a['run_id'] == run['id'] and a['kind'] == 'tool_response']
        prepared = alert_model_boundary.build(source, run['input_artifact_id'], queries, policy.alert_io)[-1]
        visible = prepared['user'];omissions = prepared['omissions']
    elif stage == 'I':
        prepared = incident_model_boundary.build(source, run['input_artifact_id'], policy.incident_io)[-1]
        visible = prepared['user'];omissions = prepared['omissions']
    else:
        omissions = []
        selected = material_entries(source['members'][0]['alert']['id'], material, policy.case_io.business,
                                    omissions, policy.case_io.config)
        # Later C3 selection separately removes the outer alert envelope.
        # Include OCSF as well as the nested received material entries.
        visible = json.dumps([entry for entry in selected
                              if entry['ref']['source_path'].startswith(('$.raw_json.raw_event.', '$.ocsf_json.'))],
                             ensure_ascii=False)
    assert source == before
    assert material['ocsf_json']['tenant_uid'] == 'program-tenant-route-only'
    assert 'program-tenant-route-only' not in visible
    assert 'program-nested-tenant-route-only' not in visible
    assert record['source'] not in visible and record['tenant_id'] not in visible
    assert record['connector_id'] not in visible and record['event_id'] not in visible
    for value in ('business-source-kept', 'business-id-kept', '原文照录。', 'other-business-source-kept',
                  'business-tenant-kept', 'business-cloud-tenant-kept', 'cloud-source-kept', 'cloud-id-kept',
                  'packet_count', 'connection_reset', 'dns_answers', 'false', '[]'):
        assert value in visible, value
    assert any(o['path'] == '$.raw_json.raw_event.telemetry.0.source' for o in omissions)
    assert any(o['path'] == '$.raw_json.raw_event.telemetry.1.source' for o in omissions)
    assert any(o['path'] == '$.ocsf_json.tenant_uid' for o in omissions)
    assert any(o['path'] == '$.raw_json.raw_event.ocsf_event.tenant_uid' for o in omissions)
    old_request = json.loads((SAVED / 'model-input-output' / ('alert-request.json' if stage == 'A' else 'incident-request.json')).read_text())
    assert record['source'] in json.dumps(old_request['messages'])
