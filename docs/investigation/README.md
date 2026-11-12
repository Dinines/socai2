# 调查模块入口

当前状态见 [PROGRESS](../../PROGRESS.md)，前后端接手以[交接指南](../../FRONTEND_BACKEND_HANDOFF.md)为准。21 已部署 A/I 和 Case C1/C3/Deep/C6；当前流程、配置与验收见[流程实测与发布](../../openspec/changes/archive/2026-11-10-align-case-finding-evidence-roles/validation.md)。

| 接手内容 | 资料 |
| --- | --- |
| 页面功能和跳转 | [产品需求](../design/alert-incident-case-product-requirements.md)、[功能清单](../../deliverables/investigation-validation-20261106/frontend-feature-list.md) |
| 数据及接口 | [数据交接](socai2-page-data-handoff-20261106.md)、[字段字典](../design/socai2-field-dictionary-20261103.md)、[OpenAPI](../design/socai2-independent-api-v2.openapi.json) |
| 程序及模型职责 | [执行账本](current-execution-ledger.md)、[模型输入输出](model-input-output-current-20261109.md) |
| 问题与后续验收 | [问题清单](current-issues.md)、[OpenSpec 任务](../../openspec/changes/complete-socai2-investigation-chain/tasks.md) |
| 实际实现审查 | [调查流程独立审查](investigation-flow-review-20261111.md)：入口、设计合理性、合同偏差、实现真实性及证据限制 |
| 当前交付与下一项 | [Case 程序事实与补查约束](../../openspec/changes/archive/2026-11-11-ground-case-conclusions/tasks.md)已完成限定程序交付，模型问题后置；接着按[主路线](../../openspec/changes/complete-socai2-investigation-chain/design.md#下一项具体落点)推进 Case/H 正常操作 |
| 21 与本机接入 | [部署](../../deploy/aisoc21/README.md)、[SSH 转发](../operations/mac-ssh-relay-20261107.md) |
| 资料归档与保留 | [历史索引](../handoff/history/README.md)、[代码与数据保留清单](../handoff/retention-map.md) |
| 运行原件及样例 | [工作台与离线材料](../../deliverables/investigation-validation-20261106/README.md)、[本批证据](../operations/evidence/case-evidence-roles-20261110-01/) |

原始需求、各批失败及模型原答均保留。实现、运行交付、数据读取、页面接线和模型质量分别验收；未完成主任务继续保留在主调查 OpenSpec；各独立交付按一个 change 完整验收后发布。

按目标知识的执行位置、字段/索引/配置与 4177 展示见 [Case 知识交接](case-knowledge-handoff.md)。

- [历史告警知识与模型交接](historical-alert-knowledge-handoff.md)：显式卡片入库、C2 历史目标、模型角色与 4177，交付状态以 PROGRESS 为准。
- [知识检索与入库设计](../../openspec/changes/archive/2026-11-12-refine-purpose-aware-knowledge-use/design.md)：用途筛选、按阶段提供去重内容及历史选入／修订时机；一次直接流程及独审后已发布 21 r3，写读与 4177 回执见验收，模型质量保持 NOT_PASSED。
