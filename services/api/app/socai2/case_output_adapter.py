"""Restore C3 aliases only; the established parser and partial review judge units."""
import copy
import json

from pydantic import ValidationError

from . import baseline_analysis_contract as contract
from .analysis_review import Review, decode
from .baseline_execution_schema import execution_format
from .case_citation_feedback import feedback
from .case_finding_schema import constrain_findings
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
        members=boundary["member_aliases"].values(), questions=[q.id for q in context.questions],
        objects=boundary["object_aliases"].values(), bindings=bindings or ())
    aliased = {key: {**value, "alert_ids": [boundary["member_aliases"][aid] for aid in value["alert_ids"]],
        "objects": [{**obj, "object_key": boundary["object_aliases"][obj["object_key"]]} for obj in value["objects"]]}
        for key, value in (bindings or {}).items()}
    return constrain_findings(execution_format(result, aliased), prepared["source_map"], context.alerts)


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
    return contract.parse(restore(content, prepared["case_boundary"]), prepared["source_map"],
        context, prepared["coverage"], bindings=bindings)


class CaseReview(Review):
    def __init__(self, prepared, context, bindings):
        super().__init__("C3", prepared["source_map"], context, prepared["coverage"], bindings=bindings)
        self.boundary = prepared["case_boundary"]

    def feedback(self, content):
        restore(content, self.boundary)
        sources = copy.deepcopy(self.sources)
        for item in sources.values():
            for key in ("alert_ids", "query_alert_ids", "record_alert_ids"):
                if key in item:
                    item[key] = [self.boundary["member_aliases"].get(aid, "案件外成员") for aid in item[key]]
        return feedback(content, "C3", sources, self.boundary["member_aliases"].values(), [q.id for q in self.context.questions])

    def partial(self, content):
        return super().partial(restore(content, self.boundary))
