# socai2 / stingAISOC 工作约定

- **2026-10-21二开实施最新顺序：** 用户要求先规划并记录整条路线和关键点，再逐独立模块分析、取舍、修改和功能测试。先可复用支撑能力：UEBA → 威胁情报/IOC → 20上一版既有知识库，再进入Fusion → 分诊 → 调查/攻击路径 → Markdown结果交付。UEBA重点针对哪些实体开启、基线/时间/样本/阈值配置、输入输出及偏离算法；IOC先固定命中/未命中查询，数据量/覆盖率暂不考虑；知识库历史经验相关后看，已有读者/源码保留。基础属性表及讨论纪要见[模块工作说明](docs/operations/module-review-plan.md)，顺序细化唯一总计划B1—B6；本轮只规划，不代表业务代码、运行或验收完成。不预定合并原编排或一次重构全链，复杂可用性和冗余专项继续后置。

- **2026-10-21报告交付：** 当前只要求Markdown生成、持久保存及按Case/Run读取；PDF暂缓，HTML不作本轮前置。不继续格式专项或新报告模型验证；已有代码、依赖和历史结果保留。

- **2026-10-21 full配套补迁：** 按用户最新指示，历史事件补查、Attack Path、UEBA、事件检索、IOC信誉增强及OpenSearch原版索引/检索纳入原版迁移；补enrichment/threatintel/ueba完整模块和直接依赖，沿原接口做必要配置/认证适配并保证基本功能可运行。复用21存储，不另起整套full；不新建上游缺失后端，不扩全量采集/原始检测。复杂可用性、额外质量及未使用分支专项继续暂缓；具体实际验证见[full配套回执](docs/operations/full-support-migration.md)。


## 项目与当前路线

- **full配套运行更新（2026-10-21）：** 历史事件Kafka→Fusion→ClickHouse→API SQL/补查、原UEBA基线→常驻Agents读取、IOC增强接口、OpenSearch项目IOC索引写/搜/精确匹配及TI/API代理已基本实测；无新模型/Feed/厂商调用。API/Fusion同1be37/c52镜像，Agents更新为aec3c54f（candidate05仅COPY bundle）、UEBA 8b04bc64 / enrichment eb59af97 / TI c15d75f4。原图/APOC依赖已接，AttackPath目前实证为PG2节点/1关系回退；UEBA仅1样本，无来源增强不判安全。原worker OFF/7RO/60秒保持，报告只需Markdown。完整运行保原29层后加full-support/ueba/enrichment/threatintel四层；Neo4j插件单独infra overlay。旧“当前镜像/层数/graph关闭”是历史侧注，最新以[本批回执](docs/operations/full-support-migration.md)和PROGRESS为准，整体迁移未完成。



- **2026-10-21最新执行口径（覆盖下文旧优先级和验收前置）：** 当前先完成迁移第一步：从正式输入告警开始，经原告警处理/分诊实际触发并走完调查编排，取得与告警/Run关联的基本调查结果和报告；需要调查时无需人工再次点击。先接通这条完整流程，其他入口、全部分支和常驻运行准入不作为这一步前置。复用已有有效证据，只补实际未接通的环节，不以仅创建Run或调用函数代替走完流程。
- **问题及复杂验证后置：** 用户明确“发现的问题可以做好记录，然后迁移结束后逐步评估解决”，且包括复杂可用性专项、冗余测试和重复校验。质量、算法、报告表述、用量完善、恢复等问题保留原证据并登记迁移后评估；当前仅做走通主链所需的源码/直接依赖/配置/接口接入及最低限度验证。复用相关原测试，不默认重复组合回归、全量hash/水位/表计数/冻结、逐入口模型矩阵、多轮复核或新建验收控制框架；保留change结束的一次必要独审。详细问题沿用[现有登记](docs/operations/upstream-issues.md)，不另建任务树。
- **事实和既有保护保持：** 后置不追认旧质量通过，不撤现有租户/权限、预算和unknown保护，不重放旧unknown或清空积压；未授权真实厂商动作和Git提交/推送不开启。已修源码及已有测试保留，不为回退另造工作；运行启用和第一步是否走通仍按实际证据记录。

