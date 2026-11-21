"""Bare OCSF consumer: actual save receipts precede explicit partition commits.

One partition batch is in flight. Any unresolved save/commit stops this inlet;
there is no automatic retry, skip, DLQ acknowledgement or promotion here.
"""

from __future__ import annotations

import asyncio
import json
import logging
from app.core.operational_logging import log_exception
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from aiokafka import AIOKafkaConsumer, ConsumerRebalanceListener

from app.core.kafka_security import kafka_client_kwargs
from app.services.lake_ingress import KafkaPosition
from app.services.lake_writer import LakePersistenceError, LakeWriter


@dataclass(frozen=True)
class LakeConsumerProfile:
    enabled: bool
    bootstrap_servers: list[str]
    group_id: str
    initial_offset: str
    batch_size: int
    max_wait_ms: int
    request_timeout_ms: int
    max_poll_interval_ms: int
    max_partition_fetch_bytes: int
    fetch_max_bytes: int

    def __post_init__(self):
        if type(self.enabled) is not bool or not isinstance(self.group_id, str) or not self.group_id.strip():
            raise ValueError("explicit lake enabled/group required")
        if not isinstance(self.bootstrap_servers, list) or not self.bootstrap_servers or any(
            not isinstance(item, str) or not item.strip() for item in self.bootstrap_servers
        ):
            raise ValueError("explicit lake brokers required")
        if self.initial_offset not in {"earliest", "require_committed"}:
            raise ValueError("unsupported lake initial offset policy")
        for name in ("batch_size", "max_wait_ms", "request_timeout_ms", "max_poll_interval_ms",
                     "max_partition_fetch_bytes", "fetch_max_bytes"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"invalid lake consumer {name}")
        if self.max_wait_ms >= self.max_poll_interval_ms or self.max_partition_fetch_bytes > self.fetch_max_bytes:
            raise ValueError("inconsistent lake poll/fetch limits")

    @classmethod
    def load(cls, path: str | Path) -> LakeConsumerProfile:
        body = json.loads(Path(path).read_text())
        if set(body) != set(cls.__dataclass_fields__):
            raise ValueError("incomplete/unsupported lake consumer profile")
        return cls(**body)


class LakeConsumeHold(RuntimeError):
    """Safe status only; exception text must not carry received records."""


class _Ownership(ConsumerRebalanceListener):
    def __init__(self, worker: LakeConsumer):
        self.worker = worker

    async def on_partitions_revoked(self, revoked):
        if revoked:
            # Never flush or commit from a rebalance callback. Native I/O may
            # still be running; the processing path settles it before exit.
            self.worker._revoked = True
            self.worker._attached = False

    async def on_partitions_assigned(self, assigned):
        worker = self.worker
        if worker._revoked:
            return
        try:
            for tp in assigned:
                if await worker._consumer.committed(tp) is None:
                    if worker.profile.initial_offset != "earliest":
                        raise LakeConsumeHold("initial_offset_missing")
                    # Explicit first start only. Out-of-range existing offsets
                    # use auto_offset_reset=none and fail, never silently reset.
                    if not await worker._consumer.seek_to_beginning(tp):
                        raise LakeConsumeHold("initial_offset_unconfirmed")
        except Exception:  # noqa: BLE001 - coordinator callback cannot acknowledge missing offsets
            worker._assignment_failed = True
            log_exception(logging.getLogger(__name__), "lake_assignment_failed", extra={
                "operation": "assign_partition", "stage": "assignment", "dependency": "kafka",
                "error_code": "assignment_failed"})
        finally:
            worker._assignment_ready.set()


