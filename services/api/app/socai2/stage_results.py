"""Atomic A/I input and result storage; legacy consumers remain separate.

The producer must claim before executing and publish its validated output. This
module does not manufacture query receipts or infer that an engine was called.
Lock order: Alert/Incident -> Run. Incident reads never lock member Alerts.
"""
from uuid import UUID, uuid4, uuid5

from sqlalchemy import func, insert, select, text, update

from app.models import socai2 as m

from .baseline_contracts import Limits
from .baseline_service import BaselineService
from .baseline_store import StoreError, digest, encoded
from .runtime_policy import retention_limit
from .stage_inputs import SOURCE_SQL, VERSION, incident_source_sql
from .stage_result_contracts import (
    ALERT_EXECUTOR_VERSION,
    INCIDENT_EXECUTOR_VERSION,
    AlertOutput,
    IncidentOutput,
)

A, I, R, F, D, AS = (x.__table__ for x in (m.Alerts, m.Incidents, m.Runs, m.Artifacts,
                                          m.IncidentDiagnoses, m.AlertAssessments))


async def source_input(store, kind, identity, *, validated_triage=False, with_queries=False):
    sql = incident_source_sql(with_queries=with_queries) if kind == "incident_diagnosis" and validated_triage else SOURCE_SQL
    return (await store.db.execute(text(sql), {"tenant": store.tenant_id,
        "id": identity, "kind": kind, "version": VERSION})).scalar_one()


def parent(kind):
    if kind == "alert_basic":
        return A, "alert_id"
    if kind == "incident_diagnosis":
        return I, "incident_id"
    raise StoreError("unsupported_stage_kind", 422)


async def artifact(store, run, identity, kind, value, now, refs, *, step_id=None, schema_version=VERSION):
    body = encoded(value)
    if len(body) > retention_limit():
        raise StoreError("stage_artifact_too_large", 422)
    sha = digest(value)
    _, key = parent(run["kind"])
    await store.db.execute(insert(F).values(id=identity, tenant_id=store.tenant_id,
        **{key: run[key]}, run_id=run["id"], step_id=step_id, kind=kind, schema_version=schema_version,
        content_json=value, mime_type="application/json", sha256=sha, size_bytes=len(body),
        captured_at=now, material_state="complete", source_refs=refs,
        retention={"original_size_bytes": len(body), "retained_size_bytes": len(body),
            "original_sha256": sha, "retained_sha256": sha, "truncated": False,
            "reason": None, "omitted_paths": []}))


