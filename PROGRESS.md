# 当前进度

更新于 2026-11-11。当前交付单元 [enable-purpose-aware-case-knowledge](openspec/changes/archive/2026-11-11-enable-purpose-aware-case-knowledge/tasks.md) 已完成本地实现、直接验收、限定独审和一次 21 r3 发布，已通过发布补核并归档。C2 按技术解释/取证指导检索本地嵌入索引，C3/Deep/C6 消费冻结片段，4177 显示真实输入输出与引用关系。工作规则见 [AGENTS](AGENTS.md)，对接从[交接指南](FRONTEND_BACKEND_HANDOFF.md)进入。

## 当前运行状态

| 项目 | 已核验结果 |
| --- | --- |
| 分支与交付 | `V1.1`；每个 change 本地收口后统一更新 21 一次，最终 Git 与父项目 `SpiritHub/add-server-submoudle` 的 `server` 引用统一推送并读回 |
| 21 发布 | `v1.2-20261111-r3`；API 与 4177 各切换一次，处理镜像 `processing-20261111-r3`；fusion/agents/projection/litellm 四容器和已有嵌入容器保持 |
| 正式数据 | `aisoc.socai2`，29 表、462 列；告警交接字段、37 组枚举、40 项 JSON 合同保持，无调查 DDL |
| 知识 | qwen3-embedding:0.6b/1024，专用 `socai2_knowledge_qwen06b_1024`；两份 MITRE 资料 4 块经原 HTTP 导入/索引/GET，C2 两目的只读实际检索返回 4 块并核 PG 原文/hash |
| HTTP/身份 | Case/H 写读保持；知识验收用本次临时 scope key，完成后已撤销且读取 401，不改账号角色。既有 viewer 正常登录不具备 KB 写权限 |
| 模型与消费者 | 单 Run 6 模型、4 工具、131,072 token；单次 300 秒、Case 1500 秒、C6 预留 300 秒，额度不增；自动消费者暂停 |
| 4177 | 源码随统一 r3；21 追加至 36 份，本地 65 份；本机端口经 SSH 转发 21，实际浏览器已核 C2 片段/查空和 C6 失败 |

本次[交付回执](docs/operations/evidence/case-knowledge-20261111-01/delivery-summary.json)区分本地完整 Run、生产 7 次业务 HTTP、只读 adapter 探针和页面静态批次。生产未启动新 Case/Run 或分析模型。知识输入/输出字段见[知识交接](docs/investigation/case-knowledge-handoff.md)。

## 前序有效证据

[Case/H HTTP](openspec/changes/archive/2026-11-11-enable-case-human-http-flow/validation.md)已完成建案→首轮→人工完成/修订→后轮→保存读取，人工第 2 修订进入后轮实际输入；产品页面和完整语义质量仍开放。[有据结论程序交付](openspec/changes/archive/2026-11-11-ground-case-conclusions/validation.md)的观察原值、coverage 与 C3 两项上限保持。

[独立流程审查](docs/investigation/investigation-flow-review-20261111.md)及[整理归档](docs/handoff/history/2026-11-11-local-cleanup/README.md)继续有效，不重开已完成 change；无关未提交的 `tools/model-preflight/` 保持。

## 未完项与下一步

知识功能的本地链路、交接、限定独审与一次发布已完成；[验收](openspec/changes/archive/2026-11-11-enable-purpose-aware-case-knowledge/validation.md)保留失败和未验范围。C2 6 查询/8 命中（4 唯一块）、1 条有效查空；5 份模型输入可见，C3/C6 引用，两个 Deep 无引用。5 次模型、90,292 reported tokens；C6 duplicate_source 纠正仍失败，Result partial/rejected、conclusion=null，模型质量 NOT_PASSED，不再采样。

后续优先处理产品页面 P01–P04 的功能与字段对应，再接自动处理。F02 知识召回相关性和取证方法使用效果、F01 完整语义质量继续开放；A/I 新检索、Deep 动态再检索及独立处置检索后置。M01-A/M01-B 保持已知未修复，Hunt A03/A04 仅在其模块启用前处理。本 change 已归档；最终 Git 与父项目引用按一次推送读回交付，不重复发布。

主调查仍 31/41，3.7、3.10、3.12、3.16、3.23、3.30 等整体任务不因局部 HTTP 接通直接完成。当前问题见[问题清单](docs/investigation/current-issues.md)。
