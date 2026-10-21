# 当前进度

更新：2026-10-21。

**二开路线已重排（最新，仅规划）：** 用户明确先规划/记录，再按UEBA → 威胁情报/IOC → 20上一版既有知识库 → Fusion → 分诊 → 调查/攻击路径 → Markdown交付推进。[总计划](docs/operations/completion-plan.md)已记录整条顺序，[模块说明](docs/operations/module-review-plan.md)保存共享能力基础属性表和本次讨论纪要：UEBA重点实体启用、基线时间/样本配置、输入输出及偏离机制；IOC数据量/覆盖率暂缓；知识库复用既有资料，历史经验后看。原码UEBA没有按实体名单启用配置，30天参数仅初始化时间标签、不是淘汰过期样本的滚动窗口，作为首模块待讨论项记录；20实际资料/索引待只读确认。本轮未修业务代码、运行配置或做测试/模型/部署，不勾新产品完成项；主链已通与标书完整满足仍分别判定。

**报告交付最新口径：** 用户确认当前只需Markdown能生成、持久保存并按Case/Run读取；PDF暂缓，HTML额外交付也不作本轮前置。复用已有Markdown主链证据，不重跑报告模型或增加格式专项；已有PDF源码/依赖/历史结果保留。

**full配套按原码迁移（当前）：** 用户明确历史补查、Attack Path、UEBA、事件检索、IOC增强及OpenSearch需要，复用21依赖，保证原功能基本可运行。新增原版101服务文件+图schema资源，按现有OpenSpec做必要认证/字段/配置接线。原Fusion→ClickHouse→lake SQL/调查补查已实证：同一合成事件A1行/B0行；原APOC依赖补齐后AttackPath200（PG2节点/1关系回退），首两503/跨租户404保持。UEBA原122项+7项直接测试通过，原迁移head0004、原HTTP及Kafka基线与常驻Agents实际读取通过，只有1样本不作画像/异常质量通过；enrichment已健康/HTTP200但无provider，不将零分解释安全。OpenSearch原Store合成IOC写1/搜1/精确匹配1及TI原HTTP200通过；TI airgap/Feed0、Qdrant浏览200空集合，API原代理200/source=qdrant/degraded=false已接通；基本实测及未参与实现者唯一结束独审accept，无本批新增功能阻塞，具体以[本批回执](docs/operations/full-support-migration.md)为准。0新模型/厂商调用，未启全局worker或真实响应，整体迁移未完成；下列只读分析为较早状态。


