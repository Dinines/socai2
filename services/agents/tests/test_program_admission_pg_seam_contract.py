"""PG probe adapters/configuration only; these tests never connect to PG."""
import asyncio
from contextlib import asynccontextmanager
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock,patch
from uuid import UUID

ROOT=Path(__file__).resolve().parents[3]
PROBE=ROOT/'openspec/changes/continue-isolated-investigation-v2/probes/program_admission_pg_seam.py'
spec=importlib.util.spec_from_file_location('program_admission_pg_seam',PROBE)
seam=importlib.util.module_from_spec(spec);spec.loader.exec_module(seam)


class Connection:
    def __init__(self):self.commits=0;self.rollbacks=0;self.fetches=0;self.rows=[];self.closed=False;self.terminated=False
    def get_server_pid(self):return 321
    @asynccontextmanager
    async def transaction(self,**kwargs):
        try:yield self
        except BaseException:self.rollbacks+=1;raise
        else:self.commits+=1
    async def fetchrow(self,*args):return {'runs':1,'events':2,'artifacts':3}
    async def fetchval(self,*args):self.fetches+=1;return UUID(int=4)
    async def fetch(self,*args):return self.rows
    async def close(self):self.closed=True
    def terminate(self):self.terminated=True


class PGAdmissionProbeTests(unittest.IsolatedAsyncioTestCase):
    def config(self,ca):
        return dict(batch='investigation-program-admission-pg-20261025-01',ssl_ca=str(ca),
            writer_dsn='postgresql://socai2_inv_m8a_20261025_01_w:test-only-password@192.168.1.21:5432/aisoc',
            reader_dsn='postgresql://socai2_inv_m8a_20261025_01_r:test-only-password@192.168.1.21:5432/aisoc',
            operational_isolation_ref='test-only-config-ref-not-operational-proof')

    def controls(self):return seam.Controls(UUID(int=77))

    def test_exact_config_roles_host_no_replay_or_override(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.local/verification') as directory:
            ca=Path(directory)/'test-only.crt';ca.write_text('test-only','utf-8');config=self.config(ca)
            self.assertEqual(seam.validate_config(config),config['batch'])
            for changes in ({'batch':'bad;DROP DATABASE'}, {'writer_dsn':config['writer_dsn'].replace('192.168.1.21','evil.invalid')},
                            {'reader_dsn':config['writer_dsn']},{'writer_dsn':config['writer_dsn']+'?sslmode=disable'},
                            {'writer_dsn':config['writer_dsn'].replace('/aisoc','/other')},{'operational_isolation_ref':''}, {'override':True}):
                with self.assertRaises(AssertionError):seam.validate_config({**config,**changes})

    def test_exact_zero_budget_and_stable_selected_targets(self):
        ids=seam.identities('investigation-program-admission-pg-20261025-01')
        self.assertEqual(len({v['alert_id'] for v in ids.values()}),3)
        p=seam.budget();self.assertEqual((p.max_model_calls,p.max_tool_calls,p.max_tokens,p.max_cost_microusd),(0,0,0,0))
        actor=UUID(int=44);intent=seam.make_intent('investigation-program-admission-pg-20261025-01','normal',actor)
        other=seam.make_intent('investigation-program-admission-pg-20261025-01','normal',actor,other_key=True)
        self.assertNotEqual(intent['run_id'],other['run_id']);self.assertEqual(intent['request']['target'],other['request']['target'])

    async def test_precommit_barrier_observes_complete_uncommitted_rows_before_commit(self):
        raw=Connection();controls=self.controls();conn=seam.ConnectionAdapter(raw,controls,'normal-owner')
        async def transaction():
            async with conn.transaction(isolation='read_committed'):pass
        task=asyncio.create_task(transaction());await asyncio.wait_for(controls.pre_ready.wait(),1)
        self.assertEqual(raw.commits,0);self.assertEqual(controls.before_commit_counts,{'runs':1,'events':2,'artifacts':3})
        controls.pre_release.set();await task;self.assertEqual(raw.commits,1)
        async with conn.transaction():pass
        self.assertEqual(raw.commits,2)  # Barrier only applies to the first admission.

    async def test_cancelled_precommit_barrier_rolls_back_without_commit(self):
        raw=Connection();controls=self.controls();conn=seam.ConnectionAdapter(raw,controls,'normal-owner')
        async def transaction():
            async with conn.transaction():pass
        task=asyncio.create_task(transaction());await asyncio.wait_for(controls.pre_ready.wait(),1);task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertEqual((raw.commits,raw.rollbacks),(0,1))

    async def test_unknown_ack_fault_is_strictly_after_commit_and_only_once(self):
        raw=Connection();controls=self.controls();conn=seam.ConnectionAdapter(raw,controls,'ack-owner')
        with self.assertRaises(RuntimeError):
            async with conn.transaction():pass
        self.assertEqual((raw.commits,raw.rollbacks),(1,0));self.assertTrue(controls.ack_fired);self.assertEqual(controls.ack_pid,321)
        async with conn.transaction():pass
        self.assertEqual((raw.commits,raw.rollbacks),(2,0))

    async def test_artifact_fault_is_inside_transaction_and_does_not_call_driver(self):
        raw=Connection();controls=self.controls();conn=seam.ConnectionAdapter(raw,controls,'rollback-owner')
        with self.assertRaises(RuntimeError):
            async with conn.transaction():await conn.fetchval('INSERT INTO investigation_artifacts',1,2,3,4,seam.ARTIFACT_KIND,6,7,8)
        self.assertEqual((raw.commits,raw.rollbacks,raw.fetches),(0,1,0));self.assertTrue(controls.rollback_fired)

    async def test_actual_tag_is_task_local_and_restored(self):
        async def method():await asyncio.sleep(0);return seam.TAG.get()
        self.assertEqual(await asyncio.gather(seam.tagged('one',method),seam.tagged('two',method)),['one','two'])
        self.assertEqual(seam.TAG.get(),'unclassified')

    async def test_blocking_direct_and_transitive_chains_are_accepted(self):
        for blockers in ([1],[2]):
            raw=Connection();controls=self.controls();controls.pids={'normal-owner':1,'same-key':2,'other-key':3}
            raw.rows=[dict(pid=1,wait_event_type=None,wait_event=None,blockers=[]),
                      dict(pid=2,wait_event_type='Lock',wait_event='transactionid',blockers=[1]),
                      dict(pid=3,wait_event_type='Lock',wait_event='tuple',blockers=blockers)]
            result=await seam.wait_for_locks(raw,controls);self.assertEqual(result['pids'],controls.pids)

    async def test_same_connection_or_no_actual_lock_wait_cannot_count_as_concurrency(self):
        raw=Connection();controls=self.controls();controls.pids={'normal-owner':1,'same-key':1,'other-key':3}
        with self.assertRaises(AssertionError):await seam.wait_for_locks(raw,controls)
        controls.pids={'normal-owner':1,'same-key':2,'other-key':3}
        raw.rows=[dict(pid=i,wait_event_type='Client',wait_event='ClientRead',blockers=[]) for i in (1,2,3)]
        with self.assertRaises(TimeoutError):await asyncio.wait_for(seam.wait_for_locks(raw,controls),.03)

    async def test_pool_connection_and_TLS_setup_failure_still_saves_failed_receipt(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.local/verification') as directory:
            ca=Path(directory)/'test-only.crt';ca.write_text('test-only','utf-8');config=self.config(ca)
            for name,tls_error in (('connection',False),('TLS',True)):
                out=Path(directory)/name
                with patch.object(seam.ssl,'create_default_context',side_effect=RuntimeError('PRIVATE_CA') if tls_error else None,return_value=object()), \
                     patch('asyncpg.create_pool',new=AsyncMock(side_effect=RuntimeError('PRIVATE_DSN'))) as connect:
                    with self.assertRaises(RuntimeError):await seam.run_probe(config,out)
                r=json.loads((out/'receipt.json').read_text('utf-8'));self.assertEqual(r['status'],'failed_preserve_actual_pg_trial')
                self.assertTrue(r['connection_closed']);self.assertNotIn('PRIVATE',(out/'receipt.json').read_text('utf-8'))
                self.assertEqual(connect.await_count,0 if tls_error else 1)
                with self.assertRaises(FileExistsError):await seam.run_probe(config,out)

    async def test_resource_close_timeout_terminates_only_that_resource(self):
        raw=Connection()
        async def hang():await asyncio.Future()
        raw.close=hang
        original=asyncio.wait_for
        async def short(awaitable,timeout):return await original(awaitable,.03)
        with patch.object(seam.asyncio,'wait_for',short):
            with self.assertRaises(TimeoutError):await seam.closed(raw)
        self.assertTrue(raw.terminated)

    async def test_owner_failure_before_barrier_is_preserved_instead_of_timeout(self):
        actor=UUID(int=9);intent=seam.make_intent('investigation-program-admission-pg-20261025-01','normal',actor)
        other=seam.make_intent('investigation-program-admission-pg-20261025-01','normal',actor,other_key=True)
        controls=seam.Controls(UUID(intent['run_id']))
        class Failed:
            async def start(self,**kwargs):raise seam.ExecutionPersistenceError('test-only-early-admission-failure')
        with self.assertRaises(seam.ExecutionPersistenceError):
            await asyncio.wait_for(seam.normal_race(Failed(),controls,None,None,intent,other,actor),.2)
        self.assertEqual(controls.primary_failure['type'],'ExecutionPersistenceError')
        self.assertEqual(controls.task_failures[0]['type'],'ExecutionPersistenceError')

    async def test_slow_cleanup_does_not_replace_primary_observer_failure(self):
        actor=UUID(int=9);intent=seam.make_intent('investigation-program-admission-pg-20261025-01','normal',actor)
        other=seam.make_intent('investigation-program-admission-pg-20261025-01','normal',actor,other_key=True)
        controls=seam.Controls(UUID(intent['run_id']));release=asyncio.Event();tasks=[]
        class Slow:
            async def start(self,**kwargs):
                tasks.append(asyncio.current_task());controls.pre_ready.set()
                try:await asyncio.Future()
                except asyncio.CancelledError:await release.wait();raise
        original=asyncio.wait
        async def brief(awaitables,timeout,**kwargs):return await original(awaitables,timeout=min(timeout,.03),**kwargs)
        try:
            with patch.object(seam,'read_ledger',new=AsyncMock(side_effect=ValueError('test-only-observer-failure'))),patch.object(seam.asyncio,'wait',brief):
                with self.assertRaises(ValueError):await seam.normal_race(Slow(),controls,None,None,intent,other,actor)
            self.assertEqual(controls.primary_failure['type'],'ValueError')
            self.assertEqual(controls.cleanup_failure,{'type':'TimeoutError','pending':['owner']})
        finally:
            release.set();await asyncio.gather(*tasks,return_exceptions=True)


if __name__=='__main__':unittest.main()
