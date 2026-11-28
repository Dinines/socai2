# 8181 案件故事单页实施设计

2026-11-26，所属 change 为 `complete-socai2-investigation-chain`。

## 范围与完成效果

本步只迁移 Case 详情的「案件故事」，覆盖 F20-01、F20-02、F20-03、F20-05 及 F14-05 中的故事跳转。8181 恢复登录后已实页复现首屏 422 和失败提示叠加空态。当前前端使用旧参数和偏移分页，21 同案用 E65 正式默认参数及游标续页均已读回。完整交付包含全案统计、搜索与单等级联动、焦点详情、独立勾选和原记录回链。 [逐页实况对照](case-detail-4173-8181-comparison-20261126.md#2-案件故事-story) · [HTTP 核对](case-detail-http-review-20261126.md#2-案件故事-story)

正常进入时直接读本案现存事实、调查和人工完成修订。默认显示混合时间线和真实统计，搜索或选等级后从首页读回。告警焦点驱动右栏，勾选只维护页面选择。右栏所见共同对象和调查都可回实际对象、材料和固定轮次。页面能区分等待、失败、成功空结果、未知时间及源范围未核实。

F20-04 助手仍按项目既定后置范围处理。类型页签和多选等级属于当前 8181 的旧交互，实施范围按已核的 4173 搜索、单值等级、重置、焦点、告警复选及时间线确定。实施限读侧和页面接线，C1 与其他输入冻结沿现有写链。参考案原型显示 2 轮 `baseline` 和 1 轮 `ai_followup`，均属本案，有原型结论投影。正式读侧按已有 Run 和已保存 Result 的实际身份显示。测试沿已有绑定和隔离夹具读回，无需新增 Case、业务写操作、模型调用或部署。 [4173 故事](../../../prototypes/security-pages-v2/case-assistant.js#L127) · [案内 Run 选择规则](../../../prototypes/security-pages-v2/investigation-workspace.js#L103)

## 一、E65 时间线与全案统计

`GET /api/v1/socai2/cases/{case_id}/story` 保留原生路径，由 8181 的 Q13 读取。路由的未知或重复查询参数继续返回 422。

| 请求字段 | 类型与语义 |
| --- | --- |
| `case_id` | 路径 UUID，使用同一 Case 已有身份。 |
| `q` | 可选字符串，最多 200 字符，去首尾空白，空字符串与省略同义。沿现有不区分大小写的字面子串匹配及通配符转义。 |
| `severity` | 可选单值 `info/low/medium/high/critical`，省略为全部。 |
| `limit`、`cursor` | `limit` 默认 20，范围 1–100。`cursor` 可选，最长 2048 字符，用上一页 `next_cursor` 原值，结束为 null。 |
| `view` | 可选枚举，唯一新增显式值 `related`。省略使用原 E65 语义和 `StoryPage`。显式选择后使用下文关联过滤和响应扩展。 |
| `focus_alert_id` | `view=related` 时可选 UUID，用于按完整命中集合解析焦点。未选择该视图时传入返回 422。 |

省略 `view` 时，原封套字段、条目内容、只对告警施加等级条件的行为及旧游标指纹保持原样。旧指纹继续按原租户、Case 和规范化后的 `q/severity` 生成，新增字段的默认值不进入旧序列化。新视图在同一指纹输入上加入视图标识，绑定租户、Case、关键词和等级。`limit`、`cursor`、焦点均不参与过滤指纹。更换 Case、视图、关键词、等级或重置时从第一页读。保持原 E65 实际事件时间、未知时间最后、同时间按稳定条目键倒序的分页规则。每次请求沿现有只读一致快照，跨页期间源记录变化后从首屏重读。 [现行 E65](../../../docs/integration/case-story-http.md) · [游标及查询实现](../../../services/api/app/socai2/case_story.py#L23)

### 响应 DTO

`StoryPage` 保持 `items: StoryEntry[]`、`total: int`、`next_cursor: string | null`、`observed_at: datetime`。`view=related` 返回 `RelatedStoryPage`，以 `RelatedStoryEntry[]` 为条目，并增加 `summary: StorySummary` 和 `limitations: string[]`。下列字段均在该视图返回，可空范围在表中注明。

| 字段路径 | 类型与来源 |
| --- | --- |
| `summary.member_alert_count` | 非负整数。按租户和 Case 的当前 `case_alerts.alert_id` 去重，口径与 E03 `member_count` 同义。与时间线在同一请求内聚合。 |
| `summary.member_object_count` | 非负整数。当前成员关联 `alerts.latest_material_id`，以同租户、同告警、同材料连接 `alert_objects`，按 `object_type,namespace,object_key` 去重。表示正规化投影中已保存的对象数。 |
| `summary.members_without_current_material_count` | 非负整数。当前材料指针缺失或没有同一主体的材料记录的成员数。对象计数展示时以此提示已知覆盖。 |
| `summary.activity_time_from`、`summary.activity_time_to` | 带时区时间或 null。取全案当前成员 `alerts.event_time` 的非空最小／最大值，两端同时未知时均为 null。 |
| `summary.matched_alert_count` | 非负整数。全案当前成员中命中当前 `q` 与单值 `severity` 的告警数。根 `total` 仍表示全部命中的故事条目数。 |
| `summary.focus_alert_id` | UUID 或 null。请求的焦点仍在全量命中告警集合时保留，否则取按 E65 顺序第一条匹配告警。无匹配告警为 null。 |
| `items[].investigation_ref` | 下文 `InvestigationRef` 或 null。调查条目始终带其真实归属和回链，其他条目为 null。 |
| `limitations` | 字符串数组。已关联的历史候选轮无法从可确认的输入还原成员时，包含 `frozen_input_membership_unverified`。无此限制时为空。 |

条目继续使用稳定 `id/kind/occurred_at/time_source`，`kind` 为 `alert/investigation/human_result`。告警仍用 `alert: AlertFacts`，人工仍用 `task_revision: TaskRevisionView` 和 `is_current_task_revision`。已知 Case Run 复用 `run: RunView` 以及 E14 的已保存 Result 投影，保持按保存时间和 ID 排序。相关 A/I 按 `investigation_ref` 显示，其 `run` 为 null，`results` 为 []，阶段结果从同轮 `result_refs` 进入原主体读取。时间线以已有实际 Run 时间、告警发生时间、人工完成时间为准，读取时间只表示观察时点。 [现有 DTO](../../../services/api/app/socai2/case_story_contracts.py) · [E03 成员读侧](../../../services/api/app/socai2/case_reader.py#L244)

### 筛选和数据来源

先以当前正式 Case 成员构成全案范围。告警的 `q` 匹配标题、说明和当前材料已保存对象的 `raw_value/normalized_value`，`severity` 匹配 `alerts.severity`。两条件共同确定匹配告警集合 M。`summary` 的全案字段从未分页的当前成员集合求得，`matched_alert_count` 和焦点使用未分页的 M。

对每个调查或人工完成修订，R 表示其真实冻结成员集合与 M 有交集。显示条件为「关键词为空、自己的可搜索内容命中或 R 成立」并且「等级为空或 R 成立」。自己的内容沿下表指定的已保存字段。缺少可核的冻结成员时，相关性保持未核实。纯文字正例仍按文字规则出现，按相关性得出的确定匹配只使用已验证范围。

| 条目 | 自身内容 | 关联依据 |
| --- | --- | --- |
| Case 调查 | `runs.title/purpose`，同轮实际已保存的 `results.title/conclusion/change_summary/findings[].statement`。 | 有可核 C1 冻结工件时使用该工件确认的同轮输入成员。待启动和未启动取消的暂定成员在下节单独约束。 |
| 告警分诊／事件诊断 | `runs.title/purpose`，按原主体和 `source_run_id` 锁定的 `alert_assessments.rationale` 或 `incident_diagnoses.summary`。 | 已验证的原 Run 固定输入，规则见下节。 |
| 人工完成修订 | `task_revisions.title/description/result_text`，记录状态为 `completed`。 | 同一不可变修订的 `result_scope.alert_ids`。全案范围也以当时显式冻结的列表为准。旧修订回链保留原 `task_id/revision_id`。 |

## 二、时间线与右栏共用的调查范围

查询先确定本租户和 Case，按下列持久来源合并调查，以真实 `run_id` 去重。多条命中路径共同返回来源，由各轮原主体提供结果。

| 关联来源 | 纳入范围和可验证依据 |
| --- | --- |
| `case_owned` | `runs.case_id` 指向本案的基础调查。读取真实已保存状态，成员关系通过下节冻结条件确认。 |
| `saved_result` | E10 可回查的同案真实 Result，包括已有的历史 `ai_saved`，沿 `results.source_run_id` 归入原轮。按实际 Run 类型和保存内容显示。`result_members` 只描述保存结果的范围，输入范围按原 Run 的冻结来源判断。 |
| `explicit_reference` | 有正式源记录的显式关联。沿 `case_assessment_sources.result_id` 到 Result 的原 Run，或由 `artifact_id` 到工件原 Run。当前证据索引使用已保存并通过身份核验的引用。引用类型为 `task_revision` 时，按同租户、同 Case、同任务和指定修订定位，只沿该不可变修订保存的 `source_refs` 解原 Run。 |
| `frozen_member_overlap` | 在下节确认原轮的冻结输入后，关联其中与当前 Case 成员有交集的 A/I Run。显式关联与冻结输入的成员关系分别记录。 |

事件的当前显式关联和当前成员可以帮助缩小候选，查询还须按冻结成员反查历史轮，以覆盖后来变化过的事件关系。R1 的 `case_relations` 用于当前关系统计。故事以本节单独的来源和冻结条件建立关联集合，复用 R1 的原主体链接及保存结果引用。

### 冻结输入判定

| 原轮 | 可用于搜索继承、等级交集和焦点关系的输入 |
| --- | --- |
| Case | C1 启动时按真实范围重建 `run_members`，并保存 `input_snapshot`。通过 `runs.input_artifact_id` 校验工件的租户、Case、Run 和 `kind=input_snapshot`，按已知快照合同确认 `scope.alert_ids` 与同轮输入成员。现行快照为 `socai2.page-model.v1`。 |
| A/I 通用校验 | 按 `runs.input_artifact_id` 关联工件，同时核相同租户、Run 和原告警或事件 ID。工件外层为 `kind=input_snapshot`、`schema_version=socai2.stage-result.v1`，正文的 `version` 同版，`kind` 为与原 Run 对应的 `alert_basic` 或 `incident_diagnosis`。输入须能通过既有原件识别与可用性检查。 |
| 告警分诊 A | 从已验证的同轮快照成员读取原告警身份，与 `runs.alert_id` 核对。 |
| 事件诊断 I | 正文选择版本为 `socai2.incident-selection.v1` 时，仅按 `input_selection.selected_alert_ids` 读取。只有符合已识别旧合同且正文没有 `selection_version` 时，才读 `members[].alert.id`。版本未知、选择字段缺损或身份异常时按未核实范围处理。 |

`pending_update` 的 `run_members` 是暂定行。无可核实际输入的待启动或未启动取消 Run 仍可按真实状态出现在时间线，其可搜索正文沿自身字段，暂定成员对关键词继承、等级交集及焦点关系均无贡献。对已关联而无法核实冻结输入的历史轮保留 `frozen_input_membership_unverified`。 [暂定成员更新](../../../services/api/app/socai2/baseline_store.py#L172) · [C1 保存输入](../../../services/api/app/socai2/baseline_store.py#L289) · [阶段工件及版本判定](../../../services/api/app/socai2/stage_inputs.py#L95) · [事件选择版本](../../../services/api/app/socai2/incident_inputs.py#L3)

`InvestigationRef` 由时间线和右栏复用。它携带以下身份和公开导航字段。

| 字段 | 类型与来源 |
| --- | --- |
| `run_id`、`subject_type`、`subject_id` | UUID、`case/alert/incident`、UUID。由原 `runs` 行及真实父主体确定。 |
| `run_kind`、`title`、`state`、`delivery_state` | 复用 `DirectoryRunKind`、字符串、`RunState`、`Delivery`。均源于原 `runs`，执行状态和交付状态分别显示。 |
| `requested_at` | 带时区时间，来自 `runs.requested_at`。与 `run_id` 一起用于右栏调查目录的稳定倒序。 |
| `detail_url` | 原生相对路径，Case Run 到 E12，告警分诊到 E24，事件诊断到 E25。复用 R1 原主体 URL 规则。 |
| `result_refs` | `DirectoryResultRef[]`，复用 `result_type,id,source_run_id,kind,url`。Case Result 进入 E14，A/I 结果在该阶段的精确 Run 路径读取。已有 R1 的保存结果关联规则可复用。 |
| `relations` | 非空数组。每项为 `kind,source_type,source_id,source_url`。来源类型为 `case/result/artifact/task_revision/run`，身份为 UUID，链接是对应的已登记原生读取路径。以 E03、E14、E43、原工件入口或原 Run 入口核实上述来源。 |

记录查阅沿现有 Case 以及各来源的读取约束。实施为具体表、已支持快照版本上的限定查询、当前页 DTO 装配及接口接线。原文、工件解析与恢复沿现有读取路径。 [统一目录 DTO](../../../services/api/investigation_http/run_directory_contracts.py) · [原主体 URL](../../../services/api/investigation_http/adapters/run_directory.py#L5) · [人工范围校验](../../../services/api/app/socai2/human_task_service.py#L44)

## 三、Case 成员关联读取

`GET /api/v1/socai2/cases/{case_id}/members/{alert_id}/relations`。两个路径字段均为 UUID。确认焦点是当前 Case 成员后读取同一快照，成功返回 `CaseMemberRelations`。`objects_limit` 和 `runs_limit` 默认 20，范围 1–100。`objects_cursor`、`runs_cursor` 各为可选的上页游标，最长 2048 字符。游标绑定租户、Case、焦点及本分区，分别续页。错误父身份或焦点当前不在案内返回 404，未知或重复参数、非法或不匹配游标返回 422，服务读取失败按现有错误规则处理。

| 字段路径 | 类型与来源 |
| --- | --- |
| `case_id`、`alert_id`、`observed_at` | 同一请求的实际 Case／焦点 UUID 和数据库观察时间。 |
| `shared_objects.items[]` | 每项包含字符串 `object_type,namespace,object_key,label,material_url`、UUID `focus_material_id,focus_object_id` 和正整数 `other_alert_count`。同案其他成员的当前材料按 E30 的三键与焦点的当前对象匹配，按不同告警计数。重复来源路径合并，选该组焦点对象中 ID 最小的实际行，`label` 取其 `raw_value`，`material_url` 指向对应 E31。按代表对象 ID 升序分页。 |
| `investigations.items[]` | `InvestigationRef[]`。按上节真实关联集合再要求原 Run 冻结输入包含焦点。按原请求时间与 Run ID 倒序，包含已有真实状态与不同结果身份。 |
| `shared_objects.total/next_cursor`、`investigations.total/next_cursor` | 非负整数和字符串或 null。各为已确认全集的条目数及本分区续页位置。 |
| `shared_objects.limitations`、`investigations.limitations` | 各为字符串数组。缺当前成员材料的对象分区可带 `current_member_material_unavailable`，不能确认旧冻结输入的调查分区可带 `frozen_input_membership_unverified`。确认完整时为空。 |

对象匹配在本案全范围进行，焦点来自故事的当前命中结果。切换焦点时重置右栏两组游标，复选独立维护。右栏的关系图入口回同案关系图，图内功能归其自身迁移步骤。新增路径在平台代理的案内读取中登记，使用现有 Case 与来源读取约束。 [既有对象匹配](../../../services/api/app/socai2/page_reader.py#L364) · [原生材料路由](../../../services/api/investigation_http/external_routes/pages.py#L157)

### 原记录回链

下列已有 GET 路径均以 `/api/v1/socai2` 为前缀。Case、告警或事件的父身份以条目和引用返回的原主体为准。

| 来源 | 路径 |
| --- | --- |
| 告警、当前对象和指定材料 | E28 `/alerts/{alert_id}`，E30 `/alerts/{alert_id}/records/objects`，E31 `/alerts/{alert_id}/materials/{material_id}` |
| Case Run 和已保存结果 | E12 `/cases/{case_id}/runs/{run_id}`，E14 `/cases/{case_id}/results/{result_id}` |
| 告警分诊和事件诊断原轮 | E24 `/alerts/{alert_id}/analysis/runs/{run_id}`，E25 `/incidents/{incident_id}/analysis/runs/{run_id}`。阶段结果在原轮读取。 |
| 人工完成修订 | E43 `/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` |

## 四、顺序、必要测试与通过条件

待主规格及任务同步后，实施前运行 `openspec validate complete-socai2-investigation-chain --strict --no-interactive`。以本页为交付范围，按下表验过一步再推进依赖步骤。已有读回和直接测试入口优先复用。

| 步骤 | 最小直接测试及通过条件 |
| --- | --- |
| 1. 后端实现及直接核验 | 实现 E65 `view=related` 和成员 `relations` 两个只读合同及旧 E65 兼容。用同一既有隔离 Case 核旧参数 200、原条目形状及旧游标直接续页。新视图核 E03 和 PG 全案统计、搜索经命中成员带出 Run／人工修订、单等级收窄及游标顺序。用可查的正式显式来源及相关 A/I 固定输入核原主体、事件关系变化和多路径去重。两个焦点的共同对象和对应调查分别核字段来源及小页续读，并区分历史输入未核实、有效空集和非成员错误。待启动及未启动取消另验下述冻结边界。 |
| 2. 平台本机接线 | Q13 逐项透传新视图及查询参数，成员关系 GET 登记到 Case 路由。用同一既有 Case 从本机平台直接读取两个 GET 入口，核 200、响应形状、原身份、正式游标与上游一致。实际错误按现有平台方式返回。 |
| 3. 8181 一次迁成整页 | 首屏直接消费 `view=related`，右栏使用成员 `relations`。在同一实际 Case 自验默认时间线、统计、搜索、单等级、重置、独立复选、焦点、翻页和原记录回链。接口 200 且无条目时显示相应空态，首屏失败显示错误和重试，翻页失败保留已读内容及原游标重试。 |
| 4. 统筹整页验收 | 对照 4173 核首屏统计、筛选行、混合时间线、独立未知时间组及焦点详情。验右栏两组列表、原记录回链、默认视口和浮层。使用已有 Case 保存实际 8181 读取、关联断言及页面表现证据。 |

**待启动输入单项直验。** 用隔离夹具中的待启动及未启动取消 Run，确认暂定成员中有当前焦点告警且无可核输入工件。无筛选时读到原状态。以只命中该告警的关键词读取时，两轮均无成员继承命中。选择该告警等级后，两轮均无等级交集，焦点关系查询也无两轮。以同告警实际进入 C1 冻结输入的已存 Run 作正例，核三处均可按已保存输入命中。测试只读已备记录。

后端兼容直接验证复用 `verify_story.py` 的 `verify`／`snapshot-verify` 读取已有夹具，也可复用现有 Case HTTP、统一目录和人工修订夹具，均沿正式保存身份读回。旧参数 200 和旧游标复用是后端兼容验收，产品在第 3 步接完整新合同。生产查询按租户、Case、当前成员或原 Run 的实际范围聚合及分页。数据证据留本机，回执记录结构、状态和覆盖。统一参考案用于 Case 自有轮和页面行为，跨主体与显式引用各用可核的来源正例。单页以全部必要交互、真实读回和视觉对照通过为完成条件。 [故事直验脚本](../../../deploy/http-service/verify_story.py) · [Case HTTP 直验](../../../services/api/tests/test_socai2_case_update_http_pg.py) · [统一目录直验](../../../services/api/tests/test_socai2_run_directory_pg.py) · [逐页验收清单](investigation-page-migration-checklist-20261126.md#案件故事)

### 前端拆分与定向用例

冻结合同和平台候选类型齐备后，可并行编写尚未挂载的专用故事组件、样式及定向用例；不替换当前路由，不先把旧页接成半套合同。两项 HTTP 直接验收与平台本机接线通过后，在第 3 步一次挂载完整故事时间线和成员关系，随后核实际页面。

| 实施位置 | 本页改动 |
| --- | --- |
| `CaseStory.tsx`、`CaseStory.css` | 专用故事标题与历史入口、全案统计、搜索／单选等级／重置、混合时间线和焦点右栏。保持服务端条目顺序，未知时间独立成组。告警聚焦与勾选分别维护。 |
| `CaseWorkbenchDetail.tsx`、`CaseReadPanels.tsx` | 原故事路由接专用组件，按 Case 身份重置页面状态。将旧故事和选区查询从共享文件移出，活动页继续使用原入口。 |
| `workbench-api.ts`、本页平台生成类型 | 故事直接消费 `view=related` 与正式 `next_cursor`。焦点由 `summary.focus_alert_id` 初始化，复用 E28 告警详情与成员关系读取。右栏续页使用各自游标，切焦点时重置两个分区。 |
| 原主体回链 | Case Run 链接显式携带 `run`，保存结果同时携带 `result`。相关告警和事件分诊按原主体及固定 Run 进入，人工完成回不可变修订。未启动 Run 只显示真实状态及已提供的暂定范围，冻结输入及参与关系以已核实的实际记录为准。 |

整页视觉沿 4173 故事样式迁移：保留时间线竖线与圆点、选中卡边框与圆点高亮、无框范围横行、浅蓝选择条、普通标题的深色及悬停色、双列间距和浅色详情栏。原型提问入口保留明确的不可用态，本步不启用后置的问答或模型调用。相关 A/I 工作卡摘要沿已有 E24/E25 固定轮读取其已保存正文，复用对应缓存，仅读取已载入卡片所需结果；不得用 latest 或其他轮次正文补齐。原本材料或结果不可用时按实际状态显示。右栏保留时序与共同对象不代表攻击因果的说明。

#### 告警卡的等级、战术和对象标签

- 等级直接用 `items[].alert.severity` 和现有 `SeveritySignal`。战术复用 `workbenchApi.subject('alerts', id)` 的 E28 请求和 `workbenchKeys.subject('alerts', id)` 缓存，焦点详情与卡片共用该读取。显示 `derived.tactics[].label`，来源是告警当前已保存材料的检测标签。告警 `category` 保持原分类含义，AI 分诊映射另沿告警原页查看。[4173 告警卡](../../../prototypes/security-pages-v2/case-assistant.js#L132) · [告警事实及派生字段](../../../services/api/app/socai2/page_contracts.py#L47) · [检测标签取数](../../../services/api/app/socai2/page_reader.py#L145) · [现有 E28 客户端](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/AlertWorkbenchDetail.tsx:138) · [等级组件](/Users/lychee/Projects/SpiritHub-web-8181/web/src/shared/ui/SeveritySignal.tsx:6)
- 卡片底部最多展示 3 个该告警的已保存对象标签。E30 `GET /alerts/{alert_id}/records/objects` 返回当前材料的对象记录，标签使用 `items[].raw_value`。只处理已载入故事告警，优先复用现有 E30 已载入记录。需要请求时只读 `limit=3&offset=0` 的首段，缓存与完整目录分开。以 `alert_id` 和 `material_id` 校验归属并按类型、命名空间和对象键去重。右栏 `shared_objects` 表示与本案其它告警共有的集合。E31 沿原材料入口按指定版本打开。[E30 正式分区](../../../services/api/investigation_http/external_routes/pages.py#L131) · [E30 当前材料连接](../../../services/api/app/socai2/page_reader.py#L81) · [告警对象记录展示](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/socai2-alerts/AlertWorkbenchDetail.tsx:261)
- 首次读取、无已记录战术或对象、材料不可用及请求失败分别显示。E30 原生读取当前材料，`AlertFacts.latest_material_id` 和 E28／E30 的材料版本不一致时提示材料已变化，可刷新故事重新核对。卡片依赖部分读取失败时仍显示 E65 已读事实。

定向用例沿用 Case 路由测试装配、游标读取和分页控件。使用隔离结构夹具补足以下直接回归。

1. 通过现有入口检查首读、关键词／等级变化和重置。请求只含约定键，续页原样传游标。422 仅显示错误和重试，成功无命中显示空态，续页失败后保留已读内容。
2. 第一页只有调查或人工条目时，按摘要给出的焦点 ID 发 E28 与成员关系请求。勾选告警时焦点保持，切换焦点后两分区从首页读。分别触发共同对象与相关调查续页，核每次只发送目标分区游标并合并相应内容。
3. 同页核 Case Run、其保存 Result、相关阶段轮和人工修订的回链身份。已有暂定范围的未启动 Run 保留其状态语义，关联范围按正式响应显示。
4. 用 E28 保存的战术标签和 E30 当前材料对象核同一告警卡。等级保留正式值，对象最多三项，包含该告警独有对象时仍可显示。用材料缺供或读取失败核局部状态，故事事实与右栏共同对象各依正式来源。

候选接线后运行 `npm run typecheck` 及故事、现有 Case 路由与分页定向检查。随后用已有 Case 和 4173 主参考核默认展示、正常路径及原 422 阻断。 [案内路由](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseWorkbenchDetail.tsx:71) · [现有 Case 深链测试](/Users/lychee/Projects/SpiritHub-web-8181/web/src/features/soc-cases/CaseDeepLinks.test.tsx:28) · [游标读取](/Users/lychee/Projects/SpiritHub-web-8181/web/src/shared/query/useInfiniteTableQuery.ts:6) · [分页控件测试](/Users/lychee/Projects/SpiritHub-web-8181/web/src/shared/ui/InfiniteTableFooter.test.tsx:10)
