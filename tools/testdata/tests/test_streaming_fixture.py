"""S01/S04 offline contracts against current Fusion schemas and lake mapping."""
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/testdata"))
sys.path.insert(0, str(ROOT / "services/fusion"))
import streaming_fixture as fixture
from alert_kafka import raw_alert_model
from alert_scenarios import json_bytes, sha256
from app.services.event_schema import (
    validate_raw_alert,
    validate_raw_event,
)
from app.services.lake_writer import event_to_row


@pytest.fixture
def config():
    return json.loads((ROOT / "tools/testdata/streaming-fixture.example.json").read_text())


def records(inputs, suffix):
    return [json.loads(line) for p, data in inputs.items() if p.endswith(suffix)
            for line in data.splitlines()]


def test_offline_deterministic_and_reusable_with_new_batch(config, tmp_path):
    with patch("socket.socket", side_effect=AssertionError("offline only")):
        result = fixture.generate(config, tmp_path / "one")
        fixture.generate({**config, "base_time": "2026-11-15T12:00:00+08:00"}, tmp_path / "two")
        fixture.validate(tmp_path / "one")
    for path in (tmp_path / "one").rglob("*"):
        if path.is_file():
            assert path.read_bytes() == (tmp_path / "two" / path.relative_to(tmp_path / "one")).read_bytes()
    assert result["kafka_sends"] == result["model_calls"] == result["business_connections"] == 0
    _, m1, _, _ = fixture.build(config)
    _, m2, _, _ = fixture.build({**config, "batch_id": "new-test-batch"})
    assert set(m1["logical_ids"].values()).isdisjoint(m2["logical_ids"].values())
    assert len(set(m1["logical_ids"].values())) == 17


def test_wire_source_and_correlation_contracts(config):
    _, manifest, inputs, _ = fixture.build(config)
    alerts = records(inputs, "alerts.jsonl")
    events = {e["event_id"]: e for e in records(inputs, "context-events.jsonl")}
    assert [len(inputs[f"{s}/alerts.jsonl"].splitlines()) for s in ("S01", "S04")] == [3, 1]
    keys = []
    for alert, source in zip(alerts, ("E02", "E04", "E05", "E13"), strict=True):
        parsed = raw_alert_model().model_validate(alert)
        assert validate_raw_alert(alert).ok
        assert alert["identity_version"] == "source-v1"
        assert alert["source_alert_id"] == alert["id"]
        assert alert["source_event_ids"] == [manifest["logical_ids"][source]]
        assert alert["raw_event"]["ocsf_event"] == events[alert["source_event_ids"][0]]["ocsf_event"]
        assert parsed.correlation_entity() == ("ip", config["source_ip"])
        keys.append(parsed.correlation_key())
        assert datetime.fromisoformat(alert["created_at"]) - datetime.fromisoformat(alert["event_time"]) == timedelta(seconds=1)
    assert len(set(keys)) == 1
    changed = raw_alert_model().model_validate({**alerts[0], "mitre_tactics": ["Execution"]})
    assert changed.correlation_key() != keys[0]


def test_actual_lake_mapping_preserves_source_time_and_values(config):
    _, manifest, inputs, _ = fixture.build(config)
    events = records(inputs, "context-events.jsonl")
    assert len(events) == 13
    for event in events:
        assert validate_raw_event(event).ok
        row = event_to_row(event)
        ocsf = event["ocsf_event"]
        raw = json.loads(row["raw_payload"])
        assert row["event_id"] == ocsf["uid"] == raw["uid"] == event["event_id"]
        assert row["tenant_id"] == ocsf["tenant_uid"] == raw["tenant_uid"]
        assert row["event_time"].replace(tzinfo=UTC) == datetime.fromisoformat(raw["time"])
        assert raw["time"] == ocsf["time"]
        assert row["src_hostname"] == raw["device"]["name"]
        assert row["user_name"] == raw["actor"]["user"]["name"]
        assert row["class_uid"] == ocsf["class_uid"]
    zero = next(e for e in events if e["event_id"] == manifest["logical_ids"]["E07"])
    stored = json.loads(event_to_row(zero)["ocsf_json"])
    assert stored["traffic"] == {"bytes_out": 0, "bytes_in": 0, "packets_out": 0, "packets_in": 0}
    assert stored["sensor_observation"] == {"connection_reset": False, "dns_answers": []}
    assert stored["activity"]["outcome"] == "unknown"


