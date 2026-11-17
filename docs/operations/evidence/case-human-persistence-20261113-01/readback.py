"""Complete the remaining read checks on pg-02; no write or model dispatch."""
import argparse
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
parser = argparse.ArgumentParser()
parser.add_argument("--database-config", type=Path, required=True)
parser.add_argument("--environment-file", type=Path, required=True)
parser.add_argument("--snapshot", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
cfg = json.loads(args.database_config.read_text())
plan = json.loads(Path(__file__).with_name("config.json").read_text())
assert cfg["host"] == plan["database_host"] and cfg["processing_database"] == plan["database"]
os.environ.update(json.loads(args.environment_file.read_text()))
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / plan["policy"])
sys.path[:0] = [str(ROOT / p) for p in (".", "services/api", "services/api/tests", "docs/operations")]

from app.api.v1.endpoints import socai2_cases as api
from app.socai2.baseline_service import BaselineService
from app.socai2.case_service import CaseService
from app.socai2.human_task_contracts import TaskRevisionView
from capture_processing_case import check_credentials
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from test_socai2_case_followup_pg import T, human_readback

args.output.mkdir(exist_ok=False)
data = json.loads(args.snapshot.read_text())
artifacts = {r["id"]: r for r in data["artifacts"]}
run = next(r for r in data["runs"] if r.get("comparison_result_id"))
cid, rid = UUID(run["case_id"]), UUID(run["id"])
prior = next(r for r in data["results"] if r["id"] == run["comparison_result_id"])
prior_scope = artifacts[prior["input_artifact_id"]]["content_json"]["scope"]
base = next(a["content_json"] for a in data["artifacts"]
            if a["run_id"] == str(rid) and "input_ledger" in (a["content_json"] or {}))
human_ref = next(r["ref"] for r in base["input_ledger"]["records"] if r.get("context_kind") == "human_feedback")
revisions = [TaskRevisionView.model_validate({k: row[k] for k in TaskRevisionView.model_fields})
             for row in sorted(data["task_revisions"], key=lambda r: r["revision"])]
result = next(r for r in data["results"] if r["source_run_id"] == str(rid))


def save(name, value):
    body = json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n"
    check_credentials(body.encode())
    with (args.output / name).open("x") as file:
        file.write(body)


async def main():
    url = URL.create("postgresql+psycopg", username=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), host=cfg["host"],
        port=cfg["port"], database=cfg["processing_database"])
    engine = create_async_engine(url, connect_args={"sslmode": plan["database_sslmode"],
        "options": "-c role=" + cfg["processor"] + " -c default_transaction_read_only=on"})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.connect() as connection:
            assert (await connection.execute(text("select current_database(),current_user,current_setting('transaction_read_only')"))).one() == (
                cfg["processing_database"], cfg["processor"], "on")
        evidence = await human_readback(BaselineService(sessions), cid, rid, prior["id"], prior_scope, human_ref, revisions)
        save("H-reference-readback.json", evidence)
        app = FastAPI()
        app.include_router(api.router)
        app.dependency_overrides[api.get_service] = lambda: CaseService(sessions)
        app.dependency_overrides[api.ReadUser.__metadata__[0].dependency] = lambda: SimpleNamespace(tenant_id=T)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
            response = await client.get(f"/socai2/cases/{cid}/results/{result['id']}")
            assert response.status_code == 200
            saved = response.json()["result"]
            assert all(saved[k] == result[k] for k in (
                "id", "source_run_id", "conclusion", "conclusion_state", "validation_state", "delivery_state",
                "recommendations", "change_kind", "change_summary"))
            save("result-get.json", response.json())
            response = await client.get(f"/socai2/cases/{cid}")
            assert response.status_code == 200
            current = response.json()["current_assessment"]
            assert current["value"]["conclusion"] == result["conclusion"]
            assert current["value"]["validity"] == "accepted" and current["covers_current_members"]
            save("case-get.json", response.json())
        save("validation.json", {"status": "passed", "database": cfg["processing_database"],
            "case_id": cid, "run_id": rid, "result_id": result["id"], "real_model_calls": 0,
            "database_writes": 0, "new_runs": 0, "original_failure_retained": True,
            "checks": ["full_delivery_H_and_comparison_refs", "H_revision_1_and_2_GETs", "result_GET", "current_assessment_GET"],
            "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (
                args.snapshot.resolve(), Path(__file__), ROOT / "services/api/tests/test_socai2_case_followup_pg.py",
                ROOT / "services/api/tests/test_socai2_case_boundary_pg.py")}})
        print("Remaining H references and four read-only ASGI GETs passed.")
    finally:
        await engine.dispose()


asyncio.run(main())
