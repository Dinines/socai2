"""Read-only S01 checks against this batch's frozen candidate and real sources."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import asyncpg
from clickhouse_driver import Client

TABLES = ("alerts", "alert_materials", "alert_source_refs", "incidents", "incident_alerts",
          "analysis_tasks", "analysis_attempts", "runs", "cases", "artifacts",
          "alert_assessments", "incident_diagnoses", "results")


def check(value, label):
    if not value:
        raise AssertionError(label)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
        stream.write("\n")


def load_inputs(batch):
    cfg = json.loads((batch / "ingress.json").read_text())
    manifest = json.loads((batch / "prepared/manifest.json").read_text())
    dataset = json.loads((batch / "dataset/manifest.json").read_text())
    check(digest(batch / "dataset/manifest.json") == manifest["dataset_manifest_sha256"], "dataset_manifest_changed")
    check(digest(batch / "dataset/expected.json") == dataset["controls"]["expected.json"], "expected_changed")
    check(digest(batch / "prepared/resource-readback.json") == manifest["resource_readback_sha256"], "ready_changed")
    for name, expected in dataset["inputs"].items():
        check(digest(batch / "dataset" / name) == expected, "input_changed")
    check(not cfg["models_enabled"] and not cfg["dispatcher_enabled"], "execution_must_remain_disabled")
    check(cfg["candidate_id"] == manifest["candidate_id"], "candidate_mismatch")
    events = [json.loads(line) for line in (batch / "dataset/S01/context-events.jsonl").read_text().splitlines()]
    alerts = [json.loads(line) for line in (batch / "dataset/S01/alerts.jsonl").read_text().splitlines()]
    return cfg, manifest, dataset, events, alerts


async def pg_snapshot(cfg, tenant, connector):
    private = json.loads(Path(cfg["postgres"]["private_runtime"]).read_text())
    dsn = private["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(dsn, timeout=cfg["timeout_seconds"],
                                 command_timeout=cfg["postgres"]["statement_timeout_seconds"])
    try:
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", tenant)
            identity = dict(await conn.fetchrow("""SELECT current_database() AS database,
                current_user AS role, current_setting('transaction_read_only') AS readonly,
                ssl,version FROM pg_stat_ssl WHERE pid=pg_backend_pid()"""))
            check(identity["database"] == cfg["postgres"]["database"], "wrong_pg_database")
            check(identity["role"] == cfg["postgres"]["reader"], "wrong_pg_reader")
            check(identity["readonly"] == "on" and identity["ssl"], "pg_not_readonly_tls")
            rows = {}
            for table in TABLES:
                values = await conn.fetch("SELECT row_to_json(t) AS row FROM socai2." + table
                                          + " t WHERE tenant_id=$1 ORDER BY id", UUID(tenant))
                rows[table] = [json.loads(row["row"]) for row in values]
            found = await conn.fetch("SELECT id,tenant_id FROM public.connectors WHERE tenant_id=$1 AND id=$2",
                                     UUID(tenant), UUID(connector))
            return {"identity": identity, "counts": {key: len(value) for key, value in rows.items()},
                    "connector": [dict(row) for row in found], "rows": rows}
    finally:
        await conn.close()


def lake_snapshot(cfg, tenant, query):
    lake = cfg["clickhouse"]
    private = json.loads(Path(lake["private_runtime"]).read_text())["reader"]
    client = Client(host=lake["host"], port=lake["native_port"], database=lake["database"],
                    user=private["user"], password=private["password"],
                    connect_timeout=cfg["timeout_seconds"], send_receive_timeout=cfg["timeout_seconds"],
                    settings={"readonly": 1, "max_execution_time": cfg["timeout_seconds"]})
    try:
        who = client.execute("SELECT currentDatabase(),currentUser()")[0]
        check(who == (lake["database"], lake["reader"]), "wrong_lake_identity")
        values, columns = client.execute("SELECT *,toUnixTimestamp64Milli(event_time) AS event_time_ms FROM "
            + lake["table"] + " WHERE tenant_id=%(tenant)s ORDER BY event_id", {"tenant": tenant}, with_column_types=True)
        rows = [dict(zip([col[0] for col in columns], value, strict=True)) for value in values]
        hits = {}
        for name, kind in (("authentication_activity", 3002), ("process_activity", 1007), ("network_connections", 4001)):
            result = client.execute("SELECT event_id FROM " + lake["table"] + " WHERE tenant_id=%(tenant)s "
                "AND src_hostname=%(host)s AND class_uid=%(kind)s "
                "AND event_time>=toDateTime64(%(start)s,3,'UTC') AND event_time<toDateTime64(%(end)s,3,'UTC') "
                "ORDER BY event_id", {"tenant": tenant, "host": query["hostname"], "kind": kind,
                    "start": datetime.fromisoformat(query["window_start"]).astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S.%f"),
                    "end": datetime.fromisoformat(query["window_end"]).astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")})
            hits[name] = [str(row[0]) for row in result]
        return {"identity": {"database": who[0], "role": who[1]}, "rows": rows,
                "query": query, "hits": hits}
    finally:
        client.disconnect()


def verify_lake(lake, events, dataset, expected):
    rows = lake["rows"]
    check(len(rows) == 12, "lake_expected_exactly_12")
    by_id = {str(row["event_id"]): row for row in rows}
    check(set(by_id) == {event["event_id"] for event in events}, "lake_event_ids")
    for event in events:
        row, original = by_id[event["event_id"]], event["ocsf_event"]
        check(str(row["tenant_id"]) == event["tenant_id"], "lake_tenant")
        check(row["src_hostname"] == original["device"]["name"], "lake_hostname")
        check(row["user_name"] == original["actor"]["user"]["name"], "lake_account")
        check(row["class_uid"] == original["class_uid"] and row["activity_id"] == 0, "lake_class_activity")
        check(row["event_time_ms"] == round(datetime.fromisoformat(original["time"]).timestamp() * 1000), "lake_time_precision")
        check(row["raw_payload"] == original["raw_data"], "lake_raw_text")
        saved = json.loads(row["ocsf_json"])
        check(all(saved.get(k) == v for k, v in original.items()), "lake_original_fields")
        check(saved["_socai2_storage"]["raw_payload"]["truncated"] is False, "lake_truncated")
        check(saved["_socai2_storage"]["event_time_fallback"] is False, "lake_fallback_time")
    zero = json.loads(by_id[dataset["logical_ids"]["E07"]]["ocsf_json"])
    check(all(value == 0 for value in zero["traffic"].values()), "zero_traffic_lost")
    check(zero["sensor_observation"] == {"connection_reset": False, "dns_answers": []}, "false_or_empty_lost")
    for name, logical in expected["queries"]["S01_full_host"]["included"].items():
        check(set(lake["hits"][name]) == {dataset["logical_ids"][key] for key in logical}, "query_members_" + name)


def verify_alerts(pg, alerts, dataset, expected, cfg):
    counts, rows = pg["counts"], pg["rows"]
    wanted = {"alerts": 3, "alert_materials": 3, "alert_source_refs": 3, "incidents": 1,
              "incident_alerts": 3, "analysis_tasks": 4, "artifacts": 3}
    check(counts == {table: wanted.get(table, 0) for table in TABLES}, "business_counts")
    check(len(pg["connector"]) == 1, "connector_missing")
    incident = rows["incidents"][0]
    tasks = {row["subject_id"]: row for row in rows["analysis_tasks"]}
    check(len(tasks) == 4, "task_subjects")
    for task in tasks.values():
        check((task["state"], task["source"], task["intent"]) == ("accepted", "ingress", "initial"), "task_admission")
        check(task["started_at"] is None and task["retry_count"] == 0, "task_not_started")
        check(all(task[key] == value for key, value in cfg["initial_task_policy"].items()), "task_policy")
    mapping = {"alerts": {}, "incidents": {"I01": {"incident_id": incident["id"],
        "task_id": tasks[incident["id"]]["id"], "members": []}}, "cases": {}, "runs": {}}
    it = tasks[incident["id"]]
    check((it["subject_type"], it["kind"]) == ("incident", "incident_diagnosis"), "incident_initial_task")
    for index, alert in enumerate(alerts, 1):
        logical = f"A{index:02d}"
        candidates = [row for row in rows["alerts"] if row["source_alert_id"] == alert["id"]]
        check(len(candidates) == 1, "source_to_canonical")
        canonical = candidates[0]
        aid = canonical["id"]
        check(aid == expected["predicted_canonical_alert_ids"][logical], "canonical_identity_contract")
        check(canonical["connector_id"] == alert["connector_id"], "canonical_connector")
        material = [row for row in rows["alert_materials"] if row["alert_id"] == aid]
        member = [row for row in rows["incident_alerts"] if row["alert_id"] == aid]
        refs = [row for row in rows["alert_source_refs"] if row["alert_id"] == aid]
        artifacts = [row for row in rows["artifacts"] if row["alert_id"] == aid]
        check(len(material) == len(member) == len(refs) == len(artifacts) == 1, "alert_relationship_counts")
        material, member, ref, artifact = material[0], member[0], refs[0], artifacts[0]
        check(canonical["latest_material_id"] == material["id"] and material["revision"] == 1, "latest_material")
        check(material["raw_json"]["raw_event"] == alert["raw_event"], "alert_raw_original")
        check(material["ocsf_json"] == alert["raw_event"]["ocsf_event"], "alert_ocsf_original")
        check(material["raw_text"] == alert["raw_event"]["ocsf_event"]["raw_data"], "alert_raw_text")
        scope = material["source_scope"]
        check(scope["received_count"] == scope["retained_count"] == 1 and scope["complete"] is True
              and scope["truncated"] is False, "material_source_scope")
        check(material["material_state"] == "complete" and material["retention"]["truncated"] is False, "material_retention")
        check(ref["source_event_id"] == alert["source_event_ids"][0]
              and ref["material_id"] == material["id"] and ref["relation_kind"] == "source_event", "source_reference")
        check(member["incident_id"] == incident["id"] and member["membership_source"] == "fusion", "incident_membership")
        check(artifact["kind"] == "source_snapshot" and artifact["material_state"] == "complete", "first_snapshot")
        task = tasks[aid]
        check((task["subject_type"], task["kind"]) == ("alert", "alert_triage"), "alert_initial_task")
        mapping["alerts"][logical] = {"source_alert_id": canonical["source_alert_id"], "alert_id": aid,
            "material_id": material["id"], "source_event_id": ref["source_event_id"],
            "incident_id": member["incident_id"], "task_id": task["id"], "artifact_id": artifact["id"]}
        mapping["incidents"]["I01"]["members"].append(aid)
    return mapping


async def main(batch, mode):
    cfg, manifest, dataset, events, alerts = load_inputs(batch)
    expected = json.loads((batch / "dataset/expected.json").read_text())
    out = batch / "readback"
    out.mkdir(exist_ok=True)
    receipt = out / (mode + "-readback.json")
    check(not receipt.exists(), "readback_already_recorded")
    result = {"status": "running", "mode": mode, "batch_id": manifest["batch_id"],
        "tenant_id": manifest["tenant_id"], "candidate_id": manifest["candidate_id"],
        "started_at": datetime.now(UTC).isoformat(), "prepared_manifest_sha256": digest(batch / "prepared/manifest.json"),
        "readback_source_sha256": digest(Path(__file__)), "ingress_sha256": digest(batch / "ingress.json"),
        "model_calls": 0, "model_evidence": "dispatcher/models disabled; attempts and runs checked as zero"}
    try:
        deadline = time.monotonic() + cfg["timeout_seconds"]
        while True:
            pg = await pg_snapshot(cfg, manifest["tenant_id"], alerts[0]["connector_id"])
            lake = lake_snapshot(cfg, manifest["tenant_id"], expected["queries"]["S01_full_host"])
            arrived = len(lake["rows"]) >= 12 if mode == "context" else pg["counts"]["analysis_tasks"] >= 4
            if mode == "preflight" or arrived or time.monotonic() >= deadline:
                break
            await asyncio.sleep(1)
        save(out / (mode + "-pg.json"), pg)
        save(out / (mode + "-lake.json"), lake)
        result.update(pg_counts=pg["counts"], lake_rows=len(lake["rows"]),
            snapshots={name: digest(out / (mode + "-" + name + ".json")) for name in ("pg", "lake")})
        if mode == "preflight":
            check(not any(pg["counts"].values()) and not lake["rows"], "candidate_not_empty")
            check(len(pg["connector"]) == 1, "connector_missing")
        elif mode == "context":
            verify_lake(lake, events, dataset, expected)
            check(not any(pg["counts"].values()), "context_created_business_records")
            result.update(source="real_lake_readback", event_ids=[event["event_id"] for event in events],
                unexpected_alerts=0, unexpected_incidents=0, unexpected_tasks=0, attempts=0, runs=0)
        else:
            mapping = verify_alerts(pg, alerts, dataset, expected, cfg)
            save(out / "identity-map.json", {"status": "passed", "source": "real_postgres_readback",
                "batch_id": manifest["batch_id"], "tenant_id": manifest["tenant_id"],
                "prepared_manifest_sha256": result["prepared_manifest_sha256"],
                "postgres_snapshot_sha256": result["snapshots"]["pg"], "actual_mappings": mapping})
        result["status"] = "passed"
    except Exception as exc:  # noqa: BLE001 -- save bounded failure, never secret exception strings
        result.update(status="failed", error_type=type(exc).__name__, sqlstate=getattr(exc, "sqlstate", None),
                      check=str(exc) if isinstance(exc, AssertionError) else None)
    result["ended_at"] = datetime.now(UTC).isoformat()
    save(receipt, result)
    print(json.dumps({key: result.get(key) for key in ("status", "mode", "batch_id", "pg_counts", "lake_rows", "error_type", "check")}))
    return result["status"] == "passed"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--mode", choices=("preflight", "context", "alerts"), required=True)
    args = parser.parse_args()
    raise SystemExit(0 if asyncio.run(main(args.batch, args.mode)) else 1)
