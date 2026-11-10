"""Shared model-step recording for Deep and post-evidence synthesis only."""
import asyncio
import copy
import json
from uuid import UUID, uuid4

from sqlalchemy import insert, null, select, update

from . import baseline_analysis_contract as analysis
from .baseline_analysis import budget_reason, reserved_calls
from .baseline_analysis_model import usage
from .baseline_capacity import final_wire_reason, remaining_seconds, reservation_for
from .baseline_context import reference, retention_limit
from .baseline_contracts import Limits
from .baseline_enrichment import S, error
from .baseline_evidence import BaselineEvidence
from .baseline_final_evidence import update_query_visibility
from .baseline_model_view import SYSTEM, blocked, draft_limit, field_limit
from .baseline_store import StoreError, digest, encoded
from .model_errors import ModelCallError
from .model_input_view import LIMITATIONS, compact, items, size, source_prefix
from .model_protocol import prepare_request, response_choices


def bounded_input(data, candidates, instruction):
    """Candidates carry the exact value the model will see, not a whole artifact."""
    data = {**data, "items": [], "omission_counts": {}, "view_limitations": LIMITATIONS}
    def messages_for(value):
        return [{"role": "system", "content": SYSTEM + "\n" + instruction},
                {"role": "user", "content": encoded(compact(value)).decode("utf-8")}]
    source_map, omitted = {}, []
    prefix = source_prefix([data, [c["original"] for c in candidates]])
    required_failed = False
    # Preserve each tier's order, but never let optional background crowd out
    # later mandatory feedback, paired judgments or received observations.
    for candidate in sorted(candidates, key=lambda c: not c.get("required", False)):
        why = "source_guard_blocked" if blocked(candidate["original"]) else None
        entry = {**candidate["entry"], "id": prefix + candidate["entry"]["id"]}
        if why is None and len(encoded(entry["value"])) > field_limit():
            why = "whole_field_exceeds_budget"
        if why is None:
            data["items"].append(entry)
            if size(data) > draft_limit() - 256 or len(encoded(messages_for(data))) > draft_limit() - 256:
                data["items"].pop()
                why = "model_view_budget_exhausted"
        if why:
            required_failed = required_failed or candidate.get("required", False)
            omitted.append({"ref": candidate["source"]["ref"], "reason": why})
            data["omission_counts"][why] = data["omission_counts"].get(why, 0) + 1
        else:
            source_map[entry["id"]] = {**candidate["source"], "visible_value_sha256": digest(entry["value"]),
                "required": candidate.get("required", False)}
    if "members" in data:
        for aid, member in data["members"].items():
            member["included"] = sum(aid in s["alert_ids"] for s in source_map.values())
    update_query_visibility(data, source_map)
    messages = messages_for(data)
    reason = "required_model_input_unavailable" if required_failed else "mandatory_scope_exceeds_model_budget" if size(data) > draft_limit() else None
    if reason is None and len(encoded(messages)) > draft_limit():
        reason = "mandatory_message_exceeds_budget"
    if reason is None and any(blocked(m["content"]) for m in messages):
        reason = "projected_message_guard_blocked"
    return {"ready": reason is None, "reason": reason, "messages": messages if reason is None else [],
        "source_map": source_map if reason is None else {}, "omissions": omitted,
        "coverage": data.get("members", {}), "bytes": size(data)}


def evidence_candidates(view, *, prefix="E"):
    data = json.loads(view["messages"][1]["content"])
    result = []
    for i, item in enumerate(data["items"], 1):
        source = view["source_map"][item["id"]]
        related = source["related_alert_ids"]
        # Only frozen material establishes direct member ownership. A host/time
        # lake row remains a related observation, not an attributed alert fact.
        basis = "frozen_material" if ".members." in source["ref"]["source_path"] else "query_binding_only"
        value = {k: v for k, v in item.items() if k not in {"id", "role", "related_alert_ids"}}
        result.append({"original": value, "entry": {"id": f"{prefix}{i}", "role": source["ref"]["role"],
            "alert_ids": related, "membership_basis": basis, "value": value},
            "source": {**source, "alert_ids": related, "membership_basis": basis}})
    return data, result


