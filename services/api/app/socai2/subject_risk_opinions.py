"""Frozen I/C6 opinions and monotonic application, under the subject/Run lock."""
import copy
import hashlib
import json
from datetime import datetime
from uuid import UUID, uuid5

from sqlalchemy import insert, select, text, update

from app.models import socai2 as m

from .baseline_context import reference
from .baseline_store import StoreError, digest, encoded
from .severity_opinion import PATH, VERSION, Opinion
from .stage_delivery import Unit, original_value
from .subject_risk import load_policy
from .subject_risk_contracts import SubjectRisk

F, R, S = (t.__table__ for t in (m.Artifacts, m.Runs, m.RunSteps))
LEVELS = ("info", "low", "medium", "high", "critical")


def subject(run):
    if run["kind"] == "incident_diagnosis":
        return m.Incidents.__table__, "incident_id", "incident"
    if run["kind"] == "baseline":
        return m.Cases.__table__, "case_id", "case"
    raise StoreError("severity_opinion_stage_invalid", 422)


def identity(run, role):
    return uuid5(run["id"], VERSION + ":" + role)


async def read(store, run, role):
    row = await store.one(select(F).where(*store.where(F, F.c.run_id == run["id"], F.c.id == identity(run, role))))
    if row is None:
        return None
    body = row["content_json"]
    if row["material_state"] != "complete" or digest(body) != row["sha256"] or len(encoded(body)) != row["size_bytes"]:
        raise StoreError("severity_opinion_artifact_invalid", 422)
    return body


async def save(store, run, role, value, refs, *, step_id=None):
    value = {**value, "schema_version": VERSION}
    old = await read(store, run, role)
    if old is not None:
        if old != value:
            raise StoreError("severity_opinion_identity_conflict")
        return identity(run, role)
    # Compare the persisted envelope, not a caller's mutable dictionary.
    aid, now = identity(run, role), await store.now()
    if run["kind"] == "baseline":
        await store.save_input_artifact(run["case_id"], run["id"], aid, value, kind="source_snapshot",
            schema=VERSION, captured_at=now, refs=refs, actor_id=run.get("requested_by"), step_id=step_id)
    else:
        from .stage_results import artifact
        await artifact(store, run, aid, "source_snapshot", value, now, refs, step_id=step_id, schema_version=VERSION)
    return aid


async def members(store, kind, subject_id):
    a = m.Alerts.__table__
    link = m.CaseAlerts.__table__ if kind == "case" else m.IncidentAlerts.__table__
    rows = (await store.db.execute(select(a.c.id, a.c.latest_material_id).join(link,
        (link.c.tenant_id == a.c.tenant_id) & (link.c.alert_id == a.c.id)).where(
            *store.where(a), link.c[kind + "_id"] == subject_id).order_by(a.c.id))).mappings().all()
    return {str(row["id"]): str(row["latest_material_id"]) if row["latest_material_id"] else None for row in rows}


async def initialize_for_analysis(store, kind, subject_id, *, bump_version=True):
    """Initialize on explicit writes; management owns its single version increment."""
    table = m.Cases.__table__ if kind == "case" else m.Incidents.__table__
    row = await store.one(select(table).where(*store.where(table, table.c.id == subject_id)).with_for_update())
    if row is None:
        raise StoreError("subject_risk_subject_missing", 404)
    if row["risk_metadata"] is not None:
        return row
    policy = load_policy()
    risk = (await store.db.execute(text("""SELECT socai2.initialize_subject_risk(
        :tenant,:kind,:subject,CAST(:policy AS jsonb),NULL,NULL)"""),
        {"tenant": store.tenant_id, "kind": kind, "subject": subject_id, "policy": json.dumps(policy)})).scalar_one()
    previous = row.get("severity_override") if kind == "incident" else row.get("severity")
    values = {}
    if previous is not None:
        source = "manual_override" if kind == "incident" else row.get("severity_source")
        source = source if source in {"manual", "manual_override", "member_max", "model", "initial_policy"} else "unknown"
        risk["current"].update(level=previous, source=source,
            actor_id=str(row["severity_override_by"]) if row.get("severity_override_by") else None,
            reason_code="legacy_value_preserved")
        risk["manual_severity_revision"] = 1 if source in {"manual", "manual_override", "unknown"} else 0
        risk["system_priority"].update(value=policy["priority_by_severity"][previous], severity=previous)
        values.update(severity=previous, severity_source=source,
            priority_value=risk["system_priority"]["value"], priority_basis=risk["system_priority"])
    if row["priority_state"] == "available" and row["priority_source"] != "severity_mapping":
        # Preserve an existing value of unknown/manual origin; never relabel it as model output.
        risk["priority_override"] = {"value": float(row["priority_value"]), "source": row["priority_source"],
            "reason": "legacy_priority_preserved", "actor_id": None, "updated_at": risk["current"]["updated_at"]}
        values.update({k: row[k] for k in ("priority_value", "priority_state", "priority_source", "priority_basis")})
    risk = SubjectRisk.model_validate(risk).model_dump(mode="json")
    await store.db.execute(update(table).where(*store.where(table, table.c.id == subject_id)).values(
        risk_metadata=risk, row_version=table.c.row_version + int(bump_version), **values))
    return await store.one(select(table).where(*store.where(table, table.c.id == subject_id)))


