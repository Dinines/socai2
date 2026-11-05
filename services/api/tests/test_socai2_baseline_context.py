"""C1 integration checks against the explicitly isolated synthetic PG database."""
import asyncio
import json
import traceback
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2 import baseline_context as c1
from app.socai2.baseline_contracts import Actor, Limits, Publication, Start
from app.socai2.baseline_service import BaselineService
from app.socai2.baseline_store import RM, A, C, F, R, StoreError, digest
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

T, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
ACTOR = Actor(user_id=USER, name="synthetic C1 reviewer")
LIMITS = Limits(max_model_calls=0, max_tokens=0, max_tool_calls=0,
                max_rows_per_query=0, deadline_at=None, policy_version="synthetic.no-execution.v1")
CONTEXT_SCHEMA = json.loads((Path(__file__).parents[1] / "app/socai2/baseline_context.schema.json").read_text("utf-8"))


async def run_checks(engine, record, only=None):
    service = BaselineService(async_sessionmaker(engine, expire_on_commit=False))

    async def one(q):
        async with service.transaction(T) as store:
            return await store.one(q)

    async def fixture(n=5):
        cid, aids, mids = uuid4(), [uuid4() for _ in range(n)], [uuid4() for _ in range(n)]
        async with service.transaction(T) as store:
            await store.db.execute(insert(C).values(id=cid, tenant_id=T, title="synthetic Case original",
                description="synthetic Case explanation", created_by=USER))
            for i, (aid, mid) in enumerate(zip(aids, mids)):
                await store.db.execute(insert(A).values(id=aid, tenant_id=T, title=f"synthetic alert {i}",
                    source_namespace="c1-test", source_identity_key=str(aid), source_alert_id=f"integration-{i}",
                    vendor_alert_id=None, original_vendor=None))
                await material(store, aid, mid, 1, f"original-{i}")
                await store.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
            outcome = await store.replace_members(cid, set(aids), expected_revision=0,
                actor=ACTOR, operation_id=uuid4())
        return cid, aids, mids, UUID(outcome["pending_run_id"])

    async def material(store, aid, mid, revision, body, state="complete"):
        await store.db.execute(insert(m.AlertMaterials.__table__).values(id=mid, tenant_id=T,
            alert_id=aid, revision=revision, raw_text=body, raw_json={"event": "synthetic", "pid": 123},
            ocsf_json={"process": {"pid": 123, "cmd_line": "synthetic --test"}},
            detection={"rule_id": "synthetic-rule", "confidence_state": "not_computed", "confidence_value": None},
            source_scope={}, material_state=state, retention={}))

    async def start(cid, rid, revision=1, comparison=None):
        async def no_execution(claim):
            assert (await one(select(R.c.state).where(R.c.id == claim.run_id)))["state"] == "running"
        return await service.start(T, cid, rid, Start(expected_scope_revision=revision,
            operation_key=uuid4(), comparison_result_id=comparison), actor=ACTOR,
            executor=no_execution, executor_version="synthetic.c1.v1", limits=LIMITS)

    async def task(cid, aids, *, state="completed", task_id=None, revision=1, value="synthetic human confirmation"):
        tid, vid = task_id or uuid4(), uuid4()
        async with service.transaction(T) as store:
            now = await store.now()
            if task_id is None:
                await store.db.execute(insert(m.Tasks.__table__).values(id=tid, tenant_id=T,
                    case_id=cid, current_revision_id=vid, created_by=USER))
            await store.db.execute(insert(m.TaskRevisions.__table__).values(id=vid, tenant_id=T,
                case_id=cid, task_id=tid, revision=revision, title="synthetic task", state=state,
                result_text=value if state == "completed" else None,
                result_scope={"kind": "selected_alerts", "alert_ids": list(map(str, aids)), "object_keys": [],
                              "window_start": None, "window_end": None, "limitations": []},
                source_refs=[], completed_at=now if state == "completed" else None,
                completed_by=USER if state == "completed" else None, changed_by=USER))
            if task_id:
                await store.db.execute(update(m.Tasks.__table__).where(m.Tasks.id == tid).values(
                    current_revision_id=vid, row_version=m.Tasks.row_version + 1))
        return tid, vid

    async def incident(cid, aids, *, link=True, diagnosis_state="completed", validation="accepted"):
        iid, did, source_run, art_id = uuid4(), uuid4(), uuid4(), uuid4()
        async with service.transaction(T) as store:
            now = await store.now()
            await store.db.execute(insert(m.Incidents.__table__).values(id=iid, tenant_id=T,
                title="synthetic incident", source_namespace="c1-test", source_incident_id=str(iid)))
            for aid in aids:
                await store.db.execute(insert(m.IncidentAlerts.__table__).values(id=uuid4(), tenant_id=T,
                    incident_id=iid, alert_id=aid, membership_source="fusion",
                    correlation_basis={"synthetic_observed_key": "host:fixture"},
                    basis_version="synthetic.v1", source_operation_id=uuid4()))
            if link:
                await store.db.execute(insert(m.CaseIncidents.__table__).values(id=uuid4(), tenant_id=T,
                    case_id=cid, incident_id=iid, source_operation_id=uuid4()))
            manifest = {"schema_version": "socai2.page-model.v1", "run_kind": "incident_diagnosis",
                "scope_revision": None, "scope": {"kind": "selected_alerts", "alert_ids": list(map(str, aids)),
                    "object_keys": [], "window_start": None, "window_end": None, "limitations": []},
                "source_materials": [], "prior_results": [], "task_revisions": [], "comparison_result_id": None,
                "projection_version": "synthetic.incident.v1", "omissions": [], "captured_at": now.isoformat()}
            await store.db.execute(insert(F).values(id=art_id, tenant_id=T, incident_id=iid, run_id=source_run,
                kind="input_snapshot", schema_version="socai2.page-model.v1", content_json=manifest,
                mime_type="application/json", material_state="complete", captured_at=now, source_refs=[], retention={}))
            await store.db.execute(insert(R).values(id=source_run, tenant_id=T, incident_id=iid,
                kind="incident_diagnosis", title="synthetic source run", purpose="fixture only", trigger="manual",
                state="completed", operation_key=str(uuid4()), request_hash="0" * 64,
                input_artifact_id=art_id, executor_version="synthetic.v1", started_at=now, ended_at=now))
            await store.db.execute(insert(m.IncidentDiagnoses.__table__).values(id=did, tenant_id=T,
                incident_id=iid, source_run_id=source_run, revision=1, state=diagnosis_state,
                summary="synthetic prior diagnosis", diagnosis={"conclusion": "synthetic interpretation",
                    "validation_state": validation, "findings": [], "source_refs": [], "limitations": []},
                open_questions=[], input_artifact_id=art_id, source_fingerprint="1" * 64,
                producer="synthetic", requested_at=now, generated_at=now if diagnosis_state == "completed" else None))
            await store.db.execute(update(m.Incidents.__table__).where(m.Incidents.id == iid).values(latest_diagnosis_id=did))
        return iid, did

    async def reject(code, call):
        try:
            await call
        except StoreError as exc:
            assert exc.code == code, (exc.code, code)
        else:
            raise AssertionError("expected " + code)

    def result(context, refs=None, system=False):
        return Publication.model_validate({"operation_key": uuid4(), "terminal_state": "completed",
            "stop_reason": "synthetic_only", "title": "synthetic result", "conclusion": None if system else "synthetic conclusion",
            "conclusion_state": "unavailable" if system else "uncertain", "conclusion_origin": "system" if system else "model",
            "validation_state": "system_only" if system else "accepted", "closing_note": "synthetic handoff",
            "findings": [], "questions": [], "recommendations": [], "change_kind": "initial", "change_summary": None,
            "case_impact": {"summary": None, "supported_changes": [], "cannot_generalize": [],
                            "affected_scope": context.scope.model_dump(mode="json"), "next_steps": []},
            "delivery_state": "partial", "members": [{"alert_id": aid,
                "read_state": "not_read" if a.material else "missing", "assessment_state": "unresolved",
                "conclusion_covered": not system, "assessment": "synthetic", "limitations": "synthetic only",
                "evidence_refs": refs or []} for aid, a in context.alerts.items()]})

    async def test_c1_all_members_and_contract():
        cid, aids, mids, rid = await fixture()
        await start(cid, rid)
        ctx = await service.read_context(T, cid, rid)
        assert set(ctx.alerts) == set(map(str, aids)) and len(ctx.questions) == 6
        assert all(q.state == "open" and q.answer is None for q in ctx.questions)
        assert ctx.case["description"] == "synthetic Case explanation"
        for aid in aids:
            a = ctx.alerts[str(aid)]
            assert a.alert["original_vendor"] is None and a.alert["vendor_alert_id"] is None
            assert a.material["detection"]["confidence_value"] is None
            assert "raw_text" not in a.material and "raw_json" not in a.material
            assert a.membership["membership_source"] == "manual"
            assert ctx.citation_roles[f"$.alerts.{aid}.membership"] == "execution_receipt"
        Draft202012Validator(CONTEXT_SCHEMA, format_checker=FormatChecker()).validate(ctx.model_dump(mode="json"))
        assert CONTEXT_SCHEMA == c1.Context.model_json_schema()
        raw = await service.read_material(T, cid, rid, mids[4])
        assert raw["raw_text"] == "original-4" and raw["ocsf_json"]["process"]["cmd_line"] == "synthetic --test"
        row = await one(select(RM.c.read_state).where(RM.c.run_id == rid, RM.c.alert_id == aids[4]))
        assert row["read_state"] == "not_read"  # GET/metadata capture never claims model reading
        return {"case": str(cid), "run": str(rid), "members": len(ctx.alerts), "questions": 6}

    async def test_c1_source_versions_survive_edits():
        cid, aids, mids, rid = await fixture(1)
        tid, vid = await task(cid, aids)
        iid, did = await incident(cid, aids, link=False)  # discovered via member relation
        await start(cid, rid)
        before = await service.read_context(T, cid, rid)
        await task(cid, aids, task_id=tid, revision=2, value="synthetic revised statement")
        async with service.transaction(T) as store:
            await store.db.execute(update(C).where(C.c.id == cid).values(description="edited Case explanation"))
            await store.db.execute(update(m.Incidents.__table__).where(m.Incidents.id == iid).values(title="edited incident"))
            new_mid = uuid4()
            await material(store, aids[0], new_mid, 2, "edited raw")
            await store.db.execute(update(A).where(A.c.id == aids[0]).values(latest_material_id=new_mid, title="edited alert"))
        after = await service.read_context(T, cid, rid)
        assert before.model_dump() == after.model_dump()
        assert after.tasks[str(tid)].revision["id"] == str(vid)
        assert after.incidents[str(iid)].diagnosis["id"] == str(did)
        assert (await service.read_material(T, cid, rid, mids[0]))["raw_text"] == "original-0"
        await reject("frozen_material_not_found", service.read_material(T, cid, rid, new_mid))

    async def test_c1_same_statement_pointer_selection():
        cid, aids, mids, rid = await fixture(1)
        tid, vid = await task(cid, aids)
        _, next_vid = await task(cid, aids, task_id=tid, revision=2, value="prepared second revision")
        async with service.transaction(T) as store:
            await store.db.execute(update(m.Tasks.__table__).where(m.Tasks.id == tid).values(current_revision_id=vid))
        original_capture = c1.capture
        newer_mid, calls = uuid4(), []
        async def concurrent_edit(*args):
            ctx = await original_capture(*args)
            calls.append(True)
            async with service.transaction(T) as other:
                # Update existing pointers. Inserting a new task revision would
                # also need a Case FK key lock and correctly wait for the claim.
                await other.db.execute(update(m.Tasks.__table__).where(m.Tasks.id == tid).values(current_revision_id=next_vid))
                await material(other, aids[0], newer_mid, 2, "committed after snapshot read")
                await other.db.execute(update(A).where(A.c.id == aids[0]).values(latest_material_id=newer_mid))
            return ctx
        with patch.object(c1, "capture", concurrent_edit):
            await start(cid, rid)
        ctx = await service.read_context(T, cid, rid)
        assert len(calls) == 1 and ctx.tasks[str(tid)].revision["id"] == str(vid)
        member = await one(select(RM.c.material_id).where(RM.c.run_id == rid))
        assert member["material_id"] == mids[0] and ctx.alerts[str(aids[0])].material["id"] == str(mids[0])

    async def test_c1_incomplete_and_wider_scope():
        cid, aids, _mids, rid = await fixture(4)
        other_case, other_aids, _, _ = await fixture(2)
        tid, _ = await task(cid, aids, state="in_progress")
        iid, _ = await incident(cid, [aids[0], other_aids[0]])
        failed_iid, _ = await incident(cid, [aids[1]], diagnosis_state="failed")
        rejected_iid, _ = await incident(cid, [aids[2]], validation="rejected")
        unrelated_iid, _ = await incident(other_case, [other_aids[1]])
        async with service.transaction(T) as store:
            await store.db.execute(update(A).where(A.c.id == aids[3]).values(latest_material_id=None))
        await start(cid, rid)
        ctx = await service.read_context(T, cid, rid)
        assert not ctx.tasks[str(tid)].usable_feedback
        assert ctx.citation_roles[f"$.tasks.{tid}.revision"] == "execution_receipt"
        assert not ctx.incidents[str(iid)].diagnosis_usable
        assert ctx.incidents[str(iid)].diagnosis_freshness == "unverified"
        assert "incident_scope_extends_beyond_case" in ctx.incidents[str(iid)].limitations
        assert ctx.incidents[str(iid)].case_member_ids == [aids[0]]
        assert ctx.incidents[str(iid)].member_links[0]["correlation_basis"] == {"synthetic_observed_key": "host:fixture"}
        assert ctx.citation_roles[f"$.incidents.{iid}.member_links"] == "source_label"
        assert not ctx.incidents[str(failed_iid)].diagnosis_usable
        assert not ctx.incidents[str(rejected_iid)].diagnosis_usable
        assert str(unrelated_iid) not in ctx.incidents
        assert "source_material_not_available" in ctx.alerts[str(aids[3])].limitations
        assert not any(path.endswith("diagnosis") and str(failed_iid) in path for path in ctx.citation_roles)

    async def test_c1_paired_triage_and_feedback():
        cid, aids, mids, rid = await fixture(1)
        triage, feedback = uuid4(), uuid4()
        async with service.transaction(T) as store:
            now = await store.now()
            for identity, kind, verdict, rationale, confidence in [
                (triage, "triage", "true_positive", "synthetic original triage", .91),
                (feedback, "human_feedback", "false_positive", "synthetic human correction", None)]:
                await store.db.execute(insert(m.AlertAssessments.__table__).values(id=identity, tenant_id=T,
                    alert_id=aids[0], kind=kind, input_material_id=mids[0], verdict=verdict, rationale=rationale,
                    confidence=confidence, score_state="available" if confidence is not None else "not_provided",
                    producer="synthetic", actor=ACTOR.snapshot(), assessed_at=now, operation_key=str(uuid4())))
            await store.db.execute(update(A).where(A.c.id == aids[0]).values(
                latest_triage_id=triage, latest_feedback_id=feedback, disposition="false_positive"))
        await start(cid, rid)
        ctx = await service.read_context(T, cid, rid)
        a = ctx.alerts[str(aids[0])]
        assert a.triage["verdict"] == "true_positive" and a.triage["confidence"] == .91
        assert a.feedback["verdict"] == "false_positive" and a.feedback["confidence"] is None
        assert not a.triage_usable and a.triage_freshness == "unavailable"
        assert f"$.alerts.{aids[0]}.triage" not in ctx.citation_roles
        assert ctx.citation_roles[f"$.alerts.{aids[0]}.feedback"] == "human_statement"

    async def test_c1_adopted_old_task_and_current_revision():
        cid, aids, _mids, rid = await fixture(1)
        tid, old_vid = await task(cid, aids, value="original adopted statement")
        judgment = uuid4()
        async with service.transaction(T) as store:
            now = await store.now()
            await store.db.execute(insert(m.CaseAssessments.__table__).values(id=judgment, tenant_id=T,
                case_id=cid, revision=1, conclusion="synthetic adopted judgment", origin="human", validity="accepted",
                scope_revision=0, formed_at=now, adopted_at=now, actor=ACTOR.snapshot(), operation_key=str(uuid4())))
            await store.db.execute(insert(m.CaseAssessmentSources.__table__).values(id=uuid4(), tenant_id=T,
                case_id=cid, assessment_id=judgment, task_revision_id=old_vid))
            await store.db.execute(update(C).where(C.c.id == cid).values(current_assessment_id=judgment))
        _, current_vid = await task(cid, aids, task_id=tid, revision=2, value="later edited statement")
        claim = await start(cid, rid)
        ctx = await service.read_context(T, cid, rid)
        assert ctx.tasks[str(tid)].revision["id"] == str(current_vid)
        assert ctx.adopted_task_revisions[str(old_vid)]["result_text"] == "original adopted statement"
        assert ctx.current_assessment["id"] == str(judgment)
        assert "assessment_scope_outdated" in [o.reason for o in ctx.omissions]
        manifest = (await one(select(F.c.content_json).where(F.c.id == claim.input_artifact_id)))["content_json"]
        assert set(manifest["task_revisions"]) == {str(old_vid), str(current_vid)}

    async def test_c1_explicit_comparison_not_latest():
        cid, aids, _, rid = await fixture(3)
        await start(cid, rid)
        ctx = await service.read_context(T, cid, rid)
        pub = await service.publish(T, cid, rid, result(ctx, system=True))
        async with service.transaction(T) as store:
            next_run = await store.replace_members(cid, set(aids[:2]), expected_revision=1,
                actor=ACTOR, operation_id=uuid4())
        rid2 = UUID(next_run["pending_run_id"])
        await start(cid, rid2, 2)
        ctx2 = await service.read_context(T, cid, rid2)
        assert ctx2.prior_results == {}  # latest system result is not an implicit baseline
        await service.publish(T, cid, rid2, result(ctx2, system=True))
        async with service.transaction(T) as store:
            next_run = await store.replace_members(cid, set(aids), expected_revision=2,
                actor=ACTOR, operation_id=uuid4())
        rid3 = UUID(next_run["pending_run_id"])
        await start(cid, rid3, 3, comparison=UUID(pub["result_id"]))
        ctx3 = await service.read_context(T, cid, rid3)
        assert set(ctx3.prior_results) == {pub["result_id"]}
        assert ctx3.prior_results[pub["result_id"]]["conclusion_origin"] == "system"

    async def test_c1_citation_role_and_path():
        cid, aids, _, rid = await fixture(1)
        tid, _ = await task(cid, aids)
        claim = await start(cid, rid)
        ctx = await service.read_context(T, cid, rid)
        snapshot = (await one(select(F.c.content_json).where(F.c.id == claim.input_artifact_id)))["content_json"]
        ctx_id = UUID(snapshot["source_materials"][0]["id"])
        path = f"$.tasks.{tid}.revision"
        bad = c1.reference("artifact", ctx_id, "observation", path)
        await reject("context_citation_path_or_role_invalid", service.publish(T, cid, rid, result(ctx, [bad])))
        bad = c1.reference("artifact", ctx_id, "human_statement", "$.tasks.invented.revision")
        await reject("context_citation_path_or_role_invalid", service.publish(T, cid, rid, result(ctx, [bad])))
        good = c1.reference("artifact", ctx_id, "human_statement", path)
        out = await service.publish(T, cid, rid, result(ctx, [good]))
        assert out["adoption"]["state"] == "adopted"

    async def test_c1_size_limit_atomic_and_tenant():
        cid, _aids, mids, rid = await fixture(1)
        await reject("frozen_material_not_found", service.read_material(T, cid, rid, mids[0]))
        async with service.transaction(T) as store:
            await store.db.execute(update(C).where(C.c.id == cid).values(description="X" * c1.MAX_CONTEXT_BYTES))
        await reject("baseline_context_too_large", start(cid, rid))
        assert (await one(select(R.c.state).where(R.c.id == rid)))["state"] == "pending_update"
        assert await one(select(F.c.id).where(F.c.run_id == rid)) is None
        await reject("case_not_found", service.read_context(OTHER, cid, rid))

    async def test_c1_legacy_does_not_reconstruct_live():
        cid, _aids, _, rid = await fixture(1)
        async with service.transaction(T) as store:
            await store.case(cid)
            await store.run(cid, rid)
            now, input_id = await store.now(), uuid4()
            old = {"projection_version": "socai2.baseline-manifest.v1", "source_materials": []}
            await store.save_input_artifact(cid, rid, input_id, old, kind="input_snapshot",
                schema="socai2.page-model.v1", captured_at=now, refs=[], actor_id=USER)
            await store.db.execute(update(R).where(R.c.id == rid).values(state="running", input_artifact_id=input_id,
                operation_key=str(uuid4()), request_hash=digest({}), executor_version="synthetic.legacy",
                started_at=now))
        await reject("frozen_c1_context_not_available", service.read_context(T, cid, rid))

    async def test_c1_json_null_and_truncated_material():
        cid, aids, _, rid = await fixture(2)
        async with service.transaction(T) as store:
            empty, truncated = uuid4(), uuid4()
            await store.db.execute(insert(m.AlertMaterials.__table__).values(id=empty, tenant_id=T,
                alert_id=aids[0], revision=2, raw_json=None, ocsf_json=None,
                detection={}, source_scope={}, material_state="complete", retention={}))
            await material(store, aids[1], truncated, 2, "synthetic truncated original", state="truncated")
            await store.db.execute(update(A).where(A.c.id == aids[0]).values(latest_material_id=empty))
            await store.db.execute(update(A).where(A.c.id == aids[1]).values(latest_material_id=truncated))
        await start(cid, rid)
        ctx = await service.read_context(T, cid, rid)
        assert ctx.alerts[str(aids[0])].material["has_raw"] is False
        assert "source_material_no_raw" in ctx.alerts[str(aids[0])].limitations
        assert "source_material_truncated" in ctx.alerts[str(aids[1])].limitations

    checks = [test_c1_all_members_and_contract, test_c1_source_versions_survive_edits,
        test_c1_same_statement_pointer_selection, test_c1_incomplete_and_wider_scope,
        test_c1_paired_triage_and_feedback, test_c1_adopted_old_task_and_current_revision,
        test_c1_explicit_comparison_not_latest, test_c1_citation_role_and_path,
        test_c1_size_limit_atomic_and_tenant, test_c1_legacy_does_not_reconstruct_live,
        test_c1_json_null_and_truncated_material]
    for check in checks:
        if only is not None and check.__name__ not in only:
            continue
        try:
            detail = await asyncio.wait_for(check(), 35)
            record(check.__name__, True, detail)
        except Exception:  # noqa: BLE001 -- keep each independent test's original failure
            record(check.__name__, False, traceback.format_exc())
