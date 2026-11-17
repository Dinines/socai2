-- Additive Case allocation; reuse explicit existing writer/reader roles and timeouts.
\set ON_ERROR_STOP on
BEGIN;
SELECT set_config('socai2.migration.expected_database', :'expected_database', true);
SELECT set_config('lock_timeout', :'analysis_lock_timeout', true);
SELECT set_config('statement_timeout', :'analysis_statement_timeout', true);
SELECT EXISTS(SELECT FROM pg_roles WHERE rolname=:'analysis_writer_role'
  AND NOT (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb))
  AND EXISTS(SELECT FROM pg_roles WHERE rolname=:'reader_role') AS allocation_roles_exist \gset
\if :allocation_roles_exist
\ir ../../services/api/migrations/129_socai2_case_allocation.sql
GRANT SELECT,INSERT,UPDATE,DELETE ON socai2.case_alert_exclusions TO :"analysis_writer_role";
GRANT SELECT ON socai2.case_alert_exclusions TO :"reader_role";
COMMIT;
\else
ROLLBACK;
DO $failure$ BEGIN RAISE EXCEPTION 'case_allocation_runtime_roles_invalid'; END $failure$;
\endif
