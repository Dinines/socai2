"""M6.2b2 actual runtime/store/M3 gate with SQL and HTTP transports doubled."""
import asyncio
from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock
from uuid import UUID

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.execution_state import ExecutionRejected
from app.investigation_v2.execution_store import ExecutionPersistenceError, ExecutionStore
from app.investigation_v2.fixed_recon_runtime import FixedReconRuntime
from app.investigation_v2.recon_runtime_store import ReconExecutionStore, HANDOFF_KIND, OBSERVATION_KIND
import test_recon_runtime_store_contract as store_fixtures
from test_recon_runtime_state_contract import OWNER, START

SECRET = "DO_NOT_STORE_SERVICE_SECRET"
API = "https://private-runtime.invalid"


class FixedReconRuntimeContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fixture = store_fixtures.ReconRuntimeStoreContractTests()
        await self.fixture.asyncSetUp()
        self.store, self.request, self.ledger = self.fixture.store, self.fixture.request, self.fixture.ledger
        self.calls = []

    def runtime(self, *, store=None, handler=None):
        async def transport(request):
            self.calls.append(request)
            if handler: return await handler(request)
            return httpx.Response(200, json=self.fixture.payload())
        return FixedReconRuntime(store or self.store, self.request, api_url=API, service_token=SECRET,
                                 transport=httpx.MockTransport(transport))

    async def begin(self, runtime, **changes):
        return await runtime.begin(limits=replace(self.fixture.limits, **changes), opening=self.fixture.opening)

    def assert_no_credentials(self):
        text = json.dumps([self.ledger.events, list(self.ledger.artifacts.values())], default=str)
        self.assertNotIn(SECRET, text)
        self.assertNotIn(API, text)

    async def test_normal_once_and_repeated_cold_read_never_adds_http(self):
        runtime = self.runtime();await self.begin(runtime)
        first = await runtime.execute()
        self.assertEqual(first["handoff"]["candidate"]["result"]["scope_readiness"], "ready")
        second = await self.runtime().execute()
        self.assertEqual(first["handoff"]["candidate"], second["handoff"]["candidate"])
        self.assertFalse(second["http_attempted_by_this_invocation"])
        self.assertEqual(len(self.calls), 1)
        self.assertIsNone(runtime._gate.observed_output(runtime._plan["attempt_id"]))
        self.assert_no_credentials()

    async def test_zero_budget_stops_before_gate_or_http(self):
        runtime = self.runtime();await self.begin(runtime, max_tool_calls=0)
        runtime._gate.execute = AsyncMock(side_effect=AssertionError("must not call gate"))
        saved = await runtime.execute()
        self.assertEqual(saved["handoff"]["candidate"]["result"]["stop_reason"], "budget_limit")
        self.assertEqual(self.calls, [])
        self.assertEqual(saved["handoff"]["state"]["attempts"], {})

    async def test_concurrent_duplicate_only_reads_active_claim(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def handler(request):
            entered.set();await release.wait()
            return httpx.Response(200, json=self.fixture.payload())
        runtime = self.runtime(handler=handler);await self.begin(runtime)
        first = asyncio.create_task(runtime.execute());await entered.wait()
        second = await self.runtime().execute()
        self.assertEqual(second["status"], "in_progress_or_interrupted")
        self.assertEqual(len(self.calls), 1)
        release.set();await first

    async def test_claim_commit_ack_loss_never_dispatches_or_reclaims(self):
        runtime = self.runtime();await self.begin(runtime)
        self.ledger.fail_after_commit = True
        with self.assertRaises(ExecutionPersistenceError): await runtime.execute()
        self.assertEqual(self.calls, [])
        self.assertEqual((await runtime.execute())["status"], "in_progress_or_interrupted")
        self.assertEqual((await self.store.load())["attempts"], {})

    async def test_reservation_persistence_failure_is_a_saved_stop_without_http(self):
        runtime = self.runtime();await self.begin(runtime)
        self.store.reserve = AsyncMock(side_effect=ExecutionPersistenceError("sensitive-driver-text"))
        saved = await runtime.execute()
        self.assertEqual(saved["handoff"]["candidate"]["result"]["stop_reason"], "retention_gap")
        self.assertEqual(self.calls, [])
        self.assertNotIn("sensitive-driver-text", json.dumps(self.ledger.events, default=str))
        self.assert_no_credentials()

    async def test_reservation_invariant_failure_is_not_a_generic_budget_stop(self):
        runtime = self.runtime();await self.begin(runtime)
        self.store.reserve = AsyncMock(side_effect=ExecutionRejected("invalid-frozen-request"))
        with self.assertRaisesRegex(ExecutionRejected, "invariant"):
            await runtime.execute()
        self.assertEqual(self.calls, [])
        self.assertEqual((await self.store.load())["recon"]["phase"], "claimed")

    async def test_completion_failure_preserves_observation_without_adoption(self):
        runtime = self.runtime();await self.begin(runtime)
        self.store.complete = AsyncMock(side_effect=ExecutionPersistenceError("completion unavailable"))
        saved = await runtime.execute()
        candidate = saved["handoff"]["candidate"]
        self.assertIsNotNone(candidate["unconfirmed_observation_ref"])
        self.assertEqual(candidate["result"]["facts"], [])
        self.assertEqual(saved["handoff"]["state"]["stage_usage"]["unsettled_attempts"], 1)
        self.assertEqual(len(self.calls), 1)
        await self.runtime().execute()
        self.assertEqual(len(self.calls), 1)

    async def test_completion_ack_loss_is_verified_by_readback_without_requery(self):
        async def handler(request):
            self.ledger.fail_after_commit = True
            return httpx.Response(200, json=self.fixture.payload())
        runtime = self.runtime(handler=handler);await self.begin(runtime)
        saved = await runtime.execute()
        self.assertEqual(saved["handoff"]["candidate"]["result"]["scope_readiness"], "ready")
        self.assertIsNone(saved["handoff"]["candidate"]["unconfirmed_observation_ref"])
        self.assertEqual(saved["handoff"]["state"]["stage_usage"]["unsettled_attempts"], 0)
        self.assertEqual(len(self.calls), 1)

    async def test_cancel_during_http_propagates_and_preserves_unknown(self):
        entered = asyncio.Event()
        async def handler(request):
            entered.set();await asyncio.Event().wait()
        runtime = self.runtime(handler=handler);await self.begin(runtime)
        task = asyncio.create_task(runtime.execute());await entered.wait();task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task
        saved = await self.store.read_handoff(self.request)
        self.assertEqual(saved["candidate"]["result"]["stop_reason"], "cancelled")
        self.assertEqual(saved["state"]["stage_usage"]["unknown_attempts"], 1)
        self.assertEqual(saved["state"]["stage_usage"]["unsettled_attempts"], 1)

    async def test_cancel_during_complete_still_retains_the_already_received_output(self):
        entered = asyncio.Event()
        async def paused_complete(**kwargs):
            entered.set();await asyncio.Event().wait()
        runtime = self.runtime();await self.begin(runtime)
        self.store.complete = paused_complete
        task = asyncio.create_task(runtime.execute());await entered.wait();task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task
        saved = await self.store.read_handoff(self.request)
        ref = saved["candidate"]["unconfirmed_observation_ref"]
        observation = self.ledger.artifacts[UUID(ref["artifact_id"])]
        self.assertEqual(observation["kind"], OBSERVATION_KIND)
        self.assertEqual(len(json.loads(observation["content"])["tool_result"]["rows"]), 1)
        self.assertEqual(saved["candidate"]["result"]["facts"], [])
        self.assertEqual(saved["state"]["stage_usage"]["unsettled_attempts"], 1)
        self.assertEqual(len(self.calls), 1)

    async def test_duplicate_cannot_freeze_cancelled_handoff_before_owner_observation(self):
        entered, marked, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
        runtime = self.runtime();await self.begin(runtime)
        async def paused_complete(**kwargs):
            entered.set();await asyncio.Event().wait()
        real_mark = self.store.mark_cancelled
        async def paused_mark(request):
            saved = await real_mark(request);marked.set();await release.wait();return saved
        self.store.complete = paused_complete;self.store.mark_cancelled = paused_mark
        owner = asyncio.create_task(runtime.execute());await entered.wait();owner.cancel();await marked.wait()
        try:
            repeated = await self.runtime().execute()
            self.assertEqual(repeated["status"], "blocked_handoff_pending")
        finally:
            release.set()
            with self.assertRaises(asyncio.CancelledError): await owner
        saved = await self.store.read_handoff(self.request)
        self.assertIsNotNone(saved["candidate"]["unconfirmed_observation_ref"])
        self.assertEqual(saved["candidate"]["result"]["facts"], [])
        self.assertEqual(saved["state"]["stage_usage"]["unsettled_attempts"], 1)
        self.assertEqual(sum(a["kind"] == OBSERVATION_KIND for a in self.ledger.artifacts.values()), 1)
        self.assertEqual(len(self.calls), 1)
        await runtime.execute()
        self.assertIsNone(runtime._gate.observed_output(runtime._plan["attempt_id"]))

    async def test_readback_never_discards_observation_absent_from_a_frozen_handoff(self):
        entered, marked, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
        runtime = self.runtime();await self.begin(runtime)
        async def paused_complete(**kwargs):
            entered.set();await asyncio.Event().wait()
        mark = self.store.mark_cancelled
        async def paused_mark(request):
            saved = await mark(request);marked.set();await release.wait();return saved
        self.store.complete = paused_complete;self.store.mark_cancelled = paused_mark
        owner = asyncio.create_task(runtime.execute());await entered.wait();owner.cancel();await marked.wait()
        # Simulate an incompatible already-sealed record from an older caller.
        await self.store.finalize(self.request)
        release.set()
        with self.assertRaises(asyncio.CancelledError): await owner
        self.assertIsNotNone(runtime._gate.observed_output(runtime._plan["attempt_id"]))
        with self.assertRaisesRegex(ExecutionRejected, "observation cannot modify"):
            await runtime.execute()
        self.assertIsNotNone(runtime._gate.observed_output(runtime._plan["attempt_id"]))
        self.assertEqual(len(self.calls), 1)

    async def test_cancelling_duplicate_request_never_cancels_the_original_worker(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def handler(request):
            entered.set();await release.wait()
            return httpx.Response(200, json=self.fixture.payload())
        first_runtime = self.runtime(handler=handler);await self.begin(first_runtime)
        first = asyncio.create_task(first_runtime.execute());await entered.wait()
        other_store = ReconExecutionStore(self.ledger, tenant_id=self.store.tenant_id, run_id=self.store.run_id, executor_id=OWNER)
        claim = other_store.claim;duplicate_entered = asyncio.Event()
        async def paused_claim(request):
            saved = await claim(request);duplicate_entered.set();await asyncio.Event().wait()
            return saved
        other_store.claim = paused_claim
        duplicate = asyncio.create_task(self.runtime(store=other_store).execute())
        await duplicate_entered.wait();duplicate.cancel()
        with self.assertRaises(asyncio.CancelledError): await duplicate
        self.assertEqual((await self.store.load())["recon"]["phase"], "claimed")
        self.assertFalse(first.done())
        release.set();self.assertEqual((await first)["handoff"]["candidate"]["result"]["scope_readiness"], "ready")
        self.assertEqual(len(self.calls), 1)

    async def test_unconfirmed_cancelled_claim_is_not_taken_over(self):
        runtime = self.runtime();await self.begin(runtime)
        claim = self.store.claim
        async def interrupted_claim(request):
            await claim(request);raise asyncio.CancelledError
        self.store.claim = interrupted_claim
        with self.assertRaises(asyncio.CancelledError): await runtime.execute()
        self.store.claim = claim
        self.assertEqual((await runtime.execute())["status"], "in_progress_or_interrupted")
        self.assertEqual(self.calls, [])
        self.assertEqual((await self.store.load())["recon"]["phase"], "claimed")

    async def test_failed_handoff_is_not_hidden_or_retried_with_another_query(self):
        runtime = self.runtime();await self.begin(runtime)
        self.ledger.fail_kind = HANDOFF_KIND
        with self.assertRaises(ExecutionPersistenceError): await runtime.execute()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual((await runtime.execute())["status"], "in_progress_or_interrupted")
        self.assertEqual(len(self.calls), 1)
        self.assertIsNotNone(runtime._gate.observed_output(runtime._plan["attempt_id"]))

    async def test_readback_after_handoff_ack_loss_clears_the_process_observation(self):
        runtime = self.runtime();await self.begin(runtime)
        finalize = self.store.finalize
        async def lost_ack(*args, **kwargs):
            await finalize(*args, **kwargs)
            raise ExecutionPersistenceError("simulated handoff acknowledgement loss")
        self.store.finalize = lost_ack
        with self.assertRaises(ExecutionPersistenceError): await runtime.execute()
        self.assertIsNotNone(runtime._gate.observed_output(runtime._plan["attempt_id"]))
        self.store.finalize = finalize
        saved = await runtime.execute()
        self.assertEqual(saved["status"], "stopped")
        self.assertIsNone(runtime._gate.observed_output(runtime._plan["attempt_id"]))
        self.assertEqual(len(self.calls), 1)

    async def test_begin_is_required_and_generic_store_is_rejected(self):
        with self.assertRaisesRegex(ExecutionRejected, "durable begin"):
            await self.runtime().execute()
        generic = ExecutionStore(self.ledger, tenant_id=self.store.tenant_id, run_id=self.store.run_id, executor_id=OWNER)
        with self.assertRaisesRegex(ExecutionRejected, "versioned recon store"):
            FixedReconRuntime(generic, self.request, api_url=API, service_token=SECRET)
        self.assertEqual(self.calls, [])

    async def test_deadline_between_claim_and_reserve_stops_without_http(self):
        runtime = self.runtime();await self.begin(runtime)
        claim = self.store.claim
        async def delayed_claim(request):
            saved = await claim(request)
            self.ledger.now = START + timedelta(seconds=31)
            return saved
        self.store.claim = delayed_claim
        saved = await runtime.execute()
        self.assertEqual(saved["handoff"]["candidate"]["result"]["stop_reason"], "deadline")
        self.assertEqual(saved["handoff"]["state"]["stage_usage"]["tool_calls"], 0)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
