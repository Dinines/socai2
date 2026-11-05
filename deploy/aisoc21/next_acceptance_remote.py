"""Fixed synthetic acceptance ON 21. Never prints credentials or reads old business rows."""
import argparse
import hashlib
import importlib.util
import ipaddress
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("next_service", HERE / "next_service_remote.py")
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)
BATCH = "r1"
EVIDENCE_ROOT = Path("/opt/sting-aisoc-socai2/evidence")
ROOT = EVIDENCE_ROOT / ("next-acceptance-" + BATCH)
IDENTITY = json.loads((service.PRIVATE / "identity.json").read_text())
assert IDENTITY["tenant_id"] == service.TENANT


def uid(label):
    return str(uuid5(NAMESPACE_URL, "socai2-next-acceptance-" + BATCH + ":" + label))


def save(name, value):
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = ROOT / (name + ".json")
    assert not path.exists(), "acceptance phase is immutable; inspect outcome before any new batch"
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")
    path.chmod(0o600)


def read(name):
    return json.loads((ROOT / (name + ".json")).read_text())


def http(label, method, path, body=None, *, key="api_key", expected=200):
    assert path.startswith("/api/v1/socai2/")
    request = {"method": method, "path": path, "body": body, "authentication": key or "none"}
    save(label + "-request", request)  # persist intent BEFORE dispatch; never silently retry
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + IDENTITY[key]
    req = urllib.request.Request("http://127.0.0.1:18020" + path,
        data=json.dumps(body).encode() if body is not None else None, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=150) as response:
            status, raw = response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read().decode()
    result = {"status": status, "body": json.loads(raw)}
    save(label + "-response", result)
    print(json.dumps({"call": label, "status": status}), flush=True)
    assert status == expected, f"unexpected HTTP status for {label}: {status}"
    return result["body"]


def fixture():
    now = datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=5)
    times = [now, now + timedelta(seconds=15)]
    host, username = "next-validation-host", "synthetic-operator"
    alerts, rows = [], []
    for index, when in enumerate(times):
        event_id = uid("source-event-" + str(index))
        if index == 0:
            ocsf = {"class_uid": 1007, "time": when.isoformat(), "device": {"hostname": host},
                "process": {"pid": 4242, "name": "powershell.exe", "cmd_line": "powershell.exe -File C:\\Lab\\inventory.ps1",
                    "parent_process": {"pid": 2100, "name": "cmd.exe"}}, "user": {"name": username},
                "activity": {"action": "process_start", "outcome": "success"}}
            title = "Synthetic PowerShell inventory process"
        else:
            ocsf = {"class_uid": 4001, "time": when.isoformat(), "src_endpoint": {"hostname": host, "ip": "192.0.2.20", "port": 50123},
                "dst_endpoint": {"ip": "198.51.100.20", "port": 443, "hostname": "inventory.example.invalid"},
                "network": {"protocol_name": "tcp"}, "activity": {"action": "network_connect", "outcome": "success"}}
            title = "Synthetic outbound inventory endpoint connection"
        raw = {"fixture": "socai2-next-acceptance-r1", "original_vendor": "SyntheticLab", "event_id": event_id,
            "ocsf_event": ocsf, "raw_data": json.dumps(ocsf, ensure_ascii=False)}
        alert = {"tenant_id": service.TENANT, "identity_version": "source-v1", "source_alert_id": uid("source-alert-" + str(index)),
            "source": "synthetic-next-validation", "connector_type": "synthetic", "title": title,
            "description": "Synthetic validation only. Shared host/time do not prove the process made the connection. Authorization is not supplied.",
            "event_time": when.isoformat(), "severity": "medium", "hostname": host, "username": username if index == 0 else None,
            "rule_id": "synthetic-rule-" + str(index), "rule_name": title, "source_event_ids": [event_id],
            "external_id": "synthetic-vendor-" + str(index), "ocsf_class_uid": ocsf["class_uid"],
            "mitre_tactics": ["Execution"] if index == 0 else [], "mitre_techniques": ["T1059.001"] if index == 0 else [],
            "raw_event": raw}
        alerts.append(alert)
        rows.append({"event_id": event_id, "tenant_id": service.TENANT,
            "event_time": when.strftime("%Y-%m-%d %H:%M:%S.000"), "class_uid": ocsf["class_uid"],
            "src_hostname": host, "source_ip": "::ffff:192.0.2.20", "dest_ip": "::ffff:198.51.100.20" if index else "::",
            "user_name": username if index == 0 else "", "process_name": "powershell.exe" if index == 0 else "",
            "src_port": 50123 if index else 0, "dst_port": 443 if index else 0,
            "dst_hostname": "inventory.example.invalid" if index else "", "protocol": "tcp" if index else "",
            "action": "process_start" if index == 0 else "network_connect", "outcome": "success",
            "connector_type": "synthetic", "raw_payload": json.dumps(raw), "ocsf_json": json.dumps(ocsf)})
    return {"database": service.DATABASE, "tenant_id": service.TENANT, "incident_id": uid("incident"),
        "event_time": now.isoformat(), "window_start": (now - timedelta(minutes=1)).isoformat(),
        "window_end": (now + timedelta(minutes=1)).isoformat(), "alerts": alerts, "lake_rows": rows}


