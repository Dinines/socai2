"""Explicit, source-bound historical alert cards. No generated summaries or verdicts."""
import json
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import text

from .baseline_optional_sources import SourceUnavailable
from .baseline_store import digest
from .knowledge_config import at

PURPOSE = "historical_case_reference"
SCHEMA = "socai2.historical-alert-card.v1"
LIMITATIONS = ["historical_reference_not_current_case_observation", "not_independently_verified",
              "prior_verdict_not_current_verdict", "human_statement_not_business_authorization",
              "recommendation_not_executed_response", "selected_material_fields_not_complete_activity_history"]
READ = """SELECT to_jsonb(a) AS alert, to_jsonb(m) AS material,
 to_jsonb(t) AS triage, to_jsonb(f) AS feedback,
 (SELECT r.state FROM socai2.runs r WHERE r.tenant_id=a.tenant_id
  AND r.id=t.source_run_id AND r.alert_id=a.id) AS triage_run_state,
 COALESCE((SELECT jsonb_agg(to_jsonb(o) ORDER BY o.id) FROM socai2.alert_objects o
 WHERE o.tenant_id=a.tenant_id AND o.alert_id=a.id AND o.material_id=m.id),'[]'::jsonb) AS objects
 FROM socai2.alerts a
 LEFT JOIN socai2.alert_materials m ON m.tenant_id=a.tenant_id AND m.alert_id=a.id AND m.id=a.latest_material_id
 LEFT JOIN socai2.alert_assessments t ON t.tenant_id=a.tenant_id AND t.alert_id=a.id
 AND t.id=a.latest_triage_id AND t.kind='triage'
 LEFT JOIN socai2.alert_assessments f ON f.tenant_id=a.tenant_id AND f.alert_id=a.id
 AND f.id=a.latest_feedback_id AND f.kind='human_feedback'
 WHERE a.tenant_id=:tenant AND a.id=:alert_id"""
INSERT = """INSERT INTO public.aisoc_kb_documents
 (id,tenant_id,title,doc_kind,source_url,content,tags,chunk_index,chunk_total,created_by)
 VALUES (:id,:tenant,:title,'other',:url,:content,CAST(:tags AS text[]),0,1,:actor)
 ON CONFLICT (id) DO NOTHING"""


def selected(value, keys):
    return {key: value.get(key) for key in keys}


def assessment_usability(row):
    states = {}
    for key in ("triage", "feedback"):
        value = row[key]
        states[key] = ("not_recorded" if not value else
            "assessment_body_missing" if not value.get("verdict") or not (value.get("rationale") or "").strip() else
            "different_or_unknown_material" if value.get("input_material_id") != row["material"]["id"] else
            "source_run_not_completed" if key == "triage" and value.get("source_run_id")
                and row.get("triage_run_state") != "completed" else "usable_saved_judgment")
    return states


def card_from(row, profile):
    alert, material = row["alert"], row["material"]
    if material is None or material.get("material_state") != "complete":
        raise SourceUnavailable("history_complete_material_missing")
    if not alert.get("event_time"):
        raise SourceUnavailable("history_event_time_missing")
    if not row["triage"] and not row["feedback"]:
        raise SourceUnavailable("history_assessment_missing")
    if "usable_saved_judgment" not in assessment_usability(row).values():
        raise SourceUnavailable("history_aligned_usable_assessment_missing")
    assessment_fields = ("id", "alert_id", "input_material_id", "source_run_id", "kind", "verdict", "rationale",
                         "recommendations", "confidence", "score_state", "producer", "actor", "assessed_at")
    observations = []
    for path in profile.history.observation_paths:
        value = at(material, path)
        if value is not None and value != "":
            observations.append({"source_path": path, "value": value, "role": "historical_material"})
    card = {"schema_version": SCHEMA,
        "source": {"alert_id": alert["id"], "material_id": material["id"], "material_revision": material["revision"],
            "material_sha256": material["sha256"], "triage_id": row["triage"]["id"] if row["triage"] else None,
            "feedback_id": row["feedback"]["id"] if row["feedback"] else None},
        "event": selected(alert, ("title", "event_time", "source_namespace", "original_vendor", "severity")),
        "detection": material["detection"], "observations": observations,
        "objects": [selected(o, ("object_type", "namespace", "object_key", "normalized_value", "source_path"))
                    for o in row["objects"]],
        "triage": selected(row["triage"], assessment_fields) if row["triage"] else None,
        "feedback": selected(row["feedback"], assessment_fields) if row["feedback"] else None,
        "material_alignment": {key: ("not_recorded" if not row[key] else
            "unknown" if row[key].get("input_material_id") is None else
            "same_material" if row[key]["input_material_id"] == material["id"] else "different_material")
            for key in ("triage", "feedback")},
        "verification": "not_independently_verified", "limitations": LIMITATIONS}
    if len(serialize(card)) > profile.history.max_card_characters:
        raise SourceUnavailable("history_card_exceeds_limit")
    return card