- **2026-10-21工作目的与执行授权：** 用户明确开始执行，允许多个worker并行。当前工作有三个共同目的：①迁移告警及后续处理流程，保证实际功能和结果符合预期；②在迁移中理解源码，对照固定版本官方文档核功能点，标清已实现、未接通和声明未实现，不把文档声明当交付事实；③整理当前架构、模块职责、数据/调用关系与扩展点，供后续二次开发。执行与功能对照、架构梳理同步推进；不另开全平台重构或无限上游审计。见[总计划](docs/operations/completion-plan.md)、[官方功能对照](docs/operations/alert-function-alignment.md)、[当前架构](docs/architecture/alert-processing.md)。下列旧“先讨论/仅规划”是历史阶段，当前已进入实施，完成仍以实际证据为准。

- **2026-10-21最新范围/优先级（优先于下列旧批次“下一项”）：** 用户确认完整迁移告警与调查，包括自动分诊、自动关闭告警、自动升级调查及人工调查/报告；playbook和反馈可暂缓，一体源码/依赖原样保留，不额外修改或专项测试。启动顺序、退出、重启/故障恢复等可用性专项登记后置，不作为功能迁移前置；现有保护代码、旧unknown和历史证据保留。[完整性评估](openspec/changes/restore-alert-investigation-integrity/assessment.md)已完成，现按批实施修复和必要定向部署，实际运行与质量以回执为准；R02[侧附暂缓](openspec/changes/admit-review-only-triage-worker/status.md)，原0/17及五文件不改。完整目标不等于自治质量或真实响应已验收，亦不扩大前端/采集/检测职责。
- **实施总原则：功能完整、结果正确优先，最小必要适配。** 所有一体模块/依赖都可整体原样迁入，不因本轮暂不使用就拆分、删改、重构或额外测试，playbook/反馈只是例子。仅改直接缺失的功能、正常业务结果错误及实际接入必需项；复用现有测试，只做本次改动所需的最少代表验证。冗余抽象/多层包装、提前统一架构，以及启动顺序、退出、重启/恢复、故障注入、长稳/压力等服务可用性测试和修复登记暂缓，不再设成功能迁移前置。整体原样迁入可标“未专项验证”，不得改写成已测通过；现有保护与旧证据保留。
- **当前总计划：** [completion-plan](docs/operations/completion-plan.md)按B1告警链、B2默认人工调查、B3知识实际消费、B4自动分诊/关闭/自动调查、B5其他调查及交付、B6整体功能验收推进，沿用现有六阶段及restore产品任务。自动升级后须实际自动取证/分析/结果交付，无需人工再次点击；不是仅创建Run或给建议。当前B1已限定完成，B2/B3已接入并有实际消费/报告证据但质量未全过，B4自动调查的正常结果阻塞正最小修复，R02仍后置。

- **当前运行侧注：** B1已限定验收；candidate03的B4/B5/报告/技能pin修复与原生PDF依赖已部署，组合383项通过并独审。candidate04再修一处KB标记解析并接原七权限只读API服务身份，32项直接测试通过、定向替换API/Agents健康（API1be37c38、Agentsc311a94b、Fusionc52b9aac），部署后独审及六项HTTP通过（200/403/403/401/403/200）。candidate05仅默认Forensic/Report两文件假设/范围/处理时间语义，24项直接测试及独审后已一次替换Agents至4ccf3a6d，env/七RO/60秒保持；0新模型/消息/业务写，不含尚未部署的C2图/deep修复。实际仍用原28层末加integrity的[二十九层命令](deploy/aisoc21/README.md)，772运行Py/lock1。新人工Run四调用10167 tokens、MD/HTML/PDF200，内容质量仍未全过，原失败Run不重调/改写。旧unknown/积压/十reader保持，B1两临时操作key已撤401；后续A/B两操作key及新C六短期key现已全部停用并逐枚真实401，旧十reader及永久服务只读身份保留。C上下文11项只读验收通过；第一条source-v1 C告警经原worker实测BTP0.95/原0.85阈值自动关闭、1真实回复2174tokens，分类/理由/实际关闭独审通过，旧预算/两old组保持；第二条已自动调查，但deep六步截断、graph20451 tokens超过20000边界，报告把知识映射和风险prior写成攻击/确认事实，质量失败后STOP；首NR/告警未关保持。两例8回复24742 tokens，不重调旧输入；最小源码修复/独审进行中，常驻worker仍OFF，整体迁移未完成。下列旧运行层数与“下一项”为历史事实。

