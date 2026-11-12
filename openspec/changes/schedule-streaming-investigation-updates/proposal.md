# 流式告警下的调查更新与反馈重算

## Why

事件进入调查后仍会收到新告警和人工归并。目前事件关联只取当时成员，Case 主要依赖手动启动，不能完整表达持续变化后的自动更新。2026-11-12 项目负责人确认采用简单方案：持续接收材料、每轮冻结输入、同一对象单轮运行、后续变化合并，人工反馈单独变化时只重算综合结论。

本文及本 change 的规格是**后置、待实施目标合同**，不是自动消费或模型质量已通过的声明。负责人随后明确顺序：**先完成固定范围的一次调查，再推进更新和流式调查**。当前先按主 change 的[固定流程计划](../complete-socai2-investigation-chain/fixed-flow-plan.md)收口；本项只保留规划，不提前实施队列、自动接续或反馈重算。

## What Changes

- 新告警只触发自己的 A 分诊；实质材料、成员及已采用分诊变化分别合并到 I/Case 待更新，不因一条告警到来重跑全部 A。
- 从整个事件创建或关联的活动 Case 跟随该事件新增成员；单条告警关联不扩大范围，人工移出不自动加回，已结束 Case 不自动重开。
- 一份持久化任务列表承载 A、I、Case 和历史知识维护；同一业务对象最多一个执行中任务及一个合并待办，完整调查与反馈重算共用 Case 执行槽。
- 建议初始配置为 I 合并 60 秒、Case 自动更新合并 300 秒；人工明确请求优先，自动任务按固定到期时间排序，不等告警队列清空。所有值走 profile。
- 完成或修订有效 Case H 反馈后，仅反馈变化走 C6 综合复核；同时有新成员/材料等变化则合并为完整调查。原证据、反馈范围和每轮版本保留。
- 明确固定阶段模板与知识内容的组合：完整 Case 沿用 C2 三目的检索；反馈复核复用所选原调查的相关知识，不新增取证、Deep 或知识再检索；历史知识维护移到低优先级待办。

## Capabilities

### New Capabilities

- `investigation-update-scheduling`: A/I/Case 更新触发、事件成员跟随、持久化合并、单对象串行、执行频率及版本读取。

### Modified Capabilities

- `case-human-http-flow`: 启用调度后，有效 H 反馈提交合并进入 C6 复核或已有完整调查待办，替代每次反馈均手动重跑整案的默认流程。
- `case-purpose-knowledge`: 固定母版中的知识用途/容量边界，以及反馈复核对原调查知识的冻结复用。
- `historical-alert-knowledge`: 新采用 A 分诊的知识维护改为提交时登记、提交后由低优先级任务执行，保持判断和索引结果分离。

## Impact

属于主 change [complete-socai2-investigation-chain](../complete-socai2-investigation-chain/tasks.md) 的 3.7、3.12、3.14、3.16、3.21 子范围；本项任务集中于本目录，不复制主调查任务树，不核销已有质量问题。前置复用 [Case/H](../archive/2026-11-11-enable-case-human-http-flow/validation.md)、[知识用途筛选](../archive/2026-11-12-refine-purpose-aware-knowledge-use/validation.md)及[历史同步](../archive/2026-11-12-sync-saved-alert-knowledge/validation.md)回执。

影响入站保存后的触发、`stage_results`、Case 关联/领取/H 服务、C6 输入装配、知识同步和 profile；需要内部队列及跟随标记的增量迁移。保留当前 28 表/450 列基线、冻结 V1 原件与数据，不修改告警交接字段、现有枚举含义或原 GET 合同。执行入口返回语义和新增调度读取见 design.md，排队成功不能冒充执行完成。

不新建消息中间件、通用工作流/恢复平台、复杂增量调查、Q 自由调查、独立告警人工反馈写接口或 A/I 新知识检索。不做全仓回归、压力/故障矩阵或多模型比较。本轮只完成规划和 strict 校验；运行开关、部署及业务数据不由规划改变。
