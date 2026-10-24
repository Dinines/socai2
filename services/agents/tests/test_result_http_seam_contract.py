"""Controlled two-process GET probe guards; actual store, offline SQL transport."""
from contextlib import asynccontextmanager
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/agents"))
SPEC = importlib.util.spec_from_file_location("result_http_probe_contract", ROOT / "openspec/changes/continue-isolated-investigation-v2/probes/result_http_read_seam.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)
import test_owned_result_reader_contract as fixtures


class ResultHttpProbeGuardTests(unittest.TestCase):
    def config(self):
        return dict(batch=probe.BATCH, api_url="http://127.0.0.1:18441", internal_url="http://127.0.0.1:18442",
            ledger_dsn="postgresql://socai2_inv_m8r_20261025_01_w:fake@192.168.1.21:5432/aisoc",
            auth_dsn="postgresql://socai2_inv_m8r_20261025_01_r:fake@192.168.1.21:5432/aisoc",
            api_service_token="external-test-credential-" + "a" * 32, internal_read_token="internal-test-credential-" + "b" * 32)

    def test_only_fixed_approved_run_and_exact_new_roles(self):
        config = self.config();self.assertEqual(probe.validate_config(config), probe.BATCH)
        self.assertEqual(str(probe.RUN), "4dfd374a-17a6-5fec-833b-803bfbcb85c6")
        for key in ("run_id", "owner", "tenant_id", "source_batch", "scope"):
            with self.subTest(key=key), self.assertRaises(AssertionError): probe.validate_config({**config, key: "override"})
        for key in ("ledger_dsn", "auth_dsn"):
            for value in (config[key].replace("m8r", "m7"), config[key].replace("_01_", "_02_"), config[key].replace("/aisoc", "/postgres"), config[key] + "?sslmode=disable"):
                with self.subTest(key=key, value=value), self.assertRaises(AssertionError): probe.validate_config({**config, key: value})

    def test_two_plain_distinct_loopback_services_required(self):
        config = self.config()
        for key in ("api_url", "internal_url"):
            for value in ("http://192.168.1.21:18441", "https://127.0.0.1:18441", "http://127.0.0.1", "http://u:p@127.0.0.1:18441", "http://127.0.0.1:18441/path", "http://127.0.0.1:18441?override=1", "http://127.0.0.1:18441#fragment"):
                with self.subTest(key=key, value=value), self.assertRaises(AssertionError): probe.validate_config({**config, key: value})
        with self.assertRaises(AssertionError): probe.validate_config({**config, "internal_url": config["api_url"]})

    def test_separate_nonempty_credentials_and_batch_are_required(self):
        config = self.config()
        for key in ("api_service_token", "internal_read_token"):
            for value in ("", "short", "a" * 257, "a" * 40 + " "):
                with self.subTest(key=key), self.assertRaises(AssertionError): probe.validate_config({**config, key: value})
        with self.assertRaises(AssertionError): probe.validate_config({**config, "internal_read_token": config["api_service_token"]})
        with self.assertRaises(AssertionError): probe.validate_config({**config, "batch": "investigation-result-http-20261024-01"})


class ResultHttpProbeLedgerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fixture = fixtures.OwnedResultReaderContractTests();await self.fixture.asyncSetUp()
        await self.fixture.store.publish(self.fixture.request)
        self.payload = await self.fixture.read();self.ledger = self.fixture.ledger
        self.rows = deepcopy((self.ledger.events, list(self.ledger.artifacts.values()), self.ledger.run))
        self.prior = {"real_publish": dict(manifest_ref=self.payload["manifest"]["manifest_ref"],
            manifest_artifact=self.payload["manifest_artifact"], report_sha256=probe._m7.content_hash(self.payload["markdown"]),
            report_bytes=len(self.payload["markdown"].encode()), execution_snapshot=self.payload["execution_snapshot"],
            m6_verified_baseline_sha256=probe._m7.baseline_hash(self.rows[0], self.rows[1]))}

    def verify(self, *, before=None, after=None, payload=None, prior=None):
        with patch.object(probe, "RUN", self.fixture.store.run_id), patch.object(probe._m7, "OWNER", self.fixture.store.executor_id):
            return probe.verify_stable_read(self.payload if payload is None else payload,
                self.rows if before is None else before, self.rows if after is None else after,
                tenant=self.fixture.store.tenant_id, prior=self.prior if prior is None else prior)

    async def test_owned_read_matches_all_fourteen_raw_artifacts_and_accepted_version(self):
        checked = self.verify()
        self.assertEqual((checked["events"], checked["artifacts"], checked["stage_usage"]["tool_calls"]), (6, 14, 1))
        self.assertEqual(checked["whole_verified_ledger_sha256"], probe.snapshot_hash(self.rows))
        self.assertEqual(len(self.fixture.fixture.runtime_fixture.calls), 1)

    async def test_preflight_raw_rows_match_owned_http_fields_and_are_fully_checked(self):
        with patch.object(probe, "RUN", self.fixture.store.run_id):
            baseline = probe.raw_published_result(self.rows, self.fixture.store.tenant_id)
        self.verify(payload=baseline)
        for key in baseline: self.assertEqual(baseline[key], self.payload[key])
        changed = deepcopy(self.rows);changed[0][-1]["agent"] = "invalid"
        with patch.object(probe, "RUN", self.fixture.store.run_id):
            comparison = probe.raw_published_result(changed, self.fixture.store.tenant_id)
        with self.assertRaises(AssertionError): self.verify(payload=comparison, before=changed, after=changed)

    async def test_snapshot_artifact_order_stable_but_body_or_legacy_column_changes_refused(self):
        reversed_rows = deepcopy(self.rows);reversed_rows[1].reverse()
        self.assertEqual(probe.snapshot_hash(self.rows), probe.snapshot_hash(reversed_rows))
        for kind in ("body", "run"):
            changed = deepcopy(self.rows)
            if kind == "body": changed[1][0]["content"] += " "
            else: changed[2]["total_tokens"] = 1
            with self.subTest(kind=kind), self.assertRaisesRegex(AssertionError, "changed_verified_ledger"): self.verify(after=changed)

    async def test_stable_corrupt_event_or_artifact_is_still_refused(self):
        for key, value in (("agent", "different-runtime"), ("output_hash", "0" * 64)):
            changed = deepcopy(self.rows);changed[0][-1][key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError): self.verify(before=changed, after=changed)
        changed = deepcopy(self.rows);changed[1][-1]["size_bytes"] = 0
        with self.assertRaises(AssertionError): self.verify(before=changed, after=changed)

    async def test_self_consistent_new_snapshot_cannot_rewrite_frozen_usage(self):
        changed = deepcopy(self.rows);payload = changed[0][-1]["payload"]
        state = next(a for a in changed[1] if str(a["id"]) == payload["state_artifact_id"])
        value = probe._m7._m6.decoded(state["content"]);value["stage_usage"]["tool_calls"] = 0
        state["content"] = probe._m7.canonical_json(value);state["sha256"] = probe._m7.content_hash(state["content"])
        state["size_bytes"] = len(state["content"].encode());payload["state_hash"] = state["sha256"]
        with self.assertRaisesRegex(AssertionError, "changed_frozen"): self.verify(before=changed, after=changed)

    async def test_dto_identity_notification_and_accepted_manifest_report_execution_are_pinned(self):
        for key, value in (("tenant_id", str(UUID(int=99))), ("run_id", str(UUID(int=99))), ("profile", "case_analysis"), ("notification", {})):
            payload = deepcopy(self.payload);payload[key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError): self.verify(payload=payload)
        for key, value in (("manifest_ref", "different"), ("manifest_artifact", {}), ("report_sha256", "0" * 64), ("report_bytes", 0), ("execution_snapshot", {}), ("m6_verified_baseline_sha256", "0" * 64)):
            prior = deepcopy(self.prior);prior["real_publish"][key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError): self.verify(prior=prior)

    async def test_unchanged_legacy_completed_or_billed_rows_are_not_approved_baseline(self):
        for key, value in (("status", "completed"), ("completed_at", "2026-10-25"), ("total_cost_usd", 1)):
            changed = deepcopy(self.rows);changed[2][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(AssertionError, "legacy_Run"): self.verify(before=changed, after=changed)

    async def test_entire_outer_owned_dto_must_match_raw_publication_and_run(self):
        for key, value in (("publication_state", "not_published"), ("target", {"type": "alert", "id": str(UUID(int=99))}),
                           ("objective", "different_objective"), ("retention", "not_attempted"), ("legacy_run_status", "completed"),
                           ("unexpected_field", "extra"), ("missing_field", None), ("bool_as_manifest_version", True)):
            changed = deepcopy(self.payload)
            if key == "missing_field": changed.pop("retention")
            elif key == "bool_as_manifest_version": changed["manifest"]["version"] = value
            else: changed[key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError): self.verify(payload=changed)

    async def test_observer_uses_readonly_transaction_and_tenant_bound_selects(self):
        fixture = self
        class Observer:
            @asynccontextmanager
            async def transaction(self, **kwargs):
                fixture.assertEqual(kwargs, {"readonly": True});yield self
            async def execute(self, sql, *args): fixture.assertEqual(args, (str(fixture.fixture.store.tenant_id),))
            async def fetchval(self, sql): fixture.assertEqual(sql, "SHOW transaction_read_only");return "on"
            async def fetch(self, sql, *args):
                fixture.assertEqual(args, (probe.RUN, fixture.fixture.store.tenant_id))
                fixture.assertTrue(sql.startswith("SELECT "));fixture.assertIn("tenant_id=$2", sql)
                return fixture.rows[0] if "FROM investigation_events" in sql else fixture.rows[1]
            async def fetchrow(self, sql, *args):
                fixture.assertTrue(sql.startswith("SELECT "));fixture.assertIn("tenant_id=$2", sql)
                fixture.assertEqual(args, (probe.RUN, fixture.fixture.store.tenant_id));return fixture.rows[2]
        self.assertEqual(await probe.read_rows(Observer(), self.fixture.store.tenant_id), self.rows)


if __name__ == "__main__": unittest.main()
