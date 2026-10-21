# 告警与调查：官方声明和实际实现对照

2026-10-21。服务范围、完成条件和实施次序仍以[当前范围](alert-processing-scope.md)、[完成计划](completion-plan.md)、[PROGRESS](../../PROGRESS.md)为准；本表服务于源码理解和二开，不增加一套验收门禁。结构和扩展位置见[告警处理架构](../architecture/alert-processing.md)。

当前第一步按最新口径只先接通告警输入到自动实际调查及基本结果报告读取，已由[B4 case02](integrity-autonomy-r01.md)覆盖。下表质量失败、缺源及原版差距继续保留，转迁移后评估，不据此扩大当前修复或测试。

对照固定上游 `34ca18c57dd4175539e5c6dd3d04a72dc057306b`，本机只读参考位于 `/Users/lychee/Documents/project/SOCAI/opensource/AiSOC`。这里选择核查告警、Fusion、分诊、调查、知识和报告的 **18 组声明**，不表示已审完上游所有文档、功能或测试。源码结论针对当前工作区；B1 已按[限定回执](integrity-b1.md)在21部署并核受理链，candidate03已部署B2/B3/B4/B5及报告修复。新人工调查[R01](integrity-investigation-r01.md)四次模型/10167 tokens、MD/HTML/PDF200，技术通过但三项内容质量失败；自动两例[B4](integrity-autonomy-r01.md)已有真实结果：一例关闭通过，另一例自动调查partial/质量失败；后续未部署修改单列，不能外推整体完成。

## 2026-10-21当前迁入对照（源码、运行与原版缺口分开）

本次按固定上游git tracked路径做存在性核对，未做hash/测试/模型/部署：API872/872、Fusion115/115、Agents426/426、Actions165/165、enrichment19/19、threatintel45/45、UEBA37/37，合计1679/1679，缺失0。Agents原函数/类名及HTTP/WebSocket路由声明亦无缺项；结合既有来源及补丁记录，未发现所选服务内删文件、删入口的功能裁剪。此结论不表示每个函数内部与上游逐字/行为相同；项目已有认证、持久、字段/配置接线和修复差异，以及有意运行隔离。

下表功能源码均已随这7个完整服务带入。“未启用、未配置来源、未专项验证、上游未接线/占位”均不得笼统记成“未迁入”。

| 功能/原版模块 | 已带入的能力 | 当前可用性、暂缓与原版边界 |
| --- | --- | --- |
| 告警受理/API、Fusion | HTTP/Kafka输入、校验、来源身份、持久化、fused发布 | 主链已实测；保留必要本地交付/租户修复 |
| Fusion处理 | 去重、关联、风险/优先级、处理规则、抑制、IOC上下文 | 核心处理已接通；ML训练/效果未作为通过，原检测相关代码随包保留、当前不开启原始事件检测 |
| 告警/Case运营/API | 查询、状态、人员、Case关联、任务/评论/时间线等服务端实现 | 告警/Case/Run主链关系已用；全部运营接口未逐项验收，前端另属未迁整模块 |
| 自动分诊/Agents | 模型分类、理由、依据检查、预算、持久结果 | 已有真实模型/持久实录；完整质量未过，常驻worker仍OFF |
| 自动关闭/升级/Agents | 原关闭策略、canonical状态写回、未关闭后进入调查 | 受控样例已实际关闭或自动执行调查；自动调查有partial/质量失败，常驻review_only/worker OFF限制仍在 |
| 人工调查/Agents | Recon→Forensic→Responder→Report | 默认四节点和Markdown生成/保存/读取已实证；内容质量另列 |
| Router/full graph/deep | 原编排、工具循环、路由及结果接口 | 入口/实现都在，自动样例实际进入graph/deep；Router等所有分支未逐一实测，不能据此写未迁 |
| 历史事件补查/检索 | Fusion LakeWriter、ClickHouse SQL、参数化调查工具、已有外部SIEM查询适配 | 单规范化事件→湖→同租户1行/另一租户0行/进程补查1行已实测；完整历史数据须外部提供 |
| Attack Path/Chain | Neo4j/APOC查询、PG关系回退、共享实体的告警链关联 | Path已实际返回PG Case→Alert关系；完整观测图无自动补造，事件图投影及足够关联告警仍取决于来源/原接缝 |
| UEBA | 特征提取、实体/peer基线、偏差评分、异常持久/发布与查询 | 单事件基线、HTTP及Agents认证读取已过；成熟基线/peer/异常效果未验，1样本不等于功能未迁 |
| IOC增强/enrichment | 原provider客户端、单条/批量并发、合并、Redis缓存 | 服务/缓存/接口已实测；厂商凭据未配。Shodan/URLScan/IPinfo原版仅配置声明、没有客户端 |
| TI/OpenSearch | Feed、STIX、调度、去重、索引/搜索/匹配、actor归因、Qdrant/Neo4j存储 | OS合成IOC写/搜/匹配、TI/API读取已过；airgap/Feed0/空向量集合是当前配置/数据状态，真实Feed与归因效果未验 |
| 知识/记忆/技能 | KB检索、组织记忆、技能、处置、身份上下文、语义memory接口 | 当前PG全文及五类读取已有证据；不同向量路径未全部进入正常调查，不是相关源码丢失 |
| MITRE/ATT&CK | 普通map/lookup、完整语料读取及semantic helper | 普通查询有实际调用；语义helper源码保留，固定上游正常调查也未调用它 |
| Playbook | 原触发匹配、引擎、步骤、investigate action和样例 | 原79文件和样例保留；专项暂缓，默认关闭，原alert_context/case_id接缝另记；不是模块没迁 |
| 反馈/持续学习 | 人工纠正、处置意见、memory override、蒸馏等代码 | 近期处置读取已用；反馈写回/学习闭环后置，部分夜间/在线记忆接线原版也未完成 |
| 审批/响应/Actions | 处置提案、审批、厂商动作、dry-run与回执实现 | dry-run已有证据；Actions对外仍仅开放discovery/dry-run，真实响应未启用，不能称为源码被删 |
| Ledger/模型用量 | Run、步骤、工具/模型可见材料、工件、usage/cost、导出/回放实现 | 主要调查路径及结果读取已有实证；不保证全部分支全文/费用/质量均通过 |
| 调查报告 | Markdown、HTML、PDF源码/路由 | 当前只要求Markdown；HTML/PDF保留但专项后置，不能写成格式源码没迁 |
| Swarm/通用定时报告 | 并行假设/debate组件、reports handler/scheduler | 源码完整带入；Swarm正常触发未接、通用reports pending消费/渲染占位属于原版差距，迁移未新造缺口 |
| 深度取证数据类 | process_tree、mailbox、OAuth grant、persistence工具入口 | 原版就返回not_ingested/unavailable；不是本地删实现，也不能靠复制变成已实现 |

