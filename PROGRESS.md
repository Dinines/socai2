# 当前进度

更新于 2026-11-11。当前交付单元为 [enable-case-human-http-flow](openspec/changes/archive/2026-11-11-enable-case-human-http-flow/tasks.md)：本地 Case/H HTTP 正常流程、人工修订传递、交接及独立结束审计已通过，并已统一发布到 21、完成 OpenSpec 归档。权限专项不作为当前工作，直接复用功能所需读写连接。工作规则见 [AGENTS.md](AGENTS.md)，对接从[交接指南](FRONTEND_BACKEND_HANDOFF.md)进入。

## 当前运行状态

| 项目 | 已核验结果 |
| --- | --- |
| 分支与交付 | `V1.1`；每个 change 本地完成后统一更新 21 一次，再推送子仓库及父项目 `SpiritHub/add-server-submoudle` 的 `server` 引用 |
| 21 发布 | `v1.2-20261111-r2`，本轮仅一次 API 更新；处理镜像复用 `processing-20261111-r1`，其他五项服务保持 |
| 正式数据 | `aisoc.socai2`，29 表、462 列；告警交接字段、37 组枚举和 40 项 JSON 合同保持，无 DDL |
| HTTP | 21 Case/H GET 与写入口均已开放；使用既有账号正常登录后完成独立验收 Case/H 写读，通用 API 连接保持 |
| 模型与消费者 | 单 Run 6 模型、4 工具、131,072 token；单次 300 秒、Case 1500 秒、C6 预留 300 秒，额度不增；自动消费者暂停 |
| 4177 | 组件 `workbench-20261110-r2`；21 为 35 份，本地资料已追加本 Case 至 64 份；本机端口通过 SSH 转发到 21 |

## 本轮功能与证据

沿原 HTTP 路由、服务、执行器及数据库走通建案→首轮调查→人工任务完成/修订→prepare/start 后轮→结果读取。13 次 HTTP 操作成功；人工第 2 修订、原文及 human_statement 来源进入后轮冻结输入与 4 份实际模型请求，原修订保留；两份 Result 六项关键字段与落库一致。

两轮真实模型分别 5/4 次，reported tokens 71,723/45,452，费用未知。两轮实际 completed/partial；首轮 C6 引用非法，经现有一次纠正后仍 rejected、conclusion=null，后轮 accepted 并保留授权/命令结果/影响未知。执行完成和反馈可见不等于模型质量通过。模型标签推事实、查询状态正文偏差按负责人决定登记后置，不再重复采样。[本轮验收与限制](openspec/changes/archive/2026-11-11-enable-case-human-http-flow/validation.md)

本地认证主体和模型内网传输为明确适配器，实际业务服务和存储没有替换；产品登录/页面不能由本地 ASGI 证明。11 项直接检查通过，不做复杂测试、可用性开发、全库对账或多模型比较。21 正常登录后 8 次业务 HTTP 请求通过，人工任务 8 项字段与正式库一致；验收 Case 的 Run 保持 pending_update，未调用生产模型。实际来源开关与写连接已核实，其他五容器保持。[交付回执](docs/operations/evidence/case-human-http-20261111-01/delivery-summary.json)

## 已完成的前序工作

[有据结论程序交付](openspec/changes/archive/2026-11-11-ground-case-conclusions/validation.md)已统一发布 r1 并同步子仓库和父项目。C3 新补查上限为 2，observed.statement 原值装配及 C6 真实 coverage 生效；模型质量 NOT_PASSED、原答和失败保持。[交付回执](docs/operations/evidence/case-grounding-20261111-01/delivery-summary.json)

[独立流程审查](docs/investigation/investigation-flow-review-20261111.md)及[本地整理归档](docs/handoff/history/2026-11-11-local-cleanup/README.md)已完成，审计和历史证据保留；不重开已完成 change。独立未提交的 `tools/model-preflight/` 保持。

## 未完项与下一步

本 change 的程序功能、交接、限定独审与一次发布回执已完成。Git 交付规则：归档后推送包含本批回执/冻结 manifest 的 V1.1 提交，再同步父项目 server，并以实际远端 hash 读回为完成依据。持续模型问题继续后置，不以重复采样阻塞后续。

下一项按[既定路线](openspec/changes/complete-socai2-investigation-chain/design.md#后续工作顺序)推进真实非空知识的检索→输入→引用，再处理产品页面 P01–P04 与自动消费。Case/H 产品页面操作、F01 正确利用反馈的完整语义质量仍未核销；M01-A/M01-B 保持已知未修复，Hunt A03/A04 仅在该模块启用前处理。

主调查仍 31/41，3.7、3.10、3.12、3.16、3.23、3.30 等整体任务不因局部 HTTP 接通直接完成。当前问题见[问题清单](docs/investigation/current-issues.md)。
