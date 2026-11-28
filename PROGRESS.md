# 当前进度

本轮按负责人最新要求，将已实现的完整调查链交付到 **socai2 main 与 SpiritHub main**，并整理前端、平台后端、调查 HTTP、Fusion、调查执行及 LLM 代理的发布方式。独立工作树中的主线整合、合同及生产构建验证已完成，源码核对见 [完整 main 交付记录](docs/operations/evidence/main-integration-20261128-01/README.md)。发布源码必须取自最终推送后读回的 main，父项目 `server` 必须指向同一 socai2 提交；最终 SHA 由 Git 回执记录。线上各组件尚未按这一完整组合统一切换，旧局部候选不能作为最终完整发布。

原有逐轮内容已保留到 [完整 main 交付前快照](docs/handoff/history/2026-11-28-main-integration/README.md)，历史失败、授权范围和未验项不改写为通过。当前入口仍为 [OpenSpec 任务](openspec/changes/complete-socai2-investigation-chain/tasks.md) 和 [前后端交接](FRONTEND_BACKEND_HANDOFF.md)。

## 本轮完整源码与发布交接

| 范围 | 当前安排与证据入口 |
| --- | --- |
| socai2 | 纳入当前所有调查核心、原生 HTTP、Fusion、查阅工作台的生产源码和直接测试，包含 V1.1 已提交的输入过滤依赖、S1/S2/S3 模型异常处理、前序材料归一化、Case 故事/历史/资料等读取及部署/迁移依赖。见 [核心/Fusion/模型清单](openspec/changes/complete-socai2-investigation-chain/core-fusion-model-git-handoff-20261128.md)、[HTTP 完整清单](openspec/changes/complete-socai2-investigation-chain/http-complete-delivery-handoff-20261128.md)。 |
| SpiritHub | 实际 8181 源树已冻结为提交 `837ea616`，在普通独立工作树与远端 main `83a4f5ef` 合并；保留主线扫描、PDF、助手及其他模块更新。前端与平台 bridge/合同/配置一起整合，类型由最终 OpenAPI 生成。见 [整合计划](openspec/changes/complete-socai2-investigation-chain/spirithub-frontend-precommit-audit-20261128.md)、[前端交接](openspec/changes/complete-socai2-investigation-chain/spirithub-frontend-release-handoff-20261128.md)。 |
| 配置与包 | 实际凭据、运行 profile、原始材料、模型原答和生成的工作台快照留本机受控位置；生产源码、配置结构/模板、依赖、迁移及手册入 Git。4173 本机录制与混合演示修改整组保留，不作为生产实现提交；生产组件不依赖该组原型文件。 |
| 最新版本发布 | [21 完整 main 部署手册 §12](docs/operations/investigation-manual-deployment-21-20261127.md#12-完整-main-版本发布2026-11-28)给出组件产物、构建入口、监听/连接字段、依赖顺序、最小验收与回退。本轮沿现有库升级，不额外建库；历史 D1/D2/D3 新库演练仅保留为记录。 |

整合中发现的实际阻断按最小范围修正：原生 HTTP 日志接入回到 adapter 边界，保持真实日志和错误响应；合同测试精确识别已确认的事件判定与既有描述增量，不改告警合同。平台合同以当前原生注册为准，保留事件详情已发布诊断/最近尝试；不能复活已经退役的公开 prepare/start 或手动告警执行入口。没有新增按测试样本分支、虚构默认值或用于伪装成功的业务实现。

最终源码核对：原生 HTTP 定向 4 项、平台 bridge 定向 34 项、前端受影响失败项的定向复验、类型检查及生产构建通过。三个 OpenSpec change 严格校验通过；平台 212 条非 SOC 路径及 378 个可达组件与 main 保持一致。前端构建保留主线扫描模块混合导入及分块大小提示，未另开无关优化。

## 最近真实执行与独立验收

- S1/S2/S3 输入拒绝、无效响应及无回复/超时/取消的本地处理与动态查阅已完成定向验证和独审。前序材料修正只复用已有引用归一化，不改原件、范围、摘要或正文校验；旧 profile 夹具失败及原批次失败保留。
- 最近一笔原生 Case 重跑已完成；C3/C6 有完整 JSON 原答，真实模型结果已保存并由当前 Case 采用。实际结论为待核实、部分交付，正文质量未审，不能称为完整交付或准确性通过。8181 调查概览、历史与固定结果页已核对保存来源。
- 原生固定 Run 的 Case 定位在该批返回 404，源码核明是冻结 HTTP 未注册新 Q34/Q35 路由；当时只切执行器，不能用通用 Run 详情替代该接口追认。当前完整 HTTP 源码已含依赖，仍须在整栈正式发布后核实际加载和同源读回。
- 4177 的新增最小报告已获负责人审阅脱敏与限定读取授权。统筹已核实际动态请求、同 Run/步骤目录、所选模型输入/输出及保存错误读取；私密离线归档与动态服务分开。只读首个配置页，工件目录未读全，没有浏览器视觉验收或额外模型调用。

原始运行回执及模型正文留在受控批次中，不随本次源码推送。代码/替身检查、真实 PG/HTTP 读回、浏览器显示和模型正文质量分别记录。

## 仍需保留的工作边界

| 项目 | 状态 |
| --- | --- |
| 事件输出精简 | 已完成 [结构审计与最小方案](openspec/changes/complete-socai2-investigation-chain/incident-output-structure-audit-20261128.md)，逐成员正文造成增长的原因已明确；提示、输出 Schema 和装配仍未实施，不混入当前发布。 |
| 完整线上组合 | main 整合与本地检查不能替代普通平台 POST、Q34/Q35、全部页面字段及实际容器加载验收。发布时按最终同版完整包核对，保留已知 404 和旧失败。 |
| 产品迁移剩余项 | 保留主线正式结果采用预览及令牌流程，本轮没有追加真实采用写入。部分引用/响应/附件与图的交互按 [逐页对照](openspec/changes/complete-socai2-investigation-chain/case-detail-4173-8181-comparison-20261126.md)、[当前问题](docs/investigation/current-issues.md)保持各自已验/未验口径；Case AI 写入仍为保留接口，G1 图保持只读，不以本次提交核销整个页面或 change。 |
| 后续模型与数据功能 | 事件输出方案、按环节提取/向量查询、两轮多行为数据、知识适用与后轮影响等依原任务推进。已决定后置的模型正文质量不追加采样追认；程序阻断继续按实际问题修复。 |
| OpenSpec 收口 | `complete-socai2-investigation-chain`、流式范围及内部可信 HTTP 仍保留未完成任务。本批是负责人明确要求的完整源码阶段交付，不归档未完成的 change。 |

后续部署：以两个远端 main 的实际回执及父项目 gitlink 固定源码，按手册绑定镜像与配置，再进行对应线上切换与直接读回。源代码推送与线上部署回执分别报告，不能用本地构建通过代替实际服务加载验收。
