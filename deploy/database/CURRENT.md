# 当前调查数据库入口

21 正式 `aisoc.socai2` 已应用 130–136。135 时读回 **35 张表、566 列**，136 更新事件初始化函数和入站列接线。正式湖表沿 005 为 62 列。[135 读回](../../docs/operations/evidence/c173-escalation-release-20261121-04/README.md) · [136 读回](../../docs/operations/evidence/c173-formal-alert-readback-20261123-01/README.md)

[11-16 r4 实际读回](../../docs/operations/evidence/streaming-release-20261116-04/deployment-ready.json)保留当时的发布证据。D1–D4c本轮未改结构、未重跑迁移；历史业务清理使用明确84表清单，Schema及127张未选表内容保持。基线[调查表职责](../../docs/investigation/investigation-table-scope.md)和[机器字典](../../docs/design/socai2-data-contract-current.json)须结合128/129增量阅读，不能拿旧28表450列记载否定当前实库。

128新增analysis_tasks/attempts/subject_state，129增加Case分配字段及排除表，规格见[存储设计](../../openspec/changes/schedule-streaming-investigation-updates/storage-and-runtime-design-20261114.md)。独立候选socai2_streaming_20261115及本机v12_upgrade_dev已有各自32/521验证；本机其他旧库本轮未操作。资产、用户和租户沿业务后端基础数据。
## 湖告警持久交付增量131的早期验收

2026-11-19新增`lake_alert_deliveries`和`lake_alert_delivery_attempts`，共2表25列；持久保存选择去向、待处理状态、精确湖引用及逐次接收结果。确认delivered需关联130的已提交来源回执及告警材料；失败/unknown尝试不改写，恢复另记。该增量不改变V1或公开告警字段。

已有目标先有130，再运行`install_reader.py lake-alert-deliveries --profile <显式配置>`，使用[lake_alert_deliveries.sql](lake_alert_deliveries.sql)。沿`analysis`及`analysis_ingress`配置，入口获得功能所需SELECT/INSERT/UPDATE，reader只读。当前新装在选择analysis_ingress时使用同一130/131，verify按账本增计；未应用131的库仍核原计数。本批独立PG已通过新装、重复增量及reader verify，清理后当前基线加130/131为35表556列；冻结V1另有保留表，不混用计数。该早期验收时正式库为 123–129。[运行配置](../aisoc21/lake-alert-delivery-4c/README.md)及[直接回执](../../docs/operations/evidence/lake-alert-delivery-4c-20261119-01/README.md)不代表正式消费者已启用。

## 湖告警回执增量130的早期验收

2026-11-19新增内部`lake_alert_receipts`，全局来源ID对应首次告警、完整材料及冻结湖引用；与既有告警/材料/初诊登记同事务提交。不修改V1原件、告警字段或HTTP合同。该候选批次的数据库状态沿原回执保留，正式库以页首版本为准。

`install_reader.py lake-alert-receipts --profile <显式配置>`复用[lake_alert_receipts.sql](lake_alert_receipts.sql)。需既有128及`analysis`/`analysis_ingress`配置，给入口角色SELECT/INSERT、reader SELECT；回执不可更新/删除，保留租户隔离。新装current入口在配置analysis_ingress时包含同一130，verify按迁移账本增加1表10列，保留未应用130库的旧计数。03隔离批验证新装、重复增量及只读verify；[接收证据](../../docs/operations/evidence/lake-alert-receive-4b-20261119-03/README.md)与[运行配置](../aisoc21/lake-alert-receive-4b/README.md)分别说明实际范围。

## 正式增量 130–136

升级已有库时，通过 `install_reader.py <子命令> --profile <选定配置>` 应用缺少的增量。21 已应用并读回以下增量。

| 增量 | 安装子命令 | 用途和脚本 |
| --- | --- | --- |
| 130 | `lake-alert-receipts` | [湖告警接收回执](lake_alert_receipts.sql) |
| 131 | `lake-alert-deliveries` | [湖告警持久交付](lake_alert_deliveries.sql) |
| 132 | `subject-risk` | [事件与 Case 风险与人工优先级](subject_risk.sql) |
| 133 | `analysis-task-times` | [任务与尝试入队及时间字段](analysis_task_times.sql) |
| 134 | `business-verdict` | [事件诊断与 Case 结果业务判定](business_verdict.sql) |
| 135 | `run-escalation-decision` | [调查运行不升级决定](run_escalation_decision.sql) |
| 136 | `subject-risk` | [告警入站事件风险初始化](../../services/api/migrations/136_socai2_subject_risk_ingress.sql) |

## 任务生命周期增量128

部署连接按负责人2026-11-15确认简化为普通账号密码；[当前安装模板](reader-install.example.toml)默认`PGSSLMODE=require`，没有客户端CA/证书/私钥字段，密码仍由受控`PGPASSFILE`提供。安装器不再接受旧PGSSLROOTCERT配置；已有历史profile原件不改写，目标部署使用当前模板。具体参数及认证/服务端TLS区别见[数据库部署说明](../../docs/operations/deployment-datastores.md)。本轮没有修改21 HBA、角色密码或重启数据库。

