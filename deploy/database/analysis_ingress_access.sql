-- Ordinary functional grants for the selected existing ingress writer; no new role.
\set ON_ERROR_STOP on
BEGIN;
SELECT current_database()=:'expected_database' AND EXISTS(SELECT FROM pg_roles
  WHERE rolname=:'analysis_ingress_role' AND NOT (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb)) AS ingress_ready \gset
\if :ingress_ready
SELECT set_config('lock_timeout', :'analysis_ingress_lock_timeout', true);
SELECT set_config('statement_timeout', :'analysis_ingress_statement_timeout', true);
GRANT USAGE ON SCHEMA socai2 TO :"analysis_ingress_role";
GRANT SELECT,INSERT ON socai2.analysis_tasks,socai2.analysis_subject_state TO :"analysis_ingress_role";
COMMIT;
\else
ROLLBACK;
DO $failure$ BEGIN RAISE EXCEPTION 'analysis_ingress_target_invalid'; END $failure$;
\endif
