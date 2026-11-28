# 调查模块迁移前逐页理解与整页验收清单

2026-11-26。以4173为设计基准，结合负责人后续已确认规则核对。17组覆盖原88个F编号；包含完整页面和共用运行视图。这里记录的是源码结构与迁移要求，**实际截图、有效字体、布局尺寸和默认视口完整性仍未验收**。

[总规划与顺序](investigation-test-plan-20261126.md) · [每F项数据、测试与接口](investigation-test-matrix-20261126.md) · [源码盘点原件](../../../docs/operations/evidence/investigation-test-plan-20261126-01/frontend-migration-understanding.json)

本轮补充以既有两个显式事件、三次调查的4173 Case作主参考：[详情页逐项对照](case-detail-4173-8181-comparison-20261126.md)、[HTTP核对](case-detail-http-review-20261126.md)、[平台核对](case-detail-platform-review-20261126.md)。统筹已实际打开10个子页和5个固定Run视图，核多轮身份、管理打开取消及故事复选清除；这不等于8181已迁移或视觉验收。8181登录失效后的页面仍待实页比较。

一个页面只有功能完整、交互一致、数据真实且可读回、视觉对齐四项都有直接证据才算完成。4173演示占位不能当真实能力；已有后续产品决定优先并注明差异。保留Case助手、定向问答、附件字节联调和新增响应执行的后置范围。

## 迁移前核对

1. **确认本页入口、用户目的和退出回链**：用该页 F 编号和实际原型标记首屏、页签、次级入口、侧栏、弹窗及按钮动作。标明原型没有入口、交互演示和正式暂缓项。
2. **确认原型结构与产品现状**：记录参考模板、现行路由和组件、已有外壳边界及已知差异。对尚未从真实 UI 核到的位置和断点保留待核。
3. **追到样式真正归属**：建立页面根类、组件和 CSS 选择器对应。迁移时在实际页面查公共主题、页内样式、旧覆盖和断点的生效顺序，将本页规则的复用或移除归到对应来源。
4. **确认读取、提交和状态来源**：条目逐项对照 88 项的操作、所需数据和近期正式接口。固定主体及原 task、Run、Result/工件、人工版本，不因展示缺值拼补业务字段。
5. **把整页验收范围写入当步计划**：确定正常路径、默认画面、必要空态及典型浮层。按功能、交互、数据和视觉四部分分别保存通过证据，明确暂缓分支和当前实现差异。

## 公共框架与样式来源

### 4173

| 项目 | 来源 |
| --- | --- |
| routing_and_shared_components | [workspace-layout.js:6](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/workspace-layout.js:6) · 4173 全局外壳与案件详情时的紧凑侧栏<br>[workspace-layout.js:19](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/workspace-layout.js:19) · Case 分组左侧导航<br>[workspace-layout.js:22](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/workspace-layout.js:22) · 页头、左侧导航与右侧内容的外层布局<br>[app.js:409](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:409) · 案内十个页面入口<br>[investigation-workspace.js:424](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:424) · 共用 Run 选择器、五个主视图及辅助操作 |
| global_style_sources | [styles.css:1](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:1) · 原型字体、颜色及基础变量<br>[styles.css:5](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:5) · 案件框架、卡片和导航<br>[styles.css:6](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:6) · 表格、预览及弹窗基础样式<br>[styles.css:8](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:8) · 案件框架的响应断点<br>[investigation.css:8](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:8) · 调查内容和默认版面 |
| stylesheet_declaration_order | linked_from：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/index.html<br>line：10<br>role：原型实际 stylesheet 引用<br>stylesheet：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css<br>line：1<br>role：对应样式文件<br>linked_from：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/index.html<br>line：11<br>role：原型实际 stylesheet 引用<br>stylesheet：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/workspace.css<br>line：1<br>role：对应样式文件<br>linked_from：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/index.html<br>line：12<br>role：原型实际 stylesheet 引用<br>stylesheet：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/platform-preview.css<br>line：1<br>role：对应样式文件<br>linked_from：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/index.html<br>line：13<br>role：原型实际 stylesheet 引用<br>stylesheet：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-graph.css<br>line：1<br>role：对应样式文件<br>linked_from：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/index.html<br>line：14<br>role：原型实际 stylesheet 引用<br>stylesheet：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css<br>line：1<br>role：对应样式文件<br>linked_from：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/index.html<br>line：28<br>role：原型实际 stylesheet 引用<br>stylesheet：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/recommendation-view.css<br>line：1<br>role：对应样式文件<br>linked_from：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/index.html<br>line：30<br>role：原型实际 stylesheet 引用<br>stylesheet：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/assessment-view.css<br>line：1<br>role：对应样式文件<br>linked_from：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/index.html<br>line：58<br>role：原型实际 stylesheet 引用<br>stylesheet：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.css<br>line：1<br>role：对应样式文件<br>linked_from：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/index.html<br>line：60<br>role：原型实际 stylesheet 引用<br>stylesheet：path：/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/service-workspace.css<br>line：1<br>role：对应样式文件 |

### 8181

| 项目 | 来源 |
| --- | --- |
| routing_and_shared_components | [router.tsx:35](/Users/lychee/Projects/SpiritHub-web-8181/web/src/app/router.tsx:35) · SpiritHub 路由登记全局调查目录与 Run<br>[router.tsx:42](/Users/lychee/Projects/SpiritHub-web-8181/web/src/app/router.tsx:42) · 案件列表绑定 CaseWorkbenchList，案件详情绑定 CaseWorkbenchDetail<br>[SidebarNavigation.tsx:44](/Users/lychee/Projects/SpiritHub-web-8181/web/src/app/shell/SidebarNavigation.tsx:44) · SpiritHub 平台左侧主导航<br>[CaseWorkbenchDetail.tsx:40](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchDetail.tsx:40) · 案内页签列表<br>[CaseWorkbenchDetail.tsx:66](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchDetail.tsx:66) · 案内横向页签承载<br>[RunWorkspace.tsx:17](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunWorkspace.tsx:17) · 共用五个运行主视图<br>[shared.tsx:61](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-alerts/shared.tsx:61) · 多页共用 SocModal 与 drawer 变体<br>[SubjectPreview.tsx:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/SubjectPreview.tsx:1) · 共享右侧记录预览 |
| global_style_sources | [main.tsx:8](/Users/lychee/Projects/SpiritHub-web-8181/web/src/main.tsx:8) · Web 入口导入 styles.css<br>[styles.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/styles.css:1) · Tailwind、tokens、组件主题及业务主题 CSS 入口<br>[styles.css:31](/Users/lychee/Projects/SpiritHub-web-8181/web/src/styles.css:31) · 平台字体变量<br>[theme.css:33](/Users/lychee/Projects/SpiritHub-web-8181/web/src/components/shadcn/theme.css:33) · 共享字体与主题<br>[soc-workbench.css:11](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/soc-workbench.css:11) · 调查公共工作区样式<br>[DetailWorkspace.css:15](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/DetailWorkspace.css:15) · 详情页签内距、侧栏宽度、吸顶和断点覆盖<br>[table.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/components/shadcn/table.css:1) · 主表及列表密度基础<br>[dialog.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/components/shadcn/dialog.css:1) · 弹窗、面板和遮罩基础 |
| routing_note | 案件页面和调查页面沿实际 router 挂载。实际生效的公共与局部规则须在页面查看，文件存在与加载顺序只作为源码证据。 |

## 逐页清单

## Case 列表与公共页头

在真实案件队列里找到并预览指定案件，打开其资料或进入跨主体运行目录，并在案内页头核当前责任与运行状态。

功能：`F09-01`, `F09-02`, `F09-03`, `F09-08`, `F09-09`, `F09-10`, `F09-11`, `F09-04`, `F09-05`, `F23-04`, `F14-01`。

| 页面范围 | 内容 |
| --- | --- |
| 4173路由 | #/cases<br>#/cases/:caseId/case-info |
| 8181路由 | /cases<br>/cases/:caseId/case-info |
| 进入 | 主导航「案件」进入队列<br>告警或事件的合法关联入口可进入实际案件<br>从案内页签回到同案公共页头 |
| 离开/返回 | 关闭预览回到原列表位置<br>点标题或预览中的打开入口进入案件资料<br>运行入口切至全局目录<br>案内页头返回案件或打开已关联事件 |
| 主区域 | 列表标题和操作区<br>四项指标及说明<br>筛选工具栏和案件表<br>案内公共页头、进度条和页签 |
| 页签/次级入口 | 左侧先列案件资料与案件故事，后续分组标题为 AI 调查、案件材料、协作与跟进<br>列选择、日期范围和指标说明<br>导出与刷新<br>查看调查运行<br>案件管理设置占位 |
| 侧栏/弹窗 | 列表案件预览<br>4173 案内左侧 Case 导航<br>日期、筛选和列设置<br>已有新建或管理表单<br>结案提示及确认 |
| 关键状态 | 列表加载、空、失败、分页和无筛选命中<br>已选指标、排序、当前预览<br>未分配、优先级缺供<br>无关联或多个显式关联事件<br>task 已受理可无 Run、活跃、失败或待核<br>结案门禁及未完任务 |

**正常操作流程**

1. 先读四项总体指标，再按指标、搜索、日期和业务条件定位案件
2. 按列、排序、页码或继续读取调整显示，按当前条件导出
3. 预览后核同一案件再进入资料
4. 获准创建时选择实际告警或事件，沿分配和首轮任务读回
5. 案内查看管理信息与进度，带现行门禁管理、结案或重开

**当前差异与样式归属**

| 对照项 | 具体内容 |
| --- | --- |
| 已定位源码差异 | 4173 案内是分组左侧导航，8181 是横向页签。外层 SpiritHub 导航属于产品外壳<br>4173 案件名称列预览图标位于标题前，现 8181 标题后是预览按钮且 ID 另起一行<br>4173 列表有直达运行按钮，8181 有独立运行路由，当前案件列表标题区未见该按钮<br>原型创建按钮是占位且自动刷新重绘本地集合，8181 有新建与真实请求。逐项继续按确认的 F 规范核对 |
| 4173组件/布局 | [app.js:366](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:366) · 队列工具栏、日期和列设置<br>[app.js:376](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:376) · 案件列及预览入口<br>[app.js:403](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:403) · 全局运行按钮、指标、设置占位<br>[app.js:412](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:412) · 公共页头、关联事件、切案和执行提示<br>[workspace-layout.js:19](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/workspace-layout.js:19) · 内部左侧导航和页面内容框架 |
| 4173样式 | [styles.css:5](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:5) · .case-body、.case-nav 与标题卡片的分栏和间距<br>[styles.css:6](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:6) · .drawer、.modal 和原型通用浮层<br>[styles.css:14](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:14) · .case-queue-metrics、.case-list-metric、.cases-queue 表格及工具栏<br>[styles.css:15](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:15) · 队列指标及工具栏断点 |
| 8181组件/布局 | [CaseWorkbenchList.tsx:63](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchList.tsx:63) · 列表、新建、导出与指标<br>[CaseWorkbenchList.tsx:67](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchList.tsx:67) · 共享筛选、刷新与选列<br>[CaseWorkbenchList.tsx:73](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchList.tsx:73) · 标题及后置预览图标<br>[CaseWorkbenchList.tsx:93](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchList.tsx:93) · 同案 SubjectPreview<br>[CaseWorkbenchDetail.tsx:62](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchDetail.tsx:62) · 案内公共页头、状态及横向导航<br>[CaseSelectionDialog.tsx:28](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseSelectionDialog.tsx:28) · 实际案件新建或关联表单 |
| 8181样式 | [case-workbench.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-workbench.css:1) · .soc-case-metrics、.soc-case-table、.soc-case-preview<br>[DetailWorkspace.css:15](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/DetailWorkspace.css:15) · 粘性的 .soc-workbench-tabs 与详情布局<br>[SubjectPreview.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/SubjectPreview.css:1) · 共享预览框、右侧位置及内部滚动<br>[ListWorkspace.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/shared/ui/ListWorkspace.css:1) · 列表筛选、工具区和列设置共用样式<br>[table.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/components/shadcn/table.css:1) · 共享表格列、排序图标及内容承载 |