- 用户于2026-10-20授权按当前服务端范围持续推进到迁移完成：先落实剩余规划，每个change结束必须由未参与实现者做审计；常规接入、阻塞修复、隔离验收、有界模型和必要定向部署直接推进。上游已有非阻塞问题统一登记暂缓，不扩为无休止优化；本地适配缺陷和已承诺主链/租户/持久/审批阻塞不能用登记替代修复。执行追踪见[完成计划](docs/operations/completion-plan.md)与[上游问题清单](docs/operations/upstream-issues.md)。真实高风险动作仍需明确受控目标/凭据/审批，Git不自动提交或推送。

- 工作目录：`/Users/lychee/Documents/project/socai2`；GitHub：`https://github.com/Dinines/socai2`。
- 产品名称为 **stingAISOC**；AiSOC 是上游来源，服务名、配置名、数据库名暂按原版保留，避免为改名破坏移植基线。
- 当前目标：**告警及后续数据处理服务端**。接收已有告警，交付API、消息与持久化结果；不负责前端、采集、原始事件检测或独立展示推送服务。范围以[模块对齐](docs/operations/alert-processing-scope.md)为准，阶段目标见[迁移路线](docs/operations/service-roadmap.md)。早期全量移植决定已归档，不再约束当前完成条件。
- 本项目是新的独立工作线，不自动继续旧 SOCAI 的 Basic/OpenSpec 任务，不以旧实现合同强制改写原版。
- 用户于2026-10-21明确采用 **OpenSpec 作为本项目实施规范**。后续变更按本项目 `openspec/` 管理，不导入旧工程的 change 或完成证明；入口见[OpenSpec实施说明](openspec/README.md)。
- API/Fusion固定源码及直接测试已迁入并在21跑通1F标记数据链；1D向量和1E五角色网关只完成各自结构/存取/路由验收；1G Agents/Actions已迁入并验人工调查/API持久结果与dry-run，常驻自动worker/完整知识消费/真实响应未启；不能写成整个服务端迁移已完成。当前实测与限制见PROGRESS及各批回执。
- 用户已确认不同上游告警各存一行，再关联到同一事件。2A独立告警source-v1/旧legacy兼容及持久关联已限定验收（95项测试），旧legacy合并事实不重建；2B-01风险重投/并发边界（40项）与2B-02规则内容指纹/实际方法采用/缓存恢复（83项）已限定验收，旧材料/回执不改写。
- 2C-01本地历史IOC经真实HTTP/Kafka/Fusion/PG/API及重启回查已验（62项测试），历史匹配保留日期/弱证据且不增权，见[回执](docs/operations/2c-ioc-consumption.md)。2C-02 PG资产/权限/漏洞/先前告警只读视图及独立评分已限定验收（30项测试），见[上下文回执](docs/operations/2c-processing-context.md)；2C-03已核来源不足及缺源返回，真实事件/UEBA消费仍未接，见[回执](docs/operations/2c-event-ueba-sources.md)。3A-01规则抑制持久回执与DLQ/提交保护已限定验收（83项测试），见[回执](docs/operations/3a-policy-suppression.md)；3A-02有界真实模型/账本/API及盲测分类已限定验收（46项测试，6成功回复/7406 tokens），首轮污染结果保留，完整质量未过，见[回执](docs/operations/3a-model-triage.md)。该批发现的风险分语义问题后续由3A-03修复；当时五类context401后续已逐项处理；旧增强/API工具身份及引用质量仍未解决，常驻worker和响应关闭。
- 3A-03缺失/null与显式0风险分及来源语义已限定验收（184项测试，1次真实模型/1345 tokens），见[回执](docs/operations/3a-risk-score.md)，保留原数值特征算法和旧材料。3A-04每租户组织记忆认证、过期/失败状态、事务工件与真实模型消费已限定验收（194项测试、1次真实模型/1523 tokens），见[回执](docs/operations/3a-org-memory.md)。只配置A/B测试tenant，两枚受控30天只读reader key保留，三操作key停用；缓存120秒不保证服务端即时撤销。3A-05技能读取认证/选择来源、事务工件与实际模型消费已限定验收（347项测试、48项最终HTTP检查、一次真实模型/1677 tokens），v3当前头与原v2工件分离、重启回查保持，见[回执](docs/operations/3a-tenant-skill.md)。两枚新settings:read reader保留30天，三操作key停用；原两枚组织记忆alerts:read key及映射保持。3A-06 KB读取认证、保守cutoff、实际采用文本/引用及事务工件已限定验收（236项测试、一次真实模型/2095 tokens），见[回执](docs/operations/3a-kb-read.md)。真实prompt提供KB1，模型未引用KB标记，不能宣称引用质量通过；两次模型前预算预检失败保留，恢复未重发输入或模型。新增两枚独立knowledge_base:read reader保留30天，原组织记忆/技能四枚key及映射保持。只验A/B合成PG全文资料，不等于已有向量索引或真实SOP质量；该批当时处置/身份两类context401及完整质量未过；处置后续见下条。
- 3A-07近期分析员处置认证读取/采用来源与事务工件已限定验收（396项测试、60项显式HTTP检查、一次真实模型/1909 tokens），见[回执](docs/operations/3a-dispositions.md)。三条个人意见进入7355字符的实际prompt，模型needs_review/自报0.65，未精确提及note或反馈ID，不作因果采用或质量通过。初394项测试后收尾独立读取发现导入环，补两项独立进程测试并仅重建Agents；最终镜像常驻身份读取通过，未重测模型。新增两枚独立alerts:read reader保留30天，原org/skill/KB六枚key保持，三操作key停用；该批当时身份reader401，后续见下条。
- 3A-08身份读取认证/图源失败/确切采用及事务工件已限定验收（496项测试、62项HTTP检查、一次模型1781 tokens），见[回执](docs/operations/3a-identity-read.md)。五类reader已接通，仅A/B合成资料；新增两枚graph:read reader，原八枚保持。导入cutoff不等于HR历史或当前授权，300秒缓存不保证即时撤销。脚本失败与检查点恢复保留；受控复验后续见下条。
- 3A-09三例受控复验与可靠性审计已完成，见[回执](docs/operations/3a-triage-admission.md)。三次真实模型5223 tokens，分类3/3但p01时间/授权理由不受支持，完整质量不通过；broker替身复现冷重投重入模型方法、坏schema无DLQ提交、ledger False仍提交及暖保存恢复丢五类来源语义，worker准入不通过。无运行改动或重启，三操作key401、十枚reader保持；后续修复见下条，旧回执不改写。
- 3A-10-01普通分诊持久确认与坏消息已限定验收（143项测试、26项显式HTTP、0真实模型），见[回执](docs/operations/3a-triage-durability.md)。两文件修复使live持久失败及已解码坏schema不再静默提交；真实broker7次发布/8次交付、4次模型方法替身，正常五类来源工件及Agents重启回查保持。旧57告警/28Run/77事件/77工件/21成本行保留，该批后58/29/78/82/21；仅Agents更新，35其他容器/18卷/134迁移保持，三操作key401、十枚reader保持。该批当时冷重投/缓存来源/SDK预算未修，后续保护见下条，旧回执保留。
- 3A-10-02普通分诊首次结果/重投保护已限定验收（207项测试、55项显式HTTP、0真实模型），见[回执](docs/operations/3a-triage-recovery.md)。三条真实HTTP/Fusion信封经新独立broker对象验证同worker完整保存恢复、fresh进程复用、跨进程单次认领及退出后unknown；3次发布/7次交付/3次方法替身。当前61告警/32Run/83事件/92工件/21成本行，两新Run完成、一条仅保留开始意图；旧14表材料、35其他容器/18卷/134迁移及十枚reader凭据保持，三操作key401。保护仅Kafka普通live路径，direct triage/replay及原抑制分支不扩张；负cursor真实422、生产SDK预算和完整质量仍未过，下一3A-10-03见[总计划](docs/operations/3a-worker-reliability-plan.md)。
- 3A-10-03-01分诊SDK默认retry0/45秒、整次调用45秒截止及-1增量cursor已限定验收（189项测试、71项显式HTTP、0真实模型），见[回执](docs/operations/3a-triage-request.md)。仅更新并重启API/Agents，旧14表材料、34其他容器/18卷/134迁移及十枚reader保持，三操作key401；无新增告警/Run/事件/工件/成本。跨进程租户额度、积压和停止恢复仍待3A-10-03-02，完整质量与worker准入未过。
- 3A-10-03-02持久分诊额度/积压/停止恢复已限定验收（263项测试、137项显式HTTP、0真实模型），见[回执](docs/operations/3a-triage-budget.md)。新增项目预算表，原134迁移及旧14表材料保持；每次20000预留单位非实际usage，未知占位不自动过期。真实broker6发布/14交付/5次HTTP替身开始，保留三未知预约及一条积压；最终67告警/37Run/92事件/106工件/21成本行，5预约/100000预留单位。仅Agents更新/重启，35其他容器/18卷/十枚reader保持、三操作key401；失败与受控额度调整保留。当前A/B测试policy，完整准入与质量仍未过。
- 3A-11-01只读准入复核已完成，见[回执](docs/operations/3a-admission-review.md)：旧p01时间/授权错误未被indicator gate识别；常驻Agents审批提案guard实际True且缺Kafka bootstrap/TLS，旧调查工具身份仍缺。三未知预约及A积压保持，0模型/消息/offset提交/运行改动；完整准入未过。下一[3A-11-02配置补齐](docs/operations/3a-triage-admission-config-plan.md)，保持worker禁用，然后单独修提示词/复验质量。
- 3A-11-02常驻分诊配置补齐已限定验收，见[回执](docs/operations/3a-triage-admission-config.md)：仅Agents同镜像重建一次，新增四项环境值，复用原只读CA；审批提案guard现False、Kafka SSL/主机名校验及六组offset读取通过。旧14表/三unknown/A积压/十reader/其他35容器/18卷/134迁移保持，0模型/消息/提交。当前22层、19源码层，worker仍OFF；下一[3A-11-03理由提示词修复](docs/operations/3a-triage-reasoning-plan.md)，完整准入/质量未过。
- 2026-10-20[已有迁移审核](docs/operations/migration-review-20261020.md)发现Fusion交付确认、source-v1缺行关联恢复、分诊正文/时间投影、校验前缓存及停止异常清理仍有缺陷；源码来源/hash对应不等于整体正确。该轮未修运行代码；后续R1/R3由C01限定修复，R2/R4/R5由C02限定修复，理由复验见C03；此前topic/group/DLQ“未配置”系误判，1G已配置topic/group、DLQ按项目topic派生，旧冻结回执由审核勘误。常驻worker仍禁用，不重调unknown。
- C01 Fusion交付/首次结果恢复已限定验收（107项测试、6项HTTP、0模型），见[回执](docs/operations/c01-fusion-delivery.md)。真实PG故障接缝与独立SDK发送失败均未越过offset，首次完整快照/新legacy兼容及DLQ确认通过；只更新Fusion，新增5告警/1DLQ，旧材料/预算/reader/其他35容器保持，2操作key停用；探针失败与只读恢复保留，最终独立审计通过。有限TTL全部痕迹消失不保证恢复，旧snapshotless行不重建；下一C02见[执行卡](docs/operations/c02-triage-material-cache-stop-plan.md)。
- C02分诊正文/发生时间投影、普通live停跨告警pattern结论复用及异常停止清理已限定验收（118项测试/断网SDK探针/0真实模型），见[回执](docs/operations/c02-triage-material-cache-stop.md)。仅Agents更新并设60秒停止宽限；旧14表/预算/十reader/原积压及其他35容器保持，首轮失败与部署列表顺序断言/只读恢复保留。direct/replay旧缓存、实际在途Docker停止及模型质量未外推；下一[C03](docs/operations/c03-triage-reasoning-plan.md)。
- C03-01分诊时间/授权证据提示词v3已限定验收（88项测试/断网SDK/0真实模型），见[回执](docs/operations/c03-triage-reasoning.md)。21其他prompt、schema及旧数据/预算/reader保持，仅Agents更新一次、继承60秒宽限；完整prompt6560字符/6502字节。原操作入口拒绝及探针前修正保留；不等于理由质量或常驻准入，该批传输验收不替后续质量。C03-02仅case01一次1998 tokens后因冻结分类/理由未过而受控停止，后三例未执行；基础设施通过、3操作key401、原失败/恢复保留，见[回执](docs/operations/c03-triage-quality.md)。C03-02B新case01一次真实模型1918 tokens，TP分类正确但无据断言未授权，理由质量未过；后三例未执行，3操作key已停用/401，见[回执](docs/operations/c03-triage-quality-recheck.md)。02B当时v3/039f及25配置/22源码层保持，worker OFF；后续澄清见下条。
- [C03-02C-01授权事实边界](docs/operations/c03-triage-authorization.md)v4及lock已限定验收：88项直接测试、4个断网生产SDK完整body（7754–7814字符/7669–7729规范UTF-8字节），0真实模型/业务PG写/新消息。只更新Agents一次至9ba6，env/七只读bind/60秒宽限保持，当前26 Compose/23源码层。旧14表/7预约140000单位/3unknown/十reader及其他35容器/18卷/134迁移保持。验收脚本导入副作用已修，早期104只读SQL/4次metrics误追加的112计数文件保留并归本批，旧844冻结字节保持。模型理由质量和常驻准入仍未过，worker OFF；下一02C-02另冻新四例，不重调旧两例。
- [C03-02C-02新复验](docs/operations/c03-triage-authorization-quality.md)受控停止并封存：C03-02C-02三例实际模型共5971 tokens：前两例分类/理由通过，第三例把缺少转移证据误判为FP并推断规则误报，按冻结判据失败停止，第四例未发。三操作key已停用且实际401，技术持久链与结束独审通过；新增3告警/Run、9事件/21工件/3成本/3shadow、3responded预约60000单位，0QA。旧7预约/140000单位/3unknown保持，累计10预约/200000单位；26配置/23源码层保持，0重启。下一C03-02D-01只澄清“无法核查检测条件不等于规则误报”的最小提示词边界，先做0真实模型直接验证和独审；不重调旧三例、不改旧判据。理由/分类质量与常驻准入仍未过，worker OFF，整体迁移未完成。
- [C03-02D-01检测有效性边界](docs/operations/c03-triage-detection-validity.md)v5检测有效性提示词及lock已限定验收：88项直接测试、4次断网生产SDK完整body（7827–7917字符/7742–7832规范UTF-8字节），0真实模型/新业务写。仅Agents一次更新至9cb719，原env/七只读挂载/60秒停止宽限保持，当前27配置/24源码层。旧14表、10预约/200000预留单位/3unknown、十reader、其他35容器/18卷/134迁移保持，部署前/运行/收尾三审通过。下一C03-02D-02另冻四条新对照输入，验证有反证FP、明确授权BTP、缺证NR及事件窗外NR；本四例不复验v5 TP，后续常驻新TP仍须实际独审。旧三批质量失败与七条未发输入保持，worker OFF，质量/常驻及整体迁移未完成。
- [C03-02D-02新对照](docs/operations/c03-triage-validity-quality.md)质量失败后已受控停止并完成结束、撤key后及封后独立审计：两次真实模型回复共4081 tokens；case01 FP分类/理由通过，case02时区换算错误且把窗内已授权活动判为FP，分类/理由失败，case03/04未执行。三操作key已停用并逐枚真实401，十reader及旧10预约/200000单位/3unknown保持。新增2告警/Run、6事件、14工件、2成本/2shadow、2responded预约40000单位，0QA；预约单位不是usage。告警仍new、auto_closed=false，不声称发生错误关闭。当前27配置/24来源层、184Agents/769运行Py及lock保持，0源码/Compose改动、0重启/DDL。首次发送前因本地验收算子遗留旧输入SHA/v4合同被拒绝，0业务/模型；原失败、旧stop与显式恢复审计/独立断网合同probe/新质量stop全部保留，未重复freeze、身份、额度或topic，不重调旧输入。下一先另冻人审profile新准入计划，尚未实施或验收；原自治分类/理由质量及常驻准入未过，worker OFF。原C03质量硬门和本批判据保持，C04/C05调查/知识及后续响应仍待逐批验收，整体迁移未完成。
- [C03-R01](docs/operations/c03-triage-review-only.md)代码隔离与定向部署已限定验收：191项断网测试通过（22项新增、169项既有直接测试），0真实模型/新业务写；仅Agents一次构建、一次替换为19f8f1a5，review_only_v1已配置、worker OFF，七只读挂载/60秒宽限保持。旧14材料表、全部告警字段、12预约/240000预留单位/3unknown、十reader、其他35容器/18卷/134迁移及消息水位保持。首次观察脚本RLS错误与189通过/2夹具失败及恢复均保留。当前28层运行定义、185 Agents/770运行Py，prompt/lock v5不变。下一按[人审准入卡](docs/operations/c03-review-only-profile-plan.md)另冻R02，验两条新A/B输入的有限真实main消费与首次结果恢复；原自治质量失败、C04/C05及后续调查/响应仍待验，整体迁移未完成。
- 当前运行必须使用identity→risk→policy→ioc→context→suppression→risk-score→org-memory→tenant-skill→kb-read→dispositions→identity-read→triage-durability→triage-recovery→triage-request→triage-budget→triage-admission-config→fusion-delivery-c01→triage-material-c02→triage-reasoning-c03→triage-authorization-c03→triage-detection-validity-c03→triage-review-only-c03叠加层，完整二十八层命令见[21操作说明](deploy/aisoc21/README.md)。当前配置差异见[配置来源](docs/handoff/3a-triage-admission-config-source-manifest.json)，当前源码见[C03-R01来源清单](docs/handoff/c03-triage-review-only-source-manifest.json)。专用图读取不启通用schema初始化，READ_ACCESS不是数据库只读租户角色；处置意见按rule优先、创建时间及ID排序，created cutoff不重建后来编辑的旧意见，来源投影hash不是历史版本证明；默认120秒缓存不保证服务端即时撤销或编辑生效。KB为PG全文检索，保守排除split后创建或修改的行，不重建旧正文；最终nonce块/文本/hash与引用记录分开核。技能加法权重不等于严格优先级，deep investigation旧版本pin失败可落当前版本，graph关闭，列入3B准入检查。回退注意旧float-only消费者不兼容新null消息；新读取回执/工件first-write保证不等于整个Run完全冻结。不外推完整缓存丢失、持久风险账本、跨实体事务、无限并发或完整调查质量；Fusion ML状态认证503仍保留。
- 用户于2026-10-20进一步确认：从 `/Users/lychee/Documents/project/SOCAI/opensource/AiSOC` 参考源码直接复制相关代码，**按规划逐步迁入，先迁依赖**；必要的删除或修改先讨论。第一批依赖快照不等于业务源码完整迁入。

