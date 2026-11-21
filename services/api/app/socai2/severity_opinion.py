"""Independent I/C6 output unit; source aliases never become program identities."""
import copy
import hashlib
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from .baseline_contracts import Contract
from .baseline_model_view import blocked
from .baseline_store import StoreError
from .citation_quality import issue, new_review, record_references
from .stage_delivery import Unit

VERSION = "socai2.severity-opinion.v1"
PATH = "$.severity_opinion"
Text = Annotated[str, StringConstraints(min_length=1, max_length=3000, pattern=r"\S")]


class ImpactBasis(Contract):
    confirmed: list[Text] = Field(max_length=12)
    potential: list[Text] = Field(max_length=12)


class Opinion(Contract):
    level: Literal["info", "low", "medium", "high", "critical"]
    reason: Text
    impact_basis: ImpactBasis
    source_refs: list[str] = Field(max_length=60)
    limitations: list[Text] = Field(max_length=12)


PROMPT = (
    "另输出独立severity_opinion单元，评价本次选入事件成员或全案调查范围的安全影响，"
    "不是恶意概率、置信度或任务成败。不重复计算来源最高等级或优先级。"
    "info须有正常/授权/误报依据且无仍需处置影响；low为有依据的有限局部影响；"
    "medium为需调查处置但未达高影响依据的风险；high须重要资产、特权身份、敏感数据"
    "或较大业务范围的高影响依据；critical须关键系统控制、核心业务严重受损或持续重大破坏/泄露依据。"
    "reason说明依据，impact_basis.confirmed只写已确认影响，potential写潜在影响，未确定的不能写成已发生。"
    "source_refs只引用本轮可见来源别名，limitations保留限制和反证。未查、查空或失败不证明安全。"
    "待复核仍需有说明的等级意见。不要生成主体/Run/结果ID、优先级数字、人工操作或执行台账。"
)


def extend_schema(schema, prepared):
    """Version only the added unit; legacy analysis schemas remain readable."""
    unit = Opinion.model_json_schema()
    schema.setdefault("$defs", {}).update(unit.pop("$defs", {}))
    evidence = sorted(sid for sid, src in prepared["source_map"].items()
                      if src["ref"]["role"] != "execution_receipt")
    unit["properties"]["source_refs"]["items"] = {"type": "string", **({"enum": evidence} if evidence else {})}
    if not evidence:
        unit["properties"]["source_refs"]["maxItems"] = 0
    schema["properties"]["severity_opinion"] = unit
    schema["required"].append("severity_opinion")
    prepared["severity_opinion_version"] = VERSION
    return schema


def enabled(prepared):
    return prepared.get("severity_opinion_version") == VERSION


def receive_unit(unit, content, prepared, original_id, content_path):
    raw = unit["value"]
    if blocked(raw):
        raise StoreError("severity_opinion_content_blocked", 422)
    value = Opinion.model_validate(raw, strict=True).model_dump(mode="json")
    sources = {sid: src for sid, src in prepared["source_map"].items()
               if src["ref"]["role"] != "execution_receipt"}
    review = new_review()
    record_references(review, value["source_refs"], sources, PATH + ".source_refs", required=True)
    unknown = sorted(set(value["source_refs"]) - set(sources))
    if unknown:
        issue(review, "unbound_source_ids", PATH + ".source_refs", unresolved_ids=unknown)
    if len(value["source_refs"]) != len(set(value["source_refs"])):
        issue(review, "duplicate_source", PATH + ".source_refs", source_ids=value["source_refs"])
    resolved = [{"source_id": sid, "ref": copy.deepcopy(sources[sid]["ref"]),
                 "alert_ids": list(sources[sid].get("alert_ids", []))}
                for sid in dict.fromkeys(value["source_refs"]) if sid in sources]
    start, end = unit["value_span"]
    record = Unit.model_validate({**unit, "original_artifact_id": original_id,
        "original_content_path": content_path,
        "declared_scope": None,
        "value_sha256": hashlib.sha256(content[start:end].encode()).hexdigest(),
        "resolved_refs": resolved, "structure_state": "valid", "quality_issues": review["issues"]}).model_dump(mode="json")
    return value, record, review
