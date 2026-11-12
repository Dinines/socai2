"""Direct card/scope/model-boundary checks; not real model quality evidence."""
import copy
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import patch
from uuid import UUID

import httpx
from app.socai2.baseline_enrichment import citation_roles
from app.socai2.baseline_optional_sources import SourceUnavailable
from app.socai2.case_source_scope import query_scope
from app.socai2.incident_model_boundary import query_items
from app.socai2.knowledge_config import Profile, selectors
from app.socai2.knowledge_history import (
    PURPOSE,
    card_from,
    document_id,
    import_cards,
    in_scope,
    index_payload,
    retrieval_record,
    serialize,
)
from app.socai2.knowledge_vectors import Vectors

ROOT = Path(__file__).resolve().parents[3]
TENANT, AID, MID, TID, FID = [UUID(int=n) for n in range(1, 6)]


def profile():
    value = json.loads((ROOT / "deploy/local-investigation/knowledge-profile.json").read_text())
    value["vector"]["api_key_file"] = None
    return Profile.model_validate(value)


def source():
    assessment = {"alert_id": str(AID), "input_material_id": str(MID), "rationale": "原文，没有查询不代表查空。",
                  "verdict": "needs_review", "recommendations": [], "actor": {"type": "user"}}
    return {"alert": {"id": str(AID), "title": "Recorded process", "event_time": "2026-11-01T00:00:00+00:00",
                      "latest_material_id": str(MID), "latest_triage_id": str(TID), "latest_feedback_id": str(FID)},
            "material": {"id": str(MID), "revision": 1, "sha256": "a" * 64, "material_state": "complete",
                         "detection": {"rule_name": "source label"}, "ocsf_json": {"process": {"count": 0, "allowed": False, "args": []}}},
            "triage": {**assessment, "id": str(TID), "kind": "triage"},
            "feedback": {**assessment, "id": str(FID), "kind": "human_feedback"}, "objects": []}


def history_key(p):
    context = SimpleNamespace(alerts={str(UUID(int=20)): SimpleNamespace(alert={"title": "process", "source_namespace": "lab"})},
                              scope=SimpleNamespace(window_start=datetime(2026, 11, 10, tzinfo=UTC)))
    materials = {aid: {"ocsf_json": {"process": {"name": "example"}}} for aid in context.alerts}
    return next(k for k in selectors(context, materials, p) if k["purpose"] == PURPOSE)


class Cards(TestCase):
    def test_only_aligned_saved_judgment_is_eligible_without_rewriting_other_statements(self):
        row, p = source(), profile()
        row["triage"]["input_material_id"] = str(UUID(int=99))
        card = card_from(row, p)
        self.assertEqual(card["triage"]["rationale"], row["triage"]["rationale"])
        self.assertEqual(card["material_alignment"]["triage"], "different_material")
        row["feedback"] = None
        with self.assertRaisesRegex(SourceUnavailable, "history_aligned_usable_assessment_missing"):
            card_from(row, p)
        row["triage"].update(input_material_id=str(MID), rationale=None)
        with self.assertRaisesRegex(SourceUnavailable, "history_aligned_usable_assessment_missing"):
            card_from(row, p)
        row["triage"].update(input_material_id=str(MID), rationale="saved judgment", source_run_id=str(UUID(int=88)))
        row["triage_run_state"] = "failed"
        with self.assertRaisesRegex(SourceUnavailable, "history_aligned_usable_assessment_missing"):
            card_from(row, p)

    def test_card_preserves_original_roles_values_and_source_versions(self):
        row, p = source(), profile()
        card = card_from(row, p)
        self.assertEqual(card["triage"]["rationale"], row["triage"]["rationale"])
        self.assertEqual(card["observations"][0]["value"], {"count": 0, "allowed": False, "args": []})
        self.assertEqual(card["verification"], "not_independently_verified")
        first = document_id(TENANT, card)
        self.assertEqual(first, document_id(TENANT, card_from(copy.deepcopy(row), p)))
        row["material"]["revision"] += 1
        self.assertNotEqual(first, document_id(TENANT, card_from(row, p)))

    def test_missing_history_or_scope_does_not_invent_a_card_or_query(self):
        p = profile()
        for value, code in [("material", "history_complete_material_missing"), ("event_time", "history_event_time_missing"),
                            ("assessments", "history_assessment_missing")]:
            row = source()
            if value == "material":
                row[value] = None
            elif value == "event_time":
                row["alert"][value] = None
            else:
                row["triage"] = row["feedback"] = None
            with self.assertRaisesRegex(SourceUnavailable, code):
                card_from(row, p)
        ctx = SimpleNamespace(alerts={"a": SimpleNamespace(alert={"title": "process", "source_namespace": "lab"})})
        self.assertNotIn(PURPOSE, [k["purpose"] for k in selectors(ctx, {}, p)])

    def test_historical_fields_keep_external_subject_and_separate_citations(self):
        card = card_from(source(), profile())
        record = {"id": "doc", "content": serialize(card), "history": copy.deepcopy(card),
                  "triage": card["triage"], "feedback": card["feedback"]}
        record["history"].pop("triage")
        record["history"].pop("feedback")
        body = {"tool_name": "knowledge", "state": "completed", "rows": [{"purpose": PURPOSE, "record_id": "doc", "record": record}],
                "returned_rows": 1, "truncated": False, "actual_args": {"scope": {"alert_ids": ["current"]}}}
        roles = citation_roles(body)
        self.assertEqual(list(roles.values()), ["source_label", "prior_analysis", "human_statement"])
        for path in roles:
            scope = query_scope(body, path, ["current"], ["current"])
            self.assertEqual(scope["alert_ids"], [])
            self.assertEqual(scope["record_alert_ids"], [str(AID)])
        cfg = {"query_receipt_fields": ["state", "returned_rows"], "query_scope_backend_fields": [],
               "query_selector_backend_fields": [], "query_envelope_backend_fields": [], "query_record_backend_fields": [],
               "container_rules": {"$.members.*.triage": {"omit": []}, "$.members.*.feedback": {"omit": []}}}
        items = list(query_items(None, {"id": str(TENANT), "content_json": body}, cfg))
        root = items[1][2]["record"]
        self.assertNotIn("content", root)
        self.assertNotIn("triage", root)
        self.assertEqual(items[2][2]["rationale"], card["triage"]["rationale"])


