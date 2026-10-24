"""V2-only tool dispatch. Never falls back to the legacy registry."""
from __future__ import annotations
from typing import Any
from uuid import UUID
from .records import ActivityRecordsResult, activity_records

TOOLS = {"activity_records": activity_records}
BACKED_TOOLS = frozenset(TOOLS)

async def dispatch(name: str, tenant_id: UUID | str, args: dict[str, Any]) -> ActivityRecordsResult:
    if name not in TOOLS:
        return ActivityRecordsResult("rejected", {"executed": False, "returned_count": 0},
                                     reason="unknown_v2_tool")
    if not isinstance(args, dict) or "tenant_id" in args:
        return ActivityRecordsResult("rejected", {"executed": False, "returned_count": 0},
                                     reason="invalid_or_unsupported_arguments")
    return await activity_records(tenant_id, **args)
