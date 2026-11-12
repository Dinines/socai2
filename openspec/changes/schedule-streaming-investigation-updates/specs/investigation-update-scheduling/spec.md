## ADDED Requirements

### Requirement: Saved business changes schedule only affected analysis subjects
启用新调度时，系统 SHALL 按同租户实际主体登记持久化待办：新告警/实质材料变化只触发该 A，成员/材料/已采用 A 变化合并相关 I 和活动 Case。业务提交及其源待办 MUST 原子保存；下游传播未完成不得丢弃待办。相同投递、GET、纯管理编辑、I 新总结及知识索引完成 MUST NOT 单独循环触发调查。I/Case SHALL 如实使用可取得的材料并标记未完成 A，不无限等待整个流或 I 结束。

#### Scenario: A new alert joins an incident under investigation
- **WHEN** A3 保存并归入已有事件，而 A1/A2 已被 Case 选入
- **THEN** 仅 A3 进入分诊，事件及符合跟随规则的 Case 合并待更新；A3 分诊采用后更新同一待办目标，不重新分诊 A1/A2

#### Scenario: Repeated delivery or reference maintenance completes
- **WHEN** 完全相同材料再次投递、读取状态或只保存一版 I 总结/知识索引回执
- **THEN** 不因此创建新的 A 或 Case 调查，原保存结果和已存在待办保留

### Requirement: Whole incident associations follow new members within explicit Case boundaries
新建或明确关联整个事件的活动 Case SHALL 纳入当前成员并跟随后续新增；单条告警关联 MUST NOT 隐式跟随其整个事件。人工移出 Case 的告警 SHALL 保持排除直到明确重新加入。已结束 Case SHALL 只记录关联新数据提示，不自动重开/扩范围；切换前旧关联保留快照方式，直到明确再次关联。事件移出成员 MUST NOT 隐式删除已纳入 Case 的调查材料。

#### Scenario: Automatic arrivals and manual membership edits coexist
- **WHEN** 活动 Case 跟随 E1，E1 新增 A3，人工另加入 A4 并移出 A2
- **THEN** Case 纳入 A3/A4、排除 A2，变化合并为一份待办；未来 E1 更新不把 A2 加回，冻结历史保持

#### Scenario: A closed or snapshot-only Case has related arrivals
- **WHEN** 已结束 Case 或尚未启用跟随的旧关联遇到事件新成员
- **THEN** 不自动扩范围或启动调查，能读取关联新数据/跟随状态；告警和事件自身仍按原触发规则处理

### Requirement: Each subject has one active execution and one coalesced successor
系统 SHALL 用主体身份而非 Run ID/告警数量合并待办；同 A、I 或 Case 最多一个活跃执行和一份待更新，Case full/final_review 共用槽。领取、冻结及单活跃检查 MUST 在外部调用前提交。后续变化不得修改已冻结输入，只更新后继目标；有完整调查原因时 MUST 合并覆盖仅反馈复核模式。unknown SHALL 继续占槽，不自动超时重派。

#### Scenario: Several alerts arrive while a Case run is active
- **WHEN** R1 已冻结 A1/A2，期间 A3/A4/A5 被纳入同 Case
- **THEN** R1 不重启，后继只保留一份最新范围待办；R1 明确结束且后继可执行后才领取 R2，R2 冻结当前完整范围

#### Scenario: A feedback review acquires new material before claim
- **WHEN** 仅反馈待办尚未领取而 Case 又有新成员或材料/有效 A 变化
- **THEN** 同一待办升级为 full 并携带适用反馈，不并行执行反馈 C6 和完整调查

### Requirement: Configured batching never slides indefinitely under continuous arrivals
所有周期、优先级、并发、轮询和开关 SHALL 由显式 profile 提供；初始建议 A 立即、I 60 秒、Case 自动更新 300 秒、全局并发 1。首次待办确定到期时间，后续合并 MUST NOT 推迟；人工明确请求可提前到期但不得抢占同主体 Run。自动任务 SHALL 按到期时间及首次登记顺序领取，不要求告警队列清空；知识维护较低优先。

#### Scenario: New alerts continue arriving after an incident becomes ready
- **WHEN** I/Case 已到期，仍有新的立即到期 A 进入队列
- **THEN** 已到期的较早自动任务保持顺序，不因新通知重置计时或始终排在所有 A 之后

#### Scenario: A user requests an immediate update during an active run
- **WHEN** 用户明确请求更新或提交有效反馈，而同 Case 已有活动/unknown Run
- **THEN** 合并并提升待办优先级，不启动第二个执行；现有槽释放后才能领取

### Requirement: Completed results remain scoped to their frozen inputs
系统 SHALL 保存每轮真实冻结范围、执行模式、输入/反馈/知识版本及采用结果，并提供运行/待更新状态读取；新材料到来 MUST NOT 改写旧 Run 或把旧覆盖报告为全量。现有新鲜度和当前判断保护 MUST 保持；仅 I 参考版本变化导致未采用时保留具体原因，不单凭此再跑全案。原 GET 及告警交接字段 MUST 保持，独立更新受理回执不得冒充执行完成。

#### Scenario: A run completes after the Case has grown
- **WHEN** R1 处理两成员期间 Case 增至五成员
- **THEN** R1 仍按两成员保存/读取，当前五成员范围及待更新另行呈现，采用按实际新鲜度判断，不伪造新增三成员已调查

#### Scenario: A queued update is read before execution
- **WHEN** 用户读取已受理但未领取的更新
- **THEN** 返回待办原因、到期时间及可用原结果链接，不显示模型成功、补查已执行或新结论已生成
