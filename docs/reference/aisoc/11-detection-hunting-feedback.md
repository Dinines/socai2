# 11 检测、狩猎与反馈改进闭环

> 用途：固定上游源码与历史证据分析（2026-10-20对齐）。本轮负责告警处理策略、当前告警相关只读补查与反馈提案；原始事件检测、扫描及检测规则生产发布不在范围。 当前职责见[范围](../../operations/alert-processing-scope.md)，阶段退出见[路线](../../operations/service-roadmap.md)，执行批次见[依赖计划](../../operations/dependency-migration-plan.md)。

返回[总入口](README.md)或[模块总览](01-system-map.md)。对应 **M01/M16/M19/M20**。告警后续处理不仅输出报告，还会形成规则改进、主动查询和经验回流；这些回流不能无审批改变事实或静默关掉检测。

<a id="m01"></a>

## M01 事件到检测：四类执行能力

| 能力 | 输入 | 处理方式 | 输出/下游 |
| --- | --- | --- | --- |
| 单事件规则 | 规范化事件、厂商字段、rule corpus | 字段恢复、规则候选索引、条件计算、tenant overlay | 命中 Detection/RawAlert，来源 event/rule 贯穿 Fusion |
| 窗口/序列规则 | 多事件、实体 key、时间窗 | Redis 窗口计数、distinct、阶段序列与 fired 标记 | 窗口告警及对应来源事件 |
| 首见/行为派生 | principal/属性/行为与历史 | FirstSeen、CORE baseline 生成 typed 字段 | 供规则条件使用；派生信号本身不是 finding |
| 厂商 finding 提升 | 上游已判定的安全发现 | promoter/RawAlert 映射 | 保留厂商判定及 external_id，进入 Fusion |

源码：[detection_engine.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/detection_engine.py)、[windowed_detection.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/windowed_detection.py)、[promoter.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/promoter.py)、[first_seen.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/first_seen.py)、[baselines.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/baselines.py)。

单事件引擎的 `evaluate_async` 在条件计算前按实际绑定读取 first-seen/baseline derived fields。关键词/条件只会匹配实际字段；一条规则的文件存在不证明其所依赖的身份、注册时间、peer 或厂商字段可达。

窗口规则可表达次数、不同值个数和顺序；序列要满足 whole window 与阶段次序，不把无关多条记录简单凑成攻击链。Redis 不可达时跳过某些 stateful detections，不应向分析员报告“窗口检查正常且无异常”。

