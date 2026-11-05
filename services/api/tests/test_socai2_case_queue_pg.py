"""Restricted synthetic PostgreSQL queue checks; no model/lake calls.

The isolation runner supplies its temporary restricted role and existing
synthetic database. Authentication is an explicit ASGI substitute.
"""
import asyncio
import traceback
from unittest.mock import patch
from uuid import UUID, uuid4

from app.api.v1.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import socai2_cases as api
from app.models import socai2 as m
from app.socai2.baseline_store import C
from app.socai2.case_contracts import CaseQueueQuery
from app.socai2.case_reader import CaseReader
from app.socai2.case_service import CaseService
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

TENANT, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
BASE = "/api/v1/socai2/cases"
TASKS, REVISIONS = m.Tasks.__table__, m.TaskRevisions.__table__


async def run_checks(engine, record, only=None):
    service = CaseService(async_sessionmaker(engine, expire_on_commit=False))
    principal = CurrentUser(USER, TENANT, "viewer", "synthetic-queue@example.invalid", scopes=["cases:read"])
    app = FastAPI()
    app.include_router(api.router, prefix="/api/v1")

    async def user():
        return principal

    app.dependency_overrides[get_current_user] = user
    app.dependency_overrides[api.get_service] = lambda: service
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local")

    async def get(*, code=200, **params):
        response = await client.get(BASE, params=params)
        assert response.status_code == code, (response.status_code, response.text)
        return response.json()

    async def persisted(ids, tenant=TENANT):
        async with service.transaction(tenant, readonly=True) as store:
            return [dict(row) for row in (await store.db.execute(select(C).where(
                C.c.id.in_(ids)).order_by(C.c.id))).mappings()]

    async def fixture():
        prefix = "synthetic-queue-" + uuid4().hex
        ids = [uuid4() for _ in range(5)]
        async with service.transaction(TENANT) as store:
            now = await store.now()
            for cid, suffix, state, assignment, severity in zip(ids[:4],
                    ("100%_one", "two", "three", "four"),
                    ("new", "in_progress", "resolved", "new"),
                    ("unassigned", "unresolved", "unassigned", "assigned"),
                    ("high", "high", "high", "critical"), strict=True):
                await store.db.execute(insert(C).values(id=cid, tenant_id=TENANT,
                    title=f"{prefix} {suffix}", handling_status=state,
                    assignment_state=assignment, severity=severity, business_updated_at=now,
                    owner_id=USER if assignment == "assigned" else None,
                    owner_source_value="missing synthetic person" if assignment == "unresolved" else None))
            for cid, state in ((ids[0], "not_started"), (ids[0], "in_progress"),
                               (ids[1], "completed"), (ids[2], "not_started"), (ids[3], "cancelled")):
                tid, old, current = uuid4(), uuid4(), uuid4()
                await store.db.execute(insert(TASKS).values(id=tid, tenant_id=TENANT,
                    case_id=cid, current_revision_id=current))
                for revision_id, revision, revision_state in ((old, 1, "not_started"), (current, 2, state)):
                    values = {"id": revision_id, "tenant_id": TENANT, "case_id": cid, "task_id": tid,
                        "revision": revision, "title": "synthetic queue task", "state": revision_state, "changed_by": USER}
                    if revision_state == "completed":
                        values.update(result_text="Synthetic feedback only", completed_at=now,
                            completed_by=USER, result_scope={"kind": "whole_case", "alert_ids": [],
                                "object_keys": [], "window_start": None, "window_end": None, "limitations": []})
                    await store.db.execute(insert(REVISIONS).values(**values))
        async with service.transaction(OTHER) as store:
            await store.db.execute(insert(C).values(id=ids[4], tenant_id=OTHER,
                title=f"{prefix} foreign", severity="high", business_updated_at=now))
        return prefix, ids

    async def test_queue_pg_metrics_filters_and_stable_pagination():
        before = (await get())["metrics"]
        prefix, ids = await fixture()
        first = await get(q=prefix, limit=2)
        expected = {"awaiting_assignment": 1, "in_progress": 1, "high_severity": 2, "awaiting_human": 1}
        assert {key: first["metrics"][key] - before[key] for key in expected} == expected
        assert first["total"] == 4 and first["next_cursor"]
        second = await get(q=prefix, limit=2, cursor=first["next_cursor"])
        all_items = first["items"] + second["items"]
        assert [item["case"]["id"] for item in all_items] == [str(cid) for cid in sorted(ids[:4], reverse=True)]
        assert second["total"] == 4 and second["next_cursor"] is None and second["metrics"] == first["metrics"]
        for metric, total in expected.items():
            filtered = await get(q=prefix, metric=metric, limit=1)
            assert filtered["total"] == total and filtered["metrics"] == first["metrics"]
        human = await get(q=prefix, metric="awaiting_human")
        assert human["items"][0]["open_task_count"] == 2
        for params, expected_ids in (({"q": prefix + " 100%_"}, [ids[0]]),
                ({"q": str(ids[1])}, [ids[1]]), ({"q": prefix, "owner_id": str(USER)}, [ids[3]]),
                ({"q": prefix, "assignment_state": "unresolved"}, [ids[1]]),
                ({"q": prefix, "handling_status": "new", "severity": "high"}, [ids[0]])):
            data = await get(**params)
            assert [item["case"]["id"] for item in data["items"]] == list(map(str, expected_ids))
            assert data["metrics"] == first["metrics"]
        assert (await get(q=prefix + " absent"))["items"] == []
        assert (await get(q=prefix, metric="high_severity", cursor=first["next_cursor"], code=422))[
            "detail"] == "case_cursor_filters_changed"
        return {"case_ids": list(map(str, ids)), "metric_delta": expected, "pages": 2}

    async def test_queue_pg_tenant_permissions_and_cursor_binding():
        nonlocal principal
        prefix, ids = await fixture()
        initial = await get(q=prefix, limit=1)
        original = principal
        try:
            principal = CurrentUser(USER, OTHER, "viewer", original.email, scopes=["cases:read"])
            foreign = await get(q=prefix)
            assert foreign["total"] == 1 and foreign["items"][0]["case"]["id"] == str(ids[4])
            assert (await get(q=str(ids[0])))["total"] == 0
            assert (await get(q=prefix, cursor=initial["next_cursor"], code=422))["detail"] == "case_cursor_filters_changed"
            # Raw SELECT deliberately has no tenant predicate: this checks the
            # restricted role's RLS, in addition to reader-level predicates.
            assert [row["id"] for row in await persisted(ids, OTHER)] == [ids[4]]
            principal = CurrentUser(USER, TENANT, "viewer", original.email, scopes=["alerts:read"])
            await get(code=403)

            async def unauthorized():
                raise HTTPException(401, "synthetic missing authentication")

            app.dependency_overrides[get_current_user] = unauthorized
            await get(code=401)
        finally:
            principal = original
            app.dependency_overrides[get_current_user] = user
        await get(limit=0, code=422)
        await get(limit=51, code=422)
        return {"tenant_isolation": True, "http_statuses": [401, 403, 422]}

    async def test_queue_pg_readonly_snapshot_and_no_time_refresh():
        prefix, ids = await fixture()
        before = await persisted(ids)
        await get(q=prefix)
        await get(q=prefix, metric="high_severity")
        assert await persisted(ids) == before
        initial = await get(q=prefix)
        inserted = uuid4()
        original = CaseReader.rows
        changed = False

        async def interleave(reader, query):
            nonlocal changed
            result = await original(reader, query)
            if not changed:
                # The first metrics SELECT fixed the GET's snapshot; this
                # independent committed write must not leak into its list.
                changed = True
                async with service.transaction(TENANT) as store:
                    await store.db.execute(insert(C).values(id=inserted, tenant_id=TENANT,
                        title=prefix + " concurrent", severity="high"))
            return result

        with patch.object(CaseReader, "rows", interleave):
            frozen = await service.read_cases(TENANT, CaseQueueQuery(q=prefix))
        assert changed and frozen.total == 4 and len(frozen.items) == 4
        assert frozen.metrics.model_dump() == initial["metrics"]
        after = await get(q=prefix)
        assert after["total"] == 5 and after["metrics"]["awaiting_assignment"] == initial["metrics"]["awaiting_assignment"] + 1
        assert await persisted(ids) == before
        try:
            async with service.transaction(TENANT, readonly=True) as store:
                await store.db.execute(update(C).where(C.c.id == ids[0]).values(title="must not write"))
        except DBAPIError as exc:
            assert getattr(exc.orig, "sqlstate", None) == "25006"
        else:
            raise AssertionError("queue transaction allowed a write")
        return {"repeatable_read": True, "readonly_sqlstate": "25006", "case_rows_unchanged": 4}

    checks = [test_queue_pg_metrics_filters_and_stable_pagination,
        test_queue_pg_tenant_permissions_and_cursor_binding, test_queue_pg_readonly_snapshot_and_no_time_refresh]
    try:
        for check in checks:
            if only is not None and check.__name__ not in only:
                continue
            try:
                detail = await asyncio.wait_for(check(), 120)
                record(check.__name__, True, detail)
            except Exception:  # noqa: BLE001 -- retain original synthetic failures
                record(check.__name__, False, traceback.format_exc())
    finally:
        await client.aclose()
