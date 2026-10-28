"""Three-alert Case synthesis through the current API and model HTTP protocol."""
from copy import deepcopy
from datetime import timedelta
import json
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
from uuid import UUID

import httpx

import test_case_analysis_api as examples
from app.investigation_v2.case_synthesis import build_timeline
from app.models.alert import Alert

ORIGINAL_CLIENT = httpx.AsyncClient


class MultiAlertExamples(IsolatedAsyncioTestCase):
    add = examples.CaseAnalysisExamples.add
    start = examples.CaseAnalysisExamples.start

    async def asyncSetUp(self):
        await examples.CaseAnalysisExamples.asyncSetUp(self)
        self.alerts = [examples.fixtures.alert(index) for index in (1, 2, 3)]
        for index, alert in enumerate(self.alerts):
            alert.event_time = examples.NOW + timedelta(minutes=index)
            alert.affected_users = ["alice"] if index < 2 else ["bob"]
        self.alerts[2].affected_hosts = ["printer-03"]
        self.alerts[2].affected_ips = ["192.0.2.3"]
        self.alerts[2].entities = [{"type": "host", "value": "printer-03"}]
        self.case.alert_ids = [alert.id for alert in self.alerts]
        ids = [str(alert.id) for alert in self.alerts]
        self.conclusion = {
            "summary": "前两条告警共享主机，第三条作为背景；完整行为联系尚待核对。",
            "findings": [{"text": "主机返回PowerShell进程记录", "evidence_ids": ["A1", "E1"]}],
            "counterevidence": ["第三条告警涉及另一主机和账号"], "gaps": [], "recommendations": [],
            "member_assessments": [
                {"alert_id": ids[0], "status": "addressed", "role": "supporting", "summary": "进程记录已读取",
                 "evidence_ids": ["A1", "E1"]},
                {"alert_id": ids[1], "status": "unresolved", "role": "supporting", "summary": "外联归属尚缺行为材料",
                 "evidence_ids": ["A2"]},
                {"alert_id": ids[2], "status": "addressed", "role": "background", "summary": "另一主机和账号，当前作为背景",
                 "evidence_ids": ["A3"]}],
            "relationships": [{"alert_ids": ids[:2], "kind": "shared_context", "assessment": "supported",
                               "basis": "前两条告警共享host-01且时间相近，不能据此推断因果", "evidence_ids": ["A1", "A2"]}],
            "open_questions": [{"question": "外联是否由可疑进程发起？", "alert_ids": ids[:2],
                                "evidence_ids": ["A1", "A2", "E1"], "missing_evidence": "直接关联进程与连接的记录",
                                "suggested_action": "补查网络连接及进程关联字段"}],
        }
        patcher = patch.object(examples.models.httpx, "AsyncClient", side_effect=lambda **kwargs: ORIGINAL_CLIENT(
            transport=httpx.MockTransport(self.provider), **kwargs))
        patcher.start()
        self.addCleanup(patcher.stop)

    async def execute(self, statement, params=None):
        if Alert in [item.get("entity") for item in getattr(statement, "column_descriptions", [])]:
            return examples.result(rows=self.alerts)
        return await examples.CaseAnalysisExamples.execute(self, statement, params)

    def provider(self, request):
        body = json.loads(request.content)
        self.messages.append(body)
        if body["messages"][-1]["role"] != "tool":
            message = {"tool_calls": [{"id": "call-process", "type": "function", "function": {
                "name": "process_activity", "arguments": json.dumps({"hostname": "host-01", "limit": 20})}}]}
            finish = "tool_calls"
        else:
            message = {"content": json.dumps(self.conclusion, ensure_ascii=False)}
            finish = "stop"
        return httpx.Response(200, json={"choices": [{"message": message, "finish_reason": finish}],
                                        "usage": {"prompt_tokens": 100, "completion_tokens": 50}})

    async def test_three_members_relationship_timeline_and_open_question_are_saved(self):
        response = await self.start()
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["result"]["completion"], "partial")
        report = data["result"]["report"]
        self.assertEqual(report["member_coverage"], {"selected_count": 3, "read_count": 3, "addressed_count": 2,
            "unresolved_count": 1, "not_assessed_count": 0, "source_unavailable_count": 0})
        self.assertEqual(report["relationships"], self.conclusion["relationships"])
        self.assertEqual(report["open_questions"], self.conclusion["open_questions"])
        self.assertEqual([row["evidence_id"] for row in report["timeline"]], ["A1", "E1", "A2", "A3"])
        process = report["timeline"][1]
        self.assertEqual(process["source_record_id"], "event-7001")
        self.assertEqual(process["row_index"], 0)
        self.assertEqual(process["candidate_member_ids"], [str(UUID(int=1)), str(UUID(int=2))])
        self.assertTrue(process["in_window"])
        context = json.loads(self.messages[0]["messages"][1]["content"])
        third = next(item for item in context["evidence"] if item["evidence_id"] == "A3")
        self.assertIn({"type": "user", "value": "bob"}, third["data"]["entities"])
        self.assertIn("member_assessments", self.messages[0]["messages"][0]["content"])
        self.assertEqual(self.messages[0]["max_tokens"], 3000)
        downloaded = (await self.client.get(data["report_url"])).text
        for label in ("成员覆盖与判断", "跨告警关联依据", "来源时间线", "未决问题", "event-7001"):
            self.assertIn(label, downloaded)
        self.assertEqual((await self.client.get(data["result_url"])).json()["result"], data["result"])
        self.assertEqual(len(self.messages), 2)

    async def test_omitted_and_unreadable_members_remain_open(self):
        self.case.alert_ids.append(UUID(int=4))
        self.conclusion["member_assessments"].pop()
        self.conclusion["relationships"][0]["assessment"] = "hypothesis"
        self.conclusion["open_questions"] = []
        response = await self.start()
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()["result"]
        coverage = result["report"]["member_coverage"]
        self.assertEqual((coverage["selected_count"], coverage["read_count"]), (4, 3))
        self.assertEqual(coverage["not_assessed_count"], 1)
        self.assertEqual(coverage["source_unavailable_count"], 1)
        self.assertEqual(result["report"]["member_assessments"][-2]["status"], "not_assessed")
        self.assertEqual(result["report"]["member_assessments"][-1]["status"], "source_unavailable")
        self.assertEqual(len(result["report"]["open_questions"]), 4)
        self.assertTrue(any(item["question"].startswith("该关联是否成立") for item in result["report"]["open_questions"]))
        self.assertEqual(result["completion"], "partial")

    async def test_outside_members_and_unknown_references_do_not_become_conclusions(self):
        original = deepcopy(self.conclusion)
        for key, invalid in ((120, "member"), (121, "evidence")):
            with self.subTest(invalid=invalid):
                self.conclusion = deepcopy(original)
                if invalid == "member":
                    self.conclusion["relationships"][0]["alert_ids"].append(str(UUID(int=999)))
                else:
                    self.conclusion["open_questions"][0]["evidence_ids"].append("E999")
                response = await self.start(key)
                self.assertEqual(response.status_code, 200, response.text)
                data = response.json()
                self.assertEqual(data["status"], "failed")
                self.assertEqual(data["result"]["stop_reason"], "invalid_or_unreferenced_conclusion")
                self.assertEqual(data["result"]["report"]["relationships"], [])
                self.assertEqual(data["result"]["report"]["member_coverage"]["not_assessed_count"], 3)

    async def test_timeline_keeps_unknown_times_and_marks_outside_window(self):
        rows = build_timeline({"start": examples.NOW.isoformat(), "end": (examples.NOW + timedelta(minutes=5)).isoformat()}, [
            {"kind": "alert", "evidence_id": "A1", "data": {"alert_id": str(UUID(int=1)), "title": "Earlier alert",
              "hosts": ["host-01"], "event_time": examples.NOW - timedelta(minutes=1)}},
            {"kind": "tool", "tool": "process_activity", "evidence_id": "E1", "available": True,
             "query_scope": {"hostname": "host-01"}, "rows": [{"event_id": "unknown-time", "process_name": "powershell.exe"}]},
        ])
        self.assertFalse(rows[0]["in_window"])
        self.assertIsNone(rows[1]["timestamp"])
        self.assertIsNone(rows[1]["in_window"])
        self.assertEqual(rows[1]["source_record_id"], "unknown-time")
