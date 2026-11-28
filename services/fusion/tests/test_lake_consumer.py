"""3d direct save/commit boundary tests; all records are synthetic."""

import asyncio
import dataclasses
import hashlib
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiokafka.structs import TopicPartition
from app.core.config import settings
from app.services.lake_ingress import IngressProfile
from app.services.lake_writer import LakePersistenceError, LakeWriter
from app.workers.consumer import FusionWorker
from app.workers.lake_consumer import LakeConsumeHold, LakeConsumer, LakeConsumerProfile

from .lake_ingress_cases import encoded, event

ROOT = Path(__file__).resolve().parents[3]
TOPIC = "lyc-ocsf-events"


def message(partition, offset, value=b'{"class_uid":0}'):
    return SimpleNamespace(topic=TOPIC, partition=partition, offset=offset, timestamp=1000, value=value)


class Native:
    def __init__(self):
        self.rows = []
        self.attempts = 0
        self.fail_partition = None
        self.lose_reply = False
        self.started = threading.Event()
        self.release = None
        self.disconnected = False

    def execute(self, sql, data=None, **kw):
        if sql.startswith("INSERT"):
            self.attempts += 1
            self.started.set()
            if self.release is not None:
                assert self.release.wait(3)
            if data[0]["kafka_partition"] == self.fail_partition:
                if self.lose_reply:
                    self.rows.extend(data)
                raise ConnectionError("private body must never appear in consumer status")
            self.rows.extend(data)
            return None
        if "migration_id" in sql:
            return [("005_lake_ingress_v1",)]
        if "LIMIT 0" in sql:
            return []
        return [(row["event_id"], row["source_version"], hashlib.sha256(row["ocsf_json"].encode()).hexdigest().upper(),
                 hashlib.sha256(row["raw_payload"].encode()).hexdigest().upper()) for row in self.rows]

    def disconnect(self):
        self.disconnected = True


class Broker:
    def __init__(self, batches):
        self.batches = list(batches)
        self.commits = []
        self.idle = asyncio.Event()
        self.stopped = False
        self.polls = 0
        self.assigned = set(batches[0]) if batches else set()
        self.seek_to_beginning = AsyncMock(return_value=True)
        self.committed = AsyncMock(return_value=None)
        self.fail_commit = False

    def subscribe(self, *, topics, listener):
        self.topics, self.listener = topics, listener

    async def start(self):
        await self.listener.on_partitions_assigned(self.assigned)

    async def stop(self):
        self.stopped = True

    async def getmany(self, **kwargs):
        self.polls += 1
        if self.batches:
            return self.batches.pop(0)
        self.idle.set()
        await asyncio.Event().wait()

    async def commit(self, offsets):
        if self.fail_commit:
            raise ConnectionError("commit response unknown")
        self.commits.append(offsets)


@pytest.fixture
def setup(monkeypatch):
    config = LakeConsumerProfile.load(ROOT / "deploy/aisoc21/lake-consumer-3d/consumer.example.json")
    ingress = IngressProfile.load(ROOT / "deploy/aisoc21/lake-ingress-3c/ingress.example.json", database="lyc_lake_3c_example")
    writer = LakeWriter(host="unused.invalid", database=ingress.database, ingress_profile=ingress)
    native = Native()
    writer._client = native
    worker = LakeConsumer(writer, config)
    monkeypatch.setattr("app.workers.lake_consumer.kafka_client_kwargs", lambda: {"security_protocol": "PLAINTEXT"})

    def attach(batches):
        broker = Broker(batches)
        captured = {}
        def construct(**kwargs):
            captured.update(kwargs)
            return broker
        monkeypatch.setattr("app.workers.lake_consumer.AIOKafkaConsumer", construct)
        return broker, captured
    return worker, native, attach


@pytest.mark.asyncio
async def test_raw_low_volume_partition_commits_follow_complete_insert(setup):
    worker, native, attach = setup
    tp0, tp1 = TopicPartition(TOPIC, 0), TopicPartition(TOPIC, 1)
    raw = encoded(event(raw_data="x" * 70000, extension="y" * 280000))
    broker, kwargs = attach([{tp0: [message(0, 4, raw), message(0, 8, b'\xff')], tp1: [message(1, 0, None)]}])
    task = asyncio.create_task(worker.run())
    await asyncio.wait_for(broker.idle.wait(), 2)
    assert broker.commits == [{tp0: 9}, {tp1: 1}]
    assert len(native.rows) == 3 and native.rows[0]["ocsf_json"].encode() == raw
    assert not worker.pending and worker.attached and native.attempts == 2
    assert kwargs["value_deserializer"] is None and kwargs["enable_auto_commit"] is False
    assert kwargs["auto_offset_reset"] == "none" and kwargs["group_id"] == worker.profile.group_id
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert broker.stopped and not worker.attached


@pytest.mark.asyncio
@pytest.mark.parametrize("lost_reply", [False, True], ids=["insert_rejected", "saved_reply_unknown"])
async def test_failed_or_unknown_insert_never_skips_pending_input(setup, lost_reply):
    worker, native, attach = setup
    tp0, tp1, tp2 = [TopicPartition(TOPIC, i) for i in range(3)]
    native.fail_partition, native.lose_reply = 1, lost_reply
    broker, _ = attach([{tp0: [message(0, 0)], tp1: [message(1, 0)], tp2: [message(2, 0)]},
                        {tp1: [message(1, 1)]}])
    with pytest.raises(LakePersistenceError):
        await worker.run()
    assert broker.commits == [{tp0: 1}] and broker.polls == 1
    assert set(worker.pending) == {tp1, tp2} and native.attempts == 2
    assert worker.readback == (("present",) if lost_reply else ("not_observed",))
    assert not worker.attached and broker.stopped
    assert "private body" not in str(worker.status()) and worker.failure["outcome"] == "unknown"


