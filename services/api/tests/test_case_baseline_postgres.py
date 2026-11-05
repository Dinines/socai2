"""Real PostgreSQL transaction/trigger tests in a disposable local database.

Opt in with AISOC_BASELINE_TEST_DSN pointing to a local PostgreSQL role that
can create databases. Never uses DATABASE_URL or an existing business database.
"""
import asyncio
import json
import os
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, skipUnless
from urllib.parse import urlparse
from uuid import UUID, uuid4

import asyncpg

DSN = os.environ.get("AISOC_BASELINE_TEST_DSN")
MIGRATION = Path(__file__).resolve().parents[1] / "migrations/122_case_baseline_pending.sql"
TENANT, CASE, A, B, C = (UUID(int=i) for i in (10, 30, 1, 2, 3))
BOOTSTRAP = """
CREATE TABLE tenants (id UUID PRIMARY KEY);
CREATE TABLE aisoc_cases (id UUID PRIMARY KEY, tenant_id UUID REFERENCES tenants(id),
    title TEXT NOT NULL, alert_ids UUID[]);
CREATE TABLE investigation_runs (
    id UUID PRIMARY KEY, tenant_id UUID NOT NULL REFERENCES tenants(id), case_id VARCHAR(200) NOT NULL,
    alert_summary TEXT, raw_alert JSONB, status VARCHAR(20) NOT NULL DEFAULT 'running',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
"""


