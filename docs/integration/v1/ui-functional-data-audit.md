# 告警与调查 V1：功能必要性与数据可得性审计

拆分说明：后续仅按用户要求调整文档分类和导航；下列审计证据/结论仍对应原审计时点，新字段字典的解释补充另作静态复核。拆分时另纠正一处原展示枚举拼写：调查完成度的程序值为`completed/partial`（不是`complete/partial`），观察到的partial样例及原审计数据不变。

审计日期：2026-10-23；最新生产只读取数时间：16:42（Asia/Shanghai，UTC+8）。本篇是[页面建议](page-elements.md)及[取数映射](page-data-mapping.md)和[七份功能示意](ui-wireframes/README.md)的审计附件，不另立一版需求。

**审计结论：四页的信息范围有业务依据，但必须按字段条件交付，不能把90项字段组全部宣称为“当前线上已有”。** 告警事实、首次分诊、自动调查的状态/材料/报告已经有可读取数据；若干组合字段只有部分子项有值；人工复核、统一根因/影响结论及逐条证据支持关系尚无统一持久合同；新版单次工具留存仅有本地验证。数据能读到，也不代表分析内容已经正确。

对第一版的判断如下：

| 产品范围 | 审计判断 | 第一版处理 |
| --- | --- | --- |
| 告警列表、告警详情 | 原页面已有，来源/时间/对象/状态/分诊理由是判断与交接必需信息 | 保留；来源、时间和分数采用本文核实后的语义，不能照搬旧适配器混用逻辑 |
| 独立调查列表、无Case的Run详情 | 是本版必要新增组织方式；原Case页面已有部分内容，但没有证据证明原版已有完整独立调查页面 | 保留；实际生产自动调查无Case，需要按Run定位结果；这不表示前端已经实现 |
| 证据、过程、Markdown报告 | 原版Case的Ledger/Report及图页有依据；本产品还需要解释未完成与缺源 | 保留；只展示真实留存，预览/截断/完整正文分别说明 |
| 空值与资料覆盖 | 必要。没有命中、没有配置和查询失败具有不同业务含义 | 保留状态，不用绿色“正常”填补资料缺口 |
| 负责人、人工复核、根因/影响、证据支持连线 | 产品有价值，但当前统一数据或人员映射不足 | 不作为已具备能力；按具体行的条件隐藏、提示缺失或后置 |
| 单次工具结构结果 | 有必要，但当前生产镜像没有本地新版合同 | 线上使用旧预览；新版仅作开发版说明，部署及接口验收后才开放 |
| 费用、模型、原始交换、完整hash | 有诊断/成本追溯价值，不能都占据值班人员默认视野 | 详情折叠或有权限时展开；金额缺计价时明确未计价 |
| 独立工作队列、PDF、Replay、反馈、Playbook、真实封禁隔离 | 不阻碍本版查看告警与调查结果 | 保留已有实现，不纳入本版必须交付，不借审计启动实施 |

**图的使用边界：七张Mermaid只展示功能要素与字段对照，不是UI设计稿或交互原型。布局、页签样式、组件、尺寸、配色和交互由后续设计确定。网页截图及截图对照已取消，本次没有采集截图。**

## 1. 审计范围、方法与证据强度

### 1.1 两个问题分别判定

每项均回答：①它帮助使用者作出什么判断，原页面是否存在，若新增为何必要；②它从哪张表、哪条JSON路径或哪个接口取，已观察到什么值、哪些子项为空、是否需要聚合、是否只在本地。必要性是产品判断，可得性是事实判断，二者不能相互替代。

“原页面有”不直接等于本版必须做；“数据库有列”不直接等于列有值；“HTTP 200”不直接等于过滤有效；“正文hash匹配”只证明读取和留存一致，不证明模型结论正确。本报告90项是90个**字段组**，包含重复展示与组合字段，不是90个独立功能，也不是90个已填满的原子字段。

### 1.2 本次与复用证据

| 证据 | 实际覆盖 | 能证明什么 / 不能证明什么 |
| --- | --- | --- |
| E1：本轮16:42生产PG只读事务 | `aisoc/public`六核心表167列；本租户3 Alert/3 Run/0 Case；定向读既有两例的Alert、Run、21事件、21工件、3成本行 | 证明当时表结构和所选数据可读；不外推其他租户、所有来源或所有状态 |
| E2：本轮10个reader GET | 告警列表/无匹配搜索、调查列表、两例Alert与Run详情、调查例事件/工件目录/MD正文，全部200 | 确认这些读取路径可访问；搜索实际未过滤，列/字段仍有缺口 |
| E3：14:39既有字段验证 | 41 GET、两例全部21工件正文、processing-context和图接口等，见[原字段证据](ui-field-verification-20261023.json) | 当前上下文类结果是14:39动态快照，本轮没有重查；历史Run工件正文哈希本轮全部一致 |
| E4：本地两个停止样例 | 真实本地runner/Deep/ledger与隔离PG，模型/工具为替身；与直接交接用例共8 passed | 证明本地工具留存和停止后冷读取，不能证明生产部署、真实模型输出或完整RLS/HTTP已验 |
| E5：本地原版前端参考副本与既有浏览记录 | Alerts、AlertDetail、Case Investigation/AttackPath/AttackChain/Ledger/Report；下文给文件定位 | 参考源码能证明功能设计/调用存在，不证明20服务器此刻所有交互都正常；本轮没有重新浏览或截图 |
| E6：已有人工真实模型采用样例 | 2回复/2714 tokens；采用结果与原文遵循问题分别保留 | 只证明该本地采用样例；`db_writes=false`，不得当作生产可查阶段JSON |

本轮API镜像为 `sha256:5a1e1fd8cf08349438e7d1346a25c9599bff7937df5d22ea94426e77b33f2aa9`；Agents为 `sha256:49643b84b8f797229d793adbc462c8c8e5428cfa585934f0345b8b3400a25ba9`。未因本地新增代码而推断线上已更新。

本轮原始读回SHA256为 `4cc00c9a09856cc87adbcab1d441fad290e04b7953b8b776169b7ad3b9984bd5`，原件保存在 `.local/verification/ui-v1-20261023/audit-online-readback.json`。对外交接用[脱敏审计数据](ui-functional-data-audit.json)，不包含认证凭据或完整模型提示词。

### 1.3 可得性标记

以下逐字段表保留组合字段内部的差异。线上实值不意味着所有来源都有值；线上空态只允许显示缺失状态；派生表示需要业务后端组装，不是可以直接SELECT同名列。对于没有统一合同的字段，仅有报告中的一段文字不算结构字段已具备。

## 2. 原页面依据与业务功能取舍

参考源码为本地 `.local/initialization/full-source-staging/apps/web/src/` 副本。既有[功能对照](../../operations/alert-function-alignment.md)固定上游revision `34ca18c57dd4175539e5c6dd3d04a72dc057306b`；本轮没有重新核定该副本与revision、20当前部署镜像逐文件相同。因此下文“原版已有”严格指已审查参考副本中的实际render/handler，不能据此宣称20此刻完整可用。

### 2.1 原前端代码证据索引

下文U编号指下表，每行已给出可定位文件和关键行；“复用原型”仍需对21的数据合同重新适配。