def manual_stamp(row):
    return {k: str(row[k]) if row.get(k) is not None else None for k in
            ("severity_override", "severity_override_at", "severity_override_by", "severity_override_reason")}


async def freeze(store, run, *, selected_members, scope_kind="whole_case"):
    """Called after the Run is claimed, before any model or tool request."""
    if await read(store, run, "input") is not None:
        return identity(run, "input")
    table, key, kind = subject(run)
    row = await store.one(select(table).where(*store.where(table, table.c.id == run[key])).with_for_update())
    risk = SubjectRisk.model_validate(row["risk_metadata"])
    body = {"schema_version": VERSION, "type": "severity_opinion_input", "run_id": str(run["id"]),
        "subject_type": kind, "subject_id": str(run[key]), "started_at": run["started_at"].isoformat(),
        "manual_severity_revision": risk.manual_severity_revision, "manual_stamp": manual_stamp(row),
        "current_level": row["severity"], "policy": load_policy(), "scope_kind": scope_kind,
        "scope_revision": row.get("scope_revision"), "members": await members(store, kind, run[key]),
        "selected_members": {str(k): str(v) if v else None for k, v in selected_members.items()}}
    return await save(store, run, "input", body, [reference("artifact", run["input_artifact_id"], "execution_receipt")])


async def save_candidate(store, run, stage_step, received):
    frozen = await read(store, run, "input")
    if frozen is None:  # Historical Runs have no invented opinion contract.
        return None
    units = [u for u in received.get("retained_units", []) if u["path"] == PATH]
    if len(units) > 1:
        raise StoreError("severity_opinion_duplicate_unit", 422)
    unit = Unit.model_validate(units[0]).model_dump(mode="json") if units else None
    refs = [reference("artifact", identity(run, "input"), "execution_receipt")]
    if unit:
        Opinion.model_validate(unit["value"], strict=True)
        original_id = UUID(unit["original_artifact_id"])
        original = await store.one(select(F).where(*store.where(F, F.c.run_id == run["id"], F.c.id == original_id)))
        if (original is None or original["material_state"] != "complete"
                or digest(original["content_json"]) != original["sha256"]
                or len(encoded(original["content_json"])) != original["size_bytes"]):
            raise StoreError("severity_opinion_original_invalid", 422)
        content = original_value(original["content_json"], unit["original_content_path"])
        start, end = unit["value_span"]
        if (not isinstance(content, str) or end > len(content)
                or hashlib.sha256(content[start:end].encode()).hexdigest() != unit["value_sha256"]
                or json.loads(content[start:end]) != unit["value"]):
            raise StoreError("severity_opinion_original_mismatch", 422)
        request_id = UUID(original["content_json"]["request_artifact_id"])
        request = await store.one(select(F).where(*store.where(F, F.c.run_id == run["id"],
            F.c.id == request_id, F.c.kind == "model_request")))
        if (request is None or request["material_state"] != "complete"
                or digest(request["content_json"]) != request["sha256"]
                or len(encoded(request["content_json"])) != request["size_bytes"]):
            raise StoreError("severity_opinion_request_invalid", 422)
        saved_request = request["content_json"]
        source_map = (saved_request.get("payload") or saved_request).get("source_map", {})
        expected = [{"source_id": sid, "ref": source_map[sid]["ref"],
                     "alert_ids": source_map[sid].get("alert_ids", [])}
                    for sid in dict.fromkeys(unit["value"]["source_refs"])
                    if sid in source_map and source_map[sid]["ref"]["role"] != "execution_receipt"]
        restored = Unit.model_validate({**unit, "resolved_refs": expected}).model_dump(mode="json")
        if restored["resolved_refs"] != unit["resolved_refs"]:
            raise StoreError("severity_opinion_source_mapping_mismatch", 422)
        refs.append(reference("artifact", original_id, "prior_analysis", unit["original_content_path"]))
        refs.append(reference("artifact", request_id, "execution_receipt"))
    body = {"schema_version": VERSION, "type": "severity_opinion_candidate", "run_id": str(run["id"]),
        "stage": "C6" if run["kind"] == "baseline" else "I", "input_artifact_id": str(identity(run, "input")),
        "unit": unit, "missing_units": [u for u in received.get("missing_units", []) if u["path"] in {PATH, "$"}],
        "invalid_units": [u for u in received.get("invalid_units", []) if u["path"].startswith(PATH)]}
    return await save(store, run, "candidate", body, refs, step_id=stage_step)


