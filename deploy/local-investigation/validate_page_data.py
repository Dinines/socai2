"""DA01-DA06: local storage/readback fixtures. No models, Kafka or remote hosts."""
import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from config import API_ROLE, DATABASE, ROOT, TENANT, USER, read_private

sys.path.insert(0, str(ROOT / "services/api"))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://metadata:metadata@127.0.0.1:1/metadata")

from app.models import socai2 as m
from app.socai2.baseline_contracts import Actor
from app.socai2.baseline_store import StoreError, digest
from app.socai2.case_contracts import CaseQueueQuery
from app.socai2.case_data import export_page_data
from app.socai2.case_data_contracts import (
    CaseDataUpdate,
    EvidenceIndex,
    EvidencePublish,
)
from app.socai2.case_service import CaseService
from flow_export import TABLES, query_for
from initialize import pg_connect, safe_error
from sqlalchemy import insert, select, update
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

MIGRATION = "126_socai2_case_page_data.sql"
TEN, UID = UUID(TENANT), UUID(USER)
ACTOR = Actor(user_id=UID, name="Local investigator / synthetic data contract")


async def migrate(values):
    conn = await pg_connect(values)
    try:
        assert await conn.fetchval("SELECT current_database()") == DATABASE
        name = await conn.fetchval("SELECT name FROM public.aisoc_schema_migrations WHERE name=$1", MIGRATION)
        if not name:
            await conn.execute((ROOT / "services/api/migrations" / MIGRATION).read_text())
            await conn.execute("INSERT INTO public.aisoc_schema_migrations(name) VALUES($1)", MIGRATION)
        columns = await conn.fetchval("SELECT count(*) FROM information_schema.columns WHERE table_schema='socai2'")
        assert columns == 462, columns
        return {"migration": MIGRATION, "applied_now": not bool(name), "tables": 29, "columns": columns}
    finally:
        await conn.close()


async def seed(service, batch):
    output = []
    a, mat, ca = m.Alerts.__table__, m.AlertMaterials.__table__, m.CaseAlerts.__table__
    c, ass, src, cover = (m.Cases.__table__, m.CaseAssessments.__table__, m.CaseAssessmentSources.__table__, m.CaseAssessmentMembers.__table__)
    for label, verdict, classification in (("正常授权", "clean", "informational"),
            ("恶意样例", "malicious", "true_positive"), ("尚待核查", "unknown", None), ("尚无记录", None, None)):
        cid, aids, mids = uuid4(), [uuid4(), uuid4()], [uuid4(), uuid4()]
        async with service.transaction(TEN) as store:
            now = await store.now()
            await store.db.execute(insert(c).values(id=cid, tenant_id=TEN, title=f"数据合同样例 · {label} · {batch}",
                description="合成数据合同验收：固定录入的材料与判断，用于核对保存、来源及页面字段；未调用模型或执行调查。",
                source_namespace="synthetic.page-data.v1", scope_revision=1, created_by=UID))
            entries = []
            for i, (aid, mid) in enumerate(zip(aids, mids)):
                threat = {"namespace": "synthetic.validation", "key": "shared-threat", "label": "合成威胁记录"}
                raw = {"record_kind": "synthetic_page_data", "event": "材料记录 " + str(i+1),
                    "evidence": {"verdict": verdict or "unknown", "threat": threat}, "alternative_verdict": "clean"}
                await store.db.execute(insert(a).values(id=aid, tenant_id=TEN, source_namespace="synthetic.page-data.v1",
                    source_identity_key=str(aid), title=f"{label} · 合成材料 {i+1}", event_time=now, event_time_source="source",
                    latest_material_id=mid))
                await store.db.execute(insert(mat).values(id=mid, tenant_id=TEN, alert_id=aid, revision=1,
                    raw_json=raw, detection={}, source_scope={}, material_state="complete", retention={
                        "original_sha256": digest(raw), "retained_sha256": digest(raw), "truncated": False,
                        "reason": None, "omitted_paths": []}))
                await store.db.execute(insert(ca).values(id=uuid4(), tenant_id=TEN, case_id=cid, alert_id=aid,
                    added_by=UID, membership_source="manual", source_operation_id=uuid4()))
                ref = lambda path, role, mid=mid: {"type": "alert_material", "id": str(mid), "external": None,
                    "source_path": path, "row_keys": [], "role": role}
                entries.append({"evidence_id": "synthetic:"+str(uuid4()), "title": f"{label}证据 {i+1}",
                    "type": "合成原始材料", "alert_ids": [str(aid)], "object_keys": [],
                    "source_refs": [ref("/raw_json/event", "observation")], "verdict": verdict or "unknown",
                    "verdict_sources": [] if verdict in {None, "unknown"} else [ref("/raw_json/evidence/verdict", "source_label")],
                    "threat": {**threat, "source_refs": [ref("/raw_json/evidence/threat", "source_label")]} if verdict else None,
                    "remediation": None, "state": "active"})
            if verdict:
                sid, artifact = uuid4(), uuid4()
                conclusion = f"数据合同样例：{label}。此结论为固定导入材料，用于字段核对，未运行模型。"
                await store.save_input_artifact(cid, None, artifact, {"conclusion": conclusion, "synthetic": True},
                    kind="source_snapshot", schema="socai2.synthetic-page-judgment.v1", captured_at=now, refs=[], actor_id=UID)
                await store.db.execute(insert(ass).values(id=sid, tenant_id=TEN, case_id=cid, revision=1,
                    conclusion=conclusion, origin="legacy", validity="legacy_unverified", scope_revision=1,
                    formed_at=now, adopted_at=now, adopted_by=UID, actor=ACTOR.snapshot(), reason="synthetic data contract import",
                    operation_key=str(uuid4())))
                await store.db.execute(insert(src).values(id=uuid4(), tenant_id=TEN, case_id=cid,
                    assessment_id=sid, artifact_id=artifact))
                for aid in aids:
                    await store.db.execute(insert(cover).values(id=uuid4(), tenant_id=TEN, case_id=cid,
                        assessment_id=sid, alert_id=aid, coverage_note="合成导入范围"))
                await store.db.execute(update(c).where(c.c.id == cid).values(current_assessment_id=sid))
        output.append({"case_id": cid, "alert_ids": aids, "material_ids": mids, "entries": entries,
            "label": label, "verdict": verdict, "classification": classification})
    return output


