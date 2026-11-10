"""Restore program-owned fields before the unchanged Deep/C6 validators."""
import copy
import json

from pydantic import ValidationError

from . import baseline_analysis_contract as analysis
from . import baseline_deep_contract as deep
from . import baseline_delivery_contract as delivery
from .analysis_review import Review, decode, empty_reference_feedback
from .structured_output import response_format


def deep_format(prepared):
    fmt = response_format(deep.Decision, prepared["source_map"], bindings=prepared["binding_map"])
    schema = fmt["json_schema"]["schema"]
    schema["properties"].pop("question_id")
    schema["required"].remove("question_id")
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
    recommendation = schema["$defs"]["Recommendation"]
    recommendation["properties"].pop("id")
    recommendation["required"].remove("id")
    if fixed_comparison(comparison):
        schema["properties"].pop("comparison")
        schema["required"].remove("comparison")
    return fmt


def restore_final(content, prepared, comparison):
    value = decode(content)
    boundary = prepared["case_boundary"]
    members = {v: k for k, v in boundary["member_aliases"].items()}
    objects = {v: k for k, v in boundary["object_aliases"].items()}
    try:
        root = value["analysis"]
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
    return delivery.parse(restore_final(content, prepared, comparison),
                          prepared["source_map"], context, prepared["coverage"], comparison)


class FinalReview(Review):
    def __init__(self, prepared, context, comparison):
        super().__init__("C6", prepared["source_map"], context, prepared["coverage"])
        self.prepared, self.comparison = prepared, comparison

    def feedback(self, content):
        sources = copy.deepcopy(self.sources)
        for row in sources.values():
            row["alert_ids"] = [self.prepared["case_boundary"]["member_aliases"].get(a, a) for a in row["alert_ids"]]
        return empty_reference_feedback(content, "C6", sources)

    def partial(self, content):
        return super().partial(restore_final(content, self.prepared, self.comparison))
