# C4.deep 已保存输入的材料清单

这是历史请求的只读展开，供设计核对；不是新的模型请求。下列正文和旧编号保持原样。

## question

```json
{
  "answer": null,
  "evidence_refs": [],
  "evidence_requirements": [
    "影响对象、行为与证据；图可达不等于受影响"
  ],
  "id": "impact",
  "limitations": [],
  "scope": {
    "alert_ids": [
      "09e91978-d201-5435-901e-b6a40368b921",
      "3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3",
      "65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"
    ],
    "kind": "whole_case",
    "limitations": [],
    "object_keys": [
      "[\"host\",\"socai2-flow-20261108-01\"]",
      "[\"ip\",\"192.0.2.88\"]",
      "[\"ip\",\"198.51.100.88\"]",
      "[\"ip\",\"203.0.113.88\"]",
      "[\"user\",\"flow-observer-20261108-01\"]"
    ],
    "window_end": "2026-11-08T01:31:09Z",
    "window_start": "2026-11-08T01:21:09Z"
  },
  "state": "open",
  "text": "哪些影响已经观察到，哪些只是待核的可能影响？"
}
```

## prior_analysis

```json
{
  "followups": [
    {
      "alert_ids": [
        "65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"
      ],
      "binding_id": null,
      "mode": "deep",
      "object_keys": [
        "[\"ip\",\"198.51.100.88\"]"
      ],
      "objective": "查询主机 socai2-flow-20261108-01 在案件时间窗口内的网络连接，确认 198.51.100.88 的连接细节及流量特征。",
      "priority": "decision_critical",
      "question_id": "impact",
      "required_evidence": "dest_ip, dst_port, protocol, file_path, hash_sha256",
      "source_ids": [
        "N2_S17",
        "N2_S22"
      ]
    }
  ],
  "question": {
    "answer": "已观察到网络连接建立，但未观察到数据外传、文件哈希或敏感信息访问的具体证据，潜在影响待核。",
    "evidence_ids": [
      "N2_S17",
      "N2_S21"
    ],
    "id": "impact",
    "limitations": [
      "连接成功不证明数据外传"
    ],
    "state": "unresolved"
  },
  "role": "prior_analysis"
}
```

## queries

```json
[
  {
    "artifact_id": "762da185-007a-4dc7-a30e-af8b16729cac",
    "hostname": "socai2-flow-20261108-01",
    "limitations": [
      "host_time_match_is_not_causality_or_alert_membership",
      "lake_has_no_source_namespace_filter_may_include_multiple_connectors",
      "source_id_match_is_not_independent_corroboration",
      "empty_query_is_not_counterevidence",
      "coverage_and_collection_completeness_unknown"
    ],
    "observed_rows_in_bounded_fetch": 0,
    "omissions": [],
    "question_id": "authorization",
    "reason": null,
    "related_alert_ids": [
      "09e91978-d201-5435-901e-b6a40368b921",
      "3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3",
      "65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"
    ],
    "state": "completed",
    "tool_name": "authentication_activity",
    "truncated": false,
    "window_end": "2026-11-08T01:31:09Z",
    "window_start": "2026-11-08T01:21:09Z"
  }
]
```

## tool_options

```json
[
  {
    "hostname": "socai2-flow-20261108-01",
    "id": "B1",
    "related_alert_ids": [
      "09e91978-d201-5435-901e-b6a40368b921",
      "3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3",
      "65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"
    ],
    "tool_name": "process_activity"
  },
  {
    "hostname": "socai2-flow-20261108-01",
    "id": "B2",
    "related_alert_ids": [
      "09e91978-d201-5435-901e-b6a40368b921",
      "3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3",
      "65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"
    ],
    "tool_name": "network_connections"
  }
]
```

## tool_capabilities

