"""Restore program-owned fields before the unchanged Deep/C6 validators."""
import copy
import json

from pydantic import ValidationError

from . import baseline_analysis_contract as analysis
from . import baseline_deep_contract as deep
from . import baseline_delivery_contract as delivery
from . import case_program_output as program
from .analysis_review import Review, decode
from .case_citation_feedback import feedback
from .case_finding_schema import constrain_findings, validate_conflicts
from .structured_output import response_format


def deep_format(prepared):
    # Query status stays visible in the input; it cannot substantiate a Deep
    # answer. Match deep.parse's existing role check at generation time too.
    evidence = {sid: source for sid, source in prepared["source_map"].items()
                if source["ref"]["role"] != "execution_receipt"}
    fmt = response_format(deep.Decision, evidence, bindings=prepared["binding_map"])
    schema = fmt["json_schema"]["schema"]
    schema["properties"].pop("question_id")
    schema["required"].remove("question_id")
    # Mirror the receiver's cross-field contract. A handoff still carries an
    # unresolved answer describing the gap; null is reserved for a query.
    def answer_variant(state):
        value = copy.deepcopy(schema["$defs"]["Answer"])
        value["properties"]["state"] = {"type": "string", "enum": [state]}
        field = "limitations" if state == "unresolved" else "support_ids"
        array = value["properties"][field]
        while "$ref" in array:
            array = copy.deepcopy(schema["$defs"][array["$ref"].removeprefix("#/$defs/")])
        value["properties"][field] = {**array, "minItems": 1}
        return value

    def variant(action, answer, binding):
        # The configured provider compiles branches separately. Include every
        # required field/limit in each branch, not just discriminating fields.
        props = copy.deepcopy(schema["properties"])
        props.update(action={"type": "string", "enum": [action]}, answer=answer, binding_id=binding)
        return {"type": "object", "properties": props, "required": list(schema["required"]), "additionalProperties": False}

    unresolved = answer_variant("unresolved")
    variants = [variant("answer", {"anyOf": [unresolved, answer_variant("supported")]}, {"type": "null"}),
                variant("handoff", unresolved, {"type": "null"})]
    if prepared["binding_map"]:
        variants.append(variant("query", {"type": "null"}, {"$ref": "#/$defs/BindingId"}))
    schema["anyOf"] = variants
    return fmt


def parse_deep(content, prepared):
    value = decode(content)
    if set(value) != {"action", "binding_id", "reason", "answer"}:
        raise analysis.AnalysisRejected("deep_boundary_shape_invalid")
    qid = prepared["case_boundary"]["question_id"]
    return deep.parse(json.dumps({"question_id": qid, **value}, ensure_ascii=False),
                      prepared["source_map"], prepared["binding_map"], qid)


def fixed_comparison(comparison):
    return comparison["state"] == "initial" and comparison["result_id"] is None


def final_format(prepared, context, comparison):
    boundary = prepared["case_boundary"]
    fmt = response_format(delivery.Delivery, prepared["source_map"],
        members=[boundary["member_aliases"][aid] for aid in context.alerts],
        questions=[q.id for q in context.questions], objects=[boundary["object_aliases"][key] for key in context.scope.object_keys])
    schema = fmt["json_schema"]["schema"]
    # Only these final-delivery slots reject receipts. Analysis can still cite
    # query coverage. Copy a compacted array instead of changing its shared def.
    evidence = [sid for sid, source in prepared["source_map"].items()
                if source["ref"]["role"] != "execution_receipt"]
    if evidence:
        schema["$defs"]["EvidenceSourceId"] = {"type": "string", "enum": sorted(evidence)}
    for name, field in (("Conclusion", "support_ids"), ("Comparison", "support_ids"),
                        ("Impact", "support_ids"), ("Recommendation", "source_ids")):
        props = schema["$defs"][name]["properties"]
        array = props[field]
        while "$ref" in array:
            array = schema["$defs"][array["$ref"].removeprefix("#/$defs/")]
        array = copy.deepcopy(array)
        if evidence:
            array["items"] = {"$ref": "#/$defs/EvidenceSourceId"}
        else:
            array["maxItems"] = 0
        props[field] = array
    recommendation = schema["$defs"]["Recommendation"]
    recommendation["properties"].pop("id")
    recommendation["required"].remove("id")
    if fixed_comparison(comparison):
        schema["properties"].pop("comparison")
        schema["required"].remove("comparison")
    if program.enabled(boundary):
        schema["$defs"]["Answer"]["properties"]["id"] = {"type": "string", "enum": [q.id for q in context.questions if q.id != "coverage"]}
        questions = schema["$defs"]["Analysis"]["properties"]["questions"]
        while "$ref" in questions:
            questions = schema["$defs"][questions["$ref"].removeprefix("#/$defs/")]
        schema["$defs"]["Analysis"]["properties"]["questions"] = {**copy.deepcopy(questions),
            "minItems": len(context.questions) - 1, "maxItems": len(context.questions) - 1}
    return constrain_findings(delivery.constrain_recommendations(fmt), prepared["source_map"], context.alerts,
                              program_owned=program.enabled(boundary))


