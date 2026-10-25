"""Opt-in actual PG manual admission; zero tools/models, no HTTP application.

Private setup creates only the three selected synthetic Alerts and short-lived
roles beforehand. This probe never grants privileges, changes schema or cleans
retained data. The setup owner must revoke the roles after this exits.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import ssl
import sys
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'services/agents'))
import httpx
from app.investigation_v2.execution_state import ExecutionRejected
from app.investigation_v2.execution_store import ExecutionPersistenceError, canonical_json, content_hash
from app.investigation_v2.program_start_contract import normalize_program_alert_start, REQUEST_VERSION
from app.investigation_v2.program_start_store import ProgramAlertStartStore, ARTIFACT_KIND
from app.investigation_v2.program_start_coordinator import ProgramManualStartCoordinator
from app.investigation_v2.program_start_api import ControlledManualTargetPolicy
from app.investigation_v2.program_result_reader import CompatibleOwnedReconResultReader
from app.investigation_v2.scope import TenantPrincipal, UTCWindow
from app.investigation_v2.start_contract import StartBudgetPolicy

TENANT=UUID('53824f24-d1d4-5820-8147-f6cfda8a1247')
OLD_RUN=UUID('4dfd374a-17a6-5fec-833b-803bfbcb85c6')
TAG=ContextVar('manual_pg_probe_tag',default='unclassified')
CASES=('normal','rollback','admission_ACK')
TOOL_TOKEN='test-only-zero-tool-pg-probe-credential-not-live'


def require(value,reason='controlled PG probe invariant failed'):
    if not value:raise AssertionError(reason)


def identities(batch):
    require(type(batch) is str and re.fullmatch(r'investigation-program-admission-pg-20261025-\d{2}',batch))
    return {name:dict(alert_id=str(uuid5(NAMESPACE_URL,'socai2:'+batch+':'+name+':alert')),
                     operation_key=str(uuid5(NAMESPACE_URL,'socai2:'+batch+':'+name+':operation'))) for name in CASES}


def validate_config(config):
    require(type(config) is dict and set(config)=={'batch','writer_dsn','reader_dsn','ssl_ca','operational_isolation_ref'},'explicit exact PG probe configuration required')
    batch=config['batch'];identities(batch)
    for key,suffix in (('writer_dsn','w'),('reader_dsn','r')):
        parsed=urlsplit(config[key])
        require((parsed.scheme,parsed.hostname,parsed.port,parsed.path)==('postgresql','192.168.1.21',5432,'/aisoc'))
        require(parsed.username=='socai2_inv_m8a_20261025_'+batch[-2:]+'_'+suffix and bool(parsed.password)
                and not parsed.query and not parsed.fragment,'fresh exact PG role required')
    require(type(config['operational_isolation_ref']) is str and bool(config['operational_isolation_ref'].strip()))
    require(type(config['ssl_ca']) is str and Path(config['ssl_ca']).is_file(),'explicit CA required')
    return batch


def budget():
    return StartBudgetPolicy(max_model_calls=0,max_tool_calls=0,max_tokens=0,max_cost_microusd=0,max_unsettled=1,
        duration_seconds=180,config_ref='controlled-pg-admission-zero-call.v1',legacy_model_limit_mapping='No models or tool dispatch; admission/locking verification only')


def principal(actor):return TenantPrincipal(frozenset({TENANT}),'verified-pg-probe:'+str(actor),True)


def make_intent(batch,name,actor,*,other_key=False):
    ids=identities(batch)[name];key=UUID(ids['operation_key'])
    if other_key:key=uuid5(key,'competing-operation')
    return normalize_program_alert_start(principal=principal(actor),tenant_id=TENANT,actor_id=actor,operation_key=key,
        alert_id=UUID(ids['alert_id']),window=UTCWindow(datetime(2026,10,23,10,tzinfo=timezone.utc),datetime(2026,10,23,10,5,tzinfo=timezone.utc)),
        budget_policy=budget(),profile='alert_recon',trigger='manual',request_version=REQUEST_VERSION)


def exception_types(error):
    chain=[];seen=set()
    while error is not None and id(error) not in seen:
        seen.add(id(error));chain.append(type(error).__name__)
        error=error.__cause__ if error.__cause__ is not None else error.__context__
    return chain


class Controls:
    def __init__(self,normal_run,on_change=None):
        self.normal_run=normal_run
        self.pre_ready=asyncio.Event();self.pre_release=asyncio.Event()
        self.post_ready=asyncio.Event();self.post_release=asyncio.Event()
        self.pre_fired=False;self.rollback_fired=False;self.ack_fired=False
        self.pids={};self.before_commit_counts=None;self.ack_pid=None
        self.last_locks=[];self.primary_failure=None;self.task_failures=[];self.cleanup_failure=None
        self.on_change=on_change

    def snapshot(self):
        return dict(pids=dict(self.pids),pre_ready=self.pre_ready.is_set(),post_ready=self.post_ready.is_set(),
            pre_released=self.pre_release.is_set(),post_released=self.post_release.is_set(),
            before_commit_counts=self.before_commit_counts,last_locks=self.last_locks,
            rollback_injected=self.rollback_fired,commit_ACK_injected=self.ack_fired,ack_backend_pid=self.ack_pid,
            primary_failure=self.primary_failure,task_failures=self.task_failures,cleanup_failure=self.cleanup_failure)

    def changed(self):
        if self.on_change is not None:self.on_change(self.snapshot())


class ConnectionAdapter:
    """Faults apply only to the explicit test tag, not to shared driver code."""
    def __init__(self,connection,controls,tag):self.connection,self.controls,self.tag=connection,controls,tag
    def __getattr__(self,name):return getattr(self.connection,name)

    @asynccontextmanager
    async def transaction(self,**kwargs):
        c=self.controls
        async with self.connection.transaction(**kwargs):
            yield self
            if self.tag=='normal-owner' and not c.pre_fired:
                c.pre_fired=True
                # The first admission has written all rows, still uncommitted.
                counts=await self.connection.fetchrow("SELECT (SELECT count(*) FROM investigation_runs WHERE id=$1 AND tenant_id=$2) AS runs,"
                    "(SELECT count(*) FROM investigation_events WHERE run_id=$1 AND tenant_id=$2) AS events,"
                    "(SELECT count(*) FROM investigation_artifacts WHERE run_id=$1 AND tenant_id=$2) AS artifacts",c.normal_run,TENANT)
                require(tuple(counts[k] for k in ('runs','events','artifacts'))==(1,2,3),'first uncommitted admission must be complete')
                c.before_commit_counts=dict(counts);c.pre_ready.set();c.changed()
                await asyncio.wait_for(c.pre_release.wait(),10)
        if self.tag=='ack-owner' and not c.ack_fired:
            # This point is strictly AFTER the actual connection COMMIT.
            c.ack_fired=True;c.ack_pid=self.connection.get_server_pid();c.changed()
            raise RuntimeError('test-only-confirmed-COMMIT-acknowledgement-lost')

    async def fetchval(self,sql,*args):
        if self.tag=='rollback-owner' and not self.controls.rollback_fired and sql.startswith('INSERT INTO investigation_artifacts') and args[4]==ARTIFACT_KIND:
            self.controls.rollback_fired=True
            self.controls.changed()
            raise RuntimeError('test-only-admission-artifact-write-failure')
        return await self.connection.fetchval(sql,*args)


class TaggedPool:
    def __init__(self,pool,controls):self.pool,self.controls=pool,controls
    @asynccontextmanager
    async def acquire(self):
        async with self.pool.acquire(timeout=10) as connection:
            tag=TAG.get();self.controls.pids.setdefault(tag,connection.get_server_pid());self.controls.changed()
            yield ConnectionAdapter(connection,self.controls,tag)


class GatedAdmission(ProgramAlertStartStore):
    async def admit(self,**kwargs):
        result=await super().admit(**kwargs)
        controls=self.pool.controls
        if TAG.get()=='normal-owner' and result.receipt['fresh']:
            controls.post_ready.set();controls.changed()
            await asyncio.wait_for(controls.post_release.wait(),10)
        return result


async def tagged(tag,method,**kwargs):
    token=TAG.set(tag)
    try:return await method(**kwargs)
    finally:TAG.reset(token)


async def read_ledger(connection,run_id):
    async with connection.transaction(readonly=True):
        await connection.execute("SELECT set_config('app.current_tenant_id',$1,true)",str(TENANT))
        require(await connection.fetchval('SHOW transaction_read_only')=='on')
        run=await connection.fetchrow('SELECT * FROM investigation_runs WHERE id=$1 AND tenant_id=$2',run_id,TENANT)
        events=await connection.fetch('SELECT id,tenant_id,run_id,seq,ts,kind,agent,summary,payload,input_hash,output_hash,duration_ms,created_at FROM investigation_events WHERE run_id=$1 AND tenant_id=$2 ORDER BY seq',run_id,TENANT)
        arts=await connection.fetch('SELECT * FROM investigation_artifacts WHERE run_id=$1 AND tenant_id=$2 ORDER BY id',run_id,TENANT)
    return dict(run=dict(run) if run else None,events=[dict(r) for r in events],artifacts=[dict(r) for r in arts])


def ledger_hash(ledger):return content_hash(canonical_json(ledger,max_bytes=8*1024*1024))


def checked_artifacts(ledger):
    event_ids={str(e['id']) for e in ledger['events']}
    require(len(event_ids)==len(ledger['events']))
    for art in ledger['artifacts']:
        require(str(art['event_id']) in event_ids and art['tenant_id']==TENANT)
        require(art['content'] is not None and len(art['content'].encode('utf-8'))==art['size_bytes'] and content_hash(art['content'])==art['sha256'])
    return True


async def wait_for_locks(connection,controls):
    async with asyncio.timeout(10):
        while not all(k in controls.pids for k in ('normal-owner','same-key','other-key')):await asyncio.sleep(.02)
        pids={k:controls.pids[k] for k in ('normal-owner','same-key','other-key')}
        require(len(set(pids.values()))==3,'real distinct connections required, not a pool queue')
        while True:
            async with connection.transaction(readonly=True):
                rows=await connection.fetch('SELECT pid,wait_event_type,wait_event,pg_blocking_pids(pid) AS blockers FROM pg_stat_activity WHERE pid=ANY($1::int[])',list(pids.values()))
            graph={r['pid']:list(r['blockers']) for r in rows}
            observed=[dict(r) for r in rows]
            if controls.last_locks!=observed:
                controls.last_locks=observed;controls.changed()
            def reaches(start,seen=None):
                seen=set() if seen is None else seen
                if start==pids['normal-owner']:return True
                if start in seen:return False
                seen.add(start)
                return any(reaches(p,seen.copy()) for p in graph.get(start,[]))
            by_id={r['pid']:r for r in rows}
            if all(by_id.get(pids[k],{}).get('wait_event_type')=='Lock' and reaches(pids[k]) for k in ('same-key','other-key')):
                return dict(pids=pids,observations=[dict(r) for r in rows])
            await asyncio.sleep(.025)


async def barrier_or_owner(event,owner):
    signal=asyncio.create_task(event.wait())
    try:
        done,_=await asyncio.wait((signal,owner),timeout=10,return_when=asyncio.FIRST_COMPLETED)
        if owner in done:
            await owner  # Preserve an actual early admission/commit failure.
            raise AssertionError('owner finished before the required barrier release')
        if signal not in done:raise TimeoutError('probe barrier was not reached within ten seconds')
    finally:
        if not signal.done():signal.cancel()
        await asyncio.gather(signal,return_exceptions=True)


async def normal_race(coordinator,controls,observer,diagnostic,intent,other,actor):
    kwargs=dict(current_principal=principal(actor),current_actor_id=actor)
    tasks=[];primary_error=None;expected_rejections=set()
    try:
        async with asyncio.timeout(60):
            owner=asyncio.create_task(tagged('normal-owner',coordinator.start,intent=intent,**kwargs));tasks.append(('owner',owner))
            await barrier_or_owner(controls.pre_ready,owner)
            invisible=await read_ledger(observer,UUID(intent['run_id']))
            require(invisible=={'run':None,'events':[],'artifacts':[]},'uncommitted admission visible to another connection')
            duplicate=asyncio.create_task(tagged('same-key',coordinator.start,intent=intent,**kwargs));tasks.append(('same-key',duplicate))
            different=asyncio.create_task(tagged('other-key',coordinator.start,intent=other,**kwargs));tasks.append(('other-key',different))
            locks=await wait_for_locks(diagnostic,controls)
            controls.pre_release.set();controls.changed();await barrier_or_owner(controls.post_ready,owner)
            repeated=await duplicate
            require(repeated['mode']=='read_only' and repeated['runtime']['entered_by_this_invocation'] is False)
            require(repeated['result']['progress']['phase']=='ready')
            try:await different
            except ExecutionRejected:other_rejected=True;expected_rejections.add(different)
            else:raise AssertionError('other active key was admitted')
            require((await read_ledger(observer,UUID(other['run_id'])))['run'] is None)
            committed=await read_ledger(observer,UUID(intent['run_id']))
            require((len(committed['events']),len(committed['artifacts']))==(2,3))
            controls.post_release.set();controls.changed();first=await owner
            require(first['mode']=='coordinated' and first['runtime']['http_attempted_by_this_invocation'] is False)
            require(first['result']['publication_state']=='published' and first['result']['execution_snapshot']['scope_readiness']=='partial')
            return dict(locks=locks,uncommitted_visibility=invisible,precommit_counts=controls.before_commit_counts,
                duplicate=repeated,other_key_rejected=other_rejected,first=first)
    except BaseException as exc:
        primary_error=exc;controls.primary_failure=dict(type=type(exc).__name__,chain=exception_types(exc));controls.changed()
        raise
    finally:
        controls.pre_release.set();controls.post_release.set()
        for _,task in tasks:
            if not task.done():task.cancel()
        if tasks:
            done,pending=await asyncio.wait([t for _,t in tasks],timeout=5)
            for name,task in tasks:
                if task in done and not task.cancelled() and task not in expected_rejections:
                    error=task.exception()
                    if error is not None:controls.task_failures.append(dict(task=name,type=type(error).__name__,chain=exception_types(error)))
            if pending:
                controls.cleanup_failure=dict(type='TimeoutError',pending=[name for name,task in tasks if task in pending])
            controls.changed()
            if pending and primary_error is None:raise TimeoutError('parallel PG task cleanup exceeded five seconds')


async def closed(resource,pool=False):
    if resource is None:return
    try:await asyncio.wait_for(resource.close(),5)
    except BaseException:
        resource.terminate()
        raise


async def run_probe(config,out):
    import asyncpg
    batch=validate_config(config);out=Path(out).resolve()
    require(out.is_relative_to(ROOT/'.local'/'verification') and out.parent.is_dir(),'new local process-evidence directory required')
    out.mkdir(exist_ok=False)
    pool=observer=diagnostic=controls=None
    receipt=dict(schema='program_admission_actual_pg.v1',batch=batch,status='starting',cases={},tool_attempts=0,model_calls=0)
    def save():
        (out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save()
    actor=uuid5(NAMESPACE_URL,'socai2:'+batch+':verified-probe-actor')
    inputs={name:make_intent(batch,name,actor) for name in CASES}
    receipt.update(actor_id=str(actor),tenant_id=str(TENANT),inputs=inputs,connection_closed=False)
    try:
        tls=ssl.create_default_context(cafile=config['ssl_ca'])
        pool=await asyncpg.create_pool(config['writer_dsn'],ssl=tls,min_size=3,max_size=3,timeout=10,command_timeout=10)
        observer=await asyncpg.connect(config['reader_dsn'],ssl=tls,timeout=10,command_timeout=10)
        # Same role as the waiters, so own-session pg_stat_activity remains
        # visible without granting pg_monitor or global statistics access.
        diagnostic=await asyncpg.connect(config['writer_dsn'],ssl=tls,timeout=10,command_timeout=10)
        receipt['observer_session']=dict(await observer.fetchrow("SELECT current_user AS role,current_setting('default_transaction_read_only') AS default_readonly,current_setting('default_transaction_isolation') AS default_isolation"))
        require(receipt['observer_session']['default_readonly']=='on')
        old_before=await read_ledger(observer,OLD_RUN);checked_artifacts(old_before)
        require(old_before['run'] is not None and len(old_before['events'])==6 and len(old_before['artifacts'])==14)
        reports=[a for a in old_before['artifacts'] if a['kind']=='fixed_recon_report_markdown']
        require(len(reports)==1 and reports[0]['size_bytes']==3111 and reports[0]['sha256']=='e5f4c3fe2d4f4130eb4ad4964260f87f4a63aea9bb31426566dedafdd8ad68ac')
        receipt['old_baseline_before']=ledger_hash(old_before)
        def progress(value):receipt['race_controls']=value;save()
        controls=Controls(UUID(inputs['normal']['run_id']),on_change=progress);wrapped=TaggedPool(pool,controls)
        policy_doc=dict(schema='controlled_manual_start_targets.v1',policy_ref='controlled-pg-admission-targets.v1',mode='isolated_manual_test',
            targets=[dict(tenant_id=str(TENANT),alert_id=v['alert_id'],operational_isolation_ref=config['operational_isolation_ref']) for v in identities(batch).values()])
        guard=ControlledManualTargetPolicy.from_document(policy_doc)
        async def forbidden(request):
            receipt['tool_attempts']+=1;save();raise AssertionError('zero-tool PG probe attempted external dispatch')
        coordinator=ProgramManualStartCoordinator(GatedAdmission(wrapped,budget_policy=budget()),CompatibleOwnedReconResultReader(wrapped),
            target_guard=guard,target_policy_ref=guard.policy_ref,api_url='https://zero-call.invalid',service_token=TOOL_TOKEN,transport=httpx.MockTransport(forbidden))
        kwargs=dict(current_principal=principal(actor),current_actor_id=actor)
        race=await normal_race(coordinator,controls,observer,diagnostic,inputs['normal'],make_intent(batch,'normal',actor,other_key=True),actor)
        receipt['cases']['normal']=race;save()
        for name,tag in (('rollback','rollback-owner'),('admission_ACK','ack-owner')):
            intent=inputs[name]
            try:await tagged(tag,coordinator.start,intent=intent,**kwargs)
            except ExecutionPersistenceError:receipt['cases'][name]=dict(status='expected_persistence_error')
            else:raise AssertionError('faulted start was reported successful')
            ledger=await read_ledger(observer,UUID(intent['run_id']))
            if name=='rollback':require(ledger=={'run':None,'events':[],'artifacts':[]} and controls.rollback_fired)
            else:require((len(ledger['events']),len(ledger['artifacts']))==(2,3) and controls.ack_fired)
            receipt['cases'][name]['ledger']=json.loads(canonical_json(ledger,max_bytes=8*1024*1024));save()
        for name in ('normal','admission_ACK'):
            intent=inputs[name];run=UUID(intent['run_id']);before=await read_ledger(observer,run);checked_artifacts(before)
            read=await tagged('read-'+name,coordinator.read_operation,intent=intent,**kwargs)
            repeat=await tagged('repeat-'+name,coordinator.start,intent=intent,**kwargs)
            owned=await CompatibleOwnedReconResultReader(wrapped).read(current_principal=principal(actor),tenant_id=TENANT,run_id=run)
            after=await read_ledger(observer,run)
            require(canonical_json(read)==canonical_json(repeat) and canonical_json(owned)==canonical_json(read['result']))
            require(ledger_hash(before)==ledger_hash(after),'read or repeat changed ledger')
            require(read['mode']=='read_only' and read['runtime']['entered_by_this_invocation'] is False)
            expected=(5,11) if name=='normal' else (2,3)
            require((len(after['events']),len(after['artifacts']))==expected)
            require(after['run']['status']=='running' and after['run']['completed_at'] is None and after['run']['total_tokens']==after['run']['total_cost_usd']==0)
            receipt['cases'][name].update(read=read,repeat=repeat,owned=owned,ledger=json.loads(canonical_json(after,max_bytes=8*1024*1024)),ledger_sha256=ledger_hash(after))
            save()
        old_after=await read_ledger(observer,OLD_RUN)
        require(ledger_hash(old_before)==ledger_hash(old_after),'selected old baseline changed')
        require(receipt['tool_attempts']==0)
        receipt.update(status='passed_limited_actual_pg_zero_call',old_baseline_after=ledger_hash(old_after),
            controls=dict(precommit_counts=controls.before_commit_counts,rollback_injected=controls.rollback_fired,commit_ACK_injected=controls.ack_fired,ack_backend_pid=controls.ack_pid),
            limits=['No real JWT/RBAC,HTTP/CH/model,notification,deployment or legacy configuration change','ACK loss is a post-COMMIT test adapter, not a real network interruption','Unknown ACK Run stays ready/legacy running; never replayed or closed'])
    except BaseException as exc:
        receipt.update(status='failed_preserve_actual_pg_trial',error_type=type(exc).__name__)
        receipt['error_chain']=exception_types(exc)
        if isinstance(exc,AssertionError):receipt['check']=str(exc)
        # A failed/unknown run still gets an independent raw read when that
        # connection is available. No runtime or admission is invoked here.
        if observer is not None:
            captured={}
            for name,intent in inputs.items():
                try:
                    captured[name]=json.loads(canonical_json(await read_ledger(observer,UUID(intent['run_id'])),max_bytes=8*1024*1024))
                except BaseException as failure:
                    captured[name]={'capture_error_type':type(failure).__name__}
            receipt['failure_raw_ledgers']=captured
        raise
    finally:
        if controls is not None:receipt['race_controls']=controls.snapshot()
        errors=[]
        for label,resource in (('diagnostic',diagnostic),('observer',observer),('pool',pool)):
            try:await closed(resource,pool=label=='pool')
            except BaseException as exc:errors.append(dict(resource=label,error_type=type(exc).__name__))
        receipt['connection_closed']=not errors;receipt['cleanup_errors']=errors
        if errors:receipt['status']='failed_cleanup_preserve_trial'
        save()
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    try:
        config=json.loads(args.config.read_text('utf-8'));r=asyncio.run(run_probe(config,args.out))
        print(json.dumps(dict(status=r['status'],tool_attempts=r['tool_attempts'],model_calls=r['model_calls'],connection_closed=r['connection_closed'])))
        return 0 if r['status']=='passed_limited_actual_pg_zero_call' and r['connection_closed'] else 1
    except BaseException as exc:
        print(json.dumps(dict(status='failed_preserve_pg_trial',error_type=type(exc).__name__,credentials_printed=False)));return 1


if __name__=='__main__':raise SystemExit(main())