### 确实尚未迁入的是独立模块，不是上述服务内裁剪

| 独立模块 | 当前事实 |
| --- | --- |
| ingest、connectors | 整个服务未选入当前部署/源码迁移；负责采集、规范化及外部数据接入，当前接收已有告警/规范化事件。API客户端源码存在不代表这些独立服务也已迁入 |
| apps/web等前端、realtime | 整模块未迁；当前服务端交付不含20的页面/独立实时展示服务 |
| slack-bot、teams-bot | 独立机器人未迁；API相关入口即使随包存在，也不等于War room外部协作服务已部署 |
| MCP、mesh、honeytokens、purple-team、osquery相关、demo-producer等 | 独立平台/探测/演示服务未纳本轮；不是从API/Fusion/Agents/Actions中删除了相应文件 |

因此，应说“所选7服务完整迁入，部分能力未启用/缺源/未验/上游已有缺口”；不能说“上游整个仓库已经全部复制”，也不能把尚未选入的独立模块隐瞒成仅未启用。代码之外的外置服务、规则/语料、模型及真实历史资料仍须按实际来源分别记录。

## 判定与资料

- **已实现**：有可追到的入口和被调用的实现；是否真实运行、质量通过另列。
- **未接通**：组件存在，但本次核查的正常入口没有调用它；不能推广为所有扩展入口都不可用。
- **功能缺口**：入口或输出合同存在，具体实现仍缺一段或只有简化内容。缺源、配置关闭、尚未实测均单列，不据此判作源码缺失。
- **文档滞后**：同一固定版本的源码已比该段文档前进，或文档自己明确列为后续接线。

复用[历史分析入口](../anal/README.md)、[M02 Fusion](../anal/02-fusion.md)、[M03 告警/Case](../anal/03-alert-case.md)、[M04/M05 调查](../anal/04-triage-investigation.md)、[M06—M09 工具/知识/模型](../anal/05-tools-knowledge-model.md)及[交接版索引](../reference/aisoc/README.md)。历史分析中的风险和建议须以当前源码复核，不能覆盖后续已修批次。

官方依据均读自固定版本本地原件：

