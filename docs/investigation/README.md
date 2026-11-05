# 当前调查模块

当前分支为 `codex/case-baseline-history-20261103`。2026-11-05当前进度：19/26项完成；本机累计48/50次模型尝试。C6已不依赖C3成功，并将案件业务判断与执行原因分字段保存；g首轮及新增三组案例均形成模型Case判断，原页面可回查。三组新增15次DeepSeek，最终均accepted/partial/uncertain；03有事实扩大，模型质量不通过。H后容量、知识实际消费、语义约束、完整页面闭环、远端模型对照及结束审计仍待。用户已授权提交推送到origin/codex/case-baseline-history-20261103；不部署、不归档、不核销旧失败。

[修改与后续评审记录](design-audit-and-scenario-evaluation-20261105.md#9-实施变更与后续评审记录2026-11-05提交快照)汇总本次提交内容、实际验证和R1—R8待修项；[OpenSpec任务](../../openspec/changes/complete-socai2-investigation-chain/tasks.md)保留逐项完成状态。第1—8节是最初只读审计，不能代替随后实施状态。

当前采用本机专属PG/ClickHouse/Kafka/Redis/ZooKeeper与API/Fusion，常态DeepSeek直连；远端模型只在VPN窗口确认地址、认证和协议后切换，数据和页面全程留本机。旧采集/UEBA等后台已停止，历史数据保留。知识沿告警标题→PG全文检索，图/向量/Embedding非本阶段前提。

用户要求先做功能闭环、后端保持简单，所以当前页面以数据库及工件的真实导出呈现原模板。Case背景、当前判断、原始材料、A/I/C历史、图谱和失败分别读取对应记录；导出可读不表示所有页面保存动作已接通。Q仍501，Case手动单活跃；新完整C保持48000保守单位、4模型/4工具/120秒，旧Run不回写。

按以下顺序阅读：

1. [当前执行账本](current-execution-ledger.md)：Kafka/Fusion→A→I→Case C1—C6→H的输入、处理、输出与写表。
2. [本机执行计划和最新结果](../../openspec/changes/complete-socai2-investigation-chain/local-first-validation-plan-20261105.md)：真实批次、模型额度、环境与复验边界。
3. [三组案例比对](../operations/evidence/investigation-repair-20261105/local-comparison-summary.json)和[收尾/字段修复回执](../operations/evidence/investigation-repair-20261105/local-c6-business-fields-summary.json)：按各自取数时点读取，保留失败和原答。
4. [主设计](../architecture/investigation-planning-design.md)、[当前产品需求](../design/alert-incident-case-product-requirements.md)、[字段字典](../design/socai2-field-dictionary-20261103.md)与[OpenAPI](../design/socai2-independent-api-v2.openapi.json)。
5. [只读查账SQL](current-execution-readback.sql)、[历史写入目录](current-database-write-catalog.md)与[历史执行索引](current-execution-records.md)：目录及源指纹属于各自固定快照，不冒称本次全量刷新。

[最初审计修复记录](current-investigation-audit-20261105.md)、n15/125、旧k5权限失败和k6未派发按各自回执保留。a/b/c及g第二轮失败未重派；私密运行原件留本地，远端提交包含非敏感回执和可直接打开的合成案例页面数据。此前“未提交/未推送”仅是当时状态，最终以Git及远端核对为准。
