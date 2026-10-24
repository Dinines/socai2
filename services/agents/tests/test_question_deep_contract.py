"""M5.1 direct task/query contracts: no model, HTTP, PG or stage creation."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import sys
import unittest
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.question_deep import QuestionTask, admit_deep_query, DeepRequestRejected
from app.investigation_v2.execution_store import scope_fingerprint
from test_evidence_view_contract import scope, ALERT, FILTERS


def proposal(task):
    return dict(action="query", tool="activity_records", parameters=task.query_defaults,
                reason="Read the original source record supporting Q1.")


class QuestionDeepContractTests(unittest.TestCase):
    def setUp(self):
        self.context = scope()
        self.task = QuestionTask(self.context, "Q1", ALERT, "source_check")

    def test_program_task_binds_parent_and_subtask_without_changing_scope(self):
        before = scope_fingerprint(self.context)
        same = QuestionTask(self.context, "Q1", str(ALERT), "source_check")
        other = QuestionTask(self.context, "Q1", ALERT, "other_check")
        self.assertEqual(self.task.task_id, same.task_id)
        self.assertNotEqual(self.task.task_id, other.task_id)
        another_run = replace(self.context, run_id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"))
        self.assertNotEqual(self.task.task_id, QuestionTask(another_run, "Q1", ALERT, "source_check").task_id)
        self.assertEqual(self.task.descriptor["max_queries"], 1)
        self.assertEqual(self.task.descriptor["max_model_rounds"], 2)
        self.assertFalse(self.task.descriptor["overall_assessment_allowed"])
        self.assertEqual(scope_fingerprint(self.context), before)

    def test_foreign_question_member_and_principal_are_rejected(self):
        for question in ("Q2", "Q3b", "Q99"):
            with self.subTest(question=question), self.assertRaises(DeepRequestRejected):
                QuestionTask(self.context, question, ALERT, "source_check")
        with self.assertRaises(DeepRequestRejected):
            QuestionTask(self.context, "Q1", UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"), "source_check")
        with self.assertRaises(DeepRequestRejected):
            QuestionTask(replace(self.context, tenant_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")), "Q1", ALERT, "source_check")
        for key in ("", "../source_check", "model decides", "x" * 65):
            with self.subTest(key=key), self.assertRaises(DeepRequestRejected):
                QuestionTask(self.context, "Q1", ALERT, key)

    def test_admitted_query_uses_only_checked_fields_and_parent_metadata(self):
        result = admit_deep_query(self.task, proposal(self.task))
        data = json.loads(result.canonical_doc)
        self.assertEqual(result.task_id, self.task.task_id)
        self.assertEqual({k: result.parameters[k] for k in FILTERS}, FILTERS)
        self.assertEqual((data["tenant_id"], data["run_id"], data["scope_revision"]),
                         (str(self.context.tenant_id), str(self.context.run_id), self.context.revision))
        self.assertEqual(result.parameters["limit"], self.context.query_scope.max_limit)
        self.assertEqual(data["model_assessed_reason"], proposal(self.task)["reason"])
        self.assertEqual(len(result.fingerprint), 64)

    def test_identity_sql_url_headers_and_wrong_capability_never_pass(self):
        for key in ("tenant_id", "run_id", "task_id", "question_id", "sql", "headers", "api_url", "service_token"):
            for place in ("proposal", "parameters"):
                value = proposal(self.task)
                (value if place == "proposal" else value["parameters"])[key] = "do-not-echo-this-value"
                with self.subTest(key=key, place=place), self.assertRaises(DeepRequestRejected) as caught:
                    admit_deep_query(self.task, value)
                self.assertNotIn("do-not-echo", str(caught.exception))
        for key, bad in (("tool", "run_sql"), ("tool", "https://arbitrary.example"), ("action", "execute")):
            value = proposal(self.task)
            value[key] = bad
            with self.subTest(key=key, value=bad), self.assertRaises(DeepRequestRejected):
                admit_deep_query(self.task, value)

    def test_filters_must_match_type_and_provenance(self):
        for key, bad in (("hostname", "another-host"), ("source_ip", "192.0.2.99"),
                         ("dest_ip", "198.51.100.99"), ("dst_port", "443"), ("protocol", "udp")):
            value = proposal(self.task)
            value["parameters"][key] = bad
            with self.subTest(key=key), self.assertRaisesRegex(DeepRequestRejected, "provenance"):
                admit_deep_query(self.task, value)

    def test_absolute_window_and_limit_admission_reuses_parent_bounds(self):
        changes = ({"start": "2026-10-23T09:59:59Z"}, {"end": "2026-10-23T10:05:01Z"},
                   {"start": "2026-10-23T10:05:00Z"}, {"start": "2026-10-23T10:00:00"},
                   {"limit": 0}, {"limit": 11}, {"limit": True})
        for change in changes:
            value = proposal(self.task)
            value["parameters"].update(change)
            with self.subTest(change=change), self.assertRaises(DeepRequestRejected):
                admit_deep_query(self.task, value)
        smaller = proposal(self.task)
        smaller["parameters"].update(start="2026-10-23T10:01:00Z", end="2026-10-23T10:02:00Z", limit=1)
        result = admit_deep_query(self.task, smaller)
        self.assertEqual(result.parameters["limit"], 1)
        self.assertEqual(self.context.query_scope.window.start.isoformat(), self.task.query_defaults["start"])

    def test_equivalent_queries_and_reason_changes_cannot_evade_deduplication(self):
        first = admit_deep_query(self.task, proposal(self.task))
        same = proposal(self.task)
        same["reason"] = "The same read with different words."
        same["parameters"].pop("limit")
        same["parameters"].update(start="2026-10-23T18:00:00+08:00", end="2026-10-23T10:05:00.000000Z")
        self.assertEqual(admit_deep_query(self.task, same).fingerprint, first.fingerprint)
        with self.assertRaisesRegex(DeepRequestRejected, "duplicate_query"):
            admit_deep_query(self.task, same, seen_queries=frozenset({first.fingerprint}))
        other_task = QuestionTask(self.context, "Q1", ALERT, "second_task")
        self.assertEqual(admit_deep_query(other_task, same).fingerprint, first.fingerprint)
        self.assertNotEqual(other_task.task_id, first.task_id)

    def test_query_history_and_reason_are_bounded_program_inputs(self):
        for history in ({"not-a-hash"}, frozenset({"bad"}), ["a" * 64]):
            with self.subTest(history=history), self.assertRaises(DeepRequestRejected):
                admit_deep_query(self.task, proposal(self.task), seen_queries=history)
        for text in ("", " ", "中" * 400, {"instruction": "query"}):
            value = proposal(self.task)
            value["reason"] = text
            with self.subTest(text_type=type(text).__name__), self.assertRaises(DeepRequestRejected):
                admit_deep_query(self.task, value)

    def test_returned_values_and_descriptors_are_detached(self):
        value = proposal(self.task)
        result = admit_deep_query(self.task, value)
        before = result.canonical_doc
        value["parameters"]["hostname"] = "mutated"
        changed = result.parameters
        changed["hostname"] = "mutated-again"
        descriptor = self.task.descriptor
        descriptor["approved_query_defaults"]["hostname"] = "mutated-descriptor"
        self.assertEqual(result.canonical_doc, before)
        self.assertEqual(result.parameters["hostname"], FILTERS["hostname"])
        self.assertEqual(self.task.query_defaults["hostname"], FILTERS["hostname"])
        with self.assertRaises(FrozenInstanceError):
            self.task.subtask_key = "replaced"


if __name__ == "__main__":
    unittest.main()
