"""Executed only in the NEW API container, with a copied Fusion package in /tmp."""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

payload = json.load(sys.stdin)
assert payload["database"] == "socai2_next_20261104"
assert os.environ["SOCAI2_SERVICE_DATABASE_NAME"] == payload["database"]
root = Path("/tmp/socai2-next-acceptance-fusion-r1")
root.mkdir(exist_ok=False)
for name, body in payload["files"].items():
    path = root / name
    assert path.resolve().is_relative_to(root) and name.startswith("app/")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
sys.path.insert(0, str(root))
from app.models.alert import CorrelationBasis, FusedAlert, FusionDecision, RawAlert
from app.services.socai2_sink import Socai2AlertSink


async def main():
    sink = Socai2AlertSink(os.environ["DATABASE_URL"])
    await sink.start()
    try:
        assert sink._pool is not None
        async with sink._pool.acquire() as conn:
            assert await conn.fetchval("SELECT current_database()") == payload["database"]
        saved = []
        for entry in payload["alerts"]:
            alert = RawAlert.model_validate(entry)
            alert.id = alert.deterministic_id()
            now = datetime.fromisoformat(payload["event_time"])
            basis = CorrelationBasis(entity_type="host", entity_value=alert.hostname, tactic="Execution",
                correlation_key=alert.correlation_key(), window_seconds=300, max_alerts=20,
                decision="new_incident", reason="no_index", decided_at=now)
            fused = FusedAlert(id=alert.id, tenant_id=alert.tenant_id, incident_id=UUID(payload["incident_id"]),
                fusion_decision=FusionDecision.NEW_INCIDENT, alert=alert, correlation_basis=basis,
                confidence_status="computed", confidence_score=.75, confidence_label="medium",
                confidence_rationale=[], narrative="Synthetic validation: two records share a host; causality unknown.")
            result = await sink.persist(fused)
            assert result.persisted, result.outcome
            saved.append({"alert_id": str(alert.id), "outcome": result.outcome.value,
                "source_event_ids": alert.source_event_ids})
        print(json.dumps({"seeded": saved, "writer": "Socai2AlertSink.persist", "synthetic_only": True}))
    finally:
        await sink.stop()


asyncio.run(main())
