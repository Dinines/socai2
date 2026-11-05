"""Local real Kafka/Fusion/PG/lake assembly without legacy background branches."""
import asyncio
from contextlib import asynccontextmanager, suppress
from urllib.parse import urlsplit

import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logging import configure_logging, logger
from app.services.confidence import ConfidenceScorer
from app.services.correlator import Correlator
from app.services.deduplicator import Deduplicator
from app.services.entity_risk import EntityRiskEngine
from app.services.fusion_engine import FusionEngine
from app.services.lake_writer import LakeWriter
from app.services.socai2_sink import Socai2AlertSink
from app.workers.consumer import FusionWorker
from config import DATABASE, FUSION_ROLE, LAKE, PORTS, TOPIC
from fastapi import FastAPI
from fastapi.responses import JSONResponse


def verify_route():
    url = urlsplit(settings.database_url)
    assert (url.hostname, url.port, url.path, url.username) == ("127.0.0.1", PORTS["postgres"], "/" + DATABASE, FUSION_ROLE)
    assert settings.alert_store_schema == "socai2" and settings.alert_sink_enabled
    assert settings.clickhouse_host == "127.0.0.1" and settings.clickhouse_port == PORTS["clickhouse_native"]
    assert settings.clickhouse_database == LAKE and settings.lake_writer_enabled and settings.lake_batch_size == 1
    assert settings.redis_url == "redis://127.0.0.1:16379/0"
    assert settings.kafka_bootstrap_servers == "127.0.0.1:19092"
    assert settings.kafka_consumer_group == TOPIC + ".fusion"
    assert settings.kafka_topic_alerts_raw == TOPIC + ".alerts.raw"
    assert settings.kafka_topic_raw_events == TOPIC + ".raw_events"
    assert settings.kafka_topic_alerts_fused == TOPIC + ".alerts.fused"
    assert not any((settings.event_promotion_enabled, settings.detection_engine_enabled,
                    settings.windowed_detection_enabled, settings.ueba_fusion_enabled, settings.attack_chain_grouping_enabled))


def task_ended(task):
    if not task.cancelled():
        exc = task.exception()
        logger.error("local_fusion_consumer_stopped", error_type=type(exc).__name__ if exc else "returned")


@asynccontextmanager
async def lifespan(app):
    verify_route()
    configure_logging()
    redis = aioredis.from_url(settings.redis_url, decode_responses=False)
    await redis.ping()
    engine = FusionEngine(Deduplicator(redis), Correlator(redis), entity_risk=EntityRiskEngine(redis),
                          confidence_scorer=ConfidenceScorer(enabled=settings.confidence_enabled))
    sink = Socai2AlertSink(settings.database_url)
    lake = LakeWriter(host=settings.clickhouse_host, port=settings.clickhouse_port,
        database=settings.clickhouse_database, user=settings.clickhouse_user, password=settings.clickhouse_password,
        batch_size=settings.lake_batch_size, batch_max_age_seconds=settings.lake_batch_max_age_seconds)
    worker = FusionWorker(engine, sink=sink, lake=lake)
    task = asyncio.create_task(worker.start())
    task.add_done_callback(task_ended)
    app.state.worker, app.state.worker_task = worker, task
    try:
        # Never report ready before both partitions are assigned and the real sink opened.
        async with asyncio.timeout(45):
            while not (worker.attached and worker._consumer and len(worker._consumer.assignment()) == 2):
                if task.done():
                    await task
                    raise RuntimeError("local_fusion_consumer_ended_before_ready")
                await asyncio.sleep(0.1)
        assert sink._pool is not None, "local_fusion_database_unavailable"
        async with sink._pool.acquire() as conn:
            assert await conn.fetchval("SELECT current_database()") == DATABASE
        assert lake._client is not None and not lake._disabled, "local_fusion_lake_unavailable"
        await asyncio.to_thread(lake._client.execute, "SELECT 1")
        yield
    finally:
        await worker.stop()
        task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await task
        await redis.aclose()


app = FastAPI(title="Local socai2 Fusion", lifespan=lifespan)


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "socai2-local-fusion"}


@app.get("/readyz")
async def readyz():
    worker, task = getattr(app.state, "worker", None), getattr(app.state, "worker_task", None)
    ready = bool(worker and worker.attached and task and not task.done())
    return JSONResponse({"ready": ready, "service": "socai2-local-fusion"}, status_code=200 if ready else 503)


@app.get("/metrics")
async def metrics():
    return app.state.worker.get_metrics()
