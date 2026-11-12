## ADDED Requirements

### Requirement: Historical cards and nested citations remain inspectable
4177 SHALL 在本 Run 知识节点展示历史目的的范围、过滤、历史告警/材料/判断身份、原观察/分诊/人工反馈与版本状态，并关联模型的卡片及子字段引用。页面 MUST 使用已保存回执，不重新检索，不将相似度或历史人工判断显示为本案可信度或授权。

#### Scenario: A model cites historical human feedback
- **WHEN** 本轮原答引用已进入输入的历史卡片人工反馈字段
- **THEN** 面板定位具体历史卡片、人工来源路径和输出位置，输入可见/原答引用/校验状态分别显示

#### Scenario: Historical knowledge was not retrieved
- **WHEN** 缺少时间范围、未执行、有效查空或失败
- **THEN** 显示已记录原因及真实状态，不因 C2 父阶段完成显示为知识已成功使用
