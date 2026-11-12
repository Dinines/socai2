"""Checks for the investigator's local folder importer."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

import processing_audit_import as importer


class FolderImportTest(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "folder"
        self.output = self.root / "site"
        self.tenant, self.alert = str(uuid4()), str(uuid4())

    def capture(self, folder=None):
        folder = folder or self.source
        folder.mkdir(parents=True)
        data = {key: [] for key in importer.TABLES}
        data["alerts"] = [{"tenant_id": self.tenant, "id": self.alert, "title": "Standalone alert"}]
        manifest = {"schema_version": "socai2.page-export.v1", "batch_id": "capture01", "tenant_id": self.tenant,
                    "exported_at": "2026-11-06T12:00:00Z", "case_id": None}
        self.save(folder, manifest, data)
        return manifest, data

    def save(self, folder, manifest, data):
        body = json.dumps(data).encode()
        manifest.update(sources=[{"file": "database.json", "sha256": importer.site.sha(body)}],
                        table_counts={key: len(rows) for key, rows in data.items()})
        (folder / "database.json").write_bytes(body)
        (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def test_standalone_subject_and_idempotent_update(self):
        self.capture()
        before = {p: p.read_bytes() for p in self.source.iterdir()}
        self.assertEqual(importer.import_folder(self.source, self.output), (1, 1))
        index = self.output / "index.html"
        saved = index.read_bytes()
        self.assertEqual(importer.import_folder(self.source, self.output), (1, 1))
        self.assertEqual(index.read_bytes(), saved)
        self.assertEqual(before, {p: p.read_bytes() for p in self.source.iterdir()})
        self.assertEqual(next(importer.folder_cases(self.source))[2], self.alert)

    def test_legacy_graph_collection_preserved_and_unknown_tables_rejected(self):
        manifest, data = self.capture()
        cid = str(uuid4())
        data["cases"] = [{"tenant_id": self.tenant, "id": cid}]
        data["graph_explorations"] = [{"tenant_id": self.tenant, "id": str(uuid4()), "case_id": cid}]
        counts = {key: len(rows) for key, rows in data.items()}
        before = json.dumps(data)
        importer.checked_rows(data, self.tenant, counts)
        self.assertEqual(json.dumps(data), before)
        data["unknown_table"] = []
        with self.assertRaisesRegex(ValueError, "database tables"):
            importer.checked_rows(data, self.tenant, counts)

    def test_incomplete_credential_and_foreign_snapshot_leave_index_intact(self):
        manifest, data = self.capture()
        importer.import_folder(self.source, self.output)
        previous = (self.output / "index.html").read_bytes()
        data["alerts"][0]["raw"] = json.dumps({"password": "do-not-publish"})
        self.save(self.source, manifest, data)
        with self.assertRaisesRegex(ValueError, "possible credential"):
            importer.import_folder(self.source, self.output)
        del data["alerts"][0]["raw"]
        data["run_steps"].append({"id": str(uuid4()), "run_id": str(uuid4()), "tenant_id": self.tenant})
        self.save(self.source, manifest, data)
        with self.assertRaisesRegex(ValueError, "outside snapshot"):
            importer.import_folder(self.source, self.output)
        data.pop("run_steps")
        self.save(self.source, manifest, data)
        with self.assertRaisesRegex(ValueError, "29 database tables"):
            importer.import_folder(self.source, self.output)
        self.assertEqual(previous, (self.output / "index.html").read_bytes())

    def test_manifest_path_traversal_and_overlapping_output(self):
        manifest, _ = self.capture()
        manifest["sources"][0]["file"] = "../database.json"
        (self.source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "manifest file"):
            importer.import_folder(self.source, self.output)
        with self.assertRaisesRegex(ValueError, "separate"):
            importer.import_folder(self.source, self.source / "published")
        self.assertFalse(self.output.exists())

    def test_direct_folder_does_not_load_adjacent_files(self):
        self.capture()
        (self.root / "plan.json").write_text('{"password":"private"}', encoding="utf-8")
        case, = importer.folder_cases(self.source)
        self.assertIsNone(case[5]["plan"])

    def test_driver_chooses_latest_manifest_timestamp(self):
        first = self.source / "exports" / "B"
        self.capture(first)
        last = self.source / "exports" / "A"
        manifest, data = self.capture(last)
        data["alerts"][0]["title"] = "Updated title"
        manifest["exported_at"] = "2026-11-07T12:00:00Z"
        self.save(last, manifest, data)
        case, = importer.folder_cases(self.source)
        self.assertEqual(case[4]["alerts"][0]["title"], "Updated title")
        data["alerts"][0]["id"] = str(uuid4())
        self.save(last, manifest, data)
        with self.assertRaisesRegex(ValueError, "mixes different"):
            list(importer.folder_cases(self.source))

    def test_prior_member_requires_a_successful_membership_activity(self):
        manifest, data = self.capture()
        cid, activity = str(uuid4()), str(uuid4())
        manifest["case_id"] = cid
        data["cases"] = [{"id": cid, "tenant_id": self.tenant}]
        data["activities"] = [{"id": activity, "tenant_id": self.tenant, "subject_case_id": cid,
                               "action": "case_members_moved_out"}]
        target = {"id": str(uuid4()), "activity_id": activity, "tenant_id": self.tenant, "alert_id": self.alert,
                  "result_state": "succeeded", "before_value": {"member": True}, "after_value": {"member": False}}
        data["activity_targets"] = [target]
        self.save(self.source, manifest, data)
        self.assertEqual(next(importer.folder_cases(self.source))[2], cid)
        target["result_state"] = "failed"
        self.save(self.source, manifest, data)
        with self.assertRaisesRegex(ValueError, "unrelated subjects"):
            list(importer.folder_cases(self.source))

    def test_replay_on_fresh_site_blocks_the_standard_importer_and_keeps_retired_order(self):
        self.capture()
        record, = importer.folder_cases(self.source)
        replacement = (importer.replay.REPLAY, *record[1:])
        old = importer.site.EVIDENCE / importer.replay.SOURCE
        index = self.output / "index.html"
        with patch.object(importer, "folder_cases", return_value=[replacement]):
            importer.import_folder(self.source, self.output)
            retired = importer.site.retired_records(index)
            self.assertEqual({r["key"] for r in retired}, {"m01", "s02", "u03"})
            self.assertEqual(importer.site.update([old], self.output), (0, 1))
            # An already-migrated registry can have a different historical order.
            rows = importer.site.existing(index)
            sorted_before = importer.site.registry_html(rows, self.output, list(reversed(retired)))
            index.write_bytes(sorted_before)
            importer.import_folder(self.source, self.output)
            self.assertEqual(index.read_bytes(), sorted_before)

    def test_active_prior_scope_requires_verified_replacement(self):
        self.capture()
        record, = importer.folder_cases(self.source)
        old = importer.site.EVIDENCE / importer.replay.SOURCE
        importer.site.update([old], self.output)
        index = self.output / "index.html"
        before = index.read_bytes()
        with (patch.object(importer, "folder_cases", return_value=[(importer.replay.REPLAY, *record[1:])]),
              self.assertRaisesRegex(ValueError, "migrate the previous three")):
            importer.import_folder(self.source, self.output)
        self.assertEqual(before, index.read_bytes())

    def test_independent_incident_requires_its_member_relation(self):
        manifest, data = self.capture()
        iid = str(uuid4())
        data["incidents"] = [{"tenant_id": self.tenant, "id": iid}]
        self.save(self.source, manifest, data)
        with self.assertRaisesRegex(ValueError, "unrelated alerts"):
            list(importer.folder_cases(self.source))
        data["incident_alerts"] = [{"tenant_id": self.tenant, "id": str(uuid4()), "incident_id": iid,
                                    "alert_id": self.alert}]
        self.save(self.source, manifest, data)
        self.assertEqual(next(importer.folder_cases(self.source))[2], iid)


if __name__ == "__main__":
    unittest.main()
