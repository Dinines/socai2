"""Field preservation through actual builders, sink arguments and lake mapping."""
import copy
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.models.alert import FusedAlert, FusionDecision, RawAlert
from app.services.alert_sink import AlertSink, _DEDUP_SOURCE_EVENT_SQL, _INSERT_SQL, _insert_args
from app.services.confidence import ConfidenceScorer
from app.services.detection_engine import DetectionEngine, DetectionHit
from app.services.lake_writer import event_to_row
from app.services.promoter import promote_normalized_event
from app.services.received_fields import activity_block
from app.services.sessions import _session_block
from app.services.window_sources import record_sources, read_sources
from app.services.windowed_detection import SequenceRule, WindowedDetectionEngine, WindowRule
from tests.test_process_delivery import TENANT, worker_fixture
from tests.test_sigma_correlation_replay import _FakeRedis

WHEN = datetime(2026, 10, 31, 1, 2, 3, tzinfo=UTC)


def message(identity="event-1"):
    return {"event_id": identity, "tenant_id": str(TENANT), "ocsf_event": {
        "class_uid": 2001, "severity_id": 5, "time": WHEN.isoformat(), "message": "Same finding",
        "rule": {"uid": "vendor-rule", "name": "Vendor rule"},
        "device": {"name": "observed-host"}, "actor": {"user": {"name": "alice"}},
        "src_endpoint": {"ip": "192.0.2.1"}, "dst_endpoint": {"ip": "192.0.2.2"},
        "domain": "example.test", "url": {"url_string": "https://example.test/path"},
        "mitre_attck": [{"technique_id": "T1003", "tactic_names": ["credential-access"]}],
        "raw_data": {"event_type": "auth", "user": "alice", "outcome": "failure"}}}


def generated(origin, payload):
    hit = DetectionHit("local-rule", "Rule", "high", "not-a-tactic", ["T1059"], tactics=["execution"])
    if origin == "promotion":
        return promote_normalized_event(payload)
    if origin == "rule":
        return DetectionEngine(rules=[]).build_alert(payload, hit)
    return WindowedDetectionEngine(_FakeRedis(), rules=(), sequences=()).build_alert(payload, hit)


@pytest.mark.parametrize("origin", ["promotion", "rule", "window"])
def test_received_time_objects_and_label_origins_reach_sink(origin):
    payload = message()
    original = copy.deepcopy(payload)
    alert = generated(origin, payload)
    assert alert.event_time == WHEN and alert.hostname == "observed-host" and alert.username == "alice"
    assert alert.dst_ip == "192.0.2.2" and alert.domain == "example.test" and alert.url.endswith("/path")
    assert "credential-access" in alert.mitre_tactics and "not-a-tactic" not in alert.mitre_tactics
    labels = alert.field_metadata["detection_labels"]
    assert labels["source"] == {"tactics": ["credential-access"], "techniques": ["T1003"]}
    if origin != "promotion":
        assert labels["rule"] == {"tactics": ["execution"], "techniques": ["T1059"]}
    else:
        assert alert.rule_id == "vendor-rule" and alert.rule_name == "Vendor rule"
        before_rule = alert.model_copy(update={"rule_id": None})
        assert alert.deterministic_id() == before_rule.deterministic_id()
    fused = FusedAlert(id=alert.deterministic_id(), tenant_id=TENANT, alert=alert, fusion_decision=FusionDecision.NEW_INCIDENT)
    args = _insert_args(fused)
    assert args[16] == WHEN and args[21] == alert.rule_id
    metadata = json.loads(args[-1])["socai2_fusion"]
    assert metadata["event_time_source"] == "ocsf.time" and not metadata["event_time_fallback"]
    assert "first_seen, last_seen" in _INSERT_SQL and _INSERT_SQL.count("COALESCE($17, NOW())") == 3
    assert original == payload


def test_missing_time_and_labels_stay_unknown_with_explicit_storage_fallback():
    payload = message()
    payload["ocsf_event"].pop("time")
    payload["ocsf_event"].pop("mitre_attck")
    alert = generated("promotion", payload)
    assert alert.event_time is None and alert.mitre_tactics == []
    fused = FusedAlert(id=alert.id, tenant_id=TENANT, alert=alert, fusion_decision=FusionDecision.NEW_INCIDENT)
    metadata = json.loads(_insert_args(fused)[-1])["socai2_fusion"]
    assert metadata["event_time_fallback"] and metadata["event_time_source"] == "unknown"
    lake = event_to_row(payload)
    assert json.loads(lake["ocsf_json"])["_socai2_storage"]["event_time_fallback"]