def validate_refs(payload, source, input_id, tool_refs=None):
    """Only frozen local sources and verified same-Run query response fields.

    A whole mixed input is an execution receipt, not an observation. Exact JSON
    fields may be cited for material; arbitrary JSONPath/query syntax is refused.
    """
    materials = {x["material"]["id"]: x["material"] for x in source["members"] if x["material"]}
    members = {x["alert"]["id"] for x in source["members"]}
    objects = {o["object_key"] for x in source["members"] for o in x["objects"]}

    def visit(value):
        if isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            if "type" in value and "source_path" in value:
                mid = value["id"]
                if value["row_keys"]:
                    raise StoreError("stage_reference_rows_not_supported", 422)
                if value["type"] == "alert_material" and mid in materials:
                    material = materials[mid]
                    if material["material_state"] != "complete" or value["role"] not in {"observation", "source_label"}:
                        raise StoreError("stage_material_role_invalid", 422)
                    path = value["source_path"]
                    # Detection/score labels cannot become observations.
                    if value["role"] == "observation" and (not path or not path.startswith(("$.raw_json.", "$.ocsf_json.", "$.raw_text"))):
                        raise StoreError("stage_observation_path_required", 422)
                    if path:
                        if not path.startswith("$."):
                            raise StoreError("stage_reference_path_invalid", 422)
                        cursor = material
                        for part in path[2:].split("."):
                            if isinstance(cursor, dict) and part in cursor:
                                cursor = cursor[part]
                            elif isinstance(cursor, list) and part.isdigit() and int(part) < len(cursor):
                                cursor = cursor[int(part)]
                            else:
                                raise StoreError("stage_reference_path_invalid", 422)
                        if cursor is None:
                            raise StoreError("stage_reference_value_unavailable", 422)
                elif value["type"] == "artifact" and mid in (tool_refs or {}):
                    if tool_refs[mid].get(value["source_path"]) != value["role"]:
                        raise StoreError("stage_query_reference_role_or_path_invalid", 422)
                elif value["type"] == "artifact" and mid == str(input_id):
                    path = value["source_path"]
                    roles = {"alert": "source_label", "membership": "source_label", "objects": "source_label",
                             "triage": "prior_analysis", "feedback": "human_statement"}
                    parts = path.split(".") if path else []
                    if not path and value["role"] == "execution_receipt":  # noqa: SIM114 -- whole receipt and typed field are distinct policies
                        pass
                    elif path == "$.parent" and value["role"] == "source_label" and source["parent"]:  # noqa: SIM114 -- parent and member roles differ
                        pass
                    elif (len(parts) == 4 and parts[:2] == ["$", "members"] and parts[2].isdigit()  # noqa: SIM114 -- scalar and whole-field policies stay distinct
                          and int(parts[2]) < len(source["members"]) and parts[3] in roles
                          and roles[parts[3]] == value["role"] and source["members"][int(parts[2])][parts[3]]):
                        pass
                    elif (len(parts) == 5 and parts[:2] == ["$", "members"] and parts[2].isdigit()
                          and int(parts[2]) < len(source["members"]) and parts[3:] == ["alert", "event_time"]
                          and value["role"] == "source_label"
                          and source["members"][int(parts[2])]["alert"].get("event_time") is not None):
                        pass
                    else:
                        raise StoreError("stage_input_reference_role_or_path_invalid", 422)
                else:
                    raise StoreError("stage_reference_outside_frozen_input", 422)
            if "alert_ids" in value and "object_keys" in value and (
                not set(value["alert_ids"]) <= members or not set(value["object_keys"]) <= objects
            ):
                raise StoreError("stage_output_scope_invalid", 422)
            for item in value.values():
                visit(item)
    visit(payload)


