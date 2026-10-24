**调查新版开发与评审入口：** [docs/investigation/README.md](investigation/README.md) 汇总设计、开源/当前/目标对照、实际进度、全部已知问题入口、测试与公开回执。其他机器正常拉取调查分支即可阅读；开发在普通项目目录，不在.local工作树。

后续调查设计与换账号续接统一读[调查模块规划设计文档](architecture/investigation-planning-design.md)：问题/证据/分析判断/执行状态、程序与模型分工、旧模块融合、完整案例和官方参考。未来在专用分支逐模块明确预期、开发测试，通过后再推进；统一设计尚未实施。旧产品研究及工程建议保留为依据，不作为第二份实施主方案。

后端表/数据交接新增[25表428字段与实际落库盘点](integration/v1/data-inventory.md)，附真实两例ID、完整性/截断边界及已执行的只读SQL。

当前v1.0.0服务已发布并启用自动分诊/调查：先读[生产接入与实际结果](integration/v1/production.md)、[发布回执](operations/service-v1-release-20261022.md)。模型保持，调查partial/质量边界如实保留。

后端对接发布文档v1：[总入口与每步输入输出](integration/v1/README.md)、[数据库/Kafka等连接配置](integration/v1/configuration.md)、[Kafka消息合同](integration/v1/kafka.md)、[调查入口/逐步输出/结论读取](integration/v1/investigation.md)、[表与关系](integration/v1/database.md)。正式告警走Kafka，HTTP告警仅测试；含JSON/SQL/env示例，配置依据/待核项与运行边界明确列出。

两个暂停项目已恢复：[逐步执行记录](operations/two-projects-resume-20261022.md)。[测试工具](operations/testdata-tools-20261022.md)3条新隔离告警真实入口/Kafka/Fusion/PG已通过；产品建议已补v1实际状态，优化方案尚未选定实施。原[收尾停点](handoff/session-closeout-20261022.md)保留为历史。

智能调查产品设计：[急需问题、四个共享合同、Deep优化与场景扩展](architecture/investigation-product-engineering-roadmap-20261022.md)。从安全产品与工程角度给出优先级、代码落点、首批场景及验收口径；仅建议，未新增实施或运行。

标书需求评估：[模块设计、迁移正确性与后续推进](operations/tender-requirements-assessment-20261022.md)，附 [35 子组164条逐项矩阵](requirements/socai2-requirements-matrix-20261022.md)。以当前项目实证判断，区分部分满足、缺口、未验和外部模块责任；不把迁移接通当作标书验收。

最新本地镜像：[候选镜像构建、镜像内核验与正确本地builder用法](operations/investigation-candidate-images-20261022.md)。API/Agents两镜像已生成，19源码/7排除项与离线导入路由通过；未部署21或启用常驻。

最新候选准备：[19文件组合、父版本与最小构建用法](operations/investigation-candidate-build-20261022.md)，本地100项直接合同及路由登记通过；本地Docker未运行，尚未构建或部署。

