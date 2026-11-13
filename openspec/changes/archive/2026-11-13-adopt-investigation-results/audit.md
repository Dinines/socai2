# 独立结束审计

审计者：未参与本轮核心、HTTP、Swagger 或部署实现的独立审计代理。日期：2026-11-13。

## 发布前限定结论

**通过本批代码、合同、文档和本机冻结候选验收审查，可继续按既定范围统一发布。** 本结论不表示两端正式服务或 Swagger 已更新；发布后仍须核对实际运行版本、七文件摘要、数据读回和 Swagger 载荷，之后才能完成任务 1.5 与归档。审计未发出业务 HTTP、数据库或模型请求，未实施部署。

审查范围为 E21 采用已有结果、E63 采用预览、E64 判断历史及其七个运行文件；其他 61 操作保持。采用后的判断保留结果来源、实际操作人及理由，不执行模型，不结束人工任务、取消 Run 或改变 Case 处理状态。无迁移、附件、问答、自动调查或并行模型改动进入本批结论。

## 核心、HTTP 与存取核对

1. 复用[核心独立审计](../../../../docs/operations/evidence/case-result-adoption-20261113-01/audit.md)，并核对 `case_adoption.py`、`case_adoption_contracts.py`、`case_service.py` 与该批 `after-source/` 原件逐字一致。核心的整案/成员覆盖/输入新鲜度资格、未完工作确认、旧 Run 与后续自动判断时序等已有直接证据继续适用；不重复运行模型或数据库批次。
2. HTTP 路由仅通过 `CaseOperations` 与 DTO 接入核心，未直接编排模型或泄露数据库会话。新请求使用 `expected_review_token`、非空理由和必要确认；旧 E21 占位请求的 `expected_scope_revision` 返回 422。预览变化、未确认未完工作、同操作键异意图均为 409；历史按判断版本倒序分页，不把历史的保存状态当作当前输入新鲜度。
3. 审计独立运行 `test_socai2_case_ai_reserved.py` 和 `test_socai2_http_boundary.py`：**6 tests、12 subtests 通过**；`openspec validate adopt-investigation-results --strict --no-interactive` 通过。没有扩展全仓回归或新业务写入。
4. 逐项核对[原 HTTP 验收](../../../../docs/operations/evidence/case-result-adoption-http-20261113-01/http-01/verification.json)的 20 次原始请求与前后 SQL：采用新建 revision 2 判断、来源、成员覆盖和采用活动；Case 指针及版本与六字段回执一致；同键重放返回原回执，异意图未新增判断。预览摘要可由响应重算；历史响应与已保存判断、来源、覆盖及原 Result 对齐。原 Result、任务及修订、Run 及成员、工件在采用前后保持一致。该批是全工作树本机服务验收，不能单独证明发布包隔离。
5. 随后独立比对普通目录中的附件版运行基底与本批冻结候选：实际差异恰为 `aisoc21.json` 列出的七文件，且仓库源码、候选和[冻结清单](../../../../docs/operations/evidence/case-result-adoption-release-20261113-01/local-source-manifest.json)摘要一致，基底其他文件保持。候选目录为 `../socai2-http-runtime/case-result-adoption-20261113-r1`，预览 profile 使用 18026、`v12_upgrade_dev`。
6. 核对[冻结候选验收](../../../../docs/operations/evidence/case-result-adoption-release-20261113-01/local-candidate/verification.json)及原文：另一个独立合成 Case 完成 20 次真实 TCP HTTP 和 PostgreSQL 保存/读取。最终为 1 Case、2 Run、1 Result、2 判断及各自来源/覆盖、1 任务/修订；采用前后任务、Run、Result 和工件保持一致。SQL 快照记录一次只读一致性快照，摘要与清单一致。程序构造 Result 不构成模型分析质量证据。

## 文档和合同

核对 docs13 候选的 64 操作、139 Schema、655 固定字段位置、35 动态结构以及告警/事件/调查三类的 125 功能。E01–E62 原编号保留，E21由预留变为实现，E63/E64追加；当前为 62 已实现、E19/E20 两个预留。除 E21 外原 61 操作及原有引用模型保持，新 DTO、请求与成功响应结构和真实候选 OpenAPI 对齐。562 个 JSON 响应例、3 个 CSV 例通过 Schema 检查；示例明确为合成合同示例。

最初发现候选 README/guide 仍保留 docs12、62 操作及 E21 501 旧说明，已反馈并复核修正。现指南说明预览、确认、保存、详情/历史/活动读取顺序、旧请求不兼容、幂等重试和冲突处理；区分模型来源与人工采用、保存有效性与模型质量、历史判断与当前新鲜度。候选文字注明实际发布状态以回执和总交接为准。发布前文档阻断已清零。

## 尚需发布后核对

- 两端正式 18024 加载的本批版本、冻结七文件与旧基底；不将并行模型代码带入。
- 正式读回证据所支持的实际范围，保留失败原文，不用候选成功替代正式观测。本机可核既有本批 SQL；21采用既有对象的只读 HTTP、源码与版本核验，不新增正式库写验证。
- 两端 docs13 各入口与仓库交接包的摘要、操作数和实现状态一致，根入口更新为实际发布事实。

