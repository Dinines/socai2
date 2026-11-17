"""Exploration snapshots are browsing state, never investigation conclusions."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, JsonValue, model_validator

from .baseline_contracts import Contract
from .exploration_contracts import ExplorationMatch, ExplorationObject
from .page_contracts import AlertFacts


class ExplorationSources(Contract):
    alerts: list[AlertFacts] = Field(description="保存时的告警事实；继续旧快照保留原值，不代表实时状态。")
    objects: list[ExplorationObject] = Field(description="对应明确材料版本的原始对象；保留原件 ID 和字段路径。")


class ExplorationBase(Contract):
    kind: Literal["members", "investigation"] = Field(description="members 为无完成调查时的成员关系；investigation 为指定完成调查。")
    case_id: UUID = Field(description="底图所属案件。")
    run_id: UUID | None = Field(description="固定的已完成基础调查 ID；成员底图为 null。")
    result_id: UUID | None = Field(description="该调查的基础结果 ID；缺结果为 null。")
    graph_artifact_id: UUID | None = Field(description="该结果关联的图原件 ID；结果未关联图时 null；已有引用但内容不可用时保留 ID，查看 graph_state。")
    scope_revision: int = Field(description="底图成员范围版本；调查图使用该 Run 的版本。")
    delivery_state: str | None = Field(description="原调查交付状态，partial 保留；成员图为 null。")
    graph_state: str = Field(description="members 或原图材料状态；缺图为 unavailable，不能借用其他轮图。")
    graph: JsonValue = Field(description="原调查图 JSON 原样保留；成员底图或缺图时为 null。")
    sources: ExplorationSources = Field(description="成员或 Run 成员的告警与指定材料对象；图原文仍以 graph 为准。")
    fingerprint: str = Field(description="当前返回内容的摘要；首次保存/重置原样送回，来源变化返回409。")


class ExplorationLinkInput(Contract):
    seed_object_id: UUID = Field(description="E66 matches.seed.id；必须连到当前底图或前序展开告警。")
    candidate_object_id: UUID = Field(description="E66 matches.candidate.id；按实际保存对象版本核对，不要求仍是最新材料。")


class ExplorationSave(Contract):
    operation_key: UUID = Field(description="本次保存幂等键；相同用户/请求重试返回原快照，改请求409。")
    expected_snapshot_id: UUID | None = Field(description="最近读到的保存 ID，首次必须明确 null；并发变化409。")
    base_snapshot_id: UUID | None = Field(default=None, description="继续已存探索时填该快照 ID，固定复制其底图；首次或重置为 null。")
    base_run_id: UUID | None = Field(default=None, description="首次/重置的底图 Run ID；成员图为 null；复制快照时不可填。")
    base_fingerprint: str | None = Field(default=None, pattern="^[0-9a-f]{64}$", description="首次/重置必填 GET 底图指纹；复制快照时不可填。")
    expanded_links: list[ExplorationLinkInput] = Field(description="按展开先后排列的所有保留关系；撤销需去除后续悬空分支。")
    view_state: dict[str, JsonValue] = Field(description="客户端画布位置、选择、隐藏、视角等 JSON，原样保存返回；不当作业务事实或成员。")

    @model_validator(mode="after")
    def base_choice(self):
        if self.base_snapshot_id:
            if self.base_run_id or self.base_fingerprint:
                raise ValueError("snapshot_base_cannot_mix_live_base")
        elif not self.base_fingerprint:
            raise ValueError("base_fingerprint_required")
        keys = [(p.seed_object_id, p.candidate_object_id) for p in self.expanded_links]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate_expansion_link")
        return self


class ExplorationSnapshot(Contract):
    id: UUID = Field(description="不可变探索保存 ID；下一次保存作为 expected_snapshot_id。")
    case_id: UUID = Field(description="所属案件 ID。")
    created_at: datetime = Field(description="数据库保存时间。")
    created_by: UUID = Field(description="实际保存用户 ID。")
    base: ExplorationBase = Field(description="固定的底图内容及来源，新结果不会替换。")
    expanded_links: list[ExplorationMatch] = Field(description="经真实对象核对的共有对象关系；不表示攻击因果。")
    expanded_sources: ExplorationSources = Field(description="展开告警及其匹配材料对象快照；已保存记录继续沿用原内容。")
    view_state: dict[str, JsonValue] = Field(description="客户端保存的展示状态原样返回。")


class ExplorationSaved(Contract):
    snapshot: ExplorationSnapshot | None = Field(description="本案最近一次保存；从未保存时 null，不能伪装成空图。")
