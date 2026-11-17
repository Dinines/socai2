"""C3 unit admission: immutable received values and separate derived analysis."""
import copy
import hashlib
from collections import Counter
from types import SimpleNamespace

from pydantic import TypeAdapter, ValidationError

from . import baseline_analysis_contract as contract
from . import case_output_adapter as output
from . import case_program_output as program
from .baseline_model_view import blocked
from .case_c3_sections import SECTIONS, read_units
from .case_citation_quality import normalized
from .case_finding_schema import validate_conflicts
from .citation_quality import FIELDS, new_review
from .stage_delivery import Unit

CONTENT_PATH = "$.raw.choices[0].message.content"
TYPES = {"summary": contract.Text, "members": contract.Member, "findings": contract.Finding,
    "questions": contract.Answer, "domains": contract.Domain, "conflicts": contract.Conflict,
    "followups": contract.ExecutionFollowup}
IDENTITY = {"members": "alert_id", "findings": "id", "questions": "id", "domains": "name", "conflicts": "id"}


class RetainedAnalysis:
    """Missing fields stay absent on disk; internal iterations may be empty."""
    def __init__(self, fields):
        self.fields = copy.deepcopy(fields)

    def model_dump(self, **_):
        return copy.deepcopy(self.fields)

    def __getattr__(self, key):
        if key in TYPES and key != "summary":
            return [TypeAdapter(TYPES[key]).validate_python(item) for item in self.fields.get(key, [])]
        raise AttributeError(key)


def section(unit):
    return unit["path"].removeprefix("$.supplement.").removeprefix("$.").split("[", 1)[0]


def identity(unit):
    key, raw = section(unit), unit["value"]
    value = raw.get(IDENTITY[key]) if key in IDENTITY and isinstance(raw, dict) else None
    return key, value if isinstance(value, str) else None


def remap_review(review, key, path):
    for name in ("issues", "processing", "references"):
        for item in review[name]:
            item["path"] = item["path"].replace("$." + key + ".0", path, 1)


def merge_review(target, review):
    for key in ("issues", "processing", "references"):
        for entry in review[key]:
            if entry not in target[key]:
                target[key].append(entry)
    target["state"] = "issues_recorded" if target["issues"] else "checked"


def typed_unit(unit, prepared, context):
    key, raw, review = section(unit), copy.deepcopy(unit["value"]), new_review()
    if blocked(raw):
        raise contract.AnalysisRejected("unit_content_blocked")
    if unit["kind"] == "empty_array":
        if key in {"members", "questions", "domains"}:
            raise contract.AnalysisRejected("required_array_empty")
        return [], review
    if key == "summary":
        return TypeAdapter(contract.Text).validate_python(raw), review
    value = normalized({key: [raw]}, review)
    boundary = prepared["case_boundary"]
    if key == "findings":
        program.restore_observed(value, boundary, citation_review=review)
        program.validate_program(value, boundary, citation_review=review)
    output.restore_aliases(value, boundary)
    item = TypeAdapter(TYPES[key]).validate_python(value[key][0])
    if key == "members" and str(item.alert_id) not in context.alerts:
        raise contract.AnalysisRejected("member_outside_run")
    if key in {"questions", "followups"}:
        qid = item.id if key == "questions" else item.question_id
        if qid not in output.model_questions(context, boundary):
            raise contract.AnalysisRejected("question_outside_run")
    return item, review


