# 告警分诊：功能、默认规则与下一步实施

2026-10-21。接续[Fusion阶段小结](fusion.md#六当前阶段小结可以转入下游分诊)，按“支持什么、默认怎么做、输入输出、具体例子、再讨论取舍”梳理当前工作区源码。本次是只读分析和实施规划，没有新增模型调用、业务测试、运行启用或发布。实施仍归[当前OpenSpec change](../../openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/proposal.md)的2.1/3.3/3.4/4.1，不另造产品任务树。

## 1. 它解决什么问题

Fusion给出身份、关联、信号与分数；分诊决定这条告警属于真阳性、合法真阳性、误报、良性或待人工判断，满足策略时关闭，否则可以自动进入实际调查。**Fusion confidence、模型分类confidence、调查的启发式分数是不同数值**，不互相等价。

主入口是`FusedAlertTriageWorker.start → triage`，消费fused Kafka。`POST /cases/{id}/triage`走Router，是另一个入口，不能把它的步骤当成Kafka默认分诊。代码入口：[消费者](../../services/agents/app/workers/fused_alert_consumer.py)、[模型分诊](../../services/agents/app/agents/auto_triage_agent.py)、[确定性分诊](../../services/agents/app/agents/triage_agent.py)。

## 2. 输入到底采用了什么

| 输入 | 实际采用与边界 |
| --- | --- |
| `tenant_id`、canonical Alert ID | 核内外tenant及UUID；告警引用优先`alert_row_id → message.id → alert.id` |
| `incident_id` | Fusion关联组进入state，不自动等于人工Case |
| 标题、正文、原事件与时间 | 提取description/raw_event、event_time/created_at，保留缺失/null语义；Fusion narrative拼入summary，不能代替原事实 |
| 实体、IOC、MITRE、来源及规则 | 选取账号/主机/IP等、techniques、source/connector/规则标识和risk_score，供规则、reader及模型使用 |
| Fusion `confidence_score` | 映射为raw_alert.confidence，是支持信号，不是模型已作出的分类 |
| Fusion其他字段 | `enrichments`、anomaly/priority、confidence_rationale/label、候选attack_chain对象没有整体映射到分诊state；仍保存在Fusion首次snapshot中 |

具体字段以[build_state](../../services/agents/app/workers/fused_alert_consumer.py)为准。模型随后通过`_build_alert_context`再次摘要并限制字段、长度；“消息中有”不等于“模型看到了”。

自动Run为`UUID5(canonical Alert ID + ':auto-triage-v1')`；自动Run账本的`case_id`列实际写canonical Alert ID，而不是人工Case ID。不同来源的独立告警即便同属一个Fusion incident，仍各有自动Run；同一告警交付复用首次事实。关联含义不得只按列名推断。

## 3. 一条告警的真实处理顺序

| 步骤 | 做了什么 / 用什么 | 产物与下一步 |
| --- | --- | --- |
| 1 身份与首次结果 | 校验信封；普通Kafka live路径查/认领本Alert首次处理结果 | 已有结果按原保护复用；不把另一条相似告警的结论当本条首次结论 |
| 2 业务规则 | 读取tenant PG规则及已配置文件规则；按priority、ID排序，匹配severity/实体/字段等条件 | suppress命中先保存政策回执后结束，无模型；否则可能修改severity、route_to、tags |
| 3 选择writer及历史抑制 | 选择live/shadow；开启时查可信历史处置prior，按类别、人工确认、有效期、注入等限制 | 合法历史抑制可提前结束；不能把AI自己的结论无限当成人工确认 |
| 4 决定是否用模型 | CostGovernor、确定性模式、tenant模型配置及普通live额度共同决定 | 使用LLM、确定性分诊或保留受控停止；tier/fallback必须如实记录 |
| 5 读取模型上下文 | 需要LLM才读取组织记忆、tenant skill、KB/runbook、近期分析员处置、身份资料 | 保存各类读取状态、来源与实际提供的文本；成功无匹配与读取失败不同 |
| 6 一次模型分类 | `triage`角色；system prompt＋有界告警/上下文，要求`verdict/confidence/rationale` JSON | 通常一次回复；这里没有deep调查的选工具循环。模型失败可回确定性路径，高/严重告警失败另有保守保护 |
| 7 校验与关闭策略 | agent解析分类，结合注入/工具来源检查及tenant/class关闭policy、阈值、kill switch和可选grant形成关闭候选；worker再做groundedness最终复核，可降级/撤销关闭 | 只有可关闭类别且所有条件允许才关闭；模型自报高confidence不是关闭授权 |
| 8 首次结果持久 | `_record`保存分类、可见模型材料、上下文工件、usage及业务状态 | 普通live更新对应Alert，首次分诊确认后才向后续调查推进 |
| 9 prior写回及自动升级 | 首次持久后先按开关写处置prior；随后未关闭、writer允许且升级开关开启时，`_maybe_escalate → run_escalation` | 实际调查节点和工具继续执行；详见[调查调用说明](investigation.md)，不是只创建Run |
| 10 附加出口 | 升级返回后按各自开关处理审批提案、源SIEM处置写回等 | 建议、提案、dry-run、实际厂商写入分别表达。`response_dispatched=false`不能证明所有附加出口都无副作用 |

顺序依据[worker.triage](../../services/agents/app/workers/fused_alert_consumer.py)、[业务规则](../../services/agents/app/workers/business_context.py)、[模型及关闭](../../services/agents/app/agents/auto_triage_agent.py)。review_only会拒绝/隔离不属于其准入范围的分支，不能拿上表直接描述该profile当前都在执行。

## 4. 支持、源码默认和当前配置分别是什么

| 控制 | 支持/源码默认 | 当前解释 |
| --- | --- | --- |
| worker启动 | 有Kafka配置且没有`AISOC_AGENT_KAFKA_DISABLE`才起消费 | 最近运行回执仍OFF；本次不改，不等于源码不支持自动处理 |
| `AISOC_TRIAGE_ADMISSION_PROFILE` | 缺省`legacy`；另有本地`review_only_v1` | 常驻为review_only；模型建议另存，有效结果固定needs_review、confidence=null，不改canonical Alert，不关闭/升级/审批/写回 |
| 模型调用 | `triage`角色；temperature=0、completion上限512，当前SDK retry0及整次45秒截止 | 角色别名由既有网关配置解析；不是Fusion模型，也不由告警正文选择任意模型 |
| 关闭类别 | 固定FP、benign、BTP可以考虑；TP、needs_review不能自动关闭 | 类别本身还不够，须同时满足policy和安全检查 |
| `AISOC_AUTO_CLOSE_THRESHOLD` | 全局缺省0.85；tenant/class policy可覆盖，kill switch可拒绝；policy读失败拒绝关闭 | 无tenant行沿全局阈值；不要把“配了关闭表”直接当“已启用本类” |
| groundedness | 默认开启，floor缺省0.75 | 主要检测指标是否得到提供材料支持；不能据此保证时间换算、授权或全部理由正确 |
| 自动升级 | 源码默认开启，具体由`_maybe_escalate`及writer控制 | 不是单独按告警等级触发；凡未终止/关闭的结果，包括TP、NR或未达关闭要求的benign，都可能进入调查 |
| 业务规则 | 可suppress、set_severity、route_to、tag；匹配顺序固定 | severity进入state；**route_to/tags/category在build_state没有完整传递，worker不据route_to选Router**，不能宣称已有路由改写生效 |
| 首次分类prompt | 当前本地`triage.system` v5与lock，固定上游较早版本保留在来源记录 | 提示词升级不等于质量通过，旧分类/时间/授权失败不改写 |

配置依据[准入profile](../../services/agents/app/workers/triage_admission.py)、[关闭策略](../../services/agents/app/closure/policy.py)、[auto-triage](../../services/agents/app/agents/auto_triage_agent.py)及worker。当前运行状态引用[既有运行证据](../operations/integrity-autonomy-r01.md)和[full回执](../operations/full-support-migration.md)，本次没有在线重查或修改配置。升级、memory、shadow、审批及源写回等开关在进入实施时只核本次所用项，不把原默认ON当当前已启用。

### 待共同取舍的真实接缝

1. **Fusion材料采用范围。** 是否需要把anomaly、priority、UEBA具体来源和候选链送入分诊，先解释用途；当前不自动扩大prompt，也不把所有分数叠成第二套评分。
2. **业务规则路由。** route_to/tag在规则引擎有写入，当前主链没有完整消费。先确定是否需要它改变调查路径；不能仅加字段就宣称功能完整，亦不预定合并Router/graph。
3. **自动关闭及升级策略。** 先用下列例子解释原行为，再讨论所需类别/阈值/启用范围；不静默改原阈值，不以review_only永久代替完整自治。
4. **调查质量缺口。** 深度、证据与报告的既有失败登记保留。对本批直接正常业务阻塞最小修复，其余按[问题表](../operations/upstream-issues.md)安排，不先重跑旧质量矩阵。

## 5. 用同一方式比较几个例子

| 例子 | 进入了什么材料 | 决定怎样产生 | 最后效果 / 证据边界 |
| --- | --- | --- | --- |
| 已有C1，实际执行 | 新source-v1告警，账号/目标/命令和UTC批准窗有对应材料；五类reader成功无匹配 | 模型BTP/0.95；原0.85阈值和保护允许关闭 | 实际PG resolved、有resolved_at、API BTP；一次回复2174 tokens。不是“任何BTP都关闭” |
| 已有C2，实际执行 | 新告警，授权与后续活动未知；不是没有攻击 | 模型needs_review/0.85；NR不在可关闭类别 | 实际未关闭且自动执行graph/deep，无需人再点；调查partial/报告质量失败。原因不是`0.85 < 0.85` |
| 规则抑制，源码示意 | 一条匹配已配置suppress规则的告警 | 规则决定，不调用LLM | 保存政策抑制回执后停止；要核的是命中规则与实际状态，不把它包装成模型判断 |
| 同一模型建议在不同控制下，源码示意 | 假设模型给BTP/0.95，材料与策略允许 | legacy可进入关闭；review_only只留建议，有效NR/null；worker OFF则根本不消费 | profile、模型建议和运行启停是三个不同层次；示意不是新实测 |
| UEBA信号有/无，待讨论示意 | 同实体Fusion confidence可能随异常变化；当前并非完整UEBA工件直入分诊 | 仍由本次模型/确定性路径及关闭policy判断 | 不能从Fusion加分推导固定分类或必然升级；无需为说明额外发两轮模型 |

C1/C2原始事实见[自治R01回执](../operations/integrity-autonomy-r01.md)。首次分诊、后续graph和报告质量分别判断，Run completed不等于全部调查完整。

## 6. 输出、审计与二开落点

| 查什么 | 记录/位置 | 需要看清的边界 |
| --- | --- | --- |
| 最初决定 | ledger Run、首次triage_verdict及首次结果工件，live对应Alert | 自动Run case_id与真实Case ID区分；首次NR不能被后续报告追改成TP |
| 模型用了什么 | 五类读取回执、实际提供的prompt材料、原可见response、hash、版本 | 有8000可见文本等边界；hash不等于已归档完整provider wire，不包含隐藏推理 |
| 为什么关/没关 | verdict、confidence、closure policy来源/阈值、groundedness及实际auto_closed/Alert状态 | 模型理由与策略理由分开；状态和关闭时间证明实际关闭 |
| 后续做了什么 | graph_step、deep工具/模型工件、graph结果/报告、graph_usage | 首次分诊usage与调查增量分别保留；每步详见调查说明 |
| 用了多少 | 实际prompt/completion tokens；measured/estimated/unpriced cost | 固定预约单位不是usage；unknown价格不能说零费用 |

实现集中在[triage持久端口](../../services/agents/app/workers/triage_persistence.py)、[ledger](../../services/agents/app/investigator/ledger.py)及worker `_record`。读取端沿已有Run详情/events/artifacts/report接口；确切路径见[调查审计交接](investigation.md#6-逐调用审计如何阅读)，不新建账本或审计服务。

## 7. 接下来的实际实施顺序

1. **本轮先交接原机制。** 本文加调查逐调用说明，给出输入/依赖/默认规则/真实例子与待取舍接缝；这是分析完成，不是新功能验收。
2. **逐项决定保留和必要修改。** 先分诊字段、业务规则、关闭/升级交接，再进入调查；每个决定落现有OpenSpec任务。合同确有新增时先补规格/设计，不提前裁剪源码或合并编排。
3. **只验证当前改动。** 优先复用3A/C03/B4已有证据与直接测试；新改字段就核输入到实际采用，新改决策就核类别/阈值及PG输出。只补无法被旧证据覆盖的少量代表输入，不默认再跑全部分类、全部入口或多轮真实模型。
4. **本地先测、借21基础设施。** 确有必要的联动用新标记数据和隔离入口，保留旧unknown/积压；本地业务源码运行，不上传源码做临时测试。
5. **阶段收尾。** 一次未参与实现者审计，保存本地可回查版本/需要时的本地镜像，再按阶段统一发布。当前不发布、不启常驻worker；复杂可用性、恢复、冗余、压力专项继续后置。