`install_reader.py analysis-lifecycle --profile <显式配置>`复用[同一SQL入口](analysis_lifecycle.sql)，新增analysis_tasks、analysis_attempts、analysis_subject_state，以及对应真实引用、不可改历史、同主体实际执行唯一约束。baseline活动唯一索引改为running；原unknown Run和其NULL ended_at不改写。此入口不执行127清理、不创建历史task、不启消费者。已有库运行此增量；不能对已有库运行空库初始化。

profile沿原连接配置，另需`[analysis]`下的`writer_role`、`lock_timeout_seconds`、`statement_timeout_seconds`，见[示例](reader-install.example.toml)。writer为已有调查处理角色，reader仅授予新表SELECT。先应用增量，再加载依赖这三张表的核心/HTTP代码；重试与周期参数另走运行[配置](../local-investigation/analysis-tasks.json)。128已随此前正式发布应用，当前r4仅核既有结构，不重复执行。

## Case分配增量129

`install_reader.py case-allocation --profile <显式配置>`复用[同一SQL入口](case_allocation.sql)。cases增量3个续建字段、incidents增加active_case_id，新建6列case_alert_exclusions；同租户外键及接收者实际关联约束保持。仅对新案保存root，不回填/识别旧对象，不修改旧Run或既有告警合同。

沿`[analysis]`配置选择已有writer/reader和超时；新表writer获得SELECT/INSERT/UPDATE/DELETE，reader仅SELECT。依赖128先应用，随后加载[Case分配配置及核心](../local-investigation/case-allocation.md)。本机隔离库升级、重复应用和只读verify通过；新空库入口已同步并离线核同一增量，未新建空库测试。129已随此前正式发布应用，当前实库以页首读回为准。

## 已有调查库

以下是历史127迁移的适用条件，不是本次r4待执行操作：仅删除 `socai2.graph_explorations`。先部署 28 表查询适配，再使用[受限增量入口](remove_unused_graph_table.sql)，显式传入 `expected_database`、`cleanup_lock_timeout` 和 `cleanup_statement_timeout`。脚本锁表后核空、核创建结构与依赖，使用 `DROP ... RESTRICT`，任何不符均回滚；不清空数据、不删其他表。迁移 127 要求显式目标，不通过未传此配置的通用全量迁移器执行。

已有 reader profile 可配置下列节，使用 `install_reader.py remove-unused-graph --profile <选定配置>`；普通 `upgrade` 不自动删表。

```toml
[cleanup]
lock_timeout_seconds = 3
statement_timeout_seconds = 30
```

目标连接、管理员、reader 和总时限沿既有 profile；凭据不写在命令行。[配置示例](reader-install.example.toml)保留普通安装用法，清理节仅供显式选择新入口时加入。

## 新独立空库

2026-11-15已在21新候选库`socai2_streaming_20261115`实际执行当时的新装入口，覆盖 123–129、32表521列及reader verify通过，普通reader/writer和基础tenant/actor就绪，业务记录为0。详见[供给回执](../../docs/operations/evidence/streaming-candidate-20261115-01/database-prepare-01.json)。该证据对应当时的独立候选，正式库以页首版本为准。

- [init_socai2_current.sql](init_socai2_current.sql)：先检查显式目标，再应用冻结V1和127/128/129/132/133/134增量。显式配置analysis_ingress时另包含130/131。
- [init_socai2_current_reader.sql](init_socai2_current_reader.sql)：增加既有V1.2 reader依赖。使用`install_reader.py initialize-current --profile <选定配置>`，需cleanup和analysis两节及显式owner/reader/writer。128/129已验证升级及重复应用，本次21候选完整初始化亦已通过。

这些独立运行入口复用 V1 的公共依赖支撑结构，仅用于新专用空库；它们不是业务后端的公共建表清单。共享业务库必须沿现有安装及后端提供的基础数据接入，不能运行空库初始化。

## 核验与实际交付

使用 `install_reader.py verify --profile <选定配置>` 按各环境的增量账本核基线、计数及 reader 读取。旧 `install_aisoc21_v1.py verify` 及冻结 V1 自检适用于未清理基线。

当前reader公共查找包含`assets`、`users`及`aisoc_kb_documents`的SELECT。Case来源验收发现候选reader缺知识表读取，已通过同一[公共查找安装片段](reader_public_lookups_20261107.sql)补齐并同步verify；新装/升级继续复用此片段。该回执只证明当时候选读接线；正式当前连接与结构见本轮发布读回；无新表/业务字段/RLS或写权变化，见[读接线回执](../../docs/operations/evidence/streaming-case-20261115-01/knowledge-reader-access-01.json)。

127的既有交付范围包括21 `aisoc`、本机`v12_upgrade_dev`与`socai2_local_20261105`；这不表示三处均应用了128。其他开发者表、公共表、历史验收库及原业务数据保留。[127清理回执](../../docs/operations/evidence/graph-table-cleanup-20261112-01/delivery-summary.json) · [工作台实际装载与读取](../../docs/operations/evidence/graph-table-cleanup-20261112-01/workbench-after-cleanup.json)。

