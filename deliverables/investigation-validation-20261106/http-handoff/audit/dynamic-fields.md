> 既有JSON接口字段审计原文；原文47/53操作仅指原审计时点。本批当前62操作，CSV接口/104列见[E54–E56](../endpoints.md#e54)；新增统计/12字段见[E57](../endpoints.md#e57)。

# 动态输出字段与版本边界

这些字段在原OpenAPI里是dict/array[Any]或空Schema。下文按实际读取装配展开，语义复用已存在的当前字段字典；不是新增数据表，也不要求业务后端直连数据库。字段类型写enum/contract时，完整定义沿[现有JSON合同](../../../docs/design/socai2-json-contracts-20261103.schema.json)或[当前机器字典](../../../docs/design/socai2-data-contract-current.json)。原件开放内容不伪造成固定业务DTO。

<a id="case-members"></a>

## case-members

落点：E03 CaseDetail.members[]。

当前成员最多200；这是当前范围，与Run冻结成员分开。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| alert_id | ref.alerts | 非null | 当前正式成员 | `case_alerts.alert_id` |
| added_at | timestamptz | 非null | 加入时间 | `case_alerts.added_at` |
| added_by | uuid | 可为null | 明确操作人 | `case_alerts.added_by` |
| membership_source | enum.membership_source：fusion,manual,incident_link,move,legacy | 非null | 加入来源 | `case_alerts.membership_source` |
| title | text | 非null | 接收到的标题；未知来源用显式缺失显示，不编造内容 | alerts.title |
| severity | enum.severity | 可为null | 当前来源严重程度 | alerts.severity |
| handling_status | enum.alert_status | 非null | 业务处理状态 | alerts.handling_status |
| event_time | timestamptz | 可为null | 真实发生时间 | alerts.event_time |
| latest_material_id | ref.alert_materials | 可为null | 同告警最新有效材料 | alerts.latest_material_id |


<a id="case-linked-incidents"></a>

## case-linked-incidents

落点：E03 CaseDetail.linked_incidents[]。

显式关系最多200；没有自动并入“共享成员导致的间接关联”。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| incident_id | ref.incidents | 非null | 显式关联事件 | `case_incidents.incident_id` |
| linked_at | timestamptz | 非null | 关联时间 | `case_incidents.linked_at` |
| linked_by | uuid | 可为null | 操作者 | `case_incidents.linked_by` |
| source_operation_id | uuid | 非null | 操作ID | `case_incidents.source_operation_id` |
| title | text | 非null | 事件自身标题 | incidents.title |
| source_namespace | text | 非null | Fusion实例/来源命名空间 | incidents.source_namespace |


<a id="assessment-value"></a>

## assessment-value

落点：E03 current_assessment.value。



| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| case_id | ref.cases | 非null | 案件 | `case_assessments.case_id` |
| revision | bigint | 非null | 案件判断版本 | `case_assessments.revision` |
| conclusion | text | 非null | 明确采用的判断 | `case_assessments.conclusion` |
| origin | enum.origin：model,human,system,legacy | 非null | model/human/legacy，system交接不得采用为有效结论 | `case_assessments.origin` |
| validity | enum.validation：not_checked,accepted,rejected,system_only,legacy_unverified | 非null | 采用时有效性；不代表绝对事实证明 | `case_assessments.validity` |
| scope_revision | bigint | 非null | 采用时Case范围版本 | `case_assessments.scope_revision` |
| formed_at | timestamptz | 非null | 判断形成时间 | `case_assessments.formed_at` |
| adopted_at | timestamptz | 非null | 采用时间 | `case_assessments.adopted_at` |
| adopted_by | uuid | 可为null | 人工采用时用户；基础结果自动采用NULL，actor明确service | `case_assessments.adopted_by` |
| actor | json.actor | 非null | 真实采用主体；baseline自动采用记录service | `case_assessments.actor` |
| reason | text | 可为null | 采用/修改理由 | `case_assessments.reason` |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `case_assessments.id` |


<a id="assessment-members"></a>

## assessment-members

落点：E03 current_assessment.members[]。



| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| alert_id | ref.alerts | 非null | 判断明确覆盖的告警 | `case_assessment_members.alert_id` |
| coverage_note | text | 可为null | 范围限制；覆盖不是全告警都恶意 | `case_assessment_members.coverage_note` |


<a id="assessment-sources"></a>

## assessment-sources

落点：E03 current_assessment.sources[]；E02/E03内嵌page_data.assessment.sources[]及E05 assessment.sources[]。

E03通过without_internal剔除tenant_id/operation_key/request_hash；E02/E03内嵌page_data及E05均由read_page_data直接dict(row)，额外含tenant_id（认证租户UUID）。不要假定两个sources投影完全相同。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| case_id | ref.cases | 非null | 用于父案复合FK | `case_assessment_sources.case_id` |
| assessment_id | ref.case_assessments | 非null | 采用判断 | `case_assessment_sources.assessment_id` |
| result_id | ref.results | 可为null | 具体正式结果版本 | `case_assessment_sources.result_id` |
| task_revision_id | ref.task_revisions | 可为null | 具体人工事实版本 | `case_assessment_sources.task_revision_id` |
| artifact_id | ref.artifacts | 可为null | 同案其他具体材料 | `case_assessment_sources.artifact_id` |
| source_note | text | 可为null | 此来源被采用的部分 | `case_assessment_sources.source_note` |
| tenant_id | uuid | 非null，仅page_data路径返回 | 已采用判断来源行的认证租户；E03 current_assessment.sources不含此字段 | case_assessment_sources.tenant_id |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `case_assessment_sources.id` |


<a id="current-assessment"></a>

## current-assessment

落点：E03 current_assessment。

整个对象在没有采用指针时为null；source/member目录各最多200。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| value | object | 非null | 采用判断行，见assessment-value | case_reader.case |
| members | array | 非null | 覆盖成员，见assessment-members | case_assessment_members |
| sources | array | 非null | 采用来源，见assessment-sources | case_assessment_sources |
| members_truncated / sources_truncated | boolean | 非null | 分别标记截断，不保证遍历完整 | 各取201判断是否超过200 |
| input_freshness | object | 非null | 本版固定包含state/reasons，下一两行分别说明；按冻结输入对比当前材料、分诊/诊断、任务修订及成对查询回执 | case_query_snapshot.freshness_statement + baseline_input_freshness |
| input_freshness.state | current / stale / unverified | 非null | 输入未变/已变/无法核实，冻结上下文缺失或版本不支持时unverified | baseline_input_freshness及case_query_snapshot |
| input_freshness.reasons | string[] | 非null | scope_changed、member_versions_changed、incident_context_changed、human_feedback_changed、frozen_context_unavailable等原因；包装层还可能补paired_alert_queries_changed或case_query_version_unsupported | SQL函数及查询回执比较 |
| scope_revision_changed | boolean | 非null | 采用时scope_revision是否不同于当前Case版本 | case_assessments vs cases |
| covers_current_members | boolean | 可为null | 当前全部成员是否落入判断覆盖；任一集合不完整时null | 集合包含关系 |
| uncovered_current_alert_ids | UUID[] | 可为null | 当前成员未覆盖的部分；不能完整比较时null | current - known |
| no_longer_current_alert_ids | UUID[] | 可为null | 判断旧覆盖中已不在当前Case的部分；不能完整比较时null | known - current |


<a id="run-members"></a>

## run-members

落点：E12/E13 RunDetail.members[]。

固定material_id/triage_id/feedback_id以及读取/分析状态，不由当前告警指针替换。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| run_id | ref.runs | 非null | Case执行；非Case成员快照存输入工件 | `run_members.run_id` |
| case_id | ref.cases | 非null | 同案FK | `run_members.case_id` |
| alert_id | ref.alerts | 非null | 本轮约定成员 | `run_members.alert_id` |
| material_id | ref.alert_materials | 可为null | 领取选择的材料版；确实缺失NULL并标read状态 | `run_members.material_id` |
| triage_id | ref.alert_assessments | 可为null | 同告警同次分诊 | `run_members.triage_id` |
| feedback_id | ref.alert_assessments | 可为null | 同告警当时人工反馈 | `run_members.feedback_id` |
| read_state | enum.read_state：not_read,read,missing,denied,failed | 非null | 实际读到材料 | `run_members.read_state` |
| analysis_state | enum.analysis_state：not_analyzed,analyzed,unresolved,excluded | 非null | 实际分析状态 | `run_members.analysis_state` |
| omission_reason | text | 可为null | 缺失/失败/排除的具体原因 | `run_members.omission_reason` |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `run_members.id` |


<a id="run-steps"></a>

## run-steps

落点：E12/E13 steps[]；E32 steps[]。

按seq排列；parent_step_id组织层次，retry_of_step_id说明重试来源。Case最多1000；A/I同MAX_STEPS=1000。usage/actual_args/error是已保存的对应合同；GET不执行步骤。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| run_id | ref.runs | 非null | 实际执行 | `run_steps.run_id` |
| seq | bigint | 非null | 同Run显示顺序 | `run_steps.seq` |
| parent_step_id | ref.run_steps | 可为null | 同Run父阶段；不是跨Run复用 | `run_steps.parent_step_id` |
| retry_of_step_id | ref.run_steps | 可为null | 同Run失败调用的重试 | `run_steps.retry_of_step_id` |
| kind | enum.step_kind：stage,model,tool,graph,render | 非null | stage/model/tool/graph/render | `run_steps.kind` |
| stage_code | text | 非null | A1/I1/C1..C6/Q1等版本化阶段码 | `run_steps.stage_code` |
| question_id | text | 可为null | 输入计划中稳定问题ID | `run_steps.question_id` |
| state | enum.step_state：planned,running,completed,failed,timeout,cancelled,skipped,unknown | 非null | 实际状态 | `run_steps.state` |
| name | text | 非null | 阶段、模型或工具实际名称 | `run_steps.name` |
| provider | text | 可为null | 模型/工具提供者 | `run_steps.provider` |
| implementation_version | text | 可为null | 工具合同/模型版本 | `run_steps.implementation_version` |
| started_at | timestamptz | 可为null | 真实开始 | `run_steps.started_at` |
| ended_at | timestamptz | 可为null | 真实完成 | `run_steps.ended_at` |
| input_artifact_id | ref.artifacts | 可为null | 实际输入/参数原件 | `run_steps.input_artifact_id` |
| output_artifact_id | ref.artifacts | 可为null | 实际输出原件 | `run_steps.output_artifact_id` |
| reused_artifact_id | ref.artifacts | 可为null | 明确复用旧材料，不记为新外部调用 | `run_steps.reused_artifact_id` |
| actual_args | json.tool_args | 可为null | 类型化查询范围/时间/上限及具体参数 | `run_steps.actual_args` |
| returned_rows | bigint | 可为null | 成功查询实际返回行数；未知/失败不填0 | `run_steps.returned_rows` |
| usage | json.usage | 可为null | 模型真实tokens/费用与已知状态；非调用父阶段NULL | `run_steps.usage` |
| error | json.error | 可为null | 实际错误 | `run_steps.error` |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `run_steps.id` |


<a id="run-row"></a>

## run-row

落点：E32 TraceView.run。

A/I trace的完整公开Run行含alert_id/incident_id/limits等；精简StageRunView/Case RunView没有这些全部字段，不能互换形状。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| kind | enum.run_kind：alert_basic,incident_diagnosis,baseline,ai_question | 非null | 四机器流程明确区分 | `runs.kind` |
| alert_id | ref.alerts | 可为null | alert_basic归属 | `runs.alert_id` |
| incident_id | ref.incidents | 可为null | incident_diagnosis归属 | `runs.incident_id` |
| case_id | ref.cases | 可为null | baseline/ai_question归属 | `runs.case_id` |
| title | text | 非null | 本次执行名称，pending随范围更新 | `runs.title` |
| purpose | text | 非null | 本轮目标/提问 | `runs.purpose` |
| trigger | enum.run_trigger：ingested,refresh,case_created,members_changed,manual,question,retry | 非null | 触发原因 | `runs.trigger` |
| scope_revision | bigint | 可为null | Case成员版本；非Case NULL | `runs.scope_revision` |
| scope_updated_at | timestamptz | 可为null | pending最近合并范围时间 | `runs.scope_updated_at` |
| scope_kind | enum.scope_kind：whole_case,selected_alerts,explicit_objects | 可为null | baseline whole_case，AI可选范围；其他流程NULL | `runs.scope_kind` |
| window_start | timestamptz | 可为null | 固定绝对查询起点；不适用NULL | `runs.window_start` |
| window_end | timestamptz | 可为null | 固定绝对查询终点；成对出现 | `runs.window_end` |
| state | enum.run_state：pending_update,running,unknown,completed,failed,cancelled | 非null | 记录/执行状态 | `runs.state` |
| retry_of_run_id | ref.runs | 可为null | 显式重试指向旧已结束Run，不重写旧Run | `runs.retry_of_run_id` |
| comparison_result_id | ref.results | 可为null | 领取时固定的同案比较基线，可跨成员范围 | `runs.comparison_result_id` |
| input_artifact_id | ref.artifacts | 可为null | 领取前NULL；提交running前冻结本地输入 | `runs.input_artifact_id` |
| executor_version | text | 可为null | 实际执行版本，pending NULL | `runs.executor_version` |
| requested_at | timestamptz | 非null | 记录创建/首次请求 | `runs.requested_at` |
| requested_by | uuid | 可为null | 真实请求人 | `runs.requested_by` |
| started_at | timestamptz | 可为null | running领取事务时间 | `runs.started_at` |
| ended_at | timestamptz | 可为null | 终态时间；unknown未确认结束NULL | `runs.ended_at` |
| stop_reason | text | 可为null | 稳定原因码；不强用人类结论代替 | `runs.stop_reason` |
| stop_detail | text | 可为null | 可读原因 | `runs.stop_detail` |
| delivery_state | enum.delivery：none,partial,complete,unknown | 非null | 实际产物交付 | `runs.delivery_state` |
| limits | json.limits | 可为null | 启动时预算和查询限额快照 | `runs.limits` |
| row_version | bigint | 非null | 执行状态条件更新版本 | `runs.row_version` |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `runs.id` |


<a id="result-members"></a>

## result-members

落点：E14 ResultDetail.members[]。

最多200；assessment_state与conclusion_covered不同，入选成员不等于被结论覆盖。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| case_id | ref.cases | 非null | 父案校验 | `result_members.case_id` |
| result_id | ref.results | 非null | 正式结果 | `result_members.result_id` |
| run_id | ref.runs | 非null | 与result.source_run一致 | `result_members.run_id` |
| alert_id | ref.alerts | 非null | 来自本轮run_members | `result_members.alert_id` |
| assessment_state | enum.analysis_state：not_analyzed,analyzed,unresolved,excluded | 非null | 实际逐成员分析状态 | `result_members.assessment_state` |
| conclusion_covered | boolean | 非null | 结论明确适用，不代表恶意 | `result_members.conclusion_covered` |
| assessment | text | 可为null | 本成员发现或未决说明 | `result_members.assessment` |
| limitations | text | 可为null | 限制 | `result_members.limitations` |
| evidence_refs | json.evidence_refs | 非null | 明确材料及行/字段定位 | `result_members.evidence_refs` |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `result_members.id` |


<a id="artifact-metadata"></a>

## artifact-metadata

落点：E15/E16 artifact；E33/E34/E35 metadata；E12/E32 artifacts[]。

工件元数据包含种类、schema_version、大小/hash、保留状态及原所属。Case响应字段名artifact，A/I字段名metadata。E30 source_artifacts额外有content_url且run_id为空。正文不在元数据目录内。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| alert_id | ref.alerts | 可为null | 非Case告警材料归属 | `artifacts.alert_id` |
| incident_id | ref.incidents | 可为null | 非Case事件材料归属 | `artifacts.incident_id` |
| case_id | ref.cases | 可为null | Case材料归属 | `artifacts.case_id` |
| run_id | ref.runs | 可为null | 存在时必须与其父对象一致 | `artifacts.run_id` |
| step_id | ref.run_steps | 可为null | 实际产生步骤，须属于run_id | `artifacts.step_id` |
| kind | enum.artifact_kind：input_snapshot,model_request,model_response,tool_request,tool_response,domain_analysis,deep_analysis,attack_chain,attack_path,alert_graph,report_json,report_markdown,attachment,source_snapshot,handoff,query_plan,alert_explanation,case_evidence_index | 非null | 材料类别 | `artifacts.kind` |
| schema_version | text | 非null | 结构合同版本 | `artifacts.schema_version` |
| mime_type | text | 非null | 实际内容类型 | `artifacts.mime_type` |
| file_name | text | 可为null | 附件显示名，不作路径 | `artifacts.file_name` |
| sha256 | char(64) | 可为null | 已留存规范字节哈希 | `artifacts.sha256` |
| size_bytes | bigint | 可为null | 已留存字节数 | `artifacts.size_bytes` |
| captured_at | timestamptz | 非null | 记录取得时间 | `artifacts.captured_at` |
| event_time | timestamptz | 可为null | 材料中的发生时间，未知NULL | `artifacts.event_time` |
| material_state | enum.material_state：complete,truncated,summary_only,unavailable | 非null | 完整/截断/摘要/不可用 | `artifacts.material_state` |
| source_refs | json.evidence_refs | 非null | 来源和原材料引用；可为空数组但明确是无来源记录 | `artifacts.source_refs` |
| retention | json.retention | 非null | 原件大小/原hash/保存大小/截断范围 | `artifacts.retention` |
| created_by | uuid | 可为null | 人工上传人；自动来源由Run/Step明确 | `artifacts.created_by` |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `artifacts.id` |


<a id="alert-material-meta"></a>

## alert-material-meta

落点：E28 material；E31 metadata。

上述两个附加字段分别属于不同响应，不要求同时存在。事件SubjectView.material=null。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| alert_id | ref.alerts | 非null | 所属告警 | `alert_materials.alert_id` |
| revision | bigint | 非null | 同告警材料版本，从1开始 | `alert_materials.revision` |
| received_at | timestamptz | 非null | 接收时间 | `alert_materials.received_at` |
| source_version | text | 可为null | 输入已有源版本，未知NULL | `alert_materials.source_version` |
| detection | json.detection | 非null | 规则、ATT&CK与来源检测评分合同 | `alert_materials.detection` |
| source_scope | json.source_scope | 非null | 来源引用范围、数量、截断和完整性 | `alert_materials.source_scope` |
| material_state | enum.material_state：complete,truncated,summary_only,unavailable | 非null | 原件留存状态 | `alert_materials.material_state` |
| sha256 | char(64) | 可为null | 已留存字节哈希；原大小/原hash另在retention | `alert_materials.sha256` |
| retention | json.retention | 非null | 字节数、保存形式、截断及原因 | `alert_materials.retention` |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `alert_materials.id` |
| content_url | string | E28存在 | 版本正文读取URL，E31 metadata不包含此派生字段 | page_reader.view |
| content_bytes | integer | E31存在 | raw_json/raw_text/ocsf_json/enrichment的读取大小总和，用于正文限制；E28 material不含 | page_reader.material_content |


<a id="frozen-material"></a>

## frozen-material

落点：E18 响应根对象。

直接返回完整原始行，含tenant_id；没有metadata/content_json包装或availability字段。必须是该Case Run实际冻结的材料。原始JSON按对应原件合同解释。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| alert_id | ref.alerts | 非null | 所属告警 | `alert_materials.alert_id` |
| revision | bigint | 非null | 同告警材料版本，从1开始 | `alert_materials.revision` |
| received_at | timestamptz | 非null | 接收时间 | `alert_materials.received_at` |
| source_version | text | 可为null | 输入已有源版本，未知NULL | `alert_materials.source_version` |
| raw_text | text | 可为null | 原始字符串，保留原文 | `alert_materials.raw_text` |
| raw_json | json.raw_payload | 可为null | 合法JSON输入 | `alert_materials.raw_json` |
| ocsf_json | json.raw_payload | 可为null | 收到的OCSF原值 | `alert_materials.ocsf_json` |
| detection | json.detection | 非null | 规则、ATT&CK与来源检测评分合同 | `alert_materials.detection` |
| enrichment | json.enrichment | 可为null | 已收到富化；来源及时间 | `alert_materials.enrichment` |
| source_scope | json.source_scope | 非null | 来源引用范围、数量、截断和完整性 | `alert_materials.source_scope` |
| material_state | enum.material_state：complete,truncated,summary_only,unavailable | 非null | 原件留存状态 | `alert_materials.material_state` |
| sha256 | char(64) | 可为null | 已留存字节哈希；原大小/原hash另在retention | `alert_materials.sha256` |
| retention | json.retention | 非null | 字节数、保存形式、截断及原因 | `alert_materials.retention` |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `alert_materials.id` |
| tenant_id | uuid | 非null | 服务端认证租户UUID。 | `alert_materials.tenant_id` |


<a id="alert-triage-feedback"></a>

## alert-triage-feedback

落点：E28 triage/feedback。

triage/feedback整体可null；feedback没有4个triage派生字段。不要把此完整行当成分析目录TriageView。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| alert_id | ref.alerts | 非null | 所属告警 | `alert_assessments.alert_id` |
| kind | enum.assessment_kind：triage,human_feedback | 非null | 分诊或人工反馈 | `alert_assessments.kind` |
| input_material_id | ref.alert_materials | 可为null | 判断依据的材料版；旧未知NULL | `alert_assessments.input_material_id` |
| source_run_id | ref.runs | 可为null | 新alert_basic执行；与此告警一致 | `alert_assessments.source_run_id` |
| verdict | enum.disposition：true_positive,false_positive,benign,needs_review | 可为null | 同次判定 | `alert_assessments.verdict` |
| rationale | text | 可为null | 同次理由，历史缺失NULL | `alert_assessments.rationale` |
| confidence | numeric(6,5) | 可为null | 分诊置信度0..1，页面可乘100显示；人工无评分 | `alert_assessments.confidence` |
| score_state | enum.score_state：not_provided,not_computed,disabled,failed,available,legacy_unverified | 非null | 计算状态 | `alert_assessments.score_state` |
| recommendations | json.recommendations | 可为null | 同次建议，不与新人工判断拼接 | `alert_assessments.recommendations` |
| producer | text | 非null | 生产者及版本 | `alert_assessments.producer` |
| actor | json.actor | 非null | 实际操作者/服务身份 | `alert_assessments.actor` |
| assessed_at | timestamptz | 非null | 判断发生时间 | `alert_assessments.assessed_at` |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `alert_assessments.id` |
| freshness | string | 仅triage | 分诊输入新鲜度 | freshness_sql(alert_basic) |
| confidence_percent | number | 仅triage，可null | score_state=available且confidence非null时乘100；否则null | page_reader.view |
| run_state | RunState | 仅triage，可null | 对应alert_basic Run实际状态 | runs |
| valid_for_current_input | boolean | 仅triage | freshness=current且Run completed且输入材料ID等于当前材料 | page_reader.view |


<a id="records-objects"></a>

## records-objects

落点：E30 items[]，section=objects。

同一subject归属下的当前记录；此只读投影不意味着存在相应写入API。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| alert_id | ref.alerts | 非null | 来源告警 | `alert_objects.alert_id` |
| material_id | ref.alert_materials | 非null | 来源材料版本 | `alert_objects.material_id` |
| object_key | text | 非null | type+namespace+normalized值计算的稳定键 | `alert_objects.object_key` |
| object_type | enum.object_type：host,user,ip,domain,url,file,hash,process,email,application,cloud_resource,technique,other | 非null | 有类型的对象 | `alert_objects.object_type` |
| source_type | text | 可为null | 来源原类型；other必有 | `alert_objects.source_type` |
| object_role | enum.object_role：entity,ioc,both | 非null | 实体或IOC | `alert_objects.object_role` |
| namespace | text | 非null | 主机域/账号域/算法等身份边界 | `alert_objects.namespace` |
| raw_value | text | 非null | 原对象值 | `alert_objects.raw_value` |
| normalized_value | text | 非null | 按明确类型规则规范；不跨类型合并 | `alert_objects.normalized_value` |
| source_path | text | 非null | 来源材料字段路径 | `alert_objects.source_path` |
| attributes | json.object_attributes | 非null | 进程/端点/哈希等类型化已收属性 | `alert_objects.attributes` |
| asset_match_state | enum.asset_match：matched,ambiguous,not_found,not_checked | 非null | 当时库存匹配状态 | `alert_objects.asset_match_state` |
| asset_ref | json.external_ref | 可为null | 已有库存的类型化引用 | `alert_objects.asset_ref` |
| match_basis | json.match_basis | 可为null | 匹配依据及时间快照 | `alert_objects.match_basis` |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `alert_objects.id` |


<a id="records-sources"></a>

## records-sources

落点：E30 items[]，section=sources。

同一subject归属下的当前记录；此只读投影不意味着存在相应写入API。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| alert_id | ref.alerts | 非null | 归属告警 | `alert_source_refs.alert_id` |
| material_id | ref.alert_materials | 非null | 在哪版材料中接收到 | `alert_source_refs.material_id` |
| source_namespace | text | 非null | 湖/数据源标识 | `alert_source_refs.source_namespace` |
| source_event_id | text | 非null | 原始事件ID，有效UUID只规范表示，不拒绝其他文本 | `alert_source_refs.source_event_id` |
| relation_kind | enum.ref_kind：source_event,threshold_candidate,sequence_candidate,related_record | 非null | 来源参与方式 | `alert_source_refs.relation_kind` |
| observed_at | timestamptz | 可为null | 源事件时间 | `alert_source_refs.observed_at` |
| source_path | text | 可为null | 材料字段路径 | `alert_source_refs.source_path` |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `alert_source_refs.id` |


<a id="records-comments"></a>

## records-comments

落点：E30 items[]，section=comments。

同一subject归属下的当前记录；此只读投影不意味着存在相应写入API。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| alert_id | ref.alerts | 可为null | 所属告警 | `comments.alert_id` |
| incident_id | ref.incidents | 可为null | 所属事件 | `comments.incident_id` |
| case_id | ref.cases | 可为null | 所属Case | `comments.case_id` |
| body | text | 非null | 普通评论非空 | `comments.body` |
| author_id | uuid | 非null | 实际作者 | `comments.author_id` |
| author_name_snapshot | text | 非null | 当时显示名 | `comments.author_name_snapshot` |
| created_at | timestamptz | 非null | 创建 | `comments.created_at` |
| edited_at | timestamptz | 可为null | 实际编辑时间 | `comments.edited_at` |
| edited_by | uuid | 可为null | 实际编辑人 | `comments.edited_by` |
| row_version | bigint | 非null | 并发编辑 | `comments.row_version` |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `comments.id` |


<a id="records-responses"></a>

## records-responses

落点：E30 items[]，section=responses。

同一subject归属下的当前记录；此只读投影不意味着存在相应写入API。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| alert_id | ref.alerts | 可为null | 告警所属来源 | `response_links.alert_id` |
| incident_id | ref.incidents | 可为null | 事件所属来源 | `response_links.incident_id` |
| case_id | ref.cases | 可为null | Case所属来源 | `response_links.case_id` |
| result_id | ref.results | 可为null | 正式结果建议 | `response_links.result_id` |
| proposal_id | text | 可为null | recommendations中稳定ID；需result_id | `response_links.proposal_id` |
| legacy_proposal_ref | json.external_ref | 可为null | 没有新result时已有建议/执行来源 | `response_links.legacy_proposal_ref` |
| external_namespace | text | 非null | 已有审批执行服务命名空间 | `response_links.external_namespace` |
| approval_id | text | 可为null | 真实审批ID，不强转UUID | `response_links.approval_id` |
| action_id | text | 可为null | 真实动作ID，批准不等于执行 | `response_links.action_id` |
| linked_at | timestamptz | 非null | 关系建立 | `response_links.linked_at` |
| receipt_artifact_id | ref.artifacts | 可为null | 已有实际回执快照，同归属 | `response_links.receipt_artifact_id` |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `response_links.id` |


<a id="records-members"></a>

## records-members

落点：E30 items[]，section=members。

members仅事件，incidents仅告警。related_alerts匹配同类型/同命名空间/同对象键，并排除当前成员。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| source_namespace | text | 非null | 来源系统命名空间，不是原厂名称 | `alerts.source_namespace` |
| source_alert_id | text | 可为null | 接入来源编号；允许非UUID | `alerts.source_alert_id` |
| vendor_alert_id | text | 可为null | 厂商原始告警编号；与接入编号分开 | `alerts.vendor_alert_id` |
| connector_id | uuid | 可为null | 已有连接器引用，同租户校验 | `alerts.connector_id` |
| connector_type | text | 可为null | 接入类型原值，不代替original_vendor | `alerts.connector_type` |
| original_vendor | text | 可为null | 明确原厂，未知NULL | `alerts.original_vendor` |
| title | text | 非null | 接收到的标题；未知来源用显式缺失显示，不编造内容 | `alerts.title` |
| description | text | 可为null | 来源说明；人工补充用评论 | `alerts.description` |
| category | text | 可为null | 来源类别，不拿判定替代 | `alerts.category` |
| severity | enum.severity：info,low,medium,high,critical | 可为null | 当前来源严重程度 | `alerts.severity` |
| severity_raw | text | 可为null | 未映射来源等级原文 | `alerts.severity_raw` |
| event_time | timestamptz | 可为null | 真实发生时间 | `alerts.event_time` |
| event_time_source | enum.time_source：source,derived_source,unknown | 非null | 发生时间依据 | `alerts.event_time_source` |
| first_seen_at | timestamptz | 可为null | 已收到材料中首次活动时间 | `alerts.first_seen_at` |
| last_seen_at | timestamptz | 可为null | 已收到材料中末次活动时间 | `alerts.last_seen_at` |
| ingested_at | timestamptz | 非null | 首次接收时间 | `alerts.ingested_at` |
| source_updated_at | timestamptz | 非null | 本地保存新材料的时间 | `alerts.source_updated_at` |
| business_updated_at | timestamptz | 非null | 实际业务字段变更时间；GET不更新 | `alerts.business_updated_at` |
| handling_status | enum.alert_status：new,in_progress,completed,unknown | 非null | 业务处理状态 | `alerts.handling_status` |
| disposition | enum.disposition：true_positive,false_positive,benign,needs_review | 可为null | 当前采用判定；与latest反馈或分诊配套 | `alerts.disposition` |
| owner_id | uuid | 可为null | public.users.id | `alerts.owner_id` |
| assignment_state | enum.assignment_state：unassigned,assigned,unresolved | 非null | 分配状态 | `alerts.assignment_state` |
| owner_source_value | text | 可为null | unresolved时原负责人值 | `alerts.owner_source_value` |
| assigned_at | timestamptz | 可为null | 最近分配操作时间 | `alerts.assigned_at` |
| tags | text[] | 非null | 业务标签；资产标签从库存读取 | `alerts.tags` |
| priority_value | numeric(5,2) | 可为null | 已有优先级0到100，不以分诊分数填充 | `alerts.priority_value` |
| priority_state | enum.score_state：not_provided,not_computed,disabled,failed,available,legacy_unverified | 非null | 优先级评分状态 | `alerts.priority_state` |
| priority_source | text | 可为null | 评分生产者/模型版本 | `alerts.priority_source` |
| priority_basis | json.priority_basis | 可为null | 评分来源依据；无值不造理由 | `alerts.priority_basis` |
| closed_at | timestamptz | 可为null | 当前完成周期关闭时间；重开后置空，旧值在活动中 | `alerts.closed_at` |
| closed_by | uuid | 可为null | 明确用户关闭人；自动关闭记录活动服务身份 | `alerts.closed_by` |
| reopened_at | timestamptz | 可为null | 最近明确重开时间 | `alerts.reopened_at` |
| latest_material_id | ref.alert_materials | 可为null | 同告警最新有效材料 | `alerts.latest_material_id` |
| latest_triage_id | ref.alert_assessments | 可为null | 同告警kind=triage记录 | `alerts.latest_triage_id` |
| latest_feedback_id | ref.alert_assessments | 可为null | 同告警kind=human_feedback记录 | `alerts.latest_feedback_id` |
| row_version | bigint | 非null | 管理乐观锁；每次实际写入+1 | `alerts.row_version` |
| latest_explanation_id | ref.artifacts | 可为null | 同告警kind=alert_explanation的有效Explain材料；GET不生成并写业务时钟 | `alerts.latest_explanation_id` |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `alerts.id` |
| linked_at | timestamptz | 非null | 加入时间 | incident_alerts.linked_at |
| membership_source | enum.membership_source | 非null | 成员产生方式 | incident_alerts.membership_source |
| correlation_basis | json.correlation_basis | 非null | 实际规则、对象类型、值、窗口及候选关系 | incident_alerts.correlation_basis |
| basis_version | text | 非null | 归并算法/合同版本 | incident_alerts.basis_version |


<a id="records-incidents"></a>

## records-incidents

落点：E30 items[]，section=incidents。

members仅事件，incidents仅告警。related_alerts匹配同类型/同命名空间/同对象键，并排除当前成员。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| source_namespace | text | 非null | Fusion实例/来源命名空间 | `incidents.source_namespace` |
| source_incident_id | text | 非null | 来源事件ID，兼容原有文本键 | `incidents.source_incident_id` |
| title | text | 非null | 事件自身标题 | `incidents.title` |
| description | text | 可为null | 事件自身说明，非第一条成员标题 | `incidents.description` |
| handling_status | enum.work_status：new,in_progress,resolved,unknown | 非null | 事件业务处理状态 | `incidents.handling_status` |
| owner_id | uuid | 可为null | 当前明确负责人 | `incidents.owner_id` |
| assignment_state | enum.assignment_state：unassigned,assigned,unresolved | 非null | 未分配/已分配/原值未解析 | `incidents.assignment_state` |
| owner_source_value | text | 可为null | 未解析来源负责人 | `incidents.owner_source_value` |
| assigned_at | timestamptz | 可为null | 最近改派时间 | `incidents.assigned_at` |
| tags | text[] | 非null | 事件业务标签，成员资产标签另外派生 | `incidents.tags` |
| severity_override | enum.severity：info,low,medium,high,critical | 可为null | 人工事件覆盖等级；NULL=采用成员最高；不改成员 | `incidents.severity_override` |
| severity_override_reason | text | 可为null | 人工覆盖依据 | `incidents.severity_override_reason` |
| severity_override_at | timestamptz | 可为null | 覆盖设置时间 | `incidents.severity_override_at` |
| severity_override_by | uuid | 可为null | 覆盖人 | `incidents.severity_override_by` |
| priority_value | numeric(5,2) | 可为null | 已有优先级0..100 | `incidents.priority_value` |
| priority_state | enum.score_state：not_provided,not_computed,disabled,failed,available,legacy_unverified | 非null | 无来源不合成 | `incidents.priority_state` |
| priority_source | text | 可为null | 已有评分生产者 | `incidents.priority_source` |
| priority_basis | json.priority_basis | 可为null | 评分依据 | `incidents.priority_basis` |
| resolution_note | text | 可为null | 事件解决说明，人工解决必填 | `incidents.resolution_note` |
| resolved_at | timestamptz | 可为null | 当前解决周期时间 | `incidents.resolved_at` |
| resolved_by | uuid | 可为null | 解决人 | `incidents.resolved_by` |
| reopened_at | timestamptz | 可为null | 最近明确重开时间 | `incidents.reopened_at` |
| created_at | timestamptz | 非null | 事件首次持久化时间 | `incidents.created_at` |
| business_updated_at | timestamptz | 非null | 自身管理或成员关联变动；移除最后成员仍更新 | `incidents.business_updated_at` |
| latest_diagnosis_id | ref.incident_diagnoses | 可为null | 同事件最新成功诊断；失败尝试不能覆盖 | `incidents.latest_diagnosis_id` |
| row_version | bigint | 非null | 管理/范围写入乐观版本 | `incidents.row_version` |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `incidents.id` |
| linked_at | timestamptz | 非null | 加入时间 | incident_alerts.linked_at |
| membership_source | enum.membership_source | 非null | 成员产生方式 | incident_alerts.membership_source |
| correlation_basis | json.correlation_basis | 非null | 实际规则、对象类型、值、窗口及候选关系 | incident_alerts.correlation_basis |
| basis_version | text | 非null | 归并算法/合同版本 | incident_alerts.basis_version |


<a id="records-related_alerts"></a>

## records-related_alerts

落点：E30 items[]，section=related_alerts。

members仅事件，incidents仅告警。related_alerts匹配同类型/同命名空间/同对象键，并排除当前成员。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| source_namespace | text | 非null | 来源系统命名空间，不是原厂名称 | `alerts.source_namespace` |
| source_alert_id | text | 可为null | 接入来源编号；允许非UUID | `alerts.source_alert_id` |
| vendor_alert_id | text | 可为null | 厂商原始告警编号；与接入编号分开 | `alerts.vendor_alert_id` |
| connector_id | uuid | 可为null | 已有连接器引用，同租户校验 | `alerts.connector_id` |
| connector_type | text | 可为null | 接入类型原值，不代替original_vendor | `alerts.connector_type` |
| original_vendor | text | 可为null | 明确原厂，未知NULL | `alerts.original_vendor` |
| title | text | 非null | 接收到的标题；未知来源用显式缺失显示，不编造内容 | `alerts.title` |
| description | text | 可为null | 来源说明；人工补充用评论 | `alerts.description` |
| category | text | 可为null | 来源类别，不拿判定替代 | `alerts.category` |
| severity | enum.severity：info,low,medium,high,critical | 可为null | 当前来源严重程度 | `alerts.severity` |
| severity_raw | text | 可为null | 未映射来源等级原文 | `alerts.severity_raw` |
| event_time | timestamptz | 可为null | 真实发生时间 | `alerts.event_time` |
| event_time_source | enum.time_source：source,derived_source,unknown | 非null | 发生时间依据 | `alerts.event_time_source` |
| first_seen_at | timestamptz | 可为null | 已收到材料中首次活动时间 | `alerts.first_seen_at` |
| last_seen_at | timestamptz | 可为null | 已收到材料中末次活动时间 | `alerts.last_seen_at` |
| ingested_at | timestamptz | 非null | 首次接收时间 | `alerts.ingested_at` |
| source_updated_at | timestamptz | 非null | 本地保存新材料的时间 | `alerts.source_updated_at` |
| business_updated_at | timestamptz | 非null | 实际业务字段变更时间；GET不更新 | `alerts.business_updated_at` |
| handling_status | enum.alert_status：new,in_progress,completed,unknown | 非null | 业务处理状态 | `alerts.handling_status` |
| disposition | enum.disposition：true_positive,false_positive,benign,needs_review | 可为null | 当前采用判定；与latest反馈或分诊配套 | `alerts.disposition` |
| owner_id | uuid | 可为null | public.users.id | `alerts.owner_id` |
| assignment_state | enum.assignment_state：unassigned,assigned,unresolved | 非null | 分配状态 | `alerts.assignment_state` |
| owner_source_value | text | 可为null | unresolved时原负责人值 | `alerts.owner_source_value` |
| assigned_at | timestamptz | 可为null | 最近分配操作时间 | `alerts.assigned_at` |
| tags | text[] | 非null | 业务标签；资产标签从库存读取 | `alerts.tags` |
| priority_value | numeric(5,2) | 可为null | 已有优先级0到100，不以分诊分数填充 | `alerts.priority_value` |
| priority_state | enum.score_state：not_provided,not_computed,disabled,failed,available,legacy_unverified | 非null | 优先级评分状态 | `alerts.priority_state` |
| priority_source | text | 可为null | 评分生产者/模型版本 | `alerts.priority_source` |
| priority_basis | json.priority_basis | 可为null | 评分来源依据；无值不造理由 | `alerts.priority_basis` |
| closed_at | timestamptz | 可为null | 当前完成周期关闭时间；重开后置空，旧值在活动中 | `alerts.closed_at` |
| closed_by | uuid | 可为null | 明确用户关闭人；自动关闭记录活动服务身份 | `alerts.closed_by` |
| reopened_at | timestamptz | 可为null | 最近明确重开时间 | `alerts.reopened_at` |
| latest_material_id | ref.alert_materials | 可为null | 同告警最新有效材料 | `alerts.latest_material_id` |
| latest_triage_id | ref.alert_assessments | 可为null | 同告警kind=triage记录 | `alerts.latest_triage_id` |
| latest_feedback_id | ref.alert_assessments | 可为null | 同告警kind=human_feedback记录 | `alerts.latest_feedback_id` |
| row_version | bigint | 非null | 管理乐观锁；每次实际写入+1 | `alerts.row_version` |
| latest_explanation_id | ref.artifacts | 可为null | 同告警kind=alert_explanation的有效Explain材料；GET不生成并写业务时钟 | `alerts.latest_explanation_id` |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `alerts.id` |


<a id="activity"></a>

## activity

落点：E17 items[]；E30 activities items[]。

E17按Case/当前成员/显式事件等集合匹配，保留operation_id；E30仅实际subject或target且剔除operation_id，不按共享Case泛化活动。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| actor | json.actor | 非null | 真实人/服务身份和名称快照 | `activities.actor` |
| action | text | 非null | 受版本控制业务动作码，见action_registry合同 | `activities.action` |
| subject_alert_id | ref.alerts | 可为null | 主对象告警 | `activities.subject_alert_id` |
| subject_incident_id | ref.incidents | 可为null | 主对象事件 | `activities.subject_incident_id` |
| subject_case_id | ref.cases | 可为null | 主对象Case | `activities.subject_case_id` |
| occurred_at | timestamptz | 非null | 实际操作时间 | `activities.occurred_at` |
| summary | text | 非null | 可读操作摘要，不能替代结构目标 | `activities.summary` |
| detail | json.activity_detail | 非null | 请求原因和未完成原因，不复制完整原件 | `activities.detail` |
| operation_id | uuid | 非null，仅E17 | 一次批量操作分组，所有目标同ID；E30 public投影不返回此字段 | activities.operation_id |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `activities.id` |
| matching_targets | array | 非null | 匹配的具体目标，见activity-target；至多200 | activity_targets |
| targets_truncated | boolean | 非null | 该活动匹配目标超过200时true | 读取计数 |


<a id="activity-target"></a>

## activity-target

落点：活动matching_targets[]。



| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| activity_id | ref.activities | 非null | 所属实际活动 | `activity_targets.activity_id` |
| alert_id | ref.alerts | 可为null | 被处理告警 | `activity_targets.alert_id` |
| incident_id | ref.incidents | 可为null | 被处理事件 | `activity_targets.incident_id` |
| case_id | ref.cases | 可为null | 被处理Case | `activity_targets.case_id` |
| task_id | ref.tasks | 可为null | 被处理任务 | `activity_targets.task_id` |
| run_id | ref.runs | 可为null | 被操作执行 | `activity_targets.run_id` |
| result_id | ref.results | 可为null | 被采用/保存结果 | `activity_targets.result_id` |
| comment_id | ref.comments | 可为null | 评论 | `activity_targets.comment_id` |
| before_value | json.activity_value | 可为null | 相关变更字段前值；新建NULL | `activity_targets.before_value` |
| after_value | json.activity_value | 可为null | 相关变更字段后值；移除NULL | `activity_targets.after_value` |
| result_state | enum.activity_result：succeeded,failed,skipped | 非null | 实际成功/跳过/失败 | `activity_targets.result_state` |
| reason | text | 可为null | 跳过/失败原因 | `activity_targets.reason` |
| id | uuid | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `activity_targets.id` |


<a id="records-cases"></a>

## records-cases

落点：E30 section=cases 的items[]。

同一事件可通过成员或显式关系属于一个Case，两种布尔来源分开。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| id / title / handling_status / scope_revision | Case原类型 | 非null | 对应Case身份、标题、处理状态和当前范围版本 | cases |
| via_member_alert | boolean | 非null | 至少一个当前成员告警也属于该Case | case_alerts |
| explicit_incident_link | boolean | 非null | 事件存在显式case_incidents关系；告警subject固定false | case_incidents |


<a id="records-assets"></a>

## records-assets

落点：E30 section=assets 的items[]。

对象–资产匹配边；total统计边，多个对象/资产可能重复，不是资产库存列表。只读匹配，不保存关联。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| object_id / alert_id / material_id | UUID | 非null | 当前对象行、所属告警和材料版本 | alert_objects |
| object_key / namespace | string | 非null | 来源对象键和命名空间 | alert_objects |
| asset_id | UUID | 非null | 匹配的外部库存资产身份 | 配置的assets只读关系 |
| name / fqdn / asset_type / criticality / os / os_version | 库存字段原类型 | 按库存保留缺值 | 资产名称、FQDN、类型、关键性、操作系统及版本，不是调查判断 | 配置的assets只读关系 |
| tags / ip_addresses | array | 按库存保留 | 资产标签与IP列表；不能用告警tags替代 | 配置的assets只读关系 |
| match_basis | string枚举 | 非null | exact_ip / exact_name_casefold / exact_fqdn_casefold，真实命中方式 | page_reader.assets |


<a id="overall-stats"></a>

## overall-stats

落点：E26/E27 overall_stats。

都是平铺字段，没有by_state对象；指标与当前分页分开。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| total | integer | 非null | 本租户该主体总数 | 主体表 |
| new / in_progress / unknown | integer | 非null | 各业务处理状态的主体数量，未输出completed/resolved专门键 | 主体handling_status分组 |
| high_severity | integer | 非null | 告警high/critical；事件有效严重度high/critical | page_reader.stats |
| investigating | integer | 仅告警 | 出现在running baseline里的不同告警数，不是A分诊运行数 | run_members + runs |
| active | integer | 仅事件 | new+in_progress事件数 | 业务状态汇总 |
| unassigned | integer | 仅事件 | assignment_state=unassigned事件数 | incidents |
| grouped_alert_count | integer | 仅事件 | 所有事件成员关系中的去重告警数 | incident_alerts |
| new_alerts_24h | integer | 仅事件 | 24小时窗口内含新增发生告警的事件数；不是告警条数 | 成员alerts.event_time |


<a id="usage-total"></a>

## usage-total

落点：E12/E13/E32 usage。

Case按返回的步骤目录汇总；A/I trace另读全部模型usage。未知不补0。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| model_calls | integer | 非null | 全部非planned/skipped模型步骤数，含失败尝试 | run_steps计数 |
| known_total_tokens | integer | 非null | usage_state=reported且total_tokens为有效非负整数的合计 | 步骤usage |
| unknown_token_calls | integer | 非null | model_calls减有明确token的调用数 | 计数差 |
| total_tokens | integer | 可null | 所有模型调用都有明确token时返回总和，否则null；无调用时可为0 | known_calls==model_calls |
| costs_by_currency_and_price_version | array | 非null | 仅已定价且成本有效的分组数组，空不代表所有调用免费 | usage.cost_state |
| costs_by_currency_and_price_version[].currency | string | 非null | 币种 | 步骤usage |
| costs_by_currency_and_price_version[].price_version | string | 非null | 价格版本 | 步骤usage |
| costs_by_currency_and_price_version[].cost | decimal字符串 | 非null | 同币种同价格版本累计成本 | Decimal合计 |
| unpriced_model_calls | integer | 非null | 未能得出有效价格的模型调用数量 | model_calls-priced_calls |


<a id="delivery"></a>

## delivery

落点：E14 delivery。

无可识别C6交付回执时整个对象null。

| 字段 | 类型/合同 | 空值或出现条件 | 业务含义/取值规则 | 实际来源 |
| --- | --- | --- | --- | --- |
| receipt_artifact_id | UUID | 非null | C6输出回执工件ID | C6 step.output_artifact_id |
| detail_artifact_id | UUID | 非null | 结构化报告/交付详情工件ID | 回执detail_artifact_id |
| markdown_artifact_id | UUID | 非null | 可读报告文本工件ID | 回执markdown_artifact_id |
| detail | object | 非null | 上述detail工件已保存content_json，须与result_id匹配，结构随该工件schema版本 | case_reader.result |


## 版本化正文需要继续沿原件合同读取

- 告警材料：E31.content_json仅包装raw_json/ocsf_json/enrichment，content_text是raw_text。原始厂商JSON保留原结构，不能宣称有统一的固定字段清单。E18是冻结材料整行，结构不同。
- 事件DiagnosisView.diagnosis沿既有diagnosis合同：conclusion、validation_state、findings、source_refs、limitations、program_facts、partial_review_artifact_id、delivery_assessment；open_questions独立列返回。delivery_assessment的完整性、成员覆盖和待复核分别展示，不由state=completed推断质量通过。
- ExplanationView.content：A解释沿alert_explanation合同；partial_analysis.content是被保存的partial_review，含完整/不完整状态和可保留内容，不能统一当A解释。
- ResultView.findings/questions/recommendations/case_impact的字段已在固定字段表逐一列出；D07保留questions[].state作为当轮内容状态，不建设独立问题管理。
- 工件content_json/content_text是多类型容器。先看artifact.kind/schema_version，再按现有artifact_contracts或对应执行器保存合同解释；模型请求、原答、工具请求/结果、图、报告、输入快照不能套成同一结构。外部来源parameters、原始正文和历史版本中的新增键保留，不在本轮编造字段或丢弃未知业务值。
- 已有JSON合同是机器形状来源，不能代替实现启用证据。当前工件版本、动态字段未在HTTP响应Schema固定的事实列为交接限制；本次补字段说明，不修改服务输出。

## 原件可用性与错误不能统一处理

Case工件完整性不符抛HTTP409 `artifact_integrity_invalid`。A/I工件同类情况返回HTTP200、`availability=content_integrity_mismatch`、正文null。解释/partial_review以available=false与reason说明。原材料正文超限用content_exceeds_read_limit，普通工件可能用content_exceeds_read_limit_or_size_unknown或external_content_not_loaded。

E18冻结材料不经过以上ContentView可用性包装，直接返回实际材料行；调用方读material_state/retention且保留空正文，不能凭没有availability认定完整。
