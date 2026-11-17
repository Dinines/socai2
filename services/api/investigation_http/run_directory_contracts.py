"""Public contract for the unified saved-Run directory."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from investigation_http.contracts import (
    AnalysisIntent,
    Delivery,
    DirectoryRunKind,
    RunState,
    RunSubject,
)
from investigation_http.run_record_contracts import RecordView


class DirectoryResultRef(RecordView):
    result_type: Literal["case_result", "alert_assessment", "incident_diagnosis"] = Field(description="结果记录类型。")
    id: UUID = Field(description="该条真实结果的ID，不是Run或任务ID。")
    source_run_id: UUID = Field(description="产生结果的Run ID，与所在目录项一致。")
    kind: str = Field(description="结果种类，沿已保存记录返回。")
    url: str = Field(description="读取结果的相对HTTP地址；告警/事件结果在Run详情中，Case结果有独立详情。")


class RunDirectoryItem(RecordView):
    run_id: UUID = Field(description="一次已保存分析记录的ID；同任务重试可产生多个Run。")
    subject_type: RunSubject = Field(description="分析对象类别：告警、事件或案件。")
    subject_id: UUID = Field(description="实际分析对象ID。")
    subject_title: str | None = Field(description="对象当前标题；没有标题时为null。")
    run_kind: DirectoryRunKind = Field(description="本次执行类型，不代表发起意图。")
    # Required even when null: a missing provider cannot quietly claim history.
    intent: AnalysisIntent | None = Field(description="真实任务意图：initial首次、check检查更新、rerun重跑、targeted定向、synthesis综合；历史无关联为null。")
    task_id: UUID | None = Field(description="经真实attempt关联的任务ID；历史无关联为null，不根据trigger猜测。")
    state: RunState = Field(description="Run执行状态；unknown保持结果未知，不自动转为成功或失败。")
    delivery_state: Delivery = Field(description="交付完整性：none无、partial部分、complete完整、unknown未知；独立于执行状态。")
    requested_at: datetime | None = Field(description="Run记录的请求时间；用于筛选和倒序分页，不取任务submitted_at。")
    started_at: datetime | None = Field(description="Run实际开始时间；未记录为null。")
    ended_at: datetime | None = Field(description="Run结束时间；未记录/unknown可为null，不用任务结束时间代替。")
    input_member_count: int | None = Field(ge=0, description="本次冻结输入成员数，不是主体当前成员数；未知为null，已保存空数组为0。")
    results: list[DirectoryResultRef] = Field(description="实际保存的结果及各版本引用；无结果为[]。")
    detail_url: str = Field(description="读取该Run详情的相对HTTP地址。")


class RunDirectoryStatistics(RecordView):
    total_runs: int = Field(ge=0, description="全部筛选结果的Run数，与分页total一致。")
    by_state: dict[RunState, int] = Field(description="全部筛选结果按Run状态计数；未出现的枚举为0。")
    by_delivery_state: dict[Delivery, int] = Field(description="全部筛选结果按交付状态计数；未出现的枚举为0。")
    without_related_case_count: int = Field(ge=0, description="当前没有实际Case关联的Run数；不计候选关联。")
    related_case_count: int = Field(ge=0, description="全部筛选结果实际关联的不同Case数；多路径及多Run去重。")


class RunDirectoryPage(RecordView):
    items: list[RunDirectoryItem] = Field(description="本页，按requested_at DESC、run_id DESC排序。")
    total: int = Field(ge=0, description="符合所有筛选的Run总数，不是本页数量。")
    next_cursor: str | None = Field(description="下一页游标；结束为null，变更筛选需重取第一页。")
    observed_at: datetime = Field(description="本页及统计的数据库观察时间；跨页不是永久冻结快照。")
    statistics: RunDirectoryStatistics = Field(description="与本页同一只读事务、全部筛选范围的统计；分页不缩小范围。")
