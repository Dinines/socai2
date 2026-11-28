# 两轮案件更新测试的前端只读交接

2026-11-27。当前先完成 M0 的模板、源标签和两段数据核验。本交接记录 8181 现有最短链及下一轮启动的最小修正方案，M0 核验后由统筹通知实施。范围是调查概览的“检查更新”入口、平台转发和原分析任务读回。资料、成员、历史、固定 Run、采用及其它概览区块沿各自已有入口。[两轮测试安排](host-context-scenario-20261126.md#2026-11-27-两轮案件更新测试) · [既有页面接口对照](case-detail-http-review-20261126.md)

## 8181 现有链路

下表的 API 路径省略 `/api/v1/socai2`。普通页面写入的现况按源码、既有 HTTP 与页面回执区分。

| 操作与页面 | 当前普通入口及取数 | 本轮边界 |
| --- | --- | --- |
| 新建 Case，`/cases` | “创建”打开“新建案件”，可跨告警/事件两个平表选择，“确认新建”发 E01 `POST /cases`，载荷为 `title, alert_ids, incident_ids, operation_key`。按 `receiving_case_id` 进入 `/cases/{case_id}/case-info`。若回执有该接收案自己的 `initial_task`，携 `?task=` 从 Q31 读实际状态与 `latest_run_id` | 创建与首轮受理身份已接正式合同。既有普通浏览器回执验到弹窗打开和取消，保存有原生 HTTP 证据。本次未提交新 Case。[列表入口](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchList.tsx:124) · [创建与导航](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseSelectionDialog.tsx:44) · [首轮任务读取](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkspaceFrame.tsx:147) |
| 加成员，Case 页头 | “添加告警 / 事件” → “确认添加”发 E08 `POST /cases/{case_id}/associations`，带两类 ID、`expected_scope_revision,operation_key`。冲突可选“读取最新范围”。回执里的接收案归属和实际添加清单决定 M2 的同案范围 | 4173 事件候选可展开成员，8181 当前用平表和服务分配回执。确认已添加、已存在及实际接收案；E03 读当前成员与显式事件。[页头](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkspaceFrame.tsx:81) · [身份守卫](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-entry-api.ts:62) |
| 范围变化，资料及概览 | 资料有采用/系统记录时，E03 给保存范围、`scope_revision_changed` 及可核差集。概览“待启动”区按旧 `pending_update`、E12 冻结成员列增减。Q36 若与 E03 范围版本不一致会提示重读 | 4173 另有“基础调查待更新”提示。8181 概览还没有受理已保存但暂未产生 Run 的后轮视图，旧人工版本比较仍可能因 Q10 工件上下文缺路由出现统一 404。资料的采用覆盖与某个 Run 的冻结输入分别核对。[资料页范围](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInfoAssessment.tsx:69) · [概览状态与比较](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigationOverview.tsx:25) · [既有 404 对照](../../../docs/operations/evidence/case-info-migration-20261127-01/http-four-page-contract-review.md:22) |
| 后轮启动，`/cases/{case_id}/overview` | “准备新一轮 / 更新待启动范围”仍发 E11 `POST /baseline/prepare`，“确认并启动”仍用 E13 `POST /runs/{run_id}/start` | 平台旧路径仍登记，现行正式上游已删除，既有核对明确缺路由 404 风险。原生现行提交已存在，8181 概览和普通平台的该 POST 均缺接线。历史同路径的 GET 已独验。[旧按钮调用](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/workbench-api.ts:54) · [正式提交](../../../services/api/investigation_http/external_routes/analysis_submissions.py:29) |
| 历史、比较及当前采用 | “调查历史 → 打开调查”或“当前调查”下拉走 Q34/Q35，固定 E12/E14。结果有 `change_summary` 或 `comparison_result_id` 时显示“认识的变化”或“查看比较对象”。资料按 E03 采用指针及保存来源查原 E14 | 已有固定轮及当前采用普通页证据。正式 `previous_run_url/comparison_result_url` 尚未接入前端，M2 按保存关联核对前后轮。手动“采用此结果”仍走旧请求载荷，缺 E63 和 `expected_review_token`，自动采用按保存指针读回。[历史页](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigationHistory.tsx:55) · [比较入口](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx:47) · [现有新结果验收](../../../docs/operations/evidence/case-capacity-live-retry-20261127-01/coordinator-browser-acceptance.json) |
| 非空 ATT&CK 源战术，案件资料右栏 | Q36 `GET /cases/{case_id}/info-summary` 的 `tactics[].{label,alert_count}`。按同案当前成员最新材料 `detection.tactics` 的每标签告警数去重。E03/Q36 `scope_revision` 一致才渲染 | 已有隔离有值证据和真实普通页空态证据。随 M1/M2 的真实源标签直接读现有柱形。[柱形组件](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInfo.tsx:181) · [原生聚合](../../../services/api/app/socai2/case_info.py:16) |

## 下一轮按钮的最小修正

### 4173 对照和本步落点

4173 在调查概览保留「当前工作」「调查安排」、案件范围、既有结果卡、人工待办和调查历史入口。8181 本步沿用这些区块和同案确认交互，把行动区接到正式后轮受理。「当前工作」读取实际分析任务和保存的 Run。「调查安排」保留真实旧 `pending_update` 的范围差异及原轮入口，以历史记录呈现。原「准备新一轮」「更新待启动范围」、按预选 Run「启动」和时间窗控件由正式受理确认取代。结果卡、待确认事项、人工任务和侧栏保持现有读取与布局。 [4173 概览结构](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:321) · [当前工作及调查安排](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-workflow.js:150) · [8181 旧操作](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigationOverview.tsx:17)

| 操作 | 正式语义和交互 | 建议实施范围 |
| --- | --- | --- |
| 检查更新 | 现有行动区的主要操作。打开同案确认，展示 E03 当前成员范围，说明由服务在实际开始时冻结并检查材料变化。有变化按正式流程处理，无变化可保存 `skipped/no_changes`。 | 统筹确认本步接入。沿现有更新权限和结案状态呈现，用本地替身验证。 |
| 再次调查 | 正式 `rerun` 是用户明确要求重新分析。使用独立的次级操作和确认说明，共用同案 POST、任务条和读回流程。 | 统筹确认同批接入。客户端沿生成合同使用两个模式，本步的直接验证不增加实际后轮。 |
| 旧轮、结果与人工待办 | 继续从 E03/E10、原 Run/Result 和现有调查历史读取。旧待启动记录标明历史状态，可查看其冻结范围并打开原轮。 | 保留只读行为和历史链接。本步集中在概览后轮入口。手工采用、关系图、报告/证据读取及整页视觉迁移各按原步骤。 |

### 提交、读回和状态

| 读取或写入 | 本步需要的合同字段 | 页面行为 |
| --- | --- | --- |
| E03 当前案 | `case.id`、`scope_revision`、`member_count`、`handling_status`、保存的 `baseline_records`。 | 在确认中提示当前范围和成员数。以原 E03、E10 和保存身份呈现现有记录。保留案内页签、来源导航和取消操作。 |
| 正式 POST | `POST /api/v1/socai2/cases/{case_id}/investigations`。请求体仅 UUID `operation_key`、`mode`。成功受理契约为 HTTP 202 和 `task_id/subject_type/subject_id/status/status_url`。 | 复用 `useOperationKey` 与现有命令提交。等待响应时禁重复确认。前端在成功响应正文校验 `task_id`、`subject_type=case`、当前 `subject_id`、`status=accepted` 及同案相对 Q31 地址，随后仅显示已受理。同案写入 `?task=` 并保留现有位置状态。 |
| Q30 分析任务目录 | `GET /cases/{case_id}/analysis-tasks`，查询仅 `limit/cursor`。按返回的 `subject_type/subject_id` 核当前案，用 `items/next_cursor` 读取，保留 `total` 的完整目录含义。 | 当前工作中读取已有受理及执行任务，按真实同案任务身份打开 Q31。显示空态须有成功读回，未读全时注明已载入范围或继续分页。 `update_state` 只描述自动更新资格，手动检查不以该字段作为受理门槛。Q30 无操作键查询，不能从最新一条推定不明提交的身份。 |
| Q31 指定任务 | `task_id/subject_type/subject_id/kind/intent/status/reason_code/next_retry_at/latest_run_id`，原 `attempts/results` 沿既有字段。 | 复用案头任务条和 `caseEntryApi.analysisTask`，以当前案、原任务和 `case_investigation` 类型为准。有确认意图时核 `intent`，直接进入任务链接时按服务返回。初次读取显示「调查任务」，既有 E01/E08 可沿已知的首轮受理语义。读回后用 `initial/check/rerun` 对应首轮调查、检查更新或再次调查。 |
| 固定 Run/Result | Q31 返回的实际 `latest_run_id`、Q34/Q35 及 E12/E14 中的对应身份， `result_refs` 和保存的比较字段。 | 有真实 Run 才显示固定的 `/cases/{case_id}/investigations?run={run_id}&view=process`。任务进入终态后定向刷新同案 E03、E10 及已使用的 Q30/Q34 目录，按 `caseInfoSummaryKey(caseId)` 前缀失效 Q36 摘要，以覆盖版本键不变的调查数更新。原轮和 Result 以保存身份查回。 |

POST 源码已独核，现有 GET 与 202 登记均已查到，平台实际运行接线仍待。Q30/Q31 公开 OpenAPI 和生成类型由平台后端完成交接并独核。前端候选在 `caseEntryApi` 使用生成的提交、受理及任务列表和详情合同，已执行组合类型检查。 [平台 POST 注册](/Users/lychee/Projects/SpiritHub-web-8181/backend/src/spirithub/api/routes/socai2.py:371) · [正式受理合同](/Users/lychee/Documents/project/socai2/services/api/investigation_http/analysis_submission_contracts.py:11) · [Q30/Q31 合同](/Users/lychee/Documents/project/socai2/services/api/investigation_http/analysis_task_contracts.py:54) · [现有案头任务条](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkspaceFrame.tsx:147)

| 状态 | 呈现和允许动作 |
| --- | --- |
| 202 或 Q31 `accepted` | 显示「已受理 · 等待执行」。Q31 有 `retry_scheduled` 时沿真实原因及 `next_retry_at` 表达服务端已安排重试。 |
| Q31 `running` | 显示「执行中」，准备时可尚无 Run。复用现有 5 秒 GET 轮询，仅在 `accepted/running` 且读取无错误时继续。有保存的 Run 才显示链接。 |
| Q31 `completed / failed / skipped` | 分别显示任务已结束、执行失败或已跳过，保留原因和原尝试。 `skipped/no_changes` 显示未发现变化，有既有失败 Run 时仅打开其原身份。任务状态、尝试 `unknown`、Run 状态、交付和采用分别以保存读侧表达。 |
| 提交未确认或回执身份不合 | 原表单及原操作键留存，显示请求或身份核验错误后停止这次提交。404、409、422 沿正式业务反馈，网络中断或 5xx 显示受理未确认。保留已知原任务，后续操作限只读核对，Q30 最近一条不用于推定未知受理。 |
| Q31 读取失败或身份不合 | 保留已知原任务，关闭自动读取，允许重试同一个 GET。页面刷新和返回均只读。 |

[提交错误及同键重放](/Users/lychee/Documents/project/socai2/docs/integration/analysis-submission-http.md:76) · [任务状态与自动更新](/Users/lychee/Documents/project/socai2/docs/integration/analysis-tasks-http.md:25) · [现有操作键与提交](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/queries.ts:12)

## 直接测试及 M2 通过证据

1. 统筹已确认两个入口的范围。在当前 change 执行严格校验后实施。候选集中于 `CaseInvestigationOverview`、现有 Case 任务客户端和案头任务显示。旧读侧和其余模块适用原记录。
2. 更新 `CaseInvestigationOverview.test.tsx` 的旧准备/启动用例。核取消时零 POST，确认后一次同案 POST、精确 `check/rerun` 载荷、操作键和成功受理正文中的任务身份。将 Q31 从已受理未出 Run 读到真实 `latest_run_id`，打开固定过程入口。明确的 `skipped/no_changes` 无新 Run，保留旧记录链接。HTTP 202 透传基线使用平台已有定向检查。 [平台 202 用例](/Users/lychee/Projects/SpiritHub-web-8181/backend/tests/soc/test_bridge.py:582)
3. 保留一个未知提交或错位回执的定向用例，核失败后的刷新、取任务及读取失败重试仍仅 GET，原 POST 次数为一。复用既有 Case 首轮 E03/Q31 用例和历史固定轮用例。挂载前补一个定向用例，核 Q31 终态后范围版本相同的 Q36 调查记录数重新读回。 [概览定向用例](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigationOverview.test.tsx:13) · [首轮读回](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbench.test.tsx:91) · [固定历史](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigationHistory.test.tsx:122)
4. 替身证据用于检查请求、受理、任务状态和导航。实际验证待统筹挂载并明确范围。在获准候选沿一次正常后轮任务，核真实平台 202、同案 Q30/Q31 保存的身份。如已有经确认符合本批的原任务，沿其原身份读回。出现新轮后用 Q34/Q35、E12/E14 和 E03 核固定结果、旧轮保留、实际范围差异及保存的比较来源。无变化时以原任务的保存原因和无新轮为据。21 的运行接线与实际业务验收另由统筹记录。

独立候选已完成。两个正式入口共用同案受理身份、Q31 案头任务条与固定 Run 进度地址。Q30 只读任务列表区分成功全量、部分加载和读取失败。提交失败保留选择及该次操作键，写入停止，原任务链接仍可读。旧待启动记录保留范围和原轮链接。

初版组合类型检查通过，概览四项、首轮受理条一项和固定历史一项均通过。挂载前复核发现 Q31 终态后，同范围版本的 Q36 摘要会留在缓存。定向用例先复现原调查记录数未更新。补同案 `caseInfoSummaryKey` 前缀失效后，范围版本保持相同，资料页重新 GET 并显示更新的调查记录数。此轮实施前严格校验、一个 Q36 用例与组合类型检查均通过。 [初版检查](/Users/lychee/Documents/project/socai2/.local/validation/spirithub-case-overview-20261128-01/direct-checks.json) · [最终定向检查与指纹](/Users/lychee/Documents/project/socai2/.local/validation/spirithub-case-overview-20261128-02/direct-checks.json)

前端组件验证用替身检查成功响应正文中的受理身份，复用现有 `command`。HTTP 202 透传由平台已有定向用例覆盖。最终六文件补丁在相同前像副本上精确回放，等同测试后像。 [最终源码与测试补丁](/Users/lychee/Documents/project/socai2/.local/validation/spirithub-case-overview-20261128-02/case-overview-follow-up.patch) · [平台 202 用例](/Users/lychee/Projects/SpiritHub-web-8181/backend/tests/soc/test_bridge.py:582)

统筹完成最终源码独核，已将六个文件精确挂载到 8181。读回的六文件和五项组合依赖均匹配原检查指纹，组合类型检查和定向组件证据按该版本复用。正式平台的新 POST 仍待上线核验，实际执行按统筹已发起的原任务追踪。 [独审回执](/Users/lychee/Documents/project/socai2/.local/validation/model-exceptions-release-coordinator-20261128-01/case-overview-final-source-review.json) · [8181 挂载指纹](/Users/lychee/Documents/project/socai2/.local/validation/spirithub-case-overview-20261128-02/8181-mounted.json)

## 本轮 21 rerun 的 8181 只读验收准备

本轮同案 rerun 的提交证据从正式原生 HTTP 取得。8181 查验同一已受理任务和原 Run 的页面读回。现行平台新 POST 尚未部署，8181 写入口验收仍待。本节记录查验方案，待统筹提供本轮私密绑定并安排读取。

### 本机引用与源码

- 普通 8181 使用 SpiritHub Web 的 `frontend-8181` 配置。代理读取 `SPIRITHUB_API_PROXY_TARGET`、`SPIRITHUB_PUBLIC_ORIGIN` 和 `VITE_API_MODE`。既有实际转发核对可在私密回执定位，目标值留在原配置。 [8181 本机配置](/Users/lychee/Projects/SpiritHub-web-8181/web/.env.frontend-8181.local) · [Vite 代理](/Users/lychee/Projects/SpiritHub-web-8181/web/vite.config.ts:10) · [既有平台转发回执](/Users/lychee/Documents/project/socai2/.local/validation/m0g-spirithub-readonly-20261128-01/platform-routing-target.private.json)
- 会话沿既有普通 8181 登录上下文。已有会话核对和恢复记录可在本机引用。读取时遇到会话失效或权限错误，记录在本机并由统筹处理。用户名、凭据、Cookie、令牌和会话状态值留在原处。 [既有会话核对](/Users/lychee/Documents/project/socai2/.local/validation/m0g-spirithub-readonly-20261128-01/frontend-8181-session-check-01.private.json) · [既有会话恢复](/Users/lychee/Documents/project/socai2/.local/validation/m0g-spirithub-readonly-20261128-01/frontend-8181-session-restore-01.private.json)
- 既有读取源码可复用同源白名单、私密绑定、GET 捕获和原件可用性判定。旧浏览器脚本的整套入口会打开页面、包含认证请求路径，且回执字段以初始任务命名。后续只选用其读取片段，在既有会话上按本轮绑定限制 GET。旧离线核对脚本可参考身份与可用性判据，首轮测试断言及旧证据留在原批。 [页面捕获源码](/Users/lychee/Documents/project/socai2/.local/validation/m0g-spirithub-readonly-20261128-01/frontend-case-readback.mjs:40) · [离线核对源码](/Users/lychee/Documents/project/socai2/.local/validation/m0g-spirithub-readonly-20261128-01/frontend-case-verify.py:15)

### 最小页面读回

以统筹绑定的原生受理回执作为起点，在本机留存 `case_id`、`task_id`、`status_url` 及已有的精确运行或结果引用。所有下面的页面路径只使用本轮已绑定的身份。字段名为校验项，实际身份、状态、报文、页面和逐项查询结果保存为本机私密回执。

| 8181 页面 | 只读请求 | 最小核对 |
| --- | --- | --- |
| 调查概览 `/cases/{case_id}/overview?task={task_id}` | E03、指定 Q31 `GET /cases/{case_id}/analysis-tasks/{task_id}` | E03 `case.id` 与同案身份对应。Q31 核 `task_id/subject_type/subject_id/kind/intent/status/status_url/reason_code` 及 `latest_run_id`，其中意图须与已绑定的 rerun 一致。沿 `attempts[].run_id/outcome` 保留真实尝试结果。终态可能没有 Run，按原回执呈现。按任务参数直读，Q30 的当前工作列表可能仅显示受理或执行中的任务。 |
| 调查历史 `/cases/{case_id}/investigations`，再开固定 `?run={run_id}&view=process` | Q34 `GET /cases/{case_id}/investigations`、精确 Q35 `GET /cases/{case_id}/investigations/{run_id}`、E12 `GET /cases/{case_id}/runs/{run_id}` | 用 Q31 保存的实际 `latest_run_id` 查该轮。Q34/Q35 核 `case_id` 和卡片的 `run_id/subject_type/subject_id/run_kind/state/delivery_state/result_refs`。目录尊重 `next_cursor`。E12 核 `run.id/run.case_id/run.state/run.delivery_state` 与 `result_ids/results_truncated`。旧轮按原身份读取，需要比较时使用已保存的比较引用。 |
| 固定结果 `/cases/{case_id}/investigations?run={run_id}&result={result_id}&view=overview` | E14 `GET /cases/{case_id}/results/{result_id}`，已有采用指针需要核对时沿 E03 | 结果按 Q31 或 Q35 的保存引用选定，核 `id/result_type/source_run_id`。E14 核 `run.id`、`result.id/case_id/source_run_id`，以及 `validation_state/conclusion_origin/conclusion_state/delivery_state`。缺结果或存在多个未选结果时保留原状态。若显示当前采用，沿 E03 的 `case.current_assessment_id` 和 `current_assessment` 读回。 |

入口失配、读取失败、未读全及成功为空分别写入本机私密回执。无真实 Run 或 Result 时，验收停在实际可读的原任务或原轮，避免依据列表首条或时间推定身份。正式任务和 Run 的状态各沿保存字段，已受理或任务进入终态均不足以确认结果交付。

[任务与域身份校验](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-entry-api.ts:74) · [案头任务与进度链接](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkspaceFrame.tsx:158) · [历史定位](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigationHistory.tsx:71) · [固定结果校验](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunWorkspace.tsx:42)
