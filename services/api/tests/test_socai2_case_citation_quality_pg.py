"""One isolated C3→Deep→C6 save/read/adoption batch with model substitutes."""
import copy
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2.baseline_context import reference
from app.socai2.baseline_dispatch import dispatch_followups
from app.socai2.baseline_enrichment import S
from app.socai2.baseline_executor import SCHEMA, BaselineExecutor
from app.socai2.baseline_store import F, digest
from app.socai2.case_citation_quality import VALIDATION
from app.socai2.case_service import CaseService
from app.socai2.citation_quality import NOTE
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from investigation_http.external_routes import cases
from socai2_test_model_view import synthetic_measure
from sqlalchemy import insert, select, text, update
from test_socai2_case_boundary_pg import USER, T
from test_socai2_case_boundary_pg import run_checks as seeded_case
from test_socai2_case_citation_quality import faulty_analysis
from test_socai2_case_followup_boundary import final_answer
from test_socai2_case_model_boundary import answer_for


class RetainedGateway:
    provider, model = "synthetic", "synthetic-case-retention-no-network"

    def __init__(self, service, cid, rid, save):
        self.service, self.cid, self.rid, self.save = service, cid, rid, save
        self.calls, self.requests, self.responses = [], [], []

    async def configure(self, *_):
        return True

    async def measure(self, body, stage):
        return await synthetic_measure(body, stage)

    async def complete(self, body, timeout):
        assert timeout > 0
        async with self.service.transaction(T, readonly=True) as store:
            request = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
                F.c.run_id == self.rid, F.c.kind == "model_request"))
                .order_by(F.c.captured_at.desc()).limit(1))).scalar_one()["payload"]
            context = await store.read_context(self.cid, self.rid)
        assert request["body"] == body
        stage = request["case_boundary"].get("stage", "C3")
        assert stage not in self.calls, "No correction, supplementation or retry belongs to this batch"
        self.calls.append(stage)
        if stage == "C3":
            answer = faulty_analysis(answer_for(request, context), request)
            answer["followups"] = [{"question_id": context.questions[0].id,
                "alert_ids": [m["alert_id"] for m in answer["members"]], "mode": "deep",
                "objective": "原后续分析需求。", "required_evidence": "原待查依据。", "source_ids": ["missing-reference"],
                "object_keys": [], "binding_id": None, "priority": "decision_critical"}]
        elif stage == "Deep":
            assert NOTE in body["messages"][1]["content"] and "原问题回答" in body["messages"][1]["content"]
            answer = {"action": "answer", "binding_id": None, "reason": "原 Deep 完成理由。",
                "answer": {"state": "supported", "text": "  原 Deep 回答。\n", "support_ids": [],
                    "counter_ids": ["missing-reference"] * 2, "alternatives": ["原替代解释。"], "limitations": []}}
        else:
            assert stage == "C6"
            assert NOTE in body["messages"][1]["content"] and "原 Deep 回答" in body["messages"][1]["content"]
            comparison = request["followup_boundary"]["program_metadata"]["comparison"]
            answer = final_answer(request, context, comparison)
            faulty_analysis(answer["analysis"], request)
            answer["conclusion"].update(text="  原 Case 最终结论保留。\n", state="supported", support_ids=[])
            answer["impact"].update(summary="原 Case 影响分析。", supported_changes=["原影响判定。"],
                                    alert_ids=answer["conclusion"]["alert_ids"], support_ids=[])
            answer["recommendations"][0].update(reason="原最终建议。", source_ids=[])
        reply = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(answer, ensure_ascii=False)}}],
            "usage": {"prompt_tokens": 200, "completion_tokens": 200, "total_tokens": 400}}
        self.requests.append(copy.deepcopy(request))
        self.responses.append(copy.deepcopy(reply))
        self.save("substitute-calls.json", {"stages": self.calls, "requests": self.requests, "responses": self.responses})
        return reply