class LakeConsumer:
    def __init__(self, lake: LakeWriter, profile: LakeConsumerProfile):
        if lake.ingress_profile is None:
            raise ValueError("lake consumer requires an ingress profile")
        self.lake = lake
        self.profile = profile
        self._consumer = None
        self._attached = False
        self._revoked = False
        self._assignment_failed = False
        self._assignment_ready = asyncio.Event()
        self.pending = {}
        self.failure: dict | None = None
        self.readback: tuple[str, ...] = ()
        self.phase = "not_started"

    @property
    def attached(self):
        return self._attached and not self._revoked and not self._assignment_failed and self.failure is None

    def _check_ownership(self):
        if self._revoked or self._assignment_failed:
            raise LakeConsumeHold("partition_revoked" if self._revoked else "assignment_failed")

    async def run(self):
        if not self.profile.enabled:
            raise ValueError("disabled lake consumer must not be started")
        try:
            self.phase = "preflight"
            await self.lake.check_ingress_ready()
            self._consumer = AIOKafkaConsumer(
                bootstrap_servers=self.profile.bootstrap_servers,
                group_id=self.profile.group_id,
                enable_auto_commit=False,
                auto_offset_reset="none",
                value_deserializer=None,
                request_timeout_ms=self.profile.request_timeout_ms,
                max_poll_interval_ms=self.profile.max_poll_interval_ms,
                max_partition_fetch_bytes=self.profile.max_partition_fetch_bytes,
                fetch_max_bytes=self.profile.fetch_max_bytes,
                **kafka_client_kwargs(),
            )
            self._consumer.subscribe(topics=self.lake.ingress_profile.topics, listener=_Ownership(self))
            await self._consumer.start()
            # start() can return as soon as assignment exists, before its
            # asynchronous listener has set every initial fetch position.
            self.phase = "assignment"
            await asyncio.wait_for(self._assignment_ready.wait(), self.profile.request_timeout_ms / 1000)
            self._check_ownership()
            self._attached = True
            while True:
                self._check_ownership()
                self.phase = "poll"
                batches = await self._consumer.getmany(
                    timeout_ms=self.profile.max_wait_ms, max_records=self.profile.batch_size)
                # Retain every fetched range, including partitions not reached
                # if an earlier partition fails. Never use global commit().
                self.pending = {tp: messages for tp, messages in batches.items() if messages}
                await self.process_pending()
        except BaseException as exc:
            if not isinstance(exc, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)):
                log_exception(logging.getLogger(__name__), "lake_consume_failed", extra={
                    "operation": "consume_ocsf", "stage": self.phase,
                    "dependency": "clickhouse" if self.phase in {"preflight", "insert", "save_unconfirmed", "receipt_unconfirmed"} else "kafka",
                    "error_code": "lake_consume_unconfirmed"})
            self.failure = {"phase": self.phase, "cause_type": type(exc).__name__,
                            "outcome": getattr(exc, "outcome", "unconfirmed"),
                            "storage_cause_type": getattr(exc, "cause_type", None)}
            raise
        finally:
            self._attached = False
            if self._consumer is not None:
                await self._consumer.stop()

    async def process_pending(self):
        """Process only the fetched order; native offset gaps are not missing rows."""
        self._check_ownership()
        for tp, messages in list(self.pending.items()):
            records = [(msg.value, KafkaPosition(msg.topic, msg.partition, msg.offset,
                        msg.timestamp if msg.timestamp is not None and msg.timestamp >= 0 else None)) for msg in messages]
            if any(pos.topic != tp.topic or pos.partition != tp.partition for _, pos in records) or any(
                a[1].offset >= b[1].offset for a, b in pairwise(records)
            ):
                raise LakeConsumeHold("invalid_partition_order")
            self.phase = "insert"
            try:
                receipts = await self.lake.write_ocsf_batch(records)
            except (LakePersistenceError, asyncio.CancelledError):
                # write_ocsf_batch joins its native thread before propagating
                # cancellation. Readback cannot race that client invocation.
                self.phase = "save_unconfirmed"
                self.readback = await self.lake.inspect_ocsf_batch(records)
                raise
            if len(receipts) != len(records) or any(not receipt.persisted or receipt.position != pos
                                                   for receipt, (_, pos) in zip(receipts, records)):
                self.phase = "receipt_unconfirmed"
                raise LakeConsumeHold("incomplete_persistence_receipts")
            self._check_ownership()
            self.phase = "commit"
            await self._consumer.commit({tp: records[-1][1].offset + 1})
            self._check_ownership()
            del self.pending[tp]

    def status(self):
        """Operational metadata, never bodies, upstream IDs or database results."""
        return {"attached": self.attached, "phase": self.phase, "failure": self.failure,
                "pending": [{"topic": tp.topic, "partition": tp.partition,
                             "first": messages[0].offset, "next": messages[-1].offset + 1,
                             "records": len(messages)} for tp, messages in self.pending.items()],
                "readback": {name: self.readback.count(name) for name in ("present", "not_observed", "unknown")}}
