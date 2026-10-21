# C02：分诊材料、普通live缓存与停止清理

状态：**实施中；C01验收与独立审计已完成**。2026-10-20。承接[迁移审核R2/R4/R5](migration-review-20261020.md)、[C01执行卡](c01-fusion-delivery-plan.md)及用户持续迁移、每轮change审计的授权。本批不实施时间/授权理由提示词修复，也不把材料正确送达视为模型理解或完整质量通过。

## 限定变化

### R2：传递描述及事件发生时间

`services/agents/app/workers/fused_alert_consumer.py:build_state`在现有原告警投影中保留`description`及`event_time`，维持原值、缺失与null语义。事件发生时间来自告警，不能以处理时间、`created_at`或常规维护习惯补齐。继续保留tenant、canonical alert ID、source、source_event_ids、raw_event和风险分缺失/null/显式0的现有合同。

`services/agents/app/agents/auto_triage_agent.py`在原untrusted telemetry中提供独立描述、来源事件发生时间段，不能依赖Additional fields排序前10项或通用单值400字符压缩。明确展示缺失状态；描述使用有界、可辨认的裁剪标记，实际采用范围在捕获的完整messages中可核。原nonce、提示注入边界、五类reader状态和输出schema保持。继续执行完整messages账本8000字符、canonical UTF-8请求16000字节、输出512及SDK retry0/45秒限制，不通过扩容或隐式裁剪掩盖超限。

### R4：普通live停用跨告警pattern结论缓存

普通Kafka live路径不再直接采用CostGovernor按pattern缓存的跨告警verdict。该pattern有意排除描述、发生时间、原始事件与外部上下文版本，因此本批采用保守准入策略，避免新材料或新时间窗口沿用旧结论。相同Run的PG首次结果、暖待保存结果及unknown保护继续按已验[重投合同](3a-triage-recovery.md)执行；不重新计费、不重调旧unknown。

共享`memory.fingerprint`、API机构记忆指纹和`WORKFLOW_VERSION`保持，不以版本升级触发既有告警重跑。本批不重写共享CostGovernor或把跨告警缓存包装成完整上下文快照。原spend/token统计、已配置PG持久额度、shadow/replay写端口语义保持；停用缓存时仍须核实际调用的预算预留、usage与花费来源。若实现涉及开关，普通live与direct/replay的作用范围必须有直接测试，不能只改环境值而遗漏生产分支。

原groundedness gate仍在最终持久投影之前运行，不外推其能识别时间、授权或任意自然语言错误。普通live停止读取/发布该pattern结论缓存后，不允许通过其他分支复活gate已否定的FP/.99。direct/replay保留的旧缓存及其他上游行为分别标明限制，不把本批限定修复外推为所有入口已安全。

### R5：停止异常也完成任务清理

`FusedAlertTriageWorker.stop()`先设置stopping/running/attached，再分段停止consumer、有界drain/cancel并join全部EntityLanes、停止producer。consumer.stop、drain或producer.stop异常不能跳过后续清理；取消前尚未启动的lane也需清空task/lock/waiter。保留现有10秒drain语义、停止后拒绝新工作/请求、未确认结果不提交offset，取消不伪造响应或退还未知预算预约。

`services/agents/app/main.py`把主worker task的cancel/await放入保证执行的清理段，即使worker.stop失败也要等待任务结束后再关闭账本池。保留取消语义与错误可见性，不承诺非协作任务、无限并发或所有第三方客户端的强制中断。

预计生产源码范围为上述consumer、auto_triage_agent和main三个文件；必要时复用现有EntityLanes.cancel，不为本批改并发调度算法。发现必须扩大到schema、共享指纹或Run身份时，先收敛执行卡再实施。

## 直接验收

