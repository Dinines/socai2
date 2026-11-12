"""Batch-scoped current-table readback and separate, unmodified API observations."""
import json
from datetime import UTC, datetime
from uuid import UUID, uuid5

from config import DATABASE, TENANT
from flow_fixture import encoded, sha, uid

TABLES = ("alerts", "alert_materials", "alert_source_refs", "alert_objects", "alert_assessments",
    "incidents", "incident_alerts", "incident_diagnoses", "cases", "case_alerts", "case_incidents",
    "case_assessments", "case_assessment_sources", "case_assessment_members", "runs", "run_members", "run_steps",
    "artifacts", "results", "result_members", "tasks", "task_revisions", "conversations", "messages",
    "activities", "activity_targets", "comments", "response_links")


def query_for(table):
    assert table in TABLES
    runs = "SELECT r.id FROM socai2.runs r WHERE r.tenant_id=s.tenant AND (r.case_id=s.cid OR r.id=ANY(s.stages))"
    subject = "subject_case_id=s.cid OR subject_alert_id=ANY(s.aids) OR subject_incident_id=s.incident"
    if table == "alerts":
        clause = "t.id=ANY(s.aids)"
    elif table in {"alert_materials", "alert_source_refs", "alert_objects"}:
        clause = "t.alert_id=ANY(s.aids)"
    elif table in {"incidents", "incident_alerts"}:
        clause = "t." + ("id" if table == "incidents" else "incident_id") + "=s.incident"
    elif table in {"alert_assessments", "incident_diagnoses"}:
        clause = "t.source_run_id IN (" + runs + ")"
    elif table == "runs":
        clause = "t.id IN (" + runs + ")"
    elif table in {"run_members", "run_steps"}:
        clause = "t.run_id IN (" + runs + ")"
    elif table == "artifacts":
        clause = "t.run_id IN (" + runs + ") OR t.case_id=s.cid OR (t.run_id IS NULL AND t.alert_id=ANY(s.aids))"
    elif table == "activities":
        clause = subject
    elif table == "activity_targets":
        clause = "t.activity_id IN (SELECT id FROM socai2.activities WHERE tenant_id=s.tenant AND (" + subject + "))"
    elif table in {"comments", "response_links"}:
        clause = "t.case_id=s.cid OR t.alert_id=ANY(s.aids) OR t.incident_id=s.incident"
    else:
        clause = "t." + ("id" if table == "cases" else "case_id") + "=s.cid"
    return ("WITH scope AS (SELECT $1::uuid tenant,$2::uuid[] aids,$3::uuid incident,$4::uuid cid,$5::uuid[] stages) "
        "SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY t.id),'[]'::jsonb) FROM socai2." + table
        + " t CROSS JOIN scope s WHERE t.tenant_id=s.tenant AND (" + clause + ")")


