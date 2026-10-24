"""Write-only ASGI boundary; actual coordinator cases separate from fake envelopes."""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import ssl
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.program_start_api import (create_app,ControlledManualTargetPolicy,MAX_BODY_BYTES,
    TOKEN_ENV,DSN_ENV,CA_ENV,READ_TOKEN_ENV)
from app.investigation_v2.program_start_coordinator import ProgramManualStartCoordinator,OUTCOME_SCHEMA
from app.investigation_v2.program_start_store import RECEIPT_SCHEMA
from app.investigation_v2.program_recon_publication_store import ProgramReconPublicationStore,REPORT_KIND
from app.investigation_v2.program_result_reader import CompatibleOwnedReconResultReader
from app.investigation_v2.execution_store import ExecutionPersistenceError,canonical_json
from app.investigation_v2.execution_state import ExecutionRejected
import test_program_start_coordinator_contract as c
from test_program_start_api_config import WRITE_TOKEN,TOOL_TOKEN,READ_TOKEN,environment,policy_doc

TENANT,ALERT,ACTOR=c.a.e.TENANT,c.a.e.ALERT,c.a.ACTOR
PATH='/internal/investigation-v2/alerts/'+str(ALERT)+'/start'
READ_PATH=PATH.removesuffix('start')+'operation-read'

def body():
    intent=c.a.start_intent()
    return {'operation_key':intent['request']['operation_key'],'window':intent['request']['window'],'request_version':intent['request']['request_version']}

def fake_outcome(intent,read_only=False):
    fresh=not read_only
    receipt=dict(schema=RECEIPT_SCHEMA,tenant_id=intent['request']['tenant_id'],run_id=intent['run_id'],executor_id=intent['executor_id'],
        intent_ref=intent['intent_ref'],request_hash=intent['request_hash'],fresh=fresh,may_enter_runtime=fresh,
        persistence_status='committed',external_call_authorized=False)
    owned=dict(schema='owned_program_recon_result.v1',tenant_id=intent['request']['tenant_id'],run_id=intent['run_id'],profile='alert_recon',
        target=intent['request']['target'],objective=intent['request']['objective'],notification=None,publication_state='not_published')
    return dict(schema=OUTCOME_SCHEMA,mode='read_only' if read_only else 'coordinated',admission=receipt,external_call_authorized=False,
        runtime=dict(entered_by_this_invocation=fresh,status=None if read_only else 'in_progress_or_interrupted',
                     http_attempted_by_this_invocation=False,publication_attempted_by_this_invocation=False),result=owned)

class StartAPIBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.response=None
        async def start(**kwargs):return deepcopy(self.response) if self.response is not None else fake_outcome(kwargs['intent'])
        async def read(**kwargs):return deepcopy(self.response) if self.response is not None else fake_outcome(kwargs['intent'],True)
        self.coordinator=SimpleNamespace(start=AsyncMock(side_effect=start),read_operation=AsyncMock(side_effect=read),close=AsyncMock())
        self.app=create_app(coordinator=self.coordinator,start_token=WRITE_TOKEN,budget_policy=c.a.policy())
        self.headers={'Authorization':'Bearer '+WRITE_TOKEN,'X-AiSOC-Tenant-ID':str(TENANT),'X-AiSOC-Actor-ID':str(ACTOR)}
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='http://isolated-start')
        self.addAsyncCleanup(self.client.aclose)

    async def send(self, *, path=PATH, headers=None, value=None):
        return await self.client.post(path,headers=self.headers if headers is None else headers,json=body() if value is None else value)

    async def test_server_normalizes_current_gateway_identity_budget_and_only_selected_method(self):
        response=await self.send();self.assertEqual(response.status_code,200)
        kwargs=self.coordinator.start.await_args.kwargs
        intent=kwargs['intent']
        self.assertEqual(intent['request']['tenant_id'],str(TENANT));self.assertEqual(intent['request']['actor_id'],str(ACTOR))
        self.assertEqual(intent['request']['budget_policy'],c.a.policy().descriptor)
        self.assertEqual((intent['request']['profile'],intent['request']['trigger']),('alert_recon','manual'))
        self.assertEqual(kwargs['current_principal'].tenant_ids,frozenset({TENANT}));self.assertTrue(kwargs['current_principal'].delegated)
        self.assertEqual(kwargs['current_principal'].subject,'verified-api-starter:'+str(ACTOR))
        self.coordinator.read_operation.assert_not_awaited()
        self.assertEqual((await self.send(path=READ_PATH)).status_code,200)
        self.assertEqual(self.coordinator.start.await_count,1);self.assertEqual(self.coordinator.read_operation.await_count,1)

    async def test_missing_wrong_basic_read_credentials_and_duplicate_auth_never_dispatch(self):
        for auth in (None,'Bearer wrong','Basic '+WRITE_TOKEN,'Bearer '+READ_TOKEN):
            headers=dict(self.headers)
            if auth is None:headers.pop('Authorization')
            else:headers['Authorization']=auth
            self.assertEqual((await self.send(headers=headers)).status_code,401)
        duplicated=[*self.headers.items(),('Authorization','Bearer '+WRITE_TOKEN)]
        self.assertEqual((await self.send(headers=duplicated)).status_code,401)
        self.coordinator.start.assert_not_awaited()

    async def test_token_rotation_and_disabled_token_are_checked_per_request(self):
        self.assertEqual((await self.send()).status_code,200)
        self.app.state.start_token='test-only-rotated-write-credential-not-live'
        self.assertEqual((await self.send()).status_code,401)
        self.app.state.start_token=None;self.assertEqual((await self.send()).status_code,401)
        self.assertEqual(self.coordinator.start.await_count,1)

    async def test_authentication_is_before_body_consumption_or_path_validation(self):
        consumed=[]
        async def never():consumed.append(True);raise AssertionError('must not read');yield b''
        response=await self.client.post(PATH,headers={},content=never())
        self.assertEqual(response.status_code,401);self.assertEqual(consumed,[])
        self.assertEqual((await self.send(path=PATH.replace(str(ALERT),'invalid'),headers={})).status_code,401)
        self.coordinator.start.assert_not_awaited()

    async def test_missing_bad_nil_or_duplicate_gateway_identity_refused(self):
        for key in ('X-AiSOC-Tenant-ID','X-AiSOC-Actor-ID'):
            for value in (None,'bad',str(UUID(int=0))):
                headers=dict(self.headers)
                if value is None:headers.pop(key)
                else:headers[key]=value
                self.assertEqual((await self.send(headers=headers)).status_code,400)
            self.assertEqual((await self.send(headers=[*self.headers.items(),(key,str(ACTOR))])).status_code,400)
        self.coordinator.start.assert_not_awaited()

    async def test_query_nil_and_invalid_alert_path_refused(self):
        for path,status in ((PATH+'?owner=all',400),(PATH.replace(str(ALERT),str(UUID(int=0))),400),(PATH.replace(str(ALERT),'bad'),422)):
            self.assertEqual((await self.send(path=path)).status_code,status)
        self.coordinator.start.assert_not_awaited()

    async def test_forbidden_control_keys_and_nested_extra_keys_never_dispatch(self):
        for key in ('owner','run_id','budget','profile','trigger','target','intent','policy_ref','permission','tool'):
            self.assertEqual((await self.send(value={**body(),key:'PRIVATE_INPUT'})).status_code,422)
        value=body();value['window']['extra']=True
        self.assertEqual((await self.send(value=value)).status_code,422);self.coordinator.start.assert_not_awaited()

    async def test_body_types_and_windows_are_strict_and_errors_do_not_echo_input(self):
        values=[{},[],{**body(),'operation_key':True},{**body(),'operation_key':str(UUID(int=0))},
                {**body(),'request_version':'PRIVATE_WRONG_VERSION'}]
        for window in ({'start':'2026-10-23T10:00:00','end':'2026-10-23T10:05:00'},
                       {'start':'2026-10-23T10:00:00Z','end':'2026-10-23T10:06:00Z'},
                       {'start':'2026-10-23T10:00:00Z','end':'2026-10-23T10:00:00Z'}):values.append({**body(),'window':window})
        for value in values:
            r=await self.send(value=value);self.assertEqual(r.status_code,422);self.assertNotIn('PRIVATE',r.text)
        self.coordinator.start.assert_not_awaited()

    async def test_duplicate_JSON_keys_malformed_UTF8_and_nonobject_bodies_refused(self):
        valid=json.dumps(body()).encode()
        for raw in (b'not json',b'\xff',b'[]',b'null',b'{"operation_key":"x","operation_key":"x"}',
                    valid.replace(b'"window": {',b'"window": {"start":"duplicate",',1)):
            r=await self.client.post(PATH,headers=self.headers,content=raw)
            self.assertEqual(r.status_code,422)
        self.coordinator.start.assert_not_awaited()

    async def test_exact_4KiB_body_accepts_and_next_byte_refuses_before_parse(self):
        raw=json.dumps(body()).encode();raw+=b' '*(MAX_BODY_BYTES-len(raw))
        self.assertEqual((await self.client.post(PATH,headers=self.headers,content=raw)).status_code,200)
        self.assertEqual((await self.client.post(PATH,headers=self.headers,content=raw+b' ')).status_code,413)
        self.assertEqual(self.coordinator.start.await_count,1)

    async def test_stream_stops_at_limit_without_consuming_extra_chunk(self):
        emitted=[]
        async def stream():
            for i in range(3):emitted.append(i);yield b'x'*(MAX_BODY_BYTES//2+1)
        r=await self.client.post(PATH,headers=self.headers,content=stream())
        self.assertEqual(r.status_code,413);self.assertEqual(emitted,[0,1]);self.coordinator.start.assert_not_awaited()

    async def test_both_POST_contract_refusals_including_missing_operation_are_409(self):
        for method,path in ((self.coordinator.start,PATH),(self.coordinator.read_operation,READ_PATH)):
            for error in (ExecutionRejected('owned admitted Run not found'),ExecutionRejected('PRIVATE_INTEGRITY')):
                method.side_effect=error;r=await self.send(path=path)
                self.assertEqual(r.status_code,409);self.assertNotIn('PRIVATE',r.text)

    async def test_persistence_and_unexpected_errors_are_sanitized_503(self):
        for error in (ExecutionPersistenceError('PRIVATE_DSN'),RuntimeError('PRIVATE_CREDENTIAL')):
            self.coordinator.start.side_effect=error;r=await self.send()
            self.assertEqual(r.status_code,503);self.assertNotIn('PRIVATE',r.text)

    async def test_bad_envelope_identity_schema_and_flags_are_502_without_payload_leak(self):
        await self.send();original=fake_outcome(self.coordinator.start.await_args.kwargs['intent'])
        for mutate in (lambda p:p.update(schema='future.v1'),lambda p:p.update(extra='PRIVATE'),
                       lambda p:p['admission'].update(run_id=str(UUID(int=99))),lambda p:p['admission'].update(fresh=1),
                       lambda p:p['runtime'].update(entered_by_this_invocation=1),lambda p:p['result'].update(tenant_id=str(UUID(int=99))),
                       lambda p:p['result'].update(schema='owned_fixed_recon_result.v1'),lambda p:p['result'].update(target={'type':'case','id':str(ALERT)}),
                       lambda p:p['result'].update(publication_state=[]),lambda p:p.update(external_call_authorized=True)):
            self.response=deepcopy(original);mutate(self.response);r=await self.send()
            self.assertEqual(r.status_code,502);self.assertNotIn('PRIVATE',r.text)

    async def test_operation_read_cannot_return_coordinated_or_execution_flags(self):
        await self.send();self.response=fake_outcome(self.coordinator.start.await_args.kwargs['intent'])
        self.assertEqual((await self.send(path=READ_PATH)).status_code,502)

    async def test_unready_and_only_two_write_routes_no_docs_or_legacy(self):
        self.app.state.coordinator=None;self.assertEqual((await self.send()).status_code,503)
        for path in ('/docs','/openapi.json','/api/v1/investigate','/internal/investigation-v2/runs/'+str(UUID(int=1))):
            self.assertEqual((await self.client.get(path)).status_code,404)
        self.assertEqual((await self.client.get(PATH)).status_code,405);self.coordinator.start.assert_not_awaited()

    async def test_injected_coordinator_is_not_closed_or_connected(self):
        with patch('asyncpg.create_pool',new=AsyncMock(side_effect=AssertionError('no pool'))) as pool:
            async with self.app.router.lifespan_context(self.app):self.assertIs(self.app.state.coordinator,self.coordinator)
        pool.assert_not_awaited();self.coordinator.close.assert_not_awaited()

class StartAPIOwnedConfigTests(unittest.IsolatedAsyncioTestCase):
    async def test_pool_TLS_explicit_parameters_and_owned_cleanup(self):
        pool=SimpleNamespace(close=AsyncMock(),terminate=Mock())
        with patch.dict(os.environ,environment(),clear=True),patch('asyncpg.create_pool',new=AsyncMock(return_value=pool)) as created:
            app=create_app()
            async with app.router.lifespan_context(app):
                self.assertIsInstance(app.state.coordinator,ProgramManualStartCoordinator)
        kwargs=created.await_args.kwargs
        self.assertEqual((kwargs['min_size'],kwargs['max_size'],kwargs['timeout'],kwargs['command_timeout']),(1,2,10,10))
        self.assertEqual(kwargs['ssl'].verify_mode,ssl.CERT_REQUIRED);self.assertTrue(kwargs['ssl'].check_hostname)
        pool.close.assert_awaited_once();pool.terminate.assert_not_called();self.assertIsNone(app.state.coordinator)

    async def test_pool_startup_and_CA_errors_are_sanitized(self):
        with patch.dict(os.environ,environment(),clear=True),patch('asyncpg.create_pool',new=AsyncMock(side_effect=RuntimeError('PRIVATE_DSN'))):
            app=create_app()
            with self.assertRaises(RuntimeError) as error:
                async with app.router.lifespan_context(app):pass
            self.assertNotIn('PRIVATE',str(error.exception))
        env=environment();env[CA_ENV]='PRIVATE_MISSING_CA'
        with patch.dict(os.environ,env,clear=True),patch('asyncpg.create_pool',new=AsyncMock()) as created:
            app=create_app()
            with self.assertRaises(RuntimeError) as error:
                async with app.router.lifespan_context(app):pass
            self.assertNotIn('PRIVATE',str(error.exception));created.assert_not_awaited()

    async def test_pool_close_timeout_is_real_cancel_and_terminate_once(self):
        cancelled=[]
        async def close():
            try:await asyncio.Future()
            finally:cancelled.append(True)
        pool=SimpleNamespace(close=AsyncMock(side_effect=close),terminate=Mock());real_wait=asyncio.wait_for;limits=[]
        async def bounded(coro,timeout):limits.append(timeout);return await real_wait(coro,timeout=0.001)
        with patch.dict(os.environ,environment(),clear=True),patch('asyncpg.create_pool',new=AsyncMock(return_value=pool)), \
             patch('app.investigation_v2.program_start_api.asyncio.wait_for',new=bounded):
            app=create_app()
            async with app.router.lifespan_context(app):pass
        self.assertEqual(limits,[5]);self.assertEqual(cancelled,[True]);pool.terminate.assert_called_once()
        self.assertIsNone(app.state.coordinator)

    async def test_owned_close_failure_clears_coordinator_and_sanitizes_error(self):
        pool=SimpleNamespace(close=AsyncMock(side_effect=RuntimeError('PRIVATE_DRIVER')),terminate=Mock())
        with patch.dict(os.environ,environment(),clear=True),patch('asyncpg.create_pool',new=AsyncMock(return_value=pool)):
            app=create_app()
            with self.assertRaises(RuntimeError) as error:
                async with app.router.lifespan_context(app):pass
        self.assertNotIn('PRIVATE',str(error.exception));self.assertIsNone(app.state.coordinator);pool.terminate.assert_called_once()

    async def test_factory_refuses_old_defaults_reused_read_token_and_missing_injected_budget(self):
        with patch.dict(os.environ,{'AISOC_SERVICE_TOKEN':WRITE_TOKEN,'DATABASE_URL':'PRIVATE'},clear=True):
            with self.assertRaises(ValueError):create_app()
        fake=SimpleNamespace(start=AsyncMock(),read_operation=AsyncMock())
        with self.assertRaises(ValueError):create_app(coordinator=fake,start_token=WRITE_TOKEN)
        with patch.dict(os.environ,{READ_TOKEN_ENV:WRITE_TOKEN},clear=True),self.assertRaises(ValueError):
            create_app(coordinator=fake,start_token=WRITE_TOKEN,budget_policy=c.a.policy())

class StartAPIActualCoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fixture=c.ProgramStartCoordinatorTests();await self.fixture.asyncSetUp();self.db=self.fixture.db
        guard=ControlledManualTargetPolicy.from_document(policy_doc())
        self.coordinator=self.fixture.make(target_guard=guard,target_policy_ref=guard.policy_ref)
        self.app=create_app(coordinator=self.coordinator,start_token=WRITE_TOKEN,budget_policy=self.fixture.fixture.policy)
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='http://actual-coordinator-ASGI')
        self.addAsyncCleanup(self.client.aclose)
        self.headers={'Authorization':'Bearer '+WRITE_TOKEN,'X-AiSOC-Tenant-ID':str(TENANT),'X-AiSOC-Actor-ID':str(ACTOR)}

    async def send(self,path=PATH,headers=None,value=None):
        return await self.client.post(path,headers=self.headers if headers is None else headers,json=body() if value is None else value)

    async def test_actual_start_repeat_and_read_preserve_full_DTO_rows_and_one_mock_query(self):
        first=await self.send();self.assertEqual(first.status_code,200)
        self.assertEqual((len(self.db.events),len(self.db.artifacts),len(self.fixture.calls)),(7,15,1))
        before=self.db.snapshot();repeat=await self.send();read=await self.send(READ_PATH)
        self.assertEqual(repeat.status_code,200);self.assertEqual(read.status_code,200)
        self.assertEqual(canonical_json(first.json()['result']),canonical_json(read.json()['result']))
        self.assertEqual(repeat.json(),read.json());self.assertEqual(self.db.snapshot(),before);self.assertEqual(len(self.fixture.calls),1)

    async def test_current_concrete_target_refusal_is_zero_SQL_and_missing_operation409(self):
        other=PATH.replace(str(ALERT),str(UUID(int=99)))
        self.assertEqual((await self.send(other)).status_code,409);self.assertEqual(self.db.trace,[])
        self.assertEqual((await self.send(READ_PATH)).status_code,409);self.assertEqual(self.db.snapshot(),({},[],{}))
        self.assertEqual(self.fixture.calls,[])

    async def test_server_budget_zero_yields_partial_without_tool_HTTP(self):
        self.fixture.fixture.policy=c.a.policy(max_tool_calls=0)
        admission=c.ProgramAlertStartStore(self.db,budget_policy=self.fixture.fixture.policy)
        guard=ControlledManualTargetPolicy.from_document(policy_doc())
        self.coordinator=self.fixture.make(admission_store=admission,target_guard=guard,target_policy_ref=guard.policy_ref)
        app=create_app(coordinator=self.coordinator,start_token=WRITE_TOKEN,budget_policy=self.fixture.fixture.policy)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://zero') as client:
            r=await client.post(PATH,headers=self.headers,json=body())
        self.assertEqual(r.status_code,200);self.assertEqual(r.json()['result']['execution_snapshot']['scope_readiness'],'partial')
        self.assertEqual(self.fixture.calls,[])

    async def test_actual_admission_ACK503_then_read_only_recovery_no_runtime(self):
        self.db.fail_after_commit=True;r=await self.send()
        self.assertEqual(r.status_code,503);self.assertEqual((len(self.db.events),len(self.db.artifacts)),(2,3))
        before=self.db.snapshot();read=await self.send(READ_PATH);repeat=await self.send()
        self.assertEqual(read.status_code,200);self.assertEqual(read.json(),repeat.json())
        self.assertEqual(read.json()['mode'],'read_only');self.assertEqual(self.fixture.calls,[]);self.assertEqual(self.db.snapshot(),before)

    async def test_actual_publication_ACK503_then_read_original_published_without_replay(self):
        original=ProgramReconPublicationStore.publish
        async def uncertain(store,request):self.db.fail_after_commit=True;return await original(store,request)
        with patch.object(ProgramReconPublicationStore,'publish',new=uncertain):self.assertEqual((await self.send()).status_code,503)
        before=self.db.snapshot();r=await self.send(READ_PATH)
        self.assertEqual(r.status_code,200);self.assertEqual(r.json()['result']['publication_state'],'published')
        self.assertIsNone(r.json()['result']['notification']);self.assertEqual(self.db.snapshot(),before);self.assertEqual(len(self.fixture.calls),1)

    async def test_actual_cancelled_request_propagates_and_read_does_not_replay(self):
        arrived=asyncio.Event()
        async def wait(request):arrived.set();await asyncio.Future()
        self.fixture.handler=wait;task=asyncio.create_task(self.send());await asyncio.wait_for(arrived.wait(),2);task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        before=self.db.snapshot();r=await self.send(READ_PATH)
        self.assertEqual(r.status_code,200);self.assertEqual(r.json()['mode'],'read_only')
        self.assertEqual(self.db.snapshot(),before);self.assertEqual(len(self.fixture.calls),1)

    async def test_rotated_write_token_cannot_be_the_current_configured_read_token(self):
        self.app.state.start_token=READ_TOKEN
        with patch.dict(os.environ,{READ_TOKEN_ENV:READ_TOKEN}):
            r=await self.send(headers={**self.headers,'Authorization':'Bearer '+READ_TOKEN})
        self.assertEqual(r.status_code,401);self.assertEqual(self.db.trace,[]);self.assertEqual(self.fixture.calls,[])

    async def test_rotated_write_token_cannot_be_the_current_actual_tool_token(self):
        tool_token=self.coordinator._token;self.app.state.start_token=tool_token
        r=await self.send(headers={**self.headers,'Authorization':'Bearer '+tool_token})
        self.assertEqual(r.status_code,401);self.assertEqual(self.db.trace,[]);self.assertEqual(self.fixture.calls,[])

if __name__=='__main__':unittest.main()