| 证据 | 实际位置 | 已证明什么 / 没证明什么 |
| --- | --- | --- |
| U01 告警列表基础 | [AlertsView.tsx:165](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/AlertsView.tsx:165)、[273](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/AlertsView.tsx:273)、[314](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/AlertsView.tsx:314)、[477](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/AlertsView.tsx:477)、[679](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/AlertsView.tsx:679) | severity/status按钮；标题/首个MITRE/来源/可选负责人/Fusion置信等级/严重度/状态/createdAt；同过滤范围四统计；上一页/下一页。默认entities，告警页sort=priority。没有该FiltersBar中的来源、对象、发生时间范围、关键词控件。 |
| U02 告警详情 | [AlertDetailView.tsx:856](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/AlertDetailView.tsx:856)、[967](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/AlertDetailView.tsx:967)、[980](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/AlertDetailView.tsx:980)、[1004](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/AlertDetailView.tsx:1004)、[1049](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/AlertDetailView.tsx:1049)、[1071](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/AlertDetailView.tsx:1071) | 详情头、Overview/Timeline/Raw，Description、Source/Source Ref/Tenant/Assignee/Created/Resolved/Tags、MITRE、IOC、Raw和Wazuh locator。不是通用所有来源规则/命令/端口已有标准专栏。 |
| U03 侧栏与分诊 | [InvestigationRail.tsx:137](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/InvestigationRail.tsx:137)、[383](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/InvestigationRail.tsx:383)、[429](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/InvestigationRail.tsx:429)、[444](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/InvestigationRail.tsx:444)、[540](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/InvestigationRail.tsx:540)、[579](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/InvestigationRail.tsx:579) | Story/Details；AI verdict/aiScore/aiSummary、融合narrative、相关实体、短时间线、建议。原分诊理由读aiSummary；本项目改读T结构字段属于必要适配。 |
| U04 旧适配器风险 | [api.ts:1573](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/lib/api.ts:1573)、[1586](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/lib/api.ts:1586)、[1601](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/lib/api.ts:1601) | source只读source/connector_type，未读fusion_identity；createdAt优先created_at，不是event_time；riskScore会回落ai_score或Fusion confidence；缺时间还会默认当前时间。照搬会使本项目显示unknown来源、混淆时间/评分。 |
| U05 人工操作 | [AlertDetailView.tsx:385](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/AlertDetailView.tsx:385)、[530](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/AlertDetailView.tsx:530)、[885](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/AlertDetailView.tsx:885)、[BulkTriageBar.tsx:68](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/BulkTriageBar.tsx:68) | 告警人工调查走创建Case→关联告警→Case investigate；Create Case/反馈/批量分诊确有处理代码。不是当前生产写操作验收；bulk triage不等于bulk close。 |
| U06 队列 | [QueueView.tsx:64](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/queue/QueueView.tsx:64)、[334](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/queue/QueueView.tsx:334)、[537](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/queue/QueueView.tsx:537)、[740](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/queue/QueueView.tsx:740) | Mine/Unassigned/All、period、SLA、Claim/Release/Snooze/Open。查询queueApi，不是调查Run。不能用该页证明独立调查列表存在。 |
| U07 Case调查 | [CaseWorkspace.tsx:395](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/CaseWorkspace.tsx:395)、[516](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/CaseWorkspace.tsx:516)、[896](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/CaseWorkspace.tsx:896)、[1171](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/CaseWorkspace.tsx:1171)、[1228](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/CaseWorkspace.tsx:1228) | Case页签、启动/恢复调查、idle/running/failed/completed、Recon/Forensic/Responder卡、Forensic假设/置信度、建议。原completed显示Investigation complete；没有本项目已要求的partial三状态语义。 |
| U08 Ledger | [InvestigationLedger.tsx:112](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/InvestigationLedger.tsx:112)、[178](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/InvestigationLedger.tsx:178)、[322](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/InvestigationLedger.tsx:322)、[512](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/InvestigationLedger.tsx:512)、[569](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/InvestigationLedger.tsx:569)、[678](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/InvestigationLedger.tsx:678)、[729](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/InvestigationLedger.tsx:729)、[914](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/InvestigationLedger.tsx:914) | Case内Run picker（limit25）、kind/agent过滤、时间/seq/执行者/耗时/摘要、模型费用、解释抽屉、工件正文/bytes/hash、导出/回放。不是独立全量Run列表；注释“every prompt”等不能当全文持久证据。 |
| U09 图 | [CaseWorkspace.tsx:1388](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/CaseWorkspace.tsx:1388)、[1429](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/CaseWorkspace.tsx:1429)、[1663](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/CaseWorkspace.tsx:1663)、[1693](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/CaseWorkspace.tsx:1693)、[1738](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/CaseWorkspace.tsx:1738) | Case当前Path/Chain、窗口、置信度、实体图/链列表、空态。未证明自动Run历史Alert邻域已有同样页面；原“reconstruct lateral movement”“entities or MITRE”措辞不能继承为事实。 |
| U10 报告 | [CaseWorkspace.tsx:2024](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/CaseWorkspace.tsx:2024)、[2049](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/CaseWorkspace.tsx:2049)、[2065](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/CaseWorkspace.tsx:2065)、[2109](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/cases/CaseWorkspace.tsx:2109) | Case reportMd、MD/PDF下载、无报告空态；实际正文用pre展示原文，不是Markdown预览/原文双模式；新预览为必要性较低的体验增量，MD读取/下载才是本版交付。 |
| U11 独立Run路由边界 | [AlertDetailView.tsx:310](/Users/lychee/Documents/project/socai2/.local/initialization/full-source-staging/apps/web/src/components/alerts/AlertDetailView.tsx:310)，检查参考副本`src/app/**`全部文件路径；原实际入口为`(app)/cases/[id]/page.tsx`和上述U08组件 | 存在`/investigations/{runId}`链接，但未找到对应独立investigations路由文件；不能据Link、API或组件名认定完整页面已实现。 |
| U12 既有核查边界 | [alert-function-alignment.md](/Users/lychee/Documents/project/socai2/docs/operations/alert-function-alignment.md)“20的Case页面与full需求”及“原版实现差距” | 原三卡内存恢复、Tasks/Notes/Resolution等接缝、原图/报告声明与实际区别已登记；原完整服务迁移不等于前端已迁。 |

### 2.2 所有功能组的产品判断

原版已有并不自动成为V1必要；原版没有也不自动删除。判断只回答分析员完成“发现→研判→接手”是否需要，且是否有可解释数据。

| 功能组 | 原版依据 | 决策及产品理由 | 数据/实施边界 |
| --- | --- | --- | --- |
| 两一级菜单、四页七图 | U01/U02/U07；独立Run见U11 | 必要新增信息架构。减少Case前置，让生产自动调查可达；七图是四页分区，不再扩七菜单 | 入口/路由需新实现，不能称20页面原样复用 |
| 告警统计4卡 | U01:477 | 保留，提供当前工作量与优先级；不加降噪率/MTTR | 全过滤范围统计；图中2条只是固定样例，生产实读3；手工筛子集不可称生产总量 |
| 等级/状态筛选 | U01:165 | 原版保留，基本排查入口 | 旧API有条件；只读取基础列表不等于每枚举已验 |
| 来源/发生时间/对象/关键词 | 原告警FiltersBar没有；不是Queue period同义 | 必要新增；查指定设备/事件/来源是工作必需，不强制原版缺失就不做 | 字段可直查不等于过滤实现完成；keyword/source/time/object无既有HTTP完整验证，开放前落实SQL/统计一致性 |
| 排序/分页/总数 | U01:314/679 | 严重程度优先合理；发生时间与入库时间选项需清楚；20条/25条只是可选配置 | 原priority是severity再created_at；不要标AI风险排序；Run recentN不得伪造全量 |
| 列设置、页大小切换 | U01只见固定row/分页，无本次列选择器 | 可后置体验新增；90项不等于都要动态列配置 | 不必为首版另做服务端保存偏好；A10/A11可固定折叠 |
| 列表来源摘要/对象/分诊/调查入口 | 原row U01无这些全套，侧栏U03有部分 | 必要新增。减少逐条开详情，直见需要接手的partial | 列表来源、目标Run关系需要聚合；current A与Run快照不能混用 |
| 右侧Story/Details | U03 | 原型可复用但后置侧栏，详情页已覆盖同任务 | 双入口不要各自复制一套判定逻辑 |
| 来源身份/事件引用/规则/时间 | U02/U04仅部分 | 必要增强可追溯性；上游ID/规则可折叠 | 取数source不能复用旧adapter；event_time要新映射；引用数不是次数 |
| 对象、进程命令、网络角色 | U02 IOC/Raw，U03 entities | 关联对象必要；进程命令端口依来源条件展示 | 不能保证每来源都提供；不自动把对象命名受害资产 |
| Raw/JSON/复制/原快照 | U02:1071 | 必要可核对入口；JSON树与复制为小体验新增 | raw_event不是全部原日志；command/secret等内容按已有权限，不以展示范围扩大调用权限 |
| 来源/融合/分诊/调查分区 | U03有分诊+narrative，U04混风险字段 | 必要修正，不属于单纯美化 | 三置信度不同；85%/19%不可称恶意概率；说明原文不能当事实 |
| 当前资产/身份/漏洞/历史/UEBA覆盖 | 原选定告警组件无processing-context卡 | 有条件必要新增：让分析员知道缺了什么；默认紧凑覆盖摘要 | 本例多为空；未验丰富明细或全部资料类型，不能承诺完整CMDB/UEBA分析 |
| 告警处理记录 | U02 timeline、U03 miniTimeline、U08 | 必要，可从Run记录补空miniTimeline | ts是处理/留存时间，不是攻击经过；缺省duration0不显示0ms实测 |
| 独立调查列表及筛选 | U08只有Case picker，U11无独立路由 | 必要新增：自动Run无Case并存在多个目标/历史Run | Run target/trigger/completion分类需聚合；只triage不能计调查；近期limit不能当总量 |
| 调查三状态、停止原因/缺源 | U07原只statuscomplete | 必要新增，直接解决真实completed+partial误导 | 已有GE/G可取；执行状态、完成度、分析结论各自来源固定 |
| 最终摘要卡 | U07三角色摘要 | 必要的是可读状态与缺口摘要；新增模型summary后置 | 当前无统一final_summary，采用确定性状态组合；工具JSON不是总摘要 |
| 根因/影响/逐项证据支持 | U07有hypothesis卡，U08有工件关联 | 不宜承诺已验证结论；空占位可后置 | 无统一稳定结构与证据支持合同。应写“当前未提供结构化验证结果”，不暗示已排除入侵 |
| 材料目录+正文 | U08:914已有按步骤工件 | 必要新增集中Run目录/懒加载正文，支撑取证和交接 | 21工件全文可读仅是这批工件；工具预览仍约200字；内容有界不等于全文 |
| 五类读取回执与知识引用 | U08能显示泛工件，无专门5类卡 | 必要的覆盖摘要新增；丰富引用详情按有值显示 | 本次五类no_match、知识0引用；不画假资料或“知识已支撑结论” |
| 关系图/候选链/Case Path | U09原Case实时图 | 历史快照关系视图为有用新增；Path未关联为空可收起 | 不以5邻居/6可达节点称确认攻击路径；不把当前查询混入当次证据 |
| 工具结构状态/留存定位 | U08泛payload，无本地新tool_result专卡 | 开发版保留；生产入口暂缓 | 两例本地PG成功状态已测不代表所有状态均有真实来源；旧Run不回填 |
| 过程筛选/点击模型或工具详情 | U08 kind/agent及Explain | 保留，便于查用了什么和何处停止 | 每次实际输入完整性不能从hash推断；没有精确wire-body/隐藏推理合同 |
| MD读取/下载/Case报告 | U10 | 保留基础交付；无需Case的通用Run工件读取为必要新增 | MD原文有旧running，外层partial必须解释；重试读取不重启调查 |
| 预览/原文切换、PDF | U10原pre+MD/PDF | 可渲染预览为体验新增；PDF按既定范围后置 | 不因原PDF按钮存在就要求本版实现；过滤危险HTML不改原MD |
| 用量、模型、hash/bytes、工具轮数 | U08大量原有技术诊断 | 保留折叠高级信息；不是值班首屏任务 | 费用未计价不为免费；成本/模型表不等于实际攻击证据；不需要把所有诊断做成独立卡 |
| 认领/转派/关闭/暂缓 | U05/U06 | 有协作必要，但当前读结果V1可后置，不假装按钮可用 | 现有入口存在≠21操作验收；不直接UPDATE库触发工作流 |
| 人工发起调查/创建Case/关联 | U05/U07 | 可保留后续入口；自动Run查看不要求再点一次 | 手工会触发真实工作/预算，应走既有Case接口；不把escalate当调查 |
| 批量、保存视图、反馈/重分诊 | U01:501、U05 | 原版有部分，均非本版必要；后置合理 | 不继承未验状态变更/权限/历史效果承诺 |
| 实体默认视图、Queue/SLA | U01:322/U06 | 暂不独立上架合理；避免扩全平台 | 告警对象字段足以当前主链；不能因此说原版不存在这些功能 |
| Replay/完整重放、Copilot、War room等 | U08/U05/U12 | 后置；不是阅读已有调查必需 | 代码存在不证明当前数据全留存或外部依赖可用；不新增模型/消息行为 |


