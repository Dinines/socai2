"""Ordinary Case collaboration notes, separate from human evidence and results."""
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator

from .baseline_contracts import Contract


class CaseCommentCreate(Contract):
    operation_key: UUID = Field(description="本次评论的幂等键；同案同作者同正文重试沿用，改变意图须新键。")
    body: str = Field(min_length=1, max_length=20000, description="普通评论纯文本原文，不接受空白；不会自动成为已核实事实或触发调查。")

    @field_validator("body")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("comment must not be blank")
        return value


class CaseCommentView(Contract):
    id: UUID = Field(description="已保存评论ID。")
    case_id: UUID = Field(description="评论所属Case；不因共享告警混入其他案件。")
    body: str = Field(description="完整普通评论原文；调用方按纯文本显示，不作为已核实事实。")
    author_id: UUID = Field(description="认证用户的实际作者ID，由服务端保存。")
    author_name_snapshot: str = Field(description="提交时作者显示名快照，不随人员目录后续改名而改写。")
    created_at: AwareDatetime = Field(description="服务端保存时间。")
    edited_at: AwareDatetime | None = Field(description="历史记录的实际编辑时间；本接口只追加，不提供编辑，新增为null。")
    edited_by: UUID | None = Field(description="历史记录的实际编辑人；新增评论为null。")
    row_version: int = Field(ge=1, description="评论自身行版本；本接口新增为1，不是Case版本。")


class CaseCommentPage(Contract):
    items: list[CaseCommentView] = Field(description="指定Case评论，按created_at、id升序；无评论为[]。")
    total: int = Field(ge=0, description="指定Case的评论总数，不包含成员告警或事件的评论。")
    next_offset: int | None = Field(description="有后续记录时的下一页偏移，否则null；分页不是跨请求冻结快照。")
    observed_at: AwareDatetime = Field(description="本次只读一致快照的观察时间。")
