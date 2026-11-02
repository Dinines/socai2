"""Execute the scoped SQL against duplicate rows; SQLite is not a live CH test."""
import json
import re
import sqlite3
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
from uuid import UUID

from app.investigation_v2 import case_analysis_tools as tools


class CaseLakeDuplicates(IsolatedAsyncioTestCase):
    async def test_duplicate_rows_are_removed_before_limit_in_both_tools(self):
        db = sqlite3.connect(":memory:")
        self.addCleanup(db.close)
        db.create_function("toDateTime64", 3, lambda value, *_: value)
        db.execute("ATTACH DATABASE ':memory:' AS aisoc")
        db.execute("""CREATE TABLE aisoc.raw_events (
          tenant_id TEXT, event_id TEXT, event_time TEXT, ingest_time TEXT, class_uid INTEGER,
          src_hostname TEXT, process_name TEXT, file_path TEXT, hash_sha256 TEXT, user_name TEXT,
          activity_id INTEGER, action TEXT, outcome TEXT, source_ip TEXT, dest_ip TEXT, dst_port INTEGER, protocol TEXT)""")
        tenant = UUID(int=10)
        start = datetime(2026, 11, 1, tzinfo=UTC)
        when = start.strftime("%Y-%m-%d %H:%M:%S.%f")
        for category in (1007, 4001):
            for identity, ingestion, host, scope, occurred in [
                ("one", "1", "h", str(tenant), when), ("one", "2", "h", str(tenant), when),
                ("one", "3", "h", str(tenant), when), ("two", "1", "h", str(tenant), when),
                ("outside-host", "1", "other", str(tenant), when),
                ("outside-tenant", "1", "h", str(UUID(int=11)), when),
                ("outside-time", "1", "h", str(tenant), "2026-10-01 00:00:00.000000")]:
                db.execute("INSERT INTO aisoc.raw_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           (scope, identity, occurred, ingestion, category, host, "p", "/p", "", "alice", 1, ingestion, "", "192.0.2.1", "192.0.2.2", 443, "tcp"))
        async def lake(sql, *, params, **kwargs):
            cursor = db.execute(re.sub(r"%\((\w+)\)s", r":\1", sql), params)
            return SimpleNamespace(columns=[c[0] for c in cursor.description], rows=cursor.fetchall())
        instance = tools.CaseTools(tenant, ["h"], start, start + timedelta(minutes=1))
        with patch.object(tools.settings, "AISOC_DISABLE_CLICKHOUSE", False), patch.object(tools.settings, "CLICKHOUSE_HOST", "unused"), patch.object(tools, "execute_lake_query", side_effect=lake):
            for tool in ("process_activity", "network_connections"):
                result = await instance.execute(tool, {"hostname": "h", "limit": 2})
                self.assertTrue(result["available"], result)
                self.assertEqual([row["event_id"] for row in result["rows"]], ["one", "two"])
                self.assertFalse(result["truncated"])
                if tool == "process_activity":
                    self.assertEqual(result["rows"][0]["action"], "3")
                limited = await instance.execute(tool, {"hostname": "h", "limit": 1})
                self.assertTrue(limited["truncated"])
                self.assertEqual(limited["returned_count"], 1)

    async def test_old_query_contracts_are_not_reused_and_old_semantic_view_still_works(self):
        instance = tools.CaseTools(UUID(int=10), ["h"], datetime.now(UTC), datetime.now(UTC))
        with patch.object(tools.settings, "AISOC_DISABLE_CLICKHOUSE", False), patch.object(tools.settings, "CLICKHOUSE_HOST", "unused"):
            for tool, old in (("process_activity", "case.process_activity.v2"), ("network_connections", None)):
                self.assertFalse(instance.can_reuse(tool, {"query_contract": old}))
                self.assertTrue(instance.can_reuse(tool, {"query_contract": tools.QUERY_CONTRACTS[tool]}))
        view = json.loads(tools.model_result({"tool": "process_activity", "query_contract": "case.process_activity.v2",
            "available": True, "rows": [{"class_uid": 1007, "activity_id": 1}]}))
        self.assertEqual(view["rows"], [{"event_kind": "process_activity"}])
