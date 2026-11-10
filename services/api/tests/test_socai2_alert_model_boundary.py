"""A deployment boundary against frozen originals and structural edge cases."""
import copy
import json
from pathlib import Path

import pytest
from app.socai2 import alert_model_boundary, alert_output_adapter, runtime_policy
from app.socai2.baseline_model_view import blocked
from app.socai2.baseline_store import StoreError
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / 'docs/operations/evidence/production-multialert-20261108-01/exports/20261108T013952440775Z/database.json'


@pytest.fixture
def sample(monkeypatch):
    policy = runtime_policy.load_policy(ROOT / 'deploy/local-investigation/investigation-policy-ai-v1.toml')
    monkeypatch.setattr(runtime_policy, 'active_policy', lambda: policy)
    data = json.loads(SNAPSHOT.read_text())
    run = next(r for r in data['runs'] if r['kind'] == 'alert_basic')
    source = next(a['content_json'] for a in data['artifacts'] if a['id'] == run['input_artifact_id'])
    queries = [(a['id'], a['content_json']) for a in data['artifacts'] if a['run_id'] == run['id'] and a['kind'] == 'tool_response']
    return source, run['input_artifact_id'], queries, policy.alert_io


def build(sample):
    return alert_model_boundary.build(*sample)[-1]


def answer(prepared):
    sid = next(s for s, ref in prepared['source_map'].items() if ref['ref']['role'] == 'observation')
    return {'verdict': 'needs_review', 'confidence': None, 'rationale': 'S3 业务记录尚待核实。',
            'evidence_ids': [sid], 'recommendations': []}


def test_frozen_input_and_v3_prompt_are_preserved(sample):
    original = copy.deepcopy(sample)
    messages, mapping, data, prepared = alert_model_boundary.build(*sample)
    assert sample == original and mapping == prepared['source_map']
    assert messages[0]['content'] == (ROOT / 'tools/testdata/alert_prompt_eval/five-field-system-v3.txt').read_text()
    raw = sample[0]['members'][0]['material']['raw_text']
    if blocked(raw):
        assert any(o['source']['source_path'] == '$.raw_text' and o['reason'] == 'input_guard'
                   for o in data['omission_details'])
    else:
        assert raw in messages[1]['content']
    assert data['program_facts']['query_statuses']
    assert prepared['boundary']['output_validation'] == {'prose_alias_format': 'namespaced_v1'}


def test_unknown_nested_ids_zero_false_empty_and_prose_survive(sample):
    sample[0]['members'][0]['material']['raw_text'] = '这份原始描述必须完整保留。'
    sample[0]['members'][0]['material']['raw_json']['custom'] = {
        'id': 'business-id', 'schema_version': 'business-v2', 'size': 0, 'authorized': False,
        'permissions_after': [], 'details': {'id': 'nested-id'}, 'text': '原文不得改写。'}
    p = build(sample)
    for value in ('business-id', 'business-v2', 'nested-id', 'false', 'permissions_after', '[]', '原文不得改写。'):
        assert value in p['user']
    assert '"size"' in p['user'] or '$.raw_json.custom.size' in p['user']
    assert sample[0]['members'][0]['alert']['id'] not in p['user']
    assert sample[0]['members'][0]['material']['raw_text'] in p['user']


def test_five_fields_restore_original_contract_without_rejudging(sample):
    prepared = build(sample); body = answer(prepared)
    Draft202012Validator(alert_output_adapter.schema(prepared['source_map'])['json_schema']['schema']).validate(body)
    result = alert_output_adapter.parse(json.dumps(body), prepared)
    assert result.verdict == body['verdict'] and result.rationale == body['rationale']
    assert result.confidence is None and result.score_state == 'not_computed'
    assert result.generation_method == 'template' and result.explanation.endswith(body['rationale'])


@pytest.mark.parametrize('changes', [{'evidence_ids': []}, {'evidence_ids': ['N999_S999']},
                                    {'confidence': 2}, {'tenant_id': 'extra'}])
def test_invalid_core_is_failed_not_unknown_or_rewritten(sample, changes):
    prepared = build(sample)
    with pytest.raises(StoreError):
        alert_output_adapter.parse(json.dumps(answer(prepared) | changes), prepared)
    result, _ = alert_output_adapter.review(json.dumps(answer(prepared) | changes), prepared)
    assert result is None


def test_invalid_advice_does_not_discard_valid_core(sample):
    prepared = build(sample); body = answer(prepared)
    body['recommendations'] = [{'reason': '需核实授权。', 'source_ids': body['evidence_ids']},
                               {'reason': '错误引用。', 'source_ids': ['N999_S999']}]
    result, review = alert_output_adapter.review(json.dumps(body), prepared)
    assert result.rationale == body['rationale'] and len(result.recommendations) == 1
    assert review['conclusion_adoptable'] and len(review['diagnostics']) == 1
    assert result.generation_method == 'template'


def test_labels_cannot_be_used_as_definitive_basis_and_old_mode_is_opt_in(sample):
    prepared = build(sample); body = answer(prepared)
    body.update(verdict='benign', evidence_ids=[next(s for s, ref in prepared['source_map'].items()
                                                 if ref['ref']['role'] == 'source_label')])
    with pytest.raises(StoreError, match='direct'):
        alert_output_adapter.parse(json.dumps(body), prepared)
    assert runtime_policy.load_policy(ROOT / 'deploy/local-investigation/investigation-policy.toml').alert_io is None
