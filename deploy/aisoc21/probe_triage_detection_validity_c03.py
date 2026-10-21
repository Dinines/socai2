"""Inside-only C03-02D-01: four sequential, disconnected SDK transport fixtures.

Use baked /app; mount only public operator/source, one controlled fixture file
and writable /evidence. No real env/private/key/reader mount or pytest import.
No provider, Invocation/claim, PG, broker or current reader call is made.
Fixed replies prove rendering/transport only, never model reasoning quality.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sys

E = Path('/evidence')
FIXTURE = Path('/fixtures/materials.json')
URL = 'http://127.0.0.1.invalid/v1'
KEY = 'synthetic-c03-no-credential'
READS = ('organisation_memory_read', 'tenant_skill_read', 'knowledge_base_read',
         'recent_dispositions_read', 'identity_context_read')
MATERIALS = ('organisation_memory', 'tenant_skill', 'knowledge_base',
             'recent_dispositions', 'identity_context')
GUIDANCE = ('- Distinguish observed harm from authorization status. Harmful behavior may\n'
    '  support true_positive while authorization remains unknown. Assert an\n'
    '  authorization decision only when an applicable decision is supplied.\n'
    '  Use needs_review when remaining gaps prevent judging threat.')

DETECTION_GUIDANCE = ("- Missing evidence is not a rule misfire. Use needs_review when the rule's\n"
    "  condition cannot be checked; false_positive needs supplied contrary evidence.")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(directory, name, value):
    with (directory / name).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    (directory / name).chmod(0o600)


def sources():
    return {'services/agents/app/' + str(path.relative_to('/app/app')): sha(path)
            for path in sorted(Path('/app/app').rglob('*.py'))}


async def one(case, item, prompt):
    import httpx
    from app.agents import auto_triage_agent as agent
    from app.closure import policy as closure
    from app.core.cost_telemetry import CostTracker
    from app.llm import contract, egress_privacy
    from app.workers import fused_alert_consumer as worker
    from app.workers import triage_budget as budget
    for module in (agent, closure, contract, worker, budget):
        assert Path(module.__file__).resolve().is_relative_to('/app/app')
    directory = E / 'cases' / case
    directory.mkdir(parents=True, exist_ok=False)
    save(directory, 'inputs.json', {'synthetic_only': True, 'constructed_transport_fixture': True,
         'actual_reader_calls': 0, **item})
    state = worker.build_state(deepcopy(item['envelope']))
    assert state is not None and set(item['materials']) == set(MATERIALS) and set(item['reads']) == set(READS)
    for key, value in {**item['materials'], **item['reads']}.items():
        setattr(state, key, deepcopy(value))
    assert budget.current_invocation() is None
    answer = {'verdict': 'needs_review', 'confidence': .5, 'rationale': 'Synthetic transport fixture requires review.'}
    usage = {'prompt_tokens': 11, 'completion_tokens': 7, 'total_tokens': 18}
    seen = {'safe': 0, 'egress': 0, 'sdk': 0, 'closure_pool': 0}
    original_factory, original_safe = agent.make_chat_model, agent.safe_ainvoke
    original_redact, original_pool = egress_privacy.EgressSession.redact_messages, closure._pool
    observed = {}

    async def safe(model, messages, *args, **kwargs):
        seen['safe'] += 1
        assert seen['safe'] == 1 and budget.current_invocation() is None
        materialized = list(messages)
        observed['pre'] = contract.LLMInputContract.validate(materialized)
        save(directory, 'egress-pre-messages.json', observed['pre'])
        return await original_safe(model, materialized, *args, **kwargs)

    def redact(session, messages):
        seen['egress'] += 1
        assert seen['egress'] == 1
        result = original_redact(session, messages)
        observed['post'] = contract.LLMInputContract.validate(result)
        save(directory, 'egress-post-messages.json', observed['post'])
        return result

    async def transport(request):
        seen['sdk'] += 1
        assert seen['sdk'] == 1 and str(request.url).startswith(URL + '/')
        assert budget.current_invocation() is None
        body = json.loads(request.content)
        assert body['messages'] == observed['post']
        assert body['messages'][0]['content'].startswith(prompt.text + '\n\n')
        assert GUIDANCE in body['messages'][0]['content'] and DETECTION_GUIDANCE in body['messages'][0]['content']
        telemetry = body['messages'][1]['content']
        for field in ('description', 'event_time', 'created_at'):
            value = state.raw_alert[field]
            assert isinstance(value, str) and value in telemetry
        literal = json.dumps(body['messages'], sort_keys=True, default=str)
        canonical = json.dumps(contract.LLMInputContract.validate(body['messages']),
                               sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
        assert len(literal) <= 8000 and len(canonical) <= 16000
        caps = [body[key] for key in ('max_tokens', 'max_completion_tokens') if key in body]
        assert caps and all(value == 512 for value in caps)
        assert body['response_format'] == {'type': 'json_object'}
        observed.update(body=body, literal=literal, byte_count=len(canonical))
        save(directory, 'request.json', {'synthetic_only': True, 'transport': 'httpx.MockTransport',
             'real_network_request': False, 'body': body})  # Body only, no headers.
        return httpx.Response(200, json={'id': 'c03-auth-' + case, 'object': 'chat.completion',
            'created': 1, 'model': 'synthetic-c03-detection-validity',
            'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': json.dumps(answer)},
                         'finish_reason': 'stop'}], 'usage': usage})

    async def no_pool():
        seen['closure_pool'] += 1
        return None

    try:
        closure.reset_cache()
        closure._pool = no_pool
        agent.safe_ainvoke = safe
        egress_privacy.EgressSession.redact_messages = redact
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            def factory(*args, **kwargs):
                assert 'http_async_client' not in kwargs
                model = original_factory(*args, **kwargs, http_async_client=client)
                assert str(model.root_async_client.base_url).rstrip('/') == URL
                assert model.max_tokens == 512 and model.root_async_client.max_retries == 0
                assert model.request_timeout == model.root_async_client.timeout == 45.0
                return model
            agent.make_chat_model = factory
            async with CostTracker(run_id=str(state.run_id), tenant_id=str(state.tenant_id), persist=False) as tracker:
                result = await agent.run_auto_triage(state)
    finally:
        agent.make_chat_model, agent.safe_ainvoke = original_factory, original_safe
        egress_privacy.EgressSession.redact_messages, closure._pool = original_redact, original_pool
    assert seen == {'safe': 1, 'egress': 1, 'sdk': 1, 'closure_pool': 1}
    assert len(result.llm_exchanges) == 1 and result.llm_exchanges[0]['prompt'] == observed['literal']
    assert result.llm_exchanges[0]['prompt_truncated'] is False
    assert result.verdict == answer['verdict'] and result.confidence == answer['confidence']
    assert tracker.calls_made == 1 and tracker.total_tokens == 18 and tracker.measured_cost_usd is None
    assert tracker._records[0].prompt_tokens == 11 and tracker._records[0].completion_tokens == 7
    assert budget.current_invocation() is None
    row = {'case': case, 'accepted': True, 'synthetic_only': True, 'actual_reader_calls': 0,
        'constructed_from_frozen_five_source_fixture': True, 'full_messages_literal_chars': len(observed['literal']),
        'canonical_message_utf8_bytes': observed['byte_count'], 'ledger_literal_limit': 8000,
        'canonical_message_byte_limit': 16000, 'mock_http_requests': 1, 'real_model_calls': 0,
        'pg_claims_or_updates': 0, 'pg_writes': 0, 'new_kafka_messages': 0,
        'sdk_retries': 0, 'sdk_timeout_seconds': 45.0, 'output_token_cap': 512,
        'fixture_usage': usage, 'provider_usage_or_cost_measured': False,
        'source_snapshot_does_not_establish_current_authorization': True,
        'evidence_sha256': {name: sha(directory / name) for name in
            ('inputs.json', 'egress-pre-messages.json', 'egress-post-messages.json', 'request.json')}}
    save(directory, 'response-summary.json', row)
    return row


async def inside():
    import structlog
    assert os.geteuid() == 10001 and os.environ.get('ENVIRONMENT') == 'production'
    assert os.environ.get('C03_PROBE_SYNTHETIC_ONLY') == '1'
    assert os.environ.get('LLM_GATEWAY_URL') == URL and os.environ.get('LITELLM_MASTER_KEY') == KEY
    assert os.environ.get('AISOC_LLM_RESPONSE_CACHE') == os.environ.get('AISOC_PSEUDONYMIZE_EGRESS') == '0'
    assert os.environ.get('AISOC_AGENT_KAFKA_DISABLE') == '1'
    assert not (E / 'acceptance.json').exists() and not (E / 'cases').exists()
    def drop(*args):
        raise structlog.DropEvent
    structlog.configure(processors=[drop])
    logging.disable(logging.CRITICAL)
    contract_data = json.loads((E / 'contract.json').read_text())
    assert contract_data['image_id'] == os.environ['C03_PROBE_IMAGE_ID']
    assert re.fullmatch(r'sha256:[0-9a-f]{64}', contract_data['image_id'])
    assert contract_data['operator_sha256'] == sha(__file__)
    assert re.fullmatch(r'[0-9a-f]{64}', contract_data['parent_quality_acceptance_sha256'])
    assert sources() == contract_data['source_sha256'] and len(sources()) == 184
    assert sha('/app/app/llm/prompts.lock.json') == contract_data['lock_sha256']
    assert sha(FIXTURE) == contract_data['fixture_sha256']
    assert re.fullmatch(r'[0-9a-f]{64}', contract_data['unit_test_record_sha256'])
    from app.llm.prompt_registry import default_registry, load_lock
    from app.llm import contract
    from app.models import state
    from app.workers import triage_budget as budget
    from app.workers import fused_alert_consumer as worker
    registry = default_registry()
    assert registry.verify_against_lock(load_lock()) == []
    prompt = registry.get('triage.system')
    assert prompt.version == '5' and prompt.text.endswith(GUIDANCE + '\n') and DETECTION_GUIDANCE in prompt.text
    assert state._LLM_LITERAL_LIMIT == 8000 and budget.PROMPT_BYTE_CAP == 16000
    assert worker.worker_enabled() is False and contract._RESPONSE_CACHE_ENABLED is False
    assert budget.current_invocation() is None
    data = json.loads(FIXTURE.read_text())
    assert data['synthetic_only'] is True and data['case_order'] == ['case01', 'case02', 'case03', 'case04']
    rows = []
    for case in data['case_order']:  # Only four fixed, offline Mock cases.
        rows.append(await one(case, data['cases'][case], prompt))
    assert sources() == contract_data['source_sha256'] and sum(row['mock_http_requests'] for row in rows) == 4
    save(E, 'acceptance.json', {'accepted': True, 'synthetic_only': True, 'image_id': contract_data['image_id'],
        'source_sha256': sources(), 'source_count': 184, 'operator_sha256': sha(__file__),
        'unit_test_record_sha256': contract_data['unit_test_record_sha256'],
        'lock_sha256': contract_data['lock_sha256'], 'fixture_sha256': contract_data['fixture_sha256'],
        'triage_prompt_version': '5', 'triage_prompt_sha256': prompt.sha256,
        'cases': rows, 'mock_http_requests': 4, 'real_models': 0, 'real_model_calls': 0,
        'real_network_requests': 0, 'actual_reader_calls': 0, 'pg_claims_or_updates': 0,
        'pg_writes': 0, 'new_kafka_messages': 0, 'broker_offset_commits': 0,
        'all_four_constructed_transport_fixtures_not_reader_or_model_quality': True,
        'three_reused_stored_preflight_material_snapshots': True, 'fourth_is_constructed_unexecuted_transport_only': True,
        'cached_unit_suite_replaced_by_probe': False})
    print(json.dumps({'accepted': True, 'mock_http_requests': 4, 'real_models': 0, 'image_id': contract_data['image_id']}))


if __name__ == '__main__':
    os.umask(0o077)
    sys.dont_write_bytecode = True
    try:
        assert sys.argv[1:] == ['inside']
        asyncio.run(inside())
    except BaseException as error:
        if E.is_dir() and not (E / 'failure.json').exists():
            save(E, 'failure.json', {'exception_type': type(error).__name__, 'synthetic_only': True,
                'message_or_locals_recorded': False, 'automatic_retry': False})
        print(json.dumps({'failed': True, 'exception_type': type(error).__name__, 'message_or_locals_recorded': False}))
        raise SystemExit(1) from None
