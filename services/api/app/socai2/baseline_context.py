"""C1 source selection and frozen context. This is not a model prompt.

Mutable pointers and their rows are selected in ONE PostgreSQL statement. Raw
materials remain in their immutable versions, and are read by exact ID later.
"""
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, JsonValue, ValidationError
from sqlalchemy import text

from .baseline_contracts import Contract, Question, Scope
from .stage_inputs import Freshness, freshness_sql

SCHEMA = "socai2.baseline-context.v1"
PROJECTION = "socai2.baseline-manifest.v2"
# Preserve the existing source snapshot retention ceiling. Never silently take
# the first N members or enlarge the downstream model budget to fit a Case.
MAX_CONTEXT_BYTES = 131072


def feedback_validity(revision, member_ids):
    """Keep historical scope literal; never expand 'whole_case' to new members."""
    reasons = []
    if revision["state"] != "completed" or not (revision.get("result_text") or "").strip():
        reasons.append("feedback_not_submitted")
    try:
        scope = Scope.model_validate(revision.get("result_scope"))
    except ValidationError:
        reasons.append("feedback_scope_not_provided_or_invalid")
    else:
        declared = set(map(str, scope.alert_ids))
        if not declared:
            reasons.append("feedback_scope_empty")
        if declared - set(map(str, member_ids)):
            reasons.append("feedback_scope_extends_beyond_case")
    return not reasons, reasons


class AlertInput(Contract):
    alert: dict[str, JsonValue]
    membership: dict[str, JsonValue]
    material: dict[str, JsonValue] | None
    source_refs: list[dict[str, JsonValue]]
    objects: list[dict[str, JsonValue]]
    triage: dict[str, JsonValue] | None
    feedback: dict[str, JsonValue] | None
    limitations: list[str]
    # Defaults preserve parsing of historical frozen v1 contexts.
    triage_freshness: Freshness = "unverified"
    triage_usable: bool | None = None


class IncidentInput(Contract):
    incident: dict[str, JsonValue]
    linked_from_case: bool
    member_ids: list[UUID]
    case_member_ids: list[UUID]
    member_links: list[dict[str, JsonValue]]
    diagnosis: dict[str, JsonValue] | None
    diagnosis_usable: bool
    limitations: list[str]
    diagnosis_freshness: Freshness = "unverified"


class TaskInput(Contract):
    task_id: UUID
    revision: dict[str, JsonValue]
    usable_feedback: bool
    limitations: list[str]


class Omission(Contract):
    section: str
    source_id: UUID | None
    reason: str


class Context(Contract):
    schema_version: Literal["socai2.baseline-context.v1"]
    case_id: UUID
    captured_at: AwareDatetime
    scope: Scope
    case: dict[str, JsonValue]
    alerts: dict[str, AlertInput]
    incidents: dict[str, IncidentInput]
    tasks: dict[str, TaskInput]
    current_assessment: dict[str, JsonValue] | None
    assessment_members: list[dict[str, JsonValue]]
    assessment_sources: list[dict[str, JsonValue]]
    prior_results: dict[str, dict[str, JsonValue]]
    adopted_task_revisions: dict[str, dict[str, JsonValue]]
    adopted_artifacts: dict[str, dict[str, JsonValue]]
    questions: list[Question]
    omissions: list[Omission]
    # Only these paths may be cited through this context artifact. A diagnosis
    # remains prior analysis; completing a human task never makes it observation.
    citation_roles: dict[str, Literal["source_label", "prior_analysis", "human_statement", "execution_receipt"]]


