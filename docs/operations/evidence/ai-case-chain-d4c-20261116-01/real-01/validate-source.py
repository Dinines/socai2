"""One D4c isolated current-task chain; fresh real model calls, labelled A/I cuts."""
import argparse
import asyncio
import copy
import hashlib
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / "services/api")]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=lambda v:
        v.model_dump(mode="json") if hasattr(v, "model_dump") else str(v)) + "\n")


def environment(config):
    for key in ("environment_file", "model_environment_file"):
        os.environ.update(json.loads(Path(config[key]).read_text()))
    os.environ.update(config["runtime_overrides"])
    for name, key in (("SOCAI2_INVESTIGATION_POLICY", "investigation_policy_file"),
                      ("SOCAI2_ANALYSIS_TASKS_CONFIG_FILE", "lifecycle_policy_file"),
                      ("SOCAI2_CASE_ALLOCATION_CONFIG_FILE", "allocation_policy_file"),
                      ("SOCAI2_RUN_RECORDS_CONFIG_FILE", "run_records_config_file")):
        os.environ[name] = config[key]
    os.environ.pop("SOCAI2_KNOWLEDGE_PROFILE", None)


def sources(config):
    files = [Path(__file__), *sorted((ROOT / "services/api/app/socai2").glob("*.py")),
             *sorted((ROOT / "services/api/app/socai2").glob("*.json")),
             *sorted((ROOT / "services/api/investigation_http").rglob("*.py")),
             ROOT / "services/api/app/services/llm_safety.py",
             ROOT / "services/api/app/services/llm_resolver.py",
             *[Path(config[k]) for k in ("investigation_policy_file", "lifecycle_policy_file",
                                         "allocation_policy_file", "run_records_config_file")]]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


async def snapshot(service, tenant):
    from app.models import socai2 as m
    from app.socai2.baseline_store import digest
    from sqlalchemy import select
    models = (m.Alerts, m.AlertMaterials, m.AlertObjects, m.AlertAssessments,
              m.Incidents, m.IncidentAlerts, m.IncidentDiagnoses, m.Cases, m.CaseAlerts,
              m.CaseIncidents, m.CaseAlertExclusions, m.AnalysisTasks, m.AnalysisAttempts,
              m.AnalysisSubjectState, m.Runs, m.RunMembers, m.RunSteps, m.Artifacts,
              m.Results, m.ResultMembers, m.CaseAssessments, m.CaseAssessmentSources,
              m.CaseAssessmentMembers, m.Activities, m.ActivityTargets)
    rows, hashes = {}, {}
    async with service.transaction(tenant, readonly=True) as store:
        for model in models:
            table = model.__table__
            values = [dict(r) for r in (await store.db.execute(select(table)
                .where(table.c.tenant_id == tenant).order_by(*table.primary_key.columns))).mappings()]
            rows[table.name] = json.loads(json.dumps(values, default=str))
            hashes[table.name] = {"count": len(values), "sha256": digest(rows[table.name])}
    return rows, hashes


