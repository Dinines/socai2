"""One new isolated Case: C3 five findings, empty followups, stored HTTP reads."""
import copy
import hashlib
import json
from datetime import UTC, datetime
from types import SimpleNamespace

from app.socai2.baseline_context import reference
from app.socai2.baseline_dispatch import dispatch_followups
from app.socai2.baseline_enrichment import S
from app.socai2.baseline_executor import SCHEMA, BaselineExecutor
from app.socai2.baseline_store import F, digest
from app.socai2.case_service import CaseService
from app.socai2.runtime_policy import active_policy
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from investigation_http.external_routes import cases
from jsonschema import Draft202012Validator
from socai2_test_model_view import synthetic_measure
from sqlalchemy import select
from test_socai2_c3_output_contract import SECTIONS, with_findings
from test_socai2_case_boundary_pg import T
from test_socai2_case_boundary_pg import run_checks as seeded_case
from test_socai2_case_citation_quality_pg import snapshot
from test_socai2_case_followup_boundary import final_answer


class Gateway:
    provider, model = "synthetic", "synthetic-c3-output-contract-no-network"

    def __init__(self, service, cid, rid, save):
        self.service, self.cid, self.rid, self.save = service, cid, rid, save
        self.stages, self.requests, self.responses = [], [], []

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
        assert stage not in self.stages and stage in {"C3", "C6"}
        self.stages.append(stage)
        if stage == "C3":
            assert body["max_tokens"] == active_policy().model.output_tokens["C3"]
            schema = body["response_format"]["json_schema"]["schema"]
            assert set(schema["required"]) == SECTIONS and schema["properties"]["findings"]["maxItems"] == 5
            assert request["case_boundary"]["c3_output"] == {"version": "socai2.c3-output.v1", "max_findings": 5}
            answer = with_findings(request, context, 5)
        else:
            prior = next(row for row in request["followup_boundary"]["records"] if row["block"] == "C3")
            original = json.loads(self.responses[0]["choices"][0]["message"]["content"])
            assert prior["ref"]["role"] == "prior_analysis"
            assert [f["statement"] for f in prior["value"]["findings"]] == [f["statement"] for f in original["findings"]]
            comparison = request["followup_boundary"]["program_metadata"]["comparison"]
            answer = final_answer(request, context, comparison)
            answer["analysis"] = with_findings(request, context, 5)
        Draft202012Validator(body["response_format"]["json_schema"]["schema"]).validate(answer)
        reply = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(answer, ensure_ascii=False)}}],
            "usage": {"prompt_tokens": 200, "completion_tokens": 200, "total_tokens": 400}}
        self.requests.append(copy.deepcopy(request))
        self.responses.append(copy.deepcopy(reply))
        self.save("substitute-calls.json", {"stages": self.stages, "requests": self.requests, "responses": self.responses})
        return reply


