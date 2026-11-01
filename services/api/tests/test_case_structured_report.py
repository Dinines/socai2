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
        self.assertEqual(view["case_material"]["description"]["source_path"], "Case.description")
        for item in view["evidence"]:
            if item["kind"] == "alert":
                self.assertEqual(item["data"]["source_material"]["description"]["source_path"], "Alert.description")
                self.assertEqual(item["data"]["source_material"]["raw_event"]["source_path"], "Alert.raw_event")
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
        self.assertIn({"location": ["relationships", 0, "evidence_ids"], "issue": "引用须包含涉及成员的告警来源", "required": ["A1", "A2"]}, feedback["errors"])
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
        evidence = context["evidence"] + [{"evidence_id": "E1", "kind": "tool"}, {"evidence_id": "E2", "kind": "tool"}]
        duplicate = deepcopy(self.report);duplicate["relationships"][0]["alert_refs"].append("A2")
        mapped = models.translate_report(duplicate, context, evidence)
        self.assertEqual(len(mapped["relationships"][0]["alert_ids"]), 2)
        for field, change in [("unknown", lambda r:r["relationships"][0]["alert_refs"].append("A99")),
                              ("duplicate_judgment", lambda r:r["member_assessments"].append(deepcopy(r["member_assessments"][0])))]:
            with self.subTest(field=field):
                report = deepcopy(self.report);change(report)
                with self.assertRaises(models.ReportContractError):models.translate_report(report, context, evidence)
        missing = deepcopy(self.report); missing["relationships"][0].update(evidence_ids=["E1"])
        context.update(selected_member_ids=[str(a.id) for a in self.alerts], read_member_ids=[str(a.id) for a in self.alerts])
        with self.assertRaisesRegex(models.ReportContractError, "missing_member_source_reference"):
            validate_synthesis(models.translate_report(missing, context, evidence), context, evidence)

    async def test_r9_uncertain_protocol_phrases_and_unsupported_claims(self):
        context = {"selected_member_ids": [str(a.id) for a in self.alerts], "read_member_ids": [str(a.id) for a in self.alerts],
            "evidence": [{"kind": "alert", "evidence_id": f"A{i+1}", "data": {"alert_id": str(a.id)}} for i,a in enumerate(self.alerts)]}
        evidence = context["evidence"] + [{"evidence_id": "E1", "kind": "tool", "tool": "network_connections", "available": True, "rows": [{"protocol": "TCP"}]} , {"evidence_id": "E2", "kind": "tool", "tool": "process_activity"}]
        report = models.translate_report(self.report, context, evidence)
        for text in ["无法确认流量是否为 HTTPS 或具体内容。", "无法验证 HTTPS 状态。", "HTTPS尚未确认。",
                     "HTTPS/TLS 状态尚未确认。", "目前属于'HTTPS/TLS 尚未确认'的状态。",
                     "应用协议“TLS 协议尚未证实”，仍需材料。", "无法确认 HTTPS / TLS。"]:
            report["summary"] = text;validate_synthesis(report, context, evidence)
        for text in ["已确认HTTPS通信。", "不是HTTPS。", "HTTPS尚未确认，但TLS已证实。",
                     "不是 HTTPS 尚未确认。", "并非“HTTPS 尚未确认”。", "HTTPS 未确认但TLS已使用。",
                     "未决点需确认协议为 HTTPS/TLS 及目的合法性。",
                     "无法确认HTTPS 流量已证实存在。", "无法确认HTTPS 连接已证实存在。"]:
            report["summary"] = text
            with self.assertRaises(models.ReportContractError):validate_synthesis(report, context, evidence)

    async def test_r11_original_reports_and_control_leaks_are_rejected(self):
        root = Path(__file__).resolve().parents[3] / "docs/operations/evidence/investigation-r11-20261101"
        steps = [json.loads(path.read_text(encoding="utf-8")) for path in (root / "live/results").glob("*-step-*.response.txt")]
        context = next(step["data"] for step in steps if step["seq"] == 1)
        original_context = deepcopy(context)
        evidence = context["evidence"] + [step["data"]["evidence"] for step in steps if "model_message" in step["data"]]
        view = analysis.model_context(context)
        for item in view["evidence"]:
            if item["kind"] == "alert":
                original = next(e for e in context["evidence"] if e["evidence_id"] == item["evidence_id"])
                for field in ("description", "raw_event"):
                    self.assertEqual(item["data"]["source_material"][field]["text"], original["data"]["source_material"][field]["text"])
                    self.assertEqual(item["data"]["source_material"][field]["source_path"], "Alert." + field)
        self.assertEqual(context, original_context)
        for name, expected in (("first-model-report.json", "unobserved_application_protocol_use_gaps"),
                               ("correction-model-report.json", "report_control_text")):
            report = models.translate_report(json.loads((root / name).read_text(encoding="utf-8")), context, evidence)
            with self.subTest(name=name), self.assertRaisesRegex(models.ReportContractError, expected):
                validate_synthesis(report, context, evidence)
        # A correct uncertainty phrase must not mask control text in other sections.
        clean = {**report, "summary": "HTTPS/TLS 状态尚未确认。", "findings": [], "relationships": [],
                 "counterevidence": [], "gaps": [], "recommendations": [], "open_questions": [],
                 "member_assessments": [{**item, "summary": "性质待核。"} for item in report["member_assessments"]]}
        validate_synthesis(clean, context, evidence)
        for section in ("counterevidence", "gaps", "recommendations"):
            with self.subTest(section=section), self.assertRaisesRegex(models.ReportContractError, "report_control_text"):
                validate_synthesis({**clean, section: ["unobserved_application_protocol_use_gaps"]}, context, evidence)
        for field in ("question", "missing_evidence", "suggested_action"):
            item = {"question": "用途是什么？", "alert_ids": [], "evidence_ids": [],
                    "missing_evidence": "用途说明", "suggested_action": "核对来源", field: "依据校验规则，应重写。"}
            with self.subTest(field=field), self.assertRaisesRegex(models.ReportContractError, "report_control_text"):
                validate_synthesis({**clean, "open_questions": [item]}, context, evidence)

    async def test_protocol_observation_and_negation_boundaries(self):
        context = {"selected_member_ids": [str(a.id) for a in self.alerts], "read_member_ids": [str(a.id) for a in self.alerts],
            "evidence": [{"kind": "alert", "evidence_id": f"A{i+1}", "data": {"alert_id": str(a.id)}} for i,a in enumerate(self.alerts)]}
        network = {"evidence_id": "E1", "kind": "tool", "tool": "network_connections", "available": True, "rows": []}
        evidence = context["evidence"] + [network, {"evidence_id": "E2", "kind": "tool", "tool": "process_activity"}]
        report = models.translate_report(self.report, context, evidence)
        cases = [
            ("TCP", "不能不确认 HTTPS。", False), ("TCP", "不得不确认 TLS。", False),
            ("TCP", "无法不确认 SSL。", False), ("TCP", "并不是无法确认 HTTPS。", False),
            ("TCP", "HTTPS / TLS 状态尚未确认。", True), ("TCP", "不能确认 TLSv1.3。", True),
            ("TCP", "HTTPS 尚未确认；但TLSv1.3已经证实。", False),
            ("TLS1.2", "记录明确标注 TLS1.2。", True), ("TLS1.2", "记录明确标注 TLS。", True),
            ("TLS1.2", "记录明确标注 TLSv1.2。", True), ("TLS1.2", "记录明确标注 TLS1.3。", False),
            ("TLS", "记录明确标注 TLS1.3。", False), ("TLS1.2", "TLS1.3 尚未确认。", True),
            ("HTTPS", "记录明确标注 HTTPS。", True), ("TCP", "记录明确标注 HTTPS。", False),
        ]
        for observed, text, accepted in cases:
            with self.subTest(observed=observed, text=text):
                network["rows"] = [{"protocol": observed}]
                report["summary"] = text
                if accepted:
                    validate_synthesis(report, context, evidence)
                else:
                    with self.assertRaisesRegex(models.ReportContractError, "unobserved_application_protocol_use_gaps"):
                        validate_synthesis(report, context, evidence)
        report["summary"] = "记录明确标注 HTTPS。"
        for available, rows in ((False, [{"protocol": "HTTPS"}]), (True, [])):
            with self.subTest(available=available, rows=rows):
                network.update(available=available, rows=rows)
                with self.assertRaises(models.ReportContractError):validate_synthesis(report, context, evidence)

    async def test_control_codes_next_to_chinese_are_not_business_conclusions(self):
        context = {"selected_member_ids": [str(a.id) for a in self.alerts], "read_member_ids": [str(a.id) for a in self.alerts],
            "evidence": [{"kind": "alert", "evidence_id": f"A{i+1}", "data": {"alert_id": str(a.id)}} for i,a in enumerate(self.alerts)]}
        evidence = context["evidence"] + [{"evidence_id": "E1", "kind": "tool"}, {"evidence_id": "E2", "kind": "tool"}]
        report = models.translate_report(self.report, context, evidence)
        for text in ("触发unobserved_application_protocol_use_gaps错误。", "发生report_control_text需重写。",
                     "按照response_format输出报告。", "response_format", "在报告中必须重新填写结论。"):
            with self.subTest(rejected=text):
                report["summary"] = text
                with self.assertRaisesRegex(models.ReportContractError, "report_control_text"):
                    validate_synthesis(report, context, evidence)
        for text in ("业务规则要求核对授权记录。", "根据源记录，校验结果尚未确认。", "需要补充脚本正文和审批材料。"):
            with self.subTest(allowed=text):
                report["summary"] = text
                validate_synthesis(report, context, evidence)

    async def test_history_gap_dedup_and_repeated_compaction_preserve_material(self):
        root = Path(__file__).resolve().parents[3] / "docs/operations/evidence/investigation-audit-fixes-20261031/live-r6/results"
        context = json.loads(next(root.glob("*-followup-step-1.response.txt")).read_text(encoding="utf-8"))["data"]
        history = next(e["data"] for e in context["evidence"] if e["kind"] == "prior_analysis")
        report = history["report"]
        question = {"question": "是否取得审批？", "alert_ids": [context["selected_member_ids"][0]],
                    "evidence_ids": ["A1", "E1"], "missing_evidence": "审批记录", "suggested_action": "核对审批系统"}
        oversized = {**question, "question": "长问题" * 600}
        report["open_questions"] = [oversized, question]
        report["gaps"] = ["仅原报告保留的缺口", "未决问题：" + oversized["question"],
                          "未决问题：" + question["question"], "未决问题：" + question["question"] + "（待补）"]
        original = deepcopy(context)
        view = analysis.model_context(context)
        visible = next(e["data"] for e in view["evidence"] if e["kind"] == "prior_analysis")
        self.assertEqual(visible["report"]["open_questions"], [question])
        self.assertEqual(visible["report"]["gaps"], [report["gaps"][i] for i in (0, 1, 3)])
        self.assertEqual(visible["omitted_report_items"]["open_questions"], 1)
        self.assertEqual(visible["omitted_report_items"]["gaps"], 1)
        self.assertEqual(visible["run_id"], history["run_id"])
        control = {"role": "user", "content": analysis.CORRECTION_PREFIX + analysis.encoded({"errors":
            models.report_feedback([{"type": "json_invalid", "location": [], "instruction": "internal-only"}])})}
        messages = [{"role": "system", "content": analysis.CORRECTION_SYSTEM},
                    {"role": "user", "content": analysis.encoded(view)}, control]
        saved_messages = deepcopy(messages)
        compact = analysis.compact_correction(messages)
        self.assertEqual(analysis.compact_correction(compact), compact)
        self.assertEqual(compact[-1], control)
        self.assertNotIn("internal-only", analysis.encoded(compact))
        self.assertEqual(next(e["data"] for e in json.loads(compact[1]["content"])["evidence"]
                              if e["kind"] == "prior_analysis"), visible)
        self.assertEqual(context, original)
        self.assertEqual(messages, saved_messages)

    async def test_r11_four_reply_replay_preserves_raw_budget_and_failed_report(self):
        root = Path(__file__).resolve().parents[3] / "docs/operations/evidence/investigation-r11-20261101/live/results"
        steps = sorted([json.loads(p.read_text(encoding="utf-8")) for p in root.glob("*-step-*.response.txt")], key=lambda s:s["seq"])
        context = steps[0]["data"]
        original = deepcopy(context)
        replies = [s["data"] for s in steps if "response" in s["data"]]
        tool_results = [s["data"]["evidence"] for s in steps if "model_message" in s["data"]]
        request = analysis.CaseAnalysisRequest.model_validate_json(next(root.glob("*-main.body.json")).read_text(encoding="utf-8"))
        run = base.InvestigationRun(id=UUID(int=850), tenant_id=base.TENANT, case_id=context["case_id"],
                                   raw_alert={"scope": {}}, total_tokens=0, iterations=0)
        self.runs[run.id] = run
        dispatched = []
        async def tool(name, arguments):
            recorded = tool_results[len(dispatched)]
            self.assertEqual((name, arguments), (recorded["tool"], recorded["arguments"]))
            dispatched.append(name)
            return {k:v for k,v in recorded.items() if k not in {"evidence_id", "kind", "tool", "arguments"}}
        def provider(http_request):
            body = json.loads(http_request.content)
            used = sum(r["usage"]["prompt_tokens"] + r["usage"]["completion_tokens"] for r in replies[:len(self.wire)])
            required = sum(len(analysis.encoded(body.get(k), compact=True).encode()) for k in ("messages", "tools", "response_format"))
            required += len(analysis.encoded(body.get("tool_choice"), compact=True).encode()) + models.MAX_OUTPUT_TOKENS + 256
            self.assertLessEqual(required, analysis.LIMITS["tokens"] - used)
            self.wire.append(body)
            reply = replies[len(self.wire)-1]
            return httpx.Response(200, json={"choices": [{"message": reply["response"],
                "finish_reason": "tool_calls" if reply["response"].get("tool_calls") else "stop"}], "usage": reply["usage"]})
        client_type = type(self.client)
        with patch.object(base.tools.CaseTools, "execute", side_effect=tool), patch.object(models.httpx, "AsyncClient",
                side_effect=lambda **kw:client_type(transport=httpx.MockTransport(provider), **kw)):
            outcome = await analysis.CaseAnalysis(self.db, run, context, request).execute()
        self.assertEqual(outcome["status"], "failed", outcome)
        self.assertEqual(outcome["result"]["stop_reason"], "invalid_or_unreferenced_conclusion")
        self.assertEqual((len(self.wire), len(dispatched)), (4, 2))
        self.assertEqual(outcome["result"]["usage"]["known_tokens"], 12728)
        for body in self.wire:
            view = json.loads(body["messages"][1]["content"])
            for original_alert in context["evidence"]:
                if original_alert["kind"] == "alert":
                    alert = next(e for e in view["evidence"] if e["evidence_id"] == original_alert["evidence_id"])
                    self.assertEqual(alert["data"]["source_material"]["raw_event"]["text"],
                                     original_alert["data"]["source_material"]["raw_event"]["text"])
        saved_tools = [e for e in outcome["result"]["evidence"] if e["kind"] == "tool"]
        self.assertEqual(saved_tools, tool_results)
        self.assertTrue(self.wire[-1]["messages"][-1]["content"].startswith(analysis.CORRECTION_PREFIX))
        self.assertNotIn("unobserved_application_protocol_use_gaps", analysis.encoded(self.wire[-1]["messages"]))
        self.assertEqual(outcome["result"]["report"]["member_coverage"]["not_assessed_count"], 2)
        self.assertNotIn("文档服务器", outcome["result"]["markdown"])
        self.assertEqual(context, original)
        self.lake.assert_not_awaited()

    async def test_control_feedback_stays_outside_evidence_and_correction_is_once(self):
        self.bad_report = deepcopy(self.report)
        self.bad_report["summary"] = "在总结中必须明确指出 HTTPS/TLS 状态尚未确认。"
        first = (await self.run_case()).json()
        self.assertEqual(first["status"], "completed", first)
        self.assertEqual(len(self.wire), 4)
        correction = self.wire[-1]["messages"]
        self.assertTrue(correction[-1]["content"].startswith(analysis.CORRECTION_PREFIX))
        self.assertNotIn("report_control_text", analysis.encoded(correction))
        self.assertNotIn(self.bad_report["summary"], analysis.encoded(correction))
        self.assertNotIn("instruction", json.loads(correction[-1]["content"].split("\n", 1)[1])["errors"][0])
        compact = analysis.compact_correction(correction)
        self.assertEqual(compact[-1], correction[-1])
        self.assertNotIn("纠错约束", compact[1]["content"])
        self.assertEqual(json.loads(compact[1]["content"])["case_material"]["description"]["source_path"], "Case.description")
        feedback = [json.loads(a.content) for a in self.artifacts if a.kind == "case_analysis_step" and '"errors"' in a.content]
        self.assertIn("report_control_text", {error["type"] for error in feedback[0]["errors"]})
        self.wire.clear(); self.report_count = 0
        self.report = self.bad_report
        failed = (await self.run_case(key=102)).json()
        self.assertEqual(failed["status"], "failed", failed)
        self.assertEqual(len(self.wire), 4)
        self.assertEqual(failed["result"]["stop_reason"], "invalid_or_unreferenced_conclusion")
        self.assertNotIn(self.bad_report["summary"], failed["result"]["markdown"])

    async def test_r12_source_absence_and_coordinated_protocol_uncertainty(self):
        context = {"selected_member_ids": [str(a.id) for a in self.alerts],
                   "read_member_ids": [str(a.id) for a in self.alerts],
                   "evidence": [{"kind": "alert", "evidence_id": f"A{i+1}", "data": {"alert_id": str(a.id)}}
                                for i, a in enumerate(self.alerts)]}
        evidence = context["evidence"] + [{"evidence_id": "E1", "kind": "tool", "tool": "network_connections",
            "available": True, "rows": [{"protocol": "TCP"}]}, {"evidence_id": "E2", "kind": "tool"}]
        report = models.translate_report(self.report, context, evidence)
        for text in ["原文未声明应用层协议（如 HTTPS），亦未说明流量用途。",
                     "无法分析通信数据方向或确认是否为 HTTPS。"]:
            with self.subTest(text=text):
                report["summary"] = text
                validate_synthesis(report, context, evidence)
        for text in ["并非未声明应用层协议（如 HTTPS）。", "无法分析通信方向，但确认是 HTTPS。",
                     "无法分析已确认HTTPS的流量或确认是否为 TLS。",
                     "未声明应用层协议（如 HTTPS），但TLS已经证实。"]:
            with self.subTest(text=text):
                report["summary"] = text
                with self.assertRaises(models.ReportContractError):
                    validate_synthesis(report, context, evidence)

    async def test_source_identities_use_cited_original_fields_not_other_alerts_or_judgments(self):
        context = {"selected_member_ids": [str(a.id) for a in self.alerts],
                   "read_member_ids": [str(a.id) for a in self.alerts]}
        evidence = [{"kind": "alert", "evidence_id": f"A{i+1}", "data": {
            "alert_id": str(a.id), "source_material": {"raw_event": {"text": json.dumps({
                "full_log": f"powershell.exe PID {4200+i} under {'demo.finance' if i == 0 else 'admin'}"})}},
            "saved_analysis": "User admin 使用进程 PID 9999。"}} for i, a in enumerate(self.alerts)]
        context["evidence"] = evidence
        evidence += [{"kind": "triage", "evidence_id": "T1", "data": {"rationale": "PID 9999，用户root。"}},
                     {"kind": "tool", "evidence_id": "E1", "tool": "process_activity", "available": True,
                      "rows": [{"process_name": "powershell.exe", "user_name": "demo.finance"}]},
                     {"kind": "tool", "evidence_id": "E2", "tool": "network_connections", "available": True, "rows": []}]
        report = models.translate_report(self.report, context, evidence)
        for text, refs, allowed in [
            ("告警原文记录 PID 4200。", ["A1"], True),
            ("告警原文记录 User demo.finance 使用 PID 4200。", ["A1"], True),
            ("告警原文记录 PID 4201。", ["A1"], False),
            ("工具记录 PID 4200。", ["E1"], False),
            ("工具记录用户 demo.finance。", ["E1"], True),
            ("User admin 使用 PID 4200。", ["A1"], False),
            ("查询证实 PID 9999，用户root。", ["T1"], False),
            ("直接观察：PID 4200 已由工具核实。", ["A1", "E1"], False),
            ("告警原文有 PID 4200；工具未核实PID。", ["A1", "E1"], True),
            ("告警原文记录 PID 4200，工具记录用户 demo.finance。", ["A1", "E1"], True),
        ]:
            with self.subTest(text=text, refs=refs):
                report["findings"] = [{"text": text, "evidence_ids": refs}]
                if allowed:
                    validate_synthesis(report, context, evidence)
                else:
                    with self.assertRaisesRegex(models.ReportContractError, "unsupported_source_value"):
                        validate_synthesis(report, context, evidence)
        evidence[-2]["rows"][0]["pid"] = 4200
        report["findings"] = [{"text": "工具记录 PID 4200，用户 demo.finance。", "evidence_ids": ["E1"]}]
        validate_synthesis(report, context, evidence)
        evidence[-2]["available"] = False
        with self.assertRaisesRegex(models.ReportContractError, "unsupported_source_value"):
            validate_synthesis(report, context, evidence)

    async def test_r12_reports_expose_source_errors_after_protocol_false_rejections_are_fixed(self):
        root = Path(__file__).resolve().parents[3] / "docs/operations/evidence/investigation-r12-20261101"
        for label in ("A", "B"):
            with self.subTest(label=label):
                folder = root / label
                context = json.loads(next(folder.glob("*-step-1.response.txt")).read_text(encoding="utf-8"))["data"]
                evidence = json.loads((folder / "003-result.response.txt").read_text(encoding="utf-8"))["result"]["evidence"]
                raw = json.loads((root / f"{label}-model-report-step-14.txt").read_text(encoding="utf-8"))
                report = models.translate_report(raw, context, evidence)
                with self.assertRaises(models.ReportContractError) as raised:
                    validate_synthesis(report, context, evidence)
                errors = raised.exception.errors
                types = {e["type"] for e in errors}
                self.assertIn("unsupported_source_value", types)
                self.assertNotIn("unobserved_application_protocol_use_gaps", types)
                if label == "B":
                    self.assertIn("missing_member_source_reference", types)
                    self.assertIn("report_control_text", types)
                self.assertTrue(any(e.get("value") == ("4209" if label == "A" else "admin") for e in errors))

    async def test_r12_empty_results_do_not_supply_a_missing_data_cause(self):
        folder = Path(__file__).resolve().parents[3] / "docs/operations/evidence/investigation-r12-20261101/B"
        context = json.loads(next(folder.glob("*-step-1.response.txt")).read_text(encoding="utf-8"))["data"]
        evidence = json.loads((folder / "003-result.response.txt").read_text(encoding="utf-8"))["result"]["evidence"]
        original = json.loads((folder.parent / "B-model-report-step-11.txt").read_text(encoding="utf-8"))
        report = models.translate_report(original, context, evidence)
        with self.assertRaises(models.ReportContractError) as raised:
            validate_synthesis(report, context, evidence)
        self.assertIn("unsupported_empty_query_cause", {e["type"] for e in raised.exception.errors})
        self.assertNotIn("unobserved_application_protocol_use_gaps", {e["type"] for e in raised.exception.errors})
        # The same empty results allow a bounded conclusion, not just failure.
        report.update(summary="告警原文已读取；当前查询范围无匹配，原因未知。", findings=[],
                      recommendations=[], open_questions=[], relationships=[])
        report["gaps"] = ["当前来源和范围无匹配，缺失原因未知；不能证明日志丢失。"]
        validate_synthesis(report, context, evidence)
        report["gaps"] = ["空查询无法确认是否日志丢失，但可能由于采样。"]
        with self.assertRaisesRegex(models.ReportContractError, "unsupported_empty_query_cause"):
            validate_synthesis(report, context, evidence)
        report["gaps"] = ["空结果并非不能证明日志丢失。"]
        with self.assertRaisesRegex(models.ReportContractError, "unsupported_empty_query_cause"):
            validate_synthesis(report, context, evidence)

    async def test_one_correction_receives_source_and_reference_errors_together(self):
        self.bad_report = deepcopy(self.report)
        self.bad_report["findings"] = [{"text": "工具确认 PID 9999。", "evidence_ids": ["E1"]}]
        self.bad_report["member_assessments"][1]["evidence_ids"] = ["E1"]
        self.bad_report["gaps"] = ["evidence_id_list_6"]
        data = (await self.run_case()).json()
        self.assertEqual(data["status"], "completed", data)
        self.assertEqual((len(self.wire), self.lake.await_count), (4, 2))
        feedback = json.loads(self.wire[-1]["messages"][-1]["content"].split("\n", 1)[1])
        self.assertEqual({tuple(e["location"]) for e in feedback["errors"]},
                         {("findings", 0, "text"), ("member_assessments", 1, "evidence_ids"), ("gaps", 0)})
        self.assertNotIn("unsupported_source_value", analysis.encoded(self.wire[-1]["messages"]))
        self.assertNotIn("PID 9999", analysis.encoded(self.wire[-1]["messages"]))
        self.assertNotIn("PID 9999", data["result"]["markdown"])
        saved = [json.loads(a.content) for a in self.artifacts if a.kind == "case_analysis_step" and '"errors"' in a.content]
        self.assertEqual({e["type"] for e in saved[0]["errors"]},
                         {"unsupported_source_value", "missing_member_source_reference", "report_control_text"})

    async def test_r12_four_reply_replays_preserve_sources_usage_and_reject_bad_reports(self):
        root = Path(__file__).resolve().parents[3] / "docs/operations/evidence/investigation-r12-20261101"
        for number, label in enumerate(("A", "B")):
            with self.subTest(label=label):
                folder = root / label
                steps = sorted([json.loads(p.read_text(encoding="utf-8")) for p in folder.glob("*-step-*.response.txt")],
                               key=lambda s: s["seq"])
                context = steps[0]["data"]
                original = deepcopy(context)
                replies = [s["data"] for s in steps if "response" in s["data"]]
                results = [s["data"]["evidence"] for s in steps if "model_message" in s["data"]]
                request = analysis.CaseAnalysisRequest.model_validate_json((folder / "002-investigate.body.json").read_text(encoding="utf-8"))
                run = base.InvestigationRun(id=UUID(int=870 + number), tenant_id=base.TENANT, case_id=context["case_id"],
                                           raw_alert={"scope": {}}, total_tokens=0, iterations=0)
                self.runs[run.id] = run
                wire, dispatched = [], []

                async def tool(name, arguments):
                    recorded = results[len(dispatched)]
                    self.assertEqual((name, arguments), (recorded["tool"], recorded["arguments"]))
                    dispatched.append(name)
                    return {k: v for k, v in recorded.items() if k not in {"evidence_id", "kind", "tool", "arguments"}}

                def provider(http_request):
                    body = json.loads(http_request.content)
                    used = sum(r["usage"]["total_tokens"] for r in replies[:len(wire)])
                    required = sum(len(analysis.encoded(body.get(k), compact=True).encode())
                                   for k in ("messages", "tools", "response_format", "tool_choice"))
                    self.assertLessEqual(required + models.MAX_OUTPUT_TOKENS + 256, analysis.LIMITS["tokens"] - used)
                    wire.append(body)
                    reply = replies[len(wire)-1]
                    return httpx.Response(200, json={"choices": [{"message": reply["response"],
                        "finish_reason": "tool_calls" if reply["response"].get("tool_calls") else "stop"}], "usage": reply["usage"]})

                client_type = type(self.client)
                with patch.object(base.tools.CaseTools, "execute", side_effect=tool), patch.object(models.httpx, "AsyncClient",
                        side_effect=lambda **kw: client_type(transport=httpx.MockTransport(provider), **kw)):
                    outcome = await analysis.CaseAnalysis(self.db, run, context, request).execute()
                self.assertEqual(outcome["status"], "failed", outcome)
                self.assertEqual(outcome["result"]["stop_reason"], "invalid_or_unreferenced_conclusion")
                self.assertEqual((len(wire), len(dispatched)), (4, 2))
                self.assertEqual(outcome["result"]["usage"]["known_tokens"], 12352 if label == "A" else 13431)
                for body in wire:
                    view = json.loads(body["messages"][1]["content"])
                    for source in context["evidence"]:
                        if source["kind"] == "alert":
                            visible = next(e for e in view["evidence"] if e["evidence_id"] == source["evidence_id"])
                            self.assertEqual(visible["data"]["source_material"]["raw_event"]["text"],
                                             source["data"]["source_material"]["raw_event"]["text"])
                self.assertEqual(outcome["result"]["report"]["member_coverage"]["not_assessed_count"], 2)
                self.assertNotIn("4209", outcome["result"]["markdown"])
                self.assertNotIn("User admin", outcome["result"]["markdown"])
                self.assertEqual(context, original)
                self.lake.assert_not_awaited()

    async def test_followup_keeps_bounded_open_state_in_prior_run(self):
        first = (await self.run_case()).json()
        self.assertEqual(first["status"], "completed", first)
        self.wire.clear()
        second = (await self.run_case(key=103, previous_run_id=first["run_id"])).json()
        self.assertEqual(second["status"], "completed", second)
        view = json.loads(self.wire[0]["messages"][1]["content"])
        history = next(e["data"] for e in view["evidence"] if e["kind"] == "prior_analysis")
        self.assertEqual(history["run_id"], first["run_id"])
        self.assertIn("证据编号属于原Run", history["notice"])
        for section in ("open_questions", "member_assessments", "relationships"):
            self.assertEqual(history["report"][section], first["result"]["report"][section])
        self.assertEqual(self.lake.await_count, 2)
        self.assertEqual((await self.client.get(first["result_url"])).json()["result"], first["result"])
        context = next(json.loads(a.content) for a in self.artifacts if a.kind == "case_analysis_step"
                       and json.loads(a.content).get("case_id") and any(e.get("kind") == "prior_analysis"
                           for e in json.loads(a.content).get("evidence", [])))
        original = next(e["data"]["report"] for e in context["evidence"] if e["kind"] == "prior_analysis")
        original["open_questions"] += [{**original["open_questions"][0], "question": "长问题" * 1000},
            {**original["open_questions"][0], "alert_ids": [str(UUID(int=999))]}] + original["open_questions"] * 20
        saved = deepcopy(context)
        history = next(e["data"] for e in analysis.model_context(context)["evidence"] if e["kind"] == "prior_analysis")
        self.assertGreater(history["omitted_report_items"]["open_questions"], 0)
        retained = sum(len(analysis.encoded(e, compact=True).encode("utf-8"))
                       for section in ("open_questions", "member_assessments", "relationships") for e in history["report"][section])
        self.assertLessEqual(retained, analysis.HISTORY_OPEN_BYTES)
        for item in history["report"]["open_questions"]:
            self.assertEqual(item, original["open_questions"][0])
        self.assertEqual(context, saved)

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
