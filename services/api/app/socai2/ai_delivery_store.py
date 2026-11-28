"""Persist A/I delivery only after checking its actual saved request and original."""
from uuid import uuid4

from sqlalchemy import select, update

from .ai_stage_delivery import receive
from .baseline_context import reference
from .baseline_enrichment import S, error
from .baseline_store import StoreError, digest, encoded
from .citation_quality import new_review
from .model_errors import INPUT_CONTRACT_REJECTED
from .model_protocol import response_choices, response_content_path
from .stage_delivery import VERSION, validate_sources
from .stage_results import F, R, artifact


def receive_payload(stage, payload, prepared, original_id, recorded, request):
    content, reason, finish, path = None, None, None, None
    try:
        choices = response_choices(payload)
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise StoreError("model_choices_invalid", 422)
        choice = choices[0]
        finish, message = choice.get("finish_reason"), choice.get("message")
        if finish not in {"stop", "length"}:
            raise StoreError("model_response_not_complete", 422)
        if (not isinstance(message, dict) or not isinstance(message.get("content"), str)
                or message.get("tool_calls") or message.get("function_call") or message.get("refusal")):
            raise StoreError("model_content_or_tool_protocol_invalid", 422)
        if recorded["usage_state"] != "reported":
            raise StoreError("model_usage_unknown_or_inconsistent", 422)
        if recorded["total_tokens"] > request["reserved_token_upper_bound"]:
            raise StoreError("provider_usage_exceeds_reservation", 422)
        content, path = message["content"], response_content_path(payload)
    except StoreError as exc:
        reason = exc.code
    received = receive(stage, content or "", prepared, original_id,
                       finish_reason=finish, **({"original_content_path": path} if path else {}))
    if content is None:
        received["parse"] = {"state": "unusable", "truncated": finish == "length", "reasons": [reason]}
        received["missing_units"] = [{"path": "$", "reason_code": reason}]
    if received["result"] is None and reason is None:
        reason = "stage_core_conclusion_unavailable"
    received.update(content=content, finish_reason=finish, rejection=reason)
    return received


async def saved_originals(store, run, items):
    sources, originals = {}, []
    for aid, kind in items:
        row = await store.one(select(F).where(*store.where(F, F.c.id == aid, F.c.run_id == run["id"])))
        body = row["content_json"] if row else None
        if (not row or row["material_state"] != "complete" or digest(body) != row["sha256"]
                or len(encoded(body)) != row["size_bytes"]):
            raise StoreError("stage_delivery_source_invalid", 422)
        sources[str(aid)] = body
        originals.append({"artifact_id": aid, "kind": kind, "sha256": row["sha256"]})
    return sources, originals


async def save_input_rejection(store, run, stage_step, model_step, request_id, schema):
    """The input guard ended locally without dispatch; this is not a provider answer."""
    return await save_local_failure(store, run, stage_step, model_step, request_id, schema,
        {"raw": None, "validation_error": INPUT_CONTRACT_REJECTED}, dispatched=False,
        retry_reason="input_guard_rejection_no_retry", quality_policy="input_guard_no_business_judgment")


async def save_envelope_failure(store, run, stage_step, model_step, request_id, schema, failure):
    """An actual HTTP response was received, but it is not a model JSON object."""
    if not failure.envelope_code:
        raise ValueError("received_envelope_failure_required")
    return await save_local_failure(store, run, stage_step, model_step, request_id, schema,
        failure.payload(), dispatched=True, parse_state="unusable",
        retry_reason="invalid_envelope_no_retry", quality_policy="invalid_envelope_no_business_judgment")


async def save_call_failure(store, run, stage_step, model_step, request_id, schema, failure):
    """Called only after the actual owned model call exits with an exception."""
    from .analysis_dispatch_types import (
        ExecutionFailure,
        classify_failure,
        model_dispatch_fact,
    )
    from .model_errors import ModelCallError
    if (isinstance(failure, ExecutionFailure) and failure.code == INPUT_CONTRACT_REJECTED
            and failure.not_executed and not failure.temporary):
        return await save_input_rejection(store, run, stage_step, model_step, request_id, schema)
    if isinstance(failure, ModelCallError) and failure.envelope_code:
        return await save_envelope_failure(store, run, stage_step, model_step, request_id, schema, failure)
    outcome = classify_failure(failure, stage="execute")
    payload = failure.payload() if isinstance(failure, ModelCallError) else {
        "raw": None, "transport_error": outcome.error_detail}
    return await save_local_failure(store, run, stage_step, model_step, request_id, schema,
        {**payload, "validation_error": outcome.error_code}, state=outcome.outcome,
        dispatched=model_dispatch_fact(failure))


