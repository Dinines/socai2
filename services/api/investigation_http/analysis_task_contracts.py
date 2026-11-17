"""External analysis task views; separate from human verification tasks."""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from investigation_http.contracts import AnalysisIntent, RunSubject
from investigation_http.run_directory_contracts import DirectoryResultRef
from investigation_http.run_record_contracts import RecordView


class AnalysisAttemptView(RecordView):
    attempt_no: int = Field(ge=1, description="同任务的实际尝试序号，从1开始；不是内部attempt ID。")
    run_id: UUID | None = Field(description="本次真实Run；准备失败或尚未开始时可空。")
    run_url: str | None = Field(description="该Run详情地址；无Run则为null。")
    started_at: datetime = Field(description="本次尝试实际开始时间，可能早于Run创建。")
    local_ended_at: datetime | None = Field(description="本地实际收尾时间；不是Run的结束时间。")
    interruption_observed_at: datetime | None = Field(description="实际观察到执行中断的时间；未记录为null。")
    local_state: Literal["running", "ended", "interrupted"] = Field(description="本地执行状态，不替代Run结果。")
    outcome: Literal["completed", "failed", "unknown"] | None = Field(description="本次尝试结果；仍执行中为null。unknown不伪造确定结论。")
    failed_at: datetime | None = Field(description="记录失败或未知结果的时间；没有则为null。")
    error_code: str | None = Field(description="保存的失败原因码；没有则为null。")
    error_stage: str | None = Field(description="保存的失败阶段；没有则为null。")
    error_detail: dict[str, str | int | bool] | None = Field(description="受控错误明细，可含exception_type/http_status/stage/code；不含提示词、凭据或堆栈。")
    retryable: bool = Field(description="本次是否为允许重试的已知失败；不保证还剩次数或一定再次执行。")


class AnalysisTaskDetail(RecordView):
    task_id: UUID = Field(description="原始受理任务ID；合并任务仍以原ID读取，不暴露内部根任务ID。")
    status_url: str = Field(description="本任务详情的相对HTTP地址。")
    subject_type: RunSubject = Field(description="告警alert、事件incident或案件case。")
    subject_id: UUID = Field(description="任务所属业务对象ID。")
    kind: Literal["alert_triage", "incident_diagnosis", "case_investigation"] = Field(description="业务任务类型；不包含内部知识同步任务。")
    intent: AnalysisIntent = Field(description="initial首次、check检查更新、rerun重跑、targeted定向、synthesis综合。")
    source: Literal["ingress", "case_create", "periodic", "user", "knowledge"] = Field(description="真实受理来源，不从Run触发字段猜测。")
    status: Literal["accepted", "running", "completed", "failed", "skipped"] = Field(description="accepted包括等待及已安排重试；completed只表示流程结束，不表示结论质量或已采用。")
    reason_code: str | None = Field(description="真实原因，如no_changes、closed_before_start、retry_scheduled或失败码。")
    submitted_at: datetime = Field(description="本任务原始受理时间；合并后仍保留。")
    started_at: datetime | None = Field(description="实际开始时间；尚未开始为null。")
    ended_at: datetime | None = Field(description="本地任务终态时间；不改写Run的unknown。")
    request: dict[str, Any] = Field(description="回显保存的业务请求；当前initial/check/rerun为{}，不含队列或内部输入摘要。")
    retry_count: int = Field(ge=0, description="已实际开始的重试次数；首次尝试不计为重试。")
    next_retry_at: datetime | None = Field(description="已安排重试的最早时间，不保证该时刻启动；未安排为null。")
    latest_run_id: UUID | None = Field(description="最近实际尝试关联的Run；尚无任何Run为null。")
    attempts: list[AnalysisAttemptView] = Field(description="实际尝试，按attempt_no升序；无尝试为[]。")
    results: list[DirectoryResultRef] = Field(description="各次实际保存的结果及读取地址；无结果为[]，不推断或伪造成功。")


class AnalysisUpdateState(RecordView):
    eligible: bool = Field(description="主体是否满足核心自动更新资格；不表示调度已运行或任务正在执行。")
    last_normal_completed_at: datetime | None = Field(description="最近正常全案/事件完成时间；未记录为null。")
    auto_expires_at: datetime | None = Field(description="本轮自动资格到期时间；告警非周期对象为null。")
    next_check_at: datetime | None = Field(description="核心保存的下次检查时间；未安排为null，不保证执行时刻。")
    ineligible_reason: str | None = Field(description="不具资格的原因：not_periodic/not_registered/closed/expired或实际停止原因；具备资格为null。")


class AnalysisTaskPage(RecordView):
    subject_type: RunSubject = Field(description="所查询的业务对象类别。")
    subject_id: UUID = Field(description="所查询的业务对象ID。")
    items: list[AnalysisTaskDetail] = Field(description="按submitted_at DESC、task_id DESC排列的本页任务。")
    total: int = Field(ge=0, description="该主体全部业务分析任务数，含合并原任务，不含知识同步。")
    next_cursor: str | None = Field(description="下一页游标；到底为null，不能跨主体/租户使用。")
    observed_at: datetime = Field(description="本页、总数和更新资格的同一事务观察时刻；跨请求不是冻结快照。")
    update_state: AnalysisUpdateState = Field(description="主体自动更新资格摘要，与任务状态分开表示。")
