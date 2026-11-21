"""Explicit standalone lake delivery worker; never starts Kafka or analysis."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from urllib.parse import unquote, urlparse

import asyncpg
import redis.asyncio as redis
import structlog
from clickhouse_driver import Client

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.operational_logging import log_exception
from app.services.confidence import ConfidenceScorer
from app.services.correlator import Correlator
from app.services.deduplicator import Deduplicator
from app.services.fusion_engine import FusionEngine
from app.services.lake_alert_delivery import (
    DeliveryPolicy,
    DeliveryStore,
    LakeAlertDelivery,
    LakeDeliverySource,
)
from app.services.lake_alert_receiver import LakeAlertReceiver, ReceivePolicy
from app.services.lake_alert_selection import SelectionPolicy
from app.services.socai2_sink import Socai2AlertSink


def connections(policy, selection, receive):
    body = json.loads(policy.file("connection_file").read_text())
    if set(body) != {"postgres_dsn", "postgres_pool_size", "postgres_connect_timeout_seconds", "clickhouse", "redis"}:
        raise ValueError("explicit_delivery_connections_required")
    pg = urlparse(body["postgres_dsn"])
    if (pg.scheme not in {"postgres", "postgresql"} or not pg.hostname or pg.port is None
            or unquote(pg.path.removeprefix("/")) != receive.body["postgres_database"]
            or type(body["postgres_pool_size"]) is not int or body["postgres_pool_size"] < 2
            or type(body["postgres_connect_timeout_seconds"]) is not int or body["postgres_connect_timeout_seconds"] <= 0):
        raise ValueError("delivery_postgres_binding_invalid")
    ch = body["clickhouse"]
    if (set(ch) != {"host", "port", "database", "user", "password", "secure", "verify"}
            or ch["database"] != selection.body["database"] or not ch["host"] or not ch["user"]
            or type(ch["port"]) is not int or not 0 < ch["port"] < 65536
            or type(ch["secure"]) is not bool or type(ch["verify"]) is not bool):
        raise ValueError("delivery_lake_binding_invalid")
    cache = body["redis"]
    if (set(cache) != {"url", "connect_timeout_seconds", "socket_timeout_seconds"}
            or any(type(cache[k]) is not int or cache[k] <= 0 for k in ("connect_timeout_seconds", "socket_timeout_seconds"))):
        raise ValueError("delivery_cache_binding_invalid")
    uri = urlparse(cache["url"])
    if uri.scheme not in {"redis", "rediss"} or not uri.hostname or uri.port is None or not uri.path:
        raise ValueError("delivery_cache_binding_invalid")
    return body


@asynccontextmanager
async def open_delivery(path):
    configure_logging()
    policy = DeliveryPolicy.load(path)
    if not policy.body["enabled"]:
        raise ValueError("delivery_worker_disabled")
    selection = SelectionPolicy.load(policy.file("selection_profile_file"))
    receive = ReceivePolicy.load(policy.file("receive_profile_file"))
    config = connections(policy, selection, receive)
    runtime = policy.body["runtime"]
    # This entry point is its own process. The existing Fusion components take
    # these settings at construction; no default environment/DB is selected.
    for name in ("dedup_window_seconds", "correlation_window_seconds", "max_alerts_per_incident"):
        setattr(settings, name, runtime[name])
    if not settings.operational_logging_profile_file:
        structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, runtime["log_level"])))
    limits = selection.body["read_limits"]
    client = Client(**config["clickhouse"], disable_reconnect=True,
                    connect_timeout=limits["connect_timeout_seconds"], send_receive_timeout=limits["send_receive_timeout_seconds"])
    cache = redis.from_url(config["redis"]["url"], decode_responses=False,
        socket_connect_timeout=config["redis"]["connect_timeout_seconds"], socket_timeout=config["redis"]["socket_timeout_seconds"])
    sink = Socai2AlertSink(config["postgres_dsn"], pool_size=config["postgres_pool_size"],
        analysis_policy=receive.body["initial_analysis"], material_max_bytes=receive.body["limits"]["material_bytes"],
        snapshot_max_bytes=receive.body["limits"]["snapshot_bytes"])
    try:
        sink._pool = await asyncpg.create_pool(config["postgres_dsn"], min_size=1, max_size=config["postgres_pool_size"],
                                             timeout=config["postgres_connect_timeout_seconds"])
        await cache.ping()
        engine = FusionEngine(Deduplicator(cache), Correlator(cache), confidence_scorer=ConfidenceScorer(enabled=runtime["confidence_enabled"]))
        receiver = LakeAlertReceiver(selection, receive, sink, engine)
        store = DeliveryStore(sink._pool, selection, receive, policy)
        yield LakeAlertDelivery(LakeDeliverySource(client, selection), receiver, store, policy)
    finally:
        await sink.stop()
        await cache.aclose()
        client.disconnect()


async def run(path, *, once=False, stage_only=False):
    async with open_delivery(path) as delivery:
        while True:
            result = await delivery.cycle(deliver=not stage_only)
            # Counts, IDs and body values never appear in this status output.
            print(json.dumps({"state": result.state, "reason": result.reason}), flush=True)
            if result.state in {"blocked", "unknown"}:
                return 2
            if once or stage_only:
                return 0 if result.state != "busy" else 3
            await asyncio.sleep(delivery.policy.body["poll_interval_seconds"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--stage-only", action="store_true")
    args = parser.parse_args()
    try:
        return asyncio.run(run(args.profile, once=args.once, stage_only=args.stage_only))
    except Exception:  # noqa: BLE001 -- no source records or credentials in error text.
        log_exception(logging.getLogger(__name__), "lake_delivery_runtime_failed", extra={
            "operation": "lake_delivery", "stage": "runtime", "error_code": "delivery_runtime_unconfirmed"})
        print('{"state":"unknown","reason":"delivery_runtime_unconfirmed"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
