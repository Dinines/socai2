"""Actual M7 store and renderer with SQL transport only; no real publication."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.execution_state import ExecutionRejected
from app.investigation_v2.execution_store import ExecutionPersistenceError, canonical_json, content_hash
from app.investigation_v2.recon_publication_store import (ReconPublicationStore, PUBLICATION_EVENT,
    MANIFEST_KIND, EXECUTION_KIND, REPORT_KIND)
import test_recon_publication_contract as fixtures
from test_evidence_view_contract import query


class ReconPublicationStoreContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fixture = fixtures.ReconPublicationContractTests()
        await self.fixture.asyncSetUp()
        self.runtime_fixture = self.fixture.fixture
        self.ledger, self.request = self.runtime_fixture.ledger, self.runtime_fixture.request

    def store(self, *, tenant=None, owner=None):
        return ReconPublicationStore(self.ledger, tenant_id=tenant or self.request.context.tenant_id,
            run_id=self.request.context.run_id, executor_id=owner or self.runtime_fixture.store.executor_id)

    async def normal(self, payload=None):
        await self.fixture.normal(payload)
        return self.store()

    async def cancelled_pending(self):
        f = self.runtime_fixture
        await f.fixture.begin();await f.store.claim(self.request);await f.fixture.reserve()
        await f.store.mark_cancelled(self.request);await f.store.finalize(self.request)
        return self.store()

    def publication_rows(self):
        return [e for e in self.ledger.events if e["kind"] == PUBLICATION_EVENT]

    async def test_unpublished_candidate_is_not_an_official_report(self):
        store = await self.normal();state = await store.load()
        read = await store.read_result(self.request)
        self.assertEqual(read["publication_state"], "not_published")
        self.assertIsNotNone(read["candidate"])
        self.assertIsNone(read["markdown"]);self.assertIsNone(read["manifest"]);self.assertIsNone(read["notification"])
        self.assertEqual(await store.load(), state)

    async def test_first_publish_is_one_event_four_artifacts_same_version(self):
        store = await self.normal();run = deepcopy(self.ledger.run);before = await store.load()
        saved = await store.publish(self.request)
        self.assertEqual((len(self.ledger.events), len(self.ledger.artifacts)), (6, 14))
        self.assertEqual(len(self.publication_rows()), 1)
        event = self.publication_rows()[0]
        owned = [a for a in self.ledger.artifacts.values() if a["event_id"] == event["id"]]
        self.assertEqual({a["kind"] for a in owned}, {MANIFEST_KIND, EXECUTION_KIND, REPORT_KIND, "unified_state_snapshot"})
        self.assertEqual(saved["publication_state"], "published")
        self.assertEqual(saved["manifest"]["retention"]["publication_artifacts"], "committed")
        self.assertEqual(saved["notification"]["manifest_artifact"], saved["manifest_artifact"])
        self.assertEqual(saved["notification"]["manifest_ref"], saved["manifest"]["manifest_ref"])
        self.assertEqual(saved["notification"]["delivery_status"], "not_attempted")
        after = await store.load()
        self.assertEqual(before["attempts"], after["attempts"])
        self.assertEqual(before["stage_usage"], after["stage_usage"])
        self.assertEqual(self.ledger.run, run)
        for row in owned:
            self.assertEqual(content_hash(row["content"]), row["sha256"])
            self.assertEqual(len(row["content"].encode("utf-8")), row["size_bytes"])

    async def test_repeat_and_cold_read_never_publish_or_notify_again(self):
        store = await self.normal();first = await store.publish(self.request)
        second = await self.store().publish(self.request)
        cold = await self.store().read_result(self.request)
        self.assertTrue(second["repeated"]);self.assertIsNone(second["notification"]);self.assertIsNone(cold["notification"])
        for key in ("manifest", "manifest_artifact", "execution_snapshot", "markdown"):
            self.assertEqual(first[key], second[key]);self.assertEqual(first[key], cold[key])
        self.assertEqual((len(self.ledger.events), len(self.ledger.artifacts), len(self.runtime_fixture.calls)), (6, 14, 1))

    async def test_two_publishers_create_exactly_one_version_and_one_descriptor(self):
        await self.normal()
        results = await asyncio.gather(self.store().publish(self.request), self.store().publish(self.request))
        self.assertEqual(sum(r["notification"] is not None for r in results), 1)
        self.assertEqual(results[0]["manifest_artifact"], results[1]["manifest_artifact"])
        self.assertEqual((len(self.ledger.events), len(self.ledger.artifacts)), (6, 14))

    async def test_each_publication_artifact_failure_rolls_back_whole_version(self):
        store = await self.normal();before = deepcopy((self.ledger.events, self.ledger.artifacts, self.ledger.run))
        for kind in (MANIFEST_KIND, EXECUTION_KIND, REPORT_KIND, "unified_state_snapshot"):
            self.ledger.fail_kind = kind
            with self.subTest(kind=kind), self.assertRaises(ExecutionPersistenceError): await store.publish(self.request)
            self.assertEqual((self.ledger.events, self.ledger.artifacts, self.ledger.run), before)
            self.assertEqual((await store.read_result(self.request))["publication_state"], "not_published")
        self.ledger.fail_kind = None

    async def test_commit_ack_unknown_never_returns_success_or_notification(self):
        store = await self.normal();self.ledger.fail_after_commit = True
        with self.assertRaises(ExecutionPersistenceError): await store.publish(self.request)
        recovered = await self.store().read_result(self.request)
        self.assertEqual(recovered["publication_state"], "published")
        self.assertIsNone(recovered["notification"])
        repeat = await self.store().publish(self.request)
        self.assertTrue(repeat["repeated"]);self.assertIsNone(repeat["notification"])
        self.assertEqual((len(self.ledger.events), len(self.ledger.artifacts)), (6, 14))

    async def test_partial_sources_keep_gaps_after_publication(self):
        store = await self.normal(query(status="empty"));saved = await store.publish(self.request)
        self.assertEqual(saved["execution_snapshot"]["run_state"], "stopped")
        self.assertEqual(saved["execution_snapshot"]["investigation_completeness"], "partial")
        self.assertIn("empty_within_query_only", saved["manifest"]["retention"]["source_gaps"])
        self.assertEqual((await self.store().read_result(self.request))["markdown"], saved["markdown"])

    async def test_cancelled_publication_preserves_unsettled_reservation(self):
        store = await self.cancelled_pending();before = await store.load();saved = await store.publish(self.request)
        self.assertEqual(saved["execution_snapshot"]["run_state"], "cancelled")
        self.assertEqual(saved["manifest"]["retention"]["unsettled_attempts"], 1)
        self.assertIsNone(saved["manifest"]["snapshots"]["evidence"])
        self.assertEqual((await store.load())["attempts"], before["attempts"])

    async def test_unconfirmed_observation_is_checked_and_remains_unadopted(self):
        f = self.runtime_fixture
        await f.fixture.begin();await f.store.claim(self.request);await f.fixture.reserve()
        await f.store.finalize(self.request, observed_tool_output=f.fixture.payload())
        saved = await self.store().publish(self.request)
        self.assertIsNotNone(saved["manifest"]["retention"]["unconfirmed_observation_ref"])
        self.assertIsNone(saved["manifest"]["snapshots"]["evidence"])
        self.assertEqual(saved["manifest"]["retention"]["unsettled_attempts"], 1)
        self.assertIn("未确认观察", saved["markdown"])

    async def test_missing_manifest_report_or_execution_has_no_fallback(self):
        store = await self.normal();await store.publish(self.request)
        for kind in (MANIFEST_KIND, REPORT_KIND, EXECUTION_KIND):
            row = next(a for a in self.ledger.artifacts.values() if a["kind"] == kind)
            removed = self.ledger.artifacts.pop(row["id"])
            with self.subTest(kind=kind), self.assertRaises(ExecutionRejected): await self.store().read_result(self.request)
            self.ledger.artifacts[row["id"]] = removed

    async def test_changed_retained_tool_bytes_are_not_hidden_by_intact_report(self):
        store = await self.normal();await store.publish(self.request)
        tool = next(a for a in self.ledger.artifacts.values() if a["kind"] == "unified_step_output")
        tool["content"] += " "
        with self.assertRaises(ExecutionRejected): await store.read_result(self.request)

    async def test_wrong_owner_or_tenant_cannot_read_or_publish(self):
        store = await self.normal();await store.publish(self.request)
        for other in (self.store(owner=UUID(int=99)), self.store(tenant=UUID(int=99))):
            async def session_setting(sql, *args):
                self.assertIn("set_config('app.current_tenant_id'", sql)
                self.assertEqual(args, (str(other.tenant_id),))
            # Real PG accepts a different valid tenant GUC; the row lookup
            # must then reject it. The single-tenant fixture otherwise stops
            # too early in its execute() assertion.
            with patch.object(self.ledger, "execute", new=AsyncMock(side_effect=session_setting)):
                with self.assertRaises(ExecutionRejected): await other.read_result(self.request)
                with self.assertRaises(ExecutionRejected): await other.publish(self.request)

    async def test_active_phase_only_has_progress_and_cannot_publish(self):
        f = self.runtime_fixture;await f.fixture.begin()
        store = self.store();read = await store.read_result(self.request)
        self.assertIsNone(read["candidate"]);self.assertIsNone(read["markdown"])
        self.assertEqual(read["progress"]["phase"], "ready")
        with self.assertRaises(ExecutionRejected): await store.publish(self.request)

    async def test_late_settle_before_publication_is_refused_without_new_version(self):
        store = await self.cancelled_pending();f = self.runtime_fixture
        await store.complete(attempt_id=f.runtime()._plan["attempt_id"], output_data=f.fixture.payload(), outcome="responded", actual_tokens=0, actual_cost_microusd=0, usage_source_ref="late")
        before = len(self.ledger.events)
        with self.assertRaisesRegex(ExecutionRejected, "stale"): await store.publish(self.request)
        self.assertEqual(len(self.ledger.events), before);self.assertEqual(self.publication_rows(), [])

    async def test_late_settle_after_publication_preserved_but_current_read_refused(self):
        store = await self.cancelled_pending();await store.publish(self.request);f = self.runtime_fixture
        await store.complete(attempt_id=f.runtime()._plan["attempt_id"], output_data=f.fixture.payload(), outcome="responded", actual_tokens=0, actual_cost_microusd=0, usage_source_ref="late-after-publication")
        self.assertEqual((await store.load())["stage_usage"]["unsettled_attempts"], 0)
        with self.assertRaisesRegex(ExecutionRejected, "no longer current"): await store.read_result(self.request)
        with self.assertRaisesRegex(ExecutionRejected, "no longer current"): await store.publish(self.request)
        self.assertEqual(len(self.publication_rows()), 1)

    async def test_older_writer_losing_pointer_cannot_make_second_publication(self):
        store = await self.cancelled_pending();await store.publish(self.request);f = self.runtime_fixture
        # The older M6 reader cannot see M7's kind; its late settlement loses
        # the pointer. The explicit publication event guard must still reject.
        await f.store.complete(attempt_id=f.runtime()._plan["attempt_id"], output_data=f.fixture.payload(), outcome="responded", actual_tokens=0, actual_cost_microusd=0, usage_source_ref="older-writer-late")
        with self.assertRaisesRegex(ExecutionRejected, "pointer is missing"): await store.read_result(self.request)
        with self.assertRaisesRegex(ExecutionRejected, "pointer is missing"): await store.publish(self.request)
        self.assertEqual(len(self.publication_rows()), 1)

    async def test_rehashed_report_with_forged_manifest_chain_is_still_rejected(self):
        store = await self.normal();await store.publish(self.request)
        event = self.publication_rows()[0];payload = event["payload"]
        manifest_row = self.ledger.artifacts[UUID(payload["body_artifact_id"])]
        manifest = json.loads(manifest_row["content"])
        report_row = self.ledger.artifacts[UUID(manifest["report"]["artifact_id"])]
        report_row["content"] += "\n新增未经采用的结论。\n"
        report_row["sha256"] = content_hash(report_row["content"]);report_row["size_bytes"] = len(report_row["content"].encode())
        manifest["report"]["sha256"] = report_row["sha256"]
        manifest.pop("manifest_ref");manifest["manifest_ref"] = "recon-manifest:" + content_hash(canonical_json(manifest))
        manifest_row["content"] = canonical_json(manifest);manifest_row["sha256"] = content_hash(manifest_row["content"]);manifest_row["size_bytes"] = len(manifest_row["content"].encode())
        snapshot = self.ledger.artifacts[UUID(payload["state_artifact_id"])]
        state = json.loads(snapshot["content"])
        state["publication"]["manifest_artifact"]["sha256"] = manifest_row["sha256"]
        state["publication"]["manifest_ref"] = manifest["manifest_ref"]
        state["persistence"]["body_hash"] = payload["body_hash"] = manifest_row["sha256"]
        snapshot["content"] = canonical_json(state);snapshot["sha256"] = content_hash(snapshot["content"]);snapshot["size_bytes"] = len(snapshot["content"].encode())
        payload["state_hash"] = snapshot["sha256"]
        with self.assertRaisesRegex(ExecutionRejected, "report differs from frozen basis"): await store.read_result(self.request)

    async def test_self_consistent_published_state_cannot_change_original_m3_usage(self):
        store = await self.normal();await store.publish(self.request)
        event = self.publication_rows()[0];payload = event["payload"]
        snapshot = self.ledger.artifacts[UUID(payload["state_artifact_id"])]
        state = json.loads(snapshot["content"])
        state["stage_usage"]["known_tokens"] = 123
        snapshot["content"] = canonical_json(state);snapshot["sha256"] = content_hash(snapshot["content"]);snapshot["size_bytes"] = len(snapshot["content"].encode())
        payload["state_hash"] = snapshot["sha256"]
        with self.assertRaisesRegex(ExecutionRejected, "changed the frozen execution basis"): await store.read_result(self.request)

    async def broken_required_source(self, case, *, after_publication):
        if case == "event":
            store = await self.normal()
        else:
            f = self.runtime_fixture;output = f.fixture.payload()
            output["rows"][0]["raw_payload"]["sha256"] = "0" * 64
            await f.fixture.completed(output=output);await f.store.finalize(self.request)
            store = self.store()
        if after_publication: await store.publish(self.request)
        tool = next(a for a in self.ledger.artifacts.values() if a["kind"] == "unified_step_output")
        if case == "event": tool["event_id"] = self.ledger.events[0]["id"]
        elif case == "kind": tool["kind"] = "wrong_kind"
        else: tool.update(content="{}", sha256=content_hash("{}"), size_bytes=2)
        return store

    async def test_every_completed_source_is_pinned_before_publication_even_if_rejected(self):
        for case in ("event", "kind", "rehash"):
            with self.subTest(case=case):
                await self.asyncSetUp()
                store = await self.broken_required_source(case, after_publication=False)
                with self.assertRaises(ExecutionRejected): await store.publish(self.request)

    async def test_every_completed_source_is_pinned_on_read_even_if_rejected(self):
        for case in ("event", "kind", "rehash"):
            with self.subTest(case=case):
                await self.asyncSetUp()
                store = await self.broken_required_source(case, after_publication=True)
                with self.assertRaises(ExecutionRejected): await store.read_result(self.request)

    async def test_no_begin_does_not_read_any_legacy_report(self):
        with self.assertRaises(ExecutionRejected): await self.store().read_result(self.request)
        self.assertEqual(self.ledger.events, [])


if __name__ == "__main__": unittest.main()
