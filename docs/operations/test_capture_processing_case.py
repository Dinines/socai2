"""Regression checks for the read-only live capture and its restartable workbench output."""
import asyncio
import hashlib
import json
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import capture_processing_case as live
from read_processing_audit_20261106 import ROOT, query_for


class ReadOnlyConnection:
    def __init__(self, data, at):
        self.data, self.at = data, at
        self.queries = []
        self.settings = None
        self.tenant = None
        self.rls = True

    @asynccontextmanager
    async def transaction(self, **settings):
        self.settings = settings
        yield

    async def execute(self, sql, tenant):
        assert sql == "SELECT set_config('app.current_tenant_id',$1,true)"
        self.tenant = tenant

    async def fetchrow(self, sql, tenant, case):
        assert sql == live.SCOPE and str(tenant) == self.tenant and str(case) == self.data["cases"][0]["id"]
        return {"captured_at": self.at, "alerts": [], "incidents": [], "stages": []}

    async def fetchval(self, sql, tenant, *args):
        assert str(tenant) == self.tenant
        if sql == live.RLS:
            assert args == (list(live.TABLES),)
            return self.rls
        table = live.TABLES[len(self.queries)]
        assert sql == live.case_query(table)
        self.queries.append(sql)
        return json.dumps(self.data[table])

    async def close(self, **kwargs):
        pass


class CaseCaptureTest(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.folder = self.root / "capture"
        self.site = self.root / "site"
        self.tenant, self.case = uuid4(), uuid4()
        self.at = datetime.now(timezone.utc)
        self.data = {t: [] for t in live.TABLES}
        self.data["cases"] = [{"id": str(self.case), "tenant_id": str(self.tenant), "title": "运行中"}]

    def save(self, at=None):
        return live.save(self.folder, self.tenant, self.case, at or self.at, self.data)

    def test_queries_use_rls_and_one_readonly_transaction(self):
        conn = ReadOnlyConnection(self.data, self.at)
        at, data = asyncio.run(live.capture(conn, self.tenant, self.case))
        self.assertEqual((at, data), (self.at, self.data))
        self.assertEqual(conn.settings, {"isolation": "repeatable_read", "readonly": True})
        self.assertEqual(len(conn.queries), 29)
        conn.rls = False
        with self.assertRaisesRegex(ValueError, "read-only tenant RLS"):
            asyncio.run(live.capture(conn, self.tenant, self.case))
        self.assertEqual(len(conn.queries), 29)

    def test_pilot_driver_retains_verified_file_and_queries(self):
        driver = ROOT / "deploy/local-investigation/flow_export.py"
        # 21's deployed_matrix_host verifies the raw helper bytes before loading it.
        self.assertEqual(hashlib.sha256(driver.read_bytes()).hexdigest(),
                         "320e6d19dd384ee66b013629e80fc875fb6ea8fdb48c796d7b997c0519b65e0e")
        original = hashlib.sha256(b"\0".join(query_for(t).encode() for t in live.TABLES))
        self.assertEqual(original.hexdigest(), "58e783fb4a12e6d6bc4691aa89582987a56ad9a277c6644d6cf57a30eccd3569")

    def test_case_selectors_support_multiple_incidents(self):
        queries = hashlib.sha256(b"\0".join(live.case_query(t).encode() for t in live.TABLES))
        self.assertEqual(queries.hexdigest(), "b0565c622a1b31748b53fa2ca21a728967b05598c49dc735f9ec16e6ed2f5d62")
        for t in ("incidents", "incident_alerts", "incident_diagnoses", "artifacts", "activities", "activity_targets",
                  "comments", "response_links"):
            sql = live.case_query(t)
            self.assertIn("=ANY(s.incident)", sql)
            self.assertIn("t.tenant_id=s.tenant", sql)
        self.assertIn("t.alert_id=ANY(s.aids)", live.case_query("alert_assessments"))
        self.assertIn(" AND (t.case_id", live.case_query("activity_targets"))

    def test_same_state_once_and_running_step_appears_on_next_capture(self):
        a, sha, created = self.save()
        self.assertTrue(created)
        self.assertEqual(self.save(self.at + timedelta(seconds=1)), (a, sha, False))
        rid = str(uuid4())
        self.data["runs"] = [{"id": rid, "tenant_id": str(self.tenant), "case_id": str(self.case), "kind": "baseline",
                              "started_at": self.at.isoformat(), "state": "running"}]
        self.data["run_steps"] = [{"id": str(uuid4()), "tenant_id": str(self.tenant), "run_id": rid,
                                   "seq": 1, "stage_code": "C3", "kind": "model", "state": "running"}]
        b, new_sha, created = self.save(self.at + timedelta(seconds=2))
        self.assertTrue(created)
        self.assertNotEqual(sha, new_sha)
        self.assertEqual(json.loads((a / "database.json").read_bytes())["run_steps"], [])
        self.assertEqual(live.importer.import_folder(self.folder, self.site), (1, 1))
        manifest = json.loads((b / "manifest.json").read_bytes())
        self.assertEqual((manifest["source_environment"], manifest["input_kind"]), ("processing", "investigation"))
        saved, = live.site.existing(self.site / "index.html").values()
        self.assertEqual((saved["scope_id"], saved["state"], saved["steps"]), (str(self.case), "running", 1))

    def test_invalid_scope_or_credentials_can_never_become_a_snapshot(self):
        self.data["cases"][0]["title"] = '{"api_key":"example-credential"}'
        with self.assertRaisesRegex(ValueError, "credential"):
            self.save()
        self.assertFalse(self.folder.exists())
        self.data["cases"][0]["title"] = "正常"
        self.save()
        self.case = uuid4()
        self.data["cases"][0]["id"] = str(self.case)
        with self.assertRaisesRegex(ValueError, "folder belongs"):
            self.save(self.at + timedelta(seconds=1))
        self.assertEqual(len(list((self.folder / "exports").iterdir())), 1)

    def test_publish_retry_after_site_failure_without_duplicate_capture(self):
        args = SimpleNamespace(tenant=self.tenant, case=self.case, folder=self.folder, site=self.site, follow=None)
        connect = AsyncMock(side_effect=lambda *a, **k: ReadOnlyConnection(self.data, self.at))
        with patch.dict(live.os.environ, SOCAI2_AUDIT_DATABASE_URL="postgresql://fixture/db"), patch.object(
            live.asyncpg, "connect", connect,
        ):
            with patch.object(live.importer, "import_folder", side_effect=OSError), self.assertRaises(OSError):
                asyncio.run(live.collect(args))
            self.assertFalse(self.site.exists())
            asyncio.run(live.collect(args))
        self.assertEqual(len(list((self.folder / "exports").iterdir())), 1)
        self.assertEqual(len(live.site.existing(self.site / "index.html")), 1)

    def test_real_stored_three_subject_snapshot_has_all_29_tables_and_rows(self):
        original = Path(__file__).with_name("evidence") / "ie-audit-20261106-a1/readback/s02/database.json"
        data = json.loads(original.read_bytes())
        case, = data["cases"]
        folder, _, _ = live.save(self.folder, UUID(case["tenant_id"]), UUID(case["id"]), self.at, data)
        self.assertEqual(json.loads((folder / "database.json").read_bytes()), data)
        self.assertEqual(len(data["alerts"]), 2)
        self.assertEqual(len(data["incidents"]), 1)
