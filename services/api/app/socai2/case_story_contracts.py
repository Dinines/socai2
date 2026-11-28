"""Read-only story envelopes; source DTOs retain their existing contracts."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator

from .baseline_contracts import Contract
from .case_contracts import ResultView, RunView
from .enums import Severity
from .human_task_contracts import TaskRevisionView
from .page_contracts import AlertFacts


class StoryQuery(Contract):
    q: str | None = Field(default=None, max_length=200, description="字面关键词；查询标题、说明及各类型明确的业务正文。告警还检索最新材料的主机/账号对象值。")
    severity: Severity | None = Field(default=None, description="只筛选告警等级；调查和人工完成结果保留作上下文。")
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=2048)

    @field_validator("q")
    @classmethod
    def trim_search(cls, value):
        return (value.strip() or None) if value is not None else None


class RelatedStoryQuery(StoryQuery):
    view: Literal["related"] = "related"
    focus_alert_id: UUID | None = None


class MemberRelationsQuery(Contract):
    objects_limit: int = Field(default=20, ge=1, le=100)
    objects_cursor: str | None = Field(default=None, max_length=2048)
    runs_limit: int = Field(default=20, ge=1, le=100)
    runs_cursor: str | None = Field(default=None, max_length=2048)


class StorySummary(Contract):
    member_alert_count: int = Field(ge=0)
    member_object_count: int = Field(ge=0)
    members_without_current_material_count: int = Field(ge=0)
    activity_time_from: AwareDatetime | None
    activity_time_to: AwareDatetime | None
    matched_alert_count: int = Field(ge=0)
    focus_alert_id: UUID | None


class StoryCursor(Contract):
    fingerprint: str
    at: AwareDatetime | None
    key: str = Field(pattern=r"^(alert|investigation|human_result):[0-9a-f-]{36}$")


class MemberRelationCursor(Contract):
    fingerprint: str
    id: UUID
    at: AwareDatetime | None = None


class StoryEntry(Contract):
    id: str = Field(description="稳定条目键：alert/investigation/human_result加源记录UUID。")
    kind: Literal["alert", "investigation", "human_result"] = Field(description="告警事实、基础调查或人工完成修订；不包含AI对话。")
    occurred_at: datetime | None = Field(description="该条目的实际业务时间；未知为null并排在最后，不以读取时间补齐。")
    time_source: Literal["event_time", "started_at", "ended_at", "completed_at", "unknown"] = Field(description="occurred_at对应的源时间字段；缺失为unknown。")
    alert: AlertFacts | None = Field(default=None, description="告警条目复用原告警事实合同；其他类型为null。E28按id回查，战术/库存用E31/E30。")
    run: RunView | None = Field(default=None, description="调查条目的原Run；其他类型为null。E12按case_id/id回查。")
    results: list[ResultView] = Field(default_factory=list, description="终态Run已保存的baseline结果，按saved_at/id升序；活跃或无结果为空，不代表没有风险。E14按结果id回查。")
    task_revision: TaskRevisionView | None = Field(default=None, description="人工完成条目的不可变原修订；其他类型为null。E43按case/task/revision回查。")
    is_current_task_revision: bool | None = Field(default=None, description="此完成修订是否仍为任务当前修订；false仍保留历史事实，不能据此判断当前待办。其他类型为null。")


class StoryPage(Contract):
    items: list[StoryEntry] = Field(description="本页故事条目；按真实时间倒序、未知时间最后，同时间按稳定id倒序。")
    total: int = Field(description="整个Case内筛选命中的故事条目数，不是当前页数或告警数。")
    next_cursor: str | None = Field(description="原样用于相同Case和筛选的下一页；null结束，条件改变须清空。")
    observed_at: datetime = Field(description="本次数据库读取时间；每请求一致快照，跨页源数据变化后应刷新。")