**四项整页验收**

| 维度 | 必须核对 |
| --- | --- |
| 功能 | 核 F09 四项指标、筛选分页、选列排序、日期导出、预览和公共页头<br>核新建分配和首轮任务落点、管理门禁、运行入口及任务跨页状态 |
| 交互 | 从队列筛选后打开预览、进入同一案件并返回，保持筛选、焦点和位置<br>分别核标题、预览图标、管理按钮和筛选面板能独立工作<br>检查切换指标、列、页和刷新不改变未操作条件 |
| 数据 | 总体指标与列表过滤各用自身范围，潜在重复条件保留原字段<br>导出据全部命中和选列依据验证<br>页头、关联事件、实际分配和 task/Run 随案件身份绑定 |
| 视觉：布局/表图卡 | 同屏确认标题工具栏、四项指标、筛选行、表格列和案内导航顺序，比较 4173 左目录与 8181 当前横页签的实际完整性。 |
| 视觉：按钮/图标 | 核预览图标相对于案件标题、导出/创建图标相对于按钮文字、刷新和切案图标在页头的实际位置。任何刻意差异需有功能依据。 |
| 视觉：字体/间距 | 核页头与指标数字层级、标题和 ID 字号、表头和数据行行高、按钮与相邻控件间距。按实际有效主题记录字体族及 fallback。 |
| 视觉：侧栏/弹窗 | 核案件预览从右侧打开，顶部关闭/切换、中间内容和底部进入入口完整。并排看日期、选列、关联选择和结案表单的宽度、滚动和焦点。 |
| 视觉：默认视口 | 默认位置可看到列表身份、操作、筛选和首屏表头。窄窗口若横向滚动，仍能触达表头和操作。公共页头与进度提示不覆盖案内导航。 |

当前验收状态：本组实现已应用8181，10项直接用例和类型检查通过；统筹在1280×720现有平台主题下核真实空列表、12默认/18可选列、日期/筛选/指标/排序、创建打开取消和Case运行目录空读取。完整预览与4组左导航的有值布局仅有隔离浏览器替身证据；正式上下文没有Case，真实预览、页头关联和保存闭环仍待验。原型设置入口保持占位；原型通用表格的复选列没有Case批量动作，本步未新增无业务动作的勾选逻辑。Case类别、检测源、资产总量及未支持筛选仍为明确缺口。默认平台主题未变，不声称其它主题/断点已验。[本步独审](../../../docs/operations/evidence/case-list-migration-20261126-01/coordinator-review.json)

## 案件资料

理解当前案件背景、范围和当前采用判断，并能查看判断依据、未决事实与管理资料。

功能：`F09-06`, `F10-01`, `F11-01`, `F12-01`, `F12-02`, `F11-02`, `F09-07`, `F11-03`。

| 页面范围 | 内容 |
| --- | --- |
| 4173路由 | #/cases/:caseId/case-info |
| 8181路由 | /cases/:caseId/case-info |
| 进入 | 列表或摘要进入案件默认「案件资料」<br>案内目录直接进入资料<br>从原判断来源返回同案资料 |
| 离开/返回 | 范围卡进入成员、对象证据或历史<br>来源跳转打开具体 Run、Result、工件或人工修订<br>管理编辑保存后回读同案资料<br>返回案件队列 |
| 主区域 | 案件说明及范围概况<br>当前案件判断和原依据<br>未决项、ATT&CK 阶段、管理资料 |
| 页签/次级入口 | 案件资料为 Case 默认页签<br>成员、对象证据、历史范围卡<br>查看来源和当轮材料 |
| 侧栏/弹窗 | 资料右侧管理信息或范围辅助区<br>来源阅读抽屉<br>分类期限编辑<br>候选结果比较及采用 |
| 关键状态 | 有采用、尚无采用和系统说明<br>原来源可读、仅摘要、受限或未记录<br>依据 current、stale、unverified<br>覆盖完整和未覆盖成员<br>分类期限为空、版本冲突或保存完成 |

**正常操作流程**

1. 读案件说明、范围和管理资料
2. 读当前采用判断及采用来源，比较原适用范围与当前覆盖
3. 看未决项和依据后回查固定来源
4. 在适用时编辑分类期限，或比较并明确采用另一已存结果

**当前差异与样式归属**

| 对照项 | 具体内容 |
| --- | --- |
| 已定位源码差异 | 4173 的范围计数在 .case-summary-metrics 卡片里，8181 在 .soc-case-scope 用分栏事实面板<br>4173 可查导入采用来源，8181 增加独立候选比较和采用弹窗，属于需正式接线验收的 F11-03<br>范围覆盖、当前判断、状态与管理卡的视觉层级需要整体对照 |
| 4173组件/布局 | [app.js:415](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:415) · 保存采用来源、依据及未决项<br>[app.js:420](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:420) · 当前案件判断和覆盖<br>[app.js:431](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:431) · 资料首页、范围与辅助资料<br>[investigation-workspace.js:219](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:219) · 按成员战术标签汇总<br>[assessment-view.js:18](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/assessment-view.js:18) · Result 问题与依据结构 |
| 4173样式 | [styles.css:5](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:5) · .case-summary-metrics、.case-overview-grid、.case-content<br>[assessment-view.css:1](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/assessment-view.css:1) · 判断、来源、覆盖和未决卡片<br>[investigation.css:8](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:8) · 统一调查卡片、元信息和依据阅读样式 |
| 8181组件/布局 | [CaseWorkbenchDetail.tsx:68](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchDetail.tsx:68) · 说明、范围与阶段卡<br>[CaseFields.tsx:45](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseFields.tsx:45) · CaseJudgment 与来源<br>[CaseReferences.tsx:21](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseReferences.tsx:21) · 精确引用抽屉<br>[CaseManagementDialog.tsx:45](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseManagementDialog.tsx:45) · 资料编辑<br>[AdoptResultDialog.tsx:28](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/AdoptResultDialog.tsx:28) · 产品采用表单 |
| 8181样式 | [CaseDetail.css:4](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseDetail.css:4) · .soc-case-scope 格线、管理区及本地覆盖<br>[case-workbench.css:6](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-workbench.css:6) · .soc-case-judgment、范围和管理卡<br>[DetailWorkspace.css:17](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/DetailWorkspace.css:17) · 两列内容、面板内距和断点<br>[dialog.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/components/shadcn/dialog.css:1) · 采用和资料弹窗容器 |

**四项整页验收**

| 维度 | 必须核对 |
| --- | --- |
| 功能 | 核默认案件资料、说明及范围、当前采用、未决项、阶段卡和管理资料。覆盖明确采用与采用前比较的入口。 |
| 交互 | 从判断跳到固定来源并返回，从范围卡切页。检查取消编辑和采用前确认保持案件状态。 |
| 数据 | 以同案已采用记录、其源 Result 或人工版本及原范围为准。当前成员覆盖、阶段和业务元数据分别对照。 |
| 视觉：布局/表图卡 | 首屏按原型核范围卡、当前判断、说明和管理区层级，阶段条与信息卡保持清楚区分。 |
| 视觉：按钮/图标 | 核编辑铅笔紧邻管理信息动作，采用和来源入口带清楚文字，卡片点击与内嵌链接不相互抢事件。 |
| 视觉：字体/间距 | 比对数字、状态、标签和较长判断正文的视觉层级。核正文、证据行及卡片留白，小字号也需可读。 |
| 视觉：侧栏/弹窗 | 来源抽屉与分类期限、采用弹窗在不同操作下分别打开，固定标题、内容可滚和底部确认区正确归属。 |
| 视觉：默认视口 | 默认页可见案件身份、判断和范围入口。长判断及卡片内容可连续滚动，右侧管理区不压缩正文。 |

当前验收状态：未开始整页迁移与真实视觉验收。

## 案件故事

按时间理解告警事实和调查、人工认识如何演变，并从故事回到相应原记录。

功能：`F20-01`, `F20-02`, `F20-03`, `F20-04`, `F20-05`。

| 页面范围 | 内容 |
| --- | --- |
| 4173路由 | #/cases/:caseId/story |
| 8181路由 | /cases/:caseId/story |
| 进入 | 案件页签「案件故事」<br>调查概览打开案件故事<br>案内判断或资料回到故事 |
| 离开/返回 | 从条目回告警详情、固定 Run、Result 或人工修订<br>跳同案调查历史<br>关闭告警预览保留故事选中 |
| 主区域 | 故事统计和活动范围<br>搜索和等级条<br>事实与工作时间线及未记录时间区<br>右侧焦点告警的活动详情 |
| 页签/次级入口 | 案件故事主视图<br>调查历史<br>告警与原记录入口<br>提问预填保留暂缓 |
| 侧栏/弹窗 | 右栏焦点告警、与本案其他告警的共同对象、包含此告警的调查<br>告警原记录跳转；提问入口按已确认范围暂缓 |
| 关键状态 | 全部、筛选无匹配、日期未知<br>单选、多选、清除与焦点离开<br>运行进行中和已有保存结果<br>原来源无记录 |

**正常操作流程**

1. 读时间线的事实和工作记录
2. 按搜索和等级缩小显示范围
3. 单击切换焦点告警，核右栏共同对象和包含此告警的调查；复选集合单独维护，不能改变焦点详情语义
4. 打开同轮或人工原记录，按原入口返回

**当前差异与样式归属**

| 对照项 | 具体内容 |
| --- | --- |
| 已定位源码差异 | 4173 使用故事专用 .cs-* 时间线与聚焦右栏，8181 使用共用 VerticalTimeline 与 StorySelection<br>4173 单击聚焦决定右栏，复选集合用于提问范围；8181 StorySelection 按复选集合取交集，属于需纠正的旧逻辑<br>4173 仅有搜索、单值等级和重置，没有8181旧类型标签与多值添加筛选；等级命中告警还决定关联调查/人工记录是否显示，与E65目前保留全部上下文的语义不同<br>窄屏右栏折叠/显示策略在 4173 的断点中有专用处理，8181 从共享布局继承 |
| 4173组件/布局 | [case-assistant.js:127](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.js:127) · 故事筛选和时间线处理<br>[case-assistant.js:132](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.js:132) · 告警条目操作与来源<br>[case-assistant.js:140](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.js:140) · 左右分栏、右栏选择和清除 |
| 4173样式 | [case-assistant.css:1](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.css:1) · .cs-layout、.cs-timeline、.cs-details 的故事布局<br>[case-assistant.css:74](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.css:74) · 故事和助手的窄屏规则<br>[investigation.css:8](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:8) · 共用页标题及调查卡片 |
| 8181组件/布局 | [CaseReadPanels.tsx:27](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseReadPanels.tsx:27) · CaseStory<br>[CaseReadPanels.tsx:38](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseReadPanels.tsx:38) · 过滤和共享时间线<br>[CaseReadPanels.tsx:44](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseReadPanels.tsx:44) · StorySelection 查询及右栏<br>[VerticalTimeline.tsx:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/VerticalTimeline.tsx:1) · 统一时间线绘制 |
| 8181样式 | [DetailWorkspace.css:17](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/DetailWorkspace.css:17) · 双列工作区及单列断点<br>[soc-workbench.css:15](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/soc-workbench.css:15) · 时间线、事实行和内容面板<br>[ListWorkspace.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/shared/ui/ListWorkspace.css:1) · 搜索筛选头及操作间距<br>[SubjectPreview.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/SubjectPreview.css:1) · 告警预览共用布局 |

