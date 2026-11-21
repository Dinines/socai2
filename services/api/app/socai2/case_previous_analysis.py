"""Freeze selected, already admitted analysis from the immediately preceding Run.

Original responses are checked against saved spans, never parsed for new units.
Only business judgments enter the model view; provenance stays in C1's copy.
"""
import copy
import re
from uuid import UUID, uuid4

from sqlalchemy import select

from .baseline_context import reference
from .baseline_store import F, StoreError, digest, encoded
from .stage_delivery import validate_sources

VERSION = "socai2.previous-analysis-material.v1"
PREFIX = "$.update_context.previous_analysis_material.units."
FIELDS = {
    "members": ("state", "summary", "limitations"),
    "findings": ("state", "statement", "limitations", "alternatives"),
    "questions": ("state", "answer", "limitations"),
    "conclusion": ("state", "text", "limitations"),
    "answer": ("state", "text", "limitations", "alternatives"),
}


class Sources:
    def __init__(self, rows, tenant, case, run):
        self.rows = {str(r["id"]): r for r in rows}
        self.owner = tuple(map(str, (tenant, case, run)))
        self.used = {}

    def read(self, identity):
        row = self.rows[str(identity)]
        value = row["content_json"]
        if (tuple(str(row[k]) for k in ("tenant_id", "case_id", "run_id")) != self.owner
                or row["material_state"] != "complete" or row.get("blob_ref") is not None
                or digest(value) != row["sha256"] or len(encoded(value)) != row["size_bytes"]):
            raise ValueError("previous_analysis_source_invalid")
        self.used[str(identity)] = {k: str(row[k]) if k == "id" else row[k]
                                  for k in ("id", "sha256", "kind", "schema_version")}
        return value

    def receipt(self, identity):
        body = self.read(identity)
        originals = {o["artifact_id"]: self.read(o["artifact_id"]) for o in body["originals"]}
        receipt = validate_sources(body, originals).model_dump(mode="json")
        self.read(receipt["input_artifact_id"])
        if receipt["run_id"] != self.owner[2]:
            raise ValueError("previous_analysis_receipt_run_mismatch")
        return receipt

    def bodies(self, predicate):
        # These are program-owned published summaries, not arbitrary originals.
        return [(str(r["id"]), self.read(r["id"])) for r in self.rows.values()
                if predicate(r.get("content_json") or {})]