def fit_final_request(body, prepared, byte_limit):
    """Fit optional final input to the remaining reservation, never raise it.

    The caller's existing candidate order decides priority. Scope, questions,
    members and source states are mandatory. Removed values remain in their
    immutable artifacts and receive explicit request-level omission entries.
    """
    wire_messages = body["input"] if "input" in body else body["messages"]
    wire_schema = body["text"]["format"]["schema"] if "text" in body else body["response_format"]["json_schema"]["schema"]
    data = json.loads(wire_messages[1]["content"])
    grouped = "source_groups" in data
    data["items"] = items(data)
    data.pop("source_groups", None)
    while len(encoded(body)) > byte_limit and len(data["items"]) > 1:
        index = next((i for i in reversed(range(len(data["items"])))
            if not prepared["source_map"][data["items"][i]["id"]].get("required", False)), None)
        if index is None:
            break
        item = data["items"].pop(index)
        source = prepared["source_map"].pop(item["id"])
        prepared["omissions"].append({"ref": source["ref"], "reason": "remaining_final_token_budget"})
        counts = data.setdefault("omission_counts", {})
        counts["remaining_final_token_budget"] = counts.get("remaining_final_token_budget", 0) + 1
        for aid, member in data.get("members", {}).items():
            member["included"] = sum(aid in src["alert_ids"] for src in prepared["source_map"].values())
        update_query_visibility(data, prepared["source_map"])
        wire_messages[1]["content"] = encoded(compact(data) if grouped else data).decode()
        wire_schema["$defs"]["SourceId"]["enum"] = sorted(prepared["source_map"])
    prepared["coverage"] = data.get("members", {})


