"""Direct Case workflow examples using model HTTP, lake and ledger substitutes."""
from datetime import timedelta
import asyncio
import json
import hashlib
import os
import re
import sqlite3
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import httpx
from sqlalchemy.dialects.postgresql import Insert
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_investigation_incident_api as fixtures
from app.api.v1.deps import CurrentUser, get_current_user
from app.db.rls import get_tenant_db
from app.investigation_v2 import case_analysis as analysis, case_analysis_models as models, case_analysis_tools as tools
from app.investigation_v2 import case_source_material as sources
from app.investigation_v2.program_start_api import create_app
from app.models.alert import Alert
from app.models.case import Case
from app.models.investigation import InvestigationArtifact, InvestigationEvent, InvestigationRun
from app.services.llm_resolver import LlmConfig

TENANT, NOW, CASE = fixtures.TENANT, fixtures.NOW, UUID(int=30)


def single_member_assessment():
    return [{"alert_id": str(UUID(int=1)), "status": "addressed", "role": "undetermined",
             "summary": "告警材料已核对，行为性质尚未证实。", "evidence_ids": ["A1"]}]


def current_network_fixture(parent):
    """Adapt only an in-memory report fixture, never the archived evidence.

    Old network queries are deliberately ineligible for new query reuse. These
    report/correction tests need a synthetic current-contract parent; separate
    query tests verify rejection of the actual legacy contract and SQL dedup.
    """
    parent = json.loads(json.dumps(parent))
    for item in parent["evidence"]:
        if item.get("tool") == "network_connections":
            identities = [(row.get("event_time"), row["event_id"]) for row in item["rows"]]
            assert len(set(identities)) == len(identities)
            item["query_contract"] = tools.NETWORK_QUERY_CONTRACT
    return parent


def result(one=None, rows=None):
    response = MagicMock()
    response.scalar_one_or_none.return_value = one
    response.scalars.return_value.all.return_value = rows or []
    response.all.return_value = rows or []
    return response


