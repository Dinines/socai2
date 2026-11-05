-- Read-only PostgreSQL catalog inspection for the schema plan dated 2026-11-03.
-- Not executed by this task. No business rows, credentials, or raw events are read.
-- Proposed tables being absent is expected before implementation.
-- This does not verify migration history, application behavior, or data quality.

-- 1. Existing / proposed table inventory and RLS flags.
WITH expected(table_name, role) AS (
    VALUES
        ('aisoc_cases', 'existing'),
        ('aisoc_case_tasks', 'existing'),
        ('aisoc_case_comments', 'existing'),
        ('case_timeline_events', 'existing'),
        ('case_status_transitions', 'existing'),
        ('investigation_case_links', 'existing'),
        ('investigation_runs', 'existing'),
        ('investigation_events', 'existing'),
        ('investigation_artifacts', 'existing'),
        ('aisoc_copilot_conversations', 'existing'),
        ('fusion_incident_summaries', 'existing'),
        ('agent_approvals', 'existing'),
        ('aisoc_action_records', 'existing'),
        ('audit_log', 'existing'),
        ('case_saved_ai_records', 'proposed_core'),
        ('case_incident_links', 'proposed_core'),
        ('case_graph_explorations', 'proposed_core'),
        ('fusion_incident_state', 'proposed_supporting'),
        ('alert_comments', 'proposed_supporting')
)
SELECT e.table_name, e.role, c.oid IS NOT NULL AS present,
       c.relkind, c.relrowsecurity, c.relforcerowsecurity
FROM expected e
LEFT JOIN pg_catalog.pg_class c
    ON c.oid = pg_catalog.to_regclass('public.' || e.table_name)
ORDER BY e.role, e.table_name;

-- 2. Current columns, types, nullability and defaults.
SELECT table_name, ordinal_position, column_name,
       data_type, udt_name, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = ANY (ARRAY[
      'aisoc_cases', 'aisoc_case_tasks', 'aisoc_case_comments',
      'case_timeline_events', 'case_status_transitions',
      'investigation_case_links', 'investigation_runs',
      'investigation_events', 'investigation_artifacts',
      'aisoc_copilot_conversations', 'fusion_incident_summaries',
      'agent_approvals', 'aisoc_action_records', 'audit_log',
      'case_saved_ai_records', 'case_incident_links',
      'case_graph_explorations', 'fusion_incident_state', 'alert_comments'
  ])
ORDER BY table_name, ordinal_position;

-- 3. Check constraints, FKs and uniqueness, including referenced tables.
SELECT r.relname AS table_name, k.conname, k.contype, k.convalidated,
       referenced.relname AS referenced_table,
       pg_catalog.pg_get_constraintdef(k.oid, true) AS definition
FROM pg_catalog.pg_constraint k
JOIN pg_catalog.pg_class r ON r.oid = k.conrelid
JOIN pg_catalog.pg_namespace n ON n.oid = r.relnamespace
LEFT JOIN pg_catalog.pg_class referenced ON referenced.oid = k.confrelid
WHERE n.nspname = 'public'
  AND r.relname = ANY (ARRAY[
      'aisoc_cases', 'aisoc_case_tasks', 'aisoc_case_comments',
      'case_timeline_events', 'case_status_transitions',
      'investigation_case_links', 'investigation_runs',
      'investigation_events', 'investigation_artifacts',
      'aisoc_copilot_conversations', 'fusion_incident_summaries',
      'agent_approvals', 'aisoc_action_records', 'audit_log',
      'case_saved_ai_records', 'case_incident_links',
      'case_graph_explorations', 'fusion_incident_state', 'alert_comments'
  ])
ORDER BY r.relname, k.contype, k.conname;

-- 4. Indexes: partial unique predicates matter for active Runs / Case chats.
SELECT tablename, indexname, indexdef
FROM pg_catalog.pg_indexes
WHERE schemaname = 'public'
  AND tablename = ANY (ARRAY[
      'aisoc_cases', 'aisoc_case_tasks', 'aisoc_case_comments',
      'case_timeline_events', 'case_status_transitions',
      'investigation_case_links', 'investigation_runs',
      'investigation_events', 'investigation_artifacts',
      'aisoc_copilot_conversations', 'fusion_incident_summaries',
      'agent_approvals', 'aisoc_action_records', 'audit_log',
      'case_saved_ai_records', 'case_incident_links',
      'case_graph_explorations', 'fusion_incident_state', 'alert_comments'
  ])
ORDER BY tablename, indexname;

-- 5. RLS definitions. Application-level tenant checks still need code review.
SELECT tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_catalog.pg_policies
WHERE schemaname = 'public'
  AND tablename = ANY (ARRAY[
      'aisoc_cases', 'aisoc_case_tasks', 'aisoc_case_comments',
      'case_timeline_events', 'case_status_transitions',
      'investigation_case_links', 'investigation_runs',
      'investigation_events', 'investigation_artifacts',
      'aisoc_copilot_conversations', 'fusion_incident_summaries',
      'agent_approvals', 'aisoc_action_records', 'audit_log',
      'case_saved_ai_records', 'case_incident_links',
      'case_graph_explorations', 'fusion_incident_state', 'alert_comments'
  ])
ORDER BY tablename, policyname;

-- 6. Existing immutability triggers; do not assume all artifact tables have one.
SELECT r.relname AS table_name, t.tgname, t.tgenabled,
       pg_catalog.pg_get_triggerdef(t.oid, true) AS definition
FROM pg_catalog.pg_trigger t
JOIN pg_catalog.pg_class r ON r.oid = t.tgrelid
JOIN pg_catalog.pg_namespace n ON n.oid = r.relnamespace
WHERE n.nspname = 'public'
  AND NOT t.tgisinternal
  AND r.relname = ANY (ARRAY[
      'investigation_events', 'investigation_artifacts', 'audit_log',
      'case_saved_ai_records', 'case_timeline_events'
  ])
ORDER BY r.relname, t.tgname;
