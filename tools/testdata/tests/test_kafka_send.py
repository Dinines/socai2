"""Transport doubles check ACK/unknown boundaries, not broker functionality."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alert_scenarios import generate_batch
from alert_kafka import prepare_kafka, send_kafka

TENANT = "11111111-1111-4111-8111-111111111111"
TOPIC = "socai2.testdata.send-test.raw"


class SenderTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        generate_batch(run_id="send-test", tenant=TENANT, event_time="2026-10-23T08:00:00+08:00", out=self.root / "input")
        prepare_kafka(input_dir=self.root / "input", tenant=TENANT, out=self.root / "wire")
        self.calls = []
        self.stopped = False

    async def send(self, behavior="ok", **overrides):
        owner = self
        class Producer:
            def __init__(self, **kwargs):
                owner.assertTrue(kwargs["enable_idempotence"])
                owner.assertEqual(kwargs["acks"], "all")
            async def start(self):
                if behavior == "start-fail":
                    raise ConnectionError("secret")
            async def send_and_wait(self, topic, value, key):
                saved = json.loads((owner.root / "receipt.json").read_text())
                owner.assertEqual(saved["records"][-1]["state"], "started_outcome_unknown")
                owner.calls.append(json.loads(value))
                owner.assertEqual(key, TENANT.encode())
                if behavior == "timeout":
                    raise asyncio.TimeoutError("secret")
                if behavior == "cancel":
                    raise asyncio.CancelledError()
                return SimpleNamespace(topic="wrong" if behavior == "wrong" else topic, partition=0, offset=len(owner.calls)-1)
            async def stop(self):
                owner.stopped = True
        args = dict(wire_dir=self.root / "wire", tenant=TENANT, topic=TOPIC,
                    receipt=self.root / "receipt.json", config={"bootstrap_servers":"test:9092", "security_protocol":"PLAINTEXT"},
                    producer_factory=Producer)
        args.update(overrides)
        return await send_kafka(**args)

    async def test_acknowledged_only_and_exclusive_receipt(self):
        result = await self.send()
        self.assertEqual((result["status"],result["accepted"],result["not_attempted"]), ("accepted_only",3,0))
        self.assertFalse(result["processing_confirmed"])
        self.assertTrue(self.stopped)
        with self.assertRaises(FileExistsError):
            await self.send()
        self.assertEqual(len(self.calls), 3)

    async def test_unknown_or_wrong_confirmation_stops_after_first(self):
        for behavior in ("timeout", "wrong"):
            with self.subTest(behavior=behavior):
                result = await self.send(behavior)
                self.assertEqual((result["accepted"],result["not_attempted"]), (0,2))
                self.assertEqual(result["records"][0]["state"], "outcome_unknown")
                self.assertNotIn("secret", (self.root / "receipt.json").read_text())
                (self.root / "receipt.json").unlink()
        self.assertEqual(len(self.calls), 2)

    async def test_pre_send_failure_and_cancel_are_distinct(self):
        result = await self.send("start-fail")
        self.assertEqual((result["not_attempted"], len(result["records"])), (3,0))
        (self.root / "receipt.json").unlink()
        with self.assertRaises(asyncio.CancelledError):
            await self.send("cancel")
        saved = json.loads((self.root / "receipt.json").read_text())
        self.assertEqual(saved["records"][0]["state"], "outcome_unknown")
        self.assertTrue(self.stopped)

    async def test_production_topic_refused_before_client_or_receipt(self):
        with self.assertRaises(ValueError):
            await self.send(topic="socai2.alerts.raw")
        self.assertFalse((self.root / "receipt.json").exists())
        self.assertEqual(self.calls, [])
