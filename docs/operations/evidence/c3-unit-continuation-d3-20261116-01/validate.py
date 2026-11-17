"""D3 unique fresh Case: controlled replay of saved real answers, real PG/Redis and HTTP."""
import argparse
import asyncio
import hashlib
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / "services/api"), str(ROOT / "services/api/tests")]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=lambda v:
        v.model_dump(mode="json") if hasattr(v, "model_dump") else str(v)) + "\n")


def environment(config):
    for key in ("environment_file",):
        os.environ.update(json.loads(Path(config[key]).read_text()))
    os.environ.update(config["runtime_overrides"])
    for env, key in (("SOCAI2_INVESTIGATION_POLICY", "investigation_policy_file"),
                     ("SOCAI2_ANALYSIS_TASKS_CONFIG_FILE", "lifecycle_policy_file"),
                     ("SOCAI2_CASE_ALLOCATION_CONFIG_FILE", "allocation_policy_file")):
        os.environ[env] = config[key]
    os.environ.pop("SOCAI2_KNOWLEDGE_PROFILE", None)


async def main(config, out):
    from app.models import socai2 as m
    from app.socai2.analysis_case_executor import executors
    from app.socai2.analysis_dispatch_config import DispatchPolicy
    from app.socai2.analysis_dispatch_redis import AnalysisQueues
    from app.socai2.analysis_dispatch_store import DispatchRepository
    from app.socai2.analysis_dispatcher import AnalysisDispatcher
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.baseline_contracts import Actor
    from app.socai2.baseline_store import F, digest
    from app.socai2.case_contracts import CaseCreate
    from app.socai2.case_service import CaseService
    from redis.asyncio import Redis
    from sqlalchemy import insert, null, select, text, update
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from test_socai2_case_initial_http_pg import snapshot

    out.mkdir(exist_ok=False)
    source_files = [Path(__file__), *sorted((ROOT / "services/api/app/socai2").glob("*.py")),
                    ROOT / "services/api/app/socai2/case-input-v1.json", Path(config["investigation_policy_file"])]
    save(out / "source-manifest.json", {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in source_files})
    (out / "validate-source.py").write_text(Path(__file__).read_text())
    cfg = json.loads(Path(config["database_profile"]).read_text())
    assert cfg["host"] == "127.0.0.1" and cfg["processing_database"] == "v12_upgrade_dev"
    url = URL.create("postgresql+psycopg", username=cfg["admin"], password=Path(cfg["password_file"]).read_text().strip(),
        host=cfg["host"], port=cfg["port"], database=cfg["processing_database"])
    admin = create_async_engine(url, hide_parameters=True, connect_args={"sslmode": config["sslmode"]})
    engine = create_async_engine(url, hide_parameters=True, connect_args={"sslmode": config["sslmode"], "options": "-c role="+cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cases, tasks = CaseService(sessions), AnalysisTaskService(sessions, AnalysisTaskPolicy.load())
    tenant, actor = uuid4(), uuid4()
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())
    source_path = Path(config["source_snapshot_file"])
    source = json.loads(source_path.read_text())
    result = {"state": "running", "tenant_id": tenant, "actor_id": actor, "database": cfg["processing_database"],
        "database_host": cfg["host"], "database_port": cfg["port"], "substitute_model_calls": 0, "deployment": False,
        "checks": [], "source_snapshot": str(source_path.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "source_content_digest": digest(json.loads(source_path.read_text()))}
    calls, dispatcher = [], None
    save(out / "intent.json", {**result, "input": "D2 real-run source materials copied to new isolated identities; controlled response replay",
        "real_model_calls": 0, "planned_controlled_responses": 3,
        "policy_file": config["investigation_policy_file"]})

    mother_calls = json.loads(Path(config["mother_calls_file"]).read_text())
    mother_requests = [a["content_json"]["payload"] for a in source["artifacts"] if a["kind"] == "model_request"]
    identity_map = {}

    def adapt_answer(call, request):
        old = next(r for r in mother_requests if r["body"] == call["request"])
        old_boundary, new_boundary = old["case_boundary"], request["case_boundary"]
        members = {alias: new_boundary["member_aliases"][identity_map[aid]]
                   for aid, alias in old_boundary["member_aliases"].items()}
        objects = {alias: new_boundary["object_aliases"][key] for key, alias in old_boundary["object_aliases"].items()
                   if key in new_boundary["object_aliases"]}
        def key(source, mapped):
            ref = source["ref"]
            owners = sorted(identity_map.get(a, a) if mapped else a for a in source["alert_ids"])
            path = ref.get("source_path")
            if path and mapped:
                for before, after in identity_map.items():
                    path = path.replace(before, after)
            return ref["type"], ref["role"], tuple(owners), path
        index = {}
        for sid, value in request["source_map"].items():
            index.setdefault(key(value, False), []).append(sid)
        refs, unresolved = {}, []
        for sid, value in old["source_map"].items():
            matches = index.get(key(value, True), [])
            if len(matches) == 1:
                refs[sid] = matches[0]
            else:
                # A source absent from this partial run cannot become evidence.
                refs[sid] = "unavailable_d2_source_" + sid
                unresolved.append(sid)
        def walk(value):
            if isinstance(value, list):
                return [walk(v) for v in value]
            if not isinstance(value, dict):
                return value  # Prose is never rewritten.
            return {k: [refs.get(v, "unavailable_d2_source_" + v) for v in child]
                    if k in {"evidence_ids", "support_ids", "counter_ids", "source_ids"}
                    else [members[v] for v in child] if k == "alert_ids"
                    else members[child] if k == "alert_id"
                    else [objects[v] for v in child] if k == "object_keys" else walk(child)
                    for k, child in value.items()}
        answer = walk(json.loads(call["response"]["choices"][0]["message"]["content"]))
        return answer, {"member_aliases": members, "object_aliases": objects,
            "source_ids": refs, "unavailable_sources": unresolved,
            "rule": "exact source type/role/mapped owners/field path; prose unchanged; unavailable sources stay unavailable"}

    class RecordingGateway:
        provider, model, schema_profile = "chat_completions", "controlled-real-D2-replay", "vllm_grammar_v1"
        async def configure(self, *_):
            return True
        async def measure(self, body, stage):
            from socai2_test_model_view import synthetic_measure
            return await synthetic_measure(body, stage)
        async def complete(self, body, timeout):
            async with cases.transaction(tenant, readonly=True) as store:
                request = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
                    F.c.run_id == self.run_id, F.c.kind == "model_request"))
                    .order_by(F.c.captured_at.desc()).limit(1))).scalar_one()["payload"]
            assert request["body"] == body and timeout > 0
            stage = request["case_boundary"].get("stage", "C3")
            call = {"stage": stage, "request": body, "state": "started", "controlled_replay": True}
            calls.append(call)
            save(out / "calls.json", calls)
            if stage == "C3" and len(calls) == 1:
                mother = next(c for c in mother_calls if c["stage"] == "C3")
                answer, mapping = adapt_answer(mother, request)
                assert all(s in request["source_map"] for s in answer["findings"][0]["support_ids"])
                complete = json.dumps(answer, ensure_ascii=False)
                second = json.dumps(answer["findings"][1], ensure_ascii=False)
                cut = complete.index(second) + len(second) // 2
                content, finish = complete[:cut], "length"
                call.update(complete_derived_answer=complete, cut_offset=cut, mapping=mapping,
                    mother_content_sha256=hashlib.sha256(mother["response"]["choices"][0]["message"]["content"].encode()).hexdigest())
            elif stage == "C3" and len(calls) == 2:
                assert request["section_completion"]["attempt"] == 1
                content, finish = config["substitute_supplement_content"], "stop"
                call["failure_injection"] = "whitespace_supplement"
            else:
                assert stage == "C6" and len(calls) == 3
                prior = next(r for r in request["followup_boundary"]["records"] if r["block"] == "C3")
                assert [f["id"] for f in prior["value"]["findings"]] == ["F1"]
                assert "followups" not in prior["value"] and "questions" not in prior["value"]
                assert prior["ref"]["role"] == "prior_analysis"
                assert "C3仅完成已列出的部分" in body["messages"][1]["content"]
                mother = next(c for c in mother_calls if c["stage"] == "C6")
                answer, mapping = adapt_answer(mother, request)
                content, finish = json.dumps(answer, ensure_ascii=False), "stop"
                call.update(mapping=mapping, actual_C6_prior=prior,
                    mother_content_sha256=hashlib.sha256(mother["response"]["choices"][0]["message"]["content"].encode()).hexdigest())
            response = {"choices": [{"finish_reason": finish, "message": {"content": content}}],
                "usage": {"prompt_tokens": 200, "completion_tokens": 200, "total_tokens": 400}}
            call.update(state="responded", response=response, usage_kind="explicit_test_substitute")
            save(out / "calls.json", calls)
            print("controlled replay returned:", stage, finish, flush=True)
            return response

    try:
        async with admin.begin() as db:
            await db.execute(text("""INSERT INTO public.tenants(id,name,slug,plan,is_active,settings,limits,created_at,updated_at)
                VALUES(:id,'D3 unit continuation verification',:slug,'enterprise',true,'{}','{}',now(),now())"""),
                {"id": tenant, "slug": "d3-units-"+str(tenant)})
            await db.execute(text("""INSERT INTO public.users(id,tenant_id,email,username,hashed_password,role,is_active,is_verified,preferences,created_at,updated_at)
                VALUES(:id,:tenant,:email,'D3 unit continuation verification','!','soc_analyst',true,false,'{}',now(),now())"""),
                {"id": actor, "tenant": tenant, "email": str(actor)+"@example.invalid"})
        gateway = RecordingGateway()
        assert await gateway.configure(cases, tenant)
        result["model_route"] = {"model": gateway.model, "protocol": gateway.provider,
            "schema_profile": gateway.schema_profile, "real_model_calls": 0,
            "test_kind": "controlled replay of D2 real response; no new generation"}
        ids, mapping = [], []
        for old in source["alerts"]:
            aid, mid = uuid4(), uuid4()
            material = next(v for v in source["alert_materials"] if v["id"] == old["latest_material_id"])
            async with cases.transaction(tenant) as store:
                values = {k: old[k] for k in ("title", "description", "source_namespace", "original_vendor",
                    "category", "severity", "severity_raw", "event_time_source", "tags")}
                values["event_time"] = datetime.fromisoformat(old["event_time"]) if old["event_time"] else None
                await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=tenant, source_identity_key=str(aid), **values))
                values = {k: material[k] for k in ("raw_text", "raw_json", "ocsf_json", "detection", "enrichment",
                    "source_scope", "material_state", "sha256", "retention")}
                await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=tenant, alert_id=aid, revision=1, **values))
                await store.db.execute(update(m.Alerts).where(m.Alerts.id == aid).values(latest_material_id=mid))
                for obj in source["alert_objects"]:
                    if obj["alert_id"] == old["id"]:
                        values = {k: obj[k] for k in ("object_key", "object_type", "source_type", "object_role", "namespace",
                            "raw_value", "normalized_value", "source_path", "attributes", "asset_match_state", "asset_ref", "match_basis")}
                        # A database NULL exported to JSON is not the JSONB null literal.
                        for key in ("asset_ref", "match_basis"):
                            if values[key] is None:
                                values[key] = null()
                        await store.db.execute(insert(m.AlertObjects).values(id=uuid4(), tenant_id=tenant,
                            alert_id=aid, material_id=mid, **values))
            ids.append(aid)
            identity_map[str(old["id"])] = str(aid)
            identity_map[str(material["id"])] = str(mid)
            mapping.append({"source_alert_id": old["id"], "alert_id": aid, "source_material_id": material["id"], "material_id": mid})
        save(out / "source-mapping.json", mapping)
        created = await cases.create_case(tenant, CaseCreate(operation_key=uuid4(), title="登录、进程与外联活动调查",
            alert_ids=ids), actor=Actor(user_id=actor, name="D3 unit continuation verification"))
        cid, tid = created.primary_case_id, created.allocations[0].initial_task.task_id
        result.update(case_id=cid, task_id=tid, alert_ids=ids)
        save(out / "created.json", created)
        admission, _ = await snapshot(cases, tenant)
        assert not admission["runs"] and not admission["analysis_attempts"]
        handlers = executors({k: config[k] for k in ("investigation_policy_file", "incident", "case")}, tasks)
        def factory(claim):
            gateway.run_id = claim.run_id
            return gateway
        handlers["case_investigation"].gateway_factory = factory
        handlers["case_investigation"].lake_factory = lambda _: SimpleNamespace(configured=lambda: False)
        policy = DispatchPolicy(**config["dispatch"])
        dispatcher = AnalysisDispatcher(DispatchRepository(tasks, tenant), AnalysisQueues(redis, policy.namespace, tenant), policy, handlers)
        await dispatcher.start()
        async with asyncio.timeout(config["check_timeout_seconds"]):
            while True:
                await dispatcher.tick()
                current = await tasks.read_task(tenant, "case", cid, tid)
                if current["status"] not in {"accepted", "running"}:
                    break
                await asyncio.sleep(config["check_interval_seconds"])
        save(out / "task.json", current)
        saved, _ = await snapshot(cases, tenant)
        save(out / "database.json", saved)
        assert len(saved["runs"]) == len(saved["analysis_attempts"]) == len(saved["results"]) == 1
        run, attempt, stored = saved["runs"][0], saved["analysis_attempts"][0], saved["results"][0]
        result.update(run_id=run["id"], result_id=stored["id"], task_status=current["status"])
        assert run["state"] == "completed" and attempt["local_state"] == "ended" and attempt["outcome"] == "completed"
        assert [c["stage"] for c in calls] == ["C3", "C3", "C6"]
        artifacts = {str(a["id"]): a for a in saved["artifacts"]}
        stage_receipts = [a for a in artifacts.values() if a["schema_version"] == "socai2.stage-delivery.v1"]
        assert len(stage_receipts) == 1
        delivery = stage_receipts[0]["content_json"]
        from app.socai2.stage_delivery import validate_sources
        validate_sources(delivery, {aid: a["content_json"] for aid, a in artifacts.items()})
        assert delivery["delivery"]["state"] == "partial"
        assert [u["path"] for u in delivery["retained_units"]] == ["$.summary", *[f"$.members[{i}]" for i in range(4)], "$.findings[0]"]
        assert delivery["use"]["dispatch_paths"] == [] and len(delivery["originals"]) == 4
        c3 = next(a["content_json"] for a in artifacts.values() if (a["content_json"] or {}).get("stage") == "C3_initial")
        assert c3["state"] == "completed" and "followups" not in c3["analysis"]
        assert [f["id"] for f in c3["analysis"]["findings"]] == ["F1"]
        assert c3["basis"]["section_completion"]["attempts"] == 1
        routing = next(a["content_json"] for a in artifacts.values() if (a["content_json"] or {}).get("type") == "followup_dispatch")
        assert routing["routes"] == []
        final = json.loads(calls[-1]["response"]["choices"][0]["message"]["content"])
        assert stored["conclusion"] == final["conclusion"]["text"] and stored["conclusion_state"] == final["conclusion"]["state"]
        assert stored["validation_state"] == "accepted" and stored["conclusion_origin"] == "model"
        assert all("tenant_uid" not in json.dumps(c["request"]["messages"]) for c in calls)
        result["checks"] += ["one_current_task_one_attempt", "C3_length_closed_F1_retained", "blank_supplement_does_not_erase_initial",
            "one_supplement_only", "actual_C6_receives_F1_without_F2_or_invented_followups", "zero_C4_dispatch",
            "saved_original_hashes_spans_exact", "C6_conclusion_retained", "model_inputs_exclude_tenant_uid"]
        await http_readback(sessions, cases, tenant, actor, result, saved, out, config)
        assert not dispatcher.active and not dispatcher.receipts and await redis.scard(dispatcher.queues.key("running")) == 0
        result["checks"].append("slot_released")
        result.update(state="passed", prose_quality="not_checked", stage_delivery_artifact_id=stage_receipts[0]["id"])
    except Exception as exc:
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        if dispatcher:
            for _, future in dispatcher.active.values():
                future.cancel()
            if dispatcher.active:
                await asyncio.gather(*(f for _, f in dispatcher.active.values()), return_exceptions=True)
            dispatcher._collect()
            await dispatcher._flush_receipts()
        save(out / "calls.json", calls)
        result["real_model_calls"] = 0
        result["substitute_model_calls"] = len(calls)
        save(out / "result.json", result)
        save(out / "snapshot.json", (await snapshot(cases, tenant))[0])
        await redis.aclose()
        await engine.dispose()
        await admin.dispose()


