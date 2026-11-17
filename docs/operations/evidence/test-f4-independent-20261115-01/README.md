# 测试侧F4独立验证

2026-11-15。按负责人要求由测试会话实际参与验证。**31项离线测试、新批真实PG/Redis六组流程检查及独立重试上限检查均通过；同批HTTP的78+11次只读GET也已通过。** 本机中间验证使用实际A/I/Case执行器和明确模型/查询替身；没有调用真实模型、投Kafka、操作21、发布业务服务或重派旧任务。F5、21完整验收及结束审计仍待。

## 实际执行与证据

分支`V1.1`，复用工作树现有测试，显式使用`deploy/local-investigation/investigation-policy-case-v1.toml`和本机`.local/conda-envs/socai2/bin/python`。关闭pytest插件自动加载，仅显式加载pytest_asyncio；未引入新测试框架或修改业务源码。源码/配置15文件运行前后hash一致。

- [执行命令、配置引用与源码摘要](offline-01.json)
- [pytest原输出：31 passed](offline-01.txt)
- [JUnit逐项结果](offline-01.xml)

实际命令为上述Python执行`-m pytest -p pytest_asyncio.plugin -q`，目标仅以下三份测试文件；完整参数见JSON，未运行`*_pg.py`。

| 实际测试 | 数量 | 本次证明的范围 | 不能据此证明 |
| --- | --- | --- | --- |
| [case_update_inputs](../../../../services/api/tests/test_socai2_case_update_inputs.py) | 20 | 同业务新ID/管理元数据不触发，手动业务变化可识别，自动只比较适用可用I；告警成员/晚到A/反馈/I失效/Case交集变化不越过I直触；有效H独立保留 | 输入为明确内存Context，不能替代真实capture/SQL、周期扫描及自动任务入队 |
| [case_incident_scope](../../../../services/api/tests/test_socai2_case_incident_scope.py) | 8 | 用真实C3 builder及保存样本副本核3成员选1，实际覆盖/待核/未分析区别，缺源/选入/覆盖/指纹/交集不猜，跨Case发现原范围传至Deep/C6；Case外真实成员不再造成等级别名KeyError | 不代表新的模型请求、数据库存取或所有历史展示场景通过 |
| [analysis_dispatch](../../../../services/api/tests/test_socai2_analysis_dispatch.py) | 3 | 失败分类、重试资格、disabled配置不启动运行、N/锁/发布依赖基本规则 | 不直接运行真实队列和任务落库，不能单凭这3项判取消归并或同主体串行闭环通过 |

离线31项未出现失败，未据此改业务代码。保留核心F4 `pg-01`未知、`pg-02/03`存储失败及`retry-guard-01`不完整状态，未读取后改写或恢复它们。

## PG/Redis直接验证与结果

只读检查现有[validate_trigger.py](../case-trigger-fix-20261115-01/validate_trigger.py)及[validate_retry_guard.py](../case-trigger-fix-20261115-01/validate_retry_guard.py)，其直接范围符合既有TC-Q01/C05/C07/C08/C10：真实调度/Case执行器、PG/Redis，以可控模型/查询依赖观察排队与冻结；I→活跃Case链仍是直接构造来源，不是Kafka完整链。

| 已实际验证的行为 | 驱动与通过证据 |
| --- | --- |
| 不同请求独立、同key幂等、忙项不占另一槽位 | validate_trigger：实际task/队列/执行路径，保留独立身份且不产生新merged；相同key仍返回原任务 |
| 开始前读最新、冻结后留后轮、已覆盖请求跳过 | validate_trigger：可控进入点加入成员，后任务新范围、前Run原范围保持；no_changes无attempt/Run/模型 |
| 整事件I→活跃Case、单告警固定范围 | validate_trigger：晚到A/新事件成员不越过I；I可用更新后仅活跃整事件Case变化，自动/手动分别保留适用I范围 |
| 容量续建不绕过I | validate_trigger：本测试容量2，第三条成员需有效I后才续建，继承关系/新成员/initial可读；不代替正式100上限证据 |
| 独立请求不绕过旧任务重试等待/上限 | retry_guard：同主体新普通请求pending、另一主体可运行；60秒前不启动重试，原任务耗尽后同材料新请求跳过，不重新获得预算 |

