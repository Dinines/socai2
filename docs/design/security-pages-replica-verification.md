# AiSOC 页面原型：实现与核验回执

2026-10-24，分支`codex/security-pages-replica`。来源见[功能清单](security-pages-replica.md)，启动见[原型说明](../../prototypes/security-pages/README.md)。

## 实现

独立HTML/CSS/JavaScript模块使用文档示例及自拟数据，初始51条告警、12个事件、12个Case。顶部品牌、浏览器标题和favicon改为AiSOC；“告警和事件”下分开告警、事件，“案件管理”下为Cases。数据保存在当前浏览器localStorage，可重置。

| 页面 | 内容 |
| --- | --- |
| 告警 | 列表、搜索筛选、排序分页、列设置、导出、详情、状态/分类/负责人管理 |
| 事件列表 | 多事件队列、优先级及统计、筛选/日期/列设置、预览、详情、单条/批量管理及筛选链接 |
| 事件详情 | 攻击故事、图谱联动/筛选/布局/分组/回放/潜在影响，概览、告警、资产、调查、证据、活动、相似事件和建议 |
| Case列表 | 官方Prioritize incident cases两张图的结构；四统计卡片、Incident/Generic名称、工具栏、筛选集、时间范围、搜索、案件表格、预览和右侧列设置 |
| Case详情 | 概览、内部目录、攻击图、告警及本地成员移动、资产、调查、证据、活动、评论和预置附件 |

Case列表不是从事件队列扩展设计；已另外核对官方列表和列设置图。Case优先级分段为>85、15–85、<15。按用户“不自行发挥”的要求，Generic、创建、设置及仅在图中出现的Similar cases目录保留名称，撤除自拟相似Case列表/理由/计数。

## 浏览器直接检查

使用实际点击、输入、选择、刷新及截图，留存43项结构化观察。前期部分检查发生在扩充数据前的24条告警阶段，其中筛选数量不能当作最终51条数据的固定统计。

| 检查 | 结果 |
| --- | --- |
| 告警搜索/筛选 | PowerShell为1条，空搜索0条且显示空态；严重程度筛选生效 |
| 告警管理 | 保存状态/负责人/分类后列表详情一致；取消不写入；刷新保留；分类列为保存的误报值 |
| 图谱 | 告警/实体联动；分组仍保留精确实体；3条潜在路径标明演示；筛选可得空图；回放前进且可暂停 |
| 范围及审批 | 切换事件后批量选择限定当前范围；无证据事件不显示别的事件建议；批准后证据与对应活动同步 |
| 事件队列 | 12条、首屏8行、下一页4行；外泄搜索2条；未分配且优先级≥70为1条；隐藏标签列生效 |
| 事件管理 | 预览留在队列；解决无说明被拒绝；加说明保存后关联3条告警同步负责人与Resolved |
| Case成员/评论 | 移动后源11→10、目标6→7；评论和数量更新，刷新保留；核验后重置 |
| Case时间/资产 | 11条回放按08:40–09:40升序；用户资产类型显示对应账号；内部目录切换可用 |
| Case列表优先级 | >85得到4条，评分93、89、92、86 |
| Case列表筛选集 | 保存、刷新后可重新应用，仍得到4条 |
| Case入口/预览 | 摘要留在`#/cases`；打开详情为17420；Cases面包屑返回列表 |
| Case列/时间/分页 | 右侧列设置隐藏标签生效；24小时范围6条；下一页4条 |
| Case搜索/范围 | ID17420为1条，空搜索0条；Similar cases没有自拟列表，仅目录名称 |

浏览器错误日志为空。最终截图前恢复初始演示数据。材料均留本地、忽略Git：

- [43项观察](../../.local/verification/security-pages-replica/browser-checks.json)
- [告警](../../.local/verification/security-pages-replica/alerts.png)、[事件列表](../../.local/verification/security-pages-replica/incidents.png)、[事件详情](../../.local/verification/security-pages-replica/incident-detail.png)
- [Case列表](../../.local/verification/security-pages-replica/cases-list.png)、[Case详情](../../.local/verification/security-pages-replica/case.png)

## 独立审阅与限制

未参与实现者`prototype_end_review`只读审查源码，并以本地Node VM复核数据及交互合同。修复分类/类别混淆、跨事件建议取证、残留批量选择、分组实体不对应、Case时间顺序、事件扩充后的相似计数。

Case列表增量最终限定**ACCEPT，0项必须修**：12案事件/告警引用、原两案成员、优先级边界、筛选集、日期、列拖动应用/取消、旧localStorage补齐及原有页面渲染通过。拖动顺序由本地合同检查，未作真实浏览器拖动专项。

