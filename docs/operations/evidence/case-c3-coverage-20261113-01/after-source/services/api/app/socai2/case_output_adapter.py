"""Assemble C3 program fields and aliases before the established unit review."""
import copy
import json

from pydantic import ValidationError

from . import baseline_analysis_contract as contract
from . import case_program_output as program
from .analysis_review import Review, decode
from .baseline_execution_schema import execution_format
from .case_citation_feedback import feedback
from .case_finding_schema import constrain_findings, validate_conflicts
from .structured_output import response_format


def alias_catalog(value, boundary):
    if isinstance(value, list):
        return [alias_catalog(item, boundary) for item in value]
    if not isinstance(value, dict):
        return value
    return {key: [boundary["member_aliases"][aid] for aid in item] if key == "alert_ids"
        else [boundary["object_aliases"][obj] for obj in item] if key == "object_keys"
        else alias_catalog(item, boundary) for key, item in value.items() if key != "schema_version"}


def output_format(prepared, context, bindings):
    boundary = prepared["case_boundary"]
    result = response_format(contract.ExecutionAnalysis, prepared["source_map"],
        members=boundary["member_aliases"].values(), questions=model_questions(context, boundary),
        objects=boundary["object_aliases"].values(), bindings=bindings or ())
    aliased = {key: {**value, "alert_ids": [boundary["member_aliases"][aid] for aid in value["alert_ids"]],
        "objects": [{**obj, "object_key": boundary["object_aliases"][obj["object_key"]]} for obj in value["objects"]]}
        for key, value in (bindings or {}).items()}
    result = constrain_findings(execution_format(result, aliased), prepared["source_map"], context.alerts,
                                program_owned=program.enabled(boundary))
    result["json_schema"]["schema"]["properties"]["followups"]["maxItems"] = followup_limit(boundary)
    if program.owns_coverage(boundary):
        schema = result["json_schema"]["schema"]
        questions = schema["properties"]["questions"]
        while "$ref" in questions:
            questions = copy.deepcopy(schema["$defs"][questions["$ref"].removeprefix("#/$defs/")])
        schema["properties"]["questions"] = {**questions, "minItems": len(context.questions) - 1,
                                             "maxItems": len(context.questions) - 1}
    return result


def model_questions(context, boundary):
    return [q.id for q in context.questions if not program.owns_coverage(boundary) or q.id != "coverage"]


def followup_limit(boundary):
    limit = boundary.get("max_followups")
    if type(limit) is not int or not 0 <= limit <= 12:
        raise contract.AnalysisRejected("case_followup_limit_unavailable")
    return limit


def restore_current(content, boundary):
    """Admit new C3 replies; historical and C6 structural restoration stays compatible."""
    limit = followup_limit(boundary)
    value = decode(content)
    if isinstance(value.get("followups"), list) and len(value["followups"]) > limit:
        raise contract.AnalysisRejected("case_followup_limit_exceeded")
    try:
        if program.owns_coverage(boundary) and any(row["question_id"] == "coverage" for row in value["followups"]):
            raise contract.AnalysisRejected("coverage_followup_is_program_owned")
        program.restore_observed(value, boundary)
        program.restore_coverage(value, boundary)
    except (KeyError, TypeError):
        raise contract.AnalysisRejected("case_output_shape_or_alias_invalid") from None
    return restore(json.dumps(value, ensure_ascii=False), boundary)


def restore(content, boundary):
    value = decode(content)
    members = {v: k for k, v in boundary["member_aliases"].items()}
    objects = {v: k for k, v in boundary["object_aliases"].items()}
    try:
        for member in value["members"]:
            member["alert_id"] = members[member["alert_id"]]
        for key in ("findings", "domains", "followups"):
            for item in value[key]:
                item["alert_ids"] = [members[aid] for aid in item["alert_ids"]]
                if key == "followups":
                    item["object_keys"] = [objects[obj] for obj in item["object_keys"]]
        contract.ExecutionAnalysis.model_validate(value)
    except (KeyError, TypeError, ValidationError) as exc:
        raise contract.AnalysisRejected("case_output_shape_or_alias_invalid") from exc
    return json.dumps(value, ensure_ascii=False)


def parse(content, prepared, context, bindings):
    value = contract.parse(restore_current(content, prepared["case_boundary"]), prepared["source_map"],
        context, prepared["coverage"], bindings=bindings)
    validate_conflicts(value.model_dump(mode="json"), prepared["source_map"])
    program.validate_program(value.model_dump(mode="json"), prepared["case_boundary"])
    return value


class CaseReview(Review):
    def __init__(self, prepared, context, bindings):
        super().__init__("C3", prepared["source_map"], context, prepared["coverage"], bindings=bindings,
                         validator=lambda value: (validate_conflicts(value, prepared["source_map"]),
                                                  program.validate_program(value, prepared["case_boundary"])))
        self.boundary = prepared["case_boundary"]

    def feedback(self, content):
        restore_current(content, self.boundary)
        sources = copy.deepcopy(self.sources)
        for item in sources.values():
            for key in ("alert_ids", "query_alert_ids", "record_alert_ids"):
                if key in item:
                    item[key] = [self.boundary["member_aliases"].get(aid, "案件外成员") for aid in item[key]]
        return feedback(content, "C3", sources, self.boundary["member_aliases"].values(), model_questions(self.context, self.boundary),
                        extra_errors=program.program_errors(decode(content), self.boundary))

    def partial(self, content):
        result = super().partial(restore_current(content, self.boundary))
        if program.owns_coverage(self.boundary):
            retained = self.details["retained_analysis"]
            retained["questions"] = [row for row in retained["questions"] if row["id"] != "coverage"]
            retained["questions"].append(program.coverage_question(retained, self.boundary))
            result = contract.parse(json.dumps(retained), self.sources, self.context, self.coverage, bindings=self.bindings)
        return result
