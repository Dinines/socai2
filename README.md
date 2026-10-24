# socai2 · stingAISOC

以固定上游 [beenuar/AiSOC](https://github.com/beenuar/AiSOC) revision `34ca18c57dd4175539e5c6dd3d04a72dc057306b` 为参考，交付已有告警及后续调查的服务端：Kafka输入、Fusion、分诊、按策略自动关闭或自动升级调查、人工调查，以及API/持久化结果和Markdown报告。前端、采集和原始事件检测不在本轮迁移范围。

**2026-10-24：按用户安排收尾已选范围的迁移基线。** [收尾回执与后续规划](docs/operations/migration-closeout-20261024.md)记录交付证据、原15项责任核销、版本和未解决项。测试背景事件入湖及调查闭环由单独开发的调查模块承接，本会话不再重复测试。后续工作先规划、再讨论，不因本文自动开工。

已发布v1的回执记录：API `5a1e1fd8`、Agents `49643b84`、Fusion `c52b9aac`；独立生产租户的Kafka自动分诊和自动升级已开启，有自动关闭/实际调查/结果和Markdown读取实证。**调查存在partial及质量失败，迁移收尾不等于完整产品或自治质量验收。** 本次未重新检查生产运行态；生产接入及版本以[发布记录](docs/operations/service-v1-release-20261022.md)和[对接指引](docs/integration/v1/production.md)为准。

10月23日的前置校验、逐工具留存和停止交接小修已有本地验证，当时未部署；不能当作线上v1能力。旧失败、unknown、预算、积压和权限保护保留，真实厂商动作未开启。本轮没有修改运行配置、部署或Git提交/推送。

| 入口 | 用途 |
| --- | --- |
| [工作约定](AGENTS.md)、[进度](PROGRESS.md) | 最新授权、收尾状态及历史阶段记录 |
| [收尾及后续规划](docs/operations/migration-closeout-20261024.md) | 已交付范围、原任务核销、证据/版本、承接分工和待讨论工作 |
| [文档导航](docs/README.md) | 源码理解、功能、架构与证据入口 |
| [服务端职责](docs/operations/alert-processing-scope.md)、[六阶段路线](docs/operations/service-roadmap.md)、[原执行计划](docs/operations/completion-plan.md) | 迁移范围、历史实施路线与10月24日收尾说明 |
| [后端对接](docs/integration/v1/README.md)、[生产接入](docs/integration/v1/production.md) | 正式Kafka、查询API、结果读取和受控凭据交接 |
| [数据库字段字典](docs/integration/v1/table-fields.md)、[页面信息建议](docs/integration/v1/page-elements.md)、[取数附件](docs/integration/v1/page-data-mapping.md) | 25表428字段盘点、四页90项建议、SQL/HTTP及空态/缺口 |
| [测试数据工具](tools/testdata/README.md)、[实测回执](docs/operations/testdata-migration-execution-20261023.md) | 场景生成、答案分离、Kafka有界投放和持久观察 |
| [功能对照](docs/operations/alert-function-alignment.md)、[架构](docs/architecture/alert-processing.md)、[问题登记](docs/operations/upstream-issues.md) | 固定版本声明/实现、服务职责、既有缺口与延期项 |
| [独立调查规划](docs/architecture/investigation-planning-design.md) | 原M0—M9设计参考；实现及入湖验证由独立工作记录，不在迁移中重做 |
| [OpenSpec说明](openspec/README.md) | 已归档迁移规格、历史审计及新变更流程；旧R02仍暂缓 |
| [21部署说明](deploy/aisoc21/README.md)、[配置索引](docs/operations/configuration.md)、[full配套](docs/operations/full-support-migration.md) | 复用存储、实际版本及完整叠加配置，秘密仅存受控位置 |
| [需求](docs/requirements/README.md)、[既有分析](docs/anal/README.md)、[参考模块](docs/reference/aisoc/01-system-map.md) | 产品需求及源码理解，不能据文档声明追认已实现 |

固定参考源码 `/Users/lychee/Documents/project/SOCAI/opensource/AiSOC` 只读保留，不在其中修改；本项目仓库为 [Dinines/socai2](https://github.com/Dinines/socai2)。已有来源、测试和历史失败回执直接复用，不因收尾重跑全量模型或基础设施矩阵。
