# 事件页与 AI 调查工作区：功能划分、展示内容和数据依据

**最新续接（2026-10-27）：** 已查看本机 4174 的 V2 事件与 Case 页面，用户重申事件汇总告警及基础调查信息、Case 重点展示 AI 调查。当前页面表现和待讨论方向见[第12节](#12-2026-10-27-v2-页面核对与功能分析续接)。本轮内容保持中文，保存到 `codex/functional-analysis`；未实施新的页面或后端修改。下文第1—11节保留 10 月 25 日的分析范围与当时事实，10 月 26 日已实现部分以[V2交付回执](frontend-v2-verification.md)为准。

更新：2026-10-25。本文按用户已确认的划分分析：**事件页汇聚告警及调查输入，调查工作区展示 AI 实际开展的分析、进展和交付结果。** 调查工作区指整个 Case 工作区及其中的调查详情，不仅是事件里的“调查”页签。本轮只形成文档，前端、交接包、后端和运行配置均不改。

socai2 是能力基线，20 原版 AiSOC 作只读参考。用户后续“20应该可以访”已恢复20参考范围；之前微软复刻阶段“先不管20”仍作为那一批的历史边界。Attack Chain、Attack Path、Alert Graph 和 Blast Radius 均单独核对，不因页面尚未接入就判定服务或数据不存在。

## 1. 两页最核心的差别

| 对比 | 事件页 | 调查工作区 |
| --- | --- | --- |
| 回答的问题 | 有哪些告警，它们涉及谁、何时发生、为什么关联？ | 这次调查查了什么、得到什么判断、依据是什么、还有什么没查到？ |
| 主对象 | 事件及其成员告警、已有实体和来源材料 | Case 工作上下文，以及选定的一次调查 Run |
| 主要材料 | 原始告警、检测/融合资料、已有增强、关联图、来源证据 | 当次输入、工具查询、模型输出、采用材料、结论、停止原因和报告 |
| 图的主要含义 | 当前已知关联，供人理解和选择调查范围 | 本次运行保存的关系材料，以及实际做出的路径/影响分析 |
| 时间视角 | 事件当前材料与业务发生时间 | 运行开始/结束、步骤时间、材料查询时间及版本 |
| 主要操作 | 查看来源、筛选聚焦、管理事件、创建/关联调查、进入已有调查 | 切换 Run、核查步骤/工具/证据、审阅结果、接手未完成工作 |
| 调查开始之后 | 继续保留告警和上下文，增加调查摘要及入口 | 承载完整分析过程，避免在事件页再复制一套过程与报告 |

这里的“调查前”是页面职责，**不是调查开始后把事件页冻结或清空**。后续新到告警仍属事件资料；是否纳入某次调查，必须查该 Run 的输入。当前也不能保证能还原任意“启动前一秒”的完整事件快照。

事件材料可以包含成员告警已有的自动分诊、Explain 或厂商调查结果。它们是带来源的既有输入，不自动成为“AI 已对整个事件完成调查”的结论。无需为了分两页而隐藏这些信息。

### 1.1 什么才算进入调查

创建 Case、关联告警、分配负责人、收到启动按钮点击，均不证明调查已执行。普通 Kafka Run 也先承载分诊，随后才可能在同一 Run 升级 Graph 调查。

人工入口应核对成功启动回执及后续运行记录；自动入口核对实际升级/Graph 执行记录。只有分诊记录时，显示分诊结果和“未见后续调查记录”，不能仅凭 Run 存在显示“调查完成”。当前样例用 `graph_step` 等记录证明曾进入调查；这不是要求未来所有入口必须使用同一种事件名称。

Case 可以先建后启动；无 Case 的自动调查也可以查看。业务 Case ID、Fusion Incident ID、Run ID 和历史命名为 `investigation_runs.case_id` 的运行目标字符串必须分开，不能为打开自动调查强制补造 Case。

### 1.2 三种状态和几种评分必须并列解释

| 信息 | 实际来源及含义 | 展示要求 |
| --- | --- | --- |
| 业务状态 | Alert/Case 的处理状态；事件管理语义另需承接 | 谁在处理、是否关闭，不由 Run 结束自动改写 |
| Run 状态 | `investigation_runs.status/error/started_at/completed_at` | 本次运行记录的状态；自动路径还可能主要反映首次分诊落账 |
| 调查交付完整性 | `graph_result` **事件**的 `payload.completion` | `partial` 明示部分结果；缺字段显示未提供，不从报告存在推定完整 |
| 调查判定 | 同次 `graph_result` 工件的 `verdict/findings/confidence` | 与首次分诊判定分开；待复核不能改成确认恶意 |
| 首次分诊评分 | `triage_verdict.payload.confidence`，其告警投影 `alerts.ai_score` | 例如0.85按已确认规则显示85；不替换为Graph置信度 |
| 检测、关联和范围评分 | Fusion `alerts.confidence`、Chain `confidence/score`、`blast_radius_score` | 分别解释检测、候选关联、图可达范围，不能统一为恶意概率 |

## 2. 微软产品逻辑与本项目划分的关系

微软传统 Incident 和新版 Incident Case 都承载告警、实体、证据及调查上下文；新版增加更完整的工作管理。因此两页看起来很像有其产品原因，不能把微软直接解释为固定的“先事件、再 AI Case”两阶段。这个两页分工是本项目按用户目标作出的组织方式。[微软事件调查](https://learn.microsoft.com/en-us/defender-xdr/investigate-incidents)、[微软 Case 调查](https://learn.microsoft.com/en-us/defender-xdr/investigate-incident-cases)

微软图谱的筛选、布局和聚焦用于阅读已有材料；潜在传播分析另有数据与权限条件。socai2 可以借鉴“对象→关系→来源→动作”的交互，但不能因同叫 Attack Path 就宣称实现了微软的关键目标传播分析。Windows Security 日志可作为检测来源；本文参考的运营工作区是 Defender/Sentinel 门户体验，不是 Windows 桌面安全设置。

本轮重新在线读取上述两个官方页面成功；页面仍将 Incident Case 标为 Preview，并保留 legacy 体验。详细产品拆解见[微软产品与图谱交互分析](microsoft-incident-case-analysis.md)，该文大部分内容仍基于2026-10-24留存的官方PDF，本轮不追认其他章节全部经过最新在线复核。

## 3. 当前能力按什么证据认定

| 层次 | 已有内容 | 本文如何使用 |
| --- | --- | --- |
| 当前原型 | 事件/Case 列表、图谱、告警、资产、调查摘要、证据与响应、活动；Case任务/评论等 | 页面与交互基线。多数是本地样例/本地保存，不等于后端已接通 |
| socai2 v1 发布及回执 | Kafka分诊/自动升级、Case调查入口、Run事件/工件/报告、链图上下文和用量 | 当前可承接的调查能力；具体实值优先使用10月25日六条回执 |
| 本地后续小修 | 更完整的工具留存、校验和停止交接等 | 标明未随本批上线，不把本地源码全部当作21运行事实 |
| 独立调查 v2 / v4设计 | 问题、证据、分析判断、执行状态；告警侦察与Case调查profile | 后续页面方向。D1—M4限定成果、M5.1合同与M5.2未完成增量，不等于正式入口/完整流程已交付 |
| 20原版参考 | 自动处理详情、Case的investigation/attack-path/attack-chain/ledger/report组织 | 复用展示思想；其API、工件名及部署补丁不能直接套给21 |

**事件层有一个实质缺口：** 当前已核PG流程没有独立的 `incidents` 主表；Fusion分组保存在 `alerts.enrichment_data.socai2_fusion.incident_id` 等关联材料中。原型 `store.incidents` 及 `incidentId` 不能直接当生产字段。事件列表聚合、事件级名称/负责人/状态持久化及成员管理合同尚待对应后端承接；不能用 `aisoc_cases` 偷换事件，也不能把所有告警按时间接近自行分组。[表与关系说明](../integration/v1/table-fields.md)

## 4. 事件页逐项保留什么

下面“保留/调整”为分析建议，不表示已改页面。来源编号对应第9节；其中“已有源值、需事件聚合”与“整项待实现”分开表述。

| 编号 / 区域 | 保留的功能及具体展示 | 点击/操作意味着什么 | 来源与当前边界 |
| --- | --- | --- | --- |
| E01 事件列表 | 事件名称/标识、等级、处理状态、负责人、发生时间范围、告警数量；搜索筛选和预览 | 行预览看摘要，名称进入事件详情；筛选不改变成员 | S1；原型已有，事件聚合及管理字段尚无已验完整后端合同 |
| E02 详情头部 | 名称/ID、描述、等级、负责人、标签、时间、成员数量和处理状态 | 管理事件属性、进入成员及已有调查 | S1；描述为空留空，不自动生成整事件AI结论；事件等级如何汇总需明确规则 |
| E03 所含告警 | 每条名称、等级、发生时间、状态、检测源、战术、受影响对象和负责人；保留来源跳转 | 查看告警完整详情；仅筛选不增删成员 | S1/S2；同租户按明确成员关系取数，不能按Case关系替代 |
| E04 发生时间线 / 攻击故事 | 告警和有来源的观察按发生时间排列；选中项显示来源告警、时间、实体与原文 | 聚焦某条材料，联动图中相关节点 | S2；发生时间 `event_time`，不拿Run处理时间补成攻击行为；MITRE标签不是已验证阶段顺序 |
| E05 实体 / 资产 | 主机、账户、IP、文件等已有对象；类型、标识、关联告警数、已有风险/标签及来源 | 有真实资产ID才进资产详情；原始实体可打开其关联告警 | S2；本批六例原始实体存在但库存关联为0，不能伪造库存标签或把全部对象称为已攻陷 |
| E06 已有上下文 | 告警携带的IOC增强、身份/资产背景、检测/融合理由；每项显示值和来源/查询时间（若有） | 回看来源与已有查询结果 | S2/S6；没有资料、未查、查询失败分开；成员告警的上下文不自动覆盖全事件 |
| E07 已有分诊 / Explain | 成员告警首次判定、评分、解释正文和既有建议，清楚归属到具体告警 | 打开对应告警及解释；请求新Explain时沿已有调用语义 | S2/S3；正文保留，不强拆“待核实”等必填新字段；不将单告警解释命名为事件调查报告 |
| E08 当前关联图 | 告警与实体的节点/边、选中对象信息、关联来源、范围筛选 | 点击告警看详情；点击实体聚焦；点击边看关系类型及来源；布局只改变视觉 | S6；原型图与服务图不是同一数据集；事件级聚合尚未接入，不能直接把Case路径当整个事件图 |
| E09 Attack Chain | 种子告警、查询窗口、候选关联告警、时间、共享实体、距离及关联分数 | 点告警回原告警；点共享实体解释为什么关联；改窗口重新读取当前关联 | S6；已有Alert/Case服务。展示候选链，不代表已证实攻击过程；无事件ID直接接口，不能静默任选一个种子代表全事件 |
| E10 Attack Path / 范围入口 | 有合法Case关系时可引用其关联路径，显示路径归属、来源、节点/边；无Case仍可看Alert Graph | 进入关联Case路径或实体邻接/范围视图，不自动创建Case | S6；Case路径有范围条件，不作为每个事件必有内容；Blast Radius是可达候选，见第6节 |
| E11 概览统计 | 所含告警数量、等级/战术分布、涉及设备/账户、首末发生时间及来源分布 | 点统计回到构成该数值的材料 | S1/S2；需明确去重对象和统计范围。图上临时扩展的外部告警不得悄悄计入事件成员总数 |
| E12 相似 / 关联事件 | 候选事件、时间、等级、共享实体或其他实际关联依据 | 查看另一事件；切换关联视角只是扩展上下文 | S1/S6；当前原型按样例共享实体计算。全库事件检索/合并未接，候选不等于已并案 |
| E13 原始证据与响应摘要 | 原始日志/文件/IOC引用、来源告警、已有厂商处置结果；保留查验入口 | 回原文或已有执行记录；真实审批/执行须对应动作记录 | S2/S5；原型证据审批是演示。AI新增建议和执行细节以调查工作区为主，事件仅关联摘要 |
| E14 活动 | 分配、成员变更、管理状态、创建/关联调查、启动及关闭的实际记录 | 查看谁在何时做了什么，跳到相关Run/对象 | S1/S3/S7；业务活动与攻击发生时间线分开；没有日志不能用当前字段反推历史时间 |
| E15 调查入口与摘要 | 未启动/启动请求中/已有关联Run；Run的范围、时间、状态、完整性及简短结果 | 创建/关联Case与启动调查分别表达；进入选定Run查看过程 | S3；无Case自动Run可直接查看；事件成员的多个Run分别展示，不能拼成整事件单一结论 |
| E16 建议动作页签 | 保留查看既有建议的能力，并标清来源告警/厂商/Run | 进入建议来源或相应调查/响应记录 | S2/S5；建议将AI调查产生的详细建议主位置放调查页，事件只留摘要入口；不复制两套审批状态 |

事件的管理和关闭仍保留为业务能力，但当前原型“事件管理同步关联告警”和“Case关闭不关闭告警”只是已存在的本地交互。未来接后端前应确认级联规则，不能由本分析自动改变或追认该规则。

## 5. 调查工作区逐项增加、调整什么

原型已有基础材料与少量调查卡片，新增重点是让分析过程可核查。以下字段只在真实记录存在时展示；某种编排没有的阶段无需补卡片。

| 编号 / 区域 | 具体展示内容 | 用户要完成的判断或操作 | 来源 / 能力状态 |
| --- | --- | --- | --- |
| I01 调查列表 / Case入口 | Case名称/标识、负责人、状态、成员数、最新相关Run时间与结果摘要；可进入历史Run | 找到要接手的工作，区分无Run与已有运行 | S3/S7；Case管理可参考已有接口，无Case自动Run需要独立可达入口，不混入Case计数 |
| I02 Run选择 | Run ID、已知入口/编排、目标类型、起止时间、执行状态、完整性 | 切换某次尝试，所有过程/报告/工件随同切换 | S3；不是默认拿各表“最新一行”拼接；未存编排名时不根据标题猜测 |
| I03 本次调查输入 | 目标告警/Case、输入摘要、实际纳入的告警ID/原文、时间/实体范围、原始材料引用 | 核对AI究竟拿到了什么，比较Case成员与本次输入 | S3；读 `raw_alert` 等保存材料。当前Case启动路径有界取最多3条，不能声称查遍全部成员；完整冻结范围属于v2方向 |
| I04 执行与交付状态 | Run状态、Graph完整性、结论判定、开始/结束时间、最后记录时间 | 区分正在执行、已停但部分交付、完整交付和业务关闭 | S3/S4；不把 `completed`、`partial`、`needs_review`压成同一个状态 |
| I05 进度 / 最近步骤 | 已记录的阶段、时间、耗时（有值时）、最后完成节点、当前失败点 | 看实际做到哪里，决定等待还是接手 | S3；`graph_step`通常在节点完成时记录，不能据此显示“该节点正在执行”；动态流程不编造百分比 |
| I06 分诊与升级依据 | 初次判定、评分、理由、自动关闭标志、升级/后续执行记录 | 知道为什么进入调查，区分首次判断和后续复核 | S3/S4；同Run可能同时含两者，Graph结果不得静默覆盖首次分诊 |
| I07 阶段分析 | 自动Graph按实际triage/enrichment/investigation/attack_path展示；人工默认Recon/Forensic/Responder/Report按实际材料展示 | 展开该阶段输入、输出、错误和关联工件 | S3/S4；Router是替代路径，不硬套四节点；冷读不保证每阶段完整JSON都存在 |
| I08 Deep调查深度 | 策略、实际轮数、查询方向/转向、覆盖说明、截断、缺失数据、实际叙述 | 看调查是否深入、哪些问题仍缺证 | S4 `investigation_depth`；轮数/`reached_depth`不是完成百分比，也不证明所有查询成功 |
| I09 工具调用 | 工具名、实际参数、窗口/实体、返回摘要或原文、成功/空结果/失败/不可用、耗时与来源引用（存在时） | 看AI是否真正查到资料，而非只在报告里说查过 | S3/S4；v1样例 `tool_call`只有args和最多200字符preview，不能伪装成全量结果；本地完整留存小修未发布 |
| I10 来源与知识使用 | 组织记忆、技能、知识库、历史处置、身份资料、IOC增强的读取结果和实际采用引用 | 区分配置了、读到了、提供给模型、被结果引用 | S3/S4；出现来源工件只证明留存，不能自动声称推理采用或证据支持充分 |
| I11 发现 / 判断 | 原文findings、verdict、confidence及已有依据说明；区分观察、假设、建议 | 核查判断与输入是否一致，进入支持材料 | S4；目前未统一结构化“证据→发现→结论”合同。有文本展示文本，有引用展示引用，不补造引用链 |
| I12 Attack Chain快照 | 同Run保存的种子、窗口、候选链/共享实体、状态、查询时间和来源 | 还原当时提供给调查的关联线索，跳回告警 | S5/S6；与事件当前查询可不同；改变查看窗口不能覆盖Run原件 |
| I13 Attack Path快照与分析 | 同Run路径nodes/edges/source/fallback；实际attack_path步骤、findings和范围摘要（若执行） | 分清服务返回的关系图与程序/模型后来做的分析 | S4/S5/S6；有路径工件不代表该阶段必然运行；无Case可 `not_linked`，不能画假路径 |
| I14 Alert Graph / Blast Radius | 告警邻居、关系类型、可达实体、hop数、类型分布、范围分数、来源与查询状态 | 知道图提供了多大关联范围，打开节点和依据 | S5/S6；不把 `total_affected`显示成已确认受害数量；不是微软传播模型的同等实现 |
| I15 停止原因与未完成事项 | 预算耗尽、超时、工具失败、无数据来源、截断、现有coverage_notes/unavailable_data/error | 说明结果为何不完整，人工接手需要补什么 | S4；错误为空也可partial。建议/缺口若仅在正文中，保留正文，不要求模型新增必填字段 |
| I16 建议响应 | 实际动作类型、目标、理由、风险、是否需审批、参数、来源Run | 审阅建议是否有依据，进入已有审批流程 | S4；`proposed_actions`是建议，图评分触发的规则建议也不是模型确认攻击 |
| I17 执行结果 | 实际执行动作、目标、执行者/时间、审批和结果记录、dry-run标记（有记录时） | 核实做过什么、成功还是失败 | S4及已有响应记录；空 `executed_actions` 不补“隔离成功”；本批未启真实厂商响应 |
| I18 调查报告 | 当次Markdown报告、生成时间/工件版本、partial说明和关联Run | 阅读、复制/下载已存报告，回到证据与过程 | S5；无Case从 `report_md`工件取；不额外调用模型美化或把不同Run拼成一份报告 |
| I19 审计材料 | 按步骤列prompt/response、Graph交换记录、工件kind/ID/hash/字节数及关联event | 审阅实际传入/返回的可见材料、下载原件 | S3/S5；注明截断/缺失，不声称展示模型内部思维或完整重放；正文按权限展示 |
| I20 模型与成本 | 模型、调用数、输入/输出tokens、Run总tokens、实测/估算/未定价分类 | 理解运行消耗和额度停止 | S3/S8；Graph用量可能已计入Run，不能重复加；未定价不显示为免费 |
| I21 协作 / 任务 / 评论 | 人工跟进事项、负责人、期限、完成时间、评论与已有附件 | 分工接手和保存人工意见 | S7；这些是辅助工作管理，不是事件和调查的核心AI差异；原型附件是演示下载，不等于已接上传系统 |
| I22 历史Run对照 / 后续调查 | 查看不同Run的范围、判断、停止原因及材料时间，保留旧结果 | 判断新材料是否值得再调查 | 当前可先并列查看，自动差异分析/继承/增量调查属后续设计；本轮不新增运行或重放 |

### 5.1 打开页面后建议的阅读顺序

先选择 Case 或自动调查，再明确当前 Run。首屏优先放**调查对象与范围、执行/交付状态、当前结果、停止原因**。随后进入分析过程、工具和证据、链图、报告、人工协作。

不必把以上22项都变成独立页签：过程容纳阶段、Deep和工具；证据容纳来源与工件；链图容纳Chain/Path/邻接范围；报告保持完整阅读。成员告警/资产仍可查看，但不再占据调查页的大部分首屏。

### 5.2 当前默认编排不宜画成一个固定流程

自动Kafka主要是“首次分诊→按条件升级同Run Graph→保存结果/报告”；Graph中Deep按实际调用工具多轮展开，达到终止条件可提前结束。人工Case默认四角色与可选Router有不同输出。图上某节点名称存在于代码，不表示该Run执行过；某图工件已准备，也不表示attack_path步骤已执行。

因此进度轨迹按真实事件生成，未执行步骤不显示为失败，缺记录步骤不补完成。`graph_step`没有每步完整输入输出hash时，不能做出每条边都有完整证据的视觉暗示。

## 6. Attack Chain、Attack Path与图谱不能再合并略写

### 6.1 各自真正代表什么

| 能力 | socai2背后逻辑 | 输入与结果 | 页面归属 |
| --- | --- | --- | --- |
| Attack Chain | 从种子告警出发，按PG已有共享实体、时间接近与风险/技术重合，寻找候选相关告警 | seed + window → ranked chain、entity_graph、signature、关联confidence | 事件看当前线索；调查看当次工件 |
| Case Attack Path | 读Case→Alert→Host/User→IOC/Technique等已有关系；Neo4j不可用或无节点时可回退PG有限关系 | Case ID/max_depth → nodes、edges、source、fallback | 合法Case范围的关系路径，可被事件引用；不能把事件ID当CaseID |
| Alert Graph | 以某条告警为对象读取邻接与关联范围 | Alert → neighbors及blast_radius | 无Case也有用；事件展示关联，调查保留本次结果 |
| Blast Radius | 从选定实体按图关系遍历可达节点并评分 | entity_type/id/hops → affected_nodes、类型分布、总数、score | 当前范围探索或Run中的实际范围分析；候选可达≠真实传播 |
| attack_path调查步骤 | 读取/复用上述关系材料，添加范围findings及可能的建议；本地实现包含确定性程序逻辑 | state/context → findings、threat_intel、proposed_actions等 | 调查过程。不是每执行一个步骤就一定调用模型，也不是链图服务本身 |
| Fusion内部链/分组 | Fusion的检测关联及状态结构 | fused元信息、incident_id、内部Redis等 | 事件成员/来源上下文；不能冒充Case Attack Chain API结果 |

Attack Chain算法当前最大3层关联、最多50条候选，分数组成为距离0.55、时间0.30、风险重合0.15。它使用 `affected_users/hosts/ips/assets` 构造实体触达关系，不能只看到 `entities`有值就假定链服务必有结果。没有候选可能来自本次窗口/字段投影/关系条件；必须据实核查，不能直接判定数据丢失或已证无攻击。

Case Attack Path的PG回退可能只有Case、Alert和Technique层关系；source/fallback应保留。知识图谱中节点排列、MITRE标签首次出现顺序都不能证明攻击实际发生顺序。有关联的实体不等于每一个都被攻击，也不等于路径里的每条边都已经被模型验证。[链算法](../../services/api/app/services/attack_chain.py)、[图读取与回退](../../services/api/app/api/v1/endpoints/graph.py)

### 6.2 每块具体展示哪些字段

| 对象 | 已有字段 / JSON路径 | 可读展示与空态 |
| --- | --- | --- |
| Chain整体 | `seed_alert_id/window/generated_at/chain_signature/confidence` | 哪个告警为种子、围绕其发生时间的查询窗口、生成时间、关联程度；signature放详情，不是攻击ID |
| Chain条目 | `chain[].alert_id/title/severity/event_time/score/distance/dt_seconds/shared_entities/mitre_techniques/connector_type/source_event_ids` | 候选告警、时间和等级、为什么关联、相隔多久、来源引用；关联排序与时间排序明确区分 |
| Chain关系图 | `entity_graph.nodes/edges` | 告警—共享实体关系；点击边看可核对的实体依据，不补“入侵/横移成功”动词 |
| Path整体 | `case_id/node_count/edge_count/source/fallback` | 归属Case、节点/关系数、Neo4j或关系库回退来源 |
| Path节点与边 | `nodes[].id/label/properties`；`edges[].source/target/type` | 节点类型、业务显示名、实际属性、关系类型；内部IOC节点ID不直接当IOC值 |
| Neighbor | `neighbors.source/neighbors/neighbor_count` | 当前对象及直接邻居、每条关联；source为空与查询失败不同 |
| Blast Radius | `entity_type/entity_id/hops/affected_nodes/total_affected/type_breakdown/blast_radius_score` | 起点、遍历深度、可达对象/类型和范围评分；文案用“可达/关联范围”而不是“已攻陷” |
| 统一上下文 | `scope/alert_id/case_id/queried_at/query_scope`；每块 `status/source/data/error` | 说明查询对象、时间、截断、Case歧义以及各块结果；不以一个总绿色状态覆盖某块失败 |
| Run快照 | 工件content顶层 `scope/alert_id/case_id/queried_at/prepare/model_summary`，内层对应 `attack_chain/attack_path/alert_graph` | 保留同Run材料及当时准备状态；`prepare`是历史写图回执，不代表当前查看触发写图 |

统一上下文GET中的 `query_scope` 包括 `projection_alert_limit/truncated/case_ambiguous/seed_alert_id/semantics`。当前工件拆分器只复制选定顶层字段，不保证原样保留 `query_scope`；当工件没有该字段时不能事后补画完整范围。保留服务结果和 `model_summary` 也不等于整幅图都进入模型：摘要当前只选有限条目，实际模型可见内容需核对交换记录。[上下文读取](../../services/api/app/services/investigation_attack_context.py)、[模型摘要与工件拆分](../../services/agents/app/context/attack_context.py)

### 6.3 点击不同节点、按钮到底改变了什么

| 交互 | 预期作用 | 不能暗示的行为 |
| --- | --- | --- |
| 点击告警 | 选中告警，显示其时间/实体/来源材料，突出直接关联 | 没有自动加入Case、启动模型或确认攻击 |
| 点击实体 | 看实体属性和与当前告警的关系，可进入已有详情 | 不因被点击成为受害资产 |
| 点击边 | 展示关系类型、来源告警/工件、共享实体或其他实际依据 | 不把无来源的连线称作证据链 |
| 切换事件/关联上下文 | 扩展可见范围，标明哪些是外部线索 | 不改变成员关系、事件数量或Case调查范围 |
| 筛选、布局、分组、缩放 | 改变当前图的可见内容与排布 | 不重新执行调查，不代表后台建立新关系 |
| 改Chain窗口 / 刷新当前图 | 发起相应服务读取，结果和查询时间可变化 | 不覆盖旧Run工件，不声称还原旧时刻全局图 |
| 查看当次Chain/Path | 从选定Run工件读取当时保存的返回 | 不使用今天的查询代替当时输入 |
| 查看影响范围 | 读取选定实体的实际图可达结果 | 不等于扫描网络、验证横移或证实所有节点失陷 |
| 新查日志 / 开始调查 | 明确工具/运行操作，有范围、回执及后续记录 | 不与纯点击展开/布局混在一起；本轮不执行 |

### 6.4 空图需要区分六种情况

| 实际情况 | 合理说明 | 不能写成 |
| --- | --- | --- |
| `empty`且查询成功 | 当前种子和窗口没有返回候选关系 | “链数据丢失”或“已证实无攻击” |
| `not_linked / no_linked_case` | 当前告警未关联Case，因此没有Case路径；已有Alert Graph仍可查看 | “图服务不可用”或“没有任何图数据” |
| Case关系歧义 | 无法唯一确定路径归属，保留实际歧义说明 | 静默选任意Case |
| `unavailable/error` | 查询不可用或失败，范围未知；有fallback时说明回退来源 | 空结果、查询成功 |
| 没有对应工件 | 本次运行未保存该类材料，无法从当前记录回查 | 断言服务不存在或该步骤已执行且无结果 |
| 页面未读取已有工件 | 展示尚未接入，可按Run/工件定位 | 数据库被删、模型没有看到任何上下文 |

## 7. 用现有真实处理样例走一遍

本例是合成告警经真实服务处理的保存回执，不是真实攻击。来自21的2026-10-25 **11:59:33北京时间**观察文件；本轮读取本地留存，没有重新查询21库存或发起调查。[六条重放回执](../operations/alert-reset-replay-20261025.md)

- 告警：`4c71eec2-77da-5b81-b68a-72801d55ea24`，Office启动隐藏PowerShell，主机 `DEMO-FIN-11`、账户 `demo.finance`。
- Run：`d141b0e3-16cc-5a0b-8d7f-35159342efe6`；`run.case_id`保存的是该Alert ID，业务 `alerts.case_id=NULL`。
- 已存告警：`status=triaged`、`disposition=true_positive`、`ai_score=0.85`；后续Graph：`verdict=needs_review`、`confidence=0.75`、`completion=partial`。

| 页面区域 | 该例可以展示的实值 | 应怎样理解 |
| --- | --- | --- |
| 事件成员材料 | 发生时间11:30:16.539577、上述主机/账户、首次分诊TP/85及原文来源 | 仍是该告警材料，不据此给整个事件判TP |
| 运行资料 | Run记录11:40:57开始、11:41:16结束，`status=completed`，总tokens 29025 | 这是Run字段；不能单用这两个时间表示Graph全流程耗时或宣称调查已完整 |
| 最终调查交付 | `graph_result.payload.completion=partial`；同payload的 `status=running`、`verdict=needs_review` | 不将内部state的running当当前仍在执行；展示已存部分交付及状态来源差异 |
| 停止原因 | state中 `budget_exhausted_reason="token budget exhausted (26922 of 20000)"` | 26922是当时停止原因的计量口径，不覆盖Run总tokens 29025；原软额度超出事实保留 |
| Deep过程 | iterations=6、distinct_pivots=3、truncated=true；process_tree/network_connections列为不可用 | 有6轮不等于6轮成功取证；查询失败不等于没有网络活动 |
| Chain工件 | `0809f207-3be5-41d1-a6f3-a8c7801ca2d8`，3795字节；`attack_chain.status=empty`、source=postgres、chain=0、window=24h | 材料已存，返回候选为空；不是工件不见 |
| Path工件 | `3ffb8c17-f946-4896-8db9-a96ce286c64d`，2458字节；`attack_path.status=not_linked`、error=no_linked_case | 没有关联Case路径，不该伪造Case来补图 |
| Alert Graph工件 | `4529f945-e840-47a9-bf2d-d1c7f732422b`，6411字节；`alert_graph.status=success`、source=neo4j，含neighbors/blast_radius | 图材料仍存在；三种结果必须分别显示 |
| 报告 | 同Run `report_md` 6563字节 | 可读已有报告，保留partial；报告存在不代表结论质量通过 |

三个图工件的 `queried_at`均为 `2026-10-25T03:41:00.984949+00:00`。该例Graph state顶层没有 `attack_path`字段；不能因此判定Path工件不存在。应列工件并按各自kind读取，必要时再查state的 `context_bundle.attack_context` 或实际 `threat_intel`，不凭想象拼JSON路径。

首次分诊与后续Graph判定不同，应并列注明阶段及依据。本例 `error=NULL`也不能把partial显示为成功完整。现存工具记录的 `result_preview`和Deep说明已表明资料查询受限，页面应把这种限制呈现给接手人，而不是用一段肯定的“攻击故事”盖掉。

## 8. 20参考核到了什么、值得借鉴什么

本轮只读访问20成功，检查容器名称/镜像/挂载和选定六条测试样例的聚合计数。API与Agents为原版latest镜像，Web为 `aisoc-web:showcase-20261024`；读取容器中展示适配文件SHA256与本地补丁一致。没有启动新Run、发模型、改库或部署。

选定六条样例仍有 **6 Alert / 6 Run**，工件计数为 `graph_state=5`、`report_markdown=5`、`report_html=5`、`llm_prompt=6`、`llm_response=6`。这是限定样例的读取结果，不是20全库盘点，也没有据此证明20当前每个Case的Chain/Path都有数据。

| 20已有展示/源码组织 | 可借鉴的内容 | 接到socai2时的差别 |
| --- | --- | --- |
| 告警“自动处理过程” | 无Case也能展示已做步骤、部分完成原因、工具、发现、建议、用量和报告 | 不强迫用户创建Case才能看自动调查；告警入口保持，完整调查工作区可提供同Run详情 |
| Case Attack Chain / Attack Path独立区域 | 链和图有自己的范围、窗口、节点和依据，不被普通概览吞掉 | 对应本分析I12—I14；事件也保留当前关联入口 |
| Investigation Ledger | Run选择、步骤/agent筛选、相邻步骤说明、工件查看 | 按21实际持久粒度实现，不把源码标题中的“完整回放/每次完整prompt”当验收事实 |
| 自动处理汇总API | `available/run_id/workflow/status/completion/stop_reasons/audit_log/investigation_depth/report_md/model_usage` | 20专用 `/alerts/{id}/automatic-investigation` 是展示补丁，不是21现成合同 |
| 图结果与报告工件 | `graph_state/report_markdown` | 21实际使用 `graph_result/report_md`；按服务与版本适配，不因kind不匹配返回空页就判丢数据 |

20 CaseWorkspace原始源码中有overview、investigation、attack-path、attack-chain、ledger、report入口；本轮读取的是源码及部署适配，不是逐个浏览器功能验收。20旧Case Chain接口与21新Alert Chain/统一上下文也不能混同。参考[20展示回执](../operations/aisoc20-showcase-20261024.md)、[本地展示适配](../../deploy/aisoc20/showcase_api_delivery.py)、[自动处理组件](../../deploy/aisoc20/AutomaticInvestigation.tsx)。

## 9. 取数对照与操作边界

下表的PG基线为21、数据库 `aisoc`、schema `public`。既有表/JSON不保证已在每个API响应中同名暴露。Case/Alert/Run/工件关联保持同tenant；API沿已有身份权限处理。当前原型不直接连接数据库。

| 编号 | 实际来源 | 用于哪些展示 / 关联方式 |
| --- | --- | --- |
| S1 事件与成员 | `alerts.enrichment_data.socai2_fusion.incident_id`；原型 `store.incidents/alerts[].incidentId`另属样例 | E01/E02/E03/E11/E12/E14；真实事件聚合和管理合同待承接，不以Case ID替代 |
| S2 告警事实 | `alerts.id/tenant_id/title/description/severity/status/event_time/first_seen/last_seen/entities/affected_*/source_event_ids/raw_event/enrichment_data/mitre_*/ai_score/ai_summary/ai_recommendations/disposition/assigned_to_id` | E03—E07/E13/E16；同tenant+canonical ID。资产、用户名称按真实关联另查；检测源结合Fusion `socai2_fusion.identity`，不把中转标识必然当厂商 |
| S3 Run与事件 | `investigation_runs.id/tenant_id/case_id/raw_alert/alert_summary/status/error/started_at/completed_at/model_used/iterations`；`investigation_events.run_id/seq/ts/kind/agent/summary/payload/duration_ms/input_hash/output_hash` | E15、I01—I10/I19；先核入口目标，再按同Run读取。`case_id`是字符串且无Case外键，自动Kafka通常为Alert ID |
| S4 实际结果 | `kind=triage_verdict`事件payload；`kind=graph_result`事件payload及同名工件JSON `verdict/confidence/findings/proposed_actions/executed_actions/investigation_depth/budget_exhausted_reason/error/context_bundle/threat_intel` | I04/I06—I17；有结构读结构，字段缺失留缺失；人工四节点的热读结构与持久冷读能力分开 |
| S5 工件目录与正文 | `investigation_artifacts.id/tenant_id/run_id/event_id/kind/content/blob_ref/sha256/size_bytes/created_at` | I12—I14/I18/I19；kind包括attack_chain/attack_path/alert_graph/graph_result/graph_llm_exchanges/report_md等。按event_id/hash核版本，不只凭时间接近拼接 |
| S6 链图服务 | Alert/Case Attack Chain、graph investigation-context、attack-path、neighbors、blast-radius；准确结构见第6节 | E08—E10/E12、I12—I14；事件当前读取与Run历史工件分开；关联图可用不等于因果/完整覆盖 |
| S7 Case管理 | `aisoc_cases.id/title/description/status/severity/assignee/alert_ids/sla_due_at/summary`；任务 `aisoc_case_tasks.title/status/assignee/due_at`及已有Case任务/时间线接口 | I01/I21；主要Case API负责人/期限读写 `assignee/sla_due_at`，不保证与旧 `assigned_to_id/sla_deadline`同步；summary无自动调查总结写回保证。Case成员与实际Run输入分别列出；E14事件活动不能直接套Case记录 |
| S8 用量 | `investigation_runs.total_tokens/total_cost_usd/measured_call_count/estimated_cost_usd/estimated_call_count/unpriced_call_count`；`aisoc_run_costs`按run_id/tenant_id/model的prompt/completion、call_count及各费用字段 | I20；Run总量与Graph增量不重复累加，未计价单列 |

### 9.1 可复用读取入口

以下相对API `/api/v1`。本轮核代码/既有回执，不代表重新逐个调用通过。

| 入口 | 用途与注意 |
| --- | --- |
| `GET /alerts/{id}` | 原告警事实；原文和JSON具体暴露程度核响应 |
| `GET /investigations?case_id={anchor}&limit=20` | 按已知入口目标找Run；并非只接受业务Case；不能凭此自动覆盖所有独立Graph目标 |
| `GET /investigations/{run_id}` | Run摘要、用量/数量等，不是完整Graph state |
| `GET /investigations/{run_id}/events?limit=200` | 首次不带since，以包含负seq；之后可增量，但seq不是严格写入时间游标 |
| `GET /investigations/{run_id}/explain?step={seq}` | 读取focus/前后步骤及工件，不是重新调用告警Explain模型；当前step要求非负，负seq直接读events payload及关联工件 |
| `GET /investigations/{run_id}/artifacts`及 `/{artifact_id}` | 列目录/读正文；自动无Case报告读 `kind=report_md` |
| `GET /cases/{id}/investigations/{run_id}`及 `/report.md` | 有合法Case时的状态代理/报告；与ledger摘要格式不同 |
| `GET /alerts/{id}/attack-chain?window=24h` | 只读按Alert取候选链；返回数据主体，不是统一上下文的外层status封装 |
| `GET /graph/investigation-context?alert_id={id}&window=24h`或 `case_id={id}` | 只读取得各块状态/来源/数据；受功能开关约束，可能503 |
| `GET /graph/attack-path/{case_id}?max_depth=6` | Case路径及source/fallback；无Case不能拼URL |
| `GET /graph/neighbors/{entity_type}/{entity_id}` | 直接邻居，不是整事件图 |
| `GET /graph/blast-radius/{entity_type}/{entity_id}` | 选定实体的图可达范围 |

后写的低seq `graph_result`可能落在10000+工具事件之后；运行中只追最高seq会漏记录。取得交付后从不带since的首页重新分页补齐，按 `(run_id,seq)`去重，再核工件关联。不根据一次暂时空页清空已读材料。[读取合同](../integration/v1/investigation.md)、[实际落库与分页边界](../integration/v1/page-data-mapping.md)

**并非所有GET都只读。** 当前 `GET /cases/{case_id}/attack-chain` 会写 `aisoc_attack_chains`缓存并commit，本轮没有调用；只读分析使用既有工件或新Alert链/统一上下文GET。`POST /graph/investigation-context`会投影PG资料到Neo4j；创建/关联Case、`POST /cases/{id}/investigate`、反馈与响应都是另有写入/运行效果的操作。查看图或打开历史Run不应暗中触发它们。[Case Chain实现](../../services/api/app/api/v1/endpoints/attack_chain.py)

Case启动当前路由的 `raw_alert_payload.alerts`最多取3条，旁边 `_investigation_evidence` helper另有25条上限，二者不能混写。应根据该Run实际 `raw_alert`及入口解释覆盖范围；不能见Case有20个成员就显示“已分析20个告警”。人工启动路径还可能先修改告警状态再代理Agents，状态改变本身不是成功启动证明。[Case入口源码](../../services/api/app/api/v1/endpoints/cases.py)

### 9.2 空值、缺关系、未实现分开交接

没有负责人是值为空；有主机名却无库存ID是缺资产关联；有工件却页面没读是展示未接；缺事件管理合同是后端待承接；某轮只有工具preview是留存粒度不足；v2问题/证据结构未上线是版本能力边界。这些都不应统一解释为“数据没了”。

## 10. 当前划分后的落点与待定事项

事件页保留告警、实体、发生时间线、已有上下文、当前链图和关联线索，承接管理及调查入口。调查工作区在原Case材料与协作能力上，突出**Run范围、实际步骤、工具证据、判断、链图快照、停止原因、建议/执行、报告和用量**。同一资料可以从两页进入，但以来源对象/Run作为同一个依据，不维护相互矛盾的副本。

后续如果转为实现，适合先接已有Run/事件/工件和链图读取，体现现有能力；v2问题组、完整成员冻结、证据采用关系、增量调查沿独立调查方案继续，不在页面中先编造一套已落地流程。本段只是分析建议，不启动实现。

尚需在对应开发前确定的事项：

1. 事件级管理如何持久化，Fusion分组怎样映射用户看到的事件；事件关闭是否级联告警。
2. 事件的多告警Chain展示采用哪个明确种子/选择方式，如何呈现超出成员范围的候选；不默认选择最早一条就代表整个事件。
3. 新调查的范围选择与Case成员关系：展示实际选材、是否继承已有结果、后续新成员是否触发新Run，沿v4设计而非本页自行确定。
4. 实际审批/执行由哪一处承接，保证建议、批准、执行和验证各有真实记录；原型批准按钮不充当生产执行证明。

## 11. 依据与本轮核验范围

| 依据 | 支持内容 |
| --- | --- |
| [页面讨论原则](ui-discussion-principles.md) | 已确认语义、逐项对照、保留原型、空值与缺口规则 |
| [现有原型](../../prototypes/security-pages/README.md)、[工作区视图](../../prototypes/security-pages/workspace-view.js) | 当前可见功能与演示边界 |
| [调查读取合同](../integration/v1/investigation.md)、[逐元素表](../integration/v1/page-elements.md)、[真实表字段](../integration/v1/table-fields.md) | v1来源、表/JSON/API；告警具体展示以最新页面原则为准 |
| [v1发布](../operations/service-v1-release-20261022.md)、[10月25日六条结果](../operations/alert-reset-replay-20261025.md) | 已发布与真实处理证据；不重写旧质量/额度问题 |
| [本地小修回执](../operations/investigation-result-handoff-20261023.md) | 工具完整留存等未发布边界 |
| [调查规划v4](../architecture/investigation-planning-design.md)、[实施记录](../operations/unified-investigation-implementation.md) | 新版目标与实际阶段，非现成页面数据合同 |
| [图上下文](../../services/api/app/services/investigation_attack_context.py)、[Graph API](../../services/api/app/api/v1/endpoints/graph.py)、[attack_path步骤](../../services/agents/app/agents/attack_path_agent.py) | 链图来源、缺关系、回退、程序分析和建议逻辑 |
| [账本持久化](../../services/agents/app/investigator/ledger.py)、[账本API](../../services/api/app/api/v1/endpoints/investigations.py) | 同Run事件/工件/报告、字段粒度与读取方式 |

本轮核验仅覆盖上述源码/文档、21既有回执、20限定只读参考、两个微软官方页面与文档一致性。未重新跑业务测试、模型、调查或浏览器逐项验收。详细静态核验和独审见[本批回执](../../openspec/changes/archive/2026-10-25-analyze-incident-ai-investigation-pages/verification.md)；不以分析文档宣称页面已修改或后台能力已上线。

## 12. 2026-10-27 V2 页面核对与功能分析续接

### 12.1 用户重申的页面职责

事件以告警信息及各告警已有基础调查信息的汇总为中心；整个 Case 工作区以 AI 调查的过程、发现和交付为中心。这里的基础调查可以已经包含 AI 分诊、Explain 或自动调查结果，仍须保留告警及运行来源；不能将各条结果直接拼成整个事件的统一判定。

| 内容 | 事件页面 | Case 工作区 |
| --- | --- | --- |
| 核心问题 | 发生了什么，涉及哪些告警，目前已知什么？ | AI 调查了什么，发现了什么，依据是什么？ |
| 告警与实体 | 汇总成员告警、发生时间、资产、账户及关联关系 | 说明本次调查使用的材料和覆盖对象，区分当前成员与当次输入 |
| 基础调查 | 汇总各告警已有的分诊、解释、增强信息和处理结果，支持回查来源 | 继承已有材料，呈现进一步查询、关联分析和判断 |
| 调查结果 | 展示简短摘要与详情入口 | 展示发现、证据、实际分析过程、未解决问题、报告和响应情况 |

上述是页面职责，不新增 Case 创建、自动启动或事件关闭规则。无 Case 的自动调查保持可独立查看；同一 Case 可以查看多次调查，Run 结束与案件关闭分别表达。

### 12.2 当前 V2 实际看到的页面

核对入口为[事件上下文](http://127.0.0.1:4174/#/incidents/262144/attack)、[事件概览](http://127.0.0.1:4174/#/incidents/262144/summary)、[事件关联调查](http://127.0.0.1:4174/#/incidents/262144/investigations)、[Case AI调查](http://127.0.0.1:4174/#/cases/17420/overview)及其分析过程。以下数量是本次本地页面观察，不是生产统计。

| 区域 | 当前表现 | 本轮评价 |
| --- | --- | --- |
| 事件首屏 | 成员告警15、实体8、发生范围、已有调查2；告警列表与关系图为主要内容 | 已突出告警和上下文，但基础调查结果尚未形成清晰的汇总阅读层次 |
| 事件概览 | 告警/战术统计、对象范围、告警时间线、证据和事件资料 | 有基础材料概况，仍不便直接看清各告警已有何种初步判断、哪些需继续调查 |
| 事件调查页签 | 两次关联调查的范围、摘要、运行状态和交付完整性，提供打开调查入口 | 适合保留摘要跳转；不据两次运行推定已完成整个事件的调查 |
| Case 首屏 | 已以“AI调查”为入口，选择 Run 后查看结果与范围、分析过程、工具与证据、Chain / Path、报告与响应 | AI调查框架已有，整体仍较偏运行材料的组织与核对 |
| Case 当前样例 | 当前成员11、本次输入3；过程显示收集材料、分析证据、形成结果三条概要 | 成员与当次范围区分正确；概要不能代替完整可核查的 AI 分析或工具证据 |
| 重复区域 | Case 同时保留攻击关系图与 Chain / Path、证据与工具/证据；事件另有调查、证据与响应、建议动作 | 需要明确对象范围、内容来源和主阅读位置；本轮未决定删除或合并 |

本次查看了上述代表视图并核对前端源码；没有逐一验收所有页签、管理操作或全部数据。V2 仍为本地原型，既有设计样例与保存的实际运行结果共存；未新查生产、重跑调查或模型。既有工具摘要和运行完整性限制沿用[版本说明](../../prototypes/security-pages-v2/README.md)。

### 12.3 待讨论的调整方向

1. **事件的基础调查汇总。** 让用户能快速辨认哪些告警已有初步判断、具体判断及依据来自哪里、哪些仍需进一步调查。这里只讨论已有信息怎样组织，不新增模型必填字段或自动生成整个事件结论。
2. **Case 首屏的信息次序。** 建议按“关键发现 → 支撑证据 → AI实际做过的工作 → 尚未查清的内容 → 下一步处理”组织。Run ID、Tokens、工具参数等保留核查入口，具体层级待逐区域讨论。该顺序是本轮建议，尚未作为最终页面设计实施。
3. **相近区域的含义。** 案件关系图可表达案件当前关联，某次调查中的 Chain / Path 表达当次保存的关系与分析材料；案件证据可表达材料集合，工具与证据表达当次查询取得的内容。需要核对现有功能后再定名称、位置及是否合并，不能因页面重名就直接删除已有能力。

### 12.4 保存位置与下一步

本轮按用户要求在 `codex/functional-analysis` 保存当前前端相关成果与中文分析进度；英文仅用于分支名。本地保存不代表已发布、已接后台或上述建议已确认实施。

后续先逐项讨论**事件首页如何汇总告警和基础调查信息**，再讨论 **Case 首页如何突出 AI 调查发现、过程和交付**。沿现有视觉与已确认样例推进，不将数据核对当作重设计授权。本次保存回执位于 OpenSpec `save-frontend-functional-analysis-progress`。