| 编号 | 官方原件及本次使用部分 |
| --- | --- |
| O1 | [README](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/README.md)；[architecture](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/apps/docs/docs/architecture.md)：融合交付、自动分诊、账本、响应边界 |
| O2 | [architecture/overview](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/apps/docs/docs/architecture/overview.md)：服务与 Qdrant 职责；[architecture/agents](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/apps/docs/docs/architecture/agents.md)：四个公开 façade、调查和账本 |
| O3 | [groundedness](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/apps/docs/docs/concepts/groundedness.md)；[llmops](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/apps/docs/docs/concepts/llmops.md)：指标依据检查、prompt/模型与缓存合同 |
| O4 | [triage-context](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/apps/docs/docs/console/triage-context.md)：组织记忆、skill、runbook、advisory/cutoff；[agent-vendor-tools](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/apps/docs/docs/operations/agent-vendor-tools.md)：租户只读工具及缺后端语义 |
| O5 | [capabilities](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/apps/docs/docs/concepts/capabilities.md)：KB 全文检索/答案、报告及成本遥测 |
| O6 | [investigation-swarm](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/apps/docs/docs/concepts/investigation-swarm.md)：复杂度触发、并行假设与 debate；[compounding-memory](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/apps/docs/docs/concepts/compounding-memory.md)：蒸馏与明确尚待接线项 |

## 声明 → 调用 → 状态 → 证据与处理

表内“当前验证”引用已有冻结回执，不把上游测试数量、上游演示或本项目结构检查写作业务质量证明。源码存在、已部署、实际调用、结果质量是不同状态；本表同时支持原版理解、功能差距判断和二开导航，不另立完成标准。

