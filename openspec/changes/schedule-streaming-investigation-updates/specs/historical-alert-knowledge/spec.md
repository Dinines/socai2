## MODIFIED Requirements

### Requirement: Adopted alert triage can synchronize knowledge after commit
系统 SHALL 仅为本次新采用且材料对应的A，在业务事务内保存持久知识维护task；A提交完成 MUST NOT 等待嵌入/索引。knowledge_sync由同一调度器最低优先级执行并计入总N，不新建分析Run，沿原卡片身份/源资格/配置时限保存回执。统一目标版本替换旧提交后等待路径，显式维护也经过执行保护，MUST NOT 同时双派发或扫描历史回填。

#### Scenario: A newly adopted triage commits while synchronization is enabled
- **WHEN** 同步配置开启且新A判断被采用
- **THEN** A与维护意图持久化后A即可结束，后续任务保存卡/索引；受理不等于已可检索

#### Scenario: Synchronization is disabled or the result is ineligible for triggering
- **WHEN** 同步关闭、事务失败、A未采用/unknown、只重读，或仅Case H/告警人工反馈变化
- **THEN** 不自动派发知识维护，不改原判断和历史

#### Scenario: The source changes during synchronization
- **WHEN** 待领取维护的源已被更新，或索引过程中源变化
- **THEN** 重新核资格并保存被替代/来源变化回执，旧卡保留，不把过期卡报告为当前有效

### Requirement: Knowledge synchronization receipts remain separate from triage results
系统 SHALL 沿原A Run trace/工件读取维护意图、实际源版本、配置、起止、卡片及索引状态；内部knowledge任务不进入公共分析任务列表，不改变告警交接字段。失败 MUST NOT 回滚业务判断、伪造成功或自动重放未知外部写；模型分析和知识维护的状态分别保存。

#### Scenario: A card is stored but indexing fails
- **WHEN** 卡片已保存而索引明确失败
- **THEN** 保留卡及失败回执，A仍保持真实完成/采用状态，不称知识已可检索

#### Scenario: An external write is unconfirmed
- **WHEN** 知识写请求已发出但结果未知
- **THEN** 保留未知回执，本地收尾释放名额，不自动重试未知写、不要求人工解锁队列

#### Scenario: A synchronization receipt is read
- **WHEN** 用户读取原A Run的trace/工件
- **THEN** 可区分受理、被替代、卡片保存和索引完成，读取不派发新同步