def admit(scanned, prepared, context, bindings, *, prior_analysis=None):
    retained, derived, typed, quality = [], {}, {}, new_review()
    invalid = copy.deepcopy(scanned["invalid_units"])
    definitions = Counter(identity(u) for u in scanned["units"] if identity(u)[1] is not None)
    limits = {"findings": output.finding_limit(prepared["case_boundary"]),
              "followups": output.followup_limit(prepared["case_boundary"]), "conflicts": 12}
    counts = Counter()
    # JSON property order is not a dependency order. Validate findings before
    # domain/conflict links, preserving each original path and its array index.
    ordered = sorted(scanned["units"], key=lambda unit: SECTIONS.index(section(unit)))
    for unit in ordered:
        path, key = unit["path"], section(unit)
        if unit["kind"] != "empty_array":
            counts[key] += 1
        try:
            if definitions.get(identity(unit), 0) > 1:
                raise contract.AnalysisRejected("duplicate_" + key + "_definition")
            item, review = typed_unit(unit, prepared, context)
            if key in limits and limits[key] is not None and counts[key] > limits[key] and unit["kind"] != "empty_array":
                raise contract.AnalysisRejected("section_item_limit_exceeded")
            if key != "summary" and unit["kind"] != "empty_array":
                fields = {k: [] for k in SECTIONS if k != "summary"}
                fields[key] = [item]
                if key in {"domains", "conflicts"}:
                    fields["findings"] = [TypeAdapter(contract.Finding).validate_python(f)
                        for f in (prior_analysis or {}).get("findings", [])]
                    fields["findings"] += [x for x in typed.values() if isinstance(x, contract.Finding)]
                contract.validate_analysis(SimpleNamespace(**fields), prepared["source_map"], context,
                    prepared["coverage"], bindings=bindings, citation_review=review, sections=set(),
                    question_ids=output.model_questions(context, prepared["case_boundary"]))
                if key == "conflicts":
                    validate_conflicts({"findings": [x.model_dump(mode="json") for x in fields["findings"]],
                        "conflicts": [item.model_dump(mode="json")]}, prepared["source_map"], citation_review=review)
            remap_review(review, key, path)
            # Extra findings were supplied only for domain/conflict dependency checks.
            for field in ("issues", "processing", "references"):
                review[field] = [r for r in review[field] if r["path"].startswith(path)]
            raw = unit["value"]
            ids = list(dict.fromkeys(s for k in FIELDS for s in raw.get(k, []) if isinstance(s, str))) if isinstance(raw, dict) else []
            declared = ({"alert_ids": raw["alert_ids"]} if "alert_ids" in raw else
                        {"alert_ids": [raw["alert_id"]]} if "alert_id" in raw else None) if isinstance(raw, dict) else None
            record = {**unit, "declared_scope": declared, "resolved_refs": [
                {"source_id": sid, "alert_ids": prepared["source_map"][sid].get("alert_ids", []),
                 "ref": prepared["source_map"][sid]["ref"]} for sid in ids if sid in prepared["source_map"]],
                "structure_state": "valid", "quality_issues": review["issues"]}
            record = Unit.model_validate(record).model_dump(mode="json")
            retained.append(record)
            typed[path] = item
            merge_review(quality, review)
            value = item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            if key == "summary":
                derived[key] = value
            elif unit["kind"] == "empty_array":
                derived.setdefault(key, [])
            else:
                derived.setdefault(key, []).append(value)
        except (contract.AnalysisRejected, ValidationError, KeyError, TypeError, AttributeError) as exc:
            invalid.append({"path": path, "reason_code": str(exc) if isinstance(exc, contract.AnalysisRejected) else "unit_shape_or_identity_invalid"})
    missing = copy.deepcopy(scanned["missing_units"])
    for key, actual, required in (
        ("members", {m["alert_id"] for m in derived.get("members", [])}, set(context.alerts)),
        ("questions", {q["id"] for q in derived.get("questions", [])}, set(output.model_questions(context, prepared["case_boundary"]))),
        ("domains", {d["name"] for d in derived.get("domains", [])}, set(contract.DOMAINS)),
    ):
        if required - actual:
            missing.append({"path": "$." + key, "reason_code": key + "_coverage_incomplete"})
    missing = [dict(p) for p in {tuple(p.items()): p for p in missing}.values()]
    all_sections = set(scanned["closed_sections"]) == set(SECTIONS)
    complete = all_sections and not invalid and not any(m["path"] != "$" for m in missing)
    if complete and program.owns_coverage(prepared["case_boundary"]):
        program.restore_coverage(derived, prepared["case_boundary"])
    dispatch = []
    questions = {q["id"] for q in derived.get("questions", [])}
    for unit in retained:
        if section(unit) != "followups" or unit["kind"] == "empty_array":
            continue
        item = typed[unit["path"]]
        if item.question_id in questions and all(sid in prepared["source_map"] for sid in item.source_ids):
            dispatch.append(unit["path"])
    return {"retained_units": retained, "analysis": derived, "missing_units": missing, "invalid_units": invalid,
        "quality": quality, "delivery": {"state": "complete" if complete else "partial" if retained else "none",
            "reasons": [] if complete else ["required_units_missing_or_invalid"]},
        "use": {"material_paths": [u["path"] for u in retained], "dispatch_paths": dispatch,
            "conclusion_available": False, "adoption_eligible": False, "comparison_eligible": False,
            "reasons": ["C3_final_conclusion_and_adoption_not_applicable"]},
        "parse": {"state": scanned["parse_state"], "truncated": scanned["truncated"], "reasons": scanned["reasons"]},
        "closed_sections": list(scanned["closed_sections"])}


