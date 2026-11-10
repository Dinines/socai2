"""Five-field candidate -> existing validated AlertOutput; never a new verdict."""
import json
from copy import deepcopy
from typing import Literal

from pydantic import Field, ValidationError

from app.socai2 import alert_basic_contract as legacy
from app.socai2.baseline_contracts import Contract
from app.socai2.baseline_store import StoreError
from app.socai2.stage_result_contracts import AlertOutput
from app.socai2.structured_output import response_format


class Answer(Contract):
    verdict: Literal["true_positive", "false_positive", "benign", "needs_review"]
    confidence: float | None = Field(ge=0, le=1, allow_inf_nan=False)
    rationale: legacy.Text
    evidence_ids: list[legacy.Alias] = Field(min_length=1, max_length=30)
    recommendations: list[legacy.Advice] = Field(max_length=5)


def schema(sources):
    fmt = response_format(Answer, sources)
    base = fmt["json_schema"]["schema"]
    defs = base.pop("$defs", {})
    direct = [sid for sid, src in sources.items() if src["ref"]["role"] in {"observation", "human_statement"}]
    branches = []
    for verdict in ("needs_review", "true_positive", "benign", "false_positive"):
        if verdict != "needs_review" and not direct:
            continue
        branch = deepcopy(base)
        branch["properties"]["verdict"] = {"type": "string", "enum": [verdict]}
        if verdict != "needs_review":
            branch["properties"]["evidence_ids"]["items"] = {"type": "string", "enum": direct}
        branches.append(branch)
    fmt["json_schema"]["schema"] = {"type": "object", "anyOf": branches, "$defs": defs}
    return fmt


def decode(content):
    def unique(pairs):
        obj = {}
        for k, v in pairs:
            if k in obj:
                raise StoreError("alert_answer_duplicate_key", 422)
            obj[k] = v
        return obj
    return json.loads(content, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(StoreError("alert_answer_nonfinite", 422)))


def canonical(content):
    try:
        answer = Answer.model_validate(decode(content))
    except (ValueError, TypeError, ValidationError) as exc:
        raise StoreError("alert_answer_shape_invalid", 422) from exc
    body = answer.model_dump(mode="json")
    kind = {"true_positive": "malicious_behavior", "benign": "authorized_or_expected_behavior",
            "false_positive": "refuted_detection"}.get(answer.verdict)
    body.update(explanation=answer.rationale, limitations=[], decision_basis=None if kind is None else {
        "kind": kind, "claim": answer.rationale, "source_ids": answer.evidence_ids})
    return body


def parse(content, prepared, *, diagnostics=None):
    body = canonical(content)
    result = legacy.parse(json.dumps(body, ensure_ascii=False), prepared["source_map"], prepared["data"], diagnostics=diagnostics)
    return assemble(result, prepared)


def assemble(result, prepared):
    refs = {json.dumps(ref, sort_keys=True): ref for ref in [
        *[v.model_dump(mode="json") for v in result.source_refs], *prepared["fact_refs"]]}
    return AlertOutput.model_validate({**result.model_dump(mode="json"),
                                      "explanation": prepared["fact_text"] + "\n分析原文：" + result.rationale,
                                      "generation_method": "template", "source_refs": list(refs.values())})


def review(content, prepared):
    from .stage_answer_review import review_alert
    try:
        body = canonical(content)
    except StoreError:
        return None, None
    result, detail = review_alert(json.dumps(body, ensure_ascii=False), prepared["source_map"], prepared["data"])
    if result is not None:
        result = assemble(result, prepared)
        detail["retained_analysis"]["assessment"] = result.model_dump(mode="json")
    return result, detail
