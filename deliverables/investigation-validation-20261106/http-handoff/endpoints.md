# 调查HTTP接口目录（62项）

[共同约定与调用流程](README.md) · [嵌套Schema](schemas.md) · [合成示例JSON](examples.json)

参数来自现有OpenAPI，附加业务校验来自现有实现。以下错误列出调用方直接处理的典型分支；未枚举的5xx仍按未知处理，不伪造成功。示例独立，不可将示例UUID当真实数据发送。

<a id="e01"></a>

## E01 新建 Case

`POST /api/v1/socai2/cases`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 新建 Case。

**输入：** JSON请求体：`CaseCreate`，字段和必填要求见Request body。

**输出：** HTTP 200，`AssociationReceipt`；完整字段和示例见Responses。

**结果：** 创建Case并保存所选告警/事件关系，返回案件ID、范围版本和待启动Run ID；创建本身不执行调查。

**规则与限制：** 至少选择一个告警或事件；事件展开为成员并保留显式事件关系，合并后最多 200 条。保存后返回 pending_run_id；不自动执行。后续 E12→E13。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机TCP及21正式HTTP已完成本批Case/H直接操作；保存值与SQL读回一致，Run未启动。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e01) · [动态投影与差异](audit/dynamic-fields.html)

无路径/查询参数。

请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| title | 是 | string; minLength=1; maxLength=200 | 无（可空不等于可省略） | 显示标题；写入必须非空，长度约束见Schema。 |
| description | 否 | string; maxLength=20000 / null | 无（可空不等于可省略） | 补充说明，可空；不是程序生成结论。 |
| severity | 否 | [Severity](schemas.md#severity) / null | 无（可空不等于可省略） | 严重度枚举；null为未知，不强行补默认等级。 |
| tags | 否 | array <string; minLength=1; maxLength=128>; maxItems=50 | 无（可空不等于可省略） | 标签列表，不替代资产标签。 |
| alert_ids | 否 | array <string (uuid)>; maxItems=200 | 无（可空不等于可省略） | 真实告警UUID集合，禁止重复；具体是新增、完整替换或反馈覆盖范围见操作说明。 |
| incident_ids | 否 | array <string (uuid)>; maxItems=200 | 无（可空不等于可省略） | 显式关联事件UUID集合，服务展开成员。 |


响应类型：[AssociationReceipt](schemas.md#associationreceipt)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {},
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "title": "核查异常登录",
    "description": null,
    "severity": null,
    "tags": [],
    "alert_ids": [
      "00000000-0000-4000-8000-000000000002"
    ],
    "incident_ids": []
  }
}
```

输出示例（HTTP 200）：

```json
{
  "case_id": "00000000-0000-4000-8000-000000000001",
  "scope_revision": 1,
  "pending_run_id": "00000000-0000-4000-8000-000000000004",
  "changed": true,
  "added_alert_ids": [
    "00000000-0000-4000-8000-000000000002"
  ],
  "linked_incident_ids": []
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | case_member_limit_exceeded | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_incident_not_found | 业务约束/对象状态，见操作说明 |
| 409 | case_source_namespace_mismatch | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | case_source_scope_unverified | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E01.errors`，Swagger同操作 Responses 可直接展开。

<a id="e02"></a>

## E02 Case 队列与指标

`GET /api/v1/socai2/cases`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** Case 队列与指标。

**输入：** 查询参数：`limit`, `cursor`, `q`, `handling_status`, `severity`, `owner_id`, `assignment_state`, `metric`, `classification`, `time_from`, `time_to`, `sort_by`, `sort_order`；无请求体。

**输出：** HTTP 200，`CaseQueuePage`；完整字段和示例见Responses。

**结果：** 按指定条件和顺序返回案件列表、筛选总数total和next_cursor；metrics保留租户整体指标。

**规则与限制：** q按标题字面包含或精确UUID；保留handling_status、severity、owner_id、assignment_state、metric、classification。time_from/time_to按business_updated_at；sort_by=business_updated_at（默认）/created_at/severity。total为全部筛选命中数，metrics为租户整体且high_severity仍只计high。未使用新增日期/排序时兼容旧v1游标。时间必须带时区，区间为[time_from,time_to)，允许单边；两端同时传时起点必须早于终点。等级info<low<medium<high<critical，未知值总在最后；同值按同方向UUID排序。每页1–50条，默认20；sort_order默认desc。改变筛选或排序后清空cursor；下一页原样传next_cursor，不自行解析。每次请求为当前只读快照，跨请求有业务更新时不是冻结导出。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机真实PostgreSQL和TCP完成三类列表117次请求：筛选、九种排序双向分页、旧游标兼容及查询前后行不变；21发布读回见本批回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e02) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| query | limit | False | integer; minimum=1; maximum=50 | 20 | 本次最多返回条数；不是总量。默认值及上限见字段约束。 |
| query | cursor | False | string; maxLength=1024 / null | null | 使用服务上一页 next_cursor；改变筛选条件后清空。 |
| query | q | False | string; maxLength=200 / null | null | 标题字面包含或精确UUID搜索；%和_按普通字符处理。 |
| query | handling_status | False | [WorkStatus](schemas.md#workstatus) / null | null | 主体业务处理状态，与Run执行状态分开。 |
| query | severity | False | [Severity](schemas.md#severity) / null | null | 严重度枚举；null为未知，不强行补默认等级。 |
| query | owner_id | False | string (uuid) / null | null | 负责人用户UUID；人员目录由业务后端负责。 |
| query | assignment_state | False | [AssignmentState](schemas.md#assignmentstate) / null | null | 分配状态，unresolved不等于unassigned。 |
| query | metric | False | string awaiting_assignment, in_progress, high_severity, awaiting_human / null | null | Case整体指标快捷过滤条件。 |
| query | classification | False | string true_positive, informational, false_positive / string = not_set / null | null | 案件分类true_positive/informational/false_positive；null未设置；队列可用not_set过滤未设置。 |
| query | time_from | False | string (date-time) / null | null | 带时区的起点，包含；告警按event_time，事件至少一条成员event_time命中，Case按business_updated_at。 |
| query | time_to | False | string (date-time) / null | null | 带时区的终点，不包含；两端同时传时必须晚于time_from。 |
| query | sort_by | False | string business_updated_at, created_at, severity / null | null | 服务排序字段，可选值见本接口枚举；记录排序字段缺值时置后，同值按UUID排序；非法sort_by返回422。 |
| query | sort_order | False | string asc, desc / null | null | asc升序或desc降序，默认desc。 |


无请求体。

响应类型：[CaseQueuePage](schemas.md#casequeuepage)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "limit": 20,
    "q": "需要核实",
    "sort_by": "severity",
    "sort_order": "desc",
    "time_from": "2026-11-10T00:00:00Z",
    "time_to": "2026-11-11T00:00:00Z"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "items": [],
  "total": 0,
  "next_cursor": null,
  "metrics": {
    "awaiting_assignment": 0,
    "in_progress": 0,
    "high_severity": 0,
    "awaiting_human": 0
  }
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | permission_denied | 缺少Case读取能力 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | invalid_time_window | 起点不早于终点；无时区、非法排序或枚举同样422；参数修正前不重试。 |
| 422 | invalid_case_cursor | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | case_cursor_filters_changed | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | invalid_list_cursor | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | list_cursor_filters_changed | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |

完整错误JSON示例见 `examples.json` 的 `E02.errors`，Swagger同操作 Responses 可直接展开。

<a id="e03"></a>

## E03 Case 详情与当前判断

`GET /api/v1/socai2/cases/{case_id}`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** Case 详情与当前判断。

**输入：** 路径参数：`case_id`；无请求体。

**输出：** HTTP 200，`CaseDetail`；完整字段和示例见Responses。

**结果：** 返回指定案件的资料、当前成员、关联事件、已采用判断和调查记录引用。

**规则与限制：** 读取成员、显式事件、当前采用判断、baseline_records 和资料。检查集合总数与截断标记。current_assessment 为 null 时不得挑最新 Run 当成已采用判断。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机TCP及21正式HTTP已完成本批Case/H直接操作；保存值与SQL读回一致，Run未启动。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e03) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |


无请求体。

响应类型：[CaseDetail](schemas.md#casedetail)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "case": {
    "id": "00000000-0000-4000-8000-000000000001",
    "source_namespace": null,
    "title": "合成示例：核查异常登录",
    "description": null,
    "handling_status": "new",
    "severity": null,
    "severity_source": null,
    "owner_id": null,
    "assignment_state": "unassigned",
    "owner_source_value": null,
    "assigned_at": null,
    "tags": [],
    "priority_value": null,
    "priority_state": "not_provided",
    "priority_source": null,
    "priority_basis": null,
    "scope_revision": 1,
    "current_assessment_id": null,
    "classification": null,
    "due_at": null,
    "current_evidence_artifact_id": null,
    "created_at": "2026-11-12T08:00:00Z",
    "created_by": null,
    "business_updated_at": "2026-11-12T08:00:00Z",
    "resolved_at": null,
    "resolved_by": null,
    "resolution_note": null,
    "reopened_at": null,
    "row_version": 1
  },
  "members": [],
  "member_count": 0,
  "members_truncated": false,
  "linked_incidents": [],
  "linked_incident_count": 0,
  "linked_incidents_truncated": false,
  "current_assessment": null,
  "baseline_records": [],
  "page_data": null
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_not_found | 业务约束/对象状态，见操作说明 |
| 409 | current_assessment_reference_invalid | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E03.errors`，Swagger同操作 Responses 可直接展开。

<a id="e04"></a>

## E04 更新分类和截止时间

`PATCH /api/v1/socai2/cases/{case_id}/page-data`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 更新分类和截止时间。

**输入：** 路径参数：`case_id`；JSON请求体：`CaseDataUpdate`，字段和必填要求见Request body。

**输出：** HTTP 200，`CaseDataReceipt`；完整字段和示例见Responses。

**结果：** 保存分类和截止时间，返回案件ID、行版本、是否变更及当前证据目录ID；资料正文需随后GET E03/E05读取。传null会清空对应值。

**规则与限制：** 先 E03 读 row_version。PATCH 必须同时传 classification、due_at，null 表示清空；source=manual/import，source_note 非空。不支持负责人、标题或关闭/重开。成功 E03/E05 刷新。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e04) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_row_version | 是 | integer; minimum=1.0 | 无（可空不等于可省略） | 读当前 Case/Task 获得的行版本；不匹配返回409。 |
| classification | 是 | string true_positive, informational, false_positive / null | 无（可空不等于可省略） | 案件分类true_positive/informational/false_positive；null未设置；队列可用not_set过滤未设置。 |
| due_at | 是 | string (date-time) / null | 无（可空不等于可省略） | 带时区的截止时间；null清空。 |
| source | 是 | string manual, import | 无（可空不等于可省略） | 本次资料变更来源 manual 或 import。 |
| source_note | 是 | string; minLength=1; maxLength=500; pattern=\S | 无（可空不等于可省略） | 资料修改原因/来源说明，非空。 |


响应类型：[CaseDataReceipt](schemas.md#casedatareceipt)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "expected_row_version": 1,
    "classification": "informational",
    "due_at": null,
    "source": "manual",
    "source_note": "业务负责人确认该案用于跟踪已知活动"
  }
}
```

输出示例（HTTP 200）：

```json
{
  "case_id": "00000000-0000-4000-8000-000000000001",
  "row_version": 2,
  "changed": true,
  "current_evidence_artifact_id": null
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_not_found | 业务约束/对象状态，见操作说明 |
| 409 | case_row_version_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E04.errors`，Swagger同操作 Responses 可直接展开。

<a id="e05"></a>

## E05 Case 资料与证据目录

`GET /api/v1/socai2/cases/{case_id}/page-data`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** Case 资料与证据目录。

**输入：** 路径参数：`case_id`；无请求体。

**输出：** HTTP 200，`CasePageData`；完整字段和示例见Responses。

**结果：** 返回案件分类、期限、已采用判断摘要和当前证据目录。

**规则与限制：** 读取 classification、due_at、determination、assessment、evidence。not_recorded 与 evidence_count=null 不等于没有威胁；questions 沿采用来源结果读取。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e05) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |


无请求体。

响应类型：[CasePageData](schemas.md#casepagedata)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "schema_version": "socai2.case-page-data.v1",
  "classification": null,
  "due_at": null,
  "determination": null,
  "assessment": null,
  "evidence": {
    "artifact_id": null,
    "state": "not_recorded",
    "evidence_count": null,
    "threat_count": null,
    "covered_alert_ids": [],
    "uncovered_alert_ids": [],
    "excluded_evidence_ids": [],
    "limitations": [],
    "entries": [],
    "index": null
  }
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_not_found | 业务约束/对象状态，见操作说明 |
| 409 | current_assessment_reference_invalid | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E05.errors`，Swagger同操作 Responses 可直接展开。

<a id="e06"></a>

## E06 发布证据目录

`POST /api/v1/socai2/cases/{case_id}/evidence-index`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 发布证据目录。

**输入：** 路径参数：`case_id`；JSON请求体：`EvidencePublish`，字段和必填要求见Request body。

**输出：** HTTP 200，`CaseDataReceipt`；完整字段和示例见Responses。

**结果：** 保存并发布提交的证据目录版本，返回当前目录工件ID；此操作不生成新证据。

**规则与限制：** 发布已整理的引用目录，不会生成新证据或执行模型。先 E03/E05 获取行版本和旧 artifact_id；index.supersedes_artifact_id 对应旧版本，范围需匹配当前成员。partial/unavailable 必须写 limitations；unavailable 的 entries 必须为空。对象、来源路径、hash、角色均以实际原件为准。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e06) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_row_version | 是 | integer; minimum=1.0 | 无（可空不等于可省略） | 读当前 Case/Task 获得的行版本；不匹配返回409。 |
| expected_current_artifact_id | 是 | string (uuid) / null | 无（可空不等于可省略） | 当前证据目录工件 ID；首次为null。必须显式传入，和实际旧版本比较。 |
| index | 是 | [EvidenceIndex](schemas.md#evidenceindex) | 无（可空不等于可省略） | 证据目录版本正文，不是自动生成证据的命令。 |


响应类型：[CaseDataReceipt](schemas.md#casedatareceipt)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "expected_row_version": 1,
    "expected_current_artifact_id": null,
    "index": {
      "schema_version": "socai2.case-evidence.v1",
      "scope_revision": 1,
      "alert_ids": [
        "00000000-0000-4000-8000-000000000002"
      ],
      "supersedes_artifact_id": null,
      "availability_state": "unavailable",
      "limitations": [
        "尚未整理可发布的证据目录"
      ],
      "entries": []
    }
  }
}
```

输出示例（HTTP 200）：

```json
{
  "case_id": "00000000-0000-4000-8000-000000000001",
  "row_version": 2,
  "changed": true,
  "current_evidence_artifact_id": "00000000-0000-4000-8000-000000000009"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | evidence_index_scope_invalid | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | evidence_source_not_found | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | evidence_source_path_not_found | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | evidence_index_digest_invalid | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | evidence_sources_do_not_cover_entry | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 409 | case_row_version_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | case_evidence_version_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | case_scope_revision_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E06.errors`，Swagger同操作 Responses 可直接展开。

<a id="e07"></a>

## E07 替换完整 Case 成员

`PUT /api/v1/socai2/cases/{case_id}/members`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 替换完整 Case 成员。

**输入：** 路径参数：`case_id`；JSON请求体：`MemberChange`，字段和必填要求见Request body。

**输出：** HTTP 200，`MutationReceipt`；完整字段和示例见Responses。

**结果：** 用提交的完整告警集合替换当前成员范围，返回新的范围版本及待启动调查引用。

**规则与限制：** alert_ids 是替换后的完整集合，不能只传想删除的条目。可为空但空范围不能启动调查。保存产生范围版本及 pending 记录，不覆盖历史冻结输入。普通添加用 E08。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e07) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_scope_revision | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 读 Case 详情获得的当前范围版本；不匹配返回409。 |
| alert_ids | 是 | array <string (uuid)>; maxItems=200 | 无（可空不等于可省略） | 真实告警UUID集合，禁止重复；具体是新增、完整替换或反馈覆盖范围见操作说明。 |


响应类型：[MutationReceipt](schemas.md#mutationreceipt)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "expected_scope_revision": 1,
    "alert_ids": [
      "00000000-0000-4000-8000-000000000002"
    ]
  }
}
```

输出示例（HTTP 200）：

```json
{
  "case_id": "00000000-0000-4000-8000-000000000001",
  "scope_revision": 1,
  "pending_run_id": "00000000-0000-4000-8000-000000000004",
  "changed": true
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_not_found | 业务约束/对象状态，见操作说明 |
| 404 | member_alert_not_found | 业务约束/对象状态，见操作说明 |
| 409 | case_scope_revision_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | resolved_case_scope_policy_not_enabled | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E07.errors`，Swagger同操作 Responses 可直接展开。

<a id="e08"></a>

## E08 关联告警或事件

`POST /api/v1/socai2/cases/{case_id}/associations`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 关联告警或事件。

**输入：** 路径参数：`case_id`；JSON请求体：`AssociationRequest`，字段和必填要求见Request body。

**输出：** HTTP 200，`AssociationReceipt`；完整字段和示例见Responses。

**结果：** 将所选告警或事件关联到案件，返回实际新增成员、事件关系和范围版本。

**规则与限制：** 先 E03 获取 expected_scope_revision。至少选择一个告警/事件；只添加关联，不从别的 Case 移除，也不自动启动。事件展开成员；返回实际新增与显式关联列表。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e08) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_scope_revision | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 读 Case 详情获得的当前范围版本；不匹配返回409。 |
| alert_ids | 否 | array <string (uuid)>; maxItems=200 | 无（可空不等于可省略） | 真实告警UUID集合，禁止重复；具体是新增、完整替换或反馈覆盖范围见操作说明。 |
| incident_ids | 否 | array <string (uuid)>; maxItems=200 | 无（可空不等于可省略） | 显式关联事件UUID集合，服务展开成员。 |


响应类型：[AssociationReceipt](schemas.md#associationreceipt)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "expected_scope_revision": 1,
    "alert_ids": [
      "00000000-0000-4000-8000-000000000002"
    ],
    "incident_ids": []
  }
}
```

输出示例（HTTP 200）：

```json
{
  "case_id": "00000000-0000-4000-8000-000000000001",
  "scope_revision": 1,
  "pending_run_id": "00000000-0000-4000-8000-000000000004",
  "changed": true,
  "added_alert_ids": [
    "00000000-0000-4000-8000-000000000002"
  ],
  "linked_incident_ids": []
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | case_member_limit_exceeded | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 409 | case_scope_revision_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | case_source_namespace_mismatch | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | resolved_case_scope_policy_not_enabled | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 404 | case_incident_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E08.errors`，Swagger同操作 Responses 可直接展开。

<a id="e09"></a>

## E09 在两个 Case 间移动告警成员

`POST /api/v1/socai2/cases/{case_id}/members/move`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 在两个 Case 间移动告警成员。

**输入：** 路径参数：`case_id`；JSON请求体：`MoveMembers`，字段和必填要求见Request body。

**输出：** HTTP 200，`MoveReceipt`；完整字段和示例见Responses。

**结果：** 将所选告警从源案件移至目标案件，返回两案变更回执；历史调查范围保持不变。

**规则与限制：** 先分别 E03 读取两案 scope_revision。源/目标不同；一次事务更新两案，返回 source/target 回执；不移动显式事件关系，不改历史 Run。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e09) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| target_case_id | 是 | string (uuid) | 无（可空不等于可省略） | 移动目标Case；不得等于路径源Case。 |
| expected_source_scope_revision | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 源 Case 当前范围版本。 |
| expected_target_scope_revision | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 目标 Case 当前范围版本。 |
| alert_ids | 是 | array <string (uuid)>; minItems=1; maxItems=200 | 无（可空不等于可省略） | 真实告警UUID集合，禁止重复；具体是新增、完整替换或反馈覆盖范围见操作说明。 |


响应类型：[MoveReceipt](schemas.md#movereceipt)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "target_case_id": "00000000-0000-4000-8000-000000000014",
    "expected_source_scope_revision": 1,
    "expected_target_scope_revision": 1,
    "alert_ids": [
      "00000000-0000-4000-8000-000000000002"
    ]
  }
}
```

输出示例（HTTP 200）：

```json
{
  "source": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "scope_revision": 2,
    "pending_run_id": "00000000-0000-4000-8000-000000000004",
    "changed": true
  },
  "target": {
    "case_id": "00000000-0000-4000-8000-000000000014",
    "scope_revision": 2,
    "pending_run_id": null,
    "changed": true
  },
  "moved_alert_ids": [
    "00000000-0000-4000-8000-000000000002"
  ],
  "added_to_target_alert_ids": [
    "00000000-0000-4000-8000-000000000002"
  ]
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | case_move_requires_different_target | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | case_member_limit_exceeded | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 409 | case_move_member_not_in_source | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | case_scope_revision_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E09.errors`，Swagger同操作 Responses 可直接展开。

<a id="e10"></a>

## E10 Case 调查历史

`GET /api/v1/socai2/cases/{case_id}/history`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** Case 调查历史。

**输入：** 路径参数：`case_id`；查询参数：`limit`, `cursor`；无请求体。

**输出：** HTTP 200，`HistoryPage`；完整字段和示例见Responses。

**结果：** 返回该案件的基础调查Run及已保存AI结果历史和下一页游标；人工任务修订历史通过E42/E43读取。

**规则与限制：** 按 next_cursor 取后续历史；类型区分 baseline 与 ai_saved，当前 Q 保存未实现。相关 A/I 运行需 E22/E23 组合，不能从 Case 历史推断全局目录。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e10) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| query | limit | False | integer; minimum=1; maximum=100 | 20 | 本次最多返回条数；不是总量。默认值及上限见字段约束。 |
| query | cursor | False | string; maxLength=512 / null | null | 使用服务上一页 next_cursor；改变筛选条件后清空。 |