JavaScript和预览服务器语法、静态HTTP及OpenSpec检查见change audit。未做移动端专项、逐像素比较或实际下载文件落盘核验。无截图的核心区域按文字和工作区样式实现，不能称逐像素复刻。

无后端API、真实账号、模型或安全响应调用，无生产配置修改、部署或Git提交/推送。现有其他未提交材料保留。

## 后续逐项适配：告警筛选行

按用户补图，严重程度/处理状态快捷筛选放在“添加筛选”这一行，上方刷新/导出/时间/搜索/自定义列保持。沿用现有高/中/低及New/In progress/Resolved字段，快捷项和原筛选弹窗双向联动，各组可单独清除，重置全部同时清搜索，筛选变化回第一页。浏览器7项观察：高31条、高+新建15条、弹窗同步值、弹窗改中+已解决后4条、重置51条、回第一页、与PowerShell搜索组合2条；错误日志为空。独立本地材料为`alert-quick-filters.json`与`alert-quick-filters.png`，不并入先前43项观察。JS语法与diff检查通过。

## 后续逐项适配：告警主表列

本轮只调整 `#/alerts` 主表。依据 AiSOC Alert 的 status/event_time 语义，保留处理状态；调查状态和分类列移除，类别保留；首次/末次活动改为一个告警时间。旧 Mock 没有 event_time 时，仅在主表投影用 first 样例值。详情和管理中的调查/分类不变，事件及 Case 内嵌表继续原12列。

浏览器10项直接观察保存在 `.local/verification/security-pages-replica/alert-table-columns.json`，截图为 `alert-table-columns.png`：主表/列设置均9列；发生时间升降序可用；UTC+08:00 的08:40–09:00筛得5条，叠加进行中得2条；实际下载CSV为9列2行，时间为对应UTC的00:40/01:00；事件及Case内嵌表仍12列；错误日志为空。此批核验了导出文件正文，不改变前批“未落盘核验”的历史限制。JS语法通过。独审及归档结果见本批 change `adapt-alert-table-columns`。

## 后续逐项适配：主表所选告警管理

用户随后追加删除选中告警后管理弹窗的分类。顶部“管理告警”和表内“管理所选”均仅保留状态、分配给、评论，保存不修改已有分类。详情与其他工作区管理保持。浏览器4项观察：两个入口均3个字段；选择不同状态/负责人后取消，原值仍为进行中/未分配；无错误日志。材料为同目录 `alert-management.json/png`。

未参与实现者 prototype_end_review 本地 Node VM 窄审限定 ACCEPT/0必须修：保存不改分类（额外注入分类字段也忽略）、取消不改数据/活动、详情及内嵌管理原样。JS语法通过；无真实服务、模型、部署或提交。

## 后续逐项适配：分配给我

主告警筛选行增加“全部告警 / 分配给我”，当前用户为示例账号 Alex Wilber。复用负责人条件，与原弹窗双向同步；当前用户不重复显示chip，其他负责人仍显示条件；切换回第一页，全部告警仅清owner。

浏览器8项观察保存为同目录 `alert-owner-filter.json/png`：第二页选我的回第一页、12条；我的+高+新建3条；全部仅清负责人后15条；重置51条；原弹窗同步Alex；Megan6条并显示chip且两个快捷项均不选中；我的+Identity搜索3条；无错误日志。JS语法通过。

未参与实现者 prototype_end_review 本地Node VM独审限定ACCEPT/0必须修，验证组合、清除、页码与弹窗同步。无后端、账号接入、模型或部署。

## 告警详情融合与逐项修订

来源：只读原项目 AlertDetailView.tsx、ExplainDrawer.tsx，和 deploy/aisoc20/AutomaticInvestigation.tsx；后端未改。新增 alert-detail.js，现有浅色风格下迁移四页签及Overview功能。保留事件/Case关联，去触发式Explain和重复原始描述/跳转入口；预生成说明保留。原四选项反馈卡片恢复选择/高亮/保存。Case新建和已有分模式，已有隐藏新名称、按活跃时间默认7条、支持名称/ID检索；调查按钮移至管理左侧。时间线聚焦发生/检测/入库/启动/取证/分配/关闭，工具过程在跟踪。

