"""Bounded local Kafka → Fusion → A/I/C → reviewed H/C validation.

prepare is offline. Other phases require --execute and exclusively target the
fixed local environment. A phase intent is written before any mutation; an
existing intent is never replayed. This driver never starts a service or model.
"""
import argparse
import asyncio
import fcntl
import json
from datetime import UTC, datetime
from uuid import UUID, uuid5

from backend_profile import BACKENDS, ModelProfileMismatch
from backend_profile import validate as validate_model_profile
from config import (
    API_ROLE,
    CH_READER,
    DATABASE,
    LAKE,
    PORTS,
    STATE,
    TENANT,
    TOPIC,
    USER,
    read_private,
    runtime_environment,
)
from flow_export import export
from flow_fixture import encoded, prepare, sha, source_hashes, uid


class FlowStopped(RuntimeError):
    pass


class ConfigurationStopped(FlowStopped):
    """Do not contact services, including automatic failure export."""


class Driver:
    def __init__(self, root, values):
        self.root, self.values = root, values
        self.plan = self.read("plan")
        assert self.plan["tenant_id"] == TENANT and self.plan["database"] == DATABASE
        assert self.plan["lake_database"] == LAKE and self.plan["topic_prefix"] == TOPIC
        assert self.plan["global_local_model_call_cap"] == 50 and self.plan["max_model_calls"] == 11
        self.batch = self.plan["batch_id"]
        self.env = runtime_environment("api", values)

    def read(self, name):
        return json.loads((self.root / (name + ".json")).read_text())

    def save(self, name, value):
        with (self.root / (name + ".json")).open("x") as stream:
            stream.write(encoded(value).decode() + "\n")

    async def connect(self):
        import asyncpg
        return await asyncpg.connect(host="127.0.0.1", port=PORTS["postgres"], database=DATABASE,
            user=API_ROLE, password=self.values["API_DB_PASSWORD"], ssl=False, timeout=10,
            server_settings={"statement_timeout": "30000", "application_name": "socai2-local-flow"})

    async def pg(self, sql, *args):
        connection = await self.connect()
        try:
            async with connection.transaction(readonly=True):
                await connection.execute("SELECT set_config('app.current_tenant_id',$1,true)", TENANT)
                return [dict(r) for r in await connection.fetch(sql, *args)]
        finally:
            await connection.close()

    async def lake(self):
        import httpx
        ids = [UUID(e["event_id"]) for e in self.plan["case"]["events"]]
        # UUIDs and database are code-owned, not caller SQL or free-form filters.
        sql = "SELECT * FROM " + LAKE + ".raw_events WHERE tenant_id='" + TENANT + "' AND event_id IN (" + ",".join("'" + str(i) + "'" for i in ids) + ") ORDER BY event_id FORMAT JSONEachRow"
        async with httpx.AsyncClient(trust_env=False, timeout=15) as client:
            response = await client.post(f"http://127.0.0.1:{PORTS['clickhouse_http']}/", content=sql,
                auth=(CH_READER, self.values["CH_READER_PASSWORD"]))
        if response.status_code != 200:
            raise FlowStopped("lake_readback_http_" + str(response.status_code))
        return [json.loads(line) for line in response.text.splitlines()]

    async def http(self, label, method, path, body=None, *, record=True, require_success=True):
        import httpx
        assert path.startswith("/api/v1/socai2/") and "?" not in path and ".." not in path
        request = {"method": method, "path": path, "body": body, "authentication": "local_api_key"}
        if record:
            self.save(label + "-request", request)
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=150) as client:
                response = await client.request(method, f"http://127.0.0.1:{PORTS['api']}" + path,
                    json=body, headers={"Authorization": "Bearer " + self.values["API_KEY"]})
        except httpx.HTTPError as exc:
            result = {"method": method, "path": path, "status": None, "body": None,
                "failure": {"category": "transport_unknown", "exception_type": type(exc).__name__, "retry_allowed": False}}
            if record:
                self.save(label + "-response", result)
            if require_success:
                raise FlowStopped("http_transport_unknown") from None
            return result
        try:
            body = response.json()
        except ValueError:
            body = None
        result = {"method": method, "path": path, "status": response.status_code, "body": body}
        if body is None:
            result["unparsed_body"] = {"bytes": len(response.content), "sha256": sha(response.content)}
        if record:
            self.save(label + "-response", result)
        if require_success and not 200 <= response.status_code < 300:
            raise FlowStopped("http_rejected_" + str(response.status_code))
        return result

    async def budget(self, reserve=0):
        # Actual attempted model steps remain the counting authority; unknown
        # attempts consume a slot and prevent a new model phase.
        rows = await self.pg("SELECT r.id,r.state,count(s.id) FILTER (WHERE s.kind='model' AND s.state NOT IN ('planned','skipped')) AS calls FROM socai2.runs r LEFT JOIN socai2.run_steps s ON s.run_id=r.id AND s.tenant_id=r.tenant_id WHERE r.tenant_id=$1::uuid GROUP BY r.id,r.state", UUID(TENANT))
        if any(r["state"] in {"unknown", "running"} for r in rows):
            raise FlowStopped("active_or_unknown_run_blocks_dispatch")
        used = sum(r["calls"] for r in rows)
        if used + reserve > 50:
            raise FlowStopped("global_50_model_attempt_cap")
        return {"attempted_models": used, "reserved_for_phase": reserve, "global_cap": 50}

    async def preflight(self):
        import httpx
        try:
            model_profile = validate_model_profile(self.plan, self.env)
        except ModelProfileMismatch as exc:
            raise ConfigurationStopped(str(exc)) from None
        if not self.values["OPENAI_API_KEY"]:
            raise ConfigurationStopped("local_model_credential_not_configured")
        # A simultaneous source change must not mask an unverified backend
        # and enter the ordinary failure-export path that reads local services.
        self.verify_sources()
        async with httpx.AsyncClient(trust_env=False, timeout=10) as client:
            for service in ("api", "fusion"):
                response = await client.get(f"http://127.0.0.1:{PORTS[service]}/readyz")
                if response.status_code != 200:
                    raise FlowStopped(service + "_not_ready")
        row = (await self.pg("SELECT current_database() AS database, (SELECT count(*) FROM information_schema.tables WHERE table_schema='socai2' AND table_type='BASE TABLE') AS tables, to_regprocedure('socai2.baseline_input_freshness(uuid,uuid)') IS NOT NULL AS freshness"))[0]
        assert row == {"database": DATABASE, "tables": 29, "freshness": True}
        return {"database": row, "runtime": model_profile,
            "budget": await self.budget(), "model_calls": 0, "services_started": False}

    def verify_sources(self):
        if source_hashes() != self.plan["source_sha256"]:
            raise FlowStopped("source_changed_after_plan_freeze_new_batch_required")

    async def ingest(self):
        from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
        await self.preflight()
        existing = await self.pg("SELECT id FROM socai2.alerts WHERE tenant_id=$1::uuid AND id=ANY($2::uuid[])",
            UUID(TENANT), list(map(UUID, self.plan["canonical_alert_ids"])))
        assert not existing and not await self.lake(), "planned identities already exist; no replay"
        self.save("ingest-intent", {"dispatched_at": datetime.now(UTC).isoformat(), "alerts": 2, "lake_events": 2, "model_calls": 0})
        topics = {"events": TOPIC + ".raw_events", "alerts": TOPIC + ".alerts.raw"}
        producer = AIOKafkaProducer(bootstrap_servers=f"127.0.0.1:{PORTS['kafka']}", value_serializer=encoded)
        reader = AIOKafkaConsumer(TOPIC + ".alerts.fused", bootstrap_servers=f"127.0.0.1:{PORTS['kafka']}",
            auto_offset_reset="earliest", group_id=None, value_deserializer=lambda b: json.loads(b))
        receipts, fused = [], {}
        source_ids = {a["source_alert_id"] for a in self.plan["case"]["alerts"]}
        try:
            await producer.start()
            await reader.start()
            for kind in ("events", "alerts"):
                for index, value in enumerate(self.plan["case"][kind]):
                    self.save(f"send-{kind}-{index}-intent", {"topic": topics[kind], "sha256": sha(encoded(value))})
                    meta = await producer.send_and_wait(topics[kind], value)
                    receipt = {"kind": kind, "index": index, "topic": meta.topic, "partition": meta.partition,
                        "offset": meta.offset, "sha256": sha(encoded(value))}
                    self.save(f"send-{kind}-{index}-receipt", receipt)
                    receipts.append(receipt)
            deadline = asyncio.get_running_loop().time() + 90
            while len(fused) < 2 and asyncio.get_running_loop().time() < deadline:
                for messages in (await reader.getmany(timeout_ms=1000)).values():
                    for message in messages:
                        value = message.value
                        sid = value.get("alert", {}).get("source_alert_id")
                        if sid in source_ids:
                            assert sid not in fused, "unexpected repeated fused record"
                            fused[sid] = {"topic": message.topic, "partition": message.partition,
                                "offset": message.offset, "value": value}
            self.save("ingest-receipts", {"sent": receipts, "fused": list(fused.values())})
            assert len(fused) == 2, "fused_readback_incomplete"
        finally:
            await reader.stop()
            await producer.stop()
        members = [fused[a["source_alert_id"]]["value"] for a in self.plan["case"]["alerts"]]
        aids, incidents = [m["alert_row_id"] for m in members], {m["incident_id"] for m in members}
        assert aids == self.plan["canonical_alert_ids"] and len(incidents) == 1
        incident = next(iter(incidents))
        actual = await self.pg("SELECT alert_id FROM socai2.incident_alerts WHERE tenant_id=$1::uuid AND incident_id=$2::uuid",
            UUID(TENANT), UUID(incident))
        assert {str(a["alert_id"]) for a in actual} == set(aids)
        rows = []
        for _ in range(30):
            rows = await self.lake()
            if len(rows) == 2:
                break
            await asyncio.sleep(.5)
        expected = {e["event_id"]: e for e in self.plan["case"]["events"]}
        assert len(rows) == 2 and {r["event_id"] for r in rows} == set(expected), "lake_readback_missing_or_duplicate"
        for row in rows:
            ocsf = json.loads(row["ocsf_json"])
            assert {k: v for k, v in ocsf.items() if k != "_socai2_storage"} == expected[row["event_id"]]["ocsf_event"]
        self.save("lake-readback", {"passed": True, "database": LAKE, "rows": rows, "query_scope": "exact_frozen_event_ids"})
        self.save("ingest-subjects", {"alert_ids": aids, "incident_id": incident, "passed": True})
        return {"alerts": 2, "incidents": 1, "lake_rows": 2, "model_calls": 0}

    async def start_round(self, label, cid, rid, revision, previous=None):
        case = self.plan["case"]
        response = await self.http(label, "POST", f"/api/v1/socai2/cases/{cid}/runs/{rid}/start", {
            "operation_key": uid(self.batch, label), "expected_scope_revision": revision,
            "window_start": case["window_start"], "window_end": case["window_end"], "comparison_result_id": previous})
        for index, result_id in enumerate(response["body"]["result_ids"]):
            await self.http(f"{label}-result-{index}", "GET", f"/api/v1/socai2/cases/{cid}/results/{result_id}")
        return response["body"]

    async def first(self):
        await self.preflight()
        assert self.read("ingest-subjects")["passed"] and self.read("lake-readback")["passed"]
        allowance = await self.budget(7)
        self.save("first-intent", {**allowance, "max_model_calls": 7, "retries": 0, "plan_sha256": sha((self.root / "plan.json").read_bytes())})
        subjects = self.read("ingest-subjects")
        stages = [("A" + str(i), f"/alerts/{aid}/analyze") for i, aid in enumerate(subjects["alert_ids"])]
        stages.append(("I", f"/incidents/{subjects['incident_id']}/diagnose"))
        stage_outcomes = []
        for label, path in stages:
            await self.http(label, "POST", "/api/v1/socai2" + path, {"operation_key": uid(self.batch, label)})
            await self.budget()
            stage_id = uuid5(UUID(TENANT), "socai2.stage:" + uid(self.batch, label))
            row = (await self.pg("SELECT state,stop_reason FROM socai2.runs WHERE tenant_id=$1::uuid AND id=$2::uuid", UUID(TENANT), stage_id))[0]
            stage_outcomes.append({"stage": label, "run_id": str(stage_id), **row})
            if row["state"] not in {"completed", "failed", "cancelled"}:
                raise FlowStopped("stage_not_completed:" + label + ":" + str(row["stop_reason"]))
        # A/I is context, not a prerequisite for a Case investigation. Retain
        # known failures and let C6 reason from the original alert materials.
        # budget() above still blocks any unknown/active call without retry.
        self.save("prior-stage-outcomes", {"stages": stage_outcomes, "failed_analyses_not_adopted": True})
        created = (await self.http("case-create", "POST", "/api/v1/socai2/cases", {"operation_key": uid(self.batch, "case"),
            "title": self.plan["case"].get("title", "Maintenance record review") + " " + self.batch,
            "description": self.plan["case"].get("description", "本案涉及主机 " + self.plan["case"]["host"] +
                " 的进程启动与网络连接记录，需核查行为关系、授权情况及影响范围。"),
            "incident_ids": [subjects["incident_id"]], "alert_ids": []}))["body"]
        await self.start_round("C1", created["case_id"], created["pending_run_id"], created["scope_revision"])
        return {"first_phase_returned": True, "next": "export_and_root_semantic_review", "budget": await self.budget()}

    def accepted_first(self):
        created = self.read("case-create-response")["body"]
        run = self.read("C1-response")["body"]
        detail = self.read("C1-result-0-response")["body"]
        result = detail["result"]
        assert run["run"]["state"] == "completed" and len(run["result_ids"]) == 1
        assert result["id"] == run["result_ids"][0] and result["case_id"] == created["case_id"]
        assert result["source_run_id"] == run["run"]["id"] and result["validation_state"] == "accepted"
        assert result["conclusion_origin"] == "model" and result["conclusion"]
        return created, result

    async def second(self):
        assert self.plan["case"].get("rounds", 2) == 2, "this fixture has no human follow-up phase"
        await self.preflight()
        created, previous = self.accepted_first()
        review = self.read("semantic-review")
        assert review.get("approved") is True and review.get("reviewer") == "root"
        assert review["plan_sha256"] == sha((self.root / "plan.json").read_bytes())
        assert review["first_result_sha256"] == sha((self.root / "C1-result-0-response.json").read_bytes())
        assert review["result_id"] == previous["id"]
        allowance = await self.budget(4)
        self.save("second-intent", {**allowance, "max_model_calls": 4, "retries": 0,
            "human_source": "fixed_synthetic_driver_not_real_employee", "review_sha256": sha((self.root / "semantic-review.json").read_bytes())})
        cid, revision, case = created["case_id"], created["scope_revision"], self.plan["case"]
        scope = {"kind": "selected_alerts", "alert_ids": [self.plan["canonical_alert_ids"][0]], "object_keys": [],
            "window_start": case["window_start"], "window_end": case["window_end"],
            "limitations": ["Synthetic driver confirms A0 task authorization only, not completion or network attribution."]}
        await self.http("H", "POST", f"/api/v1/socai2/cases/{cid}/tasks", {"operation_key": uid(self.batch, "H"),
            "expected_scope_revision": revision, "title": "Synthetic maintenance authorization statement", "state": "completed",
            "assignee_id": USER, "result_text": "Synthetic scenario driver: inventory.ps1 on " + case["host"] +
            " was authorized in this window. Successful script completion and the process making the network connection are not confirmed.",
            "result_scope": scope})
        pending = (await self.http("prepare", "POST", f"/api/v1/socai2/cases/{cid}/baseline/prepare", {
            "operation_key": uid(self.batch, "prepare"), "expected_scope_revision": revision}))["body"]
        await self.start_round("C2", cid, pending["pending_run_id"], revision, previous["id"])
        return {"second_phase_returned": True, "budget": await self.budget()}


