"""Asynchronous Incident/Case admission, independent of internal execution."""
from typing import Literal
from uuid import UUID

from pydantic import Field

from investigation_http.contracts import RunSubject
from investigation_http.run_record_contracts import RecordView


class AnalysisSubmitRequest(RecordView):
    operation_key: UUID = Field(description="本次操作的幂等UUID；重放相同请求沿用，不以换key代替查询进度。")
    mode: Literal["check", "rerun"] = Field(description="check检查已有材料变化；rerun明确重新分析。执行判断由调查核心负责。")


class AnalysisTaskReceipt(RecordView):
    task_id: UUID = Field(description="已持久受理的原任务ID；同key同内容返回原ID。")
    subject_type: RunSubject = Field(description="任务真实所属对象类型。")
    subject_id: UUID = Field(description="任务真实所属对象ID。")
    status: Literal["accepted"] = Field(description="仅表示受理已保存，不表示已经开始或完成；最新状态读status_url。")
    status_url: str = Field(description="已注册任务详情GET的相对HTTP地址。")
