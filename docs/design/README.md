# 当前设计与合同入口

当前功能从[调查导航](../investigation/README.md)和[交接指南](../../FRONTEND_BACKEND_HANDOFF.md)进入。设计目标、当前实现和历史验收分别查阅，不按文件名中的“最新”“当前”判断实际版本。

| 内容 | 权威入口 |
| --- | --- |
| 调查流程与模型职责 | [主调查设计](../../openspec/changes/complete-socai2-investigation-chain/design.md)、[按环节输入设计](../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md) |
| 更新、队列与反馈 | [流式设计](../../openspec/changes/schedule-streaming-investigation-updates/design.md)，尚未实施 |
| 产品与确认规则 | [产品需求](alert-incident-case-product-requirements.md)、[D01–D07](investigation-product-decisions.md)、[功能清单](../../deliverables/investigation-validation-20261106/frontend-feature-list.md) |
| 数据与接口 | [当前字典](socai2-data-contract-current.json)、[数据交接](../investigation/socai2-page-data-handoff-20261106.md)、[OpenAPI](socai2-independent-api-v2.openapi.json)、[接口边界](investigation-http-boundary.md) |
| 冻结原件 | [V1字段字典](socai2-field-dictionary-20261103.md)和迁移123–126保持；当前增量结构见[数据库入口](../../deploy/database/CURRENT.md) |
| 当前问题 | [11-14评审](../investigation/investigation-current-review-20261114.md)、[问题清单](../investigation/current-issues.md) |
| 旧设计及评审 | [11-14归档](../handoff/history/2026-11-14-investigation-cleanup/README.md)及[历史索引](../handoff/history/README.md) |

部分早期文档仍由历史生成/核验脚本引用，因此保留原路径供兼容；具体引用方见归档manifest的`protected`。它们不作为当前设计或部署入口，旧失败和未完成要求继续保留。
