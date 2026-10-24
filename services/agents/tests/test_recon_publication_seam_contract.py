"""Opt-in PG publication probe guards/phase separation with offline ledger."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/agents"))
SPEC = importlib.util.spec_from_file_location("publication_probe_contract", ROOT / "openspec/changes/continue-isolated-investigation-v2/probes/fixed_recon_publication_seam.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)
import test_recon_publication_store_contract as fixtures
from app.investigation_v2.execution_store import ExecutionPersistenceError
from app.investigation_v2.execution_store import canonical_json, content_hash


class PublicationProbeGuardTests(unittest.TestCase):
    def config(self): return {"batch": probe.BATCH, "writer_dsn": "postgresql://socai2_inv_m7_20261024_01_w:fake@192.168.1.21:5432/aisoc", "reader_dsn": "postgresql://socai2_inv_m7_20261024_01_r:fake@192.168.1.21:5432/aisoc"}

    def test_exact_fresh_roles_and_source_run_cannot_be_overridden(self):
        config = self.config();self.assertEqual(probe.validate_config(config), probe.BATCH)
        self.assertEqual(str(probe.RUN), "4dfd374a-17a6-5fec-833b-803bfbcb85c6")
        for key in ("run_id", "owner", "tenant_id", "source_batch", "api_url"):
            with self.subTest(key=key), self.assertRaises(AssertionError): probe.validate_config({**config, key: "override"})

    def test_prior_roles_broad_database_or_batch_are_rejected(self):
        config = self.config()
        for key in ("writer_dsn", "reader_dsn"):
            for changed in (config[key].replace("m7_", "m6_"), config[key].replace("_01_", "_02_"), config[key].replace("aisoc", "postgres"), config[key].replace("192.168.1.21", "127.0.0.1"), config[key] + "?sslmode=disable"):
                with self.subTest(key=key, changed=changed), self.assertRaises(AssertionError): probe.validate_config({**config, key: changed})
        for batch in (probe.BATCH + "x", "investigation-fixed-runtime-20261024-01"):
            with self.assertRaises(AssertionError): probe.validate_config({**config, "batch": batch})


class PublicationProbeLedgerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fixture = fixtures.ReconPublicationStoreContractTests();await self.fixture.asyncSetUp()
        self.store = await self.fixture.normal();self.ledger = self.fixture.ledger;self.request = self.fixture.request
        self.identity = dict(tenant=self.store.tenant_id, run_id=self.store.run_id, owner=self.store.executor_id)

    def verify(self, expected=None, events=None, artifacts=None):
        return probe.verify_publication_ledger(events or self.ledger.events, artifacts or list(self.ledger.artifacts.values()), expected_result=expected, **self.identity)

    async def test_before_and_after_raw_ledger_checks_match_store_and_all_edges(self):
        self.assertEqual(self.verify()["artifacts"], 10)
        await self.store.publish(self.request)
        read = await self.store.read_result(self.request)
        self.assertEqual(self.verify(read)["artifacts"], 14)
        self.assertEqual(self.verify(read)["report_sha256"], read["manifest"]["report"]["sha256"])

    async def test_original_verified_rows_hash_is_order_stable_and_unchanged_after_publish(self):
        original = probe.baseline_hash(self.ledger.events, list(self.ledger.artifacts.values()))
        await self.store.publish(self.request)
        reverse_artifacts = list(reversed(list(self.ledger.artifacts.values())))
        self.assertEqual(original, probe.baseline_hash(self.ledger.events, reverse_artifacts))
        changed = deepcopy(list(self.ledger.artifacts.values()))
        changed[0]["content"] += " "
        self.assertNotEqual(original, probe.baseline_hash(self.ledger.events, changed))

    async def test_read_phase_never_calls_publish_or_changes_rows(self):
        await self.store.publish(self.request);before = deepcopy((self.ledger.events, self.ledger.artifacts))
        with patch.object(type(self.store), "publish", new=AsyncMock(side_effect=AssertionError("read must never publish"))) as denied:
            result, descriptor = await probe.resolve_phase(lambda: self.fixture.store(), self.request, phase="read", expected_handoff_ref="unused")
        denied.assert_not_awaited();self.assertFalse(descriptor)
        self.assertEqual(result["publication_state"], "published")
        self.assertEqual((self.ledger.events, self.ledger.artifacts), before)

    async def test_publish_phase_checks_baseline_then_repeat_only_reads(self):
        original = await self.store.read_result(self.request)
        result, descriptor = await probe.resolve_phase(lambda: self.fixture.store(), self.request, phase="publish", expected_handoff_ref=original["candidate"]["handoff_ref"])
        self.assertTrue(descriptor);self.assertEqual(self.verify(result)["events"], 6)
        self.assertEqual(len(self.fixture.runtime_fixture.calls), 1)
        with self.assertRaisesRegex(AssertionError, "already_published"):
            await probe.resolve_phase(lambda: self.fixture.store(), self.request, phase="publish", expected_handoff_ref="unused")

    async def test_changed_baseline_never_calls_publish(self):
        with patch.object(type(self.store), "publish", new=AsyncMock(side_effect=AssertionError("no publish"))) as denied:
            with self.assertRaisesRegex(AssertionError, "handoff_changed"):
                await probe.resolve_phase(lambda: self.fixture.store(), self.request, phase="publish", expected_handoff_ref="wrong")
        denied.assert_not_awaited();self.assertEqual(len(self.ledger.events), 5)

    async def test_uncertain_first_commit_stops_without_automatic_second_call(self):
        original = await self.store.read_result(self.request)
        publish = type(self.store).publish
        async def lose_publish_ack(store, request):
            self.ledger.fail_after_commit = True
            return await publish(store, request)
        with patch.object(type(self.store), "publish", new=lose_publish_ack):
            with self.assertRaises(ExecutionPersistenceError):
                await probe.resolve_phase(lambda: self.fixture.store(), self.request, phase="publish", expected_handoff_ref=original["candidate"]["handoff_ref"])
        self.assertEqual(len(self.fixture.publication_rows()), 1)
        read, descriptor = await probe.resolve_phase(lambda: self.fixture.store(), self.request, phase="read", expected_handoff_ref="unused")
        self.assertFalse(descriptor);self.assertEqual(self.verify(read)["events"], 6)

    async def test_published_raw_body_hash_kind_owner_or_section_tampering_is_rejected(self):
        await self.store.publish(self.request);read = await self.store.read_result(self.request)
        for key, value in (("body_hash", "0" * 64), ("body_artifact_id", str(self.ledger.events[0]["payload"]["body_artifact_id"]))):
            events = deepcopy(self.ledger.events);events[-1]["payload"][key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError): self.verify(read, events=events)
        for key, value in (("kind", "wrong_kind"), ("tenant_id", UUID(int=99)), ("size_bytes", 0)):
            artifacts = deepcopy(list(self.ledger.artifacts.values()))
            artifact = next(a for a in artifacts if a["kind"] == probe.REPORT_KIND);artifact[key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError): self.verify(read, artifacts=artifacts)

    async def test_new_event_executor_and_in_out_hashes_are_fixed(self):
        await self.store.publish(self.request);read = await self.store.read_result(self.request)
        for key, value in (("agent", "unrelated_executor.v1"), ("input_hash", "0" * 64), ("output_hash", "0" * 64)):
            with self.subTest(key=key):
                events = deepcopy(self.ledger.events);events[-1][key] = value
                with self.assertRaises(AssertionError): self.verify(read, events=events)

    async def test_rehashed_publication_snapshot_cannot_change_frozen_runtime_scope_or_usage(self):
        await self.store.publish(self.request);read = await self.store.read_result(self.request)
        for field, value in (("runtime_version", "wrong.v1"), ("scope_hash", "0" * 64), ("stage_usage", {"tool_calls": 777})):
            with self.subTest(field=field):
                events = deepcopy(self.ledger.events);artifacts = deepcopy(list(self.ledger.artifacts.values()))
                snapshot = next(a for a in artifacts if str(a["id"]) == events[-1]["payload"]["state_artifact_id"])
                data = probe._m6.decoded(snapshot["content"]);data[field] = value
                snapshot["content"] = canonical_json(data);snapshot["sha256"] = content_hash(snapshot["content"]);snapshot["size_bytes"] = len(snapshot["content"].encode())
                events[-1]["payload"]["state_hash"] = snapshot["sha256"]
                with self.assertRaises(AssertionError): self.verify(read, events=events, artifacts=artifacts)


if __name__ == "__main__": unittest.main()
