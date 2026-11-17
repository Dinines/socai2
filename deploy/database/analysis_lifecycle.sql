-- Additive migration and grants for explicitly selected existing runtime roles.
\set ON_ERROR_STOP on
BEGIN;
SELECT set_config('socai2.migration.expected_database', :'expected_database', true);
SELECT set_config('lock_timeout', :'analysis_lock_timeout', true);
SELECT set_config('statement_timeout', :'analysis_statement_timeout', true);
SELECT EXISTS(SELECT FROM pg_roles WHERE rolname=:'analysis_writer_role'
  AND NOT (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb))
  AND EXISTS(SELECT FROM pg_roles WHERE rolname=:'reader_role') AS analysis_roles_exist \gset
\if :analysis_roles_exist
\ir ../../services/api/migrations/128_socai2_analysis_lifecycle.sql
GRANT USAGE ON SCHEMA socai2 TO :"analysis_writer_role", :"reader_role";
GRANT SELECT,INSERT,UPDATE ON socai2.analysis_tasks,socai2.analysis_attempts,socai2.analysis_subject_state TO :"analysis_writer_role";
GRANT SELECT ON socai2.analysis_tasks,socai2.analysis_attempts,socai2.analysis_subject_state TO :"reader_role";
COMMIT;
\else
ROLLBACK;
DO $failure$ BEGIN RAISE EXCEPTION 'analysis_runtime_roles_invalid'; END $failure$;
\endif
