# 告警基本分析与事件诊断：输入、结果写入和剩余接线

2026-11-04。本批实现服务器内部 `StageResultService`：A告警基本分析、I事件诊断的开始记录、冻结输入、产物保存、失败记录和新鲜度核对。沿用29表458列，无DDL。**实际查询/模型执行器尚未接到该服务，旧Agents仍走旧表；本批不能称A/I真实业务链已上线。** 页面、旧消费入口、生产配置均未改。

## 1. 现有代码核对与取舍

旧Agents的 `workers/triage_persistence.py` 把旧表写入、记忆、成本和处置等效果放在TriageWriter接口后；worker还涉及升级调查及playbook。直接替换其中一段SQL会形成两套数据与后续效果，因此本批不把新表writer塞进旧流程。新存储先提供明确的输入/结果合同，后续执行适配器需逐一接入真正发生的查询、模型和来源回执。

Fusion负责来源事实、材料与归并关系；归并narrative不是事件诊断。A/I也不启动完整Case调查，不使用Case的单活跃槽或pending机制，不创建自动队列。Case已有手动C1–C6流程保持。

## 2. 实际保存流程

1. 服务端提供租户、A或I身份、操作UUID、实际执行器版本和额度，调用 `begin`。锁定告警或事件；同操作重发返回原Run，不重复领取。
2. 单条SQL冻结输入：当前材料全文、对象、业务字段、人工反馈；I还包含完整当前成员、实际归并依据和每条告警同次分诊。输入超过1MiB整次拒绝，不裁剪成员后继续。材料本身为空时保空，后续输出不能引用不存在材料。
3. 同事务创建 `runs`、`input_snapshot`；I另建running的 `incident_diagnoses`，分配事件内递增revision。离开事务成功后才返回领取结果。
4. **未来执行适配器**完成常规查询与分析，把经过自身验证的输出交给 `finish`。当前服务不执行这些调用，也不创建虚构的model_response/tool_response或用量。
5. 核输出类型、来源身份、路径、角色与范围；重新计算当前输入指纹。A原子保存同次分诊和Explain；I保存该次诊断与未决；另保存输出回执和Run终态。
6. 输入仍相同且没有更新启动的成功结果，才推进当前指针；否则结果进入历史，回执标 `input_changed` 或 `newer_result_exists`。完全相同的发布重发返回原回执，改变内容的重发拒绝。

锁顺序为告警/事件→Run；A采用分诊后按告警→事件顺序更新业务时间，与Fusion一致。I读取成员时不反向锁告警。未来成员移动服务也须沿统一锁约定。数据库延期外键检查失败时，分诊/Explain/诊断/指针/Run终态全部回滚。

## 3. 字段与表明细

