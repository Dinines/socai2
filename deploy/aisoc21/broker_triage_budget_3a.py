"""Real SSL Kafka/PG with HTTP-model transport substitutes; zero real models."""
from __future__ import annotations
import asyncio,contextlib,hashlib,json,os,sys,time,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

sys.path.insert(0,'/app')
E=Path('/evidence');B='3a-triage-budget-20261020'
ALIASES=['a_done','b_done','a_unknown','a_denied','b_denied','b_extra']
PREFIX='socai2.test.'+B+'.'


def save(name,value):
    with (E/name).open('x') as f:json.dump(value,f,indent=2,default=str)
    (E/name).chmod(0o600)


def read(name):return json.loads((E/name).read_text())


def resources():
    return {n:{'topic':PREFIX+n,'dlq':PREFIX+n+'.dlq','group':PREFIX+n+'.worker'} for n in ALIASES}


async def barrier(name,seconds=45):
    end=asyncio.get_running_loop().time()+seconds
    while not (E/name).exists():
        assert asyncio.get_running_loop().time()<end,'Barrier timeout; inspect instead of replay'
        await asyncio.sleep(.05)
    return read(name)


async def main(phase,role=None):
    import structlog
    structlog.configure(processors=[structlog.processors.TimeStamper(fmt='iso'),structlog.processors.format_exc_info,structlog.processors.JSONRenderer()])
    from aiokafka import AIOKafkaConsumer,AIOKafkaProducer,TopicPartition,OffsetAndMetadata
    from app.core.kafka_security import kafka_client_kwargs
    from app.investigator import ledger
    from app.workers import fused_alert_consumer as worker_module,triage_budget as budget,triage_delivery as delivery
    from app.agents import auto_triage_agent as agent
    from app.llm import contract
    from app.llm.factory import make_chat_model
    import httpx
    os.umask(0o077)
    state=json.loads(Path('/private/state.json').read_text());assert state['batch']==B
    inputs=read('inputs.json')
    if (E/'inputs-extra.json').exists():inputs.update(read('inputs-extra.json'))
    assert set(inputs)==set(ALIASES)
    topicmap=resources();security=kafka_client_kwargs();bootstrap=os.environ['KAFKA_BOOTSTRAP_SERVERS']
    assert security['security_protocol']=='SSL' and not worker_module.worker_enabled()
    assert not worker_module._escalation_enabled() and not worker_module._memory_writeback_enabled()
    assert not worker_module._approvals_enabled() and not worker_module.alert_trigger.deployment_enabled()
    source={'services/agents/app/'+str(p.relative_to('/app/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/app').rglob('*.py')}
    assert source==read('tests-agents-final.json')['tested_runtime_source_sha256']
    label=role if phase=='child' else phase
    save('budget-'+label+'-started.json',{'phase':phase,'role':role,'pid':os.getpid(),'source_sha256':hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest(),'real_models':0})
    ids={n:worker_module.build_state(v) for n,v in inputs.items()}
    pool=await ledger.get_pool();assert pool is not None
    async def db(tenant,sql,*args):
        async with pool.acquire() as conn:
            async with conn.transaction():
                await ledger._set_rls_context(conn,tenant)
                return [dict(v) for v in await conn.fetch(sql,*args)]
    async def reservations():
        result=[]
        for n in ['a','b']:
            result+=await db(uuid.UUID(state['identities'][n]['tenant_id']),
                 'SELECT * FROM socai2_triage_budget_reservations WHERE tenant_id=$1 ORDER BY run_id',uuid.UUID(state['identities'][n]['tenant_id']))
        return result
    async def runs(alias):
        s=ids[alias]
        return await db(s.tenant_id,'SELECT id,status,model_used,total_tokens FROM investigation_runs WHERE id=$1',s.run_id)
    async def observer(alias,group=None):
        value=topicmap[alias]
        c=AIOKafkaConsumer(bootstrap_servers=bootstrap,group_id=group or value['group'],enable_auto_commit=False,**security)
        await c.start();tp=TopicPartition(value['topic'],0);c.assign([tp]);return c,tp
    async def offsets(alias,group=None):
        c,tp=await observer(alias,group)
        try:return {'committed':await c.committed(tp),'end':(await c.end_offsets([tp]))[tp]}
        finally:await c.stop()
    async def publish(alias):
        assert len(list(E.glob('budget-publish-*-ack.json')))<12
        save('budget-publish-'+alias+'-sending.json',{'alias':alias,'run_id':ids[alias].run_id})
        p=AIOKafkaProducer(bootstrap_servers=bootstrap,value_serializer=lambda v:json.dumps(v).encode(),**security)
        await p.start()
        try:
            sent=await p.send_and_wait(topicmap[alias]['topic'],value=inputs[alias])
            save('budget-publish-'+alias+'-ack.json',{'topic':sent.topic,'partition':sent.partition,'offset':sent.offset})
        finally:await p.stop()
    if phase in ['setup','setup-extra']:
        from aiokafka.admin import AIOKafkaAdminClient,NewTopic
        admin=AIOKafkaAdminClient(bootstrap_servers=bootstrap,**security);await admin.start()
        aliases=['b_extra'] if phase=='setup-extra' else ALIASES
        names=[topicmap[n][k] for n in aliases for k in ['topic','dlq']]
        try:
            assert not set(names).intersection(await admin.list_topics())
            await admin.create_topics([NewTopic(n,1,1,topic_configs={'retention.ms':'604800000'}) for n in names])
        finally:await admin.close()
        groups=[]
        for alias in aliases:
            for group in [topicmap[alias]['group']]+([topicmap[alias]['group']+'.cold'] if alias=='b_done' else []):
                c,tp=await observer(alias,group)
                try:
                    assert await c.committed(tp) is None and (await c.end_offsets([tp]))[tp]==0
                    await c.commit({tp:OffsetAndMetadata(0,'new-budget-baseline')});groups.append({'alias':alias,'group':group,'offset':0})
                finally:await c.stop()
        save('budget-resources-extra.json' if phase=='setup-extra' else 'budget-resources.json',{'resources':topicmap,'groups':groups});return
    if phase=='pg-boundaries':
        assert not await reservations()
        s=ids['a_done'];fields=worker_module.FusedAlertTriageWorker._delivery_fields(s)
        original=budget.reserve
        async def fail(conn,**kwargs):await conn.execute('SELECT 1/0')
        budget.reserve=fail
        try:
            with contextlib.suppress(budget.BudgetHold):await delivery.claim(**fields,budget=budget.policy_for(s.tenant_id))
        finally:budget.reserve=original
        assert not await runs('a_done') and not await reservations()
        original_pool=ledger.get_pool
        async def absent():return None
        ledger.get_pool=absent
        try:
            try:await delivery.claim(**fields,budget=budget.policy_for(s.tenant_id))
            except budget.BudgetHold:pass
            else:raise AssertionError('No pool must not admit a model')
        finally:ledger.get_pool=original_pool
        fields['tenant_id']=uuid.UUID(state['identities']['b']['tenant_id'])
        try:await delivery.claim(**fields,budget=budget.policy_for(fields['tenant_id']))
        except budget.BudgetHold:pass
        else:raise AssertionError('Cross-tenant claim admitted')
        assert not await reservations() and not await runs('a_done')
        save('budget-pg-boundaries.json',{'real_artifact_free_claim_insert_rolled_back_with_reservation_fault':True,'no_pool_denied':True,'cross_tenant_denied':True,'new_runs_or_reservations':0,'real_shared_pg_outage':False});return

    # Only the HTTP transport is replaced. The real agent/prompt/parser,
    # request-boundary admission, PG ledger and Kafka loop remain in use.
    async def transport(request):
        invocation=budget.current_invocation();assert invocation is not None and invocation.request_marked
        number=len(list(E.glob('budget-http-start-*.json')))+1;assert number<=6
        save('budget-http-start-'+str(number)+'.json',{'pid':os.getpid(),'run_id':invocation.run_id,'body_sha256':hashlib.sha256(request.content).hexdigest(),'provider_substitute':True,'real_model':False})
        if role in ['unknown-owner','unknown-owner-recovered','live-owner','b-live-owner']:
            marker='budget-b-live-request-entered.json' if role=='b-live-owner' else 'budget-live-request-entered.json' if role=='live-owner' else 'budget-unknown-request-entered.json'
            save(marker,{'pid':os.getpid(),'run_id':invocation.run_id,'reservation_visible':await reservations()})
            await asyncio.Event().wait()
        return httpx.Response(200,json={'id':'probe-http-substitute-'+str(number),'object':'chat.completion','created':1,'model':'probe:no-real-model',
            'choices':[{'index':0,'message':{'role':'assistant','content':'{"verdict":"needs_review","confidence":0.5,"rationale":"Synthetic HTTP transport substitute; no model quality claim."}'},'finish_reason':'stop'}]})
    http_client=httpx.AsyncClient(transport=httpx.MockTransport(transport))
    real_factory=agent.make_chat_model
    agent.make_chat_model=lambda *a,**k:real_factory(*a,http_async_client=http_client,**k)
    contract.record_llm_call=lambda *a,**k:None  # A synthetic reply is not real usage/cost.
    class Reader:
        async def fetch_organisation_memory(self,*args):return {'status':'not_requested','statements':[],'probe_only':True}
    class Worker(worker_module.FusedAlertTriageWorker):
        def __init__(self,alias,group=None):
            v=topicmap[alias]
            super().__init__(bootstrap_servers=bootstrap,topic=v['topic'],group_id=group or v['group'],dlq_topic=v['dlq'],max_attempts=1,entity_concurrency=1,context_reader=Reader())
            self.alias=alias;self.results=[]
            for method,kind in [('_attach_tenant_skill','tenant_skill_read'),('_attach_runbooks','knowledge_base_read'),
                                ('_attach_recent_dispositions','recent_dispositions_read'),('_attach_identity_context','identity_context_read')]:
                async def attach(s,kind=kind):setattr(s,kind,{'status':'not_requested','probe_only':True})
                setattr(self,method,attach)
        async def _process_with_retry(self,message):
            n=len(list(E.glob('budget-delivery-*.json')))+1;assert n<=16
            save('budget-delivery-'+str(n)+'.json',{'alias':self.alias,'pid':os.getpid(),'run_id':ids[self.alias].run_id})
            return await super()._process_with_retry(message)
        async def triage(self,message):
            result=await super().triage(message);self.results.append(result);return result
    async def launch(worker):
        task=asyncio.create_task(worker.start())
        for _ in range(200):
            if task.done():return task
            if worker._consumer and worker._consumer.assignment():return task
            await asyncio.sleep(.05)
        raise AssertionError('No assignment; do not republish')
    async def join_stopped(worker,task):
        await worker.stop()
        try:await asyncio.wait_for(task,5)
        except (asyncio.CancelledError,ledger.LedgerPersistError):pass
        assert worker._lanes.in_flight==0
    async def until(alias,task,expected):
        for _ in range(200):
            if task.done():await task
            if (await offsets(alias))['committed']==expected:return
            await asyncio.sleep(.05)
        raise AssertionError('Offset not confirmed; no replay')
    async def completed(alias,*,republish=True,cold=False):
        group=topicmap[alias]['group']+'.cold' if cold else None
        worker=Worker(alias,group);task=await launch(worker)
        if republish:await publish(alias)
        for _ in range(200):
            if task.done():await task
            if (await offsets(alias,group))['committed']==1:break
            await asyncio.sleep(.05)
        else:raise AssertionError('Completed offset not confirmed')
        await join_stopped(worker,task)
        assert len(worker.results)==1
        save('budget-result-'+alias+('-cold' if cold else '-resume' if not republish else '')+'.json',worker.results[0])
    async def held(alias,*,republish):
        worker=Worker(alias);task=await launch(worker)
        if republish:await publish(alias)
        try:await asyncio.wait_for(task,25)
        except ledger.LedgerPersistError:pass
        else:raise AssertionError('Budget hold must stop the consumer window')
        await worker.stop()
        actual=await offsets(alias)
        assert actual=={'committed':0,'end':1} and not await runs(alias)
        suffix='-live' if role=='live-loser' else ''
        save('budget-held-'+alias+suffix+'.json',{'offset':actual,'reservations':await reservations(),'run_created':False,'dlq_or_model':False})
    async def child(name):
        log=E/('budget-child-'+name+'.log');assert not log.exists()
        with log.open('xb') as f:p=await asyncio.create_subprocess_exec(sys.executable,__file__,'child',name,stdout=f,stderr=asyncio.subprocess.STDOUT)
        log.chmod(0o600);save('budget-child-'+name+'-spawned.json',{'pid':p.pid});return p
    async def join(p,name):
        try:code=await asyncio.wait_for(p.wait(),60)
        except BaseException:
            if p.returncode is None:p.kill();await p.wait()
            raise
        save('budget-child-'+name+'-exit.json',{'pid':p.pid,'exit_code':code});assert code==0
    try:
        if phase=='child' and role in ['unknown-owner','unknown-owner-recovered']:
            worker=Worker('a_unknown');task=await launch(worker)
            if role=='unknown-owner':await publish('a_unknown')
            else:assert (E/'budget-publish-a_unknown-ack.json').exists() and not await runs('a_unknown')
            await barrier('budget-unknown-stop-requested.json')
            started=time.monotonic();await join_stopped(worker,task)
            elapsed=time.monotonic()-started
            assert 9<=elapsed<=20 and await offsets('a_unknown')=={'committed':0,'end':1}
            rows=await reservations();row=next(r for r in rows if str(r['run_id'])==str(ids['a_unknown'].run_id))
            assert row['outcome']=='reserved' and row['settled_at'] is None and row['request_started_at'] is not None
            save('budget-unknown-stopped.json',{'seconds':elapsed,'offset':await offsets('a_unknown'),'reservation':row,'lanes_after_stop':worker._lanes.in_flight});return
        if phase=='child' and role=='concurrent-loser':
            await held('a_denied',republish=True);return
        if phase=='child' and role=='live-owner':
            assert not await runs('a_done') and not (E/'budget-publish-a_done-ack.json').exists()
            worker=Worker('a_done');task=await launch(worker);await publish('a_done')
            await barrier('budget-live-stop-requested.json')
            started=time.monotonic();await join_stopped(worker,task);elapsed=time.monotonic()-started
            assert 9<=elapsed<=20 and await offsets('a_done')=={'committed':0,'end':1}
            row=next(r for r in await reservations() if str(r['run_id'])==str(ids['a_done'].run_id))
            assert row['settled_at'] is None and row['request_started_at'] is not None
            save('budget-live-stopped.json',{'seconds':elapsed,'offset':await offsets('a_done'),'reservation':row,'lanes_after_stop':worker._lanes.in_flight});return
        if phase=='child' and role=='live-loser':
            assert await offsets('a_denied')=={'committed':0,'end':1}
            await held('a_denied',republish=False);return
        if phase=='child' and role=='b-live-owner':
            assert not await runs('b_denied') and await offsets('b_denied')=={'committed':0,'end':1}
            worker=Worker('b_denied');task=await launch(worker)
            await barrier('budget-b-live-stop-requested.json')
            started=time.monotonic();await join_stopped(worker,task);elapsed=time.monotonic()-started
            assert 9<=elapsed<=20 and await offsets('b_denied')=={'committed':0,'end':1}
            row=next(r for r in await reservations() if str(r['run_id'])==str(ids['b_denied'].run_id))
            assert row['settled_at'] is None and row['request_started_at'] is not None
            save('budget-b-live-stopped.json',{'seconds':elapsed,'offset':await offsets('b_denied'),'reservation':row,'lanes_after_stop':worker._lanes.in_flight});return
        if phase=='child' and role=='b-live-loser':
            await held('b_extra',republish=True);return
        if phase=='b-live-concurrency':
            assert (E/'budget-token-hold.json').exists() and (E/'budget-topup.json').exists()
            owner=await child('b-live-owner');await barrier('budget-b-live-request-entered.json')
            assert owner.returncode is None
            loser=await child('b-live-loser');await join(loser,'b-live-loser')
            assert owner.returncode is None and not await runs('b_extra')
            rows=await reservations();b=[r for r in rows if str(r['tenant_id'])==state['identities']['b']['tenant_id']]
            assert len(b)==2 and sum(r['settled_at'] is None for r in b)==1
            save('budget-b-live-stop-requested.json',{'owner_pid':owner.pid,'loser_pid':loser.pid,'both_processes_overlapped':True})
            await join(owner,'b-live-owner')
            save('budget-concurrency-complete.json',{'owner_pid':owner.pid,'loser_pid':loser.pid,'b_reserved':2,'loser_run_absent':True,'owner_pending_during_loser':True,'prior_A_unknowns_kept':True});return
        if phase=='live-concurrency':
            assert read('budget-expand-a.json')['prior_unknown_refunded_or_reclaimed'] is False
            assert len(await reservations())==2 and not await runs('a_done')
            owner=await child('live-owner');await barrier('budget-live-request-entered.json')
            assert owner.returncode is None
            loser=await child('live-loser');await join(loser,'live-loser')
            assert owner.returncode is None and not await runs('a_denied')
            rows=await reservations();a=[r for r in rows if str(r['tenant_id'])==state['identities']['a']['tenant_id']]
            assert len(a)==2 and all(r['settled_at'] is None for r in a)
            save('budget-live-stop-requested.json',{'owner_pid':owner.pid,'loser_pid':loser.pid,'both_processes_overlapped':True})
            await join(owner,'live-owner')
            save('budget-concurrency-complete.json',{'owner_pid':owner.pid,'loser_pid':loser.pid,'a_reserved':2,'a_loser_run_absent':True,'owner_pending_during_loser':True,'prior_unknown_kept':True});return
        if phase in ['concurrency','concurrency-recover']:
            if phase=='concurrency-recover':
                assert not (E/'budget-unknown-request-entered.json').exists() and not await reservations()
                assert await offsets('a_unknown')=={'committed':0,'end':1} and not await runs('a_unknown')
                save('budget-concurrency-recovery-preconditions.json',{'old_delivery_did_not_admit_or_start_request':True,'same_offset_no_republish':True,'fix':'probe DAC_OVERRIDE reads explicitly mounted UID10001 policy; resident already had access'})
            owner=await child('unknown-owner-recovered' if phase=='concurrency-recover' else 'unknown-owner');await barrier('budget-unknown-request-entered.json')
            # Tenant B progresses while A has an actual pending HTTP await.
            await completed('b_done')
            loser=await child('concurrent-loser');await join(loser,'concurrent-loser')
            rows=await reservations();a=[r for r in rows if str(r['tenant_id'])==state['identities']['a']['tenant_id']]
            assert len(a)==1 and a[0]['charged_tokens']==20000 and a[0]['settled_at'] is None
            save('budget-unknown-stop-requested.json',{'owner_pid':owner.pid})
            await join(owner,'unknown-owner-recovered' if phase=='concurrency-recover' else 'unknown-owner')
            save('budget-concurrency-complete.json',{'distinct_owner_loser_pids':True,'a_reserved':1,'a_loser_run_absent':True,'b_completed_while_a_pending':True});return
        if phase=='holds':
            await held('b_denied',republish=True)
            rows=await reservations();b=[r for r in rows if str(r['tenant_id'])==state['identities']['b']['tenant_id']]
            assert len(b)==1 and b[0]['settled_at'] is not None
            save('budget-token-hold.json',{'calls_before':1,'max_calls':3,'reserved_tokens_before':20000,'max_reserved_tokens':20000,'unsettled_before':0,'offset_retained':True});return
        if phase=='success':
            before=await reservations();calls=len(list(E.glob('budget-http-start-*.json')))
            await completed('b_done',republish=False,cold=True)
            assert await reservations()==before and len(list(E.glob('budget-http-start-*.json')))==calls
            save('budget-completed-cold-reused.json',{'no_new_reservation_or_request':True});return
        if phase=='resume':
            assert read('budget-topup.json')['only_change']=='tenant_b_max_reserved_tokens_20000_to_40000'
            before=len(list(E.glob('budget-http-start-*.json')))
            await completed('b_denied',republish=False)
            assert len(list(E.glob('budget-http-start-*.json')))==before+1
            save('budget-backlog-resumed.json',{'same_group_offset':await offsets('b_denied'),'republished':False,'new_http_model_substitute':1,'reservations':await reservations()});return
        if phase=='resume-extra':
            assert (E/'budget-allow-b-backlog.json').exists()
            before=len(list(E.glob('budget-http-start-*.json')))
            await completed('b_extra',republish=False)
            assert len(list(E.glob('budget-http-start-*.json')))==before+1
            save('budget-backlog-resumed.json',{'same_group_offset':await offsets('b_extra'),'republished':False,'new_http_model_substitute':1,'unknown_reservations_kept':True,'reservations':await reservations()});return
        if phase in ['stop','stop-live','stop-b']:
            before=len(list(E.glob('budget-http-start-*.json')))
            alias='a_unknown' if phase=='stop' else 'b_denied' if phase=='stop-b' else 'a_done'
            worker=Worker(alias);task=await launch(worker)
            await until(alias,task,1);await join_stopped(worker,task)
            assert len(list(E.glob('budget-http-start-*.json')))==before
            save('budget-'+alias+'-cold-recovery.json',{'offset':await offsets(alias),'new_http_requests':0,'confirmed_dlq':True,'reservation_unsettled_preserved':True});return
        if phase=='verify':
            rows=await reservations();assert len(rows)==5
            a=[r for r in rows if str(r['tenant_id'])==state['identities']['a']['tenant_id']]
            b=[r for r in rows if str(r['tenant_id'])==state['identities']['b']['tenant_id']]
            assert len(a)==2 and all(r['settled_at'] is None for r in a) and len(b)==3 and sum(r['outcome']=='responded' for r in b)==2
            assert all(r['observed_tokens'] is None for r in rows)
            # A stricter independent cap isolates call-count admission from
            # the already-tested active/token conditions; no Run is inserted.
            s=ids['a_denied'];fields=Worker._delivery_fields(s)
            try:await delivery.claim(**fields,budget=budget.Policy(86400,2,60000,3))
            except budget.BudgetHold:pass
            else:raise AssertionError('Call ceiling bypassed')
            assert not await runs('a_denied')
            other=await db(ids['b_done'].tenant_id,'SELECT run_id FROM socai2_triage_budget_reservations WHERE run_id=$1',ids['a_unknown'].run_id)
            assert not other
            # The immutable trigger protects the already-admitted charge.
            async with pool.acquire() as conn:
                async with conn.transaction():
                    await ledger._set_rls_context(conn,ids['a_unknown'].tenant_id)
                    try:
                        async with conn.transaction():await conn.execute('UPDATE socai2_triage_budget_reservations SET charged_tokens=1 WHERE run_id=$1',ids['a_unknown'].run_id)
                    except Exception:pass
                    else:raise AssertionError('Charge was mutable')
            assert await reservations()==rows
            summary={n:await offsets(n) for n in ALIASES}
            assert summary['a_denied']=={'committed':0,'end':1}
            assert all(summary[n]=={'committed':1,'end':1} for n in ['b_done','b_denied','a_unknown','a_done','b_extra'])
            counts={'publishes':len(list(E.glob('budget-publish-*-ack.json'))),'deliveries':len(list(E.glob('budget-delivery-*.json'))),'http_model_substitute_starts':len(list(E.glob('budget-http-start-*.json'))),'real_models':0}
            assert counts=={'publishes':6,'deliveries':14,'http_model_substitute_starts':5,'real_models':0},counts
            save('budget-verified.json',{'reservations':rows,'offsets':summary,'counts':counts,'call_cap_isolated':True,'token_cap_isolated':True,'concurrency_cap_isolated':True,'tenant_rls_rejects_cross_read':True,'charge_immutable':True,'unknown_not_reclaimed':True});return
        raise AssertionError((phase,role))
    finally:
        await http_client.aclose()


if __name__=='__main__':asyncio.run(main(*sys.argv[1:]))
