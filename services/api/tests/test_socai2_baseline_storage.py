"""Real PostgreSQL checks; invoked by the isolated SSH runner, no production DSN.

All fixtures are synthetic and use fresh UUIDs. No model/Tool/external API calls.
The runner supplies a restricted-role engine for the dedicated validation DB.
"""
import asyncio
import json
import traceback
from pathlib import Path
from uuid import UUID, uuid4

from app.models import socai2 as models
from app.socai2.baseline_contracts import Actor, Limits, Publication, Start
from app.socai2.baseline_service import BaselineService
from app.socai2.baseline_store import ACT, RES, A, C, F, StoreError
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

T = UUID(int=1)
T2 = UUID(int=2)
USER = UUID(int=3)
ACTOR = Actor(user_id=USER, name="synthetic storage test")
LIMITS = Limits(max_model_calls=0, max_tokens=0, max_tool_calls=0,
                max_rows_per_query=0, deadline_at=None, policy_version="synthetic.no-execution.v1")
SCHEMA = json.loads((Path(__file__).parents[1] / "app/socai2/contracts.schema.json").read_text("utf-8"))


def check_schema(name, value):
    Draft202012Validator({**SCHEMA, "$ref": f"#/$defs/{name}"},
                         format_checker=FormatChecker()).validate(value)


