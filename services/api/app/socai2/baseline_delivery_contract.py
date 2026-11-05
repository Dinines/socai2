"""C6 output: final analysis, explicit comparison and scoped Case impact."""
import json
from typing import Literal
from uuid import UUID

from pydantic import Field, ValidationError

from . import baseline_analysis_contract as analysis
from .baseline_contracts import Contract
from .baseline_model_view import blocked

SCHEMA = "socai2.baseline-delivery.v1"
Text, Refs = analysis.Text, analysis.Refs


class Conclusion(Contract):
    text: Text
    state: Literal["supported", "uncertain"]
    alert_ids: analysis.Members
    support_ids: Refs
    limitations: list[Text] = Field(max_length=12)


class Comparison(Contract):
    kind: Literal["initial", "unchanged", "expanded", "revised", "withdrawn", "not_comparable"]
    summary: Text | None
    support_ids: Refs


class Impact(Contract):
    summary: Text
    alert_ids: list[UUID] = Field(max_length=200)
    support_ids: Refs
    supported_changes: list[Text] = Field(max_length=12)
    cannot_generalize: list[Text] = Field(min_length=1, max_length=12)
    next_steps: list[Text] = Field(max_length=12)


class Recommendation(Contract):
    id: Text
    action_type: Literal["investigate", "contain", "remediate", "monitor"]
    object_keys: Refs
    reason: Text
    source_ids: Refs
    limitations: list[Text] = Field(max_length=12)


class Delivery(Contract):
    analysis: analysis.Analysis
    conclusion: Conclusion
    closing_note: Text
    comparison: Comparison
    impact: Impact
    recommendations: list[Recommendation] = Field(max_length=12)


def parse(content, source_map, context, coverage, comparison):
    def fail(code):
        raise analysis.AnalysisRejected(code)

    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                fail("duplicate_json_key")
            result[k] = v
        return result

    try:
        raw = json.loads(content, object_pairs_hook=unique, parse_constant=lambda _: fail("invalid_json_number"))
        if blocked(raw):
            fail("delivery_output_guard_blocked")
        def nonblank(item):
            if isinstance(item, str) and not item.strip():
                fail("delivery_blank_text")
            if isinstance(item, dict):
                for v in item.values():
                    nonblank(v)
            if isinstance(item, list):
                for v in item:
                    nonblank(v)
        nonblank(raw)
        value = Delivery.model_validate(raw)
    except (ValueError, TypeError, ValidationError) as exc:
        if isinstance(exc, analysis.AnalysisRejected):
            raise
        raise analysis.AnalysisRejected("delivery_shape_invalid") from None
    analysis.parse(json.dumps(raw["analysis"]), source_map, context, coverage)

    def scope(ids):
        ids = list(map(str, ids))
        if len(ids) != len(set(ids)) or not set(ids) <= set(context.alerts):
            fail("delivery_scope_outside_run_or_duplicate")
        return set(ids)

    def refs(ids, aids=(), *, direct=False):
        if len(ids) != len(set(ids)) or not set(ids) <= set(source_map):
            fail("delivery_source_not_visible_or_duplicate")
        owned = set()
        for sid in ids:
            src = source_map[sid]
            if src["ref"]["role"] == "execution_receipt":
                fail("execution_receipt_not_conclusion_evidence")
            if not direct or (src["ref"]["role"] in {"observation", "human_statement"}
                    and src.get("membership_basis") != "query_binding_only"):
                owned.update(src["alert_ids"])
        if not set(aids) <= owned:
            fail("delivery_source_coverage_missing")

    covered = scope(value.conclusion.alert_ids)
    refs(value.conclusion.support_ids, covered, direct=value.conclusion.state == "supported")
    members = {str(m.alert_id): m for m in value.analysis.members}
    if any(members[a].state == "not_analyzed" for a in covered):
        fail("unanalysed_member_in_conclusion")
    if value.conclusion.state == "uncertain" and not value.conclusion.limitations:
        fail("uncertain_conclusion_needs_limits")
    refs(value.comparison.support_ids)
    baseline_ids = {sid for sid, src in source_map.items() if src["ref"]["type"] == "result"
        and src["ref"]["id"] == comparison["result_id"]}
    comparable = comparison["state"] == "eligible" and bool(baseline_ids)
    if not comparison["result_id"] and comparison["state"] == "initial":
        if value.comparison.kind != "initial" or value.comparison.summary is not None or value.comparison.support_ids:
            fail("initial_delivery_must_not_invent_comparison")
    elif not comparable:
        if value.comparison.kind != "not_comparable" or not value.comparison.summary:
            fail("comparison_not_available")
    elif (value.comparison.kind == "initial" or not value.comparison.summary
            or not (baseline_ids & set(value.comparison.support_ids))
            or (value.comparison.kind != "not_comparable" and not (set(value.comparison.support_ids) - baseline_ids))):
        fail("comparison_needs_selected_baseline_and_current_sources")
    affected = scope(value.impact.alert_ids)
    refs(value.impact.support_ids, affected, direct=bool(value.impact.supported_changes))
    if value.impact.supported_changes and not affected:
        fail("supported_impact_needs_member_scope")
    seen = set()
    for item in value.recommendations:
        if item.id in seen or not set(item.object_keys) <= set(context.scope.object_keys):
            fail("recommendation_identity_or_target_invalid")
        seen.add(item.id)
        refs(item.source_ids)
        if not item.source_ids:
            fail("recommendation_needs_sources")
    return value


def citation_roles(payload):
    if not isinstance(payload, dict):
        return {}
    if payload.get("type") == "delivery_report" and payload.get("delivery"):
        return {"$.delivery": "prior_analysis", "$.result": "prior_analysis"}
    if "result_id" in payload and "findings" in payload:
        return {"$.conclusion": "prior_analysis", "$.findings": "prior_analysis",
            **{f"$.findings.{i}": "prior_analysis" for i in range(len(payload["findings"]))}}
    return analysis.citation_roles(payload)


PROMPT = """C6整案交付：仅按Schema输出完整JSON，不调用工具/执行响应。
source_groups角色/成员适用于组内项。observed只用本成员直接observation，时间仅为上下文；成员属性不互移。标题/厂商/演练标签不证明授权或良性；未提供审批非无审批，端口不证明应用协议。
analysis覆盖全成员/六问题/四领域；无资料用not_analyzed/undetermined，列限制及替代解释。核验：identity认证/MFA/会话/权限/授权；cloud控制面/IAM/配置/影响；phishing邮件/链接/附件/投递/点击/执行；insider数据访问/外传量/目的地/基线/授权。非applicable须解释，引用finding非定性。conflicts仅列至少两条发现的实际矛盾；缺证据不算。
supported结论及实际影响须由对应成员的观察或人工陈述支持；旧判断/标签/图/query_binding_only不作直接事实。impact无确定变化填[]，说明不能推广。
comparison限指定result_id：initial用summary=null/support_ids=[]；基线不可用用not_comparable并说明；可比时引用基线和当前来源，区分范围/判断变化。
followups文字及object_keys限alert_ids，跨成员列全。query单次/deep按结果续查/graph关系核验/human人工确认，不写SQL或扩范围。execution_plan_index对应routes.followup_index；其他followup为新提议。completed/answer_available非问题解决，human handoff非人工确认。
建议限已有对象，不声称审批/执行。closing_note写认识/待核，执行/交付/采用由服务端定。短句，最多3个findings/2个followups；不复制原文/内部码，不宣称全文已读。完整输出目标2200tokens。
"""
