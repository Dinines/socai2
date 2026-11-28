# Case 详情逐页对照与迁移验收

2026-11-26 建立，2026-11-27 更新 · Case 详情逐页迁移

## 取证范围与口径

4173 监听器的工作目录是 `/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2`，以普通入口 `index.html` 实际加载的脚本、样式和 Case 路由分支为准。原型中的录入样例、保存导入、只读分支与普通分支分别判读。8181 监听器在 `/Users/lychee/Projects/SpiritHub-web-8181/web`，以 `codex/spirithub-4173` 的现有工作区为准，底层提交为 `8051df5008af9e711a2c71890ad9bf111ff82301`。本报告以源码、合同及现场观察逐项比较。统筹已打开 4173 的十个默认子页、当前 Run 五视图及另外两轮，也已在恢复登录后观察 8181 十个默认子页。案件故事已完成本机实现、接线及正常会话独立验收，实测覆盖见第 2 节。[4173 样式入口](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/index.html:10) · [4173 Case 与 Run 模块入口](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/index.html:51) · [8181 路由](/Users/lychee/Projects/SpiritHub-web-8181/web/src/app/router.tsx:35)

本次覆盖同一 Case ID 的十个导航、历史内五个 Run 视图及执行明细和直接浮层。旧清单用于查功能编号。有值列表、预览、公共页头及成员集合沿用前轮相应实证。已有工作区修改按当前行为描述，超出前轮证据的页面和尝试仍待实页验收。案件助手发送和定向分析、附件字节联调、响应执行沿已确认的后置范围。原型本地交互用于说明产品设计。正式记录和执行由实际服务回执证明。[既有逐页清单](/Users/lychee/Documents/project/socai2/openspec/changes/complete-socai2-investigation-chain/investigation-page-migration-checklist-20261126.md) · [88 项接口与验收矩阵](/Users/lychee/Documents/project/socai2/openspec/changes/complete-socai2-investigation-chain/investigation-test-matrix-20261126.md) · [前轮列表及建案验收范围](/Users/lychee/Documents/project/socai2/openspec/changes/complete-socai2-investigation-chain/case-list-migration-20261126.md)

所有页面用同一主体和有效角色对照，默认视口从 1280×720 起。图、表、卡、标题及按钮位置、字体字号与行距、长内容溢出、浮层宽度和关闭回焦均按实际有效 CSS 检查。表中的数值是样式声明，可用作测量起点。各表列出的状态和交互是页面设计要求。逐页实测聚焦正常流程及本步实际遇到的具体阻断，核对直接受影响的字段、关联和必要读回。其它设计状态记录已有证据或实页待验边界。

## 逐字段与接口错误的统一核对要求

负责人再次明确：上述十个子页和固定Run各视图都须与4173逐项比对。每页先记录完整区块、控件、字段及预期交互，再迁移；不能仅确认有一个页面或某个请求返回200。

- 每项字段记录：4173来源/含义、当前8181取数路径、展示格式与单位、值为0/空/null/未供/部分时的不同表现、所属当前案或原轮范围、点击目标以及已有验证证据。原型中的值是示例，正式页必须读取真实保存数据。
- 每项直接操作记录：按钮所在位置、打开的浮层或页面、输入/取消/提交效果和对应接口。只验开窗与取消不等于保存能力通过；目录通过不等于固定Run正文通过。
- 对“记录不存在或不可访问”等错误，记录实际方法、路由模板、HTTP状态及业务错误码，由前端→平台→原生逐层定位。分清未接入路由、请求参数/版本不匹配、身份或原父级丢失、真实资源不存在/不可访问及读取服务失败。不能只凭中文文案认定记录已删除，也不能把错误替换为“暂无”。
- 标记源码确认、已有真实证据、本轮实页通过或仍待验证。已完成页面保留原证据；只复验受本步影响的行为，不为凑对照修改原始数据或新增业务补值。

2026-11-27 已补齐[十页及五视图逐字段对照](../../../docs/operations/evidence/case-info-migration-20261127-01/frontend-four-page-field-review.md)和[实际调用及错误定位](../../../docs/operations/evidence/case-info-migration-20261127-01/http-four-page-contract-review.md)，统筹已核对目录覆盖、关键旧路径及证据边界，并纠正案件列表/旧目录的操作编号。当前案件资料、故事、历史目录及固定轮入口、关系图G1的已验范围分别见各节；其余字段/动作继续保留缺口。每次只实施一个边界明确的页面或依赖步骤，不把本次总审当作一次实现所有页面的任务。

## 公共页头与导航

| 设计项 | 4173 实际构成 | 8181 当前构成与差异 | 通过判据 |
| --- | --- | --- | --- |
| 返回与同案身份 | 面包屑、显式 Case ID 加标题、刷新及切换 Case。4173 案件内外壳侧栏有紧凑状态。 | 已改为独立公共页头。列表来源搜索可通过案内目录回传。Case 详情校验响应 `case.id`，切案是可搜索的只读弹窗。Run/标签内部的其他链接仍须核查返回状态。 | 列表筛选到预览、资料、另一个案内页并返回，保持同案 ID、选中状态和原筛选。切到另一案后，标题、关联、任务及临时选中一起切换。 |
| 分组、标签和计数 | Case、AI 调查、案件材料、协作与跟进四组十页。历史、成员、对象、待办、活动及评论附件有各自计数。嵌入 Run 时原型将目录选中指向概览。 | 已有四组十页。当前左侧仅成员告警有计数，历史 Run 通常保持历史链接选中。旧清单的横向页签差异已过时。 | 同案十个标签按指定顺序可达。计数各用实际全集字段，部分和缺供辨识清楚。Run 的父入口选中和返回目标与原型逐项确定。 |
| 页头事实和动作 | 严重度、状态、负责人可进同一管理弹窗。优先级、关键资产及关联事件按资料展示。事件含显式关系和满足来源边界的当前成员关联，超过两项可展开。页头加成员、助手及活跃进度有独立动作。 | 同案已接等级、状态、负责人、标签和已显式关联事件。运行横条与首次任务另读，`latest_run_id` 出现后才有 Run 跳转。管理、关闭和重开由既有菜单处理。 | 同案读取无关联、一个、多项及截断。任务受理未生成 Run、运行中、未知和失败分别显示状态与适用入口。打开或切标签只执行读取。 |
| 布局 | `.page-header` 加 `.case-body`，目录基准 222px，较窄时按 185px、160px 到横向滚动。 | `.soc-case-frame-body` 190px，760px 起横向目录。平台外层导航仍由 SpiritHub 管理。 | 核首屏身份、导航、进度和正文起点不相遮挡。长标题、UUID、多事件及窄屏操作可达。对齐页内标题、图标间距、选中行及正文有效宽度。 |

[4173 Case 路由与页头](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:405) · [4173 分组目录](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/workspace-layout.js:19) · [4173 Case 框架 CSS](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:5) · [8181 四组目录和公共页头](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkspaceFrame.tsx:23) · [首轮提示](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkspaceFrame.tsx:147) · [同案读取](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchDetail.tsx:56) · [8181 框架 CSS](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-workbench.css:105)

## 1. 案件资料 `case-info`

F09-06、F10-01、F11-01 至 F11-03、F12-01、F12-02、F09-07。默认资料页应让用户先识别案情、当前判断和真实范围，再按需查来源、成员与管理。

2026-11-27，负责人标注的管理入口、阶段和整体布局已按[单页方案](case-info-migration-20261127.md)完成本机只读迁移。4173表单存在截止时间，入口统一为“管理 Case”；阶段按最新明确要求改用源标签计数的柱形图。四卡、摘要/成员、右栏详细信息和对象预览已挂载，经统筹17项HTTP/PG及32项普通8181检查通过。[本步回执](../../../docs/operations/evidence/case-info-migration-20261127-01/README.md)

