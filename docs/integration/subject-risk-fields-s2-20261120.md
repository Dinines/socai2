# S2：每轮等级意见与自动上调

2026-11-20，候选实现；验证状态以[本批回执](../operations/evidence/subject-risk-s2-20261120-01/README.md)为准。依赖[S1创建与读取](subject-risk-fields-s1-20261120.md)，复用增量132已有列和工件/活动，不增加数据库迁移、HTTP操作或告警交接字段。正式核心/18024/18080仍未发布本候选。

I/C6 在原有调用中新增独立 `severity_opinion`，结构为 `level`、`reason`、`impact_basis.confirmed/potential`、`source_refs` 和 `limitations`。`level` 为五档安全影响等级；待复核不免除本轮意见，未知/失败/查空也不能直接判低风险。`source_refs` 是该请求可见来源的别名；程序恢复真实引用、绑定主体、Run及冻结成员/材料。该单元有独立版本 `socai2.severity-opinion.v1`，新请求要求它，历史原答/旧分析合同不改写。

## 当前值与本轮意见

| 字段 | 读取含义 |
| --- | --- |
| Case `severity`、Incident `derived.severity_effective` | 持久当前等级，列表、详情、过滤、统计和导出同源；Incident `severity_auto`仍只表示来源成员汇总 |
| `risk.current` | 当前等级的来源、更新时间及原因；由模型上调时 `source=model`、`reason_code=model_raise`，`opinion`指向真正生效的意见 |
| `risk.latest_opinion` | 最近已处理轮次的意见链接及处理原因；`level=null`表示该轮没有可用等级，不能当作初值/旧值的模型重述 |
| `risk.system_priority` | 依据当前生效等级及本轮冻结配置保存的系统建议；适用的同值/降低意见也按当前等级计算，不按建议降低值计算 |
| `risk.priority_override` | 已有人工或来源未明的历史优先级保存值；有覆盖时系统建议可变化，当前`priority_value`保持，含0 |
| `risk.initial` | 创建/首次明确分析写操作时的规则初值和成员材料，不随后轮意见改写 |

`RiskOpinionLink` 含 `run_id/artifact_id/application_artifact_id/started_at/processed_at/level/reason_code`。沿既有同主体/同Run工件详情入口读取这两个工件，不能按当前latest替代指定轮次。旧行GET不初始化；旧主体首次新分析写操作保留已有人工等级、优先级及未知来源，不伪造历史模型意见。

`risk.policy`保留创建/首次初始化策略。本轮完整策略保存在`severity_opinion_input.policy`，`system_priority.mapping_version`标明本次实际计算版本。新直接I输入以`risk_input_version`冻结比较合同：保存等级、风险台账和优先级不会使自己的诊断立即过期，真正业务输入/材料变化仍判stale；旧无标记Run保持原比较和原结论。

| `reason_code` | 生效处理 |
| --- | --- |
| `raised` | 新适用意见高于当前等级，自动上调 |
| `lower_not_applied` | 保存降低建议，当前等级保持；普通业务提示，不是程序错误 |
| `unchanged` | 同值意见保存，不新增等级变更活动 |
| `manual_revision_changed` | Run开始后人工修订变化，当前值保持；后续新轮仍可上调人工值 |
| `frozen_scope_changed` / `local_scope_only` / `scope_unavailable` | 成员/材料或Case范围不适用，不改全主体当前等级 |
| `input_changed` / `newer_round_exists` | 输入已过期或更晚轮次已开始，不应用旧意见 |
| `execution_unconfirmed` | unknown或尚无可应用终态，只留候选 |
| `opinion_missing_or_invalid` | 没有结构完整的等级单元，保留原答和其他有效分析 |

## 工件、幂等与状态

同一Run的 `source_snapshot` 工件新增三种`type`：`severity_opinion_input`保存后台人工修订号、策略及冻结范围；`severity_opinion_candidate`保存原答单元、字符位置/hash、已还原引用、引用质量及缺项；`severity_opinion_application`保存处理原因、前后值和实际人工版本。原答全文仍沿原工件存取；候选的`unit.value`是模型原值，`unit.resolved_refs`来自已存请求的来源映射，未知引用不会被编造为真实证据。

等级单元与普通结论分开接收。截断中已闭合完整单元可保留，纯引用质量问题独立记录；缺等级时合法正文继续保存。仅有等级不能据此宣称诊断完整、Case Result可采用或Run正常完成；原有拒收/部分结果仍按实际状态保存。整轮unknown即使有完整单元也不会自动应用。处理回执、当前值、系统优先级和等级活动在同一事务保存；同一意见重放返回原处理，不重复写当前值或重复活动。

自动上调和降低建议分别写入 `severity_raised`、`severity_lower_suggested` 活动，保存真实来源链接及前后值。S2当步未验人工入口；后续[S3候选](subject-risk-fields-s3-20261120.md)已完成其真实管理写读与受控联动。S4时间线/4173/4177交互和S7真实模型仍为后续范围，不能由S2/S3局部验证追认完成。
