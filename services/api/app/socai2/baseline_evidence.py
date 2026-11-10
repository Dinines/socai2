"""C4 material reads and deterministic queries on the existing baseline Run.

This is the execution primitive for a later question-level Deep loop, not that
loop itself. The caller selects a server-generated binding, never SQL/filters.
"""
import asyncio
from collections import Counter
from uuid import UUID, uuid4

from sqlalchemy import func, insert, null, select, update

from . import baseline_evidence_tools as tools
from .baseline_context import reference, retention_limit
from .baseline_contracts import Limits
from .baseline_enrichment import S, error
from .baseline_model_view import SYSTEM, blocked, draft_limit
from .baseline_optional_sources import SourceUnavailable
from .baseline_semantics import material_projection
from .baseline_store import RM, F, StoreError, digest, encoded

SCHEMA = "socai2.baseline-evidence.v1"


def citation_roles(payload):
    roles = {}
    if payload.get("type") == "materials":
        for aid, data in payload["members"].items():
            for i in range(len(data.get("fields", []))):
                roles[f"$.members.{aid}.fields.{i}"] = "observation"
    elif payload.get("type") == "query_projection":
        for i, row in enumerate(payload["rows"]):
            for j in range(len(row["semantics"]["fields"])):
                roles[f"$.rows.{i}.semantics.fields.{j}"] = payload.get("source_role", "observation")
    return roles


