"""A/I admission of actual closed units, with immutable sources and sparse analysis."""
import copy
import hashlib
import json
from collections import Counter

from pydantic import TypeAdapter, ValidationError

from . import alert_output_adapter as alert
from . import incident_output_adapter as incident
from .answer_validation import Checks
from .baseline_contracts import Scope
from .baseline_model_view import blocked
from .baseline_store import StoreError
from .citation_quality import issue, new_review, record_references
from .closed_json_units import read_units
from .stage_delivery import Unit
from .stage_result_contracts import IncidentOutput

A_FIELDS = ("verdict", "confidence", "rationale", "evidence_ids")
I_FIELDS = ("summary", "conclusion", "source_ids", "limitations")
I_ARRAYS = ("members", "findings", "open_questions")
CONTENT_PATH = "$.raw.choices[0].message.content"


def selection(stage):
    if stage == "A":
        return {"fields": tuple((key,) for key in A_FIELDS), "arrays": (("recommendations",),)}
    if stage == "I":
        return {"fields": tuple(("diagnosis", key) for key in I_FIELDS),
                "arrays": tuple((key,) for key in I_ARRAYS)}
    raise ValueError("unsupported_ai_stage")


def key_of(path):
    return path.removeprefix("$.").split("[", 1)[0]


def checked_value(stage, unit, prepared):
    key, raw = key_of(unit["path"]), unit["value"]
    if blocked(raw):
        raise StoreError("unit_content_blocked", 422)
    if unit["kind"] == "empty_array":
        if key == "members":
            raise StoreError("required_array_empty", 422)
        return []
    if stage == "A":
        typ = alert.legacy.Advice if key == "recommendations" else alert.Answer.model_fields[key].rebuild_annotation()
    elif key.startswith("diagnosis."):
        typ = incident.BoundaryDiagnosis.model_fields[key.split(".")[1]].rebuild_annotation()
    else:
        typ = {"members": incident.BoundaryMember, "findings": incident.BoundaryFinding,
               "open_questions": incident.BoundaryQuestion}[key]
    item = TypeAdapter(typ).validate_python(raw, strict=True)
    value = item.model_dump(mode="json") if hasattr(item, "model_dump") else item
    if stage == "I" and key in I_ARRAYS:
        aliases = {alias: aid for aid, alias in prepared["member_aliases"].items()}
        names = [value["alert_ref"]] if key == "members" else value["alert_refs"]
        if not names or len(names) != len(set(names)) or not set(names) <= set(aliases):
            raise StoreError("incident_answer_scope_invalid", 422)
        value = copy.deepcopy(value)
        if key == "members":
            value["alert_id"] = aliases[value.pop("alert_ref")]
        else:
            value["alert_ids"] = [aliases[a] for a in value.pop("alert_refs")]
    return value


def references(ids, sources, quality, path, owned=None, *, required=True):
    record_references(quality, ids, sources, path, owned, required=required)
    if len(ids) != len(set(ids)):
        issue(quality, "duplicate_source", path, source_ids=ids)
    known = list(dict.fromkeys(s for s in ids if s in sources))
    if set(ids) - set(sources):
        issue(quality, "unbound_source_ids", path, unresolved_ids=sorted(set(ids) - set(sources)))
    actual = {a for sid in known for a in sources[sid].get("alert_ids", [])}
    if owned is not None and (actual != set(owned) or any(not sources[s].get("alert_ids") for s in known)):
        issue(quality, "source_scope_diagnostic", path, declared_members=owned,
              resolved_members={s: sources[s].get("alert_ids", []) for s in known})
    return [{"source_id": sid, "alert_ids": sources[sid].get("alert_ids", []), "ref": sources[sid]["ref"]}
            for sid in known]


def scope(ids):
    return Scope(kind="selected_alerts", alert_ids=ids, object_keys=[], window_start=None,
                 window_end=None, limitations=["frozen_incident_members_only"]).model_dump(mode="json")


