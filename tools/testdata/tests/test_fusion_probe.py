"""Offline probe boundaries only; these tests do not contact infrastructure."""
import copy
from datetime import datetime
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alert_kafka import raw_alert_model
from fusion_probe import IsolatedRedis, check_material, read_configuration


class ConfigurationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "probe.env"
        self.values = {"DATABASE_URL": "postgresql://test:private@localhost/test", "REDIS_URL": "redis://localhost/9",
            "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092", "KAFKA_SECURITY_PROTOCOL": "PLAINTEXT",
            "KAFKA_TOPIC_ALERTS_RAW": "socai2.testdata.probe-test.raw",
            "KAFKA_TOPIC_ALERTS_FUSED": "socai2.testdata.probe-test.fused",
            "SOCAI_TESTDATA_REDIS_PREFIX": "socai2:testdata:probe-test:"}

    def read(self, **overrides):
        self.path.write_text("\n".join(f"{key}={value}" for key, value in {**self.values, **overrides}.items()))
        return read_configuration(self.path, "probe-test")

    def test_explicit_environment_and_batch_isolation(self):
        self.assertEqual(self.read(), self.values)
        for changes in ({"KAFKA_TOPIC_ALERTS_RAW": "socai2.alerts.raw"},
                        {"KAFKA_TOPIC_ALERTS_FUSED": "socai2.testdata.other.fused"},
                        {"SOCAI_TESTDATA_REDIS_PREFIX": "aisoc:"},
                        {"DATABASE_URL": "${DATABASE_URL}"},
                        {"REDIS_URL": ""}, {"OPENAI_API_KEY": "private"},
                        {"KAFKA_SECURITY_PROTOCOL": "SSL"}, {"KAFKA_SECURITY_PROTOCOL": "ssl"},
                        {"PGSSLMODE": "verify-full"}):
            with self.subTest(keys=list(changes)), self.assertRaises(ValueError):
                self.read(**changes)

    def test_missing_environment_is_not_satisfied_by_ambient_config(self):
        with self.assertRaises(ValueError):
            read_configuration(self.path, "probe-test")


class MaterialTest(unittest.TestCase):
    def setUp(self):
        self.raw = raw_alert_model().model_validate({"id": "11111111-1111-4111-8111-111111111111",
            "source_alert_id": "11111111-1111-4111-8111-111111111111", "identity_version": "source-v1",
            "tenant_id": "22222222-2222-4222-8222-222222222222", "source": "synthetic",
            "title": "bounded probe", "description": "source material", "raw_event": {"telemetry": [{"value": 1}]},
            "source_event_ids": ["event-original"], "event_time": "2026-10-23T08:00:00+08:00"})
        adopted = self.raw.model_dump(mode="json")
        adopted["id"] = str(self.raw.deterministic_id())
        adopted["source_event_ids"].append(str(self.raw.id))
        self.envelope = {"alert": adopted}
        self.pg = {key: adopted[key] for key in ("title", "description", "severity", "raw_event", "mitre_tactics",
                                                "mitre_techniques", "source_event_ids")}
        self.pg["event_time"] = datetime.fromisoformat("2026-10-23T00:00:00+00:00")

    def test_original_source_id_adoption_and_timezone_equivalence(self):
        self.envelope["alert"]["created_at"] = "2026-10-23T10:00:00"
        check_material(self.raw, self.envelope, self.pg)
        self.assertEqual(self.raw.source_event_ids, ["event-original"])

    def test_explicit_source_created_at_is_not_ignored(self):
        self.raw.created_at = datetime(2026, 10, 23, 9)
        self.envelope["alert"]["created_at"] = "2026-10-23T10:00:00"
        with self.assertRaises(ValueError):
            check_material(self.raw, self.envelope, self.pg)

    def test_material_loss_in_either_message_or_row_is_rejected(self):
        damaged = copy.deepcopy(self.envelope)
        damaged["alert"]["raw_event"] = {}
        with self.assertRaises(ValueError):
            check_material(self.raw, damaged, self.pg)
        for changes in ({"raw_event": {}}, {"source_event_ids": [str(self.raw.id)]},
                        {"description": "changed"}, {"event_time": datetime(2026, 10, 23)}):
            with self.subTest(keys=list(changes)), self.assertRaises(ValueError):
                check_material(self.raw, self.envelope, {**self.pg, **changes})


class RedisBoundaryTest(unittest.IsolatedAsyncioTestCase):
    async def test_original_commands_are_prefixed_and_other_keys_refused(self):
        calls = []
        class Client:
            async def get(self, key):
                calls.append(("get", key))
                return None
            async def set(self, key, value, **kwargs):
                calls.append(("set", key, value, kwargs))
                return True
        cache = IsolatedRedis(Client(), "socai2:testdata:probe-test:")
        key = "aisoc:fusion:delivery:v1:tenant:alert"
        await cache.get(key)
        await cache.set(key, "snapshot", ex=300, nx=True)
        self.assertEqual(calls[0], ("get", cache.prefix + key))
        self.assertEqual(calls[1], ("set", cache.prefix + key, "snapshot", {"ex": 300, "nx": True}))
        with self.assertRaises(ValueError):
            await cache.set("production:unrelated", "value")
        self.assertEqual(len(calls), 2)
