"""New fixed repair cards ON 21; credentials remain inside this server process.

Reuses the verified service helper, original HTTP evidence/readback helpers,
and Kafka worker. No deployment or migration operation is exposed here.
"""
import argparse
import hashlib
import importlib.util
import ipaddress
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID, uuid5

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((HERE / (name + ".json")).read_text())


def save(name, value):
    with (HERE / (name + ".json")).open("x") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    (HERE / (name + ".json")).chmod(0o600)


def bootstrap():
    assert HERE.parent == Path("/opt/sting-aisoc-socai2/evidence")
    for name, digest in read("manifest").items():
        assert Path(name).name == name and sha(HERE / name) == digest, "packet hash mismatch"
    plan = read("plan")
    assert plan["batch"] == "repair-k6" and plan["max_model_calls"] == 50
    release = Path("/opt/sting-aisoc-socai2/releases") / plan["release"]
    assert release.parent == Path("/opt/sting-aisoc-socai2/releases") and release.name.startswith("next-")
    assert sha(release / "manifest.json") == plan["candidate_manifest_sha256"]
    service = load("repair_service", release / "next_service_remote.py")
    identity = json.loads((service.PRIVATE / "identity.json").read_text())
    assert plan["tenant_id"] == identity["tenant_id"] == service.TENANT
    assert service.DATABASE == "socai2_next_20261104" and service.LAKE == "socai2_next_validation"
    return plan, release, service


def core_gate(plan):
    approval = read("core-review")
    assert approval.get("approved") is True and approval.get("reviewer") == "root"
    assert approval.get("candidate_manifest_sha256") == plan["candidate_manifest_sha256"]
    assert approval.get("plan_sha256") == sha(HERE / "plan.json")
    assert approval.get("max_model_calls") == 50


def semantic_gate(approval, result_id, plan_hash, result_hash):
    assert approval.get("approved") is True and approval.get("reviewer") == "root"
    assert approval.get("result_id") == result_id and approval.get("plan_sha256") == plan_hash
    assert approval.get("first_result_sha256") == result_hash


def verify_runtime(plan, release, service, backend):
    manifest = service.candidate()
    runtime = service.inspect(service.NEW)
    assert runtime["Config"]["Image"] == manifest["image"] == plan["image"], "candidate image not running"
    expected = {name: value for name, value in plan["candidate_files"].items() if name.startswith("app/")}
    check = """import hashlib,json,pathlib,sys
expected=json.load(sys.stdin); root=pathlib.Path('/app')
actual={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
for p in (root/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
assert actual==expected
print(len(actual))"""
    verified = int(service.command(["docker", "exec", "-i", service.NEW, "python", "-c", check],
        body=json.dumps(expected).encode()))
    assert service.pg(service.DATABASE, "SELECT to_regprocedure('socai2.baseline_input_freshness(uuid,uuid)') IS NOT NULL;") == "t"
    env = service.environment(service.NEW)
    expected_model = "deepseek-flash" if backend == "deepseek" else "aisoc-investigation"
    protocol = "deepseek_responses" if backend == "deepseek" else "chat_completions"
    profile = "standard" if backend == "deepseek" else "vllm_grammar_v1"
    assert (env.get("OPENAI_MODEL"), env.get("SOCAI2_MODEL_PROTOCOL"), env.get("SOCAI2_MODEL_SCHEMA_PROFILE")) == (expected_model, protocol, profile)
    assert env["SOCAI2_SERVICE_DATABASE_NAME"] == service.DATABASE
    assert env["SOCAI2_LAKE_DATABASE"] == service.LAKE
    return {"model": expected_model, "protocol": protocol, "schema_profile": profile,
        "image_id": runtime["Image"], "verified_application_files": verified, "migration_125_function_present": True}


def event_filter(service, cases):
    ids = [str(UUID(e["event_id"])) for c in cases for e in c["events"]]
    assert len(ids) == len(set(ids)) == 18
    return "tenant_id=" + service.literal(service.TENANT) + " AND event_id IN (" + ",".join(service.literal(i) for i in ids) + ")"


