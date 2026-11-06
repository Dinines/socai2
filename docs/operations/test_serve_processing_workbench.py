"""Exercise the local refresh endpoints without contacting a database."""
import http.client
import json
import threading
import unittest
from datetime import datetime, timedelta, timezone
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

import serve_processing_workbench as web
from read_processing_audit_20261106 import TABLES


class WorkbenchTest(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.app = web.Workbench("21", uuid4(), root / "site", root / "captures")
        self.app.output.mkdir()
        (self.app.output / "index.html").write_bytes(web.site.registry_html({}, self.app.output, []))
        self.case = uuid4()

    def start_http(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(web.Handler, app=self.app))
        self.addCleanup(server.server_close)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        self.port = server.server_port
        self.origin = "http://127.0.0.1:" + str(self.port)

    def request(self, method, path, headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            return response.status, response.read()
        finally:
            conn.close()

    def test_browser_source_is_fixed_and_cross_origin_reads_and_updates_rejected(self):
        self.start_http()
        path = "/_workbench/refresh"
        case = {"case_id": str(self.case)}
        with patch.object(self.app, "refresh", return_value=case) as read:
            for origin in (None, "null", "http://other.example", "http://localhost:999"):
                headers = {"Content-Type": "application/json"}
                if origin:
                    headers["Origin"] = origin
                self.assertEqual(403, self.request("POST", path, headers, json.dumps(case))[0])
            good = {"Content-Type": "application/json", "Origin": self.origin}
            self.assertEqual(400, self.request("POST", path, good, json.dumps({**case, "database": "other"}))[0])
            self.assertEqual(415, self.request("POST", path, {"Origin": self.origin}, json.dumps(case))[0])
            self.assertEqual(403, self.request("GET", "/_workbench/cases", {"Host": "outside.example"})[0])
            self.assertEqual(403, self.request("GET", "/", {"Host": "outside.example"})[0])
            read.assert_not_called()
            self.assertEqual(200, self.request("POST", path, good, json.dumps(case))[0])
            read.assert_called_once_with(self.case)

    def test_listing_passes_cursor_and_handles_source_busy_or_unavailable(self):
        self.start_http()
        with patch.object(web.source_db, "list_cases", return_value={"cases": [], "next_cursor": None}) as page:
            status, body = self.request("GET", "/_workbench/cases?cursor=page2")
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body), {"cases": [], "next_cursor": None})
            page.assert_called_once_with("21", self.app.tenant, "page2")
            with self.app.reading_list:
                self.assertEqual(409, self.request("GET", "/_workbench/cases")[0])
            page.side_effect = RuntimeError("password-must-never-escape")
            status, body = self.request("GET", "/_workbench/cases")
            self.assertEqual(503, status)
            self.assertNotIn(b"password", body)

    def test_revision_skips_unchanged_export_even_after_restart_and_replaces_previous_files(self):
        tenant = self.app.tenant
        data = {t: [] for t in TABLES}
        case = str(self.case)
        data["cases"] = [{"id": case, "tenant_id": str(tenant), "title": "第一轮"}]
        at = datetime.now(timezone.utc)
        with patch.object(web.source_db, "read_case_if_changed") as read:
            read.return_value = (at, data, "rev1")
            first = self.app.refresh(self.case)
            self.assertTrue(first["changed"])
            first_detail = self.app.output / first["record"]["detail"]
            self.assertTrue(first_detail.is_file())
            restarted = web.Workbench("21", tenant, self.app.output, self.app.captures)
            read.return_value = (at, None, "rev1")
            with patch.object(web, "save", side_effect=AssertionError("unchanged record was exported")):
                second = restarted.refresh(self.case)
            self.assertEqual(first, {**second, "changed": True})
            read.assert_called_with("21", tenant, self.case, "rev1")
            data["cases"][0]["title"] = "第二轮"
            read.return_value = (at + timedelta(seconds=1), data, "rev2")
            updated = restarted.refresh(self.case)
            self.assertNotEqual(first["version"], updated["version"])
            self.assertTrue((self.app.output / updated["record"]["detail"]).is_file())
            self.assertFalse(first_detail.exists())
            self.assertEqual(1, len(list(self.app.captures.rglob("database.json"))))


if __name__ == "__main__":
    unittest.main()
