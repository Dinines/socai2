"""A2 limited completion policy: explicit window quantifiers, no I/O."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.fixed_recon import evaluate_alert_recon
from test_business_profile_contract import bind
from test_evidence_view_contract import query, scope, view

START = "2026-10-23T10:00:00.000000+00:00"
END = "2026-10-23T10:05:00.000000+00:00"
TARGET = dict(start=START, end=END)


def material_view(start=START, end=END, **query_options):
    payload = query(**query_options)
    for params in (payload["query_receipt"]["parameters"], payload["caller_receipt"]["request_parameters"]):
        params.update(start=start, end=end)
    original = deepcopy(payload)
    evidence = view(payload)
    assert payload == original
    return evidence


class ReconWindowContractTests(unittest.TestCase):
    def evaluate(self, evidence, **kwargs):
        with patch("socket.socket", side_effect=AssertionError("pure window policy")):
            return evaluate_alert_recon(bind(scope()), evidence,
                                        current_snapshot_ref=evidence.snapshot_ref if evidence else None, **kwargs)

    def test_full_window_has_versioned_limited_readiness(self):
        result = self.evaluate(material_view())
        self.assertEqual(result["completion_policy_ref"], "bounded_full_window_source_check.v1")
        self.assertEqual(result["coverage"], dict(target_window=TARGET, query_window=TARGET,
                                               covered_window=TARGET, uncovered_windows=[], full_window_queried=True,
                                               basis="confirmed_bounded_source_query_only"))
        self.assertEqual(result["scope_readiness"], "ready")
        self.assertEqual(result["completion_basis"], "limited_source_observation_only")
        self.assertEqual((result["nature"], result["authorization"]), ("unresolved", "unknown"))
        self.assertEqual(result["handoff"]["run_completion"], "not_published")

    def test_one_microsecond_subwindow_preserves_facts_and_discloses_both_gaps(self):
        start, end = "2026-10-23T10:01:00.000000+00:00", "2026-10-23T10:01:00.000001+00:00"
        result = self.evaluate(material_view(start, end))
        self.assertEqual(result["scope_readiness"], "partial")
        self.assertTrue(result["handoff"]["review_required"])
        self.assertEqual(result["coverage"]["uncovered_windows"],
                         [dict(start=START, end=start), dict(start=end, end=END)])
        self.assertFalse(result["coverage"]["full_window_queried"])
        self.assertIn("query_window_coverage_incomplete", result["blocking_gaps"])
        self.assertEqual([q["status"] for q in result["questions"] if q["question"] in {"Q1", "Q5"}],
                         ["supported", "supported"])
        self.assertEqual(len(result["facts"]), 4)

    def test_boundary_subwindows_disclose_only_the_missing_side(self):
        cases = [(START, "2026-10-23T10:02:00.000000+00:00",
                  dict(start="2026-10-23T10:02:00.000000+00:00", end=END)),
                 ("2026-10-23T10:01:00.000000+00:00", END,
                  dict(start=START, end="2026-10-23T10:01:00.000000+00:00"))]
        for start, end, missing in cases:
            with self.subTest(start=start, end=end):
                result = self.evaluate(material_view(start, end))
                self.assertEqual(result["scope_readiness"], "partial")
                self.assertEqual(result["coverage"]["uncovered_windows"], [missing])

    def test_timezone_equivalent_receipt_is_compared_in_utc_microseconds(self):
        result = self.evaluate(material_view("2026-10-23T18:00:00+08:00", "2026-10-23T18:05:00+08:00"))
        self.assertEqual(result["coverage"]["query_window"], TARGET)
        self.assertTrue(result["coverage"]["full_window_queried"])
        self.assertEqual(result["scope_readiness"], "ready")

    def test_empty_and_truncated_queries_keep_existing_readiness_blockers(self):
        for options, gap in ((dict(status="empty"), "source_observation_not_resolved"),
                             (dict(truncated=True), "query_rows_truncated")):
            with self.subTest(options=options):
                result = self.evaluate(material_view(**options))
                self.assertTrue(result["coverage"]["full_window_queried"])
                self.assertEqual(result["scope_readiness"], "partial")
                self.assertIn(gap, result["blocking_gaps"])

    def test_declared_full_window_failure_is_not_confirmed_coverage(self):
        for status in ("unavailable", "error", "rejected"):
            with self.subTest(status=status):
                result = self.evaluate(material_view(status=status))
                self.assertEqual(result["coverage"]["query_window"], TARGET)
                self.assertIsNone(result["coverage"]["covered_window"])
                self.assertEqual(result["coverage"]["uncovered_windows"], [TARGET])
                self.assertFalse(result["coverage"]["full_window_queried"])
                self.assertEqual(result["scope_readiness"], "partial")

    def test_missing_material_and_observed_stop_do_not_invent_execution(self):
        result = self.evaluate(None)
        self.assertIsNone(result["coverage"]["query_window"])
        self.assertEqual(result["coverage"]["uncovered_windows"], [TARGET])
        self.assertEqual(result["blocking_gaps"], ["committed_source_material_missing"])
        stopped = self.evaluate(material_view(), execution_stop="deadline")
        self.assertTrue(stopped["coverage"]["full_window_queried"])
        self.assertEqual(stopped["scope_readiness"], "partial")
        self.assertEqual(stopped["stop_reason"], "deadline")


if __name__ == "__main__":
    unittest.main()
