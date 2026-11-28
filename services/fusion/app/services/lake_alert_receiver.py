"""One immutable lake alert -> atomic PG receipt and initial analysis tasks.

This callable does not poll Kafka, publish messages or run analysis workers.
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import asyncpg

from app.models.alert import AlertSeverity, RawAlert
from app.services import socai2_projection as projection
from app.services.alert_sink import PersistOutcome
from app.services.delivery_recovery import (
    DeliveryHold,
    DeliveryRecovery,
    make_snapshot,
    restore_snapshot,
)
from app.services.lake_alert_selection import SelectionPolicy, field, select_alert
from app.services.lake_ingress import ABSENT, Projection, decode, nested, project_labels
from app.services.receipt_json import (
    LAKE_INPUT_VERSION,
    decoded,
    encoded,
    lake_input,
    model_value,
)
from app.services.received_fields import parse_received_time
from app.services.socai2_analysis_tasks import initial_key


class ReceiptHold(DeliveryHold):
    pass


@dataclass(frozen=True)
class ReceivePolicy:
    body: dict

    @classmethod
    def load(cls, path):
        body = json.loads(Path(path).read_text())
        keys = {"version", "postgres_database", "source", "connector_type", "connector_id", "projection", "limits", "initial_analysis"}
        if set(body) != keys or body["version"] != "socai2.lake-alert-receive.v1":
            raise ValueError("invalid_receive_profile")
        if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", body["postgres_database"]):
            raise ValueError("invalid_receive_database")
        if any(not isinstance(body[k], str) or not body[k].strip() for k in ("source", "connector_type")):
            raise ValueError("explicit_receive_source_required")
        if body["connector_id"] is not None:
            body["connector_id"] = str(UUID(body["connector_id"]))
        limits = body["limits"]
        if set(limits) != {"material_bytes", "snapshot_bytes", "receive_timeout_seconds", "lock_timeout_seconds", "recovery_ttl_seconds"}:
            raise ValueError("explicit_receive_limits_required")
        if any(type(n) is not int or n <= 0 for n in limits.values()):
            raise ValueError("invalid_receive_limits")
        fields = body["projection"]
        if set(fields) != {"title_paths", "description_paths", "entity_paths", "severity_mapping"}:
            raise ValueError("invalid_receive_projection")
        if set(fields["entity_paths"]) != {"hostname", "src_ip", "dst_ip", "username", "domain", "url"}:
            raise ValueError("invalid_entity_projection")
        for paths in [fields["title_paths"], fields["description_paths"], *fields["entity_paths"].values()]:
            if not isinstance(paths, list) or not paths or any(not isinstance(p, str) or not re.fullmatch(r"[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)*", p) for p in paths):
                raise ValueError("invalid_projection_paths")
        levels = fields["severity_mapping"]
        if not levels or any(k not in {"1", "2", "3", "4", "5", "6"} or v not in {s.value for s in AlertSeverity} for k,v in levels.items()):
            raise ValueError("invalid_source_severity_mapping")
        initial = body["initial_analysis"]
        if set(initial) != {"retry_limit", "retry_delay_seconds"} or any(type(v) is not int or v < 0 for v in initial.values()):
            raise ValueError("invalid_initial_analysis_policy")
        return cls(body)


def adapt_alert(row, selection: SelectionPolicy, policy: ReceivePolicy, *, decision=None):
    if not selection.immutable:
        raise ReceiptHold("immutable_selection_required")
    current = select_alert(row, selection)
    if decision is not None:
        if decision["delivery_key"] != current["delivery_key"] or decision["policy_digest"] != selection.digest:
            raise ReceiptHold("selection_receipt_mismatch")
        if decision["action"] != "new_alert_candidate":
            raise ReceiptHold("selection_not_deliverable")
    if current["action"] != "new_alert_candidate" or not (current["identity"] or {}).get("ready"):
        raise ReceiptHold("selection_not_deliverable")
    document, _, _, _ = decode(row["ocsf_json"].encode())
    partial = nested(document, ("unmapped", "spirithub", "mapping_status")) == "partial"
    fields = policy.body["projection"]

    def string(paths):
        for path in paths:
            value, actual, conflict = field(document, path, partial=partial)
            if conflict:
                raise ReceiptHold("projection_field_conflict")
            if isinstance(value, str) and value.strip():
                return value, actual
            if value is not ABSENT:
                return None, actual  # explicit null/invalid cannot be hidden by a fallback
        return None, None

    title, title_path = string(fields["title_paths"])
    if title is None:
        raise ReceiptHold("source_title_missing")
    severity, severity_path, conflict = field(document, "severity_id", partial=partial)
    if conflict or type(severity) is not int or str(severity) not in fields["severity_mapping"]:
        raise ReceiptHold("source_severity_unmapped")
    entities, paths = {}, {}
    for name, candidates in fields["entity_paths"].items():
        entities[name], paths[name] = string(candidates)
    description, _ = string(fields["description_paths"])
    rule_id, rule_id_path = string(("finding_info.analytic.uid",))
    rule_name, rule_name_path = string(("finding_info.analytic.name",))
    techniques, tactics = project_labels(Projection(document))
    rule_sources = {
        key: path
        for key, path in (("rule_id_source", rule_id_path), ("rule_name_source", rule_name_path))
        if path is not None
    }
    ref = current["lake_ref"]
    source_id = document["metadata"]["uid"]
    envelope = {"ocsf_event": document, "source_ocsf_json": row["ocsf_json"]}
    vendor = nested(document, ("metadata", "product", "vendor_name"))
    if isinstance(vendor, str) and vendor.strip():
        envelope["original_vendor"] = vendor
    alert = RawAlert(tenant_id=UUID(ref["tenant_id"]), identity_version="source-v1",
        source_alert_id=UUID(current["identity"]["source_subject_id"]), source=policy.body["source"],
        connector_type=policy.body["connector_type"], connector_id=policy.body["connector_id"],
        title=title, description=description or "", severity=fields["severity_mapping"][str(severity)],
        rule_id=rule_id, rule_name=rule_name, mitre_tactics=tactics, mitre_techniques=techniques,
        external_id=source_id, source_event_ids=[source_id], ocsf_class_uid=ref["class_uid"],
        event_time=parse_received_time(ref["event_time"]) if row["event_time_source"] == "ocsf_time_ms" else None,
        raw_event=envelope, field_metadata={"entity_sources": paths, "title_source": title_path,
            "severity_source": severity_path, **rule_sources, "lake_ingress": {"schema_version": LAKE_INPUT_VERSION,
                "lake_database": selection.body["database"], "lake_ref": ref,
                "source_subject_id": current["identity"]["source_subject_id"], "source_event_id": source_id}}, **entities)
    alert.id = alert.deterministic_id()
    if len(encoded(model_value(alert)).encode()) > policy.body["limits"]["material_bytes"]:
        raise ReceiptHold("received_material_exceeds_configured_limit")
    return alert


@dataclass(frozen=True)
class ReceiveResult:
    state: str
    reason: str | None = None
    alert_id: str | None = None
    material_id: str | None = None
    incident_id: str | None = None
    initial_alert_task_id: str | None = None
    initial_incident_task_id: str | None = None

    @property
    def durable(self):
        return self.state in {"created", "duplicate"}


class LakeAlertReceiver:
    def __init__(self, selection, policy, sink, engine):
        self.selection, self.policy, self.sink, self.engine = selection, policy, sink, engine
        limits = policy.body["limits"]
        if (sink.material_max_bytes != limits["material_bytes"] or sink.snapshot_max_bytes != limits["snapshot_bytes"]
                or sink.analysis_policy != policy.body["initial_analysis"]):
            raise ValueError("receiver_sink_policy_mismatch")

    async def _fuse(self, alert):
        dedup = self.engine._dedup
        recovery = DeliveryRecovery(dedup._redis, self.policy.body["limits"]["recovery_ttl_seconds"],
                                    max_bytes=self.sink.snapshot_max_bytes)
        fused = await recovery.load(alert)
        if fused is None:
            duplicate, _ = await dedup.is_duplicate(alert)
            if duplicate:
                raise ReceiptHold("fusion_dedup_without_first_result")
            fused = await recovery.remember(await self.engine.process(alert))
        prior = lake_input(fused.alert)
        if prior is None or prior["lake_ref"]["source_version"] != lake_input(alert)["lake_ref"]["source_version"]:
            raise ReceiptHold("recovered_source_content_conflict")
        return fused

    async def _read_receipt(self, conn, saved, alert, *, state):
        tenant, aid, mid = alert.tenant_id, saved["alert_id"], saved["material_id"]
        body = await conn.fetchrow("""SELECT a.id,m.raw_text,f.content_json,ia.incident_id
            FROM socai2.alerts a JOIN socai2.alert_materials m ON m.tenant_id=a.tenant_id AND m.alert_id=a.id AND m.id=$3
            JOIN socai2.artifacts f ON f.tenant_id=a.tenant_id AND f.alert_id=a.id AND f.id=$4
            JOIN socai2.incident_alerts ia ON ia.tenant_id=a.tenant_id AND ia.alert_id=a.id
            WHERE a.tenant_id=$1 AND a.id=$2""", tenant, aid, mid, projection.snapshot_id(aid))
        if body is None:
            raise ReceiptHold("saved_receipt_material_unproven")
        _, _, _, version = decode(body["raw_text"].encode())
        if version != saved["source_version"]:
            raise ReceiptHold("saved_receipt_content_conflict")
        restore_snapshot(decoded(body["content_json"]), alert, max_bytes=self.sink.snapshot_max_bytes)
        tasks = []
        for kind, subject_type, identity in (("alert_triage", "alert", aid), ("incident_diagnosis", "incident", body["incident_id"])):
            task = await conn.fetchval("""SELECT id FROM socai2.analysis_tasks
                WHERE tenant_id=$1 AND kind=$2 AND operation_key=$3 AND subject_id=$4""",
                tenant, kind, initial_key(identity, subject_type), identity)
            tasks.append(str(task) if task else None)
        if tasks[0] is None:
            raise ReceiptHold("initial_alert_task_unproven")
        return ReceiveResult(state, alert_id=str(aid), material_id=str(mid), incident_id=str(body["incident_id"]),
                             initial_alert_task_id=tasks[0], initial_incident_task_id=tasks[1])

    async def lookup_receipt(self, row, *, decision=None):
        """Read a committed first receipt without re-running Fusion or writing."""
        try:
            alert = adapt_alert(row, self.selection, self.policy, decision=decision)
            lake = lake_input(alert)
            pool = await self.sink._ensure_pool()
            if pool is None:
                return ReceiveResult("unknown", "receiver_database_unavailable")
            async with asyncio.timeout(self.policy.body["limits"]["receive_timeout_seconds"]):
                async with pool.acquire() as conn, conn.transaction(readonly=True):
                    if await conn.fetchval("SELECT current_database()") != self.policy.body["postgres_database"]:
                        raise ReceiptHold("receiver_database_mismatch")
                    await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(alert.tenant_id))
                    saved = await conn.fetchrow("""SELECT * FROM socai2.lake_alert_receipts
                        WHERE tenant_id=$1 AND source_subject_id=$2""", alert.tenant_id, alert.source_alert_id)
                    if saved is None:
                        return ReceiveResult("absent", "committed_receipt_not_observed")
                    if any(saved[k] != v for k,v in {
                            "source_event_id": lake["source_event_id"], "source_namespace": lake["lake_ref"]["source_namespace"],
                            "lake_database": lake["lake_database"], "alert_id": alert.id}.items()):
                        raise ReceiptHold("global_source_identity_scope_conflict")
                    if saved["source_version"] != lake["lake_ref"]["source_version"]:
                        raise ReceiptHold("immutable_source_content_conflict")
                    return await self._read_receipt(conn, saved, alert, state="duplicate")
        except (ReceiptHold, DeliveryHold):
            return ReceiveResult("held", "saved_receipt_not_proven")
        except Exception:  # noqa: BLE001 -- a failed observation never proves absence.
            return ReceiveResult("unknown", "receipt_lookup_unconfirmed")

    async def receive(self, row, *, decision=None):
        committing = False
        try:
            alert = adapt_alert(row, self.selection, self.policy, decision=decision)
            lake = lake_input(alert)
            pool = await self.sink._ensure_pool()
            if pool is None:
                return ReceiveResult("failed", "receiver_database_unavailable")
            async with asyncio.timeout(self.policy.body["limits"]["receive_timeout_seconds"]):
                async with pool.acquire() as conn, conn.transaction():
                    if await conn.fetchval("SELECT current_database()") != self.policy.body["postgres_database"]:
                        raise ReceiptHold("receiver_database_mismatch")
                    await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(alert.tenant_id))
                    await conn.execute("SELECT set_config('lock_timeout',$1,true)", str(self.policy.body["limits"]["lock_timeout_seconds"])+"s")
                    mid = projection.material_id(alert)
                    inserted = await conn.fetchval("""INSERT INTO socai2.lake_alert_receipts
                        (source_subject_id,tenant_id,source_event_id,source_namespace,lake_database,source_version,alert_id,material_id,lake_ref)
                        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb)
                        ON CONFLICT (source_subject_id) DO NOTHING RETURNING source_subject_id""",
                        alert.source_alert_id, alert.tenant_id, lake["source_event_id"], lake["lake_ref"]["source_namespace"],
                        lake["lake_database"], lake["lake_ref"]["source_version"], alert.id, mid, encoded(lake["lake_ref"]))
                    saved = await conn.fetchrow("""SELECT * FROM socai2.lake_alert_receipts
                        WHERE tenant_id=$1 AND source_subject_id=$2""", alert.tenant_id, alert.source_alert_id)
                    if saved is None or any(saved[k] != v for k,v in {
                            "source_event_id": lake["source_event_id"], "source_namespace": lake["lake_ref"]["source_namespace"],
                            "lake_database": lake["lake_database"], "alert_id": alert.id}.items()):
                        raise ReceiptHold("global_source_identity_scope_conflict")
                    if saved["source_version"] != lake["lake_ref"]["source_version"]:
                        raise ReceiptHold("immutable_source_content_conflict")
                    if inserted is not None:
                        if await conn.fetchval("SELECT 1 FROM socai2.alerts WHERE tenant_id=$1 AND id=$2", alert.tenant_id, alert.id):
                            raise ReceiptHold("existing_alert_without_lake_receipt")
                        fused = await self._fuse(alert)
                        snapshot = make_snapshot(fused, max_bytes=self.sink.snapshot_max_bytes)
                        if await self.sink._write(conn, fused, alert, snapshot) is not PersistOutcome.INSERTED:
                            raise ReceiptHold("first_lake_receipt_not_inserted")
                    result = await self._read_receipt(conn, saved, alert, state="created" if inserted else "duplicate")
                    committing = True
            return result
        except ReceiptHold as exc:
            return ReceiveResult("held", str(exc))
        except DeliveryHold:
            return ReceiveResult("held", "fusion_first_result_unproven_or_over_budget")
        except asyncpg.PostgresError as exc:
            # A server constraint/serialization rejection proves rollback. A
            # connection loss while committing does not prove the outcome.
            uncertain = committing and (exc.sqlstate or "")[:2] not in {"23", "40"}
            return ReceiveResult("unknown" if uncertain else "failed",
                                 "receiver_commit_unconfirmed" if uncertain else "receiver_transaction_rejected")
        except Exception:  # noqa: BLE001 -- never expose source/DSN through exception text.
            return ReceiveResult("unknown" if committing else "failed", "receiver_commit_unconfirmed" if committing else "receiver_execution_failed")
