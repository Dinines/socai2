"""C3 unit delivery and at most one supplement, on the existing Run and budget."""
import copy
from uuid import UUID, uuid4

from sqlalchemy import select

from . import case_c3_completion as completion
from . import case_c3_delivery as units
from .baseline_analysis_contract import AnalysisRejected
from .baseline_context import reference
from .baseline_enrichment import S, error
from .baseline_execution_schema import compact_execution_wire
from .baseline_reasoning import ModelSteps
from .baseline_store import F, StoreError, digest
from .stage_delivery import VERSION, validate_sources


async def originals_for(service, steps, tenant, case_id, run_id, model_id, response_id):
    if model_id is None:
        return None, {}, None
    async with service.transaction(tenant) as store:
        await steps.locked(store, case_id, run_id)
        model = await store.one(select(S).where(*store.where(S, S.c.run_id == run_id, S.c.id == model_id)))
        if not model or model["state"] not in {"completed", "failed"}:
            raise StoreError("c3_model_receipt_not_terminal")

        async def read(identity):
            row = await store.one(select(F).where(*store.where(F, F.c.run_id == run_id, F.c.id == UUID(str(identity)))))
            if row is None or digest(row["content_json"]) != row["sha256"]:
                raise StoreError("c3_completion_artifact_invalid")
            return row["content_json"]

        request_id = str(model["input_artifact_id"])
        originals = {request_id: await read(request_id)}
        response = await read(response_id)
        original_id = (response["payload"].get("citation_review") or {}).get("original_response_artifact_id")
        if original_id:
            original = await read(original_id)
            if (original["raw"] != response["payload"].get("raw")
                    or original["request_artifact_id"] != request_id):
                raise StoreError("c3_completion_original_mismatch")
            originals[original_id] = original
        return model, originals, originals[request_id]["payload"]


async def complete_sections(service, tenant, case_id, run_id, stage_id, prepared, context, bindings,
                            fmt, gateway, initial, *, schema):
    _, reason, model_id, response_id = initial
    steps = ModelSteps(service, schema)
    first, originals, request = await originals_for(service, steps, tenant, case_id, run_id, model_id, response_id)
    received = prepared.get("unit_delivery")
    if received is None:
        received = units.receive("", prepared, context, bindings, None)
        received["parse"].update(state="no_response" if not originals or not prepared["citation_review"].get(
            "original_response_artifact_id") else "unusable", reasons=[reason or "response_not_admitted"])
    policy = prepared["case_boundary"]["c3_completion"]
    completion.validate_policy(policy, frozen=True)
    missing = units.completion_fields(received)
    record = {"schema_version": schema, "type": "c3_section_completion", "version": completion.VERSION,
        "initial_response_artifact_id": str(response_id) if response_id else None,
        "initial_reason": reason, "initial_delivery": copy.deepcopy(received["delivery"]),
        "initial_missing_units": copy.deepcopy(received["missing_units"]),
        "initial_invalid_units": copy.deepcopy(received["invalid_units"]),
        "state": "not_needed", "attempts": 0, "missing_fields": missing}
    if missing:
        if policy["max_attempts"] == 0:
            record.update(state="disabled", reason="c3_supplement_disabled")
        elif request is None or "unit_delivery" not in prepared:
            record.update(state="skipped", reason=reason or "initial_response_not_admitted")
        else:
            try:
                extra = completion.prepare_units(prepared, request, received, missing, str(response_id))
                async with service.transaction(tenant) as store:
                    run = await steps.locked(store, case_id, run_id)
                    plan_id = await steps.save(store, run, stage_id, {**record, "state": "ready"}, "source_snapshot",
                        [reference("artifact", response_id, "execution_receipt")])
                extra["section_completion"]["plan_artifact_id"] = str(plan_id)
                extra["input_artifact_ids"].append(str(plan_id))
                _, failure, second_id, second_response = await steps.call(
                    tenant, case_id, run_id, stage_id, "C3", extra, gateway,
                    units.parser(extra, context, bindings, prefix="$.supplement", prior_analysis=received["analysis"]),
                    output_format=completion.unit_format(fmt, received, missing),
                    wire_transform=compact_execution_wire, allow_correction=False)
                record.update(attempts=int(second_id is not None), reason=failure,
                    supplement_response_artifact_id=str(second_response) if second_response else None)
                _, more, _ = await originals_for(service, steps, tenant, case_id, run_id, second_id, second_response)
                originals.update(more)
                supplement = extra.get("unit_delivery")
                if supplement is not None:
                    received = units.combine(received, supplement, missing, prepared, context, bindings)
                    record.update(state="completed" if received["delivery"]["state"] == "complete" else "incomplete",
                        supplement_delivery=copy.deepcopy(supplement["delivery"]))
                else:
                    record.update(state="failed" if second_id else "skipped")
            except AnalysisRejected as exc:
                record.update(state="skipped", reason=str(exc))
    record["final_delivery"] = copy.deepcopy(received["delivery"])
    record["remaining_fields"] = units.completion_fields(received)
    # Raw replies and model steps remain separate. This receipt describes what
    # C3 can actually hand to downstream stages, not a fabricated complete reply.
    async with service.transaction(tenant) as store:
        run = await steps.locked(store, case_id, run_id)
        now = await store.now()
        refs = [reference("artifact", identity, "execution_receipt") for identity in originals]
        outcome_id = await steps.save(store, run, stage_id, record, "source_snapshot", refs)
        receipt = {"schema_version": VERSION, "type": "stage_delivery", "run_id": str(run_id),
            "step_id": str(stage_id), "stage": "C3", "input_artifact_id": prepared["input_view_id"],
            "originals": [{"artifact_id": identity, "kind": "response" if body.get("type") == "model_original_response"
                           else "request", "sha256": digest(body)} for identity, body in originals.items()],
            "execution": {"kind": "model", "call_state": first["state"] if first else "skipped",
                "local_state": "ended", "local_ended_at": now.isoformat(), "request_dispatched": bool(first),
                "finish_reason": prepared.get("received_finish_reason"),
                "error": error(reason, now) if reason else None,
                "retry_allowed": False, "retry_reason": "bounded_supplement_finished_or_not_available"},
            **{key: received[key] for key in ("parse", "delivery", "retained_units", "missing_units",
                                             "invalid_units", "quality", "use")}}
        receipt = validate_sources(receipt, originals).model_dump(mode="json")
        identity = uuid4()
        await store.save_input_artifact(case_id, run_id, identity, receipt, kind="source_snapshot",
            schema=VERSION, captured_at=now, refs=refs, actor_id=run["requested_by"], step_id=stage_id)
    prepared["stage_delivery_result"] = units.summary(received, identity)
    prepared["section_completion_result"] = {**record, "artifact_id": str(outcome_id)}
    # Keep original pointers; refresh diagnostics against the final unit set.
    prepared["citation_review"].update(received["quality"])
    prepared["citation_review"]["stage_delivery_artifact_id"] = str(identity)
    analysis = units.RetainedAnalysis(received["analysis"]) if received["retained_units"] else None
    return analysis, None, model_id, identity
