"""Read-only HTTP check of an ended F4 retry guard sample using its explicit private profile."""
import argparse
import asyncio
import importlib
import json
import os
import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[4]


async def main(args):
    config = json.loads(args.config.read_text())
    database = json.loads(Path(config["database_profile"]).read_text())
    assert database["processing_database"] == "v12_upgrade_dev"
    os.environ.update(json.loads(Path(config["environment_file"]).read_text()))
    os.environ.update(config["runtime_overrides"])
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = config["investigation_policy_file"]
    os.environ["SOCAI2_ANALYSIS_TASKS_CONFIG_FILE"] = config["lifecycle_policy_file"]
    os.environ["SOCAI2_CASE_ALLOCATION_CONFIG_FILE"] = config["allocation_policy_file"]
    policy = tomllib.loads(Path(config["investigation_policy_file"]).read_text())
    os.environ["AISOC_AGENTS_LLM_CONTRACT_MAX_CHARS"] = str(policy["model"]["max_prepared_bytes"])
    config["http_limits_file"] = str(ROOT / "deploy/http-service/run-records.json")
    sys.path[:0] = [str(ROOT / "services/api"), str(ROOT / "services/api/tests")]
    from sqlalchemy import URL
    from sqlalchemy.ext.asyncio import create_async_engine

    module = importlib.import_module("test_socai2_case_retry_guard_http_pg")
    hashes = module.source_hashes(ROOT, args.source)
    assert not args.output.exists(), "Use a new receipt path; preserve earlier results"
    url = URL.create("postgresql+psycopg", username=database["admin"],
        password=Path(database["password_file"]).read_text().strip(), host=database["host"],
        port=database["port"], database=database["processing_database"])
    engine = create_async_engine(url, hide_parameters=True, connect_args={
        "sslmode": config["sslmode"],
        "options": "-c role=" + database["processor"] + " -c default_transaction_read_only=on"})
    try:
        result = await module.run_checks(engine, args.source, config)
    finally:
        await engine.dispose()
    result.update(database_endpoint={"host": database["host"], "port": database["port"], "database": database["processing_database"]}, transport="ASGI_real_isolated_PG_readonly", source_hashes=hashes,
                  verification_config="explicit_private_F4_profile", model_execution="none")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, default=str)
    print(json.dumps({"state": result["state"], "http_requests": result["http_requests"],
                      "receipt": str(args.output), "checks": result["checks"]}, ensure_ascii=False))
    assert result["state"] == "passed", "See saved HTTP receipt; no task was re-executed"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(main(parser.parse_args()))