无请求体。

响应类型：[HistoryPage](schemas.md#historypage)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "limit": 20
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "items": [],
  "next_cursor": null
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | invalid_history_cursor | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | invalid_history_limit | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E10.errors`，Swagger同操作 Responses 可直接展开。

<a id="e11"></a>

## E11 准备新一轮调查

`POST /api/v1/socai2/cases/{case_id}/baseline/prepare`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 准备新一轮调查。

**输入：** 路径参数：`case_id`；JSON请求体：`PrepareBaseline`，字段和必填要求见Request body。

**输出：** HTTP 200，`BaselinePreparation`；完整字段和示例见Responses。

**结果：** 为当前案件范围准备或复用待启动Run，返回Run ID及是否本次新建；随后需显式启动。

**规则与限制：** 先 E03 读当前 scope_revision，返回 pending_run_id 和 created。仅准备，不调用模型；存在运行中记录时可保留 pending，启动资格由 E12 判断。空范围/已解决案不能直接启动。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e11) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_scope_revision | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 读 Case 详情获得的当前范围版本；不匹配返回409。 |


响应类型：[BaselinePreparation](schemas.md#baselinepreparation)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "expected_scope_revision": 1
  }
}
```

输出示例（HTTP 200）：

```json
{
  "case_id": "00000000-0000-4000-8000-000000000001",
  "scope_revision": 1,
  "pending_run_id": "00000000-0000-4000-8000-000000000004",
  "created": true
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 409 | baseline_scope_empty | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | baseline_scope_revision_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | resolved_case_start_policy_not_enabled | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E11.errors`，Swagger同操作 Responses 可直接展开。

<a id="e12"></a>

## E12 读取 Case Run 与执行明细

`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 读取 Case Run 与执行明细。

**输入：** 路径参数：`case_id`, `run_id`；无请求体。

**输出：** HTTP 200，`RunDetail`；完整字段和示例见Responses。

**结果：** 返回指定Run的执行状态、冻结成员、步骤、工件、结果引用、用量和启动资格。

**规则与限制：** 读取 start_eligibility、冻结成员、steps、工件、用量和结果 ID。can_start=false 时显示 reason。成员上限200、步骤1000、工件/结果各200；被截断的集合当前没有进一步分页 API，必须明确提示。读取不会继续执行。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机TCP及21正式HTTP已完成本批Case/H直接操作；保存值与SQL读回一致，Run未启动。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e12) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| path | run_id | True | string (uuid) | null | 该父主体下的执行 UUID。 |


无请求体。

响应类型：[RunDetail](schemas.md#rundetail)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "run_id": "00000000-0000-4000-8000-000000000004"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "run": {
    "id": "00000000-0000-4000-8000-000000000004",
    "case_id": "00000000-0000-4000-8000-000000000001",
    "kind": "baseline",
    "title": "合成示例：核查异常登录",
    "purpose": "仅说明合同结构，无真实执行或业务判断。",
    "trigger": "manual",
    "scope_revision": 1,
    "scope_updated_at": null,
    "scope_kind": null,
    "window_start": null,
    "window_end": null,
    "state": "pending_update",
    "comparison_result_id": null,
    "input_artifact_id": null,
    "executor_version": null,
    "requested_at": "2026-11-12T08:00:00Z",
    "requested_by": null,
    "started_at": null,
    "ended_at": null,
    "stop_reason": null,
    "stop_detail": null,
    "delivery_state": "none",
    "row_version": 1
  },
  "result_ids": [],
  "result_count": 0,
  "results_truncated": false,
  "start_eligibility": {
    "can_start": false,
    "reason": "empty_scope"
  },
  "current_member_count": 0,
  "input_member_count": 0,
  "members": [],
  "members_truncated": false,
  "read_counts": {},
  "analysis_counts": {},
  "steps": [],
  "steps_truncated": false,
  "tool_calls": 0,
  "usage": {
    "model_calls": 0,
    "known_total_tokens": 0,
    "unknown_token_calls": 0,
    "total_tokens": 0,
    "costs_by_currency_and_price_version": [],
    "unpriced_model_calls": 0
  },
  "artifacts": [],
  "artifact_counts": {},
  "artifacts_truncated": false,
  "duration_seconds": null,
  "elapsed_seconds": null,
  "last_recorded_at": "2026-11-12T08:00:00Z",
  "observed_at": "2026-11-12T08:00:00Z",
  "execution_summary": null
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_run_not_found | 业务约束/对象状态，见操作说明 |
| 409 | execution_plan_link_invalid | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E12.errors`，Swagger同操作 Responses 可直接展开。

<a id="e13"></a>

## E13 启动指定 pending Run

`POST /api/v1/socai2/cases/{case_id}/runs/{run_id}/start`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 启动指定 pending Run。

**输入：** 路径参数：`case_id`, `run_id`；JSON请求体：`Start`，字段和必填要求见Request body。

**输出：** HTTP 200，`RunDetail`；完整字段和示例见Responses。

**结果：** 执行指定pending Run并等待本次执行返回，返回Run状态和已有结果引用；异常或执行未知时先读取同一Run。

**规则与限制：** 必须使用 E01/E08/E11 返回的 Run ID，先看 E12 启动资格。可选 window_start/end 同时传带时区的时间，start<=end；comparison_result_id 必须属于同案。当前是同步等待执行，不是202队列提交；POST 等待时可 GET E12 观察。超时/503/unknown 先读取该 Run，不换 operation_key 重新发起。模型质量仍未通过。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库的执行、保存和读取通过；模型/外部查询为替身，真实模型效果未据此验收。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e13) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| path | run_id | True | string (uuid) | null | 该父主体下的执行 UUID。 |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| expected_scope_revision | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 读 Case 详情获得的当前范围版本；不匹配返回409。 |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| window_start | 否 | string (date-time) / null | 无（可空不等于可省略） | 窗口起点，带时区；和window_end同时提供或同时为空。 |
| window_end | 否 | string (date-time) / null | 无（可空不等于可省略） | 窗口终点，带时区且不早于起点。 |
| comparison_result_id | 否 | string (uuid) / null | 无（可空不等于可省略） | 同案比较结果ID；null表示未指定。 |


响应类型：[RunDetail](schemas.md#rundetail)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "run_id": "00000000-0000-4000-8000-000000000004"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "expected_scope_revision": 1,
    "window_start": null,
    "window_end": null,
    "comparison_result_id": null
  }
}
```

输出示例（HTTP 200）：

```json
{
  "run": {
    "id": "00000000-0000-4000-8000-000000000004",
    "case_id": "00000000-0000-4000-8000-000000000001",
    "kind": "baseline",
    "title": "合成示例：核查异常登录",
    "purpose": "仅说明合同结构，无真实执行或业务判断。",
    "trigger": "manual",
    "scope_revision": 1,
    "scope_updated_at": null,
    "scope_kind": null,
    "window_start": null,
    "window_end": null,
    "state": "failed",
    "comparison_result_id": null,
    "input_artifact_id": null,
    "executor_version": null,
    "requested_at": "2026-11-12T08:00:00Z",
    "requested_by": null,
    "started_at": "2026-11-12T08:00:00Z",
    "ended_at": "2026-11-12T08:00:00Z",
    "stop_reason": "example_unavailable",
    "stop_detail": "合成失败示例，不表示真实执行",
    "delivery_state": "none",
    "row_version": 1
  },
  "result_ids": [],
  "result_count": 0,
  "results_truncated": false,
  "start_eligibility": {
    "can_start": false,
    "reason": "not_pending"
  },
  "current_member_count": 0,
  "input_member_count": 0,
  "members": [],
  "members_truncated": false,
  "read_counts": {},
  "analysis_counts": {},
  "steps": [],
  "steps_truncated": false,
  "tool_calls": 0,
  "usage": {
    "model_calls": 0,
    "known_total_tokens": 0,
    "unknown_token_calls": 0,
    "total_tokens": 0,
    "costs_by_currency_and_price_version": [],
    "unpriced_model_calls": 0
  },
  "artifacts": [],
  "artifact_counts": {},
  "artifacts_truncated": false,
  "duration_seconds": null,
  "elapsed_seconds": null,
  "last_recorded_at": "2026-11-12T08:00:00Z",
  "observed_at": "2026-11-12T08:00:00Z",
  "execution_summary": null
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | full_executor_limits_outside_policy | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 503 | full_baseline_executor_not_configured | 业务约束/对象状态，见操作说明 |
| 503 | read_run | 执行异常或结果未知；先GET读取，禁止盲目重派 |
| 404 | baseline_not_found | 业务约束/对象状态，见操作说明 |
| 404 | comparison_result_not_found | 业务约束/对象状态，见操作说明 |
| 409 | baseline_already_active | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | baseline_already_claimed | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | baseline_scope_empty | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | baseline_scope_revision_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | resolved_case_start_policy_not_enabled | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E13.errors`，Swagger同操作 Responses 可直接展开。

<a id="e14"></a>

## E14 读取正式结果

`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 读取正式结果。

**输入：** 路径参数：`case_id`, `result_id`；无请求体。

**输出：** HTTP 200，`ResultDetail`；完整字段和示例见Responses。

**结果：** 返回指定正式结果、对应Run、冻结成员及交付信息；结论、发现、待核问题和建议分别返回。

**规则与限制：** 返回 result、run、冻结成员、source_answer、delivery。结论、发现、questions、建议分开，questions 作为结论的一部分，不建立问题管理状态；人工确认由用户 E38 建任务。conclusion=null/validation_state=rejected 不包装成成功判断。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e14) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| path | result_id | True | string (uuid) | null | 同案已保存正式结果 UUID。 |


无请求体。

响应类型：[ResultDetail](schemas.md#resultdetail)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "result_id": "00000000-0000-4000-8000-000000000005"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "result": {
    "id": "00000000-0000-4000-8000-000000000005",
    "case_id": "00000000-0000-4000-8000-000000000001",
    "kind": "baseline",
    "source_run_id": "00000000-0000-4000-8000-000000000004",
    "source_answer_id": null,
    "title": "合成示例：核查异常登录",
    "purpose": "仅说明合同结构，无真实执行或业务判断。",
    "conclusion": null,
    "conclusion_state": "unavailable",
    "conclusion_origin": "system",
    "validation_state": "system_only",
    "closing_note": "仅说明合同结构，无真实执行或业务判断。",
    "comparison_result_id": null,
    "change_kind": "initial",
    "change_summary": null,
    "input_artifact_id": "00000000-0000-4000-8000-000000000009",
    "graph_artifact_id": null,
    "report_artifact_id": null,
    "supersedes_result_id": null,
    "delivery_state": "partial",
    "created_at": "2026-11-12T08:00:00Z",
    "saved_at": "2026-11-12T08:00:00Z",
    "saved_by": null,
    "edited_fields": [],
    "edit_note": null,
    "findings": [],
    "questions": [],
    "recommendations": [],
    "case_impact": {
      "summary": null,
      "supported_changes": [],
      "cannot_generalize": [],
      "affected_scope": {
        "kind": "selected_alerts",
        "alert_ids": [
          "00000000-0000-4000-8000-000000000002"
        ],
        "object_keys": [],
        "window_start": null,
        "window_end": null,
        "limitations": [
          "该轮未形成可采用结论"
        ]
      },
      "next_steps": []
    }
  },
  "run": {
    "id": "00000000-0000-4000-8000-000000000004",
    "case_id": "00000000-0000-4000-8000-000000000001",
    "kind": "baseline",
    "title": "合成示例：核查异常登录",
    "purpose": "仅说明合同结构，无真实执行或业务判断。",
    "trigger": "manual",
    "scope_revision": 1,
    "scope_updated_at": null,
    "scope_kind": "whole_case",
    "window_start": null,
    "window_end": null,
    "state": "failed",
    "comparison_result_id": null,
    "input_artifact_id": "00000000-0000-4000-8000-000000000009",
    "executor_version": null,
    "requested_at": "2026-11-12T08:00:00Z",
    "requested_by": null,
    "started_at": "2026-11-12T08:00:00Z",
    "ended_at": "2026-11-12T08:00:00Z",
    "stop_reason": "example_no_conclusion",
    "stop_detail": null,
    "delivery_state": "partial",
    "row_version": 1
  },
  "source_answer": null,
  "members": [
    {
      "id": "00000000-0000-4000-8000-000000000007",
      "case_id": "00000000-0000-4000-8000-000000000001",
      "result_id": "00000000-0000-4000-8000-000000000005",
      "run_id": "00000000-0000-4000-8000-000000000004",
      "alert_id": "00000000-0000-4000-8000-000000000002",
      "assessment_state": "not_analyzed",
      "conclusion_covered": false,
      "assessment": null,
      "limitations": "该轮未形成可采用结论",
      "evidence_refs": []
    }
  ],
  "member_count": 1,
  "members_truncated": false,
  "delivery": null
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_result_not_found | 业务约束/对象状态，见操作说明 |
| 409 | result_answer_link_invalid | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | result_delivery_link_invalid | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E14.errors`，Swagger同操作 Responses 可直接展开。

<a id="e15"></a>

## E15 读取 Case Run 工件

`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 读取 Case Run 工件。

**输入：** 路径参数：`case_id`, `run_id`, `artifact_id`；无请求体。

**输出：** HTTP 200，`ArtifactContent`；完整字段和示例见Responses。

**结果：** 返回指定Case Run工件的元数据、正文和可用状态；完整性校验失败返回409。

**规则与限制：** 先 E12/E14 取得真实 artifact_id；父 Case/Run 必须匹配。返回 artifact 元数据和 content_json/content_text/availability；HTTP200 不保证正文可得。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e15) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| path | run_id | True | string (uuid) | null | 该父主体下的执行 UUID。 |
| path | artifact_id | True | string (uuid) | null | 工件 UUID，必须保持父主体/Run 归属。 |


无请求体。

响应类型：[ArtifactContent](schemas.md#artifactcontent)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "run_id": "00000000-0000-4000-8000-000000000004",
    "artifact_id": "00000000-0000-4000-8000-000000000009"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "artifact": {
    "id": "00000000-0000-4000-8000-000000000009",
    "run_id": "00000000-0000-4000-8000-000000000004",
    "material_state": "complete"
  },
  "content_json": null,
  "content_text": "合成示例报告：未形成可采用结论。",
  "availability": "available"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | run_artifact_not_found | 业务约束/对象状态，见操作说明 |
| 409 | artifact_integrity_invalid | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E15.errors`，Swagger同操作 Responses 可直接展开。

<a id="e16"></a>

## E16 读取 Case 非 Run 来源工件

`GET /api/v1/socai2/cases/{case_id}/artifacts/{artifact_id}`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 读取 Case 非 Run 来源工件。

**输入：** 路径参数：`case_id`, `artifact_id`；无请求体。

**输出：** HTTP 200，`ArtifactContent`；完整字段和示例见Responses。

**结果：** 返回案件非Run来源工件的元数据、正文和可用状态；不适用于Run工件。

**规则与限制：** 仅适用于 run_id 为空的本案来源工件。Run 工件必须用 E15，不能以这个路径替代。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e16) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| path | artifact_id | True | string (uuid) | null | 工件 UUID，必须保持父主体/Run 归属。 |


无请求体。

响应类型：[ArtifactContent](schemas.md#artifactcontent)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "artifact_id": "00000000-0000-4000-8000-000000000009"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "artifact": {
    "id": "00000000-0000-4000-8000-000000000009",
    "run_id": null,
    "material_state": "complete"
  },
  "content_json": null,
  "content_text": "合成示例报告：未形成可采用结论。",
  "availability": "available"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | run_artifact_not_found | 业务约束/对象状态，见操作说明 |
| 409 | artifact_integrity_invalid | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E16.errors`，Swagger同操作 Responses 可直接展开。

<a id="e17"></a>

## E17 Case 处理活动

`GET /api/v1/socai2/cases/{case_id}/activities`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** Case 处理活动。

**输入：** 路径参数：`case_id`；查询参数：`limit`, `offset`；无请求体。

**输出：** HTTP 200，`RecordPage`；完整字段和示例见Responses。

**结果：** 返回与案件、成员或显式关联事件匹配的处理活动、目标和分页信息。

**规则与限制：** 包括案件、成员和显式事件匹配活动，去重保留目标及前后值，按 next_offset 分页。活动不是模型推理过程。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e17) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| query | limit | False | integer; minimum=1; maximum=200 | 50 | 本次最多返回条数；不是总量。默认值及上限见字段约束。 |
| query | offset | False | integer; minimum=0; maximum=100000 | 0 | 分页偏移，沿 next_offset 继续。 |


无请求体。

响应类型：[RecordPage](schemas.md#recordpage)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "limit": 50,
    "offset": 0
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "items": [],
  "total": 0,
  "next_offset": null,
  "observed_at": "2026-11-12T08:00:00Z",
  "limitations": []
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | invalid_record_page | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E17.errors`，Swagger同操作 Responses 可直接展开。

<a id="e18"></a>

## E18 读取 Run 冻结的告警材料

`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/materials/{material_id}`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 读取 Run 冻结的告警材料。

**输入：** 路径参数：`case_id`, `run_id`, `material_id`；无请求体。

**输出：** HTTP 200，`FrozenAlertMaterial`；完整字段和示例见Responses。

**结果：** 返回该Run冻结的指定告警材料版本原始行，不替换为当前最新材料。

**规则与限制：** material_id 必须由该 Run 的冻结成员输入取得。返回 AlertMaterials 原始行，不是 ContentView 包装，没有 availability 字段；保留 material_state/retention。不能用当前材料代替。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e18) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| path | run_id | True | string (uuid) | null | 该父主体下的执行 UUID。 |
| path | material_id | True | string (uuid) | null | 材料版本 UUID；历史读取使用冻结版本。 |


无请求体。

响应类型：[FrozenAlertMaterial](schemas.md#frozenalertmaterial)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "run_id": "00000000-0000-4000-8000-000000000004",
    "material_id": "00000000-0000-4000-8000-000000000008"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "id": "00000000-0000-4000-8000-000000000008",
  "tenant_id": "00000000-0000-4000-8000-000000000010",
  "alert_id": "00000000-0000-4000-8000-000000000002",
  "revision": 1,
  "received_at": "2026-11-12T08:00:00Z",
  "source_version": null,
  "raw_text": null,
  "sha256": null,
  "raw_json": null,
  "ocsf_json": null,
  "enrichment": null,
  "detection": {},
  "source_scope": {},
  "retention": {},
  "material_state": "unavailable"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | frozen_material_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E18.errors`，Swagger同操作 Responses 可直接展开。

<a id="e19"></a>

## E19 Case 助手发送问题（预留）

`POST /api/v1/socai2/cases/{case_id}/ai/messages`

状态：**未实现**。分类：调查。

**实现状态：** 未实现

**用途：** Case 助手发送问题（预留）。

**输入：** 路径参数：`case_id`；JSON请求体：`AskCaseAI`，字段和必填要求见Request body。

**输出：** HTTP 501，`AIUnavailable`；完整字段和示例见Responses。

**结果：** 当前返回501，不执行问答、不调用模型，也不保存消息。

**规则与限制：** 通过请求校验后返回501，无模型调用和保存。现有 DTO 只有 operation_key、question、conversation_id；产品设计的 scope 尚无字段，额外字段会422。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 已确认返回501，功能未实现。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e19) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| question | 是 | string; minLength=1; maxLength=4000 | 无（可空不等于可省略） | 用户明确发送的问题文本；当前Q接口未实现。 |
| conversation_id | 否 | string (uuid) / null | 无（可空不等于可省略） | 可选会话UUID；当前无正式对话读写。 |


