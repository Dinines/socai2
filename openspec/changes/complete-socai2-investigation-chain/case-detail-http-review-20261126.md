# Case 详情迁移前的 HTTP 合同核对

2026-11-26，`complete-socai2-investigation-chain`，服务端分支 `V1.1`。

4173 的「案件资料」是默认页，另有故事、调查概览、调查历史、成员告警、案件关系图、对象与证据、人工任务、处理活动、评论与附件，共十页。助手是贯穿各页的浮层。固定 Run 复用五个主视图，执行明细是「AI 分析」中的辅助视图。迁移须保持进入时选定的 Case、Run、Result 和人工修订，切换视图时保持同一轮，切换轮次时只带属于新轮的 Result。

核对了 4173 页面源码、8181 当前工作区和平台路由，以及 21 已留存的调查 OpenAPI。8181 的故事和全局运行列表另核了实际提供的前端模块。故事使用既有 Case 执行了定向只读检查。「已支持」指核到对应合同或接线，逐页浏览器交互和视觉验收仍按清单执行。以下原生路径均省略 `/api/v1/socai2`。 [88 项功能矩阵](investigation-test-matrix-20261126.md) · [HTTP 操作注册表](../../../docs/operations/evidence/investigation-test-plan-20261126-01/http-function-contracts.json) · [逐页迁移清单](investigation-page-migration-checklist-20261126.md)

除已确认后置的动作和明确由新生命周期替代的步骤，整页迁移须保留原型的功能、查阅范围和原记录回链。已加载集合上的搜索、筛选、计数及覆盖只说明该集合，要求全案的动作用完整范围验收。合同缺口记为未完成，在对应页面的设计步骤补齐所需输入、返回、来源和直接验收。已有原生合同则按实际差距补前端或平台接线。

## 共用页头及多事件基准

4173 与 8181 都在页头直接展示前两个关联事件，更多已加载事件通过折叠区展开。4173 预览会合并显式事件和由成员告警反查到的事件，并检查来源环境。8181 页头读 E03 的 `linked_incidents`。正式迁移应分别呈现显式关系和成员来源，沿各自身份回到事件，历史范围沿所选 Run 读取。

| 动作 | 合同、保存来源与差异 |
| --- | --- |
| 从队列进资料、刷新、切换 Case（F09-05） | **已支持**。E03 `GET /cases/{case_id}` 回 `case`、`members`、`linked_incidents`、两组 count/truncated、`current_assessment`、`baseline_records`、`page_data`。来自 `cases`、`case_alerts`、`case_incidents` 和持久判断/Run。前端校验 `case.id`。切案及链接返回后应复核所选 Run、Result、任务和条件是否属于当前案。 |
| 展开及跳转多个事件（F09-05、F13-04） | **已支持**。E03 的 `linked_incident_count` 和 `linked_incidents_truncated` 说明完整度，逐项到 E29 `GET /incidents/{incident_id}`，事件成员另经 E30 `records/members`。事件后来新增的告警仍以实际 `case_alerts`、分配回执和事件接收关系判定是否纳入本案。**后台缺合同**。E03 为有界投影，本次核查未找到案内显式事件全集的独立分页入口。 |
| 管理、关闭、重开（F23-04） | **已支持**。E44/E45 `GET/PATCH /cases/{case_id}/management`。PATCH 用 `operation_key`、`expected_row_version` 和显式修改的标题、说明、负责人、状态、等级、优先级或标签。E46/E47 `POST /close`、`POST /reopen` 使用同主体的行版本和操作键。有未完任务时按 E44 要求确认并提供结案原因，其他场景原因可省略。读回 E03/E44 及 E17 活动。重开和调查提交各有入口。 |
| 跨页显示执行提示（F14-01） | **已支持**。已定位的首轮任务可由 8181 页头走 Q31 读原 `task_id`，有关联 Run 后可跳 E12 对应详情。**前端漏接**。页头和概览全案活跃状态仍依赖 `baseline_records`，需要结合 Q30 主体任务列表处理尚无 Run 的受理、跳过和失败。 |

以统筹已确认的既有 4173 参考案为准。本机结构检查与统一绑定指向同一案。原型源记录有 2 个显式事件和 3 个关联 Run，统筹在页头看到 2 个独立事件链接。两事件各有成员，Run 材料已存在，成员级独立证据在该案缺供。超过两个事件的折叠分支已查双方源码，该案未覆盖该分支。21 的 E65 定向读回用于定位当期 8181 报告的 422。

