# historical-alert-knowledge Specification

## Purpose

将同租户指定告警的材料、历史分诊与人工反馈保存为可追溯、分角色的知识卡片，供 Case C2 在明确历史范围内检索并冻结给 C3/Deep/C6 比较参考；来源真实不等于历史判断正确，历史知识不替代本案观察、授权或执行回执。

## Requirements

### Requirement: Historical alert cards preserve actual source versions and roles
系统 SHALL 通过显式入口从同租户指定告警的实际材料与分诊/人工反馈生成结构卡片，保存源身份、版本、原文和材料对应状态。卡片 MUST 区分历史观察、来源标签、已有判断及人工陈述，未独立核实的内容不得自动标为已核实案例或授权。

#### Scenario: An alert with recorded analysis is imported
- **WHEN** 指定告警具有可读取材料、事件时间及历史分诊或人工反馈
- **THEN** 保存可回溯的完整卡片，原记录不变，相同源内容重复入库返回相同身份；索引必须核原内容与来源对应

#### Scenario: A source cannot form a usable card
- **WHEN** 缺少材料/判断/时间或卡片超过显式配置容量
- **THEN** 返回未入库原因，不补造判断、不静默截断正文、不报告已索引

### Requirement: Historical case retrieval has explicit scope and model use boundaries
C2 SHALL 按 `historical_case_reference` 目的检索已入库历史卡片，限定同租户、明确历史时间范围并排除本轮告警。下游 MUST 保留原历史主体、版本和角色，只作为比较与方法参考，不转换为本案事实、授权或已执行响应。

#### Scenario: A historical card informs the current investigation
- **WHEN** 历史目的命中适用卡片并进入 C3/Deep/C6
- **THEN** 本轮冻结其原文和来源，模型可分别引用既往判断/人工陈述，原主体不被查询成员替换，实际输入与输出引用可核对

#### Scenario: Missing scope or an excluded current record
- **WHEN** 本轮缺少历史时间边界，或命中对象是当前告警/时间范围外记录
- **THEN** 不生成无边界历史查询或不接受该命中；未查询、查空和失败按实际状态保存

### Requirement: Explicit historical import follows saved judgments and preserves current version selection
历史告警知识 SHALL 沿现有显式入库及索引入口，在材料、事件时间和至少一份可用且对应所选材料的分诊／人工反馈保存成功后选入。仅有失败原答、没有判断或只有不对应材料的判断不得成为当前可用案例。系统 MUST 保留原文和对应状态，不把人工陈述、已关闭案件、模型 verdict 或未执行建议自动提升为已核实经验；本 change 不自动监听告警接入或启用入库调度。

#### Scenario: A source has just arrived or a usable judgment has been saved
- **WHEN** 告警刚接入而无可用判断，或已经保存可用分诊／人工反馈并被显式指定
- **THEN** 前者只保留业务原件并返回未入库原因，后者保存有源版本的参考卡并显式索引；索引成功与判断可信性分别表达，模型判断仍标为未独立核实

#### Scenario: Feedback or material changes after a card was indexed
- **WHEN** 所选材料或有效分诊／人工版本变化，后续显式导入该告警
- **THEN** 新源内容产生新快照，相同内容保持同一身份，旧卡和旧 Run 保留；新检索只采用与当前源指针和内容对应的可用快照，新卡尚未索引时不回退采用已过时卡
