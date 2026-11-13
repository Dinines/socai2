# HTTP输出字段逐项审计

2026-11-12，静态文档/实现核对。复用既有OpenAPI类型、当前字段字典语义和实际读取装配；未调用业务接口、数据库或模型。此表解释HTTP字段，不要求业务后端直接查库。

固定响应模型中的每个字段在下文列出；嵌套类型可点名称继续查看。`required`与`null`分开：字段必须出现仍可为null；可省略不等于客户端可自行补0。表中required取原OpenAPI声明；“可省略”指规范未列为required，当前响应装配若显式写出字段或默认值，实际仍会包含，不能从缺失自行推断业务状态。各结构的动态dict/items/工件正文在[动态字段](dynamic-fields.md)继续展开。输入、用途和功能对应见[47操作审计](interfaces.md)。

<a id="aiunavailable"></a>

## AIUnavailable

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| detail | [AIUnavailableDetail](#aiunavailabledetail) | 可省略 | 非null | 此501响应固定为AIUnavailableDetail对象（code/status/message），不是字符串或数组。 | [case_ai_contracts.py](../../../services/api/app/socai2/case_ai_contracts.py#L37) |


<a id="aiunavailabledetail"></a>

## AIUnavailableDetail

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| code | string = case_ai_not_implemented | 可省略 | 非null | 机器可识别的错误码；AI预留固定case_ai_not_implemented。 | [case_ai_contracts.py](../../../services/api/app/socai2/case_ai_contracts.py#L31) |
| status | string = not_implemented | 可省略 | 非null | AI预留固定not_implemented；不表示业务执行状态。 | [case_ai_contracts.py](../../../services/api/app/socai2/case_ai_contracts.py#L31) |
| message | string | 可省略 | 非null | 面向接手人的错误说明文本。 | [case_ai_contracts.py](../../../services/api/app/socai2/case_ai_contracts.py#L31) |


<a id="alertfacts"></a>

## AlertFacts

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string uuid | 是 | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `socai2.alerts.id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| source_namespace | string | 是 | 非null | 来源系统命名空间，不是原厂名称 | `socai2.alerts.source_namespace`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| title | string | 是 | 非null | 接收到的标题；未知来源用显式缺失显示，不编造内容 | `socai2.alerts.title`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| description | string / null | 是 | 可为null | 来源说明；人工补充用评论 | `socai2.alerts.description`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| owner_id | string uuid / null | 是 | 可为null | public.users.id | `socai2.alerts.owner_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| assignment_state | [AssignmentState](#assignmentstate) | 是 | 非null | 分配状态 | `socai2.alerts.assignment_state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| owner_source_value | string / null | 是 | 可为null | unresolved时原负责人值 | `socai2.alerts.owner_source_value`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| assigned_at | string date-time / null | 是 | 可为null | 最近分配操作时间 | `socai2.alerts.assigned_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| tags | array〈string〉 | 是 | 非null | 业务标签；资产标签从库存读取 | `socai2.alerts.tags`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| priority_value | string / null | 是 | 可为null | 已有优先级0到100，不以分诊分数填充 | `socai2.alerts.priority_value`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| priority_state | [ScoreState](#scorestate) | 是 | 非null | 优先级评分状态 | `socai2.alerts.priority_state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| priority_source | string / null | 是 | 可为null | 评分生产者/模型版本 | `socai2.alerts.priority_source`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| priority_basis | object / null | 是 | 可为null | 评分来源依据；无值不造理由 | `socai2.alerts.priority_basis`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| business_updated_at | string date-time | 是 | 非null | 实际业务字段变更时间；GET不更新 | `socai2.alerts.business_updated_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| reopened_at | string date-time / null | 是 | 可为null | 最近明确重开时间 | `socai2.alerts.reopened_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| row_version | integer | 是 | 非null | 管理乐观锁；每次实际写入+1 | `socai2.alerts.row_version`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| source_alert_id | string / null | 是 | 可为null | 接入来源编号；允许非UUID | `socai2.alerts.source_alert_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| vendor_alert_id | string / null | 是 | 可为null | 厂商原始告警编号；与接入编号分开 | `socai2.alerts.vendor_alert_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| connector_id | string uuid / null | 是 | 可为null | 已有连接器引用，同租户校验 | `socai2.alerts.connector_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| connector_type | string / null | 是 | 可为null | 接入类型原值，不代替original_vendor | `socai2.alerts.connector_type`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| original_vendor | string / null | 是 | 可为null | 明确原厂，未知NULL | `socai2.alerts.original_vendor`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| category | string / null | 是 | 可为null | 来源类别，不拿判定替代 | `socai2.alerts.category`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| severity | [Severity](#severity) / null | 是 | 可为null | 当前来源严重程度 | `socai2.alerts.severity`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| severity_raw | string / null | 是 | 可为null | 未映射来源等级原文 | `socai2.alerts.severity_raw`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| event_time | string date-time / null | 是 | 可为null | 真实发生时间 | `socai2.alerts.event_time`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| event_time_source | [TimeSource](#timesource) | 是 | 非null | 发生时间依据 | `socai2.alerts.event_time_source`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| first_seen_at | string date-time / null | 是 | 可为null | 已收到材料中首次活动时间 | `socai2.alerts.first_seen_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| last_seen_at | string date-time / null | 是 | 可为null | 已收到材料中末次活动时间 | `socai2.alerts.last_seen_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| ingested_at | string date-time | 是 | 非null | 首次接收时间 | `socai2.alerts.ingested_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| source_updated_at | string date-time | 是 | 非null | 本地保存新材料的时间 | `socai2.alerts.source_updated_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| handling_status | [AlertStatus](#alertstatus) | 是 | 非null | 业务处理状态 | `socai2.alerts.handling_status`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| disposition | [Disposition](#disposition) / null | 是 | 可为null | 当前采用判定；与latest反馈或分诊配套 | `socai2.alerts.disposition`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| closed_at | string date-time / null | 是 | 可为null | 当前完成周期关闭时间；重开后置空，旧值在活动中 | `socai2.alerts.closed_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| closed_by | string uuid / null | 是 | 可为null | 明确用户关闭人；自动关闭记录活动服务身份 | `socai2.alerts.closed_by`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| latest_material_id | string uuid / null | 是 | 可为null | 同告警最新有效材料 | `socai2.alerts.latest_material_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| latest_triage_id | string uuid / null | 是 | 可为null | 同告警kind=triage记录 | `socai2.alerts.latest_triage_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| latest_feedback_id | string uuid / null | 是 | 可为null | 同告警kind=human_feedback记录 | `socai2.alerts.latest_feedback_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| latest_explanation_id | string uuid / null | 是 | 可为null | 同告警kind=alert_explanation的有效Explain材料；GET不生成并写业务时钟 | `socai2.alerts.latest_explanation_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |


<a id="alertstatus"></a>

## AlertStatus

string；new, in_progress, completed, unknown

<a id="artifactcontent"></a>

## ArtifactContent

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| artifact | object | 是 | 非null | Case工件元数据，和A/I的metadata字段不同。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L375) |
| content_json | any / null | 是 | 可为null | 保存的结构化正文；格式由工件schema_version和实际类型决定。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L375) |
| content_text | string / null | 是 | 可为null | 保存的文本正文，可空；不得自动重生成。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L375) |
| availability | string | 是 | 非null | Case工件读取状态；内容hash/size不一致直接409 artifact_integrity_invalid，不返回成功正文。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L375) |


<a id="assessmentpageview"></a>

## AssessmentPageView

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string uuid | 是 | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `socai2.case_assessments.id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| conclusion | string | 是 | 非null | 明确采用的判断 | `socai2.case_assessments.conclusion`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| origin | string；model, human, system, legacy | 是 | 非null | model/human/legacy，system交接不得采用为有效结论 | `socai2.case_assessments.origin`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| validity | string | 是 | 非null | 采用时有效性；不代表绝对事实证明 | `socai2.case_assessments.validity`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| scope_revision | integer | 是 | 非null | 采用时Case范围版本 | `socai2.case_assessments.scope_revision`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| formed_at | string date-time | 是 | 非null | 判断形成时间 | `socai2.case_assessments.formed_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| adopted_at | string date-time | 是 | 非null | 采用时间 | `socai2.case_assessments.adopted_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| alert_ids | array〈string uuid〉 | 是 | 非null | 真实告警UUID集合，禁止重复；具体是新增、完整替换或反馈覆盖范围见操作说明。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L125) |
| sources | array〈object〉 | 是 | 非null | 该已采用判断的来源行；page_data版本保留tenant_id，CaseDetail.current_assessment版本剔除内部字段。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L125) |


<a id="assignmentstate"></a>

## AssignmentState

string；unassigned, assigned, unresolved

<a id="associationreceipt"></a>

## AssociationReceipt

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| case_id | string uuid | 是 | 非null | Case UUID；来自真实回执/列表，不是页面展示编号。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L107) |
| scope_revision | integer | 是 | 非null | Case成员范围版本，历史Run保持冻结值。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L107) |
| pending_run_id | string uuid / null | 是 | 可为null | 准备好的待启动Run；需要用户显式调用start。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L107) |
| changed | boolean | 是 | 非null | 本次写入是否实际改变业务内容；幂等重读不表示重新执行。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L107) |
| added_alert_ids | array〈string uuid〉 | 可省略 | 非null | 本次实际新增Case成员UUID。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L107) |
| linked_incident_ids | array〈string uuid〉 | 可省略 | 非null | 本次新增的显式事件关系UUID。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L107) |


<a id="baselinecounts"></a>

## BaselineCounts

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| running | integer | 是 | 非null | 运行中基础Run数量。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L85) |
| unknown | integer | 是 | 非null | 执行状态未确认的基础Run数量，仍占活跃约束。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L85) |


<a id="baselinepreparation"></a>

## BaselinePreparation

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| case_id | string uuid | 是 | 非null | Case UUID；来自真实回执/列表，不是页面展示编号。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L85) |
| scope_revision | integer | 是 | 非null | Case成员范围版本，历史Run保持冻结值。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L85) |
| pending_run_id | string uuid | 是 | 非null | 准备好的待启动Run；需要用户显式调用start。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L85) |
| created | boolean | 是 | 非null | 是否本次新建pending记录；false可能复用已有待启动项。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L85) |


<a id="casebaselinerecord"></a>

## CaseBaselineRecord

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| run | [RunView](#runview) | 是 | 非null | 对应的执行记录；嵌套类型或动态结构见下表，不能和正式结果/当前判断混用。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L283) |
| start_eligibility | [StartAvailability](#startavailability) | 是 | 非null | 是否可启动及原因，依据最新Run与Case范围。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L283) |


<a id="casedatareceipt"></a>

## CaseDataReceipt

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| case_id | string uuid | 是 | 非null | Case UUID；来自真实回执/列表，不是页面展示编号。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L105) |
| row_version | integer | 是 | 非null | 并发修改版本；后续写入的expected_row_version取此值。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L105) |
| changed | boolean | 是 | 非null | 是否改变资料/目录；返回回执后刷新最新row_version，幂等重放不生成新版本。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L105) |
| current_evidence_artifact_id | string uuid / null | 是 | 可为null | 本次保存后当前证据目录工件UUID；未有目录为null。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L105) |


<a id="casedetail"></a>

## CaseDetail

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| case | [CaseView](#caseview) | 是 | 非null | 当前案件主体资料，不是执行记录。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L307) |
| members | array〈object〉 | 是 | 非null | 此对象的成员列表；Case为当前成员，Run/Result为当轮冻结成员，动态字段见专门清单。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L307) |
| member_count | integer | 是 | 非null | 成员总数；超过返回长度时结合members_truncated，不把当前数组长度当全量。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L307) |
| members_truncated | boolean | 是 | 非null | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L307) |
| linked_incidents | array〈object〉 | 是 | 非null | Case显式关联事件，不包含仅共享成员而无显式关系的事件。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L307) |
| linked_incident_count | integer | 是 | 非null | 本案显式事件关系总数。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L307) |
| linked_incidents_truncated | boolean | 是 | 非null | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L307) |
| current_assessment | object / null | 是 | 可为null | 当前采用判断及来源/覆盖；null表示未形成，不能自行采用最近结果。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L307) |
| baseline_records | array〈object〉 | 是 | 非null | 本案pending_update/running/unknown基础Run及资格；已结束历史另读history。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L307) |
| page_data | [CasePageData](#casepagedata) / null | 可省略 | 可为null | 本案分类/期限/当前判断和证据目录投影。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L307) |


<a id="casepagedata"></a>

## CasePageData

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| schema_version | string = socai2.case-page-data.v1 | 可省略 | 非null | 本结构/工件的合同版本；按实际版本解释字段，不把当前模型结构套给历史版本。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L137) |
| classification | string；true_positive, informational, false_positive / null | 是 | 可为null | 案件分类true_positive/informational/false_positive；null未设置；队列可用not_set过滤未设置。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L137) |
| due_at | string date-time / null | 是 | 可为null | 带时区的截止时间；null清空。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L137) |
| determination | string / null | 是 | 可为null | 沿Case.current_assessment_id取得的已采用conclusion；没有指针为null，不取最新Result补。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L137) |
| assessment | [AssessmentPageView](#assessmentpageview) / null | 是 | 可为null | 已采用判断的页面投影。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L137) |
| evidence | [EvidenceView](#evidenceview) | 是 | 非null | 已发布证据目录及可用状态。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L137) |


<a id="casequeueitem"></a>

## CaseQueueItem

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| case | [CaseView](#caseview) | 是 | 非null | 当前案件主体资料，不是执行记录。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L288) |
| member_count | integer；minimum=0.0 | 是 | 非null | 成员总数；超过返回长度时结合members_truncated，不把当前数组长度当全量。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L288) |
| open_task_count | integer；minimum=0.0 | 是 | 非null | 本案not_started或in_progress人工任务数，questions不计入。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L288) |
| baseline_records | array〈[CaseBaselineRecord](#casebaselinerecord)〉 | 是 | 非null | 本案pending_update/running/unknown基础Run及资格；已结束历史另读history。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L288) |
| page_data | [CasePageData](#casepagedata) / null | 可省略 | 可为null | 本案分类/期限/当前判断和证据目录投影。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L288) |


<a id="casequeuemetrics"></a>

## CaseQueueMetrics

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| awaiting_assignment | integer；minimum=0.0 | 是 | 非null | handling_status为new/in_progress，且assignment_state=unassigned、owner_id=null的Case数；已解决/未知状态与unresolved分配不计。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L276) |
| in_progress | integer；minimum=0.0 | 是 | 非null | 处理状态为in_progress的Case数；不是运行中的Run数。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L276) |
| high_severity | integer；minimum=0.0 | 是 | 非null | handling_status为new/in_progress且severity=high的Case数；不含critical，也不含resolved/unknown。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L276) |
| awaiting_human | integer；minimum=0.0 | 是 | 非null | handling_status为new/in_progress且至少有一个当前修订为not_started/in_progress人工任务的Case数；不是任务条数。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L276) |


<a id="casequeuepage"></a>

## CaseQueuePage

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| items | array〈[CaseQueueItem](#casequeueitem)〉 | 是 | 非null | 本页记录数组；元素类型在本行类型中说明，空数组仅表示此查询页没有记录。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L296) |
| total | integer；minimum=0.0 | 是 | 非null | 当前集合总数；records/assets为对象资产匹配边数。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L296) |
| next_cursor | string / null | 是 | 可为null | 下一页游标；null表示结束。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L296) |
| metrics | [CaseQueueMetrics](#casequeuemetrics) | 是 | 非null | Case租户整体指标，不随分页或筛选total变化。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L296) |


<a id="caseview"></a>

## CaseView

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string uuid | 是 | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `socai2.cases.id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| source_namespace | string / null | 是 | 可为null | Case固定数据身份命名空间；首次范围绑定后不可改，旧范围不能确认时NULL；不等于原始来源环境 | `socai2.cases.source_namespace`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| title | string | 是 | 非null | 名称 | `socai2.cases.title`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| description | string / null | 是 | 可为null | 案情说明 | `socai2.cases.description`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| handling_status | [WorkStatus](#workstatus) | 是 | 非null | 业务状态 | `socai2.cases.handling_status`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| severity | [Severity](#severity) / null | 是 | 可为null | 当前明确案件等级 | `socai2.cases.severity`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| severity_source | string / null | 是 | 可为null | 手动设置或明确汇总规则，不从置信度猜 | `socai2.cases.severity_source`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| owner_id | string uuid / null | 是 | 可为null | 当前负责人 | `socai2.cases.owner_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| assignment_state | [AssignmentState](#assignmentstate) | 是 | 非null | 分配状态 | `socai2.cases.assignment_state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| owner_source_value | string / null | 是 | 可为null | 历史未解析负责人 | `socai2.cases.owner_source_value`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| assigned_at | string date-time / null | 是 | 可为null | 最近分配时间 | `socai2.cases.assigned_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| tags | array〈string〉 | 是 | 非null | 案件标签 | `socai2.cases.tags`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| priority_value | string / null | 是 | 可为null | 已有优先级 | `socai2.cases.priority_value`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| priority_state | [ScoreState](#scorestate) | 是 | 非null | 评分状态 | `socai2.cases.priority_state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| priority_source | string / null | 是 | 可为null | 评分生产者 | `socai2.cases.priority_source`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| priority_basis | object / null | 是 | 可为null | 已有依据 | `socai2.cases.priority_basis`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| scope_revision | integer | 是 | 非null | 仅当前告警成员真实变动+1 | `socai2.cases.scope_revision`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| current_assessment_id | string uuid / null | 是 | 可为null | 已明确采用版本；不等于最新Run | `socai2.cases.current_assessment_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| classification | string；true_positive, informational, false_positive / null | 可省略 | 可为null | 明确保存的案件管理分类；NULL未设置，不继承事件或告警 | `socai2.cases.classification`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| due_at | string date-time / null | 可省略 | 可为null | 案件截止时间，与任务期限和运行超时分离 | `socai2.cases.due_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| current_evidence_artifact_id | string uuid / null | 可省略 | 可为null | 同租户同Case的当前case_evidence_index不可变工件；NULL未记录 | `socai2.cases.current_evidence_artifact_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| created_at | string date-time | 是 | 非null | 创建时间 | `socai2.cases.created_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| created_by | string uuid / null | 是 | 可为null | 创建人，服务创建见活动 | `socai2.cases.created_by`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| business_updated_at | string date-time | 是 | 非null | 案件业务变化 | `socai2.cases.business_updated_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| resolved_at | string date-time / null | 是 | 可为null | 当前解决周期时间 | `socai2.cases.resolved_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| resolved_by | string uuid / null | 是 | 可为null | 明确解决人 | `socai2.cases.resolved_by`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| resolution_note | string / null | 是 | 可为null | 解决说明，不擅自添加必填要求 | `socai2.cases.resolution_note`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| reopened_at | string date-time / null | 是 | 可为null | 最近重开 | `socai2.cases.reopened_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| row_version | integer | 是 | 非null | 乐观版本 | `socai2.cases.row_version`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |


<a id="changekind"></a>

## ChangeKind

string；initial, unchanged, expanded, revised, withdrawn, not_comparable

<a id="conclusionstate"></a>

## ConclusionState

string；supported, uncertain, unavailable

<a id="contentview"></a>

## ContentView

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| metadata | object | 是 | 非null | A/I工件/材料元数据。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L138) |
| availability | string | 是 | 非null | A/I读取状态；工件hash/size不一致仍HTTP200但availability=content_integrity_mismatch且正文null。材料正文使用独立大小限制状态。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L138) |
| content_json | any | 可省略 | 非null | 保存的结构化正文；格式由工件schema_version和实际类型决定。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L138) |
| content_text | string / null | 可省略 | 可为null | 保存的文本正文，可空；不得自动重生成。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L138) |


