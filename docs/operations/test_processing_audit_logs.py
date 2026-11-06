"""File references, scope and actual execution status in Case workbench logs."""
import json
import posixpath
import re
import unittest

from processing_audit_logs import case_log_files


class CaseLogsTest(unittest.TestCase):
    def setUp(self):
        self.data = {
            "cases": [{"id": "case1", "title": "审计 </title><script>bad()</script>"}],
            "case_alerts": [{"case_id": "case1", "alert_id": "a1"}],
            "runs": [{"id": "r1", "kind": "baseline", "case_id": "case1", "state": "failed",
                      "requested_at": "2026-11-05T23:50:00Z", "input_artifact_id": "raw"},
                     {"id": "r2", "kind": "baseline", "case_id": "case1", "state": "pending",
                      "requested_at": "2026-11-06T10:30:00+08:00"},
                     {"id": "a", "kind": "alert_basic", "alert_id": "a1"}],
            "run_steps": [
                {"id": "s1", "run_id": "r1", "seq": 1, "stage_code": "C3", "kind": "stage", "state": "failed",
                 "input_artifact_id": "raw", "output_artifact_id": "missing", "reused_artifact_id": "alert-snap",
                 "error": {"code": "bad_answer"}, "ended_at": "2026-11-06T01:00:00Z"},
                {"id": "s2", "run_id": "r1", "seq": 2, "state": "skipped", "ended_at": "2026-11-06T08:30:00+08:00"},
                {"id": "s3", "run_id": "r1", "seq": 3, "state": "unknown"},
                {"id": "other", "run_id": "a", "seq": 1, "stage_code": "A", "state": "done"},
            ],
            "artifacts": [
                {"id": "raw", "run_id": "r1", "kind": "input_snapshot", "content_json": {"v": 1}},
                {"id": "extra", "run_id": "r1", "step_id": "s1", "kind": "model_response",
                 "captured_at": "2026-11-06T01:15:00Z", "content_json": {"raw": None}},
                {"id": "alert-snap", "run_id": "a", "alert_id": "a1", "kind": "source_snapshot"},
                {"id": "private", "run_id": "unrelated", "kind": "source_snapshot",
                 "content_json": {"text": "should not be exported"}},
            ],
        }

    def export(self):
        return case_log_files(self.data, batch="rerun", key="m01")

    def test_recent_state_and_resolvable_files(self):
        info, fs = self.export()
        self.assertEqual((info["run_count"], info["step_count"], info["artifact_count"]), (2, 3, 3))
        self.assertEqual([q["step_id"] for q in info["recent"]], ["s1", "s2"])
        self.assertEqual(info["updated_at"], "2026-11-06T10:30:00+08:00")
        page = fs[info["index"]].decode()
        self.assertEqual(page.count("<details open>"), 2)
        self.assertIn("已跳过", page)
        self.assertIn("本轮尚无已记录步骤", page)
        self.assertNotIn("<script>", page)
        base = posixpath.dirname(info["index"])
        for target in re.findall(r'href="([^"]+)"', page):
            self.assertIn(posixpath.normpath(posixpath.join(base, target)), fs)
        doc = json.loads(fs[info["manifest"]])
        pending, executed = doc["runs"]
        self.assertEqual((pending["id"], executed["id"]), ("r2", "r1"))
        step = executed["steps"][0]
        self.assertEqual(step["seq"], 1)
        self.assertEqual(step["updated_at"], "2026-11-06T01:15:00Z")
        self.assertEqual(step["output_artifact_id"], {"id": "missing", "path": None})
        self.assertEqual(step["other_artifacts"][0]["id"], "extra")
        log_path = info["recent"][0]["path"]
        log = json.loads(fs[log_path])
        self.assertEqual(log["step"], self.data["run_steps"][0])
        for ref in [log["artifact_links"]["input_artifact_id"], log["artifact_links"]["reused_artifact_id"],
                    *log["other_artifacts"]]:
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(log_path), ref["path"]))
            self.assertEqual(json.loads(fs[resolved]), next(a for a in self.data["artifacts"] if a["id"] == ref["id"]))
        run_log = json.loads(fs[posixpath.join(base, executed["path"])])
        for ref in [*run_log["steps"], *run_log["artifacts"], run_log["input_artifact"]]:
            self.assertIn(posixpath.normpath(posixpath.join(base, posixpath.dirname(executed["path"]), ref["path"])), fs)
        self.assertFalse(any(b"should not be exported" in b for b in fs.values()))

    def test_no_case_or_no_case_run(self):
        self.data["runs"] = [self.data["runs"][-1]]
        self.assertEqual(self.export(), (None, {}))
        self.data["cases"] = []
        self.assertEqual(self.export(), (None, {}))

    def test_changed_artifact_or_step_creates_new_snapshot(self):
        before = self.export()
        self.data["runs"].reverse()
        self.data["run_steps"].reverse()
        self.data["artifacts"].reverse()
        self.assertEqual(self.export(), before)
        self.data["artifacts"][-1]["content_json"]["v"] = 2
        self.assertNotEqual(self.export()[0]["index"], before[0]["index"])

    def test_reject_foreign_primary_pointer_without_reading_its_content(self):
        self.data["run_steps"][0]["input_artifact_id"] = "private"
        with self.assertRaisesRegex(ValueError, "another Run"):
            self.export()

    def test_foreign_tenant_or_sequence_collision_refused(self):
        self.data["run_steps"][1]["seq"] = 1
        with self.assertRaisesRegex(ValueError, "Duplicate Case step sequence"):
            self.export()
        self.data["run_steps"][1]["seq"] = 2
        self.data["run_steps"][1]["tenant_id"] = "bad-tenant"
        with self.assertRaisesRegex(ValueError, "tenant boundary"):
            self.export()


if __name__ == "__main__":
    unittest.main()