def serialize(card):
    return json.dumps(card, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def document_id(tenant, card):
    return uuid5(NAMESPACE_URL, f"{SCHEMA}:{tenant}:{digest(card)}")


def parse(doc, profile):
    try:
        card = json.loads(doc["content"])
        if (card["schema_version"] != SCHEMA or str(document_id(doc["tenant_id"], card)) != str(doc["id"])
                or not profile.history or doc["chunk_total"] != 1 or doc["chunk_index"] != 0
                or len(doc["content"]) > profile.history.max_card_characters):
            raise ValueError
        UUID(card["source"]["alert_id"])
        datetime.fromisoformat(card["event"]["event_time"])
        return card
    except (KeyError, ValueError, TypeError):
        raise SourceUnavailable("history_card_invalid") from None


async def source_row(db, tenant, aid):
    rows = list((await db.execute(text(READ), {"tenant": tenant, "alert_id": UUID(str(aid))})).mappings())
    return rows[0] if rows else None


async def import_cards(db, tenant, ids, actor, profile, *, expected_hashes=None):
    if not profile.history or PURPOSE not in profile.purposes:
        raise SourceUnavailable("history_knowledge_not_configured")
    if len(ids) > profile.history.max_import_alerts:
        raise SourceUnavailable("history_import_limit")
    results = []
    for aid in dict.fromkeys(ids):
        row = await source_row(db, tenant, aid)
        try:
            if row is None:
                raise SourceUnavailable("history_alert_not_found")
            card = card_from(row, profile)
            if expected_hashes is not None and expected_hashes.get(str(aid)) != digest(card):
                raise SourceUnavailable("history_sync_source_changed")
        except SourceUnavailable as exc:
            results.append({"alert_id": str(aid), "state": "not_imported", "reason": str(exc)})
            continue
        ident = document_id(tenant, card)
        await db.execute(text(INSERT), {"id": ident, "tenant": tenant,
            "title": f"历史告警参考 · {row['alert']['title']} · {ident}", "content": serialize(card),
            "url": f"/api/v1/socai2/alerts/{aid}/materials/{card['source']['material_id']}",
            "tags": [profile.purposes[PURPOSE].tag], "actor": actor})
        results.append({"alert_id": str(aid), "state": "stored", "document_id": str(ident),
                        "source": card["source"], "indexed": False, "verification": card["verification"]})
    await db.commit()
    return {"state": "completed", "cards": results}


async def index_payload(db, tenant, doc, profile):
    card = parse(doc, profile)
    row = await source_row(db, tenant, card["source"]["alert_id"])
    if row is None or card_from(row, profile) != card:
        raise SourceUnavailable("history_card_source_changed_or_mismatched")
    return {"source_alert_id": card["source"]["alert_id"],
            "event_epoch": datetime.fromisoformat(card["event"]["event_time"]).timestamp()}


def in_scope(card, filters):
    source = card["source"]
    event = datetime.fromisoformat(card["event"]["event_time"])
    return (source["alert_id"] not in filters["exclude_alert_ids"]
            and datetime.fromisoformat(filters["event_start"]) <= event
            < datetime.fromisoformat(filters["event_before"]))


async def retrieval_record(db, tenant, doc, profile, filters):
    card = parse(doc, profile)
    if not in_scope(card, filters):
        raise SourceUnavailable("history_hit_outside_scope")
    row = await source_row(db, tenant, card["source"]["alert_id"])
    pointers = {"material_id": "latest_material_id", "triage_id": "latest_triage_id", "feedback_id": "latest_feedback_id"}
    state = "source_missing" if row is None else "superseded"
    usability = None
    if row is not None:
        try:
            current = card_from(row, profile)
            usability = assessment_usability(row)
            if all(card["source"][key] == row["alert"].get(pointer) for key, pointer in pointers.items()) and current == card:
                state = "current"
        except SourceUnavailable as exc:
            state = str(exc)
    return {**card, "source_version_state": state, "assessment_usability": usability}
