"""M3.3 durable gate for the already scoped, read-only M2 activity query.

Not registered in production. No models, orchestration, automatic retry or
final-result publication. A retained query response is not an adopted finding.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
import json
import time
from typing import Any
from uuid import UUID

import httpx

from app.investigation_v2.activity_records import bind_activity_records
from .execution_state import ExecutionRejected
from .execution_store import ExecutionStore, ExecutionPersistenceError, canonical_json, scope_fingerprint
from .scope import ScopeContext


class DurableActivityRecords:
    def __init__(self, store: ExecutionStore, context: ScopeContext, question_id: str,
                 member_id: UUID | str, *, api_url: str, service_token: str,
                 transport: httpx.AsyncBaseTransport | None = None):
        if (store.tenant_id, store.run_id) != (context.tenant_id, context.run_id):
            raise ExecutionRejected("tool scope and durable identity differ")
        self._store = store
        self._scope_hash = scope_fingerprint(context)
        self._question_id = question_id
        self._member_id = str(UUID(str(member_id)))
        self._observed_outputs: dict[str, str] = {}
        self._tool = bind_activity_records(context, question_id, member_id,
                                          api_url=api_url, service_token=service_token, transport=transport)

    def observed_output(self, attempt_id: UUID | str) -> dict | None:
        """A detached process observation, never a persistence receipt."""
        body = self._observed_outputs.get(str(UUID(str(attempt_id))))
        return json.loads(body) if body is not None else None

    def clear_observation(self, attempt_id: UUID | str) -> None:
        self._observed_outputs.pop(str(UUID(str(attempt_id))), None)

    async def execute(self, *, step_id: UUID | str, attempt_id: UUID | str, subtask_id: str,
                      parameters: dict[str, Any], retry_of: UUID | str | None = None) -> dict:
        """Return a distinct execution outcome and retention state, never replay.

        Parameters are data-only M2 arguments. Credentials never enter artifacts.
        A timeout cannot prove that the remote read did not run. Cancellation is
        re-raised after a best-effort unknown receipt; an unsettled reservation
        remains authoritative when that receipt itself cannot be committed.
        """
        began = time.monotonic()
        try:
            if not isinstance(parameters, dict):
                raise ExecutionRejected("tool parameters must be an object")
            schema = self._tool.parameters
            if (not set(schema["required"]).issubset(parameters)
                    or not set(parameters).issubset(schema["properties"])):
                # Do not persist rejected header/token/SQL fields before M2 gets
                # a chance to refuse them. Never include rejected values here.
                raise ExecutionRejected("missing or forbidden tool arguments")
            # Detach before any await: the saved input and dispatched arguments
            # must describe the same request even if the caller mutates its dict.
            parameters = json.loads(canonical_json(parameters))
            reservation = await self._store.reserve(
                scope_hash=self._scope_hash, step_id=step_id, attempt_id=attempt_id, subtask_id=subtask_id,
                question_id=self._question_id, kind="tool", reserve_tokens=0, reserve_cost_microusd=0,
                retry_of=retry_of,
                input_data={"tool": "activity_records", "member_id": self._member_id,
                            "question_id": self._question_id, "parameters": parameters})
        except (ExecutionRejected, ExecutionPersistenceError) as exc:
            return {"execution_status": "blocked", "retention": "not_confirmed", "http_attempted": False,
                    "dispatch_started": False, "attempt_id": str(attempt_id),
                    "reason": str(exc), "reason_type": type(exc).__name__, "tool_result": None,
                    "reservation": None, "completion": None}

        state = reservation["state"]
        # The store's DB time is authoritative. Subtract the whole transaction
        # elapsed time conservatively, including commit latency, without relying
        # on the worker's wall clock. Settlements remain allowed after expiry.
        remaining = ((datetime.fromisoformat(state["limits"]["deadline"])
                      - datetime.fromisoformat(state["updated_at"])).total_seconds()
                     - (time.monotonic() - began))
        dispatched, cancelled = False, False
        if remaining <= 0:
            result = {"tool": "activity_records", "status": "rejected", "reason": "deadline_after_reservation",
                      "caller_receipt": {"http_attempted": False}}
            outcome = "no_request"
        else:
            try:
                dispatched = True
                result = await asyncio.wait_for(self._tool.fn(**parameters), timeout=remaining)
                caller = result.get("caller_receipt", {})
                if caller.get("http_attempted") is False:
                    outcome = "no_request"
                elif caller.get("http_attempted") is True and type(caller.get("http_status")) is int:
                    outcome = "responded"  # includes an HTTP/query error, never means evidence success
                else:
                    outcome = "unknown"
            except asyncio.CancelledError:
                cancelled = True
                outcome = "unknown"
                result = {"tool": "activity_records", "status": "error", "reason": "caller_cancelled",
                          "caller_receipt": {"http_attempted": None}}
            except Exception as exc:
                outcome = "unknown"
                # Exceptions may contain URLs/headers; retain type only.
                result = {"tool": "activity_records", "status": "error", "reason": "dispatch_" + type(exc).__name__,
                          "caller_receipt": {"http_attempted": None}}

        try:
            self._observed_outputs[str(UUID(str(attempt_id)))] = canonical_json(result)
        except (ExecutionRejected, UnicodeError):
            pass  # An unrepresentable observation is not a checked result.
        completion = None
        retention = "committed"
        try:
            completion = await self._store.complete(
                attempt_id=attempt_id, output_data=result, outcome=outcome,
                actual_tokens=None if outcome == "unknown" else 0,
                actual_cost_microusd=None if outcome == "unknown" else 0,
                usage_source_ref="activity_records:http-receipt; no-model-or-metered-tool-charge")
        except (ExecutionRejected, ExecutionPersistenceError):
            retention = "gap"
        if cancelled:
            raise asyncio.CancelledError
        return {"execution_status": outcome if retention == "committed" else "retention_gap",
                "observed_outcome": outcome, "retention": retention,
                "http_attempted": result.get("caller_receipt", {}).get("http_attempted"),
                "dispatch_started": dispatched, "attempt_id": str(attempt_id), "tool_result": result,
                "reservation": reservation["receipt"],
                "completion": completion["receipt"] if completion is not None else None}
