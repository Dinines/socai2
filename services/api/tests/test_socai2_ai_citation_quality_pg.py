"""One isolated A→I save/read batch; explicit model substitutes, no source calls."""
import copy
import hashlib
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4, uuid5

from app.models import socai2 as m
from app.socai2.baseline_store import digest
from app.socai2.citation_quality import NOTE
from app.socai2.page_reader import PageReadService
from app.socai2.stage_reader import StageReadService
from app.socai2.stage_results import A, F, StageResultService
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from investigation_http.external_routes import analysis, pages
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_socai2_ai_boundary_pg import Gateway as AlertGateway
from test_socai2_incident_boundary_pg import Gateway as IncidentGateway
from test_socai2_incident_boundary_pg import policy

TENANT = UUID(int=1)


class RetainedAlert(AlertGateway):
    async def complete(self, body, timeout):
        result = await super().complete(body, timeout)
        answer = json.loads(result["choices"][0]["message"]["content"])
        ids = ["missing-reference", "missing-reference"] if self.mode == "unknown" else []
        answer.update(verdict="benign" if self.mode == "unknown" else "true_positive", confidence=.8,
            rationale="  合成测试原判定，不代表真实良恶。\n", evidence_ids=ids,
            recommendations=[{"reason": "保留缺引用的原建议。", "source_ids": []}])
        result["choices"][0]["message"]["content"] = json.dumps(answer, ensure_ascii=False)
        self.responses[-1] = copy.deepcopy(result)
        return result


class RetainedIncident(IncidentGateway):
    async def complete(self, body, timeout):
        result = await super().complete(body, timeout)
        answer = json.loads(result["choices"][0]["message"]["content"])
        answer["diagnosis"].update(summary="  原事件摘要。\n", conclusion="原事件结论保留，业务仍待复核。", source_ids=[])
        answer["members"][0]["state"] = "summarized"
        answer["members"][1]["source_ids"] = answer["members"][0]["source_ids"] * 2
        answer["findings"][0].update(source_ids=["missing-reference"], state="inferred")
        answer["open_questions"][0]["source_ids"] = []
        result["choices"][0]["message"]["content"] = json.dumps(answer, ensure_ascii=False)
        self.responses[-1] = copy.deepcopy(result)
        return result