FirstSeen 的“第一次看到域名/地址”不等于域名注册年龄。当前字段映射有意只提供真实观察语义，不能为让规则能跑而制造 domain_age_days。CORE baseline 与独立 UEBA 的区别见 [M13](09-ueba.md#m13)。

测试：`test_detection_engine.py`、`test_windowed_detection.py`、`test_windowed_sequences.py`、`test_first_seen.py`、Fusion `test_baselines.py`、`test_sigma_correlation_replay.py`。验收不仅看 hit 数量，还要核 matched rule、字段来源、事件 IDs、边界时间和实际不命中的反例。

<a id="m16"></a>

## M16 检测规则管理、翻译、发布与回测

### 管理面到运行面的链

```text
规则源 / 人工规则 / 自然语言候选
→ 语法与字段映射/兼容检查
→ fixture 或历史数据回测
→ 工程师审查/发布
→ 打包规则产物 + tenant overlay
→ Fusion 实际加载与执行
→ 命中/拒绝/不可达统计与 Alert rule provenance
```

管理库显示 enabled，不等于运行引擎已使用。静态 corpus、编译产物、数据库 tenant overrides、外部 SIEM 执行是不同平面，需要选定具体路径验证。

| 子模块 | 输入与处理 | 输出/副作用 | 必须核对 |
| --- | --- | --- | --- |
| CRUD | rule body、language、enabled、tenant | 数据库规则与元信息 | 是否改变实际运行 corpus/overlay |
| Sigma/字段映射 | 规则语言和目标字段合同 | 可执行条件、窗口/序列导出或明确不支持 | 编译成功不等于来源具备所需字段 |
| NL rule/tuning | 分析员文字、现有规则、上下文 | 候选规则、解释/提案 | 模型不能自行发布；无模型不可伪造改进 |
| Fixture eval | 候选与正反样本 | 每个 fixture 的 fire/error、汇总 | 与 streaming engine 是否同一语义 |
| Historical backtest/hunt | 规则、后端、时间范围 | 历史命中及覆盖/错误 | 无后端与合法零命中分开 |
| Tenant overlay | PG tenant 规则、allowlist、privileged metadata | 版本化局部差异、热重载 | 只影响本 tenant；加载失败保留旧版本 |

入口：[detection_rules.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/detection_rules.py)、[detection_proposals.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/detection_proposals.py)、[detection_eval.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/services/detection_eval.py)、[tenant_overlay.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/tenant_overlay.py)。

导出/编译入口：[export_detection_ruleset.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/scripts/export_detection_ruleset.py)、[compile_sigma_ruleset.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/scripts/compile_sigma_ruleset.py)、[export_windowed_ruleset.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/scripts/export_windowed_ruleset.py)、[sync_packaged_detection_rulesets.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/scripts/sync_packaged_detection_rulesets.py)。本文定位这些入口，没有执行编译/发布，也没有审计全部规则覆盖。

当前 overlay 默认约 30 秒重取；含 disables、severity/条件限制、suppression、allowlists、privileged principals/roles 和 version。要分别证明“数据库改了”“overlay 加载了”“该事件实际按新版本处理了”。

测试：`test_tenant_tuning_overlay.py`、`test_detection_eval.py`、`test_detection_tuning_is_not_promotable_as_a_stub.py`。最小场景为 tenant A 关闭一条规则、B 保持 → 各自版本被实际读取 → 同事件 A 不触发、B 触发，并记录抑制依据。

<a id="m20"></a>

## M20 主动狩猎与补充查询

### 与调查的关系

调查围绕已有目标/问题补证；狩猎可以从假设、技术或情报出发搜索更大范围。两者可共享工具，但不能在一个 Case 调查里无界扩展到全租户。

入口：[hunts.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/hunts.py)、[agent_tools.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/agent_tools.py)、[retro_hunt 查询生成](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/services/retro_hunt/hunt_plan_sql.py)、[saved_hunts.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/saved_hunts.py)。不同路径可针对外部 SIEM、数据湖或保存的查询计划；不能把后端查询方言混为一种。

| 输入 | 中间产物 | 输出 |
| --- | --- | --- |
| 假设、实体、技术、窗口、tenant 授权 | 结构化 hunt plan、允许字段/操作、实际查询 | 命中事件、结果范围、后端状态、报告 |
| 新 IOC/情报 | 受限历史回查请求 | 历史相关线索，是否升级告警/Case 由明确策略决定 |
| 保存的 hunt | 版本与执行配置 | 本次执行、时间、结果；不是覆盖原历史结果 |

新增 Hunt Agent 应输出受控结构计划，由服务端生成查询；模型写“已扫描所有日志”必须有实际执行和 coverage 证据。无 lake 的 CORE 环境不能凭计划生成成功就声称历史搜索完成。

另有 [deep_investigation.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/investigator/deep_investigation.py) 从 graph 的 Investigation 节点实际调用工具循环：策略/tenant skill → 本地 registry + 已配置客户工具 + 允许的 MCP → 有界 ReAct → tool_trace、coverage、深度指标。该路径不是默认 Case 四阶段自动追加的必经步骤。

源码默认 Deep enabled，最多 6 轮、wall-clock120秒、独立 token/费用界；总 Run 外层预算也可能先结束。达到轮数只表示执行上限，不代表问题已经查清；超时、不可用后端和未验证的模型工具声明应进入结果。默认值不是 43 测试模型能力承诺。

费用/token 配置和结束后的 `cost_capped` 记录不单独证明每次发送前都硬性阻止超额；若将其作为目标预算控制，必须沿 tool_loop、CostGovernor 和实际发送检查，不能只移植结果标志。

测试 `test_deep_investigation.py`、`test_deep_investigation_customer_tools.py` 验绑定和调用；真工具验证需一条受限 query → 请求/回执/ledger trace → 调查结果引用。MCP server 注册和工具 discovery 成功不证明某次工具已实际执行或结果可信。

<a id="m19"></a>

## M19 分析员反馈、检测调优与再评测

### 三条反馈回路

| 回路 | 输入 | 处理与输出 | 保护边界 |
| --- | --- | --- | --- |
| 当前告警修正 | 原 verdict、人工 disposition、理由 | override 历史、当前处置、结构原因 | 保留原模型结果和人工身份，不能伪装模型本来正确 |
| 经验/知识 | 结构化原因、Case closure、可信 prior | organisation/institutional/semantic memory | 同 tenant、来源明确，避免未经确认的自我强化 |
| 检测规则优化 | per-rule 历史 disposition、entity、human_verified | exception/lower_severity/suppress 建议 | 只提案；工程师审查后再发布并证明生效 |

入口：[feedback.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/feedback.py)、[analyst_feedback.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/services/analyst_feedback.py)、[detection_tuner.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/services/detection_tuner.py)、[replay job](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/services/replay_evaluation/job.py)。

Tuner 默认至少 10 个已决定样本、误报率≥0.7 才建议；误报若集中某实体优先 scoped exception，极高比例且足够人工确认才建议 suppress，否则 lower_severity。`benign_true_positive` 不计为误报，needs_review/unknown 不应污染已决定分母。human_confirmations 的统计不自动等于唯一分析员数量，应按来源和实际数据解释。

Replay evaluation 会从源端读取历史处置，冻结/限制上下文并运行独立评测。它与账本 `/replay` 的“读取历史步骤”不是同一操作：前者可能重新查询和调用模型，后者不应执行副作用。质量报告必须注明样本来源、选择偏差、上下文截止、实际模型和未知/未完成项。

### 最小测试和采用边界

`test_analyst_feedback.py`、`test_feedback_context_statements.py` 验原因/记忆，`test_detection_tuner.py` 验样本阈值、BTP 不算 FP、集中例外，`test_replay_frozen_context.py` 验冻结上下文合同。

验收卡：人工纠正一个告警 → 原模型结果与人工理由均可查 → 下一次相同场景可读取本 tenant 明确 prior；规则调优仍停在 proposal，不能因模型建议静默发布。要证明调优有效，应另做固定正反样本和管理面→运行面的生效核对。

正式全量评测、自动学习发布和复杂回溯不作为当前移植前置；保留必要人工反馈、来源、不可改写事实和最少正反样本即可。20 未跑过上述完整反馈/调优回路。
