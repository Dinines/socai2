# 调查设计评价：默认Case四节点与graph/deep

2026-10-24最新设计为[调查模块规划v4](investigation-planning-design.md)：告警分诊/侦察与Case整体调查保留业务层次，共享问题/证据/分析/执行内核；Case新Run继承材料，创建/关联、启动、领域启用各有政策。20已有自动处理过程和无Case详情，不能用本篇旧建议覆盖它。本文保留旧实现评价与历史证据；实际M4仅有限网络观察通过、M5.1纯合同通过、M5.2增量未测，完整调度及分层入口未交付。当前仅修订方案，见主文档15.4及[实施记录](../operations/unified-investigation-implementation.md)。

2026-10-23本地小修已将Forensic标识检查统一放在Responder/Report之前，两入口一致；降级采用与工具停止交接见[回执](../operations/investigation-result-handoff-20261023.md)。它不构成语义验真或模型拓扑重构，下文旧校验位置为修正前事实；后续设计等待讨论。

后续产品与工程建议见[智能调查优化与扩展方案](investigation-product-engineering-roadmap-20261022.md)：明确急需问题、范围/证据/结论/结果合同和场景演进；仅设计建议，不将下文三编排现状改写为已重构。

本批已补[真实本地模型/工具逐步案例](../operations/investigation-functional-20261021.md)：Router Identity/Cloud、默认四节点含Forensic兜底、Deep六轮/7工具；下文静态示例及旧Run保持，不由新实测追认其质量。两处接口合同已本地最小修正，尚未发布。

2026-10-21。用户要求先详细理解目的、输出及两套流程的设计依据，尤其人工四Agent的实际价值，再讨论二开取舍。本文件是固定版本官方资料、当前源码及已有实测的分析，**不是新功能实施/质量验收，也不决定立即合并或删除编排**。每次调用细节见[调查调用说明](investigation.md)。

每次模型调用“为什么调、实际收到什么、返回什么、代码怎样采用”，以及预处理/工具schema→tool_calls→后端→ToolMessage过程，详见[输入输出及工具合同](investigation-preprocessing-tools.md)。专业提示词、代码固定查询和模型动态工具请求分别说明，不把数据封装当作字段已经完整送达。

## 1. 先给判断及其证据边界

默认Case四节点偏向把现有材料组织成分阶段研判、响应计划和可读报告；graph/deep具备按查询结果继续寻找新证据的能力，同时输出分类/发现/提案、调用轨迹及可选攻击路径。**两者能力有重叠、产物不相同，没有自动连接成“前者调查、后者人工复核”的双层闭环。**

从固定上游路线、变更日志及代码注释，能证明它们有演进先后、旧入口保留及局部能力补充；找不到足以证明“两套完整编排有意设计为严格互补且必须都跑”的统一设计说明。将其解释为多代实现并存，比替作者补造一套完整设计动机更符合证据。

还需区分两个维度：**自动/人工是触发与控制方式，固定流水线/动态工具调查是执行方式。** 当前默认Case点击走四节点；graph也有人工`/agent-runs`入口。人工默认调查只是人发起，此后四步自动运行，并没有天然多出四次人工复核。

### 本轮进一步讨论后的明确结论

| 讨论问题 | 已核实的说明 |
| --- | --- |
| 是否“新系统会逐步取代旧系统” | 能证明演进先后，固定版本尚未找到旧四节点明确弃用/移除计划；旧链仍默认保留。不能把较新能力擅自写成官方确定的替代路线 |
| 较新的能力是哪套 | graph/deep补主动工具调查；Router补领域分支选择及可选并行，二者不同，不能统称一套新系统 |
| Router是否额外可加载模块 | 是内置、可选启用的编排。Case `/investigate`由`AISOC_INVESTIGATE_USE_ROUTER`在旧四节点/Router间二选一；不是插件安装，也不是两套自动串跑；该开关不改变Kafka graph/deep |
| 专业分支是否各完成原四步骤 | 否。每个分支通常只发一次领域模型，给分类、指标/类别、理由；自身无现场工具查询，没有内部四节点链 |
| 是否只是给原四节点换专业提示词 | 专业prompt和字段投影确是特色，但整体任务/输出已经改变：缺独立Forensic阶段，响应是确定性摘要而非完整计划，报告是renderer而非报告模型 |
| graph/deep是否把整个流程交给模型 | 外层节点、工具集/参数、tenant及预算等仍由系统控制；主要让模型在deep内部选择下一查询、根据返回继续调查或结束，不获得任意业务流程/动作执行权限 |

