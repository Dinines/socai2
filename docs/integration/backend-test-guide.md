# 后端联调：测试数据与操作步骤

2026-11-13。适用21独立 API `http://192.168.1.21:18024`，Swagger `http://192.168.1.21:18080/`。Mac 已配置转发时可用 `http://127.0.0.1:28024`。本机18024是另一个隔离库，不能混用以下ID。

## 1. 可直接读取的三条测试告警

以下是21已经存在、标注 `synthetic/production-multialert-20261108-01` 的合成验收数据，本轮经正常HTTP重新读取。登录、进程、连接是三类观察，不代表已经证明恶意或已授权。只读复用原验收记录，写操作新建自己的 Case。

| 对象 | 真实 ID | 可验证内容 |
| --- | --- | --- |
| 登录告警 | `09e91978-d201-5435-901e-b6a40368b921` | 事实、原始材料、已有分诊、来源/事件关联 |
| 进程启动告警 | `3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3` | 进程类材料、分诊和工件 |
| 外联连接告警 | `65e2a5f9-3b00-5def-9547-c21f1b9cc4bf` | 网络类材料和查询结果 |
| 关联事件 | `06f82d36-1964-4186-aed3-4c7b9ab1a375` | 事件详情、成员和已有诊断 |
| 三成员 Case | `9c1b65d3-e7e7-5b99-8bf1-eea8ebd8283c` | Case详情、三成员、人工任务及版本；Run未启动 |
| 管理验收 Case | `d5ef9c5a-00c9-564a-9fcb-fdb5810f890e` | 管理读取、关闭/重开历史、未完任务 |
| 管理验收 Case 的 Run | `45ea262b-9ee3-41b0-963e-6b99fbcff1bd` | `pending_update`、尚未启动；不应出现伪造调查结论 |

机器可读清单：[live-21-fixtures.json](examples/current/live-21-fixtures.json)。这些ID需要同一联调租户的有效凭据；其他租户返回404时先核账号，不将其解释成接口未实现。

## 2. 先跑读取

以下在终端执行；替换凭据值，或在 Swagger Authorize 中填写同一值。curl不受浏览器CORS影响。

```sh
SOCAI2_API=http://192.168.1.21:18024
SOCAI2_TOKEN='<现有有效Bearer凭据>'
curl --fail-with-body -sS "$SOCAI2_API/api/v1/socai2/alerts/09e91978-d201-5435-901e-b6a40368b921" -H "Authorization: Bearer $SOCAI2_TOKEN"
curl --fail-with-body -sS "$SOCAI2_API/api/v1/socai2/alerts/09e91978-d201-5435-901e-b6a40368b921/analysis" -H "Authorization: Bearer $SOCAI2_TOKEN"
curl --fail-with-body -sS "$SOCAI2_API/api/v1/socai2/incidents/06f82d36-1964-4186-aed3-4c7b9ab1a375" -H "Authorization: Bearer $SOCAI2_TOKEN"
curl --fail-with-body -sS "$SOCAI2_API/api/v1/socai2/incidents/06f82d36-1964-4186-aed3-4c7b9ab1a375/records/members" -H "Authorization: Bearer $SOCAI2_TOKEN"
curl --fail-with-body -sS "$SOCAI2_API/api/v1/socai2/cases/9c1b65d3-e7e7-5b99-8bf1-eea8ebd8283c" -H "Authorization: Bearer $SOCAI2_TOKEN"
```

预期：HTTP200；告警的 `facts.id` 与请求一致，`facts.tags` 含 synthetic；详情的 `analysis_url/section_urls` 给后续取数路径；Case `member_count=3`。字段为空就按未提供处理，`current_assessment=null` 不代表接口失败。分诊目录的当前结果和失败尝试分别读取，不挑最近一条冒充有效判断。

## 3. 不调用模型，走通 Case 管理写读

### 在 Swagger 逐步操作

1. **E01 创建**：用[create-case.json](examples/current/create-case.json)，将 `operation_key` 改为本次新 UUID、标题加自己的联调批次；保存返回的 `case_id/pending_run_id/scope_revision`。
2. **E44 读取管理**：获取 `case.row_version`、`open_task_count` 和关闭条件。
3. **E45 修改**：传新 `operation_key`、最新 `expected_row_version`、自己的标题或标签。GET E03/E44核对保存后字段；重复同一请求应返回同一回执。新key配旧版本应409，非法title=null应422。
4. **E38 建人工任务**：填 `title/operation_key/expected_scope_revision`，这里用Case范围版本。GET E39/E41可读当前任务和任务行版本。
5. **E46 关闭**：重新E44取Case行版本。未完任务存在时，不带确认应409；明确提交 `acknowledge_open_tasks=true` 和非空 `reason` 后关闭。任务保持原状态，不自动完成。
6. **E47 重开**：带最新Case行版本、新key和可选理由；结果为 `handling_status=in_progress`，当前结案字段清空；E17能读到原关闭和重开记录。
7. **E12 核对 Run**：仍为pending_update、started_at=null；上述操作没有启动模型或调查。