**四项整页验收**

| 维度 | 必须核对 |
| --- | --- |
| 功能 | 核事实、Run、已保存结果及人工记录的时间线和落点。已明确暂缓的提问分支只保留入口边界。 |
| 交互 | 搜索、单值等级、单击聚焦、复选和清除分别检查；右栏依焦点告警，不能因多选自动改成集合交集。跳出原记录后返回保持同案及合理选择状态。 |
| 数据 | 事件时间、运行时间和人工记录时间分别回查。右栏依当前焦点告警及本案成员/固定轮次范围；复选集合与焦点分开，精确绑定历史修订。 |
| 视觉：布局/表图卡 | 时间线左栏、搜索及单值等级条、右侧焦点活动信息及无时间分组都纳入整页对照。 |
| 视觉：按钮/图标 | 核历史入口、搜索/清除与告警条目的点击区域，复选框和预览入口的行内位置按示意源对照。 |
| 视觉：字体/间距 | 核时钟轴标签、告警标题和次级来源的权重。卡片之间间距、右栏标题与焦点活动读序应清晰。 |
| 视觉：侧栏/弹窗 | 打开告警预览或原记录返回时，遮挡、关闭及键盘焦点要回到原条目。 |
| 视觉：默认视口 | 默认能同时理解故事流和右侧活动详情。窄屏用可触达的替代布局呈现所需选中信息，记录原型的断点行为。 |

当前验收状态：本机整页迁移及统筹独立验收通过。采用专用 CaseStory.tsx / CaseStory.css，原共用 Story/StorySelection 已移除，活动页保持。上表源码差异是迁移前基线；本轮实际功能、数据及布局证据见[单页验收](../../../docs/operations/evidence/case-story-migration-20261126-01/README.md)。历史目标页的旧布局与目录读取错误仍为下一步，不计入本页已修。

本页范围说明：F20-01：普通告警/Run/人工修订时间线纳入；助手问答保存记录暂缓。；F20-04：整项后置。

## 调查概览

了解当前正在做什么、哪些范围尚待启动，按已有结果或人工待办进入下一步。

功能：`F14-02`, `F14-03`, `F14-04`, `F16-01`, `F22-01`, `F14-05`。

| 页面范围 | 内容 |
| --- | --- |
| 4173路由 | #/cases/:caseId/overview |
| 8181路由 | /cases/:caseId/overview |
| 进入 | 案内「调查概览」<br>查看当前进度后返回概览<br>运行详情和资料中的同案回链 |
| 离开/返回 | 打开现有 Run 进度或结果<br>进入全部调查历史、故事或人工任务<br>确认后的准备或启动结果仍在同案上下文回查 |
| 主区域 | 当前工作和待启区<br>成员和材料范围<br>已有结果及来源<br>人工待办和下一步 |
| 页签/次级入口 | 调查概览为案内主视图<br>运行进度、完整历史、案件故事及人工任务 |
| 侧栏/弹窗 | 右侧待确认事项及人工摘要<br>准备或明确启动的确认和状态读取 |
| 关键状态 | 无当前工作、受理未出 Run、运行中、待启动、失败和已收尾未知<br>查无变化<br>有结果或仅保存材料<br>无人工待办及已完成任务 |

**正常操作流程**

1. 读同案当前工作和待启动范围
2. 识别已有结论、变化及限制
3. 按需进入固定运行或人工任务
4. 明确检查或启动时按对应受理身份读回，区分有变化和无变化

**当前差异与样式归属**

| 对照项 | 具体内容 |
| --- | --- |
| 已定位源码差异 | 4173 当前工作和结果以导入 Run 卡为主，早期本地模拟入口与真实任务属不同阶段。现 8181 有准备和按 Run 启动弹窗，仍需核正式 check 与 task 读取<br>原型专用结果和待确认两栏与产品共享面板样式需在同案进行整页对照 |
| 4173组件/布局 | [investigation-workspace.js:321](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:321) · 调查概览及结果卡<br>[investigation-workspace.js:330](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:330) · 范围、待更新、历史和侧栏<br>[case-workflow.js:150](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:150) · 当前工作<br>[case-workflow.js:160](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:160) · 人工待办 |
| 4173样式 | [investigation.css:3](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:3) · .iv-case-home、.iv-case-overview-grid 和范围卡布局<br>[investigation.css:117](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:117) · .cw-current-work、进度块和状态样式<br>[investigation.css:139](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:139) · 已有结果卡 |
| 8181组件/布局 | [CaseInvestigationOverview.tsx:17](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigationOverview.tsx:17) · 准备、当前工作和历史读取<br>[CaseInvestigationOverview.tsx:38](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigationOverview.tsx:38) · 实际启动对话框<br>[CaseOverviewPanels.tsx:14](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseOverviewPanels.tsx:14) · 待办及结果卡<br>[CaseRunStatus.tsx:15](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseRunStatus.tsx:15) · 进度与范围读取 |
| 8181样式 | [DetailWorkspace.css:17](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/DetailWorkspace.css:17) · 概览共用两列面板<br>[case-workbench.css:20](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-workbench.css:20) · 案件调查承载布局<br>[soc-workbench.css:50](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/soc-workbench.css:50) · 内容块、状态与间距<br>[dialog.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/components/shadcn/dialog.css:1) · 启动确认弹窗 |

**四项整页验收**

| 维度 | 必须核对 |
| --- | --- |
| 功能 | 按 F14-02/03/04/05、F16-01、F22-01 核当前、待启动、已有结果、人工待办和三个去向。提交动作按正式生命周期查回。 |
| 交互 | 在同屏区分看进度、查看历史、阅读结果和明确提交。打开/取消准备或启动后保持案内上下文。 |
| 数据 | 按独立 task 的受理与尝试追固定 Run，已完成或收尾未知记录保留原历史。结果卡与采用判断、待办数各用自身来源。 |
| 视觉：布局/表图卡 | 核当前工作、待启动提示、左侧结果卡和右侧人工摘要的层级，范围入口与结果阅读分开。 |
| 视觉：按钮/图标 | 核查看进度、打开结果、历史、添加任务和启动按钮的相邻位置与主次强度，展开错误区时不遮挡模型/工件入口。 |
| 视觉：字体/间距 | 对照工作状态、标题、时间和摘要间距。载入/失败提示在本区显示，不使其余卡片跳位。 |
| 视觉：侧栏/弹窗 | 启动确认需能看范围、时间和状态提示，默认收起，按钮和关闭控件可见且不被长表单遮挡。 |
| 视觉：默认视口 | 默认首屏能辨认当前工作、待启动和至少一个已有结果/明确空态。相关人工摘要及历史入口可正常滚到。 |

当前验收状态：未开始整页迁移与真实视觉验收。

## 调查历史

选择本案的确切轮次及比较关系，读当时范围、状态、交付、耗时和来源。

功能：`F14-06`, `F15-01`, `F16-02`, `F12-03`。

| 页面范围 | 内容 |
| --- | --- |
| 4173路由 | #/cases/:caseId/investigations<br>#/cases/:caseId/investigations?run=:runId&view=:view |
| 8181路由 | /cases/:caseId/investigations<br>/cases/:caseId/investigations?run=:runId&view=:view |
| 进入 | 案内「调查历史」<br>从概览查看全部历史<br>故事条目、资料采用来源或具体 Run 深链 |
| 离开/返回 | 选择某轮进入同一轮共用五视图<br>回调查概览或案件故事<br>打开被比较旧结果、冻结输入或人工版本 |
| 主区域 | 历史列表或结果卡<br>轮次身份及状态<br>内嵌运行详情<br>比较和来源入口 |
| 页签/次级入口 | 调查历史是案内页签，所选 Run 保留共用主视图<br>固定 Run 读取、历史比较和冻结材料 |
| 侧栏/弹窗 | 8181 案内历史目录与详情并列<br>工件或人工版本可开来源抽屉<br>本页无此类入口 |
| 关键状态 | 首次、更新、已保存回答<br>执行和交付各态、无结果和未知投入<br>无历史、指定 Run 找不到或无法访问<br>后续范围变化 |

**正常操作流程**

1. 先阅轮次列表的类型、目标、时间和状态
2. 选择一轮并从当前阅读视图打开
3. 读取其停止、投入和保存结果
4. 沿明确比较或冻结引用回查看当时范围

**当前差异与样式归属**

| 对照项 | 具体内容 |
| --- | --- |
| 已定位源码差异 | 4173 历史列表用记录卡进共用运行工作台，历史带 run 时外层可能标在概览。8181 在调查历史页内让目录与所选运行并排<br>页内导航既有案内也有运行层，验收需对照默认高亮和回退位置 |
| 4173组件/布局 | [app.js:331](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:331) · 案内历史与选中 Run 的路由分支<br>[investigation-workspace.js:197](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:197) · 历史记录卡<br>[investigation-workspace.js:424](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:424) · 所选 Run 标题及轮次选择器<br>[investigation-workspace.js:428](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:428) · 切轮保留视图 |
| 4173样式 | [investigation.css:10](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:10) · 共用五视图页签、溢出及菜单<br>[investigation.css:13](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:13) · .iv-run-link 历史记录卡和状态<br>[styles.css:5](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:5) · 案内框架与左目录 |
| 8181组件/布局 | [CaseInvestigations.tsx:14](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigations.tsx:14) · 案内历史与所选结果<br>[CaseInvestigations.tsx:32](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigations.tsx:32) · 历史目录和内嵌详情<br>[RunWorkspace.tsx:18](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunWorkspace.tsx:18) · 共享运行工作台<br>[RunViews.tsx:47](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:47) · 精确比较结果回链 |
| 8181样式 | [case-workbench.css:20](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-workbench.css:20) · .soc-case-history 目录与详情分栏<br>[investigations.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/investigations.css:1) · 历史运行和内容视图样式<br>[InvestigationDetail.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationDetail.css:1) · 状态区与运行页签 |

**四项整页验收**

| 维度 | 必须核对 |
| --- | --- |
| 功能 | 核历史分类、可选轮、切轮保留视图、指标、固定输入和明确比较。 |
| 交互 | 从案内记录卡或深链打开指定轮。从同一视图切换另一轮并返回历史，查找失败时可退出。 |
| 数据 | Run、Result、comparison_result_id、原输入及人工修订随原轮次保持。未知消耗与失败不补统计。 |
| 视觉：布局/表图卡 | 比较 4173 历史记录卡与 8181 左目录和右运行详情，状态行、标题和选择器紧随当前层级。 |
| 视觉：按钮/图标 | 核查看结果/过程的动作位置、轮次选择器开合和回到历史的可达性。上下两级导航的选中状态独立。 |
| 视觉：字体/间距 | 核轮次列表的主次色、任务标题省略、时间和交付信息间距，以及状态文字在窄列内的换行。 |
| 视觉：侧栏/弹窗 | 从历史打开原输入、报告或任务修订时，抽屉/转页来源绑定同轮，返回后仍能定位原记录。 |
| 视觉：默认视口 | 默认能看当前 Run 识别和主视图入口。目录过长可在自身区域滚动，主内容不因双导航被截断。 |