async def validate(service, fixtures):
    checks = []
    async def check_error(call, code):
        try:
            await call
        except StoreError as exc:
            assert exc.code == code, (exc.code, code)
        else:
            raise AssertionError("expected " + code)
    async def publish(f, entries=None, state="available", alerts=None, **overrides):
        row = (await service.read_case(TEN, f["case_id"]))["case"]
        index = {"schema_version": "socai2.case-evidence.v1", "scope_revision": row.scope_revision,
            "alert_ids": list(map(str, alerts if alerts is not None else f["alert_ids"])),
            "supersedes_artifact_id": str(row.current_evidence_artifact_id) if row.current_evidence_artifact_id else None,
            "availability_state": state, "limitations": ["合成范围限制"] if state != "available" else [],
            "entries": entries if entries is not None else f["entries"]}
        body = {"operation_key": uuid4(), "expected_row_version": row.row_version,
            "expected_current_artifact_id": row.current_evidence_artifact_id, "index": index, **overrides}
        request = EvidencePublish.model_validate(body)
        return await service.publish_evidence(TEN, f["case_id"], request, actor=ACTOR)
    for f in fixtures:
        row = (await service.read_case(TEN, f["case_id"]))["case"]
        req = CaseDataUpdate(operation_key=uuid4(), expected_row_version=row.row_version,
            classification=f["classification"], due_at=datetime(2026,11,12,9,tzinfo=UTC),
            source="import", source_note="synthetic data contract fixture")
        receipt = await service.update_page_data(TEN, f["case_id"], req, actor=ACTOR)
        assert await service.update_page_data(TEN, f["case_id"], req, actor=ACTOR) == receipt
        await check_error(service.update_page_data(TEN, f["case_id"], req.model_copy(update={"operation_key":uuid4()}), actor=ACTOR), "case_row_version_conflict")
        if f["verdict"]:
            await publish(f)
    first = fixtures[0]
    row = (await service.read_case(TEN, first["case_id"]))["case"]
    cleared = await service.update_page_data(TEN, first["case_id"], CaseDataUpdate(operation_key=uuid4(),
        expected_row_version=row.row_version, classification=None, due_at=None, source="manual", source_note="验证显式清空"), actor=ACTOR)
    data = await service.read_page_data(TEN, first["case_id"])
    assert data.classification is None and data.due_at is None
    await service.update_page_data(TEN, first["case_id"], CaseDataUpdate(operation_key=uuid4(),
        expected_row_version=cleared.row_version, classification="informational", due_at=datetime(2026,11,12,9,tzinfo=UTC),
        source="import", source_note="恢复合成样例显示值"), actor=ACTOR)
    checks.append("DA01 management roundtrip, explicit clear, idempotency, stale version")
    evil = fixtures[1]
    old = (await service.read_case(TEN, evil["case_id"]))["case"]
    await publish(evil)
    await check_error(publish(evil, expected_row_version=old.row_version), "case_row_version_conflict")
    await check_error(publish(evil, expected_current_artifact_id=old.current_evidence_artifact_id), "case_evidence_version_conflict")
    async with service.transaction(TEN, readonly=True) as store:
        assert await store.one(select(m.Artifacts.__table__).where(m.Artifacts.id == old.current_evidence_artifact_id))
    bad = json.loads(json.dumps(evil["entries"]))
    bad[0]["source_refs"][0]["id"] = str(first["material_ids"][0])
    await check_error(publish(evil, bad), "evidence_source_scope_or_role_invalid")
    bad[0]["source_refs"][0]["id"] = str(uuid4())
    await check_error(publish(evil, bad), "evidence_source_not_found")
    try:
        await publish(evil, [evil["entries"][0],evil["entries"][0]])
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate ID accepted")
    checks.append("DA03 immutable versions, stale pointer, wrong/missing sources, duplicate IDs")
    assert (await service.read_page_data(TEN, evil["case_id"])).evidence.threat_count == 1
    assert (await service.read_page_data(TEN, first["case_id"])).evidence.threat_count == 0
    missing = await service.read_page_data(TEN, fixtures[3]["case_id"])
    assert missing.determination is None and missing.evidence.evidence_count is None
    unknown = fixtures[2]
    await publish(unknown, [])
    assert (await service.read_page_data(TEN, unknown["case_id"])).evidence.evidence_count == 0
    await publish(unknown, [dict(e, state="withdrawn") for e in unknown["entries"]])
    assert (await service.read_page_data(TEN, unknown["case_id"])).evidence.evidence_count == 0
    await publish(unknown)
    # Partial multi-member entry must be excluded as a whole, never narrowed.
    multi = [dict(unknown["entries"][0], alert_ids=list(map(str, unknown["alert_ids"])),
        source_refs=[r for e in unknown["entries"] for r in e["source_refs"]], threat=None)]
    await publish(unknown, multi)
    from app.socai2.case_data import Lookup, evidence_view, object_map
    async with service.transaction(TEN, readonly=True) as store:
        cas = dict(await store.case(unknown["case_id"], lock=False))
        lookup = Lookup(store); art = await lookup("artifact", cas["current_evidence_artifact_id"])
        idx = EvidenceIndex.model_validate(art["content_json"])
        view = await evidence_view(cas, {unknown["alert_ids"][0]}, art, lookup, await object_map(store, idx))
        assert view.state == "partial" and view.evidence_count == 0 and len(view.excluded_evidence_ids) == 1
    await publish(unknown)
    checks.append("DA04 same-threat dedup, clean/unknown, empty/withdrawn, missing, partial multi-member")
    queue = await service.read_cases(TEN, CaseQueueQuery(q="数据合同样例", limit=50))
    for f in fixtures:
        detail = await service.read_case(TEN, f["case_id"])
        item = next(i for i in queue.items if i.case.id == f["case_id"])
        assert item.page_data == detail["page_data"]
        assert detail["case"].scope_revision == 1 and not detail["baseline_records"]
        assert detail["case"].handling_status == "new"
    checks.append("DA02/DA05 queue and detail same saved assessment/data; no Run/state side effects")
    return checks


