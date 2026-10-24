"""A3 checked-material projection failures become explicit pure handoffs."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.evidence_view import EvidenceProjectionBlocked, build_evidence_view
from app.investigation_v2.fixed_recon import evaluate_alert_recon
from app.investigation_v2.recon_material import prepare_alert_recon
from test_business_profile_contract import bind, case_context
from test_evidence_view_contract import query, record, scope, material


def many_records(text):
    return query([record(text, event_id=UUID(int=i + 1)) for i in range(10)])


class ReconMaterialContractTests(unittest.TestCase):
    def prepare(self, payload=None, context=None, **kwargs):
        context = context or scope()
        payload = query() if payload is None else payload
        with patch("socket.socket", side_effect=AssertionError("pure material preparation")):
            return prepare_alert_recon(bind(context), payload, material(payload), 1, **kwargs)

    def test_normal_preparation_uses_the_actual_view_and_existing_policy(self):
        context, payload = scope(), query()
        before = deepcopy(payload)
        evidence = build_evidence_view(context, payload, material(payload), 1)
        expected = evaluate_alert_recon(bind(context), evidence, current_snapshot_ref=evidence.snapshot_ref)
        prepared = self.prepare(payload, context)
        self.assertEqual(prepared["schema"], "alert_recon_preparation.v1")
        self.assertEqual(prepared["material_state"], "view_ready")
        self.assertEqual(prepared["evidence_document"], json.loads(evidence.canonical_doc))
        self.assertEqual(prepared["result"], expected)
        self.assertIsNone(prepared["projection_block"])
        self.assertEqual(prepared["persistence_status"], "not_attempted")
        self.assertEqual(payload, before)
        prepared["evidence_document"]["index"].clear()
        self.assertTrue(self.prepare(payload, context)["evidence_document"]["index"])

    def test_escaped_ten_record_projection_keeps_all_versions_and_real_source_state(self):
        for text in ('"' * 512, "\\" * 512):
            with self.subTest(kind=text[0]):
                payload = many_records(text)
                before = deepcopy(payload)
                with self.assertRaises(EvidenceProjectionBlocked) as caught:
                    build_evidence_view(scope(), payload, material(payload), 1)
                prepared = self.prepare(payload)
                block, result = prepared["projection_block"], prepared["result"]
                self.assertEqual(block["failure"]["code"], "complete_model_view_exceeds_byte_limit")
                self.assertGreaterEqual(block["failure"]["observed_bytes"], 12288)
                self.assertIsNone(prepared["evidence_document"])
                self.assertIsNone(prepared["evidence_snapshot_ref"])
                self.assertEqual((result["source_state"], result["source_available"]), ("ok", True))
                self.assertEqual(result["scope_readiness"], "partial")
                self.assertEqual(result["facts"], [])
                self.assertTrue(all(q["status"] == "unassessed" for q in result["questions"]))
                sources = [item for item in block["index"].values() if item["kind"] == "source_event"]
                self.assertEqual(len(sources), 10)
                self.assertEqual({item["version"] for item in sources}, {row["content_hash"] for row in payload["rows"]})
                self.assertTrue(set(block["index"]) <= set(result["held_refs"]))
                self.assertIn(block["material"]["artifact_ref"], result["held_refs"])
                self.assertEqual(payload, before)
                receipt = caught.exception.receipt
                receipt["index"].clear()
                self.assertEqual(len(caught.exception.receipt["index"]), 12)

    def test_ascii_and_multibyte_material_still_build_real_views(self):
        for text in ("x" * 512, "中" * 170):
            with self.subTest(text_bytes=len(text.encode("utf-8"))):
                prepared = self.prepare(many_records(text))
                self.assertEqual(prepared["material_state"], "view_ready")
                self.assertEqual(prepared["result"]["scope_readiness"], "ready")

    def test_long_alert_uses_only_hash_and_size_even_above_projection_document_limit(self):
        for text in ("PRIVATE_ALERT_NOTE_" * 40, "x" * (1024 * 1024 + 1)):
            with self.subTest(size=len(text.encode("utf-8"))):
                prepared = self.prepare(context=scope(text))
                block, result = prepared["projection_block"], prepared["result"]
                self.assertEqual(block["failure"]["stage"], "alert_excerpt")
                alert = next(item for item in block["index"].values() if item["kind"] == "alert_claim")
                self.assertEqual(alert["data_only_sha256"], hashlib.sha256(text.encode()).hexdigest())
                self.assertEqual(alert["data_only_bytes"], len(text.encode()))
                self.assertNotIn(text, json.dumps(prepared, ensure_ascii=False))
                self.assertLess(len(json.dumps(prepared).encode()), 64 * 1024)
                self.assertEqual(result["source_state"], "ok")

    def test_input_contract_diagnostic_and_free_coverage_text_are_not_echoed(self):
        text = '<Event xmlns="http://schemas.microsoft.com/win/">PRIVATE_ALERT_NOTE'
        payload = query()
        payload["query_receipt"]["coverage"] = "PRIVATE_FREE_COVERAGE_TEXT"
        prepared = self.prepare(payload, scope(text))
        self.assertEqual(prepared["projection_block"]["failure"]["code"], "alert_input_contract_rejected")
        rendered = json.dumps(prepared, ensure_ascii=False)
        self.assertNotIn("PRIVATE_ALERT_NOTE", rendered)
        self.assertNotIn("PRIVATE_FREE_COVERAGE_TEXT", rendered)

    def test_required_validation_failures_win_over_long_alert_projection_failure(self):
        context = scope("x" * 513)
        for kind in ("material_hash", "tenant", "source_run", "query_scope", "source_hash", "version", "conflict"):
            payload = query()
            retained = material(payload)
            if kind == "material_hash": retained = replace(retained, sha256="0" * 64)
            elif kind == "tenant": retained = replace(retained, tenant_id=UUID(int=99))
            elif kind == "source_run": retained = replace(retained, source_run_id=UUID(int=99))
            else:
                if kind == "query_scope": payload["query_receipt"]["parameters"]["source_ip"] = "192.0.2.99"
                if kind == "source_hash": payload["rows"][0]["raw_payload"]["sha256"] = "0" * 64
                if kind == "version": payload["rows"][0]["content_hash"] = "0" * 64
                if kind == "conflict": payload["rows"][0]["identity_state"] = "conflict"
                retained = material(payload)
            with self.subTest(kind=kind), self.assertRaises(ValueError) as caught:
                prepare_alert_recon(bind(context), payload, retained, 1)
            self.assertNotIsInstance(caught.exception, EvidenceProjectionBlocked)

    def test_existing_optional_excerpt_gap_keeps_legitimate_program_facts(self):
        prepared = self.prepare(query([record("x" * 513)]))
        self.assertEqual(prepared["material_state"], "view_ready")
        self.assertEqual(len(prepared["result"]["facts"]), 4)
        self.assertEqual(prepared["result"]["scope_readiness"], "partial")
        self.assertIn("source_excerpt_over_limit", prepared["result"]["blocking_gaps"])

    def test_subwindow_and_conflict_metadata_are_not_lost_in_preparation(self):
        payload = query()
        for params in (payload["query_receipt"]["parameters"], payload["caller_receipt"]["request_parameters"]):
            params.update(start="2026-10-23T10:01:00.000000+00:00", end="2026-10-23T10:01:00.000001+00:00")
        prepared = self.prepare(payload)
        self.assertEqual(prepared["result"]["scope_readiness"], "partial")
        self.assertEqual(len(prepared["result"]["facts"]), 4)
        self.assertEqual(len(prepared["result"]["coverage"]["uncovered_windows"]), 2)
        first, second = record(), record(outcome="failure")
        versions = sorted([first["content_hash"], second["content_hash"]])
        for row in (first, second):
            row.update(identity_state="conflict", conflict_version_hashes=versions)
        prepared = self.prepare(query([first, second]), scope("x" * 513))
        sources = [item for item in prepared["projection_block"]["index"].values() if item["kind"] == "source_event"]
        self.assertEqual(sorted(item["version"] for item in sources), versions)
        self.assertTrue(all(item["conflict_version_hashes"] == versions for item in sources))
        self.assertIn("source_identity_conflict", prepared["result"]["coverage_gaps"])
        self.assertEqual(prepared["result"]["facts"], [])

    def test_failed_source_and_observed_unknown_keep_their_real_states(self):
        prepared = self.prepare(query(status="error"), scope("x" * 513), execution_stop="unknown_attempt")
        result = prepared["result"]
        self.assertEqual(result["source_state"], "error")
        self.assertFalse(result["source_available"])
        self.assertEqual(result["execution_state"], "query_attempted")
        self.assertEqual(result["stop_reason"], "unknown_attempt")
        self.assertIsNone(result["coverage"]["covered_window"])
        self.assertIn("execution_unknown_attempt", result["blocking_gaps"])
        self.assertEqual(result["handoff"]["delivery_status"], "required")
        self.assertFalse(result["handoff"]["automatic_query"])
        self.assertFalse(result["handoff"]["automatic_model"])

    def test_stop_enum_profile_and_revision_validation_are_not_projection_gaps(self):
        with self.assertRaisesRegex(ValueError, "unsupported_execution_stop"):
            self.prepare(context=scope("x" * 513), execution_stop="retry_all")
        context, target = case_context()
        with self.assertRaisesRegex(ValueError, "requires_alert_profile"):
            prepare_alert_recon(bind(context, target, profile="case_investigation"), query(), material(query()), 1)
        with self.assertRaisesRegex(ValueError, "positive_view_revision"):
            prepare_alert_recon(bind(scope()), query(), material(query()), 0)


if __name__ == "__main__":
    unittest.main()
