"""Multi-Run SQL transport; transaction serialization is a test double, not PG."""
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from uuid import UUID
from _compatible_memory_ledger import MemoryLedger


class AdmissionDatabase:
    def __init__(self, *, alert, now):
        self.alerts = {alert["id"]: deepcopy(alert)}
        self.now = now
        self.runs, self.events, self.artifacts = {}, [], {}
        self.lock = asyncio.Lock()
        self.trace = []
        self.fail_kind = None
        self.fail_after_commit = False
        self.on_alert_lock = None

    @asynccontextmanager
    async def acquire(self):
        yield AdmissionConnection(self)

    def snapshot(self):
        return deepcopy((self.runs, self.events, self.artifacts))


class AdmissionConnection(MemoryLedger):
    def __init__(self, database):
        self.db = database
        self.current_run = None

    @property
    def run(self): return self.db.runs[self.current_run]
    @property
    def events(self): return self.db.events
    @property
    def artifacts(self): return self.db.artifacts
    @property
    def now(self): return self.db.now
    @property
    def fail_kind(self): return self.db.fail_kind

    @asynccontextmanager
    async def transaction(self, *, isolation=None):
        self.db.trace.append(("transaction", isolation))
        async with self.db.lock:
            before = self.db.snapshot()
            try:
                yield self
            except BaseException:
                self.db.runs, self.db.events, self.db.artifacts = before
                raise
            if self.db.fail_after_commit:
                self.db.fail_after_commit = False
                raise RuntimeError("simulated lost commit acknowledgement")

    async def execute(self, sql, *args):
        assert "set_config('app.current_tenant_id'" in sql and UUID(args[0]).int
        self.db.trace.append(("tenant", args))

    def selected_run(self, sql, value):
        if value is None: return None
        self.current_run = value["id"]
        columns = sql.split(" FROM ")[0].removeprefix("SELECT ") if sql.startswith("SELECT") else sql.split("RETURNING ")[1]
        return deepcopy({k: value[k] for k in columns.split(",")})

    async def fetchrow(self, sql, *args):
        if sql.startswith("SELECT") and "FROM investigation_runs" in sql:
            self.db.trace.append(("operation_lookup", args))
            value = self.db.runs.get(args[0])
            return self.selected_run(sql, value) if value is not None and value["tenant_id"] == args[1] else None
        if "FROM alerts" in sql:
            assert "WHERE id=$1 AND tenant_id=$2 FOR UPDATE" in sql
            self.db.trace.append(("alert_lock", args))
            if self.db.on_alert_lock:
                hook, self.db.on_alert_lock = self.db.on_alert_lock, None
                hook(self.db)
            value = self.db.alerts.get(args[0])
            return deepcopy(value) if value and value["tenant_id"] == args[1] else None
        if sql.startswith("INSERT INTO investigation_runs"):
            self.db.trace.append(("run_insert", args))
            if self.db.fail_kind == "run": raise RuntimeError("simulated Run INSERT failure")
            if args[0] in self.db.runs: return None
            self.db.runs[args[0]] = dict(id=args[0], tenant_id=args[1], case_id=args[2], status="running",
                completed_at=None, total_tokens=0, total_cost_usd=0)
            return self.selected_run(sql, self.db.runs[args[0]])
        return await super().fetchrow(sql, *args)

    async def fetch(self, sql, *args):
        if "FROM investigation_runs" in sql:
            assert "WHERE tenant_id=$1 AND case_id=$2 ORDER BY id FOR UPDATE" in sql
            assert "investigation_events" not in sql  # Missing marker must not filter a reserved Run out.
            self.db.trace.append(("target_candidates", args))
            return [self.selected_run(sql, row) for _, row in sorted(self.db.runs.items(), key=lambda pair:str(pair[0]))
                    if (row["tenant_id"], row["case_id"]) == args]
        return await super().fetch(sql, *args)

    async def fetchval(self, sql, *args):
        if sql == "SELECT EXISTS(SELECT 1 FROM investigation_events WHERE run_id=$1)":
            return any(e["run_id"] == args[0] for e in self.events)
        if sql.startswith("INSERT INTO investigation_events") and args[5] == self.db.fail_kind:
            raise RuntimeError("simulated event INSERT failure")
        return await super().fetchval(sql, *args)