### 2.3 必要性分类统计

| 分类 | 字段组数 | 含义 |
| --- | ---: | --- |
| O | 36 | 原版直接或近似展示，需适配 |
| N | 45 | 有业务理由的新字段/语义/位置 |
| H | 7 | 后置或条件开放 |
| X | 2 | 当前不宜承诺为结构化事实 |

N包括语义纠正和信息前移，不意味着45个全新功能；O也不意味着当前生产API直接可用。位置仅表示阅读优先级，详/诊断内容可折叠，最终布局另定。


## 3. 数据库与取数链审计

### 3.1 数据库及主关联

当前生产读取位置为 **PostgreSQL `192.168.1.21:5432` / database `aisoc` / schema `public`**，样例租户 `f6a5c700-69b8-44fc-8238-609362fb1a9f`。连接凭据沿[配置交接](configuration.md)提供，不写在审计或前端代码中。表/JSON/SQL细节仍以[数据库字典](table-fields.md)和[取数附件第1章](page-data-mapping.md)为准。

| 表 | 本轮列数 | 页面用途与关联条件 |
| --- | ---: | --- |
| `alerts` | 63 | 告警当前事实与状态；先按`tenant_id,id`定位，source从`enrichment_data.socai2_fusion.identity.source`提取 |
| `investigation_runs` | 18 | Run状态/时间；`case_id`是历史目标字符串，自动例指Alert UUID，不是Case外键 |
| `investigation_events` | 13 | 分诊、完成度、模型/工具记录；按同租户`run_id`读，不把`seq`当严格写入游标 |
| `investigation_artifacts` | 10 | 同Run的JSON/MD正文及hash；`event_id`仅指生成/关联步骤，不是“证据支持该结论”关系 |
| `aisoc_run_costs` | 15 | 按模型聚合的Token/调用/计价信息；tenant/run字段为TEXT，注意类型绑定及先聚合 |
| `aisoc_cases` | 48 | 人工Case及其成员关系；本生产租户0行，无Case不能阻挡自动Run阅读 |

六表167个列名/类型与[此前目录](data-catalog.json)逐项相同；本轮未重新审计全部25表428列或全部约束。支撑表仍沿原目录和14:39查询证据。

### 3.2 后端实现中必须守住的取数语义

1. 当前Alert、首次Fusion交付快照、当次调查输入、当前动态上下文分别命名。已分诊Alert的首次快照仍可能是`new`；不得用旧快照覆盖当前状态。
2. `Run completed`、`GE.completion=partial`、`G.verdict=needs_review`可以同时成立。完成度在**事件payload**；本例graph结果工件没有completion键，不能读错层。
3. 调查列表须识别是否实际进入调查，不能直接把所有Run数组都当调查。仅分诊例有Run和工件，但无调查、无报告；正在调查但还没产出报告的Run仍应列出。跨入口识别规则需接入方明确，不能仅按是否有MD筛选。
4. 告警关联Run需按已确认的Alert/Case/Incident目标语义处理；不得将全部`case_id`强转UUID关联Case，或仅取最新分诊Run充当最新调查。
5. `content`为TEXT：JSON类型先解析，`report_md`直接读字符串。相同kind可能多份，先固定Run和artifact_id；取最新时使用明确的时间/ID规则。
6. 事件展示用处理时间并保留ID；`seq=-1`需要首次完整读取，旧工具seq可高于后到graph结果，不按max(seq)盲增量。当前HTTP每批最多1000，超出时要有回看与完整性核对。
7. 费用、事件数、工件数分别聚合后再关联；避免事件×工件×模型行使统计倍增。运行iterations、Deep轮数、模型调用数、工具类别数、工具记录数分别命名。
8. processing-context是执行时生成的视图，没有同名持久表。展示当前补充资料时声明查询对象、范围、上限和时间；回看当次调查优先用其留存工件。

## 4. 90项展示字段逐项审计

本表同时列必要性、原版依据、数据库/接口定位、实际取到的子项与空项、以及第一版处理。表中原版源码证据代号见第2章；页面字段名称与主文档及七图保持一致。状态统计只描述字段组，不换算为“可上线百分比”。

| 数据状态 | 字段组数 |
| --- | ---: |
| 实值 | 46 |
| 派生 | 8 |
| 空态 | 10 |
| 部分/混合 | 21 |
| 缺合同 | 3 |
| 仅本地 | 2 |

取数路径简写如下；它们仅为本文别名，不是新表、视图或HTTP字段。`A`指数据库Alert行，勿与A01—A40编号混淆。

| 简写 | 对象/证据位置 |
| --- | --- |
| `A` | audit-online-readback.json $.sql.<sample>.alert（字符串JSON列先解析）=public.alerts |
| `F` | A.enrichment_data.socai2_fusion |
| `S` | F.delivery_snapshot.fused.alert |
| `R` | audit-online-readback.json $.sql.<sample>.run=investigation_runs |
| `E` | audit-online-readback.json $.sql.<sample>.events=investigation_events |
| `TE` | E[kind=triage_verdict]整行 |
| `T` | TE.payload |
| `GE` | E[kind=graph_result].payload |
| `G` | public.investigation_artifacts同tenant/run且kind=graph_result的content解析；完整读回位于online-readback.json相应工件响应 |
| `K` | public.investigation_artifacts同tenant/run的元数据；本轮$.sql.<sample>.artifacts |
| `BODIES` | public.investigation_artifacts同tenant/run的content或已读取blob正文；本例原始HTTP逐工件content，按kind归类仅适用于本样例各kind唯一 |
| `TOOLS` | E[kind=tool_call] |
| `NODES` | E[kind=graph_step] |
| `LLM` | E[kind=llm_call] |
| `X` | 原始读回kind=graph_llm_exchanges的content解析数组 |
| `C` | 新鲜SQL $.sql.<sample>.costs=aisoc_run_costs |
| `USAGE` | E[kind=graph_usage].payload |
| `P` | ui-field-verification-20261023.json $.online_samples.<sample>.processing_context（14:39历史动态读回） |
| `GRAPH` | kind=alert_graph工件正文解析 |
| `CHAIN` | kind=attack_chain工件正文解析 |
| `PATH` | kind=attack_path工件正文解析 |
| `READS` | 五个kind=*_read工件正文解析的按kind对象 |
| `KB` | kind=knowledge_base_read正文解析 |
| `REPORT` | kind=report_md原始正文 |
| `REPORT_META` | K[kind=report_md] |
| `LG` | local/timeout.json $.investigation_artifacts[kind=graph_result].parsed_content |
| `LT` | local/timeout.json $.investigation_artifacts[kind=tool_result].parsed_content数组 |
| `MAN` | ui-field-verification-20261023.json $.reused_manual_sample（本地人工采用文件，非PG/API） |
| `*` | 数组所有元素或对象所有value。path_checks中的missing_segments不是失败判断；空数组或不存在字段可能正是本项已声明的空态/缺口。 |

“实值”按本样例观察，“部分/混合”须逐个子项判断；详细存在性检查在审计JSON的`fields[].data.path_checks`。原文中的“线上”对应E1/E3，当前动态上下文仍以14:39为时点。

### 4.1 告警列表

对应[功能示意](ui-wireframes/01-alert-list.md)。

| ID / 字段 | 必要性与原页面依据 | 具体取数路径 | 实际观察 / 数据状态 | 限制与第一版处理 |
| --- | --- | --- | --- | --- |
| A01 告警标题 | O / 首版业务必需；U01:277；最基本事件定位；线上title实值，中文为设计译写并非已有中文字段。 | `A.title` | 实值；两例英文来源标题非空；图中中文为展示译写 | 无独立中文标题字段；默认业务主区展示；具备该项取数条件；保留原标题 |
| A02 告警来源 | O / 首版业务必需；U01:285/U04:1586；判断来自哪个系统；本例fusion_identity.source有值，旧adapter不能直接用。 | `F.identity.source` | 实值；两例v1-functional-test | 当前列表HTTP不返回fusion_identity；详情及PG可读；默认业务主区展示；后端取F.identity.source加入列表 |
| A03 发生时间 | N / 首版业务必需；U01:300原createdAt；用户明确需要业务发生时间；event_time线上有值，不能沿用createdAt。 | `A.event_time` | 实值；closed=09:09:31.862760Z；partial=09:10:17.571282Z | 不可替换为created_at；默认业务主区展示；按Asia/Shanghai显示并保留原值 |
| A04 严重程度 | O / 首版业务必需；U01:297；值班优先级；high/low有值。 | `A.severity` | 实值；closed=low；partial=high | 独立于三种置信评分；默认业务主区展示；具备该项取数条件 |
| A05 关联对象 | N / 首版业务必需；U03:444原侧栏；前移列表减少开页；affected对象有值，不能称已失陷。 | `A.affected_hosts`<br/>`A.affected_users`<br/>`A.affected_ips` | 实值；两例各1主机/1账号，IP分别1/2个 | 列表压缩与+N为展示计算；不能称受害资产；默认业务主区展示；具备该项取数条件 |
| A06 来源摘要 | N / 首版业务必需；U02:967原详情；列表增加两行有助理解；description实值，不必新增摘要模型。 | `A.description` | 实值；两例来源描述非空 | 不是AI总结，中文只是译写；默认业务主区展示；具备该项取数条件 |
| A07 AI 分诊结论 | N / 首版业务必需；U03:383原侧栏；列表前移必要；disposition有值，判断≠人工确认。 | `A.disposition`<br/>`T.verdict` | 实值；BTP与needs_review；投影和首次事件一致 | 多Run时须明确首次事件选择；不能用graph结论覆盖；默认业务主区展示；具备该项取数条件，首次理由联读T |
| A08 处理状态 | O / 首版业务必需；U01:298；反映工作状态；resolved/triaged有值。 | `A.status` | 实值；closed=resolved；partial=triaged | 不得从Run completed推导解决；默认业务主区展示；具备该项取数条件 |
| A09 调查状态/入口 | N / 首版业务必需；U05手工启动，U11旧链接非已成页；实际自动Run必须可达；需Alert→Run→GE聚合。 | `R.id`<br/>`R.case_id`<br/>`GE.completion` | 派生；closed仅分诊无GE；partial有graph结果且partial | 无latest_investigation列；正在进入调查但尚无结果需按真实调查步骤判断；默认业务主区展示；按目标及调查证据聚合，缺证据时标未知 |
| A10 告警 ID | O / 追溯或分析辅助，按需展开；U02头/路由已有；复制排障必要，默认短ID即可；线上UUID。 | `A.id` | 实值；两例canonical UUID | 不同于source_alert_id、incident_id和run_id；详情或按需展开；具备该项取数条件 |
| A11 分诊置信度 | N / 追溯或分析辅助，按需展开；U03:405原侧栏有，U01原列是Fusion；可选列保留，95/85%与Fusion分开。 | `A.ai_score`<br/>`T.confidence` | 实值；closed=.95；partial=.85 | 不是融合confidence或调查G.confidence；详情或按需展开；具备该项取数条件 |
| A12 负责人 | H / 后置或条件开放；U01:286/U02:985原有；协作需要但PG空、姓名目录未验；隐后启用合理。 | `A.assigned_to_id`<br/>`A.assigned_at` | 空态；新鲜SQL两列均null | 人员姓名目录映射未验证；生产隐藏或无值不占主要卡；默认隐藏；显示时仅未分配 |

