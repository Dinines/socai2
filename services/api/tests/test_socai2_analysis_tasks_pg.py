"""Direct lifecycle checks on an explicitly selected isolated PG, with retained fixtures."""
import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.analysis_task_store import A, R, S, T, active_case_work
from app.socai2.analysis_tasks import AnalysisTaskService
from app.socai2.baseline_contracts import Actor
from app.socai2.baseline_store import StoreError, digest, encoded
from app.socai2.case_contracts import CaseQueueQuery
from app.socai2.case_management import manage_case, read_management
from app.socai2.case_management_contracts import CaseLifecycleRequest
from app.socai2.case_reader import CaseReader
from app.socai2.case_service import CaseService
from app.socai2.human_task_service import HumanTaskService
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

TENANT, ACTOR = UUID(int=1), Actor(user_id=UUID(int=3), name="Lifecycle fixture")
ROOT = Path(__file__).resolve().parents[3]


async def expect(code, operation):
    try:
        await operation()
    except StoreError as exc:
        assert exc.code == code, (code, exc.code)
    else:
        raise AssertionError("expected " + code)


async def expect_constraint(operation):
    try:
        await operation()
    except IntegrityError:
        return
    raise AssertionError("expected database rejection")


async def run_checks(engine, record, only=None):
    if only and "analysis_lifecycle_flow" not in only:
        return
    policy = AnalysisTaskPolicy(**json.loads((ROOT / "deploy/local-investigation/analysis-tasks.json").read_text()))
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = AnalysisTaskService(sessions, policy)
    immediate = AnalysisTaskService(sessions, replace(policy, retry_delay_seconds=0))
    cases = CaseService(sessions)
    identities = []
    result_identities = []
    result_examples = {}

    async def fixture(subject_type="case"):
        aid, sid = uuid4(), uuid4()
        async with service.transaction(TENANT) as store:
            await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=TENANT,
                source_namespace="analysis-lifecycle-20261114", source_identity_key=str(aid), title="Lifecycle fixture"))
            if subject_type == "alert":
                sid = aid
            elif subject_type == "case":
                await store.db.execute(insert(m.Cases).values(id=sid, tenant_id=TENANT, title="Lifecycle fixture " + str(sid)))
                await store.db.execute(insert(m.CaseAlerts).values(id=uuid4(), tenant_id=TENANT, case_id=sid,
                    alert_id=aid, membership_source="manual", source_operation_id=uuid4()))
            else:
                await store.db.execute(insert(m.Incidents).values(id=sid, tenant_id=TENANT,
                    source_namespace="analysis-lifecycle-20261114", source_incident_id=str(sid), title="Lifecycle fixture"))
                await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=TENANT,
                    incident_id=sid, alert_id=aid, membership_source="manual", correlation_basis={},
                    basis_version="fixture.v1", source_operation_id=uuid4()))
        identities.append(sid)
        return sid

    async def submit(sid, *, selected=service, subject_type="case", key=None, intent="check"):
        return await selected.submit(TENANT, kind={"case": "case_investigation", "alert": "alert_triage",
            "incident": "incident_diagnosis"}[subject_type], subject_id=sid, intent=intent,
            source="user" if subject_type != "alert" else "ingress", operation_key=key or uuid4(), submitted_by=ACTOR.user_id)

    async def start(tid, selected=service):
        async with selected.transaction(TENANT) as store:
            return await store.start_attempt(tid)

    async def finish(aid, selected=service, **values):
        async with selected.transaction(TENANT) as store:
            return await store.finish_attempt(aid, **values)

    async def attach(attempt, *, selected=service, state="running"):
        # Saved Run/input fixtures exercise actual constraints; no model was called.
        rid, fid = uuid4(), uuid4()
        kind, sid = attempt["subject_type"], attempt["subject_id"]
        async with selected.transaction(TENANT) as store:
            now = await store.now()
            values = {"id": rid, "tenant_id": TENANT, kind + "_id": sid,
                "kind": {"case": "baseline", "alert": "alert_basic", "incident": "incident_diagnosis"}[kind],
                "title": "Synthetic lifecycle Run", "purpose": "Persistence validation only", "trigger": "manual"}
            if kind == "case":
                case = await store.case(sid)
                values.update(state="pending_update", scope_revision=case["scope_revision"], scope_kind="whole_case")
            else:
                values.update(state="running", started_at=now, input_artifact_id=fid,
                    operation_key=str(uuid4()), request_hash=digest({"run": str(rid)}), executor_version="lifecycle-fixture.v1")
            await store.db.execute(insert(R).values(**values))
            payload = {"fixture": True, "member_scope": str(sid), "attempt_no": attempt["attempt_no"]}
            await store.db.execute(insert(m.Artifacts).values(id=fid, tenant_id=TENANT, run_id=rid,
                **{kind + "_id": sid}, kind="input_snapshot", schema_version="synthetic.v1",
                mime_type="application/json", captured_at=now, material_state="complete", source_refs=[], retention={},
                content_json=payload, sha256=digest(payload), size_bytes=len(encoded(payload))))
            if kind == "case":
                for member in await store.members(sid):
                    await store.db.execute(insert(m.RunMembers).values(id=uuid4(), tenant_id=TENANT,
                        case_id=sid, run_id=rid, alert_id=member))
                await store.db.execute(update(R).where(*store.where(R, R.c.id == rid)).values(state="running",
                    started_at=now, input_artifact_id=fid, operation_key=str(uuid4()),
                    request_hash=digest(payload), executor_version="lifecycle-fixture.v1"))
            await store.bind_run(attempt["id"], rid, input_digest=digest(payload))
            if state != "running":
                await store.db.execute(update(R).where(*store.where(R, R.c.id == rid)).values(
                    state=state, ended_at=await store.now() if state in {"completed", "failed"} else None))
        return rid, fid

    async def sql_mutate(table, identity, **values):
        async with service.transaction(TENANT) as store:
            await store.db.execute(update(table).where(*store.where(table, table.c.id == identity)).values(**values))

    async def save_result_reference(attempt, run_id, input_id):
        identity, sid, subject_type = uuid4(), attempt["subject_id"], attempt["subject_type"]
        async with service.transaction(TENANT) as store:
            now = await store.now()
            values = {"id": identity, "tenant_id": TENANT, "source_run_id": run_id}
            if subject_type == "alert":
                table = m.AlertAssessments
                values.update(alert_id=sid, kind="triage", verdict="needs_review", producer="synthetic.v1",
                    actor={}, assessed_at=now, operation_key=str(uuid4()))
                human_id = uuid4()
                await store.db.execute(insert(table).values(**{**values, "id": human_id,
                    "kind": "human_feedback", "operation_key": str(uuid4())}))
                result_identities.append(human_id)
                result_type, result_kind = "alert_assessment", "triage"
            elif subject_type == "incident":
                table = m.IncidentDiagnoses
                values.update(incident_id=sid, revision=1, state="completed", input_artifact_id=input_id,
                    source_fingerprint="0" * 64, producer="synthetic.v1", requested_at=now,
                    generated_at=now, summary="Synthetic diagnosis reference")
                result_type = result_kind = "incident_diagnosis"
            else:
                table = m.Results
                values.update(case_id=sid, kind="baseline", title="Synthetic saved reference",
                    purpose="Task result contract validation", conclusion_state="unavailable",
                    conclusion_origin="system", validation_state="system_only", closing_note="Synthetic only",
                    findings=[], questions=[], recommendations=[], change_kind="initial", case_impact={
                        "summary": None, "supported_changes": [], "cannot_generalize": [], "next_steps": [],
                        "affected_scope": {"kind": "whole_case", "alert_ids": [str(a) for a in await store.members(sid)],
                            "object_keys": [], "window_start": None, "window_end": None, "limitations": []}},
                    input_artifact_id=input_id, delivery_state="partial", created_at=now, operation_key=str(uuid4()))
                result_type, result_kind = "case_result", "baseline"
            await store.db.execute(insert(table).values(**values))
        result_identities.append(identity)
        expected = {"result_type": result_type, "id": identity, "source_run_id": run_id, "kind": result_kind}
        result_examples[subject_type] = expected
        assert (await service.read_task(TENANT, subject_type, sid, attempt["task_id"]))["results"] == [expected]
        return expected

    cid = await fixture()
    key = uuid4()
    receipt = await submit(cid, key=key)
    assert receipt == await submit(cid, key=key)
    await expect("operation_key_conflict", lambda: submit(cid, key=key, intent="rerun"))
    async with service.transaction(TENANT, readonly=True) as store:
        assert not await store.one(select(R.c.id).where(*store.where(R, R.c.case_id == cid)))
        assert not await store.one(select(A.c.id).where(*store.where(A, A.c.task_id == receipt["task_id"])))
    read = await service.read_task(TENANT, "case", cid, receipt["task_id"])
    assert read["status"] == "accepted" and read["started_at"] is None and not read["attempts"]
    record("accept_idempotency_no_fake_run", True, {"case_id": cid, "task_id": receipt["task_id"]})

    skipped = await submit(cid)
    async with service.transaction(TENANT) as store:
        await store.skip(skipped["task_id"], "no_changes")
    empty = await service.read_task(TENANT, "case", cid, skipped["task_id"])
    assert empty["status"] == "skipped" and not empty["attempts"] and empty["started_at"] is None
    first = await start(receipt["task_id"])
    other = await submit(cid)
    await expect("analysis_subject_busy", lambda: start(other["task_id"]))
    management = await read_management(cases, TENANT, cid)
    assert not management.can_close and not management.blocking_runs
    await expect("case_active_run_prevents_close", lambda: manage_case(cases, TENANT, cid,
        CaseLifecycleRequest(operation_key=uuid4(), expected_row_version=management.case.row_version), ACTOR, action="case_closed"))
    record("preparation_serial_and_close_guard", True, {"attempt_without_run": first["id"], "no_changes": empty})

    rid, fid = await attach(first)
    async def illegal_freeze():
        await sql_mutate(A, first["id"], input_digest="f" * 64)
    await expect_constraint(illegal_freeze)
    await finish(first["id"], outcome="unknown", error_code="call_timeout", error_stage="model")
    read = await service.read_task(TENANT, "case", cid, receipt["task_id"])
    assert read["status"] == "failed" and read["reason_code"] == "call_timeout"
    assert read["attempts"][0]["local_ended_at"] and read["attempts"][0]["outcome"] == "unknown"
    assert (await read_management(cases, TENANT, cid)).can_close
    async with service.transaction(TENANT, readonly=True) as store:
        run = await store.one(select(R).where(*store.where(R, R.c.id == rid)))
        assert run["state"] == "unknown" and run["ended_at"] is None and run["input_artifact_id"] == fid
        pending = dict(run)
        pending.update(state="pending_update", started_at=None, ended_at=None)
        case = await store.case(cid, lock=False)
        assert (await CaseReader(store).eligibility(case, pending, 1)).can_start
    legacy_pending = uuid4()
    async with service.transaction(TENANT) as store:
        case = await store.case(cid)
        await store.db.execute(insert(R).values(id=legacy_pending, tenant_id=TENANT, case_id=cid,
            kind="baseline", title="Legacy pending fixture", purpose="Queue availability check", trigger="manual",
            state="pending_update", scope_kind="whole_case", scope_revision=case["scope_revision"]))
    async with service.transaction(TENANT, readonly=True) as store:
        queue = await CaseReader(store).queue(CaseQueueQuery(q=str(cid)))
        assert queue.total == 1
        assert next(b for b in queue.items[0].baseline_records if b.run.id == legacy_pending).start_eligibility.can_start
    second = await start(other["task_id"])
    async with service.transaction(TENANT) as store:
        queue = await CaseReader(store).queue(CaseQueueQuery(q=str(cid)))
        assert not next(b for b in queue.items[0].baseline_records if b.run.id == legacy_pending).start_eligibility.can_start
        await store.db.execute(update(R).where(*store.where(R, R.c.id == legacy_pending)).values(
            state="cancelled", ended_at=await store.now()))
    second_run, second_input = await attach(second, state="completed")
    await finish(second["id"], outcome="completed")
    await save_result_reference(second, second_run, second_input)
    async with service.transaction(TENANT, readonly=True) as store:
        state = await store.one(select(S).where(*store.where(S, S.c.subject_id == cid)))
        assert state["last_completed_attempt_id"] == second["id"] and state["stopped_task_id"] is None
    record("unknown_ended_releases_and_preserves_history", True, {"unknown_run_id": rid,
        "failed_task": read, "next_task": await service.read_task(TENANT, "case", cid, other["task_id"])})

    retry_case = await fixture()
    rt = await submit(retry_case, selected=immediate)
    r1 = await start(rt["task_id"], immediate)
    r1_run, _ = await attach(r1, selected=immediate, state="failed")
    await finish(r1["id"], immediate, outcome="failed", error_code="service_unavailable", retryable=True)
    waiting = await immediate.read_task(TENANT, "case", retry_case, rt["task_id"])
    assert waiting["status"] == "accepted" and waiting["retry_count"] == 0 and waiting["next_retry_at"]
    r2 = await start(rt["task_id"], immediate)
    r2_run, _ = await attach(r2, selected=immediate, state="failed")
    await finish(r2["id"], immediate, outcome="failed", error_code="service_unavailable", retryable=True)
    exhausted = await immediate.read_task(TENANT, "case", retry_case, rt["task_id"])
    assert exhausted["status"] == "failed" and exhausted["reason_code"] == "retry_exhausted"
    assert exhausted["retry_count"] == 1 and [a["run_id"] for a in exhausted["attempts"]] == [r1_run, r2_run]
    assert [a["attempt_no"] for a in exhausted["attempts"]] == [1, 2]
    await expect("analysis_task_not_waiting", lambda: start(rt["task_id"]))
    record("retry_same_task_new_attempt_and_run", True, exhausted)

    delayed_case = await fixture()
    delayed = await submit(delayed_case)
    da = await start(delayed["task_id"])
    await finish(da["id"], outcome="failed", error_code="connection_refused", retryable=True)
    delay_read = await service.read_task(TENANT, "case", delayed_case, delayed["task_id"])
    assert (delay_read["next_retry_at"] - delay_read["attempts"][0]["failed_at"]).total_seconds() == policy.retry_delay_seconds
    await expect("retry_not_due", lambda: start(delayed["task_id"]))
    assert delay_read["attempts"][0]["run_id"] is None
    record("default_delay_preparation_failure_recorded", True, delay_read)

    late_case = await fixture()
    late = await submit(late_case)
    # Simulate an already accepted task waiting beyond its configured window.
    async with service.transaction(TENANT) as store:
        await store.db.execute(update(m.Cases).where(m.Cases.id == late_case).values(
            created_at=await store.now() - timedelta(seconds=policy.automatic_window_seconds + 1)))
    late_attempt = await start(late["task_id"])
    assert late_attempt is not None
    await finish(late_attempt["id"], outcome="failed", error_code="connection_refused", retryable=True)
    late_read = await service.read_task(TENANT, "case", late_case, late["task_id"])
    assert late_read["status"] == "failed" and late_read["reason_code"] == "retry_stopped"
    closed_case = await fixture()
    closed_task = await submit(closed_case)
    management = await read_management(cases, TENANT, closed_case)
    await manage_case(cases, TENANT, closed_case, CaseLifecycleRequest(operation_key=uuid4(),
        expected_row_version=management.case.row_version), ACTOR, action="case_closed")
    assert await start(closed_task["task_id"]) is None
    assert (await service.read_task(TENANT, "case", closed_case, closed_task["task_id"]))["reason_code"] == "closed_before_start"
    record("accepted_crosses_expiry_once_closed_skips", True, late_read)

    for subject_type in ("alert", "incident"):
        sid = await fixture(subject_type)
        item = await submit(sid, subject_type=subject_type)
        attempt = await start(item["task_id"])
        run, input_id = await attach(attempt, state="completed")
        await finish(attempt["id"], outcome="completed")
        expected = await save_result_reference(attempt, run, input_id)
        page = await service.list_tasks(TENANT, subject_type, sid)
        assert page["total"] == 1 and page["items"][0]["latest_run_id"] == run
        assert page["items"][0]["results"] == [expected]
        record(subject_type + "_task_run_readback", True, page)
    record("task_result_reference_contract", True, {"results": result_examples,
        "alert_human_feedback_excluded": True, "old_field_aliases_absent": True})

    # Exercise immutable history/real scopes directly, rather than only DTO mocks.
    await expect_constraint(lambda: sql_mutate(A, first["id"], error_code="overwritten"))
    await expect_constraint(lambda: sql_mutate(T, receipt["task_id"], intent="rerun"))
    async def cross_subject():
        async with service.transaction(TENANT) as store:
            values = dict(first)
            values.update(id=uuid4(), task_id=delayed["task_id"], attempt_no=99)
            await store.db.execute(insert(A).values(**values))
    await expect_constraint(cross_subject)
    await expect("analysis_task_not_found", lambda: service.read_task(TENANT, "case", retry_case, receipt["task_id"]))
    await expect("subject_not_found", lambda: service.read_task(UUID(int=2), "case", cid, receipt["task_id"]))
    record("history_and_subject_boundaries", True, {"tenant_isolation": True, "immutable": True})

    async def snapshot():
        async with service.transaction(TENANT, readonly=True) as store:
            rows = []
            for table in (T, A, S):
                data = (await store.db.execute(select(table).where(*store.where(table,
                    table.c.subject_id.in_(identities))).order_by(table.c.subject_id))).mappings()
                rows.append([dict(r) for r in data])
            for table in (m.Results.__table__, m.AlertAssessments.__table__, m.IncidentDiagnoses.__table__):
                data = (await store.db.execute(select(table).where(*store.where(table,
                    table.c.id.in_(result_identities))).order_by(table.c.id))).mappings()
                rows.append([dict(r) for r in data])
            return digest(json.loads(json.dumps(rows, default=str, sort_keys=True)))
    before = await snapshot()
    found, cursor = [], None
    while True:
        page = await service.list_tasks(TENANT, "case", cid, limit=1, cursor=cursor)
        found += [r["task_id"] for r in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert len(found) == len(set(found)) == 3
    first_page = await service.list_tasks(TENANT, "case", cid, limit=1)
    await expect("invalid_cursor", lambda: service.list_tasks(TENANT, "case", retry_case, cursor=first_page["next_cursor"]))
    assert before == await snapshot()
    async with service.transaction(TENANT, readonly=True) as store:
        active, running = await active_case_work(store, cid)
        assert not active and not running
        count = (await store.db.execute(select(func.count()).select_from(T).where(
            *store.where(T, T.c.subject_id.in_(identities))))).scalar_one()
    record("task_paging_read_only", True, {"tasks_in_fixture": count, "pages": found, "sha256": before})

    # Reuse the existing complete persistence/adoption exercise: C1 and program
    # supplied results only, followed by the new unfinished task projection.
    from test_socai2_case_adoption_pg import exercise
    adoption_records = {}
    def adoption_record(name, value):
        adoption_records[name] = value
    human = HumanTaskService(sessions)
    adoption_case = await exercise(human, TENANT, ACTOR, adoption_record)
    result_id = adoption_records["initial-preview"].candidate.id
    before_adoption = await human.preview_result_adoption(TENANT, adoption_case, result_id)
    root = await submit(adoption_case)
    merged = await submit(adoption_case)
    async with service.transaction(TENANT) as store:
        await store.db.execute(update(T).where(*store.where(T, T.c.id == merged["task_id"])).values(
            state="merged", merged_into_task_id=root["task_id"], ended_at=await store.now()))
    pending_preview = await human.preview_result_adoption(TENANT, adoption_case, result_id)
    assert pending_preview.unfinished_analysis_tasks == [{"task_id": root["task_id"], "intent": "check", "status": "accepted"}]
    assert pending_preview.review_token != before_adoption.review_token
    assert pending_preview.requires_pending_work_acknowledgement
    ma = await start(root["task_id"])
    await finish(ma["id"], outcome="failed", error_code="invalid_input")
    original = await service.read_task(TENANT, "case", adoption_case, merged["task_id"])
    root_read = await service.read_task(TENANT, "case", adoption_case, root["task_id"])
    assert original["task_id"] == merged["task_id"] and original["status"] == "failed"
    assert original["attempts"] == root_read["attempts"]
    assert original["submitted_at"] != root_read["submitted_at"]
    final_preview = await human.preview_result_adoption(TENANT, adoption_case, result_id)
    assert not final_preview.unfinished_analysis_tasks
    record("adoption_and_merged_task_readback", True, {"case_id": adoption_case,
        "existing_adoption_checks": len(adoption_records), "pending": pending_preview.unfinished_analysis_tasks,
        "original_task": original, "root_task": root_read})
    record("analysis_lifecycle_flow", True, {"subjects": identities, "real_model_calls": 0})
