"""Retain independently validated A/I units without inventing a new judgment.

Neutral envelopes are used only to invoke the existing strict parsers. They are
never returned as model analysis. Global identity/shape/guard failures stay fatal.
"""
import copy
import json

from pydantic import ValidationError

from . import alert_basic_contract as alert
from . import incident_diagnosis_contract as incident
from .analysis_review import POLICY, decode
from .baseline_analysis_contract import AnalysisRejected
from .baseline_store import StoreError, digest

NOTE = "该包仅用于独立片段引用校验，不包含业务判断。"


def citation_feedback(stage, content, sources, diagnostics, prepared):
    """A single configured-boundary correction; no semantic repair or new query."""
    allowed = ({"alert_answer_source_invalid", "alert_answer_requires_direct_source",
                "alert_decision_basis_not_direct", "alert_decision_basis_not_in_evidence"} if stage == "A" else
               {"incident_answer_source_invalid", "incident_source_wrong_member", "incident_source_scope_not_covered",
                "incident_member_not_read", "incident_unread_member_has_sources"})
    errors = [item for item in diagnostics if item["severity"] == "error"]
    if not prepared or not errors or any(item["code"] not in allowed for item in errors):
        return None
    raw = decode(content)
    mapped, seen = [], set()
    for item in errors:
        path = item["path"]
        if stage == "A":
            path = path.replace("$.decision_basis.source_ids", "$.evidence_ids")
        elif path == "$.evidence_ids":
            path = "$.diagnosis.source_ids"
        key = path, item["code"]
        if key in seen:
            continue
        seen.add(key)
        detail = {"path": path, "code": item["code"]}
        parts = path.split(".")
        if stage == "I" and len(parts) >= 3 and parts[1] in {"members", "findings", "open_questions"}:
            row = raw[parts[1]][int(parts[2])]
            detail["declared_members"] = row.get("alert_refs", [row.get("alert_ref")])
            detail["source_ids"] = row["source_ids"]
        mapped.append(detail)
    aliases = prepared.get("member_aliases", {})
    return {"policy": "socai2.ai-citation-correction.v1", "attempt": 1, "stage": stage, "errors": mapped,
        "allowed_sources": [{"id": sid, "role": source["ref"]["role"],
            **({"alert_refs": [aliases[aid] for aid in source["alert_ids"]]} if stage == "I" else {})}
            for sid, source in sources.items()],
        "instruction": "在相同材料上纠正上一份完整JSON一次，返回原Schema。来源数组不能重复或使用不可见编号；"
            "I的成员、发现和问题仅引用其声明成员的来源，每个声明成员均有相应依据，不能把共同主机或用户名的记录搬给其他成员。"
            "只选择实际支持正文的来源，不为过校验补凑编号、机械扩大成员范围或改判。"
            "A的确定判定须有原始观察或适用人工陈述支持；标签、查空和缺少授权材料不能证明良性或恶意，证据不足应needs_review。"
            "保留独立有效内容，核对正文和引用，不改写输入事实；仍须通过全部校验。"}


def original(content, model):
    try:
        raw = decode(content)
        model.model_validate(raw)
        return raw
    except (AnalysisRejected, ValidationError, ValueError, TypeError):
        return None


def rejected(path, value, exc):
    return {"path": path, "code": exc.code, "action": "exclude_dependent_claim",
            "original_sha256": digest(value)}


def details(retained, diagnostics, *, adoptable=False):
    return {"policy": POLICY, "state": "partial", "retained_analysis": retained,
            "diagnostics": diagnostics, "conclusion_adoptable": adoptable,
            "limitations": ["structure_scope_sources_checked_not_truth_proven",
                "original_answer_preserved", "invalid_global_prose_not_reused",
                "retained_recommendations_are_not_executed"]}


def review_alert(content, sources, data):
    model = alert.Answer if data.get("citations") == "structured_v3" else alert.LegacyAnswer
    raw = original(content, model)
    if raw is None or not sources:
        return None, None
    diagnostics, valid_advice, projected = [], [], []
    core = {**raw, "recommendations": []}
    try:
        result = alert.parse(json.dumps(core), sources, data)
    except StoreError as exc:
        result = None
        diagnostics.append(rejected(["assessment"], core, exc))
    # The temporary evidence is NOT substituted into the original assessment.
    neutral = {"verdict": "needs_review", "confidence": None, "rationale": NOTE,
        "explanation": NOTE, "evidence_ids": [next(iter(sources))],
        "recommendations": [], "limitations": []}
    if model is alert.Answer:
        neutral["decision_basis"] = None
    for index, item in enumerate(raw["recommendations"]):
        try:
            unit = alert.parse(json.dumps({**neutral, "recommendations": [item]}), sources, data)
        except StoreError as exc:
            diagnostics.append(rejected(["recommendations", index], item, exc))
            continue
        valid_advice.append(item)
        value = unit.recommendations[0].model_dump(mode="json")
        value["id"] = f"R{index + 1}"
        projected.append(value)
    if result is not None:
        # Revalidate the combined delivery, preserving the original verdict,
        # reasoning, confidence and evidence. Only invalid advice is excluded.
        result = alert.parse(json.dumps({**raw, "recommendations": valid_advice}), sources, data)
        result = result.model_copy(update={"recommendations": [
            advice.model_copy(update={"id": value["id"]})
            for advice, value in zip(result.recommendations, projected)],
            "limitations": [*result.limitations, "invalid_recommendations_excluded"]})
    retained = {"assessment": result.model_dump(mode="json") if result else None,
                "recommendations": projected}
    return result, details(retained, diagnostics, adoptable=result is not None)


def review_incident(content, sources, data):
    raw = original(content, incident.Answer)
    if raw is None or not sources:
        return None
    members = [str(m["alert_id"]) for m in raw["members"]]
    if len(set(members)) != len(members) or set(members) != {m["alert_id"] for m in data["members"]}:
        return None
    if len({f["id"] for f in raw["findings"]}) != len(raw["findings"]):
        return None
    neutral = {"summary": NOTE, "conclusion": NOTE, "evidence_ids": [next(iter(sources))],
        "members": [{"alert_id": aid, "state": "not_reviewed", "assessment": NOTE,
                     "source_ids": [], "limitations": []} for aid in members],
        "findings": [], "open_questions": [], "limitations": []}
    # Check the skeleton too; malformed input/source maps must not create a
    # supposedly valid partial result.
    incident.parse(json.dumps(neutral), sources, data)
    retained = {"summary": None, "conclusion": None, "members": [], "findings": [], "open_questions": []}
    diagnostics = []
    for key in ("members", "findings", "open_questions"):
        for index, item in enumerate(raw[key]):
            candidate = copy.deepcopy(neutral)
            if key == "members":
                candidate[key][index] = item
            else:
                candidate[key] = [item]
            try:
                output, validated = incident.parse(json.dumps(candidate), sources, data)
            except StoreError as exc:
                diagnostics.append(rejected([key, index], item, exc))
                continue
            if key == "members":
                retained[key].append(validated[index])
                retained["findings"].append(output.findings[index].model_dump(mode="json"))
            elif key == "findings":
                retained[key].append(output.findings[-1].model_dump(mode="json"))
            else:
                value = output.open_questions[0].model_dump(mode="json")
                value["id"] = f"Q{index + 1}"
                retained[key].append(value)
    # Free prose may refer to an invalid unit without an explicit identifier.
    # Do not silently promote the remaining pieces into a revised conclusion.
    return details(retained, diagnostics)
