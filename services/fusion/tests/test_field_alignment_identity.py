"""Received identity / real worker and correlator; no external services."""
import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from app.core.config import settings
from app.models.alert import RawAlert
from app.services.alert_sink import _insert_args
from app.services.correlator import Correlator
from app.services.delivery_recovery import legacy_event_candidate, make_snapshot, restore_snapshot
from app.services.detection_engine import DetectionEngine, DetectionHit
from app.services.promoter import promote_normalized_event
from app.services.windowed_detection import WindowedDetectionEngine
from tests.test_process_delivery import MemoryRedis, TENANT, worker_fixture


def message(event="event-1", connector=401):
    return {"event_id": event, "tenant_id": str(TENANT), "connector_id": str(UUID(int=connector)),
            "ocsf_event": {"class_uid": 2001, "severity_id": 5, "message": "Same finding",
                           "device": {"name": "host-a"}, "metadata": {"product": {"name": "fixture"}}}}


def build(origin, payload, rule="rule-1"):
    hit = DetectionHit(rule_id=rule, name="Same rule title", severity="high", category="execution", mitre=[])
    if origin == "promotion":
        return promote_normalized_event(payload)
    if origin == "rule":
        return DetectionEngine(rules=[]).build_alert(payload, hit)
    return WindowedDetectionEngine(MemoryRedis(), rules=[]).build_alert(payload, hit)


@pytest.mark.parametrize("origin", ["promotion", "rule", "window"])
@pytest.mark.asyncio
async def test_independent_occurrences_replay_and_connector_are_distinct(origin):
    worker, sink, _ = worker_fixture()
    first = await worker.process_alert(build(origin, message()))
    snapshot = copy.deepcopy(sink.rows[first.id])
    replay = build(origin, message())
    replay.description = "A later description must not replace the first material"
    repeated = await worker.process_alert(replay)
    second = await worker.process_alert(build(origin, message("event-2")))
    another_connector = await worker.process_alert(build(origin, message(connector=402)))
    assert first.id == repeated.id
    assert len({first.id, second.id, another_connector.id}) == 3
    assert len(sink.rows) == 3 and worker.engine.process.await_count == 3
    assert sink.rows[first.id] == snapshot
    assert repeated.alert.description == first.alert.description


def test_detector_origin_and_rules_remain_independent():
    alerts = [build(origin, message(), rule) for origin, rule in
              [("promotion", "rule-1"), ("rule", "rule-1"), ("rule", "rule-2"), ("window", "rule-1")]]
    assert len({alert.deterministic_id() for alert in alerts}) == 4


@pytest.mark.parametrize("origin", ["promotion", "rule", "window"])
def test_missing_event_identity_keeps_legacy_and_metadata_uuid_is_supported(origin):
    payload = message()
    del payload["event_id"]
    assert build(origin, payload).identity_version == "legacy-v1"
    value = "abcdefab-cdef-abcd-efab-cdefabcdefab"
    payload["ocsf_event"]["metadata"]["uid"] = value.upper()
    alert = build(origin, payload)
    assert alert.identity_event_id == value and alert.source_event_ids == [value]
    assert alert.source_alert_id is None  # not a fabricated vendor finding UUID


@pytest.mark.parametrize("origin", ["promotion", "rule", "window"])
@pytest.mark.asyncio
async def test_proven_legacy_first_event_is_reused_but_other_occurrence_is_not(origin):
    worker, sink, _ = worker_fixture()
    old = await worker.process_alert(legacy_event_candidate(build(origin, message())))
    # Simulate a pre-change v1 snapshot, without the newly added optional fields.
    snapshot = make_snapshot(old)
    snapshot["fused"].pop("correlation_basis")
    snapshot["fused"]["alert"].pop("identity_event_id")
    snapshot["fused"]["alert"].pop("identity_origin")
    from app.services.delivery_recovery import _canonical
    import hashlib
    snapshot["sha256"] = hashlib.sha256(_canonical(snapshot["fused"])).hexdigest()
    sink.rows[old.id] = copy.deepcopy(snapshot)
    replay = await worker.process_alert(build(origin, message()))
    different = await worker.process_alert(build(origin, message("event-2")))
    assert replay.id == old.id and replay.correlation_basis is None
    assert different.id != old.id and len(sink.rows) == 2
    assert sink.rows[old.id] == snapshot


@pytest.mark.asyncio
async def test_legacy_row_from_another_connector_does_not_claim_this_event():
    worker, sink, _ = worker_fixture()
    old = await worker.process_alert(legacy_event_candidate(build("promotion", message())))
    current = await worker.process_alert(build("promotion", message(connector=402)))
    assert current.id != old.id and len(sink.rows) == 2