def decision(row, frozen, candidate, *, run_state, current_members, current_scope_revision, fresh, newer):
    """Ordered eligibility checks. Complete units do not override unknown execution."""
    risk, unit = row["risk_metadata"], candidate["unit"]
    if run_state not in {"completed", "failed"}:
        return "execution_unconfirmed"
    if unit is None:
        return "opinion_missing_or_invalid"
    if risk["manual_severity_revision"] != frozen["manual_severity_revision"] or manual_stamp(row) != frozen["manual_stamp"]:
        return "manual_revision_changed"
    if row.get("severity_source") in {"manual", "manual_override"} and row["severity"] != frozen["current_level"]:
        return "manual_revision_changed"
    if (current_members != frozen["members"] or current_scope_revision != frozen["scope_revision"]
            or any(current_members.get(k) != v or k not in current_members for k, v in frozen["selected_members"].items())):
        return "frozen_scope_changed"
    if frozen["subject_type"] == "case" and (frozen["scope_kind"] != "whole_case" or set(frozen["selected_members"]) != set(current_members)):
        return "local_scope_only"
    if not frozen["selected_members"]:
        return "scope_unavailable"
    if not fresh:
        return "input_changed"
    if newer:
        return "newer_round_exists"
    before, proposed = LEVELS.index(row["severity"]), LEVELS.index(unit["value"]["level"])
    return "raised" if proposed > before else "lower_not_applied" if proposed < before else "unchanged"


