"""Restricted existing synthetic PG. No Redis/Kafka/model/vendor network calls."""
import asyncio
import json
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.core.config import Settings
from app.models.alert import CorrelationBasis, FusedAlert, FusionDecision, RawAlert
from app.services import socai2_projection as p
from app.services.alert_sink import PersistOutcome
from app.services.delivery_recovery import DeliveryHold, make_snapshot
from app.services.socai2_sink import Socai2AlertSink
from app.workers.consumer import FusionWorker
from jsonschema import Draft202012Validator

T, OTHER = UUID(int=1), UUID(int=2)
NOW = datetime(2026, 11, 4, tzinfo=UTC)


def sample(*, tenant=T, incident=None, **changes):
    values = {"tenant_id": tenant, "identity_version": "source-v1", "source_alert_id": uuid4(),
        "source": "synthetic-socai2-fusion", "connector_type": "splunk", "title": "synthetic received alert",
        "description": "explicit synthetic fixture", "event_time": NOW, "severity": "high", "hostname": "shared-host",
        "username": "shared-host", "src_ip": "192.0.2.10", "dst_ip": "198.51.100.11", "file_hash": "a" * 64,
        "domain": "example.invalid", "url": "https://example.invalid/path", "rule_id": "rule-1", "rule_name": "synthetic rule",
        "source_event_ids": [str(uuid4()), str(uuid4())], "external_id": "vendor-finding", "ocsf_class_uid": 1007,
        "mitre_tactics": ["Execution", "Persistence"], "mitre_techniques": ["T1059"], "risk_score": 0,
        "tags": ["source-tag"], "raw_event": {"original_vendor": "original maker", "ocsf_event": {"class_uid": 1007,
            "time": NOW.isoformat(), "process": {"pid": 42, "cmd_line": "synthetic command", "parent_process": {"pid": 21}},
            "file": {"hashes": [{"algorithm": "SHA256", "value": "a" * 64}]},
            "raw_data": "synthetic original raw"}}}
    values.update(changes)
    alert = RawAlert(**values)
    alert.id = alert.deterministic_id()
    basis = CorrelationBasis(entity_type="host", entity_value=alert.hostname, tactic="Execution",
        correlation_key=alert.correlation_key(), window_seconds=300, max_alerts=20,
        decision="new_incident", reason="no_index", decided_at=NOW)
    return FusedAlert(id=alert.id, tenant_id=tenant, incident_id=incident or uuid4(),
        fusion_decision=FusionDecision.NEW_INCIDENT, alert=alert, correlation_basis=basis,
        confidence_status="computed", confidence_score=.87, confidence_label="high",
        confidence_rationale=[{"factor": "explicit", "label": "synthetic label", "value": "observed", "contribution": .2, "weight": .5}],
        narrative="synthetic deterministic narrative", enrichments={"synthetic": {"raw": True}},
        session_id=uuid4(), session_key_kind="vendor", originating_human="synthetic human")


