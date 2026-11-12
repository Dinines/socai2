## MODIFIED Requirements

### Requirement: Model knowledge inputs are deduplicated and selected for the current task
C3、Deep、C6 SHALL 使用本 Run 冻结且适合当前任务的知识，按原知识身份/版本去重并保留所有查询出处和独立角色；反馈复核可将所选原调查的相关知识及必要引用冻结进新 Run，保留原 Run/版本，不称为本轮新检索或当前最新版。模型输入 MUST 先满足本案必要材料、反馈及前序引用，再按配置容量选择完整可选条目；不得改写正文、把同卡多命中计为多份证据，或丢弃仍需使用的前序/相反依据。

#### Scenario: Multiple queries retrieve the same historical card
- **WHEN** 多个成员或目的命中同一知识块/历史快照
- **THEN** 原检索行保留，模型只接收一份正文及其用途/出处；历史分诊和人工正文各自角色可定位，不混合不同版本或主体

#### Scenario: A Deep question or final delivery needs prior knowledge
- **WHEN** 当前问题或前序结论引用了本轮知识，另一些知识与本步无关
- **THEN** 优先恢复必要依赖，仅选择相关可选知识，记录排除原因；C6 不重新检索最新正文

#### Scenario: Feedback review reuses knowledge from an earlier investigation
- **WHEN** C6-only 复核依赖原调查的某个技术解释/历史参考
- **THEN** 冻结该片段原文、原 Run/知识身份与版本并恢复引用，注明历史参考，不重新检索整库或冒充新观察

## ADDED Requirements

### Requirement: Stage templates keep reference knowledge separate from current evidence
固定阶段母版 SHALL 定义本步目标、来源角色和输出内容，由程序装配当前范围/观察、前序判断、人工陈述、实际查询状态及必要知识。完整 Case SHALL 沿现有 C2 三目的检索向 C3/Deep/C6 提供技术解释、取证指导和历史比较；反馈复核只复用相关冻结条目。本项 MUST NOT 为 A/I 新增知识检索、增加知识总结模型、按用途新建物理库，或用知识/相似度替代本案事实和授权。

#### Scenario: Retrieval returns more material than a stage can use
- **WHEN** C2 候选较多或有重复/不适用条目
- **THEN** 沿现有用途/条件过滤与配置预算选入完整条目，保留原候选/遗漏原因；必要证据优先，无法容纳时明确受限，不循环补搜或语义改写凑容量

#### Scenario: Method guidance suggests a query
- **WHEN** 模型用取证指导提出应查日志或参考历史案例解释差异
- **THEN** 建议仍由现有问题/工具派发约束控制；实际查询与知识建议分别保存，不能因引用合法就认定事实或处置成立