def receive(content, prepared, context, bindings, original_artifact_id, *, original_content_path=CONTENT_PATH,
            finish_reason="stop", prefix="$", prior_analysis=None):
    scanned = read_units(content)
    for unit in scanned["units"]:
        start, end = unit["value_span"]
        unit.update(path=prefix + unit["path"][1:], original_artifact_id=str(original_artifact_id),
            original_content_path=original_content_path,
            value_sha256=hashlib.sha256(content[start:end].encode("utf-8")).hexdigest())
    if prefix != "$":
        for key in ("missing_units", "invalid_units"):
            for item in scanned[key]:
                item["path"] = prefix + item["path"][1:]
    if finish_reason == "length":
        scanned["truncated"] = True
        scanned["reasons"] = list(dict.fromkeys([*scanned["reasons"], "provider_length"]))
    result = admit(scanned, prepared, context, bindings, prior_analysis=prior_analysis)
    result["scanned"] = scanned
    return result


def parser(prepared, context, bindings, *, prefix="$", prior_analysis=None):
    """The sole live C3 receiver for both ordinary and incomplete replies."""
    def parse(content):
        review = prepared["citation_review"]
        result = receive(content, prepared, context, bindings, review["original_response_artifact_id"],
                         original_content_path=prepared.get("original_content_path", CONTENT_PATH),
                         finish_reason=prepared.get("received_finish_reason", "stop"), prefix=prefix,
                         prior_analysis=prior_analysis)
        prepared["unit_delivery"] = result
        merge_review(review, result["quality"])
        return RetainedAnalysis(result["analysis"])
    return parse


def completion_fields(received):
    """Only absent/unfinished sections or known missing identities need a reply."""
    return [key for key in SECTIONS if key not in received["closed_sections"] or any(
        section(gap) == key and "coverage_incomplete" in gap["reason_code"] for gap in received["missing_units"])]


def raw_analysis(received):
    result = {}
    for unit in received["retained_units"]:
        key = section(unit)
        if key == "summary":
            result[key] = copy.deepcopy(unit["value"])
        elif unit["kind"] == "empty_array":
            result.setdefault(key, [])
        else:
            result.setdefault(key, []).append(copy.deepcopy(unit["value"]))
    return result


def combine(initial, supplement, requested, prepared, context, bindings):
    """An extra reply may fill gaps, never replace a previously retained unit."""
    units = copy.deepcopy(initial["retained_units"])
    invalid = copy.deepcopy(initial["invalid_units"] + supplement["invalid_units"])
    identities = {identity(u) for u in units if identity(u)[1] is not None}
    for unit in supplement["retained_units"]:
        key = section(unit)
        reason = "supplement_section_not_requested" if key not in requested else None
        if identity(unit)[1] is not None and identity(unit) in identities:
            reason = "supplement_retained_unit_conflict"
        if reason:
            invalid.append({"path": unit["path"], "reason_code": reason})
        else:
            units.append(copy.deepcopy(unit))
    closed = set(initial["closed_sections"]) | (set(supplement["closed_sections"]) & set(requested))
    scanned = {"units": units, "closed_sections": [k for k in SECTIONS if k in closed],
        "missing_units": [{"path": "$." + k, "reason_code": "section_not_complete"} for k in SECTIONS if k not in closed],
        "invalid_units": invalid, "parse_state": "closed_units" if units else "unusable",
        "truncated": initial["parse"]["truncated"] or supplement["parse"]["truncated"],
        "reasons": list(dict.fromkeys(initial["parse"]["reasons"] + supplement["parse"]["reasons"]))}
    return admit(scanned, prepared, context, bindings)


def summary(received, artifact_id):
    """Small internal link used by C4/C6; the immutable receipt is separate."""
    return {"artifact_id": str(artifact_id), "delivery": received["delivery"],
        "missing_units": received["missing_units"], "invalid_units": received["invalid_units"],
        "missing_sections": completion_fields(received),
        "followup_unit_paths": [u["path"] for u in received["retained_units"]
                                if section(u) == "followups" and u["kind"] != "empty_array"],
        "dispatch_paths": received["use"]["dispatch_paths"]}