主调查 31/41、模型正文质量 `NOT_PASSED` 及其他聊天未完事项不由本次程序功能审计核销。本结论不授权额外业务范围或其他服务发布。

已核[审批边界](../../../../docs/operations/evidence/case-result-adoption-release-20261113-01/approval-boundary.json)：导出生产数据库连接与创建生产合成验收数据被自动审批拒绝，均未执行。调整为本机写入闭环、21只读核验符合本次限定结论；生产写验证不是额外发布前置，最终报告需明确其未实测。

## 发布后限定结束审计

2026-11-13 复核结论：**通过，无本批未解决阻断；可以完成任务 1.5 并按 OpenSpec 收口归档。** 这是对 E21/E63/E64 的程序功能、本机存取闭环、两端部署与生产只读接线的限定结论，不代表生产采用写入或真实模型质量实测通过。此次审计只读本地源码、冻结包和保存的发布证据，未新增业务 HTTP、数据库、模型调用或部署。

### 实际部署与读取

- [本机发布](../../../../docs/operations/evidence/case-result-adoption-release-20261113-01/local-release.json)为 `case-result-adoption-20261113-r1-local`，18024、`v12_upgrade_dev`、PID 95878；正式入口[7 次 GET](../../../../docs/operations/evidence/case-result-adoption-release-20261113-01/local-release-readback.json)读取冻结候选的同一 Case，返回当前判断 `292edf95-ff84-4974-ac29-b6fa1c9288c3`、两版历史、原任务 `not_started` 与 Run `pending_update`。身份和状态与此前真实 HTTP/SQL 保存一致。此阶段没有重做写入，也没有新增 SQL 实测的宣称。
- [21 运行核对](../../../../docs/operations/evidence/case-result-adoption-release-20261113-01/21-runtime.json)为 `case-result-adoption-20261113-r1`，18024、`aisoc`、镜像 `sha256:056c29bf8714018df5543cecad4a371b38c2ada3f0d510bfce8fc885eb35a42a`；入口仍为 `investigation_http.main:app`。审计再次对比仓库七文件、本机普通目录运行包、冻结清单与 21 容器采集摘要，全部一致。根 `local.json`、`aisoc21.json` 与本批 profile 一致，原基底之外没有引入并行模型文件。
- 21 的[6 次 GET](../../../../docs/operations/evidence/case-result-adoption-release-20261113-01/21-readback.json)只读既有 Case、当前判断、历史及采用预览，三个身份关联一致，64 操作挂载；未提交采用或创建生产合成业务数据。审查采集脚本的实际断言和业务调用方式与回执一致。首次读取脚本从列表封套根层取字段失败，保留 `21-readback-initial.json`；修正为 `item.case` 后完成只读核对，业务合同未修改。
- 运行核对脚本比较发布前后其他容器的 ID、镜像和启动时间；回执确认除本批 API/Swagger 外的 36 个容器保持。本批迁移、模型调用和生产业务写入均为零。

### Swagger 与交接

两端 docs13 的 9 个入口均 200、逐入口摘要相同；本机为 aarch64、21 为 x86_64。审计独立核对其中 8 个交接载荷与仓库包、本机实际挂载包和发布清单一致，并核对发布清单全部 29 文件与仓库及挂载包一致。OpenAPI 摘要为 `af7edada2413bac859063fac4a0d9b78a8869d577a6b591d9456b95c3bd8d69a`；[固定回执](../../../../deploy/api-docs/deployment-receipt.json)与两端观察一致。64 操作、62 实现/2 预留、139 Schema、655 固定字段位置和 35 动态结构保持发布前核验结果。

根 README/交接、功能清单、实施计划及采用指南已说明当前部署和后端调用顺序，并保留生产写入未实测、模型质量未通过的限制。复核中发现根交接计数及部署 README 的 `expected_operations` 残留旧值，主执行者已分别改为 62 实现/2 预留与 64；复读确认。预定归档路径将在主执行者实际归档及链接校验时生效，不据链接提前宣称归档发生。

### 请求记录差异的处理

本批复制的验收驱动保留了可变请求对象引用；后续更换预览摘要使汇总 `responses.json` 中第 6 条输入被改动。审计逐条对比 20 份事前 intent 与汇总，确认**只有第 6 条输入不同**。`06-intent.json` 中摘要等于首次预览响应摘要，原响应仍是 409 `result_adoption_preview_changed`；[差异说明](../../../../docs/operations/evidence/case-result-adoption-release-20261113-01/request-reconciliation.json)准确列出原值和汇总值。已执行源代码保存在 `executed-source/verify_http.py`，旧汇总未改写；未来驱动的深拷贝修复不冒充当时实现，没有为修日志重跑业务。本审计以逐次原始 intent 作为实际输入依据，采用、重放和 SQL 对应结论不受该汇总缺陷影响。

发布前保留的核心审计和直接验收继续有效。主调查 31/41、模型正文质量 `NOT_PASSED`、同案助手 E19/E20 预留和其他未交付能力仍保持各自状态，本次不予核销。

## 归档记录

2026-11-13实际执行archive，新增主规格case-result-adoption-http。CLI初次封后检查指出自动生成Purpose占位，已补充能力目的并再次严格校验；这是规格说明修正，无业务/部署变化。归档相对证据链接已按新层级修正。
