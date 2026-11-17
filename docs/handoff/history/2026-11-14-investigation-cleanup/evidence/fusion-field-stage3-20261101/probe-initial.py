"""Bounded synthetic relationship observations, not acceptance tests.

Run `python -B probe.py fusion`, then `python -B probe.py api` in separate
processes because these services use different packages named `app`.
No business service, model, Redis, PG or graph connections are made.
"""
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
HERE = Path(__file__).resolve().parent
PART = sys.argv[1]
assert PART in {"fusion", "api"}
sys.path.insert(0, str(ROOT / "services" / PART))
observations = []


def observe(name, condition, **actual):
    assert condition, name
    observations.append({"name": name, "current_behaviour_confirmed": True, **actual})


async def fusion():
    from app.models.alert import RawAlert, FusedAlert, FusionDecision
    from app.services.correlator import Correlator
    from app.services.alert_sink import _insert_args
    from app.services.delivery_recovery import make_snapshot

    class LocalRedis:
        def __init__(self):
            self.values = {}
        async def get(self, key):
            return self.values.get(key)
        async def set(self, key, value, ex=None):
            self.values[key] = value.encode()

    common = dict(tenant_id=UUID(int=1), source="synthetic", identity_version="source-v1",
                  title="SYNTHETIC relation audit", mitre_tactics=["Execution", "Persistence"],
                  domain="shared.example.invalid", file_hash="a" * 64,
                  event_time=datetime(2026, 11, 1, tzinfo=timezone.utc))
    host = RawAlert(**common, source_alert_id=UUID(int=101), hostname="same-text")
    user = RawAlert(**common, source_alert_id=UUID(int=102), username="same-text")
    for alert in (host, user):
        alert.id = alert.deterministic_id()
    correlator = Correlator(LocalRedis())
    joined1, first = await correlator.correlate(host)
    joined2, second = await correlator.correlate(user)
    observe("distinct_entity_types_share_key_and_incident",
            host.id != user.id and host.correlation_key() == user.correlation_key()
            and not joined1 and joined2 and first.id == second.id and second.alert_count == 2,
            source_types=["host", "user"], value="same-text", key=host.correlation_key(),
            canonical_ids=[str(host.id), str(user.id)], incident_id=str(second.id), member_count=second.alert_count)
    projections = []
    for alert in (host, user):
        fused = FusedAlert(id=alert.id, tenant_id=alert.tenant_id, incident_id=second.id,
                           fusion_decision=FusionDecision.CORRELATED if alert is user else FusionDecision.NEW_INCIDENT,
                           alert=alert)
        args = _insert_args(fused, delivery_snapshot=make_snapshot(fused))
        projections.append({"id": str(args[0]), "tenant_id": str(args[1]), "title": args[2],
                            "severity": args[4], "mitre_tactics": json.loads(args[5]),
                            "mitre_techniques": json.loads(args[6]), "iocs": json.loads(args[7]),
                            "entities": json.loads(args[8]), "raw_event": json.loads(args[9]),
                            "affected_hosts": json.loads(args[24]), "affected_users": json.loads(args[25]),
                            "affected_ips": json.loads(args[26]), "enrichment_data": json.loads(args[30])})
    observe("sink_retains_iocs_and_assignment_but_no_explicit_decision_basis",
            all(len(row["iocs"]) == 2 and not any(e["type"] == "domain" for e in row["entities"])
                and row["enrichment_data"]["socai2_fusion"]["incident_id"] == str(second.id)
                for row in projections),
            persisted_iocs=projections[0]["iocs"], redis_basis=second.correlation_keys,
            snapshot_fields=list(projections[0]["enrichment_data"]["socai2_fusion"]["delivery_snapshot"]["fused"]),
            explicit_basis_field_present="correlation_keys" in FusedAlert.model_fields,
            note="Snapshot keeps inputs and fusion_decision; no full FusionEngine/narrative execution in this probe.")
    return {"stored_projection": projections}


async def api():
    from app.models.alert import Alert
    from app.investigation_v2.incident_reader import read_incident, _entities
    from app.services import processing_context
    from sqlalchemy.dialects import postgresql

    rows = json.loads((HERE / "fusion-observations.json").read_text(encoding="utf-8"))["stored_projection"]
    now = datetime(2026, 11, 1, tzinfo=timezone.utc)
    alerts = [Alert(**{**row, "id": UUID(row["id"]), "tenant_id": UUID(row["tenant_id"])},
                    status="new", disposition=None, event_time=now, first_seen=now, last_seen=now,
                    updated_at=now, case_id=None, connector_id=None, external_id=None,
                    ai_summary=None, ai_recommendations=[]) for row in rows]
    incident_id = UUID(rows[0]["enrichment_data"]["socai2_fusion"]["incident_id"])
    result, triage = MagicMock(), MagicMock()
    result.scalars.return_value.all.return_value = alerts
    triage.all.return_value = []
    db = SimpleNamespace(execute=AsyncMock(side_effect=[result, triage]))
    overview = await read_incident(db, tenant_id=alerts[0].tenant_id, incident_id=incident_id)
    observe("stored_shared_iocs_omitted_from_incident_and_case_entity_helper",
            overview.member_count == 2 and {e["type"] for e in overview.entities} == {"host", "user"}
            and all(not any(e["type"] in {"hash", "domain"} for e in _entities([a])) for a in alerts),
            stored_iocs_per_member=[a.iocs for a in alerts], returned_entities=overview.entities,
            note="Actual sink projection fed into ORM objects; DB returns are substitutes, not real inserts/SQL execution.")
    member_fields = set(overview.members[0].model_fields)
    observe("incident_projection_has_union_without_member_edges_or_tactic_counts",
            not ({"entities", "iocs", "mitre_tactics", "assets"} & member_fields)
            and overview.mitre_tactics == ["Execution", "Persistence"],
            member_fields=sorted(member_fields), returned_tactics=overview.mitre_tactics,
            expected_counts_from_supplied_members={"Execution": 2, "Persistence": 2},
            actual_member_query=str(db.execute.await_args_list[0].args[0].compile(dialect=postgresql.dialect())))
    # Existing typed entities alone must not be mistaken for missing input.
    entity_only = Alert(id=UUID(int=201), tenant_id=alerts[0].tenant_id, severity="medium",
                        affected_hosts=[], affected_users=[], affected_ips=[],
                        entities=[{"type": "host", "value": "existing-host"}],
                        event_time=now, created_at=now, confidence=50)
    async def no_match(db, query, params, source):
        return {"status": "no_match", "source": source, "rows": [], "truncated": False}
    with patch.object(processing_context, "_read", new=AsyncMock(side_effect=no_match)) as reads:
        context = await processing_context.collect_processing_context(None, entity_only)
    observe("asset_lookup_does_not_use_existing_entity_only_host",
            context["query"]["hosts"] == [] and reads.await_args_list[0].args[2]["hosts"] == [],
            received_entities=entity_only.entities, lookup_query=context["query"],
            note="Lookup mocked empty to inspect passed keys only; this does not claim a live inventory miss.")
    return {"overview": overview.model_dump(mode="json")}


extra = asyncio.run(fusion() if PART == "fusion" else api())
result = {"part": PART, "scope": "local synthetic current behaviour; no service calls; not acceptance",
          "observation_count": len(observations), "observations": observations, **extra,
          "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(HERE / f"{PART}-observations.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
print(json.dumps({"part": PART, "observations": len(observations), "confirmed": True}))
