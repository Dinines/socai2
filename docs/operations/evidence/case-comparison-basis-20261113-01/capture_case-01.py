"""Read the real Case scope for 4177; preserve the earlier seed-subject snapshot."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "docs/operations"))
import asyncpg
from capture_processing_case import capture, save

parser = argparse.ArgumentParser()
parser.add_argument("--database-config", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
cfg = json.loads(args.database_config.read_text())
plan = json.loads((HERE / "config.json").read_text())
manifest = json.loads((HERE / "pg-01/manifest.json").read_text())
assert cfg["host"] == plan["database_host"] and cfg["processing_database"] == plan["database"]
assert not args.output.exists(), "New read-only capture folder required"


async def main():
    connection = await asyncpg.connect(host=cfg["host"], port=cfg["port"], user=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), database=cfg["processing_database"],
        ssl=plan["database_sslmode"], server_settings={"role": cfg["reader"], "default_transaction_read_only": "on"})
    try:
        current = await connection.fetchrow("select current_database() db, current_user role")
        assert dict(current) == {"db": plan["database"], "role": cfg["reader"]}
        tenant, case = UUID(manifest["tenant_id"]), UUID(manifest["case_id"])
        at, data = await capture(connection, tenant, case)
        path, digest, changed = save(args.output, tenant, case, at, data)
        print(json.dumps({"snapshot": str(path), "sha256": digest, "changed": changed,
                          "new_model_calls": 0, "database_writes": 0}))
    finally:
        await connection.close()


asyncio.run(main())
