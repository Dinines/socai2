# C1整案输入：字段来源、冻结规则与验证

后续状态：[C2背景查询与模型视图](socai2-baseline-c2-20261103.md)已另批实现并验证；以下“尚未构建模型提示词”描述C1原批完成时点，原验证回执保持。

2026-11-03。本批完成新socai2存储路径的C1数据准备，并接入基础调查领取事务。已保存整案输入、六项必答问题、来源类型及缺口；**尚未构建模型提示词，也未运行C2–C6、Deep、Graph或Tool**。完整设计仍以设计工作树的 investigation-planning-design.md 为唯一正文。

## 数据从哪里来

| 输入 | 具体存储来源 | 本轮保存及语义 |
| --- | --- | --- |
| Case标题、说明、业务状态、范围版本 | cases当前行 | 保存当时整行及row_version，后续编辑不改变旧轮；作为案件资料/标签，不当检测观察 |
| 全部成员及纳入来源 | case_alerts→alerts | 不取头3条、不静默截成员；保存added_by、membership_source、source_operation_id等纳入记录 |
| 原始材料 | alerts.latest_material_id→alert_materials | run_members固定版本ID；C1保存revision、时间、hash、保留状态、检测标签、富化、来源范围；大段raw_text/raw_json/ocsf_json不重复复制，通过已冻结ID读取原不可变版本 |
| 对象及来源事件 | alert_objects、alert_source_refs，严格匹配同告警同material_id | 保存对象类型/角色、source_path、资产匹配和来源编号；不从另一版本拼对象 |
| 分诊及人工反馈 | latest_triage_id/latest_feedback_id→alert_assessments | kind分开；原判定、理由、置信度、计算状态、producer、actor、时间及输入material_id保留。人工改判不与旧分诊高分混配；材料版本不匹配明确标注 |
| 关联事件 | case_incidents显式关系，与成员告警incident_alerts关系取并集 | 保留事件资料、与本Case重合成员、事件全部成员ID、实际成员归并依据。事件包含案外成员时明确标范围更大，不扩大本Run告警范围 |
| 事件诊断 | incidents.latest_diagnosis_id→incident_diagnoses | 固定诊断版本、source_run_id、输入工件、source_fingerprint、状态/时间/正文。只有completed且validation_state=accepted、成员有交集，才作为可用历史分析；失败/运行中/未验明确标注。未重新计算材料新鲜度，不宣称诊断已重新核实 |
| 当前人工任务 | tasks.current_revision_id→task_revisions | 所有当前版本及状态均保存；只有completed且结果文本非空才进入可用人工反馈引用。完成者/完成时间、声明范围保留；进行中任务仅为执行记录，不是人工事实 |
| 案件当前判断 | cases.current_assessment_id→case_assessments及sources/members | 保存具体判断版本、来源、覆盖和原scope_revision；范围旧于本Case时标assessment_scope_outdated，不改写历史 |
| 当前判断引用的旧人工版本/工件 | case_assessment_sources的确切外键 | 即使任务当前版本已变，原被采用的task_revision仍分别保存；工件固定ID、hash和保留元数据，不用同名新工件替换 |
| 选用历史结果 | 当前判断的result依据，加启动请求明确的comparison_result_id | 保存原结果内容、实际成员交付、来源/有效性。不会把“最后完成的一条”自动加入；未采用AI保存结果也不会仅因最新而成为当前认识 |
| 六项问题 | 当前主设计4.1节 | 检测事实、成员关系、行为性质、授权、影响、覆盖/后续；均以open开始，保存scope和证据要求，不把旧判断预填为本轮答案 |

原厂未知仍为空；接入编号与厂商编号仍分开；检测标签和系统分数不转成攻击事实。Fusion收到之前缺失的内容只记录输入限制，不增加上游补数待办。

## 一致性与工件结构

领取时仍按Case→Run加锁。C1使用**一个PostgreSQL SELECT语句的读视图**，同时读取所有当前指针及对应版本；随后run_members直接使用这次选择的材料/分诊/反馈ID，避免再次读取latest指针拼出不同版本。事务提交running后才调用执行器，模型和Tool不在锁内执行。

使用现有artifacts表，不新增列、枚举或DDL：

