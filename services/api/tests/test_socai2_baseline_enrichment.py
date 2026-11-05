"""C2 synthetic checks in the existing isolated PostgreSQL database, no model."""
import asyncio
import json
import traceback
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2 import baseline_enrichment as c2
from app.socai2 import baseline_enrichment_sources as sources
from app.socai2 import baseline_model_view as view
from app.socai2.baseline_contracts import Actor, Limits, Publication, Start
from app.socai2.baseline_service import BaselineService
from app.socai2.baseline_store import RM, A, C, F, R, StoreError
from jsonschema import Draft202012Validator, FormatChecker
from socai2_test_model_view import model_data
from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

T, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
ACTOR = Actor(user_id=USER, name="synthetic C2 reviewer")
CONTRACTS = json.loads((Path(__file__).parents[1] / "app/socai2/contracts.schema.json").read_text("utf-8"))


async def run_checks(engine, record, only=None):
    service = BaselineService(async_sessionmaker(engine, expire_on_commit=False))

    async def rows(query):
        async with service.transaction(T) as store:
            return (await store.db.execute(query)).mappings().all()

    async def alert(store, name, host, *, tenant=T, namespace="fixture", when=None, include_objects=True):
        aid, mid = uuid4(), uuid4()
        await store.db.execute(insert(A).values(id=aid, tenant_id=tenant, title=name,
            source_namespace="c2-test", source_identity_key=str(aid), event_time=when,
            event_time_source="source" if when else "unknown"))
        await store.db.execute(insert(m.AlertMaterials.__table__).values(id=mid, tenant_id=tenant,
            alert_id=aid, revision=1, raw_text="synthetic retained raw", detection={
                "rule_id": "synthetic", "confidence_value": None, "confidence_state": "not_computed"},
            source_scope={}, retention={}, material_state="complete"))
        await store.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
        objects = [("host", host, "entity"), ("domain", host + ".invalid", "ioc")] if include_objects else []
        for typ, value, role in objects:
            await store.db.execute(insert(m.AlertObjects.__table__).values(id=uuid4(), tenant_id=tenant,
                alert_id=aid, material_id=mid, object_key=typ + ":" + value, namespace=namespace,
                object_type=typ, object_role=role, raw_value=value, normalized_value=value,
                source_path="$.synthetic." + typ, attributes={}))
        return aid

    async def fixture(n=2, calls=4, row_limit=20, window=True, deadline=60, description=None, include_objects=True):
        cid, host = uuid4(), "fixture-" + uuid4().hex
        async with service.transaction(T) as store:
            now = await store.now()
            await store.db.execute(insert(C).values(id=cid, tenant_id=T,
                title="synthetic C2 Case", description=description, created_by=USER))
            aids = [await alert(store, f"synthetic alert {i}", host, when=now,
                include_objects=include_objects) for i in range(n)]
            outcome = await store.replace_members(cid, set(aids), expected_revision=0,
                actor=ACTOR, operation_id=uuid4())
        rid = UUID(outcome["pending_run_id"])
        limits = Limits(max_model_calls=4, max_tokens=24000, max_tool_calls=calls,
            max_rows_per_query=row_limit, deadline_at=now + timedelta(seconds=deadline), policy_version="synthetic.c2.v1")
        async def idle(claim):
            pass
        await service.start(T, cid, rid, Start(expected_scope_revision=1, operation_key=uuid4(),
            window_start=now - timedelta(hours=1) if window else None,
            window_end=now + timedelta(hours=1) if window else None),
            actor=ACTOR, executor=idle, executor_version="synthetic.c2.v1", limits=limits)
        return cid, rid, aids, host, now

    async def seed(host, now, *, count=1):
        async with service.transaction(T) as store:
            for tenant in (T, OTHER):
                for i in range(count):
                    await store.db.execute(text("""INSERT INTO public.assets
                        (id,tenant_id,name,asset_type,criticality,tags,updated_at)
                        VALUES (:id,:tenant,:name,'host','high',ARRAY['synthetic'],:now)"""),
                        {"id": uuid4(), "tenant": tenant, "name": host, "now": now})
                for state in ("valid", "expired", "fp", "inactive"):
                    await store.db.execute(text("""INSERT INTO public.threat_intel_iocs
                        (id,tenant_id,ioc_type,value,confidence,source,source_ref,is_active,false_positive,expires_at)
                        VALUES (:id,:tenant,'domain',:value,NULL,'synthetic','fixture-only',:active,:fp,:expires)"""),
                        {"id": uuid4(), "tenant": tenant, "value": host + ".invalid", "active": state != "inactive",
                         "fp": state == "fp", "expires": now - timedelta(days=1) if state == "expired" else None})

    async def reject(code, task):
        try:
            await task
        except StoreError as exc:
            assert exc.code == code, (exc.code, code)
        else:
            raise AssertionError("expected " + code)

    async def artifacts(rid):
        return await rows(select(F).where(F.c.run_id == rid, F.c.kind == "tool_response"))

    def validate(payload, name):
        schema = {"$ref": "#/$defs/" + name, "$defs": CONTRACTS["$defs"]}
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)

    async def test_c2_actual_queries_and_tenant_scope():
        cid, rid, _aids, host, now = await fixture()
        await seed(host, now)
        async with service.transaction(T) as store:
            expected = await alert(store, "historical matching object", host, when=now - timedelta(minutes=5))
            await alert(store, "wrong namespace", host, namespace="other", when=now)
            await alert(store, "outside window", host, when=now - timedelta(days=1))
        async with service.transaction(OTHER) as store:
            await alert(store, "other tenant", host, tenant=OTHER, when=now)
        summary = await service.enrich(T, cid, rid)
        by_source = {s["source"]: s for s in summary["sources"]}
        assert all(by_source[s]["outcome"] == "data" for s in sources.CONNECTED)
        assert all(by_source[s]["outcome"] == "unavailable" for s in sources.SOURCES[3:])
        assert summary["coverage_complete"] is False
        responses = {f["content_json"]["tool_name"]: f["content_json"] for f in await artifacts(rid)}
        assert len(responses["assets"]["rows"]) == 1
        # One historic alert matches two explicit objects; rows retain each match.
        assert len(responses["history"]["rows"]) == 2
        assert {r["record_id"] for r in responses["history"]["rows"]} == {str(expected)}
        assert responses["history"]["rows"][0]["record"]["triage"] is None
        assert len(responses["threat_intel"]["rows"]) == 1
        assert responses["threat_intel"]["rows"][0]["record"]["confidence"] is None
        for payload in responses.values():
            validate(payload, "tool_exchange")
            validate(payload["actual_args"], "tool_args")
        assert (await rows(select(R).where(R.c.id == rid)))[0]["state"] == "running"
        assert all(r["read_state"] == "not_read" for r in await rows(select(RM).where(RM.c.run_id == rid)))

    async def test_c2_empty_and_unavailable_are_distinct():
        cid, rid, *_ = await fixture()
        summary = await service.enrich(T, cid, rid)
        assert [s["outcome"] for s in summary["sources"]] == ["empty"] * 3 + ["unavailable"] * 3
        for artifact in await artifacts(rid):
            payload = artifact["content_json"]
            assert (payload["rows"] == []) if payload["state"] == "completed" else (payload["rows"] is None)
        await reject("case_not_found", service.enrich(OTHER, cid, rid))

    async def test_c2_shared_budget_and_deadline():
        cid, rid, *_ = await fixture(calls=1)
        summary = await service.enrich(T, cid, rid)
        assert [s["outcome"] for s in summary["sources"]][:3] == ["empty", "not_attempted_budget", "not_attempted_budget"]
        steps = await rows(select(c2.S).where(c2.S.c.run_id == rid))
        assert sum(s["kind"] == "tool" and s["state"] == "completed" for s in steps) == 1
        assert all(s["usage"] is None for s in steps)
        cid, rid, *_ = await fixture(deadline=-1)
        summary = await service.enrich(T, cid, rid)
        assert all(s["outcome"] == "not_attempted_deadline" for s in summary["sources"][:3])
        assert all(not s["queried_object_keys"] for s in summary["sources"])

    async def test_c2_replay_concurrency_and_scope_freeze():
        cid, rid, aids, host, now = await fixture()
        entered, release = asyncio.Event(), asyncio.Event()
        original, calls = sources.query, []
        async def paused(*args):
            calls.append(args[2])
            if args[2] == "assets":
                entered.set()
                await release.wait()
            return await original(*args)
        with patch.object(sources, "query", paused):
            running = asyncio.create_task(service.enrich(T, cid, rid))
            try:
                await asyncio.wait_for(entered.wait(), 5)
                await reject("enrichment_already_claimed", service.enrich(T, cid, rid))
                async with service.transaction(T) as store:
                    extra = await alert(store, "later member", "different-" + host, when=now)
                changed = await service.replace_members(T, cid, aids + [extra], expected_revision=1,
                    actor=ACTOR, operation_id=uuid4())
                assert changed["pending_run_id"] != str(rid)
            finally:
                release.set()
            first = await running
            second = await service.enrich(T, cid, rid)
        assert first == second and calls == list(sources.SOURCES[:3])
        assert set(first["scope"]["alert_ids"]) == set(map(str, aids))
        assert all(str(extra) not in s["queried_alert_ids"] for s in first["sources"])

    async def test_c2_timeout_unavailable_and_unknown():
        cid, rid, *_ = await fixture()
        class MissingTable(Exception):
            sqlstate = "42P01"
        original = sources.query
        async def unavailable(*args):
            if args[2] == "assets":
                raise DBAPIError("redacted", {}, MissingTable())
            if args[2] == "history":
                raise TimeoutError
            return await original(*args)
        with patch.object(sources, "query", unavailable):
            summary = await service.enrich(T, cid, rid)
        assert [s["outcome"] for s in summary["sources"]][:3] == ["unavailable", "timeout", "empty"]
        cid, rid, *_ = await fixture()
        async def uncertain(*args):
            raise asyncio.CancelledError
        with patch.object(sources, "query", uncertain):
            try:
                await service.enrich(T, cid, rid)
            except asyncio.CancelledError:
                pass
            else:
                raise AssertionError("cancel was lost")
        assert (await rows(select(R).where(R.c.id == rid)))[0]["state"] == "unknown"
        await reject("enrichment_already_claimed", service.enrich(T, cid, rid))

    async def test_c2_row_limit_and_missing_window():
        cid, rid, _, host, now = await fixture(row_limit=1)
        await seed(host, now, count=3)
        summary = await service.enrich(T, cid, rid)
        assert summary["sources"][0]["returned_rows"] == 1
        assert summary["sources"][0]["truncated"] is True
        cid, rid, *_ = await fixture(window=False)
        summary = await service.enrich(T, cid, rid)
        assert summary["sources"][1]["reason"] == "history_window_not_defined"
        assert not summary["sources"][1]["queried_object_keys"]

    async def test_model_view_whole_case_and_original_guard():
        cid, rid, aids, *_ = await fixture(n=7, description='{"class_uid":4001,"message":"do not pass raw"}')
        await reject("enrichment_not_completed", service.prepare_model_view(T, cid, rid))
        await service.enrich(T, cid, rid)
        prepared = await service.prepare_model_view(T, cid, rid)
        assert prepared["ready"] and prepared["bytes"] <= 8192
        assert set(prepared["coverage"]) == set(map(str, aids))
        assert all(x["included"] >= 1 for x in prepared["coverage"].values())
        assert any(o["source"]["source_path"] == "$.case" and o["reason"] == "source_guard_blocked"
                   for o in prepared["omissions"])
        assert "class_uid" not in prepared["messages"][1]["content"]
        visible = model_data(prepared["messages"][1]["content"])
        assert len(visible["questions"]) == 6
        assert "current_inventory_not_event_time_state" in visible["source_states"][0]["limitations"]
        assert prepared == await service.prepare_model_view(T, cid, rid)
        assert all(r["read_state"] == "not_read" for r in await rows(select(RM).where(RM.c.run_id == rid)))

    async def test_model_view_budget_and_roles():
        cid, rid, *_ = await fixture()
        ctx = await service.read_context(T, cid, rid)
        aid = next(iter(ctx.alerts))
        ctx.alerts[aid].alert["description"] = "x" * 3000
        with patch.object(view, "MAX_MODEL_BYTES", 500):
            denied = view.build(ctx, uuid4(), [], [])
        assert not denied["ready"] and not denied["messages"]
        prepared = view.build(ctx, uuid4(), [], [])
        assert any(o["reason"] == "whole_field_exceeds_budget" for o in prepared["omissions"])
        # A nested forbidden field is rejected before a harmless projection.
        assert view.blocked({"safe": {"class_uid": 4001}})
        assert view.blocked("x" * 5000 + ' password="1234567890123456"')
        assert prepared["bytes"] <= 8192
        assert len(prepared["messages"][1]["content"].encode()) == prepared["prepared_ledger_bytes"]

    async def test_publish_cannot_race_active_steps_or_forge_c2_role():
        cid, rid, _, host, now = await fixture()
        ctx = await service.read_context(T, cid, rid)
        def publication(refs=None):
            return Publication.model_validate({"operation_key": uuid4(), "terminal_state": "completed",
                "stop_reason": "synthetic", "title": "synthetic", "conclusion": None,
                "conclusion_state": "unavailable", "conclusion_origin": "system", "validation_state": "system_only",
                "closing_note": "synthetic", "findings": [], "questions": [], "recommendations": [],
                "change_kind": "initial", "change_summary": None, "case_impact": {"summary": None,
                "supported_changes": [], "cannot_generalize": [], "affected_scope": ctx.scope.model_dump(mode="json"),
                "next_steps": []}, "delivery_state": "partial", "members": [{"alert_id": aid,
                "read_state": "not_read", "assessment_state": "not_analyzed", "conclusion_covered": False,
                "assessment": None, "limitations": "synthetic", "evidence_refs": refs or []} for aid in ctx.alerts]})
        entered, release = asyncio.Event(), asyncio.Event()
        original = sources.query
        async def paused(*args):
            entered.set()
            await release.wait()
            return await original(*args)
        await seed(host, now)
        with patch.object(sources, "query", paused):
            running = asyncio.create_task(service.enrich(T, cid, rid))
            try:
                await asyncio.wait_for(entered.wait(), 5)
                await reject("baseline_steps_not_settled", service.publish(T, cid, rid, publication()))
            finally:
                release.set()
            summary = await running
        ref = {"type": "artifact", "id": summary["sources"][0]["artifact_id"], "external": None,
               "source_path": "$.rows.0", "row_keys": [], "role": "observation"}
        await reject("context_citation_path_or_role_invalid", service.publish(T, cid, rid, publication([ref])))
        ref["role"] = "source_label"
        outcome = await service.publish(T, cid, rid, publication([ref]))
        assert outcome["adoption"]["state"] == "not_eligible"

    async def test_c2_byte_omission_is_not_empty_and_roles():
        cid, rid, *_ = await fixture()
        original = sources.query
        async def large(*args):
            if args[2] == "assets":
                async with service.transaction(T) as store:
                    return [{"record": {"tags": ["x" * 131073]}}], await store.now()
            return await original(*args)
        with patch.object(sources, "query", large):
            summary = await service.enrich(T, cid, rid)
        asset = summary["sources"][0]
        assert asset["outcome"] == "omitted" and asset["returned_rows"] == 0
        assert asset["observed_rows_in_bounded_fetch"] == 1
        assert asset["truncation_reasons"] == ["retained_row_bytes_limit"]
        roles = c2.citation_roles({"state": "completed", "tool_name": "history", "rows": [
            {"record": {"triage": {"confidence_value": None}, "feedback": {"decision": "false_positive"}}}]})
        assert roles == {"$.rows.0": "source_label", "$.rows.0.record.triage": "prior_analysis",
                         "$.rows.0.record.feedback": "human_statement"}

    async def test_c2_existing_tool_use_and_missing_objects():
        cid, rid, *_ = await fixture(calls=1)
        async with service.transaction(T) as store:
            now = await store.now()
            await store.db.execute(insert(c2.S).values(id=uuid4(), tenant_id=T, run_id=rid,
                seq=1, kind="tool", stage_code="C1", state="completed", name="synthetic_prior_query",
                started_at=now, ended_at=now, returned_rows=0))
        summary = await service.enrich(T, cid, rid)
        assert all(s["outcome"] == "not_attempted_budget" for s in summary["sources"][:3])
        ctx = await service.read_context(T, cid, rid)
        for alert_input in ctx.alerts.values():
            alert_input.objects.clear()
        assert all(sources.selectors(ctx, s) == [] for s in sources.CONNECTED)
        # Real frozen snapshot with no objects; do not replace the context reader.
        next_cid, next_rid, *_ = await fixture(include_objects=False)
        result = await service.enrich(T, next_cid, next_rid)
        assert all(s["outcome"] == "not_applicable" for s in result["sources"][:3])
        sample = {"id": str(uuid4()), "material_id": str(uuid4()), "object_type": "hash",
            "object_key": "hash:fixture", "namespace": "fixture", "object_role": "ioc",
            "normalized_value": "a" * 64, "source_path": "$.hash", "attributes": {"algorithm": {"unknown": True}}}
        next(iter(ctx.alerts.values())).objects.append(sample)
        assert not sources.selectors(ctx, "threat_intel")
        assert len(sources.selectors(ctx, "history")) == 1
        sample["attributes"]["algorithm"] = "SHA-256"
        assert sources.selectors(ctx, "threat_intel")[0]["ioc_type"] == "sha256"

    checks = [test_c2_actual_queries_and_tenant_scope, test_c2_empty_and_unavailable_are_distinct,
        test_c2_shared_budget_and_deadline, test_c2_replay_concurrency_and_scope_freeze,
        test_c2_timeout_unavailable_and_unknown, test_c2_row_limit_and_missing_window,
        test_model_view_whole_case_and_original_guard, test_model_view_budget_and_roles,
        test_publish_cannot_race_active_steps_or_forge_c2_role,
        test_c2_byte_omission_is_not_empty_and_roles, test_c2_existing_tool_use_and_missing_objects]
    for check in checks:
        if only is not None and check.__name__ not in only:
            continue
        try:
            detail = await asyncio.wait_for(check(), 40)
            record(check.__name__, True, detail)
        except Exception:  # noqa: BLE001 -- preserve original per-check failure
            record(check.__name__, False, traceback.format_exc())