| ID / 官方声明 | 实际源码入口与调用 | 实现状态 | 当前验证、影响与处理 |
| --- | --- | --- | --- |
| F1 / O1：告警提升、去重关联、增强/评分，持久后交付 fused | [consumer.py](../../services/fusion/app/workers/consumer.py) `process_alert → _fuse_and_persist` 调用引擎、恢复首次快照、确认 PG、等待发送；[fusion_engine.py](../../services/fusion/app/services/fusion_engine.py) 组织融合步骤 | **已实现**。本项目从已有告警开始；不以此交付采集和原始事件检测。不同 source-v1 告警保留独立行后关联，legacy 另有兼容语义 | [1F](1f-alert-chain.md)、[2A](2a-source-identity.md)、[C01](c01-fusion-delivery.md)为限定证据；有限 TTL 痕迹全失、旧无快照行不外推恢复。保留上游服务边界和现有持久/确认保护 |
| F2 / O2：Detect façade 可同步调用融合能力 | [agents/__init__.py](../../services/agents/app/agents/__init__.py) `DetectAgent.process → tools.fusion.process_alert`；[Fusion router](../../services/fusion/app/api/router.py) `/process → worker.process_alert`，与 Kafka 共用确认路径 | **本地适配已修、部署并限定验收**。B1 统一身份、首次结果和持久/发布确认，写前核tenant，保留FusedAlert响应；O2称process未交付已落后于固定版本源码 | [B1](integrity-b1.md)：119项直接测试、Fusion c52b9aac、10次真实HTTP，两条source-v1核两入口顺序/PG/API、独审accept。Agents工具tenant头已随组合候选部署；未另把façade调用写作真实验收。0模型、worker OFF |
| F3 / O1/O2：ML 异常与优先级评分、可解释置信度 | [ml_scorer.py](../../services/fusion/app/services/ml_scorer.py) `score/_predict_anomaly/_predict_priority`：已训练模型或 heuristic fallback；[confidence.py](../../services/fusion/app/services/confidence.py) 生成因素链 | **实现存在，训练/效果未据此验证**。模型未就绪时回退不等于 trained ML；risk、priority、severity 和 confidence 不是同一指标 | 既有风险/来源语义见[3A-03](3a-risk-score.md)。本轮未训练或评估评分模型，也未重验 ML 状态接口；保留算法，报告实际采用方法，不将数值存在写成模型有效 |
| T1 / O1/O3：每条 fused 进入受控分诊，依据检查、prompt 版本、预算和用量可追溯 | [fused_alert_consumer.py](../../services/agents/app/workers/fused_alert_consumer.py) `triage/_llm_triage/_apply_groundedness_gate/_record` → [auto_triage_agent.py](../../services/agents/app/agents/auto_triage_agent.py)、[contract.py](../../services/agents/app/llm/contract.py)及分诊持久层 | **代码已实现，自治质量未过**。groundedness 主要核具体指标存在；O3 明确不判整段结论真伪，不能据 gate 存在保证时间/授权推理正确。C02 普通 live 已停止跨告警 pattern 结论复用；不把 O3 通用缓存说明套到所有入口 | [C02](c02-triage-material-cache-stop.md)、[v5](c03-triage-detection-validity.md)及[质量失败](c03-triage-validity-quality.md)保持；后者错误为时区/分类，告警仍 new、未错误关闭。模型路由[1E](1e-model-gateway.md)只验路由/结构，不是分类质量 |
| T2 / O1/O2：可关闭告警自动关闭，需调查时自动升级 | worker结果/状态与writer；`_maybe_escalate → graph.runner.run_escalation`；[workflow.py](../../services/agents/app/graph/workflow.py) post-triage图，跳过已完成的自动分诊模型 | **功能源码及结果补接已部署，有限真实关闭通过、自动调查未完整通过**。常驻review_only/workerOFF保持；有限C输入使用原worker/策略，不能据一例正确关闭外推自治质量 | [B4](integrity-autonomy-r01.md) C1 BTP0.95按原0.85阈值实际关闭；C2 NR0.85未关闭并自动进graph，六回复/六工具但partial，错误confirmed/攻击阶段表述阻断完整通过；两例8回复24742tokens。保留失败，不新增规则引擎 |
| I1 / O2：调查由多能力协作并交付结构结果 | [API cases.py](../../services/api/app/api/v1/endpoints/cases.py) `case_investigate → Agents launch_investigation`；[investigate.py](../../services/agents/app/api/investigate.py) `_investigate_stream → InvestigatorOrchestrator.stream`默认Recon→Forensic→Responder→Report；可选[RouterOrchestrator](../../services/agents/app/orchestrator/router.py)，full graph另一路 | **已实现并部署，编排不等价**。默认InvestigatorState与graph InvestigationState不可混用；Responder计划/dry-run不表示执行 | B2身份/材料接缝及B5输出已部署。[R01](integrity-investigation-r01.md)默认四节点4次模型/10167 tokens、25事件、MD工件及七次归属拒读通过，内容仍有三项失败。其他入口源码/直接测试不据此升级为真实业务通过 |
| I2 / O4：调查可读取上下文和租户配置的只读厂商工具，无法检查要明说 | [bundle_prompt.py](../../services/agents/app/investigator/bundle_prompt.py)→[ContextBundleBuilder.build](../../services/agents/app/context/bundle.py)；graph Investigation→[deep_investigation.py](../../services/agents/app/investigator/deep_investigation.py) `scoped_customer_tools/ToolRegistry/run_with_tools`→[API agent_tools.py](../../services/api/app/api/v1/endpoints/agent_tools.py) | **读取/工具代码及必要接缝已部署，实际数据源另验**。默认四阶段读取上下文不等于deep主动补查，不等于已查厂商 | [2C-03](2c-event-ueba-sources.md)真实事件/UEBA尚未接；R01仍有增强/图缺源，不能把失败当观察。candidate04通用七权限只读服务身份已接；C2 MITRE真实查T1110且结果进入后续ToolMessage，四lake查询availableFalse、无厂商连接。另发现deep摘要遗漏源username/raw_event，正修原字段投影；有scope/schema不证明取证成功，缺源保持unavailable/unknown |
| K1 / O4/O5：KB runbook 与组织记忆/skill 等指导分诊 | [context/knowledge_base.py](../../services/agents/app/context/knowledge_base.py) reader → [knowledge_base.py](../../services/api/app/api/v1/endpoints/knowledge_base.py) `retrieve_runbooks_for_triage/triage_retrieval_sql`，PG `tsvector/plainto_tsquery/ts_rank`；分诊另读组织记忆、技能、处置、身份 | **已接分诊，全文检索是该官方声明的实现方式**。不因没有向量便判 KB RAG 缺失；五类 reader 和各自权限不同，来源、prompt 文本、模型引用分开记 | [3A-04](3a-org-memory.md)—[3A-08](3a-identity-read.md)为 A/B 合成资料限定验收；[3A-06](3a-kb-read.md)的 KB1 已进 prompt，但模型未引用标记，引用质量未过。cutoff 保守排除晚建/晚改，不重建历史正文；保留这些限制 |
| K2 / O2/O5：调查与报告实际消费知识，而非只有KB查询接口 | [knowledge_prompt.py](../../services/agents/app/investigator/knowledge_prompt.py) `prefetch_knowledge`复用KB reader，同Run一次；四阶段append/record；ReportWriter据实际解析标记追加来源 | **B3已部署，实际片段消费已证、语义质量未过**。提供片段、可见标记、解析来源和支持结论分别核 | B3直接验证/独审保留；首Run7bc46722质量失败、PDF500保留。新[R01](integrity-investigation-r01.md)同一KB块逐字进入4个prompt；Responder实际`(KB1)`、Report实际`Citation: KB1`，旧parser却记0，不能说无模型标记。裸标记parser修复32项通过，离线测试时未部署；随后candidate04已部署、来源/配置及6HTTP身份独审限定accept（0模型/消息，非业务质量），旧Run不回填，KB背景变事件事实仍属内容失败 |
| K3 / O2：Qdrant 为 Agents 提供向量 RAG | [API semantic_memory.py](../../services/api/app/api/v1/endpoints/semantic_memory.py) 提供 items/recall/status；[services/semantic_memory.py](../../services/api/app/services/semantic_memory.py) 管 embed/index/search；`query_kb` 仅在 `recall_memory=True` 时追加此检索。ContextBundle 的历史默认走 [institutional_search](../../services/agents/app/memory/institutional.py) | **向量接口存在，不能推断常规调查已消费**。KB 全文、组织记忆、历史标签搜索、语义 memory 和 ATT&CK 向量是不同链，不用“知识已接”一并概括 | [1D](1d-vector-embedding.md)只证明结构/存取，未证明调查消费。本轮 B3 的默认调查选择 PG 全文，未证明 semantic memory 消费，不把未用向量路径设为此前置。将来选用向量时再核 embedding 模型/维度/集合/tenant；不将索引或连通列作业务通过 |
| K4 / O2：semantic ATT&CK lookup | [main.py](../../services/agents/app/main.py) 可加载完整语料/启动向量索引；[mitre_full.py](../../services/agents/app/tools/mitre_full.py) 定义 `semantic_technique_search`。正常 Investigation 及 [default_registry](../../services/agents/app/tools/registry.py) 实际调用 [mitre.py](../../services/agents/app/tools/mitre.py) `lookup_technique`，另有按 ID 的全文语料读取 | **正常调查未接通语义查询**，不是 ATT&CK 全部缺失。已核正常入口和 registry；目前无应用调用 `semantic_technique_search`。该 helper 与固定上游相同，非本地删失 | B3 若选择此能力，沿实际调查输入接检索并验证来源；否则如实写“当前关键词/ID lookup”。模块、集合或全量语料存在不等于 semantic 调查已启用 |
| I3 / O6：复杂事件自动触发 3–5 个假设 agent 并行采证、debate 入账本 | [complexity.py](../../services/agents/app/swarm/complexity.py)、[swarm.py](../../services/agents/app/swarm/swarm.py)、[debate.py](../../services/agents/app/swarm/debate.py) 分别有评分、并行计算、辩论函数；但默认 Case、router、graph 无触发调用；`_agent → _evaluate` 为关键词/技术集合计算 | **组件已实现，官方描述的正常触发/模型采证/持久 debate 未接通**。`tokens_spent=min(budget,200)` 是确定性样例值，不能当真实模型 usage。三文件与固定上游相同 | 不把单测/演示 swarm 优势移作本项目调查质量证据。作为上游能力差距记录；多模型 swarm 不自动扩为本批必做项，现有告警调查主链仍按 B4/B5 完成 |
| A1 / O1/O2/O5：每个prompt、工具、决定、token/cost全部入Investigation Ledger | 分诊`persist_auto_triage`；默认[orchestrator.py](../../services/agents/app/investigator/orchestrator.py) drain audit_log/报告；graph [runner.py](../../services/agents/app/graph/runner.py)、deep及tool_loop；I2原子追加graph_usage/Run增量 | **按路径实现，B4补接已部署**。graph_result/MD/HTML/可见调用材料与首次分诊分开；不能概括全路径全文齐全 | I2原79项充分性撤销及PG错误保留；修正后candidate02 Agents232、后续candidate03去重358Agents+复用25API通过。B4 151项及独审是直接证据；C2真实graph六模型20451tokens、11工件API/PG匹配，Run22568=首次2117+graph20451；C预约observed只计首次，不等于整Runusage。技术链成立而graphpartial/内容失败。R01默认链四组prompt/response/hash、usage及PG MD通过，不外推全transcript、崩溃恢复或内容质量 |
| R1 / O2/O5：调查交付可读报告和证据 | [report_writer_agent.py](../../services/agents/app/investigator/report_writer_agent.py)生成MD/HTML；默认orchestrator只持久report_md；B5 [investigation_access.py](../../services/agents/app/api/investigation_access.py)冷读可由MD补安全转义HTML；graph另存MD/HTML；Agents report.pdf与API `/close`生成的investigation-summary/summary.pdf不同 | **调查报告实现及B5入口已部署；技术交付通过，内容质量未过**。failed/partial有工件时可读但状态显式，不把fallback当完整模型报告 | 旧7bc46722 PDF500/截断失败保留；新[R01](integrity-investigation-r01.md)MD/HTML/PDF均200、8节完整、MD与PG工件相等，仍有三项内容错误。默认HTML本次未持久，不声称重启后原HTML字节保持；未运行可用性矩阵。长度只按真实finish_reason处理，不追称旧事件有该元数据 |
| R2 / O1：可导出带签名、可核对的证据 bundle | [investigations.py](../../services/api/app/api/v1/endpoints/investigations.py) `export_evidence_bundle → build_bundle/serialize_bundle`；[evidence_bundle.py](../../services/api/app/services/evidence_bundle.py) 规范 JSON、prompt digest、HMAC-SHA256、usage 未知处理 | **导出实现存在，内容完整性受已落库事实约束**。签名不是完整调查事实证明；当前 `approvals=[]` 明确没有装入 Actions 审批，并非“无需审批” | 本轮仅沿调用复核，未新发真实 bundle/做篡改验证；B5 复用必要结果出口验收。若 graph 缺最终材料，导出不会自行补齐；不宣称公钥不可否认性或完整审批链 |
| R3 / O5：通用reports支持异步按需/定时PDF/HTML、工件与投递 | [reports.py](../../services/api/app/api/v1/endpoints/reports.py) `generate_report`仅插入pending；[report_scheduler.py](../../services/api/app/workers/report_scheduler.py)从cron模板另建HTML，`_render`仅标题/时窗/模板说明；`/digest/weekly`另调[executive_digest.py](../../services/api/app/services/executive_digest.py)实构摘要 | **按需pending消费缺口、定时renderer仍为占位简化**。调度/SMTP存在不证明通用PDF/章节报告完整；weekly digest及调查报告不是此stub | 上游既有差距，本轮未补实现、未触发发送。R01的调查MD/HTML/PDF200不证明通用reports可用；董事会/定时投递扩展后置，承诺此出口时需补请求消费及实际内容 |
| M1 / O6：蒸馏历史让后续判断持续改善 | [Fusion memory](../../services/fusion/app/memory) 有 distill/stage/export-import 等组件；O6 **Status 明确说** nightly scheduler、live memory stage 和提升图表尚待接线 | **组件与文档明确的待接线项并存**。不能把开头宣传性“nightly”描述当成当前自治持续学习已经运行，也不应称文档隐瞒所有限制 | 组织记忆读取实测只证明消费既有受控资料。反馈/蒸馏专项按用户口径后置，保留一体源码，不为本表新增调度或改反馈流程 |
| D1 / O2/O4：公开 façade 和只读工具配置说明 | `DetectAgent.process` 已有委托实现（F2）；[customer_tools.py](../../services/agents/app/tools/customer_tools.py) `_service_token/_headers` 实际读 `AISOC_API_SERVICE_TOKEN` 或 `AISOC_SERVICE_TOKEN`，携 `X-AiSOC-Tenant-ID`；O4 仍写 `AISOC_AGENTS_API_KEY` | **固定版本内部文档滞后**，不能据旧文案判方法/认证实现缺失；也不能照旧文案配置后把 401 归作厂商无数据 | 实施以实际 auth/tenant 合同和项目[配置索引](configuration.md)为准，保留官方原件。本轮 B2 核真实调用身份；长期文档修订只改本项目说明，不改只读参考源 |

