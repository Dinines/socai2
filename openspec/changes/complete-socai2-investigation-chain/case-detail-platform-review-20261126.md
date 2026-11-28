# Case 详情与固定 Run 的平台合同对照

## 核对范围

2026-11-26 使用统筹统一绑定的既有 4173 参考 Case，核对十个 Case 详情子页、随页助手、五个固定 Run 主视图和执行明细子视图。8181 以 `codex/spirithub-4173` 工作树为准。逐页比较调用点、21 已挂平台路由与原生调查 HTTP 的参数和响应。21 实际业务读取证据沿用同一已有 8181 Case 的两笔 E65 GET。其余 21 链路结论来自实载 OpenAPI 和源码，4173 页面观察单列。容量候选发布及随后同案复验保留为后续步骤。[4173 案内目录](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:408) · [8181 案内路由](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchDetail.tsx:64) · [逐页迁移清单](investigation-page-migration-checklist-20261126.md)

21 平台仍运行 `spirithub-backend:incident-saved-diagnosis-read-20261126-01`。平台和原生 OpenAPI 指纹分别为 `42a659e9aca0cc30526cd4b210b5ea65a301549ff8b086083731714aa593dddc`、`b06ae2e09d13f066eea769e98ab25519ae79652269a8866f0bf11c49f6161804`。28085 实载三条 Case 候选 GET，分别为 `/analysis-runs` 和两条 `analysis-tasks`。28083 负责先前的告警固定轮次读取，共八条 OpenAPI 路径。E65 和其余 Case 普通代理请求沿现有路径转 21。平台普通转发把 `query_params.multi_items()` 交给上游并返回上游 JSON，静态 OpenAPI 可描述较旧的参数和字段。[平台代理](</Users/lychee/Projects/SpiritHub-web-8181/backend/src/spirithub/api/routes/socai2.py:190>) · [本机候选回执](../../../docs/operations/evidence/case-list-migration-20261126-01/platform-local-runtime.json)

## E65 案件故事

- 4173 在故事主区提供搜索、单值严重度选择、重置和告警勾选，按时间组织主时间线，右侧显示活动详情。概况呈现成员告警数、对象数、时间范围，工具栏呈现匹配告警数与全部告警数。类型标签、多选严重度和四项旧 `metrics` 列为 8181 现状。 [4173 故事视图](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.js:127)
- 8181 `CaseStory` 首屏经 `caseApi.story` 发送 `kind=all`、`limit=50`、`offset=0`，空 `q` 已省略。旧多选等级可继续加入 `severity_groups`。平台 Q13 已注册同路径 GET，将参数原样交给调查 HTTP。21 平台 OpenAPI 仍声明 `alert_ids`、`severity_groups`、`q`、`kind`、`limit`、`offset`。 [8181 故事调用](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/workbench-api.ts:32) · [8181 旧筛选](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseReadPanels.tsx:27)
- 原生 E65 允许 `q`、单值 `severity`、`limit`、`cursor`，拒绝额外参数和同名重复参数。复用已有私密绑定，同案原生旧参数返回 **422** 和 `story_query_parameter_not_supported`，同案只传 `limit=50` 返回 **200** 且有条目。此处状态来自原生直读。 [E65 HTTP 入口](/Users/lychee/Documents/project/socai2/services/api/investigation_http/external_routes/story.py:21)
- 原生页为 `items / total / next_cursor / observed_at`。条目使用 `occurred_at`、`time_source`，三类为 `alert`、`investigation`、`human_result`，分别包含嵌套告警、Run 与其保存结果、人工完成修订。当前 8181 读取扁平 `at/title/alert_id/run_id`、`next_offset` 和旧 `metrics`。基础接线使用当前 DTO 和原样游标，按合同把 `total` 用作筛选后故事总条目数，成员告警与对象概况沿各自来源核对。 [故事数据合同](/Users/lychee/Documents/project/socai2/services/api/app/socai2/case_story_contracts.py:44)
- 4173 选定严重度后，调查及人工记录须与当前匹配告警至少有一条关联。E65 的单值 `severity` 仅筛告警，在严重度这一维仍保留调查和人工完成记录作为上下文。两端同为单值选择，应用到工作记录的范围不同，需按该实际差异对齐。 [原型匹配逻辑](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.js:130) · [E65 等级合同](/Users/lychee/Documents/project/socai2/services/api/app/socai2/case_story_contracts.py:14)
- 4173 右栏围绕当前焦点告警，展示焦点详情、它和本案其他告警共同的对象，以及包含它的调查。告警勾选提供助手提问范围。8181 旧侧栏把所选集合传给 `shared_alert_ids` 和故事 `alert_ids`，属于当前接线差异。右栏验收沿焦点身份和本案关联范围。 [原型焦点与关联](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/case-assistant.js:138) · [8181 当前侧栏](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseReadPanels.tsx:43)
- 私密原件留在 `.local/validation/case-story-capacity-live-20261126-01/`，公开仅使用状态、错误码、字段名和是否有条目。普通转发程序已有入口，后续 E65 接线需要同步前端调用及平台代理公开合同。

