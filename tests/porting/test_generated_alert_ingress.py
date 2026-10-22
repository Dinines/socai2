"""Generated payloads traverse the real API route; auth/PG/Kafka are doubles.

This proves HTTP/schema/canonical-envelope compatibility, not a live delivery.
"""
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest

from app.api.v1.endpoints import alert_ingress
from app.api.v1.deps import get_db
from app.schemas.fusion_alert import RawAlert

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("testdata_ingress_adapter", ROOT / "tools/testdata/alert_scenarios.py")
adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = adapter
spec.loader.exec_module(adapter)
TENANT = UUID("30a948cc-fb41-420b-bc3d-d4af8e26a001")


@pytest.mark.asyncio
async def test_generated_batch_passes_actual_ingress_and_keeps_answer_key_separate(tmp_path, monkeypatch):
    out = tmp_path / "batch"
    manifest = adapter.generate_batch(run_id="contract-ingress-20261022", tenant=str(TENANT),
        event_time="2026-10-22T06:00:00Z", count=3, out=out)
    monkeypatch.setenv("AISOC_ALERT_IDENTITY_VERSION", "source-v1")
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "memory.invalid:9092")
    monkeypatch.setenv("KAFKA_TOPIC_ALERTS_RAW", "testdata.contract.raw")
    producer = AsyncMock()
    producer.send_and_wait.side_effect = [SimpleNamespace(topic="testdata.contract.raw", partition=0, offset=i) for i in range(3)]
    monkeypatch.setattr(alert_ingress, "AIOKafkaProducer", lambda **kw: producer)

    class NoLegacy:
        async def execute(self, query):
            return SimpleNamespace(scalar_one_or_none=lambda: None)

    async def db():
        yield NoLegacy()

    app = FastAPI()
    app.include_router(alert_ingress.router, prefix="/api/v1")
    principal_dependency = next(d.call for d in alert_ingress.router.routes[0].dependant.dependencies if d.name == "user")
    app.dependency_overrides[principal_dependency] = lambda: SimpleNamespace(tenant_id=TENANT)
    app.dependency_overrides[get_db] = db
    canonical = set()
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        for record in manifest["records"]:
            payload = json.loads((out / record["payload"]).read_text())
            response = await client.post("/api/v1/alert-ingress", json=payload)
            assert response.status_code == 202, response.text
            receipt = response.json()
            wire = json.loads(producer.send_and_wait.await_args.args[1])
            expected_id = str(RawAlert.model_validate(wire).deterministic_id())
            assert receipt["canonical_alert_id"] == expected_id
            assert receipt["processing_confirmed"] is False
            assert wire["identity_version"] == "source-v1"
            assert wire["source_alert_id"] == payload["id"]
            assert wire["tenant_id"] == str(TENANT)
            assert wire["raw_event"] == payload["raw_event"]
            assert all(key not in json.dumps(wire) for key in ("expected_tactics", "expected_techniques", "response_class", "evidence_keywords"))
            assert json.loads((out / record["expected"]).read_text())
            canonical.add(expected_id)
        # Same generated data cannot be presented as belonging to another tenant.
        other = {**payload, "tenant_id": str(UUID(int=999))}
        assert (await client.post("/api/v1/alert-ingress", json=other)).status_code == 403
    assert len(canonical) == producer.send_and_wait.await_count == 3