@skipUnless(DSN, "requires explicit local AISOC_BASELINE_TEST_DSN; no production fallback")
class BaselinePostgresTransactions(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        if urlparse(DSN).hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("baseline integration tests require a local PostgreSQL host")
        self.name = "aisoc_baseline_test_" + uuid4().hex
        self.connections = []
        self.admin = await asyncpg.connect(DSN)
        await self.admin.execute(f'CREATE DATABASE "{self.name}"')
        self.addAsyncCleanup(self.cleanup_database)
        self.db = await self.connect()
        await self.db.execute(BOOTSTRAP)
        await self.db.execute(MIGRATION.read_text(encoding="utf-8"))
        await self.db.execute("INSERT INTO tenants VALUES ($1)", TENANT)
        await self.db.execute("INSERT INTO aisoc_cases VALUES ($1,$2,'Test baseline',$3)", CASE, TENANT, [A])

    async def connect(self):
        conn = await asyncpg.connect(DSN, database=self.name)
        await conn.set_type_codec("jsonb", schema="pg_catalog", encoder=json.dumps, decoder=json.loads)
        self.connections.append(conn)
        return conn

    async def cleanup_database(self):
        for conn in self.connections:
            await conn.close()
        assert self.name.startswith("aisoc_baseline_test_") and len(self.name.removeprefix("aisoc_baseline_test_")) == 32
        await self.admin.execute(f'DROP DATABASE "{self.name}"')
        await self.admin.close()

    async def pending(self, conn=None):
        return await (conn or self.db).fetchrow("SELECT * FROM investigation_runs WHERE tenant_id=$1 "
            "AND case_id=$2 AND status='pending_update' AND investigation_kind='baseline'", TENANT, str(CASE))

    async def add_members(self, conn, members):
        await conn.execute("UPDATE aisoc_cases SET alert_ids=ARRAY(SELECT DISTINCT unnest(alert_ids || $1::UUID[])) WHERE id=$2",
                           members, CASE)

    async def claim(self, conn, expected):
        async with conn.transaction():
            await conn.fetchrow("SELECT id FROM aisoc_cases WHERE tenant_id=$1 AND id=$2 FOR UPDATE", TENANT, CASE)
            run = await self.pending(conn)
            if run is None:
                return "already_started"
            run = await conn.fetchrow("SELECT * FROM investigation_runs WHERE id=$1 FOR UPDATE", run["id"])
            if run["scope_revision"] != expected:
                return "revision_conflict"
            await conn.execute("UPDATE investigation_runs SET status='running', started_at=NOW() WHERE id=$1", run["id"])
            return "started"

    async def test_create_update_noop_and_rollback(self):
        first = await self.pending()
        self.assertIsNone(first["started_at"])
        await self.add_members(self.db, [B])
        second = await self.pending()
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["scope_revision"], 2)
        await self.add_members(self.db, [A, B])
        self.assertEqual((await self.pending())["scope_revision"], 2)
        transaction = self.db.transaction()
        await transaction.start()
        await self.add_members(self.db, [C])
        await transaction.rollback()
        self.assertEqual((await self.pending())["scope_revision"], 2)
        self.assertEqual(await self.db.fetchval("SELECT count(*) FROM investigation_runs"), 1)

    async def test_two_membership_writers_keep_one_pending_and_both_additions(self):
        writer = await self.connect()
        transaction = self.db.transaction()
        await transaction.start()
        await self.add_members(self.db, [B])
        blocked = asyncio.create_task(self.add_members(writer, [C]))
        await asyncio.sleep(0.05)
        self.assertFalse(blocked.done())
        await transaction.commit()
        await asyncio.wait_for(blocked, 5)
        run = await self.pending()
        self.assertEqual(run["scope_revision"], 3)
        self.assertEqual(set(run["raw_alert"]["scope"]["selected_member_ids"]), {str(A), str(B), str(C)})
        self.assertEqual(await self.db.fetchval("SELECT count(*) FROM investigation_runs"), 1)

    async def test_start_wins_later_membership_creates_next_pending(self):
        writer = await self.connect()
        first = await self.pending()
        transaction = self.db.transaction()
        await transaction.start()
        await self.db.fetchrow("SELECT id FROM aisoc_cases WHERE id=$1 FOR UPDATE", CASE)
        await self.db.fetchrow("SELECT id FROM investigation_runs WHERE id=$1 FOR UPDATE", first["id"])
        await self.db.execute("UPDATE investigation_runs SET status='running',started_at=NOW() WHERE id=$1", first["id"])
        blocked = asyncio.create_task(self.add_members(writer, [B]))
        await asyncio.sleep(0.05)
        self.assertFalse(blocked.done())
        await transaction.commit()
        await asyncio.wait_for(blocked, 5)
        old = await self.db.fetchrow("SELECT * FROM investigation_runs WHERE id=$1", first["id"])
        pending = await self.pending()
        self.assertNotEqual(old["id"], pending["id"])
        self.assertEqual(old["raw_alert"]["scope"], first["raw_alert"]["scope"])
        self.assertEqual(pending["raw_alert"]["baseline"]["added_member_ids"], [str(B)])

    async def test_membership_wins_stale_start_cannot_claim(self):
        starter = await self.connect()
        transaction = self.db.transaction()
        await transaction.start()
        await self.add_members(self.db, [B])
        blocked = asyncio.create_task(self.claim(starter, 1))
        await asyncio.sleep(0.05)
        self.assertFalse(blocked.done())
        await transaction.commit()
        self.assertEqual(await asyncio.wait_for(blocked, 5), "revision_conflict")
        self.assertEqual((await self.pending())["scope_revision"], 2)

    async def test_duplicate_starts_claim_only_once(self):
        starter = await self.connect()
        results = await asyncio.gather(self.claim(self.db, 1), self.claim(starter, 1))
        self.assertCountEqual(results, ["started", "already_started"])
        self.assertEqual(await self.db.fetchval("SELECT count(*) FROM investigation_runs WHERE status='running'"), 1)

    async def test_unique_pending_and_started_scope_guards(self):
        run = await self.pending()
        with self.assertRaises(asyncpg.UniqueViolationError):
            await self.db.execute("INSERT INTO investigation_runs(id,tenant_id,case_id,investigation_kind,status) "
                "VALUES($1,$2,$3,'baseline','pending_update')", uuid4(), TENANT, str(CASE))
        self.assertEqual(await self.claim(self.db, 1), "started")
        with self.assertRaisesRegex(asyncpg.PostgresError, "started_baseline_scope_is_immutable"):
            await self.db.execute("UPDATE investigation_runs SET raw_alert=jsonb_set(raw_alert,'{scope}', '{}'::JSONB) WHERE id=$1", run["id"])
        with self.assertRaisesRegex(asyncpg.PostgresError, "started_baseline_scope_is_immutable"):
            await self.db.execute("UPDATE investigation_runs SET status='pending_update' WHERE id=$1", run["id"])

    async def test_claim_is_reserved_before_first_execution_step(self):
        first = await self.pending()
        # Simulate handing work to a worker that has not executed any step yet.
        # Reserving queued is already a claim, never an editable pending record.
        await self.db.execute("UPDATE investigation_runs SET status='queued' WHERE id=$1", first["id"])
        await self.add_members(self.db, [B])
        following = await self.pending()
        self.assertNotEqual(first["id"], following["id"])
        old = await self.db.fetchrow("SELECT * FROM investigation_runs WHERE id=$1", first["id"])
        self.assertEqual(old["raw_alert"]["scope"], first["raw_alert"]["scope"])
        with self.assertRaises(asyncpg.UniqueViolationError):
            await self.db.execute("UPDATE investigation_runs SET status='running',started_at=NOW() WHERE id=$1",
                                  following["id"])
        self.assertEqual((await self.pending())["id"], following["id"])
        await self.db.execute("UPDATE investigation_runs SET status='completed',completed_at=NOW() WHERE id=$1", first["id"])
        self.assertEqual(await self.claim(self.db, following["scope_revision"]), "started")
