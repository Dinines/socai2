# 调查处理模块与业务后端数据交接

告警页以告警为主体，事件页以事件及其当前成员为主体，调查页要同时显示 Case、某次执行（Run）、正式结果（Result）和当前采用的判断。四者通过各自的 ID 关联。一次模型调用失败时，后端仍可交付已经保存的告警原件、事件诊断、执行回执和系统待核说明。

适用范围为 PostgreSQL 16 的 `socai2` 命名空间，当前共 28 表、450 列，基准迁移 123–126 后增加 127（仅清理未用探索表）。[当前表职责](investigation-table-scope.md)及[当前机器字典](../design/socai2-data-contract-current.json)为现行目录；旧字段字典保留 V1 基线。页面功能及产品验收见[逐页功能清单](../../deliverables/investigation-validation-20261106/frontend-feature-list.md)，逐列类型、可空性与约束见[字段字典](../design/socai2-field-dictionary-20261103.md)。告警相关的前后端字段合同保持稳定；确需调整时按[项目变更规则](../../AGENTS.md#调查数据库-v1-与人工确认)列出影响并取得明确确认，必要读写接线和配置随功能处理。

**前次完整读取核验（清理前）：** 2026-11-10 在 21 的 `aisoc.socai2` 完成两案 365 次 GET、16,820 项字段／正文／关联核对。357 次正常返回，8 次错误父归属返回预期 404；读取前后快照一致。覆盖空当前判断、H 全部修订及同租户跨 Case 关系／活动。既有 29 表结构保持，Case/H GET、资产与用户关联、两项只读函数均可按现有身份读取。[实际证据](../operations/evidence/case-current-flow-20261110-01/readback-03/summary.json)

## 来源边界

| 环节 | 负责什么 | 交接边界 |
| --- | --- | --- |
| 采集与 Fusion | 提供告警来源标识、原始材料、事件引用、对象与归并依据，保存告警及事件成员 | `source_event_id` 是来源命名空间内的标识，可能缺失或尚无湖记录。后端沿已保存的关系取数；不得用相似标题、主机或时间自行认定成员。 |
| 调查处理模块 | A 分诊告警，I 诊断事件，C 执行 Case 调查，保存每次尝试、冻结输入、步骤、工件和交付记录 | 处理模块按需执行，当前版本以[交接指南](../../FRONTEND_BACKEND_HANDOFF.md#2-当前运行环境)为准，数据库为 `aisoc.socai2`；作业没有对外 HTTP 监听。A/I/Case 策略由当前 profile 显式选择。主 API 提供读取，自动消费者暂停。[部署说明](../../deploy/aisoc21/README.md) |
| 业务后端 | 从已认证用户确定租户与读取权限，通过 HTTP 调用调查服务，组装列表、详情、关联入口与空态；不要求直连 PG | 同一响应尽量使用同一只读快照。`GET` 只读；详情缺数据时仍返回已取得的主体、可用性与限制。告警、事件、Case 的写操作须走相应服务命令及权限校验。 |
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
| 当前判断 | `cases.current_assessment_id → case_assessments`，按 `(tenant_id,case_id,id)` 匹配；`case_assessment_sources / case_assessment_members` 给来源和已覆盖成员 | 返回 `conclusion, origin, validity, formed_at, adopted_at, scope_revision`。`origin=system, validity=system_only` 表示系统待核说明。列表和详情的 `page_data.determination` 均沿该指针取值。指针为空时展示尚无采用判断，不能用最近 Result 填充；本批两案即为该空态。 |
| 一次调查及其输入 | `runs.kind=baseline AND runs.case_id=cases.id`；`input_artifact_id` 是本轮输入；`run_members` 的 `alert_id, material_id, triage_id, feedback_id, read_state, analysis_state` 固定本轮版本 | `requested_at` 请求、`started_at` 实际启动、`ended_at` 实际结束。两端齐备才计算完成时长。`pending_update` 尚待启动，`unknown` 表示执行结果待确认；`running/unknown` 占用该 Case 的基础执行槽。 |
| 步骤、模型及工具输入输出 | `run_steps` 按同 `run_id` 的 `seq` 排列，`parent_step_id` 指向父步骤。`input_artifact_id / output_artifact_id` 指向本轮输入和输出，`reused_artifact_id` 可指向同案其他 Run 的原件 | 读取 `stage_code, kind, state, actual_args, returned_rows, error, usage`。`completed + returned_rows=0` 是执行后查空。`skipped` 与失败原因各自保留。工件 `step_id=NULL` 仍可属于 Run。发生错误时继续返回可用原件与失败回执。 |
| 正式结果、报告与图谱 | `results.source_run_id` 关联实际 Run，`result_members` 给 `conclusion_covered` 及依据。`report_artifact_id / graph_artifact_id` 指向同案同轮工件 | 分别展示 `runs.state`、`delivery_state`、结果的 `conclusion_state / conclusion_origin / validation_state` 和已采用判断。C6 回执中 `content_json.outcome.result_id` 可空。有报告及系统说明时，正式 Result 仍允许为零。 |
| 证据目录、判断依据和威胁数 | `cases.current_evidence_artifact_id → artifacts`，匹配同租户同 Case、`kind=case_evidence_index`、`schema_version=socai2.case-evidence.v1` | 读取 `entries[]` 的证据 ID、关联成员和对象、`source_refs`、`verdict_sources`、`verdict`、威胁身份和状态。计数及范围优先复用 `CasePageData.evidence`。 |
| 人工协作与处置 | `tasks.current_revision_id → task_revisions`。活动从 `activities.actor` 取操作者快照，从 `activity_targets` 取各目标的前后值。`response_links.receipt_artifact_id` 指向处置回执 | 区别人工任务、模型提出的后续行动、实际回执。存在 `recommendations` 时只显示建议。每条活动可能有多个目标，活动数按活动 ID 计。 |
| 评论、探索画布、问答 | `comments` 按互斥的 `alert_id / incident_id / case_id` 确定评论对象。未使用的 `graph_explorations` 空表已清理，正式探索保存服务未实现；不能按旧表设计读取画布。`conversations.case_id` 关联案件，`messages.conversation_id` 关联会话，按 `sequence` 排序 | 评论、用户探索状态和正式结果图分别展示。问答表预留存储位置，当前命令可用性见下文。 |

证据计数使用当前版本中 `state=active` 且全部关联告警仍在案件范围的条目。威胁数仅取其中 `malicious / suspicious` 且有明确威胁身份的条目，按 `(namespace,key)` 去重。`not_recorded / unavailable / invalid_reference` 的计数为 `null`；有效空目录或全撤回为 `0`；`partial` 返回已知计数、未覆盖成员及限制。证据的来源行、JSON Pointer、角色和范围均可核对。来源标签、模型判断和人工陈述应保留各自身份。[证据合同](../../services/api/app/socai2/case_evidence.schema.json) · [证据读取和验证](../../services/api/app/socai2/case_data.py)

Case/H 写入沿用原合同：建案返回 pending_run_id，任务修订追加 task_revisions 并更新 current_revision_id，后轮 C1 固定所选版本及 human_statement 来源。人工保存不自动启动 Run；操作顺序及本轮证据见 [Case/H 交接](../../openspec/changes/archive/2026-11-11-enable-case-human-http-flow/handoff.md)。本 change 不增加表列、枚举或告警交接字段。

Case 模型请求工件中的 `payload.source_map` 分别给查询范围、历史返回主体、允许的本案成员及其依据（`query_alert_ids / record_alert_ids / alert_ids / membership_basis`）。它们属于内部工件内容，数据库仍使用原 `artifacts.content_json`；告警及 Case HTTP 字段没有调整。按 `ref.id / source_path / role` 回查原件，不能把发起查询的成员当返回行主体。模型原答、`correction_feedback` 和 `validation_review` 分别留在响应工件；一次纠正前后的模型 Step 都应可查。 C3/C6 内部 Finding 的 observed 支持仅使用有成员依据的直接观察；inferred 需支持，unresolved 需限制。`socai2.case-citation-correction.v2` 额外给出角色和逐成员直接观察缺口，历史合法时间上下文仍兼容。此约束不新增列或 API 字段，也不代表正文质量通过。

## 查询形状与分页

路径均相对于 `/api/v1/socai2`。告警、事件和 A/I 分析读取要求 `alerts:read`，其中 `records/cases` 还要求 `cases:read`；Case 与 H 读取要求 `cases:read`。A/I 执行与 Case 命令分别要求 `alerts:write`、`cases:write`。21 主 API 在回环端口 18000，普通登录／有效 API key 绑定认证租户；页面及分析读取已启用，21 r2 的 Case/H HTTP 写入口已开放并经正常登录写读验证；产品页面按已保存回执与版本刷新。[完整路径及参数](../design/socai2-independent-api-v2.openapi.json)

| 读取内容 | 路径 | 分页和返回边界 |
| --- | --- | --- |
| 告警、事件列表与详情 | `/alerts`、`/incidents`、相应 `/{id}` | 列表默认20、上限50；支持标题/ID、等级、状态、负责人/分配状态、时间筛选及明确枚举排序。读items、filtered_total和next_cursor；total/overall_stats/observed_at保持整体口径。旧无新增条件调用仍用next_before_id/before_id，不能混用新条件或cursor。告警默认(ingested_at,id)、事件默认(created_at,id)倒序。 |
| 成员、对象、出处与记录 | `/{subject}/{id}/records/{section}`；告警正文 `/alerts/{id}/materials/{material_id}` | 依据详情返回的 `section_urls` 打开。记录默认 50、上限 200，按 `next_offset` 继续。正文单独读 `availability`；正文上限读取策略 `model.max_artifact_bytes`，当前为 1,048,576 字节；超过时保留元数据及不可展开原因。 |
| A/I 分析与追踪 | `/alerts/{id}/analysis` 或 `/incidents/{id}/analysis`。在分析路径后接 `/runs/{run_id}` 取一次执行，再在该执行路径后接 `/trace` 或 `/artifacts/{artifact_id}` | 分析列表默认 20、上限 50，按 `(requested_at,id)` 倒序，`next_before_run_id` 回传为 `before_run_id`。追踪区分步骤总数、工件总数和截断标志。 |
| 来源工件与活动 | `/alerts/{id}/artifacts/{artifact_id}`、`/incidents/{id}/artifacts/{artifact_id}`、`/cases/{id}/artifacts/{artifact_id}`；`/cases/{id}/activities` | 来源工件按真实归属读取；Case 活动包含本案、成员及显式事件目标，按活动去重并返回前后值。 |
| Case 队列与资料 | `/cases`、`/cases/{id}`、`/cases/{id}/page-data` | 队列默认20、上限50，默认按(business_updated_at,id)倒序，可选created_at/severity及asc/desc；日期按business_updated_at。`next_cursor` 原样用于同租户、同筛选条件的下一页；筛选后的 `total` 和全租户队列 `metrics` 分开。 |
| 案件历史、Run、Result | `/cases/{id}/history`、`/cases/{id}/runs/{run_id}`、`/cases/{id}/results/{result_id}` | 历史默认 20、上限 100，回传 `next_cursor`。来源为本案基础 Run 和明确保存的 `ai_saved` 结果。要展示相关 A/I 尝试，另按成员告警、关联事件读取，再按 Run UUID 去重。 |
| 资料与任务明细 | `/cases/{id}/runs/{run_id}/artifacts/{artifact_id}`、`/materials/{material_id}`（同一 Run 路径下）；`/cases/{id}/tasks` | Case Run 明细至多返回 200 个成员、1000 条步骤、200 个工件及 200 个结果 ID，各集合查看自己的总数与截断字段。任务/版本列表默认 20、上限 100，使用 offset。 |

字段缺失、`null`、空数组和有值零要分别传递。读到 `null` 的负责人、严重度或耗时，应显示相应缺值。HTTP 错误、正文超限、某一来源没有记录也分别返回状态。原件中 decimal 可能为数值字符串，对账前按字段类型规范化；时刻用带时区的值比较，可统一以北京时间展示。[主体读实现](../../services/api/app/socai2/page_reader.py) · [A/I 记录](../../services/api/app/socai2/stage_reader.py) · [Case 与 Run 读取](../../services/api/app/socai2/case_reader.py)

## HTTP投影与字段审计补充

逐项用途、输入、输出见[43操作审计](../../deliverables/investigation-validation-20261106/http-handoff-audit/interfaces.md)，[固定输出字段](../../deliverables/investigation-validation-20261106/http-handoff-audit/response-fields.md)和[28组动态结构](../../deliverables/investigation-validation-20261106/http-handoff-audit/dynamic-fields.md)补充原OpenAPI中仅写dict/任意对象的部分。此处的表来源用于说明，不要求业务后端直连数据库。

Case队列metrics不受列表筛选影响，但awaiting_assignment/high_severity/awaiting_human仅计new或in_progress；待分配还需assignment_state=unassigned且owner_id为空，高等级只计high。Case活动GET保留operation_id，A/I records/activities剔除该字段。

Case详情的current_assessment.sources通过without_internal剔除tenant_id等字段，而page_data.assessment.sources当前直接返回来源行、包含tenant_id；不要假定两种投影完全相同。Case工件完整性失败为409，A/I工件同类失败是200加availability=content_integrity_mismatch。冻结材料GET直接返回原行，保留material_state/retention，没有统一availability包装。

Case Run内部集合截断后当前没有继续分页的接口；读取方必须展示截断。当前判断覆盖比较遇到成员/覆盖集合不完整时返回null，不能擅自视为全部覆盖或没有未覆盖成员。questions[].state仅记录当轮回答状况，按D07随结论展示，不建立独立问题管理。

## 只读联查示例

下列 SQL 仅用于调查服务内部维护和取数解释，**不是业务后端对接要求**。对接请使用[HTTP交接包](../../deliverables/investigation-validation-20261106/http-handoff/README.md)。内部维护时可在 **psql** 的同一连接顺序执行。`tenant_id`、`case_id`、`run_id` 分别为授权租户、案件和选中调查轮次的 UUID。示例选择当前核验中的模型来源 Case，对应结果列在下一节。内部数据库读取应设置正确租户，并在事务结束后释放事务级配置；业务后端通过 HTTP 认证上下文确定租户。

```sql
\set tenant_id '00000000-0000-0000-0000-000000000001'
\set case_id '2b37f5b3-862b-52cc-84bd-86db50dd3ad4'
\set run_id '8d53cdb1-1cba-4df3-8ac2-f2724c062342'
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

步骤顺序以该 Run 实际 `seq/stage_code` 为准。展开输入、输出时按工件 ID 限定同租户同 Run，并补读该步下 `artifacts.step_id=run_steps.id` 的其他工件。展开 `reused_artifact_id` 时单独按租户、案件、工件 ID 核对所属关系，保留其实际来源 Run。写在 Run 上且 `step_id=NULL` 的材料单列。进一步核对当前判断来源与证据目录可使用[Case 资料与证据目录 SQL](socai2-page-data-readback-20261106.sql)。

## 保存的样例与验证

| 正式库 Case | 本次取数核验 |
| --- | --- |
| `2b37f5b3-862b-52cc-84bd-86db50dd3ad4` | 3 告警、1 事件、5 Run；基础 Run `8d53cdb1-1cba-4df3-8ac2-f2724c062342` 为 completed/partial。160 GET，7,128 检查；模型来源结果的保存与读取通过，正文质量未通过 |
| `5942734d-1bea-5c0b-97fe-0d9ccde01858` | 3 告警、1 事件、5 Run；基础 Run `4c870247-444c-4083-b511-db9791c32a17` 为 failed/partial。139 GET，5,970 检查；系统收尾、错误和已有上游结果可读 |

两案均核对读取前后快照一致。材料原件、相关告警、活动、Run／Result、证据与判断按实际数据库逐字段比较。[逐请求及数据库原件](../operations/evidence/current-release-20261110-01/readback-03/summary.json)

事件交付读取 `diagnosis.delivery_assessment` 的原因、成员覆盖和 `review_items`。该 JSON 块可缺失，缺失不推断为完整或无需待核；执行状态、交付、待复核、采用和质量分别显示。[状态及空态](../../FRONTEND_BACKEND_HANDOFF.md#5-状态交付和空态)

补充有值／空值样例见[字段样本](../../deliverables/investigation-validation-20261106/page-field-samples.md)，未开放业务和原页面显示差异见[问题清单](current-issues.md)。固定导出只代表采样时点，不修改其失败或 unknown 结果。

列表查询补充：告警时间为真实event_time；事件要求同一成员告警event_time落在区间内，last_activity_at为成员最晚真实时间；Case时间为business_updated_at。time_from/time_to必须带时区，前闭后开，可单边。缺失时间不替换为入库时间。记录排序字段缺值时始终排最后；非法sort_by返回422。改变条件或排序清空游标，游标原样URL编码续页。详见[HTTP交接](../../deliverables/investigation-validation-20261106/http-handoff/README.md#列表查询怎么用)。
