# 后端联调：测试数据与操作步骤

2026-11-12。适用21独立 API `http://192.168.1.21:18024`，Swagger `http://192.168.1.21:18080/`。Mac 已配置转发时可用 `http://127.0.0.1:28024`。本机18024是另一个隔离库，不能混用以下ID。

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
