"""Render a new lake schema or apply registered migrations with an explicit profile."""

import argparse
import asyncio
from pathlib import Path

from app.db.lake_schema import create_table_sql, load_policy


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path, help="render only; no database connection")
    mode.add_argument("--apply", action="store_true", help="migrate an initialized lake selected by runtime settings")
    args = parser.parse_args()
    if args.output:
        policy = load_policy(args.profile)
        args.output.write_text(f"CREATE DATABASE IF NOT EXISTS {policy.database};\n" + create_table_sql(policy))
    else:
        from app.core.config import settings
        from app.db.clickhouse import (
            close_clickhouse,
            get_clickhouse_client,
        )
        from app.db.lake_migrations import run_migrations

        policy = load_policy(args.profile, database=settings.CLICKHOUSE_DATABASE)

        async def apply() -> None:
            try:
                await run_migrations(await get_clickhouse_client(), policy=policy)
            finally:
                await close_clickhouse()

        asyncio.run(apply())


if __name__ == "__main__":
    main()
