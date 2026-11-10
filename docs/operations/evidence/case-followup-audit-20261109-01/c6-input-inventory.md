# C6 已保存输入的材料清单

这是历史请求的只读展开，供设计核对；不是新的模型请求。下列正文和旧编号保持原样。

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
    "projected_fields": 0,
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
    "view_state": "all_projected_fields",
    "visible_fields": 0,
    "window_end": "2026-11-08T01:31:09Z",
    "window_start": "2026-11-08T01:21:09Z"
  }
]
```

## followup_execution

```json
{
  "initial_analysis_artifact_id": "b0f75871-2834-4c99-86bc-f716d474263b",
  "role": "execution_receipt",
  "routes": [
    {
      "answer_available": false,
      "execution_order": 0,
      "followup_index": 0,
      "projection_id": "762da185-007a-4dc7-a30e-af8b16729cac",
      "reason": null,
      "reused": false,
      "state": "completed"
    },
    {
      "answer_available": true,
      "execution_order": 1,
      "followup_index": 1,
      "reason": "answer",
      "reused": false,
      "state": "completed"
    }
  ]
}
```

## comparison

```json
{
  "added_alert_ids": [],
  "limitations": [
    "comparison_is_between_recorded_judgments_not_independent_evidence"
  ],
  "prior_scope": null,
  "removed_alert_ids": [],
  "result_id": null,
  "shared_alert_ids": [],
  "state": "initial"
}
```

## limitations

```json
[
  "original_scope_and_material_versions_unchanged",
  "query_binding_only_does_not_prove_alert_membership",
  "old_analysis_is_not_independent_evidence",
  "derived_graph_is_not_independent_evidence_or_confirmed_impact"
]
```

## 已实际显示的来源

### N4_S1 · prior_analysis

范围：["09e91978-d201-5435-901e-b6a40368b921", "3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3", "65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "execution_plan_index": 0,
  "followup": {
    "alert_ids": [
      "09e91978-d201-5435-901e-b6a40368b921",
      "3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3",
      "65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"
    ],
    "binding_id": "B1",
    "mode": "query",
    "object_keys": [
      "[\"host\",\"socai2-flow-20261108-01\"]"
    ],
    "objective": "查询主机 socai2-flow-20261108-01 在案件时间窗口内的认证活动，验证登录来源和会话上下文。",
    "priority": "decision_critical",
    "question_id": "authorization",
    "required_evidence": "session_id, session_originating_human, outcome"
  }
}
```

### N4_S5 · prior_analysis

范围：["09e91978-d201-5435-901e-b6a40368b921", "3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3", "65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "previous_summary": "保留通过引用校验的分析片段；部分内容待核。"
}
```

### N4_S9 · prior_analysis

范围：["09e91978-d201-5435-901e-b6a40368b921", "3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3", "65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "answer": {
    "alternatives": [],
    "limitations": [
      "连接成功（N3_E47）仅证明 TCP 握手完成，不证明数据外传、文件传输或敏感信息访问（来源 N3_E5, N3_E11 等未提供 file_path 或 hash_sha256 字段）。",
      "进程启动（N3_E39）仅证明脚本执行开始，不证明脚本完成或业务成功。",
      "登录成功（N3_E31）不证明操作拥有业务授权。",
      "威胁情报查询结果为空（查空）不构成反证，不能证明行为安全（来源 N3_E51 明确说明）。",
      "时间接近和图可达（登录->进程->连接）不能直接推导因果或攻击链，需人工确认意图。"
    ],
    "state": "unresolved",
    "text": "已观察到以下具体行为事实：1. 用户 flow-observer-20261108-01 于 01:26:09 在主机 socai2-flow-20261108-01 上成功登录（来源 N3_E1, N3_E37）；2. 随后于 01:26:29 成功启动了 powershell.exe 进程，执行命令为 'Get-LocalUser'（来源 N3_E3, N3_E15, N3_E21, N3_E33, N3_E39, N3_E43）；3. 于 01:26:49 建立了从 192.0.2.88 到 198.51.100.88:443 的 TCP 网络连接（来源 N3_E5, N3_E11, N3_E23, N3_E29, N3_E35, N3_E41, N3_E45, N3_E47, N3_E49）。"
  },
  "question_id": "impact"
}
```

### N4_S2 · prior_analysis

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "execution_plan_index": 1,
  "followup": {
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
    "required_evidence": "dest_ip, dst_port, protocol, file_path, hash_sha256"
  }
}
```

### N4_S22 · prior_analysis

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "from": "Outbound connection observed",
  "limitations": [
    "source_label_not_behavior_or_cross_alert_causality",
    "derived_view_not_independent_evidence",
    "connectivity_does_not_prove_causality_or_impact",
    "record_scoped_process_endpoint_and_session_identity",
    "external_topology_not_queried",
    "no_attack_path_or_transitive_impact_inferred",
    "analysis_prose_not_converted_to_edges"
  ],
  "relation": "source_reports_object",
  "strength": "candidate",
  "to": "socai2-flow-20261108-01"
}
```