async def snapshot(service, sample):
    cid, aids, iid = sample["case_id"], sample["alert_ids"], sample["incident_id"]
    rids = [sample["run_id"], *sample["stage_run_ids"]]
    tables = [(m.Cases, m.Cases.id == cid), (m.Alerts, m.Alerts.id.in_(aids)),
        (m.AlertMaterials, m.AlertMaterials.alert_id.in_(aids)), (m.AlertObjects, m.AlertObjects.alert_id.in_(aids)),
        (m.AlertAssessments, m.AlertAssessments.source_run_id.in_(rids)),
        (m.Incidents, m.Incidents.id == iid), (m.IncidentAlerts, m.IncidentAlerts.incident_id == iid),
        (m.IncidentDiagnoses, m.IncidentDiagnoses.source_run_id.in_(rids)),
        (m.CaseAlerts, m.CaseAlerts.case_id == cid), (m.Runs, m.Runs.id.in_(rids)),
        (m.RunMembers, m.RunMembers.run_id.in_(rids)), (m.RunSteps, m.RunSteps.run_id.in_(rids)),
        (m.Artifacts, m.Artifacts.run_id.in_(rids)), (m.Results, m.Results.case_id == cid),
        (m.ResultMembers, m.ResultMembers.case_id == cid), (m.CaseAssessments, m.CaseAssessments.case_id == cid),
        (m.CaseAssessmentSources, m.CaseAssessmentSources.case_id == cid),
        (m.CaseAssessmentMembers, m.CaseAssessmentMembers.case_id == cid),
        (m.Activities, m.Activities.subject_case_id == cid), (m.ActivityTargets, m.ActivityTargets.case_id == cid)]
    data = {}
    async with service.transaction(T, readonly=True) as store:
        for model, where in tables:
            table = model.__table__
            data[table.name] = [dict(r) for r in (await store.db.execute(select(table).where(
                *store.where(table, where)).order_by(table.c.id))).mappings()]
    return json.loads(json.dumps(data, default=str))