CAPTURE_SQL = """
WITH c AS MATERIALIZED (
 SELECT * FROM socai2.cases WHERE tenant_id=:tenant AND id=:case
), a AS MATERIALIZED (
 SELECT a.* FROM socai2.alerts a JOIN socai2.case_alerts ca
 ON ca.tenant_id=a.tenant_id AND ca.alert_id=a.id
 WHERE ca.tenant_id=:tenant AND ca.case_id=:case
), current_judgment AS MATERIALIZED (
 SELECT j.* FROM socai2.case_assessments j JOIN c ON j.id=c.current_assessment_id
 WHERE j.tenant_id=:tenant AND j.case_id=:case
), judgment_sources AS MATERIALIZED (
 SELECT s.* FROM socai2.case_assessment_sources s JOIN current_judgment j ON j.id=s.assessment_id
 WHERE s.tenant_id=:tenant AND s.case_id=:case
), relevant_incidents AS MATERIALIZED (
 SELECT incident_id FROM socai2.case_incidents WHERE tenant_id=:tenant AND case_id=:case
 UNION SELECT ia.incident_id FROM socai2.incident_alerts ia JOIN a ON a.id=ia.alert_id
 WHERE ia.tenant_id=:tenant
)
SELECT jsonb_build_object(
 'captured_at',clock_timestamp(), 'case',(SELECT to_jsonb(c) FROM c),
 'alerts',COALESCE((SELECT jsonb_object_agg(a.id::text,jsonb_build_object(
   'alert',to_jsonb(a),
   'membership',(SELECT to_jsonb(ca) FROM socai2.case_alerts ca
      WHERE ca.tenant_id=:tenant AND ca.case_id=:case AND ca.alert_id=a.id),
   'material',(SELECT jsonb_build_object('id',m.id,'revision',m.revision,
      'received_at',m.received_at,'source_version',m.source_version,
      'detection',m.detection,'enrichment',m.enrichment,'source_scope',m.source_scope,
      'material_state',m.material_state,'sha256',m.sha256,'retention',m.retention,
      'has_raw',NULLIF(m.raw_text,'') IS NOT NULL
        OR (m.raw_json IS NOT NULL AND m.raw_json<>'null'::jsonb)
        OR (m.ocsf_json IS NOT NULL AND m.ocsf_json<>'null'::jsonb))
      FROM socai2.alert_materials m WHERE m.tenant_id=:tenant AND m.alert_id=a.id AND m.id=a.latest_material_id),
   'source_refs',COALESCE((SELECT jsonb_agg(to_jsonb(s) ORDER BY s.id) FROM socai2.alert_source_refs s
      WHERE s.tenant_id=:tenant AND s.alert_id=a.id AND s.material_id=a.latest_material_id),'[]'),
   'objects',COALESCE((SELECT jsonb_agg(to_jsonb(o) ORDER BY o.object_key,o.id) FROM socai2.alert_objects o
      WHERE o.tenant_id=:tenant AND o.alert_id=a.id AND o.material_id=a.latest_material_id),'[]'),
   'triage_freshness',__TRIAGE_FRESHNESS__,
   'triage',(SELECT to_jsonb(t) FROM socai2.alert_assessments t WHERE t.tenant_id=:tenant
      AND t.alert_id=a.id AND t.id=a.latest_triage_id AND t.kind='triage'),
   'feedback',(SELECT to_jsonb(t) FROM socai2.alert_assessments t WHERE t.tenant_id=:tenant
      AND t.alert_id=a.id AND t.id=a.latest_feedback_id AND t.kind='human_feedback')
 ) ORDER BY a.id) FROM a),'{}'),
 'incidents',COALESCE((SELECT jsonb_object_agg(i.id::text,jsonb_build_object(
   'incident',to_jsonb(i),
   'linked_from_case',EXISTS(SELECT 1 FROM socai2.case_incidents ci
      WHERE ci.tenant_id=:tenant AND ci.case_id=:case AND ci.incident_id=i.id),
   'member_ids',COALESCE((SELECT jsonb_agg(ia.alert_id ORDER BY ia.alert_id) FROM socai2.incident_alerts ia
      WHERE ia.tenant_id=:tenant AND ia.incident_id=i.id),'[]'),
   'member_links',COALESCE((SELECT jsonb_agg(to_jsonb(ia) ORDER BY ia.alert_id)
      FROM socai2.incident_alerts ia JOIN a ON a.id=ia.alert_id
      WHERE ia.tenant_id=:tenant AND ia.incident_id=i.id),'[]'),
   'diagnosis_freshness',__DIAGNOSIS_FRESHNESS__,
   'diagnosis',(SELECT to_jsonb(d) FROM socai2.incident_diagnoses d WHERE d.tenant_id=:tenant
      AND d.incident_id=i.id AND d.id=i.latest_diagnosis_id)
 ) ORDER BY i.id) FROM socai2.incidents i JOIN relevant_incidents ri ON ri.incident_id=i.id
 WHERE i.tenant_id=:tenant),'{}'),
 'tasks',COALESCE((SELECT jsonb_object_agg(t.id::text,jsonb_build_object('task_id',t.id,'revision',to_jsonb(v)) ORDER BY t.id)
   FROM socai2.tasks t JOIN socai2.task_revisions v ON v.id=t.current_revision_id AND v.task_id=t.id
   AND v.tenant_id=t.tenant_id AND v.case_id=t.case_id WHERE t.tenant_id=:tenant AND t.case_id=:case),'{}'),
 'current_assessment',(SELECT to_jsonb(j) FROM current_judgment j),
 'assessment_members',COALESCE((SELECT jsonb_agg(to_jsonb(m) ORDER BY m.alert_id)
   FROM socai2.case_assessment_members m JOIN current_judgment j ON j.id=m.assessment_id
   WHERE m.tenant_id=:tenant AND m.case_id=:case),'[]'),
 'assessment_sources',COALESCE((SELECT jsonb_agg(to_jsonb(s) ORDER BY s.id) FROM judgment_sources s),'[]'),
 'prior_results',COALESCE((SELECT jsonb_object_agg(r.id::text,
   to_jsonb(r)||jsonb_build_object('member_deliveries',COALESCE((SELECT jsonb_agg(to_jsonb(m) ORDER BY m.alert_id)
      FROM socai2.result_members m WHERE m.tenant_id=:tenant AND m.result_id=r.id),'[]')) ORDER BY r.id)
   FROM socai2.results r WHERE r.tenant_id=:tenant AND r.case_id=:case
   AND (r.id=CAST(:comparison AS uuid) OR r.id IN (SELECT result_id FROM judgment_sources))),'{}'),
 'adopted_task_revisions',COALESCE((SELECT jsonb_object_agg(v.id::text,to_jsonb(v) ORDER BY v.id)
   FROM socai2.task_revisions v WHERE v.tenant_id=:tenant AND v.case_id=:case
   AND v.id IN (SELECT task_revision_id FROM judgment_sources)),'{}'),
 'adopted_artifacts',COALESCE((SELECT jsonb_object_agg(f.id::text,
   to_jsonb(f)-ARRAY['content_json','content_text','blob_ref'] ORDER BY f.id)
   FROM socai2.artifacts f WHERE f.tenant_id=:tenant AND f.case_id=:case
   AND f.id IN (SELECT artifact_id FROM judgment_sources)),'{}')
)
"""


