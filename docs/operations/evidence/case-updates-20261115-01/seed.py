"""Create new isolated sources using the existing fixture; no Case or analysis task."""
import argparse
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from validate7a import HERE, environment, initial_fixture

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--batch", required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    environment(config)
    initial_fixture.HERE = HERE
    asyncio.run(initial_fixture.main(SimpleNamespace(batch=args.batch, seed_only=True), config))
