"""C3 section validation, frozen completion request and lossless wire-value merge."""
import copy
import json
from types import SimpleNamespace
from typing import Annotated

from pydantic import Field, RootModel, TypeAdapter, ValidationError

from . import baseline_analysis_contract as contract
from . import case_output_adapter as output
from . import case_program_output as program
from .analysis_review import decode
from .baseline_model_view import blocked
from .baseline_store import encoded
from .case_c3_sections import SECTIONS
from .case_citation_quality import normalized
from .citation_quality import new_review
from .runtime_policy import C3_COMPLETION_VERSION as VERSION
from .runtime_policy import draft_limit
from .runtime_policy import validate_c3_completion as validate_policy


class SectionReply(RootModel[dict]):
    pass


def validate_sections(raw, prepared, context, bindings, *, restored=False, citation_review=None):
    """Validate only present complete sections, without manufacturing absent ones."""
    if not isinstance(raw, dict) or not raw or set(raw) - set(SECTIONS) or blocked(raw):
        raise contract.AnalysisRejected("c3_completion_sections_invalid")
    boundary = prepared["case_boundary"]
    review = new_review() if citation_review is None else citation_review
    value = normalized(copy.deepcopy(raw), review)
    question_ids = output.model_questions(context, boundary)
    try:
        if "findings" in value:
            limit = output.finding_limit(boundary)
            if limit is not None and len(value["findings"]) > limit:
                raise contract.AnalysisRejected("case_finding_limit_exceeded")
            program.restore_observed(value, boundary, citation_review=review)
            program.validate_program(value, boundary, citation_review=review)
        if "followups" in value:
            if len(value["followups"]) > output.followup_limit(boundary):
                raise contract.AnalysisRejected("case_followup_limit_exceeded")
            if any(row["question_id"] not in question_ids for row in value["followups"]):
                raise contract.AnalysisRejected("followup_question_outside_run")
        output.restore_aliases(value, boundary)
        typed = {}
        for key, item in value.items():
            annotation = contract.ExecutionAnalysis.model_fields[key].rebuild_annotation()
            if key == "questions":
                annotation = Annotated[list[contract.Answer], Field(min_length=len(question_ids), max_length=len(question_ids))]
            typed[key] = TypeAdapter(annotation).validate_python(item)
        # Empty iteration fields are internal to the shared validator only;
        # they are never emitted as model answers or persisted retained fields.
        fields = {key: [] for key in SECTIONS if key != "summary"}
        fields.update(typed)
        contract.validate_analysis(SimpleNamespace(**fields), prepared["source_map"], context, prepared["coverage"],
            bindings=bindings, citation_review=review, sections=set(raw), question_ids=question_ids)
    except (KeyError, TypeError, AttributeError, ValidationError):
        raise contract.AnalysisRejected("c3_completion_section_shape_or_identity_invalid") from None
    return value if restored else SectionReply(copy.deepcopy(raw))


def parse_reply(content, missing, prepared, context, bindings):
    raw = decode(content)
    if set(raw) != set(missing):
        raise contract.AnalysisRejected("c3_completion_reply_fields_mismatch")
    return validate_sections(raw, prepared, context, bindings)


def subset_format(fmt, missing):
    value = copy.deepcopy(fmt)
    schema = value["json_schema"]["schema"]
    schema["properties"] = {key: schema["properties"][key] for key in missing}
    schema.update(required=list(missing), additionalProperties=False)
    value["json_schema"]["name"] = "C3MissingSections"
    return value


def prepare_completion(prepared, request, retained, missing, initial_response_id):
    policy = request["case_boundary"]["c3_completion"]
    try:
        validate_policy(policy, frozen=True)
    except ValueError:
        raise contract.AnalysisRejected("case_c3_completion_policy_invalid") from None
    # This is the previously saved wire's business view and offered tools,
    # not a new selection from latest materials or the live profile.
    original_messages = request["body"].get("messages", request["body"].get("input"))
    if not isinstance(original_messages, list) or original_messages[0].get("role") != "system":
        raise contract.AnalysisRejected("c3_completion_frozen_messages_invalid")
    dependencies = {key for section in missing for key in policy["dependencies"][section]}
    prior = {key: retained[key] for key in SECTIONS if key in dependencies and key in retained}
    value = copy.deepcopy(prepared)
    value["messages"] = [{"role": "system", "content": policy["system"] + "\n" +
        policy["instruction"].replace("{missing}", "、".join(missing))}, *copy.deepcopy(original_messages[1:]),
        {"role": "user", "content": encoded({"role": "prior_analysis", "retained_sections": prior,
            "requested_sections": missing}).decode()}]
    value["citation_review"] = new_review()
    for key in ("validation_review", "correction_result"):
        value.pop(key, None)
    for key in ("source_map", "binding_map", "case_boundary", "tool_presentation"):
        if key in request:
            value[key] = copy.deepcopy(request[key])
    value["input_artifact_ids"] = list(dict.fromkeys([*request["input_artifact_ids"], initial_response_id]))
    value["section_completion"] = {"version": VERSION, "attempt": 1,
        "initial_response_artifact_id": initial_response_id, "retained_fields": list(retained),
        "missing_fields": list(missing), "prior_analysis_fields": list(prior)}
    if len(encoded(value["messages"])) > draft_limit() or any(blocked(m["content"]) for m in value["messages"]):
        raise contract.AnalysisRejected("c3_completion_input_contract_or_size")
    return value


def prepare_units(prepared, request, received, missing, initial_response_id):
    from .case_c3_delivery import raw_analysis
    retained = raw_analysis(received)
    value = prepare_completion(prepared, request, retained, missing, initial_response_id)
    # A requested array may already contain complete items. Show those items
    # unchanged so the model can supply only the remainder.
    prior = json.loads(value["messages"][-1]["content"])
    prior["retained_sections"].update({k: retained[k] for k in missing if k in retained})
    value["messages"][-1]["content"] = encoded(prior).decode()
    value.pop("unit_delivery", None)
    value.pop("received_finish_reason", None)
    value.pop("original_content_path", None)
    if len(encoded(value["messages"])) > draft_limit():
        raise contract.AnalysisRejected("c3_completion_input_contract_or_size")
    return value


def unit_format(fmt, received, missing):
    from .case_c3_delivery import raw_analysis
    retained = raw_analysis(received)
    value = subset_format(fmt, missing)
    schema = value["json_schema"]["schema"]
    for key, item in list(schema["properties"].items()):
        while "$ref" in item:
            item = copy.deepcopy(schema["$defs"][item["$ref"].removeprefix("#/$defs/")])
        if item.get("type") == "array":
            count = len(retained.get(key, []))
            item["minItems"] = max(0, item.get("minItems", 0) - count)
            if "maxItems" in item:
                item["maxItems"] = max(0, item["maxItems"] - count)
        schema["properties"][key] = item
    return value


def merge(retained, reply, prepared, context, bindings, review):
    if set(retained) & set(reply) or set(retained) | set(reply) != set(SECTIONS):
        raise contract.AnalysisRejected("c3_completion_merge_fields_mismatch")
    wire = {key: copy.deepcopy(retained[key] if key in retained else reply[key]) for key in SECTIONS}
    analysis = output.parse(json.dumps(wire, ensure_ascii=False), prepared, context, bindings, citation_review=review)
    return wire, analysis
