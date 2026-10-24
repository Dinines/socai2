"""Owned M6 fixed-recon transactions on the existing ledger; no external calls."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import json
from typing import Any
from uuid import UUID, uuid4

from .business_profile import BusinessProfileRequest
from .evidence_view import CommittedMaterial
from .execution_state import BudgetLimits, OpeningUsage, ExecutionRejected, initial_state, reserve
from .execution_store import (ExecutionStore, KINDS, canonical_json, content_hash,
                              scope_fingerprint, scope_snapshot, _object)
from .fixed_recon import evaluate_alert_recon
from .recon_material import prepare_alert_recon
from .recon_runtime_state import (RUNTIME_VERSION, make_recon_plan, install_recon, claim_recon,
    validate_recon_reservation, observed_recon_stop, cancel_recon, finish_recon)

CONTROL_KINDS = ("unified_recon_started", "unified_recon_claimed", "unified_recon_cancelled",
                 "unified_recon_handoff_saved", "unified_recon_dispatch_blocked")
HANDOFF_KIND = "fixed_recon_handoff"
OBSERVATION_KIND = "fixed_recon_unconfirmed_observation"


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ExecutionRejected(reason)


class ReconExecutionStore(ExecutionStore):
    event_kinds = (*KINDS, *CONTROL_KINDS)
    runtime_version = RUNTIME_VERSION
    event_agent = RUNTIME_VERSION

    async def _bound(self, conn: Any, state: dict, request: BusinessProfileRequest) -> None:
        _require(isinstance(request, BusinessProfileRequest), "checked business request required")
        expected = make_recon_plan(request)
        _require(canonical_json(state["recon"]["plan"]) == canonical_json(expected), "request differs from frozen runtime")
        body = await self._read_artifact(conn, UUID(state["input_snapshot_ref"].removeprefix("urn:uuid:")))
        frozen = _object(body["content"])
        _, sources = scope_snapshot(request.context)
        _require(body["kind"] == "unified_step_input" and body["sha256"] == state["input_hash"]
                 and frozen["input"]["runtime_plan"] == expected
                 and frozen["input"]["business_profile"] == request.descriptor
                 and frozen["scope_hash"] == scope_fingerprint(request.context)
                 and frozen["scope_sources"] == sources, "frozen runtime input mismatch")

    async def begin_recon(self, *, request: BusinessProfileRequest, limits: BudgetLimits, opening: OpeningUsage,
                          parent_deadline: datetime | None = None) -> dict:
        plan = make_recon_plan(request)
        _require((request.context.tenant_id, request.context.run_id) == (self.tenant_id, self.run_id),
                 "runtime and store identity differ")
        if parent_deadline is not None:
            _require(parent_deadline.tzinfo is not None and parent_deadline.utcoffset() is not None,
                     "parent deadline requires timezone")
            limits = replace(limits, deadline=min(limits.deadline, parent_deadline))
        controls, sources = scope_snapshot(request.context)
        body = canonical_json({"input": {"business_profile": request.descriptor, "runtime_plan": plan},
                               "scope_sources": sources, "scope_hash": scope_fingerprint(request.context)})
        body_id = uuid4()
        async with self._locked() as (conn, run):
            _require(run["status"] == "running" and run["completed_at"] is None, "fresh running Run required")
            exists = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM investigation_events "
                                         "WHERE run_id=$1 AND kind LIKE 'unified_%')", self.run_id)
            _require(not exists, "stage already began; reset/takeover forbidden")
            now = await conn.fetchval("SELECT clock_timestamp()")
            state = initial_state(scope=controls, input_snapshot_ref="urn:uuid:" + str(body_id),
                                  input_hash=content_hash(body), limits=limits, opening=opening,
                                  executor_id=self.executor_id, now=now)
            state = install_recon(state, request, now=now)
            state["legacy_run_snapshot"] = json.loads(canonical_json(run))
            saved = await self._append(conn, state, kind=CONTROL_KINDS[0], body=body, body_id=body_id,
                                       body_kind="unified_step_input", now=now)
        return saved

    async def claim(self, request: BusinessProfileRequest) -> dict:
        async with self._locked() as (conn, _):
            state = await self._load(conn)
            await self._bound(conn, state, request)
            now = await conn.fetchval("SELECT clock_timestamp()")
            updated, decision = claim_recon(state, now=now)
            if decision["needs_commit"]:
                body = canonical_json({"plan_ref": state["recon"]["plan"]["plan_ref"], "decision": decision})
                saved = await self._append(conn, updated, kind=CONTROL_KINDS[1], body=body, body_id=uuid4(),
                                           body_kind="fixed_recon_control", now=now)
            else:
                saved = {"state": state, "receipt": state["persistence"], "repeated": True}
        return {**saved, "decision": decision}

    async def reserve(self, *, scope_hash: str, input_data: Any, **request: Any) -> dict:
        body, body_id = canonical_json(input_data), uuid4()
        async with self._locked() as (conn, _):
            state = await self._load(conn)
            _require(state["scope_hash"] == scope_hash, "caller scope differs from durable scope")
            now = await conn.fetchval("SELECT clock_timestamp()")
            validate_recon_reservation(state, input_data=json.loads(body), request=request, now=now)
            updated, attempt = reserve(state, **request, input_snapshot_ref="urn:uuid:" + str(body_id),
                                       input_hash=content_hash(body), now=now)
            saved = await self._append(conn, updated, kind=KINDS[1], body=body, body_id=body_id,
                                       body_kind="unified_step_input", now=now, attempt_id=attempt["attempt_id"])
        return saved

    async def mark_cancelled(self, request: BusinessProfileRequest) -> dict:
        async with self._locked() as (conn, _):
            state = await self._load(conn)
            await self._bound(conn, state, request)
            if state["recon"]["phase"] == "stopped":
                return {"state": state, "receipt": state["persistence"], "repeated": True}
            now = await conn.fetchval("SELECT clock_timestamp()")
            if state["recon"]["phase"] == "blocked":
                updated = state  # Preserve an already-recorded admission stop.
            else:
                updated = cancel_recon(state, now=now)
            updated["recon"]["cancellation_observed_at"] = now.isoformat(timespec="microseconds")
            updated["updated_at"] = now.isoformat(timespec="microseconds")
            saved = await self._append(conn, updated, kind=CONTROL_KINDS[2], body=canonical_json({"cancelled": True}),
                                       body_id=uuid4(), body_kind="fixed_recon_control", now=now)
        return saved

    async def mark_dispatch_block(self, request: BusinessProfileRequest, *, persistence_failure: bool) -> dict:
        _require(type(persistence_failure) is bool, "typed persistence observation required")
        async with self._locked() as (conn, _):
            state = await self._load(conn)
            await self._bound(conn, state, request)
            _require(state["recon"]["phase"] == "claimed", "dispatch block requires claimed runtime")
            now = await conn.fetchval("SELECT clock_timestamp()")
            stop = observed_recon_stop(state, now=now)
            _require(stop is not None or persistence_failure, "dispatch invariant rejected without an observed stop")
            state["recon"].update(phase="blocked", stop_reason=stop or "retention_gap")
            state["updated_at"] = now.isoformat(timespec="microseconds")
            body = canonical_json({"dispatch_not_authorized": True, "persistence_failure": persistence_failure,
                                   "stop_reason": state["recon"]["stop_reason"]})
            saved = await self._append(conn, state, kind=CONTROL_KINDS[4], body=body, body_id=uuid4(),
                                       body_kind="fixed_recon_control", now=now)
        return saved

    async def _tool_artifact(self, conn: Any, state: dict) -> dict | None:
        attempt = state["attempts"].get(state["recon"]["plan"]["attempt_id"])
        if attempt is None or not attempt.get("completion_receipt"):
            return None
        receipt = attempt["completion_receipt"]
        artifact = await self._read_artifact(conn, UUID(receipt["body_artifact_id"]), UUID(receipt["event_id"]))
        _require(artifact["kind"] == "unified_step_output" and artifact["sha256"] == receipt["body_hash"],
                 "tool completion artifact mismatch")
        return artifact

    async def _read_handoff(self, conn: Any, state: dict) -> dict:
        _require(state["recon"]["phase"] == "stopped", "runtime handoff not saved")
        reference = state["recon"]["handoff"]
        artifact = await self._read_artifact(conn, UUID(reference["artifact_id"]))
        _require(artifact["kind"] == HANDOFF_KIND and artifact["sha256"] == reference["sha256"], "handoff artifact mismatch")
        candidate = _object(artifact["content"])
        body = {key: value for key, value in candidate.items() if key != "handoff_ref"}
        _require(candidate["handoff_ref"] == "fixed-runtime-handoff:" + content_hash(canonical_json(body))
                 and candidate["runtime_plan_ref"] == state["recon"]["plan"]["plan_ref"]
                 and candidate["runtime_version"] == RUNTIME_VERSION
                 and candidate["business_profile"] == state["recon"]["plan"]["business_profile"]
                 and candidate["scope_hash"] == state["scope_hash"]
                 and candidate["completion_policy_ref"] == state["recon"]["plan"]["completion_policy_ref"],
                 "handoff content reference mismatch")
        return {"artifact": artifact, "candidate": candidate}

    async def _verify_observation(self, conn: Any, state: dict, saved: dict, observed_body: str) -> None:
        reference = saved["candidate"].get("unconfirmed_observation_ref")
        if reference is not None:
            prior = await self._read_artifact(conn, UUID(reference["artifact_id"]), saved["artifact"]["event_id"])
            record = _object(prior["content"])
            _require(prior["kind"] == OBSERVATION_KIND and prior["sha256"] == reference["sha256"]
                     and record["attempt_id"] == state["recon"]["plan"]["attempt_id"]
                     and record["tool_result_hash"] == content_hash(canonical_json(record["tool_result"]))
                     == content_hash(observed_body), "new observation differs; handoff frozen")
        else:
            original = await self._tool_artifact(conn, state)
            _require(original is not None and original["sha256"] == content_hash(observed_body),
                     "new observation cannot modify saved handoff")

    async def read_handoff(self, request: BusinessProfileRequest, *, observed_tool_output: dict | None = None) -> dict:
        observed_body = canonical_json(observed_tool_output) if observed_tool_output is not None else None
        async with self._locked() as (conn, _):
            state = await self._load(conn)
            await self._bound(conn, state, request)
            saved = await self._read_handoff(conn, state)
            if observed_body is not None:
                await self._verify_observation(conn, state, saved, observed_body)
        return {**saved, "state": state, "retention": "committed", "repeated": True}

    @staticmethod
    def _without_source(request: BusinessProfileRequest, *, stop: str | None, reason: str, references: list[str]) -> dict:
        result = evaluate_alert_recon(request, None, current_snapshot_ref=None, execution_stop=stop)
        result.pop("result_ref")
        result["schema"] = "fixed_runtime_unadopted_result.v1"
        for key in ("coverage_gaps", "blocking_gaps"):
            result[key] = sorted((set(result[key]) - {"committed_source_material_missing"}) | {reason})
        result.update(held_refs=sorted(set(references)), validated_source_refs=[], source_state="unverified",
                      stop_reason=stop or reason)
        result["handoff"]["next_step"] = "review_retained_runtime_material"
        result["result_ref"] = "unadopted-recon:" + content_hash(canonical_json(result))
        return result

    async def finalize(self, request: BusinessProfileRequest, *, observed_tool_output: dict | None = None) -> dict:
        observed_body = canonical_json(observed_tool_output) if observed_tool_output is not None else None
        async with self._locked() as (conn, _):
            state = await self._load(conn)
            await self._bound(conn, state, request)
            if state["recon"]["phase"] == "stopped":
                saved = await self._read_handoff(conn, state)
                if observed_body is not None:
                    await self._verify_observation(conn, state, saved, observed_body)
                result = {**saved, "state": state, "receipt": state["persistence"], "repeated": True}
            else:
                now = await conn.fetchval("SELECT clock_timestamp()")
                stop = observed_recon_stop(state, now=now)
                tool = await self._tool_artifact(conn, state)
                references = ["urn:uuid:" + state["persistence"]["state_artifact_id"], state["input_snapshot_ref"]]
                prepared, observation = None, None
                if tool is not None:
                    references.append("urn:uuid:" + str(tool["id"]))
                    if observed_body is not None:
                        _require(content_hash(observed_body) == tool["sha256"], "observation differs from committed output")
                    payload = _object(tool["content"])
                    material = CommittedMaterial(self.tenant_id, self.run_id, tool["id"],
                                                 content_hash(canonical_json(payload)), stored_sha256=tool["sha256"])
                    try:
                        prepared = prepare_alert_recon(request, payload, material, 1, execution_stop=stop)
                    except ValueError:
                        analysis = self._without_source(request, stop=stop, reason="source_material_rejected", references=references)
                    else:
                        analysis = prepared["result"]
                else:
                    if observed_body is not None:
                        _require(state["recon"]["plan"]["attempt_id"] in state["attempts"],
                                 "observation has no owned attempt")
                        observation_id = uuid4()
                        observation_body = canonical_json({"attempt_id": state["recon"]["plan"]["attempt_id"],
                            "provenance": "process_observation_not_original_completion", "tool_result": json.loads(observed_body),
                            "tool_result_hash": content_hash(observed_body)})
                        observation = {"artifact_id": str(observation_id), "sha256": content_hash(observation_body),
                                       "kind": OBSERVATION_KIND}
                        references.append("urn:uuid:" + str(observation_id))
                    reason = "tool_output_not_confirmed" if state["attempts"] else "query_not_started"
                    analysis = self._without_source(request, stop=stop, reason=reason, references=references)
                candidate = {"schema": "fixed_recon_runtime_handoff.v1", "runtime_version": RUNTIME_VERSION,
                    "runtime_plan_ref": state["recon"]["plan"]["plan_ref"],
                    "business_profile": state["recon"]["plan"]["business_profile"], "scope_hash": state["scope_hash"],
                    "completion_policy_ref": state["recon"]["plan"]["completion_policy_ref"],
                    "preparation": prepared, "result": analysis, "retained_artifact_refs": sorted(set(references)),
                    "unconfirmed_observation_ref": observation,
                    "execution": {"source_state_artifact_ref": "urn:uuid:" + state["persistence"]["state_artifact_id"],
                                  "stage_usage": state["stage_usage"], "run_total": state["run_total"],
                                  "cancellation_observed_at": state["recon"].get("cancellation_observed_at")}}
                candidate["handoff_ref"] = "fixed-runtime-handoff:" + content_hash(canonical_json(candidate))
                body, body_id = canonical_json(candidate), uuid4()
                updated, _ = finish_recon(state, artifact_id=body_id, body_hash=content_hash(body),
                                          execution_stop=stop, now=now)
                saved = await self._append(conn, updated, kind=CONTROL_KINDS[3], body=body, body_id=body_id,
                                           body_kind=HANDOFF_KIND, now=now)
                if observation is not None:
                    await self._insert_artifact(conn, artifact_id=UUID(observation["artifact_id"]),
                                                event_id=UUID(saved["receipt"]["event_id"]),
                                                kind=OBSERVATION_KIND, body=observation_body)
                result = {**saved, "candidate": candidate}
        return {**result, "retention": "committed"}  # after the owned transaction commits
