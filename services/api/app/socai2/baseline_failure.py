"""Settle known unsent calls without rewriting an uncertain execution."""
import json
from uuid import UUID, uuid4

from sqlalchemy import select, update

from app.models import socai2 as models

from .analysis_dispatch_types import ExecutionFailure, classify_failure


async def locally_ended(store, run_id, step):
    """An unknown remote call is idle only with its verified local end receipt."""
    from .baseline_store import F, StoreError, digest
    from .stage_delivery import VERSION, validate_sources
    if step["state"] != "unknown":
        return step["state"] not in {"running", "planned"}
    rows = (await store.db.execute(select(F).where(*store.where(F,
        F.c.run_id == run_id, F.c.step_id == step["id"], F.c.schema_version == VERSION,
        F.c.kind == "source_snapshot")))).mappings().all()
    if not rows:
        return False
    if len(rows) != 1 or digest(rows[0]["content_json"]) != rows[0]["sha256"]:
        raise StoreError("local_end_receipt_invalid")
    body = rows[0]["content_json"]
    originals = {}
    expected = {str(step["input_artifact_id"]): "request", str(step["output_artifact_id"]): "response"}
    if ({o.get("artifact_id"): o.get("kind") for o in body.get("originals", [])} != expected
            or len(body.get("originals", [])) != 2):
        raise StoreError("local_end_request_or_response_missing")
    for original in body.get("originals", []):
        row = await store.one(select(F).where(*store.where(F, F.c.run_id == run_id,
            F.c.step_id == step["id"], F.c.id == UUID(original["artifact_id"]))))
        if (row is None or digest(row["content_json"]) != row["sha256"]
                or row["kind"] != f'{step["kind"]}_{expected[original["artifact_id"]]}'):
            raise StoreError("local_end_original_invalid")
        originals[str(row["id"])] = row["content_json"]
    try:
        receipt = validate_sources(body, originals)
        if (receipt.run_id != run_id or receipt.step_id != step["id"]
                or receipt.stage != step["stage_code"] or receipt.execution.kind != step["kind"]
                or receipt.input_artifact_id != step["input_artifact_id"]
                or str(step["output_artifact_id"]) not in originals
                or receipt.execution.call_state != "unknown" or receipt.execution.retry_allowed
                or receipt.execution.local_ended_at < step["started_at"]):
            raise ValueError("local_end_identity_or_time_invalid")
    except (KeyError, ValueError, TypeError) as exc:
        raise StoreError("local_end_receipt_invalid") from exc
    return True


async def require_idle(store, run_id, steps=None, owner=None):
    from .baseline_store import StoreError
    table = models.RunSteps.__table__
    if steps is None:
        steps = (await store.db.execute(select(table).where(*store.where(table,
            table.c.run_id == run_id, table.c.state.in_(["running", "unknown", "planned"]))))).mappings().all()
    for step in steps:
        if step["id"] != owner and not await locally_ended(store, run_id, step):
            raise StoreError("baseline_step_in_progress")


