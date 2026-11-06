"""Exercise replay publication in a temporary directory with a substituted PG reader."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import NAMESPACE_URL, UUID, uuid5

import refresh_three_case_replay_20261106 as replay


class ThreeCaseReplayTest(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / replay.REPLAY
        self.root.mkdir()
        self.site = Path(temp.name) / "site"
        self.old = replay.site.EVIDENCE / replay.SOURCE
        self.plan = replay.site.read(self.old / "plan.json")
        self.plan["batch"] = replay.REPLAY
        self.rows = {}
        self.id_changes = {}
        for card in self.plan["cases"]:
            key = card["key"]
            rows = (self.old / "readback" / key / "database.json").read_text(encoding="utf-8")
            changes = {value: str(uuid5(NAMESPACE_URL, "synthetic-replay:" + value))
                       for value in replay.operation_ids(card)}
            changes[card["case_id"]] = str(uuid5(UUID(self.plan["tenant_id"]),
                                           "socai2.case.create:" + changes[card["operation_keys"]["create"]]))
            for r in json.loads(rows)["runs"]:
                changes[r["id"]] = str(uuid5(NAMESPACE_URL, "synthetic-replay:" + r["id"]))
            text = json.dumps(card)
            for old, new in changes.items():
                rows = rows.replace(old, new)
                text = text.replace(old, new)
            card.update(json.loads(text))
            self.id_changes[key] = changes
            self.rows[key] = json.loads(rows)
            self.rows[key]["input_freshness"] = [{"run_id": r["id"], "value": {}}
                                                 for r in self.rows[key]["runs"] if r["kind"] == "baseline"]
        replay.save(self.root / "plan.json", self.plan)
        self.folder = self.root / "readback"

    def capture(self):
        def substitute(plan, *, build_sql):
            query = build_sql(plan)
            self.assertIn("REPEATABLE READ READ ONLY", query)
            self.assertIn("m.raw_json->>'source'='ie-audit-20261106-a1'", query)
            self.assertNotIn(replay.REPLAY, query)
            return {"database": replay.exporter.DB, "role": replay.exporter.ROLE,
                    "isolation": "repeatable read"}, self.rows

        with patch.object(replay, "fetch", side_effect=substitute):
            replay.export_readback(self.root, self.folder)

    def test_replace_three_and_default_refresh(self):
        views = replay.site.read(self.old / "page-service-readback.json")
        replay_views = {}
        for card in self.plan["cases"]:
            key = card["key"]
            text = json.dumps(views[key])
            receipts = self.root / "receipts" / key
            receipts.mkdir(parents=True)
            for path in (self.old / "receipts" / key).glob("*.json"):
                record = path.read_text(encoding="utf-8")
                for old, new in self.id_changes[key].items():
                    record = record.replace(old, new)
                replay.save(receipts / path.name, json.loads(record))
            for old, new in self.id_changes[key].items():
                text = text.replace(old, new)
            replay_views[key] = json.loads(text)
        replay.save(self.root / "page-service-readback.json", replay_views)
        replay.site.update([self.old], self.site)
        old_index = replay.site.existing(self.site / "index.html")
        other = dict(next(iter(old_index.values())), id="unrelated", batch="another-test", key="u03")
        old_index[other["id"]] = other
        (self.site / "index.html").write_bytes(replay.site.registry_html(old_index, self.site, []))
        self.capture()
        replay.publish(self.root, self.folder, self.site)
        path = self.site / "index.html"
        new = replay.site.existing(path)
        self.assertEqual(4, len(new))
        self.assertEqual(other, new["unrelated"])
        self.assertEqual(replay.KEYS, {r["key"] for r in new.values() if r["batch"] == replay.REPLAY})
        self.assertEqual(3, len(replay.site.existing(self.root / "retired-pages/index.html")))
        for row in new.values():
            if row["batch"] == replay.REPLAY:
                page = (self.site / row["detail"]).read_text(encoding="utf-8")
                self.assertIn("case/page-data", page)
                self.assertIn("A1-output", page)
        saved = path.read_bytes()
        replay.site.update([self.old, self.root], self.site)
        replay.publish(self.root, self.folder, self.site)
        self.assertEqual(saved, path.read_bytes())
        card = self.plan["cases"][0]
        key = card["key"]
        replay_views[key]["incident/analysis"]["entries"][0]["run"]["id"] = "another-run"
        (self.root / "page-service-readback.json").write_text(json.dumps(replay_views), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "foreign or missing attempt"):
            replay.publish(self.root, self.folder, self.site)
        self.assertEqual(saved, path.read_bytes())
        receipt = self.root / "receipts" / key / "I-output.json"
        contents = replay.site.read(receipt)
        contents["receipt"]["run_id"] = "another-run"
        receipt.write_text(json.dumps(contents), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "does not belong"):
            replay.cli_receipts(receipt.parent, card, self.rows[key])

    def test_foreign_upstream_attempt_is_rejected(self):
        alert = next(r for r in self.rows["u03"]["runs"] if r["kind"] == "alert_basic")
        alert["operation_key"] = "stale-operation"
        with self.assertRaisesRegex(ValueError, "foreign processing attempt"):
            self.capture()
        self.assertFalse(self.folder.exists())

    def test_timed_receipt_requested_run_is_only_for_case_start(self):
        card = self.plan["cases"][0]
        rows = self.rows[card["key"]]
        folder = self.root / "timed"
        folder.mkdir()
        for label, kind, command, subject in [
                ("A1", "alert_basic", "alert", card["alert_ids"][0]),
                ("I", "incident_diagnosis", "incident", card["incident_id"]),
                ("C", "baseline", "case-start", card["case_id"])]:
            run = next(r for r in rows["runs"] if r["kind"] == kind)
            args = [command, "--card", card["key"], "--subject", subject, "--operation-key", run["operation_key"]]
            if label == "C":
                args.extend(["--run-id", run["id"]])
            replay.save(folder / f"{label}-input.json", {"timed": True, "job": args})
            replay.save(folder / f"{label}-output.json", {"receipt": {"batch": replay.REPLAY, "card": card["key"],
                        "command": command, "subject": subject, "operation_key": run["operation_key"],
                        "run_id": run["id"], "requested_run_id": run["id"] if label == "C" else None}})
        self.assertEqual(len(replay.cli_receipts(folder, card, rows)), 6)
        for label in ["A1", "I", "C"]:
            path = folder / f"{label}-output.json"
            original = path.read_bytes()
            value = json.loads(original)
            value["receipt"]["requested_run_id"] = None if label == "C" else value["receipt"]["run_id"]
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not belong"):
                replay.cli_receipts(folder, card, rows)
            path.write_bytes(original)

    def test_incomplete_export_cannot_replace_registry(self):
        self.rows["u03"]["runs"][0]["state"] = "running"
        self.capture()
        replay.site.update([self.old], self.site)
        old_index = (self.site / "index.html").read_bytes()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            replay.publish(self.root, self.folder, self.site)
        self.assertEqual(old_index, (self.site / "index.html").read_bytes())