当前验收状态：未开始整页迁移与真实视觉验收。

## 成员告警

确认正式案件范围，对明确选中的告警查看来源、管理、添加或移动。

功能：`F13-04`, `F13-05`, `F13-06`, `F13-07`, `F13-08`。

| 页面范围 | 内容 |
| --- | --- |
| 4173路由 | #/cases/:caseId/alerts |
| 8181路由 | /cases/:caseId/alerts |
| 进入 | 案内「成员告警」<br>案件资料成员卡或概览范围入口<br>完成已确认关联后读回成员页 |
| 离开/返回 | 开原告警或其材料<br>回案件资料与待更新提示<br>移动后分别回查源案和目标案 |
| 主区域 | 成员标题及操作栏<br>成员告警表格、勾选和分页<br>关联事件与当前范围提示 |
| 页签/次级入口 | 成员告警为案内主视图<br>告警详情、材料、管理所选、添加、移动 |
| 侧栏/弹窗 | 同成员告警预览<br>添加告警或事件的候选选择<br>移动的目标案及确认<br>管理已选告警表单 |
| 关键状态 | 有成员、空、部分载入、读失败<br>未选、单选或多选<br>目标不合规与确认成功<br>范围变化但旧轮已冻结 |

**正常操作流程**

1. 读同案成员、显式事件和分页范围
2. 选择告警查看同 ID 的详情或材料
3. 对所选告警明确管理
4. 按需搜索选择告警/事件并确认加入，或确认移动及双案读回
5. 回概览查待更新与旧轮范围

**当前差异与样式归属**

| 对照项 | 具体内容 |
| --- | --- |
| 已定位源码差异 | 4173 案件成员沿原型通用告警表，移动和添加在成员标题动作区。8181 采用共享 DataTable、持续分页和选择后的管理/移动表单<br>成员列及操作入口顺序需同屏核对 |
| 4173组件/布局 | [app.js:201](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:201) · 共用列表和分页<br>[app.js:411](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:411) · 成员标题、移动及添加入口<br>[app.js:667](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:667) · 移动所选<br>[case-workflow.js:26](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:26) · 成员与事件正式加入的原型流程 |
| 4173样式 | [styles.css:81](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:81) · .case-member-actions 与成员标题按钮排列<br>[styles.css:6](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:6) · 列表及通用浮层<br>[investigation.css:88](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:88) · 成员选择及协作表单样式 |
| 8181组件/布局 | [CaseWorkbenchDetail.tsx:85](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchDetail.tsx:85) · CaseMembers<br>[CaseWorkbenchDetail.tsx:97](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchDetail.tsx:97) · 成员 DataTable 与操作位<br>[CaseWorkbenchDetail.tsx:113](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchDetail.tsx:113) · 管理所选<br>[CaseSelectionDialog.tsx:28](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseSelectionDialog.tsx:28) · 加成员及双案移动表单 |
| 8181样式 | [case-workbench.css:12](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-workbench.css:12) · .soc-case-picker<br>[table.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/components/shadcn/table.css:1) · 成员列宽、选择及操作空间<br>[SubjectPreview.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/SubjectPreview.css:1) · 成员告警预览样式<br>[dialog.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/components/shadcn/dialog.css:1) · 选择及管理弹窗 |

**四项整页验收**

| 维度 | 必须核对 |
| --- | --- |
| 功能 | 核成员及显式事件读取、添加、移动、管理所选和加入后的待更新。 |
| 交互 | 检查选择框、标题、预览及行操作各自命中。切页选择范围清楚，取消加入或移动保持原成员。 |
| 数据 | 核候选资格、事件成员并集去重、双案版本及真实回执，旧 Run 沿冻结范围读取。 |
| 视觉：布局/表图卡 | 对照标题动作条和原成员表的列顺序、选择区、原告警链接与分页。 |
| 视觉：按钮/图标 | 核加成员、移动、管理和预览图标在标题行、批量区与成员名的相对位置。 |
| 视觉：字体/间距 | 核告警标题、严重度、状态、时间和来源彼此对齐。行高与选框、密度和间距同页面统一。 |
| 视觉：侧栏/弹窗 | 添加和移动表单区分候选、目标、范围确认和结果。打开/关闭侧栏或弹窗时成员列表保持定位。 |
| 视觉：默认视口 | 默认可见表头和关键操作。横向表格保证能滚到行操作，选择与分页区可达。 |

当前验收状态：未开始整页迁移与真实视觉验收。

## 案件关系图与关联探索

读当前案件的可核关系，从对象或告警探索一层线索，保留已保存探索与正式成员的边界。

功能：`F19-01`, `F19-02`, `F25-01`, `F25-02`, `F25-03`, `F25-04`, `F26-01`。

| 页面范围 | 内容 |
| --- | --- |
| 4173路由 | #/cases/:caseId/attack |
| 8181路由 | /cases/:caseId/attack |
| 进入 | 案内「案件关系图」<br>历史关系图显式转入当前案探索<br>已保存探索链接回原基图 |
| 离开/返回 | 开节点所引告警、材料或历史运行<br>返回基图或恢复已保存探索<br>确认加入后在成员及概览读回 |
| 主区域 | 来源和范围头部<br>三栏中的告警列表、画布、详情<br>图层、布局、选择、高亮与缩放<br>关联线索、预览和展开 |
| 页签/次级入口 | 子面板「对象详情」「关联线索」<br>当前底图、成员关系或结果图的选择<br>查看原运行与材料<br>保存、撤销或重置探索<br>节点提问为暂缓分支 |
| 侧栏/弹窗 | 告警与检测列表<br>节点/边详情和关联线索侧栏<br>候选正式加入确认<br>来源材料读取面板 |
| 关键状态 | 合格图、成员关系或无保存图<br>过期底图与已保存探索<br>空候选、预览、已展开、已撤销、已保存<br>无法扩展的战术节点<br>正式成员确认结果 |

**正常操作流程**

1. 识别当前底图及来源，必要时选择合格结果或成员关系
2. 切类、布局、缩放和分组，选节点/边查看来源
3. 预览推荐线索、展开及撤销
4. 明确保存/恢复探索，或单独确认加入到本案

**当前差异与样式归属**

| 对照项 | 具体内容 |
| --- | --- |
| 已定位源码差异 | 4173 优先合格历史结果作为当前底图。8181 当前默认 members，用户可手选结果图<br>4173 .ug-* 三栏和圆形节点当前由 8181 的共享 RelationGraph 矩形节点和布局承担<br>8181 另有成员进程树视图，只列接线差别，功能范围按 F19 和 F25 确认 |
| 4173组件/布局 | [investigation-workspace.js:332](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:332) · 当前底图资格、原探索及回源<br>[investigation-graph.js:156](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-graph.js:156) · 圆形节点及高亮模板<br>[investigation-graph.js:160](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-graph.js:160) · 三栏和默认视口控件<br>[case-exploration.js:37](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-exploration.js:37) · 探索动作栏<br>[case-exploration.js:39](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-exploration.js:39) · 详情与关联线索切换 |
| 4173样式 | [investigation-graph.css:26](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-graph.css:26) · .ug-main、.ug-toolbar 和画布<br>[investigation-graph.css:52](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-graph.css:52) · .ug-node、圆形节点与选择<br>[investigation-graph.css:113](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-graph.css:113) · .cx-toolbar、.cx-side-tabs 和候选线索<br>[investigation.css:3](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:3) · 案件视图外层 |
| 8181组件/布局 | [CaseGraph.tsx:25](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseGraph.tsx:25) · 成员关系默认与可选结果底图<br>[CaseGraph.tsx:34](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseGraph.tsx:34) · 基图开关和探索入口<br>[CaseRelationGraph.tsx:9](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseRelationGraph.tsx:9) · 同案图来源补充<br>[CaseExploration.tsx:21](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseExploration.tsx:21) · 探索工作台<br>[RelationGraph.tsx:95](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/RelationGraph.tsx:95) · 共享图视口和矩形节点 |
| 8181样式 | [RelationGraph.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/RelationGraph.css:1) · 共享 .soc-graph-* 画布、节点及边<br>[case-workbench.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-workbench.css:1) · 案件范围与面板通用层<br>[DetailWorkspace.css:15](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/DetailWorkspace.css:15) · 案内页签和面板容器 |

**四项整页验收**

| 维度 | 必须核对 |
| --- | --- |
| 功能 | 核当前底图选择、筛选/视角、精确源、推荐线索、预览扩展、撤销重置、保存恢复和明确加入。 |
| 交互 | 从默认状态选告警、对象和边，再切类型与视角。探索后保存、重进及撤销时保留原基图和背景案，加入前必须显式确认。 |
| 数据 | 当前与历史图按确切 Result/工件身份，各边有来源。候选、探索快照和正式成员关系各自查回。 |
| 视觉：布局/表图卡 | 同屏核告警栏、画布和详情/线索栏的面积、层级、图例、圆形节点及连线原型样式。比较现存矩形节点与三栏差异。 |
| 视觉：按钮/图标 | 核布局、分组、图层、缩放/重置、探索和加入按钮在图工具栏及候选侧栏的位置。节点类型图标与图例一一对应。 |
| 视觉：字体/间距 | 核节点标题、边标签、筛选文本和侧栏字体密度。长标签缩略后仍可读，画布与左右栏的间隔按参考。 |
| 视觉：侧栏/弹窗 | 点击来源、候选和加入确认时核右栏与弹窗互不遮挡。关闭后保持原选择和视角。 |
| 视觉：默认视口 | 评估默认画布是否完整显示当前节点、标签和图例。核首次进入、切底图和重置视角的完整性，以及工具栏不被默认视口裁掉。 |

当前验收状态：未开始整页迁移与真实视觉验收。

本页范围说明：F26-01：整项后置。

## 对象与证据

从对象或所选调查找到原告警、证据、威胁、查询及已保存工件。

功能：`F21-01`, `F21-02`, `F21-03`, `F21-04`。

| 页面范围 | 内容 |
| --- | --- |
| 4173路由 | #/cases/:caseId/evidence |
| 8181路由 | /cases/:caseId/evidence |
| 进入 | 案件目录「对象与证据」<br>资料范围概况<br>相关图对象或材料入口 |
| 离开/返回 | 打开源告警、Run 查询与报告、工件或人工修订<br>返回所选对象、调查模式或案件资料 |
| 主区域 | 概况计数<br>按对象/按调查切换<br>对象列表和明细面板<br>原告警、Run 与证据引用 |
| 页签/次级入口 | 按对象查看<br>按调查查看<br>仅关联到证据的材料、原告警、保存报告和引用 |
| 侧栏/弹窗 | 左侧对象搜索及类别<br>右侧所选对象资料、证据、告警和关联运行<br>原件或告警预览<br>本页无此类入口 |
| 关键状态 | 有对象、无对象或无匹配<br>有历史但当前无对象<br>索引未建立、空、可用与部分<br>外部库存缺供、正文受限或缺失 |

**正常操作流程**

1. 读对象、证据和材料概况
2. 按对象浏览时搜索、筛选并选中，读其关联告警、调查和证据
3. 按调查浏览时选实际 Run 进入其已存材料
4. 打开原件或核仅摘要、受限状态

**当前差异与样式归属**

