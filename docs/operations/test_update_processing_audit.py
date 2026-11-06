"""Regression checks for appending and refreshing scoped offline test records."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from update_processing_audit import existing, update


class AuditHistoryTest(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.out = self.root / "site"

    def batch(self, name, started):
        folder = self.root / name
        snapshot = folder / "readback" / "m01"
        snapshot.mkdir(parents=True)
        data = {
            "cases": [{"id": name, "title": "同名案例"}],
            "artifacts": [],
            "runs": [{"id": name, "case_id": name, "kind": "baseline", "started_at": started,
                      "requested_at": "2026-11-06T01:00:00Z", "state": "unknown" if started else "pending"}],
            "run_steps": [],
        }
        (snapshot / "database.json").write_text(json.dumps(data), encoding="utf-8")
        return folder

    def test_same_key_in_another_batch_appends_and_reimport_is_stable(self):
        first = self.batch("test-a", "2026-11-06T06:00:00Z")
        later = self.batch("test-b", "2026-11-07T06:00:00Z")
        update([first], self.out)
        update([later], self.out)
        index = self.out / "index.html"
        page = index.read_bytes()
        rows = list(existing(index).values())
        self.assertEqual([r["batch"] for r in rows], ["test-b", "test-a"])
        self.assertEqual([r["key"] for r in rows], ["m01", "m01"])
        self.assertNotEqual(rows[0]["detail"], rows[1]["detail"])
        for row in rows:
            self.assertIn(row["batch"], (self.out / row["detail"]).read_text(encoding="utf-8"))
        update([later], self.out)
        self.assertEqual(page, index.read_bytes())
        self.assertEqual(len(list((self.out / "cases").glob("*.html"))), 2)

    def test_pending_is_preserved_and_a_regressing_snapshot_keeps_the_previous_page(self):
        batch = self.batch("pending", None)
        update([batch], self.out)
        index = self.out / "index.html"
        row, = existing(index).values()
        self.assertIsNone(row["started_at"])
        self.assertEqual(row["state"], "pending")
        page = index.read_bytes()
        path = batch / "readback/m01/database.json"
        data = json.loads(path.read_bytes())
        data["runs"] = []
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "replace history"):
            update([batch], self.out)
        self.assertEqual(page, index.read_bytes())

    def test_source_checksum_failure_leaves_no_published_index(self):
        batch = self.batch("broken", None)
        (batch / "readback/files.sha256.json").write_text('{"m01/database.json":"bad"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            update([batch], self.out)
        self.assertFalse((self.out / "index.html").exists())

    def test_recent_pending_round_and_older_capture(self):
        batch = self.batch("case-one", "2026-11-06T06:00:00Z")
        snapshot = batch / "readback"
        file = snapshot / "m01/database.json"
        data = json.loads(file.read_bytes())
        data["runs"].append({"id": "next-round", "case_id": "case-one", "kind": "baseline",
                             "requested_at": "2026-11-07T09:10:00Z", "state": "pending_update"})
        file.write_text(json.dumps(data), encoding="utf-8")
        summary = snapshot / "summary.json"
        summary.write_text('{"snapshot":{"at":"2026-11-07T10:00:00Z"}}', encoding="utf-8")
        update([batch], self.out)
        index = self.out / "index.html"
        row, = existing(index).values()
        self.assertEqual(row["state"], "pending_update")
        previous = index.read_bytes()
        summary.write_text('{"snapshot":{"at":"2026-11-07T09:40:00Z"}}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "replace history"):
            update([batch], self.out)
        self.assertEqual(index.read_bytes(), previous)
