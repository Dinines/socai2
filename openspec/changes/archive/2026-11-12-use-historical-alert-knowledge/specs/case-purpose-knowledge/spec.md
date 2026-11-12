## MODIFIED Requirements

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
