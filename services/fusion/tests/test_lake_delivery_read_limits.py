"""Direct checks for execution limits without changing bound selection policies."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.services.lake_alert_delivery import (
    FIELDS,
    DeliveryPolicy,
    LakeDeliverySource,
    binding_digest,
)
from app.services.lake_alert_receiver import ReceivePolicy
from app.services.lake_alert_selection import SelectionPolicy


@pytest.fixture
def policies():
    root = Path(__file__).resolve().parents[3] / "deploy/aisoc21"
    return (SelectionPolicy.load(root / "lake-alert-selection-4a/selection.example.json"),
        ReceivePolicy.load(root / "lake-alert-receive-4b/receive.example.json"),
        DeliveryPolicy.load(root / "lake-alert-delivery-4c/delivery.example.json"))


def load_policy(tmp_path, body):
    path = tmp_path / "delivery.json"
    path.write_text(json.dumps(body))
    return DeliveryPolicy.load(path)


def test_legacy_fallback_and_explicit_limits_leave_bound_inputs_unchanged(policies, tmp_path):
    selection, receive, policy = policies
    original = copy.deepcopy((selection.body, receive.body))
    binding = binding_digest(selection, receive)
    legacy = copy.deepcopy(policy.body)
    legacy.pop("read_limits", None)
    old = load_policy(tmp_path, legacy)
    assert old.read_limits(selection) == selection.body["read_limits"]
    explicit = {key: value + 1 for key, value in selection.body["read_limits"].items()}
    updated = load_policy(tmp_path, {**legacy, "read_limits": explicit})
    assert updated.read_limits(selection) == explicit
    returned = updated.read_limits(selection)
    returned["max_records"] += 1
    assert updated.read_limits(selection) == explicit
    assert (selection.body, receive.body) == original
    assert binding_digest(selection, receive) == binding


@pytest.mark.parametrize("change", ["missing", "unknown", "boolean", "nonpositive", "string"])
def test_explicit_limits_must_be_complete_positive_integers(policies, tmp_path, change):
    selection, _, policy = policies
    body = copy.deepcopy(policy.body)
    limits = dict(selection.body["read_limits"])
    if change == "missing":
        limits.pop("max_records")
    elif change == "unknown":
        limits["unknown"] = 1
    else:
        limits["max_records"] = {"boolean": True, "nonpositive": 0, "string": "1"}[change]
    body["read_limits"] = limits
    with pytest.raises(ValueError, match="read_limits"):
        load_policy(tmp_path, body)


def test_scan_uses_execution_bounds_and_preserves_native_guard(policies):
    selection, _, policy = policies
    limits = {**policy.read_limits(selection), "max_records": 2}

    class Client:
        def __init__(self, count):
            self.count, self.calls = count, []

        def execute(self, sql, params, *, settings):
            self.calls.append((sql, params, settings))
            return [(self.count,)] if "uniqExact" in sql else [(None,) * len(FIELDS)] * self.count

    client = Client(2)
    source = LakeDeliverySource(client, selection, read_limits=limits)
    assert source.selection is selection and len(source._scan()) == 2
    for _, params, settings in client.calls:
        assert all(params[key] == value for key, value in selection.scope().items())
        assert settings == {"readonly": 2, "max_execution_time": limits["query_timeout_seconds"],
            "max_result_rows": 3, "max_result_bytes": limits["max_result_bytes"], "result_overflow_mode": "throw"}
    over = Client(3)
    with pytest.raises(ValueError, match="lake_delivery_scan_exceeds_limit"):
        LakeDeliverySource(over, selection, read_limits=limits)._scan()
    assert len(over.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("explicit", [False, True])
async def test_open_delivery_wires_same_limits_to_client_and_scan(policies, tmp_path, monkeypatch, explicit):
    from app.workers import lake_alert_delivery as worker

    selection, receive, original = policies
    body = copy.deepcopy(original.body)
    body["enabled"] = True
    body.pop("read_limits", None)
    if explicit:
        body["read_limits"] = {key: value + 1 for key, value in selection.body["read_limits"].items()}
    policy = load_policy(tmp_path, body)
    expected = policy.read_limits(selection)
    binding = binding_digest(selection, receive)
    captured = {}

    async def noop(*args, **kwargs):
        return None

    class Client:
        def __init__(self, **kwargs):
            captured["client"] = kwargs

        def disconnect(self):
            captured["disconnected"] = True

    class Sink:
        def __init__(self, *args, **kwargs):
            self.material_max_bytes = kwargs["material_max_bytes"]
            self.snapshot_max_bytes = kwargs["snapshot_max_bytes"]
            self.analysis_policy = kwargs["analysis_policy"]

        async def stop(self):
            captured["sink_stopped"] = True

    cache = SimpleNamespace(ping=noop, aclose=noop)
    config = {"clickhouse": {}, "postgres_dsn": "unused", "postgres_pool_size": 2,
        "postgres_connect_timeout_seconds": 1, "redis": {"url": "unused", "connect_timeout_seconds": 1, "socket_timeout_seconds": 1}}
    monkeypatch.setattr(worker, "configure_logging", lambda: None)
    monkeypatch.setattr(worker, "structlog", SimpleNamespace(configure=lambda **kwargs: None, make_filtering_bound_logger=lambda value: value))
    monkeypatch.setattr(worker, "settings", SimpleNamespace(operational_logging_profile_file=None))
    monkeypatch.setattr(worker.DeliveryPolicy, "load", lambda path: policy)
    monkeypatch.setattr(worker.SelectionPolicy, "load", lambda path: selection)
    monkeypatch.setattr(worker.ReceivePolicy, "load", lambda path: receive)
    monkeypatch.setattr(worker, "connections", lambda *args: config)
    monkeypatch.setattr(worker, "Client", Client)
    monkeypatch.setattr(worker, "redis", SimpleNamespace(from_url=lambda *args, **kwargs: cache))
    monkeypatch.setattr(worker, "asyncpg", SimpleNamespace(create_pool=noop))
    monkeypatch.setattr(worker, "Socai2AlertSink", Sink)
    for name in ("Deduplicator", "Correlator", "ConfidenceScorer", "FusionEngine"):
        monkeypatch.setattr(worker, name, lambda *args, **kwargs: None)
    async with worker.open_delivery(tmp_path / "delivery.json") as delivery:
        assert delivery.source.read_limits == expected
        assert captured["client"]["connect_timeout"] == expected["connect_timeout_seconds"]
        assert captured["client"]["send_receive_timeout"] == expected["send_receive_timeout_seconds"]
        assert delivery.source.selection is delivery.receiver.selection is delivery.store.selection is selection
        assert delivery.store.binding == binding
    assert captured["disconnected"] and captured["sink_stopped"]
