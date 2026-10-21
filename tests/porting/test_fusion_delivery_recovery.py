"""C01 direct production seams, with explicit in-memory PG/Kafka/Redis doubles.

These do not claim a real broker, a real database failure, or model quality.
The transport and storage confirmations below are the inputs under test.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from aiokafka.structs import TopicPartition

from app.models.alert import FusedAlert, FusionDecision, RawAlert
from app.services import delivery_recovery as snapshots
from app.services.alert_sink import AlertSink, PersistOutcome, PersistResult, _insert_args
from app.services.delivery_recovery import DeliveryHold, DeliveryRecovery, SnapshotLookup, make_snapshot, restore_snapshot
from app.services.dlq import DeadLetter, InMemoryDLQ, KafkaDLQ, LoggingDLQ, safe_record
from app.services.dlq_sink import PostgresDLQ
from app.workers.consumer import FusionWorker


def raw(version="source-v1"):
    alert = RawAlert(
        tenant_id=UUID(int=101), source="c01-offline", title="Finding",
        description="First description", identity_version=version,
        source_alert_id=UUID(int=102) if version == "source-v1" else None,
        source_event_ids=["first-event"], raw_event={"first": True},
        event_time="2026-10-20T11:01:00Z", hostname="c01-host",
    )
    alert.id = alert.deterministic_id()
    return alert


def fused(alert=None):
    alert = alert or raw()
    return FusedAlert(
        id=alert.id, tenant_id=alert.tenant_id, alert=alert,
        incident_id=UUID(int=103), fusion_decision=FusionDecision.NEW_INCIDENT,
        enrichments={"ioc_lookup": {"status": "matched", "first": True}, "other": ["original"]},
        confidence_score=.83, anomaly_score=.2, priority_score=.7,
        narrative="Original narrative", session_id=UUID(int=104), session_key_kind="derived",
    )


class Redis:
    def __init__(self):
        self.data = {}
        self.writes = []

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, *, ex, nx):
        self.writes.append((key, ex, nx))
        if nx and key in self.data:
            return None
        self.data[key] = value
        return True


class Pool:
    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


class MemorySink:
    def __init__(self):
        self.snapshot = None
        self.exists = False
        self.outcome = PersistOutcome.INSERTED
        self.persist_calls = []
        self.lookup_calls = 0

    async def lookup_delivery(self, alert):
        self.lookup_calls += 1
        return SnapshotLookup(self.exists, self.snapshot, str(alert.id) if self.exists else None)

    async def persist(self, value, *, replay=None, delivery_snapshot=None):
        self.persist_calls.append((value.model_copy(deep=True), replay.model_copy(deep=True)))
        if self.outcome == PersistOutcome.INSERTED:
            if not self.exists:
                self.snapshot = copy.deepcopy(delivery_snapshot)
            self.exists = True
        return PersistResult(self.outcome, str(value.id))


def worker_fixture(alert=None):
    alert = alert or raw()
    redis = Redis()
    dedup = SimpleNamespace(_redis=redis, is_duplicate=AsyncMock(return_value=(False, None)))
    engine = SimpleNamespace(_dedup=dedup, process=AsyncMock(return_value=fused(alert)))
    sink = MemorySink()
    worker = FusionWorker(engine=engine, sink=sink, dlq=InMemoryDLQ())
    worker._producer = SimpleNamespace(send_and_wait=AsyncMock())
    return worker, sink, engine, redis


@pytest.mark.parametrize("version", ["source-v1", "legacy-v1"])
def test_full_first_snapshot_roundtrip_includes_original_material(version):
    original = fused(raw(version))
    saved = make_snapshot(original)
    restored = restore_snapshot(saved, original.alert)
    assert restored.model_dump(mode="json") == original.model_dump(mode="json")
    metadata = json.loads(_insert_args(original, delivery_snapshot=saved)[-1])["socai2_fusion"]
    assert metadata["delivery_snapshot"] == saved
    assert metadata["incident_id"] == str(original.incident_id)


@pytest.mark.parametrize("fault", ["hash", "tenant", "id", "source", "incident", "decision", "version", "oversize"])
def test_unproven_snapshot_is_rejected(fault):
    alert = raw()
    saved = make_snapshot(fused(alert))
    if fault == "hash":
        saved["sha256"] = "0" * 64
    elif fault == "version":
        saved["version"] = 99
    else:
        payload = saved["fused"]
        if fault == "tenant":
            payload["tenant_id"] = str(UUID(int=999))
        elif fault == "id":
            payload["id"] = str(UUID(int=999))
        elif fault == "source":
            payload["alert"]["source"] = "another-source"
        elif fault == "incident":
            payload["incident_id"] = None
        elif fault == "decision":
            payload["fusion_decision"] = "duplicate"
        elif fault == "oversize":
            payload["alert"]["description"] = "大" * snapshots.MAX_SNAPSHOT_BYTES
        saved["sha256"] = hashlib.sha256(snapshots._canonical(payload)).hexdigest()
    with pytest.raises(DeliveryHold):
        restore_snapshot(saved, alert)


@pytest.mark.parametrize("fault", ["incident", "duplicate", "oversize"])
def test_cannot_cache_an_incomplete_or_truncated_first_result(fault):
    value = fused()
    if fault == "incident":
        value.incident_id = None
    elif fault == "duplicate":
        value.fusion_decision = FusionDecision.DUPLICATE
    else:
        value.alert.description = "x" * snapshots.MAX_SNAPSHOT_BYTES
    with pytest.raises(DeliveryHold):
        make_snapshot(value)


@pytest.mark.asyncio
async def test_nx_finite_cache_keeps_first_completed_result():
    redis = Redis()
    cache = DeliveryRecovery(redis, 300)
    original = fused()
    await cache.remember(original)
    later = original.model_copy(deep=True)
    later.incident_id = UUID(int=999)
    later.enrichments = {"changed": True}
    retained = await DeliveryRecovery(redis, 300).remember(later)
    assert retained.model_dump(mode="json") == original.model_dump(mode="json")
    assert redis.writes == [(cache.key(original.alert), 300, True)] * 2


@pytest.mark.parametrize("operation", ["get", "set"])
@pytest.mark.asyncio
async def test_cache_outage_is_an_explicit_hold(operation):
    redis = Redis()
    setattr(redis, operation, AsyncMock(side_effect=RuntimeError("offline Redis")))
    cache = DeliveryRecovery(redis, 300)
    with pytest.raises(DeliveryHold):
        await (cache.load(raw()) if operation == "get" else cache.remember(fused()))


@pytest.mark.parametrize("version", ["source-v1", "legacy-v1"])
@pytest.mark.asyncio
async def test_lookup_is_tenant_scoped_and_reports_old_snapshotless_rows(version):
    alert = raw(version)
    old_id = UUID(int=900)
    conn = SimpleNamespace(fetchrow=AsyncMock(return_value={"id": old_id, "enrichment_data": {"old": True}}))
    sink = AlertSink("unused")
    sink._ensure_pool = AsyncMock(return_value=Pool(conn))
    result = await sink.lookup_delivery(alert)
    assert result == SnapshotLookup(True, None, str(old_id))
    sql, tenant, identity, fingerprint, allow_legacy_fingerprint = conn.fetchrow.await_args.args
    assert "tenant_id = $1" in sql
    assert tenant == alert.tenant_id and identity == alert.deterministic_id()
    assert fingerprint == alert.fingerprint()
    assert allow_legacy_fingerprint is (version == "legacy-v1")


@pytest.mark.parametrize("fault", ["unavailable", "query", "metadata"])
@pytest.mark.asyncio
async def test_pg_lookup_never_masks_outage_or_bad_metadata_as_missing(fault):
    conn = SimpleNamespace(fetchrow=AsyncMock(return_value={"id": raw().id, "enrichment_data": "not json"}))
    if fault == "query":
        conn.fetchrow.side_effect = RuntimeError("offline PG")
    sink = AlertSink("unused")
    sink._ensure_pool = AsyncMock(return_value=None if fault == "unavailable" else Pool(conn))
    with pytest.raises(DeliveryHold):
        await sink.lookup_delivery(raw())


@pytest.mark.asyncio
async def test_live_snapshot_sink_does_not_insert_a_null_incident():
    value = fused()
    original_snapshot = make_snapshot(value)
    value.incident_id = None
    value.fusion_decision = FusionDecision.DUPLICATE
    conn = SimpleNamespace(fetchrow=AsyncMock())
    sink = AlertSink("unused")
    sink._ensure_pool = AsyncMock(return_value=Pool(conn))
    result = await sink.persist(value, delivery_snapshot=original_snapshot)
    assert result.outcome == PersistOutcome.FAILED
    conn.fetchrow.assert_not_awaited()


@pytest.mark.parametrize("version", ["source-v1", "legacy-v1"])
@pytest.mark.asyncio
async def test_pg_first_snapshot_recovers_after_publish_failure_and_total_redis_loss(version):
    alert = raw(version)
    worker, sink, engine, redis = worker_fixture(alert)
    worker._producer.send_and_wait.side_effect = RuntimeError("broker delivery rejected")
    with pytest.raises(RuntimeError, match="delivery rejected"):
        await worker._fuse_and_persist(alert)
    saved = copy.deepcopy(sink.snapshot)
    redis.data.clear()
    # A new worker/process may only use the PG snapshot. Its engine and cache
    # contain no prior result, and the replay's content has changed.
    replay = alert.model_copy(deep=True)
    replay.description = "Later changed content"
    replay.raw_event = {"later": True}
    cold = FusionWorker(engine=SimpleNamespace(process=AsyncMock(side_effect=AssertionError("recomputed"))), sink=sink)
    cold._producer = SimpleNamespace(send_and_wait=AsyncMock())
    sink.outcome = PersistOutcome.DUPLICATE
    await cold._fuse_and_persist(replay)
    emitted = cold._producer.send_and_wait.await_args.kwargs["value"]
    assert {key: emitted[key] for key in saved["fused"]} == saved["fused"]
    assert emitted["alert_row_id"] == str(alert.id)
    assert sink.snapshot == saved
    assert sink.persist_calls[-1][1].raw_event == {"later": True}
    engine.process.assert_awaited_once()
    cold._engine.process.assert_not_awaited()


@pytest.mark.parametrize("version", ["source-v1", "legacy-v1"])
@pytest.mark.asyncio
async def test_warm_snapshot_repairs_missing_pg_without_recorrelation_or_enrichment(version):
    alert = raw(version)
    worker, sink, engine, redis = worker_fixture(alert)
    sink.outcome = PersistOutcome.UNAVAILABLE
    with pytest.raises(DeliveryHold, match="persistence was not confirmed"):
        await worker._fuse_and_persist(alert)
    worker._producer.send_and_wait.assert_not_awaited()
    # Fresh engine, same finite Redis cache. The dedup marker is warm, but it
    # is not used as a substitute for the exact complete cached result.
    engine2 = SimpleNamespace(_dedup=SimpleNamespace(_redis=redis, is_duplicate=AsyncMock(return_value=(True, str(alert.id)))),
                              process=AsyncMock(side_effect=AssertionError("recomputed")))
    cold = FusionWorker(engine=engine2, sink=sink)
    cold._producer = SimpleNamespace(send_and_wait=AsyncMock())
    sink.outcome = PersistOutcome.INSERTED
    changed = alert.model_copy(deep=True)
    changed.description = "Do not adopt current content"
    await cold._fuse_and_persist(changed)
    engine2.process.assert_not_awaited()
    assert sink.snapshot["fused"]["incident_id"] == str(UUID(int=103))
    assert sink.snapshot["fused"]["alert"]["description"] == "First description"
    assert sink.snapshot["fused"]["enrichments"]["other"] == ["original"]
    engine.process.assert_awaited_once()


@pytest.mark.parametrize("version", ["source-v1", "legacy-v1"])
@pytest.mark.parametrize("fault", ["warm_without_snapshot", "old_pg_without_snapshot", "invalid_cache"])
@pytest.mark.asyncio
async def test_unprovable_recovery_never_recomputes_or_inserts(version, fault):
    alert = raw(version)
    worker, sink, engine, redis = worker_fixture(alert)
    if fault == "warm_without_snapshot":
        engine._dedup.is_duplicate.return_value = (True, str(alert.id))
    elif fault == "old_pg_without_snapshot":
        sink.exists = True
    else:
        redis.data[DeliveryRecovery.key(alert)] = b"bad snapshot"
    with pytest.raises(DeliveryHold):
        await worker._fuse_and_persist(alert)
    engine.process.assert_not_awaited()
    assert sink.persist_calls == []
    worker._producer.send_and_wait.assert_not_awaited()


@pytest.mark.asyncio
async def test_pg_snapshot_is_authoritative_over_bad_cache():
    alert = raw()
    worker, sink, engine, redis = worker_fixture(alert)
    sink.exists = True
    sink.snapshot = make_snapshot(fused(alert))
    sink.outcome = PersistOutcome.DUPLICATE
    redis.data[DeliveryRecovery.key(alert)] = b"corrupt"
    await worker._fuse_and_persist(alert)
    engine.process.assert_not_awaited()
    worker._producer.send_and_wait.assert_awaited_once()


@pytest.mark.asyncio
async def test_duplicate_outcome_without_real_pg_row_is_not_durable():
    worker, sink, engine, _ = worker_fixture(raw("legacy-v1"))
    sink.outcome = PersistOutcome.DUPLICATE
    with pytest.raises(DeliveryHold, match="no confirmed PostgreSQL row"):
        await worker._fuse_and_persist(raw("legacy-v1"))
    worker._producer.send_and_wait.assert_not_awaited()


class Consumer:
    def __init__(self, messages):
        self.messages = iter(messages)
        self.commits = []
        self.commit_error = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.messages)
        except StopIteration:
            raise StopAsyncIteration

    async def commit(self, offsets):
        self.commits.append(offsets)
        if self.commit_error:
            raise RuntimeError("commit not confirmed")


def message(offset, partition=0):
    return SimpleNamespace(value={"offset": offset}, topic="c01.raw", partition=partition, offset=offset)


@pytest.mark.asyncio
async def test_only_current_partition_completed_offset_is_committed():
    worker, *_ = worker_fixture()
    worker._consumer = Consumer([message(4, 1), message(8, 2)])
    worker._running = True
    worker._process_message = AsyncMock()
    await worker._consume_loop()
    assert worker._consumer.commits == [{TopicPartition("c01.raw", 1): 5}, {TopicPartition("c01.raw", 2): 9}]
    assert worker.attached is False


@pytest.mark.parametrize("failure", ["processing", "commit", "cancel"])
@pytest.mark.asyncio
async def test_failure_stops_before_any_later_record_can_cross_it(failure):
    worker, *_ = worker_fixture()
    worker._consumer = Consumer([message(0), message(1)])
    worker._running = True
    worker._process_message = AsyncMock()
    if failure == "processing":
        worker._process_message.side_effect = RuntimeError("processing failed")
    elif failure == "commit":
        worker._consumer.commit_error = True
    else:
        worker._process_message.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError if failure == "cancel" else RuntimeError):
        await worker._consume_loop()
    worker._process_message.assert_awaited_once()
    assert worker._consumer.commits == ([{TopicPartition("c01.raw", 0): 1}] if failure == "commit" else [])
    assert worker.attached is False


def letter():
    return DeadLetter.build(topic="c01.raw", payload={"invalid": True}, reason="bad schema", schema_version="v1", partition=0, offset=1)


@pytest.mark.parametrize("fault", ["no_pool", "exception", "bad_status", "none"])
@pytest.mark.asyncio
async def test_postgres_dlq_requires_explicit_insert_confirmation(fault):
    conn = SimpleNamespace(execute=AsyncMock(return_value="INSERT 0 1"))
    if fault == "exception":
        conn.execute.side_effect = RuntimeError("offline PG")
    elif fault == "bad_status":
        conn.execute.return_value = "INSERT 0 0"
    dlq = PostgresDLQ(lambda: None if fault == "no_pool" else Pool(conn))
    assert await safe_record(dlq, letter()) is (fault == "none")


@pytest.mark.asyncio
async def test_kafka_dlq_awaits_delivery_confirmation():
    producer = SimpleNamespace(send=AsyncMock(), send_and_wait=AsyncMock(side_effect=RuntimeError("delivery rejected")))
    dlq = KafkaDLQ(producer)
    assert await safe_record(dlq, letter()) is False
    producer.send.assert_not_awaited()
    producer.send_and_wait.assert_awaited_once()


@pytest.mark.parametrize("dlq", [LoggingDLQ(), SimpleNamespace(record=AsyncMock(return_value=False))])
@pytest.mark.asyncio
async def test_live_poison_message_cannot_commit_on_unconfirmed_or_logging_dlq(dlq):
    worker, *_ = worker_fixture()
    worker._dlq = dlq
    with pytest.raises(DeliveryHold):
        await worker._dead_letter(topic="c01.raw", payload={}, reason="bad schema")


@pytest.mark.asyncio
async def test_confirmed_dlq_allows_the_one_poison_input_to_be_committed():
    worker, *_ = worker_fixture()
    worker._consumer = Consumer([message(0)])
    worker._running = True
    worker._process_message = lambda *args, **kwargs: worker._dead_letter(topic="c01.raw", payload={}, reason="bad schema")
    await worker._consume_loop()
    assert len(worker._dlq.records) == 1
    assert worker._consumer.commits == [{TopicPartition("c01.raw", 0): 1}]
