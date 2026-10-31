> **最新为2026-10-31：** 当前页面和完整样例见[统一入口](../../prototypes/security-pages-v2/README.md)。以下早期记录保持原日期与范围；本次增量见文末“当前页面、完整演示与历史保存”。

# V1 冻结与 V2 事件/调查前端交付回执

**历史增量：2026-10-29 Case已有材料补齐；本轮2026-10-31记录见文末。**

日期：2026-10-26。授权：用户要求将当前前端保存为 V1，再在新端口修改优化；告警页面保持。前置[功能分析](incident-investigation-page-analysis.md)的全部规划不作为本批全部实现承诺。

## 版本与实现

- 冻结 `prototypes/security-pages-v1` 与 `deliverables/aisoc-frontend-v1`，共 52 份源文件；ZIP 298943 字节，SHA-256 `ae2e2c5898469431152ecc748002be42e730e5dd6f98560a995ca5004a394fe9`。清单见 `deliverables/frontend-v1-manifest.json`。原目录未覆盖。
- V1 在本机 4173，V2 在 4174；独立目录与 localStorage 键。浏览器原状态未清理，文件快照不包含用户本地存储导出。
- 事件保留原功能，攻击故事入口改为事件上下文，补材料概况、调查摘要及按种子/窗口查看候选关系的 Chain 页签。
- Case 首屏改为 AI 调查，旧概览移至资料概览；原告警、资产、关系图、任务、证据、活动、评论保留。新增全部运行及无 Case Run 入口。
- 调查按 Run 组织结果与范围、实际输入、分析过程、工具与证据、Chain / Path、报告与响应。6 条实际 Run 从已有回执白名单投影，另保留 2 条设计样例。
- 实际保存输入来自 `run.raw_alert`；输入摘要来自 `run.alert_summary`。不根据当前告警重建历史输入；标题与长摘要分开展示。

## 数据与状态核对

样例 `d141b0e3-16cc-5a0b-8d7f-35159342efe6`：Run completed，调查 partial，判定 needs_review，Graph confidence 0.75；首次分诊 TP/0.85，7 次调用、29025 tokens、7 次未定价。停止原因保留 `token budget exhausted (26922 of 20000)`，不改写旧预算或运行结果。

同 Run 的 attack_chain 为 empty/PostgreSQL，候选 0、24h；attack_path 为 not_linked/no_linked_case；alert_graph 为 success/Neo4j，邻居 5、可达 6、最大深度 3、原始评分 3.1。IOC 使用 `indicator_value`，关系类型使用 `rel_type`；不套用 0—1 评分假设。工具返回中的空行、不可用、查询失败及 200 字符摘要限制保持。

事件 Chain 属于本地设计样例的共享实体/时间窗口筛选，不是正式服务端候选链算法。实际 Run 工件独立展示。报告保持已保存原文，可能保留当时 `running` 和历史措辞；当前 Run 状态和完整性另列，不追认报告语义质量。建议隔离与实际执行 0 分开。

## 直接验证

| 检查 | 结果及范围 |
| --- | --- |
| V1 文件与 ZIP | 52 份源文件/冻结文件逐字节 SHA-256 一致，ZIP 每个成员一致；原目录保持 |
| JavaScript 语法 | `npm run check` 通过 |
| 定向回归 | `npm test` 18/18 通过 |
| 告警保持 | 同输入下 1 个列表、58 个抽屉、58×4 个详情，291 次 HTML 与 V1 一致；告警模块、数据、基础样式原文件未改 |
| 调查视图 | 8 个 Run × 5 页签可渲染，状态不混写、无 Case 不补造 Case、无效/越界 Run 不回落其他运行 |
| 关系与输入 | Case 计数和正文关联一致，候选链筛选不改成员、不造分数；历史输入不受当前告警修改影响；HTML 转义通过 |
| 源值独审 | 6 条真实 Run 140 项字段/工具/图/报告比较无差异；6 条原始输入白名单投影一致 |
| 浏览器 | V1 原事件页面可打开；V2 Case 首屏及调查图谱实际可见；实际工具参数/摘要、报告/建议/执行可见；运行切换到未升级调查时工具数变为 0，标题、结果和范围同步切换 |
| Chain 交互 | 种子切换为未关联 Case 的 Web 告警、窗口切为 1 小时，显示没有候选关系；URL 保留种子和窗口 |

截图留于 `.local/verification/frontend-v2-20261026/case-overview.png` 和 `run-graphs.png`。浏览器核验只证明本地展示与相应交互，不代表服务端流程验收。报告下载入口已展示；未单独验证浏览器下载落盘。

## 问题修正与独立审阅

首次本地服务器绑定因沙箱限制失败，随后使用已批准的同一 loopback 启动命令成功。一次源码替换定位断言失败发生在写入前，随后按实际源码接线；没有覆盖原版文件。