## 几项负结论的核查边界

1. **语义 ATT&CK 和 swarm**：除检索全 `services/agents/app` 的引用外，已读默认 Case `_investigate_stream/InvestigatorOrchestrator`、graph 的节点包装与 Investigation 实现、router 拓扑、deep 的 registry 构造。没有将“搜不到某字符串”单独作为未接通证据。K4 与 I3 是这些正常入口的结论；外部调用 helper 和测试/演示仍可能运行组件。
2. **graph 可追溯性**：读了 runner 的 `record_event/complete_run`、tool loop 的 messages/trace 返回、deep 的账本落点。工具调用有记录，不能说完全未入账本；核查时缺的是每轮调用材料及最终调查/报告的正常持久出口；B4 已做最小源码补接并过直接测试/独审，业务验收未外推；材料遵从原 literal 上限和 hash，不收隐藏推理。I2 只修正常 usage 组合；默认四阶段已有 audit/report 持久，不在缺口内。
3. **通用报告**：同时读了 POST handler、启动时 scheduler 开关、`run_once` 的模板查询/新建 artefact、`_render/_deliver` 及独立 weekly digest；当前 scheduler 未查询 pending artefact。没有将“没启动调度器”误作唯一原因，也未将真实 digest 或调查报告判为占位。
4. **缺源和质量**：图、UEBA、厂商工具及 runbook 为空、失败或未配置，应保留明确状态；来源能读取、片段进 prompt、模型实际引用、引用支持结论、业务决定正确是五个不同事实。模型预算预约单位不是实际 usage，未知费用不写零。