| 对照项 | 具体内容 |
| --- | --- |
| 已定位源码差异 | 4173 按调查使用独立材料卡及查询/报告入口，8181 可复用 CaseInvestigations 历史布局<br>现 8181 .soc-case-object-browser、统一引用抽屉与原型专有 .cw-material-* 右栏层级不同，须核当前对象身份及回链 |
| 4173组件/布局 | [case-workflow.js:175](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:175) · 对象筛选及证据<br>[case-workflow.js:198](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:198) · 右侧对象详情和来源<br>[case-workflow.js:202](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:202) · 按调查浏览<br>[case-workflow.js:203](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:203) · 概况和模式切换 |
| 4173样式 | [investigation.css:94](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:94) · .cw-material-browser、对象导航及细节<br>[investigation.css:95](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:95) · 对象列表和信息卡响应布局<br>[investigation.css:96](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:96) · 材料模式与断点 |
| 8181组件/布局 | [CaseEvidence.tsx:23](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseEvidence.tsx:23) · 证据概况和对象分组<br>[CaseEvidence.tsx:48](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseEvidence.tsx:48) · 对象、调查模式切换<br>[CaseEvidence.tsx:50](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseEvidence.tsx:50) · 对象资料、匹配与来源抽屉<br>[CaseInvestigations.tsx:14](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigations.tsx:14) · 按调查的历史/材料复用 |
| 8181样式 | [case-workbench.css:26](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-workbench.css:26) · .soc-case-object-browser、对象选择<br>[InvestigationDetail.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationDetail.css:1) · 证据概况复用的事实栏样式来源<br>[soc-workbench.css:50](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/soc-workbench.css:50) · 面板、状态和抽屉共用样式 |

**四项整页验收**

| 维度 | 必须核对 |
| --- | --- |
| 功能 | 核对象筛选、证据/威胁与覆盖统计、可按调查查材料、精确原件跳转。 |
| 交互 | 在对象与调查模式间切换，选择不同对象及 Run，打开和关闭素材，不串到别的案或对象。 |
| 数据 | 前后对照对象键及原材料、有效证据/威胁身份和索引状态。只显示真实资产信息及实际引用可用性。 |
| 视觉：布局/表图卡 | 覆盖顶部概况、模式切换、左侧目录、右侧证据和材料卡。无对象模式仍能进按调查区域。 |
| 视觉：按钮/图标 | 核搜索及类型控件、对象类别图标、材料类型和源链接位置。模式按钮要有清楚的当前状态。 |
| 视觉：字体/间距 | 对照计数字号、对象摘要行、字段文案与证据条目间距。保留路径或长值的可读换行。 |
| 视觉：侧栏/弹窗 | 告警预览及原件抽屉需可读完整来源，关闭后保持同一对象、Run 或查询位置。 |
| 视觉：默认视口 | 默认能看模式、概况和首个可读对象/明确空态。窄宽度侧栏可达，正文不被列表挤到不可见。 |

当前验收状态：未开始整页迁移与真实视觉验收。

## 人工任务

查看本案待办与已完成事实，创建和编辑单个事项，回查实际完成者、范围及修订。

功能：`F22-02`, `F22-03`, `F22-04`, `F22-05`, `F22-06`, `F22-07`, `F22-08`。

| 页面范围 | 内容 |
| --- | --- |
| 4173路由 | #/cases/:caseId/tasks |
| 8181路由 | /cases/:caseId/tasks |
| 进入 | 案内「人工任务」<br>调查概览待办<br>固定 Run 由来源带入创建<br>任务修订深链 |
| 离开/返回 | 保存后返回同案任务页和特定版本<br>从任务回源 Run、材料或故事<br>关闭编辑返回列表位置 |
| 主区域 | 任务列表及待办<br>状态、期限、负责人、结果<br>任务修订与来源<br>创建或编辑表单 |
| 页签/次级入口 | 人工任务主视图<br>当前任务、指定修订和来源 Run |
| 侧栏/弹窗 | 8181 编辑、详情或版本读取抽屉<br>4173 任务表单模态<br>8181 创建和编辑抽屉、历史版本与冲突重读 |
| 关键状态 | 未开始、进行中、完成、取消<br>未分配无期限、来源不明、版本未知<br>保存中、成功、失败或 409<br>范围变更与冻结原修订 |

**正常操作流程**

1. 先看待办数与当前任务状态
2. 打开详情或历史版本，核来源和结果适用范围
3. 明确新建或编辑，完成前核实结果及范围
4. 提交后读回新版本、待办数与故事，遇版本冲突明确查看最新并决定重编

**当前差异与样式归属**

| 对照项 | 具体内容 |
| --- | --- |
| 已定位源码差异 | 4173 主体以任务卡和通用模态表单呈现，8181 为表格加右抽屉，另有版本查看<br>4173 导入版本只读且本地编辑为演示，8181 具有版本约束、冲突重读和正式写入接线 |
| 4173组件/布局 | [case-workflow.js:116](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:116) · 原型任务保存和状态规则<br>[case-workflow.js:205](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:205) · 导入只读版本及角色<br>[case-workflow.js:209](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:209) · 任务卡和编辑入口<br>[case-workflow.js:235](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:235) · 任务表单 |
| 4173样式 | [investigation.css:88](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:88) · .cw-task-list、.cw-form-grid 和任务卡<br>[investigation.css:89](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:89) · 任务表单响应布局<br>[styles.css:6](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:6) · 通用模态框和滚动 |
| 8181组件/布局 | [CaseTasks.tsx:20](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseTasks.tsx:20) · 任务状态、历史和汇总<br>[CaseTasks.tsx:37](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseTasks.tsx:37) · 任务 DataTable<br>[CaseTasks.tsx:43](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseTasks.tsx:43) · TaskHistory<br>[CaseTaskDrawer.tsx:80](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseTaskDrawer.tsx:80) · 创建/编辑抽屉 |
| 8181样式 | [table.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/components/shadcn/table.css:1) · 任务表格及操作列<br>[case-workbench.css:12](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-workbench.css:12) · 任务选择和范围行<br>[soc-workbench.css:50](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/soc-workbench.css:50) · 内容面板和公共表单<br>[dialog.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/components/shadcn/dialog.css:1) · 公共弹窗底层 |

**四项整页验收**

| 维度 | 必须核对 |
| --- | --- |
| 功能 | 核待办数、四状态、明确创建、编辑和取消、完整完成范围、版本冲突、后续引用与故事。 |
| 交互 | 走正常新建和编辑路径，关闭保留列表状态。简单旧版本冲突后依靠显式查看和重编，草稿和当前记录均可读。 |
| 数据 | 核任务、修订、案范围、负责人/完成者/修改者与时间。人工结果、适用范围和其他流程状态各按保存事实。 |
| 视觉：布局/表图卡 | 按原型对照任务标题、状态、责任、期限、结果、来源及修订入口。现表格承载这些层级须同屏完整。 |
| 视觉：按钮/图标 | 核添加、编辑、关闭和保存位置。历史、引用及表格交互清楚地区别当前任务入口。 |
| 视觉：字体/间距 | 比对任务标题、次级责任和时间、状态标识、长结果与表单间距。空字段有稳定对齐。 |
| 视觉：侧栏/弹窗 | 核创建与编辑抽屉、版本窗口的高度、正文滚动和底部确认。错误提示保持在当前表单且按钮可达。 |
| 视觉：默认视口 | 默认看得到待办、任务表与添加入口。长表加载和抽屉内滚动独立，当前范围及保存按钮不会被遮挡。 |

当前验收状态：未开始整页迁移与真实视觉验收。

## 处理活动、评论与附件

回查同案管理和协作动作，另以评论和可下载附件记录协作材料。

功能：`F23-05`, `F24-01`, `F24-02`, `F24-03`。

| 页面范围 | 内容 |
| --- | --- |
| 4173路由 | #/cases/:caseId/activities<br>#/cases/:caseId/comments |
| 8181路由 | /cases/:caseId/activities<br>/cases/:caseId/comments |
| 进入 | 案内「处理活动」或「评论与附件」<br>从成员和任务变更回查活动及目标 |
| 离开/返回 | 活动打开关联对象或版本<br>评论留在该案<br>附件原件下载或显示文件状态<br>回案内资料 |
| 主区域 | 活动列表、时间、目标和变更<br>评论列表与编辑区<br>附件清单、文件元信息与下载/上传 |
| 页签/次级入口 | 处理活动与评论附件为两个案内页签<br>变更明细、原对象链接与原文件下载 |
| 侧栏/弹窗 | 活动源或文件关联按所用入口打开<br>文件选择与已有目标/材料读取控件 |
| 关键状态 | 活动无记录、可展开、仅摘要或无目标<br>评论为空、保存中或失败<br>附件可用、失效、已上传待登记、登记成功或失败 |

**正常操作流程**

1. 在处理活动筛选、展开并打开目标，核时间、操作者和变更
2. 切到评论与附件，读已有评论和文件
3. 按授权填写评论或明确选择文件上传/登记，成功后读回
4. 按同文件身份下载

**当前差异与样式归属**

| 对照项 | 具体内容 |
| --- | --- |
| 已定位源码差异 | 4173 活动用其默认列表呈现，8181 用 VerticalTimeline 和类型按钮<br>4173 评论及附件同页有两栏和演示下载，8181 使用共享内容卡并接实际上传和登记接口<br>真实附件失效、跨页活动目标与保存动作对照仍待核 |
| 4173组件/布局 | [app.js:316](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:316) · 处理活动及条目表<br>[app.js:409](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:409) · 两个独立页签<br>[app.js:436](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:436) · 评论与附件并列<br>[app.js:678](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:678) · 原型附件演示下载 |
| 4173样式 | [styles.css:5](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:5) · .comments-layout、评论和附件卡<br>[styles.css:9](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:9) · 窄屏评论附件排列<br>[styles.css:6](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:6) · 通用活动详情浮层 |
| 8181组件/布局 | [CaseReadPanels.tsx:16](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseReadPanels.tsx:16) · 过滤及活动时间线<br>[CaseReadPanels.tsx:23](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseReadPanels.tsx:23) · 变更数据与回链<br>[CaseCommentsAttachments.tsx:16](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseCommentsAttachments.tsx:16) · 评论和附件页面<br>[CaseCommentsAttachments.tsx:29](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseCommentsAttachments.tsx:29) · 文件上传、登记、下载接线 |
| 8181样式 | [case-workbench.css:48](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-workbench.css:48) · .soc-attachment、.soc-comment-form<br>[soc-workbench.css:15](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/soc-workbench.css:15) · 通用时间线和内容区<br>[DetailWorkspace.css:17](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/DetailWorkspace.css:17) · 案内分栏及正文内距 |

**四项整页验收**

| 维度 | 必须核对 |
| --- | --- |
| 功能 | 核活动事件及目标、评论保存读回、同案附件元数据、下载、上传和登记。 |
| 交互 | 两页签独立选择。评论草稿、文件选择和操作回执保持操作对应，活动详情返回同条目。 |
| 数据 | 活动和评论按保存的谁、何时、何目标读取。文件上传与案件关联分步核回执，按原 file_id 下载。 |
| 视觉：布局/表图卡 | 比较活动列表与时间线的默认层级。评论正文、输入、附件列表及上传区完整并易区分。 |
| 视觉：按钮/图标 | 核筛选按钮、展开入口和目标链接位置。附件行的文件图标、下载、上传动作在合适区域。 |
| 视觉：字体/间距 | 核长评论、文件名、时间戳和操作者的换行与间距，元信息不会盖住正文或动作。 |
| 视觉：侧栏/弹窗 | 确认系统文件选择器与页面弹窗的焦点交接，活动或素材详情关闭后回原条目，使用实际对应浮层。 |
| 视觉：默认视口 | 默认可看活动标题、过滤和条目。评论与附件正常宽度同屏有可达入口，窄宽度可滚至提交及下载。 |

