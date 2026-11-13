# 调查模块入口

当前状态见 [PROGRESS](../../PROGRESS.md)，前后端接手以[交接指南](../../FRONTEND_BACKEND_HANDOFF.md)为准。21 已部署 A/I 和 Case C1/C3/Deep/C6；当前流程、配置与验收见[流程实测与发布](../../openspec/changes/archive/2026-11-10-align-case-finding-evidence-roles/validation.md)。

| 接手内容 | 资料 |
| --- | --- |
| 当前调查表范围 | [28 表职责／25 表有写入路径](investigation-table-scope.md)、[当前机器字典](../design/socai2-data-contract-current.json)；外部资产等基础数据由业务后端实现 |
| 页面功能与规则 | [逐页功能清单](../../deliverables/investigation-validation-20261106/frontend-feature-list.md)、[规则确认记录](../design/investigation-product-decisions.md)、[产品需求](../design/alert-incident-case-product-requirements.md) |
| 页面字段和跳转 | [F 字段分组／J 跳转附录](../../deliverables/investigation-validation-20261106/frontend-data-navigation-contract.md) |
| HTTP对接主入口 | [125项功能对应接口、输入输出与错误](../../deliverables/investigation-validation-20261106/http-handoff/README.md)；[本机/21 Swagger](../../deploy/api-docs/README.md) |
| 对外与内部接口 | [查询/业务操作与内部调用的边界](../design/investigation-http-boundary.md)；53操作已迁入独立HTTP包，两端18024已发布，原合同保持 |
| 数据及接口 | [数据交接](socai2-page-data-handoff-20261106.md)、[字段字典](../design/socai2-field-dictionary-20261103.md)、[OpenAPI](../design/socai2-independent-api-v2.openapi.json) |
| 程序及模型职责 | [执行账本](current-execution-ledger.md)、[模型输入输出](model-input-output-current-20261109.md) |
| 问题与后续验收 | [问题清单](current-issues.md)、[OpenSpec 任务](../../openspec/changes/complete-socai2-investigation-chain/tasks.md) |
| 采用结果与未完任务 | [采用规则AD01–AD06](result-adoption-and-pending-work.md)及[调用指南](../integration/result-adoption-http.md)；E21/E63/E64已交付，采用不等同任务完成或结案 |
| 实际实现审查 | [调查流程独立审查](investigation-flow-review-20261111.md)：入口、设计合理性、合同偏差、实现真实性及证据限制 |
| 当前交付与下一项 | Case/H、分诊后知识同步、Case管理及告警/事件管理已交付；[HTTP分离](../../openspec/changes/archive/2026-11-13-separate-investigation-http/validation.md)已独审归档。[三类列表查询](../../openspec/changes/archive/2026-11-13-query-investigation-lists/design.md)已完成本机/21及Swagger docs8发布、独审归档；完整CSV导出及E57归并统计也已发布，普通评论E58/E59也已发布，附件引用E60–E62已发布，文件上传/下载由业务后端负责；两端Swagger为docs13；采用预览/提交/判断历史已交付，下一项同案助手，其他接口按[计划](http-implementation-plan-20261112.md)推进。固定调查和模型质量进展见[PROGRESS](../../PROGRESS.md) |
| 21 与本机接入 | [部署](../../deploy/aisoc21/README.md)、[SSH 转发](../operations/mac-ssh-relay-20261107.md) |
| 资料归档与保留 | [历史索引](../handoff/history/README.md)、[代码与数据保留清单](../handoff/retention-map.md) |
| 运行原件及样例 | [工作台与离线材料](../../deliverables/investigation-validation-20261106/README.md)、[本批证据](../operations/evidence/case-evidence-roles-20261110-01/) |

原始需求、各批失败及模型原答均保留。实现、运行交付、数据读取、页面接线和模型质量分别验收；未完成主任务继续保留在主调查 OpenSpec；各独立交付按一个 change 完整验收后发布。

按目标知识的执行位置、字段/索引/配置与 4177 展示见 [Case 知识交接](case-knowledge-handoff.md)。

- [历史告警知识与模型交接](historical-alert-knowledge-handoff.md)：显式卡片入库、C2 历史目标、模型角色与 4177，交付状态以 PROGRESS 为准。
- [知识检索与入库设计](../../openspec/changes/archive/2026-11-12-refine-purpose-aware-knowledge-use/design.md)：用途筛选、按阶段提供去重内容及历史选入／修订时机；一次直接流程及独审后已发布 21 r3，写读与 4177 回执见验收，模型质量保持 NOT_PASSED。

- [分诊保存后同步历史知识](../../openspec/changes/archive/2026-11-12-sync-saved-alert-knowledge/proposal.md)：已完成本地直接流程、独审及 21 r5 加载读回；新 A 分诊提交并采用后按配置维护卡片／索引，不启用全链消费者，人工反馈保持显式入口。
