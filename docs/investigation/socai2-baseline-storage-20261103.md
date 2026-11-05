# 新表基础调查存储服务：实现与接线边界

2026-11-03。本批将已审计的 socai2 模型同步到最新后台工作树，并增加 Case 成员、待更新记录、手动领取、结果发布和历史读取的事务服务。**这是可调用的新存储服务，尚未注册到旧 HTTP 路由，也没有切换线上写入。** 完整调查的设计仍以设计分支的 investigation-planning-design.md 为准。

同日后续已接入[C1整案数据准备](socai2-baseline-c1-20261103.md)：Case/成员/事件诊断/人工版本/当前判断及选用历史在一个读视图中选取并保存；本页17项是上一批事务验证记录，本次11项C1和10项回归另有回执，不能混称一次首过。

## 已实现的链路

| 动作 | 实际写入/读取 | 当前行为 |
| --- | --- | --- |
| 调整整案成员 | cases、case_alerts、runs、run_members、activities、activity_targets | Case 行锁；核预期范围版本；校验全部告警属于租户后一次性替换关系。成员实际变化才递增 scope_revision；记录实际增加/移除目标。相同 operation_id 重试返回原回执，不撤销后来的变化 |
| 维护待更新记录 | runs.kind=baseline / state=pending_update | 未领取时更新同一 Run；已有 running/unknown 时维护下一条 pending。不会自动派发 |
| 手动领取 | runs、run_members、artifacts | Case→Run 锁顺序，核完整范围、版本、单活跃条件；用一个查询固定最新材料、分诊、人工反馈版本指针。缺原始材料明确标 missing。保存输入清单并写 running；事务提交成功后才调用配置的执行器 |
| 重复/失败启动 | Run 状态和操作键 | 同请求不重复派发；已有活跃基础调查返回409且保留 pending。未配置执行器返回503且不领取；派发结果不确定标 unknown，占住基础槽，不自动重试 |
| 发布本轮结果 | runs、run_members、results、result_members | 终态、逐成员交付、结论、发现、未决、建议、比较、变化、影响、报告/图引用同事务保存。全体冻结成员均需有交付记录；允许明确未分析/未决，不能直接缺行 |
| 更新当前判断 | case_assessments、case_assessment_sources、case_assessment_members、cases、活动表 | 同事务调用既有 auto_adopt_baseline_result；有效结果自动采用，仅采用明确覆盖成员。旧范围、较新人工判断、系统交接均不覆盖当前判断。失败则连同结果发布一起回滚 |
| 历史读取 | runs 左连接本轮根 results | 待更新、执行中和终态记录均可读；未启动时 started_at=NULL，尚无结果时 result_id=NULL，不伪造结论 |

启动、发布和活动使用数据库时钟，与自动采用函数一致，避免应用主机时钟偏差影响“较新判断”的比较。所有事务重新设置租户上下文；不共用上一次请求的租户状态。

## 一个实际数据例子

1. 空 Case 加入 A1：scope_revision=1，建立待更新 R1，成员为 A1。
2. 尚未启动时再加入 A2：scope_revision=2，仍是 R1，成员改为 A1/A2。
3. 用户启动 R1：在事务里冻结材料 M1/M2 和同次分诊/反馈引用，写 running 并提交。执行器此后才收到 R1。
4. 执行器第一步尚未完成时加入 A3：Case 版本变为3，另建待更新 R2；R1的成员、材料、窗口不变。启动 R2 返回 baseline_already_active，R2仍为 pending_update。
5. R1结束并保存结果：结果保留在历史；由于Case已是版本3，返回 stale_scope，不更新当前判断，也不自动启动 R2。
6. 用户明确启动 R2，按三成员重新调查。若结果有效且期间无更晚判断，自动保存一版案件判断及覆盖成员。

输入清单保存于 artifacts.content_json，原材料版本另存 alert_materials，逐成员冻结指针在 run_members。后续已新增C1 source_snapshot，冻结案件说明、事件诊断、人工版本等；数据快照与模型提示词仍分开，模型视图/guard接线尚未完成，见C1交接。

## 页面字段现在如何落地