async def main(config, out):
    from app.models import socai2 as m
    from app.socai2.ai_stage_delivery import selection
    from app.socai2.analysis_case_executor import executors
    from app.socai2.analysis_dispatch_config import DispatchPolicy
    from app.socai2.analysis_dispatch_redis import AnalysisQueues
    from app.socai2.analysis_dispatch_store import DispatchRepository
    from app.socai2.analysis_dispatcher import AnalysisDispatcher
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.baseline_analysis_model import TenantChatGateway
    from app.socai2.baseline_context import reference
    from app.socai2.baseline_contracts import Actor
    from app.socai2.baseline_store import F, R, digest
    from app.socai2.case_contracts import CaseCreate
    from app.socai2.case_service import CaseService
    from app.socai2.closed_json_units import read_units
    from app.socai2.stage_delivery import VERSION, validate_sources
    from app.socai2.stage_results import StageResultService, artifact
    from redis.asyncio import Redis
    from sqlalchemy import insert, null, select, text, update
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    out.mkdir(exist_ok=False)
    frozen_sources = sources(config)
    save(out / "source-before.json", frozen_sources)
    (out / "validate-source.py").write_text(Path(__file__).read_text())
    cfg = json.loads(Path(config["database_profile"]).read_text())
    assert cfg["host"] == "127.0.0.1" and cfg["processing_database"] == "v12_upgrade_dev"
    url = URL.create("postgresql+psycopg", username=cfg["admin"], password=Path(cfg["password_file"]).read_text().strip(),
        host=cfg["host"], port=cfg["port"], database=cfg["processing_database"])
    admin = create_async_engine(url, hide_parameters=True, connect_args={"sslmode": config["sslmode"]})
    engine = create_async_engine(url, hide_parameters=True,
        connect_args={"sslmode": config["sslmode"], "options": "-c role=" + cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cases, stage = CaseService(sessions), StageResultService(sessions)
    tasks = AnalysisTaskService(sessions, AnalysisTaskPolicy.load())
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())
    tenant, actor, iid = uuid4(), uuid4(), uuid4()
    calls, records, scans, dispatcher = [], [], [], None
    gate, release = asyncio.Event(), asyncio.Event()
    ai_mode = "real"
    source_path = Path(config["source_snapshot_file"])
    source = json.loads(source_path.read_text())["rows"]
    result = {"state": "running", "tenant_id": tenant, "actor_id": actor, "incident_id": iid,
        "database": cfg["processing_database"], "database_host": cfg["host"], "database_port": cfg["port"],
        "deployment": False, "new_kafka_messages": 0, "checks": [], "uncovered": [], "prose_quality": "not_independently_validated",
        "submission_transport": "current core services; ASGI GET readback", "model_kind": "fresh real generation"}
    save(out / "intent.json", {**result, "planned_case_rounds": 2, "planned_AI_primary_calls": 4,
        "injections": ["A1 closed rationale prefix", "I1 closed first member prefix", "I2 zero-length prefix"],
        "source_snapshot": str(source_path.relative_to(ROOT)), "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "profile": config["investigation_policy_file"], "limits_note": "unchanged current per-Run policy; no sample-until-pass",
        "log_query": "explicit unconfigured test dependency", "scan_time": "controlled next_check_at only; real dispatcher clock"})

    class Gateway(TenantChatGateway):
        def __init__(self, *, run_id=None, mode="real"):
            self.run_id, self.mode = run_id, mode

        async def complete(self, body, timeout):
            async with cases.transaction(tenant, readonly=True) as store:
                query = select(F).where(*store.where(F, F.c.kind == "model_request"))
                if self.run_id:
                    query = query.where(F.c.run_id == self.run_id)
                row = await store.one(query.order_by(F.c.captured_at.desc(), F.c.id.desc()).limit(1))
                attempt = await store.one(select(m.AnalysisAttempts.__table__).where(
                    m.AnalysisAttempts.tenant_id == tenant, m.AnalysisAttempts.run_id == row["run_id"]))
            request = row["content_json"].get("payload", row["content_json"])
            assert request["body"] == body
            code = "A" if "alert_boundary" in request else "I" if "incident_boundary" in request else request["case_boundary"].get("stage", "C3")
            visible = json.dumps(body["messages"], ensure_ascii=False)
            assert not any(tag in visible for tag in ("tenant_uid", "D4c", "d4c-20261116", "受控回放", "fixture"))
            call = {"stage": code, "mode": self.mode, "state": "started", "run_id": str(row["run_id"]),
                "task_id": str(attempt["task_id"]), "attempt_id": str(attempt["id"]), "attempt_no": attempt["attempt_no"],
                "request_artifact_id": str(row["id"]), "request": body,
                "started_at": datetime.now(timezone.utc).isoformat(), "real_model_call": True}
            calls.append(call)
            save(out / "calls.json", calls)
            print("real call started", code, self.mode, flush=True)
            try:
                raw = await super().complete(body, timeout)
                call.update(real_response=raw, real_response_sha256=digest(raw), state="responded",
                            responded_at=datetime.now(timezone.utc).isoformat())
                save(out / "calls.json", calls)
                delivered = copy.deepcopy(raw)
                if self.mode != "real":
                    content = raw["choices"][0]["message"]["content"]
                    if self.mode == "I2_empty":
                        cut = 0
                    else:
                        wanted = "$.rationale" if code == "A" else "$.members[0]"
                        found = read_units(content, **selection(code))["units"]
                        selected = next((u for u in found if u["path"] == wanted), None)
                        cut = selected["value_span"][1] if selected else 0
                        if selected is None:
                            result["uncovered"].append(self.mode + ": real answer lacks requested closed unit; zero prefix used, no invented unit")
                    delivered["choices"][0]["message"]["content"] = content[:cut]
                    delivered["choices"][0]["finish_reason"] = "length"
                    retained = read_units(content[:cut], **selection(code))["units"]
                    paths = [u["path"] for u in retained]
                    if code == "A":
                        if "$.evidence_ids" in paths:
                            delivered["choices"][0]["message"]["content"] = ""
                            cut, paths = 0, []
                            result["uncovered"].append(self.mode + ": field order cannot form requested prefix; zero prefix used")
                    elif self.mode == "I1_partial":
                        assert "$.members[1]" not in paths, paths
                    else:
                        assert not paths
                    injection = {"mode": self.mode, "character_cut_offset": cut,
                        "utf8_cut_offset": len(content[:cut].encode()), "source_body_sha256": hashlib.sha256(content.encode()).hexdigest(),
                        "delivered_body_sha256": hashlib.sha256(content[:cut].encode()).hexdigest(),
                        "real_finish_reason": raw["choices"][0]["finish_reason"], "delivered_finish_reason": "length",
                        "delivered_response_sha256": digest(delivered), "retained_candidate_paths": paths,
                        "usage_note": "actual remote usage counted once; local prefix injection is not a second generation"}
                    aid = uuid4()
                    async with stage.transaction(tenant) as store:
                        run = await store.one(select(R).where(*store.where(R, R.c.id == row["run_id"])))
                        await artifact(store, run, aid, "source_snapshot", {
                            "type": "verification_real_response_before_injection", "request_artifact_id": str(row["id"]),
                            "task_id": call["task_id"], "attempt_no": call["attempt_no"], "run_id": call["run_id"],
                            "real_response": raw, "real_response_sha256": digest(raw), "injection": injection},
                            await store.now(), [reference("artifact", row["id"], "execution_receipt")],
                            step_id=row["step_id"], schema_version="socai2.verification.response-injection.v1")
                    call.update(injection=injection, complete_response_artifact_id=str(aid))
                call.update(response=delivered, received_response_sha256=digest(delivered))
                save(out / "calls.json", calls)
                print("real call returned", code, self.mode, "actual", raw["choices"][0]["finish_reason"],
                      "received", delivered["choices"][0]["finish_reason"], flush=True)
                if self.mode == "I1_partial":
                    gate.set()
                    await release.wait()
                return delivered
            except Exception as exc:
                call.update(state="error", error_type=type(exc).__name__)
                raise
            finally:
                save(out / "calls.json", calls)

    async def checkpoint(name):
        saved, hashes = await snapshot(cases, tenant)
        save(out / (name + ".json"), {"rows": saved, "hashes": hashes})
        return saved

    async def remember(accepted, label):
        item = {"label": label, **accepted}
        records.append(item)
        save(out / "tasks.json", records)
        return item

    async def submit(kind, subject, intent, source_kind, label):
        accepted = await tasks.submit(tenant, kind=kind, subject_id=subject, intent=intent,
            source=source_kind, operation_key=uuid4(), submitted_by=actor if source_kind == "user" else None)
        return await remember(accepted, label)

    async def finish(entry):
        async with asyncio.timeout(config["check_timeout_seconds"]):
            while True:
                await dispatcher.tick()
                current = await tasks.read_task(tenant, entry["subject_type"], UUID(str(entry["subject_id"])), UUID(str(entry["task_id"])))
                if current["status"] not in {"accepted", "running"}:
                    break
                await asyncio.sleep(config["check_interval_seconds"])
        entry.update(status=current["status"], task=current)
        if current["attempts"]:
            assert len(current["attempts"]) == 1, current
            entry["run_id"] = str(current["attempts"][0]["run_id"])
        save(out / "tasks.json", records)
        saved = await checkpoint(entry["label"])
        if entry.get("run_id"):
            artifacts = {a["id"]: a for a in saved["artifacts"]}
            receipts = [a for a in artifacts.values() if a["run_id"] == entry["run_id"] and a["schema_version"] == VERSION]
            for receipt in receipts:
                validate_sources(receipt["content_json"], {aid: a["content_json"] for aid, a in artifacts.items()})
            entry["stage_receipts"] = [{"id": a["id"], "state": a["content_json"]["delivery"]["state"],
                "retained_paths": [u["path"] for u in a["content_json"]["retained_units"]]} for a in receipts]
            save(out / "tasks.json", records)
        print("task terminal", entry["label"], current["status"], flush=True)
        return saved

    async def scan(kind, subject, label, expected):
        before, _ = await snapshot(cases, tenant)
        state = next(s for s in before["analysis_subject_state"] if s["subject_id"] == str(subject))
        clock = datetime.fromisoformat(state["next_check_at"])
        counts = await handlers[kind].check_updates(tenant, clock)
        after, _ = await snapshot(cases, tenant)
        prior = {t["id"] for t in before["analysis_tasks"]}
        added = [t for t in after["analysis_tasks"] if t["id"] not in prior]
        scans.append({"label": label, "kind": kind, "next_check_at_before": state["next_check_at"],
            "controlled_scan_at": clock.isoformat(), "actual_observed_at": datetime.now(timezone.utc).isoformat(),
            "counts": counts, "new_tasks": added, "calls_before_after": len(calls)})
        save(out / "scans.json", scans)
        assert counts["submitted"] == expected and len(added) == expected, (label, counts, added)
        if added:
            task = added[0]
            assert task["intent"] == "check" and task["source"] == "periodic"
            return await remember({"task_id": UUID(task["id"]), "subject_type": task["subject_type"],
                "subject_id": UUID(task["subject_id"]), "status": "accepted", "intent": "check", "source": "periodic"}, label)
        return None

    async def unchanged_check(cid, label):
        before, _ = await snapshot(cases, tenant)
        count = len(calls)
        item = await submit("case_investigation", cid, "check", "user", label)
        after = await finish(item)
        assert item["status"] == "skipped" and not item["task"]["attempts"], item
        if item["task"]["reason_code"] != "no_changes":
            result["uncovered"].append(label + ": " + str(item["task"]["reason_code"]))
        assert len(after["runs"]) == len(before["runs"]) and len(calls) == count
        await scan("case_investigation", cid, label + "_periodic", 0)
        result["checks"].append(label + "_no_Run_no_call")

    def case_result(saved, entry, source_i, expected_delivery, previous=None):
        rid = entry["run_id"]
        run = next(r for r in saved["runs"] if r["id"] == rid)
        finals = [r for r in saved["results"] if r["source_run_id"] == rid]
        if run["state"] != "completed" or not finals:
            result["uncovered"].append(entry["label"] + ": real Case lacks completed Result: " + str(run["stop_reason"]))
        final = finals[0] if finals else None
        context = next(a["content_json"] for a in saved["artifacts"] if a["run_id"] == rid and a["schema_version"] == "socai2.baseline-context.v1")
        material = context["incidents"][str(iid)]["analysis_material"]
        assert material and material["source_run_id"] == source_i["run_id"]
        assert material["receipt"]["delivery"]["state"] == expected_delivery
        assert set(context["scope"]["alert_ids"]) == set(map(str, ids))
        assert set(material["input_selection"]["selected_alert_ids"]) == set(map(str, ids))
        assert len(material["units"]) >= 1 if expected_delivery == "partial" else len(material["units"]) == 0
        comparison = context["update_context"]["comparison_context"]
        assert comparison["previous_run_id"] == previous
        if previous is None:
            assert comparison["state"] == "initial" and comparison["comparison_result_id"] is None
        elif comparison["comparison_result_id"]:
            assert next(r for r in saved["results"] if r["id"] == comparison["comparison_result_id"])["source_run_id"] == previous
        stage_codes = {s["stage_code"] for s in saved["run_steps"] if s["run_id"] == rid}
        assert {"C1", "C2", "C3", "C4", "C5", "C6"} <= {code.split(".")[0] for code in stage_codes}, stage_codes
        c6_calls = [c for c in calls if c["run_id"] == rid and c["stage"] == "C6"]
        assert all(c["mode"] == "real" for c in calls if c["run_id"] == rid)
        if final and c6_calls and c6_calls[-1].get("response"):
            try:
                answer = json.loads(c6_calls[-1]["response"]["choices"][0]["message"]["content"])
            except ValueError:
                result["uncovered"].append(entry["label"] + ": C6 answer not complete JSON")
            else:
                if final["conclusion_origin"] == "model" and final["conclusion_state"] != "unavailable":
                    assert final["conclusion"] == answer["conclusion"]["text"]
        summary = {"run_id": rid, "result_id": final["id"] if final else None, "source_I_run_id": material["source_run_id"],
            "incident_selected_count": len(material["input_selection"]["selected_alert_ids"]),
            "actual_units": [{"path": u["path"], "scope": u["scope"]} for u in material["units"]],
            "case_member_count": len(context["scope"]["alert_ids"]), "comparison": comparison,
            "validation_state": final["validation_state"] if final else None, "conclusion_state": final["conclusion_state"] if final else None,
            "delivery_state": final["delivery_state"] if final else None, "stage_codes": sorted(stage_codes)}
        save(out / (entry["label"] + "-assertions.json"), summary)
        result["checks"].append(entry["label"] + "_C1_C6_Result_source_scope_comparison")
        return summary

    try:
        async with admin.begin() as db:
            await db.execute(text("""INSERT INTO public.tenants(id,name,slug,plan,is_active,settings,limits,created_at,updated_at)
                VALUES(:id,'Application operations',:slug,'enterprise',true,'{}','{}',now(),now())"""),
                {"id": tenant, "slug": "operations-" + str(tenant)})
            await db.execute(text("""INSERT INTO public.users(id,tenant_id,email,username,hashed_password,role,is_active,is_verified,preferences,created_at,updated_at)
                VALUES(:id,:tenant,:email,'Operations analyst','!','soc_analyst',true,false,'{}',now(),now())"""),
                {"id": actor, "tenant": tenant, "email": str(actor) + "@example.invalid"})
        ids, mapping = [], []
        async with stage.transaction(tenant) as store:
            await store.db.execute(insert(m.Incidents).values(id=iid, tenant_id=tenant, source_namespace="fusion.v1",
                source_incident_id=str(iid), title="登录、进程与外联活动", description="同一主机相关活动需要联合调查。", handling_status="new"))
            for old in source["alerts"]:
                aid, mid = uuid4(), uuid4()
                original = next(v for v in source["alert_materials"] if v["id"] == old["latest_material_id"])
                values = {k: old[k] for k in ("title", "description", "source_namespace", "original_vendor", "category",
                                             "severity", "severity_raw", "event_time_source", "tags")}
                values["event_time"] = datetime.fromisoformat(old["event_time"]) if old["event_time"] else None
                await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=tenant, source_identity_key=str(aid), source_alert_id=str(aid), **values))
                values = {k: original[k] for k in ("raw_text", "raw_json", "ocsf_json", "detection", "enrichment",
                                                  "source_scope", "material_state", "sha256", "retention")}
                await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=tenant, alert_id=aid, revision=1, **values))
                await store.db.execute(update(m.Alerts).where(m.Alerts.id == aid).values(latest_material_id=mid))
                for obj in source["alert_objects"]:
                    if obj["alert_id"] != old["id"]:
                        continue
                    values = {k: obj[k] for k in ("object_key", "object_type", "source_type", "object_role", "namespace", "raw_value",
                        "normalized_value", "source_path", "attributes", "asset_match_state", "asset_ref", "match_basis")}
                    for key in ("asset_ref", "match_basis"):
                        if values[key] is None:
                            values[key] = null()
                    await store.db.execute(insert(m.AlertObjects).values(id=uuid4(), tenant_id=tenant, alert_id=aid, material_id=mid, **values))
                await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=tenant, incident_id=iid, alert_id=aid,
                    membership_source="manual", correlation_basis={"reason": "同一主机相关活动"}, basis_version="v1", source_operation_id=uuid4()))
                ids.append(aid)
                mapping.append({"source_alert_id": old["id"], "alert_id": aid, "source_material_id": original["id"], "material_id": mid})
        assert len(ids) == 4
        result["alert_ids"] = ids
        save(out / "source-mapping.json", mapping)
        seeded = await checkpoint("00-materials-before-analysis")
        assert not seeded["analysis_tasks"] and not seeded["runs"]
        probe = Gateway()
        assert await probe.configure(cases, tenant)
        result["model_route"] = {"model": probe.model, "protocol": probe.provider, "schema_profile": probe.schema_profile}
        handlers = executors({k: config[k] for k in ("investigation_policy_file", "incident", "case")}, tasks)
        handlers["alert_triage"].gateway_factory = lambda: Gateway(mode=ai_mode)
        handlers["incident_diagnosis"].gateway_factory = lambda: Gateway(mode=ai_mode)
        handlers["case_investigation"].gateway_factory = lambda claim: Gateway(run_id=claim.run_id)
        handlers["case_investigation"].lake_factory = lambda _: SimpleNamespace(configured=lambda: False)
        policy = DispatchPolicy(**config["dispatch"])
        dispatcher = AnalysisDispatcher(DispatchRepository(tasks, tenant), AnalysisQueues(redis, policy.namespace, tenant), policy, handlers)
        await dispatcher.start()

        ai_mode = "A1_partial"
        a1 = await submit("alert_triage", ids[0], "initial", "ingress", "01-A1")
        saved = await finish(a1)
        assert a1["status"] == "failed" and a1["stage_receipts"][0]["state"] in {"partial", "none"}
        assert next(a for a in saved["alerts"] if a["id"] == str(ids[0]))["latest_triage_id"] is None
        result["checks"].append("A1_partial_no_invented_triage")

        ai_mode = "I1_partial"
        i1 = await submit("incident_diagnosis", iid, "initial", "ingress", "02-I1")
        async with asyncio.timeout(config["check_timeout_seconds"]):
            while not gate.is_set():
                await dispatcher.tick()
                current = await tasks.read_task(tenant, "incident", iid, i1["task_id"])
                assert current["status"] in {"accepted", "running"}, current
                await asyncio.sleep(config["check_interval_seconds"])
        created = await cases.create_case(tenant, CaseCreate(operation_key=uuid4(), title="登录、进程与外联活动调查",
            incident_ids=[iid]), actor=Actor(user_id=actor, name="Operations analyst"))
        cid = created.primary_case_id
        initial = created.allocations[0].initial_task
        c1 = await remember({"task_id": initial.task_id, "subject_type": "case", "subject_id": cid,
            "status": "accepted", "intent": "initial", "source": "case_create"}, "03-Case-R1")
        result["case_id"] = cid
        save(out / "created.json", created)
        admission = await checkpoint("02a-case-created-during-I")
        assert len(admission["case_alerts"]) == 4 and admission["incidents"][0]["active_case_id"] == str(cid)
        assert not any(r["case_id"] == str(cid) for r in admission["runs"])
        assert not any(a["task_id"] == str(initial.task_id) for a in admission["analysis_attempts"])
        release.set()
        await finish(i1)
        assert i1["status"] == "failed" and i1["stage_receipts"][0]["state"] in {"partial", "none"}
        saved = await finish(c1)
        result["round1"] = case_result(saved, c1, i1, i1["stage_receipts"][0]["state"])
        await unchanged_check(cid, "04-unchanged-R1")

        ai_mode = "real"
        a2 = await submit("alert_triage", ids[1], "initial", "ingress", "05-A2")
        saved = await finish(a2)
        assert a2["status"] == "completed", a2
        assert next(a for a in saved["alerts"] if a["id"] == str(ids[1]))["latest_triage_id"] is not None
        await scan("case_investigation", cid, "05a-A2-alone-does-not-trigger-Case", 0)
        ai_mode = "I2_empty"
        i2 = await scan("incident_diagnosis", iid, "06-I2", 1)
        saved = await finish(i2)
        assert i2["status"] == "failed" and i2["stage_receipts"][0]["state"] == "none"
        inputs = {a["run_id"]: a["content_json"] for a in saved["artifacts"] if a["kind"] == "input_snapshot"}
        assert digest(inputs[i1["run_id"]]["change_view"]) != digest(inputs[i2["run_id"]]["change_view"])
        assert inputs[i2["run_id"]]["triage_validation"][str(ids[1])]["usable"]
        result["checks"].append("actual_late_A2_changes_I_input_and_none_is_current")
        c2 = await scan("case_investigation", cid, "07-Case-R2", 1)
        saved = await finish(c2)
        result["round2"] = case_result(saved, c2, i2, "none", c1["run_id"])
        await unchanged_check(cid, "08-unchanged-R2")
        saved, hashes = await snapshot(cases, tenant)
        save(out / "database.json", saved)
        save(out / "database-hashes.json", hashes)
        assert not dispatcher.active and not dispatcher.receipts
        assert await redis.scard(dispatcher.queues.key("running")) == 0
        assert not any(a["local_state"] == "running" for a in saved["analysis_attempts"])
        result["checks"].append("all_local_attempts_ended_and_slots_released")
        result.update(await http_readback(sessions, cases, tenant, actor, records, saved, out, config))
        after_sources = sources(config)
        save(out / "source-after.json", after_sources)
        assert after_sources == frozen_sources
        result.update(state="passed_within_D4c_scope" if not result["uncovered"] else "finished_with_uncovered_branches",
            tasks=len(saved["analysis_tasks"]), runs=len(saved["runs"]),
            steps=len(saved["run_steps"]), artifacts=len(saved["artifacts"]), results=len(saved["results"]))
    except Exception as exc:
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        release.set()
        if dispatcher:
            for _, future in dispatcher.active.values():
                future.cancel()
            if dispatcher.active:
                await asyncio.gather(*(f for _, f in dispatcher.active.values()), return_exceptions=True)
            dispatcher._collect()
            await dispatcher._flush_receipts()
            result["final_slots"] = {"active": len(dispatcher.active), "receipts": len(dispatcher.receipts),
                "redis_running": await redis.scard(dispatcher.queues.key("running"))}
        result.update(real_model_calls=len(calls), injected_returns=sum("injection" in c for c in calls),
            reported_total_tokens=sum(c["real_response"].get("usage", {}).get("total_tokens", 0) for c in calls if "real_response" in c),
            usage_missing_calls=sum(not (c.get("real_response") or {}).get("usage") for c in calls))
        save(out / "result.json", result)
        save(out / "tasks.json", records)
        save(out / "snapshot.json", (await snapshot(cases, tenant))[0])
        await redis.aclose()
        await engine.dispose()
        await admin.dispose()


