"""Page-data source boundaries and reproducible counts; no network or models."""
import copy
import unittest
from unittest.mock import AsyncMock
from uuid import UUID

from app.socai2.baseline_store import StoreError, digest
from app.socai2.case_data import evidence_view, validate_sources
from app.socai2.case_data_contracts import EvidenceIndex
from pydantic import ValidationError


class PageDataHTTPTest(unittest.IsolatedAsyncioTestCase):
    async def test_page_data_routes_use_authenticated_tenant_actor_and_permissions(self):
        from app.api.v1.deps import CurrentUser, get_current_user
        from app.api.v1.endpoints import socai2_cases as api
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        app=FastAPI();app.include_router(api.router,prefix='/api/v1')
        principal=CurrentUser(UUID(int=3),TEN,'admin','synthetic@example.test',scopes=['cases:read'])
        service=AsyncMock()
        service.read_page_data.return_value={'schema_version': 'socai2.case-page-data.v1','classification': None,
            'due_at': None,'determination': None,'assessment': None,'evidence': {'artifact_id': None,'state': 'not_recorded',
            'evidence_count': None,'threat_count': None,'covered_alert_ids': [],'uncovered_alert_ids': [],
            'excluded_evidence_ids': [],'limitations': [],'entries': [],'index': None}}
        service.update_page_data.return_value={'case_id': CASE,'row_version': 2,'changed': True,'current_evidence_artifact_id': None}
        app.dependency_overrides[get_current_user]=lambda:principal
        app.dependency_overrides[api.get_service]=lambda:service
        path=f'/api/v1/socai2/cases/{CASE}/page-data'
        body={'operation_key': str(UUID(int=99)),'expected_row_version': 1,'classification': 'informational',
            'due_at': '2026-11-12T17:00:00+08:00','source': 'manual','source_note': 'contract test'}
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://synthetic.local') as client:
            response=await client.get(path)
            self.assertEqual(response.status_code,200)
            self.assertIsNone(response.json()['evidence']['evidence_count'])
            service.read_page_data.assert_awaited_once_with(TEN,CASE)
            self.assertEqual((await client.patch(path,json=body)).status_code,403)
            principal.scopes=['cases:write']
            self.assertEqual((await client.patch(path,json=body)).status_code,200)
            args,kwargs=service.update_page_data.await_args
            self.assertEqual(args[:2],(TEN,CASE));self.assertEqual(kwargs['actor'].user_id,principal.user_id)
            self.assertEqual((await client.patch(path,json=dict(body,classification='unknown'))).status_code,422)
            self.assertEqual((await client.patch(path,json=dict(body,due_at='2026-11-12T17:00:00'))).status_code,422)
            principal.scopes=['cases:read']
            publish={'operation_key': str(UUID(int=98)),'expected_row_version': 1,'expected_current_artifact_id': None,
                'index': {'schema_version': 'socai2.case-evidence.v1','scope_revision': 1,'alert_ids': [],
                    'supersedes_artifact_id': None,'availability_state': 'available','limitations': [],'entries': []}}
            self.assertEqual((await client.post(f'/api/v1/socai2/cases/{CASE}/evidence-index',json=publish)).status_code,403)
            service.publish_evidence.assert_not_awaited()

TEN, CASE = UUID(int=1), UUID(int=2)
AIDS = [UUID(int=10+i) for i in range(4)]


def fixture():
    rows, entries = {}, []
    for i, (aid, verdict) in enumerate(zip(AIDS, ["malicious", "malicious", "clean", "unknown"])):
        mid = UUID(int=100+i)
        threat = {"namespace":"test", "key":"shared" if i<2 else "clean-only", "label":"Same label"}
        rows[("alert_material",mid)] = {"id":mid,"tenant_id":TEN,"alert_id":aid,
            "raw_json":{"record_kind":"synthetic_page_data","event":"recorded", "evidence":{"verdict":verdict,"threat":threat}},
            "detection":{"rule_name":"Synthetic rule"}}
        ref=lambda path,role,mid=mid:{'type': "alert_material",'id': mid,'external': None,'source_path': path,'row_keys': [],'role': role}
        entries.append({'evidence_id': f"unit:{i}",'title': f"Item {i}",'type': "log",'alert_ids': [aid],'object_keys': [],
            'source_refs': [ref("/raw_json/event","observation")],'verdict': verdict,
            'verdict_sources': [] if verdict=="unknown" else [ref("/raw_json/evidence/verdict","source_label")],
            'threat': {**threat,"source_refs":[ref("/raw_json/evidence/threat","source_label")]} if i<3 else None,
            'remediation': None,'state': "active"})
    payload={'schema_version': "socai2.case-evidence.v1",'scope_revision': 1,'alert_ids': AIDS,
        'supersedes_artifact_id': None,'availability_state': "available",'limitations': [],'entries': entries}
    cas={'id': CASE,'tenant_id': TEN,'scope_revision': 1,'current_evidence_artifact_id': UUID(int=500)}
    return rows,payload,cas


class PageDataTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.rows,self.payload,self.cas=fixture()
        async def lookup(kind,identity):return self.rows.get((kind,identity))
        self.lookup=lookup

    async def view(self,payload=None,members=None):
        index=EvidenceIndex.model_validate(payload or self.payload)
        body=index.model_dump(mode="json")
        artifact={'id': self.cas['current_evidence_artifact_id'],'tenant_id': TEN,'case_id': CASE,
            'kind': "case_evidence_index",'schema_version': index.schema_version,'content_json': body,'sha256': digest(body)}
        return await evidence_view(self.cas,set(AIDS if members is None else members),artifact,self.lookup,{})

    async def test_counts_are_record_and_identity_counts(self):
        view=await self.view()
        self.assertEqual((view.state,view.evidence_count,view.threat_count),("available",4,1))
        self.assertEqual(len(view.entries),4)
        # Same label, distinct namespaced keys must not merge.
        row=self.rows[("alert_material",UUID(int=101))]
        row['raw_json']['evidence']['threat']['key']='other'
        self.payload['entries'][1]['threat']['key']='other'
        self.assertEqual((await self.view()).threat_count,2)

    async def test_missing_empty_withdrawn_partial_and_invalid_are_distinct(self):
        missing=await evidence_view(dict(self.cas,current_evidence_artifact_id=None),set(AIDS),None,self.lookup,{})
        self.assertEqual((missing.state,missing.evidence_count),("not_recorded",None))
        empty=copy.deepcopy(self.payload);empty['entries']=[]
        self.assertEqual((await self.view(empty)).evidence_count,0)
        for e in self.payload['entries']:e['state']='withdrawn'
        self.assertEqual((await self.view()).evidence_count,0)
        partial=await self.view(members={AIDS[0]})
        self.assertEqual((partial.state,partial.evidence_count),("partial",0))
        self.rows.pop(("alert_material",UUID(int=100)))
        invalid=await self.view()
        self.assertEqual((invalid.state,invalid.evidence_count),("invalid_reference",None))

    async def test_multi_member_scope_is_never_shrunk(self):
        first=self.payload['entries'][0]
        first.update(alert_ids=AIDS[:2],verdict='unknown',verdict_sources=[],threat=None)
        first['source_refs']+=self.payload['entries'][1]['source_refs']
        self.payload['entries']=[first]
        view=await self.view(members={AIDS[0]})
        self.assertEqual(view.evidence_count,0)
        self.assertEqual(view.excluded_evidence_ids,['unit:0'])
        self.assertEqual(view.index.entries[0].alert_ids,AIDS[:2])

    async def test_conflicting_labels_keep_both_sources_and_no_threat_count(self):
        row=self.rows[("alert_material",UUID(int=100))]
        row['raw_json']['alternate']={'verdict':'clean'}
        entry=self.payload['entries'][0]
        entry['verdict']='conflicting'
        entry['verdict_sources'].append(dict(entry['verdict_sources'][0],source_path='/raw_json/alternate/verdict'))
        self.payload['entries']=[entry]
        view=await self.view()
        self.assertEqual((view.evidence_count,view.threat_count),(1,0))
        self.assertEqual(len(view.entries[0].verdict_sources),2)
        row['raw_json']['alternate']['verdict']='malicious'
        await self.rejected(self.payload)

    async def rejected(self,payload):
        with self.assertRaises(StoreError):
            await validate_sources(EvidenceIndex.model_validate(payload),TEN,CASE,self.lookup,{})

    async def test_detection_label_cannot_become_observation(self):
        self.payload['entries'][0]['source_refs'][0]['source_path']='/detection/rule_name'
        await self.rejected(self.payload)

    async def test_observation_requires_registered_behavior_leaf(self):
        row=self.rows[("alert_material",UUID(int=100))]
        row['raw_json']['ocsf_event']={'severity_id':5,'finding_info':{'title':'Vendor label'},'process':{'cmd_line':'whoami'}}
        row['ocsf_json']=copy.deepcopy(row['raw_json']['ocsf_event'])
        ref=self.payload['entries'][0]['source_refs'][0]
        for root in ('/raw_json/ocsf_event','/ocsf_json'):
            for path in ('/severity_id','/finding_info/title','/process'):
                ref['source_path']=root+path
                await self.rejected(self.payload)
            ref['source_path']=root+'/process/cmd_line'
            await validate_sources(EvidenceIndex.model_validate(self.payload),TEN,CASE,self.lookup,{})
        row['ocsf_json']['process']['cmd_line']={'label':'Not a scalar behavior'}
        await self.rejected(self.payload)

    async def test_frozen_context_roles_and_member_paths_are_enforced(self):
        ident=UUID(int=700); a,b=map(str,AIDS[:2])
        self.rows[('artifact',ident)]={'id': ident,'tenant_id': TEN,'case_id': CASE,'alert_id': None,
            'kind': 'source_snapshot','schema_version': 'socai2.baseline-context.v1','material_state': 'complete',
            '_alert_ids': AIDS,'content_json': {'alerts':{a:{'triage':{'summary':'prior opinion'}},b:{'alert':{'title':'B'}}},
            'citation_roles':{f'$.alerts.{a}.triage':'prior_analysis',f'$.alerts.{b}.alert':'source_label'}}}
        ref={'type': 'artifact','id': ident,'external': None,'row_keys': [],'source_path': f'/content_json/alerts/{a}/triage','role': 'observation'}
        self.payload['entries'][0]['source_refs']=[ref]
        await self.rejected(self.payload)
        ref.update(role='source_label',source_path=f'/content_json/alerts/{b}/alert')
        await self.rejected(self.payload)
        ref.update(role='prior_analysis',source_path=f'/content_json/alerts/{a}/triage')
        await validate_sources(EvidenceIndex.model_validate(self.payload),TEN,CASE,self.lookup,{})

    async def test_model_request_is_not_a_response_receipt(self):
        ident=UUID(int=701)
        self.rows[('artifact',ident)]={'id': ident,'tenant_id': TEN,'case_id': CASE,'alert_id': None,
            'kind': 'model_request','schema_version': 'model.v1','material_state': 'complete','content_json': {'state':'executed'},'_alert_ids': AIDS}
        self.payload['entries'][0]['remediation']={'type': 'artifact','id': ident,'external': None,'row_keys': [],
            'source_path': '/content_json','role': 'execution_receipt'}
        await self.rejected(self.payload)

    async def test_verdict_threat_object_and_tenant_cannot_be_filled_without_source(self):
        for change in ('verdict','threat','object','tenant','path'):
            payload=copy.deepcopy(self.payload)
            if change=='verdict':payload['entries'][0]['verdict']='clean'
            elif change=='threat':payload['entries'][0]['threat']['key']='invented'
            elif change=='object':payload['entries'][0]['object_keys']=[{'material_id':UUID(int=100),'object_key':'missing'}]
            elif change=='tenant':self.rows[('alert_material',UUID(int=100))]['tenant_id']=UUID(int=9)
            else:payload['entries'][0]['source_refs'][0]['source_path']='/raw_json/missing'
            await self.rejected(payload)
            self.rows[('alert_material',UUID(int=100))]['tenant_id']=TEN

    def test_duplicate_ids_and_unscoped_entries_are_invalid(self):
        for change in ('duplicate','scope','blank'):
            payload=copy.deepcopy(self.payload)
            if change=='duplicate':payload['entries'][1]['evidence_id']=payload['entries'][0]['evidence_id']
            elif change=='scope':payload['entries'][0]['alert_ids']=[]
            else:payload['entries'][0]['threat']['namespace']='   '
            with self.assertRaises(ValidationError):EvidenceIndex.model_validate(payload)