Router有“专业分析→汇合→响应摘要→报告”的外形，不意味着具有与原四节点相同的侦查/取证/响应产物。它与graph/deep也没有当前自动串联关系。后续是否需要补齐或复用某些产物，属于待讨论二开取舍，当前说明不构成改造决定。开关、步骤及对照详见[Router实际流程](investigation.md#51-配置选择的准确含义本轮讨论确认)。

### 官方启用说明与优势的证据范围

固定版本未找到“某告警类别/等级必须开启Router”或全面替换旧四节点的部署建议。官方T2.2计划明确的目标是相关专业Agent并行分析，例如phishing和identity信号同时出现时并行fan-out后join；这与本项目建议的使用场景须分开表达。

有两个独立开关：`AISOC_INVESTIGATE_USE_ROUTER`默认false，控制Case调查选哪套编排；`AISOC_AGENT_PARALLEL_TOPOLOGY`控制Router内部并行/顺序。上游`orchestrator/router.py`开头明确后者开发/CI默认on，**生产先关并行、待eval scoreboard为green再开**；该建议不能误写为前者的官方开启条件。本次仅记录上游原说明，不改变本项目开关，也不将全量基准或可用性测试新增为本轮功能前置。

可从源码判断的优势是领域提示词/字段投影、跨领域独立并行、有信号时选择部分分支，以及轻量的确定性结果汇总。适用判断是：已有结构化领域材料，需要专项或跨领域研判及简洁报告时可考虑；需要现场补查看graph/deep，需要完整时间线/根因/响应计划则不能把Router现有产物视为等价替代。没有信号时会全选四分支，不能保证节省调用。

计划中的p50<60秒/p95<120秒是目标。`test_orchestrator_parallel.py`及`test_latency.py`使用mock Agent/sleep，证明的是Router并行与自身顺序参考的拓扑差异；“至少快30%”不是与原Recon四节点的真实模型比较，也不能证明分类/调查质量更好。出处：[固定T2.2计划](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/plans/aisoc_v8.0_north_star_plan_1dee8c63.plan.md)、[Router开关说明](../../services/agents/app/orchestrator/router.py)、[原比较测试](../../services/agents/tests/test_orchestrator_parallel.py)。本次仅读资料，没有执行这些测试或新增模型比较。

## 2. 官方怎么定位，历史能证明什么

本次以只读参考仓库HEAD `34ca18c57dd4175539e5c6dd3d04a72dc057306b`为准，不用GitHub main的现状代替固定版本。线上检索作辅助，固定提交页面未能在线取回，以下结论核对本地固定上游原件；链接固定提交便于追源。

| 官方材料 / 源码说明 | 实际内容 | 可以得出的结论 / 不能扩大之处 |
| --- | --- | --- |
| [ROADMAP v4](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/ROADMAP.md#v40--shipped)，本地51行起 | 已交付Orchestrator、Recon/Forensic/Responder/ReportWriter及Case调查/报告页 | 四节点是较早的正式产品形态，非本地迁移拼出的替代流程；勾选不能代替当前实际质量 |
| [官方Cases的AI Investigation](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/apps/docs/docs/concepts/cases.md#ai-investigation) | 分析员点击后，由编排器组织背景、指标/时间线、响应及报告 | 能支持面向Case分析员工作区的定位；Orchestrator不是额外一轮规划模型 |
| [CHANGELOG](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/CHANGELOG.md)10929行起、[deep模块说明](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/investigator/deep_investigation.py)开头 | 原工具循环虽存在却无生产调用者，后来接deep及typed lake工具，让模型实际查询而非只总结预序列化材料 | 主动取证是明确的后续补齐目标；不能推出“自动一定深、人工一定浅”的效果保证 |
| [graph runner说明](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/graph/runner.py)开头 | 人工full graph与Kafka自动升级共用同一graph，自动子图不重复首次分类 | graph并非自动专属；作者局部也在复用实现，而非要求永久保持人工/自动各一套 |
| [Router模块说明](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/orchestrator/router.py)18行起 | 明说旁置，不改旧investigator | 支持旧实现兼容保留、新能力并置的演进方式；Router又是第三种选择，不是四节点内部隐含步骤 |

官方Cases文档把Forensic写为深入指标、时间线和攻击图路径，但代码中的该Agent没有主动查现场日志或图路径的循环；图背景可以由共享bundle预取提供，AttackPath另有节点。类似地，官方将Orchestrator称为计划/路由，当前默认实现实际是固定LangGraph接线，未调用规划LLM。**官方描述是理解意图的材料，实际能力仍须看调用和证据。**

官方另一篇[“Four agents”](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/apps/docs/docs/architecture/agents.md)说的是Detect/Triage/Hunt/Respond的对外产品分类；它与这里Recon/Forensic/Responder/ReportWriter四节点不是同一组，不应混用Agent数量来解释架构。

## 3. 目的、输入和输出对照

| 维度 | 默认Case四节点 | 自动升级所用graph/deep |
| --- | --- | --- |
| 业务目的（结合官方及源码概括） | 围绕分析员选择的Case，把分散资料整理成调查认识和可交付计划/报告 | 接住未关闭的告警，继续收集/解释证据，形成后续判断和提案，减少再次点击 |
| 起点/范围 | 实际Case、关联告警、分析员摘要；API取资料后形成raw_alert.alerts | canonical Alert和首次分诊state，Fusion incident另存；不自动等于有真实Case/完整关联图 |
| 工作方式 | 固定顺序四个专业任务；共享背景/KB加Recon增强，后续主要分析已有材料 | 外层节点固定，deep内部按工具返回迭代；工具与来源决定能查到什么 |
| 主要结构输出 | recon、forensic、responder三块＋report_md；有时间线/根因假设/范围、完整dry-run响应计划 | findings、verdict/confidence_basis、IOC/TI、proposed_actions、deep trace/depth/缺源/截断和可选AttackPath |
| 响应产物 | containment/eradication/recovery、风险、工作量、recommended_actions，dry_run=true | 多节点形成ProposedAction，不等于相同结构的完整响应计划，也不等于已经审批/执行 |
| 报告 | 专门第四轮模型整理Markdown | 当前graph确定性渲染已有结果，不另外调用人工ReportWriter模型 |
| 调用数 | 正常成功路径4次串行应用层模型调用 | 首次分类已单独完成，deep可早停或多轮；默认cap6并非每次必跑6轮 |
| 完成含义 | 四节点及报告已生成；仍可内容错误 | 图可完整/partial，deep可truncated；首次分诊completed不能抹去后续未完成 |
| 人员参与 | 人选Case并发起，不是每节点都由人校验 | 满足策略自动触发；partial仍需分析员接手，真实响应另守授权/审批 |

两套状态模型不同，输出不能直接互换。人工`root_cause_hypothesis`是待验证解释，不能直接填成confirmed incident；人工dry-run计划也不能直接当执行凭据。graph的trace或高confidence不自动生成可信的完整Case响应计划。

## 4. 人工四Agent设计逐一评价

### Recon：整理线索并做有限增强

**实际输入和动作：** 告警摘要/原结构摘要、共享Bundle和KB进入`recon`模型一次；再合并模型IOC与正则提取，逐IOC增强并合并本地MITRE映射。模型提取先于该轮单项增强，因此增强结果主要给后续Forensic。

**价值：** 将散乱材料整理成后续可消费的IOC/技术/主体候选；有统一结构和工具记录，易查某条线索从哪里来。这里确实存在可以增加外部资料的工具环节。

**限制：** IOC候选和技术映射未必是恶意证据；模型提出主体不等于完成归因。单项增强包装器原value/type与Go ioc_type不匹配已在本批真实复现400，现作一字段本地修正并单独验证，尚未发布；不能拿bulk成功代证其他入口已部署。它也不会根据增强返回再自主问新问题。

### Forensic：形成事件解释，当前并非现场取证引擎

**实际输入和动作：** 原告警、Recon摘要/MITRE、增强摘要及Bundle/KB，再调用`investigation`模型一次，生成时间线、artefacts、根因假设、范围、confidence与摘要。

**价值：** 把“有哪些线索”推进到“可能发生了什么”，将时间线/根因/范围分成可审查字段。它仍重新读取原告警，不是只转述Recon摘要。

**限制：** 没有“发现可疑进程→查进程树→再查网络”的查询回路，也不直接采集内存/磁盘/原始日志。模型生成的时间线和artefacts可能只是解释，需要来源支撑。命名为Forensic不能当已经取得取证原件；共享图/知识背景也不证明本案活动。

### Responder：将判断转换为计划

**实际输入和动作：** Forensic根因/范围/分数及末5条时间线、Recon技术/主体候选、背景/KB，一次`investigation`模型，给出隔离/清除/恢复步骤、风险和工作量，强制dry-run。

**价值：** 任务与调查分析不同，能把结论变成可由分析员评议的行动方案；对后续工单/审批内容有可复用价值。

**限制：** 没有新增事实，也没执行/验证动作。根因或范围错误会传递到建议；输出“隔离主机”不说明已经隔离，也不证明隔离必要。此节点不是独立审查前一个Agent。

### ReportWriter：整理交付，同时也是再次生成

**实际输入和动作：** 前三节点结构结果、原告警事实/时间、时间线和建议内容、增强/覆盖诊断与知识，一次`report`模型生成Markdown并持久保存。

**价值：** 为人组织一份可读、可交接的事件说明，减少人工拼装；报告与上游结构结果可分别查看。

**限制：** 不是纯格式转换，而是又一次自然语言生成，可能新增推断、将假设改成事实、混用业务事件与调查处理时间。报告完整可读、章节齐全、Run completed不证明事实正确。

具体源码及每步提示/模型/工具/审计见[四节点调用表](investigation.md#4-默认人工调查四个agent的每次调用)。

### 对四节点整体的评价

它是**有职责分工的分析流水线**，不是四个独立调查员交叉核验或投票。Forensic/Responder都用`investigation`角色，其他角色也可能解析到同一物理模型；多Agent首先意味着不同任务/提示与状态，不保证不同知识、独立事实或不同错误模式。

优点是任务较明确、产物可检查、错误能定位到阶段、计划与报告有单独价值；不能笼统说多Agent没有意义。反过来，四次串行调用会重复携带背景和前序产物，等待时间相加；每层信息裁剪及语言生成也可能传播/强化同一个未经证实的解释。当前并没有强制让后一个Agent独立找反证再接受前一个结论的机制。

当前人工stream还在报告生成后才做groundedness检查，主要改Forensic的分数/摘要，未重建Responder和Markdown。因此只能说有末尾依据检查，不能说每节点交接前已验真，或报告必然反映最终降分。它是当前实现位置的限制，不是本轮要求立即修复的新任务。

## 5. graph/deep是否更合理、更准确

**对于需要补查的调查，机制更接近“调查”。** 模型能先选工具、看到返回、再决定下一查询，工具结果确实可能增加原告警没有的现场事实；策略为方向，查询由受限schema执行。这是相较单次材料分析的重要能力差异。

但这不是更准的证明。数据不可用、工具占位、时间窗不合适时，多轮只增加尝试而非证据；模型也可能重复查询、错误解释结果或未收束。成功的ATT&CK lookup是知识，extract_iocs是原文提取，都不能替代现场日志。最后确定性报告可少一次模型转述，却不会自动修正state里已有的无据结论。

同样不能说deep一定更便宜。它可早停，也可在后几轮反复携带累积对话/工具返回；固定四节点次数可预测，但内容量与输出上限会变化。当前没有同输入/同数据/同模型的受控对比，不能给出哪套质量更高、快多少或省多少的数字，也不为回答本问题追加模型A/B测试。

## 6. 本项目真实结果证明了什么

| 既有实例 | 已证明 | 尚未证明 / 已有失败 |
| --- | --- | --- |
| [人工R01](../operations/integrity-investigation-r01.md) | 4次真实模型、10167 tokens；KB文本进入四个prompt，事件与Markdown持久/读取成立 | 知识背景写成观察、调查失败混入事件时间、影响范围过强；质量未过。说明分角色及完整报告没有消除事实错误 |
| [自动C2](../operations/integrity-autonomy-r01.md) | 首次分诊后无需点击自动执行graph；deep6次实际回复/6次工具，graph20451 tokens；调用/材料可查 | 4次lake查询不可用，仅ATT&CK和IOC提取成功；到cap、graph partial，错误确认与攻击阶段表述，质量未过 |

两例输入/任务/可用资料/运行版本不同，**不能用10167和20451当性能或成本排名**。人工candidate05投影修正已有部署证据、无新模型质量结论；graph/deep工作区修正尚未部署/真实模型验证；原失败不被源码更新覆盖。

## 7. 对当前二开的建议，尚未实施取舍

1. **告警主线仍以真实证据获取与结果为中心。** 自动未关闭告警应能继续查询、形成有依据的结果/缺口和Markdown；不先用“四个Agent都跑完”代替调查完成条件。
2. **保留四节点中有用的产物价值。** 线索结构、时间线/假设、dry-run计划、报告组织与审计均可复用；是否每条告警都值得额外四轮，需按实际产品输出决定，而不是因为上游已有四Agent就强制全部运行。
3. **触发方式和调查能力分开讨论。** 分析员也可能需要主动补查，自动链也可能需要清楚计划/报告。不能先规定人工只能四节点、自动只能deep；这是一种二开设计判断，不代表现在就统一状态或重写框架。
4. **迁移阶段暂不急删/合并。** 先把原入口、真实采用与输出差异说明白，保持已迁源码和保护，分别标已验/未验；再由所需功能决定最小复用和接缝修改。不要求一条告警串跑两套，也不扩大到复杂可用性/冗余或新模型比较矩阵。

建议后续共同决定的是：需要哪些可查询的现场事实、哪些结构化结论/计划、哪些逐调用审计，以及哪些情况下才值得追加模型生成。Agent数量应是实现选择，而不是告警调查需求本身。
