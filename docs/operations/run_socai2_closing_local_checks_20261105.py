"""Bounded local PG checks in isolated test tenants; no model or lake network calls."""
import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / p) for p in ("deploy/local-investigation", "services/api", "services/api/tests")]

from config import API_ROLE, DATABASE, read_private
from initialize import pg_connect, safe_error
from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import create_async_engine
from test_socai2_baseline_executor import run_checks


async def main(names):
    values, results = read_private(), []
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = ROOT / "docs/operations/evidence/investigation-repair-20261105" / (stamp + "-local-c6-closing.json")
    conn = await pg_connect(values)
    try:
        assert await conn.fetchval("SELECT current_database()") == DATABASE
        for number in (1, 2):
            identity = UUID(int=number)
            name = "socai2-c6-test-" + str(number)
            existing = await conn.fetchrow("SELECT name,slug FROM public.tenants WHERE id=$1", identity)
            assert existing is None or dict(existing) == {"name": name, "slug": name}, "test tenant identity collision"
            await conn.execute("""INSERT INTO public.tenants
                (id,name,slug,plan,is_active,settings,limits,created_at,updated_at)
                VALUES($1,$2,$2,'enterprise',true,'{}','{}',now(),now()) ON CONFLICT(id) DO NOTHING""", identity, name)
        existing = await conn.fetchrow("SELECT tenant_id,email FROM public.users WHERE id=$1", UUID(int=3))
        assert existing is None or dict(existing) == {"tenant_id": UUID(int=1), "email": "c6-test@local.invalid"}
        await conn.execute("""INSERT INTO public.users
            (id,tenant_id,email,username,hashed_password,role,is_active,is_verified,preferences,created_at,updated_at)
            VALUES($1,$2,'c6-test@local.invalid','C6 test','!disabled-no-api-key','soc_admin',true,true,'{}',now(),now())
            ON CONFLICT(id) DO NOTHING""", UUID(int=3), UUID(int=1))
    finally:
        await conn.close()
    engine = create_async_engine(URL.create("postgresql+asyncpg", username=API_ROLE,
        password=values["API_DB_PASSWORD"], host="127.0.0.1", port=15432, database=DATABASE),
        connect_args={"ssl": False}, hide_parameters=True, pool_size=3, max_overflow=1)
    def record(name, passed, detail):
        item = {"name": name, "passed": passed, "detail": detail}
        results.append(item)
        destination.write_text(json.dumps({"database": DATABASE, "real_pg": True,
            "model_and_lake": "substitutes", "results": results}, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"check": name, "passed": passed, "detail": detail if passed else str(detail)[-1700:]}, ensure_ascii=False), flush=True)
    try:
        async with engine.connect() as db:
            assert (await db.execute(text("SELECT current_database()"))).scalar_one() == DATABASE
        await run_checks(engine, record, only=set(names) if names else None)
    except Exception as exc:  # noqa: BLE001 -- only sanitized local test diagnostics
        print(safe_error(exc, values), flush=True)
        return 1
    finally:
        await engine.dispose()
    print(json.dumps({"receipt": str(destination), "passed": sum(r["passed"] for r in results), "total": len(results)}))
    return 0 if results and all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", action="append", default=[])
    raise SystemExit(asyncio.run(main(parser.parse_args().only)))
