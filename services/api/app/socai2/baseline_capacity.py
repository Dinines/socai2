"""Persisted full-wire C6 allowance, within the new Run's shared limits."""
from .baseline_contracts import FULL_EXECUTOR_VERSION
from .baseline_store import StoreError, digest, encoded
from .runtime_policy import (
    draft_limit as draft_limit,  # noqa: PLC0414 - shared limit re-export
)


def final_reservation(gateway, context, limits=None):
    from .runtime_policy import active_policy
    policy = active_policy()
    model = policy.model
    calls = min(model.final_reserved_calls, max(1, limits.max_model_calls - 1)) if limits else model.final_reserved_calls
    per_call = model.final_reserved_input_tokens + model.output_tokens["C6"] + model.tokenizer["safety_tokens"]
    return {"policy": "socai2.final-reservation.v2", "policy_sha256": policy.sha256,
        "model_calls": calls, "reserved_tokens": per_call * calls,
        "input_tokens_per_call": model.final_reserved_input_tokens, "output_tokens": model.output_tokens["C6"],
        "margin_tokens": model.tokenizer["safety_tokens"], "seconds": policy.final_reserve_seconds,
        "context_tokens": model.context_tokens,
        "limitations": ["minimum_final_allowance_not_a_fixed_message_byte_cap",
            "actual_final_request_measured_again_against_context_and_remaining_total",
            "correction_requires_remaining_call_time_and_token_allowances"]}


async def reservation_for(store, run, steps):
    if run["executor_version"] != FULL_EXECUTOR_VERSION:
        return None
    from sqlalchemy import select

    from .baseline_store import F
    plan = next((s for s in steps if s["stage_code"] == "C1.executor" and s["state"] == "completed"), None)
    if not plan:
        raise StoreError("final_reservation_missing")
    row = await store.one(select(F).where(*store.where(F, F.c.id == plan["output_artifact_id"], F.c.run_id == run["id"])))
    if not row or digest(row["content_json"]) != row["sha256"]:
        raise StoreError("final_reservation_invalid")
    return row["content_json"]["final_reservation"]


def remaining_seconds(limits, now, reservation=None, stage="C4"):
    seconds = (limits.deadline_at - now).total_seconds() if limits.deadline_at else 0
    return seconds - (reservation["seconds"] if reservation and stage != "C6" else 0)


def final_wire_reason(body, reservation, measurement=None):
    if not reservation:
        return None
    if reservation.get("policy") == "socai2.final-reservation.v2":
        return None if measurement and measurement["context_fits"] else "final_context_capacity_exceeded"
    # Retain inspection support for persisted legacy reservations.
    schema = body["text"]["format"]["schema"] if "text" in body else body["response_format"]["json_schema"]["schema"]
    sources = schema.get("$defs", {}).get("SourceId", {}).get("enum", [])
    if len(encoded(sources)) > reservation["source_enum_bytes"]:
        return "final_source_dictionary_exceeds_reserved_capacity"
    if len(encoded(body)) > reservation["request_bytes"]:
        return "final_wire_exceeds_reserved_capacity"
    return None
