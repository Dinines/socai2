"""Explicit one-shot A/I direct acceptance; existing isolated database only."""
import argparse
import asyncio
import hashlib
import json
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BATCH = Path(__file__).resolve().parent


async def main(output, config):
    from test_socai2_ai_citation_quality_pg import run_checks

    from tools.testdata.incident_integration.run import connect
    engine = await connect(config)
    try:
        checks = await run_checks(engine, config, output)
        print(json.dumps(checks, ensure_ascii=False))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    assert Path(args.attempt).name == args.attempt
    config = json.loads((BATCH / "config.json").read_text())
    assert config["real_model_calls"] == 0 and config["deployment"] is False
    output = BATCH / args.attempt
    output.mkdir(exist_ok=False)
    os.environ.update(json.loads((ROOT / config["environment_file"]).read_text()))
    os.environ.update(config["runtime_overrides"])
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])
    sys.path[:0] = [str(ROOT / "services/api"), str(ROOT / "services/api/tests"), str(ROOT)]
    sources = [p for p in (ROOT / "services/api/app/socai2").glob("*.py")]
    sources += [ROOT / config["policy"], Path(__file__), BATCH / "config.json",
                ROOT / "services/api/tests/test_socai2_ai_citation_quality_pg.py"]
    (output / "plan.json").write_text(json.dumps({"config": config, "source_sha256": {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}, indent=2) + "\n")
    try:
        asyncio.run(main(output, config))
    except Exception:
        # Preserve the actual failed attempt; never automatically redispatch.
        (output / "failure.txt").write_text(traceback.format_exc())
        raise
