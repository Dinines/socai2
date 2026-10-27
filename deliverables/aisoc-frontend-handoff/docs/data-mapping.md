# 告警页面与数据库字段

[返回导航](../guide.html) · [完整讨论参考](alert-ui-data-contract.html) · [数据文件说明](../data/README.html)

本页整理截至 2026-10-25 已确认的对接口径。数据库为 21 的 PostgreSQL `aisoc`，schema `public`，以 socai2 当前已落地流程为准。下面的字段是后台取数依据；本交接包运行时只读本地 JS 数据。事件与 Case 页的后台字段不在本次对接范围。

<a id="list"></a>
## 告警列表九列

| 顺序 / 页面元素 | 数据库表与字段 | 展示含义 / 转换 | 当前待补 |
| --- | --- | --- | --- |
| 1 告警名称 | `public.alerts.title` | 原告警标题 | 已有 |
| 2 严重程度 | `public.alerts.severity` | Critical / High → 高；Medium → 中；Low / Inform（含 info、informational）→ 低 | 已有；仅此列与告警时间可排序 |
| 3 告警时间 | `public.alerts.event_time` | 发生时间；北京时间展示、原始精度排序；不能拿 created_at 代替 | 已有 |
| 4 资产标签 | `public.alert_asset_correlations` 关联 `public.assets.tags` | 关联资产的标签，不能使用 alerts.tags；具体资产关联由后端处理 | 本批 6 条均无资产关联，留空 |
| 5 处理状态 | `public.alerts.status` + 已实际启动调查的记录 | 见下方状态映射；负责人和调查执行状态是不同维度 | 后端需统一映射与调查启动依据 |
| 6 类别 | `public.alerts.mitre_tactics` | 展示战术标签；不取 alerts.category 或技术编号冒充战术 | 已有；本批落库全部为 Execution，照实展示 |
| 7 检测源 | `public.alerts.enrichment_data.socai2_fusion.identity.source` | 采集送入告警的来源 / 厂商标识；alerts 没有独立 source 列 | 本批是 showcase-security-sensor；厂商友好名称映射后续补 |
| 8 受影响资产 | `public.alert_asset_correlations.asset_id → public.assets.id/name`；告警 `entities / affected_hosts / affected_users` | 有库存关系显示资产名字；也可以显示告警中的主机 / 账户 | 本批只有原始实体，没有库存 ID；不得伪造资产详情链接 |
| 9 负责人 | `public.alerts.assigned_to_id → public.users.id` | 分配给哪个用户；同租户读取用户名 / 显示名 | 本批全空；后台后续管理分配，留“未分配” |

所有关联均需约束同一 tenant_id。页面数字和 JSON 投影不是新增数据库列。

### 处理状态的确认口径

| 原始状态 / 事实 | 页面分组 | 含义 |
| --- | --- | --- |
| new / triaging / triaged，尚未启动调查 | 新建 / 待处理（当前 UI“新建”） | 自动分诊不代表人工开始处理 |
| in_progress / investigating，或已实际启动调查 | 进行中 | 启动调查也计入进行中；仅点击按钮但启动失败不能计入 |
| resolved / closed | 完成（当前 UI“已解决”） | 告警已关闭；优先于历史调查记录 |
| 仅认领 / 分配负责人 | 原处理状态不变 | 分配不自动进入进行中 |
| Run completed，或 Graph partial | 不据此关闭告警 | 本次执行结束不等于告警处置完成 |

本批导出以同告警 Run 的 `investigation_events.kind=graph_step` 证明已进入调查；5 条原始 status=triaged 因此显示进行中，1 条 resolved 显示已解决。这是本批已存在的证据，不要求后台永久仅使用 graph_step；人工和其他调查入口也应按实际启动记录统一处理。

## 列表右侧抽屉

抽屉只保留概览。标题、等级、状态、战术、负责人、来源、告警时间沿用上表。“发生了什么”使用 `alerts.description`；受影响实体沿用实体与库存关联。所属事件取 `alerts.enrichment_data.socai2_fusion.incident_id`；业务 Case 取 `alerts.case_id`，再读取对应 Case 名称。分类已取消。

<a id="detail"></a>
## 告警完整详情

