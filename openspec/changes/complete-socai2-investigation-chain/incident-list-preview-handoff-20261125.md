# 8181 事件列表与预览交接

2026-11-25，事件列表与预览的实现和前端直接验证已完成，交统筹独审。第一步的范围按产品基准与通过条件执行。 [事件阶段验收计划](incident-integration-acceptance-plan-20261125.md#产品基准与当前先做的页面修改)

## 4173 对照结果

| 4173 位置 | 8181 实现 |
| --- | --- |
| `incidentQueue()` | 「告警和事件 / 事件」面包屑、标题、说明和右侧「管理事件」齐备。两张卡为「处理中的事件」「队列压缩」，同排右侧为活跃事件、待分配、24h 有新告警、高严重程度。状态统计取事件列表的 `overall_stats`，队列压缩单独读取归并摘要。 |
| `table()` 工具栏和筛选行 | 刷新、导出、复制列表链接、紧凑日期按钮、管理所选、数量、搜索和自定义列按原型编排。独立筛选行提供添加、查看和移除条件及「重置全部」。状态、等级、负责人按现有合同查询。是空结果、尚未供数还是读取失败，由现行响应决定。 |
| `incidentQueue()` 列定义 | 默认顺序为事件名称、严重程度、状态、负责人、涉及资产、活跃 / 全部告警、最近更新时间。五个可选列为事件 ID、优先级、资产标签、分类、服务 / 检测源。预览图标在名称之前。事件 ID 可复制，优先级可开摘要。 |
| `table()` 行点击与事件摘要 | 行和预览按钮开摘要，名称进事件页。摘要显示严重程度、状态、优先级、说明、事件信息、解决说明及关联告警，资产仅在该摘要内用现有资产读取。关联告警以 `items[].id` 为准，兼容 `alert_id`，先开既有告警预览，再可进入告警页。摘要「管理事件」的目标是当前事件，列表批量管理的目标是明确勾选的事件。 |
| `exportTable()` | 唯一导出入口发送当前筛选和可导出的可见字段。已经移除「导出所选」，导出请求没有勾选 ID 或分页参数。可导出字段的范围见下表。 |

原型结构取自 `incidentQueue()`、通用 `table()`、筛选弹层、事件摘要及对应样式。 [4173 结构](../../../prototypes/security-pages-v2/app.js) · [4173 样式](../../../prototypes/security-pages-v2/styles.css)

## 实际改动

8181 监听进程的工作目录与 `/Users/lychee/Projects/SpiritHub-web-8181/web` 一致。工作树为 `codex/spirithub-4173`，基准 HEAD 为 `bb368df`。

| 相对于 SpiritHub 工作树的文件 | 改动 |
| --- | --- |
| `web/src/features/security-events/IncidentWorkbenchList.tsx` | 页头、统计、工具栏、筛选行、列和点击分流。 |
| `web/src/features/security-events/IncidentPreview.tsx` | 事件摘要、单条管理入口和关联告警预览。 |
| `web/src/features/security-events/incidentListApi.ts` | 事件专属列表、归并摘要、现有导出的 GET 参数适配。 |
| `web/src/features/security-events/incident-workbench.css` | 事件列表和预览样式，事件专用选列弹层高度。 |
| `web/src/features/security-events/IncidentWorkbench.test.tsx` | 更新受影响的列表用例，沿用原详情用例。 |
| `web/src/shared/ui/ListFilterBar.tsx` | 增加可选的清除按钮文案参数，事件页使用「重置全部」。 |
| `web/src/shared/ui/ColumnChooser.tsx` | 增加可选的弹层样式类，事件页用它把重置按钮留在可视区。 |

## 直接验证与边界

| 检查 | 结果 |
| --- | --- |
| OpenSpec | `openspec validate complete-socai2-investigation-chain --strict --no-interactive` 通过。 |
| 类型和定向用例 | `npm run typecheck` 通过。`npm test -- src/features/security-events/IncidentWorkbench.test.tsx` 通过 5 项。受控用例核对列表请求、筛选与整组导出参数、列重置、行与名称分流、摘要单条管理、现有成员 ID 到告警摘要及详情链接。管理用例止于打开和取消表单。 |
| 8181 实际结构 | 1280 × 720 的已登录浏览器用空结果核对页头、两卡及同排右侧四指标、七列默认顺序、工具栏和独立筛选行。实测搜索、添加和移除状态条件、日期应用与移除、增加可选列和恢复默认列。最近 7 天仅在选择后写入实际有时区边界，日期筛选标签同步显示。 |
| 自定义列初次失败与复验 | 初次事件 ID 仍在实际表头。现场定位到选列弹层上翻时把重置按钮挤出视口。限制事件弹层高度后，按钮可点击，表头恢复默认七列。 |
| 本轮数据与操作 | 8181 列表显示正常空态，队列压缩显示读取失败。摘要有值、成员预览及详情入口正例来自受控前端用例。真实数据验收留待接口阶段，届时仅使用原十条 OCSF 的自然结果。本轮业务写入为 0。 |

初次测试诊断回显了一条受控夹具标题，原日志留在本机，后续诊断只读取工程结果。 [结构验证与文件指纹](../../../.local/validation/incident-list-preview-ui-20261125-01/verification.json) · [定向测试日志](../../../.local/validation/incident-list-preview-ui-20261125-01/incident-vitest.log) · [类型检查日志](../../../.local/validation/incident-list-preview-ui-20261125-01/typecheck.log)

## 待接字段与流程

| 字段或能力 | 当下页面与待核事项 |
| --- | --- |
| 列表资产、资产标签、分类、服务 / 检测源 | 列保留并显示「未提供」。事件列表缺对应返回值。摘要的资产为当前事件的实际匹配读取。 |
| 活跃 / 全部告警 | `derived.member_count` 提供全部告警数，活跃成员数待供。 |
| 最近更新时间和日期 | 最近更新时间读 `derived.updated_at`。现行日期范围按任一成员告警的发生时间匹配，独立于更新时间列。更新时间排序待合同支持，页面目前开放现行严重程度排序。 |
| 检测来源、资产标签、最低优先级条件 | 筛选菜单保留，当前显示「该筛选暂不可用」。对应条件待事件列表合同支持。 |
| 队列压缩 | 调查 HTTP 有 `/incidents/grouping-summary`，8181 实测显示读取失败。平台转发及真实统计的读回待接口阶段核对。 |
| 导出列 | 现行合同可导出可见的事件名称、严重程度、状态、负责人、全部成员数、事件 ID、优先级。活跃数、资产及资产标签、分类、服务 / 检测源、`derived.updated_at` 待导出合同支持。正例的完整命中范围和 CSV 内容待接口阶段验收。 |

本步结束于列表及预览交接。统筹已完成[限定独审](../../../docs/operations/evidence/incident-list-preview-ui-20261125-01/independent-review.json)：源码对照和前端证据复核通过，7份当前文件指纹与验收版本一致；统筹未重复浏览器实跑，真实有值预览及数据保存不在通过范围。下一步按计划推进事件详情，事件整体任务保持未完成。
