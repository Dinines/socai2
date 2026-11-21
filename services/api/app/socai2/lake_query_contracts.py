"""Core lake read contracts. HTTP URLs and transport dependencies stay outside."""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class LakeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LakeSelector(LakeModel):
    role: Literal["device", "source", "destination", "legacy_host"]
    kind: Literal["hostname", "ip"]
    value: str = Field(min_length=1, max_length=253, description=(
        "hostname允许Unicode字母、数字、组合标记及_.-，不接受空白或控制字符；"
        "仅ASCII字母不区分大小写，其余字符原样匹配。ip使用IP地址。"))


class LakeSearch(LakeModel):
    source_namespace: str = Field(max_length=512)
    mapping_version: str = Field(max_length=128)
    selector: LakeSelector | None = None
    time_basis: Literal["event", "ingest", "legacy_event"]
    start: AwareDatetime
    end: AwareDatetime
    class_uids: list[Annotated[int, Field(strict=True, ge=0, le=4294967295)]] | None = Field(default=None, max_length=64)
    limit: int | None = Field(default=None, ge=1, strict=True)
    cursor: str | None = Field(default=None, max_length=4096)


class LakeRecordRef(LakeModel):
    event_id: UUID
    source_namespace: str = Field(max_length=512)
    mapping_version: str = Field(max_length=128)
    source_version: str = Field(max_length=256)
    event_time: AwareDatetime
    class_uid: int = Field(ge=0, le=4294967295)


class LakeEventView(LakeModel):
    record_ref: LakeRecordRef
    ingest_time: datetime
    event_time_source: str
    parse_status: str
    source_event_id: str
    is_alert: int | None
    device_hostname: str
    device_ip: str | None
    src_hostname: str
    source_ip: str | None
    dst_hostname: str
    dest_ip: str | None


class LakeSearchResult(LakeModel):
    state: Literal["completed"] = "completed"
    items: list[LakeEventView]
    next_cursor: str | None
    has_more: bool
    time_basis: Literal["event", "ingest", "legacy_event"]
    selector: LakeSelector | None = None
    limitations: list[str]


class LakeMaterial(LakeModel):
    state: Literal["completed"] = "completed"
    record_ref: LakeRecordRef
    parse_status: str
    event_time_source: str
    completeness: Literal["complete", "legacy_unverified", "preview"]
    raw_payload_encoding: Literal["utf8", "base64", "tombstone", "legacy_unspecified"]
    ocsf_json: str
    raw_payload: str


class LakeReadError(RuntimeError):
    def __init__(self, code, state="failed", status=502, rows=None):
        super().__init__(code)
        self.code, self.state, self.status, self.rows = code, state, status, rows