上述驱动已顺序运行一次，全部通过。主批[结果](../case-trigger-fix-20261115-01/test-pg-01/result.json)、[落库快照](../case-trigger-fix-20261115-01/test-pg-01/snapshot.json)、[执行包装回执](pg-trigger-01.json)：tenant `2fad43c6-f75d-411e-9ad6-2b4946929510`，6 Case、23 task（13 completed、10 skipped/no_changes）、13 attempt/Run、9 Case Result，22次模型替身回复、0真实模型。6组检查完整通过；9个已覆盖排队请求及历史Case自动check均没有attempt/Run，历史Case手动check完成并保存新Result。容量仅本测试设2，以第三成员验证续建，不替代默认100上限的原有直接证据。

随后独立[retry_guard结果](../case-trigger-fix-20261115-01/test-retry-guard-01.json)及[执行包装回执](pg-retry-guard-01.json)通过：tenant `56b557bd-faaa-49e9-a15a-f24bc33e3536`，真实PG/Redis、受控执行器/时钟。原任务60秒前不重试、到60秒仅重试一次，最终failed/retry_exhausted且两次attempt保留；同主体新请求保持独立pending，之后skipped/automatic_attempts_stopped、无attempt，另一主体completed。共3次受控执行，不是实际模型网络故障；Case执行器故障分类另由F3真实执行器/故障替身证据覆盖。两个阶段20文件的源码/配置hash分别前后相同，命令、时长与退出码已保存。

## 环境准备与原失败保留

早期本机`127.0.0.1:28412 / v12_upgrade_dev`的256MB tmpfs已满，曾暂停PG写入。调查模块随后将全库复制到新磁盘容器`127.0.0.1:28413`，旧容器、数据和失败记录保留；[迁移回读](../case-trigger-fix-20261115-01/storage-copy-readback.json)核34表计数一致，未删除旧数据。不是对21扩容，也不是清空旧库后重测。

测试侧先核实际配置指向新28413及专用本机Redis 32774。默认工具沙箱连接被拒的[原回执](pg-readiness-default-01.json)保留，尚无业务写入；获准访问本机网络后，[只读事务探测](pg-readiness-escalated-01.json)确认database=`v12_upgrade_dev`、read_only=`on`。严格校验通过后，按负责人“中间验证继续用本机隔离库，最终在21验收”范围执行上述全新批次。配置凭据未输出，私密配置只保存引用和摘要。

`test-pg-01`及`test-retry-guard-01.json`开始前确认不存在，各执行一次；未恢复或改写旧`pg-01/02/03`及`retry-guard-01`，不能把新批成功补成旧批成功。模型输入/回复、范围、任务/Run/结果、19类记录快照均随新批保留。两份stdout为空（驱动无终端输出），通过依据是退出码、明确断言及结果/快照，不以空日志判成功。

## 同批HTTP只读核对

HTTP提供方的[收口说明](../case-trigger-fix-20261115-01/http-readback.md)及[最终摘要](../case-trigger-fix-20261115-01/http-final-summary.json)已核，与下述原始回执和测试侧批次身份一致；公开OpenAPI保持80操作，本项没有新增业务字段。

HTTP模块已完成并由测试侧读取原回执核对：主批[http-full-read-02.json](../case-trigger-fix-20261115-01/http-full-read-02.json)78次GET全部200，19表读取前后摘要相同；guard批[http-retry-guard-read-01.json](../case-trigger-fix-20261115-01/http-retry-guard-read-01.json)11次GET全部200，10表摘要相同。均为28413真实PG强制只读/ASGI、无鉴权，0新模型/执行/写入。

实际核独立task与10个no_changes空Run、旧1/新2范围、历史手动check读取新I但Case仍原1条、自动check跳过、续建仅新1条且initial/Result/接收与关联可读、A/I/Case来源一致。guard原task两次failed Run、retry_count=1，独立新请求skipped无Run，另一主体completed；受控执行器本来没有业务Result，HTTP如实为空，不冒充Case真实调查交付。

首次[http-full-read-01.json](../case-trigger-fix-20261115-01/http-full-read-01.json)的69次GET成功，第70个关联读取503；测试入口漏加载已有`allocation_policy_file`，仅补测试配置后新只读批通过，未修业务或重派调查。该失败未取得完整after摘要，不称其前后对账通过；原失败和后续成功分别保留。本HTTP批没有POST，同key幂等仅复用本批核心用例入口证据。

F4已取得本机直接验证及同源接口读取证据，最终21候选TCP、真实模型、Kafka投递/消费/归并/事件与上下文路由、4177及独立结束审计仍待共同准入。W1未实现，本批不替代21正式验收。
