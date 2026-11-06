"""Small page-data writer/reader. No executor, model or inferred defaults."""
import json
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import select, update

from app.models import socai2 as m

from .baseline_store import C, F, StoreError, digest
from .case_data_contracts import (
    KIND,
    SCHEMA,
    CaseDataReceipt,
    CasePageData,
    EvidenceIndex,
    EvidenceView,
)

TABLES = {"alert_material": m.AlertMaterials.__table__, "artifact": F,
          "result": m.Results.__table__, "task_revision": m.TaskRevisions.__table__,
          "assessment": m.CaseAssessments.__table__}


def pointer(row, path):
    value = row
    if path is not None:
        try:
            for token in path.split("/")[1:]:
                token = token.replace("~1", "/").replace("~0", "~")
                value = value[int(token)] if isinstance(value, list) and token.isdigit() else value[token]
        except (KeyError, IndexError, TypeError, ValueError):
            raise StoreError("evidence_source_path_not_found", 422) from None
    return value


def as_ids(values):
    return {str(x) for x in values}


# Observation is opt-in at known behavior leaves. Unregistered paths and
# containers remain source_label: absence of a known label is not evidence
# that a field contains a direct observation.
OCSF_OBSERVATION_PATHS = {
    ("time",), ("start_time",), ("end_time",),
    ("device", "hostname"), ("device", "name"), ("device", "ip"),
    ("process", "cmd_line"), ("process", "pid"), ("process", "name"),
    ("process", "file", "path"), ("process", "parent_process", "pid"),
    ("actor", "process", "cmd_line"), ("actor", "process", "pid"),
    ("actor", "user", "name"), ("user", "name"),
    ("src_endpoint", "ip"), ("src_endpoint", "port"),
    ("dst_endpoint", "ip"), ("dst_endpoint", "port"),
    ("file", "path"), ("file", "name"),
}


def material_role(parts, row, value):
    if parts == ["raw_json", "event"] and (row.get("raw_json") or {}).get("record_kind") == "synthetic_page_data":
        return "observation" if isinstance(value, str) else "source_label"
    ocsf_path = parts[1:] if parts[0] == "ocsf_json" else parts[2:] if parts[:2] == ["raw_json", "ocsf_event"] else []
    if tuple(ocsf_path) in OCSF_OBSERVATION_PATHS and isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return "observation"
    return "source_label"


def source_binding(ref, row):
    """Resolve role and members at the selected saved path, never at Run level."""
    path = ref.source_path
    if path is None:
        raise StoreError("evidence_source_path_required", 422)
    parts = [p.replace("~1", "/").replace("~0", "~") for p in path.split("/")[1:]]
    value = pointer(row, path)
    if ref.type == "alert_material":
        if parts[0] in {"raw_json", "ocsf_json"}:
            role = material_role(parts, row, value)
        elif parts[0] in {"detection", "source_scope"}:
            role = "source_label"
        else:
            raise StoreError("evidence_source_path_unregistered", 422)
        return role, {str(row["alert_id"])}
    if ref.type == "result":
        if parts[0] not in {"conclusion", "findings", "questions", "case_impact"}:
            raise StoreError("evidence_source_path_unregistered", 422)
        members = as_ids(row.get("_alert_ids", []))
        if parts[0] in {"findings", "questions"}:
            if len(parts) < 2 or not parts[1].isdigit():
                raise StoreError("evidence_source_path_unregistered", 422)
            item = row[parts[0]][int(parts[1])]
            members = as_ids((item.get("scope") or {}).get("alert_ids", []))
        return "prior_analysis", members
    if ref.type == "task_revision":
        if parts[0] not in {"result_text", "result_scope"}:
            raise StoreError("evidence_source_path_unregistered", 422)
        return "human_statement", as_ids((row.get("result_scope") or {}).get("alert_ids", []))
    # v1 supports C1's explicitly frozen per-alert role directory. Other
    # artifact formats remain readable as materials, but are not silently
    # promoted into new independent evidence entries.
    body = row.get("content_json") or {}
    if row["schema_version"] == "socai2.baseline-context.v1" and row["kind"] == "source_snapshot":
        if len(parts) < 4 or parts[:2] != ["content_json", "alerts"]:
            raise StoreError("evidence_source_path_unregistered", 422)
        key = "$." + ".".join(parts[1:])
        roles = body.get("citation_roles", {})
        matches = [p for p in roles if key == p or key.startswith(p+".")]
        if not matches:
            raise StoreError("evidence_source_path_unregistered", 422)
        return roles[max(matches, key=len)], {parts[2]}
    if (row["schema_version"] == "socai2.response-receipt.v1" and row["kind"] == "source_snapshot"
            and row.get("_response_receipt") and path == "/content_json"
            and body.get("state") in {"approved", "rejected", "executed", "failed", "cancelled"}):
        return "execution_receipt", as_ids(body.get("alert_ids", []))
    raise StoreError("evidence_source_schema_unregistered", 422)


