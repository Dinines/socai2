# case-purpose-knowledge Specification

## Purpose

让 Case C2 从冻结材料按技术解释和取证指导分别检索知识，以原生本地嵌入及 PG 原文身份建立可追溯来源，供 C3/Deep/C6 使用；知识始终保留指导用途和真实查询边界。

## Requirements

### Requirement: C2 retrieves knowledge for explicit investigation purposes

C2 SHALL 在同一 Run 的冻结材料上分别按 `technical_explanation` 和 `investigation_guidance` 构造查询。各目的 MUST 声明查询依据、模板、资料类型/过滤和使用边界，保留原始来源路径与角色；所有可变参数由显式配置提供，不新增生成模型调用来编造查询事实。

#### Scenario: The same technical observation serves two different questions
- **WHEN** 冻结材料具有适用技术主题且 C2 知识来源可调用
- **THEN** 技术解释查询面向行为功能/条件，取证指导查询面向所需证据/方法，各自保存实际输入、过滤和命中；检测标签仅作为检索线索

#### Scenario: No suitable topic or tool budget is available
- **WHEN** 某目的缺少适用主题，或当前 C2 未执行知识查询
- **THEN** 保存未查询及实际原因，不补造查询、命中或完成状态，不提高总调用额度

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
