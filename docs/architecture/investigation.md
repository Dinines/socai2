# 调查逐步调用：自动链、人工链、模型、工具和审计

**2026-10-27适用范围说明：** 本页描述原有Agents graph/Router/Deep/四角色路径。新增F3 Case实际在API v2执行，不串行调用本文所有角色；其当前实现及验证边界见[实现详解](../investigation/current-implementation-reference-20261027.md)，完整文档/证据入口见[审计导航](../investigation/audit-guide-20261027.md)。

后续设计与换账号续接统一读[调查模块规划设计文档](investigation-planning-design.md)：四块合同、程序/模型分工、旧模块融合、专用分支和逐模块测试。本文继续描述已有流程及历史实证，不把拟议统一设计当成已运行行为。

2026-10-23本地小修：人工Forensic校验已前移到响应/报告之前；Deep逐次保留工具材料并以结构状态判断，异常/时限可交接已有成果。四阶段与模型参数保持，未部署；本地行为以[小修回执](../operations/investigation-result-handoff-20261023.md)为准，下文10月21日静态/旧运行记录保留。

攻击链/图已按[原规划](../operations/attack-chain-path-integration-plan.md)完成一批本地接入：已有Case起点、可信定向投影、原查询、有界模型消费及Run工件，见[实际回执](../operations/attack-chain-path-local-20261021.md)。暂未发布，下文旧运行/失败事实保持；当前Tool目录、执行、配置及最少测试见[使用指南](../operations/investigation-tools.md)。

本批已补[真实本地模型/工具逐步案例](../operations/investigation-functional-20261021.md)：Router Identity/Cloud、默认四节点含Forensic兜底、Deep六轮/7工具；下文静态示例及旧Run保持，不由新实测追认其质量。两处接口合同已本地最小修正，尚未发布。

2026-10-21。供告警二次开发使用，按用户要求细到每个智能体、每轮模型及每个实际工具调用。本次核当前工作区源码和已有Run材料，没有新运行、测试、模型调用或部署。固定上游仍为`34ca18c57dd4175539e5c6dd3d04a72dc057306b`；**当前源码、已部署版本、历史Run实况分别描述**，不以原件齐全或节点存在宣称功能已验。

两套流程的目的、输出、官方设计依据及四Agent的客观评价，单列在[调查设计评价](investigation-design-review.md)；先理解取舍依据，再决定改法，不因自动/人工触发差异预定两套执行架构。

用户要求的“每步目的、模型实际输入/输出、预处理、怎样决定并执行工具”另见[详细合同与JSON示例](investigation-preprocessing-tools.md)：区分Router代码路由、固定预查询与Deep结构化tool_calls，包含Case嵌套alerts、参数/tenant、工具返回及下一轮采用。

## 1. 先选对入口：几套调查并非同一流程

| 入口 | 实际编排 | 模型调用的性质 / 现有边界 |
| --- | --- | --- |
| fused Kafka分诊后自动升级 | `_maybe_escalate → run_escalation → triage → enrichment → investigation → attack_path` | 跳过graph里的模型auto_triage，仍执行确定性triage。investigation内部可进入deep多轮工具循环；节点可因预算提前结束 |
| Agents `POST /api/v1/agent-runs` | `run_full_investigation`先auto_triage，未关闭再进上述graph | 独立入口，有自己的scope/tenant约束；不能拿它代证Kafka自动触发 |
| Agents `POST /api/v1/cases/{case_id}/investigate`，默认 | `Recon → Forensic → Responder → ReportWriter` | 正常成功路径四次应用层模型调用，无自主选工具循环。`AISOC_INVESTIGATE_USE_ROUTER`源码默认false |
| 同Case调查开启Router | `RouterOrchestrator.stream`，分类路由→选中的专业Agent→join→确定性响应/报告 | 调用次数随命中专业分支变化；有stream逐步账本及报告出口，不等同默认四节点 |
| Agents `POST /api/v1/cases/{case_id}/triage` | `RouterOrchestrator.run` | 另一条Router入口；该run/API主要内存结果与实时事件，没有stream同等的逐步ledger/Markdown持久流程，不能合称已完整交付 |