UUID可用 `python3 -c 'import uuid; print(uuid.uuid4())'` 生成；同一次写入的重试保留原key，新意图用新key。不要关闭、修改上表的共享历史Case。

### 用已有脚本一次执行同一管理流程

已有 `deploy/http-service/verify_management.py` 已在本机和21通过；只用Python标准库。它新建一个Case，执行20个HTTP请求，包含预期409/422、幂等、关闭/重开和读取；**不启动 Run、不调用模型、不删数据**。输出目录必须为新目录，避免未知结果被盲目重派。

```sh
mkdir -p .local/backend-integration
cp docs/integration/examples/current/management-profile.json .local/backend-integration/profile.json
```

编辑 profile 的 `base_url`、标题及凭据文件路径。在 `.local/backend-integration/credentials.json` 保存 `{"api_key":"现有有效Bearer值"}`（这个工具的字段名叫api_key，也可存已取得的用户Bearer值）；不要提交凭据。选用正常用户身份，Case写入需要真实用户。然后运行：

```sh
python3 deploy/http-service/verify_management.py --profile .local/backend-integration/profile.json --output .local/backend-integration/run-001
```

成功末尾为 `state=passed/requests=20/real_model_calls=0/run_started=false`，返回新Case/Run/任务ID；`responses.json`和每一步intent可给开发者定位错误。失败先看已保存响应，不能删目录后同批重跑；修正后新建批次，原记录保留。

## 4. 人工任务完成与真实分析单独跑

任务修订是 **E40 PUT完整提交**：先读E41取得任务行版本，E03取Case范围版本；在原字段基础上修改。completed时必须给 `result_text` 和 `result_scope`，如 `kind=selected_alerts/alert_ids=[本Case成员UUID]/object_keys=[]/window_start=null/window_end=null/limitations=[]`。保留需要的标题、负责人、期限和来源；省略其他TaskFields会使用默认值，不能把PUT当PATCH。E42/E43读旧修订，确认未覆盖。

确需验证实际分析时，在自己的批次分别执行：

| 操作 | 输入 | 保存后读取 |
| --- | --- | --- |
| E36 告警分诊 | 指定告警UUID，`{"operation_key":"本次UUID"}` | E22/E24目录与Run，E32/E33步骤工件 |
| E37 事件诊断 | 指定事件UUID，同样带key | E23/E25目录与Run；检查成员覆盖及诊断结果 |
| E13 Case启动 | 自己创建的pending Run，`operation_key/expected_scope_revision`；可选成对时间窗 | E12 → 返回的结果ID → E14；核执行、交付、校验及结论，不能只判断200 |
| 反馈后再调查 | E11 prepare带范围版本和key → E13 start | 新Run冻结任务当前版本，旧Run保留 |

这些调用会真正查询和调用模型，返回可能partial/failed/unknown。现有模型质量NOT_PASSED仍保留；超时或未知先GET原Run，不换key重跑。联调脚本的“通过”不代表所有模型结论质量通过。E19–E21仍501。

## 5. 想从 Kafka 造自己的数据

[raw-alerts.json](examples/current/raw-alerts.json)提供登录、进程、网络三条**尚未投递**的合成消息，使用文档保留IP和测试主机名。数组只是分发文件，发送时每个元素为一条UTF-8 JSON消息，不能整数组发到raw Topic。