### 4.2 告警详情

对应[功能示意](ui-wireframes/02-alert-detail.md)。

| ID / 字段 | 必要性与原页面依据 | 具体取数路径 | 实际观察 / 数据状态 | 限制与第一版处理 |
| --- | --- | --- | --- | --- |
| A13 来源系统、接入类型 | N / 追溯或分析辅助，按需展开；U02只有source，U04把connector_type当fallback；必须拆分；source有值/type空。 | `F.identity.source`<br/>`A.connector_type` | 部分/混合；source非空；connector_type两例null | source-v1是身份版本不是接入类型；详情或按需展开；来源具备该项取数条件；类型未提供 |
| A14 上游告警 ID、连接器 ID | N / 追溯或分析辅助，按需展开；U02:983 sourceRef是近似原型；本项目identity路径不同，connector空；来源追溯必要。 | `F.identity.source_alert_id`<br/>`F.identity.connector_id`<br/>`A.connector_id` | 部分/混合；上游ID非空；JSON及列connector_id均null | 不能把source_alert_id当连接器ID；详情或按需展开；分别显示；连接器未提供 |
| A15 关联来源事件 ID | N / 追溯或分析辅助，按需展开；U02 locator是来源专用近似；通用source_event_ids用于查原件；引用数组有值，external_id空。 | `A.source_event_ids`<br/>`A.external_id` | 部分/混合；source_event_ids各2项；external_id两例null | 引用数不是发生次数，也不保证对应事件正文存在；详情或按需展开；引用可复制；外部引用未提供 |
| A16 规则 ID / 规则名称 | N / 追溯或分析辅助，按需展开；U02:1073仅Wazuh locator可含规则；通用规则字段为来源追溯所需；本轮PG确认alerts和S的rule_id两例有值，rule_name均空，按实际值展示。 | `A.rule_id`<br/>`A.rule_name`<br/>`S.rule_id`<br/>`S.rule_name` | 部分/混合；新SQL直接rule_id与S一致；rule_name均null | 先前文档仅确认S规则ID；不能宣称规则名有值；详情或按需展开；显示规则ID，名称未提供 |
| A17 发生时间 | N / 首版业务必需；与A03同必要性；详情复用event_time，非新字段再生成。 | `A.event_time` | 实值；与A03同源 | 同一字段重复位置；默认业务主区展示；具备该项取数条件 |
| A18 本系统入库时间 | O / 追溯或分析辅助，按需展开；U02:986 Created；来源时间晚到/延迟排障必要；created_at实值。 | `A.created_at` | 实值；两例09:09:32.656766Z / 09:10:18.277942Z | 不是上游采集时间；详情或按需展开；具备该项取数条件 |
| A19 首次/最近见到时间 | N / 追溯或分析辅助，按需展开；选定原告警详情未独立渲染这对字段；重复/新鲜度辅助，默认展开；本例相等不能推次数。 | `A.first_seen`<br/>`A.last_seen` | 实值；两例均各自相等 | 不是first_seen_at认领时间，不说明攻击持续时长；详情或按需展开；具备该项取数条件 |
| A20 最近更新时间 | N / 追溯或分析辅助，按需展开；U04有updatedAt适配≠该告警页实际独立显示；用于当前状态新鲜度；实值但不指报告完成。 | `A.updated_at` | 实值；closed=09:09:35.590617Z；partial=09:10:21.583753Z | 告警更新时间不随每个调查工件更新；详情或按需展开；具备该项取数条件 |
| A21 解决时间 | O / 追溯或分析辅助，按需展开；U02:987；核关闭时点必要；PG关闭例有值、另一例空，现API缺列。 | `A.resolved_at`<br/>`A.status` | 部分/混合；closed非空且resolved；partial=null且triaged | 历史解决时间与当前状态冲突须保留提示；详情或按需展开；分别显示时间/未解决 |
| A22 原始摘要 | O / 首版业务必需；U02:967；保来源原文；已读description。 | `A.description` | 实值；同A06全文 | 无另一份original_summary字段；默认业务主区展示；具备该项取数条件 |
| A23 分类/标签 | O / 追溯或分析辅助，按需展开；Tags U02:990；category专列属小新增；线上为空，无值不占卡，source_snapshot标签另口径。 | `A.category`<br/>`A.tags`<br/>`S.tags` | 空态；category=null、当前tags=[]；S.tags有synthetic/v1-functional-test | 来源标签非当前标签；详情或按需展开；当前分类未提供/标签空，快照标签另标 |
| A24 主机 / 用户 / IP | O / 首版业务必需；U03:444原相关实体；定位对象必要；有值，label可空。 | `A.affected_hosts`<br/>`A.affected_users`<br/>`A.affected_ips`<br/>`A.entities`<br/>`A.iocs` | 实值；实体与IOC从PG可读取；各值类型可核 | 表返回JSON字符串需解析；多来源类型可能不同；默认业务主区展示；具备该项取数条件 |
| A25 源 IP / 目的 IP | N / 追溯或分析辅助，按需展开；原相关实体无保证方向；保S角色是必要精度；调查例源/目的IP有值，关闭例仅源IP，不能由affected_ips顺序猜。 | `S.src_ip`<br/>`S.dst_ip` | 部分/混合；两例src有值；closed.dst_ip=null；partial.dst_ip=203.0.113.82 | 只能按角色字段取，不能按IP数组排序猜；详情或按需展开；缺目的IP显示未提供 |
| A26 进程名 / 命令行 | N / 追溯或分析辅助，按需展开；U02 Raw泛载荷，非统一专栏；对当前进程告警必要，但仅有值按来源显示。 | `A.raw_event.process_name`<br/>`A.raw_event.command_line` | 实值；uname与powershell.exe及完整命令均非空 | 来源扩展合同，其他来源不保证；详情或按需展开；有值显示，无值未提供 |
| A27 目的端口、域名、URL、文件哈希 | N / 追溯或分析辅助，按需展开；U02 IOC/Raw近似；条件性技术核对；本例仅443，余为空，非全来源承诺。 | `A.raw_event.destination_port`<br/>`S.domain`<br/>`S.url`<br/>`S.file_hash` | 部分/混合；partial端口443；closed端口键不存在；两例domain/url/file_hash均null | 组合字段须逐子项读取；有端口不等于域名、URL、哈希也有值；详情或按需展开；必须拆明：端口1例实值，其余仅空态 |
| A28 MITRE 战术/技术 | O / 追溯或分析辅助，按需展开；U01:278/U02:1004；提供检测分类线索；T1059.001/execution有值，非阶段链。 | `A.mitre_tactics`<br/>`A.mitre_techniques` | 部分/混合；closed=[]；partial=execution/T1059.001 | 无MITRE名称实值；映射不等于攻击证实；详情或按需展开；实值和空态均具备该项取数条件 |
| A29 来源完整载荷 | O / 追溯或分析辅助，按需展开；U02:1071；核原信息必要；raw_event有值但名称须解释不是完整Kafka/所有原日志。 | `A.raw_event`<br/>`S.raw_event` | 实值；两例对象非空、与快照一致 | 完整仅指已保存raw_event，不指上游所有事件或整个Kafka信封；详情或按需展开；标签标来源载荷，勿宣称完整外部取证 |
| A30 融合分组 / 人工 Case | N / 追溯或分析辅助，按需展开；原Create/Case存在，但Fusion Incident并非同物；两个ID分列必要；Incident有值/Case空。 | `F.incident_id`<br/>`A.case_id` | 部分/混合；两例Fusion UUID非空、Case=null | 不能把Run.case_id当Case；详情或按需展开；展示分组+未关联Case |
| A31 融合说明 | O / 追溯或分析辅助，按需展开；U03:429；解释系统为何关注，可折叠；narrative实值，含建议不等于执行。 | `A.narrative` | 实值；两例PG非空 | 包含建议文字，非行动回执；详情或按需展开；具备该项取数条件并标系统融合说明 |
| A32 融合评分及因子 | O / 追溯或分析辅助，按需展开；U02:971/U03；原解释面板可复用；65/7及因子实值，不混95/85%。 | `A.confidence`<br/>`A.confidence_label`<br/>`A.confidence_rationale.*.factor`<br/>`A.confidence_rationale.*.value`<br/>`A.confidence_rationale.*.weight`<br/>`A.confidence_rationale.*.contribution` | 实值；closed=7/low；partial=65/medium；各7因子 | 不是恶意概率；原始融合小数与投影100分不能混用；详情或按需展开；按投影100分显示 |
| A33 AI 首次分诊 | O / 首版业务必需；U03:383；业务判断入口，精确时间/结构T为改进；两个样例实值。 | `T.verdict`<br/>`T.confidence`<br/>`TE.ts` | 实值；两例BTP/.95、needs_review/.85及事件时间 | 首次按明确Run/triage事件取；默认业务主区展示；具备该项取数条件 |
| A34 AI 分诊理由 | O / 首版业务必需；U03:415原aiSummary；T.rationale更明确；保原文不能提升为事实。 | `T.rationale` | 实值；两例非空 | ai_summary为拼接文本，理由优先T；默认业务主区展示；具备该项取数条件 |
| A35 分诊是否自动关闭 | N / 首版业务必需；原status不解释自动原因；本次true/false实际记录足以解释差异；需T+当前状态一致性。 | `T.auto_closed`<br/>`A.status`<br/>`A.resolved_at` | 实值；true/resolved/有时间，false/triaged/null | 后续人工状态可与历史自动关闭不同；默认业务主区展示；联合展示历史事实和当前状态 |
| A36 分诊发现/建议 | O / 追溯或分析辅助，按需展开；U03:579/U07建议原型；发现和动作必须分开；有发现/建议空，不能补已执行。 | `T.findings`<br/>`T.proposed_actions`<br/>`A.ai_recommendations` | 部分/混合；findings非空；两处建议数组均空 | 不能把findings里的建议文字认作结构动作；详情或按需展开；发现可展开，建议未生成 |
| A37 IOC 检索状态 | N / 追溯或分析辅助，按需展开；U02有IOC badge，缺scope/external coverage成组；必要避免未命中当安全；no_match/未配置已读。 | `F.ioc_lookup.indicators`<br/>`F.ioc_lookup.status`<br/>`F.ioc_lookup.scope`<br/>`F.ioc_lookup.matches`<br/>`F.ioc_lookup.checked_at`<br/>`F.ioc_lookup.external_status` | 部分/混合；指标1/2项，no_match，租户PG范围，matches=[]，有时间，外部not_configured | 未查外部不能判安全；来源scope为文字无统一source_code；详情或按需展开；现有状态/范围具备该项取数条件 |
| A38 资产/身份/漏洞/历史告警补充资料 | N / 追溯或分析辅助，按需展开；原所审告警页无该4维卡；有资料时提高判断质量，缺资料时提示边界；目前只证明空态，丰富字段不可承诺。 | `P.dimensions.*.status`<br/>`P.dimensions.*.source`<br/>`P.dimensions.*.rows`<br/>`P.dimensions.*.truncated` | 空态；资产/身份/历史no_match；漏洞not_requested/no_matched_asset；rows=[] | 这是14:39动态查询回执，不是本次Run当时材料；无非空资料例；详情或按需展开；仅上线覆盖空态，丰富资料待非空例验 |
| A39 上下文查询范围与新鲜度 | N / 追溯或分析辅助，按需展开；原page未见此结构；否则空查询很易误读；P.query/queried_at已读，非调查当时材料。 | `P.query.hosts`<br/>`P.query.accounts`<br/>`P.query.ips`<br/>`P.query.history_before`<br/>`P.query.history_days`<br/>`P.query.limit_per_dimension`<br/>`P.queried_at` | 实值；告警前7天、20条每维、查询时点14:39 | 没有统一持久结果表；动态回执与历史Run分开；详情或按需展开；可显示明确时点和范围 |
| A40 外部历史 / UEBA | N / 追溯或分析辅助，按需展开；覆盖缺口而不是再建UEBA页面；本次not_configured，可显示一条覆盖摘要。 | `P.external_event_history.status`<br/>`P.ueba.status` | 空态；两项not_configured | 只证明此接口路径未配置，不代表全平台无UEBA或无历史数据；详情或按需展开；显示此查询未配置 |

