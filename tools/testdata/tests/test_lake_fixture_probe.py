"""D2 offline control-flow tests around the original LakeWriter implementation."""
import asyncio
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import investigation_fixture as fixture
import lake_fixture_probe as probe

TENANT = "53824f24-d1d4-5820-8147-f6cfda8a1247"
CONFIG = {role: {"host": "127.0.0.1", "port": 19000, "database": "aisoc",
                 "user": role, "password": f"{role}-secret-do-not-print"} for role in ("writer", "reader")}


class FakeBackend:
    def __init__(self, out):
        self.out = out
        self.lake = probe.lake_module([])
        self.rows = []
        self.inserts = 0
        self.writer_starts = 0
        self.writer_stops = 0
        self.reader_stops = 0
        self.missing_column = None
        self.insert_error = False
        self.corrupt_readback = False
        self.reject_second_buffer = False
        self.control_leak = False
        self.factory_settings = None

    def reader_factory(self, **kwargs):
        self.factory_settings = kwargs
        return self

    def writer_factory(self, **kwargs):
        backend = self

        class OriginalWriter(backend.lake.LakeWriter):
            async def start(self):
                backend.writer_starts += 1
                receipt = json.loads((backend.out / "receipt.json").read_bytes())
                assert receipt["status"] == "write_started_outcome_unknown"
                assert receipt["write_attempted"] is False
                self._client = InsertClient()

            async def write_event(self, event):
                if backend.reject_second_buffer and len(self._buffer) == 1:
                    return False
                return await super().write_event(event)

        class InsertClient:
            def __init__(self):
                self.connection = SimpleNamespace(connected=False)
                self.connections = []

            def execute(self, sql, rows, **options):
                receipt = json.loads((backend.out / "receipt.json").read_bytes())
                assert receipt["write_attempted"] is True
                assert receipt["stage"] == "single_flush"
                assert options == {"types_check": True}
                assert len(rows) == 3
                assert self.connection.send_receive_timeout == 5
                assert self.connection.connect_timeout == 5
                assert self.connection.disable_reconnect is True
                backend.inserts += 1
                if backend.insert_error:
                    raise RuntimeError("writer-secret-do-not-print")
                backend.rows.extend(copy.deepcopy(rows))

            def disconnect(self):
                backend.writer_stops += 1

        return OriginalWriter(**kwargs)

    def execute(self, sql, params, with_column_types=False):
        if "system.columns" in sql:
            return [(column, "fake-type") for column in self.lake._COLUMNS if column != self.missing_column]
        rows = [row for row in self.rows if str(row["tenant_id"]) == params["tenant_id"]]
        if "event_ids" in params:
            rows = [row for row in rows if str(row["event_id"]) in params["event_ids"]]
        if sql.startswith("SELECT count()"):
            if self.control_leak and params["tenant_id"] != TENANT:
                return [(1,)]
            return [(len(rows),)]
        if with_column_types:
            rows = copy.deepcopy(rows)
            if self.corrupt_readback:
                rows[0]["outcome"] = "success"
            # Original insert converts IPv4 into IPv6; returned objects exercise normalization.
            return ([tuple(row[column] for column in self.lake._COLUMNS) for row in rows],
                    [(column, "fake-type") for column in self.lake._COLUMNS])
        if sql.startswith("SELECT event_id"):
            return [(row["event_id"],) for row in rows
                    if row["src_hostname"] == params["hostname"]
                    and str(row["source_ip"].ipv4_mapped) == params["source_ip"]
                    and str(row["dest_ip"].ipv4_mapped) == params["dest_ip"]
                    and row["dst_port"] == params["dst_port"] and row["protocol"] == params["protocol"]
                    and params["window_start"] <= row["event_time"] < params["window_end"]]
        raise AssertionError("unexpected SQL")

    def disconnect(self):
        self.reader_stops += 1


class LakeFixtureProbeTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.fixture = self.root / "fixture"
        self.manifest = fixture.generate_fixture(run_id="d2-direct-test", tenant=TENANT,
                                                window_start="2026-10-23T10:00:00Z", out=self.fixture)
        self.out = self.root / "attempt"
        self.backend = FakeBackend(self.out)

    def run_probe(self, **changes):
        args = {"input_dir": self.fixture, "tenant": TENANT, "out": self.out, "config": CONFIG,
                "reader_factory": self.backend.reader_factory, "writer_factory": self.backend.writer_factory}
        args.update(changes)
        with patch("clickhouse_driver.Client", side_effect=AssertionError("offline D2 tests must not connect")):
            return asyncio.run(probe.run_probe(**args))

    def test_success_is_single_original_flush_and_independent_field_readback(self):
        result = self.run_probe()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["write_outcome"], "three_rows_verified")
        self.assertEqual((self.backend.inserts, self.backend.writer_starts, self.backend.writer_stops,
                          self.backend.reader_stops), (1, 1, 1, 1))
        self.assertEqual(result["writer_metrics"], {"rows_written": 3, "flush_failures": 0, "buffered": 0})
        self.assertEqual(result["discarded_buffer_on_cleanup"], 0)
        self.assertEqual(result["matched_event_ids"], [self.manifest["events"][0]["event_id"]])
        self.assertEqual(len(result["comparisons"]), 3)
        self.assertTrue(all(not item["differences"] for item in result["comparisons"]))
        self.assertEqual(self.backend.factory_settings["settings"], {"readonly": 1, "max_execution_time": 5})
        self.assertEqual(self.backend.factory_settings["send_receive_timeout"], 5)
        self.assertEqual([q["stage"] for q in result["queries"]],
                         ["schema", "existing_ids", "existing_tenant", "readback", "bounded_match", "control_tenant"])
        self.assertTrue((self.out / "readback.json").exists())
        text = (self.out / "receipt.json").read_text()
        self.assertNotIn("secret-do-not-print", text)
        self.assertIn("not database row-level isolation", text)

    def test_existing_event_or_tenant_data_prevents_writer_start(self):
        _, _, events = fixture.load_fixture(self.fixture)
        old = self.backend.lake.event_to_row(events[0])
        for index, event_id in enumerate((old["event_id"], "11111111-1111-4111-8111-111111111111")):
            with self.subTest(event_id=event_id):
                self.backend.rows = [{**old, "event_id": event_id}]
                self.out = self.root / f"old-{index}"
                self.backend.out = self.out
                result = self.run_probe()
                self.assertEqual(result["status"], "failed_before_write")
                self.assertIn(result["error"]["check"], ("existing_event_ids", "tenant_not_empty"))
                self.assertEqual((self.backend.inserts, self.backend.writer_starts), (0, 0))

    def test_missing_schema_prevents_any_write(self):
        self.backend.missing_column = "outcome"
        result = self.run_probe()
        self.assertEqual(result["error"]["check"], "missing_writer_columns")
        self.assertEqual(result["status"], "failed_before_write")
        self.assertEqual((self.backend.inserts, self.backend.writer_starts), (0, 0))

    def test_explicit_identities_backend_and_fixture_tampering_rejected_before_connect(self):
        for key, value in (("user", "writer"), ("host", "elsewhere"), ("database", "other")):
            config = copy.deepcopy(CONFIG)
            config["reader"][key] = value
            with self.subTest(key=key), self.assertRaises(probe.CheckFailed):
                self.run_probe(config=config)
            self.assertIsNone(self.backend.factory_settings)
            self.assertFalse(self.out.exists())
        path = self.fixture / "events/001.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            self.run_probe()
        self.assertIsNone(self.backend.factory_settings)
        self.assertFalse(self.out.exists())

    def test_failure_during_buffering_discards_without_cleanup_insert(self):
        self.backend.reject_second_buffer = True
        result = self.run_probe()
        self.assertEqual(result["status"], "failed_before_write")
        self.assertEqual(result["discarded_buffer_on_cleanup"], 1)
        self.assertEqual(self.backend.inserts, 0)
        self.assertEqual(self.backend.writer_stops, 1)
        self.assertEqual(result["error"]["check"], "writer_rejected_event")

    def test_fail_soft_insert_is_unknown_not_success_and_never_retried(self):
        self.backend.insert_error = True
        result = self.run_probe()
        self.assertEqual(result["status"], "failed_outcome_unknown")
        self.assertEqual(result["error"]["check"], "writer_flush_not_confirmed")
        self.assertEqual(result["writer_metrics"], {"rows_written": 0, "flush_failures": 1, "buffered": 0})
        self.assertEqual(self.backend.inserts, 1)
        self.assertNotIn("readback", [q["stage"] for q in result["queries"]])
        self.assertNotIn("secret-do-not-print", (self.out / "receipt.json").read_text())
        with self.assertRaises(FileExistsError):
            self.run_probe()
        self.assertEqual(self.backend.inserts, 1)

    def test_false_success_result_is_rejected_and_keeps_actual_difference(self):
        self.backend.corrupt_readback = True
        result = self.run_probe()
        self.assertEqual(result["status"], "failed_verification")
        self.assertEqual(result["write_outcome"], "insert_acknowledged")
        self.assertEqual(result["error"]["check"], "readback_field_mismatch")
        self.assertEqual(result["comparisons"][0]["differences"], ["outcome"])
        self.assertEqual(self.backend.inserts, 1)
        self.assertTrue((self.out / "readback.json").exists())

    def test_wrong_tenant_query_result_prevents_pass(self):
        self.backend.control_leak = True
        result = self.run_probe()
        self.assertEqual(result["status"], "failed_verification")
        self.assertEqual(result["write_outcome"], "three_rows_verified")
        self.assertEqual(result["error"]["check"], "control_tenant_not_empty")
        self.assertEqual(self.backend.inserts, 1)


if __name__ == "__main__":
    unittest.main()
