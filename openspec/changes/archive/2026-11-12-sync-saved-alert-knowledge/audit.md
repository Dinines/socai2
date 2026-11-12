# 限定本地结束审计

2026-11-12。审计者未参与本 change 的代码实现；只读检查当前工作树、OpenSpec、交接和保存证据，独立写入本文。未运行测试、模型、数据库查询、网络、浏览器或部署，未读取私密 `.local`，未修改运行代码或无关 `tools/model-preflight/`。基线 `f993e630`，实际分支 `V1.1`。

**结论：本地功能限定通过（LOCAL_ACCEPTED），未发现本范围待修的实现阻断，可进入一次统一发布及直接读回。** 当前生产仍为 `v1.2-20261112-r3`；处理镜像已构建不代表本功能已上线。本审计不声明生产角色写入、自动同步、正式 4177、归档或 Git／父项目交付已完成。

## 提交、同步与状态边界

| 核对项 | 结论及依据 |
| --- | --- |
| 真实提交后接线 | `StageResultService.finish()` 在原 `transaction()` 退出后才调用 `after_triage()`；该事务由 `db.begin()` 管理，先保存判断、采用指针、publication 和 Run completed，再进行知识维护。外部嵌入／向量调用不持有原分诊事务或行锁，原 outcome 未增加字段。 |
| 触发范围 | 仅新 `alert_basic` 且 adopted、已配置知识 profile 并启用同步时触发。关闭、未采用、I 不写知识；原失败／unknown 路径不经成功 finish。已有 publication 的重复 finish 分支在 hook 前直接返回，保持原输出 hash 冲突检查，不给旧 Run 补派。Case H 不被冒充告警人工反馈。 |
| 独立会话与来源 | `knowledge_sync.session()` 每次独立设置事务级租户上下文；`import_cards()` 自行 commit 后，索引重新开会话，不复用已失效的 RLS 设置。先核最新 triage 为本次结果；导入时以完整卡片期望 hash 防止换源；索引沿既有当前源核验，完成后再次检查本次身份及卡片内容。源变化不被报告为当前可用，后续检索仍核最新来源。 |
| 配置与一次尝试 | `History` 类型缺省关闭，开启必须给正数总时限；所选待发布 profile 为开启／120 秒。固定的 Run＋phase 工件身份配合短事务锁保存意图；已有意图不重派。没有后台队列、重试循环、全库扫描或消费者启用。 |
| 独立回执 | 两份 `source_snapshot`／`socai2.history-sync.v1` 工件分别保存 intent 与 result，均引用真实 publication。storage、index、source_current 与总状态分开；索引前失败保留卡片并记失败，点写入结果不明保留 unknown，源变化记 skipped。总时限耗尽或结果工件写入失败可只留下意图，不能据 Run completed 或已有卡片推断同步成功，也不自动补派。原判断和采用状态不因同步失败回滚。 |

## 已有直接证据

[11 项检查回执](../../../../docs/operations/evidence/knowledge-sync-20261112-01/direct-tests.xml)记录 tests=11，failures／errors／skipped 均为 0。覆盖默认关闭及启用时限、关闭／未采用／I 不触发、同步成功、索引前失败与写入未确认、来源变化，以及复用的卡片资格／稳定身份／查询范围。异常状态是有限替身检查，不冒充真实生产故障演练；未扩展测试矩阵。

复核 [验收驱动](../../../../tools/testdata/knowledge_sync/run.py)及[流程汇总](../../../../docs/operations/evidence/knowledge-sync-20261112-01/local-flow/summary.json)：通过原 `StageResultService.begin()`／`finish()` 保存一份标记为 template 的判断，由提交后 hook 自动触发；没有直接调用同步 helper 替代接线，也没有调用分析模型。数据库为真实本地 `v12_upgrade_dev/v12_developer`，嵌入使用现有真实服务，Qdrant 为本批独立集合。

从 [保存快照](../../../../docs/operations/evidence/knowledge-sync-20261112-01/local-flow/readback/A01/database.json)和[同步结果](../../../../docs/operations/evidence/knowledge-sync-20261112-01/local-flow/sync-result.json)核对：

