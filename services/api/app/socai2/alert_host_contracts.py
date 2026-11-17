"""Same-host recent alerts, independent of human-review similarity rules."""
from datetime import datetime
from uuid import UUID

from pydantic import Field

from .baseline_contracts import Contract
from .exploration_contracts import ExplorationObject
from .page_contracts import AlertFacts


class AlertHostMatch(Contract):
    seed: ExplorationObject = Field(description="起点最新材料中的主机对象，保留ID、namespace、原值/规范值和字段路径；algorithm为null。")
    candidate: ExplorationObject = Field(description="候选最新材料中与起点namespace及规范主机值完全相同的主机对象；沿材料ID用E31回查。")


class AlertHostItem(Contract):
    alert: AlertFacts = Field(description="原告警事实，含名称、等级、真实发生时间、处理状态和判定；点击alert.id用E28打开。")
    matches: list[AlertHostMatch] = Field(description="全部同主机对象对，按起点/候选对象ID排序；不要求战术一致，不代表攻击因果。")


class AlertHostPage(Contract):
    items: list[AlertHostItem] = Field(description="去重后按event_time倒序、alert.id倒序的最近记录；排除起点及发生时间未知的候选。")
    total: int = Field(ge=0, description="完整匹配范围的去重告警数，不受本次返回上限影响。")
    limit: int = Field(ge=1, le=100, description="本次配置的返回条数上限，当前7；7是条数，不是天数，无分页参数。")
    source_alert_id: UUID = Field(description="当前查看的起点告警ID；它自身不在items中。")
    source_material_id: UUID | None = Field(description="实际读取的起点latest_material_id，没有材料时null。")
    source_namespace: str = Field(description="告警来源范围，候选必须相同；主机对象namespace另逐对核对。")
    source_hosts: list[ExplorationObject] = Field(description="起点最新材料内非空的host对象；多个主机取并集，不从IP/资产ID推断。空列表时items为空。")
    observed_at: datetime = Field(description="本次数据库只读一致快照时间。查询已保存的最新发生记录，不限定在起点之前或最近若干天。")
