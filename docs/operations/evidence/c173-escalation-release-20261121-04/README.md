# C173 未升级调查正式发布

2026-11-21，21 的 HTTP 18024、Swagger 18080 和联合调度已切换到 `c173-release-20261121-04`。三项服务已核对实际身份与运行配置，Fusion 使用已就绪的 `c173-release-20261121-03` 实例。[发布清单](../../../../deploy/aisoc21/c173-release-20261121-04/release.json)

- PostgreSQL 调查库已备份并核对可列出 Run 表及数据。正式 `aisoc.socai2` 的迁移 135 已登记，新列约束和 Run 收尾写入规则已核对，实际为 35 张表、566 列。
- 正式 HTTP、Swagger 和仓库快照的业务合同一致，共 82 个操作。分析运行目录新增 `statistics.not_escalated_count` 和 `items[].escalation_decision`。
- 正式 `GET /api/v1/socai2/analysis-runs` 及告警完成筛选的计数和卡片与同租户 PostgreSQL 一致。正式租户在验收时没有 Run，未升级计数返回 0，运行卡片列表为空。
- 将正式使用的同一 HTTP 镜像接到隔离库。明确不升级的卡片为 `not_escalated` 且计入统计，无决定的卡片为 `null`。按主体筛选和跨页读回与 PostgreSQL 一致。
- 调度实际加载告警置信门槛 0.85，现行事件结构空白限制为 8 字符，事件输出上限为 8192。旧的三项服务停放，可用于需要时回切。

[正式检查回执](checks.json) · [隔离分诊联验](../c173-not-escalated-20261121-01/README.md) · [后端交接清单](../../../integration/c173-backend-handoff-20261121.md)