| 项 | 需求字段 | 本批保存/读取位置 | 语义及限制 |
| --- | --- | --- | --- |
| S01 | A/I类型及所属身份 | runs.kind + alert_id或incident_id | 与Case baseline不同；无混用Case ID |
| S02 | 本次操作身份 | runs.operation_key/request_hash | 重发幂等，改变目标/执行器/额度拒绝复用 |
| S03 | 执行器来源 | runs.executor_version；assessment/diagnosis.producer | 服务端提供真实版本，不能由模型自行指定 |
| S04 | 开始/结束/停止 | runs.requested_at/started_at/ended_at/state/stop_reason | 数据库时钟；unknown不伪装失败或完成 |
| S05 | 输入快照 | runs.input_artifact_id → artifacts.content_json | 同次完整快照、有大小/hash/保留信息 |
| S06 | 原始材料版本 | 快照members[].material；A.input_material_id | 引用不可变材料，后来最新材料不替换历史输入 |
| S07 | 对象与字段出处 | 快照members[].objects | 按本次材料筛选；不把所有历史版本对象合并 |
| S08 | 成员覆盖与归并依据 | I快照members[].membership | 当前完整成员及原关系；不推断因果链 |
| S09 | I读取的告警诊断 | 快照members[].triage | 同次完整assessment，按prior_analysis引用 |
| S10 | 人工反馈 | 快照members[].feedback | 单独保留，按human_statement引用 |
| S11 | 当次判定与理由 | alert_assessments.verdict/rationale | 一次提交，不能与后来人工判定混配 |
| S12 | 当次分诊置信度 | alert_assessments.confidence/score_state | 0有效；available才有0–1值，其他状态必须NULL；列精度5位小数，收到原值另保输出回执 |
| S13 | 分诊建议 | alert_assessments.recommendations | 按既有建议合同留存，不执行处置/审批 |
| S14 | 分诊操作者来源 | alert_assessments.actor | 服务身份与执行器来源，不伪造人工操作人 |
| S15 | 分诊与执行关联 | source_run_id、operation_key | 可按一次执行回查，不拼接不同轮次 |
| S16 | 告警解释正文 | artifacts.kind=alert_explanation | body、generation_method、generated_at、来源、建议、限制；GET不生成 |
| S17 | 当前分诊/解释 | alerts.latest_triage_id/latest_explanation_id | 两指针同事务推进；不修改handling_status/disposition |
| S18 | 事件诊断尝试 | incident_diagnoses.revision/state/requested_at | 开始时即有记录，失败不丢失尝试 |
| S19 | 诊断摘要与结论 | incident_diagnoses.summary/diagnosis | 接收可信执行适配器产物；结构/引用校验不证明语义正确 |
| S20 | 发现/依据/限制 | diagnosis.findings/source_refs/limitations | 保原范围和角色，不能冒充成员独立观察 |
| S21 | 未决项 | incident_diagnoses.open_questions | 复用Question结构，可有范围/证据要求/状态 |
| S22 | 诊断输入版本 | input_artifact_id/source_fingerprint | 包含成员、材料、分诊、反馈、关系及相关业务字段 |
| S23 | 当前事件诊断 | incidents.latest_diagnosis_id | 仅成功且发布时新鲜、非更旧启动结果才推进；失败不覆盖 |
| S24 | 诊断错误 | incident_diagnoses.error.code | unknown/failed/cancelled明确；不保存异常堆栈作为业务正文 |
| S25 | 发布回执 | source_snapshot输出工件 | 输出原值、hash、结果ID、是否采用及原因 |
| S26 | 后续过期判断 | StageResultService.freshness | 同一只读一致快照核对；有current指针不保证永不过期 |
| S27 | Case已读分析 | C1 alerts[].triage、incidents[].diagnosis | 实际读回验证，保持prior_analysis身份；C1仍提示诊断freshness_not_revalidated，尚未接本批新鲜度方法 |
| S28 | 执行用量及查询证据 | 既有run_steps/artifacts表可承接 | 本批没有执行适配器，未写真实步骤、请求/返回或usage，不补0冒充已知 |

引用目前支持冻结的完整告警材料及其明确字段；输入快照中的告警/对象/关系为source_label、分诊为prior_analysis、反馈为human_statement，整份快照仅execution_receipt。不存在字段、跨Run/租户来源和把分诊标为observation均拒绝。数组行级查询证据、外部来源须先由后续执行适配器留存并明确授权引用，当前拒绝这些未实现入口。

## 4. 具体例子

**A分析中更新材料。** A1开始时冻结M1；期间Fusion保存M2。A返回needs_review/置信度0及Explain，均作为这次执行结果保存，但当前指针不采用，因为输入已变化；M1仍能回查，需另一次明确执行分析M2。

**同输入乱序完成。** R1先启动，R2后启动；R2先成功，当前指向R2。R1随后成功只保存历史，不能抢回当前指针。不需要新增自动调度。

**事件诊断过期。** I1冻结A1/A2与当时分诊；A1随后有新分诊。原I结果仍可作为历史查看，freshness返回false；若I还未发布，本次成功正文可保存但不采用。事件页和C1需接此检查后才能显示“当前有效”。

**失败与提交不确定。** I已有成功D1，下一D2调用结果未知，记unknown；明确失败后记failed，D1指针保持。输出提交时若延期外键失败，则所有本次输出回滚，Run仍running；存储服务不会擅自再次执行模型。

## 5. 验证与后续

使用21既有独立合成PostgreSQL、受限角色；本批10项不同检查最新通过，首轮9项通过，新增引用角色后定向复核Case桥接并新增1项。无真实模型、湖、Redis/Kafka或厂商调用，无生产数据读取。测试将合成A/I输出交给真实存储服务，不能当真实推理质量验证。[固定回执](../operations/socai2-stage-results-20261104.json)保留各批及源码hash。

下一：接实际A常规查询/分诊和I诊断执行器，留存其来源、请求/回复、步骤、预算与实际用量；新告警/事件读取DTO及C1接新鲜度；再接显式Case事件关系/H/Q和外部来源。旧Agents消费及处置仍依赖旧表，生产不能单独切换。29表/458列、原迁移和公共枚举/JSON合同保持；原r13报告修复继续暂停，5.3未完。
