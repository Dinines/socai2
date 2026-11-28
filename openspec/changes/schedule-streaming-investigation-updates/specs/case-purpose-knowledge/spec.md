## MODIFIED Requirements

### Requirement: Model knowledge inputs are deduplicated and selected for the current task
C3、Deep、C6 SHALL 使用本Run冻结且适合本步骤的知识，按真实身份/版本去重并保留查询出处与独立角色。模型输入 SHALL 先满足本案必要材料、人工反馈、反证及前序引用，再按配置容量选完整可选条目；MUST NOT 改写正文、将同卡多命中计为独立证据或丢弃必要来源凑容量。Case自动更新和用户完整重跑仍走完整C1–C6，不新增反馈专用C6-only路径。

#### Scenario: Multiple queries retrieve the same historical card
- **WHEN** 多个成员/目的命中同一知识块
- **THEN** 原检索记录保留，模型收到一份正文及用途/出处，主体/版本和人工角色仍可定位

#### Scenario: A Deep question or final delivery needs prior knowledge
- **WHEN** Deep或C6依赖本轮前序使用的知识，另有无关候选
- **THEN** 优先恢复必要依据，只选择适用条目并记录排除原因；不再次检索或用旧结论取代真实依赖

## ADDED Requirements

### Requirement: Stage templates distinguish knowledge from current evidence
母版 SHALL 说明本步目标、输入角色和输出，由程序装配本轮观察、前序分析、人工陈述与必要知识。工具只提供任务所需业务结果，未查询只写未查询，执行台账留原工件。完整Case SHALL 复用C2技术解释/取证指导/历史参考三目的检索；A/I不新增检索，MUST NOT 增加知识总结模型、按用途另建物理库或用历史相似度证明本案结论。

#### Scenario: Retrieval exceeds a stage's useful capacity
- **WHEN** C2候选较多、重复或不适用
- **THEN** 按目的/条件与配置筛选完整条目，保留原候选及遗漏原因；必要输入放不下则明确受限，不语义改写或循环补搜

#### Scenario: A knowledge entry recommends a query
- **WHEN** 模型参考条目提出查询建议
- **THEN** 仍受现有问题/工具能力约束，实际查询与知识建议分别保存，引用合法不等于本案事实成立
