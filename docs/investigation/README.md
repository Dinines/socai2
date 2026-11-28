# 调查模块入口

当前状态以[PROGRESS](../../PROGRESS.md)为准，业务后端和前端从[交接指南](../../FRONTEND_BACKEND_HANDOFF.md)进入。这里维护现行功能、合同、问题和证据入口，旧版本设计与执行流水集中到[历史归档](../handoff/history/README.md)。

| 内容 | 当前入口 |
| --- | --- |
| 当前工作清单与推进顺序 | [主调查任务执行视图](../../openspec/changes/complete-socai2-investigation-chain/tasks.md#当前范围与顺序)：已完成/未实施/待交付分开，列责任、依赖和直接完成判据；湖3a–3f隔离存取链已验，4a规则实现与只读验证也已通过，下一步4b接收存取；来源身份语义待确认，其他原任务和后置项保持 |
| 独立接入与交付审计 | [11-19 审计](../../openspec/changes/complete-socai2-investigation-chain/independent-integration-audit-20261119.md)：SpiritHub 消息/接口、真实日志落湖与调查取证、字段职责、IA01–IA11及双方沟通/逐步验收顺序；现场结构已复核；指定Kafka直写/我方全量落湖及类型盘点沿最新方向，不冒称整链已验 |
| ClickHouse日志湖表结构与实施规划 | [11-19规划](../../openspec/changes/complete-socai2-investigation-chain/clickhouse-lake-design-20261119.md)：已核23.8/48列，3a完成48旧列映射及14新增列合同/候选SQL/合成验证；新接入入湖400天及重试刷新已确认。3b已通过迁移/读回，3c已通过原生驱动适配/完整保存；正式表未变，3d持久确认已通过真实隔离链，3e真实固定范围聚合验收已通过，3f基础查询及完整原文读回已完成 |
| 字段必需性与责任基准 | [11-18字段审查](subject-field-baseline-20261118.md)及[OpenSpec定稿](../../openspec/changes/complete-socai2-investigation-chain/subject-field-audit-20261118.md)：必需时点、自动等级只升不降/人工修改、五档优先级、时间线、任务时间与文件日志；S1–S4候选已验，下一步现有HTTP真实数据接通及新批次一轮，S5/S6与整体验收保持；SF01–SF07未整项核销 |
| 本轮评审与问题 | [11-14功能与整体流程评审](investigation-current-review-20261114.md)、[问题清单](current-issues.md)；RV12已有修复与后续4177发布证据，当前剩余边界以问题清单为准；不延用11-14未修复状态 |
| 后续实施阶段 | [11-14六阶段规划](investigation-implementation-plan-20261114.md)：各阶段目标、解决问题、交付物、依赖和通过条件；阶段2–5对应同一个流式change，正文质量继续后置 |
| 可复用完整测试 | [环境准备与全流程规划](../../openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md)、[告警和上下文设计](../../openspec/changes/schedule-streaming-investigation-updates/test-data-design-20261115.md)、[模块/HTTP依赖](../../openspec/changes/schedule-streaming-investigation-updates/test-interface-readiness-20261115.md)、[独立测试服务与4177 HTTP取数](../../openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md)；各步范围见[当前进度](../../PROGRESS.md)；当前[D6正式4177](../operations/evidence/workbench-d6-release-20261118-01/README.md)为0.6.2/r9，四异常代表及日常两轮实际读回通过；历史W5空态不代表当前数据 |
| 调查设计与任务 | [主调查设计](../../openspec/changes/complete-socai2-investigation-chain/design.md)、[主调查任务](../../openspec/changes/complete-socai2-investigation-chain/tasks.md)、[流式更新方案](../../openspec/changes/schedule-streaming-investigation-updates/design.md) |
| D6完整change收口 | [本期范围与归档条件](../../openspec/changes/schedule-streaming-investigation-updates/closeout-scope-20261118.md)、[人工定向/手动综合/知识异步维护后置原文](../../openspec/changes/schedule-streaming-investigation-updates/deferred-scope.md)；本期未完成交付保留，结构审计不替代业务验收 |
| 程序与模型职责 | [执行账本](current-execution-ledger.md)、[模型输入输出](model-input-output-current-20261109.md)、[按环节字段设计](../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md) |
| 表与字段 | [28表职责](investigation-table-scope.md)、[当前机器字典](../design/socai2-data-contract-current.json)、[数据交接](socai2-page-data-handoff-20261106.md)、[冻结V1字典](../design/socai2-field-dictionary-20261103.md) |
| 产品规则 | [125项功能清单](../../deliverables/investigation-validation-20261106/frontend-feature-list.md)、[已确认规则](../design/investigation-product-decisions.md)、[产品需求](../design/alert-incident-case-product-requirements.md)、[字段/跳转附录](../../deliverables/investigation-validation-20261106/frontend-data-navigation-contract.md) |
| HTTP交接 | [当前80操作及SpiritHub迁移交接](../integration/spirithub-18024-handoff-20261118.md)、[同版OpenAPI](../../deploy/aisoc21/acceptance-release-20261117-01/contract/openapi.json)、[对外/内部边界](../design/investigation-http-boundary.md)；[旧71操作交接包](../../deliverables/investigation-validation-20261106/http-handoff/README.md)只作历史参照 |
| 知识与采用 | [Case知识](case-knowledge-handoff.md)、[历史告警知识](historical-alert-knowledge-handoff.md)、[采用规则AD01–AD06](result-adoption-and-pending-work.md)、[采用HTTP](../integration/result-adoption-http.md) |
| 调查证据与历史原件 | [11-19现场结构及盘点/规划回执](../operations/evidence/investigation-integration-audit-20261119-01/README.md)、[证据导航](../operations/evidence/README.md)；[11-14三案](../operations/evidence/fixed-investigation-20261114-01/README.md)保留为当时原件，不称当前最新批次 |
| 当前发布依据 | [当前进度](../../PROGRESS.md)、[11-19现场版本核对](../operations/evidence/investigation-integration-audit-20261119-01/README.md)：正式核心/HTTP为11-17 r1，4177为D6 0.6.2/r9；最新D5写侧与完整change收口另按原任务，不能用工作台版本代替 |
| 部署和本机接入 | [21部署](../../deploy/aisoc21/README.md)、[SSH转发](../operations/mac-ssh-relay-20261107.md)、[配置索引](../operations/configuration.md) |
| 历史与保留 | [11-14归档及路径映射](../handoff/history/2026-11-14-investigation-cleanup/README.md)、[代码与数据保留清单](../handoff/retention-map.md) |

Case/告警/事件管理、评论、附件引用、列表/CSV、归并统计、采用、故事、候选、探索保存和相似/同主机查询已交付；实际操作和字段以HTTP交接为准。各页面AI对话暂缓，E19/E20仍501；流式任务/调度和[第3步新告警自动分诊](../operations/evidence/analysis-alert-auto-20261115-01/README.md)已本地验收，I/Case自动更新与反馈的已验边界见当前PROGRESS，指定SpiritHub Topic尚未成为正式调查消费者输入，自动消费整链尚未验收，具体服务开关以当前profile和现场回执为准。程序交付、业务结论、采用、页面接线与模型质量分别验收，原失败及NOT_PASSED保留。
