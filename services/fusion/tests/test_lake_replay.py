"""Direct fixed-range and aggregate tests, using only synthetic messages."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from aiokafka.structs import TopicPartition
from app.services.lake_ingress import IngressProfile, KafkaPosition, adapt_ocsf
from app.services.lake_replay import (
    ReplayAggregate,
    ReplayCheckError,
    ReplayLimits,
    consume_frozen,
    normalized,
    private_json,
)
from app.services.lake_writer import LakePersistenceError, LakeWriter
from app.workers.lake_consumer import LakeConsumer, LakeConsumerProfile

from .lake_ingress_cases import database_cases, encoded, event
from .test_lake_consumer import Native

ROOT = Path(__file__).resolve().parents[3]
TOPIC = "lyc-ocsf-events"


@pytest.fixture
def profile():
    return IngressProfile.load(ROOT / "deploy/aisoc21/lake-ingress-3c/ingress.example.json", database="lyc_lake_3c_example")


def test_real_content_aggregation_distinguishes_updates_duplicates_and_missing_ids(profile):
    aggregate = ReplayAggregate(profile)
    raw = encoded(event())
    updated = encoded(event(severity_id=4))
    inputs = [raw, raw, raw.replace(b'\n', b' '), updated, encoded(event(metadata={"version": "1.9.0"})),
              encoded(event(metadata={"version": "1.9.0"})), b'\xff', None]
    rows = []
    for offset, payload in enumerate(inputs):
        pos = KafkaPosition(TOPIC, 0, offset)
        aggregate.add_input(payload, pos)
        rows.append(normalized(adapt_ocsf(payload, profile=profile, position=pos).row))
    # ReplacingMergeTree may already have merged duplicates; choose an actual
    # received representation, not a reconstructed/pretty-printed body.
    for row in [rows[2], *rows[3:]]:
        aggregate.add_saved(row)
    report = aggregate.report(require_complete=True)
    assert report["messages"] == 8 and report["logical_versions"] == 6 and report["duplicate_deliveries"] == 2
    assert report["updated_source_records"] == 1 and report["additional_source_versions"] == 1
    assert report["physical_rows"] == 6 and report["expected_logical_digest"] == report["saved_logical_digest"]
    assert report["input_material_variants"] > report["stored_material_variants"]


@pytest.mark.parametrize("mutation", ["truncate", "wrong_id", "wrong_position"])
def test_stored_material_corruption_is_not_hidden_by_input_side_digest(profile, mutation):
    aggregate = ReplayAggregate(profile)
    raw = dict(database_cases())["large"]
    pos = KafkaPosition(TOPIC, 0, 0)
    aggregate.add_input(raw, pos)
    saved = normalized(adapt_ocsf(raw, profile=profile, position=pos).row)
    if mutation == "truncate":
        saved["ocsf_json"] = saved["ocsf_json"][:200]
    elif mutation == "wrong_id":
        saved["event_id"] = "00000000-0000-0000-0000-000000000000"
    else:
        saved["kafka_offset"] = 42
    with pytest.raises(ReplayCheckError):
        aggregate.add_saved(saved)
    assert not aggregate.report()["complete"]


def test_missing_versions_and_empty_input_are_not_success(profile):
    aggregate = ReplayAggregate(profile)
    with pytest.raises(ReplayCheckError):
        aggregate.report(require_complete=True)
    aggregate.add_input(b'{}', KafkaPosition(TOPIC, 0, 0))
    assert aggregate.report()["saved_logical_versions"] == 0
    with pytest.raises(ReplayCheckError):
        aggregate.report(require_complete=True)


@pytest.mark.asyncio
async def test_frozen_end_filters_prefetched_messages_and_preserves_offset_gaps(profile):
    tp = TopicPartition(TOPIC, 0)
    values = [SimpleNamespace(topic=TOPIC, partition=0, offset=offset, timestamp=1000, value=encoded(event(time=offset)))
              for offset in (1, 3, 10)]
    class Reader:
        def __init__(self):
            self.commits = []
        async def getmany(self, *partitions, **kwargs):
            return {tp: values}
        async def position(self, partition):
            return 11
        async def commit(self, positions):
            self.commits.append(positions)
    reader = Reader()
    native = Native()
    writer = LakeWriter(host="unused.invalid", database=profile.database, ingress_profile=profile)
    writer._client = native
    consumer_profile = LakeConsumerProfile.load(ROOT / "deploy/aisoc21/lake-consumer-3d/consumer.example.json")
    worker = LakeConsumer(writer, consumer_profile);worker._consumer = reader
    aggregate = ReplayAggregate(profile)
    limits = ReplayLimits(TOPIC, 60, 100, 100, 30)
    progress = {"0": {"messages": 0}}
    last_saved = await consume_frozen(reader, worker, aggregate, limits, {tp: (1, 5)}, progress)
    assert last_saved == {tp: 4} and reader.commits == [{tp: 4}]
    assert aggregate.messages == 2 and [row["kafka_offset"] for row in native.rows] == [1, 3]
    assert progress["0"]["scanned_next_offset"] == 5
    # This is a real writer with native I/O substituted; 3d owns save/commit.
    for row in native.rows:
        aggregate.add_saved(row)
    assert aggregate.report(require_complete=True)["logical_versions"] == 2


@pytest.mark.asyncio
async def test_frozen_write_failure_stops_without_advancing_commit(profile):
    from unittest.mock import AsyncMock

    tp = TopicPartition(TOPIC, 0)
    native = Native(); native.fail_partition = 0
    writer = LakeWriter(host="unused.invalid", database=profile.database, ingress_profile=profile);writer._client = native
    consumer_profile = LakeConsumerProfile.load(ROOT / "deploy/aisoc21/lake-consumer-3d/consumer.example.json")
    reader = SimpleNamespace(getmany=AsyncMock(return_value={tp: [SimpleNamespace(topic=TOPIC, partition=0, offset=0, timestamp=1000, value=b'{}')]}),
                             commit=AsyncMock(), position=AsyncMock(return_value=1))
    worker = LakeConsumer(writer, consumer_profile);worker._consumer = reader
    with pytest.raises(LakePersistenceError):
        await consume_frozen(reader, worker, ReplayAggregate(profile), ReplayLimits(TOPIC, 60, 100, 100, 30),
                             {tp: (0, 2)}, {"0": {"messages": 0}})
    reader.commit.assert_not_awaited()
    assert worker.pending and worker.readback == ("not_observed",)


def test_private_report_refuses_overwrite_and_roundtrips(tmp_path):
    target = tmp_path / "report.json"
    private_json(target, {"status": "passed", "synthetic": True})
    assert target.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        private_json(target, {"status": "overwritten"})


@pytest.mark.asyncio
async def test_partial_report_preserves_an_earlier_partition_confirmation(profile):
    from unittest.mock import AsyncMock

    tps = [TopicPartition(TOPIC, i) for i in (0, 1)]
    batch = {tp: [SimpleNamespace(topic=TOPIC, partition=tp.partition, offset=0, timestamp=1000, value=b'{}')] for tp in tps}
    native = Native(); native.fail_partition = 1
    writer = LakeWriter(host="unused.invalid", database=profile.database, ingress_profile=profile);writer._client = native
    consumer_profile = LakeConsumerProfile.load(ROOT / "deploy/aisoc21/lake-consumer-3d/consumer.example.json")
    reader = SimpleNamespace(getmany=AsyncMock(return_value=batch), commit=AsyncMock(), position=AsyncMock(return_value=1))
    worker = LakeConsumer(writer, consumer_profile);worker._consumer = reader
    progress = {str(tp.partition): {"messages": 0, "confirmed_next_offset": None} for tp in tps}
    with pytest.raises(LakePersistenceError):
        await consume_frozen(reader, worker, ReplayAggregate(profile), ReplayLimits(TOPIC, 60, 100, 100, 30),
                             {tp: (0, 1) for tp in tps}, progress)
    assert reader.commit.await_args.args[0] == {tps[0]: 1}
    assert progress["0"]["confirmed_messages"] == 1 and progress["0"]["confirmed_next_offset"] == 1
    assert progress["1"]["confirmed_next_offset"] is None and set(worker.pending) == {tps[1]}