<a id="delivery"></a>

## Delivery

string；none, partial, complete, unknown

<a id="derivedfields"></a>

## DerivedFields

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| severity_group | string；high, medium, low / null | 是 | 可为null | 展示分组：high包含high/critical，medium，low包含info/low；未知null。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L90) |
| false_positive | boolean / null | 可省略 | 可为null | 仅告警：disposition是否恰为false_positive；false不能解读为已确认真实威胁。事件为null。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L90) |
| member_count | integer / null | 可省略 | 可为null | 事件当前成员告警数；告警详情此派生字段不适用为null。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L90) |
| first_activity_at | string date-time / null | 可省略 | 可为null | 事件成员event_time最早值，全部未知则null；告警不适用为null。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L90) |
| last_activity_at | string date-time / null | 可省略 | 可为null | 事件成员event_time最晚值，全部未知则null；告警不适用为null。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L90) |
| unknown_event_time_count | integer / null | 可省略 | 可为null | 事件成员缺event_time的告警数；告警不适用为null。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L90) |
| unknown_severity_count | integer / null | 可省略 | 可为null | 事件成员缺severity的告警数；告警不适用为null。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L90) |
| severity_auto | [Severity](#severity) / null | 可省略 | 可为null | 事件已知成员的最高严重度，无已知等级为null。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L90) |
| severity_effective | [Severity](#severity) / null | 可省略 | 可为null | 事件人工severity_override优先，否则severity_auto。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L90) |
| severity_source | string；manual_override, member_max / null | 可省略 | 可为null | 事件有效严重度来源：manual_override或member_max，两者都没有则null。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L90) |
| updated_at | string date-time / null | 可省略 | 可为null | 当前记录更新时刻；DerivedFields中为事件自身与成员business_updated_at的较晚值。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L90) |
| tactics | array〈[TacticCount](#tacticcount)〉 | 是 | 非null | 当前材料detection.tactics按标签分组统计，计去重告警数；不是模型判定攻击阶段。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L90) |
| tactic_counting_note | string | 是 | 非null | 说明同一告警可计多个阶段，阶段之和可能超过告警总数。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L90) |
| object_count | integer | 是 | 非null | 当前成员材料按namespace/object_type/object_key去重的对象数。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L90) |
| baseline_execution_counts | [BaselineCounts](#baselinecounts) | 是 | 非null | 与当前成员有关联的不同baseline Run数，分别统计running和unknown。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L90) |


<a id="diagnosisstate"></a>

## DiagnosisState

string；running, completed, failed, cancelled, unknown

<a id="diagnosisview"></a>

## DiagnosisView

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string uuid | 是 | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `socai2.incident_diagnoses.id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| source_run_id | string uuid | 是 | 非null | incident_diagnosis执行，同事件 | `socai2.incident_diagnoses.source_run_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| revision | integer | 是 | 非null | 同事件尝试版本 | `socai2.incident_diagnoses.revision`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| state | [DiagnosisState](#diagnosisstate) | 是 | 非null | 生成尝试状态 | `socai2.incident_diagnoses.state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| summary | string / null | 是 | 可为null | 有效概况正文，失败不伪造 | `socai2.incident_diagnoses.summary`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| diagnosis | object / null | 是 | 可为null | 诊断、证据和限制 | `socai2.incident_diagnoses.diagnosis`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| open_questions | array〈object〉 / null | 是 | 可为null | 待核问题 | `socai2.incident_diagnoses.open_questions`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| input_artifact_id | string uuid | 是 | 非null | 冻结成员/分诊/来源材料快照 | `socai2.incident_diagnoses.input_artifact_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| source_fingerprint | string | 是 | 非null | 实际输入指纹 | `socai2.incident_diagnoses.source_fingerprint`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| producer | string | 是 | 非null | 实现和版本 | `socai2.incident_diagnoses.producer`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| requested_at | string date-time | 是 | 非null | 尝试时间 | `socai2.incident_diagnoses.requested_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| generated_at | string date-time / null | 是 | 可为null | 成功时间 | `socai2.incident_diagnoses.generated_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| error_code | string / null | 是 | 可为null | 事件诊断保存的error.code；无错误对象或无code为null，不包含完整底层异常。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L39) |


<a id="disposition"></a>

## Disposition

string；true_positive, false_positive, benign, needs_review

<a id="evidenceentry"></a>

## EvidenceEntry

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| evidence_id | string；maxLength=300；pattern=^[A-Za-z0-9_.-]+:[^\s]+$ | 是 | 非null | 命名空间化的证据条目标识，同一目录唯一。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L48) |
| title | string；minLength=1；maxLength=500；pattern=\S | 是 | 非null | 显示标题；写入必须非空，长度约束见Schema。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L48) |
| type | string；minLength=1；maxLength=500；pattern=\S | 是 | 非null | 本结构的类型判别；EvidenceRef为引用目标类型，EvidenceEntry为证据分类。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L48) |
| alert_ids | array〈string uuid〉；minItems=1；maxItems=200 | 是 | 非null | 真实告警UUID集合，禁止重复；具体是新增、完整替换或反馈覆盖范围见操作说明。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L48) |
| object_keys | array〈[EvidenceObject](#evidenceobject)〉；maxItems=50 | 是 | 非null | 对象键；explicit_objects需非空且属于所选告警当前对象。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L48) |
| source_refs | array〈[SavedReference](#savedreference)〉；minItems=1；maxItems=30 | 是 | 非null | 来源引用；任务写入为type/id，读取为已冻结EvidenceRef，不能把读取对象原样回写。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L48) |
| verdict | string；malicious, suspicious, clean, unknown, conflicting | 是 | 非null | 该对象判定；分诊Disposition和证据目录verdict是两套不同枚举，不能互换。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L48) |
| verdict_sources | array〈[SavedReference](#savedreference)〉；maxItems=30 | 是 | 非null | 支持该证据判定的已保存引用；unknown可为空，conflicting至少两份不同依据。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L48) |
| threat | [Threat](#threat) / null | 是 | 可为null | 可选明确威胁身份及来源，不按证据文本自行生成威胁ID。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L48) |
| remediation | [SavedReference](#savedreference) / null | 是 | 可为null | 可选已保存执行回执引用，role必须execution_receipt；建议不能充当处置成功。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L48) |
| state | string；active, withdrawn | 是 | 非null | 本对象状态；含义依模型枚举，不与交付/业务判定合并。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L48) |


<a id="evidenceindex"></a>

## EvidenceIndex

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| schema_version | string = socai2.case-evidence.v1 | 是 | 非null | 本结构/工件的合同版本；按实际版本解释字段，不把当前模型结构套给历史版本。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L74) |
| scope_revision | integer；minimum=0.0 | 是 | 非null | Case成员范围版本，历史Run保持冻结值。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L74) |
| alert_ids | array〈string uuid〉；maxItems=200 | 是 | 非null | 真实告警UUID集合，禁止重复；具体是新增、完整替换或反馈覆盖范围见操作说明。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L74) |
| supersedes_artifact_id | string uuid / null | 是 | 可为null | 被替换的证据目录工件；首次为null。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L74) |
| availability_state | string；available, partial, unavailable | 是 | 非null | 被发布证据目录的可用状态available/partial/unavailable；partial/unavailable要求限制说明。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L74) |
| limitations | array〈string；minLength=1；maxLength=500；pattern=\S〉；maxItems=30 | 是 | 非null | 本次结果或阅读的限制，原样保留。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L74) |
| entries | array〈[EvidenceEntry](#evidenceentry)〉；maxItems=500 | 是 | 非null | 当前对象条目数组：StagePage为历史尝试，证据模型为目录条目。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L74) |


<a id="evidenceobject"></a>

## EvidenceObject

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| material_id | string uuid | 是 | 非null | 该对象所属的具体告警材料版本ID，与object_key一起定位。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L43) |
| object_key | string；minLength=1；maxLength=500；pattern=\S | 是 | 非null | 带类型/命名空间语义的稳定对象键，不能用展示名称或裸IP替代所有对象身份。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L43) |


