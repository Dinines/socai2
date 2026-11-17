"""Question-level decisions; no SQL, filter arguments, or Case verdict."""
import json
from typing import Literal

from pydantic import Field, ValidationError

from .baseline_analysis_contract import AnalysisRejected, Refs, Text
from .baseline_contracts import Contract
from .case_citation_quality import normalized, reject_or_record
from .citation_quality import record_references

SCHEMA = "socai2.baseline-deep.v2"
READ_SCHEMAS = {"socai2.baseline-deep.v1", SCHEMA}


class Answer(Contract):
    state: Literal["supported", "unresolved"]
    text: Text
    support_ids: Refs
    counter_ids: Refs
    alternatives: list[Text] = Field(max_length=8)
    limitations: list[Text] = Field(max_length=12)


class Decision(Contract):
    question_id: Text
    action: Literal["query", "answer", "handoff"]
    binding_id: Text | None
    reason: Text
    answer: Answer | None


def validate_answer(answer, source_map, *, citation_review=None):
    """An answer can be retained independently of an incomplete control decision."""
    for field, ids in (("support_ids", answer.support_ids), ("counter_ids", answer.counter_ids)):
        path = "$.answer." + field
        record_references(citation_review, ids, source_map, path,
            required=field == "support_ids" and answer.state == "supported")
        if len(ids) != len(set(ids)) or not set(ids) <= set(source_map):
            reject_or_record(citation_review, "source_not_in_model_input_or_duplicate", path)
        if any(source_map[s]["ref"]["role"] == "execution_receipt" for s in ids if s in source_map):
            reject_or_record(citation_review, "execution_receipt_is_not_evidence", path)
    if set(answer.support_ids) & set(answer.counter_ids):
        reject_or_record(citation_review, "same_source_as_support_and_counterevidence", "$.answer")
    if answer.state == "supported" and not answer.support_ids:
        reject_or_record(citation_review, "supported_answer_needs_sources", "$.answer")
    if answer.state == "unresolved" and not answer.limitations:
        reject_or_record(citation_review, "unresolved_answer_needs_limitations", "$.answer")


def parse(content, source_map, bindings, question_id, *, citation_review=None):
    path = "$"
    def fail(code):
        reject_or_record(citation_review, code, path)

    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                fail("duplicate_json_key")
            result[k] = v
        return result

    try:
        raw = json.loads(content, object_pairs_hook=pairs, parse_constant=lambda _: fail("invalid_json_number"))
        value = Decision.model_validate(normalized(raw, citation_review))
    except (ValueError, TypeError, ValidationError) as exc:
        if isinstance(exc, AnalysisRejected):
            raise
        raise AnalysisRejected("deep_shape_invalid") from None
    if value.question_id != question_id:
        fail("question_outside_frozen_scope")
    if value.action == "query":
        if value.binding_id not in bindings or value.answer is not None:
            fail("unoffered_query_or_premature_answer")
    else:
        if value.binding_id is not None or value.answer is None:
            fail("answer_contract_invalid")
        answer = value.answer
        validate_answer(answer, source_map, citation_review=citation_review)
        path = "$.answer"
        if value.action == "handoff" and answer.state != "unresolved":
            fail("handoff_must_remain_unresolved")
    return value


def citation_roles(payload):
    if payload.get("type") == "deep_summary" and payload.get("answer"):
        return {"$.answer": "prior_analysis"}
    if payload.get("domain") == "question_deep":
        return {"$.questions": "prior_analysis"}
    return {}


PROMPT = """只处理输入的一个案件问题，不给全案结论，不结案。依据本次可见E来源回答，或选择目录中的一个B查询后等待实际结果。
查询只能填binding_id；不能填SQL/参数、扩主机或窗口。曾执行/跳过的查询不再提供，不能换理由重试。
related_alert_ids仅表示为何查此主机，不证明每行属于这些告警；相同记录的多个字段不算独立证据。父进程/共同会话/时间接近不能直接推出因果。
查空、未接通、未提供授权不构成反证或不存在。字段/行被省略不代表原文没有。prior_analysis只是待核旧判断。
够用选answer；需要目录以外来源/人工确认选handoff，明确缺口；不要为了完成问题消耗所有查询。回答只能引用本次E编号。
按Schema返回短JSON；query时answer=null，answer/handoff时binding_id=null且填写answer，handoff必须unresolved。source_groups的角色与成员适用于组内各项。"""