async def validate_sources(index, tenant_id, case_id, lookup, objects):
    """Resolve saved rows and paths. This proves provenance, not truth of labels."""
    for entry in index.entries:
        members = as_ids(entry.alert_ids)
        refs = [*entry.source_refs, *entry.verdict_sources,
                *(entry.threat.source_refs if entry.threat else []),
                *([entry.remediation] if entry.remediation else [])]
        resolved, bound = {}, {}
        for ref in refs:
            row = await lookup(ref.type, ref.id)
            if row is None or str(row["tenant_id"]) != str(tenant_id):
                raise StoreError("evidence_source_not_found", 422)
            if ref.type == "alert_material":
                valid = str(row["alert_id"]) in members
                roles = {"observation", "source_label"}
            elif ref.type == "artifact":
                valid = str(row.get("case_id")) == str(case_id) or (
                    row.get("case_id") is None and str(row.get("alert_id")) in members)
                if row["kind"] == KIND:
                    valid = False  # an index is a directory, not primary evidence
                roles = {"execution_receipt", "prior_analysis"}
                if row["kind"] in {"source_snapshot", "tool_response", "attachment"}:
                    roles |= {"observation", "source_label"}
                if row.get("material_state") == "unavailable":
                    valid = False
                if row.get("_alert_ids") is not None and not members <= as_ids(row["_alert_ids"]):
                    valid = False
            elif ref.type == "result":
                valid = str(row["case_id"]) == str(case_id) and members <= as_ids(row.get("_alert_ids", []))
                roles = {"prior_analysis"}
            else:
                valid = str(row["case_id"]) == str(case_id) and row["state"] == "completed"
                valid = valid and members <= as_ids((row.get("result_scope") or {}).get("alert_ids", []))
                roles = {"human_statement"}
            if not valid or ref.role not in roles:
                raise StoreError("evidence_source_scope_or_role_invalid", 422)
            role, scope = source_binding(ref, row)
            if role != ref.role or not scope or not scope <= members:
                raise StoreError("evidence_source_scope_or_role_invalid", 422)
            key = (ref.type, ref.id, ref.source_path)
            resolved[key], bound[key] = pointer(row, ref.source_path), scope
            if ref is entry.remediation and not (ref.type == "artifact" and row.get("_response_receipt")
                    and row["schema_version"] == "socai2.response-receipt.v1"):
                raise StoreError("evidence_remediation_receipt_unverified", 422)
        for group in (entry.source_refs, entry.verdict_sources if entry.verdict != "unknown" else [],
                      entry.threat.source_refs if entry.threat else []):
            if group and set().union(*(bound[(r.type, r.id, r.source_path)] for r in group)) != members:
                raise StoreError("evidence_sources_do_not_cover_entry", 422)
        for obj in entry.object_keys:
            if (str(obj.material_id), obj.object_key) not in objects or str(objects[(str(obj.material_id), obj.object_key)]) not in members:
                raise StoreError("evidence_object_not_in_material_scope", 422)
        # Explicit labels are stored verbatim with their role, never inferred
        # from a command or free-form model paragraph.
        if entry.verdict != "unknown":
            labels = []
            for ref in entry.verdict_sources:
                if ref.role not in {"source_label", "prior_analysis", "human_statement"}:
                    raise StoreError("evidence_verdict_role_invalid", 422)
                value = resolved[(ref.type, ref.id, ref.source_path)]
                labels.append(value.get("verdict") if isinstance(value, dict) else value)
            if entry.verdict == "conflicting":
                known = {v for v in labels if isinstance(v, str) and v in {"malicious", "suspicious", "clean"}}
                if len(known) < 2:
                    raise StoreError("evidence_conflict_sources_missing", 422)
            elif entry.verdict not in labels:
                raise StoreError("evidence_verdict_not_in_source", 422)
        if entry.threat:
            expected = entry.threat.model_dump(exclude={"source_refs"})
            if not any(isinstance(value := resolved[(r.type, r.id, r.source_path)], dict)
                       and all(value.get(k) == v for k, v in expected.items()) for r in entry.threat.source_refs):
                raise StoreError("evidence_threat_not_in_source", 422)


