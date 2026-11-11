# 当前进度

更新于 2026-11-11。[ground-case-conclusions](openspec/changes/archive/2026-11-11-ground-case-conclusions/tasks.md)的程序功能、直接验证、交接及限定独审已完成，并统一发布到 21。按负责人明确决定，持续出现的模型标签推环境、自由正文误写查询状态登记为 M01-A/M01-B 后置，质量仍 NOT_PASSED，不再阻塞已验证程序功能与后续 Case/H 正常操作，不继续同类模型采样。工作约定见 [AGENTS.md](AGENTS.md)，前后端从[交接指南](FRONTEND_BACKEND_HANDOFF.md)进入。

## 当前运行状态

| 项目 | 已核验结果 |
| --- | --- |
| 分支与交付单元 | `V1.1`；本次为 `ground-case-conclusions`，一个 change 完整验收后统一发布、推送；父项目 `SpiritHub/add-server-submoudle` 的 `server` 引用以远端实际 commit 为交付锚点 |
| 21 发布 | `v1.2-20261111-r1`，处理组件 `processing-20261111-r1`；API 仅更新一次，五项继承服务容器保持 |
| 服务 | 6 服务健康；4177 使用独立组件 `workbench-20261110-r2`，本机 4177 是 SSH 转发到 21 |
| 正式数据 | `aisoc.socai2`，29 表、462 列；告警前后端合同、37 组枚举及 40 项 JSON 合同保持，该发布无 DDL |
| 运行接线 | Case/H GET 可读，Case HTTP 写开关关闭，自动消费者暂停；权限设计不作为功能前置 |
| 预算 | 单 Run 6 模型、4 工具、131,072 token，模型单次 300 秒、Case 1500 秒、C6 预留 300 秒；额度未提高 |
| 查阅资料 | 21 的 4177 共 34 份记录，该发布追加 5 份，原记录保持；374 文件／375 HTTP 静态核验通过。本地静态资料库合计 63 份，与 21 分开计数 |

## 最近功能交付

C3 新响应补查上限 2 已贯通冻结、生成、普通接收及 partial；超限拒收且不截断派发，历史读取兼容。C3/C6 的 observed.statement 按原记录路径和值由程序装配，C6 coverage 取实际材料/查询/分析回执，对外仍为六问；冲突逐 finding/成员检查原始支持。Case 登记文字从业务模型视图排除，原件、人工正文与告警交接字段保持。[实现与验收](openspec/changes/archive/2026-11-11-ground-case-conclusions/validation.md)

受影响的直接检查通过，实际本地 C1–C6 流程使用真实 PostgreSQL 和模型网关；第五批 5 调用、60,968 reported tokens，费用未知，completed/partial，C6 accepted/uncertain 并采用。54 次原 GET 成功，Result 六项关键字段及两份 Deep 工件与保存内容一致。五批原答、失败与读取证据保留。正文仍有标签推环境、未查说成查空和时间间隔偏差，质量 NOT_PASSED；独审按负责人后置决定对程序范围补充 ACCEPT，原 REVISE 保持。

21 实际加载 `max_followups=2` 和程序输出职责标记；发布后 Case/Run/Result 三次 GET 成功，六项 Result 字段与正式库一致，读取前后快照不变。没有生产模型调用、调查数据写入或 DDL。验收 API key 过期后采用已有账号正常登录完成读取，未新增账号、key 或权限。[本次交付回执](docs/operations/evidence/case-grounding-20261111-01/delivery-summary.json)

## 已完成的独立流程审查

核实 A/I/C/H 与保留 Agents/Hunt/Swarm 的真实入口和边界；形成[审查报告](docs/investigation/investigation-flow-review-20261111.md)。主线确认 Deep/C6 正文缺少依据（A01，沿用 M01/M02）及 C3 提示最多两项补查、程序允许 12 项的不一致（A02）；Hunt 另有默认租户传递和失败误报完成（A03/A04），只在对应保留模块范围处理。

56 项定向隔离检查通过，其中反例用于确认缺陷存在，不代表业务验收通过。只读复查真实历史 Run 的输入/原答/落库，审计当时 98 个冻结来源一致；2,788 个受保护源码/配置/测试文件保持。独立结束复核 ACCEPT，流程图分流已修正，0 项未解决报告阻塞；不代表四项问题已修复。未调用新模型或数据库，未部署或 Git 提交/推送。[验证及限制](docs/operations/evidence/investigation-audit-20261111-01/README.md)

## 已完成的本地整理

归档 25 份较早文档，当前主设计与任务保留有效合同、功能顺序和全部 31/41 状态；根目录讨论稿、迁移计划与重复模块分析有明确历史入口。22 个本地发布源码快照/产物、7,667 文件移入忽略提交的归档，逐项核对内容与文件模式；当前 r6 和配置仍引用的三个包原位保留。[归档及映射](docs/handoff/history/2026-11-11-local-cleanup/README.md)

业务源码、数据库设计、既有样本与失败原答、4177 记录、独立未提交模型工具均保持。归档完整性与链接检查通过，独立结束审计 ACCEPT、0 个未解决阻塞，本轮维护 change 已归档。无模型调用、数据库操作、服务重启、21 更新或 Git 提交/推送。

## 未完项与下一步

按[OpenSpec 路线](openspec/changes/complete-socai2-investigation-chain/design.md#后续工作顺序)进入 Case/H 正常操作：接通既有 HTTP 建案、准备/启动、人工补充及下一轮调查，核选中人工版本进入输入并保存读回；必要读写配置随功能处理。之后是实际非空知识使用、页面功能对应、自动处理。Hunt 两项问题只在该模块启用前处理。

中间修改和测试在本地完成；每个 change 仅做改动相关检查和一条代表性完整路径，同批复用模型/数据库/读取证据。独审完成后统一发布一次，再推送子仓库并同步父项目。没有复杂测试、压力/恢复矩阵、全量对账或多模型比较；持续模型问题保留开放，不再通过重复采样阻塞独立功能。

主调查仍为 31/41，3.7、3.10、3.23、3.30 等整体任务未完成。知识查空不证明使用成功，H 传递不证明业务授权，减少测试不等于模型质量通过。问题集中在[问题清单](docs/investigation/current-issues.md)。