```json
[
  {
    "available": false,
    "can_answer": "登录或认证尝试的账号、来源、时间、结果和已有会话信息；字段可能缺失。",
    "cannot_answer": "认证日志不是审批记录，无法证明变更获批或操作被业务授权；需要审批证据时交人工确认。",
    "inputs": "选择已有 binding_id；按冻结源主机、租户和时间窗口查询，不按任意用户名扩查。",
    "limitations": [
      "host_time_match_is_not_causality_or_alert_membership",
      "lake_has_no_source_namespace_filter_may_include_multiple_connectors",
      "source_id_match_is_not_independent_corroboration",
      "empty_query_is_not_counterevidence",
      "coverage_and_collection_completeness_unknown"
    ],
    "purpose": "调查主机在案件时间窗口内记录的认证活动。",
    "returned_fields": [
      "event_id",
      "event_time",
      "class_uid",
      "src_hostname",
      "dst_hostname",
      "process_name",
      "source_ip",
      "dest_ip",
      "src_port",
      "dst_port",
      "protocol",
      "file_path",
      "hash_sha256",
      "user_name",
      "action",
      "outcome",
      "session_id",
      "session_key",
      "session_key_kind",
      "session_originating_human",
      "ocsf_json"
    ],
    "tool_name": "authentication_activity"
  },
  {
    "available": true,
    "can_answer": "连接端点、端口、协议、时间、结果及已记录的流量计数；字段可能缺失。",
    "cannot_answer": "连接成功不证明敏感数据外传、具体文件传输或业务授权；计数缺失不等于零，查空不是反证。",
    "inputs": "选择已有 binding_id；按冻结源主机、租户和时间窗口查询。",
    "limitations": [
      "host_time_match_is_not_causality_or_alert_membership",
      "lake_has_no_source_namespace_filter_may_include_multiple_connectors",
      "source_id_match_is_not_independent_corroboration",
      "empty_query_is_not_counterevidence",
      "coverage_and_collection_completeness_unknown"
    ],
    "purpose": "调查主机在案件时间窗口内记录的网络连接。",
    "returned_fields": [
      "event_id",
      "event_time",
      "class_uid",
      "src_hostname",
      "dst_hostname",
      "process_name",
      "source_ip",
      "dest_ip",
      "src_port",
      "dst_port",
      "protocol",
      "file_path",
      "hash_sha256",
      "user_name",
      "action",
      "outcome",
      "session_id",
      "session_key",
      "session_key_kind",
      "session_originating_human",
      "ocsf_json"
    ],
    "tool_name": "network_connections"
  },
  {
    "available": true,
    "can_answer": "有哪些进程启动、父子进程、命令行、用户、会话、文件或哈希记录；字段可能缺失。",
    "cannot_answer": "进程启动成功不能证明脚本执行完成、业务成功或操作获批；相同主机和时间不能证明因果。",
    "inputs": "选择已有 binding_id；主机、租户、案件成员和时间窗口由程序冻结，不接受模型 SQL 或额外对象。",
    "limitations": [
      "host_time_match_is_not_causality_or_alert_membership",
      "lake_has_no_source_namespace_filter_may_include_multiple_connectors",
      "source_id_match_is_not_independent_corroboration",
      "empty_query_is_not_counterevidence",
      "coverage_and_collection_completeness_unknown"
    ],
    "purpose": "调查主机在案件时间窗口内记录的进程活动。",
    "returned_fields": [
      "event_id",
      "event_time",
      "class_uid",
      "src_hostname",
      "dst_hostname",
      "process_name",
      "source_ip",
      "dest_ip",
      "src_port",
      "dst_port",
      "protocol",
      "file_path",
      "hash_sha256",
      "user_name",
      "action",
      "outcome",
      "session_id",
      "session_key",
      "session_key_kind",
      "session_originating_human",
      "ocsf_json"
    ],
    "tool_name": "process_activity"
  },
  {
    "available": false,
    "can_answer": "设备标识、操作系统、代理版本、IP、首次及最近出现时间、隔离状态和产品标签。",
    "cannot_answer": "当前快照不是案件窗口历史，不返回审批记录或进程树；标签不证明授权或恶意，主机匹配不证明人的身份。",
    "inputs": "选择已有 binding_id；固定连接器和主机，仅对提供了连接器的成员可用。",
    "limitations": [
      "current_product_snapshot_not_case_window_history",
      "source_host_match_not_identity_proof",
      "not_a_process_tree_or_authorization_record",
      "empty_product_lookup_is_not_counterevidence"
    ],
    "purpose": "读取已关联 CrowdStrike 连接器中的当前主机快照。",
    "returned_fields": [
      "device_id",
      "hostname",
      "platform",
      "os_version",
      "agent_version",
      "local_ip",
      "external_ip",
      "last_seen",
      "first_seen",
      "containment_status",
      "tags",
      "source_connector_id",
      "upstream_request_id",
      "observed_at"
    ],
    "tool_name": "product_host_details"
  }
]
```

