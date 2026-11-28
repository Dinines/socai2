# 事件/Case 严重程度和优先级：S1 候选交接

2026-11-20。创建初值与统一读取已实现并在独立合成 PostgreSQL、真实 TCP HTTP 验证；正式 18024/18080 尚未更新。完整候选 [OpenAPI](../operations/evidence/subject-risk-s1-20261120-01/candidate-openapi.json) 含 82 操作，新增的是事件/Case 返回字段，本步不增加业务路径。现有告警字段及告警分诊合同不变。

| 前端要展示的内容 | 事件接口 | Case 接口 | 含义 |
| --- | --- | --- | --- |
| 当前严重程度 | `derived.severity_effective` | `case.severity` | 持久保存的当前值，列表、详情、筛选、排序、统计和导出同源 |
| 当前严重程度来源 | `derived.severity_source` | `case.severity_source` | 创建时为 `member_max` 或 `initial_policy`；Case 创建人工指定时为 `manual` |
| 当前优先级 | `facts.priority_value/state/source/basis` | `case.priority_value/state/source/basis` | 沿原字段，系统映射值为 10/30/50/75/95；无需前端重新计算 |
| 完整创建依据 | `facts.risk` | `case.risk` | 同一 `SubjectRisk` 结构，旧记录未建立状态为 null |
| 成员来源最高等级 | `derived.severity_auto` | `risk.initial.level` 是创建快照，非动态汇总 | 事件 auto 是当前成员来源汇总，可能与生效等级不同，不能代替生效值 |

`risk` 的关键内容：

- `initial.level/source/reason_code/evaluated_at`：当时按实际成员计算的初值；`members` 保留告警 ID、材料 ID/版本及来源等级，供追溯。全部未知为 `initial_policy/source_severity_missing`，页面可显示“规则初值，待分析”，不可标为模型已判定。
- `current.level/source/reason_code/updated_at/actor_id`：创建时生效等级及来源。人工创建指定等级时保留操作者、请求来源，同时保留系统算出的 initial。
- `system_priority.value/severity/mapping_version/computed_at`：对应当前等级的系统建议及保存版本。`policy` 是当时配置快照；配置修改不经 GET 改写旧记录。
- `manual_severity_revision`：后台人工版本，供后续并发保护；不作为业务分析正文。

规则例子：成员为低、高时，新案为高 / 75；全部未知为中 / 50，明确规则初值；来源为严重但创建请求人工选择低时，当前低 / 30，系统创建初值仍可追溯为严重。按容量产生的续案按自己实际分配到的成员计算，不继承上一案等级。

事件列表继续调用 `GET /api/v1/socai2/incidents`，详情和筛选参数不变；Case 沿原列表/详情。CSV 可显式选择 `facts.priority_value/facts.risk` 或 `case.priority_value/case.risk`。旧行保持原查询兼容：事件沿已有人工覆盖/成员派生读取，Case 原空值仍空；GET 不初始化、不回填历史。

S1当步范围不含后轮意见和人工管理。后续[S2候选交接](subject-risk-fields-s2-20261120.md)已补 I/C6 独立等级意见、自动只升不降及保护回执；[S3候选](subject-risk-fields-s3-20261120.md)已补人工修改/撤销优先级覆盖并验存取，等级时间线及任务时间展示另按S4/S5。S1–S3候选不能单独发布为完整产品功能。前端当前线上仍按正式 Swagger 调用，待统一发布时使用同版候选合同。

验证见[实际回执](../operations/evidence/subject-risk-s1-20261120-01/README.md)。不把 HTTP 验证当作 SpiritHub 页面验收，4173/4177 尚未改动。