- 告警 `33e34ce6-6419-5505-a9ac-f0e63f03813a`、Run `13bc7764-3ce8-597a-9b3c-fa91e49a9c14`、判断 `6150ca41-2e3a-5359-b178-f803b214fefd` 对应；Run completed、原 rationale 与计划输入、latest_triage_id 与 publication outcome、同步 triage_id 及材料身份均一致。
- 原 publication／Run ended_at 为 `02:49:23.097893 UTC`，同步 intent 为 `02:49:23.110965 UTC`，result 为 `02:49:31.939211 UTC`。同步读取独立会话中的已提交判断，回执时序与提交后设计一致。
- 一共 5 份工件，其中恰有 2 份同步工件；重复 finish 返回原 outcome 后仍为两份，未新增 Run 或重派同步。
- 结果为 `completed / stored / completed / source_current=true`。集合 GET 的 404 明确记录为 absent，随后创建集合、嵌入及 points 写入完成；该 404 不是被隐去的同步失败。
- 历史卡 `a3c8e5ce-6005-53a5-9343-220bd6c9d297` 已被一次[历史目的只读查询](../../../../docs/operations/evidence/knowledge-sync-20261112-01/local-flow/query.json)命中。查询文档 ID、content hash 与同步结果一致，来源状态 current；不是 Case 新调查或模型采用效果证据。
- [5 个原 GET 回执](../../../../docs/operations/evidence/knowledge-sync-20261112-01/local-flow/http)均为 200，覆盖 trace、publication、同步 intent／result 和卡片。路由与读取服务为原实现，认证使用本地适配；不能由开发身份的成功读取推断生产处理角色已经具备写权限。

[流程后源码核对](../../../../docs/operations/evidence/knowledge-sync-20261112-01/post-flow-source-check.json)记录 93 个应用源码文件无变化；本审计复核计划中冻结文件与当前文件无 hash 差异。部署地址、启用开关和角色权限仍须按发布配置单独读回。

## 交接、4177 与发布前置

[本地 4177 回执](../../../../docs/operations/evidence/knowledge-sync-20261112-01/local-workbench.json)及当前索引对应 67→68 条，只追加本批一条记录，显示 1 Run／5 工件，包含两份同步原件；没有创建新状态页面。本审计未做浏览器检查，正式 4177 仍待发布和读回。

OpenSpec、PROGRESS、部署／配置说明及历史知识交接已区分现网 r3 与待发布同步功能，说明默认关闭、所选开启／120 秒、只有新采用 A 结果触发，以及未知不自动重试。原显式导入／索引继续保留，正式告警人工反馈保存入口尚无接线证据，Case H 仍为独立任务链。

[生产发布前回执](../../../../docs/operations/evidence/knowledge-sync-20261112-01/production-before.json)明确 `socai2_prod_processor` 对 KB 的 SELECT=true、INSERT=false。当前已准备的 [增量脚本](../../../../deploy/database/knowledge_history_write_access.sql)只对明确数据库及处理角色增加知识表 INSERT，并检查 SELECT／INSERT；新装脚本同步，无 UPDATE／DELETE、角色或 V1 表结构增加。**生产写入资格尚未通过**，需在本次统一发布中执行该增量并读回实际角色、既有 RLS、profile 和加载源码，不能用本地开发身份或已构建镜像核销。

本次发布读回范围不再制造第二条生产合成 A／Case Run，也不追加分析模型。端到端自动触发依据来自上述本地流程；正式页面将展示该本地批次的原工件，生产配置／权限／源码加载成功不等同生产已新执行一次自动同步。r4 已冻结但尚未切服务，后续回执仍应保持这一证据区分。

## 保留的质量和未验范围

本批 analysis_model_calls=0，保存判断来自明确标记的测试模板，因此本批模型质量为 **NOT_EVALUATED**；前序持续模型质量 **NOT_PASSED**、F02 合理使用及 M01／M02 问题仍开放。没有从模板判断、可检索卡片或 HTTP 成功推导判断正确、知识可信或模型准确率改善。

真实本地流程只覆盖一次正常保存、同步和读回；失败／未确认路径由上述直接检查和实现审查支持。SQLAlchemy 对既有循环外键排序的警告在 validation 保留，未改 DDL 或为此重跑流程。没有验证进程退出后自动恢复、全库回填、人工反馈自动同步、A/I 新检索、Deep 动态检索或自动处理主链；本项也未实现这些能力。

待完成的是一次实际生产发布、角色 INSERT 与加载开关／时限／源码读回、本地同步原件的静态发布核对，以及之后的发布审计、归档和最终 Git／父项目引用。不得把本地限定通过改写为这些工作已经完成。
