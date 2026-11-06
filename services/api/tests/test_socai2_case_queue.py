"""Queue SQL semantics on local SQLite plus ASGI/transaction contracts.

No network, PostgreSQL, model or production data is used. Portable table types
let the actual reader's SELECT expressions execute against a small local set;
this does not stand in for PostgreSQL RLS/isolation acceptance.
"""
import base64
import unittest
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID

from app.api.v1.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import socai2_cases as api
from app.socai2 import case_reader as reader
from app.socai2.baseline_store import StoreError
from app.socai2.case_contracts import CaseQueuePage, CaseQueueQuery
from app.socai2.case_service import CaseService
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    MetaData,
    Table,
    Uuid,
    create_engine,
    insert,
    select,
)
from sqlalchemy.types import TypeDecorator

TENANT, OTHER, USER = UUID(int=101), UUID(int=102), UUID(int=103)
NOW = datetime(2026, 11, 5, tzinfo=UTC)


class UTCDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value


def portable_table(source, metadata):
    def portable_type(column):
        name = type(column.type).__name__
        if name in {"JSONB", "ARRAY"}:
            return JSON()
        if name == "UUID":
            return Uuid()
        if isinstance(column.type, DateTime):
            return UTCDateTime()
        return column.type.copy()
    return Table(source.name, metadata, *[Column(c.name, portable_type(c), primary_key=c.primary_key)
                                         for c in source.columns])


class QueueSQLTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        metadata = MetaData()
        tables = {name: portable_table(getattr(reader, name), metadata)
                  for name in ("C", "CA", "R", "TASKS", "TASK_REVISIONS")}
        metadata.create_all(self.engine)
        self.connection = self.engine.connect()
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.connection.close)
        self.tables = tables
        for name, table in tables.items():
            replacement = patch.object(reader, name, table)
            replacement.start()
            self.addCleanup(replacement.stop)
        self.selects = []

        async def execute(statement):
            self.assertTrue(statement.is_select)
            self.selects.append(statement)
            return self.connection.execute(statement)

        async def members(case_id):
            return set(self.connection.execute(select(tables["CA"].c.alert_id).where(
                tables["CA"].c.tenant_id == TENANT, tables["CA"].c.case_id == case_id)).scalars())

        self.store = SimpleNamespace(tenant_id=TENANT, db=SimpleNamespace(execute=execute), members=members,
            where=lambda table, *conditions: [table.c.tenant_id == TENANT, *conditions])
        self.reader = reader.CaseReader(self.store)
        for ident, status, assignment, severity in (
            (1, "new", "unassigned", "high"), (2, "in_progress", "unresolved", "high"),
            (3, "resolved", "unassigned", "high"), (4, "new", "assigned", "critical"),
            (5, "new", "unassigned", "high"),
        ):
            row = {c.name: None for c in tables["C"].columns}
            row.update(id=UUID(int=ident), tenant_id=OTHER if ident == 5 else TENANT,
                title="Case 100%_one" if ident == 1 else f"Case {ident}", handling_status=status,
                assignment_state=assignment, owner_id=USER if assignment == "assigned" else None,
                owner_source_value="missing person" if assignment == "unresolved" else None,
                severity=severity, tags=[], priority_state="not_provided", scope_revision=1,
                created_at=NOW, business_updated_at=NOW, row_version=1)
            self.connection.execute(insert(tables["C"]).values(**row))
        for ident in (1, 2, 3, 5):
            for member in range(2):
                self.connection.execute(insert(tables["CA"]).values(id=UUID(int=ident * 100 + member),
                    tenant_id=OTHER if ident == 5 else TENANT, case_id=UUID(int=ident),
                    alert_id=UUID(int=ident * 1000 + member)))
        # Two current open tasks in case 1 count as one waiting case; old
        # revisions and completed/cancelled current revisions do not count.
        for ident, case, state in ((11, 1, "not_started"), (12, 1, "in_progress"),
                                    (13, 2, "completed"), (14, 3, "not_started"),
                                    (15, 5, "in_progress")):
            tenant = OTHER if case == 5 else TENANT
            self.connection.execute(insert(tables["TASKS"]).values(id=UUID(int=ident), tenant_id=tenant,
                case_id=UUID(int=case), current_revision_id=UUID(int=ident + 100)))
            for revision, revision_state in ((ident + 100, state), (ident + 200, "not_started")):
                self.connection.execute(insert(tables["TASK_REVISIONS"]).values(id=UUID(int=revision),
                    tenant_id=tenant, task_id=UUID(int=ident), case_id=UUID(int=case), state=revision_state))
        for ident, case, state in ((301, 1, "running"), (302, 1, "pending_update"),
                                   (303, 2, "unknown"), (304, 2, "pending_update"),
                                   (305, 4, "pending_update")):
            row = {c.name: None for c in tables["R"].columns}
            row.update(id=UUID(int=ident), tenant_id=TENANT, case_id=UUID(int=case), kind="baseline",
                title="Baseline", purpose="Check evidence", trigger="manual", scope_revision=1,
                state=state, requested_at=NOW, delivery_state="none", row_version=1)
            self.connection.execute(insert(tables["R"]).values(**row))

    async def test_metrics_ignore_filters_and_task_multiplicity(self):
        all_cases = await self.reader.queue(CaseQueueQuery())
        expected = {"awaiting_assignment": 1, "in_progress": 1, "high_severity": 2, "awaiting_human": 1}
        self.assertEqual(all_cases.total, 4)
        self.assertEqual(all_cases.metrics.model_dump(), expected)
        selected = await self.reader.queue(CaseQueueQuery(metric="awaiting_human", limit=1))
        self.assertEqual(selected.total, 1)
        self.assertEqual(selected.items[0].case.id, UUID(int=1))
        self.assertEqual(selected.items[0].open_task_count, 2)
        self.assertEqual(selected.metrics.model_dump(), expected)

    async def test_seek_pagination_is_stable_for_equal_business_times(self):
        first = await self.reader.queue(CaseQueueQuery(limit=2))
        second = await self.reader.queue(CaseQueueQuery(limit=2, cursor=first.next_cursor))
        self.assertEqual([i.case.id.int for i in first.items], [4, 3])
        self.assertEqual([i.case.id.int for i in second.items], [2, 1])
        self.assertIsNone(second.next_cursor)
        self.assertEqual(first.total, second.total)
        self.assertEqual(first.metrics, second.metrics)

    async def test_cursor_cannot_cross_filter_or_tenant(self):
        first = await self.reader.queue(CaseQueueQuery(limit=1))
        for query in (CaseQueueQuery(cursor=first.next_cursor, metric="awaiting_human"),
                      CaseQueueQuery(cursor=first.next_cursor, q="Case")):
            with self.assertRaisesRegex(StoreError, "case_cursor_filters_changed"):
                await self.reader.queue(query)
        with self.assertRaisesRegex(StoreError, "case_cursor_filters_changed"):
            reader.queue_cursor(OTHER, CaseQueueQuery(cursor=first.next_cursor))
        for value in ("not-base64", base64.urlsafe_b64encode(b'{}').decode(), ""):
            with self.assertRaisesRegex(StoreError, "invalid_case_cursor"):
                reader.queue_cursor(TENANT, CaseQueueQuery(cursor=value))

    async def test_literal_title_id_and_owner_filters(self):
        query = await self.reader.queue(CaseQueueQuery(q="%_"))
        self.assertEqual([item.case.id.int for item in query.items], [1])
        query = await self.reader.queue(CaseQueueQuery(q=str(UUID(int=2)).upper()))
        self.assertEqual([item.case.id.int for item in query.items], [2])
        for filters, expected in (({"owner_id": USER}, [4]),
                                  ({"assignment_state": "unresolved"}, [2]),
                                  ({"handling_status": "new", "severity": "high"}, [1])):
            query = await self.reader.queue(CaseQueueQuery(**filters))
            self.assertEqual([item.case.id.int for item in query.items], expected)

    async def test_pending_and_active_records_are_distinct(self):
        data = await self.reader.queue(CaseQueueQuery())
        by_case = {item.case.id.int: item for item in data.items}
        for case, active_state in ((1, "running"), (2, "unknown")):
            records = {r.run.state: r for r in by_case[case].baseline_records}
            self.assertIn(active_state, records)
            self.assertEqual(records["pending_update"].start_eligibility.reason, "baseline_active")
            self.assertEqual(records[active_state].start_eligibility.reason, "not_pending")
        self.assertEqual(by_case[4].baseline_records[0].start_eligibility.reason, "empty_scope")

    async def test_empty_page_retains_metrics_and_filtered_total(self):
        page = await self.reader.queue(CaseQueueQuery(q="No such case"))
        self.assertEqual(page.items, [])
        self.assertEqual(page.total, 0)
        self.assertEqual(page.metrics.high_severity, 2)


