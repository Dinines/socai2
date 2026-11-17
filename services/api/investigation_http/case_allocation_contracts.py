"""External allocation views extend core facts only with HTTP navigation."""
from pydantic import Field

from investigation_http.contracts import (
    CoreCaseAllocation,
    CoreCaseAllocationReceipt,
    CoreCaseMoveReceipt,
    CoreCaseReplacementReceipt,
    CoreInitialTaskReceipt,
    CoreRelatedCaseItem,
    CoreRelatedCasePage,
)


class InitialCaseTaskReceipt(CoreInitialTaskReceipt):
    status_url: str = Field(description="首轮分析任务详情的相对HTTP地址；accepted仅表示持久受理。")


class CaseAllocation(CoreCaseAllocation):
    initial_task: InitialCaseTaskReceipt | None = Field(description="本次新案的真实首轮任务；非新案为null。")
    case_url: str = Field(description="本次实际分配案件的HTTP详情地址。")


class CaseAllocationReceipt(CoreCaseAllocationReceipt):
    allocations: list[CaseAllocation] = Field(description="本次涉及的实际目标Case及新增/已有成员，按续建顺序返回。")


class CaseReplacementReceipt(CoreCaseReplacementReceipt):
    allocation: CaseAllocationReceipt


class CaseMoveReceipt(CoreCaseMoveReceipt):
    allocation: CaseAllocationReceipt


class RelatedCaseItem(CoreRelatedCaseItem):
    case_url: str = Field(description="该关联Case的HTTP详情地址；GET不切换接收者或触发调查。")


class RelatedCasePage(CoreRelatedCasePage):
    items: list[RelatedCaseItem]
