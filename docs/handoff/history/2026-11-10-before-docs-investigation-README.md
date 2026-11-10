> 此文件保存 2026-11-10 整理前的过程快照，仅供追溯。当前说明见仓库入口。

# 当前调查模块

当前21为v1.2-20261108-r5，A/I正式接入、无Case新批与历史参照见[2026-11-08部署及数据分析](../../investigation/ai-production-rollout-20261108.md)：3A/1I、51GET/1,910项核对通过，完整/失败/部分分开，正文质量独立记录。后续 [C3 同材料对照](../../../openspec/changes/complete-socai2-investigation-chain/case-model-comparison-20261108.md)已完成获准的两次独立生成：输入 −6.41%，总用量 +5.23%，两版质量未过；没有新建业务 Case 或切换生产流程。

当前 Case 推进见 [C1/C3 本地接入](../../../openspec/changes/complete-socai2-investigation-chain/case-boundary-integration-20261109.md)及 [Deep/C6 交接设计与离线核对](../../../openspec/changes/complete-socai2-investigation-chain/case-followup-handoff-20261109.md)。Deep/C6 业务接入、完整联跑和远端部署尚未完成；状态入口为根目录 [PROGRESS.md](../../../PROGRESS.md)。

逐项审阅模型职责、实际输入、完整输出字段及原答：[每个模型环节的输入与输出](../../investigation/model-input-output-current-20261109.md)。