async def run_checks(engine, record, only=None):
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = BaselineService(sessions)

    async def scalar(sql, **params):
        async with service.transaction(T) as store:
            return (await store.db.execute(text(sql), params)).scalar_one()

    async def fixture(n=2, material=True):
        cid, aids, mids = uuid4(), [uuid4() for _ in range(n)], []
        async with service.transaction(T) as store:
            await store.db.execute(insert(C).values(id=cid, tenant_id=T, title="synthetic baseline store"))
            for aid in aids:
                await store.db.execute(insert(A).values(id=aid, tenant_id=T, title="synthetic alert",
                    source_namespace="socai2-storage-test", source_identity_key=str(aid)))
                mid = uuid4() if material else None
                mids.append(mid)
                if mid:
                    await store.db.execute(insert(models.AlertMaterials.__table__).values(
                        id=mid, tenant_id=T, alert_id=aid, revision=1, raw_text="synthetic material",
                        detection={}, source_scope={}, material_state="complete", retention={}))
                    await store.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
        return cid, aids, mids

    async def members(cid, aids, rev, op=None):
        return await service.replace_members(T, cid, aids, expected_revision=rev,
                                             actor=ACTOR, operation_id=op or uuid4())

    async def nop(claim):
        # A synthetic executor that deliberately leaves execution active.
        assert await scalar("SELECT state FROM socai2.runs WHERE id=:id", id=claim.run_id) == "running"

    async def start(cid, rid, revision, executor=nop, request=None):
        return await service.start(T, cid, rid, request or Start(expected_scope_revision=revision,
            operation_key=uuid4()), actor=ACTOR, executor=executor,
            executor_version="synthetic.stub.v1", limits=LIMITS)

    async def reject(code, call):
        try:
            await call
        except StoreError as exc:
            assert exc.code == code, (code, exc.code)
        else:
            raise AssertionError("expected " + code)

    def publication(aids, mids, **override):
        scope = {"kind": "whole_case", "alert_ids": list(map(str, aids)), "object_keys": [],
                     "window_start": None, "window_end": None, "limitations": []}
        data = {"operation_key": uuid4(), "terminal_state": "completed", "stop_reason": "synthetic_complete",
            "title": "synthetic result", "conclusion": "synthetic conclusion", "conclusion_state": "uncertain",
            "conclusion_origin": "model", "validation_state": "accepted", "closing_note": "synthetic handoff",
            "findings": [], "questions": [], "recommendations": [], "change_kind": "initial", "change_summary": None,
            "case_impact": {"summary": "synthetic", "supported_changes": [], "cannot_generalize": [],
                             "affected_scope": scope, "next_steps": []}, "delivery_state": "partial",
            "members": [{"alert_id": aid, "read_state": "read" if mid else "missing",
                          "assessment_state": "unresolved", "conclusion_covered": i == 0,
                          "assessment": "synthetic unresolved", "limitations": "synthetic limitation",
                          "evidence_refs": [{"type": "alert_material", "id": mid, "external": None,
                              "source_path": None, "row_keys": [], "role": "observation"}] if mid else []}
                     for i, (aid, mid) in enumerate(zip(aids, mids))]}
        return Publication.model_validate({**data, **override})

    async def test_coalesce():
        cid, aids, _ = await fixture()
        op = uuid4()
        first = await members(cid, aids[:1], 0, op)
        replay = await members(cid, aids[:1], 0, op)
        assert replay == first
        second = await members(cid, aids, 1)
        assert second["pending_run_id"] == first["pending_run_id"] and second["scope_revision"] == 2
        assert await members(cid, aids[:1], 0, op) == first  # old retry cannot undo revision 2
        await reject("operation_key_conflict", members(cid, aids, 0, op))
        await reject("case_scope_revision_conflict", members(cid, aids[:1], 1))
        history = await service.history(T, cid)
        assert len(history) == 1 and history[0]["state"] == "pending_update"
        assert history[0]["started_at"] is None and history[0]["scope_revision"] == 2
        async with service.transaction(T) as store:
            rows = (await store.db.execute(select(ACT.c.detail, ACT.c.actor).where(
                ACT.c.subject_case_id == cid))).mappings().all()
            for row in rows:
                check_schema("activity_detail", row["detail"])
                check_schema("actor", row["actor"])
        return {"case": str(cid), "pending": first["pending_run_id"], "revision": 2}

    async def test_claim_and_change():
        cid, aids, _ = await fixture()
        pending = await members(cid, aids[:1], 0)
        rid = UUID(pending["pending_run_id"])
        entered, release = asyncio.Event(), asyncio.Event()
        async def paused(claim):
            await nop(claim)
            entered.set()
            await release.wait()
        req = Start(expected_scope_revision=1, operation_key=uuid4())
        task = asyncio.create_task(start(cid, rid, 1, paused, req))
        try:
            await asyncio.wait_for(entered.wait(), 8)
            second = await members(cid, aids, 1)
            assert second["pending_run_id"] != str(rid)
            next_id = UUID(second["pending_run_id"])
            await reject("baseline_already_active", start(cid, next_id, 2))
            duplicate = await start(cid, rid, 1, nop, req)
            assert not duplicate.newly_claimed
            assert await scalar("SELECT count(*) FROM socai2.run_members WHERE run_id=:id", id=rid) == 1
            assert await scalar("SELECT state FROM socai2.runs WHERE id=:id", id=next_id) == "pending_update"
            return {"case": str(cid), "running": str(rid), "next_pending": str(next_id)}
        finally:
            release.set()
            await task

    async def test_parallel_claims():
        cid, aids, _ = await fixture()
        rid = UUID((await members(cid, aids, 0))["pending_run_id"])
        called = []
        async def count(claim):
            await nop(claim)
            called.append(claim.run_id)
        req = Start(expected_scope_revision=1, operation_key=uuid4())
        replies = await asyncio.gather(start(cid, rid, 1, count, req), start(cid, rid, 1, count, req))
        assert len(called) == 1 and sum(r.newly_claimed for r in replies) == 1
        return {"executor_invocations": len(called)}

    async def test_mutation_first():
        cid, aids, _ = await fixture()
        rid = UUID((await members(cid, aids[:1], 0))["pending_run_id"])
        entered, release = asyncio.Event(), asyncio.Event()
        async def change_locked():
            async with service.transaction(T) as store:
                await store.replace_members(cid, set(aids), expected_revision=1, actor=ACTOR, operation_id=uuid4())
                entered.set()
                await release.wait()
        change = asyncio.create_task(change_locked())
        await entered.wait()
        claiming = asyncio.create_task(start(cid, rid, 1))
        await asyncio.sleep(.15)
        assert not claiming.done()
        release.set()
        await change
        await reject("baseline_scope_revision_conflict", claiming)
        assert await scalar("SELECT state FROM socai2.runs WHERE id=:id", id=rid) == "pending_update"

    async def test_missing_executor():
        cid, aids, _ = await fixture()
        rid = UUID((await members(cid, aids, 0))["pending_run_id"])
        await reject("full_baseline_executor_not_configured", start(cid, rid, 1, None))
        assert await scalar("SELECT state FROM socai2.runs WHERE id=:id", id=rid) == "pending_update"
        assert await scalar("SELECT count(*) FROM socai2.artifacts WHERE run_id=:id", id=rid) == 0

    async def test_dispatch_error():
        cid, aids, _ = await fixture()
        rid = UUID((await members(cid, aids[:1], 0))["pending_run_id"])
        async def uncertain(claim):
            raise RuntimeError("synthetic transport failure")
        try:
            await start(cid, rid, 1, uncertain)
        except RuntimeError:
            pass
        assert await scalar("SELECT state FROM socai2.runs WHERE id=:id", id=rid) == "unknown"
        next_id = UUID((await members(cid, aids, 1))["pending_run_id"])
        await reject("baseline_already_active", start(cid, next_id, 2))

    async def test_material_freeze():
        cid, aids, mids = await fixture(1)
        rid = UUID((await members(cid, aids, 0))["pending_run_id"])
        claim = await start(cid, rid, 1)
        async with service.transaction(T) as store:
            snapshot = await store.one(select(F).where(F.c.id == claim.input_artifact_id))
            check_schema("input_snapshot", snapshot["content_json"])
            check_schema("retention", snapshot["retention"])
            newer = uuid4()
            await store.db.execute(insert(models.AlertMaterials.__table__).values(id=newer, tenant_id=T,
                alert_id=aids[0], revision=2, raw_text="synthetic v2", detection={}, source_scope={},
                material_state="complete", retention={}))
            await store.db.execute(update(A).where(A.c.id == aids[0]).values(latest_material_id=newer))
        assert await scalar("SELECT material_id FROM socai2.run_members WHERE run_id=:id", id=rid) == mids[0]
        out = await service.publish(T, cid, rid, publication(aids, mids))
        assert out["adoption"]["state"] == "adopted"

    async def test_publish():
        cid, aids, mids = await fixture()
        rid = UUID((await members(cid, aids, 0))["pending_run_id"])
        await start(cid, rid, 1)
        pub = publication(aids, mids)
        out = await service.publish(T, cid, rid, pub)
        assert out["adoption"]["state"] == "adopted"
        assert await service.publish(T, cid, rid, pub) == out
        changed = pub.model_copy(update={"conclusion": "different synthetic conclusion"})
        await reject("publication_key_conflict", service.publish(T, cid, rid, changed))
        assert await scalar("SELECT count(*) FROM socai2.case_assessment_members WHERE assessment_id=:id",
                            id=UUID(out["adoption"]["assessment_id"])) == 1
        assert await scalar("SELECT handling_status FROM socai2.cases WHERE id=:id", id=cid) == "new"
        history = await service.history(T, cid)
        assert history[0]["result_id"] == UUID(out["result_id"])
        async with service.transaction(T) as store:
            row = await store.one(select(RES).where(RES.c.id == UUID(out["result_id"])))
            for field in ["findings", "questions", "recommendations", "case_impact"]:
                check_schema(field, row[field])
        return out

    async def test_stale_publish():
        cid, aids, mids = await fixture()
        rid = UUID((await members(cid, aids[:1], 0))["pending_run_id"])
        await start(cid, rid, 1)
        next_id = UUID((await members(cid, aids, 1))["pending_run_id"])
        out = await service.publish(T, cid, rid, publication(aids[:1], mids[:1]))
        assert out["adoption"]["state"] == "stale_scope"
        assert await scalar("SELECT current_assessment_id FROM socai2.cases WHERE id=:id", id=cid) is None
        assert await scalar("SELECT state FROM socai2.runs WHERE id=:id", id=next_id) == "pending_update"
        await start(cid, next_id, 2)  # explicit manual call is still needed

    async def test_invalid_publication_rollback():
        cid, aids, mids = await fixture()
        rid = UUID((await members(cid, aids, 0))["pending_run_id"])
        await start(cid, rid, 1)
        pub = publication(aids, mids)
        incomplete = pub.model_copy(update={"members": pub.members[:1]})
        await reject("result_member_delivery_incomplete", service.publish(T, cid, rid, incomplete))
        foreign = pub.model_dump(mode="json")
        foreign["members"][0]["evidence_refs"][0]["id"] = str(uuid4())
        await reject("result_evidence_outside_frozen_scope",
                     service.publish(T, cid, rid, Publication.model_validate(foreign)))
        assert await scalar("SELECT state FROM socai2.runs WHERE id=:id", id=rid) == "running"
        assert await scalar("SELECT count(*) FROM socai2.results WHERE source_run_id=:id", id=rid) == 0

    async def test_publication_transaction_failure():
        cid, aids, mids = await fixture()
        rid = UUID((await members(cid, aids, 0))["pending_run_id"])
        await start(cid, rid, 1)
        try:
            async with service.transaction(T) as store:
                out = await store.publish(cid, rid, publication(aids, mids))
                assert out["adoption"]["state"] == "adopted"
                raise RuntimeError("synthetic request rollback after adoption")
        except RuntimeError:
            pass
        assert await scalar("SELECT state FROM socai2.runs WHERE id=:id", id=rid) == "running"
        assert await scalar("SELECT count(*) FROM socai2.results WHERE source_run_id=:id", id=rid) == 0
        assert await scalar("SELECT current_assessment_id FROM socai2.cases WHERE id=:id", id=cid) is None

    async def test_no_auto_adopt_system():
        cid, aids, mids = await fixture(1, material=False)
        rid = UUID((await members(cid, aids, 0))["pending_run_id"])
        await start(cid, rid, 1)
        pub = publication(aids, mids, terminal_state="failed", conclusion=None,
            conclusion_state="unavailable", conclusion_origin="system", validation_state="system_only")
        out = await service.publish(T, cid, rid, pub)
        assert out["adoption"]["state"] == "not_eligible"
        assert await scalar("SELECT current_assessment_id FROM socai2.cases WHERE id=:id", id=cid) is None

    async def test_empty_and_resolved():
        cid, aids, _ = await fixture(1)
        rid = UUID((await members(cid, aids, 0))["pending_run_id"])
        await members(cid, [], 1)
        await reject("baseline_scope_empty", start(cid, rid, 2))
        async with service.transaction(T) as store:
            await store.db.execute(update(C).where(C.c.id == cid).values(handling_status="resolved"))
        await reject("resolved_case_scope_policy_not_enabled", members(cid, aids, 2))
        await reject("resolved_case_start_policy_not_enabled", start(cid, rid, 2))

    async def test_rls():
        cid, _aids, _ = await fixture(1)
        await reject("case_not_found", service.history(T2, cid))
        async with sessions() as db, db.begin():
            assert (await db.execute(select(C.c.id).where(C.c.id == cid))).scalar_one_or_none() is None
            role = (await db.execute(text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user"))).scalar_one()
            assert role is False
        cid2, _, _ = await fixture(0)
        await reject("member_alert_not_found", members(cid2, [uuid4()], 0))
        assert await scalar("SELECT scope_revision FROM socai2.cases WHERE id=:id", id=cid2) == 0

    async def test_publication_key_across_cases():
        cid, aids, mids = await fixture(1)
        rid = UUID((await members(cid, aids, 0))["pending_run_id"])
        await start(cid, rid, 1)
        pub = publication(aids, mids)
        await service.publish(T, cid, rid, pub)
        cid2, aids2, mids2 = await fixture(1)
        rid2 = UUID((await members(cid2, aids2, 0))["pending_run_id"])
        await start(cid2, rid2, 1)
        await reject("publication_key_conflict", service.publish(T, cid2, rid2,
            publication(aids2, mids2, operation_key=pub.operation_key)))
        assert await scalar("SELECT state FROM socai2.runs WHERE id=:id", id=rid2) == "running"
        assert await scalar("SELECT current_assessment_id FROM socai2.cases WHERE id=:id", id=cid2) is None

    async def test_claim_commit_before_executor():
        cid, aids, _ = await fixture(1)
        rid = UUID((await members(cid, aids, 0))["pending_run_id"])
        called = []
        async def executor(claim):
            called.append(claim)
        # The actor FK is deferred until COMMIT. A failed commit must never dispatch.
        try:
            await service.start(T, cid, rid, Start(expected_scope_revision=1, operation_key=uuid4()),
                actor=Actor(user_id=uuid4(), name="synthetic nonexistent actor"), executor=executor,
                executor_version="synthetic.stub.v1", limits=LIMITS)
        except IntegrityError:
            pass
        else:
            raise AssertionError("deferred actor FK should fail at commit")
        assert called == []
        assert await scalar("SELECT state FROM socai2.runs WHERE id=:id", id=rid) == "pending_update"
        assert await scalar("SELECT count(*) FROM socai2.artifacts WHERE run_id=:id", id=rid) == 0

    async def test_newer_human_judgment():
        cid, aids, mids = await fixture(1)
        rid = UUID((await members(cid, aids, 0))["pending_run_id"])
        claimed = await start(cid, rid, 1)
        human_id = uuid4()
        async with service.transaction(T) as store:
            now = await store.now()
            assert now > claimed.started_at
            await store.db.execute(insert(models.CaseAssessments.__table__).values(
                id=human_id, tenant_id=T, case_id=cid, revision=1, conclusion="synthetic human judgment",
                origin="human", validity="accepted", scope_revision=1, formed_at=now,
                adopted_at=now, actor=ACTOR.snapshot(), operation_key=str(uuid4())))
            await store.db.execute(update(C).where(C.c.id == cid).values(current_assessment_id=human_id))
        out = await service.publish(T, cid, rid, publication(aids, mids))
        assert out["adoption"]["state"] == "newer_assessment"
        assert await scalar("SELECT current_assessment_id FROM socai2.cases WHERE id=:id", id=cid) == human_id

    async def test_input_freshness_material_before_and_after_publication():
        from app.socai2.case_reader import CaseReader
        results = []
        for before in (True, False):
            cid, aids, mids = await fixture(1)
            rid = UUID((await members(cid, aids, 0))["pending_run_id"])
            await start(cid, rid, 1)
            assert (await scalar("SELECT socai2.baseline_input_freshness(:tenant,:run)", tenant=T, run=rid))["state"] == "current"
            if not before:
                out = await service.publish(T, cid, rid, publication(aids, mids))
                assert out["adoption"]["state"] == "adopted"
            async with service.transaction(T) as store:
                mid = uuid4()
                await store.db.execute(insert(models.AlertMaterials.__table__).values(
                    id=mid, tenant_id=T, alert_id=aids[0], revision=2, raw_text="changed material",
                    detection={}, source_scope={}, material_state="complete", retention={}))
                await store.db.execute(update(A).where(A.c.id == aids[0]).values(latest_material_id=mid))
            state = await scalar("SELECT socai2.baseline_input_freshness(:tenant,:run)", tenant=T, run=rid)
            assert state == {"state": "stale", "reasons": ["member_versions_changed"]}
            if before:
                out = await service.publish(T, cid, rid, publication(aids, mids))
                assert out["adoption"]["state"] == "stale_input"
                assert await scalar("SELECT current_assessment_id FROM socai2.cases WHERE id=:id", id=cid) is None
            else:
                async with service.transaction(T, readonly=True) as store:
                    view = await CaseReader(store).case(cid)
                    assert view["current_assessment"]["input_freshness"] == state
                    assert view["current_assessment"]["scope_revision_changed"] is False
            results.append({"run_id": str(rid), "change_before_publication": before, "freshness": state})
        return results

    async def test_input_freshness_human_semantics_not_task_metadata():
        from app.socai2.baseline_contracts import Scope
        from app.socai2.human_task_contracts import TaskCreate, TaskEdit
        from app.socai2.human_task_service import HumanTaskService
        human = HumanTaskService(sessions)
        cid, aids, mids = await fixture(1)
        rid = UUID((await members(cid, aids, 0))["pending_run_id"])
        fields = {"title": "verify authorization", "state": "completed", "result_text": "confirmed synthetic statement",
            "result_scope": Scope(kind="selected_alerts", alert_ids=aids, object_keys=[], window_start=None, window_end=None, limitations=[])}
        created = await human.write(T, cid, TaskCreate(operation_key=uuid4(), expected_scope_revision=1, **fields), actor=ACTOR)
        await start(cid, rid, 1)
        fields["title"] = "renamed review task"
        edited = await human.write(T, cid, TaskEdit(operation_key=uuid4(), expected_scope_revision=1,
            expected_row_version=created.task.row_version, **fields), actor=ACTOR, task_id=created.task.id)
        assert (await scalar("SELECT socai2.baseline_input_freshness(:tenant,:run)", tenant=T, run=rid))["state"] == "current"
        fields["result_text"] = "withdrawn synthetic authorization statement"
        await human.write(T, cid, TaskEdit(operation_key=uuid4(), expected_scope_revision=1,
            expected_row_version=edited.task.row_version, **fields), actor=ACTOR, task_id=created.task.id)
        state = await scalar("SELECT socai2.baseline_input_freshness(:tenant,:run)", tenant=T, run=rid)
        assert state == {"state": "stale", "reasons": ["human_feedback_changed"]}
        out = await service.publish(T, cid, rid, publication(aids, mids))
        assert out["adoption"]["state"] == "stale_input"
        return {"run_id": str(rid), "metadata_edit_current": True, "feedback_edit_stale": True}

    async def test_input_freshness_paired_assessment_versions():
        checked = []
        for kind, pointer in (("triage", "latest_triage_id"), ("human_feedback", "latest_feedback_id")):
            cid, aids, mids = await fixture(1)
            rid = UUID((await members(cid, aids, 0))["pending_run_id"])
            await start(cid, rid, 1)
            async with service.transaction(T) as store:
                identity = uuid4()
                await store.db.execute(insert(models.AlertAssessments.__table__).values(id=identity, tenant_id=T,
                    alert_id=aids[0], kind=kind, input_material_id=mids[0], verdict="needs_review", rationale="synthetic",
                    producer="synthetic", actor=ACTOR.snapshot(), assessed_at=await store.now(), operation_key=str(uuid4())))
                await store.db.execute(update(A).where(A.c.id == aids[0]).values(**{pointer: identity}))
            state = await scalar("SELECT socai2.baseline_input_freshness(:tenant,:run)", tenant=T, run=rid)
            assert state == {"state": "stale", "reasons": ["member_versions_changed"]}
            out = await service.publish(T, cid, rid, publication(aids, mids))
            assert out["adoption"]["state"] == "stale_input"
            checked.append(kind)
        return {"changed_judgments": checked, "adopted": 0}

    checks = [test_input_freshness_paired_assessment_versions,
              test_input_freshness_material_before_and_after_publication, test_input_freshness_human_semantics_not_task_metadata,
              test_coalesce, test_claim_and_change, test_parallel_claims, test_mutation_first,
              test_missing_executor, test_dispatch_error, test_material_freeze, test_publish,
              test_stale_publish, test_invalid_publication_rollback, test_publication_transaction_failure,
              test_no_auto_adopt_system, test_empty_and_resolved, test_rls,
              test_publication_key_across_cases, test_claim_commit_before_executor, test_newer_human_judgment]
    for test in checks:
        if only is not None and test.__name__ not in only:
            continue
        try:
            detail = await asyncio.wait_for(test(), timeout=25)
            record(test.__name__, True, detail)
        except Exception:  # noqa: BLE001 -- retain every independent check's failure receipt
            record(test.__name__, False, traceback.format_exc())