async def run_checks(engine, config, output):
    def save(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")

    service = StageResultService(async_sessionmaker(engine, expire_on_commit=False))
    reader = StageReadService(service.sessions)
    aids, mids, iid = [uuid4(), uuid4()], [uuid4(), uuid4()], uuid4()
    operations = [uuid4() for _ in range(3)]
    rids = [uuid5(TENANT, "socai2.stage:" + str(op)) for op in operations]
    save("intent.json", {"alert_ids": aids, "material_ids": mids, "incident_id": iid,
        "operation_keys": operations, "run_ids": rids, "planned_substitute_model_calls": 3,
        "real_model_calls": 0, "source_calls": 0, "no_retry": True})
    async with service.transaction(TENANT) as store:
        await store.db.execute(insert(m.Incidents).values(id=iid, tenant_id=TENANT,
            source_namespace=config["batch"], source_incident_id=str(iid), title="阶段一步骤1 A/I保存读取合成测试"))
        for aid, mid in zip(aids, mids):
            await store.db.execute(insert(A).values(id=aid, tenant_id=TENANT, source_namespace=config["batch"],
                source_identity_key=str(aid), title="Synthetic retention alert", description="原采集说明。"))
            await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=TENANT, alert_id=aid, revision=1,
                raw_text="Synthetic original observation.", raw_json={"process": {"pid": 42},
                "custom": {"authorized": False, "size": 0, "permissions_after": []}}, detection={},
                source_scope={}, retention={}, material_state="complete"))
            await store.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
            await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=TENANT,
                incident_id=iid, alert_id=aid, membership_source="manual", basis_version="synthetic",
                correlation_basis={"reason": "explicit test membership"}, source_operation_id=uuid4()))

    async def no_query(*args, **kwargs):
        raise AssertionError("This fixture has no query selectors; no external query is authorized by this test")

    gateways, outcomes = [], []
    with policy(name=config["policy"].split("/")[-1]):
        for aid, op, mode in zip(aids, operations, ("unknown", "empty")):
            gateway = RetainedAlert(service, aid, mode=mode)
            gateways.append(gateway)
            outcomes.append(await service.execute_alert(TENANT, aid, op, gateway=gateway, query=no_query))
            save("execution.json", outcomes)
        gateway = RetainedIncident(service, iid)
        gateways.append(gateway)
        outcomes.append(await service.execute_incident(TENANT, iid, operations[-1], gateway=gateway))
        save("execution.json", outcomes)
        # Existing operation keys must return the saved outcome without dispatch.
        await service.execute_alert(TENANT, aids[0], operations[0], gateway=gateways[0], query=no_query)
        await service.execute_incident(TENANT, iid, operations[-1], gateway=gateway)
    assert all(row["state"] == "completed" for row in outcomes), outcomes
    assert [g.calls for g in gateways] == [1, 1, 1]

    # Export only this new A/I batch, including every request, raw reply and receipt.
    data = {}
    tables = [(m.Alerts, m.Alerts.id.in_(aids)), (m.AlertMaterials, m.AlertMaterials.id.in_(mids)),
        (m.AlertAssessments, m.AlertAssessments.source_run_id.in_(rids)), (m.Incidents, m.Incidents.id == iid),
        (m.IncidentAlerts, m.IncidentAlerts.incident_id == iid),
        (m.IncidentDiagnoses, m.IncidentDiagnoses.source_run_id.in_(rids)),
        (m.Runs, m.Runs.id.in_(rids)), (m.RunMembers, m.RunMembers.run_id.in_(rids)),
        (m.RunSteps, m.RunSteps.run_id.in_(rids)), (m.Artifacts, m.Artifacts.run_id.in_(rids))]
    async with service.transaction(TENANT, readonly=True) as store:
        for model, where in tables:
            table = model.__table__
            data[table.name] = [dict(row) for row in (await store.db.execute(select(table).where(
                *store.where(table, where)).order_by(table.c.id))).mappings()]
    data = json.loads(json.dumps(data, default=str))
    save("database.json", data)
    artifacts = {a["id"]: a for a in data["artifacts"]}
    requests, responses, publications = [], [], []
    for rid, gateway in zip(rids, gateways):
        rows = [a for a in data["artifacts"] if a["run_id"] == str(rid)]
        request = next(a for a in rows if a["kind"] == "model_request")
        response = next(a for a in rows if a["kind"] == "model_response")
        publication = next(a for a in rows if a["id"] == str(uuid5(rid, "publication")))
        raw = gateway.responses[0]
        content = raw["choices"][0]["message"]["content"]
        quality = response["content_json"]["citation_review"]
        original = artifacts[quality["original_response_artifact_id"]]
        assert original["content_json"]["raw"] == response["content_json"]["raw"] == raw
        assert original["captured_at"] <= response["captured_at"]
        assert quality["request_artifact_id"] == request["id"] and quality["attempt"] == 0
        assert quality["state"] == "issues_recorded" and quality["conclusion_modified"] is False
        assert quality["original_sha256"] == digest(content)
        assert quality["derived_sha256"] == publication["content_json"]["output_hash"]
        assert response["content_json"]["validation_error"] is None
        assert response["content_json"]["partial_review"] is None
        assert response["content_json"]["correction_feedback"] is None
        assert publication["content_json"]["outcome"]["adopted"] is True
        requests.append(request)
        responses.append(response)
        publications.append(publication)
    for row, gateway in zip(publications[:2], gateways[:2]):
        raw = json.loads(gateway.responses[0]["choices"][0]["message"]["content"])
        out = row["content_json"]["output"]
        assert all(out[k] == raw[k] for k in ("verdict", "rationale", "confidence"))
        assert out["recommendations"][0]["reason"] == raw["recommendations"][0]["reason"]
        assert not out["recommendations"][0]["source_refs"]
    iraw = json.loads(gateways[-1].responses[0]["choices"][0]["message"]["content"])
    iout = publications[-1]["content_json"]["output"]
    assert iout["summary"] == iraw["diagnosis"]["summary"] and iout["conclusion"] == iraw["diagnosis"]["conclusion"]
    assert not iout["source_refs"] and iout["findings"][-1]["statement"] == iraw["findings"][0]["statement"]
    assert not iout["findings"][-1]["support"] and iout["findings"][-1]["state"] == "inferred"
    detail = next(r for r in responses[-1]["content_json"]["citation_review"]["references"]
                  if r["path"] == "$.members.1.source_ids")
    assert detail["declared_members"] != detail["resolved"][0]["alert_ids"]
    assert iout["findings"][1]["support"][0] == detail["resolved"][0]["ref"]
    frozen = artifacts[str(outcomes[-1]["input_artifact_id"])]["content_json"]
    for member in frozen["members"]:
        index = list(map(str, aids)).index(member["alert"]["id"])
        assert member["triage"]["source_run_id"] == str(rids[index])
        assert member["triage"]["rationale"] == publications[index]["content_json"]["output"]["rationale"]
        assert frozen["triage_citation_quality"][member["alert"]["id"]]["artifact_id"] == responses[index]["id"]
        assert frozen["triage_validation"][member["alert"]["id"]]["usable"] is True
    assert NOTE in requests[-1]["content_json"]["body"]["messages"][1]["content"]
    assert sum(s["ref"]["role"] == "prior_analysis" for s in requests[-1]["content_json"]["source_map"].values()) >= 2

    app = FastAPI()
    def dependency(value):
        return lambda: value
    for module, instance in ((analysis, reader), (pages, PageReadService(service.sessions))):
        app.include_router(module.router, prefix="/api/v1")
        app.dependency_overrides[module.get_service] = dependency(instance)
        app.dependency_overrides[module.User.__metadata__[0].dependency] = lambda: SimpleNamespace(tenant_id=TENANT)
    replies = []
    async with AsyncClient(transport=ASGITransport(app=app), base_url=config["http_base_url"]) as client:
        for index, (subject, sid, rid) in enumerate(zip(("alerts", "alerts", "incidents"), [*aids, iid], rids)):
            base = f"/api/v1/socai2/{subject}/{sid}/analysis"
            paths = [base, f"{base}/runs/{rid}", f"{base}/runs/{rid}/trace"]
            paths += [f"{base}/runs/{rid}/artifacts/{row['id']}" for row in data["artifacts"] if row["run_id"] == str(rid)]
            for path in paths:
                response = await client.get(path)
                replies.append({"path": path, "status": response.status_code, "body": response.json()})
                save("api-responses.json", replies)
                assert response.status_code == 200, replies[-1]
                body = response.json()
                if "/artifacts/" in path:
                    assert body["content_json"] == artifacts[path.rsplit("/", 1)[-1]]["content_json"]
                elif path == f"{base}/runs/{rid}":
                    assert body["run"]["state"] == "completed" and body["run"]["delivery_state"] == "complete"
                    assert body["freshness"] == "current" and body["is_current_pointer"] is True
                    expected = publications[index]["content_json"]["output"]
                    if subject == "alerts":
                        assert body["result"]["rationale"] == expected["rationale"]
                        assert body["result"]["verdict"] == expected["verdict"]
                    else:
                        assert body["result"]["summary"] == expected["summary"]
                        assert body["result"]["diagnosis"]["conclusion"] == expected["conclusion"]
        assert [g.calls for g in gateways] == [1, 1, 1]
    async with service.transaction(TENANT, readonly=True) as store:
        after = [dict(row) for row in (await store.db.execute(select(F).where(*store.where(F, F.c.run_id.in_(rids))).order_by(F.c.id))).mappings()]
    assert json.loads(json.dumps(after, default=str)) == data["artifacts"]
    checks = {"original_judgments_saved_and_read": True, "citation_issues_separate": True,
        "raw_and_derived_hashes_match": True, "no_fabricated_source_binding": True,
        "A_to_I_frozen_prior_and_quality_note": True, "existing_adoption_and_freshness": True,
        "GET_no_model_dispatch_or_artifact_write": True, "http_gets": len(replies),
        "substitute_model_calls": 3, "real_model_calls": 0, "external_query_calls": 0}
    save("checks.json", checks)
    names = ("database.json", "api-responses.json", "checks.json", "intent.json", "execution.json")
    save("manifest.json", {"schema_version": "socai2.page-export.v1", "batch_id": config["batch"],
        "tenant_id": str(TENANT), "case_id": None, "exported_at": datetime.now(UTC).isoformat(),
        "source_environment": "isolated_pg_with_model_substitutes_and_skipped_queries",
        "database": config["expected_database"], "input_kind": "synthetic", "real_model_calls": 0,
        "sources": [{"file": name, "sha256": hashlib.sha256((output / name).read_bytes()).hexdigest()} for name in names]})
    return checks
