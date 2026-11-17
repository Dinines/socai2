"""Run the bounded lifecycle PG suite using an explicit existing local validation profile."""
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

from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[2]


async def run(args):
    cfg = json.loads(Path(args.profile).read_text())
    password = Path(cfg["password_file"]).read_text().strip()
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", cfg["processor"]):
        raise ValueError("invalid configured processor role")
    if cfg["host"] not in {"127.0.0.1", "localhost"}:
        raise ValueError("this verification entry is local only")
    out = Path(args.output)
    if out.exists():
        raise ValueError("receipt already exists; use a new batch")
    out.parent.mkdir(parents=True, exist_ok=True)
    os.environ.update(json.loads(Path(args.environment_file).read_text()))
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(Path(args.investigation_policy).resolve(strict=True))
    sys.path[:0] = [str(ROOT / "services/api"), str(ROOT / "services/api/tests")]
    from test_socai2_analysis_tasks_pg import run_checks

    url = URL.create("postgresql+psycopg", username=cfg["admin"], password=password,
        host=cfg["host"], port=cfg["port"], database=cfg["processing_database"])
    engine = create_async_engine(url, hide_parameters=True,
        connect_args={"sslmode": "disable", "options": "-c role=" + cfg["processor"]})
    paths = list((ROOT / "services/api/app/socai2").glob("analysis_task*.py")) + [
        ROOT / "services/api/app/models/socai2.py", ROOT / "services/api/tests/test_socai2_analysis_tasks_pg.py",
        ROOT / "services/api/tests/test_socai2_case_adoption_pg.py",
        ROOT / "services/api/migrations/128_socai2_analysis_lifecycle.sql", Path(__file__)]
    paths += [ROOT / "services/api/app/socai2" / name for name in ("baseline_store.py", "baseline_service.py",
        "case_management.py", "case_management_contracts.py", "case_reader.py", "case_adoption.py", "case_adoption_contracts.py")]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    checks = []

    def record(name, passed, detail=None):
        checks.append({"name": name, "passed": passed, "detail": detail})
        print(name, "PASS" if passed else "FAIL", flush=True)

    try:
        async with engine.connect() as db:
            assert (await db.execute(text("SELECT current_database(),current_user"))).one() == (
                cfg["processing_database"], cfg["processor"])
        await run_checks(engine, record)
    except Exception:  # noqa: BLE001 -- retain a sanitized failed validation receipt
        record("lifecycle_execution", False, traceback.format_exc().replace(password, "[REDACTED]"))
    finally:
        await engine.dispose()
        out.write_text(json.dumps({"time": datetime.now(UTC).isoformat(), "database": cfg["processing_database"],
            "host": cfg["host"], "port": cfg["port"], "runtime_role": cfg["processor"],
            "mode": "real_PG_synthetic_records_no_model_no_HTTP", "real_model_calls": 0,
            "deployed": False, "source_sha256": hashes,
            "changed_during_run": [str(p.relative_to(ROOT)) for p in paths
                if hashes[str(p.relative_to(ROOT))] != hashlib.sha256(p.read_bytes()).hexdigest()],
            "checks": checks}, ensure_ascii=False, indent=2, default=str) + "\n")
    print(str(out))
    return 0 if checks and all(c["passed"] for c in checks) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--environment-file", required=True)
    parser.add_argument("--investigation-policy", required=True)
    parser.add_argument("--output", required=True)
    raise SystemExit(asyncio.run(run(parser.parse_args())))