## 开始工作先读

1. [项目入口](README.md)、[进度](PROGRESS.md)。
2. [当前服务端范围](docs/operations/alert-processing-scope.md)、[六阶段迁移路线](docs/operations/service-roadmap.md)、[依赖迁移计划](docs/operations/dependency-migration-plan.md)。范围、阶段退出、批次验收、完成状态分别在这些文档及PROGRESS维护，不另立冲突目标。
3. [模块总览](docs/reference/aisoc/01-system-map.md)，再读对应 M 编号的专题。
4. 涉及环境或模型时读 [环境](docs/operations/environment.md)、[配置与凭据索引](docs/operations/configuration.md)及[已有证据](docs/operations/verified-evidence.md)。需求日常阅读见 [需求 Markdown](docs/requirements/README.md)。
5. 用户指出 [docs/anal](docs/anal/README.md) 保存此前分析：复用模块、源码、测试和风险结论，对照固定源码核实。`docs/reference/aisoc`为交接链接版，两份分析保留；其中全量上游结构不扩大当前职责，历史规划不作为当前任务。文档入口见[导航](docs/README.md)。
6. 读[OpenSpec实施说明](openspec/README.md)与[项目配置](openspec/config.yaml)，通过 `openspec list` / `openspec list --specs` 查当前 change 和规格，再读本批相关的完整 spec、proposal、design、tasks及status。当前为 `restore-alert-investigation-integrity` 实施中；旧R02目录虽仍可能被CLI列为ready，但按status暂缓，不执行。

