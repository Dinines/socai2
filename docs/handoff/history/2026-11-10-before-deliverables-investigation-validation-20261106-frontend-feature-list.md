> 此文件保存 2026-11-10 整理前的过程快照，仅供追溯。当前说明见仓库入口。

# 告警、事件与 Case 页面功能清单 V1

**交接目标**　用户从一条告警出发，能回答四个问题：收到了什么、为什么归入该事件、案件当前采纳了什么判断、某一轮调查实际做了什么。告警、事件、Case 三个页面可并行开发。调查运行详情是三个页面共用的下钻入口。

本清单供产品、前端和业务后端共同签收。下表按页面给出功能、字段和数据出处；**J01–J14** 给出每个跳转的输入、目标、关联键及缺值行为。表中的“可读”指处理模块已提供读取合同；“组合”指业务后端需按给定关系组装；“待接”指页面或服务仍缺接线。数据库表、接口、权限、读回 SQL 见[服务端数据交接 V1](../../investigation/socai2-page-data-handoff-20261106.md)。有值样例与导出位置见[逐字段样本](../../../deliverables/investigation-validation-20261106/page-field-samples.md)。

按交接角色查阅：[告警页](#告警页) · [事件页](#事件页) · [Case 页](#case-页) · [调查运行](#共用的调查运行详情) · [跳转规格](#跳转与关联规格) · [案例签收](#案例签收)

## 入口与身份约定

| 页面 | 用户从哪里进 | 打开详情所需的身份 |
| --- | --- | --- |
| 告警 | `#/alerts` → 概况、时间线、原始数据、响应 | `A = alerts.id`。第三方告警号 `source_alert_id` 供展示与溯源。 |
| 事件 | `#/incidents` → 事件概览、关联分析、成员告警、涉及对象、处理活动 | `I = incidents.id`。成员由 `incident_alerts` 确定。 |
| Case | `#/cases` → 案件资料、调查概览与历史、案件故事、成员、关系图、证据、任务、活动、评论与附件 | `C = cases.id`。本案正式成员来自 `case_alerts`，显式关联的事件来自 `case_incidents`。 |
| 调查运行 | Case 历史、主体的分析入口，或运行列表 `#/investigations` | `R = runs.id`。处理流程中，告警分诊简称 A，事件诊断简称 I，Case 基础调查简称 C；表中的 `{A}`、`{I}`、`{C}` 始终指页面主体 ID。调用读取接口时另带该 Run 的实际父主体 UUID。 |

下文 HTTP 路径省略 `/api/v1/socai2`。业务接口用授权租户内的原始 UUID。四案预览的 `#` 路由用显示 ID：`socai2!<环境>!<批次>!<租户>!<alert或incident或case或run>!<UUID>`。跳转时取该记录的显示 ID，查询参数按 URL 编码；在数据库或接口中逐项核对原始 UUID。`?data=service#/cases` 为已接入部分 Case 操作的服务模式。[四案预览与数据包](../../../deliverables/investigation-validation-20261106/21-qwen9b-handoff-cases-20261106.zip)

## 告警页

详情地址为 `#/alerts/{A}/{页签}`。概况 `overview`、时间线 `timeline`、原始数据 `raw`、响应 `response` 共用同一告警 ID。

| 功能与用户目的 | 页面需要的字段 | 数据来源、点击及状态 |
| --- | --- | --- |
| **F01 列表与概况**。找到需要处理的告警，确认发生时间、来源和负责人 | `facts.id/title/description/severity/handling_status/disposition/event_time/event_time_source/ingested_at`，`original_vendor/source_alert_id/assignment_state/owner_id/priority_state/priority_value/tags`；`owner_name/owner_resolution` | 可读。`GET /alerts`、`/alerts/{A}`，事实来自 `alerts`。统计取 `overall_stats`，高严重度含 high、critical，调查中按运行中的基础调查去重告警。点行或抽屉用 J01。列表合同有分页；界面本地搜索/筛选仅作用已载入集合。发生时间、负责人或来源厂商缺失时分别标明。 |
| **F02 检测信息**。辨别是哪条规则触发、检测器给了什么分数 | `facts.latest_material_id`、`material.detection` 中实际提供的规则、检测置信度及其量纲、ATT&CK 战术与技术标签；材料版本、来源 | 可读。`alerts.latest_material_id → alert_materials.id`。概况显示检测器的值；点原件用 J02。缺少标签保留空态，AI 分诊置信度另列。 |
| **F08 关联实体、IOC 与相关告警**。看同一对象还出现在哪些告警，打开候选逐条核查 | `object_type/namespace/object_key/object_role/material_id`、候选 `id/title/severity/event_time` | 概况的对象读 `/alerts/{A}/records/objects`。服务的 `records/related_alerts` 按同类型、同命名空间、同对象键匹配；四案预览展示按主机筛出的近期告警，两种集合的筛选条件应注明。点候选用它自己的 ID 打开 J01；共享对象或 IOC 标签只表示待核对关联。 |
| **F03 分诊、解释与人工反馈**。区分模型判断和分析员意见，回查理由 | `triage.verdict/confidence_percent/rationale/source_run_id/valid_for_current_input`、`feedback`、`facts.latest_explanation_id`；本次尝试的 `run.state/stop_reason` | 可读。两个指针 `latest_triage_id/latest_feedback_id` 分别连 `alert_assessments` 对应类型；分数、理由和判定取同一条分诊。`analysis_url` 给分析目录。点“查看分诊与依据”用 J04；预览有匹配的完整解释才显示此入口。分诊拒收或超时仍展示告警、已有分诊及本次尝试状态。 |
| **F04、F05 原始数据与来源**。核实系统收到的原文、标准化内容和来源标识 | `material.id/revision/sha256/material_state`、正文 `raw_json/raw_text/ocsf_json/enrichment`；`source_namespace/source_event_id/relation_kind/source_path` | 可读。原文按 J02 读 `alert_materials`；`/alerts/{A}/records/sources` 从当前材料的 `alert_source_refs` 取引用。来源快照按有权限的已保存工件查。来源 ID 连同命名空间展示，外部源未接通时仍展示已有引用。 |
| **F01、F23 时间线与管理**。按时刻核对发生、入库和处置变更 | 告警时刻、`activities.occurred_at/action/summary`、`matching_targets[].before_value/after_value/result_state`；状态、负责人 | 时间线组合告警事实与 `/alerts/{A}/records/activities`。预览按时间列为静态条目；业务页提供来源链接时，关联主体按 J03/J05 定位。活动保留实际时间与操作者。处理状态、负责人等管理字段可读；预览管理操作及批量编辑的业务写回待接。 |
| **F27 响应**。看关联调查、处理建议和实际执行凭据 | `run.id/kind/state`，建议的 `recommendations`；响应关联的 `proposal_id/approval_id/action_id/receipt_artifact_id` | 分诊或 Result 建议按各自来源展示；`/alerts/{A}/records/responses` 读 `response_links`。点关联调查用 J04/J07、回执用 J13。审批或动作编号只能定位外部记录；有执行回执才能展示其实际结果。预览未接执行回执。 |

## 事件页

详情地址为 `#/incidents/{I}/{页签}`。事件概览 `summary`、关联分析 `attack`、成员告警 `alerts`、涉及对象 `assets`、处理活动 `activities` 共用同一事件 ID。

| 功能与用户目的 | 页面需要的字段 | 数据来源、点击及状态 |
| --- | --- | --- |
| **F06 队列与事件概览**。找到待处理事件，核对影响范围 | `facts.id/title/handling_status/assignment_state/owner_id`，`derived.severity_effective/severity_source/member_count/object_count/first_activity_at/last_activity_at/unknown_event_time_count` | 可读。`GET /incidents`、`/incidents/{I}` 读 `incidents` 及当前 `incident_alerts → alerts`。有效严重度优先人工覆盖，再按成员推导。活动时间按成员发生时间计算；有缺时成员显示缺失数。列表统计取 `overall_stats`：“近 24 小时新增告警”统计该窗口内有成员告警的**事件数**。列表点事件 J01，关联 Case 用 J05。 |
| **F07 已发布诊断与本次尝试**。分别回答“目前可引用什么”及“这次诊断怎么样” | `current.result.summary/diagnosis/open_questions`；目录 `entries[].run.id/state/stop_reason`、发生时刻 | 可读。`incidents.latest_diagnosis_id → incident_diagnoses.id`；目录从 `/incidents/{I}/analysis` 取。点击具体尝试用 J04。没有已发布摘要时显示原因及本次状态，成员照常列出；事件概览到 I Run 的按钮待接。 |
| **F06、F08 关联分析与成员告警**。解释每条告警为何归入该事件 | `items[].id/title/severity`、`linked_at/membership_source/correlation_basis/basis_version`；归并依据里的 `method/reason/object_keys` | 可读。`/incidents/{I}/records/members` 经 `incident_alerts.alert_id → alerts.id`。关联分析展示共有对象及已存归并理由；规则号、窗口缺值时按实际显示。成员行点标题先开抽屉，再点“打开告警页”走 J03。 |
| **F08 涉及对象与资产**。看哪些主机、账号或端点出现在成员材料中 | `namespace/object_type/object_key/object_role/material_id/alert_id`、`asset_ref/asset_match_state`；库存命中另有 `asset_id/match_basis` | 可读。`records/objects` 读当前材料中的 `alert_objects`；`records/assets` 按主机名、FQDN 或 IP 与同租户 `public.assets` 匹配。点击对象查看所属告警/材料（J02/J03）。同一对象可能匹配多个库存资产；未命中时仍展示来源对象。 |
| **F23 处理活动**。看谁在哪个时候变更了哪些对象 | `occurred_at/actor/action/summary`、`matching_targets[]` 的目标 ID、前值、后值、结果、原因 | 可读。`/incidents/{I}/records/activities` 从 `activities → activity_targets` 返回本主体匹配目标，单活动最多 200 条。页面可以另列诊断或步骤；分别标注来源。点目标用 J03/J04/J05。状态与严重度覆盖信息可读；预览通用管理写回待接。 |

## Case 页

详情地址为 `#/cases/{C}/{页签}`。案件资料 `case-info`、案件故事 `story`、调查概览 `overview`、调查历史 `investigations`、成员告警 `alerts`、案件关系图 `attack`、对象与证据 `evidence`、人工任务 `tasks`、处理活动 `activities`、评论与附件 `comments` 共用同一 Case ID。

| 功能与用户目的 | 页面需要的字段 | 数据来源、点击及状态 |
| --- | --- | --- |
| **F09 队列与资料**。确定谁负责、当前状态，以及有哪些成员和待办 | `case.id/title/description/handling_status/severity/owner_id/assignment_state/tags/priority_value/created_at/business_updated_at`；`member_count/open_task_count/baseline_records` | 可读。`GET /cases`、`/cases/{C}` 以 `cases` 为主，队列统计取 `metrics`。按 `q/handling_status/severity/owner_id/assignment_state/metric/classification` 筛选；换筛选条件重新取游标。点案件用 J01，点基础调查用 J07。 |
| **F10 案件分类与期限**。记录管理标签和本案截止时刻 | `page_data.classification/due_at`、`case.row_version`；分类取 `true_positive/informational/false_positive` 或空 | 可读写。`cases.classification/due_at`；`GET/PATCH /cases/{C}/page-data`。提交分类和期限两个字段、`operation_key/expected_row_version/source/source_note`，成功后重读；行版本冲突提示刷新。功能落点为页内编辑，四案预览只读。空值分别显示“未分类”“未设期限”。 |
| **F11、F12 当前判断、来源与覆盖**。读当前采纳的判断，并确认覆盖了哪些告警、依据有没有变化 | `page_data.determination` 为判断文本；`assessment.origin/validity/formed_at/adopted_at/alert_ids/sources`（位于 `page_data`）；详情另取 `current_assessment.input_freshness` | 可读。`cases.current_assessment_id → case_assessments`；成员与来源读 `case_assessment_members` 和 `case_assessment_sources`。显示模型、人工或系统来源，分别展示覆盖数和已跟踪输入的新鲜度。点依据用 J09。没有当前判断就显示“尚无已采用判断”；某轮失败可与既有判断同时展示。 |
| **F13 正式成员与关联事件**。确认案件范围，查看来源或调整成员 | `members[].alert_id`、`linked_incidents[].incident_id`、数量及截断标志、`case.scope_revision` | 可读写。`case_alerts/case_incidents`。点成员打开告警、点显式关联事件打开概览（J06）。已有服务命令支持建案、加关联、替换及跨案移动成员（J14）；共享告警形成的间接关联要标注依据。 |
| **F14、F16 调查概览与历史**。列出基础调查及与本案成员有关的分诊、诊断，选择要看的那一轮 | `run.id/kind/state/delivery_state`、时间，`result.id/source_run_id/case_impact`、主体 ID | 组合。`/cases/{C}/history` 给本案基础调查及已明确保存的助手结果；相关 A/I 按成员及关联事件各读分析目录，Run 按 `id` 去重。点具体轮次用 J07。只有正式结果可点 J08，本案当前判断单列。 |
| **F20 案件故事**。按发生顺序还原已知事实、执行过程与人工反馈 | 告警 `event_time`、Run `started_at/ended_at`、Result `saved_at`、已完成任务版本 `completed_at/result_text` 和各自 ID | 组合。按记录类型取 `alerts/runs/results/task_revisions`，标明“告警发生／调查开始或结束／结果保存／人工完成”。时间未知的单列。点击回到告警、执行或任务版本（J06/J07/J11）。 |
| **F19、F25 关系图与探索**。查某轮已保存图，区分图上临时选择和保存的探索 | `result.graph_artifact_id`、图工件的 `nodes/edges/source_refs`；探索的 `base_result_id/base_graph_artifact_id/base_input_artifact_id/graph_state/row_version` | 已保存图可读（J10）。探索有 `graph_explorations` 表；预览可在本页选节点，持久保存与再次打开的服务接线待验。无图时标明无图，仍可查成员和证据。 |
| **F21 对象与证据**。核对独立证据、关联威胁及每一条的依据 | `page_data.evidence.state/evidence_count/threat_count/covered_alert_ids/uncovered_alert_ids/limitations`；条目的 `evidence_id/verdict/alert_ids/source_refs/threat/remediation` | 可读。`cases.current_evidence_artifact_id → artifacts` 中的证据目录。只统计有效且成员全部在本案范围内的条目；可疑或恶意且有威胁身份的按 `namespace + key` 去重。缺索引显示“未记录”，有效空索引显示 0，部分可用显示限制。点来源用 J12；处置依据用 J13。 |
| **F22 人工任务**。看谁需补什么材料、最新答复适用于哪些告警 | `task.id/current_revision_id`、当前版本的 `state/assignee_id/due_at/result_text/result_scope/completed_by/completed_at` | 可读写。`/cases/{C}/tasks`，`tasks.current_revision_id → task_revisions.id`；点任务和指定修订用 J11。创建或更新后读回版本。完成任务只在声明范围内提供人工结果；判断采用情况读 F11。 |
| **F23 处理活动**。回看案件或成员调整及实际影响 | `activities.id/occurred_at/action/actor/summary`、`activity_targets.activity_id`、具体目标 ID、`before_value/after_value/result_state/reason` | 数据已存时可按 C 查询；Case 完整活动列表待业务后端组装。预览会混列步骤和其他记录，完整目标前后值未接入。点活动本页展开各目标，按类型回到 J06/J07/J08/J11。 |
| **F24 评论与附件**。查看人工备注、作者与附带文件 | `comments.case_id/body/author_id/author_name_snapshot/created_at/edited_at`；附件 `artifacts.id/case_id/kind/file_name/mime_type/size_bytes/sha256` | 告警/事件可读各自 `records/comments`；Case 的表有归属字段，评论与附件列表、上传及受控下载待接。打开附件要用本案附件 ID 和授权内容入口。预览固定空附件、评论表单只读。正式页应区分“未接入”与“已查询、无记录”。 |
| **F26 案件助手**。区分提问、保存一个回答、人工采用为当前判断 | `conversations.id`、`messages.id/conversation_id/content`、`results.source_answer_id`、`case_assessment_sources.result_id` | `conversations/messages` 有存储设计。提问、保存回答、显式采用三个服务入口为 501；四案只读 Case 隐藏助手，演示 Case 提供本地预置问答。业务页如保留入口，应标“未开放”。 |

## 共用的调查运行详情

独立详情五个入口为“调查发现”“AI 分析”“查询与证据”“调查关系图”“报告与响应”。“执行明细”在“AI 分析”下。全局列表是页面入口，跨告警、事件、Case 的运行目录需按授权主体组合，服务层目前按各主体读取。

| 功能与用户目的 | 页面需要的字段 | 数据来源、点击及状态 |
| --- | --- | --- |
| **F14–F16 调查发现** `overview`。确定是哪轮、为何停、交付了什么 | `run.kind/state/delivery_state/stop_reason/requested_at/started_at/ended_at/limits`；`results.conclusion/findings/questions/change_kind/change_summary/comparison_result_id/case_impact`、`result_members.conclusion_covered` | A/I 从主体 `analysis` 读；Case 从 Run、Result 分开读（J07/J08）。耗时只用已知起止；模型用量只计实际模型步骤，未知 token、未定价费用分别标出。成员纳入调查和模型判断覆盖人数分别展示。 |
| **F17、F18 步骤与输入输出** `process → ledger`。定位失败步骤，查看该步收到和产出的原文 | `run_steps.id/run_id/seq/parent_step_id/stage_code/name/state/error`、`input_artifact_id/output_artifact_id/reused_artifact_id`；`artifacts.kind/content_json/content_text/sha256/size_bytes` | 可读。按同轮 `seq` 排序、按 `parent_step_id` 展开；点“输入”或“输出”用 J10。“本轮初始输入”是调查开始时冻结的材料版本；“步骤输入”是这一步实际采用的参数或工件。仅有目录、正文受限或步骤未产出时显示各自原因。 |
| **F18、F28 查询与证据** `tools`。核对访问了哪个来源、参数和实际返回 | `run_steps.name/provider/state/actual_args/returned_rows/error`、查询请求及返回的工件 ID、`source_refs` | 可读。按本轮工具步骤查材料，来源可能为资产、知识、历史记录或数据湖。点查询、证据行打开对应步骤或原件（J10/J12）。“跳过”“查询成功且 0 行”“调用失败”“复用已有材料”分别展示；外部来源不承诺一直在线。 |
| **F19 调查关系图** `graphs`。确认特定结果使用了哪些节点、边、依据 | `result.id/source_run_id/graph_artifact_id`、图工件的 `nodes/edges/source_refs` | 从所选结果进入 J10，点节点查看其来源（J12）。仅有事件成员关系时在事件页展示归并依据；调查关系图需有对应图工件。 |
| **F16、F18、F27 报告与响应** `report`。看本轮可读报告、建议，以及有凭据的执行 | `delivery.markdown_artifact_id` 或明确关联的报告工件、`result.report_artifact_id/recommendations`、响应关联和回执 ID | 报告按本轮 J10 打开；有建议则列建议，有执行凭据再走 J13。Run 无正式 Result 时仍可展示已经保存的系统收尾说明、失败位置和可见材料。 |

## 跳转与关联规格

表中 `{A}/{I}/{C}/{R}` 表示目标页的身份占位；HTTP 输入用业务 UUID，预览地址用前述显示 ID。每次查找同时限定授权租户、实体类型和父主体。对同页抽屉展开保留当前页上下文。

| 编号／用户点击 | 起点需要传什么 | 目标、关联字段与异常处理 |
| --- | --- | --- |
| **J01 队列 → 详情** | 当前行 `facts.id`（告警/事件）或 `item.case.id`（Case） | 告警 `#/alerts/{A}/overview`、事件 `#/incidents/{I}/summary`、Case `#/cases/{C}/case-info`。行内入口或抽屉的“打开详情”均以选中行的 ID 为准；无权或不存在时停止下钻，给明确提示及返回入口。 |
| **J02 告警 → 原始材料** | `A + material.id`；看当前原件时从 `facts.latest_material_id` 取，回查某轮则取当时记录的版本 | `#/alerts/{A}/raw` 是当前告警原件页；`GET /alerts/{A}/materials/{material_id}` 校验材料归属。回看冻结版本用同轮记录/正文入口，不能偷偷切到当前版本。受限或无正文仍显示材料 ID、版本和可用性。 |
| **J03 告警 ↔ 事件成员** | 从 A 取 `/alerts/{A}/records/incidents` 的 `items[].id`；从 I 取 `/incidents/{I}/records/members` 的 `items[].id` | 共用 `incident_alerts(alert_id,incident_id)`。告警“关联事件”到 `#/incidents/{I}/attack`；事件 `/alerts` 页签点成员标题先开抽屉，点“打开告警页”进 `#/alerts/{A}`（默认概况）。无成员则保留事件和空列表。 |
| **J04 告警／事件 → 本次分析** | 父主体 `A` 或 `I`、对应目录 `entries[].run.id`；查看已发布分诊时用 `triage.source_run_id` | `#/investigations/{R}/overview`；按 `/{alerts或incidents}/{主体ID}/analysis/runs/{R}` 读取，核 `runs.alert_id/incident_id`。没有已发布结果时仍可从目录开尝试。四案首页提供 I Run 深链，事件概览对应入口待接。 |
| **J05 告警／事件 → 关联 Case** | 父主体的 `records/cases` 返回 `items[].id/via_member_alert/explicit_incident_link` | `#/cases/{C}/case-info`。`case_alerts.alert_id` 给成员关系，`case_incidents.incident_id` 给显式关系。单条直达、多条供选择；零条显示“未建案/无关联案件”。无 `cases:read` 按权限处理。候选建案 ID 不生成详情链接。 |
| **J06 Case → 成员／事件** | `C + members[].alert_id` 或 `C + linked_incidents[].incident_id` | 案件资料“查看告警”到 `#/alerts/{A}/raw`；成员信息按告警详情读取。显式关联事件到 `#/incidents/{I}/summary`。核 `case_alerts/case_incidents`；分页或截断要显示已加载数量及总数。 |
| **J07 Case 历史 → 指定运行** | `C + R + view`；读取前保留运行的父主体类型及 UUID | `#/cases/{C}/investigations?run={R}&view={view}`，默认 `overview`；独立入口 `#/investigations/{R}/{view}`。Case 基础调查读 `/cases/{C}/runs/{R}`；成员 A/I 走 J04 的父主体接口。无匹配运行显示“无关联运行”。 |
| **J08 运行 → 正式结果／比对** | `C + result_id` 及当前 `R`；上一次用于比较的结果以 `comparison_result_id` 为准 | 调查发现或报告页内读 `/cases/{C}/results/{result_id}`，核 `results.case_id/source_run_id`。比对目标需明确存在并属于本案。没有 Result 时保留 Run 和已存工件，不生成结果详情。 |
| **J09 当前判断 → 形成依据** | `C + current_assessment_id`，所选来源行的 `result_id/artifact_id/task_revision_id` | `case_assessment_sources.assessment_id` 定位该判断的来源，按类型进 J08、J10 或 J11；覆盖范围取 `case_assessment_members`。保留来源行的具体身份；定位不到时显示“来源不可用”。 |
| **J10 步骤、报告、图 → 工件正文** | 父主体 + `R + artifact_id`；步骤传所点输入/输出指针，报告/图传明确引用；复用另取来源归属 | A/I 用 `/{subject}/{id}/analysis/runs/{R}/artifacts/{artifact_id}`，Case 用 `/cases/{C}/runs/{R}/artifacts/{artifact_id}`；在明细、报告或图页展示。核实际 `artifacts.run_id`。跨轮复用应带来源轮次；非 Run 工件按自身归属解析。正文缺失/超限/仅外部引用时给原因。 |
| **J11 任务 → 指定人工版本** | `C + task_id`，当前版本取 `current_revision_id`，历史记录取所选 `revision_id` | 案件 `tasks` 页签内查看，`/cases/{C}/tasks/{task_id}/revisions/{revision_id}`。核 `task_revisions.task_id` 和任务所属 Case；范围、完成人、完成时间全部读该版本。 |
| **J12 证据／对象 → 来源记录** | `C + evidence_id` 或同主体的对象身份；从条目读 `source_refs[].type/id/source_path`，对象用 `material_id + object_key` | 在 `evidence` 或 `tools` 页内展开。按引用类型定位同范围材料、结果、人工版本或回执，再定位保存的 JSON 路径；按需进 J02/J08/J10/J11。对象名称只展示。来源暂不可读时保留其身份和限制。 |
| **J13 响应 → 外部审批、动作或回执** | 本主体、`result_id + proposal_id`（若来源为正式建议）、`external_namespace + approval_id/action_id`；回执另用 `receipt_artifact_id` | 响应页内按 `response_links` 查真实关联；已接且有权限时才打开命名空间对应的审批/动作详情或受控回执。当前未约定外部前端 URL，只有编号时显示编号与来源；没有回执就显示“无执行回执”。 |
| **J14 新建／关联／移动／启动** | 建案传 `operation_key/title` 和至少一个选中的 `alert_ids/incident_ids`；关联带 `C + expected_scope_revision + operation_key` 和所选 ID。移动传源 C、`target_case_id/alert_ids/operation_key`、双方 `expected_*_scope_revision`。准备和启动各传 `operation_key/expected_scope_revision`，启动路径另带 `pending_run_id` | 用户明确提交后用服务回执返回的 Case/成员/Run 打开 J01/J06/J07。基础调查先 `/baseline/prepare` 后 `/runs/{R}/start`；查详情不触发执行。范围或版本冲突须刷新重新确认；预览的本地按钮不能当作成功写入。 |

## 案例签收

先从[四案预览与原件](../../../deliverables/investigation-validation-20261106/21-qwen9b-handoff-cases-20261106.zip)解压打开 `preview/index.html`。同一案分给三方并行核对。以下是业务 UUID，可直接在导出和后端查询中核对。

| 案例 | 操作与通过条件 |
| --- | --- |
| **Q01：一条告警追到同一案件的报告** | 告警 `11e52883-0ac7-5eb2-bd15-6a7f671d2dab` → 事件 `9173ab28-8dd7-4be7-97ac-897e728d23e8` → Case `8550d7b3-137a-5bb4-b2e1-5d0b401eca0b` → 基础 Run `3ece2370-1f19-4c60-9b59-5731d5ef43e7` → Result `3152e631-51d7-4936-9d43-07866149c897`。核对事件有 2 条成员告警、Run 为 `failed/partial`、系统结果关联 2 条告警且模型判断覆盖 0/2。点报告及图能回到本轮工件。 |
| **Q02：事件诊断超时且未建案** | 两条成员告警及原件仍能查；事件显示本次尝试状态，Case 关联为空。页面不得用计划里的候选 UUID 打开一个空案件。 |
| **Q03、Q04：有系统交接说明，无正式 Result** | Q03 核对分诊/事件拒收后仍可读主体；Q04 核对已发布的上游结果。在两个 Case 内分别打开 C3 超时的尝试、查看实际工件及当前系统判断。`delivery_state=none` 显示“未交付”，用量未知和结束时刻为空按原值显示。 |
| **补充正例：证据、管理、人工** | 按[逐字段样本](../../../deliverables/investigation-validation-20261106/page-field-samples.md)的 PD、H、DS 来源，分别验分类/时限、无索引与有效的 0 威胁、任务完成范围及模型来源判断。协作附件、实际响应、探索保存尚缺端到端页面正例，分别标为待接或待验。 |

**前端签收前有四项已复现的显示问题**：事件概览补本次诊断的入口；事件列表和详情将 `severity_effective=medium` 显示为“中”；运行页区分已记录的 `none` 与字段缺失；无效告警 ID 显示“告警未找到”并允许返回。四项分别可用 J04、F06、F15、J01 复验。[浏览器核对与字段证据](../../investigation/investigation-test-handoff-20261106.md#下一阶段的前后端交接验收)

**处理审计页用于开发核查。** 在运行记录表选案例，再选 A/I/C 的某一轮。流程节点通过 `run_steps.run_id/parent_step_id` 对应到本轮步骤；点击节点，按该步 `input_artifact_id/output_artifact_id` 查输入输出。“工件原件”集中列出已保存的原文，“测试准备、调用与事后核对”单列测试输入、调用记录和事后读回。后者帮助核查这次测试，与调查步骤的实际产出分别展示。[处理审计说明](../../../deliverables/investigation-validation-20261106/processing-functional-audit.md)
