# HTTP字段与嵌套类型

按实际JSON类型保留required、可空、枚举和限制。请求额外字段禁止；服务输出可空字段不能擅自补0/空串。动态正文见[原JSON合同](json-contracts.json)，不要将任意工件统一套成一种业务结论。

<a id="aiunavailable"></a>

## AIUnavailable



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| detail | 否 | [AIUnavailableDetail](schemas.md#aiunavailabledetail) | 无（可空不等于可省略） | 此501响应固定为AIUnavailableDetail对象（code/status/message），不是字符串或数组。 [完整语义](/handoff/audit/response-fields.html#aiunavailable) |


<a id="aiunavailabledetail"></a>

## AIUnavailableDetail



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| code | 否 | string = case_ai_not_implemented | "case_ai_not_implemented" | 机器可识别的错误码；AI预留固定case_ai_not_implemented。 [完整语义](/handoff/audit/response-fields.html#aiunavailabledetail) |
| status | 否 | string = not_implemented | "not_implemented" | AI预留固定not_implemented；不表示业务执行状态。 [完整语义](/handoff/audit/response-fields.html#aiunavailabledetail) |
| message | 否 | string | "AI问答功能暂未实现；本次请求未执行、保存或采用任何结果。" | 面向接手人的错误说明文本。 [完整语义](/handoff/audit/response-fields.html#aiunavailabledetail) |


<a id="adoptcaseairesult"></a>

## AdoptCaseAIResult



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_scope_revision | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 读 Case 详情获得的当前范围版本；不匹配返回409。 |


<a id="alertfacts"></a>

## AlertFacts



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | 该记录的应用UUID，不是页面展示编号或厂商编号。 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| source_namespace | 是 | string | 无（可空不等于可省略） | 来源系统命名空间，不是原厂名称 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| title | 是 | string | 无（可空不等于可省略） | 接收到的标题；未知来源用显式缺失显示，不编造内容 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| description | 是 | string / null | 无（可空不等于可省略） | 来源说明；人工补充用评论 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| owner_id | 是 | string (uuid) / null | 无（可空不等于可省略） | public.users.id [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| assignment_state | 是 | [AssignmentState](schemas.md#assignmentstate) | 无（可空不等于可省略） | 分配状态 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| owner_source_value | 是 | string / null | 无（可空不等于可省略） | unresolved时原负责人值 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| assigned_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 最近分配操作时间 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| tags | 是 | array <string> | 无（可空不等于可省略） | 业务标签；资产标签从库存读取 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| priority_value | 是 | string / null | 无（可空不等于可省略） | 已有优先级0到100，不以分诊分数填充 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| priority_state | 是 | [ScoreState](schemas.md#scorestate) | 无（可空不等于可省略） | 优先级评分状态 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| priority_source | 是 | string / null | 无（可空不等于可省略） | 评分生产者/模型版本 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| priority_basis | 是 | object / null | 无（可空不等于可省略） | 评分来源依据；无值不造理由 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| business_updated_at | 是 | string (date-time) | 无（可空不等于可省略） | 实际业务字段变更时间；GET不更新 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| reopened_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 最近明确重开时间 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| row_version | 是 | integer | 无（可空不等于可省略） | 管理乐观锁；每次实际写入+1 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| source_alert_id | 是 | string / null | 无（可空不等于可省略） | 接入来源编号；允许非UUID [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| vendor_alert_id | 是 | string / null | 无（可空不等于可省略） | 厂商原始告警编号；与接入编号分开 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| connector_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 已有连接器引用，同租户校验 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| connector_type | 是 | string / null | 无（可空不等于可省略） | 接入类型原值，不代替original_vendor [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| original_vendor | 是 | string / null | 无（可空不等于可省略） | 明确原厂，未知NULL [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| category | 是 | string / null | 无（可空不等于可省略） | 来源类别，不拿判定替代 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| severity | 是 | [Severity](schemas.md#severity) / null | 无（可空不等于可省略） | 当前来源严重程度 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| severity_raw | 是 | string / null | 无（可空不等于可省略） | 未映射来源等级原文 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| event_time | 是 | string (date-time) / null | 无（可空不等于可省略） | 真实发生时间 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| event_time_source | 是 | [TimeSource](schemas.md#timesource) | 无（可空不等于可省略） | 发生时间依据 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| first_seen_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 已收到材料中首次活动时间 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| last_seen_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 已收到材料中末次活动时间 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| ingested_at | 是 | string (date-time) | 无（可空不等于可省略） | 首次接收时间 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| source_updated_at | 是 | string (date-time) | 无（可空不等于可省略） | 本地保存新材料的时间 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| handling_status | 是 | [AlertStatus](schemas.md#alertstatus) | 无（可空不等于可省略） | 业务处理状态 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| disposition | 是 | [Disposition](schemas.md#disposition) / null | 无（可空不等于可省略） | 当前采用判定；与latest反馈或分诊配套 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| closed_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 当前完成周期关闭时间；重开后置空，旧值在活动中 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| closed_by | 是 | string (uuid) / null | 无（可空不等于可省略） | 明确用户关闭人；自动关闭记录活动服务身份 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| latest_material_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 同告警最新有效材料 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| latest_triage_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 同告警kind=triage记录 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| latest_feedback_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 同告警kind=human_feedback记录 [完整语义](/handoff/audit/response-fields.html#alertfacts) |
| latest_explanation_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 同告警kind=alert_explanation的有效Explain材料；GET不生成并写业务时钟 [完整语义](/handoff/audit/response-fields.html#alertfacts) |


<a id="alertstatus"></a>

## AlertStatus



string new, in_progress, completed, unknown

<a id="artifactcontent"></a>

## ArtifactContent



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| artifact | 是 | object | 无（可空不等于可省略） | Case工件元数据，和A/I的metadata字段不同。 [完整语义](/handoff/audit/dynamic-fields.html#artifact-metadata) |
| content_json | 是 | object / null | 无（可空不等于可省略） | 保存的结构化正文；格式由工件schema_version和实际类型决定。 [完整语义](/handoff/audit/response-fields.html#artifactcontent) |
| content_text | 是 | string / null | 无（可空不等于可省略） | 保存的文本正文，可空；不得自动重生成。 [完整语义](/handoff/audit/response-fields.html#artifactcontent) |
| availability | 是 | string | 无（可空不等于可省略） | Case工件读取状态；内容hash/size不一致直接409 artifact_integrity_invalid，不返回成功正文。 [完整语义](/handoff/audit/response-fields.html#artifactcontent) |


<a id="askcaseai"></a>

## AskCaseAI



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| question | 是 | string; minLength=1; maxLength=4000 | 无（可空不等于可省略） | 用户明确发送的问题文本；当前Q接口未实现。 |
| conversation_id | 否 | string (uuid) / null | 无（可空不等于可省略） | 可选会话UUID；当前无正式对话读写。 |


<a id="assessmentpageview"></a>

## AssessmentPageView



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | 该记录的应用UUID，不是页面展示编号或厂商编号。 [完整语义](/handoff/audit/response-fields.html#assessmentpageview) |
| conclusion | 是 | string | 无（可空不等于可省略） | 明确采用的判断 [完整语义](/handoff/audit/response-fields.html#assessmentpageview) |
| origin | 是 | string model, human, system, legacy | 无（可空不等于可省略） | model/human/legacy，system交接不得采用为有效结论 [完整语义](/handoff/audit/response-fields.html#assessmentpageview) |
| validity | 是 | string | 无（可空不等于可省略） | 采用时有效性；不代表绝对事实证明 [完整语义](/handoff/audit/response-fields.html#assessmentpageview) |
| scope_revision | 是 | integer | 无（可空不等于可省略） | 采用时Case范围版本 [完整语义](/handoff/audit/response-fields.html#assessmentpageview) |
| formed_at | 是 | string (date-time) | 无（可空不等于可省略） | 判断形成时间 [完整语义](/handoff/audit/response-fields.html#assessmentpageview) |
| adopted_at | 是 | string (date-time) | 无（可空不等于可省略） | 采用时间 [完整语义](/handoff/audit/response-fields.html#assessmentpageview) |
| alert_ids | 是 | array <string (uuid)> | 无（可空不等于可省略） | 真实告警UUID集合，禁止重复；具体是新增、完整替换或反馈覆盖范围见操作说明。 [完整语义](/handoff/audit/response-fields.html#assessmentpageview) |
| sources | 是 | array <object> | 无（可空不等于可省略） | 该已采用判断的来源行；page_data版本保留tenant_id，CaseDetail.current_assessment版本剔除内部字段。 [完整语义](/handoff/audit/response-fields.html#assessmentpageview) |


<a id="assignmentstate"></a>

## AssignmentState



string unassigned, assigned, unresolved

<a id="associationreceipt"></a>

## AssociationReceipt



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| case_id | 是 | string (uuid) | 无（可空不等于可省略） | Case UUID；来自真实回执/列表，不是页面展示编号。 [完整语义](/handoff/audit/response-fields.html#associationreceipt) |
| scope_revision | 是 | integer | 无（可空不等于可省略） | Case成员范围版本，历史Run保持冻结值。 [完整语义](/handoff/audit/response-fields.html#associationreceipt) |
| pending_run_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 准备好的待启动Run；需要用户显式调用start。 [完整语义](/handoff/audit/response-fields.html#associationreceipt) |
| changed | 是 | boolean | 无（可空不等于可省略） | 本次写入是否实际改变业务内容；幂等重读不表示重新执行。 [完整语义](/handoff/audit/response-fields.html#associationreceipt) |
| added_alert_ids | 否 | array <string (uuid)> | 无（可空不等于可省略） | 本次实际新增Case成员UUID。 [完整语义](/handoff/audit/response-fields.html#associationreceipt) |
| linked_incident_ids | 否 | array <string (uuid)> | 无（可空不等于可省略） | 本次新增的显式事件关系UUID。 [完整语义](/handoff/audit/response-fields.html#associationreceipt) |


<a id="associationrequest"></a>

## AssociationRequest



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_scope_revision | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 读 Case 详情获得的当前范围版本；不匹配返回409。 |
| alert_ids | 否 | array <string (uuid)>; maxItems=200 | 无（可空不等于可省略） | 真实告警UUID集合，禁止重复；具体是新增、完整替换或反馈覆盖范围见操作说明。 |
| incident_ids | 否 | array <string (uuid)>; maxItems=200 | 无（可空不等于可省略） | 显式关联事件UUID集合，服务展开成员。 |


<a id="baselinecounts"></a>

## BaselineCounts



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| running | 是 | integer | 无（可空不等于可省略） | 运行中基础Run数量。 [完整语义](/handoff/audit/response-fields.html#baselinecounts) |
| unknown | 是 | integer | 无（可空不等于可省略） | 执行状态未确认的基础Run数量，仍占活跃约束。 [完整语义](/handoff/audit/response-fields.html#baselinecounts) |


<a id="baselinepreparation"></a>

## BaselinePreparation



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| case_id | 是 | string (uuid) | 无（可空不等于可省略） | Case UUID；来自真实回执/列表，不是页面展示编号。 [完整语义](/handoff/audit/response-fields.html#baselinepreparation) |
| scope_revision | 是 | integer | 无（可空不等于可省略） | Case成员范围版本，历史Run保持冻结值。 [完整语义](/handoff/audit/response-fields.html#baselinepreparation) |
| pending_run_id | 是 | string (uuid) | 无（可空不等于可省略） | 准备好的待启动Run；需要用户显式调用start。 [完整语义](/handoff/audit/response-fields.html#baselinepreparation) |
| created | 是 | boolean | 无（可空不等于可省略） | 是否本次新建pending记录；false可能复用已有待启动项。 [完整语义](/handoff/audit/response-fields.html#baselinepreparation) |


<a id="casebaselinerecord"></a>

## CaseBaselineRecord



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| run | 是 | [RunView](schemas.md#runview) | 无（可空不等于可省略） | 对应的执行记录；嵌套类型或动态结构见下表，不能和正式结果/当前判断混用。 [完整语义](/handoff/audit/response-fields.html#casebaselinerecord) |
| start_eligibility | 是 | [StartAvailability](schemas.md#startavailability) | 无（可空不等于可省略） | 是否可启动及原因，依据最新Run与Case范围。 [完整语义](/handoff/audit/response-fields.html#casebaselinerecord) |


<a id="casecreate"></a>

## CaseCreate



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| title | 是 | string; minLength=1; maxLength=200 | 无（可空不等于可省略） | 显示标题；写入必须非空，长度约束见Schema。 |
| description | 否 | string; maxLength=20000 / null | 无（可空不等于可省略） | 补充说明，可空；不是程序生成结论。 |
| severity | 否 | [Severity](schemas.md#severity) / null | 无（可空不等于可省略） | 严重度枚举；null为未知，不强行补默认等级。 |
| tags | 否 | array <string; minLength=1; maxLength=128>; maxItems=50 | 无（可空不等于可省略） | 标签列表，不替代资产标签。 |
| alert_ids | 否 | array <string (uuid)>; maxItems=200 | 无（可空不等于可省略） | 真实告警UUID集合，禁止重复；具体是新增、完整替换或反馈覆盖范围见操作说明。 |
| incident_ids | 否 | array <string (uuid)>; maxItems=200 | 无（可空不等于可省略） | 显式关联事件UUID集合，服务展开成员。 |


<a id="casedatareceipt"></a>

## CaseDataReceipt



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| case_id | 是 | string (uuid) | 无（可空不等于可省略） | Case UUID；来自真实回执/列表，不是页面展示编号。 [完整语义](/handoff/audit/response-fields.html#casedatareceipt) |
| row_version | 是 | integer | 无（可空不等于可省略） | 并发修改版本；后续写入的expected_row_version取此值。 [完整语义](/handoff/audit/response-fields.html#casedatareceipt) |
| changed | 是 | boolean | 无（可空不等于可省略） | 是否改变资料/目录；返回回执后刷新最新row_version，幂等重放不生成新版本。 [完整语义](/handoff/audit/response-fields.html#casedatareceipt) |
| current_evidence_artifact_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 本次保存后当前证据目录工件UUID；未有目录为null。 [完整语义](/handoff/audit/response-fields.html#casedatareceipt) |


<a id="casedataupdate"></a>

## CaseDataUpdate



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_row_version | 是 | integer; minimum=1.0 | 无（可空不等于可省略） | 读当前 Case/Task 获得的行版本；不匹配返回409。 |
| classification | 是 | string true_positive, informational, false_positive / null | 无（可空不等于可省略） | 案件分类true_positive/informational/false_positive；null未设置；队列可用not_set过滤未设置。 |
| due_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 带时区的截止时间；null清空。 |
| source | 是 | string manual, import | 无（可空不等于可省略） | 本次资料变更来源 manual 或 import。 |
| source_note | 是 | string; minLength=1; maxLength=500; pattern=\S | 无（可空不等于可省略） | 资料修改原因/来源说明，非空。 |


<a id="casedetail"></a>

## CaseDetail



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| case | 是 | [CaseView](schemas.md#caseview) | 无（可空不等于可省略） | 当前案件主体资料，不是执行记录。 [完整语义](/handoff/audit/response-fields.html#casedetail) |
| members | 是 | array <object> | 无（可空不等于可省略） | 此对象的成员列表；Case为当前成员，Run/Result为当轮冻结成员，动态字段见专门清单。 [完整语义](/handoff/audit/dynamic-fields.html#case-members) |
| member_count | 是 | integer | 无（可空不等于可省略） | 成员总数；超过返回长度时结合members_truncated，不把当前数组长度当全量。 [完整语义](/handoff/audit/response-fields.html#casedetail) |
| members_truncated | 是 | boolean | 无（可空不等于可省略） | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 [完整语义](/handoff/audit/response-fields.html#casedetail) |
| linked_incidents | 是 | array <object> | 无（可空不等于可省略） | Case显式关联事件，不包含仅共享成员而无显式关系的事件。 [完整语义](/handoff/audit/dynamic-fields.html#case-linked-incidents) |
| linked_incident_count | 是 | integer | 无（可空不等于可省略） | 本案显式事件关系总数。 [完整语义](/handoff/audit/response-fields.html#casedetail) |
| linked_incidents_truncated | 是 | boolean | 无（可空不等于可省略） | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 [完整语义](/handoff/audit/response-fields.html#casedetail) |
| current_assessment | 是 | object / null | 无（可空不等于可省略） | 当前采用判断及来源/覆盖；null表示未形成，不能自行采用最近结果。 [完整语义](/handoff/audit/dynamic-fields.html#current-assessment) |
| baseline_records | 是 | array <object> | 无（可空不等于可省略） | 本案pending_update/running/unknown基础Run及资格；已结束历史另读history。 [完整语义](/handoff/audit/response-fields.html#casedetail) |
| page_data | 否 | [CasePageData](schemas.md#casepagedata) / null | 无（可空不等于可省略） | 本案分类/期限/当前判断和证据目录投影。 [完整语义](/handoff/audit/response-fields.html#casedetail) |


<a id="casepagedata"></a>

## CasePageData



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| schema_version | 否 | string = socai2.case-page-data.v1 | "socai2.case-page-data.v1" | 本结构/工件的合同版本；按实际版本解释字段，不把当前模型结构套给历史版本。 [完整语义](/handoff/audit/response-fields.html#casepagedata) |
| classification | 是 | string true_positive, informational, false_positive / null | 无（可空不等于可省略） | 案件分类true_positive/informational/false_positive；null未设置；队列可用not_set过滤未设置。 [完整语义](/handoff/audit/response-fields.html#casepagedata) |
| due_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 带时区的截止时间；null清空。 [完整语义](/handoff/audit/response-fields.html#casepagedata) |
| determination | 是 | string / null | 无（可空不等于可省略） | 沿Case.current_assessment_id取得的已采用conclusion；没有指针为null，不取最新Result补。 [完整语义](/handoff/audit/response-fields.html#casepagedata) |
| assessment | 是 | [AssessmentPageView](schemas.md#assessmentpageview) / null | 无（可空不等于可省略） | 已采用判断的页面投影。 [完整语义](/handoff/audit/response-fields.html#casepagedata) |
| evidence | 是 | [EvidenceView](schemas.md#evidenceview) | 无（可空不等于可省略） | 已发布证据目录及可用状态。 [完整语义](/handoff/audit/response-fields.html#casepagedata) |


<a id="casequeueitem"></a>

## CaseQueueItem



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| case | 是 | [CaseView](schemas.md#caseview) | 无（可空不等于可省略） | 当前案件主体资料，不是执行记录。 [完整语义](/handoff/audit/response-fields.html#casequeueitem) |
| member_count | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 成员总数；超过返回长度时结合members_truncated，不把当前数组长度当全量。 [完整语义](/handoff/audit/response-fields.html#casequeueitem) |
| open_task_count | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 本案not_started或in_progress人工任务数，questions不计入。 [完整语义](/handoff/audit/response-fields.html#casequeueitem) |
| baseline_records | 是 | array <[CaseBaselineRecord](schemas.md#casebaselinerecord)> | 无（可空不等于可省略） | 本案pending_update/running/unknown基础Run及资格；已结束历史另读history。 [完整语义](/handoff/audit/response-fields.html#casequeueitem) |
| page_data | 否 | [CasePageData](schemas.md#casepagedata) / null | 无（可空不等于可省略） | 本案分类/期限/当前判断和证据目录投影。 [完整语义](/handoff/audit/response-fields.html#casequeueitem) |


<a id="casequeuemetrics"></a>

## CaseQueueMetrics



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| awaiting_assignment | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | handling_status为new/in_progress，且assignment_state=unassigned、owner_id=null的Case数；已解决/未知状态与unresolved分配不计。 [完整语义](/handoff/audit/response-fields.html#casequeuemetrics) |
| in_progress | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 处理状态为in_progress的Case数；不是运行中的Run数。 [完整语义](/handoff/audit/response-fields.html#casequeuemetrics) |
| high_severity | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | handling_status为new/in_progress且severity=high的Case数；不含critical，也不含resolved/unknown。 [完整语义](/handoff/audit/response-fields.html#casequeuemetrics) |
| awaiting_human | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | handling_status为new/in_progress且至少有一个当前修订为not_started/in_progress人工任务的Case数；不是任务条数。 [完整语义](/handoff/audit/response-fields.html#casequeuemetrics) |


<a id="casequeuepage"></a>

## CaseQueuePage



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | 是 | array <[CaseQueueItem](schemas.md#casequeueitem)> | 无（可空不等于可省略） | 本页记录数组；元素类型在本行类型中说明，空数组仅表示此查询页没有记录。 [完整语义](/handoff/audit/response-fields.html#casequeuepage) |
| total | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 当前集合总数；records/assets为对象资产匹配边数。 [完整语义](/handoff/audit/response-fields.html#casequeuepage) |
| next_cursor | 是 | string / null | 无（可空不等于可省略） | 下一页游标；null表示结束。 [完整语义](/handoff/audit/response-fields.html#casequeuepage) |
| metrics | 是 | [CaseQueueMetrics](schemas.md#casequeuemetrics) | 无（可空不等于可省略） | Case租户整体指标，不随分页或筛选total变化。 [完整语义](/handoff/audit/response-fields.html#casequeuepage) |


<a id="caseview"></a>

## CaseView



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | 该记录的应用UUID，不是页面展示编号或厂商编号。 [完整语义](/handoff/audit/response-fields.html#caseview) |
| source_namespace | 是 | string / null | 无（可空不等于可省略） | Case固定数据身份命名空间；首次范围绑定后不可改，旧范围不能确认时NULL；不等于原始来源环境 [完整语义](/handoff/audit/response-fields.html#caseview) |
| title | 是 | string | 无（可空不等于可省略） | 名称 [完整语义](/handoff/audit/response-fields.html#caseview) |
| description | 是 | string / null | 无（可空不等于可省略） | 案情说明 [完整语义](/handoff/audit/response-fields.html#caseview) |
| handling_status | 是 | [WorkStatus](schemas.md#workstatus) | 无（可空不等于可省略） | 业务状态 [完整语义](/handoff/audit/response-fields.html#caseview) |
| severity | 是 | [Severity](schemas.md#severity) / null | 无（可空不等于可省略） | 当前明确案件等级 [完整语义](/handoff/audit/response-fields.html#caseview) |
| severity_source | 是 | string / null | 无（可空不等于可省略） | 手动设置或明确汇总规则，不从置信度猜 [完整语义](/handoff/audit/response-fields.html#caseview) |
| owner_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 当前负责人 [完整语义](/handoff/audit/response-fields.html#caseview) |
| assignment_state | 是 | [AssignmentState](schemas.md#assignmentstate) | 无（可空不等于可省略） | 分配状态 [完整语义](/handoff/audit/response-fields.html#caseview) |
| owner_source_value | 是 | string / null | 无（可空不等于可省略） | 历史未解析负责人 [完整语义](/handoff/audit/response-fields.html#caseview) |
| assigned_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 最近分配时间 [完整语义](/handoff/audit/response-fields.html#caseview) |
| tags | 是 | array <string> | 无（可空不等于可省略） | 案件标签 [完整语义](/handoff/audit/response-fields.html#caseview) |
| priority_value | 是 | string / null | 无（可空不等于可省略） | 已有优先级 [完整语义](/handoff/audit/response-fields.html#caseview) |
| priority_state | 是 | [ScoreState](schemas.md#scorestate) | 无（可空不等于可省略） | 评分状态 [完整语义](/handoff/audit/response-fields.html#caseview) |
| priority_source | 是 | string / null | 无（可空不等于可省略） | 评分生产者 [完整语义](/handoff/audit/response-fields.html#caseview) |
| priority_basis | 是 | object / null | 无（可空不等于可省略） | 已有依据 [完整语义](/handoff/audit/response-fields.html#caseview) |
| scope_revision | 是 | integer | 无（可空不等于可省略） | 仅当前告警成员真实变动+1 [完整语义](/handoff/audit/response-fields.html#caseview) |
| current_assessment_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 已明确采用版本；不等于最新Run [完整语义](/handoff/audit/response-fields.html#caseview) |
| classification | 否 | string true_positive, informational, false_positive / null | 无（可空不等于可省略） | 明确保存的案件管理分类；NULL未设置，不继承事件或告警 [完整语义](/handoff/audit/response-fields.html#caseview) |
| due_at | 否 | string (date-time) / null | 无（可空不等于可省略） | 案件截止时间，与任务期限和运行超时分离 [完整语义](/handoff/audit/response-fields.html#caseview) |
| current_evidence_artifact_id | 否 | string (uuid) / null | 无（可空不等于可省略） | 同租户同Case的当前case_evidence_index不可变工件；NULL未记录 [完整语义](/handoff/audit/response-fields.html#caseview) |
| created_at | 是 | string (date-time) | 无（可空不等于可省略） | 创建时间 [完整语义](/handoff/audit/response-fields.html#caseview) |
| created_by | 是 | string (uuid) / null | 无（可空不等于可省略） | 创建人，服务创建见活动 [完整语义](/handoff/audit/response-fields.html#caseview) |
| business_updated_at | 是 | string (date-time) | 无（可空不等于可省略） | 案件业务变化 [完整语义](/handoff/audit/response-fields.html#caseview) |
| resolved_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 当前解决周期时间 [完整语义](/handoff/audit/response-fields.html#caseview) |
| resolved_by | 是 | string (uuid) / null | 无（可空不等于可省略） | 明确解决人 [完整语义](/handoff/audit/response-fields.html#caseview) |
| resolution_note | 是 | string / null | 无（可空不等于可省略） | 解决说明，不擅自添加必填要求 [完整语义](/handoff/audit/response-fields.html#caseview) |
| reopened_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 最近重开 [完整语义](/handoff/audit/response-fields.html#caseview) |
| row_version | 是 | integer | 无（可空不等于可省略） | 乐观版本 [完整语义](/handoff/audit/response-fields.html#caseview) |


<a id="changekind"></a>

## ChangeKind



string initial, unchanged, expanded, revised, withdrawn, not_comparable

<a id="conclusionstate"></a>

## ConclusionState



string supported, uncertain, unavailable

<a id="contentview"></a>

## ContentView



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| metadata | 是 | object | 无（可空不等于可省略） | A/I工件/材料元数据。 [完整语义](/handoff/audit/response-fields.html#contentview) |
| availability | 是 | string | 无（可空不等于可省略） | A/I读取状态；工件hash/size不一致仍HTTP200但availability=content_integrity_mismatch且正文null。材料正文使用独立大小限制状态。 [完整语义](/handoff/audit/response-fields.html#contentview) |
| content_json | 否 | object | 无（可空不等于可省略） | 保存的结构化正文；格式由工件schema_version和实际类型决定。 [完整语义](/handoff/audit/response-fields.html#contentview) |
| content_text | 否 | string / null | 无（可空不等于可省略） | 保存的文本正文，可空；不得自动重生成。 [完整语义](/handoff/audit/response-fields.html#contentview) |


<a id="delivery"></a>

## Delivery



string none, partial, complete, unknown

<a id="derivedfields"></a>

## DerivedFields



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| severity_group | 是 | string high, medium, low / null | 无（可空不等于可省略） | 展示分组：high包含high/critical，medium，low包含info/low；未知null。 [完整语义](/handoff/audit/response-fields.html#derivedfields) |
| false_positive | 否 | boolean / null | 无（可空不等于可省略） | 仅告警：disposition是否恰为false_positive；false不能解读为已确认真实威胁。事件为null。 [完整语义](/handoff/audit/response-fields.html#derivedfields) |
| member_count | 否 | integer / null | 无（可空不等于可省略） | 事件当前成员告警数；告警详情此派生字段不适用为null。 [完整语义](/handoff/audit/response-fields.html#derivedfields) |
| first_activity_at | 否 | string (date-time) / null | 无（可空不等于可省略） | 事件成员event_time最早值，全部未知则null；告警不适用为null。 [完整语义](/handoff/audit/response-fields.html#derivedfields) |
| last_activity_at | 否 | string (date-time) / null | 无（可空不等于可省略） | 事件成员event_time最晚值，全部未知则null；告警不适用为null。 [完整语义](/handoff/audit/response-fields.html#derivedfields) |
| unknown_event_time_count | 否 | integer / null | 无（可空不等于可省略） | 事件成员缺event_time的告警数；告警不适用为null。 [完整语义](/handoff/audit/response-fields.html#derivedfields) |
| unknown_severity_count | 否 | integer / null | 无（可空不等于可省略） | 事件成员缺severity的告警数；告警不适用为null。 [完整语义](/handoff/audit/response-fields.html#derivedfields) |
| severity_auto | 否 | [Severity](schemas.md#severity) / null | 无（可空不等于可省略） | 事件已知成员的最高严重度，无已知等级为null。 [完整语义](/handoff/audit/response-fields.html#derivedfields) |
| severity_effective | 否 | [Severity](schemas.md#severity) / null | 无（可空不等于可省略） | 事件人工severity_override优先，否则severity_auto。 [完整语义](/handoff/audit/response-fields.html#derivedfields) |
| severity_source | 否 | string manual_override, member_max / null | 无（可空不等于可省略） | 事件有效严重度来源：manual_override或member_max，两者都没有则null。 [完整语义](/handoff/audit/response-fields.html#derivedfields) |
| updated_at | 否 | string (date-time) / null | 无（可空不等于可省略） | 当前记录更新时刻；DerivedFields中为事件自身与成员business_updated_at的较晚值。 [完整语义](/handoff/audit/response-fields.html#derivedfields) |
| tactics | 是 | array <[TacticCount](schemas.md#tacticcount)> | 无（可空不等于可省略） | 当前材料detection.tactics按标签分组统计，计去重告警数；不是模型判定攻击阶段。 [完整语义](/handoff/audit/response-fields.html#derivedfields) |
| tactic_counting_note | 是 | string | 无（可空不等于可省略） | 说明同一告警可计多个阶段，阶段之和可能超过告警总数。 [完整语义](/handoff/audit/response-fields.html#derivedfields) |
| object_count | 是 | integer | 无（可空不等于可省略） | 当前成员材料按namespace/object_type/object_key去重的对象数。 [完整语义](/handoff/audit/response-fields.html#derivedfields) |
| baseline_execution_counts | 是 | [BaselineCounts](schemas.md#baselinecounts) | 无（可空不等于可省略） | 与当前成员有关联的不同baseline Run数，分别统计running和unknown。 [完整语义](/handoff/audit/response-fields.html#derivedfields) |


<a id="diagnosisstate"></a>

## DiagnosisState



string running, completed, failed, cancelled, unknown

<a id="diagnosisview"></a>

## DiagnosisView



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | 该记录的应用UUID，不是页面展示编号或厂商编号。 [完整语义](/handoff/audit/response-fields.html#diagnosisview) |
| source_run_id | 是 | string (uuid) | 无（可空不等于可省略） | incident_diagnosis执行，同事件 [完整语义](/handoff/audit/response-fields.html#diagnosisview) |
| revision | 是 | integer | 无（可空不等于可省略） | 同事件尝试版本 [完整语义](/handoff/audit/response-fields.html#diagnosisview) |
| state | 是 | [DiagnosisState](schemas.md#diagnosisstate) | 无（可空不等于可省略） | 生成尝试状态 [完整语义](/handoff/audit/response-fields.html#diagnosisview) |
| summary | 是 | string / null | 无（可空不等于可省略） | 有效概况正文，失败不伪造 [完整语义](/handoff/audit/response-fields.html#diagnosisview) |
| diagnosis | 是 | object / null | 无（可空不等于可省略） | 诊断、证据和限制 [完整语义](/handoff/audit/response-fields.html#diagnosisview) |
| open_questions | 是 | array <object> / null | 无（可空不等于可省略） | 待核问题 [完整语义](/handoff/audit/response-fields.html#diagnosisview) |
| input_artifact_id | 是 | string (uuid) | 无（可空不等于可省略） | 冻结成员/分诊/来源材料快照 [完整语义](/handoff/audit/response-fields.html#diagnosisview) |
| source_fingerprint | 是 | string | 无（可空不等于可省略） | 实际输入指纹 [完整语义](/handoff/audit/response-fields.html#diagnosisview) |
| producer | 是 | string | 无（可空不等于可省略） | 实现和版本 [完整语义](/handoff/audit/response-fields.html#diagnosisview) |
| requested_at | 是 | string (date-time) | 无（可空不等于可省略） | 尝试时间 [完整语义](/handoff/audit/response-fields.html#diagnosisview) |
| generated_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 成功时间 [完整语义](/handoff/audit/response-fields.html#diagnosisview) |
| error_code | 是 | string / null | 无（可空不等于可省略） | 事件诊断保存的error.code；无错误对象或无code为null，不包含完整底层异常。 [完整语义](/handoff/audit/response-fields.html#diagnosisview) |


<a id="disposition"></a>

## Disposition



string true_positive, false_positive, benign, needs_review

<a id="evidenceentry"></a>

## EvidenceEntry



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| evidence_id | 是 | string; maxLength=300; pattern=^[A-Za-z0-9_.-]+:[^\s]+$ | 无（可空不等于可省略） | 命名空间化的证据条目标识，同一目录唯一。 [完整语义](/handoff/audit/response-fields.html#evidenceentry) |
| title | 是 | string; minLength=1; maxLength=500; pattern=\S | 无（可空不等于可省略） | 显示标题；写入必须非空，长度约束见Schema。 [完整语义](/handoff/audit/response-fields.html#evidenceentry) |
| type | 是 | string; minLength=1; maxLength=500; pattern=\S | 无（可空不等于可省略） | 本结构的类型判别；EvidenceRef为引用目标类型，EvidenceEntry为证据分类。 [完整语义](/handoff/audit/response-fields.html#evidenceentry) |
| alert_ids | 是 | array <string (uuid)>; minItems=1; maxItems=200 | 无（可空不等于可省略） | 真实告警UUID集合，禁止重复；具体是新增、完整替换或反馈覆盖范围见操作说明。 [完整语义](/handoff/audit/response-fields.html#evidenceentry) |
| object_keys | 是 | array <[EvidenceObject](schemas.md#evidenceobject)>; maxItems=50 | 无（可空不等于可省略） | 对象键；explicit_objects需非空且属于所选告警当前对象。 [完整语义](/handoff/audit/response-fields.html#evidenceentry) |
| source_refs | 是 | array <[SavedReference](schemas.md#savedreference)>; minItems=1; maxItems=30 | 无（可空不等于可省略） | 来源引用；任务写入为type/id，读取为已冻结EvidenceRef，不能把读取对象原样回写。 [完整语义](/handoff/audit/response-fields.html#evidenceentry) |
| verdict | 是 | string malicious, suspicious, clean, unknown, conflicting | 无（可空不等于可省略） | 该对象判定；分诊Disposition和证据目录verdict是两套不同枚举，不能互换。 [完整语义](/handoff/audit/response-fields.html#evidenceentry) |
| verdict_sources | 是 | array <[SavedReference](schemas.md#savedreference)>; maxItems=30 | 无（可空不等于可省略） | 支持该证据判定的已保存引用；unknown可为空，conflicting至少两份不同依据。 [完整语义](/handoff/audit/response-fields.html#evidenceentry) |
| threat | 是 | [Threat](schemas.md#threat) / null | 无（可空不等于可省略） | 可选明确威胁身份及来源，不按证据文本自行生成威胁ID。 [完整语义](/handoff/audit/response-fields.html#evidenceentry) |
| remediation | 是 | [SavedReference](schemas.md#savedreference) / null | 无（可空不等于可省略） | 可选已保存执行回执引用，role必须execution_receipt；建议不能充当处置成功。 [完整语义](/handoff/audit/response-fields.html#evidenceentry) |
| state | 是 | string active, withdrawn | 无（可空不等于可省略） | 本对象状态；含义依模型枚举，不与交付/业务判定合并。 [完整语义](/handoff/audit/response-fields.html#evidenceentry) |


<a id="evidenceindex"></a>

## EvidenceIndex



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| schema_version | 是 | string = socai2.case-evidence.v1 | 无（可空不等于可省略） | 本结构/工件的合同版本；按实际版本解释字段，不把当前模型结构套给历史版本。 [完整语义](/handoff/audit/response-fields.html#evidenceindex) |
| scope_revision | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | Case成员范围版本，历史Run保持冻结值。 [完整语义](/handoff/audit/response-fields.html#evidenceindex) |
| alert_ids | 是 | array <string (uuid)>; maxItems=200 | 无（可空不等于可省略） | 真实告警UUID集合，禁止重复；具体是新增、完整替换或反馈覆盖范围见操作说明。 [完整语义](/handoff/audit/response-fields.html#evidenceindex) |
| supersedes_artifact_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 被替换的证据目录工件；首次为null。 [完整语义](/handoff/audit/response-fields.html#evidenceindex) |
| availability_state | 是 | string available, partial, unavailable | 无（可空不等于可省略） | 被发布证据目录的可用状态available/partial/unavailable；partial/unavailable要求限制说明。 [完整语义](/handoff/audit/response-fields.html#evidenceindex) |
| limitations | 是 | array <string; minLength=1; maxLength=500; pattern=\S>; maxItems=30 | 无（可空不等于可省略） | 本次结果或阅读的限制，原样保留。 [完整语义](/handoff/audit/response-fields.html#evidenceindex) |
| entries | 是 | array <[EvidenceEntry](schemas.md#evidenceentry)>; maxItems=500 | 无（可空不等于可省略） | 当前对象条目数组：StagePage为历史尝试，证据模型为目录条目。 [完整语义](/handoff/audit/response-fields.html#evidenceindex) |


<a id="evidenceobject"></a>

## EvidenceObject



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| material_id | 是 | string (uuid) | 无（可空不等于可省略） | 该对象所属的具体告警材料版本ID，与object_key一起定位。 [完整语义](/handoff/audit/response-fields.html#evidenceobject) |
| object_key | 是 | string; minLength=1; maxLength=500; pattern=\S | 无（可空不等于可省略） | 带类型/命名空间语义的稳定对象键，不能用展示名称或裸IP替代所有对象身份。 [完整语义](/handoff/audit/response-fields.html#evidenceobject) |


<a id="evidencepublish"></a>

## EvidencePublish



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_row_version | 是 | integer; minimum=1.0 | 无（可空不等于可省略） | 读当前 Case/Task 获得的行版本；不匹配返回409。 |
| expected_current_artifact_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 当前证据目录工件 ID；首次为null。必须显式传入，和实际旧版本比较。 |
| index | 是 | [EvidenceIndex](schemas.md#evidenceindex) | 无（可空不等于可省略） | 证据目录版本正文，不是自动生成证据的命令。 |


<a id="evidenceref"></a>

## EvidenceRef



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| type | 是 | string alert_material, artifact, task_revision, result | 无（可空不等于可省略） | 本结构的类型判别；EvidenceRef为引用目标类型，EvidenceEntry为证据分类。 [完整语义](/handoff/audit/response-fields.html#evidenceref) |
| id | 是 | string (uuid) | 无（可空不等于可省略） | 本对象唯一身份；列表导航和关联使用该值，不能使用名称代替。 [完整语义](/handoff/audit/response-fields.html#evidenceref) |
| external | 是 | null | 无（可空不等于可省略） | 现有EvidenceRef固定null；外部材料需先保存为内部可解析工件。 [完整语义](/handoff/audit/response-fields.html#evidenceref) |
| source_path | 是 | string / null | 无（可空不等于可省略） | 保存原件内的路径；SavedReference强制以/开头的JSON Pointer；普通EvidenceRef可空。 [完整语义](/handoff/audit/response-fields.html#evidenceref) |
| row_keys | 是 | array <string> | 无（可空不等于可省略） | 普通引用中的行定位键；SavedReference现合同必须为空列表。 [完整语义](/handoff/audit/response-fields.html#evidenceref) |
| role | 是 | string observation, source_label, prior_analysis, human_statement, execution_receipt | 无（可空不等于可省略） | 来源角色 observation/source_label/prior_analysis/human_statement/execution_receipt；不能相互替代证据。 [完整语义](/handoff/audit/response-fields.html#evidenceref) |


<a id="evidenceview"></a>

## EvidenceView



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| artifact_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 工件 UUID，必须保持父主体/Run 归属。 [完整语义](/handoff/audit/response-fields.html#evidenceview) |
| state | 是 | string available, partial, unavailable, not_recorded, invalid_reference | 无（可空不等于可省略） | 本对象状态；含义依模型枚举，不与交付/业务判定合并。 [完整语义](/handoff/audit/response-fields.html#evidenceview) |
| evidence_count | 是 | integer / null | 无（可空不等于可省略） | 有效active且所有关联告警仍在本案的证据条目数；未记录/不可用/失效为null。 [完整语义](/handoff/audit/response-fields.html#evidenceview) |
| threat_count | 是 | integer / null | 无（可空不等于可省略） | 上述有效恶意/可疑证据中明确威胁按namespace/key去重数量；未知为null，0不证明安全。 [完整语义](/handoff/audit/response-fields.html#evidenceview) |
| covered_alert_ids | 是 | array <string (uuid)> | 无（可空不等于可省略） | 有效证据条目覆盖的当前告警ID。 [完整语义](/handoff/audit/response-fields.html#evidenceview) |
| uncovered_alert_ids | 是 | array <string (uuid)> | 无（可空不等于可省略） | 当前成员中未被有效证据条目覆盖的告警ID。 [完整语义](/handoff/audit/response-fields.html#evidenceview) |
| excluded_evidence_ids | 是 | array <string> | 无（可空不等于可省略） | 因撤回或范围不再适用等原因不参与当前统计的证据ID。 [完整语义](/handoff/audit/response-fields.html#evidenceview) |
| limitations | 是 | array <string> | 无（可空不等于可省略） | 本次结果或阅读的限制，原样保留。 [完整语义](/handoff/audit/response-fields.html#evidenceview) |
| entries | 是 | array <[EvidenceEntry](schemas.md#evidenceentry)> | 无（可空不等于可省略） | 当前对象条目数组：StagePage为历史尝试，证据模型为目录条目。 [完整语义](/handoff/audit/response-fields.html#evidenceview) |
| index | 是 | [EvidenceIndex](schemas.md#evidenceindex) / null | 无（可空不等于可省略） | 证据目录版本正文，不是自动生成证据的命令。 [完整语义](/handoff/audit/response-fields.html#evidenceview) |


<a id="executestage"></a>

## ExecuteStage



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |


<a id="executionsummary"></a>

## ExecutionSummary



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| artifact_id | 是 | string (uuid) | 无（可空不等于可省略） | 工件 UUID，必须保持父主体/Run 归属。 [完整语义](/handoff/audit/response-fields.html#executionsummary) |
| availability | 是 | string | 无（可空不等于可省略） | 正文是否可用；200仅代表读取请求成功。available/retained_*/大小限制/外部正文未载入分开展示。 [完整语义](/handoff/audit/response-fields.html#executionsummary) |
| schema_version | 否 | string / null | 无（可空不等于可省略） | 本结构/工件的合同版本；按实际版本解释字段，不把当前模型结构套给历史版本。 [完整语义](/handoff/audit/response-fields.html#executionsummary) |
| capabilities | 否 | object / null | 无（可空不等于可省略） | 该轮计划中记录的工具/能力快照，开放字段由计划版本解释。 [完整语义](/handoff/audit/response-fields.html#executionsummary) |
| limits | 否 | object / null | 无（可空不等于可省略） | 该轮执行计划中的限制快照，不能从Case RunView读取run.limits。 [完整语义](/handoff/audit/response-fields.html#executionsummary) |
| final_reservation | 否 | object / null | 无（可空不等于可省略） | 该轮为最终收尾保留的资源，来自执行计划工件。 [完整语义](/handoff/audit/response-fields.html#executionsummary) |
| limitations | 否 | array <string> | 无（可空不等于可省略） | 本次结果或阅读的限制，原样保留。 [完整语义](/handoff/audit/response-fields.html#executionsummary) |


<a id="explanationview"></a>

## ExplanationView



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| artifact_id | 是 | string (uuid) | 无（可空不等于可省略） | 工件 UUID，必须保持父主体/Run 归属。 [完整语义](/handoff/audit/response-fields.html#explanationview) |
| available | 是 | boolean | 无（可空不等于可省略） | 此解释/部分结果工件的正文是否完整可读且通过内容完整性检查。 [完整语义](/handoff/audit/response-fields.html#explanationview) |
| reason | 是 | string / null | 无（可空不等于可省略） | available=false的读取原因；explanation可能material_*、external_or_missing_content、content_exceeds_read_limit、content_integrity_mismatch；partial_analysis可能external_or_incomplete_content等。 [完整语义](/handoff/audit/response-fields.html#explanationview) |
| content | 是 | object / null | 无（可空不等于可省略） | 可用时的已保存结构化正文；不可用时null，按具体工件schema版本解释。 [完整语义](/handoff/audit/response-fields.html#explanationview) |


<a id="finding"></a>

## Finding



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string | 无（可空不等于可省略） | 本对象唯一身份；列表导航和关联使用该值，不能使用名称代替。 [完整语义](/handoff/audit/response-fields.html#finding) |
| statement | 是 | string | 无（可空不等于可省略） | 发现正文。 [完整语义](/handoff/audit/response-fields.html#finding) |
| state | 是 | string observed, inferred, unresolved, withdrawn | 无（可空不等于可省略） | observed原始观察、inferred推断、unresolved未决、withdrawn撤回；保留各自支持/反证/限制。 [完整语义](/handoff/audit/response-fields.html#finding) |
| scope | 是 | [Scope](schemas.md#scope) | 无（可空不等于可省略） | 本条发现/问题的适用范围；范围声明不等于已证明覆盖。 [完整语义](/handoff/audit/response-fields.html#finding) |
| support | 是 | array <[EvidenceRef](schemas.md#evidenceref)> | 无（可空不等于可省略） | 支持该发现的来源引用。 [完整语义](/handoff/audit/response-fields.html#finding) |
| counterevidence | 是 | array <[EvidenceRef](schemas.md#evidenceref)> | 无（可空不等于可省略） | 反证或不支持该发现的来源引用。 [完整语义](/handoff/audit/response-fields.html#finding) |
| limitations | 是 | array <string> | 无（可空不等于可省略） | 本次结果或阅读的限制，原样保留。 [完整语义](/handoff/audit/response-fields.html#finding) |


<a id="httpvalidationerror"></a>

## HTTPValidationError



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| detail | 否 | array <[ValidationError](schemas.md#validationerror)> | 无（可空不等于可省略） | 框架422字段校验错误数组，每项为ValidationError；其他服务抛出的422字符串错误不属于此模型。 [完整语义](/handoff/audit/response-fields.html#httpvalidationerror) |


<a id="historyentry"></a>

## HistoryEntry



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string | 无（可空不等于可省略） | 历史目录显示身份，格式run:<uuid>或result:<uuid>；它不是可直接放入Run路径的UUID。 [完整语义](/handoff/audit/response-fields.html#historyentry) |
| recorded_at | 是 | string (date-time) | 无（可空不等于可省略） | 历史条目的排序时刻：Run requested_at或已保存AI结果saved_at。 [完整语义](/handoff/audit/response-fields.html#historyentry) |
| run | 是 | [RunView](schemas.md#runview) | 无（可空不等于可省略） | 对应的执行记录；嵌套类型或动态结构见下表，不能和正式结果/当前判断混用。 [完整语义](/handoff/audit/response-fields.html#historyentry) |
| result | 是 | [ResultSummary](schemas.md#resultsummary) / null | 无（可空不等于可省略） | 本次读取的结果对象；可空时表示该次执行没有保存对应结果。 [完整语义](/handoff/audit/response-fields.html#historyentry) |


<a id="historypage"></a>

## HistoryPage



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | 是 | array <[HistoryEntry](schemas.md#historyentry)> | 无（可空不等于可省略） | 本页记录数组；元素类型在本行类型中说明，空数组仅表示此查询页没有记录。 [完整语义](/handoff/audit/response-fields.html#historypage) |
| next_cursor | 是 | string / null | 无（可空不等于可省略） | 下一页游标；null表示结束。 [完整语义](/handoff/audit/response-fields.html#historypage) |


<a id="impact"></a>

## Impact



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| summary | 是 | string / null | 无（可空不等于可省略） | 当前结构的摘要，具体来源由模型/读取装配说明；null保留未形成。 [完整语义](/handoff/audit/response-fields.html#impact) |
| supported_changes | 是 | array <string> | 无（可空不等于可省略） | 本轮有依据支持的案件认识变化。 [完整语义](/handoff/audit/response-fields.html#impact) |
| cannot_generalize | 是 | array <string> | 无（可空不等于可省略） | 本轮不能推及其他成员/范围的限制。 [完整语义](/handoff/audit/response-fields.html#impact) |
| affected_scope | 是 | [Scope](schemas.md#scope) | 无（可空不等于可省略） | 案件影响的适用范围声明。 [完整语义](/handoff/audit/response-fields.html#impact) |
| next_steps | 是 | array <string> | 无（可空不等于可省略） | 后续建议，不代表已经派发任务或执行动作。 [完整语义](/handoff/audit/response-fields.html#impact) |


<a id="incidentfacts"></a>

## IncidentFacts



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | 该记录的应用UUID，不是页面展示编号或厂商编号。 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| source_namespace | 是 | string | 无（可空不等于可省略） | Fusion实例/来源命名空间 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| title | 是 | string | 无（可空不等于可省略） | 事件自身标题 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| description | 是 | string / null | 无（可空不等于可省略） | 事件自身说明，非第一条成员标题 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| owner_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 当前明确负责人 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| assignment_state | 是 | [AssignmentState](schemas.md#assignmentstate) | 无（可空不等于可省略） | 未分配/已分配/原值未解析 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| owner_source_value | 是 | string / null | 无（可空不等于可省略） | 未解析来源负责人 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| assigned_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 最近改派时间 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| tags | 是 | array <string> | 无（可空不等于可省略） | 事件业务标签，成员资产标签另外派生 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| priority_value | 是 | string / null | 无（可空不等于可省略） | 已有优先级0..100 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| priority_state | 是 | [ScoreState](schemas.md#scorestate) | 无（可空不等于可省略） | 无来源不合成 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| priority_source | 是 | string / null | 无（可空不等于可省略） | 已有评分生产者 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| priority_basis | 是 | object / null | 无（可空不等于可省略） | 评分依据 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| business_updated_at | 是 | string (date-time) | 无（可空不等于可省略） | 自身管理或成员关联变动；移除最后成员仍更新 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| reopened_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 最近明确重开时间 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| row_version | 是 | integer | 无（可空不等于可省略） | 管理/范围写入乐观版本 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| source_incident_id | 是 | string | 无（可空不等于可省略） | 来源事件ID，兼容原有文本键 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| handling_status | 是 | [WorkStatus](schemas.md#workstatus) | 无（可空不等于可省略） | 事件业务处理状态 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| severity_override | 是 | [Severity](schemas.md#severity) / null | 无（可空不等于可省略） | 人工事件覆盖等级；NULL=采用成员最高；不改成员 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| severity_override_reason | 是 | string / null | 无（可空不等于可省略） | 人工覆盖依据 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| severity_override_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 覆盖设置时间 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| severity_override_by | 是 | string (uuid) / null | 无（可空不等于可省略） | 覆盖人 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| resolution_note | 是 | string / null | 无（可空不等于可省略） | 事件解决说明，人工解决必填 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| resolved_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 当前解决周期时间 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| resolved_by | 是 | string (uuid) / null | 无（可空不等于可省略） | 解决人 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| created_at | 是 | string (date-time) | 无（可空不等于可省略） | 事件首次持久化时间 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |
| latest_diagnosis_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 同事件最新成功诊断；失败尝试不能覆盖 [完整语义](/handoff/audit/response-fields.html#incidentfacts) |


<a id="memberchange"></a>

## MemberChange



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_scope_revision | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 读 Case 详情获得的当前范围版本；不匹配返回409。 |
| alert_ids | 是 | array <string (uuid)>; maxItems=200 | 无（可空不等于可省略） | 真实告警UUID集合，禁止重复；具体是新增、完整替换或反馈覆盖范围见操作说明。 |


<a id="movemembers"></a>

## MoveMembers



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| target_case_id | 是 | string (uuid) | 无（可空不等于可省略） | 移动目标Case；不得等于路径源Case。 |
| expected_source_scope_revision | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 源 Case 当前范围版本。 |
| expected_target_scope_revision | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 目标 Case 当前范围版本。 |
| alert_ids | 是 | array <string (uuid)>; minItems=1; maxItems=200 | 无（可空不等于可省略） | 真实告警UUID集合，禁止重复；具体是新增、完整替换或反馈覆盖范围见操作说明。 |


<a id="movereceipt"></a>

## MoveReceipt



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| source | 是 | [MutationReceipt](schemas.md#mutationreceipt) | 无（可空不等于可省略） | 源Case变更回执（MoveReceipt）；请求CaseDataUpdate的source另为manual/import。 [完整语义](/handoff/audit/response-fields.html#movereceipt) |
| target | 是 | [MutationReceipt](schemas.md#mutationreceipt) | 无（可空不等于可省略） | 目标Case变更回执（MoveReceipt）。 [完整语义](/handoff/audit/response-fields.html#movereceipt) |
| moved_alert_ids | 是 | array <string (uuid)> | 无（可空不等于可省略） | 本次实际从源Case移出的告警UUID。 [完整语义](/handoff/audit/response-fields.html#movereceipt) |
| added_to_target_alert_ids | 是 | array <string (uuid)> | 无（可空不等于可省略） | 实际新增到目标Case的告警UUID；原已在目标的不会重复新增。 [完整语义](/handoff/audit/response-fields.html#movereceipt) |


<a id="mutationreceipt"></a>

## MutationReceipt



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| case_id | 是 | string (uuid) | 无（可空不等于可省略） | Case UUID；来自真实回执/列表，不是页面展示编号。 [完整语义](/handoff/audit/response-fields.html#mutationreceipt) |
| scope_revision | 是 | integer | 无（可空不等于可省略） | Case成员范围版本，历史Run保持冻结值。 [完整语义](/handoff/audit/response-fields.html#mutationreceipt) |
| pending_run_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 准备好的待启动Run；需要用户显式调用start。 [完整语义](/handoff/audit/response-fields.html#mutationreceipt) |
| changed | 是 | boolean | 无（可空不等于可省略） | 本次写入是否实际改变业务内容；幂等重读不表示重新执行。 [完整语义](/handoff/audit/response-fields.html#mutationreceipt) |


<a id="origin"></a>

## Origin



string model, human, system, legacy

<a id="preparebaseline"></a>

## PrepareBaseline



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_scope_revision | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 读 Case 详情获得的当前范围版本；不匹配返回409。 |


<a id="question"></a>

## Question



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string | 无（可空不等于可省略） | 本对象唯一身份；列表导航和关联使用该值，不能使用名称代替。 [完整语义](/handoff/audit/response-fields.html#question) |
| text | 是 | string | 无（可空不等于可省略） | 本轮待核问题正文。 [完整语义](/handoff/audit/response-fields.html#question) |
| scope | 是 | [Scope](schemas.md#scope) | 无（可空不等于可省略） | 本条发现/问题的适用范围；范围声明不等于已证明覆盖。 [完整语义](/handoff/audit/response-fields.html#question) |
| evidence_requirements | 是 | array <string> | 无（可空不等于可省略） | 要回答该问题所需的证据说明。 [完整语义](/handoff/audit/response-fields.html#question) |
| state | 是 | string open, answered, unresolved, not_attempted | 无（可空不等于可省略） | 本轮问题是否open/answered/unresolved/not_attempted，属于冻结调查内容；不是独立问题管理状态，不增加负责人/关闭/跨轮合并。 [完整语义](/handoff/audit/response-fields.html#question) |
| answer | 是 | string / null | 无（可空不等于可省略） | 本轮已有回答，无回答为null。 [完整语义](/handoff/audit/response-fields.html#question) |
| evidence_refs | 是 | array <[EvidenceRef](schemas.md#evidenceref)> | 无（可空不等于可省略） | 本轮引用的材料/结果/人工版本，保留原角色与范围。 [完整语义](/handoff/audit/response-fields.html#question) |
| limitations | 是 | array <string> | 无（可空不等于可省略） | 本次结果或阅读的限制，原样保留。 [完整语义](/handoff/audit/response-fields.html#question) |


<a id="recommendation"></a>

## Recommendation



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string | 无（可空不等于可省略） | 本对象唯一身份；列表导航和关联使用该值，不能使用名称代替。 [完整语义](/handoff/audit/response-fields.html#recommendation) |
| action_type | 是 | string | 无（可空不等于可省略） | 建议动作类型文本，不是执行接口名称。 [完整语义](/handoff/audit/response-fields.html#recommendation) |
| targets | 是 | array <[Target](schemas.md#target)> | 无（可空不等于可省略） | 建议针对的对象键和展示名称。 [完整语义](/handoff/audit/response-fields.html#recommendation) |
| reason | 是 | string | 无（可空不等于可省略） | 服务返回原因；不代表adopt已有reason请求参数。 [完整语义](/handoff/audit/response-fields.html#recommendation) |
| approval_requirement | 是 | string required, not_required, unknown | 无（可空不等于可省略） | 该建议记录的审批需求；unknown不代表无需审批，当前没有审批执行接口。 [完整语义](/handoff/audit/response-fields.html#recommendation) |
| source_refs | 是 | array <[EvidenceRef](schemas.md#evidenceref)> | 无（可空不等于可省略） | 来源引用；任务写入为type/id，读取为已冻结EvidenceRef，不能把读取对象原样回写。 [完整语义](/handoff/audit/response-fields.html#recommendation) |
| limitations | 是 | array <string> | 无（可空不等于可省略） | 本次结果或阅读的限制，原样保留。 [完整语义](/handoff/audit/response-fields.html#recommendation) |


<a id="recordpage"></a>

## RecordPage



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | 是 | array <object> | 无（可空不等于可省略） | 本页记录数组；元素类型在本行类型中说明，空数组仅表示此查询页没有记录。 [完整语义](/handoff/audit/response-fields.html#recordpage) |
| total | 是 | integer | 无（可空不等于可省略） | 当前集合总数；records/assets为对象资产匹配边数。 [完整语义](/handoff/audit/response-fields.html#recordpage) |
| next_offset | 是 | integer / null | 无（可空不等于可省略） | 下一页偏移；null表示结束。 [完整语义](/handoff/audit/response-fields.html#recordpage) |
| observed_at | 是 | string (date-time) | 无（可空不等于可省略） | 本次读取观察时间。 [完整语义](/handoff/audit/response-fields.html#recordpage) |
| limitations | 是 | array <string> | 无（可空不等于可省略） | 本次结果或阅读的限制，原样保留。 [完整语义](/handoff/audit/response-fields.html#recordpage) |


<a id="resultdetail"></a>

## ResultDetail



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| result | 是 | [ResultView](schemas.md#resultview) | 无（可空不等于可省略） | 本次读取的结果对象；可空时表示该次执行没有保存对应结果。 [完整语义](/handoff/audit/response-fields.html#resultdetail) |
| run | 是 | [RunView](schemas.md#runview) | 无（可空不等于可省略） | 对应的执行记录；嵌套类型或动态结构见下表，不能和正式结果/当前判断混用。 [完整语义](/handoff/audit/response-fields.html#resultdetail) |
| source_answer | 是 | [SavedAnswerReference](schemas.md#savedanswerreference) / null | 无（可空不等于可省略） | ai_saved结果关联的已保存原回答身份；baseline或无源回答为null。 [完整语义](/handoff/audit/response-fields.html#resultdetail) |
| members | 是 | array <object> | 无（可空不等于可省略） | 此对象的成员列表；Case为当前成员，Run/Result为当轮冻结成员，动态字段见专门清单。 [完整语义](/handoff/audit/dynamic-fields.html#result-members) |
| member_count | 是 | integer | 无（可空不等于可省略） | 成员总数；超过返回长度时结合members_truncated，不把当前数组长度当全量。 [完整语义](/handoff/audit/response-fields.html#resultdetail) |
| members_truncated | 是 | boolean | 无（可空不等于可省略） | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 [完整语义](/handoff/audit/response-fields.html#resultdetail) |
| delivery | 是 | object / null | 无（可空不等于可省略） | C6交付回执定位信息及细节；没有有效回执为null，有报告不保证有正式Result。 [完整语义](/handoff/audit/dynamic-fields.html#delivery) |


<a id="resultkind"></a>

## ResultKind



string baseline, ai_saved

<a id="resultsummary"></a>

## ResultSummary



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | 该记录的应用UUID，不是页面展示编号或厂商编号。 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| case_id | 是 | string (uuid) | 无（可空不等于可省略） | 案件 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| kind | 是 | [ResultKind](schemas.md#resultkind) | 无（可空不等于可省略） | baseline/ai_saved [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| source_run_id | 是 | string (uuid) | 无（可空不等于可省略） | 实际来源执行，同Case [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| source_answer_id | 是 | string (uuid) / null | 无（可空不等于可省略） | AI保存必有，baseline NULL [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| title | 是 | string | 无（可空不等于可省略） | 正式记录标题；AI保存可自定义 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| purpose | 是 | string | 无（可空不等于可省略） | 本轮目标 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| conclusion | 是 | string / null | 无（可空不等于可省略） | 有效/不确定结论；无结论NULL [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| conclusion_state | 是 | [ConclusionState](schemas.md#conclusionstate) | 无（可空不等于可省略） | 有依据/未决/无法给出 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| conclusion_origin | 是 | [Origin](schemas.md#origin) | 无（可空不等于可省略） | 模型/人工/系统来源 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| validation_state | 是 | [Validation](schemas.md#validation) | 无（可空不等于可省略） | 程序采用或拒绝状态 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| closing_note | 是 | string | 无（可空不等于可省略） | 每轮收尾说明，系统失败交接也有 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| comparison_result_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 明确同案已有结果；首次NULL [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| change_kind | 是 | [ChangeKind](schemas.md#changekind) | 无（可空不等于可省略） | 比较类型 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| change_summary | 是 | string / null | 无（可空不等于可省略） | 相比基线输入/证据/判断变化 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| input_artifact_id | 是 | string (uuid) | 无（可空不等于可省略） | 实际当时输入 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| graph_artifact_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 本轮图，无图NULL；不借另一轮冒充 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| report_artifact_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 同版报告，无报告NULL [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| supersedes_result_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 明确修订另建版本，不能自指或跨案 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| delivery_state | 是 | [Delivery](schemas.md#delivery) | 无（可空不等于可省略） | 正式交付完整性 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| created_at | 是 | string (date-time) | 无（可空不等于可省略） | 执行产物形成时间 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| saved_at | 是 | string (date-time) | 无（可空不等于可省略） | 正式保存时间；AI保存与答复时间不同 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| saved_by | 是 | string (uuid) / null | 无（可空不等于可省略） | 明确AI保存人；baseline由服务保存 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| edited_fields | 是 | array <string> | 无（可空不等于可省略） | 保存AI答案时用户改过的字段名；正文修改须origin=human且重新校验；原消息不改 [完整语义](/handoff/audit/response-fields.html#resultsummary) |
| edit_note | 是 | string / null | 无（可空不等于可省略） | 可选修改说明，不强制增加页面输入 [完整语义](/handoff/audit/response-fields.html#resultsummary) |


<a id="resultview"></a>

## ResultView



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | 该记录的应用UUID，不是页面展示编号或厂商编号。 [完整语义](/handoff/audit/response-fields.html#resultview) |
| case_id | 是 | string (uuid) | 无（可空不等于可省略） | 案件 [完整语义](/handoff/audit/response-fields.html#resultview) |
| kind | 是 | [ResultKind](schemas.md#resultkind) | 无（可空不等于可省略） | baseline/ai_saved [完整语义](/handoff/audit/response-fields.html#resultview) |
| source_run_id | 是 | string (uuid) | 无（可空不等于可省略） | 实际来源执行，同Case [完整语义](/handoff/audit/response-fields.html#resultview) |
| source_answer_id | 是 | string (uuid) / null | 无（可空不等于可省略） | AI保存必有，baseline NULL [完整语义](/handoff/audit/response-fields.html#resultview) |
| title | 是 | string | 无（可空不等于可省略） | 正式记录标题；AI保存可自定义 [完整语义](/handoff/audit/response-fields.html#resultview) |
| purpose | 是 | string | 无（可空不等于可省略） | 本轮目标 [完整语义](/handoff/audit/response-fields.html#resultview) |
| conclusion | 是 | string / null | 无（可空不等于可省略） | 有效/不确定结论；无结论NULL [完整语义](/handoff/audit/response-fields.html#resultview) |
| conclusion_state | 是 | [ConclusionState](schemas.md#conclusionstate) | 无（可空不等于可省略） | 有依据/未决/无法给出 [完整语义](/handoff/audit/response-fields.html#resultview) |
| conclusion_origin | 是 | [Origin](schemas.md#origin) | 无（可空不等于可省略） | 模型/人工/系统来源 [完整语义](/handoff/audit/response-fields.html#resultview) |
| validation_state | 是 | [Validation](schemas.md#validation) | 无（可空不等于可省略） | 程序采用或拒绝状态 [完整语义](/handoff/audit/response-fields.html#resultview) |
| closing_note | 是 | string | 无（可空不等于可省略） | 每轮收尾说明，系统失败交接也有 [完整语义](/handoff/audit/response-fields.html#resultview) |
| comparison_result_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 明确同案已有结果；首次NULL [完整语义](/handoff/audit/response-fields.html#resultview) |
| change_kind | 是 | [ChangeKind](schemas.md#changekind) | 无（可空不等于可省略） | 比较类型 [完整语义](/handoff/audit/response-fields.html#resultview) |
| change_summary | 是 | string / null | 无（可空不等于可省略） | 相比基线输入/证据/判断变化 [完整语义](/handoff/audit/response-fields.html#resultview) |
| input_artifact_id | 是 | string (uuid) | 无（可空不等于可省略） | 实际当时输入 [完整语义](/handoff/audit/response-fields.html#resultview) |
| graph_artifact_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 本轮图，无图NULL；不借另一轮冒充 [完整语义](/handoff/audit/response-fields.html#resultview) |
| report_artifact_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 同版报告，无报告NULL [完整语义](/handoff/audit/response-fields.html#resultview) |
| supersedes_result_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 明确修订另建版本，不能自指或跨案 [完整语义](/handoff/audit/response-fields.html#resultview) |
| delivery_state | 是 | [Delivery](schemas.md#delivery) | 无（可空不等于可省略） | 正式交付完整性 [完整语义](/handoff/audit/response-fields.html#resultview) |
| created_at | 是 | string (date-time) | 无（可空不等于可省略） | 执行产物形成时间 [完整语义](/handoff/audit/response-fields.html#resultview) |
| saved_at | 是 | string (date-time) | 无（可空不等于可省略） | 正式保存时间；AI保存与答复时间不同 [完整语义](/handoff/audit/response-fields.html#resultview) |
| saved_by | 是 | string (uuid) / null | 无（可空不等于可省略） | 明确AI保存人；baseline由服务保存 [完整语义](/handoff/audit/response-fields.html#resultview) |
| edited_fields | 是 | array <string> | 无（可空不等于可省略） | 保存AI答案时用户改过的字段名；正文修改须origin=human且重新校验；原消息不改 [完整语义](/handoff/audit/response-fields.html#resultview) |
| edit_note | 是 | string / null | 无（可空不等于可省略） | 可选修改说明，不强制增加页面输入 [完整语义](/handoff/audit/response-fields.html#resultview) |
| findings | 是 | array <[Finding](schemas.md#finding)> | 无（可空不等于可省略） | 稳定条目ID、依据、反证和限制 [完整语义](/handoff/audit/response-fields.html#resultview) |
| questions | 是 | array <[Question](schemas.md#question)> | 无（可空不等于可省略） | 本轮问题/答案/缺口 [完整语义](/handoff/audit/response-fields.html#resultview) |
| recommendations | 是 | array <[Recommendation](schemas.md#recommendation)> | 无（可空不等于可省略） | 建议含稳定proposal_id、目标、理由及审批要求 [完整语义](/handoff/audit/response-fields.html#resultview) |
| case_impact | 是 | [Impact](schemas.md#impact) | 无（可空不等于可省略） | 作用范围、可调整认识、不能推广处 [完整语义](/handoff/audit/response-fields.html#resultview) |


<a id="rundetail"></a>

## RunDetail



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| run | 是 | [RunView](schemas.md#runview) | 无（可空不等于可省略） | 对应的执行记录；嵌套类型或动态结构见下表，不能和正式结果/当前判断混用。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| result_ids | 是 | array <string (uuid)> | 无（可空不等于可省略） | 该Run已保存的正式结果UUID，按saved_at/id排序；最多200。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| result_count | 是 | integer | 无（可空不等于可省略） | 该Run正式结果总数。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| results_truncated | 是 | boolean | 无（可空不等于可省略） | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| start_eligibility | 是 | [StartAvailability](schemas.md#startavailability) | 无（可空不等于可省略） | 是否可启动及原因，依据最新Run与Case范围。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| current_member_count | 是 | integer | 无（可空不等于可省略） | 当前Case成员数量，可能与当轮输入不同。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| input_member_count | 是 | integer | 无（可空不等于可省略） | 该Run冻结的run_members总数。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| members | 是 | array <object> | 无（可空不等于可省略） | 此对象的成员列表；Case为当前成员，Run/Result为当轮冻结成员，动态字段见专门清单。 [完整语义](/handoff/audit/dynamic-fields.html#run-members) |
| members_truncated | 是 | boolean | 无（可空不等于可省略） | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| read_counts | 是 | object | 无（可空不等于可省略） | 以read_state为键统计当轮成员数量。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| analysis_counts | 是 | object | 无（可空不等于可省略） | 以analysis_state为键统计当轮成员数量。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| steps | 是 | array <object> | 无（可空不等于可省略） | 执行步骤目录，按seq组织；Case最多1000，A/I见动态结构限制。 [完整语义](/handoff/audit/dynamic-fields.html#run-steps) |
| steps_truncated | 是 | boolean | 无（可空不等于可省略） | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| tool_calls | 是 | integer | 无（可空不等于可省略） | kind=tool且state不为planned/skipped的实际尝试次数，包含失败，不是成功查询数。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| usage | 是 | object | 无（可空不等于可省略） | 按已读步骤及全量模型次数汇总；步骤截断时未读用量计unknown，不声称全量费用。 [完整语义](/handoff/audit/dynamic-fields.html#usage-total) |
| artifacts | 是 | array <object> | 无（可空不等于可省略） | 该Run工件元数据目录，正文通过对应工件接口读取。 [完整语义](/handoff/audit/dynamic-fields.html#artifact-metadata) |
| artifact_counts | 是 | object | 无（可空不等于可省略） | Case Run按工件kind分组的总数。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| artifacts_truncated | 是 | boolean | 无（可空不等于可省略） | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| duration_seconds | 是 | number / null | 无（可空不等于可省略） | started_at与ended_at均有值才计算秒数，否则null，不用0代未知。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| elapsed_seconds | 是 | number / null | 无（可空不等于可省略） | Case Run已开始且未结束时从started_at到observed_at的秒数，否则null。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| last_recorded_at | 是 | string (date-time) | 无（可空不等于可省略） | 本轮请求/范围变动/开始/结束/步骤时间/工件捕获时间中实际存在的最新时刻，非服务心跳。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| observed_at | 是 | string (date-time) | 无（可空不等于可省略） | 本次读取观察时间。 [完整语义](/handoff/audit/response-fields.html#rundetail) |
| execution_summary | 否 | [ExecutionSummary](schemas.md#executionsummary) / null | 无（可空不等于可省略） | 从C1.executor已保存计划工件读取的能力/限制快照；未找到为null，不用当前配置回填旧Run。 [完整语义](/handoff/audit/response-fields.html#rundetail) |


<a id="runkind"></a>

## RunKind



string alert_basic, incident_diagnosis, baseline, ai_question

<a id="runstate"></a>

## RunState



string pending_update, running, unknown, completed, failed, cancelled

<a id="runtrigger"></a>

## RunTrigger



string ingested, refresh, case_created, members_changed, manual, question, retry

<a id="runview"></a>

## RunView



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | 该记录的应用UUID，不是页面展示编号或厂商编号。 [完整语义](/handoff/audit/response-fields.html#runview) |
| case_id | 是 | string (uuid) | 无（可空不等于可省略） | baseline/ai_question归属 [完整语义](/handoff/audit/response-fields.html#runview) |
| kind | 是 | [RunKind](schemas.md#runkind) | 无（可空不等于可省略） | 四机器流程明确区分 [完整语义](/handoff/audit/response-fields.html#runview) |
| title | 是 | string | 无（可空不等于可省略） | 本次执行名称，pending随范围更新 [完整语义](/handoff/audit/response-fields.html#runview) |
| purpose | 是 | string | 无（可空不等于可省略） | 本轮目标/提问 [完整语义](/handoff/audit/response-fields.html#runview) |
| trigger | 是 | [RunTrigger](schemas.md#runtrigger) | 无（可空不等于可省略） | 触发原因 [完整语义](/handoff/audit/response-fields.html#runview) |
| scope_revision | 是 | integer / null | 无（可空不等于可省略） | Case成员版本；非Case NULL [完整语义](/handoff/audit/response-fields.html#runview) |
| scope_updated_at | 是 | string (date-time) / null | 无（可空不等于可省略） | pending最近合并范围时间 [完整语义](/handoff/audit/response-fields.html#runview) |
| scope_kind | 是 | string / null | 无（可空不等于可省略） | baseline whole_case，AI可选范围；其他流程NULL [完整语义](/handoff/audit/response-fields.html#runview) |
| window_start | 是 | string (date-time) / null | 无（可空不等于可省略） | 固定绝对查询起点；不适用NULL [完整语义](/handoff/audit/response-fields.html#runview) |
| window_end | 是 | string (date-time) / null | 无（可空不等于可省略） | 固定绝对查询终点；成对出现 [完整语义](/handoff/audit/response-fields.html#runview) |
| state | 是 | [RunState](schemas.md#runstate) | 无（可空不等于可省略） | 记录/执行状态 [完整语义](/handoff/audit/response-fields.html#runview) |
| comparison_result_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 领取时固定的同案比较基线，可跨成员范围 [完整语义](/handoff/audit/response-fields.html#runview) |
| input_artifact_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 领取前NULL；提交running前冻结本地输入 [完整语义](/handoff/audit/response-fields.html#runview) |
| executor_version | 是 | string / null | 无（可空不等于可省略） | 实际执行版本，pending NULL [完整语义](/handoff/audit/response-fields.html#runview) |
| requested_at | 是 | string (date-time) | 无（可空不等于可省略） | 记录创建/首次请求 [完整语义](/handoff/audit/response-fields.html#runview) |
| requested_by | 是 | string (uuid) / null | 无（可空不等于可省略） | 真实请求人 [完整语义](/handoff/audit/response-fields.html#runview) |
| started_at | 是 | string (date-time) / null | 无（可空不等于可省略） | running领取事务时间 [完整语义](/handoff/audit/response-fields.html#runview) |
| ended_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 终态时间；unknown未确认结束NULL [完整语义](/handoff/audit/response-fields.html#runview) |
| stop_reason | 是 | string / null | 无（可空不等于可省略） | 稳定原因码；不强用人类结论代替 [完整语义](/handoff/audit/response-fields.html#runview) |
| stop_detail | 是 | string / null | 无（可空不等于可省略） | 可读原因 [完整语义](/handoff/audit/response-fields.html#runview) |
| delivery_state | 是 | [Delivery](schemas.md#delivery) | 无（可空不等于可省略） | 实际产物交付 [完整语义](/handoff/audit/response-fields.html#runview) |
| row_version | 是 | integer | 无（可空不等于可省略） | 执行状态条件更新版本 [完整语义](/handoff/audit/response-fields.html#runview) |


<a id="savecaseaianswer"></a>

## SaveCaseAIAnswer



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| title | 是 | string; minLength=1; maxLength=200 | 无（可空不等于可省略） | 显示标题；写入必须非空，长度约束见Schema。 |
| conclusion | 是 | string; minLength=1; maxLength=20000 | 无（可空不等于可省略） | 本环节结论正文；null可能未交付/拒收，不补造。 |


<a id="savedanswerreference"></a>

## SavedAnswerReference



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | 该记录的应用UUID，不是页面展示编号或厂商编号。 [完整语义](/handoff/audit/response-fields.html#savedanswerreference) |
| conversation_id | 是 | string (uuid) | 无（可空不等于可省略） | 会话 [完整语义](/handoff/audit/response-fields.html#savedanswerreference) |
| in_reply_to | 是 | string (uuid) / null | 无（可空不等于可省略） | assistant指具体用户问题；同会话 [完整语义](/handoff/audit/response-fields.html#savedanswerreference) |
| source_run_id | 是 | string (uuid) | 无（可空不等于可省略） | 真实ai_question执行；用户消息NULL [完整语义](/handoff/audit/response-fields.html#savedanswerreference) |
| input_artifact_id | 是 | string (uuid) | 无（可空不等于可省略） | assistant实际输入；不能保存时重新读取 [完整语义](/handoff/audit/response-fields.html#savedanswerreference) |
| answered_at | 是 | string (date-time) | 无（可空不等于可省略） | 实际回答完成 [完整语义](/handoff/audit/response-fields.html#savedanswerreference) |


<a id="savedreference"></a>

## SavedReference



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| type | 是 | string alert_material, artifact, task_revision, result | 无（可空不等于可省略） | 本结构的类型判别；EvidenceRef为引用目标类型，EvidenceEntry为证据分类。 [完整语义](/handoff/audit/response-fields.html#savedreference) |
| id | 是 | string (uuid) | 无（可空不等于可省略） | 本对象唯一身份；列表导航和关联使用该值，不能使用名称代替。 [完整语义](/handoff/audit/response-fields.html#savedreference) |
| external | 是 | null | 无（可空不等于可省略） | 现有EvidenceRef固定null；外部材料需先保存为内部可解析工件。 [完整语义](/handoff/audit/response-fields.html#savedreference) |
| source_path | 是 | string; minLength=1; maxLength=2000 | 无（可空不等于可省略） | 保存原件内的路径；SavedReference强制以/开头的JSON Pointer；普通EvidenceRef可空。 [完整语义](/handoff/audit/response-fields.html#savedreference) |
| row_keys | 是 | array <string>; maxItems=0 | 无（可空不等于可省略） | 普通引用中的行定位键；SavedReference现合同必须为空列表。 [完整语义](/handoff/audit/response-fields.html#savedreference) |
| role | 是 | string observation, source_label, prior_analysis, human_statement, execution_receipt | 无（可空不等于可省略） | 来源角色 observation/source_label/prior_analysis/human_statement/execution_receipt；不能相互替代证据。 [完整语义](/handoff/audit/response-fields.html#savedreference) |


<a id="scope"></a>

## Scope



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| kind | 是 | string whole_case, selected_alerts, explicit_objects | 无（可空不等于可省略） | 此结构的种类；Subject为alerts/incidents，Stage为alert_basic/incident_diagnosis，Scope为范围种类，枚举不互换。 [完整语义](/handoff/audit/response-fields.html#scope) |
| alert_ids | 是 | array <string (uuid)> | 无（可空不等于可省略） | 本条结果/人工事实声明覆盖的告警UUID；历史结果按冻结范围解释，不强制变成当前成员。 [完整语义](/handoff/audit/response-fields.html#scope) |
| object_keys | 是 | array <string> | 无（可空不等于可省略） | 范围进一步限定的对象键；explicit_objects必须有键，其他类型可为空。 [完整语义](/handoff/audit/response-fields.html#scope) |
| window_start | 是 | string (date-time) / null | 无（可空不等于可省略） | 窗口起点，带时区；和window_end同时提供或同时为空。 [完整语义](/handoff/audit/response-fields.html#scope) |
| window_end | 是 | string (date-time) / null | 无（可空不等于可省略） | 窗口终点，带时区且不早于起点。 [完整语义](/handoff/audit/response-fields.html#scope) |
| limitations | 是 | array <string> | 无（可空不等于可省略） | 本次结果或阅读的限制，原样保留。 [完整语义](/handoff/audit/response-fields.html#scope) |


<a id="scorestate"></a>

## ScoreState



string not_provided, not_computed, disabled, failed, available, legacy_unverified

<a id="severity"></a>

## Severity



string info, low, medium, high, critical

<a id="stageentry"></a>

## StageEntry



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| run | 是 | [StageRunView](schemas.md#stagerunview) | 无（可空不等于可省略） | 对应的执行记录；嵌套类型或动态结构见下表，不能和正式结果/当前判断混用。 [完整语义](/handoff/audit/response-fields.html#stageentry) |
| freshness | 是 | string current, stale, unverified, unavailable | 无（可空不等于可省略） | 该次运行输入与当前材料/成员/判断的比较：current/stale/unverified/unavailable；不是采用状态。 [完整语义](/handoff/audit/response-fields.html#stageentry) |
| is_current_pointer | 是 | boolean | 无（可空不等于可省略） | 该结果ID是否正是主体当前指针。 [完整语义](/handoff/audit/response-fields.html#stageentry) |
| valid_for_current_input | 是 | boolean | 无（可空不等于可省略） | 同时是当前指针、输入current、Run completed，事件还需diagnosis.validation_state=accepted；不代表模型语义正确。 [完整语义](/handoff/audit/response-fields.html#stageentry) |
| result | 是 | [TriageView](schemas.md#triageview) / [DiagnosisView](schemas.md#diagnosisview) / null | 无（可空不等于可省略） | 本次读取的结果对象；可空时表示该次执行没有保存对应结果。 [完整语义](/handoff/audit/response-fields.html#stageentry) |
| explanation | 是 | [ExplanationView](schemas.md#explanationview) / null | 无（可空不等于可省略） | A分诊的独立解释工件及可用性；I或无解释时null。 [完整语义](/handoff/audit/response-fields.html#stageentry) |
| partial_analysis | 否 | [ExplanationView](schemas.md#explanationview) / null | 无（可空不等于可省略） | 该Run最后可识别的模型响应partial_review读取结果；不可用与未记录分开，不作为当前有效判断。 [完整语义](/handoff/audit/response-fields.html#stageentry) |


<a id="stagepage"></a>

## StagePage



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| subject_id | 是 | string (uuid) | 无（可空不等于可省略） | 本分析目录对应告警或事件UUID。 [完整语义](/handoff/audit/response-fields.html#stagepage) |
| kind | 是 | string alert_basic, incident_diagnosis | 无（可空不等于可省略） | 此结构的种类；Subject为alerts/incidents，Stage为alert_basic/incident_diagnosis，Scope为范围种类，枚举不互换。 [完整语义](/handoff/audit/response-fields.html#stagepage) |
| current_pointer_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 主体latest_triage_id/latest_diagnosis_id；它是分诊/诊断记录ID，不是Run ID。 [完整语义](/handoff/audit/response-fields.html#stagepage) |
| current | 是 | [StageEntry](schemas.md#stageentry) / null | 无（可空不等于可省略） | 指针可核对时的StageEntry，否则null；current_pointer_id是分诊/诊断记录ID。 [完整语义](/handoff/audit/response-fields.html#stagepage) |
| current_unavailable_reason | 是 | string / null | 无（可空不等于可省略） | 无当前指针时null；有指针但无法核对来源Run时current_pointer_without_verifiable_run。 [完整语义](/handoff/audit/response-fields.html#stagepage) |
| entries | 是 | array <[StageEntry](schemas.md#stageentry)> | 无（可空不等于可省略） | 当前对象条目数组：StagePage为历史尝试，证据模型为目录条目。 [完整语义](/handoff/audit/response-fields.html#stagepage) |
| next_before_run_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 下一页运行游标；null表示结束。 [完整语义](/handoff/audit/response-fields.html#stagepage) |


<a id="stagerunview"></a>

## StageRunView



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | 该记录的应用UUID，不是页面展示编号或厂商编号。 [完整语义](/handoff/audit/response-fields.html#stagerunview) |
| kind | 是 | string alert_basic, incident_diagnosis | 无（可空不等于可省略） | 四机器流程明确区分 [完整语义](/handoff/audit/response-fields.html#stagerunview) |
| state | 是 | [RunState](schemas.md#runstate) | 无（可空不等于可省略） | 记录/执行状态 [完整语义](/handoff/audit/response-fields.html#stagerunview) |
| requested_at | 是 | string (date-time) | 无（可空不等于可省略） | 记录创建/首次请求 [完整语义](/handoff/audit/response-fields.html#stagerunview) |
| requested_by | 是 | string (uuid) / null | 无（可空不等于可省略） | 真实请求人 [完整语义](/handoff/audit/response-fields.html#stagerunview) |
| started_at | 是 | string (date-time) / null | 无（可空不等于可省略） | running领取事务时间 [完整语义](/handoff/audit/response-fields.html#stagerunview) |
| ended_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 终态时间；unknown未确认结束NULL [完整语义](/handoff/audit/response-fields.html#stagerunview) |
| executor_version | 是 | string / null | 无（可空不等于可省略） | 实际执行版本，pending NULL [完整语义](/handoff/audit/response-fields.html#stagerunview) |
| input_artifact_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 领取前NULL；提交running前冻结本地输入 [完整语义](/handoff/audit/response-fields.html#stagerunview) |
| stop_reason | 是 | string / null | 无（可空不等于可省略） | 稳定原因码；不强用人类结论代替 [完整语义](/handoff/audit/response-fields.html#stagerunview) |
| delivery_state | 是 | [Delivery](schemas.md#delivery) | 无（可空不等于可省略） | 实际产物交付 [完整语义](/handoff/audit/response-fields.html#stagerunview) |


<a id="start"></a>

## Start



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| expected_scope_revision | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 读 Case 详情获得的当前范围版本；不匹配返回409。 |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| window_start | 否 | string (date-time) / null | 无（可空不等于可省略） | 窗口起点，带时区；和window_end同时提供或同时为空。 |
| window_end | 否 | string (date-time) / null | 无（可空不等于可省略） | 窗口终点，带时区且不早于起点。 |
| comparison_result_id | 否 | string (uuid) / null | 无（可空不等于可省略） | 同案比较结果ID；null表示未指定。 |


<a id="startavailability"></a>

## StartAvailability



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| can_start | 是 | boolean | 无（可空不等于可省略） | 服务给出的启动资格，不由前端从状态猜测。 [完整语义](/handoff/audit/response-fields.html#startavailability) |
| reason | 是 | string ready, not_pending, resolved_case, scope_changed, empty_scope, baseline_active | 无（可空不等于可省略） | 服务返回原因；不代表adopt已有reason请求参数。 [完整语义](/handoff/audit/response-fields.html#startavailability) |


<a id="subjectpage"></a>

## SubjectPage



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| kind | 是 | string alerts, incidents | 无（可空不等于可省略） | 此结构的种类；Subject为alerts/incidents，Stage为alert_basic/incident_diagnosis，Scope为范围种类，枚举不互换。 [完整语义](/handoff/audit/response-fields.html#subjectpage) |
| items | 是 | array <[SubjectView](schemas.md#subjectview)> | 无（可空不等于可省略） | 本页记录数组；元素类型在本行类型中说明，空数组仅表示此查询页没有记录。 [完整语义](/handoff/audit/response-fields.html#subjectpage) |
| total | 是 | integer | 无（可空不等于可省略） | 当前集合总数；records/assets为对象资产匹配边数。 [完整语义](/handoff/audit/response-fields.html#subjectpage) |
| next_before_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 下一页主体游标；null表示结束。 [完整语义](/handoff/audit/response-fields.html#subjectpage) |
| overall_stats | 是 | object | 无（可空不等于可省略） | 主体整体统计；按原口径和observed_at展示。 [完整语义](/handoff/audit/dynamic-fields.html#overall-stats) |
| observed_at | 是 | string (date-time) | 无（可空不等于可省略） | 本次读取观察时间。 [完整语义](/handoff/audit/response-fields.html#subjectpage) |


<a id="subjectview"></a>

## SubjectView



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| kind | 是 | string alerts, incidents | 无（可空不等于可省略） | 此结构的种类；Subject为alerts/incidents，Stage为alert_basic/incident_diagnosis，Scope为范围种类，枚举不互换。 [完整语义](/handoff/audit/response-fields.html#subjectview) |
| facts | 是 | [AlertFacts](schemas.md#alertfacts) / [IncidentFacts](schemas.md#incidentfacts) | 无（可空不等于可省略） | 该kind主体固定事实字段；告警AlertFacts，事件IncidentFacts。 [完整语义](/handoff/audit/response-fields.html#subjectview) |
| owner_name | 是 | string / null | 无（可空不等于可省略） | 从配置的人员目录按同租户owner_id解析出的用户名，无法解析为null。 [完整语义](/handoff/audit/response-fields.html#subjectview) |
| owner_resolution | 是 | string unassigned, resolved, unresolved | 无（可空不等于可省略） | unassigned明确未分配，resolved名称已解析，unresolved有来源/负责人但本次未解析。 [完整语义](/handoff/audit/response-fields.html#subjectview) |
| derived | 是 | [DerivedFields](schemas.md#derivedfields) | 无（可空不等于可省略） | 服务端计算字段；告警和事件含义、空值分别见DerivedFields。 [完整语义](/handoff/audit/response-fields.html#subjectview) |
| material | 是 | object / null | 无（可空不等于可省略） | 告警当前材料元数据，含content_url；事件该值null。正文另读，不含raw_text/raw_json/ocsf_json/enrichment。 [完整语义](/handoff/audit/dynamic-fields.html#alert-material-meta) |
| triage | 是 | object / null | 无（可空不等于可省略） | 告警latest_triage_id对应记录及freshness/confidence_percent/run_state/valid_for_current_input派生值，非TriageView同形状。 [完整语义](/handoff/audit/dynamic-fields.html#alert-triage-feedback) |
| feedback | 是 | object / null | 无（可空不等于可省略） | 告警latest_feedback_id对应kind=human_feedback的原始记录；事件或无记录时null。 [完整语义](/handoff/audit/dynamic-fields.html#alert-triage-feedback) |
| analysis_url | 是 | string | 无（可空不等于可省略） | 该主体分析目录的相对HTTP路径。 [完整语义](/handoff/audit/response-fields.html#subjectview) |
| section_urls | 是 | object | 无（可空不等于可省略） | section到相对HTTP路径的映射；members仅事件、incidents仅告警，其余见记录分区。 [完整语义](/handoff/audit/response-fields.html#subjectview) |


<a id="tacticcount"></a>

## TacticCount



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| label | 是 | string | 无（可空不等于可省略） | 展示标签；TacticCount为原材料战术标签，Threat为威胁标签。 [完整语义](/handoff/audit/response-fields.html#tacticcount) |
| alert_count | 是 | integer | 无（可空不等于可省略） | 含该战术标签的不同告警数。 [完整语义](/handoff/audit/response-fields.html#tacticcount) |


<a id="target"></a>

## Target



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| object_key | 是 | string | 无（可空不等于可省略） | 带类型/命名空间语义的稳定对象键，不能用展示名称或裸IP替代所有对象身份。 [完整语义](/handoff/audit/response-fields.html#target) |
| display_name | 是 | string | 无（可空不等于可省略） | 对象展示名称，不作为关联键。 [完整语义](/handoff/audit/response-fields.html#target) |


<a id="taskcreate"></a>

## TaskCreate



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| title | 是 | string; minLength=1; maxLength=200 | 无（可空不等于可省略） | 显示标题；写入必须非空，长度约束见Schema。 |
| description | 否 | string; maxLength=10000 / null | 无（可空不等于可省略） | 补充说明，可空；不是程序生成结论。 |
| assignee_id | 否 | string (uuid) / null | 无（可空不等于可省略） | 人工任务负责人UUID，需真实存在于本租户；null未分配。 |
| due_at | 否 | string (date-time) / null | 无（可空不等于可省略） | 带时区的截止时间；null清空。 |
| state | 否 | [TaskState](schemas.md#taskstate) | "not_started" | 本对象状态；含义依模型枚举，不与交付/业务判定合并。 |
| result_text | 否 | string; maxLength=20000 / null | 无（可空不等于可省略） | 人工确认结果正文；任务completed时必填非空。 |
| result_scope | 否 | [Scope](schemas.md#scope) / null | 无（可空不等于可省略） | 人工结果适用范围；completed时必填，不得扩大到Case外。 |
| source_refs | 否 | array <[TaskReference](schemas.md#taskreference)>; maxItems=50 | 无（可空不等于可省略） | 来源引用；任务写入为type/id，读取为已冻结EvidenceRef，不能把读取对象原样回写。 |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_scope_revision | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 读 Case 详情获得的当前范围版本；不匹配返回409。 |
| origin_result_id | 否 | string (uuid) / null | 无（可空不等于可省略） | 创建任务时关联的同案正式结果UUID。 |
| origin_finding_id | 否 | string; minLength=1; maxLength=200 / null | 无（可空不等于可省略） | 该结果中的发现ID；必须同时传origin_result_id。 |


<a id="taskedit"></a>

## TaskEdit



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| title | 是 | string; minLength=1; maxLength=200 | 无（可空不等于可省略） | 显示标题；写入必须非空，长度约束见Schema。 |
| description | 否 | string; maxLength=10000 / null | 无（可空不等于可省略） | 补充说明，可空；不是程序生成结论。 |
| assignee_id | 否 | string (uuid) / null | 无（可空不等于可省略） | 人工任务负责人UUID，需真实存在于本租户；null未分配。 |
| due_at | 否 | string (date-time) / null | 无（可空不等于可省略） | 带时区的截止时间；null清空。 |
| state | 否 | [TaskState](schemas.md#taskstate) | "not_started" | 本对象状态；含义依模型枚举，不与交付/业务判定合并。 |
| result_text | 否 | string; maxLength=20000 / null | 无（可空不等于可省略） | 人工确认结果正文；任务completed时必填非空。 |
| result_scope | 否 | [Scope](schemas.md#scope) / null | 无（可空不等于可省略） | 人工结果适用范围；completed时必填，不得扩大到Case外。 |
| source_refs | 否 | array <[TaskReference](schemas.md#taskreference)>; maxItems=50 | 无（可空不等于可省略） | 来源引用；任务写入为type/id，读取为已冻结EvidenceRef，不能把读取对象原样回写。 |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_scope_revision | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 读 Case 详情获得的当前范围版本；不匹配返回409。 |
| expected_row_version | 是 | integer; minimum=1.0 | 无（可空不等于可省略） | 读当前 Case/Task 获得的行版本；不匹配返回409。 |


<a id="taskmutation"></a>

## TaskMutation



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| task | 是 | [TaskView](schemas.md#taskview) | 无（可空不等于可省略） | 本次创建/修订后读取到的完整TaskView。 [完整语义](/handoff/audit/response-fields.html#taskmutation) |
| changed | 是 | boolean | 无（可空不等于可省略） | 本次写入是否实际改变业务内容；幂等重读不表示重新执行。 [完整语义](/handoff/audit/response-fields.html#taskmutation) |


<a id="taskpage"></a>

## TaskPage



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | 是 | array <[TaskView](schemas.md#taskview)> | 无（可空不等于可省略） | 本页记录数组；元素类型在本行类型中说明，空数组仅表示此查询页没有记录。 [完整语义](/handoff/audit/response-fields.html#taskpage) |
| total | 是 | integer | 无（可空不等于可省略） | 当前集合总数；records/assets为对象资产匹配边数。 [完整语义](/handoff/audit/response-fields.html#taskpage) |
| next_offset | 是 | integer / null | 无（可空不等于可省略） | 下一页偏移；null表示结束。 [完整语义](/handoff/audit/response-fields.html#taskpage) |


<a id="taskreference"></a>

## TaskReference



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| type | 是 | string alert_material, artifact, result, task_revision | 无（可空不等于可省略） | Type |
| id | 是 | string (uuid) | 无（可空不等于可省略） | Id |


<a id="taskrevisionpage"></a>

## TaskRevisionPage



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| items | 是 | array <[TaskRevisionView](schemas.md#taskrevisionview)> | 无（可空不等于可省略） | 本页记录数组；元素类型在本行类型中说明，空数组仅表示此查询页没有记录。 [完整语义](/handoff/audit/response-fields.html#taskrevisionpage) |
| total | 是 | integer | 无（可空不等于可省略） | 当前集合总数；records/assets为对象资产匹配边数。 [完整语义](/handoff/audit/response-fields.html#taskrevisionpage) |
| next_offset | 是 | integer / null | 无（可空不等于可省略） | 下一页偏移；null表示结束。 [完整语义](/handoff/audit/response-fields.html#taskrevisionpage) |


<a id="taskrevisionview"></a>

## TaskRevisionView



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | 该记录的应用UUID，不是页面展示编号或厂商编号。 [完整语义](/handoff/audit/response-fields.html#taskrevisionview) |
| case_id | 是 | string (uuid) | 无（可空不等于可省略） | 同案FK [完整语义](/handoff/audit/response-fields.html#taskrevisionview) |
| task_id | 是 | string (uuid) | 无（可空不等于可省略） | 事项 [完整语义](/handoff/audit/response-fields.html#taskrevisionview) |
| revision | 是 | integer | 无（可空不等于可省略） | 从1开始，每次有效编辑+1 [完整语义](/handoff/audit/response-fields.html#taskrevisionview) |
| title | 是 | string | 无（可空不等于可省略） | 任务事项，非空 [完整语义](/handoff/audit/response-fields.html#taskrevisionview) |
| description | 是 | string / null | 无（可空不等于可省略） | 工作说明 [完整语义](/handoff/audit/response-fields.html#taskrevisionview) |
| assignee_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 同租户可选负责人，NULL未分配 [完整语义](/handoff/audit/response-fields.html#taskrevisionview) |
| due_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 截止时间，可空 [完整语义](/handoff/audit/response-fields.html#taskrevisionview) |
| state | 是 | [TaskState](schemas.md#taskstate) | 无（可空不等于可省略） | 四种人工状态 [完整语义](/handoff/audit/response-fields.html#taskrevisionview) |
| result_text | 是 | string / null | 无（可空不等于可省略） | 事实反馈，completed必填非空 [完整语义](/handoff/audit/response-fields.html#taskrevisionview) |
| result_scope | 是 | [Scope](schemas.md#scope) / null | 无（可空不等于可省略） | 确认范围；完成时须明确，如未知部分写limitations [完整语义](/handoff/audit/response-fields.html#taskrevisionview) |
| source_refs | 是 | array <[EvidenceRef](schemas.md#evidenceref)> | 无（可空不等于可省略） | 读回为完整EvidenceRef（含角色/路径），创建/修订请求仅接收TaskReference的type/id，不能原样回传读对象。 [完整语义](/handoff/audit/response-fields.html#taskrevisionview) |
| completed_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 本次进入完成状态的真实时间 [完整语义](/handoff/audit/response-fields.html#taskrevisionview) |
| completed_by | 是 | string (uuid) / null | 无（可空不等于可省略） | 本次实际完成人，不是assignee [完整语义](/handoff/audit/response-fields.html#taskrevisionview) |
| changed_at | 是 | string (date-time) | 无（可空不等于可省略） | 版本编辑时间 [完整语义](/handoff/audit/response-fields.html#taskrevisionview) |
| changed_by | 是 | string (uuid) | 无（可空不等于可省略） | 实际编辑人 [完整语义](/handoff/audit/response-fields.html#taskrevisionview) |


<a id="taskstate"></a>

## TaskState



string not_started, in_progress, completed, cancelled

<a id="taskview"></a>

## TaskView



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | 该记录的应用UUID，不是页面展示编号或厂商编号。 [完整语义](/handoff/audit/response-fields.html#taskview) |
| case_id | 是 | string (uuid) | 无（可空不等于可省略） | 所属Case [完整语义](/handoff/audit/response-fields.html#taskview) |
| current_revision_id | 是 | string (uuid) | 无（可空不等于可省略） | 当前完整版本；延迟FK同事务插入 [完整语义](/handoff/audit/response-fields.html#taskview) |
| origin_result_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 同Case引出事项的结果 [完整语义](/handoff/audit/response-fields.html#taskview) |
| origin_finding_id | 是 | string / null | 无（可空不等于可省略） | 该结果findings中的稳定条目ID [完整语义](/handoff/audit/response-fields.html#taskview) |
| created_at | 是 | string (date-time) | 无（可空不等于可省略） | 任务创建 [完整语义](/handoff/audit/response-fields.html#taskview) |
| created_by | 是 | string (uuid) / null | 无（可空不等于可省略） | 创建者 [完整语义](/handoff/audit/response-fields.html#taskview) |
| updated_at | 是 | string (date-time) | 无（可空不等于可省略） | 最新实际编辑 [完整语义](/handoff/audit/response-fields.html#taskview) |
| row_version | 是 | integer | 无（可空不等于可省略） | 防旧表单覆盖 [完整语义](/handoff/audit/response-fields.html#taskview) |
| current | 是 | [TaskRevisionView](schemas.md#taskrevisionview) | 无（可空不等于可省略） | current_revision_id指向的完整当前修订对象；该HTTP结构为必返且不可空。 [完整语义](/handoff/audit/response-fields.html#taskview) |


<a id="threat"></a>

## Threat



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| namespace | 是 | string; minLength=1; maxLength=500; pattern=\S | 无（可空不等于可省略） | 身份命名空间；不同来源的同名键不得合并。 [完整语义](/handoff/audit/response-fields.html#threat) |
| key | 是 | string; minLength=1; maxLength=500; pattern=\S | 无（可空不等于可省略） | 该命名空间内稳定威胁键。 [完整语义](/handoff/audit/response-fields.html#threat) |
| label | 是 | string; minLength=1; maxLength=500; pattern=\S | 无（可空不等于可省略） | 展示标签；TacticCount为原材料战术标签，Threat为威胁标签。 [完整语义](/handoff/audit/response-fields.html#threat) |
| source_refs | 是 | array <[SavedReference](schemas.md#savedreference)>; minItems=1; maxItems=20 | 无（可空不等于可省略） | 来源引用；任务写入为type/id，读取为已冻结EvidenceRef，不能把读取对象原样回写。 [完整语义](/handoff/audit/response-fields.html#threat) |


<a id="timesource"></a>

## TimeSource



string source, derived_source, unknown

<a id="traceview"></a>

## TraceView



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| run | 是 | object | 无（可空不等于可省略） | A/I实际Run行的公开字段，包括主体身份与limits；不同于精简StageRunView，见动态字段。 [完整语义](/handoff/audit/dynamic-fields.html#run-row) |
| steps | 是 | array <object> | 无（可空不等于可省略） | 执行步骤目录，按seq组织；Case最多1000，A/I见动态结构限制。 [完整语义](/handoff/audit/dynamic-fields.html#run-steps) |
| steps_total | 是 | integer | 无（可空不等于可省略） | 该A/I Run全部步骤数量，不限返回目录长度。 [完整语义](/handoff/audit/response-fields.html#traceview) |
| steps_truncated | 是 | boolean | 无（可空不等于可省略） | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 [完整语义](/handoff/audit/response-fields.html#traceview) |
| artifacts | 是 | array <object> | 无（可空不等于可省略） | 该Run工件元数据目录，正文通过对应工件接口读取。 [完整语义](/handoff/audit/dynamic-fields.html#artifact-metadata) |
| artifacts_total | 是 | integer | 无（可空不等于可省略） | 该A/I Run全部工件数量。 [完整语义](/handoff/audit/response-fields.html#traceview) |
| artifacts_truncated | 是 | boolean | 无（可空不等于可省略） | 对应数组超过读取上限；true时不能把已返回集合当全量。当前Run内截断集合没有继续分页接口。 [完整语义](/handoff/audit/response-fields.html#traceview) |
| usage | 是 | object | 无（可空不等于可省略） | 读取该Run所有模型步骤汇总，与steps目录是否截断无关。 [完整语义](/handoff/audit/dynamic-fields.html#usage-total) |
| tool_calls | 是 | integer | 无（可空不等于可省略） | kind=tool且state不为planned/skipped的实际尝试次数，包含失败，不是成功查询数。 [完整语义](/handoff/audit/response-fields.html#traceview) |
| duration_seconds | 是 | number / null | 无（可空不等于可省略） | started_at与ended_at均有值才计算秒数，否则null，不用0代未知。 [完整语义](/handoff/audit/response-fields.html#traceview) |
| last_recorded_at | 是 | string (date-time) | 无（可空不等于可省略） | 本轮请求/范围变动/开始/结束/步骤时间/工件捕获时间中实际存在的最新时刻，非服务心跳。 [完整语义](/handoff/audit/response-fields.html#traceview) |
| observed_at | 是 | string (date-time) | 无（可空不等于可省略） | 本次读取观察时间。 [完整语义](/handoff/audit/response-fields.html#traceview) |


<a id="triageview"></a>

## TriageView



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | 该记录的应用UUID，不是页面展示编号或厂商编号。 [完整语义](/handoff/audit/response-fields.html#triageview) |
| input_material_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 判断依据的材料版；旧未知NULL [完整语义](/handoff/audit/response-fields.html#triageview) |
| source_run_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 新alert_basic执行；与此告警一致 [完整语义](/handoff/audit/response-fields.html#triageview) |
| verdict | 是 | [Disposition](schemas.md#disposition) / null | 无（可空不等于可省略） | 同次判定 [完整语义](/handoff/audit/response-fields.html#triageview) |
| rationale | 是 | string / null | 无（可空不等于可省略） | 同次理由，历史缺失NULL [完整语义](/handoff/audit/response-fields.html#triageview) |
| confidence | 是 | number / null | 无（可空不等于可省略） | 该分诊记录0..1置信度，score_state=available才作有效数值；SubjectView.triage.confidence_percent已乘100。 [完整语义](/handoff/audit/response-fields.html#triageview) |
| score_state | 是 | [ScoreState](schemas.md#scorestate) | 无（可空不等于可省略） | 计算状态 [完整语义](/handoff/audit/response-fields.html#triageview) |
| recommendations | 是 | array <object> / null | 无（可空不等于可省略） | 同次建议，不与新人工判断拼接 [完整语义](/handoff/audit/response-fields.html#triageview) |
| producer | 是 | string | 无（可空不等于可省略） | 生产者及版本 [完整语义](/handoff/audit/response-fields.html#triageview) |
| actor | 是 | object | 无（可空不等于可省略） | 实际操作者/服务身份 [完整语义](/handoff/audit/response-fields.html#triageview) |
| assessed_at | 是 | string (date-time) | 无（可空不等于可省略） | 判断发生时间 [完整语义](/handoff/audit/response-fields.html#triageview) |


<a id="validation"></a>

## Validation



string not_checked, accepted, rejected, system_only, legacy_unverified

<a id="validationerror"></a>

## ValidationError



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| loc | 是 | array <string / integer> | 无（可空不等于可省略） | 校验错误的位置路径，如body/字段名或path/参数。 [完整语义](/handoff/audit/response-fields.html#validationerror) |
| msg | 是 | string | 无（可空不等于可省略） | 字段校验错误说明。 [完整语义](/handoff/audit/response-fields.html#validationerror) |
| type | 是 | string | 无（可空不等于可省略） | 本结构的类型判别；EvidenceRef为引用目标类型，EvidenceEntry为证据分类。 [完整语义](/handoff/audit/response-fields.html#validationerror) |
| input | 否 | object | 无（可空不等于可省略） | 触发字段校验的输入值（框架可能省略）。 [完整语义](/handoff/audit/response-fields.html#validationerror) |
| ctx | 否 | object | 无（可空不等于可省略） | 字段校验的附加上下文（框架可能省略）。 [完整语义](/handoff/audit/response-fields.html#validationerror) |


<a id="workstatus"></a>

## WorkStatus



string new, in_progress, resolved, unknown

<a id="caseblockingrun"></a>

## CaseBlockingRun



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | 阻止结案的本案Run ID。 [完整语义](/handoff/audit/response-fields.html#caseblockingrun) |
| state | 是 | string running, unknown | 无（可空不等于可省略） | running正在执行；unknown执行结果未明确，两者均阻止结案。 [完整语义](/handoff/audit/response-fields.html#caseblockingrun) |


<a id="casecloserequest"></a>

## CaseCloseRequest



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_row_version | 是 | integer; minimum=1.0 | 无（可空不等于可省略） | 读当前 Case/Task 获得的行版本；不匹配返回409。 |
| reason | 否 | string; minLength=1; maxLength=20000 / null | 无（可空不等于可省略） | 服务返回原因；不代表adopt已有reason请求参数。 |
| acknowledge_open_tasks | 否 | boolean | false | 是否已确认当前未完人工任务；有未完任务时须true并填写reason，任务不会被取消。 |


<a id="caselifecyclerequest"></a>

## CaseLifecycleRequest



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_row_version | 是 | integer; minimum=1.0 | 无（可空不等于可省略） | 读当前 Case/Task 获得的行版本；不匹配返回409。 |
| reason | 否 | string; minLength=1; maxLength=20000 / null | 无（可空不等于可省略） | 服务返回原因；不代表adopt已有reason请求参数。 |


<a id="casemanagementreceipt"></a>

## CaseManagementReceipt



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| case | 是 | [CaseView](schemas.md#caseview) | 无（可空不等于可省略） | 本次操作保存后的Case快照；幂等重放返回原回执，新状态请重新GET。 [完整语义](/handoff/audit/response-fields.html#casemanagementreceipt) |
| changed | 是 | boolean | 无（可空不等于可省略） | 是否实际改变Case字段；false不增加行版本，幂等重放保留原回执。 [完整语义](/handoff/audit/response-fields.html#casemanagementreceipt) |


<a id="casemanagementupdate"></a>

## CaseManagementUpdate



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_row_version | 是 | integer; minimum=1.0 | 无（可空不等于可省略） | 读当前 Case/Task 获得的行版本；不匹配返回409。 |
| title | 否 | string; minLength=1; maxLength=200 | 无（可空不等于可省略） | 显示标题；写入必须非空，长度约束见Schema。 |
| description | 否 | string; maxLength=20000 / null | 无（可空不等于可省略） | 补充说明，可空；不是程序生成结论。 |
| owner_id | 否 | string (uuid) / null | 无（可空不等于可省略） | 负责人用户UUID；人员目录由业务后端负责。 |
| severity | 否 | [Severity](schemas.md#severity) / null | 无（可空不等于可省略） | 严重度枚举；null为未知，不强行补默认等级。 |
| tags | 否 | array <string; minLength=1; maxLength=128>; maxLength=50 | 无（可空不等于可省略） | 标签列表，不替代资产标签。 |
| handling_status | 否 | string new, in_progress | 无（可空不等于可省略） | 主体业务处理状态，与Run执行状态分开。 |


<a id="casemanagementview"></a>

## CaseManagementView



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| case | 是 | [CaseView](schemas.md#caseview) | 无（可空不等于可省略） | 当前已保存的Case管理字段和行版本，与Case详情一致。 [完整语义](/handoff/audit/response-fields.html#casemanagementview) |
| open_task_count | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 当前修订为not_started/in_progress的人工任务数；历史版本不重复计数。 [完整语义](/handoff/audit/response-fields.html#casemanagementview) |
| blocking_runs | 是 | array <[CaseBlockingRun](schemas.md#caseblockingrun)> | 无（可空不等于可省略） | 本案running/unknown Run；空列表表示没有执行状态阻塞，不表示没有待办。 [完整语义](/handoff/audit/response-fields.html#casemanagementview) |
| can_close | 是 | boolean | 无（可空不等于可省略） | 案件未结案且无阻塞Run；如requires_open_task_confirmation为true仍须确认及理由。 [完整语义](/handoff/audit/response-fields.html#casemanagementview) |
| can_reopen | 是 | boolean | 无（可空不等于可省略） | 当前案件是否已解决，可由人显式重开。 [完整语义](/handoff/audit/response-fields.html#casemanagementview) |
| requires_open_task_confirmation | 是 | boolean | 无（可空不等于可省略） | 未结案且存在未完人工任务；关闭请求须确认并提供理由。 [完整语义](/handoff/audit/response-fields.html#casemanagementview) |


<a id="alertfeedback"></a>

## AlertFeedback



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_row_version | 是 | integer; minimum=1.0 | 无（可空不等于可省略） | 读当前 Case/Task 获得的行版本；不匹配返回409。 |
| disposition | 是 | [Disposition](schemas.md#disposition) | 无（可空不等于可省略） | 人工判定；false_positive/benign关闭，已关闭改true_positive/needs_review恢复处理中。 |
| reason | 是 | string; minLength=1; maxLength=20000 | 无（可空不等于可省略） | 服务返回原因；不代表adopt已有reason请求参数。 |


<a id="alertfeedbackbatch"></a>

## AlertFeedbackBatch



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| items | 是 | array <[SelectedSubject](schemas.md#selectedsubject)>; minItems=1 | 无（可空不等于可省略） | 明确选择及各自版本；不允许重复ID，数量上限由服务配置。整批成功或拒绝。 |
| feedback | 是 | [FeedbackFields](schemas.md#feedbackfields) | 无（可空不等于可省略） | 应用于全部明确选中告警的人工判定及理由。 |


<a id="alertmanagementbatch"></a>

## AlertManagementBatch



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| items | 是 | array <[SelectedSubject](schemas.md#selectedsubject)>; minItems=1 | 无（可空不等于可省略） | 明确选择及各自版本；不允许重复ID，数量上限由服务配置。整批成功或拒绝。 |
| changes | 是 | [AlertManagementFields](schemas.md#alertmanagementfields) | 无（可空不等于可省略） | 应用于所选告警的局部修改。 |


<a id="alertmanagementfields"></a>

## AlertManagementFields



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| owner_id | 否 | string (uuid) / null | 无（可空不等于可省略） | 负责人用户UUID；人员目录由业务后端负责。 |
| tags | 否 | array <string; minLength=1; maxLength=128>; maxLength=50 | 无（可空不等于可省略） | 标签列表，不替代资产标签。 |
| reason | 否 | string; minLength=1; maxLength=20000 / null | 无（可空不等于可省略） | 服务返回原因；不代表adopt已有reason请求参数。 |
| handling_status | 否 | string new, in_progress, completed | 无（可空不等于可省略） | 主体业务处理状态，与Run执行状态分开。 |


<a id="alertmanagementupdate"></a>

## AlertManagementUpdate



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_row_version | 是 | integer; minimum=1.0 | 无（可空不等于可省略） | 读当前 Case/Task 获得的行版本；不匹配返回409。 |
| owner_id | 否 | string (uuid) / null | 无（可空不等于可省略） | 负责人用户UUID；人员目录由业务后端负责。 |
| tags | 否 | array <string; minLength=1; maxLength=128>; maxLength=50 | 无（可空不等于可省略） | 标签列表，不替代资产标签。 |
| reason | 否 | string; minLength=1; maxLength=20000 / null | 无（可空不等于可省略） | 服务返回原因；不代表adopt已有reason请求参数。 |
| handling_status | 否 | string new, in_progress, completed | 无（可空不等于可省略） | 主体业务处理状态，与Run执行状态分开。 |


<a id="feedbackfields"></a>

## FeedbackFields



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| disposition | 是 | [Disposition](schemas.md#disposition) | 无（可空不等于可省略） | 人工判定；false_positive/benign关闭，已关闭改true_positive/needs_review恢复处理中。 |
| reason | 是 | string; minLength=1; maxLength=20000 | 无（可空不等于可省略） | 服务返回原因；不代表adopt已有reason请求参数。 |


<a id="incidentmanagementbatch"></a>

## IncidentManagementBatch



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| items | 是 | array <[SelectedSubject](schemas.md#selectedsubject)>; minItems=1 | 无（可空不等于可省略） | 明确选择及各自版本；不允许重复ID，数量上限由服务配置。整批成功或拒绝。 |
| changes | 是 | [IncidentManagementFields](schemas.md#incidentmanagementfields) | 无（可空不等于可省略） | 应用于所选事件的局部修改。 |


<a id="incidentmanagementfields"></a>

## IncidentManagementFields



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| owner_id | 否 | string (uuid) / null | 无（可空不等于可省略） | 负责人用户UUID；人员目录由业务后端负责。 |
| tags | 否 | array <string; minLength=1; maxLength=128>; maxLength=50 | 无（可空不等于可省略） | 标签列表，不替代资产标签。 |
| reason | 否 | string; minLength=1; maxLength=20000 / null | 无（可空不等于可省略） | 服务返回原因；不代表adopt已有reason请求参数。 |
| handling_status | 否 | string new, in_progress, resolved | 无（可空不等于可省略） | 主体业务处理状态，与Run执行状态分开。 |
| severity_override | 否 | [Severity](schemas.md#severity) / null | 无（可空不等于可省略） | 人工等级覆盖；省略保持，null恢复按成员自动等级。 |
| severity_override_reason | 否 | string; minLength=1; maxLength=20000 / null | 无（可空不等于可省略） | 设置人工等级覆盖必填理由；须与severity_override一起提交。 |
| resolution_note | 否 | string; minLength=1; maxLength=20000 / null | 无（可空不等于可省略） | 将事件改为resolved必填；须与handling_status=resolved一起提交。 |


<a id="incidentmanagementupdate"></a>

## IncidentManagementUpdate



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_row_version | 是 | integer; minimum=1.0 | 无（可空不等于可省略） | 读当前 Case/Task 获得的行版本；不匹配返回409。 |
| owner_id | 否 | string (uuid) / null | 无（可空不等于可省略） | 负责人用户UUID；人员目录由业务后端负责。 |
| tags | 否 | array <string; minLength=1; maxLength=128>; maxLength=50 | 无（可空不等于可省略） | 标签列表，不替代资产标签。 |
| reason | 否 | string; minLength=1; maxLength=20000 / null | 无（可空不等于可省略） | 服务返回原因；不代表adopt已有reason请求参数。 |
| handling_status | 否 | string new, in_progress, resolved | 无（可空不等于可省略） | 主体业务处理状态，与Run执行状态分开。 |
| severity_override | 否 | [Severity](schemas.md#severity) / null | 无（可空不等于可省略） | 人工等级覆盖；省略保持，null恢复按成员自动等级。 |
| severity_override_reason | 否 | string; minLength=1; maxLength=20000 / null | 无（可空不等于可省略） | 设置人工等级覆盖必填理由；须与severity_override一起提交。 |
| resolution_note | 否 | string; minLength=1; maxLength=20000 / null | 无（可空不等于可省略） | 将事件改为resolved必填；须与handling_status=resolved一起提交。 |


<a id="selectedsubject"></a>

## SelectedSubject



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | 用户明确选中的告警或事件ID。 |
| expected_row_version | 是 | integer; minimum=1.0 | 无（可空不等于可省略） | 读当前 Case/Task 获得的行版本；不匹配返回409。 |


<a id="subjectbatchreceipt"></a>

## SubjectBatchReceipt



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 本次逻辑批量操作键；同意图重放返回同回执 [完整语义](/handoff/audit/response-fields.html#subjectbatchreceipt) |
| items | 是 | array <[SubjectMutationReceipt](schemas.md#subjectmutationreceipt)> | 无（可空不等于可省略） | 按主体UUID排序的逐项结果，整批成功或拒绝 [完整语义](/handoff/audit/response-fields.html#subjectbatchreceipt) |
| changed_count | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | items中changed=true的个数，不是模型调用数 [完整语义](/handoff/audit/response-fields.html#subjectbatchreceipt) |


<a id="subjectmutationreceipt"></a>

## SubjectMutationReceipt



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| kind | 是 | string alerts, incidents | 无（可空不等于可省略） | alerts或incidents，表示被修改的主体种类 [完整语义](/handoff/audit/response-fields.html#subjectmutationreceipt) |
| facts | 是 | [AlertFacts](schemas.md#alertfacts) / [IncidentFacts](schemas.md#incidentfacts) | 无（可空不等于可省略） | 提交时保存的完整事实快照，沿用原字段；重放原快照，最新值另GET [完整语义](/handoff/audit/response-fields.html#subjectmutationreceipt) |
| changed | 是 | boolean | 无（可空不等于可省略） | 该次是否改变主体，人工反馈新增记录为true [完整语义](/handoff/audit/response-fields.html#subjectmutationreceipt) |
| feedback_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 人工反馈记录ID；普通管理为null [完整语义](/handoff/audit/response-fields.html#subjectmutationreceipt) |
| activity_id | 是 | string (uuid) | 无（可空不等于可省略） | 本操作活动ID，可从主体records/activities读取 [完整语义](/handoff/audit/response-fields.html#subjectmutationreceipt) |


<a id="frozenalertmaterial"></a>

## FrozenAlertMaterial

Run冻结材料的原始行；不包装ContentView。嵌套业务JSON见json-contracts.json。

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | id |
| tenant_id | 是 | string (uuid) | 无（可空不等于可省略） | tenant_id |
| alert_id | 是 | string (uuid) | 无（可空不等于可省略） | 告警 UUID。 |
| revision | 是 | integer; minimum=1 | 无（可空不等于可省略） | 材料或任务修订序号。 |
| received_at | 是 | string (date-time) | 无（可空不等于可省略） | received_at |
| source_version | 是 | string/null | 无（可空不等于可省略） | source_version |
| raw_text | 是 | string/null | 无（可空不等于可省略） | 保留的原始文本。 |
| sha256 | 是 | string/null | 无（可空不等于可省略） | 原件内容摘要；不等于业务结论验证。 |
| raw_json | 是 | object/null | 无（可空不等于可省略） | 保留的原始JSON。 |
| ocsf_json | 是 | object/null | 无（可空不等于可省略） | 标准化事件正文。 |
| enrichment | 是 | object/null | 无（可空不等于可省略） | 已有富化内容。 |
| detection | 是 | object | 无（可空不等于可省略） | 实际检测信息及分数/ATT&CK标签。 |
| source_scope | 是 | object | 无（可空不等于可省略） | 原材料来源范围合同。 |
| retention | 是 | object | 无（可空不等于可省略） | 保留/截断说明。 |
| material_state | 是 | string complete, truncated, summary_only, unavailable | 无（可空不等于可省略） | complete/truncated/summary_only/unavailable，保持原材料状态。 |


<a id="recordalert"></a>

## RecordAlert

实际读取行字段；嵌套JSON保持其原合同，非新增写入DTO。

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | id |
| source_namespace | 是 | string | 无（可空不等于可省略） | source_namespace |
| source_alert_id | 是 | string/null | 无（可空不等于可省略） | source_alert_id |
| vendor_alert_id | 是 | string/null | 无（可空不等于可省略） | vendor_alert_id |
| connector_id | 是 | string/null (uuid) | 无（可空不等于可省略） | connector_id |
| connector_type | 是 | string/null | 无（可空不等于可省略） | connector_type |
| original_vendor | 是 | string/null | 无（可空不等于可省略） | original_vendor |
| title | 是 | string | 无（可空不等于可省略） | 显示标题；写入必须非空，长度约束见Schema。 |
| description | 是 | string/null | 无（可空不等于可省略） | 补充说明，可空；不是程序生成结论。 |
| category | 是 | string/null | 无（可空不等于可省略） | category |
| severity | 是 | string/null info, low, medium, high, critical, None | 无（可空不等于可省略） | 严重度枚举；null为未知，不强行补默认等级。 |
| severity_raw | 是 | string/null | 无（可空不等于可省略） | severity_raw |
| event_time | 是 | string/null (date-time) | 无（可空不等于可省略） | event_time |
| event_time_source | 是 | string source, derived_source, unknown | 无（可空不等于可省略） | event_time_source |
| first_seen_at | 是 | string/null (date-time) | 无（可空不等于可省略） | first_seen_at |
| last_seen_at | 是 | string/null (date-time) | 无（可空不等于可省略） | last_seen_at |
| ingested_at | 是 | string (date-time) | 无（可空不等于可省略） | ingested_at |
| source_updated_at | 是 | string (date-time) | 无（可空不等于可省略） | source_updated_at |
| business_updated_at | 是 | string (date-time) | 无（可空不等于可省略） | business_updated_at |
| handling_status | 是 | string new, in_progress, completed, unknown | 无（可空不等于可省略） | 主体业务处理状态，与Run执行状态分开。 |
| disposition | 是 | string/null true_positive, false_positive, benign, needs_review, None | 无（可空不等于可省略） | disposition |
| owner_id | 是 | string/null (uuid) | 无（可空不等于可省略） | 负责人用户UUID；人员目录由业务后端负责。 |
| assignment_state | 是 | string unassigned, assigned, unresolved | 无（可空不等于可省略） | 分配状态，unresolved不等于unassigned。 |
| owner_source_value | 是 | string/null | 无（可空不等于可省略） | owner_source_value |
| assigned_at | 是 | string/null (date-time) | 无（可空不等于可省略） | assigned_at |
| tags | 是 | array <string> | 无（可空不等于可省略） | 标签列表，不替代资产标签。 |
| priority_value | 是 | number/null | 无（可空不等于可省略） | priority_value |
| priority_state | 是 | string not_provided, not_computed, disabled, failed, available, legacy_unverified | 无（可空不等于可省略） | priority_state |
| priority_source | 是 | string/null | 无（可空不等于可省略） | priority_source |
| priority_basis | 是 | object/null | 无（可空不等于可省略） | priority_basis |
| closed_at | 是 | string/null (date-time) | 无（可空不等于可省略） | closed_at |
| closed_by | 是 | string/null (uuid) | 无（可空不等于可省略） | closed_by |
| reopened_at | 是 | string/null (date-time) | 无（可空不等于可省略） | reopened_at |
| latest_material_id | 是 | string/null (uuid) | 无（可空不等于可省略） | latest_material_id |
| latest_triage_id | 是 | string/null (uuid) | 无（可空不等于可省略） | latest_triage_id |
| latest_feedback_id | 是 | string/null (uuid) | 无（可空不等于可省略） | latest_feedback_id |
| row_version | 是 | integer | 无（可空不等于可省略） | 并发修改版本；后续写入的expected_row_version取此值。 |
| latest_explanation_id | 是 | string/null (uuid) | 无（可空不等于可省略） | latest_explanation_id |


<a id="recordobject"></a>

## RecordObject

实际读取行字段；嵌套JSON保持其原合同，非新增写入DTO。

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | id |
| alert_id | 是 | string (uuid) | 无（可空不等于可省略） | 告警 UUID。 |
| material_id | 是 | string (uuid) | 无（可空不等于可省略） | 材料版本 UUID；历史读取使用冻结版本。 |
| object_key | 是 | string | 无（可空不等于可省略） | object_key |
| object_type | 是 | string host, user, ip, domain, url, file, hash, process, email, application, cloud_resource, technique, other | 无（可空不等于可省略） | object_type |
| source_type | 是 | string/null | 无（可空不等于可省略） | source_type |
| object_role | 是 | string entity, ioc, both | 无（可空不等于可省略） | object_role |
| namespace | 是 | string | 无（可空不等于可省略） | namespace |
| raw_value | 是 | string | 无（可空不等于可省略） | raw_value |
| normalized_value | 是 | string | 无（可空不等于可省略） | normalized_value |
| source_path | 是 | string | 无（可空不等于可省略） | source_path |
| attributes | 是 | object | 无（可空不等于可省略） | attributes |
| asset_match_state | 是 | string matched, ambiguous, not_found, not_checked | 无（可空不等于可省略） | asset_match_state |
| asset_ref | 是 | object/null | 无（可空不等于可省略） | asset_ref |
| match_basis | 是 | object/null | 无（可空不等于可省略） | match_basis |


<a id="recordsource"></a>

## RecordSource

实际读取行字段；嵌套JSON保持其原合同，非新增写入DTO。

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | id |
| alert_id | 是 | string (uuid) | 无（可空不等于可省略） | 告警 UUID。 |
| material_id | 是 | string (uuid) | 无（可空不等于可省略） | 材料版本 UUID；历史读取使用冻结版本。 |
| source_namespace | 是 | string | 无（可空不等于可省略） | source_namespace |
| source_event_id | 是 | string | 无（可空不等于可省略） | source_event_id |
| relation_kind | 是 | string source_event, threshold_candidate, sequence_candidate, related_record | 无（可空不等于可省略） | relation_kind |
| observed_at | 是 | string/null (date-time) | 无（可空不等于可省略） | 本次读取观察时间。 |
| source_path | 是 | string/null | 无（可空不等于可省略） | source_path |


<a id="recordcomment"></a>

## RecordComment

实际读取行字段；嵌套JSON保持其原合同，非新增写入DTO。

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | id |
| alert_id | 是 | string/null (uuid) | 无（可空不等于可省略） | 告警 UUID。 |
| incident_id | 是 | string/null (uuid) | 无（可空不等于可省略） | 事件 UUID。 |
| case_id | 是 | string/null (uuid) | 无（可空不等于可省略） | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| body | 是 | string | 无（可空不等于可省略） | body |
| author_id | 是 | string (uuid) | 无（可空不等于可省略） | author_id |
| author_name_snapshot | 是 | string | 无（可空不等于可省略） | author_name_snapshot |
| created_at | 是 | string (date-time) | 无（可空不等于可省略） | created_at |
| edited_at | 是 | string/null (date-time) | 无（可空不等于可省略） | edited_at |
| edited_by | 是 | string/null (uuid) | 无（可空不等于可省略） | edited_by |
| row_version | 是 | integer | 无（可空不等于可省略） | 并发修改版本；后续写入的expected_row_version取此值。 |


<a id="recordresponse"></a>

## RecordResponse

实际读取行字段；嵌套JSON保持其原合同，非新增写入DTO。

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | id |
| alert_id | 是 | string/null (uuid) | 无（可空不等于可省略） | 告警 UUID。 |
| incident_id | 是 | string/null (uuid) | 无（可空不等于可省略） | 事件 UUID。 |
| case_id | 是 | string/null (uuid) | 无（可空不等于可省略） | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| result_id | 是 | string/null (uuid) | 无（可空不等于可省略） | 同案已保存正式结果 UUID。 |
| proposal_id | 是 | string/null | 无（可空不等于可省略） | proposal_id |
| legacy_proposal_ref | 是 | object/null | 无（可空不等于可省略） | legacy_proposal_ref |
| external_namespace | 是 | string | 无（可空不等于可省略） | external_namespace |
| approval_id | 是 | string/null | 无（可空不等于可省略） | approval_id |
| action_id | 是 | string/null | 无（可空不等于可省略） | action_id |
| linked_at | 是 | string (date-time) | 无（可空不等于可省略） | linked_at |
| receipt_artifact_id | 是 | string/null (uuid) | 无（可空不等于可省略） | receipt_artifact_id |


<a id="recordactivity"></a>

## RecordActivity

实际读取行字段；嵌套JSON保持其原合同，非新增写入DTO。

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | id |
| actor | 是 | object | 无（可空不等于可省略） | actor |
| action | 是 | string | 无（可空不等于可省略） | action |
| subject_alert_id | 是 | string/null (uuid) | 无（可空不等于可省略） | subject_alert_id |
| subject_incident_id | 是 | string/null (uuid) | 无（可空不等于可省略） | subject_incident_id |
| subject_case_id | 是 | string/null (uuid) | 无（可空不等于可省略） | subject_case_id |
| occurred_at | 是 | string (date-time) | 无（可空不等于可省略） | occurred_at |
| summary | 是 | string | 无（可空不等于可省略） | summary |
| detail | 是 | object | 无（可空不等于可省略） | detail |
| matching_targets | 是 | array <[RecordActivityTarget](schemas.md#recordactivitytarget)> | 无（可空不等于可省略） | matching_targets |
| targets_truncated | 是 | boolean | 无（可空不等于可省略） | targets_truncated |


<a id="recordactivitytarget"></a>

## RecordActivityTarget

实际读取行字段；嵌套JSON保持其原合同，非新增写入DTO。

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | id |
| activity_id | 是 | string (uuid) | 无（可空不等于可省略） | activity_id |
| alert_id | 是 | string/null (uuid) | 无（可空不等于可省略） | 告警 UUID。 |
| incident_id | 是 | string/null (uuid) | 无（可空不等于可省略） | 事件 UUID。 |
| case_id | 是 | string/null (uuid) | 无（可空不等于可省略） | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| task_id | 是 | string/null (uuid) | 无（可空不等于可省略） | 本案人工任务 UUID。 |
| run_id | 是 | string/null (uuid) | 无（可空不等于可省略） | 该父主体下的执行 UUID。 |
| result_id | 是 | string/null (uuid) | 无（可空不等于可省略） | 同案已保存正式结果 UUID。 |
| comment_id | 是 | string/null (uuid) | 无（可空不等于可省略） | comment_id |
| before_value | 是 | object/null | 无（可空不等于可省略） | before_value |
| after_value | 是 | object/null | 无（可空不等于可省略） | after_value |
| result_state | 是 | string succeeded, failed, skipped | 无（可空不等于可省略） | result_state |
| reason | 是 | string/null | 无（可空不等于可省略） | 服务返回原因；不代表adopt已有reason请求参数。 |


<a id="recordalertmember"></a>

## RecordAlertMember

实际读取行字段；嵌套JSON保持其原合同，非新增写入DTO。

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | id |
| source_namespace | 是 | string | 无（可空不等于可省略） | source_namespace |
| source_alert_id | 是 | string/null | 无（可空不等于可省略） | source_alert_id |
| vendor_alert_id | 是 | string/null | 无（可空不等于可省略） | vendor_alert_id |
| connector_id | 是 | string/null (uuid) | 无（可空不等于可省略） | connector_id |
| connector_type | 是 | string/null | 无（可空不等于可省略） | connector_type |
| original_vendor | 是 | string/null | 无（可空不等于可省略） | original_vendor |
| title | 是 | string | 无（可空不等于可省略） | 显示标题；写入必须非空，长度约束见Schema。 |
| description | 是 | string/null | 无（可空不等于可省略） | 补充说明，可空；不是程序生成结论。 |
| category | 是 | string/null | 无（可空不等于可省略） | category |
| severity | 是 | string/null info, low, medium, high, critical, None | 无（可空不等于可省略） | 严重度枚举；null为未知，不强行补默认等级。 |
| severity_raw | 是 | string/null | 无（可空不等于可省略） | severity_raw |
| event_time | 是 | string/null (date-time) | 无（可空不等于可省略） | event_time |
| event_time_source | 是 | string source, derived_source, unknown | 无（可空不等于可省略） | event_time_source |
| first_seen_at | 是 | string/null (date-time) | 无（可空不等于可省略） | first_seen_at |
| last_seen_at | 是 | string/null (date-time) | 无（可空不等于可省略） | last_seen_at |
| ingested_at | 是 | string (date-time) | 无（可空不等于可省略） | ingested_at |
| source_updated_at | 是 | string (date-time) | 无（可空不等于可省略） | source_updated_at |
| business_updated_at | 是 | string (date-time) | 无（可空不等于可省略） | business_updated_at |
| handling_status | 是 | string new, in_progress, completed, unknown | 无（可空不等于可省略） | 主体业务处理状态，与Run执行状态分开。 |
| disposition | 是 | string/null true_positive, false_positive, benign, needs_review, None | 无（可空不等于可省略） | disposition |
| owner_id | 是 | string/null (uuid) | 无（可空不等于可省略） | 负责人用户UUID；人员目录由业务后端负责。 |
| assignment_state | 是 | string unassigned, assigned, unresolved | 无（可空不等于可省略） | 分配状态，unresolved不等于unassigned。 |
| owner_source_value | 是 | string/null | 无（可空不等于可省略） | owner_source_value |
| assigned_at | 是 | string/null (date-time) | 无（可空不等于可省略） | assigned_at |
| tags | 是 | array <string> | 无（可空不等于可省略） | 标签列表，不替代资产标签。 |
| priority_value | 是 | number/null | 无（可空不等于可省略） | priority_value |
| priority_state | 是 | string not_provided, not_computed, disabled, failed, available, legacy_unverified | 无（可空不等于可省略） | priority_state |
| priority_source | 是 | string/null | 无（可空不等于可省略） | priority_source |
| priority_basis | 是 | object/null | 无（可空不等于可省略） | priority_basis |
| closed_at | 是 | string/null (date-time) | 无（可空不等于可省略） | closed_at |
| closed_by | 是 | string/null (uuid) | 无（可空不等于可省略） | closed_by |
| reopened_at | 是 | string/null (date-time) | 无（可空不等于可省略） | reopened_at |
| latest_material_id | 是 | string/null (uuid) | 无（可空不等于可省略） | latest_material_id |
| latest_triage_id | 是 | string/null (uuid) | 无（可空不等于可省略） | latest_triage_id |
| latest_feedback_id | 是 | string/null (uuid) | 无（可空不等于可省略） | latest_feedback_id |
| row_version | 是 | integer | 无（可空不等于可省略） | 并发修改版本；后续写入的expected_row_version取此值。 |
| latest_explanation_id | 是 | string/null (uuid) | 无（可空不等于可省略） | latest_explanation_id |
| linked_at | 是 | string (date-time) | 无（可空不等于可省略） | linked_at |
| membership_source | 是 | string | 无（可空不等于可省略） | membership_source |
| correlation_basis | 是 | object | 无（可空不等于可省略） | correlation_basis |
| basis_version | 是 | string | 无（可空不等于可省略） | basis_version |


<a id="recordincidentlink"></a>

## RecordIncidentLink

实际读取行字段；嵌套JSON保持其原合同，非新增写入DTO。

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | id |
| source_namespace | 是 | string | 无（可空不等于可省略） | source_namespace |
| source_incident_id | 是 | string | 无（可空不等于可省略） | source_incident_id |
| title | 是 | string | 无（可空不等于可省略） | 显示标题；写入必须非空，长度约束见Schema。 |
| description | 是 | string/null | 无（可空不等于可省略） | 补充说明，可空；不是程序生成结论。 |
| handling_status | 是 | string new, in_progress, resolved, unknown | 无（可空不等于可省略） | 主体业务处理状态，与Run执行状态分开。 |
| owner_id | 是 | string/null (uuid) | 无（可空不等于可省略） | 负责人用户UUID；人员目录由业务后端负责。 |
| assignment_state | 是 | string unassigned, assigned, unresolved | 无（可空不等于可省略） | 分配状态，unresolved不等于unassigned。 |
| owner_source_value | 是 | string/null | 无（可空不等于可省略） | owner_source_value |
| assigned_at | 是 | string/null (date-time) | 无（可空不等于可省略） | assigned_at |
| tags | 是 | array <string> | 无（可空不等于可省略） | 标签列表，不替代资产标签。 |
| severity_override | 是 | string/null info, low, medium, high, critical, None | 无（可空不等于可省略） | severity_override |
| severity_override_reason | 是 | string/null | 无（可空不等于可省略） | severity_override_reason |
| severity_override_at | 是 | string/null (date-time) | 无（可空不等于可省略） | severity_override_at |
| severity_override_by | 是 | string/null (uuid) | 无（可空不等于可省略） | severity_override_by |
| priority_value | 是 | number/null | 无（可空不等于可省略） | priority_value |
| priority_state | 是 | string not_provided, not_computed, disabled, failed, available, legacy_unverified | 无（可空不等于可省略） | priority_state |
| priority_source | 是 | string/null | 无（可空不等于可省略） | priority_source |
| priority_basis | 是 | object/null | 无（可空不等于可省略） | priority_basis |
| resolution_note | 是 | string/null | 无（可空不等于可省略） | resolution_note |
| resolved_at | 是 | string/null (date-time) | 无（可空不等于可省略） | resolved_at |
| resolved_by | 是 | string/null (uuid) | 无（可空不等于可省略） | resolved_by |
| reopened_at | 是 | string/null (date-time) | 无（可空不等于可省略） | reopened_at |
| created_at | 是 | string (date-time) | 无（可空不等于可省略） | created_at |
| business_updated_at | 是 | string (date-time) | 无（可空不等于可省略） | business_updated_at |
| latest_diagnosis_id | 是 | string/null (uuid) | 无（可空不等于可省略） | latest_diagnosis_id |
| row_version | 是 | integer | 无（可空不等于可省略） | 并发修改版本；后续写入的expected_row_version取此值。 |
| linked_at | 是 | string (date-time) | 无（可空不等于可省略） | linked_at |
| membership_source | 是 | string | 无（可空不等于可省略） | membership_source |
| correlation_basis | 是 | object | 无（可空不等于可省略） | correlation_basis |
| basis_version | 是 | string | 无（可空不等于可省略） | basis_version |


<a id="recordsourceartifact"></a>

## RecordSourceArtifact

实际读取行字段；嵌套JSON保持其原合同，非新增写入DTO。

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 是 | string (uuid) | 无（可空不等于可省略） | id |
| alert_id | 是 | string/null (uuid) | 无（可空不等于可省略） | 告警 UUID。 |
| incident_id | 是 | string/null (uuid) | 无（可空不等于可省略） | 事件 UUID。 |
| case_id | 是 | string/null (uuid) | 无（可空不等于可省略） | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| run_id | 是 | string/null (uuid) | 无（可空不等于可省略） | 该父主体下的执行 UUID。 |
| step_id | 是 | string/null (uuid) | 无（可空不等于可省略） | step_id |
| kind | 是 | string input_snapshot, model_request, model_response, tool_request, tool_response, domain_analysis, deep_analysis, attack_chain, attack_path, alert_graph, report_json, report_markdown, attachment, source_snapshot, handoff, query_plan, alert_explanation, case_evidence_index | 无（可空不等于可省略） | kind |
| schema_version | 是 | string | 无（可空不等于可省略） | schema_version |
| mime_type | 是 | string | 无（可空不等于可省略） | mime_type |
| file_name | 是 | string/null | 无（可空不等于可省略） | file_name |
| sha256 | 是 | string/null | 无（可空不等于可省略） | 原件内容摘要；不等于业务结论验证。 |
| size_bytes | 是 | integer/null | 无（可空不等于可省略） | size_bytes |
| captured_at | 是 | string (date-time) | 无（可空不等于可省略） | captured_at |
| event_time | 是 | string/null (date-time) | 无（可空不等于可省略） | event_time |
| material_state | 是 | string complete, truncated, summary_only, unavailable | 无（可空不等于可省略） | complete/truncated/summary_only/unavailable，保持原材料状态。 |
| source_refs | 是 | array <object> | 无（可空不等于可省略） | 来源引用；任务写入为type/id，读取为已冻结EvidenceRef，不能把读取对象原样回写。 |
| retention | 是 | object | 无（可空不等于可省略） | 保留/截断说明。 |
| created_by | 是 | string/null (uuid) | 无（可空不等于可省略） | created_by |
| content_url | 是 | string | 无（可空不等于可省略） | 读取该非Run来源工件正文的相对URL。 |


<a id="recordcaselink"></a>

## RecordCaseLink



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| id | 否 | string (uuid) | 无（可空不等于可省略） | id |
| title | 否 | string | 无（可空不等于可省略） | title |
| handling_status | 否 | [WorkStatus](schemas.md#workstatus) | 无（可空不等于可省略） | handling_status |
| scope_revision | 否 | integer | 无（可空不等于可省略） | scope_revision |
| via_member_alert | 否 | boolean | 无（可空不等于可省略） | via_member_alert |
| explicit_incident_link | 否 | boolean | 无（可空不等于可省略） | explicit_incident_link |


<a id="recordassetmatch"></a>

## RecordAssetMatch



| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| object_id | 否 | string | 无（可空不等于可省略） | object_id |
| alert_id | 否 | string | 无（可空不等于可省略） | alert_id |
| material_id | 否 | string | 无（可空不等于可省略） | material_id |
| object_key | 否 | string | 无（可空不等于可省略） | object_key |
| namespace | 否 | string | 无（可空不等于可省略） | namespace |
| asset_id | 否 | string | 无（可空不等于可省略） | asset_id |
| name | 否 | string/null | 无（可空不等于可省略） | name |
| fqdn | 否 | string/null | 无（可空不等于可省略） | fqdn |
| asset_type | 否 | string/null | 无（可空不等于可省略） | asset_type |
| criticality | 否 | string/null | 无（可空不等于可省略） | criticality |
| os | 否 | string/null | 无（可空不等于可省略） | os |
| os_version | 否 | string/null | 无（可空不等于可省略） | os_version |
| tags | 否 | array <string> | 无（可空不等于可省略） | tags |
| ip_addresses | 否 | array <string> | 无（可空不等于可省略） | ip_addresses |
| match_basis | 否 | string exact_ip, exact_name_casefold, exact_fqdn_casefold | 无（可空不等于可省略） | match_basis |


<a id="serviceerror"></a>

## ServiceError

实际错误有字符串、结构化对象或字段校验数组三种detail；不要假定都是code对象。

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| detail | 是 | string / object / array <object> | 无（可空不等于可省略） | detail |
