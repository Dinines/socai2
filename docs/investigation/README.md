# 调查模块入口

当前状态以[PROGRESS](../../PROGRESS.md)为准，业务后端和前端从[交接指南](../../FRONTEND_BACKEND_HANDOFF.md)进入。这里维护现行功能、合同、问题和证据入口，旧版本设计与执行流水集中到[历史归档](../handoff/history/README.md)。

| 内容 | 当前入口 |
| --- | --- |
| 本轮评审与问题 | [11-14功能与整体流程评审](investigation-current-review-20261114.md)、[问题清单](current-issues.md)；含RV12告警/事件结论展示缺陷，尚未修复 |
| 后续实施阶段 | [11-14六阶段规划](investigation-implementation-plan-20261114.md)：各阶段目标、解决问题、交付物、依赖和通过条件；阶段2–5对应同一个流式change，正文质量继续后置 |
| 可复用完整测试 | [环境准备与全流程规划](../../openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md)、[告警和上下文设计](../../openspec/changes/schedule-streaming-investigation-updates/test-data-design-20261115.md)、[模块/HTTP依赖](../../openspec/changes/schedule-streaming-investigation-updates/test-interface-readiness-20261115.md)、[独立测试服务与4177 HTTP取数](../../openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md)；各步范围见[当前进度](../../PROGRESS.md)；W5实际4177已接入，历史测试数据已清空，新材料仅离线核对 |
| 调查设计与任务 | [主调查设计](../../openspec/changes/complete-socai2-investigation-chain/design.md)、[31/41任务](../../openspec/changes/complete-socai2-investigation-chain/tasks.md)、[流式更新方案](../../openspec/changes/schedule-streaming-investigation-updates/design.md) |
| 程序与模型职责 | [执行账本](current-execution-ledger.md)、[模型输入输出](model-input-output-current-20261109.md)、[按环节字段设计](../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md) |
| 表与字段 | [28表职责](investigation-table-scope.md)、[当前机器字典](../design/socai2-data-contract-current.json)、[数据交接](socai2-page-data-handoff-20261106.md)、[冻结V1字典](../design/socai2-field-dictionary-20261103.md) |
| 产品规则 | [125项功能清单](../../deliverables/investigation-validation-20261106/frontend-feature-list.md)、[已确认规则](../design/investigation-product-decisions.md)、[产品需求](../design/alert-incident-case-product-requirements.md)、[字段/跳转附录](../../deliverables/investigation-validation-20261106/frontend-data-navigation-contract.md) |
| HTTP交接 | [71操作交接包](../../deliverables/investigation-validation-20261106/http-handoff/README.md)、[OpenAPI](../design/socai2-independent-api-v2.openapi.json)、[对外/内部边界](../design/investigation-http-boundary.md)、[实施计划](http-implementation-plan-20261112.md) |
| 知识与采用 | [Case知识](case-knowledge-handoff.md)、[历史告警知识](historical-alert-knowledge-handoff.md)、[采用规则AD01–AD06](result-adoption-and-pending-work.md)、[采用HTTP](../integration/result-adoption-http.md) |
| 最新调查原件 | [11-14三案](../operations/evidence/fixed-investigation-20261114-01/README.md)、[4177模式回执](../operations/evidence/workbench-display-fix-20261114-01/README.md)、[证据导航](../operations/evidence/README.md) |
| 当前发布依据 | [核心固定功能版](../operations/evidence/fixed-investigation-release-20261113-01/README.md)、[独立HTTP同步](../operations/evidence/investigation-http-sync-20261113-01/README.md)；发布基线与最新展示分别查看 |
| 部署和本机接入 | [21部署](../../deploy/aisoc21/README.md)、[SSH转发](../operations/mac-ssh-relay-20261107.md)、[配置索引](../operations/configuration.md) |
| 历史与保留 | [11-14归档及路径映射](../handoff/history/2026-11-14-investigation-cleanup/README.md)、[代码与数据保留清单](../handoff/retention-map.md) |

Case/告警/事件管理、评论、附件引用、列表/CSV、归并统计、采用、故事、候选、探索保存和相似/同主机查询已交付；实际操作和字段以HTTP交接为准。各页面AI对话暂缓，E19/E20仍501；流式任务/调度和[第3步新告警自动分诊](../operations/evidence/analysis-alert-auto-20261115-01/README.md)已本地验收，I/Case自动更新与反馈的已验边界见当前PROGRESS，当前消费者停止。程序交付、业务结论、采用、页面接线与模型质量分别验收，原失败及NOT_PASSED保留。
