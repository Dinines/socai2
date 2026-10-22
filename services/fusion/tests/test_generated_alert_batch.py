"""Original Fusion processes generated alerts with memory storage/transport.

The generator's answer key never enters production processing. No model runs.
"""
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.core.config import settings
from app.models.alert import RawAlert
from app.services.correlator import Correlator
from app.services.deduplicator import Deduplicator
from app.services.fusion_engine import FusionEngine
from app.workers.consumer import FusionWorker
from .test_process_delivery import MemoryRedis, MemorySink

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("testdata_fusion_adapter", ROOT / "tools/testdata/alert_scenarios.py")
adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = adapter
spec.loader.exec_module(adapter)
TENANT = UUID("30a948cc-fb41-420b-bc3d-d4af8e26a001")


@pytest.mark.asyncio
async def test_generated_batch_is_preserved_as_distinct_fused_alerts(tmp_path):
    out = tmp_path / "batch"
    manifest = adapter.generate_batch(run_id="contract-fusion-20261022", tenant=str(TENANT),
        event_time="2026-10-22T06:00:00Z", count=3, out=out)
    redis = MemoryRedis()
    sink = MemorySink()
    worker = FusionWorker(FusionEngine(Deduplicator(redis), Correlator(redis)), sink=sink)
    worker._producer = SimpleNamespace(send_and_wait=AsyncMock())
    for record in manifest["records"]:
        payload = json.loads((out / record["payload"]).read_text())
        # This is exactly the API's server-bound identity envelope.
        wire = {**payload, "tenant_id": str(TENANT), "identity_version": "source-v1", "source_alert_id": payload["id"]}
        expected_id = RawAlert.model_validate(wire).deterministic_id()
        await worker._process_message(wire, topic=settings.kafka_topic_alerts_raw)
        fused = worker._producer.send_and_wait.await_args.kwargs["value"]
        assert fused["id"] == fused["alert_row_id"] == str(expected_id)
        assert fused["persist_outcome"] == "inserted"
        assert fused["alert"]["source_alert_id"] == payload["id"]
        assert fused["alert"]["raw_event"] == payload["raw_event"]
        assert fused["alert"]["event_time"] == RawAlert.model_validate(wire).model_dump(mode="json")["event_time"]
        assert fused["incident_id"]
        assert sink.rows[expected_id]["fused"]["id"] == str(expected_id)
        assert all(key not in json.dumps(fused) for key in ("expected_tactics", "expected_techniques", "response_class", "evidence_keywords"))
    assert len(sink.rows) == worker._producer.send_and_wait.await_count == 3