**此前r1（2026-11-08）：** 原批7模型完成至C6，Case completed/partial、model/uncertain结果和3条证据目录有值；161GET及4177核对通过。原记录保持，查询正文错误未核销。[原批汇总](../../operations/evidence/production-multialert-20261108-01/summary.json) · [剩余问题](../../operations/evidence/production-multialert-20261108-01/problems.json) · [交接8.4](../../../FRONTEND_BACKEND_HANDOFF.md#84-12-续修后的有值结果与读取2026-11-08)。下段是1.2开始前的规划快照。

**下一轮修复版本为 1.2（2026-11-07，仅规划）：** [统一修复计划](../../../openspec/changes/complete-socai2-investigation-chain/design.md#v12-修复计划2026-11-07待实施)合并此前引用/领域/工具/容量/时限讨论与正式库最新问题，给出 12 项修复、M0—M4 顺序及验收。重点是调查产生可靠结果、DB 正确保存与请求能取回；前端跳转不作本版门槛。已修两函数权限作为回归，资产读取、非空负责人、归并依据、证据目录生产等分别处理。`inv-review.md` 的自动更新和资源队列等后置，未启动实现或新实验。下文按日期保留历史环境/任务与证据，不覆盖本次版本范围。

**前后端联调第一版**（`frontend-backend-integration-v1`）的[交付入口](../../../deliverables/investigation-validation-20261106/README.md)汇总了[服务端数据交接](../../investigation/socai2-page-data-handoff-20261106.md)、[页面功能与跳转清单](../../../deliverables/investigation-validation-20261106/frontend-feature-list.md)和可离线验收的案例。

[四案数据交接清单](../../investigation/investigation-test-handoff-20261106.md#下一阶段的前后端交接验收)列出告警、事件和 Case 的实际存值、失败记录及尚未产生的对象。原页显示差异另列供接手方参考。[本机预览](http://127.0.0.1:4176/) · [可离线查看的四案包](../../../deliverables/investigation-validation-20261106/21-qwen9b-handoff-cases-20261106.zip)

前后端从[告警、事件、调查三个原页面入口](../../investigation/investigation-test-handoff-20261106.md#前后端联调从这里开始)并行联调。01 案分别提供告警详情及原件、事件详情及成员、独立调查 Run 及其结果和关系图；四个字段样例补充 Case 管理字段、证据有值、零与未记录。

[21 内网小模型实测](../../investigation/investigation-test-handoff-20261106.md#21-内网小模型实测)已完成一案。Qwen3.5-9B 的两条告警分诊和一次事件诊断均已发布；Case 调查在调用前因必需事件诊断超出输入视图剩余空间而停止，保留系统结果与关系图。两种运行状态可与 DeepSeek 三案配合联调，实际响应与预览见[交接包](../../../deliverables/investigation-validation-20261106/README.md)。

用户已明确要求将本轮修改、测试及字段清单提交到`origin/codex/case-baseline-history-20261103`。统一[提交范围、剩余问题及下轮部署模型计划](../../../openspec/changes/complete-socai2-investigation-chain/publication-20261106.md)；完整已核验材料可从仓库内[交接包入口](../../../deliverables/investigation-validation-20261106/README.md)下载。下文及包内未提交/未上传字段均是各批原快照，以Git实际发布为准。

最新[测试总表与前后端数据交接](../../investigation/investigation-test-handoff-20261106.md)：11月6日追加三案/15次DeepSeek，三案C6均保存；48次只读GET、674项比较、557项页面数据检查/87视图通过，F01—F28列字段/关系/读取/页面及未实现边界。两C3拒收、各案语义扩大保留，模型质量未通过。本机累计63/69，13个本机模型批次和4个无模型数据合同样例分别归档；部署模型留下一轮。原模板仅追加数据，19/26保持；下文48/50和未重启API为前批时点。

[限定结束审计](../../../openspec/changes/complete-socai2-investigation-chain/additional-validation-review-20261106.md)已ACCEPT、0剩余必须修，仅限测试证据与数据交接。可携带ZIP在`.local/local-investigation/handoff-20261106/socai2-investigation-tests-20261106.zip`，1272文件/约10MB，CRC与逐文件SHA通过，见[打包回执](../../operations/evidence/additional-tests-20261106/package-receipt.json)；含13本机批次全部导出、4合同样例、原页面、固定候选和交接合同，不含运行凭据、不自动部署。

最新[数据优先推进方案](../../../openspec/changes/complete-socai2-investigation-chain/design.md#页面数据合同优先推进2026-11-06)：先补Case分类/截止时间，判定复用当前判断；证据索引复用现有工件表并明确版本、来源、条目与威胁计数。按[DA01—DA06](../../../openspec/changes/complete-socai2-investigation-chain/acceptance-plan-20261104.md#页面数据合同验收da01da06)单独交接数据，其他页面可并行对接；模型质量及VPN不是这部分前提。126迁移、读取/导出及必要字段绑定已完成，本机29表462列；最新[数据交接与样例](../../investigation/socai2-page-data-handoff-20261106.md)。原布局不改，模型/完整流程任务未核销。

[2026-11-06页面数据覆盖核对](../../../openspec/changes/complete-socai2-investigation-chain/page-data-coverage-20261106.md)：按用户最新口径只核数据承载，实际29表459列及七类来源关联支持主链继续推进。Case分类、Case截止时间需补存储；判定/关联威胁及独立证据口径需固定。当前样例空值和后续流程修改不算数据库设计阻塞，本轮未改DDL或页面。

[此前前后端对接评估](../../../openspec/changes/complete-socai2-investigation-chain/integration-assessment-20261106.md)保留接口接线等技术问题供后续处理，不作为本次数据层推进门槛。

后续推进已纳入[现有OpenSpec设计](../../../openspec/changes/complete-socai2-investigation-chain/design.md)与[验收矩阵](../../../openspec/changes/complete-socai2-investigation-chain/acceptance-plan-20261104.md)：先事实/效果约束和H容量，再知识/引用/领域及真实新批、原模板回查、远端配对。此轮是规划，未实施或新增模型；当前任务完成数保持。

当前分支为 `codex/case-baseline-history-20261103`。2026-11-05当前进度：19/26项完成；本机累计48/50次模型尝试。C6已不依赖C3成功，并将案件业务判断与执行原因分字段保存；g首轮及新增三组案例均形成模型Case判断，原页面可回查。三组新增15次DeepSeek，最终均accepted/partial/uncertain；03有事实扩大，模型质量不通过。H后容量、知识实际消费、语义约束、完整页面闭环、远端模型对照及结束审计仍待。用户已授权提交推送到origin/codex/case-baseline-history-20261103；不部署、不归档、不核销旧失败。

[修改与后续评审记录](../../investigation/design-audit-and-scenario-evaluation-20261105.md#9-实施变更与后续评审记录2026-11-05提交快照)汇总本次提交内容、实际验证和R1—R8待修项；[OpenSpec任务](../../../openspec/changes/complete-socai2-investigation-chain/tasks.md)保留逐项完成状态。第1—8节是最初只读审计，不能代替随后实施状态。

当前采用本机专属PG/ClickHouse/Kafka/Redis/ZooKeeper与API/Fusion，常态DeepSeek直连；远端模型只在VPN窗口确认地址、认证和协议后切换，数据和页面全程留本机。旧采集/UEBA等后台已停止，历史数据保留。知识沿告警标题→PG全文检索，图/向量/Embedding非本阶段前提。

用户要求先做功能闭环、后端保持简单，所以当前页面以数据库及工件的真实导出呈现原模板。Case背景、当前判断、原始材料、A/I/C历史、图谱和失败分别读取对应记录；导出可读不表示所有页面保存动作已接通。Q仍501，Case手动单活跃；新完整C保持48000保守单位、4模型/4工具/120秒，旧Run不回写。

按以下顺序阅读：

1. [当前执行账本](../../investigation/current-execution-ledger.md)：Kafka/Fusion→A→I→Case C1—C6→H的输入、处理、输出与写表。
2. [本机执行计划和最新结果](../../../openspec/changes/complete-socai2-investigation-chain/local-first-validation-plan-20261105.md)：真实批次、模型额度、环境与复验边界。
3. [三组案例比对](../../operations/evidence/investigation-repair-20261105/local-comparison-summary.json)和[收尾/字段修复回执](../../operations/evidence/investigation-repair-20261105/local-c6-business-fields-summary.json)：按各自取数时点读取，保留失败和原答。
4. [主设计](../../architecture/investigation-planning-design.md)、[当前产品需求](../../design/alert-incident-case-product-requirements.md)、[字段字典](../../design/socai2-field-dictionary-20261103.md)与[OpenAPI](../../design/socai2-independent-api-v2.openapi.json)。
5. [只读查账SQL](../../investigation/current-execution-readback.sql)、[历史写入目录](../../investigation/current-database-write-catalog.md)与[历史执行索引](../../investigation/current-execution-records.md)：目录及源指纹属于各自固定快照，不冒称本次全量刷新。

[最初审计修复记录](../../investigation/current-investigation-audit-20261105.md)、n15/125、旧k5权限失败和k6未派发按各自回执保留。a/b/c及g第二轮失败未重派；私密运行原件留本地，远端提交包含非敏感回执和可直接打开的合成案例页面数据。此前“未提交/未推送”仅是当时状态，最终以Git及远端核对为准。
