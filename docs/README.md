# 项目文档入口

当前状态以 [PROGRESS](../PROGRESS.md)为准；工作约定见 [AGENTS](../AGENTS.md)。前后端统一从[交接指南](../FRONTEND_BACKEND_HANDOFF.md)进入，不按过程回执选择环境或字段定义。

| 内容 | 入口 |
| --- | --- |
| 当前调查模块 | [调查导航](investigation/README.md) |
| 现行设计与历史边界 | [设计入口](design/README.md)、[11-14旧设计与评审归档](handoff/history/2026-11-14-investigation-cleanup/README.md) |
| 后端联调 | [C173 正式 HTTP 交接](integration/c173-backend-handoff-20261121.md)、[HTTP总指南](../FRONTEND_BACKEND_HANDOFF.md)、[组件/Kafka](integration/component-handoff-current.md)、[测试数据与操作](integration/backend-test-guide.md)、[4173测试页面](integration/test-page-4173.md)、[本地Swagger](../deploy/api-docs/README.md) |
| 对外与内部接口 | [调用分类、代码归属及兼容范围](design/investigation-http-boundary.md)、[独立HTTP部署](../deploy/http-service/README.md) |
| 功能与页面需求 | [产品需求](design/alert-incident-case-product-requirements.md)、[功能与跳转清单](../deliverables/investigation-validation-20261106/frontend-feature-list.md) |
| 表、字段及读取 | [字段字典](design/socai2-field-dictionary-20261103.md)、[数据交接](investigation/socai2-page-data-handoff-20261106.md)、[当前候选OpenAPI](operations/evidence/case-initial-http-20261115-01/candidate-openapi.json)、[Case首轮对接](integration/case-initial-http.md) |
| 模型输入输出 | [按环节的职责与合同](investigation/model-input-output-current-20261109.md) |
| 部署与配置 | [21调查服务手工部署与恢复手册](operations/investigation-manual-deployment-21-20261127.md)、[全模块部署](../deploy/README.md)、[四类配置与逐项索引](operations/configuration.md)、[模型/LiteLLM](operations/deployment-models.md)、[数据湖与数据库](operations/deployment-datastores.md)、[21 部署](../deploy/aisoc21/README.md)、[环境说明](operations/environment.md)、[Mac SSH 接入](operations/mac-ssh-relay-20261107.md) |
| 当前问题 | [问题清单](investigation/current-issues.md)、[实施任务](../openspec/changes/complete-socai2-investigation-chain/tasks.md) |
| 执行与评审证据 | [当前证据导航](operations/evidence/README.md)，历史批次不作为当前运行状态 |
| 需求原件 | [AI SOC2](requirements/AI%20SOC2.docx)，保持原件 |
| 变更流程 | [OpenSpec](../openspec/README.md) |
| 追溯材料 | [历史索引](handoff/history/README.md)、[代码与数据保留清单](handoff/retention-map.md) |

正式设计与非私密证据保存在仓库；私密配置、运行凭据和本机临时材料留在 `.local`。CLI、HTTP 或格式通过仅证明对应检查，不代替业务判断与模型质量验收。

[探索保存恢复 E67–E69](integration/case-exploration-save-http.md)：读取底图、保存固定展开/画布、恢复最近保存；不产生调查或改变成员。

[E70告警相似历史复核](integration/alert-review-http.md)：读取匹配来源及原判定，人工确认后再反馈。

[告警同主机最近7条E71](integration/alert-host-http.md)：匹配规则、输入输出、原件回查及错误。