### N4_S25 · prior_analysis

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "from": "Outbound connection observed",
  "limitations": [
    "source_label_not_behavior_or_cross_alert_causality",
    "derived_view_not_independent_evidence",
    "connectivity_does_not_prove_causality_or_impact",
    "record_scoped_process_endpoint_and_session_identity",
    "external_topology_not_queried",
    "no_attack_path_or_transitive_impact_inferred",
    "analysis_prose_not_converted_to_edges"
  ],
  "relation": "source_reports_object",
  "strength": "candidate",
  "to": "198.51.100.88"
}
```

### N4_S28 · prior_analysis

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "from": "Outbound connection observed",
  "limitations": [
    "source_label_not_behavior_or_cross_alert_causality",
    "derived_view_not_independent_evidence",
    "connectivity_does_not_prove_causality_or_impact",
    "record_scoped_process_endpoint_and_session_identity",
    "external_topology_not_queried",
    "no_attack_path_or_transitive_impact_inferred",
    "analysis_prose_not_converted_to_edges"
  ],
  "relation": "source_reports_object",
  "strength": "candidate",
  "to": "flow-observer-20261108-01"
}
```

### N4_S31 · prior_analysis

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "from": "Outbound connection observed",
  "limitations": [
    "source_label_not_behavior_or_cross_alert_causality",
    "derived_view_not_independent_evidence",
    "connectivity_does_not_prove_causality_or_impact",
    "record_scoped_process_endpoint_and_session_identity",
    "external_topology_not_queried",
    "no_attack_path_or_transitive_impact_inferred",
    "analysis_prose_not_converted_to_edges"
  ],
  "relation": "source_reports_object",
  "strength": "candidate",
  "to": "192.0.2.88"
}
```

### N4_S34 · prior_analysis

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "from": "192.0.2.88",
  "limitations": [
    "activity_not_proof_of_success_authorization_or_impact",
    "no_process_to_connection_link_inferred",
    "derived_view_not_independent_evidence",
    "connectivity_does_not_prove_causality_or_impact",
    "record_scoped_process_endpoint_and_session_identity",
    "external_topology_not_queried",
    "no_attack_path_or_transitive_impact_inferred",
    "analysis_prose_not_converted_to_edges"
  ],
  "relation": "reported_network_activity",
  "strength": "observed",
  "to": "198.51.100.88"
}
```

### N4_S3 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "user_name": "flow-observer-20261108-01"
}
```

### N4_S7 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "device_name": "socai2-flow-20261108-01"
}
```

### N4_S11 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "source_ip": "203.0.113.88"
}
```

### N4_S14 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "action": "logon"
}
```

### N4_S17 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "outcome": "success"
}
```

### N4_S20 · observation

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "activity_time": "2026-11-08T01:26:09+00:00",
  "unit": "iso8601_with_offset"
}
```

### N4_S23 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "process_name": "powershell.exe"
}
```

### N4_S26 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "process_command_line": "powershell.exe -NoProfile -Command Get-LocalUser"
}
```

### N4_S29 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "user_name": "flow-observer-20261108-01"
}
```

### N4_S32 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "device_name": "socai2-flow-20261108-01"
}
```

### N4_S35 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "action": "process_start"
}
```

### N4_S37 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "outcome": "success"
}
```

### N4_S39 · observation

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "activity_time": "2026-11-08T01:26:29+00:00",
  "unit": "iso8601_with_offset"
}
```

### N4_S41 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "user_name": "flow-observer-20261108-01"
}
```

### N4_S43 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "device_name": "socai2-flow-20261108-01"
}
```

### N4_S45 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "source_ip": "192.0.2.88"
}
```

### N4_S47 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "dest_ip": "198.51.100.88"
}
```

### N4_S49 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "dst_port": 443
}
```

### N4_S51 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "protocol": "TCP"
}
```

### N4_S53 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "action": "network_connection"
}
```

### N4_S55 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "outcome": "success"
}
```

### N4_S57 · observation

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "activity_time": "2026-11-08T01:26:49+00:00",
  "unit": "iso8601_with_offset"
}
```

### N4_S66 · source_label

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "alert_time": "2026-11-08T01:26:09+00:00"
}
```

### N4_S69 · source_label

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

### N4_S73 · source_label

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

### N4_S74 · source_label

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

### N4_S67 · source_label

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "alert_time": "2026-11-08T01:26:29+00:00"
}
```

