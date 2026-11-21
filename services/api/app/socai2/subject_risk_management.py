"""Manual subject risk edits inside the existing management transaction and lock."""
import copy

from sqlalchemy import select

from app.models import socai2 as m

from .subject_risk import load_policy
from .subject_risk_contracts import SubjectRisk
from .subject_risk_opinions import LEVELS, initialize_for_analysis

PRIORITY_FIELDS = {"priority_value", "priority_reason", "clear_priority_override"}
RISK_FIELDS = {"severity", "severity_source", "risk_metadata", "priority_value", "priority_state",
              "priority_source", "priority_basis"}


async def rule_basis(store, kind, subject_id, policy, now):
    alerts, materials = m.Alerts.__table__, m.AlertMaterials.__table__
    link = m.CaseAlerts.__table__ if kind == "case" else m.IncidentAlerts.__table__
    rows = (await store.db.execute(select(alerts.c.id.label("alert_id"),
        alerts.c.latest_material_id.label("material_id"), materials.c.revision.label("material_revision"),
        alerts.c.severity).select_from(alerts.join(link,
            (link.c.tenant_id == alerts.c.tenant_id) & (link.c.alert_id == alerts.c.id))
        .outerjoin(materials, (materials.c.tenant_id == alerts.c.tenant_id)
            & (materials.c.alert_id == alerts.c.id) & (materials.c.id == alerts.c.latest_material_id)))
        .where(*store.where(alerts), link.c[kind + "_id"] == subject_id).order_by(alerts.c.id))).mappings().all()
    known = [r["severity"] for r in rows if r["severity"] in LEVELS]
    return {"level": max(known, key=LEVELS.index) if known else policy["unknown_initial_severity"],
        "source": "member_max" if known else "initial_policy",
        "members": [{"alert_id": str(r["alert_id"]),
            "material_id": str(r["material_id"]) if r["material_id"] else None,
            "material_revision": r["material_revision"], "severity": r["severity"]} for r in rows],
        "evaluated_at": now.isoformat(),
        "reason_code": "highest_known_member" if known else "source_severity_missing"}


async def values(store, kind, row, changes, actor):
    """Caller checks the pre-initialization version and saves one operation receipt."""
    prepared = await initialize_for_analysis(store, kind, row["id"], bump_version=False)
    result = {key: prepared[key] for key in RISK_FIELDS} if row["risk_metadata"] is None else {}
    level_key = "severity" if kind == "case" else "severity_override"
    reason_key = "severity_reason" if kind == "case" else "severity_override_reason"
    severity_edit = level_key in changes.model_fields_set
    priority_edit = "priority_value" in changes.model_fields_set or changes.clear_priority_override
    if not severity_edit and not priority_edit:
        return result
    risk = copy.deepcopy(prepared["risk_metadata"])
    policy, now = load_policy(), await store.now()
    if severity_edit:
        requested = getattr(changes, level_key)
        reason = getattr(changes, reason_key)
        basis = await rule_basis(store, kind, row["id"], policy, now) if requested is None else None
        level = basis["level"] if basis else requested.value
        source = basis["source"] if basis else "manual" if kind == "case" else "manual_override"
        risk["current"] = {"level": level, "source": source, "updated_at": now.isoformat(),
            "actor_id": str(actor.user_id), "reason_code": "manual_rule_restore" if basis else "manual_set",
            "reason": reason, "rule_basis": basis}
        risk["manual_severity_revision"] += 1
        result.update(severity=level, severity_source=source)
        if kind == "incident":
            # Legacy columns remain a last manual-setting record, not a permanent lock.
            result.update(severity_override=level if requested is not None else None,
                severity_override_reason=reason if requested is not None else None,
                severity_override_by=actor.user_id if requested is not None else None,
                severity_override_at=now if requested is not None else None)
    level = risk["current"]["level"]
    risk["system_priority"] = {"value": policy["priority_by_severity"][level], "severity": level,
        "computed_at": now.isoformat(), "mapping_version": policy["version"]}
    if changes.clear_priority_override:
        risk["priority_override"] = None
    elif "priority_value" in changes.model_fields_set:
        risk["priority_override"] = {"value": changes.priority_value, "source": "manual",
            "reason": changes.priority_reason, "actor_id": str(actor.user_id), "updated_at": now.isoformat()}
    override = risk.get("priority_override")
    if priority_edit and override:
        result.update(priority_value=override["value"], priority_state="available",
            priority_source=override["source"], priority_basis=override)
    elif not override:
        result.update(priority_value=risk["system_priority"]["value"], priority_state="available",
            priority_source="severity_mapping", priority_basis=risk["system_priority"])
    result["risk_metadata"] = SubjectRisk.model_validate(risk).model_dump(mode="json")
    return result


def reasons(changes):
    """Keep mixed edits' reasons individually, including a cleared override's reason."""
    names = ("severity_reason", "severity_override_reason", "priority_reason", "reason", "resolution_note")
    return {name: getattr(changes, name) for name in names
            if name in changes.model_fields_set and getattr(changes, name, None) is not None}
