# AiSOC 安全运营前端原型

独立纯前端模块，参考 Microsoft Learn 的告警、事件、Case 页面。使用文档示例及自拟 Mock 数据，不需要账号或后端。

```bash
cd /Users/lychee/Documents/project/socai2/prototypes/security-pages
python3 serve.py
```

打开 <http://127.0.0.1:4173/>。可以用 `--port 4174` 指定其他本地端口；也可以 `npm start`。无需安装第三方包。静态服务器只监听 `127.0.0.1`。

## 页面入口

- `#/alerts`：告警列表；详情抽屉和单独详情页。
- `#/incidents`：事件列表；行预览摘要，名称进入详情。
- `#/incidents/262144/attack`：多阶段事件详情及攻击故事。
- `#/cases`：Case 列表；按官方 Prioritize incident cases 的列表及列设置截图实现。
- `#/cases/17420/overview`：具体 Case 工作区。

Case列表包含 Incident / Generic 名称、四个统计卡片、工具栏、筛选集和案件表格；Generic、创建、设置及未有正文说明的相似Case仅保留入口名称。

顶部使用本地 AiSOC 盾牌 SVG。左侧“告警和事件”分为两个入口，Case 在“案件管理”分组；其他模块只展示名称。

## 数据与交互

初始为51条告警、12个事件、12个Case。来源字段保留微软产品示例；账号、设备、记录及关系为文档示例和 Mock 的组合。

支持搜索、筛选、分页、排序、自定义列、CSV导出、告警管理、事件单条/批量管理、图谱联动/筛选/分组/回放/潜在影响、证据模拟审批、Case列表、筛选集保存/应用、Case告警移动和评论。事件负责人变更同步其关联告警；解决事件需要说明并同步解决活跃告警。

告警列表在“添加筛选”同一行提供严重程度（全部、高、中、低）、处理状态（全部、新建、进行中、已解决）以及“全部告警 / 分配给我”的快捷筛选，和原筛选弹窗、搜索共用条件；切换时回到第一页。“我”沿用页面示例账号 Alex Wilber；全部告警只清负责人条件，重置全部清除所有筛选。

告警主表保留处理状态，移除调查状态和分类列，保留类别；首次/末次活动收敛为“告警时间”。列设置、时间排序/筛选及 CSV 使用同一发生时间字段 `event_time`；旧 Mock 的 `first` 仅作为演示发生时间值，不定义后端回退逻辑。事件/Case 内嵌告警表及详情保持原样。

主列表选中告警后的“管理告警 / 管理所选”仅提供状态、分配给、评论；保存保留已有分类值。详情及其他工作区的管理表单保持原样。

状态使用本浏览器的 `localStorage` 保存；左下角“重置演示”恢复初始数据。隔离、审批等操作只更新演示记录。没有API请求、身份认证、真实模型或真实响应操作。

## 文件与检查

- `index.html`、`styles.css`：页面框架与样式。
- `data.js`：可替换的 Mock 数据。
- `icons.js`、`assets/aisoc-mark.svg`：本地图标。
- `app.js`：视图、路由与本地交互。
- `serve.py`：只提供静态文件的预览服务器。

`npm run check`检查JavaScript语法。功能及来源见[页面复刻清单](../../docs/design/security-pages-replica.md)，实际验证见[本轮回执](../../docs/design/security-pages-replica-verification.md)。

## 告警详情融合

详情提供概况、时间线、原始数据、跟踪四页签。原AiSOC的置信度/依据、属性、MITRE、实体/IOC、Case和人工反馈融合到浅色页面；Explain作为预生成内容出现在“发生了什么”。事件关联保留，Case关联按成员关系显示。

Case新建与已有分模式：已有模式不显示新名称，默认最近活跃7条，支持名称/ID搜索；顶部发起调查使用当前选择。反馈为四张单选卡片，选择后可保存并复核历史候选。跟踪区分执行状态/完整性、停止原因、步骤输入输出、工具返回、建议和报告；时间线展示业务生命周期。

主列表“资产标签”来自关联资产的tags，合并去重，筛选与导出一致；使用Windows域控/文件服务器/Web服务器等样例。根据用户要求去掉页面上的Mock/演示提示，底层仍为本地数据，无模型调用与后端连接。

最终逐项调整：四页签为概况/时间线/原始数据/响应。概况删除独立置信度、处置交接、原始描述及重复跳转；顶部置信度保留。Case卡片只显示关联与按钮，选择在弹窗进行；已有Case禁用新建，无Case新名称默认告警描述。响应顶部展示简短建议/目标/审批/执行结果，下方自动处理过程保持。时间线最新在上且显示秒，相关告警保留等级和时间。新增Web服务器异常外联告警 `alert-unassigned-case-001`，属于事件262144、无Case、无自动Run；初始告警总数52。

最新定位调整：无 Case 告警 `alert-unassigned-case-001`（Web 服务器出现异常外联）发生时间为北京时间 2026-10-24 19:59:57；主告警列表默认按告警时间倒序。浏览器验证第一行显示该告警、19:59，详情侧栏显示事件 262144、未关联 Case。旧样例时间定向升级保留反馈/Case/Run，截图 `.local/verification/security-pages-replica/alert-newest-first.png`。


## 2026-10-25 实际结果接入

原52条样例与全部样式保持，追加21从Kafka实际处理的6条告警，初始总数58。`replayed-alerts.js`由`tools/testdata/export_alert_ui.py`从本批只读PG及实际Explain返回生成；无后端凭据、模型prompt或实时数据库连接。Explain内容是已调用接口的真实返回，本批为无API key的模板兜底，不是LLM结果。详情四页签可查看实际评分、时间、Run、部分完成与原始字段。

资产关联/负责人在数据库中为空：标签留空，原始主机/账户展示为文本，不伪造资产库详情链接。真实事件只展示其ID，事件/Case数据仍为原设计样例。所有修改按钮保持浏览器本地行为，不写回21，也不重复调用模型。相关告警检索仅覆盖当前已加载的记录。

运行`node --test tests/replayed-alerts.test.cjs`检查原样例不覆盖、6条×4页签与真实字段；从仓库根运行`python3 -m unittest discover -s tools/testdata/tests -p test_export_alert_ui.py`检查投影语义。完整来源、实际差异及限制见[清理与重跑回执](../../docs/operations/alert-reset-replay-20261025.md)。

## 2026-10-25 事件与Case对齐

[微软产品、功能与交互逻辑](../../docs/design/microsoft-incident-case-analysis.md)为本轮分析入口。新增`workspace-model.js`、`workspace-view.js`及`workspace.css`；图谱关系有来源、展开关联不改成员、潜在路径独立；Case有任务和结案管理，关闭不改告警，调查按成员告警计算。`npm test`包含范围、来源、状态与任务测试。本轮排除20，不接业务后端，告警原呈现和数据保持。
