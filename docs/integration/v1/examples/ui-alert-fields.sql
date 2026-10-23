-- psql：告警页面字段直查，仅取已确认的两条合成样例。
-- 新增展开SELECT本次按实际字段目录/既有样例JSON校核，未重新在生产执行。
-- investigation后续查询沿用 production-two-examples.sql（已有实际执行记录）。
-- 使用获授权的只读连接与CA；不包含数据库密码。
\set ON_ERROR_STOP on
\set tenant_id 'f6a5c700-69b8-44fc-8238-609362fb1a9f'
\set alert_1 'bc625c39-56af-5403-a378-9bfb99c610d2'
\set alert_2 'e5f593f0-b328-59c3-8238-379db33d8bfe'
BEGIN READ ONLY;
SELECT set_config('app.current_tenant_id', :'tenant_id', TRUE);

SELECT a.id, a.tenant_id, a.title, a.description,
       a.severity, a.status, a.disposition,
       a.event_time, a.created_at, a.first_seen, a.last_seen,
       a.updated_at, a.resolved_at,
       a.enrichment_data #>> '{socai2_fusion,identity,source}' AS source,
       a.enrichment_data #>> '{socai2_fusion,identity,source_alert_id}' AS source_alert_id,
       a.connector_type, a.connector_id,
       a.source_event_ids, a.external_id,
       a.enrichment_data #>> '{socai2_fusion,delivery_snapshot,fused,alert,rule_id}' AS source_rule_id,
       a.enrichment_data #>> '{socai2_fusion,delivery_snapshot,fused,alert,rule_name}' AS source_rule_name,
       a.enrichment_data #>> '{socai2_fusion,delivery_snapshot,fused,alert,src_ip}' AS source_ip,
       a.enrichment_data #>> '{socai2_fusion,delivery_snapshot,fused,alert,dst_ip}' AS destination_ip,
       a.affected_hosts, a.affected_users, a.affected_ips, a.entities, a.iocs,
       a.raw_event ->> 'process_name' AS source_process_name,
       a.raw_event ->> 'command_line' AS source_command_line,
       a.raw_event ->> 'destination_port' AS source_destination_port,
       a.mitre_tactics, a.mitre_techniques, a.category, a.tags,
       a.assigned_to_id, a.assigned_at, a.case_id,
       a.enrichment_data #>> '{socai2_fusion,incident_id}' AS fusion_incident_id,
       a.ai_score AS triage_confidence, a.ai_summary, a.ai_recommendations,
       a.confidence AS fusion_confidence, a.confidence_label, a.confidence_rationale,
       a.narrative AS fusion_narrative,
       a.enrichment_data #> '{socai2_fusion,ioc_lookup}' AS fusion_ioc_lookup,
       a.raw_event
FROM public.alerts AS a
WHERE a.tenant_id = :'tenant_id'::uuid
  AND a.id IN (:'alert_1'::uuid, :'alert_2'::uuid)
ORDER BY a.event_time, a.id;

-- 示例只读结束；具体查询条件/分页由接入方按页面要求实现。
ROLLBACK;
