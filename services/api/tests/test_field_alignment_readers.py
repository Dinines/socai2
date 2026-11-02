"""Stored-field projections through real readers; services are local substitutes."""
import copy
from datetime import timedelta
import json
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.api.v1.endpoints.alerts import AlertResponse
from app.investigation_v2 import case_analysis as analysis, incident_reader as incidents, related_investigations as related
from app.models.alert import Alert
from app.models.case import Case
from app.services import alert_projection as projection, processing_context as processing, investigation_attack_context as graph
import test_investigation_incident_api as fixtures

TENANT, NOW = fixtures.TENANT, fixtures.NOW


def record(number=1):
    alert = fixtures.alert(number)
    alert.description, alert.category, alert.priority = None, None, 50
    alert.tags, alert.ai_score, alert.created_at = [], 10, NOW
    alert.connector_type, alert.connector_id = "Splunk", UUID(int=60)
    alert.rule_id, alert.rule_name = "rule-id", "Stored rule"
    alert.confidence, alert.confidence_label, alert.confidence_rationale = 75, "high", [{"factor": "stored signal"}]
    alert.raw_event = {"metadata": {"product": {"vendor_name": "Splunk"}}, "raw_data": {"original_vendor": "Producer"}}
    alert.iocs = [{"type": "domain", "value": "shared.test"}, {"type": "hash", "value": f"hash-{number}"}]
    alert.enrichment_data["socai2_fusion"].update(identity={"source_alert_id": "connector-record", "source": "Splunk"},
                                                confidence_status="computed", event_time_source="ocsf.time")
    return alert


def result(*, rows=None, one=None):
    obj = MagicMock()
    obj.scalars.return_value.all.return_value = rows or []
    obj.all.return_value = rows or []
    obj.scalar_one_or_none.return_value = one
    return obj


class StoredProjectionExamples(TestCase):
    def test_original_vendor_is_independent_from_connector_and_ids(self):
        alert = record()
        before = copy.deepcopy(alert.enrichment_data)
        source = projection.alert_source(alert)
        self.assertEqual((source["detection_source"], source["source_alert_id"], source["external_id"]),
                         ("Producer", "connector-record", "source-1"))
        alert.raw_event.pop("raw_data")
        self.assertIsNone(projection.alert_source(alert)["detection_source"])
        self.assertEqual(alert.enrichment_data, before)
        alert.raw_event["raw_data"] = json.dumps({"deviceVendor": "CEF producer"})
        self.assertEqual(projection.alert_source(alert)["detection_source"], "CEF producer")

    def test_mapped_iocs_and_known_score_state_reach_list_dto(self):
        alert = record()
        sql = str(select(Alert).compile(dialect=postgresql.dialect()))
        self.assertIn("alerts.iocs", sql)
        dto = AlertResponse.model_validate(alert)
        self.assertEqual(dto.source["detection_source"], "Producer")
        self.assertIn({"type": "hash", "value": "hash-1"}, dto.objects)
        self.assertEqual(dto.detection["confidence"]["score"], 75)
        for state in ("unknown", "failed", "disabled"):
            alert.enrichment_data["socai2_fusion"]["confidence_status"] = state
            self.assertIsNone(projection.detection_fields(alert)["confidence"]["score"])
            self.assertIsNone(AlertResponse.model_validate(alert).confidence)
        alert.enrichment_data["socai2_fusion"].pop("confidence_status")
        self.assertEqual(projection.detection_fields(alert)["confidence"]["status"], "legacy_unverified")


