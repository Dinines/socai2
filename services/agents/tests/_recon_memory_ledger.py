"""Small SQL transport double, not a budget engine or proof of PostgreSQL.

Runs the actual store methods; copies database rows for rollback and can inject
commit ambiguity. Real row locks, constraints and grants must be verified in PG.
"""
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
import json


class MemoryLedger:
    def __init__(self, *, run_id, tenant_id, now):
        self.run = dict(id=run_id, tenant_id=tenant_id, status="running", completed_at=None,
                        total_tokens=0, total_cost_usd=0)
        self.events, self.artifacts = [], {}
        self.now = now
        self.lock = asyncio.Lock()
        self.fail_kind = None
        self.fail_after_commit = False

    @asynccontextmanager
    async def acquire(self):
        yield self

    @asynccontextmanager
    async def transaction(self):
        async with self.lock:
            before = deepcopy((self.run, self.events, self.artifacts))
            try:
                yield self
            except BaseException:
                self.run, self.events, self.artifacts = before
                raise
            if self.fail_after_commit:
                self.fail_after_commit = False
                raise RuntimeError("simulated lost acknowledgement after commit")

    async def execute(self, sql, *args):
        assert "set_config('app.current_tenant_id'" in sql
        assert args == (str(self.run["tenant_id"]),)

    async def fetch(self, sql, *args):
        assert "FROM investigation_events" in sql and "ORDER BY seq ASC LIMIT 2" in sql
        run, tenant, kinds = args
        matches = [e for e in self.events if (e["run_id"], e["tenant_id"]) == (run, tenant) and e["kind"] in kinds]
        return deepcopy(sorted(matches, key=lambda e: e["seq"])[:2])

    async def fetchrow(self, sql, *args):
        if "FROM investigation_runs" in sql:
            return deepcopy(self.run) if args == (self.run["id"], self.run["tenant_id"]) else None
        if "FROM investigation_events" in sql:
            run, tenant, kinds = args
            matches = [e for e in self.events if (e["run_id"], e["tenant_id"]) == (run, tenant) and e["kind"] in kinds]
            return deepcopy(max(matches, key=lambda e: e["seq"])) if matches else None
        if "FROM investigation_artifacts" in sql:
            identity, run, tenant = args
            row = self.artifacts.get(identity)
            if row is None or (row["run_id"], row["tenant_id"]) != (run, tenant): return None
            event = next((e for e in self.events if e["id"] == row["event_id"]), None)
            if event is None or (event["run_id"], event["tenant_id"]) != (run, tenant): return None
            return deepcopy(row)
        raise AssertionError("unexpected read in ledger double")

    async def fetchval(self, sql, *args):
        if "clock_timestamp()" in sql: return self.now
        if sql.startswith("SELECT EXISTS"):
            return any(e["run_id"] == args[0] and e["kind"].startswith("unified_") for e in self.events)
        if "COALESCE(MAX(seq)" in sql:
            return max((e["seq"] for e in self.events if e["run_id"] == args[0]), default=0) + 1
        if sql.startswith("INSERT INTO investigation_events"):
            identity, run, tenant, seq, ts, kind, agent, summary, payload, input_hash, output_hash = args
            assert not any(e["id"] == identity for e in self.events)
            assert len(kind) <= 40
            self.events.append(dict(id=identity, run_id=run, tenant_id=tenant, seq=seq, ts=ts, kind=kind,
                                    agent=agent, summary=summary, payload=json.loads(payload),
                                    input_hash=input_hash, output_hash=output_hash))
            return identity
        if sql.startswith("INSERT INTO investigation_artifacts"):
            identity, run, event, tenant, kind, body, digest, size = args
            if kind == self.fail_kind: raise RuntimeError("simulated artifact write failure")
            assert identity not in self.artifacts and len(kind) <= 40
            assert any((e["id"], e["run_id"], e["tenant_id"]) == (event, run, tenant) for e in self.events)
            self.artifacts[identity] = dict(id=identity, run_id=run, event_id=event, tenant_id=tenant,
                                           kind=kind, content=body, sha256=digest, size_bytes=size)
            return identity
        raise AssertionError("unexpected scalar operation in ledger double")