def restore_final(content, prepared, comparison):
    value = decode(content)
    boundary = prepared["case_boundary"]
    members = {v: k for k, v in boundary["member_aliases"].items()}
    objects = {v: k for k, v in boundary["object_aliases"].items()}
    try:
        root = value["analysis"]
        program.restore_observed(root, boundary)
        program.restore_coverage(root, boundary)
        for row in root["members"]:
            row["alert_id"] = members[row["alert_id"]]
        for key in ("findings", "domains", "followups"):
            for row in root[key]:
                row["alert_ids"] = [members[aid] for aid in row["alert_ids"]]
                if key == "followups":
                    row["object_keys"] = [objects[key] for key in row["object_keys"]]
        for key in ("conclusion", "impact"):
            value[key]["alert_ids"] = [members[aid] for aid in value[key]["alert_ids"]]
        for i, row in enumerate(value["recommendations"], 1):
            if "id" in row:
                raise KeyError("model_must_not_supply_recommendation_id")
            row["id"] = "R" + str(i)
            row["object_keys"] = [objects[key] for key in row["object_keys"]]
        if fixed_comparison(comparison):
            if "comparison" in value:
                raise KeyError("model_must_not_supply_fixed_comparison")
            value["comparison"] = {"kind": "initial", "summary": None, "support_ids": []}
        delivery.Delivery.model_validate(value)
    except (KeyError, TypeError, ValidationError) as exc:
        raise analysis.AnalysisRejected("final_boundary_shape_or_alias_invalid") from exc
    return json.dumps(value, ensure_ascii=False)


def parse_final(content, prepared, context, comparison):
    value = delivery.parse(restore_final(content, prepared, comparison),
                           prepared["source_map"], context, prepared["coverage"], comparison)
    validate_conflicts(value.analysis.model_dump(mode="json"), prepared["source_map"])
    program.validate_program(value.analysis.model_dump(mode="json"), prepared["case_boundary"])
    return value


class FinalReview(Review):
    def __init__(self, prepared, context, comparison):
        super().__init__("C6", prepared["source_map"], context, prepared["coverage"],
                         validator=lambda value: (validate_conflicts(value, prepared["source_map"]),
                                                  program.validate_program(value, prepared["case_boundary"])))
        self.prepared, self.comparison = prepared, comparison

    def feedback(self, content):
        restore_final(content, self.prepared, self.comparison)
        sources = copy.deepcopy(self.sources)
        for row in sources.values():
            for key in ("alert_ids", "query_alert_ids", "record_alert_ids"):
                if key in row:
                    row[key] = [self.prepared["case_boundary"]["member_aliases"].get(a, "案件外成员") for a in row[key]]
        aliases = self.prepared["case_boundary"]["member_aliases"]
        owned = program.enabled(self.prepared["case_boundary"])
        return feedback(content, "C6", sources, [aliases[a] for a in self.context.alerts],
            [q.id for q in self.context.questions if not owned or q.id != "coverage"],
            extra_errors=program.program_errors(decode(content)["analysis"], self.prepared["case_boundary"]))

    def partial(self, content):
        result = super().partial(restore_final(content, self.prepared, self.comparison))
        if program.enabled(self.prepared["case_boundary"]):
            retained = self.details["retained_analysis"]
            retained["questions"] = [row for row in retained["questions"] if row["id"] != "coverage"]
            retained["questions"].append(program.coverage_question(retained, self.prepared["case_boundary"]))
            analysis.parse(json.dumps(retained), self.sources, self.context, self.coverage)
        return result
