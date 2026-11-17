# 第5步：Case成员分配与受理本地验收

2026-11-15，本步核心实现及真实PostgreSQL直接验证完成，HTTP联验见[HTTP回执](../case-allocation-http-20261115-01/README.md)。按[本步设计](../../../../openspec/changes/schedule-streaming-investigation-updates/stage5-case-allocation-design-20261115.md)先规划、strict，再实施。未部署、未启消费者、未提交推送；不把本步登记task写成Case调查已执行。

## 核心结果

- E01/E07/E08/E09复用同一容量分配：默认100，满后续建；成员、关系、版本和每个新案initial task在同一PG事务提交，原operation_key回放原完整回执。既有案只变成员，不新增待启动Run或立即重跑。
- 事件完整成员可分批读取并全部分配，独立于I模型选取100和HTTP显式ID数组200限制。事件保留全部Case关系，只向唯一active_case_id接收；旧串续建不抢回已切换的事件。告警可跨独立Case，无活跃映射。
- E07保留成员留在请求案，新增进当前接收案，空数组可清本案；E09保留真实源移出与目标分配。显式排除在本串有效，整事件/自动跟随不加回，明确单告警添加可恢复。回执列出excluded_alert_ids。
- 详情、列表及管理CaseView沿root显示续建关系；关联列表先同串、后共享事件，去重并保留explicit/member_alert来源、稳定分页及cursor_stale。shared-only项的continuation=null。事件接收资格与分析停止、Run状态分开；告警公开DTO保持。
- 自动跟随核心用例可调用并已直接验证，周期驱动仍留第7步。每个Case首轮实际执行仍留第6步；Case investigations新HTTP入口仍不挂载。

## 直接证据

| 层次 | 结果和证据 |
| --- | --- |
| 真实隔离PG主批 | [pg-04/result.json](pg-04/result.json)8组通过：99+5→100/4；事件260→100/100/60；独立接收/重放；排除与新增跟随；恢复/替换/移动/清空；版本/幂等/缺成员原子冲突；关系/游标/只读；超期及关闭。完整[分配回执](pg-04/receipts.json)、[数据库快照](pg-04/database.json)、[任务读回](pg-04/task.json)保留。 |
| 真实隔离PG补充 | [boundaries-01](boundaries-01/result.json)4组通过：容量配置为2、来源分批1；自动溢出转接；关闭旧案不影响后续；两个生产者不会超装；namespace冲突整体回滚；关闭当前目标不追加或续建。此批与HTTP租户隔离。 |
| 离线直接检查 | [direct-tests.txt](direct-tests.txt)：[20项主体检查](direct-tests.txt)通过，加上[10项事件输入检查](incident-source-tests.txt)通过；3项跳过。覆盖显式容量配置、最近正常完成时间/关闭/停止标记的接收资格、既有管理请求合同及安装器；3项需另配新空库/升级库的安装fixture未运行，不冒充新空库已实装。 |
| 迁移与元数据 | [首次应用](migration-first.txt)、[重复应用](migration-replay.txt)、[只读verify](schema-verify.txt)。仅v12_upgrade_dev应用129：32表521列，原V1/128/历史数据保留。新装及升级脚本共用129，已离线展开校验；没有新建空库验证。 |
| 新增列的输入/告警合同 | [source-readonly.json](source-readonly.json)在真实PG只读事务中核接收者已切换，而I分析parent仍等于原快照；active_case_id不进入I原摘要，告警关联事件列表不透出内部列。HTTP另补一次只读GET验证。 |
| HTTP | 独立HTTP模块完成72次实际PG/ASGI请求与23项离线检查，包含最后一次告警关联事件字段保护GET；明细见[HTTP回执](../case-allocation-http-20261115-01/README.md)。核心pg-04交接后不再写该租户，HTTP新操作另存回执。 |

主批快照为12Case、12个真实受理的initial任务、0attempt、0Run、676条Case成员关系。另有1个明确标记synthetic_stopped_state_fixture的失败check，专为验证分析停止不影响成员接收构造，不代表执行过调查。补充批4Case/4initial任务。所有批次模型调用为0，模型质量NOT_PASSED历史结论不变。

pg-04事件最初260条，后续用例加入3条，所以HTTP交接时实际263条；首批260分配回执和后续变更都保留。HTTP在获准独占租户内继续通过业务操作创建Case及明确切换接收者，不能把旧快照当作后续数据库当前值。

## 保留的中间失败与修正

pg-01/pg-02是合成事件成员夹具漏必需字段（membership_source、correlation_basis等），业务分配前事务回滚；pg-03已完成前6组，构造分析停止夹具时未同时提供失败task违反128约束。原[01](pg-01/result.json)、[02](pg-02/result.json)、[03](pg-03/result.json)和日志均保留；pg-04使用新租户及明确的合成失败check，不改旧批记录。

HTTP装配检查指出Contract不可变，核心已改model_copy并由pg-03/04验证。离线安装器检查发现新装reader入口漏129，已补齐，[初次失败](offline-tests.txt)及[修正后通过](offline-tests-final.txt)均保留。后续HTTP核对指出shared-only关联项应为continuation=null，以及管理投影应完整；核心已定向修正，由HTTP真实读回复验。E07纯新增的source.changed也由窄HTTP用例复验。最终排查发现新增active_case_id会被旧全行投影透出到告警关联事件列表，并影响旧I原输入比较；已在各自投影中排除，仅事件专用关系接口提供，并补上述只读PG/HTTP及事件输入检查。

## 范围与复现

核心脚本[validate.py](validate.py)要求显式数据库profile和未使用过的batch名；[boundaries.py](boundaries.py)仅固定隔离开发环境、新建独立合成租户，结束批次不得重派覆盖。配置含凭据部分留本机忽略目录，不进入证据。未操作21、正式库或其他项目；本步无Run/模型工件，所以不改变4177实际服务或伪造执行展示。

源码/配置与运行说明见[发布片段](../../../../deploy/local-investigation/case-allocation-release-fragment.json)、[配置说明](../../../../deploy/local-investigation/case-allocation.md)、[数据库入口](../../../../deploy/database/CURRENT.md)。本步完成只推进原2.2/2.7的Case成员与受理部分；流式任务仍2/11、主调查31/41。整体结束审计/部署仍留完整change收口，下一步第6步Case首轮执行与材料准备。