async def evidence_view(cas, members, artifact, lookup, objects):
    identity = cas.get("current_evidence_artifact_id")
    base = {"artifact_id": identity, "evidence_count": None, "threat_count": None,
                "covered_alert_ids": [], "uncovered_alert_ids": sorted(members, key=str),
                "excluded_evidence_ids": [], "entries": [], "limitations": [], "index": None}
    if identity is None:
        return EvidenceView(state="not_recorded", **base)
    try:
        if not artifact or str(artifact["tenant_id"]) != str(cas["tenant_id"]) or str(artifact["case_id"]) != str(cas["id"]) or artifact["kind"] != KIND or artifact["schema_version"] != SCHEMA:
            raise StoreError("evidence_pointer_invalid", 422)
        index = EvidenceIndex.model_validate(artifact["content_json"])
        if artifact.get("sha256") != digest(index.model_dump(mode="json")):
            raise StoreError("evidence_index_digest_invalid", 422)
        await validate_sources(index, cas["tenant_id"], cas["id"], lookup, objects)
    except (ValidationError, StoreError) as exc:
        return EvidenceView(state="invalid_reference", **{**base, "limitations": [
            exc.code if isinstance(exc, StoreError) else "evidence_schema_invalid"]})
    base.update(index=index, limitations=index.limitations)
    if index.availability_state == "unavailable":
        return EvidenceView(state="unavailable", **base)
    selected = [e for e in index.entries if e.state == "active" and set(e.alert_ids) <= members]
    excluded = [e.evidence_id for e in index.entries if not set(e.alert_ids) <= members]
    covered = set(index.alert_ids) & members
    partial = index.availability_state == "partial" or set(index.alert_ids) != members or index.scope_revision != cas["scope_revision"]
    threats = {(e.threat.namespace, e.threat.key) for e in selected
               if e.verdict in {"malicious", "suspicious"} and e.threat is not None}
    return EvidenceView(**{**base, "state": "partial" if partial else "available",
        "evidence_count": len(selected), "threat_count": len(threats), "entries": selected,
        "covered_alert_ids": sorted(covered, key=str), "uncovered_alert_ids": sorted(members-covered, key=str),
        "excluded_evidence_ids": excluded,
        "limitations": [*index.limitations, *(["case_membership_changed"] if partial and index.availability_state == "available" else [])]})


class Lookup:
    def __init__(self, store):
        self.store, self.cache = store, {}

    async def __call__(self, kind, identity):
        key = (kind, str(identity))
        if key not in self.cache:
            t = TABLES[kind]
            row = await self.store.one(select(t).where(*self.store.where(t, t.c.id == identity)))
            row = dict(row) if row else None
            if row and (kind == "result" or kind == "artifact" and row.get("run_id")):
                table = m.ResultMembers.__table__ if kind == "result" else m.RunMembers.__table__
                clause = table.c.result_id == identity if kind == "result" else table.c.run_id == row["run_id"]
                row["_alert_ids"] = list((await self.store.db.execute(select(table.c.alert_id).where(*self.store.where(table, clause)))).scalars())
            if row and kind == "artifact" and row["schema_version"] == "socai2.response-receipt.v1":
                links = m.ResponseLinks.__table__
                row["_response_receipt"] = bool(await self.store.one(select(links.c.id).where(*self.store.where(links,
                    links.c.receipt_artifact_id == identity, links.c.case_id == row["case_id"])).limit(1)))
            self.cache[key] = row
        return self.cache[key]