最新概念讨论：[Incident、Fusion候选链、调查Chain/Path的对象与ID](architecture/attack-chain-path.md#concepts)、[四种归组组合与例子](architecture/attack-chain-path.md#membership-examples)、[Case/Playbook自动化](architecture/attack-chain-path.md#case-automation)、[结论与未决取舍](architecture/attack-chain-path.md#discussion-conclusions)。仅文档澄清：Fusion链已留存但未接下游业务消费，调查链重查PG，Path展开已有关系，不把讨论当行为修改。

最新Kafka入口实证：[有界真实联合](operations/kafka-graph-joint-20261022.md)已验证本地消费者→API→21 PG/Neo4j在分诊前写图，直接邻域5节点4边；与原GET的14个可达候选、模型调查和21常驻发布分别记录。

最新本地开发环境：[Conda依赖检查与补齐](operations/local-dependencies-20261022.md)，API/Agents共同依赖清单及离线核验；与Kafka联合观察、发布状态分开记录。

2026-10-22最新：按用户选择，在Agents读取fused Kafka后、分诊前统一准备图，Fusion保持不改；Conda项目环境已建立，本地85项直接合同通过，详见[Kafka入口增量](operations/kafka-graph-intake-20261022.md)。未发布、worker OFF、5/15及旧质量失败保持；此前[B5→B6交接](operations/investigation-stage-handoff-20261022.md)保留原范围。

链/图本地交付：见[配置与使用](architecture/attack-chain-path.md)、[完整告警案例与读取](operations/attack-chain-path-local-20261021.md)。四Agent真实消费/Run工件/Markdown已本地实测；暂未发布，首轮失败保留。

# 项目文档入口

2026-10-21路线规划阶段记录：当时先按[总计划](operations/completion-plan.md)记录UEBA → 威胁情报/IOC → 20既有知识库，再Fusion → 分诊 → 调查/攻击路径 → Markdown交付的顺序。支撑能力基础属性表和讨论纪要见[逐模块设计](operations/module-review-plan.md)；该规划阶段没有功能实施，后续实际本地实施/发布以页首交接、PROGRESS和原回执为准。

当前迁移已进入实施，以[总执行计划](operations/completion-plan.md)为主表、[六阶段路线](operations/service-roadmap.md)为退出标准、[知识消费计划](operations/knowledge-data-reuse-plan.md)为B3细化；自动分诊、关闭、升级并实际执行调查均列主线。B1已限定完成；人工调查、实际工具/知识消费及Markdown持久读取已有[限定实证](operations/integrity-investigation-r01.md)，自动调查亦已走通，但内容/引用/深度质量未完整通过。后续full配套的基本接线见[回执](operations/full-support-migration.md)，不计作标书功能或整体迁移全部完成。

当前原则：功能完整、结果正确优先；一体模块可整体原样迁入，不额外改测；冗余设计和服务可用性专项测试/修复登记后置。验证仅围绕本次功能变化，权威规则见[范围](operations/alert-processing-scope.md)和[AGENTS](../AGENTS.md)。

2026-10-21最新：完整迁移告警/调查及自治能力，playbook/反馈一体保留且专项暂缓，可用性专项后置。[完整性评估](../openspec/changes/restore-alert-investigation-integrity/assessment.md)已完成，现按[实施记录](../openspec/changes/restore-alert-investigation-integrity/execution.md)逐批修复和验证；restore当前5/15，旧R02暂缓、不作功能前置。下文R01及旧“下一R02”为历史交接，不覆盖当前状态。

工作同时交付功能迁移、固定官方文档与源码对照、架构及二开入口梳理。见[官方功能对照](operations/alert-function-alignment.md)与[服务端架构](architecture/alert-processing.md)；文档和源码存在不等于运行或质量已通过。

目标：**告警及后续数据处理服务端**。已有告警输入，经服务端处理后交付API、消息和持久化结果。本轮不建设前端、采集、原始日志检测或独立展示推送服务。

历史[C03-R01](operations/c03-triage-review-only.md)代码隔离与定向部署已限定验收：191项断网测试通过（22项新增、169项既有直接测试），0真实模型/新业务写；仅Agents一次构建、一次替换为19f8f1a5，review_only_v1已配置、worker OFF，七只读挂载/60秒宽限保持。旧14材料表、全部告警字段、12预约/240000预留单位/3unknown、十reader、其他35容器/18卷/134迁移及消息水位保持。首次观察脚本RLS错误与189通过/2夹具失败及恢复均保留。该批为28层运行定义、185 Agents/770运行Py，prompt/lock v5不变。当时下一项为[人审准入卡](operations/c03-review-only-profile-plan.md)R02；现已按[status](../openspec/changes/admit-review-only-triage-worker/status.md)暂缓，不据此启动旧计划，后续调查/知识及full配套结果以新回执为准。

UEBA用法、Fusion阶段、[分诊机制](architecture/triage.md)、[调查每次智能体/模型/工具调用](architecture/investigation.md)及[两套流程评价](architecture/investigation-design-review.md)均已有交接，链图也已本地实施，当前按页首B5→B6汇总已有证据与版本。[逐模块路线](operations/module-review-plan.md)及[完整性修复设计](../openspec/changes/restore-alert-investigation-integrity/design.md)保留原任务与历史成果。源码完整不等于完整功能、自治质量或真实响应通过。

| 问题 | 当前维护入口 |
| --- | --- |
| 我们负责什么 | [服务端范围与M00—M21对齐](operations/alert-processing-scope.md) |
| 分几阶段完成、如何退出 | [服务端迁移路线](operations/service-roadmap.md) |
| 这一批做什么、如何验收 | [依赖迁移计划](operations/dependency-migration-plan.md) |
| 实际做到哪里、下一项是什么 | [PROGRESS](../PROGRESS.md) |
| 官方声明与实际实现怎样对应 | [告警与调查功能对照](operations/alert-function-alignment.md) |
| 当前架构、对象关系和二开入口 | [告警处理服务端架构](architecture/alert-processing.md) |
| 事件关联/调查链图目前是否够用、下一步怎样推进 | [模块评估与最小推进路线](architecture/attack-chain-path.md#module-assessment) |
| B5→B6哪些责任还未收口、阶段发布究竟选哪些文件 | [逐项责任、19文件候选及C2排除](operations/investigation-stage-closeout-20261022.md) |
| Fusion到底做什么，准备怎样共同取舍 | [Fusion功能清单与告警实例](architecture/fusion.md) |
| Incident、Fusion链和调查Chain/Path怎么区分，何时同组、Case何时创建 | [概念/ID](architecture/attack-chain-path.md#concepts)、[四种组合](architecture/attack-chain-path.md#membership-examples)、[调查范围](architecture/attack-chain-path.md#investigation-scope)、[自动化](architecture/attack-chain-path.md#case-automation)、[结论](architecture/attack-chain-path.md#discussion-conclusions) |
| 调查每次模型为什么调用、输入输出、预处理及工具怎样执行 | [逐步输入输出与工具合同](architecture/investigation-preprocessing-tools.md)、[调查流程](architecture/investigation.md) |
| Tool有哪些、怎样配置/执行/测试，第三方SIEM开放接口怎样接 | [工具使用指南](operations/investigation-tools.md)、[精确工具目录](architecture/investigation-tool-catalog.md)、[SIEM接入与测试示例](operations/siem-tool-integration.md) |
| 厂商只有HTTP数据接口，自己设计的Tool怎样接入并证明执行 | [外部HTTP接口与Tool执行验证设计](architecture/third-party-search-contract.md)（仅设计，未实施） |
| UEBA发送什么格式会纳入计算、配置与输出 | [UEBA模块说明与JSON实例](architecture/ueba.md) |
| UEBA、IOC和知识库有哪些功能、怎样调用 | [依赖项简明使用](operations/dependency-usage.md) |
| 变更怎样提案、实施、验证与独审 | [OpenSpec实施规范](../openspec/README.md)、[完整性评估/修复change](../openspec/changes/restore-alert-investigation-integrity/proposal.md) |
| 怎样协作、如何保留原件和数据 | [AGENTS](../AGENTS.md) |

## 需求、分析与证据

| 材料 | 用途与边界 |
| --- | --- |
| [需求原件及阅读版](requirements/README.md) | 完整产品需求不改写；本仓库按用户确认承担服务端子范围，其他要求不计作已交付 |
| [既有模块分析](anal/README.md) | 复用上游源码、输入输出、测试和风险研究；分析覆盖面大于本轮职责 |
| [交接分析版](reference/aisoc/README.md) | 同组分析的交接链接版，保留供对照，不另立一套目标 |
| [环境](operations/environment.md)、[配置与凭据索引](operations/configuration.md) | 21为目标、20为参考、43为现有Chat服务；地址快照与新部署配置分开 |
| [已有证据](operations/verified-evidence.md)、[初始化回执](operations/initialization.md) | 区分20历史smoke、本地静态校验、[21 PG/Redis实测](operations/1b-shared-services.md)、[21 Kafka实测](operations/1c-shared-kafka.md)、[21 API/Fusion主链](operations/1f-alert-chain.md)、[21向量/embedding](operations/1d-vector-embedding.md)、[21五角色网关](operations/1e-model-gateway.md)、[1G受控调查/dry-run](operations/1g-service-baseline.md)、[2A原版核对/成员重投修复](operations/2a-dedup-correlation.md)及待做完整调查/响应验收 |
| [已知问题](operations/known-issues.md) | 上游事实/风险及部署适配，按当前范围选直接验证，不自动生成全量任务 |
| [20部署适配](../deploy/aisoc20/HANDOFF.md)、[1A依赖参考包](../deploy/aisoc21/dependencies/README.md) | 可复用的原件；不是21启动方案或全量安装清单 |
| [保留清单](handoff/retention-map.md)、[交接manifest](handoff/handoff-manifest.json) | 文件来源、变更hash、历史版本和保留边界 |
| [计划迁入来源清单](handoff/migration-source-map.json) | 2个initdb脚本、134份SQL完整顺序、Python服务构建上下文及原测试候选；实际1B迁入见[来源回执](handoff/1b-import-manifest.json)，API/Fusion见[1F来源](handoff/1f-source-manifest.json)，Agents/Actions见[1G来源](handoff/1g-source-manifest.json)，其余按需模块仍待迁入 |
| [知识与模型复用](operations/knowledge-data-reuse-plan.md) | 用户授权已有/旧SOCAI数据与本地4B候选，20/21分担；盘点不等于消费通过 |

2A当前源码在1F来源之上有[单文件差异层](handoff/2a-source-manifest.json)；旧回执不改写，其后[独立身份差异层](handoff/2a-identity-source-manifest.json)已通过所列限定验收，见[回执](operations/2a-source-identity.md)；不外推完整缓存丢失与风险支路。

## 文档口径

范围只在范围文档维护，阶段退出标准在迁移路线维护，批次输入/验收在依赖计划维护，完成状态在PROGRESS维护。其他文档引用这些入口，不另写冲突的“唯一当前路线”或任务完成表。

旧规划、旧工程覆盖表和旧运行回执标为历史参考；源码分析标为参考事实。它们不能扩大本仓库职责，也不能替代真实验收。原始需求、冻结证据、凭据及依赖原件不为统一文字而改写。

2B-01当前新增[风险累计回执](operations/2b-risk-idempotence.md)及[源码差异层](handoff/2b-risk-source-manifest.json)；仅限定RBA重投/并发与所列边界通过，下一项2B-02处理规则实际版本/消费。

2B-02新增[规则回执](operations/2b-policy-versions.md)及[差异层](handoff/2b-policy-source-manifest.json)：限定规则API/PG/实际方法、缓存/恢复通过，当前下一项2C。自动Kafka分诊及持久抑制到3A另验。

2C-01当前新增[IOC回执](operations/2c-ioc-consumption.md)及[差异层](handoff/2c-ioc-source-manifest.json)：本地历史IOC查询与告警冻结结果已限定通过，整个2C尚未完成，下一项2C-02已有上下文。

2C-02新增[PG上下文回执](operations/2c-processing-context.md)及[差异层](handoff/2c-context-source-manifest.json)：现有表中合成材料的只读消费与独立评分通过，整个2C未完成。后续2C-03见下条。

2C-03新增[事件/UEBA来源回执](operations/2c-event-ueba-sources.md)及[操作输入清单](handoff/2c-sources-input-manifest.json)：已有来源不足，真实缺源返回已核，整个2C保持未完成；下一单项[3A-01规则抑制持久回执](operations/3a-triage-entry-plan.md)，常驻worker关闭。

3A-01新增[规则抑制持久回执](operations/3a-policy-suppression.md)和[差异清单](handoff/3a-suppression-source-manifest.json)：83项测试及真实PG/SSL Kafka限定验收通过；常驻worker关闭，下一项3A-02有界真实模型分诊。此前3A-01计划保留为历史输入，不能替代本批实测。

3A-02新增[真实模型分诊回执](operations/3a-model-triage.md)和[操作输入清单](handoff/3a-model-triage-input-manifest.json)：首轮污染结果保留，独立盲测分类及真实模型/账本/API限定通过；完整质量未过，下一项[3A-03缺失风险分语义](operations/3a-missing-risk-plan.md)。

3A-03新增[风险分语义回执](operations/3a-risk-score.md)和[差异清单](handoff/3a-risk-score-source-manifest.json)：184项测试及实际四类输入/一次真实模型通过，缺失/null保持未知，显式零保留。该批之后3A-04完成情况见下条；当时五类context与完整质量未过。

3A-04新增[组织记忆回执](operations/3a-org-memory.md)和[差异清单](handoff/3a-org-memory-source-manifest.json)：194项测试、真实PG/API读取与故障恢复、一次模型消费及重启回查限定通过。两枚A/B组织记忆reader key保留；当时其余四类context仍401，技能后续见下条。

3A-05新增[技能读取回执](operations/3a-tenant-skill.md)、[JSON](operations/3a-tenant-skill.json)、[差异清单](handoff/3a-tenant-skill-source-manifest.json)及[本地交付核验](operations/3a-tenant-skill-local-verification.json)：347项测试、真实API/生产选择及一次实际模型消费1572/105/1677 tokens、重启回查限定通过，v2采用文本/工件在当前头v3后保持；3操作key停用，两枚独立settings:read reader保留，原org身份保持。技能与组织记忆reader权限独立；该批当时KB/处置/身份三类context仍401，KB后续见下条，原回执保持。

3A-06新增[KB读取回执](operations/3a-kb-read.md)、[JSON](operations/3a-kb-read.json)、[差异清单](handoff/3a-kb-read-source-manifest.json)及[本地交付核验](operations/3a-kb-read-local-verification.json)：236项测试、真实API/PG全文检索/保守cutoff、实际nonce块与事务工件及重启回查限定通过。一次实际模型1955/140/2095 tokens，prompt7861字符未截断；KB1已提供但模型未引用标记，不计引用质量通过。两次模型前预算失败与检查点恢复保留，只有一次真实调用；6条合成KB行不是实际SOP或既有向量索引质量。3操作key停用，2枚独立knowledge_base:read reader保留，原org/skill四枚key保持。该批使用十五层定义，当时处置/身份两类context401与整体质量未过；处置后续见下条。


3A-07新增[近期处置回执](operations/3a-dispositions.md)、[JSON](operations/3a-dispositions.json)、[差异清单](handoff/3a-dispositions-source-manifest.json)及[本地交付核验](operations/3a-dispositions-local-verification.json)：最终396项测试、60项显式HTTP检查、真实API/PG排序/隔离/cutoff、实际采用块/账本及重启回查限定通过。三条个人意见进入7355字符prompt，一次模型1779/130/1909 tokens、needs_review/自报0.65，未精确提及note/反馈ID，不证明因果采用或质量；初394项通过后独立进程导入环已修复并补两项测试，最终Agents镜像只读验证通过，模型未重测。3操作key停用，两枚新alerts:read reader保留，原六枚reader保持；该批使用十六层定义，当时身份reader401及整体质量未过，身份后续见下条。


3A-08新增[身份读取回执](operations/3a-identity-read.md)、[JSON](operations/3a-identity-read.json)、[来源清单](handoff/3a-identity-read-source-manifest.json)和[本地核验](operations/3a-identity-read-local-verification.json)：496项、62项HTTP、真实图源/读取/采用块/账本及重启限定通过；一次模型1781 tokens、prompt6931字符，不外推历史/授权/质量。失败脚本从矩阵后恢复，无重复输入/模型。五类reader接通，该批使用十七层，当前完整命令见[21说明](../deploy/aisoc21/README.md)，受控复验后续见下条，常驻worker仍关闭。


3A-09新增[受控复验回执](operations/3a-triage-admission.md)、[JSON](operations/3a-triage-admission.json)、[来源清单](handoff/3a-triage-admission-source-manifest.json)和[本地核验](operations/3a-triage-admission-local-verification.json)：三次真实模型5223 tokens、分类3/3，p01理由仍有时间/授权错误；51项显式HTTP与真实broker/PG替身审计分别留证，提交/重投/来源恢复缺口阻止worker准入，完整质量不通过。该批无运行改动/重启、当时十七层；后续修复见下条。

3A-10-01新增[持久确认与坏消息回执](operations/3a-triage-durability.md)、[JSON](operations/3a-triage-durability.json)与[来源清单](handoff/3a-triage-durability-source-manifest.json)：143项测试、26项显式HTTP、真实SSL Kafka/PG及Agents重启回查限定通过，7次broker发布/8次交付、4次模型方法替身、0真实模型。仅更新Agents并增加第十八层，十枚reader保持、三操作key401；该批当时冷重投/缓存来源/SDK预算仍未修，后续保护见下条，不开放常驻worker。

3A-10-02新增[首次结果与重投保护回执](operations/3a-triage-recovery.md)、[JSON](operations/3a-triage-recovery.json)和[来源清单](handoff/3a-triage-recovery-source-manifest.json)：207项测试、55项显式HTTP，3次broker发布/7次交付/3次方法替身、0真实模型，普通live路径的同worker保存恢复、fresh复用、跨进程认领及unknown停止限定通过。仅更新Agents，当前十九层；原十枚reader凭据保持、三操作key401。负seq增量cursor实际422、SDK预算及完整质量未过，下一3A-10-03见[总计划](operations/3a-worker-reliability-plan.md)。

3A-10-03-01新增[请求/cursor回执](operations/3a-triage-request.md)、[JSON](operations/3a-triage-request.json)与[来源清单](handoff/3a-triage-request-source-manifest.json)：189项相关测试、71项显式HTTP，生产triage SDK默认retry0/45秒、整次45秒截止，负cursor从422修至可直接增量读取。仅API/Agents更新并重启，当前二十层，14表旧材料与十枚reader保持、三操作key401；0输入/模型。整个03及worker准入仍未过，下一3A-10-03-02持久租户额度、积压和停止恢复。

3A-10-03-02新增[持久额度/停止回执](operations/3a-triage-budget.md)、[JSON](operations/3a-triage-budget.json)与[来源](handoff/3a-triage-budget-source-manifest.json)：263项测试、137项HTTP、6次发布/14次交付/5次HTTP模型替身开始、0真实模型。独立表预约及claim原子、跨进程三类上限、积压同group恢复、10秒stop及未知不重调限定通过；5份预约合计100000预留单位非usage。当前21层，只更新Agents，旧材料和十reader保持，三操作key401。三未知预约及A积压保留，完整准入/质量仍未过；下一为准入剩余阻塞复核。

## 3A-11-01最新只读准入复核

3A-11-01只读准入复核已完成，见[回执](operations/3a-admission-review.md)：旧p01时间/授权错误未被indicator gate识别；常驻Agents审批提案guard实际True且缺Kafka bootstrap/TLS，旧调查工具身份仍缺。三未知预约及A积压保持，0模型/消息/offset提交/运行改动；完整准入未过。下一[3A-11-02配置补齐](operations/3a-triage-admission-config-plan.md)，保持worker禁用，然后单独修提示词/复验质量。

审批提案guard未显式禁用、常驻Agents缺Kafka bootstrap/TLS；worker关闭使其未作为常驻消费者运行，隔离探针通过不证明这些环境项已接。五reader不替代旧工具service身份。旧回执保持；本批无运行改动，三未知预约及A积压不清理/重调。

## 3A-11-02最新配置验收

3A-11-02常驻分诊配置补齐已限定验收，见[回执](operations/3a-triage-admission-config.md)：仅Agents同镜像重建一次，新增四项环境值，复用原只读CA；审批提案guard现False、Kafka SSL/主机名校验及六组offset读取通过。旧14表/三unknown/A积压/十reader/其他35容器/18卷/134迁移保持，0模型/消息/提交。当前22层、19源码层，worker仍OFF；下一[3A-11-03理由提示词修复](operations/3a-triage-reasoning-plan.md)，完整准入/质量未过。

当前补齐的是transport及审批提案禁用，不含常驻topic/group/DLQ项目映射；五reader与通用工具身份仍分开。A积压与unknown不清理/重调；p01理由仍未修，不能将配置就绪当质量或常驻准入。

## 2026-10-20已有迁移审核

[审核报告](operations/migration-review-20261020.md)及[机器摘要](operations/migration-review-20261020.json)区分固定来源正确与业务语义缺陷；建议先修Fusion持久交付/关联恢复和分诊材料投影，原提示词计划待实施。只有审核/文档更新，没有运行改动；旧回执保留，topic/group缺失误判由新审核勘误。

## C03-02D-02质量失败受控收尾

[回执](operations/c03-triage-validity-quality.md)、[JSON](operations/c03-triage-validity-quality.json)、[证据清单](handoff/c03-triage-validity-quality-evidence-manifest.json)与[原执行卡](operations/c03-triage-validity-quality-plan.md)/[恢复卡](operations/c03-triage-validity-quality-recovery-plan.md)分别保留。两次回复4081 tokens，case01过门、case02分类与时间理由未过，case03/04未发；技术收尾不等于质量通过。下一先另冻人审profile新准入计划，尚未实施或验收；原自治分类/理由质量及常驻准入未过，worker OFF。原C03质量硬门和本批判据保持，C04/C05调查/知识及后续响应仍待逐批验收，整体迁移未完成。

- [调查功能真实本地实测与逐步案例](operations/investigation-functional-20261021.md)：原默认四节点、Router领域分支、Deep每轮模型与工具；明确成功、兜底、部分结果和两处未发布的最小修正。

- [攻击链与Attack Path接入调查计划](operations/attack-chain-path-integration-plan.md)：保留原规划；[本地实施回执](operations/attack-chain-path-local-20261021.md)已包含真实图、模型消费和Run输出，未发布21。

- [调查阶段功能与版本交接](operations/investigation-stage-handoff-20261022.md)：B5→B6已有证据、已部署与本地差异、本地版本及剩余范围；不代替原回执或整体验收。