@pytest.mark.asyncio
async def test_legacy_promotion_without_rule_still_reuses_proven_first_event():
    from app.services.delivery_recovery import legacy_event_candidate, matches_legacy_event
    incoming = generated("promotion", message())
    prior = legacy_event_candidate(incoming.model_copy(update={"rule_id": None, "rule_name": None}))
    worker, sink, _ = worker_fixture()
    saved = await worker.process_alert(prior)
    original = copy.deepcopy(sink.rows[saved.id])
    replay = await worker.process_alert(incoming)
    assert replay.id == saved.id and len(sink.rows) == 1
    assert sink.rows[saved.id] == original and replay.alert.rule_id is None
    assert not matches_legacy_event(saved, incoming.model_copy(update={"identity_event_id": "another-event"}))
    assert not matches_legacy_event(saved, incoming.model_copy(update={"identity_origin": "rule"}))


@pytest.mark.parametrize("value", [1793408523000, "2026-10-31T09:02:03+08:00"])
def test_time_value_is_identical_in_alert_and_lake(value):
    payload = message()
    payload["ocsf_event"]["time"] = value
    assert generated("rule", payload).event_time == WHEN
    assert event_to_row(payload)["event_time"] == WHEN.replace(tzinfo=None)


def test_sequence_clock_uses_received_utc_time_without_host_local_roundtrip():
    assert WindowedDetectionEngine._event_seconds({"event_time": 1000}, 99999) == 1000
    assert WindowedDetectionEngine._event_seconds({"event_time": WHEN.isoformat()}, 99999) == WHEN.timestamp()
    assert WindowedDetectionEngine._event_seconds({"event_time": "2026-10-31T09:02:03+08:00"}, 99999) == WHEN.timestamp()


@pytest.mark.asyncio
@pytest.mark.parametrize("location", ["envelope", "ocsf"])
async def test_session_stamp_and_lake_read_the_same_activity(location):
    worker, _, _ = worker_fixture()
    payload = message()
    activity = {"action": "session.start", "outcome": "success", "session": {"key": "vendor-1", "key_kind": "vendor_session"}}
    (payload if location == "envelope" else payload["ocsf_event"])["activity"] = activity
    worker._sessions = SimpleNamespace(record_event=AsyncMock(return_value=SimpleNamespace(id=UUID(int=901), key_kind="vendor_session", originating_human=None)))
    rows = []
    async def save(event):
        rows.append(event_to_row(event))
        return True
    worker._lake = SimpleNamespace(write_event=save)
    await worker._process_message(payload, topic="aisoc.raw_events")
    assert _session_block(payload)["id"] == str(UUID(int=901))
    assert rows[0]["action"] == "session.start" and rows[0]["outcome"] == "success"
    assert rows[0]["session_id"] == str(UUID(int=901))


def test_conflicting_activity_has_explicit_envelope_precedence():
    payload = message()
    payload["activity"] = {"action": "envelope"}
    payload["ocsf_event"]["activity"] = {"action": "body"}
    payload["ocsf_event"]["activity"]["outcome"] = "success"
    assert activity_block(payload)[1] == "activity+ocsf_event.activity"
    row = event_to_row(payload)
    assert row["action"] == "envelope"
    assert row["outcome"] == "success"
    stored = json.loads(row["ocsf_json"])
    assert stored["activity"]["action"] == "body"
    assert stored["_socai2_storage"]["envelope_activity"]["action"] == "envelope"


def test_hash_algorithm_and_structured_raw_are_not_relabelled():
    payload = message()
    payload["ocsf_event"]["file"] = {"fingerprints": [{"algorithm": "MD5", "value": "b"*32}, {"algorithm": "SHA-256", "value": "a"*64}]}
    row = event_to_row(payload)
    assert row["hash_sha256"] == "a"*64 and json.loads(row["raw_payload"])["event_type"] == "auth"
    payload["ocsf_event"]["file"]["fingerprints"].pop()
    assert event_to_row(payload)["hash_sha256"] == ""
    assert "b"*32 in event_to_row(payload)["iocs"]
    payload["ocsf_event"]["file"]["fingerprints"].append({"algorithm": "SHA256", "value": "not-a-sha256"})
    assert event_to_row(payload)["hash_sha256"] == ""
    assert "not-a-sha256" in event_to_row(payload)["iocs"]
    payload["ocsf_event"]["hash_sha256"] = "C" * 64
    assert event_to_row(payload)["hash_sha256"] == "C" * 64


def test_bounded_raw_remains_valid_json_and_discloses_omissions():
    payload = message()
    payload["ocsf_event"]["raw_data"] = {"long": 'quoted"\\字' * 70000}
    row = event_to_row(payload)
    for field, limit in (("raw_payload", 65536), ("ocsf_json", 262144)):
        stored = json.loads(row[field])
        assert stored["_socai2_storage"]["truncated"]
        assert stored["_socai2_storage"]["original_bytes"] > limit
        assert len(stored["_socai2_storage"]["sha256"]) == 64
        assert len(row[field].encode()) <= limit and isinstance(stored["preview"], str)


