# 当前进度

更新于 2026-11-12。[历史告警知识与模型消费](openspec/changes/archive/2026-11-12-use-historical-alert-knowledge/tasks.md)已完成本地实现、12 项直接检查、一次完整链、本地独审及一次 21 发布读回，发布补审已 ACCEPT 并归档，最终 Git/父项目同步按本轮交付执行。C2 按技术解释、取证指导、历史案例参考检索；C3/Deep/C6 消费冻结原文及来源，模型质量仍为 NOT_PASSED。按用户最新顺序，先收尾此 change，再独立提出知识检索与历史入库优化 OpenSpec。工作规则见 [AGENTS](AGENTS.md)，对接从[交接指南](FRONTEND_BACKEND_HANDOFF.md)进入。

## 当前运行状态

| 项目 | 已核验结果 |
| --- | --- |
| 分支与交付 | `V1.1`；每个 change 本地收口后统一更新 21 一次，最终 Git 与父项目 `SpiritHub/add-server-submoudle` 的 `server` 引用统一推送并读回 |
| 21 发布 | `v1.2-20261112-r1`；API 与 4177 各切换一次，处理镜像 `processing-20261112-r1`；fusion/agents/projection/litellm 四项容器身份读回保持，沿用已有嵌入服务 |
| 正式数据 | `aisoc.socai2`，29 表、462 列；告警交接字段、37 组枚举、40 项 JSON 合同保持，无调查 DDL |
| 知识 | qwen3-embedding:0.6b/1024，专用 `socai2_knowledge_qwen06b_1024`；已有技术/方法资料保持，本轮一张已有演练告警卡经 3 次 HTTP 入库/索引/GET及一次历史目的只读检索，原身份/hash对应 |
| HTTP/身份 | Case/H 写读保持；知识验收用本次临时 scope key，完成后已撤销且读取 401，不改账号角色。既有 viewer 正常登录不具备 KB 写权限 |
| 模型与消费者 | 单 Run 6 模型、4 工具、131,072 token；单次 300 秒、Case 1500 秒、C6 预留 300 秒，额度不增；自动消费者暂停 |
| 4177 | 源码随统一发布；21 从实际 37 份追加至 38 份，本地 66 份，已有记录/文件保留；76 静态文件及 77 HTTP 读回通过。本地历史页面已实际查看，本机 4177 经 SSH 转发 21 |

本次[交付回执](docs/operations/evidence/historical-knowledge-20261112-01/delivery-summary.json)区分本地完整 Run、生产 3 次业务 HTTP、只读 adapter 探针及静态批次；生产没有新增 Case/Run 或分析模型。临时知识验收 key 已撤销并核 401，账号角色保持。[知识字段](docs/investigation/case-knowledge-handoff.md) · [历史卡片交接](docs/investigation/historical-alert-knowledge-handoff.md)。

## 前序有效证据

[Case/H HTTP](openspec/changes/archive/2026-11-11-enable-case-human-http-flow/validation.md)已完成建案→首轮→人工完成/修订→后轮→保存读取，人工第 2 修订进入后轮实际输入；产品页面和完整语义质量仍开放。[有据结论程序交付](openspec/changes/archive/2026-11-11-ground-case-conclusions/validation.md)的观察原值、coverage 与 C3 两项上限保持。

[独立流程审查](docs/investigation/investigation-flow-review-20261111.md)及[整理归档](docs/handoff/history/2026-11-11-local-cleanup/README.md)继续有效，不重开已完成 change；无关未提交的 `tools/model-preflight/` 保持。

## 未完项与下一步

知识功能的本地链路、交接、限定独审与一次发布已完成；[验收](openspec/changes/archive/2026-11-11-enable-purpose-aware-case-knowledge/validation.md)保留失败和未验范围。C2 6 查询/8 命中（4 唯一块）、1 条有效查空；5 份模型输入可见，C3/C6 引用，两个 Deep 无引用。5 次模型、90,292 reported tokens；C6 duplicate_source 纠正仍失败，Result partial/rejected、conclusion=null，模型质量 NOT_PASSED，不再采样。

历史告警知识本地已通过源卡入库/索引/GET、C2 9 查询/10 行及 C3/Deep/C6 输入传递、保存/读取；5 次模型/98,629 tokens，结构化引用数组未引用历史，部分正文有提及，C6 recommendation_needs_sources 拒收，质量 NOT_PASSED。本次收尾只补发布及读回，原答不重跑。完成本 change 归档、Git/父项目同步后，独立规划按用途选知识、按模型阶段提供片段及历史告警入库时机。F02 召回相关性/合理使用、F01 完整语义质量及 P01–P04、自动处理继续开放；A/I 新检索、Deep 动态再检索及独立处置检索仍未实施。M01-A/M01-B 保持已知未修复，Hunt A03/A04 仅在其模块启用前处理。前一 change 的 `4d46f4d4` / 父项目 `6f46647e` 回执继续适用于原批，不重复发布。

主调查仍 31/41，3.7、3.10、3.12、3.16、3.23、3.30 等整体任务不因局部 HTTP 接通直接完成。当前问题见[问题清单](docs/investigation/current-issues.md)。
