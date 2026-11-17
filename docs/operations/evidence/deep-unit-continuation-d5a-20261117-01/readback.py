"""Read the already finished D5a Run; no admission, dispatch, or model calls."""
import argparse
import asyncio
import importlib.util
import json
from pathlib import Path
from uuid import UUID

spec = importlib.util.spec_from_file_location("driver", Path(__file__).with_name("validate.py"))
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


async def main(config, source, output):
    from app.socai2.case_service import CaseService
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    output.mkdir(exist_ok=False)
    prior = json.loads((source / "result.json").read_text())
    cfg = json.loads(Path(config["database_profile"]).read_text())
    assert cfg["host"] == "127.0.0.1"
    url = URL.create("postgresql+psycopg", username=cfg["admin"], password=Path(cfg["password_file"]).read_text().strip(),
        host=cfg["host"], port=cfg["port"], database=cfg["processing_database"])
    engine = create_async_engine(url, hide_parameters=True,
        connect_args={"sslmode": config["sslmode"], "options": "-c role=" + cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cases = CaseService(sessions)
    tenant, actor = UUID(prior["tenant_id"]), UUID(prior["actor_id"])
    try:
        saved, _ = await driver.d4c_helper.snapshot(cases, tenant)
        assert saved == json.loads((source / "snapshot.json").read_text())
        entry = {"subject_type": "case", "subject_id": prior["case_id"], "task_id": prior["task_id"],
                 "run_id": prior["run_id"], "status": prior["task_status"]}
        result = await driver.d4c_helper.http_readback(sessions, cases, tenant, actor, [entry], saved, output, config)
        calls = json.loads((source / "calls.json").read_text())
        deep_call = next(c for c in calls if c.get("injection"))
        summary = next(a["content_json"] for a in saved["artifacts"]
                       if (a["content_json"] or {}).get("type") == "deep_summary")
        final = saved["results"][0]
        c6 = json.loads(calls[-1]["response"]["choices"][0]["message"]["content"])
        assert summary["answer"] is None and summary["state"] == "failed"
        assert saved["runs"][0]["state"] == "completed" and final["conclusion"] == c6["conclusion"]["text"]
        assert saved["analysis_attempts"][0]["local_state"] == "ended"
        result.update(status="passed_for_actual_received_prefix_only", new_model_calls=0, new_business_runs=0,
            real_source_calls=len(calls), received_prefix=deep_call["injection"]["received_content"],
            actual_scope="Deep no usable answer -> C6 model conclusion persisted and read back",
            unverified=["complete retained Deep answer -> C6 in real PG run", "independent PG/HTTP review", "D5b/D5c", "21 deployment/UI"])
        driver.save(output / "result.json", result)
        print(json.dumps({k:result[k] for k in ("status", "http_gets", "new_model_calls", "actual_scope")}))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    driver.environment(config)
    asyncio.run(main(config, args.source, args.output))
