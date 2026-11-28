"""Case-scoped, read-only inputs for the story and focused-member directories."""
from collections import defaultdict
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import (
    String,
    and_,
    case,
    cast,
    func,
    literal,
    null,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB, JSONPATH

from app.models import socai2 as m

from .baseline_store import CA, RES, RM, A, F, R
from .case_data import Lookup, evidence_view, object_map
from .case_data_contracts import EvidenceIndex
from .incident_inputs import SELECTION_VERSION
from .run_directory import result_references
from .run_records import subject
from .stage_inputs import VERSION as STAGE_VERSION

CI, IA, M, O, S, V = (model.__table__ for model in (
    m.CaseIncidents, m.IncidentAlerts, m.AlertMaterials, m.AlertObjects,
    m.CaseAssessmentSources, m.TaskRevisions,
))
INPUT_UNVERIFIED = "frozen_input_membership_unverified"
MATERIAL_UNAVAILABLE = "current_member_material_unavailable"
CASE_INPUT_VERSION = "socai2.page-model.v1"
BAD_UUID = '$[*] ? (@.type() != "string" || !(@ like_regex "^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$"))'


def array_or_empty(value):
    return case((func.jsonb_typeof(value) == "array", value), else_=cast(literal("[]"), JSONB))


def valid_members(value):
    invalid = func.jsonb_path_exists(value, cast(literal(BAD_UUID), JSONPATH))
    return and_(func.jsonb_typeof(value) == "array", ~invalid)


async def evidence_references(store, case_row):
    identity = case_row["current_evidence_artifact_id"]
    if not identity:
        return []
    lookup = Lookup(store)
    artifact = await lookup("artifact", identity)
    if artifact is None or artifact["material_state"] != "complete" or artifact["blob_ref"] is not None:
        return []
    objects = {}
    try:
        objects = await object_map(store, EvidenceIndex.model_validate(artifact["content_json"]))
    except ValidationError:
        pass
    members = await store.members(case_row["id"])
    view = await evidence_view(case_row, members, artifact, lookup, objects)
    if view.state not in {"available", "partial"}:
        return []
    return [
        (ref.type, ref.id)
        for entry in view.entries
        for ref in (*entry.source_refs, *entry.verdict_sources,
                    *(entry.threat.source_refs if entry.threat else ()),
                    *((entry.remediation,) if entry.remediation else ()))
    ]


async def explicit_run_sources(store, case_row):
    """Load only saved, scoped source identities before querying the Run directory."""
    case_id = case_row["id"]
    targets = defaultdict(set)
    revision_ids = set()

    def link(target_type, target_id, source_type, source_id, task_id=None):
        if target_type == "task_revision":
            revision_ids.add(target_id)
        elif target_type in {"result", "artifact"}:
            targets[target_type, target_id].add((source_type, source_id, task_id))

    sources = await store.db.execute(select(S.c.result_id, S.c.artifact_id, S.c.task_revision_id).where(
        *store.where(S, S.c.case_id == case_id)))
    for row in sources.mappings():
        for kind in ("result", "artifact", "task_revision"):
            if identity := row[kind + "_id"]:
                link(kind, identity, kind, identity)
    for kind, identity in await evidence_references(store, case_row):
        link(kind, identity, "artifact", case_row["current_evidence_artifact_id"])

    seen = set()
    first = True
    while first or revision_ids - seen:
        selection = V.c.id.in_(revision_ids - seen)
        if first:
            selection = or_(selection, V.c.state == "completed")
            first = False
        rows = (await store.db.execute(select(V.c.id, V.c.task_id, V.c.source_refs).where(
            *store.where(V, V.c.case_id == case_id, selection)))).mappings().all()
        seen.update(revision_ids)
        seen.update(row["id"] for row in rows)
        for row in rows:
            for ref in row["source_refs"] or ():
                try:
                    kind, identity = ref["type"], UUID(ref["id"])
                except (KeyError, TypeError, ValueError, AttributeError):
                    continue
                link(kind, identity, "task_revision", row["id"], row["task_id"])

    relation_by_run = defaultdict(set)
    for kind, table, run_column, filters in (
        ("result", RES, RES.c.source_run_id, (RES.c.case_id == case_id,)),
        ("artifact", F, F.c.run_id, (or_(F.c.case_id == case_id, F.c.case_id.is_(None)),
                                   F.c.case_id.is_not_distinct_from(R.c.case_id),
                                   F.c.alert_id.is_not_distinct_from(R.c.alert_id),
                                   F.c.incident_id.is_not_distinct_from(R.c.incident_id))),
    ):
        identities = [identity for target, identity in targets if target == kind]
        if not identities:
            continue
        statement = select(table.c.id, run_column).join(R, and_(
            R.c.id == run_column, R.c.tenant_id == table.c.tenant_id,
        )).where(*store.where(table, table.c.id.in_(identities), *filters))
        for identity, run_id in (await store.db.execute(statement)).all():
            relation_by_run[run_id].update(targets[kind, identity])
    return relation_by_run


def frozen_input_ids():
    body = F.c.content_json
    case_ids = body["scope"]["alert_ids"]
    member_conditions = (
        RM.c.tenant_id == R.c.tenant_id, RM.c.case_id == R.c.case_id, RM.c.run_id == R.c.id,
    )
    case_rows = select(RM.c.alert_id).where(*member_conditions).correlate(R, F)
    case_scope = and_(
        R.c.case_id.is_not(None), R.c.state != "pending_update",
        F.c.schema_version == CASE_INPUT_VERSION, body["schema_version"].astext == CASE_INPUT_VERSION,
        body["run_kind"].astext == R.c.kind, valid_members(case_ids),
        select(func.count()).select_from(RM).where(*member_conditions).correlate(R, F).scalar_subquery()
        == func.jsonb_array_length(array_or_empty(case_ids)),
        ~case_rows.where(~case_ids.has_key(cast(RM.c.alert_id, String))).exists(),
    )

    legacy_ids = func.jsonb_path_query_array(
        body, cast(literal("$.members[*].alert.id"), JSONPATH), type_=JSONB,
    )
    legacy_valid = and_(
        func.jsonb_typeof(body["members"]) == "array",
        func.jsonb_array_length(array_or_empty(body["members"])) == func.jsonb_array_length(legacy_ids),
        valid_members(legacy_ids),
    )
    stage_scope = and_(
        F.c.schema_version == STAGE_VERSION, body["version"].astext == STAGE_VERSION,
        body["kind"].astext == R.c.kind,
    )
    selected = body["input_selection"]["selected_alert_ids"]
    incident_ids = case(
        (and_(body["selection_version"].astext == SELECTION_VERSION, valid_members(selected)), selected),
        (and_(~body.has_key("selection_version"), ~body.has_key("input_selection"), legacy_valid), legacy_ids),
        else_=null(),
    )
    return case(
        (case_scope, case_ids),
        (and_(stage_scope, R.c.kind == "alert_basic", legacy_valid,
              legacy_ids == func.jsonb_build_array(cast(R.c.alert_id, String))), legacy_ids),
        (and_(stage_scope, R.c.kind == "incident_diagnosis",
              body["parent"]["id"].astext == cast(R.c.incident_id, String)), incident_ids),
        else_=null(),
    ).label("input_ids")


class StoryRelations:
    def __init__(self, store, case_id, proofs):
        self.store, self.case_id, self.proofs = store, case_id, proofs
        self.members = select(A.c.id, A.c.event_time, A.c.latest_material_id, A.c.title,
                              A.c.description, A.c.severity).select_from(CA.join(A, and_(
            A.c.tenant_id == CA.c.tenant_id, A.c.id == CA.c.alert_id,
        ))).where(*store.where(CA, CA.c.case_id == case_id)).cte("story_members")
        self.objects = select(O.c.id, O.c.alert_id, O.c.material_id, O.c.object_type, O.c.namespace,
                              O.c.object_key, O.c.raw_value, O.c.normalized_value, O.c.source_path).join(self.members, and_(
            self.members.c.id == O.c.alert_id, self.members.c.latest_material_id == O.c.material_id,
        )).where(*store.where(O)).cte("story_current_objects")

        owned = and_(R.c.case_id == case_id, R.c.kind == "baseline")
        saved = and_(R.c.case_id == case_id, select(RES.c.id).where(*store.where(
            RES, RES.c.case_id == case_id, RES.c.source_run_id == R.c.id,
        )).exists())
        named = or_(owned, saved, R.c.id.in_(proofs))
        incident_ids = select(CI.c.incident_id).where(*store.where(CI, CI.c.case_id == case_id)).union(
            select(IA.c.incident_id).join(self.members, self.members.c.id == IA.c.alert_id).where(*store.where(IA)),
        )
        current_stage = or_(R.c.alert_id.in_(select(self.members.c.id)), R.c.incident_id.in_(incident_ids))
        inputs = select(R.c.id, R.c.case_id, R.c.alert_id, R.c.incident_id, R.c.kind, R.c.title, R.c.purpose,
                        R.c.state, R.c.delivery_state, R.c.requested_at, R.c.started_at, R.c.ended_at,
                        R.c.input_artifact_id, named.label("named"), current_stage.label("current_stage"),
                        frozen_input_ids()).select_from(R.outerjoin(F, and_(
            F.c.tenant_id == R.c.tenant_id, F.c.run_id == R.c.id, F.c.id == R.c.input_artifact_id,
            F.c.case_id.is_not_distinct_from(R.c.case_id), F.c.alert_id.is_not_distinct_from(R.c.alert_id),
            F.c.incident_id.is_not_distinct_from(R.c.incident_id), F.c.kind == "input_snapshot",
            F.c.material_state == "complete", F.c.blob_ref.is_(None),
        ))).where(*store.where(R, or_(named, current_stage, R.c.kind == "incident_diagnosis"))).cte("story_inputs")
        self.inputs = inputs
        overlap = and_(inputs.c.case_id.is_(None), select(self.members.c.id).where(
            inputs.c.input_ids.has_key(cast(self.members.c.id, String)),
        ).correlate(inputs).exists())
        self.runs = select(inputs, overlap.label("overlap")).where(
            or_(inputs.c.named, overlap),
        ).cte("story_investigations")

    async def investigation_count(self):
        # The relation contains one row per Run, regardless of the number of sources.
        return await self.store.db.scalar(select(func.count()).select_from(self.runs))

    def missing_material(self):
        exists = select(M.c.id).where(*self.store.where(M, M.c.alert_id == self.members.c.id,
                                                        M.c.id == self.members.c.latest_material_id)).exists()
        return select(func.count()).select_from(self.members).where(~exists)

    async def limitations(self):
        rows = self.inputs
        unknown = await self.store.db.scalar(select(select(rows.c.id).where(
            or_(rows.c.named, rows.c.current_stage), rows.c.input_ids.is_(None),
            rows.c.state != "pending_update",
            or_(rows.c.started_at.is_not(None), rows.c.input_artifact_id.is_not(None),
                rows.c.state.in_(("completed", "failed", "unknown"))),
        ).exists()))
        return [INPUT_UNVERIFIED] if unknown else []

    def shared_objects(self, alert_id):
        focus, other = self.objects.alias("focused_object"), self.objects.alias("peer_object")
        keys = ("object_type", "namespace", "object_key")
        groups = select(cast(func.min(cast(focus.c.id, String)), focus.c.id.type).label("focus_object_id"),
                        func.count(func.distinct(other.c.alert_id)).label("other_alert_count")).select_from(
            focus.join(other, and_(*(focus.c[k] == other.c[k] for k in keys))),
        ).where(focus.c.alert_id == alert_id, other.c.alert_id != alert_id).group_by(
            *(focus.c[k] for k in keys),
        ).subquery()
        return select(*(focus.c[k] for k in keys), focus.c.raw_value.label("label"),
                      focus.c.material_id.label("focus_material_id"), groups).join_from(
            focus, groups, groups.c.focus_object_id == focus.c.id,
        ).subquery()

    async def investigations(self, run_ids):
        if not run_ids:
            return {}
        rows = (await self.store.db.execute(select(self.runs).where(
            self.runs.c.id.in_(run_ids),
        ))).mappings().all()
        return await self.investigation_refs(rows)

    async def investigation_refs(self, rows):
        results = await result_references(self.store, rows)
        refs = {}
        for row in rows:
            run_id = row["id"]
            proofs = []
            if row["case_id"] == self.case_id and row["kind"] == "baseline":
                proofs.append(("case_owned", "case", self.case_id, None))
            proofs.extend(("saved_result", "result", result["id"], None) for result in results[run_id]
                          if result["result_type"] == "case_result" and row["case_id"] == self.case_id)
            proofs.extend(("explicit_reference", *source) for source in self.proofs.get(run_id, ()))
            if row["overlap"]:
                proofs.append(("frozen_member_overlap", "run", run_id, None))
            refs[run_id] = {
                "run_id": run_id, **subject(row), "run_kind": row["kind"], "title": row["title"],
                "state": row["state"], "delivery_state": row["delivery_state"], "requested_at": row["requested_at"],
                "result_refs": results[run_id],
                "relations": [{"kind": kind, "source_type": source, "source_id": identity, "task_id": task_id}
                              for kind, source, identity, task_id in sorted(set(proofs))],
            }
        return refs
