"""Only controlled producer/resource fixtures; no actual Kafka or source writes."""
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/testdata"))
import streaming_fixture
import streaming_send as sender
from alert_scenarios import json_bytes, sha256


@pytest.fixture
def fixture(tmp_path):
    config = json.loads((ROOT / "tools/testdata/streaming-fixture.example.json").read_bytes())
    config["batch_id"] = "sender-component-new-batch"
    dataset = tmp_path / "dataset"
    streaming_fixture.generate(config, dataset)
    resource = json_bytes({"status": "passed", "source": "controlled_component_resource_fixture"})
    (tmp_path / "resource.json").write_bytes(resource)
    profile = {"schema_version": sender.VERSION, "candidate_id": "streaming-20261115-01",
        "batch_id": config["batch_id"], "tenant_id": config["tenant_id"],
        "topics": {role: f"socai2.testdata.streaming-20261115-01.{role}"
                   for role in ("raw", "raw_events", "fused", "dlq")},
        "producer_env_file": str(tmp_path / "not-read-during-prepare.env"),
        "expected_bootstrap_servers": "controlled.invalid:9092", "security_protocol": "PLAINTEXT",
        "timeout_seconds": 20.0, "request_timeout_ms": 10000,
        "resource_readback_file": "resource.json", "resource_readback_sha256": sha256(resource)}
    profile_path = tmp_path / "profile.json"
    profile_path.write_bytes(json_bytes(profile))
    return SimpleNamespace(root=tmp_path, dataset=dataset, profile=profile, profile_path=profile_path,
                           prepared=tmp_path / "prepared", calls=[], stopped=False)


def prepare(f):
    return sender.prepare(f.dataset, f.profile_path, f.prepared)


def send(f, phase="S01-context", behavior="ok", context_readback=None, preflight_readback=None):
    class Producer:
        def __init__(self, **kwargs):
            assert kwargs["acks"] == "all" and kwargs["enable_idempotence"] is True
            assert kwargs["request_timeout_ms"] == f.profile["request_timeout_ms"]
        async def start(self):
            if behavior == "start-fail":
                raise ConnectionError("sensitive-not-logged")
        async def send_and_wait(self, topic, value, key):
            intent = json.loads((f.prepared / "receipts" / f"{phase}.json").read_bytes())
            assert intent["records"][-1]["state"] == "started_outcome_unknown"
            assert key == f.profile["tenant_id"].encode()
            f.calls.append((topic, value, key))
            if behavior == "timeout":
                raise asyncio.TimeoutError("sensitive-not-logged")
            if behavior == "cancel":
                raise asyncio.CancelledError()
            return SimpleNamespace(topic="wrong-topic" if behavior == "wrong" else topic,
                                   partition=0, offset=len(f.calls) - 1)
        async def stop(self):
            f.stopped = True
    with patch.object(sender, "kafka_config", return_value={
            "bootstrap_servers": f.profile["expected_bootstrap_servers"], "security_protocol": "PLAINTEXT"}):
        return asyncio.run(sender.send_phase(f.prepared, phase,
            context_readback=context_readback, preflight_readback=preflight_readback, producer_factory=Producer))


def readback(f, **changes):
    manifest = json.loads((f.prepared / "manifest.json").read_bytes())
    data = {"status": "passed", "source": "real_lake_readback", "batch_id": f.profile["batch_id"],
        "tenant_id": f.profile["tenant_id"], "prepared_manifest_sha256": sha256((f.prepared / "manifest.json").read_bytes()),
        "event_ids": [r["source_event_id"] for r in manifest["phases"]["S01-context"]["records"]],
        "unexpected_alerts": 0, "unexpected_incidents": 0, "unexpected_tasks": 0,
        "attempts": 0, "runs": 0, "model_calls": 0,
        "test_origin": "controlled gate-shape fixture, not real lake evidence", **changes}
    path = f.root / "controlled-readback.json"
    path.write_bytes(json_bytes(data))
    return path


def test_prepare_phase_counts_identity_and_no_expected_reads(fixture):
    f = fixture
    for path in ("expected.json", "identity-map.json", "actions.json"):
        (f.dataset / path).unlink()
    with patch("socket.socket", side_effect=AssertionError("prepare must be offline")):
        m = prepare(f)
    assert m["batch_id"] not in m["phases"]["S01-context"]["topic"]
    assert [m["phases"][p]["count"] for p in sender.PHASES] == [12, 3]
    assert len(list((f.prepared / "wire").rglob("*.json"))) == 15
    assert not (f.prepared / "expected.json").exists()
    assert all(b"model_verdict" not in p.read_bytes() for p in (f.prepared / "wire").rglob("*.json"))
    with pytest.raises(FileExistsError):
        prepare(f)


