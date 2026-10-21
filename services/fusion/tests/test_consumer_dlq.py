"""Phase 5 — the fusion consumer dead-letters poison messages (never drops).

Before Phase 5 the consumer logged a warning and dropped a malformed message —
silent data loss. These tests drive ``FusionWorker._process_message`` directly
(no Kafka) with an in-memory DLQ and prove: a valid event is processed and the
DLQ stays empty; every poison shape is captured in the DLQ with a reason; and
an unconfirmed DLQ stops live consumption before a later input can pass it.
PG, Redis, and Kafka in this module are explicit in-memory/async doubles.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from app.core.config import settings
from app.models.alert import FusedAlert, FusionDecision
from app.services.alert_sink import PersistOutcome, PersistResult
from app.services.delivery_recovery import DeliveryHold, SnapshotLookup
from app.services.dlq import InMemoryDLQ
from app.workers.consumer import FusionWorker

pytestmark = pytest.mark.asyncio

TENANT = "00000000-0000-0000-0000-000000000001"
RAW_EVENTS = settings.kafka_topic_raw_events
ALERTS_RAW = settings.kafka_topic_alerts_raw


def _valid_raw_event() -> dict:
    return {
        "tenant_id": TENANT,
        "ocsf_event": {
            "class_uid": 2001,
            "category_uid": 2,
            "severity_id": 5,
            "message": "Credential dumping",
            "metadata": {"uid": "ev-1", "product": {"name": "Falcon", "vendor_name": "CrowdStrike"}},
        },
    }


def _worker_with_dlq() -> tuple[FusionWorker, InMemoryDLQ]:
    dlq = InMemoryDLQ()

    class Redis:
        def __init__(self):
            self.data = {}

        async def get(self, key):
            return self.data.get(key)

        async def set(self, key, value, *, nx, ex):
            assert nx is True and ex > 0
            if key in self.data:
                return None
            self.data[key] = value
            return True

    class Sink:
        def __init__(self):
            self.snapshot = None

        async def lookup_delivery(self, alert):
            return SnapshotLookup(self.snapshot is not None, self.snapshot, str(alert.id))

        async def persist(self, value, *, replay, delivery_snapshot):
            self.snapshot = delivery_snapshot
            return PersistResult(PersistOutcome.INSERTED, str(value.id))

    async def process(alert):
        return FusedAlert(
            id=alert.id, tenant_id=alert.tenant_id, alert=alert,
            incident_id=UUID(int=9001), fusion_decision=FusionDecision.NEW_INCIDENT,
        )

    engine = SimpleNamespace(
        _dedup=SimpleNamespace(_redis=Redis(), is_duplicate=AsyncMock(return_value=(False, None))),
        process=AsyncMock(side_effect=process),
    )
    worker = FusionWorker(engine=engine, sink=Sink(), dlq=dlq)
    worker._producer = AsyncMock()  # noqa: SLF001 — test drives the internals
    return worker, dlq


async def test_valid_event_is_processed_and_not_dead_lettered():
    worker, dlq = _worker_with_dlq()
    await worker._process_message(_valid_raw_event(), topic=RAW_EVENTS)  # noqa: SLF001
    assert dlq.records == []
    worker._engine.process.assert_awaited_once()  # noqa: SLF001
    worker._producer.send_and_wait.assert_awaited_once()  # noqa: SLF001
    worker._producer.send.assert_not_awaited()  # noqa: SLF001
    envelope = worker._producer.send_and_wait.await_args.kwargs["value"]  # noqa: SLF001
    assert envelope["incident_id"] == str(UUID(int=9001))
    assert worker._sink.snapshot["fused"]["id"] == envelope["alert_row_id"]  # noqa: SLF001


async def test_missing_ocsf_event_is_dead_lettered_not_dropped():
    worker, dlq = _worker_with_dlq()
    await worker._process_message({"tenant_id": TENANT}, topic=RAW_EVENTS)  # noqa: SLF001
    assert len(dlq.records) == 1
    assert "ocsf_event" in dlq.records[0].reason
    worker._engine.process.assert_not_awaited()  # noqa: SLF001


async def test_unknown_schema_version_is_dead_lettered():
    worker, dlq = _worker_with_dlq()
    poison = _valid_raw_event()
    poison["schema_version"] = "v99"
    await worker._process_message(poison, topic=RAW_EVENTS)  # noqa: SLF001
    assert len(dlq.records) == 1
    assert "unknown schema_version" in dlq.records[0].reason


async def test_non_uuid_tenant_is_dead_lettered_with_lineage():
    worker, dlq = _worker_with_dlq()
    poison = _valid_raw_event()
    poison["tenant_id"] = "not-a-uuid"
    poison["ocsf_event"].pop("tenant_uid", None)
    await worker._process_message(poison, topic=RAW_EVENTS)  # noqa: SLF001
    assert len(dlq.records) == 1
    assert dlq.records[0].source_event_id == "ev-1"


async def test_invalid_raw_alert_is_dead_lettered_not_silently_dropped():
    worker, dlq = _worker_with_dlq()
    # Missing every required RawAlert field — deep Pydantic validation fails.
    await worker._process_message({"tenant_id": TENANT, "nonsense": True}, topic=ALERTS_RAW)  # noqa: SLF001
    assert len(dlq.records) == 1
    assert "RawAlert validation failed" in dlq.records[0].reason
    worker._engine.process.assert_not_awaited()  # noqa: SLF001


async def test_failed_dead_letter_holds_the_live_input():
    class ExplodingDLQ:
        async def record(self, dead_letter):  # noqa: ANN001, ARG002
            raise RuntimeError("dlq sink down")

    engine = SimpleNamespace(process=AsyncMock())
    worker = FusionWorker(engine=engine, sink=None, dlq=ExplodingDLQ())
    worker._producer = AsyncMock()  # noqa: SLF001
    # safe_record catches the sink exception; the live worker must then hold
    # the input instead of treating that missing DLQ row as delivery success.
    with pytest.raises(DeliveryHold, match="dead-letter persistence was not confirmed"):
        await worker._process_message({"tenant_id": TENANT}, topic=RAW_EVENTS)  # noqa: SLF001
    engine.process.assert_not_awaited()
    worker._producer.send_and_wait.assert_not_awaited()  # noqa: SLF001


@pytest.mark.parametrize("failure", ["false", "exception"])
async def test_unconfirmed_poison_prevents_the_next_valid_input_and_commit(failure):
    worker, _ = _worker_with_dlq()
    record = AsyncMock(return_value=False)
    if failure == "exception":
        record.side_effect = RuntimeError("DLQ unavailable")
    worker._dlq = SimpleNamespace(record=record)  # noqa: SLF001

    class Consumer:
        def __init__(self):
            self.messages = iter([
                SimpleNamespace(value={"tenant_id": TENANT}, topic=RAW_EVENTS, partition=0, offset=0),
                SimpleNamespace(value=_valid_raw_event(), topic=RAW_EVENTS, partition=0, offset=1),
            ])
            self.yielded = 0
            self.commit = AsyncMock()

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                message = next(self.messages)
            except StopIteration:
                raise StopAsyncIteration
            self.yielded += 1
            return message

    consumer = Consumer()
    worker._consumer = consumer  # noqa: SLF001
    worker._running = True  # noqa: SLF001
    # Drive the real _consume_loop -> _process_message -> _dead_letter chain.
    with pytest.raises(DeliveryHold):
        await worker._consume_loop()  # noqa: SLF001
    assert consumer.yielded == 1
    consumer.commit.assert_not_awaited()
    record.assert_awaited_once()
    worker._engine.process.assert_not_awaited()  # noqa: SLF001
    worker._producer.send_and_wait.assert_not_awaited()  # noqa: SLF001
    assert worker.attached is False