### 4.3 调查列表

对应[功能示意](ui-wireframes/03-investigation-list.md)。

| ID / 字段 | 必要性与原页面依据 | 具体取数路径 | 实际观察 / 数据状态 | 限制与第一版处理 |
| --- | --- | --- | --- | --- |
| I01 调查标题 | N / 首版业务必需；U08 picker只有时间/状态/model；独立Run列表需可读标题；从已确认Alert/Case组合，非r.title。 | `A.title`<br/>`R.id` | 派生；partial目标标题可组合“·调查” | 无Run.title；已确认目标才可取标题；默认业务主区展示；确定性组合或短Run ID |
| I02 Run ID / 关联目标 | N / 首版业务必需；U08 Run ID原有，U11独立路由未成；无Case场景需目标类型映射；自动样例case_id是Alert字符串。 | `R.id`<br/>`R.case_id`<br/>`T.recovery.alert_id`<br/>`A.case_id` | 部分/混合；Run.case_id=Alert.id且recovery匹配；Case=null | 无通用target_type，其他入口不得猜测；图展示目标类型为已知入口事实；默认业务主区展示；具备该项取数条件自动路径，其他目标需确认 |
| I03 触发方式 | N / 追溯或分析辅助，按需展开；原手工入口隐含来源，通用Run没有trigger_type；仅已核自动可标自动升级，其他未知。 | `TE.agent`<br/>`T.recovery.workflow_version`<br/>`T.recovery.alert_id`<br/>`T.recovery.shadow` | 派生；auto-triage-v1、Alert已确认；partial实际进入graph | triage_started本身仅认领不证明已模型调用或已升级；详情或按需展开；按已知入口+graph证据显示自动升级 |
| I04 关联告警等级/来源 | N / 首版业务必需；原Case头并非Run告警来源；工作排序必要；当前Alert可聚合，快照与当前区分。 | `A.severity`<br/>`F.identity.source` | 实值；partial high/v1-functional-test | 这是当前Alert属性，不是全Case最高等级；默认业务主区展示；具备该项取数条件 |
| I05 执行状态 | O / 首版业务必需；U08:483/U07；completed有值，原语义需限于执行结束。 | `R.status`<br/>`R.error` | 实值；两例completed、error=null | G.status仍running，不能覆盖持久Run状态；默认业务主区展示；从R显示执行结束 |
| I06 调查完成度 | N / 首版业务必需；U07原completed直接宣告完成；真实partial强制新增；GE.completion有值。 | `GE.completion` | 实值；partial=partial；closed无GE | G无completion键；人工无字段显示未知；默认业务主区展示；按GE显示，勿读取错误路径 |
| I07 分析结论 | N / 首版业务必需；U07角色卡近似，无自动G统一结论页；G.verdict有值，不以首次分诊替代。 | `G.verdict` | 实值；partial=needs_review | closed无调查结论；不沿用首次分诊冒充；默认业务主区展示；具备该项取数条件调查例 |
| I08 开始/结束时间 | O / 首版业务必需；U08:512；Run时间可直接读，保时区。 | `R.started_at`<br/>`R.completed_at` | 实值；partial两值完整；本地夹具started_at为null | 不可改取G.started_at/ completed_at，后者无时区/null；默认业务主区展示；用Run列，缺值显示未记录 |
| I09 运行耗时 | O / 追溯或分析辅助，按需展开；U08:512计算；约21.86秒包含分诊，非纯模型耗时。 | `R.started_at`<br/>`R.completed_at` | 派生；partial=21.858900秒；closed=2.664353秒 | 包含首次分诊，不能称纯调查耗时；详情或按需展开；计算时间差，缺起点不计算 |
| I10 报告可用性 | O / 首版业务必需；U07:1243/U10空态；重要交付入口；必须正文可得，不能只目录存在。 | `K.*.kind`<br/>`REPORT` | 派生；partial report_md正文6413字节可读；closed无报告 | 目录存在不等于内容可读；blob_ref需另实现读取；默认业务主区展示；固定Run+工件实读后显示可查看 |
| I11 负责人/复核状态 | H / 后置或条件开放；原Case assignee不是Run独立复核；统一字段缺失，生产隐藏合理，不新增假姓名/已复核。 |  | 缺合同；无统一Run责任人与复核字段 | 不能用Alert负责人、Case负责人或needs_review伪造复核状态；生产隐藏或无值不占主要卡；V1隐藏 |

### 4.4 调查概览

对应[功能示意](ui-wireframes/04-investigation-overview.md)。

