"""Bounded lake acceptance; raw records and aggregate reports stay on the data host.

This is an operator-invoked verification path, not another service consumer.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from aiokafka import AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient
from aiokafka.structs import TopicPartition

from app.core.kafka_security import kafka_client_kwargs
from app.services.lake_ingress import (
    IngressProfile,
    KafkaPosition,
    adapt_ocsf,
    datetime_milliseconds,
    json_text,
)
from app.services.lake_writer import LakeWriter, _settled_thread
from app.workers.lake_consumer import LakeConsumer, LakeConsumerProfile

# Only the identities/quality/materials needed by this acceptance step. Full
# query tools and device/IP lookup belong to 3f, not this comparison.
IDENTITY_COLUMNS = (
    "event_id", "tenant_id", "event_time", "class_uid", "source_namespace", "source_event_id", "source_version",
    "mapping_version", "connector_type", "kafka_cluster", "parse_status", "event_time_source", "is_alert",
)
READ_COLUMNS = (*IDENTITY_COLUMNS, "kafka_topic", "kafka_partition", "kafka_offset", "kafka_timestamp", "ocsf_json", "raw_payload")


class ReplayCheckError(RuntimeError):
    """Invariant name only; never include a record or value in exception text."""


@dataclass(frozen=True)
class ReplayLimits:
    topic: str
    max_duration_seconds: int
    max_messages: int
    readback_block_size: int
    query_timeout_seconds: int

    def __post_init__(self):
        if not isinstance(self.topic, str) or not self.topic.strip():
            raise ValueError("explicit replay topic required")
        for name in ("max_duration_seconds", "max_messages", "readback_block_size", "query_timeout_seconds"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError("positive explicit replay limits required")

    @classmethod
    def load(cls, path):
        body = json.loads(Path(path).read_text())
        if set(body) != set(cls.__dataclass_fields__):
            raise ValueError("incomplete replay limits")
        return cls(**body)


def private_json(path: Path, body):
    """Exclusive, private file and immediate readback; no overwrite/resume."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(body, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    if json.loads(path.read_text()) != body:
        raise ReplayCheckError("private_report_readback_mismatch")


def normalized(row):
    result = dict(row)
    for name in ("event_id", "tenant_id"):
        result[name] = str(result[name])
    for name in ("event_time", "kafka_timestamp"):
        if result[name] is not None and not isinstance(result[name], int):
            result[name] = datetime_milliseconds(result[name])
    return result


def identity(row):
    return tuple(row[name] for name in IDENTITY_COLUMNS)


def material_digest(row):
    digest = hashlib.sha256()
    for name in ("ocsf_json", "raw_payload"):
        raw = row[name].encode("utf-8")
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
    return digest.hexdigest()


def location(row):
    return (row["kafka_topic"], row["kafka_partition"], row["kafka_offset"], row["kafka_timestamp"])


def bucket(row):
    return json_text([row["class_uid"], row["parse_status"], row["event_time_source"]])


def logical_digest(signatures):
    digest = hashlib.sha256()
    for signature in sorted(signatures.values(), key=lambda item: item[0]):
        encoded = json_text(list(signature)).encode()
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


