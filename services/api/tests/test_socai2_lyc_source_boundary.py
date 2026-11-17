"""Current A/I/C3/Deep/C6 construction with derived lyc metadata; zero service I/O."""
import copy
import hashlib
import json
import os
import re
import socket
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.socai2 import (
    alert_model_boundary,
    alert_output_adapter,
    case_followup_input,
    case_followup_output,
    case_model_boundary,
    case_output_adapter,
    incident_model_boundary,
    incident_output_adapter,
    runtime_policy,
)
from app.socai2.baseline_context import Context
from app.socai2.baseline_store import digest
from app.socai2.model_protocol import prepare_request
from test_socai2_d1_input_boundary_independent import has_typed_leaf

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / 'docs/operations/evidence/acceptance-fullflow-21-20261117-01/results/prepared/runs/part2/saved-records.json'
POLICY = ROOT / 'deploy/aisoc21/streaming-release-20261116-02/analysis/investigation-policy.toml'
RELEASE = ROOT / 'docs/operations/evidence/acceptance-release-20261117-01/deployment-ready.json'
STAGES = ['A', 'I', 'C3', 'Deep', 'C6']
VARIANTS = ['direct', 'structured', 'serialized_ocsf', 'serialized_envelope']
BUSINESS = {'source': 'business-origin-kept', 'connector_type': 'business-type-kept',
            'connector_id': 'business-connector-kept', 'tenant_id': 'business-account-kept',
            'amount': 0, 'authorized': False, 'permissions': [], 'statement': '保留原始业务说明。'}


@pytest.fixture(scope='module')
def frozen():
    raw = SNAPSHOT.read_bytes()
    yield raw, json.loads(raw)
    assert SNAPSHOT.read_bytes() == raw


@pytest.fixture
def configured(monkeypatch):
    attempts = []

    def deny(*_args, **_kwargs):
        attempts.append('socket_connect')
        raise AssertionError('Offline input-boundary check attempted network access')

    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setenv('SOCAI2_INVESTIGATION_POLICY', str(POLICY))
    runtime_policy.active_policy.cache_clear()
    policy = runtime_policy.active_policy()
    assert hashlib.sha256(POLICY.read_bytes()).hexdigest() == json.loads(RELEASE.read_text())['policy_sha256']
    yield policy, attempts
    runtime_policy.active_policy.cache_clear()


