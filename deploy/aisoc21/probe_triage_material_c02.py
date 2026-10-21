"""One synthetic, offline C02 prompt request against the baked Agents image.

Inside-only operator: python /operators/probe_triage_material_c02.py inside
The host owns Docker --network none, UID10001, read-only root/source, /tmp
tmpfs and the writable /evidence mount. No pytest or porting test is imported.
contract.json must bind image_id, all 184 source_sha256 entries, this
operator_sha256 and unit_test_record_sha256. All result files are exclusive.

Required dummy environment:
 ENVIRONMENT=production, PYTHONPATH=/app, PYTHONDONTWRITEBYTECODE=1,
 C02_PROBE_IMAGE_ID=<fixed candidate image ID>, C02_PROBE_SYNTHETIC_ONLY=1,
 LLM_GATEWAY_URL=http://127.0.0.1.invalid/v1,
 LITELLM_MASTER_KEY=synthetic-c02-no-credential,
 AISOC_LLM_RESPONSE_CACHE=0, AISOC_PSEUDONYMIZE_EGRESS=0,
 AISOC_AGENT_KAFKA_DISABLE=1, OTEL_SDK_DISABLED=true.
No real service env file, credentials, DB/Kafka route or reader mount is used.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
E = Path('/evidence')
DUMMY_URL = 'http://127.0.0.1.invalid/v1'
DUMMY_KEY = 'synthetic-c02-no-credential'
FILES = ('inputs.json', 'request.json', 'response-summary.json', 'acceptance.json', 'failure.json')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def save(name, value):
    with (E / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    (E / name).chmod(0o600)


async def inside():
    assert os.geteuid() == 10001 and os.environ.get('ENVIRONMENT') == 'production'
    assert os.environ.get('C02_PROBE_SYNTHETIC_ONLY') == '1'
    assert os.environ.get('LLM_GATEWAY_URL') == DUMMY_URL
    assert os.environ.get('LITELLM_MASTER_KEY') == DUMMY_KEY
    assert os.environ.get('AISOC_LLM_RESPONSE_CACHE') == os.environ.get('AISOC_PSEUDONYMIZE_EGRESS') == '0'
    assert os.environ.get('AISOC_AGENT_KAFKA_DISABLE') == '1'
    assert not any((E / name).exists() for name in FILES), 'Preserve any prior result; do not replay this operator.'
    contract_data = json.loads((E / 'contract.json').read_text())
    image = contract_data['image_id']
    assert re.fullmatch(r'sha256:[0-9a-f]{64}', image)
    assert os.environ['C02_PROBE_IMAGE_ID'] == image
    assert contract_data['operator_sha256'] == sha(__file__)
    assert re.fullmatch(r'[0-9a-f]{64}', contract_data['unit_test_record_sha256'])
    source = {'services/agents/app/' + str(path.relative_to('/app/app')): sha(path)
              for path in sorted(Path('/app/app').rglob('*.py'))}
    assert len(source) == 184 and source == contract_data['source_sha256']

    import httpx
    import structlog
    from app.agents import auto_triage_agent as agent
    from app.closure import policy as closure_policy
    from app.core.cost_telemetry import CostTracker
    from app.llm import contract
    from app.llm.factory import make_chat_model
    from app.models import state as state_module
    from app.workers import fused_alert_consumer as worker
    from app.workers import triage_budget as budget

    def drop_log(_logger, _method, _event):
        raise structlog.DropEvent
    structlog.configure(processors=[drop_log])
    logging.disable(logging.CRITICAL)
    for module in (agent, closure_policy, contract, worker, budget):
        assert Path(module.__file__).resolve().is_relative_to('/app/app'), 'Probe must use baked production modules.'
    assert worker.worker_enabled() is False and contract._RESPONSE_CACHE_ENABLED is False
    assert state_module._LLM_LITERAL_LIMIT == 8000 and budget.PROMPT_BYTE_CAP == 16000

    description = 'C02 synthetic source description.\n' + 'abcdef0123456789' * 110
    event_time, created_at = '2026-10-20T11:01:00+08:00', '2026-10-20T03:05:00Z'
    tenant, alert_id = '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222'
    envelope = {'id': alert_id, 'alert_row_id': alert_id, 'tenant_id': tenant,
        'incident_id': '33333333-3333-3333-3333-333333333333',
        'alert': {'id': alert_id, 'tenant_id': tenant, 'source': 'socai2-c02-synthetic-only',
                  'title': 'C02 bounded material transport fixture', 'severity': 'medium', 'risk_score': 0,
                  'description': description, 'event_time': event_time, 'created_at': created_at,
                  'source_event_ids': ['c02-synthetic-only'], 'raw_event': {}}}
    save('inputs.json', {'synthetic_only': True, 'persisted_or_published': False, 'envelope': envelope})
    state = worker.build_state(envelope)
    assert state is not None and state.raw_alert['description'] == description
    assert state.raw_alert['event_time'] == event_time and state.raw_alert['created_at'] == created_at
    assert state.raw_alert['risk_score'] == 0 and state.raw_alert['source_event_ids'] == ['c02-synthetic-only']
    fake_answer = {'verdict': 'needs_review', 'confidence': .5, 'rationale': 'Synthetic fixture requires review.'}
    fixture_usage = {'prompt_tokens': 11, 'completion_tokens': 7, 'total_tokens': 18}
    fixture_response = {'id': 'c02-synthetic-completion', 'object': 'chat.completion', 'created': 1,
        'model': 'synthetic-c02-observed', 'choices': [{'index': 0,
        'message': {'role': 'assistant', 'content': json.dumps(fake_answer)}, 'finish_reason': 'stop'}],
        'usage': fixture_usage}
    requests, budget_events, closure_events = [], [], []

    async def transport(request):
        assert len(requests) == 0 and str(request.url).startswith(DUMMY_URL + '/')
        body = json.loads(request.content)
        requests.append(body)
        # Deliberately store body only. Authorization is a dummy fixture and
        # still does not belong in exported request evidence.
        save('request.json', {'synthetic_only': True, 'transport': 'httpx.MockTransport',
             'real_network_request': False, 'body': body})
        # No cost headers: real/provider expenditure remains unknown.
        return httpx.Response(200, json=fixture_response)

    async def memory_budget_update(run_id, tenant_id, sql, *args):
        assert run_id == state.run_id and tenant_id == state.tenant_id
        if args:
            assert len(args) == 1 and args[0] == 18 and 'observed_tokens=$3' in sql
            budget_events.append({'stage': 'responded', 'synthetic_observed_tokens': args[0]})
        else:
            assert 'request_started_at=clock_timestamp()' in sql
            budget_events.append({'stage': 'request_intent'})
        # This seam is in-memory only; no PG reservation/claim/update is made.

    async def no_closure_pool():
        closure_events.append('pool dependency substituted with None')
        return None

    original_factory, original_update, original_pool = agent.make_chat_model, budget._update, closure_policy._pool
    invocation = budget.Invocation(state.run_id, state.tenant_id, lambda: False)
    try:
        budget._update, closure_policy._pool = memory_budget_update, no_closure_pool
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            model = make_chat_model('triage', max_tokens=512, json_output=True, http_async_client=client, include_response_headers=True)
            assert str(model.root_async_client.base_url).rstrip('/') == DUMMY_URL
            assert model.max_tokens == 512 and model.root_async_client.max_retries == 0
            assert model.request_timeout == model.root_async_client.timeout == 45.0
            agent.make_chat_model = lambda *args, **kwargs: model
            with budget.invocation_scope(invocation):
                async with CostTracker(run_id=str(state.run_id), tenant_id=tenant, persist=False) as tracker:
                    result = await agent.run_auto_triage(state)
    finally:
        agent.make_chat_model, budget._update, closure_policy._pool = original_factory, original_update, original_pool

    assert len(requests) == len(result.llm_exchanges) == 1 and len(closure_events) == 1
    body = requests[0]
    messages = body['messages']
    assert len(messages) == 2 and messages[0]['role'] == 'system' and messages[1]['role'] == 'user'
    telemetry = messages[1]['content']
    start, end = telemetry.index('<UNTRUSTED_DATA source="alert_telemetry">'), telemetry.index('</UNTRUSTED_DATA>')
    assert start < telemetry.index('Alert description (publisher supplied, untrusted):') < end
    assert start < telemetry.index('Event time (source alert.event_time; no fallback):') < end
    assert start < telemetry.index('Alert created_at (source creation field; not event time):') < end
    assert event_time + ' [explicit UTC offset retained]' in telemetry and created_at in telemetry
    expected_description = description[:1200].rstrip() + '…[truncated]'
    assert expected_description in telemetry and description not in telemetry
    assert result.raw_alert['description'] == description and result.raw_alert['event_time'] == event_time
    assert result.verdict == fake_answer['verdict'] and result.confidence == fake_answer['confidence']
    exchange = result.llm_exchanges[0]
    recorded_prompt = json.dumps(messages, sort_keys=True, default=str)
    assert exchange['prompt'] == recorded_prompt and exchange['prompt_truncated'] is False
    assert len(recorded_prompt) <= 8000
    normalized = contract.LLMInputContract.validate(messages)
    request_bytes = len(json.dumps(normalized, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
    output_caps = {key: body[key] for key in ('max_tokens', 'max_completion_tokens') if key in body}
    assert request_bytes <= 16000 and output_caps and all(value == 512 for value in output_caps.values())
    assert invocation.request_marked and invocation.response_seen
    assert budget_events == [{'stage': 'request_intent'}, {'stage': 'responded', 'synthetic_observed_tokens': 18}]
    assert tracker.total_tokens == 18 and tracker.calls_made == 1 and tracker.measured_cost_usd is None
    assert tracker._records[0].prompt_tokens == 11 and tracker._records[0].completion_tokens == 7
    assert budget.current_invocation() is None

    save('response-summary.json', {'synthetic_only': True, 'fixture_response_sha256': digest(fixture_response),
        'fixture_usage': fixture_usage, 'sdk_usage_extracted': {'prompt_tokens': tracker._records[0].prompt_tokens,
        'completion_tokens': tracker._records[0].completion_tokens, 'total_tokens': tracker.total_tokens},
        'usage_origin': 'mock response fixture, not provider/model usage', 'measured_provider_cost_usd': None,
        'result': {'verdict': result.verdict, 'confidence': result.confidence},
        'budget_updates': budget_events, 'budget_pg_updates_substituted': True, 'pg_claims': 0,
        'actual_closure_policy_function': True, 'closure_pool_substituted_with_none': True,
        'real_model_calls': 0, 'actual_network_requests': 0, 'pg_writes': 0, 'new_kafka_messages': 0})
    assert source == {'services/agents/app/' + str(path.relative_to('/app/app')): sha(path)
                      for path in sorted(Path('/app/app').rglob('*.py'))}
    save('acceptance.json', {'accepted': True, 'synthetic_only': True, 'image_id': image,
        'source_sha256': source, 'source_count': len(source), 'operator_sha256': sha(__file__),
        'unit_test_record_sha256': contract_data['unit_test_record_sha256'],
        'build_state_to_real_agent_safe_call_sdk': True, 'module_imports_from_baked_app': True,
        'description_retained_in_state': True, 'description_adopted_prefix_chars': 1200,
        'description_visible_truncation_marker': True, 'material_inside_original_untrusted_telemetry': True,
        'explicit_source_offset_retained': True, 'created_at_not_used_as_event_time': True,
        'full_messages_literal_chars': len(recorded_prompt), 'ledger_literal_limit': 8000,
        'canonical_message_utf8_bytes': request_bytes, 'canonical_message_byte_limit': 16000,
        'output_token_cap': 512, 'sdk_retries': 0, 'sdk_timeout_seconds': 45.0,
        'mock_http_requests': 1, 'synthetic_usage_tokens': tracker.total_tokens,
        'actual_usage_unknown': True, 'pg_claims_or_updates': 0, 'pg_writes': 0,
        'new_kafka_messages': 0, 'broker_offset_commits': 0, 'real_model_calls': 0, 'real_models': 0,
        'real_network_requests': 0, 'cached_unit_suite_replaced_by_probe': False,
        'evidence_sha256': {name: sha(E / name) for name in FILES[:3]}})
    print(json.dumps({'accepted': True, 'synthetic_only': True, 'image_id': image,
                      'mock_http_requests': 1, 'real_model_calls': 0, 'pg_writes': 0, 'new_kafka_messages': 0}))


if __name__ == '__main__':
    os.umask(0o077)
    try:
        assert sys.argv[1:] == ['inside']
        asyncio.run(inside())
    except BaseException as exc:
        failure = E / 'failure.json'
        if E.is_dir() and not failure.exists():
            save(failure.name, {'failed': True, 'exception_type': type(exc).__name__,
                 'synthetic_only': True, 'message_or_locals_recorded': False,
                 'action': 'Preserve existing artifacts; inspect before any new attempt.'})
        print(json.dumps({'failed': True, 'exception_type': type(exc).__name__, 'message_or_locals_recorded': False}))
        raise SystemExit(1) from None