未参与实现的 `workspace_review` 复核了 V1、实际投影、Run 范围和回归，提出 IOC/关系字段、真实 Run 计数、错误 Run 回落、历史输入缺少以及过长标题问题；均修正并复核。最终结论为限定 ACCEPT、0 项剩余必须修。独审执行 17 项既有测试通过；随后追加输入独立性用例，主验 18 项通过。最终交接文档及新增用例窄复核通过，13 个本地链接有效，维持限定 ACCEPT、0 个新增必须修。

## 交接与限制

入口见[版本说明](../../prototypes/FRONTEND-VERSIONS.md)与[V2 README](../../prototypes/security-pages-v2/README.md)。没有后端源码/运行配置变更、新查询/模型/数据重放、生产写入、部署或 Git 提交/推送。此次不是全 22 项调查规划验收；实时状态刷新、完整模型材料、调查 v2 后端入口/领域 profile、Case 服务端关联与响应执行仍由各自模块承接。

OpenSpec 已归档：[`2026-10-26-version-frontend-v1-optimize-v2`](../../openspec/changes/archive/2026-10-26-version-frontend-v1-optimize-v2/verification.md)，新增 3 条规格已同步；严格检查结果见该批回执。


## 2026-10-27：事件基础调查与Case AI能力融合

授权为重新审视并修改V2；用户追加明确保留微软式基础工作区并融合迁移来源AiSOC的Case调查能力。源码参考为本机`SOCAI/opensource/AiSOC/apps/web/src/components/cases/CaseWorkspace.tsx`的InvestigationPanel/AttackChainPanel/AttackPathPanel/ReportPanel及`InvestigationLedger.tsx`。本轮修改4174原型，未修改来源前端、V1或服务端。