| ID / 字段 | 必要性与原页面依据 | 具体取数路径 | 实际观察 / 数据状态 | 限制与第一版处理 |
| --- | --- | --- | --- | --- |
| I12 调查目标与原告警快照 | N / 首版业务必需；原U08可看payload，无统一目标卡；保当次材料必要；G.raw_alert无status，已与S区分。 | `G.raw_alert` | 实值；partial有来源标题/描述/对象/raw_event | G.raw_alert不含status；S.status=new是首次交付快照；默认业务主区展示；具备该项取数条件并标当次收到的材料 |
| I13 调查对象范围 | N / 首版业务必需；原Recon/graph近似，必须明确仅该Alert；快照对象可取，未证明所有受害资产。 | `G.raw_alert.hostname`<br/>`G.raw_alert.username`<br/>`G.raw_alert.src_ip`<br/>`G.raw_alert.dst_ip`<br/>`G.raw_alert.attack_context_preparation.source_alert_ids` | 部分/混合；单Alert，1主机/账号及2IP；projection成员1项 | 未有任意Case多告警完整范围样例；不是完整事件所有对象；默认业务主区展示；当前单Alert范围具备该项取数条件 |
| I14 查询范围 | N / 追溯或分析辅助，按需展开；U08泛payload可读，专门可读参数为增强；线上args及当次graph query_scope可取，统一绝对窗口缺失。 | `TOOLS.*.payload.args`<br/>`G.context_bundle.attack_context.query_scope`<br/>`CHAIN.attack_chain.query` | 部分/混合；实际工具args、图投影上限50、链窗口24h | 工具hours=24与days=24不同；缺统一绝对起止，不能统一成一天；详情或按需展开；逐次如实显示参数与缺口 |
| I15 调查结论与置信度 | N / 首版业务必需；U07 Forensic confidence是不同路径；自动G19%有值，新映射必要，不能当恶意概率。 | `G.verdict`<br/>`G.confidence`<br/>`G.confidence_basis` | 实值；needs_review/.19及5项依据 | 依据含旧质量问题，仅分析记录非已核事实；默认业务主区展示；具备该项取数条件并保留待核措辞 |
| I16 调查摘要 | N / 首版业务必需；U07 summary卡可作原型；当前无final_summary，只采用确定性状态摘要，禁止以最后ToolMessage填。 | `R.status`<br/>`GE.completion`<br/>`G.verdict` | 派生；可组运行结束/部分完成/待复核 | 无final_summary；depth.narrative是工具JSON；默认业务主区展示；仅确定性状态摘要 |
| I17 现有分析记录 | N / 追溯或分析辅助，按需展开；U07角色摘要/U08payload近似；G.findings实值含冲突，按分析记录而非已证实事实呈现。 | `G.findings` | 实值；22项含判断、工具文本、401错误和旧冲突语句 | 不能统一称已确认发现；详情或按需展开；可展开保留原文 |
| I18 完成度与停止原因 | N / 首版业务必需；原只有failed/error；真实预算partial需要解释；GE+G预算字段可读，error空不可吞停止信息。 | `GE.completion`<br/>`G.budget_exhausted`<br/>`G.budget_exhausted_reason` | 实值；partial/true/token budget exhausted (27697 of 20000) | 新版depth.stop_reason在本地；旧生产字段缺不能强读；默认业务主区展示；旧版按预算原因；新版另适配 |
| I19 缺失数据与覆盖限制 | N / 首版业务必需；原空图提示不等于本次实际覆盖；depth缺源/coverage/truncated实值；简短摘要主显示，全文展开。 | `G.investigation_depth.unavailable_data`<br/>`G.investigation_depth.coverage_notes`<br/>`G.investigation_depth.truncated` | 实值；process_tree、network_connections，2条外部覆盖限制，truncated=true | truncated是调查被截断，不等于所有工件正文被截断；当前P非当时证据；默认业务主区展示；现有缺口具备该项取数条件 |
| I20 后续建议 | O / 追溯或分析辅助，按需展开；U07:1318原有建议卡；本例G建议空，只显示未生成，不从正文私自提取动作。 | `G.proposed_actions` | 空态；partial=[] | 本地人工responder有verify-only建议但仅文件/内存；详情或按需展开；生产显示未生成结构化建议 |
| I21 实际执行动作 | H / 后置或条件开放；原Responder建议不是执行收据；本例[]，当前只需紧凑“无执行记录”，不开放厂商按钮。 | `G.executed_actions` | 空态；partial=[] | 未验证非空动作及回执，不把dry_run或建议当执行；生产隐藏或无值不占主要卡；显示无执行记录 |
| I22 根因与影响结论 | X / 不宜承诺；U07:1291仅hypothesis；当前无统一已验证合同，不能做确认根因/受害数量卡；假设仍可在报告读。 | `MAN.forensic.root_cause_hypothesis`<br/>`MAN.forensic.blast_radius` | 缺合同；生产无统一确认根因/影响字段；本地仅未经证实IP假设、影响空 | graph blast_radius是可达性；本地Forensic假设非持久事实；生产隐藏或无值不占主要卡；V1不提供确认根因/影响卡 |

### 4.5 证据与关联

对应[功能示意](ui-wireframes/05-investigation-evidence.md)。

| ID / 字段 | 必要性与原页面依据 | 具体取数路径 | 实际观察 / 数据状态 | 限制与第一版处理 |
| --- | --- | --- | --- | --- |
| I23 材料目录：类型、ID、时间、字节、hash、关联事件 | O / 追溯或分析辅助，按需展开；U08:914工件原型；集中目录为增强；14份有值，hash/bytes放展开，不是安全证据计数。 | `K.*.id`<br/>`K.*.kind`<br/>`K.*.created_at`<br/>`K.*.size_bytes`<br/>`K.*.sha256`<br/>`K.*.event_id` | 实值；两例7/14份；21份ID/时间/大小/hash/event关联可读 | 工件数不是证据支持结论数；详情或按需展开；具备该项取数条件 |
| I24 工件正文 | O / 追溯或分析辅助，按需展开；U08:938；交接基本必要；本批21正文已校验，不外推全部Run/所有工具完整。 | `BODIES` | 实值；21份原始HTTP正文可读，UTF-8与hash可独立核验 | public graph_result是挑选字段投影，不能拿它重算原工件hash；留存正文不等于所有外部原文；详情或按需展开；按artifact_id读原content |
| I25 已查询工具、请求参数、返回预览 | O / 追溯或分析辅助，按需展开；U08:729泛payload；可解释查过什么；10记录约200预览有值，不夸为全返回。 | `TOOLS.*.payload.tool`<br/>`TOOLS.*.payload.args`<br/>`TOOLS.*.payload.result_preview` | 实值；10工具记录均有三项；预览200字符上限 | 非全部返回；没有ToolMessage消费证明的调用不推测模型采用；详情或按需展开；具备该项取数条件旧版三项 |
| I26 单次工具状态与保留内容 | H / 后置或条件开放；原无本地新kind专卡；本地read-1可取但生产无该类型，不作为上线现成功能。 | `LT.*.tool`<br/>`LT.*.args`<br/>`LT.*.call_id`<br/>`LT.*.iteration`<br/>`LT.*.status`<br/>`LT.*.available`<br/>`LT.*.result_text`<br/>`LT.*.result_truncated` | 仅本地；两个本地PG夹具均read/read-1/success/true/未截断，94字节 | 真实SQL+冷读，替身模型/工具，非HTTP/生产；本批两例未覆盖工具empty/error/unavailable；生产隐藏或无值不占主要卡；生产隐藏；开发版按已测范围 |
| I27 单次工具留存定位 | H / 后置或条件开放；原有artifact定位但新tool_trace字段属本地；本地recorded实值，缺口如实提示；旧Run不推造。 | `LG.investigation_depth.tool_trace.*.ledger_event_id`<br/>`LG.investigation_depth.tool_trace.*.ledger_artifact_id`<br/>`LG.investigation_depth.tool_trace.*.ledger_status`<br/>`LG.investigation_depth.ledger_gaps` | 仅本地；两例recorded、ID能关联实际本地表；ledger_gaps=[] | tool_result自身不保存ledger_status/ID，定位从trace或工件元数据取；无gap非空例；诊断折叠区；生产隐藏，开发按实际引用 |
| I28 IOC 及情报覆盖 | N / 追溯或分析辅助，按需展开；原Recon/IOC badge近似；显式来源/引擎覆盖避免0分误导；本例engines0/sources空。 | `G.ioc_enrichments.*.ioc_type`<br/>`G.ioc_enrichments.*.value`<br/>`G.ioc_enrichments.*.sources`<br/>`G.ioc_enrichments.*.total_engines`<br/>`G.ioc_enrichments.*.risk_score` | 部分/混合；两IP/类型有效；sources=null、engines=0、risk_score=0 | 缺外部判定；零分不能显示安全；详情或按需展开；展示覆盖缺口，原始数值折叠 |
| I29 知识、身份、组织记忆等读取状态 | N / 追溯或分析辅助，按需展开；原只有泛工件；五类读取回执有助解释资料覆盖；本例均no_match，四类采用数为0而技能源未提供统一采用数，不表示查遍全库。 | `READS.*.status`<br/>`READS.*.source`<br/>`READS.*.read_at`<br/>`READS.*.received_count`<br/>`READS.*.adopted_count` | 部分/混合；五类均no_match/有source/read_at/received_count=0；tenant_skill_read无adopted_count，其余4类为0 | 不能统一五种schema；skills用selection.status/skills/valid_count等，valid_count不自动等于采用数；详情或按需展开；必须按kind解释采用信息 |
| I30 已采用知识引用 | H / 后置或条件开放；原无统一引用支持卡；本例citations空，按有值展示即可，不能承诺已有引用链。 | `KB.adopted_count`<br/>`KB.citations`<br/>`KB.cited_sources`<br/>`KB.model_citations` | 空态；0/[]/[]/[] | 无非空引用标题/来源定位样例；生产隐藏或无值不占主要卡；显示未采用知识引用，非空展示另验 |
| I31 告警关系图 | N / 追溯或分析辅助，按需展开；U09原Case当前图；自动Run历史Alert图为新适配，有助定位对象；5邻居可读，不是因果链。 | `GRAPH.alert_graph.data.neighbors.source`<br/>`GRAPH.alert_graph.data.neighbors.neighbors.*.id`<br/>`GRAPH.alert_graph.data.neighbors.neighbors.*.rel_type` | 实值；1起点5邻居：Host/User/IOC×2/Technique，5条关系类型 | 邻居包含关系类型但非完整方向端点边表；Case路径不是该图；详情或按需展开；可显示以Alert为中心的关联 |
| I32 关联可达范围 | N / 追溯或分析辅助，按需展开；U09图原型；可达范围辅助而非处置名单；6混合节点包含起点，避免受害数。 | `GRAPH.alert_graph.data.blast_radius.affected_nodes`<br/>`GRAPH.alert_graph.data.blast_radius.hops`<br/>`GRAPH.alert_graph.data.blast_radius.total_affected`<br/>`GRAPH.alert_graph.data.blast_radius.type_breakdown` | 实值；3跳6节点含起点，5类，Host仅1 | 非6受害主机；未列可达路径的逐边因果；详情或按需展开；具备该项取数条件关联可达性 |
| I33 候选告警链 | O / 追溯或分析辅助，按需展开；U09:1663窗口/空态已有；当前Run快照适配，链空但entity_graph不必空。 | `CHAIN.attack_chain.status`<br/>`CHAIN.attack_chain.data.chain`<br/>`CHAIN.attack_chain.data.window`<br/>`CHAIN.attack_chain.query.anchor` | 空态；empty/[]/24h/seed_event_time_plus_minus_window | 非空entity_graph不等于非空chain；详情或按需展开；显示限定范围未找到 |
| I34 Case 路径 | O / 追溯或分析辅助，按需展开；U09:1388已有；本例无Case只需紧凑not_linked，不单开必看页面。 | `PATH.attack_path.status`<br/>`PATH.attack_path.error`<br/>`PATH.attack_path.data`<br/>`A.case_id` | 空态；not_linked/no_linked_case/null/Case=null | 本次无Case，非空路径未验证；详情或按需展开；显示未关联，无可点Case路径 |
| I35 图的范围与时点 | N / 追溯或分析辅助，按需展开；原实时图window有、Run快照时点无；防止把后来图当旧证据，queried_at/query_scope可取。 | `GRAPH.queried_at`<br/>`G.context_bundle.attack_context.query_scope`<br/>`CHAIN.attack_chain.data.generated_at` | 实值；当次09:10:21.916108Z，种子与上限50，truncated=false | 14:39当前图应另标；不混入10-22当次快照；详情或按需展开；具备该项取数条件固定Run图快照 |
| I36 证据—结论对应关系 | X / 不宜承诺；U08 event→artifact不是结论→证据；统一引用合同缺失，禁止画确定支持关系。 |  | 缺合同；没有统一逐结论evidence_ids/支持关系 | artifact.event_id仅步骤关联；生产隐藏或无值不占主要卡；V1不画支持连线 |