当前验收状态：未开始整页迁移与真实视觉验收。

本页范围说明：F24-02：完整功能规则保留；本期只核有效附件引用/关联和元数据，业务后端真实文件字节上传/下载联调继续后置。本次完整规划不恢复字节操作。；F24-03：完整功能规则保留；本期只核有效附件引用/关联和元数据，业务后端真实文件字节上传/下载联调继续后置。本次完整规划不恢复字节操作。。

## Case 案件助手

从同案上下文预填问题、理解既有答复和引用，按确认边界维持对话与人工后续的结构。

功能：`F26-02`, `F26-03`, `F26-04`, `F26-05`, `F26-06`, `F26-07`, `F26-08`。

| 页面范围 | 内容 |
| --- | --- |
| 4173路由 | #/cases/:caseId/:tab |
| 8181路由 | /cases/:caseId/:tab |
| 进入 | 案内公共页头<br>故事、图节点、固定 Run 和人工版本入口的同案预填 |
| 离开/返回 | 关闭助手返回原页及选择<br>已保存答复可打开原运行、引用、任务或历史<br>切案加载另一会话上下文 |
| 主区域 | 助手标题及当前案<br>历史会话或消息<br>范围与引用<br>建议问题及输入/状态区 |
| 页签/次级入口 | 共享抽屉内会话及范围选择<br>来源工件、续问草稿、人工事实和保存记录 |
| 侧栏/弹窗 | 右侧案件助手抽屉<br>引用与消息源<br>上下文选择<br>保存答复<br>人工任务草稿 |
| 关键状态 | 新会话、已存会话、只读导入<br>范围可编辑、失败待核、已保存<br>发送与保存整项暂缓 |

**正常操作流程**

1. 按入口填入全案、告警、对象、Run 或人工范围，浏览历史及建议
2. 用户审核草稿和引用后才可能明确发送
3. 执行、已保存答复、失败和人工续接有单独状态
4. 有权限且范围恢复后才使用明确的保存到调查记录表单

**当前差异与样式归属**

| 对照项 | 具体内容 |
| --- | --- |
| 已定位源码差异 | 4173 使用 .ca-panel 专用停靠式助手，8181 采用 SocModal drawer 与共享 Markdown<br>原型真实导入只读。8181 可找到发送及保存代码入口，运行与保存保持本阶段暂缓 |
| 4173组件/布局 | [case-assistant.js:50](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.js:50) · 各入口的范围预填<br>[case-assistant.js:115](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.js:115) · 右侧助手和建议<br>[case-assistant.js:124](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.js:124) · 关闭、消息与输入区<br>[case-assistant.js:165](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.js:165) · 本地保存演示 |
| 4173样式 | [case-assistant.css:5](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.css:5) · .ca-panel 的右侧停靠<br>[case-assistant.css:16](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.css:16) · .ca-thread 消息区及滚动<br>[case-assistant.css:75](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.css:75) · 小视口助手覆盖规则 |
| 8181组件/布局 | [CaseWorkbenchDetail.tsx:81](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchDetail.tsx:81) · 同案助手挂载<br>[CaseAssistant.tsx:82](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseAssistant.tsx:82) · SocModal 抽屉和当前上下文<br>[CaseAssistant.tsx:101](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseAssistant.tsx:101) · 范围选择<br>[CaseAssistant.tsx:118](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseAssistant.tsx:118) · 保存答复表单源码 |
| 8181样式 | [case-workbench.css:32](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-workbench.css:32) · .soc-case-assistant、.soc-case-chat 和输入区<br>[soc-workbench.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/soc-workbench.css:1) · 共享视觉层<br>[AssistantMarkdown.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/assistant/AssistantMarkdown.css:1) · 回答文本及版式<br>[dialog.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/components/shadcn/dialog.css:1) · 抽屉组件的弹窗和遮罩底层 |

**四项整页验收**

| 维度 | 必须核对 |
| --- | --- |
| 功能 | 只保留 F26 和 F20-04 的入口、范围、历史与后续结构规划，正式提问、保存和续接按暂缓范围。 |
| 交互 | 后续核从不同页只预填同案上下文、关闭回原处、切案隔离。暂缓期优先辨认只读状态。 |
| 数据 | 现存历史绑定其原范围、会话和引用。实际问答等由独立授权及真实回执支持。 |
| 视觉：布局/表图卡 | 整页对照外层内容与右助手、标题、范围行、消息、建议和输入区的关系。 |
| 视觉：按钮/图标 | 核页头入口、关闭图标、范围选择及送出控件在各自区域。暂缓或只读状态有清晰可见表现。 |
| 视觉：字体/间距 | 核助手标题、范围标签、消息时间和正文的层级及行距。长 Markdown 及引用可读。 |
| 视觉：侧栏/弹窗 | 核助手抽屉与引用、保存表单的层叠和焦点。关闭后还原原页，键盘不会让输入区不可达。 |
| 视觉：默认视口 | 默认保持页头、上下文、会话滚动区及输入区，窄窗口核底部控件。实际截图仅在允许的只读范围内进行。 |

当前验收状态：未开始整页迁移与真实视觉验收。

本页范围说明：F26-02：整项后置；F26-03：整项后置；F26-04：整项后置；F26-05：整项后置；F26-06：整项后置；F26-07：整项后置；F26-08：整项后置。

## 调查运行列表

在独立运行目录定位实际告警、事件或案件轮次，并了解运行范围、状态和交付。

功能：`F14-07`, `F15-02`。

| 页面范围 | 内容 |
| --- | --- |
| 4173路由 | #/investigations |
| 8181路由 | /investigations |
| 进入 | 主导航「调查运行」<br>案件列表查看调查运行<br>运行详情返回全部运行 |
| 离开/返回 | 打开固定 Run 的调查发现或共用视图<br>回案件列表<br>从具体运行上下文返回其实际主体 |
| 主区域 | 标题与返回/操作<br>统计<br>运行记录目录及摘要<br>现有 8181 时间轴、搜索/过滤、预览 |
| 页签/次级入口 | 全局运行列表与单次 Run 详情分立<br>固定运行、返回案件和 8181 当前已载入导出入口 |
| 侧栏/弹窗 | 8181 运行预览侧栏<br>本页无此类入口 |
| 关键状态 | 有 Run、筛选空、加载或失败<br>告警 A、事件 I、Case 和无 Case<br>运行/交付分立<br>摘要或投入未知 |

**正常操作流程**

1. 读取记录统计和交付概况
2. 在候选中定位精确轮次
3. 先读主要状态、输入和时间，再开同一 Run
4. 对无 Case 的运行沿其真实主体返回

**当前差异与样式归属**

| 对照项 | 具体内容 |
| --- | --- |
| 已定位源码差异 | 4173 有统计和运行卡片网格，源码未见该目录搜索过滤。8181 以表格、时间轴和运行预览作主要展示，附搜索、筛选及已载入导出<br>统计卡和摘要的范围与位置需用同一批现有 Run 对照 |
| 4173组件/布局 | [investigation-workspace.js:240](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:240) · 全局运行目录<br>[investigation-workspace.js:241](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:241) · 统计和两列运行记录卡<br>[investigation-workspace.js:420](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:420) · 全局目录和固定轮次路由 |
| 4173样式 | [investigation.css:13](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:13) · .iv-run-grid、.iv-run-tile 和记录卡<br>[investigation.css:8](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:8) · .iv-root、统计和元信息<br>[styles.css:5](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/styles.css:5) · 产品框架与导航 |
| 8181组件/布局 | [InvestigationListPage.tsx:22](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationListPage.tsx:22) · 正式运行目录<br>[InvestigationListPage.tsx:40](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationListPage.tsx:40) · 搜索和筛选<br>[InvestigationListPage.tsx:42](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationListPage.tsx:42) · 表格和分页<br>[InvestigationListPage.tsx:47](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationListPage.tsx:47) · 运行预览<br>[InvestigationListPage.tsx:50](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationListPage.tsx:50) · 时间轴 |
| 8181样式 | [investigations.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/investigations.css:1) · .soc-investigation-table、时间轴和状态<br>[soc-workbench.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/soc-workbench.css:1) · 队列标题、统计与面板<br>[SubjectPreview.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/SubjectPreview.css:1) · 运行预览<br>[ListWorkspace.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/shared/ui/ListWorkspace.css:1) · 现有筛选列表工具 |

**四项整页验收**

| 维度 | 必须核对 |
| --- | --- |
| 功能 | 核实际多主体目录、四类统计/摘要、输入、时间及固定轮次跳转。 |
| 交互 | 从案内入口进全局目录，选一条既有 Run 再返回。现有搜索、筛选或预览与记录卡的路径都需定位准确。 |
| 数据 | 以同目录范围核计数、实际 Case 归属和原 Run。无 Case 时保留真实主体，分开执行和交付。 |
| 视觉：布局/表图卡 | 对照标题、统计、运行卡/表格及时间轴的相对顺序和可见信息。保持每行能识别固定 Run。 |
| 视觉：按钮/图标 | 核返回、导出、时间轴跳转与表格预览/详情动作的位置。现有搜索表示为实现差异。 |
| 视觉：字体/间距 | 对照统计值、轮次标题、状态、来源和摘要的层级。时间跨度、ID 和状态文本分别有足够空间。 |
| 视觉：侧栏/弹窗 | 对照原型卡片直达与产品右侧运行预览。预览应保留状态、身份、进入与关闭动作。 |
| 视觉：默认视口 | 默认可看标题、总体指标及第一批运行入口。表格宽度、长运行标题及时间轴范围可完整阅读或滚动。 |

当前验收状态：未开始整页迁移与真实视觉验收。

## 调查发现

理解这一轮的目标、原输入、判断、发现与未解决问题，明确可回查的证据和后续工作。

功能：`F16-03`, `F15-03`, `F12-04`, `F22-09`。

| 页面范围 | 内容 |
| --- | --- |
| 4173路由 | #/investigations/:runId/overview<br>#/cases/:caseId/investigations?run=:runId&view=overview |
| 8181路由 | /investigations/:runId/overview<br>/cases/:caseId/investigations?run=:runId&view=overview |
| 进入 | 案内选定 Run、全局运行或告警/事件运行目录进入「调查发现」<br>五主视图返回发现 |
| 离开/返回 | 进入同轮 AI 分析、查询与证据、关系图或报告<br>打开冻结范围、对比结果或人工任务<br>返回对应主体/历史 |
| 主区域 | 运行页头、选择器及五主视图<br>正式结论与发现<br>工具/证据及交付提示<br>范围、待核问题和后续 |
| 页签/次级入口 | 调查发现为共用主视图<br>同一 Run 的 AI 分析、查询与证据、调查关系图、报告与响应<br>原输入、比较结果、可核查材料和人工任务 |
| 侧栏/弹窗 | 原型右列范围、分诊及案件跟进<br>产品工件与引用抽屉<br>人工任务创建或来源原件 |
| 关键状态 | 运行中、待启动与已结束<br>正式结论、只有系统说明、无结果<br>部分交付、失败、未知<br>有原输入或未保存、结果缺材料 |

**正常操作流程**

