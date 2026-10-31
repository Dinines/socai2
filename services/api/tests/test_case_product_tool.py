"""Case -> model tool call -> Actions HTTP -> saved evidence, with HTTP/DB doubles."""
from datetime import timedelta
import json
from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock, patch
from uuid import UUID

import httpx

import test_case_analysis_api as examples
from app.investigation_v2 import case_product_tools as product
from app.models.connector import Connector

ORIGINAL_CLIENT = httpx.AsyncClient
CONNECTOR = UUID(int=70)


class ProductToolExamples(IsolatedAsyncioTestCase):
    # Reuse the existing ledger/API fixture without inheriting its unchanged test suite.
    report_provider = examples.CaseAnalysisExamples.report_provider
    add = examples.CaseAnalysisExamples.add
    start = examples.CaseAnalysisExamples.start

    async def asyncSetUp(self):
        await examples.CaseAnalysisExamples.asyncSetUp(self)
        self.alert.connector_id = CONNECTOR
        self.connector = Connector(id=CONNECTOR, tenant_id=examples.TENANT, name="source-instance",
            connector_type="crowdstrike", is_enabled=True, allowed_capabilities=["get_host"],
            auth_config={"encrypted": "fixture"}, connector_config={"base_url": "https://product.invalid"})
        self.actions_requests = []
        vault = MagicMock()
        vault.decrypt_dict.return_value = {"client_id": "source-client", "client_secret": "fixture-secret"}
        for patcher in (
            patch.object(product, "get_vault", return_value=vault),
            patch.object(examples.models.httpx, "AsyncClient", side_effect=lambda **kwargs: ORIGINAL_CLIENT(
                transport=httpx.MockTransport(self.report_provider(self.provider)), **kwargs)),
            patch.object(examples.tools.settings, "AISOC_DISABLE_CLICKHOUSE", True),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    async def execute(self, statement, params=None):
        entities = [item.get("entity") for item in getattr(statement, "column_descriptions", [])]
        if Connector in entities:
            values = statement.compile().params
            self.assertEqual(values["tenant_id_1"], examples.TENANT)
            if isinstance(values["id_1"], (list, tuple, set)):
                self.assertEqual(set(values["id_1"]), {CONNECTOR})
            else:
                self.assertEqual(values["id_1"], CONNECTOR)
            return examples.result(self.connector, [self.connector])
        return await examples.CaseAnalysisExamples.execute(self, statement, params)

    def provider(self, request):
        body = json.loads(request.content)
        if request.url.path == "/api/v1/live-actions/dispatch":
            self.actions_requests.append(body)
            self.assertEqual(request.method, "POST")
            self.assertEqual(body["vendor_id"], "crowdstrike")
            self.assertEqual(body["capability"], "get_host")
            self.assertEqual(body["target"], "host-01")
            self.assertEqual(body["tenant_id"], str(examples.TENANT))
            self.assertEqual(body["case_id"], str(examples.CASE))
            self.assertFalse(body["dry_run"])
            self.assertEqual(body["params"], {})
            self.assertEqual(body["auth_config"], {"client_id": "source-client", "client_secret": "fixture-secret",
                                                 "base_url": "https://product.invalid"})
            if self.scenario == "failed":
                return httpx.Response(503, json={"detail": "source unavailable"})
            return httpx.Response(200, json={"mode": "live", "result": {
                "request_id": str(UUID(int=80)), "vendor_id": "crowdstrike", "capability": "get_host",
                "status": "succeeded", "details": {"found": self.scenario != "empty",
                    "hostname": "host-01", "device_id": "device-01", "platform": "Windows",
                    "containment_status": "normal", "unused_vendor_field": "not forwarded"}}})
        self.messages.append(body)
        if body["messages"][-1]["role"] != "tool":
            message = {"tool_calls": [{"id": "call-host-01", "type": "function", "function": {
                "name": product.TOOL_NAME, "arguments": json.dumps({"source_alert_id": str(self.alert.id),
                                                                    "hostname": "host-01"})}}]}
            finish = "tool_calls"
        else:
            returned = next(json.loads(m["content"]) for m in body["messages"] if m["role"] == "tool" and "evidence_id" in json.loads(m["content"]))
            self.assertTrue(any(m.get("tool_call_id") == "call-host-01" for m in body["messages"]))
            self.assertEqual(returned["source"]["connector_id"], str(CONNECTOR))
            message = {"content": json.dumps({"summary": "当前快照查询完成，历史行为仍需核对。",
                "findings": [{"text": "产品查询返回主机资料" if returned["rows"] else "未获得主机资料",
                              "evidence_ids": ["E1"]}], "counterevidence": [],
                "gaps": ["当前快照不能证明历史窗口状态"], "recommendations": [],
                "member_assessments": examples.single_member_assessment()})}
            finish = "stop"
        return httpx.Response(200, json={"choices": [{"message": message, "finish_reason": finish}],
                                        "usage": {"prompt_tokens": 100, "completion_tokens": 50}})

    async def test_source_bound_host_read_reaches_model_steps_and_report(self):
        preview = await self.client.post(self.path + "/investigation-context", json={
            "start": examples.NOW.isoformat(), "end": (examples.NOW + timedelta(minutes=5)).isoformat()})
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual([item["function"]["name"] for item in preview.json()["tools"]], [product.TOOL_NAME])
        self.assertEqual(self.actions_requests, [])
        # A host in another source alert is not implicitly queryable through this connector.
        tool = await product.ProductHostTool.from_context(self.db, examples.TENANT, preview.json()["context"])
        denied = await tool.execute({"source_alert_id": str(UUID(int=999)), "hostname": "host-01"})
        self.assertFalse(denied["available"])
        response = await self.start()
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        evidence = data["result"]["evidence"][-1]
        self.assertTrue(evidence["available"])
        self.assertEqual(evidence["rows"][0]["device_id"], "device-01")
        self.assertNotIn("unused_vendor_field", evidence["rows"][0])
        self.assertEqual(evidence["query_scope"]["time_semantics"], "current_snapshot")
        self.assertEqual(evidence["upstream_request_id"], str(UUID(int=80)))
        snapshot = next(item for item in data["result"]["report"]["timeline"] if item["time_kind"] == "snapshot")
        self.assertEqual(snapshot["timestamp"], evidence["observed_at"])
        self.assertIsNone(snapshot["in_window"])
        self.assertEqual(snapshot["source_record_id"], "device-01")
        self.assertEqual(
            [tool for tool in self.messages[0]["tools"] if tool["function"]["name"] != "finish_analysis"],
            preview.json()["tools"],
        )
        steps = (await self.client.get(data["steps_url"])).json()["items"]
        details = [(await self.client.get(item["detail_url"])).json()["data"] for item in steps]
        returned = next(item for item in details if "model_message" in item)
        self.assertEqual(returned["evidence"], evidence)
        report = await self.client.get(data["report_url"])
        self.assertIn("device-01", report.text)
        self.assertIn(str(CONNECTOR), report.text)
        self.assertNotIn("fixture-secret", json.dumps(details) + report.text)
        again = (await self.start(101)).json()
        self.assertNotIn("reused_from", again["result"]["evidence"][-1])
        self.assertEqual(len(self.actions_requests), 2)
        self.lake.assert_not_awaited()

    async def test_empty_and_failed_reads_stay_distinct(self):
        for key, scenario in ((110, "empty"), (111, "failed")):
            with self.subTest(scenario=scenario):
                self.scenario = scenario
                response = await self.start(key)
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()["result"]
                evidence = result["evidence"][-1]
                self.assertEqual(evidence["available"], scenario == "empty")
                self.assertEqual(evidence["rows"], [])
                self.assertEqual(result["completion"], "partial")
                if scenario == "failed":
                    self.assertEqual(evidence["reason"], "product_query_failed")
                    self.assertTrue(any("未能检查" in gap for gap in result["report"]["gaps"]))
