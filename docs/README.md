# 项目文档入口

当前状态以 [PROGRESS](../PROGRESS.md)为准；工作约定见 [AGENTS](../AGENTS.md)。前后端统一从[交接指南](../FRONTEND_BACKEND_HANDOFF.md)进入，不按过程回执选择环境或字段定义。

| 内容 | 入口 |
| --- | --- |
| 当前调查模块 | [调查导航](investigation/README.md) |
| 后端联调 | [HTTP总指南](../FRONTEND_BACKEND_HANDOFF.md)、[组件/Kafka](integration/component-handoff-current.md)、[测试数据与操作](integration/backend-test-guide.md)、[4173测试页面](integration/test-page-4173.md)、[本地Swagger](../deploy/api-docs/README.md) |
| 对外与内部接口 | [调用分类、代码归属及兼容范围](design/investigation-http-boundary.md)、[独立HTTP部署](../deploy/http-service/README.md) |
| 功能与页面需求 | [产品需求](design/alert-incident-case-product-requirements.md)、[功能与跳转清单](../deliverables/investigation-validation-20261106/frontend-feature-list.md) |
| 表、字段及读取 | [字段字典](design/socai2-field-dictionary-20261103.md)、[数据交接](investigation/socai2-page-data-handoff-20261106.md)、[OpenAPI](design/socai2-independent-api-v2.openapi.json) |
| 模型输入输出 | [按环节的职责与合同](investigation/model-input-output-current-20261109.md) |
| 部署与配置 | [21 部署](../deploy/aisoc21/README.md)、[配置索引](operations/configuration.md)、[环境说明](operations/environment.md)、[Mac SSH 接入](operations/mac-ssh-relay-20261107.md) |
| 当前问题 | [问题清单](investigation/current-issues.md)、[实施任务](../openspec/changes/complete-socai2-investigation-chain/tasks.md) |
| 需求原件 | [AI SOC2](requirements/AI%20SOC2.docx)，保持原件 |
| 变更流程 | [OpenSpec](../openspec/README.md) |
| 追溯材料 | [历史索引](handoff/history/README.md)、[代码与数据保留清单](handoff/retention-map.md) |

正式设计与非私密证据保存在仓库；私密配置、运行凭据和本机临时材料留在 `.local`。CLI、HTTP 或格式通过仅证明对应检查，不代替业务判断与模型质量验收。
