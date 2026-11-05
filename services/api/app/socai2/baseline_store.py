"""Transactional Case baseline persistence for the new socai2 schema.

Opt-in only: no legacy writer, scheduler, HTTP route, or executor is registered.
All methods use the caller's transaction. Lock order is Case -> Run. Do not
perform model/Tool I/O until the claim transaction has committed.
"""
import hashlib
import json
from uuid import UUID, uuid4

from sqlalchemy import delete, func, insert, null, select, text, update

from app.models import socai2 as models

from . import baseline_context as c1
from .baseline_contracts import Actor, Claim, Limits, Publication, Start

C = models.Cases.__table__
CA = models.CaseAlerts.__table__
A = models.Alerts.__table__
R = models.Runs.__table__
RM = models.RunMembers.__table__
F = models.Artifacts.__table__
RES = models.Results.__table__
RESM = models.ResultMembers.__table__
ACT = models.Activities.__table__
TGT = models.ActivityTargets.__table__


class StoreError(Exception):
    def __init__(self, code: str, status: int = 409):
        self.code, self.status = code, status
        super().__init__(code)


def encoded(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


class BaselineStore:
    def __init__(self, db, tenant_id: UUID):
        self.db, self.tenant_id = db, tenant_id

    def where(self, table, *clauses):
        return (table.c.tenant_id == self.tenant_id, *clauses)

    async def one(self, statement):
        return (await self.db.execute(statement)).mappings().one_or_none()

    async def now(self):
        # Use the same database clock as assessment adoption. Application-host
        # clock skew must not reorder a newer human decision around a Run start.
        return (await self.db.execute(select(func.clock_timestamp()))).scalar_one()

    async def case(self, case_id, *, lock=True):
        q = select(C).where(*self.where(C, C.c.id == case_id))
        row = await self.one(q.with_for_update() if lock else q)
        if row is None:
            raise StoreError("case_not_found", 404)
        return row

    async def run(self, case_id, run_id):
        row = await self.one(select(R).where(*self.where(
            R, R.c.case_id == case_id, R.c.id == run_id, R.c.kind == "baseline"
        )).with_for_update())
        if row is None:
            raise StoreError("baseline_not_found", 404)
        return row

    async def members(self, case_id):
        return set((await self.db.execute(select(CA.c.alert_id).where(*self.where(
            CA, CA.c.case_id == case_id
        )))).scalars())

    async def event(self, case_id, operation_id, actor, action, detail, targets):
        aid = uuid4()
        targets = list(targets)
        case_target = next((i for i, t in enumerate(targets) if t[0] == "case_id"), None)
        if case_target is None:
            targets.append(("case_id", case_id, None, {"operation_receipt": detail}))
        else:
            field, target_id, before, after = targets[case_target]
            targets[case_target] = (field, target_id, before,
                                    {**(after or {}), "operation_receipt": detail})
        await self.db.execute(insert(ACT).values(id=aid, tenant_id=self.tenant_id,
            operation_id=operation_id, actor=actor, action=action, subject_case_id=case_id,
            occurred_at=func.clock_timestamp(), summary=action,
            detail={"schema_version": "activity.v1", "reason": None, "request_key": str(operation_id),
                    "source": action, "expected_version": None, "actual_version": None, "notes": []}))
        for field, target_id, before, after in targets:
            await self.db.execute(insert(TGT).values(id=uuid4(), tenant_id=self.tenant_id,
                activity_id=aid, **{field: target_id}, before_value=before if before is not None else null(),
                after_value=after if after is not None else null(), result_state="succeeded"))

    async def receipt(self, case_id, operation_id, action):
        row = await self.one(select(TGT.c.after_value).join(ACT,
            (ACT.c.id == TGT.c.activity_id) & (ACT.c.tenant_id == TGT.c.tenant_id))
            .where(*self.where(ACT), ACT.c.subject_case_id == case_id,
                   ACT.c.operation_id == operation_id, ACT.c.action == action, TGT.c.case_id == case_id))
        return row["after_value"]["operation_receipt"] if row else None

    async def replace_members(self, case_id: UUID, alert_ids: set[UUID], *,
                              expected_revision: int, actor: Actor, operation_id: UUID,
                              membership_sources: dict[UUID, str] | None = None):
        cas = await self.case(case_id)
        intent = digest({"case_id": str(case_id), "actor": str(actor.user_id),
                         "alerts": sorted(map(str, alert_ids)), "revision": expected_revision})
        prior = await self.receipt(case_id, operation_id, "case_members_changed")
        if prior:
            if prior["request_hash"] != intent:
                raise StoreError("operation_key_conflict")
            return prior["outcome"]
        if cas["scope_revision"] != expected_revision:
            raise StoreError("case_scope_revision_conflict")
        if cas["handling_status"] == "resolved":
            raise StoreError("resolved_case_scope_policy_not_enabled")
        if len(alert_ids) > 200:
            raise StoreError("case_member_limit_exceeded", 422)
        found = (await self.db.execute(select(A.c.id, A.c.source_namespace).where(*self.where(
            A, A.c.id.in_(alert_ids)
        )))).mappings().all()
        if {row["id"] for row in found} != alert_ids:
            raise StoreError("member_alert_not_found", 404)
        namespaces = {row["source_namespace"] for row in found}
        bound = cas["source_namespace"]
        if bound is None:
            # Legacy ambiguous/empty scopes are not a wildcard. Only the first
            # scope at revision zero can bind through the normal writer.
            if cas["scope_revision"] != 0 or len(namespaces) != 1:
                raise StoreError("case_source_scope_unverified")
            bound = next(iter(namespaces))
            if not bound or not bound.strip():
                raise StoreError("case_source_scope_unverified")
            await self.db.execute(update(C).where(*self.where(C, C.c.id == case_id))
                .values(source_namespace=bound))
        if namespaces - {bound}:
            raise StoreError("case_source_namespace_mismatch")
        current = await self.members(case_id)
        added, removed = alert_ids - current, current - alert_ids
        pending = await self.one(select(R).where(*self.where(R, R.c.case_id == case_id,
            R.c.kind == "baseline", R.c.state == "pending_update")).with_for_update())
        revision = cas["scope_revision"]
        now = await self.now()
        if added or removed:
            await self.db.execute(delete(CA).where(*self.where(
                CA, CA.c.case_id == case_id, CA.c.alert_id.in_(removed))))
            for aid in sorted(added):
                await self.db.execute(insert(CA).values(id=uuid4(), tenant_id=self.tenant_id,
                    case_id=case_id, alert_id=aid, added_by=actor.user_id,
                    membership_source=(membership_sources or {}).get(aid, "manual"),
                    source_operation_id=operation_id, added_at=now))
            revision += 1
            await self.db.execute(update(C).where(*self.where(C, C.c.id == case_id)).values(
                scope_revision=revision, row_version=C.c.row_version + 1, business_updated_at=now))
            if pending is None:
                pending_id = uuid4()
                await self.db.execute(insert(R).values(id=pending_id, tenant_id=self.tenant_id,
                    case_id=case_id, kind="baseline", title="完整基础调查",
                    purpose="重新调查当前 Case 全部成员", trigger="members_changed",
                    scope_revision=revision, scope_updated_at=now, scope_kind="whole_case",
                    state="pending_update", requested_by=actor.user_id, requested_at=now))
            else:
                pending_id = pending["id"]
                await self.db.execute(update(R).where(*self.where(R, R.c.id == pending_id)).values(
                    scope_revision=revision, scope_updated_at=now, row_version=R.c.row_version + 1))
            await self.refresh_members(case_id, pending_id)
        else:
            pending_id = pending["id"] if pending else None
        outcome = {"case_id": str(case_id), "scope_revision": revision,
                   "pending_run_id": str(pending_id) if pending_id else None,
                   "changed": bool(added or removed)}
        targets = [("case_id", case_id, {"scope_revision": cas["scope_revision"]},
                    {"scope_revision": revision})]
        targets += [("alert_id", aid, {"member": aid in current}, {"member": aid in alert_ids})
                    for aid in sorted(added | removed)]
        await self.event(case_id, operation_id, actor.snapshot(), "case_members_changed",
                         {"request_hash": intent, "outcome": outcome}, targets)
        return outcome

    async def refresh_members(self, case_id, run_id, rows=None):
        """One statement snapshots current pointers; referenced versions are immutable."""
        if rows is None:
            rows = (await self.db.execute(select(A.c.id, A.c.latest_material_id,
                A.c.latest_triage_id, A.c.latest_feedback_id).join(CA,
                    (CA.c.alert_id == A.c.id) & (CA.c.tenant_id == A.c.tenant_id))
                .where(*self.where(A), CA.c.case_id == case_id).order_by(A.c.id))).mappings().all()
        await self.db.execute(delete(RM).where(*self.where(RM, RM.c.run_id == run_id)))
        for row in rows:
            await self.db.execute(insert(RM).values(id=uuid4(), tenant_id=self.tenant_id,
                case_id=case_id, run_id=run_id, alert_id=row["id"], material_id=row["latest_material_id"],
                triage_id=row["latest_triage_id"], feedback_id=row["latest_feedback_id"],
                read_state="not_read" if row["latest_material_id"] else "missing",
                omission_reason=None if row["latest_material_id"] else "source_material_not_available"))
        return rows

    async def save_input_artifact(self, case_id, run_id, identity, payload, *, kind, schema,
                                  captured_at, refs, actor_id, step_id=None):
        body = encoded(payload)
        sha = hashlib.sha256(body).hexdigest()
        await self.db.execute(insert(F).values(id=identity, tenant_id=self.tenant_id,
            case_id=case_id, run_id=run_id, step_id=step_id, kind=kind, schema_version=schema,
            content_json=payload, mime_type="application/json", sha256=sha, size_bytes=len(body),
            captured_at=captured_at, material_state="complete", source_refs=refs, created_by=actor_id,
            retention={"original_size_bytes": len(body), "retained_size_bytes": len(body),
                "original_sha256": sha, "retained_sha256": sha, "truncated": False,
                "reason": None, "omitted_paths": []}))

    async def claim(self, case_id: UUID, run_id: UUID, request: Start, *,
                    actor: Actor, executor_version: str, limits: Limits) -> Claim:
        cas = await self.case(case_id)
        run = await self.run(case_id, run_id)
        intent = digest({"case_id": str(case_id), "actor": str(actor.user_id),
                         "request": request.model_dump(mode="json")})
        if run["state"] != "pending_update":
            if run["operation_key"] != str(request.operation_key) or run["request_hash"] != intent:
                raise StoreError("baseline_already_claimed")
            return Claim(run_id=run_id, case_id=case_id, scope_revision=run["scope_revision"],
                state=run["state"], newly_claimed=False, input_artifact_id=run["input_artifact_id"],
                started_at=run["started_at"])
        if cas["handling_status"] == "resolved":
            raise StoreError("resolved_case_start_policy_not_enabled")
        if cas["scope_revision"] != request.expected_scope_revision or run["scope_revision"] != cas["scope_revision"]:
            raise StoreError("baseline_scope_revision_conflict")
        active = await self.one(select(R.c.id).where(*self.where(R, R.c.case_id == case_id,
            R.c.kind == "baseline", R.c.state.in_(["running", "unknown"]))))
        if active:
            raise StoreError("baseline_already_active")
        other = await self.one(select(R.c.id).where(*self.where(R, R.c.kind == "baseline",
            R.c.operation_key == str(request.operation_key))))
        if other:
            raise StoreError("operation_key_conflict")
        if not executor_version.strip():
            raise StoreError("executor_version_required", 422)
        if request.comparison_result_id:
            prior = await self.one(select(RES.c.id).where(*self.where(RES,
                RES.c.case_id == case_id, RES.c.id == request.comparison_result_id)))
            if prior is None:
                raise StoreError("comparison_result_not_found", 404)
        context = await c1.capture(self.db, self.tenant_id, case_id, request)
        if not context.alerts:
            raise StoreError("baseline_scope_empty")
        payload = context.model_dump(mode="json")
        if len(encoded(payload)) > c1.MAX_CONTEXT_BYTES:
            raise StoreError("baseline_context_too_large", 422)
        rows = [{key: UUID(a.alert[key]) if a.alert[key] else None
                 for key in ["id", "latest_material_id", "latest_triage_id", "latest_feedback_id"]}
                for a in context.alerts.values()]
        await self.refresh_members(case_id, run_id, rows=rows)
        now, context_id, artifact_id = context.captured_at, uuid4(), uuid4()
        refs = c1.selected_refs(context)
        await self.save_input_artifact(case_id, run_id, context_id, payload, kind="source_snapshot",
            schema=c1.SCHEMA, captured_at=now, refs=refs, actor_id=actor.user_id)
        context_ref = c1.reference("artifact", context_id, "execution_receipt")
        snapshot = {"schema_version": "socai2.page-model.v1", "run_kind": "baseline",
            "scope_revision": cas["scope_revision"], "scope": context.scope.model_dump(mode="json"),
            "source_materials": [context_ref, *refs],
            "prior_results": sorted(context.prior_results),
            "task_revisions": sorted({r["id"] for r in refs if r["type"] == "task_revision"}),
            "comparison_result_id": str(request.comparison_result_id) if request.comparison_result_id else None,
            "projection_version": c1.PROJECTION,
            "omissions": [{"source_ref": context_ref, "reason": f"{o.section}:{o.source_id or '-'}:{o.reason}"}
                          for o in context.omissions], "captured_at": now.isoformat()}
        await self.save_input_artifact(case_id, run_id, artifact_id, snapshot, kind="input_snapshot",
            schema="socai2.page-model.v1", captured_at=now, refs=[context_ref, *refs], actor_id=actor.user_id)
        await self.db.execute(update(R).where(*self.where(R, R.c.id == run_id)).values(
            state="running", input_artifact_id=artifact_id, operation_key=str(request.operation_key),
            request_hash=intent, executor_version=executor_version, limits=limits.model_dump(mode="json"),
            started_at=now, requested_by=actor.user_id, window_start=request.window_start,
            window_end=request.window_end, comparison_result_id=request.comparison_result_id,
            row_version=R.c.row_version + 1))
        await self.event(case_id, request.operation_key, actor.snapshot(), "baseline_started",
            {"run_id": str(run_id), "scope_revision": cas["scope_revision"]},
            [("run_id", run_id, {"state": "pending_update"}, {"state": "running"})])
        return Claim(run_id=run_id, case_id=case_id, scope_revision=cas["scope_revision"],
            state="running", newly_claimed=True, input_artifact_id=artifact_id, started_at=now)

    async def read_context(self, case_id, run_id):
        await self.case(case_id, lock=False)
        run = await self.one(select(R.c.input_artifact_id).where(*self.where(R,
            R.c.case_id == case_id, R.c.id == run_id, R.c.kind == "baseline")))
        if run is None:
            raise StoreError("baseline_not_found", 404)
        manifest = await self.one(select(F.c.content_json).where(*self.where(F,
            F.c.id == run["input_artifact_id"], F.c.run_id == run_id, F.c.kind == "input_snapshot")))
        if not manifest or manifest["content_json"].get("projection_version") != c1.PROJECTION:
            raise StoreError("frozen_c1_context_not_available")
        refs = [UUID(r["id"]) for r in manifest["content_json"]["source_materials"] if r["type"] == "artifact"]
        context = await self.one(select(F).where(*self.where(F, F.c.id.in_(refs), F.c.case_id == case_id,
            F.c.run_id == run_id, F.c.kind == "source_snapshot", F.c.schema_version == c1.SCHEMA)))
        if context is None or digest(context["content_json"]) != context["sha256"]:
            raise StoreError("frozen_c1_context_invalid")
        return c1.Context.model_validate(context["content_json"])

    async def read_material(self, case_id, run_id, material_id):
        """Read an immutable version, never the alert's latest pointer. No GET writes."""
        await self.case(case_id, lock=False)
        material = models.AlertMaterials.__table__
        row = await self.one(select(material).join(RM,
            (RM.c.material_id == material.c.id) & (RM.c.tenant_id == material.c.tenant_id)
            & (RM.c.alert_id == material.c.alert_id))
            .join(R, (R.c.id == RM.c.run_id) & (R.c.tenant_id == RM.c.tenant_id))
            .where(*self.where(material, material.c.id == material_id), RM.c.case_id == case_id,
                   RM.c.run_id == run_id, R.c.kind == "baseline", R.c.input_artifact_id.is_not(None)))
        if row is None:
            raise StoreError("frozen_material_not_found", 404)
        return dict(row)

    async def validate_result_refs(self, run, members, publication):
        from . import baseline_analysis_contract as c3
        from . import baseline_deep_contract as deep
        from . import baseline_delivery_contract as c6
        from . import baseline_enrichment as c2
        from . import baseline_evidence as c4
        from . import baseline_graph_projection as c5
        from . import baseline_model_view as view
        snapshot = await self.one(select(F.c.content_json).where(*self.where(F,
            F.c.id == run["input_artifact_id"])))
        frozen = snapshot["content_json"]
        allowed = {"alert_material": {r["material_id"] for r in members if r["material_id"]},
                   "result": set(map(UUID, frozen["prior_results"])),
                   "task_revision": set(map(UUID, frozen["task_revisions"]))}
        allowed["artifact"] = set((await self.db.execute(select(F.c.id).where(*self.where(
            F, F.c.case_id == run["case_id"], F.c.run_id == run["id"]
        )))).scalars())
        contexts = (await self.db.execute(select(F.c.id, F.c.content_json).where(*self.where(
            F, F.c.run_id == run["id"], F.c.kind == "source_snapshot", F.c.schema_version == c1.SCHEMA
        )))).mappings().all()
        context_roles = {row["id"]: dict(row["content_json"]["citation_roles"]) for row in contexts}
        # Legacy contexts already froze this scalar in the alert object. Accept
        # only that exact child path/role without rewriting the old artifact.
        for row in contexts:
            for aid, member in row["content_json"]["alerts"].items():
                path = f"$.alerts.{aid}.alert"
                if context_roles[row["id"]].get(path) == "source_label" and member["alert"].get("event_time") is not None:
                    context_roles[row["id"]][path + ".event_time"] = "source_label"
        prepared = (await self.db.execute(select(F.c.id, F.c.schema_version, F.c.content_json)
            .where(*self.where(F, F.c.run_id == run["id"],
                              F.c.schema_version.in_([c2.SCHEMA, *view.READ_SCHEMAS, *c3.READ_SCHEMAS, c4.SCHEMA, deep.SCHEMA, c5.SCHEMA, c6.SCHEMA,
                                  "socai2.baseline-executor.v1", "socai2.baseline-executor.v2"]))))).mappings().all()
        for row in prepared:
            if row["schema_version"] == c6.SCHEMA:
                context_roles[row["id"]] = c6.citation_roles(row["content_json"])
            elif row["schema_version"] == c5.SCHEMA:
                context_roles[row["id"]] = c5.citation_roles(row["content_json"])
            elif row["schema_version"] == deep.SCHEMA:
                context_roles[row["id"]] = deep.citation_roles(row["content_json"])
            elif row["schema_version"] == c4.SCHEMA:
                context_roles[row["id"]] = c4.citation_roles(row["content_json"])
            elif row["schema_version"] in c3.READ_SCHEMAS:
                context_roles[row["id"]] = c3.citation_roles(row["content_json"])
            else:
                context_roles[row["id"]] = c2.citation_roles(row["content_json"]) if row["schema_version"] == c2.SCHEMA else {}
        # Adopted source artifacts can belong to older Runs, but must be explicitly
        # frozen into this input. No arbitrary same-Case artifact is allowed.
        allowed["artifact"].update(UUID(r["id"]) for r in frozen["source_materials"] if r["type"] == "artifact")
        member_ids = {r["alert_id"] for r in members}

        def walk(value):
            if isinstance(value, list):
                for item in value:
                    walk(item)
            elif isinstance(value, dict):
                if ("type" in value and "role" in value and "row_keys" in value
                        and UUID(value["id"]) not in allowed[value["type"]]):
                    raise StoreError("result_evidence_outside_frozen_scope", 422)
                if value.get("type") == "artifact" and UUID(value["id"]) in context_roles:
                    roles = context_roles[UUID(value["id"])]
                    expected = roles.get(value["source_path"]) if value["source_path"] else "execution_receipt"
                    if expected != value["role"]:
                        raise StoreError("context_citation_path_or_role_invalid", 422)
                if ("alert_ids" in value and "kind" in value
                        and not set(map(UUID, value["alert_ids"])) <= member_ids):
                    raise StoreError("result_scope_outside_run", 422)
                for item in value.values():
                    walk(item)
        walk(publication.model_dump(mode="json"))
        for value, kinds in [(publication.graph_artifact_id, {"alert_graph", "attack_path", "attack_chain"}),
                             (publication.report_artifact_id, {"report_json", "report_markdown"})]:
            if value:
                artifact = await self.one(select(F.c.kind).where(*self.where(
                    F, F.c.id == value, F.c.run_id == run["id"])))
                if artifact is None or artifact["kind"] not in kinds:
                    raise StoreError("result_artifact_kind_or_run_mismatch", 422)

    async def publish(self, case_id: UUID, run_id: UUID, publication: Publication, *, result_id: UUID | None = None):
        await self.case(case_id)
        run = await self.run(case_id, run_id)
        payload_hash = digest(publication.model_dump(mode="json"))
        prior = await self.receipt(case_id, publication.operation_key, "baseline_published")
        if prior:
            if prior["payload_hash"] != payload_hash or prior["run_id"] != str(run_id):
                raise StoreError("publication_key_conflict")
            return prior["outcome"]
        if run["state"] not in {"running", "unknown"}:
            raise StoreError("baseline_not_active")
        steps = models.RunSteps.__table__
        if await self.one(select(steps.c.id).where(*self.where(steps, steps.c.run_id == run_id,
                steps.c.state.in_(["planned", "running", "unknown"]))).limit(1)):
            raise StoreError("baseline_steps_not_settled")
        if publication.change_kind == "initial" and run["comparison_result_id"] is not None:
            raise StoreError("initial_result_has_comparison", 422)
        members = (await self.db.execute(select(RM).where(*self.where(
            RM, RM.c.run_id == run_id)))).mappings().all()
        if {r["alert_id"] for r in members} != {m.alert_id for m in publication.members}:
            raise StoreError("result_member_delivery_incomplete", 422)
        await self.validate_result_refs(run, members, publication)
        # C6 may reserve the identity to put the exact Result ID into its
        # immutable report in this same transaction. Public DTOs cannot set it.
        now, result_id = await self.now(), result_id or uuid4()
        for m in publication.members:
            await self.db.execute(update(RM).where(*self.where(RM,
                RM.c.run_id == run_id, RM.c.alert_id == m.alert_id)).values(
                    read_state=m.read_state, analysis_state=m.assessment_state, omission_reason=m.limitations))
        await self.db.execute(update(R).where(*self.where(R, R.c.id == run_id)).values(
            state=publication.terminal_state, ended_at=now, stop_reason=publication.stop_reason,
            stop_detail=publication.stop_detail, delivery_state=publication.delivery_state,
            row_version=R.c.row_version + 1))
        values = publication.model_dump(mode="json", exclude={"operation_key", "members", "terminal_state",
            "stop_reason", "stop_detail", "graph_artifact_id", "report_artifact_id"})
        await self.db.execute(insert(RES).values(id=result_id, tenant_id=self.tenant_id,
            case_id=case_id, kind="baseline", source_run_id=run_id, purpose=run["purpose"],
            input_artifact_id=run["input_artifact_id"], comparison_result_id=run["comparison_result_id"],
            graph_artifact_id=publication.graph_artifact_id, report_artifact_id=publication.report_artifact_id,
            created_at=now, operation_key=str(publication.operation_key), **values))
        for m in publication.members:
            vals = m.model_dump(mode="json", exclude={"alert_id", "read_state"})
            await self.db.execute(insert(RESM).values(id=uuid4(), tenant_id=self.tenant_id,
                case_id=case_id, result_id=result_id, run_id=run_id, alert_id=m.alert_id, **vals))
        adoption = (await self.db.execute(text(
            "SELECT socai2.auto_adopt_baseline_result(:tenant, :result)"),
            {"tenant": self.tenant_id, "result": result_id})).scalar_one()
        if publication.conclusion_origin == "system" and publication.validation_state == "system_only" and publication.conclusion:
            from .baseline_closing import record_case_closing
            adoption = await record_case_closing(self, run, result_id, publication.conclusion)
        outcome = {"result_id": str(result_id), "run_id": str(run_id), "adoption": adoption}
        await self.event(case_id, publication.operation_key,
            {"type": "service", "user_id": None, "name_snapshot": None,
             "service_name": "socai2.baseline", "service_version": run["executor_version"]},
            "baseline_published", {"payload_hash": payload_hash, "run_id": str(run_id), "outcome": outcome},
            [("run_id", run_id, {"state": run["state"]}, {"state": publication.terminal_state}),
             ("result_id", result_id, None, {"adoption": adoption})])
        return outcome

    async def prepare_model_view(self, case_id, run_id):
        from . import baseline_enrichment as c2
        from . import baseline_model_view as view
        await self.case(case_id)
        run = await self.run(case_id, run_id)
        prior = await self.one(select(F).where(*self.where(F, F.c.run_id == run_id,
            F.c.schema_version.in_(view.READ_SCHEMAS), F.c.kind == "source_snapshot")))
        if prior:
            if digest(prior["content_json"]) != prior["sha256"]:
                raise StoreError("model_view_receipt_invalid")
            return {"artifact_id": str(prior["id"]), **prior["content_json"]}
        if run["state"] != "running":
            raise StoreError("baseline_not_running")
        stage = await self.one(select(c2.S).where(*self.where(c2.S,
            c2.S.c.run_id == run_id, c2.S.c.stage_code == "C2", c2.S.c.kind == "stage")))
        if not stage or stage["state"] != "completed":
            raise StoreError("enrichment_not_completed")
        summary = await self.one(select(F).where(*self.where(F, F.c.id == stage["output_artifact_id"],
            F.c.run_id == run_id)))
        if not summary or digest(summary["content_json"]) != summary["sha256"]:
            raise StoreError("enrichment_receipt_invalid")
        context = await self.read_context(case_id, run_id)
        c1_row = await self.one(select(F.c.id).where(*self.where(F, F.c.run_id == run_id,
            F.c.schema_version == c1.SCHEMA, F.c.kind == "source_snapshot")))
        evidence, states = [], []
        for source in summary["content_json"]["sources"]:
            artifact = await self.one(select(F).where(*self.where(F, F.c.run_id == run_id,
                F.c.id == UUID(source["artifact_id"]), F.c.kind == "tool_response")))
            if not artifact or digest(artifact["content_json"]) != artifact["sha256"]:
                raise StoreError("enrichment_receipt_invalid")
            payload = artifact["content_json"]
            evidence.append((artifact["id"], payload, c2.citation_roles(payload)))
            states.append({"source": source["source"], "outcome": source["outcome"],
                "truncated": source["truncated"], "reason": source["reason"],
                "captured_at": payload["captured_at"], "limitations": source["limitations"]})
        materials = {aid: await self.read_material(case_id, run_id, UUID(alert.material["id"]))
                     for aid, alert in context.alerts.items() if alert.material}
        payload = view.build(context, c1_row["id"], evidence, states, materials)
        if payload["ready"]:
            from .model_input_view import frozen_items
            visible = json.loads(payload["messages"][1]["content"])
            read_ids = {UUID(item["source"]["id"]) for item in frozen_items(visible)
                        if item["source"]["type"] == "alert_material" and item["source"]["role"] == "observation"}
            if read_ids:
                await self.db.execute(update(RM).where(*self.where(RM, RM.c.run_id == run_id,
                    RM.c.material_id.in_(read_ids))).values(read_state="read"))
        identity = uuid4()
        refs = [c1.reference("artifact", c1_row["id"], "execution_receipt"),
                c1.reference("artifact", summary["id"], "execution_receipt")]
        await self.save_input_artifact(case_id, run_id, identity, payload, kind="source_snapshot",
            schema=view.SCHEMA, captured_at=await self.now(), refs=refs, actor_id=run["requested_by"])
        return {"artifact_id": str(identity), **payload}

    async def mark_unknown(self, case_id, run_id):
        await self.case(case_id)
        run = await self.run(case_id, run_id)
        if run["state"] == "running":
            await self.db.execute(update(R).where(*self.where(R, R.c.id == run_id)).values(
                state="unknown", stop_reason="executor_dispatch_uncertain", row_version=R.c.row_version + 1))

    async def history(self, case_id, *, limit=20):
        if not 1 <= limit <= 100:
            raise StoreError("invalid_history_limit", 422)
        await self.case(case_id, lock=False)
        result = await self.db.execute(select(R, RES.c.id.label("result_id"))
            .outerjoin(RES, (RES.c.source_run_id == R.c.id) & (RES.c.tenant_id == R.c.tenant_id)
                       & RES.c.supersedes_result_id.is_(None))
            .where(*self.where(R, R.c.case_id == case_id, R.c.kind == "baseline"))
            .order_by(R.c.requested_at.desc(), R.c.id.desc()).limit(limit))
        return [dict(row) for row in result.mappings()]