<a id="evidenceref"></a>

## EvidenceRef

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| type | string；alert_material, artifact, task_revision, result | 是 | 非null | 本结构的类型判别；EvidenceRef为引用目标类型，EvidenceEntry为证据分类。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L55) |
| id | string uuid | 是 | 非null | 本对象唯一身份；列表导航和关联使用该值，不能使用名称代替。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L55) |
| external | null | 是 | 可为null | 现有EvidenceRef固定null；外部材料需先保存为内部可解析工件。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L55) |
| source_path | string / null | 是 | 可为null | 保存原件内的路径；SavedReference强制以/开头的JSON Pointer；普通EvidenceRef可空。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L55) |
| row_keys | array〈string〉 | 是 | 非null | 普通引用中的行定位键；SavedReference现合同必须为空列表。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L55) |
| role | string；observation, source_label, prior_analysis, human_statement, execution_receipt | 是 | 非null | 来源角色 observation/source_label/prior_analysis/human_statement/execution_receipt；不能相互替代证据。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L55) |


<a id="evidenceview"></a>

## EvidenceView

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| artifact_id | string uuid / null | 是 | 可为null | 工件 UUID，必须保持父主体/Run 归属。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L112) |
| state | string；available, partial, unavailable, not_recorded, invalid_reference | 是 | 非null | 本对象状态；含义依模型枚举，不与交付/业务判定合并。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L112) |
| evidence_count | integer / null | 是 | 可为null | 有效active且所有关联告警仍在本案的证据条目数；未记录/不可用/失效为null。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L112) |
| threat_count | integer / null | 是 | 可为null | 上述有效恶意/可疑证据中明确威胁按namespace/key去重数量；未知为null，0不证明安全。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L112) |
| covered_alert_ids | array〈string uuid〉 | 是 | 非null | 有效证据条目覆盖的当前告警ID。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L112) |
| uncovered_alert_ids | array〈string uuid〉 | 是 | 非null | 当前成员中未被有效证据条目覆盖的告警ID。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L112) |
| excluded_evidence_ids | array〈string〉 | 是 | 非null | 因撤回或范围不再适用等原因不参与当前统计的证据ID。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L112) |
| limitations | array〈string〉 | 是 | 非null | 本次结果或阅读的限制，原样保留。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L112) |
| entries | array〈[EvidenceEntry](#evidenceentry)〉 | 是 | 非null | 当前对象条目数组：StagePage为历史尝试，证据模型为目录条目。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L112) |
| index | [EvidenceIndex](#evidenceindex) / null | 是 | 可为null | 证据目录版本正文，不是自动生成证据的命令。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L112) |


<a id="executionsummary"></a>

## ExecutionSummary

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| artifact_id | string uuid | 是 | 非null | 工件 UUID，必须保持父主体/Run 归属。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L320) |
| availability | string | 是 | 非null | 正文是否可用；200仅代表读取请求成功。available/retained_*/大小限制/外部正文未载入分开展示。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L320) |
| schema_version | string / null | 可省略 | 可为null | 本结构/工件的合同版本；按实际版本解释字段，不把当前模型结构套给历史版本。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L320) |
| capabilities | object / null | 可省略 | 可为null | 该轮计划中记录的工具/能力快照，开放字段由计划版本解释。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L320) |
| limits | object / null | 可省略 | 可为null | 该轮执行计划中的限制快照，不能从Case RunView读取run.limits。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L320) |
| final_reservation | object / null | 可省略 | 可为null | 该轮为最终收尾保留的资源，来自执行计划工件。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L320) |
| limitations | array〈string〉 | 可省略 | 非null | 本次结果或阅读的限制，原样保留。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L320) |