1. 先核 Run、主体及状态
2. 读目标、正式结果或系统交接及限制
3. 回查输入、发现和材料
4. 按固定结果入口准备人工任务或查看后续响应

**当前差异与样式归属**

| 对照项 | 具体内容 |
| --- | --- |
| 已定位源码差异 | 4173 主结果卡与右侧冻结范围和跟进并列。8181 当前 RunWorkspace 有共享状态条，RunFindings 用 .soc-content-panel 组织不同结果块<br>两版固定主题身份、待核问题和可读来源须在整页内对照，不从运行成功推断有交付 |
| 4173组件/布局 | [investigation-workspace.js:257](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:257) · 固定轮次调查发现<br>[investigation-workspace.js:261](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:261) · 结论、依据和状态<br>[investigation-workspace.js:267](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:267) · 原冻结范围<br>[investigation-workspace.js:269](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:269) · 左右列、来源和跟进 |
| 4173样式 | [investigation.css:8](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:8) · .iv-overview 两列、.iv-stack 与依据卡<br>[investigation.css:10](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:10) · .iv-tabs 主视图和当前态<br>[assessment-view.css:1](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/assessment-view.css:1) · 结构化结论和范围项目 |
| 8181组件/布局 | [InvestigationDetailPage.tsx:18](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationDetailPage.tsx:18) · Run context 与主体返回<br>[RunWorkspace.tsx:56](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunWorkspace.tsx:56) · 执行/交付、停止、时间和状态区<br>[RunViews.tsx:29](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:29) · RunFindings<br>[RunViews.tsx:55](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:55) · 发现、问题和引用<br>[RunViews.tsx:65](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:65) · 输入与成员覆盖 |
| 8181样式 | [InvestigationDetail.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationDetail.css:1) · .soc-run-five-status 和运行视图条<br>[investigations.css:22](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/investigations.css:22) · 发现和运行正文排版<br>[DetailWorkspace.css:22](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/DetailWorkspace.css:22) · 共享内容块内距 |

**四项整页验收**

| 维度 | 必须核对 |
| --- | --- |
| 功能 | 核目标、独立状态、结论与未决项、报告/材料入口、原冻结输入及人工跟进。 |
| 交互 | 在五视图间切换仍保持 Run。点当前问题、引用、原输入和回主体，确保每条落点可恢复。 |
| 数据 | 分别核运行状态、交付、停止、用量、来源和冻结范围。系统说明、已保存结论及问答原件保留各自身份。 |
| 视觉：布局/表图卡 | 对照页头、五视图、状态区、结论卡、资料块与范围辅助栏的排列。空和部分交付使用对应页面层级。 |
| 视觉：按钮/图标 | 核回主体、打开冻结输入、引用、进工具与创建任务的位置和可见性。每个按钮带准确目标。 |
| 视觉：字体/间距 | 核主结论、较长发现、说明及状态标签的阅读层级。计量和正文用各自字体与间距。 |
| 视觉：侧栏/弹窗 | 冻结输入、引用和工件由对应面板展开，返回仍是原轮次。查看受限材料可关闭并继续浏览。 |
| 视觉：默认视口 | 默认能读 Run、状态及主结论或明确的无结论说明。长正文、右侧卡和五视图均能完整触达。 |

当前验收状态：未开始整页迁移与真实视觉验收。

本页范围说明：F22-09：用户显式创建人工任务纳入；打开助手并询问结果暂缓。。

## AI 分析与执行明细

阅读本轮保存的分析及采用来源，并进一步核每步输入、输出、执行状态、错误和投入。

功能：`F17-01`, `F17-02`, `F18-01`, `F17-03`。

| 页面范围 | 内容 |
| --- | --- |
| 4173路由 | #/investigations/:runId/process<br>#/cases/:caseId/investigations?run=:runId&view=process |
| 8181路由 | /investigations/:runId/process<br>/cases/:caseId/investigations?run=:runId&view=process |
| 进入 | 固定 Run 主视图「AI 分析」<br>从本轮发现的依据或材料打开分析<br>在 AI 分析里进入「执行明细」 |
| 离开/返回 | 从执行明细返回同轮 AI 分析<br>沿实际引用到同轮查询或工件<br>回运行发现或主体 |
| 主区域 | 分析阶段及摘要卡<br>执行明细次级区和步骤账本<br>能力与投入<br>输入/输出/来源工件 |
| 页签/次级入口 | AI 分析为五主视图之一<br>执行明细是 AI 分析内部次级阅读<br>执行明细、来源工件、已保存对话和原分析依据 |
| 侧栏/弹窗 | 产品步骤或工件阅读区<br>步骤输入、输出及工件原件抽屉 |
| 关键状态 | 有阶段、仅有账本、没有分析正文<br>成功、跳过、失败和未产出<br>部分载入、目录或权限受限<br>费用或用量未知 |

**正常操作流程**

1. 先看保存的阶段和采用材料，选择原引用
2. 明确进入执行明细，按步骤、类型或来源定位
3. 打开该步参数、输入、输出或复用工件
4. 核状态、错误与冻结能力/用量后返回

**当前差异与样式归属**

| 对照项 | 具体内容 |
| --- | --- |
| 已定位源码差异 | 4173 .iv-* 阶段卡和顺序账本各有专用布局，8181 在 RunProcess 中共享阶段和执行步骤详情<br>需核父子步骤、截断和原有分类筛选，保留执行明细次级位置 |
| 4173组件/布局 | [investigation-workspace.js:273](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:273) · 阶段分析<br>[investigation-workspace.js:282](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:282) · 分析与账本次级入口<br>[investigation-workspace.js:284](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:284) · 执行明细按已有顺序阅读<br>[investigation-workspace.js:289](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:289) · 保存材料目录及内容状态 |
| 4173样式 | [investigation.css:19](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:19) · .iv-analysis-overview、.iv-ledger-controls、阶段编号和明细<br>[investigation.css:12](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:12) · .iv-raw、工件块及代码正文<br>[investigation.css:10](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:10) · 同轮主视图页签 |
| 8181组件/布局 | [RunWorkspace.tsx:62](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunWorkspace.tsx:62) · 运行主导航<br>[RunViews.tsx:80](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:80) · 分析、执行明细与步骤<br>[RunViews.tsx:99](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:99) · 步骤输入、输出和复用入口<br>[RunViews.tsx:178](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:178) · 冻结能力<br>[RunViews.tsx:219](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:219) · 工件原件抽屉 |
| 8181样式 | [investigations.css:24](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/investigations.css:24) · .soc-run-stages、.soc-run-stage-code<br>[DetailWorkspace.css:17](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/DetailWorkspace.css:17) · 共享分析内容分栏<br>[soc-workbench.css:50](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/soc-workbench.css:50) · 正文、状态、动作区和浮层<br>[AssistantMarkdown.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/assistant/AssistantMarkdown.css:1) · 保存分析文本渲染 |

**四项整页验收**

| 维度 | 必须核对 |
| --- | --- |
| 功能 | 核已保存分析、历史问答、独立步骤账本、工件及冻结能力/用量。 |
| 交互 | 进入执行明细后筛选、选步骤、开输入/输出和返回。切步骤时右侧读回必须跟随同轮。 |
| 数据 | 同轮按保存序号和父子关系核对，初始输入、步骤参数、工件和复用来源分别查回。未知投入保留空态。 |
| 视觉：布局/表图卡 | 比较阶段卡、说明、账本入口、步骤列表与当前详情区，顶部主视图保持明确层级。 |
| 视觉：按钮/图标 | 核执行明细/返回、展开箭头、步骤原件及重试动作位置。步骤状态标识对应已记录状态。 |
| 视觉：字体/间距 | 对照阶段号、步骤标题、小状态与输入输出正文。等宽工件内容与分析段落保持各自间距。 |
| 视觉：侧栏/弹窗 | 工件抽屉打开可识别 Run、步骤和类型，长内容可读，关闭回当前明细而不跳轮。 |
| 视觉：默认视口 | 默认可见分析题、阶段首段和执行明细入口。账本长列表或长原件不遮挡回退和工具栏。 |

当前验收状态：未开始整页迁移与真实视觉验收。

本页范围说明：F17-01：已有普通分析过程、材料与引用读取纳入；正式助手问答保存记录暂缓。。

## 查询与证据

按确切查询记录和证据看当轮实际查了什么、返回什么，回到原查询、工件及引用位置。

功能：`F28-01`, `F28-02`, `F18-02`。

| 页面范围 | 内容 |
| --- | --- |
| 4173路由 | #/investigations/:runId/tools<br>#/cases/:caseId/investigations?run=:runId&view=tools |
| 8181路由 | /investigations/:runId/tools<br>/cases/:caseId/investigations?run=:runId&view=tools |
| 进入 | 固定 Run 的「查询与证据」<br>调查发现与 AI 分析的 query 或 artifact 精确链接<br>案件对象与材料回到指定 Run |
| 离开/返回 | 返回本轮全部查询、原引用处、AI 分析或发现<br>打开所选工件及源告警<br>关闭详情保持当前查询 |
| 主区域 | 查询条目、参数、状态和结果<br>保存工件目录<br>精确回链及没有记录提示 |
| 页签/次级入口 | 查询与证据主视图<br>定位 query、artifact、出处和原案材料 |
| 侧栏/弹窗 | 8181 查询结果和工件抽屉<br>返回结果及受限原件的查看控件 |
| 关键状态 | 未执行、已跳过、失败或超时<br>成功零行和有结果<br>复用<br>仅目录、摘要、受限、缺失<br>错轮引用 |

**正常操作流程**

1. 读当轮查询目录和材料来源
2. 选查询看参数、对象、保存状态、实际返回或摘要
3. 依可用性读工件与引用原文
4. 返回发起页或当轮查询全表

**当前差异与样式归属**

| 对照项 | 具体内容 |
| --- | --- |
| 已定位源码差异 | 4173 查询及证据以 .iv-tools 卡片、原件目录和从正文跳转的选择提示呈现<br>8181 以查询表、计数及抽屉承载，需对照 query 深链返回以及证据可用性布局 |
| 4173组件/布局 | [investigation-workspace.js:170](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:170) · 查询状态名称<br>[investigation-workspace.js:289](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:289) · 物料目录及粒度<br>[investigation-workspace.js:299](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:299) · 查询与证据主汇总<br>[investigation-workspace.js:302](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:302) · 指定查询与返回入口 |
| 4173样式 | [investigation.css:12](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:12) · .iv-tools 双列、.iv-artifacts 与 JSON/原文<br>[investigation.css:16](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:16) · 窄视口查询区切换<br>[investigation.css:8](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:8) · 执行卡与说明 |
| 8181组件/布局 | [RunViews.tsx:102](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:102) · 真实查询状态<br>[RunViews.tsx:121](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:121) · 查询表和分页<br>[RunViews.tsx:156](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:156) · QueryResultDrawer<br>[RunViews.tsx:219](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:219) · ArtifactViewer |
| 8181样式 | [soc-workbench.css:99](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/soc-workbench.css:99) · .soc-query-counts 及查询事实<br>[investigations.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/investigations.css:1) · 运行工件及列表共用层<br>[table.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/components/shadcn/table.css:1) · 查询表格与结果样例承载<br>[dialog.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/components/shadcn/dialog.css:1) · 抽屉底层 |

**四项整页验收**