## OpenSpec 实施规范

- 行为、API/消息合同、租户/权限、持久化、模型调用、部署及运行准入变更，必须先有本项目 OpenSpec change，形成 `proposal.md`、对应规格增量、`design.md` 和 `tasks.md`，再实施。使用 `spec-driven` schema；纯工具/文档/重构且没有规格级行为变化时，设置 `.openspec.yaml` 的 `skip_specs: true`，不得编造业务需求来凑校验。简单拼写/链接修正可并入相关 change 的记录，不另开重复任务。
- 职责范围仍以 `alert-processing-scope.md`、阶段退出以 `service-roadmap.md`、路线依赖以 `completion-plan.md` 为准；实际完成由 PROGRESS、原批次回执和来源清单证明。OpenSpec追踪本次增量及场景，不复制另一套完成口径；范围冲突先对齐，不静默扩张。
- change按本次实际影响保留需求、必要设计、简短任务、直接业务证据和未参与实现者结束审计。已有受控运行边界沿用，不默认重做每批全量冻结、计数或恢复验收；仅原样迁入的一体模块不新增独立修改/测试任务。创建change或CLI校验不代表业务已通过，也不新增逐批用户确认门。
- 按最新范围，只补本批直接功能/结果及必要身份检查；冗余设计和服务可用性相关测试、修复均后置登记，不将旧R02或旧全链清单重新变为功能前置。正常业务结果错误仍按最小改法修复；只在特殊故障/恢复场景出现的接续问题可后置，不为此先建通用恢复框架。既有已验修复不回退。
- 实施前运行 `openspec validate <change> --strict --no-interactive`；任务仅在实际完成并有证据时勾选。失败、unknown、未执行样例和未验能力原样保留，不以文档齐全替代实施完成。
- 结束独审通过、直接验收和交接更新完成后，才执行 `openspec archive <change> --yes`，将已交付的规格增量同步至 `openspec/specs/`。工具/文档change使用 `--skip-specs`；归档后复核规格和任务。已封存的R01及更早批次只作前置引用，不倒填新change或改写冻结回执。
- 不自动提交或推送Git。OpenSpec不替代明确目标、凭据及高风险响应审批，亦不授权重放旧unknown、清空积压或启用常驻worker。

