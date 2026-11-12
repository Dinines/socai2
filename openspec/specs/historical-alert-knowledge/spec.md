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
历史告警知识 SHALL 保留现有显式入库及索引入口，在材料、事件时间和至少一份可用且对应所选材料的分诊／人工反馈保存成功后选入。仅有失败原答、没有判断或只有不对应材料的判断不得成为当前可用案例。系统 MUST 保留原文和对应状态，不把人工陈述、已关闭案件、模型 verdict 或未执行建议自动提升为已核实经验；仅在明确配置启用时允许已提交且被采用的告警分诊触发本次告警同步，不因原始告警到达或 Case H 保存触发。

#### Scenario: A source has just arrived or a usable judgment has been saved
- **WHEN** 告警刚接入而无可用判断，或已经保存可用分诊／人工反馈并被显式指定
- **THEN** 前者只保留业务原件并返回未入库原因，后者保存有源版本的参考卡并显式索引；索引成功与判断可信性分别表达，模型判断仍标为未独立核实

#### Scenario: Feedback or material changes after a card was indexed
- **WHEN** 所选材料或有效分诊／人工版本变化，后续显式导入该告警
- **THEN** 新源内容产生新快照，相同内容保持同一身份，旧卡和旧 Run 保留；新检索只采用与当前源指针和内容对应的可用快照，新卡尚未索引时不回退采用已过时卡

### Requirement: Adopted alert triage can synchronize knowledge after commit
系统 SHALL 仅在显式配置启用、本次新分诊事务成功提交且采用为当前判断后，对该租户的该告警尝试一次知识同步。同步 MUST 重新核当前判断与材料资格，使用独立会话和配置时限，复用现有卡片身份与索引；不得在原判断事务中访问嵌入／向量服务、启动新分析 Run、重调模型或自动扫描历史。

#### Scenario: A newly adopted triage commits while synchronization is enabled
- **WHEN** 新告警分诊提交且被采用，来源仍对应本次判断及有效材料
- **THEN** 提交后保存同步意图，入库当前卡片并索引，记录实际结果；原分诊返回及判断字段保持，新的知识只沿现有历史检索规则消费

#### Scenario: Synchronization is disabled or the result is ineligible for triggering
- **WHEN** 配置关闭、原事务未成功、结果未采用、执行失败／unknown，或请求只是重读已结束的同一 Run
- **THEN** 不自动写知识、调用嵌入或重派同步；原业务结果和已有历史记录保持

#### Scenario: The source changes during synchronization
- **WHEN** 本次分诊已被替代、材料已变化，或索引期间源版本改变
- **THEN** 保存具体跳过或来源变化原因，不把别次判断或过期快照报告为本次当前可用结果；旧卡保留，新检索仍核当前来源

### Requirement: Knowledge synchronization receipts remain separate from triage results
系统 SHALL 在既有工件中分别保存本次同步意图及实际结果，包含触发身份、源版本、文档／索引身份、配置、时间和原因，并通过原关联读取。系统 MUST 区分分诊保存、知识保存、索引完成和来源当前性；知识错误不得回滚分诊、改写原判断、伪造索引成功或自动重试未知执行。

#### Scenario: A card is stored but indexing fails
- **WHEN** 当前卡片已保存，随后索引明确失败
- **THEN** 保留卡片与失败回执，原分诊按其原完成／采用状态读取；不宣称知识已可检索，不新增模型调用

#### Scenario: An external write is unconfirmed
- **WHEN** 已有同步意图但缺结束回执，或写请求是否成功无法确认
- **THEN** 原工件及未知结果保持可追溯，不当作成功、查空或自动重试许可；显式维护先核实际现状

#### Scenario: A synchronization receipt is read
- **WHEN** 经同租户的原 alert／Run trace 和工件入口读取本次维护结果
- **THEN** 能核对原判断、卡片、索引与真实调用，读取不触发同步或模型；告警交接字段及原 publication 内容不变
