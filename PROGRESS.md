# 当前进度

更新于 2026-11-12。前序知识用途筛选 change 已交付归档（服务端 `f993e630`、父项目 `048668b4`）。本项[分诊保存后同步历史知识](openspec/changes/archive/2026-11-12-sync-saved-alert-knowledge/tasks.md)已完成本地功能、一次直接流程、独审及 21 统一发布读回，发布审计与归档已完成；最终 Git／父项目引用随本 change 统一同步。模型质量仍为 NOT_PASSED。工作规则见 [AGENTS](AGENTS.md)，对接从[交接指南](FRONTEND_BACKEND_HANDOFF.md)进入。

## 当前运行状态

| 项目 | 已核验结果 |
| --- | --- |
| 分支与交付 | `V1.1`；每个 change 本地收口后一次实际发布、统一推送及同步 `SpiritHub/add-server-submoudle` 的 `server` 引用 |
| 21 发布 | `v1.2-20261112-r5`；处理镜像 `processing-20261112-r3`；API／工作台各切换一次，fusion／agents／projection／litellm 原容器身份保持 |
| 正式数据 | `aisoc.socai2`，29 表、462 列；告警交接字段、37 组枚举、40 项 JSON 合同保持，无调查 DDL |
| 知识检索 | 技术解释、取证指导、历史案例参考按目的／条件筛选，共用存储；qwen3-embedding:0.6b/1024，专用 `socai2_knowledge_qwen06b_1024`，不改既有情报／组织记忆集合 |
| 新分诊后同步 | 实际加载 `history.sync_after_adopted_triage=true`、总时限 120 秒；仅新提交且采用的 A 触发，独立入库／索引／回执，旧 operation key 不补派；未知不自动重试 |
| 处理连接 | 实际 `aisoc/socai2_prod_processor`，租户设置及 KB SELECT/INSERT 已读回；只增加知识表 INSERT，原 RLS、API 读连接和 Case/H 写连接保持 |
| 模型知识输入 | 每目的 8 候选；C3／Deep／C6 可选知识预算 12,000／8,000／8,000 字符；前序引用依赖优先恢复，仅模型视图去重，原检索回执保留 |
| 模型与消费者 | 单 Run 6 模型、4 工具、131,072 token；单次 300 秒、Case 1500 秒、C6 预留 300 秒；自动消费者关闭，本轮没有分析模型调用 |
| 4177 | 21 由 39→40 份，本地 67→68 份；旧记录／文件保持，新增 2 文件／3 HTTP 读回通过；新同步工件沿原件入口查看，没有新状态页面 |

本次[交付回执](docs/operations/evidence/knowledge-sync-20261112-01/delivery-summary.json)明确区分本地与生产：本地一条新模板分诊经真实 finish 保存、采用、自动同步、嵌入／索引，历史查询返回当前卡，5 个原 GET 成功；重复 finish 保持原 outcome 和两份同步回执。11 项直接检查通过，不跑全仓回归或新模型采样。生产只核实际加载、处理连接与静态原件，没有新增 A／Case Run、知识写入或嵌入调用，不能称为生产重新执行了自动同步。

r4 的 Compose 基线路径在 preflight 被拒，尚未 rollout；按服务器实际路径修正后冻结 r5，失败及[修正说明](docs/operations/evidence/knowledge-sync-20261112-01/release-plan-correction.json)保留。本地 93 个冻结应用源码未在流程后变更，实际加载的 5 个受影响文件与本地一致。[知识字段](docs/investigation/case-knowledge-handoff.md) · [历史卡片与同步交接](docs/investigation/historical-alert-knowledge-handoff.md)。

## 未完项与下一步

正式告警级人工反馈写入口尚未接线，Case H 写入任务版本，不能替代告警反馈；人工反馈历史维护继续使用原显式入库／索引接口。后续优先核该业务入口及现有合同，再按独立 OpenSpec 推进保存与知识修订；不预建调度、全库回填或恢复框架。A/I 新知识检索、Deep 动态再检索及自动处理主链继续开放。

F02 召回正文相关性／合理使用、F01 完整语义质量及 P01–P04 页面事项仍未通过。前序[用途筛选验收](openspec/changes/archive/2026-11-12-refine-purpose-aware-knowledge-use/validation.md)的 6 模型／119,412 reported tokens 结果仍 partial/rejected、conclusion=null；有效模型结果未引用知识，不能用本轮可检索／模板判断证明质量改善。M01-A/M01-B 保持已知未修复，不再反复采样；Hunt A03/A04 仅在其模块启用前处理。

主调查仍 31/41，3.7、3.10、3.12、3.16、3.23、3.30 等整体任务不因局部功能完成而核销。当前问题见[问题清单](docs/investigation/current-issues.md)。无关未跟踪 `tools/model-preflight/` 保持。