async def run(args):
    root = STATE / "validation" / args.batch
    assert root.parent == STATE / "validation" and args.batch.startswith("local-") and "/" not in args.batch
    if args.phase == "prepare":
        plan, oracle = prepare(args.batch, args.window_start, backend=args.backend, model_values=read_private(), scenario=args.scenario)
        root.mkdir(parents=True, exist_ok=False)
        for name, value in (("plan", plan), ("expected", oracle)):
            (root / (name + ".json")).write_bytes(encoded(value) + b"\n")
        return {"prepared": str(root), "model_calls": 0, "service_connections": 0}
    assert args.execute, "explicit --execute is required; static preparation does not dispatch"
    driver = Driver(root, read_private())
    with (STATE / "validation-dispatch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            result = await export(driver) if args.phase == "export" else await getattr(driver, args.phase)()
            if args.phase in {"first", "second"}:
                result["export"] = await export(driver)
            driver.save(args.phase + "-outcome-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"), result)
            return result
        except Exception as exc:  # noqa: BLE001 -- save sanitized failure without credentials
            failure = {"phase": args.phase, "category": "controlled_stop" if isinstance(exc, (FlowStopped, AssertionError)) else "execution_error",
                "exception_type": type(exc).__name__, "code": str(exc) if isinstance(exc, FlowStopped) else "inspect_saved_intent_and_original_receipts",
                "retry_allowed": False, "recorded_at": datetime.now(UTC).isoformat()}
            driver.save(args.phase + "-failure-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"), failure)
            if isinstance(exc, ConfigurationStopped):
                return {"passed": False, **failure, "export_skipped_reason": "model_configuration_not_verified"}
            try:
                failure["export"] = await export(driver)
            except Exception as export_error:  # noqa: BLE001 -- preserve the primary failure
                failure["export_error_type"] = type(export_error).__name__
            return {"passed": False, **failure}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "preflight", "ingest", "first", "second", "export"])
    parser.add_argument("--batch", required=True)
    parser.add_argument("--window-start")
    parser.add_argument("--backend", choices=BACKENDS, default="deepseek", help="Freeze backend during prepare only")
    parser.add_argument("--scenario", choices=["maintenance", "routine", "credential", "impact"], default="maintenance")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.phase == "prepare" and not args.window_start:
        parser.error("prepare requires --window-start with an explicit timezone")
    if args.phase != "prepare" and args.backend != "deepseek":
        parser.error("--backend is only selected at prepare; other phases use the frozen plan")
    if args.phase != "prepare" and args.scenario != "maintenance":
        parser.error("--scenario is only selected at prepare; other phases use the frozen plan")
    result = asyncio.run(run(args))
    print(json.dumps(result, ensure_ascii=False, default=str), flush=True)
    return 1 if result.get("passed") is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