| 页面含义 | 新表字段 | 谁提供值 |
| --- | --- | --- |
| 基础调查类型、状态、本轮目的、开始/结束 | runs.kind/state/purpose/started_at/ended_at | 服务建立/领取/发布时写入 |
| 待更新范围、材料版本 | runs.scope_revision + run_members 的 alert/material/triage/feedback 引用 | 成员变更及领取事务 |
| 完整/部分交付 | results.delivery_state + result_members | 执行器根据实际覆盖提交；存储校验全体成员交付存在和完整标记的基本一致性 |
| 本轮结论、收尾说明 | results.conclusion/conclusion_state/conclusion_origin/validation_state/closing_note | 经验证的执行器输出；无模型结论使用系统交接属性 |
| 与上一结果的对比 | comparison_result_id/change_kind/change_summary | 启动冻结比较基线；执行器形成差异。首次无比较基线；不自动拿最近一条结果代替 |
| 对案件的影响 | results.case_impact | 执行器实际分析，不由状态或标题猜测 |
| 报告、图和证据来源 | results 的工件引用、逐成员 evidence_refs | 工件须同Case同Run且类型正确；引用须属于本轮冻结材料、本轮工件或明确冻结的历史输入 |
| 当前判断 | cases.current_assessment_id 及判断版本/来源/覆盖表 | 有效基础调查自动采用；保留旧版本及来源，不自动解决Case |

有存储列和发布入口不代表模型已经生成这些内容。本批测试使用明确合成的执行器输出，未调用模型、Tool、Deep或Graph。

## 代码与调用约束

- [事务入口](../../services/api/app/socai2/baseline_service.py)：每次调用创建独立事务；start 提交后才执行回调。
- [存储实现](../../services/api/app/socai2/baseline_store.py)：Case→Run加锁、成员冻结、发布及读回。
- [消费合同](../../services/api/app/socai2/baseline_contracts.py)：Pydantic严格字段与枚举、带时区时间、范围和覆盖校验。只实现本批消费的合同子集；未引入运行时 jsonschema 依赖。
- [真实PG验证](../../services/api/tests/test_socai2_baseline_storage.py)、[隔离运行脚本](../operations/verify_socai2_store_20261103.py)：测试环境使用 jsonschema 对实际写入的输入清单、活动和结果JSON按原合同校验；这不等于38类合同都已接入。

`BaselineStore`不自行commit，供已有事务组合调用；`BaselineService`管理完整提交边界。未来鉴权适配器必须从已认证用户取得tenant/actor，校验cases及alerts权限，不能从请求体信任tenant或actor。Publication只能来自受信任执行器，不能开放为客户端声称validation_state=accepted的接口。引用检查证明的是归属，不证明模型文字为真。

新代码位于 codex/case-baseline-history-20261103 最新后台工作树。123迁移、ORM、枚举与JSON合同从设计工作树逐字节同步；迁移仍是已验证的29表458列，本批无DDL修改。旧122方案及旧Case API保持原状；不能同时把两个存储路径当同一个Case的写入源。

## 验证及下一步

使用21现有 spirithub-postgres-1 / PostgreSQL16.15，独立库 socai2_schema_review_20261103_a1。仅新增合成数据；测试使用临时、无超级权限且不绕过RLS的角色和本地SSH隧道，结束删除。没有新建容器、业务数据复制、业务迁移、服务部署或真实调查。

**17个不同服务检查最终通过**，另有三批各自的角色/隧道清理检查。原始回执保存在 docs/operations/evidence/socai2-store-20261103，每批独立目录，不覆盖首轮失败。首轮14项中9过5失败，五个发布用例因测试账号漏授单个自动采用函数的执行权限失败并回滚；补权限后这5项通过。再改用数据库时钟、补跨Case重复键处理，验证10个受影响/新增用例并复用7个未变检查。不是一次首跑17项。见[逐项汇总及原件链接](../operations/socai2-baseline-storage-20261103.json)。五个新增Python文件Ruff通过，五份迁移/模型合同与设计分支逐字节一致。

C1数据构建已完成，接下来构建有界且经过guard的模型视图，再接C2富化、领域分析、Deep、Graph、Tool及C6交付。现有有限摘要 CaseAnalysis 不能直接冒充完整执行器。HTTP鉴权/DTO适配及告警、事件到新表的写入还未切换；AI明确采用和人工任务接口另按已定合同实现。页面保持不改；报告修复暂停，r13不重试。
