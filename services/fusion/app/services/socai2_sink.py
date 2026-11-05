"""Explicit new-schema sink. A single transaction owns all ingestion facts.

No dual write or fallback to public.alerts. The first delivery stays immutable;
different received material creates a new immutable revision, never a rewrite.
"""
import json
from uuid import uuid5

import structlog

from app.models.alert import FusionDecision
from app.services import socai2_projection as p
from app.services.alert_sink import AlertSink, PersistOutcome, PersistResult
from app.services.delivery_recovery import (
    MAX_SNAPSHOT_BYTES,
    DeliveryHold,
    SnapshotLookup,
    make_snapshot,
    restore_snapshot,
)

logger = structlog.get_logger()
JSON_FIELDS = frozenset({"raw_json", "ocsf_json", "detection", "enrichment", "source_scope", "retention",
    "attributes", "correlation_basis", "content_json", "source_refs"})


def decoded(value):
    return json.loads(value) if isinstance(value, str) else value


async def insert(conn, table, values, *, conflict=False):
    # Both table and column names are internal constants, never request input.
    columns = list(values)
    args = [p.encoded(v) if key in JSON_FIELDS and v is not None else v for key, v in values.items()]
    sql = f"INSERT INTO socai2.{table} ({','.join(columns)}) VALUES ({','.join('$' + str(i+1) for i in range(len(args)))})"
    return await conn.fetchval(sql + (" ON CONFLICT (id) DO NOTHING" if conflict else "") + " RETURNING id", *args)