async def run_checks(engine, config, output):
    def save(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")
    records = []
    def record(name, passed, detail):
        records.append({"name": name, "passed": passed, "detail": detail})
        save("execution.json", records)
    save("intent.json", {"batch": config["batch"], "planned_substitute_model_calls": config["planned_substitute_model_calls"],
        "readback_from": config.get("readback_from"),
        "fixture_calls": "2 A + 1 I", "case_calls": "1 C3 + 1 Deep + 1 C6", "real_model_calls": 0,
        "external_source_calls": 0, "query_receipts": "background empty-query substitutes", "no_retry": True})

    async def scenario(service, sample):
        cid, rid = sample["case_id"], sample["run_id"]
        gateway = RetainedGateway(service, cid, rid, save)
        lake = SimpleNamespace(configured=lambda: True)
        initial = await service.analyze(T, cid, rid, gateway=gateway, lake=lake)
        record("C3", initial["state"] == "completed", initial)
        assert initial["validation"] == VALIDATION and initial["basis"]["citation_review"]["state"] == "issues_recorded"
        routes = await dispatch_followups(service, T, cid, rid, initial["analysis"]["followups"],
            initial["basis"]["binding_map"], gateway=gateway, lake=lake)
        record("Deep", True, routes)
        assert routes[0]["answer_available"] and routes[0]["state"] == "completed", routes
        graph = await service.build_graph(T, cid, rid)
        executor = BaselineExecutor(service, T, gateway=gateway, lake=lake)
        async with service.transaction(T) as store:
            run = await store.run(cid, rid)
            c3 = await store.one(select(S).where(*store.where(S, S.c.run_id == rid,
                S.c.stage_code == "C3", S.c.kind == "stage")))
            await executor.record(store, run, "C4.routing", {"schema_version": SCHEMA, "type": "followup_dispatch",
                "run_id": str(rid), "initial_analysis_artifact_id": str(c3["output_artifact_id"]),
                "initial_state": initial["state"], "routes": routes, "graph_artifact_id": graph["graph_artifact_id"],
                "limitations": ["Synthetic citation retention acceptance only."]},
                [reference("artifact", c3["output_artifact_id"], "execution_receipt")])
        out = await service.finalize(T, cid, rid, gateway=gateway)
        record("C6", out["state"] == "completed", out)
        assert out["state"] == "completed" and gateway.calls == ["C3", "Deep", "C6"], out
        # Replay only finished API operations; no Run redispatch.
        assert out == await service.finalize(T, cid, rid, gateway=gateway)
        assert initial == await service.analyze(T, cid, rid, gateway=gateway, lake=lake)
        return await verify(service, sample, initial, out, gateway)

    async def verify(service, sample, initial, out, gateway):
        cid, rid = sample["case_id"], sample["run_id"]
        data = await snapshot(service, sample)
        save("database.json", data)
        artifacts = {a["id"]: a for a in data["artifacts"]}
        case_artifacts = [a for a in data["artifacts"] if a["run_id"] == str(rid)]
        responses = sorted([a for a in case_artifacts if a["kind"] == "model_response"], key=lambda a: a["captured_at"])
        assert len(responses) == 3
        for response, raw in zip(responses, gateway.responses):
            payload = response["content_json"]["payload"]
            quality = payload["citation_review"]
            original = artifacts[quality["original_response_artifact_id"]]
            assert original["content_json"]["raw"] == payload["raw"] == raw
            assert original["captured_at"] <= response["captured_at"]
            assert artifacts[quality["request_artifact_id"]]["kind"] == "model_request"
            assert quality["state"] == "issues_recorded" and quality["prose_quality"] == "not_checked"
            assert quality["conclusion_modified"] is False
            assert quality["original_sha256"] == digest(raw["choices"][0]["message"]["content"])
            assert quality["derived_sha256"] == digest(payload["derived"])
            assert payload["validation_error"] is None and not payload.get("validation_review") and not payload.get("correction_feedback")
        assert responses[0]["content_json"]["payload"]["derived"] == initial["analysis"]
        deep_summary = next(a["content_json"] for a in case_artifacts if a["content_json"]
            and a["content_json"].get("type") == "deep_summary")
        assert deep_summary["answer"] == responses[1]["content_json"]["payload"]["derived"]["answer"]
        assert deep_summary["answer"]["state"] == "supported" and deep_summary["answer"]["text"] == "  原 Deep 回答。\n"
        detail = artifacts[out["detail_artifact_id"]]["content_json"]
        report = artifacts[out["report_artifact_id"]]["content_json"]
        result = data["results"][0]
        final_raw = json.loads(gateway.responses[-1]["choices"][0]["message"]["content"])
        assert result["validation_state"] == "accepted" and result["conclusion_state"] == "supported"
        assert report["conclusion"] == result["conclusion"] == detail["delivery"]["conclusion"]["text"] == final_raw["conclusion"]["text"]
        assert detail["delivery"] == responses[-1]["content_json"]["payload"]["derived"]
        assert report["citation_review"] == detail["citation_review"] == responses[-1]["content_json"]["payload"]["citation_review"]
        for key in ("findings", "questions", "recommendations", "case_impact"):
            assert report[key] == result[key] == detail["result"][key]
        assert result["findings"][0]["statement"] == final_raw["analysis"]["findings"][0]["statement"]
        assert result["findings"][1]["state"] == "observed" and result["findings"][1]["support"] == []
        assert result["recommendations"][0]["reason"] == final_raw["recommendations"][0]["reason"]
        assert all(r["conclusion_covered"] and r["assessment_state"] == "analyzed" for r in data["result_members"])
        assert any(not r["evidence_refs"] for r in data["result_members"])
        assert data["cases"][0]["current_assessment_id"] == data["case_assessments"][0]["id"]
        assert data["case_assessments"][0]["conclusion"] == result["conclusion"]
        markdown = artifacts[out["markdown_artifact_id"]]["content_text"]
        assert final_raw["conclusion"]["text"] in markdown and "引用质量记录" in markdown

        app, reader = FastAPI(), CaseService(service.sessions)
        app.include_router(cases.router, prefix="/api/v1")
        app.dependency_overrides[cases.get_service] = lambda: reader
        user = SimpleNamespace(tenant_id=T, user_id=USER, email="Synthetic reviewer", workload_service=None)
        for param in (cases.ReadUser, cases.WriteUser):
            app.dependency_overrides[param.__metadata__[0].dependency] = lambda: user
        base = f"/api/v1/socai2/cases/{cid}"
        result_path = base + f"/results/{result['id']}"
        replies = []
        async with AsyncClient(transport=ASGITransport(app=app), base_url=config["http_base_url"]) as client:
            async def request(method, path, *, expected=200, body=None):
                reply = await client.request(method, path, **({"json": body} if body is not None else {}))
                replies.append({"method": method, "path": path, "status": reply.status_code, "body": reply.json()})
                save("api-responses.json", replies)
                assert reply.status_code == expected, replies[-1]
                return reply.json()
            for path in (base, base + f"/runs/{rid}", result_path, base + "/assessments"):
                body = await request("GET", path)
                if path == base:
                    assert body["current_assessment"]["value"]["conclusion"] == result["conclusion"]
                elif path == base + f"/runs/{rid}":
                    assert body["run"]["state"] == "completed" and body["result_ids"] == [result["id"]]
                elif path == result_path:
                    assert body["result"]["conclusion"] == result["conclusion"]
                else:
                    assert body["items"][0]["conclusion"] == result["conclusion"]
            for row in case_artifacts:
                body = await request("GET", base + f"/runs/{rid}/artifacts/{row['id']}")
                assert body["content_json"] == row["content_json"] and body["content_text"] == row["content_text"]
            after_get = await snapshot(service, sample)
            assert after_get == data and gateway.calls == ["C3", "Deep", "C6"]
            preview = await request("GET", result_path + "/adoption-preview")
            assert preview["can_adopt"] and not preview["uncovered_alert_ids"] and preview["input_freshness"]["state"] == "current"
            adopt_body = {"operation_key": str(uuid4()), "expected_review_token": preview["review_token"],
                "reason": "隔离批次直接验证：引用问题独立，原结论可采用。", "acknowledge_pending_work": False}
            adopted = await request("POST", result_path + "/adopt", body=adopt_body)
            assert adopted["previous_assessment_id"] == data["case_assessments"][0]["id"]
            assert adopted == await request("POST", result_path + "/adopt", body=adopt_body)
            changed = await request("POST", result_path + "/adopt", expected=409,
                body={**adopt_body, "operation_key": str(uuid4())})
            assert changed["detail"] == "result_adoption_preview_changed"
            history = await request("GET", base + "/assessments")
            assert history["total"] == 2 and all(a["conclusion"] == result["conclusion"] for a in history["items"])
            # An automatic replay cannot overwrite the newer manual selection.
            async with service.transaction(T) as store:
                auto = (await store.db.execute(text("SELECT socai2.auto_adopt_baseline_result(:tenant,:result)"),
                    {"tenant": T, "result": UUID(result["id"])})).scalar_one()
                assert auto["state"] == "already_adopted"
                assert (await store.case(cid))["current_assessment_id"] == UUID(adopted["assessment_id"])
            save("database-after-adoption.json", await snapshot(service, sample))
            # A new material revision makes this saved result stale; retain all old rows.
            aid, new_material = sample["alert_ids"][0], uuid4()
            old = next(row for row in data["alert_materials"] if row["alert_id"] == str(aid))
            async with service.transaction(T) as store:
                await store.db.execute(insert(m.AlertMaterials).values(id=new_material, tenant_id=T, alert_id=aid,
                    revision=2, raw_text="Synthetic newer observation for freshness guard.", raw_json={"process": {"pid": 43}},
                    detection={}, source_scope={}, retention={}, material_state="complete"))
                await store.db.execute(update(m.Alerts).where(m.Alerts.id == aid, m.Alerts.tenant_id == T)
                                       .values(latest_material_id=new_material))
            stale = await request("GET", result_path + "/adoption-preview")
            assert not stale["can_adopt"] and "result_input_not_current" in stale["refusal_reasons"]
            refused = await request("POST", result_path + "/adopt", expected=409, body={**adopt_body,
                "operation_key": str(uuid4()), "expected_review_token": stale["review_token"]})
            assert refused["detail"] == "result_input_not_current"
            assert await request("GET", base + "/assessments") == history
            final_data = await snapshot(service, sample)
            assert final_data["artifacts"] == data["artifacts"] and final_data["results"] == data["results"]
            assert next(r for r in final_data["alert_materials"] if r["id"] == old["id"]) == old
            save("database-after-freshness.json", final_data)
        checks = {"originals_diagnostics_and_derived_saved": True, "raw_and_derived_hashes_match": True,
            "C3_Deep_C6_original_prose_and_states_retained": True, "downstream_prior_role_and_quality_note": True,
            "report_Result_database_HTTP_agree": True, "automatic_and_manual_adoption": True,
            "review_token_and_new_material_freshness_guards": True, "manual_pointer_survives_auto_replay": True,
            "GET_did_not_write_or_dispatch": True, "case_substitute_model_calls": 3, "fixture_substitute_model_calls": 3,
            "new_model_calls_in_this_attempt": config["planned_substitute_model_calls"],
            "real_model_calls": 0, "external_source_calls": 0,
            "http_gets": sum(r["method"] == "GET" for r in replies), "http_posts": sum(r["method"] == "POST" for r in replies)}
        save("checks.json", checks)
        names = ["database.json", "database-after-adoption.json", "database-after-freshness.json", "checks.json",
                 "api-responses.json", "intent.json", "execution.json", "substitute-calls.json"]
        save("manifest.json", {"schema_version": "socai2.page-export.v1", "batch_id": config["batch"],
            "tenant_id": str(T), "case_id": str(cid), "exported_at": datetime.now(UTC).isoformat(),
            "source_environment": "isolated_pg_with_model_and_background_query_substitutes",
            "database": config["expected_database"], "input_kind": "synthetic", "real_model_calls": 0,
            "sources": [{"file": name, "sha256": hashlib.sha256((output / name).read_bytes()).hexdigest()} for name in names]})
        return checks

    if config.get("readback_from"):
        # Continue checking an already-completed batch; never redispatch its model/tool steps.
        from sqlalchemy.ext.asyncio import async_sessionmaker
        source = Path(config["readback_from"])
        old = json.loads((source / "execution.json").read_text())
        saved = json.loads((source / "substitute-calls.json").read_text())
        sample = next(r["detail"] for r in old if r["name"] == "fixture_registered")
        sample = {k: [UUID(v) for v in value] if isinstance(value, list) else UUID(value) for k, value in sample.items()}
        initial = next(r["detail"] for r in old if r["name"] == "C3")
        out = next(r["detail"] for r in old if r["name"] == "C6")
        assert out["state"] == "completed" and saved["stages"] == ["C3", "Deep", "C6"]
        service = CaseService(async_sessionmaker(engine, expire_on_commit=False))
        gateway = SimpleNamespace(calls=saved["stages"], requests=saved["requests"], responses=saved["responses"])
        save("execution.json", old)
        save("substitute-calls.json", saved)
        return await verify(service, sample, initial, out, gateway)
    return await seeded_case(engine, record, scenario=scenario)
