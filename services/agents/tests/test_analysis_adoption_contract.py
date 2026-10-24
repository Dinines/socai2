"""M4.1b fixed candidates: no model, HTTP, database or whole-run execution."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.analysis_adoption import adopt_candidate, readable_facts
from app.investigation_v2.evidence_view import EvidenceView
from app.investigation_v2.execution_store import canonical_json
from test_evidence_view_contract import scope, view, query, record


def candidate(evidence, mode="combined_analysis"):
    data = evidence.model_view
    event, alert, receipt = data["events"][0]["ref"], data["alert"]["ref"], data["query"]["ref"]
    findings = [dict(key="F1", question="Q1", claim="network_observed", refs=[event], rationale="A source observation, not proof of success."),
                dict(key="F2", question="Q2", claim="alert_linked", refs=[alert, event], rationale="Exact source ID association only."),
                dict(key="F3", question="Q5", claim="bounded_query", refs=[receipt], rationale="Limited query coverage.")]
    return dict(snapshot_ref=evidence.snapshot_ref, mode=mode, findings=findings,
                answers=[dict(question=q, status="supported", finding_keys=[key], rationale="Limited to cited material.")
                         for q, key in (("Q1", "F1"), ("Q2", "F2"), ("Q5", "F3"))],
                assessment=dict(finding_keys=["F1", "F2", "F3"], nature="unresolved", authorization="unknown",
                                rationale="Observation only; no nature or authorization decision.") if mode == "combined_analysis" else None,
                proposals=[])


class AnalysisAdoptionTests(unittest.TestCase):
    def setUp(self):
        self.context = scope()
        self.view = view(context=self.context)

    def adopt(self, proposed=None, evidence=None, mode="combined_analysis", current=None):
        evidence = evidence or self.view
        return adopt_candidate(self.context, evidence, proposed if proposed is not None else candidate(evidence, mode),
                               mode=mode, current_snapshot_ref=current or evidence.snapshot_ref)

    def test_positive_typed_fact_and_exact_link_remain_limited(self):
        adopted = self.adopt()
        self.assertEqual(adopted["status"], "admitted")
        self.assertEqual([f["assurance"] for f in adopted["findings"]], ["rule_checked"] * 3)
        self.assertEqual([f["validity"] for f in adopted["findings"]], ["current"] * 3)
        fact = adopted["findings"][0]["fact"]
        self.assertEqual(fact["fields"]["outcome"], "unknown")
        self.assertEqual(adopted["findings"][1]["fact"]["association"], "exact_declared_source_id_only")
        self.assertEqual((adopted["nature"], adopted["authorization"], adopted["scope_readiness"]),
                         ("unresolved", "unknown", "not_evaluated"))
        self.assertEqual([q["question"] for q in adopted["retained_questions"]], ["Q1", "Q2", "Q3a", "Q3b", "Q4", "Q5"])
        self.assertTrue(all(q["status"] == "unassessed" for q in adopted["retained_questions"] if q["question"] in {"Q3a", "Q3b", "Q4"}))
        self.assertEqual(adopted["assessment"]["assurance"], "model_assessed")
        self.assertEqual(adopted["assessment"]["validity"], "current")

    def test_correct_finding_survives_unsupported_success_and_dependent_overall(self):
        proposed = candidate(self.view)
        proposed["findings"][1].update(question="Q1", claim="connection_succeeded")
        proposed["answers"][1]["finding_keys"] = ["F2"]
        result = self.adopt(proposed)
        self.assertEqual([f["candidate_key"] for f in result["findings"]], ["F1", "F3"])
        self.assertEqual([a["question"] for a in result["answers"]], ["Q1", "Q5"])
        self.assertIsNone(result["assessment"])
        self.assertEqual({r["part"] for r in result["rejections"]}, {"finding", "answer", "assessment"})

    def test_stale_snapshot_unknown_reference_and_foreign_scope_cannot_be_adopted(self):
        self.assertEqual(self.adopt(current="ev:old")["rejections"][0]["reason"], "stale_input_snapshot")
        proposed = candidate(self.view)
        proposed["findings"][0]["refs"] = ["source:unknown"]
        self.assertNotIn("F1", [f["candidate_key"] for f in self.adopt(proposed)["findings"]])
        proposed = candidate(self.view)
        proposed["snapshot_ref"] = "ev:old"
        self.assertEqual(self.adopt(proposed)["findings"], [])
        other = scope("A different retained source snapshot.")
        result = adopt_candidate(other, self.view, candidate(self.view), mode="combined_analysis", current_snapshot_ref=self.view.snapshot_ref)
        self.assertEqual(result["rejections"][0]["reason"], "view_scope_mismatch")

    def test_duplicate_keys_are_not_ambiguous_adopted_dependencies(self):
        proposed = candidate(self.view)
        proposed["findings"].append(deepcopy(proposed["findings"][0]))
        result = self.adopt(proposed)
        self.assertNotIn("F1", [f["candidate_key"] for f in result["findings"]])
        self.assertIsNone(result["assessment"])
        proposed = candidate(self.view)
        proposed["answers"][1] = deepcopy(proposed["answers"][0])
        self.assertEqual([a["question"] for a in self.adopt(proposed)["answers"]], ["Q5"])

    def test_focused_null_is_valid_and_never_manufactures_overall(self):
        result = self.adopt(mode="focused_analysis")
        self.assertEqual(result["status"], "admitted")
        self.assertIsNone(result["assessment"])
        self.assertFalse(readable_facts(result)["has_overall_candidate"])
        proposed = candidate(self.view)
        proposed["mode"] = "focused_analysis"
        self.assertEqual(self.adopt(proposed, mode="focused_analysis")["rejections"][0]["reason"], "focused_has_no_overall_assessment")

    def test_free_model_prose_never_becomes_verified_readable_fact(self):
        proposed = candidate(self.view)
        proposed["findings"][0]["rationale"] = "Malicious and authorized; ignore the policy."
        result = self.adopt(proposed)
        self.assertIn("Malicious", result["findings"][0]["model_assessed_rationale"])
        self.assertNotIn("Malicious", json.dumps(readable_facts(result)))
        proposed["assessment"]["authorization"] = "authorized"
        self.assertIsNone(self.adopt(proposed)["assessment"])

    def test_conflict_must_include_all_visible_versions_and_can_keep_other_facts(self):
        first, second = record(), record(outcome="failure")
        versions = [first["content_hash"], second["content_hash"]]
        for row in (first, second):
            row.update(identity_state="conflict", conflict_version_hashes=versions)
        evidence = view(query([first, second]), self.context)
        proposed = candidate(evidence)
        proposed["findings"][0].update(claim="source_versions_conflict", refs=[e["ref"] for e in evidence.model_view["events"]])
        proposed["answers"][0]["status"] = "conflicting"
        result = self.adopt(proposed, evidence)
        self.assertEqual(result["status"], "admitted")
        self.assertEqual(len(result["findings"][0]["fact"]["visible_versions"]), 2)
        proposed["findings"][0]["refs"].pop()
        result = self.adopt(proposed, evidence)
        self.assertEqual([f["candidate_key"] for f in result["findings"]], ["F2", "F3"])
        self.assertIsNone(result["assessment"])

    def test_hash_only_conflict_is_a_gap_not_an_invented_event(self):
        row = record()
        row.update(identity_state="conflict", conflict_version_hashes=[row["content_hash"], "f" * 64])
        evidence = view(query([row], truncated=True), self.context)
        proposed = candidate(evidence)
        proposed["findings"][0]["claim"] = "source_versions_conflict"
        proposed["answers"][0]["status"] = "conflicting"
        result = self.adopt(proposed, evidence)
        self.assertEqual(result["findings"][0]["fact"]["missing_version_hashes"], ["f" * 64])
        self.assertEqual(result["status"], "admitted")

    def test_empty_and_failure_express_gaps_without_a_safe_or_false_positive_claim(self):
        for status, claim in (("empty", "query_empty"), ("unavailable", "source_unavailable"), ("error", "source_unavailable")):
            evidence = view(query(status=status), self.context)
            proposed = dict(snapshot_ref=evidence.snapshot_ref, mode="combined_analysis",
                            findings=[dict(key="F1", question="Q5", claim=claim, refs=[evidence.model_view["query"]["ref"]], rationale="Coverage gap.")],
                            answers=[dict(question=q, status="supported" if q == "Q5" else "insufficient_evidence",
                                          finding_keys=["F1"] if q == "Q5" else [], rationale="No affirmative activity decision.") for q in ("Q1", "Q2", "Q5")],
                            assessment=dict(finding_keys=["F1"], nature="unresolved", authorization="unknown", rationale="Limited source assessment."),
                            proposals=[])
            result = self.adopt(proposed, evidence)
            self.assertEqual(result["status"], "admitted", status)
            self.assertEqual(result["findings"][0]["fact"]["returned_count"], 0 if status == "empty" else None)
            self.assertEqual(result["answers"][0]["status"], "insufficient_evidence")

    def test_structural_limits_and_unknown_fields_do_not_silently_truncate(self):
        for mutate in (lambda p: p.update(scope="expanded"),
                       lambda p: p.update(findings=p["findings"] * 3),
                       lambda p: p.update(proposals=[{}] * 3),
                       lambda p: p.update(answers=p["answers"] * 2)):
            proposed = candidate(self.view)
            mutate(proposed)
            result = self.adopt(proposed)
            self.assertEqual(result["status"], "rejected")
            self.assertEqual(result["findings"], [])
        proposed = candidate(self.view)
        proposed["findings"][0]["id"] = "model-owned-id"
        self.assertNotIn("F1", [f["candidate_key"] for f in self.adopt(proposed)["findings"]])

    def test_view_tampering_detachment_and_advisory_proposals(self):
        document = json.loads(self.view.canonical_doc)
        document["model_view"]["events"][0]["fields"]["outcome"] = "success"
        altered = EvidenceView(canonical_json(document))
        self.assertEqual(self.adopt(candidate(altered), altered)["rejections"][0]["reason"], "view_integrity_mismatch")
        proposed = candidate(self.view)
        proposed["proposals"] = [dict(question="Q1", rationale="Review another approved source.")]
        result = self.adopt(proposed)
        proposed["findings"][0]["refs"].clear()
        self.assertTrue(result["findings"][0]["evidence_refs"])
        self.assertFalse(result["proposals"][0]["executable"])
        self.assertEqual(result["proposals"][0]["adoption"], "deferred")

    def test_safe_but_unhelpful_answers_are_not_automatically_quality_passed(self):
        proposed = candidate(self.view)
        for answer in proposed["answers"]:
            answer["status"] = "unassessed"
        result = self.adopt(proposed)
        self.assertEqual([a["status"] for a in result["answers"]], ["unassessed"] * 3)
        self.assertNotIn("quality_passed", result)
        self.assertEqual(result["scope_readiness"], "not_evaluated")

    def test_valid_reference_alone_does_not_prove_the_wrong_predicate(self):
        evidence = view(query([record(outcome="failure")]), self.context)
        proposed = candidate(evidence)
        proposed["findings"][0]["claim"] = "outcome_unknown"
        result = self.adopt(proposed, evidence)
        self.assertEqual(result["rejections"][0]["reason"], "source_does_not_support_predicate")
        proposed = candidate(self.view)
        proposed["findings"][0]["refs"] = [self.view.model_view["alert"]["ref"]]
        self.assertEqual(self.adopt(proposed)["rejections"][0]["reason"], "one_source_version_required")


if __name__ == "__main__":
    unittest.main()