class ReplayAggregate:
    """No original-body copies: expected identities, exact material hashes and positions."""

    def __init__(self, profile: IngressProfile):
        self.profile = profile
        self.messages = 0
        self.input_groups = Counter()
        self.signatures = {}
        self.materials = {}
        self.source_versions = {}
        self.actual_signatures = {}
        self.actual_groups = Counter()
        self.physical_rows = 0
        self.stored_materials = set()

    def add_input(self, payload, position):
        row = normalized(adapt_ocsf(payload, profile=self.profile, position=position).row)
        key = row["event_id"]
        signature = identity(row)
        if key in self.signatures and self.signatures[key] != signature:
            raise ReplayCheckError("input_identity_collision")
        self.messages += 1
        self.input_groups[bucket(row)] += 1
        self.signatures[key] = signature
        self.materials.setdefault(key, set()).add((material_digest(row), location(row)))
        if row["source_event_id"]:
            self.source_versions.setdefault(row["source_event_id"], set()).add(row["source_version"])

    def add_saved(self, row):
        row = normalized(row)
        key = row["event_id"]
        if key not in self.signatures or identity(row) != self.signatures[key]:
            raise ReplayCheckError("saved_identity_or_projection_mismatch")
        # Actual persisted material, not an echoed input-side hash or receipt.
        material = material_digest(row)
        if (material, location(row)) not in self.materials[key]:
            raise ReplayCheckError("saved_material_or_position_mismatch")
        if row["ocsf_json"]:
            payload = row["ocsf_json"].encode("utf-8")
        elif row["parse_status"] == "tombstone":
            payload = None
        elif row["parse_status"] == "invalid_utf8":
            payload = base64.b64decode(row["raw_payload"], validate=True)
        else:
            payload = row["raw_payload"].encode("utf-8")
        rebuilt = normalized(adapt_ocsf(payload, profile=self.profile,
                            position=KafkaPosition(*location(row))).row)
        if identity(rebuilt) != identity(row) or material_digest(rebuilt) != material:
            raise ReplayCheckError("saved_content_recomputation_mismatch")
        if key not in self.actual_signatures:
            self.actual_groups[bucket(row)] += 1
        self.actual_signatures[key] = identity(row)
        self.stored_materials.add((key, material))
        self.physical_rows += 1

    def report(self, *, require_complete=False):
        expected_groups = Counter(json_text([s[3], s[10], s[11]]) for s in self.signatures.values())
        expected_digest = logical_digest(self.signatures)
        actual_digest = logical_digest(self.actual_signatures)
        complete = (bool(self.messages) and self.signatures == self.actual_signatures
                    and expected_groups == self.actual_groups and expected_digest == actual_digest)
        if require_complete and not complete:
            raise ReplayCheckError("aggregate_mismatch_or_empty_input")
        return {"messages": self.messages, "logical_versions": len(self.signatures),
                "duplicate_deliveries": self.messages - len(self.signatures),
                "updated_source_records": sum(len(v) > 1 for v in self.source_versions.values()),
                "additional_source_versions": sum(len(v) - 1 for v in self.source_versions.values()),
                "input_material_variants": sum(len({digest for digest, _ in variants}) for variants in self.materials.values()),
                "stored_material_variants": len(self.stored_materials), "physical_rows": self.physical_rows,
                "saved_logical_versions": len(self.actual_signatures), "input_message_groups": dict(self.input_groups),
                "expected_logical_groups": dict(expected_groups), "saved_logical_groups": dict(self.actual_groups),
                "expected_logical_digest": expected_digest, "saved_logical_digest": actual_digest,
                "complete": complete}


def read_saved(client, database, aggregate, limits):
    expressions = [f"toUnixTimestamp64Milli({name}) AS {name}" if name in {"event_time", "kafka_timestamp"}
                   else name for name in READ_COLUMNS]
    # The explicitly selected database must be empty at entry and exclusive to
    # this batch. Read ALL rows, so extra/unexpected versions cannot be hidden
    # behind an input-identity filter.
    for values in client.execute_iter(f"SELECT {', '.join(expressions)} FROM {database}.raw_events",
            settings={"max_block_size": limits.readback_block_size, "max_execution_time": limits.query_timeout_seconds}):
        aggregate.add_saved(dict(zip(READ_COLUMNS, values, strict=True)))
    return aggregate.report(require_complete=True)


async def consume_frozen(consumer, worker, aggregate, limits, ranges, progress):
    """Only [start,end); a later fetched record is never saved or committed."""
    pending = {tp for tp, (start, end) in ranges.items() if start < end}
    last_saved = {tp: None for tp in ranges}
    while pending:
        remaining = limits.max_messages - aggregate.messages
        if remaining <= 0:
            raise ReplayCheckError("message_limit_before_range_end")
        batches = await consumer.getmany(*sorted(pending, key=lambda tp: (tp.topic, tp.partition)),
                                        timeout_ms=worker.profile.max_wait_ms,
                                        max_records=min(worker.profile.batch_size, remaining))
        selected = {}
        for tp, records in batches.items():
            if tp not in pending:
                raise ReplayCheckError("unexpected_partition")
            start, end = ranges[tp]
            selected[tp] = [r for r in records if start <= r.offset < end]
            for record in selected[tp]:
                aggregate.add_input(record.value, KafkaPosition(record.topic, record.partition, record.offset,
                                    record.timestamp if record.timestamp is not None and record.timestamp >= 0 else None))
                progress[str(tp.partition)]["messages"] += 1
        worker.pending = {tp: records for tp, records in selected.items() if records}
        try:
            await worker.process_pending()
        finally:
            # A later partition failure must not erase an earlier partition's
            # completed save/commit from the partial report.
            for tp, records in selected.items():
                if records and tp not in worker.pending:
                    last_saved[tp] = records[-1].offset + 1
                    part = progress[str(tp.partition)]
                    part["confirmed_next_offset"] = last_saved[tp]
                    part["confirmed_messages"] = part.get("confirmed_messages", 0) + len(records)
        for tp in list(pending):
            position = min(await consumer.position(tp), ranges[tp][1])
            progress[str(tp.partition)]["scanned_next_offset"] = position
            if position >= ranges[tp][1]:
                pending.remove(tp)
    return last_saved