def test_independent_host_window_predicate_matches_frozen_expectations(config):
    _, manifest, inputs, controls = fixture.build(config)
    expected = json.loads(controls["expected.json"])
    rows = [event_to_row(e) for e in records(inputs, "context-events.jsonl")]
    reverse = {v: k for k, v in manifest["logical_ids"].items()}
    kinds = {"authentication_activity": 3002, "process_activity": 1007, "network_connections": 4001}
    for name, query in expected["queries"].items():
        start, end = (datetime.fromisoformat(query[k]) for k in ("window_start", "window_end"))
        # E13 is prepared only in S04; it does not exist in the first query's source.
        available = [r for r in rows if not (name.startswith("S01") and reverse[r["event_id"]] == "E13")]
        for tool, class_uid in kinds.items():
            matched = {reverse[r["event_id"]] for r in available
                       if r["tenant_id"] == query["tenant_id"] and r["src_hostname"] == query["hostname"]
                       and r["class_uid"] == class_uid and start <= r["event_time"].replace(tzinfo=UTC) < end}
            assert matched == set(query["included"][tool]), (name, tool, matched)
    assert "E12" in expected["queries"]["S01_full_host"]["included"]["authentication_activity"]
    assert "E11" not in expected["queries"]["S01_full_host"]["included"]["network_connections"]
    assert "E11" in expected["queries"]["S04_full_host"]["included"]["network_connections"]


def test_input_loader_does_not_open_expected_or_actual_results(config, tmp_path):
    fixture.generate(config, tmp_path / "batch")
    for name in ("expected.json", "identity-map.json", "actions.json"):
        (tmp_path / "batch" / name).unlink()
    _, manifest, inputs = fixture.load_inputs(tmp_path / "batch")
    assert not manifest["live_ready"]
    for token in (b"predicted_canonical_alert_ids", b"logical_group", b"model_verdict", b"expected"):
        assert all(token not in value for value in inputs.values())


def test_refuses_overwrite_and_rehashed_input_changes(config, tmp_path):
    out = tmp_path / "batch"
    fixture.generate(config, out)
    with pytest.raises(FileExistsError):
        fixture.generate(config, out)
    path = out / "S01/alerts.jsonl"
    values = [json.loads(x) for x in path.read_text().splitlines()]
    values[0]["source_event_ids"] = []
    path.write_bytes(fixture._jsonl(values))
    manifest = json.loads((out / "manifest.json").read_text())
    manifest["inputs"]["S01/alerts.jsonl"] = sha256(path.read_bytes())
    (out / "manifest.json").write_bytes(json_bytes(manifest))
    with pytest.raises(ValueError, match="manifest"):
        fixture.load_inputs(out)


@pytest.mark.parametrize("change", [
    {"base_time": "2026-11-15T04:00:00"},
    {"tenant_id": "11111111-1111-4111-8111-111111111111"},
    {"source_ip": "192.168.1.21"},
])
def test_invalid_configuration_has_no_partial_output(config, change, tmp_path):
    with pytest.raises(ValueError):
        fixture.generate({**config, **change}, tmp_path / "rejected")
    assert not (tmp_path / "rejected").exists()


def test_no_business_identity_or_runtime_readiness_is_fabricated(config):
    _, manifest, _, controls = fixture.build(config)
    assert json.loads(controls["identity-map.json"])["actual_mappings"] == []
    assert manifest["execution_status"] == "offline_only" and not manifest["live_ready"]
    expected = json.loads(controls["expected.json"])
    assert expected["correlation"]["runtime_status"] == "blocked_dependency"
    assert expected["processing_confirmed"] is False
    assert all("incident_id" not in key and "run_id" not in key for key in manifest["logical_ids"])


def test_candidate_progress_flags_do_not_change_materials_but_target_change_does(config):
    original = Path.read_text
    identity_path = ROOT / config["candidate_identity"]
    identity = json.loads(identity_path.read_text())
    before = fixture.build(config)

    def read(path, *args, **kwargs):
        return json.dumps(identity) if path == identity_path else original(path, *args, **kwargs)

    with patch.object(Path, "read_text", read):
        identity["state"] = "candidate_http_ready"
        identity["credentials_created"] = not identity["credentials_created"]
        assert fixture.build(config) == before
        identity["postgres"]["database"] = "different_candidate"
        assert fixture.build(config)[1]["candidate_binding"] != before[1]["candidate_binding"]