async def object_map(store, index):
    materials = {obj.material_id for e in index.entries for obj in e.object_keys}
    if not materials:
        return {}
    t = m.AlertObjects.__table__
    rows = (await store.db.execute(select(t.c.material_id, t.c.object_key, t.c.alert_id).where(
        *store.where(t, t.c.material_id.in_(materials))))).mappings()
    return {(str(r["material_id"]), r["object_key"]): r["alert_id"] for r in rows}


async def read_page_data(store, cas):
    members = await store.members(cas["id"])
    lookup = Lookup(store)
    artifact = await lookup("artifact", cas["current_evidence_artifact_id"]) if cas.get("current_evidence_artifact_id") else None
    objects = {}
    if artifact:
        try:
            objects = await object_map(store, EvidenceIndex.model_validate(artifact["content_json"]))
        except ValidationError:
            pass
    view = await evidence_view(cas, members, artifact, lookup, objects)
    assessment = None
    if cas["current_assessment_id"]:
        row = await lookup("assessment", cas["current_assessment_id"])
        if row is None or row["case_id"] != cas["id"]:
            raise StoreError("current_assessment_reference_invalid")
        cover, source = m.CaseAssessmentMembers.__table__, m.CaseAssessmentSources.__table__
        assessment = {k: row[k] for k in ("id", "conclusion", "origin", "validity", "scope_revision", "formed_at", "adopted_at")}
        covered = await store.db.execute(select(cover.c.alert_id).where(
            *store.where(cover, cover.c.assessment_id == row["id"], cover.c.case_id == cas["id"])))
        assessment["alert_ids"] = sorted(covered.scalars(), key=str)
        sources = await store.db.execute(select(source).where(
            *store.where(source, source.c.assessment_id == row["id"], source.c.case_id == cas["id"])))
        assessment["sources"] = sorted([dict(r) for r in sources.mappings()], key=lambda r: str(r["id"]))
    return CasePageData(classification=cas.get("classification"), due_at=cas.get("due_at"),
        determination=assessment["conclusion"] if assessment else None, assessment=assessment, evidence=view)


async def export_page_data(tables):
    """Reuse the reader's evidence checks on a single saved DB snapshot."""
    mapping = {"alert_material": "alert_materials", "artifact": "artifacts",
               "result": "results", "task_revision": "task_revisions", "assessment": "case_assessments"}
    outputs = []
    for cas in tables["cases"]:
        tenant, cid = cas["tenant_id"], cas["id"]
        def owned(name, tenant=tenant):
            return [r for r in tables.get(name, []) if str(r["tenant_id"]) == str(tenant)]
        async def lookup(kind, identity):
            row = next((dict(r) for r in owned(mapping[kind]) if str(r["id"]) == str(identity)), None)
            if row and (kind == "result" or kind == "artifact" and row.get("run_id")):
                name, field, value = ("result_members", "result_id", identity) if kind == "result" else ("run_members", "run_id", row["run_id"])
                row["_alert_ids"] = [r["alert_id"] for r in owned(name) if str(r[field]) == str(value)]
            if row and kind == "artifact" and row["schema_version"] == "socai2.response-receipt.v1":
                row["_response_receipt"] = any(str(r.get("receipt_artifact_id")) == str(identity)
                    and str(r.get("case_id")) == str(row["case_id"]) for r in owned("response_links"))
            return row
        members = {UUID(str(r["alert_id"])) for r in owned("case_alerts") if str(r["case_id"]) == str(cid)}
        objects = {(str(r["material_id"]), r["object_key"]): r["alert_id"] for r in owned("alert_objects")}
        artifact = await lookup("artifact", cas["current_evidence_artifact_id"]) if cas.get("current_evidence_artifact_id") else None
        evidence = await evidence_view(cas, members, artifact, lookup, objects)
        assessment = None
        if cas["current_assessment_id"]:
            row = await lookup("assessment", cas["current_assessment_id"])
            if not row or str(row["case_id"]) != str(cid):
                raise StoreError("export_assessment_reference_invalid", 422)
            assessment = {k: row[k] for k in ("id", "conclusion", "origin", "validity", "scope_revision", "formed_at", "adopted_at")}
            assessment["alert_ids"] = sorted([r["alert_id"] for r in owned("case_assessment_members") if str(r["assessment_id"]) == str(row["id"])], key=str)
            assessment["sources"] = sorted([r for r in owned("case_assessment_sources") if str(r["assessment_id"]) == str(row["id"])], key=lambda r: str(r["id"]))
        page = CasePageData(classification=cas.get("classification"), due_at=cas.get("due_at"),
            determination=assessment["conclusion"] if assessment else None, assessment=assessment, evidence=evidence)
        outputs.append({"tenant_id": str(tenant), "case_id": str(cid), "case_row_version": cas["row_version"],
            "current_assessment_id": str(cas["current_assessment_id"]) if cas["current_assessment_id"] else None,
            "page_data": page.model_dump(mode="json")})
    return outputs


