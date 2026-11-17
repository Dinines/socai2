"""S04's two real source gates; no investigation, repair, or fabricated identity."""
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from readback_support import (
    TABLES,
    check,
    digest,
    lake_snapshot,
    normalized,
    pg_snapshot,
    save,
)


def read(path):
    return json.loads(path.read_text())


def compare(before, after, *, incident=None):
    added = {}
    for table, original in before.items():
        if table not in TABLES:
            continue
        current = {v["id"]: v for v in after[table]}
        old = {v["id"]: v for v in original}
        for key, value in old.items():
            check(key in current, "old_identity_missing_" + table)
            omit = {"business_updated_at", "row_version"} if table == "incidents" and key == incident else set()
            check({k: v for k, v in value.items() if k not in omit}
                  == {k: v for k, v in current[key].items() if k not in omit}, "old_record_changed_" + table)
        added[table] = [v for v in current.values() if v["id"] not in old]
    return added


def verify_event(row, original):
    check(str(row["event_id"]) == original["event_id"] and str(row["tenant_id"]) == original["tenant_id"], "event_identity")
    value = original["ocsf_event"]
    check(row["raw_payload"] == value["raw_data"], "event_raw_text")
    saved = json.loads(row["ocsf_json"])
    check(all(saved.get(k) == v for k, v in value.items()), "event_original_fields")
    check(row["event_time_ms"] == round(datetime.fromisoformat(value["time"]).timestamp() * 1000), "event_millisecond_time")
    check(row["src_hostname"] == value["device"]["name"] and row["user_name"] == value["actor"]["user"]["name"], "event_host_account")
    check(saved["sensor_observation"] == {"connection_reset": False, "dns_answers": []}, "false_and_empty_preserved")
    check(saved["_socai2_storage"]["raw_payload"]["truncated"] is False, "event_not_truncated")