响应类型：[AIUnavailable](schemas.md#aiunavailable)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "question": "这些告警有哪些共同依据？",
    "conversation_id": null
  }
}
```

输出示例（HTTP 501）：

```json
{
  "detail": {
    "code": "case_ai_not_implemented",
    "status": "not_implemented",
    "message": "AI问答功能暂未实现；本次请求未执行、保存或采用任何结果。"
  }
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 501 | case_ai_not_implemented | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E19.errors`，Swagger同操作 Responses 可直接展开。

<a id="e20"></a>

## E20 保存助手回答（预留）

`POST /api/v1/socai2/cases/{case_id}/ai/messages/{message_id}/save`

状态：**未实现**。分类：调查。

**实现状态：** 未实现

**用途：** 保存助手回答（预留）。

**输入：** 路径参数：`case_id`, `message_id`；JSON请求体：`SaveCaseAIAnswer`，字段和必填要求见Request body。

**输出：** HTTP 501，`AIUnavailable`；完整字段和示例见Responses。

**结果：** 当前返回501，不保存回答，也不产生正式调查结果。

**规则与限制：** 通过请求校验后返回501，没有冻结或正式结果。title/conclusion 是待保存文本，不触发执行；当前不能使用。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 已确认返回501，功能未实现。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e20) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| path | message_id | True | string (uuid) | null | message_id |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| title | 是 | string; minLength=1; maxLength=200 | 无（可空不等于可省略） | 显示标题；写入必须非空，长度约束见Schema。 |
| conclusion | 是 | string; minLength=1; maxLength=20000 | 无（可空不等于可省略） | 本环节结论正文；null可能未交付/拒收，不补造。 |


响应类型：[AIUnavailable](schemas.md#aiunavailable)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "message_id": "00000000-0000-4000-8000-000000000012"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "title": "待保存的回答",
    "conclusion": "用户确认保存的正文（接口当前501）"
  }
}
```

输出示例（HTTP 501）：

```json
{
  "detail": {
    "code": "case_ai_not_implemented",
    "status": "not_implemented",
    "message": "AI问答功能暂未实现；本次请求未执行、保存或采用任何结果。"
  }
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 501 | case_ai_not_implemented | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E20.errors`，Swagger同操作 Responses 可直接展开。

<a id="e21"></a>

## E21 显式采用其他结果（预留）

`POST /api/v1/socai2/cases/{case_id}/results/{result_id}/adopt`

状态：**未实现**。分类：调查。

**实现状态：** 未实现

**用途：** 显式采用其他结果（预留）。

**输入：** 路径参数：`case_id`, `result_id`；JSON请求体：`AdoptCaseAIResult`，字段和必填要求见Request body。

**输出：** HTTP 501，`AIUnavailable`；完整字段和示例见Responses。

**结果：** 当前返回501，不变更案件当前采用判断。

**规则与限制：** 通过请求校验后返回501。D03 要求理由和覆盖确认，但现有 DTO 只有 operation_key/expected_scope_revision，reason 尚未实现，不能发送虚构参数。已有基础流程自动采用与本操作不同。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 已确认返回501，功能未实现。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e21) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| path | result_id | True | string (uuid) | null | 同案已保存正式结果 UUID。 |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_scope_revision | 是 | integer; minimum=0.0 | 无（可空不等于可省略） | 读 Case 详情获得的当前范围版本；不匹配返回409。 |


响应类型：[AIUnavailable](schemas.md#aiunavailable)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "result_id": "00000000-0000-4000-8000-000000000005"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "expected_scope_revision": 1
  }
}
```

输出示例（HTTP 501）：

```json
{
  "detail": {
    "code": "case_ai_not_implemented",
    "status": "not_implemented",
    "message": "AI问答功能暂未实现；本次请求未执行、保存或采用任何结果。"
  }
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 501 | case_ai_not_implemented | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E21.errors`，Swagger同操作 Responses 可直接展开。

<a id="e22"></a>

## E22 告警分诊目录

`GET /api/v1/socai2/alerts/{alert_id}/analysis`

状态：**已实现**。分类：告警。

**实现状态：** 已实现

**用途：** 告警分诊目录。

**输入：** 路径参数：`alert_id`；查询参数：`limit`, `before_run_id`；无请求体。

**输出：** HTTP 200，`StagePage`；完整字段和示例见Responses。

**结果：** 返回告警当前分诊及历史执行目录；失败尝试和当前有效分诊分别保留。

**规则与限制：** current 是当前指针对应分诊；entries 是历史尝试。失败尝试不能覆盖有效旧结论。分页使用 next_before_run_id。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e22) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | alert_id | True | string (uuid) | null | 告警 UUID。 |
| query | limit | False | integer; minimum=1; maximum=50 | 20 | 本次最多返回条数；不是总量。默认值及上限见字段约束。 |
| query | before_run_id | False | string (uuid) / null | null | 沿上页 next_before_run_id 翻页。 |


无请求体。

响应类型：[StagePage](schemas.md#stagepage)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "alert_id": "00000000-0000-4000-8000-000000000002",
    "limit": 20
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "subject_id": "00000000-0000-4000-8000-000000000002",
  "kind": "alert_basic",
  "current_pointer_id": null,
  "current": null,
  "current_unavailable_reason": null,
  "entries": [],
  "next_before_run_id": null
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | invalid_stage_history_limit | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | stage_subject_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E22.errors`，Swagger同操作 Responses 可直接展开。

<a id="e23"></a>

## E23 事件诊断目录

`GET /api/v1/socai2/incidents/{incident_id}/analysis`

状态：**已实现**。分类：事件。

**实现状态：** 已实现

**用途：** 事件诊断目录。

**输入：** 路径参数：`incident_id`；查询参数：`limit`, `before_run_id`；无请求体。

**输出：** HTTP 200，`StagePage`；完整字段和示例见Responses。

**结果：** 返回事件当前诊断及历史执行目录，保留交付、成员覆盖和待核内容。

**规则与限制：** 区分当前诊断、最近尝试及 partial_analysis；分页使用 next_before_run_id。诊断交付完整性、review_items、成员覆盖不混为一个成功状态。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e23) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | incident_id | True | string (uuid) | null | 事件 UUID。 |
| query | limit | False | integer; minimum=1; maximum=50 | 20 | 本次最多返回条数；不是总量。默认值及上限见字段约束。 |
| query | before_run_id | False | string (uuid) / null | null | 沿上页 next_before_run_id 翻页。 |


无请求体。

响应类型：[StagePage](schemas.md#stagepage)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "incident_id": "00000000-0000-4000-8000-000000000003",
    "limit": 20
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "subject_id": "00000000-0000-4000-8000-000000000003",
  "kind": "incident_diagnosis",
  "current_pointer_id": null,
  "current": null,
  "current_unavailable_reason": null,
  "entries": [],
  "next_before_run_id": null
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | invalid_stage_history_limit | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | stage_subject_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E23.errors`，Swagger同操作 Responses 可直接展开。

<a id="e24"></a>

## E24 指定告警 A Run

`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`

状态：**已实现**。分类：告警。

**实现状态：** 已实现

**用途：** 指定告警 A Run。

**输入：** 路径参数：`alert_id`, `run_id`；无请求体。

**输出：** HTTP 200，`StageEntry`；完整字段和示例见Responses。

**结果：** 返回指定告警分诊Run及其分诊结果、有效性和输入是否变化。

**规则与限制：** 用目录返回 Run ID。检查 freshness、is_current_pointer、valid_for_current_input。TriageView.confidence 为0..1；SubjectView.triage.confidence_percent 为百分数，不能二次乘100。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e24) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | alert_id | True | string (uuid) | null | 告警 UUID。 |
| path | run_id | True | string (uuid) | null | 该父主体下的执行 UUID。 |


无请求体。

响应类型：[StageEntry](schemas.md#stageentry)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "alert_id": "00000000-0000-4000-8000-000000000002",
    "run_id": "00000000-0000-4000-8000-000000000004"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "run": {
    "id": "00000000-0000-4000-8000-000000000004",
    "kind": "alert_basic",
    "state": "pending_update",
    "requested_at": "2026-11-12T08:00:00Z",
    "requested_by": null,
    "started_at": null,
    "ended_at": null,
    "executor_version": null,
    "input_artifact_id": null,
    "stop_reason": null,
    "delivery_state": "none"
  },
  "freshness": "unavailable",
  "is_current_pointer": false,
  "valid_for_current_input": false,
  "result": null,
  "explanation": null,
  "partial_analysis": null
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | stage_run_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E24.errors`，Swagger同操作 Responses 可直接展开。

<a id="e25"></a>

## E25 指定事件 I Run

`GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}`

状态：**已实现**。分类：事件。

**实现状态：** 已实现

**用途：** 指定事件 I Run。

**输入：** 路径参数：`incident_id`, `run_id`；无请求体。

**输出：** HTTP 200，`StageEntry`；完整字段和示例见Responses。

**结果：** 返回指定事件诊断Run及其诊断结果、交付状态和待核内容。

**规则与限制：** 读 diagnosis、open_questions、交付与待复核字段；执行过程需 E32。保存/格式通过不代表正文质量通过。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e25) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | incident_id | True | string (uuid) | null | 事件 UUID。 |
| path | run_id | True | string (uuid) | null | 该父主体下的执行 UUID。 |


无请求体。