B4 的每轮可见调用记录复用原 `record_llm_exchange`：prompt/response literal 各最多8000字符，hash覆盖完整可见材料；工具文本是实际送入该循环的有界渲染结果。它不是完整原文归档，也不等于 `safe_ainvoke` 内部 egress 处理后的 provider wire body；不能用 hash 代替“全文已保存”的证明。隐藏推理字段和 reasoning 内容块不入该记录。

## 本次覆盖与后续

本表选择18组声明核源码/文档，文档更新本身没有运行模型、厂商查询、消息或部署。引用的B1、I2、candidate03及R01实测分别保留各自方法、失败和限制；R01为4次真实模型，不得混同断网替身测试。旧冻结回执及旧Run均不改写。未覆盖采集/原始检测、前端、全部响应厂商、playbook/反馈专项、整个上游文档或全仓测试。

下一步复用[完成计划](completion-plan.md)处理已定位的正常结果缺陷和实际自动关闭/升级业务，将未部署修复与新输入验证另记；不把本轮人工技术通过当作质量或B4自动链通过。已存在但未启用/缺源的能力不重复造框架；上述上游扩展差距不自动加入当前完成条件。启动/退出/故障恢复专项另记后置，不用增加大矩阵代替正常功能交付。

## 20的Case页面与full需求：2026-10-21只读分析

