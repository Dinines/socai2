"""Forward-only schema migrations for the ClickHouse event lake.

`services/api/clickhouse/001_init.sql` is four `CREATE TABLE IF NOT EXISTS`
statements and zero `ALTER TABLE`, and `lake_writer` "self-heals" with the
same idiom. Both are no-ops once the table exists, so a new column lands on
a fresh deployment and silently does not land on an existing one — and the
failure is invisible until a query selects a column that is not there, which
happens long after the deploy that was supposed to add it.

This is the ClickHouse half of the migration mechanism whose Neo4j half is
`graph_migrations.py`. Same shape deliberately: numbered, append-only,
applied ids recorded in the store itself so a deployment knows what it has.

Three differences ClickHouse forces:

**The ledger is a table, not a node**, and it is created with the same
`IF NOT EXISTS` idiom this module exists to work around. That is fine for
exactly one table whose schema never changes — and the schema is pinned by
a test, so "never changes" is enforced rather than hoped for.

**`ADD COLUMN IF NOT EXISTS` is genuinely idempotent** in ClickHouse, unlike
Neo4j's constraint syntax, so a migration that half-applied can be re-run.
Statements should still be written to tolerate it, because a mutation that
fails midway leaves the earlier statements applied.

**Distributed DDL is asynchronous.** On a cluster, `ALTER TABLE` returns
before every replica has applied it. Single-node deployments are unaffected;
a cluster needs `ON CLUSTER` and a sync setting, which is called out on the
migration that would need it rather than assumed.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from app.db.lake_schema import (
    COLUMNS,
    CONSTRAINTS,
    LakeStoragePolicy,
    configured_policy,
    migration_statements,
    sql_string,
)

logger = logging.getLogger("aisoc.lake_migrations")

#: Schema of the ledger itself. Pinned by a test: this table is created with
#: the `IF NOT EXISTS` idiom the rest of this module exists to replace, which
#: is only safe while its shape never changes.
_LEDGER_DDL = """
CREATE TABLE IF NOT EXISTS {database}._migrations (
    migration_id  String,
    description   String,
    applied_at    DateTime64(3, 'UTC') DEFAULT now64(),
    statements    UInt32
) ENGINE = MergeTree()
ORDER BY migration_id
"""


@dataclass(frozen=True)
class LakeMigration:
    """One forward-only change to the lake schema.

    ``statements`` run in order. ``backfill`` runs after them for changes
    that need to touch data — ClickHouse mutations are asynchronous, so a
    backfill that must complete before the next migration has to wait on
    ``system.mutations`` itself rather than assuming the ALTER returned.
    """

    id: str
    description: str
    statements: tuple[str, ...] = ()
    backfill: Callable[[Any], Awaitable[int]] | None = None
    #: True when the statements need `ON CLUSTER` on a multi-replica
    #: deployment. Recorded rather than applied, because this repo has no
    #: cluster topology to name and guessing one is worse than declaring the
    #: limitation.
    needs_cluster_ddl: bool = False
    tags: tuple[str, ...] = field(default_factory=tuple)


# ── 001: the pre-existing init schema, captured as a migration ─────────────
#
# Identical in effect to 001_init.sql, so an existing deployment records 001
# as applied and converges rather than re-running statements it cannot know
# the outcome of. Deliberately not a copy of the file: the file creates the
# database and tables, and re-running it here would be the same no-op. What
# matters is that the ledger agrees the baseline exists.
_V1_BASELINE = ("CREATE DATABASE IF NOT EXISTS aisoc",)


# ── 002: the activity projection ───────────────────────────────────────────
#
# Depth plan 2.2. Ingest now answers five questions on every event — who
# acted, what kind of actor they were, what they did, to which resource, from
# where, with what outcome — and the lake has to carry the answers as columns
# rather than only inside `ocsf_json`, or a hunt for "every action by a
# non-human actor from a new ASN" is a full scan of a ZSTD blob.
#
# `actor_kind` is a LowCardinality(String) and not an Enum: an Enum would
# make adding a kind a schema migration on a table with months of data, and
# the closed set lives in Go (`activity.ActorKinds`) where the gate can read
# it. The bloom filters mirror the ones 001_init.sql already puts on the
# high-cardinality hunt needles.
_V2_ACTIVITY_PROJECTION = (
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS actor_kind LowCardinality(String) DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS actor_kind_source String DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS actor_id String DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS actor_on_behalf_of String DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS action String DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS resource_type String DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS resource_id String DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS resource_owner String DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS src_country_code LowCardinality(String) DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS src_asn UInt32 DEFAULT 0",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS src_as_org String DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS src_reputation Float32 DEFAULT 0",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS src_reputation_known UInt8 DEFAULT 0",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS client_family LowCardinality(String) DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS client_version String DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS client_category LowCardinality(String) DEFAULT ''",
    # The raw string is kept beside the parse because a user agent is
    # attacker-controlled and every parser is a lossy summary of it. A tool
    # renamed to "Mozilla/5.0" is itself the finding, and only the raw
    # column can show it.
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS client_raw String DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS outcome LowCardinality(String) DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD INDEX IF NOT EXISTS idx_action action TYPE bloom_filter(0.01) GRANULARITY 4",
    "ALTER TABLE aisoc.raw_events ADD INDEX IF NOT EXISTS idx_resource_id resource_id TYPE bloom_filter(0.01) GRANULARITY 4",
)

# ── 003: the retention ceiling ─────────────────────────────────────────────
#
# Depth plan 4.3. `001_init.sql` wrote `TTL ... + INTERVAL 90 DAY` into the
# table, and ClickHouse enforces that during merges with no reference to any
# per-tenant setting — so a tenant who chose 400 days lost every event at day
# 90, with nothing erroring and the console still showing 400.
#
# The init file now writes the ceiling instead, and this is the half an
# *existing* deployment applies: that file runs only in the container
# entrypoint on a fresh volume, so a TTL changed there alone lands on new
# installs and silently not on the ones that already hold data — which are
# precisely the ones with retention to lose.
#
# `MODIFY TTL` rewrites the table's TTL expression and schedules a
# re-evaluation of existing parts. It does not resurrect rows already
# deleted under the old 90-day TTL; nothing can. An operator upgrading a
# deployment that has been running longer than 90 days keeps what it has and
# starts accumulating toward the new ceiling from here.
_V3_RETENTION_CEILING = ("ALTER TABLE aisoc.raw_events MODIFY TTL toDateTime(event_time) + INTERVAL 400 DAY",)

# ── 004: sessions per principal ────────────────────────────────────────────
#
# Depth plan 2.4. The lake is the third store that has to agree on a session,
# beside the `sessions` table (migration 102) and the Neo4j Session node, and
# all three carry the same deterministic uuid so a hunt can join them without
# any of them having coordinated at write time.
#
# `session_key_kind` is a column and not a derivable detail: a query counting
# events per session means something different for a vendor session than for
# a principal+address+client grouping this product derived, and a hunter who
# cannot see which they have will mix the two in one result set.
#
# A bloom filter on `session_id` rather than on `session_key`: the id is what
# a join uses, and the key is high-cardinality free text that is read after
# the id has already narrowed the scan.
_V4_SESSIONS = (
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS session_id String DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS session_key String DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS session_key_kind LowCardinality(String) DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD COLUMN IF NOT EXISTS session_originating_human String DEFAULT ''",
    "ALTER TABLE aisoc.raw_events ADD INDEX IF NOT EXISTS idx_session_id session_id TYPE bloom_filter(0.01) GRANULARITY 4",
)


MIGRATIONS: tuple[LakeMigration, ...] = (
    LakeMigration(
        id="001_baseline",
        description=("Records the 001_init.sql baseline as applied. Creates nothing an existing deployment does not already have."),
        statements=_V1_BASELINE,
        tags=("baseline",),
    ),
    LakeMigration(
        id="002_activity_projection",
        description=(
            "Adds the activity projection columns (actor kind and identity, normalized action, resource, "
            "source geography/ASN/reputation, parsed client, outcome) to aisoc.raw_events."
        ),
        statements=_V2_ACTIVITY_PROJECTION,
        # Every statement is an ALTER on an existing table, which is exactly
        # the case that needs ON CLUSTER on a multi-replica deployment. The
        # repo names no cluster topology, so this is recorded rather than
        # guessed, and the runner logs it on the way past.
        needs_cluster_ddl=True,
        tags=("activity-projection", "depth-2.2"),
    ),
    LakeMigration(
        id="003_retention_ceiling",
        description=(
            "Raises the aisoc.raw_events TTL from 90 days to the 400-day ceiling a tenant may choose, so the "
            "lake stops deleting before the per-tenant window the purge worker enforces."
        ),
        statements=_V3_RETENTION_CEILING,
        needs_cluster_ddl=True,
        tags=("retention", "depth-4.3"),
    ),
    LakeMigration(
        id="004_sessions",
        description=(
            "Adds the session columns (deterministic id shared with Postgres and the graph, the vendor's own "
            "key, how strong the grouping is, and the originating human) to aisoc.raw_events."
        ),
        statements=_V4_SESSIONS,
        needs_cluster_ddl=True,
        tags=("sessions", "depth-2.4"),
    ),
    LakeMigration(
        id="005_lake_ingress_v1",
        description="Adds source/device/Kafka provenance and profile-selected ingestion-time retention; preserves legacy rows and keys.",
        needs_cluster_ddl=True,
        tags=("lake-ingress", "retention"),
    ),
)


async def _execute(client: Any, sql: str, params: dict[str, Any] | None = None) -> Any:
    """Run one statement against whichever ClickHouse client shape we have.

    The async driver exposes `execute`; the HTTP client exposes `command`.
    Both are in use across this repo depending on the service, and a
    migration runner that only speaks one of them is a runner that silently
    does not run in half the deployments.
    """
    method = getattr(client, "execute", None) or getattr(client, "command", None)
    if method is None:
        raise TypeError(f"{type(client).__name__} exposes neither execute() nor command(); the lake migration runner cannot drive it")
    args = (sql, params) if params else (sql,)
    if inspect.iscoroutinefunction(method):
        return await method(*args)
    return await asyncio.to_thread(method, *args)


def _compact(value: str) -> str:
    # Whitespace/case in string defaults and mapping names is meaningful.
    parts = re.findall(r"'(?:\\.|[^'\\])*'|[^']+", value)
    return "".join(part if part.startswith("'") else re.sub(r"\s+|`", "", part).lower() for part in parts)


async def _expression(client: Any, expression: str) -> str:
    rows = await _execute(client, f"EXPLAIN AST SELECT {expression}")
    return _compact("\n".join(row[0] for row in rows))


async def verify_schema(client: Any, policy: LakeStoragePolicy, *, complete: bool = False) -> None:
    """Read structure only. Reject drift before DDL; never infer success from IF NOT EXISTS."""
    where = f"database = {sql_string(policy.database)} AND name = 'raw_events'"
    rows = await _execute(client, f"SELECT engine_full, partition_key, sorting_key, create_table_query FROM system.tables WHERE {where}")
    if len(rows) != 1:
        raise ValueError("lake raw_events baseline missing; render and apply the explicit new-install schema first")
    engine, partition, order, create = rows[0]
    # 23.8 engine_full includes PARTITION/ORDER/TTL/SETTINGS; partition_key
    # renders tuples with parentheses, whereas newer adapters may spell tuple().
    engine_name = engine.split(" PARTITION BY", 1)[0]
    if _compact(engine_name) != "replacingmergetree(ingest_time)" or _compact(partition) not in {
        "(toyyyymm(event_time),tenant_id)", "tuple(toyyyymm(event_time),tenant_id)",
    }:
        raise ValueError("lake engine or partition differs from the approved baseline")
    if _compact(order) != "tenant_id,event_time,class_uid,event_id":
        raise ValueError("lake sorting key differs from the approved baseline")
    cols = await _execute(client, f"SELECT name, type, default_kind, default_expression FROM system.columns WHERE database = {sql_string(policy.database)} AND table = 'raw_events'")
    actual = {name: (kind, default_kind, default) for name, kind, default_kind, default in cols}
    for index, (name, kind, default, _codec) in enumerate(COLUMNS):
        if name not in actual:
            if complete or index < 48:
                raise ValueError(f"lake required column missing: {name}")
            continue
        expected = (kind, "DEFAULT" if default else "", default)
        if tuple(map(_compact, actual[name])) != tuple(map(_compact, expected)):
            raise ValueError(f"lake column type/default mismatch: {name}")
    existing = dict(re.findall(r"CONSTRAINT\s+(\w+)\s+CHECK\s+(.+?)(?=,\s*(?:CONSTRAINT|INDEX)|\)\s*ENGINE)", create, re.DOTALL))
    for name, expression in CONSTRAINTS.items():
        if name not in existing:
            if complete:
                raise ValueError(f"lake constraint missing: {name}")
        elif await _expression(client, existing[name]) != await _expression(client, expression):
            raise ValueError(f"lake constraint mismatch: {name}")
    ttl = re.search(r"\bTTL\s+(.+?)(?:\s+SETTINGS\b|$)", create, re.DOTALL)
    if not ttl:
        raise ValueError("lake TTL missing")
    actual_ttl = await _expression(client, ttl[1])
    target_ttl = await _expression(client, policy.ttl)
    legacy_ttl = await _expression(client, f"toDateTime(event_time) + toIntervalDay({policy.legacy_days})")
    if actual_ttl != target_ttl and (complete or actual_ttl != legacy_ttl):
        raise ValueError("lake TTL differs from the approved legacy/profile rules")


async def applied_ids(client: Any, *, policy: LakeStoragePolicy | None = None) -> set[str]:
    """Migration ids this lake already has.

    Create a missing ledger, then read it. A failed read is a failure rather
    than permission to replay every migration against an unknown state.
    """
    policy = policy or configured_policy()
    await _execute(client, _LEDGER_DDL.format(database=policy.database))
    # A fresh ledger is empty. A failed SELECT is not evidence of a first run.
    rows = await _execute(client, f"SELECT migration_id FROM {policy.database}._migrations")

    ids: set[str] = set()
    for row in rows or []:
        # Drivers return tuples, dicts or scalars depending on which one.
        if isinstance(row, dict):
            value = row.get("migration_id")
        elif isinstance(row, list | tuple):
            value = row[0] if row else None
        else:
            value = row
        if value:
            ids.add(str(value))
    return ids


async def _record(client: Any, migration: LakeMigration, statements: int, policy: LakeStoragePolicy) -> None:
    await _execute(
        client,
        f"INSERT INTO {policy.database}._migrations (migration_id, description, statements) "
        f"SELECT {sql_string(migration.id)}, {sql_string(migration.description)}, toUInt32({statements})",
    )
    if migration.id not in await applied_ids(client, policy=policy):
        raise RuntimeError("lake migration ledger readback failed")


async def run_migrations(client: Any, *, strict: bool = True, policy: LakeStoragePolicy | None = None) -> list[str]:
    """Apply every unapplied migration in order. Returns the ids applied.

    Stops at the first failure rather than continuing, because migration
    N+1 is written against the schema N produced. Continuing past a failure
    is how a lake ends up in a state no migration file describes.

    ``strict=False`` logs and returns what succeeded, for deployments that
    would rather start degraded than not at all. It is not the default: a
    silently-skipped schema change is the exact failure this module exists
    to remove.
    """
    policy = policy or configured_policy()
    await verify_schema(client, policy)
    already = await applied_ids(client, policy=policy)
    if "005_lake_ingress_v1" in already:
        await verify_schema(client, policy, complete=True)
    applied: list[str] = []

    for migration in MIGRATIONS:
        if migration.id in already:
            continue

        if migration.needs_cluster_ddl:
            logger.warning(
                "lake_migrations.cluster_ddl_unhandled id=%s — this migration "
                "needs ON CLUSTER on a multi-replica deployment and will only "
                "apply to the node it is run against",
                migration.id,
            )

        logger.info("lake_migrations.applying id=%s", migration.id)
        try:
            if migration.id == "005_lake_ingress_v1":
                statements = migration_statements(policy)
            else:
                # Preflight has verified all 48 baseline columns and keys.
                # Adopt their historical IDs without replaying 003's old TTL
                # over an already-current new-install table.
                statements = ()
            for statement in statements:
                await _execute(client, statement)
            if migration.backfill is not None:
                touched = await migration.backfill(client)
                logger.info("lake_migrations.backfill id=%s rows=%s", migration.id, touched)
            if migration.id == "005_lake_ingress_v1":
                await verify_schema(client, policy, complete=True)
            await _record(client, migration, len(statements), policy)
        except Exception as exc:
            logger.error("lake_migrations.failed id=%s error=%s", migration.id, exc)
            if strict:
                raise
            return applied

        applied.append(migration.id)

    if applied:
        logger.info("lake_migrations.complete applied=%s", ",".join(applied))
    return applied


async def pending_ids(client: Any, *, policy: LakeStoragePolicy | None = None) -> list[str]:
    """Migrations this lake has not applied. For health checks and preflight."""
    already = await applied_ids(client, policy=policy)
    return [m.id for m in MIGRATIONS if m.id not in already]