| 页面区域 | 数据来源 | 使用方式与限制 |
| --- | --- | --- |
| 名称、等级、状态、属性 | `public.alerts` 对应上表字段 | 与列表共用语义 |
| 检测置信度 | `public.alerts.confidence` | Fusion 的 0–100 分，不是 AI 分诊评分 |
| 风险评分 | `public.alerts.ai_score × 100` | 当前按 AiSOC 分诊评分展示；不能改取上游 risk_score 或 Graph confidence |
| 发生了什么 | `POST /api/v1/alerts/{alert_id}/explain` 返回 | 选用 summary、suggested_actions（title / rationale）、generated_at，按返回结构选用 contributing_events。建议动作放在同一区域；没有建议则留空。无固定“待核实事项”字段，不从自然语言强行拆字段 |
| 实体、IOC、MITRE | `alerts.entities / iocs / affected_hosts / affected_users / mitre_tactics / mitre_techniques` 与资产关联 | 原始实体不等于资产台账，不制造库存标签 |
| 所属事件 | `alerts.enrichment_data.socai2_fusion.incident_id` | 每条告警应属于事件，不与 Case / Run ID 混用 |
| Case 与调查 | 业务 `alerts.case_id` 及 Case 成员关系 | 描述创建 / 关联 / 发起调查功能；后台具体写回和调查范围后续细化。`investigation_runs.case_id` 在本批为告警拥有者 ID，不能拿它当业务 Case |
| 判定与反馈 | 现有 `alerts.disposition / ai_score` 可供初始读取 | 保留四类交互；误报或符合预期的正常 / 授权行为应关闭，其他不变。反馈写回与状态同步尚待实现，人工直接关闭另有流程待定 |
| 相关告警 | 后端按同主机取发生时间最近 7 条 | 需要等级、时间和标题；当前仅查询已加载数据 |
| 相似历史复核 | 同主机同战术最近 5 条；同一 IP / 文件哈希 IOC 最近 5 条 | 只规定功能，具体检索规则由后端实现 |
| 原始数据 | `alerts` 白名单字段、raw_event | 当前包可查保存的原始载荷；不是完整库备份 |

### 时间线与响应

时间线依据 `alerts.event_time / created_at / assigned_at / resolved_at` 和 `public.investigation_events.ts / kind / summary / payload`，最新在顶部。没有检测、取证或人工操作记录时，不按固定偏移时间造事件。

自动 Run 关联：同租户 `public.investigation_runs.raw_alert->>'id' = alerts.id::text`。读取 `investigation_runs.status / started_at / completed_at / error / total_tokens`，再按 run_id 关联 events、artifacts、aisoc_run_costs。

响应建议读取 `public.investigation_artifacts.kind=graph_result` 的 content JSON 中 proposed_actions；审批要求、目标、建议和实际执行分别表达，不能把建议写成已隔离。自动处理过程读取 events、graph_result、report_md 工件。`graph_result` 事件 payload.completion 表示完整性；工具只有 result_preview 时按摘要展示，不能宣称完整返回；本批 graph_step 只有 node。成本 unpriced 是未定价，不是费用 0。

### 一条当前实值

[Office 告警](../index.html#/alerts/4c71eec2-77da-5b81-b68a-72801d55ea24/overview)：title 为 Office启动隐藏PowerShell [DEMO-FIN-11]，severity=high，event_time=`2026-10-25T03:30:16.539577+00:00`（北京时间 11:30:16）。原 status=triaged，已有调查步骤，显示进行中。Fusion confidence=80；ai_score=0.85，风险评分85。主机 DEMO-FIN-11、账户 demo.finance；无库存关联、负责人、业务 Case。

## 有数据与待补齐的边界

6 条告警均有真实处理数据及 Incident ID，无业务 Case / 资产关联 / 负责人。5 条 Graph partial；第6条分诊关闭、未升级。Explain 本批均为 HTTP200 的模板兜底（llm_used=false），不是模型生成结论。接口调用属于之前测试记录，本交接包不会再请求。

前端写回、登录身份、分配、资产关联 / 标签、厂商名称映射、Case 操作、反馈关闭、完整人工时间线及响应审批仍需后台补齐。页面占位或演示操作不构成已完成接口的证明。具体已有 JSON 与查询见 [数据说明](../data/README.html)；完整历史讨论见 [参考文档](alert-ui-data-contract.html)。
