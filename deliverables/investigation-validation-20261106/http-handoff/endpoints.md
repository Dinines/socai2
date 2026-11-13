# 调查HTTP接口目录（53项）

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

**验证结果（2026-11-12）：** 本机TCP及21正式HTTP已完成本批Case/H直接操作；保存值与SQL读回一致，Run未启动。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**输入：** 查询参数：`limit`, `cursor`, `q`, `handling_status`, `severity`, `owner_id`, `assignment_state`, `metric`, `classification`；无请求体。

**输出：** HTTP 200，`CaseQueuePage`；完整字段和示例见Responses。

**结果：** 返回符合条件的案件列表、下一页游标，以及不受列表筛选影响的租户案件指标。

**规则与限制：** q 搜索标题/完整 ID；可按处理状态、严重度、负责人、分配状态、metric、classification 筛选。total 是筛选结果数，metrics 是租户整体；high_severity 只计 high。使用 next_cursor，改变条件须清空 cursor。

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e02) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| query | limit | False | integer; minimum=1; maximum=50 | 20 | 本次最多返回条数；不是总量。默认值及上限见字段约束。 |
| query | cursor | False | string; maxLength=1024 / null | null | 使用服务上一页 next_cursor；改变筛选条件后清空。 |
| query | q | False | string; maxLength=200 / null | null | Case标题或完整ID搜索；告警/事件列表不支持此参数。 |
| query | handling_status | False | [WorkStatus](schemas.md#workstatus) / null | null | 主体业务处理状态，与Run执行状态分开。 |
| query | severity | False | [Severity](schemas.md#severity) / null | null | 严重度枚举；null为未知，不强行补默认等级。 |
| query | owner_id | False | string (uuid) / null | null | 负责人用户UUID；人员目录由业务后端负责。 |
| query | assignment_state | False | [AssignmentState](schemas.md#assignmentstate) / null | null | 分配状态，unresolved不等于unassigned。 |
| query | metric | False | string awaiting_assignment, in_progress, high_severity, awaiting_human / null | null | Case整体指标快捷过滤条件。 |
| query | classification | False | string true_positive, informational, false_positive / string = not_set / null | null | 案件分类true_positive/informational/false_positive；null未设置；队列可用not_set过滤未设置。 |


无请求体。

响应类型：[CaseQueuePage](schemas.md#casequeuepage)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "limit": 20
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
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | invalid_case_cursor | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 422 | case_cursor_filters_changed | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
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

**验证结果（2026-11-12）：** 本机TCP及21正式HTTP已完成本批Case/H直接操作；保存值与SQL读回一致，Run未启动。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机TCP及21正式HTTP已完成本批Case/H直接操作；保存值与SQL读回一致，Run未启动。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库的执行、保存和读取通过；模型/外部查询为替身，真实模型效果未据此验收。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 已确认返回501，功能未实现。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 已确认返回501，功能未实现。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 已确认返回501，功能未实现。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**输入：** 查询参数：`limit`, `before_id`；无请求体。

**输出：** HTTP 200，`SubjectPage`；完整字段和示例见Responses。

**结果：** 返回告警列表、基础信息、负责人名称、汇总信息、统计和下一页游标。

**规则与限制：** 仅有 limit/before_id 分页，没有 q、严重度、状态、日期等完整筛选入参。overall_stats 是服务统计；前端对已加载集合的过滤不能当全库搜索或全量导出。

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e26) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| query | limit | False | integer; minimum=1; maximum=50 | 20 | 本次最多返回条数；不是总量。默认值及上限见字段约束。 |
| query | before_id | False | string (uuid) / null | null | 沿上页 next_before_id 翻页。 |


无请求体。

响应类型：[SubjectPage](schemas.md#subjectpage)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "limit": 20
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
  "observed_at": "2026-11-12T08:00:00Z"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | invalid_page_limit | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |

完整错误JSON示例见 `examples.json` 的 `E26.errors`，Swagger同操作 Responses 可直接展开。

<a id="e27"></a>

## E27 事件列表

`GET /api/v1/socai2/incidents`

状态：**已实现**。分类：事件。

**实现状态：** 已实现

**用途：** 事件列表。

**输入：** 查询参数：`limit`, `before_id`；无请求体。

**输出：** HTTP 200，`SubjectPage`；完整字段和示例见Responses。

**结果：** 返回事件列表、基础信息、汇总信息、统计和下一页游标。

**规则与限制：** 仅有 limit/before_id；按 next_before_id 分页。当前没有完整搜索/日期过滤。derived/overall_stats 按事件口径，不拿加载页数当全量。

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

[本接口用途及完整输出字段审计](audit/interfaces.html#e27) · [动态投影与差异](audit/dynamic-fields.html)

| 位置 | 参数 | 必传 | 类型/限制 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| query | limit | False | integer; minimum=1; maximum=50 | 20 | 本次最多返回条数；不是总量。默认值及上限见字段约束。 |
| query | before_id | False | string (uuid) / null | null | 沿上页 next_before_id 翻页。 |


无请求体。

响应类型：[SubjectPage](schemas.md#subjectpage)。字段完整展开见Schema或Swagger Models。

输入示例（参数与JSON体）：

```json
{
  "parameters": {
    "limit": 20
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
  "observed_at": "2026-11-12T08:00:00Z"
}
```

| HTTP | 错误/形状 | 处理 |
| --- | --- | --- |
| 401 | not_authenticated | 缺少有效已有凭据 |
| 403 | identity | 现有身份/访问条件不符 |
| 422 | validation | UUID、枚举、长度、额外字段或跨字段约束不符；参数修正前不重试。 |
| 422 | invalid_page_limit | 业务约束/对象状态，见操作说明；参数修正前不重试。 |
| 503 | feature_disabled | 服务对应功能开关关闭 |

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库的执行、保存和读取通过；模型/外部查询为替身，真实模型效果未据此验收。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库的执行、保存和读取通过；模型/外部查询为替身，真实模型效果未据此验收。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机TCP及21正式HTTP已完成本批Case/H直接操作；保存值与SQL读回一致，Run未启动。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机原路由及真实隔离库直接检查通过；21已核对路由和结构，本轮未重复调用此操作。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机TCP及21正式HTTP已完成本批Case/H直接操作；保存值与SQL读回一致，Run未启动。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机TCP及21正式HTTP已完成本批Case/H直接操作；保存值与SQL读回一致，Run未启动。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机TCP及21正式HTTP已完成本批Case/H直接操作；保存值与SQL读回一致，Run未启动。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机TCP及21正式HTTP已完成本批Case/H直接操作；保存值与SQL读回一致，Run未启动。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机及21正式HTTP完成管理读取/局部更新、结案与重开，SQL读回一致；任务/Run保持，版本冲突和未完任务确认已验证。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机及21正式HTTP完成管理读取/局部更新、结案与重开，SQL读回一致；任务/Run保持，版本冲突和未完任务确认已验证。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机及21正式HTTP完成管理读取/局部更新、结案与重开，SQL读回一致；任务/Run保持，版本冲突和未完任务确认已验证。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机及21正式HTTP完成管理读取/局部更新、结案与重开，SQL读回一致；任务/Run保持，版本冲突和未完任务确认已验证。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机六项单条/批量HTTP、状态联动、幂等/冲突及SQL读回已验；21发布和验收见本批部署回执。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机六项单条/批量HTTP、状态联动、幂等/冲突及SQL读回已验；21发布和验收见本批部署回执。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机六项单条/批量HTTP、状态联动、幂等/冲突及SQL读回已验；21发布和验收见本批部署回执。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机六项单条/批量HTTP、状态联动、幂等/冲突及SQL读回已验；21发布和验收见本批部署回执。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机六项单条/批量HTTP、状态联动、幂等/冲突及SQL读回已验；21发布和验收见本批部署回执。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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

**验证结果（2026-11-12）：** 本机六项单条/批量HTTP、状态联动、幂等/冲突及SQL读回已验；21发布和验收见本批部署回执。

**部署情况：** 本机18024为subject-management-20261112-r1-local，21正式18024为subject-management-20261112-r1；两端均已挂载53操作，本机使用v12_upgrade_dev，21使用aisoc。

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
