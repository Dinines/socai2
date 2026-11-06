"""Fixed November 6 audit fixture. plan/inputs are offline; seed/verify use the r3 image.

Supply this script on stdin to a one-shot r3 Python process. No code from
observations executes. Kafka, lake writer, model, A/I and Case jobs are outside this writer.
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5

BATCH = "ie-audit-20261106-a1"
TENANT = uuid5(NAMESPACE_URL, "socai2-processing-handoff:tenant")
ACTOR = uuid5(NAMESPACE_URL, "socai2-processing-handoff:actor")
DATABASE = "socai2_processing_handoff"
ROLE = "socai2_processing_job"
KEYS = ("m01", "s02", "u03")
TITLES = ("Web 证书替换", "审计策略及安全日志变更", "出站 TCP 会话")
IMAGE_FUSION = Path("/opt/processor/smoke-fusion")


def identity(key, part):
    return uuid5(TENANT, f"{BATCH}:{key}:{part}")


def observations(key):
    if key == "m01":
        return [("Web 证书替换完成", "low", {"class_uid": 6003,
                "actor": {"user": {"name": "svc-certmgr"}},
                "activity": {"action": "certificate_replace", "outcome": "success"},
                "change_record": {"id": "CR-261106-031", "state": "approved", "authorized_actor": "svc-certmgr",
                                  "scope": "replace web TLS certificate on edge-a17", "service": "edge-web"}})]
    if key == "s02":
        return [
            ("禁用登录审计的命令已启动", "high", {"class_uid": 1007,
             "process": {"name": "auditpol.exe", "cmd_line": "auditpol /set /subcategory:Logon /success:disable /failure:disable"},
             "actor": {"user": {"name": "temp-svc"}},
             "activity": {"action": "process_start", "outcome": "success"}}),
            ("安全日志文件清零", "high", {"class_uid": 1001,
             "actor": {"user": {"name": "temp-svc"}},
             "file": {"path": "C:/Windows/System32/winevt/Logs/Security.evtx", "size": 0, "previous_size": 786432},
             "activity": {"action": "file_truncate", "outcome": "success"}}),
        ]
    return [("记录到出站 TCP 会话", "medium", {"class_uid": 4001,
            "src_endpoint": {"ip": "192.0.2.63"}, "dst_endpoint": {"ip": "203.0.113.47", "port": 8443},
            "connection_info": {"protocol_name": "TCP"}, "activity": {"action": "connect", "outcome": "success"}})]


def fixtures():
    from app.models.alert import FusedAlert, FusionDecision, RawAlert

    cards = []
    for k, key in enumerate(KEYS):
        host = ("edge-a17", "win-c23", "ws-b63")[k]
        incident = identity(key, "incident")
        start = datetime(2026, 11, 6, 5, 20 + k * 10, tzinfo=UTC)
        fused_records = []
        lake_events = []
        for index, (title, severity, event) in enumerate(observations(key)):
            stamp = start + timedelta(seconds=30 * index)
            ocsf = {**event, "device": {"name": host}, "time": stamp.isoformat()}
            raw_event = {"tenant_id": str(TENANT), "event_time": stamp.isoformat(), "ocsf_event": ocsf}
            if key != "u03":
                source_id = str(identity(key, f"event-{index}"))
                raw_event["event_id"] = source_id
                ocsf["metadata"] = {"uid": source_id}
                lake_events.append(raw_event)
            alert = RawAlert(tenant_id=TENANT, source=BATCH, identity_version="source-v1",
                source_alert_id=identity(key, f"source-alert-{index}"), title=title, severity=severity,
                external_id=f"IE-26-{k + 1:02d}-{index + 1}", rule_id=f"edge-event-{k + 1}{index + 1}",
                rule_name=title, hostname=host, username=ocsf.get("actor", {}).get("user", {}).get("name"),
                src_ip=ocsf.get("src_endpoint", {}).get("ip"), dst_ip=ocsf.get("dst_endpoint", {}).get("ip"),
                ocsf_class_uid=ocsf["class_uid"], event_time=stamp, created_at=stamp, raw_event=raw_event,
                source_event_ids=[raw_event["event_id"]] if "event_id" in raw_event else [])
            alert.id = alert.deterministic_id()
            fused_records.append(FusedAlert(id=alert.id, incident_id=incident, tenant_id=TENANT, alert=alert,
                fused_at=stamp, fusion_decision=FusionDecision.NEW_INCIDENT if not index else FusionDecision.CORRELATED))
        create = identity(key, "create")
        card = {"key": key, "title": TITLES[k], "hostname": host, "incident_id": incident,
                "alert_ids": [record.id for record in fused_records], "case_id": uuid5(TENANT, "socai2.case.create:" + str(create)),
                "window_start": (start - timedelta(seconds=30)).isoformat(), "window_end": (start + timedelta(minutes=1)).isoformat(),
                "lake_events": lake_events,
                "operation_keys": {"alerts": [identity(key, f"analyze-{i}") for i in range(len(fused_records))],
                                   "incident": identity(key, "diagnose"), "create": create,
                                   "prepare": identity(key, "prepare"), "start": identity(key, "start")}}
        cards.append((card, fused_records))
    return cards


def manifest(cards):
    return {"batch": BATCH, "tenant_id": TENANT, "source": BATCH, "source_namespace": "fusion.v1",
            "source_boundary": "Authored fused alerts / Fusion PG sink; no Kafka consumption or lake writes",
            "cases": [c for c, _ in cards]}


class AuditError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise AuditError(code)


async def check_record(conn, fused):
    from app.services import socai2_projection as projection
    from app.services.delivery_recovery import make_snapshot
    from app.services.socai2_sink import decoded

    alert = fused.alert
    sid = projection.snapshot_id(alert.id)
    _, material, refs, objects = projection.project(fused, alert, sid)
    row = await conn.fetchrow("""SELECT a.title,a.event_time,a.source_alert_id,a.source_identity_key,a.source_namespace,
        m.id,m.revision,m.sha256,m.raw_json,m.ocsf_json,m.detection,m.enrichment,m.source_scope,m.retention,m.material_state,
        ia.incident_id,f.content_json,f.sha256 AS snapshot_sha,
        (SELECT count(*) FROM socai2.alert_materials x WHERE x.tenant_id=a.tenant_id AND x.alert_id=a.id) AS versions,
        (SELECT count(*) FROM socai2.alert_objects x WHERE x.tenant_id=a.tenant_id AND x.material_id=m.id) AS objects,
        (SELECT count(*) FROM socai2.alert_source_refs x WHERE x.tenant_id=a.tenant_id AND x.material_id=m.id) AS refs
        FROM socai2.alerts a JOIN socai2.alert_materials m ON (m.tenant_id,m.alert_id,m.id)=(a.tenant_id,a.id,a.latest_material_id)
        JOIN socai2.incident_alerts ia ON (ia.tenant_id,ia.alert_id)=(a.tenant_id,a.id)
        JOIN socai2.artifacts f ON (f.tenant_id,f.alert_id,f.id)=(a.tenant_id,a.id,$3)
        WHERE a.tenant_id=$1 AND a.id=$2""", TENANT, alert.id, sid)
    require(row and row["source_namespace"] == projection.STORE_NAMESPACE and row["title"] == alert.title
            and row["event_time"] == alert.event_time and row["source_alert_id"] == str(alert.source_alert_id)
            and row["source_identity_key"] == alert.fingerprint() and row["incident_id"] == fused.incident_id,
            "alert_or_membership_mismatch")
    require(row["versions"] == row["revision"] == 1 and row["objects"] == len(objects)
            and row["refs"] == len(refs) and row["sha256"] == material["sha256"]
            and row["material_state"] == "complete", "stored_material_identity_mismatch")
    for field in ("raw_json", "ocsf_json", "detection", "enrichment", "source_scope", "retention"):
        require(decoded(row[field]) == material[field], "material_field_mismatch_" + field)
    snapshot = make_snapshot(fused)
    require(decoded(row["content_json"]) == snapshot and row["snapshot_sha"] == projection.digest(snapshot),
            "stored_fusion_snapshot_mismatch")
    recorded_refs = await conn.fetch("SELECT source_event_id FROM socai2.alert_source_refs WHERE tenant_id=$1 AND material_id=$2",
                                     TENANT, row["id"])
    require(sorted(r["source_event_id"] for r in recorded_refs) == sorted(alert.source_event_ids), "source_ids_mismatch")
    return {"alert_id": alert.id, "material_id": row["id"], "sha256": row["sha256"],
            "snapshot_id": sid, "snapshot_sha256": row["snapshot_sha"], "object_count": len(objects),
            "source_event_ids": alert.source_event_ids}


async def run(phase, cards):
    from app.services.socai2_sink import Socai2AlertSink

    dsn = urlsplit(os.environ["DATABASE_URL"])
    require((dsn.hostname, dsn.path, dsn.username) == ("192.168.1.21", "/" + DATABASE, ROLE), "unexpected_target")
    sink = Socai2AlertSink(os.environ["DATABASE_URL"], pool_size=2)
    await sink.start()
    try:
        require(sink._pool is not None, "missing_pool")
        async with sink._pool.acquire() as conn, conn.transaction(readonly=phase == "verify"):
            await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(TENANT))
            target = await conn.fetchval("""SELECT current_database()=$1 AND current_user=$2 AND
                NOT (rolsuper OR rolcreaterole OR rolcreatedb OR rolbypassrls) AND EXISTS
                (SELECT 1 FROM public.users WHERE tenant_id=$3 AND id=$4 AND is_active)
                FROM pg_roles WHERE rolname=current_user""", DATABASE, ROLE, TENANT, ACTOR)
            require(target, "runtime_identity_mismatch")
            if phase == "seed":
                require(await conn.fetchval("SELECT pg_try_advisory_xact_lock(hashtext($1),hashtext($2))",
                        str(TENANT), BATCH), "concurrent_fixture_seed")
            results = []
            for card, records in cards:
                expected = set(card["alert_ids"])
                members = await conn.fetch("SELECT alert_id FROM socai2.incident_alerts WHERE tenant_id=$1 AND incident_id=$2",
                                           TENANT, card["incident_id"])
                require({r["alert_id"] for r in members} <= expected, "foreign_incident_member")
                for fused in records:
                    exists = await conn.fetchval("SELECT EXISTS(SELECT FROM socai2.alerts WHERE tenant_id=$1 AND id=$2)",
                                                 TENANT, fused.id)
                    if not exists:
                        require(phase == "seed", "missing_frozen_input")
                        require(not await conn.fetchval("""SELECT EXISTS(SELECT FROM socai2.runs WHERE tenant_id=$1 AND
                            (alert_id=ANY($2::uuid[]) OR incident_id=$3 OR case_id=$4))""",
                            TENANT, card["alert_ids"], card["incident_id"], card["case_id"]), "processing_already_started")
                        require((await sink.persist(fused)).durable, "fusion_write_failed")
                    receipt = await check_record(conn, fused)
                    results.append({**receipt, "case_key": card["key"], "newly_inserted": not exists})
                members = await conn.fetch("SELECT alert_id FROM socai2.incident_alerts WHERE tenant_id=$1 AND incident_id=$2",
                                           TENANT, card["incident_id"])
                require({r["alert_id"] for r in members} == expected, "membership_readback_failed")
            return {"batch": BATCH, "phase": phase, "cases": len(cards), "rows": results, "model_calls": 0, "lake_writes": 0}
    finally:
        await sink.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["plan", "inputs", "seed", "verify"])
    args = parser.parse_args()
    if IMAGE_FUSION.is_dir():
        sys.path.insert(0, str(IMAGE_FUSION))
    elif args.phase not in {"plan", "inputs"}:
        raise AuditError("installed_fusion_package_required")
    cards = fixtures()
    if args.phase == "plan":
        result = manifest(cards)
    elif args.phase == "inputs":
        result = {c["key"]: [f.model_dump(mode="json") for f in records] for c, records in cards}
    else:
        result = asyncio.run(run(args.phase, cards))
    print(json.dumps(result, ensure_ascii=False, default=str, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 -- driver details may contain connection credentials.
        # Do not emit service configuration or driver errors that could include credentials.
        print(json.dumps({"error": str(exc) if isinstance(exc, AuditError) else type(exc).__name__}))
        sys.exit(1)
