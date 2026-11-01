"""Direct report-phase, alias and fresh-query examples through the Case API."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch
from uuid import UUID

import httpx
from jsonschema import Draft202012Validator

import test_case_analysis_api as base
from app.investigation_v2 import case_analysis as analysis, case_analysis_models as models
from app.investigation_v2.case_synthesis import validate_synthesis


class StructuredReportExamples(IsolatedAsyncioTestCase):
    add = base.CaseAnalysisExamples.add
    start = base.CaseAnalysisExamples.start

    async def execute(self, statement, params=None):
        if base.Alert in [item.get("entity") for item in getattr(statement, "column_descriptions", [])]:
            return base.result(rows=self.alerts)
        return await base.CaseAnalysisExamples.execute(self, statement, params)

    async def asyncSetUp(self):
        await base.CaseAnalysisExamples.asyncSetUp(self)
        self.alerts = [self.alert, base.fixtures.alert(2)]
        self.case.alert_ids = [a.id for a in self.alerts]
        for index, alert in enumerate(self.alerts):
            alert.raw_event = {"full_log": f"process activity for selected member {index + 1}", "approval_status": "not_supplied"}
            alert.description = "Original source is retained without clipping."
        self.report = {
            "summary": "已读取进程和网络记录，HTTPS尚未确认，行为性质待核。",
            "findings": [{"text": "窗口内有进程和TCP连接记录。", "evidence_ids": ["E1", "E2"]}],
            "counterevidence": [], "gaps": ["应用层协议和授权材料未确认。"], "recommendations": ["补充来源材料。"],
            "member_assessments": [{"alert_ref": f"A{i+1}", "status": "unresolved", "role": "undetermined",
                "summary": "原始材料与查询结果已读取，性质待核。", "evidence_ids": [f"A{i+1}", "E1"]} for i in range(2)],
            "relationships": [{"alert_refs": ["A1", "A2"], "kind": "shared_context", "assessment": "hypothesis",
                "basis": "具有共同主机，因果关系待核。", "evidence_ids": ["A1", "A2", "E1"]}],
            "open_questions": [{"question": "连接用途和授权情况是什么？", "alert_refs": ["A1", "A2"],
                "evidence_ids": ["A1", "A2", "E2"], "missing_evidence": "用途和授权材料", "suggested_action": "核对原始记录。"}]}
        self.bad_report = None
        self.report_count = 0
        self.finish_signal = False
        self.unknown_usage = False
        self.wire = []

        async def lake(sql, **kwargs):
            if "class_uid = 4001" in sql:
                return SimpleNamespace(columns=["event_id", "event_time", "src_hostname", "process_name", "source_ip", "dest_ip", "dst_port", "protocol"],
                    rows=[("source-event-01", base.NOW, "host-01", "powershell.exe", "192.0.2.1", "198.51.100.1", 443, "TCP")])
            return SimpleNamespace(columns=["event_id", "event_time", "src_hostname", "process_name", "file_path", "hash_sha256", "user_name", "class_uid", "activity_id", "action", "outcome"],
                rows=[("source-event-01", base.NOW, "host-01", "powershell.exe", "script.ps1", "a" * 64, "alice", 1007, 1, "start", "")])
        self.lake.side_effect = lake
        original_client = type(self.client)
        patcher = patch.object(models.httpx, "AsyncClient", side_effect=lambda **kwargs:
            original_client(transport=httpx.MockTransport(self.provider), **kwargs))
        patcher.start(); self.addCleanup(patcher.stop)

    def provider(self, request):
        body = json.loads(request.content); self.wire.append(body)
        if body.get("response_format"):
            self.report_count += 1
            report = self.bad_report if self.bad_report and self.report_count == 1 else self.report
            message = {"content": json.dumps(report, ensure_ascii=False)}
        else:
            name = (body.get("tool_choice") or {}).get("function", {}).get("name") if isinstance(body.get("tool_choice"), dict) else None
            name = name or ("finish_analysis" if self.finish_signal else "process_activity")
            message = {"tool_calls": [{"id": "call-" + str(len(self.wire)), "type": "function", "function": {
                "name": name, "arguments": "{ \n }" if name == "finish_analysis" else json.dumps({"hostname": "host-01", "limit": 20})}}]}
        payload = {"choices": [{"message": message, "finish_reason": "tool_calls" if "tool_calls" in message else "stop"}],
                   "usage": {"prompt_tokens": 300, "completion_tokens": 100}}
        if self.unknown_usage: payload.pop("usage")
        return httpx.Response(200, json=payload)

    async def run_case(self, key=100, **options):
        return await self.client.post(self.path + "/investigate", json={"operation_key": str(UUID(int=key)),
            "start": base.NOW.isoformat(), "end": (base.NOW + timedelta(minutes=5)).isoformat(),
            "required_tools": ["process_activity", "network_connections"], **options})

    async def test_first_report_has_schema_and_public_uuid_readback(self):
        response = await self.run_case(refresh_queries=True)
        data = response.json(); self.assertEqual(data["status"], "completed", data)
        self.assertEqual(len(self.wire), 3)
        self.assertEqual(self.lake.await_count, 2)
        self.assertTrue(all(not m.get("response_format") for m in self.wire[:2]))
        final = self.wire[2]; self.assertNotIn("tools", final)
        schema = final["response_format"]["json_schema"]["schema"]
        Draft202012Validator(schema).validate(self.report)
        self.assertEqual(schema["$defs"]["MemberAssessment"]["properties"]["alert_ref"]["enum"], ["A1", "A2"])
        view = json.loads(self.wire[0]["messages"][1]["content"])
        self.assertEqual(view["selected_member_refs"], ["A1", "A2"])
        self.assertNotIn("selected_member_ids", view)
        self.assertEqual(data["result"]["report"]["relationships"][0]["alert_ids"], [str(a.id) for a in self.alerts])
        self.assertFalse(any(item.get("reused_from") for item in data["result"]["evidence"]))
        for item in data["result"]["evidence"]:
            if item["kind"] == "alert":
                self.assertFalse(item["data"]["source_material"]["raw_event"]["truncated"])
                self.assertIn("full_log", item["data"]["source_material"]["raw_event"]["text"])
        for call in self.lake.call_args_list:
            self.assertEqual(call.kwargs["params"]["tenant_id"], str(base.TENANT))
            self.assertEqual(call.kwargs["params"]["hostname"], "host-01")
        read = await self.client.get(self.path + f"/investigations/{data['run_id']}")
        self.assertEqual(read.json()["result"], data["result"])

    async def test_refresh_queries_bypasses_existing_same_material_result(self):
        first = (await self.run_case()).json(); self.assertEqual(first["status"], "completed", first)
        second = (await self.run_case(key=101, previous_run_id=first["run_id"], refresh_queries=True)).json()
        self.assertEqual(second["status"], "completed", second)
        self.assertEqual(self.lake.await_count, 4)
        self.assertTrue(all(not e.get("reused_from") for e in second["result"]["evidence"] if e.get("kind") == "tool"))
        read = await self.client.get(self.path + f"/investigations/{first['run_id']}")
        self.assertEqual(read.json()["result"], first["result"])

    async def test_one_correction_reports_exact_missing_citations_after_reference_dedup(self):
        self.bad_report = deepcopy(self.report)
        self.bad_report["relationships"][0].update(alert_refs=["A1", "A2", "A2"], evidence_ids=["E1"])
        data = (await self.run_case()).json(); self.assertEqual(data["status"], "completed", data)
        self.assertEqual(len(self.wire), 4)
        self.assertEqual(self.lake.await_count, 2)
        feedback = json.loads(self.wire[-1]["messages"][-1]["content"].split("\n", 1)[1])
        self.assertIn({"location": ["relationships", 0, "evidence_ids"], "type": "missing_member_source_reference", "required": ["A1", "A2"]}, feedback["errors"])
        self.assertEqual(data["result"]["usage"]["model_calls"], 4)

    async def test_finish_signal_is_not_counted_as_source_query(self):
        self.finish_signal = True
        # Only the first required Tool is needed in this scenario.
        self.report["findings"][0]["evidence_ids"] = ["E1"]
        self.report["open_questions"][0]["evidence_ids"] = ["A1", "A2", "E1"]
        data = (await self.run_case(required_tools=["process_activity"])).json()
        self.assertEqual(data["status"], "completed", data)
        self.assertEqual(data["result"]["usage"]["tool_calls"], 1)
        self.assertEqual(self.lake.await_count, 1)
        compact = analysis.compact_correction(self.wire[-1]["messages"])
        self.assertFalse(any("report_phase" in item for item in json.loads(compact[1]["content"])["evidence"]))

    async def test_unknown_usage_stops_before_database_query(self):
        self.unknown_usage = True
        data = (await self.run_case()).json()
        self.assertEqual(data["result"]["stop_reason"], "usage_unknown_or_budget_exhausted")
        self.assertEqual(self.lake.await_count, 0)
        self.assertEqual(len(self.wire), 1)

    async def test_reference_normalization_never_invents_sources_or_merges_judgments(self):
        context = {"evidence": [{"kind": "alert", "evidence_id": f"A{i+1}", "data": {"alert_id": str(a.id)}} for i,a in enumerate(self.alerts)]}
        evidence = context["evidence"] + [{"evidence_id": "E1"}, {"evidence_id": "E2"}]
        duplicate = deepcopy(self.report);duplicate["relationships"][0]["alert_refs"].append("A2")
        mapped = models.translate_report(duplicate, context, evidence)
        self.assertEqual(len(mapped["relationships"][0]["alert_ids"]), 2)
        for field, change in [("unknown", lambda r:r["relationships"][0]["alert_refs"].append("A99")),
                              ("duplicate_judgment", lambda r:r["member_assessments"].append(deepcopy(r["member_assessments"][0]))),
                              ("missing_sources", lambda r:r["relationships"][0].update(evidence_ids=["E1"]))]:
            with self.subTest(field=field):
                report = deepcopy(self.report);change(report)
                with self.assertRaises(models.ReportContractError):models.translate_report(report, context, evidence)

    async def test_r9_uncertain_protocol_phrases_and_unsupported_claims(self):
        context = {"selected_member_ids": [str(a.id) for a in self.alerts], "read_member_ids": [str(a.id) for a in self.alerts],
            "evidence": [{"kind": "alert", "evidence_id": f"A{i+1}", "data": {"alert_id": str(a.id)}} for i,a in enumerate(self.alerts)]}
        evidence = context["evidence"] + [{"evidence_id": "E1", "kind": "tool", "tool": "network_connections", "available": True, "rows": [{"protocol": "TCP"}]} , {"evidence_id": "E2", "kind": "tool", "tool": "process_activity"}]
        report = models.translate_report(self.report, context, evidence)
        for text in ["无法确认流量是否为 HTTPS 或具体内容。", "无法验证 HTTPS 状态。", "HTTPS尚未确认。"]:
            report["summary"] = text;validate_synthesis(report, context, evidence)
        for text in ["已确认HTTPS通信。", "不是HTTPS。", "HTTPS尚未确认，但TLS已证实。"]:
            report["summary"] = text
            with self.assertRaises(models.ReportContractError):validate_synthesis(report, context, evidence)

    async def test_r10_duplicate_triage_is_removed_only_from_model_view(self):
        root = Path(__file__).resolve().parents[3] / "docs/operations/evidence/investigation-audit-fixes-20261031/live-r10/results"
        context = json.loads(next(root.glob("*-step-1.response.txt")).read_text(encoding="utf-8"))["data"]
        original = deepcopy(context)
        view = analysis.model_context(context)
        for item in view["evidence"]:
            if item["kind"] == "alert":
                self.assertNotIn("saved_analysis", item["data"])
                self.assertEqual(item["data"]["saved_analysis_refs"], [item["evidence_id"].replace("A", "T")])
                saved = next(x for x in original["evidence"] if x["evidence_id"] == item["evidence_id"])
                self.assertEqual(json.loads(item["data"]["source_material"]["raw_event"]["text"]),
                                 json.loads(saved["data"]["source_material"]["raw_event"]["text"]))
            elif item["kind"] == "triage":
                self.assertEqual(item, next(x for x in original["evidence"] if x["evidence_id"] == item["evidence_id"]))
        self.assertEqual(context, original)
        alert = next(x for x in context["evidence"] if x["kind"] == "alert")
        alert["data"].update(saved_analysis="Different prior judgment", saved_analysis_truncated=False)
        self.assertEqual(analysis.model_context(context)["evidence"][0]["data"]["saved_analysis"], "Different prior judgment")

    async def test_empty_and_unavailable_results_keep_their_boundaries_in_report_and_model(self):
        for index, failed in enumerate((False, True)):
            with self.subTest(failed=failed):
                self.wire.clear()
                self.lake.side_effect = RuntimeError("source unavailable") if failed else None
                self.lake.return_value = SimpleNamespace(columns=[], rows=[])
                self.report["summary"] = "告警原文已读取，本次未取得可独立核验的行为记录，原因未知。"
                self.report["findings"] = []
                data = (await self.run_case(key=110+index, refresh_queries=True)).json()
                self.assertEqual(data["status"], "completed", data)
                for request in self.wire:
                    self.assertIn(analysis.EVIDENCE_RULES, request["messages"][0]["content"])
                sources = data["result"]["report"]["query_sources"]
                self.assertTrue(all(s["query_status"] == ("unavailable" if failed else "success_empty") for s in sources))
                self.assertTrue(all(s["returned_count"] == (None if failed else 0) for s in sources))
                final = self.wire[-1]["messages"]
                for message in final:
                    if message["role"] == "tool":
                        evidence = json.loads(message["content"])
                        if failed:
                            self.assertNotIn("empty_result_boundary", evidence)
                        else:
                            self.assertEqual(evidence["empty_result_boundary"]["absence_reason"], "unknown")
                compact = analysis.compact_correction(final)
                self.assertIn(analysis.EVIDENCE_RULES, compact[0]["content"])
                if not failed:
                    self.assertIn("不能反证告警", data["result"]["markdown"])
                    self.assertEqual([x["empty_result_boundary"]["coverage"] for x in json.loads(compact[1]["content"])["evidence"]
                                      if x.get("kind") == "tool"], ["unknown", "unknown"])
                read = await self.client.get(self.path + f"/investigations/{data['run_id']}")
                self.assertEqual(read.json()["result"], data["result"])
