"""The 4177 subject lookup only includes this subject, tenant and source snapshot."""
import hashlib
import json
import unittest
from pathlib import Path

from processing_audit_subjects import prepare_subjects


class SubjectViewsTest(unittest.TestCase):
    def setUp(self):
        self.record = {"batch": "test", "key": "standalone", "id": "source"}
        self.alert = {"tenant_id": "tenant", "id": "a", "title": "<alert>", "latest_triage_id": None}
        self.incident = {"tenant_id": "tenant", "id": "i", "title": "组内事件"}
        self.data = {"alerts": [self.alert], "incidents": [self.incident],
                     "incident_alerts": [{"tenant_id": "tenant", "alert_id": "a", "incident_id": "i"}]}

    def views(self):
        return {(m["kind"], m["id"]): b.decode() for m, b in prepare_subjects(self.record, self.data)}

    def test_standalone_and_cross_links_with_snapshot_source(self):
        result = self.views()
        self.assertIn("没有该主体的执行轮次", result["alert", "a"])
        self.assertIn("../index.html#incident/i/source", result["alert", "a"])
        self.assertIn("../index.html#alert/a/source", result["incident", "i"])
        self.assertNotIn("<alert>", result["incident", "i"])
        self.assertIn("&lt;alert&gt;", result["incident", "i"])
        earlier = result["incident", "i"]
        self.record["id"] = "another&source"
        self.assertIn("#alert/a/another%26source", self.views()["incident", "i"])
        self.assertNotEqual(earlier, self.views()["incident", "i"])

    def test_exact_run_and_tenant_and_current_pointer(self):
        self.data.update({
            "runs": [{"tenant_id": "tenant", "id": "run-a", "kind": "alert_basic", "alert_id": "a", "state": "failed"},
                     {"tenant_id": "other", "id": "secret-run", "kind": "alert_basic", "alert_id": "a"}],
            "run_steps": [{"tenant_id": "tenant", "id": "s", "run_id": "run-a", "seq": 1, "stage_code": "A",
                           "kind": "model", "state": "failed", "error": {"code": "audit_refused"}}],
            "artifacts": [{"tenant_id": "tenant", "id": "file1", "run_id": "run-a", "content_text": "local-trace"},
                          {"tenant_id": "other", "id": "file2", "run_id": "run-a", "content_text": "other-trace"}],
            "alert_assessments": [{"tenant_id": "tenant", "id": "unpublished", "alert_id": "a",
                                   "verdict": "benign"}],
        })
        result = self.views()
        self.assertIn("audit_refused", result["alert", "a"])
        self.assertIn("local-trace", result["alert", "a"])
        self.assertNotIn("local-trace", result["incident", "i"])
        self.assertNotIn("other-trace", result["alert", "a"])
        self.assertNotIn("secret-run", result["alert", "a"])
        self.assertIn("没有已发布的记录", result["alert", "a"])
        self.alert["latest_triage_id"] = "absent"
        self.assertIn("absent 的原件未包含", self.views()["alert", "a"])
        self.alert["latest_triage_id"] = "unpublished"
        self.assertIn("<dd>benign</dd>", self.views()["alert", "a"])

    def test_missing_member_and_credentials(self):
        self.data["alerts"] = []
        html = self.views()["incident", "i"]
        self.assertIn("缺少主体记录", html)
        self.assertNotIn("#alert/a", html)
        self.data["incident_diagnoses"] = [{"tenant_id": "tenant", "id": "bad", "incident_id": "i",
                                            "diagnosis": {"api_key": "fixture-do-not-print"}}]
        with self.assertRaisesRegex(ValueError, "possible credential"):
            self.views()

    def test_stored_s02_with_two_distinct_alerts(self):
        file = Path(__file__).with_name("evidence") / "ie-audit-20261106-a1/readback/s02/database.json"
        data = json.loads(file.read_bytes())
        record = {**self.record, "scope_id": data["cases"][0]["id"]}
        rows = prepare_subjects(record, data)
        self.assertEqual(len(rows), 3)
        for meta, body in rows:
            self.assertEqual(meta["detail"], f"subjects/{hashlib.sha256(body).hexdigest()}.html")
            html = body.decode()
            self.assertIn("查看关联 Case 调查过程", html)
            if meta["kind"] == "incident":
                for alert in data["alerts"]:
                    self.assertIn(f'#alert/{alert["id"]}/source', html)
                self.assertIn("汇总并保存事件诊断", html)
            else:
                self.assertIn("向模型请求分诊", html)

    def test_complete_delivery_and_pending_review_are_displayed_separately(self):
        self.incident["latest_diagnosis_id"] = "d"
        self.data["runs"] = [{"tenant_id": "tenant", "id": "r", "kind": "incident_diagnosis", "incident_id": "i",
                              "state": "completed", "delivery_state": "complete"}]
        self.data["incident_diagnoses"] = [{"tenant_id": "tenant", "id": "d", "incident_id": "i", "source_run_id": "r",
            "summary": "事件概要", "diagnosis": {"delivery_assessment": {"schema_version": "socai2.incident-delivery.v1",
                "state": "complete", "reasons": [], "review_items": {"state": "required", "unresolved_member_ids": ["a"],
                    "unresolved_finding_ids": [], "open_question_ids": ["Q1"]}}}}]
        view = self.views()["incident", "i"]
        self.assertIn("完整交付", view)
        self.assertIn("<dt>复核状态</dt><dd>待复核</dd>", view)
        self.assertNotIn("部分交付", view)
        self.data["runs"][0].update(state="failed", delivery_state="partial")
        delivery = self.data["incident_diagnoses"][0]["diagnosis"]["delivery_assessment"]
        delivery.update(state="partial", reasons=["invalid_response_units_excluded"])
        view = self.views()["incident", "i"]
        self.assertIn("部分交付", view)
        self.assertIn("已单独排除", view)
        self.assertIn("· 失败</h3>", view)