**后续决定已更新：** 用户随后确认历史补查、Attack Path、UEBA、事件检索、IOC增强和OpenSearch需要按原版设计迁入并保证基本运行；21既有基础设施复用。以下只读发现保留，先前“是否采用/暂缓full”的建议不再代表当前范围。实际源码、必要适配、数据流及运行证据见[full配套迁移](full-support-migration.md)。

用户提供Overview、Investigation、Attack Path、Attack Chain、Ledger、Report六张截图。本次对照20实际固定revision `34ca18c…`、现有记录及源码，不发起调查、模型、评论、建频道或配置修改。21对照已部署candidate05和既有业务回执；工作区后来保留的未发布修复不算运行能力。

### 本例事实

截图Alert `b6f8d542-a461-5b03-b515-6da94297b205` 精确对应20 golden pipeline合成事件 `5c3757a85756`。输入由[上游验收脚本](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/tests/e2e/golden_pipeline/run_golden_pipeline.py:117)构造，包含WIN-FIN-01、j.doe、Office启动编码PowerShell；connector_type写crowdstrike，不等于真实厂商取证。旧[部署记录](/Users/lychee/Documents/project/SOCAI/deploy/aisoc20/README.md:46)与本项目[既有证据](verified-evidence.md)均已标合成。调查和基础设施调用是真实执行，不能据此认定真实入侵。

Case `e239bb33-5cdb-44ea-bae1-7a357138df8d` 的截图Run `c4018146-5e8e-4b5c-b313-692a1605e125` 在PG为completed，开始时间2026-10-19 23:20:53 UTC；20当前Agents容器启动于23:33:46 UTC。使用已有服务身份/指定tenant读该Run结构返回404，而其PG账本及6015字节MD仍在；同Case后来Run `43d309c3…` 返回200且recon/forensic/responder字段齐全。这与上游只把结构结果放进程内存、前端恢复吞读取异常的接缝一致。

截图Run有四条LLM回复事件，用量974+1378+1339+2731=6422；成本表记8calls/12844，正好二倍。固定源码safe_ainvoke和四节点分别记录同一回复，存在重复计量；不要把8个入账call当8次独立成功推理。本例成本表measured_call_count=8、estimated/unpriced=0，金额记0；该记录也不代表已计设备等总成本。21既有响应身份去重和四回复/四calls实证另见[R01](integrity-investigation-r01.md)。

### 页面功能、缺口及迁移状态