class QueueBoundaryTest(unittest.IsolatedAsyncioTestCase):
    async def test_manual_start_uses_authorized_capacity_policy(self):
        service = CaseService(None)

        @asynccontextmanager
        async def transaction(tenant_id):
            self.assertEqual(tenant_id, TENANT)
            yield SimpleNamespace(now=AsyncMock(return_value=NOW))

        service.transaction = transaction
        service.actor = AsyncMock()
        service.start_full = AsyncMock()
        service.read_run = AsyncMock(return_value="run")
        case_id, run_id, request, actor = UUID(int=1), UUID(int=301), object(), object()
        result = await service.start_case(TENANT, case_id, run_id, request, actor=actor)
        self.assertEqual(result, "run")
        call = service.start_full.await_args
        self.assertEqual(call.args, (TENANT, case_id, run_id, request))
        self.assertIs(call.kwargs["actor"], actor)
        limits = call.kwargs["limits"]
        self.assertEqual((limits.max_tokens, limits.max_model_calls, limits.max_tool_calls), (48000, 4, 4))
        self.assertEqual(limits.max_rows_per_query, 200)
        self.assertEqual((limits.deadline_at - NOW).total_seconds(), 120)
        self.assertEqual(limits.policy_version, "socai2.manual-http.v2")
        service.read_run.assert_awaited_once_with(TENANT, case_id, run_id)

    async def test_service_uses_one_readonly_transaction(self):
        service = CaseService(None)
        entered = []

        @asynccontextmanager
        async def transaction(tenant_id, *, readonly=False):
            entered.append((tenant_id, readonly))
            yield SimpleNamespace(db=None)

        service.transaction = transaction
        with patch.object(reader.CaseReader, "queue", new=AsyncMock(return_value="result")) as queue:
            query = CaseQueueQuery()
            self.assertEqual(await service.read_cases(TENANT, query), "result")
            queue.assert_awaited_once_with(query)
        self.assertEqual(entered, [(TENANT, True)])

    def test_query_limits_and_enum_values(self):
        for bad in ({"limit": 0}, {"limit": 51}, {"metric": "all"}, {"severity": "high-ish"},
                    {"cursor": "x" * 1025}, {"q": "x" * 201}):
            with self.assertRaises(ValidationError):
                CaseQueueQuery(**bad)
        self.assertIsNone(CaseQueueQuery(q="  ").q)

    async def test_asgi_collection_auth_parameters_and_disabled_gate(self):
        principal = CurrentUser(USER, TENANT, "admin", "synthetic@example.invalid", scopes=["cases:read"])
        app = FastAPI()
        app.include_router(api.router, prefix="/api/v1")

        async def current_user():
            return principal

        output = CaseQueuePage(items=[], total=0, next_cursor=None,
            metrics={"awaiting_assignment": 0, "in_progress": 0, "high_severity": 0, "awaiting_human": 0})
        service = SimpleNamespace(read_cases=AsyncMock(return_value=output))
        app.dependency_overrides[get_current_user] = current_user
        app.dependency_overrides[api.get_service] = lambda: service
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
            result = await client.get("/api/v1/socai2/cases", params={"limit": 7, "q": " Case ",
                "metric": "awaiting_human", "owner_id": str(USER), "tenant_id": str(OTHER)})
            self.assertEqual(result.status_code, 200)
            tenant, query = service.read_cases.await_args.args
            self.assertEqual(tenant, TENANT)
            self.assertEqual((query.limit, query.q, query.metric, query.owner_id), (7, "Case", "awaiting_human", USER))
            self.assertEqual((await client.get("/api/v1/socai2/cases?limit=51")).status_code, 422)
            principal.scopes = ["alerts:read"]
            self.assertEqual((await client.get("/api/v1/socai2/cases")).status_code, 403)
            principal.scopes = ["cases:read"]
            app.dependency_overrides.pop(api.get_service)
            with patch.object(api.settings, "SOCAI2_CASE_API_ENABLED", False):
                self.assertEqual((await client.get("/api/v1/socai2/cases")).status_code, 503)
        self.assertIn("get", app.openapi()["paths"]["/api/v1/socai2/cases"])


if __name__ == "__main__":
    unittest.main()