响应类型：[StageEntry](schemas.md#stageentry)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "incident_id": "00000000-0000-4000-8000-000000000003",
    "run_id": "00000000-0000-4000-8000-000000000004"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "run": {
    "id": "00000000-0000-4000-8000-000000000004",
    "kind": "incident_diagnosis",
    "state": "pending_update",
    "requested_at": "2026-11-12T08:00:00Z",
    "requested_by": null,
    "started_at": null,
    "ended_at": null,
    "executor_version": null,
    "input_artifact_id": null,
    "stop_reason": null,
    "delivery_state": "none"
  },
  "freshness": "unavailable",
  "is_current_pointer": false,
  "valid_for_current_input": false,
  "result": null,
  "explanation": null,
  "partial_analysis": null
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | stage_run_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E25.errors`，Swagger同操作 Responses 可直接展开。

<a id="e26"></a>

## E26 告警列表

`GET /api/v1/socai2/alerts`

状态：**已实现**。分类：告警。

**实现状态：** 已实现

**用途：** 告警列表。

**输入：** 查询参数：`limit`, `before_id`, `cursor`, `q`, `severity`, `handling_status`, `owner_id`, `assignment_state`, `time_from`, `time_to`, `sort_by`, `sort_order`；无请求体。

**输出：** HTTP 200，`SubjectPage`；完整字段和示例见Responses。

**结果：** 按条件和顺序返回告警列表；filtered_total为筛选总数，next_cursor用于下一页，total/overall_stats保持租户整体统计。

**规则与限制：** q按标题字面包含或精确UUID，支持severity、handling_status（new/in_progress/completed/unknown）、owner_id、assignment_state。time_from/time_to按真实event_time，缺失不以入库时间补齐。sort_by=ingested_at（默认）/event_time/severity。filtered_total为全部筛选命中数；total和overall_stats仍为租户整体。无新增筛选/排序时旧before_id/next_before_id继续可用；新查询用cursor，before_id与cursor或新条件混用返回422。时间必须带时区，区间为[time_from,time_to)，允许单边；两端同时传时起点必须早于终点。等级info<low<medium<high<critical，未知值总在最后；同值按同方向UUID排序。每页1–50条，默认20；sort_order默认desc。改变筛选或排序后清空cursor；下一页原样传next_cursor，不自行解析。每次请求为当前只读快照，跨请求有业务更新时不是冻结导出。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机真实PostgreSQL和TCP完成三类列表117次请求：筛选、九种排序双向分页、旧游标兼容及查询前后行不变；21发布读回见本批回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e26) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| query | limit | False | integer; minimum=1; maximum=50 | 20 | 本次最多返回条数；不是总量。默认值及上限见字段约束。 |
| query | before_id | False | string (uuid) / null | null | 仅无新增筛选/排序的旧调用沿next_before_id翻页；不与cursor混用。 |
| query | cursor | False | string; maxLength=1024 / null | null | 使用服务上一页 next_cursor；改变筛选条件后清空。 |
| query | q | False | string; maxLength=200 / null | null | 标题字面包含或精确UUID搜索；%和_按普通字符处理。 |
| query | severity | False | [Severity](schemas.md#severity) / null | null | 严重度枚举；null为未知，不强行补默认等级。 |
| query | handling_status | False | [AlertStatus](schemas.md#alertstatus) / null | null | 主体业务处理状态，与Run执行状态分开。 |
| query | owner_id | False | string (uuid) / null | null | 负责人用户UUID；人员目录由业务后端负责。 |
| query | assignment_state | False | [AssignmentState](schemas.md#assignmentstate) / null | null | 分配状态，unresolved不等于unassigned。 |
| query | time_from | False | string (date-time) / null | null | 带时区的起点，包含；告警按event_time，事件至少一条成员event_time命中，Case按business_updated_at。 |
| query | time_to | False | string (date-time) / null | null | 带时区的终点，不包含；两端同时传时必须晚于time_from。 |
| query | sort_by | False | string ingested_at, event_time, severity / null | null | 服务排序字段，可选值见本接口枚举；记录排序字段缺值时置后，同值按UUID排序；非法sort_by返回422。 |
| query | sort_order | False | string asc, desc / null | null | asc升序或desc降序，默认desc。 |


无请求体。

响应类型：[SubjectPage](schemas.md#subjectpage)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "limit": 20,
    "q": "需要核实",
    "sort_by": "severity",
    "sort_order": "desc",
    "time_from": "2026-11-10T00:00:00Z",
    "time_to": "2026-11-11T00:00:00Z"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "kind": "alerts",
  "items": [],
  "total": 0,
  "next_before_id": null,
  "overall_stats": {
    "total": 0,
    "new": 0,
    "in_progress": 0,
    "unknown": 0,
    "high_severity": 0,
    "investigating": 0
  },
  "observed_at": "2026-11-12T08:00:00Z",
  "filtered_total": 0,
  "next_cursor": null
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | invalid_time_window | 起点不早于终点；无时区、非法排序或枚举同样422；参数修正前不重试。 |
| 422 | mixed_pagination | before_id不能与cursor、新筛选或排序混用；参数修正前不重试。 |
| 422 | invalid_list_cursor | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | list_cursor_filters_changed | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | page_subject_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E26.errors`，Swagger同操作 Responses 可直接展开。

<a id="e27"></a>

## E27 事件列表

`GET /api/v1/socai2/incidents`

状态：**已实现**。分类：事件。

**实现状态：** 已实现

**用途：** 事件列表。

**输入：** 查询参数：`limit`, `before_id`, `cursor`, `q`, `severity`, `handling_status`, `owner_id`, `assignment_state`, `time_from`, `time_to`, `sort_by`, `sort_order`；无请求体。

**输出：** HTTP 200，`SubjectPage`；完整字段和示例见Responses。

**结果：** 按条件和顺序返回事件列表；filtered_total为筛选总数，next_cursor用于下一页，total/overall_stats保持租户整体统计。

**规则与限制：** q按标题字面包含或精确UUID，支持severity、handling_status（new/in_progress/resolved/unknown）、owner_id、assignment_state。severity为人工覆盖优先、否则成员最大等级；time_from/time_to要求至少一条成员告警真实event_time处于该区间，不能仅用事件首尾跨越判断。sort_by=created_at（默认）/last_activity_at（成员最晚真实发生时间）/severity。filtered_total为全部筛选命中数；total和overall_stats仍为租户整体。无新增筛选/排序时旧before_id/next_before_id继续可用；新查询用cursor，before_id与cursor或新条件混用返回422。时间必须带时区，区间为[time_from,time_to)，允许单边；两端同时传时起点必须早于终点。等级info<low<medium<high<critical，未知值总在最后；同值按同方向UUID排序。每页1–50条，默认20；sort_order默认desc。改变筛选或排序后清空cursor；下一页原样传next_cursor，不自行解析。每次请求为当前只读快照，跨请求有业务更新时不是冻结导出。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机真实PostgreSQL和TCP完成三类列表117次请求：筛选、九种排序双向分页、旧游标兼容及查询前后行不变；21发布读回见本批回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e27) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| query | limit | False | integer; minimum=1; maximum=50 | 20 | 本次最多返回条数；不是总量。默认值及上限见字段约束。 |
| query | before_id | False | string (uuid) / null | null | 仅无新增筛选/排序的旧调用沿next_before_id翻页；不与cursor混用。 |
| query | cursor | False | string; maxLength=1024 / null | null | 使用服务上一页 next_cursor；改变筛选条件后清空。 |
| query | q | False | string; maxLength=200 / null | null | 标题字面包含或精确UUID搜索；%和_按普通字符处理。 |
| query | severity | False | [Severity](schemas.md#severity) / null | null | 严重度枚举；null为未知，不强行补默认等级。 |
| query | handling_status | False | [WorkStatus](schemas.md#workstatus) / null | null | 主体业务处理状态，与Run执行状态分开。 |
| query | owner_id | False | string (uuid) / null | null | 负责人用户UUID；人员目录由业务后端负责。 |
| query | assignment_state | False | [AssignmentState](schemas.md#assignmentstate) / null | null | 分配状态，unresolved不等于unassigned。 |
| query | time_from | False | string (date-time) / null | null | 带时区的起点，包含；告警按event_time，事件至少一条成员event_time命中，Case按business_updated_at。 |
| query | time_to | False | string (date-time) / null | null | 带时区的终点，不包含；两端同时传时必须晚于time_from。 |
| query | sort_by | False | string created_at, last_activity_at, severity / null | null | 服务排序字段，可选值见本接口枚举；记录排序字段缺值时置后，同值按UUID排序；非法sort_by返回422。 |
| query | sort_order | False | string asc, desc / null | null | asc升序或desc降序，默认desc。 |


无请求体。

响应类型：[SubjectPage](schemas.md#subjectpage)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "limit": 20,
    "q": "需要核实",
    "sort_by": "severity",
    "sort_order": "desc",
    "time_from": "2026-11-10T00:00:00Z",
    "time_to": "2026-11-11T00:00:00Z"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "kind": "incidents",
  "items": [],
  "total": 0,
  "next_before_id": null,
  "overall_stats": {
    "total": 0,
    "new": 0,
    "in_progress": 0,
    "unknown": 0,
    "active": 0,
    "unassigned": 0,
    "grouped_alert_count": 0,
    "new_alerts_24h": 0,
    "high_severity": 0
  },
  "observed_at": "2026-11-12T08:00:00Z",
  "filtered_total": 0,
  "next_cursor": null
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | invalid_time_window | 起点不早于终点；无时区、非法排序或枚举同样422；参数修正前不重试。 |
| 422 | mixed_pagination | before_id不能与cursor、新筛选或排序混用；参数修正前不重试。 |
| 422 | invalid_list_cursor | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | list_cursor_filters_changed | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | page_subject_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E27.errors`，Swagger同操作 Responses 可直接展开。

<a id="e28"></a>

## E28 告警详情

`GET /api/v1/socai2/alerts/{alert_id}`

状态：**已实现**。分类：告警。

**实现状态：** 已实现

**用途：** 告警详情。

**输入：** 路径参数：`alert_id`；无请求体。

**输出：** HTTP 200，`SubjectView`；完整字段和示例见Responses。

**结果：** 返回告警事实、当前材料摘要、分诊、已存人工反馈及后续读取地址。

**规则与限制：** 返回 facts、derived、material、triage、feedback 及 analysis_url/section_urls。反馈读取不代表人工判定写入口已实现；发生时间缺失不以入库时间替代。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e28) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | alert_id | True | string (uuid) | null | 告警 UUID。 |


无请求体。

响应类型：[SubjectView](schemas.md#subjectview)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "alert_id": "00000000-0000-4000-8000-000000000002"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "kind": "alerts",
  "facts": {
    "id": "00000000-0000-4000-8000-000000000002",
    "source_namespace": "example",
    "title": "合成示例：核查异常登录",
    "description": null,
    "owner_id": null,
    "assignment_state": "unassigned",
    "owner_source_value": null,
    "assigned_at": null,
    "tags": [],
    "priority_value": null,
    "priority_state": "not_provided",
    "priority_source": null,
    "priority_basis": null,
    "business_updated_at": "2026-11-12T08:00:00Z",
    "reopened_at": null,
    "row_version": 1,
    "source_alert_id": null,
    "vendor_alert_id": null,
    "connector_id": null,
    "connector_type": null,
    "original_vendor": null,
    "category": null,
    "severity": null,
    "severity_raw": null,
    "event_time": null,
    "event_time_source": "unknown",
    "first_seen_at": null,
    "last_seen_at": null,
    "ingested_at": "2026-11-12T08:00:00Z",
    "source_updated_at": "2026-11-12T08:00:00Z",
    "handling_status": "new",
    "disposition": null,
    "closed_at": null,
    "closed_by": null,
    "latest_material_id": null,
    "latest_triage_id": null,
    "latest_feedback_id": null,
    "latest_explanation_id": null
  },
  "owner_name": null,
  "owner_resolution": "unassigned",
  "derived": {
    "severity_group": null,
    "false_positive": null,
    "member_count": null,
    "first_activity_at": null,
    "last_activity_at": null,
    "unknown_event_time_count": null,
    "unknown_severity_count": null,
    "severity_auto": null,
    "severity_effective": null,
    "severity_source": null,
    "updated_at": null,
    "tactics": [],
    "tactic_counting_note": "示例",
    "object_count": 0,
    "baseline_execution_counts": {
      "running": 0,
      "unknown": 0
    }
  },
  "material": null,
  "triage": null,
  "feedback": null,
  "analysis_url": "/api/v1/socai2/alerts/00000000-0000-4000-8000-000000000002/analysis",
  "section_urls": {
    "incidents": "/api/v1/socai2/alerts/00000000-0000-4000-8000-000000000002/records/incidents",
    "objects": "/api/v1/socai2/alerts/00000000-0000-4000-8000-000000000002/records/objects",
    "sources": "/api/v1/socai2/alerts/00000000-0000-4000-8000-000000000002/records/sources",
    "source_artifacts": "/api/v1/socai2/alerts/00000000-0000-4000-8000-000000000002/records/source_artifacts",
    "assets": "/api/v1/socai2/alerts/00000000-0000-4000-8000-000000000002/records/assets",
    "cases": "/api/v1/socai2/alerts/00000000-0000-4000-8000-000000000002/records/cases",
    "comments": "/api/v1/socai2/alerts/00000000-0000-4000-8000-000000000002/records/comments",
    "activities": "/api/v1/socai2/alerts/00000000-0000-4000-8000-000000000002/records/activities",
    "related_alerts": "/api/v1/socai2/alerts/00000000-0000-4000-8000-000000000002/records/related_alerts",
    "responses": "/api/v1/socai2/alerts/00000000-0000-4000-8000-000000000002/records/responses"
  }
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | page_subject_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E28.errors`，Swagger同操作 Responses 可直接展开。

<a id="e29"></a>

## E29 事件详情

`GET /api/v1/socai2/incidents/{incident_id}`

状态：**已实现**。分类：事件。

**实现状态：** 已实现

**用途：** 事件详情。

**输入：** 路径参数：`incident_id`；无请求体。

**输出：** HTTP 200，`SubjectView`；完整字段和示例见Responses。

**结果：** 返回事件事实、成员和对象汇总及后续读取地址；诊断和成员明细使用对应读取接口。

**规则与限制：** 返回主体事实、derived 及目录链接；诊断另取 E23，成员/对象另取 E30。资产完整资料由业务后端提供。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e29) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | incident_id | True | string (uuid) | null | 事件 UUID。 |


无请求体。

响应类型：[SubjectView](schemas.md#subjectview)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "incident_id": "00000000-0000-4000-8000-000000000003"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "kind": "incidents",
  "facts": {
    "id": "00000000-0000-4000-8000-000000000003",
    "source_namespace": "example",
    "title": "合成示例：核查异常登录",
    "description": null,
    "owner_id": null,
    "assignment_state": "unassigned",
    "owner_source_value": null,
    "assigned_at": null,
    "tags": [],
    "priority_value": null,
    "priority_state": "not_provided",
    "priority_source": null,
    "priority_basis": null,
    "business_updated_at": "2026-11-12T08:00:00Z",
    "reopened_at": null,
    "row_version": 1,
    "source_incident_id": "示例",
    "handling_status": "new",
    "severity_override": null,
    "severity_override_reason": null,
    "severity_override_at": null,
    "severity_override_by": null,
    "resolution_note": null,
    "resolved_at": null,
    "resolved_by": null,
    "created_at": "2026-11-12T08:00:00Z",
    "latest_diagnosis_id": null
  },
  "owner_name": null,
  "owner_resolution": "unassigned",
  "derived": {
    "severity_group": null,
    "false_positive": null,
    "member_count": null,
    "first_activity_at": null,
    "last_activity_at": null,
    "unknown_event_time_count": null,
    "unknown_severity_count": null,
    "severity_auto": null,
    "severity_effective": null,
    "severity_source": null,
    "updated_at": null,
    "tactics": [],
    "tactic_counting_note": "示例",
    "object_count": 0,
    "baseline_execution_counts": {
      "running": 0,
      "unknown": 0
    }
  },
  "material": null,
  "triage": null,
  "feedback": null,
  "analysis_url": "/api/v1/socai2/incidents/00000000-0000-4000-8000-000000000003/analysis",
  "section_urls": {
    "members": "/api/v1/socai2/incidents/00000000-0000-4000-8000-000000000003/records/members",
    "objects": "/api/v1/socai2/incidents/00000000-0000-4000-8000-000000000003/records/objects",
    "sources": "/api/v1/socai2/incidents/00000000-0000-4000-8000-000000000003/records/sources",
    "source_artifacts": "/api/v1/socai2/incidents/00000000-0000-4000-8000-000000000003/records/source_artifacts",
    "assets": "/api/v1/socai2/incidents/00000000-0000-4000-8000-000000000003/records/assets",
    "cases": "/api/v1/socai2/incidents/00000000-0000-4000-8000-000000000003/records/cases",
    "comments": "/api/v1/socai2/incidents/00000000-0000-4000-8000-000000000003/records/comments",
    "activities": "/api/v1/socai2/incidents/00000000-0000-4000-8000-000000000003/records/activities",
    "related_alerts": "/api/v1/socai2/incidents/00000000-0000-4000-8000-000000000003/records/related_alerts",
    "responses": "/api/v1/socai2/incidents/00000000-0000-4000-8000-000000000003/records/responses"
  }
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | page_subject_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E29.errors`，Swagger同操作 Responses 可直接展开。

<a id="e30"></a>

## E30 主体分区记录

`GET /api/v1/socai2/{subject}/{identity}/records/{section}`

状态：**已实现**。分类：告警、事件。

**实现状态：** 已实现

**用途：** 主体分区记录。

**输入：** 路径参数：`subject`, `identity`, `section`；查询参数：`limit`, `offset`；无请求体。

**输出：** HTTP 200，`RecordPage`；完整字段和示例见Responses。

**结果：** 返回所选分区的记录、总数和下一页偏移；资产分区返回对象与真实库存资产的匹配记录及资产标签。

**规则与限制：** subject 只能 alerts/incidents；section 参见分区说明。members 仅事件，incidents 仅告警；其他错误组合404。items 随 section 变化，不能固定为一种记录。next_offset=null 结束；related_alerts 只是同类型/同命名空间/同对象键匹配，不是相似历史反馈或图探索服务。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e30) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | subject | True | string alerts, incidents | null | alerts 或 incidents，不能传 cases。 |
| path | identity | True | string (uuid) | null | subject 对应的告警或事件 UUID。 |
| path | section | True | string members, incidents, objects, sources, source_artifacts, assets, cases, comments, activities, related_alerts, responses | null | 记录分区；members仅事件、incidents仅告警。见分区表。 |
| query | limit | False | integer; minimum=1; maximum=200 | 50 | 本次最多返回条数；不是总量。默认值及上限见字段约束。 |
| query | offset | False | integer; minimum=0; maximum=100000 | 0 | 分页偏移，沿 next_offset 继续。 |


无请求体。

响应类型：[RecordPage](schemas.md#recordpage)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "subject": "alerts",
    "identity": "00000000-0000-4000-8000-000000000009",
    "section": "objects",
    "limit": 50,
    "offset": 0
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "items": [],
  "total": 0,
  "next_offset": null,
  "observed_at": "2026-11-12T08:00:00Z",
  "limitations": []
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | invalid_record_page | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | page_subject_not_found | 业务约束/对象状态，见操作说明 |
| 404 | section_not_applicable | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E30.errors`，Swagger同操作 Responses 可直接展开。

<a id="e31"></a>

## E31 告警材料正文

`GET /api/v1/socai2/alerts/{alert_id}/materials/{material_id}`

状态：**已实现**。分类：告警。

**实现状态：** 已实现

**用途：** 告警材料正文。

**输入：** 路径参数：`alert_id`, `material_id`；无请求体。

**输出：** HTTP 200，`ContentView`；完整字段和示例见Responses。

**结果：** 返回指定告警材料版本的原始JSON、标准化记录、富化内容及原始文本，并说明正文可用性。

**规则与限制：** 从 E28 material.id 取得版本；content_json 包含 raw_json/ocsf_json/enrichment，content_text 为 raw_text。availability 限制与缺正文必须保留，不能展示空JSON当无异常。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e31) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | alert_id | True | string (uuid) | null | 告警 UUID。 |
| path | material_id | True | string (uuid) | null | 材料版本 UUID；历史读取使用冻结版本。 |


无请求体。

响应类型：[ContentView](schemas.md#contentview)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "alert_id": "00000000-0000-4000-8000-000000000002",
    "material_id": "00000000-0000-4000-8000-000000000008"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "metadata": {
    "id": "00000000-0000-4000-8000-000000000008",
    "alert_id": "00000000-0000-4000-8000-000000000002",
    "revision": 1,
    "material_state": "complete"
  },
  "availability": "available",
  "content_json": {
    "raw_json": {
      "example": true
    },
    "ocsf_json": null,
    "enrichment": null
  },
  "content_text": "合成原始材料示例"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | alert_material_not_found | 业务约束/对象状态，见操作说明 |
| 404 | material_subject_invalid | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E31.errors`，Swagger同操作 Responses 可直接展开。

<a id="e32"></a>

## E32 A/I Run 步骤及工件目录

`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace`

状态：**已实现**。分类：告警、事件。

**实现状态：** 已实现

**用途：** A/I Run 步骤及工件目录。

**输入：** 路径参数：`subject`, `identity`, `run_id`；无请求体。

**输出：** HTTP 200，`TraceView`；完整字段和示例见Responses。

**结果：** 返回指定告警/事件Run的原始执行记录、步骤、工件目录、用量及截断标志。

**规则与限制：** subject=alerts/incidents，identity 为对应主体 UUID。返回 run、steps、artifacts、用量及截断标志。仅查既有记录，读取不重新执行；正文按 E33。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e32) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | subject | True | string alerts, incidents | null | alerts 或 incidents，不能传 cases。 |
| path | identity | True | string (uuid) | null | subject 对应的告警或事件 UUID。 |
| path | run_id | True | string (uuid) | null | 该父主体下的执行 UUID。 |


无请求体。

响应类型：[TraceView](schemas.md#traceview)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "subject": "alerts",
    "identity": "00000000-0000-4000-8000-000000000009",
    "run_id": "00000000-0000-4000-8000-000000000004"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "run": {},
  "steps": [],
  "steps_total": 0,
  "steps_truncated": false,
  "artifacts": [],
  "artifacts_total": 0,
  "artifacts_truncated": false,
  "usage": {},
  "tool_calls": 0,
  "duration_seconds": null,
  "last_recorded_at": "2026-11-12T08:00:00Z",
  "observed_at": "2026-11-12T08:00:00Z"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | stage_run_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E32.errors`，Swagger同操作 Responses 可直接展开。

<a id="e33"></a>

## E33 A/I Run 工件正文

`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`

状态：**已实现**。分类：告警、事件。

**实现状态：** 已实现

**用途：** A/I Run 工件正文。

**输入：** 路径参数：`subject`, `identity`, `run_id`, `artifact_id`；无请求体。

**输出：** HTTP 200，`ContentView`；完整字段和示例见Responses。

**结果：** 返回告警/事件Run工件的元数据、正文及可用状态；内容完整性异常时正文为空并返回对应availability。

**规则与限制：** 父主体及 Run 必须匹配。返回 metadata/content_json/content_text/availability；metadata 与 Case E15 的 artifact 字段不同。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e33) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | subject | True | string alerts, incidents | null | alerts 或 incidents，不能传 cases。 |
| path | identity | True | string (uuid) | null | subject 对应的告警或事件 UUID。 |
| path | run_id | True | string (uuid) | null | 该父主体下的执行 UUID。 |
| path | artifact_id | True | string (uuid) | null | 工件 UUID，必须保持父主体/Run 归属。 |


无请求体。

响应类型：[ContentView](schemas.md#contentview)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "subject": "alerts",
    "identity": "00000000-0000-4000-8000-000000000009",
    "run_id": "00000000-0000-4000-8000-000000000004",
    "artifact_id": "00000000-0000-4000-8000-000000000009"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "metadata": {
    "id": "00000000-0000-4000-8000-000000000009",
    "run_id": "00000000-0000-4000-8000-000000000004",
    "material_state": "complete"
  },
  "availability": "available",
  "content_json": null,
  "content_text": "合成示例原文"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | stage_artifact_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E33.errors`，Swagger同操作 Responses 可直接展开。

<a id="e34"></a>

## E34 告警非 Run 来源工件

`GET /api/v1/socai2/alerts/{identity}/artifacts/{artifact_id}`

状态：**已实现**。分类：告警。

**实现状态：** 已实现

**用途：** 告警非 Run 来源工件。

**输入：** 路径参数：`identity`, `artifact_id`；无请求体。

**输出：** HTTP 200，`ContentView`；完整字段和示例见Responses。

**结果：** 返回告警非Run来源工件的元数据、正文及可用状态。

**规则与限制：** 读取本告警 run_id 为空的来源工件，artifact_id 可由 source_artifacts 记录取得。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e34) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | identity | True | string (uuid) | null | subject 对应的告警或事件 UUID。 |
| path | artifact_id | True | string (uuid) | null | 工件 UUID，必须保持父主体/Run 归属。 |


无请求体。

响应类型：[ContentView](schemas.md#contentview)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "identity": "00000000-0000-4000-8000-000000000009",
    "artifact_id": "00000000-0000-4000-8000-000000000009"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "metadata": {
    "id": "00000000-0000-4000-8000-000000000009",
    "run_id": null,
    "material_state": "complete"
  },
  "availability": "available",
  "content_json": null,
  "content_text": "合成示例原文"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | stage_artifact_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E34.errors`，Swagger同操作 Responses 可直接展开。

<a id="e35"></a>

## E35 事件非 Run 来源工件

`GET /api/v1/socai2/incidents/{identity}/artifacts/{artifact_id}`

状态：**已实现**。分类：事件。

**实现状态：** 已实现

**用途：** 事件非 Run 来源工件。

**输入：** 路径参数：`identity`, `artifact_id`；无请求体。

**输出：** HTTP 200，`ContentView`；完整字段和示例见Responses。

**结果：** 返回事件非Run来源工件的元数据、正文及可用状态。

**规则与限制：** 读取本事件 run_id 为空的来源工件，不能替代运行工件路径。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e35) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | identity | True | string (uuid) | null | subject 对应的告警或事件 UUID。 |
| path | artifact_id | True | string (uuid) | null | 工件 UUID，必须保持父主体/Run 归属。 |


无请求体。

响应类型：[ContentView](schemas.md#contentview)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "identity": "00000000-0000-4000-8000-000000000009",
    "artifact_id": "00000000-0000-4000-8000-000000000009"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "metadata": {
    "id": "00000000-0000-4000-8000-000000000009",
    "run_id": null,
    "material_state": "complete"
  },
  "availability": "available",
  "content_json": null,
  "content_text": "合成示例原文"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | stage_artifact_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E35.errors`，Swagger同操作 Responses 可直接展开。

<a id="e36"></a>

## E36 手动告警分诊

`POST /api/v1/socai2/alerts/{alert_id}/analyze`

状态：**已实现**。分类：告警。

**实现状态：** 已实现

**用途：** 手动告警分诊。

**输入：** 路径参数：`alert_id`；JSON请求体：`ExecuteStage`，字段和必填要求见Request body。

**输出：** HTTP 200，`StageEntry`；完整字段和示例见Responses。

**结果：** 发起告警分诊并返回Run结果；21新独立正式入口已挂载并启用，调用会执行当前模型流程。

**规则与限制：** 21新独立正式服务18024已挂载/开启，读写目标aisoc。operation_key 同租户稳定映射 Run；执行异常先 E24 查询，异常回执含 run_id；其他部署未启用时503仅返回socai2_stage_execution_not_enabled。调用会执行模型，本轮入口验收未派发真实模型，结论质量以独立验收为准。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库的执行、保存和读取通过；模型/外部查询为替身，真实模型效果未据此验收。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e36) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | alert_id | True | string (uuid) | null | 告警 UUID。 |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |


响应类型：[StageEntry](schemas.md#stageentry)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "alert_id": "00000000-0000-4000-8000-000000000002"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011"
  }
}
```

输出示例（HTTP 200）：

```json
{
  "run": {
    "id": "00000000-0000-4000-8000-000000000004",
    "kind": "alert_basic",
    "state": "failed",
    "requested_at": "2026-11-12T08:00:00Z",
    "requested_by": null,
    "started_at": "2026-11-12T08:00:00Z",
    "ended_at": "2026-11-12T08:00:00Z",
    "executor_version": null,
    "input_artifact_id": null,
    "stop_reason": "example_unavailable",
    "delivery_state": "none"
  },
  "freshness": "unavailable",
  "is_current_pointer": false,
  "valid_for_current_input": false,
  "result": null,
  "explanation": null,
  "partial_analysis": null
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 503 | socai2_stage_execution_not_enabled | 业务约束/对象状态，见操作说明 |
| 503 | read_run | 先读该主体下指定Run；此错误没有read_path |
| 404 | stage_subject_not_found | 业务约束/对象状态，见操作说明 |
| 409 | stage_execution_not_ready | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E36.errors`，Swagger同操作 Responses 可直接展开。

<a id="e37"></a>

## E37 手动事件诊断

`POST /api/v1/socai2/incidents/{incident_id}/diagnose`

状态：**已实现**。分类：事件。

**实现状态：** 已实现

**用途：** 手动事件诊断。

**输入：** 路径参数：`incident_id`；JSON请求体：`ExecuteStage`，字段和必填要求见Request body。

**输出：** HTTP 200，`StageEntry`；完整字段和示例见Responses。

**结果：** 发起事件诊断并返回Run结果；21新独立正式入口已挂载并启用，调用会执行当前模型流程。

**规则与限制：** 部署同E36，21新独立正式服务18024已挂载/开启。只传 operation_key，主体来自路径。执行异常先 E25 查询返回的 Run；其他部署未启用时503不产生Run。不能把路由可用当成自动消费者已开启或真实模型质量通过。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库的执行、保存和读取通过；模型/外部查询为替身，真实模型效果未据此验收。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e37) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | incident_id | True | string (uuid) | null | 事件 UUID。 |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |


响应类型：[StageEntry](schemas.md#stageentry)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "incident_id": "00000000-0000-4000-8000-000000000003"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011"
  }
}
```

输出示例（HTTP 200）：

```json
{
  "run": {
    "id": "00000000-0000-4000-8000-000000000004",
    "kind": "incident_diagnosis",
    "state": "failed",
    "requested_at": "2026-11-12T08:00:00Z",
    "requested_by": null,
    "started_at": "2026-11-12T08:00:00Z",
    "ended_at": "2026-11-12T08:00:00Z",
    "executor_version": null,
    "input_artifact_id": null,
    "stop_reason": "example_unavailable",
    "delivery_state": "none"
  },
  "freshness": "unavailable",
  "is_current_pointer": false,
  "valid_for_current_input": false,
  "result": null,
  "explanation": null,
  "partial_analysis": null
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 503 | socai2_stage_execution_not_enabled | 业务约束/对象状态，见操作说明 |
| 503 | read_run | 先读该主体下指定Run；此错误没有read_path |
| 404 | stage_subject_not_found | 业务约束/对象状态，见操作说明 |
| 409 | stage_execution_not_ready | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E37.errors`，Swagger同操作 Responses 可直接展开。

<a id="e38"></a>

## E38 用户创建人工任务

`POST /api/v1/socai2/cases/{case_id}/tasks`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 用户创建人工任务。

**输入：** 路径参数：`case_id`；JSON请求体：`TaskCreate`，字段和必填要求见Request body。

**输出：** HTTP 200，`TaskMutation`；完整字段和示例见Responses。

**结果：** 保存用户创建的人工任务及首个修订，返回任务ID、当前版本和创建结果。

**规则与限制：** 用户明确决定需要人工确认后创建；不自动从 questions 批量生成。先 E03 获取范围版本，assignee_id 由业务后端人员目录取得。origin_finding_id 需同时有 origin_result_id；引用对象必须属于本案。保存不启动调查。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机TCP及21正式HTTP已完成本批Case/H直接操作；保存值与SQL读回一致，Run未启动。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e38) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |


请求体：

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


响应类型：[TaskMutation](schemas.md#taskmutation)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001"
  },
  "body": {
    "title": "核实登录是否为本人操作",
    "description": "联系对应负责人核实",
    "assignee_id": null,
    "due_at": null,
    "state": "not_started",
    "result_text": null,
    "result_scope": null,
    "source_refs": [],
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "expected_scope_revision": 1,
    "origin_result_id": null,
    "origin_finding_id": null
  }
}
```

输出示例（HTTP 200）：

```json
{
  "task": {
    "id": "00000000-0000-4000-8000-000000000006",
    "case_id": "00000000-0000-4000-8000-000000000001",
    "current_revision_id": "00000000-0000-4000-8000-000000000007",
    "origin_result_id": null,
    "origin_finding_id": null,
    "created_at": "2026-11-12T08:00:00Z",
    "created_by": null,
    "updated_at": "2026-11-12T08:00:00Z",
    "row_version": 1,
    "current": {
      "id": "00000000-0000-4000-8000-000000000007",
      "case_id": "00000000-0000-4000-8000-000000000001",
      "task_id": "00000000-0000-4000-8000-000000000006",
      "revision": 1,
      "title": "核实登录是否为本人操作",
      "description": "联系对应负责人核实",
      "assignee_id": null,
      "due_at": null,
      "state": "not_started",
      "result_text": null,
      "result_scope": null,
      "source_refs": [],
      "completed_at": null,
      "completed_by": null,
      "changed_at": "2026-11-12T08:00:00Z",
      "changed_by": "00000000-0000-4000-8000-000000000010"
    }
  },
  "changed": true
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | task_assignee_not_in_tenant | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | task_origin_finding_not_found | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | task_source_reference_outside_case | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 409 | case_scope_revision_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 404 | task_origin_result_not_found | 业务约束/对象状态，见操作说明 |
| 404 | task_source_reference_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E38.errors`，Swagger同操作 Responses 可直接展开。

<a id="e39"></a>

## E39 人工任务列表

`GET /api/v1/socai2/cases/{case_id}/tasks`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 人工任务列表。

**输入：** 路径参数：`case_id`；查询参数：`limit`, `offset`；无请求体。

**输出：** HTTP 200，`TaskPage`；完整字段和示例见Responses。

**结果：** 返回案件人工任务的当前版本列表、总数和下一页偏移。

**规则与限制：** 返回当前修订、总数和 next_offset；待办统计只计实际未结束任务。旧版本必须另用 E42/E43。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e39) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| query | limit | False | integer; minimum=1; maximum=100 | 20 | 本次最多返回条数；不是总量。默认值及上限见字段约束。 |
| query | offset | False | integer; minimum=0; maximum=100000 | 0 | 分页偏移，沿 next_offset 继续。 |


无请求体。

响应类型：[TaskPage](schemas.md#taskpage)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "limit": 20,
    "offset": 0
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "items": [],
  "total": 0,
  "next_offset": null
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | invalid_record_page | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E39.errors`，Swagger同操作 Responses 可直接展开。

<a id="e40"></a>

## E40 修订人工任务

`PUT /api/v1/socai2/cases/{case_id}/tasks/{task_id}`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 修订人工任务。

**输入：** 路径参数：`case_id`, `task_id`；JSON请求体：`TaskEdit`，字段和必填要求见Request body。

**输出：** HTTP 200，`TaskMutation`；完整字段和示例见Responses。

**结果：** 完整更新任务字段，实际变更时保存新的不可变修订并返回当前版本；无变化不新建修订，幂等重试沿用原回执。完成任务必须提供结果正文及有效适用范围。

**规则与限制：** PUT 为完整 TaskFields，不是局部 PATCH；先 E41 取当前字段和 row_version，再 E03 取范围版本，完整带回未修改字段。省略可选字段会取默认值，可能清空原值。completed 必须有 result_text 和 result_scope；whole_case 覆盖当前全部成员，selected_alerts 只能当前子集，explicit_objects 还需非空有效 object_keys。事实变更生成新修订，旧引用不变。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机TCP及21正式HTTP已完成本批Case/H直接操作；保存值与SQL读回一致，Run未启动。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e40) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| path | task_id | True | string (uuid) | null | 本案人工任务 UUID。 |


请求体：

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


响应类型：[TaskMutation](schemas.md#taskmutation)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "task_id": "00000000-0000-4000-8000-000000000006"
  },
  "body": {
    "title": "核实登录是否为本人操作",
    "description": "联系对应负责人核实",
    "assignee_id": null,
    "due_at": null,
    "state": "completed",
    "result_text": "人工已联系负责人；其确认该次登录为本人操作。",
    "result_scope": {
      "kind": "selected_alerts",
      "alert_ids": [
        "00000000-0000-4000-8000-000000000002"
      ],
      "object_keys": [],
      "window_start": null,
      "window_end": null,
      "limitations": [
        "仅覆盖人工核实的该条告警"
      ]
    },
    "source_refs": [],
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "expected_scope_revision": 1,
    "expected_row_version": 1
  }
}
```

输出示例（HTTP 200）：

```json
{
  "task": {
    "id": "00000000-0000-4000-8000-000000000006",
    "case_id": "00000000-0000-4000-8000-000000000001",
    "current_revision_id": "00000000-0000-4000-8000-000000000007",
    "origin_result_id": null,
    "origin_finding_id": null,
    "created_at": "2026-11-12T08:00:00Z",
    "created_by": null,
    "updated_at": "2026-11-12T08:00:00Z",
    "row_version": 2,
    "current": {
      "id": "00000000-0000-4000-8000-000000000007",
      "case_id": "00000000-0000-4000-8000-000000000001",
      "task_id": "00000000-0000-4000-8000-000000000006",
      "revision": 2,
      "title": "核实登录是否为本人操作",
      "description": "联系对应负责人核实",
      "assignee_id": null,
      "due_at": null,
      "state": "completed",
      "result_text": "人工已联系负责人；其确认该次登录为本人操作。",
      "result_scope": {
        "kind": "selected_alerts",
        "alert_ids": [
          "00000000-0000-4000-8000-000000000002"
        ],
        "object_keys": [],
        "window_start": null,
        "window_end": null,
        "limitations": [
          "仅覆盖人工核实的该条告警"
        ]
      },
      "source_refs": [],
      "completed_at": "2026-11-12T08:00:00Z",
      "completed_by": "00000000-0000-4000-8000-000000000010",
      "changed_at": "2026-11-12T08:00:00Z",
      "changed_by": "00000000-0000-4000-8000-000000000010"
    }
  },
  "changed": true
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | task_scope_outside_current_case | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | task_whole_case_scope_incomplete | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | task_object_scope_empty | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | task_objects_outside_current_scope | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_task_not_found | 业务约束/对象状态，见操作说明 |
| 404 | task_source_reference_not_found | 业务约束/对象状态，见操作说明 |
| 409 | task_row_version_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | case_scope_revision_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E40.errors`，Swagger同操作 Responses 可直接展开。

<a id="e41"></a>

## E41 人工任务当前版本

`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 人工任务当前版本。

**输入：** 路径参数：`case_id`, `task_id`；无请求体。

**输出：** HTTP 200，`TaskView`；完整字段和示例见Responses。

**结果：** 返回指定任务的当前修订和行版本，供读取或后续完整更新使用。

**规则与限制：** 读取 task.current 及 row_version。编辑要保留原字段；负责人和完成人均由服务保存，不由客户端伪造完成时间。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机TCP及21正式HTTP已完成本批Case/H直接操作；保存值与SQL读回一致，Run未启动。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e41) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| path | task_id | True | string (uuid) | null | 本案人工任务 UUID。 |


无请求体。

响应类型：[TaskView](schemas.md#taskview)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "task_id": "00000000-0000-4000-8000-000000000006"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "id": "00000000-0000-4000-8000-000000000006",
  "case_id": "00000000-0000-4000-8000-000000000001",
  "current_revision_id": "00000000-0000-4000-8000-000000000007",
  "origin_result_id": null,
  "origin_finding_id": null,
  "created_at": "2026-11-12T08:00:00Z",
  "created_by": null,
  "updated_at": "2026-11-12T08:00:00Z",
  "row_version": 1,
  "current": {
    "id": "00000000-0000-4000-8000-000000000007",
    "case_id": "00000000-0000-4000-8000-000000000001",
    "task_id": "00000000-0000-4000-8000-000000000006",
    "revision": 1,
    "title": "核实登录是否为本人操作",
    "description": "联系对应负责人核实",
    "assignee_id": null,
    "due_at": null,
    "state": "not_started",
    "result_text": null,
    "result_scope": null,
    "source_refs": [],
    "completed_at": null,
    "completed_by": null,
    "changed_at": "2026-11-12T08:00:00Z",
    "changed_by": "00000000-0000-4000-8000-000000000010"
  }
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_task_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E41.errors`，Swagger同操作 Responses 可直接展开。

<a id="e42"></a>

## E42 人工任务修订历史

`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 人工任务修订历史。

**输入：** 路径参数：`case_id`, `task_id`；查询参数：`limit`, `offset`；无请求体。

**输出：** HTTP 200，`TaskRevisionPage`；完整字段和示例见Responses。

**结果：** 返回任务的历史修订列表及下一页偏移，保留各次确认时的事实和范围。

**规则与限制：** 使用 next_offset 分页。任务被引用时必须保存具体 revision_id，不用最新版本覆盖历史事实。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机TCP及21正式HTTP已完成本批Case/H直接操作；保存值与SQL读回一致，Run未启动。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e42) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| path | task_id | True | string (uuid) | null | 本案人工任务 UUID。 |
| query | limit | False | integer; minimum=1; maximum=100 | 20 | 本次最多返回条数；不是总量。默认值及上限见字段约束。 |
| query | offset | False | integer; minimum=0; maximum=100000 | 0 | 分页偏移，沿 next_offset 继续。 |


无请求体。

响应类型：[TaskRevisionPage](schemas.md#taskrevisionpage)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "task_id": "00000000-0000-4000-8000-000000000006",
    "limit": 20,
    "offset": 0
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "items": [],
  "total": 0,
  "next_offset": null
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | invalid_record_page | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_task_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E42.errors`，Swagger同操作 Responses 可直接展开。

<a id="e43"></a>

## E43 人工任务指定修订

`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 人工任务指定修订。

**输入：** 路径参数：`case_id`, `task_id`, `revision_id`；无请求体。

**输出：** HTTP 200，`TaskRevisionView`；完整字段和示例见Responses。

**结果：** 返回指定不可变修订的事项、人工结果、范围、引用及完成信息。

**规则与限制：** 按引用的 revision_id 阅读当时 title/result_text/result_scope/source_refs/completed_at/by；旧版本不可变。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机TCP及21正式HTTP已完成本批Case/H直接操作；保存值与SQL读回一致，Run未启动。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e43) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| path | task_id | True | string (uuid) | null | 本案人工任务 UUID。 |
| path | revision_id | True | string (uuid) | null | 指定不可变任务修订 UUID。 |


无请求体。

响应类型：[TaskRevisionView](schemas.md#taskrevisionview)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "task_id": "00000000-0000-4000-8000-000000000006",
    "revision_id": "00000000-0000-4000-8000-000000000007"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "id": "00000000-0000-4000-8000-000000000007",
  "case_id": "00000000-0000-4000-8000-000000000001",
  "task_id": "00000000-0000-4000-8000-000000000006",
  "revision": 1,
  "title": "核实登录是否为本人操作",
  "description": "联系对应负责人核实",
  "assignee_id": null,
  "due_at": null,
  "state": "not_started",
  "result_text": null,
  "result_scope": null,
  "source_refs": [],
  "completed_at": null,
  "completed_by": null,
  "changed_at": "2026-11-12T08:00:00Z",
  "changed_by": "00000000-0000-4000-8000-000000000010"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_task_revision_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E43.errors`，Swagger同操作 Responses 可直接展开。

<a id="e44"></a>

## E44 Case管理信息与结案条件

`GET /api/v1/socai2/cases/{case_id}/management`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** Case管理信息与结案条件。

**输入：** 路径参数：`case_id`；无请求体。

**输出：** HTTP 200，`CaseManagementView`；完整字段和示例见Responses。

**结果：** 返回当前Case、未完人工任务数量、running/unknown阻塞Run、结案/重开资格及是否需要待办确认。

**规则与限制：** 先读取当前Case行版本、未完任务数及阻塞Run。can_close只说明状态/执行条件；requires_open_task_confirmation为true时仍须确认及理由。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机及21正式HTTP完成管理读取/局部更新、结案与重开，SQL读回一致；任务/Run保持，版本冲突和未完任务确认已验证。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e44) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |


无请求体。

响应类型：[CaseManagementView](schemas.md#casemanagementview)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "case": {
    "id": "00000000-0000-4000-8000-000000000001",
    "source_namespace": null,
    "title": "合成示例：核查异常登录",
    "description": null,
    "handling_status": "in_progress",
    "severity": null,
    "severity_source": null,
    "owner_id": null,
    "assignment_state": "unassigned",
    "owner_source_value": null,
    "assigned_at": null,
    "tags": [],
    "priority_value": null,
    "priority_state": "not_provided",
    "priority_source": null,
    "priority_basis": null,
    "scope_revision": 1,
    "current_assessment_id": null,
    "classification": null,
    "due_at": null,
    "current_evidence_artifact_id": null,
    "created_at": "2026-11-12T08:00:00Z",
    "created_by": null,
    "business_updated_at": "2026-11-12T08:00:00Z",
    "resolved_at": null,
    "resolved_by": null,
    "resolution_note": null,
    "reopened_at": null,
    "row_version": 1
  },
  "open_task_count": 1,
  "blocking_runs": [],
  "can_close": true,
  "can_reopen": false,
  "requires_open_task_confirmation": true
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E44.errors`，Swagger同操作 Responses 可直接展开。

<a id="e45"></a>

## E45 修改Case基本信息

`PATCH /api/v1/socai2/cases/{case_id}/management`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 修改Case基本信息。

**输入：** 路径参数：`case_id`；JSON请求体：`CaseManagementUpdate`，字段和必填要求见Request body。

**输出：** HTTP 200，`CaseManagementReceipt`；完整字段和示例见Responses。

**结果：** 只保存显式提交的管理字段，实际变化才增加行版本；返回保存后的完整Case及changed，不执行调查。

**规则与限制：** PATCH局部更新；至少一个管理字段。省略保持；description/owner_id/severity可null清空，tags=[]清空；title/tags/handling_status不能null。负责人不自动改状态，已结案状态只能显式重开。回执含完整Case快照，随后可E03/E44读取；同键重放返回原回执。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机及21正式HTTP完成管理读取/局部更新、结案与重开，SQL读回一致；任务/Run保持，版本冲突和未完任务确认已验证。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e45) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |


请求体：

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


响应类型：[CaseManagementReceipt](schemas.md#casemanagementreceipt)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "expected_row_version": 1,
    "title": "需要人工跟进的调查",
    "description": "核对相关告警",
    "owner_id": null,
    "severity": "high",
    "tags": [
      "人工跟进"
    ],
    "handling_status": "in_progress"
  }
}
```

输出示例（HTTP 200）：

```json
{
  "case": {
    "id": "00000000-0000-4000-8000-000000000001",
    "source_namespace": null,
    "title": "需要人工跟进的调查",
    "description": "核对相关告警",
    "handling_status": "in_progress",
    "severity": "high",
    "severity_source": "manual",
    "owner_id": null,
    "assignment_state": "unassigned",
    "owner_source_value": null,
    "assigned_at": null,
    "tags": [
      "人工跟进"
    ],
    "priority_value": null,
    "priority_state": "not_provided",
    "priority_source": null,
    "priority_basis": null,
    "scope_revision": 1,
    "current_assessment_id": null,
    "classification": null,
    "due_at": null,
    "current_evidence_artifact_id": null,
    "created_at": "2026-11-12T08:00:00Z",
    "created_by": null,
    "business_updated_at": "2026-11-12T08:00:00Z",
    "resolved_at": null,
    "resolved_by": null,
    "resolution_note": null,
    "reopened_at": null,
    "row_version": 2
  },
  "changed": true
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | case_owner_not_in_tenant | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_not_found | 业务约束/对象状态，见操作说明 |
| 409 | case_row_version_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | case_reopen_required | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E45.errors`，Swagger同操作 Responses 可直接展开。

<a id="e46"></a>

## E46 结案

`POST /api/v1/socai2/cases/{case_id}/close`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 结案。

**输入：** 路径参数：`case_id`；JSON请求体：`CaseCloseRequest`，字段和必填要求见Request body。

**输出：** HTTP 200，`CaseManagementReceipt`；完整字段和示例见Responses。

**结果：** 核对当前运行和人工待办后，将Case标为resolved，保存解决人/时间/理由；返回Case快照，任务与Run保持。

**规则与限制：** 先E44提示未完任务及阻塞Run。running/unknown禁止结案；有未完任务须acknowledge_open_tasks=true及非空reason。无未完任务reason可省略。pending_update保留，不自动取消任务，不修改成员/判断；解决人及时间由服务保存。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机及21正式HTTP完成管理读取/局部更新、结案与重开，SQL读回一致；任务/Run保持，版本冲突和未完任务确认已验证。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e46) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_row_version | 是 | integer; minimum=1.0 | 无（可空不等于可省略） | 读当前 Case/Task 获得的行版本；不匹配返回409。 |
| reason | 否 | string; minLength=1; maxLength=20000 / null | 无（可空不等于可省略） | 服务返回原因；不代表adopt已有reason请求参数。 |
| acknowledge_open_tasks | 否 | boolean | false | 是否已确认当前未完人工任务；有未完任务时须true并填写reason，任务不会被取消。 |


响应类型：[CaseManagementReceipt](schemas.md#casemanagementreceipt)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "expected_row_version": 1,
    "acknowledge_open_tasks": true,
    "reason": "当前调查结案，未完人工任务另行跟进。"
  }
}
```

输出示例（HTTP 200）：

```json
{
  "case": {
    "id": "00000000-0000-4000-8000-000000000001",
    "source_namespace": null,
    "title": "合成示例：核查异常登录",
    "description": null,
    "handling_status": "resolved",
    "severity": null,
    "severity_source": null,
    "owner_id": null,
    "assignment_state": "unassigned",
    "owner_source_value": null,
    "assigned_at": null,
    "tags": [],
    "priority_value": null,
    "priority_state": "not_provided",
    "priority_source": null,
    "priority_basis": null,
    "scope_revision": 1,
    "current_assessment_id": null,
    "classification": null,
    "due_at": null,
    "current_evidence_artifact_id": null,
    "created_at": "2026-11-12T08:00:00Z",
    "created_by": null,
    "business_updated_at": "2026-11-12T08:00:00Z",
    "resolved_at": "2026-11-12T08:00:00Z",
    "resolved_by": "00000000-0000-4000-8000-000000000010",
    "resolution_note": "当前调查结案，未完人工任务另行跟进。",
    "reopened_at": null,
    "row_version": 2
  },
  "changed": true
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_not_found | 业务约束/对象状态，见操作说明 |
| 409 | case_row_version_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | case_active_run_prevents_close | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | case_open_tasks_confirmation_required | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | case_already_resolved | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E46.errors`，Swagger同操作 Responses 可直接展开。

<a id="e47"></a>

## E47 重开Case

`POST /api/v1/socai2/cases/{case_id}/reopen`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 重开Case。

**输入：** 路径参数：`case_id`；JSON请求体：`CaseLifecycleRequest`，字段和必填要求见Request body。

**输出：** HTTP 200，`CaseManagementReceipt`；完整字段和示例见Responses。

**结果：** 将已解决Case恢复in_progress，记录重开时间并清空当前结案字段；返回Case快照，历史活动保留，不自动调查。

**规则与限制：** 仅resolved案件可重开，恢复in_progress并记录reopened_at，清空当前结案字段；旧结案说明保留在E17活动。reason可选。不新建或启动Run，不改变人工任务/成员/判断。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机及21正式HTTP完成管理读取/局部更新、结案与重开，SQL读回一致；任务/Run保持，版本冲突和未完任务确认已验证。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e47) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_row_version | 是 | integer; minimum=1.0 | 无（可空不等于可省略） | 读当前 Case/Task 获得的行版本；不匹配返回409。 |
| reason | 否 | string; minLength=1; maxLength=20000 / null | 无（可空不等于可省略） | 服务返回原因；不代表adopt已有reason请求参数。 |


响应类型：[CaseManagementReceipt](schemas.md#casemanagementreceipt)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "expected_row_version": 1,
    "reason": "收到需要继续处理的信息，人工重开。"
  }
}
```

输出示例（HTTP 200）：

```json
{
  "case": {
    "id": "00000000-0000-4000-8000-000000000001",
    "source_namespace": null,
    "title": "合成示例：核查异常登录",
    "description": null,
    "handling_status": "in_progress",
    "severity": null,
    "severity_source": null,
    "owner_id": null,
    "assignment_state": "unassigned",
    "owner_source_value": null,
    "assigned_at": null,
    "tags": [],
    "priority_value": null,
    "priority_state": "not_provided",
    "priority_source": null,
    "priority_basis": null,
    "scope_revision": 1,
    "current_assessment_id": null,
    "classification": null,
    "due_at": null,
    "current_evidence_artifact_id": null,
    "created_at": "2026-11-12T08:00:00Z",
    "created_by": null,
    "business_updated_at": "2026-11-12T08:00:00Z",
    "resolved_at": null,
    "resolved_by": null,
    "resolution_note": null,
    "reopened_at": "2026-11-12T08:00:00Z",
    "row_version": 2
  },
  "changed": true
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_not_found | 业务约束/对象状态，见操作说明 |
| 409 | case_row_version_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | case_not_resolved | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E47.errors`，Swagger同操作 Responses 可直接展开。

<a id="e48"></a>

## E48 提交告警人工判定

`POST /api/v1/socai2/alerts/{alert_id}/feedback`

状态：**已实现**。分类：告警。

**实现状态：** 已实现

**用途：** 提交告警人工判定。

**输入：** 路径参数：`alert_id`；JSON请求体：`AlertFeedback`，字段和必填要求见Request body。

**输出：** HTTP 200，`SubjectMutationReceipt`；完整字段和示例见Responses。

**结果：** 单条人工判定，reason必填，追加反馈并保留模型分诊；误报/正常关闭，已关闭改真实威胁/需跟进恢复处理中。E28读feedback及facts，E30读活动，不自动改父事件/Case结论或启动模型。

**规则与限制：** 单条人工判定，reason必填，追加反馈并保留模型分诊；误报/正常关闭，已关闭改真实威胁/需跟进恢复处理中。E28读feedback及facts，E30读活动，不自动改父事件/Case结论或启动模型。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机六项单条/批量HTTP、状态联动、幂等/冲突及SQL读回已验；21发布和验收见本批部署回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e48) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | alert_id | True | string (uuid) | null | 告警 UUID。 |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_row_version | 是 | integer; minimum=1.0 | 无（可空不等于可省略） | 读当前 Case/Task 获得的行版本；不匹配返回409。 |
| disposition | 是 | [Disposition](schemas.md#disposition) | 无（可空不等于可省略） | 人工判定；false_positive/benign关闭，已关闭改true_positive/needs_review恢复处理中。 |
| reason | 是 | string; minLength=1; maxLength=20000 | 无（可空不等于可省略） | 服务返回原因；不代表adopt已有reason请求参数。 |


响应类型：[SubjectMutationReceipt](schemas.md#subjectmutationreceipt)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "alert_id": "00000000-0000-4000-8000-000000000002"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "expected_row_version": 1,
    "disposition": "false_positive",
    "reason": "人工核实为已知检测误报"
  }
}
```

输出示例（HTTP 200）：

```json
{
  "kind": "alerts",
  "facts": {
    "id": "00000000-0000-4000-8000-000000000002",
    "source_namespace": "example",
    "title": "合成示例：核查异常登录",
    "description": null,
    "owner_id": "00000000-0000-4000-8000-000000000010",
    "assignment_state": "assigned",
    "owner_source_value": null,
    "assigned_at": "2026-11-12T08:00:00Z",
    "tags": [],
    "priority_value": null,
    "priority_state": "not_provided",
    "priority_source": null,
    "priority_basis": null,
    "business_updated_at": "2026-11-12T08:00:00Z",
    "reopened_at": null,
    "row_version": 2,
    "source_alert_id": null,
    "vendor_alert_id": null,
    "connector_id": null,
    "connector_type": null,
    "original_vendor": null,
    "category": null,
    "severity": null,
    "severity_raw": null,
    "event_time": null,
    "event_time_source": "source",
    "first_seen_at": null,
    "last_seen_at": null,
    "ingested_at": "2026-11-12T08:00:00Z",
    "source_updated_at": "2026-11-12T08:00:00Z",
    "handling_status": "completed",
    "disposition": "false_positive",
    "closed_at": "2026-11-12T08:00:00Z",
    "closed_by": "00000000-0000-4000-8000-000000000010",
    "latest_material_id": null,
    "latest_triage_id": null,
    "latest_feedback_id": "00000000-0000-4000-8000-000000000005",
    "latest_explanation_id": null
  },
  "changed": true,
  "feedback_id": "00000000-0000-4000-8000-000000000005",
  "activity_id": "00000000-0000-4000-8000-000000000011"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | subject_not_found | 业务约束/对象状态，见操作说明 |
| 409 | subject_row_version_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E48.errors`，Swagger同操作 Responses 可直接展开。

<a id="e49"></a>

## E49 批量提交告警人工判定

`POST /api/v1/socai2/alerts/feedback-batch`

状态：**已实现**。分类：告警。

**实现状态：** 已实现

**用途：** 批量提交告警人工判定。

**输入：** JSON请求体：`AlertFeedbackBatch`，字段和必填要求见Request body。

**输出：** HTTP 200，`SubjectBatchReceipt`；完整字段和示例见Responses。

**结果：** 仅用户明确选中的items，共用feedback判定和理由；逐项版本校验，整批成功或拒绝，默认配置最多100项。不会自动按相似度选中或批量改判。

**规则与限制：** 仅用户明确选中的items，共用feedback判定和理由；逐项版本校验，整批成功或拒绝，默认配置最多100项。不会自动按相似度选中或批量改判。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机六项单条/批量HTTP、状态联动、幂等/冲突及SQL读回已验；21发布和验收见本批部署回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e49) · [动态投影与差异](audit/dynamic-fields.html)

无路径/查询参数。

请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| items | 是 | array <[SelectedSubject](schemas.md#selectedsubject)>; minItems=1 | 无（可空不等于可省略） | 明确选择及各自版本；不允许重复ID，数量上限由服务配置。整批成功或拒绝。 |
| feedback | 是 | [FeedbackFields](schemas.md#feedbackfields) | 无（可空不等于可省略） | 应用于全部明确选中告警的人工判定及理由。 |


响应类型：[SubjectBatchReceipt](schemas.md#subjectbatchreceipt)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {},
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "items": [
      {
        "id": "00000000-0000-4000-8000-000000000002",
        "expected_row_version": 1
      }
    ],
    "feedback": {
      "disposition": "false_positive",
      "reason": "逐条核实所选告警属于本次误报"
    }
  }
}
```

输出示例（HTTP 200）：

```json
{
  "operation_key": "00000000-0000-4000-8000-000000000011",
  "items": [
    {
      "kind": "alerts",
      "facts": {
        "id": "00000000-0000-4000-8000-000000000002",
        "source_namespace": "example",
        "title": "合成示例：核查异常登录",
        "description": null,
        "owner_id": "00000000-0000-4000-8000-000000000010",
        "assignment_state": "assigned",
        "owner_source_value": null,
        "assigned_at": "2026-11-12T08:00:00Z",
        "tags": [],
        "priority_value": null,
        "priority_state": "not_provided",
        "priority_source": null,
        "priority_basis": null,
        "business_updated_at": "2026-11-12T08:00:00Z",
        "reopened_at": null,
        "row_version": 2,
        "source_alert_id": null,
        "vendor_alert_id": null,
        "connector_id": null,
        "connector_type": null,
        "original_vendor": null,
        "category": null,
        "severity": null,
        "severity_raw": null,
        "event_time": null,
        "event_time_source": "source",
        "first_seen_at": null,
        "last_seen_at": null,
        "ingested_at": "2026-11-12T08:00:00Z",
        "source_updated_at": "2026-11-12T08:00:00Z",
        "handling_status": "completed",
        "disposition": "false_positive",
        "closed_at": "2026-11-12T08:00:00Z",
        "closed_by": "00000000-0000-4000-8000-000000000010",
        "latest_material_id": null,
        "latest_triage_id": null,
        "latest_feedback_id": "00000000-0000-4000-8000-000000000005",
        "latest_explanation_id": null
      },
      "changed": true,
      "feedback_id": "00000000-0000-4000-8000-000000000005",
      "activity_id": "00000000-0000-4000-8000-000000000011"
    }
  ],
  "changed_count": 1
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | subject_batch_selection_invalid | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | subject_not_found | 业务约束/对象状态，见操作说明 |
| 409 | subject_row_version_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E49.errors`，Swagger同操作 Responses 可直接展开。

<a id="e50"></a>

## E50 管理单条告警

`PATCH /api/v1/socai2/alerts/{alert_id}/management`

状态：**已实现**。分类：告警。

**实现状态：** 已实现

**用途：** 管理单条告警。

**输入：** 路径参数：`alert_id`；JSON请求体：`AlertManagementUpdate`，字段和必填要求见Request body。

**输出：** HTTP 200，`SubjectMutationReceipt`；完整字段和示例见Responses。

**结果：** PATCH省略保持，owner_id=null取消分配、tags=[]清空；仅分配不改状态，人工关闭须reason且保留原判定。返回保存时facts及activity_id，最新摘要沿E28读取。

**规则与限制：** PATCH省略保持，owner_id=null取消分配、tags=[]清空；仅分配不改状态，人工关闭须reason且保留原判定。返回保存时facts及activity_id，最新摘要沿E28读取。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机六项单条/批量HTTP、状态联动、幂等/冲突及SQL读回已验；21发布和验收见本批部署回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e50) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | alert_id | True | string (uuid) | null | 告警 UUID。 |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| expected_row_version | 是 | integer; minimum=1.0 | 无（可空不等于可省略） | 读当前 Case/Task 获得的行版本；不匹配返回409。 |
| owner_id | 否 | string (uuid) / null | 无（可空不等于可省略） | 负责人用户UUID；人员目录由业务后端负责。 |
| tags | 否 | array <string; minLength=1; maxLength=128>; maxLength=50 | 无（可空不等于可省略） | 标签列表，不替代资产标签。 |
| reason | 否 | string; minLength=1; maxLength=20000 / null | 无（可空不等于可省略） | 服务返回原因；不代表adopt已有reason请求参数。 |
| handling_status | 否 | string new, in_progress, completed | 无（可空不等于可省略） | 主体业务处理状态，与Run执行状态分开。 |


