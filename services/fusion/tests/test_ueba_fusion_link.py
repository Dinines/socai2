"""UEBA messages -> original Fusion processing -> saved/published scores.

Only Redis, PostgreSQL storage and Kafka delivery are memory boundaries, as in
test_process_delivery. The worker, cache, dedup, correlator, ML heuristic and
confidence scorer are real. No service, broker, model or vendor is contacted.
"""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.core.config import settings
from app.models.alert import FusedAlert, RawAlert
from app.services.correlator import Correlator
from app.services.deduplicator import Deduplicator
from app.services.fusion_engine import FusionEngine
from app.services.ueba_signal import UebaSignalCache
from app.workers.consumer import FusionWorker

from .test_process_delivery import MemoryRedis, MemorySink


TENANT = UUID("30a948cc-fb41-420b-bc3d-d4af8e26a001")
OTHER_TENANT = UUID("30a948cc-fb41-420b-bc3d-d4af8e26a002")
USER = "ueba-link-alice"
HOST = "UEBA-LINK-H1"


def _message(risk, *, entity_type="user", entity_id=USER, tenant=TENANT):
    return {
        "anomaly_id": str(UUID(int=7602)),
        "tenant_id": str(tenant),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "event_type": "login",
        "anomaly_score": {"medium": 3.5, "high": 4.7, "critical": 6.2}[risk],
        "risk_level": risk,
        "features": {},
        "peer_group_id": None,
        "peer_deviation_score": None,
        "detected_at": "2026-10-21T08:00:00+00:00",
    }


CASES = [
    ("off_with_cached_critical", False, [_message("critical")], 0.656, 0.15, None),
    ("on_without_signal", True, [], 0.656, 0.15, None),
    ("on_medium", True, [_message("medium")], 0.726, 0.45, "user:" + USER),
    ("on_high", True, [_message("high")], 0.796, 0.75, "user:" + USER),
    ("on_critical", True, [_message("critical")], 0.856, 1.0, "user:" + USER),
    (
        "on_multiple_entities",
        True,
        [_message("medium"), _message("critical", entity_type="device", entity_id=HOST)],
        0.856,
        1.0,
        "device:" + HOST,
    ),
    ("on_other_tenant", True, [_message("critical", tenant=OTHER_TENANT)], 0.656, 0.15, None),
    ("on_other_entity", True, [_message("critical", entity_id="someone-else")], 0.656, 0.15, None),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("name,enabled,messages,confidence,anomaly,selected", CASES, ids=[c[0] for c in CASES])
async def test_ueba_message_changes_only_matching_alert_scores(
    monkeypatch, name, enabled, messages, confidence, anomaly, selected,
):
    # Reproduce the production startup choice; never change a running service.
    monkeypatch.setattr(settings, "ueba_fusion_enabled", enabled)
    redis = MemoryRedis()
    cache = UebaSignalCache(redis, ttl_seconds=settings.ueba_signal_ttl_seconds)
    active_cache = cache if settings.ueba_fusion_enabled else None
    engine = FusionEngine(Deduplicator(redis), Correlator(redis), ueba_cache=active_cache)
    sink = MemorySink()
    worker = FusionWorker(engine, sink=sink, ueba_cache=active_cache)
    worker._producer = SimpleNamespace(send_and_wait=AsyncMock())

    for message in messages:
        wire = json.loads(json.dumps(message))
        if enabled:
            await worker._process_message(wire, topic=settings.kafka_topic_ueba_anomalies)
        else:
            # Disabling leaves pre-existing cache entries intact, but the
            # worker does not subscribe to this topic or attach the cache.
            assert await cache.record(wire)
    worker._producer.send_and_wait.assert_not_awaited()

    alert = RawAlert(
        id=UUID(int=7601), tenant_id=TENANT,
        identity_version="source-v1", source_alert_id=UUID(int=7601),
        source="ueba-link-example", title="UEBA linkage example",
        severity="high", username=USER, hostname=HOST, src_ip="192.0.2.10",
        mitre_tactics=["execution"], mitre_techniques=["T1059.001"],
        risk_score=0.5, source_event_ids=["ueba-link-source-event"],
        event_time="2026-10-21T08:01:00+00:00",
    )
    original = copy.deepcopy(alert.model_dump(mode="json"))
    await worker._process_message(original, topic=settings.kafka_topic_alerts_raw)
    worker._producer.send_and_wait.assert_awaited_once()
    delivery = worker._producer.send_and_wait.await_args
    assert delivery.args[0] == settings.kafka_topic_alerts_fused
    envelope = delivery.kwargs["value"]
    fused = FusedAlert.model_validate(envelope)

    assert fused.confidence_score == pytest.approx(confidence)
    assert fused.anomaly_score == pytest.approx(anomaly)
    assert fused.priority_score == pytest.approx(1.0)
    assert fused.confidence_label.value == ("high" if confidence >= 0.7 else "medium")
    assert fused.alert.risk_score == 0.5
    assert fused.alert.severity.value == "high"
    assert fused.alert.source_alert_id == UUID(int=7601)
    assert sink.rows[fused.id]["fused"]["confidence_score"] == pytest.approx(confidence)
    assert sink.rows[fused.id]["fused"]["anomaly_score"] == pytest.approx(anomaly)
    factors = [f for f in fused.confidence_rationale if f.factor == "ueba_anomaly"]
    assert len(factors) == (1 if selected else 0)
    if selected:
        assert selected in factors[0].value

    print("UEBA_FUSION_EXAMPLE " + json.dumps({
        "case": name, "enabled": enabled, "input_signal_count": len(messages),
        "confidence_score": fused.confidence_score,
        "confidence_label": fused.confidence_label.value,
        "anomaly_score": fused.anomaly_score, "priority_score": fused.priority_score,
        "selected_entity": selected, "ueba_factor_count": len(factors),
        "published_and_saved_scores_match": True,
    }, sort_keys=True))
