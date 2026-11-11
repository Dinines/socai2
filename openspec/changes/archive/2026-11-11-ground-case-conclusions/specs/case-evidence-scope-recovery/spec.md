## ADDED Requirements

### Requirement: 当前模型不得重新生成程序所有的固定事实
新 Case 边界 SHALL 冻结程序所有字段的职责。C6 的 coverage 问题和 C3/C6 observed finding 的 statement 由程序按实际输入与已接收输出装配；对外保存 SHALL 保留原六问及字段结构，历史冻结边界保持读取兼容。

#### Scenario: 查询覆盖由程序汇总
- **WHEN** C6 返回其余五个业务问题和分析
- **THEN** 程序用成员读取/分析状态、来源遗漏、逐项真实查询回执、问题、冲突、后续需求与执行记录补齐 coverage
- **AND** 未记录、失败、未知、未查和有效零结果保持区别，partial 仅统计实际保留单元，不能据此宣称安全或调查完成

#### Scenario: 直接观察只呈现原字段
- **WHEN** 模型选择合法原始 observation 形成 observed finding
- **THEN** 程序按成员及原记录分组呈现所选路径和值，不补方向、因果或内外网判断
- **AND** 新模型擅自提交 observed.statement 或 C6 coverage 时明确拒收，超长内容明确失败而不静默删改，原答与装配结果分别保留

### Requirement: 当前 Case 冲突必须具有可核验的原始支持
系统 SHALL 在新 C3/C6 生成、接收、一次反馈和 partial 路径中，对冲突引用及其参与发现采用同一来源规则：参与发现须有相应成员的直接 observation 支持，冲突引用须覆盖各方支持且至少涉及两个不同原始来源；查询回执、标签、前序判断及仅查询绑定不得充当冲突事实依据。该规则 MUST NOT 修改历史读取合同或将被拒收的 C6 总结重新采用。

#### Scenario: 缺资料的发现不能成为冲突的一方
- **WHEN** 一个冲突引用的发现只有查空、未查询、标签或前序判断支持
- **THEN** 新响应明确拒收该冲突，反馈说明缺失的原始支持，partial 只保留通过校验的独立部分并记录排除原因
- **AND** 不得仅删除冲突中的回执编号或随意增加观察编号来绕过逐 finding 的支持覆盖检查

#### Scenario: 有原始观察依据的推断可参与冲突
- **WHEN** 两条发现均有各自成员的直接观察支持且冲突引用覆盖这些支持
- **THEN** 来源门禁允许保留 observed 或 inferred 的原状态，正文是否互斥仍须单独验收

### Requirement: Deep and final inputs preserve explicit evidence boundaries

Case 输入构建 SHALL 保留原始来源与正文，在业务模型视图中按配置排除 Case 登记 title/description，并在依赖恢复时采用相同投影。动作字段含义和阶段指令 SHALL 明确缺资料不作反证、命令文本/启动不作结果、来源标签不证明环境或授权；原件和独立人工陈述保持。程序 MUST NOT 改写失败原答或补造引用追认质量通过。

#### Scenario: Approval or exercise records are not provided
- **WHEN** 当前材料没有审批或演练计划
- **THEN** 指令明确只能作为待核缺口，保留模型原答及其实际校验/采用状态，不由程序补造业务授权

#### Scenario: The input describes a local investigation or acceptance run
- **WHEN** Case 登记 title/description 描述本次验证/调查方式
- **THEN** 当前模型视图按配置排除这些字段并记录遗漏，旧引用恢复也不重新带入，原数据库内容不变

#### Scenario: An activity is observed but its effect is not established
- **WHEN** 输入包含命令行、activity.action 或 activity.outcome 字段
- **THEN** 按配置在原值旁标明同一记录/动作及结果边界，impact 问题指令区分动作、有据结果与未知影响，不改原值

### Requirement: Known narrative quality issues remain explicit during functional delivery

系统交接与验收记录 SHALL 区分程序合同接收和模型正文质量。按项目负责人 2026-11-11 的明确决定，持续出现的标签推环境、自由正文误写查询状态 SHALL 登记开放，保留原答/失败和 NOT_PASSED 质量结论，允许已验证的程序功能交付和后续功能继续推进，不将它们伪记为修复。

#### Scenario: A repeated narrative issue is deferred by the project owner
- **WHEN** 重复问题已具有实际原答、保存读取证据，且负责人明确决定记录后置
- **THEN** 在问题清单、交接与审计中说明后置范围和未解决状态，不重新采样追求一份通过答案，也不把 accepted、当前采用指针或 HTTP 成功作为质量通过证据

### Requirement: Case query coverage remains tied to program receipts

Case 输入的程序查询记录与程序装配的 coverage 状态/数量 SHALL 来源于实际回执，区分有效零结果、未执行、明确失败和不确定。阶段指令明确由模型解释调查限制，程序回执与模型正文分别保存以便发现偏差；自由正文残余误述按已知质量问题记录，不宣称已被自动语义校验阻断。

#### Scenario: Completed empty queries coexist with skipped queries
- **WHEN** assets/knowledge 查询完成零行，而其他来源未执行
- **THEN** 输入和交付能够分别定位两种状态，未执行来源不得呈现为已查零行，零结果不能成为安全或事件未发生的证明

#### Scenario: A source did not provide a confirmed successful result
- **WHEN** 查询回执为 failed 或 unknown
- **THEN** 保留相应状态和实际原因/未知信息，不补零行或完整覆盖，不因模型或报告阶段完成改变该回执语义

### Requirement: Current C3 followup generation and acceptance share a frozen bound

本 change 的新 C3 执行路径 SHALL 从冻结 Case 配置取得每份响应的补查上限，当前值为 2，提示、生成 Schema、接收及局部结果保留 MUST 使用同一值。超限补查集合 MUST NOT 被截取、改写或直接派发；保留原答和校验原因。原有范围/预算/依赖检查仍须通过；该限制不改变六类冻结问题身份、历史工件读取或 C6 后续建议用途。

#### Scenario: Two otherwise valid followups are returned
- **WHEN** C3 返回两项合法绑定/成员/问题范围的补查，且后续执行门禁满足
- **THEN** 数量检查通过，派发继续接受原有预算、依赖和去重约束，不增加运行额度

#### Scenario: Three followups pass all other checks
- **WHEN** 新 C3 原答含三项补查，或该原答进入 partial 审查路径
- **THEN** 记录数量错误，该超限集合零实际派发，不默取前两项；若按既有机制获得另一次合法纠正回答，只有新回答重新通过全部约束后才可派发

#### Scenario: An earlier saved artifact contains more than two followups
- **WHEN** 读取基于此前冻结合同保存的合法工件
- **THEN** 原记录继续可读且不重写，其历史内容不会因为本次新生成/接收限制被截断、改状态或重派
