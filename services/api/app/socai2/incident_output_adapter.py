"""Candidate shape -> existing IncidentOutput, without inventing any analysis."""
import copy
import json

from pydantic import ValidationError, create_model

from . import incident_diagnosis_contract as legacy
from .baseline_store import StoreError
from .stage_answer_review import review_incident
from .structured_output import response_format


def model_fields(model, names=None, renames=None):
    fields = {}
    for name, info in model.model_fields.items():
        if names is not None and name not in names:
            continue
        annotation = str if name == "alert_id" else list[str] if name == "alert_ids" else info.annotation
        fields[(renames or {}).get(name, name)] = (annotation, copy.deepcopy(info))
    return fields


# Derive receipt validation from the existing field constraints. The API already
# ships Pydantic; the opt-in adapter must not add an undeclared runtime dependency.
BoundaryMember = create_model("BoundaryMember", __base__=legacy.Contract,
    **model_fields(legacy.Member, renames={"alert_id": "alert_ref"}))
BoundaryFinding = create_model("BoundaryFinding", __base__=legacy.Contract,
    **model_fields(legacy.Finding, set(legacy.Finding.model_fields) - {"id"}, {"alert_ids": "alert_refs"}))
BoundaryQuestion = create_model("BoundaryQuestion", __base__=legacy.Contract,
    **model_fields(legacy.Question, renames={"alert_ids": "alert_refs"}))
BoundaryDiagnosis = create_model("BoundaryDiagnosis", __base__=legacy.Contract,
    **model_fields(legacy.Answer, {"summary", "conclusion", "evidence_ids", "limitations"}, {"evidence_ids": "source_ids"}))
BoundaryAnswer = create_model("BoundaryAnswer", __base__=legacy.Contract, diagnosis=(BoundaryDiagnosis, ...),
    **{name: (list[model], copy.deepcopy(legacy.Answer.model_fields[name])) for name, model in (
        ("members", BoundaryMember), ("findings", BoundaryFinding), ("open_questions", BoundaryQuestion))})


def candidate_schema(prepared, *, constrain=True):
    if constrain:
        schema = response_format(legacy.Answer, prepared["source_map"],
                                 members=prepared["member_aliases"].values(),
                                 member_sources=[sid for sid, source in prepared["source_map"].items()
                                                 if source["alert_ids"]])["json_schema"]["schema"]
    else:
        schema = legacy.Answer.model_json_schema()

    def visit(node):
        if isinstance(node, list):
            for child in node:
                visit(child)
        if not isinstance(node, dict):
            return
        for key in ("title", "description", "default"):
            node.pop(key, None)
        props = node.get("properties", {})
        for old, new in (("alert_id", "alert_ref"), ("alert_ids", "alert_refs")):
            if old in props:
                props[new] = props.pop(old)
                if not constrain:
                    props[new] = {"type": "string"} if old == "alert_id" else {"type": "array", "items": {"type": "string"}, "minItems": 1}
                node["required"] = [new if k == old else k for k in node.get("required", [])]
        for child in node.values():
            if isinstance(child, (dict, list)):
                visit(child)

    visit(schema)
    finding = schema["$defs"]["Finding"]
    finding["properties"].pop("id")
    finding["required"].remove("id")
    props = schema["properties"]
    diagnosis = {k: props.pop(k) for k in ("summary", "conclusion", "evidence_ids", "limitations")}
    diagnosis["source_ids"] = diagnosis.pop("evidence_ids")
    props["diagnosis"] = {"type": "object", "additionalProperties": False,
                          "properties": diagnosis, "required": list(diagnosis)}
    schema["required"] = ["diagnosis", "members", "findings", "open_questions"]
    return schema


def decode(content):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise StoreError("incident_answer_duplicate_key", 422)
            result[key] = value
        return result
    return json.loads(content, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(StoreError("incident_answer_nonfinite", 422)))


def canonical(content, prepared):
    try:
        answer = decode(content)
        BoundaryAnswer.model_validate(answer, strict=True)
    except (ValueError, TypeError, ValidationError) as exc:
        raise StoreError("incident_answer_shape_invalid", 422) from exc
    mapping = {alias: aid for aid, alias in prepared["member_aliases"].items()}

    def aid(alias):
        if alias not in mapping:
            raise StoreError("incident_answer_scope_invalid", 422)
        return mapping[alias]

    body = copy.deepcopy(answer["diagnosis"])
    body["evidence_ids"] = body.pop("source_ids")
    body["members"] = [{**{k: v for k, v in item.items() if k != "alert_ref"}, "alert_id": aid(item["alert_ref"])}
                       for item in answer["members"]]
    for key in ("findings", "open_questions"):
        body[key] = [{**{k: v for k, v in item.items() if k != "alert_refs"},
                      "alert_ids": [aid(alias) for alias in item["alert_refs"]]}
                     for item in answer[key]]
    for i, finding in enumerate(body["findings"], 1):
        finding["id"] = f"F{i}"
    return body


def parse(content, prepared, *, diagnostics=None):
    return legacy.parse(json.dumps(canonical(content, prepared), ensure_ascii=False),
                        prepared["source_map"], prepared["data"], diagnostics=diagnostics)


def review(content, prepared):
    try:
        body = canonical(content, prepared)
    except StoreError:
        return None
    return review_incident(json.dumps(body, ensure_ascii=False), prepared["source_map"], prepared["data"])