def test_two_phases_gate_actual_readback_ack_and_fixed_receipts(fixture):
    f = fixture
    prepare(f)
    with pytest.raises(ValueError, match="actual context readback"):
        send(f, "S01-alerts")
    context = send(f)
    assert context["accepted"] == 12 and context["status"] == "accepted_only"
    assert context["processing_confirmed"] is False
    with pytest.raises(FileExistsError):
        send(f)
    gate = readback(f)
    alerts = send(f, "S01-alerts", context_readback=gate)
    assert alerts["accepted"] == 3 and alerts["context_readback_sha256"] == sha256(gate.read_bytes())
    _, manifest, values = sender.load_prepared(f.prepared)
    assert [value for _, value, _ in f.calls] == values["S01-context"] + values["S01-alerts"]
    assert {topic for topic, _, _ in f.calls} == {f.profile["topics"][k] for k in ("raw", "raw_events")}
    assert manifest["phases"]["S01-alerts"]["count"] == 3 and f.stopped


@pytest.mark.parametrize("behavior", ["timeout", "wrong", "cancel"])
def test_unknown_stops_and_preserves_unattempted_and_no_resend(fixture, behavior):
    f = fixture
    prepare(f)
    if behavior == "cancel":
        with pytest.raises(asyncio.CancelledError):
            send(f, behavior=behavior)
    else:
        send(f, behavior=behavior)
    text = (f.prepared / "receipts/S01-context.json").read_text()
    saved = json.loads(text)
    assert saved["accepted"] == 0 and saved["not_attempted"] == 11
    assert saved["records"][0]["state"] == "outcome_unknown"
    assert len(f.calls) == 1 and f.stopped and "sensitive-not-logged" not in text
    with pytest.raises(FileExistsError):
        send(f)


def test_known_presend_failure_keeps_all_unattempted(fixture):
    prepare(fixture)
    result = send(fixture, behavior="start-fail")
    assert result["records"] == [] and result["not_attempted"] == 12 and not fixture.calls


@pytest.mark.parametrize("change", [
    {"tenant_id": "11111111-1111-4111-8111-111111111111"},
    {"batch_id": "different-batch"}, {"resource_readback_sha256": "0" * 64},
    {"topics": {"raw": "aisoc.alerts.raw"}},
])
def test_wrong_profile_refused_before_output(fixture, change):
    fixture.profile_path.write_bytes(json_bytes({**fixture.profile, **change}))
    with pytest.raises(ValueError):
        prepare(fixture)
    assert not fixture.prepared.exists()


def test_bad_readback_or_s04_and_transport_change_do_not_send(fixture):
    f = fixture
    prepare(f)
    with pytest.raises(ValueError, match="only S01"):
        send(f, "S04-alerts")
    send(f)
    for change in ({"unexpected_alerts": 1}, {"runs": 1}, {"event_ids": []},
                   {"batch_id": "other"}, {"source": "broker_ack"}):
        with pytest.raises(ValueError, match="same-batch readback"):
            send(f, "S01-alerts", context_readback=readback(f, **change))
    with (patch.object(sender, "kafka_config", return_value={
            "bootstrap_servers": "different.invalid:9092", "security_protocol": "PLAINTEXT"}),
          pytest.raises(ValueError, match="transport differs")):
        asyncio.run(sender.send_phase(f.prepared, "S01-alerts", context_readback=readback(f)))
    assert not (f.prepared / "receipts/S01-alerts.json").exists() and len(f.calls) == 12


def test_tampered_wire_and_profile_are_refused(fixture):
    f = fixture
    prepare(f)
    path = f.prepared / "wire/S01-context/001.json"
    original = path.read_bytes()
    value = json.loads(original)
    value["ocsf_event"]["time"] = "2025-01-01T00:00:00Z"
    path.write_bytes(json_bytes(value))
    with pytest.raises(ValueError, match="bytes or identity changed"):
        send(f)
    path.write_bytes(original)
    profile_path = f.prepared / "profile.json"
    profile = json.loads(profile_path.read_bytes())
    profile["producer_env_file"] = "/some-other-env"
    profile_path.write_bytes(json_bytes(profile))
    with pytest.raises(ValueError, match="profile/contracts changed"):
        send(f)
    assert not fixture.calls and not list((f.prepared / "receipts").iterdir())


def s04(f):
    f.profile.update(phase_set="S04", baseline_snapshot_sha256="a" * 64)
    f.profile_path.write_bytes(json_bytes(f.profile))
    return prepare(f)