响应类型：[SubjectMutationReceipt](schemas.md#subjectmutationreceipt)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "alert_id": "00000000-0000-4000-8000-000000000002"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "expected_row_version": 1,
    "owner_id": "00000000-0000-4000-8000-000000000010",
    "tags": [
      "人工跟进"
    ]
  }
}
```

输出示例（HTTP 200）：

```json
{
  "kind": "alerts",
  "facts": {
    "id": "00000000-0000-4000-8000-000000000002",
    "source_namespace": "example",
    "title": "合成示例：核查异常登录",
    "description": null,
    "owner_id": "00000000-0000-4000-8000-000000000010",
    "assignment_state": "assigned",
    "owner_source_value": null,
    "assigned_at": "2026-11-12T08:00:00Z",
    "tags": [
      "人工跟进"
    ],
    "priority_value": null,
    "priority_state": "not_provided",
    "priority_source": null,
    "priority_basis": null,
    "business_updated_at": "2026-11-12T08:00:00Z",
    "reopened_at": null,
    "row_version": 2,
    "source_alert_id": null,
    "vendor_alert_id": null,
    "connector_id": null,
    "connector_type": null,
    "original_vendor": null,
    "category": null,
    "severity": null,
    "severity_raw": null,
    "event_time": null,
    "event_time_source": "source",
    "first_seen_at": null,
    "last_seen_at": null,
    "ingested_at": "2026-11-12T08:00:00Z",
    "source_updated_at": "2026-11-12T08:00:00Z",
    "handling_status": "in_progress",
    "disposition": null,
    "closed_at": null,
    "closed_by": null,
    "latest_material_id": null,
    "latest_triage_id": null,
    "latest_feedback_id": null,
    "latest_explanation_id": null
  },
  "changed": true,
  "feedback_id": null,
  "activity_id": "00000000-0000-4000-8000-000000000011"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | subject_owner_not_in_tenant | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | alert_close_reason_required | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | subject_not_found | 业务约束/对象状态，见操作说明 |
| 409 | subject_row_version_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E50.errors`，Swagger同操作 Responses 可直接展开。

<a id="e51"></a>

## E51 批量管理告警

`POST /api/v1/socai2/alerts/management-batch`

状态：**已实现**。分类：告警。

**实现状态：** 已实现

**用途：** 批量管理告警。

**输入：** JSON请求体：`AlertManagementBatch`，字段和必填要求见Request body。

**输出：** HTTP 200，`SubjectBatchReceipt`；完整字段和示例见Responses。

**结果：** items带每条ID和expected_row_version，共用changes；批量整体事务，未选告警不改。设置负责人不自动关闭或重开。返回按ID排序的逐项快照和changed_count。

**规则与限制：** items带每条ID和expected_row_version，共用changes；批量整体事务，未选告警不改。设置负责人不自动关闭或重开。返回按ID排序的逐项快照和changed_count。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机六项单条/批量HTTP、状态联动、幂等/冲突及SQL读回已验；21发布和验收见本批部署回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e51) · [动态投影与差异](audit/dynamic-fields.html)

无路径/查询参数。

请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| items | 是 | array <[SelectedSubject](schemas.md#selectedsubject)>; minItems=1 | 无（可空不等于可省略） | 明确选择及各自版本；不允许重复ID，数量上限由服务配置。整批成功或拒绝。 |
| changes | 是 | [AlertManagementFields](schemas.md#alertmanagementfields) | 无（可空不等于可省略） | 应用于所选告警的局部修改。 |


响应类型：[SubjectBatchReceipt](schemas.md#subjectbatchreceipt)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {},
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "items": [
      {
        "id": "00000000-0000-4000-8000-000000000002",
        "expected_row_version": 1
      }
    ],
    "changes": {
      "owner_id": "00000000-0000-4000-8000-000000000010",
      "tags": [
        "人工跟进"
      ]
    }
  }
}
```

输出示例（HTTP 200）：

```json
{
  "operation_key": "00000000-0000-4000-8000-000000000011",
  "items": [
    {
      "kind": "alerts",
      "facts": {
        "id": "00000000-0000-4000-8000-000000000002",
        "source_namespace": "example",
        "title": "合成示例：核查异常登录",
        "description": null,
        "owner_id": "00000000-0000-4000-8000-000000000010",
        "assignment_state": "assigned",
        "owner_source_value": null,
        "assigned_at": "2026-11-12T08:00:00Z",
        "tags": [
          "人工跟进"
        ],
        "priority_value": null,
        "priority_state": "not_provided",
        "priority_source": null,
        "priority_basis": null,
        "business_updated_at": "2026-11-12T08:00:00Z",
        "reopened_at": null,
        "row_version": 2,
        "source_alert_id": null,
        "vendor_alert_id": null,
        "connector_id": null,
        "connector_type": null,
        "original_vendor": null,
        "category": null,
        "severity": null,
        "severity_raw": null,
        "event_time": null,
        "event_time_source": "source",
        "first_seen_at": null,
        "last_seen_at": null,
        "ingested_at": "2026-11-12T08:00:00Z",
        "source_updated_at": "2026-11-12T08:00:00Z",
        "handling_status": "in_progress",
        "disposition": null,
        "closed_at": null,
        "closed_by": null,
        "latest_material_id": null,
        "latest_triage_id": null,
        "latest_feedback_id": null,
        "latest_explanation_id": null
      },
      "changed": true,
      "feedback_id": null,
      "activity_id": "00000000-0000-4000-8000-000000000011"
    }
  ],
  "changed_count": 1
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | subject_owner_not_in_tenant | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | subject_batch_selection_invalid | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | alert_close_reason_required | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | subject_not_found | 业务约束/对象状态，见操作说明 |
| 409 | subject_row_version_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E51.errors`，Swagger同操作 Responses 可直接展开。

<a id="e52"></a>

## E52 管理单个事件

`PATCH /api/v1/socai2/incidents/{incident_id}/management`

状态：**已实现**。分类：事件。

**实现状态：** 已实现

**用途：** 管理单个事件。

**输入：** 路径参数：`incident_id`；JSON请求体：`IncidentManagementUpdate`，字段和必填要求见Request body。

**输出：** HTTP 200，`SubjectMutationReceipt`；完整字段和示例见Responses。

**结果：** 分配未解决事件默认进入处理中；已解决仅改负责人不重开。显式resolved须resolution_note；severity_override非null须理由，null恢复自动等级且清空覆盖元数据；不改成员告警等级。

**规则与限制：** 分配未解决事件默认进入处理中；已解决仅改负责人不重开。显式resolved须resolution_note；severity_override非null须理由，null恢复自动等级且清空覆盖元数据；不改成员告警等级。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机六项单条/批量HTTP、状态联动、幂等/冲突及SQL读回已验；21发布和验收见本批部署回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e52) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | incident_id | True | string (uuid) | null | 事件 UUID。 |


