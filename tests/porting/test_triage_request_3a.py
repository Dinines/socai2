"""Real cached SDK and agent control flow; transports/models are substitutes."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import openai
import pytest
from langchain_core.messages import HumanMessage

from app.agents import auto_triage_agent as agent
from app.llm.factory import llm_override, make_chat_model
from app.workers.fused_alert_consumer import FusedAlertTriageWorker, build_state


@pytest.fixture(autouse=True)
def route(monkeypatch):
    monkeypatch.setenv('LLM_GATEWAY_URL', 'http://sdk-substitute.invalid/v1')
    monkeypatch.setenv('LITELLM_MASTER_KEY', 'synthetic-unit')
    monkeypatch.delenv('OPENAI_BASE_URL', raising=False)
    monkeypatch.delenv('LLM_BASE_URL', raising=False)


def test_production_triage_constructor_bounds_root_clients():
    model = make_chat_model('triage', max_tokens=512, json_output=True)
    assert model.max_retries == model.root_client.max_retries == model.root_async_client.max_retries == 0
    assert model.request_timeout == model.root_client.timeout == model.root_async_client.timeout == 45.0
    assert model.max_tokens == 512 and model.extra_body['max_tokens'] == 512


def test_byok_keeps_triage_bounds():
    with llm_override(api_key='synthetic-byok', base_url='http://byok.invalid/v1', model='bounded-byok'):
        model = make_chat_model('triage', max_tokens=512, json_output=True)
    assert model.model_name == 'bounded-byok' and str(model.root_async_client.base_url) == 'http://byok.invalid/v1/'
    assert model.root_async_client.max_retries == 0 and model.root_async_client.timeout == 45.0


@pytest.mark.parametrize('failure', ['500', 'timeout'])
@pytest.mark.asyncio
async def test_sdk_failure_issues_only_one_http_request(failure):
    requests = []
    async def transport(request):
        requests.append(request)
        if failure == 'timeout':
            raise httpx.ReadTimeout('unit transport timeout', request=request)
        return httpx.Response(500, json={'error': {'message': 'unit server failure', 'type': 'server_error'}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        model = make_chat_model('triage', max_tokens=512, json_output=True, http_async_client=client)
        with pytest.raises(openai.APITimeoutError if failure == 'timeout' else openai.InternalServerError):
            await model.ainvoke([HumanMessage(content='Bounded synthetic request')])
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_sdk_success_preserves_usage_and_output_cap():
    requests = []
    async def transport(request):
        import json
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            'id': 'unit-completion', 'object': 'chat.completion', 'created': 1, 'model': 'unit-observed',
            'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': '{"verdict":"needs_review"}'}, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 11, 'completion_tokens': 7, 'total_tokens': 18}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        model = make_chat_model('triage', max_tokens=512, json_output=True, http_async_client=client)
        result = await model.ainvoke([HumanMessage(content='Bounded synthetic request')])
    assert len(requests) == 1 and requests[0]['max_tokens'] == 512
    assert requests[0]['response_format'] == {'type': 'json_object'}
    assert result.usage_metadata['total_tokens'] == 18


@pytest.mark.asyncio
async def test_sdk_external_cancel_does_not_retry():
    entered = asyncio.Event()
    requests = []
    async def transport(request):
        requests.append(request)
        entered.set()
        await asyncio.Event().wait()
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        model = make_chat_model('triage', max_tokens=512, http_async_client=client)
        task = asyncio.create_task(model.ainvoke([HumanMessage(content='Bounded cancel')]))
        await asyncio.wait_for(entered.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert len(requests) == 1


def state():
    tenant = '11111111-1111-1111-1111-111111111111'
    alert = '22222222-2222-2222-2222-222222222222'
    return build_state({'id': alert, 'alert_row_id': alert, 'tenant_id': tenant,
                        'alert': {'id': alert, 'tenant_id': tenant, 'title': 'Bounded synthetic alert',
                                  'severity': 'high', 'risk_score': None}})


@pytest.mark.asyncio
async def test_whole_invocation_deadline_reaches_original_review_fallback(monkeypatch):
    cancelled = asyncio.Event()
    async def never(*args, **kwargs):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()
    monkeypatch.setattr(agent, 'TRIAGE_REQUEST_TIMEOUT_SECONDS', .01, raising=False)
    monkeypatch.setattr(agent, 'make_chat_model', lambda *a, **k: SimpleNamespace(model_name='unit'))
    invoke = AsyncMock(side_effect=never)
    monkeypatch.setattr(agent, 'safe_ainvoke', invoke)
    worker = FusedAlertTriageWorker(bootstrap_servers='unused')
    result, tier = await asyncio.wait_for(worker._llm_triage(state()), .5)
    assert tier == 'deterministic' and result.verdict == 'needs_review'
    assert invoke.await_count == 1 and cancelled.is_set()
    assert not result.llm_exchanges  # No response or fabricated usage on timeout.


@pytest.mark.asyncio
async def test_agent_external_cancel_propagates_without_fallback(monkeypatch):
    entered = asyncio.Event()
    async def never(*args, **kwargs):
        entered.set()
        await asyncio.Event().wait()
    monkeypatch.setattr(agent, 'make_chat_model', lambda *a, **k: SimpleNamespace(model_name='unit'))
    invoke = AsyncMock(side_effect=never)
    monkeypatch.setattr(agent, 'safe_ainvoke', invoke)
    worker = FusedAlertTriageWorker(bootstrap_servers='unused')
    task = asyncio.create_task(worker._llm_triage(state()))
    await asyncio.wait_for(entered.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert invoke.await_count == 1
