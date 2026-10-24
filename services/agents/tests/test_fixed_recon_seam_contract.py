"""Pure preflight guards and answer isolation for the opt-in M6.2 probe."""
from copy import deepcopy
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/agents"))
SPEC = importlib.util.spec_from_file_location("fixed_recon_seam_under_test", ROOT / "openspec/changes/continue-isolated-investigation-v2/probes/fixed_recon_runtime_seam.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)
import test_v2_seam_scenario_contract as fixtures
import test_fixed_recon_runtime_contract as runtime_fixtures


class FixedReconSeamContractTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.V2ScenarioContractTests()
        self.fixture.setUp()
        self.config = {"batch": probe.BATCH, "api_url": "http://127.0.0.1:45123",
            "writer_dsn": "postgresql://socai2_inv_m6_20261024_01_w:fake@192.168.1.21:5432/aisoc",
            "reader_dsn": "postgresql://socai2_inv_m6_20261024_01_r:fake@192.168.1.21:5432/aisoc", "service_token": "f" * 64}

    def context(self, card=None):
        return probe.build_context(self.fixture.alert, (card or self.fixture.card)["business_input"], checked_ref="live-contract", run_id=probe.run_identity(probe.BATCH))

    def test_new_run_is_distinct_from_old_seams_and_replay_identity_is_stable(self):
        current = probe.run_identity(probe.BATCH)
        self.assertEqual(current, probe.validate_config(self.config)[1])
        self.assertNotIn(current, [fixtures.probe.run_identity("investigation-v2-query-20261024-01"), fixtures.probe.run_identity("investigation-v2-query-20261024-02")])
        self.assertNotEqual(current, probe.run_identity("investigation-fixed-runtime-20261024-02"))
        for bad in ("investigation-v2-query-20261024-01", "x", probe.BATCH + ";", probe.BATCH + "0"):
            with self.subTest(batch=bad), self.assertRaises(AssertionError): probe.run_identity(bad)

    def test_private_configuration_accepts_only_loopback_separate_api(self):
        for api in ("https://127.0.0.1:80", "http://localhost:80", "http://192.168.1.21:80", "http://127.0.0.1", "http://x@127.0.0.1:80", "http://127.0.0.1:80?x", "http://127.0.0.1:80#x", "http://127.0.0.1:80/legacy"):
            with self.subTest(api=api), self.assertRaises(AssertionError): probe.validate_config({**self.config, "api_url": api})

    def test_role_and_database_guards_prevent_old_or_broader_identities(self):
        for key in ("writer_dsn", "reader_dsn"):
            original = self.config[key]
            for value in (original.replace("m6_", "v2q_"), original.replace("_01_", "_02_"), original.replace("aisoc", "postgres"), original.replace(":5432", ":5433"), original.replace("192.168.1.21", "127.0.0.1"), original + "?sslmode=disable", original.replace(":fake", "")):
                with self.subTest(key=key, value=value), self.assertRaises(AssertionError): probe.validate_config({**self.config, key: value})
        with self.assertRaises(AssertionError): probe.validate_config({**self.config, "service_token": "short"})

    def test_current_checked_projection_and_plan_without_network(self):
        with patch("socket.socket", side_effect=AssertionError("offline contract")):
            context, request, parameters = self.context()
            plan = probe.make_recon_plan(request)
        self.assertEqual(context.run_id, probe.run_identity(probe.BATCH))
        planned = plan["query_input"]["parameters"]
        self.assertEqual({k: v for k, v in planned.items() if k not in {"start", "end"}}, {k: v for k, v in parameters.items() if k not in {"start", "end"}})
        for boundary in ("start", "end"):
            self.assertEqual(datetime.fromisoformat(planned[boundary]), datetime.fromisoformat(parameters[boundary]))
        self.assertEqual(parameters, self.fixture.business["query_parameters"])
        self.assertNotIn("event_id", parameters)

    def test_expected_answer_changes_do_not_change_scope_profile_or_runtime_plan(self):
        original = self.context()
        card = deepcopy(self.fixture.card)
        card["evaluation_only"] = {"expected_event_ids": ["poison"], "nature": "malicious", "authorization": "authorized"}
        changed = self.context(card)
        self.assertEqual(original, changed)
        self.assertEqual(probe.make_recon_plan(original[1]), probe.make_recon_plan(changed[1]))

    def test_current_source_change_still_rejects_before_execution(self):
        raw = json.loads(self.fixture.alert["raw_event"])
        raw["telemetry"][0]["dest_ip"] = "198.51.100.99"
        with self.assertRaises(AssertionError):
            probe.build_context({**self.fixture.alert, "raw_event": json.dumps(raw)}, self.fixture.business, checked_ref="changed", run_id=probe.run_identity(probe.BATCH))

    def test_post_execution_evaluation_checks_hash_and_source_semantics(self):
        expected = self.fixture.card["evaluation_only"]
        output = {"status": "ok", "caller_receipt": {"http_status": 200}, "rows": [{"event_id": expected["expected_event_ids"][0],
            "raw_payload": {"sha256": expected["matching_raw_sha256"]}, "ocsf_json": {"sha256": expected["matching_ocsf_sha256"]}, "action": expected["action"], "outcome": expected["outcome"]}]}
        context, _, _ = self.context()
        self.assertEqual(probe.evaluate_source(output, expected, context), output["rows"][0])
        for field, value in (("event_id", str(probe.run_identity(probe.BATCH))), ("outcome", "success"), ("raw_payload", {"sha256": "0" * 64})):
            changed = deepcopy(output); changed["rows"][0][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError): probe.evaluate_source(changed, expected, context)


class LedgerReadbackContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fixture = runtime_fixtures.FixedReconRuntimeContractTests()
        await self.fixture.asyncSetUp()
        runtime = self.fixture.runtime()
        await self.fixture.begin(runtime)
        await runtime.execute()
        self.events = deepcopy(self.fixture.ledger.events)
        self.artifacts = deepcopy(list(self.fixture.ledger.artifacts.values()))
        self.identity = dict(tenant=self.fixture.store.tenant_id, run_id=self.fixture.store.run_id, owner=self.fixture.store.executor_id)

    def verify(self, events=None, artifacts=None):
        return probe.verify_ledger(events or self.events, artifacts or self.artifacts, **self.identity)

    def test_actual_store_five_events_ten_artifacts_have_complete_edges(self):
        self.assertEqual(len(self.verify()), 10)

    def test_changed_body_hash_or_cross_event_reference_or_receipt_is_rejected(self):
        for key, value in (("body_hash", "0" * 64), ("body_artifact_id", self.events[0]["payload"]["body_artifact_id"]), ("seq", 99), ("tenant_id", str(probe.run_identity(probe.BATCH))), ("attempt_id", str(probe.run_identity(probe.BATCH)))):
            events = deepcopy(self.events); events[2]["payload"][key] = value
            with self.subTest(field=key), self.assertRaises(AssertionError): self.verify(events=events)

    def test_artifact_kind_owner_event_and_bytes_are_all_checked(self):
        for key, value in (("kind", "wrong"), ("tenant_id", probe.run_identity(probe.BATCH)), ("event_id", self.events[-1]["id"]), ("size_bytes", 0)):
            artifacts = deepcopy(self.artifacts); artifacts[0][key] = value
            with self.subTest(field=key), self.assertRaises(AssertionError): self.verify(artifacts=artifacts)

    def test_self_consistent_rehashed_snapshot_cannot_rewrite_its_receipt(self):
        artifacts, events = deepcopy(self.artifacts), deepcopy(self.events)
        snapshot = next(a for a in artifacts if str(a["id"]) == events[1]["payload"]["state_artifact_id"])
        state = json.loads(snapshot["content"]); state["persistence"]["seq"] = 100
        snapshot["content"] = probe.canonical_json(state)
        snapshot["sha256"] = probe.content_hash(snapshot["content"])
        snapshot["size_bytes"] = len(snapshot["content"].encode("utf-8"))
        events[1]["payload"]["state_hash"] = snapshot["sha256"]
        with self.assertRaisesRegex(AssertionError, "snapshot_receipt_mismatch"): self.verify(events, artifacts)


if __name__ == "__main__": unittest.main()