class StageResultService(BaselineService):
    """Server-internal persistence boundary. A/I calls do not start Case runs."""

    async def begin(self, tenant_id, kind, identity, operation_key: UUID, *, producer: str, limits: Limits | None,
                    requested_by: UUID | None = None):
        table, key = parent(kind)
        if not producer.strip():
            raise StoreError("stage_producer_required", 422)
        expected = {"alert_basic": ALERT_EXECUTOR_VERSION, "incident_diagnosis": INCIDENT_EXECUTOR_VERSION}
        if limits is None and producer != expected[kind]:
            raise StoreError("stage_limits_required", 422)
        body = {"kind": kind, "identity": str(identity), "producer": producer,
                "limits": limits.model_dump(mode="json") if limits else kind + "_server_policy_v1"}
        if requested_by is not None:
            body["requested_by"] = str(requested_by)
        intent = digest(body)
        rid = uuid5(tenant_id, "socai2.stage:" + str(operation_key))
        async with self.transaction(tenant_id) as store:
            if requested_by is not None:
                user = (await store.db.execute(text("SELECT id FROM public.users WHERE tenant_id=CAST(:tenant AS uuid) AND id=CAST(:actor AS uuid)"),
                    {"tenant": str(tenant_id), "actor": str(requested_by)})).scalar_one_or_none()
                if user is None:
                    raise StoreError("stage_actor_not_in_tenant", 403)
            target = await store.one(select(table).where(*store.where(table, table.c.id == identity)).with_for_update())
            if not target:
                raise StoreError("stage_subject_not_found", 404)
            old = await store.one(select(R).where(*store.where(R, R.c.id == rid)))
            if old:
                if old["request_hash"] != intent:
                    raise StoreError("operation_key_conflict")
                return {"run_id": rid, "input_artifact_id": old["input_artifact_id"], "newly_claimed": False}
            from .runtime_policy import active_policy
            with_queries = kind == "incident_diagnosis" and producer == INCIDENT_EXECUTOR_VERSION and active_policy().incident_io is not None
            source = await source_input(store, kind, identity, validated_triage=producer == INCIDENT_EXECUTOR_VERSION,
                with_queries=with_queries)
            if not source["members"]:
                raise StoreError("stage_members_required", 422)
            now, input_id = await store.now(), uuid4()
            if limits is None:
                from .runtime_policy import active_policy
                policy = active_policy()
                limits = getattr(policy, kind).limits(now, policy.identity)
            run = {"id": rid, "kind": kind, key: identity}
            await artifact(store, run, input_id, "input_snapshot", source, now, [])
            await store.db.execute(insert(R).values(**run, tenant_id=tenant_id,
                title="告警基本分析" if kind == "alert_basic" else "事件诊断", purpose="source-scoped analysis",
                trigger="refresh", state="running", operation_key=str(operation_key), request_hash=intent,
                input_artifact_id=input_id, executor_version=producer, requested_at=now, started_at=now,
                limits=limits.model_dump(mode="json"), requested_by=requested_by))
            if kind == "incident_diagnosis":
                rev = (await store.db.execute(select(func.coalesce(func.max(D.c.revision), 0)).where(
                    *store.where(D, D.c.incident_id == identity)))).scalar_one() + 1
                await store.db.execute(insert(D).values(id=uuid5(rid, "diagnosis"), tenant_id=tenant_id,
                    incident_id=identity, source_run_id=rid, revision=rev, state="running",
                    input_artifact_id=input_id, source_fingerprint=digest(source), producer=producer, requested_at=now))
        return {"run_id": rid, "input_artifact_id": input_id, "newly_claimed": True}

    async def locked(self, store, run_id):
        run = await store.one(select(R).where(*store.where(R, R.c.id == run_id)))
        if not run or run["kind"] not in {"alert_basic", "incident_diagnosis"}:
            raise StoreError("stage_run_not_found", 404)
        table, key = parent(run["kind"])
        target = await store.one(select(table).where(*store.where(table, table.c.id == run[key])).with_for_update())
        run = await store.one(select(R).where(*store.where(R, R.c.id == run_id)).with_for_update())
        source = (await store.db.execute(select(F.c.content_json).where(*store.where(F, F.c.id == run["input_artifact_id"])))).scalar_one()
        return run, target, source

    async def finish(self, tenant_id, run_id, output: AlertOutput | IncidentOutput, *, execution_step_id=None,
                     validated_members=None, alert_delivery_state=None):
        payload = output.model_dump(mode="json")
        async with self.transaction(tenant_id) as store:
            run, target, source = await self.locked(store, run_id)
            is_alert = run["kind"] == "alert_basic"
            if alert_delivery_state is not None and (not is_alert or alert_delivery_state not in {"complete", "partial"}):
                raise StoreError("alert_delivery_state_invalid", 422)
            if is_alert != isinstance(output, AlertOutput):
                raise StoreError("stage_output_kind_mismatch", 422)
            receipt_id = uuid5(run_id, "publication")
            old = await store.one(select(F.c.content_json).where(*store.where(F, F.c.id == receipt_id)))
            if old:
                if old["content_json"]["output_hash"] != digest(payload):
                    raise StoreError("stage_publication_conflict")
                return old["content_json"]["outcome"]
            if run["state"] != "running":
                raise StoreError("stage_run_not_running")
            tool_refs, query_receipts = {}, []
            steps = m.RunSteps.__table__
            if run["executor_version"] == ALERT_EXECUTOR_VERSION:
                from .baseline_enrichment import citation_roles
                rows = (await store.db.execute(select(F).join(steps,
                    (steps.c.tenant_id == F.c.tenant_id) & (steps.c.run_id == F.c.run_id)
                    & (steps.c.id == F.c.step_id) & (steps.c.output_artifact_id == F.c.id)).where(
                    *store.where(F, F.c.run_id == run_id, F.c.alert_id == run["alert_id"],
                        F.c.kind == "tool_response", F.c.schema_version == ALERT_EXECUTOR_VERSION),
                    steps.c.kind == "tool").order_by(steps.c.seq))).mappings().all()
                for row in rows:
                    body = row["content_json"]
                    if row["material_state"] != "complete" or digest(body) != row["sha256"] or len(encoded(body)) != row["size_bytes"]:
                        raise StoreError("stage_query_receipt_invalid", 422)
                    query_receipts.append((row["id"], body))
                    if body.get("state") == "completed":
                        tool_refs[str(row["id"])] = citation_roles(body)
            if not is_alert and "query_receipts_version" in source:
                from .incident_query_receipts import reference_roles
                tool_refs = reference_roles(source)
            validate_refs(payload, source, run["input_artifact_id"], tool_refs)
            if execution_step_id is not None:
                step = await store.one(select(steps).where(*store.where(steps, steps.c.run_id == run_id,
                    steps.c.id == execution_step_id, steps.c.kind == "stage", steps.c.state == "running")))
                active = await store.one(select(steps.c.id).where(*store.where(steps, steps.c.run_id == run_id,
                    steps.c.id != execution_step_id, steps.c.state.in_(["planned", "running", "unknown"]))).limit(1))
                if not step or active:
                    raise StoreError("stage_execution_not_ready")
            table, key = parent(run["kind"])
            fresh = digest(await source_input(store, run["kind"], run[key],
                validated_triage="triage_validation_version" in source,
                with_queries="query_receipts_version" in source)) == digest(source)
            pointer = "latest_triage_id" if is_alert else "latest_diagnosis_id"
            result_table = AS if is_alert else D
            newer = False
            if target[pointer]:
                prior = await store.one(select(R.c.started_at).join(result_table, result_table.c.source_run_id == R.c.id).where(
                    *store.where(result_table, result_table.c.id == target[pointer]), R.c.tenant_id == tenant_id))
                newer = bool(prior and prior["started_at"] > run["started_at"])
            now, result_id = await store.now(), uuid5(run_id, "assessment" if is_alert else "diagnosis")
            refs = payload["source_refs"]
            from .program_facts import stage_facts
            facts = stage_facts(source, run["input_artifact_id"], run["started_at"].isoformat(),
                queries=query_receipts if run["executor_version"] == ALERT_EXECUTOR_VERSION else None)
            if is_alert:
                explanation = {"schema_version": VERSION, "body": output.explanation,
                    "generation_method": output.generation_method, "generated_at": now.isoformat(),
                    "source_refs": refs, "recommendations": payload["recommendations"], "limitations": output.limitations,
                    "program_facts": facts}
                explain_id = uuid5(run_id, "explanation")
                await artifact(store, run, explain_id, "alert_explanation", explanation, now, refs)
                await store.db.execute(insert(AS).values(id=result_id, tenant_id=tenant_id, alert_id=run[key], kind="triage",
                    input_material_id=UUID(source["members"][0]["material"]["id"]) if source["members"][0]["material"] else None,
                    source_run_id=run_id, verdict=output.verdict, rationale=output.rationale, confidence=output.confidence,
                    score_state=output.score_state, recommendations=payload["recommendations"], producer=run["executor_version"],
                    actor={"type": "service", "user_id": None, "name_snapshot": None, "service_name": run["executor_version"],
                        "service_version": VERSION}, assessed_at=now, operation_key=str(run_id)))
            else:
                from .incident_delivery import assess
                delivery = assess(source, output=payload, members=validated_members)
                diagnosis = {"conclusion": output.conclusion, "validation_state": "accepted", "findings": payload["findings"],
                             "source_refs": refs, "limitations": output.limitations, "program_facts": facts,
                             "delivery_assessment": delivery}
                await store.db.execute(update(D).where(*store.where(D, D.c.id == result_id)).values(state="completed",
                    summary=output.summary, diagnosis=diagnosis, open_questions=payload["open_questions"], generated_at=now))
            adopted = fresh and not newer
            if adopted:
                values = {pointer: result_id}
                if is_alert:
                    values["latest_explanation_id"] = explain_id
                    values["business_updated_at"] = func.greatest(A.c.business_updated_at, now)
                    values["row_version"] = A.c.row_version + 1
                await store.db.execute(update(table).where(*store.where(table, table.c.id == run[key])).values(**values))
                if is_alert:
                    # Same Alert -> Incident order as Fusion. Serializes member
                    # analysis changes with an incident publication's fingerprint.
                    await store.db.execute(text("""UPDATE socai2.incidents SET business_updated_at=greatest(business_updated_at,:now),
                        row_version=row_version+1 WHERE tenant_id=:tenant AND id IN
                        (SELECT incident_id FROM socai2.incident_alerts WHERE tenant_id=:tenant AND alert_id=:alert)"""),
                        {"now": now, "tenant": tenant_id, "alert": run[key]})
            outcome = {"result_id": str(result_id), "adopted": adopted,
                "reason": "current" if adopted else "input_changed" if not fresh else "newer_result_exists"}
            await artifact(store, run, receipt_id, "source_snapshot", {"output_hash": digest(payload),
                "output": payload, "outcome": outcome, **({"delivery_assessment": delivery} if not is_alert else {})}, now, refs)
            await store.db.execute(update(R).where(*store.where(R, R.c.id == run_id)).values(state="completed", ended_at=now,
                stop_reason="stage_output_saved", delivery_state=(alert_delivery_state or "partial") if is_alert else delivery["state"], row_version=R.c.row_version + 1))
            if execution_step_id is not None:
                await store.db.execute(update(steps).where(*store.where(steps, steps.c.id == execution_step_id)).values(
                    state="completed", ended_at=now, output_artifact_id=receipt_id))
        return outcome

    async def execute_alert(self, tenant_id, alert_id, operation_key: UUID, *, gateway=None, query=None, requested_by=None):
        """Trusted server entry: frozen A only; no Case run or legacy side effects."""
        from .alert_basic_executor import AlertBasicExecutor
        return await AlertBasicExecutor(self, gateway=gateway, query=query).execute(tenant_id, alert_id, operation_key, requested_by=requested_by)

    async def execute_incident(self, tenant_id, incident_id, operation_key: UUID, *, gateway=None, requested_by=None):
        """Trusted I entry: aggregate frozen members; no A query or Case start."""
        from .incident_diagnosis_executor import IncidentDiagnosisExecutor
        return await IncidentDiagnosisExecutor(self, gateway=gateway).execute(tenant_id, incident_id, operation_key, requested_by=requested_by)

    async def stop(self, tenant_id, run_id, *, state, code):
        if state not in {"failed", "cancelled", "unknown"} or not code.strip():
            raise StoreError("stage_stop_invalid", 422)
        async with self.transaction(tenant_id) as store:
            run, _, _ = await self.locked(store, run_id)
            if run["state"] == state and run["stop_reason"] == code:
                return
            if run["state"] not in {"running", "unknown"}:
                raise StoreError("stage_run_terminal")
            now = await store.now()
            await store.db.execute(update(R).where(*store.where(R, R.c.id == run_id)).values(state=state,
                ended_at=None if state == "unknown" else now, stop_reason=code, row_version=R.c.row_version + 1))
            if run["kind"] == "incident_diagnosis":
                await store.db.execute(update(D).where(*store.where(D, D.c.source_run_id == run_id)).values(
                    state=state, error={"code": code}))

    async def freshness(self, tenant_id, run_id):
        async with self.transaction(tenant_id, readonly=True) as store:
            run = await store.one(select(R).where(*store.where(R, R.c.id == run_id)))
            if not run:
                raise StoreError("stage_run_not_found", 404)
            _, key = parent(run["kind"])
            source = (await store.db.execute(select(F.c.content_json).where(*store.where(F, F.c.id == run["input_artifact_id"])))).scalar_one()
            return digest(source) == digest(await source_input(store, run["kind"], run[key],
                validated_triage="triage_validation_version" in source,
                with_queries="query_receipts_version" in source))
