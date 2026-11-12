## MODIFIED Requirements

### Requirement: Adopted alert triage can synchronize knowledge after commit
启用新调度及历史同步时，系统 SHALL 仅为本次提交且被采用的 A 判断，在采用事务内登记持久化维护意图，提交后由低优先级任务尝试同步；A 完成 MUST NOT 等待嵌入/索引。同告警未领取意图可合并到最新有效源，旧意图记录替代关系而非虚报成功。执行 SHALL 重新核判断/材料资格，沿用卡片身份、独立会话、配置时限和索引；不得在原判断事务访问外部知识服务、启动新分析 Run 或扫描历史。未启用新调度时保持原配置控制的提交后同步路径，两条路径 MUST NOT 同时派发。

#### Scenario: A newly adopted triage commits while synchronization is enabled
- **WHEN** 新调度/同步开启且 A 结果被采用
- **THEN** 判断与维护意图持久化成功后 A 可完成返回，worker 后续保存当前卡片及索引回执；仅排队不表示知识已可检索

#### Scenario: Synchronization is disabled or the result is ineligible for triggering
- **WHEN** 同步关闭、事务失败、结果未采用/unknown，或只重读已结束 Run
- **THEN** 不自动写知识、嵌入或重派维护；原业务结果/历史保留，原始告警及 Case H 保存不直接生成案例卡

#### Scenario: The source changes during synchronization
- **WHEN** 待领取意图被新采用判断替代，或已领取索引期间源版本变化
- **THEN** 分别记录意图被替代或来源变化；不把过期卡报告为当前可用，旧卡保留，新检索仍核当前来源

### Requirement: Knowledge synchronization receipts remain separate from triage results
系统 SHALL 沿原工件/关联读取记录维护意图、排队/被替代状态及实际保存/索引结果，包含触发身份、目标源版本、实际文档/索引身份、配置、时间和原因。系统 MUST 区分分诊保存、维护受理、知识保存、索引完成与当前性；失败不得回滚分诊/改写判断、伪造成功或自动重试未知外部写。

#### Scenario: A card is stored but indexing fails
- **WHEN** 卡片已保存而索引明确失败
- **THEN** 保留卡片和失败回执，原分诊保持完成/采用状态，不报告知识已可检索，不启动新分析

#### Scenario: An external write is unconfirmed
- **WHEN** 已发出知识写请求但是否成功无法确认
- **THEN** 保留原意图/未知状态，不将排队超时视为重试许可；显式维护先核实际现状

#### Scenario: A synchronization receipt is read
- **WHEN** 通过同租户原 alert/Run trace 或独立更新状态读取维护
- **THEN** 可区分待办、被替代和实际完成并定位原判断/卡片；读取不派发同步，告警交接字段及原判断内容保持
