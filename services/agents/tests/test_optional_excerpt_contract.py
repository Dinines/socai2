"""I1 local source-excerpt degradation, actual builder/adopter, no I/O."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import NAMESPACE_URL, uuid5

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.analysis_adoption import adopt_candidate, readable_facts
from test_analysis_adoption_contract import candidate
from test_evidence_view_contract import query, record, scope, source_body, view


class OptionalExcerptContractTests(unittest.TestCase):
    def test_bad_optional_message_keeps_other_records_and_checked_fields(self):
        for message, reason in (("x" * 513, "over_limit"), ("界" * 171, "over_limit"),
                                ({"note": "requires review"}, "unsupported_type"),
                                ('{"class_uid":4001}', "input_contract_rejected")):
            rows = [record(message), record("normal note", event_id=uuid5(NAMESPACE_URL, "normal-control"))]
            with self.subTest(reason=reason), patch("socket.socket", side_effect=AssertionError("no I/O")):
                evidence = view(query(rows))
            self.assertEqual(len(evidence.model_view["events"]), 2)
            bad = next(item for item in evidence.model_view["events"] if item["version"] == rows[0]["content_hash"])
            self.assertEqual(bad["fields"]["action"], "network_connection_observed")
            self.assertEqual(bad["fields"]["outcome"], "unknown")
            self.assertEqual(bad["excerpt_gaps"], [reason])
            self.assertNotIn("data_only_excerpt", bad)
            self.assertIn("source_excerpt_" + reason, evidence.model_view["query"]["coverage"]["gaps"])
            self.assertEqual(evidence.index[bad["ref"]]["retrievals"][0]["bodies"]["raw_payload"]["full_sha256"],
                             rows[0]["raw_payload"]["sha256"])

    def test_unread_optional_counterexample_stays_visible_in_adopted_readable_fact(self):
        text = "This may be a replay simulation; do not infer a real successful connection. " + "x" * 513
        evidence = view(query([record(text)]))
        adopted = adopt_candidate(scope(), evidence, candidate(evidence, "focused_analysis"),
                                  mode="focused_analysis", current_snapshot_ref=evidence.snapshot_ref)
        self.assertEqual(adopted["status"], "admitted")
        readable = readable_facts(adopted)
        self.assertEqual(readable["facts"][0]["excerpt_gaps"], ["over_limit"])
        self.assertIn("source_excerpt_over_limit", readable["facts"][2]["coverage"]["gaps"])
        self.assertEqual((readable["nature"], readable["authorization"]), ("unresolved", "unknown"))
        self.assertNotIn(text, str(evidence.model_view))
        proposed = candidate(evidence, "focused_analysis")
        proposed["findings"][0]["claim"] = "connection_succeeded"
        refused = adopt_candidate(scope(), evidence, proposed, mode="focused_analysis", current_snapshot_ref=evidence.snapshot_ref)
        self.assertNotIn("F1", [item["candidate_key"] for item in refused["findings"]])

    def test_truncated_source_cannot_claim_message_is_fully_read(self):
        row = record("critical counterexample")
        partial = deepcopy(row)
        prefix = '{"message":"different prefix"}'
        # This retained prefix cannot be verified as the full source. Even
        # syntactically complete JSON must not become an authoritative excerpt.
        partial["raw_payload"].update(text=prefix, retained_bytes=len(prefix.encode()), truncated=True)
        evidence = view(query([partial]))
        event = evidence.model_view["events"][0]
        self.assertNotIn("data_only_excerpt", event)
        self.assertEqual(event["excerpt_gaps"], ["not_extractable"])
        self.assertIn("source_body_truncated", evidence.model_view["query"]["coverage"]["gaps"])

    def test_full_same_version_retrieval_restores_excerpt_without_erasing_old_provenance(self):
        full = record("complete checked note")
        partial = deepcopy(full)
        partial["raw_payload"].update(text=full["raw_payload"]["text"][:15], retained_bytes=15, truncated=True)
        for rows in ([full, partial], [partial, full]):
            evidence = view(query(rows))
            event = evidence.model_view["events"][0]
            self.assertEqual(event["data_only_excerpt"], "complete checked note")
            self.assertNotIn("excerpt_gaps", event)
            self.assertEqual(len(evidence.index[event["ref"]]["retrievals"]), 2)
            self.assertIn("source_body_truncated", evidence.model_view["query"]["coverage"]["gaps"])

    def test_untrusted_identity_or_body_hash_is_still_rejected(self):
        for mutate in (lambda row: row.update(content_hash="0" * 64),
                       lambda row: row["raw_payload"].update(text="tampered"),
                       lambda row: row.update(dest_ip="198.51.100.99")):
            payload = query([record("x" * 513)])
            mutate(payload["rows"][0])
            with self.assertRaises(ValueError):
                view(payload)

    def test_nonjson_or_ambiguous_source_body_degrades_after_full_hash_verification(self):
        # Recompute the public complete source projection for these synthetic
        # bodies. This is fixture derivation, not mutation of retained evidence.
        from app.investigation_v2.evidence_view import _FIELDS, _message
        from app.investigation_v2.execution_store import canonical_json, content_hash
        for text, reason in (("not JSON", "not_json"), ('{"message":"one","message":"two"}', "ambiguous_json"),
                             (r'{"message":"\ud800"}', "invalid_unicode"),
                             ('[{"message":"not a supported top-level object"}]', "unsupported_body_shape")):
            row = record()
            row["raw_payload"] = source_body(text)
            projection = {key: row[key] for key in _FIELDS}
            projection.update(namespace=row["namespace"], outcome_provided=row["outcome_provided"])
            for name in ("raw_payload", "ocsf_json"):
                projection[name] = {key: row[name][key] for key in ("sha256", "original_bytes")}
            row["content_hash"] = content_hash(canonical_json(projection))
            evidence = view(query([row, record("normal control", event_id=uuid5(NAMESPACE_URL, "encoding-control"))]))
            self.assertEqual(len(evidence.model_view["events"]), 2)
            event = next(item for item in evidence.model_view["events"] if item["version"] == row["content_hash"])
            self.assertEqual(event["excerpt_gaps"], [reason])
            self.assertNotIn("data_only_excerpt", event)
        # Parser recursion limits vary by runtime; inject this specific parse
        # failure rather than assuming a fixed nesting count always raises.
        with patch("app.investigation_v2.evidence_view.json.loads", side_effect=RecursionError):
            self.assertEqual(_message({"text": "[]", "truncated": False}), (None, "json_nesting_limit"))


if __name__ == "__main__":
    unittest.main()