class Socai2AlertSink(AlertSink):
    async def lookup_delivery(self, alert):
        pool = await self._ensure_pool()
        if pool is None:
            raise DeliveryHold("socai2 delivery database unavailable")
        try:
            async with pool.acquire() as conn, conn.transaction(readonly=True):
                await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(alert.tenant_id))
                row = await conn.fetchrow("""SELECT a.id,f.content_json FROM socai2.alerts a
                    LEFT JOIN socai2.artifacts f ON f.tenant_id=a.tenant_id AND f.alert_id=a.id AND f.id=$3
                    WHERE a.tenant_id=$1 AND a.id=$2 AND a.source_namespace=$4 AND a.source_identity_key=$5""",
                    alert.tenant_id, alert.deterministic_id(), p.snapshot_id(alert.deterministic_id()),
                    p.STORE_NAMESPACE, alert.fingerprint())
                if row is None:
                    return SnapshotLookup(False)
                snapshot = decoded(row["content_json"])
                if snapshot is not None:
                    restore_snapshot(snapshot, alert)
                return SnapshotLookup(True, snapshot, str(row["id"]))
        except DeliveryHold:
            raise
        except Exception as exc:
            raise DeliveryHold("socai2 delivery lookup failed") from exc

    async def persist(self, fused, *, replay=None, delivery_snapshot=None):
        alert = replay if replay is not None else fused.alert
        if (alert.tenant_id != fused.tenant_id or alert.fingerprint() != fused.alert.fingerprint()
                or fused.fusion_decision == FusionDecision.DUPLICATE):
            return PersistResult(PersistOutcome.FAILED)
        pool = await self._ensure_pool()
        if pool is None:
            return PersistResult(PersistOutcome.UNAVAILABLE, str(fused.id))
        try:
            snapshot = delivery_snapshot if delivery_snapshot is not None else make_snapshot(fused)
            restored = restore_snapshot(snapshot, fused.alert)
            if restored.model_dump(mode="json") != fused.model_dump(mode="json"):
                raise DeliveryHold("socai2 snapshot differs from fused result")
            if len(p.encoded(alert.model_dump(mode="json")).encode("utf-8")) > MAX_SNAPSHOT_BYTES:
                raise DeliveryHold("socai2 received material exceeds delivery bound")
            async with pool.acquire() as conn, conn.transaction():
                await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(alert.tenant_id))
                outcome = await self._write(conn, fused, alert, snapshot)
            # Return durable only after COMMIT (including deferred checks).
            return PersistResult(outcome, str(fused.id))
        except Exception as exc:  # noqa: BLE001 -- one row failure is observable, never a durable duplicate
            logger.error("socai2_sink.persist_failed", error_type=type(exc).__name__)
            return PersistResult(PersistOutcome.FAILED)

    async def persist_many(self, fused_batch):
        # Same transaction and recovery semantics as single writes; a bad item
        # rolls back its own transaction and cannot erase a preceding item.
        return [await self.persist(fused) for fused in fused_batch]

    async def _write(self, conn, fused, alert, snapshot):
        tenant, aid, sid = alert.tenant_id, fused.id, p.snapshot_id(fused.id)
        if alert.connector_id is not None and not await conn.fetchval(
                "SELECT 1 FROM public.connectors WHERE id=$1 AND tenant_id=$2", alert.connector_id, tenant):
            raise DeliveryHold("socai2 source connector is not in tenant")
        fields, _, _, _ = p.project(fused, alert, sid)
        inserted = await insert(conn, "alerts", {"id": aid, "tenant_id": tenant,
            "source_namespace": p.STORE_NAMESPACE, "source_identity_key": alert.fingerprint(), **fields}, conflict=True)
        row = await conn.fetchrow("SELECT * FROM socai2.alerts WHERE tenant_id=$1 AND id=$2 FOR UPDATE", tenant, aid)
        if row is None or row["source_namespace"] != p.STORE_NAMESPACE or row["source_identity_key"] != alert.fingerprint():
            raise DeliveryHold("socai2 alert identity conflict")
        now = await conn.fetchval("SELECT clock_timestamp()")
        if inserted is None:
            saved = await conn.fetchval("SELECT content_json FROM socai2.artifacts WHERE tenant_id=$1 AND alert_id=$2 AND id=$3", tenant, aid, sid)
            if saved is None:
                raise DeliveryHold("socai2 existing alert has no first delivery")
            # First committed result wins. A replay cannot change incident,
            # scores, narrative or the recoverable outbound result.
            fused = restore_snapshot(decoded(saved), alert)
        else:
            retention = p.retained(snapshot)
            await insert(conn, "artifacts", {"id": sid, "tenant_id": tenant, "alert_id": aid,
                "kind": "source_snapshot", "schema_version": "fusion.first-result.v1", "content_json": snapshot,
                "mime_type": "application/json", "sha256": retention["retained_sha256"],
                "size_bytes": retention["retained_size_bytes"], "captured_at": now, "material_state": "complete",
                "source_refs": [], "retention": retention})
        mid = uuid5(aid, p.VERSION + ":" + p.digest(p.input_value(alert)))
        if await conn.fetchval("SELECT 1 FROM socai2.alert_materials WHERE tenant_id=$1 AND alert_id=$2 AND id=$3", tenant, aid, mid):
            return PersistOutcome.DUPLICATE
        fields, material, refs, objects = p.project(fused, alert, sid)
        revision = 1 + await conn.fetchval("SELECT coalesce(max(revision),0) FROM socai2.alert_materials WHERE tenant_id=$1 AND alert_id=$2", tenant, aid)
        await insert(conn, "alert_materials", {"id": mid, "tenant_id": tenant, "alert_id": aid,
            "revision": revision, "received_at": now, "source_version": p.VERSION, **material})
        for ref in refs:
            identity = uuid5(mid, p.encoded([ref["source_namespace"], ref["source_event_id"], ref["relation_kind"]]))
            await insert(conn, "alert_source_refs", {"id": identity, "tenant_id": tenant, "alert_id": aid, "material_id": mid, **ref})
        for obj in objects:
            identity = uuid5(mid, p.encoded([obj["object_key"], obj["source_path"]]))
            await insert(conn, "alert_objects", {"id": identity, "tenant_id": tenant, "alert_id": aid, "material_id": mid, **obj})
        # The canonical alert describes the first Fusion result (as before).
        # Later received payloads have their own immutable material versions;
        # never replace operator-editable title/tags/severity on redelivery.
        await conn.execute("""UPDATE socai2.alerts SET
            latest_material_id=$3,source_updated_at=$4,business_updated_at=$4,row_version=row_version+1,
            first_seen_at=least(first_seen_at,$5),last_seen_at=greatest(last_seen_at,$5)
            WHERE tenant_id=$1 AND id=$2""", tenant, aid, mid, now, fields["event_time"])
        link = await conn.fetchrow("SELECT incident_id FROM socai2.incident_alerts WHERE tenant_id=$1 AND alert_id=$2", tenant, aid)
        if link is None:
            await insert(conn, "incidents", {"id": fused.incident_id, "tenant_id": tenant,
                "source_namespace": p.STORE_NAMESPACE, "source_incident_id": str(fused.incident_id),
                "title": "关联事件 · " + fused.alert.title}, conflict=True)
            inc = await conn.fetchrow("SELECT source_namespace,source_incident_id FROM socai2.incidents WHERE tenant_id=$1 AND id=$2 FOR UPDATE", tenant, fused.incident_id)
            if not inc or inc["source_namespace"] != p.STORE_NAMESPACE or inc["source_incident_id"] != str(fused.incident_id):
                raise DeliveryHold("socai2 incident identity conflict")
            await insert(conn, "incident_alerts", {"id": uuid5(aid, "socai2.fusion.membership.v1"),
                "tenant_id": tenant, "incident_id": fused.incident_id, "alert_id": aid,
                "linked_at": now, "membership_source": "fusion", "correlation_basis": p.correlation(fused, sid),
                "basis_version": fused.correlation_basis.policy_version if fused.correlation_basis else "unrecorded",
                "source_operation_id": sid})
        incident_id = link["incident_id"] if link else fused.incident_id
        await conn.execute("""UPDATE socai2.incidents SET business_updated_at=greatest(business_updated_at,$3),row_version=row_version+1
            WHERE tenant_id=$1 AND id=$2""", tenant, incident_id, now)
        return PersistOutcome.INSERTED if inserted is not None else PersistOutcome.DUPLICATE