async def run_checks(engine, config, output):
    def save(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")
    records = []
    def record(name, passed, detail):
        records.append({"name": name, "passed": passed, "detail": detail})
        save("execution.json", records)
    save("intent.json", {"batch": config["batch"], "planned_substitute_model_calls": 5,
        "fixture_calls": "2 A + 1 I", "case_calls": "1 C3 + 1 C6", "real_model_calls": 0,
        "external_source_calls": 0, "background_queries": "empty-query substitutes", "no_retry": True})

    async def scenario(service, sample):
        cid, rid = sample["case_id"], sample["run_id"]
        gateway = Gateway(service, cid, rid, save)
        lake = SimpleNamespace(configured=lambda: True)
        initial = await service.analyze(T, cid, rid, gateway=gateway, lake=lake)
        record("C3", initial["state"] == "completed", initial)
        assert initial["state"] == "completed" and initial["reason"] is None, initial
        assert set(initial["analysis"]) == SECTIONS and len(initial["analysis"]["findings"]) == 5
        assert len(initial["analysis"]["questions"]) == 6 and len(initial["analysis"]["domains"]) == 4
        assert initial["analysis"]["followups"] == []
        routes = await dispatch_followups(service, T, cid, rid, initial["analysis"]["followups"],
            initial["basis"]["binding_map"], gateway=gateway, lake=lake)
        assert routes == [] and gateway.stages == ["C3"]
        graph = await service.build_graph(T, cid, rid)
        executor = BaselineExecutor(service, T, gateway=gateway, lake=lake)
        async with service.transaction(T) as store:
            run = await store.run(cid, rid)
            c3 = await store.one(select(S).where(*store.where(S, S.c.run_id == rid,
                S.c.stage_code == "C3", S.c.kind == "stage")))
            await executor.record(store, run, "C4.routing", {"schema_version": SCHEMA, "type": "followup_dispatch",
                "run_id": str(rid), "initial_analysis_artifact_id": str(c3["output_artifact_id"]),
                "initial_state": initial["state"], "routes": routes, "graph_artifact_id": graph["graph_artifact_id"],
                "limitations": ["Synthetic C3 contract acceptance only."]},
                [reference("artifact", c3["output_artifact_id"], "execution_receipt")])
        out = await service.finalize(T, cid, rid, gateway=gateway)
        record("C6", out["state"] == "completed", out)
        assert out["state"] == "completed" and gateway.stages == ["C3", "C6"], out
        assert initial == await service.analyze(T, cid, rid, gateway=gateway, lake=lake)
        assert out == await service.finalize(T, cid, rid, gateway=gateway)
        data = await snapshot(service, sample)
        save("database.json", data)
        artifacts = {a["id"]: a for a in data["artifacts"]}
        case_artifacts = [a for a in data["artifacts"] if a["run_id"] == str(rid)]
        response = next(a for a in case_artifacts if a["kind"] == "model_response"
            and a["content_json"]["payload"]["citation_review"]["stage"] == "C3")
        payload = response["content_json"]["payload"]
        quality = payload["citation_review"]
        original = artifacts[quality["original_response_artifact_id"]]
        request = artifacts[quality["request_artifact_id"]]["content_json"]["payload"]
        assert request["body"]["max_tokens"] == active_policy().model.output_tokens["C3"] and request == gateway.requests[0]
        assert original["content_json"]["raw"] == payload["raw"] == gateway.responses[0]
        assert original["captured_at"] <= response["captured_at"]
        assert payload["derived"] == initial["analysis"] and payload["validation_error"] is None
        assert quality["derived_sha256"] == digest(initial["analysis"])
        assert quality["original_sha256"] == digest(gateway.responses[0]["choices"][0]["message"]["content"])
        assert not payload.get("correction_feedback") and not initial["basis"].get("correction_result")
        context = next(a["content_json"] for a in case_artifacts if a["schema_version"] == "socai2.baseline-context.v1")
        assert context["case_input_profile"] == request["case_boundary"]["profile"]
        c3_saved = artifacts[str(c3["output_artifact_id"])]["content_json"]
        assert c3_saved == initial
        steps = [s for s in data["run_steps"] if s["run_id"] == str(rid)]
        assert not any(s["stage_code"] in {"C4.deep", "C4.query", "C3.reanalysis"} for s in steps)
        assert len([s for s in steps if s["kind"] == "model" and s["stage_code"] == "C3"]) == 1
        result = data["results"][0]
        report = artifacts[out["report_artifact_id"]]["content_json"]
        assert result["validation_state"] == "accepted" and len(result["findings"]) == 5
        assert result["conclusion"] == report["conclusion"] == data["case_assessments"][0]["conclusion"]

        app, reader = FastAPI(), CaseService(service.sessions)
        app.include_router(cases.router, prefix="/api/v1")
        app.dependency_overrides[cases.get_service] = lambda: reader
        app.dependency_overrides[cases.ReadUser.__metadata__[0].dependency] = lambda: SimpleNamespace(tenant_id=T)
        base_path = f"/api/v1/socai2/cases/{cid}"
        replies = []
        async with AsyncClient(transport=ASGITransport(app=app), base_url=config["http_base_url"]) as client:
            async def get(path):
                response = await client.get(path)
                replies.append({"path": path, "status": response.status_code, "body": response.json()})
                save("api-responses.json", replies)
                assert response.status_code == 200, replies[-1]
                return response.json()
            case = await get(base_path)
            assert case["current_assessment"]["value"]["conclusion"] == result["conclusion"]
            run = await get(base_path + f"/runs/{rid}")
            assert run["run"]["state"] == "completed" and run["result_ids"] == [result["id"]]
            saved_result = await get(base_path + f"/results/{result['id']}")
            assert saved_result["result"]["findings"] == result["findings"]
            for row in case_artifacts:
                readback = await get(base_path + f"/runs/{rid}/artifacts/{row['id']}")
                assert readback["content_json"] == row["content_json"] and readback["content_text"] == row["content_text"]
        assert await snapshot(service, sample) == data and gateway.stages == ["C3", "C6"]
        checks = {"C3_once_seven_sections": True, "C3_actual_request_output_limit": request["body"]["max_tokens"],
            "frozen_max_findings": 5, "C3_saved_findings": 5, "model_questions": 5, "stored_questions": 6,
            "stored_domains": 4, "empty_followups_no_extra_call": True,
            "original_derived_and_summary_read_identically": True, "C6_reads_all_C3_findings": True,
            "GET_no_writes_or_dispatch": True, "http_gets": len(replies), "case_substitute_model_calls": 2,
            "fixture_substitute_model_calls": 3, "real_model_calls": 0, "external_source_calls": 0,
            "supplement_calls": 0, "case_id": str(cid), "run_id": str(rid), "result_id": result["id"]}
        save("checks.json", checks)
        names = ["database.json", "api-responses.json", "substitute-calls.json", "checks.json", "intent.json", "execution.json"]
        save("manifest.json", {"schema_version": "socai2.page-export.v1", "batch_id": config["batch"],
            "tenant_id": str(T), "case_id": str(cid), "exported_at": datetime.now(UTC).isoformat(),
            "source_environment": "isolated_pg_with_model_and_background_query_substitutes",
            "database": config["expected_database"], "input_kind": "synthetic", "real_model_calls": 0,
            "sources": [{"file": name, "sha256": hashlib.sha256((output / name).read_bytes()).hexdigest()} for name in names]})
        return checks

    return await seeded_case(engine, record, scenario=scenario)