def raw(title="one", **fields):
    alert = RawAlert(tenant_id=TENANT, source="fixture", title=title, **fields)
    alert.id = alert.deterministic_id()
    return alert


@pytest.mark.asyncio
async def test_typed_entity_unknown_and_delimiters_cannot_merge_unrelated_members():
    correlator = Correlator(MemoryRedis())
    inputs = [raw(hostname="shared"), raw(username="shared"), raw("unknown-a"), raw("unknown-b"),
              raw(hostname="x:y", mitre_tactics=["z"]), raw(hostname="x", mitre_tactics=["y:z"])]
    results = [await correlator.correlate(alert) for alert in inputs]
    assert len({incident.id for _, incident, _ in results}) == len(inputs)
    matched, incident, basis = await correlator.correlate(raw("another", hostname="shared"))
    assert matched and incident.id == results[0][1].id and incident.alert_count == 2
    assert basis.entity_type == "host" and basis.reason == "matched"
    assert results[2][2].entity_value is None  # no invented unknown object


@pytest.mark.asyncio
async def test_old_untyped_index_is_not_used_for_new_members():
    redis = MemoryRedis()
    correlator = Correlator(redis)
    host = raw(hostname="shared", mitre_tactics=["execution"])
    old = correlator._create_incident(host)
    await correlator._save_incident(old)
    await redis.set(f"aisoc:fusion:correlation:{TENANT}:shared:execution", str(old.id))
    matched, incident, _ = await correlator.correlate(raw(username="shared", mitre_tactics=["execution"]))
    assert not matched and incident.id != old.id


@pytest.mark.asyncio
async def test_actual_decision_basis_survives_sink_arguments_snapshot_and_replay():
    worker, _, _ = worker_fixture()
    worker.engine._correlator._window = 731
    first = await worker.process_alert(build("promotion", message()))
    second = await worker.process_alert(build("promotion", message("event-2")))
    assert second.incident_id == first.incident_id
    basis = second.correlation_basis.model_dump(mode="json")
    assert basis["window_seconds"] == 731 and basis["decision"] == "correlated"
    assert basis["entity_type"] == "host" and basis["entity_value"] == "host-a"
    metadata = json.loads(_insert_args(second, delivery_snapshot=make_snapshot(second))[-1])["socai2_fusion"]
    assert metadata["correlation_basis"] == basis
    assert metadata["identity"]["event_id"] == "event-2"
    restored = restore_snapshot(metadata["delivery_snapshot"], second.alert)
    assert restored.correlation_basis.model_dump(mode="json") == basis
    worker.engine._correlator._window = 99
    replay = await worker.process_alert(build("promotion", message("event-2")))
    assert replay.correlation_basis.model_dump(mode="json") == basis


@pytest.mark.asyncio
async def test_member_limit_and_missing_summary_reasons_are_recorded():
    redis = MemoryRedis()
    correlator = Correlator(redis)
    correlator._max_alerts = 1
    first = raw(hostname="h")
    _, incident, _ = await correlator.correlate(first)
    _, replay, reason = await correlator.correlate(first)
    assert replay.alert_count == 1 and reason.reason == "existing_member"
    _, next_incident, reason = await correlator.correlate(raw("two", hostname="h"))
    assert next_incident.id != incident.id and reason.reason == "member_limit"
    redis.data.pop(f"aisoc:fusion:incident:{next_incident.id}")
    _, _, reason = await correlator.correlate(raw("three", hostname="h"))
    assert reason.reason == "missing_summary"


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.asyncio
async def test_promotion_switch_preserves_lake_and_both_detectors(monkeypatch, enabled):
    worker, _, _ = worker_fixture()
    payload = message()
    monkeypatch.setattr(settings, "event_promotion_enabled", enabled)
    worker._lake = SimpleNamespace(write_event=AsyncMock(return_value=True))
    detected, windowed = build("rule", payload), build("window", payload)
    worker._detector = SimpleNamespace(evaluate_async=AsyncMock(return_value=[object()]), build_alert=Mock(return_value=detected))
    worker._windowed = SimpleNamespace(evaluate=AsyncMock(return_value=[object()]), build_alert=Mock(return_value=windowed))
    promotion = Mock(wraps=promote_normalized_event)
    monkeypatch.setattr("app.workers.consumer.promote_normalized_event", promotion)
    worker.process_alert = AsyncMock()
    await worker._process_message(payload, topic=settings.kafka_topic_raw_events)
    worker._lake.write_event.assert_awaited_once()
    assert worker.process_alert.await_count == (3 if enabled else 2)
    assert promotion.call_count == int(enabled)