async def snapshot(values, fixtures, root, batch):
    conn = await pg_connect(values, role=API_ROLE, password_key="API_DB_PASSWORD")
    tables = {t: {} for t in TABLES}
    try:
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", TENANT)
            for f in fixtures:
                for table in TABLES:
                    rows = json.loads(await conn.fetchval(query_for(table), TEN, f["alert_ids"], None, f["case_id"], []))
                    tables[table].update({r["id"]: r for r in rows})
    finally:
        await conn.close()
    tables = {t: list(rows.values()) for t, rows in tables.items()}
    page = await export_page_data(tables)
    payloads = {"database.json": tables, "case-page-data.json": page}
    sources = []
    for name, payload in payloads.items():
        raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)+"\n").encode()
        (root/name).write_bytes(raw)
        import hashlib
        sources.append({"file":name, "sha256":hashlib.sha256(raw).hexdigest(),
            "role":"database" if name=="database.json" else "case_page_data"})
    manifest = {"schema_version":"socai2.page-export.v1", "batch_id":batch,
        "source_environment":"local-data-contract", "input_kind":"synthetic",
        "exported_at":datetime.now(UTC).isoformat(), "source_sha256":sources[0]["sha256"],
        "sources":sources,"database_snapshot":"single_readonly_repeatable_read", "model_calls":0,
        "sample_kind":"persisted_data_contract_not_model_execution", "table_counts":{k:len(v) for k,v in tables.items()}}
    (root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return page, manifest


async def main(apply, readback=None):
    values=read_private()
    migration=await migrate(values) if apply else {"migration":"already applied"}
    engine=create_async_engine(URL.create("postgresql+asyncpg", username=API_ROLE,
        password=values["API_DB_PASSWORD"], host="127.0.0.1", port=15432, database=DATABASE), connect_args={"ssl":False})
    batch="page-data-"+datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')
    root=ROOT/'.local/local-investigation'/batch
    if readback:
        previous=Path(readback).resolve()
        assert previous.parent == (ROOT/'.local/local-investigation').resolve()
        batch=previous.name
        root=previous/('readback-'+datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ'))
    root.mkdir(parents=True,exist_ok=False)
    try:
        service=CaseService(async_sessionmaker(engine,expire_on_commit=False))
        if readback:
            fixtures=json.loads((previous/'fixture-ids.json').read_text())
            for f in fixtures:
                f['case_id']=UUID(f['case_id'])
                for key in ('alert_ids','material_ids'):f[key]=list(map(UUID,f[key]))
            checks=['Read-only normalization recheck of preserved fixtures; no repeated writes or models']
        else:
            fixtures=await seed(service,batch)
            (root/'fixture-ids.json').write_text(json.dumps([{k:v for k,v in f.items() if k!='entries'} for f in fixtures],default=str,ensure_ascii=False,indent=2)+'\n')
            checks=await validate(service,fixtures)
            (root/'storage-checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
        page, _manifest=await snapshot(values,fixtures,root,batch)
        for p in page:
            direct=await service.read_page_data(TEN,UUID(p['case_id']))
            assert direct.model_dump(mode='json') == p['page_data'], 'export/reader mismatch'
        # Existing Cases must remain readable with nullable additive fields;
        # their adopted model/system judgments must agree across both readers.
        queue=await service.read_cases(TEN,CaseQueueQuery(limit=50))
        fixture_ids={f['case_id'] for f in fixtures}
        origins={}
        for item in queue.items:
            detail=await service.read_case(TEN,item.case.id)
            assert detail['page_data']==item.page_data
            if item.case.id not in fixture_ids:
                assert item.case.classification is None and item.case.due_at is None
                assert item.case.current_evidence_artifact_id is None
            if item.page_data.assessment:
                origin=item.page_data.assessment.origin
                origins[origin]=origins.get(origin,0)+1
                assert item.page_data.determination==detail['current_assessment']['value']['conclusion']
        compatibility={"cases_checked": len(queue.items),"old_cases_checked": len(queue.items)-len(fixtures),
            "assessment_origins": origins,"queue_detail_equal": True,"old_additive_fields_null": True}
        (root/'compatibility.json').write_text(json.dumps(compatibility,ensure_ascii=False,indent=2)+'\n')
        receipt={"status":"passed", "migration":migration,"checks":checks,"model_calls":0,
            "compatibility":compatibility,
            "batch":batch,"case_ids":[str(f['case_id']) for f in fixtures],"export_directory":str(root),
            "counts":[{"case_id":p['case_id'],"state":p['page_data']['evidence']['state'],
                "evidence":p['page_data']['evidence']['evidence_count'],"threats":p['page_data']['evidence']['threat_count']} for p in page]}
        (root/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(receipt,ensure_ascii=False,indent=2))
    finally:
        await engine.dispose()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply-migration',action='store_true')
    parser.add_argument('--readback',help='Read-only re-export of a preserved fixture batch')
    args=parser.parse_args()
    try:
        asyncio.run(main(args.apply_migration,args.readback))
    except Exception as exc:  # noqa: BLE001 -- redact CLI failures before emitting any details
        print(json.dumps({"status":"failed","type":type(exc).__name__,"reason":safe_error(exc,read_private())},ensure_ascii=False))
        raise SystemExit(1)