**20页面/full需求只读对照：** 已按六张Case截图核固定源码、20已有Case/Run和当前部署；旧Run结构GET404而账本/MD保持，新Run三块结构GET200，原版冷恢复/页面接缝与full无关。截图告警精确对应golden pipeline合成输入。full六个可选组件、Attack Path/Chain差异及Tasks/Notes/Resolution等缺口已写[功能对照](docs/operations/alert-function-alignment.md#20的case页面与full需求2026-10-21只读分析)。本次未新增模型、测试、运行代码/配置或部署，未扩大迁移职责；是否选实体图/事件湖及完整工作台留讨论。

**最新口径／第一步主链已走通：** 当前只要求正式告警输入→Fusion/持久化/分诊→自动实际执行调查→已配置工具/知识调用→基本结果/报告/关联持久记录可取得。[已有B4 case02](docs/operations/integrity-autonomy-r01.md)已满足该接通口径：source4e169979→Alert17254632→Run e3d019ae，实际执行graph/deep、六工具及MITRE查询，MD/HTML与11项工件经原API取得；不需人工再点调查。复用该证据，不补其他入口或重跑模型。该次partial/质量失败仍原样保留，第一步接通不等于完整质量、常驻准入或整体迁移完成；常驻worker仍OFF。

**执行已收敛：** 算法/模型、报告、deep截断/用量及恢复问题迁移后评估，不再以修完或质量复验为第一步前置。停止重复组合测试、全量hash/水位/表计数/冻结、逐入口模型矩阵、多轮审计及自造控制脚本；复杂可用/冗余专项后置。已有代码修复不回退：graph最后一轮在指示到达前已发出，实录157项通过（4.02秒）；关闭文案39项及旧153/155等记录保留，最新源码未完成最终独审、未部署、不作真实质量通过。运行仍candidate05，八临时key已撤，旧十reader/服务身份/unknown/积压保护保持。下列较早“继续修复/质量硬门”等仅保留过程事实，当前以本条和AGENTS顶部口径为准。

**当前运行更新（优先于下列过程快照）：** candidate03组合358项Agents+25项API=383项通过并独审，B4/B5结果/用量/交付、报告及技能pin修复和原生PDF依赖已部署；新人工Run四模型10167 tokens，25事件/一MD，MD/HTML/PDF200。报告仍有意图、范围及时间表述超证据的问题，不作完整质量通过。旧Run保持并冷回查，原PDF缺库现可读取。candidate04仅改一处KB引用格式解析（32项直接测试）并配置原七权限只读服务身份，已定向更新API1be/Agentsc311健康，部署后独审及六项HTTP通过；[原28+integrity共29层](deploy/aisoc21/README.md)，workerOFF；[引用/工具身份回执](docs/operations/integrity-citations-tools.md)。candidate05默认两个报告节点假设/范围/处理时间投影24项直接测试及独审通过，已定向替换Agents为4ccf3a6d（全部env/7RO/60秒保持），0新模型/消息/业务写，部署后773来源/运行配置独审通过；C2图/deep修复未部署。新C六短期key当时创建、五来源及拒绝边界11项HTTP通过，C第一条经原worker实测BTP0.95/原0.85阈值自动关闭、APInew→resolved且最终PG关闭时间非空，1真实回复2174tokens；分类/理由/关闭独审通过，C2已自动调用调查/六个工具，7回复22568 tokens；首分诊NR保留且告警未关闭，但deep六步截断、graph20451超过20000边界，报告把MITRE映射和风险prior当攻击/确认事实，完整验收失败并停止后续输入。两例合计8回复24742 tokens，保留原失败、不重调；最小源码修复进行中，八枚本批短期key已停用/逐枚401；旧十reader/永久只读身份/三unknown/积压保持。

**B1限定完成、B2/B3候选已部署：** [Fusion入口回执](docs/operations/integrity-b1.md)：119项直接测试、10次真实HTTP，两条新source-v1输入走通HTTP→Kafka及Kafka→HTTP，首次结果不变，跨tenant403/无效凭据401；Fusion一次更新至c52b9aac，源码/部署/结束独审通过，restore任务2.4完成，当前5/15。B2权限84、上下文44及B3组合94已做直接验证/独审；I2初轮隔离PG79漏普通SQL状态断言，后由PG错误日志发现死CASE问题，撤销其作为充分验收的结论，原结果与错误保留。修正后candidate02去重组合232项Agents+25项API=257项通过，独审核状态/iterations/error实际写入；API已定向部署至1be37c38、Agents至9f74c4a8，Fusion c52保持，worker OFF。真实人工调查、知识采用及报告验收尚待，不计作整链完成；下方前期规划与“未实施”说明保留为当时阶段记录，不覆盖本条。

**首轮人工实测与后续：** [B2/B3回执](docs/operations/integrity-b2b3.md)：新Case/Run四模型8062 tokens、25事件/一MD工件、KB确切块进入四prompt但0引用，七拒读404；技术材料/租户/usage成立，报告因测试输入污染、失败增强误当证据及截断而质量未过，PDF缺原生库500。原Run保留不重调。当前B4源码151项、B5最终78项、报告修复56项直接验证及各自独审通过，组合/新业务尚待；PDF依赖候选仅隔离渲染通过，未运行发布。B1两操作key已撤401，后续两操作key及旧十reader保持，workerOFF。

**工作目的明确：** ①迁移告警及后续处理流程，确保功能/结果符合预期；②过程中理解源码并对照固定版本官方文档，识别已实现、未接通和声明未实现的功能；③形成架构/功能/扩展点梳理便于二开。官方对照及架构产物随实际批次更新，不扩大为全平台重构或无边界缺陷修复。

**开始实施：** 用户已授权按总计划执行并允许并行worker。当前并行处理B1融合入口合同、B2默认调查身份和上下文，root统筹直接测试、运行接线与跨批组合；每批由未参与实现者独审。实施状态以本条及后续回执为准，下文“仅规划”保留历史；当前尚未新增完成任务或启用自治。

**自动调查讨论勘误：** 用户询问的是原有代码设计，上一轮误记为新增规则触发需求，已撤回新增合同/优先级/专项验证要求。原版已有playbook事件/severity/tags触发及investigate步骤，另有worker分诊未关闭后升级；按原设计保留，不新增一套规则机制。仅文档纠正，无产品、部署、模型或消息操作，worker仍OFF，restore任务仍4/15。

**后续总规划：** [主执行表](docs/operations/completion-plan.md)已按B1告警、B2默认人工调查、B3知识、B4自动分诊/关闭/自动调查、B5其他调查/交付、B6整体验收组织，并映射现有六阶段及restore任务；文档严格校验与未参与实现者独审通过。自动升级后实际自动取证/分析和交付结果，无需人工再点；第一实施项B1，B2独立部分可并行准备。本轮仅文档规划，无产品或运行变更，原4/15及11项未实施不变。

**最新范围/当前下一项：** 用户确认完整告警/调查及自动关闭、自动升级；playbook/反馈一体保留不额外改测，可用性专项后置。[完整性评估与修复规划](openspec/changes/restore-alert-investigation-integrity/assessment.md)已严格校验及独审通过：1578原件无缺失，当前功能存在临时限制及阶段/usage、跨入口、上下文组合缺口；4项评估任务完成、11项修复/交付任务未完成，未改运行。旧R02[暂缓](openspec/changes/admit-review-only-triage-worker/status.md)、0/17及五文件/hash保持，不作为功能前置。下文旧“下一R02”保留历史，不变更运行OFF或旧质量失败事实。

**目标：完整迁移告警及调查服务端功能，保证功能完整、结果正确。** 包含告警处理、自动分诊/关闭/升级、人工调查、工具/知识消费和报告交付。所有一体模块可原样整体迁入，不额外修改或测试；playbook/反馈专项、冗余设计及服务可用性相关测试/修复登记后置。验证仅补当前功能变化所需部分，前端/采集/原始检测/独立展示推送不在本轮职责。

## 已完成

- 2026-10-21再次同步目标与原则：优先完整迁移告警/调查并保证结果正确；所有一体模块可原样整体迁入，不额外修改或测试；冗余设计和服务可用性相关测试/修复登记后置。已收敛当前修复计划，I2正常graph用量问题与特殊故障恢复接续分开，未增加通用阶段/恢复框架；纯文档严格校验与独审通过，无运行变更或业务/可用性测试。

- 2026-10-21按用户要求接入[OpenSpec实施规范](openspec/README.md)：项目配置、变更流程及入口已建立，严格校验与未参与实现者结束审计通过；C03-R02已建[待执行change](openspec/changes/admit-review-only-triage-worker/proposal.md)，17项任务全部未勾选。只接入实施规范，不改变运行源码、部署、旧回执或完成状态；不导入旧SOCAI任务。

- 项目入口、[范围](docs/operations/alert-processing-scope.md)、[六阶段路线](docs/operations/service-roadmap.md)及[批次计划](docs/operations/dependency-migration-plan.md)已按同一目标对齐；旧规划与过程记录保留为历史。
- 1A依赖参考快照：90个原件完成本地来源/Git blob/hash/权限核对，13个Python服务main/all版本导出，上游导出自测26项通过。快照包含范围外文件，不是全部安装清单。
- 20/21只读盘点：20基础Compose/官方应用revision/overlay对应；21共30容器（22运行、8退出）、18卷，与旧服务关闭回执比较无变化。证据见[初始化回执](docs/operations/initialization.md)。
- 需求原件、既有分析、20适配、来源清单及受控配置位置已保留。私有凭据仅在Git忽略目录，不写入公开文档。
- 迁移规划已细化：第一阶段按1B→1C→1F→1D→1E→1G执行，每批含源码落点、输入/验收/恢复；后续2A—4D及冻结交付也已分批。计划来源清单含2个initdb脚本、134份SQL、所选Python服务上下文和直接测试候选；其中1B的137个原件已迁入，SQL已实执行；API/Fusion已执行1F；Agents/Actions已执行1G，其余按需适配仍为规划。新增静态阻塞见[已知问题](docs/operations/known-issues.md)。
- 1B已复用21共享PG16.15/Redis7.4.11：新建aisoc库/两角色，134份SQL全部执行成功；绑定tenant读写、越权写/DDL拒绝通过。Redis专用账号/逻辑库与ACL持久化完成，单服务重建后账号和测试key恢复，原镜像/卷保留；其余29容器元数据未变。详见[1B回执](docs/operations/1b-shared-services.md)。
- 1C已复用21 Kafka7.5.0 KRaft：项目raw/fused/Agents DLQ topic已准备；原锁aiokafka0.10.0经独立容器验证消息offset/hash、手动提交及单broker重启后的续读/新写/全量回放。53个旧用户topic起止offset不变，仅清理本批smoke topic/group。详见[1C回执](docs/operations/1c-shared-kafka.md)。

- 1F已迁入API/Fusion共987个原版输入/测试（含已有134 SQL），3个原文件作最小接入/启动适配；Python3.11.17源码镜像已部署到21 loopback18000/18003。真实HTTP→项目Kafka SSL→Fusion→PG TLS→API主链、权限/跨租户拒绝、重投和坏schema持久DLQ取证完成；70项相关测试通过。见[1F回执](docs/operations/1f-alert-chain.md)。

- 1D已复用21 Qdrant1.7.0，实际进程nofile65536；21独立Ollama0.40.6/qwen3-embedding:0.6b已启动，16核CPU/32GiB内存。真实3条1024维向量写读/查询及Qdrant重建恢复通过，测试集合已清理；其余31已有容器与18卷名保持。见[1D回执](docs/operations/1d-vector-embedding.md)。

- 1E已在21部署固定LiteLLM1.106.0独立网关（loopback14000）：五角色分别真实调用43并通过JSON结构校验，共463输入/153输出/616 tokens，费用unknown。其余33已有容器与18卷名保持；错误key原版返回400的限制及首次探针失败保留。见[1E回执](docs/operations/1e-model-gateway.md)。

- 1G已迁入Agents/Actions共591原件，6个最小差异及8个新增服务文件；21源码镜像、人工HTTP→四模型节点→18事件/报告→重启后API回查已验，Actions仅dry-run，123项直接测试通过。发现并修复同响应usage重复累计和错误工具结果被记成功；修复Run实际/账本均5718 tokens、unpriced4，首次错误Run原样保留。34个已有容器/18卷保持，测试key已停用。见[1G回执](docs/operations/1g-service-baseline.md)。
- 知识复用已只读核429文件/约5GB、29份原始来源摘要及402,744行结构记录；本地4B模型摘要已核（声明2560维），允许20/21分担模型负载。已形成[复用计划](docs/operations/knowledge-data-reuse-plan.md)，尚未导入、比较检索或切换模型。

- 2A已完成8次原版投递核对，复现不同发生被折叠及缓存丢失重投虚增关联数。后者仅改1个原文件修复，25项测试及独立实体3次投递复验通过；原5条PG材料保持，只重建Fusion，其余35容器/18卷保持，测试key已停用。当时发生记录合同仍待明确；后续完成见下一条，原始结果见[回执](docs/operations/2a-dedup-correlation.md)。

- 2A-01已按独立上游告警合同实施source-v1，保留旧Kafka及可匹配旧HTTP身份。7个源码/测试文件差异、无DDL，95项相关测试及12条broker输入/41项HTTP检查通过；新增7行分别保留材料与持久关联，重启后可查，旧12行不可变材料不变。仅API/Fusion更新，其余34容器/18卷保持，3测试key停用，Kafka lag0。**2A限定验收通过**，见[回执](docs/operations/2a-source-identity.md)。

- 2B-01已复现并修复RBA缓存失效重投重复加分：真实链修复前30→近60分/计数1→2，修复后独立样例始终30分/1次。40项相关测试、真实Redis32次同告警/64条不同告警并发及超50条展示上限重投通过。只更新/重启Fusion，19条旧材料、其他35容器/18卷、134迁移保持，2测试key停用，模型调用不增。Fusion ML状态接口仍因租户认证未配置返回503，处理规则在当时未验（后续见2B-02），见[风险回执](docs/operations/2b-risk-idempotence.md)。

- 2B-02已完成稳定规则内容指纹/实际采用状态、保存失败缓存污染修复；83项相关测试通过。真实API→PG→生产applier/worker抑制方法验证v1/v2、30秒缓存、恢复、租户/权限与依赖失败，25项HTTP检查通过；只更新/重启API/Agents，22条旧材料/其他34容器/18卷/134迁移保持，3key停用，模型调用不增。自动worker仍关闭、抑制摘要尚无持久ledger，见[规则回执](docs/operations/2b-policy-versions.md)。

- 2C-01已接Fusion本地IOC查询及冻结结果：复用旧SOCAI一条有来源/日期的历史指标，真实6投递/5新行验证命中、无匹配、tenant、过期/停用及重投，21项HTTP检查、62项测试通过。历史参考弱证据不增权；独立SDK故障/恢复与整服务故障分开。仅更新/重启API/Fusion，25旧材料/其他34容器/18卷/134迁移保持，2key及2标记IOC停用。见[IOC回执](docs/operations/2c-ioc-consumption.md)。

- 2C-02已新增认证只读processing-context接口：合成材料在现有PG表中，资产/权限/开放漏洞实际算706，改A材料后当前视图435，另一tenant280，原告警medium/priority50不改。显式关联、无匹配、已修复/未来排除、真实PG SAVEPOINT故障恢复及API重启回查通过，30项测试/38项HTTP检查；只更新API，30旧材料/其他35容器/18卷/134迁移保持，3key停用。不是实际CMDB/HR/扫描器同步或普通日志消费，见[回执](docs/operations/2c-processing-context.md)。

- 2C-03已只读核21/20事件与UEBA来源：21 ClickHouse无业务表、旧UEBA六表精确0行；20 UEBA为空，事件topic仅一条未定性消息且无可用ClickHouse。50项原工具合同测试、12项HTTP检查/3项停用复核及3次生产Agents方法调用完成，缺源明确available=false；生产Agents还缺API凭据。未变服务/配置/旧36告警/134迁移，3key停用；首次快照断言失败保留，单独复核一致。真实事件/UEBA消费仍未通过，见[回执](docs/operations/2c-event-ueba-sources.md)。

- 3A-01已补规则抑制持久回执与DLQ/提交保护：现有账本保存policy_decision，原告警不改、不生成模型verdict；83项相关测试、真实PG事务失败/恢复及SSL Kafka实际worker验证offset1→1→2→3、恢复不重发/确认DLQ后提交。只更新/重启Agents，旧36告警/2Run/36事件、其他35容器/18卷/134迁移保持，3key停用；3份新回执含1份probe-only恢复记录，常驻worker仍关闭，见[回执](docs/operations/3a-policy-suppression.md)。

- 3A-02已完成有界真实模型/消息/账本/API验证：首轮标签污染导致材料不足被判FP，原Run保留；另3条盲测依次TP/BTP/needs_review，独立模型失败回退needs_review。6次成功回复usage/Run/成本行均7406 tokens、unpriced6，费用unknown；46项原测试/66项HTTP检查通过。显式group起点0、最终4/3及同group重启无新调用；未改运行源码/镜像/常驻配置或重启服务，旧38告警/5Run/39事件等材料、36容器/18卷/134迁移保持，3key停用。缺失risk_score被显示0.0、五类context401及技术引用错配尚未修复，完整质量未过，见[回执](docs/operations/3a-model-triage.md)。

- 3A-03已修复缺失风险分被当零分：实际ingress/Kafka/Fusion/PG/API及worker/prompt中缺失/null保持未知、0和0.8原值保留，四条独立告警关联同一事件。184项相关测试/33项HTTP检查、一次真实模型needs_review及1345 tokens账本核对、三服务重启回查通过；旧45告警及既有账本、其他33容器/18卷/134迁移保持，3key停用。未重做数值评分，五类context401及完整质量仍未过，见[回执](docs/operations/3a-risk-score.md)。

- 3A-04已接每租户组织记忆读取与明确失败状态：194项测试/46项显式HTTP检查，真实PG/API有效/过期/缓存/认证失败及恢复通过；一次真实模型消费A语句仍needs_review，1523 tokens与账本一致。新读取回执/工件同事务，真实PG工件故障回滚及同Run恢复通过（独立probe-only Run）；API/Agents重启后回查及常驻身份读取通过。旧49告警/既有账本、其他34容器/18卷/134迁移保持；3操作key停用，2枚A/B只读reader key保留30天。其他四类context401及完整质量未过，见[回执](docs/operations/3a-org-memory.md)。

- 3A-05技能读取认证/选择来源及事务工件已限定验收：347项测试（API142、Agents205）、48项最终HTTP检查；一次真实Fusion→worker→43模型采用skill-a-rule@v2，needs_review/自报0.95，1572/105/1677 tokens与账本一致、费用unknown。事后合成头v3与原v2工件分离，真实PG故障/同Run恢复及API/Agents重启回查通过；旧50告警/既有账本、其他34容器/18卷/134迁移保持。3操作key停用，2枚独立settings:read reader保留30天，原组织记忆身份保持；失败尝试保留，见[回执](docs/operations/3a-tenant-skill.md)。4条failed/probe-only FK占位不作真实编写/回测/激活成绩。

- 3A-06 KB认证读取、保守cutoff、确切采用文本/引用及事务工件已限定验收：236项测试（API38、Agents198），真实API/PG全文检索、租户与scope拒绝、缓存失败/恢复及重启回查通过。一次真实模型prompt含KB1，返回needs_review/自报0.95，1955/140/2095 tokens与账本一致、费用unknown；实际prompt7861字符、未截断，但模型未引用KB标记，引用质量未过。8717/8105两次模型前预算预检失败保留，仅压缩本批合成资料及等义inline note后从检查点恢复，没有重发告警或追加模型。旧51告警/既有账本、其他34容器/18卷/134迁移保持；新增1告警、1真实模型Run与1独立probe-only Run、6条合成KB行。3操作key停用，2枚knowledge_base:read reader保留30天，原组织记忆/技能4key保持；见[回执](docs/operations/3a-kb-read.md)。

- 3A-07近期分析员处置认证读取/采用来源及事务工件已限定验收：最终396项测试（API91、Agents305）、60项显式HTTP检查，真实API/PG规则优先与tenant隔离、created cutoff、缓存撤销/失败恢复及重启回查通过。一次真实模型prompt7355字符含三条个人意见，needs_review/自报0.65，1779/130/1909 tokens与账本一致、费用unknown；未精确提及note或反馈ID，不能证明因果采用或质量。初394项通过后独立读取发现导入环，补两项新进程测试、仅额外重建Agents，后半只读恢复未重启或重发输入/模型；最终镜像读取通过，模型未重测。旧52告警/19Run/63事件/31工件、其他34容器/18卷/134迁移保持；新增1告警、2Run（含probe-only）、7工件及5条合成反馈。3操作key停用，两枚新alerts:read reader保留30天，原六枚reader保持，见[回执](docs/operations/3a-dispositions.md)。

- 3A-08身份读取已限定验收：496项（API108/Agents388）、62项HTTP；27合成节点/22关系、严格tenant/cutoff及真实图源503/查询恢复、PG工件故障/重启回查通过。一次模型身份1进入6931字符prompt，needs_review/自报0.65、1646/135/1781 tokens，费用unknown，不证明引用/质量。初次脚本TEXT参数错型在输入/模型前停止，仅修脚本并从已完成矩阵后恢复，原失败保留。旧53告警/21Run/66事件/38工件/17成本行及其他34容器/18卷/134迁移保持；原八枚reader保持，新增两枚graph:read保留30天，三操作key停用。见[回执](docs/operations/3a-identity-read.md)。

- 3A-09已完成三例真实分诊及51项显式HTTP回查：TP/BTP/needs_review，5223 tokens/费用unknown；分类3/3，但p01时间窗及授权过断言保留，不能算完整质量通过。真实broker7投递/8交付、6次方法/失败替身且无额外模型，复现坏schema/ledger False静默提交、冷重投模型方法重入及暖恢复来源丢失，worker准入不通过。旧54告警/23Run/69事件/46工件/18成本行保持，该批后57/28/77/77/21；36容器/18卷/134迁移不变，无运行修改/重启。3操作key401，10reader保持；初次broker导入及finish断言失败/受控恢复保留，见[回执](docs/operations/3a-triage-admission.md)。

- 3A-10-01普通分诊持久确认与坏消息已限定验收（143项测试、26项显式HTTP、0真实模型），见[回执](docs/operations/3a-triage-durability.md)。两文件修复使live持久失败及已解码坏schema不再静默提交；真实broker7次发布/8次交付、4次模型方法替身，正常五类来源工件及Agents重启回查保持。旧57告警/28Run/77事件/77工件/21成本行保留，该批后58/29/78/82/21；仅Agents更新，35其他容器/18卷/134迁移保持，三操作key401、十枚reader保持。该批当时冷重投/缓存来源/SDK预算未修，后续见下条。

- 3A-10-02普通分诊首次结果/重投保护已限定验收（207项测试、55项显式HTTP、0真实模型），见[回执](docs/operations/3a-triage-recovery.md)。三条真实HTTP/Fusion信封经新独立broker对象验证同worker完整保存恢复、fresh进程复用、跨进程单次认领及退出后unknown；3次发布/7次交付/3次方法替身。当前61告警/32Run/83事件/92工件/21成本行，两新Run完成、一条仅保留开始意图；旧14表材料、35其他容器/18卷/134迁移及十枚reader凭据保持，三操作key401。保护仅Kafka普通live路径，direct triage/replay及原抑制分支不扩张；负cursor真实422、生产SDK预算和完整质量仍未过，下一3A-10-03见[总计划](docs/operations/3a-worker-reliability-plan.md)。

- 3A-10-03-01分诊SDK默认retry0/45秒、整次调用45秒截止及-1增量cursor已限定验收（189项测试、71项显式HTTP、0真实模型），见[回执](docs/operations/3a-triage-request.md)。仅更新并重启API/Agents，旧14表材料、34其他容器/18卷/134迁移及十枚reader保持，三操作key401；无新增告警/Run/事件/工件/成本。跨进程租户额度、积压和停止恢复仍待3A-10-03-02，完整质量与worker准入未过。

- 3A-10-03-02持久分诊额度/积压/停止恢复已限定验收（263项测试、137项显式HTTP、0真实模型），见[回执](docs/operations/3a-triage-budget.md)。新增项目预算表，原134迁移及旧14表材料保持；每次20000预留单位非实际usage，未知占位不自动过期。真实broker6发布/14交付/5次HTTP替身开始，保留三未知预约及一条积压；最终67告警/37Run/92事件/106工件/21成本行，5预约/100000预留单位。仅Agents更新/重启，35其他容器/18卷/十枚reader保持、三操作key401；失败与受控额度调整保留。当前A/B测试policy，完整准入与质量仍未过。

- 3A-11-01只读准入复核已完成，见[回执](docs/operations/3a-admission-review.md)：旧p01时间/授权错误未被indicator gate识别；常驻Agents审批提案guard实际True且缺Kafka bootstrap/TLS，旧调查工具身份仍缺。三未知预约及A积压保持，0模型/消息/offset提交/运行改动；完整准入未过。下一[3A-11-02配置补齐](docs/operations/3a-triage-admission-config-plan.md)，保持worker禁用，然后单独修提示词/复验质量。

- 3A-11-02常驻分诊配置补齐已限定验收，见[回执](docs/operations/3a-triage-admission-config.md)：仅Agents同镜像重建一次，新增四项环境值，复用原只读CA；审批提案guard现False、Kafka SSL/主机名校验及六组offset读取通过。旧14表/三unknown/A积压/十reader/其他35容器/18卷/134迁移保持，0模型/消息/提交。当前22层、19源码层，worker仍OFF；下一[3A-11-03理由提示词修复](docs/operations/3a-triage-reasoning-plan.md)，完整准入/质量未过。

- C01 Fusion持久交付/首次结果恢复已限定验收，见[回执](docs/operations/c01-fusion-delivery.md)：107项测试，真实PG/Redis/SSL Kafka及6项HTTP；17次发送尝试/16次确认、23次物理交付/回读（含独立审计4次），0真实模型。只更新Fusion为delivery-c01，该批当时23层/20源码层；新增5告警/1DLQ，旧14表/35其他容器/18卷/134迁移、十reader、三unknown和原积压保持，2操作key401。探针断言及启动失败、无重发的恢复检查点和计数补充均保留；结束及撤key后独立审计通过，不外推全缓存丢失或整体迁移完成。

- C02分诊正文/发生时间、普通live跨告警缓存与停止清理已限定验收，见[回执](docs/operations/c02-triage-material-cache-stop.md)：118项测试、一次断网生产SDK探针及部署前/后独立审计通过；仅Agents更新为triage-material-c02并设置60秒停止宽限，当前24层/21源码层。0真实模型、0新业务记录/凭据/消息；旧14表、5预约/3unknown、原积压、十reader、35其他容器/18卷/134迁移保持。首轮112通过6失败、误解析与部署挂载顺序断言失败保留；部署只读复核通过，未重复重建。direct/replay旧缓存、实际在途Docker停止和模型质量不外推。

- C03-01分诊时间/授权证据提示词v3及lock已限定验收，见[回执](docs/operations/c03-triage-reasoning.md)：88项测试、一次断网生产SDK探针，完整messages6560字符/6502字节；21其他prompt与schema保持。仅Agents更新一次，60秒停止宽限继承，当前25层/22源码层，0真实模型/新业务写/凭据/消息。旧14表/5预约100000预留单位/3unknown/十reader/六group及35其他容器/18卷/134迁移保持，部署前/后独立审计通过。重复测试入口被独占门拒绝、探针前路径修正均保留，无重复test或失败probe；模型质量及常驻准入待C03-02/03。

- C03-02新理由复验已按质量失败受控停止并通过结束/撤key后独审，见[回执](docs/operations/c03-triage-quality.md)：仅case01一次真实模型/1998 tokens，实际needs_review/0.65未达冻结TP判据，后三例未执行；原schema、材料/PG/API/usage/offset链通过。新增1告警/1Run/3事件/7工件/1成本/1responded预约20000单位及1shadow，0QA；旧五预约/三unknown保留。首次脚本读取权限失败发生在发送前，独审后只改0644并从未发送检查点恢复，原件保留。三操作key401，运行25层/22源码层及其他服务保持、0重启。下一用更明确恶意工件的新四例另冻结，不为旧标签改prompt或重调旧例，常驻仍OFF。

- C03-02B新case01一次真实模型1918 tokens，TP分类正确但无据断言未授权，理由质量未过；后三例未执行，3操作key已停用/401，见[回执](docs/operations/c03-triage-quality-recheck.md)。02B当时v3/039f及25配置/22源码层保持，worker OFF；后续澄清见下条。 新增1告警/1Run/3事件/7工件/1成本/1responded预约20000单位及1shadow、0QA；旧6预约/120000单位/3unknown保持，累计7预约/140000单位。分类与事实支持分别审核，不以技术链通过代替质量。

- [C03-02C-01授权事实边界](docs/operations/c03-triage-authorization.md)v4及lock已限定验收：88项直接测试、4个断网生产SDK完整body（7754–7814字符/7669–7729规范UTF-8字节），0真实模型/业务PG写/新消息。只更新Agents一次至9ba6，env/七只读bind/60秒宽限保持，当前26 Compose/23源码层。旧14表/7预约140000单位/3unknown/十reader及其他35容器/18卷/134迁移保持。验收脚本导入副作用已修，早期104只读SQL/4次metrics误追加的112计数文件保留并归本批，旧844冻结字节保持。模型理由质量和常驻准入仍未过，worker OFF；下一02C-02另冻新四例，不重调旧两例。

- [C03-02C-02新四例复验](docs/operations/c03-triage-authorization-quality.md)已按质量失败受控停止：C03-02C-02三例实际模型共5971 tokens：前两例分类/理由通过，第三例把缺少转移证据误判为FP并推断规则误报，按冻结判据失败停止，第四例未发。三操作key已停用且实际401，技术持久链与结束独审通过；新增3告警/Run、9事件/21工件/3成本/3shadow、3responded预约60000单位，0QA。旧7预约/140000单位/3unknown保持，累计10预约/200000单位；26配置/23源码层保持，0重启。下一C03-02D-01只澄清“无法核查检测条件不等于规则误报”的最小提示词边界，先做0真实模型直接验证和独审；不重调旧三例、不改旧判据。理由/分类质量与常驻准入仍未过，worker OFF，整体迁移未完成。

- [C03-02D-01检测有效性边界](docs/operations/c03-triage-detection-validity.md)v5检测有效性提示词及lock已限定验收：88项直接测试、4次断网生产SDK完整body（7827–7917字符/7742–7832规范UTF-8字节），0真实模型/新业务写。仅Agents一次更新至9cb719，原env/七只读挂载/60秒停止宽限保持，当前27配置/24源码层。旧14表、10预约/200000预留单位/3unknown、十reader、其他35容器/18卷/134迁移保持，部署前/运行/收尾三审通过。首个source stage语法错误在远端Python执行前被拒绝，原失败/恢复及父标签措辞勘误保留；未重复测试、重建或模型调用。下一C03-02D-02另冻四条新对照输入，验证有反证FP、明确授权BTP、缺证NR及事件窗外NR；本四例不复验v5 TP，后续常驻新TP仍须实际独审。旧三批质量失败与七条未发输入保持，worker OFF，质量/常驻及整体迁移未完成。

- [C03-02D-02新对照](docs/operations/c03-triage-validity-quality.md)质量失败后已受控停止并完成结束、撤key后及封后独立审计：两次真实模型回复共4081 tokens；case01 FP分类/理由通过，case02时区换算错误且把窗内已授权活动判为FP，分类/理由失败，case03/04未执行。三操作key已停用并逐枚真实401，十reader及旧10预约/200000单位/3unknown保持。新增2告警/Run、6事件、14工件、2成本/2shadow、2responded预约40000单位，0QA；预约单位不是usage。告警仍new、auto_closed=false，不声称发生错误关闭。当前27配置/24来源层、184Agents/769运行Py及lock保持，0源码/Compose改动、0重启/DDL。首次发送前因本地验收算子遗留旧输入SHA/v4合同被拒绝，0业务/模型；原失败、旧stop与显式恢复审计/独立断网合同probe/新质量stop全部保留，未重复freeze、身份、额度或topic，不重调旧输入。公开交付已完成：28公开文件、远端573索引及769运行Py/lock逐hash一致，交付后独审accepted；不把技术收尾通过写成质量通过。

- [C03-R01](docs/operations/c03-triage-review-only.md)代码隔离与定向部署已限定验收：191项断网测试通过（22项新增、169项既有直接测试），0真实模型/新业务写；仅Agents一次构建、一次替换为19f8f1a5，review_only_v1已配置、worker OFF，七只读挂载/60秒宽限保持。旧14材料表、全部告警字段、12预约/240000预留单位/3unknown、十reader、其他35容器/18卷/134迁移及消息水位保持。首次观察脚本RLS错误与189通过/2夹具失败及恢复均保留。当前28层运行定义、185 Agents/770运行Py，prompt/lock v5不变。下一按[人审准入卡](docs/operations/c03-review-only-profile-plan.md)另冻R02，验两条新A/B输入的有限真实main消费与首次结果恢复；原自治质量失败、C04/C05及后续调查/响应仍待验，整体迁移未完成。

## 尚未完成与限制

- 2026-10-20[已有迁移审核](docs/operations/migration-review-20261020.md)确认来源/部署对应合理，但发现Fusion保存/发布未确认仍提交、source-v1缺行恢复丢关联、分诊正文/时间丢失、校验前缓存及停止异常漏清理。本轮只审核，未修代码或重启；后续R1/R3见C01，R2/R4/R5见C02限定修复。此前“项目topic/group未配置”是误判，1G已设置，DLQ按项目topic派生；未验的是消费起点/逐tenant准入/持续消费。

- 1G已验所列人工入口/API持久结果及dry-run；常驻自动分诊、完整知识消费、完整调查质量、审批/真实响应未验。3A-04—06只验A/B合成组织记忆、技能、PG全文资料读取及各一次真实模型输入；KB1虽已提供但模型未引用，已有向量索引与完整知识/检索/引用质量仍未过。Agents旧只读enrich_ioc仍因增强依赖未接而失败，正确记partial/error；2C-01通过的是Fusion本地IOC路径，不等于该工具已接；报告达token上限，不外推质量，完整服务端基线未冻结。
- 原legacy告警仍保留原归并事实，不重建缺失历史；新source-v1按稳定上游UUID独立保存并关联。旧HTTP桥接仅覆盖已记录UUID且原特征/connector匹配的投递；2B-01补验了所列RBA重投/并发边界；完整缓存丢失、持久风险账本、跨实体事务与旧不可见贡献仍未验。未知schema在tenant/source解析前拒绝，未知identity已验证带tenant/来源的持久DLQ。
- API/Fusion为production配置，无demo/匿名绕过；Kafka新增19093 TLS入口，PG重载启TLS无重启，均验证CA/IP。旧Kafka明文入口保留，broker无客户认证/ACL，单节点不等于生产高可用。
- runtime角色仍保留上游未绑定tenant的worker语义；本批外部HTTP身份与指定告警查询已实测，不外推所有API路由。Redis逻辑库不是ACL隔离。
- 各批操作key已停用；组织记忆与近期处置各两枚alerts:read、技能两枚settings:read与KB两枚knowledge_base:read reader key分别受控、仅映射A/B测试tenant；另有两枚graph:read身份reader，十枚key按用途独立映射，不作万能身份。原四类默认120秒、身份300秒缓存不保证API端即时撤销/编辑/退休；组织记忆/技能逐项检查expires_at，KB时间cutoff不重建被编辑的旧正文，处置created cutoff不重建后来编辑的旧意见；deep investigation原版本pin失败仍可落当前版本，graph关闭、3B前须核。标记数据/失败证据保留。应用只在21 loopback开放，尚非LAN公开API；真实对话模型证据按各批回执区分，未做真实厂商动作。

**旧执行快照（仅保留历史，不覆盖页首新进展）：R01限定验收完成；当时下一C03-R02另冻有限常驻。** [C03-R01](docs/operations/c03-triage-review-only.md)代码隔离与定向部署已限定验收：191项断网测试通过（22项新增、169项既有直接测试），0真实模型/新业务写；仅Agents一次构建、一次替换为19f8f1a5，review_only_v1已配置、worker OFF，七只读挂载/60秒宽限保持。旧14材料表、全部告警字段、12预约/240000预留单位/3unknown、十reader、其他35容器/18卷/134迁移及消息水位保持。首次观察脚本RLS错误与189通过/2夹具失败及恢复均保留。当前28层运行定义、185 Agents/770运行Py，prompt/lock v5不变。下一按[人审准入卡](docs/operations/c03-review-only-profile-plan.md)另冻R02，验两条新A/B输入的有限真实main消费与首次结果恢复；原自治质量失败、C04/C05及后续调查/响应仍待验，整体迁移未完成。 不提交或推送。

历史过程及早期路线调整见[初始化过程归档](docs/handoff/history/2026-10-20-initialization-progress.md)，不作为当前任务表。