async def main(folder, mode):
    cfg, expected, manifest = (read(folder / n) for n in ("ingress.json", "expected.json", "prepared/manifest.json"))
    profile = read(folder / "prepared/profile.json")
    baseline = read(folder / "case-initial-pg.json")
    baseline_sha = digest(folder / "case-initial-pg.json")
    check(baseline_sha == profile["baseline_snapshot_sha256"], "frozen_case_baseline_changed")
    check(not cfg["models_enabled"] and not cfg["dispatcher_enabled"], "dispatcher_must_remain_stopped")
    event = read(folder / "prepared/wire/S04-context/001.json")
    alert = read(folder / "prepared/wire/S04-alerts/001.json")
    check(event["event_id"] == expected["new_event_id"] and alert["id"] == expected["new_alert_source_id"], "new_identity_changed")
    out = folder / "readback"
    out.mkdir(exist_ok=True)
    receipt = out / (mode + "-readback.json")
    check(not receipt.exists(), "readback_already_saved")
    result = {"status": "started", "mode": mode, "batch_id": manifest["batch_id"], "tenant_id": manifest["tenant_id"],
              "prepared_manifest_sha256": digest(folder / "prepared/manifest.json"), "baseline_snapshot_sha256": baseline_sha,
              "started_at": datetime.now(UTC).isoformat(), "model_calls_by_test": 0}
    try:
        deadline = time.monotonic() + cfg["timeout_seconds"]
        while True:
            pg = await pg_snapshot(cfg, manifest["tenant_id"], alert["connector_id"])
            lake = lake_snapshot(cfg, manifest["tenant_id"], expected["query_expectations"]["S04_full_host"])
            present = [r for r in pg["rows"]["alerts"] if r["source_alert_id"] == alert["id"]]
            events = [r for r in lake["rows"] if str(r["event_id"]) == event["event_id"]]
            if mode == "preflight" or (events if mode == "context" else present) or time.monotonic() >= deadline:
                break
            await asyncio.sleep(cfg["s04_readback_poll_seconds"])
        save(out / (mode + "-pg.json"), pg)
        save(out / (mode + "-lake.json"), lake)
        result["snapshots"] = {kind: digest(out / (mode + "-" + kind + ".json")) for kind in ("pg", "lake")}
        check(len(pg["connector"]) == 1, "connector_missing")
        if mode == "preflight":
            check(not present and not any(r["id"] == expected["predicted_new_alert_id"] for r in pg["rows"]["alerts"]), "A04_already_present")
            check(not events, "E13_already_present")
            compare(baseline["rows"], pg["rows"])
            check({r["id"] for r in pg["rows"]["runs"]} == {r["id"] for r in baseline["rows"]["runs"]}, "unexpected_runs_before_send")
            check({r["id"] for r in pg["rows"]["cases"]} == {r["id"] for r in baseline["rows"]["cases"]}, "unexpected_cases_before_send")
            result.update(source="real_lake_and_postgres_readback", new_alert_absent=True, new_event_absent=True,
                          business_baseline_unchanged=True, actual_counts=pg["counts"], lake_rows=len(lake["rows"]))
        else:
            preflight = read(out / "preflight-readback.json")
            check(preflight["status"] == "passed", "preflight_not_passed")
            for kind in ("pg", "lake"):
                check(digest(out / ("preflight-" + kind + ".json")) == preflight["snapshots"][kind], "preflight_snapshot_changed")
            old_pg, old_lake = (read(out / ("preflight-" + kind + ".json")) for kind in ("pg", "lake"))
            new = compare(old_pg["rows"], pg["rows"], incident=expected["existing_incident_id"] if mode == "alerts" else None)
            old_events = {r["event_id"]: r for r in old_lake["rows"]}
            current_events = {r["event_id"]: r for r in normalized(lake["rows"])}
            check(all(current_events.get(k) == v for k, v in old_events.items()), "old_lake_records_changed")
            check(len(lake["rows"]) == len(old_lake["rows"]) + 1 and set(current_events) - set(old_events) == {event["event_id"]}, "only_one_E13_added")
            check(len(events) == 1, "E13_not_exactly_once")
            verify_event(events[0], event)
            logical = read(folder / "dataset-manifest.json")["logical_ids"]
            for tool, wanted in expected["query_expectations"]["S04_full_host"]["included"].items():
                check(set(lake["hits"][tool]) == {logical[k] for k in wanted}, "S04_expanded_query_" + tool)
            if mode == "context":
                check(not any(new.values()), "context_created_business_rows")
                result.update(source="real_lake_readback", event_ids=[event["event_id"]], business_baseline_unchanged=True,
                              delta_counts=dict.fromkeys(("alerts", "incidents", "tasks", "attempts", "runs", "model_calls"), 0))
            else:
                wanted = {"alerts": 1, "alert_materials": 1, "alert_source_refs": 1, "incident_alerts": 1,
                          "analysis_tasks": 1, "artifacts": 1, "alert_objects": len(new["alert_objects"])}
                check({k: len(v) for k, v in new.items()} == {k: wanted.get(k, 0) for k in TABLES}, "A04_only_expected_business_delta")
                check(len(present) == 1, "A04_source_mapping")
                canonical = present[0]
                aid = canonical["id"]
                check(aid == expected["predicted_new_alert_id"] and canonical["connector_id"] == alert["connector_id"], "A04_actual_canonical_contract")
                material, ref, member, task, original = (new[t][0] for t in
                    ("alert_materials", "alert_source_refs", "incident_alerts", "analysis_tasks", "artifacts"))
                check(canonical["latest_material_id"] == material["id"] and material["alert_id"] == aid and material["revision"] == 1, "A04_material_identity")
                check(material["raw_json"]["raw_event"] == alert["raw_event"] and material["ocsf_json"] == event["ocsf_event"]
                      and material["raw_text"] == event["ocsf_event"]["raw_data"], "A04_material_original_bytes")
                scope = material["source_scope"]
                check(scope["received_count"] == scope["retained_count"] == 1 and scope["complete"] and not scope["truncated"], "A04_source_scope_exactly_E13")
                check(ref["source_event_id"] == event["event_id"] and ref["material_id"] == material["id"]
                      and ref["relation_kind"] == "source_event" and ref["alert_id"] == aid, "A04_direct_source_E13")
                check(member["alert_id"] == aid and member["incident_id"] == expected["existing_incident_id"]
                      and member["membership_source"] == "fusion", "A04_merged_into_original_I")
                check(len(new["alert_objects"]) > 0 and all(o["alert_id"] == aid and o["material_id"] == material["id"] for o in new["alert_objects"]), "A04_objects_scoped")
                check((task["subject_id"], task["subject_type"], task["intent"], task["source"], task["state"])
                      == (aid, "alert", "initial", "ingress", "accepted") and task["started_at"] is None, "A04_initial_accepted_no_Run")
                check(original["alert_id"] == aid and original["kind"] == "source_snapshot" and original["run_id"] is None, "A04_original_saved")
                check(all(task[k] == v for k, v in cfg["initial_task_policy"].items()), "A04_current_task_retry_policy")
                iid = expected["existing_incident_id"]
                members = sorted(r["alert_id"] for r in pg["rows"]["incident_alerts"] if r["incident_id"] == iid)
                check(len(members) == 4 and aid in members, "I_now_has_four_members")
                mapping = {"status": "passed", "source": "real_native_ingress_readback", "batch_id": manifest["batch_id"],
                           "A04": {"alert_id": aid, "material_id": material["id"], "task_id": task["id"], "source_event_id": ref["source_event_id"],
                                   "source_ref_id": ref["id"], "artifact_id": original["id"], "incident_id": iid},
                           "incident_members": members, "baseline_cases": expected["baseline_cases"],
                           "postgres_snapshot_sha256": result["snapshots"]["pg"], "new_attempts": 0, "new_runs": 0}
                save(out / "identity-map.json", mapping)
                result.update(source="real_postgres_and_lake_ingress_readback", delta_counts={k: len(v) for k, v in new.items()},
                              old_case_rows_and_initial_runs_unchanged=True, identity_map="identity-map.json")
        result["status"] = "passed"
    except Exception as exc:  # noqa: BLE001 -- preserve bounded failure, do not expose DSNs
        result.update(status="failed", error_type=type(exc).__name__, sqlstate=getattr(exc, "sqlstate", None),
                      check=str(exc) if isinstance(exc, AssertionError) else None)
    result["ended_at"] = datetime.now(UTC).isoformat()
    save(receipt, result)
    print(json.dumps({k: v for k, v in result.items() if k not in {"actual_counts"}}, ensure_ascii=False))
    return result["status"] == "passed"


raise SystemExit(0 if asyncio.run(main(Path(sys.argv[1]), sys.argv[2])) else 1)