def s04_gate(f, *, context=False, **changes):
    manifest = json.loads((f.prepared / "manifest.json").read_bytes())
    value = {"status": "passed", "source": "real_lake_and_postgres_readback",
        "batch_id": f.profile["batch_id"], "tenant_id": f.profile["tenant_id"],
        "prepared_manifest_sha256": sha256((f.prepared / "manifest.json").read_bytes()),
        "baseline_snapshot_sha256": f.profile["baseline_snapshot_sha256"],
        "business_baseline_unchanged": True, "new_alert_absent": True, "new_event_absent": True,
        "test_origin": "controlled gate-shape fixture, not real source evidence"}
    if context:
        value.update(source="real_lake_readback", event_ids=[r["source_event_id"] for r in manifest["phases"]["S04-context"]["records"]],
            delta_counts=dict.fromkeys(("alerts", "incidents", "tasks", "attempts", "runs", "model_calls"), 0),
            existing_runs=6)
    path = f.root / ("s04-context-gate.json" if context else "s04-preflight-gate.json")
    path.write_bytes(json_bytes({**value, **changes}))
    return path


def test_s04_prepares_only_frozen_increment_without_expected_reads(fixture):
    f = fixture
    for name in ("expected.json", "identity-map.json", "actions.json"):
        (f.dataset / name).unlink()
    with patch("socket.socket", side_effect=AssertionError("offline only")):
        manifest = s04(f)
    assert set(manifest["phases"]) == {"S04-context", "S04-alerts"}
    assert len(list((f.prepared / "wire").rglob("*.json"))) == 2
    for phase, source in (("S04-context", "context-events.jsonl"), ("S04-alerts", "alerts.jsonl")):
        assert (f.prepared / f"wire/{phase}/001.json").read_bytes() == (f.dataset / "S04" / source).read_bytes()
    with pytest.raises(ValueError, match="only S04"):
        send(f, "S01-context")
    assert not f.calls


def test_s04_absence_and_incremental_gate_before_exactly_two_sends(fixture):
    f = fixture
    s04(f)
    with pytest.raises(ValueError, match="actual preflight"):
        send(f, "S04-context")
    for change in ({"new_event_absent": False}, {"new_alert_absent": False}, {"baseline_snapshot_sha256": "b" * 64}):
        with pytest.raises(ValueError, match="preflight"):
            send(f, "S04-context", preflight_readback=s04_gate(f, **change))
    result = send(f, "S04-context", preflight_readback=s04_gate(f))
    assert result["accepted"] == 1
    with pytest.raises(FileExistsError):
        send(f, "S04-context", preflight_readback=s04_gate(f))
    with pytest.raises(ValueError, match="actual context"):
        send(f, "S04-alerts")
    for change in ({"delta_counts": {"runs": 0}}, {"baseline_snapshot_sha256": "b" * 64},
                   {"business_baseline_unchanged": False}, {"event_ids": []}):
        with pytest.raises(ValueError, match="same-batch readback"):
            send(f, "S04-alerts", context_readback=s04_gate(f, context=True, **change))
    result = send(f, "S04-alerts", context_readback=s04_gate(f, context=True))
    assert result["accepted"] == 1 and len(f.calls) == 2
    assert f.calls[0][1] == (f.dataset / "S04/context-events.jsonl").read_bytes()
    assert f.calls[1][1] == (f.dataset / "S04/alerts.jsonl").read_bytes()
    with pytest.raises(FileExistsError):
        send(f, "S04-alerts", context_readback=s04_gate(f, context=True))


def test_s04_unknown_never_replays_or_unlocks_alert(fixture):
    f = fixture
    s04(f)
    result = send(f, "S04-context", behavior="timeout", preflight_readback=s04_gate(f))
    assert result["accepted"] == 0 and result["records"][0]["state"] == "outcome_unknown"
    with pytest.raises(FileExistsError):
        send(f, "S04-context", preflight_readback=s04_gate(f))
    with pytest.raises(ValueError, match="same-batch readback"):
        send(f, "S04-alerts", context_readback=s04_gate(f, context=True))
    assert len(f.calls) == 1 and not (f.prepared / "receipts/S04-alerts.json").exists()


def test_s04_requires_prior_snapshot_in_selected_profile(fixture):
    fixture.profile_path.write_bytes(json_bytes({**fixture.profile, "phase_set": "S04"}))
    with pytest.raises(ValueError, match="frozen prior"):
        prepare(fixture)
    assert not fixture.prepared.exists()
