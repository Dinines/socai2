"""B1/I3 HTTP/Kafka ordering with real processing code and memory boundaries.

PG, Redis, Kafka delivery and enrichment are explicit doubles. No external
service, model call, or Kafka offset is used by this suite.
"""

from __future__ import annotations

import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api import router as router_module
from app.core.config import settings
from app.models.alert import RawAlert
from app.security.tenant_scope import TenantPrincipal, require_console_or_service_auth
from app.services.alert_sink import PersistOutcome, PersistResult
from app.services.correlator import Correlator
from app.services.deduplicator import Deduplicator
from app.services.delivery_recovery import SnapshotLookup
from app.services.fusion_engine import FusionEngine
from app.workers.consumer import FusionWorker


TENANT = UUID(int=301)


class MemoryRedis:
    def __init__(self):
        self.data = {}

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, *, ex=None, nx=False):
        if nx and key in self.data:
            return None
        self.data[key] = value.encode() if isinstance(value, str) else value
        return True


class MemorySink:
    def __init__(self):
        self.rows = {}
        self.lookup_calls = 0

    async def lookup_delivery(self, alert):
        self.lookup_calls += 1
        snapshot = self.rows.get(alert.id)
        return SnapshotLookup(snapshot is not None, copy.deepcopy(snapshot), str(alert.id))

    async def persist(self, fused, *, replay, delivery_snapshot):
        if fused.id in self.rows:
            return PersistResult(PersistOutcome.DUPLICATE, str(fused.id))
        self.rows[fused.id] = copy.deepcopy(delivery_snapshot)
        return PersistResult(PersistOutcome.INSERTED, str(fused.id))


def worker_fixture():
    redis = MemoryRedis()

    async def score(fused):
        return fused

    enricher = SimpleNamespace(enrich=AsyncMock(return_value={"test_evidence": {"first": True}}))
    engine = FusionEngine(
        Deduplicator(redis), Correlator(redis),
        ml_scorer=SimpleNamespace(score=AsyncMock(side_effect=score)), enricher=enricher,
    )
    engine.process = AsyncMock(wraps=engine.process)
    sink = MemorySink()
    worker = FusionWorker(engine, sink=sink)
    worker._producer = SimpleNamespace(send_and_wait=AsyncMock())
    return worker, sink, redis


def client_for(worker, tenant=TENANT):
    router_module.set_worker(worker)
    app = FastAPI()
    app.include_router(router_module.router)
    app.dependency_overrides[require_console_or_service_auth] = lambda: TenantPrincipal(
        tenant_ids=frozenset({tenant}), subject="b1-i3-test",
    )
    return AsyncClient(transport=ASGITransport(app), base_url="http://fusion")


def payload(version):
    return {
        "id": str(UUID(int=302)), "tenant_id": str(TENANT),
        "identity_version": version,
        "source_alert_id": str(UUID(int=302)) if version == "source-v1" else None,
        "source": "b1-i3-fixture", "title": "Original finding",
        "description": "First description", "hostname": "b1-i3-host",
        "event_time": "2026-10-21T01:02:03Z",
        "source_event_ids": ["first-event"], "raw_event": {"first": True},
    }


@pytest.fixture(autouse=True)
def reset_worker():
    yield
    router_module._worker_ref = None


@pytest.mark.parametrize("first_entry", ["http", "kafka"])
@pytest.mark.parametrize("version", ["legacy-v1", "source-v1"])
@pytest.mark.asyncio
async def test_entries_share_canonical_identity_and_complete_first_result(first_entry, version):
    worker, sink, _ = worker_fixture()
    original = payload(version)
    canonical_id = RawAlert.model_validate(original).deterministic_id()
    replay = {**original, "description": "Later description", "raw_event": {"later": True},
              "event_time": "2026-10-21T09:10:11Z"}

    async with client_for(worker) as client:
        if first_entry == "http":
            response = await client.post("/process", json=original)
            assert response.status_code == 200
            await worker._process_message(replay, topic=settings.kafka_topic_alerts_raw)
        else:
            await worker._process_message(original, topic=settings.kafka_topic_alerts_raw)
            response = await client.post("/process", json=replay)
            assert response.status_code == 200

    publications = [call.kwargs["value"] for call in worker._producer.send_and_wait.await_args_list]
    assert len(publications) == 2
    first, second = publications
    assert first["persist_outcome"] == "inserted"
    assert second["persist_outcome"] == "duplicate"
    assert first["alert_row_id"] == second["alert_row_id"] == str(canonical_id)
    expected = {key: value for key, value in first.items() if key not in {"alert_row_id", "persist_outcome"}}
    assert response.json() == expected
    assert {key: value for key, value in second.items() if key not in {"alert_row_id", "persist_outcome"}} == expected
    assert expected["id"] == expected["alert"]["id"] == str(canonical_id)
    assert expected["alert"]["description"] == "First description"
    assert expected["alert"]["raw_event"] == {"first": True}
    assert expected["incident_id"] is not None
    assert expected["enrichments"] == {"test_evidence": {"first": True}}
    assert len(sink.rows) == 1
    worker.engine.process.assert_awaited_once()
    worker.engine._enricher.enrich.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_refuses_other_tenant_before_any_processing_write():
    worker, sink, redis = worker_fixture()
    async with client_for(worker, tenant=UUID(int=999)) as client:
        response = await client.post("/process", json=payload("source-v1"))
    assert response.status_code == 403
    assert sink.lookup_calls == 0 and not sink.rows and not redis.data
    worker.engine.process.assert_not_awaited()
    worker._producer.send_and_wait.assert_not_awaited()
