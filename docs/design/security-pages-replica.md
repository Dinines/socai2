# 告警、事件与 Case 页面复刻：功能清单

更新：2026-10-24。分支：`codex/security-pages-replica`。当前阶段：**三组纯前端原型已实现，浏览器直接核验及结束独审完成**。启动入口见[原型说明](../../prototypes/security-pages/README.md)，实际检查与范围见[验证回执](security-pages-replica-verification.md)。

用户要求对照官方文档的图片和正文复刻前三组页面，数据全部可以 mock，不按当前产品能提供的数据裁剪。事件页按用户新指定链接替换原 Sentinel 页面。范围集中在告警、事件和 Case；全局侧边栏的其他模块只保留名称，不实现对应页面。

## 1. 三组参考

| 页面组 | 官方正文 | 复刻重点 |
| --- | --- | --- |
| A 告警 | [Investigate alerts](https://learn.microsoft.com/en-us/defender-xdr/investigate-alerts) | 列表、告警详情、告警管理 |
| I 事件 | [Manage incidents：列表](https://learn.microsoft.com/en-us/defender-xdr/manage-incidents) · [Investigate incidents：详情，用户指定](https://learn.microsoft.com/en-us/defender-xdr/investigate-incidents) | 多事件队列、摘要预览、单条/批量管理、攻击故事、告警/资产/调查/证据/活动、概览 |
| C Case | [Prioritize incident cases：列表](https://learn.microsoft.com/en-us/defender-xdr/prioritize-incident-cases) · [Investigate incident cases](https://learn.microsoft.com/en-us/defender-xdr/investigate-incident-cases) | 案件概览、内部目录、调查材料与协作资料 |

I 被微软标注为 Legacy，C 被标注为 Preview。两组按各自图片保留：事件是横向页签工作台，Case 是内部左侧目录；不把它们混成微软已有的同一页面。原 Sentinel Azure 门户页面不再作为本轮主参考。

**核对方法：** 图片确定布局、信息位置、控件及面板关系；正文补充点击、展开、筛选和跳转。下表记录实现范围，直接检查结果以验证回执为准。文档没有完整截图的区域明确注明，不能宣称逐像素复刻。

## 2. A：告警列表与详情

图片结构：Defender 顶栏及全局导航 → 列表工具栏 → 筛选条 → 密集表格；告警详情及管理使用右侧面板。详情正文分为“发生了什么、已采取动作、相关事件”，并显示属性和描述。

| 编号 | 核心功能 | 本地 mock 交互 |
| --- | --- | --- |
| A01 | 列表：名称、标签、等级、调查状态、处理状态、分类、检测源、产品、资产、首末活动时间 | 点选告警、排序、分页、勾选 |
| A02 | 标题/ID搜索、日期范围、条件筛选、结果数量 | 条件实际改变数据；可清空、可显示无结果 |
| A03 | 自定义列、导出、批量选择 | 切换列，导出当前 mock 结果，批量管理 |
| A04 | 告警详情：来源事实、过程、关联实体、动作、相关事件和属性 | 展开过程及实体，查看记录，复制ID |
| A05 | 关联事件、相似告警、既往分类与建议 | 跳到事件，打开相似告警并查看建议 |
| A06 | Manage alert：状态、负责人、分类、评论 | 保存后同步列表与详情；取消不保存 |

状态与分类分列：状态为 New / In progress / Resolved；分类包括未设置、真实威胁、信息性或预期活动、误报。前端只保存本地状态。

代表原图：

- [列表](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-alerts/alerts-page-defender-small.png) · [筛选](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-alerts/alert-filters-small.png)
- [详情抽屉](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-alerts/alerts-ss-alerts-main.png) · [管理表单](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-alerts/alerts-ss-alerts-manage.png)

详情原图实际是事件工作区上的告警抽屉，独立告警页需结合正文和管理图补齐。告警调优/规则配置不展开，相关入口只保留名称。

## 3. I：事件列表与调查工作台

按用户补充的PDF第600页，事件入口先显示多事件列表，参考[队列原图](https://learn.microsoft.com/en-us/defender-xdr/media/manage-incidents/incidents-queue.png)。顶部保留攻击中断和队列压缩统计，表格显示优先级、标签、严重程度、状态、分类、负责人、关联告警、资产、产品及更新时间；支持搜索、筛选、日期范围、排序、分页、列设置、导出和复制筛选链接。行预览留在列表，标题进入详情。单条/批量管理可改负责人、分类、标签等；解决时需要说明，并同步关联活跃告警，负责人变更同步关联告警。这些均只修改浏览器内的mock记录。

图片结构：标题、状态/等级/负责人/标签 → 横向页签。Attack story 是“左侧告警序列 / 中央关系图 / 右侧事件或实体详情”；Summary 是分栏卡片，其他页签以表格为主。

| 编号 | 核心区域 | 本地 mock 交互 |
| --- | --- | --- |
| I01 | 事件头部与详情：ID、优先级及原因、等级、状态、负责人、分类、时间、描述 | 摘要抽屉、管理状态及负责人 |
| I02 | Attack story：告警序列、实体关系、时间回放、实体详情 | 点告警/节点联动，播放/暂停，缩放及重置 |
| I03 | 图谱筛选、布局、相似节点分组、实体类型显隐 | 应用/清空条件、切换分组及布局；支持空图 |
| I04 | Blast radius：潜在影响路径、目标列表及路径详情 | 切换影响图，点选目标和路径；支持无路径 |
| I05 | Alerts：事件内告警、来源、实体、关联理由及时间 | 搜索排序，查看上下文告警详情 |
| I06 | Activities：人工/自动活动、执行人、目标、触发及结果 | 筛选并展开活动元数据 |
| I07 | Assets：设备、用户、邮箱、应用和云资源 | 类型切换、数量、列表、资产详情 |
| I08 | Investigations：调查记录、调查/处置状态及关联 | 列表到调查详情，查看过程；支持0条状态 |
| I09 | Evidence and Response：证据、判定及处置状态 | 类型筛选、详情、模拟批准/拒绝待审批动作 |
| I10 | Summary：战术分布、影响范围、告警、证据、事件属性 | 点统计定位对应页签 |
| I11 | Similar incidents、Recommended actions | 打开相似事件，查看建议及本地演示处理状态 |

Recommended actions 在原图/正文中出现，保留为事件内页签。实际动作、待审批动作与建议分开；Blast radius 代表可能路径，不当成已发生攻击。Go hunt、Playbook、Copilot等外围入口保留名称，不开发独立查询平台、自动化或对话助手。

代表原图：

- [Summary](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-incidents/incident-summary.png) · [攻击故事回放动图](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-incidents/play-alert-attack-story.gif) · [实体详情动图](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-incidents/review-entity-details-attack-story.gif)
- [影响范围](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-incidents/blast-radius-graph.png) · [告警](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-incidents/incident-page-alerts-small.png) · [活动](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-incidents/incident-activities-tab.png)
- [资产](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-incidents/incident-assets-tab-small.png) · [调查及空态](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-incidents/incident-investigationspage-small.png) · [证据与响应](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-incidents/incidents-evidenceresponse-small.png) · [审批](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-incidents/evidence-approve-small.png)

## 4. C：Case 列表与工作区

按用户补充要求核对官方Prioritize incident cases正文及[列表原图](https://learn.microsoft.com/en-us/defender-xdr/media/prioritize-incident-cases/prioritize-incident-cases-priority-score.png)、[列设置原图](https://learn.microsoft.com/en-us/defender-xdr/media/prioritize-incident-cases/prioritize-incident-cases-customize-columns.png)。`#/cases`显示案件列表，保留Incident / Generic名称、四个统计卡片、创建/刷新/自动刷新/导出工具栏、筛选集、搜索、时间范围、自定义列和案件表格。核心列表支持预览、标题进入详情、搜索筛选、排序分页、保存并复用筛选集、日期和列显隐/顺序；优先级分段严格为>85、15–85、<15。Generic、创建和设置不展开对应模块。

图片结构：全局导航 → 案件头部 → Case内部左侧目录 → 右侧内容。头部显示ID/标题、优先级、等级、状态、负责人及关键资产标签；内部目录属于核心功能，需要切换内容。

| 编号 | 核心区域 | 本地 mock 交互 |
| --- | --- | --- |
| C01 | Overview：优先级、案件资料、描述、创建/更新时间 | 展开资料、修改状态及负责人 |
| C02 | Summary by Copilot | 预写摘要、更新时间、折叠及反馈；不调用模型 |
| C03 | Attack graph | 告警与节点联动、筛选、布局/分组、节点详情及影响范围 |
| C04 | Artifacts / Alerts | 搜索筛选、列设置、告警详情、模拟移到另一Case |
| C05 | Assets：设备、用户、邮箱、应用、云资源、AI代理 | 按类型查看数量、搜索/导出、资产详情 |
| C06 | Investigations、Evidence | 查看调查和处置进展、证据与判定、待处理及空态 |
| C07 | Activities | 查看分派、状态、人工/自动操作和评论变更 |
| C08 | Comments & attachments | 本地评论、查看和下载预置示例附件 |
| C09 | Similar cases | 仅保留原图目录名称，不自行设计列表、相似理由或算法 |

原文只有四张完整/局部图：摘要、攻击图、告警、资产。调查、证据、活动和附件有文字说明，已按工作区样式补齐。`Similar cases`仅在目录图中可见，按用户“不要自己发挥”的要求撤除自拟列表及原因，仅留目录名称。案件任务/关闭等更深管理在其他链接，本轮不因此扩展完整案件管理系统。

代表原图：

- [摘要卡片](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-incident-cases/investigate-incident-cases-summary-by-copilot.png) · [攻击图](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-incident-cases/investigate-incident-cases-attack-story.png)
- [告警：案件框架](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-incident-cases/investigate-incident-cases-alerts.png) · [资产：案件框架与类型导航](https://learn.microsoft.com/en-us/defender-xdr/media/investigate-incident-cases/investigate-incident-cases-assets.png)

## 5. 范围与演示约定

| 范围 | 实现约定 |
| --- | --- |
| 三个主入口 | 告警、事件、Case；详情/页签/抽屉仍归属各自主入口 |
| 全局侧边栏 | “告警和事件”分组下分开显示告警、事件；Cases放在“案件管理”。其他模块保留名称及图标 |
| 顶栏品牌 | 按用户要求替换为AiSOC和本地蓝色盾牌SVG，浏览器标题及favicon同步 |
| 核心内部导航 | 事件横向页签和Case内部目录实际切换内容；告警/资产/证据点击可打开详情 |
| 外围动作 | 调优、Playbook、Go hunt、完整Copilot助手等只保留名称，明确为原型范围外 |
| 样式 | 白色工作区、紧凑表格、细分隔线、蓝色选中态，按选定原图分别复刻 |
| 数据 | 预置一个多阶段攻击场景贯穿三组页面，并提供不同状态及空态；不对接现有后端 |
| 一致性 | 复用告警/实体/事件/Case ID；本地修改后对应列表、详情与计数同步 |
| 实际可点 | 搜索、筛选、排序、分页、列设置、抽屉、页签、管理、模拟审批、评论、mock CSV导出 |
| 图谱及摘要 | 预置节点、边、时间和影响路径；摘要预写，所有动作只更新mock数据 |

实现位于`prototypes/security-pages/`，无需第三方依赖或构建步骤，Python仅提供loopback静态文件预览。初始数据为51条告警、12个事件、12个Case；本地修改保存在localStorage，可通过“重置演示”恢复。

## 6. 本轮核验记录

2026-10-24已读取三份官方正文，提取公开图片索引，并在浏览器查看告警列表/详情/管理、事件概览/攻击故事/活动/证据、Case四张代表图。未操作真实微软控制台。

最初阶段只整理功能并下载PDF；随后按用户授权完成前端。已添加前端规格，浏览器留存43项检查观察及五张代表截图；未参与实现者源码/本地Node VM审阅限定ACCEPT，0项剩余必须修。具体检查和限制见[验证回执](security-pages-replica-verification.md)。未改后端、生产配置或其他既有未提交工作；无Git提交/推送或部署。

## 7. 整本官方 PDF（2026-10-24已下载）

用户指出可以下载整本文档，已使用左侧 Download PDF 对应的[官方整本下载入口](https://learn.microsoft.com/pdf?url=https%3A%2F%2Flearn.microsoft.com%2Fen-us%2Fdefender-xdr%2Ftoc.json)保存本地参考：[Microsoft Defender XDR 完整PDF](../../.local/references/microsoft-defender-xdr/microsoft-defender-xdr.pdf)。该文件为完整XDR文档集，下载不扩大本轮三个页面的实现范围。

| 核对项 | 实际结果 |
| --- | --- |
| 文件 | 161,192,410字节，约153.7MiB，共2254页 |
| 书签 | 466个，已定位下列三个章节并核对起始页标题 |
| Case | PDF第388页：Investigate incident cases |
| 告警 | PDF第476页：Investigate alerts |
| 事件列表 | PDF第600页：Manage incidents in Microsoft Defender |
| 事件 | PDF第639页：Investigate incidents |
| 元数据生成时间 | 2026-10-17 00:07:29，Asia/Shanghai；这是官方PDF快照，页面复刻仍对照已选网页及原图 |
| 留存 | `.local/references/microsoft-defender-xdr/download-manifest.json`保存下载地址、时间、字节数、SHA-256及章节页码；PDF与渲染核验材料留本地，不纳入Git |

已核PDF可解析，抽查首页和事件章节首页；未逐页审读2254页。单独下载TOC JSON的请求遇到TLS连接错误，未作为成功材料；章节索引来自已下载PDF书签。前端实现是后续用户授权的独立阶段。