async def run_replay(writer: LakeWriter, consumer_profile: LakeConsumerProfile, limits: ReplayLimits, directory: Path):
    ingress = writer.ingress_profile
    if ingress is None or ingress.topics != (limits.topic,) or not consumer_profile.enabled:
        raise ValueError("explicit single-topic enabled replay profile required")
    if not ingress.database.startswith("lyc_lake_3e_") or not consumer_profile.group_id.startswith("lyc-"):
        raise ValueError("isolated replay database and group required")
    if not ingress.source_namespace.startswith("lyc") or not ingress.connector_type.startswith("lyc"):
        raise ValueError("neutral test source required")
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    private_json(directory / "started.json", {"state": "started"})
    aggregate = ReplayAggregate(ingress)
    worker = LakeConsumer(writer, consumer_profile)
    consumer = None
    report = {"status": "incomplete", "phase": "preflight", "ranges": {}, "progress": {}}
    try:
        async with asyncio.timeout(limits.max_duration_seconds):
            await writer.start()
            await writer.check_ingress_ready()
            count = await _settled_thread(writer._client.execute, f"SELECT count() FROM {ingress.database}.raw_events")
            if count[0][0] != 0:
                raise ReplayCheckError("replay_database_not_empty")
            security = kafka_client_kwargs()
            admin = AIOKafkaAdminClient(bootstrap_servers=consumer_profile.bootstrap_servers,
                                       request_timeout_ms=consumer_profile.request_timeout_ms, **security)
            try:
                await admin.start()
                metadata = await admin.describe_topics()  # All names: cannot auto-create a requested topic.
            finally:
                await admin.close()
            rows = [row for row in metadata if row["topic"] == limits.topic and row["error_code"] == 0]
            if len(rows) != 1 or not rows[0]["partitions"] or any(p["error_code"] for p in rows[0]["partitions"]):
                raise ReplayCheckError("configured_topic_unavailable")
            tps = [TopicPartition(limits.topic, p["partition"]) for p in rows[0]["partitions"]]
            consumer = AIOKafkaConsumer(bootstrap_servers=consumer_profile.bootstrap_servers,
                group_id=consumer_profile.group_id, enable_auto_commit=False, auto_offset_reset="none", value_deserializer=None,
                request_timeout_ms=consumer_profile.request_timeout_ms, max_poll_interval_ms=consumer_profile.max_poll_interval_ms,
                max_partition_fetch_bytes=consumer_profile.max_partition_fetch_bytes, fetch_max_bytes=consumer_profile.fetch_max_bytes,
                **security)
            await consumer.start()
            for tp in tps:
                if await consumer.committed(tp) is not None:
                    raise ReplayCheckError("replay_group_already_used")
            starts, ends = await consumer.beginning_offsets(tps), await consumer.end_offsets(tps)
            ranges = {tp: (starts[tp], ends[tp]) for tp in tps}
            report["ranges"] = {str(tp.partition): {"topic": tp.topic, "start": starts[tp], "end_exclusive": ends[tp]} for tp in tps}
            private_json(directory / "frozen-ranges.json", report["ranges"])
            consumer.assign(tps)
            for tp in tps:
                consumer.seek(tp, starts[tp])
            worker._consumer = consumer
            report["progress"] = {str(tp.partition): {"messages": 0, "scanned_next_offset": starts[tp], "confirmed_next_offset": None} for tp in tps}
            report["phase"] = "consume_and_save"
            last_saved = await consume_frozen(consumer, worker, aggregate, limits, ranges, report["progress"])
            report["phase"] = "broker_readback"
            latest_starts = await consumer.beginning_offsets(tps)
            for tp in tps:
                committed = await consumer.committed(tp)
                report["progress"][str(tp.partition)]["broker_committed"] = committed
                if latest_starts[tp] > starts[tp] or committed != last_saved[tp]:
                    raise ReplayCheckError("range_expired_or_commit_mismatch")
            report["phase"] = "lake_readback"
            report["aggregate"] = await _settled_thread(read_saved, writer._client, ingress.database, aggregate, limits)
            report["status"] = "passed"
            report["phase"] = "complete"
    except Exception as exc:  # noqa: BLE001 - private values never enter public exception text
        report["error_type"] = type(exc).__name__
        report["persistence_outcome"] = getattr(exc, "outcome", None)
        report["storage_cause_type"] = getattr(exc, "cause_type", None)
        if isinstance(exc, ReplayCheckError):
            report["invariant"] = str(exc)
    finally:
        report.setdefault("aggregate", aggregate.report())
        report["held"] = worker.status()
        if consumer is not None:
            try:
                await consumer.stop()
            except Exception as exc:  # noqa: BLE001 - close failure is incomplete
                report["status"] = "incomplete"
                report["close_error_type"] = type(exc).__name__
        await writer.stop()
        private_json(directory / "report.json", report)
    return report["status"] == "passed"
