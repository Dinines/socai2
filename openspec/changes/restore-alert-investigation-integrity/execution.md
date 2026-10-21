# 迁移实施记录

## 2026-10-21支撑能力先行：路线与讨论记录（最新，仅规划）

用户纠正顺序并明确本轮首先完成整个实施路线、记录关键点。已将[总计划](../../../docs/operations/completion-plan.md)重排为UEBA → 威胁情报/IOC → 20上一版既有知识库 → Fusion → 分诊 → 调查/攻击路径 → Markdown结果交付；沿用B1—B6及原任务，不新增产品树。共享能力基础属性表与讨论纪要保存在[模块说明](../../../docs/operations/module-review-plan.md)，项目入口/架构/AGENTS/OpenSpec上下文同步。

本次确定：UEBA首先解释针对哪些实体启用、基线时间/样本/阈值配置、输入输出和偏离算法；IOC先固定查询命中/未命中，数据量与覆盖率暂不考虑；知识库先复用20上一版已采集资料，实际库表/索引待只读确认，历史经验相关后看。空结果为可接受合同，但来源未配置、不可用或失败不能伪装成查无匹配；UEBA不可评分不等于正常。

只读核源码确认UEBA目前无按tenant/实体名单启用配置，normalized输入按user→device→ip固定择一；window_days仅初始化时间标签，无超期样本淘汰。机制边界已记原问题表，后续明确配置需求再提出最小适配；本轮未改算法或业务源码、数据、运行配置，无新测试/模型/消息/部署。原主链/质量失败、unknown及workerOFF保持，产品仍5/15，不归档未完成change。

本轮规划结束独审：未参与文档实现的api_auth_review给出ACCEPT，确认顺序、UEBA配置重点、IOC数据规模暂缓及KB历史经验后看均符合用户说明，无提前实施或新框架；按建议澄清“20上前一版”资料措辞。OpenSpec strict通过，11份本次文档引用检查无缺失，UEBA工作卡已置于Fusion前；仅为文档/结构校验，不是业务验收。

## 前一版二开逐模块方案（历史设计，顺序以上节为准）

用户要求以独立模块推进，先Fusion职责/输入输出/依赖；必要独立依赖先梳理再交回主模块，调查说明输入、所查服务、执行步骤及逐步审计。已结合固定源码及需求形成[模块设计](../../../docs/operations/module-review-plan.md)：Fusion边界与依赖初稿、UEBA输入/配置/启动/两种输出交接、调查步骤/审计表、标书差距及最少功能验证方式。总计划/架构/项目上下文同步，不新增第二套产品任务树。

静态新发现登记到原问题表：UEBA HTTP基线与Fusion Kafka异常是两条合同，promotion执行门、自动Case/AttackPath身份/图材料及历史查询窗口仍需模块内评估。没有修改业务源码/运行配置、启动服务、发送消息、调用模型或做功能测试；尚未确定的新行为不新增spec或勾任务，当前仍5/15。既有主链已通、质量失败、unknown和workerOFF保持；后续二开按具体模块合同再实施。

文档结束独审由未参与文档实现的api_auth_review完成：主设计ACCEPT，无业务改测阻塞；按审查修正导航旧“尚未实测”与架构旧“正在修复”的现时表述，明确限定实证/质量失败及本地修正未部署状态。`openspec validate restore-alert-investigation-integrity --strict --no-interactive`通过；新文档及本次顶部引用10份文档本地链接检查无缺失。上述是文档/结构校验，不是新功能或模型验收；未归档未完成change。

## 当前优先口径：第一步主链接通已有实证

用户最新要求先走通正式告警输入到调查结果/报告：只补缺源码/直接依赖/环境或接口接线导致无法执行、基本结果取不回的环节。其他入口/全部分支、质量修完、常驻准入及复杂可用/冗余校验不作为前置。复用B4 case02已实测的正式输入→Fusion/分诊→原worker自动graph/deep/工具/MITRE→MD/HTML与关联持久工件读取，第一步已有走通证据；原partial和质量失败保持，不追认质量。

