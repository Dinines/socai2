# I事件诊断：执行、字段与例子

2026-11-04。OpenSpec `complete-socai2-investigation-chain` 3.2已完成服务器内部执行接线。入口为`StageResultService.execute_incident(tenant_id, incident_id, operation_key)`；当前开发目录为`E:/aisoc/socai2`，分支`codex/case-baseline-history-20261103`。生产消费者未切换，页面未改。

## 完整流程

1. 领取：锁定事件，按租户和operation_key取得唯一Run；同一键重发只读已有状态。首次事务一起保存完整输入、running Run和running诊断尝试，截止时间只生成一次。
2. 冻结：同一SQL快照读取事件事实、完整成员、材料、对象、归并依据、人工反馈及成员分诊，同时核验每条分诊的来源Run、材料配对和输入新鲜度。旧分诊正文保留在冻结原件；只有可核验且仍有效的分诊进入模型。
3. 准备：保留所有成员的覆盖目录，按成员轮流选择有限字段；来源标签、原始观察、已有分析、人工陈述分角色。超限、输入guard命中、无法精确引用的字段明确省略；完整成员目录放不下则失败，不能偷偷缩小范围。
4. 执行：先提交模型步骤、实际请求、来源映射和额度预留，再调用一次模型。I不重复A的资产/历史/TI查询，不启动Case调查，也不改变成员告警的状态或判定。
5. 校验：保存模型原回复及上报用量；校验结构、完整成员覆盖、实际可见来源和成员归属。模型遗漏成员、引用其他成员材料、未知用量或不完整输出均不能发布为有效诊断。校验不等于证明推理为真。
6. 发布：诊断、未决问题、发布回执、父阶段与Run终态同事务提交。输入未变且没有较新结果已采用时更新事件当前诊断；否则只保留历史。请求提交失败不外呼；发布失败不留下半份正式结论，已提交原回复仍保留。
7. 读取：已有A/I只读接口和C1按当前输入重新判断新鲜度。之后成员或材料变化时，旧诊断仍可查，但不再作为新Case Run的有效已有分析；已冻结Case历史保持原样。

服务器固定上限：1次模型、0次外部查询、24000 tokens、120秒；模型视图8192字节、单字段2048字节、完整消息12288字节、输出3000 tokens。超过上限明确停止，不增加纠错调用、自动重试或自动接续。

## 字段与存储对照

本批复用既有29表458列。下表32项按实际写入和读取列出；没有新增DDL、ORM列或公共枚举。`artifacts`正文均指`content_json`，不是新增表列。

| 项 | 字段/语义 | 来源及存储位置 | 当前处理与读取 |
| --- | --- | --- | --- |
| I01 | 租户及事件身份 | runs.tenant_id / incident_id；incident_diagnoses同键 | 服务端传入并受租户隔离，不能由模型指定 |
| I02 | 幂等请求及执行版本 | runs.operation_key / request_hash / executor_version | 相同意图重发不再调用模型；不同意图同键拒绝 |
| I03 | 执行状态及停止原因 | runs.state / stop_reason / requested_at / started_at / ended_at | failed与unknown分开；unknown不伪造结束时间 |
| I04 | 固定预算及截止时间 | runs.limits | 首次领取时生成，不随重发刷新 |
| I05 | 诊断尝试身份及版本 | incident_diagnoses.id / revision / source_run_id / state | 领取时已存在；失败也保留尝试 |
| I06 | 冻结输入及材料指纹 | runs.input_artifact_id；incident_diagnoses.input_artifact_id / source_fingerprint；artifacts.input_snapshot | hash、字节数与完整状态执行前核验 |
| I07 | 事件独立事实 | input_snapshot.parent ← incidents | 模型选择id/title/description/severity_override/tags；归并摘要不冒充诊断 |
| I08 | 全部成员身份与告警字段 | input_snapshot.members[].alert ← alerts | 发生时间、严重度、原厂、来源编号等按已有值提供 |
| I09 | 成员材料版本与原文 | members[].material ← alert_materials | 原文、OCSF和检测标签保留；仅complete原文可作为观察 |
| I10 | 成员归并依据 | members[].membership ← incident_alerts | 作为来源背景，不能自动推导因果 |
| I11 | 对象与成员关系 | members[].objects ← alert_objects | 只读取该成员当前材料的对象 |
| I12 | 人工反馈 | members[].feedback ← alerts.latest_feedback_id → alert_assessments.id | human_statement；不与分诊评分混配 |
| I13 | 同次分诊原件 | members[].triage ← alerts.latest_triage_id → alert_assessments.id | verdict/rationale/confidence/score_state与同次id/Run/材料配对 |
| I14 | 分诊核验版本 | input_snapshot.triage_validation_version | 新值socai2.incident-triage.v1；旧快照继续按原合同核对 |
| I15 | 分诊来源配对 | triage_validation[alert_id].triage_id / source_run_id | 同一SQL快照产生，模型准备再次核对配对 |
| I16 | 分诊新鲜度及可用性 | triage_validation[alert_id].freshness / usable | Run完成、输入current、材料配对才可用；未知/过期正文不进模型 |
| I17 | 模型输入成员覆盖 | model_request.member_coverage | 每成员material_state、triage_freshness、triage_usable、included、omitted |
| I18 | 有界输入省略 | model_request.input_omissions | field_size/view_size/input_guard/unaddressable_source_path及计数 |
| I19 | 模型实际来源映射 | model_request.source_map | 实际可见S编号→准确引用、所属alert_ids、visible_value_sha256 |
| I20 | 实际模型请求 | model_request.body / provider / model | 完整messages、max_tokens、response_format先提交再外呼 |
| I21 | 模型额度预留 | model_request.reserved_token_upper_bound | 沿既有预算校验，超出上报值不采纳 |
| I22 | 阶段及模型步骤 | run_steps.kind / stage_code / parent_step_id / state及工件指针 | I父阶段加一次model子步骤；无虚构Tool步骤 |
| I23 | 原回复及校验错误 | model_response.raw / validation_error | 无效输出也保存，不拼接或伪造成功 |
| I24 | 实际上报用量 | model_response.usage；run_steps.usage | reported/unknown明确；未知不补0，本批不证明真实模型费用 |
| I25 | 模型逐成员输出 | model_response.validated_members | alert_id、summarized/unresolved/not_reviewed、assessment、source_ids、limitations |
| I26 | 诊断摘要与结论 | incident_diagnoses.summary / diagnosis.conclusion | 模型成功且合同通过后发布；不是Fusion narrative |
| I27 | 正式逐成员判断 | diagnosis.findings[id=member:<UUID>] | 单成员scope、判断、support和member_coverage限制；公共合同不增属性 |
| I28 | 跨成员发现 | diagnosis.findings[id=F1等] | inferred/unresolved；引用覆盖所属成员，不新增独立观察事实 |
| I29 | 未决问题 | incident_diagnoses.open_questions | open、answer=null、scope、证据需求与来源；问题不是事实 |
| I30 | 总体来源及限制 | diagnosis.source_refs / limitations / validation_state | accepted仅表示合同接受；省略和未用分诊逐项注明 |
| I31 | 生成时间和当前指针 | incident_diagnoses.generated_at；incidents.latest_diagnosis_id | 当前指针与当前有效性分开；生成诊断不改成员判定 |
| I32 | 发布与采用结论 | artifacts.source_snapshot.output / outcome | result_id、adopted、current/input_changed/newer_result_exists可追踪 |

