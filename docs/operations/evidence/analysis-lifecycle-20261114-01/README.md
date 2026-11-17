# 任务记录与执行生命周期：第1步本地验收

2026-11-14，按负责人“开始实施”推进[流式change实施顺序第1步](../../../../openspec/changes/schedule-streaming-investigation-updates/tasks.md#实施顺序与每步完成边界)。仅本机隔离库`127.0.0.1:28412/v12_upgrade_dev`；真实PostgreSQL、受限处理角色、新UUID合成记录。未调用模型、工具、Redis或正式服务，未部署、提交、推送或清理数据。

## 已完成的业务效果

- 同操作重复受理返回原task_id；换意图/主体/内容冲突。受理和无变化跳过均不提前创建Run；可在调用方现有事务使用`AnalysisTaskStore.accept`，Case新建自动首轮接线仍属第5/6步。
- 实际开始才创建attempt；同Case准备阶段尚无Run也算活动。Run创建并冻结输入后关联该attempt，记录真实Run/input artifact/digest，冻结后不能改写。Run非空关联按tenant/run唯一，不能把历史Run伪绑成新执行。
- 每次失败保留原尝试与Run。策略受理时保存，重试次数只在实际开始时增加；默认60秒/最多1次均来自配置。准备失败可无Run。窗口内已受理首试跨期仍执行，失败不重试；关闭前未开始则跳过。
- unknown保留原Run的unknown及NULL ended_at；本地真实结束写attempt.local_ended_at，任务呈failed。不会把unknown永远当活动，也不新增人工解除；真正运行的尝试仍阻止同Case领取和结案。
- 成功结束推进完成输入和活动时间；失败不冒充已覆盖。原失败和原输入工件均保留。模型结论质量未在此验证，原NOT_PASSED保持。
- 核心任务详情/列表、稳定分页和更新资格摘要可读；归并的原task_id保留原受理时间、跟随根任务真实尝试，不输出队列或内部attempt ID。采用预览增加unfinished_analysis_tasks并沿原review_token/确认规则处理；已结束unknown不算未完Run。

## 验证与原始回执

[最终pg-05](pg-05.json)12项均通过，包含已有完整结果采用用例的23次记录检查，读取前后任务/尝试/主体状态摘要一致。代码哈希在运行期间未变化。

| 回执 | 结果 |
| --- | --- |
| [migration-01](migration-01.txt) | 沙箱拒绝本机Docker socket；未操作数据库 |
| [migration-02](migration-02.txt) | 128的函数CASE表达式语法错误，整个DDL事务回滚；修正后新次执行通过 |
| [pg-01](pg-01.json) | 受理验证通过，开始尝试时nullable JSON被写成JSON null而触发对象检查；修正新ORM可空JSON的SQL NULL处理，保留该批受理/跳过记录 |
| [pg-02](pg-02.json) | 11项基础生命周期验证通过 |
| [pg-03](pg-03.json) | 补真实Run时间/比较来源约束及采用、归并读取，12项通过 |
| [pg-04](pg-04.json) | Case详情可开始判断与unknown口径对齐后，12项通过 |
| [pg-05](pg-05.json) | 补Case队列直接读取：旧unknown不挡下一轮，实际准备仍阻止开始；12项通过 |

[直接检查](direct-checks.json)记录12项离线配置/安装入口检查、Ruff、OpenSpec strict、迁移重复应用及reader核验。128增加3表61列，该隔离库现31表511列；123–127及冻结V1文件原件保持。新空库完整初始化未重跑；没有将本地升级验收当成21发布或真实模型质量通过。

复验入口为[专用runner](../../verify_analysis_lifecycle_20261114.py)，必须显式给数据库profile、环境文件、调查policy及新的回执路径。业务检查在[专用PG用例](../../../../services/api/tests/test_socai2_analysis_tasks_pg.py)，复用既有[结果采用用例](../../../../services/api/tests/test_socai2_case_adoption_pg.py)。不重派旧Run，不覆盖已结束批次。

## 核心与HTTP交接

实现入口：[AnalysisTaskService](../../../../services/api/app/socai2/analysis_tasks.py)、[事务Store](../../../../services/api/app/socai2/analysis_task_store.py)、[配置](../../../../deploy/local-investigation/analysis-tasks.json)、[增量安装入口](../../../../deploy/database/CURRENT.md)、[发布清单片段](../../../../deploy/local-investigation/analysis-lifecycle-release-fragment.json)。

- `AnalysisTaskService(session_factory, policy)`；`read_task(tenant_id, subject_type, subject_id, task_id)`；`list_tasks(tenant_id, subject_type, subject_id, *, limit=None, cursor=None)`。返回真实数据dict，URL由独立HTTP层构造。
- `submit(tenant_id, **request)`返回`task_id/subject_type/subject_id/status=accepted`。`service.transaction(tenant)`提供`accept`、`start_attempt`、`bind_run`、`finish_attempt`、`skip`，均由调用方控制事务，不在事务内调用模型。
- Run目录SQL：`runs LEFT JOIN analysis_attempts ON tenant相同且run.id=attempt.run_id LEFT JOIN analysis_tasks ON tenant相同且attempt.task_id=task.id`；intent取真实task。历史无关联为NULL，不补假任务。
- 任务`results`已在后续HTTP对接中[补齐并验证](../analysis-task-results-20261114-01/README.md)为`result_type/id/source_run_id/kind`四字段，kind取结果自身类型，URL由HTTP生成；该非空结果验证不计入原pg-05的既有范围。
- `CaseBlockingRun`和`CaseManagementView`字段/类型未增删，仅更正说明和判断：准备中无Run时blocking_runs可空但can_close=false。`ResultAdoptionPreview`新增`unfinished_analysis_tasks`，元素为task_id/intent/status，waiting投影accepted，排除merged子任务。原人工事项及采用确认口径保留。

已将实际方法、唯一键、PG证据和上述Case读侧增量送达HTTP对接聊天`01a1cdfd-330c-7452-a4fd-ce74a55ce0b3`；对方确认使用真实关联接R1及同步合同断言。已读回对方[R1最终验收](../run-directory-http-20261114-01/README.md)：真实关联/intent筛选、32次ASGI及10次基础读取通过，候选75操作，正式仍71；此结论复用其独立证据，本聊天未重跑R1。**公共analysis-tasks GET尚未接路由**，后续由HTTP侧适配；本步完成核心最小读用例，不修改其共享路由文件。

## 本步边界和下一步

三张内部表及生命周期已有直接证据，整体2.1/2.3/2.7尚未完成，流式仍1/11、主调查31/41。下一主线步骤为Redis task/pending、唯一调度循环、配置总并发N和60秒轮询，届时直接验证可执行任务不被忙主体阻塞及实际重试调度。没有提前启A/I/Case生产者、Case续建/跟随、targeted/synthesis或knowledge_sync；这些意图的核心受理暂明确拒绝为未实现。进程重启发现interrupted及收尾补写在调度步骤接入，不把表枚举当已实现恢复能力。

本步未做完整change结束审计或统一发布，4177未加入这些程序合成记录；它们不是新的模型调查验收样本。