## 来源与开发边界

- [AI SOC2.docx](docs/requirements/AI%20SOC2.docx)是完整产品需求原件，不改写；本仓库实施其用户确认的服务端职责子集，范围外需求不计作本服务已交付，也不自动转为本轮任务。实际完成与运行行为以证据为准，上游注释、历史建议及旧工程完成状态不能覆盖当前范围或实测事实。
- 固定上游 `https://github.com/beenuar/AiSOC`，初始 revision：`34ca18c57dd4175539e5c6dd3d04a72dc057306b`。测试中途不自动升级。
- 范围内尽量保留上游服务关系、测试和直接构建依赖；不默认迁入采集、原始事件检测、前端和独立展示推送服务，不因范围收敛盲删共享代码/SQL。仅做必要接入/环境适配、真实阻塞修复及基本授权/凭据保护，记录差异；编排合并、存储替换等在基线测试后再决定。
- `SOCAI/opensource/AiSOC` 为旧工程只读参考，不在其中修改移植业务。迁入范围内服务源码时先检查与本目录 README/AGENTS 等同名文件，保留上游原件和本地差异，不直接覆盖。
- 用户授权充分调配已提供资源，复用已有数据及`../SOCAI/knowledge`，模型服务可按负载部署在20、21，43沿用既有对话服务；常规已授权操作直接推进。数据/模型来源及选择见[知识复用计划](docs/operations/knowledge-data-reuse-plan.md)，较大本地4B模型作为比较候选，不能把资源充足写成质量已验。
- 原版持久化、租户、身份和状态语义先实测；调查结论、响应提案、审批、执行和效果验证分别记录。已冻结事实/原始证据不改写。
- 模型建议不直接扩大工具权限；高风险真实响应要求明确目标、基本授权与审批。结果 unknown 不自动重发有副作用操作。
- 日志、文档和 Git 不放密码、token、私钥、隐藏推理或不受控原始敏感材料。凭据仅记录受控位置。