浏览器材料：`.local/verification/security-pages-replica/alert-detail-merge.json`，截图 alert-detail-overview.png、alert-detail-tracking.png、alert-verdict-cards.png、alert-lifecycle-timeline.png。验证四页签、原始JSON、步骤展开、反馈保存刷新保留、已有关联Case调查产生等待/未交付Run、资产Windows域控筛选17条、卡片未选禁用/选后启用、已有模式7条且名称不可见、17420搜索1条、新建模式名称可见且搜索隐藏、生命周期呈现。JS语法通过，浏览器错误为空；顶部调查按钮实测进入跟踪并显示等待/尚未交付、0步骤及未记录用量。

测试在当前本地数据留下该告警人工反馈及等待中的Run；没有真实模型或服务调用。界面按用户要求移除Mock/演示提示，不改变上述实现边界。

### 本轮最终逐项修订

最终页签：概况、时间线、原始数据、响应；独立置信度/交接卡片已删。Case已改弹窗，已有Case创建按钮禁用且处理器同样拒绝，未关联名称默认告警描述；搜索覆盖全部Case，初始按最近活跃7条。响应详情在自动过程上方，建议/审批/执行分别显示。时间线倒序到秒；相关告警每行有等级及时间。新增告警 alert-unassigned-case-001 属于262144，无Case/Run；Node直接核52条告警均有有效事件。

新增浏览器观察附在同一JSON：Case弹窗7条/已关联禁用新建、未关联默认描述、新告警关联/无Run、倒序、相关告警等级时间。截图新增 alert-case-picker.png、alert-response.png、alert-no-case.png、alert-timeline-desc.png、alert-related-metadata.png。实际反馈测试保留记录；早期截图中的文案/常驻Case表单代表迭代阶段，以最终修订为准。

独立审阅发现并修复store重置引用、旧资产角色迁移以及未打开详情前分配关闭历史缺失；最后一项现先建立原始材料再记录真实操作时点，不再用旧last补造用户操作。前端源文件语法及局部直接验证通过。

最新定位调整：无 Case 告警 `alert-unassigned-case-001`（Web 服务器出现异常外联）发生时间为北京时间 2026-10-24 19:59:57；主告警列表默认按告警时间倒序。浏览器验证第一行显示该告警、19:59，详情侧栏显示事件 262144、未关联 Case。旧样例时间定向升级保留反馈/Case/Run，截图 `.local/verification/security-pages-replica/alert-newest-first.png`。

### 告警主表排序与固定列宽

2026-10-24：业务列顺序为告警名称、严重程度、告警时间、资产标签、处理状态、类别、检测源、受影响资产、负责人。仅严重程度/告警时间可排序；未激活 ↕，升序 ↑，降序 ↓，aria-sort 同步。默认时间降序保持。

浏览器实测默认、等级升序/降序、时间升序/降序五轮，表头宽度始终为 40/360/112/140/150/112/150/180/160/150px（首项为勾选列）；对应第一行分别为新外联、高低切换、最早/最新告警，符合预期。自定义列隐藏资产标签后其余列顺序/宽度保持，刷新恢复默认。超出可视区水平滚动，长名称省略并保留 title。直接证据：`.local/verification/security-pages-replica/alert-sorting-widths.json`、`alert-sorting-fixed.png`。JS语法与 OpenSpec strict 通过；其他工作区表头/排序保持原实现。

### 告警预览、Case 页签与资产入口

2026-10-24：移除告警侧栏“查看相似告警”，完整详情的相关告警/相似历史继续保留。Case 弹框采用“关联已有 Case / 新建 Case”互斥页签，每次打开默认关联已有；已关联告警禁用新建，提交校验保持。未关联的新建页仅名称输入，默认当前告警描述；已有页保留最近七条、搜索和已选提示。

浏览器核：新建页隐藏搜索列表，切回关联已有后恢复列表；已关联告警新建 tab disabled；只切换/取消，未创建或关联测试 Case。主告警表、告警侧栏与完整详情的资产为链接；点击侧栏 cont-adrianbrad 后到 /assets/d1，正文只有“资产详情 · cont-adrianbrad”大标题。其他工作区实体预览保持。截图：`.local/verification/security-pages-replica/case-existing-tab.png`、`case-new-tab.png`、`asset-placeholder.png`。JS 语法与 change strict 通过。

本轮最终追加：告警侧栏仅保留概览，原相关事件/处理记录入口和内容分支已删除；告警状态区改为告警信息，显示 ID、告警时间、负责人、检测源、资产标签，移除分类和首次活动文案。顶部等级/状态/类别保持。浏览器可见树及截图 `alert-preview-overview-only.png` 核验，完整详情四页签未改。