class ReadPathExamples(IsolatedAsyncioTestCase):
    async def test_assignee_identity_and_name_are_tenant_scoped(self):
        alert = record()
        alert.assigned_to_id, alert.assigned_at = UUID(int=80), NOW
        db = AsyncMock()
        db.execute.return_value = result(rows=[(UUID(int=80), "analyst-name")])
        names = await projection.assignee_names(db, TENANT, [alert])
        self.assertEqual(names, {UUID(int=80): "analyst-name"})
        sql = db.execute.call_args.args[0].compile(dialect=postgresql.dialect())
        self.assertIn("users.tenant_id", str(sql))
        self.assertIn(TENANT, sql.params.values())
        dto = AlertResponse.model_validate(alert)
        self.assertEqual((dto.assigned_to_id, dto.assigned_at), (UUID(int=80), NOW))
        db.execute.side_effect = [result(rows=[alert]), result(rows=[]), result(rows=[(UUID(int=80), "analyst-name")])]
        view = await incidents.read_incident(db, tenant_id=TENANT, incident_id=fixtures.INCIDENT)
        self.assertEqual(view.members[0].assigned_to_name, "analyst-name")

    async def test_member_object_edges_tactic_counts_and_business_clock(self):
        first, second = record(), record(2)
        first.event_time = NOW - timedelta(hours=2)
        first.first_seen = NOW + timedelta(hours=1)  # old ingestion-time default
        first.mitre_tactics = ["execution", "execution", "persistence"]
        triage = fixtures.verdict(1, "Prior judgment", at=NOW + timedelta(hours=3))
        triage[1].payload["confidence"] = .91
        db = AsyncMock()
        db.execute.side_effect = [result(rows=[first, second]), result(rows=[triage])]
        view = await incidents.read_incident(db, tenant_id=TENANT, incident_id=fixtures.INCIDENT)
        self.assertEqual(view.first_seen, first.event_time)
        self.assertEqual(view.updated_at, NOW)
        self.assertEqual(view.source_updated_at, triage[1].ts)
        self.assertEqual(view.tactic_counts, {"execution": 2, "persistence": 1})
        self.assertEqual(len([o for o in view.object_links if o["value"] == "shared.test"]), 2)
        self.assertEqual(view.members[0].triage.confidence, .91)
        self.assertEqual(view.members[0].source_alert_id, "connector-record")
        relation = {"cases": [{"case_id": str(UUID(int=i)), "member_ids": [str(first.id)]} for i in (90, 91)],
                    "cases_truncated": False, "items": [{"started_at": NOW + timedelta(days=1), "completed_at": None}]}
        with patch.object(related, "read_related", AsyncMock(return_value=relation)):
            attached = await related.attach_related(db, view)
        self.assertEqual(attached.updated_at, NOW)
        self.assertEqual(attached.source_updated_at, NOW + timedelta(days=1))
        self.assertEqual(attached.members[0].case_ids, [UUID(int=90), UUID(int=91)])
        self.assertEqual(attached.members[1].case_ids, [])
        self.assertIsNone(view.members[0].case_ids)

    async def test_entity_only_asset_keys_and_matching_evidence(self):
        alert = record()
        alert.affected_hosts = []
        expected = {"status": "matched", "rows": [{"id": str(UUID(int=70)), "tags": ["critical"],
                    "correlations": [{"match_field": "hostname", "confidence": .9}]}], "truncated": False}
        with patch.object(processing, "_read", AsyncMock(return_value=expected)) as read:
            asset = await processing.read_asset_context(object(), alert)
        self.assertEqual(read.call_args.args[2]["hosts"], ["host-01"])
        self.assertEqual(read.call_args.args[2]["tenant_id"], str(TENANT))
        self.assertIn("a.tags", read.call_args.args[1])
        self.assertIn("c.tenant_id=a.tenant_id", read.call_args.args[1])
        self.assertEqual(asset["rows"][0]["tags"], ["critical"])
        db = AsyncMock()
        db.execute.side_effect = [result(rows=[alert]), result(rows=[])]
        with patch.object(processing, "read_asset_context", AsyncMock(return_value=asset)):
            view = await incidents.read_incident(db, tenant_id=TENANT, incident_id=fixtures.INCIDENT, include_assets=True)
        self.assertEqual(view.members[0].assets, asset)
        self.assertEqual(view.asset_coverage["read_member_ids"], [str(alert.id)])

    async def test_case_freezes_detection_and_pairs_score_with_same_triage(self):
        alert = record()
        alert.disposition = "benign_true_positive"
        event = fixtures.verdict(1, "Previous triage", decision="true_positive")[1]
        event.payload.update(confidence=.93, findings=["saved finding"], proposed_actions=["verify source"])
        case = Case(id=UUID(int=30), tenant_id=TENANT, title="Case", alert_ids=[alert.id])
        request = analysis.CaseAnalysisRequest(operation_key=UUID(int=40), start=NOW-timedelta(hours=1), end=NOW+timedelta(hours=1))
        async def context():
            db = AsyncMock()
            db.execute.side_effect = [result(one=case), result(rows=[alert]), result(rows=[(str(alert.id), event)])]
            return await analysis.case_context(db, TENANT, case.id, request)
        saved = await context()
        a, t = saved["evidence"]
        self.assertEqual(a["data"]["detection"]["rule_name"], "Stored rule")
        self.assertEqual(t["data"]["verdict"], "true_positive")
        self.assertEqual(t["data"]["confidence"], .93)
        self.assertEqual(t["data"]["run_id"], str(event.run_id))
        self.assertEqual(a["data"]["disposition"], "benign_true_positive")
        self.assertIn({"type": "hash", "value": "hash-1"}, a["data"]["entities"])
        original = analysis.encoded(saved)
        visible = analysis.model_context(saved)
        self.assertEqual(visible["evidence"][1]["data"]["confidence"], .93)
        self.assertEqual(analysis.encoded(saved), original)
        alert.confidence_rationale.append({"factor": "later"})
        event.payload["findings"].append("later analysis")
        self.assertEqual(analysis.encoded(saved), original)
        alert.rule_name = "Changed rule"
        self.assertNotEqual(analysis.digest(await context()), analysis.digest(saved))
        a["data"]["detection"]["rule_name"] = "x" * 5000
        bounded = analysis.model_context(saved)
        self.assertEqual(bounded["evidence"][0]["data"]["omitted_projection_fields"]["detection"], "field_projection_budget")
        a["data"]["detection"]["rule_name"] = '{"class_uid":1007}'
        guarded = analysis.model_context(saved)
        self.assertEqual(guarded["evidence"][0]["data"]["omitted_projection_fields"]["detection"], "llm_input_contract")

    async def test_graph_ignores_legacy_single_case_pointer_and_reads_iocs(self):
        alert = {"id": UUID(int=1), "case_id": UUID(int=30), "iocs": [{"type": "domain", "value": "stored.test"}]}
        self.assertEqual(graph._values(alert, "affected_ips", {"domain"}), ["stored.test"])
        # A stale single pointer does not authorize including a nonmember.
        with patch.object(graph, "_rows", AsyncMock(side_effect=[[alert], [{"id": UUID(int=30), "alert_ids": [UUID(int=2)]}]])):
            with self.assertRaisesRegex(HTTPException, "alert_not_linked_to_case"):
                await graph._anchor(object(), TENANT, case_id=UUID(int=30), alert_id=UUID(int=1))
        with patch.object(graph, "_rows", AsyncMock(side_effect=[[{"id": UUID(int=30), "alert_ids": []}], []])) as rows:
            scope = await graph._anchor(object(), TENANT, case_id=UUID(int=30))
        self.assertEqual(scope["alerts"], [])
        self.assertNotIn("OR case_id", rows.call_args.args[1])

    async def test_asset_projection_bound_keeps_omissions_and_failures_explicit(self):
        alerts = [record(i) for i in range(1, 22)]
        db = AsyncMock()
        db.execute.side_effect = [result(rows=alerts), result(rows=[])]
        unavailable = {"status": "unavailable", "rows": [], "truncated": False, "error_type": "TimeoutError"}
        with patch.object(processing, "read_asset_context", AsyncMock(return_value=unavailable)) as read:
            view = await incidents.read_incident(db, tenant_id=TENANT, incident_id=fixtures.INCIDENT, include_assets=True)
        self.assertEqual(read.await_count, 20)
        self.assertEqual(view.members[0].assets["status"], "unavailable")
        self.assertIsNone(view.members[-1].assets)
        self.assertEqual(view.asset_coverage["omitted_member_ids"], [str(alerts[-1].id)])
