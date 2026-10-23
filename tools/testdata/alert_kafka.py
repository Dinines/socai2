"""Explicit source-v1 wire preparation and bounded Kafka transport for test fixtures."""
from __future__ import annotations

import importlib.util
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any
from uuid import UUID

from alert_scenarios import _load_payloads, _without_answers, json_bytes, sha256

ROOT = Path(__file__).resolve().parents[2]


def raw_alert_model():
    """Load the actual wire/identity model without importing a service's `app`."""
    name = "socai2_testdata_fusion_alert_model"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / "services/fusion/app/models/alert.py")
        if spec is None or spec.loader is None:
            raise ValueError("Fusion alert model unavailable")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name].RawAlert


def source_wire(payload: dict[str, Any], tenant: str) -> tuple[dict[str, Any], str]:
    tenant = str(UUID(tenant))
    if payload.get("tenant_id") != tenant:
        raise ValueError("payload tenant differs from explicit test tenant")
    _without_answers(payload)
    if payload.get("identity_version", "source-v1") != "source-v1":
        raise ValueError("legacy identity is not accepted for a new test")
    if payload.get("source_alert_id", payload["id"]) != payload["id"]:
        raise ValueError("source ID differs from input ID")
    wire = {**payload, "identity_version": "source-v1", "source_alert_id": payload["id"]}
    parsed = raw_alert_model().model_validate(wire)
    return wire, str(parsed.deterministic_id())


def prepare_kafka(*, input_dir: Path, tenant: str, out: Path) -> dict[str, Any]:
    """Pure local conversion. Expected answers are never opened."""
    manifest, payloads = _load_payloads(Path(input_dir))
    tenant = str(UUID(tenant))
    if tenant != manifest["tenant_id"]:
        raise ValueError("explicit tenant differs from batch tenant")
    materials = [source_wire(payload, tenant) for payload in payloads]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    (out / "wire").mkdir()
    records = []
    for index, ((wire, canonical), original) in enumerate(zip(materials, manifest["records"]), 1):
        path = f"wire/{index:03d}.json"
        data = json_bytes(wire)
        (out / path).write_bytes(data)
        records.append({"alert_id": wire["id"], "scenario_id": original["scenario_id"],
                        "payload_sha256": original["payload_sha256"], "wire": path,
                        "wire_sha256": sha256(data), "predicted_canonical_alert_id": canonical})
    result = {"schema_version": "socai2-kafka-wire/v1", "run_id": manifest["run_id"],
              "tenant_id": tenant, "count": len(records), "records": records,
              "source_manifest_sha256": sha256((Path(input_dir) / "manifest.json").read_bytes()),
              "identity_model_sha256": sha256((ROOT / "services/fusion/app/models/alert.py").read_bytes()),
              "identity_prediction_only": True, "processing_confirmed": False}
    (out / "manifest.json").write_bytes(json_bytes(result))
    return result


def load_wire(wire_dir: Path, tenant: str) -> tuple[dict[str, Any], list[bytes]]:
    manifest = json.loads((wire_dir / "manifest.json").read_text())
    tenant = str(UUID(tenant))
    records = manifest.get("records")
    if (manifest.get("schema_version") != "socai2-kafka-wire/v1" or manifest.get("tenant_id") != tenant
            or not isinstance(records, list) or not 1 <= len(records) <= 20
            or manifest.get("count") != len(records)):
        raise ValueError("invalid wire manifest or test tenant")
    values = []
    identities = set()
    for index, record in enumerate(records, 1):
        if record.get("wire") != f"wire/{index:03d}.json":
            raise ValueError("unexpected wire path")
        path = wire_dir / record["wire"]
        if path.is_symlink():
            raise ValueError("wire symlinks are not accepted")
        data = path.read_bytes()
        if sha256(data) != record.get("wire_sha256"):
            raise ValueError("wire hash mismatch")
        payload = json.loads(data)
        wire, canonical = source_wire(payload, tenant)
        if (wire != payload or payload.get("id") != record.get("alert_id")
                or canonical != record.get("predicted_canonical_alert_id")
                or canonical in identities):
            raise ValueError("wire identity mismatch or duplicate")
        identities.add(canonical)
        values.append(data)
    return manifest, values