## tool_availability

```json
"available"
```

## limitations

```json
[
  "tool_members_are_query_bindings_not_row_attribution",
  "empty_queries_are_not_counterevidence",
  "only_listed_tools_available_no_automatic_scope_expansion"
]
```

## 已实际显示的来源

### N3_E1 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "conflict": false,
  "name": "event_kind",
  "record_key": "R1",
  "source_path": "$.ocsf_json.class_uid",
  "transform": "explicit_class_mapping",
  "value": "authentication_activity"
}
```

### N3_E7 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "conflict": false,
  "name": "user_name",
  "record_key": "R1",
  "source_path": "$.ocsf_json.actor.user.name",
  "transform": "identity",
  "value": "flow-observer-20261108-01"
}
```

### N3_E13 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "conflict": false,
  "name": "device_name",
  "record_key": "R1",
  "source_path": "$.ocsf_json.device.name",
  "transform": "identity",
  "value": "socai2-flow-20261108-01"
}
```

### N3_E19 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "conflict": false,
  "name": "source_ip",
  "record_key": "R1",
  "source_path": "$.ocsf_json.src_endpoint.ip",
  "transform": "identity",
  "value": "203.0.113.88"
}
```

### N3_E25 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "conflict": false,
  "name": "action",
  "record_key": "R1",
  "source_path": "$.ocsf_json.activity.action",
  "transform": "identity",
  "value": "logon"
}
```

### N3_E31 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "conflict": false,
  "name": "outcome",
  "record_key": "R1",
  "source_path": "$.ocsf_json.activity.outcome",
  "transform": "identity",
  "value": "success"
}
```

### N3_E37 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "conflict": false,
  "name": "activity_time",
  "record_key": "R1",
  "source_path": "$.ocsf_json.time",
  "transform": "identity",
  "unit": "iso8601_with_offset",
  "value": "2026-11-08T01:26:09+00:00"
}
```

### N3_E2 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "user_name": "flow-observer-20261108-01"
}
```

### N3_E4 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "device_name": "socai2-flow-20261108-01"
}
```

### N3_E6 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "source_ip": "203.0.113.88"
}
```

### N3_E8 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "action": "logon"
}
```

### N3_E10 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "outcome": "success"
}
```

### N3_E12 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "activity_time": "2026-11-08T01:26:09+00:00",
  "unit": "iso8601_with_offset"
}
```

### N3_E3 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "conflict": false,
  "name": "event_kind",
  "record_key": "R2",
  "source_path": "$.ocsf_json.class_uid",
  "transform": "explicit_class_mapping",
  "value": "process_activity"
}
```

### N3_E9 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "conflict": false,
  "name": "process_name",
  "record_key": "R2",
  "source_path": "$.ocsf_json.process.name",
  "transform": "identity",
  "value": "powershell.exe"
}
```

### N3_E15 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "conflict": false,
  "name": "process_command_line",
  "record_key": "R2",
  "source_path": "$.ocsf_json.process.cmd_line",
  "transform": "identity",
  "value": "powershell.exe -NoProfile -Command Get-LocalUser"
}
```

### N3_E21 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "conflict": false,
  "name": "user_name",
  "record_key": "R2",
  "source_path": "$.ocsf_json.actor.user.name",
  "transform": "identity",
  "value": "flow-observer-20261108-01"
}
```

### N3_E27 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "conflict": false,
  "name": "device_name",
  "record_key": "R2",
  "source_path": "$.ocsf_json.device.name",
  "transform": "identity",
  "value": "socai2-flow-20261108-01"
}
```

### N3_E33 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "conflict": false,
  "name": "action",
  "record_key": "R2",
  "source_path": "$.ocsf_json.activity.action",
  "transform": "identity",
  "value": "process_start"
}
```

### N3_E39 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "conflict": false,
  "name": "outcome",
  "record_key": "R2",
  "source_path": "$.ocsf_json.activity.outcome",
  "transform": "identity",
  "value": "success"
}
```