class ModelSteps(BaselineEvidence):
    def __init__(self, service, schema):
        super().__init__(service)
        self.schema = schema

    async def save(self, store, run, step, payload, kind, refs=()):
        if len(encoded(payload)) > retention_limit():
            raise StoreError("reasoning_artifact_exceeds_retention_limit", 422)
        identity = uuid4()
        await store.save_input_artifact(run["case_id"], run["id"], identity, payload, kind=kind,
            schema=self.schema, captured_at=await store.now(), refs=list(refs), actor_id=run["requested_by"], step_id=step)
        return identity

    async def idle(self, store, run_id, owner=None):
        rows = (await store.db.execute(select(S).where(*store.where(S, S.c.run_id == run_id,
            S.c.state.in_(["running", "unknown", "planned"]))))).mappings().all()
        if any(r["id"] != owner for r in rows):
            raise StoreError("baseline_step_in_progress")

    async def uncertain(self, tenant_id, case_id, run_id, stage_id):
        async with self.service.transaction(tenant_id) as store:
            await self.locked(store, case_id, run_id)
            await store.db.execute(update(S).where(*store.where(S, S.c.run_id == run_id,
                (S.c.id == stage_id) | (S.c.parent_step_id == stage_id), S.c.state.in_(["running", "planned"]))
            ).values(state="unknown", error=error("reasoning_dispatch_or_commit_uncertain", await store.now())))
            await store.mark_unknown(case_id, run_id)

    async def call(self, tenant_id, case_id, run_id, stage_id, stage_code, prepared, gateway, parser, *, output_format,
                   response_adapter=None, wire_transform=None, review=None, allow_correction=True):
        if not prepared["ready"]:
            return None, prepared["reason"], None, None
        if not await gateway.configure(self.service, tenant_id):
            return None, "model_not_configured", None, None
        from .runtime_policy import active_policy
        meter_stage = "C3" if stage_code in {"C3", "C3.reanalysis"} else "C6" if stage_code == "C6" else "Deep"
        body = {"model": gateway.model, "messages": prepared["messages"], "max_tokens": active_policy().model.output_tokens[meter_stage], "temperature": 0,
                "response_format": output_format}
        body = prepare_request(gateway, body)
        if wire_transform:
            body = wire_transform(body)
        # Count requests consume the same wall-clock allowance. In particular,
        # pre-final counting cannot eat into the final 300 seconds.
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            limits, now = Limits.model_validate(run["limits"]), await store.now()
            steps = (await store.db.execute(select(S).where(*store.where(S, S.c.run_id == run_id)))).mappings().all()
            reservation = await reservation_for(store, run, steps)
            reason = budget_reason(steps, limits, len(encoded(body)), now,
                reserve_calls=reserved_calls(run, stage_code), reservation=reservation if stage_code != "C6" else None)
            if reason != "token_measurement_missing":
                return None, reason, None, None
            meter_seconds = remaining_seconds(limits, now, reservation, stage_code)
        try:
            from .token_budget import measure_with_deadline
            measurement = await measure_with_deadline(gateway, body, meter_stage, meter_seconds)
        except StoreError as exc:
            return None, exc.code, None, None
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            await self.idle(store, run_id, stage_id)
            owner = await store.one(select(S).where(*store.where(S, S.c.id == stage_id,
                S.c.run_id == run_id, S.c.kind == "stage", S.c.state == "running")))
            if not owner or owner["stage_code"] != stage_code:
                raise StoreError("reasoning_owner_invalid")
            limits, now = Limits.model_validate(run["limits"]), await store.now()
            steps = (await store.db.execute(select(S).where(*store.where(S, S.c.run_id == run_id)))).mappings().all()
            reservation = await reservation_for(store, run, steps)
            reason = budget_reason(steps, limits, len(encoded(body)), now,
                reserve_calls=reserved_calls(run, stage_code), reservation=reservation if stage_code != "C6" else None,
                measurement=measurement)
            if reason is None and stage_code == "C6":
                reason = final_wire_reason(body, reservation, measurement)
            if reason:
                return None, reason, None, None
            model_id = uuid4()
            await store.db.execute(insert(S).values(id=model_id, tenant_id=tenant_id, run_id=run_id,
                seq=await self.seq(store, run_id), kind="model", stage_code=stage_code, parent_step_id=stage_id,
                question_id=owner["question_id"], state="running", name="bounded_reasoning_step",
                provider=gateway.provider, implementation_version=self.schema, started_at=now))
            request = {"schema_version": self.schema, "provider": gateway.provider, "model": gateway.model,
                "schema_profile": getattr(gateway, "schema_profile", "standard"),
                "direction": "request", "payload": {"body": body, "source_map": prepared["source_map"],
                    "binding_map": prepared.get("binding_map", {}), "input_artifact_ids": prepared["input_artifact_ids"],
                    "input_sha256": digest(prepared), "omissions": prepared["omissions"],
                    "reserved_token_upper_bound": measurement["reserved_total_tokens"], "token_measurement": measurement,
                    "final_reservation": reservation, "correction": prepared.get("correction"),
                    "input_view_id": prepared.get("input_view_id"),
                    "unoffered_bindings": prepared.get("unoffered_bindings", [])},
                "captured_at": now.isoformat(), "request_id": None, "usage": None}
            if "case_boundary" in prepared:
                request["payload"]["case_boundary"] = prepared["case_boundary"]
                request["payload"]["tool_presentation"] = prepared.get("tool_presentation")
            if "followup_boundary" in prepared:
                request["payload"]["followup_boundary"] = prepared["followup_boundary"]
            refs = [reference("artifact", UUID(i), "execution_receipt") for i in prepared["input_artifact_ids"]]
            request_id = await self.save(store, run, model_id, request, "model_request", refs)
            await store.db.execute(update(S).where(*store.where(S, S.c.id == model_id)).values(input_artifact_id=request_id))
            deadline = asyncio.get_running_loop().time() + remaining_seconds(limits, now, reservation, stage_code)
        try:
            async with asyncio.timeout_at(deadline):
                payload = await gateway.complete(body, max(0, deadline - asyncio.get_running_loop().time()))
        except ModelCallError as exc:
            async with self.service.transaction(tenant_id) as store:
                run = await self.locked(store, case_id, run_id)
                if run["state"] != "running":
                    raise StoreError("baseline_not_running")
                response = {"schema_version": self.schema, "provider": gateway.provider, "model": gateway.model,
                    "direction": "response", "payload": exc.payload(), "captured_at": (await store.now()).isoformat(),
                    "request_id": None, "usage": usage(None)}
                response_id = await self.save(store, run, model_id, response, "model_response",
                    [reference("artifact", request_id, "execution_receipt")])
                await store.db.execute(update(S).where(*store.where(S, S.c.id == model_id)).values(
                    output_artifact_id=response_id, usage=usage(None)))
                if exc.rejection_code:
                    now = await store.now()
                    await store.db.execute(update(S).where(*store.where(S, S.c.id == model_id)).values(
                        state="failed", ended_at=now, error=error(exc.rejection_code, now)))
            if exc.rejection_code:
                return None, exc.rejection_code, model_id, response_id
            raise
        recorded, parsed, reason, adaptation, content = usage(payload), None, None, None, None
        try:
            if recorded["usage_state"] != "reported":
                raise analysis.AnalysisRejected("model_usage_unknown_or_inconsistent")
            if recorded["total_tokens"] > measurement["reserved_total_tokens"]:
                raise analysis.AnalysisRejected("provider_usage_exceeds_reservation")
            choices = response_choices(payload)
            if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                raise analysis.AnalysisRejected("model_choices_invalid")
            msg = choices[0].get("message")
            if choices[0].get("finish_reason") != "stop":
                raise analysis.AnalysisRejected("model_response_not_complete")
            if (not isinstance(msg, dict) or msg.get("tool_calls") or msg.get("function_call") or msg.get("refusal")
                    or not isinstance(msg.get("content"), str)):
                raise analysis.AnalysisRejected("model_content_or_tool_protocol_invalid")
            content = msg["content"]
            if response_adapter is not None:
                content, adaptation = response_adapter(content)
            parsed = parser(content)
        except analysis.AnalysisRejected as exc:
            reason = str(exc)
        feedback = None
        if reason and content is not None and review is not None and allow_correction:
            try:
                feedback = review.feedback(content)
            except analysis.AnalysisRejected:
                pass
        if reason and content is not None and review is not None and not feedback:
            try:
                parsed = review.partial(content)
                prepared["validation_review"] = review.details
            except analysis.AnalysisRejected:
                pass
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            now = await store.now()
            response = {"schema_version": self.schema, "provider": gateway.provider, "model": gateway.model,
                "direction": "response", "payload": {"raw": payload, "validation_error": reason},
                "captured_at": now.isoformat(), "request_id": recorded["request_id"], "usage": recorded}
            if adaptation is not None:
                response["payload"]["output_adapter"] = adaptation
            if review and review.details:
                response["payload"]["validation_review"] = review.details
            if feedback:
                response["payload"]["correction_feedback"] = feedback
            response_id = await self.save(store, run, model_id, response, "model_response",
                [reference("artifact", request_id, "execution_receipt")])
            await store.db.execute(update(S).where(*store.where(S, S.c.id == model_id)).values(
                state="completed" if parsed else "failed", ended_at=now, output_artifact_id=response_id,
                usage=recorded, error=error(reason, now) if reason else null()))
        if feedback:
            corrected = copy.deepcopy(prepared)
            corrected["correction"] = {**feedback, "original_response_artifact_id": str(response_id)}
            corrected["input_artifact_ids"] = [*prepared["input_artifact_ids"], str(response_id)]
            corrected["messages"] += [{"role": "assistant", "content": content},
                {"role": "user", "content": encoded(feedback).decode()}]
            result = await self.call(tenant_id, case_id, run_id, stage_id, stage_code, corrected, gateway, parser,
                output_format=output_format, response_adapter=response_adapter, wire_transform=wire_transform,
                review=review, allow_correction=False)
            prepared["correction_result"] = {"original_response_artifact_id": str(response_id),
                "correction_response_artifact_id": str(result[3]) if result[3] else None,
                "reason": result[1], "dispatched": result[2] is not None}
            if corrected.get("validation_review"):
                prepared["validation_review"] = corrected["validation_review"]
            if result[0] is not None or corrected.get("validation_review"):
                return result
            # A skipped correction has no new model answer. Preserve useful
            # parts of the first reply, and record the concrete skip reason.
            try:
                parsed = review.partial(content)
                review.details["retained_response_artifact_id"] = str(response_id)
                prepared["validation_review"] = review.details
            except analysis.AnalysisRejected:
                pass
            if result[2] is not None:
                return parsed, result[1], model_id, response_id
        return parsed, reason, model_id, response_id