## 多事件与选中上下文

4173 的页头先放前两个事件，再展开其余事件。原型 `caseIncidents` 先检查来源租户和环境，读取显式事件关联，也允许按受限的原型告警来源补充展示。8181 页头读正式 `CaseDetail.linked_incidents`，同样先放两个，余下按已载入数组展开，并用 `linked_incidents_truncated` 和 `linked_incident_count` 说明范围。正式事件关联取已保存的 Case–事件关系。成员告警取同一案 `members` 与 `member_count`，保留 `members_truncated`。成员视图当前在已载入集合内搜索和增显，按事件归属、当前案件成员和运行冻结成员分别解释来源，处理共享告警时保留唯一告警身份。 [4173 事件与成员来源](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/app.js:135) · [8181 页头](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkspaceFrame.tsx:103) · [Case 详情读模型](/Users/lychee/Documents/project/socai2/services/api/app/socai2/case_reader.py:247)

4173 的 `forCase` 以同源约束归集 Case 自身、显式引用和与成员有关的运行。8181 将同案 `history` 与旧的案件关联目录合用，故需区分 Case 自身 Run、关联事件或告警的 Run、同一 Run 的不同保存结果。案内嵌入保留 `run`、`view` 和显式 `result`，结果须验证属于指定 Run，工件和冻结材料沿该轮来源回读。全局目录按 Case 主体筛选只能表达该主体的运行。当前 E65 同案读回只覆盖故事参数与响应结构。 [4173 运行归集](/Users/lychee/Documents/project/socai2/prototypes/security-pages-v2/investigation-workspace.js:103) · [8181 案内历史选中态](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseInvestigations.tsx:15)

### 统一参考 Case 的实际覆盖

| 范围 | 4173 已有参考 Case 的观察 | 本次缺口 |
| --- | --- | --- |
| 十个案内子页 | 逐一打开并核到活动页签和内容区域。十页均保留同一个 Case 与同一对事件链接，案内导航各有十项。 | 此项核原型页面和共享上下文，21 读取状态仍按各页合同证据记录。 |
| 显式关联事件 | 源记录有两个显式事件，页面有两个不同链接，逐项与私密绑定一致。 | 参考案只有两个事件，第 3 项及其折叠、展开未覆盖。 |
| Run 与材料 | 源记录有三个 Run，历史呈现三个不同固定 Run 链接，固定视图选择器也有三项。对象与证据的按调查视图有三张材料卡，三个链接目标均属于该参考案。 | 源记录含 Run 材料，缺成员级独立证据。查询与材料视图未观察到独立工件目录，已保存报告正文可见。 |
| 固定 Run 与选中态 | 五个主视图和执行明细子视图均在指定 Run 下打开。从查询与证据切换到另一已有 Run 后，Case 与当前视图保持。 | 同一 Run 的多个保存结果切换未覆盖，合同仍要求按选中结果归属读取。 |

绑定与页面原件留在受控目录。只读覆盖计数与布尔另存为 `prototype-multi-case-readonly-engineering.json` 和 `prototype-multi-case-evidence-engineering.json`。

## 十个 Case 详情子页

表内短路径以 `/api/v1/socai2/cases/{case_id}` 为前缀。全局和告警、事件路径另标明。各行列出当前代码与实载合同，运行成功结论见 E65 专节。