### N3_E43 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "conflict": false,
  "name": "activity_time",
  "record_key": "R2",
  "source_path": "$.ocsf_json.time",
  "transform": "identity",
  "unit": "iso8601_with_offset",
  "value": "2026-11-08T01:26:29+00:00"
}
```

### N3_E5 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "conflict": false,
  "name": "event_kind",
  "record_key": "R3",
  "source_path": "$.ocsf_json.class_uid",
  "transform": "explicit_class_mapping",
  "value": "network_activity"
}
```

### N3_E11 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "conflict": false,
  "name": "user_name",
  "record_key": "R3",
  "source_path": "$.ocsf_json.actor.user.name",
  "transform": "identity",
  "value": "flow-observer-20261108-01"
}
```

### N3_E17 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "conflict": false,
  "name": "device_name",
  "record_key": "R3",
  "source_path": "$.ocsf_json.device.name",
  "transform": "identity",
  "value": "socai2-flow-20261108-01"
}
```

### N3_E23 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "conflict": false,
  "name": "source_ip",
  "record_key": "R3",
  "source_path": "$.ocsf_json.src_endpoint.ip",
  "transform": "identity",
  "value": "192.0.2.88"
}
```

### N3_E29 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "conflict": false,
  "name": "dest_ip",
  "record_key": "R3",
  "source_path": "$.ocsf_json.dst_endpoint.ip",
  "transform": "identity",
  "value": "198.51.100.88"
}
```

### N3_E35 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "conflict": false,
  "name": "dst_port",
  "record_key": "R3",
  "source_path": "$.ocsf_json.dst_endpoint.port",
  "transform": "identity",
  "value": 443
}
```

### N3_E41 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "conflict": false,
  "name": "protocol",
  "record_key": "R3",
  "source_path": "$.ocsf_json.connection_info.protocol_name",
  "transform": "identity",
  "value": "TCP"
}
```

### N3_E45 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "conflict": false,
  "name": "action",
  "record_key": "R3",
  "source_path": "$.ocsf_json.activity.action",
  "transform": "identity",
  "value": "network_connection"
}
```

### N3_E47 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "conflict": false,
  "name": "outcome",
  "record_key": "R3",
  "source_path": "$.ocsf_json.activity.outcome",
  "transform": "identity",
  "value": "success"
}
```

### N3_E49 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "conflict": false,
  "name": "activity_time",
  "record_key": "R3",
  "source_path": "$.ocsf_json.time",
  "transform": "identity",
  "unit": "iso8601_with_offset",
  "value": "2026-11-08T01:26:49+00:00"
}
```

### N3_E14 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "process_name": "powershell.exe"
}
```

### N3_E16 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "process_command_line": "powershell.exe -NoProfile -Command Get-LocalUser"
}
```

### N3_E18 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "user_name": "flow-observer-20261108-01"
}
```

### N3_E20 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "device_name": "socai2-flow-20261108-01"
}
```

### N3_E22 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "action": "process_start"
}
```

### N3_E24 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "outcome": "success"
}
```

### N3_E26 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "activity_time": "2026-11-08T01:26:29+00:00",
  "unit": "iso8601_with_offset"
}
```

### N3_E28 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "user_name": "flow-observer-20261108-01"
}
```

### N3_E30 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "device_name": "socai2-flow-20261108-01"
}
```

### N3_E32 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "source_ip": "192.0.2.88"
}
```

### N3_E34 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "dest_ip": "198.51.100.88"
}
```

### N3_E36 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "dst_port": 443
}
```

### N3_E38 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "protocol": "TCP"
}
```

### N3_E40 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "action": "network_connection"
}
```

### N3_E42 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "outcome": "success"
}
```

### N3_E44 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "activity_time": "2026-11-08T01:26:49+00:00",
  "unit": "iso8601_with_offset"
}
```

### N3_E46 · prior_analysis

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "assessed_at": "2026-11-08T01:34:57.992726+00:00",
  "confidence": 0.65,
  "rationale": "告警显示用户'flow-observer-20261108-01'在主机'socai2-flow-20261908-01'上登录成功，但缺乏授权依据。威胁情报查询、资产库存和历史记录均未返回命中或异常关联，查空结果不能证明行为安全。检测标签'does_not_establish_observed_attack'为上游属性，不否定本次告警的有效性。无法区分是正常运维登录还是潜在攻击前奏。",
  "score_state": "available",
  "verdict": "needs_review"
}
```