def lake_preflight(plan, service):
    where = event_filter(service, plan["cases"])
    schema = service.lake("DESCRIBE TABLE socai2_next_validation.raw_events FORMAT JSONEachRow")
    columns = [json.loads(line) for line in schema.splitlines()]
    assert {"event_id", "tenant_id", "raw_payload", "ocsf_json", "action", "session_id"} <= {r["name"] for r in columns}
    counts = {db: int(service.lake("SELECT count() FROM " + db + ".raw_events WHERE " + where))
              for db in ("socai2_next_validation", "aisoc")}
    assert counts == {"socai2_next_validation": 0, "aisoc": 0}, "new event IDs already exist; no dispatch"
    return {"columns": columns, "preexisting_counts": counts, "connection": "server_only_management",
            "grants_changed": False, "database": "socai2_next_validation"}


def lake_readback(plan, service, ingestion):
    where = event_filter(service, plan["cases"])
    output = service.lake("SELECT * FROM socai2_next_validation.raw_events WHERE " + where + " ORDER BY event_id FORMAT JSONEachRow")
    rows = [json.loads(line) for line in output.splitlines()]
    expected = {r["event_id"]: r for r in ingestion["lake_rows_projection"]}
    assert len(rows) == len(expected) == 18 and {r["event_id"] for r in rows} == set(expected)
    checks = []
    for row in rows:
        source = expected[row["event_id"]]
        for field, value in source.items():
            actual = row[field]
            if field == "event_time":
                actual, value = datetime.fromisoformat(actual), datetime.fromisoformat(value)
            elif field in {"source_ip", "dest_ip"}:
                actual, value = ipaddress.ip_address(actual), ipaddress.ip_address(value)
            assert actual == value, "lake field mismatch: " + field
        checks.append({"event_id": row["event_id"], "compared_fields": len(source)})
    old_count = int(service.lake("SELECT count() FROM aisoc.raw_events WHERE " + where))
    assert old_count == 0, "fixed event IDs unexpectedly entered old lake"
    expected_cases = {e["case_key"]: e for e in read("expected")["cases"]}
    tool_scopes = []
    for case in plan["cases"]:
        for tool, class_uid in [("process_activity", 1007), ("network_connections", 4001), ("authentication_activity", 3002)]:
            selected = [r["event_id"] for r in rows if r["src_hostname"] == case["host"] and r["class_uid"] == class_uid
                and datetime.fromisoformat(case["window_start"]) <= datetime.fromisoformat(r["event_time"]).replace(tzinfo=UTC)
                < datetime.fromisoformat(case["window_end"])]
            assert set(selected) == set(expected_cases[case["key"]]["tool_expected_event_ids"][tool])
            tool_scopes.append({"card": case["key"], "tool": tool, "expected_event_ids": sorted(selected)})
    return {"passed": True, "rows": rows, "field_checks": checks, "old_lake_count": old_count,
        "expected_tool_scopes": tool_scopes, "scope_check_only_not_actual_model_tool_invocation": True}


