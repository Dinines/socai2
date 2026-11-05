"""Persisted full-wire C6 allowance, within the new Run's shared limits."""
from .baseline_contracts import FULL_EXECUTOR_VERSION
from .baseline_store import StoreError, digest, encoded

FINAL_SECONDS = 30
FINAL_SOURCE_ENUM_BYTES = 4600
MAX_MESSAGE_BYTES = 12288
OUTPUT_TOKENS = 3000
MARGIN = 256


def final_reservation(gateway, context):
    from .baseline_delivery_contract import Delivery
    from .model_protocol import prepare_request
    from .structured_output import response_format
    # The source dictionary is the only part of the output schema that grows
    # after C3. Its explicit allowance is checked against the actual final wire;
    # no source or required value is removed to meet this allowance.
    body = prepare_request(gateway, {"model": getattr(gateway, "model", "") or "",
        "messages": [], "max_tokens": OUTPUT_TOKENS, "temperature": 0,
        "response_format": response_format(Delivery, ["reserved_source"], members=context.alerts,
            questions=[q.id for q in context.questions], objects=context.scope.object_keys)})
    envelope = len(encoded(body)) - len(encoded([])) - len(encoded(["reserved_source"]))
    request_bytes = envelope + MAX_MESSAGE_BYTES + FINAL_SOURCE_ENUM_BYTES
    return {"policy": "socai2.final-reservation.v1", "model_calls": 1,
        "request_bytes": request_bytes, "output_tokens": OUTPUT_TOKENS, "margin": MARGIN,
        "conservative_units": request_bytes + OUTPUT_TOKENS + MARGIN,
        "seconds": FINAL_SECONDS, "messages_bytes": MAX_MESSAGE_BYTES,
        "source_enum_bytes": FINAL_SOURCE_ENUM_BYTES,
        "limitations": ["required_final_input_must_still_fit_original_view_and_field_limits",
            "final_wire_checked_again_before_dispatch", "usage_remains_provider_reported_tokens"]}


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


def final_wire_reason(body, reservation):
    if not reservation:
        return None
    schema = body["text"]["format"]["schema"] if "text" in body else body["response_format"]["json_schema"]["schema"]
    sources = schema.get("$defs", {}).get("SourceId", {}).get("enum", [])
    if len(encoded(sources)) > reservation["source_enum_bytes"]:
        return "final_source_dictionary_exceeds_reserved_capacity"
    if len(encoded(body)) > reservation["request_bytes"]:
        return "final_wire_exceeds_reserved_capacity"
    return None