### N3_E48 · prior_analysis

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "assessed_at": "2026-11-08T01:35:13.281603+00:00",
  "confidence": 0.65,
  "rationale": "告警显示 powershell.exe 进程启动成功，执行命令为获取本地用户列表。现有证据（历史登录记录、威胁情报查空、资产库存查空）均不足以证明该行为是授权运维还是恶意侦察。检测标签明确标注'不证明攻击发生'，且无明确授权依据，符合需进一步调查的特征。",
  "score_state": "available",
  "verdict": "needs_review"
}
```

### N3_E50 · prior_analysis

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "assessed_at": "2026-11-08T01:35:32.822326+00:00",
  "confidence": 0.65,
  "rationale": "现有证据不足以区分该出站连接是授权运维行为还是恶意外传。虽然检测到出站连接成功，但缺乏明确的授权依据（如白名单、审批记录）。威胁情报查询结果为空（查空），不能证明行为安全；历史查询仅显示同主机/用户的登录和进程启动记录，未提供因果关联或异常模式证明。检测标签'does_not_establish_observed_attack'为上游属性，不否定本次告警的有效性。无法排除潜在攻击前奏或正常业务的可能性。",
  "score_state": "available",
  "verdict": "needs_review"
}
```

### N3_E51 · prior_analysis

范围：["09e91978-d201-5435-901e-b6a40368b921", "3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3", "65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "conclusion": "All three alerts require review. Evidence is insufficient to confirm malicious intent or authorize the actions. The outbound connection involves an external IP (198.51.100.88) not present in the logon or process start objects, requiring verification of its legitimacy.",
  "limitations": [
    "N1_S19, N1_S23, N1_S27 rationales explicitly state that empty threat intel searches do not prove safety.",
    "Detection labels 'does_not_establish_observed_attack' are upstream properties and do not negate alert validity.",
    "No prior analysis or human statement provided to override the 'needs_review' verdict.",
    "incident_diagnosis_not_case_investigation",
    "structure_scope_sources_checked_not_truth_proven",
    "model_view_has_omitted_fields"
  ],
  "summary": "Incident 06f82d36-1964-4186-aed3-4c7b9ab1a375 aggregates three sequential alerts on host 'socai2-flow-20261108-01' involving user 'flow-observer-20261108-01'. The sequence includes a successful account logon (2026-11-08T01:26:09), a PowerShell process start executing 'Get-LocalUser' (2026-11-08T01:26:29), and a successful outbound TCP connection to 198.51.100.88:443 (2026-11-08T01:26:49). All alerts are rated 'medium' severity. Prior analysis for all members flags them as 'needs_review' due to lack of authorization evidence and inability to distinguish between authorized operations and potential reconnaissance/exfiltration. No causal chain is proven; temporal proximity is noted but not confirmed as attack progression."
}
```

### N3_E52 · source_label

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "alert_time": "2026-11-08T01:26:09+00:00"
}
```

### N3_E55 · source_label

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "description": null,
  "event_time": "2026-11-08T01:26:09+00:00",
  "original_vendor": "LabTelemetry",
  "severity": "medium",
  "source_alert_id": "8eb1558e-143f-485c-8763-8a8d076cb3c6",
  "title": "Account logon observed",
  "vendor_alert_id": null
}
```

### N3_E59 · source_label

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "detection": {
    "confidence_label": "low",
    "confidence_rationale": [
      "{\"contribution\":-0.8,\"factor\":\"ml_anomaly\",\"label\":\"ML anomaly score\",\"value\":\"0.10\",\"weight\":0.18}",
      "{\"contribution\":-1.0,\"factor\":\"upstream_risk\",\"label\":\"Upstream provided risk score (source unverified)\",\"value\":\"not supplied; numeric feature baseline only\",\"weight\":0.08}",
      "{\"contribution\":-0.4,\"factor\":\"mitre_coverage\",\"label\":\"MITRE technique coverage\",\"value\":\"0 techniques\",\"weight\":0.14}",
      "{\"contribution\":-0.3,\"factor\":\"threat_intel\",\"label\":\"Threat-intel match\",\"value\":\"no TI match\",\"weight\":0.16}",
      "{\"contribution\":0.19999999999999996,\"factor\":\"ml_priority\",\"label\":\"ML priority rank\",\"value\":\"0.60\",\"weight\":0.18}",
      "{\"contribution\":0.0,\"factor\":\"severity\",\"label\":\"Alert severity\",\"value\":\"medium\",\"weight\":0.2}",
      "{\"contribution\":0.0,\"factor\":\"ioc_density\",\"label\":\"IOC density\",\"value\":\"2 populated fields\",\"weight\":0.06}"
    ],
    "confidence_state": "available",
    "confidence_value": 20.8,
    "labels_provided": false,
    "ocsf_class_uid": 3002,
    "rule_id": null,
    "rule_name": null,
    "score_source": "fusion",
    "tactics": [],
    "techniques": []
  },
  "material_state": "complete",
  "source_scope": {
    "complete": true,
    "kind": "explicit_sources",
    "omission_reason": null,
    "received_count": 2,
    "retained_count": 2,
    "truncated": false,
    "window_end": null,
    "window_start": null
  }
}
```

