"""Shared scene/real-probe input mapping, pure fixtures only."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/agents"))
PATH = ROOT / "openspec/changes/continue-isolated-investigation-v2/probes/v2_query_seam.py"
SPEC = importlib.util.spec_from_file_location("v2_seam_probe_under_test", PATH)
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)


class V2ScenarioContractTests(unittest.TestCase):
    def setUp(self):
        self.card = json.loads(probe.SCENARIO.read_text(encoding="utf-8"))
        self.business = self.card["business_input"]
        args = self.business["query_parameters"]
        self.alert = {"id": UUID(self.business["canonical_alert_id"]), "tenant_id": UUID(self.business["tenant_id"]),
                      "raw_event": json.dumps({"synthetic": True, "telemetry": [{"tenant_id": self.business["tenant_id"], "event_id": "951c5352-2df4-53d8-a431-b2763fea5e6e", "hostname": args["hostname"], "source_ip": args["source_ip"], "dest_ip": args["dest_ip"], "dst_port": 443, "protocol": "TCP"}]}),
                      "source_event_ids": json.dumps(["951c5352-2df4-53d8-a431-b2763fea5e6e", "d92cb914-0026-509d-916a-9f9d43f03546"])}

    def test_actual_checked_fields_map_to_scope_and_new_query_arguments(self):
        with patch("socket.socket", side_effect=AssertionError("pure mapping must not connect")):
            context, profile, arguments = probe.build_context(self.alert, self.business, checked_ref="live-read-contract")
        self.assertEqual(arguments, self.business["query_parameters"])
        self.assertEqual(profile.descriptor["delivery_target"]["id"], self.business["canonical_alert_id"])
        self.assertEqual(context.run_id, probe.RUN)
        self.assertNotIn("event_id", arguments)
        self.assertEqual(context.member_snapshot.selected[0].fields[3].path, "raw_event.telemetry[0].dst_port")

    def test_wrong_identity_changed_source_fields_or_nonfixture_are_rejected(self):
        for changes in ({"id": UUID(int=1)}, {"tenant_id": UUID(int=1)},
                        {"raw_event": json.dumps({"synthetic": False, "telemetry": []})}):
            with self.subTest(changes=changes), self.assertRaises(AssertionError):
                probe.build_context({**self.alert, **changes}, self.business, checked_ref="live-read-contract")
        for changes in ({"hostname": "different-host"}, {"dest_ip": "198.51.100.99"}, {"tenant_id": str(UUID(int=1))}, {"event_id": str(UUID(int=1))}):
            raw = json.loads(self.alert["raw_event"])
            raw["telemetry"][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(AssertionError):
                probe.build_context({**self.alert, "raw_event": json.dumps(raw)}, self.business, checked_ref="live-read-contract")

    def test_evaluation_answers_cannot_change_runtime_scope_or_arguments(self):
        first = probe.build_context(self.alert, self.card["business_input"], checked_ref="live-read-contract")
        changed = deepcopy(self.card)
        changed["evaluation_only"]["expected_event_ids"] = ["00000000-0000-0000-0000-000000000001"]
        changed["evaluation_only"]["authorization"] = "authorized"
        second = probe.build_context(self.alert, changed["business_input"], checked_ref="live-read-contract")
        self.assertEqual(first[0], second[0])
        self.assertEqual(first[1].descriptor, second[1].descriptor)
        self.assertEqual(first[2], second[2])
        self.assertNotIn("authorized", str(first[1].descriptor))

    def test_shared_card_reuses_existing_fixture_and_separates_run_identity(self):
        prior = json.loads((ROOT / self.card["source_fixture"]["prior_receipt"]).read_text(encoding="utf-8"))
        self.assertEqual(self.business["canonical_alert_id"], prior["canonical_alert_id"])
        self.assertEqual(self.card["evaluation_only"]["expected_event_ids"], [prior["source_event_id"]])
        controls = self.card["evaluation_only"]["excluded_events"]
        self.assertEqual({item["reason"] for item in controls}, {"different_destination", "outside_window"})
        self.assertEqual(len({item["event_id"] for item in controls} | set(self.card["evaluation_only"]["expected_event_ids"])), 3)
        self.assertNotEqual(str(probe.RUN), self.business["canonical_alert_id"])
        self.assertNotEqual(probe.RUN, probe.run_identity("investigation-v2-query-20261024-02"))
        self.assertEqual(self.card["observation_contract"]["model_calls"], 0)


if __name__ == "__main__":
    unittest.main()