1. `source_snapshot` / `schema_version=socai2.baseline-context.v1`：具体Case、成员、事件、诊断、任务、当前判断、选用历史、问题、遗漏及可引用路径。
2. `input_snapshot` / `projection_version=socai2.baseline-manifest.v2`：保持已有通用合同；引用上述C1工件和实际选用材料/人工版本/历史结果。完整C1缺口同时写入其omissions，旧读取方不会只看到一份空缺口清单。
3. `run_members`：固定材料/分诊/反馈版本。准备阶段不把元数据读取标成模型已读或已分析。

C1专用合同由Pydantic实际校验，[对应JSON schema](../../services/api/app/socai2/baseline_context.schema.json)与类型定义一致。原38种通用JSON合同保持；本合同细化其中source_snapshot允许的raw_payload内容，不改现有input_snapshot结构。复制到设计树的同名合同用于审阅，运行时以本后台代码为准。

沿用现有源快照128KiB保留上限。C1元数据/正文快照超限则本次准备失败，返回baseline_context_too_large，pending和旧输入保持；不静默截断成员，不提高模型额度。原始日志不复制进这份快照，原材料自身的truncated/unavailable状态仍保留。JSON null不当成已有原文。这个上限是当前准备边界，不能宣称任意规模Case已经验收。

## 读取、引用与例子

服务新增`read_context(tenant_id, case_id, run_id)`和`read_material(..., material_id)`。前者只读已保存C1并核hash，后者只允许该基础Run已经领取时固定的材料版本。GET不写业务时钟或读取状态；旧manifest.v1若没有C1工件，返回frozen_c1_context_not_available，绝不临时用现在的数据重建“历史输入”。

例如C100当前有A1、A2，材料M1、M2；I1的诊断为D3；人工任务H1当前版本V2；当前判断J4仍引用H1的V1。

- 启动R1时，C1保存A1/A2、M1/M2、D3、当前H1/V2，同时单独保留J4采用的H1/V1。两版不会互相覆盖。
- 之后用户改Case说明，H1提交V3，A1收到M3；R1读取的仍是原说明、V2以及J4依据V1，原文仍读M1。数据库中的最新数据可以变化。
- 如果I1还包含案外A3，C1记录I1范围更大，R1仍只有A1/A2；归并依据仍只是来源分组标签，不是因果链。
- H2还在进行中时保存其任务版本和未提交提示，但不把H2作为已完成反馈引用，也不凭“未反馈”推断“没有授权”。

C1工件有明确可引用路径和语义。例如`$.tasks.<task_id>.revision`对已完成反馈为human_statement；分诊和事件诊断为prior_analysis；成员纳入记录为execution_receipt；检测/对象/归并标签为source_label。结果发布会拒绝不存在的C1路径或错误角色，不能把人工说法通过改role冒充工具观察。这只是来源归属校验，不是对模型文字真实性的证明。

## 验证与剩余工作

11项C1检查最终通过，另外定向回归10项原存储检查；均连接21现有PG16.15的独立合成库socai2_schema_review_20261103_a1。覆盖五成员完整输入、原文按旧版本读取、后续编辑保持、真正双会话指针变化、同次评分与人工改判分开、事件范围/失败诊断、旧人工依据与当前版本、明确历史选择、引用角色/路径、超限回滚、跨租户、旧轮不补造输入、JSON null及截断。10项回归覆盖单次派发、两种成员竞争顺序、发布回滚、旧范围和较新人工判断等。

首批C1为8过2失败：并发测试在持有Case FOR UPDATE锁时等待新task_revision的延迟FK提交，被锁阻塞而超时；改为预建不可变版本后并发更新现有指针，验证真正可并行的场景，没有放松Case锁。另一测试将同一告警分配多个事件，违反incident_alerts唯一归属；改为不同成员对应不同事件。原失败保留，后续仅复核受影响/新增项，不称一次首过。各批临时受限账号和SSH隧道已删除，没有新建容器或修改业务库。详见[本批回执](../operations/socai2-baseline-c1-20261103.json)。

下一接C2及执行器模型视图：使用这份冻结输入，按证据来源构建有界且经过guard的模型视图，获取必要背景并保存请求/产物，再接领域分析、Deep、Graph及C6。当前快照本身不直接作为模型提示词；没有绕开原安全边界或提高模型预算。诊断新鲜度尚未重算，材料更新不自动重跑；完整调查、HTTP鉴权/DTO、告警事件新表写入、人工/AI业务入口和业务库切换仍未接通。页面不改，报告修复暂停，r13不重试，5.3未完成。