def seed():
    assert BATCH == "r1", "only the original batch may create source fixtures"
    data = fixture()
    save("fixture", data)
    package = {p.relative_to(HERE / "fusion").as_posix(): p.read_text() for p in (HERE / "fusion/app").rglob("*.py")}
    output = service.command(["docker", "exec", "-i", service.NEW, "python", "-c",
        (HERE / "next_acceptance_seed.py").read_text()], body=json.dumps({**data, "files": package}).encode(), timeout=60)
    records = [json.loads(line) for line in output.splitlines() if line.startswith("{\"seeded\"")]
    assert len(records) == 1
    save("fusion", records[0])
    # Keep SQL and JSON payload separate. This loader has no business consumer
    # claim; a partial failure must be inspected by exact fixture event IDs.
    env = service.environment(service.CH)
    service.command(["docker", "exec", "-i", service.CH, "clickhouse-client",
        "--user", env.get("CLICKHOUSE_USER", "default"), "--password", env.get("CLICKHOUSE_PASSWORD", ""),
        "--query", "INSERT INTO socai2_next_validation.raw_events FORMAT JSONEachRow"],
        body=("\n".join(json.dumps(r) for r in data["lake_rows"]) + "\n").encode(), timeout=60)
    count = service.lake("SELECT count() FROM socai2_next_validation.raw_events WHERE tenant_id='" + service.TENANT + "'")
    assert count == "2", count
    save("lake", {"rows": 2, "database": service.LAKE, "fixture_loader_not_fusion_lake_consumer": True})
    print(json.dumps({"phase": "seed", "alerts": len(records[0]["seeded"]), "lake_rows": 2}), flush=True)


def alert_ids():
    if BATCH in {"r2", "r3", "r4", "r5", "r6", "r7"}:
        return read("reuse")["alert_ids"]
    return [row["alert_id"] for row in read("fusion")["seeded"]]