| 维度 | 必须核对 |
| --- | --- |
| 功能 | 核真实目录、查询参数/回执、状态区分、复用与原件回查。 |
| 交互 | 从正文进入同轮确切查询，打开或关闭结果抽屉。返回来源后可再次进本轮全量目录。 |
| 数据 | 请求/返回属于同 Run 的同一步。成功零行、未执行、失败、未知和复用保持真实状态，只有摘要时按可用性说明。 |
| 视觉：布局/表图卡 | 对照目录、材料区和记录详情，不漏查询类型、状态、结果及原件入口。 |
| 视觉：按钮/图标 | 核查看查询、展开、工件和返回动作在指定条目附近。按钮需要有清楚可访问名称。 |
| 视觉：字体/间距 | 核参数、JSON、正文和计数的行高、横向滚动与长内容换行。故障和缺失提示在所属范围。 |
| 视觉：侧栏/弹窗 | 结果与工件抽屉需完整显示当轮记录摘要和可读原件。关闭再选另一查询，样式或旧状态不串。 |
| 视觉：默认视口 | 默认可看查询状态及首个条目/明确空态。长查询、表格及 JSON 通过明确区域滚动，让工具入口持续可达。 |

当前验收状态：未开始整页迁移与真实视觉验收。

## 调查关系图

以历史只读方式看所选轮的真实关系和依据，从原始对象或边追出处。

功能：`F19-03`, `F19-04`。

| 页面范围 | 内容 |
| --- | --- |
| 4173路由 | #/investigations/:runId/graphs<br>#/cases/:caseId/investigations?run=:runId&view=graphs |
| 8181路由 | /investigations/:runId/graphs<br>/cases/:caseId/investigations?run=:runId&view=graphs |
| 进入 | 固定 Run 的「调查关系图」<br>当轮发现或图材料入口<br>案内历史指定 Run |
| 离开/返回 | 查看本轮原图材料或引用<br>显式转入当前案件探索<br>回同轮其他视图或原主体 |
| 主区域 | 轮次及来源头部<br>三栏关系画布和关系详情<br>转入当前案件探索的明确入口<br>原图材料 |
| 页签/次级入口 | 调查关系图主视图，保留同轮五视图<br>保存图工件、原关系、源告警与转入当前案 |
| 侧栏/弹窗 | 原型历史图告警和选中对象详情<br>工件来源抽屉<br>本页无此类入口 |
| 关键状态 | 有图、部分图、缺图、该轮未执行、来源不可用<br>告警/对象/边焦点<br>有实际关联案可转探索 |

**正常操作流程**

1. 确认本轮图是否有保存
2. 查看图范围、图例和本次输入
3. 选节点或边读来源、必要时调整视角
4. 需要继续探索时明确离开历史图进当前案件

**当前差异与样式归属**

| 对照项 | 具体内容 |
| --- | --- |
| 已定位源码差异 | 4173 历史图保留来源材料、同轮范围和专用图形布局。8181 由 RunGraph 读取工件后交共享关系图渲染<br>已见节点形状与控件组织差异。当前案件探索链接要与历史图只读状态各有位置 |
| 4173组件/布局 | [investigation-workspace.js:391](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:391) · 历史源图和工件<br>[investigation-workspace.js:396](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:396) · 所选轮的图视图及空态<br>[investigation-graph.js:156](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-graph.js:156) · 节点/边展示<br>[investigation-graph.js:160](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-graph.js:160) · 三栏画布与来源侧栏 |
| 4173样式 | [investigation-graph.css:26](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-graph.css:26) · .ug-toolbar 与图分栏<br>[investigation-graph.css:38](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-graph.css:38) · .ug-canvas 与视口<br>[investigation-graph.css:52](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-graph.css:52) · .ug-node 与选择高亮<br>[investigation.css:12](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:12) · 历史图材料和说明 |
| 8181组件/布局 | [RunWorkspace.tsx:18](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunWorkspace.tsx:18) · 固定 Run 上下文<br>[RunViews.tsx:229](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:229) · RunGraph<br>[RunViews.tsx:236](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:236) · 历史图只读与当前案链接<br>[RelationGraph.tsx:95](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/RelationGraph.tsx:95) · 共享画布、节点及右区 |
| 8181样式 | [RelationGraph.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/RelationGraph.css:1) · 共享 .soc-graph-* 样式<br>[InvestigationDetail.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationDetail.css:1) · 运行身份及导航<br>[DetailWorkspace.css:17](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/DetailWorkspace.css:17) · 共用内容容器 |

**四项整页验收**

| 维度 | 必须核对 |
| --- | --- |
| 功能 | 核精确历史图、节点/边来源、缺图、同案探索回链和历史只读。 |
| 交互 | 用默认视口选择节点与边，再核缩放/重置和材料说明。进入当前探索后仍可返回原历史快照。 |
| 数据 | graph_artifact_id、节点、边和来源均属该轮。较新图与历史图分别读取，没图时展示真实可用性。 |
| 视觉：布局/表图卡 | 核历史阅读区、节点和边样式、两侧栏目、画布图例及材料入口。保留与当前探索页的视觉区分。 |
| 视觉：按钮/图标 | 核缩放、重置、图层、来源、展开和离开历史的动作位置，关联图标不误导用户以为已可修改历史。 |
| 视觉：字体/间距 | 核图标题、节点/边文字、图例、材料说明及侧栏字体间距，长标签仍可识别来源。 |
| 视觉：侧栏/弹窗 | 材料抽屉、详情与当前探索入口各自归属准确，关闭后恢复原图选择和位置。 |
| 视觉：默认视口 | 首进及重置时实测节点和标签在默认画布内的完整性，必要时可顺畅缩放。无图时保留导航与来源提示。 |

当前验收状态：未开始整页迁移与真实视觉验收。

## 报告与响应

读取和下载这一轮保存的报告或系统收尾材料，并核对建议及实际响应回执。

功能：`F16-04`, `F18-03`, `F27-02`, `F27-03`, `F27-04`。

| 页面范围 | 内容 |
| --- | --- |
| 4173路由 | #/investigations/:runId/report<br>#/cases/:caseId/investigations?run=:runId&view=report |
| 8181路由 | /investigations/:runId/report<br>/cases/:caseId/investigations?run=:runId&view=report |
| 进入 | 固定 Run 主视图「报告与响应」<br>调查发现的后续处理或案件材料中的报告链接 |
| 离开/返回 | 下载同轮报告<br>打开建议依据或已有动作回执<br>返回当轮发现、工具或实际主体 |
| 主区域 | 报告标题、状态与正文<br>建议卡<br>批准/拒绝状态和实际回执分区<br>无报告及缺记录提示 |
| 页签/次级入口 | 报告与响应为固定 Run 的主视图<br>Markdown 下载、引用、实际响应回执 |
| 侧栏/弹窗 | 建议源或当前已有响应计划阅读<br>引用读回或受控的响应计划入口。审批按暂缓范围 |
| 关键状态 | 报告完整、部分、无报告或只有系统说明<br>建议有/无、审批要求三态<br>已审阅、已执行、失败、执行不明或未关联回执 |

**正常操作流程**

1. 读报告正文、交付及缺报告状态
2. 有已保存报告时核原件并下载
3. 逐条读响应建议和来源
4. 按明确动作身份查回执，审批暂缓

**当前差异与样式归属**

| 对照项 | 具体内容 |
| --- | --- |
| 已定位源码差异 | 4173 报告在 .iv-report 里以预格式化正文展示，8181 渲染共享 Markdown 并有下载动作<br>4173 支持同轮建议与回执按明确动作配对，8181 可经响应计划回查，页内动作级回执需按保存的接线核<br>已确认暂缓的审批仍按 F27-03 管理 |
| 4173组件/布局 | [investigation-workspace.js:407](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:407) · 动作和回执明确配对<br>[investigation-workspace.js:417](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:417) · 建议、审阅和执行区<br>[investigation-workspace.js:419](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:419) · 该轮保存报告与下载<br>[case-workflow.js:137](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:137) · 原型审批展示 |
| 4173样式 | [investigation.css:12](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:12) · .iv-report 及报告原文<br>[investigation.css:109](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation.css:109) · .iv-response-action-list 建议与执行展示<br>[recommendation-view.css:1](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/recommendation-view.css:1) · 响应/建议样式来源，核本页使用的选择器 |
| 8181组件/布局 | [RunViews.tsx:238](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:238) · RunReport 和实际报告读取<br>[RunViews.tsx:244](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:244) · 报告 Markdown 及下载<br>[RunViews.tsx:246](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:246) · 审批要求信号<br>[CaseResponseProposal.tsx:19](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseResponseProposal.tsx:19) · 已有响应计划与连接入口 |
| 8181样式 | [AssistantMarkdown.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/assistant/AssistantMarkdown.css:1) · 报告 Markdown 版式<br>[soc-workbench.css:50](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/soc-workbench.css:50) · 共用建议及报告卡片<br>[InvestigationDetail.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationDetail.css:1) · 状态及标签<br>[dialog.css:1](/Users/lychee/Projects/SpiritHub-web-8181/web/src/components/shadcn/dialog.css:1) · 建议来源和响应计划浮层 |

**四项整页验收**

| 维度 | 必须核对 |
| --- | --- |
| 功能 | 核实际报告、有无正文、合法下载、建议卡和真实回执。审批写侧保留暂缓。 |
| 交互 | 下载前确认当前 Run，打开来源或已有回执再返回。建议卡的操作与执行记录明确分开。 |
| 数据 | 报告、建议、动作和可读回执均对应原 Run/Result。审批要求未知、明确无需审批及待执行分别保存与阅读。 |
| 视觉：布局/表图卡 | 对照报告标题、下载、状态提示、正文板块、建议和实际回执。缺报告仍保留交付及回到原材料。 |
| 视觉：按钮/图标 | 核下载位于报告标题附近，引用和响应阅读贴随具体卡片，审批/执行按钮以现有授权和状态显隐。 |
| 视觉：字体/间距 | 比对预排版正文和实际 Markdown 的层级、段落、列表、代码块与间距。长表和长链接可读不撑破面板。 |
| 视觉：侧栏/弹窗 | 相关计划和引用打开各自容器，带明确动作/目标。关闭后仍定位原建议或报告。 |
| 视觉：默认视口 | 默认可见报告标题、下载或明确空态、第一块正文或状态提示。长报告和响应卡都可按自然滚动继续阅读。 |

当前验收状态：未开始整页迁移与真实视觉验收。

本页范围说明：F27-03：整项后置；F27-04：已有真实响应记录/回执只读纳入；新执行、重试和审批链暂缓。。

## 实际页面核对与证据保存

### 核对条件

- 独立验收时使用相同浏览器、视口、缩放、语言和可比数据状态，记录实际尺寸和样式主题。
- 先留参考整页的默认状态，再在明确需要的页签、选择和浮层留对照。正常视口与相关窄屏断点单列。
- 默认视口的完整性分别观察初始进入、内容滚动和图重置。区分正常滚动与不可达、意外裁切或重叠。

### 保存记录

- 使用受控目录保存需要业务画面的截图。共享回执只给固定标签、尺寸/数量是否对齐、选择器位置及工程布尔结果。
- 把源码观察和实际 UI 观察分字段记录。视觉差异记录页面、状态、参考位置、实际有效 CSS 来源及解决后的复核结果。

只做默认正常状态和本页直接相关的代表交互/断点；不新增跨浏览器、全设备或故障组合测试。含业务值的截图/DOM保存在受控位置，向Codex/GPT传输遵守AGENTS的数据边界。

源码盘点与当前页面实际效果分别记录。本表没有一项被标作真实视觉通过。