def project(rows, tenant, case, run, members, *, comparable=False):
    sources = Sources(rows, tenant, case, run)
    contexts = sources.bodies(lambda c: c.get("schema_version") == "socai2.baseline-context.v1")
    if not contexts:
        return {"version": VERSION, "source_run_id": str(run), "units": [], "sources": [],
                "omissions": ["previous_context_unavailable"]}
    if len(contexts) != 1:
        raise ValueError("previous_analysis_context_ambiguous")
    context = contexts[0][1]
    scope = context["scope"]
    questions = {q["id"]: q for q in context["questions"]}
    units, seen, omissions = [], set(), []

    def add(stage, summary_id, receipt_id, raw, kind, value, declared, identity=None):
        key = kind, identity
        if key in seen or not set(declared["alert_ids"]) & set(map(str, members)):
            return
        if not set(declared["alert_ids"]) <= set(scope["alert_ids"]):
            raise ValueError("previous_analysis_scope_invalid")
        selected = ({"summary": value} if kind == "summary" else
                    {k: copy.deepcopy(value[k]) for k in FIELDS[kind] if k in value})
        # Scope/IDs and evidence arrays were restored separately. Prose remains
        # exactly as saved, including unresolved limitations and alternatives.
        raw_value = raw["value"]
        if kind == "summary" and value != raw_value:
            raise ValueError("previous_analysis_prose_mismatch")
        if isinstance(raw_value, dict) and any(k in raw_value and raw_value[k] != v for k, v in selected.items()):
            raise ValueError("previous_analysis_prose_mismatch")
        if kind in {"questions", "answer"}:
            selected["question"] = questions[identity]["text"]
        selected.update(source_stage=stage, material_kind=kind)
        units.append({"kind": kind, "identity": identity, "source_stage": stage,
            "summary_artifact_id": summary_id, "receipt_artifact_id": receipt_id,
            "unit_path": raw["path"], "original_artifact_id": raw["original_artifact_id"],
            "value_sha256": raw["value_sha256"], "declared_scope": copy.deepcopy(declared),
            "applicable_alert_ids": sorted(set(declared["alert_ids"]) & set(map(str, members))), "value": selected})
        seen.add(key)

    def analysis(stage, summary_id, descriptor, fields):
        if not descriptor or not descriptor.get("artifact_id"):
            omissions.append(stage + "_admission_receipt_unavailable")
            return
        rid = descriptor["artifact_id"]
        receipt = sources.receipt(rid)
        if not receipt["stage"].startswith(stage):
            raise ValueError("previous_analysis_stage_mismatch")
        prepared = sources.read(receipt["input_artifact_id"])
        boundary = prepared.get("payload", prepared)["case_boundary"]
        aliases = {alias: aid for aid, alias in boundary["member_aliases"].items()}
        if len(aliases) != len(boundary["member_aliases"]):
            raise ValueError("previous_analysis_aliases_invalid")
        counters = {}
        for raw in receipt["retained_units"]:
            if raw["path"] not in receipt["use"]["material_paths"] or raw["kind"] == "empty_array":
                continue
            field = raw["path"].removeprefix("$.analysis.").removeprefix("$.supplement.").removeprefix("$.").split("[", 1)[0]
            if field not in {"summary", "members", "findings", "questions", "conclusion"}:
                continue
            if field == "conclusion":
                if comparable or stage != "C6":
                    continue
                value, identity = fields[field], None
            elif field == "summary":
                value, identity = fields[field], None
            else:
                index = counters.get(field, 0)
                counters[field] = index + 1
                value = fields[field][index]
                identity = value["alert_id"] if field == "members" else value["id"]
                if field != "members" and identity != raw["value"]["id"]:
                    raise ValueError("previous_analysis_unit_identity_mismatch")
                if field == "members" and identity != aliases[raw["value"]["alert_id"]]:
                    raise ValueError("previous_analysis_member_identity_mismatch")
            if (field in {"findings", "conclusion"}
                    and set(value["alert_ids"]) != {aliases[a] for a in raw["value"]["alert_ids"]}):
                raise ValueError("previous_analysis_scope_mismatch")
            if field == "findings" and value["state"] == "observed" and "statement" not in raw["value"]:
                from .case_program_output import observed_text
                from .citation_quality import new_review
                if value["statement"] != observed_text(raw["value"], boundary, citation_review=new_review()):
                    raise ValueError("previous_analysis_program_observation_mismatch")
            if field == "questions" and (identity == "coverage" or identity not in questions):
                continue
            declared = (questions[identity]["scope"] if field == "questions" else
                        {"alert_ids": [identity]} if field == "members" else
                        {"alert_ids": value["alert_ids"]} if field in {"findings", "conclusion"} else scope)
            add(stage, summary_id, rid, raw, field, value, declared, identity)

    for identity, body in sources.bodies(lambda c: c.get("type") == "delivery_report"):
        fields = (body.get("retained_output") or {}).get("fields", {})
        analysis("C6", identity, body.get("stage_delivery"),
                 {**fields.get("analysis", {}), **({"conclusion": fields["conclusion"]} if "conclusion" in fields else {})})
    for identity, body in sources.bodies(lambda c: c.get("stage") == "C3_initial"):
        analysis("C3", identity, body.get("basis", {}).get("stage_delivery"), body.get("analysis") or {})
    for identity, body in sources.bodies(lambda c: c.get("type") == "deep_summary"):
        qid = body["question_id"]
        if ("questions", qid) in seen or ("answer", qid) in seen or qid not in questions or not body.get("answer"):
            continue
        for iteration in reversed(body["iterations"]):
            descriptor = iteration.get("stage_delivery") or {}
            if not descriptor.get("artifact_id"):
                continue
            rid = descriptor["artifact_id"]
            receipt = sources.receipt(rid)
            if receipt["stage"] != "C4.deep":
                raise ValueError("previous_analysis_stage_mismatch")
            raw = next((u for u in receipt["retained_units"] if u["path"] == "$.answer"
                        and u["path"] in receipt["use"]["material_paths"]), None)
            if raw:
                add("Deep", identity, rid, raw, "answer", body["answer"], questions[qid]["scope"], qid)
                break
    return {"version": VERSION, "source_run_id": str(run), "units": units,
            "sources": list(sources.used.values()), "omissions": omissions}


async def freeze(store, case_id, run_id, context, comparison, actor_id):
    previous = comparison.get("previous_run_id")
    if previous is None:
        return context
    rows = (await store.db.execute(select(F).where(*store.where(F,
        F.c.case_id == case_id, F.c.run_id == UUID(previous))))).mappings().all()
    try:
        material = project(rows, store.tenant_id, case_id, previous, context.alerts,
                           comparable=comparison["state"] == "eligible")
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise StoreError("previous_analysis_material_invalid", 422) from exc
    identity = uuid4()
    await store.save_input_artifact(case_id, run_id, identity, material, kind="source_snapshot",
        schema=VERSION, captured_at=context.captured_at, actor_id=actor_id,
        refs=[reference("artifact", s["id"], "execution_receipt") for s in material["sources"]])
    material = {**material, "artifact_id": str(identity)}
    return context.model_copy(update={
        "update_context": {**(context.update_context or {}), "previous_analysis_material": material},
        "citation_roles": {**context.citation_roles, **{PREFIX + str(i) + ".value": "prior_analysis"
                                                      for i in range(len(material["units"]))}}})


def unit(context, path):
    match = re.fullmatch(re.escape(PREFIX) + r"(\d+)\.value", path or "")
    if not match:
        return None
    update = context.get("update_context") if isinstance(context, dict) else context.update_context
    material = (update or {}).get("previous_analysis_material")
    return material["units"][int(match[1])] if material else None
