"""Candidate shape -> existing IncidentOutput, without inventing any analysis."""
import copy
import json

from app.socai2 import incident_diagnosis_contract as legacy
from app.socai2.baseline_store import StoreError
from app.socai2.stage_answer_review import review_incident
from app.socai2.structured_output import response_format
from jsonschema import Draft202012Validator


def candidate_schema(prepared, *, constrain=True):
    if constrain:
        schema = response_format(legacy.Answer, prepared["source_map"],
                                 members=prepared["member_aliases"].values())["json_schema"]["schema"]
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
    answer = decode(content)
    Draft202012Validator(candidate_schema(prepared, constrain=False)).validate(answer)
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
    return review_incident(json.dumps(canonical(content, prepared), ensure_ascii=False),
                           prepared["source_map"], prepared["data"])


def replay_candidate(answer, aliases):
    """Offline structure replay of an OLD answer, never a new model result."""
    body = {"diagnosis": {k: copy.deepcopy(answer[k]) for k in ("summary", "conclusion", "limitations")}}
    body["diagnosis"]["source_ids"] = copy.deepcopy(answer["evidence_ids"])
    body["members"] = [{**copy.deepcopy({k: v for k, v in item.items() if k != "alert_id"}),
                        "alert_ref": aliases[item["alert_id"]]} for item in answer["members"]]
    for key in ("findings", "open_questions"):
        body[key] = [{**copy.deepcopy({k: v for k, v in item.items() if k not in {"alert_ids", "id"}}),
                      "alert_refs": [aliases[aid] for aid in item["alert_ids"]]} for item in answer[key]]
    return body
