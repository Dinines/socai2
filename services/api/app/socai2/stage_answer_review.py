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