逐成员状态无需新表或新公共枚举：模型专用合同保存在[运行时导出的schema](../design/socai2-incident-diagnosis-answer-v1.schema.json)，正式诊断映射为原Finding结构。`summarized`表示模型给出概述，不表示原始证据充分；`not_reviewed`不能带伪造来源。通用diagnosis JSON仍只含原来的conclusion、validation_state、findings、source_refs、limitations。

## 四个具体例子

**两条有效分诊：** 事件包含进程告警A1和网络告警A2，两条已完成A Run且材料仍一致。I冻结两条分诊，分别作为prior_analysis；替身模型逐成员给出未决判断，并保存一个跨成员推断和一个需人工确认的问题。测试读回2个成员Finding＋1个共享Finding、完整来源及用量；成员告警整行保持。共同主机不能直接证明进程导致外联。

**三条成员、只有一条分诊有效：** A1的分诊仍current；A2分诊后告警描述变化，即使材料ID相同也判过期；A3有旧分诊但没有可核验来源Run。输入原件保留三份旧分诊，模型正文只收到A1分诊，三条成员仍全部列出。A2/A3留下triage_not_used限制，不能写成它们没有风险。

**执行期间移走一个成员：** I开始时冻结A1/A2，模型尚未返回时移走A2。本轮仍按两条的原输入生成历史诊断，outcome为input_changed，当前指针不更新；相同operation_key不会重新派发。之后新Case冻结时不采用过期诊断，旧Case已冻结内容不回填。

**输出或提交不合格：** 漏掉A2、让A1引用A2专属来源、未上报用量都会保留失败尝试及原回复，已有成功诊断指针保持。请求事务提交失败时模型调用数为0；正式发布事务失败时诊断正文/当前指针整体回滚，原回复保留、执行记unknown。系统不自动重试。

## 验证与后续

- 9个新检查和5个受影响回归首次通过；5批均使用21既有独立合成PostgreSQL，实际执行冻结/新鲜度/发布SQL和事务回滚，模型全部替身。受限测试角色与隧道已清理。没有真实模型、湖、厂商或生产数据调用，没有新容器或DDL。
- 覆盖有效/过期/旧分诊、全成员与引用隔离、幂等重发、输入变化、停用/unknown、请求先提交、发布原子性、Case历史及旧I快照兼容、输入预算和租户边界。首次静态检查的闭包绑定、导入及重复pass规则提示已处理，业务测试没有失败回执。
- [固定测试回执与源码指纹](../operations/socai2-incident-diagnosis-20261104.json)保存这5批证据；本批不证明真实模型判断质量，旧r13仍暂停、5.3未完成。
- 现有四条A/I只读接口可读诊断与未决；完整告警/事件页面字段DTO、步骤/用量出口和逐项页面对照是下一项3.3。事件Case关系、H人工记录、必要外部来源及生产迁移/真实验收仍待。Q业务暂缓，只保留接口。

实现入口：[执行器](../../services/api/app/socai2/incident_diagnosis_executor.py)、[模型合同](../../services/api/app/socai2/incident_diagnosis_contract.py)、[输入及新鲜度SQL](../../services/api/app/socai2/stage_inputs.py)、[共享领取/发布服务](../../services/api/app/socai2/stage_results.py)。