async def http_readback(sessions, cases, tenant, actor, result, saved, out, config):
    from app.socai2.run_records import RunRecordLimits
    from httpx import ASGITransport, AsyncClient
    from investigation_http.adapters.analysis_tasks import AnalysisTaskBackend
    from investigation_http.adapters.identity import BusinessContext
    from investigation_http.adapters.run_records import RunRecordBackend
    from investigation_http.adapters.services import CaseBackend
    from investigation_http.dependencies import (
        analysis_task_service,
        case_service,
        run_record_service,
    )
    from investigation_http.main import app
    from test_socai2_case_initial_http_pg import snapshot

    overrides, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    replies = []
    try:
        _, before = await snapshot(cases, tenant)
        app.state.business_context = BusinessContext(tenant, actor, "D3 directory HTTP readback")
        page_size = config["directory_page_size"]
        app.dependency_overrides.update({case_service: lambda: CaseBackend(sessions),
            analysis_task_service: lambda: AnalysisTaskBackend(sessions),
            run_record_service: lambda: RunRecordBackend(sessions, limits=RunRecordLimits(page_size, page_size))})
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def get(path, **kwargs):
                response = await client.get(path, **kwargs)
                body = response.json()
                replies.append({"method": "GET", "path": str(response.request.url).removeprefix("http://isolated.local"),
                    "status": response.status_code, "body": body})
                assert response.status_code == 200, (path, response.status_code, body)
                return body
            cid, tid = result["case_id"], result["task_id"]
            task = await get(f"/api/v1/socai2/cases/{cid}/analysis-tasks/{tid}")
            assert task["status"] == "completed" and len(task["attempts"]) == 1
            detail = await get(task["attempts"][0]["run_url"])
            assert detail["run"]["state"] == "completed"
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
            steps = await pages(detail["steps_url"])
            directory = await pages(detail["artifacts_url"])
            assert {s["id"] for s in steps} == {str(s["id"]) for s in saved["run_steps"]}
            assert {a["id"] for a in directory} == {str(a["id"]) for a in saved["artifacts"]}
            stored = {str(a["id"]): a for a in saved["artifacts"]}
            discovered, bodies = [], {}
            for row in directory:
                content = await get(row["content_url"])
                assert content["content_json"] == stored[row["id"]]["content_json"]
                assert content["content_text"] == stored[row["id"]]["content_text"]
                bodies[row["id"]] = content["content_json"]
                if row["schema_version"] == "socai2.stage-delivery.v1":
                    discovered.append(row)
            assert len(discovered) == 1
            receipt = bodies[discovered[0]["id"]]
            from app.socai2.stage_delivery import validate_sources
            validate_sources(receipt, bodies)
            assert receipt["delivery"]["state"] == "partial" and len(receipt["originals"]) == 4
            value = await get(task["results"][0]["url"])
            final = saved["results"][0]
            for field in ("conclusion", "conclusion_state", "validation_state", "findings", "questions", "delivery_state"):
                assert value["result"][field] == final[field]
            report = stored[str(final["report_artifact_id"])]["content_json"]
            assert value["delivery"]["detail"]["citation_review"] == report["citation_review"]
        _, after = await snapshot(cases, tenant)
        assert before == after
        result.update(http_gets=len(replies), before_http=before, after_http=after,
            directory_discovered_stage_delivery=discovered, http_transport="ASGITransport",
            discovered_steps=len(steps), discovered_artifacts=len(directory))
        result["checks"] += ["HTTP_full_paginated_directories_discover_new_receipt_and_originals",
            "HTTP_values_equal_saved_content", "HTTP_read_does_not_write"]
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
    configuration = json.loads(args.config.read_text())
    environment(configuration)
    asyncio.run(main(configuration, args.output))
