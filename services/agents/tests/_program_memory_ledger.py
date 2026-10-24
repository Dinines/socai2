"""Program store SQL transport adds an owned event-by-id read; no PG proof."""
from copy import deepcopy
from _recon_memory_ledger import MemoryLedger as BaseLedger

class MemoryLedger(BaseLedger):
    async def fetchrow(self, sql, *args):
        if "FROM investigation_events WHERE id=$1" in sql:
            identity, run, tenant = args
            return next((deepcopy(e) for e in self.events if (e["id"], e["run_id"], e["tenant_id"]) == (identity, run, tenant)), None)
        if "kind LIKE 'unified_%'" in sql:
            run, tenant = args[:2]
            boundary = args[2] if len(args) == 3 else float("inf")
            matches = [e for e in self.events if (e["run_id"], e["tenant_id"]) == (run, tenant)
                       and e["kind"].startswith("unified_") and e["seq"] < boundary]
            return {"id": max(matches, key=lambda e:e["seq"])["id"]} if matches else None
        return await super().fetchrow(sql, *args)
