"""Read only the new source fixture through the candidate ordinary reader."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from uuid import UUID

import asyncpg


async def main():
    folder = Path(sys.argv[1])
    plan = json.loads((folder / "sources-plan.json").read_text())
    identity = json.loads((folder / "source-target.json").read_text())
    config = json.loads((folder / "source-runtime.json").read_text())
    private = json.loads(Path(config["private_http_source"]).read_text())
    dsn = private["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(dsn, timeout=config["probe_timeout_seconds"],
                                command_timeout=config["probe_timeout_seconds"])
    try:
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", plan["target"]["tenant_id"])
            who = dict(await conn.fetchrow("""SELECT current_database() AS database,
                current_user AS role,current_setting('transaction_read_only') AS readonly,
                ssl,version FROM pg_stat_ssl WHERE pid=pg_backend_pid()"""))
            assert who["database"] == plan["target"]["database"] == identity["postgres"]["database"]
            assert who["role"] == identity["postgres"]["reader"]
            assert who["readonly"] == "on" and who["ssl"]
            rows = await conn.fetch("""SELECT row_to_json(a) AS row FROM public.assets a
                WHERE tenant_id=$1 AND id=$2""", UUID(plan["target"]["tenant_id"]), UUID(plan["asset"]["id"]))
            assert len(rows) == 1
            record = json.loads(rows[0]["row"])
            assert all(record[key] == value for key, value in plan["asset"].items())
            times = [record[key] for key in ("first_seen", "last_seen", "created_at", "updated_at")]
            assert all(times) and len(set(times)) == 1
            matches = await conn.fetch("""SELECT 'exact_name_casefold' AS match_basis,id FROM public.assets
                WHERE tenant_id=$1 AND lower(name)=lower($2)
                UNION ALL SELECT 'exact_ip',id FROM public.assets
                WHERE tenant_id=$1 AND $3=ANY(ip_addresses)""",
                UUID(plan["target"]["tenant_id"]), plan["asset"]["name"], plan["asset"]["ip_addresses"][0])
            assert len(matches) == plan["expected_asset_hits"]["per_alert_row_count"]
            assert {str(row["id"]) for row in matches} == set(plan["expected_asset_hits"]["distinct_asset_ids"])
            assert sorted(row["match_basis"] for row in matches) == sorted(plan["expected_asset_hits"]["match_bases"])
            result = {"status": "passed", "source": "real_postgres_readonly_snapshot", "identity": who,
                      "batch_id": plan["batch_id"], "record": record,
                      "matches": [dict(row) for row in matches],
                      "sources_plan_sha256": hashlib.sha256((folder / "sources-plan.json").read_bytes()).hexdigest(),
                      "model_calls": 0, "history_or_intelligence_written": False}
            with (folder / "source-reader-01.json").open("x") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2, default=str)
                stream.write("\n")
            print(json.dumps({"status": "passed", "record_id": record["id"], "matches": len(matches)}))
    finally:
        await conn.close()


asyncio.run(main())
