"""Synthetic A/I storage contracts on the existing isolated PostgreSQL."""
import asyncio
import traceback
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2.baseline_contracts import Actor, Limits, Start
from app.socai2.baseline_store import StoreError
from app.socai2.stage_result_contracts import AlertOutput, IncidentOutput
from app.socai2.stage_results import AS, A, D, F, I, R, StageResultService
from pydantic import ValidationError
from sqlalchemy import insert, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

T, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
LIMITS = Limits(max_model_calls=0, max_tokens=0, max_tool_calls=0, max_rows_per_query=0,
                deadline_at=None, policy_version="synthetic.storage-only")


async def run_checks(engine, record, only=None):
    service = StageResultService(async_sessionmaker(engine, expire_on_commit=False))

    async def fixture(n=2):
        iid, aids, mids = uuid4(), [uuid4() for _ in range(n)], [uuid4() for _ in range(n)]
        async with service.transaction(T) as s:
            await s.db.execute(insert(I).values(id=iid, tenant_id=T, source_namespace="synthetic.stage",
                source_incident_id=str(iid), title="synthetic incident"))
            for aid, mid in zip(aids, mids):
                await s.db.execute(insert(A).values(id=aid, tenant_id=T, source_namespace="synthetic.stage",
                    source_identity_key=str(aid), title="synthetic member", handling_status="completed", disposition="benign"))
                await material(s, aid, mid, 1)
                await s.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=T, incident_id=iid,
                    alert_id=aid, membership_source="fusion", correlation_basis={}, basis_version="synthetic", source_operation_id=uuid4()))
        return iid, aids, mids

    async def material(s, aid, mid, revision):
        await s.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=T, alert_id=aid, revision=revision,
            raw_json={"process": {"pid": 42}}, detection={}, source_scope={}, material_state="complete", retention={}))
        await s.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))

    async def begin(kind, identity, op=None, producer="synthetic.stage.v1"):
        return await service.begin(T, kind, identity, op or uuid4(), producer=producer, limits=LIMITS)

    def ref(mid):
        return {"type": "alert_material", "id": str(mid), "external": None, "source_path": "$.raw_json.process.pid",
            "row_keys": [], "role": "observation"}

    def alert(mid, **changes):
        return AlertOutput.model_validate({"verdict": "needs_review", "rationale": "synthetic observed PID; intent unknown",
            "confidence": 0, "score_state": "available", "explanation": "synthetic explanation", "generation_method": "template",
            "source_refs": [ref(mid)], "recommendations": [], "limitations": ["synthetic only"], **changes})

    def incident(mid):
        return IncidentOutput(summary="synthetic common background", conclusion="synthetic unresolved relationship",
            findings=[], source_refs=[ref(mid)], open_questions=[], limitations=["synthetic; no causal proof"])

    async def one(table, identity):
        async with service.transaction(T, readonly=True) as s:
            return await s.one(select(table).where(*s.where(table, table.c.id == identity)))

    async def reject(code, call):
        try:
            await call
        except StoreError as exc:
            assert exc.code == code, exc.code
        else:
            raise AssertionError(code)

    async def test_stage_alert_pair_explanation_and_case_input():
        iid, aids, mids = await fixture()
        claim = await begin("alert_basic", aids[0])
        out = await service.finish(T, claim["run_id"], alert(mids[0]))
        assert out["adopted"] and await service.freshness(T, claim["run_id"])
        row = await one(A, aids[0]); assessment = await one(AS, UUID(out["result_id"]))
        assert assessment["confidence"] == 0 and assessment["input_material_id"] == mids[0]
        assert row["handling_status"] == "completed" and row["disposition"] == "benign"
        assert (await one(F, row["latest_explanation_id"]))["content_json"]["body"] == "synthetic explanation"
        ic = await begin("incident_diagnosis", iid)
        frozen = (await one(F, ic["input_artifact_id"]))["content_json"]
        index = next(n for n, row in enumerate(frozen["members"]) if row["alert"]["id"] == str(aids[0]))
        prior = {"type": "artifact", "id": str(ic["input_artifact_id"]), "external": None,
            "source_path": f"$.members.{index}.triage", "row_keys": [], "role": "prior_analysis"}
        data = incident(mids[0]).model_dump(mode="json")
        data["source_refs"].append(prior)
        result = await service.finish(T, ic["run_id"], IncidentOutput.model_validate(data))
        assert result["adopted"] and await service.freshness(T, ic["run_id"])
        cid = uuid4()
        async with service.transaction(T) as s:
            await s.db.execute(insert(m.Cases).values(id=cid, tenant_id=T, title="synthetic stage bridge"))
        change = await service.replace_members(T, cid, aids, expected_revision=0,
            actor=Actor(user_id=USER, name="synthetic"), operation_id=uuid4())
        async def no_execution(_):
            return None
        rid = UUID(change["pending_run_id"])
        await service.start(T, cid, rid, Start(expected_scope_revision=1, operation_key=uuid4()),
            actor=Actor(user_id=USER, name="synthetic"), executor=no_execution, executor_version="synthetic.no-execution", limits=LIMITS)
        ctx = await service.read_context(T, cid, rid)
        assert ctx.alerts[str(aids[0])].triage["id"] == out["result_id"]
        assert ctx.incidents[str(iid)].diagnosis["id"] == result["result_id"]
        assert ctx.citation_roles[f"$.incidents.{iid}.diagnosis"] == "prior_analysis"
        async with service.transaction(T) as s:
            await s.mark_unknown(cid, rid)
        return {"alert_run": str(claim["run_id"]), "incident_run": str(ic["run_id"]), "case_run": str(rid)}

    async def test_stage_concurrent_claim_and_publication_replay():
        _, aids, mids = await fixture(1)
        op = uuid4()
        claims = await asyncio.gather(*(begin("alert_basic", aids[0], op) for _ in range(3)))
        assert sum(c["newly_claimed"] for c in claims) == 1
        rid = claims[0]["run_id"]
        outputs = await asyncio.gather(*(service.finish(T, rid, alert(mids[0])) for _ in range(3)))
        assert outputs[0] == outputs[1] == outputs[2]
        await reject("operation_key_conflict", begin("alert_basic", aids[0], op, "other"))
        await reject("stage_publication_conflict", service.finish(T, rid, alert(mids[0], rationale="changed")))

    async def test_stage_material_change_history_not_adopted():
        _, aids, mids = await fixture(1)
        claim = await begin("alert_basic", aids[0])
        async with service.transaction(T) as s:
            await material(s, aids[0], uuid4(), 2)
        result = await service.finish(T, claim["run_id"], alert(mids[0]))
        assert result["reason"] == "input_changed" and not result["adopted"]
        assert (await one(A, aids[0]))["latest_triage_id"] is None
        assert (await one(AS, UUID(result["result_id"])))["input_material_id"] == mids[0]
        assert not await service.freshness(T, claim["run_id"])

    async def test_stage_older_result_cannot_replace_newer():
        _, aids, mids = await fixture(1)
        older, newer = await begin("alert_basic", aids[0]), await begin("alert_basic", aids[0])
        new = await service.finish(T, newer["run_id"], alert(mids[0]))
        old = await service.finish(T, older["run_id"], alert(mids[0]))
        assert old["reason"] == "newer_result_exists"
        assert str((await one(A, aids[0]))["latest_triage_id"]) == new["result_id"]

    async def test_stage_incident_input_change_and_later_freshness():
        iid, aids, mids = await fixture()
        first = await begin("incident_diagnosis", iid)
        saved = await service.finish(T, first["run_id"], incident(mids[0]))
        next_run = await begin("incident_diagnosis", iid)
        ac = await begin("alert_basic", aids[0])
        await service.finish(T, ac["run_id"], alert(mids[0]))
        assert not await service.freshness(T, first["run_id"])
        stale = await service.finish(T, next_run["run_id"], incident(mids[0]))
        assert stale["reason"] == "input_changed"
        assert str((await one(I, iid))["latest_diagnosis_id"]) == saved["result_id"]

    async def test_stage_failed_unknown_attempt_preserves_success():
        iid, _, mids = await fixture()
        success = await begin("incident_diagnosis", iid)
        saved = await service.finish(T, success["run_id"], incident(mids[0]))
        failed = await begin("incident_diagnosis", iid)
        await service.stop(T, failed["run_id"], state="unknown", code="transport_unknown")
        await reject("stage_run_not_running", service.finish(T, failed["run_id"], incident(mids[0])))
        await service.stop(T, failed["run_id"], state="failed", code="confirmed_failure")
        await service.stop(T, failed["run_id"], state="failed", code="confirmed_failure")
        assert str((await one(I, iid))["latest_diagnosis_id"]) == saved["result_id"]
        async with service.transaction(T, readonly=True) as s:
            row = await s.one(select(D).where(D.c.source_run_id == failed["run_id"]))
            assert row["state"] == "failed" and row["diagnosis"] is None

    async def test_stage_reference_and_tenant_rejections():
        _, aids, mids = await fixture()
        claim = await begin("alert_basic", aids[0])
        await reject("stage_run_not_found", service.finish(OTHER, claim["run_id"], alert(mids[0])))
        await reject("stage_reference_outside_frozen_input", service.finish(T, claim["run_id"], alert(mids[1])))
        bad = {**ref(mids[0]), "source_path": "$.raw_json.not_received"}
        await reject("stage_reference_path_invalid", service.finish(T, claim["run_id"], alert(mids[0], source_refs=[bad])))
        try:
            alert(mids[0], score_state="failed", confidence=.7)
        except ValidationError:
            pass
        else:
            raise AssertionError("uncomputed score accepted")
        assert (await one(R, claim["run_id"]))["state"] == "running"

    async def test_stage_prior_analysis_cannot_be_observation():
        iid, aids, mids = await fixture(1)
        ac = await begin("alert_basic", aids[0])
        await service.finish(T, ac["run_id"], alert(mids[0]))
        ic = await begin("incident_diagnosis", iid)
        data = incident(mids[0]).model_dump(mode="json")
        data["source_refs"] = [{"type": "artifact", "id": str(ic["input_artifact_id"]), "external": None,
            "source_path": "$.members.0.triage", "row_keys": [], "role": "observation"}]
        await reject("stage_input_reference_role_or_path_invalid", service.finish(T, ic["run_id"], IncidentOutput.model_validate(data)))
        data["source_refs"][0]["role"] = "prior_analysis"
        assert (await service.finish(T, ic["run_id"], IncidentOutput.model_validate(data)))["adopted"]

    async def test_stage_deferred_commit_rolls_back_entire_output():
        _, aids, mids = await fixture(1)
        claim = await begin("alert_basic", aids[0])
        class FailingService(StageResultService):
            @asynccontextmanager
            async def transaction(self, tenant_id, **kwargs):
                async with super().transaction(tenant_id, **kwargs) as s:
                    yield s
                    await s.db.execute(update(A).where(A.c.id == aids[0]).values(latest_explanation_id=uuid4()))
        failing = FailingService(service.sessions)
        try:
            await failing.finish(T, claim["run_id"], alert(mids[0]))
        except DBAPIError:
            pass
        else:
            raise AssertionError("deferred FK should fail")
        assert (await one(R, claim["run_id"]))["state"] == "running"
        assert (await one(A, aids[0]))["latest_triage_id"] is None
        async with service.transaction(T, readonly=True) as s:
            assert not (await s.db.execute(select(AS.c.id).where(AS.c.source_run_id == claim["run_id"]))).all()
            kinds = (await s.db.execute(select(F.c.kind).where(F.c.run_id == claim["run_id"]))).scalars().all()
            assert kinds == ["input_snapshot"]

    async def test_stage_oversize_input_atomic_rejection():
        _, aids, _ = await fixture(1)
        async with service.transaction(T) as s:
            await s.db.execute(update(A).where(A.c.id == aids[0]).values(description="x" * 1048576))
        await reject("stage_artifact_too_large", begin("alert_basic", aids[0]))
        async with service.transaction(T, readonly=True) as s:
            assert not (await s.db.execute(select(R.c.id).where(R.c.alert_id == aids[0]))).all()

    checks = [v for k, v in locals().copy().items() if k.startswith("test_stage_")]
    for check in checks:
        if only and check.__name__ not in only:
            continue
        try:
            detail = await asyncio.wait_for(check(), 40)
            record(check.__name__, True, detail)
        except Exception:  # noqa: BLE001 -- retain original independent failures
            record(check.__name__, False, traceback.format_exc())