<a id="explanationview"></a>

## ExplanationView

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| artifact_id | string uuid | 是 | 非null | 工件 UUID，必须保持父主体/Run 归属。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L55) |
| available | boolean | 是 | 非null | 此解释/部分结果工件的正文是否完整可读且通过内容完整性检查。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L55) |
| reason | string / null | 是 | 可为null | available=false的读取原因；explanation可能material_*、external_or_missing_content、content_exceeds_read_limit、content_integrity_mismatch；partial_analysis可能external_or_incomplete_content等。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L55) |
| content | object / null | 是 | 可为null | 可用时的已保存结构化正文；不可用时null，按具体工件schema版本解释。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L55) |


<a id="finding"></a>

## Finding

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string | 是 | 非null | 本对象唯一身份；列表导航和关联使用该值，不能使用名称代替。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L89) |
| statement | string | 是 | 非null | 发现正文。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L89) |
| state | string；observed, inferred, unresolved, withdrawn | 是 | 非null | observed原始观察、inferred推断、unresolved未决、withdrawn撤回；保留各自支持/反证/限制。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L89) |
| scope | [Scope](#scope) | 是 | 非null | 本条发现/问题的适用范围；范围声明不等于已证明覆盖。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L89) |
| support | array〈[EvidenceRef](#evidenceref)〉 | 是 | 非null | 支持该发现的来源引用。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L89) |
| counterevidence | array〈[EvidenceRef](#evidenceref)〉 | 是 | 非null | 反证或不支持该发现的来源引用。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L89) |
| limitations | array〈string〉 | 是 | 非null | 本次结果或阅读的限制，原样保留。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L89) |


<a id="httpvalidationerror"></a>

## HTTPValidationError

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| detail | array〈[ValidationError](#validationerror)〉 | 可省略 | 非null | 框架422字段校验错误数组，每项为ValidationError；其他服务抛出的422字符串错误不属于此模型。 | 框架HTTP校验响应 |


<a id="historyentry"></a>

## HistoryEntry

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string | 是 | 非null | 历史目录显示身份，格式run:<uuid>或result:<uuid>；它不是可直接放入Run路径的UUID。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L227) |
| recorded_at | string date-time | 是 | 非null | 历史条目的排序时刻：Run requested_at或已保存AI结果saved_at。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L227) |
| run | [RunView](#runview) | 是 | 非null | 对应的执行记录；嵌套类型或动态结构见下表，不能和正式结果/当前判断混用。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L227) |
| result | [ResultSummary](#resultsummary) / null | 是 | 可为null | 本次读取的结果对象；可空时表示该次执行没有保存对应结果。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L227) |


<a id="historypage"></a>

## HistoryPage

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| items | array〈[HistoryEntry](#historyentry)〉 | 是 | 非null | 本页记录数组；元素类型在本行类型中说明，空数组仅表示此查询页没有记录。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L234) |
| next_cursor | string / null | 是 | 可为null | 下一页游标；null表示结束。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L234) |


<a id="impact"></a>

## Impact

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| summary | string / null | 是 | 可为null | 当前结构的摘要，具体来源由模型/读取装配说明；null保留未形成。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L125) |
| supported_changes | array〈string〉 | 是 | 非null | 本轮有依据支持的案件认识变化。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L125) |
| cannot_generalize | array〈string〉 | 是 | 非null | 本轮不能推及其他成员/范围的限制。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L125) |
| affected_scope | [Scope](#scope) | 是 | 非null | 案件影响的适用范围声明。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L125) |
| next_steps | array〈string〉 | 是 | 非null | 后续建议，不代表已经派发任务或执行动作。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L125) |


<a id="incidentfacts"></a>

## IncidentFacts

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string uuid | 是 | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `socai2.incidents.id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| source_namespace | string | 是 | 非null | Fusion实例/来源命名空间 | `socai2.incidents.source_namespace`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| title | string | 是 | 非null | 事件自身标题 | `socai2.incidents.title`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| description | string / null | 是 | 可为null | 事件自身说明，非第一条成员标题 | `socai2.incidents.description`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| owner_id | string uuid / null | 是 | 可为null | 当前明确负责人 | `socai2.incidents.owner_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| assignment_state | [AssignmentState](#assignmentstate) | 是 | 非null | 未分配/已分配/原值未解析 | `socai2.incidents.assignment_state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| owner_source_value | string / null | 是 | 可为null | 未解析来源负责人 | `socai2.incidents.owner_source_value`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| assigned_at | string date-time / null | 是 | 可为null | 最近改派时间 | `socai2.incidents.assigned_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| tags | array〈string〉 | 是 | 非null | 事件业务标签，成员资产标签另外派生 | `socai2.incidents.tags`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| priority_value | string / null | 是 | 可为null | 已有优先级0..100 | `socai2.incidents.priority_value`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| priority_state | [ScoreState](#scorestate) | 是 | 非null | 无来源不合成 | `socai2.incidents.priority_state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| priority_source | string / null | 是 | 可为null | 已有评分生产者 | `socai2.incidents.priority_source`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| priority_basis | object / null | 是 | 可为null | 评分依据 | `socai2.incidents.priority_basis`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| business_updated_at | string date-time | 是 | 非null | 自身管理或成员关联变动；移除最后成员仍更新 | `socai2.incidents.business_updated_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| reopened_at | string date-time / null | 是 | 可为null | 最近明确重开时间 | `socai2.incidents.reopened_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| row_version | integer | 是 | 非null | 管理/范围写入乐观版本 | `socai2.incidents.row_version`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| source_incident_id | string | 是 | 非null | 来源事件ID，兼容原有文本键 | `socai2.incidents.source_incident_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| handling_status | [WorkStatus](#workstatus) | 是 | 非null | 事件业务处理状态 | `socai2.incidents.handling_status`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| severity_override | [Severity](#severity) / null | 是 | 可为null | 人工事件覆盖等级；NULL=采用成员最高；不改成员 | `socai2.incidents.severity_override`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| severity_override_reason | string / null | 是 | 可为null | 人工覆盖依据 | `socai2.incidents.severity_override_reason`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| severity_override_at | string date-time / null | 是 | 可为null | 覆盖设置时间 | `socai2.incidents.severity_override_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| severity_override_by | string uuid / null | 是 | 可为null | 覆盖人 | `socai2.incidents.severity_override_by`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| resolution_note | string / null | 是 | 可为null | 事件解决说明，人工解决必填 | `socai2.incidents.resolution_note`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| resolved_at | string date-time / null | 是 | 可为null | 当前解决周期时间 | `socai2.incidents.resolved_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| resolved_by | string uuid / null | 是 | 可为null | 解决人 | `socai2.incidents.resolved_by`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| created_at | string date-time | 是 | 非null | 事件首次持久化时间 | `socai2.incidents.created_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| latest_diagnosis_id | string uuid / null | 是 | 可为null | 同事件最新成功诊断；失败尝试不能覆盖 | `socai2.incidents.latest_diagnosis_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |


<a id="movereceipt"></a>

## MoveReceipt

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| source | [MutationReceipt](#mutationreceipt) | 是 | 非null | 源Case变更回执（MoveReceipt）；请求CaseDataUpdate的source另为manual/import。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L127) |
| target | [MutationReceipt](#mutationreceipt) | 是 | 非null | 目标Case变更回执（MoveReceipt）。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L127) |
| moved_alert_ids | array〈string uuid〉 | 是 | 非null | 本次实际从源Case移出的告警UUID。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L127) |
| added_to_target_alert_ids | array〈string uuid〉 | 是 | 非null | 实际新增到目标Case的告警UUID；原已在目标的不会重复新增。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L127) |


<a id="mutationreceipt"></a>

## MutationReceipt

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| case_id | string uuid | 是 | 非null | Case UUID；来自真实回执/列表，不是页面展示编号。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L73) |
| scope_revision | integer | 是 | 非null | Case成员范围版本，历史Run保持冻结值。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L73) |
| pending_run_id | string uuid / null | 是 | 可为null | 准备好的待启动Run；需要用户显式调用start。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L73) |
| changed | boolean | 是 | 非null | 本次写入是否实际改变业务内容；幂等重读不表示重新执行。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L73) |


<a id="origin"></a>

## Origin

string；model, human, system, legacy

<a id="question"></a>

## Question

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string | 是 | 非null | 本对象唯一身份；列表导航和关联使用该值，不能使用名称代替。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L99) |
| text | string | 是 | 非null | 本轮待核问题正文。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L99) |
| scope | [Scope](#scope) | 是 | 非null | 本条发现/问题的适用范围；范围声明不等于已证明覆盖。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L99) |
| evidence_requirements | array〈string〉 | 是 | 非null | 要回答该问题所需的证据说明。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L99) |
| state | string；open, answered, unresolved, not_attempted | 是 | 非null | 本轮问题是否open/answered/unresolved/not_attempted，属于冻结调查内容；不是独立问题管理状态，不增加负责人/关闭/跨轮合并。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L99) |
| answer | string / null | 是 | 可为null | 本轮已有回答，无回答为null。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L99) |
| evidence_refs | array〈[EvidenceRef](#evidenceref)〉 | 是 | 非null | 本轮引用的材料/结果/人工版本，保留原角色与范围。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L99) |
| limitations | array〈string〉 | 是 | 非null | 本次结果或阅读的限制，原样保留。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L99) |


