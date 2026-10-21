"""C03 prompt transport, preservation and existing budget boundaries.

The production state builder, safe-call, SDK and accounting paths are real;
HTTP and budget/closure database dependencies are explicit offline substitutes.
The same fixed answer is returned for every input. These checks do not grade
model reasoning, establish authorization, or implement a general time guard.
"""
from __future__ import annotations

import hashlib
import json
from unittest.mock import AsyncMock

import httpx
import pytest

from app.agents import auto_triage_agent as agent
from app.closure import policy as closure_policy
from app.core.cost_telemetry import CostTracker
from app.llm import contract
from app.llm.factory import make_chat_model
from app.llm.prompt_registry import default_registry, load_lock
from app.models import state as state_module
from app.workers import fused_alert_consumer as worker
from app.workers import triage_budget as budget

TENANT = '11111111-1111-1111-1111-111111111111'
ALERT = '22222222-2222-2222-2222-222222222222'
FIXTURE_ANSWER = {'verdict': 'needs_review', 'confidence': .5,
                  'rationale': 'Synthetic transport fixture requires review.'}

# C02 baseline: pins all other prompts and the existing classification/schema.
# This is not a pin over the newly written guidance being tested below.
OTHER_PROMPTS_SHA256 = 'ffc3815db66e4af819423df49a147789b3229adf119b1d33452ff24795c02640'
CLASSIFICATION_SCHEMA_SHA256 = 'a0b27c50764c86074e8c146cae902193ea0a234223f91130e296dc5bf9794e2a'

CASES = [
    pytest.param({
        'event_time': '2026-10-21T00:05:00+08:00',
        'created_at': '2026-10-21T03:00:00Z',
        'description': ('Rule detected a port scan by acct-r27 on host-k18 targeting 198.51.100.0/28. '
            'Approval CR-842 covers that account, host, target and port-scan action from '
            '2026-10-20T15:50:00Z through 2026-10-20T16:20:00Z.'),
    }, None, id='complete-window-cross-date-offset'),
    pytest.param({
        'event_time': '2026-10-20T11:01:00Z',
        'created_at': '2026-10-20T02:00:00Z',
        'description': ('Process deleted recovery snapshots and rewrote 37 canary files in 45 seconds. '
            'A supplied backup approval covers acct-r27 on host-k18 only from '
            '2026-10-20T01:50:00Z through 2026-10-20T02:20:00Z. No matching scheduled job was returned.'),
    }, 'Backup jobs on host-k18 usually run at 02:00 UTC.', id='outside-window-with-direct-behavior'),
    pytest.param({
        'event_time': '2026-10-20T11:01:00Z',
        'created_at': '2026-10-20T11:02:00Z',
        'description': ('Rule detected a port scan by acct-r27 on host-k18. '
            'Approval CR-843 supplies start 2026-10-20T10:50:00Z but supplies no end time. '
            'Account, target and action scopes were not provided.'),
    }, None, id='missing-end-and-scope'),
    pytest.param({
        'event_time': '2026-10-20T11:01:00',
        'created_at': '2026-10-20T11:02:00Z',
        'description': ('Rule detected a port scan by acct-r27 on host-k18. '
            'Approval CR-844 lists start 2026-10-20T10:50:00 and end 2026-10-20T11:20:00; '
            'no time zone is supplied for either endpoint or the event.'),
    }, None, id='missing-time-zones'),
    pytest.param({
        'event_time': '2026-10-20T11:01:00+08:00',
        'created_at': '2026-10-20T03:05:00Z',
        'description': ('Rule detected a port scan by acct-r27 on host-k18. '
            'No matching scheduled job was returned. The supplied material contains no approval '
            'record or explicit denial for this action, account and target.'),
    }, 'Similar scans were previously treated as expected maintenance.', id='missing-job-is-not-a-denial'),
]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv('LLM_GATEWAY_URL', 'http://c03-synthetic.invalid/v1')
    monkeypatch.setenv('LITELLM_MASTER_KEY', 'synthetic-c03-no-credential')
    monkeypatch.setenv('AISOC_AGENTS_LLM_CONTRACT_ENFORCED', '1')
    monkeypatch.delenv('OPENAI_BASE_URL', raising=False)
    monkeypatch.delenv('LLM_BASE_URL', raising=False)
    monkeypatch.setattr(contract, '_RESPONSE_CACHE_ENABLED', False)
    monkeypatch.setattr(contract.egress_privacy, '_FORCE', '0')
    # Preserve the actual closure decision function; only decline its DB pool.
    closure_policy.reset_cache()
    monkeypatch.setattr(closure_policy, '_pool', AsyncMock(return_value=None))


def make_state(fields, memory):
    envelope = {'id': ALERT, 'alert_row_id': ALERT, 'tenant_id': TENANT,
        'alert': {'id': ALERT, 'tenant_id': TENANT, 'source': 'c03-offline',
            'title': 'Activity recorded on host-k18', 'severity': 'medium',
            'hostname': 'host-k18', 'risk_score': None, 'source_event_ids': ['r-27'],
            'raw_event': {}, **fields}}
    state = worker.build_state(envelope)
    # These are source-status/material fixtures, not simulated successful HTTP
    # reader calls. All renderers still run through the production prompt path.
    state.tenant_skill_read = {'status': 'no_match', 'selection': {'status': 'no_match'}}
    state.organisation_memory_read = {'status': 'success' if memory else 'no_match'}
    state.knowledge_base_read = {'status': 'no_match'}
    state.recent_dispositions_read = {'status': 'no_match'}
    state.identity_context_read = {'status': 'success'}
    state.identity_context = {'identities': [{'account': 'acct-r27', 'title': 'Administrator', 'is_active': True}]}
    if memory:
        state.organisation_memory = [{'statement': memory, 'observations': 4}]
    return state


