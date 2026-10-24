#!/usr/bin/env python3
"""One offline network-observation fixture; no backend or model calls.

The normalized envelope is compatible with Fusion's v1 envelope contract. This
does not claim full OCSF-standard validation or that a connection succeeded.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from alert_scenarios import RUN_ID, SOURCE, _event_time, _load_payloads, _without_answers, json_bytes, sha256
from alert_kafka import source_wire

FIXTURE_KIND = "socai2-investigation-network-observation/v1"
CONNECTOR = "socai2-investigation-fixture"
SCENARIO = "network-observation"
SOURCE_IP = "192.0.2.70"
DEST_IP = "198.51.100.70"
CONTROL_DEST_IP = "198.51.100.71"
ACTION = "network_connection_observed"


def _parameters(run_id: str, tenant: str, window_start: str) -> tuple[str, datetime]:
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError("run-id must be 1..64 letters, digits, dots, underscores or hyphens")
    tenant = str(UUID(tenant))
    start = datetime.fromisoformat(_event_time(window_start))
    # Keep all three samples within the supported fixture/DateTime64 interval.
    if not 1971 <= start.year <= 2099:
        raise ValueError("fixture window year must be 1971..2099")
    return tenant, start


def _identity(tenant: str, run_id: str, role: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"socai2:investigation-fixture:v1:{tenant}:{run_id}:{role}"))


def _build(*, run_id: str, tenant: str, window_start: str) -> tuple[dict[str, Any], dict[str, bytes]]:
    tenant, start = _parameters(run_id, tenant, window_start)
    hostname = f"{run_id}-host"
    connector_id = _identity(tenant, run_id, "connector")
    alert_id = _identity(tenant, run_id, "alert")
    events = []
    for role, minutes, destination in (
        ("matching-event", 1, DEST_IP),
        ("different-target-event", 2, CONTROL_DEST_IP),
        ("outside-window-event", -1, DEST_IP),
    ):
        event_id = _identity(tenant, run_id, role)
        when = (start + timedelta(minutes=minutes)).isoformat()
        raw = {
            "event_id": event_id, "tenant_id": tenant, "event_time": when,
            "source": CONNECTOR, "connector_id": connector_id, "synthetic": True,
            "hostname": hostname, "source_ip": SOURCE_IP, "dest_ip": destination,
            "src_port": 51470, "dst_port": 443, "protocol": "TCP",
            "action": ACTION, "outcome": "unknown",
        }
        ocsf = {
            "uid": event_id, "tenant_uid": tenant, "time": when,
            "class_uid": 4001, "category_uid": 4, "activity_id": 0,
            "severity_id": 1, "severity": "Informational",
            "metadata": {"uid": event_id, "product": {"name": CONNECTOR,
                         "vendor_name": "socai2 synthetic fixture"}},
            "device": {"name": hostname},
            "src_endpoint": {"ip": SOURCE_IP, "hostname": hostname, "port": 51470},
            "dst_endpoint": {"ip": destination, "port": 443}, "protocol": "TCP",
            "activity": {"action": ACTION, "outcome": "unknown"},
            "raw_data": json_bytes(raw).decode("utf-8"),
        }
        events.append({"schema_version": "v1", "id": event_id, "tenant_id": tenant,
                       "connector_id": connector_id, "connector_type": CONNECTOR,
                       "ocsf_event": ocsf})
    payload = {
        "schema_version": "v1", "id": alert_id, "tenant_id": tenant, "source": SOURCE,
        "title": "Synthetic network observation requiring fact verification",
        "description": "A synthetic source reported a network observation; its outcome is unknown.",
        "severity": "medium", "event_time": events[0]["ocsf_event"]["time"],
        "created_at": events[0]["ocsf_event"]["time"],
        "hostname": hostname, "src_ip": SOURCE_IP, "dst_ip": DEST_IP,
        "connector_id": connector_id, "connector_type": CONNECTOR, "ocsf_class_uid": 4001,
        "source_event_ids": [events[0]["id"]], "tags": ["synthetic", f"run:{run_id}"],
        "raw_event": {"synthetic": True, "run_id": run_id, "scenario_id": SCENARIO,
                      "telemetry": [json.loads(events[0]["ocsf_event"]["raw_data"])]},
    }
    _without_answers(payload)
    source_wire(payload, tenant)  # Validate the actual RawAlert/source-v1 contract, offline.
    expected = {
        "scenario_id": SCENARIO, "alert_id": alert_id, "synthetic": True,
        "expectation_source": "authored fixture assertions; not observed backend results",
        "matching_event_ids": [events[0]["id"]],
        "excluded_events": [{"event_id": events[1]["id"], "reason": "different_destination"},
                            {"event_id": events[2]["id"], "reason": "outside_window"}],
        "connection_success": "unknown", "behavior_nature": "unresolved",
        "authorization_status": "unknown",
    }
    files = {"payloads/001.json": json_bytes(payload), "expected/001.json": json_bytes(expected)}
    event_records = []
    for index, event in enumerate(events, 1):
        _without_answers(event)
        path = f"events/{index:03d}.json"
        files[path] = json_bytes(event)
        event_records.append({
            "event_id": event["id"], "event": path, "event_sha256": sha256(files[path]),
            "raw_payload_sha256": sha256(event["ocsf_event"]["raw_data"].encode("utf-8")),
            # Match the original LakeWriter's exact JSON serialization, not json_bytes.
            "ocsf_json_sha256": sha256(json.dumps(json.loads(files[path])["ocsf_event"],
                                                   default=str).encode("utf-8")),
        })
    manifest = {
        "schema_version": "socai2-existing-alert-fixtures/v1", "fixture_kind": FIXTURE_KIND,
        "run_id": run_id, "tenant_id": tenant, "event_time": payload["event_time"],
        "count": 1, "event_count": 3, "mode": "synthetic-existing-alerts",
        "source": {"generator": "tools/testdata/investigation_fixture.py", "version": "v1"},
        "records": [{"scenario_id": SCENARIO, "alert_id": alert_id,
                     "payload": "payloads/001.json", "payload_sha256": sha256(files["payloads/001.json"]),
                     "expected": "expected/001.json", "expected_sha256": sha256(files["expected/001.json"])}],
        "events": event_records,
        "query_context": {"tenant_id": tenant, "hostname": hostname, "source_ip": SOURCE_IP,
                          "dest_ip": DEST_IP, "dst_port": 443, "protocol": "TCP",
                          "window_start": start.isoformat(),
                          "window_end": (start + timedelta(minutes=5)).isoformat(),
                          "window_bounds": "start_inclusive_end_exclusive"},
        "limitations": ["Synthetic observation only; no connection success, malice or authorization is asserted.",
                        "No backend, broker, model or business request runs during generation.",
                        "Fusion envelope compatibility is not complete OCSF-standard validation."],
    }
    return manifest, files


def generate_fixture(*, run_id: str, tenant: str, window_start: str, out: Path) -> dict[str, Any]:
    """Build all bounded materials before creating a fresh output directory."""
    out = Path(out)
    if out.exists():
        raise FileExistsError("output directory already exists; choose a new directory")
    manifest, files = _build(run_id=run_id, tenant=tenant, window_start=window_start)
    out.mkdir(parents=True, exist_ok=False)
    for directory in ("payloads", "events", "expected"):
        (out / directory).mkdir()
    for name, data in files.items():
        (out / name).write_bytes(data)
    (out / "manifest.json").write_bytes(json_bytes(manifest))
    validate_fixture(out)
    return manifest


def _read_file(input_dir: Path, name: str) -> bytes:
    """Only fixed fixture paths are passed here; reject redirected directories too."""
    path = input_dir / name
    for candidate in (input_dir, path.parent, path):
        if candidate.is_symlink() or candidate.is_junction():
            raise ValueError("fixture symlinks and junctions are not accepted")
    if path.stat().st_size > 65536:
        raise ValueError("fixture file exceeds 64 KiB")
    return path.read_bytes()


def load_fixture(input_dir: Path, *, tenant: str | None = None
                 ) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate send materials without ever opening expected/ (also safe if absent).

    The exact versioned recipe checks identity, fields, source linkage, absolute
    windows and hashes even if a modified file's manifest hash was recomputed.
    D2 callers should provide their independently selected test tenant.
    """
    input_dir = Path(input_dir)
    manifest = json.loads(_read_file(input_dir, "manifest.json"))
    if not isinstance(manifest, dict) or manifest.get("fixture_kind") != FIXTURE_KIND:
        raise ValueError("unsupported investigation fixture")
    try:
        canonical, files = _build(run_id=manifest["run_id"], tenant=manifest["tenant_id"],
                                 window_start=manifest["query_context"]["window_start"])
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("invalid fixture parameters") from exc
    if tenant is not None and str(UUID(tenant)) != manifest["tenant_id"]:
        raise ValueError("fixture differs from explicit test tenant")
    if manifest != canonical:
        raise ValueError("fixture manifest differs from the bounded v1 recipe")
    for name, expected_data in files.items():
        if not name.startswith("expected/") and _read_file(input_dir, name) != expected_data:
            raise ValueError(f"fixture content/hash mismatch: {name}")
    # Retain compatibility with the original alert sender, including answer checks.
    _, payloads = _load_payloads(input_dir)
    events = [json.loads(files[record["event"]]) for record in manifest["events"]]
    return manifest, payloads, events


def validate_fixture(input_dir: Path) -> dict[str, Any]:
    """Offline validation includes expected-file integrity; not a transport loader."""
    manifest, _, _ = load_fixture(input_dir)
    record = manifest["records"][0]
    if sha256(_read_file(Path(input_dir), record["expected"])) != record["expected_sha256"]:
        raise ValueError("expected file hash mismatch")
    return {"run_id": manifest["run_id"], "tenant_id": manifest["tenant_id"],
            "alerts": 1, "events": 3, "status": "offline_fixture_validated"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate", help="create one bounded offline fixture")
    generate.add_argument("--run-id", required=True)
    generate.add_argument("--tenant", required=True)
    generate.add_argument("--window-start", required=True)
    generate.add_argument("--out", required=True, type=Path)
    args = vars(parser.parse_args())
    args.pop("command")
    result = generate_fixture(**args)
    print(json.dumps({"run_id": result["run_id"], "alerts": result["count"],
                      "events": result["event_count"], "status": "generated_offline"}))


if __name__ == "__main__":
    main()
