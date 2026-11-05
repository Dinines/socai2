-- Host 192.168.1.21 / database aisoc / schema public.
-- Read-only examples. Use an already authorized connection; no credentials here.
BEGIN READ ONLY;
SELECT set_config('app.current_tenant_id','f6a5c700-69b8-44fc-8238-609362fb1a9f',true);

SELECT a.id, a.title, a.severity, a.status, a.event_time, a.created_at,
       a.assigned_to_id, a.assigned_at, u.username,
       a.category, a.confidence, a.ai_score, a.disposition, a.resolved_at,
       a.enrichment_data#>>'{socai2_fusion,identity,source}' AS detection_source,
       a.enrichment_data#>>'{socai2_fusion,incident_id}' AS incident_id,
       a.case_id, a.affected_hosts, a.entities, a.raw_event
FROM public.alerts a
LEFT JOIN public.users u ON u.id=a.assigned_to_id AND u.tenant_id=a.tenant_id
WHERE a.tenant_id='f6a5c700-69b8-44fc-8238-609362fb1a9f'::uuid
  AND a.id IN ('92070605-0aa0-5e8f-8f0f-4a44222a0146'::uuid,
               '56fbc8de-9b62-5ac3-8f85-79dabc7be3a8'::uuid,
               '59f41776-1dca-5ba0-ad64-a95746ea78a5'::uuid)
ORDER BY a.event_time DESC;

-- Use this selected canonical alert for the remaining examples.
SELECT c.alert_id,c.asset_id,a.name,a.asset_type,a.tags
FROM public.alert_asset_correlations c
JOIN public.assets a ON a.id=c.asset_id AND a.tenant_id=c.tenant_id
WHERE c.tenant_id='f6a5c700-69b8-44fc-8238-609362fb1a9f'::uuid
  AND c.alert_id='92070605-0aa0-5e8f-8f0f-4a44222a0146'::uuid;

-- Automatic Run association uses raw_alert.id, NOT legacy run.case_id as a business Case.
SELECT r.id,r.status,r.started_at,r.completed_at,r.error,r.total_tokens,r.unpriced_call_count
FROM public.investigation_runs r
WHERE r.tenant_id='f6a5c700-69b8-44fc-8238-609362fb1a9f'::uuid
  AND r.raw_alert->>'id'='92070605-0aa0-5e8f-8f0f-4a44222a0146';

SELECT e.ts,e.seq,e.kind,e.summary,e.payload
FROM public.investigation_events e
JOIN public.investigation_runs r ON r.id=e.run_id AND r.tenant_id=e.tenant_id
WHERE r.tenant_id='f6a5c700-69b8-44fc-8238-609362fb1a9f'::uuid
  AND r.raw_alert->>'id'='92070605-0aa0-5e8f-8f0f-4a44222a0146'
ORDER BY e.ts DESC,e.seq DESC;

SELECT k.kind,k.sha256,k.size_bytes,k.content
FROM public.investigation_artifacts k
JOIN public.investigation_runs r ON r.id=k.run_id AND r.tenant_id=k.tenant_id
WHERE r.tenant_id='f6a5c700-69b8-44fc-8238-609362fb1a9f'::uuid
  AND r.raw_alert->>'id'='92070605-0aa0-5e8f-8f0f-4a44222a0146'
  AND k.kind IN ('graph_result','report_md');

SELECT c.model,c.call_count,c.total_prompt_tokens,c.total_completion_tokens,c.unpriced_call_count
FROM public.aisoc_run_costs c
JOIN public.investigation_runs r ON r.id::text=c.run_id AND r.tenant_id::text=c.tenant_id
WHERE r.tenant_id='f6a5c700-69b8-44fc-8238-609362fb1a9f'::uuid
  AND r.raw_alert->>'id'='92070605-0aa0-5e8f-8f0f-4a44222a0146';
ROLLBACK;