async def invoke_sdk(monkeypatch, state):
    requests, updates = [], AsyncMock()
    monkeypatch.setattr(budget, '_update', updates)

    async def transport(request):
        assert str(request.url).startswith('http://c03-synthetic.invalid/v1/')
        requests.append(json.loads(request.content))
        # Usage is a response fixture. No provider cost headers or real usage.
        return httpx.Response(200, json={
            'id': 'c03-synthetic', 'object': 'chat.completion', 'created': 1, 'model': 'c03-synthetic',
            'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': json.dumps(FIXTURE_ANSWER)},
                         'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 11, 'completion_tokens': 7, 'total_tokens': 18}})

    invocation = budget.Invocation(state.run_id, state.tenant_id, lambda: False)
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        model = make_chat_model('triage', max_tokens=512, json_output=True, http_async_client=client)
        assert model.max_retries == model.root_async_client.max_retries == 0
        assert model.request_timeout == model.root_async_client.timeout == 45.0
        monkeypatch.setattr(agent, 'make_chat_model', lambda *args, **kwargs: model)
        with budget.invocation_scope(invocation):
            async with CostTracker(run_id=str(state.run_id), tenant_id=TENANT, persist=False) as tracker:
                result = await agent.run_auto_triage(state)
    return requests, updates, invocation, tracker, result


def test_prompt_v5_lock_and_unchanged_taxonomy_schema_other_prompts():
    registry = default_registry()
    assert registry.verify_against_lock(load_lock()) == []
    assert registry.get('triage.system').version == '5'
    unchanged = {name: entry for name, entry in registry.as_lock().items() if name != 'triage.system'}
    canonical = json.dumps(unchanged, sort_keys=True, separators=(',', ':')).encode()
    assert len(unchanged) == 21 and hashlib.sha256(canonical).hexdigest() == OTHER_PROMPTS_SHA256
    prefix = registry.get('triage.system').text.split('Reasoning guidelines:')[0]
    assert hashlib.sha256(prefix.encode()).hexdigest() == CLASSIFICATION_SCHEMA_SHA256


@pytest.mark.parametrize('fields,memory', CASES)
@pytest.mark.asyncio
async def test_actual_sdk_receives_time_authorization_rules_and_original_facts(monkeypatch, fields, memory):
    state = make_state(fields, memory)
    requests, updates, invocation, tracker, result = await invoke_sdk(monkeypatch, state)
    assert len(requests) == len(result.llm_exchanges) == 1
    body, exchange = requests[0], result.llm_exchanges[0]
    messages = body['messages']
    assert len(messages) == 2 and [row['role'] for row in messages] == ['system', 'user']
    system, user = messages[0]['content'], messages[1]['content']
    assert system.startswith(default_registry().get('triage.system').text + '\n\n')
    for rule in (
        "Missing evidence is not a rule misfire. Use needs_review when the rule's",
        'condition cannot be checked; false_positive needs supplied contrary evidence.',
        'Use event_time for the activity, never created_at or receipt time.',
        'complete authorization start/end on one time base using explicit time zones',
        'and offsets, including across dates.',
        'Do not invent missing endpoints or time zones.',
        'Check authorization for this action, account and target.',
        'organisation habits and historical dispositions do not establish approval',
        'Missing matching jobs or approvals are evidence gaps, not proof that no',
        'maliciousness nor the absence of another authorization.',
        'Distinguish observed harm from authorization status.',
        'support true_positive while authorization remains unknown.',
        'authorization decision only when an applicable decision is supplied.',
        'Use needs_review when remaining gaps prevent judging threat.',
    ):
        assert rule in system
    start, end = user.index('<UNTRUSTED_DATA source="alert_telemetry">'), user.index('</UNTRUSTED_DATA>')
    for value in (fields['description'], fields['event_time'], fields['created_at']):
        assert state.raw_alert['description'] == fields['description']
        assert start < user.index(value) < end
    event_line = next(line for line in user.splitlines() if line.startswith('Event time (source'))
    assert fields['event_time'] in event_line and fields['created_at'] not in event_line
    if fields['event_time'].endswith('+08:00'):
        assert 'explicit UTC offset retained' in event_line
    elif fields['event_time'] == '2026-10-20T11:01:00':
        assert 'timezone not provided; not assumed UTC' in event_line
    assert 'title Administrator' in user and 'active in the directory' in user
    assert 'Recent analyst decisions read: status=no_match' in user
    if memory:
        assert memory in user and user.index(memory) < start
    assert exchange['prompt_truncated'] is False and json.loads(exchange['prompt']) == messages
    assert state_module._LLM_LITERAL_LIMIT == 8000 and len(exchange['prompt']) <= 8000
    canonical = contract.LLMInputContract.validate(messages)
    assert budget.PROMPT_BYTE_CAP == 16000
    assert len(json.dumps(canonical, ensure_ascii=False, separators=(',', ':')).encode()) <= 16000
    output_caps = [body[key] for key in ('max_tokens', 'max_completion_tokens') if key in body]
    assert output_caps and all(value == 512 for value in output_caps)
    assert body['response_format'] == {'type': 'json_object'}
    assert invocation.request_marked and invocation.response_seen and updates.await_count == 2
    assert updates.await_args.args[-1] == tracker.total_tokens == 18
    assert result.verdict == FIXTURE_ANSWER['verdict'] and result.confidence == FIXTURE_ANSWER['confidence']
    assert budget.current_invocation() is None