### 4.6 调查过程

对应[功能示意](ui-wireframes/06-investigation-process.md)。

| ID / 字段 | 必要性与原页面依据 | 具体取数路径 | 实际观察 / 数据状态 | 限制与第一版处理 |
| --- | --- | --- | --- | --- |
| I37 处理步骤 | O / 追溯或分析辅助，按需展开；U08:678；18真实记录可读；按ts+id去重，非按seq假定严格写入时序。 | `E.*.id`<br/>`E.*.ts`<br/>`E.*.kind`<br/>`E.*.agent`<br/>`E.*.summary`<br/>`E.*.seq` | 实值；partial18事件，含-1与10000+ | seq不是时间游标；工具ts是留存时刻不是独立执行起止；详情或按需展开；按ts/ID去重排序，终态全量核对 |
| I38 graph 节点 | O / 追溯或分析辅助，按需展开；U08通用kind/payload支持；当前3节点名可取，完整每节点输入输出不具备。 | `NODES.*.payload.node`<br/>`NODES.*.duration_ms` | 实值；triage/enrichment/investigation，3/12/18292ms | 只有node与节点耗时，无各节点完整输入输出；详情或按需展开；具备该项取数条件简要节点记录 |
| I39 模型调用 | O / 诊断辅助，默认折叠；U08模型/explain/成本；实际调用目的/时间有值，可归因调试；不在结论主卡铺prompt。 | `LLM.*.payload.agent`<br/>`LLM.*.payload.model`<br/>`LLM.*.payload.purpose`<br/>`LLM.*.duration_ms`<br/>`X.*.agent`<br/>`X.*.model`<br/>`X.*.purpose`<br/>`X.*.duration_ms`<br/>`C.*.resolved_model` | 部分/混合；1分诊llm_call+6graph交换，目的/时长有值；实际模型在按模型费用行 | 不是7条llm_call事件；resolved_model非逐交换字段，模型切换不能盲目映射；诊断折叠区；列明两种读取来源及聚合模型边界 |
| I40 输入/输出留存范围 | O / 诊断辅助，默认折叠；U08:799 hash及正文；完整性提示必要，原全留存宣传不可用；prompt有截断，不能说可完整重放。 | `LLM.*.payload.prompt_truncated`<br/>`LLM.*.payload.response_truncated`<br/>`X.*.prompt_truncated`<br/>`X.*.response_truncated`<br/>`X.*.input_hash`<br/>`X.*.output_hash` | 部分/混合；分诊输入截断；graph前2输入未截断、后4截断；所有输出未截断 | 输入hash可能针对截断前内容；工件hash只证明所存文本一致，不能恢复截断原文；诊断折叠区；保留原始交换内容与截断说明 |
| I41 工具处理耗时/状态 | H / 后置或条件开放；U08:709只显示duration>0；旧工具无独立状态且duration0默认，生产不显示精确耗时；本地新状态另列。 | `TOOLS.*.duration_ms`<br/>`TOOLS.*.payload.status`<br/>`LT.*.duration_ms`<br/>`LT.*.status` | 部分/混合；旧生产10条duration_ms=0、status键缺；本地read=0ms/success | 旧写入未传duration_ms而用默认0；本地0为测量舍入，语义不同；诊断折叠区；主文档明确旧版未提供，不显示0ms成功 |
| I42 运行失败/部分完成提示 | N / 首版业务必需；U07failed原有，但partial与Run error合并解释是必要新增；已实读partial+error null。 | `R.error`<br/>`GE.completion`<br/>`G.budget_exhausted_reason`<br/>`LG.investigation_depth.stop_reason`<br/>`LG.investigation_depth.error` | 部分/混合；生产error=null但partial/预算原因有效；本地超时/ValueError原因有效 | 本地两Run仍completed；页面读取失败与运行错误区分；默认业务主区展示；状态组合展示，勿仅判断R.error |

### 4.7 报告与运行信息

对应[功能示意](ui-wireframes/07-investigation-report.md)。

| ID / 字段 | 必要性与原页面依据 | 具体取数路径 | 实际观察 / 数据状态 | 限制与第一版处理 |
| --- | --- | --- | --- | --- |
| I43 Markdown 报告预览/下载 | O / 首版业务必需；U10已有原文/下载，预览双模式属于体验新增；6413字节可读；无Case入口为必要适配。 | `REPORT` | 实值；partial6413字节正文可读；closed无report_md | 旧正文Status=running及内容缺陷保留；没有通用report.md路径；默认业务主区展示；按通用工件读取并外置partial提示 |
| I44 报告元信息 | N / 追溯或分析辅助，按需展开；U08泛工件有hash/bytes，U10报告头没有完整版本卡；追溯artifact必要，hash折叠。 | `REPORT_META.id`<br/>`REPORT_META.created_at`<br/>`REPORT_META.size_bytes`<br/>`REPORT_META.sha256` | 实值；72e0c864…、09:10:40.265643Z、6413字节、SHA256匹配 | 记录时间不是每句话发生时间，须固定版本工件ID；详情或按需展开；具备该项取数条件 |
| I45 Case 报告入口 | O / 追溯或分析辅助，按需展开；U10已有；本例Case空则隐藏点击，但Run MD仍可读。 | `A.case_id`<br/>`PATH.case_id` | 空态；两例均null；生产租户Case=0 | Case报告源代码存在但本批未实读非空Case链路；详情或按需展开；当前隐藏Case入口；Run报告可用 |
| I46 总 Token / 模型调用数 | O / 诊断辅助，默认折叠；U08:527/569；诊断和费用透明有用，非风险指标；29755/7有值。 | `R.total_tokens`<br/>`C.*.call_count` | 派生；partial29755/7；closed2033/1 | 调用数SUM按模型行聚合；不是r.iterations或事件条数；诊断折叠区；先按Run聚合费用，避免乘积 |
| I47 首次分诊与后续调查用量 | N / 诊断辅助，默认折叠；U08按模型表是原型，按阶段区分需要新映射；2058+27697，本例两个角色明确，不能泛化任意共享模型。 | `T.recovery.cost.tokens`<br/>`C.*.total_prompt_tokens`<br/>`C.*.total_completion_tokens`<br/>`C.*.call_count`<br/>`USAGE.usage` | 派生；partial首2058/1、graph27697/6，和为29755/7 | 按模型别名拆分仅对已确认入口成立；同模型多阶段通用场景需graph_usage/首次回执核对；诊断折叠区；显示此例精确分段及来源 |
| I48 费用及未计价情况 | O / 诊断辅助，默认折叠；U08:644已区分测量/估算；7unpriced，显示未计价，金额0不等于免费。 | `R.measured_call_count`<br/>`R.estimated_call_count`<br/>`R.unpriced_call_count`<br/>`C.*.measured_call_count`<br/>`C.*.estimated_call_count`<br/>`C.*.unpriced_call_count` | 部分/混合；partial=0实测/0估算/7未计价，closed=1未计价 | 计数可取但有效价格无；不能显示免费；诊断折叠区；V1费用未计价 |
| I49 模型名称 | O / 诊断辅助，默认折叠；U08:606含resolved_model；别名与解析名分开，Run.model_used为工作流名不能冒充真实模型。 | `C.*.model`<br/>`C.*.resolved_model` | 实值；aisoc-triage/aisoc-investigation均解析同一openai/aisoc-test-investigation | r.model_used=kafka:auto_triage:llm是流程标识；诊断折叠区；按费用模型行显示别名和解析名 |
| I50 轮数与查询数 | N / 诊断辅助，默认折叠；U08原Run.iterations不可代替Deep轮数；depth6/7/10已有记录，查询类别不等于证据有效性。 | `G.investigation_depth.iterations`<br/>`G.investigation_depth.distinct_pivots`<br/>`G.investigation_depth.ledger_rows` | 实值；6轮/7类别/10条留存工具记录，实际工具事件10 | 旧distinct_pivots不是成功证据计数；r.iterations=3不替代Deep轮数；诊断折叠区；分别命名、解释计数含义 |


## 5. 从用户任务反查：三个完整例子

### 5.1 值班人员查看已自动解决告警

Alert `bc625c39-56af-5403-a378-9bfb99c610d2`，Run `4f5a0a57-050a-57a4-8443-504550fbc5fd`。来源 `v1-functional-test`，低危，来源描述为获授权盘点命令；发生时间 `2026-10-22 17:09:31.862760+08:00`，入库时间 `17:09:32.656766+08:00`。

| 用户需要判断 | 实际读取 | 页面应呈现 |
| --- | --- | --- |
| 是谁报的、发现什么 | `alerts.title/description`、F.identity.source、raw_event的uname命令 | 来源事实与AI理由分别展示；“来源声称获授权”不扩大成已独立核查全部变更系统 |
| 分诊后怎样处理 | `triage_verdict`为BTP/0.95、auto_closed=true；当前Alert resolved且resolved_at有值 | 良性真阳性、已自动解决，非“误报” |
| 是否完成调查 | 3事件/7工件；只有分诊，未进入后续调查，无report_md | 告警处理记录中可看该Run；调查列“未启动”，不能显示“调查完成” |
| 花费多少 | 2033 tokens、1次调用、unpriced=1 | 显示Token/调用数；费用未计价 |

此例主要验证告警列表/详情和“没有调查”的分支；不能用它证明调查所有卡片可用。

### 5.2 分析员接手部分完成的自动调查

Alert `e5f593f0-b328-59c3-8238-379db33d8bfe`，Run `bdccd907-7f36-558f-8ed4-4be2e417b101`。本轮复核18事件/14工件，仍无Case。