async def apply_saved(store, run):
    """Same transaction as terminal publication; immutable processing receipt is the idempotency key."""
    table, key, kind = subject(run)
    row = await store.one(select(table).where(*store.where(table, table.c.id == run[key])).with_for_update())
    run = await store.one(select(R).where(*store.where(R, R.c.id == run["id"])).with_for_update())
    previous = await read(store, run, "application")
    if previous is not None:
        return previous
    frozen, candidate = await read(store, run, "input"), await read(store, run, "candidate")
    if frozen is None:
        return None
    if candidate is None:
        await save_candidate(store, run, None, {"missing_units": [
            {"path": PATH, "reason_code": "no_admitted_opinion_response"}]})
        candidate = await read(store, run, "candidate")
    fresh = False
    if kind == "case":
        fresh = (await store.input_freshness(run["id"]))["state"] == "current"
    else:
        from .stage_results import source_input
        saved = await store.one(select(F.c.content_json).where(*store.where(F, F.c.id == run["input_artifact_id"])))
        source = saved["content_json"]
        current = await source_input(store, run["kind"], run[key],
            validated_triage="triage_validation_version" in source, with_queries="query_receipts_version" in source,
            with_citation_quality="triage_citation_quality_version" in source,
            incident_limit=source.get("input_selection", {}).get("limit"))
        from .stage_inputs import comparison_source
        fresh = digest(comparison_source(current, risk_version=source.get("risk_input_version"))) == digest(comparison_source(source))
    later = await store.one(select(R.c.id).where(*store.where(R, R.c[key] == run[key], R.c.kind == run["kind"],
        R.c.started_at > run["started_at"])).limit(1))
    risk = copy.deepcopy(row["risk_metadata"])
    last = risk.get("latest_opinion")
    newer = bool(later or last and datetime.fromisoformat(last["started_at"]) > run["started_at"])
    unsettled = await store.one(select(S.c.id).where(*store.where(S, S.c.run_id == run["id"],
        S.c.state.in_(["running", "planned", "unknown"]))).limit(1))
    reason = decision(row, frozen, candidate, run_state="unknown" if unsettled else run["state"],
        current_members=await members(store, kind, run[key]), current_scope_revision=row.get("scope_revision"),
        fresh=fresh, newer=newer)
    now = await store.now()
    opinion = candidate["unit"]["value"] if candidate["unit"] else None
    link = {"run_id": str(run["id"]), "artifact_id": str(identity(run, "candidate")),
        "application_artifact_id": str(identity(run, "application")), "started_at": run["started_at"].isoformat(),
        "processed_at": now.isoformat(), "reason_code": reason, "level": opinion["level"] if opinion else None}
    before = {k: row[k] for k in ("severity", "severity_source")}
    values = {}
    if reason == "raised":
        level = opinion["level"]
        risk["current"] = {"level": level, "source": "model", "updated_at": now.isoformat(), "actor_id": None,
            "reason_code": "model_raise", "opinion": link}
        values.update(severity=level, severity_source="model")
    if reason in {"raised", "lower_not_applied", "unchanged"}:
        level = values.get("severity", row["severity"])
        risk["system_priority"] = {"value": frozen["policy"]["priority_by_severity"][level], "severity": level,
            "computed_at": now.isoformat(), "mapping_version": frozen["policy"]["version"]}
        if not risk.get("priority_override"):
            values.update(priority_value=risk["system_priority"]["value"], priority_state="available",
                priority_source="severity_mapping", priority_basis=risk["system_priority"])
    if last is None or datetime.fromisoformat(last["started_at"]) <= run["started_at"]:
        risk["latest_opinion"] = link
    risk = SubjectRisk.model_validate(risk).model_dump(mode="json")
    await store.db.execute(update(table).where(*store.where(table, table.c.id == run[key])).values(
        **values, risk_metadata=risk, row_version=table.c.row_version + 1))
    outcome = {"schema_version": VERSION, "type": "severity_opinion_application", **link,
        "before": before, "after": {"severity": values.get("severity", row["severity"]),
            "severity_source": values.get("severity_source", row["severity_source"])},
        "frozen_manual_revision": frozen["manual_severity_revision"], "current_manual_revision": risk["manual_severity_revision"]}
    await save(store, run, "application", outcome, [reference("artifact", identity(run, "candidate"), "execution_receipt")])
    if reason in {"raised", "lower_not_applied"}:
        act, target = m.Activities.__table__, m.ActivityTargets.__table__
        aid = identity(run, "activity")
        await store.db.execute(insert(act).values(id=aid, tenant_id=store.tenant_id,
            operation_id=identity(run, "application"), **{"subject_" + key: run[key]}, occurred_at=now,
            actor={"type": "service", "user_id": None, "name_snapshot": None,
                "service_name": "socai2.subject-risk", "service_version": VERSION},
            action="severity_raised" if reason == "raised" else "severity_lower_suggested",
            summary=reason, detail={"schema_version": "activity.v1", "reason": opinion["reason"],
                "request_key": str(identity(run, "application")), "source": VERSION,
                "expected_version": None, "actual_version": row["row_version"] + 1, "notes": []}))
        await store.db.execute(insert(target).values(id=identity(run, "activity_target"), tenant_id=store.tenant_id,
            activity_id=aid, **{key: run[key]}, before_value=before,
            after_value={**outcome["after"], "severity_opinion": link}, result_state="succeeded"))
    return outcome
