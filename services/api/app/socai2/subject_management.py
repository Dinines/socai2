"""Atomic manual feedback and management, without model or scheduling calls."""
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid5

from sqlalchemy import func, insert, select, text, update

from app.models.socai2 import AlertAssessments, IncidentAlerts, Incidents

from .baseline_service import BaselineService
from .baseline_store import ACT, TGT, A, StoreError, digest
from .case_contracts import project
from .case_service import USERS
from .page_contracts import AlertFacts, IncidentFacts
from .subject_management_contracts import SubjectBatchReceipt, SubjectMutationReceipt

I, IA, ASSESS = Incidents.__table__, IncidentAlerts.__table__, AlertAssessments.__table__


def batch_limit():
    path = Path(os.environ.get("SOCAI2_MANAGEMENT_CONFIG_FILE", Path(__file__).with_suffix('.json')))
    value = json.loads(path.read_text())["max_batch_items"]
    if type(value) is not int or value < 1:
        raise ValueError("max_batch_items must be a positive integer")
    return value


class SubjectManagementService(BaselineService):
    async def apply(self, tenant_id, kind, targets, changes, operation_key, actor, *, feedback=False):
        if not targets or len(targets) > batch_limit() or len({t.id for t in targets}) != len(targets):
            raise StoreError("subject_batch_selection_invalid", 422)
        targets = sorted(targets, key=lambda t: t.id)
        table, facts_model, target_key = (A, AlertFacts, "alert_id") if kind == "alerts" else (I, IncidentFacts, "incident_id")
        action = "alert_feedback_recorded" if feedback else f"{kind}_management_updated"
        change_values = changes.model_dump(mode="json", exclude_unset=True,
                                           exclude={"operation_key", "expected_row_version"})
        intent = digest({"kind": kind, "action": action, "actor": str(actor.user_id),
                         "targets": [t.model_dump(mode="json") for t in targets], "changes": change_values})
        activity_id = uuid5(tenant_id, "socai2.subject.operation:" + str(operation_key))
        receipt_target_id = uuid5(activity_id, "receipt")
        lock_key = int.from_bytes(hashlib.sha256(activity_id.bytes).digest()[:8], "big", signed=True)
        async with self.transaction(tenant_id) as store:
            await store.db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
            prior = await store.one(select(TGT.c.after_value).where(*store.where(TGT, TGT.c.id == receipt_target_id)))
            if prior:
                receipt = prior["after_value"]["operation_receipt"]
                if receipt["request_hash"] != intent:
                    raise StoreError("operation_key_conflict")
                return SubjectBatchReceipt.model_validate(receipt["outcome"])
            if not await store.one(select(USERS.c.id).where(USERS.c.tenant_id == tenant_id, USERS.c.id == actor.user_id)):
                raise StoreError("subject_actor_not_in_tenant", 403)
            rows = []
            for target in targets:
                row = await store.one(select(table).where(*store.where(table, table.c.id == target.id)).with_for_update())
                if row is None:
                    raise StoreError("subject_not_found", 404)
                if row["row_version"] != target.expected_row_version:
                    raise StoreError("subject_row_version_conflict")
                rows.append(row)
            if (not feedback and changes.owner_id is not None
                    and not await store.one(select(USERS.c.id).where(USERS.c.tenant_id == tenant_id, USERS.c.id == changes.owner_id))):
                raise StoreError("subject_owner_not_in_tenant", 422)
            now = await store.now()
            # Calculate/validate all requested transitions before the first write.
            updates = [self.feedback_values(row, changes, actor, now) if feedback else
                       self.management_values(kind, row, changes, actor, now) for row in rows]
            outcomes = []
            for row, values in zip(rows, updates, strict=True):
                feedback_id = None
                if feedback:
                    feedback_id = uuid5(activity_id, "feedback:" + str(row["id"]))
                    await store.db.execute(insert(ASSESS).values(id=feedback_id, tenant_id=tenant_id,
                        alert_id=row["id"], kind="human_feedback", input_material_id=row["latest_material_id"],
                        verdict=changes.disposition, rationale=changes.reason, confidence=None,
                        score_state="not_provided", producer="socai2.manual-feedback.v1", actor=actor.snapshot(),
                        assessed_at=now, operation_key=str(feedback_id)))
                    values["latest_feedback_id"] = feedback_id
                changed = any(row[key] != value for key, value in values.items())
                if changed:
                    values.update(row_version=row["row_version"] + 1, business_updated_at=now)
                    await store.db.execute(update(table).where(*store.where(table, table.c.id == row["id"])).values(**values))
                saved = {**row, **values} if changed else row
                outcomes.append(SubjectMutationReceipt(kind=kind, facts=project(facts_model, saved),
                    changed=changed, feedback_id=feedback_id, activity_id=activity_id))
            if feedback:
                # Same Alert -> Incident order used by the existing stage writer.
                incident_ids = (await store.db.execute(select(IA.c.incident_id).where(*store.where(
                    IA, IA.c.alert_id.in_([r["id"] for r in rows]))).distinct().order_by(IA.c.incident_id))).scalars().all()
                for incident_id in incident_ids:
                    await store.db.execute(update(I).where(*store.where(I, I.c.id == incident_id)).values(
                        row_version=I.c.row_version + 1, business_updated_at=func.greatest(I.c.business_updated_at, now)))
            result = SubjectBatchReceipt(operation_key=operation_key, items=outcomes,
                                         changed_count=sum(o.changed for o in outcomes))
            await store.db.execute(insert(ACT).values(id=activity_id, tenant_id=tenant_id, operation_id=operation_key,
                actor=actor.snapshot(), action=action, **{"subject_" + target_key: rows[0]["id"]},
                occurred_at=now, summary=action, detail={"schema_version": "activity.v1",
                    "reason": change_values.get("reason") or change_values.get("resolution_note"),
                    "request_key": str(operation_key), "source": action,
                    "expected_version": None, "actual_version": None, "notes": []}))
            for index, (row, outcome) in enumerate(zip(rows, outcomes, strict=True)):
                after = outcome.facts.model_dump(mode="json")
                if index == 0:
                    after["operation_receipt"] = {"request_hash": intent, "outcome": result.model_dump(mode="json")}
                await store.db.execute(insert(TGT).values(
                    id=receipt_target_id if index == 0 else uuid5(activity_id, str(row["id"])),
                    tenant_id=tenant_id, activity_id=activity_id, **{target_key: row["id"]},
                    before_value=project(facts_model, row).model_dump(mode="json"), after_value=after,
                    result_state="succeeded", reason=change_values.get("reason") or change_values.get("resolution_note")))
            return result

    @staticmethod
    def feedback_values(row, changes, actor, now):
        values = {"disposition": changes.disposition}
        if changes.disposition in {"false_positive", "benign"} and row["handling_status"] != "completed":
            values.update(handling_status="completed", closed_at=now, closed_by=actor.user_id)
        elif changes.disposition in {"true_positive", "needs_review"} and row["handling_status"] == "completed":
            values.update(handling_status="in_progress", reopened_at=now, closed_at=None, closed_by=None)
        return values

    @staticmethod
    def management_values(kind, row, changes, actor, now):
        values = changes.model_dump(exclude_unset=True, exclude={"operation_key", "expected_row_version",
                    "reason", "resolution_note", "severity_override_reason"})
        if "owner_id" in values:
            owner = values["owner_id"]
            values.update(assignment_state="assigned" if owner else "unassigned", owner_source_value=None)
            values["assigned_at"] = (row["assigned_at"] if owner == row["owner_id"] else now) if owner else None
            if kind == "incidents" and owner is not None and row["handling_status"] != "resolved" and "handling_status" not in values:
                values["handling_status"] = "in_progress"
        status = values.get("handling_status", row["handling_status"])
        if kind == "alerts":
            if status == "completed" and "handling_status" in values and not changes.reason:
                raise StoreError("alert_close_reason_required", 422)
            if status != row["handling_status"]:
                if status == "completed":
                    values.update(closed_at=now, closed_by=actor.user_id)
                elif row["handling_status"] == "completed":
                    values.update(closed_at=None, closed_by=None, reopened_at=now)
        else:
            if "severity_override" in values:
                severity = values["severity_override"]
                # A reason edit is a real manual revision; an identical request is a no-op.
                if severity != row["severity_override"] or changes.severity_override_reason != row["severity_override_reason"]:
                    values.update(severity_override_reason=changes.severity_override_reason if severity else None,
                                  severity_override_by=actor.user_id if severity else None,
                                  severity_override_at=now if severity else None)
            if status == "resolved" and "handling_status" in values:
                values["resolution_note"] = changes.resolution_note
                if row["handling_status"] != "resolved":
                    values.update(resolved_at=now, resolved_by=actor.user_id)
            elif row["handling_status"] == "resolved" and status != "resolved":
                values.update(resolved_at=None, resolved_by=None, resolution_note=None, reopened_at=now)
        return values