def reuse():
    assert BATCH == "r7", "only the current r7 batch may prepare source reuse"
    source = EVIDENCE_ROOT / "next-acceptance-r1"
    original = {name: (source / (name + ".json")).read_bytes() for name in ("fixture", "fusion")}
    data, fused = (json.loads(original[name]) for name in ("fixture", "fusion"))
    assert data["database"] == service.DATABASE and data["tenant_id"] == service.TENANT
    assert len(data["alerts"]) == len(data["lake_rows"]) == len(fused["seeded"]) == 2
    save("reuse-request", {"source_batch": "r1", "target_batch": BATCH, "read_only": True,
        "source_file_sha256": {name: hashlib.sha256(body).hexdigest() for name, body in original.items()}})
    verified = []
    for expected, entry in zip(data["alerts"], fused["seeded"], strict=True):
        aid = str(UUID(entry["alert_id"]))
        raw = service.pg(service.DATABASE, "SELECT jsonb_build_object('material_id',m.id,'raw_json',m.raw_json,'incident_id',i.incident_id) "
            "FROM socai2.alerts a JOIN socai2.alert_materials m ON m.id=a.latest_material_id AND m.tenant_id=a.tenant_id "
            "JOIN socai2.incident_alerts i ON i.alert_id=a.id AND i.tenant_id=a.tenant_id "
            "WHERE a.tenant_id='" + service.TENANT + "' AND a.id='" + aid + "'")
        assert raw, "reused alert/material missing"
        row = json.loads(raw)
        assert row["incident_id"] == data["incident_id"], "reused incident membership changed"
        for key, value in expected.items():
            actual = row["raw_json"][key]
            if key == "event_time":
                actual, value = datetime.fromisoformat(actual), datetime.fromisoformat(value)
            assert actual == value, "received alert material differs: " + key
        verified.append({"alert_id": aid, "material_id": row["material_id"], "checked_received_fields": len(expected)})
    lake_verified = []
    for expected in data["lake_rows"]:
        event_id = str(UUID(expected["event_id"]))
        raw = service.lake("SELECT " + ",".join(expected) + " FROM socai2_next_validation.raw_events WHERE tenant_id='" +
            service.TENANT + "' AND event_id='" + event_id + "' FORMAT JSONEachRow")
        assert len(raw.splitlines()) == 1, "reused lake event missing or duplicated"
        actual = json.loads(raw)
        for key, value in expected.items():
            saved = actual[key]
            if key in {"source_ip", "dest_ip"}:
                saved, value = ipaddress.ip_address(saved), ipaddress.ip_address(value)
            assert saved == value, "received lake field differs: " + key
        lake_verified.append({"event_id": event_id, "checked_received_fields": len(expected)})
    save("fixture", data)  # original source fixture, not a new ingestion claim
    save("reuse", {"source_batch": "r1", "target_batch": BATCH, "mode": "verified_existing_sources",
        "source_file_sha256": {name: hashlib.sha256(body).hexdigest() for name, body in original.items()},
        "alert_ids": [r["alert_id"] for r in verified], "alerts": verified, "lake_events": lake_verified,
        "incident_id": data["incident_id"], "upstream_writes": 0, "r1_case_run_unchanged": True,
        "prior_requests_and_model_responses_copied": False})
    print(json.dumps({"phase": "reuse", "batch": BATCH, "alerts": 2, "lake_rows": 2, "upstream_writes": 0}), flush=True)


def stages():
    for index, aid in enumerate(alert_ids()):
        http(f"A{index}", "POST", f"/api/v1/socai2/alerts/{aid}/analyze", {"operation_key": uid(f"A{index}")})
    http("I", "POST", f"/api/v1/socai2/incidents/{read('fixture')['incident_id']}/diagnose", {"operation_key": uid("I")})


def start_round(label, cid, run, revision, previous=None):
    data = read("fixture")
    result = http(label, "POST", f"/api/v1/socai2/cases/{cid}/runs/{run}/start",
        {"operation_key": uid(label), "expected_scope_revision": revision,
         "window_start": data["window_start"], "window_end": data["window_end"], "comparison_result_id": previous})
    for index, rid in enumerate(result["result_ids"]):
        http(f"{label}-result-{index}", "GET", f"/api/v1/socai2/cases/{cid}/results/{rid}")


def case_first():
    created = http("case-create", "POST", "/api/v1/socai2/cases", {"operation_key": uid("case"),
        "title": "Synthetic two-record inventory review " + BATCH, "incident_ids": [read("fixture")["incident_id"]], "alert_ids": []})
    start_round("C1", created["case_id"], created["pending_run_id"], created["scope_revision"])


