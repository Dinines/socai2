"""One owned fixed-recon invocation; explicit begin, no retries or publication."""
from __future__ import annotations

import asyncio

import httpx

from .business_profile import BusinessProfileRequest
from .execution_state import BudgetLimits, OpeningUsage, ExecutionRejected
from .execution_store import ExecutionPersistenceError
from .execution_tools import DurableActivityRecords
from .recon_runtime_state import make_recon_plan
from .recon_runtime_store import ReconExecutionStore


class FixedReconRuntime:
    def __init__(self, store: ReconExecutionStore, request: BusinessProfileRequest, *, api_url: str,
                 service_token: str, transport: httpx.AsyncBaseTransport | None = None):
        if not isinstance(store, ReconExecutionStore):
            raise ExecutionRejected("versioned recon store required")
        self._plan = make_recon_plan(request)
        self._store, self._request = store, request
        self._gate = DurableActivityRecords(store, request.context, "Q1", self._plan["query_input"]["member_id"],
                                            api_url=api_url, service_token=service_token, transport=transport)

    async def begin(self, *, limits: BudgetLimits, opening: OpeningUsage, parent_deadline=None) -> dict:
        return await self._store.begin_recon(request=self._request, limits=limits, opening=opening,
                                             parent_deadline=parent_deadline)

    async def execute(self) -> dict:
        owns_claim = False
        attempt = self._plan["attempt_id"]
        try:
            claimed = await self._store.claim(self._request)
            decision = claimed["decision"]
            action = decision["action"]
            if action == "in_progress_or_interrupted":
                return {"status": action, "control_retention": "committed", "handoff": None,
                        "http_attempted_by_this_invocation": False, "receipt": claimed["receipt"]}
            if action == "read_handoff":
                saved = await self._store.read_handoff(self._request,
                    observed_tool_output=self._gate.observed_output(attempt))
                self._gate.clear_observation(attempt)
                return {"status": "stopped", "handoff": saved, "http_attempted_by_this_invocation": False}
            if action not in {"dispatch_after_commit", "finalize_blocked"}:
                raise ExecutionRejected("unknown fixed runtime decision")
            if action == "finalize_blocked" and decision["needs_commit"] is False:
                return {"status": "blocked_handoff_pending", "control_retention": "committed", "handoff": None,
                        "stop_reason": claimed["state"]["recon"]["stop_reason"],
                        "http_attempted_by_this_invocation": False, "receipt": claimed["receipt"]}
            owns_claim = decision["needs_commit"] is True
            http_attempted = False
            if action == "dispatch_after_commit":
                outcome = await self._gate.execute(step_id=self._plan["step_id"], attempt_id=attempt,
                                                    subtask_id=self._plan["subtask_id"],
                                                    parameters=self._plan["query_input"]["parameters"])
                http_attempted = outcome["http_attempted"]
                if outcome["execution_status"] == "blocked":
                    await self._store.mark_dispatch_block(self._request,
                        persistence_failure=outcome.get("reason_type") == "ExecutionPersistenceError")
            saved = await self._store.finalize(self._request, observed_tool_output=self._gate.observed_output(attempt))
            self._gate.clear_observation(attempt)
            return {"status": "stopped", "handoff": saved, "http_attempted_by_this_invocation": http_attempted}
        except asyncio.CancelledError:
            if owns_claim:
                try:
                    await self._store.mark_cancelled(self._request)
                    await self._store.finalize(self._request, observed_tool_output=self._gate.observed_output(attempt))
                    self._gate.clear_observation(attempt)
                except (ExecutionRejected, ExecutionPersistenceError):
                    pass  # Preserve the last confirmed ledger; do not replay.
            raise