入口依据[worker](../../services/agents/app/workers/fused_alert_consumer.py)、[graph](../../services/agents/app/graph/workflow.py)、[AgentRuns API](../../services/agents/app/api/router.py)、[Case调查API](../../services/agents/app/api/investigate.py)、[Case Router分诊](../../services/agents/app/api/triage.py)。Case、Fusion incident、Alert、Run各自含义见[分诊输入](triage.md#2-输入到底采用了什么)。

以下按告警自动链优先说明，再单列人工默认和Router；不预定合并编排。

## 2. 调查前先取哪些共同资料

自动升级与默认人工调查均可调用`prefetch_context_bundle_dict`。从原告警提取实体，再**并行**取五类资料；这不是五次模型调用，也不是模型每次自己决定查什么。

| 来源及输入 | 调用/后端 | 返回后如何使用 |
| --- | --- | --- |
| host/user/email等实体 | API neighbors与blast-radius，后接实体图 | 邻居、关系及影响范围候选，进入ContextBundle；图失败/禁用不等于0邻居 |
| 当前tenant、模板/类别/严重度等标签 | `institutional_search`，默认最多5条历史相似处置 | 历史经验进入bundle，不是查询整个历史事件湖，也不证明本次事件事实 |
| tenant、实体类型/ID | UEBA `GET /api/v1/ueba/baselines`，再按实体过滤 | 读取既有基线，不在调查内重新训练或计算一次异常；不能假定每条baseline都有现成deviation |
| 告警中的IP/domain/hash/url | Enrichment `POST /enrich/bulk`，最多64项 | IOC信誉/来源进入bundle；没有provider或错误不证明安全 |
| 直接及关联Alert ID合并去重，direct优先，总计最多3条 | API `GET /api/v1/graph/incident-context/{alert_id}` | 身份、资产、业务/云/威胁背景；范围裁剪、partial及错误须保留 |

代码：[bundle构建](../../services/agents/app/context/bundle.py)、[调用适配](../../services/agents/app/investigator/bundle_prompt.py)。默认人工Recon另预取一次KB，后续节点复用；自动deep还可选择tenant skill。它们与首次分诊的五类reader不是一次查询，不能因分诊reader已通就认定全部调查查询已通。

## 3. 自动升级调查每一步怎样执行

### 3.1 从首次分诊交接到graph

分诊先保存首次决定，再检查未关闭、`AISOC_AGENT_ESCALATE_TO_GRAPH`及writer权限；review_only/shadow等限制会阻止升级。`_maybe_escalate`复制调查state，补ContextBundle，带同tenant、Alert、Run和独立调查CostTracker进入runner。**调查后续结论不应追改首次分类或让新提案偷偷进入首次分诊的审批/写回。**

源码入口：[worker `_maybe_escalate`](../../services/agents/app/workers/fused_alert_consumer.py)、[run_escalation](../../services/agents/app/graph/runner.py)。首次分类具体规则见[分诊说明](triage.md#3-一条告警的真实处理顺序)。当前常驻worker仍OFF，本段是支持的调用方式，不是宣称正在持续消费。

### 3.2 graph固定节点与每个节点的内部工作

| 顺序 / 调用 | 实际输入 | 内部步骤及外部调用 | 输出 / 条件 |
| --- | --- | --- | --- |
| G1 `run_triage` | 原告警summary/raw_alert、severity/risk等state | 本地规则/关键词/风险启发式、IOC提取及MITRE映射；**不再发一轮分类LLM** | findings、IOCs/技术候选、初始提案；这是graph内triage，与已完成的模型auto_triage有区别 |
| G2 `run_enrichment` | 从state提取的IOCs及规则/技术材料 | 按实际分支调用批量IOC增强，汇总缓存与TI资料；本身不是模型选工具循环 | ioc_enrichments等，缺源/失败保留；工具包装器和服务认证须按本路径核实 |
| G3 `run_investigation`前半段 | 原告警、G1/G2结果、ContextBundle | Splunk来源适用时只读补查；分析成功增强中的恶意/可疑IOC；本地查MITRE知识；具备条件时调TI actor attribution；将bundle转findings | 这些是代码选择的确定性查询，不是deep模型已经访问了全部来源 |
| G3内部 `run_deep_investigation` | 原告警有界投影、MITRE候选、技能/内置策略、可用性说明 | 见下一小节：模型自主选择已注册工具，多轮接收工具结果 | narrative、tool_trace、实际轮数、深度/覆盖缺口、partial原因及usage |
| G3后半段 | 既有证据与deep结果 | 确定性汇总发现、生成响应提案、启发式score；当前源码对deep不完整保留needs_review/partial | findings/verdict/confidence及proposed_actions；知识映射/风险先验不能自动成为已确认攻击 |
| G4 `run_attack_path` | **真实Case链接**及图资料 | 有Case才GET attack-path，再对最多5个实体GET blast-radius；无LLM。节点可因预算或缺Case不执行查询 | 路径/影响范围候选写state.threat_intel.attack_path及提案，不等于已执行隔离/阻断 |
| G5 runner交付 | 最终或partial state、实际model/tool记录 | 沿现有graph报告渲染、ledger事件/工件与用量汇总保存，不额外调用默认ReportWriter模型 | graph结果、Markdown、usage与首次triage事实分别读取；Run状态不替代graph completion/deep truncated |

节点代码：[triage](../../services/agents/app/agents/triage_agent.py)、[enrichment](../../services/agents/app/agents/enrichment_agent.py)、[investigation](../../services/agents/app/agents/investigation_agent.py)、[attack_path](../../services/agents/app/agents/attack_path_agent.py)、[runner](../../services/agents/app/graph/runner.py)。响应行为当前主要是提案；真实厂商执行不由调查自动获得授权。`workflow._should_continue`虽定义terminal/max_iterations检查，当前没有接到后四节点的图边上，不能只看该函数就宣称每步都会按它退出；实际还受runner截止/预算控制。

G3前半段的调用再细分：Splunk仅对适用来源且有对应凭据时执行有界只读查询，保存查询/数量/摘要hash；逐MITRE ID调用本地`lookup_technique`；有IOC或MITRE才尝试TI `POST /api/v1/actors/attribute`，失败记finding继续。Bundle在此转为确定性findings，不能由此推断deep模型已经读取完整Bundle。见[Splunk补查](../../services/agents/app/investigator/splunk_evidence.py)及`investigation_agent._perform_threat_actor_attribution`。

**Attack Path的实际接缝：** agent只认`raw_alert.case_id/caseId`或`threat_intel.case_id`，不会把Fusion incident自动当Case。自动告警state目前没有凭空建Case；旧`AGENTS_API_TOKEN`及tenant传递也需按该工具接缝核。已有full实测只证明Case→Alert的PG两节点一关系回退，尚不证明自动事件图/完整攻击路径。原C2更在G3后预算停止，未到G4，不能称已复现G4查询失败。该问题已在[登记表](../operations/upstream-issues.md)保留，后续单独讨论Case关联或Alert起点，不在本轮擅自改合同。

### 3.3 deep里每一次模型和工具调用怎样发生

| 环节 | 当前代码行为 | 留下什么 / 不能推断什么 |
| --- | --- | --- |
| D0 选调查计划 | 先用匹配tenant skill；否则内置策略按MITRE匹配每项10分、关键词每项2分，最高者优先，同分按原顺序，无命中用fallback | 计划是指导，不是必须顺序执行的workflow；技能版本与实际文本要可定位 |
| D1 组工具集 | 注册本地/IOC工具＋11个typed调查工具；按tenant配置追加SIEM/EDR/cloud等customer工具和MCP工具 | 可用工具、拒绝/未配置来源写coverage；列入工具集不证明本Run调用过 |
| D2 第n轮模型请求 | 逻辑角色`investigation`；system=`deep_investigation.preamble`＋策略/技能＋coverage/数据边界，Human为有界原告警；后续请求带之前可见对话和ToolMessage | `safe_ainvoke`；保存可见prompt/response、模型、轮号、hash与耗时，usage由CostTracker记录 |
| D3 判断模型回复 | 无tool_calls则把可见文本作为最终narrative；有调用则取name/args/tool_call_id | 一轮可0/1/多个工具，绝不是每个Agent固定一个工具 |
| D4 执行每个工具 | registry按name/args调用实际函数，tenant由服务绑定；将有界结果作为匹配tool_call_id的ToolMessage追加 | tool_trace保存tool/args/result_preview；下一轮才可基于该结果继续选工具 |
| D5 下一轮或结束 | 无工具的综合回复可提前结束；迭代上限、时间/额度、异常可使partial。默认deep开启、最多6轮、120秒；deep参数60000 tokens/$0.50，graph另默认20000 tokens/8模型调用及120秒 | `$0.50`不能描述为未知价格调用的硬保证；历史字段max_tool_calls实际检查模型调用数。当前工作区已有逐reply预算/cap修正，不等于旧C2/常驻已生效或质量通过，不重做专项 |
| D6 汇总 | 成功且可用的工具计有效pivot，available=false/error不当有效调查深度；记录覆盖缺口/截断及tool_call账本 | reached_depth反映工具覆盖数量，不证明结论或因果正确；达cap应无最终综合结论，不能把末ToolMessage当报告 |

代码：[deep入口/策略/工具组装](../../services/agents/app/investigator/deep_investigation.py)、[逐轮循环](../../services/agents/app/llm/tool_loop.py)、[内置策略](../../services/agents/app/investigator/strategies.py)、[工具registry](../../services/agents/app/tools/registry.py)。模型逻辑角色可能解析到同一个物理模型，实际alias/resolved_model以Run账本为准。

### 3.4 可选工具到底查哪里

| 工具 | 主要输入 | 实际处理/后端 |
| --- | --- | --- |
| `process_activity` | hostname、hours | 查询主机执行进程，ClickHouse `aisoc.raw_events` |
| `historical_execution` | process_name或sha256、days | 查询该二进制历史出现的主机/账号，同一事件湖 |
| `network_connections` | hostname/source_ip、hours | 查询连接目标及聚合，同一事件湖 |
| `authentication_events` | user_name、hours | 查询账号认证记录，同一事件湖 |
| `fleet_ioc_hunt` | indicator、days | 查询其他主机上相同IP/domain/hash，同一事件湖 |
| `entity_timeline` | hostname/user_name、hours | 按时间排列实体相关事件，同一事件湖 |
| `technique_activity` | technique_id、days | 查询相同ATT&CK标签事件，同一事件湖；标签不证明真实攻击 |
| `process_tree/mailbox_activity/oauth_grants/persistence_mechanisms` | 对应host/user/pid | 原版显式not_ingested占位；分别需要EDR谱系、邮箱、OAuth、持久化来源，当前不自动新建采集后端 |
| `extract_iocs/map_to_mitre/lookup_technique` | 文本/technique_id | 本地正则、关键词映射、ATT&CK知识；不等于查询现场 |
| `enrich_ioc` | ioc_value、ioc_type | 单项信誉增强包装器；见下文单项合同差异，不能以bulk通了代证 |
| 文件hash沙箱查询 | sha256 | 查询已连接沙箱结果，不据工具名称推断已经实际执行样本 |
| tenant customer/MCP工具 | 各注册schema | 只提供所配置/允许的工具，按该Run trace判断有无调用；本阶段不扩厂商动作测试 |

前11个typed工具由[Agents适配](../../services/agents/app/tools/investigation.py)调用API `POST /api/v1/graph/investigate/query`，需`lake:query`，tenant取认证身份，不让模型指定。API [dispatch/SQL](../../services/api/app/services/investigation_tools.py)有固定参数化查询，时间默认依函数而异（主机进程/连接/实体时间线24小时，认证实际168小时），最多90天、默认50/最多200行；共享schema的hours默认24描述不等于所有函数默认。查询通常按`now()-hours/days`，并非已有告警发生前后UTC窗口合同。各工具默认及调用详见[预处理/工具专篇](investigation-preprocessing-tools.md#8-工具输出是什么模型如何使用)。我们负责查询其他模块提供的数据，不在此接管raw事件采集。

一次查询须区分：有记录、成功0条、available=false/not_ingested、实际查询失败。只有后者错误时不得声称已经查清；0条也仅对给定来源/时间/查询范围成立。

## 4. 默认人工调查四个Agent的每次调用

共享Bundle准备后，`InvestigatorOrchestrator`按下表顺序调用。节点异常/failed可提前结束后续；**正常成功路径四次模型调用，不含deep循环**。四次temperature均0，completion源码默认2048，环境可覆盖；角色别名并不代表四个不同物理模型。已有运行值与旧失败见原回执，不在本次重跑。

| 步骤 | 调用前的实际材料 | 模型调用 / 随后动作 | 输出及下步采用 |
| --- | --- | --- | --- |
| M1 Recon | 先按rule_name或关联告警标题预取一次KB；模型看到summary、结构化原告警有界摘要、Bundle、KB | `recon`角色＋`recon.system`，一次`safe_ainvoke`。**随后**合并模型IOC/本地正则IOC，逐IOC并行增强并复用缓存；本地合并MITRE关键词映射 | IOC、MITRE/主体候选、攻击面和summary写state.recon，增强进cache；本轮新增单项增强主要给Forensic，不能追称已进先前Recon prompt |
| M2 Forensic | 原告警结构、Recon summary/MITRE、前10项增强摘要、同Bundle及KB | `investigation`角色＋`forensic.system`，一次模型。没有在此主动查询lake/现场进程/厂商取证接口 | timeline、artefacts、root_cause_hypothesis、blast_radius、confidence、summary；artefacts按hypothesis留痕。缺原事实且无有效增强时inconclusive/低confidence，不能凭模型补现场事实 |
| M3 Responder | Forensic根因/范围/分数和末5条时间线，Recon MITRE/主体候选、同Bundle/KB | `investigation`角色＋`responder.system`，一次模型；没有调用Actions或厂商执行 | recommended_actions、containment/eradication/recovery步骤、工作量/风险/summary，强制dry_run=true |
| M4 ReportWriter | 前三节点结构结果、时间线和建议内容、IOC/增强样本、原告警事实/发生时间、Bundle/KB | `report`角色＋`report_writer.system`，一次模型生成Markdown；本地转HTML不再调模型。失败或实际finish_reason=length时留原回复并交明确fallback，标failed、不再请求模型 | report_md沿orchestrator存工件，按Run读取；HTML在state/done不等于独立持久工件。当前只要求Markdown，不扩PDF/格式测试 |

调用代码：[Recon](../../services/agents/app/investigator/recon_agent.py)、[Forensic](../../services/agents/app/investigator/forensic_agent.py)、[Responder](../../services/agents/app/investigator/responder_agent.py)、[ReportWriter](../../services/agents/app/investigator/report_writer_agent.py)、[KB复用](../../services/agents/app/investigator/knowledge_prompt.py)、[orchestrator](../../services/agents/app/investigator/orchestrator.py)。每一步的可见请求/回复、证据引用、决策与阶段输入输出hash由state.log系列记录，后续持久化。

**单项IOC增强合同已本地最小修正，未发布：** 本批原Recon真实请求`{value,type}`两次返回400（`ioc_type is required`），现仅将`investigator/tools.py`字段改为`{value,ioc_type}`；7项直接测试及本地原函数→21无provider服务实际调用通过。默认URL仍为`http://enrichment:8080`，实际接线必须以`ENRICHMENT_SERVICE_URL`指向原Go的8082端口；本批未改默认值/提取算法。该包装器同供deep使用，Bundle/G2 bulk是另一条调用；零分和sources为空不证明安全。详见[真实回执](../operations/investigation-functional-20261021.md#6-两处最小本地修正)，原失败结果保持。

## 5. Router及full graph的差异

### 5.1 配置选择的准确含义（本轮讨论确认）

Router是随源码内置、可选启用的编排，不是运行时另装/动态加载的插件。对Case `POST /api/v1/cases/{case_id}/investigate`，`AISOC_INVESTIGATE_USE_ROUTER=false`（默认）选原四节点，`true`选Router。两者在这个入口**二选一**；启用Router后改走其流程，不先跑原四节点，也不是在四节点后追加专业分析。[选择代码](../../services/agents/app/api/investigate.py)读取这个开关，文档更新不代表已改变运行值。

这个选择开关不控制Kafka自动升级的graph/deep；人工`/agent-runs`也有独立graph入口，Case `/triage`本身另走Router。因此不能说“开启Router后整个项目调查都换成Router”，也不能把Router与deep当成同一个新模块。

### 5.2 Router有分析和报告出口，但不等价于专业化四节点

```text
auto_triage
  ├─满足提前结束条件 → 渲染报告 → END
  └─classify_signals → 选中的领域分支（各1次模型）
                     → join → 确定性响应摘要 → Markdown渲染/保存
```

**每个专业分支不是一条Recon→Forensic→Responder→ReportWriter小流水线。** 专业化主要体现在输入字段投影、领域system prompt、领域指标/类别输出，再由代码选择和汇合分支。不能据此宣称原四节点只换了提示词、其余调查能力完整等价。

| 所问环节 | 原四节点 | Router当前实际内容 |
| --- | --- | --- |
| 线索/侦查 | Recon模型整理线索，随后做IOC增强 | 选中专业分支基于已有告警字段，各调用一次模型，主要给分类/指标/理由；分支自身不查外部工具 |
| 取证/事件解释 | Forensic单独给时间线、根因假设、范围等结构；本身也没有deep主动补查循环 | 没有对应的独立Forensic阶段；领域分析不保证生成同等时间线/根因/范围结构 |
| 响应 | Responder模型生成containment/eradication/recovery及风险/工作量，dry-run | 只追加分类、分数、已有待处理动作数/技术的dry-run摘要；不调用完整Responder，不生成同等响应计划，也不执行动作 |
| 报告 | ReportWriter模型整理交付Markdown | renderer确定性整理已有状态并保存Markdown，不发ReportWriter模型请求 |

例如Identity只把已有账号、IP、MFA、失败次数等投影给身份提示词，返回分类/置信度/attack_type/identity_indicators/rationale；没有因此自动查IdP、UEBA或认证日志。字段/专业背景帮助理解，与取得新证据是不同能力。已有单次调用/返回代码见[Identity](../../services/agents/app/agents/identity_agent.py)，响应摘要见[Router](../../services/agents/app/orchestrator/router.py)，报告见[renderer](../../services/agents/app/orchestrator/report.py)。

### 5.3 专业分支和其他graph入口

Router先用关键词/字段`classify_signals`选phishing、identity、cloud、insider分支；没有命中时选全四。并行拓扑源码默认开启，每个分支拿同一基础state的副本执行后join，并不是前一专业Agent的输出顺序喂给后一Agent。每个专业Agent一般一次`investigation`模型请求、completion上限768；不做deep工具循环。

Router里命名为responder的阶段是**确定性dry-run汇总**，报告也用确定性renderer，不再发两次模型；若包括前面的auto_triage，一般是1次＋选中的1～4次专业模型，不能按“Agent总数”说6次模型。Case调查开Router时走stream有逐步ledger/MD；Case `/triage`调用run主要是内存状态与事件，不能混用其持久保证。代码：[Router](../../services/agents/app/orchestrator/router.py)。

四个专业Agent每次模型调用的区别如下；共同包含summary、severity，输入都来自已有`raw_alert`字段。**它们自身没有HTTP/PG/厂商现场查询。** 函数虽然支持可选bundle参数，当前Router只传state，没有传入bundle，函数也不从state.context_bundle读取；不能把前述共享预取写成这些分支已经消费。

| Agent / 单次模型 | 实际模型输入 | 提示词与结构输出 | 返回后采用 / 没有发生的查询 |
| --- | --- | --- | --- |
| [Phishing](../../services/agents/app/agents/phishing_agent.py) | 发件人/域/Reply-To/Return-Path、主题/收件人、URL/附件hash、SPF/DKIM/DMARC、正文片段 | `phishing.system`；verdict/confidence/rationale、phishing_indicators | 写state分类/分数，指标及理由进findings/basis；没有自行查询域龄/信誉或扫描附件 |
| [Identity](../../services/agents/app/agents/identity_agent.py) | 用户/邮箱、IP/位置、设备/UA、认证/MFA、失败数/尝试数、权限变化/登录时间 | `identity.system`；共同三项＋identity_indicators/attack_type | 写分类/分数/依据及攻击类型摘要；没有查IdP，也未重新计算impossible travel |
| [Cloud](../../services/agents/app/agents/cloud_agent.py) | 云商/区域/账号与资源、API动作/principal、IP、已有ACL/安全组/IAM权限/公网标记及finding | `cloud.system`；共同三项＋cloud_indicators/risk_category/cloud_provider | 分类/分数及云商/风险/指标进入findings/basis；没有自行调用AWS/Azure/GCP |
| [Insider](../../services/agents/app/agents/insider_threat_agent.py) | 用户/部门/岗位/雇佣信息、动作/资源/IP/目的地、文件量/大小、时间/工作时段、流量/USB/近期活动、已有baseline_deviation | `insider_threat.system`；共同三项＋threat_indicators/threat_category/user_risk_level | 分类/分数及用户风险摘要进入findings/basis；没有重新查询HR/DLP/USB或UEBA |

这四个模型分类只接`true_positive/false_positive/benign`，confidence限制到0～1；调用/解析失败留错误finding并返回原state，不另调一次模型。没有独立专业结果块，专业Agent也不新增MITRE或响应动作。Router join保留各分支findings，按`TP > FP > benign`选结论，同结论选较高confidence及对应依据。提示词写“检查域龄/权限/行为基线”只是分析要求，不能据此宣传外部查询已经实现。

`/agent-runs`的full graph则保留auto_triage入口，满足关闭条件可提前终止，否则进入第3节G1—G4。它与Kafka升级共享graph节点，不证明两个入口在运行配置、身份或交付状态上已经同等验收；本轮不为兄弟入口逐个再跑整链。

## 6. 逐调用审计如何阅读

“把每一步讲清楚”包括核实可见输入、调用和依据，不是索取模型隐藏推理。当前账本没有保证保存所有服务的完整原响应；缺少的审计材料必须明确，不以新文档追认已存在。

| 层次 | 实际可查内容 | 当前记录边界 |
| --- | --- | --- |
| Alert/Case/Run关联 | Alert快照、Run tenant及关联ID、首次triage与后续graph结果 | 自动Run.case_id曾用canonical Alert ID；不能当真实Case链接 |
| graph节点 | graph_step主要保存节点名、完成摘要与耗时；另有graph_result完整有界结果、完成/partial与usage事件 | graph_step本身没有每个节点完整输入输出副本；节点名不证明内部工具成功，step序号不等于每轮模型序号 |
| deep每轮模型 | `graph_llm_exchanges`等工件中的agent/purpose=tool_loop:n、可见messages/response、tool_calls及ID | 可能有可见长度裁剪，hash与完整wire不同；旧C2没有逐轮usage，只有该阶段6calls合计 |
| deep每个工具 | `tool_call`事件含tool/args/result_preview，序号从10000开始；下一轮ToolMessage带匹配tool_call_id | preview约200字符，ToolMessage也有边界；不等于完整SQL结果归档。ledger_rows可核实际写入数 |
| 默认人工模型/工具 | prompt/response、tool_call、evidence_cited、decision、阶段hash、模型/耗时及费用来源 | 可见响应前8000字符及全文hash；Bundle五类内部查询不自动各自产生完整tool_call事件 |
| Router专业Agent | stream主要记分支signal、verdict/confidence、耗时等步骤材料 | 专业Agent没有record_llm_exchange，不能照搬默认四节点或deep的逐轮prompt/response工件保证；需要时再按实际功能取舍补接 |
| 报告与费用 | Markdown工件、graph/triage usage及measured/estimated/unpriced cost | 预约单位不是tokens；价格未知不是免费；报告可读不代表事实/引用质量通过 |

持久和读取入口：

- API `GET /api/v1/investigations/{run_id}`查Run，追加`/events`、`/artifacts`及`/artifacts/{artifact_id}`查步骤/材料；`/explain?step=...`、`/timeline`、`/replay`作已有只读审计。以[API定义](../../services/api/app/api/v1/endpoints/investigations.py)的参数为准，replay不是再次运行模型。
- Agents `GET /api/v1/investigations/{run_id}/report.md`读取所支持调查路径的Markdown；API `/bundle`可打包已有材料。各入口仍受tenant/Run归属及当前开放范围约束，不因文档列出就算全部已开放。
- 默认人工普通run结束后批量保存事件，stream逐条持久再发step；自动graph由runner保存节点/结果，deep保存工具事件。具体实现见[ledger](../../services/agents/app/investigator/ledger.py)、[runner](../../services/agents/app/graph/runner.py)、[人工orchestrator](../../services/agents/app/investigator/orchestrator.py)。

后续每个代表例子用“序号、Agent/模型角色、实际输入、工具及参数、返回状态/来源、如何影响下一步、审计ID/工件、tokens及结束原因”讲解；这是使用现有证据的说明格式，不先新建统一审计schema/服务。

## 7. 原C2实际Run：每次调用究竟做了什么

下表由原C2六轮交换工件、tool事件和成本记录只读复原，复用[自治R01公开回执](../operations/integrity-autonomy-r01.md)，**没有再调用模型**。示例host按“该告警主机”表述，避免把示例值当固定参数。各轮都是同一个deep-investigator，不是6个Agent。

| 实际顺序 | 调用 / 收到的输入 | 模型选中的工具及关键参数 | 返回与下一步 |
| --- | --- | --- | --- |
| 0 | 首次auto_triage，告警和五类reader材料 | 无工具循环 | needs_review/0.85；不关闭，首次2117 tokens=1968输入+149输出 |
| 1 | deep第1轮：当时版本告警摘要、策略及工具说明 | `process_activity(hostname, hours=24)` | available=false / LakeQueryError；第2轮看到失败，不能读作无进程活动 |
| 2 | deep第2轮：原材料＋上轮ToolMessage | `entity_timeline(hostname, hours=24)` | 同类查询失败；第3轮继续 |
| 3 | deep第3轮：加入上轮失败 | `network_connections(hostname, hours=24)` | 查询失败，未获得连接证据 |
| 4 | deep第4轮：已有失败及技术线索 | `lookup_technique(T1110)` | 成功取得ATT&CK背景知识；以匹配tool_call_id进入第5、6轮实际prompt，不是现场攻击事实 |
| 5 | deep第5轮：包含上述知识和失败记录 | `technique_activity(T1110, days=7)` | Lake查询失败，不证明该技术没有其他活动 |
| 6 | deep第6轮：包含前面可见记录 | `extract_iocs(alert摘要)` | 成功提取IP；随后到六轮cap，**没有第7轮最终综合回复** |

这一Run的graph实际只执行`triage → enrichment → investigation`。deep六次模型合计20451 tokens=19797输入+654输出；**原材料没保存每一轮单独usage，不能拆分或均摊**。加首次分诊2117，Run为22568 tokens、7次回复，均unpriced，费用未知。

deep当时`truncated=true`，最后IOC ToolMessage被旧实现当narrative；节点后graph核到20451超过20000边界，保存partial/running，未走attack_path。报告存在无据确认/范围断言，完整调查与报告质量失败保持，不能因Run completed或Markdown可取改写结论。

当前工作区已有deep材料投影、cap/预算及证据边界修正，直接测试结果见[graph源码修正回执](../operations/integrity-graph-correctness.md)，**尚未部署/真实模型验证**；默认人工candidate05修正和本C2路径不是同一批代码。原C2用的是candidate04，不能用新源码解释成它当时已经正确收束。

## 8. 后续按怎样的粒度实施

先按[分诊工作卡](triage.md#7-接下来的实际实施顺序)弄清第一步判定和交接，再依次讨论：自动调查state/查询范围→工具真实后端与返回语义→deep策略与逐调用采用→Attack Path真实关联→人工各Agent及Markdown输出。每次只处理当前模块确定要用的功能，说明上述每步的支持/默认/当前配置、所需改动与最少例子。

已有C1/C2、人工R01、full配套等有效证据优先复用；当前不预定重新调用四节点/六轮模型或完整入口矩阵。确有接线缺口再按原OpenSpec任务做最小修改及本地代表验证，保留版本并在阶段收尾发布一次。源码取舍、查询范围或路由合同改变先讨论和更新对应设计/规格；缺数据、复杂可用性/冗余和未使用分支继续登记，不扩采集或新框架。
