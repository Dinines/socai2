"""Same-Run result selection and truthful adoption in the saved-snapshot viewer."""
import copy
import json
import re
import unittest

from processing_audit_delivery import run_delivery
from processing_audit_detail import render_case_detail
from test_processing_audit_flow import Nodes


class DeliveryTest(unittest.TestCase):
    def setUp(self):
        self.run = {"id": "r", "kind": "alert_basic", "alert_id": "a", "tenant_id": "t",
                    "state": "completed", "delivery_state": "complete", "stop_reason": "stage_output_saved"}
        self.result = {"id": "out", "source_run_id": "r", "alert_id": "a", "tenant_id": "t",
                       "verdict": "needs_review", "rationale": "  原文\n", "confidence": 0}

    def test_other_run_subject_and_tenant_cannot_supply_missing_conclusion(self):
        wrong = [{**self.result, **change} for change in
                 ({"source_run_id": "old"}, {"alert_id": "other"}, {"tenant_id": "other"})]
        data = {"alert_assessments": wrong, "artifacts": [{"id": "raw", "run_id": "r",
                "kind": "model_response", "content_json": {"raw": {"verdict": "benign"}}}]}
        self.assertEqual(run_delivery(self.run, data)["results"], [])

    def test_original_judgment_and_save_adoption_do_not_imply_current_adoption(self):
        data = {"alert_assessments": [self.result], "alerts": [{"id": "a", "latest_triage_id": "newer"}],
                "artifacts": [{"id": "pub", "run_id": "r", "content_json":
                               {"outcome": {"result_id": "out", "adopted": True}}}]}
        original = copy.deepcopy(data)
        result = run_delivery(self.run, data)["results"][0]
        self.assertEqual(result["fields"]["rationale"], "  原文\n")
        self.assertEqual(result["fields"]["confidence"], 0)
        self.assertTrue(result["saved_adoption"]["outcome"]["adopted"])
        self.assertEqual(result["current_adoption"]["state"], "not_adopted")
        self.assertEqual(data, original)

    def test_missing_current_case_sources_is_unverified_even_with_adoption_receipt(self):
        run = {"id": "r", "kind": "baseline", "case_id": "c"}
        data = {"results": [{"id": "out", "source_run_id": "r", "case_id": "c", "conclusion": "原结论"}],
                "cases": [{"id": "c", "current_assessment_id": "current"}],
                "case_assessments": [{"id": "current", "case_id": "c"}]}
        self.assertEqual(run_delivery(run, data)["results"][0]["current_adoption"]["state"], "unverified")
        data["case_assessment_sources"] = [{"case_id": "c", "assessment_id": "current", "result_id": "out"}]
        self.assertEqual(run_delivery(run, data)["results"][0]["current_adoption"]["state"], "adopted")

    def test_incident_conclusion_and_open_questions_remain_separate(self):
        run = {"id": "r", "kind": "incident_diagnosis", "incident_id": "i"}
        result = {"id": "out", "source_run_id": "r", "incident_id": "i", "state": "completed",
                  "summary": "摘要", "diagnosis": {"conclusion": "待核结论"}, "open_questions": []}
        view = run_delivery(run, {"incident_diagnoses": [result]})["results"][0]
        self.assertEqual(view["fields"]["conclusion"], "待核结论")
        self.assertEqual(view["review"], {"open_questions": []})
        self.assertEqual(view["current_adoption"]["state"], "unverified")

    def test_cancelled_incident_placeholder_does_not_supply_a_conclusion(self):
        run = {"id": "r", "kind": "incident_diagnosis", "incident_id": "i", "state": "cancelled"}
        row = {"id": "out", "source_run_id": "r", "incident_id": "i", "state": "cancelled",
               "summary": None, "diagnosis": None, "open_questions": None}
        view = run_delivery(run, {"incident_diagnoses": [row]})["results"][0]
        self.assertFalse(view["has_conclusion"])
        self.assertEqual(view["fields"]["state"], "cancelled")

    def test_rendered_summary_is_safe_and_saved_original_is_complete(self):
        self.result["rationale"] = '</script><script>alert("x")</script>'
        raw = "原" * 524321
        data = {"runs": [self.run], "run_steps": [], "alert_assessments": [self.result],
                "artifacts": [{"id": "large", "run_id": "r", "kind": "source_snapshot", "content_text": raw}]}
        page = render_case_detail(key="x", title="x", batch="x", data=data, extras={})
        self.assertNotIn(self.result["rationale"], page)
        summary = json.loads(re.search(r'id="inspector-data">(.*?)</script>', page, re.DOTALL)[1])
        self.assertEqual(summary["runs"]["r"]["results"][0]["fields"]["rationale"], self.result["rationale"])
        self.assertIn(raw, page)

    def test_c3_labels_follow_saved_request_not_success_or_sequence(self):
        run = {"id": "r", "kind": "baseline"}
        steps = [{"id": name, "run_id": "r", "stage_code": "C3", "kind": "model", "name": "model",
                  "seq": seq, "state": state, "input_artifact_id": name + "-request"}
                 for seq, name, state in [(1, "initial", "failed"), (2, "supplement", "completed")]]
        artifacts = [{"id": name + "-request", "run_id": "r", "step_id": name, "kind": "model_request",
                      "content_json": {"payload": payload}} for name, payload in
                     [("initial", {}), ("supplement", {"section_completion": {"missing_fields": ["followups"]}})]]
        page = render_case_detail(key="x", title="x", batch="x",
                                  data={"runs": [run], "run_steps": steps, "artifacts": artifacts}, extras={})
        labels = Nodes(page).nodes
        self.assertTrue(any("初答" in s and "失败" in s for s in labels))
        self.assertTrue(any("补答" in s and "已完成" in s for s in labels))
