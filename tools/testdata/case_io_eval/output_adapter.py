"""Short identifiers restore C3's existing seven business blocks, no new claims."""
import copy
import json

from app.socai2 import baseline_analysis_contract as legacy
from app.socai2.structured_output import response_format
from jsonschema import Draft202012Validator


def schema(prepared, context, bindings):
    return response_format(legacy.ExecutionAnalysis, prepared["source_map"],
        members=prepared["member_aliases"].values(), questions=[q["id"] for q in context["questions"]],
        objects=prepared["object_aliases"].values(), bindings=bindings)["json_schema"]["schema"]


def convert(answer, members, objects):
    """Translate only declared structural fields; never touch any prose."""
    answer = copy.deepcopy(answer)
    for item in answer["members"]:
        item["alert_id"] = members[item["alert_id"]]
    for key in ("findings", "domains", "followups"):
        for item in answer[key]:
            item["alert_ids"] = [members[aid] for aid in item["alert_ids"]]
            if key == "followups":
                item["object_keys"] = [objects[key] for key in item["object_keys"]]
    return answer


def canonical(content, prepared, context, bindings):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    answer = json.loads(content, object_pairs_hook=unique,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid_json_number")))
    Draft202012Validator(schema(prepared, context, bindings)).validate(answer)
    return convert(answer, {v: k for k, v in prepared["member_aliases"].items()},
                   {v: k for k, v in prepared["object_aliases"].items()})


def parse(content, prepared, context, bindings):
    from app.socai2.baseline_context import Context

    answer = canonical(content, prepared, context, bindings)
    return legacy.parse(json.dumps(answer, ensure_ascii=False), prepared["source_map"],
                        Context.model_validate(context), prepared["coverage"], bindings=bindings)


def tool_catalog(value, prepared):
    """Only program-owned directory IDs change; capability prose stays exact."""
    if isinstance(value, list):
        return [tool_catalog(item, prepared) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        if key == "alert_ids":
            result[key] = [prepared["member_aliases"][aid] for aid in item]
        elif key == "object_keys":
            result[key] = [prepared["object_aliases"][obj] for obj in item]
        elif key != "schema_version":
            result[key] = tool_catalog(item, prepared)
    return result