<a id="recommendation"></a>

## Recommendation

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string | 是 | 非null | 本对象唯一身份；列表导航和关联使用该值，不能使用名称代替。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L115) |
| action_type | string | 是 | 非null | 建议动作类型文本，不是执行接口名称。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L115) |
| targets | array〈[Target](#target)〉 | 是 | 非null | 建议针对的对象键和展示名称。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L115) |
| reason | string | 是 | 非null | 服务返回原因；不代表adopt已有reason请求参数。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L115) |
| approval_requirement | string；required, not_required, unknown | 是 | 非null | 该建议记录的审批需求；unknown不代表无需审批，当前没有审批执行接口。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L115) |
| source_refs | array〈[EvidenceRef](#evidenceref)〉 | 是 | 非null | 来源引用；任务写入为type/id，读取为已冻结EvidenceRef，不能把读取对象原样回写。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L115) |
| limitations | array〈string〉 | 是 | 非null | 本次结果或阅读的限制，原样保留。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L115) |


<a id="recordpage"></a>

## RecordPage

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| items | array〈object〉 | 是 | 非null | 本页记录数组；元素类型在本行类型中说明，空数组仅表示此查询页没有记录。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L130) |
| total | integer | 是 | 非null | 当前集合总数；records/assets为对象资产匹配边数。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L130) |
| next_offset | integer / null | 是 | 可为null | 下一页偏移；null表示结束。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L130) |
| observed_at | string date-time | 是 | 非null | 本次读取观察时间。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L130) |
| limitations | array〈string〉 | 是 | 非null | 本次结果或阅读的限制，原样保留。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L130) |


<a id="resultdetail"></a>

## ResultDetail

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| result | [ResultView](#resultview) | 是 | 非null | 本次读取的结果对象；可空时表示该次执行没有保存对应结果。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L365) |
| run | [RunView](#runview) | 是 | 非null | 对应的执行记录；嵌套类型或动态结构见下表，不能和正式结果/当前判断混用。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L365) |
| source_answer | [SavedAnswerReference](#savedanswerreference) / null | 是 | 可为null | ai_saved结果关联的已保存原回答身份；baseline或无源回答为null。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L365) |
| members | array〈object〉 | 是 | 非null | 此对象的成员列表；Case为当前成员，Run/Result为当轮冻结成员，动态字段见专门清单。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L365) |
| member_count | integer | 是 | 非null | 成员总数；超过返回长度时结合members_truncated，不把当前数组长度当全量。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L365) |
| members_truncated | boolean | 是 | 非null | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L365) |
| delivery | object / null | 是 | 可为null | C6交付回执定位信息及细节；没有有效回执为null，有报告不保证有正式Result。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L365) |


<a id="resultkind"></a>

## ResultKind

string；baseline, ai_saved

<a id="resultsummary"></a>

