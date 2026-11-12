## ADDED Requirements

### Requirement: Knowledge selection checks purpose and comparable applicability conditions
C2 SHALL 在现有三目的检索中，以冻结材料的主题、原角色和 profile 指定的结构条件选择资料。系统 MUST 保留同租户／资料类型／目的过滤，以及历史窗口和当前成员排除；有明确适用条件冲突或缺必要条件的候选不得仅因相似度达标而进入模型。相同目的、主题和实际范围的查询可合并，但必须保留全部查询来源。

#### Scenario: A similar document belongs to an incompatible topic
- **WHEN** 候选相似度达标，但存在同语义、同命名空间的主题条件冲突，或缺少该目的必要条件
- **THEN** 候选被排除并记录原因；候选全被筛掉与原始无命中、未查、来源失败分别显示，不再补搜凑满

#### Scenario: Applicable knowledge is selected within existing limits
- **WHEN** 候选目的正确，至少一个声明的主题条件匹配、没有已知冲突，或是明确标注适用该主题的通用技术／方法资料
- **THEN** 在配置上限内回读核原文并选入，保留条件／未知和使用限制；相似度不作为事实置信度，历史卡片不能走通用兜底

### Requirement: Model knowledge inputs are deduplicated and selected for the current task
C3、Deep、C6 SHALL 只使用本 Run 冻结且适合当前任务的知识，按原知识身份／版本去重并保留所有查询出处与独立来源角色。模型输入 MUST 先满足本案必要材料及前序引用依赖，再按配置容量选择完整可选条目；不得改写原正文、把同卡多命中计为多份证据，或借精简丢弃仍需使用的前序依据。

#### Scenario: Multiple queries retrieve the same historical card
- **WHEN** 多个成员或目的命中同一知识块／同一历史快照
- **THEN** 原检索行均保留，模型只接收一份正文及其用途／出处；卡片、历史分诊、人工正文各自角色和冻结引用仍可定位，不合并不同版本或不同主体

#### Scenario: A Deep question or final delivery needs prior knowledge
- **WHEN** 当前问题或前序结论引用了本轮已冻结知识，而另一些知识与该任务无明确关联
- **THEN** 先恢复所需引用依赖，只选相关可选知识；容量或相关性排除有具体记录，历史空成员范围不自动代表全案适用，C6 不重新检索最新正文