1. **材料到实际prompt**：采用合成信封，逐项核description/event_time经build_state进入真实safe-call完整messages；覆盖缺失、null、显式时间偏移、文本换行及超长描述的标记范围。风险分null/0、来源身份、五类读取状态与nonce不变；仅HTTP模型传输替身，不调用真实模型。
2. **缓存不复活与支出**：在同pattern、不同canonical alert ID的新告警上，第一条替身FP/.99含未支持指标并被gate降级，第二条不能通过旧缓存得到FP或空理由。不同描述/时间及上下文变化仍按当前材料处理；同Run PG完成重投不再进入模型，unknown不重发。对两条实际新调用分别核预算/usage，避免将禁用缓存误写成不收费。
3. **异常停止**：consumer.stop抛错、drain超时、外部cancel、producer.stop抛错分别验证后续清理与错误保留；最终lane task/lock归零，无停止后新增模型请求或offset提交。实际进入main lifespan并替换外部启动依赖，核worker.stop抛错后主task被cancel/await且账本池关闭，不能只以AST文本测试代替行为。
4. **相关既有回归**：复用`test_fused_alert_worker.py`、`test_groundedness_gate.py`、`test_entity_lanes.py`及porting的`test_triage_recovery_3a.py`、`test_triage_budget_3a.py`、`test_triage_request_3a.py`，只补直接边界；不默认全仓或慢速矩阵。
5. **部署候选**：只在测试通过及来源/范围核定后构建新的Agents差异镜像，保留当时真实父镜像和回退定义；仅Agents可重建。worker、graph、审批提案、记忆写回及真实响应继续关闭。模型计数、旧14表材料、预算预约、旧offset/积压、十枚reader、其他服务/卷/134迁移保持；所有输入使用新的合成标记，不重放旧unknown。
6. **change独立审计**：未参与实现者核最终差异、测试输入与运行源码hash、实际传输/PG/Kafka坐标及旧数据保护；保存失败尝试与检查点，不盲目重跑。审计通过后才更新本批回执/PROGRESS并进入理由提示词及新的独立质量复验。

本批目标为**0真实模型调用**，HTTP/模型方法替身、真实基础设施和最终运行验证分别取证。当前仅实施草稿，不构成验收或部署证明。

## 正式实施前的验收收敛

独立预审确认三处变化不改Kafka消息合同、offset算法、SQL、PG事务、Run版本或持久额度。复用C01及3A已验、合同未变的真实持久化/重投证据，本批不另建真实Kafka/PG业务样例，也不重调A/B满额和unknown。新验证采用实际普通live worker路径（驱动broker ContextVar，PG读取/claim/结果保存明确标为替身）、真实CostGovernor与gate、实际safe-call→生产SDK→httpx.MockTransport完整messages/usage捕获，以及实际main lifespan和带inflight任务的stop异常/迟到提交测试。不能以直接`triage()`的旧缓存路径替代普通live验证。

缓存测试及baked候选探针均断网，不挂真实模型凭据；模型/PG/Kafka传输替身与旧真实证据分别记录，不能写成本批新的真实broker故障或模型质量通过。预算固定为：真实模型0、broker发布/消费/提交0、业务PG写0、新tenant/key/reader/业务行0、DDL0、共享服务重启0；仅Agents可重建一次，其他35容器/18卷、旧14表/预算/十reader/原group保持。缓存镜像测试限300秒；baked候选探针使用本批合成输入、独占检查点和固定镜像hash。发生直接实现缺陷先修并保留失败尝试，按必要边界复测，不扩成慢速矩阵。

部署前核实Agents `Config.StopTimeout=null`，沿用Docker默认10秒；三个合作清理阶段各至多10秒，main join还需留余量。因此本批追加层只改Agents镜像及`stop_grace_period: 60s`，保持env/挂载/依赖、其余服务不变；在部署前另存范围补充，原执行卡快照不覆盖。60秒是容器退出宽限，不是新的模型请求超时、并发或无限等待保证。常驻worker保持关闭，本批不以真实docker stop下正在执行的模型作为测试；函数清理由有界替身行为取证。
