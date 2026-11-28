# S3：人工等级与优先级管理

2026-11-20，候选已通过真实隔离PG/TCP及限定独立复核，见[本批回执](../operations/evidence/subject-risk-s3-20261120-01/README.md)与[同版OpenAPI](../operations/evidence/subject-risk-s3-20261120-01/candidate-openapi.json)。沿用[S1创建读取](subject-risk-fields-s1-20261120.md)和[S2意见应用](subject-risk-fields-s2-20261120.md)，正式18024/18080尚未更新；告警管理、告警来源等级和分诊字段保持。

使用现有三个入口：`PATCH /api/v1/socai2/cases/{case_id}/management`、`PATCH /api/v1/socai2/incidents/{incident_id}/management`、`POST /api/v1/socai2/incidents/management-batch`。Case用`case.row_version`，事件用`facts.row_version`；每次明确操作带`operation_key`和`expected_row_version`，批量在`items[]`带各自版本、`changes`带共同修改。

| 操作 | Case请求 | Incident请求 | 结果 |
| --- | --- | --- | --- |
| 人工升降或同级确认 | `severity`及非空`severity_reason` | `severity_override`及非空`severity_override_reason` | 写入持久当前等级、人工来源/理由/操作者/时间，人工修订递增；之后新轮仍可自动上调 |
| 恢复成员规则等级 | 不提供清空等级操作，`severity=null`返回422 | `severity_override=null`且必填非空`severity_override_reason` | 以当前成员来源最高等级恢复，全部未知按配置初值；保留恢复理由及当时成员/材料依据 |
| 人工优先级 | `priority_value`及非空`priority_reason` | 同Case | 数值0–100，最多两位小数；当前人工值与系统建议分存 |
| 撤销优先级覆盖 | `clear_priority_override=true`及非空`priority_reason` | 同Case | 恢复本次配置与当前等级对应的系统值，不使用创建时旧值 |

省略字段保持原值；`clear_priority_override=false`不撤销。优先级不接受null、布尔、字符串、越界或超过两位小数；设置和撤销不能同时提交，理由不能单独提交。多个操作可以同一请求提交，各自理由分别保存。Incident旧客户端无理由null撤销现在明确422；Case旧null清空也明确422。这两项必须与新版OpenAPI同时交接，旧服务行为不能套用候选请求。

人工等级操作会更新`risk.current`，新增`reason`与可选`rule_basis`，原因码为`manual_set`或`manual_rule_restore`；显式人工决策不再指向旧自动生效意见，但`risk.latest_opinion`和旧Run工件保持。恢复成员规则时`rule_basis`保留本次来源等级/成员材料，`risk.initial`与创建`risk.policy`不变。事件旧`severity_override*`列继续保存最近人工设置；它不是永久阻止新轮上调的锁。null恢复后这些旧列清空，恢复理由仍在`risk.current`及活动中。

`risk.system_priority`保存当前等级对应的建议和映射版本。有`risk.priority_override`时，模型上调仅改变系统建议，生效`priority_value`仍为人工值（包括0）；撤销后`priority_source=severity_mapping`。等级调整和优先级设置/撤销按显式profile重新计算系统映射；GET不写库。旧主体首次明确管理写操作在同一事务建立风险状态并保留已有人工值，新的人工调整再按请求处理。

同键同意图重试返回原保存回执，不再次推进版本、生成活动或覆盖后来修改；同键不同意图和旧版本返回409。一次成功管理最多推进一次主体行版本。事件批量是整批成功或整批拒绝：任一版本冲突时全部不改，成功才返回各项回执。未确认执行结果时先读回，沿原幂等键确认，不自动换键重派。

修改与活动同事务保存。Case从`/cases/{case_id}/activities`、事件从`/incidents/{incident_id}/records/activities`读操作者、时间、理由及目标前后值；`detail.notes`保持原字符串数组，混合理由另保存在操作回执的`risk_reasons`中。管理回执是当时快照，之后状态用独立GET；列表、详情、过滤、统计及导出沿同一持久值。

S3验收只覆盖后端请求、保存、读取及与S2的受控联动；页面按钮/时间线交互归S4。S3不新增模型调用、队列调度或审批环节，真实模型整链与正式发布按后续change验收。
