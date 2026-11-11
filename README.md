# socai2 · stingAISOC

[前后端交接指南](FRONTEND_BACKEND_HANDOFF.md)是功能、数据库、字段对应与接口的统一入口。当前服务端流程包括告警分诊、事件诊断、Case 调查及其保存和读取；21 已部署当前 A/I/Case 输入输出与读取代码。

调查数据库为 `aisoc.socai2`，29 表、462 列。字段和实际读取核验通过，模型正文质量仍未通过；生产 Case HTTP 写开关关闭，自动消费者暂停。实际部署、证据和下一步见 [PROGRESS.md](PROGRESS.md)。

| 内容 | 入口 |
| --- | --- |
| 工作规则及变更 | [AGENTS](AGENTS.md)、[OpenSpec](openspec/README.md)、[当前任务](openspec/changes/complete-socai2-investigation-chain/tasks.md) |
| 功能与字段 | [产品需求](docs/design/alert-incident-case-product-requirements.md)、[功能清单](deliverables/investigation-validation-20261106/frontend-feature-list.md)、[字段字典](docs/design/socai2-field-dictionary-20261103.md) |
| 流程和问题 | [调查入口](docs/investigation/README.md)、[执行账本](docs/investigation/current-execution-ledger.md)、[问题清单](docs/investigation/current-issues.md) |
| 运行与查阅 | [21 部署](deploy/aisoc21/README.md)、[SSH 接入](docs/operations/mac-ssh-relay-20261107.md)、[4177 运行记录](deliverables/investigation-validation-20261106/README.md#调查运行记录页) |
| 资料与证据 | [文档导航](docs/README.md)、[本批流程实测](openspec/changes/complete-socai2-investigation-chain/case-current-flow-20261110.md)、[归档索引](docs/handoff/history/README.md)、[代码与数据保留清单](docs/handoff/retention-map.md) |

告警相关的前后端交接字段保持稳定，确需调整时先列明影响并确认；必要读写接线与配置随功能处理。数据库迁移保留冻结建表原件及既有数据。所有可变运行配置由显式 profile 提供，凭据留在受控且忽略提交的文件。

参考工程为 `beenuar/AiSOC` 固定 revision `34ca18c57dd4175539e5c6dd3d04a72dc057306b`，本机参考目录保持只读。当前任务不自动扩展到采集、原始检测或整个平台。