1. 将tenant_id替换为已接入的真实联调租户；为新批次生成三个不同上游UUID，分别同步id/source_alert_id；同批重投保持UUID、source和正文。时间、主机名、source_event_ids按本批明确设置。
2. 按[Kafka连接与合同](component-handoff-current.md#2-kafka-实际-topic-与消费组)连接 `192.168.1.21:19093`，发送到 `socai2.alerts.raw`，保存broker回执。
3. 在自己的消费组读取 `socai2.alerts.fused`，按`tenant_id`与`alert.source_alert_id`匹配本批，记录返回canonical告警UUID和incident_id。消息可能重复，按稳定身份幂等。
4. 用18024的GET读取最终UUID，确认原文、来源和事件关联已出现。是否归到同一事件以实际Fusion结果为准，不把共享主机写成攻击因果。
5. 再显式调用E36/E37，或创建Case并start；只投Kafka不会自动完成AI调查。

本轮只校验样例格式，没有替后端投递这三条消息。需要完整湖补查时还要按事件信封提供相应日志；三条告警不等于已填充ClickHouse查询上下文。

[4173测试页面及数据说明](test-page-4173.md) · [产品需求](../design/alert-incident-case-product-requirements.md) · [125项功能](../../deliverables/investigation-validation-20261106/frontend-feature-list.md) · [确认规则](../design/investigation-product-decisions.md) · [HTTP总指南](../../FRONTEND_BACKEND_HANDOFF.md)


## 告警人工判定与告警事件管理

当前新增六个操作，路径都加 `/api/v1/socai2`。先 GET 告警／事件详情，取 `facts.id`、`facts.row_version`。以下 UUID 为独立合成示例，不能直接向真实记录发送；正式联调请使用双方约定的测试对象。

21已完成本批管理验收，可只读查看告警`a631df8d-5268-446d-bd0d-cb63a549f89c`、事件`9dbd1442-8164-40c2-9acb-4408850548d7`及Case`0407cdc9-141c-5cb6-95a5-13ecfbfe62a3`的详情和活动，观察反馈、管理字段及修改前后值。完整对象清单见[21合成测试数据](../operations/evidence/subject-management-20261112-01/21-fixture.json)，实际请求／响应见[验收回执](../operations/evidence/subject-management-20261112-01/21-http/verification.json)。这些是已结束验收记录，写入联调使用新测试批次；材料里的分诊为合成fixture，不代表真实模型结论。

| 功能 | 方法与路径 | 输入的业务内容 | 结果与读回 |
| --- | --- | --- | --- |
| 单条告警人工判定 E48 | `POST /alerts/{alert_id}/feedback` | `operation_key`、`expected_row_version`、`disposition`、非空`reason` | 追加人工反馈，返回主体快照及反馈ID；GET详情的`feedback`读理由，`facts`读状态 |
| 批量人工判定 E49 | `POST /alerts/feedback-batch` | 操作键、`items`逐条ID/版本、共用`feedback` | 整批校验保存，返回每条结果；不自动选择相似告警 |
| 单条告警管理 E50 | `PATCH /alerts/{alert_id}/management` | 操作键、版本；`owner_id`、`tags`、`handling_status`中需改的字段，关闭带`reason` | 保存管理字段，原判定和分诊保留 |
| 批量告警管理 E51 | `POST /alerts/management-batch` | 操作键、`items`、共用`changes` | 只修改选中对象，逐项返回新版本 |
| 单个事件管理 E52 | `PATCH /incidents/{incident_id}/management` | 操作键、版本；负责人、标签、状态、等级覆盖及对应理由 | 保存后GET事件详情的`derived`读取有效等级及来源 |
| 批量事件管理 E53 | `POST /incidents/management-batch` | 操作键、`items`、共用`changes` | 规则与单条一致，整批成功或拒绝，不修改成员等级 |

单条人工判定请求：

```json
{
  "operation_key": "00000000-0000-4000-8000-000000000901",
  "expected_row_version": 3,
  "disposition": "false_positive",
  "reason": "经人工核实，本次检测为误报"
}
```

批量事件解决请求：

```json
{
  "operation_key": "00000000-0000-4000-8000-000000000902",
  "items": [
    {"id": "00000000-0000-4000-8000-000000000903", "expected_row_version": 2},
    {"id": "00000000-0000-4000-8000-000000000904", "expected_row_version": 4}
  ],
  "changes": {"handling_status": "resolved", "resolution_note": "所选事件均已人工核实处理"}
}
```

批量反馈将`changes`替换为`feedback`，内容为`disposition`和`reason`。默认最多100个明确选择的对象；空选择、重复ID或超限返回422。单条和批量每次操作用一个新`operation_key`，同意图网络重试沿用；同键改内容409。批量中任一版本过期、对象不存在或理由不完整，全部不保存；不要把失败当部分成功。

单条响应包含以下全部字段；批量响应为`operation_key`、`items`（单条响应数组，按ID排序）、`changed_count`（实际变更对象数）：

| 返回字段 | 含义 |
| --- | --- |
| `kind` | `alerts`或`incidents` |
| `facts` | 保存当时的完整主体字段，结构与原详情`facts`相同；下次修改取其中`row_version` |
| `changed` | 是否改变主体；相同管理值可为false，新人工反馈为true |
| `feedback_id` | 本次新人工反馈ID，管理操作为null |
| `activity_id` | 本次活动ID；从`/{alerts或incidents}/{id}/records/activities`读原值、新值和理由 |

反馈四值：`true_positive`真实威胁、`false_positive`误报、`benign`正常/授权、`needs_review`需跟进。误报/正常使告警`completed`；已关闭改真实威胁/需跟进恢复`in_progress`。管理时仅分配不改告警状态；人工直接关闭必须有理由，不改原判定。

事件分配未解决对象默认进入`in_progress`，已解决只换负责人保持`resolved`；显式解决须`resolution_note`。`severity_override`设置非null需同时给`severity_override_reason`，清空覆盖用null并省略理由；清空后恢复成员自动等级。省略字段不改，`owner_id=null`取消分配，`tags=[]`清空；`handling_status`和`tags`不接受null，不能人工写unknown。

错误：404 `subject_not_found`；409 `subject_row_version_conflict`／`operation_key_conflict`；422 字段校验或`subject_owner_not_in_tenant`、`subject_batch_selection_invalid`、`alert_close_reason_required`。解决或覆盖理由缺失由字段校验返回422。未知执行先GET确认，不自动换键重新提交。写入不调用模型，不启动Run，不自动关闭/重开父事件或Case。


## 三类列表筛选、排序和分页

E26告警、E27事件、E02调查列表已经支持全库查询。先用本页同环境的真实ID执行 `GET /api/v1/socai2/alerts?q=<告警UUID>&sort_by=event_time&sort_order=desc&limit=20`；事件路径改为 `/incidents`、sort_by改为`last_activity_at`，调查改为 `/cases`、sort_by改为`business_updated_at`。返回该主体，不修改状态或启动分析。

要连续翻页，将q改为待搜索的标题片段；也可按severity、handling_status、owner_id、assignment_state筛选。使用带时区的time_from/time_to时要URL编码，范围前闭后开：告警按实际发生时间，事件至少一条成员告警在范围内，Case按业务更新时间。sort_order为asc或desc，未知时间/等级始终在最后。

读取items后，将next_cursor原样URL编码为下次cursor，保持其他条件；null表示结束。改条件或排序时清空cursor。告警/事件filtered_total表示全部筛选命中数，total/overall_stats保持租户整体；Case total表示筛选数，metrics保持整体。旧告警/事件before_id仅在无新增条件时可用，不能和cursor、新筛选或排序混用。

非法排序、日期无时区、起点不早于终点、游标非法或与条件不符返回422；旧before_id主体不存在返回404。具体输入输出、字段及错误示例见[Swagger交接](../../deliverables/investigation-validation-20261106/http-handoff/README.md#列表查询怎么用)。完整CSV导出使用E54/E55/E56；列表和导出均不会触发模型。

## 下载完整筛选结果

导出接口为`GET /api/v1/socai2/alerts/export`、`incidents/export`、`cases/export`。沿用列表筛选排序、可加`columns`；不传分页参数。21可用上面的合成管理批次标题查询：

```sh
curl --fail-with-body --get "$API/api/v1/socai2/alerts/export" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'q=SYNTHETIC subject management a0735538-3c99-40a8-8af0-f1f6e14a0641' \
  --data-urlencode 'columns=facts.id,facts.title,facts.handling_status,facts.disposition' \
  --output synthetic-alerts.csv
```

该21合成组应命中3条；相同q用于事件导出也是3条。调查可用`q=d5ef9c5a-00c9-564a-9fcb-fdb5810f890e`读取1条。仅GET，不触发分析或修改。当前上限10000行/16MiB，错误返回JSON；空结果CSV仅表头。[默认列、空值/转义和错误规则](../../deliverables/investigation-validation-20261106/http-handoff/README.md#完整列表导出)。本机专属55条合成告警及3事件/3Case见[新批次数据](../operations/evidence/list-export-20261113-01/fixture.json)，不能拿本机ID在21查询。

## 事件归并统计联调

使用E57 `GET /api/v1/socai2/incidents/grouping-summary`，可先只读查询21既有合成来源：

```sh
curl --fail-with-body --get "$API/api/v1/socai2/incidents/grouping-summary" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'source_namespace=synthetic-subject-management'
```

该来源记录可能继续增加，以接口实际数量为准。输入仅来源与可选发生时间范围，不传q、负责人、状态或分页；完整字段和比例解释见[归并统计指南](../../deliverables/investigation-validation-20261106/http-handoff/README.md#事件归并统计)。本机专属[新合成批次](../operations/evidence/grouping-summary-20261113-01/fixture.json)主来源6告警，4条归为2事件，2条未归并，处理中1事件，比例0.5；次来源用于核对跨来源成员，不在21复写。查询不修改事件或触发调查。