async def local_receipt(store, run, step, request, response, *, code, dispatched, state="unknown", rows=None):
    """Called after the owned coroutine/worker has actually exited, never on dispatch."""
    from .baseline_context import reference
    from .baseline_store import digest
    from .stage_delivery import VERSION, validate_sources
    now, originals = await store.now(), {str(request[0]): request[1], str(response[0]): response[1]}
    units = []
    if rows:
        import hashlib
        text, pos, decoder = response[1]["received_rows_json"], 1, json.JSONDecoder()
        for index, row in enumerate(rows):
            while text[pos] in " ,\n\t":
                pos += 1
            value, end = decoder.raw_decode(text, pos)
            if value != row:
                raise ValueError("received_query_row_mismatch")
            units.append({"path": f"$.rows[{index}]", "kind": "query_record", "value": row,
                "original_artifact_id": str(response[0]), "original_content_path": "$.received_rows_json",
                "value_span": [pos, end], "value_sha256": hashlib.sha256(text[pos:end].encode()).hexdigest(),
                "declared_scope": request[1].get("scope"), "resolved_refs": [],
                "structure_state": "valid", "quality_issues": []})
            pos = end
    value = {"schema_version": VERSION, "type": "stage_delivery", "run_id": str(run["id"]),
        "step_id": str(step["id"]), "stage": step["stage_code"], "input_artifact_id": str(request[0]),
        "originals": [{"artifact_id": key, "kind": "request" if key == str(request[0]) else "response",
            "sha256": digest(body)} for key, body in originals.items()],
        "execution": {"kind": step["kind"], "call_state": state, "local_state": "ended",
            "local_ended_at": now.isoformat(), "request_dispatched": dispatched, "finish_reason": None,
            "error": {"code": code, "message": code, "retryable": False, "occurred_at": now.isoformat()},
            "retry_allowed": False, "retry_reason": "local_call_closed_no_automatic_replay"},
        "parse": {"state": "closed_units" if units else "no_response", "truncated": bool(units), "reasons": [code]},
        "delivery": {"state": "partial" if units else "none", "reasons": [code]}, "retained_units": units,
        "missing_units": [{"path": "$", "reason_code": "remote_result_not_complete"}], "invalid_units": [],
        "quality": {"policy": "transport_receipt_no_business_judgment", "state": "not_checked", "issues": [],
            "processing": [], "references": [], "prose_quality": "not_checked"},
        "use": {"material_paths": [u["path"] for u in units], "dispatch_paths": [],
            "conclusion_available": False, "adoption_eligible": False, "comparison_eligible": False, "reasons": [code]}}
    value = validate_sources(value, originals).model_dump(mode="json")
    identity = uuid4()
    await store.save_input_artifact(run["case_id"], run["id"], identity, value, kind="source_snapshot", schema=VERSION,
        captured_at=now, refs=[reference("artifact", key, "execution_receipt") for key in originals],
        actor_id=run["requested_by"], step_id=step["id"])
    return {"artifact_id": str(identity), "delivery": value["delivery"],
        "missing_units": value["missing_units"], "invalid_units": []}


async def accounted_steps(store, run_id, steps):
    """Unknown usage reserves the exact persisted request; it is not measured usage."""
    from .baseline_store import F, StoreError, digest
    result = []
    for step in steps:
        row = dict(step)
        if step["kind"] == "model" and step["state"] not in {"planned", "skipped"}:
            request = await store.one(select(F).where(*store.where(F, F.c.run_id == run_id,
                F.c.step_id == step["id"], F.c.id == step["input_artifact_id"], F.c.kind == "model_request")))
            if not request or digest(request["content_json"]) != request["sha256"]:
                raise StoreError("model_budget_request_invalid")
            payload = request["content_json"].get("payload", {})
            bound, meter = payload.get("reserved_token_upper_bound"), payload.get("token_measurement", {})
            if (type(bound) is int and bound > 0 and meter.get("reserved_total_tokens") == bound
                    and meter.get("body_sha256") == digest(payload.get("body"))):
                row["reserved_tokens"] = bound
            if ((step["error"] or {}).get("code") in {"model_schema_rejected", "service_unavailable"}
                    and (step["error"] or {}).get("request_dispatched") is False):
                row["not_executed"] = True
        result.append(row)
    return result


def unsent_failure(exc):
    outcome = classify_failure(exc, stage="execute")
    if (outcome.retryable and outcome.error_code == "service_unavailable"
            and (not isinstance(exc, ExecutionFailure) or exc.not_executed)):
        return outcome
    return None


async def settle_unsent(store, run, exc):
    """Call only while holding the Run lock; prior uncertain operations win."""
    outcome = unsent_failure(exc) if exc is not None else None
    if outcome is None or run["state"] != "running":
        return False
    steps, runs = models.RunSteps.__table__, models.Runs.__table__
    unsettled = await store.one(select(steps.c.id).where(*store.where(steps,
        steps.c.run_id == run["id"], steps.c.kind.in_(["model", "tool"]),
        steps.c.state.in_(["running", "unknown"]))).limit(1))
    if unsettled:
        return False
    now = await store.now()
    detail = {"code": outcome.error_code, "message": outcome.error_code,
              "retryable": True, "occurred_at": now.isoformat(), **outcome.error_detail}
    await store.db.execute(update(steps).where(*store.where(steps,
        steps.c.run_id == run["id"], steps.c.state == "running"))
        .values(state="failed", ended_at=now, error=detail))
    await store.db.execute(update(steps).where(*store.where(steps,
        steps.c.run_id == run["id"], steps.c.state == "planned"))
        .values(state="skipped", ended_at=now, error=detail))
    await store.db.execute(update(runs).where(*store.where(runs, runs.c.id == run["id"]))
        .values(state="failed", ended_at=now, stop_reason=outcome.error_code,
                stop_detail=json.dumps(outcome.error_detail), row_version=runs.c.row_version + 1))
    return True