### N3_E60 · source_label

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
[
  {
    "asset_match_state": "not_checked",
    "namespace": "source:socai2-flow-acceptance",
    "normalized_value": "socai2-flow-20261108-01",
    "object_role": "entity",
    "object_type": "host",
    "raw_value": "socai2-flow-20261108-01"
  },
  {
    "asset_match_state": "not_checked",
    "namespace": "source:socai2-flow-acceptance",
    "normalized_value": "203.0.113.88",
    "object_role": "both",
    "object_type": "ip",
    "raw_value": "203.0.113.88"
  },
  {
    "asset_match_state": "not_checked",
    "namespace": "source:socai2-flow-acceptance",
    "normalized_value": "flow-observer-20261108-01",
    "object_role": "entity",
    "object_type": "user",
    "raw_value": "flow-observer-20261108-01"
  }
]
```

### N3_E53 · source_label

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "alert_time": "2026-11-08T01:26:29+00:00"
}
```

### N3_E56 · source_label

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "description": null,
  "event_time": "2026-11-08T01:26:29+00:00",
  "original_vendor": "LabTelemetry",
  "severity": "medium",
  "source_alert_id": "45dfa0b7-8e51-4b5a-bb8c-eca33c9aafdd",
  "title": "Process start observed",
  "vendor_alert_id": null
}
```

### N3_E61 · source_label

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "detection": {
    "confidence_label": "low",
    "confidence_rationale": [
      "{\"contribution\":-0.8,\"factor\":\"ml_anomaly\",\"label\":\"ML anomaly score\",\"value\":\"0.10\",\"weight\":0.18}",
      "{\"contribution\":-1.0,\"factor\":\"upstream_risk\",\"label\":\"Upstream provided risk score (source unverified)\",\"value\":\"not supplied; numeric feature baseline only\",\"weight\":0.08}",
      "{\"contribution\":-0.4,\"factor\":\"mitre_coverage\",\"label\":\"MITRE technique coverage\",\"value\":\"0 techniques\",\"weight\":0.14}",
      "{\"contribution\":-0.3,\"factor\":\"threat_intel\",\"label\":\"Threat-intel match\",\"value\":\"no TI match\",\"weight\":0.16}",
      "{\"contribution\":0.19999999999999996,\"factor\":\"ml_priority\",\"label\":\"ML priority rank\",\"value\":\"0.60\",\"weight\":0.18}",
      "{\"contribution\":0.0,\"factor\":\"severity\",\"label\":\"Alert severity\",\"value\":\"medium\",\"weight\":0.2}",
      "{\"contribution\":0.0,\"factor\":\"ioc_density\",\"label\":\"IOC density\",\"value\":\"2 populated fields\",\"weight\":0.06}"
    ],
    "confidence_state": "available",
    "confidence_value": 20.8,
    "labels_provided": false,
    "ocsf_class_uid": 1007,
    "rule_id": null,
    "rule_name": null,
    "score_source": "fusion",
    "tactics": [],
    "techniques": []
  },
  "material_state": "complete",
  "source_scope": {
    "complete": true,
    "kind": "explicit_sources",
    "omission_reason": null,
    "received_count": 2,
    "retained_count": 2,
    "truncated": false,
    "window_end": null,
    "window_start": null
  }
}
```

