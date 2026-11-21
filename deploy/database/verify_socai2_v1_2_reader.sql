-- Metadata only. No business rows, permission changes or credential output.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
WITH revision AS (
 SELECT EXISTS(SELECT FROM public.aisoc_schema_migrations
   WHERE name='127_socai2_remove_unused_graph_table.sql') AS cleaned,
   EXISTS(SELECT FROM public.aisoc_schema_migrations
   WHERE name='128_socai2_analysis_lifecycle.sql') AS lifecycle,
   EXISTS(SELECT FROM public.aisoc_schema_migrations
   WHERE name='129_socai2_case_allocation.sql') AS allocation,
   EXISTS(SELECT FROM public.aisoc_schema_migrations
   WHERE name='130_socai2_lake_alert_receipts.sql') AS lake_receipts,
   EXISTS(SELECT FROM public.aisoc_schema_migrations
   WHERE name='131_socai2_lake_alert_deliveries.sql') AS lake_deliveries,
   EXISTS(SELECT FROM public.aisoc_schema_migrations
   WHERE name='132_socai2_subject_risk.sql') AS subject_risk,
   EXISTS(SELECT FROM public.aisoc_schema_migrations
   WHERE name='133_socai2_analysis_task_times.sql') AS task_times,
   EXISTS(SELECT FROM public.aisoc_schema_migrations
   WHERE name='134_socai2_business_verdict.sql') AS business_verdict
)
SELECT current_database() = :'expected_database'
 AND (to_regclass('socai2.graph_explorations') IS NULL)=cleaned
 AND (to_regclass('socai2.lake_alert_receipts') IS NOT NULL)=lake_receipts
 AND (to_regclass('socai2.lake_alert_deliveries') IS NOT NULL)=lake_deliveries
 AND (to_regclass('socai2.lake_alert_delivery_attempts') IS NOT NULL)=lake_deliveries
 AND (SELECT count(*) FROM pg_class WHERE relnamespace='socai2'::regnamespace AND relkind='r')=CASE WHEN cleaned THEN 28 ELSE 29 END + CASE WHEN lifecycle THEN 3 ELSE 0 END + CASE WHEN allocation THEN 1 ELSE 0 END + CASE WHEN lake_receipts THEN 1 ELSE 0 END + CASE WHEN lake_deliveries THEN 2 ELSE 0 END
 AND (SELECT count(*) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
      WHERE c.relnamespace='socai2'::regnamespace AND c.relkind='r'
        AND a.attnum>0 AND NOT a.attisdropped)=CASE WHEN cleaned THEN 450 ELSE 462 END + CASE WHEN lifecycle THEN 61 ELSE 0 END + CASE WHEN allocation THEN 10 ELSE 0 END + CASE WHEN lake_receipts THEN 10 ELSE 0 END + CASE WHEN lake_deliveries THEN 25 ELSE 0 END + CASE WHEN subject_risk THEN 4 ELSE 0 END + CASE WHEN task_times THEN 3 ELSE 0 END + CASE WHEN business_verdict THEN 2 ELSE 0 END
 AND (NOT task_times OR (SELECT count(*)=3 AND bool_and(a.atttypid='timestamptz'::regtype AND NOT a.attnotnull)
     FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
     WHERE c.relnamespace='socai2'::regnamespace AND a.attnum>0 AND NOT a.attisdropped
       AND ((c.relname='analysis_tasks' AND a.attname IN ('first_enqueued_at','next_attempt_enqueued_at'))
         OR (c.relname='analysis_attempts' AND a.attname='enqueued_at'))))
 AND (NOT business_verdict OR (SELECT count(*)=2 AND bool_and(a.atttypid='text'::regtype AND NOT a.attnotnull AND NOT a.atthasdef)
     FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
     WHERE c.relnamespace='socai2'::regnamespace AND a.attnum>0 AND NOT a.attisdropped
       AND c.relname IN ('incident_diagnoses','results') AND a.attname='business_verdict'))
 AND has_schema_privilege(:'reader_role','socai2','USAGE')
 AND NOT has_schema_privilege(:'reader_role','socai2','CREATE')
 AND has_table_privilege(:'reader_role','public.assets','SELECT')
 AND has_table_privilege(:'reader_role','public.users','SELECT')
 AND has_table_privilege(:'reader_role','public.aisoc_kb_documents','SELECT')
 AND NOT EXISTS (SELECT FROM pg_class c WHERE c.relnamespace='socai2'::regnamespace
   AND c.relkind='r' AND (NOT c.relrowsecurity OR NOT c.relforcerowsecurity
     OR NOT has_table_privilege(:'reader_role',c.oid,'SELECT')
     OR has_table_privilege(:'reader_role',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE')
     OR has_any_column_privilege(:'reader_role',c.oid,'INSERT,UPDATE')))
 AND (SELECT count(*)=2 AND bool_and(has_function_privilege(:'reader_role',p.oid,'EXECUTE'))
      FROM pg_proc p WHERE p.oid IN (
        to_regprocedure('socai2.baseline_input_freshness(uuid,uuid)'),
        to_regprocedure('socai2.task_feedback_signature(jsonb)'))) AS reader_v1_2_ready FROM revision \gset
ROLLBACK;
\if :reader_v1_2_ready
\echo verified_socai2_v1_2_reader
\else
DO $failure$ BEGIN RAISE EXCEPTION 'reader_v1_2_dependency_or_permission_mismatch'; END $failure$;
\endif