class HistoryIO(IsolatedAsyncioTestCase):
    async def test_import_reuses_identity_and_index_checks_actual_source(self):
        p, row, writes = profile(), source(), []
        class DB:
            async def execute(self, statement, params):
                if str(statement).startswith("SELECT"):
                    return SimpleNamespace(mappings=lambda: [row])
                writes.append(params)
            async def commit(self):
                pass
        db = DB()
        one = await import_cards(db, TENANT, [AID], "test", p)
        two = await import_cards(db, TENANT, [AID], "test", p)
        self.assertEqual(one, two)
        blocked = await import_cards(db, TENANT, [AID], "test", p, expected_hashes={str(AID): "changed"})
        self.assertEqual(blocked["cards"][0]["reason"], "history_sync_source_changed")
        self.assertEqual(len(writes), 2)
        doc = {"id": writes[0]["id"], "tenant_id": TENANT, "content": writes[0]["content"], "chunk_total": 1, "chunk_index": 0}
        indexed = await index_payload(db, TENANT, doc, p)
        self.assertEqual(indexed["source_alert_id"], str(AID))
        current = await retrieval_record(db, TENANT, doc, p, history_key(p)["filters"])
        self.assertEqual(current["source_version_state"], "current")
        row["triage"]["rationale"] = "changed"
        superseded = await retrieval_record(db, TENANT, doc, p, history_key(p)["filters"])
        self.assertEqual(superseded["source_version_state"], "superseded")
        with self.assertRaisesRegex(SourceUnavailable, "history_card_source_changed_or_mismatched"):
            await index_payload(db, TENANT, doc, p)

    async def test_vector_filter_and_readback_exclude_current_and_out_of_window_alerts(self):
        p, requests = profile(), []
        key = history_key(p)
        def respond(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={"result": []})
        with patch.dict(os.environ, {"AISOC_AIRGAPPED": "false"}):
            await Vectors(p, transport=httpx.MockTransport(respond)).search(TENANT, key, [1.])
        self.assertEqual(requests[0]["filter"]["must_not"][0]["match"]["any"], key["filters"]["exclude_alert_ids"])
        self.assertTrue(any(c.get("key") == "event_epoch" for c in requests[0]["filter"]["must"]))
        card = card_from(source(), p)
        self.assertTrue(in_scope(card, key["filters"]))
        card["source"]["alert_id"] = key["filters"]["exclude_alert_ids"][0]
        self.assertFalse(in_scope(card, key["filters"]))
        card["source"]["alert_id"] = str(AID)
        card["event"]["event_time"] = key["filters"]["event_before"]
        self.assertFalse(in_scope(card, key["filters"]))