async def export(driver):
    batch = driver.plan["batch_id"]
    cid = uuid5(UUID(TENANT), "socai2.case.create:" + uid(batch, "case"))
    subject = driver.read("ingest-subjects") if (driver.root / "ingest-subjects.json").exists() else {}
    incident = UUID(subject["incident_id"]) if subject.get("incident_id") else None
    args = (UUID(TENANT), list(map(UUID, driver.plan["canonical_alert_ids"])), incident, cid,
        [uuid5(UUID(TENANT), "socai2.stage:" + uid(batch, k)) for k in ("A0", "A1", "I")])
    connection = await driver.connect()
    data, freshness = {}, []
    try:
        async with connection.transaction(isolation="repeatable_read", readonly=True):
            await connection.execute("SELECT set_config('app.current_tenant_id',$1,true)", TENANT)
            for table in TABLES:
                data[table] = json.loads(await connection.fetchval(query_for(table), *args))
            for run in data["runs"]:
                if run["kind"] == "baseline":
                    value = await connection.fetchval("SELECT socai2.baseline_input_freshness($1::uuid,$2::uuid)",
                        UUID(TENANT), UUID(run["id"]))
                    freshness.append({"run_id": run["id"], "value": json.loads(value)})
    finally:
        await connection.close()
    now = datetime.now(UTC)
    folder = driver.root / "exports" / now.strftime("%Y%m%dT%H%M%S%fZ")
    folder.mkdir(parents=True, exist_ok=False)
    responses = []
    if data["cases"]:
        paths = [f"/cases/{cid}", f"/cases/{cid}/history", f"/cases/{cid}/tasks"]
        paths += [f"/cases/{cid}/runs/{r['id']}" for r in data["runs"] if r["kind"] == "baseline"]
        paths += [f"/cases/{cid}/results/{r['id']}" for r in data["results"]]
        for path in paths:
            responses.append(await driver.http(None, "GET", "/api/v1/socai2" + path, record=False, require_success=False))
    for aid in driver.plan["canonical_alert_ids"]:
        responses.append(await driver.http(None, "GET", f"/api/v1/socai2/alerts/{aid}/analysis", record=False, require_success=False))
    classification = classify(data)
    import sys

    from config import ROOT
    sys.path.insert(0, str(ROOT / "services/api"))
    from app.socai2.case_data import export_page_data
    payloads = {"database.json": data, "case-page-data.json": await export_page_data(data), "api-responses.json": responses, "input-freshness.json": freshness,
        "failures.json": classification}
    sources = []
    roles = {"database.json": "database", "case-page-data.json": "case_page_data", "api-responses.json": "api_responses", "input-freshness.json": "run_input_freshness", "failures.json": "failure_classification"}
    for name, payload in payloads.items():
        body = encoded(payload) + b"\n"
        (folder / name).write_bytes(body)
        sources.append({"role": roles[name], "file": name, "sha256": sha(body)})
    manifest = {"schema_version": "socai2.page-export.v1", "batch_id": batch, "source_environment": "local-standalone",
        "exported_at": now.isoformat(), "source_sha256": sources[0]["sha256"], "input_kind": "synthetic",
        "sources": sources, "database": DATABASE, "tenant_id": TENANT, "case_id": str(cid),
        "table_counts": {k: len(v) for k, v in data.items()}, "oracle_included": False,
        "database_snapshot": "single_readonly_repeatable_read", "api_observations": "separate_later_GETs"}
    (folder / "manifest.json").write_bytes(encoded(manifest) + b"\n")
    return {"export_directory": str(folder), "table_counts": manifest["table_counts"],
        "failure_counts": classification["failure_counts"], "unknown_counts": classification["unknown_counts"],
        "skip_counts": classification["skip_counts"]}


def category_for(state, code):
    code = code or ""
    if state == "unknown":
        return "uncertain_execution"
    if state == "skipped":
        if code == "no_supported_frozen_objects":
            return "skip_not_applicable"
        if any(s in code for s in ("budget", "reserved", "deadline", "limits_not_defined", "usage_unknown")):
            return "skip_policy"
        if any(s in code for s in ("source", "connected", "window", "not_configured")):
            return "skip_source_availability"
        if any(s in code for s in ("input", "not_ready", "no_accepted")):
            return "skip_missing_prerequisite"
        return "skip_unclassified"
    if state != "failed":
        return "nonfailure_diagnostic"
    return ("model_schema" if "schema" in code
        else "capacity_or_time" if any(s in code for s in ("budget", "reserved", "deadline", "exceeds"))
        else "missing_required_input" if any(s in code for s in ("input", "not_ready", "no_accepted"))
        else "usage_unknown" if "usage" in code
        else "source_availability" if any(s in code for s in ("source", "connected", "window"))
        else "contract_or_execution")


def classify(data):
    rows, counts, state_counts = [], {}, {}
    by_state = {"failed": {}, "unknown": {}, "skipped": {}}
    for step in data["run_steps"]:
        code = (step.get("error") or {}).get("code")
        if not code and step["state"] not in {"failed", "unknown", "skipped"}:
            continue
        category = category_for(step["state"], code)
        rows.append({"run_id": step["run_id"], "step_id": step["id"], "stage": step["stage_code"],
            "state": step["state"], "code": code, "category": category})
        counts[category] = counts.get(category, 0) + 1
        state_counts[step["state"]] = state_counts.get(step["state"], 0) + 1
        if step["state"] in by_state:
            target = by_state[step["state"]]
            target[category] = target.get(category, 0) + 1
    return {"schema_version": "socai2.step-outcome-classification.v2", "rows": rows, "counts": counts,
        "state_counts": state_counts, "failure_counts": by_state["failed"], "unknown_counts": by_state["unknown"],
        "skip_counts": by_state["skipped"], "meaning": "execution_outcomes_not_model_accuracy",
        "limitations": ["counts are step counts, not distinct Run failures", "raw state and error code retained",
            "skips are not failed executions or proof of successful investigation",
            "unrecognized skip reasons remain skip_unclassified; no success inferred"]}