class CaseAnalysisExamples(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.case = Case(id=CASE, tenant_id=TENANT, title="Script activity", alert_ids=[UUID(int=1)])
        self.alert = fixtures.alert(1)
        self.alert.source_event_ids = ["source-event-01"]
        self.runs, self.events, self.artifacts, self.statements = {}, [], [], []
        self.db = MagicMock(spec=AsyncSession)
        self.db.execute = AsyncMock(side_effect=self.execute)
        self.db.commit = AsyncMock()
        self.db.add.side_effect = self.add
        self.messages = []
        self.scenario = "normal"

        async def lake(sql, **kwargs):
            if self.scenario == "failed":
                raise RuntimeError("example source unavailable")
            rows = [] if self.scenario == "empty" else [("event-7001", NOW, "host-01", "powershell.exe", "script.ps1", "a" * 64, "alice",
                                                        1007, 2, "terminate", "")]
            return SimpleNamespace(columns=["event_id", "event_time", "src_hostname", "process_name", "file_path", "hash_sha256", "user_name",
                                            "class_uid", "activity_id", "action", "outcome"], rows=rows)
        self.lake = AsyncMock(side_effect=lake)
        self.config = AsyncMock(return_value=LlmConfig(True, "http://model.invalid/v1", "example-model", "example-only", "environment", ""))
        app = create_app(start_gateway=object(), result_gateway=object())
        async def user():
            return CurrentUser(UUID(int=1), TENANT, "analyst", "example@invalid.test",
                               scopes=["investigation:run", "cases:read", "alerts:read"])
        async def session():
            yield self.db
        app.dependency_overrides[get_current_user] = user
        app.dependency_overrides[get_tenant_db] = session
        original_client = httpx.AsyncClient
        self.client = original_client(transport=httpx.ASGITransport(app=app), base_url="http://case.invalid",
                                      headers={"Authorization": "Bearer example-only"})
        self.addAsyncCleanup(self.client.aclose)
        def provider(request):
            body = json.loads(request.content)
            self.messages.append(body)
            if body["messages"][-1]["role"] != "tool":
                message = {"content": None, "tool_calls": [{"id": "call-process-01", "type": "function", "function": {
                    "name": "process_activity", "arguments": json.dumps({"hostname": "host-01", "limit": 20})}}]}
                finish = "tool_calls"
            else:
                message = {"content": json.dumps({
                    "summary": "查询发现脚本进程，尚不足以判断攻击成立。" if self.scenario == "normal" else "来源不足，保留未解问题。",
                    "findings": [{"text": "本窗口返回进程记录" if self.scenario == "normal" else "本来源未能提供匹配证据",
                                  "evidence_ids": ["E1"]}],
                    "counterevidence": [], "gaps": [] if self.scenario == "normal" else ["仍需其他来源核对"],
                    "recommendations": ["核对脚本来源和父进程材料"],
                    "member_assessments": single_member_assessment(),
                }, ensure_ascii=False)}
                finish = "stop"
            payload = {"choices": [{"message": message, "finish_reason": finish}],
                       "usage": {"prompt_tokens": 100, "completion_tokens": 50}}
            if self.scenario == "unknown_usage":
                payload.pop("usage")
            return httpx.Response(200, json=payload)
        for patcher in (
            patch.object(analysis, "resolve_llm_config", self.config),
            patch.object(tools, "execute_lake_query", self.lake),
            patch.object(tools.settings, "AISOC_DISABLE_CLICKHOUSE", False),
            patch.object(tools.settings, "CLICKHOUSE_HOST", "example-lake"),
            patch.object(models.httpx, "AsyncClient", side_effect=lambda **kwargs: original_client(
                transport=httpx.MockTransport(self.report_provider(provider)), **kwargs)),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.path = f"/api/v2/investigation/cases/{CASE}"

    def report_provider(self, provider, *, finish=True):
        """Adapt saved UUID report templates to the current A-ref model protocol.

        self.messages records scripted fixture requests; all_model_requests also
        records the explicit finish signal. Original frozen files are untouched.
        """
        def respond(request):
            body = json.loads(request.content)
            if not hasattr(self, "all_model_requests"):
                self.all_model_requests = []
            self.all_model_requests.append(body)
            if finish and body.get("tools") and body.get("tool_choice") == "required" and body["messages"][-1]["role"] == "tool":
                return httpx.Response(200, json={"choices": [{"message": {"tool_calls": [{"id": "fixture-finish", "type": "function",
                    "function": {"name": "finish_analysis", "arguments": "{}"}}]}, "finish_reason": "tool_calls"}],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0}})
            response = provider(request)
            payload = response.json()
            for choice in payload.get("choices", []):
                message = choice.get("message", {})
                try:
                    report = json.loads(message.get("content") or "null")
                except (ValueError, TypeError):
                    continue
                if not isinstance(report, dict) or "member_assessments" not in report:
                    continue
                # Each old template explicitly cites its own A source.
                refs = {item["alert_id"]: next((ref for ref in item.get("evidence_ids", []) if ref.startswith("A")), "A-invalid")
                        for item in report["member_assessments"] if "alert_id" in item}
                for item in report["member_assessments"]:
                    if "alert_id" in item:
                        item["alert_ref"] = refs.get(item.pop("alert_id"), "A-invalid")
                for section in ("relationships", "open_questions"):
                    for item in report.get(section, []):
                        if "alert_ids" in item:
                            item["alert_refs"] = [refs.get(value, "A-invalid") for value in item.pop("alert_ids")]
                message["content"] = json.dumps(report, ensure_ascii=False)
            return httpx.Response(response.status_code, json=payload)
        return respond

    def add(self, value):
        if isinstance(value, InvestigationEvent):
            self.events.append(value)
        elif isinstance(value, InvestigationArtifact):
            self.artifacts.append(value)

    async def execute(self, statement, params=None):
        self.statements.append(statement)
        if isinstance(statement, Insert):
            values = statement.compile().params
            run_id = values["id"]
            if run_id in self.runs:
                return result()
            self.runs[run_id] = InvestigationRun(**values)
            return result(run_id)
        descriptions = getattr(statement, "column_descriptions", [])
        entities = [item.get("entity") for item in descriptions]
        values = list(statement.compile().params.values())
        run_id = next((value for value in values if isinstance(value, UUID) and value in self.runs), None)
        if Case in entities:
            return result(self.case)
        if Alert in entities:
            return result(rows=[self.alert])
        if InvestigationArtifact in entities and "JOIN investigation_runs" in str(statement):
            source_hash = next((value for value in values if isinstance(value, str) and len(value) == 64), None)
            prior = [item for item in self.artifacts if item.kind == "case_analysis_result"
                     and self.runs[item.run_id].raw_alert.get("source_hash") == source_hash]
            return result(prior[-1] if prior else None)
        if InvestigationEvent in entities and InvestigationRun in entities:
            return result(rows=[fixtures.verdict(1, "Needs evidence")])
        if InvestigationRun in entities:
            return result(self.runs.get(run_id))
        if InvestigationArtifact in entities:
            kind = statement.compile().params.get("kind_1", "case_analysis_result")
            event_id = statement.compile().params.get("event_id_1")
            return result(next((item for item in self.artifacts if item.run_id == run_id and item.kind == kind
                                and (event_id is None or item.event_id == event_id)), None))
        if InvestigationEvent in entities:
            rows = [item for item in self.events if item.run_id == run_id]
            seq = statement.compile().params.get("seq_1")
            if statement._limit_clause is not None:
                rows = [item for item in rows if item.seq > seq][:statement._limit_clause.value]
            return result(one=next((item for item in rows if item.seq == seq), None), rows=rows)
        return result()

    async def start(self, key=100, end_minutes=5):
        return await self.client.post(self.path + "/investigate", json={
            "operation_key": str(UUID(int=key)), "start": NOW.isoformat(),
            "end": (NOW + timedelta(minutes=end_minutes)).isoformat(),
        })

    async def test_case_model_query_analysis_report_and_readback(self):
        response = await self.start()
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["case_id"], str(CASE))
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["result"]["evidence"][-1]["rows"][0]["event_id"], "event-7001")
        self.assertEqual(data["result"]["report"]["findings"][0]["evidence_ids"], ["E1"])
        self.assertIn("Case调查报告", data["result"]["markdown"])
        self.assertEqual(len(self.messages), 2)
        self.assertIn("process_activity", [item["function"]["name"] for item in self.messages[0]["tools"]])
        self.assertTrue(any(m.get("tool_call_id") == "call-process-01" for m in self.messages[1]["messages"]))
        self.assertTrue(any(m.get("tool_calls", [{}])[0].get("id") == "call-process-01" for m in self.messages[1]["messages"]))
        self.assertNotIn("response_format", self.messages[0])
        self.assertIn("response_format", self.messages[1])
        params = self.lake.call_args.kwargs["params"]
        self.assertEqual(params["tenant_id"], str(TENANT))
        self.assertEqual(params["hostname"], "host-01")
        self.assertEqual(params["start"], "2026-10-25 10:00:00.000000")
        self.assertEqual(params["end"], "2026-10-25 10:05:00.000000")
        self.assertEqual(data["result"]["evidence"][-1]["query_scope"]["start"], NOW.isoformat())
        self.assertEqual(data["result"]["evidence"][-1]["query_scope"]["end"], (NOW + timedelta(minutes=5)).isoformat())
        read = await self.client.get(self.path + f"/investigations/{data['run_id']}")
        self.assertEqual(read.status_code, 200, read.text)
        self.assertEqual(read.json()["result"], data["result"])
        repeat = await self.start()
        self.assertEqual(repeat.json()["run_id"], data["run_id"])
        self.assertEqual(len(self.messages), 2)
        self.assertEqual(self.lake.await_count, 1)

    async def test_invalid_conclusion_gets_one_schema_correction_after_tool_feedback(self):
        conclusion = {"summary": "窗口内有脚本记录，攻击性质待核。",
                      "findings": [{"text": "读取到进程记录", "evidence_ids": ["E1"]}],
                      "counterevidence": [], "gaps": [], "recommendations": [],
                      "member_assessments": single_member_assessment()}
        invalid = {**conclusion, "findings": [{"text": "尚未查询的记录", "evidence_ids": ["E404"]}]}
        replies = [{"tool_calls": [{"id": "source-query", "type": "function", "function": {
                       "name": "process_activity", "arguments": json.dumps({"hostname": "host-01", "limit": 20})}}]},
                   {"content": json.dumps(invalid)},
                   {"content": json.dumps(conclusion)}]

        def provider(request):
            self.messages.append(json.loads(request.content))
            message = replies[len(self.messages) - 1]
            return httpx.Response(200, json={"choices": [{"message": message,
                "finish_reason": "tool_calls" if "tool_calls" in message else "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50}})

        client_type = type(self.client)
        with patch.object(models.httpx, "AsyncClient", side_effect=lambda **kwargs:
                          client_type(transport=httpx.MockTransport(self.report_provider(provider)), **kwargs)):
            response = await self.start()
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["result"]["usage"]["model_calls"], 4)
        self.assertEqual(self.lake.await_count, 1)
        correction = self.messages[2]
        self.assertNotIn("response_format", self.messages[0])
        self.assertIn("response_format", self.messages[1])
        self.assertNotIn("tools", correction)
        output_format = correction["response_format"]
        self.assertEqual(output_format["type"], "json_schema")
        self.assertTrue(output_format["json_schema"]["strict"])
        schema = output_format["json_schema"]["schema"]
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), set(schema["properties"]))
        self.assertEqual(schema["$defs"]["Finding"]["properties"]["evidence_ids"]["items"]["enum"], ["A1", "T1", "E1"])
        self.assertEqual(schema["$defs"]["MemberAssessment"]["properties"]["alert_ref"]["enum"], ["A1"])
        feedback = json.loads(correction["messages"][-1]["content"].split("\n", 1)[1])
        self.assertEqual(feedback, {"errors": [{"issue": "证据编号须来自当前输入", "location": []}]})
        self.assertEqual(correction["messages"][1:-1], self.messages[1]["messages"][1:])
        self.assertEqual(correction["messages"][0]["content"], analysis.CORRECTION_SYSTEM)
        saved_feedback = next(json.loads(item.content) for item in self.artifacts
                              if item.kind == "case_analysis_step" and '"errors"' in item.content)
        self.assertEqual(saved_feedback["available_evidence_ids"], ["A1", "T1", "E1"])
        self.assertEqual(saved_feedback["selected_member_refs"], ["A1"])
        self.assertFalse(any("E404" in message.get("content", "") for message in correction["messages"]))
        self.assertEqual(sum(event.kind == "case_analysis_validation" for event in self.events), 1)
        self.assertEqual(result["result"]["report"]["findings"][0]["evidence_ids"], ["E1"])

    async def test_gateway_model_wait_uses_remaining_case_deadline(self):
        actual_call = models.call_model

        async def elapsed_call(*args, **kwargs):
            payload = await actual_call(*args, **kwargs)
            if len(self.messages) == 1:
                await asyncio.sleep(0.02)
            return payload

        with patch.dict(os.environ, {"LLM_GATEWAY_URL": "http://model.invalid/v1/"}), \
                patch.object(analysis, "call_model", side_effect=elapsed_call):
            response = await self.start()
        self.assertEqual(response.json()["status"], "completed")
        first, second = [body["timeout"] for body in self.messages]
        self.assertGreater(first, 60)
        self.assertLessEqual(first, 120)
        self.assertLess(second, first - 0.01)
        self.assertEqual(self.lake.await_count, 1)

    async def test_model_transport_wait_and_gateway_only_parameter(self):
        observed = []

        def provider(request):
            observed.append((json.loads(request.content), request.extensions["timeout"]))
            return httpx.Response(200, json={"choices": []})

        client_type = type(self.client)
        with patch.object(models.httpx, "AsyncClient", side_effect=lambda **kwargs:
                client_type(transport=httpx.MockTransport(self.report_provider(provider)), **kwargs)), \
                patch.dict(os.environ, {"LLM_GATEWAY_URL": "http://model.invalid/v1"}):
            for base, seconds in [("http://model.invalid/v1", 97.25), ("http://byok.invalid/v1", 7.5)]:
                config = LlmConfig(True, base, "example-model", "example-only", "environment", "")
                await models.call_model(config, [{"role": "user", "content": "核对材料"}], [], timeout_seconds=seconds)
            with self.assertRaises(TimeoutError):
                await models.call_model(config, [{"role": "user", "content": "核对材料"}], [], timeout_seconds=0)
        self.assertEqual(len(observed), 2)
        self.assertEqual(observed[0][0]["timeout"], 97.25)
        self.assertEqual(observed[0][1]["read"], 97.25)
        self.assertEqual(observed[0][1]["connect"], 10)
        self.assertNotIn("timeout", observed[1][0])
        self.assertEqual(observed[1][1]["read"], 7.5)
        self.assertEqual(observed[1][1]["connect"], 7.5)

    async def test_total_case_deadline_still_stops_pending_model_without_retry(self):
        async def pending(*args, **kwargs):
            await asyncio.sleep(1)
            raise AssertionError("total deadline must cancel the pending model")

        with patch.dict(analysis.LIMITS, {"duration_seconds": 0.02}), \
                patch.object(analysis, "call_model", side_effect=pending) as model:
            response = await self.start()
        data = response.json()
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["result"]["stop_reason"], "duration_limit")
        self.assertTrue(data["result"]["usage"]["unknown_usage"])
        self.assertEqual(model.await_count, 1)
        self.assertEqual(self.lake.await_count, 0)

    async def test_empty_result_and_query_failure_remain_distinct(self):
        self.scenario = "empty"
        empty = (await self.start()).json()["result"]
        self.assertTrue(empty["evidence"][-1]["available"])
        self.assertEqual(empty["evidence"][-1]["rows"], [])
        self.assertEqual(empty["completion"], "partial")
        self.assertEqual(next(json.loads(m["content"])["query_status"] for m in self.messages[-1]["messages"] if m["role"] == "tool" and "query_status" in json.loads(m["content"])), "success_empty")
        self.assertNotIn("query_status", empty["evidence"][-1])
        self.scenario = "failed"
        # A new window requires a new source query rather than reusing the empty result.
        failed = (await self.start(101, end_minutes=6)).json()["result"]
        self.assertFalse(failed["evidence"][-1]["available"])
        self.assertEqual(next(json.loads(m["content"])["query_status"] for m in self.messages[-1]["messages"] if m["role"] == "tool" and "query_status" in json.loads(m["content"])), "unavailable")
        self.assertTrue(any("未能检查" in value for value in failed["report"]["gaps"]))

    async def test_applicable_prior_query_is_reused_in_a_new_case_run(self):
        first = (await self.start()).json()
        second = (await self.start(101)).json()
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual(self.lake.await_count, 1)
        self.assertEqual(second["result"]["evidence"][-1]["reused_from"]["run_id"], first["run_id"])

    async def test_process_query_excludes_other_event_classes_and_keeps_activity(self):
        # Execute the real predicate/projection on mixed rows. SQLite only substitutes
        # driver binding and the CH time conversion; this is not a live lake test.
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.create_function("toDateTime64", 3, lambda value, precision, zone: value)
        connection.execute("""ATTACH DATABASE ':memory:' AS aisoc""")
        connection.execute("""CREATE TABLE aisoc.raw_events (
            event_id TEXT, tenant_id TEXT, event_time TEXT, src_hostname TEXT,
            process_name TEXT, file_path TEXT, hash_sha256 TEXT, user_name TEXT,
            class_uid INTEGER, activity_id INTEGER, action TEXT, outcome TEXT,
            source_ip TEXT, dest_ip TEXT, dst_port INTEGER, protocol TEXT, ingest_time TEXT)""")
        when = NOW.strftime("%Y-%m-%d %H:%M:%S.%f")
        for event_id, event_class in (("process-1", 1007), ("network-1", 4001), ("file-1", 1001)):
            connection.execute("INSERT INTO aisoc.raw_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                event_id, str(TENANT), when, "host-01", "powershell.exe", "script.ps1", "a" * 64,
                "alice", event_class, 2, "terminate", "", "10.0.0.1", "192.0.2.1", 443, "tcp", when))

        async def lake(sql, *, params, **kwargs):
            cursor = connection.execute(re.sub(r"%\((\w+)\)s", r":\1", sql), params)
            return SimpleNamespace(columns=[column[0] for column in cursor.description], rows=cursor.fetchall())
        self.lake.side_effect = lake
        response = await self.start()
        self.assertEqual(response.status_code, 200, response.text)
        evidence = response.json()["result"]["evidence"][-1]
        self.assertEqual(response.json()["status"], "completed", response.text)
        self.assertEqual([row["event_id"] for row in evidence["rows"]], ["process-1"])
        self.assertEqual(evidence["query_contract"], tools.PROCESS_QUERY_CONTRACT)
        model_evidence = next(json.loads(m["content"]) for m in self.messages[-1]["messages"] if m["role"] == "tool" and "query_status" in json.loads(m["content"]))
        self.assertEqual(model_evidence["rows"], [{**{key: value for key, value in evidence["rows"][0].items()
                                                      if key not in {"class_uid", "activity_id"}}, "event_kind": "process_activity"}])
        self.assertEqual(model_evidence["model_omitted_fields"], ["rows.class_uid", "rows.activity_id"])
        self.assertEqual({key: evidence["rows"][0][key] for key in ("class_uid", "activity_id", "action", "outcome")},
                         {"class_uid": 1007, "activity_id": 2, "action": "terminate", "outcome": ""})
        network = await tools.CaseTools(TENANT, ["host-01"], NOW, NOW + timedelta(minutes=5)).execute(
            "network_connections", {"hostname": "host-01"})
        self.assertEqual([row["event_id"] for row in network["rows"]], ["network-1"])

    async def test_legacy_process_result_is_not_reused_as_current_contract(self):
        first = (await self.start()).json()
        artifact = next(item for item in self.artifacts if item.kind == "case_analysis_result")
        legacy = json.loads(artifact.content)
        legacy["evidence"][-1].pop("query_contract")
        artifact.content = analysis.encoded(legacy)
        second = (await self.start(101)).json()
        self.assertEqual(self.lake.await_count, 2)
        self.assertNotIn("reused_from", second["result"]["evidence"][-1])
        third = (await self.start(102)).json()
        self.assertEqual(self.lake.await_count, 2)
        self.assertEqual(third["result"]["evidence"][-1]["reused_from"]["run_id"], second["run_id"])
        self.assertEqual((await self.start()).json()["result"], legacy)
        self.assertEqual(first["run_id"], str(artifact.run_id))

    async def test_unknown_model_usage_stops_before_query(self):
        self.scenario = "unknown_usage"
        response = await self.start()
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["result"]
        self.assertEqual(data["completion"], "partial")
        self.assertTrue(data["usage"]["unknown_usage"])
        self.lake.assert_not_awaited()

    async def test_office_frozen_followup_reaches_correction_with_new_sources(self):
        root = Path(__file__).resolve().parents[3] / "docs/operations/evidence/INVHTTP-20261028-01/results/office-powershell"
        def frozen(name):
            return json.loads((root / name).read_text(encoding="utf-8-sig"))
        context = frozen("043-followup-step-1.response.txt")["data"]
        original_history = json.loads(json.dumps(context["evidence"][-1]))
        alerts = [SimpleNamespace(**frozen(name)) for name in ("001-source-0.response.txt", "002-source-1.response.txt")]
        case_material, alert_material = sources.freeze_sources(SimpleNamespace(description=None), alerts)
        context.update(source_material_schema=sources.SOURCE_SCHEMA, case_material=case_material)
        for item in context["evidence"]:
            if item["kind"] == "alert":
                item["data"]["source_material"] = alert_material[item["data"]["alert_id"]]
        request = analysis.CaseAnalysisRequest.model_validate(frozen("039-followup.body.json"))
        run = InvestigationRun(id=UUID(int=800), tenant_id=TENANT, case_id=context["case_id"],
                               raw_alert={"scope": {}}, total_tokens=0, iterations=0)
        self.runs[run.id] = run
        rejected = frozen("045-followup-step-3.response.txt")["data"]
        conclusion = {"summary": "来源描述已保存，缺少独立行为印证。", "findings": [{"text": "两条来源描述涉及同一主机",
                      "evidence_ids": ["A1", "A2"]}], "counterevidence": [], "gaps": ["仍需独立行为印证"],
                      "recommendations": [], "member_assessments": [
                          {"alert_id": member, "status": "addressed", "role": "background", "summary": "仅核对来源描述",
                           "evidence_ids": [f"A{index}"]} for index, member in enumerate(context["read_member_ids"], 1)]}
        def provider(http_request):
            self.messages.append(json.loads(http_request.content))
            first = len(self.messages) == 1
            return httpx.Response(200, json={"choices": [{"message": rejected["response"] if first else
                {"content": json.dumps(conclusion)}, "finish_reason": "stop"}],
                "usage": rejected["usage"] if first else {"prompt_tokens": 100, "completion_tokens": 50}})
        client_type = type(self.client)
        with patch.object(models.httpx, "AsyncClient", side_effect=lambda **kwargs:
                          client_type(transport=httpx.MockTransport(self.report_provider(provider)), **kwargs)):
            outcome = await analysis.CaseAnalysis(self.db, run, context, request).execute()
        self.assertEqual(outcome["status"], "completed", outcome["result"]["stop_reason"])
        self.assertEqual(len(self.messages), 2)
        correction = self.messages[-1]
        required = sum(len(analysis.encoded(value, compact=True).encode()) for value in
                       (correction["messages"], [], correction["response_format"])) + models.MAX_OUTPUT_TOKENS + 256
        self.assertLessEqual(required, 17018)  # 24000 - frozen first-response usage 6982; unchanged budget.
        print(f"Office current correction required={required}, recorded remaining=17018, headroom={17018-required}")
        self.assertEqual(outcome["result"]["usage"]["known_tokens"], 7132)
        self.assertEqual(outcome["result"]["evidence"][-1], original_history)
        view = json.loads(correction["messages"][1]["content"])
        raw = view["evidence"][0]["data"]["source_material"]["raw_event"]
        self.assertIn("approval_status", raw["text"])
        self.assertIs(raw.get("model_truncated", view.get("source_field_defaults", {}).get("model_truncated")), False)
        self.assertEqual(context["evidence"][-1], original_history)
        self.lake.assert_not_awaited()
        self.assertTrue(any(item.kind == "case_analysis_result" for item in self.artifacts))

    async def test_live_main_failures_reach_correction_with_original_usage_and_rows(self):
        root = Path(__file__).resolve().parents[3] / "docs/operations/evidence/investigation-audit-fixes-20261031/live-r3/results"
        for index, name in enumerate(("office-powershell", "network-positive-reuse")):
            with self.subTest(case=name):
                steps = sorted([json.loads(path.read_text(encoding="utf-8"))
                                for path in root.glob(f"*-{name}-main-step-*.response.txt")], key=lambda step: step["seq"])
                context = steps[0]["data"]
                original_context = analysis.encoded(context)
                replies = [step["data"] for step in steps if "response" in step["data"]]
                original_requests = [step["data"] for step in steps if "messages" in step["data"]]
                tool_results = [step["data"]["evidence"] for step in steps if "model_message" in step["data"]]
                request = analysis.CaseAnalysisRequest.model_validate_json(
                    next(root.glob(f"*-{name}-main.body.json")).read_text(encoding="utf-8"))
                run = InvestigationRun(id=UUID(int=810 + index), tenant_id=TENANT, case_id=context["case_id"],
                                       raw_alert={"scope": {}}, total_tokens=0, iterations=0)
                self.runs[run.id] = run
                self.messages.clear()
                conclusion = {"summary": "已核对来源与查询，攻击性质仍待证实。",
                    "findings": [{"text": "已提供告警陈述与窗口内查询结果", "evidence_ids": ["A1", "E1", "E2"]}],
                    "counterevidence": [], "gaps": ["材料不能证明攻击性质"], "recommendations": [],
                    "member_assessments": [{"alert_id": item["data"]["alert_id"], "status": "addressed",
                        "role": "background", "summary": "来源陈述已核对，不能独立证明攻击",
                        "evidence_ids": [item["evidence_id"]]} for item in context["evidence"] if item["kind"] == "alert"]}

                def provider(http_request):
                    body = json.loads(http_request.content)
                    self.messages.append(body)
                    turn = len(self.messages) - 1
                    if turn < len(replies):
                        reply = replies[turn]
                    else:
                        reply = {"response": {"content": json.dumps(conclusion)},
                                 "usage": {"prompt_tokens": 100, "completion_tokens": 50}}
                    return httpx.Response(200, json={"choices": [{"message": reply["response"],
                        "finish_reason": "tool_calls" if reply["response"].get("tool_calls") else "stop"}],
                        "usage": reply["usage"]})

                dispatched = []
                async def tool(name, arguments):
                    recorded = tool_results[len(dispatched)]
                    self.assertEqual((name, arguments), (recorded["tool"], recorded["arguments"]))
                    dispatched.append(name)
                    return {key: value for key, value in recorded.items()
                            if key not in {"evidence_id", "kind", "tool", "arguments"}}

                client_type = type(self.client)
                with patch.object(tools.CaseTools, "execute", side_effect=tool), patch.object(models.httpx, "AsyncClient",
                        side_effect=lambda **kwargs: client_type(transport=httpx.MockTransport(self.report_provider(provider, finish=False)), **kwargs)):
                    outcome = await analysis.CaseAnalysis(self.db, run, context, request).execute()
                self.assertEqual(outcome["status"], "completed", outcome["result"]["stop_reason"])
                self.assertEqual(len(self.messages), len(replies) + 1)
                # Phase and member references changed; frozen source text/rows/usage are checked below.
                self.assertEqual(len(dispatched), 2)
                self.lake.assert_not_awaited()
                known = sum(reply["usage"]["prompt_tokens"] + reply["usage"]["completion_tokens"] for reply in replies)
                self.assertEqual(outcome["result"]["usage"]["known_tokens"], known + 150)
                correction = self.messages[-1]
                self.assertNotIn("tools", correction)
                required = sum(len(analysis.encoded(value, compact=True).encode()) for value in
                    (correction["messages"], [], correction["response_format"])) + models.MAX_OUTPUT_TOKENS + 256
                self.assertLessEqual(required, analysis.LIMITS["tokens"] - known)
                print(f"r3 frozen {name}: correction required={required}, remaining={24000-known}")
                view = json.loads(correction["messages"][1]["content"])
                for original in tool_results:
                    visible = next(item for item in view["evidence"] if item["evidence_id"] == original["evidence_id"])
                    filtered = json.loads(tools.model_result(original))
                    for key in ("rows", "available", "query_status", "returned_count", "truncated", "arguments", "limitation"):
                        self.assertEqual(visible[key], filtered[key])
                    self.assertEqual(visible["query_scope"], {"same_as_case": True})
                    saved = next(item for item in outcome["result"]["evidence"] if item["evidence_id"] == original["evidence_id"])
                    self.assertEqual(saved, original)
                expected_view = analysis.model_context(context)
                for visible, expected in zip(sources.source_fields(view), sources.source_fields(expected_view)):
                    self.assertEqual(visible["text"], expected["text"])
                    self.assertEqual(visible["status"], expected["status"])
                    for key, default in view["source_field_defaults"].items():
                        self.assertEqual(visible.get(key, default), expected[key])
                self.assertEqual(analysis.encoded(context), original_context)
                self.assertEqual((await self.client.get(outcome["result_url"])).json()["result"], outcome["result"])

    async def test_followup_new_sources_required_reuse_and_correction_together(self):
        self.alert.description = "来源描述：脚本活动，尚无独立印证"
        self.alert.raw_event = {"full_log": "PowerShell command line", "approval_status": "unknown"}
        first = (await self.start()).json()
        original = first["result"]
        self.messages.clear()
        good = {"summary": "有进程活动记录，性质待核。", "findings": [{"text": "记录包含活动字段", "evidence_ids": ["E1"]}],
                "counterevidence": [], "gaps": [], "recommendations": [],
                      "member_assessments": single_member_assessment()}
        replies = [{"tool_calls": [{"id": "required-process", "type": "function", "function": {
            "name": "process_activity", "arguments": json.dumps({"hostname": "host-01", "limit": 20})}}]},
            {"content": json.dumps({**good, "findings": [{"text": "invalid", "evidence_ids": ["E404"]}]})},
            {"content": json.dumps(good)}]
        def provider(request):
            self.messages.append(json.loads(request.content))
            message = replies[len(self.messages)-1]
            return httpx.Response(200, json={"choices": [{"message": message,
                "finish_reason": "tool_calls" if "tool_calls" in message else "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50}})
        client_type = type(self.client)
        body = {"operation_key": str(UUID(int=801)), "previous_run_id": first["run_id"],
                "start": NOW.isoformat(), "end": (NOW+timedelta(minutes=5)).isoformat(),
                "required_tools": ["process_activity"]}
        with patch.object(models.httpx, "AsyncClient", side_effect=lambda **kwargs:
                          client_type(transport=httpx.MockTransport(self.report_provider(provider)), **kwargs)):
            response = await self.client.post(self.path + "/investigate", json=body)
        follow = response.json()
        self.assertEqual(follow["status"], "completed", follow)
        self.assertEqual(len(self.messages), 3)
        self.assertEqual(self.messages[0]["tool_choice"]["function"]["name"], "process_activity")
        self.assertIn("response_format", self.messages[-1])
        self.assertEqual(self.lake.await_count, 1)
        self.assertEqual(follow["result"]["evidence"][-1]["reused_from"]["run_id"], first["run_id"])
        self.assertEqual((await self.client.get(first["result_url"])).json()["result"], original)
        self.assertEqual((await self.client.get(follow["result_url"])).json()["result"], follow["result"])

    async def test_frozen_network_protocol_and_missing_members_are_corrected_once(self):
        root = Path(__file__).resolve().parents[3] / "docs/operations/evidence/investigation-audit-fixes-20261031"
        files = root / "live-r5/results"
        steps = sorted([json.loads(path.read_text(encoding="utf-8")) for path in
                        files.glob("*-network-positive-reuse-followup-step-*.response.txt")], key=lambda step: step["seq"])
        context = steps[0]["data"]
        original_context = analysis.encoded(context)
        parent = json.loads(next((root / "live-r4/results").glob("*-network-positive-reuse-main-result.response.txt"))
                            .read_text(encoding="utf-8"))["result"]
        parent = current_network_fixture(parent)
        request = analysis.CaseAnalysisRequest.model_validate_json(next(files.glob("*-network-positive-reuse-followup.body.json"))
                                                                 .read_text(encoding="utf-8"))
        replies = [step["data"] for step in steps if "response" in step["data"]]
        bad = analysis.AnalysisConclusion.model_validate_json(replies[-1]["response"]["content"]).model_dump(mode="json")
        network = next(item for item in parent["evidence"] if item.get("tool") == "network_connections")
        evidence = [*context["evidence"], network]
        with self.assertRaisesRegex(ValueError, "unobserved_application_protocol_use_gaps"):
            analysis.validate_synthesis(bad, context, evidence)
        good = {**bad, "summary": "历史网络查询返回TCP/443记录，应用协议未核实。", "findings": [],
                "member_assessments": [{"alert_id": item["data"]["alert_id"], "status": "unresolved",
                    "role": "undetermined", "summary": "告警来源与历史连接记录已核对，行为性质待证。",
                    "evidence_ids": [item["evidence_id"], "E1"]} for item in context["evidence"] if item["kind"] == "alert"],
                "gaps": ["缺少HTTPS/TLS应用层证据，不能由端口推断。"], "open_questions": []}
        with self.assertRaisesRegex(ValueError, "missing_readable_member_assessment"):
            analysis.validate_synthesis({**good, "member_assessments": []}, context, evidence)
        # An actual protocol value in the query record is not a port inference.
        marked = json.loads(json.dumps(network))
        marked["rows"][0]["protocol"] = "HTTPS"
        analysis.validate_synthesis({**good, "summary": "来源记录标注HTTPS。"}, context, [*context["evidence"], marked])
        run = InvestigationRun(id=UUID(int=820), tenant_id=TENANT, case_id=context["case_id"],
                               raw_alert={"scope": {}}, total_tokens=0, iterations=0)
        self.runs[run.id] = run
        exchanges = [replies[0], replies[-1], {"response": {"content": json.dumps(good)},
                                              "usage": {"prompt_tokens": 100, "completion_tokens": 50}}]
        def provider(http_request):
            body = json.loads(http_request.content)
            self.messages.append(body)
            # This is the actual HTTPX wire encoding, covered by the unchanged
            # 256-byte envelope allowance rather than an expanded token budget.
            accounted = sum(len(analysis.encoded(body.get(key), compact=True).encode())
                            for key in ("messages", "tools", "response_format")) + 256
            if body.get("tool_choice"):
                accounted += len(analysis.encoded(body["tool_choice"], compact=True).encode())
            self.assertLessEqual(len(http_request.content), accounted)
            reply = exchanges[len(self.messages) - 1]
            return httpx.Response(200, json={"choices": [{"message": reply["response"],
                "finish_reason": "tool_calls" if reply["response"].get("tool_calls") else "stop"}], "usage": reply["usage"]})
        client_type = type(self.client)
        with patch.object(models.httpx, "AsyncClient", side_effect=lambda **kwargs:
                          client_type(transport=httpx.MockTransport(self.report_provider(provider)), **kwargs)):
            outcome = await analysis.CaseAnalysis(self.db, run, context, request, parent).execute()
        self.assertEqual(outcome["status"], "completed", outcome["result"]["stop_reason"])
        self.assertEqual(len(self.messages), 3)
        self.assertEqual(outcome["result"]["report"]["member_coverage"]["not_assessed_count"], 0)
        self.assertEqual(outcome["result"]["evidence"][-1]["reused_from"]["run_id"], parent["run_id"])
        self.assertEqual(outcome["result"]["evidence"][-1]["rows"], network["rows"])
        self.assertEqual(analysis.encoded(context), original_context)
        self.assertEqual((await self.client.get(outcome["result_url"])).json()["result"], outcome["result"])
        self.lake.assert_not_awaited()

    async def test_r6_network_sources_survive_model_correction_and_report_readback(self):
        root = Path(__file__).resolve().parents[3] / "docs/operations/evidence/investigation-audit-fixes-20261031/live-r6/results"
        steps = sorted([json.loads(path.read_text(encoding="utf-8")) for path in
                        root.glob("*-network-positive-reuse-followup-step-*.response.txt")], key=lambda step: step["seq"])
        context = steps[0]["data"]
        original_context = analysis.encoded(context)
        parent = json.loads((root / "005-network-positive-reuse-parent-result.response.txt").read_text(encoding="utf-8"))["result"]
        parent = current_network_fixture(parent)
        original_parent = analysis.encoded(parent)
        request = analysis.CaseAnalysisRequest.model_validate_json(
            (root / "007-network-positive-reuse-followup.body.json").read_text(encoding="utf-8"))
        replies = [step["data"] for step in steps if "response" in step["data"]]
        # r6's final prose was semantically wrong despite valid schema/references.
        # This test checks the actual material/report plumbing, not model truth.
        bad = json.loads(replies[-1]["response"]["content"])
        self.assertIn("nuclear", bad["summary"])
        history_summary = next(item["data"]["report"]["summary"] for item in context["evidence"] if item["kind"] == "prior_analysis")
        self.assertIn("有网络流量记录", history_summary)
        good = {"summary": "本次工具调用复用H1原有的三条TCP记录，未重新查询。H1已说明存在网络记录，但未证实攻击。",
                "findings": [{"text": "前两行分别对应A1和A2；第三行未匹配选定告警的来源事件ID，不能据此判无关。",
                              "evidence_ids": ["A1", "A2", "E1", "H1"]}],
                "counterevidence": [], "gaps": ["缺少进程关联证据"], "recommendations": [],
                "member_assessments": [{"alert_id": item["data"]["alert_id"], "status": "unresolved",
                    "role": "undetermined", "summary": "告警称合成测试待核网络活动，来源ID对应历史网络记录，性质待证。",
                    "evidence_ids": [item["evidence_id"], "E1"]} for item in context["evidence"] if item["kind"] == "alert"]}
        run = InvestigationRun(id=UUID(int=830), tenant_id=TENANT, case_id=context["case_id"],
                               raw_alert={"scope": {}}, total_tokens=0, iterations=0)
        self.runs[run.id] = run
        exchanges = [*replies[:2], {"response": {"content": json.dumps(good)},
                                   "usage": {"prompt_tokens": 100, "completion_tokens": 50}}]
        def provider(http_request):
            self.messages.append(json.loads(http_request.content))
            reply = exchanges[len(self.messages) - 1]
            return httpx.Response(200, json={"choices": [{"message": reply["response"],
                "finish_reason": "tool_calls" if reply["response"].get("tool_calls") else "stop"}], "usage": reply["usage"]})
        client_type = type(self.client)
        with patch.object(models.httpx, "AsyncClient", side_effect=lambda **kwargs:
                          client_type(transport=httpx.MockTransport(self.report_provider(provider)), **kwargs)):
            outcome = await analysis.CaseAnalysis(self.db, run, context, request, parent).execute()
        self.assertEqual(outcome["status"], "completed", outcome["result"]["stop_reason"])
        self.assertEqual(len(self.messages), 3)
        expected = {"origin": "historical_reuse", "already_in_history": "H1", "row_alert_refs": [["A1"], ["A2"], []]}
        for body in self.messages[1:]:
            model_context = json.loads(body["messages"][1]["content"])
            tools_visible = [json.loads(message["content"]) for message in body["messages"] if message["role"] == "tool"]
            visible = next(item for item in tools_visible + model_context["evidence"] if item.get("evidence_id") == "E1")
            self.assertEqual(visible["source_alignment"], expected)
            self.assertEqual(next(item["data"]["report"]["summary"] for item in model_context["evidence"]
                                  if item["kind"] == "prior_analysis"), history_summary)
        saved_tool = outcome["result"]["evidence"][-1]
        self.assertNotIn("source_alignment", saved_tool)
        self.assertEqual(saved_tool["rows"], parent["evidence"][-2]["rows"])
        self.assertEqual(outcome["result"]["report"]["query_sources"],
                         [{"evidence_id": "E1", **expected, "reused_from": saved_tool["reused_from"],
                           "tool": "network_connections", "query_scope": saved_tool["query_scope"],
                           "query_status": "success_with_rows", "returned_count": 3}])
        self.assertIn("本次未重新查询该来源", outcome["result"]["markdown"])
        self.assertIn("E1/rows/2：未匹配选定告警的来源事件ID", outcome["result"]["markdown"])
        clipped = json.loads(tools.model_result({**saved_tool, "rows": [{**saved_tool["rows"][0], "process_name": "x" * 9000}]}, context))
        self.assertEqual(clipped["rows"], [])
        self.assertEqual(clipped["source_alignment"]["row_alert_refs"], [])
        fresh = {key: value for key, value in saved_tool.items() if key != "reused_from"}
        self.assertEqual(tools.source_alignment(fresh, context)["origin"], "current_tool_result")
        self.assertNotIn("already_in_history", tools.source_alignment(fresh, context))
        self.assertEqual(analysis.encoded(context), original_context)
        self.assertEqual(analysis.encoded(parent), original_parent)
        self.assertEqual((await self.client.get(outcome["result_url"])).json()["result"], outcome["result"])
        self.assertEqual((await self.client.get(outcome["report_url"])).text, outcome["result"]["markdown"])
        self.lake.assert_not_awaited()

    async def test_protocol_uncertainty_does_not_allow_unsupported_assertions(self):
        root = Path(__file__).resolve().parents[3] / "docs/operations/evidence/investigation-audit-fixes-20261031/live-r7/results"
        result = json.loads(next(root.glob("*-followup-result.response.txt")).read_text(encoding="utf-8"))["result"]
        context = json.loads(next(root.glob("*-step-1.response.txt")).read_text(encoding="utf-8"))["data"]
        response = json.loads(next(root.glob("*-step-10.response.txt")).read_text(encoding="utf-8"))["data"]["response"]["content"]
        original = analysis.AnalysisConclusion.model_validate_json(response).model_dump(mode="json")
        # The actual r7 reply contains both valid uncertainty and unsupported
        # negative claims. Allowing one phrase must not accept the whole reply.
        with self.assertRaisesRegex(ValueError, "unobserved_application_protocol_use_gaps"):
            analysis.validate_synthesis(original, context, result["evidence"])
        report = {**original, "summary": "应用协议待核。", "findings": [], "relationships": [],
                  "member_assessments": [{**item, "summary": "材料不足，性质待核。"} for item in original["member_assessments"]]}
        for text in ("TCP/443不直接证明HTTPS。", "HTTPS尚未确认。", "无法确认是否使用HTTPS/TLS。",
                     "HTTPS/TLS协议尚未证实。", "SSL协议待核实。", "尚未验证TLS1.3。"):
            with self.subTest(allowed=text):
                analysis.validate_synthesis({**report, "summary": text}, context, result["evidence"])
        for text in ("使用HTTPS连接。", "协议标注TCP/443，非TLS/HTTPS。", "TCP/443≠HTTPS。",
                     "不是HTTPS。", "并非无法确认HTTPS。", "无法确认HTTPS连接已证实存在。",
                     "HTTPS尚未确认，但已证实TLS。", "无法确认HTTPS；实际使用SSL。"):
            with self.subTest(rejected=text), self.assertRaisesRegex(ValueError, "unobserved_application_protocol_use_gaps"):
                analysis.validate_synthesis({**report, "summary": text}, context, result["evidence"])

    async def test_r7_fenced_response_gets_one_chinese_correction_with_uncertainty(self):
        root = Path(__file__).resolve().parents[3] / "docs/operations/evidence/investigation-audit-fixes-20261031/live-r7/results"
        steps = sorted([json.loads(path.read_text(encoding="utf-8")) for path in
                        root.glob("*-followup-step-*.response.txt")], key=lambda step: step["seq"])
        context = steps[0]["data"]
        parent = json.loads(next(root.glob("*-parent-result.response.txt")).read_text(encoding="utf-8"))["result"]
        parent = current_network_fixture(parent)
        original_parent = analysis.encoded(parent)
        request = analysis.CaseAnalysisRequest.model_validate_json(next(root.glob("*-followup.body.json")).read_text(encoding="utf-8"))
        replies = [step["data"] for step in steps if "response" in step["data"]]
        good = {"summary": "本次复用历史网络记录，无新查询。TCP/443不直接证明HTTPS。未证实攻击也不等于证实非攻击。",
                "findings": [{"text": "前两行分别匹配A1和A2的来源事件ID，第三行未匹配所选告警，关联仍待核。",
                              "evidence_ids": ["A1", "A2", "E1"]}],
                "counterevidence": [], "gaps": ["缺少进程关联和协议层证据"], "recommendations": [],
                "member_assessments": [{"alert_id": item["data"]["alert_id"], "status": "unresolved",
                    "role": "undetermined", "summary": "告警来源对应历史连接记录，HTTPS尚未确认，行为性质待核。",
                    "evidence_ids": [item["evidence_id"], "E1"]} for item in context["evidence"] if item["kind"] == "alert"]}
        run = InvestigationRun(id=UUID(int=840), tenant_id=TENANT, case_id=context["case_id"],
                               raw_alert={"scope": {}}, total_tokens=0, iterations=0)
        self.runs[run.id] = run
        exchanges = [*replies[:2], {"response": {"content": json.dumps(good)},
                                   "usage": {"prompt_tokens": 100, "completion_tokens": 50}}]
        def provider(http_request):
            self.messages.append(json.loads(http_request.content))
            reply = exchanges[len(self.messages) - 1]
            return httpx.Response(200, json={"choices": [{"message": reply["response"],
                "finish_reason": "tool_calls" if reply["response"].get("tool_calls") else "stop"}], "usage": reply["usage"]})
        client_type = type(self.client)
        with patch.object(models.httpx, "AsyncClient", side_effect=lambda **kwargs:
                          client_type(transport=httpx.MockTransport(self.report_provider(provider)), **kwargs)):
            outcome = await analysis.CaseAnalysis(self.db, run, context, request, parent).execute()
        self.assertEqual(outcome["status"], "completed", outcome["result"]["stop_reason"])
        self.assertEqual(len(self.messages), 3)
        self.assertIn("完整中文JSON", self.messages[-1]["messages"][0]["content"])
        self.assertIn("未证实攻击≠证实非攻击", self.messages[-1]["messages"][0]["content"])
        self.assertNotIn("tools", self.messages[-1])
        validation = [json.loads(item.content) for item in self.artifacts if item.kind == "case_analysis_step"
                      and "errors" in json.loads(item.content)]
        self.assertEqual(validation[0]["errors"][0]["type"], "json_invalid")
        self.assertEqual(len(validation), 1)
        self.assertEqual(outcome["result"]["report"]["summary"], good["summary"])
        self.assertEqual(outcome["result"]["report"]["member_coverage"]["not_assessed_count"], 0)
        self.assertEqual((await self.client.get(outcome["result_url"])).json()["result"], outcome["result"])
        self.assertEqual(analysis.encoded(parent), original_parent)
        self.lake.assert_not_awaited()

    async def test_original_sources_are_frozen_model_visible_and_bounded(self):
        source_path = Path(__file__).resolve().parents[3] / "docs/operations/evidence/INVHTTP-20261028-01/results/office-powershell/001-source-0.response.txt"
        source = json.loads(source_path.read_text(encoding="utf-8"))
        self.case.description = "Case background; not an independent observation."
        self.alert.description, self.alert.raw_event = source["description"], source["raw_event"]
        response = await self.start()
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["status"], "completed", response.text)
        material = data["result"]["evidence"][0]["data"]["source_material"]
        self.assertEqual(material["description"]["text"], source["description"])
        self.assertIn("4100", material["description"]["text"])
        self.assertEqual(json.loads(material["raw_event"]["text"]), source["raw_event"])
        self.assertEqual(material["raw_event"]["sha256"], hashlib.sha256(material["raw_event"]["text"].encode()).hexdigest())
        model_view = json.loads(self.messages[0]["messages"][1]["content"])
        model_material = model_view["evidence"][0]["data"]["source_material"]
        self.assertEqual(model_material["description"]["text"], source["description"])
        self.assertEqual(json.loads(model_material["raw_event"]["text"]), source["raw_event"])
        self.assertFalse(model_material["raw_event"]["model_truncated"])
        self.assertEqual(data["result"]["case_material"]["description"]["text"], self.case.description)
        read = await self.client.get(data["evidence_url"] + "/A1")
        self.assertEqual(read.json()["evidence"]["data"]["source_material"], material)

        # A multi-member oversized source exercises both byte limits without any I/O.
        members = [SimpleNamespace(id=UUID(int=i), description="证" * 2000,
                                   raw_event={"full_log": "据" * 10000}) for i in range(1, 10)]
        case_material, alert_material = sources.freeze_sources(SimpleNamespace(description="案" * 2000), members)
        context = {"source_material_schema": sources.SOURCE_SCHEMA, "case_material": case_material,
                   "evidence": [{"kind": "alert", "data": {"source_material": value}} for value in alert_material.values()]}
        original = json.dumps(context, ensure_ascii=False)
        fields = list(sources.source_fields(context))
        self.assertLessEqual(sum(field["retained_bytes"] for field in fields), sources.RUN_BYTES)
        self.assertTrue(any(field["omission_reason"] == "run_limit" for field in fields))
        self.assertTrue(any(field["omission_reason"] == "field_limit" for field in fields))
        for field in fields:
            self.assertEqual(len(field["text"].encode()), field["retained_bytes"])
            self.assertNotIn("\ufffd", field["text"])
        limited = sources.model_source_view(context)
        self.assertLessEqual(sum(field["model_retained_bytes"] for field in sources.source_fields(limited)), sources.MODEL_BYTES)
        self.assertEqual(json.dumps(context, ensure_ascii=False), original)

    async def test_original_sources_do_not_bypass_model_input_contract(self):
        self.alert.raw_event = {"class_uid": 1007, "activity_id": 1, "process": {"name": "example.exe"}}
        response = await self.start()
        self.assertEqual(response.json()["status"], "completed", response.text)
        saved = response.json()["result"]["evidence"][0]["data"]["source_material"]["raw_event"]
        self.assertEqual(json.loads(saved["text"]), self.alert.raw_event)
        view = json.loads(self.messages[0]["messages"][1]["content"])
        field = view["evidence"][0]["data"]["source_material"]["raw_event"]
        self.assertEqual(field["text"], "")
        self.assertEqual(field["model_omission_reason"], "llm_input_contract")
        self.assertTrue(any("输入合同" in gap for gap in response.json()["result"]["report"]["gaps"]))

    async def test_source_changes_and_legacy_material_invalidate_reuse_without_rewriting_history(self):
        self.alert.raw_event = {"full_log": "x" * 20000, "tail": "before"}
        first = (await self.start()).json()
        first_report = first["result"]["markdown"]
        artifact = next(item for item in self.artifacts if item.kind == "case_analysis_result")
        legacy = json.loads(artifact.content)
        legacy.pop("source_material_schema")
        legacy.pop("case_material")
        legacy["evidence"][0]["data"].pop("source_material")
        artifact.content = analysis.encoded(legacy)
        artifact.sha256 = hashlib.sha256(artifact.content.encode()).hexdigest()
        self.runs[UUID(first["run_id"])].raw_alert.pop("source_material_schema")
        follow = await self.client.post(self.path + "/investigate", json={
            "operation_key": str(UUID(int=101)), "previous_run_id": first["run_id"],
            "start": NOW.isoformat(), "end": (NOW + timedelta(minutes=5)).isoformat()})
        self.assertEqual(follow.json()["status"], "completed", follow.text)
        self.assertEqual(self.lake.await_count, 2)
        self.assertEqual(next(item for item in follow.json()["result"]["evidence"] if item["kind"] == "prior_analysis")["data"]["report"], legacy["report"])
        prior_field = follow.json()["result"]["evidence"][0]["data"]["source_material"]["raw_event"]
        self.alert.raw_event = {**self.alert.raw_event, "tail": "after"}
        changed = (await self.start(102)).json()
        current_field = changed["result"]["evidence"][0]["data"]["source_material"]["raw_event"]
        self.assertEqual(current_field["text"], prior_field["text"])
        self.assertNotEqual(current_field["sha256"], prior_field["sha256"])
        self.assertEqual(self.lake.await_count, 3)
        self.alert.description = "Only description changed."
        self.assertEqual((await self.start(103)).json()["status"], "completed")
        self.assertEqual(self.lake.await_count, 4)
        self.assertEqual((await self.start()).json()["result"], legacy)
        self.assertEqual((await self.client.get(first["report_url"])).text, first_report)
        self.assertEqual(self.lake.await_count, 4)

    async def test_preview_steps_and_download_deliver_the_saved_case_workflow(self):
        preview = await self.client.post(self.path + "/investigation-context", json={
            "start": NOW.isoformat(), "end": (NOW + timedelta(minutes=5)).isoformat(),
            "selected_member_ids": [str(self.alert.id)],
        })
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(preview.json()["context"]["read_member_ids"], [str(self.alert.id)])
        self.assertEqual(len(preview.json()["tools"]), 2)
        self.assertEqual(self.runs, {})
        self.config.assert_not_awaited()
        self.lake.assert_not_awaited()
        self.db.commit.assert_not_awaited()

        started = (await self.start()).json()
        page = await self.client.get(started["steps_url"], params={"limit": 2})
        self.assertEqual([item["seq"] for item in page.json()["items"]], [1, 2])
        next_page = await self.client.get(started["steps_url"], params={"after_seq": page.json()["next_after_seq"]})
        self.assertEqual(next_page.json()["items"][0]["seq"], 3)
        self.assertIsNone(next_page.json()["next_after_seq"])
        details = []
        for item in page.json()["items"] + next_page.json()["items"]:
            detail = await self.client.get(item["detail_url"])
            self.assertEqual(detail.status_code, 200, detail.text)
            details.append(detail.json()["data"])
        request = next(item for item in details if "call_id" in item)
        returned = next(item for item in details if "model_message" in item)
        self.assertEqual(returned["call_id"], request["call_id"])
        self.assertEqual(request["tool"], "process_activity")
        self.assertEqual(request["arguments"], {"hostname": "host-01", "limit": 20})
        self.assertEqual(returned["evidence"]["rows"][0]["event_id"], "event-7001")
        self.assertEqual(json.loads(returned["model_message"])["evidence_id"], "E1")
        download = await self.client.get(started["report_url"])
        self.assertEqual(download.text, started["result"]["markdown"])
        self.assertIn("attachment;", download.headers["content-disposition"])
        self.assertEqual((await self.client.get(started["steps_url"] + "/999")).status_code, 404)
        self.assertEqual(len(self.messages), 2)  # Every subsequent request was read-only.

    async def test_followup_question_preserves_previous_report_and_can_refresh_queries(self):
        first = (await self.start()).json()
        original = first["result"]
        body = {"operation_key": str(UUID(int=101)), "previous_run_id": first["run_id"],
                "start": NOW.isoformat(), "end": (NOW + timedelta(minutes=5)).isoformat(),
                "question": "继续核对脚本启动来源，已有证据是否足够？"}
        response = await self.client.post(self.path + "/investigate", json=body)
        self.assertEqual(response.status_code, 200, response.text)
        followup = response.json()
        self.assertNotEqual(followup["run_id"], first["run_id"])
        self.assertEqual(followup["previous_run_id"], first["run_id"])
        historical = next(item for item in followup["result"]["evidence"] if item["kind"] == "prior_analysis")
        self.assertEqual(historical["data"]["report"], original["report"])
        model_view = json.loads(self.messages[2]["messages"][1]["content"])
        model_history = next(item for item in model_view["evidence"] if item["kind"] == "prior_analysis")
        self.assertEqual(model_history["data"]["omitted_report_fields"],
                         ["timeline", "member_coverage", "recommendations", "query_sources"])
        self.assertNotIn("timeline", model_history["data"]["report"])
        self.assertEqual(model_history["data"]["report"]["summary"], original["report"]["summary"])
        self.assertEqual(model_history["data"]["report"]["gaps"], original["report"]["gaps"])
        self.assertTrue(model_view["member_sets_equal"])
        self.assertEqual(model_history["data"]["scope"], {"same_as_current": True})
        model_alert = next(item for item in model_view["evidence"] if item["kind"] == "alert")
        self.assertIn("saved_analysis", model_alert["data"]["omitted_fields"])
        self.assertNotIn("saved_analysis", model_alert["data"])
        self.assertIn("saved_analysis", followup["result"]["evidence"][0]["data"])
        self.assertEqual(self.lake.await_count, 1)
        self.assertEqual(followup["result"]["evidence"][-1]["reused_from"]["run_id"], first["run_id"])
        self.assertEqual((await self.client.get(first["result_url"])).json()["result"], original)
        repeated = await self.client.post(self.path + "/investigate", json=body)
        self.assertEqual(repeated.json()["run_id"], followup["run_id"])
        self.assertEqual(len(self.messages), 4)
        body.update(operation_key=str(UUID(int=102)), refresh_queries=True)
        refreshed = await self.client.post(self.path + "/investigate", json=body)
        self.assertEqual(refreshed.status_code, 200, refreshed.text)
        self.assertEqual(self.lake.await_count, 2)
        self.assertNotIn("reused_from", refreshed.json()["result"]["evidence"][-1])

    async def test_required_tool_choice_uses_scoped_dispatch_and_prior_query(self):
        first = (await self.start()).json()
        self.assertNotIn("required_tools", self.runs[UUID(first["run_id"])].raw_alert["intent"]["request"])
        body = {"operation_key": str(UUID(int=103)), "previous_run_id": first["run_id"],
                "start": NOW.isoformat(), "end": (NOW + timedelta(minutes=5)).isoformat(),
                "question": "请再次核对进程记录", "required_tools": ["process_activity"]}
        follow = (await self.client.post(self.path + "/investigate", json=body)).json()
        self.assertEqual(follow["status"], "completed")
        self.assertEqual(self.messages[2]["tool_choice"], {"type": "function", "function": {"name": "process_activity"}})
        self.assertNotIn("response_format", self.messages[2])
        self.assertNotIn("tool_choice", self.messages[3])
        self.assertEqual(self.lake.await_count, 1)
        self.assertEqual(follow["result"]["evidence"][-1]["reused_from"]["run_id"], first["run_id"])

    async def test_required_tool_cannot_be_silently_skipped_or_unavailable(self):
        def provider(request):
            return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
                                           "usage": {"prompt_tokens": 100, "completion_tokens": 10}})
        client_type = type(self.client)
        with patch.object(models.httpx, "AsyncClient", side_effect=lambda **kwargs:
                          client_type(transport=httpx.MockTransport(self.report_provider(provider)), **kwargs)):
            body = {"operation_key": str(UUID(int=104)), "start": NOW.isoformat(),
                    "end": (NOW + timedelta(minutes=5)).isoformat(), "required_tools": ["process_activity"]}
            skipped = (await self.client.post(self.path + "/investigate", json=body)).json()
            self.assertEqual(skipped["status"], "failed")
            self.assertEqual(skipped["result"]["stop_reason"], "required_tool_not_called")
            body.update(operation_key=str(UUID(int=105)), required_tools=["not_offered"])
            unavailable = (await self.client.post(self.path + "/investigate", json=body)).json()
            self.assertEqual(unavailable["result"]["stop_reason"], "required_tool_unavailable")
            self.assertEqual(unavailable["result"]["usage"]["model_calls"], 0)
        self.lake.assert_not_awaited()

    async def test_followup_requires_finished_run_and_same_member_window(self):
        first = (await self.start()).json()
        body = {"operation_key": str(UUID(int=101)), "previous_run_id": first["run_id"],
                "start": NOW.isoformat(), "end": (NOW + timedelta(minutes=6)).isoformat()}
        rejected = await self.client.post(self.path + "/investigate", json=body)
        self.assertEqual(rejected.status_code, 409, rejected.text)
        self.assertEqual(rejected.json()["detail"], "followup_scope_changed")
        self.runs[UUID(first["run_id"])].status = "running"
        body["end"] = (NOW + timedelta(minutes=5)).isoformat()
        rejected = await self.client.post(self.path + "/investigate", json=body)
        self.assertEqual(rejected.json()["detail"], "previous_analysis_not_finished")
        self.assertEqual(len(self.runs), 1)
        self.assertEqual(len(self.messages), 2)