async def http_readback(sessions, cases, tenant, actor, records, saved, out, config):
    from app.socai2.baseline_store import digest
    from app.socai2.page_reader import PageReadService
    from app.socai2.run_records import RunRecordLimits
    from app.socai2.stage_delivery import validate_sources
    from app.socai2.stage_reader import StageReadService
    from httpx import ASGITransport, AsyncClient
    from investigation_http.adapters.analysis_tasks import AnalysisTaskBackend
    from investigation_http.adapters.identity import BusinessContext
    from investigation_http.adapters.run_records import RunRecordBackend
    from investigation_http.adapters.services import CaseBackend
    from investigation_http.dependencies import (
        analysis_service,
        analysis_task_service,
        case_service,
        page_service,
        run_record_service,
    )
    from investigation_http.main import app

    overrides, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    replies, directories, bodies, result_replies, details = [], {}, {}, {}, {}
    stored = {a["id"]: a for a in saved["artifacts"]}
    _, before = await snapshot(cases, tenant)
    try:
        page_size = config["directory_page_size"]
        app.state.business_context = BusinessContext(tenant, actor, "Operations analyst")
        app.dependency_overrides.update({case_service: lambda: CaseBackend(sessions),
            analysis_task_service: lambda: AnalysisTaskBackend(sessions),
            analysis_service: lambda: StageReadService(sessions), page_service: lambda: PageReadService(sessions),
            run_record_service: lambda: RunRecordBackend(sessions, limits=RunRecordLimits(page_size, page_size))})
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def get(path, **kwargs):
                response = await client.get(path, **kwargs)
                body = response.json()
                replies.append({"method": "GET", "path": str(response.request.url).removeprefix("http://isolated.local"),
                    "status": response.status_code, "body": body})
                save(out / "http.json", replies)
                assert response.status_code == 200, (path, response.status_code, body)
                return body

            async def pages(url):
                rows, seen, cursor = [], set(), None
                while True:
                    page = await get(url, params={"limit": page_size, **({"cursor": cursor} if cursor else {})})
                    rows.extend(page["items"])
                    cursor = page["next_cursor"]
                    if cursor is None:
                        assert len(rows) == page["total"]
                        return rows
                    assert cursor not in seen
                    seen.add(cursor)

            async def read_run(url, subject_type):
                detail = await get(url)
                rid = detail["run"]["id"]
                details[rid] = detail
                if rid in directories:
                    return detail
                source = detail if subject_type == "case" else await get(url + "/trace")
                steps = await pages(source["steps_url"])
                artifacts = await pages(source["artifacts_url"])
                assert {r["id"] for r in steps} == {r["id"] for r in saved["run_steps"] if r["run_id"] == rid}
                assert {r["id"] for r in artifacts} == {r["id"] for r in saved["artifacts"] if r["run_id"] == rid}
                directories[rid] = {"run_url": url, "steps": steps, "artifacts": artifacts}
                for row in artifacts:
                    content = await get(row["content_url"])
                    original = stored[row["id"]]
                    metadata = content.get("artifact", content.get("metadata"))
                    assert metadata["id"] == row["id"]
                    assert content["availability"] == "available"
                    assert content["content_json"] == original["content_json"]
                    assert content["content_text"] == original["content_text"]
                    if original["content_json"] is not None:
                        assert digest(content["content_json"]) == original["sha256"]
                    bodies[row["id"]] = content["content_json"]
                return detail

            for entry in records:
                base = f"/api/v1/socai2/{entry['subject_type']}s/{entry['subject_id']}"
                task = await get(base + f"/analysis-tasks/{entry['task_id']}")
                assert task["status"] == entry["status"]
                if entry.get("run_id"):
                    assert len(task["attempts"]) == 1
                    attempt = task["attempts"][0]
                    assert attempt["run_id"] == entry["run_id"] and attempt["attempt_no"] == 1
                    await read_run(attempt["run_url"], entry["subject_type"])
                else:
                    assert task["status"] == "skipped" and not task["attempts"]
                for link in task.get("results", []):
                    if link["result_type"] != "case_result":
                        continue  # A/I result is already read in its exact Run detail above.
                    reply = await get(link["url"])
                    final = next(r for r in saved["results"] if r["id"] == reply["result"]["id"])
                    for field in ("conclusion", "conclusion_state", "validation_state", "findings", "questions", "delivery_state"):
                        assert reply["result"][field] == final[field]
                    result_replies[final["id"]] = reply

            cross_run = []
            for rid, detail in list(details.items()):
                if detail["run"].get("case_id") is None:
                    continue
                manifest = bodies[detail["run"]["input_artifact_id"]]
                context_refs = [r for r in manifest["source_materials"] if r.get("id") in bodies
                    and (bodies[r["id"]] or {}).get("schema_version") == "socai2.baseline-context.v1"]
                assert len(context_refs) == 1
                frozen = bodies[context_refs[0]["id"]]
                for iid, item in frozen["incidents"].items():
                    material = item["analysis_material"]
                    assert material
                    source_run = material["source_run_id"]
                    # Source Run identity comes from C1, artifacts from its HTTP directory.
                    await read_run(f"/api/v1/socai2/incidents/{iid}/analysis/runs/{source_run}", "incident")
                    source_ids = {a["id"] for a in directories[source_run]["artifacts"]}
                    required = [material[k]["id"] for k in ("input", "response", "receipt_source")]
                    required += [a["id"] for a in material["originals"]]
                    assert set(required) <= source_ids
                    for aid in required:
                        assert bodies[aid] == stored[aid]["content_json"]
                    cross_run.append({"case_run_id": rid, "context_artifact_id": context_refs[0]["id"],
                                      "source_run_id": source_run, "source_artifact_ids": required})
                comparison = manifest["comparison_context"]
                if comparison["previous_run_id"]:
                    previous = comparison["previous_run_id"]
                    assert previous in details
                    if comparison["comparison_result_id"]:
                        assert comparison["comparison_result_id"] in result_replies
            for a in stored.values():
                if a["schema_version"] == "socai2.stage-delivery.v1":
                    validate_sources(bodies[a["id"]], bodies)
            _, after = await snapshot(cases, tenant)
            assert before == after
            receipt = {"http_gets": len(replies), "http_transport": "ASGITransport", "before": before, "after": after,
                "directories": {k: {"steps": len(v["steps"]), "artifacts": len(v["artifacts"])} for k, v in directories.items()},
                "cross_run": cross_run, "checks": ["all_directory_pages_content_equal_PG", "source_I_frozen_identity",
                    "all_strict_receipts_validate", "all_Result_values_equal", "HTTP_readonly"]}
            save(out / "http-validation.json", receipt)
            return {"http_gets": len(replies), "http_validation": "passed", "cross_run_sources": cross_run}
    finally:
        save(out / "http.json", replies)
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = context


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    environment(config)
    asyncio.run(main(config, args.output))
