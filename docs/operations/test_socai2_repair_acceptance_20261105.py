"""Offline packet identity isolation and review-gate checks; no network."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import UUID

import prepare_socai2_repair_acceptance_20261105 as preparation

spec = importlib.util.spec_from_file_location("repair_remote", preparation.ROOT / "deploy/aisoc21/repair_acceptance_remote_20261105.py")
remote = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remote)
sys.path.insert(0, str(preparation.ROOT / "deploy/aisoc21"))
import repair_page_proxy_20261105 as proxy


class RepairPreparationTest(unittest.TestCase):
    def test_new_identities_and_bounded_two_card_packet(self):
        with tempfile.TemporaryDirectory(prefix="next-repair-offline-", dir=preparation.ROOT / ".local/releases") as directory:
            candidate = Path(directory)
            files = {"app/socai2/baseline_contracts.py": 'FULL_EXECUTOR_VERSION = "socai2.baseline-executor.v2"\n',
                "app/socai2/case_service.py": 'max_tokens=48000\npolicy_version="socai2.manual-http.v2"\n'}
            for name, content in files.items():
                path = candidate / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            manifest = {"image": "synthetic-offline-only", "files": {name: {"sha256": preparation.sha(candidate / name),
                "bytes": (candidate / name).stat().st_size} for name in files}}
            (candidate / "manifest.json").write_text(json.dumps(manifest))
            with tempfile.TemporaryDirectory() as output, patch.object(preparation, "OUT", Path(output) / "packet"), \
                    patch("sys.argv", ["prepare", "--candidate", str(candidate)]):
                preparation.main()
                plan = json.loads((preparation.OUT / "plan.json").read_text())
                self.assertEqual((plan["max_model_calls"], plan["max_runs"], plan["new_alerts"]), (22, 10, 4))
                self.assertEqual(plan["initial_analysis_schema"], "socai2.baseline-analysis.v2")
                first, second = plan["cases"]
                self.assertNotEqual(first["host"], second["host"])
                self.assertNotEqual(first["window_start"], second["window_start"])
                all_ids = [alert["source_alert_id"] for case in plan["cases"] for alert in case["alerts"]]
                self.assertEqual(len(set(all_ids)), 4)
                old = json.loads((preparation.ROOT / "docs/operations/evidence/socai2-kafka-chain-20261105/k2/plan.json").read_text())
                old_ids = {alert["source_alert_id"] for case in old["cases"] for alert in case["alerts"]}
                self.assertFalse(set(all_ids) & old_ids)
                for case in plan["cases"]:
                    for alert, event in zip(case["alerts"], case["events"], strict=True):
                        self.assertEqual(alert["source_event_ids"], [event["event_id"]])
                        self.assertEqual(alert["event_time"], event["ocsf_event"]["time"])
                        raw = json.loads(event["ocsf_event"]["raw_data"])
                        self.assertEqual(raw["time"], event["ocsf_event"]["time"])
                        self.assertEqual(raw["device"]["name"], case["host"])
                with self.assertRaises(FileExistsError):
                    preparation.main()

    def test_semantic_gate_binds_review_to_exact_first_result(self):
        accepted = {"approved": True, "reviewer": "root", "result_id": "result-a",
            "plan_sha256": "plan-a", "first_result_sha256": "answer-a"}
        remote.semantic_gate(accepted, "result-a", "plan-a", "answer-a")
        for changes in ({"approved": False}, {"reviewer": "automatic"}, {"result_id": "result-b"},
                        {"plan_sha256": "plan-b"}, {"first_result_sha256": "answer-b"}):
            with self.assertRaises(AssertionError):
                remote.semantic_gate({**accepted, **changes}, "result-a", "plan-a", "answer-a")

    def test_page_proxy_denies_cross_case_machine_and_unbounded_requests(self):
        cid, tid, rid = map(str, (UUID(int=1), UUID(int=2), UUID(int=3)))
        base = "/api/v1/socai2/cases/" + cid
        for suffix in ("", "/history?limit=20", "/tasks?limit=20&offset=0", "/tasks/" + tid,
                       "/tasks/" + tid + "/revisions", "/runs/" + rid, "/results/" + rid,
                       "/runs/" + rid + "/materials/" + tid):
            self.assertTrue(proxy.allowed("GET", base + suffix, cid))
        self.assertTrue(proxy.allowed("POST", base + "/tasks", cid))
        self.assertTrue(proxy.allowed("PUT", base + "/tasks/" + tid, cid, tid))
        for method, target in (("POST", base + "/runs/" + rid + "/start"), ("POST", base + "/baseline/prepare"),
                ("GET", "/api/v1/socai2/cases"), ("GET", base.replace(cid, tid)), ("POST", base + "/associations"),
                ("GET", base + "/history?limit=999"), ("GET", base + "/tasks?offset=1001"),
                ("GET", base + "/history?limit=20&limit=50"), ("GET", base + "/tasks?tenant_id=" + rid),
                ("GET", base + "/%2e%2e/tasks"), ("GET", "http://remote.example" + base),
                ("DELETE", base + "/tasks/" + tid), ("PUT", base + "/tasks/" + rid)):
            self.assertFalse(proxy.allowed(method, target, cid, tid), (method, target))
        self.assertFalse(proxy.allowed("POST", base + "/tasks", cid, tid))

    def test_page_h_readback_matches_closed_review_and_never_creates(self):
        task = {"id": "task-a", "case_id": "case-a", "current_revision_id": "revision-a",
            "current": {"state": "completed", "result_scope": {"alert_ids": ["alert-a"]}, "completed_by": "user-a"}}
        task_hash = proxy.digest_json(task)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            session = {"closed": True, "case_id": "case-a", "task_id": "task-a",
                "final_revision_id": "revision-a", "final_task_sha256": task_hash}
            (root / "page-session-end.json").write_text(json.dumps(session))
            approval = {"approved": True, "reviewer": "root", "plan_sha256": "plan-a", "first_result_id": "first-a",
                "task_id": "task-a", "task_revision_id": "revision-a", "task_sha256": task_hash,
                "session_end_sha256": remote.sha(root / "page-session-end.json")}
            helper = SimpleNamespace(ROOT=root, service=SimpleNamespace(USER="user-a"), http=Mock(return_value=task),
                read=lambda name: {"page-human-review": approval, "page-session-end": session, "page-H-task": task}[name])
            receipt = remote.page_human(helper, "case-a", "first-a", "plan-a", "alert-a")
            self.assertFalse(receipt["created_by_driver"])
            helper.http.assert_called_once_with("page-H-current", "GET", "/api/v1/socai2/cases/case-a/tasks/task-a")
            helper.http.return_value = {**task, "current_revision_id": "revision-b"}
            with self.assertRaises(AssertionError):
                remote.page_human(helper, "case-a", "first-a", "plan-a", "alert-a")
            session["closed"] = False
            with self.assertRaises(AssertionError):
                remote.page_human(helper, "case-a", "first-a", "plan-a", "alert-a")

    def test_page_second_round_never_posts_another_human_task(self):
        approval = {"approved": True, "reviewer": "root", "result_id": "first-a",
            "plan_sha256": "hash", "first_result_sha256": "hash"}
        reads = {"semantic-review": approval, "case-create-response": {"body": {"case_id": "case-a", "scope_revision": 1}}}
        helper = SimpleNamespace(ROOT=Path("/tmp/synthetic-page-test"), read=lambda name: reads[name],
            accepted_first_result=Mock(return_value="first-a"), save=Mock(), uid=lambda value: value,
            http=Mock(return_value={"pending_run_id": "next-run"}), start_round=Mock())
        scenario = {"window_start": None, "window_end": None}
        with patch.object(remote, "core_gate"), patch.object(remote, "verify_runtime", return_value={}), \
                patch.object(remote, "card", return_value=(scenario, helper, ["alert-a", "alert-b"], "incident-a")), \
                patch.object(remote, "sha", return_value="hash"), patch.object(remote, "page_human", return_value={"origin": "page"}):
            remote.second({}, Path("/tmp/synthetic-release"), None, "deepseek", "page")
        self.assertEqual([call.args[1] for call in helper.http.call_args_list], ["POST", "GET", "GET"])
        self.assertTrue(helper.http.call_args_list[0].args[2].endswith("/baseline/prepare"))
        helper.start_round.assert_called_once_with("C2", "case-a", "next-run", 1, "first-a")


if __name__ == "__main__":
    unittest.main()