已通知全部worker停止质量/用量补修、重复组合/全量hash水位计数冻结、模型矩阵、多轮审计及新控制脚本。已发出的最后同组仅读取结果157passed/4.02秒；新源码未终审/未部署，155及此前记录保留。未再新建批次树或change，不为回退已修代码另做工作。现有租户/预算/unknown及高风险授权边界不变，workerOFF。整体change余项留后续，当前第一步不以15项全部勾选为前置，复用既有独审技术证据收尾。下文阶段修复/质量门及候选动作均为当时记录。


2026-10-21用户明确开始实施，允许并行worker。沿用本change原任务与B1—B6，不新建重复实施树。

## 本轮并行范围

- fusion_review：B1/I3，统一HTTP/Kafka canonical身份、首次材料、持久确认及tenant合同，保留FusedAlert响应和C01交付保护。直接验证两入口先后顺序和跨tenant写前拒绝。
- api_auth_review：B2/I1，默认Case调查身份与临时baseline解耦，必要结果/报告入口的Case/Run归属；不简单关闭baseline或连带启用厂商执行。直接验证同/跨tenant。
- triage_review：B2/I4及B3，沿既有上下文链补实际token接缝，区分缺源/失败/合法空结果；复用已有KB读取与来源封装接默认四节点，同Run读取一次并记录实际材料、引用和报告关系，只补直接影响的测试。
- root：运行/测试环境、I2正常graph用量及首次分诊读取组合、跨批接线、按实际成果更新回执与完成任务。真实验证使用受控tenant与新输入，旧unknown/积压/回执保持。

并行修改按文件分工，部署由root串行执行。完成后安排未参与对应实现者交叉审计，审计阻塞在本批修复。playbook/反馈原样保留、额外改测和可用性专项后置；只做本次功能正确性必要验证，不默认重跑全仓。

## candidate02阶段快照（历史）

B1已限定完成：119项直接测试及10次真实HTTP验两入口顺序、首次材料和tenant，Fusion一次更新至c52b9aac；源码/部署/运行结束独审通过，任务2.4完成，当前5/15，见[回执](../../../docs/operations/integrity-b1.md)。

B2身份/上下文和B3知识消费已完成直接测试与独审。I2初轮隔离PG79缺普通SQL状态断言，后由PG日志发现死CASE错误；初轮结果与错误保留，其充分性已撤销。最小修正后candidate02去重组合232项Agents、25项API共257项通过，独审确认状态/iterations/error实际写入。

API已定向部署至1be37c38、Agents至9f74c4a8，Fusion c52保持；自动worker仍OFF。B2/B3/I2的真实人工调查、知识材料/实际引用、usage和报告验证尚待，部署及直接测试不计作整链完成，相关跨批任务暂不勾选。官方声明与源码差距见[功能对照](../../../docs/operations/alert-function-alignment.md)，结构及扩展点见[当前架构](../../../docs/architecture/alert-processing.md)。

首次只读SSH连接限制及超时是此前环境接入过程，保留原操作日志；不据此改写产品通过，也不覆盖上述后续实际部署。

## B2/B6 正常报告修复（实施中）

真实新Run `7bc46722`已完成四节点/8062 tokens技术链，报告质量失败；原输出、0个KB marker及失败结论保留，不重调。triage_review负责四个默认调查system prompt及lock、ReportWriter材料传递与实际截断处理和必要直接测试；不改schema、triage v5、其他18个prompt或B4/B5编排文件。先记录本备注，再做最小源码修复；维持有界completion，截断不重发模型，缺证保持未知、动作未执行。真实新输入/部署由root另行推进，最终由未参与实现者独审；不提前勾选整链任务。

root随后授权追加Forensic单文件：修仅error增强被当作有证据的正常语义缺陷，保留错误详情，补零primary/全失败回到原inconclusive分支的直接测试；知识定义不冒充事件事实。工具/增强服务、其他编排与旧Run仍保持。

