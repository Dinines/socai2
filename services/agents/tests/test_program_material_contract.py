"""b2.1 program material integrity, independent of model projection eligibility."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import sys
import unittest
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.program_material import (ProgramMaterial, build_program_material, checked_program_material,
    MATERIAL_SCHEMA, MATERIAL_POLICY_REF)
from app.investigation_v2.analysis_adoption import checked_view
from app.investigation_v2.evidence_view import EvidenceView, EvidenceProjectionBlocked, build_evidence_view
from app.investigation_v2.execution_store import canonical_json, content_hash, scope_snapshot
import test_alert_projection_contract as a
import test_evidence_view_contract as e


class ProgramMaterialTests(unittest.TestCase):
    def build(self, payload=None, context=None, **changes):
        payload = e.query() if payload is None else payload
        context = a.project().context if context is None else context
        return build_program_material(context, payload, e.material(payload), **{**dict(revision=1), **changes})

    def rehash(self, doc):
        doc["snapshot_ref"] = "program-material:" + content_hash(canonical_json({k: v for k, v in doc.items() if k != "snapshot_ref"}))

    def test_full_alert_program_material_references_all_frozen_bytes_without_model_eligibility(self):
        request = a.project();context = request.context;payload = e.query()
        with self.assertRaises(EvidenceProjectionBlocked): build_evidence_view(context, payload, e.material(payload), 1)
        material = self.build(payload, context);doc = checked_program_material(context, material, current_snapshot_ref=material.snapshot_ref)
        self.assertEqual((doc["schema"], doc["material_policy_ref"]), (MATERIAL_SCHEMA, MATERIAL_POLICY_REF))
        full = context.member_snapshot.selected[0].data_only_text;digest = content_hash(full)
        self.assertEqual(doc["alert"]["data_only_source"], {"ref": "scope-source:"+digest, "sha256": digest, "size_bytes": 1299})
        self.assertEqual(doc["scope_sources"], [doc["alert"]["data_only_source"]])
        self.assertNotIn("真实保留", material.canonical_doc)
        self.assertEqual(doc["model_projection"], {"status": "not_requested", "eligible_for_model": False})
        self.assertEqual(doc["free_text_semantics"], "not_assessed_by_program_material")
        self.assertNotIn("model_view", doc);self.assertNotIn("facts", doc);self.assertNotIn("scope_readiness", doc)
        self.assertEqual(len(material.records), 1)

    def test_new_type_cannot_be_consumed_as_an_old_evidence_view(self):
        context = a.project().context;material = self.build(context=context)
        self.assertNotIsInstance(material, EvidenceView);self.assertFalse(hasattr(material, "model_view"))
        with self.assertRaisesRegex(ValueError, "scope_and_view"): checked_view(context, material)
        with self.assertRaisesRegex(ValueError, "program_scope_and_material"):
            checked_program_material(context, e.view(), current_snapshot_ref=material.snapshot_ref)

    def test_complete_escaped_model_view_over_limit_does_not_block_program_material(self):
        payload = e.query([e.record('"' * 512, event_id=UUID(int=i+1)) for i in range(10)])
        context = e.scope()
        with self.assertRaises(EvidenceProjectionBlocked) as blocked:
            build_evidence_view(context, payload, e.material(payload), 1)
        self.assertEqual(blocked.exception.receipt["failure"]["stage"], "complete_model_view")
        material = self.build(payload, context)
        self.assertEqual(len(material.records), 10)
        self.assertTrue(all(len(record["data_only_excerpt"]) == 512 for record in material.records))
        self.assertIn('"' * 512, material.records[0]["data_only_excerpt"])
        self.assertEqual(material.query["coverage"]["gaps"], sorted({"bounded_query_only", "no_global_identity_completeness",
            "no_authorization_source", "no_behavior_corroboration"}))

    def test_old_normal_and_blocked_model_paths_keep_exact_documents_and_limits(self):
        payload = e.query();context = e.scope();before = e.view(payload, context).canonical_doc
        self.build(payload, context)
        self.assertEqual(e.view(payload, context).canonical_doc, before)
        context = a.project().context
        for _ in range(2):
            with self.assertRaises(EvidenceProjectionBlocked) as caught: build_evidence_view(context, payload, e.material(payload), 1)
            self.assertEqual(caught.exception.receipt["failure"]["limit"], 512)

    def test_necessary_material_hash_tenant_and_source_run_checks_still_refuse(self):
        context = a.project().context;payload = e.query()
        for ref in (replace(e.material(payload), sha256="0"*64), replace(e.material(payload), tenant_id=UUID(int=99)),
                    replace(e.material(payload), source_run_id=UUID(int=99))):
            with self.subTest(ref=ref), self.assertRaises(ValueError): build_program_material(context, payload, ref, 1)
        for field, value in (("tenant_id", str(UUID(int=99))), ("member_id", str(UUID(int=99))), ("policy_ref", "other.v1")):
            changed = deepcopy(payload);changed["caller_receipt"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.build(changed)

    def test_required_scope_receipt_source_version_and_body_integrity_are_not_projection_gaps(self):
        payload = e.query()
        changes = []
        row = deepcopy(payload);row["query_receipt"]["parameters"]["dest_ip"] = "198.51.100.99";changes.append(row)
        row = deepcopy(payload);row["rows"][0]["content_hash"] = "0"*64;changes.append(row)
        row = deepcopy(payload);row["rows"][0]["raw_payload"]["text"] += " ";changes.append(row)
        row = deepcopy(payload);row["rows"][0]["dst_port"] = True;changes.append(row)
        row = deepcopy(payload);row["query_receipt"]["returned_count"] = 9;changes.append(row)
        row = deepcopy(payload);row.pop("query_receipt");changes.append(row)
        for number, changed in enumerate(changes):
            with self.subTest(number=number), self.assertRaises(ValueError) as raised: self.build(changed)
            self.assertNotIsInstance(raised.exception, EvidenceProjectionBlocked)

    def test_conflict_and_missing_versions_are_retained_without_implicit_resolution(self):
        first, second = e.record(), e.record(outcome="failure")
        versions = sorted([first["content_hash"], second["content_hash"]])
        for row in (first, second): row.update(identity_state="conflict", conflict_version_hashes=versions)
        material = self.build(e.query([first, second]))
        self.assertEqual(sorted(record["version"] for record in material.records), versions)
        self.assertTrue(all(record["conflict"] for record in material.records))
        self.assertIn("source_identity_conflict", material.query["coverage"]["gaps"])
        incomplete = self.build(e.query([first], truncated=True))
        self.assertEqual(incomplete.records[0]["missing_version_hashes"], [second["content_hash"]])
        self.assertIn("undelivered_conflict_versions", incomplete.query["coverage"]["gaps"])
        with self.assertRaises(ValueError): self.build(e.query([first], truncated=False))

    def test_source_body_truncation_and_excerpt_gaps_keep_existing_meaning(self):
        row = e.record();row["raw_payload"].update(text=row["raw_payload"]["text"][:20], retained_bytes=20, truncated=True)
        material = self.build(e.query([row]))
        self.assertIn("source_body_truncated", material.query["coverage"]["gaps"])
        self.assertIn("source_excerpt_not_extractable", material.query["coverage"]["gaps"])
        material = self.build(e.query([e.record("x"*513)]))
        self.assertIn("source_excerpt_over_limit", material.query["coverage"]["gaps"])
        self.assertEqual(material.records[0]["excerpt_gaps"], ["over_limit"])

    def test_empty_failed_unknown_execution_and_subwindow_are_not_claimed_complete(self):
        empty = self.build(e.query(status="empty"));self.assertEqual((empty.query["status"], empty.query["executed"], empty.query["returned_count"]), ("empty", True, 0))
        for status in ("unavailable", "error", "rejected"):
            material = self.build(e.query(status=status))
            self.assertEqual(material.records, []);self.assertEqual(material.query["execution_state"], "query_attempted")
            self.assertIsNone(material.query["executed"]);self.assertIn("source_"+status, material.query["coverage"]["gaps"])
        payload = {"tool": "activity_records", "status": "error", "caller_receipt": {"http_attempted": True}}
        self.assertEqual(self.build(payload).query["execution_state"], "unknown")
        payload = e.query()
        for params in (payload["query_receipt"]["parameters"], payload["caller_receipt"]["request_parameters"]):
            params.update(start="2026-10-23T10:01:00.000000+00:00", end="2026-10-23T10:01:00.000001+00:00")
        material = self.build(payload)
        self.assertEqual(material.query["coverage"]["window"]["end"], "2026-10-23T10:01:00.000001+00:00")
        self.assertNotIn("scope_readiness", json.loads(material.canonical_doc))

    def test_material_self_hash_version_revision_scope_and_canonical_types_are_checked(self):
        context = a.project().context;material = self.build(context=context);original = json.loads(material.canonical_doc)
        for field, value in (("schema", "other.v1"), ("material_policy_ref", "other.v1"), ("revision", True),
                             ("snapshot_ref", "program-material:"+"0"*64), ("unexpected", "extra")):
            doc = deepcopy(original);doc[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): ProgramMaterial(canonical_json(doc))
        doc = deepcopy(original);doc["scope_hash"] = "0"*64;self.rehash(doc);forged = ProgramMaterial(canonical_json(doc))
        with self.assertRaises(ValueError): checked_program_material(context, forged, current_snapshot_ref=forged.snapshot_ref)
        for kind in ("scope_ref", "alert_ref", "eligible_boolean"):
            doc = deepcopy(original)
            if kind == "scope_ref": doc["scope_sources"][0]["size_bytes"] += 1
            if kind == "alert_ref": doc["alert"]["data_only_source"]["sha256"] = "0"*64
            if kind == "eligible_boolean": doc["model_projection"]["eligible_for_model"] = 0
            self.rehash(doc)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                checked_program_material(context, ProgramMaterial(canonical_json(doc)), current_snapshot_ref=doc["snapshot_ref"])
        with self.assertRaises(ValueError): checked_program_material(context, material, current_snapshot_ref="program-material:"+"0"*64)

    def test_events_index_and_material_claims_remain_cross_linked(self):
        original = json.loads(self.build().canonical_doc)
        for kind in ("record", "query_ref", "material"):
            doc = deepcopy(original)
            if kind == "record": doc["records"][0]["fields"]["outcome"] = "success"
            if kind == "query_ref": doc["query"]["ref"] = "query:"+str(UUID(int=99))
            if kind == "material": doc["material"]["artifact_ref"] = "urn:uuid:"+str(UUID(int=99))
            self.rehash(doc)
            with self.subTest(kind=kind), self.assertRaises(ValueError): ProgramMaterial(canonical_json(doc))

    def test_input_immutability_and_detached_outputs(self):
        context = a.project().context;payload = e.query();before = deepcopy(payload)
        material = self.build(payload, context);self.assertEqual(payload, before)
        material.records.clear();material.index.clear();material.alert.clear();material.query.clear()
        self.assertEqual(material.canonical_doc, self.build(payload, context).canonical_doc)
        with self.assertRaises(FrozenInstanceError): material.canonical_doc = "changed"
        self.assertEqual(list(scope_snapshot(context)[1].values()), [context.member_snapshot.selected[0].data_only_text])


if __name__ == "__main__": unittest.main()
