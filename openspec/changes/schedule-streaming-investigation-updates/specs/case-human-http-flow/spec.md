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
Case SHALL 将实际选入H及必要原材料按本阶段目标筛选，保留原文/范围/引用；反馈不得扩大工具能力或证明未取得的事实。运行中新人工采用 SHALL 沿既有新鲜度/采用保护处理，不被在途旧Run覆盖。模型读取附件正文非本期要求；评论/description/文件元数据 MUST NOT 冒充已经提供的调查证据。

#### Scenario: A statement applies only to a limited host and time
- **WHEN** H说明特定主机的某时段属于维护
- **THEN** 新调查仅在该范围使用人工陈述，其他成员仍按各自材料分析；保留独立原件和待核事项

#### Scenario: A user adopts another result while the current run executes
- **WHEN** R2已启动后用户明确采用另一个合格结果
- **THEN** R2仍保存真实结论和比较对象，但沿既有保护不得自动覆盖用户较新的采用

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