@pytest.mark.asyncio
async def test_cancel_joins_native_before_readback_disconnect_or_commit(setup):
    worker, native, attach = setup
    tp = TopicPartition(TOPIC, 0)
    broker, _ = attach([{tp: [message(0, 0)]}])
    native.release = threading.Event()
    task = asyncio.create_task(worker.run())
    assert await asyncio.to_thread(native.started.wait, 2)
    task.cancel()
    await asyncio.sleep(0)
    # A second cancellation must not unlock the native connection either.
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done() and not broker.stopped and not broker.commits
    native.release.set()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, 2)
    assert worker.readback == ("present",) and tp in worker.pending and broker.stopped
    await worker.lake.stop()
    assert native.disconnected and not broker.commits


@pytest.mark.asyncio
async def test_partition_revoke_during_save_never_commits_old_batch(setup):
    worker, native, attach = setup
    tp = TopicPartition(TOPIC, 0)
    broker, _ = attach([{tp: [message(0, 0)]}])
    native.release = threading.Event()
    task = asyncio.create_task(worker.run())
    assert await asyncio.to_thread(native.started.wait, 2)
    await broker.listener.on_partitions_revoked({tp})
    native.release.set()
    with pytest.raises(LakeConsumeHold, match="partition_revoked"):
        await asyncio.wait_for(task, 2)
    assert native.rows and not broker.commits and tp in worker.pending and not worker.attached


@pytest.mark.asyncio
async def test_commit_unknown_keeps_saved_range_without_rewrite(setup):
    worker, native, attach = setup
    tp = TopicPartition(TOPIC, 0)
    broker, _ = attach([{tp: [message(0, 0)]}, {tp: [message(0, 1)]}])
    broker.fail_commit = True
    with pytest.raises(ConnectionError):
        await worker.run()
    assert native.attempts == 1 and broker.polls == 1 and tp in worker.pending
    assert worker.failure["phase"] == "commit" and not worker.attached


@pytest.mark.asyncio
async def test_incomplete_receipts_never_commit(setup):
    worker, _native, attach = setup
    tp = TopicPartition(TOPIC, 0)
    broker, _ = attach([{tp: [message(0, 0)]}])
    worker.lake.write_ocsf_batch = AsyncMock(return_value=())
    with pytest.raises(LakeConsumeHold, match="incomplete_persistence_receipts"):
        await worker.run()
    assert not broker.commits and tp in worker.pending


@pytest.mark.asyncio
async def test_missing_initial_commit_policy_and_unknown_readback(setup):
    worker, native, attach = setup
    worker.profile = dataclasses.replace(worker.profile, initial_offset="require_committed")
    tp = TopicPartition(TOPIC, 0)
    broker, _ = attach([{tp: [message(0, 0)]}])
    with pytest.raises(LakeConsumeHold, match="assignment_failed"):
        await worker.run()
    broker.seek_to_beginning.assert_not_awaited()
    assert not broker.commits and not native.rows
    worker.lake._client = None
    from app.services.lake_ingress import KafkaPosition
    assert await worker.lake.inspect_ocsf_batch([(b"{}", KafkaPosition(TOPIC, 0, 0))]) == ("unknown",)


def test_activation_requires_explicit_writer_profile_and_separate_group(setup):
    worker, _, _ = setup
    with pytest.raises(ValueError, match="requires lake writer"):
        FusionWorker(engine=None, lake_consumer_profile=worker.profile)
    with pytest.raises(ValueError, match="separate topic and consumer group"):
        FusionWorker(engine=None, lake=worker.lake,
                     lake_consumer_profile=dataclasses.replace(worker.profile, group_id=settings.kafka_consumer_group))
    fusion = FusionWorker(engine=None, lake=worker.lake, lake_consumer_profile=worker.profile)
    fusion._attached = True
    assert not fusion.attached
    fusion._lake_consumer._attached = True
    assert fusion.attached
    fusion._lake_consumer.failure = {"phase": "insert"}
    assert not fusion.attached


@pytest.mark.asyncio
async def test_waits_for_all_initial_positions_before_first_poll(setup):
    worker, _native, attach = setup
    tp = TopicPartition(TOPIC, 0)
    broker, _ = attach([{tp: [message(0, 0)]}])
    release = asyncio.Event()
    started = asyncio.Event()
    listener_task = None

    async def seek(*partitions):
        started.set()
        await release.wait()
        return True

    async def start_before_listener_finishes():
        nonlocal listener_task
        listener_task = asyncio.create_task(broker.listener.on_partitions_assigned(broker.assigned))

    broker.start = start_before_listener_finishes
    broker.seek_to_beginning = seek
    task = asyncio.create_task(worker.run())
    await asyncio.wait_for(started.wait(), 2)
    await asyncio.sleep(0)
    assert broker.polls == 0 and not worker.attached and not broker.commits
    release.set()
    await asyncio.wait_for(broker.idle.wait(), 2)
    assert broker.commits == [{tp: 1}]
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await listener_task
