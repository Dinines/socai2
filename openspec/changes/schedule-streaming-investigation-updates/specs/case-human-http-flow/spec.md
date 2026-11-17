## MODIFIED Requirements

### Requirement: Human feedback remains an explicit versioned input to the next investigation
系统 SHALL 沿现有Case/H版本、原文、范围及来源合同保存反馈。有效已完成H正文/范围/引用变化或撤回 SHALL 进入下一次定时/手动检查，下一轮完整C1–C6冻结实际适用版本；MUST NOT 新增H-only/C6-only或以当前采用结果代替上一轮比较。草稿、空正文、范围不适用、同值保存和纯管理编辑不触发模型。人工输入 SHALL 保持human_statement角色，不自动成为业务授权/采用/结案，不冒充告警human_feedback。

#### Scenario: A user completes and revises feedback before starting the next run
- **WHEN** 用户完成并修订有效H，随后提交下一轮check/rerun
- **THEN** 完整调查在执行前读取并冻结当时适用的修订，保留原文/范围和旧结果，沿原Result读取

#### Scenario: Valid feedback changes while an investigation is running
- **WHEN** 用户修订适用H而R1已固定输入
- **THEN** 原H和R1输入不变，下次检查登记更新，后续完整调查冻结新版本；不并行运行额外C6

#### Scenario: Feedback is withdrawn or only its owner changes
- **WHEN** 原有效H被撤回，或只改变负责人/标题
- **THEN** 撤回进入更新判断并保留来源；纯管理变更不执行模型

#### Scenario: No result has been adopted yet
- **WHEN** Case有有效H但尚未采用调查结果
- **THEN** 后续完整调查可使用该H，不要求当前采用基线作为前置；上一轮无结论如实说明

## ADDED Requirements

### Requirement: New analyses preserve human scope and later adoption decisions
Case SHALL 将实际选入H及必要原材料按本阶段目标筛选，保留原文/范围/引用；反馈不得扩大工具能力或证明未取得的事实。运行中新人工采用 SHALL 沿既有新鲜度/采用保护处理，不被在途旧Run覆盖。人工定向及手动后续综合 SHALL 保持与有效H更新的区别；模型读取附件正文非本期要求；评论/description/文件元数据 MUST NOT 冒充已经提供的调查证据。

#### Scenario: A statement applies only to a limited host and time
- **WHEN** H说明特定主机的某时段属于维护
- **THEN** 新调查仅在该范围使用人工陈述，其他成员仍按各自材料分析；保留独立原件和待核事项

#### Scenario: A user adopts another result while the current run executes
- **WHEN** R2已启动后用户明确采用另一个合格结果
- **THEN** R2仍保存真实结论和比较对象，但沿既有保护不得自动覆盖用户较新的采用

### Requirement: User directed analysis may deliver a recommendation or a conclusion independently
人工定向分析 SHALL 允许围绕用户问题/方向及可选现有工具形成建议、结论或待核事项，不强制新增证据或重跑完整Case链。结果 SHALL 保存实际范围、所用材料/工具及未执行原因，建议不得冒充执行、局部判断不得冒充全案覆盖或自动采用。定向结果交付后 SHALL 结束该次任务，可在同次回答中给出继续综合的建议及原因，MUST NOT 因该建议或保存结果自动提交后续综合任务；不另开模型调用判断其价值，不设置永久方向字段。

定向任务 SHALL 使用kind=case_investigation、intent=targeted，RunKind/ResultKind=targeted；请求及实际输入分别保存，明确范围执行前重核，缺省范围按执行前当前Case。工具 SHALL 限现有允许的只读工具，不接收任意SQL或连接参数。结果沿任务/Run/Result与工件读取，不复用暂停的AI会话，也不新增公共执行身份层。局部成功/失败 MUST NOT 推进全案完成基线、刷新自动窗口或设置/清除主体自动更新的失败停止标记；MUST NOT 作为上一轮完整调查或直接采用的全案判断。