def project_incident(key, item, index, refs):
    if key == "members":
        return {"id": "member:" + item["alert_id"], "statement": item["assessment"],
            "state": "inferred" if item["state"] == "summarized" else "unresolved", "scope": scope([item["alert_id"]]),
            "support": refs, "counterevidence": [], "limitations": [*item["limitations"], "member_coverage:" + item["state"]]}
    if key == "findings":
        return {"id": f"F{index + 1}", "statement": item["statement"], "state": item["state"],
            "scope": scope(item["alert_ids"]), "support": refs, "counterevidence": [],
            "limitations": [*item["limitations"], "event_synthesis_not_independent_observation"]}
    return {"id": f"Q{index + 1}", "text": item["text"], "scope": scope(item["alert_ids"]),
        "evidence_requirements": item["evidence_requirements"], "state": "open", "answer": None,
        "evidence_refs": refs, "limitations": ["question_not_a_fact"]}


def receive(stage, content, prepared, original_artifact_id, *, finish_reason="stop", original_content_path=CONTENT_PATH):
    scanned = read_units(content, **selection(stage))
    retained, analysis, quality = [], {}, new_review()
    invalid, missing = copy.deepcopy(scanned["invalid_units"]), copy.deepcopy(scanned["missing_units"])
    sources = prepared["source_map"]
    member_counts = Counter(u["value"].get("alert_ref") for u in scanned["units"]
        if key_of(u["path"]) == "members" and isinstance(u["value"], dict)
        and isinstance(u["value"].get("alert_ref"), str))
    projected = {key: [] for key in I_ARRAYS}
    array_indices = {}
    limits = {"recommendations": 5, "findings": 8, "open_questions": 10}
    counts = Counter()
    for unit in scanned["units"]:
        path, raw = unit["path"], unit["value"]
        key, before = key_of(path), len(quality["issues"])
        try:
            counts[key] += unit["kind"] != "empty_array"
            if key in limits and counts[key] > limits[key]:
                raise StoreError("section_item_limit_exceeded", 422)
            if key == "members" and isinstance(raw, dict) and member_counts.get(raw.get("alert_ref"), 0) > 1:
                raise StoreError("duplicate_members_definition", 422)
            value = checked_value(stage, unit, prepared)
            owned = ([value["alert_id"]] if key == "members" else value.get("alert_ids")) if isinstance(value, dict) else None
            ids = (value.get("source_ids", []) if isinstance(value, dict) else
                   value if key in {"evidence_ids", "diagnosis.source_ids"} else None)
            resolved = references(ids, sources, quality, path, owned,
                required=not (key == "members" and value["state"] == "not_reviewed")) if ids is not None else []
            checks = Checks(citation_review=quality)
            if key == "members" and value:
                coverage = next(m for m in prepared["data"]["members"] if m["alert_id"] == value["alert_id"])
                if value["state"] != "not_reviewed" and (not coverage.get("included") or not ids):
                    checks.add("incident_member_not_read", path, "coverage")
                if value["state"] == "not_reviewed" and ids:
                    checks.add("incident_unread_member_has_sources", path, "coverage")
            texts = []
            if isinstance(value, str) and key in {"rationale", "diagnosis.summary", "diagnosis.conclusion"}:
                texts = [(path, value)]
            elif key == "diagnosis.limitations":
                texts = [(f"{path}[{i}]", text) for i, text in enumerate(value)]
            elif isinstance(value, dict):
                texts = [(path + "." + name, value[name]) for name in ("reason", "assessment", "statement", "text") if name in value]
                texts += [(f"{path}.{name}[{i}]", text) for name in ("limitations", "evidence_requirements")
                          for i, text in enumerate(value.get(name, []))]
            for at, text in texts:
                checks.prose(text, at, ids or [], sources, prepared["data"], "alert_answer" if stage == "A" else "incident_answer", owned=owned)
            declared = ({"alert_refs": [raw["alert_ref"]]} if "alert_ref" in raw else
                        {"alert_refs": raw["alert_refs"]} if "alert_refs" in raw else None) if isinstance(raw, dict) else None
            start, end = unit["value_span"]
            retained.append(Unit.model_validate({**unit, "original_artifact_id": original_artifact_id,
                "original_content_path": original_content_path, "value_sha256": hashlib.sha256(content[start:end].encode()).hexdigest(),
                "declared_scope": declared, "resolved_refs": resolved, "structure_state": "valid",
                "quality_issues": quality["issues"][before:]}).model_dump(mode="json"))
            if key.startswith("diagnosis."):
                analysis.setdefault("diagnosis", {})[key.split(".")[1]] = value
            elif key in A_FIELDS:
                analysis[key] = value
            elif unit["kind"] == "empty_array":
                analysis.setdefault(key, [])
            else:
                index = int(path.rsplit("[", 1)[1][:-1])
                array_indices.setdefault(key, []).append(index)
                analysis.setdefault(key, []).append(value)
                if stage == "I":
                    projected[key].append(project_incident(key, value, index, [r["ref"] for r in resolved]))
        except (StoreError, ValidationError, KeyError, TypeError, StopIteration) as exc:
            invalid.append({"path": path, "reason_code": exc.code if isinstance(exc, StoreError) else "unit_shape_or_identity_invalid"})
    result = None
    members = analysis.get("members", []) if stage == "I" else None
    if stage == "I":
        expected = set(prepared["member_aliases"])
        if {m["alert_id"] for m in members} != expected:
            missing.append({"path": "$.members", "reason_code": "members_coverage_incomplete"})
        diagnosis = analysis.get("diagnosis", {})
        if set(diagnosis) == set(I_FIELDS) and {m["alert_id"] for m in members} == expected:
            refs = references(diagnosis["source_ids"], sources, quality, "$.diagnosis.source_ids")
            limits_out = [*diagnosis["limitations"], "incident_diagnosis_not_case_investigation", "structure_scope_sources_checked_not_truth_proven"]
            if prepared["data"]["omissions"]:
                limits_out.append("model_view_has_omitted_fields")
            limits_out += [f"triage_not_used:{m['alert_id']}:{m['triage_freshness']}" for m in prepared["data"]["members"]
                          if not m.get("triage_eligible", m.get("triage_usable"))]
            result = IncidentOutput(summary=diagnosis["summary"], conclusion=diagnosis["conclusion"],
                findings=projected["members"] + projected["findings"], source_refs=[r["ref"] for r in refs],
                open_questions=projected["open_questions"], limitations=limits_out)
    elif set(A_FIELDS) <= set(analysis):
        try:
            result = alert.parse(json.dumps({**analysis, "recommendations": analysis.get("recommendations", [])}, ensure_ascii=False),
                                 prepared, citation_review=quality)
            result = result.model_copy(update={"recommendations": [r.model_copy(update={"id": f"R{index + 1}"})
                for r, index in zip(result.recommendations, array_indices.get("recommendations", []))]})
        except StoreError as exc:
            invalid.append({"path": "$", "reason_code": exc.code})
    complete = not invalid and not any(g["path"] != "$" for g in missing)
    delivery = "complete" if complete and result else "partial" if retained else "none"
    if result is not None and delivery != "complete":
        result = result.model_copy(update={"limitations": [*result.limitations, "stage_output_incomplete_see_stage_delivery"]})
    quality["state"] = "issues_recorded" if quality["issues"] else "checked"
    parse = {"state": scanned["parse_state"], "truncated": scanned["truncated"] or finish_reason == "length",
             "reasons": [*scanned["reasons"], *(["provider_length"] if finish_reason == "length" else [])]}
    return {"analysis": analysis, "result": result, "validated_members": members, "retained_units": retained,
        "missing_units": missing, "invalid_units": invalid, "quality": quality, "parse": parse,
        "delivery": {"state": delivery, "reasons": [] if delivery == "complete" else ["required_units_missing_or_invalid"]},
        "use": {"material_paths": [u["path"] for u in retained], "dispatch_paths": [],
            "conclusion_available": result is not None, "adoption_eligible": False, "comparison_eligible": False,
            "reasons": ["case_adoption_and_comparison_not_applicable", *([] if result else ["core_conclusion_or_scope_unavailable"])]}}