## 环境与测试

- 用户确认新项目部署目标是 `192.168.1.21`；SSH 别名 `sting-infra21`。优先复用21公开数据服务，按项目库/账号、topic/group、集合隔离对象；用户允许必要时适当重启，先核影响、保存配置与状态，仅操作所需单服务并验证恢复。21四个旧业务容器保持关闭；保留其他项目和数据，禁止全库/全卷清理。
- `192.168.1.20` 是已有 AiSOC 参考环境，账号 `lychee`、目录 `/home/lychee/beenuar`；其部署/测试记录可复用为对照，不等于新项目已经部署到21。
- 对话测试服务沿用 43 的现有 OpenAI-compatible 服务；20 本地 Ollama 只做 embedding，21已复现独立同模型实例（16核CPU/32GiB），仅结构/存取已验，未接调查消费。配置和实际可用性以操作前核对为准。
- 开始先检查分支、未提交内容及目标环境，保留已有修改；默认工作分支 main。
- 优先复用有效上游测试和既有证据，只补本次变更所需的最少功能/正确性验证；一体模块原样迁入不额外修改或测试，不默认全仓回归、全部依赖专项或慢速矩阵。冗余设计与服务可用性测试/修复按上述原则登记后置。
- 每条重要验收写输入 → 实际中间产品/调用 → 最终值与关系。区分测试替身、真实基础设施、真实模型、真实厂商和生产观测。
- 用样本/测试 tenant、Case、Run 或可识别测试标签隔离；不清空整个数据库、集合或现有业务数据来方便测试。
- 模型/向量服务连通不等于质量通过；ATT&CK/TI/memory 的索引成功不等于调查已消费结果。费用/usage 未知不写成零。
- 变更行为前按上述OpenSpec规范建立当前批次的范围、规格增量、设计、任务和验收；不复制旧任务树或借用旧 change 作为完成证明。
- 交付时更新最近文档和简短 PROGRESS，说明实际变化、验证限制及下一单项。提交/推送依据本项目明确指令执行。
