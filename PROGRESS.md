**2026-10-29 云端保存授权：** 用户要求完成审计后推送云端，提交当前V2前端成果及功能审计到 `origin/codex/functional-analysis`。9项问题仍未修；独立报告复核限定ACCEPT、OpenSpec归档及strict all9/archived36通过。另一图谱change随当前前端版本保存，但保持未归档状态；后端/部署/模型测试工作不混入。此前“无提交/push”均指各批当时阶段，实际同步以Git和远端核对为准。

## 2026-10-29 V2功能审计（未修改页面）

[逐区域盘点及9项问题](docs/design/frontend-functional-audit-20261029.md)：主阅读跳转已接通，操作闭环仍有4项P1、4项P2、1项P3。浏览器验证代表链路、Unknown弹窗、筛选重置/刷新、时间控件和历史图谱；VM运行实际源码858视图/1095链接无缺目标，但操作反例暴露启动Run不互通、跨来源成员与Run不一致、活动错误归属等。65已有测试通过；36个V2文件hash未变，无浏览器业务编辑、远端/模型/部署/提交。本轮只保存审计结论，问题未修，另一图谱change保持。

## 2026-10-29 V2 Case 数据整合

全部19 Case同入口保留，7个AiSOC Case靠前、12原设计可筛选；已保存13Run的192过程/90工具/108工件目录/11报告统一案件材料入口。20原告警事件关系新增3组（2/2/1），无关系不补造；Case/事件双向来源校核、错误ID空态、历史Run引用保留。65直接测试/原告警291HTML对照通过，入口与边界见[交付回执](docs/design/frontend-v2-verification.md)。无新后端/模型/部署/提交；原始数据和V1保持。结束独审及归档见consolidate-v2-case-data。

