"""SQL transport adds full managed-event version guard; no real PG proof."""
from _program_memory_ledger import MemoryLedger as ProgramLedger

class MemoryLedger(ProgramLedger):
    async def fetchval(self, sql, *args):
        if "agent IS DISTINCT FROM $4" in sql:
            run,tenant,kinds,agent=args
            return any((e["run_id"],e["tenant_id"]) == (run,tenant) and e["kind"].startswith("unified_")
                       and (e["kind"] not in kinds or e["agent"] != agent) for e in self.events)
        return await super().fetchval(sql,*args)

    @classmethod
    def from_ledger(cls, original):
        # Keep the same lock and row objects used by actual store methods.
        transport=cls.__new__(cls)
        transport.__dict__=original.__dict__
        return transport
