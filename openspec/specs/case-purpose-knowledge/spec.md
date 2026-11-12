# case-purpose-knowledge Specification

## Purpose

让 Case C2 从冻结材料按技术解释和取证指导分别检索知识，以原生本地嵌入及 PG 原文身份建立可追溯来源，供 C3/Deep/C6 使用；知识始终保留指导用途和真实查询边界。

## Requirements

### Requirement: C2 retrieves knowledge for explicit investigation purposes
C2 SHALL 在同一 Run 的冻结材料上按 `technical_explanation`、`investigation_guidance` 及配置启用的 `historical_case_reference` 构造不同查询。各目的 MUST 声明查询依据、模板、资料类型/过滤和使用边界，保留原始来源路径与角色；所有可变参数由显式配置提供，不新增生成模型调用来编造查询事实。

#### Scenario: The same technical observation serves two different questions
- **WHEN** 冻结材料具有适用技术主题且 C2 知识来源可调用
- **THEN** 技术解释查询面向行为功能/条件，取证指导查询面向所需证据/方法，各自保存实际输入、过滤和命中；检测标签仅作为检索线索

#### Scenario: The same observation serves different knowledge goals
- **WHEN** 冻结材料具有适用主题且 C2 知识来源可调用
- **THEN** 技术解释面向功能/条件，取证指导面向证据/方法，历史案例参考面向既往观察和判断比较，各自保存输入/过滤/命中；检测标签仅作为检索线索

#### Scenario: No suitable topic or tool budget is available
- **WHEN** 某目的缺少适用主题或必须的时间边界，或 C2 未执行知识查询
- **THEN** 保存实际缺项或未查询原因，不补造查询、命中或完成状态，不提高总调用额度

### Requirement: Knowledge indexing and retrieval preserve document and embedding identity

系统 SHALL 通过既有文档导入及明确索引入口关联 PG 原文档块与本地嵌入索引，记录内容 hash、模型、维度及目的分类。检索 MUST 使用同一模型空间，并核命中仍对应目标原文；不得通过维度补齐/截断混用模型或将过期向量当当前正文。

#### Scenario: An ingested document is indexed and retrieved
- **WHEN** 指定有来源的文档块被成功索引，适用目的查询返回命中
- **THEN** 命中可回到同一原文身份/hash，C2 保存实际片段和检索元数据；资料类型、来源和用途保持

#### Scenario: Embedding or index retrieval fails
- **WHEN** 嵌入/索引调用失败、模型空间不匹配或原文对应失效
- **THEN** 保存具体不可用/失败原因及已有执行边界，不以空列表报告成功，不静默改用另一来源冒充原检索

### Requirement: Retrieved knowledge remains guidance in frozen downstream inputs

C2 SHALL 按目的保存真实输入、输出、状态和限制到本 Run 的步骤及工件。C3、Deep、C6 SHALL 从这些工件选择符合当前判断目标的内容，保留可追溯引用及非观察来源身份；知识 MUST NOT 成为本案行为、环境、业务授权或响应已执行的证明。

#### Scenario: Technical knowledge guides an investigation
- **WHEN** C3 使用技术解释或方法片段提出待核事项/补查，后续 Deep 或 C6 使用该片段
- **THEN** 每次实际输入都保留片段身份和目的，后续结论仍依据本案证据，补查继续由现有合法候选和派发流程控制

#### Scenario: A search succeeds without relevant results
- **WHEN** 查询真实完成但没有符合条件的知识片段
- **THEN** 保存成功查空及范围，后续可用证据调查继续，不把无知识解释为安全、不强制填入通用知识

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