def construct(rows, policy, stage, variant):
    artifacts = {a['id']: a for a in rows['artifacts']}
    kind = stage if stage in {'A', 'I'} else 'Case'
    subject_column = {'A': 'alert_id', 'I': 'incident_id', 'Case': 'case_id'}[kind]
    candidates = [r for r in rows['runs'] if r[subject_column]]
    run = min(candidates, key=lambda r: r['started_at'])
    changes = []

    def mark(value, key, path):
        marker = f'lyc-input-{stage}-{variant}-{len(changes):03d}'
        changes.append({'path': path + '.' + key, 'marker': marker, 'previous': copy.deepcopy(value.get(key))})
        value[key] = marker

    def backend(alert, path):
        for key in ['connector_type', 'connector_id', 'tenant_id']:
            mark(alert, key, path)

    def paired_tenant(receipts, alert, path):
        # Preserve the existing receipt/alert identity contract in the derived copy.
        for index, row in enumerate(receipts):
            changes.append({'path': f'{path}.{index}.tenant_id', 'marker': alert['tenant_id'],
                            'previous': row['tenant_id'], 'reason': 'same_derived_tenant_as_owner'})
            row['tenant_id'] = alert['tenant_id']

    def material(value, path):
        mark(value, 'tenant_id', path)
        raw = value['raw_json']
        for key in ['source', 'connector_type', 'connector_id', 'tenant_id']:
            mark(raw, key, path + '.raw_json')
        envelope = raw['raw_event']
        for key in ['source', 'connector_type', 'connector_id', 'tenant_id']:
            mark(envelope, key, path + '.raw_json.raw_event')
        for name, event in [('ocsf_json', value['ocsf_json']), ('raw_json.raw_event.ocsf_event', envelope['ocsf_event'])]:
            mark(event, 'tenant_uid', path + '.' + name)
            event['business_extension'] = copy.deepcopy(BUSINESS)
        if variant == 'structured':
            envelope['telemetry'] = []
            for index in range(2):
                record = {'business_extension': copy.deepcopy(BUSINESS)}
                for key in ['source', 'connector_type', 'connector_id', 'tenant_id']:
                    mark(record, key, path + f'.raw_json.raw_event.telemetry.{index}')
                envelope['telemetry'].append(record)
        if variant.startswith('serialized'):
            # Both forms use existing JSON material paths; never change a business name or product label.
            record = (copy.deepcopy(value['ocsf_json']) if variant == 'serialized_ocsf' else copy.deepcopy(raw))
            text = json.dumps(record, ensure_ascii=False)
            value['raw_text'] = text
            value['ocsf_json']['raw_data'] = text
            envelope['ocsf_event']['raw_data'] = text
            for original in list(changes):
                if original['marker'] in text:
                    changes.append({'path': path + '.{raw_text,ocsf_json.raw_data,raw_json.raw_event.ocsf_event.raw_data}(JSON)',
                                    'marker': original['marker'], 'nested_source_path': original['path']})

    if stage in {'A', 'I'}:
        source = copy.deepcopy(artifacts[run['input_artifact_id']]['content_json'])
        for index, member in enumerate(source['members']):
            backend(member['alert'], f'$.members.{index}.alert')
            paired_tenant(source.get('triage_queries', {}).get(member['alert']['id'], []),
                          member['alert'], f'$.triage_queries.{member["alert"]["id"]}')
            material(member['material'], f'$.members.{index}.material')
        queries = [(a['id'], copy.deepcopy(a['content_json'])) for a in artifacts.values()
                   if a['run_id'] == run['id'] and a['kind'] == 'tool_response']
        before = digest([source, queries])
        if stage == 'A':
            messages, mapping, _, prepared = alert_model_boundary.build(
                source, run['input_artifact_id'], queries, policy.alert_io, execution_time=run['started_at'])
            output = alert_output_adapter.schema(mapping)
        else:
            messages, mapping, _, prepared = incident_model_boundary.build(
                source, run['input_artifact_id'], policy.incident_io, execution_time=run['started_at'])
            output = {'type': 'json_schema', 'json_schema': {'name': 'socai2_incident_boundary', 'strict': True,
                      'schema': incident_output_adapter.candidate_schema(prepared)}}
        unchanged = before == digest([source, queries])
    else:
        owned = [a for a in artifacts.values() if a['run_id'] == run['id']]
        snapshot = next(a for a in owned if a['schema_version'] == 'socai2.baseline-context.v1')
        raw_context = copy.deepcopy(snapshot['content_json'])
        assert raw_context['case_input_profile'] == policy.case_io.identity
        materials = {}
        for aid, member in raw_context['alerts'].items():
            backend(member['alert'], f'$.C1.alerts.{aid}.alert')
            paired_tenant(member.get('queries', []), member['alert'], f'$.C1.alerts.{aid}.queries')
            value = copy.deepcopy(next(m for m in rows['alert_materials'] if m['id'] == member['material']['id']))
            material(value, f'$.materials.{aid}')
            materials[aid] = value
        context = Context.model_validate(raw_context)
        enrichment = [(a['id'], copy.deepcopy(a['content_json']), {}) for a in owned
                      if a['kind'] == 'tool_response' and a['schema_version'] == 'socai2.baseline-enrichment.v1']
        previous = next(a for a in owned if isinstance(a.get('content_json'), dict) and a['content_json'].get('analysis'))
        prior = copy.deepcopy(previous['content_json'])
        before = digest([raw_context, materials, enrichment, prior])
        base = case_model_boundary.build(context, snapshot['id'], enrichment, [], materials,
                                        execution_time=run['started_at'], run_id=run['id'])
        assert base['ready'], base['reason']
        if stage == 'C3':
            prepared = base
            messages, mapping = case_model_boundary.messages(base, context, [])
            output = case_output_adapter.output_format(base, context, {})
        else:
            question = next(q.id for q in context.questions if q.id != 'coverage')
            comparison = {'state': 'initial', 'result_id': None}
            prepared = case_followup_input.build(stage, context, base, {}, previous=prior, prior_id=previous['id'],
                question_id=question if stage == 'Deep' else None,
                extra={'comparison': comparison} if stage == 'C6' else None)
            assert prepared['ready'], prepared['reason']
            messages, mapping = prepared['messages'], prepared['source_map']
            output = (case_followup_output.deep_format(prepared) if stage == 'Deep'
                      else case_followup_output.final_format(prepared, context, comparison))
        unchanged = before == digest([raw_context, materials, enrichment, prior])
    gateway = SimpleNamespace(provider=policy.model.protocol, schema_profile=policy.model.schema_profile)
    wire = prepare_request(gateway, {'model': policy.model.alias, 'messages': messages,
        'max_tokens': policy.model.output_tokens[stage], 'temperature': 0, 'response_format': output})
    if 'selected_values' in prepared:
        selected = [{'field': mapping[sid]['ref']['source_path'], 'value': value}
                    for sid, value in prepared['selected_values'].items()]
    else:
        records = prepared.get('records') or (prepared.get('input_ledger') or prepared.get('followup_boundary') or {})['records']
        selected = [{'field': row.get('field') or row.get('ref', {}).get('source_path'), 'value': row['value']} for row in records]
    return wire, changes, selected, unchanged, before, run['id']


