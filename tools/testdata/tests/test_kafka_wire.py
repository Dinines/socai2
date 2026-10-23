"""Offline checks against the original Fusion identity model; no service calls."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import alert_scenarios as scenarios
from alert_kafka import prepare_kafka, load_wire, raw_alert_model

TENANT = "11111111-1111-4111-8111-111111111111"
TIME = "2026-10-23T08:00:00+08:00"


class WireTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def generate(self, **kw):
        return scenarios.generate_batch(run_id="wire-test", tenant=TENANT, event_time=TIME,
                                        out=self.root / "input", **kw)

    def test_selected_template_retains_upstream_identity_and_order(self):
        originals = scenarios._generator().generate_incidents(10)
        names = [originals[8]["template_id"], originals[1]["template_id"]]
        batch = self.generate(template_ids=names)
        self.assertEqual(batch["count"], 2)
        self.assertEqual([r["scenario_id"] for r in batch["records"]], [originals[8]["id"], originals[1]["id"]])
        first = json.loads((self.root / "input/payloads/001.json").read_text())
        self.assertEqual(first["raw_event"]["telemetry"], originals[8]["telemetry"])

    def test_selection_rejects_bad_inputs_before_creating_directory(self):
        for args in ({"template_ids": ["missing"]}, {"template_ids": []},
                     {"template_ids": ["a", "a"]}, {"template_ids": ["a"], "count": 2}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.generate(**args)
            self.assertFalse((self.root / "input").exists())

    def test_wire_matches_real_model_and_preserves_material_without_reading_answers(self):
        original = self.generate()
        for answer in (self.root / "input/expected").iterdir():
            answer.unlink()  # Conversion must not depend on answers.
        result = prepare_kafka(input_dir=self.root / "input", tenant=TENANT, out=self.root / "prepared")
        _, wires = load_wire(self.root / "prepared", TENANT)
        for record, data, before in zip(result["records"], wires, original["records"]):
            wire = json.loads(data)
            payload = json.loads((self.root / "input" / before["payload"]).read_text())
            self.assertEqual({k:v for k,v in wire.items() if k not in {"identity_version", "source_alert_id"}}, payload)
            self.assertEqual(wire["source_alert_id"], payload["id"])
            self.assertEqual(record["predicted_canonical_alert_id"], str(raw_alert_model().model_validate(wire).deterministic_id()))
        with self.assertRaises(FileExistsError):
            prepare_kafka(input_dir=self.root / "input", tenant=TENANT, out=self.root / "prepared")

    def test_tamper_and_cross_tenant_refused(self):
        self.generate()
        with self.assertRaises(ValueError):
            prepare_kafka(input_dir=self.root / "input", tenant="22222222-2222-4222-8222-222222222222", out=self.root / "prepared")
        self.assertFalse((self.root / "prepared").exists())
        prepare_kafka(input_dir=self.root / "input", tenant=TENANT, out=self.root / "prepared")
        p = self.root / "prepared/wire/001.json"
        p.write_text(p.read_text() + " ")
        with self.assertRaises(ValueError):
            load_wire(self.root / "prepared", TENANT)


if __name__ == "__main__":
    unittest.main()
