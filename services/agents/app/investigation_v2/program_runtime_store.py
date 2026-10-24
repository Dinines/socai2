"""Owned manual program runtime transactions; no HTTP, models or publication."""
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
from .program_recon import evaluate_program_alert_recon, PREPARATION_SCHEMA, RESULT_SCHEMA
from .program_recon import prepare_program_alert_recon
from .program_runtime_state import (RUNTIME_VERSION, make_program_recon_plan, install_program_recon, claim_program_recon,
    validate_program_reservation, observed_program_stop, cancel_program_recon, finish_program_recon,
    policy_versions, HANDOFF_SCHEMA, UNADOPTED_RESULT_SCHEMA, _runtime_copy)

CONTROL_KINDS = ("unified_program_recon_started", "unified_program_recon_claimed", "unified_program_recon_cancelled",
                 "unified_program_recon_handoff_saved", "unified_program_recon_dispatch_blocked")
HANDOFF_KIND = "program_recon_handoff"
OBSERVATION_KIND = "program_recon_unconfirmed_observation"


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ExecutionRejected(reason)


class ProgramReconExecutionStore(ExecutionStore):
    event_kinds = (*KINDS, *CONTROL_KINDS)
    runtime_version = RUNTIME_VERSION
    event_agent = RUNTIME_VERSION

    async def _load(self, conn: Any) -> dict:
        state = await super()._load(conn)
        latest = await conn.fetchrow("SELECT id FROM investigation_events WHERE run_id=$1 AND tenant_id=$2 "
            "AND kind LIKE 'unified_%' ORDER BY seq DESC LIMIT 1", self.run_id, self.tenant_id)
        _require(latest is not None and str(latest["id"]) == state["persistence"]["event_id"],
                 "unknown latest managed event; fallback forbidden")
        event = await self._event(conn, UUID(state["persistence"]["event_id"]))
        await self._check_event_bodies(conn, event, state)
        _runtime_copy(state, datetime.fromisoformat(state["updated_at"]))
        return state

    async def _check_event_bodies(self, conn: Any, event: dict, state: dict) -> None:
        payload = _object(event["payload"])
        receipt = state["persistence"]
        _require(event["kind"] in self.event_kinds
                 and canonical_json(receipt) == canonical_json({k:v for k,v in payload.items() if k != "state_hash"})
                 and (receipt["event_id"], receipt["seq"], receipt["tenant_id"], receipt["run_id"], receipt["stage_id"])
                 == (str(event["id"]), event["seq"], str(self.tenant_id), str(self.run_id), state["stage_id"]),
                 "program event receipt mismatch")
        artifact = await self._read_artifact(conn, UUID(receipt["body_artifact_id"]), event["id"])
        expected_kind = {CONTROL_KINDS[0]: "unified_step_input", CONTROL_KINDS[3]: HANDOFF_KIND,
                         KINDS[1]: "unified_step_input", KINDS[2]: "unified_step_output"}.get(event["kind"], "program_recon_control")
        _require(artifact["kind"] == expected_kind and artifact["sha256"] == receipt["body_hash"]
                 and event["input_hash"] == (artifact["sha256"] if expected_kind == "unified_step_input" else None)
                 and event["output_hash"] == (artifact["sha256"] if expected_kind == "unified_step_output" else None),
                 "program event body pin mismatch")

    async def _origin(self, conn: Any, state: dict) -> dict:
        # A current self-consistent state is not its own original-input proof.
        beginnings = await conn.fetch("SELECT id,tenant_id,run_id,seq,kind,agent,payload,input_hash,output_hash "
            "FROM investigation_events WHERE run_id=$1 AND tenant_id=$2 AND kind=ANY($3::text[]) ORDER BY seq ASC LIMIT 2",
            self.run_id, self.tenant_id, [KINDS[0], "unified_recon_started", CONTROL_KINDS[0]])
        _require(len(beginnings) == 1, "unique owned program begin required")
        event = beginnings[0]
        _require((event["tenant_id"], event["run_id"], event["kind"], event["agent"])
                 == (self.tenant_id, self.run_id, CONTROL_KINDS[0], RUNTIME_VERSION), "program begin event identity mismatch")
        receipt = _object(event["payload"])
        body = await self._read_artifact(conn, UUID(receipt["body_artifact_id"]), event["id"])
        snapshot = await self._read_artifact(conn, UUID(receipt["state_artifact_id"]), event["id"])
        _require(body["kind"] == "unified_step_input" and body["sha256"] == receipt["body_hash"] == event["input_hash"]
                 and event["output_hash"] is None and snapshot["kind"] == "unified_state_snapshot"
                 and snapshot["sha256"] == receipt["state_hash"], "program begin artifact or event hash mismatch")
        initial = _object(snapshot["content"])
        _require(canonical_json(initial["persistence"]) == canonical_json({k:v for k,v in receipt.items() if k != "state_hash"})
                 and (receipt["event_id"], receipt["seq"], receipt["tenant_id"], receipt["run_id"], receipt["stage_id"], receipt["attempt_id"])
                 == (str(event["id"]), event["seq"], str(self.tenant_id), str(self.run_id), state["stage_id"], None),
                 "program begin receipt mismatch")
        _require((initial["tenant_id"], initial["run_id"], initial["executor_id"], initial["stage_id"])
                 == (str(self.tenant_id), str(self.run_id), str(self.executor_id), state["stage_id"]), "program origin identity mismatch")
        _runtime_copy(initial, datetime.fromisoformat(initial["updated_at"]))
        _runtime_copy(state, datetime.fromisoformat(state["updated_at"]))
        _require(initial["recon"]["phase"] == "ready" and not initial["attempts"]
                 and initial["input_hash"] == state["input_hash"] == body["sha256"]
                 and initial["input_snapshot_ref"] == state["input_snapshot_ref"] == "urn:uuid:" + str(body["id"]),
                 "program origin initial state mismatch")
        for key in ("scope", "scope_hash", "limits", "opening_usage"):
            _require(canonical_json(state[key]) == canonical_json(initial[key]), "program origin " + key + " changed")
        return _object(body["content"])

    async def _bound(self, conn: Any, state: dict, request: BusinessProfileRequest) -> None:
        _require(isinstance(request, BusinessProfileRequest), "checked business request required")
        frozen = await self._origin(conn, state)
        expected = make_program_recon_plan(request)
        _, sources = scope_snapshot(request.context)
        body = {"input": {"runtime_plan": expected, "business_profile": request.descriptor},
                "scope_sources": sources, "scope_hash": scope_fingerprint(request.context)}
        _require(canonical_json(frozen) == canonical_json(body)
                 and canonical_json(state["recon"]["plan"]) == canonical_json(expected), "program frozen input or plan mismatch")

    async def load(self) -> dict:
        async with self._locked() as (conn, _):
            state = await self._load(conn)
            await self._origin(conn, state)
        return state

    async def read_artifact(self, artifact_id: UUID | str) -> dict:
        async with self._locked() as (conn, _):
            state = await self._load(conn)
            await self._origin(conn, state)
            artifact = await self._read_artifact(conn, UUID(str(artifact_id)))
        return artifact

    async def begin_recon(self, *, request: BusinessProfileRequest, limits: BudgetLimits, opening: OpeningUsage,
                          parent_deadline: datetime | None = None) -> dict:
        plan = make_program_recon_plan(request)
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
            state = install_program_recon(state, request, now=now)
            state["legacy_run_snapshot"] = json.loads(canonical_json(run))
            saved = await self._append(conn, state, kind=CONTROL_KINDS[0], body=body, body_id=body_id,
                                       body_kind="unified_step_input", now=now)
        return saved

    async def claim(self, request: BusinessProfileRequest) -> dict:
        async with self._locked() as (conn, _):
            state = await self._load(conn)
            await self._bound(conn, state, request)
            now = await conn.fetchval("SELECT clock_timestamp()")
            updated, decision = claim_program_recon(state, now=now)
            if decision["needs_commit"]:
                body = canonical_json({"plan_ref": state["recon"]["plan"]["plan_ref"], "decision": decision})
                saved = await self._append(conn, updated, kind=CONTROL_KINDS[1], body=body, body_id=uuid4(),
                                           body_kind="program_recon_control", now=now)
            else:
                saved = {"state": state, "receipt": state["persistence"], "repeated": True}
        return {**saved, "decision": decision}

    async def reserve(self, *, scope_hash: str, input_data: Any, **request: Any) -> dict:
        body, body_id = canonical_json(input_data), uuid4()
        async with self._locked() as (conn, _):
            state = await self._load(conn)
            await self._origin(conn, state)
            _require(state["scope_hash"] == scope_hash, "caller scope differs from durable scope")
            now = await conn.fetchval("SELECT clock_timestamp()")
            validate_program_reservation(state, input_data=json.loads(body), request=request, now=now)
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
                updated = cancel_program_recon(state, now=now)
            updated["recon"]["cancellation_observed_at"] = now.isoformat(timespec="microseconds")
            updated["updated_at"] = now.isoformat(timespec="microseconds")
            saved = await self._append(conn, updated, kind=CONTROL_KINDS[2], body=canonical_json({"cancelled": True}),
                                       body_id=uuid4(), body_kind="program_recon_control", now=now)
        return saved

    async def mark_dispatch_block(self, request: BusinessProfileRequest, *, persistence_failure: bool) -> dict:
        _require(type(persistence_failure) is bool, "typed persistence observation required")
        async with self._locked() as (conn, _):
            state = await self._load(conn)
            await self._bound(conn, state, request)
            _require(state["recon"]["phase"] == "claimed", "dispatch block requires claimed runtime")
            now = await conn.fetchval("SELECT clock_timestamp()")
            stop = observed_program_stop(state, now=now)
            _require(stop is not None or persistence_failure, "dispatch invariant rejected without an observed stop")
            state["recon"].update(phase="blocked", stop_reason=stop or "retention_gap")
            state["updated_at"] = now.isoformat(timespec="microseconds")
            body = canonical_json({"dispatch_not_authorized": True, "persistence_failure": persistence_failure,
                                   "stop_reason": state["recon"]["stop_reason"]})
            saved = await self._append(conn, state, kind=CONTROL_KINDS[4], body=body, body_id=uuid4(),
                                       body_kind="program_recon_control", now=now)
        return saved

    async def _tool_artifact(self, conn: Any, state: dict) -> dict | None:
        attempt = state["attempts"].get(state["recon"]["plan"]["attempt_id"])
        if attempt is None or not attempt.get("completion_receipt"):
            return None
        receipt = attempt["completion_receipt"]
        event = await self._event(conn, UUID(receipt["event_id"]))
        payload = _object(event["payload"])
        _require(event["kind"] == KINDS[2] and event["output_hash"] == receipt["body_hash"]
                 and event["input_hash"] is None and payload["attempt_id"] == attempt["attempt_id"]
                 and canonical_json({k:v for k,v in payload.items() if k != "state_hash"}) == canonical_json(receipt),
                 "tool completion event pin mismatch")
        artifact = await self._read_artifact(conn, UUID(receipt["body_artifact_id"]), UUID(receipt["event_id"]))
        _require(artifact["kind"] == "unified_step_output" and artifact["sha256"] == receipt["body_hash"],
                 "tool completion artifact mismatch")
        return artifact

    async def _event(self, conn: Any, event_id: UUID) -> dict:
        event = await conn.fetchrow("SELECT id,tenant_id,run_id,seq,ts,kind,agent,payload,input_hash,output_hash "
            "FROM investigation_events WHERE id=$1 AND run_id=$2 AND tenant_id=$3", event_id, self.run_id, self.tenant_id)
        _require(event is not None and (event["tenant_id"], event["run_id"], event["agent"])
                 == (self.tenant_id, self.run_id, RUNTIME_VERSION), "owned program event required")
        return dict(event)

    async def _pinned_snapshot(self, conn: Any, artifact: dict) -> tuple[dict, dict]:
        event = await self._event(conn, artifact["event_id"])
        receipt = _object(event["payload"])
        _require(event["kind"] in self.event_kinds and artifact["kind"] == "unified_state_snapshot"
                 and str(artifact["id"]) == receipt["state_artifact_id"] and artifact["sha256"] == receipt["state_hash"],
                 "historical state event pin mismatch")
        state = _object(artifact["content"])
        _require(canonical_json(state["persistence"]) == canonical_json({k:v for k,v in receipt.items() if k != "state_hash"})
                 and (receipt["event_id"], receipt["seq"], receipt["tenant_id"], receipt["run_id"])
                 == (str(event["id"]), event["seq"], str(self.tenant_id), str(self.run_id)), "historical state receipt mismatch")
        await self._check_event_bodies(conn, event, state)
        await self._origin(conn, state)
        return state, event

    async def _read_handoff(self, conn: Any, state: dict, request: BusinessProfileRequest) -> dict:
        _require(state["recon"]["phase"] == "stopped", "runtime handoff not saved")
        reference = state["recon"]["handoff"]
        artifact = await self._read_artifact(conn, UUID(reference["artifact_id"]))
        _require(artifact["kind"] == HANDOFF_KIND and artifact["sha256"] == reference["sha256"], "handoff artifact mismatch")
        candidate = _object(artifact["content"])
        body = {key: value for key, value in candidate.items() if key != "handoff_ref"}
        _require(candidate["handoff_ref"] == "program-runtime-handoff:" + content_hash(canonical_json(body))
                 and candidate["runtime_plan_ref"] == state["recon"]["plan"]["plan_ref"]
                 and candidate["runtime_version"] == RUNTIME_VERSION
                 and canonical_json(candidate["business_profile"]) == canonical_json(state["recon"]["plan"]["business_profile"])
                 and candidate["scope_hash"] == state["scope_hash"]
                 and candidate["completion_policy_ref"] == state["recon"]["plan"]["completion_policy_ref"],
                 "handoff content reference mismatch")
        _require(candidate["schema"] == HANDOFF_SCHEMA and canonical_json(candidate["policy_versions"]) == canonical_json(policy_versions()),
                 "program handoff closed versions mismatch")
        preparation, result = candidate["preparation"], candidate["result"]
        if preparation is None:
            _require(result["schema"] == UNADOPTED_RESULT_SCHEMA and result["validated_source_refs"] == []
                     and not result["facts"] and result["scope_readiness"] == "partial"
                     and result["source_state"] == "not_confirmed" and result["source_available"] is None
                     and result["execution_state"] == "unknown", "unadopted program handoff mismatch")
            prefix = "program-runtime-unadopted:"
        else:
            _require(preparation["schema"] == PREPARATION_SCHEMA and result["schema"] == RESULT_SCHEMA
                     and preparation["material_state"] == "program_material_validated"
                     and canonical_json(preparation["result"]) == canonical_json(result)
                     and preparation["program_material_snapshot_ref"] == result["snapshot_ref"]
                     == preparation["program_material_document"]["snapshot_ref"], "validated program handoff mismatch")
            _require(preparation["preparation_ref"] == "program-recon-preparation:" + content_hash(canonical_json(
                {k:v for k,v in preparation.items() if k != "preparation_ref"})), "program preparation reference mismatch")
            prefix = "program-recon:"
        _require(result["result_ref"] == prefix + content_hash(canonical_json({k:v for k,v in result.items() if k != "result_ref"})),
                 "program result reference mismatch")
        # Re-read the exact pre-handoff state and its original completion. A
        # self-rehashed candidate is not evidence that these bodies still exist.
        event = await self._event(conn, artifact["event_id"])
        receipt = _object(event["payload"])
        _require(event["kind"] == CONTROL_KINDS[3] and receipt["body_artifact_id"] == str(artifact["id"])
                 and receipt["body_hash"] == artifact["sha256"] and event["input_hash"] is None
                 and event["output_hash"] is None, "handoff event pin mismatch")
        source_ref = candidate["execution"]["source_state_artifact_ref"]
        _require(isinstance(source_ref, str) and source_ref.startswith("urn:uuid:"), "source state reference required")
        source_artifact = await self._read_artifact(conn, UUID(source_ref.removeprefix("urn:uuid:")))
        source, source_event = await self._pinned_snapshot(conn, source_artifact)
        previous = await conn.fetchrow("SELECT id FROM investigation_events WHERE run_id=$1 AND tenant_id=$2 "
            "AND kind LIKE 'unified_%' AND seq<$3 ORDER BY seq DESC LIMIT 1", self.run_id, self.tenant_id, event["seq"])
        _require(previous is not None and previous["id"] == source_event["id"] and source["recon"]["phase"] != "stopped"
                 and source["recon"]["plan"] == state["recon"]["plan"], "pre-handoff source state mismatch")
        stop = observed_program_stop(source, now=event["ts"])
        closing_artifact = await self._read_artifact(conn, UUID(receipt["state_artifact_id"]), event["id"])
        closing, _ = await self._pinned_snapshot(conn, closing_artifact)
        expected_closing, _ = finish_program_recon(source, artifact_id=artifact["id"], body_hash=artifact["sha256"],
                                                  execution_stop=stop, now=event["ts"])
        expected_closing["persistence"] = closing["persistence"]
        _require(canonical_json(expected_closing) == canonical_json(closing)
                 and canonical_json(state["recon"]) == canonical_json(closing["recon"]),
                 "saved handoff state or current stopped control mismatch")
        tool = await self._tool_artifact(conn, source)
        references = [source_ref, source["input_snapshot_ref"]]
        expected_preparation, observation = None, candidate["unconfirmed_observation_ref"]
        if tool is not None:
            _require(observation is None, "confirmed completion cannot be an observer")
            references.append("urn:uuid:" + str(tool["id"]))
            try:
                payload = _object(tool["content"])
                material = CommittedMaterial(self.tenant_id, self.run_id, tool["id"], content_hash(canonical_json(payload)),
                                             stored_sha256=tool["sha256"])
                expected_preparation = prepare_program_alert_recon(request, payload, material, 1, execution_stop=stop)
            except ValueError:
                expected_result = self._without_source(request, stop=stop, reason="source_material_rejected", references=references)
            else:
                expected_result = expected_preparation["result"]
        else:
            if observation is not None:
                prior = await self._read_artifact(conn, UUID(observation["artifact_id"]), artifact["event_id"])
                record = _object(prior["content"])
                _require(source["recon"]["plan"]["attempt_id"] in source["attempts"]
                         and observation == {"artifact_id": str(prior["id"]), "sha256": prior["sha256"], "kind": OBSERVATION_KIND}
                         and prior["kind"] == OBSERVATION_KIND and record["attempt_id"] == source["recon"]["plan"]["attempt_id"]
                         and record["provenance"] == "process_observation_not_original_completion"
                         and record["tool_result_hash"] == content_hash(canonical_json(record["tool_result"])),
                         "unconfirmed observer event or provenance mismatch")
                references.append("urn:uuid:" + str(prior["id"]))
            reason = "tool_output_not_confirmed" if source["attempts"] else "query_not_started"
            expected_result = self._without_source(request, stop=stop, reason=reason, references=references)
        expected = {"schema": HANDOFF_SCHEMA, "runtime_version": RUNTIME_VERSION, "policy_versions": policy_versions(),
            "runtime_plan_ref": source["recon"]["plan"]["plan_ref"], "business_profile": source["recon"]["plan"]["business_profile"],
            "scope_hash": source["scope_hash"], "completion_policy_ref": source["recon"]["plan"]["completion_policy_ref"],
            "preparation": expected_preparation, "result": expected_result, "retained_artifact_refs": sorted(set(references)),
            "unconfirmed_observation_ref": observation, "execution": {"source_state_artifact_ref": source_ref,
            "stage_usage": source["stage_usage"], "run_total": source["run_total"],
            "cancellation_observed_at": source["recon"].get("cancellation_observed_at")}}
        _require(canonical_json(expected) == canonical_json(body), "handoff differs from retained original sources")
        return {"artifact": artifact, "candidate": candidate}

    async def _verify_observation(self, conn: Any, state: dict, saved: dict, observed_body: str) -> None:
        reference = saved["candidate"].get("unconfirmed_observation_ref")
        if reference is not None:
            prior = await self._read_artifact(conn, UUID(reference["artifact_id"]), saved["artifact"]["event_id"])
            record = _object(prior["content"])
            _require(prior["kind"] == OBSERVATION_KIND and prior["sha256"] == reference["sha256"]
                     and record["provenance"] == "process_observation_not_original_completion"
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
            saved = await self._read_handoff(conn, state, request)
            if observed_body is not None:
                await self._verify_observation(conn, state, saved, observed_body)
        return {**saved, "state": state, "retention": "committed", "repeated": True}

    @staticmethod
    def _without_source(request: BusinessProfileRequest, *, stop: str | None, reason: str, references: list[str]) -> dict:
        _require(reason in {"source_material_rejected", "tool_output_not_confirmed", "query_not_started"}, "unsupported unadopted reason")
        result = evaluate_program_alert_recon(request, None, current_snapshot_ref=None, execution_stop=stop)
        result.pop("result_ref")
        result["schema"] = UNADOPTED_RESULT_SCHEMA
        for key in ("coverage_gaps", "blocking_gaps"):
            result[key] = sorted((set(result[key]) - {"committed_source_material_missing"}) | {reason})
        result.update(held_refs=sorted(set(result["held_refs"]) | set(references)), validated_source_refs=[],
                      material_adoption_reason=reason, stop_reason=stop or reason)
        result["handoff"]["next_step"] = "review_retained_runtime_material"
        result["result_ref"] = "program-runtime-unadopted:" + content_hash(canonical_json(result))
        return result

    async def finalize(self, request: BusinessProfileRequest, *, observed_tool_output: dict | None = None) -> dict:
        observed_body = canonical_json(observed_tool_output) if observed_tool_output is not None else None
        async with self._locked() as (conn, _):
            state = await self._load(conn)
            await self._bound(conn, state, request)
            if state["recon"]["phase"] == "stopped":
                saved = await self._read_handoff(conn, state, request)
                if observed_body is not None:
                    await self._verify_observation(conn, state, saved, observed_body)
                result = {**saved, "state": state, "receipt": state["persistence"], "repeated": True}
            else:
                now = await conn.fetchval("SELECT clock_timestamp()")
                stop = observed_program_stop(state, now=now)
                tool = await self._tool_artifact(conn, state)
                references = ["urn:uuid:" + state["persistence"]["state_artifact_id"], state["input_snapshot_ref"]]
                prepared, observation = None, None
                if tool is not None:
                    references.append("urn:uuid:" + str(tool["id"]))
                    if observed_body is not None:
                        _require(content_hash(observed_body) == tool["sha256"], "observation differs from committed output")
                    try:
                        payload = _object(tool["content"])
                        material = CommittedMaterial(self.tenant_id, self.run_id, tool["id"],
                                                     content_hash(canonical_json(payload)), stored_sha256=tool["sha256"])
                        prepared = prepare_program_alert_recon(request, payload, material, 1, execution_stop=stop)
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
                candidate = {"schema": HANDOFF_SCHEMA, "runtime_version": RUNTIME_VERSION, "policy_versions": policy_versions(),
                    "runtime_plan_ref": state["recon"]["plan"]["plan_ref"],
                    "business_profile": state["recon"]["plan"]["business_profile"], "scope_hash": state["scope_hash"],
                    "completion_policy_ref": state["recon"]["plan"]["completion_policy_ref"],
                    "preparation": prepared, "result": analysis, "retained_artifact_refs": sorted(set(references)),
                    "unconfirmed_observation_ref": observation,
                    "execution": {"source_state_artifact_ref": "urn:uuid:" + state["persistence"]["state_artifact_id"],
                                  "stage_usage": state["stage_usage"], "run_total": state["run_total"],
                                  "cancellation_observed_at": state["recon"].get("cancellation_observed_at")}}
                candidate["handoff_ref"] = "program-runtime-handoff:" + content_hash(canonical_json(candidate))
                body, body_id = canonical_json(candidate), uuid4()
                updated, _ = finish_program_recon(state, artifact_id=body_id, body_hash=content_hash(body),
                                          execution_stop=stop, now=now)
                saved = await self._append(conn, updated, kind=CONTROL_KINDS[3], body=body, body_id=body_id,
                                           body_kind=HANDOFF_KIND, now=now)
                if observation is not None:
                    await self._insert_artifact(conn, artifact_id=UUID(observation["artifact_id"]),
                                                event_id=UUID(saved["receipt"]["event_id"]),
                                                kind=OBSERVATION_KIND, body=observation_body)
                result = {**saved, "candidate": candidate}
        return {**result, "retention": "committed"}  # after the owned transaction commits
