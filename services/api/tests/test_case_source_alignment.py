"""Source-ID compatibility without executing an investigation or lake query."""
import copy
from unittest import TestCase

from app.investigation_v2.case_analysis_tools import source_alignment


class CaseSourceAlignmentTests(TestCase):
    def test_uuid_spellings_match_without_mutating_frozen_sources(self):
        event_id = "abcdefab-cdef-abcd-efab-cdefabcdefab"
        context = {"evidence": [
            {"evidence_id": "A1", "kind": "alert", "data": {"source_event_ids": [event_id.upper()]}},
            {"evidence_id": "A2", "kind": "alert", "data": {"source_event_ids": ["{" + event_id + "}"]}},
        ]}
        result = {"tool": "process_activity", "available": True, "rows": [{"event_id": event_id}]}
        original = copy.deepcopy(context)
        self.assertEqual(source_alignment(result, context), {
            "origin": "current_tool_result", "row_alert_refs": [["A1", "A2"]],
        })
        self.assertEqual(context, original)

    def test_opaque_ids_remain_exact_and_history_is_not_new_evidence(self):
        context = {"evidence": [
            {"evidence_id": "A1", "kind": "alert", "data": {"source_event_ids": ["Vendor-1", None, {}]}},
            {"evidence_id": "H1", "kind": "prior_analysis", "data": {"run_id": "old-run"}},
        ]}
        result = {"tool": "network_connections", "available": True,
                  "reused_from": {"run_id": "old-run", "evidence_id": "E1"},
                  "rows": [{"event_id": "vendor-1"}, {"event_id": "Vendor-1"}, {"event_id": "other"}]}
        self.assertEqual(source_alignment(result, context), {
            "origin": "historical_reuse", "already_in_history": "H1", "row_alert_refs": [[], ["A1"], []],
        })