当时运行completion配置为1024，源码默认仍为2048；旧报告尾文截断，但旧事件未保存finish_reason，不能追称已观察到length。新代码只按实际返回的length处理；本轮直接测试区分源码默认与环境上限，后续由root做有界配置适配，不设无限上限。

本批实现已冻结待独审：4个运行文件（prompt registry/lock、ReportWriter、Forensic）及1个直接测试文件。最终56项断网真实模块测试通过（2.12秒），包含现有知识四节点/来源引用、LLMOps、报告HTML、groundedness、audit helpers及新增正常报告边界；真实SDK客户端经内存HTTP替身分别验证1024配置与2048默认均只调用一次并传递length、原文及usage。首轮55项通过原件保留，第二轮仅增加1024/默认2048区分及原usage断言。测试不等于真实模型内容质量通过；0真实模型/业务写/部署，原Run质量失败保持。冻结清单见本地受控 `.local/aisoc21/completion-integrity-20261021/report-integrity-test-result.json`，21私有 `report-integrity-test/attempt01`、`attempt02`保留原回执，后续独审与新输入由root推进。

## B3 引用格式接缝（实施中）

新Run36bd18e0的实际报告明确使用裸KB1，原parser只识别[KB1]，与实际prompt“marker(KB1)”不一致。root仅扩大完整独立marker识别，保括号格式、未知引用及identifier边界；用捕获原句纯函数验证，不重调模型、不改旧Run或旧0个“已解析引用”事实。后续仅单文件发布，先直接验证与未参与者独审。模型以知识推测本案意图等质量缺陷另保留，不以格式修复追认完整质量。

## candidate04引用与原只读身份接入

2026-10-21，[限定回执](../../../docs/operations/integrity-citations-tools.md)：单parser文件差异32项直接测试，保旧R01的实际裸标记/0parsed记录不改写。原七权限API服务身份接入，无新工具/API；部署前后独审及六HTTP通过。API1be、Agentsc311健康，仅两服务定向替换；773来源匹配、29层、旧env/七RO/60秒/2048/关闭开关保持，0模型/新业务消息。新C五读者11HTTP通过，尚无C告警/模型；B4下一有界业务，不因源码或认证通过勾完整自治任务。

## 默认调查R01证据与最小语义修正

[R01](../../../docs/operations/integrity-investigation-r01.md)四次真实调用10167 tokens及MD/HTML/PDF200技术成立，三内容缺陷不改写。两默认节点最小调整hypothesis/observed-scope/unknown及调查处理时间的呈现，保原模型response；明确naive审计时间zone未记录，不补Z或借源事件时区。最终24项直接测试/独审通过，首23与后续修正分别留证；0模型/PG/消息、未部署，待B4当前c311绑定结束后再定向。该修正不等同未来模型内容质量通过。

## B4有限算子预备与首条受理（未启模型）

C上下文11项与common身份六项HTTP通过后，控制算子暴露目录挂载、标准库operator同名、Kafka空metadata缓存三个假设错误，均未到业务；原STOP/脚本/日志保留，明确根审接续且不重冻spec/IDs/time。metadata改公开Admin先查存在后取分区，实际c311/188源码/TLS/PG/Cpolicy/预算及两旧组只读核对通过，未改产品worker或阈值。

随后case01仅一次alert-ingress 202：source51d8a02c-e601-4459-8a74-bbbd63e2b603→canonical756fca9f-cf30-57e6-82b3-a14c4ab59602，raw p0/35；API实证初态new（原schema不暴露resolved_at，不将缺键当实测null）。原Fusion唯一信封fused p2/38，外id、alert_row_id、内alert.id都是canonical，内source_alert_id保原source-v1身份；算子误把内id当source而止于观察，未启worker/模型或重POST。该错误属于验收算子，固定源码与实际消息一致；保留原失败后仅纠观察合同。不得将已受理写成自动关闭通过。