async def write_data(service, tenant_id, case_id, request, actor, *, evidence=False):
    action = "case_evidence_published" if evidence else "case_management_data_updated"
    intent = digest({"actor": str(actor.user_id), "request": request.model_dump(mode="json")})
    async with service.transaction(tenant_id) as store:
        await service.actor(store, actor)
        cas = await store.case(case_id)
        prior = await store.receipt(case_id, request.operation_key, action)
        if prior:
            if prior["request_hash"] != intent:
                raise StoreError("operation_key_conflict")
            return CaseDataReceipt.model_validate(prior["outcome"])
        if cas["row_version"] != request.expected_row_version:
            raise StoreError("case_row_version_conflict")
        now, values = await store.now(), {}
        if evidence:
            index, current = request.index, cas["current_evidence_artifact_id"]
            if request.expected_current_artifact_id != current or index.supersedes_artifact_id != current:
                raise StoreError("case_evidence_version_conflict")
            if index.scope_revision != cas["scope_revision"]:
                raise StoreError("case_scope_revision_conflict")
            members = await store.members(case_id)
            if not set(index.alert_ids) <= members or index.availability_state == "available" and set(index.alert_ids) != members:
                raise StoreError("evidence_index_scope_invalid", 422)
            lookup = Lookup(store)
            if current:
                old = await lookup("artifact", current)
                if not old or old["case_id"] != case_id or old["kind"] != KIND or old["schema_version"] != SCHEMA:
                    raise StoreError("evidence_previous_index_invalid", 422)
            await validate_sources(index, tenant_id, case_id, lookup, await object_map(store, index))
            payload = index.model_dump(mode="json")
            if len(json.dumps(payload, ensure_ascii=False).encode()) > 1048576:
                raise StoreError("evidence_index_too_large", 422)
            identity = uuid4()
            refs = [r.model_dump(mode="json") for e in index.entries for r in e.source_refs]
            await store.save_input_artifact(case_id, None, identity, payload, kind=KIND, schema=SCHEMA,
                captured_at=now, refs=refs, actor_id=actor.user_id)
            values = {"current_evidence_artifact_id": identity}
        else:
            values = {"classification": request.classification, "due_at": request.due_at}
        changed = any(cas[k] != v for k, v in values.items())
        before = {k: str(cas[k]) if cas[k] is not None else None for k in values}
        after = {k: str(v) if v is not None else None for k, v in values.items()}
        if changed:
            await store.db.execute(update(C).where(*store.where(C, C.c.id == case_id)).values(
                **values, row_version=C.c.row_version+1, business_updated_at=now))
        out = CaseDataReceipt(case_id=case_id, row_version=cas["row_version"]+int(changed), changed=changed,
            current_evidence_artifact_id=values.get("current_evidence_artifact_id", cas["current_evidence_artifact_id"]))
        await store.event(case_id, request.operation_key, actor.snapshot(), action,
            {"request_hash": intent, "outcome": out.model_dump(mode="json"),
             "source": "manual" if evidence else request.source,
             "source_note": None if evidence else request.source_note}, [("case_id", case_id, before, after)])
        return out
