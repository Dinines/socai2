"""New fixed repair cards ON 21; credentials remain inside this server process.

Reuses the verified service helper, original HTTP evidence/readback helpers,
and Kafka worker. No deployment or migration operation is exposed here.
"""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

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
    assert plan["batch"] == "repair-k5" and plan["max_model_calls"] == 22
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
    assert approval.get("max_model_calls") == 22


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


def ingest(plan, release, service):
    core_gate(plan)
    verify_runtime(plan, release, service, "deepseek")
    save("ingest-intent", {"model_calls": 0, "alerts": 4, "lake_events": 4,
        "topic_prefix": plan["topic_prefix"], "group": plan["group"]})
    # Kept only on 21 and deliberately excluded from all exports.
    save("protected-private", service.protected_model_config())
    original, independent = service.environment("socai2-fusion-1"), service.environment(service.NEW)
    env = {key: value for key, value in original.items() if key.startswith("KAFKA_")}
    prefix, redis = plan["topic_prefix"], urlsplit(independent["REDIS_URL"])
    env.update({"KAFKA_TOPIC_ALERTS_RAW": prefix + ".alerts.raw", "KAFKA_TOPIC_RAW_EVENTS": prefix + ".raw_events",
        "KAFKA_TOPIC_ALERTS_FUSED": prefix + ".alerts.fused", "KAFKA_CONSUMER_GROUP": plan["group"],
        "KAFKA_SSL_CAFILE": "/run/certs/ca.crt", "DATABASE_URL": independent["DATABASE_URL"],
        "REDIS_URL": urlunsplit(redis._replace(path="/13")), "ENVIRONMENT": "production",
        "AISOC_ALERT_STORE_SCHEMA": "socai2", "AISOC_EVENT_PROMOTION_ENABLED": "false",
        "AISOC_UEBA_FUSION_ENABLED": "false", "AISOC_DETECTION_ENGINE_ENABLED": "false",
        "AISOC_WINDOWED_DETECTION_ENABLED": "false", "CLICKHOUSE_DATABASE": service.LAKE,
        "CLICKHOUSE_HOST": original["CLICKHOUSE_HOST"], "CLICKHOUSE_PORT": original["CLICKHOUSE_PORT"],
        "CLICKHOUSE_USER": original["CLICKHOUSE_USER"], "CLICKHOUSE_PASSWORD": original["CLICKHOUSE_PASSWORD"]})
    assert urlsplit(env["DATABASE_URL"]).path == "/" + service.DATABASE
    files = {p.relative_to(release / "fusion").as_posix(): p.read_text() for p in (release / "fusion/app").rglob("*.py")}
    packet = {"environment": env, "files": files, "cases": plan["cases"], "topic_prefix": prefix,
        "expected_fused": 5, "expected_lake": 4, "replay_alert": True}
    output = service.command(["docker", "exec", "-i", service.NEW, "python", "-c",
        (HERE / "kafka_chain_child.py").read_text()], body=json.dumps(packet).encode(), timeout=180)
    records = [json.loads(line.removeprefix("K1_RESULT=")) for line in output.splitlines() if line.startswith("K1_RESULT=")]
    assert len(records) == 1
    save("ingest-result", records[0])
    assert records[0]["passed"], "Kafka ingestion failed; do not start models"
    fused = {row["value"]["alert"]["source_alert_id"]: row["value"] for row in records[0]["fused"]}
    subjects = []
    for case in plan["cases"]:
        members = [fused[alert["source_alert_id"]] for alert in case["alerts"]]
        ids, incidents = {row["alert_row_id"] for row in members}, {row["incident_id"] for row in members}
        assert len(ids) == 2 and len(incidents) == 1, "card did not produce exactly two alerts and one incident"
        incident = next(iter(incidents))
        actual = json.loads(service.pg(service.DATABASE, "SELECT coalesce(json_agg(alert_id),'[]') FROM socai2.incident_alerts WHERE tenant_id="
            + service.literal(service.TENANT) + " AND incident_id=" + service.literal(incident)))
        assert set(actual) == ids, "incident contains unexpected members"
        subjects.append({"backend": case["backend"], "alert_ids": sorted(ids), "incident_id": incident})
    assert len({item["incident_id"] for item in subjects}) == 2, "paired backend incidents merged"
    save("ingest-subjects", subjects)
    assert service.protected_model_config() == read("protected-private"), "protected configuration changed"
    print(json.dumps({"ingested": True, "model_calls": 0, "fused": 5, "lake_events": 4}))


