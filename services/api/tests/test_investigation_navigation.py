"""Business entry -> saved Run -> evidence -> Tool exchange -> source row."""
from datetime import datetime, timedelta
import json
from unittest import IsolatedAsyncioTestCase
from uuid import UUID

from sqlalchemy.dialects import postgresql

import test_case_analysis_api as examples
import test_case_synthesis as synthesis
from app.models.alert import Alert
from app.models.investigation import InvestigationEvent, InvestigationRun


def mapped(rows):
    result = examples.result(rows=rows)
    result.mappings.return_value.all.return_value = rows
    result.mappings.return_value.one_or_none.return_value = rows[0] if rows else None
    return result


class NavigationExamples(IsolatedAsyncioTestCase):
    add = examples.CaseAnalysisExamples.add
    start = examples.CaseAnalysisExamples.start
    provider = synthesis.MultiAlertExamples.provider
    asyncSetUp = synthesis.MultiAlertExamples.asyncSetUp

    def index_row(self, run):
        raw = run.raw_alert or {}
        artifact = next((item for item in self.artifacts if item.run_id == run.id and item.kind == "case_analysis_result"), None)
        result = json.loads(artifact.content) if artifact else {}
        return {"run_id": run.id, "recorded_case_reference": run.case_id, "status": run.status,
                "started_at": run.started_at, "completed_at": run.completed_at,
                "profile": raw.get("analysis_profile"), "source_alert_id": raw.get("id"), "scope": raw.get("scope"),
                "previous_run_id": raw.get("previous_run_id"), "result_available": artifact is not None,
                "completion": result.get("completion"), "stop_reason": result.get("stop_reason"),
                "summary": result.get("report", {}).get("summary"), "summary_truncated": False}

    async def execute(self, statement, params=None):
        descriptions = getattr(statement, "column_descriptions", [])
        names = [item.get("name") for item in descriptions]
        entities = [item.get("entity") for item in descriptions]
        values = statement.compile().params
        if "recorded_case_reference" in names:
            self.statements.append(statement)
            compiled = statement.compile(dialect=postgresql.dialect())
            self.assertIn(examples.TENANT, compiled.params.values())
            rows = [self.index_row(run) for run in self.runs.values()]
            if isinstance(values.get("id_1"), UUID):
                return mapped([row for row in rows if row["run_id"] == values["id_1"]])
            self.assertIn("case_analysis.v1", compiled.params.values())
            if "case_id_1" not in values:
                self.assertIn("selected_member_ids", compiled.params.values())
            members = next((value for value in values.values() if isinstance(value, list)), [])
            if "case_id_1" in values:
                rows = [row for row in rows if (row["profile"] == "case_analysis.v1" and row["recorded_case_reference"] == values["case_id_1"])
                        or (row["profile"] != "case_analysis.v1" and row["source_alert_id"] in members)]
            else:
                self.assertIn("?|", str(compiled))
                # ARRAY parameters are scalar binds; the legacy IN list is the same requested membership.
                rows = [row for row in rows if (row["profile"] == "case_analysis.v1" and set(row["scope"]["selected_member_ids"]) & set(members))
                        or (row["profile"] != "case_analysis.v1" and row["source_alert_id"] in members)]
            rows.sort(key=lambda row: (row["started_at"], row["run_id"]), reverse=True)
            after_at = next((value for value in values.values() if isinstance(value, datetime)), None)
            if after_at:
                after_id = next(value for value in values.values() if isinstance(value, UUID) and value != examples.TENANT)
                rows = [row for row in rows if (row["started_at"], row["run_id"]) < (after_at, after_id)]
            return mapped(rows[:statement._limit_clause.value])
        if names == ["seq", "content"]:
            run_id = values["run_id_1"]
            return mapped([{"seq": event.seq, "content": artifact.content} for event in self.events
                for artifact in self.artifacts if event.run_id == run_id and event.kind == "case_analysis_tool"
                and artifact.event_id == event.id and artifact.kind == "case_analysis_step"])
        if Alert in entities:
            ids = values.get("id_1")
            alerts = [item for item in self.alerts if ids is None or item.id == ids or isinstance(ids, list) and item.id in ids]
            return examples.result(rows=[item.id for item in alerts] if names == ["id"] else alerts)
        if entities == [InvestigationEvent] and values.get("id_1"):
            source = examples.fixtures.verdict(1, "Needs evidence")[1]
            return examples.result(source if source.id == values["id_1"] else None)
        if entities == [InvestigationRun] and values.get("case_id_1"):
            run = self.runs.get(values.get("id_1"))
            if run is not None and run.case_id != values["case_id_1"]:
                return examples.result()
        return await examples.CaseAnalysisExamples.execute(self, statement, params)

    async def test_three_filters_reach_the_same_evidence_and_recorded_tool_exchange(self):
        started = await self.start()
        self.assertEqual(started.status_code, 200, started.text)
        data = started.json()
        saved_commits = self.db.commit.await_count
        for kind, identity in (("alert_id", self.alerts[0].id), ("incident_id", examples.fixtures.INCIDENT), ("case_id", examples.CASE)):
            response = await self.client.get("/api/v2/investigation/executions", params={kind: str(identity)})
            self.assertEqual(response.status_code, 200, response.text)
            entry = response.json()["items"][0]
            self.assertEqual(entry["run_id"], data["run_id"])
            self.assertEqual(entry["scope"], data["scope"])
            self.assertEqual(entry["result_url"], data["result_url"])
            self.assertEqual(entry["completion"], "partial")
            result = (await self.client.get(entry["result_url"])).json()
            self.assertEqual(result["result"], data["result"])
        metadata = (await self.client.get(data["execution_url"])).json()
        self.assertEqual(metadata["run_type"], "case_analysis")
        index = (await self.client.get(data["evidence_url"])).json()["items"]
        self.assertEqual([item["evidence_id"] for item in index], ["A1", "T1", "A2", "A3", "E1"])
        link = next(item["url"] for item in data["navigation"]["findings"][0]["evidence_links"] if item["evidence_id"] == "E1")
        evidence = (await self.client.get(link)).json()
        self.assertEqual(evidence["query_execution"], "recorded_attempt")
        trace = evidence["tool_trace"]
        request = (await self.client.get(trace["request_step_url"])).json()["data"]
        returned = (await self.client.get(trace["response_step_url"])).json()["data"]
        self.assertEqual(request["call_id"], returned["call_id"])
        self.assertEqual(request["tool"], "process_activity")
        self.assertEqual(returned["evidence"], evidence["evidence"])
        source = (await self.client.get(evidence["rows"][0]["url"])).json()
        self.assertEqual(source["source_record_id"], "event-7001")
        self.assertEqual(source["row"], returned["evidence"]["rows"][0])
        self.assertIn(evidence["rows"][0]["url"], [item["row_url"] for item in data["navigation"]["timeline"]])
        report = (await self.client.get(data["report_url"])).text
        self.assertIn(f"[E1]({link})", report)
        self.assertIn(evidence["rows"][0]["url"], report)
        triage = (await self.client.get(data["evidence_url"] + "/T1")).json()
        self.assertEqual(triage["source_links"]["source_event_id"], str(UUID(int=101)))
        self.assertEqual(self.db.commit.await_count, saved_commits)
        self.assertEqual(len(self.messages), 2)
        self.assertEqual(self.lake.await_count, 1)

    async def test_followup_reuse_links_back_without_changing_the_original_report(self):
        first = (await self.start()).json()
        response = await self.client.post(self.path + "/investigate", json={"operation_key": str(UUID(int=101)),
            "previous_run_id": first["run_id"], "question": "继续核对关联依据", "start": examples.NOW.isoformat(),
            "end": (examples.NOW + timedelta(minutes=5)).isoformat()})
        self.assertEqual(response.status_code, 200, response.text)
        followup = response.json()
        self.assertEqual(followup["previous_result_url"], first["result_url"])
        reused = (await self.client.get(followup["evidence_url"] + "/E1")).json()
        self.assertEqual(reused["query_execution"], "reused")
        self.assertEqual(reused["source_links"]["reused_evidence_url"], first["evidence_url"] + "/E1")
        original = (await self.client.get(reused["source_links"]["reused_evidence_url"])).json()
        self.assertEqual(reused["evidence"]["rows"], original["evidence"]["rows"])
        self.assertNotEqual(reused["tool_trace"]["response_step_url"], original["tool_trace"]["response_step_url"])
        historical = (await self.client.get(followup["evidence_url"] + "/H1")).json()
        self.assertEqual(historical["source_links"]["previous_result_url"], first["result_url"])
        self.assertEqual((await self.client.get(first["result_url"])).json()["result"], first["result"])
        self.assertEqual((await self.client.get(first["evidence_url"] + "/E1/rows/50")).status_code, 404)
        self.assertEqual((await self.client.get(first["evidence_url"] + "/E999")).status_code, 404)
        wrong_case = first["evidence_url"].replace(str(examples.CASE), str(UUID(int=999)))
        self.assertEqual((await self.client.get(wrong_case + "/E1")).status_code, 404)
        self.assertEqual(self.lake.await_count, 1)

    async def test_legacy_records_keep_the_native_reader_and_unselected_members_are_excluded(self):
        current = (await self.start()).json()
        legacy_id, unknown_id = UUID(int=800), UUID(int=801)
        for run_id, raw in ((legacy_id, {"id": str(self.alerts[0].id)}), (unknown_id, {})):
            self.runs[run_id] = InvestigationRun(id=run_id, tenant_id=examples.TENANT, case_id=str(examples.CASE),
                raw_alert=raw, status="completed", started_at=examples.NOW, completed_at=examples.NOW)
        self.alerts.append(examples.fixtures.alert(4))
        self.case.alert_ids.append(self.alerts[-1].id)
        base = "/api/v2/investigation/executions"
        excluded = (await self.client.get(base, params={"alert_id": str(self.alerts[-1].id)})).json()
        self.assertEqual(excluded["items"], [])
        indexed = (await self.client.get(base, params={"case_id": str(examples.CASE)})).json()["items"]
        self.assertEqual({item["run_id"] for item in indexed}, {current["run_id"], str(legacy_id)})
        old = next(item for item in indexed if item["run_id"] == str(legacy_id))
        self.assertEqual(old["native_reader"], "legacy_ledger")
        self.assertEqual(old["result_url"], f"/api/v1/investigations/{legacy_id}")
        self.assertIsNone(old["case_id"])
        self.assertIsNone(old["completion"])
        self.assertIsNone(old["result_available"])
        unknown = (await self.client.get(base + f"/{unknown_id}")).json()
        self.assertIsNone(unknown["source_alert_id"])
        self.assertEqual(unknown["run_type"], "legacy_or_other")
        self.assertEqual((await self.client.get(base)).status_code, 422)
        page = (await self.client.get(base, params={"alert_id": str(self.alerts[0].id), "limit": 1})).json()
        self.assertIsNotNone(page["next_cursor"])
        next_page = (await self.client.get(base, params={"alert_id": str(self.alerts[0].id), "limit": 1,
                                                       "cursor": page["next_cursor"]})).json()
        self.assertEqual(next_page["items"][0]["run_id"], str(legacy_id))
