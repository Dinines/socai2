"""
Kafka consumer worker: reads raw alerts (and, since Phase 3.1, ingest's
normalized OCSF events), runs them through the fusion engine, publishes fused
results back to Kafka, and persists non-duplicate alerts to Postgres.
"""

import asyncio
import contextlib
import json
import time
from typing import Any

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.structs import TopicPartition

from app.core.config import settings
from app.core.kafka_security import kafka_client_kwargs
from app.models.alert import FusedAlert, FusionDecision, RawAlert
from app.services.ai_asset_recorder import AiAssetRecorder
from app.services.alert_sink import AlertSink, PersistOutcome
from app.services.detection_engine import DetectionEngine
from app.services.delivery_recovery import DeliveryHold, DeliveryRecovery, make_snapshot, restore_snapshot
from app.services.dlq import DeadLetter, DeadLetterQueue, LoggingDLQ, safe_record
from app.services.event_schema import validate_event
from app.services.fusion_engine import FusionEngine
from app.services.lake_writer import LakeWriter
from app.services.promoter import promote_normalized_event
from app.services.scale_hint import compute as compute_scale_hint
from app.services.sessions import DERIVED_IDLE_SECONDS, SessionRef, SessionStore
from app.services.tenant_overlay import OverlayCache
from app.services.ueba_signal import UebaSignalCache
from app.services.windowed_detection import WindowedDetectionEngine

logger = structlog.get_logger()

_METRICS = {
    "processed": 0,
    "duplicates": 0,
    "correlated": 0,
    "new_incidents": 0,
    "promoted": 0,
    "not_promoted": 0,
    "persisted": 0,
    "persist_unavailable": 0,
    "persist_failed": 0,
    "laked": 0,
    # Events recorded against a session (depth plan 2.4). Counted separately
    # from `laked` so a deployment can see that the session store is working
    # rather than inferring it from alerts that happen to carry an id.
    "sessions": 0,
    "detected": 0,
    "dead_lettered": 0,
    "errors": 0,
    "ai_assets_observed": 0,
}


#: How often the worker sweeps for derived sessions that have gone quiet.
#: A quarter of the idle window, so a session is closed within roughly
#: DERIVED_IDLE_SECONDS of its last event rather than up to twice that.
SESSION_SWEEP_SECONDS = DERIVED_IDLE_SECONDS / 4