def card(plan, release, service, backend):
    scenario = next(case for case in plan["cases"] if case["backend"] == backend)
    ingestion = read("ingest-result")
    assert ingestion["passed"]
    assert len({item["incident_id"] for item in read("ingest-subjects")}) == 2
    fused = {row["value"]["alert"]["source_alert_id"]: row["value"] for row in ingestion["fused"]}
    members = [fused[alert["source_alert_id"]] for alert in scenario["alerts"]]
    ids = [row["alert_row_id"] for row in members]
    incidents = {row["incident_id"] for row in members}
    assert len(ids) == len(set(ids)) == 2 and len(incidents) == 1
    helper = load("repair_http_" + backend, release / "next_acceptance_remote.py")
    helper.service = service
    helper.BATCH = plan["batch"] + "-" + backend
    helper.ROOT = HERE / backend
    helper.alert_ids = lambda: ids
    return scenario, helper, ids, next(iter(incidents))


def first(plan, release, service, backend):
    core_gate(plan)
    runtime = verify_runtime(plan, release, service, backend)
    scenario, helper, _, incident = card(plan, release, service, backend)
    helper.save("first-intent", {**runtime, "max_model_calls": 7, "max_runs": 4, "retries": 0})
    helper.save("fixture", {"incident_id": incident, "window_start": scenario["window_start"],
        "window_end": scenario["window_end"]})
    helper.stages()
    helper.case_first()
    print(json.dumps({"backend": backend, "first_phase_finished": True, "next": "export and root semantic review"}))


def page_human(helper, case_id, previous, plan_hash, alert_id):
    from repair_page_proxy_20261105 import digest_json
    approval = helper.read("page-human-review")
    session = helper.read("page-session-end")
    saved = helper.read("page-H-task")
    assert session.get("closed") is True and session.get("case_id") == case_id
    assert approval.get("approved") is True and approval.get("reviewer") == "root"
    assert approval.get("plan_sha256") == plan_hash and approval.get("first_result_id") == previous
    assert approval.get("task_id") == saved["id"] == session.get("task_id")
    assert approval.get("task_revision_id") == saved["current_revision_id"] == session.get("final_revision_id")
    assert approval.get("task_sha256") == digest_json(saved) == session.get("final_task_sha256")
    assert approval.get("session_end_sha256") == sha(helper.ROOT / "page-session-end.json")
    current = helper.http("page-H-current", "GET", f"/api/v1/socai2/cases/{case_id}/tasks/{saved['id']}")
    assert current == saved, "page H changed since root review"
    assert current["case_id"] == case_id and current["current"]["state"] == "completed"
    assert current["current"]["result_scope"]["alert_ids"] == [alert_id]
    assert current["current"]["completed_by"] == helper.service.USER
    return {"task_id": current["id"], "revision_id": current["current_revision_id"],
        "task_sha256": digest_json(current), "origin": "page", "created_by_driver": False}


def second(plan, release, service, backend, human_source="page"):
    core_gate(plan)
    runtime = verify_runtime(plan, release, service, backend)
    scenario, helper, aids, _ = card(plan, release, service, backend)
    approval = helper.read("semantic-review")
    created = helper.read("case-create-response")["body"]
    previous = helper.accepted_first_result(created["case_id"])
    semantic_gate(approval, previous, sha(HERE / "plan.json"), sha(helper.ROOT / "C1-result-0-response.json"))
    cid, revision = created["case_id"], created["scope_revision"]
    if human_source == "page":
        page_receipt = page_human(helper, cid, previous, sha(HERE / "plan.json"), aids[0])
    else:
        assert not (helper.ROOT / "page-session-start.json").exists(), "page H session exists; driver must not create another task"
    helper.save("second-intent", {**runtime, "max_model_calls": 4, "max_runs": 1, "retries": 0,
        "human_source": human_source, "semantic_review_sha256": sha(helper.ROOT / "semantic-review.json")})
    scope = {"kind": "selected_alerts", "alert_ids": [aids[0]], "object_keys": [],
        "window_start": scenario["window_start"], "window_end": scenario["window_end"],
        "limitations": ["Only process-task authorization is confirmed; completion and network attribution are not confirmed."]}
    if human_source == "page":
        helper.save("page-H-use", page_receipt)
    else:
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["preflight", "ingest", "first", "second", "export"])
    parser.add_argument("--backend", choices=["deepseek", "small"], default="deepseek")
    parser.add_argument("--human-source", choices=["page", "driver"], default="page")
    args = parser.parse_args()
    plan, release, service = bootstrap()
    if args.phase == "preflight":
        print(json.dumps(verify_runtime(plan, release, service, args.backend)))
    elif args.phase == "ingest":
        ingest(plan, release, service)
    elif args.phase == "export":
        _, helper, _, _ = card(plan, release, service, args.backend)
        helper.export()
        print(json.dumps({"protected_unchanged": service.protected_model_config() == read("protected-private")}))
    elif args.phase == "first":
        first(plan, release, service, args.backend)
    else:
        second(plan, release, service, args.backend, args.human_source)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 -- provider/connection details may contain credentials
        print(json.dumps({"failed": True, "error_type": type(exc).__name__,
            "detail": str(exc) if isinstance(exc, AssertionError) else "external operation failed; inspect saved phase evidence"}))
        sys.exit(1)
