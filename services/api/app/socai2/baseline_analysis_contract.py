"""C3 initial analysis: provisional reasoning, never a final Case judgment."""
import json
import re
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StrictStr, ValidationError

from .baseline_contracts import Contract

SCHEMA = "socai2.baseline-analysis.v1"
EXECUTION_SCHEMA = "socai2.baseline-analysis.v2"
READ_SCHEMAS = {SCHEMA, EXECUTION_SCHEMA}
DOMAINS = ("identity", "cloud", "phishing", "insider")
Text = Annotated[StrictStr, Field(min_length=1, max_length=1200)]
Refs = Annotated[list[StrictStr], Field(max_length=32)]
Members = Annotated[list[UUID], Field(min_length=1, max_length=200)]


class Finding(Contract):
    id: Text
    state: Literal["observed", "inferred", "unresolved"]
    statement: Text
    alert_ids: Members
    support_ids: Refs
    counter_ids: Refs
    alternatives: list[Text] = Field(max_length=8)
    limitations: list[Text] = Field(max_length=12)


class Member(Contract):
    alert_id: UUID
    state: Literal["analyzed", "unresolved", "not_analyzed"]
    summary: Text
    evidence_ids: Refs
    limitations: list[Text] = Field(max_length=12)


class Answer(Contract):
    id: Text
    state: Literal["answered", "unresolved", "not_applicable"]
    answer: Text
    evidence_ids: Refs
    limitations: list[Text] = Field(max_length=12)


class Domain(Contract):
    name: Literal["identity", "cloud", "phishing", "insider"]
    applicability: Literal["applicable", "not_applicable", "undetermined"]
    reason: Text
    alert_ids: list[UUID] = Field(max_length=200)
    finding_ids: Refs
    limitations: list[Text] = Field(max_length=12)


class Conflict(Contract):
    id: Text
    finding_ids: Refs = Field(min_length=2, json_schema_extra={"uniqueItems": True})
    state: Literal["resolved", "unresolved"]
    explanation: Text
    evidence_ids: Refs


class Followup(Contract):
    question_id: Text
    alert_ids: Members
    mode: Literal["query", "deep", "graph", "human"]
    objective: Text
    required_evidence: Text
    source_ids: Refs
    object_keys: Refs


class Analysis(Contract):
    summary: Text
    members: list[Member] = Field(min_length=1, max_length=200)
    findings: list[Finding] = Field(max_length=24)
    questions: list[Answer] = Field(min_length=6, max_length=6)
    domains: list[Domain] = Field(min_length=4, max_length=4)
    conflicts: list[Conflict] = Field(max_length=12)
    followups: list[Followup] = Field(max_length=12)


class ExecutionFollowup(Followup):
    binding_id: StrictStr | None
    priority: Literal["decision_critical", "supporting"]


class ExecutionAnalysis(Analysis):
    followups: list[ExecutionFollowup] = Field(max_length=12)


class AnalysisRejected(ValueError):
    """A safe code, never a provider body or a user-controlled validation message."""


def time_context(ref):
    return ref.get("type") == "artifact" and ref.get("role") == "source_label" and bool(re.fullmatch(
        r"\$\.alerts\.[0-9a-fA-F-]{36}\.alert\.event_time", ref.get("source_path", "")))


def citation_roles(payload):
    if payload.get("validation") == "structure_scope_sources_checked" and payload.get("analysis"):
        return {"$.analysis": "prior_analysis", **{f"$.analysis.findings.{i}": "prior_analysis"
            for i, _ in enumerate(payload["analysis"]["findings"])},
            **{f"$.analysis.followups.{i}": "prior_analysis"
                for i, _ in enumerate(payload["analysis"].get("followups", []))}}
    if payload.get("domain") in DOMAINS:
        return {"$.findings": "prior_analysis", **{f"$.findings.{i}": "prior_analysis"
            for i, _ in enumerate(payload["findings"])}}
    return {}