@pytest.mark.parametrize('stage', STAGES)
@pytest.mark.parametrize('variant', VARIANTS)
def test_lyc_metadata_excluded_from_actual_visible_messages(frozen, configured, stage, variant):
    original_bytes, rows = frozen
    before = digest(rows)
    policy, network_attempts = configured
    wire, markers, selected, unchanged, fixture_hash, run_id = construct(rows, policy, stage, variant)
    visible = json.dumps(wire['messages'], ensure_ascii=False)
    message_text = '\n'.join(m['content'] for m in wire['messages'])
    leaked = [m for m in markers if m['marker'] in visible]
    checks = {
        'nonempty_actual_messages': bool(wire['messages'] and selected and markers),
        'lyc_backend_markers_absent': not leaked,
        'source_file_bytes_unchanged': SNAPSHOT.read_bytes() == original_bytes,
        'loaded_frozen_rows_unchanged': digest(rows) == before,
        'derived_backend_inputs_unchanged': unchanged,
        'no_network_attempts': not network_attempts,
        'zero_preserved': has_typed_leaf(selected, 'amount', 0) and bool(re.search(r'amount[=：:]\s*0(?:\s|[,}])', message_text)),
        'false_preserved': has_typed_leaf(selected, 'authorized', False) and bool(re.search(r'authorized[=：:]\s*false', message_text)),
        'empty_list_preserved': has_typed_leaf(selected, 'permissions', []) and bool(re.search(r'permissions[=：:]\s*\[\]', message_text)),
        'same_named_business_fields_preserved': all(v in visible for v in BUSINESS.values() if isinstance(v, str)),
    }
    destination = os.environ.get('SOCAI2_LYC_EVIDENCE_DIR')
    if destination:
        folder = Path(destination); folder.mkdir(parents=True, exist_ok=True)
        receipt = {'stage': stage, 'variant': variant, 'checks': checks, 'injected_paths': markers,
                   'leaked_paths': leaked, 'wire': wire, 'source_snapshot': str(SNAPSHOT.relative_to(ROOT)),
                   'source_snapshot_sha256': hashlib.sha256(original_bytes).hexdigest(), 'source_run_id': run_id,
                   'derived_input_sha256': fixture_hash, 'policy_sha256': hashlib.sha256(POLICY.read_bytes()).hexdigest(),
                   'input_profiles': {'A': policy.alert_io.sha256, 'I': policy.incident_io.sha256, 'Case': policy.case_io.identity},
                   'provenance': 'offline_current_constructor_with_derived_metadata', 'new_model_calls': 0,
                   'network_attempts': len(network_attempts), 'business_writes': 0,
                   'Deep_scope': 'offline request construction only; no actual Deep response or D5 acceptance'}
        with (folder / f'{stage}-{variant}.json').open('x') as out:
            json.dump(receipt, out, ensure_ascii=False, indent=2)
    assert all(checks.values()), {'failed': [k for k, v in checks.items() if not v], 'leaked_paths': leaked}
