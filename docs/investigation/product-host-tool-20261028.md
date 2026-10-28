# Case产品HTTP Tool：主机详情

2026-10-28。[后续功能计划](next-phase-plan-20261028.md)第3批代码已接通。首个能力是已有CrowdStrike `get_host`，不虚构当前适配器没有的父进程链或历史遥测字段。本批未部署、未连接真实厂商账号。

## 调用流程与来源绑定

1. 调用既有 `POST /api/v2/investigation/cases/{case_id}/investigation-context` 预览。Case成员告警的 `Alert.connector_id` 作为 `evidence[].data.source_connector_id`；每条告警的 `hosts` 独立保留。
2. 服务端读取这些精确ID对应的本租户连接器，仅对已启用、类型为`crowdstrike`、`allowed_capabilities`未限制或包含`get_host`的实例生成工具。无事件湖配置时，此产品工具也可单独使用。
3. 实际调查启动时重新读取材料，模型工具定义包含`product_host_details`。模型提交`source_alert_id`和`hostname`；程序核对主机属于该告警，并绑定其来源连接器。模型不能提交URL、凭据、tenant、产品名或任意查询。
4. 执行前按tenant及精确connector ID重新读取实例，检查启用与能力，解密其`client_id`/`client_secret`，采用配置的`base_url`。不按产品类型选择另一个连接器；缺少凭据返回不可用。
5. 通过原`actions_client.dispatch_live_action`发送HTTP到Actions。固定`vendor_id=crowdstrike`、`capability=get_host`、目标主机及当前Case；`dry_run=false`用于实际只读查询。
6. Actions沿已有凭据映射、治理与CrowdStrike适配器获取设备信息。只有`status=succeeded`且结果合同完整才算可用，模拟/审批/失败状态都不当作查询完成。
7. 映射结果成为`E1`等工具证据，与原`tool_call_id`一起回传模型。沿现有步骤、完整结果工件和Markdown保存；报告证据索引包含设备ID、连接器、来源告警、请求ID和快照限制。

地址与凭据只在服务端HTTP边界使用，不写入模型消息或报告。当前支持字母、数字、点、下划线、连字符组成的1–253字符主机名；不匹配的主机不会生成此工具绑定。

## 一个实际代码路径的例子

Case成员告警A1来自连接器`00000000-0000-0000-0000-000000000046`，主机`host-01`。以下均为直接验证中的合成数据。

模型选择：

```json
{"name":"product_host_details","arguments":{"source_alert_id":"00000000-0000-0000-0000-000000000001","hostname":"host-01"}}
```

API发出的业务字段：

```json
{"vendor_id":"crowdstrike","capability":"get_host","target":"host-01","tenant_id":"当前租户UUID","case_id":"当前Case UUID","params":{},"dry_run":false,"requested_by":"aisoc-case-analysis"}
```

同一请求的`auth_config`由服务端加入实际连接器凭据，不进入公开证据。Actions向该连接器的产品地址发出：

| 顺序 | HTTP调用 | 输入 | 采用的输出 |
| --- | --- | --- | --- |
| 1 | POST `/oauth2/token` | 表单`client_id/client_secret` | `access_token`，仅内部使用 |
| 2 | GET `/devices/queries/devices/v1` | `filter=hostname:'host-01'`、`limit=1` | `resources[0]`设备ID；空数组表示未找到 |
| 3 | GET `/devices/entities/devices/v2` | `ids=device-01` | 设备记录；只有步骤2找到ID才执行 |

设备返回`platform_name`映射为`platform`，`status`映射为`containment_status`；其余采用`device_id/hostname/os_version/agent_version/local_ip/external_ip/last_seen/first_seen/tags`。设备ID存在但读取失败属于查询失败。返回主机名必须与请求主机名一致（忽略大小写），否则返回`product_host_mismatch`。

Case规范结果示意（rows省略空字段）：

```json
{
  "available": true,
  "query_id": "本次API查询UUID",
  "upstream_request_id": "Actions请求UUID",
  "observed_at": "2026-10-28T01:00:00+00:00",
  "source": {"source_alert_id":"00000000-0000-0000-0000-000000000001","connector_id":"00000000-0000-0000-0000-000000000046","vendor_id":"crowdstrike","capability":"get_host"},
  "query_scope": {"hostname":"host-01","time_semantics":"current_snapshot"},
  "rows": [{"device_id":"device-01","hostname":"host-01","platform":"Windows","containment_status":"normal"}],
  "returned_count": 1,
  "truncated": false,
  "limitation": "产品返回查询时的主机快照，不覆盖Case历史时间窗口，不包含进程树；未找到主机不证明安全。"
}
```

正常无匹配：`available=true, rows=[], returned_count=0`。HTTP失败：`available=false, rows=[], reason=product_query_failed`；上游返回失败等状态为`product_query_not_succeeded`，保留`upstream_status`。原始上游错误正文不交给模型。

`observed_at`记录本次读取开始时间，不是厂商记录发生时间；`last_seen`保留厂商实际字段。该工具不发送Case时间窗口，不能用当前在线或隔离状态证明历史时刻状态。新Run即使其他材料完全相同，也重新查询产品快照；事件湖固定窗口查询继续沿用原复用规则。

## 直接验证与边界

- API侧2个直接用例覆盖正常链路，以及空结果/失败两个子场景：实际Case ASGI路由、模型HTTP协议、Actions HTTP请求、来源绑定、Tool消息、证据步骤、报告、新Run重新查询；数据库、模型和Actions响应使用替身。
- Actions侧3个参数化场景使用已有实际凭据映射、`CrowdStrikeGetHost`及HTTP客户端，核对认证表单、主机过滤条件、设备ID参数和字段解析；厂商HTTP响应为MockTransport替身。
- 受影响的既有Case直接用例7个通过。未重复其他模块测试。OpenSpec CLI在当前Shell不可用，未执行严格CLI校验；规格文件已保存，不据此声称校验通过。
- 未测试真实PG、真实模型自主选工具、真实Actions服务治理配置或真实CrowdStrike授权与产品返回。未部署、未执行迁移、未发真实响应动作。

实现：[产品工具](../../services/api/app/investigation_v2/case_product_tools.py)、[Case工具组合](../../services/api/app/investigation_v2/case_analysis_tools.py)、[Case循环](../../services/api/app/investigation_v2/case_analysis.py)。验证：[API流程](../../services/api/tests/test_case_product_tool.py)、[厂商HTTP映射](../../services/actions/tests/test_case_host_http.py)。新增其他工具遵循[接入指南](tool-onboarding-and-flow-verification.md)，无需复制一个通用模拟平台。