@pytest.mark.asyncio
async def test_score_computed_disabled_failed_and_unknown_are_distinguishable():
    worker, _, _ = worker_fixture()
    computed = await worker.process_alert(generated("promotion", message()))
    assert computed.confidence_status == "computed" and _insert_args(computed)[11] is not None
    worker.engine._confidence_scorer = ConfidenceScorer(enabled=False)
    disabled = await worker.process_alert(generated("promotion", message("event-2")))
    assert disabled.confidence_status == "disabled" and _insert_args(disabled)[11:14] == (None, None, None)
    def fail(*args, **kwargs):
        raise RuntimeError("synthetic scoring failure")
    worker.engine._confidence_scorer = SimpleNamespace(score=fail)
    failed = await worker.process_alert(generated("promotion", message("event-3")))
    assert failed.confidence_status == "failed" and _insert_args(failed)[11] is None
    unknown = failed.model_copy(update={"confidence_status": "unknown"})
    assert _insert_args(unknown)[11] is None


@pytest.mark.asyncio
async def test_source_reference_cap_and_append_time_do_not_rewrite_first_material():
    alert = generated("promotion", message())
    alert.source_event_ids = [f"e-{i}" for i in range(201)]
    fused = FusedAlert(id=alert.id, tenant_id=TENANT, alert=alert, fusion_decision=FusionDecision.NEW_INCIDENT)
    args = _insert_args(fused)
    assert len(json.loads(args[19])) == 200
    assert json.loads(args[-1])["socai2_fusion"]["source_event_ids_truncated"]
    conn = SimpleNamespace(execute=AsyncMock())
    await AlertSink("unused")._record_deduplicated_event(conn, alert)
    assert conn.execute.await_args.args[-1] == WHEN
    assert "AND NOT (source_event_ids @>" in _DEDUP_SOURCE_EVENT_SQL
    assert "updated_at = NOW()" in _DEDUP_SOURCE_EVENT_SQL and "GREATEST(last_seen" in _DEDUP_SOURCE_EVENT_SQL
    assert "raw_event =" not in _DEDUP_SOURCE_EVENT_SQL and "delivery_snapshot" not in _DEDUP_SOURCE_EVENT_SQL


class SourcesRedis(_FakeRedis):
    async def get(self, key):
        return self.strings.get(key)

    async def zremrangebyrank(self, key, start, end):
        ordered = sorted(self.zsets.get(key, {}), key=lambda v: self.zsets[key][v])
        for value in ordered[start:end+1]:
            del self.zsets[key][value]


@pytest.mark.asyncio
async def test_threshold_carries_participating_ids_and_explicit_window():
    rule = WindowRule("threshold", "Threshold", "high", "identity", ["T1110"], {"outcome": "failure"}, "user", 2, 60)
    engine = WindowedDetectionEngine(SourcesRedis(), rules=(rule,), sequences=())
    one, two = message("one"), message("two")
    for payload in (one, two):
        payload["ocsf_event"]["raw_data"] = json.dumps(payload["ocsf_event"]["raw_data"])
    assert await engine.evaluate(one) == []
    hit = (await engine.evaluate(two))[0]
    alert = engine.build_alert(two, hit)
    assert set(alert.source_event_ids) == {"one", "two"}
    window = alert.field_metadata["source_window"]
    assert window["scope"] == "matched_events_in_processing_window" and window["window_seconds"] == 60
    assert not window["truncated"] and not window["complete"]  # prior counter history is not proven


@pytest.mark.asyncio
async def test_window_reference_overflow_and_missing_identity_are_explicit():
    redis = SourcesRedis()
    for i in range(201):
        assert await record_sources(redis, "refs", f"e-{i}", WHEN, 1000+i, 600)
    await record_sources(redis, "refs", None, None, 1201, 600)
    ids, metadata = await read_sources(redis, "refs", 1201, 600, True)
    assert len(ids) == 200 and metadata["truncated"] and metadata["missing_ids"] and not metadata["complete"]


@pytest.mark.asyncio
async def test_sequence_preserves_ids_as_candidates_without_claiming_a_causal_chain():
    rule = SequenceRule("seq", "Sequence", "high", "identity", [], ({"step": "a"}, {"step": "b"}), "user", 60)
    engine = WindowedDetectionEngine(SourcesRedis(), rules=(), sequences=(rule,))
    first, second = message("first"), message("second")
    for payload, step, when in ((first, "a", 1000), (second, "b", 1010)):
        payload["ocsf_event"]["raw_data"] = json.dumps({"user": "alice", "step": step, "event_time": when})
    assert await engine.evaluate(first) == []
    hit = (await engine.evaluate(second))[0]
    assert set(hit.source_event_ids) == {"first", "second"}
    assert hit.source_metadata["scope"] == "matched_stage_candidates"
    assert set(engine.build_alert(second, hit).source_event_ids) == {"first", "second"}
