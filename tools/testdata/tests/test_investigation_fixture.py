"""D1 direct offline contracts; no service startup or backend access."""
import importlib.util
import json
from datetime import datetime
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import UUID

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
import investigation_fixture as fixture
from alert_kafka import load_wire, prepare_kafka, raw_alert_model
from alert_scenarios import _load_payloads, json_bytes, sha256


def source_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


schema = source_module("investigation_fixture_event_schema", "services/fusion/app/services/event_schema.py")
lake = source_module("investigation_fixture_lake_writer", "services/fusion/app/services/lake_writer.py")
TENANT = "53824f24-d1d4-5820-8147-f6cfda8a1247"
OTHER_TENANT = "11111111-1111-4111-8111-111111111111"
RUN = "investigation-ch-contract"
START = "2026-10-23T10:00:00Z"


class InvestigationFixtureTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.batch = self.root / "batch"

    def generate(self, directory=None, **changes):
        args = {"run_id": RUN, "tenant": TENANT, "window_start": START,
                "out": directory or self.batch}
        args.update(changes)
        return fixture.generate_fixture(**args)

    def test_generation_is_offline_deterministic_and_timezone_normalized(self):
        with patch("socket.socket", side_effect=AssertionError("D1 must not access network")):
            one = self.generate()
            two = self.generate(self.root / "second", window_start="2026-10-23T18:00:00+08:00")
        self.assertEqual(one, two)
        for path in self.batch.rglob("*.json"):
            self.assertEqual(path.read_bytes(), (self.root / "second" / path.relative_to(self.batch)).read_bytes())
        self.assertEqual(len(list(self.batch.rglob("*.json"))), 6)
        other = self.generate(self.root / "other-tenant", tenant=OTHER_TENANT)
        self.assertNotEqual(one["records"][0]["alert_id"], other["records"][0]["alert_id"])
        self.assertTrue(set(r["event_id"] for r in one["events"]).isdisjoint(r["event_id"] for r in other["events"]))
        run = self.generate(self.root / "other-run", run_id="different-run")
        self.assertNotEqual(one["events"][0]["event_id"], run["events"][0]["event_id"])

    def test_original_envelopes_rawalert_and_writer_preserve_fields_and_unknown(self):
        self.generate()
        manifest, alerts, events = fixture.load_fixture(self.batch, tenant=TENANT)
        alert = alerts[0]
        parsed = raw_alert_model().model_validate(alert)
        self.assertEqual(str(parsed.tenant_id), TENANT)
        self.assertTrue(schema.validate_raw_alert(alert).ok)
        self.assertEqual(alert["source_event_ids"], [events[0]["id"]])
        self.assertEqual(len({UUID(e["id"]) for e in events}), 3)
        for event, record, stamp, dest in zip(events, manifest["events"],
                ("2026-10-23T10:01:00", "2026-10-23T10:02:00", "2026-10-23T09:59:00"),
                ("198.51.100.70", "198.51.100.71", "198.51.100.70")):
            with self.subTest(event=event["id"]):
                verdict = schema.validate_raw_event(event)
                self.assertTrue(verdict.ok)
                self.assertEqual(verdict.tenant_id, TENANT)
                self.assertEqual(verdict.source_event_id, event["id"])
                row = lake.event_to_row(event)
                self.assertEqual(row["event_id"], event["id"])
                self.assertEqual(row["tenant_id"], TENANT)
                self.assertEqual(row["event_time"], datetime.fromisoformat(stamp))
                self.assertEqual((row["class_uid"], row["category_uid"], row["activity_id"]), (4001, 4, 0))
                self.assertEqual((row["source_ip"], row["dest_ip"], row["dst_port"], row["protocol"]),
                                 ("192.0.2.70", dest, 443, "TCP"))
                self.assertEqual(row["src_hostname"], f"{RUN}-host")
                self.assertEqual((row["action"], row["outcome"]), ("network_connection_observed", "unknown"))
                self.assertEqual(row["connector_type"], "socai2-investigation-fixture")
                raw = json.loads(row["raw_payload"])
                self.assertEqual(raw["event_id"], row["event_id"])
                self.assertEqual(raw["tenant_id"], row["tenant_id"])
                self.assertEqual(raw["event_time"], stamp + "+00:00")
                self.assertEqual(raw["hostname"], row["src_hostname"])
                for key in ("source_ip", "dest_ip", "src_port", "dst_port", "protocol", "action", "outcome"):
                    self.assertEqual(raw[key], row[key])
                self.assertEqual(raw["source"], row["connector_type"])
                self.assertEqual(sha256(row["raw_payload"].encode()), record["raw_payload_sha256"])
                self.assertEqual(sha256(row["ocsf_json"].encode()), record["ocsf_json_sha256"])
                self.assertEqual(json.loads(row["ocsf_json"]), event["ocsf_event"])
                self.assertEqual(str(lake._to_ip_obj(row["source_ip"])), "::ffff:c000:246")

    def test_independent_query_predicate_matches_only_linked_event(self):
        self.generate()
        _, alerts, events = fixture.load_fixture(self.batch)
        rows = [lake.event_to_row(event) for event in events]
        # Independent fixed expectations, not the generator's own query helper.
        matched = [row["event_id"] for row in rows if row["tenant_id"] == TENANT
                   and row["src_hostname"] == f"{RUN}-host" and row["source_ip"] == "192.0.2.70"
                   and row["dest_ip"] == "198.51.100.70" and row["dst_port"] == 443
                   and row["protocol"] == "TCP"
                   and datetime(2026, 10, 23, 10) <= row["event_time"] < datetime(2026, 10, 23, 10, 5)]
        self.assertEqual(matched, [events[0]["id"]])
        self.assertEqual(alerts[0]["source_event_ids"], matched)
        self.assertNotIn(events[1]["id"], alerts[0]["source_event_ids"])
        self.assertNotIn(events[2]["id"], alerts[0]["source_event_ids"])

    def test_load_and_prepare_kafka_do_not_open_expected(self):
        self.generate()
        (self.batch / "expected/001.json").unlink()
        manifest, alerts, events = fixture.load_fixture(self.batch, tenant=TENANT)
        old_manifest, old_payloads = _load_payloads(self.batch)
        self.assertEqual((manifest, alerts), (old_manifest, old_payloads))
        wire_dir = self.root / "wire"
        prepared = prepare_kafka(input_dir=self.batch, tenant=TENANT, out=wire_dir)
        _, values = load_wire(wire_dir, TENANT)
        wire = json.loads(values[0])
        self.assertEqual(prepared["count"], 1)
        self.assertFalse(prepared["processing_confirmed"])
        self.assertEqual(wire["identity_version"], "source-v1")
        self.assertEqual(wire["source_event_ids"], [events[0]["id"]])
        self.assertEqual(str(raw_alert_model().model_validate(wire).deterministic_id()),
                         prepared["records"][0]["predicted_canonical_alert_id"])
        for name in ("matching_event_ids", "excluded_events", "connection_success", "behavior_nature",
                     "authorization_status", "expected_tactics", "response_class"):
            self.assertNotIn(name, values[0].decode())
            self.assertNotIn(name, json.dumps(events))

    def test_invalid_parameters_and_existing_directory_are_rejected(self):
        for index, changes in enumerate(({"run_id": "../escape"}, {"tenant": "invalid"},
                {"window_start": "2026-10-23T10:00:00"}, {"window_start": "bad"},
                {"window_start": "1900-01-01T00:00:00Z"})):
            directory = self.root / f"invalid-{index}"
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.generate(directory, **changes)
            self.assertFalse(directory.exists())
        self.generate()
        before = (self.batch / "manifest.json").read_bytes()
        with self.assertRaises(FileExistsError):
            self.generate()
        self.assertEqual(before, (self.batch / "manifest.json").read_bytes())
        with self.assertRaisesRegex(ValueError, "explicit test tenant"):
            fixture.load_fixture(self.batch, tenant=OTHER_TENANT)

    def test_file_mutation_and_rehashed_semantic_mutation_are_rejected(self):
        for index, change in enumerate(("bytes", "address", "time", "tenant", "source_link", "answer")):
            directory = self.root / f"mutation-{index}"
            manifest = self.generate(directory)
            event_path = directory / "events/001.json"
            event = json.loads(event_path.read_bytes())
            if change == "bytes":
                event_path.write_bytes(event_path.read_bytes() + b" ")
            elif change == "source_link":
                path = directory / "payloads/001.json"
                payload = json.loads(path.read_bytes())
                payload["source_event_ids"] = [manifest["events"][1]["event_id"]]
                path.write_bytes(json_bytes(payload))
                manifest["records"][0]["payload_sha256"] = sha256(path.read_bytes())
            else:
                if change == "address":
                    event["ocsf_event"]["dst_endpoint"]["ip"] = "not-an-ip"
                elif change == "time":
                    event["ocsf_event"]["time"] = "2026-10-23T10:01:00"
                elif change == "tenant":
                    event["ocsf_event"]["tenant_uid"] = OTHER_TENANT
                else:
                    event["ocsf_event"]["response_class"] = "malicious"
                event_path.write_bytes(json_bytes(event))
                manifest["events"][0]["event_sha256"] = sha256(event_path.read_bytes())
            (directory / "manifest.json").write_bytes(json_bytes(manifest))
            with self.subTest(change=change), self.assertRaises(ValueError):
                fixture.load_fixture(directory)

    def test_query_scope_paths_and_event_count_cannot_be_relaxed(self):
        for index, change in enumerate(("scope", "path", "count")):
            directory = self.root / f"manifest-{index}"
            manifest = self.generate(directory)
            if change == "scope":
                manifest["query_context"]["window_end"] = "2026-10-23T20:00:00+00:00"
            elif change == "path":
                manifest["events"][0]["event"] = "../outside.json"
            else:
                manifest["event_count"] = 4
            (directory / "manifest.json").write_bytes(json_bytes(manifest))
            with self.subTest(change=change), self.assertRaises(ValueError):
                fixture.load_fixture(directory)

    def test_expected_integrity_is_separate_from_transport_validation(self):
        self.generate()
        (self.batch / "expected/001.json").write_bytes(b"tampered expected")
        self.assertEqual(len(fixture.load_fixture(self.batch)[2]), 3)
        with self.assertRaisesRegex(ValueError, "expected file hash"):
            fixture.validate_fixture(self.batch)


if __name__ == "__main__":
    unittest.main()