class FusionWorker:
    """Kafka consumer/producer pair that drives the fusion pipeline."""

    def __init__(
        self,
        engine: FusionEngine,
        sink: AlertSink | None = None,
        dlq: DeadLetterQueue | None = None,
        lake: LakeWriter | None = None,
        detector: DetectionEngine | None = None,
        windowed_detector: WindowedDetectionEngine | None = None,
        first_seen: Any | None = None,
        baselines: Any | None = None,
        ueba_cache: UebaSignalCache | None = None,
        overlays: OverlayCache | None = None,
        sessions: SessionStore | None = None,
        ai_assets: AiAssetRecorder | None = None,
    ) -> None:
        self._engine = engine
        self._sink = sink
        self._lake = lake
        self._detector = detector
        self._windowed = windowed_detector
        self._first_seen = first_seen
        #: Depth plan 3.4 behavioural baselines, computed in CORE.
        self._baselines = baselines
        self._ueba_cache = ueba_cache
        #: Depth 6.1 — the observed AI estate. Optional in the same sense the
        #: lake writer is: a deployment that passes nothing behaves exactly
        #: as before, and `main.py` passes one on every profile.
        self._ai_assets = ai_assets
        #: Per-tenant detection tuning (parity 5.4). Optional, so a
        #: deployment that passes nothing behaves exactly as before.
        self._overlays = overlays
        #: Depth plan 2.4. Optional so a deployment without the migration
        #: behaves exactly as before: alerts carry no session context
        #: rather than carrying an invented one.
        self._sessions = sessions
        # A poison message must never vanish silently; default to a structured
        # logging DLQ so persistence-free deployments still get the signal.
        self._dlq: DeadLetterQueue = dlq or LoggingDLQ()
        self._consumer: AIOKafkaConsumer | None = None
        self._producer: AIOKafkaProducer | None = None
        self._running = False
        self._attached = False
        self._flush_task: asyncio.Task | None = None

    @property
    def engine(self) -> FusionEngine:
        return self._engine

    @property
    def attached(self) -> bool:
        """Whether the consume loop is currently iterating the subscription.

        ``_running`` is a request ("keep going"); this is an observation ("it
        is going"). Readiness needs the second one: the worker was started as
        a fire-and-forget task and ``/readyz`` latched to 200 next to it, so a
        loop that exited left the service reporting ready forever.
        """
        return self._attached

    async def start(self) -> None:
        topics = [settings.kafka_topic_alerts_raw]
        # Subscribe to raw_events when EITHER promotion or lake archival needs
        # it — the lake must fill even if promotion is turned off.
        if settings.event_promotion_enabled or self._lake is not None or self._detector is not None or self._windowed is not None:
            topics.append(settings.kafka_topic_raw_events)
        # Phase A4 — also consume the UEBA behavioral-anomaly stream so the
        # per-entity signal cache stays warm for fuse-time boosting.
        if self._ueba_cache is not None:
            topics.append(settings.kafka_topic_ueba_anomalies)
        self._consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_consumer_group,
            auto_offset_reset="latest",
            # At-least-once: commit offsets only AFTER a message is fully
            # processed (see _consume_loop), not on a background timer that could
            # commit an in-flight message before processing finishes.
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            **kafka_client_kwargs(),
        )
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            **kafka_client_kwargs(),
        )
        await self._consumer.start()
        await self._producer.start()
        if self._sink is not None:
            await self._sink.start()
        if self._lake is not None or self._sessions is not None:
            if self._lake is not None:
                await self._lake.start()
            # Low-traffic safety net: a single buffered event would otherwise
            # wait for the NEXT message before flush_if_stale runs. A background
            # ticker guarantees the lake batch flushes by age even when idle.
            #
            # The same ticker closes idle derived sessions. A derived session
            # ends when the activity stops, so nothing on the event path can
            # ever close one -- the closing condition is the *absence* of an
            # event. Without a ticker every derived session would stay open
            # forever and "what else did this sitting do" would accumulate
            # months of unrelated activity under one id.
            self._flush_task = asyncio.create_task(self._periodic_flush())
        self._running = True
        logger.info(
            "Fusion worker started",
            consumer_group=settings.kafka_consumer_group,
            input_topics=topics,
            output_topic=settings.kafka_topic_alerts_fused,
            alert_sink=self._sink is not None,
            lake_writer=self._lake is not None,
        )
        await self._consume_loop()

    async def _periodic_flush(self) -> None:
        interval = max(0.5, settings.lake_batch_max_age_seconds)
        # Elapsed wall-clock rather than a tick count, because the two
        # cadences are set independently: a tick count derived from the
        # lake's flush interval silently changes the sweep period whenever
        # someone tunes the lake, which is a coupling nobody would expect
        # from either setting's name.
        last_sweep = time.monotonic()
        try:
            while self._running:
                await asyncio.sleep(interval)
                if self._lake is not None:
                    await self._lake.flush_if_stale()
                if self._ai_assets is not None:
                    await self._ai_assets.flush_if_stale()
                if self._sessions is None:
                    continue
                now = time.monotonic()
                if now - last_sweep < SESSION_SWEEP_SECONDS:
                    continue
                last_sweep = now
                closed = await self._sessions.close_idle()
                if closed:
                    logger.info("Closed idle derived sessions", closed=closed)
        except asyncio.CancelledError:  # pragma: no cover — shutdown path
            pass

    async def stop(self) -> None:
        self._running = False
        if self._flush_task is not None:
            self._flush_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                _ = await self._flush_task  # await the cancellation to settle
            self._flush_task = None
        if self._consumer:
            await self._consumer.stop()
        if self._producer:
            await self._producer.stop()
        if self._sink is not None:
            await self._sink.stop()
        if self._lake is not None:
            await self._lake.stop()
        # Flush the inventory buffer on the way out, so a clean shutdown does
        # not discard up to 30 seconds of sightings.
        if self._ai_assets is not None:
            await self._ai_assets.flush()
        logger.info("Fusion worker stopped", metrics=_METRICS)

    async def _consume_loop(self) -> None:
        # `start()` is the only caller and assigns `_consumer` before getting
        # here. Bound locally so that invariant is stated where it is relied
        # on: iterating or committing a None consumer would otherwise be an
        # AttributeError inside the message loop, reported as a processing
        # failure rather than as the startup bug it is.
        consumer = self._consumer
        if consumer is None:  # pragma: no cover — unreachable via start()
            raise RuntimeError("fusion consume loop started before the Kafka consumer")
        # Attached for as long as this loop is iterating; read by the
        # readiness probe app/main.py registers. Cleared in the ``finally`` so
        # every exit path reports the same way, including one that raises.
        self._attached = True
        try:
            async for msg in consumer:
                if not self._running:
                    break
                try:
                    await self._process_message(msg.value, topic=msg.topic, partition=msg.partition, offset=msg.offset)
                except Exception as exc:
                    _METRICS["errors"] += 1
                    logger.error("Failed to process message", error=str(exc), exc_info=True)
                    # No later success may commit past this failed input.
                    # Exiting also clears attached/readiness; recovery needs
                    # an explicit restart, rather than a tight failure loop.
                    raise
                else:
                    # At-least-once: commit only after the message is handled
                    # (validated + laked + promoted, or dead-lettered). A crash
                    # before this line re-delivers the in-flight message on restart
                    # instead of losing it. Commit failure => reprocess on restart.
                    try:
                        await consumer.commit({TopicPartition(msg.topic, msg.partition): msg.offset + 1})
                    except Exception as commit_exc:  # noqa: BLE001
                        logger.warning("fusion.commit_failed", error=str(commit_exc))
                        raise
                # Flush any stale lake batch so archival isn't stranded during a
                # low-traffic window (batch fills by size OR age).
                #
                # Guarded, because this await sat outside the per-message
                # try/except: a ClickHouse outage raising here left the
                # ``async for`` entirely and stopped fusion consuming, with the
                # archive fault reported as nothing at all. Archival falling
                # behind must not cost the alert path.
                if self._lake is not None:
                    try:
                        await self._lake.flush_if_stale()
                    except Exception as flush_exc:  # noqa: BLE001 — the lake is not the alert path
                        _METRICS["errors"] += 1
                        logger.error("fusion.lake_flush_failed", error=str(flush_exc), exc_info=True)
        finally:
            self._attached = False

    async def _dead_letter(
        self,
        *,
        topic: str,
        payload,
        reason: str,
        schema_version: str = "v1",
        source_event_id: str | None = None,
        tenant_id: str | None = None,
        partition: int | None = None,
        offset: int | None = None,
    ) -> None:
        """Route a poison message to the DLQ instead of dropping it silently.

        ``partition`` and ``offset`` are carried through because the excerpt
        stored alongside them is a triage record, not the event: replaying a
        refused message means re-reading it from Kafka, and these are the only
        way back to it (deferral 5b).
        """
        if isinstance(self._dlq, LoggingDLQ):
            raise DeliveryHold("fusion live poison input has no durable DLQ")
        confirmed = await safe_record(
            self._dlq,
            DeadLetter.build(
                topic=topic,
                reason=reason,
                schema_version=schema_version,
                payload=payload,
                source_event_id=source_event_id,
                tenant_id=tenant_id,
                partition=partition,
                offset=offset,
            ),
        )
        if not confirmed:
            raise DeliveryHold("fusion dead-letter persistence was not confirmed")
        _METRICS["dead_lettered"] += 1

    async def _process_message(
        self, payload: dict, topic: str | None = None, partition: int | None = None, offset: int | None = None
    ) -> None:
        resolved_topic = topic or settings.kafka_topic_alerts_raw

        # Phase A4 — UEBA anomaly stream: warm the per-entity signal cache and
        # return (these are behavioral signals, not alerts).
        if self._ueba_cache is not None and topic == settings.kafka_topic_ueba_anomalies:
            await self._ueba_cache.record(payload)
            return

        # Phase 5 — schema-validate the envelope BEFORE the promoter sees it.
        # A malformed / mis-versioned / mis-tenanted message is dead-lettered
        # (captured with its reason + lineage), never silently dropped.
        validation = validate_event(
            resolved_topic,
            payload,
            raw_events_topic=settings.kafka_topic_raw_events,
            alerts_raw_topic=settings.kafka_topic_alerts_raw,
        )
        if not validation.ok:
            await self._dead_letter(
                topic=resolved_topic,
                payload=payload,
                reason=validation.reason,
                schema_version=validation.schema_version,
                source_event_id=validation.source_event_id,
                tenant_id=validation.tenant_id,
                partition=partition,
                offset=offset,
            )
            return

        # Declared ahead of the branch because the tail call below is shared.
        # A vendor-asserted finding on the alerts topic is not a normalized
        # event and has no session: None reaches the sink, which renders no
        # session context rather than attaching the previous event's.
        session: SessionRef | None = None

        if topic == settings.kafka_topic_raw_events:
            # Depth plan 2.4 — record the session this event belongs to before
            # anything else reads the event, so the lake row, the alert and the
            # graph node all carry the same session id. `session.go` derived
            # the key; this is the stateful half that counts the events and
            # walks the assumed-role chain. It returns None, not an error, for
            # an event whose source names no session — and that stays None all
            # the way to the console rather than becoming a session of one.
            if self._sessions is not None and validation.tenant_id:
                session = await self._sessions.record_event(str(validation.tenant_id), payload)
                if session is not None:
                    _METRICS["sessions"] += 1
                    # Stamped onto the event so the lake row carries the same
                    # id as the Postgres row and the graph node, which is what
                    # lets a hunt join the three without any of them having
                    # agreed on anything at write time.
                    payload["activity"]["session"]["id"] = str(session.id)

            # Phase A1 — archive EVERY normalized event into the ClickHouse lake
            # first, independent of the promotion decision below. A non-promoted
            # Medium event still has to be queryable via /lake/sql.
            if self._lake is not None and await self._lake.write_event(payload):
                _METRICS["laked"] += 1

            # Depth 6.1 — the observed AI estate is built here rather than by
            # a separate worker reading the lake, for one reason: this is the
            # branch every normalized event already travels on the default
            # profile. A reader of the lake would be a second service CORE
            # does not start, and the inventory page would be empty on the
            # deployment most likely to have an ungoverned AI estate.
            if self._ai_assets is not None:
                _METRICS["ai_assets_observed"] += await self._ai_assets.observe(payload)

            # Resolved once and shared by both engines. Parity 5.4: without
            # the overlay the stateless engine evaluated the shared corpus and
            # nothing else, so a tenant who disabled a noisy rule in the
            # console kept receiving its alerts while the console showed it
            # disabled. The windowed engine reads it for the same reason and
            # for its allowlist booleans.
            overlay = None
            if self._overlays is not None and validation.tenant_id and (self._detector is not None or self._windowed is not None):
                overlay = await self._overlays.get(str(validation.tenant_id))

            # Phase A2 — run the executable detection corpus against the live
            # event. Each firing rule becomes a RawAlert routed through fusion,
            # so telemetry that isn't a vendor-asserted finding still alerts.
            #
            # One event firing N rules produces N alert rows, deliberately
            # (issue #1244 reported one Sysmon event becoming five or six).
            # Each row names the rule that fired, carries that rule's severity
            # and category, and is dispositioned on its own: collapsing them
            # would mean picking one rule's verdict to stand for the others,
            # and an analyst who closes "suspicious PowerShell" has not
            # thereby closed "LSASS access". `Correlator.correlate` already
            # groups them into one incident on
            # {tenant}:{entity}:{tactic} for the console, which is where the
            # N-into-1 view belongs.
            if self._detector is not None:
                for hit in await self._detector.evaluate_async(payload, overlay, self._first_seen, self._baselines):
                    det_alert = self._detector.build_alert(payload, hit)
                    if det_alert is not None:
                        _METRICS["detected"] += 1
                        await self.process_alert(det_alert, source_event_id=validation.source_event_id, session=session)

            # Wave 2 — stateful/windowed detections (brute force, spray, scans)
            # count this event into its sliding window and fire once on threshold.
            if self._windowed is not None:
                for hit in await self._windowed.evaluate(payload, overlay):
                    win_alert = self._windowed.build_alert(payload, hit)
                    if win_alert is not None:
                        _METRICS["detected"] += 1
                        await self.process_alert(win_alert, source_event_id=validation.source_event_id, session=session)

            # Ingest-normalized OCSF event — run the deterministic promotion
            # policy (see app/services/promoter.py). Non-promoted events are
            # dropped here by design; the detect stage (above) owns rule eval.
            alert = promote_normalized_event(payload)
            if alert is None:
                _METRICS["not_promoted"] += 1
                return
            _METRICS["promoted"] += 1
        else:
            try:
                alert = RawAlert.model_validate(payload)
            except Exception as exc:
                # Deep validation failure — dead-letter it (the schema layer
                # only caught gross shape); never silently drop.
                await self._dead_letter(
                    topic=resolved_topic,
                    payload=payload,
                    reason=f"RawAlert validation failed: {exc}",
                    schema_version=validation.schema_version,
                    source_event_id=validation.source_event_id,
                    tenant_id=validation.tenant_id,
                    partition=partition,
                    offset=offset,
                )
                return

        await self.process_alert(alert, source_event_id=validation.source_event_id, session=session)

    async def process_alert(
        self, alert: RawAlert, *, source_event_id: str | None = None, session: SessionRef | None = None,
    ) -> FusedAlert:
        """The shared HTTP/Kafka alert path, including confirmed delivery.

        Callers receive the durable first result only after the fused message
        is acknowledged. Kafka owns its offset commit separately; HTTP must
        authenticate the tenant before invoking this state-changing method.
        """
        return await self._fuse_and_persist(alert, source_event_id=source_event_id, session=session)

    async def _fuse_and_persist(
        self, alert: RawAlert, *, source_event_id: str | None = None, session: SessionRef | None = None,
    ) -> FusedAlert:
        """Run one RawAlert through fusion, persist it, then publish it.

        Issue #568: the canonical, replay-stable alert id and source-event
        provenance are stamped on the RawAlert *before* fusion, so ``FusedAlert.id``
        (derived from ``alert.id``) matches the persisted ``alerts.id`` row.
        Persist runs *before* publish so the published envelope carries the
        durable row id + a truthful persistence outcome downstream can trust.
        """
        # Stamp source-event provenance + canonical id (issue #568).
        if source_event_id and source_event_id not in alert.source_event_ids:
            alert.source_event_ids.append(source_event_id)
        alert.id = alert.deterministic_id()

        if self._sink is None:
            raise DeliveryHold("fusion live alert has no PostgreSQL sink")

        fresh_result = True
        recovery = None
        # PG is authoritative even when Redis has expired or contains a
        # different candidate. Never reconstruct an old row from current
        # raw/enrichment data and call it the first result.
        previous = await self._sink.lookup_delivery(alert)
        if previous.exists:
            if previous.snapshot is None:
                raise DeliveryHold("fusion existing row has no provable first-result snapshot")
            fused = restore_snapshot(previous.snapshot, alert)
            fresh_result = False
        else:
            dedup = getattr(self._engine, "_dedup", None)
            redis = getattr(dedup, "_redis", None)
            if redis is None:
                raise DeliveryHold("fusion alert has no first-result recovery cache")
            recovery = DeliveryRecovery(redis, settings.dedup_window_seconds)
            fused = await recovery.load(alert)
            if fused is None:
                duplicate, _ = await dedup.is_duplicate(alert)
                if duplicate:
                    # The old engine registers before correlation. A
                    # crash in that gap has no completed result to reuse.
                    raise DeliveryHold("fusion dedup hit has no provable first-result snapshot")
                fused = await self._engine.process(alert)
            else:
                fresh_result = False
        _METRICS["processed"] += 1

        # Depth plan 2.4. Attached after fusion rather than before, because
        # fusion builds the FusedAlert and anything set on the RawAlert first
        # would have to survive that construction — which is the kind of
        # assumption that holds until someone adds a field.
        if fresh_result and session is not None:
            fused.session_id = session.id
            fused.session_key_kind = session.key_kind
            fused.originating_human = session.originating_human

        if recovery is not None:
            # Store the full result before PG insertion. The finite TTL and
            # NX policy preserve exact evidence for a warm missing-row retry.
            fused = await recovery.remember(fused)

        if fused.fusion_decision == FusionDecision.DUPLICATE:
            _METRICS["duplicates"] += 1
        elif fused.fusion_decision == FusionDecision.CORRELATED:
            _METRICS["correlated"] += 1
        else:
            _METRICS["new_incidents"] += 1

        result = await self._sink.persist(fused, replay=alert, delivery_snapshot=make_snapshot(fused))
        if result.outcome is PersistOutcome.INSERTED:
            _METRICS["persisted"] += 1
        elif result.outcome is PersistOutcome.UNAVAILABLE:
            _METRICS["persist_unavailable"] += 1
        elif result.outcome is PersistOutcome.FAILED:
            _METRICS["persist_failed"] += 1
        if not result.durable:
            raise DeliveryHold("fusion alert persistence was not confirmed")
        confirmed = await self._sink.lookup_delivery(alert)
        if not confirmed.exists:
            # In particular, legacy DUPLICATE is a dedup decision, not proof
            # of a PG row: the upstream sink can return it while disconnected.
            raise DeliveryHold("fusion dedup result has no confirmed PostgreSQL row")
        if confirmed.snapshot is None:
            raise DeliveryHold("fusion PostgreSQL row has no provable first-result snapshot")
        fused = restore_snapshot(confirmed.snapshot, alert)

        # Publish fused alert (even duplicates, so downstream can track),
        # carrying the durable row id + persistence outcome (issue #568).
        envelope = fused.model_dump(mode="json")
        envelope["alert_row_id"] = confirmed.alert_id
        envelope["persist_outcome"] = result.outcome.value
        producer = self._producer
        if producer is None:  # pragma: no cover — assigned by start()
            raise RuntimeError("fusion produced a fused alert before the Kafka producer started")
        await producer.send_and_wait(
            settings.kafka_topic_alerts_fused,
            value=envelope,
        )
        return fused

    @staticmethod
    def get_metrics() -> dict:
        return dict(_METRICS)

    async def consumer_lag(self) -> int | None:
        """Total backlog across the partitions this replica is assigned.

        ``None`` when it cannot be read — no consumer, no assignment yet,
        or a broker that did not answer. Deliberately not zero: an
        unreadable backlog reported as no backlog is how a stalled
        consumer looks healthy, which is the defect this service has
        shipped before.
        """
        consumer = self._consumer
        if consumer is None:
            return None
        try:
            assignment = consumer.assignment()
            if not assignment:
                return None
            total = 0
            for partition in assignment:
                end = await consumer.position(partition)
                highwater = consumer.highwater(partition)
                if end is None or highwater is None:
                    return None
                total += max(0, highwater - end)
            return total
        except Exception as exc:  # noqa: BLE001 — a lag read must never stop the consumer
            logger.warning("fusion.lag_unreadable", error=str(exc))
            return None

    async def scale_hint(self) -> dict:
        """The autoscaling signal, for an operator's HPA or KEDA scaler.

        AiSOC publishes this and does not act on it; ADR-0012 records
        why. The per-replica budget is derived from the published
        realistic-mix run rather than chosen, so the number relates to a
        measurement someone can go and check.
        """
        return compute_scale_hint(await self.consumer_lag()).as_dict()