### N4_S70 · source_label

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

### N4_S75 · source_label

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

### N4_S76 · source_label

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

### N4_S68 · source_label

范围：["65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "alert_time": "2026-11-08T01:26:49+00:00"
}
```

### N4_S71 · source_label

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

### N4_S77 · source_label

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

### N4_S78 · source_label

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

### N4_S4 · observation

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

### N4_S15 · observation

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

### N4_S24 · observation

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

### N4_S33 · observation

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

### N4_S40 · observation

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

### N4_S46 · observation

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

### N4_S52 · observation

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

### N4_S6 · prior_analysis

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "from": "Account logon observed",
  "limitations": [
    "source_label_not_behavior_or_cross_alert_causality",
    "derived_view_not_independent_evidence",
    "connectivity_does_not_prove_causality_or_impact",
    "record_scoped_process_endpoint_and_session_identity",
    "external_topology_not_queried",
    "no_attack_path_or_transitive_impact_inferred",
    "analysis_prose_not_converted_to_edges"
  ],
  "relation": "source_reports_object",
  "strength": "candidate",
  "to": "socai2-flow-20261108-01"
}
```

### N4_S10 · prior_analysis

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "from": "Account logon observed",
  "limitations": [
    "source_label_not_behavior_or_cross_alert_causality",
    "derived_view_not_independent_evidence",
    "connectivity_does_not_prove_causality_or_impact",
    "record_scoped_process_endpoint_and_session_identity",
    "external_topology_not_queried",
    "no_attack_path_or_transitive_impact_inferred",
    "analysis_prose_not_converted_to_edges"
  ],
  "relation": "source_reports_object",
  "strength": "candidate",
  "to": "203.0.113.88"
}
```

### N4_S13 · prior_analysis

范围：["09e91978-d201-5435-901e-b6a40368b921"]

```json
{
  "from": "Account logon observed",
  "limitations": [
    "source_label_not_behavior_or_cross_alert_causality",
    "derived_view_not_independent_evidence",
    "connectivity_does_not_prove_causality_or_impact",
    "record_scoped_process_endpoint_and_session_identity",
    "external_topology_not_queried",
    "no_attack_path_or_transitive_impact_inferred",
    "analysis_prose_not_converted_to_edges"
  ],
  "relation": "source_reports_object",
  "strength": "candidate",
  "to": "flow-observer-20261108-01"
}
```

### N4_S8 · observation

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

### N4_S18 · observation

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

### N4_S27 · observation

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

### N4_S36 · observation

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

### N4_S42 · observation

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

### N4_S48 · observation

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

### N4_S54 · observation

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

### N4_S58 · observation

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

### N4_S12 · observation

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

### N4_S21 · observation

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

### N4_S30 · observation

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

### N4_S38 · observation

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

### N4_S44 · observation

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

### N4_S50 · observation

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

### N4_S56 · observation

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

### N4_S60 · observation

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

### N4_S62 · observation

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

### N4_S64 · observation

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

### N4_S16 · prior_analysis

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "from": "Process start observed",
  "limitations": [
    "source_label_not_behavior_or_cross_alert_causality",
    "derived_view_not_independent_evidence",
    "connectivity_does_not_prove_causality_or_impact",
    "record_scoped_process_endpoint_and_session_identity",
    "external_topology_not_queried",
    "no_attack_path_or_transitive_impact_inferred",
    "analysis_prose_not_converted_to_edges"
  ],
  "relation": "source_reports_object",
  "strength": "candidate",
  "to": "socai2-flow-20261108-01"
}
```

### N4_S19 · prior_analysis

范围：["3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3"]

```json
{
  "from": "Process start observed",
  "limitations": [
    "source_label_not_behavior_or_cross_alert_causality",
    "derived_view_not_independent_evidence",
    "connectivity_does_not_prove_causality_or_impact",
    "record_scoped_process_endpoint_and_session_identity",
    "external_topology_not_queried",
    "no_attack_path_or_transitive_impact_inferred",
    "analysis_prose_not_converted_to_edges"
  ],
  "relation": "source_reports_object",
  "strength": "candidate",
  "to": "flow-observer-20261108-01"
}
```

### N4_S59 · prior_analysis

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

### N4_S61 · prior_analysis

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

### N4_S63 · prior_analysis

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

### N4_S65 · prior_analysis

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

### N4_S72 · source_label

范围：["09e91978-d201-5435-901e-b6a40368b921", "3fde9da5-8ff1-5c42-8c91-b72fdc77dbd3", "65e2a5f9-3b00-5def-9547-c21f1b9cc4bf"]

```json
{
  "description": null,
  "title": "1.2 四项续修多告警验收 20261108-01"
}
```