#### Scenario: Existing evidence supports advice without a new observation
- **WHEN** 用户指定一个问题，模型根据已保存材料给出下一步建议而未取得新证据
- **THEN** 可以保存并交付该次定向结果，明确来源及限制，不为满足流程而伪造发现或自动重跑全案

#### Scenario: A targeted result recommends updating the overall analysis
- **WHEN** 定向分析得到可能影响全案的新发现或新判断，并建议后续综合
- **THEN** 先保存和交付定向结果并结束本次任务；未收到用户手动触发时不生成续接任务，周期检查也不因该结果自身自动续跑

#### Scenario: A targeted tool is known but unavailable for this Case
- **WHEN** 用户选择现有支持工具，但本案没有执行该工具所需的可靠时间或来源条件
- **THEN** 保存未执行原因，保留其他分析及建议；不编造查询结果，也不因该局部问题停止普通全案更新

### Requirement: Users explicitly submit subsequent synthesis as a separate asynchronous task
后续全案综合 SHALL 由用户手动触发，持久受理新的task并返回task_id，实际执行时再关联新的run_id；原定向任务、Run、结果和输入输出 SHALL 保持原样。续接 SHALL 关联选定的定向结果与实际使用的完整调查记录，在执行前保存真实材料身份/版本/范围及必要前序，再复用适用证据完成必要的关联整理和全案综合，不一律重跑已有检索和分析。新结果 MUST NOT 冒称覆盖未纳入材料、伪造新的工具执行或自动覆盖当前采用判断。

续接 SHALL 共用同Case串行、Case优先级、全局N和已有失败规则；手动续接意图不能被普通check吞掉，同operation_key重放仍返回原task，不新增对外身份层。仅因没有新证据或模型未建议继续 MUST NOT 拒绝用户手动综合；必要前序材料不可用时应如实记录，不能以局部结果代替缺失的全案依据。

综合任务 SHALL 使用kind=case_investigation、intent=synthesis，RunKind/ResultKind仍为baseline；不新增synthesis结果枚举。客户端提交同Case的targeted_result_ids，程序确定适用完整前序，并将实际复用来源与上一轮比较对象分别记录；前序/范围不足时记录prerequisite_unavailable，不伪造完整交付。只有真实完成本轮固定全案输入才推进完成基线和活动窗口，普通initial/check与定向/综合不得互相归并。

#### Scenario: A user requests synthesis after a targeted conclusion
- **WHEN** 用户对已保存定向结果手动触发后续综合，此时同Case仍有其他任务运行
- **THEN** 返回新的task_id并等待；真正开始时创建新Run并固定实际复用材料，保留各来源及原定向记录，完成后可分别读取定向与全案结果

#### Scenario: A user repeats the same continuation submission
- **WHEN** 用户以相同operation_key和相同内容重送手动综合请求
- **THEN** 返回原task_id，不新增一次逻辑任务；普通check不能替代这次明确的综合请求

#### Scenario: Reused materials cannot support the requested synthesis
- **WHEN** 续接执行前无法取得必要的完整调查材料
- **THEN** 记录实际缺口，不伪造全案覆盖或悄悄重跑完整链；此前已交付的定向结果仍可读取
# 第7步比较读取增量

## ADDED Requirements

### Requirement: Case comparison identity is frozen and readable
The system SHALL freeze the preceding locally ended full Case investigation and its usable comparison result before execution. Case Run and Result reads SHALL expose that frozen comparison context, preserving an unavailable preceding Run without falling back to an older adopted result. Records without saved comparison context SHALL return null.

#### Scenario: Previous investigation has no usable result
- **WHEN** a new full investigation follows a locally ended failed or unknown Run without a usable conclusion
- **THEN** its comparison context preserves that previous Run ID, reports unavailable with a reason, and leaves comparison_result_id null
- **AND** later reads do not substitute a newer or older Run

#### Scenario: First investigation and historical records
- **WHEN** a newly prepared Case has no previous full investigation
- **THEN** it saves comparison state initial with no previous Run or Result
- **AND** historical records without this saved field remain null rather than inferred
