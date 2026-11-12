"""Page field/relationship/ledger reads against isolated synthetic PostgreSQL."""
import asyncio
import traceback
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID, uuid4

from app.api.v1.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import socai2_pages as api
from app.models import socai2 as m
from app.models.asset import Asset
from app.socai2 import page_reader
from app.socai2.baseline_contracts import Actor, Limits, Start
from app.socai2.page_contracts import SubjectPage, SubjectView, TraceView
from app.socai2.page_reader import PageReadService
from app.socai2.stage_result_contracts import AlertOutput
from app.socai2.stage_results import StageResultService, artifact
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker

T, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
NOW = datetime(2026, 11, 4, 0, 0, tzinfo=UTC)
LIMITS = Limits(max_model_calls=0, max_tokens=0, max_tool_calls=0, max_rows_per_query=0,
    deadline_at=None, policy_version="synthetic.page")


async def run_checks(engine, record, only=None, fixture_engine=None):
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    writer, reader = StageResultService(sessions), PageReadService(sessions)
    principal = CurrentUser(USER, T, "analyst", "synthetic@example.invalid", scopes=["alerts:read", "cases:read"])
    app = FastAPI()
    app.include_router(api.router, prefix="/api/v1")
    async def user():
        return principal
    app.dependency_overrides[get_current_user] = user
    app.dependency_overrides[api.get_service] = lambda: reader
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local")

    async def get(path, status=200):
        response = await client.get("/api/v1/socai2/" + path)
        assert response.status_code == status, (response.status_code, response.text)
        return response.json()

    async def fixture():
        aids, mids, iid = [uuid4(), uuid4()], [uuid4(), uuid4()], uuid4()
        host = "synthetic-page-" + str(iid)
        async with writer.transaction(T) as s:
            for index, (aid, mid) in enumerate(zip(aids, mids, strict=True)):
                await s.db.execute(insert(m.Alerts).values(id=aid, tenant_id=T, title="synthetic page " + str(index),
                    source_namespace="page-review", source_identity_key=str(aid), source_alert_id="ingress-"+str(index),
                    vendor_alert_id="vendor-"+str(index), connector_type="splunk", original_vendor=None,
                    handling_status="completed" if index == 0 else "new", disposition="false_positive" if index == 0 else "needs_review",
                    severity="critical" if index == 0 else "medium", event_time=None if index == 0 else NOW,
                    event_time_source="unknown" if index == 0 else "source", business_updated_at=NOW+timedelta(hours=index),
                    source_updated_at=NOW+timedelta(days=2), tags=["alert-only-tag"], owner_id=USER if index == 0 else None,
                    assignment_state="assigned" if index == 0 else "unassigned", priority_value=0 if index == 0 else None,
                    priority_state="available" if index == 0 else "not_provided", priority_source="synthetic" if index == 0 else None))
                await s.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=T, alert_id=aid, revision=1,
                    raw_json={"private_raw_marker": str(aid), "pid": 42}, enrichment={"raw": "stored"},
                    detection={"rule_id":"rule-1", "tactics":["Execution", "Execution"] + (["Persistence"] if index == 0 else []),
                        "techniques":["T1059"], "confidence_state":"not_computed", "confidence_value":None},
                    source_scope={"complete":False,"truncated":True}, retention={}, material_state="complete"))
                await s.db.execute(update(m.Alerts).where(m.Alerts.id == aid).values(latest_material_id=mid))
                await s.db.execute(insert(m.AlertObjects).values(id=uuid4(), tenant_id=T, alert_id=aid, material_id=mid,
                    object_key="host:"+host, namespace="page-review", object_type="host", source_type="source", object_role="entity",
                    raw_value=host, normalized_value=host, source_path="$.raw_json.host", attributes={}))
                await s.db.execute(insert(m.AlertSourceRefs).values(id=uuid4(), tenant_id=T, alert_id=aid, material_id=mid,
                    source_namespace="page-review", source_event_id="event-"+str(index), relation_kind="source_event"))
            await s.db.execute(insert(m.Incidents).values(id=iid, tenant_id=T, title="independent incident title",
                description="independent incident description", source_namespace="page-review", source_incident_id=str(iid),
                severity_override="low", severity_override_reason="synthetic override", severity_override_at=NOW,
                severity_override_by=USER, business_updated_at=NOW-timedelta(days=1), handling_status="new"))
            for aid in aids:
                await s.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=T, incident_id=iid, alert_id=aid,
                    membership_source="fusion", correlation_basis={"rule":"same-host"}, basis_version="synthetic", source_operation_id=uuid4()))
        return aids, mids, iid, host

    async def triage(aid, mid):
        claim = await writer.begin(T, "alert_basic", aid, uuid4(), producer="synthetic.page", limits=LIMITS)
        ref = {"type":"alert_material","id":mid,"external":None,"source_path":"$.raw_json.pid","row_keys":[],"role":"observation"}
        await writer.finish(T, claim["run_id"], AlertOutput(verdict="benign", rationale="same-round-rationale", confidence=0.96,
            score_state="available", explanation="saved explanation", generation_method="template", source_refs=[ref], recommendations=[], limitations=[]))
        return claim

    async def test_page_alert_fields_pairing_and_material():
        aids, mids, _iid, _ = await fixture()
        await triage(aids[0], mids[0])
        result = await get(f"alerts/{aids[0]}")
        SubjectView.model_validate(result)
        facts = result["facts"]
        assert facts["original_vendor"] is None and facts["source_alert_id"] == "ingress-0" and facts["vendor_alert_id"] == "vendor-0"
        assert facts["handling_status"] == "completed" and facts["disposition"] == "false_positive"
        assert facts["event_time"] is None and facts["event_time_source"] == "unknown" and Decimal(facts["priority_value"]) == 0
        async with writer.transaction(T, readonly=True) as s:
            owner = (await s.db.execute(text("SELECT username FROM public.users WHERE id=:id AND tenant_id=:tenant"),
                {"id":USER,"tenant":T})).scalar_one()
        assert result["owner_resolution"] == "resolved" and result["owner_name"] == owner
        assert result["triage"]["verdict"] == "benign" and result["triage"]["confidence_percent"] == 96
        assert result["triage"]["freshness"] == "current" and result["triage"]["valid_for_current_input"] and result["derived"]["false_positive"]
        assert "private_raw_marker" not in str(result) and "source_identity_key" not in str(result)
        assert result["material"]["source_scope"]["truncated"]
        body = await get(f"alerts/{aids[0]}/materials/{mids[0]}")
        assert body["content_json"]["raw_json"]["private_raw_marker"] == str(aids[0]) and body["availability"] == "available"
        await get(f"alerts/{aids[1]}/materials/{mids[0]}", 404)
        async with writer.transaction(T) as s:
            await s.db.execute(update(m.Alerts).where(m.Alerts.id == aids[0]).values(description="new source description"))
        assert (await get(f"alerts/{aids[0]}"))["triage"]["freshness"] == "stale"

    async def test_page_incident_aggregate_override_and_clock():
        aids, _, iid, _ = await fixture()
        result = await get(f"incidents/{iid}")
        d = result["derived"]
        assert result["facts"]["title"] == "independent incident title" and result["facts"]["handling_status"] == "new"
        assert d["member_count"] == 2 and d["unknown_event_time_count"] == 1 and d["object_count"] == 1
        assert d["severity_auto"] == "critical" and d["severity_effective"] == "low" and d["severity_group"] == "low"
        assert datetime.fromisoformat(d["first_activity_at"]) == NOW and datetime.fromisoformat(d["updated_at"]) == NOW+timedelta(hours=1)
        assert {v["label"]:v["alert_count"] for v in d["tactics"]} == {"Execution":2,"Persistence":1}
        members = await get(f"incidents/{iid}/records/members?limit=1")
        assert members["total"] == 2 and members["next_offset"] == 1 and len(members["items"]) == 1
        assert (await get(f"alerts/{aids[0]}"))["facts"]["severity"] == "critical"
        linked = await get(f"alerts/{aids[0]}/records/incidents")
        assert linked["items"][0]["id"] == str(iid)

    async def test_page_current_objects_sources_assets_and_neighbors():
        aids, _mids, iid, host = await fixture()
        asset, neighbor, wrong = uuid4(), uuid4(), uuid4()
        # Inventory is maintained by the backend. Seed only these synthetic
        # rows through an explicit fixture connection, keep the HTTP role unchanged.
        async with (fixture_engine or engine).begin() as conn:
            await conn.execute(insert(Asset.__table__).values(id=asset, tenant_id=T, name=host,
                tags=['inventory-tag'], ip_addresses=[]))
            await conn.execute(insert(Asset.__table__).values(id=uuid4(), tenant_id=OTHER, name=host,
                tags=['other-tenant-tag']))
        async with writer.transaction(T) as s:
            for aid, namespace in [(neighbor,"page-review"),(wrong,"different-environment")]:
                mid = uuid4()
                await s.db.execute(insert(m.Alerts).values(id=aid, tenant_id=T, title="synthetic neighbor", source_namespace=namespace, source_identity_key=str(aid)))
                await s.db.execute(insert(m.AlertMaterials).values(id=mid,tenant_id=T,alert_id=aid,revision=1,raw_json={},detection={},source_scope={},material_state="complete",retention={}))
                await s.db.execute(update(m.Alerts).where(m.Alerts.id == aid).values(latest_material_id=mid))
                await s.db.execute(insert(m.AlertObjects).values(id=uuid4(),tenant_id=T,alert_id=aid,material_id=mid,object_key="host:"+host,
                    namespace=namespace,object_type="host",source_type="source",object_role="entity",raw_value=host,normalized_value=host,
                    source_path="$.raw_json.host",attributes={}))
        assets = await get(f"incidents/{iid}/records/assets?limit=1")
        assert assets["total"] == 2 and assets["next_offset"] == 1
        assert assets["items"][0]["tags"] == ["inventory-tag"] and assets["items"][0]["asset_id"] == str(asset)
        related = await get(f"incidents/{iid}/records/related_alerts")
        assert [x["id"] for x in related["items"]] == [str(neighbor)]
        assert (await get(f"incidents/{iid}/records/sources"))["total"] == 2
        newmid = uuid4()
        async with writer.transaction(T) as s:
            await s.db.execute(insert(m.AlertMaterials).values(id=newmid,tenant_id=T,alert_id=aids[0],revision=2,raw_json={},detection={},source_scope={},material_state="complete",retention={}))
            await s.db.execute(update(m.Alerts).where(m.Alerts.id == aids[0]).values(latest_material_id=newmid))
        assert (await get(f"alerts/{aids[0]}/records/objects"))["total"] == 0
        assert (await get(f"alerts/{aids[0]}/records/sources"))["total"] == 0
        assert (await get(f"alerts/{aids[0]}/records/assets"))["total"] == 0

    async def test_page_relations_activity_comments_and_permissions():
        nonlocal principal
        aids, _, iid, _ = await fixture()
        cid, explicit = uuid4(), uuid4()
        async with writer.transaction(T) as s:
            for c in [cid, explicit]:
                await s.db.execute(insert(m.Cases).values(id=c,tenant_id=T,title="synthetic page case"))
        await writer.replace_members(T, cid, [aids[0]], expected_revision=0, actor=Actor(user_id=USER,name="synthetic"), operation_id=uuid4())
        activity_id, unrelated = uuid4(), uuid4()
        async with writer.transaction(T) as s:
            await s.db.execute(insert(m.CaseIncidents).values(id=uuid4(),tenant_id=T,case_id=explicit,incident_id=iid,source_operation_id=uuid4()))
            for act in [activity_id, unrelated]:
                await s.db.execute(insert(m.Activities).values(id=act,tenant_id=T,operation_id=uuid4(),actor={"type":"human"},
                    action="synthetic_edit",subject_case_id=cid,summary="saved activity",detail={}))
            for aid in aids:
                await s.db.execute(insert(m.ActivityTargets).values(id=uuid4(),tenant_id=T,activity_id=activity_id,alert_id=aid,
                    before_value={"handling_status":"new"},after_value={"handling_status":"completed"},result_state="succeeded"))
            await s.db.execute(insert(m.Comments).values(id=uuid4(),tenant_id=T,alert_id=aids[0],body="saved comment",author_id=USER,author_name_snapshot="original name"))
            await s.db.execute(insert(m.ResponseLinks).values(id=uuid4(),tenant_id=T,alert_id=aids[0],external_namespace="synthetic",
                legacy_proposal_ref={"namespace":"synthetic","object_type":"proposal","id":"p1","version":None,"captured_at":None},
                approval_id="a1",action_id=None))
        cases = await get(f"incidents/{iid}/records/cases")
        assert cases["total"] == 2
        mapped = {c["id"]:c for c in cases["items"]}
        assert mapped[str(cid)]["via_member_alert"] and not mapped[str(cid)]["explicit_incident_link"]
        assert mapped[str(explicit)]["explicit_incident_link"] and not mapped[str(explicit)]["via_member_alert"]
        events = await get(f"alerts/{aids[0]}/records/activities")
        found = {a["id"]:a for a in events["items"]}
        assert str(activity_id) in found and str(unrelated) not in found
        assert [t["alert_id"] for t in found[str(activity_id)]["matching_targets"]] == [str(aids[0])]
        assert (await get(f"alerts/{aids[0]}/records/comments"))["items"][0]["author_name_snapshot"] == "original name"
        assert (await get(f"alerts/{aids[0]}/records/responses"))["items"][0]["action_id"] is None
        principal = CurrentUser(USER,T,"analyst","synthetic@example.invalid",scopes=["alerts:read"])
        await get(f"incidents/{iid}/records/cases",403)
        principal = CurrentUser(USER,T,"analyst","synthetic@example.invalid",scopes=["alerts:read","cases:read"])

    async def test_page_list_totals_pagination_and_no_write():
        aids, _, iid, _ = await fixture()
        async with writer.transaction(T) as s:
            before = (await s.db.execute(select(m.Alerts.__table__).where(m.Alerts.id.in_(aids)))).mappings().all()
        page = await get("alerts?limit=1")
        SubjectPage.model_validate(page)
        assert page["total"] > 1 and page["next_before_id"] and len(page["items"]) == 1
        second = await get("alerts?limit=1&before_id=" + page["next_before_id"])
        assert second["items"][0]["facts"]["id"] != page["items"][0]["facts"]["id"]
        assert second["overall_stats"] == page["overall_stats"] and page["total"] == page["overall_stats"]["total"]
        incidents = await get("incidents?limit=1")
        assert incidents["total"] > 0 and "unassigned" in incidents["overall_stats"]
        await get(f"incidents/{iid}")
        async with writer.transaction(T) as s:
            after = (await s.db.execute(select(m.Alerts.__table__).where(m.Alerts.id.in_(aids)))).mappings().all()
        assert before == after

    async def test_page_material_size_and_tenant_boundaries():
        nonlocal principal
        aids, _, iid, _ = await fixture()
        mid = uuid4()
        async with writer.transaction(T) as s:
            await s.db.execute(insert(m.AlertMaterials).values(id=mid,tenant_id=T,alert_id=aids[0],revision=2,
                raw_json={"large":"x"*140000},detection={},source_scope={},retention={},material_state="complete"))
        value = await get(f"alerts/{aids[0]}/materials/{mid}")
        assert value["availability"] == "content_exceeds_read_limit" and value["content_json"] is None
        principal = CurrentUser(USER,OTHER,"analyst","synthetic@example.invalid",scopes=["alerts:read"])
        await get(f"alerts/{aids[0]}",404)
        await get(f"incidents/{iid}/records/objects",404)
        await get(f"alerts/{aids[0]}/materials/{mid}",404)
        other_page = await get("alerts")
        async with writer.transaction(OTHER) as s:
            expected = (await s.db.execute(text("SELECT count(*) FROM socai2.alerts WHERE tenant_id=:tenant"),{"tenant":OTHER})).scalar_one()
        assert other_page["total"] == expected and not set(map(str,aids)) & {x["facts"]["id"] for x in other_page["items"]}
        principal = CurrentUser(USER,T,"analyst","synthetic@example.invalid",scopes=[])
        await get(f"alerts/{aids[0]}",403)
        principal = CurrentUser(USER,T,"analyst","synthetic@example.invalid",scopes=["alerts:read","cases:read"])
        await get("alerts?limit=201",422)
        await get(f"incidents/{iid}/records/objects?offset=-1",422)
        app.dependency_overrides.pop(api.get_service)
        try:
            with patch.object(api.settings,"SOCAI2_PAGE_READ_ENABLED",False):
                await get(f"alerts/{aids[0]}",503)
        finally:
            app.dependency_overrides[api.get_service] = lambda: reader

    async def test_page_trace_usage_complete_and_artifact_binding():
        aids, _, iid, _ = await fixture()
        claim = await writer.begin(T,"alert_basic",aids[0],uuid4(),producer="synthetic.page.trace",limits=LIMITS)
        rid, good, bad = claim["run_id"], uuid4(), uuid4()
        async with writer.transaction(T) as s:
            for seq,state,usage in [(1,"completed",{"usage_state":"reported","total_tokens":10,"cost_state":"unpriced"}),
                (2,"unknown",{"usage_state":"unknown","cost_state":"unpriced"})]:
                await s.db.execute(insert(m.RunSteps).values(id=uuid4(),tenant_id=T,run_id=rid,seq=seq,kind="model",stage_code="A",name="synthetic",state=state,
                    started_at=NOW+timedelta(seconds=seq),ended_at=NOW+timedelta(seconds=seq+1) if state=="completed" else None,usage=usage))
            await artifact(s,{"id":rid,"kind":"alert_basic","alert_id":aids[0]},good,"model_request",{"saved":"request"},await s.now(),[])
            await s.db.execute(insert(m.Artifacts).values(id=bad,tenant_id=T,run_id=rid,alert_id=aids[0],kind="model_response",schema_version="synthetic",
                content_json={"bad":"hash"},sha256="0"*64,size_bytes=5,mime_type="application/json",captured_at=await s.now(),material_state="complete",source_refs=[],retention={}))
        root = f"alerts/{aids[0]}/analysis/runs/{rid}"
        with patch.object(page_reader,"MAX_STEPS",1),patch.object(page_reader,"MAX_ARTIFACTS",1):
            result = await get(root+"/trace")
        TraceView.model_validate(result)
        assert result["steps_total"]==2 and result["steps_truncated"] and len(result["steps"])==1
        assert result["usage"]["known_total_tokens"]==10 and result["usage"]["unknown_token_calls"]==1 and result["usage"]["total_tokens"] is None
        assert result["artifacts_total"]==3 and result["artifacts_truncated"] and "blob_ref" not in str(result)
        assert "request_hash" not in result["run"] and "operation_key" not in result["run"]
        assert (await get(root+f"/artifacts/{good}"))["content_json"]=={"saved":"request"}
        assert (await get(root+f"/artifacts/{bad}"))["availability"]=="content_integrity_mismatch"
        await get(f"alerts/{aids[1]}/analysis/runs/{rid}/trace",404)
        await get(f"incidents/{iid}/analysis/runs/{rid}/artifacts/{good}",404)

    async def test_page_stats_use_full_scope_and_baseline_only():
        aids, _, iid, _ = await fixture()
        page = await get("incidents?limit=1")
        before = page["overall_stats"]
        # Resolved remains unassigned; override controls displayed severity.
        async with writer.transaction(T) as s:
            await s.db.execute(update(m.Incidents).where(m.Incidents.id == iid).values(handling_status="resolved",severity_override="high"))
        after = (await get("incidents?limit=1"))["overall_stats"]
        assert after["active"] == before["active"]-1 and after["unassigned"] == before["unassigned"]
        assert after["high_severity"] == before["high_severity"]+1
        before_running = (await get("alerts?limit=1"))["overall_stats"]["investigating"]
        await writer.begin(T,"alert_basic",aids[0],uuid4(),producer="synthetic.no-dispatch",limits=LIMITS)
        assert (await get("alerts?limit=1"))["overall_stats"]["investigating"] == before_running
        cid = uuid4()
        async with writer.transaction(T) as s:
            await s.db.execute(insert(m.Cases).values(id=cid,tenant_id=T,title="synthetic running baseline"))
        receipt = await writer.replace_members(T,cid,aids,expected_revision=0,actor=Actor(user_id=USER,name="synthetic"),operation_id=uuid4())
        rid = UUID(receipt["pending_run_id"])
        async def nop(_):
            return None
        await writer.start(T,cid,rid,Start(operation_key=uuid4(),expected_scope_revision=1),actor=Actor(user_id=USER,name="synthetic"),
            executor=nop,executor_version="synthetic.no-dispatch",limits=LIMITS)
        assert (await get("alerts?limit=1"))["overall_stats"]["investigating"] == before_running+2
        assert (await get(f"incidents/{iid}"))["derived"]["baseline_execution_counts"] == {"running":1,"unknown":0}
        async with writer.transaction(T) as s:
            await s.mark_unknown(cid,rid)
        assert (await get("alerts?limit=1"))["overall_stats"]["investigating"] == before_running
        assert (await get(f"incidents/{iid}"))["derived"]["baseline_execution_counts"] == {"running":0,"unknown":1}

    checks = [v for k,v in locals().copy().items() if k.startswith("test_page_")]
    try:
        for check in checks:
            if only and check.__name__ not in only:
                continue
            principal = CurrentUser(USER,T,"analyst","synthetic@example.invalid",scopes=["alerts:read","cases:read"])
            try:
                detail = await asyncio.wait_for(check(),100)
                record(check.__name__,True,detail)
            except Exception:  # noqa: BLE001 -- preserve original test failures
                record(check.__name__,False,traceback.format_exc())
    finally:
        await client.aclose()
