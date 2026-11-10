> 此文件保存 2026-11-10 整理前的过程快照，仅供追溯。当前说明见仓库入口。

# 调查处理模块与业务后端数据交接 V1

告警页以告警为主体，事件页以事件及其当前成员为主体，调查页要同时显示 Case、某次执行（Run）、正式结果（Result）和当前采用的判断。四者通过各自的 ID 关联。一次模型调用失败时，后端仍可交付已经保存的告警原件、事件诊断、执行回执和系统待核说明。

适用范围为 PostgreSQL 16 的 `socai2` 命名空间，V1 共 29 表、462 列，建表基准为迁移 123–126。页面功能及产品验收见[三页功能清单](../../../deliverables/investigation-validation-20261106/frontend-feature-list.md)，逐列类型、可空性与约束见[字段字典](../../design/socai2-field-dictionary-20261103.md)。表设计调整须按[项目变更规则](../../../AGENTS.md#调查数据库-v1-与人工确认)登记并取得负责人明确人工确认。

**2026-11-07 正式库复验：** 同一多告警 Case 的字段、材料正文、步骤工件及父子关联已按实际 GET 对照 `aisoc` 的原始行；本轮不做前端跳转。Case 详情所需两项函数权限已经人工授权并修复；资产匹配仍缺 `public.assets` SELECT，4 个请求 500。127 个正常 GET 成功，4 个错误归属请求正确拒绝；本批缺少的模型 Case 结论、归并依据与独立证据索引仍保留。见[交接指南第 8.1 节](../../../FRONTEND_BACKEND_HANDOFF.md#81-2026-11-07-正式库数据库与-get-核对)和[逐功能状态](../../operations/evidence/database-handoff-review-20261107/review.json)。下文 11 月 6 日独立测试库回执保持原来源，不能代替本次正式库。

## 来源边界

| 环节 | 负责什么 | 交接边界 |
| --- | --- | --- |
| 采集与 Fusion | 提供告警来源标识、原始材料、事件引用、对象与归并依据，保存告警及事件成员 | `source_event_id` 是来源命名空间内的标识，可能缺失或尚无湖记录。后端沿已保存的关系取数；不得用相似标题、主机或时间自行认定成员。 |
| 调查处理模块 | A 分诊告警，I 诊断事件，C 执行 Case 调查，保存每次尝试、冻结输入、步骤、工件和交付记录 | 21 的 `processing-20261106-r3` 是按需作业，数据库为 `socai2_processing_handoff`；作业没有对外 HTTP 监听。三案来自受控合成输入，按实际主体执行，生产消费与页面服务需分别配置。[部署说明](../../../deliverables/investigation-validation-20261106/processing-deployment.md) |
| 业务后端 | 从已认证用户确定租户与读取权限，调用读取服务或使用授权的只读 PG 连接，组装列表、详情、关联入口与空态 | 同一响应尽量使用同一只读快照。`GET` 只读；详情缺数据时仍返回已取得的主体、可用性与限制。告警、事件、Case 的写操作须走相应服务命令及权限校验。 |
| 页面 | 按后端返回的字段、状态、计数与实体 ID 展示，按主体与版本打开详情 | 业务状态、模型判定、执行状态、交付完整性分别展示。模型响应中的建议、事实主张与外部实际行动分别标明来源。 |

## 字段—保存—读取

表名下文均属于 `socai2`。数据读取须从经验证的 `tenant_id` 和主体 UUID 开始。每次联表同时限定租户和所属关系；同一个 Case 或 Run 下有多条记录时，再按对应指针或类型选取。`public.users` 等外部依赖按同租户 ID 解析，未分配、已解析、来源负责人未解析分别返回。来源厂商 ID、用户名、主机名均不得替代主体 UUID。

### 告警页

| 页面用途 | 权威存储与关联 | 后端取值 |
| --- | --- | --- |
| 列表及概览 | `alerts` 的 `id, title, description, category, severity, handling_status, disposition, event_time, event_time_source, ingested_at, owner_id, assignment_state` | `event_time` 是发生时间，可空；`ingested_at` 是入库时间。保留五级严重度。优先级同时返回 `priority_value, priority_state, priority_source`，有依据时再返回 `priority_basis`。 |
| 来源和原件 | `alerts.latest_material_id → alert_materials.id`，同时匹配 `alert_id`。材料有 `revision, raw_json, raw_text, ocsf_json, detection, enrichment, material_state, sha256` | 列表读元数据，详情按版本加载正文。来源事件看 `alert_source_refs` 的 `material_id, source_namespace, source_event_id, source_path`；当前实体看同一材料版本 `alert_objects` 的 `object_key, object_type, normalized_value, object_role`。 |
| 已发布分诊、人工反馈、解释 | `alerts.latest_triage_id / latest_feedback_id → alert_assessments`，分别校验 `kind=triage / human_feedback`；`latest_explanation_id → artifacts` | 分诊的 `verdict, rationale, confidence, score_state, input_material_id, source_run_id` 来自同一行。有效性还要核输入新鲜度、当前材料和对应 Run。`score_state=available` 且有值时才转换成百分数。 |
| 查看分析尝试 | `runs.kind=alert_basic AND runs.alert_id=alerts.id`，再按 `run_id` 读步骤及工件 | 一个失败的 A Run 仍有执行记录。`latest_triage_id=NULL` 时显示尚无已发布分诊；从 `runs.stop_reason` 或步骤错误说明失败。 |

### 事件页

| 页面用途 | 权威存储与关联 | 后端取值 |
| --- | --- | --- |
| 事件概览和成员 | `incidents` 取 `id, title, description, handling_status, severity_override, priority_value, priority_state, owner_id, created_at`；`incident_alerts.(incident_id,alert_id) → alerts` | 成员数按告警计，归并依据来自关系行 `membership_source, correlation_basis, basis_version`。先聚合成员再连接材料、对象或步骤，避免成员数被一对多连接放大。 |
| 时间与有效严重度 | 对成员 `alerts.event_time` 求最早、最晚，并单列无时间数。自动严重度按 `info < low < medium < high < critical` 取已知成员的最高级 | `severity_effective` 优先取人工覆盖 `severity_override`，其次取成员最高值，两者的来源分别为 `manual_override / member_max`。两者均缺失时，有效严重度与来源均返回 `null`。 |
| 诊断摘要、未决问题 | `incidents.latest_diagnosis_id → incident_diagnoses.id`，同时匹配 `incident_id`；取 `state, summary, diagnosis, open_questions, source_run_id, generated_at` | 已发布诊断用指针读取。全部尝试从 `runs.kind=incident_diagnosis` 且 `incident_id` 相同的记录读取。I 的冻结输入含当时的成员及其分诊；当前成员或分诊可能已变化。 |
| 进入 Case | `case_incidents.(incident_id,case_id)` 保存显式关系，`case_alerts` 保存实际 Case 成员 | “该事件关联的 Case”和“某成员告警所在的 Case”有不同含义；分别说明关联依据。没有 Case 时事件详情仍可展示。 |

### Case 与调查执行页

| 页面用途 | 权威存储与关联 | 后端取值 |
| --- | --- | --- |
| 案件资料及成员 | `cases` 取 `title, handling_status, severity, owner_id, scope_revision, row_version, classification, due_at`；成员用 `case_alerts`、关联事件用 `case_incidents` | `classification` 可为 `true_positive / informational / false_positive / null`；`due_at` 是可空带时区的案件期限。任务期限和 Run 预算独立读取。 |
| 当前判断 | `cases.current_assessment_id → case_assessments`，按 `(tenant_id,case_id,id)` 匹配；`case_assessment_sources / case_assessment_members` 给来源和已覆盖成员 | 返回 `conclusion, origin, validity, formed_at, adopted_at, scope_revision`。`origin=system, validity=system_only` 表示系统待核说明。列表和详情的 `page_data.determination` 均沿该指针取值。 |
| 一次调查及其输入 | `runs.kind=baseline AND runs.case_id=cases.id`；`input_artifact_id` 是本轮输入；`run_members` 的 `alert_id, material_id, triage_id, feedback_id, read_state, analysis_state` 固定本轮版本 | `requested_at` 请求、`started_at` 实际启动、`ended_at` 实际结束。两端齐备才计算完成时长。`pending_update` 尚待启动，`unknown` 表示执行结果待确认；`running/unknown` 占用该 Case 的基础执行槽。 |
| 步骤、模型及工具输入输出 | `run_steps` 按同 `run_id` 的 `seq` 排列，`parent_step_id` 指向父步骤。`input_artifact_id / output_artifact_id` 指向本轮输入和输出，`reused_artifact_id` 可指向同案其他 Run 的原件 | 读取 `stage_code, kind, state, actual_args, returned_rows, error, usage`。`completed + returned_rows=0` 是执行后查空。`skipped` 与失败原因各自保留。工件 `step_id=NULL` 仍可属于 Run。发生错误时继续返回可用原件与失败回执。 |
| 正式结果、报告与图谱 | `results.source_run_id` 关联实际 Run，`result_members` 给 `conclusion_covered` 及依据。`report_artifact_id / graph_artifact_id` 指向同案同轮工件 | 分别展示 `runs.state`、`delivery_state`、结果的 `conclusion_state / conclusion_origin / validation_state` 和已采用判断。C6 回执中 `content_json.outcome.result_id` 可空。有报告及系统说明时，正式 Result 仍允许为零。 |
| 证据目录、判断依据和威胁数 | `cases.current_evidence_artifact_id → artifacts`，匹配同租户同 Case、`kind=case_evidence_index`、`schema_version=socai2.case-evidence.v1` | 读取 `entries[]` 的证据 ID、关联成员和对象、`source_refs`、`verdict_sources`、`verdict`、威胁身份和状态。计数及范围优先复用 `CasePageData.evidence`。 |
| 人工协作与处置 | `tasks.current_revision_id → task_revisions`。活动从 `activities.actor` 取操作者快照，从 `activity_targets` 取各目标的前后值。`response_links.receipt_artifact_id` 指向处置回执 | 区别人工任务、模型提出的后续行动、实际回执。存在 `recommendations` 时只显示建议。每条活动可能有多个目标，活动数按活动 ID 计。 |
| 评论、探索画布、问答 | `comments` 按互斥的 `alert_id / incident_id / case_id` 确定评论对象。`graph_explorations` 按 `case_id` 及基底工件取已保存的用户画布。`conversations.case_id` 关联案件，`messages.conversation_id` 关联会话，按 `sequence` 排序 | 评论、用户探索状态和正式结果图分别展示。问答表预留存储位置，当前命令可用性见下文。 |

证据计数使用当前版本中 `state=active` 且全部关联告警仍在案件范围的条目。威胁数仅取其中 `malicious / suspicious` 且有明确威胁身份的条目，按 `(namespace,key)` 去重。`not_recorded / unavailable / invalid_reference` 的计数为 `null`；有效空目录或全撤回为 `0`；`partial` 返回已知计数、未覆盖成员及限制。证据的来源行、JSON Pointer、角色和范围均可核对。来源标签、模型判断和人工陈述应保留各自身份。[证据合同](../../../services/api/app/socai2/case_evidence.schema.json) · [证据读取和验证](../../../services/api/app/socai2/case_data.py)

## 查询形状与分页

路径均相对于 `/api/v1/socai2`。告警、事件和 A/I 分析读取要求 `alerts:read`，其中 `records/cases` 还要求 `cases:read`；Case 与 H 读取要求 `cases:read`。A/I 执行与 Case 命令分别要求 `alerts:write`、`cases:write`。21 的三页核验通过处理环境里的读取服务执行，部署方另行提供 HTTP 站点地址、读身份和网络权限。[完整路径及参数](../../design/socai2-independent-api-v2.openapi.json)

| 读取内容 | 路径 | 分页和返回边界 |
| --- | --- | --- |
| 告警、事件列表与详情 | `/alerts`、`/incidents`、相应 `/{id}` | 列表默认 20、上限 50。`next_before_id` 原样作为 `before_id`，告警按 `(ingested_at,id)`、事件按 `(created_at,id)` 倒序；读 `items, total, overall_stats, observed_at`。 |
| 成员、对象、出处与记录 | `/{subject}/{id}/records/{section}`；告警正文 `/alerts/{id}/materials/{material_id}` | 依据详情返回的 `section_urls` 打开。记录默认 50、上限 200，按 `next_offset` 继续。正文单独读 `availability`；告警原件读出超过 131072 字节时保留元数据及不可展开原因。 |
| A/I 分析与追踪 | `/alerts/{id}/analysis` 或 `/incidents/{id}/analysis`。在分析路径后接 `/runs/{run_id}` 取一次执行，再在该执行路径后接 `/trace` 或 `/artifacts/{artifact_id}` | 分析列表默认 20、上限 50，按 `(requested_at,id)` 倒序，`next_before_run_id` 回传为 `before_run_id`。追踪区分步骤总数、工件总数和截断标志。 |
| Case 队列与资料 | `/cases`、`/cases/{id}`、`/cases/{id}/page-data` | 队列默认 20、上限 50，按 `(business_updated_at,id)` 倒序。`next_cursor` 原样用于同租户、同筛选条件的下一页；筛选后的 `total` 和全租户队列 `metrics` 分开。 |
| 案件历史、Run、Result | `/cases/{id}/history`、`/cases/{id}/runs/{run_id}`、`/cases/{id}/results/{result_id}` | 历史默认 20、上限 100，回传 `next_cursor`。来源为本案基础 Run 和明确保存的 `ai_saved` 结果。要展示相关 A/I 尝试，另按成员告警、关联事件读取，再按 Run UUID 去重。 |
| 资料与任务明细 | `/cases/{id}/runs/{run_id}/artifacts/{artifact_id}`、`/materials/{material_id}`（同一 Run 路径下）；`/cases/{id}/tasks` | Case Run 明细至多返回 200 个成员、1000 条步骤、200 个工件及 200 个结果 ID，各集合查看自己的总数与截断字段。任务/版本列表默认 20、上限 100，使用 offset。 |

字段缺失、`null`、空数组和有值零要分别传递。读到 `null` 的负责人、严重度或耗时，应显示相应缺值。HTTP 错误、正文超限、某一来源没有记录也分别返回状态。原件中 decimal 可能为数值字符串，对账前按字段类型规范化；时刻用带时区的值比较，可统一以北京时间展示。[主体读实现](../../../services/api/app/socai2/page_reader.py) · [A/I 记录](../../../services/api/app/socai2/stage_reader.py) · [Case 与 Run 读取](../../../services/api/app/socai2/case_reader.py)

## 只读联查示例

下列 SQL 可在 **psql** 的同一连接顺序执行。`tenant_id`、`case_id`、`run_id` 分别为授权租户、案件和选中调查轮次的 UUID。示例选择 m01，对应结果列在下一节。业务后端应从认证上下文设置租户，并在事务结束后释放事务级配置。

```sql
\set tenant_id '6aff0ef7-c670-5a84-a2ee-83d73e25b964'
\set case_id 'aa27a48f-10b7-53c8-bc80-d9ea022bcad3'
\set run_id '0e85ecb5-db82-4dc4-8561-da5fce18c744'
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT set_config('app.current_tenant_id', :'tenant_id', true);

-- 当前告警材料和已发布分诊；即使分诊为空也返回告警。
SELECT a.id, a.title, a.event_time, m.id AS material_id, m.material_state,
       t.id AS triage_id, t.verdict, t.source_run_id
FROM socai2.case_alerts ca
JOIN socai2.alerts a ON (a.tenant_id,a.id)=(ca.tenant_id,ca.alert_id)
LEFT JOIN socai2.alert_materials m
  ON (m.tenant_id,m.alert_id,m.id)=(a.tenant_id,a.id,a.latest_material_id)
LEFT JOIN socai2.alert_assessments t
  ON (t.tenant_id,t.alert_id,t.id)=(a.tenant_id,a.id,a.latest_triage_id) AND t.kind='triage'
WHERE ca.tenant_id=:'tenant_id'::uuid AND ca.case_id=:'case_id'::uuid ORDER BY a.id;

-- 每个显式关联事件返回一行，含成员数量和已发布诊断。
SELECT i.id, i.title, d.id AS diagnosis_id, d.summary,
       (SELECT count(*) FROM socai2.incident_alerts ia
        WHERE (ia.tenant_id,ia.incident_id)=(i.tenant_id,i.id)) AS member_count
FROM socai2.case_incidents ci
JOIN socai2.incidents i ON (i.tenant_id,i.id)=(ci.tenant_id,ci.incident_id)
LEFT JOIN socai2.incident_diagnoses d
  ON (d.tenant_id,d.incident_id,d.id)=(i.tenant_id,i.id,i.latest_diagnosis_id)
WHERE ci.tenant_id=:'tenant_id'::uuid AND ci.case_id=:'case_id'::uuid ORDER BY i.id;

-- 当前判断与每轮基础调查并列；正式结果按 Run 独立计数。
SELECT c.id AS case_id, a.origin, a.validity, a.conclusion,
       r.id AS run_id, r.state, r.delivery_state, r.started_at, r.ended_at,
       (SELECT count(*) FROM socai2.results x
        WHERE (x.tenant_id,x.case_id,x.source_run_id)=(c.tenant_id,c.id,r.id)
          AND x.kind='baseline') AS baseline_result_count
FROM socai2.cases c
LEFT JOIN socai2.case_assessments a
  ON (a.tenant_id,a.case_id,a.id)=(c.tenant_id,c.id,c.current_assessment_id)
LEFT JOIN socai2.runs r ON (r.tenant_id,r.case_id)=(c.tenant_id,c.id) AND r.kind='baseline'
WHERE c.tenant_id=:'tenant_id'::uuid AND c.id=:'case_id'::uuid ORDER BY r.requested_at,r.id;
-- 逐步回查该 Case 的一轮调查；父步骤、查询和模型分别保留。
SELECT s.seq, s.stage_code, s.kind, s.state, s.parent_step_id, s.error,
       s.input_artifact_id, s.output_artifact_id, s.reused_artifact_id,
       s.returned_rows, s.usage
FROM socai2.runs r
JOIN socai2.run_steps s ON (s.tenant_id,s.run_id)=(r.tenant_id,r.id)
WHERE r.tenant_id=:'tenant_id'::uuid AND r.case_id=:'case_id'::uuid
  AND r.id=:'run_id'::uuid AND r.kind='baseline'
ORDER BY s.seq;
ROLLBACK;
```

在 m01 的基础调查中，第 9 步为材料整理，第 10、11 步为 C3 父步骤和模型尝试，第 12 步为 C6 系统收尾。展开输入、输出时按工件 ID 限定同租户同 Run，并补读该步下 `artifacts.step_id=run_steps.id` 的其他工件。展开 `reused_artifact_id` 时单独按租户、案件、工件 ID 核对所属关系，保留其实际来源 Run。写在 Run 上且 `step_id=NULL` 的材料单列。进一步核对当前判断来源与证据目录可使用[Case 资料与证据目录 SQL](../../investigation/socai2-page-data-readback-20261106.sql)。

## 保存的样例与验证

21 处理交接库的合成批次 `ie-audit-20261106-a1` 共 4 条告警、3 个事件、3 个 Case、10 个 Run、62 条步骤和 130 份工件。2026-11-06 15:36（北京时间）再次对同一租户做只读快照，三个案例范围内的 29 张表逐表与留存原件一致。另有 53 项页面读取与原件对照。[三案逐阶段审计](../../../deliverables/investigation-validation-20261106/processing-functional-audit.md) · [核对记录](../../operations/evidence/ie-audit-20261106-a1/page-cross-check.json)

| 接手时可复查的场景 | 期望读数 |
| --- | --- |
| m01 · Web 证书替换；上节 SQL | 告警 `75827d24-8392-5797-84bf-31e9783ef223` 有材料 `52f5b089-8965-5a85-946b-d2a433203698`，分诊指针为空。事件 `b908e5ac-74b8-584c-9d53-35f70b1189fd` 有 1 个成员，诊断 `b277b121-8637-54fc-b73b-141f7cb703a7`。Case 的基础 Run `0e85ecb5-db82-4dc4-8561-da5fce18c744` 为 `unknown/none`；开始于 14:23:49，结束时刻为空，正式 Result 为 0，Case 当前判断为 `system/system_only`。C6 的系统收尾工件已经保存。 |
| s02 · 登录审计设置与安全日志 | Case `4f74d23e-d277-561a-bcab-d60ce11a60cd` 关联 1 个事件和 2 条告警，二者各自的已发布 A 分诊均为 `needs_review`，可从各自的 `source_run_id` 查原答。基础调查的系统说明可与事件诊断同时展示。 |
| 独立证据计数（隔离合同样例） | Case `80b07fe5-3493-4b4d-80e5-032e190b2ccd` 有 2 条证据、1 个威胁；`7dfdf1ed-1bfa-45f8-b8b5-a8b6c01b143c` 为 2/0；`a8f6bca9-fa1f-44ed-b14f-456dfc5a3d20` 为 null/null。此组专用于数据合同，无模型调用。[样例回执](../../operations/evidence/page-data-20261106/summary.json) |
| 已有事件、建案未发生（独立四案包 02） | 导出计划有候选 Case UUID；`database.json.cases=[]`。告警、事件及已有 A/I 尝试照常返回，Case、基础 Run、正式结果按实际记录展示。[四案字段与原件位置](../../../deliverables/investigation-validation-20261106/page-field-samples.md) |

## 后续对接顺序

1. **接入只读数据。** 确认连接到目标库、使用受限读取身份，按已授权租户跑两组不同样例。每页至少核对一条有值记录、一条与之关联的子表记录和一种空态。
2. **校验三页与运行明细。** 同时比对列表、详情、关联跳转和导出中的 ID；按游标读下一页。用 m01 验证执行失败仍有材料和系统说明，用 s02 验证同事件下的两条告警各有自己的分诊与来源。
3. **按命令接写操作。** Case `PATCH /page-data` 同时提交可空的 `classification`、`due_at`、`operation_key`、`expected_row_version`、`source`、`source_note`。发布证据目录时校验同案来源、目录修订关系、当前工件指针与成员范围；详情打开不得隐式启动调查。H 任务版本、成员关联、手动启动分别走相应服务命令。保留幂等与过期版本冲突。Q 问答、保存问答结果及显式采用三个预留接口当前返回 501。
4. **签收范围。** 可签收三页的数据保存、版本与只读取数。21 三案 C3 超时，成功的最终模型推断、受控处置执行、附件上传、协作表单及全局独立调查列表服务仍需各自验收。模型或工具的实现调整若不改变字段与取值语义，页面可以继续依此合同开发。
