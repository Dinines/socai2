# 事件页与 AI 调查工作区：功能划分、展示内容和数据依据

**最新续接（2026-10-29）：** 用户要求将无后台Case但已有的调查材料补齐到Case工作区，已追加3个明确的本地集合及案件汇总/证据/来源活动，见[第19节](#19-2026-10-29将已有材料补入本地-case-工作区)。事件及单Run的同步见第18节，修改前字段盘点见第17节。使用10月25日保存结果，保留源归属、原样例和V1，未新建后台Case或执行新调查。

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


## 13. 2026-10-27 V2 融合修改

用户明确：Case更多参考迁移来源AiSOC Case页面，同时保留原微软式事件/调查页面的基础能力，融合组织而不是移除任一方功能。只改本地4174的V2，事件仍承担告警及基础调查汇总，Case突出当次AI分析与后续处理。

### 13.1 融合结果

| 区域 | 本轮页面组织 | 保留和来源 |
| --- | --- | --- |
| 事件概览 | 成员告警、已有判定、关联调查覆盖、涉及实体；按告警列出判定/已有解释/调查来源，另列各次调查摘要 | 不将多告警Run的综合结论变成每条告警判定；无材料保留空态 |
| 基础调查 | 全部、已有判定、有关联调查、待继续核查、未记录判定五种筛选 | 覆盖按告警去重；当前判定和单告警Run的首次分诊分别展示，保留各自来源 |
| 原事件功能 | 顶部“告警阶段与时间线”进入事件资料概况，保留战术聚合、时间线、证据类型统计、事件信息；关系图、链、资产、活动、管理和建议继续可用 | 结束审阅发现原summary失去入口后已接回；没有用新概览覆盖这些基础功能 |
| Case 导航 | AI调查/调查历史，案件材料，协作与跟进三组 | 原案件资料、成员、对象、关系图、证据、相似Case、任务、活动、评论附件及管理保留；相似Case仍是原目录占位 |
| AI调查首页 | 关键发现、可核查材料、实际工作、已保存的停止/缺失资料、后续处理；范围与案件跟进在侧栏 | Run ID/时间/用量折叠；本次输入与Case当前成员分开，输入证据不自动称为AI已采用 |
| 阶段分析 | 按实际节点/已有阶段记录展示；有Deep资料时显示策略、轮次、查询方向、截断及停止原因 | 参考AiSOC InvestigationPanel的阶段组织；实际graph样例没有Recon/Forensic/Responder输出时不伪造三卡 |
| 查询与证据 | 查询返回为主，参数展开，输入关联证据与工件目录分区 | 保留最多200字符工具摘要限制与工件ID/hash；不补完整prompt或证据引用关系 |
| 攻击链与路径 | 全部/攻击链/攻击路径/关联范围分别定位 | 参考AiSOC独立AttackChain/AttackPath功能；读取同Run保存状态/范围，与案件当前关系图并存 |
| 调查记录 | 类型、执行者/节点双筛选，展开已有记录载荷 | 参考InvestigationLedger；不是完整prompt回放或实时尾随 |
| 报告与响应 | 原Markdown报告及下载、建议动作/目标/审批要求/依据、实际执行分别展示 | 使用保存原文，不把建议隔离标为执行；未接真实启动或响应写回 |

### 13.2 样例与界面边界

事件262144仍为原15告警样例：当前无已记录判定，5条有关联调查、2次Run、8个实体；显示0判定不等于未调查。Case17420当前11个成员，第一/第二次Run分别只用3/2条输入。以上与6条实际保存Run分别保留，未新造实际Incident/Case父对象。

实际Run `d141b0e3-16cc-5a0b-8d7f-35159342efe6`保持completed/partial/needs_review、调查置信度75%、首次分诊85、7调用29025tokens；Deep6轮、6工具，停止原因及查询失败原文保留，建议隔离1项、实际执行0。没有通过UI组织调整追认调查质量通过。

本轮25项直接测试包含291告警HTML比较、8Run×6视图、覆盖来源/筛选/固定输入/调查记录及原事件入口。浏览器检查事件筛选、Case切换保留页签、实际Deep/记录筛选/无Case路径/报告响应和700px布局；详见回执。后端启动调查、审批执行、完整模型轨迹与正式事件/Case取数仍由后续模块承接。


## 14. 2026-10-28 AiSOC20 历史结果填充

用户要求使用之前AiSOC上的告警数据。沿上一轮融合设计，在V2追加三个原场景的六条告警与已有运行结果。输入来自2026-10-24合成演示，运行结果实际持久，源后端没有Case；因此新入口使用local-aisoc20-1/2/3，并明确标注本地整理。原Case17420、52条设计告警、6条21重放及全部原有功能保留。

| 展示内容 | 实际来源与转换 | 空值/限制 |
| --- | --- | --- |
| 告警基本信息 | `.local/verification/alert-reset-replay-20261025/source20.json` 的 rows；ID/租户/时间/严重度/状态/判定/置信度/分诊分数 | captured_at为10月25日读回，event_time是10月24日；未提供末次活动不填 |
| 原始主机/账户/IP/战术/检测源 | `.local/aisoc20/showcase-20261024/evidence/final-N.json` 中按alert_ids对应的inputs | 校核租户/title，原输入另存；实体加环境+租户命名空间，无库存ID/风险/组织/标签不造值 |
| 事件关联 | `final-read-verification.json.rows[].incident_id`，按alert_id精确匹配 | 5条有已知incident_id、1条为空；未导出Incident父对象，本轮不补造事件标题/状态/评分 |
| 本地Case | 原final-N场景名、两条成员告警、本地整理时间；sourceCaseId=null | 本地工作状态新建、未分配；优先级无评分；源alerts.caseId维持null；不是后端Case或综合AI结论 |
| Run输入及结果 | `final-N-<alert_id>-delivery.json` 的run_id/raw_alert/status/completion/verdict/findings/report_md/stop_reasons | 每Run输入1告警。完成态、完整性、判定分开；triage-only缺raw_alert及开始时间，不用当前告警补成Run输入 |
| 过程/Deep/工具 | delivery.audit_log白名单与investigation_depth；工具args/result_preview | 71记录/34工具，摘要可能截断。payload.step_status=skipped优先于completed模板摘要；未执行attack_path不显示完成 |
| 工件目录 | final-read-verification.artifacts按run_id关联 | 27目录含kind/event_id/size_bytes/actual_bytes/hash_match；原件未提供工件ID/hash/时间，显示未记录，event_id另列 |
| 用量/报告/建议 | verification.costs按run_id累计；5份report_md与独立MD逐字节核对；proposed_actions/executed_actions分别展示 | 36调用117286tokens；无执行记录不把隔离建议视为已执行；报告原文保留旧判断和质量限制 |
| 案件关系 | final-graph-overview.json仅保留与这六告警直接相连的21节点24边，再按当前Case成员过滤 | 不含诊断Case/其他场景；不映射为Run.graphs，不当作模型采用证据或因果 |
| Explain/附件/协作 | 本批没有保存这些资料 | 正常空态，不调用懒生成逻辑、不复用设计样例附件 |

告警相关/相似候选新增同环境同租户约束，避免20与21同名主机混用。历史Run材料独立于本地成员编辑；重复导入不覆盖用户编辑，重置恢复初始设计及这两批已有记录。原告警样式保留，同输入291次HTML比较保持。

离线脚本为`tools/testdata/export_aisoc20_ui.py`，来源hash在V2的`aisoc20-data.manifest.json`；完整模型提示词/回复不进入投影，只保留工件目录与已有报告。此轮不发模型、重放、改后端或部署；真实运行不等于真实攻击、查询完备或结论质量通过。

用户预览反馈“攻击链与路径”没有数据后，已将同批已保存关系直接接到该页签：全部/攻击链/攻击路径/关联范围均可查看源关系图，攻击链页另列告警时序。Office组7节点8边，输入告警蓝色标识；已跳过路径分析的状态保留，不将可视化关系线索说成Run生成的攻击路径。独立Run按同批共享主机/账户/IOC展示关联告警；Case内按当前成员和本次输入确定展示范围。


## 15. 2026-10-28 已持久化 Case 的联合调查样例

新增2026-10-21的历史实际Case：`82b1246f-9f34-463c-8c2d-27d2b075c741`，持久Run `e998308a-a353-4647-99f6-10f94ced0ecf`。这是本地API/Agents连接21基础设施时，三条合成测试告警的实际处理回执，不是当前线上库存或真实攻击。本次只读取本机原件，不重发调查。

| 页面信息 | 原始来源 | 显示与边界 |
| --- | --- | --- |
| Case及成员 | case-created.json的201返回、active-case.json、run-detail.json的200返回、启动返回 | 保留Case UUID、new状态及三告警ID；不同于第14节的本地整理Case |
| 输入告警 | 04-report_writer-output.json.raw_alert.alerts | 3条原始输入；无canonical处理状态/分诊评分则Unknown/未记录，不借draft补值。告警响应链接同一次Case联合调查 |
| 调查身份 | API Run与Agent内部Run12522217-c0ef-4222-8522-ee0fb680c0e6不同 | 29条audit和持久events逐序/载荷全等、报告一致来核对归属，两ID分开保留。成员移走不删除明确归属的历史Run |
| 攻击链 | 该Run的attack_chain工件正文 | 5候选，2个属于本次输入、3个为历史外部候选；保存分数、距离及共享实体，不扩为Case成员 |
| 攻击路径 | 该Run的attack_path工件正文 | 原11节点15边，保留原关系、提供可点击告警与原始边；不重建为攻击因果 |
| 关联范围 | alert_graph工件的neighbors/blast_radius | 邻居5、可达16、深度3、范围评分9；不是确认受害16个对象 |
| 阶段与报告 | 四节点输出、29条事件、4份Run工件、独立report.md | Recon/Forensic/Responder采用结果及Report留存记录；4工件字节/hash和报告全文一致 |
| 结论与执行 | forensic.confidence=0.1、responder.dry_run=true、Run.status=completed | 取证置信度10%；完整性与判定未单独记录；3建议、无执行记录。Case仍new，不随Run结束关闭 |
| 工具与用量 | 7tool_call及Run用量 | 1次知识库不可用，其余保存结果原样；4调用18388tokens。与旧v1的200字符摘要分型 |
| 时间 | events.ts及Run.started_at/completed_at | 来源存在8小时差异，原值保留并在详情说明，不推测纠正 |

离线投影工具`tools/testdata/export_persisted_case_ui.py`；V2新增`persisted-case-data.js`及16份来源SHA的manifest。只导出白名单与业务结果，不输出prompt/messages/完整模型回复。合计67告警、16Case、15Run；原样例和两批六告警保留。验证见[交付回执](frontend-v2-verification.md)。

## 16. 2026-10-28 调查关系图统一设计（待接入页面）

用户偏好事件页“左告警、右实体图”的风格，希望评估融合attack chain与attack path，并丰富战术、技术和跨告警关联。随后澄清点击高亮只是举例，由设计判断更合适的表现。本节为方案和独立可点击设计稿，尚未替换4174的V2图谱，也没有新增业务查询或调整算法。

### 16.1 统一入口与布局

调查内用一个“调查关系图”承接原“攻击链与路径”。同一画布可叠加实体关系、候选关联、技术映射；原始Chain/Path/Alert Graph按来源保留在依据详情中，不把三种返回拼成一种统一结论。事件页继续面向当前成员与基础信息，调查页锁定所选Run当时的输入与材料；复用布局和交互，而不是混用数据时间点。

- 顶部：当前Run及输入范围沿用原选择器；图内只显示本次输入数、候选查询的种子/窗口。布局切换、类型筛选、分组和缩放沿用已有图谱操作，后续接入时保留。
- 左侧约24%：输入告警列表，时间、严重程度、名称、已有处理状态；缺状态保持未记录。切到“链候选”看原PG排序、候选分数、距离和成员身份。五条候选中两条同时是输入，只保留同一个告警身份，不复制成新成员。
- 右侧：实体沿用圆形图标，告警使用小型矩形锚点，技术为标签节点。Case作为范围上下文，默认不占中心节点；原Case成员边仍可在关系详情回查。相同实体连接多条告警，跨告警关联通过共享节点可见。
- 顶部ATT&CK分类条用于聚焦，不画固定“初始访问→执行→外联”的箭头。单个技术可能映射多个战术，保留多映射，不从告警名字猜一个战术。
- 下方：随选择显示告警、实体或关系的依据。默认不设第三个常驻详情栏，避免挤占图谱；更多资料按需展开。

### 16.2 选择反馈与联动

推荐“聚焦但保留上下文”，不将点击直接做成过滤或重新布局：

| 操作 | 图谱表现 | 列表/依据与范围 |
| --- | --- | --- |
| 点击左侧告警 | 告警锚点加选中框；直接关联实体加蓝色细外圈；直接关系加深；无关对象轻微淡化但仍可辨认 | 左侧保留选中条目；共享实体涉及的其他告警给次级标记；下方显示该告警关联对象与来源。查询种子、Run输入、Case成员均不变 |
| 再点已选项或取消聚焦 | 恢复全图强度，节点坐标不变 | 恢复全部关系摘要 |
| 点击实体 | 聚焦该实体及直接关系，标记连接到它的告警 | 下方显示精确实体值、相关告警与关系依据，不默认发新的多跳查询 |
| 点击技术/战术 | 标记有该技术或已核战术映射的告警和技术关系 | 同一技术不构成攻击先后；多战术时显示目录映射与来源版本 |
| 点击关系或关系依据 | 强调选定关系与两端 | 显示关系类型、来源记录、支持告警、查询范围；有原方向才显示方向，方向不解释为攻击传播 |
| 开关图层/类型 | 当前选项不可见时清除聚焦并说明；不移动其他节点 | 候选层打开只扩展查看范围，不自动加入Case。明确当前显示数量和隐藏数量 |

颜色之外必须有形状、外圈、线型、选中标记及文字。严重程度颜色继续表示告警等级，不再同时编码选中。同类型分组在聚焦时标“组内命中数/总数”，不要给整个分组附上某一个告警的关系；可展开命中成员。大图先看本次输入的一跳关系，外部候选和多跳可达按需展开，保留布局位置。

### 16.3 数据与图层语义

| 图层 | 来源及可用字段 | 视觉与语义 |
| --- | --- | --- |
| 已记录实体关系 | 同Run的attack_path/alert_graph保存正文；Neo4j nodes/edges，原关系类型与方向 | 中性实线；选中时蓝色加强。“已记录”不等于已确认恶意或已证实攻击路径 |
| 候选关联 | PG attack_chain.chain、seed_alert_id、window、score、distance、dt_seconds、shared_entities、entity_graph | 暖色虚线连接候选与有记录的共享实体；候选排序/分数置左侧或依据详情。分数和顶层confidence是关联排序信息，不叫恶意概率/AI置信度 |
| 技术与战术 | 精确告警技术字段或MAPS_TO；战术由带版本ATT&CK目录映射 | 技术标签和点线；战术作为分类条或分组背景。多战术分类不可强排成单一路径；目录映射与本次告警已确认战术分别表达 |
| 扩展可达范围 | Alert Graph/Blast Radius的原节点与实际保存路径 | 作为按需扩展的上下文，不默认把16个可达对象列为受害资产。只有计数但没有连线时展示计数，不补画路径 |
| AI分析关联（后续条件项） | 只有具备明确端点、证据引用与本Run采用记录时才可叠加 | 独立“AI判断”标识，不从报告叙述自行抽线，不作为本轮必须新增的结构字段 |

数据库是来源维度，事实/候选/分类是业务语义维度。用户默认看到业务图例，PG/Neo4j及工件ID放在可回查的来源详情。不能把“来自Neo4j”当成事实已证实，也不能把“来自PG”都归为候选；同一关系可能有多个来源。

### 16.4 适配规则与当前限制

1. 告警按环境+tenant+alert_id合并；实体优先使用规范实体ID。只有同租户、类型兼容且映射明确的自然键才合并。本样例IP/主机/用户别名由原件精确核对，不泛化为任意同名合并。同端点线段可合并绘制，但逐来源保留原关系类型，例如Neo4j OBSERVED_ON与PG TOUCHES；不得因此称为同谓词，关系类型不同不强行去重。
2. PG当前`_entity_graph_payload`只为候选输出与原种子直接共享的实体。实际E3距离2但shared_entities为空、图中无连接；保留独立候选及“中间连线未保存”，不画“种子→E3”或猜造中间实体。若后端后续返回已核的完整walk，再显示实际两跳路径。
3. 当前graph API的`postgres_fallback`把Case级技术逐一连到每条告警。统一图需要将这类关系降为“Case级技术资料，逐告警归属未核”；不能作为点击某告警时的精确技术高亮依据。本次真实样例source=neo4j，使用其逐告警MAPS_TO。
4. 原Chain排序是候选分数降序，非时间顺序。左侧若切到时间排序必须明确；时间播放仅改变可见时间片，不制造因果边。选择其他告警不重算原种子结果；另行查询须明确新的种子、窗口和结果范围，不覆盖已保存Run材料。
5. 单个数据源失败时保留其他图层，分别表达失败/空返回/未保存/未关联Case；不能一处成功即显示整图完整。原20单告警没有Run路径时仍只能标其上下文资料，不能借本次真实Case的图替代。
6. 统一适配是前端展示建议，不要求合并PG/Neo4j、改算法或把技术/战术拆成新必填字段；缺少精确映射的增量先按条件显示。

依据：本地`services/api/app/services/attack_chain.py`（score_candidate、_entity_graph_payload）、`services/api/app/services/graph_service.py:get_attack_path`、`services/api/app/api/v1/endpoints/graph.py:_attack_path_from_relational`及第15节同Run原件；技术目录于2026-10-28核对[PowerShell](https://attack.mitre.org/techniques/T1059/001/)、[Web Protocols](https://attack.mitre.org/techniques/T1071/001/)、[Valid Accounts](https://attack.mitre.org/techniques/T1078/)。这是本地源码能力核对，不宣称当前部署接口均返回这些数据。

### 16.5 本轮可点击设计稿

使用第15节同Run三输入/五候选：默认聚焦A2 PowerShell，可点击告警、共享主机/账户/IP、技术分类和下方关系依据；可开关实体、候选、技术图层。圆形实体和原事件图保持一致，告警锚点使跨告警关系更清楚。中文短标题是展示别名，原英文标题及告警ID保留在来源详情。可调“淡化不相关对象”和左栏宽度，用于评估交互强度；不要求按此具体颜色实现。

设计稿是会话内交互预览，4174页面及原源数据保持不变；未做后端取数、业务测试或部署。正式接入时继续保留原布局/筛选/分组/缩放、未知状态和Run冻结范围。验收重点是点击能解释关联，状态不变、关联不造、换Run不串材料。

## 17. 2026-10-28 V2 与告警流程数据的字段对照

本节回答：**已有告警流程产生的哪些内容能供当前页面使用，哪些是真的缺，哪些只是没有接到页面。** 复用以前的核对，不重新定义一套必填字段，也不以页面缺值为由修改原设计。

### 17.1 复用依据、数据日期与核对口径

- 告警九列及语义沿用[已确认字段稿](alert-ui-data-contract.md)；旧90项清单沿用[页面取数交接](../integration/v1/page-elements.md)，真实SQL/JSON及留存限制沿用[落库映射](../integration/v1/page-data-mapping.md)、[表字典](../integration/v1/table-fields.md)。旧清单的A/I编号和本文E/I编号各有范围，不直接等同。
- 主样本是21上socai2在 **2026-10-25 11:59:33北京时间** 保存的六条重放最终结果，PG `aisoc.public`，租户 `f6a5c700-69b8-44fc-8238-609362fb1a9f`。本轮读本机保存的原件，不新查远端数据库；因此下述“6/6”“5/5”只描述这一批，不能称为10月28日线上全量库存。[原执行回执](../operations/alert-reset-replay-20261025.md)
- 20的10月24日六条处理结果只作格式参考；21的10月21日历史Case作多告警调查参考，分别见第14、15节。清理前Case不能与10月25日批次合并成当前数据库统计。
- 页面侧核本地V2源码及初始数据，不含用户浏览器localStorage的个人改动：67告警、12事件、16 Case、15 Run。其中只有原52条告警的 `incidentId` 匹配这12个设计事件；追加的15条实际处理记录未生成对应的事件列表行。**六条socai2告警本身已有3个Fusion事件ID，每组2条；缺的是事件聚合展示接入，不能说没有事件归组数据。**

取数缩写：`A=alerts`；`F=A.enrichment_data.socai2_fusion`；`S=F.delivery_snapshot.fused.alert`；`R=investigation_runs`；`E=investigation_events`；`K=investigation_artifacts`；`G=kind=graph_result的工件content解析后的JSON`；`GE=kind=graph_result的事件payload`；`T=kind=triage_verdict的事件payload`。所有关系同时核环境、租户和ID；`K.content`是TEXT，按kind决定是否解析JSON，报告正文不强转JSON。

| 核对标签 | 本节含义 | 处理方式 |
| --- | --- | --- |
| 已有可对应 | 表列或保存JSON已有同义信息 | 复用现有读取，保留来源与转换 |
| 可汇总／未接展示 | 基础数据存在，页面尚未按该关系读取或聚合 | 补读取与汇总，不先增数据库字段 |
| 本例为空 | 列存在，值为NULL、空数组或本次查询零结果 | 正常空态，不能填成“没有能力” |
| 缺关系 | 对象分别存在，但未完成资产/人员/Case等关联 | 补关系；未关联前展示原始对象或未分配 |
| 留存不足 | 只保存摘要、缺步骤输入输出或精确证据引用 | 如实显示粒度，不从报告补造原件 |
| 待承接合同 | 现有流程没有证实该业务字段/动作的完整来源 | 由相应模块明确读写与规则，本轮不实施 |

### 17.2 告警九列：保留原结论，补本批实际值

| 页面字段 | 既有来源与显示含义 | 六条样本与当前缺口 |
| --- | --- | --- |
| 名称、严重程度、告警时间 | `A.title/severity/event_time`；严重程度沿已确认分组，时间按北京时间显示 | 三列6/6有值；时间不静默换成 `created_at` |
| 资产标签 | 同租户告警→`alert_asset_correlations`→`assets.tags` | 本批关联结果0条、`affected_assets=[]`，所以缺库存关联；不是资产表不存在，更不能改用告警tags |
| 处理状态 | `A.status`，结合已证实启动调查事实按原约定显示 | 6/6有值；分配、Run结束、调查完整性和告警关闭仍分开 |
| 类别 | `A.mitre_tactics`的战术含义 | 6/6有值；不换成 `A.category` |
| 检测源 | `F.identity.source`；详情API投影为 `fusion_identity` | 6/6为 `showcase-security-sensor`；`connector_id/connector_type`均NULL，不能宣称已识别原厂商。没有connector值不等于没有source |
| 受影响资产／账户 | `A.affected_hosts/affected_ips/affected_users/entities`；库存名称需真实资产关联 | 主机/IP/账户数组6/6非空；库存ID、库存标签/所属业务等仍缺关系，不把图中Host节点当已匹配资产库存 |
| 负责人 | `A.assigned_to_id`关联用户目录 | 6/6为NULL，是未分配；不是缺负责人列。样本owners查询0行不代表用户目录为空 |

当前本地 `AlertResponse` 列表响应已有名称、严重程度、状态、战术、时间、分诊评分等；没有完整暴露Fusion来源/事件ID、负责人及库存标签关联。`AlertDetailResponse`已有 `fusion_identity/fusion_incident_id/fusion_ioc_lookup/raw_event/source_event_ids`。**列表缺响应与数据库缺字段分开处理**；本轮未调用线上接口确认其部署版本。[告警API源码](../../services/api/app/api/v1/endpoints/alerts.py)

### 17.3 事件列表、预览与详情：逐区域对照

| 页面区域／具体内容 | 已有可用字段或汇总依据 | 当前差距与承接 |
| --- | --- | --- |
| 事件ID、成员告警数、成员跳转 | 同租户按 `F.incident_id`归组，成员用 `A.id` | **可汇总／未接展示**。本批6告警→3组；V2 `store.incidents`仍12个设计事件，追加真实告警没有对应事件行。真实ID不能换成Case ID |
| 事件标题、说明 | 成员 `A.title/description/narrative`可逐条展示 | 尚未证实独立事件标题/说明的持久合同。选择代表告警或生成摘要都需要明确规则；不能把某条告警叙述当整体调查结论 |
| 严重程度、优先级及评估因素 | 告警有 `A.severity/priority`；另有 `priority_score/priority_rationale` | 本批score全NULL、rationale全空。事件级评分/聚合规则待承接；当前预览90/45、85/60/30等因素是前端样例计算，不能当后端已计算值，也不能拿 `ai_score`代替 |
| 事件状态、分类、负责人、标签、解决说明 | 成员各有 `A.status/disposition/assigned_to_id/tags` | 告警信息可汇总，但不能直接代替事件管理状态、统一分类和事件负责人。已核范围未提供完整事件主对象读写合同；原型 `inc.status/owner/classification/tags/resolutionNote`仍属本地管理 |
| 首次／最近活动、更新时间 | 成员 `A.event_time/first_seen/last_seen/updated_at`可按不同含义聚合 | **可汇总，但需区分业务时间**：最早发生、最近发生、最近更新不是同一列；`first_seen_at`是人工认领/确认时间，不作首次告警发生时间 |
| 活跃／全部告警 | 成员ID去重计数，状态按已确认语义归一 | 可汇总；当前原型按 `status !== Resolved`计数，不能原样处理后台closed/resolved等枚举 |
| 检测源、涉及实体数量 | 成员 `F.identity.source`去重；主机、用户、IP等按类型和值去重 | 可汇总；要保留来源标识的粒度。当前列表 `assetCount`实际统计 `entityIds`，含账户/IP，不能宣称全部是库存资产 |
| 攻击中断、队列压缩 | 真正中断需实际响应执行凭据；压缩需同租户/同时间范围的输入告警与归组结果 | **当前统计仍为样例**：中断按 `Attack Disruption`标签计数；压缩用全部67告警和12个设计事件计算，但仅52条匹配，不能作为真实Fusion压缩率或自动阻断成果 |
| 事件概览：成员、已有判定、有关联调查、待核查 | `A.disposition`、单告警 `T.verdict/confidence/rationale`、关联Run实际阶段及完整性 | 基础值已有；统计需按同一成员集合。不能把多输入Run的整体结论写到每条告警，也不能把“有Run”直接当已开展完整调查 |
| 基础调查：当前判定、分诊依据、Explain、Run入口 | `A.disposition/ai_score/ai_summary`、`T`、已有Explain响应、已核输入→Run关系 | **已有可对应**。Explain按已有接口/保存正文使用，不拆出固定“待核实事项”等新字段；本批6份Explain为已记录的模板兜底，不等于模型给出完整调查 |
| 成员告警表 | 沿17.2逐条读取；事件筛选条件用 `F.incident_id` | 字段大多已有，列表API投影及归组读取待接。保留原样例与用户已确认列语义 |
| 检测规则、IOC及原始资料 | `A.rule_id/rule_name/iocs/entities/raw_event/source_event_ids/external_id`；S中的原来源字段 | 本批rule_id 6/6有值、rule_name全NULL；可展示ID，不能编规则名。raw_event有原文不等于全Kafka信封或每类日志都有独立进程/命令行列；source_event_ids只是引用，不是日志正文；源/目的角色读实际命名字段，不按IP数组顺序猜测 |
| 告警阶段与时间线 | `A.event_time/created_at/resolved_at`和同输入Run的 `E.ts/kind/summary` | 能展示已记录发生、接收、分诊、调查等时间；原始日志全量、人工分配/修改全历史并不自动存在，不能补造步骤 |
| 关联关系、关联告警链 | 成员实体、当前Alert链/图上下文GET；Run图工件只代表该Run当时读取 | 事件当前关系与Run历史图分开。原型事件链是已加载成员的共享实体/时间窗筛选，不等于已经消费后端候选链算法；点击筛选不改变成员归属 |
| 涉及对象：名称、类型、域、风险、库存ID | 原始对象来自 `affected_* / entities`；库存属性来自真实资产关联；图属性保留自身来源 | 名称/类型可展示。六条样本库存关联为空，不能用默认域、合成资产ID、图中默认风险分充当库存事实 |
| 关联AI调查 | `R`及真实输入ID关联；自动Kafka样本 `R.case_id`是告警锚点 | **可对应**，以告警或明确Case入口核归属。当前6条 `A.case_id=NULL`，但6条都有Run；关联调查入口不应强制先建Case |
| 证据与处置：对象、判定、检测来源、威胁、处置状态 | `A.iocs/entities/raw_event`提供源对象；G可提供IOC分析及建议/执行数组；案件证据另有Case结构 | 源对象不是已定性的证据。统一证据ID、对象级威胁判定、审批/处置状态不能从一条IOC或建议推定；当前 `store.evidence`样例与Run工件是不同集合 |
| 处理活动：人/自动、目标、动作、结果 | 已保存调查事件支持机器过程；Case时间线与相关审计可供对应Case使用 | 事件级人工管理和真实响应活动链未由本批证明；不能把Case时间线直接当事件历史，或把建议隔离记为已隔离 |
| 相似事件、关联到Case、管理弹窗 | 已有成员实体/战术/时间支持候选检索；Case API可创建/关联成员 | 原型在已加载数据中筛选/本地修改。全库跨事件查询、关系验证及事件管理写回待承接；不自动合并，不因关联成功宣称已启动调查 |

事件页的主要缺口是 **真实成员归组读取、事件级管理/统计合同，以及资产和人员关联**。告警原文、分诊结果、实体、时间、关联Run本身不是空白。事件保持“材料汇聚”职责，不需要复制Case里的完整工具、过程、报告和响应工作区。

### 17.4 AI 调查详情：按当前六个页签核对

| 页面区域／具体内容 | 真实来源和展示转换 | 样本覆盖及缺口 |
| --- | --- | --- |
| Run选择、标题、所属对象 | `R.id/alert_summary/raw_alert/case_id`；标题可用保存的alert_summary或输入标题 | 6/6有Run。无统一 `R.title/target_type/trigger_type`列，不能只看case_id字段名推断业务Case；优先沿已核入口身份解释 |
| 输入与范围、当前Case成员 | `R.raw_alert`；Case入口用其实际 `raw_alert.alerts[]`；当前成员另读Case | 已有保存输入；Case当前成员与Run输入必须并列区分。现Case启动源码最多选3条；原始描述/full_log也有截断，不能宣称冻结了全部成员全文或分析全部Case成员 |
| 运行状态、完整性、开始/结束、停止原因 | `R.status/started_at/completed_at/error`；`GE.completion`；`G.budget_exhausted_reason/error`等实际字段 | 6个Run均completed，其中5个Graph为partial、1个分诊关闭未升级。历史Case完整性未记录。状态字段不能互相补值；G/report内部的running保留为历史原文，不覆盖外层运行状态 |
| **调查发现**：最终判定、置信度、发现、范围限制 | `G.verdict/confidence/confidence_basis/findings/investigation_depth` | 5份G可读，全部needs_review；分诊 `T.confidence`、检测 `A.confidence`、G置信度分列。findings混有观察、过程和失败，不全是已证实攻击事实；没有统一根因/最终结论摘要字段就不强拆报告补列 |
| **阶段分析**：实际阶段、摘要、输入输出、采用结果 | `E.kind/agent/summary/payload`；graph入口的graph_step；历史Case另有recon/forensic/responder/report记录 | 本批15个graph_step通常只说明node完成，不保完整阶段输入输出；不能为所有Run补齐四Agent卡片。历史Case有实际四阶段，按其原件展示，不能移植到自动Run |
| Deep深挖：轮数、不同查询方向、未覆盖数据、停止 | `G.investigation_depth.iterations/distinct_pivots/pivots/strategy_id/truncated/unavailable_data/coverage_notes/narrative` | 5份调查可对应；轮数不是模型调用数，空查询不是安全结论。预算停止与覆盖不足保留；不从模型正文反造精确任务进度/完成率 |
| **查询与证据**：工具名、参数、返回、时间、耗时 | `E.kind=tool_call`；`payload.tool/args/result_preview`，`E.ts/duration_ms` | **49条工具记录已进V2数据**。48条有preview，1条空，最长200字符；49条 `E.duration_ms=0`为留存默认值，payload无duration_ms，不能显示成实测耗时0ms。未证明完整返回普遍留存 |
| 工具成功／失败、查询范围、命中数量 | 实际返回中的 `available/status/success/row_count/reason`等；参数及source/window | 各工具结构不同，preview还可能截断；不能把事件已记录当调用成功，不能把 `available=false,row_count=0`当成功零命中。当前独立调查v2合同不倒填旧数据 |
| 工件目录与正文 | `K.id/run_id/event_id/kind/created_at/sha256/size_bytes/content/blob_ref` | **77份工件目录已进V2**，其中5份MD/5份HTML报告、15份链图工件。已有目录不代表正文都在当前视图展开；精确追溯用artifact/event/hash，不靠相近时间 |
| 输入证据、查询证据、分析采用证据 | 源告警材料、实际工具返回/工件、模型输出/程序采用分别保留 | 当前 `inputEvidence`只取 `store.evidence`中与输入告警ID相连的记录，数量0不等于工具/工件0。统一证据项ID、结论到证据的精确引用、逐条采用关系没有由旧自动流程普遍提供；不从Explain正文制造必填新证据字段 |
| 组织知识、近期处置、技能、记忆、身份上下文 | 五类 `*_read`工件，各6份，共30份 | 读取回执和内容已有；读取成功、材料提供给模型、模型引用、程序采用是不同层。不能因有30份工件就称全部语义采用有效 |
| **调查关系图**：Chain/Path/Alert Graph及选择来源 | 同Run `K.kind=attack_chain/attack_path/alert_graph`的content；状态外层与data分层 | 15份均已保存并投影到V2；具体为空原因见17.5。统一图的布局、颜色、选中态、图层开关是前端派生，不要求新增数据库列；关系缺失不能靠绘图补造 |
| **调查记录**：时间、角色、种类、摘要、载荷、筛选 | `E.id/seq/ts/kind/agent/summary/payload` | 原件92条，V2步骤投影81条，省略6条llm_call和5条graph_usage；这是展示投影差额，不是数据库丢失。seq不保证写入顺序；运行中增量和交付后补齐按9.1处理 |
| 模型调用及输出 | 本批6份llm_prompt、6份llm_response、5份graph_llm_exchanges，另有E及成本表 | 原件有留存，但V2未把全部模型正文作为可读步骤展示。现有留存仍有截断/粒度边界，不能宣称每一步完整提示与输出都齐全；也不要求公开隐藏推理 |
| **报告与响应**：报告、建议、审批要求、实际执行 | `K.kind=report_md/report_html`原文；`G.proposed_actions/executed_actions` | 5份报告；2份G各有1条隔离建议，3份无建议，5份executed_actions均空。建议中的requires_approval只是要求，不证明已有审批单或执行成功 |
| 用量、调用次数、费用 | R总量与 `aisoc_run_costs`按Run/model聚合；graph_usage只作对应增量 | 本批36调用157310tokens，36调用未计价；不能把0成本显示成免费，不能将Run总量与Graph增量再次相加 |

当前已经有足够材料展示“AI做了什么、查了什么、交付了什么、为何停止”。主要不足在 **完整工具/阶段原件、精确证据采用关系及部分读取展示**，不宜一概称为调查页缺字段。[调查工作区源码](../../prototypes/security-pages-v2/investigation-workspace.js)、[调查读取API](../../services/api/app/api/v1/endpoints/investigations.py)

### 17.5 Chain、Path、工具和证据空态的同源核查

工件内容存在外层封装，不能直接读取 `content.chain`：例如 `attack_chain`工件应先解析content，再读 `attack_chain.status/source/error/data`；候选是 `attack_chain.data.chain`，实体图是 `attack_chain.data.entity_graph`。Path、Alert Graph同理。外层还保存 `scope/alert_id/case_id/queried_at/prepare`等信息；查询范围亦可从G的 `context_bundle.attack_context.query_scope`核对。

| 对照对象 | Chain | Path | 工具／工件 | 正确解释 |
| --- | --- | --- | --- | --- |
| 原设计Case17420、Run `INV-20261024-001` | 无同Run服务链原件 | 无同Run服务路径原件 | 原型阶段说明，工具/工件数组空 | 设计样例没有实际运行材料；不能借其他Run的数据填上 |
| 10月25日六条socai2自动流程 | 5份链：2次success各1候选、3次empty零候选；链的entity_graph仍有节点 | 5份均 `not_linked/no_linked_case`；告警Case为空 | 6Run共49工具、77工件；1条分诊关闭没有Graph图工件 | 查无候选、未关联Case、未升级是三种不同情况，均非工件消失 |
| 同批Run `d141b0e3-16cc-5a0b-8d7f-35159342efe6` | empty，候选0；entity_graph仍5节点4边 | not_linked | 6条工具记录；Alert Graph success，邻居5、图可达6 | 候选链空仍可显示源告警与实体，图可达不代表已受攻击；工具摘要有查询失败，不能记安全 |
| 10月21日历史Case联合Run `e998308a-a353-4647-99f6-10f94ced0ecf` | 5候选，其中3条不是本Run输入 | 11节点15边 | 7工具、4工件、29过程、报告；完整性未知 | 已有历史样例证明Case关联路径材料存在；不是10月25日新批次，也不能借外部候选扩大实际Run输入 |
| 20的10月24日六条单告警处理 | 没有这6个Run专属链工件 | 无Case专属路径 | 34工具、27工件目录、5报告 | `graph_state/report_markdown`不同于21kind；全局图只能作上下文，不能当本Run当时的读取证据 |

以第一条实际告警 `4c71eec2-77da-5b81-b68a-72801d55ea24`为贯穿例：`F.incident_id=7bde0c0b-0d18-4abc-9382-9752f2ae5e98`；`A.case_id=NULL`；对应Run的 `R.case_id`等于该Alert ID；分诊TP/0.85，调查needs_review/0.75，Run completed而Graph partial。**事件、Case、Run锚点、分诊判定与调查交付不能用同一个字段替换。** 同事件另一个成员是 `f7af404b-26a6-5d15-bd6c-3a872bdaf451`；在当前V2中，这两个真实成员尚未形成可进入的事件行。

### 17.6 整个 Case 工作区：哪些属于案件管理，不由自动告警流程填齐

| Case区域 | 已有结构／接口 | 当前差距 |
| --- | --- | --- |
| 名称、说明、状态、严重程度、负责人、期限 | `aisoc_cases`及Case API的 `title/description/status/severity/assignee/sla_due_at` | 表/接口能力已有；六条自动告警均无Case，所以本批没有这些案件值。API主要字段与旧ORM的 `assigned_to_id/sla_deadline`不保证同步，不能混接 |
| 成员告警、当前对象、关联调查／历史 | Case `alert_ids`、告警 `case_id`、已确认的Run归属和输入快照 | 关系需同租户核对。历史Case Run应按持久归属保留，不能因当前成员移除就丢记录；本地整理Case不是后端创建Case |
| 案件摘要、判定、优先级评分 | 已有 `summary`等Case结构；具体可读响应按Case接口 | 不证明自动调查写回完整案件摘要/判定；当前页面0—100优先级评分不能直接对应旧Case字符串priority或告警分诊分数 |
| 案件任务、截止时间、责任人 | `aisoc_case_tasks.title/status/assignee/due_at`及任务接口 | 已有能力但自动流程未必产生任务；原型新增/完成任务仍是本地交互，不能当后端任务记录 |
| 评论、活动、附件、案件证据 | Case评论/时间线/证据等已有接口和结构 | 需逐项核真实Case返回及权限。自动调查工件不是人工上传附件；当前样例附件名称不证明实际文件存在；当前Case状态不能复原全部人工操作历史 |
| 启动／重跑调查、关联成员、管理、响应 | 对应创建/关联/启动及响应写入入口，见9.1 | **这是操作闭环差距，不是补几个读取字段就能完成**。本轮不接写入，不触发模型、审批或真实厂商动作 |

[Case接口源码](../../services/api/app/api/v1/endpoints/cases.py)是本地可用能力依据，不作为本轮线上读写验收。案件协作资料应归Case模块承接；不要求告警处理器为每条告警自动建立Case并生成负责人、任务、附件和评论。

### 17.7 本轮明确的差距与建议承接顺序

| 顺序 | 具体差距 | 谁承接／已有基础 | 本轮结论 |
| --- | --- | --- | --- |
| 1 | 六条真实告警已有3个事件组，但事件列表/详情没有按它们取数；成员级来源等列表字段也未完整暴露 | 事件读取/后端呈现模块复用 `F.incident_id`及告警事实，前端沿现设计映射 | 优先补读取和同范围聚合，保留原设计样例；不先造事件调查结论 |
| 2 | 事件标题/说明、状态、负责人、分类、优先级、标签与人工活动缺完整事件级合同 | 事件管理模块；告警字段只能提供成员事实，Case表不能替代事件对象 | 记录待承接字段及业务含义；本轮不决定新表或自动聚合算法 |
| 3 | 原始主机/账户存在，库存资产、资产标签和处理负责人缺关系/本例未分配 | 资产匹配、用户与分配模块；复用既有表和键 | 保留原始对象和未分配，不填默认库存身份或标签 |
| 4 | 92条过程仅81条进入步骤视图，工件正文、模型输出未全部提供可读入口 | 调查读取/前端适配；复用现有events、artifacts及正文接口 | 已保存但未展示；按Run和kind读取，避免错把整段报告拆成必填字段 |
| 5 | 工具preview最多200字符、阶段输入输出有限、精确证据采用关系不完整 | 对应调查模块；沿其已规划的独立版本和交付范围推进 | 留存粒度差距，前端无法恢复旧原件；不把本地新版源码当旧服务已发布 |
| 6 | 事件/Case编辑、任务、反馈、审批和响应在当前页面仍主要是本地交互 | 对应业务读写模块，复用既有API并补真实权限/结果回显 | 功能接入差距，不在本轮改页面或启动后端实现 |

另有五处**展示统计口径待后续接入时修正**：①队列压缩混用67条混合来源告警与12个设计事件；②攻击中断用样例标签充当执行成果；③优先级因素是前端样例数值；④资产数实际含账户/IP等实体；⑤“有关联调查”的告警计数仅接受completion=partial/completed，会漏掉历史Case这种有真实调查但完整性未知的记录，而另一处Run列表仍可展示它。第五项应以真实调查启动/阶段及输入关系判断“有关联调查”，不能为了计数给未知完整性补completed。以上只登记，不在本轮修改页面。

**本轮核验范围：** 本地原件重数为6Alert/6Run/92事件/77工件/11成本行；工具49、前端步骤81及差额11按kind核对；Fusion归组3×2；链图封装与空态逐份核查。原件SHA-256为 `e751eb2e57790dbc696c931d5179b4e780bcdb8bab089286c880ec497eae1ec9`，本机增量统计保存在 `.local/verification/v2-field-mapping-20261028/`。没有新远端读取、清理/重放/模型调用、业务源码/页面修改、部署或Git提交推送；这次是字段可对应性核对，不追认调查内容质量或未发布能力。

## 18. 2026-10-28：告警流程数据同步到 V2

用户在第17节字段核对后明确要求“更改同步前端上述业务的数据”。本节记录实际完成内容，覆盖第17节中“未展示”的对应问题；第17节仍保留为修改前盘点。只读取本机10月25日保存结果，没有重新查询21/20、运行模型、重放告警、修改后端或部署。

### 18.1 事件页逐区域落地

| 页面区域 | 本批同步内容 | 仍保留的语义边界 |
| --- | --- | --- |
| 列表 | 按同租户Fusion incident_id追加3个事件，每组2条真实成员；原12个事件保留，共15个 | 名称用源主机和成员数，说明列出成员标题，严重程度取成员最高等级；这些是展示聚合，不是已持久化的事件管理记录 |
| 统计、侧栏 | 本批6条告警→3组，队列压缩50%；缺优先级显示“尚未评分”，无自动中断执行记录保持空态 | 不把混合历史/原型的67条告警除以12个样例事件，也不以标签证明自动中断 |
| 详情抬头、管理 | 时间来自成员event_time及updated_at；缺状态/负责人显示未记录，分类未设置、优先级空、标签空 | 不拿告警状态、分诊分数或受影响账户替代事件管理值；仅改标题不会默认改状态/分配成员告警。管理仍只保存浏览器本地状态 |
| 概览、成员告警、基础调查 | 展示成员等级、时间、来源、首次分诊评分、已有解释、关联Run与partial摘要 | 分诊和Graph结果分别展示；Run已结束不证明调查完整，BTP分诊关闭不计入已调查 |
| 关联关系、涉及对象 | 源告警中的主机、账户、IP及直接归属连线；可点击回查告警/原始对象 | 每个组4个涉及对象；没有库存关系时显示“未关联库存”，不补Contoso组织、库存ID、资产标签或因果链 |
| 关联告警链 | 选择当前成员作为种子，读取该Run当时保存的Chain与实际窗口，可进入对应调查 | 不用当前时间重算旧样例窗口；候选不自动加入事件，空候选不是数据消失 |
| 关联AI调查 | 每个组2个Run入口；是否进入后续调查看实际执行记录 | 六个Run为5次部分调查、1次分诊后关闭；没有给六条源告警补Case |
| 证据与处置 | 成员来源材料、原始告警入口、各Run的工具/工件/报告入口及已执行动作数 | 没有已分类证据/实际执行时不制造“恶意证据”或处置成功；工具/工件在调查中按Run查看 |
| 处理活动 | 成员发生记录和同范围Run过程按时间倒序展示，可回查来源Run | 记录已保存不等于查询成功或执行成功；不制造人工处理记录，不挂到无关Case |
| 重置 | 恢复原样例时同步追加这3组，刷新与重置行为一致 | 不改V1，不清理用户原浏览器状态；验证重置用离线状态替身，不对用户浏览器执行重置 |

直接入口：[本批三个事件](http://127.0.0.1:4174/#/incidents?q=DEMO)、[DEMO-FIN-11事件](http://127.0.0.1:4174/#/incidents/7bde0c0b-0d18-4abc-9382-9752f2ae5e98/summary)。三个ID及源成员保留在 `alert-flow-data.js`，`alert-flow-workspace.js` 按ID追加，不覆盖已有本地修改。

### 18.2 调查页新增可读材料

| 区域 | 完成本批同步 | 尚未填造的内容 |
| --- | --- | --- |
| 调查记录 | 六Run全部92条事件，补回原遗漏6条llm_call及5条graph_usage；保留记录ID、seq、时间、角色、类型及可读payload | seq不作为严格写入游标；隐藏推理与提示词不进入公开页面 |
| 查询与证据 | 原49条工具记录保持；77份工件可展开来源ID、关联event_id、hash、时间及可用内容 | 工具200字符preview仍受原留存限制；不能在前端补出未保存的全量查询结果 |
| 工件正文 | 31份完整内容、40份节选、6份提示词仅目录。可按artifact ID定位且只能读取同Run工件 | “完整”是可读业务内容完整，不保证JSON原字节排版；原件hash始终标识源完整材料，节选不冒充原件全文 |
| 调用材料 | 六份首次分诊回复可读；graph_llm_exchanges仅输出角色、模型、时间、耗时、hash等元数据 | 不把Graph隐藏推理或整段模型提示投到页面；模型结论仍需人工核查 |
| Chain / Path | 五份Chain中2次有候选、3次查无候选；五份Path均因无关联Case而跳过 | 不借10月21日历史Case的路径填当前自动Run；“未关联Case”不改成无风险 |
| 调查覆盖 | 根据实际执行阶段判断是否调查；历史联合Case的完整性未知也能计入已调查 | 已调查、已完成、完整性、判定、费用分别保留；无价格不补0成本 |
| 案件工作区 | 原Case及历史样例保持，关联告警后沿既有读取方式进入对应Run | 本批没有后台创建Case，没有把单告警Run扩成事件联合Run，没有接后端操作按钮 |

[第一条自动调查的查询与证据](http://127.0.0.1:4174/#/investigations/d141b0e3-16cc-5a0b-8d7f-35159342efe6/tools)。数据采集时间为2026-10-25 11:59:33（上海），本次是**保存结果的离线页面同步**，不是10月28日实时服务连接。源文件SHA-256为 `e751eb2e57790dbc696c931d5179b4e780bcdb8bab089286c880ec497eae1ec9`；导出器核同租户、Run锚点、工件字节/hash及event关联，输出清单见 `alert-flow-data.manifest.json`。

### 18.3 验证和未处理范围

52项前端测试通过，其中9项针对本批、原告警291种HTML呈现比较保持。浏览器核三个真实事件、成员/对象、种子Chain、材料入口、工件展开及事件管理未知选项；原V1与冻结包52份文件hash保持，原告警模块/源数据及其他任务的统一图文件保持。独审首次提出“未知管理值被默认改写”“重置漏事件”两项，修复后9项定向复核通过，最终限定ACCEPT、0剩余必须修。

第17节仍未解决的事件管理后端合同、库存关系、实时读取/写入、工具全量留存、响应执行闭环、模型内容质量，不因本批页面可读而宣称通过。另一个统一调查图change独立保留，本批不接管其任务或验收。详见[V2回执](frontend-v2-verification.md)及本批OpenSpec审计。

## 19. 2026-10-29：将已有材料补入本地 Case 工作区

用户明确指出：没有自动创建Case不代表没有可供Case使用的数据，要求有数据则补齐。已按10月25日六告警的同租户Fusion组追加3个**本地整理Case**，原16个Case与原告警保持，总计19个Case、67条告警、15个Run、15个事件。使用既有保存结果，不查询或创建后台Case，不启动新调查。

### 19.1 三个集合的实际材料

| 本地Case | 当前初始成员 | 既有Run | 过程记录 | 工具记录 | 工件 | 报告 | 调查完整性 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DEMO-FIN-11 | 2 | 2 | 28 | 12 | 28 | 2 | 2次partial |
| DEMO-APP-12 | 2 | 2 | 44 | 28 | 28 | 2 | 2次partial |
| DEMO-DATA-13 | 2 | 2 | 20 | 9 | 21 | 1 | 1次partial、1次仅分诊关闭 |
| 合计 | 6 | 6 | 92 | 49 | 77 | 5 | 5次partial、1次未升级 |

[打开本批Case列表](http://127.0.0.1:4174/#/cases?q=local-socai2)，[打开DEMO-FIN-11案件概览](http://127.0.0.1:4174/#/cases/local-socai2-7bde0c0b-0d18-4abc-9382-9752f2ae5e98/overview)。

### 19.2 逐区域补齐范围

| 区域 | 已补内容 | 不由已有材料推定的内容 |
| --- | --- | --- |
| 列表与侧栏 | 3个明确本地整理的Case、成员/对象、来源、初始最高等级、本地创建时间；调查状态单列部分交付 | 初始“新建”是本地案件状态，不是源服务Case状态；优先级和案件判定不自动评分 |
| AI调查首页 | 汇总两次既有Run；逐次显示首次分诊与评分、后续调查判定、原始输入、停止原因、完整性和工具/工件计数 | 不把两次单告警调查写成一次联合调查或统一案件结论 |
| 案件资料 | 当前成员、涉及对象、已有调查/材料/报告统计、来源事件链接；本地整理时间与源采集时间分开 | 源Case为空；初始负责人未分配、分类未设置、期限未设置 |
| 案件证据 | 当前成员原始告警入口；按Run展开77份工件目录和可用内容，可转工具/报告 | 原工件不是人工上传附件，也不自动成为已判恶意的证据；仍按31完整/40节选/6提示词仅目录提供 |
| 案件关系图 | 当前成员与主机/账户/IP直接来源关联，初始每组6节点8边 | 不补攻击因果或Case路径；5份Path仍为当时未关联Case的跳过记录 |
| 调查历史与详情 | 精确引用六个既有Run，各自六个视图沿原读取可访问 | 当前Case集合不改写原Run输入与源Case归属，不重新执行查询 |
| 处理活动 | 当前成员发生记录＋已引用Run过程，按时间倒序；点击可进入当前Case中的对应调查 | 这些自动记录发生于整理之前，不伪装成后台Case操作历史 |
| 任务、评论、附件、响应 | 保持已有交互和空态，报告/建议/执行从原Run查看 | 不从报告正文强拆任务，不补附件或执行成功；写入仍仅浏览器本地 |
| 日期筛选 | 预置区间截至已保存案件最新创建日期，本批截至10月29日；自定义区间保持输入 | 修复旧固定10月24日导致新Case筛选后消失的问题，不改变告警日期规则 |

### 19.3 关系、留存与验证

本地ID为 `local-socai2-<Fusion incident_id>`，`localCollection/alertFlowCollection=true`，`sourceCaseId=null`；`alertIds`是当前集合成员，`sourceAlertIds/sourceRunIds`记录初始来源与材料引用。引用Run按ID、环境、租户核对，成员移除仍能回查原Run，关系图和当前成员资料则随当前成员变化。六个源Alert.caseId和Run.sourceCaseId仍为空，各Run仍只有1条输入。

组织时间为2026-10-29 07:51:56（上海）；采集时间仍为10月25日11:59:33。导出器新增显式 `--organized-at`，重建命令见[V2说明](../../prototypes/security-pages-v2/README.md)。只追加不覆盖浏览器编辑，原重置路径可恢复3个集合。

直接验证59项通过（原52＋本批7），包含3集合×11区域、6Run×6视图、同来源隔离、成员移除后回查、编辑/重置、日期范围与291种原告警HTML比较。浏览器核列表、汇总、工件展开和Case内Run跳转。具体独审及最终收口见[V2回执](frontend-v2-verification.md)。本批不更改原20、10月21日历史Case或另一统一图change的结论；无新远端请求、模型、重放、后端改动、部署、提交或push。


## 20. 2026-10-29 Case 数据整合

用户明确主要整合数据，原设计数据可保留，同时包含AiSOC。最终入口为 [全部Case](http://127.0.0.1:4174/#/cases?data=all)，不再把旧17420案例作为默认交付入口。

保留19 Case/67 Alert/15 Run；按20保存告警incidentId追加3个事件视图后共18事件。7个AiSOC Case引用13个原Run，共192过程/90工具/108工件目录/11报告。6个本地集合不等于源后端创建Case；实际历史联合Case独立保留。默认排序AiSOC优先、原12案例继续可达，来源筛选及指标一致。所有已保存Case材料页统一展示逐Run工具/工件/报告，活动使用已有记录；缺正文、未生成Path、失败、partial和未知完整性保留。

20事件仅投影原告警关系（2/2/1），无事件第6条不补造关系；历史联合3告警也不新造事件。Case/事件按成员和环境租户互链；replay告警顶层缺来源时使用已有alertFlowData精确成员投影，不按标题/时间/同名主机猜配。无效详情不回落原样例。原始文件不改，改动仅本地适配和展示。

验证、限定独审与保存检查见[本批交付回执](frontend-v2-verification.md)和 `consolidate-v2-case-data` 归档记录。未实时访问20/21，无新的业务/模型执行、后台Case写入或部署。