请求体：

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


响应类型：[SubjectMutationReceipt](schemas.md#subjectmutationreceipt)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "incident_id": "00000000-0000-4000-8000-000000000003"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "expected_row_version": 1,
    "severity_override": "high",
    "severity_override_reason": "人工核对影响范围后调整"
  }
}
```

输出示例（HTTP 200）：

```json
{
  "kind": "incidents",
  "facts": {
    "id": "00000000-0000-4000-8000-000000000003",
    "source_namespace": "example",
    "title": "合成示例：核查异常登录",
    "description": null,
    "owner_id": null,
    "assignment_state": "unassigned",
    "owner_source_value": null,
    "assigned_at": null,
    "tags": [],
    "priority_value": null,
    "priority_state": "not_provided",
    "priority_source": null,
    "priority_basis": null,
    "business_updated_at": "2026-11-12T08:00:00Z",
    "reopened_at": null,
    "row_version": 2,
    "source_incident_id": "示例",
    "handling_status": "in_progress",
    "severity_override": "high",
    "severity_override_reason": "人工核对影响范围后调整",
    "severity_override_at": "2026-11-12T08:00:00Z",
    "severity_override_by": "00000000-0000-4000-8000-000000000010",
    "resolution_note": null,
    "resolved_at": null,
    "resolved_by": null,
    "created_at": "2026-11-12T08:00:00Z",
    "latest_diagnosis_id": null
  },
  "changed": true,
  "feedback_id": null,
  "activity_id": "00000000-0000-4000-8000-000000000011"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | subject_owner_not_in_tenant | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | subject_not_found | 业务约束/对象状态，见操作说明 |
| 409 | subject_row_version_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E52.errors`，Swagger同操作 Responses 可直接展开。

<a id="e53"></a>

## E53 批量管理事件

`POST /api/v1/socai2/incidents/management-batch`

状态：**已实现**。分类：事件。

**实现状态：** 已实现

**用途：** 批量管理事件。

**输入：** JSON请求体：`IncidentManagementBatch`，字段和必填要求见Request body。

**输出：** HTTP 200，`SubjectBatchReceipt`；完整字段和示例见Responses。

**结果：** 对明确选中事件应用共用changes；每项都验证版本、状态和理由，整批成功或拒绝。负责人/严重度/状态遵守单条规则，不修改其他事件或Case。

**规则与限制：** 对明确选中事件应用共用changes；每项都验证版本、状态和理由，整批成功或拒绝。负责人/严重度/状态遵守单条规则，不修改其他事件或Case。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机六项单条/批量HTTP、状态联动、幂等/冲突及SQL读回已验；21发布和验收见本批部署回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e53) · [动态投影与差异](audit/dynamic-fields.html)

无路径/查询参数。

请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 客户端为一次逻辑写操作生成的 UUID；同一意图重试沿用，改变意图或操作者须新 key。执行未知先读取状态。 |
| items | 是 | array <[SelectedSubject](schemas.md#selectedsubject)>; minItems=1 | 无（可空不等于可省略） | 明确选择及各自版本；不允许重复ID，数量上限由服务配置。整批成功或拒绝。 |
| changes | 是 | [IncidentManagementFields](schemas.md#incidentmanagementfields) | 无（可空不等于可省略） | 应用于所选事件的局部修改。 |


响应类型：[SubjectBatchReceipt](schemas.md#subjectbatchreceipt)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {},
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "items": [
      {
        "id": "00000000-0000-4000-8000-000000000003",
        "expected_row_version": 1
      }
    ],
    "changes": {
      "handling_status": "resolved",
      "resolution_note": "人工完成事件核实"
    }
  }
}
```

输出示例（HTTP 200）：

```json
{
  "operation_key": "00000000-0000-4000-8000-000000000011",
  "items": [
    {
      "kind": "incidents",
      "facts": {
        "id": "00000000-0000-4000-8000-000000000003",
        "source_namespace": "example",
        "title": "合成示例：核查异常登录",
        "description": null,
        "owner_id": null,
        "assignment_state": "unassigned",
        "owner_source_value": null,
        "assigned_at": null,
        "tags": [],
        "priority_value": null,
        "priority_state": "not_provided",
        "priority_source": null,
        "priority_basis": null,
        "business_updated_at": "2026-11-12T08:00:00Z",
        "reopened_at": null,
        "row_version": 2,
        "source_incident_id": "示例",
        "handling_status": "resolved",
        "severity_override": "high",
        "severity_override_reason": "人工核对影响范围后调整",
        "severity_override_at": "2026-11-12T08:00:00Z",
        "severity_override_by": "00000000-0000-4000-8000-000000000010",
        "resolution_note": "人工完成事件核实",
        "resolved_at": "2026-11-12T08:00:00Z",
        "resolved_by": "00000000-0000-4000-8000-000000000010",
        "created_at": "2026-11-12T08:00:00Z",
        "latest_diagnosis_id": null
      },
      "changed": true,
      "feedback_id": null,
      "activity_id": "00000000-0000-4000-8000-000000000011"
    }
  ],
  "changed_count": 1
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | subject_owner_not_in_tenant | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | subject_batch_selection_invalid | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | subject_not_found | 业务约束/对象状态，见操作说明 |
| 409 | subject_row_version_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E53.errors`，Swagger同操作 Responses 可直接展开。

<a id="e54"></a>

## E54 导出告警列表 CSV

`GET /api/v1/socai2/alerts/export`

状态：**已实现**。分类：告警。

**实现状态：** 已实现

**用途：** 导出告警列表 CSV。

**输入：** 查询参数：`columns`, `q`, `severity`, `handling_status`, `owner_id`, `assignment_state`, `time_from`, `time_to`, `sort_by`, `sort_order`；无请求体。

**输出：** HTTP 200，`text/csv；字段名表头，完整CSV，错误仍为JSON`；完整字段和示例见Responses。

**结果：** 返回告警筛选命中的全部记录CSV；已选列按给定顺序，超限明确失败。不会修改记录。

**规则与限制：** 复用相应列表的筛选和排序，导出本次只读快照的全部命中；columns为逗号分隔的公开字段路径，省略使用默认列。禁止limit/cursor/before_id/offset及未知参数；列名空白、重复或不支持返回422。UTF-8 BOM、逗号分隔、CRLF、字段名为表头；空结果200仅表头。null写\N，空串留空；实际以反斜杠开头的字符串额外加一个反斜杠，以单引号开头或可能成为公式的字符串前加单引号，程序读取时按此规则去掉一个前缀再还原；数组/对象为JSON。文件包含完整范围，超过10000行或16MiB返回413，不返回截断文件；SQL限时30秒，超时503。Content-Disposition提供文件名；X-Export-Count为实际条数、X-Export-Observed-At为快照观察时间、X-Export-Schema=socai2.list-export.v1。仅查询，不写库或启动分析。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机62次真实TCP及PG核对：55条告警超过旧单页范围，三类104个公开列与列表逐值一致，行上限413，查询前后数据不变；发布读回见本批回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

**可选输出列（按columns传入顺序）：**

| 列名 | 默认列 | 含义 |
| --- | --- | --- |
| `facts.id` | 是 | 该记录的应用UUID，不是页面展示编号或厂商编号。 |
| `facts.source_namespace` | 是 | 来源系统命名空间，不是原厂名称 |
| `facts.title` | 是 | 接收到的标题；未知来源用显式缺失显示，不编造内容 |
| `facts.description` | 否 | 来源说明；人工补充用评论 |
| `facts.owner_id` | 是 | public.users.id |
| `facts.assignment_state` | 是 | 分配状态 |
| `facts.owner_source_value` | 否 | unresolved时原负责人值 |
| `facts.assigned_at` | 否 | 最近分配操作时间 |
| `facts.tags` | 是 | 业务标签；资产标签从库存读取 |
| `facts.priority_value` | 否 | 已有优先级0到100，不以分诊分数填充 |
| `facts.priority_state` | 否 | 优先级评分状态 |
| `facts.priority_source` | 否 | 评分生产者/模型版本 |
| `facts.priority_basis` | 否 | 评分来源依据；无值不造理由 |
| `facts.business_updated_at` | 是 | 实际业务字段变更时间；GET不更新 |
| `facts.reopened_at` | 否 | 最近明确重开时间 |
| `facts.row_version` | 否 | 管理乐观锁；每次实际写入+1 |
| `facts.source_alert_id` | 否 | 接入来源编号；允许非UUID |
| `facts.vendor_alert_id` | 否 | 厂商原始告警编号；与接入编号分开 |
| `facts.connector_id` | 否 | 已有连接器引用，同租户校验 |
| `facts.connector_type` | 是 | 接入类型原值，不代替original_vendor |
| `facts.original_vendor` | 是 | 明确原厂，未知NULL |
| `facts.category` | 是 | 来源类别，不拿判定替代 |
| `facts.severity` | 是 | 当前来源严重程度 |
| `facts.severity_raw` | 否 | 未映射来源等级原文 |
| `facts.event_time` | 是 | 真实发生时间 |
| `facts.event_time_source` | 否 | 发生时间依据 |
| `facts.first_seen_at` | 否 | 已收到材料中首次活动时间 |
| `facts.last_seen_at` | 否 | 已收到材料中末次活动时间 |
| `facts.ingested_at` | 否 | 首次接收时间 |
| `facts.source_updated_at` | 否 | 本地保存新材料的时间 |
| `facts.handling_status` | 是 | 业务处理状态 |
| `facts.disposition` | 否 | 当前采用判定；与latest反馈或分诊配套 |
| `facts.closed_at` | 否 | 当前完成周期关闭时间；重开后置空，旧值在活动中 |
| `facts.closed_by` | 否 | 明确用户关闭人；自动关闭记录活动服务身份 |
| `facts.latest_material_id` | 否 | 同告警最新有效材料 |
| `facts.latest_triage_id` | 否 | 同告警kind=triage记录 |
| `facts.latest_feedback_id` | 否 | 同告警kind=human_feedback记录 |
| `facts.latest_explanation_id` | 否 | 同告警kind=alert_explanation的有效Explain材料；GET不生成并写业务时钟 |
| `owner_name` | 是 | 本租户人员目录中的负责人显示名；未解析为null。 |


| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| query | columns | False | string / null | null | 逗号分隔的公开字段路径，按给定顺序输出；省略使用默认列；空列、重复或未知列返回422。全部可选列及默认列见Responses。 |
| query | q | False | string; maxLength=200 / null | null | 标题字面包含或精确UUID搜索；%和_按普通字符处理。 |
| query | severity | False | [Severity](schemas.md#severity) / null | null | 按已知等级精确筛选；省略不筛选。当前没有单独筛选未知等级的参数，不传null字符串。 |
| query | handling_status | False | [AlertStatus](schemas.md#alertstatus) / null | null | 主体业务处理状态，与Run执行状态分开。 |
| query | owner_id | False | string (uuid) / null | null | 负责人用户UUID；人员目录由业务后端负责。 |
| query | assignment_state | False | [AssignmentState](schemas.md#assignmentstate) / null | null | 分配状态，unresolved不等于unassigned。 |
| query | time_from | False | string (date-time) / null | null | 带时区的起点，包含；告警按event_time，事件至少一条成员event_time命中，Case按business_updated_at。 |
| query | time_to | False | string (date-time) / null | null | 带时区的终点，不包含；两端同时传时必须晚于time_from。 |
| query | sort_by | False | string ingested_at, event_time, severity / null | null | 服务排序字段，可选值见本接口枚举；记录排序字段缺值时置后，同值按UUID排序；非法sort_by返回422。 默认ingested_at。 |
| query | sort_order | False | string asc, desc / null | null | asc升序或desc降序，默认desc。 |


无请求体。

响应类型：string (binary)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "q": "合成示例无记录",
    "columns": "facts.id,facts.title,facts.severity,facts.event_time,facts.handling_status,facts.category,facts.original_vendor,facts.connector_type,facts.source_namespace,facts.owner_id,owner_name,facts.assignment_state,facts.tags,facts.business_updated_at",
    "sort_by": "severity",
    "sort_order": "desc"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```csv
facts.id,facts.title,facts.severity,facts.event_time,facts.handling_status,facts.category,facts.original_vendor,facts.connector_type,facts.source_namespace,facts.owner_id,owner_name,facts.assignment_state,facts.tags,facts.business_updated_at
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | permission_denied | 现有读取条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | export_columns_invalid | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | export_pagination_not_supported | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | export_query_parameter_not_supported | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 503 | export_query_timeout | 业务约束/对象状态，见操作说明 |
| 503 | export_snapshot_incomplete | 业务约束/对象状态，见操作说明 |
| 413 | export_row_limit_exceeded | 业务约束/对象状态，见操作说明 |
| 413 | export_size_limit_exceeded | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E54.errors`，Swagger同操作 Responses 可直接展开。

<a id="e55"></a>

## E55 导出事件列表 CSV

`GET /api/v1/socai2/incidents/export`

状态：**已实现**。分类：事件。

**实现状态：** 已实现

**用途：** 导出事件列表 CSV。

**输入：** 查询参数：`columns`, `q`, `severity`, `handling_status`, `owner_id`, `assignment_state`, `time_from`, `time_to`, `sort_by`, `sort_order`；无请求体。

**输出：** HTTP 200，`text/csv；字段名表头，完整CSV，错误仍为JSON`；完整字段和示例见Responses。

**结果：** 返回事件筛选命中的全部记录CSV；已选列按给定顺序，超限明确失败。不会修改记录。

**规则与限制：** 复用相应列表的筛选和排序，导出本次只读快照的全部命中；columns为逗号分隔的公开字段路径，省略使用默认列。禁止limit/cursor/before_id/offset及未知参数；列名空白、重复或不支持返回422。UTF-8 BOM、逗号分隔、CRLF、字段名为表头；空结果200仅表头。null写\N，空串留空；实际以反斜杠开头的字符串额外加一个反斜杠，以单引号开头或可能成为公式的字符串前加单引号，程序读取时按此规则去掉一个前缀再还原；数组/对象为JSON。文件包含完整范围，超过10000行或16MiB返回413，不返回截断文件；SQL限时30秒，超时503。Content-Disposition提供文件名；X-Export-Count为实际条数、X-Export-Observed-At为快照观察时间、X-Export-Schema=socai2.list-export.v1。仅查询，不写库或启动分析。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机62次真实TCP及PG核对：55条告警超过旧单页范围，三类104个公开列与列表逐值一致，行上限413，查询前后数据不变；发布读回见本批回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

**可选输出列（按columns传入顺序）：**

| 列名 | 默认列 | 含义 |
| --- | --- | --- |
| `facts.id` | 是 | 该记录的应用UUID，不是页面展示编号或厂商编号。 |
| `facts.source_namespace` | 否 | Fusion实例/来源命名空间 |
| `facts.title` | 是 | 事件自身标题 |
| `facts.description` | 否 | 事件自身说明，非第一条成员标题 |
| `facts.owner_id` | 是 | 当前明确负责人 |
| `facts.assignment_state` | 是 | 未分配/已分配/原值未解析 |
| `facts.owner_source_value` | 否 | 未解析来源负责人 |
| `facts.assigned_at` | 否 | 最近改派时间 |
| `facts.tags` | 是 | 事件业务标签，成员资产标签另外派生 |
| `facts.priority_value` | 否 | 已有优先级0..100 |
| `facts.priority_state` | 否 | 无来源不合成 |
| `facts.priority_source` | 否 | 已有评分生产者 |
| `facts.priority_basis` | 否 | 评分依据 |
| `facts.business_updated_at` | 是 | 自身管理或成员关联变动；移除最后成员仍更新 |
| `facts.reopened_at` | 否 | 最近明确重开时间 |
| `facts.row_version` | 否 | 管理/范围写入乐观版本 |
| `facts.source_incident_id` | 否 | 来源事件ID，兼容原有文本键 |
| `facts.handling_status` | 是 | 事件业务处理状态 |
| `facts.severity_override` | 否 | 人工事件覆盖等级；NULL=采用成员最高；不改成员 |
| `facts.severity_override_reason` | 否 | 人工覆盖依据 |
| `facts.severity_override_at` | 否 | 覆盖设置时间 |
| `facts.severity_override_by` | 否 | 覆盖人 |
| `facts.resolution_note` | 否 | 事件解决说明，人工解决必填 |
| `facts.resolved_at` | 否 | 当前解决周期时间 |
| `facts.resolved_by` | 否 | 解决人 |
| `facts.created_at` | 是 | 事件首次持久化时间 |
| `facts.latest_diagnosis_id` | 否 | 同事件最新成功诊断；失败尝试不能覆盖 |
| `owner_name` | 是 | 本租户人员目录中的负责人显示名；未解析为null。 |
| `derived.member_count` | 是 | 事件当前告警成员数。 |
| `derived.first_activity_at` | 是 | 成员真实event_time最小值；全部缺失为null。 |
| `derived.last_activity_at` | 是 | 成员真实event_time最大值；全部缺失为null。 |
| `derived.severity_auto` | 否 | 成员已知等级最大值；全部未知为null。 |
| `derived.severity_effective` | 是 | 人工覆盖优先，否则使用成员最大等级。 |
| `derived.severity_source` | 是 | manual_override/member_max；无已知等级为null。 |


| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| query | columns | False | string / null | null | 逗号分隔的公开字段路径，按给定顺序输出；省略使用默认列；空列、重复或未知列返回422。全部可选列及默认列见Responses。 |
| query | q | False | string; maxLength=200 / null | null | 标题字面包含或精确UUID搜索；%和_按普通字符处理。 |
| query | severity | False | [Severity](schemas.md#severity) / null | null | 按已知等级精确筛选；省略不筛选。当前没有单独筛选未知等级的参数，不传null字符串。 |
| query | handling_status | False | [WorkStatus](schemas.md#workstatus) / null | null | 主体业务处理状态，与Run执行状态分开。 |
| query | owner_id | False | string (uuid) / null | null | 负责人用户UUID；人员目录由业务后端负责。 |
| query | assignment_state | False | [AssignmentState](schemas.md#assignmentstate) / null | null | 分配状态，unresolved不等于unassigned。 |
| query | time_from | False | string (date-time) / null | null | 带时区的起点，包含；告警按event_time，事件至少一条成员event_time命中，Case按business_updated_at。 |
| query | time_to | False | string (date-time) / null | null | 带时区的终点，不包含；两端同时传时必须晚于time_from。 |
| query | sort_by | False | string created_at, last_activity_at, severity / null | null | 服务排序字段，可选值见本接口枚举；记录排序字段缺值时置后，同值按UUID排序；非法sort_by返回422。 默认created_at。 |
| query | sort_order | False | string asc, desc / null | null | asc升序或desc降序，默认desc。 |


无请求体。

响应类型：string (binary)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "q": "合成示例无记录",
    "columns": "facts.id,facts.title,derived.severity_effective,derived.severity_source,derived.member_count,derived.first_activity_at,derived.last_activity_at,facts.handling_status,facts.owner_id,owner_name,facts.assignment_state,facts.tags,facts.created_at,facts.business_updated_at",
    "sort_by": "severity",
    "sort_order": "desc"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```csv
facts.id,facts.title,derived.severity_effective,derived.severity_source,derived.member_count,derived.first_activity_at,derived.last_activity_at,facts.handling_status,facts.owner_id,owner_name,facts.assignment_state,facts.tags,facts.created_at,facts.business_updated_at
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | permission_denied | 现有读取条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | export_columns_invalid | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | export_pagination_not_supported | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | export_query_parameter_not_supported | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 503 | export_query_timeout | 业务约束/对象状态，见操作说明 |
| 503 | export_snapshot_incomplete | 业务约束/对象状态，见操作说明 |
| 413 | export_row_limit_exceeded | 业务约束/对象状态，见操作说明 |
| 413 | export_size_limit_exceeded | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E55.errors`，Swagger同操作 Responses 可直接展开。

<a id="e56"></a>

## E56 导出调查列表 CSV

`GET /api/v1/socai2/cases/export`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 导出调查列表 CSV。

**输入：** 查询参数：`columns`, `q`, `severity`, `handling_status`, `owner_id`, `assignment_state`, `time_from`, `time_to`, `sort_by`, `sort_order`, `metric`, `classification`；无请求体。

**输出：** HTTP 200，`text/csv；字段名表头，完整CSV，错误仍为JSON`；完整字段和示例见Responses。

**结果：** 返回调查筛选命中的全部记录CSV；已选列按给定顺序，超限明确失败。不会修改记录。

**规则与限制：** 复用相应列表的筛选和排序，导出本次只读快照的全部命中；columns为逗号分隔的公开字段路径，省略使用默认列。禁止limit/cursor/before_id/offset及未知参数；列名空白、重复或不支持返回422。UTF-8 BOM、逗号分隔、CRLF、字段名为表头；空结果200仅表头。null写\N，空串留空；实际以反斜杠开头的字符串额外加一个反斜杠，以单引号开头或可能成为公式的字符串前加单引号，程序读取时按此规则去掉一个前缀再还原；数组/对象为JSON。文件包含完整范围，超过10000行或16MiB返回413，不返回截断文件；SQL限时30秒，超时503。Content-Disposition提供文件名；X-Export-Count为实际条数、X-Export-Observed-At为快照观察时间、X-Export-Schema=socai2.list-export.v1。仅查询，不写库或启动分析。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机62次真实TCP及PG核对：55条告警超过旧单页范围，三类104个公开列与列表逐值一致，行上限413，查询前后数据不变；发布读回见本批回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

**可选输出列（按columns传入顺序）：**

| 列名 | 默认列 | 含义 |
| --- | --- | --- |
| `case.id` | 是 | 该记录的应用UUID，不是页面展示编号或厂商编号。 |
| `case.source_namespace` | 否 | Case固定数据身份命名空间；首次范围绑定后不可改，旧范围不能确认时NULL；不等于原始来源环境 |
| `case.title` | 是 | 名称 |
| `case.description` | 否 | 案情说明 |
| `case.handling_status` | 是 | 业务状态 |
| `case.severity` | 是 | 当前明确案件等级 |
| `case.severity_source` | 否 | 手动设置或明确汇总规则，不从置信度猜 |
| `case.owner_id` | 是 | 当前负责人 |
| `case.assignment_state` | 是 | 分配状态 |
| `case.owner_source_value` | 否 | 历史未解析负责人 |
| `case.assigned_at` | 否 | 最近分配时间 |
| `case.tags` | 是 | 案件标签 |
| `case.priority_value` | 否 | 已有优先级 |
| `case.priority_state` | 否 | 评分状态 |
| `case.priority_source` | 否 | 评分生产者 |
| `case.priority_basis` | 否 | 已有依据 |
| `case.scope_revision` | 否 | 仅当前告警成员真实变动+1 |
| `case.current_assessment_id` | 否 | 已明确采用版本；不等于最新Run |
| `case.classification` | 是 | 明确保存的案件管理分类；NULL未设置，不继承事件或告警 |
| `case.due_at` | 是 | 案件截止时间，与任务期限和运行超时分离 |
| `case.current_evidence_artifact_id` | 否 | 同租户同Case的当前case_evidence_index不可变工件；NULL未记录 |
| `case.created_at` | 是 | 创建时间 |
| `case.created_by` | 否 | 创建人，服务创建见活动 |
| `case.business_updated_at` | 是 | 案件业务变化 |
| `case.resolved_at` | 否 | 当前解决周期时间 |
| `case.resolved_by` | 否 | 明确解决人 |
| `case.resolution_note` | 否 | 解决说明，不擅自添加必填要求 |
| `case.reopened_at` | 否 | 最近重开 |
| `case.row_version` | 否 | 乐观版本 |
| `member_count` | 是 | 当前案件告警成员数。 |
| `open_task_count` | 是 | 当前案件未完成人工任务数。 |


| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| query | columns | False | string / null | null | 逗号分隔的公开字段路径，按给定顺序输出；省略使用默认列；空列、重复或未知列返回422。全部可选列及默认列见Responses。 |
| query | q | False | string; maxLength=200 / null | null | 标题字面包含或精确UUID搜索；%和_按普通字符处理。 |
| query | severity | False | [Severity](schemas.md#severity) / null | null | 按已知等级精确筛选；省略不筛选。当前没有单独筛选未知等级的参数，不传null字符串。 |
| query | handling_status | False | [WorkStatus](schemas.md#workstatus) / null | null | 主体业务处理状态，与Run执行状态分开。 |
| query | owner_id | False | string (uuid) / null | null | 负责人用户UUID；人员目录由业务后端负责。 |
| query | assignment_state | False | [AssignmentState](schemas.md#assignmentstate) / null | null | 分配状态，unresolved不等于unassigned。 |
| query | time_from | False | string (date-time) / null | null | 带时区的起点，包含；告警按event_time，事件至少一条成员event_time命中，Case按business_updated_at。 |
| query | time_to | False | string (date-time) / null | null | 带时区的终点，不包含；两端同时传时必须晚于time_from。 |
| query | sort_by | False | string business_updated_at, created_at, severity / null | null | 服务排序字段，可选值见本接口枚举；记录排序字段缺值时置后，同值按UUID排序；非法sort_by返回422。 默认business_updated_at。 |
| query | sort_order | False | string asc, desc / null | null | asc升序或desc降序，默认desc。 |
| query | metric | False | string awaiting_assignment, in_progress, high_severity, awaiting_human / null | null | Case整体指标快捷过滤条件。 |
| query | classification | False | string true_positive, informational, false_positive / string = not_set / null | null | 案件分类true_positive/informational/false_positive；null未设置；队列可用not_set过滤未设置。 |


无请求体。

响应类型：string (binary)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "q": "合成示例无记录",
    "columns": "case.id,case.title,case.handling_status,case.severity,case.owner_id,case.assignment_state,case.classification,case.due_at,member_count,open_task_count,case.tags,case.created_at,case.business_updated_at",
    "sort_by": "severity",
    "sort_order": "desc"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```csv
case.id,case.title,case.handling_status,case.severity,case.owner_id,case.assignment_state,case.classification,case.due_at,member_count,open_task_count,case.tags,case.created_at,case.business_updated_at
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | permission_denied | 现有读取条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | export_columns_invalid | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | export_pagination_not_supported | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | export_query_parameter_not_supported | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 503 | export_query_timeout | 业务约束/对象状态，见操作说明 |
| 503 | export_snapshot_incomplete | 业务约束/对象状态，见操作说明 |
| 413 | export_row_limit_exceeded | 业务约束/对象状态，见操作说明 |
| 413 | export_size_limit_exceeded | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E56.errors`，Swagger同操作 Responses 可直接展开。

<a id="e57"></a>

## E57 事件归并统计

`GET /api/v1/socai2/incidents/grouping-summary`

状态：**已实现**。分类：事件。

**实现状态：** 已实现

**用途：** 事件归并统计。

**输入：** 查询参数：`source_namespace`, `time_from`, `time_to`；无请求体。

**输出：** HTTP 200，`GroupingSummary`；完整字段和示例见Responses。

**结果：** 返回同一告警范围的6个数量/比例字段、三个筛选条件和观察时间。例6条告警中4条归为2事件、2条未归并，compression_rate=0.5；处理中只数这些事件的实际in_progress状态。

**规则与限制：** 按当前租户告警选范围：source_namespace精确匹配告警来源并区分大小写；time_from/time_to按alerts.event_time，带时区，[起点,终点)，允许单边。时间条件排除未知时间，无时间条件包含。省略三个条件统计全租户。仅支持这三个参数；q/负责人/处理状态/排序/分页等返回422，顶部统计不沿用事件表格筛选。只数范围内告警，按当前关联去重事件；跨范围成员不扩入分母，无范围内成员的事件不计。处理中只按所计事件handling_status=in_progress。压缩比例=(已归并告警数-事件数)/已归并告警数，0..1乘100展示百分比；无已归并告警时null。未归并数量单列，不当成压缩成果，也不代表准确率或解决率。所有数量与observed_at来自同一只读快照，不写库、不触发归并或模型。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机新8告警/4事件/6关系，13次真实TCP与独立SQL计算一致；覆盖已归并/未归并、跨来源、日期及未知时间、空事件和422；查询前后数据保持。两端正式发布另有读回回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| query | source_namespace | False | string; minLength=1; maxLength=256 / null | null | 告警来源命名空间精确匹配，区分大小写；省略为全部来源；空白拒绝422。 |
| query | time_from | False | string (date-time) / null | null | 告警真实event_time的带时区范围：起点包含、终点不含；允许单边；范围内不包含未知时间。省略时间条件则包含未知时间。 |
| query | time_to | False | string (date-time) / null | null | 告警真实event_time的带时区范围：起点包含、终点不含；允许单边；范围内不包含未知时间。省略时间条件则包含未知时间。 |


无请求体。

响应类型：[GroupingSummary](schemas.md#groupingsummary)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "source_namespace": "example"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "schema_version": "socai2.incident-grouping.v1",
  "scope": {
    "source_namespace": "example",
    "time_from": null,
    "time_to": null
  },
  "alert_count": 6,
  "grouped_alert_count": 4,
  "ungrouped_alert_count": 2,
  "incident_count": 2,
  "in_progress_incident_count": 1,
  "compression_rate": 0.5,
  "observed_at": "2026-11-12T08:00:00Z"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | permission_denied | 现有读取条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | grouping_query_parameter_not_supported | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 503 | read_dependency_missing | 业务约束/对象状态，见操作说明 |
| 503 | read_dependency_permission_denied | 业务约束/对象状态，见操作说明 |
| 503 | read_dependency_schema_mismatch | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E57.errors`，Swagger同操作 Responses 可直接展开。

<a id="e58"></a>

## E58 提交Case评论

`POST /api/v1/socai2/cases/{case_id}/comments`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 提交Case评论。

**输入：** 路径参数：`case_id`；JSON请求体：`CaseCommentCreate`，字段和必填要求见Request body。

**输出：** HTTP 200，`CaseCommentView`；完整字段和示例见Responses。

**结果：** 保存同案评论并返回ID、原文、作者和时间；重试返回原评论，不重复写入。任务、Run和当前判断保持。

**规则与限制：** 提交operation_key和body纯文本原文（非空白，最多20000字符）。作者和时间由服务端保存；同案同键同作者同正文返回原评论，改内容或操作者409。只追加，不提供编辑/删除。允许已结案案件补充说明；更新案件业务时间和行版本，但不改变范围、处理状态、当前判断、任务或Run。评论不是已核实事实，不进入模型或自动成为任务。保存后用E59读取，E17回查活动。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机21次真实TCP已完成提交/原文/分页/幂等与冲突，SQL读回一致；未完人工任务、待启动Run及案件判断保持。两端正式发布另见回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 本次评论的幂等键；同案同作者同正文重试沿用，改变意图须新键。 |
| body | 是 | string; minLength=1; maxLength=20000 | 无（可空不等于可省略） | 普通评论纯文本原文，不接受空白；不会自动成为已核实事实或触发调查。 |


响应类型：[CaseCommentView](schemas.md#casecommentview)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "body": "请运维核实维护窗口；本条为协作说明，尚未核实。"
  }
}
```

输出示例（HTTP 200）：

```json
{
  "id": "00000000-0000-4000-8000-000000000015",
  "case_id": "00000000-0000-4000-8000-000000000001",
  "body": "请运维核实维护窗口；本条为协作说明，尚未核实。",
  "author_id": "00000000-0000-4000-8000-000000000010",
  "author_name_snapshot": "analyst@example.invalid",
  "created_at": "2026-11-12T08:00:00Z",
  "edited_at": null,
  "edited_by": null,
  "row_version": 1
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | permission_denied | 缺少对应Case操作能力 |
| 403 | case_actor_not_in_tenant | 业务约束/对象状态，见操作说明 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_not_found | 业务约束/对象状态，见操作说明 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E58.errors`，Swagger同操作 Responses 可直接展开。

<a id="e59"></a>

## E59 读取Case评论

`GET /api/v1/socai2/cases/{case_id}/comments`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 读取Case评论。

**输入：** 路径参数：`case_id`；查询参数：`limit`, `offset`；无请求体。

**输出：** HTTP 200，`CaseCommentPage`；完整字段和示例见Responses。

**结果：** 返回指定Case的评论列表、总数、下一页偏移及观察时间；不返回其他主体评论。

**规则与限制：** 仅指定Case的普通评论，不混入成员告警、事件或其他案件评论。limit默认20、范围1–100，offset默认0、范围0–100000；按created_at及id升序。返回items、total、next_offset和observed_at，空集合明确为空；单次一致快照，跨页非冻结快照。只接受limit/offset，其他参数422。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机21次真实TCP已完成提交/原文/分页/幂等与冲突，SQL读回一致；未完人工任务、待启动Run及案件判断保持。两端正式发布另见回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| query | limit | False | integer; minimum=1; maximum=100 | 20 | 每页评论数，默认20，1–100。 |
| query | offset | False | integer; minimum=0; maximum=100000 | 0 | 跳过已读取评论数，默认0，0–100000；按next_offset续页。 |


无请求体。

响应类型：[CaseCommentPage](schemas.md#casecommentpage)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "limit": 20,
    "offset": 0
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "items": [
    {
      "id": "00000000-0000-4000-8000-000000000015",
      "case_id": "00000000-0000-4000-8000-000000000001",
      "body": "请运维核实维护窗口；本条为协作说明，尚未核实。",
      "author_id": "00000000-0000-4000-8000-000000000010",
      "author_name_snapshot": "analyst@example.invalid",
      "created_at": "2026-11-12T08:00:00Z",
      "edited_at": null,
      "edited_by": null,
      "row_version": 1
    }
  ],
  "total": 1,
  "next_offset": null,
  "observed_at": "2026-11-12T08:00:00Z"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | permission_denied | 缺少对应Case操作能力 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | comment_query_parameter_not_supported | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E59.errors`，Swagger同操作 Responses 可直接展开。

<a id="e60"></a>

## E60 登记Case附件引用

`POST /api/v1/socai2/cases/{case_id}/attachments`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 登记Case附件引用。

**输入：** 路径参数：`case_id`；JSON请求体：`CaseAttachmentCreate`，字段和必填要求见Request body。

**输出：** HTTP 200，`CaseAttachmentView`；完整字段和示例见Responses。

**结果：** 保存文件与Case的关联，返回附件关联ID、原file_id/元数据和登记人/时间；文件由业务后端管理，不触发分析。

**规则与限制：** 业务后端先上传并保存文件，再提交operation_key、file_id、file_name、mime_type、size_bytes及可选sha256。本服务保存案件关联、服务端登记人/时间和活动；同key同意图返回原记录，改意图409；同案同file_id另键重复409。元数据由业务后端声明，文件实时可用性和下载由业务后端决定。本服务不接收文件字节或下载URL、不查验文件，不启动调查或改任务/判断。已结案Case可补充资料，状态保持。E61/E62读回，E17查回执。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机25次真实TCP及独立SQL完成附件引用登记、分页、单项、重放/冲突和跨案404；任务/Run/判断保持。合成文件ID仅验引用，不代表业务后端文件上传/下载通过；两端正式发布见回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |


请求体：

| 字段 | OpenAPI required | 类型与约束 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| operation_key | 是 | string (uuid) | 无（可空不等于可省略） | 本次登记的幂等键；同案同作者同元数据重试沿用。 |
| file_id | 是 | string; minLength=1; maxLength=512 | 无（可空不等于可省略） | 业务后端已保存文件的稳定ID，不是下载URL；文件内容变化须使用新ID。 |
| file_name | 是 | string; minLength=1; maxLength=512 | 无（可空不等于可省略） | 业务后端提供的文件显示名，原值保存，不作为路径使用。 |
| mime_type | 是 | string; minLength=1; maxLength=255 | 无（可空不等于可省略） | 业务后端声明的文件内容类型，例如application/pdf。 |
| size_bytes | 是 | integer; minimum=0.0; maximum=9.223372036854776e+18 | 无（可空不等于可省略） | 业务后端声明的完整文件字节数；本服务不读取文件核验。 |
| sha256 | 否 | string; pattern=^[0-9a-f]{64}$ / null | 无（可空不等于可省略） | 业务后端提供的文件SHA-256；未知可省略或为null，不由本服务计算或验证。 |


响应类型：[CaseAttachmentView](schemas.md#caseattachmentview)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001"
  },
  "body": {
    "operation_key": "00000000-0000-4000-8000-000000000011",
    "file_id": "synthetic-business-file-01",
    "file_name": "维护工单.pdf",
    "mime_type": "application/pdf",
    "size_bytes": 1234,
    "sha256": null
  }
}
```

输出示例（HTTP 200）：

```json
{
  "id": "00000000-0000-4000-8000-000000000009",
  "case_id": "00000000-0000-4000-8000-000000000001",
  "file_id": "synthetic-business-file-01",
  "file_name": "维护工单.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 1234,
  "sha256": null,
  "created_by": "00000000-0000-4000-8000-000000000010",
  "created_at": "2026-11-12T08:00:00Z",
  "file_owner": "business_backend",
  "availability": "managed_by_backend"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | permission_denied | 缺少对应Case操作能力 |
| 403 | case_actor_not_in_tenant | 业务约束/对象状态，见操作说明 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_not_found | 业务约束/对象状态，见操作说明 |
| 409 | operation_key_conflict | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |
| 409 | attachment_already_linked | 业务约束/对象状态，见操作说明；保留用户输入→读最新版本→确认差异后重新提交。 |

完整错误JSON示例见 `examples.json` 的 `E60.errors`，Swagger同操作 Responses 可直接展开。

<a id="e61"></a>

## E61 读取Case附件目录

`GET /api/v1/socai2/cases/{case_id}/attachments`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 读取Case附件目录。

**输入：** 路径参数：`case_id`；查询参数：`limit`, `offset`；无请求体。

**输出：** HTTP 200，`CaseAttachmentPage`；完整字段和示例见Responses。

**结果：** 返回本Case已登记附件目录、总数及下一页偏移；文件是否存在和能否下载由业务后端判断。

**规则与限制：** 仅列本服务登记到本Case的附件引用，不混入其他Case、成员材料或Run报告。limit默认20(1–100)、offset默认0(0–100000)，按created_at/id升序；返回items/total/next_offset/observed_at，空集合为[]。同次只读一致快照，跨请求不冻结。只接受limit/offset。availability=managed_by_backend不代表文件探测或下载成功。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机25次真实TCP及独立SQL完成附件引用登记、分页、单项、重放/冲突和跨案404；任务/Run/判断保持。合成文件ID仅验引用，不代表业务后端文件上传/下载通过；两端正式发布见回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| query | limit | False | integer; minimum=1; maximum=100 | 20 | 每页附件引用数，默认20，1–100。 |
| query | offset | False | integer; minimum=0; maximum=100000 | 0 | 跳过的附件引用数，默认0，0–100000；按next_offset续页。 |


无请求体。

响应类型：[CaseAttachmentPage](schemas.md#caseattachmentpage)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "limit": 20,
    "offset": 0
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "items": [
    {
      "id": "00000000-0000-4000-8000-000000000009",
      "case_id": "00000000-0000-4000-8000-000000000001",
      "file_id": "synthetic-business-file-01",
      "file_name": "维护工单.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 1234,
      "sha256": null,
      "created_by": "00000000-0000-4000-8000-000000000010",
      "created_at": "2026-11-12T08:00:00Z",
      "file_owner": "business_backend",
      "availability": "managed_by_backend"
    }
  ],
  "total": 1,
  "next_offset": null,
  "observed_at": "2026-11-12T08:00:00Z"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | permission_denied | 缺少对应Case操作能力 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | attachment_query_parameter_not_supported | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E61.errors`，Swagger同操作 Responses 可直接展开。

<a id="e62"></a>

## E62 读取Case单个附件信息

`GET /api/v1/socai2/cases/{case_id}/attachments/{attachment_id}`

状态：**已实现**。分类：调查。

**实现状态：** 已实现

**用途：** 读取Case单个附件信息。

**输入：** 路径参数：`case_id`, `attachment_id`；无请求体。

**输出：** HTTP 200，`CaseAttachmentView`；完整字段和示例见Responses。

**结果：** 返回本Case单个附件引用信息，供业务后端按file_id提供下载；不返回文件内容或下载地址。

**规则与限制：** 按Case和附件关联ID读取原file_id、名称、类型、大小、可选哈希及登记人/时间。该ID是本服务关联ID，file_id才是业务后端下载时使用的文件ID；下载地址由业务后端提供。本接口不返回文件字节或下载URL，不报告未核验的文件存在性。不存在或跨案件404，不接受查询参数。

**验证结果（列表更新于2026-11-13；其他沿既有验收）：** 本机25次真实TCP及独立SQL完成附件引用登记、分页、单项、重放/冲突和跨案404；任务/Run/判断保持。合成文件ID仅验引用，不代表业务后端文件上传/下载通过；两端正式发布见回执。

**部署情况：** 对应本机18024版本为case-attachments-20261113-r1-local，21正式18024为case-attachments-20261113-r1；合同含62操作，实际发布见部署回执，本机使用v12_upgrade_dev，21使用aisoc。

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| path | case_id | True | string (uuid) | null | Case UUID；来自真实回执/列表，不是页面展示编号。 |
| path | attachment_id | True | string (uuid) | null | E60/E61返回的附件关联id，不是业务后端file_id。 |


无请求体。

响应类型：[CaseAttachmentView](schemas.md#caseattachmentview)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "case_id": "00000000-0000-4000-8000-000000000001",
    "attachment_id": "00000000-0000-4000-8000-000000000009"
  },
  "body": null
}
```

输出示例（HTTP 200）：

```json
{
  "id": "00000000-0000-4000-8000-000000000009",
  "case_id": "00000000-0000-4000-8000-000000000001",
  "file_id": "synthetic-business-file-01",
  "file_name": "维护工单.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 1234,
  "sha256": null,
  "created_by": "00000000-0000-4000-8000-000000000010",
  "created_at": "2026-11-12T08:00:00Z",
  "file_owner": "business_backend",
  "availability": "managed_by_backend"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | permission_denied | 缺少对应Case操作能力 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | attachment_query_parameter_not_supported | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |
| 404 | case_not_found | 业务约束/对象状态，见操作说明 |
| 404 | case_attachment_not_found | 业务约束/对象状态，见操作说明 |

完整错误JSON示例见 `examples.json` 的 `E62.errors`，Swagger同操作 Responses 可直接展开。