def ingest(plan, release, service):
    core_gate(plan)
    verify_runtime(plan, release, service, "deepseek")
    save("ingest-intent", {"model_calls": 0, "alerts": 12, "lake_events": 18,
        "topic_prefix": plan["topic_prefix"], "group": plan["group"]})
    save("lake-preflight", lake_preflight(plan, service))
    save("protected-private", service.protected_model_config())
    original, independent = service.environment("socai2-fusion-1"), service.environment(service.NEW)
    management = service.environment(service.CH)
    env = {key: value for key, value in original.items() if key.startswith("KAFKA_")}
    prefix, redis = plan["topic_prefix"], urlsplit(independent["REDIS_URL"])
    env.update({"KAFKA_TOPIC_ALERTS_RAW": prefix + ".alerts.raw", "KAFKA_TOPIC_RAW_EVENTS": prefix + ".raw_events",
        "KAFKA_TOPIC_ALERTS_FUSED": prefix + ".alerts.fused", "KAFKA_CONSUMER_GROUP": plan["group"],
        "KAFKA_SSL_CAFILE": "/run/certs/ca.crt", "DATABASE_URL": independent["DATABASE_URL"],
        "REDIS_URL": urlunsplit(redis._replace(path="/13")), "ENVIRONMENT": "production",
        "AISOC_ALERT_STORE_SCHEMA": "socai2", "AISOC_EVENT_PROMOTION_ENABLED": "false",
        "AISOC_UEBA_FUSION_ENABLED": "false", "AISOC_DETECTION_ENGINE_ENABLED": "false",
        "AISOC_WINDOWED_DETECTION_ENABLED": "false", "CLICKHOUSE_DATABASE": "socai2_next_validation",
        "CLICKHOUSE_HOST": original["CLICKHOUSE_HOST"], "CLICKHOUSE_PORT": original["CLICKHOUSE_PORT"],
        "CLICKHOUSE_USER": management.get("CLICKHOUSE_USER", "default"),
        "CLICKHOUSE_PASSWORD": management.get("CLICKHOUSE_PASSWORD", "")})
    assert urlsplit(env["DATABASE_URL"]).path == "/" + service.DATABASE
    files = {p.relative_to(release / "fusion").as_posix(): p.read_text() for p in (release / "fusion/app").rglob("*.py")}
    packet = {"environment": env, "files": files, "cases": plan["cases"], "topic_prefix": prefix,
        "expected_fused": 13, "expected_lake": 18, "replay_alert": True}
    output = service.command(["docker", "exec", "-i", service.NEW, "python", "-c",
        (HERE / "repair_k6_child_20261105.py").read_text()], body=json.dumps(packet).encode(), timeout=240)
    records = [json.loads(line.removeprefix("K1_RESULT=")) for line in output.splitlines() if line.startswith("K1_RESULT=")]
    assert len(records) == 1
    save("ingest-result", records[0])
    assert records[0]["passed"], "Kafka ingestion failed; do not start models"
    fused = {r["value"]["alert"]["source_alert_id"]: r["value"] for r in records[0]["fused"]}
    subjects = []
    for case in plan["cases"]:
        members = [fused[a["source_alert_id"]] for a in case["alerts"]]
        ids, incidents = {r["alert_row_id"] for r in members}, {r["incident_id"] for r in members}
        assert len(ids) == 2 and len(incidents) == 1, "card did not produce exactly two alerts and one incident"
        incident = next(iter(incidents))
        actual = json.loads(service.pg(service.DATABASE, "SELECT coalesce(json_agg(alert_id),'[]') FROM socai2.incident_alerts WHERE tenant_id="
            + service.literal(service.TENANT) + " AND incident_id=" + service.literal(incident)))
        assert set(actual) == ids, "incident contains unexpected members"
        subjects.append({"card": case["key"], "backend": case["backend"], "alert_ids": sorted(ids), "incident_id": incident})
    assert len({s["incident_id"] for s in subjects}) == 6
    save("lake-readback", lake_readback(plan, service, records[0]))
    save("ingest-subjects", subjects)
    assert service.protected_model_config() == read("protected-private"), "protected configuration changed"
    print(json.dumps({"ingested": True, "model_calls": 0, "fused_messages": 13,
        "canonical_alerts": 12, "unique_incidents": 6, "lake_events": 18, "lake_fields_verified": True}))


def card(plan, release, service, key):
    scenario = next(c for c in plan["cases"] if c["key"] == key)
    assert read("ingest-result")["passed"] and read("lake-readback")["passed"]
    subjects = read("ingest-subjects")
    assert len({s["incident_id"] for s in subjects}) == 6
    subject = next(s for s in subjects if s["card"] == key)
    fused = {r["value"]["alert"]["source_alert_id"]: r["value"] for r in read("ingest-result")["fused"]}
    ids = [fused[a["source_alert_id"]]["alert_row_id"] for a in scenario["alerts"]]
    assert set(ids) == set(subject["alert_ids"])
    helper = load("repair_http_" + key, release / "next_acceptance_remote.py")
    helper.service, helper.BATCH, helper.ROOT = service, plan["batch"] + "-" + key, HERE / key
    helper.alert_ids = lambda: ids
    return scenario, helper, ids, subject["incident_id"]


def first(plan, release, service, key):
    core_gate(plan)
    scenario, helper, _, incident = card(plan, release, service, key)
    runtime = verify_runtime(plan, release, service, scenario["backend"])
    helper.save("first-intent", {**runtime, "max_model_calls": 7, "max_runs": 4, "retries": 0})
    helper.save("fixture", {"incident_id": incident, "window_start": scenario["window_start"],
        "window_end": scenario["window_end"]})
    helper.stages()
    created = helper.http("case-create", "POST", "/api/v1/socai2/cases", {"operation_key": helper.uid("case"),
        "title": "Record review " + plan["batch"] + " " + key, "incident_ids": [incident], "alert_ids": []})
    helper.start_round("C1", created["case_id"], created["pending_run_id"], created["scope_revision"])
    helper.http("case-first", "GET", f"/api/v1/socai2/cases/{created['case_id']}")
    print(json.dumps({"card": key, "first_phase_finished": True, "next": "export and root semantic review"}))