def parse(content, source_map, context, coverage, *, bindings=None):
    def fail(code):
        raise AnalysisRejected(code)

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                fail("duplicate_json_key")
            result[key] = value
        return result

    try:
        raw = json.loads(content, object_pairs_hook=pairs,
            parse_constant=lambda _: fail("invalid_json_number"))
        analysis = (Analysis if bindings is None else ExecutionAnalysis).model_validate(raw)
    except (ValueError, TypeError, ValidationError) as exc:
        if isinstance(exc, AnalysisRejected):
            raise
        raise AnalysisRejected("analysis_shape_invalid") from None
    member_ids = set(context.alerts)
    question_ids = {q.id for q in context.questions}

    def unique(values, code):
        if len(values) != len(set(values)):
            fail(code)

    def scope(ids):
        ids = list(map(str, ids))
        unique(ids, "duplicate_member")
        if not set(ids) <= member_ids:
            fail("member_outside_run")
        return set(ids)

    def refs(ids, members=None, require_coverage=False):
        unique(ids, "duplicate_source")
        if not set(ids) <= set(source_map):
            fail("source_not_in_model_input")
        available = set()
        for sid in ids:
            owned = set(source_map[sid]["alert_ids"])
            if members and not (owned & members):
                fail("source_member_mismatch")
            available.update(owned)
        if require_coverage and members and not members <= available:
            fail("member_source_coverage_missing")

    ids = [str(m.alert_id) for m in analysis.members]
    unique(ids, "duplicate_member_delivery")
    if set(ids) != member_ids:
        fail("member_delivery_incomplete")
    for item in analysis.members:
        aid = str(item.alert_id)
        refs(item.evidence_ids, {aid}, item.state != "not_analyzed")
        if coverage[aid]["included"] == 0 and item.state != "not_analyzed":
            fail("unseen_member_marked_analyzed")
        if item.state != "analyzed" and not item.limitations:
            fail("member_limitations_required")
    ids = [q.id for q in analysis.questions]
    unique(ids, "duplicate_question")
    if set(ids) != question_ids:
        fail("question_coverage_incomplete")
    for item in analysis.questions:
        refs(item.evidence_ids)
        if item.state == "answered" and not item.evidence_ids:
            fail("answered_question_needs_sources")
        if item.state != "answered" and not item.limitations:
            fail("question_limitations_required")
    finding_ids = [f.id for f in analysis.findings]
    unique(finding_ids, "duplicate_finding")
    for item in analysis.findings:
        members = scope(item.alert_ids)
        refs(item.support_ids, members, item.state != "unresolved")
        refs(item.counter_ids, members)
        if set(item.support_ids) & set(item.counter_ids):
            fail("same_source_as_support_and_counterevidence")
        if item.state == "observed":
            observations = [s for s in item.support_ids if source_map[s]["ref"]["role"] == "observation"]
            if any(source_map[s]["ref"]["role"] != "observation" and not time_context(source_map[s]["ref"])
                    for s in item.support_ids):
                fail("non_observation_promoted_to_observed")
            # A timestamp is context, never the observation that proves a claim.
            if not observations:
                fail("observed_requires_activity_source")
            refs(observations, members, True)
        if item.state == "observed" and any(source_map[s].get("membership_basis") == "query_binding_only" for s in item.support_ids):
            fail("direct_alert_membership_not_proven")
        if item.state == "unresolved" and not item.limitations:
            fail("finding_limitations_required")
    names = [d.name for d in analysis.domains]
    unique(names, "duplicate_domain")
    if set(names) != set(DOMAINS):
        fail("domain_coverage_incomplete")
    finding_lookup = {f.id: f for f in analysis.findings}
    for item in analysis.domains:
        members = scope(item.alert_ids)
        unique(item.finding_ids, "duplicate_domain_finding")
        if not set(item.finding_ids) <= set(finding_ids):
            fail("unknown_domain_finding")
        if item.applicability == "applicable" and not members:
            fail("applicable_domain_needs_scope")
        if item.applicability != "applicable" and not item.limitations:
            fail("unapplied_domain_needs_limitations")
        for fid in item.finding_ids:
            if not set(map(str, finding_lookup[fid].alert_ids)) <= members:
                fail("domain_finding_scope_mismatch")
    unique([c.id for c in analysis.conflicts], "duplicate_conflict")
    for item in analysis.conflicts:
        unique(item.finding_ids, "duplicate_conflict_finding")
        if len(item.finding_ids) < 2 or not set(item.finding_ids) <= set(finding_ids):
            fail("invalid_conflict_findings")
        refs(item.evidence_ids)
        if item.state == "resolved" and not item.evidence_ids:
            fail("resolved_conflict_needs_sources")
    for item in analysis.followups:
        members = scope(item.alert_ids)
        refs(item.source_ids, members)
        if item.question_id not in question_ids:
            fail("followup_question_outside_run")
        if not set(item.object_keys) <= set(context.scope.object_keys):
            fail("followup_objects_outside_run")
        owned = {obj["object_key"] for aid in members for obj in context.alerts[aid].objects
            if isinstance(obj.get("object_key"), str)}
        if not set(item.object_keys) <= owned:
            fail("followup_objects_outside_members")
        if bindings is not None:
            if item.mode == "query":
                binding = bindings.get(item.binding_id)
                if binding is None:
                    fail("followup_binding_not_offered")
                if set(binding["alert_ids"]) != members:
                    fail("followup_binding_member_mismatch")
                bound_objects = {obj["object_key"] for obj in binding["objects"]}
                if not set(item.object_keys) <= bound_objects:
                    fail("followup_binding_object_mismatch")
            elif item.binding_id is not None:
                fail("followup_binding_requires_query")
    return analysis