[4173 案内入口与页头](../../../prototypes/security-pages-v2/app.js#L405) · [8181 页头实现](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkspaceFrame.tsx#L37) · [Case 关联与分配](../../../docs/integration/case-allocation-http.md)

## 1. 案件资料 `case-info`

| 4173 动作 | 原生输入、输出与保存读回 | 当前差异 |
| --- | --- | --- |
| 看说明、范围、对象/证据入口（F09-06） | E03 读说明、成员、显式事件和有界历史。E05 `GET /cases/{case_id}/page-data` 回 `classification`、`due_at`、`determination`、`assessment`、`evidence`、`schema_version`。证据索引沿 Case 当前工件指针查 E16。历史、任务走 E10/E39。 | **已支持**。现有 Case 资料及入口可读。**后台缺合同**。全案统一对象、资产库存和跨所有来源的材料计数无同义聚合，当前页或某事件的计数不能替用。 |
| 编辑分类与期限（F10-01） | E04 `PATCH /cases/{case_id}/page-data` 提交 `operation_key`、`expected_row_version`、`classification`、`due_at`、`source`、`source_note`。返回 `case_id`、`changed`、`row_version`、`current_evidence_artifact_id`。分类/期限存 Case 资料，写后读 E05/E03/E17。 | **已支持**。清空和保留已有字段按相应版本及请求合同处理。 |
| 看当前判断、依据、覆盖和未决事项（F11-01、F12-01、F11-02） | E03/E05 定位 `current_assessment`、来源、判定、范围和新鲜度。覆盖来自 `case_assessment_members` 与当前成员的比较。保存的 Result 结论、`questions`、`findings`、`recommendations`、`case_impact` 由 E14 `GET /cases/{case_id}/results/{result_id}` 读原文。 | **已支持**。已有判断/覆盖卡及 Result 未决读取。需用同案查原覆盖、当前显式多事件范围的区别，以及有采用、系统说明、暂无采用和依据已变化的空态。 |
| 打开判断来源（F12-02） | 按 `result_id` 走 E14，按 `task_id/task_revision_id` 走 E43，按 `run_id/artifact_id` 走 E15 或按 Case 工件走 E16。告警、事件阶段结果走对应主体 E24/E25。源由 `case_assessment_sources` 锁定。 | **前端漏接、后台缺合同**。已有可直接读的来源入口，但部分抽屉回退到 Q11 的 `/references/{reference_type}/{reference_id}/context`。当前原生 Swagger 无该通用上下文路由，已带父主体与原件身份时应沿现有源路由。 |
| 看 ATT&CK 阶段和明细（F09-07） | E03 确认成员，E28 告警详情、E31 指定材料及 E24 指定告警 Run 提供同源战术及来源。历史轮次沿 E18 冻结原材料。 | **已支持**。成员级依据可读。**后台缺合同**。未提供全案 ATT&CK 聚合。展示使用明确的已读成员范围和带来源字段。 |
| 比较和明确采用已存结果（F11-03） | E63 `GET /cases/{case_id}/results/{result_id}/adoption-preview` 回候选、当前判断、涵盖、依据和未完工作，以及 `can_adopt`、`review_token`。E21 `POST .../adopt` 带 `operation_key`、`expected_review_token`、`reason`、`acknowledge_pending_work`，回 `assessment_id`、旧判断、修订和 Case 行版本。E03/E64 `GET .../assessments?limit&offset`/E17 核同案判断、历史与活动。 | **前端漏接、平台漏转**。8181 用 E14 作本地预览并提交旧 `expected_scope_revision`、`expected_assessment_id`、`confirm_partial`。平台有 E21，当前代理缺 E63/E64。 |

[4173 资料和判断](../../../prototypes/security-pages-v2/app.js#L415) · [8181 CaseFields](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseFields.tsx#L45) · [8181 AdoptResultDialog](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/AdoptResultDialog.tsx#L18) · [采用合同](../../../docs/integration/result-adoption-http.md)

## 2. 案件故事 `story`

**422 已定界。** 8181 正在提供的模块将空搜索省略，首屏产生 `kind=all&limit=50&offset=0`。筛选会另外发送 `severity_groups`，右栏关联 Run 走 `kind=run` 和 `alert_ids`，也依赖旧偏移分页。当前平台 Q13 源码按原路径逐项转发查询参数。21 对同一 Case 的无参 E65 返回 200，相同旧参数组合返回 422 `story_query_parameter_not_supported`。以 `limit=1` 读取和按 `next_cursor` 续页均返回 200，首、次页顺序与正式默认页一致，条目结构及嵌套身份校验通过。平台环节以源代码核对为证据。

4173 的故事提供搜索、单值严重度、重置和告警勾选，主区域为时间线，右栏为焦点告警的活动详情。「全部／告警／调查／结果／人工」类型页签及「添加筛选」多选等级是当前 8181 的控件。4173 的迁移范围按上述原型动作核查。

| 4173 动作 | 合同、保存来源与差异 |
| --- | --- |
| 时间线、统计及未知时间区（F20-01） | **前端漏接**。E65 `GET /cases/{case_id}/story` 回 `items,total,next_cursor,observed_at`。条目 `id,kind,occurred_at,time_source,alert,run,results,task_revision,is_current_task_revision`。`kind` 为 `alert`、`investigation`、`human_result`，Result 在终态 Run 的 `results[]` 内，未产出时保留空数组。时间取告警事实、实际 Run 时间或任务完成时间，未知排最后。来源为 `case_alerts/alerts`、`runs/results`、完成的 `task_revisions`。当前组件用旧 `at` 与平铺身份。**后台缺合同**。E65 的 `total` 是当前筛选的条目总数。4173 页头的成员告警总数已有 E03。涉及对象的去重总数及告警已知时间跨度仍缺对应的完整范围合同。 |
| 搜索、单等级、重置和续页（F20-02） | **前端漏接**。正式参数仅单值 `q`、`severity`、`limit`、`cursor`。`q` 最长 200，`severity` 允许 `info/low/medium/high/critical`。`limit` 默认 20，范围 1–100。换 Case、关键词、等级或重置时清游标，续页原样传回，null 到末页。**后台缺合同**。4173 在选择严重度后，按当前匹配的告警筛选有对应关联的调查和人工完成记录。E65 的严重度只筛告警，Run 和人工上下文继续按其搜索条件保留。应以多页、同案不同严重度及有关联和无关联的调查／人工记录验证这处语义。 |
| 聚焦、勾选及右栏下钻（F20-03） | **已支持**。原型独立维护焦点与勾选。右栏以焦点告警为主，展示它与同案其他告警的共有对象及包含它的调查。焦点不在当前匹配集合时，显示该集合的首条告警。预览走 E28，对象/材料沿 E30/E31，以同案对象的类型、命名空间和对象键匹配，包含关系沿 E12 冻结成员。**前端漏接**。8181 目前按勾选集合打 Q12 和带 `alert_ids` 的 E65 请求。**后台缺合同**。跨全案的焦点告警共有对象及相关 Run 缺完整集合查询，若 E03/E12 截断则需在该页设计补齐所需范围。 |
| 从告警、Run、结果、人员陈述回原记录（F20-05） | **前端漏接**。使用 `alert.id` 走 E28/E31，`run.id` 走 E12，`results[].id` 逐项走 E14，`task_revision.task_id/id` 走 E43。E41 另读当前任务，历史完成修订显示其实际历史身份。旧平铺字段及独立 `result` 项不匹配。 |
| 围绕条目、选区或全案提问（F20-04） | **明确后置**。保留原型场景及当前产品入口位置作为设计依据，E19/E20 仍为 501，任务和调查历史各沿正式读取。 |

[4173 故事和选区](../../../prototypes/security-pages-v2/case-assistant.js#L127) · [8181 CaseStory](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseReadPanels.tsx#L27) · [8181 story 请求](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/workbench-api.ts#L32) · [平台代理](/Users/lychee/Projects/SpiritHub-web-8181/backend/src/spirithub/api/routes/socai2.py#L226) · [E65 指南](../../../docs/integration/case-story-http.md)

## 3. 调查概览 `overview`

| 4173 动作 | 合同、保存来源与差异 |
| --- | --- |
| 看当前活动、待启动、暂停和失败的真实状态（F14-02） | **前端漏接**。Q30 对接 `GET /cases/{case_id}/analysis-tasks?limit&cursor`，回 `items,total,next_cursor,observed_at,update_state`。Q31 同案同 `task_id` 读 `status,reason_code,attempts,active_step,latest_run_id,results`。任务、尝试及主体变更来自 `analysis_tasks`、`analysis_attempts`、`analysis_subject_state`。没有 Run 的任务只显示任务进度，有 Run 才取 E12。有运行也分别显示执行状态、交付和业务判断。 |
| 检查更新（F14-03） | **前端漏接、平台漏转**。原生 `POST /cases/{case_id}/investigations` 只接受 `operation_key` 和 `mode=check`，202 回 `task_id,status_url,subject_type,subject_id,status`。按原地址读回。无变化可返回 `skipped` 和原因，无新 Run。8181 仍发送 E11 prepare，桥接缺现行 POST。 |
| 再次调查并看本轮进度（F14-04） | **前端漏接、平台漏转**。同现行 POST 用 `mode=rerun`，依同任务的实际尝试到 E12，再沿 E14/E15 读本轮结果/工件。首轮读建案原 `initial_task.status_url`。旧 E11/E13 和原型本地草稿/自选窗口没有现行等价提交合同。 |
| 读已有结果摘要、原件和来源（F16-01） | **已支持**。E10 提供本案历史的 `run` 和可空 `result`。E14 读选定 Result 原文/范围，E15 读原工件。跨事件的来源关联跟各自保存的 Result。 |
| 查人工待办或去历史、故事（F22-01、F14-05） | **已支持**。E39 按 `limit,offset` 和 `next_offset` 读任务，E41 选定记录，E10 读历史。**前端漏接**。故事跳转到本案后仍受 E65 旧参数阻断。 |

[4173 调查概览](../../../prototypes/security-pages-v2/investigation-workspace.js#L321) · [8181 CaseInvestigationOverview](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigationOverview.tsx#L17) · [受理、检查与再次调查](../../../docs/integration/analysis-submission-http.md) · [任务列表与详情](../../../docs/integration/analysis-tasks-http.md)

## 4. 调查历史 `investigations`

| 4173 动作 | 合同、保存来源与差异 |
| --- | --- |
| 分类浏览、选择多轮、切视图/返回（F14-06） | **已支持**。E10 `GET /cases/{case_id}/history?limit&cursor` 回 `items[].id/recorded_at/run/result`、`next_cursor`。Case 基础 Run 和既存的 `ai_saved` Result 记录来自 `runs/results`，结果允许为空。8181 案内已有 `run,result,view` 和 E12/E14 接线。切轮保留 `view`，按新条目设置或清除旧 `result`。**前端漏接、平台漏转**。同页补充告警分诊和事件诊断仍用旧 Q08 `/runs?case_id=…` 及 `q` 查 Run，原生无同路径。正式目录 Q32 的 `subject_type,subject_id` 只筛单一主体。跨事件轮次须从真实关联主体沿 E22/E23/E24/E25 定位。需全案跨主体关联目录时，**后台缺合同**。 |
| 看所选轮状态、交付、投入（F15-01） | **已支持**。E12 回 `run.state/delivery_state`、时长、`usage`、`read_counts`、`analysis_counts`、`tool_calls`、`execution_summary`、`steps_url/artifacts_url` 等。有保存结果读 E14。**前端漏接、平台漏转**。完整步骤/原件目录还受固定 Run 所述限制。 |
| 看本轮对前轮的变化和比较（F16-02） | **前端漏接**。E12/E14 的 `previous_run_url`、`comparison_result_url` 来源是冻结的前轮关联，含不可比较空值。原比较身份保存在 `runs/results`。`comparison_context`、`change_kind/change_summary` 取保存值。现案内切换有选择器，未见完整消费两条正式比较链接的产品流。 |
| 看当轮覆盖、历史材料、结果与未决原引用（F12-03） | **已支持**。E12 的 `input_member_count,members,members_truncated,input_artifact_id` 定位 `run_members` 和输入工件，E18 `GET /cases/{case_id}/runs/{run_id}/materials/{material_id}` 查当轮材料，E15 查工件，E43 查原人工修订。**前端漏接**。精确固定引用与共用抽屉的旧上下文回退需联验。 |

全局运行列表（F14-07、F15-02）现已用 Q32 `GET /analysis-runs`，可按 `subject_type,subject_id,run_kind,intent,state,time_from,time_to,limit,cursor` 查询，回 `items,next_cursor,total,observed_at,statistics`，每行有主体、Run、可空 task、结果、`detail_url`。**前端漏接、后台缺合同**。全局列表点击仍进入通用 `/investigations/:runId/overview`，再取 Q09 `/runs/{run_id}/context`。当前只核到平台的事件专用定位分支，原生无通用上下文，Case 应沿主体明确的 E12 和固定视图，A/I 沿各自主体入口。目录的刷新、预览、导出是目录动作，查阅 Case 固定 Run 独立验收。

[8181 CaseInvestigations](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigations.tsx#L14) · [8181 全局运行列表](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationListPage.tsx#L34) · [原生历史读侧](../../../services/api/app/socai2/case_reader.py#L304) · [正式运行目录](../../../docs/integration/run-directory-http.md)

## 5. 成员告警 `alerts`

| 4173 动作 | 合同、保存来源与差异 |
| --- | --- |
| 查成员、打开告警/事件、看采用覆盖（F13-04） | **已支持**。E03 返本案当前成员及显式事件，E28/E29 回各主体，E30 对象/资产/事件成员。当前前端搜索、选中和加载更多对已载入成员有效。覆盖与新鲜度取采用的原范围，多事件共同告警按实际告警身份核对。**后台缺合同**。当 `members_truncated` 生效时，当前 E03 无下一页游标。 |
| 添加所选告警或整事件（F13-05） | **已支持**。E08 `POST /cases/{case_id}/associations` 提交 `alert_ids,incident_ids,expected_scope_revision,operation_key`，回 `primary_case_id,receiving_case_id,allocations,incident_receivers,excluded_alert_ids` 等。8181 当前分配处理已校验实际 `allocations[]` 与首轮任务归属。读 E03/E17 及原任务，E29 核事件接收关系。续建案组各自有成员与历史。 |
| 移动已选告警（F13-06） | **已支持**。E09 `POST .../members/move` 带 `target_case_id,alert_ids,expected_source_scope_revision,expected_target_scope_revision,operation_key`，回 `source,allocation,moved_alert_ids`。读源案和全部实际接收案/活动，旧 E12/E14 冻结材料仍沿原轮。移动 UI 的多接收案提示与原回执读回待联验。 |
| 管理所选及成员变化后看在途覆盖（F13-07、F13-08） | **已支持**。E51 告警批管理按所选告警和行版本保存，E28/E30 读所选及活动，E03 读当前范围，E12/E15 读固定在途范围。**前端漏接**。后续明确检查受概览旧提交路径影响。 |

[原型成员操作](../../../prototypes/security-pages-v2/case-workflow.js#L26) · [8181 成员表](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchDetail.tsx#L86) · [8181 分配接线](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/case-entry-api.ts#L54) · [Case 分配合同](../../../docs/integration/case-allocation-http.md)

## 6. 案件关系图与关联探索 `attack`

| 4173 动作 | 合同、保存来源与差异 |
| --- | --- |
| 读底图、筛选布局、看节点和来源（F19-01、F19-02） | **前端漏接、平台漏转**。E67 `GET /cases/{case_id}/exploration-base` 可带 `run_id`，回 `case_id,scope_revision,run_id,result_id,graph_artifact_id,graph_state,graph,sources,fingerprint` 等。图来自保存工件或当前成员、告警材料和对象。8181 现从历史图工件和 Q12 对象拼工作区，未接 E67，平台缺 E67。布局、缩放、筛选、节点选中为界面行为。 |
| 按种子/时间查候选，打开、展开、撤销（F25-01、F25-02） | **前端漏接**。E66 `GET .../exploration-candidates` 仅 `alert_id,object_id,time_from,time_to,limit,cursor`，回 `items,scope,total,next_cursor,observed_at` 和匹配材料/对象身份。Q16 可转，8181 仍送 offset，展开还依赖旧 Q20 预览。候选原件沿 E28/E31，客户端可撤销展开。**后台缺合同**。Q20 合同未在原生注册，正式底图和候选可供渲染与来源查读。 |
| 保存并恢复探索（F25-03） | **前端漏接、平台漏转**。E68 `PUT .../exploration` 带 `operation_key,expected_snapshot_id,base_snapshot_id` 或固定底图的 `base_run_id/base_fingerprint`，以及有序 `expanded_links` 和 `view_state`。保存快照回 `id,case_id,base,expanded_links,expanded_sources,view_state`。E69 单数 `GET .../exploration` 回同一当前快照，首次 `snapshot=null`。保存为在案探索工件和活动，E03/E10 仍分别核正式成员及历史。8181 与桥接仅有旧的复数 `explorations`。 |
| 明确加入候选到本案（F25-04） | **已支持**。正式写入沿 E08 关联和实际接收案读回。**前端漏接**。从有效底图、候选到确认加入的完整 8181 路径仍受旧探索调用影响。 |
| 按所选对象提问（F26-01） | **明确后置**。原型保留所选对象情境，业务助手按统一后置范围。 |

[8181 探索实现](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseExploration.tsx#L39) · [E66 候选合同](../../../docs/integration/case-exploration-http.md) · [E67–E69 底图与保存](../../../docs/integration/case-exploration-save-http.md)

## 7. 对象与证据 `evidence`

| 4173 动作 | 合同、保存来源与差异 |
| --- | --- |
| 按对象看、按所选成员或多个事件定位来源（F21-01） | **后台缺合同、前端漏接**。8181 的 Q12 `GET /cases/{case_id}/objects` 无原生对应。已有 E03 成员、E30 `/{subject}/{identity}/records/{section}` 对告警/事件的 `objects/assets` 和对应材料身份，按 `limit,offset` 读 `items,total,next_offset,limitations`。保留对象键、命名空间、告警/事件来源。案件范围与单事件范围分别标明。 |
| 按调查选轮或结果（F21-02） | **已支持**。E10/E12/E14 找固定 Run、Result，再走 E15 或正式目录链接。当前入口的数据完整性受目录层限制。无对象时仍可到选定的历史 Run。 |
| 读证据索引、威胁、覆盖（F21-03） | **已支持**。E05 `evidence` 投影当前索引状态、覆盖、限制及来源，E16 读 Case 工件，E15 查当轮原件。显式发布索引已有 E06 `POST .../evidence-index`，接 `operation_key,expected_row_version,expected_current_artifact_id,index`，存工件及 Case 指针，回 E05/E03。按原型浏览无需额外发布。 |
| 摘要、原件、引用返回（F21-04） | **已支持、前端漏接**。按真实标识走 E14/E15/E16/E18、E31/E33–E35 或 E43。保留父主体、版本和 `availability`。有直接原件路径时可读，未知父身份的通用引用回退仍受 Q11/Q26 限制。 |

[4173 对象与证据](../../../prototypes/security-pages-v2/case-workflow.js#L175) · [8181 CaseEvidence](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseEvidence.tsx#L20)

## 8. 人工任务 `tasks`

| 4173 动作 | 合同、保存来源与差异 |
| --- | --- |
| 状态、待办、详情（F22-02） | **已支持**。E39 `GET .../tasks?limit&offset` 回 `items,total,next_offset`。E41 同案指定任务回 `current,current_revision_id,row_version,origin_result_id,origin_finding_id` 等。待办数按 Case 的当前修订及状态，分页只说明已加载的任务。来源为 `tasks/task_revisions`。 |
| 新建、分配、编辑、取消和改状态（F22-03、F22-04） | **已支持**。E38 `POST .../tasks`、E40 `PUT .../tasks/{task_id}` 接 `operation_key,expected_scope_revision` 和完整可编辑字段 `title,description,assignee_id,due_at,state,result_text,result_scope,source_refs`。E40 再传 `expected_row_version`，E38 可关联 `origin_result_id/origin_finding_id`。Q04 查人员，返回 `changed,task` 后走 E41/E42/E43 读回。 |
| 完成并保存适用范围、作者及版本（F22-05、F22-06） | **已支持**。完成要求 `result_text` 和显式 `result_scope`。E42 `GET .../revisions?limit&offset`、E43 `GET .../revisions/{revision_id}` 回不可变修订、完成人、修改人、时间、范围和源引用。E65 历史保留曾完成的修订及是否仍当前。**前端漏接**。对象范围选择仍调用无原生对应的 Q12，部分仅按修订 ID 的深链接依赖 Q11。 |
| 处理并发变更与失败读回（F22-07） | **已支持**。按 Case 范围版本和任务行版本判断冲突，读 E03/E41 最新版本，保留本次编辑供用户明确处理。相同意图重读原保存结果，旧修订可回查。 |
| 保存后查看对调查的影响（F22-08） | **已支持**。E41/E43/E65 可确认保存及来源，后续明确调查沿任务、尝试、Run 输入工件查当时冻结版本。**前端漏接**。概览的正式 check 尚待接线。**明确后置**。助手续接和保存问答。 |

[4173 人工协作](../../../prototypes/security-pages-v2/case-workflow.js#L205) · [8181 CaseTasks](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseTasks.tsx#L28) · [任务请求合同](../../../services/api/app/socai2/human_task_contracts.py)

## 9. 处理活动 `activities`

**F23-05 已支持**。E17 `GET /cases/{case_id}/activities?limit&offset` 回 `items,total,next_offset,observed_at,limitations`。活动来自 `activities/activity_targets`，按本案、实际成员和显式关联事件归集、去重，保留操作者、时间、目标和前后值。8181 接了 E17 和偏移分页。迁移验收应核多事件活动展开、实际目标跳转和相同活动只出现一次，事件范围或处理 Run 须按各自身份回查。 [4173 活动视图](../../../prototypes/security-pages-v2/app.js#L316) · [8181 CaseActivities](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseReadPanels.tsx#L16)

## 10. 评论与附件 `comments`

| 4173 动作 | 合同、保存来源与差异 |
| --- | --- |
| 浏览、提交评论（F24-01） | **已支持**。Q21/E59 `GET .../comments?limit&offset` 回 `items,total,next_offset,observed_at`。Q22/E58 `POST .../comments` 只收 `operation_key,body`，回评论身份、同案、原文、作者、时间和版本。来自 `comments`，写后读 E59 和 E17。**前端漏接**。现 8181 提交额外 `source_refs`，现行请求模型拒绝额外字段。 |
| 看附件关联、文件元信息及下载（F24-02） | **已支持**。Q23/E61 偏移分页，Q24/E62 指定关联，回关联 `id,case_id` 和文件 `file_id,file_name,mime_type,size_bytes,sha256,file_owner,availability` 等。以 Case 已保存外部文件引用为准。**前端漏接**。现附件列表仍尝试从旧 `descriptor` 取部分元数据。**明确后置**。真实文件字节下载和联调。 |
| 登记已有文件、上传新文件（F24-03） | **平台漏转、前端漏接**。E60 `POST .../attachments` 以已存在的外部 `file_id` 加 `file_name,mime_type,size_bytes`、可选 `sha256` 和 `operation_key` 保存关联，E61/E62/E17 读回。当前桥接缺登记 POST，现 8181 的登记只带 `file_id` 和键。**明确后置**。业务后端字节上传、下载及其与登记的联调。 |

[8181 评论和附件客户](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseCommentsAttachments.tsx#L24) · [评论请求模型](../../../services/api/app/socai2/case_comment_contracts.py) · [附件请求模型](../../../services/api/app/socai2/case_attachment_contracts.py)

助手浮层的统一会话、范围选择、建议问题、发送、失败续接、保存及引用追问（F26-02 至 F26-08）均**明确后置**。原型使用同案种子及浏览器演示状态，原生当前只有保留的 E19/E20 两条 501 POST，无正式 GET 会话历史。故事、材料、任务与固定 Run 的正常读取均有各自入口。 [4173 助手](../../../prototypes/security-pages-v2/case-assistant.js#L115) · [保留接口](../../../services/api/investigation_http/external_routes/case_ai.py)

## 固定 Run 的五个主视图

案内入口 `/cases/:caseId/investigations?run=&result=&view=`，4173 通过同案 `overview?run=&view=` 使用共享视图。Case 首次取 E12，实际结果按原 `result_id` 读 E14，并校验 `result.source_run_id`。A/I 轮次按原主体 E24/E25，历史图、报告、来源沿实际工件或材料身份。Run 原件路由 E15 `GET /cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}` 回 `artifact,content_json,content_text,availability`。E16 读取 Case 层级工件，E18 读取本轮冻结材料。

| 视图及动作 | HTTP、保存来源与差异 |
| --- | --- |
| **调查发现** `overview`（F16-03、F15-03、F12-04、F22-09） | **已支持**。E12 读目的、状态、停止原因等。E14 读结论、发现、限制、待核、交付和冻结范围。原件沿 E15/E18/E43。用保存的 `runs/results/run_members/result_members` 及来源。未决事项可显式用 E38 建普通人工任务并传 `origin_result_id/origin_finding_id`，读 E41/E43。**前端漏接**。从单项带原 Result/发现进入任务的身份需补齐，全部原件目录依下列分页。**明确后置**。询问所选结果。 |
| **AI 分析与执行明细** `process`（F17-01、F17-02、F18-01、F17-03） | **已支持**。Case E12／A/I E32 提供有界投影和目录链接。正式 `GET /analysis-runs/{run_id}/steps?limit&cursor&kind`、`GET /analysis-runs/{run_id}/steps/{step_id}` 和 `GET /analysis-runs/{run_id}/artifacts?limit&cursor&step_id` 回完整游标目录和单步。步骤有 `seq,parent_step_id,retry_of_step_id,state,usage,artifact_refs`，来源是 `run_steps/artifacts`。原件按 `artifact_refs[].content_url` 受限读取，保留原主体。**平台漏转、前端漏接**。Q27–Q29 对外只接受告警 Run，当前 Case 组件使用 E12 有界嵌入，Case 的分页、单步、跨轮复用来源仍需接通。**明确后置**。助手追问。 |
| **查询与证据** `tools`（F28-01、F28-02、F18-02） | **已支持**。同一 Run 的步骤、查询回执和工件定位实际查询结果，按保存状态区分未查、完成查空、失败、未知、复用及受限。E15/E18/E31/E33–E35/E43 读真实源。**平台漏转、前端漏接**。有界 `steps/artifacts` 触发截断时 Case 当前无法从 Q27–Q29 补齐，不应把未加载归作未查询。共用抽屉需核保留原材料、步骤或人工版本的父身份。 |
| **调查关系图** `graphs`（F19-03、F19-04） | **已支持**。由 E14 的 `graph_artifact_id` 读 E15，沿图中当轮工件与材料来源定位节点/边。没有图按本轮状态展示。**前端漏接、平台漏转**。从明确历史轮进入当前探索需将选定 `run_id` 交给 E67，并走现行 E66/E68/E69。现产品仍用旧探索路由。 |
| **报告与响应** `report`（F16-04、F18-03、F27-02、F27-03、F27-04） | **已支持**。E14 `report_artifact_id` 或同轮目录的报告工件→E15 原件，浏览器可下载已有报告。已有建议读 E14 的 `recommendations` 和原工件。已有响应沿 A/I 的 E30 `records/responses` 或实际引用的工件/回执查阅。**后台缺合同**。Q25 `/cases/{case_id}/responses` 无原生对应。**明确后置**。新增真实响应审批、意见提交和执行。 |

[4173 Run 选择与视图](../../../prototypes/security-pages-v2/investigation-workspace.js#L420) · [8181 RunWorkspace](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunWorkspace.tsx#L18) · [8181 RunViews](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunViews.tsx) · [完整步骤与工件目录](../../../docs/integration/run-records-http.md)

## 需在对应页面设计中补齐的合同

| 涉及页面 | 真实缺口及完成判据 |
| --- | --- |
| 公共页头、成员告警 | E03 已给出成员和显式事件的总数、当前投影和截断状态。超出投影上限时的全量展阅、成员搜索及选中操作缺可续读目录。用源 Case 的真实成员、显式事件和各事件来源关系验分页、跨页搜索及返回。 |
| 案件资料、关系图、对象与证据、人工任务 | 全案对象目录、库存资产及材料聚合、用于全案展示的 ATT&CK 阶段统计缺相应完整范围。设计明确统计对象、去重键、时间或版本及空态，先复用真实成员、对象、告警材料和证据来源，明确输入缺供时的完整度。人工任务对象选择和探索取用同一来源身份。 |
| 案件故事 | E65 已给单等级、搜索和游标。全案成员数复用 E03。需补涉及对象数和告警时间跨度、按等级命中告警收窄关联调查及人工记录，以及焦点告警与同案其他告警的共有对象和包含该告警的调查。以多页、多事件的匹配边界、总数及原记录回链验收。 |
| 调查历史和固定 Run | E10 负责 Case 自身历史，单主体可从正式运行目录读取。需呈现分诊、诊断与本案调查的统一目录时，先在本页确定真实关联、去重、排序及全范围续页语义。完整步骤、单步和原件已有原生合同，当前阻断归前端及平台接线。现有来源已返回父身份或正式链接时，直接据此定位，复用原件合同。 |
| 报告与响应 | 本案已有响应的统一聚合读回缺合同。若原型动作要求完整浏览这一集合，在此页明确已有响应条目、跨主体来源和实际回执关联。新增审批与执行沿明确后置范围。 |

统一异步受理和持久任务链替代旧 prepare/start 和浏览器调查草稿，执行窗口由正式任务合同确定。助手问答与真实附件字节上传下载按既定后置处理。

## 迁移时的直接验收

1. 固定统筹选定的既有多事件参考案。核页头事件展开到各自详情、Case 当前成员与事件全部成员、当前判断适用范围和不同 Run 的冻结范围。检验在两个以上实际 Run 及其 Result 间切换，页签、原引用和返回链接都对应当前选择。
2. 故事单独验默认、搜索、单等级、重置、游标续页、告警勾选和回链。对照严重度是否收窄关联调查及人工记录，焦点变化是否带动右栏共有对象和包含该告警的调查，并核全案统计。
3. 概览先核任务、尝试和 Run 的只读关系，历史核刷新后还原选择、无结果及前轮不可比空态，固定 Run 核截断、原件可用性和独立结果身份。后续正式写操作由各自迁移步骤走原生接口及同案读回。
4. 其余七个页面按表中实际来源检查产品正例和空态。沿既有保存与读回合同验收，截图和默认视口对照沿逐页迁移清单执行。此次只读核对未触发提交、保存业务数据或发布。
