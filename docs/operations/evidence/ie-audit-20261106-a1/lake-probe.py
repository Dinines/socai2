"""Independent read-only Tool probes using the recorded C1 frozen contexts, after all Runs finished."""
import asyncio
import json
import sys
from uuid import NAMESPACE_URL, UUID, uuid5

from app.db.clickhouse import close_clickhouse
from app.socai2.baseline_context import Context
from app.socai2.baseline_evidence_tools import LakeGateway, catalog, validate_rows


async def run(packet):
    tenant = UUID("6aff0ef7-c670-5a84-a2ee-83d73e25b964")
    out = []
    for case in packet:
        ctx = Context.model_validate(case["context"])
        assert str(tenant) == str(ctx.case["tenant_id"]) and str(ctx.case_id) == case["case_id"]
        for key, b in catalog(ctx, tenant)["bindings"].items():
            tool = b["tool_name"]
            if tool not in {"network_connections", "process_activity", "authentication_activity"}:
                continue
            assert b["source_database"] == "socai2_next_validation" and b["hostname"] == case["host"]
            qid = str(uuid5(NAMESPACE_URL, "ie-audit-20261106-a1:postrun:" + key))
            args = {"tool_name": tool, "contract_version": b["contract_version"], "scope": b["scope"], "limit": 10,
                    "parameters": {"tenant_id": str(tenant), "hostname": b["hostname"], "source_database": b["source_database"],
                                   "alert_ids": b["alert_ids"], "binding_id": key, "query_id": qid}}
            rows = await LakeGateway().query(args, qid, 12)
            validate_rows(rows, args)
            assert all(str(r["event_id"]) in case["event_ids"] for r in rows)
            out.append({"key": case["key"], "args": args, "rows": rows, "row_count": len(rows)})
    await close_clickhouse()
    print("PROBE=" + json.dumps(out, ensure_ascii=False, default=str))


asyncio.run(run(json.load(sys.stdin)))
