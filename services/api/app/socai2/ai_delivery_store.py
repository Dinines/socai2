"""Persist A/I delivery only after checking its actual saved request and original."""
from uuid import uuid4

from sqlalchemy import select, update

from .ai_stage_delivery import receive
from .baseline_context import reference
from .baseline_enrichment import S
from .baseline_store import StoreError, digest, encoded
from .citation_quality import new_review
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


async def save(store, run, stage_step, request_id, original_id, received):
    sources, originals = {}, []
    for aid, kind in ((request_id, "request"), (original_id, "response")):
        row = await store.one(select(F).where(*store.where(F, F.c.id == aid, F.c.run_id == run["id"])))
        body = row["content_json"] if row else None
        if (not row or row["material_state"] != "complete" or digest(body) != row["sha256"]
                or len(encoded(body)) != row["size_bytes"]):
            raise StoreError("stage_delivery_source_invalid", 422)
        sources[str(aid)] = body
        originals.append({"artifact_id": aid, "kind": kind, "sha256": row["sha256"]})
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
