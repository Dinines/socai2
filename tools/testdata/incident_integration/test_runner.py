"""Checks before permitting the bounded live integration batch."""
import asyncio
import copy
import json
from pathlib import Path

import pytest
from app.socai2.model_errors import ModelCallError
from app.socai2.runtime_policy import active_policy

from tools.testdata.incident_integration import fixtures, gateway, run

ROOT = Path(__file__).resolve().parents[3]


def test_packets_preserve_source_values_and_do_not_send_answer_keys():
    config = json.loads((Path(__file__).parent / 'config.json').read_text())
    before = copy.deepcopy(config)
    packet = fixtures.packets(ROOT, config)
    assert config == before and len(packet) == 3 and sum(len(p['members']) for p in packet) == 7
    assert packet[2]['members'][1]['material'] is None
    text = json.dumps(packet)
    assert not any(key in text for key in ('expected_disposition', 'decisive_evidence', 'human_reasoning'))
    corpus = {v['id']: v for v in json.loads((ROOT / config['corpus']).read_text())['decisions']}
    for sample, scenario in zip(packet[1:], config['scenarios'][1:]):
        for member, key in zip(sample['members'], scenario['templates']):
            assert member['alert']['event_time'] is None  # Do not redate old ticket evidence.
            if member['material']:
                assert member['material']['raw_json'][scenario['block']] == corpus[key]['evidence']


def test_wrong_database_profile_is_rejected_before_connect(monkeypatch):
    monkeypatch.setattr(run, 'read', lambda _: {'processing_database': 'unexpected-business-database'})
    with pytest.raises(AssertionError, match='not_the_configured_isolated_database'):
        asyncio.run(run.connect({'database_profile': 'not-opened', 'expected_database': 'isolated'}))


def test_unknown_model_receipt_is_not_redispatched(monkeypatch, tmp_path):
    calls = []
    def remote(config, body):
        calls.append(body)
        return {'state': 'unknown_no_retry'}
    monkeypatch.setattr(gateway, 'remote', remote)
    value = gateway.Gateway({'preflight': {'state': 'ready'}}, tmp_path, 'E-test')
    with pytest.raises(ModelCallError):
        asyncio.run(value.complete({'messages': []}, 2))
    with pytest.raises(AssertionError):
        asyncio.run(value.complete({'messages': []}, 2))
    assert len(calls) == 1 and (tmp_path / 'model-intent.json').exists() and (tmp_path / 'model-receipt.json').exists()


def test_real_meter_contract_uses_both_relay_requests(monkeypatch, tmp_path):
    requests = []
    def tokenizer_call(config, request):
        requests.append(copy.deepcopy(request))
        return {'status': 200, 'body': {'count': 100, 'max_model_len': active_policy().model.context_tokens},
            'measurement_is_real': False}  # Explicit substitute in this pure check only.
    monkeypatch.setattr(gateway, 'tokenizer_call', tokenizer_call)
    value = gateway.Gateway({'preflight': {'state': 'ready'}}, tmp_path, 'E-test')
    body = {'model': value.model, 'messages': [{'role': 'user', 'content': 'test'}],
        'max_tokens': active_policy().model.output_tokens['I']}
    result = asyncio.run(value.measure(body, 'I'))
    assert len(requests) == 2
    assert requests[0]['body']['messages'] == body['messages']
    assert json.loads(requests[1]['body']['prompt']) == {k: v for k, v in body.items() if k != 'messages'}
    assert result['chat_tokens'] == result['envelope_tokens'] == 100
    assert (tmp_path / 'tokenizer-1.json').exists() and (tmp_path / 'tokenizer-2.json').exists()


def test_existing_batch_intent_stops_before_dispatch(monkeypatch, tmp_path):
    monkeypatch.setattr(run, 'validate_plan', lambda *_: {})
    monkeypatch.setattr(run, 'read', lambda _: {'state': 'committed'})
    (tmp_path / 'execute-intent.json').write_text('{}')
    with pytest.raises(AssertionError, match='batch_already_attempted_do_not_redispatch'):
        asyncio.run(run.execute({}, tmp_path))
