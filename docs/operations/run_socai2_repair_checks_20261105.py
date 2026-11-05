"""Mac SSH adapter for the existing restricted synthetic PostgreSQL checks.

Only the existing socai2_schema_review_20261103_a1 database is used. The
historical runner still creates/removes the ephemeral restricted role and SSH
tunnel. No model, lake, business database, deployment or historical Run replay.
"""
import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure(suite, selected):
    runner = load_module("socai2_repair_existing_runner", Path(__file__).with_name("verify_socai2_store_20261103.py"))
    runner.SSH = ["ssh", "-o", "StrictHostKeyChecking=yes", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8"]
    runner.DEST = "sting-infra21"
    # Reuse case_http's restricted grants for the new queue suite.
    runner.SUITE = "case_http" if suite == "case_queue" else suite
    runner.SELECTED = selected
    runner.STAMP = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    runner.EVIDENCE = ROOT / "docs/operations/evidence/investigation-repair-20261105" / f"{runner.STAMP}-{suite}"
    original_save = runner.save
    initial_hashes = None
    extra_paths = [Path(__file__), ROOT / "services/api/tests/test_socai2_case_queue_pg.py",
        ROOT / "services/api/tests/test_socai2_case_queue.py", ROOT / "services/api/app/models/socai2.py"]
    extra_paths += sorted((ROOT / "services/api/app/socai2").glob("case_*.py"))

    def save():
        nonlocal initial_hashes
        original_save()
        path = runner.EVIDENCE / "receipt.json"
        receipt = json.loads(path.read_text("utf-8"))
        receipt["hashes"].update({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in extra_paths})
        if initial_hashes is None:
            initial_hashes = dict(receipt["hashes"])
        receipt.update(suite=suite, selected=selected, ssh_alias="sting-infra21",
            runner_scope="existing isolated PostgreSQL, synthetic fixtures, local application code",
            real_model_calls=0, real_lake_queries=0, deployed=False,
            source_hashes_at_start=initial_hashes,
            source_files_changed_during_run=[name for name, digest in receipt["hashes"].items()
                if initial_hashes.get(name) != digest])
        path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", "utf-8")

    runner.save = save
    if suite == "case_queue":
        async def queue_exercise(port, role, password):
            sys.path.insert(0, str(ROOT / "services/api"))
            sys.path.insert(0, str(ROOT / "services/api/tests"))
            module = load_module("socai2_queue_pg_checks", ROOT / "services/api/tests/test_socai2_case_queue_pg.py")
            engine = create_async_engine(URL.create("postgresql+asyncpg", username=role, password=password,
                host="127.0.0.1", port=port, database=runner.DATABASE), pool_size=4, max_overflow=0,
                connect_args={"timeout": 10, "server_settings": {"statement_timeout": "12000"}})
            try:
                await module.run_checks(engine, runner.record, only=selected)
                executed = {item["name"] for item in runner.OBSERVATIONS if item["name"].startswith("test_")}
                if not executed or (selected and executed != set(selected)):
                    runner.record("requested_checks_not_executed", False,
                        {"requested": selected, "executed": sorted(executed)})
            finally:
                await engine.dispose()
        runner.exercise = queue_exercise
    return runner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=["case_queue", "executor", "human_tasks"], required=True)
    parser.add_argument("--only", nargs="+")
    args = parser.parse_args()
    runner = configure(args.suite, args.only)
    runner.save()
    try:
        return runner.main()
    except Exception as exc:  # noqa: BLE001 -- retain failure without ephemeral connection details
        runner.record("repair_runner_error", False, {"exception_type": type(exc).__name__})
        print(str(runner.EVIDENCE / "receipt.json"))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