CAPTURE_SQL = CAPTURE_SQL.replace("__TRIAGE_FRESHNESS__", freshness_sql("alert_basic", "a.id",
    "SELECT t.source_run_id FROM socai2.alert_assessments t WHERE t.tenant_id=:tenant AND t.alert_id=a.id AND t.id=a.latest_triage_id AND t.kind='triage'"))
CAPTURE_SQL = CAPTURE_SQL.replace("__DIAGNOSIS_FRESHNESS__", freshness_sql("incident_diagnosis", "i.id",
    "SELECT d.source_run_id FROM socai2.incident_diagnoses d WHERE d.tenant_id=:tenant AND d.incident_id=i.id AND d.id=i.latest_diagnosis_id"))


QUESTIONS = (
    ("detection_facts", "原始记录支持哪些行为和对象？", "原始材料和具体来源；检测标签本身不是攻击事实"),
    ("member_relationships", "成员告警之间有哪些已证实的行为联系？", "同对象、时间邻近与有证据的行为连接分开"),
    ("behavior_nature", "恶意、正常或误操作等解释分别有哪些依据和反证？", "可追溯行为证据与替代解释；不以单个标签或分数定性"),
    ("authorization", "谁确认了哪些行为、对象和时间的授权？", "明确授权材料或人工反馈及适用范围；未提供不等于不存在"),
    ("impact", "哪些影响已经观察到，哪些只是待核的可能影响？", "影响对象、行为与证据；图可达不等于受影响"),
    ("coverage", "还有哪些未处理成员、来源缺口、矛盾和后续事项？", "全部成员的读取/分析覆盖、工具状态与明确限制"),
)


