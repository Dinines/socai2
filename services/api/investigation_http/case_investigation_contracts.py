"""External Case investigation directory and fixed-Run lookup."""
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field

from investigation_http.run_record_contracts import RecordView
from investigation_http.story_contracts import InvestigationRef


class CaseInvestigationUsage(RecordView):
    model_calls: int = Field(ge=0, description="本轮已保存的模型步骤数，排除 planned/skipped。")
    total_tokens: int | None = Field(ge=0, description="所有计入的模型步骤均有完整上报时的合计。")
    known_total_tokens: int = Field(ge=0, description="本轮已完整上报用量的小计。")
    unknown_token_calls: int = Field(ge=0, description="本轮用量缺供或未完整上报的模型步骤数。")


class CaseInvestigationPreview(RecordView):
    result_id: UUID
    result_type: Literal["case_result", "alert_assessment", "incident_diagnosis"]
    kind: str = Field(description="预览对应的实际保存结果种类。")
    source_field: Literal["conclusion", "closing_note", "rationale", "summary"]
    text: str = Field(description="选定结果中对应字段的原文。")


class CaseInvestigationCard(InvestigationRef):
    started_at: AwareDatetime | None
    ended_at: AwareDatetime | None
    duration_seconds: float | None = Field(ge=0, description="已保存的实际开始与结束时间之差。")
    input_member_count: int | None = Field(ge=0, description="已验证冻结输入的成员数，未知为 null。")
    tool_record_count: int = Field(ge=0, description="本轮已保存的全部工具步骤数，含 planned/skipped。")
    usage: CaseInvestigationUsage
    preview: CaseInvestigationPreview | None


class CaseInvestigationPage(RecordView):
    case_id: UUID
    items: list[CaseInvestigationCard]
    total: int = Field(ge=0, description="完整 Case 关联集合的不同 Run 数。")
    next_cursor: str | None
    observed_at: AwareDatetime
    limitations: list[str]


class CaseInvestigationLookup(RecordView):
    case_id: UUID
    item: CaseInvestigationCard
    observed_at: AwareDatetime
    limitations: list[str]