功能落点见[分析第13节](incident-investigation-page-analysis.md#13-2026-10-27-v2-融合修改)。事件概览汇总来源清楚的告警判定/Explain/关联调查；Case保留基础功能，突出发现、阶段、Deep、查询证据、链图、筛选调查记录和响应。新增`context`路由接回原事件战术、时间线和证据统计。

验证结果：

- `npm run check`通过，`npm test`25/25通过；291次告警HTML与V1一致、8Run×6视图及来源/覆盖/筛选/历史输入不改写验证通过。与HEAD比较，原前端、V1、冻结交接、原数据与告警模块无改动。
- 浏览器事件262144显示15成员、0已有判定、5条覆盖、2次调查、8实体；点击覆盖指标仅显示对应5条，原资料概况入口可见战术、时间线、证据等6类标题。
- Case17420保留11成员、案件/协作目录；选择第二次Run后仍在阶段分析，输入切为2、partial保持。第一Run输入3、证据4按输入关联展示；不代表AI采用关系。
- 实际Run `d141b0e3-16cc-5a0b-8d7f-35159342efe6`显示graph三节点和Deep6轮/6工具/截断/原停止原因。调查记录选择tool_call与deep-investigator后显示6/12条；攻击路径独立显示未关联Case；报告仍有需审批建议1项与实际执行0。
- 1280px与700px检查：Case导航/卡片按断点重排，事件表格在自身容器滚动，文档宽度没有横向溢出；测试完已恢复默认视口。当前页面控制台未捕获error。
- 截图保存在`.local/verification/frontend-v2-refinement-20261027/`：`incident-overview.png`、`case-overview.png`、`actual-stages.png`、`actual-ledger.png`、两张narrow截图。属于本地验证材料，不重打冻结交接包。

过程修正：首次新增测试把实际告警的incident_id误当已导出的Incident父对象；修正测试为显式test-only父对象，产品不新增实际Incident。原目录测试一次因导航加入SVG使文字正则失效，已匹配实际导航结构。两次在仓库根目录误运行npm因无package.json失败，随后都在V2目录正确执行；不计通过。浏览器初次仍读旧缓存，检查本机服务实际文件后为修改资源加版本号，重新载入后验新页面。

独审指出原summaryView失去入口，已补context入口与直接测试，并在浏览器实际点击确认。最终独审限定ACCEPT、0剩余必须修；本change已归档并同步3条规格，见[审阅记录](../../openspec/changes/archive/2026-10-27-refine-incident-case-functional-workspaces/audit.md)。此轮没有生产访问、模型请求、数据重放、后端修改、部署或新增Git提交/推送。

## 2026-10-28：AiSOC20历史结果填充

本轮仅读取已有本机来源，将2026-10-24六条合成演示输入的实际处理结果追加至V2：6Run、71过程记录、34工具摘要、27工件目录、5份原文报告，36次调用117286tokens。原52设计告警与6条21记录保留。源Case全空，按原三场景整理的local-aisoc20-1/2/3明确为本地展示；历史Run仍是各1条输入。来源映射和限制见[第14节](incident-investigation-page-analysis.md#14-2026-10-28-aisoc20-历史结果填充)。

- 离线导出校验原输入租户/标题/告警ID与delivery的Run/Alert身份，五份报告和独立Markdown逐字节一致。独审另核17份来源SHA，重建投影/manifest与保存文件一致；六Run字段/工具/报告/Deep逐项对源一致，递归未输出模型prompt/response/messages或凭据键。
- `npm run check`及`npm test`32/32通过。覆盖新增数据幂等追加、不覆盖本地编辑、真实来源、6Run×6视图、三个Case全部页签、来源环境/租户候选隔离、阶段跳过、工件缺值、原始实体无假库存、无假附件、数值优先级空值、图关系与时序；原291次同输入告警HTML比较保持。
- 浏览器实际打开Office组，2条成员/2次Run，首Run显示1输入/2当前成员、partial、6查询、5工件、模型置信度95%与首次分诊95；阶段分析明确attack_path已跳过。切到第二Run仍保留阶段分析，策略切到c2-beaconing、查询方向2；工具页真实呈现查询失败、空返回及200字符摘要限制。
- 用户指出攻击链/路径空态后，已接入历史关系资料到该页签，并保留“路径分析已跳过”说明。当前Office组显示7对象8关系，含两条告警、主机DEMO-FIN-11、账户demo.finance、IP198.51.100.41及两条ATT&CK技术；蓝色仅标本次输入。告警时序按原event_time排列，不能代表攻击因果；没有写入Run.graphs。
- 页面截图保存于`.local/verification/frontend-v2-recorded-20261028/recorded-graph-full.png`。本地界面核验不代表新后端调查或语义质量通过；下载落盘本轮未另验。

修正与过程：独审发现null优先级被JS比较归入低分，已用数值有效性校验修复并增加窄回归；未给未知值补分。两次在仓库根目录执行npm因无package.json失败，随后均在V2目录重新执行通过；不将失败计为通过。无新业务读取/写入、模型、重放、后端修改、部署、Git提交或push。

结束独审限定ACCEPT、0剩余必须修；独审自行核来源及30项原测试，修复后复核3项窄回归。主代理最终32项通过、当前页控制台error为空。审阅范围与结果见本批OpenSpec审计。

本change已[归档并结束审计](../../openspec/changes/archive/2026-10-28-populate-v2-aisoc-recorded-examples/audit.md)，同步1条规格；strict all 8/8、archived 29/29通过。


## 2026-10-28：历史实际Case与联合调查

本轮按用户“本地AiSOC数据、继续”的要求，将已有`case-v2`回执接入V2。详细映射见[功能分析第15节](incident-investigation-page-analysis.md#15-2026-10-28-已持久化-case-的联合调查样例)。保留实际Case UUID/Run关系，不重发后端创建或调查。原设计与20单告警记录不变。

- 离线投影/独审核16份来源SHA，重建JS及manifest一致；29条Agent audit与持久Run events逐序、完整payload一致，4工件hash/字节正确，报告与独立Markdown/API返回/最终采用状态完全一致。Agent内部Run ID与API Run不同，单独保留并注明核验依据。
- `npm run check`通过；36项直接测试通过，包括原291次同输入告警HTML比较、新Case/三告警全部详情及六种Run视图、5候选的范围区分、11节点15边、16图可达对象、3建议/0执行、无模型prompt/response/messages/凭据字段输出。
- 浏览器确认真实Case的3输入、1次调查；链页5候选含3个历史外部候选；路径页11对象15边SVG及原始边可展开；关联范围5邻居/16可达/3跳/评分9；阶段页Recon/Forensic/Responder/Report四阶段及采用结果。原Run时间和事件时间8小时差异保留。
- 路径及阶段全页截图：`.local/verification/frontend-v2-persisted-case-20261028/path-full.png`、`stages-full.png`。当前页控制台error为空。浏览器首次旧页处于connection refused错误页，本地预览无监听；沙箱普通启动不能绑定端口，通过授权审查后恢复仅127.0.0.1:4174静态服务，新预览页核验成功。
- 独审指出清空当前成员会丢失真实Case调查历史，已按源Case/tenant/environment保留所属Run，并统一页面及计数；测试清空全部成员后仍有调查发现、历史入口和冻结路径。修正时一次文本替换误及事件页，被2项原测试捕获，恢复事件按成员关联后36项重跑全过。

独立审阅`functional_analysis_save_review`最终限定ACCEPT、0剩余必须修，独立执行7项窄回归全通过；结论不代表调查内容质量或当前线上服务验收。本轮无新业务请求、模型、重放、后端源码改动、部署、提交或push。OpenSpec归档状态见本change审计记录。

本批已[归档并完成结束审计](../../openspec/changes/archive/2026-10-28-populate-v2-persisted-case-investigation/audit.md)，同步1条规格，strict all 8/8、archived 30/30通过。

## 2026-10-28：统一调查关系图设计稿

布局与取数语义见[功能分析第16节](incident-investigation-page-analysis.md#16-2026-10-28-调查关系图统一设计待接入页面)。本轮使用同Run三输入、五候选制作会话内可点击设计；4174源码和数据未变。PG候选、Neo4j已记录关系、技术分类分别表达；距离2但缺少中间连线的E3不补路径，postgres_fallback的Case级技术不作为精确逐告警映射。

浏览器验证告警/技术选择、单边及两端聚焦、候选开关、隐藏实体后从依据恢复可见关系、E3缺关系说明；1024px与390px查看布局，320px无横向溢出，控制台error为空，临时视口已复原。截图保存于`.local/verification/frontend-v2-unified-graph-design-20261028/alert-focus.png`。样稿脚本语法通过。

独审发现并修正关系点击误选整实体、同端点不同来源谓词混同两项；9项交互、4项来源窄回归通过，最终限定ACCEPT/0剩余必须修。仅设计验收，不表示统一图已接入V2或后端已实现新增能力，无模型/业务请求/部署/提交/push。结束审阅见[本批记录](../../openspec/changes/archive/2026-10-28-design-unified-investigation-graph/audit.md)。

## 2026-10-28：告警流程业务数据同步

授权：字段盘点之后，用户要求更改同步上述业务数据。具体区域和字段转换见[功能分析第18节](incident-investigation-page-analysis.md#18-2026-10-28告警流程数据同步到-v2)。仅本机V2和离线投影，无远端业务请求、模型、重放、后端修改、部署或提交/push。

- 输入：10月25日 `observed-final.json`，SHA-256 `e751eb2e57790dbc696c931d5179b4e780bcdb8bab089286c880ec497eae1ec9`；导出时核同租户、Run/Alert归属、77工件hash/UTF-8字节及event关联。
- 输出：3个真实事件×2成员；原12事件保留。6Run共92过程、49原工具记录、77工件（31完整/40节选/6仅目录）。无Case不补Case，无库存不补库存；原未定价、partial及失败保持。
- `npm run check`通过；`npm test`共52/52通过（既有43＋本批9），包含291种原告警HTML比较。直接覆盖3事件×11区域、92过程、77工件与同Run隔离/转义、统计、调查覆盖、管理单改标题、重置后成员及数量。
- 浏览器：4174原用户页刷新即显示15事件；搜索DEMO得到3事件，2/2、2/2、1/2活跃/全部成员；详情基础分诊和partial调查分别显示。Chain切换种子可见empty/1候选及对应Run；材料入口可读工具失败与工件目录，llm_response展开显示业务回复、原件hash与event_id。关系图主机可点击，抽屉显示未关联库存；管理弹窗状态/负责人均选中未记录。
- 两个必须修均已关闭：未知值下拉默认改写；重置遗漏新事件。离线实际点击处理器测试证明只改标题不改告警/Case，重置后不刷新即有15事件和三组两成员。没有在用户浏览器执行重置或测试保存。
- 失败记录：新用例首次因把同环境历史Case也算进本批而断言失败，改为精确六Run ID；后续两交互测试的DOM替身只保留最后一个click监听而误调用告警详情监听，改为按注册顺序执行且按选择器匹配后9/9通过。中途两次编辑命令目录错误、一次模板多余括号均修正；不影响原件或后端。
- 保留校验：本轮前后V1/冻结目录52文件无变，原告警模块、data、replayed-alerts、investigation-data、20/历史Case投影、另一change的统一图JS/CSS均无本轮改写。独审另核既有V1清单源目录与冻结目录共104文件及ZIP一致。

独立审阅 `workspace_review` 未参与实现；首次REVISE两项、修复后重跑9项及JS语法检查，最终限定ACCEPT/0剩余必须修。结论不覆盖模型内容质量、实时服务或另一统一图change。浏览器截图位于 `.local/verification/v2-business-sync-20261028/incidents.png`；保留校验在同目录 `preservation.json`。本批已[归档并完成封后检查](../../openspec/changes/archive/2026-10-28-sync-v2-alert-flow-business-data/audit.md)：同步2条主规格，strict all 9/9、archived 33/33通过，git diff --check通过。


## 2026-10-29：Case已有材料补齐

按用户授权把已有告警流程材料填入Case。新增3个本地整理集合，原16Case保留；6个源Alert/Run的Case仍为空、每Run仍1条输入。FIN/APP/DATA分别28/28/21工件，工具12/28/9，过程28/44/20，报告2/2/1；总计92过程/49工具/77工件/5报告。字段和区域见[第19节](incident-investigation-page-analysis.md#19-2026-10-29将已有材料补入本地-case-工作区)。

案件首页逐Run汇总分诊/调查判定与完整性；案件资料保留本地时间、来源事件和当前成员；工件直接展开并转同Case工具/报告；关系图按当前成员，历史Run引用不随成员移除丢失；处理活动回查原Run。空协作记录不补造，本地管理与源归属分开。日期预置截至保存案件最新创建日，修复固定10月24日排除本批集合的问题。

语法检查及59项测试通过（旧52＋本批7，含291原告警HTML比较）。浏览器核3项列表、FIN双Run汇总与28份工件、工件正文/hash/event关联、同Case工具跳转，DATA仅分诊/partial分开。截图`.local/verification/v2-case-flow-20261029/case-overview.png`；未在用户浏览器重置或保存测试编辑。

独审workspace_review限定ACCEPT/0必须修，独立58项旧全套＋最新16项定向通过，重算投影一致、63保护文件hash保持。主线程最终59/59。开发中路径/脚本匹配失败及误替换事件队列已修复，详见本批OpenSpec验证。仅本机静态页面，无远端业务请求、模型、重放、后端改动、部署、提交/push，不覆盖另一统一图change。

本批已[归档并完成封后校验](../../openspec/changes/archive/2026-10-29-populate-v2-alert-flow-cases/audit.md)：同步1条规格，strict all9/archived34通过，git diff --check通过，最终67份保护文件hash保持。


## 2026-10-29 数据整合最终入口

- 入口：`http://127.0.0.1:4174/#/cases?data=all`；全部19 Case保留，AiSOC 7个靠前，来源筛选可只看7个实际材料集合或12个原案例。来源分开，不混作线上业务统计。
- AiSOC数据：当前3本地Case/6Run、20历史3本地Case/6Run、历史实际1Case/1联合Run；192过程、90工具记录、108工件目录、11报告。Case材料页均可跳相同Run工具、图与报告。20新事件按原ID汇集2/2/1成员，1条无事件保持，事件总数18。
- Case/事件互链、失效ID空态、来源隔离、原Run引用/本地成员编辑保留已测。独审发现当前6告警没有顶层来源字段导致互链漏失，已通过alertFlowData精确成员/租户/环境锚点修复，并补当前3Case双向链接与错误来源反例。
- `npm run check`及65项测试通过；保留291次原告警HTML对照。浏览器发现一处旧资源缓存版本漏更新，已统一更新变动资源版本并重新验证。
- 原始数据/V1/告警详情/另一图change文件的保护清单与截图在 `.local/verification/v2-data-consolidation-20261029/`。最终独审结论和归档见相应change的audit。
- 本批不改后台、未查询或写入远端、未调用模型/重放/部署/Git提交；历史数据与本地Case集合不表示新生产对象或质量验收。

本轮最终独审限定ACCEPT、0必须修；已归档 `2026-10-29-consolidate-v2-case-data`，同步1条规格，封后strict校验9/9及35/35通过。26保护文件均未改。截图：`.local/verification/v2-data-consolidation-20261029/cases-integrated.png`。


## 2026-10-29 功能审计（只读）

详见[逐区域功能清单、9项问题及复现](frontend-functional-audit-20261029.md)。浏览器代表链路与隔离VM检查区分记录；858个渲染组合/1095个本地链接无异常或缺目标，不等于全部操作闭环通过。65项已有测试及语法检查通过，36个V2文件hash保持。启动调查、跨来源移动、活动归属、Unknown保护、反馈/关闭联动及筛选/时间/失效链接共9项未修。所有业务提交仅在无存储、无网络的内存副本执行；用户浏览器仅导航、筛选和打开/取消弹窗。无前端修复、后端请求、模型、部署或Git提交。


## 2026-10-31 当前页面、完整演示与历史保存

用户确认事件和Case均保留完整演示与AiSOC实际材料，不精简例子，历史保存。当前入口见[V2 README](../../prototypes/security-pages-v2/README.md)。

- 改前V2和4份入口/设计/审计文档共39文件已保存到 `deliverables/history/security-pages-v2-before-20261031.zip`，逐文件hash及ZIP hash匹配；V1、原交接、实际投影文件不改。
- 67告警/18事件/19Case/15Run保持；13实际Run相对改前归档逐值一致，仍为192过程/90工具/108目录/11报告。去掉来源标签不改变源Case关系、状态或查询完整性。
- 原两次设计Run独立补5查询/9可读工件/2报告、四阶段和输入范围；Case17420缺省任务2项，用户既有任务和空任务列表保留。工件字节/hash匹配，全部输入last不晚于Run开始，不虚构真实调用/用量或执行。
- 68项本地检查通过（65既有＋3本批），含原告警291次等输入呈现比较。独立审阅另外核15Run×6视图共90次只读渲染、真实Run与归档一致性及浏览器编辑重载。首次预期失败为旧测试仍要求已撤下横幅/来源筛选；更新相应预期后通过。
- 浏览器刷新加载新脚本后实见：事件262144有15成员/8证据/2关联调查且可到Case17420；Case有11成员/8证据/2任务，第一Run的3查询/5工件可读；当前FIN实际Case不再出现来源横幅及后缀，partial和正确事件/Run链接仍在。
- 视觉查看事件概览和Case概览无本批布局异常；截图保存于本次Codex可视化目录的 `latest-event.png`、`latest-case.png`。浏览器未保存业务操作或重置数据。
- 未参与实现者 `current_workspace_review` 限定ACCEPT，0剩余必须修；样例第二Run起止时间及两处选择入口后缀遗漏已修后复核。该结论不覆盖后台能力、模型质量或另一图谱change。

前一轮F07的来源筛选控件已经撤下；其他功能审计问题未在本批修复。无新远端读取/真实模型/后台数据写入/部署/Git提交推送。

## 2026-10-31 事件列表指标与字段口径

用户选择“有关联调查的事件”，初始显示7；成员已启动调查按事件去重，partial纳入、仅分诊排除。状态未提供明确为缺事件管理状态；资产标签与告警一致，相关主机直接展示前2名称/+N；侧栏图标替代展开箭头，成员评分与保存分诊判定并列，事件优先级缺值保留。口径与产品参考见[分析第22节](incident-investigation-page-analysis.md#22-2026-10-31-事件列表七项核对与呈现调整)。

最终语法检查及70项测试通过；浏览器核事件列表/两真实预览/资产标签筛选/名称详情跳转/Case列表19项。原store及全部样例不变，改前3文件和hash保存。独审发现末尾文案替换误入Case函数，已恢复并经3项定向复核和全70项通过；最终限定ACCEPT/0必须修。截图在`.local/verification/incident-queue-20261031/`，完整回执见`clarify-incident-queue-context`归档audit。无后台、模型、部署或Git提交推送。

### 后续：四项事件统计

用户选择右侧活跃、待分配、近24小时有新告警、高严重程度四项，删除状态未提供汇总；事件行与侧栏仍如实显示缺值。71项测试、浏览器默认及700px/刷新检查通过，初始9/4/0/13。独立窄审限定ACCEPT/0必须修；四份改前文件hash保持，原数据与两大卡不改。回执见update-incident-summary-metrics归档audit。

后续位置修正：仅CSS/缓存恢复指标组紧凑右对齐。默认宽实测右边界差0，700px两列可见；源码统计和数据未改，未重复71项逻辑测试。截图在.local/verification/incident-alignment-20261031。

后续文案与浮层：四项名称精简，单个右上角ⓘ通过hover/focus-within显示定义；Escape隐藏且保留键盘焦点，重新聚焦可打开。语法与71项测试通过；默认宽度与700px均右边界差0，窄屏两列，310px说明浮层在视口内。浏览器实测仅悬停仍保持可读、鼠标/焦点离开收起。截图及几何结果在.local/verification/incident-metric-help-20261031；改前四文件保留。
独立窄审current_workspace_review限定ACCEPT/0必须修，统计函数逐字节不变、四份改前hash一致；另两项定向测试通过。回执见simplify-incident-metric-labels归档audit。

## 2026-10-31 事件侧栏整体概述

保存事件侧栏由告警评分块改为事件描述与调查进展；缺状态显示处理状态未记录。原事件数据、Run、整体优先级空值和完整演示因素保持。

- 语法检查及72项测试通过，新增直接合同核用户示例2成员/2部分交付、共享Run按ID去重、triage-only排除、无子结论提升、store不变；更新原侧栏分数断言。
- 浏览器查看Office实际事件，2告警/1主机/2调查/2partial与保存材料一致；原逐告警评分卡和重复技术描述不再显示，缺状态解释可从title读取。
- 浏览器核事件262144原优先级因素及description仍在；700px侧栏摘要自然换行无横溢出。
- 截图actual.png、demo.png、narrow.png及geometry.json位于.local/verification/incident-preview-20261031；改前四文件及hash在.local/versions/incident-preview-before-20261031。
- 独立窄审current_workspace_review限定ACCEPT/0必须修，另4项定向测试通过；6保存事件、12原设计预览和Case列表核对保持，备份hash一致。无真实模型/后台读写/部署/Git提交推送。

同日视觉微调：事件侧栏严重程度与处理状态之间增加16px留白、1px浅线和16px内距；元信息分组，资产标签可另行。仅呈现，无语义和数据变更。
语法及2项既有定向测试通过；浏览器默认/700px间距清晰，实测分隔线前16px、线及后内距17px。截图/geometry在.local/verification/incident-preview-spacing-20261031，改前3文件在.local/versions/incident-preview-spacing-before-20261031。
本批结束独审限定ACCEPT/0必须修，见separate-incident-preview-metadata归档audit。

## 2026-10-31 事件生命周期

默认新建、指定负责人后处理中、仅手动已解决；列表/预览/详情/筛选/表单中文一致。源缺状态单独保留，已有已解决不因改负责人重开，AI完成不解决事件。初始活跃由9增至15，其他三项4/0/13保持。

- 语法及75项测试通过；新增3项验证初始化/重载/源状态保留、单条分配/必填解决说明/人工关闭、批量与占位负责人。既有重置/标题编辑合同已按新规则更新。
- 初轮3失败：范围替换误及Case状态列造成2项失败，已恢复Case原render；旧Not set预期在相关测试中更新。修后75项通过。
- 浏览器事件侧栏默认为新建，管理表单选择Alex Wilber即时变为处理中；仅预览后取消，未保存浏览器测试编辑。直接测试完成保存、重新加载、批量和解决校验。
- 截图default-new.png和assigned-preview.png在.local/verification/incident-lifecycle-20261031；改前4文件/hash在.local/versions/incident-lifecycle-before-20261031。
- 结束独审限定ACCEPT/0必须修，另6项定向测试、56组状态/负责人组合、表单边界及4份历史hash通过；无后台/模型/部署/Git提交推送。

独审发现事件筛选状态选项仍显示“进行中”，已仅对事件status复用独立中文映射，补原字段合同断言；修后语法及2项定向复核通过，Case筛选保持。


## 2026-10-31 事件详情合并与Case衔接

事件围绕“是什么、为何关联、有哪些关系”，说明/信息合一，阶段及时间线入概览，故事图直接展开，关联分析包含图/链；旧context/chain与其他历史材料深链兼容。判断进Case，无Case可显式创建/关联，不启动Run。

语法及81项测试通过。新增共享对象来源去重、创建/并集/重复及跨来源拦截、实际/演示新Case重载与10视图；真实13Run不改。新Case初版演示附件/假Completed及演示Run被来源过滤两个独审问题均修复并补合同。新建/保存由VM测试验证，浏览器未写入测试Case。

IAB验证依据展开并打开告警侧栏、事件跳入已有Case、告警链种子改变对应Run、演示关系图筛选15→2→15。700px文档宽度与滚动宽度均685，无页面横溢出。截图在.local/verification/incident-detail-20261031，改前8文件/hash在.local/versions/incident-detail-before-20261031。

结束独审限定ACCEPT/0必须修，另7项定向合同、216事件视图/90Run视图、8份hash通过；19旧Case概览与初始源数据保持。本批仅本地前端/交接，无后台/真实查询/模型/部署/Git提交推送，详见consolidate-incident-detail-workspace归档audit。


## 2026-10-31 阶段覆盖和关联时间线

ATT&CK阶段覆盖从图后大卡移至事件说明内，改为紧凑计数条；时间线与关联依据合并，最新告警在前，每条展示其实际共同对象。来源对象/告警按钮保持，图谱及Case不改。

语法和81项既有测试通过，按新布局更新已有概览断言，未另增测试。IAB真实Office事件和完整262144阶段布局均已查看；时间线共同主机按钮打开原始对象详情并显示2条来源告警。700px堆叠布局，document clientWidth/scrollWidth均685。截图coverage-wide、timeline-wide、timeline-narrow、design-coverage在.local/verification/incident-coverage-20261031，改前5文件/hash在.local/versions/incident-coverage-before-20261031。源数据和历史编辑不重置，无新Case或Run、无后台/模型/部署/提交推送。独审结论见elevate-incident-coverage-timeline归档audit。

本批结束独审限定ACCEPT/0必须修；18事件54条时间线/182个共同对象标签匹配，3项定向合同通过，36图谱/链视图和19旧Case概览保持，5份历史hash核对通过。


## 2026-10-31 保存事件图谱统一呈现

保存事件概览/关联分析接入同一圆形三栏图谱，数据适配只显示既有告警到对象关系，缺路径不借演示材料。控件、原对象端点/来源、同环境租户边界、缺时间保持，Case/Run与告警链不改。

语法和86项检查通过；Office2告警4对象8边、点击告警/关系来源、筛选空态、取消分组/布局/缩放/播放进度、700px详情下移通过，窄屏文档宽度及scrollWidth均685。截图在.local/verification/incident-unified-graph-20261031，历史5文件保存在.local/versions/incident-unified-graph-before-20261031。完整回执见unify-recorded-incident-graph-presentation的audit；初始数据及浏览器历史编辑未重置，无后台/模型/部署/提交推送。


## 2026-10-31 事件单图、Case入口与队列口径

关系图只在关联分析展示，固定仅此事件；事件Chain及潜在路径控件撤下，旧链深链回到单图。无Case默认新建表单，事件名及全成员带入，显式确认才写入本地；Case/Run的Chain、Path来源材料保持。

- 语法与88项本地检查通过；测试覆盖18事件旧/新路由、残留扩展状态、取消/确认/重载不丢新Case且不启Run。
- IAB核Office关系图1个、概览0图，旧chain链接仍显示单图；700px文档宽度/滚动宽度均685，详情下移。Case17420调查原始Chain 2候选、Path 8节点10边可读。
- 初始所有事件均有Case；无Case创建在隔离VM验证，浏览器未清Case、未新建测试业务记录。原源数据及15Run/13实际记录不变。
- 独审current_workspace_review限定ACCEPT/0必须修：5定向合同、6备份SHA、162次真实注册残留handler保持事件范围，114个Case页及75个Run图输出一致。后续追加仅对Case资产文案作22.10同名同步。
- 用户追加名称统一“涉及资产”；首卡“处理中的事件”按事件处理状态计数，当前5，说明“已开始处理，尚未解决”。原四统计/数据不变；更新既有合同，首轮87/88为V1旧列头断言，单点更新后88/88。浏览器告警及事件列头、卡片数与说明已核。
- 历史6文件：.local/versions/incident-scope-before-20261031；追加前4文件：.local/versions/incident-labels-before-20261031；截图graph-final、narrow、queue-final：.local/verification/incident-scope-20261031。

仅本地前端/交接，不代表后台创建Case或调查运行已接通；无新模型、后台写入、部署或提交推送。完整审计见本批scope-incident-graph-and-case-entry归档audit。

追加独审纠正：负责人取消分配并不自动撤销既有处理中状态，因此卡片说明最终使用“已开始处理，尚未解决”。对应状态边界定向复核通过；追加独审8项定向/4备份SHA/76处呈现及数据对照限定ACCEPT、0剩余必须修。追加窄屏队列685px无页面横溢出，截图queue-final/queue-narrow保留。


## 2026-10-31 事件布局收紧

落实概览去重、图谱上移和默认核心列：状态/负责人/更新时间留页头，成员/主机计数与时间范围改紧凑行，共享/对象数量留对应区域；图谱范围与筛选合并工具区，事件/成员表默认核心7列、完整字段可选、事件ID短显但完整复制/导出。

语法和88项原检查通过，未另增镜像式测试。1600×1000事件262144 whyTop≈580、graphTop309/bottom971，事件默认表1318宽无横向滚动；实际Office2成员/1主机/4共同对象保持。700px三代表页面文档宽及scrollWidth685，图详情下移，表格仅内部滚动。自定义列完整ID保留已核；无业务保存/重置/后台/模型/部署/提交。历史8文件及截图分别在.local/versions/incident-layout-before-20261031、.local/verification/incident-layout-20261031。独审及归档见本批audit。

布局批次结束独审限定ACCEPT/0必须修：5定向合同/8备份SHA通过，完整UUID复制/CSV、默认7列/完整可选列及已有选择保持；6个Case视图逐字等价，store/15Run/统计不变。

### 2026-10-31 事件导航与阶段位置

页签顺序、事件图范围提示/来源名称、ATT&CK阶段位置按新要求调整。语法检查和88项现有测试通过；固定范围合同保留并更新显示断言，无数据修改。改前6文件及SHA在.local/versions/incident-navigation-before-20261031，浏览截图和独审见adjust-incident-navigation-labels回执。

### 2026-10-31 实际数据与事件/告警完整演示

AiSOC20按保存原件重新投影逐值一致，17份原件SHA及21 observed-final SHA共18项匹配。新增3事件/11告警/2Case/3Run，旧记录及13实际Run保持；语法及94测试通过，含6个新合同核关系端点/工件hash/页签/保编辑/创建Case/分配手动解决/反馈作用域。初测的旧计数与日期预期随新增样例更新，跨VM数组断言统一后通过，无业务数据重置。浏览核1600宽屏概览/关系依据/告警完整响应/无Case弹窗及700窄屏；文档宽与scrollWidth均685，未横向溢出；原件来源显示可读，缺源记录ID为—。截图见.local/verification/incident-alert-showcase-20261031，用户浏览器数据未写入，viewport已恢复。完整字段缺口和功能矩阵见[新对照](incident-alert-data-showcase.md)。

结束复核补记：修正新样例冻结输入包含未来人工关闭记录及跨主机查询范围不一致；输入限定为分诊前原始记录，返回记录与args主机/账号/窗口逐项一致，定向6项及最终94检查通过。
