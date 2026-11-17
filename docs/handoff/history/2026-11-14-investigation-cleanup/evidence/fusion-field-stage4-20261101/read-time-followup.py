"""One new observation for the detail GET's cache write; local substitutes only."""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "services/api"))
from app.api.v1.endpoints import alerts
from sqlalchemy.dialects import postgresql


async def main():
    now = datetime(2026, 11, 1, tzinfo=timezone.utc)
    row = SimpleNamespace(id=UUID(int=11), tenant_id=UUID(int=1), title="SYNTHETIC detail read",
        description=None, severity="high", status="new", priority=50, category=None,
        mitre_tactics=[], mitre_techniques=[], connector_type=None, ai_score=None,
        ai_summary=None, ai_recommendations=[], affected_ips=[], affected_hosts=[], affected_users=[],
        case_id=None, tags=[], event_time=now, first_seen=now, last_seen=now, created_at=now,
        updated_at=now, narrative=None, raw_event={}, enrichment_data={}, source_event_ids=[], external_id=None)
    loaded = MagicMock(); loaded.scalar_one_or_none.return_value = row
    db = SimpleNamespace(execute=AsyncMock(side_effect=[loaded, MagicMock()]), commit=AsyncMock())
    envelope = SimpleNamespace(related_entities=[], mini_timeline=[], recommended_actions=[])
    with patch.object(alerts, "project_alert_to_narrative_inputs", return_value=object()), \
         patch.object(alerts, "build_narrative", return_value="Synthetic deterministic narrative"), \
         patch.object(alerts, "build_rail_envelope", new=AsyncMock(return_value=envelope)):
        response = await alerts.get_alert(row.id, SimpleNamespace(tenant_id=row.tenant_id), db)
    compiled = db.execute.await_args_list[1].args[0].compile(dialect=postgresql.dialect())
    assert "narrative=" in str(compiled) and "updated_at=" in str(compiled) and db.commit.await_count == 1
    assert response.narrative == "Synthetic deterministic narrative"
    return {"scope": "actual get_alert handler; narrative builder, rail and DB substituted; no service calls",
            "observation_count": 1, "name": "detail_get_lazy_fill_writes_business_updated_at",
            "current_behaviour_confirmed": True, "sql": str(compiled), "params": compiled.params,
            "commit_attempts_on_substitute": db.commit.await_count}


out = asyncio.run(main())
out["probe_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
Path(__file__).with_name("read-time-followup.json").write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str)+"\n", encoding="utf-8")
print(json.dumps({"observations": 1, "confirmed": True}))
