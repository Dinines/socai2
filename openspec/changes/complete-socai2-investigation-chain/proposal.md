## Why

新页面要求区分告警基本查询/分诊（A）、事件诊断（I）、完整基础调查（C）、人工确认（H）和AI问答（Q）。新socai2表及部分读写/执行组件已有实现和分批回执，但仍缺A/I实际执行、完整页面数据出口和部分关系/人工来源接线；需要在同一开发分支用OpenSpec明确剩余交付。

## What Changes

- 承接已有新表、Fusion写入、C1–C6、Case API及A/I存储/读取，以原回执说明已完成范围；不重跑原批次或将替身验证当作真实质量验收。
- 补A/I实际执行及模型/查询请求、返回、步骤和用量；完善页面字段出口、显式事件Case关系、人工结果与必要外部来源。
- 保留完整C手动启动、同Case单活跃、领取前合并pending/领取后冻结、有效基础结果自动采用等已确认合同。
- 按用户最新决定，Q具体实现暂缓，仅预留HTTP及类型合同。发送、保存和采用接口明确返回501；不产生业务数据或调用模型/Tool。
- 在主目录`E:/aisoc/socai2`的`codex/case-baseline-history-20261103`直接开发；源码、最新设计和本地页面预览统一维护。
- 按2026-11-04最新要求单开新API服务，使用现有PG/CH实例上的独立空间、独立端口和真实身份；原服务、旧业务数据及Kafka消费者保持。以新合成材料完成真实模型验收。

本change规格是目标合同；完成事实以tasks和对应回执为准。页面交互、Fusion接收前的输入问题、Q业务执行、旧r13报告修复与自动任务领取不在本change实施范围。

## Capabilities

### New Capabilities

- `socai2-investigation-data`: 新命名空间的A/I/C/H职责、来源/范围/结果及页面读取支撑。
- `socai2-case-ai-reservation`: 暂缓AI问答的三个预留入口及明确未实现、无业务副作用的合同。

### Modified Capabilities

无。现有`alert-investigation-integrity`是旧迁移及旧自动调查链的合同；本change新增独立socai2路径，不改变旧自动链和历史验收含义，不修改归档change。

## Impact

- `services/fusion/app/services/socai2_*`、`services/api/app/socai2/`、新API/测试与既有迁移123；本次目录迁移和Q预留不新增表/列/枚举。
- [最新主设计](../../../docs/architecture/investigation-planning-design.md)、[字段字典](../../../docs/design/socai2-field-dictionary-20261103.md)、[交接](../../../docs/design/socai2-schema-implementation-20261103.md)为需求和字段依据。
- 原123的29表458列保持；增量124增加Case固定来源命名空间，当前29表459列已在现有独立PG验证库中验证。环境未提供不猜测。生产和页面尚未切换，Case/analysis API默认关闭，Fusion默认public保持。
- 后续只补受影响的直接验证，不引入记忆平台、自动恢复或临时基础设施容器。独立应用服务部署已获授权，不替换原版；不提交或推送。旧r13仍暂停、5.3未完成。
