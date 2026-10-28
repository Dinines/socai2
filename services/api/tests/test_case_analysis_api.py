"""Direct Case workflow examples using model HTTP, lake and ledger substitutes."""
from datetime import timedelta
import json
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
from app.investigation_v2.program_start_api import create_app
from app.models.alert import Alert
from app.models.case import Case
from app.models.investigation import InvestigationArtifact, InvestigationEvent, InvestigationRun
from app.services.llm_resolver import LlmConfig

TENANT, NOW, CASE = fixtures.TENANT, fixtures.NOW, UUID(int=30)


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
            rows = [] if self.scenario == "empty" else [("event-7001", NOW, "host-01", "powershell.exe", "script.ps1", "a" * 64, "alice")]
            return SimpleNamespace(columns=["event_id", "event_time", "src_hostname", "process_name", "file_path", "hash_sha256", "user_name"], rows=rows)
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
                transport=httpx.MockTransport(provider), **kwargs)),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.path = f"/api/v2/investigation/cases/{CASE}"

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
        self.assertEqual(self.messages[1]["messages"][-1]["tool_call_id"], "call-process-01")
        self.assertEqual(self.messages[1]["messages"][-2]["tool_calls"][0]["id"], "call-process-01")
        params = self.lake.call_args.kwargs["params"]
        self.assertEqual(params["tenant_id"], str(TENANT))
        self.assertEqual(params["hostname"], "host-01")
        self.assertEqual(params["start"], NOW.isoformat())
        self.assertEqual(params["end"], (NOW + timedelta(minutes=5)).isoformat())
        read = await self.client.get(self.path + f"/investigations/{data['run_id']}")
        self.assertEqual(read.status_code, 200, read.text)
        self.assertEqual(read.json()["result"], data["result"])
        repeat = await self.start()
        self.assertEqual(repeat.json()["run_id"], data["run_id"])
        self.assertEqual(len(self.messages), 2)
        self.assertEqual(self.lake.await_count, 1)

    async def test_empty_result_and_query_failure_remain_distinct(self):
        self.scenario = "empty"
        empty = (await self.start()).json()["result"]
        self.assertTrue(empty["evidence"][-1]["available"])
        self.assertEqual(empty["evidence"][-1]["rows"], [])
        self.assertEqual(empty["completion"], "partial")
        self.scenario = "failed"
        # A new window requires a new source query rather than reusing the empty result.
        failed = (await self.start(101, end_minutes=6)).json()["result"]
        self.assertFalse(failed["evidence"][-1]["available"])
        self.assertTrue(any("未能检查" in value for value in failed["report"]["gaps"]))

    async def test_applicable_prior_query_is_reused_in_a_new_case_run(self):
        first = (await self.start()).json()
        second = (await self.start(101)).json()
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual(self.lake.await_count, 1)
        self.assertEqual(second["result"]["evidence"][-1]["reused_from"]["run_id"], first["run_id"])

    async def test_unknown_model_usage_stops_before_query(self):
        self.scenario = "unknown_usage"
        response = await self.start()
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["result"]
        self.assertEqual(data["completion"], "partial")
        self.assertTrue(data["usage"]["unknown_usage"])
        self.lake.assert_not_awaited()

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
        self.assertIn("H1", self.messages[2]["messages"][1]["content"])
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
