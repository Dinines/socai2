"""Explicit model/tokenizer substitute for step 4 direct workflow and HTTP integration."""
import asyncio
import json
import re
from app.models import socai2 as m
from jsonschema import Draft202012Validator
from socai2_test_model_view import synthetic_measure
from sqlalchemy import select

class Gateway:
    def __init__(self, service, tenant, calls=None):
        self.service, self.tenant = service, tenant
        self.calls = calls if calls is not None else []
        self.behaviors = {}
        self.entered, self.release = asyncio.Event(), asyncio.Event()
        self.release.set()

    async def rows(self, model):
        table = model.__table__
        async with self.service.transaction(self.tenant, readonly=True) as store:
            return [dict(row) for row in (await store.db.execute(select(table).where(table.c.tenant_id == self.tenant))).mappings()]

    provider, model = 'controlled', 'controlled-A-I'
    async def configure(self,*_):
        return True
    async def measure(self,body,stage):
        measurement = await synthetic_measure(body,stage)
        if stage == 'I':
            active = [r for r in await self.rows(m.Runs) if r['state'] == 'running']
            if active and self.behaviors.get(active[0]['incident_id']) == 'capacity':
                measurement.update(context_fits=False, reserved_total_tokens=measurement['context_tokens']+1)
        return measurement
    async def complete(self,body,timeout):
        attempts=[a for a in await self.rows(m.AnalysisAttempts) if a['local_state']=='running']
        assert len(attempts)==1
        attempt=attempts[0]
        run=next(x for x in await self.rows(m.Runs) if x['id']==attempt['run_id'])
        assert attempt['input_artifact_id']==run['input_artifact_id'] and attempt['policy_artifact_id']
        behavior = self.behaviors.get(run['incident_id'])
        if behavior == 'hold':
            self.entered.set()
            await self.release.wait()
        if behavior in {'read_timeout','connect_timeout'}:
            import httpx
            from app.socai2.model_errors import ModelCallError, provider_error
            exc = httpx.ReadTimeout('controlled response timeout') if behavior == 'read_timeout' else httpx.ConnectTimeout('controlled not sent')
            raise ModelCallError(provider_error(exc, None))
        if run['kind']=='alert_basic':
            ids=re.findall(r'\[(N\d+_S\d+)｜原始记录\]',body['messages'][1]['content'])
            answer={'verdict':'needs_review','confidence':.3,'rationale':'Synthetic process observed; authorization is not established.',
                    'evidence_ids':ids[:2],'recommendations':[]}
        else:
            request=next(x['content_json'] for x in await self.rows(m.Artifacts) if x['run_id']==run['id'] and x['kind']=='model_request')
            members=request['incident_boundary']['member_aliases']
            sources=request['source_map']
            selected={aid:next(s for s,item in sources.items() if item['alert_ids']==[aid] and item['ref']['role']=='observation') for aid in members}
            answer={'diagnosis':{'summary':'Synthetic selected member assessment.','conclusion':'Authorization remains unresolved.',
                                'source_ids':list(selected.values())[:2],'limitations':[]},
                    'members':[{'alert_ref':alias,'state':'unresolved','assessment':'Observed process requires authorization verification.',
                                'source_ids':[selected[aid]],'limitations':[]} for aid,alias in members.items()],
                    'findings':[],'open_questions':[]}
        Draft202012Validator(body['response_format']['json_schema']['schema']).validate(answer)
        payload={'id':'controlled-'+str(run['id']),'choices':[{'finish_reason':'stop','message':{'content':json.dumps(answer)}}],
                 'usage':{'prompt_tokens':120,'completion_tokens':80,'total_tokens':200}}
        self.calls.append({'task_id':attempt['task_id'],'run_id':run['id'],'request':body,'response':payload})
        return payload