class BaselineEvidence:
    def __init__(self, service):
        self.service = service

    async def locked(self, store, case_id, run_id):
        await store.case(case_id)
        return await store.run(case_id, run_id)

    async def seq(self, store, run_id):
        return (await store.db.execute(select(func.coalesce(func.max(S.c.seq), 0)).where(
            *store.where(S, S.c.run_id == run_id)))).scalar_one() + 1

    async def artifact(self, store, run, payload, *, kind="source_snapshot", step=None, refs=None):
        identity = uuid4()
        if len(encoded(payload)) > retention_limit():
            raise StoreError("evidence_artifact_exceeds_retention_limit", 422)
        await store.save_input_artifact(run["case_id"], run["id"], identity, payload,
            kind=kind, schema=SCHEMA, captured_at=await store.now(), refs=refs or [],
            actor_id=run["requested_by"], step_id=step)
        return identity

    async def read_artifact(self, store, run_id, identity):
        row = await store.one(select(F).where(*store.where(F, F.c.id == identity, F.c.run_id == run_id)))
        if not row or digest(row["content_json"]) != row["sha256"]:
            raise StoreError("evidence_receipt_invalid")
        return row["content_json"]

    async def prepared(self, store, run):
        stage = await store.one(select(S).where(*store.where(S, S.c.run_id == run["id"],
            S.c.stage_code == "C4.materials", S.c.kind == "stage")))
        if not stage:
            raise StoreError("evidence_materials_not_prepared")
        return await self.read_artifact(store, run["id"], stage["output_artifact_id"]), stage["output_artifact_id"]

    async def prepare(self, tenant_id, case_id, run_id):
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            stage = await store.one(select(S).where(*store.where(S, S.c.run_id == run_id,
                S.c.stage_code == "C4.materials", S.c.kind == "stage")))
            if stage:
                value = await self.read_artifact(store, run_id, stage["output_artifact_id"])
                return {"artifact_id": str(stage["output_artifact_id"]), **value}
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            context = await store.read_context(case_id, run_id)
            members, refs = {}, []
            for aid, item in sorted(context.alerts.items()):
                if item.material:
                    mid = UUID(item.material["id"])
                    material = await store.read_material(case_id, run_id, mid)
                    members[aid] = material_projection(material)
                    refs.append(reference("alert_material", mid, "execution_receipt"))
                    # Indicates selected fields were read. The artifact explicitly
                    # distinguishes this from full raw review / model analysis.
                    await store.db.execute(update(RM).where(*store.where(RM,
                        RM.c.run_id == run_id, RM.c.alert_id == UUID(aid))).values(read_state="read"))
                else:
                    members[aid] = {"state": "unavailable", "fields": [],
                        "omissions": [{"source_path": None, "reason": "frozen_material_missing"}],
                        "limitations": ["no_fallback_to_latest_material"]}
            now, step = await store.now(), uuid4()
            value = {"schema_version": SCHEMA, "type": "materials", "run_id": str(run_id),
                "scope": context.scope.model_dump(mode="json"), "members": members,
                "catalog": tools.catalog(context, tenant_id), "captured_at": now.isoformat()}
            await store.db.execute(insert(S).values(id=step, tenant_id=tenant_id, run_id=run_id,
                seq=await self.seq(store, run_id), kind="stage", stage_code="C4.materials",
                state="running", name="frozen_material_semantics", implementation_version=SCHEMA, started_at=now))
            identity = await self.artifact(store, run, value, step=step, refs=refs)
            await store.db.execute(update(S).where(*store.where(S, S.c.id == step)).values(
                state="completed", ended_at=await store.now(), output_artifact_id=identity))
        return {"artifact_id": str(identity), **value}

    async def receipt(self, store, run, step):
        raw = await self.read_artifact(store, run["id"], step["output_artifact_id"])
        projected = (await store.db.execute(select(F.c.id, F.c.content_json, F.c.sha256).where(
            *store.where(F, F.c.run_id == run["id"], F.c.step_id == step["id"],
                         F.c.schema_version == SCHEMA, F.c.kind == "source_snapshot")))).mappings().all()
        if len(projected) != 1 or digest(projected[0]["content_json"]) != projected[0]["sha256"]:
            raise StoreError("evidence_projection_invalid")
        return {"step_id": str(step["id"]), "artifact_id": str(step["output_artifact_id"]),
            "projection_id": str(projected[0]["id"]), "result": raw, "projection": projected[0]["content_json"]}

    async def query(self, tenant_id, case_id, run_id, binding_id, question_id, gateway=None, *, parent_step_id=None):
        gateway = gateway or tools.LakeGateway(self.service)
        if isinstance(gateway, tools.LakeGateway) and gateway.service is None:
            gateway.service = self.service
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            context = await store.read_context(case_id, run_id)
            if question_id not in {q.id for q in context.questions}:
                raise StoreError("question_outside_frozen_scope", 422)
            prepared, prepared_id = await self.prepared(store, run)
            binding = prepared["catalog"]["bindings"].get(binding_id)
            if not binding or digest(binding) != binding_id:
                raise StoreError("tool_binding_outside_frozen_scope", 422)
            # Same contract + frozen scope + exact binding can only dispatch once.
            prior = await store.one(select(S).where(*store.where(S, S.c.run_id == run_id,
                S.c.stage_code == "C4.query", S.c.name == binding_id)))
            if prior:
                if prior["state"] in {"running", "unknown", "planned"}:
                    raise StoreError("evidence_query_already_claimed")
                return {**await self.receipt(store, run, prior), "reused": True}
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            steps = (await store.db.execute(select(S).where(*store.where(S, S.c.run_id == run_id)))).mappings().all()
            if parent_step_id:
                owner = next((s for s in steps if s["id"] == parent_step_id), None)
                if not owner or (owner["kind"], owner["stage_code"], owner["state"], owner["question_id"]) != (
                        "stage", "C4.deep", "running", question_id):
                    raise StoreError("query_owner_invalid")
            if any(s["id"] != parent_step_id and s["state"] in {"running", "unknown", "planned"} for s in steps):
                raise StoreError("baseline_step_in_progress")
            now, limits = await store.now(), Limits.model_validate(run["limits"])
            reason = None
            from .baseline_capacity import remaining_seconds, reservation_for
            reservation = await reservation_for(store, run, steps)
            remaining = remaining_seconds(limits, now, reservation)
            if binding["tool_name"] != "product_host_details" and (not context.scope.window_start or not context.scope.window_end):
                reason = "query_window_not_defined"
            elif (binding["tool_name"] != "product_host_details"
                    and context.scope.window_start >= context.scope.window_end):
                reason = "query_window_empty"
            elif hasattr(gateway, "unavailable_reason") and gateway.unavailable_reason(binding):
                reason = gateway.unavailable_reason(binding)
            elif not gateway.configured():
                reason = "lake_not_configured"
            elif limits.max_tool_calls is None or limits.max_rows_per_query is None or limits.deadline_at is None:
                reason = "execution_limits_not_defined"
            elif sum(s["kind"] == "tool" and s["state"] not in {"planned", "skipped"} for s in steps) >= limits.max_tool_calls or limits.max_rows_per_query == 0:
                reason = "tool_budget_exhausted"
            elif remaining < 1:
                reason = "final_model_time_reserved" if reservation else "insufficient_query_time"
            step_id, query_id = uuid4(), str(uuid4())
            args = {"tool_name": binding["tool_name"], "contract_version": tools.VERSION,
                "scope": binding["scope"], "limit": min(limits.max_rows_per_query or 0, 50),
                "parameters": {"tenant_id": str(tenant_id), "hostname": binding["hostname"],
                    "binding_id": binding_id, "alert_ids": binding["alert_ids"], "query_id": query_id}}
            if binding["tool_name"] == "product_host_details":
                args["parameters"]["case_id"] = str(case_id)
                args["parameters"].update({k: binding[k] for k in ("connector_id", "source_alert_id")})
            elif "source_database" in binding:
                args["parameters"]["source_database"] = binding["source_database"]
            await store.db.execute(insert(S).values(id=step_id, tenant_id=tenant_id, run_id=run_id,
                seq=await self.seq(store, run_id), kind="tool", stage_code="C4.query", question_id=question_id,
                parent_step_id=parent_step_id,
                name=binding_id, state="running" if reason is None else "planned",
                provider="crowdstrike_via_actions" if binding["tool_name"] == "product_host_details" else "clickhouse",
                implementation_version=tools.VERSION, started_at=now if reason is None else None, actual_args=args))
            refs = [reference("artifact", prepared_id, "execution_receipt")]
            request_id = await self.artifact(store, run, args, kind="tool_request", step=step_id, refs=refs)
            await store.db.execute(update(S).where(*store.where(S, S.c.id == step_id)).values(input_artifact_id=request_id))
            deadline = asyncio.get_running_loop().time() + remaining
        try:
            rows, state, observed, truncated, omitted = None, "skipped", None, False, []
            if reason is None and deadline - asyncio.get_running_loop().time() < 1:
                reason = "insufficient_query_time"
            if reason is None:
                # A local timeout cannot prove that the threaded CH query ended.
                # Uncertain transport/cancellation marks unknown and retains slot.
                try:
                    async with asyncio.timeout_at(deadline):
                        rows = await gateway.query(args, query_id, deadline - asyncio.get_running_loop().time())
                except SourceUnavailable as exc:
                    state, reason = "failed", str(exc)
            if reason is None:
                rows = tools.normalize_rows(rows)
                if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                    raise ValueError("invalid_lake_response")
                tools.validate_rows(rows, args)
                observed, truncated = len(rows), len(rows) > args["limit"]
                if truncated:
                    omitted.append("row_limit")
                rows = rows[:args["limit"]]
                if len(encoded(rows)) > retention_limit() // 2:
                    omitted.append("retained_row_bytes_limit")
                while rows and len(encoded(rows)) > retention_limit() // 2:
                    rows.pop()
                    truncated = True
                state = "completed"
            async with self.service.transaction(tenant_id) as store:
                run = await self.locked(store, case_id, run_id)
                if run["state"] != "running":
                    raise StoreError("baseline_not_running")
                captured = await store.now()
                raw = {"schema_version": SCHEMA, "tool_name": args["tool_name"], "contract_version": tools.VERSION,
                    "actual_args": args, "state": state, "rows": rows, "returned_rows": len(rows) if rows is not None else None,
                    "truncated": truncated, "query_id": query_id if state != "skipped" else None,
                    "error": error(reason, captured) if reason else None, "captured_at": captured.isoformat()}
                raw_id = await self.artifact(store, run, raw, kind="tool_response", step=step_id, refs=refs)
                projected = {"schema_version": SCHEMA, "type": "query_projection", "run_id": str(run_id),
                    "binding_id": binding_id, "question_id": question_id, "alert_ids": binding["alert_ids"],
                    "receipt_id": str(raw_id), "state": state, "reason": reason,
                    "observed_rows_in_bounded_fetch": observed, "truncated": truncated, "omissions": omitted,
                    "rows": [{"receipt_row": i, "semantics": tools.row_projection(row)} for i, row in enumerate(rows or [])],
                    "limitations": binding["limitations"], "captured_at": captured.isoformat()}
                if binding["tool_name"] == "product_host_details":
                    projected["source_role"] = "source_label"
                # Semantic projections are independently bounded; preserve raw rows.
                while projected["rows"] and len(encoded(projected)) > retention_limit():
                    projected["rows"].pop()
                    projected["truncated"] = True
                    if "semantic_projection_bytes_limit" not in projected["omissions"]:
                        projected["omissions"].append("semantic_projection_bytes_limit")
                await self.artifact(store, run, projected, step=step_id,
                    refs=[reference("artifact", raw_id, "execution_receipt")])
                await store.db.execute(update(S).where(*store.where(S, S.c.id == step_id)).values(
                    state=state, ended_at=captured, output_artifact_id=raw_id,
                    returned_rows=raw["returned_rows"], error=raw["error"] or null()))
                step = await store.one(select(S).where(*store.where(S, S.c.id == step_id)))
                receipt = await self.receipt(store, run, step)
            return {**receipt, "reused": False}
        except (Exception, asyncio.CancelledError):
            async with self.service.transaction(tenant_id) as store:
                await self.locked(store, case_id, run_id)
                await store.db.execute(update(S).where(*store.where(S, S.c.id == step_id,
                    S.c.state.in_(["running", "planned"]))).values(state="unknown",
                    error=error("evidence_dispatch_or_commit_uncertain", await store.now())))
                await store.mark_unknown(case_id, run_id)
            raise

    async def model_view(self, tenant_id, case_id, run_id, question_id):
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            context = await store.read_context(case_id, run_id)
            question = next((q for q in context.questions if q.id == question_id), None)
            if question is None:
                raise StoreError("question_outside_frozen_scope", 422)
            prepared, identity = await self.prepared(store, run)
            sources = [(identity, prepared)]
            artifacts = (await store.db.execute(select(F).where(*store.where(F, F.c.run_id == run_id,
                F.c.schema_version == SCHEMA, F.c.kind == "source_snapshot")).order_by(F.c.captured_at, F.c.id))).mappings().all()
            for a in artifacts:
                if digest(a["content_json"]) != a["sha256"]:
                    raise StoreError("evidence_receipt_invalid")
                if a["content_json"].get("type") == "query_projection":
                    sources.append((a["id"], a["content_json"]))
            data = {"scope": context.scope.model_dump(mode="json"), "question": question.model_dump(mode="json"),
                "coverage": {aid: {"selected_material_fields": len(d["fields"]), "model_fields": 0,
                    "material_omissions": dict(Counter(o["reason"] for o in d["omissions"]))} for aid, d in prepared["members"].items()},
                "queries": [{"artifact_id": str(sid), "state": s["state"], "reason": s["reason"],
                    "tool_name": prepared["catalog"]["bindings"][s["binding_id"]]["tool_name"],
                    "hostname": prepared["catalog"]["bindings"][s["binding_id"]]["hostname"],
                    "question_id": s["question_id"], "related_alert_ids": s["alert_ids"],
                    "window_start": s_scope["window_start"], "window_end": s_scope["window_end"],
                    "observed_rows_in_bounded_fetch": s["observed_rows_in_bounded_fetch"],
                    "truncated": s["truncated"], "omissions": s["omissions"], "limitations": s["limitations"]}
                    for sid, s in sources[1:] for s_scope in [prepared["catalog"]["bindings"][s["binding_id"]]["scope"]]],
                "items": [], "omission_counts": {}}
            ledger, source_map, counts = [], {}, Counter()
            candidates, groups = [], {}
            for sid, src in sources:
                for path, role in citation_roles(src).items():
                    bits = path.split(".")[1:]
                    item = src
                    for bit in bits:
                        item = item[int(bit)] if isinstance(item, list) else item[bit]
                    aids = [bits[1]] if src["type"] == "materials" else src["alert_ids"]
                    group = (str(sid), path.rsplit(".fields.", 1)[0])
                    group_index = groups.setdefault(group, len(groups))
                    candidates.append((int(bits[-1]), group_index, sid, path, aids, item, role))
            # Interleave records so earlier material cannot consume all space
            # before any newly queried row is represented. Omitted fields remain
            # explicit; this is not a claim that every row was fully analyzed.
            for _, group_index, sid, path, aids, item, role in sorted(candidates, key=lambda x: (x[0], x[1])):
                ref = reference("artifact", sid, role, path)
                why = "source_guard_blocked" if blocked(item) else None
                alias = "E" + str(len(source_map) + 1)
                entry = {"id": alias, "role": role, "related_alert_ids": aids,
                    "record_key": "R" + str(group_index + 1), **item}
                if why is None:
                    data["items"].append(entry)
                    if len(encoded(data)) > draft_limit() - 256:
                        data["items"].pop()
                        why = "model_view_budget_exhausted"
                if why:
                    counts[why] += 1
                    data["omission_counts"] = dict(counts)
                    ledger.append({"source": ref, "reason": why})
                else:
                    source_map[alias] = {"ref": ref, "record_key": entry["record_key"],
                        "related_alert_ids": aids, "visible_value_sha256": digest(item)}
                    for aid in aids:
                        data["coverage"][aid]["model_fields"] += 1
            messages = [{"role": "system", "content": SYSTEM + " 原始字段是来源报告的观察。related_alert_ids仅为查询绑定，不能当成该行属于全部告警；同一原始来源不重复计证。"},
                        {"role": "user", "content": encoded(data).decode()}]
            why = "mandatory_scope_exceeds_model_budget" if len(encoded(data)) > draft_limit() else None
            if why is None and (len(encoded(messages)) > draft_limit() or any(blocked(m["content"]) for m in messages)):
                why = "projected_message_guard_blocked"
            value = {"schema_version": SCHEMA, "type": "model_view", "question_id": question_id,
                "ready": why is None, "reason": why, "messages": messages if why is None else [],
                "source_map": source_map if why is None else {}, "omissions": ledger, "coverage": data["coverage"],
                "bytes": len(encoded(data)), "input_artifact_ids": [str(sid) for sid, _ in sources]}
            # Same evidence set and question reuses the exact stored view.
            prior = next((a for a in artifacts if a["content_json"] == value), None)
            if prior:
                return {"artifact_id": str(prior["id"]), **value}
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            view_id = await self.artifact(store, run, value,
                refs=[reference("artifact", sid, "execution_receipt") for sid, _ in sources])
        return {"artifact_id": str(view_id), **value}