## ResultSummary

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string uuid | 是 | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `socai2.results.id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| case_id | string uuid | 是 | 非null | 案件 | `socai2.results.case_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| kind | [ResultKind](#resultkind) | 是 | 非null | baseline/ai_saved | `socai2.results.kind`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| source_run_id | string uuid | 是 | 非null | 实际来源执行，同Case | `socai2.results.source_run_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| source_answer_id | string uuid / null | 是 | 可为null | AI保存必有，baseline NULL | `socai2.results.source_answer_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| title | string | 是 | 非null | 正式记录标题；AI保存可自定义 | `socai2.results.title`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| purpose | string | 是 | 非null | 本轮目标 | `socai2.results.purpose`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| conclusion | string / null | 是 | 可为null | 有效/不确定结论；无结论NULL | `socai2.results.conclusion`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| conclusion_state | [ConclusionState](#conclusionstate) | 是 | 非null | 有依据/未决/无法给出 | `socai2.results.conclusion_state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| conclusion_origin | [Origin](#origin) | 是 | 非null | 模型/人工/系统来源 | `socai2.results.conclusion_origin`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| validation_state | [Validation](#validation) | 是 | 非null | 程序采用或拒绝状态 | `socai2.results.validation_state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| closing_note | string | 是 | 非null | 每轮收尾说明，系统失败交接也有 | `socai2.results.closing_note`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| comparison_result_id | string uuid / null | 是 | 可为null | 明确同案已有结果；首次NULL | `socai2.results.comparison_result_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| change_kind | [ChangeKind](#changekind) | 是 | 非null | 比较类型 | `socai2.results.change_kind`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| change_summary | string / null | 是 | 可为null | 相比基线输入/证据/判断变化 | `socai2.results.change_summary`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| input_artifact_id | string uuid | 是 | 非null | 实际当时输入 | `socai2.results.input_artifact_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| graph_artifact_id | string uuid / null | 是 | 可为null | 本轮图，无图NULL；不借另一轮冒充 | `socai2.results.graph_artifact_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| report_artifact_id | string uuid / null | 是 | 可为null | 同版报告，无报告NULL | `socai2.results.report_artifact_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| supersedes_result_id | string uuid / null | 是 | 可为null | 明确修订另建版本，不能自指或跨案 | `socai2.results.supersedes_result_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| delivery_state | [Delivery](#delivery) | 是 | 非null | 正式交付完整性 | `socai2.results.delivery_state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| created_at | string date-time | 是 | 非null | 执行产物形成时间 | `socai2.results.created_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| saved_at | string date-time | 是 | 非null | 正式保存时间；AI保存与答复时间不同 | `socai2.results.saved_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| saved_by | string uuid / null | 是 | 可为null | 明确AI保存人；baseline由服务保存 | `socai2.results.saved_by`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| edited_fields | array〈string〉 | 是 | 非null | 保存AI答案时用户改过的字段名；正文修改须origin=human且重新校验；原消息不改 | `socai2.results.edited_fields`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| edit_note | string / null | 是 | 可为null | 可选修改说明，不强制增加页面输入 | `socai2.results.edit_note`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |


<a id="resultview"></a>

## ResultView

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string uuid | 是 | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `socai2.results.id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| case_id | string uuid | 是 | 非null | 案件 | `socai2.results.case_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| kind | [ResultKind](#resultkind) | 是 | 非null | baseline/ai_saved | `socai2.results.kind`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| source_run_id | string uuid | 是 | 非null | 实际来源执行，同Case | `socai2.results.source_run_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| source_answer_id | string uuid / null | 是 | 可为null | AI保存必有，baseline NULL | `socai2.results.source_answer_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| title | string | 是 | 非null | 正式记录标题；AI保存可自定义 | `socai2.results.title`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| purpose | string | 是 | 非null | 本轮目标 | `socai2.results.purpose`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| conclusion | string / null | 是 | 可为null | 有效/不确定结论；无结论NULL | `socai2.results.conclusion`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| conclusion_state | [ConclusionState](#conclusionstate) | 是 | 非null | 有依据/未决/无法给出 | `socai2.results.conclusion_state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| conclusion_origin | [Origin](#origin) | 是 | 非null | 模型/人工/系统来源 | `socai2.results.conclusion_origin`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| validation_state | [Validation](#validation) | 是 | 非null | 程序采用或拒绝状态 | `socai2.results.validation_state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| closing_note | string | 是 | 非null | 每轮收尾说明，系统失败交接也有 | `socai2.results.closing_note`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| comparison_result_id | string uuid / null | 是 | 可为null | 明确同案已有结果；首次NULL | `socai2.results.comparison_result_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| change_kind | [ChangeKind](#changekind) | 是 | 非null | 比较类型 | `socai2.results.change_kind`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| change_summary | string / null | 是 | 可为null | 相比基线输入/证据/判断变化 | `socai2.results.change_summary`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| input_artifact_id | string uuid | 是 | 非null | 实际当时输入 | `socai2.results.input_artifact_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| graph_artifact_id | string uuid / null | 是 | 可为null | 本轮图，无图NULL；不借另一轮冒充 | `socai2.results.graph_artifact_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| report_artifact_id | string uuid / null | 是 | 可为null | 同版报告，无报告NULL | `socai2.results.report_artifact_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| supersedes_result_id | string uuid / null | 是 | 可为null | 明确修订另建版本，不能自指或跨案 | `socai2.results.supersedes_result_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| delivery_state | [Delivery](#delivery) | 是 | 非null | 正式交付完整性 | `socai2.results.delivery_state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| created_at | string date-time | 是 | 非null | 执行产物形成时间 | `socai2.results.created_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| saved_at | string date-time | 是 | 非null | 正式保存时间；AI保存与答复时间不同 | `socai2.results.saved_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| saved_by | string uuid / null | 是 | 可为null | 明确AI保存人；baseline由服务保存 | `socai2.results.saved_by`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| edited_fields | array〈string〉 | 是 | 非null | 保存AI答案时用户改过的字段名；正文修改须origin=human且重新校验；原消息不改 | `socai2.results.edited_fields`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| edit_note | string / null | 是 | 可为null | 可选修改说明，不强制增加页面输入 | `socai2.results.edit_note`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| findings | array〈[Finding](#finding)〉 | 是 | 非null | 稳定条目ID、依据、反证和限制 | `socai2.results.findings`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| questions | array〈[Question](#question)〉 | 是 | 非null | 本轮问题/答案/缺口 | `socai2.results.questions`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| recommendations | array〈[Recommendation](#recommendation)〉 | 是 | 非null | 建议含稳定proposal_id、目标、理由及审批要求 | `socai2.results.recommendations`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| case_impact | [Impact](#impact) | 是 | 非null | 作用范围、可调整认识、不能推广处 | `socai2.results.case_impact`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |


<a id="rundetail"></a>

## RunDetail

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| run | [RunView](#runview) | 是 | 非null | 对应的执行记录；嵌套类型或动态结构见下表，不能和正式结果/当前判断混用。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| result_ids | array〈string uuid〉 | 是 | 非null | 该Run已保存的正式结果UUID，按saved_at/id排序；最多200。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| result_count | integer | 是 | 非null | 该Run正式结果总数。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| results_truncated | boolean | 是 | 非null | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| start_eligibility | [StartAvailability](#startavailability) | 是 | 非null | 是否可启动及原因，依据最新Run与Case范围。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| current_member_count | integer | 是 | 非null | 当前Case成员数量，可能与当轮输入不同。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| input_member_count | integer | 是 | 非null | 该Run冻结的run_members总数。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| members | array〈object〉 | 是 | 非null | 此对象的成员列表；Case为当前成员，Run/Result为当轮冻结成员，动态字段见专门清单。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| members_truncated | boolean | 是 | 非null | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| read_counts | object | 是 | 非null | 以read_state为键统计当轮成员数量。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| analysis_counts | object | 是 | 非null | 以analysis_state为键统计当轮成员数量。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| steps | array〈object〉 | 是 | 非null | 执行步骤目录，按seq组织；Case最多1000，A/I见动态结构限制。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| steps_truncated | boolean | 是 | 非null | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| tool_calls | integer | 是 | 非null | kind=tool且state不为planned/skipped的实际尝试次数，包含失败，不是成功查询数。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| usage | object | 是 | 非null | 按已读步骤及全量模型次数汇总；步骤截断时未读用量计unknown，不声称全量费用。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| artifacts | array〈object〉 | 是 | 非null | 该Run工件元数据目录，正文通过对应工件接口读取。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| artifact_counts | object | 是 | 非null | Case Run按工件kind分组的总数。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| artifacts_truncated | boolean | 是 | 非null | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| duration_seconds | number / null | 是 | 可为null | started_at与ended_at均有值才计算秒数，否则null，不用0代未知。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| elapsed_seconds | number / null | 是 | 可为null | Case Run已开始且未结束时从started_at到observed_at的秒数，否则null。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| last_recorded_at | string date-time | 是 | 非null | 本轮请求/范围变动/开始/结束/步骤时间/工件捕获时间中实际存在的最新时刻，非服务心跳。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| observed_at | string date-time | 是 | 非null | 本次读取观察时间。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |
| execution_summary | [ExecutionSummary](#executionsummary) / null | 可省略 | 可为null | 从C1.executor已保存计划工件读取的能力/限制快照；未找到为null，不用当前配置回填旧Run。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L330) |


<a id="runkind"></a>

## RunKind

string；alert_basic, incident_diagnosis, baseline, ai_question

<a id="runstate"></a>

## RunState

string；pending_update, running, unknown, completed, failed, cancelled

<a id="runtrigger"></a>

## RunTrigger

string；ingested, refresh, case_created, members_changed, manual, question, retry

<a id="runview"></a>

## RunView

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string uuid | 是 | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `socai2.runs.id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| case_id | string uuid | 是 | 非null | baseline/ai_question归属 | `socai2.runs.case_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| kind | [RunKind](#runkind) | 是 | 非null | 四机器流程明确区分 | `socai2.runs.kind`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| title | string | 是 | 非null | 本次执行名称，pending随范围更新 | `socai2.runs.title`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| purpose | string | 是 | 非null | 本轮目标/提问 | `socai2.runs.purpose`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| trigger | [RunTrigger](#runtrigger) | 是 | 非null | 触发原因 | `socai2.runs.trigger`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| scope_revision | integer / null | 是 | 可为null | Case成员版本；非Case NULL | `socai2.runs.scope_revision`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| scope_updated_at | string date-time / null | 是 | 可为null | pending最近合并范围时间 | `socai2.runs.scope_updated_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| scope_kind | string / null | 是 | 可为null | baseline whole_case，AI可选范围；其他流程NULL | `socai2.runs.scope_kind`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| window_start | string date-time / null | 是 | 可为null | 固定绝对查询起点；不适用NULL | `socai2.runs.window_start`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| window_end | string date-time / null | 是 | 可为null | 固定绝对查询终点；成对出现 | `socai2.runs.window_end`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| state | [RunState](#runstate) | 是 | 非null | 记录/执行状态 | `socai2.runs.state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| comparison_result_id | string uuid / null | 是 | 可为null | 领取时固定的同案比较基线，可跨成员范围 | `socai2.runs.comparison_result_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| input_artifact_id | string uuid / null | 是 | 可为null | 领取前NULL；提交running前冻结本地输入 | `socai2.runs.input_artifact_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| executor_version | string / null | 是 | 可为null | 实际执行版本，pending NULL | `socai2.runs.executor_version`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| requested_at | string date-time | 是 | 非null | 记录创建/首次请求 | `socai2.runs.requested_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| requested_by | string uuid / null | 是 | 可为null | 真实请求人 | `socai2.runs.requested_by`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| started_at | string date-time / null | 是 | 可为null | running领取事务时间 | `socai2.runs.started_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| ended_at | string date-time / null | 是 | 可为null | 终态时间；unknown未确认结束NULL | `socai2.runs.ended_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| stop_reason | string / null | 是 | 可为null | 稳定原因码；不强用人类结论代替 | `socai2.runs.stop_reason`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| stop_detail | string / null | 是 | 可为null | 可读原因 | `socai2.runs.stop_detail`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| delivery_state | [Delivery](#delivery) | 是 | 非null | 实际产物交付 | `socai2.runs.delivery_state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| row_version | integer | 是 | 非null | 执行状态条件更新版本 | `socai2.runs.row_version`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |


<a id="savedanswerreference"></a>

## SavedAnswerReference

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string uuid | 是 | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `socai2.messages.id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| conversation_id | string uuid | 是 | 非null | 会话 | `socai2.messages.conversation_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| in_reply_to | string uuid / null | 是 | 可为null | assistant指具体用户问题；同会话 | `socai2.messages.in_reply_to`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| source_run_id | string uuid | 是 | 非null | 真实ai_question执行；用户消息NULL | `socai2.messages.source_run_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| input_artifact_id | string uuid | 是 | 非null | assistant实际输入；不能保存时重新读取 | `socai2.messages.input_artifact_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| answered_at | string date-time | 是 | 非null | 实际回答完成 | `socai2.messages.answered_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |


<a id="savedreference"></a>

## SavedReference

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| type | string；alert_material, artifact, task_revision, result | 是 | 非null | 本结构的类型判别；EvidenceRef为引用目标类型，EvidenceEntry为证据分类。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L24) |
| id | string uuid | 是 | 非null | 本对象唯一身份；列表导航和关联使用该值，不能使用名称代替。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L24) |
| external | null | 是 | 可为null | 现有EvidenceRef固定null；外部材料需先保存为内部可解析工件。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L24) |
| source_path | string；minLength=1；maxLength=2000 | 是 | 非null | 保存原件内的路径；SavedReference强制以/开头的JSON Pointer；普通EvidenceRef可空。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L24) |
| row_keys | array〈string〉；maxItems=0 | 是 | 非null | 普通引用中的行定位键；SavedReference现合同必须为空列表。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L24) |
| role | string；observation, source_label, prior_analysis, human_statement, execution_receipt | 是 | 非null | 来源角色 observation/source_label/prior_analysis/human_statement/execution_receipt；不能相互替代证据。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L24) |


<a id="scope"></a>

## Scope

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| kind | string；whole_case, selected_alerts, explicit_objects | 是 | 非null | 此结构的种类；Subject为alerts/incidents，Stage为alert_basic/incident_diagnosis，Scope为范围种类，枚举不互换。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L36) |
| alert_ids | array〈string uuid〉 | 是 | 非null | 本条结果/人工事实声明覆盖的告警UUID；历史结果按冻结范围解释，不强制变成当前成员。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L36) |
| object_keys | array〈string〉 | 是 | 非null | 范围进一步限定的对象键；explicit_objects必须有键，其他类型可为空。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L36) |
| window_start | string date-time / null | 是 | 可为null | 窗口起点，带时区；和window_end同时提供或同时为空。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L36) |
| window_end | string date-time / null | 是 | 可为null | 窗口终点，带时区且不早于起点。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L36) |
| limitations | array〈string〉 | 是 | 非null | 本次结果或阅读的限制，原样保留。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L36) |


<a id="scorestate"></a>

## ScoreState

string；not_provided, not_computed, disabled, failed, available, legacy_unverified

<a id="severity"></a>

## Severity

string；info, low, medium, high, critical

<a id="stageentry"></a>

## StageEntry

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| run | [StageRunView](#stagerunview) | 是 | 非null | 对应的执行记录；嵌套类型或动态结构见下表，不能和正式结果/当前判断混用。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L62) |
| freshness | string；current, stale, unverified, unavailable | 是 | 非null | 该次运行输入与当前材料/成员/判断的比较：current/stale/unverified/unavailable；不是采用状态。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L62) |
| is_current_pointer | boolean | 是 | 非null | 该结果ID是否正是主体当前指针。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L62) |
| valid_for_current_input | boolean | 是 | 非null | 同时是当前指针、输入current、Run completed，事件还需diagnosis.validation_state=accepted；不代表模型语义正确。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L62) |
| result | [TriageView](#triageview) / [DiagnosisView](#diagnosisview) / null | 是 | 可为null | 本次读取的结果对象；可空时表示该次执行没有保存对应结果。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L62) |
| explanation | [ExplanationView](#explanationview) / null | 是 | 可为null | A分诊的独立解释工件及可用性；I或无解释时null。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L62) |
| partial_analysis | [ExplanationView](#explanationview) / null | 可省略 | 可为null | 该Run最后可识别的模型响应partial_review读取结果；不可用与未记录分开，不作为当前有效判断。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L62) |


<a id="stagepage"></a>

## StagePage

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| subject_id | string uuid | 是 | 非null | 本分析目录对应告警或事件UUID。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L72) |
| kind | string；alert_basic, incident_diagnosis | 是 | 非null | 此结构的种类；Subject为alerts/incidents，Stage为alert_basic/incident_diagnosis，Scope为范围种类，枚举不互换。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L72) |
| current_pointer_id | string uuid / null | 是 | 可为null | 主体latest_triage_id/latest_diagnosis_id；它是分诊/诊断记录ID，不是Run ID。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L72) |
| current | [StageEntry](#stageentry) / null | 是 | 可为null | 指针可核对时的StageEntry，否则null；current_pointer_id是分诊/诊断记录ID。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L72) |
| current_unavailable_reason | string / null | 是 | 可为null | 无当前指针时null；有指针但无法核对来源Run时current_pointer_without_verifiable_run。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L72) |
| entries | array〈[StageEntry](#stageentry)〉 | 是 | 非null | 当前对象条目数组：StagePage为历史尝试，证据模型为目录条目。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L72) |
| next_before_run_id | string uuid / null | 是 | 可为null | 下一页运行游标；null表示结束。 | [stage_read_contracts.py](../../../services/api/app/socai2/stage_read_contracts.py#L72) |


<a id="stagerunview"></a>

## StageRunView

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string uuid | 是 | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `socai2.runs.id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| kind | string；alert_basic, incident_diagnosis | 是 | 非null | 四机器流程明确区分 | `socai2.runs.kind`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| state | [RunState](#runstate) | 是 | 非null | 记录/执行状态 | `socai2.runs.state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| requested_at | string date-time | 是 | 非null | 记录创建/首次请求 | `socai2.runs.requested_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| requested_by | string uuid / null | 是 | 可为null | 真实请求人 | `socai2.runs.requested_by`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| started_at | string date-time / null | 是 | 可为null | running领取事务时间 | `socai2.runs.started_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| ended_at | string date-time / null | 是 | 可为null | 终态时间；unknown未确认结束NULL | `socai2.runs.ended_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| executor_version | string / null | 是 | 可为null | 实际执行版本，pending NULL | `socai2.runs.executor_version`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| input_artifact_id | string uuid / null | 是 | 可为null | 领取前NULL；提交running前冻结本地输入 | `socai2.runs.input_artifact_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| stop_reason | string / null | 是 | 可为null | 稳定原因码；不强用人类结论代替 | `socai2.runs.stop_reason`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| delivery_state | [Delivery](#delivery) | 是 | 非null | 实际产物交付 | `socai2.runs.delivery_state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |


<a id="startavailability"></a>

## StartAvailability

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| can_start | boolean | 是 | 非null | 服务给出的启动资格，不由前端从状态猜测。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L244) |
| reason | string；ready, not_pending, resolved_case, scope_changed, empty_scope, baseline_active | 是 | 非null | 服务返回原因；不代表adopt已有reason请求参数。 | [case_contracts.py](../../../services/api/app/socai2/case_contracts.py#L244) |


<a id="subjectpage"></a>

## SubjectPage

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| kind | string；alerts, incidents | 是 | 非null | 此结构的种类；Subject为alerts/incidents，Stage为alert_basic/incident_diagnosis，Scope为范围种类，枚举不互换。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L121) |
| items | array〈[SubjectView](#subjectview)〉 | 是 | 非null | 本页记录数组；元素类型在本行类型中说明，空数组仅表示此查询页没有记录。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L121) |
| total | integer | 是 | 非null | 租户全部该类主体数，不随列表筛选或分页变化。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L121) |
| next_before_id | string uuid / null | 是 | 可为null | 旧调用的下一页主体UUID；新筛选/排序时为null，应使用next_cursor。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L121) |
| filtered_total | integer；minimum=0 | 是 | 非null | 本次全部筛选命中数，不受游标/页长影响；无筛选时等于total。 | [page_reader.py](../../../services/api/app/socai2/page_reader.py) |
| next_cursor | string / null | 是 | 可为null | 下一页不透明游标；null为末页，改变条件或排序后丢弃旧游标。 | [list_query.py](../../../services/api/app/socai2/list_query.py) |
| overall_stats | object | 是 | 非null | 主体整体统计；按原口径和observed_at展示。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L121) |
| observed_at | string date-time | 是 | 非null | 本次读取观察时间。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L121) |


<a id="subjectview"></a>

## SubjectView

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| kind | string；alerts, incidents | 是 | 非null | 此结构的种类；Subject为alerts/incidents，Stage为alert_basic/incident_diagnosis，Scope为范围种类，枚举不互换。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L108) |
| facts | [AlertFacts](#alertfacts) / [IncidentFacts](#incidentfacts) | 是 | 非null | 该kind主体固定事实字段；告警AlertFacts，事件IncidentFacts。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L108) |
| owner_name | string / null | 是 | 可为null | 从配置的人员目录按同租户owner_id解析出的用户名，无法解析为null。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L108) |
| owner_resolution | string；unassigned, resolved, unresolved | 是 | 非null | unassigned明确未分配，resolved名称已解析，unresolved有来源/负责人但本次未解析。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L108) |
| derived | [DerivedFields](#derivedfields) | 是 | 非null | 服务端计算字段；告警和事件含义、空值分别见DerivedFields。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L108) |
| material | object / null | 是 | 可为null | 告警当前材料元数据，含content_url；事件该值null。正文另读，不含raw_text/raw_json/ocsf_json/enrichment。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L108) |
| triage | object / null | 是 | 可为null | 告警latest_triage_id对应记录及freshness/confidence_percent/run_state/valid_for_current_input派生值，非TriageView同形状。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L108) |
| feedback | object / null | 是 | 可为null | 告警latest_feedback_id对应kind=human_feedback的原始记录；事件或无记录时null。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L108) |
| analysis_url | string | 是 | 非null | 该主体分析目录的相对HTTP路径。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L108) |
| section_urls | object | 是 | 非null | section到相对HTTP路径的映射；members仅事件、incidents仅告警，其余见记录分区。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L108) |