### N3_E62 · source_label

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
[
  {
    "asset_match_state": "not_checked",
    "namespace": "source:socai2-flow-acceptance",
    "normalized_value": "socai2-flow-20261108-01",
    "object_role": "entity",
    "object_type": "host",
    "raw_value": "socai2-flow-20261108-01"
  },
  {
    "asset_match_state": "not_checked",
    "namespace": "source:socai2-flow-acceptance",
    "normalized_value": "flow-observer-20261108-01",
    "object_role": "entity",
    "object_type": "user",
    "raw_value": "flow-observer-20261108-01"
  }
]
```

### N3_E54 · source_label

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "alert_time": "2026-11-08T01:26:49+00:00"
}
```

### N3_E57 · source_label

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "description": null,
  "event_time": "2026-11-08T01:26:49+00:00",
  "original_vendor": "LabTelemetry",
  "severity": "medium",
  "source_alert_id": "bd1e95f5-382c-420a-9877-e0001d473ab5",
  "title": "Outbound connection observed",
  "vendor_alert_id": null
}
```

### N3_E63 · source_label

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "detection": {
    "confidence_label": "low",
    "confidence_rationale": [
      "{\"contribution\":-0.8,\"factor\":\"ml_anomaly\",\"label\":\"ML anomaly score\",\"value\":\"0.10\",\"weight\":0.18}",
      "{\"contribution\":-1.0,\"factor\":\"upstream_risk\",\"label\":\"Upstream provided risk score (source unverified)\",\"value\":\"not supplied; numeric feature baseline only\",\"weight\":0.08}",
      "{\"contribution\":-0.4,\"factor\":\"mitre_coverage\",\"label\":\"MITRE technique coverage\",\"value\":\"0 techniques\",\"weight\":0.14}",
      "{\"contribution\":-0.3,\"factor\":\"threat_intel\",\"label\":\"Threat-intel match\",\"value\":\"no TI match\",\"weight\":0.16}",
      "{\"contribution\":0.19999999999999996,\"factor\":\"ml_priority\",\"label\":\"ML priority rank\",\"value\":\"0.60\",\"weight\":0.18}",
      "{\"contribution\":0.0,\"factor\":\"severity\",\"label\":\"Alert severity\",\"value\":\"medium\",\"weight\":0.2}",
      "{\"contribution\":0.0,\"factor\":\"ioc_density\",\"label\":\"IOC density\",\"value\":\"2 populated fields\",\"weight\":0.06}"
    ],
    "confidence_state": "available",
    "confidence_value": 20.8,
    "labels_provided": false,
    "ocsf_class_uid": 4001,
    "rule_id": null,
    "rule_name": null,
    "score_source": "fusion",
    "tactics": [],
    "techniques": []
  },
  "material_state": "complete",
  "source_scope": {
    "complete": true,
    "kind": "explicit_sources",
    "omission_reason": null,
    "received_count": 2,
    "retained_count": 2,
    "truncated": false,
    "window_end": null,
    "window_start": null
  }
}
```

### N3_E64 · source_label

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
[
  {
    "asset_match_state": "not_checked",
    "namespace": "source:socai2-flow-acceptance",
    "normalized_value": "socai2-flow-20261108-01",
    "object_role": "entity",
    "object_type": "host",
    "raw_value": "socai2-flow-20261108-01"
  },
  {
    "asset_match_state": "not_checked",
    "namespace": "source:socai2-flow-acceptance",
    "normalized_value": "192.0.2.88",
    "object_role": "both",
    "object_type": "ip",
    "raw_value": "192.0.2.88"
  },
  {
    "asset_match_state": "not_checked",
    "namespace": "source:socai2-flow-acceptance",
    "normalized_value": "198.51.100.88",
    "object_role": "both",
    "object_type": "ip",
    "raw_value": "198.51.100.88"
  },
  {
    "asset_match_state": "not_checked",
    "namespace": "source:socai2-flow-acceptance",
    "normalized_value": "flow-observer-20261108-01",
    "object_role": "entity",
    "object_type": "user",
    "raw_value": "flow-observer-20261108-01"
  }
]
```

### N3_E58 · source_label

范围：["09e91978-d201-5435-901e-b6a40368b921", "3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3", "65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "description": null,
  "title": "1.2 四项续修多告警验收 20261108-01"
}
```