case01首次原worker消费/原API回查及独审通过：BTP0.95、threshold0.85 env、shadowfalse、auto_closedtrue，APInew→resolved/BTP/.95，最终PGresolved_at非空；初始PG该时间字段未单独取证，原API缺键不等于null。1真实回复2174tokens/1unpriced，20000预留单位不是usage，C预约responded；旧A/B预算/两old组commit保持。根审仅批准case02同冻结输入继续，不等同完整自治准入或整批完成。


## B4第二条失败与正常结果修复

case02源4e169979→canonical17254632→Run e3d019ae经真实入口/原worker自动升级调查，无需人工再点；首分诊NR0.85/auto_closedfalse保持，告警triaged、消费前后PG resolved_at均null。七回复22568 tokens（首次2117+graph六次20451）、六工具及11工件的PG/API内容/hash匹配。缺实际lake/厂商资料明确availableFalse/unknown，MITRE查询实际进入后续模型ToolMessage。

完整验收失败：deep六轮仍请求工具，graph20451超过冻结20000 token边界，结果partial；原版确定性risk prior错误派生confirmed_incident/.94，附T1110映射被写成已观察攻击阶段/单阶段事实，末ToolMessage被当narrative；deep摘要还遗漏原raw_event/username字段。保留此次失败和既定边界，不抬限额、不重调旧输入。常驻仍workerOFF/review_only。两例合计8回复24742 tokens；C两预约40000预留单位、observed4291只计首次分诊，不能当整Run usage。

本批仅修实际正常结果问题：fusion_review负责已有investigation/scoring/tool_loop/deep/runner的证据语义、原始材料投影及实际用量边界，保持原编排和cap；triage_review负责关闭兜底finding在NR=阈值时的错误比较文案，不改关闭决策。只补直接测试，0真实模型/旧输入重放，由未参与实现者独审。candidate05仅修默认调查两个报告节点，不声称覆盖本次graph缺陷；独立预构建已过，B4有限窗口退出封存后再定向部署。


## candidate05定向部署与临时身份收尾

C2质量失败STOP后已确认两个有限窗口退出、0活动有限容器。candidate05已预构建4ccf/完整773来源和部署脚本独审通过，root一次定向替换Agents；健康、全部env/七RO/60秒/2048/workerOFF及其余托管容器ID保持，仍29层。只有两个默认报告文件变化，不包含未部署C2修复；0新模型/消息/业务写，详见[回执](../../../docs/operations/integrity-report-semantics.md)。运行后独审另记，不外推未来内容质量。

八枚本批临时key（A/B两操作、C六）已按独审脚本一次停用，逐枚真实401；事务核所有其他api_key行逐对象保持，旧十reader和永久七权限服务身份不在目标。旧三unknown/原积压、失败输入/判据和工件保持；不重复旧输入或放宽限额。


部署后candidate05独立只读审计accepted：实际773运行输入、远端source及完整父层/两COPY匹配M05；全部env/7RO/60秒、关闭开关/2048/common身份及其他托管容器ID保持。净化记录见[运行回执](../../../docs/handoff/integrity-candidate05-runtime.json)，原始SHA8f8e72b5a3620d1d2fef6dd838d61723ec32279943d1215d0e51cc39a3f931f9；0新增HTTP/模型/消息/业务写，不外推内容质量。


## 2026-10-21 full配套与Markdown范围

已按用户指示整体补迁enrichment/threatintel/ueba共101固定原件和图schema资源，沿原依赖最小接线。历史事件、参数化调查补查、UEBA实际消费/Agents读取、IOC增强、OS索引/查询及TI/API代理已基本运行验证；原缺失后端不补，0模型/厂商/Feed调用。报告当前只要求Markdown，复用原生成/持久/读取证据，PDF/HTML额外交付不作前置。严格校验通过；本批实录与最后独审见docs/operations/full-support-migration.md/json。沿用任务2.1/3.1/4.1的本批部分，不勾选未完成的完整change任务、不归档，整体迁移仍未完成。

本批结束：未参与实现者api_auth_review最终限定ACCEPT，无新增功能接通阻塞；仅更新本批回执，未额外验证/归档或勾选总change未完成项。