EXECUTION_PROMPT = """options继承组的hostname/alert_ids/object_keys。query按binding_id取证，列全组alert_ids，对象限组内；空目录禁query。其余模式binding_id=null，deep按结果续查。priority取decision_critical或supporting。绑定不证明返回行属于告警。禁写SQL或参数。"""


DOMAIN_FINDING_SCOPE = "先按证据定领域alert_ids。若finding的alert_ids有任一不在其中，finding_ids就略去该发现；无可引项填[]。"

PROMPT = f"""执行C3初始主分析，不出终报、不结案、不调工具。只引本轮编号；source_groups组内共用角色/成员。
本轮编号含N前缀；历史文本编号不属于本轮。source_label、旧判断、人工陈述不能证明observed；告警时间仅可附作上下文，仍须该成员的observation证明行为。无观察用inferred/unresolved。标题、厂商、测试/演练自述不证明授权、良性或排除恶意；有效旧分诊仍需核实。成员属性不得相互移植。
覆盖全员及六问；无资料填not_analyzed并说明。领域缺资料选undetermined；非applicable写限制，引用不决定适用性。{DOMAIN_FINDING_SCOPE}
四领域：identity核认证/MFA/会话/权限及授权范围；cloud核控制面、资源/IAM/配置及影响；phishing核邮件身份/头、链接/附件、投递/点击/执行；insider核数据访问/外传、数量/目的地/时间、行为基线及授权，不凭作息或角色定恶意。
保留替代解释与未决；conflicts仅列至少两条已有发现的实际矛盾，缺证据不算矛盾，不编造发现凑数。未提供审批、查空、未接通不构成不存在或反证；省略不同于未发生。端口不能证明HTTPS/TLS等应用协议。
followups只提需求：一次补查用query、按返回继续查用deep、关系核验用graph、人工确认用human；不生成SQL或扩范围。正文仅涉及alert_ids，object_keys须属于这些成员；跨成员核验须列全相关成员。
仅返回符合response_format的完整JSON，不加围栏。每段一句短句，合并重复限制，引用发现避免重复叙述；最多3个核心findings、2个必要followups，成员/六问题/四领域完整。目标1800输出tokens，不复制原文或内部限制代码，不宣称全文已读。
"""
