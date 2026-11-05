"""Consume a specifically recorded synthetic Fusion insert using real Case C1."""
import os
import traceback
from datetime import timedelta
from uuid import UUID, uuid4

from app.socai2.baseline_contracts import Actor, Limits, Start
from app.socai2.baseline_model_view import build
from app.socai2.baseline_semantics import material_projection
from app.socai2.case_contracts import CaseCreate
from app.socai2.case_service import CaseService
from socai2_test_model_view import model_data
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

T, USER = UUID(int=1), UUID(int=3)


async def run_checks(engine, record, only=None):
    async def test_fusion_persisted_material_enters_case_frozen_context():
        aid = UUID(os.environ["SOCAI2_FUSION_BRIDGE_ALERT_ID"])
        service = CaseService(async_sessionmaker(engine, expire_on_commit=False))
        actor = Actor(user_id=USER, name="synthetic-fusion-bridge@example.invalid")
        async with service.transaction(T, readonly=True) as store:
            saved = (await store.db.execute(text("""SELECT a.source_namespace,m.raw_json,m.id FROM socai2.alerts a
                JOIN socai2.alert_materials m ON m.tenant_id=a.tenant_id AND m.id=a.latest_material_id
                WHERE a.tenant_id=:tenant AND a.id=:alert"""), {"tenant": T, "alert": aid})).mappings().one()
            assert saved["source_namespace"] == "fusion.v1"
            assert saved["raw_json"]["source"] == "synthetic-socai2-fusion"
            now = await store.now()
        created = await service.create_case(T, CaseCreate(operation_key=uuid4(), title="synthetic Fusion to Case",
            alert_ids=[aid]), actor=actor)
        async def no_external_executor(claim):
            assert claim.newly_claimed
        claim = await service.start(T, created.case_id, created.pending_run_id,
            Start(expected_scope_revision=1, operation_key=uuid4()), actor=actor, executor=no_external_executor,
            executor_version="synthetic.c1-only.v1", limits=Limits(max_model_calls=0, max_tokens=0,
                max_tool_calls=0, max_rows_per_query=200, deadline_at=now + timedelta(seconds=120), policy_version="synthetic"))
        context = await service.read_context(T, created.case_id, claim.run_id)
        source = context.alerts[str(aid)]
        assert source.material["id"] == str(saved["id"])
        assert source.material["detection"]["confidence_value"] == 87
        assert source.alert["original_vendor"] == "original maker" and source.alert["vendor_alert_id"] == "vendor-finding"
        assert len(source.objects) == 7 and len(source.source_refs) == 2
        assert len(context.incidents) == 1 and all(not i.diagnosis_usable for i in context.incidents.values())
        material = await service.read_frozen_material(T, created.case_id, claim.run_id, saved["id"])
        assert material["raw_json"] == saved["raw_json"] and material["raw_text"] == "synthetic original raw"
        semantics = material_projection(material)
        assert any(f["source_path"].endswith(".process.pid") and f["value"] == 42 for f in semantics["fields"])
        view = build(context, claim.input_artifact_id, [], [])
        assert view["ready"] and view["bytes"] <= 8192
        body = model_data(view["messages"][1]["content"])
        assert "synthetic original raw" not in view["messages"][1]["content"]
        assert any(i["value"].get("detection", {}).get("confidence_value") == 87
            for i in body["items"] if isinstance(i["value"], dict)), view["omissions"]
        # This check deliberately stops after C1; it never executes a model.
        async with service.transaction(T) as store:
            await store.mark_unknown(created.case_id, claim.run_id)
        return {"alert_id": str(aid), "material_id": str(saved["id"]), "case_id": str(created.case_id),
            "run_id": str(claim.run_id), "model_view_bytes": view["bytes"], "real_model_calls": 0}

    check = test_fusion_persisted_material_enters_case_frozen_context
    if only is None or check.__name__ in only:
        try:
            record(check.__name__, True, await check())
        except Exception:  # noqa: BLE001 -- preserve original integration failure
            record(check.__name__, False, traceback.format_exc())
