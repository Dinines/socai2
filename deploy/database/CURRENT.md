# 当前调查数据库入口

2026-11-16，21正式aisoc已为 **32表、521列**（123–129），[本次r4实际读回](../../docs/operations/evidence/streaming-release-20261116-04/deployment-ready.json)再次确认。D1–D4c本轮未改结构、未重跑迁移；历史业务清理使用明确84表清单，Schema及127张未选表内容保持。基线[调查表职责](../../docs/investigation/investigation-table-scope.md)和[机器字典](../../docs/design/socai2-data-contract-current.json)须结合128/129增量阅读，不能拿旧28表450列记载否定当前实库。

128新增analysis_tasks/attempts/subject_state，129增加Case分配字段及排除表，规格见[存储设计](../../openspec/changes/schedule-streaming-investigation-updates/storage-and-runtime-design-20261114.md)。独立候选socai2_streaming_20261115及本机v12_upgrade_dev已有各自32/521验证；本机其他旧库本轮未操作。资产、用户和租户沿业务后端基础数据。
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

2026-11-15已在21新候选库`socai2_streaming_20261115`实际执行当前完整新装入口：123–129、32表521列及reader verify通过，普通reader/writer和基础tenant/actor就绪，业务记录为0。详见[供给回执](../../docs/operations/evidence/streaming-candidate-20261115-01/database-prepare-01.json)。这是当时独立候选的初始化证据；正式aisoc随后已应用128/129，当前不再停留127。

- [init_socai2_current.sql](init_socai2_current.sql)：先检查显式目标，再应用冻结V1、同一127/128/129增量。
- [init_socai2_current_reader.sql](init_socai2_current_reader.sql)：增加既有V1.2 reader依赖。使用`install_reader.py initialize-current --profile <选定配置>`，需cleanup和analysis两节及显式owner/reader/writer。128/129已验证升级及重复应用，本次21候选完整初始化亦已通过。

这些独立运行入口复用 V1 的公共依赖支撑结构，仅用于新专用空库；它们不是业务后端的公共建表清单。共享业务库必须沿现有安装及后端提供的基础数据接入，不能运行空库初始化。

## 核验与实际交付

使用`install_reader.py verify --profile <选定配置>`；它依据127/128/129账本核基线及增量计数（128增加3表61列，129增加1表10列），并核reader实际读权限。旧`install_aisoc21_v1.py verify`及冻结V1自检只适用于未清理基线，不能用来否定已完成增量的当前库。

当前reader公共查找包含`assets`、`users`及`aisoc_kb_documents`的SELECT。Case来源验收发现候选reader缺知识表读取，已通过同一[公共查找安装片段](reader_public_lookups_20261107.sql)补齐并同步verify；新装/升级继续复用此片段。该回执只证明当时候选读接线；正式当前连接与结构见本轮发布读回；无新表/业务字段/RLS或写权变化，见[读接线回执](../../docs/operations/evidence/streaming-case-20261115-01/knowledge-reader-access-01.json)。

127的既有交付范围包括21 `aisoc`、本机`v12_upgrade_dev`与`socai2_local_20261105`；这不表示三处均应用了128。其他开发者表、公共表、历史验收库及原业务数据保留。[127清理回执](../../docs/operations/evidence/graph-table-cleanup-20261112-01/delivery-summary.json) · [工作台实际装载与读取](../../docs/operations/evidence/graph-table-cleanup-20261112-01/workbench-after-cleanup.json)。

## 原生Fusion公共支撑

专用调查库完成`initialize-current`后，以同一显式profile运行`install_reader.py fusion-support --profile <配置>`，补齐正常Fusion入口所需`public.sessions`、`public.aisoc_dead_letters`和`public.aisoc_ai_assets`。已有目标库也使用同一支撑入口；须已存在tenant、当前调查表及普通入口角色。

[支撑SQL](fusion_public_support_20261115.sql)引用053/102会话部分/110的现有表定义并记源摘要，保留原迁移；不执行102对旧`public.alerts`的扩展，不创建旧告警库或登记全平台迁移已完成，不修改socai2的32表521列。`[analysis_ingress]`沿现有`role`、`lock_timeout_seconds`、`statement_timeout_seconds`三项必填，角色需普通读写身份；owner、reader及目标库沿原profile。三表仅授予所选入口和reader必要权限；reader另获public.connectors只读以核对实际来源身份。最终脚本不改变其他既有角色授权。

21候选实际安装及普通账号回滚写读记录在[本轮入站证据](../../docs/operations/evidence/streaming-ingress-20261115-01/README.md)。此安装不启模型或投消息；当前r4已分阶段发布，新批完整链验收与整个change结束审计分别跟进。
