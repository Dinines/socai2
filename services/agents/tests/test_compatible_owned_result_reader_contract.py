"""Explicit compatible owned bootstrap plus actual program read; SQL double, no real auth/PG."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.program_result_reader import CompatibleOwnedReconResultReader
from app.investigation_v2.execution_state import ExecutionRejected
from app.investigation_v2.execution_store import ExecutionPersistenceError, canonical_json, content_hash
from app.investigation_v2.program_recon_publication_store import ProgramReconPublicationStore, REPORT_KIND
from app.investigation_v2.scope import TenantPrincipal
import test_program_recon_publication_store_contract as fixtures
from _compatible_memory_ledger import MemoryLedger


class CompatibleOwnedResultReaderContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fixture = fixtures.ProgramReconPublicationStoreContractTests();await self.fixture.asyncSetUp()
        self.store = await self.fixture.normal();self.ledger = MemoryLedger.from_ledger(self.fixture.ledger);self.request = self.fixture.request
        self.principal = TenantPrincipal(frozenset({self.store.tenant_id}), "new-permitted-reader", False)
        self.reader = CompatibleOwnedReconResultReader(self.ledger)

    async def read(self, **changes):
        return await self.reader.read(**{**dict(current_principal=self.principal, tenant_id=self.store.tenant_id, run_id=self.store.run_id), **changes})

    def snapshot(self): return deepcopy((self.ledger.run, self.ledger.events, self.ledger.artifacts))

    async def test_published_lookup_by_ids_returns_original_version_and_explicit_target(self):
        saved = await self.store.publish(self.request);before = self.snapshot()
        read = await self.read()
        for key in ("manifest", "manifest_artifact", "execution_snapshot", "markdown"): self.assertEqual(read[key], saved[key])
        self.assertEqual(read["target"], self.request.descriptor["delivery_target"])
        self.assertEqual(read["profile"], "alert_recon")
        self.assertEqual(read["legacy_run_status"], "running")
        self.assertEqual(read["execution_snapshot"]["run_state"], "finished")
        self.assertEqual(read["schema"], "owned_program_recon_result.v1")
        self.assertIsNone(read["notification"]);self.assertEqual(self.snapshot(), before)

    async def test_same_transaction_read_uses_internal_helper_without_nested_lock(self):
        await self.store.publish(self.request)
        with patch.object(ProgramReconPublicationStore, "read_result", new=AsyncMock(side_effect=AssertionError("no nested lock"))):
            read = await asyncio.wait_for(self.read(), timeout=3)
        self.assertEqual(read["publication_state"], "published")

    async def test_unpublished_read_has_progress_and_no_formal_report_or_writes(self):
        before = self.snapshot();read = await self.read()
        self.assertEqual(read["publication_state"], "not_published")
        self.assertIsNotNone(read["candidate"]);self.assertIsNone(read["markdown"])
        self.assertEqual(self.snapshot(), before)

    async def test_current_empty_or_foreign_principal_is_refused_before_pool_use(self):
        for principal in (TenantPrincipal(), TenantPrincipal(frozenset({UUID(int=99)}), "foreign", True)):
            with patch.object(self.ledger, "execute", new=AsyncMock(side_effect=AssertionError("no SQL allowed"))) as blocked:
                with self.assertRaises(ExecutionRejected): await self.read(current_principal=principal)
            blocked.assert_not_awaited()

    async def test_wrong_run_id_or_owned_run_tenant_cannot_be_guessed(self):
        with self.assertRaisesRegex(ExecutionRejected, "owned Run not found"): await self.read(run_id=UUID(int=99))
        principal = TenantPrincipal(frozenset({self.store.tenant_id, UUID(int=99)}), "multi-tenant-reader", True)
        async def tenant_setting(sql, *args): self.assertEqual(args, (str(UUID(int=99)),))
        with patch.object(self.ledger, "execute", new=AsyncMock(side_effect=tenant_setting)):
            with self.assertRaisesRegex(ExecutionRejected, "owned Run not found"):
                await self.read(current_principal=principal, tenant_id=UUID(int=99))

    async def test_other_permitted_reader_uses_frozen_identity_without_querying_alert(self):
        saved = await self.store.publish(self.request)
        principal = TenantPrincipal(self.principal.tenant_ids, "another-reader", True)
        with patch.object(self.ledger, "fetchrow", wraps=self.ledger.fetchrow) as reads:
            read = await self.read(current_principal=principal)
        self.assertEqual(read["manifest"], saved["manifest"])
        self.assertTrue(all("FROM alerts" not in call.args[0] for call in reads.await_args_list))
        self.assertEqual(len(self.fixture.runtime_fixture.calls), 1)

    async def test_missing_or_duplicate_begin_marker_never_uses_legacy_report(self):
        original = self.ledger.events[0]["kind"]
        self.ledger.events[0]["kind"] = "legacy_report"
        with self.assertRaisesRegex(ExecutionRejected, "exactly one"): await self.read()
        self.ledger.events[0]["kind"] = original
        extra = deepcopy(self.ledger.events[0]);extra["id"] = uuid4();extra["seq"] = 99;self.ledger.events.append(extra)
        with self.assertRaisesRegex(ExecutionRejected, "exactly one"): await self.read()

    async def test_begin_event_agent_io_hash_payload_and_receipt_are_pinned(self):
        before = self.snapshot()
        for key, value in (("agent", "wrong"), ("input_hash", "0" * 64), ("output_hash", "0" * 64)):
            self.ledger.run, self.ledger.events, self.ledger.artifacts = deepcopy(before)
            self.ledger.events[0][key] = value
            with self.subTest(key=key), self.assertRaises(ExecutionRejected): await self.read()
        self.ledger.run, self.ledger.events, self.ledger.artifacts = deepcopy(before)
        self.ledger.events[0]["payload"]["body_artifact_id"] = self.ledger.events[2]["payload"]["body_artifact_id"]
        with self.assertRaises(ExecutionRejected): await self.read()

    async def test_bootstrap_artifact_kind_event_hash_or_owner_mismatch_is_rejected(self):
        before = self.snapshot()
        identity = UUID(self.ledger.events[0]["payload"]["body_artifact_id"])
        for key, value in (("kind", "wrong"), ("event_id", self.ledger.events[1]["id"]), ("tenant_id", UUID(int=99)), ("sha256", "0" * 64)):
            self.ledger.run, self.ledger.events, self.ledger.artifacts = deepcopy(before)
            self.ledger.artifacts[identity][key] = value
            with self.subTest(key=key), self.assertRaises(ExecutionRejected): await self.read()

    async def test_rehashed_bootstrap_snapshot_owner_cannot_replace_current_owner(self):
        payload = self.ledger.events[0]["payload"]
        row = self.ledger.artifacts[UUID(payload["state_artifact_id"])]
        state = json.loads(row["content"]);state["executor_id"] = str(UUID(int=99))
        row["content"] = canonical_json(state);row["sha256"] = content_hash(row["content"]);row["size_bytes"] = len(row["content"].encode())
        payload["state_hash"] = row["sha256"]
        with self.assertRaisesRegex(ExecutionRejected, "owner"): await self.read()

    async def test_missing_downstream_report_does_not_fall_back_to_candidate(self):
        await self.store.publish(self.request)
        row = next(a for a in self.ledger.artifacts.values() if a["kind"] == REPORT_KIND)
        self.ledger.artifacts.pop(row["id"])
        with self.assertRaises(ExecutionRejected): await self.read()

    async def test_driver_failure_is_sanitized_and_does_not_create_a_run(self):
        before = self.snapshot()
        with patch.object(self.ledger, "fetch", new=AsyncMock(side_effect=RuntimeError("PRIVATE_DRIVER_DSN_OR_TEXT"))):
            with self.assertRaises(ExecutionPersistenceError) as raised: await self.read()
        self.assertNotIn("PRIVATE_DRIVER", str(raised.exception));self.assertEqual(self.snapshot(), before)

    async def test_late_settle_is_retained_but_read_refuses_old_published_version(self):
        await self.fixture.asyncSetUp();self.store = await self.fixture.cancelled_pending()
        self.ledger = MemoryLedger.from_ledger(self.fixture.ledger);self.reader = CompatibleOwnedReconResultReader(self.ledger)
        await self.store.publish(self.request)
        f = self.fixture.runtime_fixture
        await self.store.complete(attempt_id=f.runtime()._plan["attempt_id"], output_data=f.fixture.payload(), outcome="responded", actual_tokens=0, actual_cost_microusd=0, usage_source_ref="reader-late")
        before = self.snapshot()
        with self.assertRaisesRegex(ExecutionRejected, "no longer current"): await self.read()
        self.assertEqual(self.snapshot(), before)

    async def version_fixture(self, version, phase="published"):
        if version=="fixed":
            from test_recon_publication_store_contract import ReconPublicationStoreContractTests
            fixture=ReconPublicationStoreContractTests()
        else:
            fixture=fixtures.ProgramReconPublicationStoreContractTests()
        await fixture.asyncSetUp()
        if phase=="progress":
            await fixture.runtime_fixture.fixture.begin();store=fixture.store()
        elif phase=="cancelled":store=await fixture.cancelled_pending()
        elif phase=="observer":
            f=fixture.runtime_fixture
            await f.fixture.begin();await f.store.claim(fixture.request);await f.fixture.reserve()
            await f.store.finalize(fixture.request,observed_tool_output=f.fixture.payload());store=fixture.store()
        else:store=await fixture.normal()
        if phase in {"published","observer","cancelled"}:await store.publish(fixture.request)
        pool=MemoryLedger.from_ledger(fixture.ledger)
        return fixture,store,pool

    async def test_fixed_legacy_full_DTO_is_exact_for_published_candidate_progress_and_partial(self):
        from app.investigation_v2.result_reader import OwnedReconResultReader
        for phase in ("published","candidate","progress","observer","cancelled"):
            f,store,pool=await self.version_fixture("fixed",phase)
            principal=TenantPrincipal(frozenset({store.tenant_id}),"same-current-reader",True)
            before=deepcopy((pool.run,pool.events,pool.artifacts));calls=len(f.runtime_fixture.calls)
            kwargs=dict(current_principal=principal,tenant_id=store.tenant_id,run_id=store.run_id)
            old=await OwnedReconResultReader(pool).read(**kwargs)
            new=await CompatibleOwnedReconResultReader(pool).read(**kwargs)
            with self.subTest(phase=phase):
                self.assertEqual(canonical_json(new),canonical_json(old))
                self.assertEqual(new["schema"],"owned_fixed_recon_result.v1")
                self.assertEqual((pool.run,pool.events,pool.artifacts),before)
                self.assertEqual(len(f.runtime_fixture.calls),calls)

    async def test_unknown_managed_begin_or_control_anywhere_refuses_both_versions(self):
        for version in ("fixed","program"):
            f,store,pool=await self.version_fixture(version)
            original=deepcopy(pool.events)
            principal=TenantPrincipal(frozenset({store.tenant_id}),"reader",False)
            for kind in ("unified_future_recon_started","unified_future_control"):
                for position in ("before","middle","after"):
                    pool.events=deepcopy(original)
                    if position=="middle":pool.events[2]["kind"]=kind
                    else:
                        row=deepcopy(original[0]);row.update(id=uuid4(),kind=kind,seq=0 if position=="before" else 99)
                        pool.events.append(row)
                    before=deepcopy((pool.events,pool.artifacts))
                    with self.subTest(version=version,kind=kind,position=position),self.assertRaisesRegex(ExecutionRejected,"unknown or mixed managed event"):
                        await CompatibleOwnedReconResultReader(pool).read(current_principal=principal,tenant_id=store.tenant_id,run_id=store.run_id)
                    self.assertEqual((pool.events,pool.artifacts),before)

    async def test_known_historical_control_with_wrong_or_null_agent_is_not_ignored(self):
        for version in ("fixed","program"):
            f,store,pool=await self.version_fixture(version)
            original=deepcopy(pool.events)
            for value in ("other-runtime",None):
                pool.events=deepcopy(original);pool.events[2]["agent"]=value
                with self.subTest(version=version,agent=value),self.assertRaisesRegex(ExecutionRejected,"unknown or mixed managed event"):
                    await CompatibleOwnedReconResultReader(pool).read(current_principal=self.principal,tenant_id=store.tenant_id,run_id=store.run_id)

    async def test_self_rehashed_float_begin_receipt_is_not_actual_integer_event_sequence(self):
        for version in ("fixed","program"):
            f,store,pool=await self.version_fixture(version)
            payload=pool.events[0]["payload"];payload["seq"]=float(pool.events[0]["seq"])
            row=pool.artifacts[UUID(payload["state_artifact_id"])];state=json.loads(row["content"])
            state["persistence"]["seq"]=payload["seq"]
            row["content"]=canonical_json(state);row.update(sha256=content_hash(row["content"]),size_bytes=len(row["content"].encode()))
            payload["state_hash"]=row["sha256"]
            with self.subTest(version=version),self.assertRaisesRegex(ExecutionRejected,"owned begin receipt mismatch"):
                await CompatibleOwnedReconResultReader(pool).read(current_principal=self.principal,tenant_id=store.tenant_id,run_id=store.run_id)

    async def test_program_legal_scope_revision_two_is_restored_by_owned_entry(self):
        from app.investigation_v2.scope import initialize_scope
        f=fixtures.ProgramReconPublicationStoreContractTests();await f.asyncSetUp()
        original=f.request.context
        revised=initialize_scope(principal=TenantPrincipal(original.principal.tenant_ids,original.principal.subject,original.principal.delegated),
            tenant_id=original.tenant_id,run_id=original.run_id,snapshot=original.member_snapshot,window=original.query_scope.window,
            target_type=original.target_type,policy_ref=original.policy_ref,revision=2,previous=original)
        request=replace(f.request,context=revised)
        f.request=f.runtime_fixture.request=f.runtime_fixture.fixture.request=request
        store=await f.normal();saved=await store.publish(request);pool=MemoryLedger.from_ledger(f.ledger)
        read=await CompatibleOwnedReconResultReader(pool).read(current_principal=self.principal,tenant_id=store.tenant_id,run_id=store.run_id)
        self.assertEqual(read["schema"],"owned_program_recon_result.v1")
        self.assertEqual(read["manifest"]["scope_revision"],2)
        self.assertEqual(read["manifest"],saved["manifest"])

    async def test_other_managed_start_kind_cannot_select_a_generic_or_mixed_branch(self):
        from app.investigation_v2.execution_store import KINDS
        from app.investigation_v2.recon_runtime_store import CONTROL_KINDS as OLD
        for change in ("generic","mixed"):
            await self.asyncSetUp()
            if change=="generic":self.ledger.events[0]["kind"]=KINDS[0]
            else:
                event=deepcopy(self.ledger.events[0]);event.update(id=uuid4(),kind=OLD[0],seq=99)
                self.ledger.events.append(event)
            with self.subTest(change=change),self.assertRaises(ExecutionRejected):await self.read()


if __name__ == "__main__": unittest.main()
