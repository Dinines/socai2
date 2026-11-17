"""Dialect parse plus actual query comparison on SQLite, not live PG/CH."""
import ast
import asyncio
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
from uuid import UUID

import sqlglot
from app.investigation_v2 import case_analysis_tools as current

ROOT = Path(__file__).resolve().parents[4]
old = ModuleType("app.investigation_v2._baseline_tools")
sys.modules[old.__name__] = old
source = subprocess.check_output(["git", "-c", f"safe.directory={ROOT.as_posix()}", "show", "b400fd0:services/api/app/investigation_v2/case_analysis_tools.py"], cwd=ROOT).decode()
exec(compile(source, "baseline_case_analysis_tools.py", "exec"), old.__dict__)


async def main():
    parsed = []
    tree = ast.parse((ROOT / "services/fusion/app/services/alert_sink.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {"_INSERT_SQL", "_DEDUP_SOURCE_EVENT_SQL"} for t in node.targets):
            sqlglot.parse_one(ast.literal_eval(node.value), read="postgres")
            parsed.append(node.targets[0].id)
    db = sqlite3.connect(":memory:")
    db.create_function("toDateTime64", 3, lambda v, *_: v)
    db.execute("ATTACH DATABASE ':memory:' AS aisoc")
    db.execute("""CREATE TABLE aisoc.raw_events (tenant_id TEXT,event_time TEXT,class_uid INTEGER,event_id TEXT,ingest_time TEXT,
        src_hostname TEXT,process_name TEXT,file_path TEXT,hash_sha256 TEXT,user_name TEXT,activity_id INTEGER,action TEXT,outcome TEXT,
        source_ip TEXT,dest_ip TEXT,dst_port INTEGER,protocol TEXT)""")
    tenant, start = UUID(int=10), datetime(2026, 11, 1, tzinfo=UTC)
    for category in (1007, 4001):
        for identity, ingestion in (("one", "1"), ("one", "2"), ("one", "3"), ("two", "1")):
            db.execute("INSERT INTO aisoc.raw_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (str(tenant), "2026-11-01 00:00:00.000000", category, identity, ingestion, "host", "p", "/p", "", "user", 1, ingestion, "", "192.0.2.1", "192.0.2.2", 443, "tcp"))
    sql_calls = []
    async def query(sql, *, params, **kwargs):
        sqlglot.parse_one(re.sub(r"%\((\w+)\)s", r"'\1'", sql), read="clickhouse")
        sql_calls.append(sql)
        result = db.execute(re.sub(r"%\((\w+)\)s", r":\1", sql), params)
        return SimpleNamespace(columns=[c[0] for c in result.description], rows=result.fetchall())
    comparisons = []
    with patch.object(current.settings, "AISOC_DISABLE_CLICKHOUSE", False), patch.object(current.settings, "CLICKHOUSE_HOST", "unused"):
        for name in current.DESCRIPTIONS:
            pair = {}
            for label, module in (("before", old), ("after", current)):
                with patch.object(module, "execute_lake_query", side_effect=query):
                    result = await module.CaseTools(tenant, ["host"], start, start + timedelta(minutes=1)).execute(name, {"hostname": "host", "limit": 2})
                assert result["available"], result
                pair[label] = {"ids": [row["event_id"] for row in result["rows"]], "truncated": result["truncated"]}
            assert pair["before"]["ids"] == ["one", "one"] and pair["after"]["ids"] == ["one", "two"]
            assert pair["before"]["truncated"] and not pair["after"]["truncated"]
            comparisons.append({"tool": name, **pair})
    db.close()
    output = {"postgres_dialect_parsed": parsed, "clickhouse_dialect_parsed": len(sql_calls),
              "scope": "SQLite query execution with identical synthetic rows; dialect parser is not deployed database validation", "comparisons": comparisons}
    Path(__file__).with_name("sql-validation.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PG insert/update and four CH SQL statements parsed; both tools: duplicate rows -> distinct rows before limit")


asyncio.run(main())
