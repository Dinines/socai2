-- psql只读例子；只查生产tenant与本轮两个真实Run，不改写业务数据。
-- 使用获授权的只读DSN和TLS CA；本文件不包含凭据。
\set tenant_id 'f6a5c700-69b8-44fc-8238-609362fb1a9f'
\set alert_1 'bc625c39-56af-5403-a378-9bfb99c610d2'
\set alert_2 'e5f593f0-b328-59c3-8238-379db33d8bfe'
\set run_1 '4f5a0a57-050a-57a4-8443-504550fbc5fd'
\set run_2 'bdccd907-7f36-558f-8ed4-4be2e417b101'
BEGIN READ ONLY;
SELECT set_config('app.current_tenant_id', :'tenant_id', TRUE);

-- A. 来源身份、canonical、首次融合与当前分诊投影
SELECT id, title, status, disposition, ai_score, ai_summary, resolved_at,
       source_event_ids, external_id, case_id,
       enrichment_data #>> '{socai2_fusion,identity,source_alert_id}' AS source_alert_id,
       enrichment_data #>> '{socai2_fusion,incident_id}' AS fusion_incident_id,
       enrichment_data #> '{socai2_fusion,delivery_snapshot}' AS first_fusion_snapshot
FROM alerts
WHERE tenant_id=:'tenant_id'::uuid AND id IN (:'alert_1'::uuid, :'alert_2'::uuid);

-- B. Alert找自动Run；case_id是varchar关联，不是Case外键
SELECT id AS run_id, case_id, raw_alert->>'id' AS canonical_alert_id,
       status, error, started_at, completed_at, total_tokens,
       measured_call_count, estimated_call_count, unpriced_call_count
FROM investigation_runs
WHERE tenant_id=:'tenant_id'::uuid
  AND (raw_alert->>'id' IN (:'alert_1', :'alert_2') OR case_id IN (:'alert_1', :'alert_2'))
ORDER BY started_at;

-- C. 全部已持久步骤：保留seq=-1，不只读seq>0
-- 展示时间线用ts；seq跨外层和工具子序列，不是全局写入时间游标。
SELECT run_id, seq, ts, kind, agent, summary, payload,
       input_hash, output_hash, duration_ms
FROM investigation_events
WHERE tenant_id=:'tenant_id'::uuid AND run_id IN (:'run_1'::uuid, :'run_2'::uuid)
ORDER BY run_id, ts, seq;

-- D. 工件目录、正文长度及与步骤关联；SHA256本轮已在客户端独立重算。
SELECT run_id, id AS artifact_id, event_id, kind, sha256, size_bytes,
       octet_length(convert_to(COALESCE(content,''), 'UTF8')) AS actual_utf8_bytes,
       content IS NOT NULL AS has_inline_content, blob_ref
FROM investigation_artifacts
WHERE tenant_id=:'tenant_id'::uuid AND run_id IN (:'run_1'::uuid, :'run_2'::uuid)
ORDER BY run_id, created_at, id;

-- E. 结论与Markdown按不同kind读，不用Run.status代替graph completion。
SELECT run_id, seq, payload->>'completion' AS graph_completion,
       payload->>'status' AS graph_state_status, payload->>'verdict' AS graph_verdict
FROM investigation_events
WHERE tenant_id=:'tenant_id'::uuid AND run_id IN (:'run_1'::uuid, :'run_2'::uuid)
  AND kind='graph_result';
SELECT run_id, id AS artifact_id, kind, content
FROM investigation_artifacts
WHERE tenant_id=:'tenant_id'::uuid AND run_id IN (:'run_1'::uuid, :'run_2'::uuid)
  AND kind IN ('report_md', 'graph_result', 'graph_llm_exchanges')
ORDER BY run_id, kind;

-- F. 成本表两个关联字段是TEXT；各模型行已经是聚合，不再乘事件行数。
SELECT run_id, model, resolved_model, call_count,
       total_prompt_tokens, total_completion_tokens,
       total_prompt_tokens+total_completion_tokens AS total_tokens,
       measured_call_count, measured_cost_usd,
       estimated_call_count, estimated_cost_usd, unpriced_call_count
FROM aisoc_run_costs
WHERE tenant_id=:'tenant_id' AND run_id IN (:'run_1', :'run_2')
ORDER BY run_id, model;

-- G. 初次分诊预留与调查用量是两个合同；不要清除unknown来绕过预算。
SELECT run_id, charged_tokens, reserved_at, settled_at, outcome
FROM socai2_triage_budget_reservations
WHERE tenant_id=:'tenant_id'::uuid AND run_id IN (:'run_1'::uuid, :'run_2'::uuid);
ROLLBACK;
