"""The I/C6 verdict is an independent unit of the existing model answer."""
import hashlib

from pydantic import TypeAdapter

from .enums import BusinessVerdict
from .stage_delivery import Unit

FIELD = "business_verdict"
PATH = "$.business_verdict"
VERSION = "socai2.business-verdict.v1"
VERDICT = TypeAdapter(BusinessVerdict)

RULE = (
    "在顶层输出business_verdict。malicious表示本轮证据支持行为构成威胁，benign表示证据支持行为正常或已授权，"
    "false_positive表示证据表明检测或归因前提不成立，needs_review表示证据不足定性或仍有冲突。"
    "用现有结论、依据与限制交代判断理由。严重程度、告警投票、未查询或查空不能决定该字段。"
)
INCIDENT_RULE = "事件判定只适用于本轮选入且已分析的成员，不推广到其余成员。" + RULE
CASE_RULE = "业务判定只覆盖conclusion.alert_ids声明的本轮范围，由本轮证据支撑。" + RULE


def extend_schema(schema, prepared):
    schema["properties"][FIELD] = VERDICT.json_schema()
    schema["required"].append(FIELD)
    prepared["business_verdict_version"] = VERSION


def enabled(prepared):
    return prepared.get("business_verdict_version") == VERSION


def receive_unit(unit, content, original_id, content_path):
    value = VERDICT.validate_python(unit["value"], strict=True)
    start, end = unit["value_span"]
    return Unit.model_validate({**unit, "value": value, "original_artifact_id": original_id,
        "original_content_path": content_path, "value_sha256": hashlib.sha256(content[start:end].encode()).hexdigest(),
        "declared_scope": None, "resolved_refs": [], "structure_state": "valid", "quality_issues": []}).model_dump(mode="json")