def accepted_first_result(case_id):
    response = read("C1-response")
    assert response["status"] == 200, "first C request did not complete successfully"
    body = response["body"]
    run, result_ids = body["run"], body["result_ids"]
    assert run["state"] == "completed" and run["case_id"] == case_id, "first C must have a completed matching Run"
    assert len(result_ids) == 1, "first C must publish exactly one result"
    detail = read("C1-result-0-response")
    assert detail["status"] == 200, "first C result is not readable"
    result = detail["body"]["result"]
    assert result["id"] == result_ids[0] and result["case_id"] == case_id and result["source_run_id"] == run["id"], "first C result identity mismatch"
    assert detail["body"]["run"]["id"] == run["id"] and detail["body"]["run"]["state"] == "completed", "first C result Run mismatch"
    assert result["kind"] == "baseline" and result["conclusion_origin"] == "model", "first C requires a model baseline result"
    assert result["validation_state"] == "accepted", "first C requires accepted validation, not a system-only handoff"
    assert isinstance(result["conclusion"], str) and result["conclusion"].strip(), "first C requires a nonempty conclusion"
    return result["id"]


def human_and_second():
    created = read("case-create-response")["body"]
    cid, revision = created["case_id"], created["scope_revision"]
    data = read("fixture")
    previous = accepted_first_result(cid)
    scope = {"kind": "selected_alerts", "alert_ids": [alert_ids()[0]], "object_keys": [],
        "window_start": data["window_start"], "window_end": data["window_end"],
        "limitations": ["Human statement confirms only the process task; network attribution remains unknown."]}
    http("H", "POST", f"/api/v1/socai2/cases/{cid}/tasks", {"operation_key": uid("H"), "expected_scope_revision": revision,
        "title": "Confirm inventory task authorization", "state": "completed", "assignee_id": service.USER,
        "result_text": "Synthetic operator statement: I authorized the inventory.ps1 task on next-validation-host in this window. I have not confirmed which process made the network connection.",
        "result_scope": scope})
    pending = http("prepare", "POST", f"/api/v1/socai2/cases/{cid}/baseline/prepare",
        {"operation_key": uid("prepare"), "expected_scope_revision": revision})
    start_round("C2", cid, pending["pending_run_id"], revision, previous)
    http("case-final", "GET", f"/api/v1/socai2/cases/{cid}")
    http("history-final", "GET", f"/api/v1/socai2/cases/{cid}/history")


def auth():
    aid = alert_ids()[0]
    http("auth-none", "GET", f"/api/v1/socai2/alerts/{aid}/analysis", key=None, expected=401)
    http("auth-denied", "POST", f"/api/v1/socai2/alerts/{aid}/analyze", {"operation_key": uid("denied")}, key="read_api_key", expected=403)
    http("auth-read", "GET", f"/api/v1/socai2/alerts/{aid}/analysis", key="read_api_key")


def export_clause(table):
    if BATCH == "r1":
        return "TRUE"
    cid = str(uuid5(UUID(service.TENANT), "socai2.case.create:" + uid("case")))
    ids = ",".join("'" + str(UUID(a)) + "'" for a in alert_ids())
    stage_ids = ",".join("'" + str(uuid5(UUID(service.TENANT), "socai2.stage:" + uid(label))) + "'" for label in ("A0", "A1", "I"))
    runs = "SELECT id FROM socai2.runs WHERE tenant_id='" + service.TENANT + "' AND (case_id='" + cid + "' OR id IN (" + stage_ids + "))"
    if table == "alerts":
        return "t.id IN (" + ids + ")"
    if table in {"alert_materials", "alert_source_refs", "alert_objects"}:
        return "t.alert_id IN (" + ids + ")"
    if table in {"incidents", "incident_alerts"}:
        field = "id" if table == "incidents" else "incident_id"
        return "t." + field + "='" + str(UUID(read("fixture")["incident_id"])) + "'"
    if table in {"alert_assessments", "incident_diagnoses"}:
        return "t.source_run_id IN (" + runs + ")"
    if table == "runs":
        return "t.id IN (" + runs + ")"
    if table in {"run_members", "run_steps"}:
        return "t.run_id IN (" + runs + ")"
    if table == "artifacts":
        return "(t.run_id IN (" + runs + ") OR (t.run_id IS NULL AND t.alert_id IN (" + ids + ")))"
    if table == "activities":
        return "t.subject_case_id='" + cid + "'"
    if table == "activity_targets":
        return "t.activity_id IN (SELECT id FROM socai2.activities WHERE tenant_id='" + service.TENANT + "' AND subject_case_id='" + cid + "')"
    return "t." + ("id" if table == "cases" else "case_id") + "='" + cid + "'"


