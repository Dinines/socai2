"""External representation of the current Case information summary."""
from uuid import UUID

from pydantic import AwareDatetime, Field

from investigation_http.contracts import TacticCount
from investigation_http.run_record_contracts import RecordView


class CaseInfoObject(RecordView):
    object_id: UUID = Field(description="当前对象分组中 ID 最小的原始对象记录。")
    namespace: str
    object_type: str
    object_key: str
    raw_value: str
    alert_id: UUID
    material_id: UUID
    source_path: str


class CaseInfoSummary(RecordView):
    case_id: UUID
    scope_revision: int = Field(ge=0)
    observed_at: AwareDatetime
    member_object_count: int = Field(ge=0, description="当前成员最新材料的不同对象组总数。")
    object_preview: list[CaseInfoObject] = Field(
        max_length=4, description="按 namespace、object_type、object_key 排序的前四个对象组及各组的一条真实来源。",
    )
    members_without_current_material_count: int = Field(ge=0)
    activity_time_from: AwareDatetime | None
    activity_time_to: AwareDatetime | None
    tactics: list[TacticCount] = Field(description="当前材料的源战术标签及各标签的去重告警数。")
    investigation_count: int = Field(ge=0, description="案件调查历史目录涵盖的不同 Run 总数。")
