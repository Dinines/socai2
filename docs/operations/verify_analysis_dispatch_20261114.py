"""One retained PG/Redis dispatcher validation batch, using explicit local profiles."""
import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path

from redis.asyncio import Redis
from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[2]


async def run(args):
    cfg = json.loads(Path(args.profile).read_text())
    dispatch = json.loads(Path(args.dispatch_profile).read_text())
    password = Path(cfg["password_file"]).read_text().strip()
    if cfg["host"] not in {"localhost", "127.0.0.1"} or dispatch["bind_host"] != "127.0.0.1":
        raise ValueError("local validation only")
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", cfg["processor"]):
        raise ValueError("invalid role")
    out = Path(args.output)
    if out.exists():
        raise ValueError("receipt already exists; use a new batch")
    out.parent.mkdir(parents=True, exist_ok=True)
    os.environ.update(json.loads(Path(args.environment_file).read_text()))
    sys.path[:0] = [str(ROOT / "services/api"), str(ROOT / "services/api/tests")]
    from test_socai2_analysis_dispatch_pg import run_checks

    url = URL.create("postgresql+psycopg", username=cfg["admin"], password=password,
        host=cfg["host"], port=cfg["port"], database=cfg["processing_database"])
    admin = create_async_engine(url, hide_parameters=True, connect_args={"sslmode": "disable"},
        pool_size=dispatch["database_pool_size"], max_overflow=0)
    engine = create_async_engine(url, hide_parameters=True,
        connect_args={"sslmode": "disable", "options": "-c role=" + cfg["processor"]},
        pool_size=dispatch["database_pool_size"], max_overflow=0)
    redis = Redis(host=dispatch["bind_host"], port=dispatch["redis_port"],
        socket_timeout=dispatch["redis_socket_timeout_seconds"],
        socket_connect_timeout=dispatch["redis_connect_timeout_seconds"])
    paths = list((ROOT / "services/api/app/socai2").glob("analysis_*.py")) + [
        ROOT / "services/api/tests/test_socai2_analysis_dispatch_pg.py",
        ROOT / "deploy/local-investigation/analysis-tasks.json", Path(__file__)]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    checks = []

    def record(name, passed, detail=None):
        checks.append({"name": name, "passed": passed, "detail": detail})
        print(name, "PASS" if passed else "FAIL", flush=True)

    try:
        async with engine.connect() as db:
            assert (await db.execute(text("select current_database(),current_user"))).one() == (
                cfg["processing_database"], cfg["processor"])
        assert await redis.ping()
        await run_checks(engine, admin, redis, dispatch, record)
    except Exception:  # noqa: BLE001 -- preserve failed batches; credentials are never retained
        record("dispatch_execution", False, traceback.format_exc().replace(password, "[REDACTED]"))
    finally:
        await redis.aclose()
        await engine.dispose()
        await admin.dispose()
        out.write_text(json.dumps({"time": datetime.now(UTC).isoformat(), "database": cfg["processing_database"],
            "host": cfg["host"], "port": cfg["port"], "runtime_role": cfg["processor"],
            "mode": "real_PG_and_isolated_Redis_controlled_executor_and_clock", "real_model_calls": 0,
            "deployed": False, "redis_binding": [dispatch["bind_host"], dispatch["redis_port"]],
            "redis_namespace": dispatch["namespace"], "source_sha256": hashes,
            "changed_during_run": [str(p.relative_to(ROOT)) for p in paths
                if hashes[str(p.relative_to(ROOT))] != hashlib.sha256(p.read_bytes()).hexdigest()],
            "checks": checks}, ensure_ascii=False, indent=2, default=str) + "\n")
    print(str(out))
    return 0 if checks and all(c["passed"] for c in checks) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--dispatch-profile", required=True)
    parser.add_argument("--environment-file", required=True)
    parser.add_argument("--output", required=True)
    raise SystemExit(asyncio.run(run(parser.parse_args())))