def export():
    # Only the dedicated synthetic tenant in the NEW DB; no users/keys/settings.
    data = {}
    for table in ["alerts", "alert_materials", "alert_source_refs", "alert_objects", "alert_assessments",
            "incidents", "incident_alerts", "incident_diagnoses", "cases", "case_alerts", "case_incidents",
            "runs", "run_members", "run_steps", "artifacts", "results", "result_members", "tasks", "task_revisions",
            "case_assessments", "case_assessment_sources", "case_assessment_members", "activities", "activity_targets"]:
        exists = service.pg(service.DATABASE, "SELECT count(*) FROM information_schema.tables WHERE table_schema='socai2' AND table_name=" + service.literal(table))
        assert exists == "1", "required acceptance table missing: " + table
        rows = service.pg(service.DATABASE, "SELECT COALESCE(jsonb_agg(to_jsonb(t)),'[]'::jsonb) FROM socai2." + table +
            " t WHERE tenant_id='" + service.TENANT + "' AND (" + export_clause(table) + ")")
        data[table] = json.loads(rows)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    save("database-" + stamp, data)
    unchanged = service.old_snapshot() == json.loads((service.PRIVATE / "original-containers.json").read_text())
    assert unchanged
    files = {p.name: json.loads(p.read_text()) for p in sorted(ROOT.glob("*.json"))}
    print(json.dumps({"export": files, "original_containers_unchanged": unchanged, "synthetic_only": True,
        "database": service.DATABASE, "batch": BATCH,
        "snapshot_scope": "dedicated_synthetic_tenant" if BATCH == "r1" else BATCH + "_runs_case_and_explicit_reused_sources"}, ensure_ascii=False), flush=True)


def phase_allowed(batch, phase):
    # Prior batches are closed; retain read-only export of their original evidence.
    # r7 verifies the m1 contract fixes; closed batches can only export evidence.
    return (batch in {"r1", "r2", "r3", "r4", "r5", "r6"} and phase == "export") or (batch == "r7" and phase in {"reuse", "auth", "stages", "first", "second", "export"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["seed", "reuse", "auth", "stages", "first", "second", "export"])
    parser.add_argument("--batch", choices=["r1", "r2", "r3", "r4", "r5", "r6", "r7"], default="r1")
    args = parser.parse_args()
    phase, BATCH = args.phase, args.batch
    ROOT = EVIDENCE_ROOT / ("next-acceptance-" + BATCH)
    try:
        assert phase_allowed(BATCH, phase), "closed_batch_or_source_ingestion_not_allowed"
        {"seed": seed, "reuse": reuse, "auth": auth, "stages": stages, "first": case_first, "second": human_and_second, "export": export}[phase]()
    except Exception as exc:  # noqa: BLE001 -- sanitized boundary, preserve failed phase without credentials
        # Known local assertions may be shown; external exception text may contain credentials.
        print(json.dumps({"failed_phase": phase, "error_type": type(exc).__name__,
            "detail": str(exc) if isinstance(exc, AssertionError) else "external operation failed; inspect sanitized diagnostics"}), flush=True)
        sys.exit(1)