async def capture(db, tenant_id, case_id, request) -> Context:
    """Called with the Case and pending Run locked, before any Run input freezes."""
    raw = (await db.execute(text(CAPTURE_SQL), {"tenant": tenant_id, "case": case_id,
        "comparison": request.comparison_result_id})).scalar_one()
    omissions, roles = [], {"$.case": "source_label"}

    def omit(section, source_id, reason):
        omissions.append(Omission(section=section, source_id=source_id, reason=reason))

    member_ids = set(raw["alerts"])
    for aid, item in raw["alerts"].items():
        reasons = []
        material = item["material"]
        if material is None:
            reasons.append("source_material_not_available")
        elif material["material_state"] != "complete" or not material["has_raw"]:
            reasons.append("source_material_" + (material["material_state"] if material["has_raw"] else "no_raw"))
        for name, pointer in [("triage", "latest_triage_id"), ("feedback", "latest_feedback_id")]:
            value = item[name]
            if value:
                if value["input_material_id"] != item["alert"]["latest_material_id"]:
                    reasons.append(name + "_different_material_version")
                roles[f"$.alerts.{aid}.{name}"] = "prior_analysis" if name == "triage" else "human_statement"
            elif item["alert"][pointer]:
                reasons.append(name + "_reference_invalid")
        item["triage_usable"] = bool(item["triage"] and item["triage_freshness"] == "current")
        if item["triage"] and not item["triage_usable"]:
            reasons.append("triage_input_" + item["triage_freshness"])
            roles.pop(f"$.alerts.{aid}.triage", None)
        roles[f"$.alerts.{aid}.alert"] = "source_label"
        if item["alert"].get("event_time") is not None:
            roles[f"$.alerts.{aid}.alert.event_time"] = "source_label"
        roles[f"$.alerts.{aid}.membership"] = "execution_receipt"
        roles[f"$.alerts.{aid}.objects"] = "source_label"
        if material:
            roles[f"$.alerts.{aid}.material"] = "source_label"
        item["limitations"] = reasons
        for reason in reasons:
            omit("alerts", aid, reason)
    if not raw["case"].get("description"):
        omit("case", case_id, "description_not_provided")
    if not raw["incidents"]:
        omit("incidents", None, "no_linked_incident")
    for iid, item in raw["incidents"].items():
        reasons, diagnosis = [], item["diagnosis"]
        item["case_member_ids"] = sorted(set(item["member_ids"]) & member_ids)
        validity = (diagnosis.get("diagnosis") or {}).get("validation_state") if diagnosis else None
        item["diagnosis_usable"] = bool(diagnosis and diagnosis["state"] == "completed"
                                       and validity == "accepted" and item["case_member_ids"]
                                       and item["diagnosis_freshness"] == "current")
        if set(item["member_ids"]) - member_ids:
            reasons.append("incident_scope_extends_beyond_case")
        if not item["case_member_ids"]:
            reasons.append("no_current_member_overlap")
        if not diagnosis:
            reasons.append("diagnosis_not_available")
        elif diagnosis["state"] != "completed":
            reasons.append("diagnosis_" + diagnosis["state"])
        elif validity != "accepted":
            reasons.append("diagnosis_not_validated")
        if diagnosis and item["diagnosis_freshness"] != "current":
            reasons.append("diagnosis_input_" + item["diagnosis_freshness"])
        if item["diagnosis_usable"]:
            roles[f"$.incidents.{iid}.diagnosis"] = "prior_analysis"
        roles[f"$.incidents.{iid}.incident"] = "source_label"
        roles[f"$.incidents.{iid}.member_links"] = "source_label"
        item["limitations"] = reasons
        for reason in reasons:
            omit("incidents", iid, reason)
    for tid, item in raw["tasks"].items():
        revision = item["revision"]
        usable, reasons = feedback_validity(revision, member_ids)
        item.update(usable_feedback=usable, limitations=reasons)
        roles[f"$.tasks.{tid}.revision"] = "human_statement" if usable else "execution_receipt"
        for reason in reasons:
            omit("tasks", revision["id"], reason)
    if not any(t["usable_feedback"] for t in raw["tasks"].values()):
        omit("tasks", None, "no_current_completed_feedback")
    judgment = raw["current_assessment"]
    if judgment:
        roles["$.current_assessment"] = "prior_analysis"
        if judgment["scope_revision"] != raw["case"]["scope_revision"]:
            omit("current_assessment", judgment["id"], "assessment_scope_outdated")
    for rid in raw["prior_results"]:
        roles[f"$.prior_results.{rid}"] = "prior_analysis"
    for vid in raw["adopted_task_revisions"]:
        revision = raw["adopted_task_revisions"][vid]
        usable, reasons = feedback_validity(revision, member_ids)
        roles[f"$.adopted_task_revisions.{vid}"] = "human_statement" if usable else "execution_receipt"
        for reason in reasons:
            omit("adopted_task_revisions", vid, reason)
    for fid in raw["adopted_artifacts"]:
        roles[f"$.adopted_artifacts.{fid}"] = "execution_receipt"
    scope = Scope(kind="whole_case", alert_ids=sorted(member_ids), object_keys=sorted({
        obj["object_key"] for alert in raw["alerts"].values() for obj in alert["objects"]}),
        window_start=request.window_start, window_end=request.window_end, limitations=[])
    questions = [Question(id=key, text=question, scope=scope, evidence_requirements=[requirement],
        state="open", answer=None, evidence_refs=[], limitations=[]) for key, question, requirement in QUESTIONS]
    return Context(schema_version=SCHEMA, case_id=case_id, scope=scope,
                   questions=questions, omissions=omissions, citation_roles=roles, **raw)


def reference(kind, identity, role, path=None):
    return {"type": kind, "id": str(identity), "external": None, "source_path": path,
            "row_keys": [], "role": role}


def selected_refs(context):
    refs = [reference("alert_material", a.material["id"], "observation")
            for a in context.alerts.values() if a.material]
    task_ids = {t.revision["id"] for t in context.tasks.values() if t.usable_feedback}
    task_ids.update(vid for vid in context.adopted_task_revisions
                    if context.citation_roles[f"$.adopted_task_revisions.{vid}"] == "human_statement")
    refs += [reference("task_revision", tid, "human_statement") for tid in sorted(task_ids)]
    refs += [reference("result", rid, "prior_analysis") for rid in sorted(context.prior_results)]
    refs += [reference("artifact", fid, "prior_analysis") for fid in sorted(context.adopted_artifacts)]
    return refs