<a id="tacticcount"></a>

## TacticCount

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| label | string | 是 | 非null | 展示标签；TacticCount为原材料战术标签，Threat为威胁标签。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L80) |
| alert_count | integer | 是 | 非null | 含该战术标签的不同告警数。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L80) |


<a id="target"></a>

## Target

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| object_key | string | 是 | 非null | 带类型/命名空间语义的稳定对象键，不能用展示名称或裸IP替代所有对象身份。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L110) |
| display_name | string | 是 | 非null | 对象展示名称，不作为关联键。 | [baseline_contracts.py](../../../services/api/app/socai2/baseline_contracts.py#L110) |


<a id="taskmutation"></a>

## TaskMutation

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| task | [TaskView](#taskview) | 是 | 非null | 本次创建/修订后读取到的完整TaskView。 | [human_task_contracts.py](../../../services/api/app/socai2/human_task_contracts.py#L97) |
| changed | boolean | 是 | 非null | 本次写入是否实际改变业务内容；幂等重读不表示重新执行。 | [human_task_contracts.py](../../../services/api/app/socai2/human_task_contracts.py#L97) |


<a id="taskpage"></a>

## TaskPage

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| items | array〈[TaskView](#taskview)〉 | 是 | 非null | 本页记录数组；元素类型在本行类型中说明，空数组仅表示此查询页没有记录。 | [human_task_contracts.py](../../../services/api/app/socai2/human_task_contracts.py#L102) |
| total | integer | 是 | 非null | 当前集合总数；records/assets为对象资产匹配边数。 | [human_task_contracts.py](../../../services/api/app/socai2/human_task_contracts.py#L102) |
| next_offset | integer / null | 是 | 可为null | 下一页偏移；null表示结束。 | [human_task_contracts.py](../../../services/api/app/socai2/human_task_contracts.py#L102) |


<a id="taskrevisionpage"></a>

## TaskRevisionPage

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| items | array〈[TaskRevisionView](#taskrevisionview)〉 | 是 | 非null | 本页记录数组；元素类型在本行类型中说明，空数组仅表示此查询页没有记录。 | [human_task_contracts.py](../../../services/api/app/socai2/human_task_contracts.py#L108) |
| total | integer | 是 | 非null | 当前集合总数；records/assets为对象资产匹配边数。 | [human_task_contracts.py](../../../services/api/app/socai2/human_task_contracts.py#L108) |
| next_offset | integer / null | 是 | 可为null | 下一页偏移；null表示结束。 | [human_task_contracts.py](../../../services/api/app/socai2/human_task_contracts.py#L108) |


<a id="taskrevisionview"></a>

## TaskRevisionView

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string uuid | 是 | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `socai2.task_revisions.id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| case_id | string uuid | 是 | 非null | 同案FK | `socai2.task_revisions.case_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| task_id | string uuid | 是 | 非null | 事项 | `socai2.task_revisions.task_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| revision | integer | 是 | 非null | 从1开始，每次有效编辑+1 | `socai2.task_revisions.revision`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| title | string | 是 | 非null | 任务事项，非空 | `socai2.task_revisions.title`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| description | string / null | 是 | 可为null | 工作说明 | `socai2.task_revisions.description`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| assignee_id | string uuid / null | 是 | 可为null | 同租户可选负责人，NULL未分配 | `socai2.task_revisions.assignee_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| due_at | string date-time / null | 是 | 可为null | 截止时间，可空 | `socai2.task_revisions.due_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| state | [TaskState](#taskstate) | 是 | 非null | 四种人工状态 | `socai2.task_revisions.state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| result_text | string / null | 是 | 可为null | 事实反馈，completed必填非空 | `socai2.task_revisions.result_text`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| result_scope | [Scope](#scope) / null | 是 | 可为null | 确认范围；完成时须明确，如未知部分写limitations | `socai2.task_revisions.result_scope`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| source_refs | array〈[EvidenceRef](#evidenceref)〉 | 是 | 非null | 读回为完整EvidenceRef（含角色/路径），创建/修订请求仅接收TaskReference的type/id，不能原样回传读对象。 | `socai2.task_revisions.source_refs`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| completed_at | string date-time / null | 是 | 可为null | 本次进入完成状态的真实时间 | `socai2.task_revisions.completed_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| completed_by | string uuid / null | 是 | 可为null | 本次实际完成人，不是assignee | `socai2.task_revisions.completed_by`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| changed_at | string date-time | 是 | 非null | 版本编辑时间 | `socai2.task_revisions.changed_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| changed_by | string uuid | 是 | 非null | 实际编辑人 | `socai2.task_revisions.changed_by`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |


<a id="taskstate"></a>

## TaskState

string；not_started, in_progress, completed, cancelled

<a id="taskview"></a>

## TaskView

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string uuid | 是 | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `socai2.tasks.id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| case_id | string uuid | 是 | 非null | 所属Case | `socai2.tasks.case_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| current_revision_id | string uuid | 是 | 非null | 当前完整版本；延迟FK同事务插入 | `socai2.tasks.current_revision_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| origin_result_id | string uuid / null | 是 | 可为null | 同Case引出事项的结果 | `socai2.tasks.origin_result_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| origin_finding_id | string / null | 是 | 可为null | 该结果findings中的稳定条目ID | `socai2.tasks.origin_finding_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| created_at | string date-time | 是 | 非null | 任务创建 | `socai2.tasks.created_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| created_by | string uuid / null | 是 | 可为null | 创建者 | `socai2.tasks.created_by`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| updated_at | string date-time | 是 | 非null | 最新实际编辑 | `socai2.tasks.updated_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| row_version | integer | 是 | 非null | 防旧表单覆盖 | `socai2.tasks.row_version`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| current | [TaskRevisionView](#taskrevisionview) | 是 | 非null | current_revision_id指向的完整当前修订对象；该HTTP结构为必返且不可空。 | [human_task_contracts.py](../../../services/api/app/socai2/human_task_contracts.py#L84) |


<a id="threat"></a>

## Threat

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| namespace | string；minLength=1；maxLength=500；pattern=\S | 是 | 非null | 身份命名空间；不同来源的同名键不得合并。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L36) |
| key | string；minLength=1；maxLength=500；pattern=\S | 是 | 非null | 该命名空间内稳定威胁键。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L36) |
| label | string；minLength=1；maxLength=500；pattern=\S | 是 | 非null | 展示标签；TacticCount为原材料战术标签，Threat为威胁标签。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L36) |
| source_refs | array〈[SavedReference](#savedreference)〉；minItems=1；maxItems=20 | 是 | 非null | 来源引用；任务写入为type/id，读取为已冻结EvidenceRef，不能把读取对象原样回写。 | [case_data_contracts.py](../../../services/api/app/socai2/case_data_contracts.py#L36) |


<a id="timesource"></a>

## TimeSource

string；source, derived_source, unknown

<a id="traceview"></a>

## TraceView

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| run | object | 是 | 非null | A/I实际Run行的公开字段，包括主体身份与limits；不同于精简StageRunView，见动态字段。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L145) |
| steps | array〈object〉 | 是 | 非null | 执行步骤目录，按seq组织；Case最多1000，A/I见动态结构限制。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L145) |
| steps_total | integer | 是 | 非null | 该A/I Run全部步骤数量，不限返回目录长度。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L145) |
| steps_truncated | boolean | 是 | 非null | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L145) |
| artifacts | array〈object〉 | 是 | 非null | 该Run工件元数据目录，正文通过对应工件接口读取。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L145) |
| artifacts_total | integer | 是 | 非null | 该A/I Run全部工件数量。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L145) |
| artifacts_truncated | boolean | 是 | 非null | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L145) |
| usage | object | 是 | 非null | 读取该Run所有模型步骤汇总，与steps目录是否截断无关。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L145) |
| tool_calls | integer | 是 | 非null | kind=tool且state不为planned/skipped的实际尝试次数，包含失败，不是成功查询数。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L145) |
| duration_seconds | number / null | 是 | 可为null | started_at与ended_at均有值才计算秒数，否则null，不用0代未知。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L145) |
| last_recorded_at | string date-time | 是 | 非null | 本轮请求/范围变动/开始/结束/步骤时间/工件捕获时间中实际存在的最新时刻，非服务心跳。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L145) |
| observed_at | string date-time | 是 | 非null | 本次读取观察时间。 | [page_contracts.py](../../../services/api/app/socai2/page_contracts.py#L145) |


<a id="triageview"></a>

## TriageView

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string uuid | 是 | 非null | 该记录的应用UUID，不是页面展示编号或厂商编号。 | `socai2.alert_assessments.id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| input_material_id | string uuid / null | 是 | 可为null | 判断依据的材料版；旧未知NULL | `socai2.alert_assessments.input_material_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| source_run_id | string uuid / null | 是 | 可为null | 新alert_basic执行；与此告警一致 | `socai2.alert_assessments.source_run_id`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| verdict | [Disposition](#disposition) / null | 是 | 可为null | 同次判定 | `socai2.alert_assessments.verdict`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| rationale | string / null | 是 | 可为null | 同次理由，历史缺失NULL | `socai2.alert_assessments.rationale`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| confidence | number / null | 是 | 可为null | 该分诊记录0..1置信度，score_state=available才作有效数值；SubjectView.triage.confidence_percent已乘100。 | `socai2.alert_assessments.confidence`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| score_state | [ScoreState](#scorestate) | 是 | 非null | 计算状态 | `socai2.alert_assessments.score_state`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| recommendations | array〈object〉 / null | 是 | 可为null | 同次建议，不与新人工判断拼接 | `socai2.alert_assessments.recommendations`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| producer | string | 是 | 非null | 生产者及版本 | `socai2.alert_assessments.producer`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| actor | object | 是 | 非null | 实际操作者/服务身份 | `socai2.alert_assessments.actor`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |
| assessed_at | string date-time | 是 | 非null | 判断发生时间 | `socai2.alert_assessments.assessed_at`；[既有字段语义](../../../docs/design/socai2-data-contract-current.json) |


<a id="validation"></a>

## Validation

string；not_checked, accepted, rejected, system_only, legacy_unverified

<a id="validationerror"></a>

## ValidationError

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| loc | array〈string / integer〉 | 是 | 非null | 校验错误的位置路径，如body/字段名或path/参数。 | 框架HTTP校验响应 |
| msg | string | 是 | 非null | 字段校验错误说明。 | 框架HTTP校验响应 |
| type | string | 是 | 非null | 本结构的类型判别；EvidenceRef为引用目标类型，EvidenceEntry为证据分类。 | 框架HTTP校验响应 |
| input | any | 可省略 | 非null | 触发字段校验的输入值（框架可能省略）。 | 框架HTTP校验响应 |
| ctx | object | 可省略 | 非null | 字段校验的附加上下文（框架可能省略）。 | 框架HTTP校验响应 |


<a id="workstatus"></a>

## WorkStatus

string；new, in_progress, resolved, unknown


## CaseBlockingRun

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| id | string | 必填 | 非null | 阻止结案的本案Run ID。 | `services/api/app/socai2/case_management_contracts.py`、`case_management.py` |
| state | string running,unknown | 必填 | 非null | running正在执行；unknown执行结果未明确，两者均阻止结案。 | `services/api/app/socai2/case_management_contracts.py`、`case_management.py` |


## CaseManagementView

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| case | CaseView | 必填 | 非null | 当前已保存的Case管理字段和行版本，与Case详情一致。 | `services/api/app/socai2/case_management_contracts.py`、`case_management.py` |
| open_task_count | integer | 必填 | 非null | 当前修订为not_started/in_progress的人工任务数；历史版本不重复计数。 | `services/api/app/socai2/case_management_contracts.py`、`case_management.py` |
| blocking_runs | array | 必填 | 非null | 本案running/unknown Run；空列表表示没有执行状态阻塞，不表示没有待办。 | `services/api/app/socai2/case_management_contracts.py`、`case_management.py` |
| can_close | boolean | 必填 | 非null | 案件未结案且无阻塞Run；如requires_open_task_confirmation为true仍须确认及理由。 | `services/api/app/socai2/case_management_contracts.py`、`case_management.py` |
| can_reopen | boolean | 必填 | 非null | 当前案件是否已解决，可由人显式重开。 | `services/api/app/socai2/case_management_contracts.py`、`case_management.py` |
| requires_open_task_confirmation | boolean | 必填 | 非null | 未结案且存在未完人工任务；关闭请求须确认并提供理由。 | `services/api/app/socai2/case_management_contracts.py`、`case_management.py` |


## CaseManagementReceipt

| 输出字段 | 类型/枚举/限制 | required | 空值 | 业务含义与取值规则 | 语义/实现来源 |
| --- | --- | --- | --- | --- | --- |
| case | CaseView | 必填 | 非null | 本次操作保存后的Case快照；幂等重放返回原回执，新状态请重新GET。 | `services/api/app/socai2/case_management_contracts.py`、`case_management.py` |
| changed | boolean | 必填 | 非null | 是否实际改变Case字段；false不增加行版本，幂等重放保留原回执。 | `services/api/app/socai2/case_management_contracts.py`、`case_management.py` |


## SubjectMutationReceipt

| 输出字段 | 类型 | 必填 | 空值 | 含义 | 来源 |
| --- | --- | --- | --- | --- | --- |
| kind | string | 是 | 非null | alerts或incidents，表示被修改的主体种类 | subject_management_contracts.py |
| facts | AlertFacts / IncidentFacts | 是 | 非null | 提交时保存的完整事实快照，沿用原字段；重放原快照，最新值另GET | subject_management_contracts.py |
| changed | boolean | 是 | 非null | 该次是否改变主体，人工反馈新增记录为true | subject_management_contracts.py |
| feedback_id | UUID | 是 | 可为null | 人工反馈记录ID；普通管理为null | subject_management_contracts.py |
| activity_id | UUID | 是 | 非null | 本操作活动ID，可从主体records/activities读取 | subject_management_contracts.py |

## SubjectBatchReceipt

| 输出字段 | 类型 | 必填 | 空值 | 含义 | 来源 |
| --- | --- | --- | --- | --- | --- |
| operation_key | UUID | 是 | 非null | 本次逻辑批量操作键；同意图重放返回同回执 | subject_management_contracts.py |
| items | SubjectMutationReceipt[] | 是 | 非null | 按主体UUID排序的逐项结果，整批成功或拒绝 | subject_management_contracts.py |
| changed_count | integer | 是 | 非null | items中changed=true的个数，不是模型调用数 | subject_management_contracts.py |
