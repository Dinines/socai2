-- psql只读示例，未执行。先替换为获授权的真实标识和只读连接。
-- psql连接使用postgresql:// DSN及sslmode=verify-full，不是postgresql+asyncpg。
\set tenant_id '11111111-1111-4111-8111-111111111111'
\set alert_id '90e34b3b-fc4d-5835-b0dd-9c2c5f6780d6'
\set run_id '55555555-5555-4555-8555-555555555555'
\set case_id '66666666-6666-4666-8666-666666666666'
BEGIN READ ONLY;
SELECT set_config('app.current_tenant_id', :'tenant_id', TRUE);

-- 1. canonical Alert、首次身份与Incident；不是按source_alert_id当主键查
SELECT id, tenant_id, title, severity, status, disposition, event_time,
       ai_score, ai_summary, resolved_at,
       enrichment_data #>> '{socai2_fusion,incident_id}' AS fusion_incident_id,
       enrichment_data #>> '{socai2_fusion,identity,source_alert_id}' AS source_alert_id
FROM alerts WHERE tenant_id = :'tenant_id'::uuid AND id = :'alert_id'::uuid;

-- 2. 普通Kafka triage常见关联；不是所有独立graph的通用检索条件
SELECT id, case_id, status, error, started_at, completed_at, total_tokens
FROM investigation_runs
WHERE tenant_id = :'tenant_id'::uuid
  AND (case_id = :'alert_id' OR raw_alert->>'id' = :'alert_id')
ORDER BY started_at DESC LIMIT 20;

-- 3. 用已确认run_id读步骤，包含seq=-1；按(run_id,seq)去重
SELECT seq, ts, kind, agent, summary, payload, input_hash, output_hash, duration_ms
FROM investigation_events
WHERE tenant_id = :'tenant_id'::uuid AND run_id = :'run_id'::uuid
ORDER BY seq LIMIT 200;

-- 4. 工件目录；需要正文时按同tenant/run/id再查content/blob_ref
SELECT id, event_id, kind, sha256, size_bytes, created_at
FROM investigation_artifacts
WHERE tenant_id = :'tenant_id'::uuid AND run_id = :'run_id'::uuid
ORDER BY created_at, id;

-- 5. Case关联独立读取：alert_ids是uuid[]，不要无条件JOIN runs.case_id
SELECT c.id AS case_id, c.case_number, c.status, a.id AS alert_id, a.title
FROM aisoc_cases AS c
LEFT JOIN alerts AS a ON a.tenant_id = c.tenant_id AND a.id = ANY(c.alert_ids)
WHERE c.tenant_id = :'tenant_id'::uuid AND c.id = :'case_id'::uuid;

ROLLBACK;