**2026-10-29 Case已有材料补齐：** 用户明确无自动建Case但有材料则补齐。新增3个明确本地集合，原16保留；六源告警/Run归属与单告警输入保持。案件首页逐Run汇总，补资料/工件/当前关系/来源活动，合计92过程/49工具/77工件/5报告；空任务评论附件不造。59测试、浏览器与独审通过，限定ACCEPT/0必须修，63保护文件hash保持。详见[功能分析第19节](docs/design/incident-investigation-page-analysis.md#19-2026-10-29将已有材料补入本地-case-工作区)与[V2回执](docs/design/frontend-v2-verification.md)。本机离线同步，无新远端请求/模型/后端改动/部署/提交push，另一统一图change独立保持。本批OpenSpec已归档并同步1条规格，strict all9/archived34通过。

**2026-10-28 V2业务数据同步：** 用户在字段盘点后授权修改。沿原设计追加21保存结果的3个事件×2成员，六Run补齐92过程（原81）、77工件可读入口（31完整/40节选/6仅目录），保49工具和真实Chain/Path/partial状态。事件管理未知值与重置遗漏经独审发现后已修，52测试及浏览器验证通过，独审限定ACCEPT/0必须修；V1、原告警数据/291呈现及另一统一图change保持。详见[功能分析第18节](docs/design/incident-investigation-page-analysis.md#18-2026-10-28告警流程数据同步到-v2)及[V2回执](docs/design/frontend-v2-verification.md)。仅本机离线数据同步，无新业务查询/模型/重放/后端改动/部署/提交push。本批OpenSpec已归档并同步2条规格，strict all9/archived33通过。

**2026-10-28 V2字段对照续接：** 复用旧九列/90项映射，新增[第17节逐区域对照](docs/design/incident-investigation-page-analysis.md#17-2026-10-28-v2-与告警流程数据的字段对照)。按21六条保存结果核6Alert/6Run/92过程/77工件及49工具；6告警已有3个Fusion组但未进入当前12个样例事件，步骤视图81条与原件差11条是未投影。Chain 2success/3empty、Path 5not_linked；资产/负责人/Case关系与事件管理合同、部分留存分别列出。20及10月21日Case历史单列，不当当前库存。31个V2文件hash保持，独审限定ACCEPT/0必须修；文档change已归档，strict all9/archived32通过。[本批回执](openspec/changes/archive/2026-10-28-reconcile-v2-alert-flow-field-mapping/verification.md)。仅本机原件/源码核对和文档，无页面或后端修改、新业务查询/模型/部署/提交push。

**2026-10-28 统一调查关系图设计：** 已保存[功能分析第16节](docs/design/incident-investigation-page-analysis.md#16-2026-10-28-调查关系图统一设计待接入页面)与会话内可点击样稿，保留左告警/右实体图，增加候选和技术图层、稳定布局聚焦与来源依据。核PG/Neo4j实际数据边界，不补缺失中间路径，不把Case级降级技术当精确告警映射。浏览器关键交互、布局及独立13项窄回归通过，独审限定ACCEPT/0剩余必须修；本轮仅设计，4174未接入新图，无业务/模型/后端/部署/提交push。

**2026-10-28 V2实际Case历史样例：** 新增已创建Case及三告警联合Run，来自本机2026-10-21真实执行回执（测试输入）。5链候选（3外部）、11节点15边路径、16图可达、4阶段、29事件/7工具/4工件/报告、4调用18388tokens。保留源Case与Run归属，当前成员全移走仍可回查；完整性未知、建议与执行分开。36前端测试及浏览器核验通过，独审限定ACCEPT/0剩余必须修；OpenSpec已归档，strict all8/archived30；见[功能分析第15节](docs/design/incident-investigation-page-analysis.md#15-2026-10-28-已持久化-case-的联合调查样例)和[验证回执](docs/design/frontend-v2-verification.md)。本地静态展示，无新业务/模型/后端修改/部署/提交push。

**2026-10-28 V2历史数据填充：** 按用户要求追加20上2026-10-24六条演示告警的真实处理结果，按原三场景整理为明确标识的本地Case，源Case全null、各Run仍为单告警输入。6Run/71过程/34查询/27工件目录/5原文报告，36调用117286tokens，5partial、1分诊关闭。原52样例和6条21记录保留；补来源环境/租户隔离、skipped阶段、无库存实体与元数据空态。32项前端直接测试（含原291告警HTML比较）通过；来源映射见[功能分析第14节](docs/design/incident-investigation-page-analysis.md#14-2026-10-28-aisoc20-历史结果填充)。仅本地静态展示，无新模型/业务请求/后端修改/部署/提交push；结束独审限定ACCEPT/0必须修，OpenSpec已归档（strict all8/archived29）；浏览器回执见[验证记录](docs/design/frontend-v2-verification.md)。

**2026-10-27 V2融合修改：** 用户授权重审并修改，追加要求保留微软式事件/调查基础能力并突出迁移来源AiSOC功能。4174事件现汇总告警判定、解释与关联调查；Case保留案件材料/关系图/协作，突出发现、实际阶段与Deep、查询证据、攻击链/路径、可筛选调查记录及报告响应。原事件战术/时间线/证据统计经独审发现入口遗漏后已接回。25项前端测试与291告警HTML对比通过，8Run×6视图及1280/700px浏览器检查通过；见[功能分析第13节](docs/design/incident-investigation-page-analysis.md#13-2026-10-27-v2-融合修改)和[回执](docs/design/frontend-v2-verification.md)。仅本地V2，原数据/告警模块/V1/冻结交接保留，无后端/模型/生产/部署或新增提交/push；独审限定ACCEPT/0剩余必须修，本批OpenSpec已归档并同步3条规格。

**2026-10-27 前端功能分析续接：** 用户要求将当前进度保存到英文名功能分析分支，明确正文不用英文；本轮建立 `codex/functional-analysis`，保存已有前端 V1/V2、交接与相关设计。已查看4174事件上下文/概览/关联调查及Case AI调查/过程，重申事件汇总告警和基础调查、Case集中呈现AI过程与结果；页面现状、重复区域及首页组织建议见[功能分析第12节](docs/design/incident-investigation-page-analysis.md#12-2026-10-27-v2-页面核对与功能分析续接)。建议仍待讨论，未改页面功能或后端、未调用模型或生产、未部署或推送；本次本地提交结果以Git历史和保存回执为准。

**2026-10-26 V1 冻结与 V2 前端优化：** [版本入口](prototypes/FRONTEND-VERSIONS.md)和[交付回执](docs/design/frontend-v2-verification.md)。原前端/交接包 52 文件及 ZIP 已冻结，4173 保留 V1，4174 运行 V2、状态隔离。事件保留输入与关系汇聚；整个 Case 工作区突出 Run 输入/范围、过程、工具、链图及报告，6 条既有实际 Run 可无 Case 独立打开。原告警 291 次 HTML 比较一致，语法与 18 项定向测试通过，浏览器交互通过；独审限定 ACCEPT/0 必须修。未改后端、调用模型、重放、部署或 Git 提交推送；完整规划与服务端实现不在本批验收内。

**2026-10-25 事件与AI调查划分（仅文档）：** [逐项功能、链图及取数分析](docs/design/incident-investigation-page-analysis.md)已保存，事件16项、调查工作区22项；按输入汇聚/AI实际过程区分，保留Chain/Path/Alert Graph/Blast Radius及同Run样例。20限定只读样例仍有6Run/5Graph/5报告，21引用10月25日已有回执；不能把空链、未关联Case或未接展示当数据丢失。两个微软官方入口重新在线核对；52份原型/交接文件hash不变，未发模型、写业务数据、改后端、部署或提交推送。独审字段修正已落实并最终限定ACCEPT、0剩余必须修；仅文档验收，不追认页面或业务实现。

**2026-10-25 微软事件与Case对齐：** [详细功能与交互分析](docs/design/microsoft-incident-case-analysis.md)及前端工作区已更新，20排除、告警保持。图谱关系有依据、视角扩展不改成员、潜在路径独立；Case任务/管理和按成员关联的调查已落地为本地演示。9项直接测试、291次告警HTML一致性、4份文件SHA、浏览器关键操作及35文件/62链接交接通过；独审限定ACCEPT/0必须修。来源是10月24日官方PDF留存，未宣称在线最新或后台能力；无生产/模型/部署/提交/push。

**2026-10-25 页面讨论原则：** 根据用户要求整理 [后续页面讨论基础](docs/design/ui-discussion-principles.md)，保存已纠正的问题、通用方法、告警已确认语义及仍待讨论范围；在AGENTS和文档导航加入续接入口。此次仅总结文档，不修改原型、交接包数据、后端或运行环境；相似历史只记录候选方向与最近5条功能，检索合并交后端。

**2026-10-25 前端整目录交接：** 已整理 [交接目录与打开方式](deliverables/aisoc-frontend-handoff/README.md)，根 index.html 直接进入现有静态前端，guide.html 导航页面/字段文档；附原52样例+6实际处理数据、JSON与只读SQL。11份前端原样复制，29文件/57链接、已有2测试及迁移目录HTTP浏览通过，独审限定ACCEPT/0必须修；file协议受浏览工具限制，未实测双击。原设计/业务服务不改，无远程查询/模型/部署/提交。详细证据见 [交接验证](openspec/changes/archive/2026-10-25-package-frontend-handoff/verification.md)。

**2026-10-24 恢复已确认告警设计稿：** 用户要求原设计和原展示数据恢复，删除21快照等新增页面标签，新增数据可保留。已撤回上一轮页面接入/禁用控件/缺口面板，原52条及既有交互恢复，localStorage未重置。真实字段对照、缺口、SQL及三条新增重放数据保留为离线材料；未再次写库、部署或提交。

**2026-10-24 告警真实取数展示：** 按新授权从20选3条测试告警新身份重放21，3Alert/3Run/20事件/28工件，9调用32667tokens，1待处理+2自动关闭。告警列表/侧栏/四详情页签使用21只读快照；负责人未分配、资产匹配与标签等缺口显式标明，操作写回禁用。事件/Case数据未接。第一条graph partial及预算超额、模型质量未验保留；无服务源码/配置/部署/提交/push。见[回执](docs/operations/alert-ui-replay-20261024.md)。

**2026-10-24 告警反馈规则确认：** 保存反馈选择误报、符合预期的正常或授权行为时关闭；真实威胁/需人工跟进保持原处理状态。人工直接关闭需要额外流程、待定；终态枚举及批量候选范围尚未定。已记录[讨论稿D2](docs/design/alert-ui-data-contract.md#d2-判定和关闭)，仅文档，无UI/API/业务改动或部署。

**2026-10-24 告警UI取数讨论稿：** 用户确认以socai2当前已落地流程为基线、原版参考；已按新版告警UI逐项核模型/写入/API与既有21回执，见[字段与流程讨论稿](docs/design/alert-ui-data-contract.md)。明确状态词表、资产/人员关联、Case单值与成员关系、ai_score置信度、预生成解释及生命周期缺口；均为待讨论，未据此改页面/业务或启动生产查询。

**2026-10-24 告警导航简化：** 预览仅留概览、删除分类并重整告警信息、去掉相似告警入口；Case 弹框双页签、默认关联已有，已有关联禁用新建；告警资产链接指向仅标题的资产占位页。浏览器交互验证通过，纯前端，无后端/部署/提交。

**2026-10-24 告警主表排序调整：** 仅严重程度/告警时间排序，置于第二/第三业务列；方向标识和固定列宽已实现。浏览器五轮双向排序列宽一致，自定义列兼容；纯前端，无后端/部署/提交。见[验证回执](docs/design/security-pages-replica-verification.md#告警主表排序与固定列宽)。

**2026-10-24 告警详情融合：** 四页签、预生成解释、Overview功能、事件/Case提示、资产标签、四卡片反馈及Case搜索选择已落地；顶部发起调查，时间线显示生命周期，响应页保留步骤输入输出并新增响应建议；无Case告警时间更新为最新、主列表默认倒序，相关告警保留等级与时间。纯本地前端，验证见[回执](docs/design/security-pages-replica-verification.md#告警详情融合与逐项修订)，无后端/模型/部署或Git提交。

**2026-10-24 告警“分配给我”快捷筛选：** 主表增加全部告警/分配给我，沿用Alex示例账号及原owner条件；与级别、状态、搜索组合，切换回第一页，其他负责人条件仍可见。浏览器8项观察和独立Node VM窄审限定ACCEPT/0必须修，JS语法通过，见[增量回执](docs/design/security-pages-replica-verification.md#后续逐项适配分配给我)。仅前端，未提交/推送或部署。

**2026-10-24 主表所选告警管理简化：** 用户追加要求后，顶部“管理告警”和“管理所选”删除分类，仅保留状态/分配给/评论；保存保留已有分类，其他工作区和详情原样。浏览器4项观察、JS语法及独立Node VM窄审限定ACCEPT/0必须修，见[增量回执](docs/design/security-pages-replica-verification.md#后续逐项适配主表所选告警管理)。纯前端，未提交/推送或部署。

**2026-10-24 告警主表字段适配：** `codex/security-pages-replica`仅调整告警主表：保留处理状态、删除调查状态/分类、首次末次合为告警时间；类别、快捷筛选、详情及事件/Case内嵌表保持。列设置/时间排序/筛选/实际CSV导出一致，10项浏览器观察及JS语法通过，见[增量回执](docs/design/security-pages-replica-verification.md#后续逐项适配告警主表列)。本批change `adapt-alert-table-columns`；无后端、模型、部署或Git提交/推送。

**2026-10-24 AiSOC安全页面原型已实现：** 独立`codex/security-pages-replica`分支，纯前端模块见[启动说明](prototypes/security-pages/README.md)、[功能来源](docs/design/security-pages-replica.md)和[实际回执](docs/design/security-pages-replica-verification.md)。告警、事件及Case均有列表/详情入口；事件含PDF600页队列，Case另核官方Prioritize两张图，按用户要求不自行扩展相似Case等未说明区域。品牌AiSOC，本地51告警/12事件/12Case；43项浏览器观察、5张截图及源码/Node VM结束独审限定ACCEPT/0必须修。未改后端、生产或其他既有未提交工作，无模型/业务请求、部署、Git提交/推送；OpenSpec已归档`2026-10-24-replicate-security-reference-pages`，同步7条规格，封后strict通过。

**2026-10-24完整官方前端参考文档已下载：** 按用户补充下载Microsoft Defender XDR整本官方PDF，2254页/161192410字节，留本地`.local/references/microsoft-defender-xdr/`。书签及章节起始页标题已核：Case388、告警476、事件639；完整来源/哈希见本地manifest，入口见[复刻清单第7节](docs/design/security-pages-replica.md)。只抽查首页和事件章节，未逐页审读；独立TOC JSON请求TLS失败保持，不影响PDF书签核对。本轮不实施页面或扩展其他模块，分支及其他未提交工作保持，无Git提交/推送。

**2026-10-24安全页面复刻功能整理：** 用户新授权独立前端mock复刻，先整理功能；已建`codex/security-pages-replica`分支，见[核心功能及原图清单](docs/design/security-pages-replica.md)。三组为告警、Defender事件、Case；事件主参考按用户指定链接替换原Sentinel。已对照官方图片和正文，外围侧边栏/模块只留名称；前端实现、构建/预览及交互验收均未开始。独立change为`replicate-security-reference-pages`；未提交/推送或部署，其他未提交内容保留。

**2026-10-24数据与调查重新独立设计评审：** 用户要求不受先前结论影响、不改代码。基于main a82346dd重新核需求、设计和源码，见[详细评审及双方意见](docs/operations/independent-design-review-20261024.md)。总体方向合理；数据线应先审定可见证据与标签的关系、补配对评价，非法输出MCC虚高经纯内存反例重现；调查线发现可选正文异常阻断整视图、完整messages预算与视图预算不一致，版本分歧粒度及模型增量价值另列建议。未将待实现入口/Case等判成设计缺陷，未改代码/测试/配置/原设计，评审未调用模型、访问业务服务、写湖或部署；用户随后要求提交并推送本次评审与两处引用，其他未提交材料保持。

**2026-10-24数据/调查已合并并统一审计：** main5c1202b5包含数据评估cec5ea98和调查469e9467，双方源码/测试保持、旧入口不变；见[总审计与数据湖协作](docs/operations/data-investigation-integration-audit-20261024.md)。数据96/39通过；新调查Agents85/API8通过；合并工具112通过但同一IPv6文本测试3子项失败，不能报全绿。另有Python3.11 Path.is_junction兼容、原MCC/批次冻结及分诊截断待处理。现有网络fixture与单批写湖工具共享，调查继续scope/查询/证据采用/额度，数据线承接准备/期望/评分；M5.2及v4分层/新入口未完成。仅合并与审计，无新模型/业务写湖/生产或部署，20/暂停规划未提交内容保持。

**2026-10-24远程同步与旧工作树清理完成：** 正常项目根目录E:/aisoc/socai2当前为codex/investigation-working；共享代码/文档已推送，远端曾核到32d00ca与本地一致。旧.local/worktrees/investigation-working已用Git安全移除；382份验证原件和171份冻结原件迁至根.local/verification与.local/versions，逐文件hash保持，5个可再生缓存删除。Windows本机适配只在被忽略.local/windows-local，原Windows分支94bb52f保留且未推送。其他机器从[调查协作入口](docs/investigation/README.md)读取设计/进展/问题，后续正常合并main/其他分支；本轮无功能、模型/业务测试或部署。此记录随后随正常提交同步，最新提交以分支log为准。

**2026-10-24正常目录与跨机器协作（最新）：** 调查分支已回到普通项目根目录E:/aisoc/socai2；Windows适配复制到被忽略的.local/windows-local，Windows分支原提交保留。代码/设计/进度/已知问题/公开回执纳入Git并按用户要求推送调查分支供团队拉取评审，从[统一入口](docs/investigation/README.md)阅读；后续正常合并main/其他目标分支，不在.local下开发活动分支。旧工作树在确认远程后清理，私密原始材料保留本机且不作为阅读前提。当前仅整理交接，无功能实施/业务模型测试/部署。

**2026-10-24调查严格版本隔离：** 用户明确两个互不影响的版本线；新实现移至Agents/API各自app/investigation_v2包，撤出旧API注册并恢复旧测试，已跟踪旧services文件无差异。先API新8/旧51通过，再迁Agents并85项直接合同通过；新v2 HTTP入口仍未接入，不冒称历史真实回执验证新路径。旧版/Windows/生产不改，调查本地提交已授权，暂不push/部署。见主设计1.10与实施记录顶部。

**2026-10-24调查Git保存授权与核对：** 用户明确调查设计、功能、测试及非私密回执须统一在`codex/investigation-working`本地提交；此前不提交要求针对Windows本机工作，不覆盖调查。当前保存D1—M4限定成果、M5.1及M5.2未完成增量、v4/13项对照。提交前只补查模型合同15项与问题Deep纯合同9项，均exit0；M5.2专用步骤/循环仍未完成，历史冻结回执不改。不推送/部署，不修改Windows分支，原5/15保持。

**2026-10-24开源到当前的调查改动对照（仅说明）：** 主设计新增第16节，按固定上游34ca18→当前实际→v4目标列13环节，补流程、具体行为/原因/状态证据和两实例；不把原有Deep/Router/CH/账本算新增。独立事实审阅限定ACCEPT/0必须修，静态校核通过；13主题交互对照已核，完整业务分层仍未实施。见[主稿第16节](docs/architecture/investigation-planning-design.md)。本轮无业务代码/模型测试/部署/提交/push，进度停点及5/15保持。

**2026-10-24调查v4分层设计（当前，仅文档）：** 告警分诊/侦察与Case整体调查共用内核，保留20自动处理过程和无Case Run详情；Case新Run继承已核材料，创建/关联与启动独立，领域按需，成员覆盖不再默认最近3条。见[主设计v4](docs/architecture/investigation-planning-design.md)第1及12.7节。实际D1—M4限定通过、M5.1纯合同9项通过；M5.2仅observer增量未测，后续实施先等待本轮方案讨论。未改业务代码/测试、调用模型、访问服务器、部署/提交/push。累计开发tokens不限、单调查有限，OS后置，原5/15及旧失败保持。

**调查M4当前结果：** 2026-10-24 M4限定通过：选定8例原文/采用/可读均通过，23484tokens；其中两例冲突按完整消息/9源码/调用AST等价复用。02开发18回复52185tokens，5个失败原件保持、无unknown/unsettled、费用unpriced。15项直接测试通过，未参与实现者audit_contracts限定ACCEPT/0必须修。仅network_observation.v1/Q1,Q2,Q5，非完整恶意/授权卡或全调查通过。PG临时角色NOLOGIN并撤权；M5待按小步实施，OS后置、无部署/提交/push，原5/15保持。 见[实施记录](docs/operations/unified-investigation-implementation.md)和[机器回执](docs/operations/unified-investigation-m4-20261024.json)。

**2026-10-23调查M4.5预期已固定（历史）：** 用户明确开发调试测试累计tokens不限，持续修复复测无需逐批预算确认；单次调查仍有限额，前批pending8/30000已被新授权覆盖。拟逐个复测原8个语义组合，每个独立test Run沿M3 20000tokens/180秒，请求45秒/2048/retry0，驱动无累计token硬上限；未知不自动重放，失败先定位修复/直接测试，再新版本新trial留证，不清旧Run。原文/采用/可读三层分别达标才过M4，未过不进M5。当前仅文档预期，尚无M4.5实测；见[实施卡](docs/operations/unified-investigation-implementation.md)。原7回复/15042tokens失败、第8未测、19文件冻结及旧unknown保持；生产额度不改，OS后置、无部署/提交/push，5/15保持。

**2026-10-23调查M3限定完成（前批停止位置）：** 先12项纯状态通过，再4项真实PG通过，最后9项gate及1次真实HTTP通过；1匹配、3事件/6工件独立读回hash/UTF-8/关联正确，实际模型0。两处审阅问题先修后测，最终独审限定ACCEPT、0剩余必须修项，见[主回执](docs/operations/unified-investigation-implementation.md)及[M3摘要](docs/operations/unified-investigation-m3-20261023.json)。Run总量在原子snapshot分列opening triage/stage/unknown/unpriced，不回写旧计费/状态；测试Run running不代表最终调查完成。临时API已停，PG测试角色NOLOGIN并撤权，CH reader保留。当批M4、调度、M7 manifest、M8入口/读取projection与OS后置，无部署/提交/push，原5/15与旧失败保持。

**2026-10-23调查数据、M1与首M2工具已通过（前批停止位置）：** 用户确认CH先、OS IOC后，先D1/D2/D3通过，再M1范围、M2查询，五块各8直接共40项＋旧51兼容通过；真实3湖事件/1告警/2消息精确关联，再5次HTTP查询/4认证反例通过。M2逐条身份/原文hash/微秒半开窗口与真实来源一致，M1/M2独审限定ACCEPT0。临时API已停，writer INSERT撤回、reader保留；新账号仅表级权限，未改共享row policy。当批未发模型或持久Run、未部署/提交推送，M3以后及OS未启动；后续以顶部M3记录为准。见[逐步记录](docs/operations/unified-investigation-implementation.md)。独立调查树、原5/15与旧失败保持。

**2026-10-23统一调查M0来源盘点与工具数据规划（前一阶段）：** 用户已授权逐块实施、逐块测试，又要求工具影响设计先讨论。[逐步记录](docs/operations/unified-investigation-implementation.md)已固定M0/M1预期；真实只读核15字段和旧合成事件1行，缺外联目标，不能代替新场景。main已fetch到`7ea813a`，仅文档更新；现测试工具仍只有告警/结果链，没有CH历史记录或OS夹具写入。建议复用CH事件链补同批告警/来源UUID/绝对窗口，首工具逐条可追溯查询，OS IOC另步按需，详见[规划](docs/architecture/investigation-tool-data-plan.md)。当时M0未放行，M1及后续代码未写；探针权限/别名错误已记录并修正，旧工具失败未追认修复。原5/15、旧质量/unknown保持，当时无业务写入/模型/部署/提交推送。

**2026-10-23调查方案重新审计及v3修订（仅文档）：** 在独立`codex/investigation-working`工作树、main基线`3fa4be3`修订[唯一设计主文档](docs/architecture/investigation-planning-design.md)：行为性质与授权分开、控制指令与来源正文分开、结论覆盖与关联补查分开，允许小模型按问题组分析及必要综合；明确调查阶段共享额度/Run总成本、热读冷读与通知同版，以及有用判断/安全交付两门和成本记录。第12.6节首场景策略卡仍为候选、来源未核，未启动M0实施、业务/模型测试、生产或部署；Windows工作保留原目录，无提交推送，原5/15及旧失败保持。文档复核与静态结果见原change audit/execution，不代表业务验收。

**2026-10-24数据评估审计与合并授权：** 用户要求保存[分支审计](docs/operations/data-evaluation-audit-20261024.md)并合main。实跑96测试/39子项通过；复现非法分类MCC=1.0与完整配对未锁定，E1关键输入截断仍待讨论。按阶段成果保存，不声称修复或真实模型/查询质量通过；不发模型、访问生产、写库或部署/push。实际本地Git合并另记回执，20展示与暂停规划工作保持。

**2026-10-23数据与评估E0本地完成：** 在`codex/data-evaluation`隔离工作区接上72条/36对四分类语料答案隔离、原评分器离线复用及原工具轨迹核对，见[设计](docs/operations/data-evaluation-design-20261023.md)和[回执](docs/operations/data-evaluation-execution-20261023.md)。79测试/39子项通过；费用unknown问题独审发现并补测修复，限定ACCEPT、0剩余必须修项。旧10模型提议/8执行（6不可用2错误），8份返回均见后续请求记录；不证明成功查询或语义采用。E1—E4未执行，登录合同改动先讨论；生成证据在已忽略.local，0新模型/业务查询/业务改码/部署/提交/push，主工作区未覆盖，原5/15保持。

**2026-10-24本地提交授权：** 用户要求将已完成的迁移收尾做一轮Git commit，随后继续规划设计。提交范围为前轮已审文档/OpenSpec归档及本条授权说明；先复查静态校核与暂存差异，不push、不改业务/运行、不重复独立调查及入湖测试。用户追加呈现相关工作交对应后端模块，本会话不规划或实施列表/筛选/统计/取数对接；实际commit以Git历史/当轮回执为准，下文“未提交”为收尾时快照。

**2026-10-24迁移基线收尾：** 用户取消本会话的测试背景事件入湖/调查联测，说明已由独立调查开发承接；本批不重复、不复验或追认其完成。已收拢[交付范围、原15项核销、版本与后续规划](docs/operations/migration-closeout-20261024.md)：已有Kafka→Fusion→自动关闭/实际调查→持久结果/Markdown、人工路径、full支撑、测试工具及数据库文档按现有证据交付；partial、质量/预算/unknown失败保持。线上v1 API5a1e1fd8/Agents49643b84与本地小修分列，未新查生产。后续先讨论后端查询/列表接入，再按需求选择支撑数据、协作响应和评估/运行专项；不自动实施。migration_closeout_audit结束独审限定ACCEPT/0必须修后已归档`2026-10-24-restore-alert-investigation-integrity`，同步17条主规格；封后独立窄复核限定ACCEPT/0必须修，17条正文/适用版本、15/15限定核销、R02 0/17与原件、33份MD/1028链接及strict均通过；实际见收尾回执和归档audit。无业务改码、新测试/模型/消息/生产访问/写库/部署/Git提交推送。

以下为各日期原始阶段记录；其中5/15、worker OFF、候选未发布或“当前未完成”等只描述当时，不能覆盖10月24日收尾及10月22日v1发布事实。

**2026-10-23数据库字典与页面建议拆分完成：** 按用户要求保留两份主文档：[当前数据库设计与字段字典](docs/integration/v1/table-fields.md)完整解释25表428列（含类型/空值/默认/取值约束/关联/源码依据）；[页面功能与展示要素建议](docs/integration/v1/page-elements.md)直接给出四页90项建议，已去掉原系统对比。SQL/HTTP和独有样例信息合入[取数附件](docs/integration/v1/page-data-mapping.md)。3份旧混合/重复文档已删除，不留跳转占位，引用统一；原实测JSON/审计证据保持。核25表428列顺序、277链接、90名称与七图一致，diff检查通过；完成度枚举纠正为completed/partial。结束独审限定ACCEPT、0交付阻塞，独立核101条约束及完整物理元数据一致。只做文档和静态核查，未新访问生产/调用模型/改表/业务改码/部署或执行Git提交推送。

**2026-10-23告警/调查功能与数据完整审计：** 已形成[审计附件](docs/integration/v1/ui-functional-data-audit.md)与[90项机器矩阵](docs/integration/v1/ui-functional-data-audit.json)，逐项对照原页面依据/必要新增、数据库与JSON路径、实际子项和开放条件。数据46实值/8派生/10空态/21混合/3缺合同/2仅本地；产品O36/N45/H7/X2。16:42 PG只读核六表167列、两例21事件/21工件/3成本行，10GET200但search缺陷仍在；21正文hash/字节与事件关联通过。主文档、图05/07及索引已修组合空值/采用数/工具耗时/报告空态；七图仅功能对照、截图取消。两路结束独审限定ACCEPT、0本批必须修，164链接/51源行/90字段名静态一致；未新发告警/模型、改业务码/表结构、部署或Git提交推送，原5/15及旧质量/预算/unknown保持。

**2026-10-23功能示意使用口径（最新）：** 用户取消网页截图及截图对照；此前未生成网页截图或对照附件，不继续Playwright采集。七份[功能要素示意](docs/integration/v1/ui-wireframes/README.md)均在文首和Mermaid图内标注：只用于说明展示要素及字段对照，不是UI/交互设计稿，后续模块不得按图确定布局、组件、样式或交互。90字段及主文档保持，文字/编号/链接核对通过，本次未重新截图或渲染。

**2026-10-23页面示意附件：** 按用户要求将四个页面拆为[七份独立Mermaid页面示意](docs/integration/v1/ui-wireframes/README.md)，覆盖告警列表/详情、调查列表及详情四页签；填入既有两例实值，90字段逐项与主文档对应，主文档正文保持不变。仅补索引及文档，未运行业务、访问生产、新发模型或部署；字段/链接核对和七图渲染通过，独审限定ACCEPT、0必须修项。

**2026-10-23测试数据工具迁移已实测：** 按用户授权完成场景选择、source-v1 Kafka wire/发送、真实Fusion探针、持久结果观察与本地两例原worker联测，见[逐步回执](docs/operations/testdata-migration-execution-20261023.md)。44直接测试/39子项通过；新3条接线3Alert/6消息/0模型；另2例自动BTP关闭和NR调查partial，6回复26492tokens、29工件及MD可读。测试标记影响推理、21796/20000软预算停止及running/partial展示差异保留待讨论，无本批调查业务改动或新部署。临时进程/隧道停、2新key停用、预算2 responded；Git忽略已核并补可选输出目录，源码/测试/上游可提交。原5/15不变，不自动提交或push。

**2026-10-23调查规划主文档与换账号续接（仅文档）：** 已将完整统一设计整理为[调查模块规划设计文档](docs/architecture/investigation-planning-design.md)，保留四块合同、逐步输入输出、旧模块融合及案例，汇总官方参考与采用边界。新增`codex/investigation-working`专用分支要求和M0—M9模块验收：先明确概念/功能/预期，再逐块实现、测试、留回执，通过后继续；不得等整流程写完再测。第14节包含新账号读取顺序、未提交基线注意事项和可直接发送的续接指令；旧dated正文改为跳转，其他设计入口已对齐。当前仍main，未启动统一设计实施、业务/模型测试、生产访问、部署或提交推送；原5/15与旧失败保持。

**2026-10-23统一调查四块设计（仅方案）：** 按用户允许融合现有编排的最新要求，形成[具体设计](docs/architecture/investigation-planning-design.md)：问题、证据、分析判断、执行状态的字段/所有权，S0—S10输入输出，主分析/Deep/领域能力协作及现有模块复用调整。补清问题验收、整体评估采用、待复核传播、Run级序号/预算、新格式开始标记和同版manifest。独立设计审阅修订后ACCEPT、0剩余必须修项；只做文档静态校核，未改业务代码/配置、调用模型/业务测试/生产或部署，未提交推送。原5/15和旧失败保持，下一步仍为方案讨论。

**2026-10-23页面与数据库统一交接：** 用户要求先交接库表供自行查询、保留HTTP，并只保留最新文档。已合并为[唯一交接主文档](docs/integration/v1/page-elements.md)：四页90项展示信息、21 PG aisoc/public六核心表、字段/JSON映射、关联及SQL、HTTP说明和实测边界。结构按用户要求调整为页面/功能/字段→数据库表→功能取数与六例→已有HTTP→补充说明。删除本轮两份dated旧稿及旧文档快照包，索引统一；实值JSON/SQL及原始测试证据保留。此前41 GET/21工件/8本地用例复用，本次仅核38列及两例8路径，无新生产查询/模型/改表/部署/提交推送；原5/15与旧失败保持。 增量独审限定ACCEPT、0必须修项；不再另存旧文档副本。

**2026-10-23测试数据迁移重新规划（仅方案）：** 已找回原会话、OpenSpec设计和attempt02完成点，形成[修订计划](docs/operations/testdata-migration-plan-20261023.md)。复用已迁原件/旧有效测试，计划补正式Kafka wire与有界发送、结果观察、2例自动分诊/调查，逐项改测后再推进；明确场景/实体/时间与可查数据的区别、Replay/Quality/Purple/Honey用途。尚未实施或发起新增业务/模型测试，无生产访问/部署，原调查小修保持，5/15不变。

**2026-10-23调查小修本地完成：** 按用户逐步测试及缩小范围要求，已修人工前置校验/采用、逐工具留存/结构状态、停止交接，见[回执](docs/operations/investigation-result-handoff-20261023.md)。独立PG串联44 passed、runner/报告18 passed，人工及工具直接用例逐步留证；当前模型2回复2714tokens，交付采用通过，原文遵循缺陷及先2次503未知用量保留。方案已提交5e0ce171，实施增量未部署/推送；后续设计等待讨论，原5/15不改。结束独审限定ACCEPT、0本批必须修项；本地版本与证据已保留。

**2026-10-23调查优化开始按批推进：** 用户已授权先提交后实施，明确小模型稳定输出为约束。方案新增阶段职责、有界输入、程序管理结构及事件后续路线；首批沿restore完成结果一致与停止交接的设计、本地直接校验和结束独审。当前仅准备实施基线，尚未新增业务修正/验证或发布；原5/15及旧失败保持。

**2026-10-23事件级及跨事件分析研究（仅方案）：** 用户要求参考主流安全产品评估必要性。已核本地入口/分组/图上下文与Microsoft Defender XDR、Sentinel、Security Copilot、CrowdStrike Falcon、SentinelOne官方资料，见[研究](docs/architecture/incident-analysis-product-comparison-20261023.md)。当前有Case多告警和跨Incident候选检索，缺持续事件整体研判；建议事件结果→增量更新→候选关联验证，自动合并/Campaign后置。明确微软Incident cases Preview、Endpoint AIR 2026-09变化及Falcon共享上下文调查Pre-beta。统一证据材料供主分析，补查/领域分析可组合；仅保存文档，不据此启动实施、业务测试/模型/生产访问/部署，原5/15及旧失败保持。

**2026-10-23调查优化方案已修订保存（未实施）：** 根据用户“不是执行，是方案保存”，将本轮审核意见融入[原方案](docs/architecture/investigation-product-engineering-roadmap-20261022.md)。首批聚焦结果一致、停止交接和已有C2取舍；第二批校正查询语义并依真实字段选择一个场景；第三批推广共享结构与扩展能力。补参数来源、API实际时间窗口、认证事件类别/结果缺口、人工校验顺序、逐次工具留存、Router未知结论及汇合、有限验收材料。仅保存文档，不启动方案实施或新业务测试/模型/部署；原5/15、v1运行及历史失败保持。

**2026-10-22两个暂停项目恢复：** 用户要求继续并逐步记录；测试工具attempt02三条新输入真实入口/Kafka/Fusion/PG通过，3Alert/new/无Case、6消息、关联Run0/模型0，隔离topic/Redis前缀，本地进程已停。原8离线＋2替身结果复用，attempt01及一次source_event_ids观察假设失败保留；产品建议已补v1已上线和两例数据事实，未实施未选定方案。见[逐步记录](docs/operations/two-projects-resume-20261022.md)、[工具回执](docs/operations/testdata-tools-20261022.md)。resumed_projects_end_audit结束独审限定ACCEPT、0本轮必须修项，选定版本与逐步记录已留存；原5/15/旧unknown预算/质量失败保持；无业务源码/部署配置修改、Git提交推送，生产v1维持原授权状态。

**2026-10-22 v1两例落库及后端数据盘点：** 用户授权正式服务跑1—2例后，已通过raw Kafka新增2条合成告警：例1自动BTP0.95关闭（3事件/7工件/2033tokens），例2自动NR0.85升级调查（18事件/14工件/29755tokens，graph partial）。21工件正文的UTF-8字节/hash均通过，21份event关联完整；成本3行共8回复31788tokens，全部unpriced。22:56真实PG补查生产tenant总计3Alert/3Run/36事件/35工件（含旧发布canary），选定25表428字段/实际约束已留存；23:09实际只读执行后端SQL9个SELECT通过。见[后端盘点](docs/integration/v1/page-data-mapping.md)、[两例回执](docs/operations/service-v1-functional-20261022.md)。graph_step仅node/无输入输出hash，工具200字符preview、prompt副本截断、seq并非严格写入游标已明示；不能宣称所有步骤原文完整或质量通过。原5/15、旧unknown/预算保持，无新部署/业务改码，v1_two_examples_audit限定ACCEPT、0本轮收口阻塞；资料包 `.local/releases/stingaisoc-backend-integration-v1.0.0-data-inventory-20261022.zip`（94331字节/26项）已生成，124链接/3锚点/7JSON、diff/OpenSpec strict通过，旧包保留。

**2026-10-22 v1.0.0服务已发布：** 用户授权开启自动分诊/调查、沿用模型并新建独立生产租户。21 API5a1e1fd8/Agents49643b84已定向部署并healthy/ready，fused常驻订阅已附着；模型摘要一致，其他13个选定容器元数据保持。生产tenant `f6a5c700-69b8-44fc-8238-609362fb1a9f`，新组 `socai2-agents-v1-prod-20261022` 起点30/32/39。单条新raw Kafka合成告警自动分诊及调查，15事件/14工件/MD读取200、新组追平end；7次回复28216tokens，graph partial/六轮及软预算超限，内容质量未验收。新租户仅1条responded/settled预留，无本批unknown；旧租户/group/unknown/预算、原5/15保持。读[生产接入](docs/integration/v1/production.md)、[发布回执](docs/operations/service-v1-release-20261022.md)及[JSON](docs/handoff/service-v1-release-20261022.json)。未提交/推送Git，未启真实厂商动作。service_v1_release_audit结束独审限定ACCEPT、0本轮阻塞；97链接/2锚点/3段shell语法/6JSON、Raw/Fused及身份、diff/OpenSpec strict通过。服务配套文档包 `.local/releases/stingaisoc-backend-integration-v1.0.0-service-20261022.zip` 已生成，不含秘密。

**2026-10-22后端对接指引v1：** 已按用户“正式Kafka、HTTP告警仅测试”的口径整理[发布文档入口](docs/integration/v1/README.md)，包含各存储连接/库表/认证配置、raw/fused/DLQ合同、告警及调查每一步输入输出、结论/工件/Markdown读取、核心关系与只读SQL。21先SSH超时，恢复后16:02已核远端15容器的生效镜像/端口/配置白名单；补实湖/TI OpenSearch/Redis DB12共享、实际worker关闭及升级0。Agents enrichment仍禁用目标，未将容器healthy当调用接通；未发业务探活。未改业务源码/数据库/运行配置或调用模型/发消息/部署，原5/15、worker OFF、候选未部署及旧失败保持；Raw/Fused模型及身份、4份JSON/86链接/1锚点/2段shell语法、diff/strict通过；backend_v1_doc_audit结束独审及新增配置窄复核限定ACCEPT。文档阅读包保存`.local/releases/stingaisoc-backend-integration-v1-20261022.zip`，包内manifest列文件/hash，不含秘密或业务源码。

**2026-10-22两会话收尾留存：** 按用户要求只做简单收尾，已整理[两个会话的完成项、停点和续接入口](docs/handoff/session-closeout-20261022.md)，并选择性保存相关工具/测试/方案及非私有回执到`.local/versions/session-closeout-20261022/`。测试数据已有8项离线＋2项替身合同通过，真实attempt01在联网前配置失败，修正后未重跑，真实联测和增量结束独审待续。产品工程方案237行最终版本的原独审已完成，现找回限定ACCEPT/0阻塞并补audit；方案未进入实施。未续跑业务测试/模型、部署、启worker或Git提交，原5/15与旧失败保持。

**2026-10-22智能调查产品与工程建议：** 已形成[急需问题、优化设计与扩展路线](docs/architecture/investigation-product-engineering-roadmap-20261022.md)。优先范围/真实资料、证据与结论/报告一致性、停止后的可接手结果；保留三编排，共享四个小合同，沿现有工具/策略按场景扩展，含代码落点、业务例子、分批交付和指标。只是设计建议，不把后续产品化列为当前迁移前置；现有候选已构建但不含旧C2全部修正、未部署，原5/15和旧质量失败保持。本轮未改业务源码/运行或新增模型/业务测试。

**2026-10-22标书需求与迁移评估：** 已核AI SOC2原件hash、正文/表格与三图，形成[详细评估和推进建议](docs/operations/tender-requirements-assessment-20261022.md)及[35子组164条逐项矩阵](docs/requirements/socai2-requirements-matrix-20261022.md)，未继承旧SOCAI完成状态。主链/Markdown基本接通不等于标书完整满足；关键差距为真实数据/调查范围、证据与时序、行为路径、完整RAG及人员/响应闭环；SFT、架构选型与六项成效单列。收尾已纳入本地两候选镜像完成的新回执，下一迁移责任为阶段发布准备与交付，不再要求重复构建。告警筛选和UEBA50条限制仅静态登记；本轮无业务代码/模型/消息/Docker/部署变更，原5/15及旧失败保持。164条原文/569链接/strict/diff核验通过，tender_document_final_audit结束独审限定ACCEPT、0文档阻塞；具体见原change审计，不代表产品验收。

**2026-10-22本地候选镜像及离线核验：** 用户明确授权完整父镜像导出后，已本地构建API5a1e1fd8/Agents49643b84；[实际回执](docs/operations/investigation-candidate-images-20261022.md)记录固定父ID/19清单、层/配置继承，镜像内19hash/编译、7排除项、API385/Agents129导入及4方法通过。两次非root/只读/禁网探针exit0并删除，candidate_images_end_audit结束独审限定ACCEPT、0项本轮阻塞；不重复前批100项。helper修可选字段/显式本地BuildKit/context，三次构建停止及初拒绝后授权保留。OrbStack恢复11既有本地容器；未部署21或启其worker/发模型，5/15、旧质量及unknown保护保持。

**2026-10-22候选组合与构建准备：** [本批回执](docs/operations/investigation-candidate-build-20261022.md)补核21父镜像ID与已发布full bundle/UEBA保持，19文件隔离组合100 passed（Agents55/API45）、router登记通过；API7/Agents12最小context与Docker配方准备完成，candidate_preparation_audit结束独审限定ACCEPT、0项本轮阻塞。7项后置保持父版本，Deep只追加摘要。当前本地Docker未运行，未构建镜像或发布，0新模型/业务写/常驻启用；原5/15与旧质量失败保持。前批缺证/未组合验收记录保留为历史。

**2026-10-22阶段收口与具体候选差异：** [清单](docs/operations/investigation-stage-closeout-20261022.md)逐项映射10项未勾责任，整理API7＋Agents12共19运行文件审查副本；Deep从匹配candidate05的原件仅接链图摘要，7项旧C2/文案差异先不选，原工作区保留。新变体用一个已有离线材料交接用例验证，1 passed；19文件语法及来源检查通过，不代表组合/构建/发布验收。基线采用最近full记录，纯full bundle字节/hash本地缺证；stage_closeout_audit结束独审限定ACCEPT、0项本轮阻塞，仅审收口/源码副本。未发布/启worker/调用模型或写业务数据，5/15与旧失败保持。

**2026-10-22关联/链图模块阶段评估：** [评估与推进路线](docs/architecture/attack-chain-path.md#module-assessment)确认已有相关告警检索、关系上下文、Run工件与基本交付，可以沿B5→B6收口；尚非跨Incident活动关联或行为路径引擎。建议先核原任务责任及候选发布差异，旧C2未终审内容不随整文件自动获准发布；再据业务目标选跨事件关联、Case自动化或行为图二开。只是评估与建议，未扩功能/模型/运行/发布；5/15、worker OFF及旧质量失败保持。

**2026-10-22链/图概念讨论已保存：** 用户要求保存辨析、例子及结论，已补[对象/ID与四项能力](docs/architecture/attack-chain-path.md#concepts)、[Incident/Fusion链四种组合](docs/architecture/attack-chain-path.md#membership-examples)、[调查范围](docs/architecture/attack-chain-path.md#investigation-scope)、[Case/Playbook](docs/architecture/attack-chain-path.md#case-automation)、[结论与未决](docs/architecture/attack-chain-path.md#discussion-conclusions)，并连接Fusion清单、导航和AGENTS。Fusion链内部续组/交付/留存已实现，当前未接后续业务消费；调查PG链与Neo4j Path不复用该链，图关系不是行为因果。只保存当前事实和规则推演，不新增业务实现、自动建Case或验收结论；449个本地链接/新锚点及diff检查通过，concept_docs_final_audit结束独审限定ACCEPT、0文档阻塞。原5/15、worker OFF及旧质量失败保持。

**2026-10-22 Kafka写图真实联合已通过：** 已补齐的Conda环境、本地原Kafka消费者及API连接21 PG/Neo4j，独立topic/group一条消息在分诊入口前prepare成功，当前Alert直接邻域5节点4关系、来源一致；reader写403/读200，原GET另返14可达候选而非确认影响。观察入口主动hold，未提交offset、未建Case/Run或执行模型，临时进程已停；不重跑Fusion或部署/启常驻。累计夹具2条（旧失败1＋成功1），旧失败保持。见[真实联合回执](docs/operations/kafka-graph-joint-20261022.md)，joint_graph_audit结束独审限定ACCEPT、0接线阻塞，5/15保持。

**2026-10-22先补齐本地依赖：** 用户在联合观察前要求全面检查，按API+Agents的56项运行/开发直接声明及必需extras统一解析安装；修缺包/低版本、补Conda动态库，清新环境中克隆的旧项目editable冲突，处理SQLAlchemy追踪插件的本地兼容范围。记录见[依赖回执](docs/operations/local-dependencies-20261022.md)，最终65项离线核验、85项直接合同及pip check通过，未参与实现者dependency_final_audit结束独审限定ACCEPT、0剩余阻塞。未改业务源码、pyproject/lock或21部署；此前Kafka联合attempt2因缺greenlet停止，仅留一条合成PG记录、未发布消息，不改写成通过。

**2026-10-22 Kafka消费入口写图本地接通：** 按用户选择，在Agents读取合法fused Kafka消息后、分诊之前统一prepare；Fusion源码保持，后续Graph/Deep上下文纯GET。独立writer、tenant/canonical ID、review-only/shadow及原提交/预算保护保留；API显式Alert只投当前告警并补真实Case边，修正Case前50截断漏投。用户要求的Conda项目环境已建于`.local/conda-envs/socai2`，85项直接合同通过（新入口24＋既有Agents47＋API14），源码/测试/环境版本保存在本地；[用法与回执](docs/operations/kafka-graph-intake-20261022.md)。本批是替身接缝验证，0新模型/真实broker/业务图写/部署，不将旧真实Case证据移作新入口实证；未参与实现者kafka_graph_audit结束独审限定ACCEPT、0剩余阻塞，16份版本核验及strict/diff通过。原5/15、常驻worker OFF及旧失败保持。

**2026-10-22阶段交接与链图保版：** 沿B5→B6汇总[功能/版本交接](docs/operations/investigation-stage-handoff-20261022.md)及[机器摘要](docs/handoff/investigation-stage-handoff-20261022.json)，分列已部署、本地已验与未终审差异；纠正AGENTS/总计划/导航的过时“链图仅规划”。已补`.local/versions/attack-chain-path-20261022/`的36份选定源码/测试/依赖/回执及manifest/归档，副本与归档字节一致；依赖Git基线，不是独立安装包或已审发布包。已有自动关闭/自动调查/人工与Markdown证据复用，本轮0新业务源码/测试/HTTP/模型/消息/部署，不实施假设厂商Tool。完整change5/15、常驻worker OFF、旧质量失败保持；36文件保版、文档/规格检查通过，未参与编写者stage_handoff_audit阶段独审限定ACCEPT、0剩余阻塞，不代替整体结束验收。

**2026-10-21链/图本地实施完成，暂不发布：** 保原链算法及四Agent/Router/Graph流程，补可信PG→Neo4j投影、Case/Alert查询、模型摘要与三类Run工件。新Case四次真实模型输入均含链图，Neo4j11节点15边，29事件/4工件/Markdown读回200，18388tokens；首轮3.5秒截止导致context不可用的13941tokens结果保原，修后用全新输入，本批共8回复32329tokens。API109通过/7既有livePG跳过，Agents兼容120＋2新用例通过、最终22合同复核（重叠不累加）。详见[本批回执](docs/operations/attack-chain-path-local-20261021.md)及[模块用法](docs/architecture/attack-chain-path.md)。未参与实现者deep_functional_tests结束独审限定ACCEPT、0阻塞；5/15保持，不归档、不部署/启worker/Git提交。

# 当前进度


**2026-10-21外部HTTP接口/Tool验证设计完成（未实施）：** 用户明确重点是厂商已有HTTP数据接口，以及自己设计Tool怎样接入、如何证明正确执行。[设计与样例](docs/architecture/third-party-search-contract.md)沿内部统一查询→原厂GET/POST适配→标准行→ToolMessage，按实际厂商能力映射条件/认证/时间/字段，不要求厂商改API。区分现有SIEM工具复用与新独立Tool，给出手工HTTP、直接Tool、脚本模型交接及按需真实选择四层验证；HTTP200或模型自称查询不作执行证明。6个JSON/12处文件引用、时间示例和OpenSpec strict/diff检查通过，未参与编写者结束独审ACCEPT。只交付设计，0源码/配置/功能测试/HTTP/模型/部署；5/15、worker OFF及旧证据保持。

**2026-10-21Tool使用文档完成，结束独审ACCEPT：** 已补[执行/配置/最少测试指南](docs/operations/investigation-tools.md)、[精确工具目录](docs/architecture/investigation-tool-catalog.md)及[第三方SIEM接入示例](docs/operations/siem-tool-integration.md)。按用户假设场景说明配置位置和适配边界，拆解Elastic/Sentinel的typed参数→统一条件→ES|QL/KQL→HTTP→结果投影；自研检索可直接转JSON，不要求SQL或采集。当前独立connectors服务未迁入，配置发现不证明可查；Sentinel认证/工作区/字段接缝仅静态说明。12个JSON/5段shell语法和92处本地文件引用通过，OpenSpec strict及diff检查通过。仅文档，无新业务测试/模型/HTTP/运行/部署，旧失败、worker OFF及5/15保持，不归档、不Git提交。

更新：2026-10-22。

**攻击链/图接入实施开始（本地，不发布）：** 用户授权按计划实施并用一个新完整告警案例交接逐步输入/输出/读取。保持原算法/三种编排，补定向可信投影、Case/Alert查询、Bundle/模型消费及Run工件；本地接21基础设施，现常驻/正式topic/旧Run保持。只做最少功能与身份测试、一个代表模型案例，复杂可用性后置；当前尚未验证完成，不提前勾完整任务。

**攻击链/图接入规划（未实施）：** 用户要求先规划，已核原查询/图写函数都在，但固定原版和当前Case/告警业务均未自动投影，且Router/Deep未完整消费链/路径，不能称只差开关。[具体计划](docs/operations/attack-chain-path-integration-plan.md)按真实Case/tenant→调查准备阶段定向写图→原链/图查询→实际模型摘要→Run工件/Markdown推进，沿B5/现有OpenSpec，不改算法/合并编排/自动建Case。当前只读与文档，0新业务代码/模型/测试/图写/部署，5/15不变；规划独审ACCEPT、strict/链接/格式检查通过。

**调查功能本地实测已完成一批（2026-10-21，结束独审ACCEPT）：** [逐步案例回执](docs/operations/investigation-functional-20261021.md)记录四个新本地Run、三种路径：78项直接测试通过；14次模型调用尝试/13次可见回复，已知31,995 tokens，Forensic一次无回复/执行与usage未知。Router选Identity/Cloud并交付模板MD；默认四节点交付带Forensic兜底MD；Deep执行7工具后因21,540/20,000停止、无最终narrative。两处原版合同（认证SQL IPv6空值、单项IOC字段）已最小本地修正，各有真实只读查询/服务验证，未部署。UEBA失效连接、Forensic连接错误、空结果/预算/报告质量及缺源后置登记；不重调旧Run、不启常驻，不追认完整调查/质量通过。本地13文件增量快照已保存于`.local/versions/investigation-functional-20261021/`，不含凭据。沿现有OpenSpec2.1/3.1/3.3/3.4/4.1部分成果，原5/15不变、不归档。


**调查功能实测开始：** 用户授权本地运行原四节点/Router/Deep，案例来源均可。现有Router12项、Deep8项通过但模型/部分服务为替身；20仅有已调查Golden样例，不重调。接下来采用公开事件派生的新隔离输入，连接21模型与只读工具，逐步记录实际输入/输出及Markdown；不部署、不启常驻、不改旧Run或复杂可用性专项。具体范围见现有OpenSpec执行记录，未提前勾完成。

**预处理、模型输入输出与工具调用已细拆：** 新增[专篇](docs/architecture/investigation-preprocessing-tools.md)，逐调用列目的/实际输入/输出及采用，覆盖Router首次分诊和四领域、默认四节点及Deep每轮；给出schema、规范化tool_calls、HTTP/认证、ToolResult/ToolMessage示例及静态时序。明确Router无工具循环、Case嵌套alerts不flatten、模型不读取完整state/数据库，通用registry未做完整schema校验；更正认证查询默认168小时与shared schema24差异，旧源码/结果保持。本次0业务源码/配置/功能测试/模型/线上查询/部署，沿原2.1/4.1文档交接，任务状态不变。

**Router及调查方式讨论已同步：** [调查说明](docs/architecture/investigation.md#5-router及full-graph的差异)补开关二选一、准确流程和与原四节点逐环节比较；专业分支各一次领域分析，响应摘要/模板Markdown不等价于完整Forensic/响应计划。与Kafka graph/deep独立、外层固定/内部动态查询，以及“较新能力不代表官方已淘汰旧链”同步到[设计评价](docs/architecture/investigation-design-review.md)、模块计划及OpenSpec记录。本次仅文档，0业务源码/配置/功能测试/模型/部署，原产品完成状态不变。

**调查设计对比已补：** 按用户最新重点，[设计评价](docs/architecture/investigation-design-review.md)比较默认Case四节点与graph/deep的目的、输入/输出、四Agent逐一价值/限制和官方历史依据。固定上游ROADMAP/Case文档/CHANGELOG及模块说明更支持演进并存，不能证明必须同时运行的严格互补双架构；graph本身也能人工启动。结合人工R01/自动C2说明结构化报告和多轮工具都不保证事实质量，不用不同样例tokens做性能排名。当前只读分析，未选择裁剪/合并或新发模型，既有运行及任务状态保持。

**下一模块规划及调查逐调用说明：** Fusion之后进入Agents分诊，已形成[分诊工作卡](docs/architecture/triage.md)，按支持/默认/当前配置、输入实际采用、规则与模型、关闭/升级、输出审计及C1/C2对比交接。按用户补充，[调查说明](docs/architecture/investigation.md)分别展开自动graph、默认人工四Agent、Router/full入口、deep每轮模型/工具参数/来源/采用/终止和审计；原C2还原为首次分诊＋6轮同一deep Agent、4次lake失败及2次知识/提取成功，旧partial/质量失败保持。记录route_to字段消费、单项IOC增强合同和Router bundle/持久边界，尚未修或新实测。当前只读分析/文档，0新业务代码/测试/模型/线上操作/发布，原15任务和5/15保持；下一步先讨论分诊取舍，再按直接差异本地验证、保留版本并阶段发布。

**Fusion阶段总结：可以继续分诊模块。** 已完成职责/输入输出/默认规则说明，复用B1身份与交付、2A独立告警关联、2B风险和2C历史IOC证据，UEBA实际异常→真实Kafka/Redis→Fusion→PG/消息5例本地联合通过。当前无阻断已有告警主链交接的已知Fusion接线问题；外部增强缺源、候选链/算法取舍、仅声明配置及复杂可用性登记后置，不追认全质量或整体change完成。[阶段小结](docs/architecture/fusion.md#六当前阶段小结可以转入下游分诊)、[更新路线](docs/operations/completion-plan.md)。下一模块先看Agents分诊输入/上下文、规则/模型、关闭/升级及审计交接；本次无新业务代码、模型、运行或测试，不发布21，现有本地版本/旧质量失败保持。

**UEBA/Fusion本地真实联合验证已通过：** 按用户最新要求本地运行原源码、借21 PG/Redis/Kafka，运行1c84658ebb88。三个新实体各用原BaselineService准备30样本，原Kafka消费者实际生成medium/high/critical（3.4903/4.5227/6.4891），经真实异常消息→Redis缓存→5条真实告警保存/发布。无信号0.656/0.15；三档分别0.726/0.45、0.796/0.75、0.856/1；OFF控制回基准。真实PG severity=high/status=new及priority1/risk0.5保持。5专用topic/3新group、3基线最终count31、3异常/5告警，无正式topic/旧unknown/模型，两个本地进程已停止。[对照说明](docs/architecture/ueba.md#5-本地真实联合验证异常带来了什么改变)、[真实回执](docs/handoff/ueba-fusion-joint-20261021.json)。本地验证后保留版本，按阶段统一发布；本批未部署21、未改常驻开关。原18项内存边界证明继续保留，不改写旧证据或勾整体change完成。

本批结束独审ACCEPT；本地验证版本保存在`.local/versions/ueba-fusion-20261021-1c84658ebb88/`，含代码快照、测试环境版本及manifest。仅本地保留，不自动Git提交/推送或部署。

**UEBA→Fusion联动例子完成：** 按用户授权，原FusionWorker异常分支→cache→原完整告警评分/交付处理的8例与原10项信号测试共18 passed；基础confidence0.656时medium/high/critical分别0.726/0.796/0.856，anomaly0.45/0.75/1，priority保持1。关闭/无信号/另一tenant或实体不加分，多实体只取最高等级。PG/Redis/Kafka为B1内存替身，不宣称真实broker、成熟异常生成或常驻启用通过；21开关仍false，0正式消息/PG写/模型/部署。[配置及结果](docs/architecture/ueba.md#4-ueba与fusion联动评分开关及实测例子)、[回执](docs/handoff/ueba-fusion-examples-20261021.json)。源码上传21方案被自动审批拒绝未执行，转本地临时venv；首次夹具导入错误已修，业务源码/原测试保持。沿restore 2.1/4.1记录，不勾完整产品任务、不提交。

**raw规范化事件支路暂缓（最新）：** 用户明确交其他模块处理；当前回到已有告警输入后的Fusion功能分析，不展开事件生产/规范化、入湖、检测/提升或派生会话/AI资产。`RawAlert`/`alerts.raw`及告警原正文仍属当前输入，调查读取外部历史事件与UEBA结果继续保留。[范围](docs/operations/alert-processing-scope.md)、[模块计划](docs/operations/module-review-plan.md)及[Fusion说明](docs/architecture/fusion.md)已同步；已有源码/配置/实测保持，本次仅文档澄清，0业务代码/运行变更/新功能测试，不新增或勾选产品任务。

**Fusion进入功能理解阶段：** 按用户最新要求，先解释原模块做哪些事，再共同讨论要/不要哪些功能。[功能说明](docs/architecture/fusion.md)已区分已有告警主链、normalized事件支路、辅助接口，并给出去重/关联/候选链/Case及多类评分的区别和一条告警实例。本轮只读整理，尚未做功能取舍或确定修复/启用项，0业务代码/运行变更/新测试，不以源码存在宣称全功能已启用；B1/full证据复用，change完整任务不勾选。

**依赖项用法交接继续推进：** [简明使用说明](docs/operations/dependency-usage.md)补齐TI/IOC精确查询、PG租户列表、信誉增强和不调用模型的KB检索，UEBA直接复用现有说明及full证据，不改实现或重跑测试。本轮只读确认20原项目PG文档KB表存在但为空，ATT&CK/TI/语义记忆集合存在；未把集合存在当内容/21导入通过，未扩数据规模、导入或历史经验。原TI OS搜索无tenant过滤的边界已记录，当前仅作共享公开情报入口，租户私有IOC用原PG路径。0新模型/业务写/部署，不勾完整change未完项。

**UEBA首项触发合同已梳理：** 用户确认按原码由上游选择投喂，当前不新增实体名单或滚动窗口。[模块说明](docs/architecture/ueba.md)已给出当前共享topic的normalized JSON、预提取兼容JSON及HTTP评分请求，明确实体优先级、数值特征、基线更新和异常输出，以及Kafka event_id/HTTP source_event_id差异。2个文档Kafka样例用原extract直接核对通过、3 JSON语法正确，复用原122+7及full基线/Agents证据，不重跑测试套件或复杂可用性专项；0新HTTP/消息/PG/模型/部署。UEBA→Fusion真实异常加分仍未证，本增量不写通过。继续沿restore 2.1/4.1部分推进，不勾完整change未完任务、不自动提交。

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

**最新范围/当前下一项：** 用户确认完整告警/调查及自动关闭、自动升级；playbook/反馈一体保留不额外改测，可用性专项后置。[完整性评估与修复规划](openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/assessment.md)已严格校验及独审通过：1578原件无缺失，当前功能存在临时限制及阶段/usage、跨入口、上下文组合缺口；4项评估任务完成、11项修复/交付任务未完成，未改运行。旧R02[暂缓](openspec/changes/admit-review-only-triage-worker/status.md)、0/17及五文件/hash保持，不作为功能前置。下文旧“下一R02”保留历史，不变更运行OFF或旧质量失败事实。

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
