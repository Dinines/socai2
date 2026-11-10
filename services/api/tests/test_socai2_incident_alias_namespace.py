"""Generic alias-grammar fix plus unmodified, completed live I answers."""
import copy
import json
from pathlib import Path

import pytest
from app.socai2 import incident_model_boundary, incident_output_adapter, runtime_policy
from app.socai2.answer_validation import Checks
from app.socai2.baseline_store import StoreError

ROOT = Path(__file__).resolve().parents[3]
BATCH = ROOT / 'docs/operations/evidence/incident-integration-validation-20261108-01'


def recorded(key, monkeypatch, *, original=False):
    policy = runtime_policy.load_policy(ROOT / 'deploy/local-investigation/investigation-policy-incident-v1.toml')
    monkeypatch.setattr(runtime_policy, 'active_policy', lambda: policy)
    data = json.loads((BATCH / 'readback' / key / 'database.json').read_text())
    run = data['runs'][0]
    source = next(a['content_json'] for a in data['artifacts'] if a['id'] == run['input_artifact_id'])
    request = next(a['content_json'] for a in data['artifacts'] if a['kind'] == 'model_request')
    response = next(a['content_json'] for a in data['artifacts'] if a['kind'] == 'model_response')
    profile = policy.incident_io
    if original:
        import hashlib
        raw = (BATCH / 'frozen-incident-profile.json').read_bytes()
        profile = runtime_policy.IncidentProfile(profile.version, hashlib.sha256(raw).hexdigest(), raw)
    messages, _, _, prepared = incident_model_boundary.build(source, run['input_artifact_id'], profile,
        execution_time=run['started_at'])
    assert messages == request['body']['messages']  # No prompt or input changes to make a replay pass.
    assert prepared['source_map'] == request['source_map']
    assert prepared['member_aliases'] == request['incident_boundary']['member_aliases']
    return prepared, response['raw']['choices'][0]['message']['content'], response['validation_error']


def test_real_cloud_answer_is_accepted_without_rewriting_any_text(monkeypatch):
    before = (BATCH / 'readback/E2/database.json').read_bytes()
    old, content, error = recorded('E2', monkeypatch, original=True)
    with pytest.raises(StoreError, match=error):
        incident_output_adapter.parse(content, old)
    new, same, _ = recorded('E2', monkeypatch)
    assert same == content
    output, members = incident_output_adapter.parse(content, new)
    answer = json.loads(content)
    assert output.summary == answer['diagnosis']['summary'] and output.conclusion == answer['diagnosis']['conclusion']
    assert len(members) == 2 and len(output.open_questions) == 3
    assert (BATCH / 'readback/E2/database.json').read_bytes() == before
    assert new['boundary']['output_validation'] == {'prose_alias_format': 'namespaced_v1'}


@pytest.mark.parametrize('key', ['E1', 'E3'])
def test_real_wrong_member_references_still_fail(key, monkeypatch):
    prepared, content, error = recorded(key, monkeypatch)
    with pytest.raises(StoreError, match=error):
        incident_output_adapter.parse(content, prepared)


def test_unprefixed_business_tokens_are_not_promoted_to_citations():
    mapping = {'N1_S1': {'ref': {'role': 'observation'}, 'alert_ids': ['a']}}
    data = {'items': [], 'citations': 'structured_v3', 'prose_alias_format': 'namespaced_v1'}
    checks = Checks()
    checks.prose('S3, S12 and S999 are ordinary business text.', '$', [], mapping, data, 'incident_answer')
    assert checks.entries == []
    checks.prose('N1_S1', '$', [], mapping, data, 'incident_answer')
    assert checks.entries[-1]['code'] == 'inline_source_not_structured_evidence' and checks.first_error is None
    checks.prose('N9_S1', '$', [], mapping, data, 'incident_answer')
    assert checks.first_error == 'incident_answer_prose_source_unbound'


def test_bare_alias_in_structured_array_and_cross_member_prose_are_still_rejected(monkeypatch):
    prepared, content, _ = recorded('E2', monkeypatch)
    answer = json.loads(content)
    answer['diagnosis']['source_ids'] = ['S3']
    with pytest.raises(StoreError, match='incident_answer_source_invalid'):
        incident_output_adapter.parse(json.dumps(answer), prepared)
    checks = Checks()
    mapping = {'N1_S1': {'ref': {'role': 'observation'}, 'alert_ids': ['other']}}
    checks.prose('N1_S1', '$', [], mapping, prepared['data'], 'incident_answer', owned=['own'])
    assert checks.first_error == 'incident_answer_prose_source_wrong_member'


def test_legacy_prose_grammar_and_invalid_profile_do_not_change(monkeypatch):
    checks = Checks()
    checks.prose('Source S3', '$', [], {}, {'items': [], 'citations': 'structured_v3'}, 'incident_answer')
    assert checks.first_error == 'incident_answer_prose_source_unbound'
    valid = json.loads((ROOT / 'services/api/app/socai2/incident-input-v1.json').read_text())
    invalid = copy.deepcopy(valid)
    invalid['output_validation'] = {'prose_alias_format': 'ignore_all_sources'}
    monkeypatch.setattr(Path, 'read_bytes', lambda _: json.dumps(invalid).encode())
    with pytest.raises(ValueError, match='incident_profile_output_validation_invalid'):
        runtime_policy.load_incident_profile({'profile': 'incident-input-v1.json'})
