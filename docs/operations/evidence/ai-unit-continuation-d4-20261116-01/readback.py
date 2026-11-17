"""Read already saved D4a runs only: no submissions, replay or model generation."""
import argparse
import asyncio
import importlib.util
import json
import traceback
from pathlib import Path
from uuid import UUID

spec = importlib.util.spec_from_file_location("d4_driver", Path(__file__).with_name("validate.py"))
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


async def main(config, batch, out):
    from app.socai2.analysis_dispatch_redis import AnalysisQueues
    from app.socai2.stage_delivery import VERSION, validate_sources
    from app.socai2.stage_results import StageResultService
    from redis.asyncio import Redis
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    out.mkdir(exist_ok=False)
    original = json.loads((batch / "result.json").read_text())
    tenant, actor = UUID(original["tenant_id"]), UUID(original["actor_id"])
    cfg = json.loads(Path(config["database_profile"]).read_text())
    url = URL.create("postgresql+psycopg", username=cfg["admin"], password=Path(cfg["password_file"]).read_text().strip(),
                    host=cfg["host"], port=cfg["port"], database=cfg["processing_database"])
    engine = create_async_engine(url, hide_parameters=True, connect_args={"sslmode":config["sslmode"], "options":"-c role="+cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = StageResultService(sessions)
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())
    result = {"state":"running", "source_batch":str(batch), "model_calls":0, "business_writes":0}
    try:
        saved, _ = await driver.snapshot(service, tenant)
        assert saved == json.loads((batch / "database.json").read_text())
        originals = {a['id']:a['content_json'] for a in saved['artifacts']}
        receipts = [a for a in saved['artifacts'] if a['schema_version'] == VERSION]
        assert len(receipts)==5
        for row in receipts:
            validate_sources(row['content_json'], originals)
        driver.save(out / 'database.json',saved)
        records=json.loads((batch/'tasks.json').read_text())
        result.update(await driver.http_readback(sessions, service, tenant, actor, records, saved, out))
        queues = AnalysisQueues(redis, config['dispatch']['namespace'], tenant)
        assert await redis.scard(queues.key('running')) == 0
        result.update(state='passed',slots_used=0,strict_receipts=len(receipts),steps=len(saved['run_steps']),
            artifacts=len(saved['artifacts']),runs=len(saved['runs']),tasks=len(saved['analysis_tasks']))
    except Exception as exc:
        result.update(state='failed',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
        raise
    finally:
        driver.save(out/'result.json',result)
        await redis.aclose()
        await engine.dispose()


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--batch',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(); c=json.loads(args.config.read_text());driver.environment(c)
    asyncio.run(main(c,args.batch,args.output))