实际同案无源战术标签，页面验真实空态；有值柱形由隔离定向用例覆盖。只验证管理打开/读取/取消，没有提交；管理写合同、正式采用、任务修订/工件父身份真实正例及对象证据目的页不由本步追认完成。以下表格保留迁移前差异与完整判据，当前只读完成状态以上述回执为准。

负责人再次指出资料缺项，复核确认普通4173摘要的主要依据、未决及原来源未在8181首屏保留，原适用范围、条目状态/引用和定级条件区也未完整迁移。前述检查仅证明原回执覆盖项。按[复核补齐方案](case-info-migration-20261127.md#复核后补齐采用来源的完整阅读)，保存来源阅读已补齐并通过20项普通8181直接检查；跨轮覆盖/材料聚合与调查类别仍未完成，当前整页完整性仍未通过。同案新调查另批获准执行，随后17项8181/4177检查确认新模型判断、保存依据/未决及实际输入/输出/原答一致；整体部分交付，未将执行完成或自动采用记成正文质量通过。[新调查独验](../../../docs/operations/evidence/case-capacity-live-retry-20261127-01/README.md)。

### 迁移前对照与完整判据

| 项 | 4173 实际构成 | 8181 当前差异或缺项 | 逐项通过判据 |
| --- | --- | --- | --- |
| 四项范围入口与资料摘要 | 首屏四卡是成员告警、涉及对象、独立证据或告警证据、调查记录，卡可跳页。主列是可折叠案件资料摘要、当前判断、活动范围、查看调查结果和故事，接最近成员预览。导入态另链原始告警材料。 | 当前先放判断卡，再放说明、范围事实格和 ATT&CK 区。范围是成员、事件、对象、材料版本和活动时间，含显式跳转。缺可折叠摘要、成员短列表及原型四个独立入口和层级。不同证据计数语义须分别呈现。 | 同案核四类数量和可供状态，显示未知、部分和零的真实意义。点卡、短列表和摘要去正确页，回到原案。摘要折叠时保留标题与动作，原件按来源与版本定位。 |
| 当前判断及业务判定 | 当前已采用正文、来源、形成或更新时间、适用成员、依据新鲜度、未覆盖，另有按来源展开的业务判定、依据和未决项。无判断可继续看各轮。 | 有正文、系统说明、覆盖、新鲜度和来源。本页 `CaseJudgment` 仍将 `page_data.determination` 作为判定标签输入。队列和预览的正式业务判定映射已修，本页需单独对照。 | 将采用正文、分类和 `current_assessment.business_verdict` 分别与保存字段比对。无采用、正式采用、系统说明、判定缺供各示一例。新鲜度和覆盖各自显示，历史原文保持可回查。 |
| 固定来源与未决项 | 导入模板按原 Result、Run、人工/其他来源看依据与未决项，逐来源展示异常，保留其原范围。 | `CaseReferences` 有来源抽屉，按引用上下文回查。未决项逐 Result 请求并可进新建任务。资料区当前对原因与覆盖有额外独立格线，原型右栏无同款格线。 | 点两类不同来源，核实际 Case、Run、Result 或人工修订以及原材料版本一致。无来源、正文缺供、越范围、读取失败具备明确信息。问题转任务只预填引用，由用户提交。 |
| 详细信息、阶段、涉及对象 | 右栏 Case 详细信息，含状态、显式事件、期限、结案说明等，管理按钮在卡内。ATT&CK 是阶段覆盖卡并带解释，涉及对象列表可回对象页。定级样例另有条件显示的区块。 | 右栏是管理事实卡和编辑分类与期限。阶段在正文下方用共享阶段条，缺原型对象短列表。显式事件主要在页头，结案说明和定级依据需核实际供给和显示位置。 | 核有值、未分配、未设置、已结案及多事件。阶段使用保存的检测标签和范围，单独标识依据性质。右栏卡长文本不溢出，窄屏顺序同设计。 |
| 分类、期限与采用 | 管理表单含分类/期限。导入页支持回查已采用来源。原型资料页没有与现有独立采用比较弹窗等效的确认路径。 | 分类期限独立版本表单。采用弹窗已比较当前和拟采用结论、覆盖及局部确认，但计算来自已读成员，提交仍为旧合同口径。正式采用前预览与版本字段是迁移依赖。 | 取消保持原保存版本。获准后按正式采用预览选择有效 Result，正确处理局部覆盖、冲突及重读，提交一次后读回同案采用指针和旧来源。分类或期限清空以正式 null 读回。 |

样式对比以四卡呈现、摘要折叠、成员短列表和三类右栏卡为观察点。4173 `.case-overview-grid` 的基准比例为 1.75fr / 1fr，8181 用共享 split 和 24px 数字的五格范围卡。核长判断正文行距、嵌套引用的视觉优先级、右栏管理入口及抽屉固定头尾。[4173 固定采用来源](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:415) · [4173 资料及范围模板](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:431) · [4173 范围与资料栅格](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:5) · [8181 资料主体](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchDetail.tsx:67) · [8181 判断、覆盖与来源](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseFields.tsx:45) · [采用比较](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/AdoptResultDialog.tsx:12) · [来源抽屉](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseReferences.tsx:21) · [8181 资料格线和字号](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseDetail.css:4) · [正式 Case 及续建读取](/Users/lychee/Documents/project/socai2/docs/integration/case-allocation-http.md)

## 2. 案件故事 `story`

F20-01 至 F20-05。目标是看本案告警事实、调查工作的发生与保存、人工完成版本，并从任何条目回到原记录。

**本机实现、接线及统筹独立验收通过。** 正常 8181 会话首读已恢复，原 422 和错误叠加空态均未再出现。全案统计与独立的 HTTP／PG 读回一致。 [本机整页验收](/Users/lychee/Documents/project/socai2/docs/operations/evidence/case-story-migration-20261126-01/README.md) · [独立 HTTP／PG](/Users/lychee/Documents/project/socai2/docs/operations/evidence/case-story-migration-20261126-01/coordinator-http-readback.json)

- 实页完成两条告警勾选、切换焦点、单等级筛选、重置、清除选择及搜索有效空态。勾选和焦点独立，切换筛选时全案统计保持原口径。
- 从故事打开固定 Case Run 并返回，同案同轮及既有失败记录均核对通过。返回后默认视口无横向溢出。验收沿用户原有深色主题，对照了时间线轨道、圆点、选中卡、无框统计、选区、标题层级和右侧分栏。助手入口处于明确禁用态。
- 本案默认一次读完 16 条故事记录。游标续页及右栏两个关系分区分别续页由 HTTP 和前端定向检查覆盖。人工完成修订、未知时间和其它冻结输入边界沿隔离直接检查。实际工作树类型检查与 15 项相关测试通过。 [浏览器验收明细](/Users/lychee/Documents/project/socai2/docs/operations/evidence/case-story-migration-20261126-01/coordinator-browser-acceptance.json)

### 迁移前对照和判据

| 项 | 4173 实际构成 | 8181 迁移前差异或缺项 | 逐项通过判据 |
| --- | --- | --- | --- |
| 首屏、范围与入口 | 标题说明、查看调查历史、成员条数、对象数、开始和结束发生时间，然后是一行搜索/单选等级/命中数/重置。 | 用通用工具栏、类型快捷项、多选等级及右侧统计。旧统计读不存在的 `metrics`。缺同层头区、重置、真实范围及活动详情右栏。 | 入口位置、默认控件和统计层级与原型一致。原型“命中告警 / 全部告警”与 E65 `total` 的筛后混合条目总数各有口径。成员数、对象数、活动范围和全量命中告警数各自有正式来源。 |
| 默认请求、搜索、严重度 | 原型单选严重度。告警按标题和对象检索，调查及人工记录可按正文或命中告警联动。选择等级时，原型也按匹配告警收窄这些记录。 | 默认发 `kind=all&limit=50&offset=0`。E65 白名单仅为 `q,severity,limit,cursor`，任何未知或重复键返回 422 `story_query_parameter_not_supported`，因此截图错误在取数入口。旧 8181 界面另有类型快捷项与多值 `severity_groups`。E65 默认视图的单值等级筛选保留调查和人工上下文。 | 当前同案首次请求只带合法键。词长最多 200，关键词对全案生效。按原型验证搜索、重置和单选等级。按 `view=related` 验证等级对相关调查和人工记录的联动及全案统计。 |
| 时间线、时间与游标 | 事实卡和工作卡混排，降序，未知时间在末尾独立组。告警卡有时间、等级、阶段/对象和聚焦区，工作卡有保存或结束时间、摘要、变化及影响。 | `VerticalTimeline` 读老扁平字段 `kind,at,title,body,phase`，按客户端时间排序。旧 `offsetPage` 读 `next_offset`，无法续 E65 游标。正式三类为 `alert,investigation,human_result`，时间是 `occurred_at/time_source`，内容来自 `alert/run/results/task_revision`。 | 保持服务排序，同时间稳定键一致，未知时间在最后。原样传 `next_cursor`，换案、搜索、等级后从首页取。终态 Run 的保存结果保持属于本轮，各结果独立跳转。待启动、未知、失败、真实无结果有可读状态。 |
| 聚焦、选中与共同线索 | 点击告警聚焦右栏，勾选是另一操作。右栏展示聚焦说明、详情、该告警与其他案内告警的共同对象、覆盖该告警的调查及图入口。清除选择及提问有独立动作。 | 按标题直接打开通用 AlertPreview，右栏只按勾选集合显示。选中后另发对象请求并以 `kind=run&alert_ids=…` 调 E65。E65 拒绝这两个条件。旧读侧没有焦点成员关系入口。 | 单击聚焦和勾选的状态分别稳定，关闭预览或回跳不丢同案选中。逐个聚焦本案告警，核与其它案内告警的共同对象以及范围包含该告警的调查。多条告警勾选保留为独立的选择状态。助手入口按既有后置边界，选择本身只读。 |
| 原记录与边界状态 | 告警进详情或故事右栏，调查回同轮，人工回任务。导入态提示可用记录与未保存内容。 | 老逻辑按 `row.alert_id/run_id/task_id/revision_id` 拼跳转，正式字段位于各自嵌套对象。错误后仍渲染空时间线，容易同查空混淆。 | 按 `alert.id`、`run.id` 与实际 Result、`task_revision.task_id/id` 解析。人工 `is_current_task_revision=false` 显示历史版本。加载、首屏失败、无匹配、空案及尾页失败分别验证。失败提供重试，已加载内容按实际范围保持。 |

### 本机现行取数和回链

- 8181 通过 E65 的 `view=related` 读取按时间排序的全案结果及 `summary`，搜索和单等级按正式关联过滤，游标原样续读。E65 默认视图保留既有响应和旧游标语义。 [现行故事设计](/Users/lychee/Documents/project/socai2/openspec/changes/complete-socai2-investigation-chain/case-story-migration-20261126.md) · [8181 请求接线](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/workbench-api.ts:35)
- 右栏按摘要的真实焦点告警读取成员 `relations`，共同对象和相关调查独立续页。卡片等级取告警事实，检测战术和最多三个对象沿 E28、E30 承载。相关告警分诊、事件诊断按固定轮与保存结果身份读取原摘要。 [8181 故事组件](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseStory.tsx:56) · [固定阶段摘要](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseStory.tsx:263) · [焦点右栏](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseStory.tsx:324)
- 专用时间线使用 280px 详情栏、28px 分栏间距和 1100px 单列断点。 [4173 故事模板](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.js:127) · [4173 故事样式](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.css:1) · [8181 故事样式](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseStory.css:91)

## 3. 调查概览 `overview`

F14-02 至 F14-05、F16-01、F22-01。本页面向当前工作、已有分析结果和待确认事项。带 `run` 的原型入口是具体运行读取，和不带 `run` 的概览分开核。

| 项 | 4173 实际构成 | 8181 当前差异或缺项 | 逐项通过判据 |
| --- | --- | --- | --- |
| 当前工作和范围变化 | 当前工作卡区分执行中和待启动，范围变化横条列增入/移出，随后是当前成员、涉及资产、已有记录入口。 | 当前工作改成执行中/待启动两栏。读 `baseline_records`，有版本、资格和比较范围，成员、资产与已有记录概览条不齐。只靠该字段会遗漏尚未获得 Run 的已受理任务。 | 用真实任务状态、冻结 Run 和 Case 范围分别核待受理、在途、状态未知和历史待启动。核新增、移出、无变化与缺比较来源，旧 Run 冻结不漂移。 |
| 检查更新和启动 | 原型有调查安排与范围确认模板。导入或非模拟模式保留已保存状态或禁用执行。 | 仍提供 `准备新一轮`、`更新待启动范围`、`确认并启动`，调用旧 prepare/start。正式后续调查由异步 `POST /investigations` 的 check/rerun 受理，用任务原身份读回。 | 页面先明确动作作用范围和已授权能力，受理态、无变化跳过和已有 Run 分别呈现。取消、冲突、关闭案、未知回执时能按实际状态恢复验证。重复点击不产生另一业务请求。 |
| 已有结果摘要 | 终态结果卡默认前三项，结论与目的、发现、认识变化及对案件影响，用本轮输入和保存时间，连到分析依据、原调查和全部历史。 | 结果区现默认五项，系统说明、部分覆盖、未决数、已经采用提示。有 Result 即按其身份读覆盖和未决项。缺原型的简短目的/发现及成对入口，需对齐状态层级而保留正式来源判读。 | 验活动轮与终态分开，成功、部分交付、失败、有系统说明无正式判断分别正确。点击卡片中的依据、详情或报告定位同一 Run 和 Result。 |
| 人工与待确认 | 右栏有待办摘要和跨轮待确认，含已存的限制/后续建议和更多历史。上方有案件故事入口。 | 右栏为待办计数及列表、历史/故事链接，缺独立跨轮待确认区。待办全集计数与已加载任务有区分。 | 核真实任务、问题与建议三者角色。点人工项定位本案相应任务。读待跟进限制时标明原 Run。空、部分、失败和已加载用语准确。 |

对齐标题和故事入口、当前工作横条、范围入口行、主列结果卡和右列人工/待确认卡。4173 的 `.iv-case-overview-grid` 有独立单双列断点，8181 沿用 `.soc-workbench-split`，需用实际视口核对首屏排列。[4173 概览模板](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:321) · [4173 当前工作与待办](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:150) · [原型调查安排弹窗](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:224) · [概览样式](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:3) · [8181 当前工作与结果](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigationOverview.tsx:17) · [旧启动弹窗](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigationOverview.tsx:38) · [待办与结果卡](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseOverviewPanels.tsx:14) · [8181 详情分栏](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/DetailWorkspace.css:17) · [正式异步检查与再次调查](/Users/lychee/Documents/project/socai2/docs/integration/analysis-submission-http.md)

## 4. 调查历史 `investigations`

F14-06、F15-01、F16-02、F12-03。调查历史列为下一独立迁移页。故事验收中已核原 Run 回链，目的页仍复现旧目录读取错误。先核不带 Run 参数的轮次目录，再核选中 Run 的六类读取入口。五个主视图与执行明细详见后文。 [未完成边界](/Users/lychee/Documents/project/socai2/docs/operations/evidence/case-story-migration-20261126-01/README.md#未完成边界)

| 项 | 4173 实际构成 | 8181 当前差异或缺项 | 逐项通过判据 |
| --- | --- | --- | --- |
| 目录首屏、分类与选择 | 无 `run` 时每轮一张纵向卡。状态、完整性、标题、结论摘要、耗时/工具/模型/Tokens、输入和开始时间，显式打开调查。带 Run 后有当前调查下拉和返回概览。 | 无 `run` 也会取第一页首项自动渲染。250px 左侧窄栏是历史条目选择，右侧直接嵌入运行。缺原型独立目录卡、首屏统计及 Run 选择器。结果条目与轮次可混陈列。 | 同案只在适当动作后进入指定 Run。提供可回目录的入口。两轮和同轮多结果可分别定位，所见统计与原轮次一致，目录无结果与加载错误区分。 |
| 正式目录与关联轮次 | 原型目录合成含同案基础调查及有明确来源关系的历史记录。关联类别依据保存来源。 | `caseApi.history` 已发正式游标请求。关联告警/事件轮次、未命中深链仍用旧 `/runs?case_id` 和 `q`，不能假定新的全局 `analysis-runs` 提供相同关系范围。 | 各类来源、相关主体和权限经实际接口核实，缺链或找不到目标有独立状态。打开深链在分页外也精确找同轮，防止默认落到首轮。 |
| 比较与冻结输入 | 每轮各自数据，当前案新增或移出成员不会改变冻结范围。摘要和比较保留当时结果。 | 运行视图支持结果链接和保存比较 ID，但历史首屏没有原型规模的摘要与投入展示，独立页返回继续依赖旧上下文接口。 | 以前一轮正式比较链接核结果和空态。对照历史冻结与当前 Case 计数、原件和人工版本。重读后保持 Run/Result 参数，未提供用量保留未知。 |

样式上检查 4173 `.iv-run-link` 卡片目录和 `.iv-run-selector` 行，与 8181 左栏分割线、选中高亮、嵌入运行五项状态区分别对照。当前两层左导航缩小运行内容的可用宽度，需要在同视口核参数栏、长标题和回链。[原型无 Run/有 Run 路由分支](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:331) · [4173 历史轮次卡](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:197) · [4173 Run 工作区](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:420) · [4173 运行样式](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:8) · [8181 历史、旧关联目录与选择](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigations.tsx:14) · [正式历史游标绑定](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/workbench-api.ts:50) · [8181 历史左栏](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-workbench.css:149) · [独立运行及回到案件](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationDetailPage.tsx:15)

## 5. 告警 `alerts`

| 项目 | 4173 | 8181 现况与差异 | 迁移通过判据 |
| --- | --- | --- | --- |
| 表格与成员字段 | 案内共用告警表，默认列为名称、标签、严重程度、调查状态、处理状态、类别、分类、检测源、涉及资产、首次活动、末次活动、负责人。表头与行支持选择。标题下另有成员动作和表格工具条。 | 当前为名称、严重程度、告警时间、处理状态、涉及资产、判断覆盖、加入方式。资产已从对应告警取值，加入方式已补 `incident_link`，判断覆盖仍可读取。表格缺原型的表格行密度、列组及部分业务列。 | 按 4173 确认默认列顺序、排序、名称链接、空白列及长值。逐列按告警正式合同核取值。业务字段有独立来源，避免用告警时间代替首次/末次活动。当前覆盖另有可追溯入口。 |
| 工具条与分页 | 有搜索、日期、筛选、刷新、导出、列设置、分页和勾选条。原型分页大小可选 8、15、25。 | 当前对已载入的成员名称本地筛选。受 E03 返回的成员截断与平台加载量影响，案内全量搜索、列/导出范围及日期筛选未接。 | 用超出首段的同案成员核搜索、页大小、总数、选择随排序和翻页的行为。数据截断要可见，导出及筛选的作用范围应一致。刷新后保留合规状态并反映已保存变更。 |
| 添加与移动 | 原型可分别选独立告警和事件。事件行可展开自身告警和数量，支持多事件和混选。已在案项有状态。移动先勾选案内告警，再单选目标 Case 并确认。 | 共享页头已有添加。当前案内表有批量移动。新添加已切换正式查询，候选弹窗当前为分栏平表。多事件展开、已在本案与在他案候选区分、移动后实际接收方展示待核。移动接线使用源/目标版本，当前成功关闭后重读。 | 核候选的源环境、租户、资格和总数。选两组事件再勾重复告警，确认服务回执去重，已在案、不能分配、分配到已有或新 Case 的反馈可见。移动前后分别读源案、目标案和正式分配回执，失败保留选择，冲突重读版本并可取消。 |
| 多事件成员界线 | 事件展开表达事件自己的告警集合。案内表表达当前 Case 的成员集合。历史还保存各 Run 的冻结集合。 | Case 详情直接读当期成员，事件入口和来源标签已存在。缺一处可核全部成员来源/事件展开的对应视觉，不宜用按钮数量推断成员完整。 | 对同案两个显式事件分别核事件内成员、案内实际成员和独立加入成员，可见未纳入同一 Case 的事件告警。源条件相同仍按身份去重，详情中的证据和计数同一口径。 |

[4173 表格和工具条](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:158) · [4173 案内告警布局](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:411) · [4173 事件候选与展开](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:217) · [4173 移动确认](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:511) · [8181 成员表](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchDetail.tsx:85) · [8181 添加选择](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseSelectionDialog.tsx:18) · [8181 移动选择](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseSelectionDialog.tsx:88) · [E03 详情](/Users/lychee/Documents/project/socai2/services/api/investigation_http/external_routes/cases.py:120) · [成员替换、关联与移动合同](/Users/lychee/Documents/project/socai2/services/api/investigation_http/external_routes/cases.py:164)

## 6. 关系图 `attack`

| 项目 | 4173 | 8181 现况与差异 | 迁移通过判据 |
| --- | --- | --- | --- |
| 首屏与基线 | 案件视图从有已保存工件的调查挑选基线，原型记录允许失败 Run 保存有图阶段的结果。已保存拓展在其原基线上重新打开。普通样例可展示按成员投影。记录模式有基线未保存的独立提示。 | 案件视图先显示成员关系，可在历史载入项中选有 `graph_artifact_id` 的 Result。默认图、同轮多图、失败轮保存图、带拓展的旧基线选择不同。 | 首屏明确标记是哪一 Run、哪一图及时间，历史基线可复现。没有正式图时说明缺供或显示带来源的成员视图。失败、部分交付及工件已留存能独立表达。 |
| 图面布局和交互 | 左栏告警与检测层、中间画布、右栏选中节点/边/详情。工具条缩放、拖动、适应、重置、分组或分层，点击可定位来源告警和关系。CSS 默认左右 215px/235px。 | 共享关系图已有画布和控制，工作区里的查询/预览是独立块。默认图滚动高度受共享 640px 限制，缺与原型对应的三栏布局、层级栏、连通详情和来源列表。 | 同一数据的分组、节点、边、标签、缩放范围和第一视口逐项比对。点击节点/边显示其类型、依据和关联范围，点来源再返回可保持基线。键盘、窄屏、无边、无节点、部分图及读取失败各有实态。 |
| 探索、保存、加入 | 图内可开候选侧栏，展示范围/原因，选项扩展、撤回、清空、保存及还原。加入案有确认。已保存快照带基线和候选。 | 已有候选筛选、预览、撤回、排布、保存和读取界面，仍走旧预览和复数 `explorations` 端点。新后端使用 `exploration-base`、`exploration-candidates`、单数 `exploration`。当前加入后未在图内展示正式分配回执和成员受影响范围。 | 验同案基线身份、候选只读浏览、保存后精确复开及取消保留。加入后读取实际成员/关系/回执，重复或他案候选有明确结果。读取旧基线时不随当前选中 Run 漂移。案件助手生成与定向分析仍按后置范围。 |

[4173 案件关系图选择](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:332) · [4173 图详情和三栏](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-graph.js:137) · [4173 图布局](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-graph.css:11) · [4173 拓展和保存](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-exploration.js:37) · [8181 基线视图](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseGraph.tsx:21) · [8181 拓展](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseExploration.tsx:21) · [8181 画布](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/RelationGraph.css:7) · [8181 拓展旧取数](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/workbench-api.ts:19) · [正式基线和快照](/Users/lychee/Documents/project/socai2/services/api/investigation_http/external_routes/exploration_state.py:32) · [候选合同](/Users/lychee/Documents/project/socai2/docs/integration/case-exploration-http.md)

## 7. 对象证据 `evidence`

| 项目 | 4173 | 8181 现况与差异 | 迁移通过判据 |
| --- | --- | --- | --- |
| 框架与对象目录 | 页头计对象、证据、调查材料，提供「按对象查看」「调查材料」。左栏对对象/证据词检索、类型、重置、排序和无关联证据。右栏显示对象身份、分类、关联告警，完整与无原件各自表达。 | 首屏概要更偏证据状态、威胁、覆盖和限制五格，目录是已加载对象的名称搜索和按钮筛选，使用旧 `/objects` 视图。无关联证据区、对象与资产区分及右侧相关 Run 卡未完整呈现。 | 正式来源确认后逐项核对象、证据、材料总数及搜索范围，独立资产字段不当成对象记录。核类型和排序、无关联对象、无原件、已失效、未核实与读取失败，证据归属不会因另一个事件同名对象串案。 |
| 证据明细与原件 | 对象右侧证据卡带类型、依据、源成员预览（默认前三项，可展开）和相关 Run。记录分支按来源显示材料，关联只用于导航。 | 能显示关联到选中对象的证据、原始工件按钮，当前证据范围受旧接口返回约束，缺可单独辨识的无对象证据。案内与 Run 原件分别有取数链。 | 分别打开有/无来源的对象证据，点来源回同案下对应告警、Run 或工件。不可读原件保留元数据与权限/缺失状态。冻结证据在当前成员变更后仍可按其历史范围打开。 |
| 调查材料及布局 | 单独的 Run 卡目录带保存覆盖、冻结输入和工件分类，支持展开。左侧窄栏和右侧证据卡在小视口换行。 | 当前在材料选项嵌入历史工作区，首屏没有逐 Run 材料卡和目录。对象区两列网格左侧 300px、间距 24px。原型窄屏为 205px 等断点。 | 同屏对齐目录和卡片层级、搜索与定位。每个 Run 独立展开可见材料、目录摘录、截断与未录。切换工作区带上当前 Case、Run、Result，在返回时恢复所选对象或材料。 |

当前正式取数需按案件数据、证据索引及案内源工件的职责核对。如果平台继续提供对象聚合视图，应由正式记录给出对象归属和关系。已核原生案内路由有 `page-data`、证据索引发布及源工件读取，聚合 `/objects` 要另核明确的服务来源、字段映射与过滤边界。

[4173 对象与材料布局](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:167) · [4173 Run 材料卡](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:289) · [4173 对象证据样式](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:94) · [8181 对象和证据布局](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseEvidence.tsx:23) · [8181 调查材料入口](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseEvidence.tsx:55) · [8181 对象证据布局](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-workbench.css:155) · [案件数据及证据索引](/Users/lychee/Documents/project/socai2/services/api/investigation_http/external_routes/cases.py:150) · [案内源工件](/Users/lychee/Documents/project/socai2/services/api/investigation_http/external_routes/cases.py:264)

## 8. 人工任务 `tasks`

| 项目 | 4173 | 8181 现况与差异 | 迁移通过判据 |
| --- | --- | --- | --- |
| 列表与统计 | 任务卡集中显示事项、状态、负责人、期限、内容和已完成产出，按当前规模在首屏可扫读。保存导入的历史任务可查看原任务范围、修订、完成结果。 | 有待办/全部及服务端未完成计数，正文为八列表格，额外显示版本、更新时间、操作。旧版本在右抽屉或链接里展开，列表默认视觉和状态认知与原型不同。 | 按原型检查首屏卡与计数、逾期、未分配、已完成及无任务。列表呈现最新保存态。打开历史版本后，仍能辨识其当期范围、时间、责任人与结果。 |
| 新建/编辑与业务来源 | 居中表单将任务、负责人、日期、来源、范围和进一步检查放在同一操作。可以关联具体调查/来源，并查看已保存详情。 | 右抽屉支持整案或选定告警/对象和时间窗，选择项的状态与来源靠正式字段和加载回退。冲突可读最新并显式替换，避免静默覆盖。谈及旧 Run、对象或历史版本时需核来源身份及布局。 | 验从 Case、Run、故事事件进入时能带入正确来源，整案和选定范围可见，未找到旧引用仍可审计。一次保存一版，读列表/详情/版本后刷新保持。表单关闭和冲突路径保留草稿且可以安全退出。 |
| 版本与调查使用 | 已完成产出单独显示，导入静态记录保留完成时的来源与版本。 | 版本目录和单版入口已具备。把已完成结果当下一轮输入的选择应以保存版本及范围为限，旧启动仍待替换。 | 确认正在选和已冻结的任务版本明确区分。改变当前版本后，原 Run 仍可打开原修订。结果和完成状态分别核查。任务列表与版本目录有单独分页、加载、空态、失败处理。 |

[4173 任务卡与历史详情](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:202) · [4173 居中任务表单](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:224) · [4173 浮层布局](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:88) · [8181 待办/全部和任务列表](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseTasks.tsx:20) · [8181 任务抽屉与版本](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseTaskDrawer.tsx:20) · [8181 来源选择](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/TaskSources.tsx) · [正式写入、列表及版本](/Users/lychee/Documents/project/socai2/services/api/investigation_http/external_routes/tasks.py:30) · [人工任务合同](/Users/lychee/Documents/project/socai2/services/api/app/socai2/human_task_contracts.py:46)

## 9. 活动 `activities`

| 项目 | 4173 | 8181 现况与差异 | 迁移通过判据 |
| --- | --- | --- | --- |
| 活动目录 | 七列为时间、标题、类型、目标、执行者、触发、状态，提供查询与通用表设置。记录导入可区分已保存活动、Run 明细的投影及告警发生。 | 当前为垂直时间线，支持按动作类别筛选和分页。单项内嵌改动、匹配目标和截断线索。缺原型表格、标题/目标搜索、列与排序控制、单项点击详情。 | 第一屏依原型核表头、时间顺序、动作与来源分组、搜索、缺省列和分页总数。保存的动作、阶段执行、告警发生、建议、部分或失败各按字段显示，来源缺供时有状态。 |
| 单项详情与跳转 | 点击行开约 455px 右侧详情，展示记录身份、执行时间、对象、状态、与相关 Run 日志入口。 | 当前读案内活动页，改动与目标展示在行内，未覆盖独立详情抽屉或同 Run 步骤定位。 | 点单项保留 Case/活动身份，打开原 Run 或其它来源后能回到原条目和过滤。核已保存变更的前后值、角色、失败/未执行和截断。只有发生过的动作进入实际执行时间线。 |

[4173 活动来源和列表](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:309) · [4173 活动详情抽屉](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:472) · [8181 活动时间线](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseReadPanels.tsx:11) · [8181 时间线样式](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/soc-workbench.css:62) · [正式活动分页](/Users/lychee/Documents/project/socai2/services/api/investigation_http/external_routes/cases.py:273)

## 10. 评论附件 `comments`

| 项目 | 4173 | 8181 现况与差异 | 迁移通过判据 |
| --- | --- | --- | --- |
| 评论 | 左侧时间序列卡有作者头像、时间和正文，尾部输入限制 4000。记录样例可见历史来源与只读记录。 | 当前保留作者快照、可有来源引用和分页，提交输入限制 10000，两列等宽。来源联动和从历史回到对应评论的滚动状态需核。 | 核实际作者、时间、长文折行和键盘操作。明确正式评论长度限制与产品表单一致性，空白、超限、提交、失败、重试、保存读回可区分。右栏优先级和窄屏阅读顺序按原型。 |
| 附件 | 右侧附件区显示文件名、时间、来源及打开/下载。部分保存页的报告或材料单独走原 Run 链。两栏为 1.5:1，间距 20px，窄屏单列。 | 当前两栏约 1:1，间距 24px。已有登记前先上传的界面、拖放、格式和 5MiB 前置检查、登记失败后重试，支持加载已有附件元数据。正式服务本期主接元数据，文件字节联调仍后置。 | 核已有登记、无附件、无可读内容、来源不可用和故障提示。可访问报告/材料从实际来源打开。元数据、内容及上传成功分别判定。未确认字节传输前保留后置项。 |

[4173 评论与附件](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:436) · [4173 两列布局](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:5) · [8181 评论与附件](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseCommentsAttachments.tsx:16) · [8181 上传与登记](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseCommentsAttachments.tsx:48) · [8181 两栏样式](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-workbench.css:174) · [正式附件登记、目录和详情](/Users/lychee/Documents/project/socai2/services/api/investigation_http/external_routes/attachments.py:26)

## 历史内 Run 工作区

4173 在案内历史选择 Run 后，页头显示返回、同案 Run 下拉、身份和开始/结束、执行与交付，再由五个主视图接管正文。「执行明细」从 AI 分析进入。8181 的已实现五态条与标签可复用。嵌入 Case 时历史左栏常驻，独立调查详情依赖 `run-context`，嵌入和独立的选中上下文与来源返回均需核对。Case 运行目前取单轮回执内联的成员、步骤和工件。正式回执同时给出目录地址、截断态和比较链接。Step 与 Artifact 均有同源的正式游标目录。告警调查已有专用记录上下文，案内须验证它的独立转发及权限边界。

| 项目 | 验收判据 |
| --- | --- |
| 进入与切换 | 从历史卡和案内概览进入至少两个已有 Run。切换 Run 后保留目标视图，让从属 Result、选中明细等归属于新轮。切换 Result 保持 Case、Run 及视图。存在同轮多结果时应可选、可回显，结果缺供时有明确状态。外部/错误 Result 应提示不匹配。原型样例若仅按 Run 切换，也需用正式记录验证 8181 独立 Result 语义。 |
| URL、返回和身份 | 从查询/证据、关系图、活动或来源直接打开，重载和浏览器前进/后退仍回到匹配的主体、Run、Result 及视图。比较入口用已保存关联，既可跨 Run 又能返回观察起点。案内目录按正式关联筛除无关主体。相关告警和事件的分诊按各自主体读取和展示。打开 Case Run 和 Result 时核对所属案件。 |
| 运行状态和时间 | 按执行、交付、停止原因、请求/执行/完成、记录时间和时长逐项显示。执行中依据正式的观察时间，终态优先用已记录时长，用量未知不补零。区分失败有工件、部分有结果、实际未开始和清空式空态。 |
| 完整目录 | 核大于首段读回的步骤、工件和结果，显示真实完整性与总数。缺字段、地址不可用和内容失败可重试。切换多个 Run 后，分页、查询缓存、选中项、快照和原件都受 Run 约束。 |
| 版式 | 对齐返回、Run 控件、状态条、页签和正文首段。核左栏是否仍合理占位，所有五个标签及「执行明细」在长 Case 标题和窄屏均可操作。 |

[4173 Run 路由](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:166) · [4173 选中 Run 工作区](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:420) · [4173 状态栏与正文布局](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:8) · [8181 案内 Run 选择](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigations.tsx:14) · [8181 Run 工作区](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunWorkspace.tsx:17) · [8181 独立 Run 入口](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationDetailPage.tsx:15) · [目录和比较链接](/Users/lychee/Documents/project/socai2/services/api/investigation_http/run_record_contracts.py:88) · [正式步骤与工件目录](/Users/lychee/Documents/project/socai2/docs/integration/run-records-http.md:7)

### Run 1. 调查发现

| 项目 | 4173 | 8181 现况与差异 | 迁移通过判据 |
| --- | --- | --- | --- |
| 结论与发现 | 左主栏先说明目的、实际结论与可靠性，再列发现、对案影响、变化、未查清项、限制。已有依据、查询预览、近期步骤、建议和实际响应各有区域。 | 当前具备结论、系统交接、发现、影响、变化、未决、限制和采用按钮。Case 结论标题仍从共用的 `verdict` 取值，而 Case 正式字段是 `business_verdict`。缺部分原型的查询卡、材料可核查区及活动预览。 | 同屏逐字段核正式业务判定、来源、质量、适用范围、影响、对比和未知项。系统说明、助手未保存回答、已保存模型结论与人工来源分开。有证据的事实、推断、未解决及撤回各可追溯。 |
| 右栏范围与投入 | 展示冻结成员和当前范围的变化、关联人工任务和评论、只读 Run 元数据与执行投入。可从材料回原告警或冻结记录。 | 已有投入与覆盖、未覆盖成员和冻结输入按钮。待补以本轮为中心的来源、任务修订、当前范围对照及折叠层级。 | 取跨两个显式事件的全案轮与选定轮，对比每轮冻结范围和当期成员集合。每条已覆盖、未覆盖、待复核及首段截断有说明。跳转和返回保留当前结果，未知预算或费用无推算值。 |

[4173 Run 元数据和范围](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:243) · [4173 调查发现](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:257) · [8181 调查发现](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:29) · [正式 Case Result 字段](/Users/lychee/Documents/project/socai2/services/api/app/socai2/case_contracts.py:206)

### Run 2. AI 分析及执行明细

| 项目 | 4173 | 8181 现况与差异 | 迁移通过判据 |
| --- | --- | --- | --- |
| 分析过程 | 按阶段展示所作工作、已采用的输出与证据入口。右侧显示当轮约束、未决及下一步，关系可追到对应快照。 | 分析过程和执行明细已有两个切换入口。分析过程用步骤类型进行分组，在有工件时支持打开，Case 仍以回执内联步骤共用时间线。独立的阶段显示、同一阶段多步骤及右栏限制需核。 | 逐 C 段核身份、先后、输入、调用、采用的输出和真实状态。已记录失败阶段可开错误，上游跳过和无记录各有空态。模型原答、阶段摘要和保存的结论可区分。 |
| 执行明细 | 明细有类型、执行者和执行节点筛选，按序展开步骤。展开保留执行理由、调用/预留、耗时、摘要、截断及已保存引用。 | 已有明细时间线、步骤详情、参数/错误、工件和冻结能力配置。Case 未拥有告警视图同等目录分页与步骤 URL 状态，原型的执行者、类型、节点筛选与首屏明细层级不齐。 | 用同轮的阶段、工具、模型、图和渲染步骤核筛选、分页、关联、不同用量状态。直接定位一个已保存步骤并刷新、返回。日志只能反映本轮实际执行和保存，缺原件时保留目录元数据及状态。 |

[4173 分阶段分析](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:272) · [4173 执行明细](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:284) · [8181 分析及明细](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:80) · [8181 配置和能力信息](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:178) · [8181 明细样式](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/investigations.css:24) · [正式步骤字段](/Users/lychee/Documents/project/socai2/docs/integration/run-records-http.md:70)

### Run 3. 查询与证据

| 项目 | 4173 | 8181 现况与差异 | 迁移通过判据 |
| --- | --- | --- | --- |
| 查询目录和单项 | 查询按当轮排列，有总体查询/材料覆盖数、摘要、响应限制。支持打开返回、有查询无命中、仅摘要、失败等。直接链接保留查询与来源。可返回列表。 | 现为计数和五列表，明细抽屉含参数、失败信息、数据/行预览，显示范围有限。有复用、成功零行和未执行状态，个别跳过细节分支具备告警专用处理。Case 查询选中主要在组件内。 | 从 Run 与来源页分别打开同一工具步骤。重载后仍能定位。核返回、零行、未执行、跳过、失败、结果未知、复用已有与保留摘要。行/列/页截断有提示，查空只表述查询事实。 |
| 冻结输入和工件目录 | 独立段展示冻结告警与从其得出的证据、原件目录（类型、大小、摘要、时间、来源）。保存记录可打开可读内容。 | 工件抽屉和链接已具备，主要从步骤/图/结论进入。案内该视图没有等效的独立可浏览目录及冻结证据列表。 | 核分页目录中非工具工件仍可达。当前告警/人工任务改动后，同一历史材料仍能读到冻结版本。缺正文、不可用、较大、部分及读取失败分别可见。返回保留目录页与所选步骤。 |

[4173 材料分类与目录](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:289) · [4173 查询明细](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:299) · [8181 查询列表](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:121) · [8181 查询抽屉](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:156) · [8181 工件查看器](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:219) · [冻结材料读取](/Users/lychee/Documents/project/socai2/services/api/investigation_http/external_routes/cases.py:286) · [正式工件字段](/Users/lychee/Documents/project/socai2/docs/integration/run-records-http.md:101)

### Run 4. 调查关系图

| 项目 | 4173 | 8181 现况与差异 | 迁移通过判据 |
| --- | --- | --- | --- |
| 来源选择和视图 | 独立切换 Attack Chain、Attack Path、Alert Graph，展开状态与 Run/数据来源绑定。三栏图保留选中节点、关联范围和来源说明。记录模式对缺图、路径未关联和只读投影分别说明。 | 当前优先选 Result 的 `graph_artifact_id`，回退到同一 Run 的一种 `alert_graph` 工件。展示共享图。缺原型中的三种材料选择、独立披露和状态。 | 同一 Run 可切换正式有供给的三类。无工件、空结果、某来源错误、历史只读和只剩上下文的状态独立处理。切 Run 或 Result 后读取相应图和来源，保持当前视图但清理失效选中项。 |
| 与案内图的联系 | 案件当前基线与历史轮各自保留。在有来源的情况下可以查看同轮关联材料。 | 有到案内拓展入口，目前通过 `explore=1` 打开案内图，未串起指定 Run/图身份。 | 从旧轮进入案内探索时可明确查看/选择同一基线，返回后本轮不变。已保存探索和其所属来源各可追溯。 |

[4173 来源展开身份](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:369) · [4173 关系材料导航](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:387) · [4173 本轮图](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:396) · [8181 本轮图与拓展入口](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:229) · [8181 案内基线](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseGraph.tsx:21)

### Run 5. 报告与响应

| 项目 | 4173 | 8181 现况与差异 | 迁移通过判据 |
| --- | --- | --- | --- |
| Markdown 报告 | 按当前轮展示保存正文、下载、部分交付提示，缺正文时保留执行和材料。 | 已使用 Markdown 及原件查看。当前优先从同一 Run 工件列表取首个报告，再回退 Result 专属工件。多个 Result 时需核该顺序是否会打开不同报告。 | 有两个 Result 时，从各 Result 的报告进入，页面、原件和下载归属一致。部分和失败展示原来的保存工件、限制和停止原因。没有正式报告时无下载假状态。 |
| 响应 | 建议、复核和实际回执分开，使用明确关联键。无法匹配的实际条目独立显示。 | 已有提案状态与复核视图，实际关联由响应子组件解释。右栏和整体顺序待对齐，仍需核没有对应提案的既有回执与直接入口是否可见。 | 只读核既有建议、审核状态、未执行、已保存执行记录和不匹配项，保留目标、范围、原因及时间。变更与执行仅按已有授权和实际回执判定。 |

[4173 响应条目与匹配](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:407) · [4173 报告布局](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:419) · [8181 报告及原件选择](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:238) · [8181 响应提案](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseResponseProposal.tsx:13)

## 直接弹窗、抽屉和就地展开

| 入口 | 4173 设计 / 8181 差异 | 直接通过判据 |
| --- | --- | --- |
| 切换 Case | 原型中央列表卡，按保存案排序，卡显示标题、编号、等级和进入箭头。8181 现有中央弹窗，增加正式搜索、续页、当前态、失败及返回筛选。 | 逐项对齐行高、标题和元信息。搜索及加载新页可回焦。关闭或取消保留当前 Case 及页签，进入目标后读目标资料和真实关联。[4173](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:527) · [8181](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkspaceFrame.tsx:169) |
| 管理资料、结案与重开 | 原型从页头事实进入集中管理，表单含案件名称、严重程度、状态、负责人、分类、标签、期限和结案说明。8181 分管理/页面数据与专门结案重开，生命周期读取正式条件、版本与确认。 | 对齐字段分布和表单底部按钮。空、未分配、清空、冲突、结果未知各保留正式状态。结案说明及限制以保存回执读回，取消不发送请求。[4173 入口](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:497) · [4173 字段](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/workspace-view.js:68) · [8181](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseManagementDialog.tsx:19) · [管理合同](/Users/lychee/Documents/project/socai2/services/api/investigation_http/external_routes/cases.py:295) |
| 添加告警/事件、移动成员 | 原型添加弹窗含已有状态、事件展开和多选，移动为告警选择加目标确认。8181 已具备两种正式候选源和版本，但事件行的自身成员展开及移动结果呈现有差异。 | 两个事件可独立展开，单一成员不重复分配。移出目标列表显示正文与可搜索身份。成功后查同案、目标案和关联事件。部分、冲突和取消保留图/故事入口的原上下文。[4173 添加](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:217) · [4173 移动](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:511) · [8181 添加](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseSelectionDialog.tsx:18) · [8181 移动](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseSelectionDialog.tsx:88) |
| 调查检查与再次调查 | 原型集中呈现意图、当时输入和范围。8181 目前为准备、更新待启动快照再确认启动。与正式异步受理的输入和页面状态不同。 | 确认弹窗标出具体意图、选定范围、当前已受理工作。响应返回后由任务原身份追踪到真实 Run/Result。无变化跳过、冲突、无法确认回执、取消各可查。[4173](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:224) · [8181](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigationOverview.tsx:38) · [异步合同](/Users/lychee/Documents/project/socai2/docs/integration/analysis-submission-http.md) |
| 当前判断的来源与采用 | 原型资料区有按保存来源展开、原件和未决项。8181 有引用抽屉与独立采用比较，仍须接正式服务端预览。 | 只读引用打开确切的 Run、Result、人工修订或原件。预览包含原判断、候选、范围及未覆盖和版本。用户确认一次后按正式回执读回，取消关闭不改变采用版本。[4173](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:415) · [8181 来源](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseReferences.tsx:21) · [8181 采用](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/AdoptResultDialog.tsx:12) · [采用预览合同](/Users/lychee/Documents/project/socai2/services/api/investigation_http/external_routes/cases.py:225) |
| 告警预览、对象证据与活动 | 原型告警和对象证据可在当前页打开右侧详情，活动另有抽屉和执行明细入口。8181 故事用右栏焦点详情并保留原告警与材料回链，来源可进工件查看器，Case 活动仍以内嵌项为主。 | 打开时标题、对象类型、时间、范围及来源相互匹配，错误重试仍针对该条。关闭返回原行、原过滤与原选中，导航只有在用户点击时切换。[4173 证据与活动抽屉](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:467) · [8181 故事焦点详情](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseStory.tsx:324) · [8181 对象证据](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseEvidence.tsx:23) |
| 图选中、探索保存、加入 | 4173 左右图栏及候选和保存/恢复是同基线连续操作。8181 拓展区有候选选择和工作状态，原图、候选和保存回执仍需连贯。 | 逐个看节点/边、候选、运行归属和选区。预览可取消，返回能恢复布局。旧快照重新打开使用其保存基线。加入后的分配结果按实际回执。[4173 图详情](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-graph.js:137) · [4173 拓展](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-exploration.js:37) · [8181 拓展](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseExploration.tsx:21) |
| 人工任务与版本 | 4173 居中任务表单、历史任务详情及完成结果。8181 右抽屉用正式版本，可从 Result 或来源带入内容，支持编辑冲突。 | 新建、编辑、只读旧版、无引用及冲突均能打开与关闭。选择冻结任务修订可回查，编辑不会改动历史修订。[4173](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:209) · [8181](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseTaskDrawer.tsx:20) |
| Run 查询、步骤与工件 | 原型查询和来源可在同工作区直接定位，图源和原件有单独展开。8181 查询/工件为不同抽屉，Case 查询选择和常用工件选择主要为组件状态。 | 锁定 Case、Run、Result 和 Step/Artifact。依次打开多个步骤、刷新、回退，查看器内容不会来自前轮或前项。遮罩、Esc、关闭回焦、内容缺失和截断均可辨识。[4173 查询](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:299) · [8181 查询抽屉](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:156) · [8181 工件抽屉](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:219) |
| 评论附件与案件助手 | 4173 评论/附件为就地操作，案件助手以右侧独立入口带入选中范围。8181 附件支持拖放和二阶段登记，案件助手有抽屉与保存表单。 | 先验已有评论、附件元数据及来源阅读，另核无附件和访问受限。助手的开/关、聚焦来源、所选范围只作已批准的界面验收，提交能力随实际后置范围单独确认。[4173 评论附件](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:436) · [4173 助手](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.js:120) · [8181 附件](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseCommentsAttachments.tsx:48) · [8181 助手抽屉](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseAssistant.tsx:82) |

## 多事件主案例与覆盖

统筹已在 4173 实页打开本轮既有主案例。页头两条独立事件链接与源码结构的两个显式关联一致，两个事件各有当前成员。统筹逐页打开十个默认子页，核了三个 Run 的实页入口与身份切换。固定同一 Run 切过五个主视图，路由上的 Run 保持一致。主案例有 Run 材料。该案例的成员级独立证据和第三事件折叠仍待用相应实例覆盖。两个显式事件均直接显示。样例的同轮多 Result、选定范围结果与特定执行回执另按实际记录核。私密主体绑定、DOM、截图和工程观察保存在本批次统筹目录。工程观察文件为 `prototype-multi-page-review.json`、`prototype-multi-run-review.json` 和 `prototype-multi-alternate-run-check.json`。本轮实页观察覆盖默认展示及指定导航。证据细节、第三事件折叠、各类保存、待复验页面及其它历史状态按各节验收。候选筛选与参考均使用既有记录。

4173 的页头从 `caseIncidents` 取前两项。该函数优先识别同源显式关联，还可能沿当前告警的事件边拼入展示。因此同页可见事件次数和显式关联次数应独立验证。8181 头部以正式 `linked_incidents` 为准，也先显示两条再展开，以 `linked_incidents_truncated` 和总数声明局部范围。须以正式关系、当前成员及冻结输入分别对照。[4173 事件来源边界](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:130) · [4173 页头事件展开](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:412) · [8181 事件导航](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkspaceFrame.tsx:50) · [8181 直显、展开及截断](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkspaceFrame.tsx:102) · [正式 Case 详情](/Users/lychee/Documents/project/socai2/services/api/investigation_http/external_routes/cases.py:120)

| 验收项 | 当前覆盖与通过判据 |
| --- | --- |
| 同案事件、展开与回跳 | 主案例覆盖两条独立链接，将分别验返回同案、事件原 ID、当前链接源条件和相关案身份。第三事件之后的折叠、空集合及截断分别用可取得的既有实态或明确注明的界面替身核。折叠后的每条仍能打开。 |
| 多事件成员去重与边界 | 分别核事件内、案内、独立加入、未在案及已移出的告警。一个告警即使经多条关系命中也只计入一次。跨租户、源环境和他案的同名对象不越界。故事、图和证据从各自正式来源核范围。 |
| 多 Run 与 Result | 主案例可在同一 Case 切三轮。对照每轮身份、实际状态、历史成员和材料。同轮多 Result 若未观察到，正式验收保留该条件。存在时检验跳转链接、不可比较、报告/图工件、同页刷新的选中上下文。 |
| 独立证据与历史材料 | 主案例可核 Run 材料。成员级独立证据、有/无归属对象、只见目录无原件的状态需要其它已存在证据或按合同核形态，待实际正式记录验证。 |
| 8181 现有范围 | 本机故事已在前轮同一 Case 通过验收，该案有一个显式事件和六个成员。单事件展示与既有首轮状态已有相应观察。多事件、多个 Run 与 Result 切换、关系折叠、独立证据各自补实际覆盖。 |

## 逐页迁移顺序与验收交接

凡 4173 的目标功能缺少当前正式 HTTP 支持，进入该页实施前确认通用查询、保存及读取合同或明确待决项。目录、搜索、过滤和统计以完整合法范围为准。只读状态、来源缺供、历史边界与用户已确认的后置内容在页面内保留可辨识状态。正式新生命周期已替代的旧启动动作按新受理、跟踪与读回验收。

1. 案件故事本机整页验收已通过，覆盖和证据见第 2 节。
2. 调查历史目录、原轮深链/返回、关系图G1及案件资料只读页已完成本机独验；历史读取性能未修，固定Run五视图正文及执行明细仍按各节单独迁移核对。
3. 其它子页按统筹排期各自验收。案内关系图和对象证据依赖正确的基线与原件目录。调查概览使用正式异步受理、跟踪及读回。
4. 每页在统一默认视口核首屏、典型浮层及正常业务路径。遇到具体阻断，完成定向修正与复验。表中的异常状态按设计留待相应实际场景核验。证据应包含页与来源、可复现操作、能公开的字段路径、结构性计数和结果，实际业务值留在本机。写动作若在后续阶段开展，补保存与独立读回。仅源码或样式比对记为源码结论。

本文件区分已完成的本机单页独验与其余页面的需求对照、缺口和验收判据，不代表完整Case或整个change完成。[第三步现行安排](/Users/lychee/Documents/project/socai2/openspec/changes/complete-socai2-investigation-chain/case-list-migration-20261126.md:96)