| 4173 子页及用途 | 8181 当前代码 | 21 平台与原生对应及差异 |
| --- | --- | --- |
| `case-info` 案件资料。说明、当前判断和原依据、管理信息、显式关联事件 | 公共壳读 Case 详情。资料读当前判断和 `page_data`，管理弹窗读 `/management`，判断详情可读 `/results/{result_id}`。负责人查询用全局 `/people?user_id&limit`。任务回执按同案和任务 ID 读。 | 详情、`/page-data`、`/management`、结果和人员都有代理及原生。Case 详情旧平台 Schema 额外宣称 `scope_summary`，原生从成员、事件列表及独立计数给范围。人员原生为 `OwnerDirectoryPage`，各自保留 `limit/offset`。原生 `/assessments`、`/related-cases`、结果 `/adoption-preview` 在 21 平台未挂。新分析任务读取由 28085 提供。 |
| `story` 案件故事。搜索、单值严重度、重置、告警勾选、时间线及焦点详情 | `CaseStory` 当前使用旧 `kind/offset`、类型标签和多选严重度。旧侧栏以所选告警集合取对象和 Run。 | Q13 原样转发。基础读取采用 E65 的 `q/severity/limit/cursor`、类型化条目与游标。原型等级选择按匹配告警限定调查和人工记录，E65 等级筛选保留这些上下文。原型右栏按焦点告警关联同案对象和调查。 |
| `overview` 调查概览。当前工作、待启范围、已保存结果与人工待办 | `CaseInvestigationOverview` 从 Case 详情取 `baseline_records`，执行中和待启分别读真实状态。另读 `/history?limit&cursor`、`/tasks?limit&offset`、指定 `/runs/{run_id}`。 | 上述读路径两端已挂。历史按原生游标继续，人工任务保留偏移分页。当前 8181 的准备、启动按钮调用 `POST /baseline/prepare`、`POST /runs/{run_id}/start`，21 平台仍宣称这两条，原生当前未挂。正式自动受理的初轮通过任务身份与真实 Run 关联展示。 |
| `investigations` 调查历史。结果列表、内嵌固定轮次、比较与来源 | `CaseInvestigations` 同时读 `/history?limit&cursor` 和全局 `/runs?case_id`。未在已载入历史命中时用旧 `case_id+q=run_id` 查找。结果点击按 `result` 读 `/results/{result_id}`。 | 原生保留 Case 历史、结果和固定 Case Run。旧全局 `/runs` 只在平台挂载，既有证据显示旧上游返回 404。原生和 28085 的 `/analysis-runs?subject_type=case&subject_id` 只读该 Case 主体，关联告警/事件轮次和按 Run 精确定位需有对应关系和身份入口。 |
| `alerts` 成员告警。成员表、勾选、添加或移出、关联事件 | `CaseMembers` 使用 Case 详情的 `members/member_count`，已载入记录内搜索及增显。告警预览用全局告警详情，资产用告警 `records/assets`。选择弹窗接正式 `/alerts`、`/incidents` 列表，保存后按 Case 身份回读。 | 当前 E26/E27 普通代理已有同路径原生读取，正式列表支持 `q/limit/cursor`，平台静态文档仍只声明 `limit/before_id`。已退役的 `/alerts/query`、`/incidents/query` 曾实测被识别为 UUID 详情而 422。事件关联与 Case 成员分别来源于真实 Case 详情，后续验证多事件共享成员的选择、预览和保存读回。 |
| `attack` 案件关系图。选择基准、三栏关系、预览和关联探索 | `CaseGraph` 读 `/history` 找有图的已保存结果，按选中 `base` 取对应工件。工件共用全局 `/runs/{run_id}/artifact-references/{id}`。探索使用 `/exploration-candidates`、`/exploration-preview`、`/explorations` 和按快照 ID 恢复。 | 历史及确定身份后的原生 Case 工件入口存在。旧全局工件上下文、旧预览和复数快照入口仅平台挂载。原生候选改用 `alert_id/object_id/time_from/time_to/limit/cursor`，替代旧 `match/window_start/window_end/seed_object_id/offset`。原生独立 `/exploration-base?run_id` 和单数 `GET/PUT /exploration` 尚无正常平台入口。基准图、候选与保存草图须分别对照。 |
| `evidence` 对象与证据。对象明细、证据引用、按调查切换 | `CaseEvidence` 读 `/page-data` 的 `evidence` 和 `/objects?limit&offset`，对象组件在已载入对象内搜索和按类型分组。按调查切换复用 `CaseInvestigations`，引用抽屉走旧上下文。 | `/page-data` 两端有同名 `evidence` 投影。平台代理仍声明旧 `/objects` 和 Case `/references/{reference_type}/{reference_id}/context`，现行原生未挂。原生已有确定 Case/Run 的工件、材料、结果和具体任务修订读取。全案对象集合、焦点告警与同案其他告警的共同对象、泛型引用解析需分别核对来源。 |
| `tasks` 人工任务。待办、状态、负责人、任务结果及修订 | `CaseTasks` 读 `/tasks?limit&offset`、指定任务、`/revisions?limit&offset` 和指定修订。带修订深链会用 `/references/task_revision/{id}/context` 查任务身份。 | 人工任务与修订的清单和详情两端均挂，沿 `next_offset`。旧引用解析只有平台入口。已知任务和修订身份时有原生直接读取。首轮分析任务是另一个原生资源，28085 读取 `/analysis-tasks` 及其详情，保留无 Run 的受理状态。 |
| `activities` 处理活动。时间、操作目标及变更 | `CaseActivities` 走 `/activities?limit&offset`，活动类型列表和过滤基于已加载行。时间线读 `occurred_at`、动作、操作者快照及变更明细。 | 两端有同名偏移查询和 `RecordPage` 顶层字段。当前筛选范围以页面已载入的活动为边界。读回对照要保留动作的真实目标及 Case 关联，多个事件的活动和成员范围分别核对。 |
| `comments` 评论与附件。评论原文、附件元信息、文件上传和下载 | `CaseCommentsAttachments` 读 `/comments`、`/attachments`，皆传 `limit/offset`。下载按附件 ID，上传经平台主管文件路由后注册元数据。 | 两端的列表和附件详情已有路径。原生分别返回类型化 `CaseCommentPage`、`CaseAttachmentPage`，保留 `next_offset`，静态平台旧 `RecordPage` 额外宣称 `limitations`。二进制上传和下载属于平台文件接口，原生负责附件元数据。 |

