"""Local, synthetic field-mapping observations; no I/O to business services.

Run from the repo with .venv/Scripts/python.exe -B <this file>.
This calls existing mapping/model/snapshot functions, not detection execution,
the full worker, PostgreSQL, ClickHouse, Redis, Kafka or a model provider.
Assertions describe current behaviour, including gaps; they are not acceptance.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "services/fusion"))
from app.models.alert import RawAlert, FusedAlert, FusionDecision
from app.services.alert_sink import _insert_args, _INSERT_SQL, _DEDUP_SOURCE_EVENT_SQL, _MAX_SOURCE_EVENT_IDS
from app.services.confidence import ConfidenceScorer
from app.services.delivery_recovery import make_snapshot, restore_snapshot
from app.services.detection_engine import DetectionEngine, DetectionHit
from app.services.event_schema import validate_raw_alert, validate_raw_event
from app.services.promoter import promote_normalized_event
from app.services.windowed_detection import WindowedDetectionEngine

message = {
    "id": str(UUID(int=101)), "tenant_id": str(UUID(int=1)),
    "connector_id": str(UUID(int=2)), "connector_type": "splunk",
    "ocsf_event": {
        "class_uid": 2004, "severity_id": 4,
        "time": "2026-10-01T01:02:03Z", "message": "SYNTHETIC field audit",
        "metadata": {"product": {"vendor_name": "Splunk", "name": "Splunk Enterprise"}},
        "finding": {"uid": "synthetic-finding-1"},
        "device": {"name": "synthetic-host"},
        "actor": {"user": {"name": "synthetic-user"}},
        "src_endpoint": {"ip": "192.0.2.1"}, "dst_endpoint": {"ip": "192.0.2.2"},
        "file": {"fingerprints": [{"value": "a" * 64}, {"value": "b" * 64}]},
        "mitre_attck": [{"technique_id": "T1059", "tactic_names": ["Execution", "Persistence"]}],
        "raw_data": json.dumps({"rule_id": "synthetic-vendor-rule", "rule_name": "Vendor rule", "domain": "example.invalid", "risk_score": 0.8, "tags": ["synthetic"]}),
    },
}
promoted = promote_normalized_event(message)
assert promoted is not None
hit = DetectionHit("synthetic-local-rule", "Synthetic local rule", "high", "execution", ["T1059"])
detected = DetectionEngine([]).build_alert(message, hit)
windowed = WindowedDetectionEngine(None, (), sequences=()).build_alert(message, hit)
assert detected is not None and windowed is not None
results = []

def observe(name, condition, **actual):
    assert condition, name
    results.append({"name": name, "current_behaviour_confirmed": True, **actual})

observe("event_time_by_entry", promoted.event_time == datetime(2026, 10, 1, 1, 2, 3, tzinfo=timezone.utc) and detected.event_time is None and windowed.event_time is None,
        promoted=promoted.event_time.isoformat(), detected=detected.event_time, windowed=windowed.event_time,
        pg_fallback_is_now="COALESCE($17, NOW())" in _INSERT_SQL)
bad_time = deepcopy(message); bad_time["ocsf_event"]["time"] = "invalid"
observe("invalid_time_unknown_before_sink", promote_normalized_event(bad_time).event_time is None)
observe("source_is_product_label_not_verified_original_vendor", promoted.source == "Splunk Enterprise" and promoted.connector_type == "splunk",
        source=promoted.source, connector_type=promoted.connector_type)
observe("normalized_source_identity", promoted.identity_version == "legacy-v1" and promoted.source_alert_id is None,
        version=promoted.identity_version, source_alert_id=promoted.source_alert_id,
        source_event_id=validate_raw_event(message).source_event_id, external_id=promoted.external_id)
observe("rules_and_tactics_by_entry", promoted.rule_id is None and promoted.rule_name is None and promoted.mitre_tactics == ["Execution", "Persistence"] and detected.rule_id == hit.rule_id and not detected.mitre_tactics and not windowed.mitre_tactics,
        promoted_rule=promoted.rule_id, promoted_tactics=promoted.mitre_tactics,
        detected_rule=detected.rule_id, detected_tactics=detected.mitre_tactics,
        windowed_tactics=windowed.mitre_tactics, detected_techniques=detected.mitre_techniques)
observe("windowed_entity_shape", promoted.hostname == "synthetic-host" and detected.hostname == "synthetic-host" and windowed.hostname is None and windowed.dst_ip is None,
        promoted_host=promoted.hostname, detected_host=detected.hostname, windowed_host=windowed.hostname,
        windowed_dst_ip=windowed.dst_ip)
observe("raw_preserved_but_optional_fields_unprojected", promoted.raw_event == message["ocsf_event"] and promoted.risk_score is None and promoted.domain is None and not promoted.tags,
        risk_score=promoted.risk_score, domain=promoted.domain, tags=promoted.tags,
        first_hash_only=promoted.file_hash == "a" * 64, raw_retains_second_hash=True)
other = promoted.model_copy(deep=True, update={"connector_id": UUID(int=3), "external_id": "synthetic-finding-2", "event_time": datetime(2026, 10, 2, tzinfo=timezone.utc)})
observe("legacy_dedup_ignores_connector_external_id_time", promoted.deterministic_id() == other.deterministic_id())
direct = RawAlert(tenant_id=UUID(int=1), source="synthetic-source", title="Synthetic direct alert", identity_version="source-v1", source_alert_id=UUID(int=201), event_time=promoted.event_time, source_event_ids=["synthetic-event"], tags=["synthetic"], rule_id="r1", rule_name="Rule 1", mitre_tactics=["Execution"], risk_score=0.8, raw_event={"synthetic": True})
direct.id = direct.deterministic_id()
another = direct.model_copy(deep=True, update={"source_alert_id": UUID(int=202)})
observe("source_v1_separates_distinct_upstream_ids", direct.deterministic_id() != another.deterministic_id())
fused = FusedAlert(id=direct.id, tenant_id=direct.tenant_id, incident_id=UUID(int=301), fusion_decision=FusionDecision.NEW_INCIDENT, alert=direct)
snapshot = make_snapshot(fused)
changed = direct.model_copy(deep=True, update={"raw_event": {"synthetic": "updated"}, "source_event_ids": ["synthetic-second-event"]})
restored = restore_snapshot(snapshot, changed)
args = _insert_args(fused, delivery_snapshot=snapshot)
observe("first_material_frozen_and_tags_only_in_snapshot", restored.alert.raw_event == {"synthetic": True} and restored.alert.source_event_ids == ["synthetic-event"] and "tags" not in _INSERT_SQL and json.loads(args[30])["socai2_fusion"]["delivery_snapshot"]["fused"]["alert"]["tags"] == ["synthetic"],
        projected_rule_id=args[21], projected_rule_name=args[22], projected_tactics=json.loads(args[5]),
        projected_raw=json.loads(args[9]), snapshot_tags=direct.tags)
observe("dedup_lineage_limits_static_sql", _MAX_SOURCE_EVENT_IDS == 200 and "updated_at" not in _DEDUP_SOURCE_EVENT_SQL and "last_seen" not in _DEDUP_SOURCE_EVENT_SQL,
        cap=_MAX_SOURCE_EVENT_IDS, updates_updated_at=False, updates_last_seen=False)
observe("default_confidence_is_not_missing", args[11] == 50 and args[12] == "medium" and json.loads(args[13]) == [],
        score=args[11], label=args[12], rationale=json.loads(args[13]))
scored = ConfidenceScorer().score(fused.model_copy(deep=True))
scored_args = _insert_args(scored)
observe("computed_confidence_roundtrips", bool(scored.confidence_rationale) and scored_args[11] == round(scored.confidence_score * 100) and json.loads(scored_args[13]) == [x.model_dump() for x in scored.confidence_rationale],
        score=scored_args[11], label=scored_args[12], rationale_count=len(scored.confidence_rationale))
observe("raw_alert_envelope_id_becomes_lineage", validate_raw_alert({"id": str(UUID(int=401)), "tenant_id": str(UUID(int=1))}).source_event_id == str(UUID(int=401)),
        note="This is an envelope ID; no lake membership was checked.")

files = ["models/alert.py", "services/promoter.py", "services/detection_engine.py", "services/windowed_detection.py", "services/alert_sink.py", "services/delivery_recovery.py", "services/event_schema.py", "services/confidence.py", "services/provenance.py", "workers/consumer.py"]
output = {"scope": "local synthetic mapping observations only", "business_services_called": 0, "live_acceptance": False,
          "observations": results, "source_sha256": {"services/fusion/app/" + p: hashlib.sha256((ROOT / "services/fusion/app" / p).read_bytes()).hexdigest() for p in files}}
Path(__file__).with_name("observations.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"observations_confirmed": len(results), "business_services_called": 0, "live_acceptance": False}, ensure_ascii=False))
