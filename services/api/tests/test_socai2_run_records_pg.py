"""Run record HTTP reads against isolated local PG; no model, tool or deployment.

Use the existing run_checks runner. Fixtures are fresh UUIDs and retained.
"""
import base64
import hashlib
import json
import traceback
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2.baseline_store import StoreError, digest, encoded
from app.socai2.page_reader import PageReadService
from app.socai2.run_records import F, R, RunRecordLimits, RunRecordService, S
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.identity import BusinessContext
from investigation_http.adapters.run_records import RunRecordBackend
from investigation_http.adapters.services import CaseBackend
from investigation_http.dependencies import (
    case_service,
    page_service,
    run_record_service,
)
from investigation_http.main import app
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

TENANT, USER = UUID(int=1), UUID(int=3)
ROOT = Path(__file__).resolve().parents[3]
PREFIX = "/api/v1/socai2/analysis-runs/"


async def run_checks(engine, record, only=None):
    if only and "run_records_flow" not in only:
        return
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    limits = RunRecordLimits(50, 100)
    backend = RunRecordBackend(sessions, limits=limits)
    service = backend.reader
    subjects = {k: uuid4() for k in ("alert", "incident", "case")}
    runs = {k: uuid4() for k in subjects}
    empty_run = uuid4()
    steps = {k: [uuid4() for _ in range(1001 if k == "case" else 2)] for k in subjects}
    artifacts = {k: [uuid4() for _ in range(201 if k == "case" else 2)] for k in subjects}
    source_artifact = uuid4()
    requests = []
    saved_overrides = dict(app.dependency_overrides)
    old_context = getattr(app.state, "business_context", None)

    async def fixture():
        async with service.transaction(TENANT) as store:
            now = await store.now()
            await store.db.execute(insert(m.Alerts).values(id=subjects["alert"], tenant_id=TENANT,
                source_namespace="run-records-20261114", source_identity_key=str(subjects["alert"]), title="Run records fixture"))
            await store.db.execute(insert(m.Incidents).values(id=subjects["incident"], tenant_id=TENANT,
                source_namespace="run-records-20261114", source_incident_id=str(subjects["incident"]), title="Run records fixture"))
            await store.db.execute(insert(m.Cases).values(id=subjects["case"], tenant_id=TENANT, title="Run records fixture"))
            await store.db.execute(insert(m.CaseAlerts).values(id=uuid4(), tenant_id=TENANT,
                case_id=subjects["case"], alert_id=subjects["alert"], membership_source="manual", source_operation_id=uuid4()))
            scope = (await store.db.execute(select(m.Cases.scope_revision).where(m.Cases.id == subjects["case"]))).scalar_one()
            for kind, identity in subjects.items():
                await store.db.execute(insert(R).values(id=runs[kind], tenant_id=TENANT, **{kind + "_id": identity},
                    kind={"alert": "alert_basic", "incident": "incident_diagnosis", "case": "baseline"}[kind],
                    title="Run records fixture", purpose="saved read validation", trigger="manual",
                    state={"alert": "failed", "incident": "unknown", "case": "pending_update"}[kind],
                    **({"scope_revision": scope, "scope_kind": "whole_case"} if kind == "case" else {
                        "started_at": now, **({"ended_at": now} if kind == "alert" else {}),
                        "operation_key": str(uuid4()), "request_hash": digest({"run": str(runs[kind])}),
                        "input_artifact_id": artifacts[kind][0], "executor_version": "synthetic-records-fixture"})))
                rows = []
                for n, sid in enumerate(steps[kind]):
                    rows.append(dict(id=sid, tenant_id=TENANT, run_id=runs[kind], seq=n + 1,  # noqa: C408 -- fixture row assembly
                        kind="stage" if n == 0 else "tool", stage_code="fixture", name="Saved step",
                        state="completed", started_at=now, ended_at=now,
                        parent_step_id=steps[kind][0] if n else None,
                        input_artifact_id=artifacts[kind][0] if n == 0 else None,
                        output_artifact_id=artifacts[kind][1] if n == 0 else None,
                        reused_artifact_id=(artifacts["alert"][0] if n == 0 else source_artifact) if kind == "case" and n < 2 else None,
                        actual_args={"fixture": True, "index": n},
                        returned_rows=0 if n else None))
                await store.db.execute(insert(S), rows)
                for n, fid in enumerate(artifacts[kind]):
                    payload = {"fixture": True, "subject": kind, "index": n}
                    unavailable = kind == "case" and n == 200
                    await store.db.execute(insert(F).values(id=fid, tenant_id=TENANT, run_id=runs[kind],
                        **{kind + "_id": identity}, step_id=steps[kind][0] if n < 2 else None,
                        kind="input_snapshot" if n == 0 else "tool_response", schema_version="synthetic.v1",
                        mime_type="application/json", captured_at=now, material_state="unavailable" if unavailable else "complete",
                        source_refs=[], retention={"reason": "fixture intentionally unavailable"} if unavailable else {},
                        **({} if unavailable else {"content_json": payload, "sha256": digest(payload), "size_bytes": len(encoded(payload))})))
                if kind == "case":
                    await store.db.execute(insert(m.RunMembers).values(id=uuid4(), tenant_id=TENANT,
                        case_id=identity, run_id=runs[kind], alert_id=subjects["alert"]))
                    await store.db.execute(update(R).where(R.c.id == runs[kind]).values(state="running", started_at=now,
                        operation_key=str(uuid4()), request_hash=digest({"run": str(runs[kind])}),
                        input_artifact_id=artifacts[kind][0], executor_version="synthetic-records-fixture"))
                    await store.db.execute(update(R).where(R.c.id == runs[kind]).values(state="completed", ended_at=now))
            payload = {"fixture": True, "source": "no-run"}
            await store.db.execute(insert(F).values(id=source_artifact, tenant_id=TENANT, alert_id=subjects["alert"],
                kind="source_snapshot", schema_version="synthetic.v1", mime_type="application/json", captured_at=now,
                content_json=payload, size_bytes=len(encoded(payload)), sha256=digest(payload),
                material_state="complete", source_refs=[], retention={}))
            await store.db.execute(insert(R).values(id=empty_run, tenant_id=TENANT, case_id=subjects["case"],
                kind="baseline", title="Empty pending fixture", purpose="empty read validation", trigger="manual",
                state="pending_update", scope_revision=scope, scope_kind="whole_case"))

    async def snapshot():
        values = {}
        async with service.transaction(TENANT, readonly=True) as store:
            for table in (m.Alerts.__table__, m.Incidents.__table__, m.Cases.__table__, R, S, F):
                # IDs scoped to this fresh batch. Includes complete rows, not only counts.
                ids = list(subjects.values()) + list(runs.values()) + [empty_run, source_artifact]
                ids += [v for group in steps.values() for v in group] + [v for group in artifacts.values() for v in group]
                rows = (await store.db.execute(select(table).where(*store.where(table, table.c.id.in_(ids)))
                    .order_by(table.c.id))).mappings().all()
                values[table.name] = {"count": len(rows), "sha256": hashlib.sha256(
                    json.dumps([dict(v) for v in rows], sort_keys=True, default=str).encode()).hexdigest()}
        return values

    async def get(client, path, *, code=200, error=None, **params):
        response = await client.get(path, **({"params": params} if params else {}))
        requests.append({"path": path, "params": {k: v for k, v in params.items() if k != "cursor"}, "status": response.status_code})
        assert response.status_code == code, (path, response.status_code, response.text[:1000])
        value = response.json()
        if error:
            assert value["detail"]["code"] == error, value
        return value

    async def collect(client, path, **params):
        items, total, page_count, cursor = [], None, 0, None
        while True:
            page = await get(client, path, **params, **({"cursor": cursor} if cursor else {}))
            assert page["total"] == total if total is not None else True
            total, cursor = page["total"], page["next_cursor"]
            items.extend(page["items"])
            page_count += 1
            assert page_count < 100, "cursor did not terminate"
            if cursor is None:
                break
        assert len(items) == total == len({r["id"] for r in items})
        return items, page_count

    try:
        await fixture()
        before = await snapshot()
        app.state.business_context = BusinessContext(TENANT, USER, "Synthetic HTTP record reader")
        app.dependency_overrides[run_record_service] = lambda: backend
        app.dependency_overrides[case_service] = lambda: CaseBackend(sessions)
        app.dependency_overrides[page_service] = lambda: PageReadService(sessions)
        evidence = {"subjects": subjects, "runs": runs, "empty_run": empty_run, "pages": {}}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
            for kind, identity in subjects.items():
                base = PREFIX + str(runs[kind])
                rows, count = await collect(client, base + "/steps", limit=100 if kind == "case" else 1)
                assert [r["id"] for r in rows] == [str(sid) for sid in steps[kind]]
                evidence["pages"][kind + "_steps"] = {"pages": count, "count": len(rows)}
                arts, count = await collect(client, base + "/artifacts", limit=100 if kind == "case" else 1)
                assert [r["id"] for r in arts] == sorted(map(str, artifacts[kind]))
                evidence["pages"][kind + "_artifacts"] = {"pages": count, "count": len(arts)}
                assert all(not ({"blob_ref", "content_json", "tenant_id", "created_at"} & set(v)) for v in arts)
                for row in [v for v in arts if v["id"] == str(artifacts[kind][0])]:
                    body = await get(client, row["content_url"])
                    assert body["content_json"] == {"fixture": True, "subject": kind, "index": 0}
                detail = await get(client, f"/api/v1/socai2/cases/{identity}/runs/{runs[kind]}" if kind == "case"
                    else f"/api/v1/socai2/{kind}s/{identity}/analysis/runs/{runs[kind]}/trace")
                assert detail["steps_url"] == base + "/steps" and detail["artifacts_url"] == base + "/artifacts"
                if kind == "case":
                    assert detail["steps_truncated"] and detail["artifacts_truncated"]
            base = PREFIX + str(runs["case"])
            for n in (0, 1):
                row = await get(client, base + "/steps/" + str(steps["case"][n]))
                ref = next(r for r in row["artifact_refs"] if r["role"] == "reused")
                assert ref["subject_type"] == "alert" and ref["subject_id"] == str(subjects["alert"])
                assert ref["run_id"] == (str(runs["alert"]) if n == 0 else None)
                body = await get(client, ref["content_url"])
                assert body["availability"] == "available" and body["content_json"]["fixture"]
            rows = await get(client, base + "/artifacts", step_id=str(steps["case"][0]))
            assert rows["total"] == 2 and {r["id"] for r in rows["items"]} == set(map(str, artifacts["case"][:2]))
            page = await get(client, base + "/artifacts", step_id=str(steps["case"][0]), limit=1)
            await get(client, base + "/artifacts", cursor=page["next_cursor"], code=422, error="invalid_cursor")
            last = await get(client, base + "/steps/" + str(steps["case"][-1]))
            assert last["seq"] == 1001 and last["actual_args"]["index"] == 1000
            tools, _ = await collect(client, base + "/steps", kind="tool", limit=100)
            assert len(tools) == 1000 and all(v["parent_step_id"] == str(steps["case"][0]) for v in tools)
            first = await get(client, base + "/steps")
            assert len(first["items"]) == limits.default_limit
            cursor = first["next_cursor"]
            await get(client, base + "/steps", cursor=cursor, kind="tool", code=422, error="invalid_cursor")
            await get(client, PREFIX + str(runs["alert"]) + "/steps", cursor=cursor, code=422, error="invalid_cursor")
            await get(client, base + "/artifacts", cursor=cursor, code=422, error="invalid_cursor")
            for bad in ("not-a-cursor", base64.urlsafe_b64encode(b'[]').decode(), ""):
                await get(client, base + "/steps", cursor=bad, code=422, error="invalid_cursor")
            await get(client, base + "/steps", limit=101, code=422, error="invalid_input")
            await get(client, base + "/steps", unexpected="x", code=422, error="invalid_input")
            await get(client, base + "/steps?limit=1&limit=2", code=422, error="invalid_input")
            await get(client, base + "/steps", kind="invalid", code=422)
            await get(client, PREFIX + "invalid/steps", code=422)
            await get(client, PREFIX + str(uuid4()) + "/steps", code=404, error="run_not_found")
            await get(client, base + "/steps/" + str(steps["alert"][0]), code=404, error="step_not_found")
            await get(client, base + "/artifacts", step_id=str(steps["alert"][0]), code=404, error="step_not_found")
            for directory in ("steps", "artifacts"):
                page = await get(client, PREFIX + str(empty_run) + "/" + directory)
                assert page["total"] == 0 and page["items"] == [] and page["next_cursor"] is None
            alternate = RunRecordBackend(sessions, limits=RunRecordLimits(7, 11))
            app.dependency_overrides[run_record_service] = lambda: alternate
            page = await get(client, base + "/steps")
            assert len(page["items"]) == 7
            await get(client, base + "/steps", limit=12, code=422, error="invalid_input")
            app.dependency_overrides.pop(run_record_service)
            with patch.dict("os.environ", {"SOCAI2_RUN_RECORDS_CONFIG_FILE": str(ROOT / "missing-read-config.json")}):
                await get(client, base + "/steps", code=503, error="service_unavailable")
            with patch.dict("os.environ", {"SOCAI2_RUN_RECORDS_CONFIG_FILE": str(ROOT / "deploy/http-service/run-records.json")}):
                assert RunRecordLimits.load() == limits
            # Same core API remains independent of HTTP identity/URL handling.
            try:
                await RunRecordService(sessions, limits=limits).page(UUID(int=2), runs["case"], "steps")
            except StoreError as exc:
                assert (exc.status, exc.code) == (404, "run_not_found")
            else:
                raise AssertionError("wrong tenant unexpectedly read fixture")
        after = await snapshot()
        assert before == after, "GET changed saved business rows"
        schema = app.openapi()
        routes = {k: v for k, v in schema["paths"].items() if k.startswith(PREFIX)}
        assert len(routes) == 3 and all(set(v) == {"get"} for v in routes.values())
        assert not any("security" in method for methods in routes.values() for method in methods.values())
        evidence.update({"http_requests": requests, "database_before": before, "database_after": after,
                         "http_count": len(requests), "real_pg": True, "transport": "ASGI", "model_calls": 0,
                         "tool_calls": 0, "schema_migrations": 0, "deployment": False})
        record("run_records_flow", True, evidence)
    except Exception:  # noqa: BLE001 -- preserve exact failed test evidence
        record("run_records_flow", False, {"trace": traceback.format_exc(), "http_requests": requests})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved_overrides)
        app.state.business_context = old_context
