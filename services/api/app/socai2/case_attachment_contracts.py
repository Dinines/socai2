"""Case file references; the business backend owns file storage and download."""
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator

from .baseline_contracts import Contract


class CaseAttachmentCreate(Contract):
    operation_key: UUID = Field(description="本次登记的幂等键；同案同作者同元数据重试沿用。")
    file_id: str = Field(min_length=1, max_length=512, description="业务后端已保存文件的稳定ID，不是下载URL；文件内容变化须使用新ID。")
    file_name: str = Field(min_length=1, max_length=512, description="业务后端提供的文件显示名，原值保存，不作为路径使用。")
    mime_type: str = Field(min_length=1, max_length=255, description="业务后端声明的文件内容类型，例如application/pdf。")
    size_bytes: int = Field(strict=True, ge=0, le=9223372036854775807, description="业务后端声明的完整文件字节数；本服务不读取文件核验。")
    sha256: str | None = Field(default=None, pattern="^[0-9a-f]{64}$", description="业务后端提供的文件SHA-256；未知可省略或为null，不由本服务计算或验证。")

    @field_validator("file_id", "file_name", "mime_type")
    @classmethod
    def text_metadata(cls, value):
        if not value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("attachment metadata must be nonblank text without control characters")
        return value

    @field_validator("file_id")
    @classmethod
    def file_identity(cls, value):
        if "://" in value:
            raise ValueError("file_id must be a backend file identity, not a URL")
        return value


class CaseAttachmentView(Contract):
    id: UUID = Field(description="本服务保存的附件关联ID，不是业务后端文件ID。")
    case_id: UUID = Field(description="附件明确归属的Case。")
    file_id: str = Field(description="业务后端文件ID；由业务后端据此提供下载或报告文件失效。")
    file_name: str = Field(description="登记时业务后端提供的文件显示名。")
    mime_type: str = Field(description="登记时业务后端声明的文件内容类型，未经本服务检测。")
    size_bytes: int = Field(ge=0, description="登记时业务后端声明的文件字节数，未经本服务核验。")
    sha256: str | None = Field(description="业务后端提供的文件哈希；null表示未提供，不是校验失败。")
    created_by: UUID = Field(description="实际登记人的认证用户ID，由服务端保存。")
    created_at: AwareDatetime = Field(description="服务端保存附件关联的时间，不是文件发生时间。")
    file_owner: Literal["business_backend"] = Field(description="文件字节、上传和下载统一由业务后端管理。")
    availability: Literal["managed_by_backend"] = Field(description="本服务只提供引用，未探测文件实时存在性或可下载性；下载结果由业务后端决定。")


class CaseAttachmentPage(Contract):
    items: list[CaseAttachmentView] = Field(description="本服务登记到指定Case的附件，按created_at/id升序；不混入Run工件或其他案件。")
    total: int = Field(ge=0, description="指定Case已登记附件引用的总数，不是探测可下载文件数。")
    next_offset: int | None = Field(description="有后续记录时的下一页偏移，否则null；不承诺跨请求冻结快照。")
    observed_at: AwareDatetime = Field(description="本次只读一致快照的观察时间。")