## 原生Fusion公共支撑

专用调查库完成`initialize-current`后，以同一显式profile运行`install_reader.py fusion-support --profile <配置>`，补齐正常Fusion入口所需`public.sessions`、`public.aisoc_dead_letters`和`public.aisoc_ai_assets`。已有目标库也使用同一支撑入口；须已存在tenant、当前调查表及普通入口角色。

[支撑SQL](fusion_public_support_20261115.sql)引用053/102会话部分/110的现有表定义并记源摘要，保留原迁移；不执行102对旧`public.alerts`的扩展，不创建旧告警库或登记全平台迁移已完成，不修改socai2的32表521列。`[analysis_ingress]`沿现有`role`、`lock_timeout_seconds`、`statement_timeout_seconds`三项必填，角色需普通读写身份；owner、reader及目标库沿原profile。三表仅授予所选入口和reader必要权限；reader另获public.connectors只读以核对实际来源身份。最终脚本不改变其他既有角色授权。

21候选实际安装及普通账号回滚写读记录在[本轮入站证据](../../docs/operations/evidence/streaming-ingress-20261115-01/README.md)。此安装不启模型或投消息；当前r4已分阶段发布，新批完整链验收与整个change结束审计分别跟进。

## 事件/Case 属性候选 132（2026-11-20）

S1 增量新增 Incident 的 severity/severity_source/risk_metadata 与 Case 的 risk_metadata，共四列、无新表；不回填旧行，冻结 V1 不改。两个 current 新装入口和 `install_reader.py subject-risk --profile <显式配置>` 复用 [subject_risk.sql](subject_risk.sql)，verify 按 132 账本增加四列。调查 writer 与已配置的 analysis_ingress.role 使用同一事务内初始化函数，reader 仍只读。运行配置及统一交付见[候选清单](../local-investigation/subject-risk-release-fragment.json)。该步骤不表示正式 aisoc 已应用 132，S2/S3 管理闭环完成后随 change 发布。

## 任务时间候选 133（2026-11-20）

S5 为 analysis_tasks 增加 first_enqueued_at、next_attempt_enqueued_at，为 analysis_attempts 增加 enqueued_at，共三列、无新表，均为可空 timestamptz，不回填旧任务。已有 last_enqueued_at 保留最近确认入队历史。严格准备检查例外只允许指定 skipped 原因的无 Run 尝试本地结束，不进入正常分析完成指针或刷新自动窗口。

两个 current 新装入口和 `install_reader.py analysis-task-times --profile <显式配置>` 复用 [analysis_task_times.sql](analysis_task_times.sql)；verify 按 133 账本增加三列并核类型/可空。继续使用既有 analysis 配置的锁/语句时限，不新增环境默认。先迁移再加载新 ORM/调度/HTTP，统一交付见[候选清单](../local-investigation/analysis-task-times-release-fragment.json)。本轮为隔离验证，正式库未应用 133；验收结果及后续统一发布以当前进展为准。

## 业务判定候选 134（2026-11-20）

`incident_diagnoses.business_verdict` 和 `results.business_verdict` 为可空文本。约束仅允许已完成事件诊断或已接受模型结论保存约定的四种判定。旧行以 `null` 读取。Case 当前判定沿采用来源读取 Result，无第二份存储。

两个 current 新装入口与 `install_reader.py business-verdict --profile <显式配置>` 共用 [business_verdict.sql](business_verdict.sql)，使用现有分析迁移时限。最终验收时先校验数据库目标和应用 134，再装载读取这两列的调查服务和 HTTP 版本。[统一交付清单](../local-investigation/subject-business-verdict-release-fragment.json)

## 未升级调查 135

`socai2.runs.escalation_decision` 是可空文本列。数据库约束允许完整结束的自动告警分诊保存 `not_escalated`。已有记录保持空值。两个 current 新装入口复用本增量。升级用 `install_reader.py run-escalation-decision --profile <显式配置>`，再执行 `verify` 核对同一数据库。[迁移入口](run_escalation_decision.sql) · [接口合同](../../docs/integration/run-directory-http.md#未升级调查)

## 正式告警入站初始化 136

现有 `install_reader.py subject-risk --profile <显式配置>` 和两个 current 新装入口复用 [136](../../services/api/migrations/136_socai2_subject_risk_ingress.sql)。已有库使用 132 的迁移账本识别此前结构。136 按主体读取成员，并沿 profile 的 `analysis_ingress.role` 接通 Fusion 初始化所需的事件等级与优先级列。21 已应用 136，已用在运 Fusion 和 HTTP 通过真实小批保存、同 ID 详情及原文读回。[正式联验回执](../../docs/operations/evidence/c173-formal-alert-readback-20261123-01/README.md) · [隔离 Case 回归](../../docs/operations/evidence/c173-alert-readback-20261123-01/README.md)