def second(plan, release, service, key):
    core_gate(plan)
    scenario, helper, aids, _ = card(plan, release, service, key)
    assert scenario["scenario"] == "maintenance" and scenario["rounds"] == 2, "second C is only authorized for maintenance"
    runtime = verify_runtime(plan, release, service, scenario["backend"])
    created = helper.read("case-create-response")["body"]
    previous = helper.accepted_first_result(created["case_id"])
    semantic_gate(helper.read("semantic-review"), previous, sha(HERE / "plan.json"), sha(helper.ROOT / "C1-result-0-response.json"))
    helper.save("second-intent", {**runtime, "max_model_calls": 4, "max_runs": 1, "retries": 0,
        "semantic_review_sha256": sha(helper.ROOT / "semantic-review.json"), "human_source": "fixed_driver"})
    cid, revision = created["case_id"], created["scope_revision"]
    scope = {"kind": "selected_alerts", "alert_ids": [aids[0]], "object_keys": [],
        "window_start": scenario["window_start"], "window_end": scenario["window_end"],
        "limitations": ["Only process-task authorization is confirmed; completion and network attribution are not confirmed."]}
    helper.http("H", "POST", f"/api/v1/socai2/cases/{cid}/tasks", {"operation_key": helper.uid("H"),
        "expected_scope_revision": revision, "title": "Confirm maintenance authorization", "state": "completed",
        "assignee_id": service.USER, "result_text": "I authorized inventory.ps1 on " + scenario["host"] +
        " during this window. I have not confirmed successful script completion or which process made the network connection.",
        "result_scope": scope})
    pending = helper.http("prepare", "POST", f"/api/v1/socai2/cases/{cid}/baseline/prepare",
        {"operation_key": helper.uid("prepare"), "expected_scope_revision": revision})
    helper.start_round("C2", cid, pending["pending_run_id"], revision, previous)
    helper.http("case-final", "GET", f"/api/v1/socai2/cases/{cid}")
    helper.http("history-final", "GET", f"/api/v1/socai2/cases/{cid}/history")

TABLES = ("alerts", "alert_materials", "alert_source_refs", "alert_objects", "alert_assessments",
    "incidents", "incident_alerts", "incident_diagnoses", "cases", "case_alerts", "case_incidents",
    "case_assessments", "case_assessment_sources", "case_assessment_members", "runs", "run_members", "run_steps",
    "artifacts", "results", "result_members", "tasks", "task_revisions", "conversations", "messages",
    "graph_explorations", "activities", "activity_targets", "comments", "response_links")


def export_queries(helper, service, incident):
    cid = str(uuid5(UUID(service.TENANT), "socai2.case.create:" + helper.uid("case")))
    quote = service.literal
    tenant = quote(service.TENANT)
    aids = ",".join(quote(str(UUID(a))) for a in helper.alert_ids())
    stages = ",".join(quote(str(uuid5(UUID(service.TENANT), "socai2.stage:" + helper.uid(label)))) for label in ("A0", "A1", "I"))
    runs = "SELECT id FROM socai2.runs WHERE tenant_id=" + tenant + " AND (case_id=" + quote(cid) + " OR id IN (" + stages + "))"
    subject = "subject_case_id=" + quote(cid) + " OR subject_alert_id IN (" + aids + ") OR subject_incident_id=" + quote(incident)
    clauses = {}
    for table in TABLES:
        if table == "alerts":
            clause = "t.id IN (" + aids + ")"
        elif table in {"alert_materials", "alert_source_refs", "alert_objects"}:
            clause = "t.alert_id IN (" + aids + ")"
        elif table in {"incidents", "incident_alerts"}:
            clause = "t." + ("id" if table == "incidents" else "incident_id") + "=" + quote(incident)
        elif table in {"alert_assessments", "incident_diagnoses"}:
            clause = "t.source_run_id IN (" + runs + ")"
        elif table == "runs":
            clause = "t.id IN (" + runs + ")"
        elif table in {"run_members", "run_steps"}:
            clause = "t.run_id IN (" + runs + ")"
        elif table == "artifacts":
            clause = "t.run_id IN (" + runs + ") OR t.case_id=" + quote(cid) + " OR (t.run_id IS NULL AND t.alert_id IN (" + aids + "))"
        elif table == "activities":
            clause = subject
        elif table == "activity_targets":
            clause = "t.activity_id IN (SELECT id FROM socai2.activities WHERE tenant_id=" + tenant + " AND (" + subject + "))"
        elif table in {"comments", "response_links"}:
            clause = "t.case_id=" + quote(cid) + " OR t.alert_id IN (" + aids + ") OR t.incident_id=" + quote(incident)
        else:
            clause = "t." + ("id" if table == "cases" else "case_id") + "=" + quote(cid)
        clauses[table] = "SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY t.id),'[]'::jsonb) FROM socai2." + table + " t WHERE tenant_id=" + tenant + " AND (" + clause + ")"
    return cid, runs, clauses


