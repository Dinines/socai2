# Why

事件列表F06-06展示处理中事件与队列压缩；现有E26/E27整体统计的范围和观察时刻不同，不能组合计算可信的归并比例。按已确认后续计划补独立只读统计，不修改原列表合同。

# What Changes

新增E57 GET `/api/v1/socai2/incidents/grouping-summary`，按告警发生时间和来源命名空间选取一个范围，在同一只读快照返回告警总数、已归并/未归并告警、相关事件数、其中处理中事件数和已归并成员的压缩比例。对外HTTP与内部核心分开，无数据库迁移或模型调用。

# Capabilities

## New Capabilities
- `incident-grouping-summary`: 同范围事件归并统计与明确比例含义。

## Modified Capabilities
- 无。原56操作和JSON字段/枚举/关联保持。

# Impact

新增核心查询/DTO、独立HTTP路由和装配、直接测试、Swagger与125功能清单F06-06。仅本机/21独立18024与Swagger18080发布；其他服务、页面、模型和消费者保持。业务验收与独审后一次发布，按本轮继续推进授权统一Git/父项目同步。