async def run_checks(engine, record, only=None):
    sink = Socai2AlertSink(engine.url.render_as_string(hide_password=False))
    await sink.start()
    assert sink._pool is not None

    async def rows(sql, *args, tenant=T):
        async with sink._pool.acquire() as conn, conn.transaction():
            await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(tenant))
            return await conn.fetch(sql, *args)

    async def state(fused):
        return dict((await rows("SELECT * FROM socai2.alerts WHERE id=$1", fused.id, tenant=fused.tenant_id))[0])

    async def materials(fused):
        return await rows("SELECT * FROM socai2.alert_materials WHERE alert_id=$1 ORDER BY revision", fused.id, tenant=fused.tenant_id)

    async def test_fusion_full_field_contract_and_atomic_membership():
        fused = sample()
        assert (await sink.persist(fused)).outcome is PersistOutcome.INSERTED
        alert, material = await state(fused), (await materials(fused))[0]
        assert alert["source_alert_id"] == str(fused.alert.source_alert_id) and alert["vendor_alert_id"] == "vendor-finding"
        assert alert["original_vendor"] == "original maker" and alert["event_time"] == NOW
        assert alert["first_seen_at"] == alert["last_seen_at"] == NOW
        assert alert["priority_value"] is None and alert["latest_triage_id"] is None
        raw, detection = json.loads(material["raw_json"]), json.loads(material["detection"])
        assert raw == fused.alert.model_dump(mode="json") and material["raw_text"] == "synthetic original raw"
        assert detection["confidence_value"] == 87 and detection["rule_id"] == "rule-1"
        assert detection["tactics"] == ["Execution", "Persistence"]
        objects = await rows("SELECT * FROM socai2.alert_objects WHERE material_id=$1", material["id"])
        assert len(objects) == 7
        assert len({r["object_key"] for r in objects if r["raw_value"] == "shared-host"}) == 2
        assert json.loads(next(r for r in objects if r["object_type"] == "hash")["attributes"])["algorithm"] == "SHA256"
        link = (await rows("SELECT * FROM socai2.incident_alerts WHERE alert_id=$1", fused.id))[0]
        assert link["incident_id"] == fused.incident_id and link["membership_source"] == "fusion"
        schema = json.loads((Path(__file__).resolve().parents[2] / "api/app/socai2/contracts.schema.json").read_text("utf-8"))
        for key in ("detection", "enrichment", "source_scope", "retention"):
            Draft202012Validator({"$ref": "#/$defs/" + key, "$defs": schema["$defs"]}).validate(json.loads(material[key]))
        Draft202012Validator({"$ref": "#/$defs/correlation_basis", "$defs": schema["$defs"]}).validate(json.loads(link["correlation_basis"]))
        assert (await sink.lookup_delivery(fused.alert)).snapshot == make_snapshot(fused)
        assert not await rows("SELECT id FROM socai2.incident_diagnoses WHERE incident_id=$1", fused.incident_id)
        return {"bridge_alert_id": str(fused.id), "material_id": str(material["id"]), "incident_id": str(fused.incident_id)}

    async def test_fusion_unknown_time_vendor_and_confidence():
        for status in ("unknown", "disabled", "failed", "computed"):
            fused = sample(event_time=None, raw_event={"metadata": {"product": {"vendor_name": "Splunk"}}})
            fused.confidence_status, fused.confidence_score = status, 0
            assert (await sink.persist(fused)).durable
            row = await state(fused)
            detection = json.loads((await materials(fused))[0]["detection"])
            assert row["event_time"] is None and row["event_time_source"] == "unknown"
            assert row["first_seen_at"] is None and row["last_seen_at"] is None and row["original_vendor"] is None
            assert detection["confidence_value"] == (0 if status == "computed" else None)
            assert detection["confidence_state"] == {"unknown": "not_computed", "computed": "available"}.get(status, status)
        assert Settings(_env_file=None).alert_store_schema == "public"

    async def test_fusion_concurrent_replay_versions_and_operator_values():
        fused = sample()
        results = await asyncio.gather(*(sink.persist(fused) for _ in range(3)))
        assert sum(r.persisted for r in results) == 1 and all(r.durable for r in results)
        initial = await state(fused)
        first_material = dict((await materials(fused))[0])
        snapshot = (await sink.lookup_delivery(fused.alert)).snapshot
        await rows("""UPDATE socai2.alerts SET title='operator title',tags=ARRAY['operator-tag'],
            handling_status='completed',disposition='false_positive',severity='low' WHERE id=$1 RETURNING id""", fused.id)
        changed = fused.alert.model_copy(deep=True)
        changed.event_time = NOW + timedelta(hours=1)
        changed.raw_event["additional"] = "new received raw"
        changed.source_event_ids.append(str(uuid4()))
        assert (await sink.persist(fused, replay=changed)).outcome is PersistOutcome.DUPLICATE
        second = await state(fused)
        assert second["title"] == "operator title" and second["tags"] == ["operator-tag"] and second["severity"] == "low"
        assert second["handling_status"] == "completed" and second["disposition"] == "false_positive"
        assert second["event_time"] == NOW and second["last_seen_at"] == changed.event_time
        assert second["latest_material_id"] != initial["latest_material_id"]
        assert dict((await materials(fused))[0]) == first_material
        assert json.loads((await materials(fused))[1]["detection"])["confidence_state"] == "not_computed"
        assert (await sink.lookup_delivery(changed)).snapshot == snapshot
        assert (await sink.persist(fused)).durable and await state(fused) == second
        assert len(await materials(fused)) == 2

    async def test_fusion_incident_members_and_manual_move_preserved():
        first, second = sample(), sample()
        second.incident_id = first.incident_id
        assert all(r.durable for r in await asyncio.gather(sink.persist(first), sink.persist(second)))
        assert len(await rows("SELECT * FROM socai2.incident_alerts WHERE incident_id=$1", first.incident_id)) == 2
        moved = uuid4()
        await rows("INSERT INTO socai2.incidents(id,tenant_id,source_namespace,source_incident_id,title) VALUES($1,$2,'manual',$3,'manual incident') RETURNING id", moved, T, str(moved))
        await rows("UPDATE socai2.incident_alerts SET incident_id=$2,membership_source='move' WHERE alert_id=$1 RETURNING id", first.id, moved)
        # A member transaction may have captured its time before another
        # committed member update; the final event business clock cannot recede.
        newer = (await rows("UPDATE socai2.incidents SET business_updated_at=clock_timestamp()+interval '1 minute' WHERE id=$1 RETURNING business_updated_at", moved))[0]["business_updated_at"]
        replay = first.alert.model_copy(deep=True)
        replay.raw_event["later"] = True
        assert (await sink.persist(first, replay=replay)).durable
        links = await rows("SELECT incident_id,membership_source FROM socai2.incident_alerts WHERE alert_id=$1", first.id)
        assert links[0]["incident_id"] == moved and links[0]["membership_source"] == "move"
        assert (await rows("SELECT business_updated_at FROM socai2.incidents WHERE id=$1", moved))[0]["business_updated_at"] == newer

    async def test_fusion_window_candidates_bounded_and_source_paths():
        ids = [str(uuid4()) for _ in range(202)]
        fused = sample(source_event_ids=[ids[0], *ids], field_metadata={"source_window": {
            "scope": "matched_stage_candidates", "complete": True, "candidate_start": NOW.timestamp(),
            "candidate_end": (NOW + timedelta(minutes=5)).timestamp()}})
        assert (await sink.persist(fused)).durable
        material = (await materials(fused))[0]
        scope = json.loads(material["source_scope"])
        assert scope["kind"] == "sequence_candidates" and scope["truncated"] and not scope["complete"]
        assert scope["received_count"] == 202 and scope["retained_count"] == 200
        refs = await rows("SELECT * FROM socai2.alert_source_refs WHERE material_id=$1", material["id"])
        assert len(refs) == 200 and all(r["relation_kind"] == "sequence_candidate" for r in refs)
        for row in refs:
            index = int(row["source_path"].rsplit("[", 1)[1][:-1])
            assert fused.alert.source_event_ids[index] == row["source_event_id"]
        raw = json.loads(material["raw_json"])
        assert raw["source_event_ids"] == fused.alert.source_event_ids

    async def test_fusion_raw_separation_extra_endpoints_and_activity_conflict():
        fused = sample()
        fused.alert.raw_event["activity"] = {"session": {"id": "envelope-session"}}
        fused.alert.raw_event["ocsf_event"]["activity"] = {"session": {"id": "ocsf-session"}}
        fused.alert.raw_event["ocsf_event"]["dst_endpoint"] = {"hostname": "target-host", "ip": "203.0.113.8"}
        assert (await sink.persist(fused)).durable
        material = (await materials(fused))[0]
        assert "synthetic original raw" not in material["enrichment"]
        assert json.loads(material["raw_json"])["raw_event"] == fused.alert.raw_event
        projected = json.loads(material["ocsf_json"])
        assert projected["activity"]["session"]["id"] == "ocsf-session"
        assert projected["_socai2_storage"]["envelope_activity"]["session"]["id"] == "envelope-session"
        objects = await rows("SELECT object_type,raw_value,source_path FROM socai2.alert_objects WHERE material_id=$1", material["id"])
        assert any(o["raw_value"] == "target-host" and o["source_path"] == "$.ocsf_json.dst_endpoint.hostname" for o in objects)
        assert any(o["raw_value"] == "203.0.113.8" and o["object_type"] == "ip" for o in objects)

    async def test_fusion_failures_rollback_whole_row_and_batch_isolation():
        bad_connector, invalid_title, valid = sample(connector_id=UUID(int=6)), sample(title="  "), sample()
        results = await sink.persist_many([bad_connector, valid, invalid_title])
        assert [r.outcome for r in results] == [PersistOutcome.FAILED, PersistOutcome.INSERTED, PersistOutcome.FAILED]
        for fused in (bad_connector, invalid_title):
            assert not await rows("SELECT id FROM socai2.alerts WHERE id=$1", fused.id)
            assert not await rows("SELECT id FROM socai2.artifacts WHERE alert_id=$1", fused.id)
        class FailedCommit(Socai2AlertSink):
            async def _write(self, conn, fused, alert, snapshot):
                result = await super()._write(conn, fused, alert, snapshot)
                await conn.execute("UPDATE socai2.alerts SET latest_material_id=$2 WHERE id=$1", fused.id, uuid4())
                return result
        broken = FailedCommit(sink._dsn)
        broken._pool = sink._pool
        fused = sample()
        assert (await broken.persist(fused)).outcome is PersistOutcome.FAILED
        for table, field, identity in (("alerts", "id", fused.id), ("alert_materials", "alert_id", fused.id),
                ("incidents", "id", fused.incident_id), ("artifacts", "alert_id", fused.id)):
            assert not await rows(f"SELECT id FROM socai2.{table} WHERE {field}=$1", identity)

    async def test_fusion_tenant_snapshot_and_unproven_existing_row():
        fused = sample()
        assert (await sink.persist(fused)).durable
        assert not await rows("SELECT id FROM socai2.alerts WHERE id=$1", fused.id, tenant=OTHER)
        valid_connector = sample(tenant=OTHER, connector_id=UUID(int=6))
        assert (await sink.persist(valid_connector)).durable
        assert (await state(valid_connector))["connector_id"] == UUID(int=6)
        wrong = fused.alert.model_copy(update={"tenant_id": OTHER})
        assert (await sink.persist(fused, replay=wrong)).outcome is PersistOutcome.FAILED
        snapshot = make_snapshot(fused)
        snapshot["fused"]["narrative"] = "tampered"
        assert (await sink.persist(fused, delivery_snapshot=snapshot)).outcome is PersistOutcome.FAILED
        missing = sample()
        await rows("INSERT INTO socai2.alerts(id,tenant_id,source_namespace,source_identity_key,title) VALUES($1,$2,$3,$4,'unproven fixture') RETURNING id",
            missing.id, T, p.STORE_NAMESPACE, missing.alert.fingerprint())
        lookup = await sink.lookup_delivery(missing.alert)
        assert lookup.exists and lookup.snapshot is None
        assert (await sink.persist(missing)).outcome is PersistOutcome.FAILED
        assert not await materials(missing)

    async def test_fusion_worker_reuses_pg_first_delivery_without_refusion():
        class Redis:
            def __init__(self):
                self.values = {}
            async def get(self, key):
                return self.values.get(key)
            async def set(self, key, value, **kwargs):
                if key in self.values:
                    return False
                self.values[key] = value
                return True
        class Engine:
            def __init__(self):
                self._dedup = SimpleNamespace(_redis=Redis(), is_duplicate=self.is_duplicate)
                self.calls = 0
            async def is_duplicate(self, alert):
                return False, None
            async def process(self, alert):
                self.calls += 1
                fused = sample()
                return fused.model_copy(update={"id": alert.id, "alert": alert, "tenant_id": alert.tenant_id})
        class Producer:
            def __init__(self):
                self.values = []
            async def send_and_wait(self, topic, *, value):
                assert (await sink.lookup_delivery(RawAlert.model_validate(value["alert"]))).exists
                self.values.append(value)
        engine, producer = Engine(), Producer()
        worker = FusionWorker(engine, sink=sink)
        worker._producer = producer
        alert = sample().alert
        first = await worker._fuse_and_persist(alert)
        engine._dedup._redis.values.clear()
        second = await worker._fuse_and_persist(alert)
        assert first == second and engine.calls == 1
        assert [r["persist_outcome"] for r in producer.values] == ["inserted", "duplicate"]
        assert len(await materials(first)) == 1
        # Failure before durable commit cannot emit an outbound message.
        invalid = sample(connector_id=UUID(int=6)).alert
        try:
            await worker._fuse_and_persist(invalid)
        except DeliveryHold:
            pass
        else:
            raise AssertionError("undurable row must not publish")
        assert len(producer.values) == 2

    checks = [test_fusion_full_field_contract_and_atomic_membership, test_fusion_unknown_time_vendor_and_confidence,
        test_fusion_concurrent_replay_versions_and_operator_values, test_fusion_incident_members_and_manual_move_preserved,
        test_fusion_window_candidates_bounded_and_source_paths, test_fusion_failures_rollback_whole_row_and_batch_isolation,
        test_fusion_tenant_snapshot_and_unproven_existing_row, test_fusion_worker_reuses_pg_first_delivery_without_refusion,
        test_fusion_raw_separation_extra_endpoints_and_activity_conflict]
    try:
        for check in checks:
            if only is not None and check.__name__ not in only:
                continue
            try:
                record(check.__name__, True, await asyncio.wait_for(check(), 180))
            except Exception:  # noqa: BLE001 -- preserve originals for each synthetic check
                record(check.__name__, False, traceback.format_exc())
    finally:
        await sink.stop()