def kafka_config(env_file: Path) -> dict[str, Any]:
    """Read only explicit Kafka settings, using the service's existing TLS policy."""
    from dotenv import dotenv_values
    values = {k: v for k, v in dotenv_values(env_file).items() if k.startswith("KAFKA_") and v is not None}
    if not values.get("KAFKA_BOOTSTRAP_SERVERS") or not values.get("KAFKA_SECURITY_PROTOCOL"):
        raise ValueError("Kafka file must explicitly set bootstrap servers and security protocol")
    name = "socai2_testdata_kafka_transport"
    spec = importlib.util.spec_from_file_location(name, ROOT / "services/fusion/app/core/kafka_security.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    previous = {k: v for k, v in os.environ.items() if k.startswith("KAFKA_")}
    try:
        for key in previous:
            os.environ.pop(key)
        os.environ.update(values)
        transport = module.kafka_client_kwargs(environment="test")
    finally:
        for key in list(os.environ):
            if key.startswith("KAFKA_"):
                os.environ.pop(key)
        os.environ.update(previous)
    return {"bootstrap_servers": values["KAFKA_BOOTSTRAP_SERVERS"], **transport}


def _save_receipt(path: Path, state: dict[str, Any]) -> None:
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(json_bytes(state))
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


async def send_kafka(*, wire_dir: Path, tenant: str, topic: str, receipt: Path,
                     config: dict[str, Any], timeout: float = 20, producer_factory=None) -> dict[str, Any]:
    """Send one at a time; unknown ACK stops. Never application-retry or read answers."""
    manifest, values = load_wire(Path(wire_dir), tenant)
    if topic != f"socai2.testdata.{manifest['run_id']}.raw":
        raise ValueError("topic must be socai2.testdata.<run-id>.raw")
    if not 0 < timeout <= 60:
        raise ValueError("timeout must be 0..60 seconds")
    if not config.get("bootstrap_servers") or not config.get("security_protocol"):
        raise ValueError("Kafka transport must be explicit")
    if producer_factory is None:
        from aiokafka import AIOKafkaProducer
        producer_factory = AIOKafkaProducer
    receipt = Path(receipt)
    fd = os.open(receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    state = {"schema_version": "socai2-kafka-send/v1", "run_id": manifest["run_id"],
             "tenant_id": manifest["tenant_id"], "topic": topic, "requested": len(values),
             "accepted": 0, "not_attempted": len(values), "processing_confirmed": False,
             "wire_manifest_sha256": sha256((Path(wire_dir) / "manifest.json").read_bytes()),
             "transport": {"bootstrap_servers": config["bootstrap_servers"],
                           "security_protocol": config["security_protocol"]},
             "status": "starting", "records": [], "cleanup_errors": []}
    _save_receipt(receipt, state)
    producer = None
    try:
        producer = producer_factory(**config, acks="all", enable_idempotence=True,
                                    request_timeout_ms=min(int(timeout * 1000), 10000))
        await asyncio.wait_for(producer.start(), timeout)
        state["status"] = "running"
        for record, value in zip(manifest["records"], values):
            item = {"alert_id": record["alert_id"],
                    "predicted_canonical_alert_id": record["predicted_canonical_alert_id"],
                    "wire_sha256": record["wire_sha256"], "state": "started_outcome_unknown"}
            state["records"].append(item)
            state["not_attempted"] -= 1
            _save_receipt(receipt, state)
            metadata = await asyncio.wait_for(
                producer.send_and_wait(topic, value=value, key=tenant.encode()), timeout)
            if (metadata.topic != topic or type(metadata.partition) is not int or metadata.partition < 0
                    or type(metadata.offset) is not int or metadata.offset < 0):
                raise ValueError("broker confirmation does not match target")
            item.update(state="accepted_not_processed", message={"topic": metadata.topic,
                        "partition": metadata.partition, "offset": metadata.offset})
            state["accepted"] += 1
            _save_receipt(receipt, state)
        state["status"] = "accepted_only"
    except BaseException as exc:
        state.update(status="failed", error_type=type(exc).__name__)
        if state["records"] and state["records"][-1]["state"] == "started_outcome_unknown":
            state["records"][-1]["state"] = "outcome_unknown"
        _save_receipt(receipt, state)
        if not isinstance(exc, Exception):
            raise
    finally:
        if producer is not None:
            try:
                await asyncio.wait_for(producer.stop(), timeout)
            except BaseException as exc:
                state["cleanup_errors"].append(type(exc).__name__)
        _save_receipt(receipt, state)
    return state
