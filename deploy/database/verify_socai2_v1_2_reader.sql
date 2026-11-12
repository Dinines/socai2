-- Metadata only. No business rows, permission changes or credential output.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
WITH revision AS (
 SELECT EXISTS(SELECT FROM public.aisoc_schema_migrations
   WHERE name='127_socai2_remove_unused_graph_table.sql') AS cleaned
)
SELECT current_database() = :'expected_database'
 AND (to_regclass('socai2.graph_explorations') IS NULL)=cleaned
 AND (SELECT count(*) FROM pg_class WHERE relnamespace='socai2'::regnamespace AND relkind='r')=CASE WHEN cleaned THEN 28 ELSE 29 END
 AND (SELECT count(*) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
      WHERE c.relnamespace='socai2'::regnamespace AND c.relkind='r'
        AND a.attnum>0 AND NOT a.attisdropped)=CASE WHEN cleaned THEN 450 ELSE 462 END
 AND has_schema_privilege(:'reader_role','socai2','USAGE')
 AND NOT has_schema_privilege(:'reader_role','socai2','CREATE')
 AND has_table_privilege(:'reader_role','public.assets','SELECT')
 AND has_table_privilege(:'reader_role','public.users','SELECT')
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
