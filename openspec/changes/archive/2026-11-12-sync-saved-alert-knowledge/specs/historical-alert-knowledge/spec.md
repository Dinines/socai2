## MODIFIED Requirements

### Requirement: Explicit historical import follows saved judgments and preserves current version selection
历史告警知识 SHALL 保留现有显式入库及索引入口，在材料、事件时间和至少一份可用且对应所选材料的分诊／人工反馈保存成功后选入。仅有失败原答、没有判断或只有不对应材料的判断不得成为当前可用案例。系统 MUST 保留原文和对应状态，不把人工陈述、已关闭案件、模型 verdict 或未执行建议自动提升为已核实经验；仅在明确配置启用时允许已提交且被采用的告警分诊触发本次告警同步，不因原始告警到达或 Case H 保存触发。

#### Scenario: A source has just arrived or a usable judgment has been saved
- **WHEN** 告警刚接入而无可用判断，或已经保存可用分诊／人工反馈并被显式指定
- **THEN** 前者只保留业务原件并返回未入库原因，后者保存有源版本的参考卡并显式索引；索引成功与判断可信性分别表达，模型判断仍标为未独立核实

#### Scenario: Feedback or material changes after a card was indexed
- **WHEN** 所选材料或有效分诊／人工版本变化，后续显式导入该告警
- **THEN** 新源内容产生新快照，相同内容保持同一身份，旧卡和旧 Run 保留；新检索只采用与当前源指针和内容对应的可用快照，新卡尚未索引时不回退采用已过时卡

## ADDED Requirements

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
