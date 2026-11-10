"""Optional-source SQL and real PG persistence; graph/product/lake transports are fakes."""
import asyncio
import importlib.util
import json
import os
import traceback
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2 import baseline_enrichment_sources as sources
from app.socai2 import baseline_evidence as evidence
from app.socai2 import baseline_evidence_tools as tools
from app.socai2 import baseline_optional_sources as optional
from app.socai2.baseline_contracts import Actor, Limits, Start
from app.socai2.baseline_executor import BaselineExecutor
from app.socai2.baseline_reasoning import evidence_candidates
from app.socai2.baseline_service import BaselineService
from app.socai2.baseline_store import A, C, F, R
from socai2_test_model_view import model_data
from sqlalchemy import insert, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker

T, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
ACTOR = Actor(user_id=USER, name="synthetic-source-review")


async def run_checks(engine, record, only=None):
    service = BaselineService(async_sessionmaker(engine, expire_on_commit=False))

    async def fixture(product=False,window=True,complete_executor=False):
        cid, aid, mid = uuid4(), uuid4(), uuid4()
        host, account, term = "source-"+uuid4().hex, "user-"+uuid4().hex, "sourceword"+uuid4().hex
        async with service.transaction(T) as store:
            now = await store.now()
            connector = uuid4() if product else None
            if connector:
                await store.db.execute(text("INSERT INTO public.connectors(id,tenant_id) VALUES (:id,:tenant)"), {"id":connector,"tenant":T})
            await store.db.execute(insert(C).values(id=cid, tenant_id=T, title="synthetic optional sources"))
            await store.db.execute(insert(A).values(id=aid, tenant_id=T, title=term,
                source_namespace="source-fixture", source_identity_key=str(aid), connector_id=connector,
                connector_type="crowdstrike" if connector else None))
            await store.db.execute(insert(m.AlertMaterials.__table__).values(id=mid, tenant_id=T, alert_id=aid,
                revision=1, ocsf_json={"class_uid":3002,"actor":{"user":{"name":account}},"device":{"name":host}},
                detection={}, source_scope={}, retention={}, material_state="complete"))
            await store.db.execute(update(A).where(A.c.id==aid).values(latest_material_id=mid))
            for typ,value in [("host",host),("user",account)]:
                await store.db.execute(insert(m.AlertObjects.__table__).values(id=uuid4(),tenant_id=T,alert_id=aid,
                    material_id=mid,object_key=typ+":"+value,namespace="source-fixture",object_type=typ,
                    object_role="entity",raw_value=value,normalized_value=value,source_path="$.synthetic."+typ,attributes={}))
            out = await store.replace_members(cid,{aid},expected_revision=0,actor=ACTOR,operation_id=uuid4())
        rid = UUID(out["pending_run_id"])
        async with service.transaction(T) as store:
            await store.claim(cid,rid,Start(operation_key=uuid4(),expected_scope_revision=1,
                window_start=now-timedelta(minutes=5) if window else None,
                window_end=now+timedelta(minutes=5) if window else None),actor=ACTOR,
                executor_version="socai2.baseline-executor.v1" if complete_executor else "source-fixture",
                limits=Limits(max_model_calls=4,max_tool_calls=4,max_tokens=24000,
                    max_rows_per_query=20,deadline_at=now+timedelta(seconds=120),policy_version="source-fixture"))
        return SimpleNamespace(cid=cid,rid=rid,aid=aid,mid=mid,host=host,account=account,term=term,
            now=now,connector=connector,context=await service.read_context(T,cid,rid))

    async def artifact(identity):
        async with service.transaction(T,readonly=True) as store:
            return (await store.one(select(F).where(F.c.id==identity)))["content_json"]

    def flags(*enabled):
        return patch.dict(os.environ,{"SOCAI2_SOURCE_"+name.upper()+"_ENABLED":"true" if name in enabled else "false"
            for name in ["ueba","knowledge","graph","product_host"]})

    async def enrich(f,source):
        with flags(source), patch.object(sources,"CONNECTED",frozenset()):
            summary = await service.enrich(T,f.cid,f.rid)
        item = next(s for s in summary["sources"] if s["source"]==source)
        return summary,item,await artifact(UUID(item["artifact_id"]))

    async def test_optional_source_selectors_preserve_namespaces():
        f=await fixture()
        keys=sources.selectors(f.context,"ueba")
        assert len(keys)==1 and keys[0]["value"]==f.account and keys[0]["namespace"]=="source-fixture"
        assert keys==sources.selectors(f.context,"graph")
        assert sources.selectors(f.context,"knowledge")[0]["value"]==f.term
        with flags():
            assert not sources.connected("graph") and not sources.connected("knowledge")
        f.context.alerts[str(f.aid)].objects[1]["namespace"]=""
        assert sources.selectors(f.context,"ueba")==[]
        f.context.alerts[str(f.aid)].alert["title"]="x"*300
        key=sources.selectors(f.context,"knowledge")[0]
        assert len(key["value"])==256 and key["source_paths"][0]["query_text_truncated"]
        assert key["source_paths"][0]["original_characters"]==300

    async def test_authentication_sql_database_and_bound_rows():
        f=await fixture()
        with patch.dict(os.environ,{"SOCAI2_LAKE_DATABASE":"socai2_next_validation"}):
            catalog=tools.catalog(f.context,T)
            binding=next(b for b in catalog["bindings"].values() if b["tool_name"]=="authentication_activity")
            args={"tool_name":"authentication_activity","contract_version":tools.VERSION,
                "scope":binding["scope"],"limit":20,"parameters":{"tenant_id":str(T),"hostname":f.host,
                    "source_database":binding["source_database"]}}
            sql,params=tools.query_sql(args)
            assert "FROM socai2_next_validation.raw_events" in sql and params["class_uid"]==3002
            assert params["tenant_id"]==str(T) and params["hostname"]==f.host
            args["parameters"]["source_database"]="aisoc"
            try:
                tools.query_sql(args)
            except ValueError as exc:
                assert str(exc)=="frozen_lake_database_changed"
            else:
                raise AssertionError("database mismatch accepted")
        with patch.dict(os.environ,{"SOCAI2_LAKE_DATABASE":"aisoc; DROP TABLE x"}):
            try:
                optional.lake_database()
            except ValueError:
                pass
            else:
                raise AssertionError("invalid identifier accepted")

    async def test_ueba_real_sql_tenant_scope_role_and_replay():
        f=await fixture()
        for tenant in (T,OTHER):
            async with service.transaction(tenant) as store:
                await store.db.execute(text("""INSERT INTO public.user_risk_profiles
                    (id,tenant_id,external_user_ref,risk_score,risk_tier,failed_auth_24h,off_hours_events_7d,
                     peer_anomaly_score,last_evaluated_at,updated_at)
                    VALUES (:id,:tenant,:account,NULL,'unknown',2,1,NULL,:now,:now)"""),
                    {"id":uuid4(),"tenant":tenant,"account":f.account,"now":f.now})
        summary,item,raw=await enrich(f,"ueba")
        assert item["outcome"]=="data" and len(raw["rows"])==1
        assert raw["rows"][0]["record"]["risk_score"] is None
        assert set(item["citation_roles"].values())=={"prior_analysis"}
        model=await service.prepare_model_view(T,f.cid,f.rid)
        assert model["ready"]
        encoded=json.dumps(model,default=str)
        assert "prior_analysis" in encoded and "stored_prior_analysis_calculation_unverified" in encoded
        async with service.transaction(T) as store:
            await store.db.execute(text("UPDATE public.user_risk_profiles SET risk_score=100 WHERE tenant_id=:tenant AND external_user_ref=:account"),
                {"tenant":T,"account":f.account})
        with flags("ueba"),patch.object(sources,"CONNECTED",frozenset()):
            assert await service.enrich(T,f.cid,f.rid)==summary
        assert (await artifact(UUID(item["artifact_id"])))["rows"][0]["record"]["risk_score"] is None

    async def test_knowledge_real_sql_guidance_tenant_and_no_match():
        f=await fixture()
        for tenant,kind in [(T,"runbook"),(OTHER,"runbook"),(T,"wiki")]:
            async with service.transaction(tenant) as store:
                await store.db.execute(text("""INSERT INTO public.aisoc_kb_documents
                    (id,tenant_id,title,doc_kind,source_url,chunk_index,chunk_total,content,created_at,updated_at)
                    VALUES (:id,:tenant,'synthetic runbook',:kind,'https://example.invalid/runbook',0,1,:content,:now,:now)"""),
                    {"id":uuid4(),"tenant":tenant,"kind":kind,"content":f.term+" synthetic investigation guidance","now":f.now})
        _,item,raw=await enrich(f,"knowledge")
        assert item["outcome"]=="data" and len(raw["rows"])==1
        assert raw["rows"][0]["record"]["doc_kind"]=="runbook"
        assert set(item["citation_roles"].values())=={"source_label"}
        other=await fixture()
        _,empty,raw=await enrich(other,"knowledge")
        assert empty["outcome"]=="empty" and raw["rows"]==[]

    async def test_identity_graph_counts_and_unavailable_are_distinct():
        f=await fixture()
        async def identity(tenant,accounts,limit):
            assert tenant==str(T) and accounts==[f.account] and limit==20
            return SimpleNamespace(status="success",identities=[{"identity_id":"fixture-person","account":f.account}],
                candidate_count=2,eligible_count=2,truncated_count=1,import_timestamp_missing=0)
        with patch("app.services.incident_context.read_identity_context_for_accounts",identity):
            _,item,raw=await enrich(f,"graph")
        assert item["outcome"]=="data" and item["truncated"] and len(raw["rows"])==1
        assert item["source_metadata"]["source_truncated_count"]==1
        f=await fixture()
        async def unavailable(*args,**kwargs):
            return SimpleNamespace(status="unavailable")
        with patch("app.services.incident_context.read_identity_context_for_accounts",unavailable):
            _,item,raw=await enrich(f,"graph")
        assert item["outcome"]=="unavailable" and raw["rows"] is None and raw["state"]=="failed"

    async def test_authentication_persisted_query_and_model_observation():
        f=await fixture()
        prepared=await service.prepare_evidence(T,f.cid,f.rid)
        bid=next(k for k,b in prepared["catalog"]["bindings"].items() if b["tool_name"]=="authentication_activity")
        class Gateway:
            def configured(self):
                return True
            async def query(self,args,query_id,timeout):
                row=dict.fromkeys(tools.FIELDS,"")
                row.update(event_id=str(uuid4()),event_time=args["scope"]["window_start"],class_uid=3002,
                    src_hostname=f.host,ocsf_json={"class_uid":3002,"actor":{"user":{"name":f.account}},
                        "activity":{"action":"logon","outcome":"failure"}})
                return [row]
        out=await service.query_evidence(T,f.cid,f.rid,bid,f.context.questions[0].id,gateway=Gateway())
        assert out["result"]["state"]=="completed"
        assert set(evidence.citation_roles(out["projection"]).values())=={"observation"}
        view=await service.prepare_evidence_view(T,f.cid,f.rid,f.context.questions[0].id)
        assert view["ready"] and "logon" in view["messages"][1]["content"]

    async def test_product_binding_disabled_and_no_implicit_retry():
        f=await fixture(product=True)
        prepared=await service.prepare_evidence(T,f.cid,f.rid)
        bid=next(k for k,b in prepared["catalog"]["bindings"].items() if b["tool_name"]=="product_host_details")
        binding=prepared["catalog"]["bindings"][bid]
        assert binding["connector_id"]==str(f.connector) and binding["alert_ids"]==[str(f.aid)]
        with flags():
            out=await service.query_evidence(T,f.cid,f.rid,bid,f.context.questions[0].id)
        assert out["result"]["state"]=="skipped" and out["result"]["rows"] is None
        with flags("product_host"):
            assert await service.query_evidence(T,f.cid,f.rid,bid,f.context.questions[0].id)==out

    async def test_product_snapshot_stays_source_label_and_scope_checked():
        f=await fixture(product=True,window=False)
        prepared=await service.prepare_evidence(T,f.cid,f.rid)
        bid=next(k for k,b in prepared["catalog"]["bindings"].items() if b["tool_name"]=="product_host_details")
        class Gateway:
            def configured(self):
                return True
            async def query(self,args,query_id,timeout):
                assert args["parameters"]["connector_id"]==str(f.connector)
                row=dict.fromkeys(tools.PRODUCT_FIELDS,None)
                row.update(device_id="synthetic-device",hostname=f.host,source_connector_id=str(f.connector),
                    upstream_request_id="synthetic-product-request",observed_at=f.now.isoformat(),platform="Linux")
                return [row]
        out=await service.query_evidence(T,f.cid,f.rid,bid,f.context.questions[0].id,gateway=Gateway())
        assert set(evidence.citation_roles(out["projection"]).values())=={"source_label"}
        view=await service.prepare_evidence_view(T,f.cid,f.rid,f.context.questions[0].id)
        product=[s["ref"] for s in view["source_map"].values() if s["ref"]["id"]==out["projection_id"]]
        assert product and all(r["role"]=="source_label" for r in product)
        _,candidates=evidence_candidates(view)
        product_candidates=[c for c in candidates if c["source"]["ref"]["id"]==out["projection_id"]]
        assert product_candidates and all(c["entry"]["role"]=="source_label" for c in product_candidates)
        snapshot=await service.build_graph(T,f.cid,f.rid)
        assert snapshot["omissions"]["current_snapshot_not_activity"]==1
        assert any(q["projection_id"]==out["projection_id"] and q["tool_name"]=="product_host_details" for q in snapshot["queries"])
        assert all(ref["id"]!=out["projection_id"] for edge in snapshot["graph"]["edges"] for ref in edge["source_refs"])
        wrong={**out["result"]["rows"][0],"hostname":"wrong-host"}
        try:
            tools.validate_rows([wrong],out["result"]["actual_args"])
        except ValueError:
            pass
        else:
            raise AssertionError("wrong host accepted")

    async def test_known_source_failure_preserves_running_without_empty_success():
        f=await fixture(product=True)
        prepared=await service.prepare_evidence(T,f.cid,f.rid)
        bid=next(k for k,b in prepared["catalog"]["bindings"].items() if b["tool_name"]=="product_host_details")
        class Gateway:
            def configured(self):
                return True
            async def query(self,*args):
                raise optional.SourceUnavailable("source_credentials_missing")
        out=await service.query_evidence(T,f.cid,f.rid,bid,f.context.questions[0].id,gateway=Gateway())
        assert out["result"]["state"]=="failed" and out["result"]["rows"] is None
        async with service.transaction(T,readonly=True) as store:
            assert (await store.one(select(R).where(R.c.id==f.rid)))["state"]=="running"

    async def test_product_gateway_exact_binding_and_transport_uncertainty():
        f=await fixture(product=True,window=False)
        args={"tool_name":"product_host_details","parameters":{"tenant_id":str(T),
            "source_alert_id":str(f.aid),"connector_id":str(f.connector),"hostname":f.host,"case_id":str(f.cid)}}
        async def returned(tool,received):
            assert tool.tenant_id==T and tool.case_id==str(f.cid)
            assert tool.bindings=={str(f.aid):{"connector_id":str(f.connector),"hosts":[f.host]}}
            assert received=={"source_alert_id":str(f.aid),"hostname":f.host}
            row={key:None for key in tools.PRODUCT_FIELDS if key not in {"source_connector_id","upstream_request_id","observed_at"}}
            row.update(device_id="synthetic-device",hostname=f.host)
            return {"available":True,"rows":[row],"upstream_request_id":"synthetic-upstream","observed_at":f.now.isoformat()}
        with flags("product_host"),patch("app.investigation_v2.case_product_tools.ProductHostTool.execute",returned):
            out=await tools.LakeGateway(service).query(args,str(uuid4()),10)
        assert out[0]["source_connector_id"]==str(f.connector) and out[0]["upstream_request_id"]=="synthetic-upstream"
        async def failure(tool,received):
            return {"available":False,"reason":"product_query_failed"}
        with flags("product_host"),patch("app.investigation_v2.case_product_tools.ProductHostTool.execute",failure):
            try:
                await tools.LakeGateway(service).query(args,str(uuid4()),10)
            except RuntimeError as exc:
                assert str(exc)=="product_dispatch_uncertain"
            else:
                raise AssertionError("uncertain dispatch became successful empty data")

    async def test_complete_executor_reserves_evidence_budget_without_increase():
        f=await fixture(complete_executor=True)
        with flags("ueba","knowledge"),patch.object(sources,"CONNECTED",frozenset({"history"})):
            summary=await service.enrich(T,f.cid,f.rid)
        by_name={item["source"]:item for item in summary["sources"]}
        assert by_name["history"]["outcome"]=="empty" and by_name["ueba"]["outcome"]=="empty"
        assert by_name["knowledge"]["outcome"]=="not_attempted_budget"
        assert by_name["knowledge"]["reason"]=="tool_budget_reserved_for_evidence"
        prepared=await service.prepare_evidence(T,f.cid,f.rid)
        binding_ids=[key for key,value in prepared["catalog"]["bindings"].items()
            if value["tool_name"] in {"authentication_activity","process_activity"}]
        class Gateway:
            calls=0
            def configured(self):
                return True
            async def query(self,args,query_id,timeout):
                self.calls+=1
                assert args["parameters"]["hostname"]==f.host and timeout>0
                return []
        gateway=Gateway()
        for bid in binding_ids:
            out=await service.query_evidence(T,f.cid,f.rid,bid,f.context.questions[0].id,gateway=gateway)
            assert out["result"]["state"]=="completed" and out["result"]["rows"]==[]
        network=next(key for key,value in prepared["catalog"]["bindings"].items() if value["tool_name"]=="network_connections")
        stopped=await service.query_evidence(T,f.cid,f.rid,network,f.context.questions[0].id,gateway=gateway)
        assert stopped["result"]["state"]=="skipped" and stopped["projection"]["reason"]=="tool_budget_exhausted"
        assert gateway.calls==2
        async with service.transaction(T,readonly=True) as store:
            steps=(await store.db.execute(select(m.RunSteps.__table__).where(m.RunSteps.run_id==f.rid,
                m.RunSteps.kind=="tool",m.RunSteps.state.not_in(["planned","skipped"])))).mappings().all()
            run=await store.one(select(R).where(R.c.id==f.rid))
        assert len(steps)==4 and run["limits"]["max_tool_calls"]==4

    async def test_product_deep_default_gateway_without_history_window():
        spec=importlib.util.spec_from_file_location("source_c3_fixture",Path(__file__).with_name("test_socai2_baseline_analysis.py"))
        helper=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        for executor_path in (False,True):
            f=await fixture(product=True,window=False,complete_executor=executor_path)
            calls=[]
            async def returned(tool,received,fixture=f,seen=calls):
                assert tool.db is not None and tool.tenant_id==T and tool.case_id==str(fixture.cid)
                assert received=={"source_alert_id":str(fixture.aid),"hostname":fixture.host}
                seen.append(received)
                row={key:None for key in tools.PRODUCT_FIELDS if key not in {"source_connector_id","upstream_request_id","observed_at"}}
                row.update(device_id="synthetic-device",hostname=fixture.host)
                return {"available":True,"rows":[row],
                    "upstream_request_id":"synthetic-deep-product","observed_at":fixture.now.isoformat()}
            class Decision:
                provider,model="synthetic","synthetic-product-deep-no-network"
                async def configure(self,*args):
                    return True
                async def measure(self, body, stage):
                    from socai2_test_model_view import synthetic_measure
                    return await synthetic_measure(body, stage)

                async def complete(self,body,timeout):
                    data=model_data(body["messages"][1]["content"])
                    if not data["queries"]:
                        assert [o["tool_name"] for o in data["tool_options"]]==["product_host_details"]
                        reply={"question_id":data["question"]["id"],"action":"query",
                            "binding_id":data["tool_options"][0]["id"],"reason":"synthetic current host lookup","answer":None}
                    else:
                        assert not data["tool_options"]
                        assert data["queries"][0]["observed_rows_in_bounded_fetch"]==1
                        product_items=[item for item in data["items"] if isinstance(item["value"],dict)
                            and item["value"].get("name","").startswith("product_")]
                        assert product_items and all(item["role"]=="source_label" for item in product_items)
                        reply={"question_id":data["question"]["id"],"action":"handoff","binding_id":None,
                            "reason":"current snapshot cannot prove historical behavior","answer":{
                                "state":"unresolved","text":"Historical authorization still requires confirmation",
                                "support_ids":[],"counter_ids":[],"alternatives":[],
                                "limitations":["current product state is not historical activity"]}}
                    return {"id":"synthetic-deep-product","choices":[{"finish_reason":"stop","message":{
                        "role":"assistant","content":json.dumps(reply)}}],
                        "usage":{"prompt_tokens":500,"completion_tokens":500,"total_tokens":1000}}
            with flags("product_host"),patch.object(sources,"CONNECTED",frozenset()), \
                 patch("app.investigation_v2.case_product_tools.ProductHostTool.execute",returned), \
                 patch.object(tools.LakeGateway,"unavailable_reason",lambda *args:None):
                await service.enrich(T,f.cid,f.rid)
                initial=await service.analyze(T,f.cid,f.rid,gateway=helper.SyntheticGateway())
                assert initial["state"]=="completed"
                decision=Decision()
                lake=BaselineExecutor(service,T,gateway=decision).lake if executor_path else None
                out=await service.deepen(T,f.cid,f.rid,f.context.questions[0].id,gateway=decision,lake=lake)
            assert out["stop_reason"]=="handoff" and len(calls)==1 and len(out["iterations"])==2, out
            async with service.transaction(T,readonly=True) as store:
                rows=(await store.db.execute(select(F).where(F.c.run_id==f.rid,F.c.kind=="tool_response"))).mappings().all()
            receipts=[r["content_json"] for r in rows if r["content_json"]["tool_name"]=="product_host_details"]
            assert len(receipts)==1 and receipts[0]["state"]=="completed"

    checks=[test_optional_source_selectors_preserve_namespaces,test_authentication_sql_database_and_bound_rows,
        test_ueba_real_sql_tenant_scope_role_and_replay,test_knowledge_real_sql_guidance_tenant_and_no_match,
        test_identity_graph_counts_and_unavailable_are_distinct,test_authentication_persisted_query_and_model_observation,
        test_product_binding_disabled_and_no_implicit_retry,test_product_snapshot_stays_source_label_and_scope_checked,
        test_known_source_failure_preserves_running_without_empty_success,test_product_gateway_exact_binding_and_transport_uncertainty,
        test_complete_executor_reserves_evidence_budget_without_increase,test_product_deep_default_gateway_without_history_window]
    for check in checks:
        if only is not None and check.__name__ not in only:
            continue
        try:
            detail=await asyncio.wait_for(check(),180)
            record(check.__name__,True,detail)
        except Exception:  # noqa: BLE001 -- preserve original synthetic failures
            record(check.__name__,False,traceback.format_exc())
