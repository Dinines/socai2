# 当前进度

更新于 2026-11-12。前序[历史告警知识](openspec/changes/archive/2026-11-12-use-historical-alert-knowledge/tasks.md)已先完成归档及 Git／父项目同步。在该基线上，[知识按用途筛选与模型使用](openspec/changes/archive/2026-11-12-refine-purpose-aware-knowledge-use/tasks.md)已完成适用条件筛选、模型去重／任务选取、当前历史快照过滤、一次本地流程及独立审计，并实际发布 21、读回配置和知识写读；已归档且封后规格校验通过。最终 Git 交付按 `V1.1` 及父项目 `add-server-submoudle` 的 `server` 引用读回对应，精确提交见 Git 历史和本轮交付回复。模型质量仍为 NOT_PASSED。工作规则见 [AGENTS](AGENTS.md)，对接从[交接指南](FRONTEND_BACKEND_HANDOFF.md)进入。

## 当前运行状态

| 项目 | 已核验结果 |
| --- | --- |
| 分支与交付 | `V1.1`；每个 change 本地收口后统一更新 21 一次，最终 Git 与父项目 `SpiritHub/add-server-submoudle` 的 `server` 引用统一推送并读回 |
| 21 发布 | `v1.2-20261112-r3`；API 与 4177 各切换一次，处理镜像 `processing-20261112-r2`；fusion/agents/projection/litellm 四项容器身份读回保持，沿用已有嵌入服务 |
| 正式数据 | `aisoc.socai2`，29 表、462 列；告警交接字段、37 组枚举、40 项 JSON 合同保持，无调查 DDL |
| 知识 | qwen3-embedding:0.6b/1024，专用 `socai2_knowledge_qwen06b_1024`；三目的按标签／条件筛选，共用存储。7 次生产业务 HTTP 通过；3 个目的只读查询返回 5 行，历史已有卡身份保持，新方法资料 2 块；旧资料保持 |
| 模型知识输入 | 实际加载每目的 8 候选；C3／Deep／C6 可选知识预算 12,000／8,000／8,000 字符；Deep 可选方法／历史，前序引用依赖优先恢复；仅模型视图去重，原检索回执保留 |
| HTTP/身份 | Case/H 写读保持；知识验收用本次临时 scope key，完成后已撤销且读取 401，不改账号角色。既有 viewer 正常登录不具备 KB 写权限 |
| 模型与消费者 | 单 Run 6 模型、4 工具、131,072 token；单次 300 秒、Case 1500 秒、C6 预留 300 秒，额度不增；自动消费者暂停 |
| 4177 | 源码随统一发布；21 从实际 38 份追加至 39 份，本地 67 份，已有记录／文件保留；79 静态文件及 80 HTTP 读回通过。浏览器已查看筛除原因与模型合并出处，本机 4177 经 SSH 转发 21 |

本次[交付回执](docs/operations/evidence/knowledge-selection-20261112-01/delivery-summary.json)区分本地完整 Run、生产 7 次业务 HTTP、3 个只读目的探针及静态批次；生产没有新增 Case／Run 或分析模型。临时知识验收 key 已撤销并核 401，账号角色保持。首次 r2 冻结因旧部署基线在 preflight 失败，未 rollout；核实际基线后冻结 r3，原失败回执保留。[知识字段](docs/investigation/case-knowledge-handoff.md) · [历史卡片交接](docs/investigation/historical-alert-knowledge-handoff.md)。

## 前序有效证据

[Case/H HTTP](openspec/changes/archive/2026-11-11-enable-case-human-http-flow/validation.md)已完成建案→首轮→人工完成/修订→后轮→保存读取，人工第 2 修订进入后轮实际输入；产品页面和完整语义质量仍开放。[有据结论程序交付](openspec/changes/archive/2026-11-11-ground-case-conclusions/validation.md)的观察原值、coverage 与 C3 两项上限保持。

[独立流程审查](docs/investigation/investigation-flow-review-20261111.md)及[整理归档](docs/handoff/history/2026-11-11-local-cleanup/README.md)继续有效，不重开已完成 change；无关未提交的 `tools/model-preflight/` 保持。

## 未完项与下一步

本轮[验收](openspec/changes/archive/2026-11-12-refine-purpose-aware-knowledge-use/validation.md)记录一条新批次：9 查询／5 行（3 唯一块），排除 6 次条件冲突和 2 次过期卡候选，模型合并 2 次重复正文；6 模型／119,412 reported tokens。C6 duplicate_source 纠正后仍 delivery_source_coverage_missing，Result partial/rejected、conclusion=null，质量 NOT_PASSED。知识依赖恢复和缩小任务范围由直接检查支持，本轮有效模型结果未引用知识、两个 Deep 仍为全案问题；不扩大真实流程结论，也不再采样。历史入库在有效分诊或人工反馈保存后显式触发，修订产生新快照并索引；旧卡和旧 Run 保留。

F02 召回正文相关性／合理使用、F01 完整语义质量及 P01–P04、自动处理继续开放；A/I 新检索、Deep 动态再检索及独立处置检索仍未实施。M01-A/M01-B 保持已知未修复，Hunt A03/A04 仅在其模块启用前处理。

主调查仍 31/41，3.7、3.10、3.12、3.16、3.23、3.30 等整体任务不因局部 HTTP 接通直接完成。当前问题见[问题清单](docs/investigation/current-issues.md)。