| 用户需要判断 | 实际读取 | 页面应呈现 |
| --- | --- | --- |
| 查的是谁 | 主机/账号`v1-functional-host-2/user-2`，`192.0.2.82 → 203.0.113.82:443`，powershell命令，T1059.001 | 关联对象、来源技术映射；不称全部为受害资产或已确认攻击 |
| 当前状态如何 | Alert triaged；首次分诊NR/0.85；Run completed；graph_result事件completion partial；工件verdict needs_review/confidence0.19 | 业务状态、执行状态、完成度、当次结论分别显示；不以85%覆盖调查19% |
| 是否可接手 | G.investigation_depth含缺失process_tree/network_connections、覆盖限制；六轮停止及budget_exhausted | 突出部分完成/缺源/停止原因，已有材料可继续读 |
| 真正查过什么 | 10条tool_call，7类查询；旧版约200字符preview，部分参数为`days=24`或以主机/账号作process_name | 显示实际参数，不能写成已正确查询24小时或查清该进程；查询有效性另列待改 |
| 图能说明什么 | 5个直接邻居；3跳范围含起点6节点、5种类型；chain empty、Case path not_linked | 关系图和范围可展示；不是6受害主机、不是完整攻击因果链 |
| 能否读报告 | report_md工件`72e0c864-41a0-4096-bfa2-8aa0ebe3a641`，6413 UTF-8字节，SHA256校验一致 | 预览/下载真实Markdown，并在页面外层提示这是部分结果 |
| 报告与状态是否一致 | 报告/旧G快照仍含running，当前Run已结束且completion partial | 保留原报告，显式提示历史快照与当前执行状态不同；不静默改写原文 |
| 用量是否准确 | 分诊2058 + 调查27697 = 29755 tokens；1+6=7次模型；全部未计价 | 6轮、7类、10记录不混称；图分支27697超过20000软预算，不宣称预算控制质量通过 |

**数据读取通过，分析质量未通过全面验收。** 本例输入为合成告警，源端资料有限；测试标记影响理由、查询参数含义、预算越界和报告状态陈旧均保持原问题记录。不能把展示丰富程度当作检测/调查有效性的证明。

### 5.3 本地开发版调查中止后保留材料

复用[字段验证JSON](ui-field-verification-20261023.json)的两个local_samples：真实PG与本地runner/ledger执行，模型/工具为替身，分别模拟外层超时与模型报错。两个Run先完成一次`read`工具，再停止，冷读仍有tool_result与report_md、completion partial。

`call_id=read-1`、iteration1、status success、available true、result_truncated false、result_size_bytes94、留存状态recorded。页面可示意“完成一次查询，随后停止，已有材料可查看”。这验证I26/I27的本地合同，不将其放入上述生产14份材料中；真实模型采用样例和隔离PG样例也不得混为同一次验证。

本地result_text有约4000字符上限，result_size_bytes/result_sha256描述原始序列化结果；截断时即使hash存在也不能恢复未留存原文。上线条件是选定版本部署、真实读取新工件和页面处理截断状态，**本次不执行这些操作**。

## 6. HTTP逐项对照与已确认的接入缺口

[取数附件第2章](page-data-mapping.md#http)保留完整路径、参数和操作语义；这里专门记录审计结论。

| 能力 | 本轮或复用验证 | 对页面交付的影响 |
| --- | --- | --- |
| 告警列表/页码 | 本轮GET200、total3、items3；默认25/最大200沿源码 | 可接基本列表；总量统计仍须同筛选范围 |
| 关键词搜索 | 本轮无匹配字符串`UI_AUDIT_NO_MATCH_20261023_XYZ`仍total3 | **已确认无效**，不得开放“可用搜索”；按PG自行查询或修API后验收 |
| 来源字段/来源、时间、对象过滤 | 列表返回键不含source/fusion_identity；现有参数未覆盖这些条件 | 后端从PG补字段/查询，不能让浏览器逐条补详情当作完成统一列表合同 |
| 告警详情 | 两例本轮200，含fusion_identity、raw_event等 | source可从详情读；rule/connector/owner等不保证都在详情返回，PG路径见逐项表 |
| 当前上下文、图 | 14:39查询200；本轮复核历史图工件hash | 标清历史快照与当前查询，不能用旧快照称16:42实时覆盖 |
| 通用Run列表 | 本轮200返回3Run，含仅分诊Run；仅最近N条、无总量游标 | 后端增加实际调查识别与分页/统计；不能把返回数组长度当所有调查总量 |
| Run详情/事件/工件 | 本轮两Run详情、调查例18事件/14目录均200；PG共21工件校验通过 | 分层读取，完成度取事件，报告正文取具体工件；旧事件seq限制仍在 |
| 无Case Markdown | 本轮指定report_md详情200，6413字节、hash一致 | 用工件读取链；不存在通用Run `/report.md`合同 |
| 人工Case报告 | 当前租户0Case；旧入口源码/既有历史证据 | 条件能力，本轮不宣称生产Case分支新验收通过 |
| Claim/Snooze/PATCH/Close/Case investigate等操作 | 本轮均未调用 | 原版有价值，但需选定范围后的权限/状态/回执验收；不直接UPDATE表代替启动调查 |

PG直查是用户认可的接入方式，因此缺HTTP聚合不意味着数据库缺数据；同样，提供PG路径也不意味着业务后端与前端已经完成适配。

## 7. 审计发现、处理与验收条件

| 编号 | 发现及影响 | 本轮处理 / 后续可验证条件 |
| --- | --- | --- |
| D01 | 原A26/A27合并说明容易使人误认为域名/URL/哈希都有值 | 已拆明：进程/命令两例有值，端口仅调查例443，domain/url/file_hash两例均空；图中空态一致 |
| D02 | 旧tool_call的duration_ms=0可能被误读为真实零耗时 | 主文档补明0为默认/未测；无独立测量证据显示“未提供”，旧预览不推出执行成功 |
| D03 | 规则列此前只确认来源快照，主表填充值未核 | 本轮确认两例alerts.rule_id均有值，rule_name均空；同步主文档，保持上游ID与规则名称分开 |
| D04 | “90项展示字段”容易被当成90项全部生产可用 | 增加本审计逐项必要性/子项可得性/条件；未具备卡片不默认启用 |
| D05 | 独立调查页可能被误称原版已有 | 明确是适配无Case自动调查的必要新增组织方式；原版仅提供Case页相关内容基础 |
| D06 | 主文档布局措辞可能与功能示意用途冲突 | 改成信息分组建议，强调非UI/交互定稿；七图继续保留文首及图内声明 |
| D07 | 图05把五类回执都描述成有统一采用计数 | 已按kind说明：前四类采用数0，技能源没有adopted_count，valid_count不能代替采用数；主文档I29同步 |
| D08 | 图07将没有正文合并成尚无报告 | 已区分无report_md目录、目录存在但正文不可用/外置未取到、请求失败；与I10一致 |
| G01 | 关键词、来源/时间/对象过滤、列表source缺口 | 后端选PG查询或补HTTP；验收应含无匹配搜索返回0、边界时间、同条件总量和分页，不用200替代结果断言 |
| G02 | 调查列表识别、目标类型和真正“最新调查”需聚合 | 后端明确已知入口判断，至少核仅分诊/已开始无报告/部分完成/失败；未知目标显示未知，不猜Case |
| G03 | 人员姓名、Run负责人/复核状态无统一现成取数 | A12按人员映射条件，I11暂不显示有效复核；以后须有持久状态、操作人/时间和读取权限合同 |
| G04 | 统一根因、影响结论、逐条证据支持关系缺失 | I22/I36不做已确认卡片；须存在结构字段、证据定位及状态语义后才开放，现报告假设保持假设 |
| G05 | 结构工具结果仅本地，新旧留存粒度不同 | 先旧预览并标范围；本地部署另验I26/I27及截断/留存缺口，不能把上线条件隐去 |
| G06 | 资料丰富度不足：知识引用/外部情报/资产身份/Case链路径等空 | 空态可交付；要声称正例能力，需后续真实有值场景验证，当前不临时伪造数据填卡片 |
| G07 | 模型/工具原始交换并非逐节点全量持久 | 目录/留存范围可交付；缺失/截断明确展示，不宣称每一步完整可重放 |
| G08 | 数据可读与调查有效性不同 | 原查询参数、预算、依据和报告质量问题沿[既有问题登记](../../operations/upstream-issues.md)及主文档保持，不在本审计中追认质量通过 |

G项是后续选定功能的接入条件，不是本轮授权修改业务代码、改表、重新调查或部署。主文档仍是功能字段要求入口，审计附件用于解释其依据与当前可实施边界。

## 8. 复核结果与交付范围

产品审阅者`ui_display_audit`与数据审阅者`local_display_data`对各自证据及最终合稿分别复核，均为**限定ACCEPT，0项本轮必须修正**。覆盖90/90项；独立重算既有21工件正文hash/字节、核21份工件Run及事件关联、6表167列、7份本地源码/测试证据与2份本地样例hash。组合字段空值、技能源采用数、旧工具耗时、报告空态以及MD/JSON发现编号不一致均已修正。

主执行者静态核对主文档、七图和审计90项编号/名称一致，164个本地链接及51个源码行链接有效，七个Mermaid代码块及功能用途声明齐全；公开材料凭据特征扫描0命中。本轮没有重新渲染或采集截图。最终文件hash与校核记录保存在`.local/verification/ui-v1-20261023/final-audit-check.json`，不另存旧版主文档副本。

独审接受的是本次文档、产品判断及取数证据边界，**不代表UI或聚合后端已实现、所有字段都有非空生产数据、所有来源/状态分支已验或调查质量通过**。D01—D08为已修文档问题，G01—G08为已记录的后续接入条件。

本次没有新发Kafka告警、启动调查、调用模型、改数据库结构、修改业务源码或部署，也未提交/推送Git。生产动作限定既有两例的PG只读事务和reader GET；个别GET可能按原服务逻辑生成/缓存派生内容，故不宣称数据库所有行完全零变化。原迁移5/15、旧质量/unknown/预算问题与其他工作流进度保持。

交接阅读顺序：先看本篇第1—2章确认取舍，再按第4章逐字段对接；字段的完整SQL与HTTP返回回到[取数与接口附件](page-data-mapping.md)，页面要素对照看[七图索引](ui-wireframes/README.md)。本篇不要求后续模块按照Mermaid的外观实现UI。