| 页面项 | 原版实际行为或缺口 | 21状态；是否靠full解决 |
| --- | --- | --- |
| Investigation四节点 | 默认Recon→Forensic→Responder→Report真实存在；Case状态与Run状态独立 | 后端已迁并实测；不依赖full。前端未纳入当前迁移 |
| 三块结构卡片 | 旧_run仅内存，刷新先设completed再读结构，失败被吞；Ledger不反向水合卡片 | 已补基本Run/报告冷读，但默认三块结构的持久恢复仍未补齐；full无关 |
| Attack Path | `INCLUDES`来自PG fallback，截图两节点是Case关联Alert；Neo4j无结果也会fallback | API源码已迁，通用图未接真实材料。full可提供Neo4j，仍需Case/Alert/实体同步及读取身份 |
| Attack Chain | PG按同tenant共享实体寻找其他告警、排除seed；无候选返回空正常。MITRE只加排序分，不能单独形成候选 | 源码已迁；不依赖Neo4j或ClickHouse。先看实体字段与相关第二条告警；页面的“entities or MITRE”文案不准确 |
| Ledger | Run/events/artifacts和模型明细已实现；默认Run.model_used未传可为null；存在上述重复计量 | 账本后端及原读取已迁/实测；full无关。模型字段空不等于没调用模型 |
| Report | 页面明确用`<pre>{markdown}</pre>`，故显示Markdown原文；不是渲染失败证明 | MD/HTML/PDF后端已有实测；网页渲染需改前端，与full无关 |
| 三项文案草稿 | 真实contextual/copilot流，缺配置时有明确占位；不发送客户通知 | 源码保留，当前baseline未开放contextual入口；需要模型/路由，非full |
| War room | 真实bot调用，需要Slack/Teams机器人和厂商凭据 | API保留，机器人未部署；属独立chatops profile，非full |
| Tasks | 后端CRUD存在；页面初始未GET任务列表，仅读Case中不存在的tasks字段 | 后端源码已迁，前端水合缺口仍在；full无关 |
| Notes | 前端发`{comment}`，API要求`{body}`；失败仍可显示Saved locally | 静态合同缺口，未发评论验证；full无关 |
| Resolution文本框 | 没有保存handler，普通Case更新schema也无对应字段 | 原版未接完整保存；full无关，不等于所有结案API都不存在 |

关键源码：[页面恢复/卡片](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/apps/web/src/components/cases/CaseWorkspace.tsx:395)、[Markdown展示](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/apps/web/src/components/cases/CaseWorkspace.tsx:2109)、[21冷读](../../services/agents/app/api/investigation_access.py:55)、[图fallback](../../services/api/app/api/v1/endpoints/graph.py:319)、[PG攻击链](../../services/api/app/services/attack_chain.py:426)。普通Case创建/关联没有自动调用graph upsert；原ingest图writer的natural_key/关系投影也不自动等于Case图读接口需要的ID/边，启Neo4j不能补齐该接缝。

### full的实际含义与本项目选择

官方README的core/full是部署profile：[官方说明](https://github.com/beenuar/AiSOC#deployment-profiles)。固定[Makefile](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/Makefile:200)的make up-full在启动full服务之外还开启lake writer与ingest graph两个flag；单选Compose profile不等于自动写入数据。full新增ClickHouse、Neo4j、OpenSearch、enrichment、UEBA、kafka-ui六服务。LLM网关、Qdrant、connectors/actions本就在CORE；不存在本项目只需设置一个AISOC_PROFILE=full便开放全部调查的合同。

“full investigation graph”是另一编排入口；默认Case四节点、router开关与Compose profile独立。“View full report”只是查看报告入口。语义ATT&CK及其embedding/集合维度又是独立接线，不因full自动消费；现PG全文KB不需要OpenSearch。

当前建议保留21服务端职责，按实际数据需求选择：内部历史事件补查才接ClickHouse及事件写入/读取；实体权限关系/图遍历才接Neo4j及投影；实时IOC查询按一家实际来源接enrichment或现有只读厂商工具。独立UEBA、OpenSearch、kafka-ui和chatops不作为当前调查主链前置。21已有共享数据服务可复用，但项目schema、tenant隔离、资料和读取身份仍需实际接入。

真实进程树、邮箱活动、OAuth授权、持久化项等工具有直接返回unavailable的原实现（[工具](../../services/api/app/services/investigation_tools.py:469)）；full不会生成缺失的取证资料或替它们实现后端。若要把20整页接到21，另外需要前端/实时展示及结构结果、任务、评论、resolution合同的收尾；这属于待讨论的扩展，未在本次修改或开启。


## 自动调查实测揭示的原版实现差距

[B4两例](integrity-autonomy-r01.md)将此前“业务未验”具体化。C1原关闭策略在明确匹配授权材料下正确关闭；C2原自动升级真实调用deep及只读工具，未错误关闭，但调查未完成且结论有误。与固定上游逐字节核对，`investigation_agent.py`直接把附带T1110的MITRE映射写成observed/single-stage攻击，`confidence/scoring.py`继承风险/关键词prior并以阈值判confirmed，不能当独立证据证实。`tool_loop.py`六轮结束取最后ToolMessage作叙述，`deep_investigation.py`摘要旧字段接缝漏源账号/正文，实际tracker用量未进入原deep governor。

这些是当前调查结果正确性的实际阻塞，按最小源码修复处理，保原服务/编排/限额和旧失败结果；不是以“上游已有”登记后放任。语义ATT&CK、swarm、通用定时报告等未承诺扩展仍保持上表边界，启动/退出及恢复专项仍后置。修复和直接测试本身不追认C2质量，也不重调原输入。
