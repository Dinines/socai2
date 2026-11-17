"""One direct PG/Redis check reusing the existing controlled dispatcher executor."""
import argparse
import asyncio
import json
import sys
import traceback
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "services/api"), str(ROOT / "services/api/tests")]
import httpx
from redis.asyncio import Redis
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import create_async_engine
from test_socai2_analysis_dispatch_pg import Harness


async def run(args):
    config = json.loads(args.config.read_text())
    cfg = json.loads(Path(config["database_profile"]).read_text())
    assert cfg["processing_database"] == "v12_upgrade_dev"
    url = URL.create("postgresql+psycopg", username=cfg["admin"], password=Path(cfg["password_file"]).read_text().strip(),
        host=cfg["host"], port=cfg["port"], database=cfg["processing_database"])
    admin = create_async_engine(url, hide_parameters=True, connect_args={"sslmode": config["sslmode"]})
    engine = create_async_engine(url, hide_parameters=True,
        connect_args={"sslmode": config["sslmode"], "options": "-c role=" + cfg["processor"]})
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())
    if args.output.exists():
        raise ValueError("use a new output batch")
    result = {"state": "running", "real_model_calls": 0, "mode": "controlled_executor_and_clock_real_PG_Redis"}
    try:
        h = await Harness().initialize(engine, admin, redis,
            {**config["dispatch"], "control_timeout_seconds": config["check_timeout_seconds"]}, 1)
        result["tenant_id"] = h.tenant
        ca, cb = await h.subject(), await h.subject()
        h.executor.behavior[ca] = httpx.ConnectTimeout("synthetic unsent request")
        t1 = await h.submit(ca)
        await h.dispatcher.tick()
        await h.finish_active()
        waiting = await h.repository.task(t1)
        result["first_waiting"] = await h.read(t1)
        assert waiting["next_retry_at"] == h.service.clock + timedelta(seconds=60)
        t2, tb = await h.submit(ca), await h.submit(cb)
        await h.dispatcher.tick()
        await h.finish_active()
        assert (await h.repository.task(t2))["state"] == "accepted"
        assert (await h.repository.task(t2))["merged_into_task_id"] is None
        assert (await h.read(tb))["status"] == "completed"
        h.service.clock += timedelta(seconds=59)
        await h.dispatcher.tick()
        assert not h.dispatcher.active
        h.service.clock += timedelta(seconds=1)
        await h.dispatcher.tick()
        await h.finish_active()
        await h.finish_active()
        done, skipped = await h.read(t1), await h.read(t2)
        assert done["reason_code"] == "retry_exhausted" and len(done["attempts"]) == 2
        assert skipped["reason_code"] == "automatic_attempts_stopped" and not skipped["attempts"]
        assert len(h.executor.calls) == 3
        result.update(state="passed", first=done, independent=skipped, other=await h.read(tb), calls=h.executor.calls)
    except Exception:
        result.update(state="failed", traceback=traceback.format_exc())
        raise
    finally:
        args.output.write_text(json.dumps(result, default=str, indent=2) + "\n")
        await redis.aclose()
        await engine.dispose()
        await admin.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args()))
