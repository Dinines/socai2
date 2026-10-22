"""Offline checks: no business imports, real HTTP, models or brokers."""
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from uuid import UUID

MODULE = Path(__file__).resolve().parents[1] / "alert_scenarios.py"
SPEC = importlib.util.spec_from_file_location("alert_scenarios_test_subject", MODULE)
scenarios = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scenarios)
TENANT = "11111111-1111-4111-8111-111111111111"
TIME = "2026-10-22T08:00:00+08:00"
URL = "http://127.0.0.1:24930/api/v1/alert-ingress"


class Reply:
    def __init__(self, body, status=202):
        self.body, self.status = body, status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return scenarios.json_bytes(self.body)[:limit]


class AlertScenariosTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def generate(self, directory="batch", count=3, **kwargs):
        return scenarios.generate_batch(run_id="contract-test", tenant=TENANT, event_time=TIME,
                                        count=count, out=self.root / directory, **kwargs)

    def send(self, opener):
        with patch.dict(os.environ, {"TESTDATA_TEST_TOKEN": "private-do-not-print"}), \
                patch.object(scenarios, "build_opener", return_value=opener):
            return scenarios.send_batch(input_dir=self.root / "batch", url=URL,
                                        token_env="TESTDATA_TEST_TOKEN", receipt=self.root / "receipt.json")

    def test_generation_is_deterministic_and_keeps_answers_separate(self):
        left = self.generate("left", count=20)
        right = self.generate("right", count=20)
        self.assertEqual(left, right)
        for item in (self.root / "left").rglob("*.json"):
            self.assertEqual(item.read_bytes(), (self.root / "right" / item.relative_to(self.root / "left")).read_bytes())
        all_ids = []
        for record in left["records"]:
            payload = json.loads((self.root / "left" / record["payload"]).read_text())
            expected = json.loads((self.root / "left" / record["expected"]).read_text())
            all_ids.append(payload["id"])
            UUID(payload["id"])
            self.assertEqual(payload["tenant_id"], TENANT)
            self.assertTrue(payload["source_event_ids"])
            self.assertEqual(payload["event_time"], "2026-10-22T00:00:00+00:00")
            self.assertIn("synthetic", payload["tags"])
            for forbidden in scenarios.ANSWER_FIELDS:
                self.assertNotIn(forbidden, json.dumps(payload))
                self.assertIn(forbidden, expected)
            for absent in ("case_id", "incident_id", "identity_version", "source_alert_id", "mitre_tactics", "mitre_techniques"):
                self.assertNotIn(absent, payload)
        self.assertEqual(len(set(all_ids)), 20)

    def test_entity_mapping_uses_explicit_unique_fields_only(self):
        manifest = self.generate()
        second = json.loads((self.root / "batch" / manifest["records"][1]["payload"]).read_text())
        # This template names its host only inside URLs/narrative; no hostname inference.
        self.assertNotIn("hostname", second)
        self.assertIn("src_ip", second)
        self.assertEqual(scenarios._entities([{"Computer": "A", "User": "alice"}, {"Computer": "B", "User": "alice"}]),
                         {"username": "alice"})

    def test_generation_rejects_overwrite_and_invalid_boundaries(self):
        self.generate()
        with self.assertRaises(FileExistsError):
            self.generate()
        for count in (0, 21):
            with self.subTest(count=count), self.assertRaises(ValueError):
                self.generate(f"invalid-{count}", count=count)
        with self.assertRaises(ValueError):
            scenarios.generate_batch(run_id="x", tenant=TENANT, event_time="2026-10-22T08:00:00", out=self.root / "naive")

    def test_send_success_means_accepted_only_and_excludes_answers(self):
        self.generate()
        calls = []
        class Opener:
            def open(self, request, timeout):
                payload = json.loads(request.data)
                calls.append(payload)
                assert request.get_header("Authorization") == "Bearer private-do-not-print"
                return Reply({"status": "accepted", "input_id": payload["id"], "tenant_id": TENANT,
                              "source_event_ids": payload["source_event_ids"],
                              "canonical_alert_id": payload["id"], "identity_version": "source-v1",
                              "processing_confirmed": False,
                              "message": {"topic": "isolated.raw", "partition": 0, "offset": len(calls) - 1}})
        result = self.send(Opener())
        self.assertEqual(result["status"], "accepted_only")
        self.assertEqual(result["accepted"], 3)
        self.assertFalse(result["processing_confirmed"])
        self.assertEqual(result["not_attempted"], 0)
        self.assertNotIn("private-do-not-print", (self.root / "receipt.json").read_text())
        self.assertNotIn("expected_tactics", json.dumps(calls))

    def test_transport_failure_stops_without_retry(self):
        self.generate()
        calls = []
        class Opener:
            def open(self, request, timeout):
                calls.append(request)
                raise URLError("private-do-not-print")
        result = self.send(Opener())
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["records"][0]["state"], "outcome_unknown")
        self.assertEqual(result["not_attempted"], 2)
        self.assertNotIn("private-do-not-print", (self.root / "receipt.json").read_text())

    def test_wrong_tenant_or_source_echo_stops_after_first_response(self):
        self.generate()
        for field, wrong in (("tenant_id", "22222222-2222-4222-8222-222222222222"),
                             ("source_event_ids", ["different-event"])):
            with self.subTest(field=field):
                receipt = self.root / "receipt.json"
                if receipt.exists():
                    receipt.unlink()
                calls = []
                class Opener:
                    def open(self, request, timeout):
                        payload = json.loads(request.data)
                        calls.append(payload)
                        response = {"status": "accepted", "input_id": payload["id"], "tenant_id": TENANT,
                                    "source_event_ids": payload["source_event_ids"],
                                    "canonical_alert_id": payload["id"], "identity_version": "source-v1",
                                    "processing_confirmed": False,
                                    "message": {"topic": "isolated.raw", "partition": 0, "offset": 0}}
                        response[field] = wrong
                        return Reply(response)
                result = self.send(Opener())
                self.assertEqual(len(calls), 1)
                self.assertEqual(result["accepted"], 0)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["records"][0]["state"], "response_unconfirmed")

    def test_http_refusal_and_unconfirmed_response_stop(self):
        for name, value in (("http", HTTPError(URL, 503, "private-do-not-print", {}, io.BytesIO(b"secret-body"))),
                            ("shape", Reply({"status": "accepted"})),
                            ("status", Reply({"status": "accepted"}, status=200))):
            with self.subTest(name=name):
                if not (self.root / "batch").exists():
                    self.generate()
                receipt = self.root / "receipt.json"
                if receipt.exists():
                    receipt.unlink()
                calls = []
                class Opener:
                    def open(self, request, timeout):
                        calls.append(request)
                        if isinstance(value, Exception):
                            raise value
                        return value
                result = self.send(Opener())
                self.assertEqual(len(calls), 1)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["not_attempted"], 2)

    def test_no_redirect_and_existing_receipt_or_tampered_payload_prevent_send(self):
        self.assertIsNone(scenarios.NoRedirect().redirect_request(None, None, 302, "", {}, "http://elsewhere"))
        self.generate()
        class NeverOpen:
            def open(self, *args, **kwargs):
                raise AssertionError("network must not be attempted")
        (self.root / "receipt.json").write_text("previous result")
        with self.assertRaises(FileExistsError):
            self.send(NeverOpen())
        self.assertEqual((self.root / "receipt.json").read_text(), "previous result")
        path = self.root / "batch/payloads/001.json"
        path.write_text(path.read_text() + " ")
        with self.assertRaises(ValueError):
            self.send(NeverOpen())


if __name__ == "__main__":
    unittest.main()
