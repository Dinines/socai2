"""Actual coordinator/admission/runtime/publication; SQL and HTTP doubled."""
import asyncio
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID

import httpx
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.program_start_coordinator import ProgramManualStartCoordinator, ELIGIBILITY_SCHEMA
from app.investigation_v2.program_start_store import AdmittedProgramOperation, ProgramAlertStartStore, ARTIFACT_KIND
from app.investigation_v2.program_recon_runtime import ProgramReconRuntime
from app.investigation_v2.program_recon_publication_store import ProgramReconPublicationStore, REPORT_KIND, PUBLICATION_EVENT
from app.investigation_v2.program_result_reader import CompatibleOwnedReconResultReader
from app.investigation_v2.program_runtime_store import HANDOFF_KIND
from app.investigation_v2.execution_store import ExecutionPersistenceError, canonical_json
from app.investigation_v2.execution_state import ExecutionRejected
import test_program_start_store_contract as a

POLICY = "test-only-controlled-targets.v1"
TOKEN = "test-only-coordinator-tool-token-not-live"
API = "https://test-only-coordinator.invalid"


class Guard:
    """Server eligibility double; not proof that a legacy writer is stopped."""
    def __init__(self): self.calls=[];self.override=None;self.error=None;self.wait=None
    async def assess(self, **kwargs):
        self.calls.append(kwargs)
        if self.wait: await self.wait()
        if self.error: raise self.error
        result=dict(schema=ELIGIBILITY_SCHEMA,policy_ref=kwargs['policy_ref'],tenant_id=str(kwargs['tenant_id']),
            actor_id=str(kwargs['actor_id']),target={'type':'alert','id':str(kwargs['alert_id'])},eligible=True,reason='test-only-policy-accepts')
        return {**result,**self.override} if self.override is not None else result


class ProgramStartCoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fixture=a.ProgramStartStoreTests();await self.fixture.asyncSetUp()
        self.db,self.admission=self.fixture.db,self.fixture.store
        self.guard=Guard();self.calls=[];self.handler=None;self.payload=None
        self.reader=CompatibleOwnedReconResultReader(self.db)
        async def handle(request):
            self.calls.append(request)
            if self.handler:return await self.handler(request)
            payload=deepcopy(self.payload) if self.payload is not None else a.e.query()
            payload['caller_receipt']['run_id']=self.fixture.intent['run_id']
            return httpx.Response(200,json=payload)
        self.transport=httpx.MockTransport(handle)
        self.coordinator=self.make()

    def make(self, **changes):
        return ProgramManualStartCoordinator(**{**dict(admission_store=self.admission,reader=self.reader,target_guard=self.guard,
            target_policy_ref=POLICY,api_url=API,service_token=TOKEN,transport=self.transport),**changes})

    async def start(self, **changes):
        return await self.coordinator.start(**{**dict(intent=self.fixture.intent,current_principal=a.current(),current_actor_id=a.ACTOR),**changes})

    async def read(self, **changes):
        return await self.coordinator.read_operation(**{**dict(intent=self.fixture.intent,current_principal=a.current(),current_actor_id=a.ACTOR),**changes})

    def assert_no_credentials(self):
        body=canonical_json({'events':self.db.events,'artifacts':list(self.db.artifacts.values())},max_bytes=8000000)
        self.assertNotIn(TOKEN,body);self.assertNotIn(API,body)

    async def test_fresh_normal_runs_once_publishes_and_returns_owned_same_version(self):
        with patch.object(ProgramReconRuntime,'begin',new=AsyncMock(side_effect=AssertionError('no second begin'))) as begin:
            result=await self.start()
        self.assertEqual(result['mode'],'coordinated');self.assertTrue(result['runtime']['entered_by_this_invocation'])
        self.assertTrue(result['runtime']['publication_attempted_by_this_invocation']);self.assertFalse(result['external_call_authorized'])
        self.assertEqual(result['result']['schema'],'owned_program_recon_result.v1')
        self.assertEqual(result['result']['execution_snapshot']['scope_readiness'],'ready')
        self.assertEqual((len(self.db.events),len(self.db.artifacts),len(self.calls)),(7,15,1));begin.assert_not_awaited()
        expected=await self.reader.read(current_principal=a.current(),tenant_id=a.e.TENANT,run_id=UUID(self.fixture.intent['run_id']))
        self.assertEqual(canonical_json(result['result']),canonical_json(expected));self.assert_no_credentials()

    async def test_repeat_and_cold_read_do_not_execute_begin_or_publish(self):
        first=await self.start();before=self.db.snapshot()
        with patch.object(ProgramReconRuntime,'execute',new=AsyncMock(side_effect=AssertionError('no execute'))) as execute, \
             patch.object(ProgramReconPublicationStore,'publish',new=AsyncMock(side_effect=AssertionError('no publication'))) as publish:
            second=await self.start();third=await self.make().read_operation(intent=self.fixture.intent,current_principal=a.current(),current_actor_id=a.ACTOR)
        self.assertEqual(second['mode'],'read_only');self.assertEqual(second,third)
        self.assertEqual(first['result'],second['result']);self.assertEqual(self.db.snapshot(),before)
        execute.assert_not_awaited();publish.assert_not_awaited();self.assertEqual(len(self.calls),1)
        self.assertEqual(len(self.guard.calls),3)

    async def test_existing_active_operation_is_read_only_without_owner_takeover(self):
        admitted=await self.fixture.admit();store=self.fixture.runtime_store(admitted);await store.claim(admitted.request)
        before=self.db.snapshot()
        with patch.object(ProgramReconRuntime,'execute',new=AsyncMock(side_effect=AssertionError('no takeover'))):result=await self.start()
        self.assertEqual(result['result']['progress']['phase'],'claimed');self.assertEqual(result['mode'],'read_only')
        self.assertEqual(self.db.snapshot(),before);self.assertEqual(self.calls,[])

    async def test_stopped_unpublished_repeat_does_not_repair_publication(self):
        admitted=await self.fixture.admit();await self.fixture.execute(admitted);before=self.db.snapshot()
        with patch.object(ProgramReconPublicationStore,'publish',new=AsyncMock(side_effect=AssertionError('no repeat publication'))):
            start=await self.start();read=await self.read()
        self.assertEqual(start,read);self.assertEqual(start['result']['publication_state'],'not_published')
        self.assertIsNotNone(start['result']['candidate']);self.assertIsNone(start['result']['markdown'])
        self.assertEqual(self.db.snapshot(),before);self.assertEqual(self.calls,[])

    async def test_parallel_start_has_one_tool_request_and_duplicate_never_seals_owner(self):
        began,release=asyncio.Event(),asyncio.Event()
        async def block(request):
            began.set();await release.wait();payload=a.e.query();payload['caller_receipt']['run_id']=self.fixture.intent['run_id']
            return httpx.Response(200,json=payload)
        self.handler=block;owner=asyncio.create_task(self.start());await asyncio.wait_for(began.wait(),2)
        try:
            duplicate=await self.start()
            self.assertEqual(duplicate['mode'],'read_only');self.assertEqual(duplicate['result']['progress']['phase'],'claimed')
            self.assertEqual(len(self.calls),1)
        finally:release.set()
        result=await owner;self.assertEqual(result['result']['publication_state'],'published')
        self.assertEqual((len(self.db.events),len(self.db.artifacts),len(self.calls)),(7,15,1))

    async def test_guard_refusal_unknown_bad_identity_policy_or_extra_fields_never_admit(self):
        for change in ({'eligible':False},{'eligible':None},{'eligible':1},{'schema':'future.v1'},
                       {'policy_ref':'other.v1'},{'tenant_id':str(UUID(int=99))},{'actor_id':str(UUID(int=99))},
                       {'target':{'type':'alert','id':str(UUID(int=99))}},{'reason':None},{'extra':True}):
            self.guard.override=change
            with self.subTest(change=change),self.assertRaises(ExecutionRejected):await self.start()
        self.assertEqual(self.db.trace,[]);self.assertEqual(self.calls,[])

    async def test_guard_failure_is_sanitized_without_admission_or_http(self):
        self.guard.error=RuntimeError('PRIVATE_ELIGIBILITY_DSN')
        with self.assertRaises(ExecutionPersistenceError) as error:await self.start()
        self.assertNotIn('PRIVATE',str(error.exception));self.assertEqual(self.db.trace,[]);self.assertEqual(self.calls,[])

    async def test_current_policy_is_rechecked_for_start_and_read_of_existing_result(self):
        await self.start();before=self.db.snapshot();self.guard.override={'eligible':False}
        for call in (self.start,self.read):
            with self.assertRaises(ExecutionRejected):await call()
        self.assertEqual(self.db.snapshot(),before);self.assertEqual(len(self.calls),1)

    async def test_invalid_current_actor_and_intent_refused_before_guard_or_SQL(self):
        for change in ({'current_actor_id':UUID(int=99)},{'intent':{}},{'current_principal':a.TenantPrincipal()}):
            with self.assertRaises(ExecutionRejected):await self.start(**change)
        self.assertEqual(self.guard.calls,[]);self.assertEqual(self.db.trace,[])

    async def test_detached_intent_cannot_be_changed_while_guard_awaits(self):
        arrived,release=asyncio.Event(),asyncio.Event()
        async def pause():arrived.set();await release.wait()
        self.guard.wait=pause;original=deepcopy(self.fixture.intent)
        task=asyncio.create_task(self.start());await asyncio.wait_for(arrived.wait(),2)
        self.fixture.intent['request']['target']['id']=str(UUID(int=99));release.set()
        result=await task
        self.assertEqual(result['result']['target'],original['request']['target'])
        self.assertEqual(self.guard.calls[0]['alert_id'],UUID(original['request']['target']['id']))

    async def test_zero_tool_budget_stops_partial_without_http(self):
        self.fixture.policy=a.policy(max_tool_calls=0);self.fixture.intent=self.fixture.changed_intent(budget_policy=self.fixture.policy)
        self.admission=ProgramAlertStartStore(self.db,budget_policy=self.fixture.policy);self.coordinator=self.make()
        result=await self.start()
        self.assertEqual(result['result']['execution_snapshot']['scope_readiness'],'partial')
        self.assertEqual(result['result']['execution_snapshot']['stop_reason'],'budget_limit')
        self.assertEqual(result['result']['publication_state'],'published');self.assertEqual(self.calls,[])

    async def test_empty_error_and_unknown_results_never_claim_ready(self):
        for mode in ('empty','error','unknown'):
            await self.asyncSetUp()
            if mode=='unknown':
                async def timeout(request):raise httpx.ReadTimeout('test-only-unknown')
                self.handler=timeout
            else:self.payload=a.e.query(status=mode)
            result=await self.start()
            with self.subTest(mode=mode):
                self.assertEqual(result['result']['execution_snapshot']['scope_readiness'],'partial')
                self.assertEqual(len(self.calls),1)
                before=self.db.snapshot();self.assertEqual((await self.read())['result'],result['result'])
                self.assertEqual(self.db.snapshot(),before)

    async def test_admission_each_write_failure_and_unknown_ACK_never_dispatch(self):
        for kind in ('run','unified_step_input','unified_state_snapshot',ARTIFACT_KIND):
            self.db.fail_kind=kind
            with self.subTest(kind=kind),self.assertRaises(ExecutionPersistenceError):await self.start()
            self.assertEqual(self.db.snapshot(),({},[],{}));self.assertEqual(self.calls,[])
        self.db.fail_kind=None;self.db.fail_after_commit=True
        with self.assertRaises(ExecutionPersistenceError):await self.start()
        self.assertEqual((len(self.db.events),len(self.db.artifacts)),(2,3));self.assertEqual(self.calls,[])
        result=await self.read();self.assertEqual(result['result']['progress']['phase'],'ready')
        self.assertFalse(result['runtime']['entered_by_this_invocation'])

    async def test_runtime_exception_preserves_admission_and_is_not_replayed(self):
        with patch.object(ProgramReconRuntime,'execute',new=AsyncMock(side_effect=ExecutionPersistenceError('PRIVATE_RUNTIME_TOKEN'))):
            with self.assertRaises(ExecutionPersistenceError) as error:await self.start()
        self.assertNotIn('PRIVATE',str(error.exception));before=self.db.snapshot()
        read=await self.read();repeat=await self.start()
        self.assertEqual(read,repeat);self.assertEqual(self.db.snapshot(),before);self.assertEqual(self.calls,[])

    async def test_unconfirmed_runtime_stop_cannot_publish(self):
        fake=dict(status='stopped',http_attempted_by_this_invocation=False,handoff={'retention':'not_confirmed'})
        with patch.object(ProgramReconRuntime,'execute',new=AsyncMock(return_value=fake)), \
             patch.object(ProgramReconPublicationStore,'publish',new=AsyncMock(side_effect=AssertionError('no publish'))) as publish:
            with self.assertRaises(ExecutionRejected):await self.start()
        publish.assert_not_awaited();self.assertEqual((len(self.db.events),len(self.db.artifacts)),(2,3))

    async def test_publication_failure_keeps_stopped_candidate_and_repeat_does_not_publish(self):
        async def inject(request):
            self.db.fail_kind=REPORT_KIND;value=a.e.query();value['caller_receipt']['run_id']=self.fixture.intent['run_id']
            return httpx.Response(200,json=value)
        self.handler=inject
        with self.assertRaises(ExecutionPersistenceError):await self.start()
        self.assertEqual((len(self.db.events),len(self.db.artifacts)),(6,11));before=self.db.snapshot()
        read=await self.start();self.assertEqual(read['mode'],'read_only');self.assertEqual(read['result']['publication_state'],'not_published')
        self.assertEqual(self.db.snapshot(),before);self.assertEqual(len(self.calls),1)

    async def test_publication_committed_but_ACK_unknown_recovers_by_read_without_notification(self):
        original=ProgramReconPublicationStore.publish
        async def uncertain(store,request):
            self.db.fail_after_commit=True
            return await original(store,request)
        with patch.object(ProgramReconPublicationStore,'publish',new=uncertain):
            with self.assertRaises(ExecutionPersistenceError):await self.start()
        self.assertEqual((len(self.db.events),len(self.db.artifacts)),(7,15));before=self.db.snapshot()
        result=await self.read();self.assertEqual(result['result']['publication_state'],'published')
        self.assertIsNone(result['result']['notification']);self.assertEqual(self.db.snapshot(),before);self.assertEqual(len(self.calls),1)

    async def test_handoff_retention_failure_never_publishes_or_restarts(self):
        self.db.fail_kind=HANDOFF_KIND
        with self.assertRaises(ExecutionPersistenceError):await self.start()
        before=self.db.snapshot();read=await self.start()
        self.assertEqual(read['mode'],'read_only');self.assertIsNone(read['result']['markdown'])
        self.assertFalse(any(e['kind']==PUBLICATION_EVENT for e in self.db.events))
        self.assertEqual(self.db.snapshot(),before);self.assertEqual(len(self.calls),1)

    async def test_owner_cancellation_propagates_without_publication_and_repeat_is_read_only(self):
        arrived=asyncio.Event()
        async def wait(request):arrived.set();await asyncio.Future()
        self.handler=wait;task=asyncio.create_task(self.start());await asyncio.wait_for(arrived.wait(),2);task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        before=self.db.snapshot();read=await self.read();repeat=await self.start()
        self.assertEqual(read,repeat);self.assertEqual(read['mode'],'read_only');self.assertEqual(self.db.snapshot(),before)
        self.assertFalse(any(e['kind']==PUBLICATION_EVENT for e in self.db.events));self.assertEqual(len(self.calls),1)

    async def test_cancelled_guard_never_admits_and_propagates(self):
        arrived=asyncio.Event()
        async def wait():arrived.set();await asyncio.Future()
        self.guard.wait=wait;task=asyncio.create_task(self.start());await asyncio.wait_for(arrived.wait(),2);task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertEqual(self.db.snapshot(),({},[],{}));self.assertEqual(self.calls,[])

    async def test_bad_admission_flags_or_identity_cannot_reach_runtime(self):
        admitted=await self.fixture.admit()
        for changes in ({'fresh':1},{'may_enter_runtime':False},{'external_call_authorized':True},
                        {'persistence_status':'unknown'},{'tenant_id':str(UUID(int=99))}):
            fake=AdmittedProgramOperation(admitted.request,{**admitted.receipt,**changes})
            with patch.object(self.admission,'admit',new=AsyncMock(return_value=fake)), \
                 patch.object(ProgramReconRuntime,'execute',new=AsyncMock(side_effect=AssertionError('no runtime'))) as execute:
                with self.subTest(changes=changes),self.assertRaises(ExecutionRejected):await self.start()
            execute.assert_not_awaited()
        self.assertEqual(self.calls,[])

    async def test_reader_wrong_identity_never_leaks_mismatched_result(self):
        await self.start();real=self.reader.read
        async def wrong(**kwargs):
            result=await real(**kwargs);result['tenant_id']=str(UUID(int=99));return result
        with patch.object(self.reader,'read',new=wrong):
            with self.assertRaises(ExecutionRejected):await self.read()
        self.assertEqual(len(self.calls),1)

    async def test_explicit_guard_backend_pair_and_controlled_tool_config_required(self):
        for changes in ({'target_guard':None},{'target_policy_ref':''},{'api_url':'file:///tmp/test'},
                        {'api_url':'http://user:secret@host'},{'api_url':'http://host?secret=bad'},
                        {'api_url':'http://bad host'}, {'api_url':' http://host'},
                        {'service_token':'short'},{'service_token':'密'*40},
                        {'reader':CompatibleOwnedReconResultReader(object())}):
            with self.subTest(changes=changes),self.assertRaises(ExecutionRejected):self.make(**changes)
        self.assertEqual(self.db.trace,[])


if __name__=='__main__':unittest.main()