Case 助手随页展示，独立于十个页签。当前客户端读 `/ai/messages?conversation_id&operation_key&limit&offset` 作历史和恢复，并通过固定 Run 工件读取已保存答复。21 平台声明消息 GET，原生当前只挂消息提交与保存入口。会话历史、来源身份和保存答复的读取需要分别核合同。本轮只查源码和元信息。 [案件助手](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseAssistant.tsx:23) · [案件共享 API](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/workbench-api.ts:12) · [成员选择证据](../../../docs/operations/evidence/case-create-readback-20261126-01/member-selection-route-review.json)

## 调查固定 Run 视图

4173 的案内固定 Run 直接保留 `run/view`，脱离 Case 可进入全局 `/investigations/:runId/:view`。8181 案内使用同样的查询参数，显式结果时还保留 `result`。全局目录已读原生 `/analysis-runs`，但行链接仍仅传 Run ID，详情先调用旧 `/runs/{run_id}/context`。原生当前无此路径。21 平台 Q09 有事件专用解析，经步骤目录确认事件主体，再读固定事件轮次和事件详情。告警与 Case 分支仍依赖旧上下文转发，需分别对照来源承载方式。 [全局目录链接](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationListPage.tsx:34) · [固定轮次入口](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/InvestigationDetailPage.tsx:15)

固定 Case Run 的正常明细是 `GET /cases/{case_id}/runs/{run_id}`，结果是 `GET /cases/{case_id}/results/{result_id}`。两端均已挂。原生 `RunDetailWithDirectories` 比旧平台 `Socai2RunDetail` 多 `steps_url`、`artifacts_url`、`previous_run_url` 和 `comparison_result_url`，原生结果也返回两个比较链接。明确的工件和冻结材料分别有同案同轮次的 `/runs/{run_id}/artifacts/{artifact_id}`、`/runs/{run_id}/materials/{material_id}` 普通转发。当前通用工件读取先请求原生未挂的旧全局工件上下文。跟随目录链接前须核权限和主体边界，现有平台 Q27–Q29 对步骤和工件目录附加了告警 Run 校验。告警专用视图在 28083 上已有对应读路由；内嵌事件使用原生事件固定 Run 和 trace，平台静态旧 trace 少两个目录链接。 [固定 Run 工作区](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/investigations/RunWorkspace.tsx:17) · [共用 Run 请求](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-workbench/api.ts:69)

| 4173 与 8181 固定视图 | 当前读源和迁移边界 |
| --- | --- |
| `overview` 调查发现 | 同一 `RunWorkspace` 读取指定 Run，根据显式 `result` 或该 Run 返回的结果目录读保存结果，并检查 `result.run.id`。多结果选择使用真实结果身份和比较来源。 |
| `process` AI 分析与执行明细 | Case 用已读固定 Run 中的步骤、工件和截断标志。告警、事件阶段另读 trace，告警专用视图有已接的分页目录。4173 的执行明细使用 `view=ledger`，8181 使用 `view=process&mode=ledger`。回链需按实际路由保留 Run 和显式结果。 |
| `tools` 查询与证据 | 查询与结果从同轮步骤和工件目录渲染。打开内容时当前共用的旧工件上下文需核真实等价路径，按同案同轮次的工件、冻结材料及原始引用读取。 |
| `graphs` 调查关系图 | 从该结果及轮次工件选择已保存图。图、转入当前案的探索基准和其他轮次的图分别绑定身份，沿图工件与探索基准的正式读取路径。 |
| `report` 报告与响应 | 用指定轮次的已保存结果和报告工件。平台另声明 Case `/responses`，原生当前 OpenAPI 未挂。建议、批准、执行和实际回执分别核真实来源。 |

## 后续接线边界

故事基础读取先对齐 E65 的请求、条目与分页，再逐页推进。统一参考 Case 已用于十页和固定 Run 的原型对照，第三项事件折叠、成员级独立证据与同一 Run 多结果切换保留覆盖缺口。当前对照把旧路由、旧参数、旧 DTO 和平台未挂的原生路径分别列出。平台主管、前端和调查 HTTP 按各页实际依赖接线，并用同案定向核验。容量候选的正式发布及随后的同案复验另按统筹顺序执行。
