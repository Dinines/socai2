"""One new batch, reusing existing HTTP/Case drivers; no repeated model sampling."""
import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.testdata.case_knowledge.run import application, export
from tools.testdata.case_scope_recovery.real_model import initialize, plan_for, prepare
from tools.testdata.historical_knowledge.run import run, seed_history
from tools.testdata.incident_integration.fixtures import identity
from tools.testdata.incident_integration.run import connect, read, save, sha


async def knowledge(config, folder):
    from app.db import database
    from app.models import socai2 as m
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import insert, text, update

    plan = plan_for(config, folder)
    save(folder / "knowledge-intent.json", {"attempts": 1})
    aid = await seed_history(config, plan)
    receipts = []
    try:
        async with AsyncClient(transport=ASGITransport(app=application(config)), base_url=config["http_base_url"],
                               timeout=config["http_timeout_seconds"]) as client:
            async def request(label, method, path, body=None):
                response = await client.request(method, path, json=body)
                data = response.json()
                receipt = {"label": label, "method": method, "path": path, "request": body,
                           "status": response.status_code, "body": data}
                receipts.append(receipt)
                save(folder / "knowledge-http" / f"{len(receipts):02d}-{label}.json", receipt)
                print(label, response.status_code, flush=True)
                assert response.is_success, label
                return data

            old = await request("import", "POST", "/api/v1/kb/alert-experiences", {"alert_ids": [aid]})
            old_id = old["cards"][0]["document_id"]
            assert old == await request("duplicate", "POST", "/api/v1/kb/alert-experiences", {"alert_ids": [aid]})
            await request("index-old", "POST", "/api/v1/kb/index", {"document_ids": [old_id]})
            old_card = await request("old-card", "GET", "/api/v1/kb/alert-experiences/" + old_id)
            engine = await connect(config)
            try:
                async with engine.begin() as conn:
                    await conn.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {"tenant": config["tenant_id"]})
                    fid = UUID(identity(config["batch"], "feedback-revision-2"))
                    feedback = read(ROOT / config["history_fixture"])["feedback"]
                    feedback["rationale"] += " 第二版演练反馈：核查清单补记父进程、输出与用途，仍未提供这些材料。"
                    await conn.execute(insert(m.AlertAssessments).values(id=fid, tenant_id=UUID(config["tenant_id"]),
                        alert_id=UUID(aid), input_material_id=UUID(old_card["card"]["source"]["material_id"]),
                        kind="human_feedback", **feedback, actor={"type": "service", "service_name": "knowledge-selection-fixture",
                        "service_version": "fixture.v2", "user_id": None, "name_snapshot": None},
                        producer="synthetic_fixture_not_actual_human", assessed_at=datetime.now(UTC),
                        operation_key=identity(config["batch"], "feedback-revision-2")))
                    await conn.execute(update(m.Alerts).where(m.Alerts.id == UUID(aid)).values(latest_feedback_id=fid))
            finally:
                await engine.dispose()
            current = await request("revised-import", "POST", "/api/v1/kb/alert-experiences", {"alert_ids": [aid]})
            current_id = current["cards"][0]["document_id"]
            assert current_id != old_id
            assert old_card == await request("old-preserved", "GET", "/api/v1/kb/alert-experiences/" + old_id)
            ids = [current_id]
            for i, doc in enumerate(read(ROOT / config["corpus"])):
                stored = await request(f"method-{i}", "POST", "/api/v1/kb/ingest", doc["request"])
                ids.extend(r["id"] for r in stored)
            await request("index-current", "POST", "/api/v1/kb/index", {"document_ids": ids})
            revised = await request("current-card", "GET", "/api/v1/kb/alert-experiences/" + current_id)
            assert revised["card"]["feedback"]["rationale"] == feedback["rationale"]
            save(folder / "knowledge-http.json", receipts)
            save(folder / "knowledge-ready.json", {"historical_alert_id": aid, "document_ids": ids,
                "superseded_document_id": old_id, "same_content_same_id": True, "old_card_unchanged": True})
    finally:
        await database.engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "knowledge", "run", "export"))
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config, folder = initialize(args.config.resolve())
    if args.phase == "prepare":
        prepare(config, args.config.resolve(), folder)
        paths = [Path(__file__), ROOT / config["history_fixture"], ROOT / config["knowledge_profile"], ROOT / config["corpus"]]
        save(folder / "knowledge-source-sha256.json", {str(p.relative_to(ROOT)): sha(p) for p in paths})
    else:
        assert all(sha(ROOT / p) == h for p, h in read(folder / "knowledge-source-sha256.json").items())
        result = asyncio.run({"knowledge": knowledge, "run": run, "export": export}[args.phase](config, folder))
        if args.phase == "run" and not result:
            sys.exit(1)