def export(plan, release, service, key):
    _, helper, _, incident = card(plan, release, service, key)
    cid, _runs, clauses = export_queries(helper, service, incident)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    query = "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY; SELECT jsonb_build_object(" + ",".join(
        service.literal(t) + ",(" + sql + ")" for t, sql in clauses.items()) + "); COMMIT;"
    data = json.loads(service.pg(service.DATABASE, query))
    helper.save("database-" + stamp, data)
    baseline_ids = [str(UUID(r["id"])) for r in data["runs"] if r["kind"] == "baseline"]
    freshness = []
    for rid in baseline_ids:
        value = json.loads(service.pg(service.DATABASE, "SELECT socai2.baseline_input_freshness(" +
            service.literal(service.TENANT) + "::uuid," + service.literal(rid) + "::uuid)"))
        freshness.append({"run_id": rid, "value": value, "source": "socai2.baseline_input_freshness"})
    helper.save("input-freshness-" + stamp, {"read_at": datetime.now(UTC).isoformat(), "case_id": cid, "runs": freshness})
    if data["cases"]:
        helper.http("case-export-" + stamp, "GET", f"/api/v1/socai2/cases/{cid}")
        helper.http("history-export-" + stamp, "GET", f"/api/v1/socai2/cases/{cid}/history")
        helper.http("tasks-export-" + stamp, "GET", f"/api/v1/socai2/cases/{cid}/tasks")
    helper.save("export-scope-" + stamp, {"case_id": cid, "card": key, "read_at": datetime.now(UTC).isoformat(),
        "database": service.DATABASE, "all_related_tables": len(TABLES), "table_counts": {k: len(v) for k, v in data.items()},
        "database_snapshot": "single readonly repeatable-read transaction", "api_and_freshness_reads": "separate later readonly observations"})
    unchanged = service.old_snapshot() == json.loads((service.PRIVATE / "original-containers.json").read_text())
    assert unchanged and service.protected_model_config() == read("protected-private")
    files = {p.name: json.loads(p.read_text()) for p in sorted(helper.ROOT.glob("*.json"))}
    files.update({"batch-" + name + ".json": read(name) for name in ("ingest-result", "ingest-subjects", "lake-readback", "lake-preflight")})
    print(json.dumps({"export": files, "original_containers_unchanged": unchanged, "credentials_exported": False,
        "synthetic_only": True, "database": service.DATABASE, "card": key, "table_counts": {k: len(v) for k, v in data.items()}}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["preflight", "ingest", "first", "second", "export"])
    parser.add_argument("--card", choices=[b + "-card-" + str(i) for b in ("deepseek", "small") for i in (1, 2, 3)])
    parser.add_argument("--backend", choices=["deepseek", "small"], default="deepseek")
    args = parser.parse_args()
    plan, release, service = bootstrap()
    if args.phase == "preflight":
        print(json.dumps(verify_runtime(plan, release, service, args.backend)))
    elif args.phase == "ingest":
        ingest(plan, release, service)
    else:
        assert args.card, "an explicit fixed card is required"
        {"first": first, "second": second, "export": export}[args.phase](plan, release, service, args.card)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 -- no credential-bearing provider exception text
        print(json.dumps({"failed": True, "error_type": type(exc).__name__,
            "detail": str(exc) if isinstance(exc, AssertionError) else "external operation failed; inspect saved phase evidence"}))
        sys.exit(1)