async def save_local_failure(store, run, stage_step, model_step, request_id, schema, payload, *, dispatched,
        state="failed", parse_state="no_response", retry_reason="local_call_closed_no_automatic_replay",
        quality_policy="transport_receipt_no_business_judgment"):
    """Local end does not establish a remote result or authorize queue retries."""
    from .baseline_analysis_model import usage
    now, response_id, identity = await store.now(), uuid4(), uuid4()
    code = payload["validation_error"]
    recorded = usage(None)
    failure = {**error(code, now), "request_dispatched": dispatched}
    response = {"schema_version": schema, **payload, "request_dispatched": dispatched, "usage": recorded}
    await artifact(store, run, response_id, "model_response", response, now,
        [reference("artifact", request_id, "execution_receipt")], step_id=model_step, schema_version=schema)
    sources, originals = await saved_originals(store, run, ((request_id, "request"), (response_id, "response")))
    value = {"schema_version": VERSION, "type": "stage_delivery", "run_id": run["id"], "step_id": stage_step,
        "stage": "A" if run["kind"] == "alert_basic" else "I", "input_artifact_id": run["input_artifact_id"],
        "originals": originals, "execution": {"kind": "model", "call_state": state, "local_state": "ended",
            "local_ended_at": now, "request_dispatched": dispatched, "finish_reason": None,
            "error": error(code, now), "retry_allowed": False,
            "retry_reason": retry_reason},
        "parse": {"state": parse_state, "truncated": False, "reasons": [code]},
        "delivery": {"state": "none", "reasons": [code]}, "retained_units": [],
        "missing_units": [{"path": "$", "reason_code": code}], "invalid_units": [],
        "quality": {"policy": quality_policy,
            "state": "not_checked", "issues": [],
            "processing": [], "references": [], "prose_quality": "not_checked"},
        "use": {"material_paths": [], "dispatch_paths": [], "conclusion_available": False,
            "adoption_eligible": False, "comparison_eligible": False, "reasons": [code]}}
    value = validate_sources(value, sources).model_dump(mode="json")
    await artifact(store, run, identity, "source_snapshot", value, now,
        [reference("artifact", key, "execution_receipt") for key in sources], step_id=stage_step, schema_version=VERSION)
    await store.db.execute(update(S).where(*store.where(S, S.c.id == model_step, S.c.run_id == run["id"])).values(
        state=state, ended_at=now if state == "failed" else None, output_artifact_id=response_id, usage=recorded, error=failure))
    await store.db.execute(update(S).where(*store.where(S, S.c.id == stage_step, S.c.run_id == run["id"])).values(
        output_artifact_id=identity))
    await store.db.execute(update(R).where(*store.where(R, R.c.id == run["id"])).values(delivery_state="none",
        row_version=R.c.row_version + 1))
    return identity, value


async def save(store, run, stage_step, request_id, original_id, received):
    sources, originals = await saved_originals(store, run, ((request_id, "request"), (original_id, "response")))
    now = await store.now()
    quality = {k: received["quality"][k] for k in new_review()}
    value = {"schema_version": VERSION, "type": "stage_delivery", "run_id": run["id"], "step_id": stage_step,
        "stage": "A" if run["kind"] == "alert_basic" else "I", "input_artifact_id": run["input_artifact_id"],
        "originals": originals, "execution": {"kind": "model", "call_state": "completed", "local_state": "ended",
            "local_ended_at": now, "request_dispatched": True, "finish_reason": received["finish_reason"],
            "error": None, "retry_allowed": False, "retry_reason": "received_response_no_queue_retry"},
        **{k: received[k] for k in ("parse", "delivery", "retained_units", "missing_units", "invalid_units", "use")},
        "quality": quality}
    value = validate_sources(value, sources).model_dump(mode="json")
    identity = uuid4()
    await artifact(store, run, identity, "source_snapshot", value, now,
        [reference("artifact", request_id, "execution_receipt"), reference("artifact", original_id, "execution_receipt")],
        step_id=stage_step, schema_version=VERSION)
    await store.db.execute(update(S).where(*store.where(S, S.c.id == stage_step, S.c.run_id == run["id"])).values(output_artifact_id=identity))
    await store.db.execute(update(R).where(*store.where(R, R.c.id == run["id"])).values(delivery_state=value["delivery"]["state"],
        row_version=R.c.row_version + 1))
    if run["kind"] == "incident_diagnosis":
        from .subject_risk_opinions import save_candidate
        await save_candidate(store, run, stage_step, received)
    return identity, value
