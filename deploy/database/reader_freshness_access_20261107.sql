-- Incremental grant only. User-approved scope is recorded in the active OpenSpec change.
-- psql variables expected_database and reader_role must come from the selected configuration.
\set ON_ERROR_STOP on
BEGIN;
SELECT current_database() = :'expected_database'
 AND EXISTS (SELECT FROM pg_roles WHERE rolname=:'reader_role'
   AND rolcanlogin AND NOT (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb))
 AND EXISTS (SELECT FROM pg_proc WHERE oid='socai2.baseline_input_freshness(uuid,uuid)'::regprocedure
   AND NOT prosecdef AND provolatile='s')
 AND EXISTS (SELECT FROM pg_proc WHERE oid='socai2.task_feedback_signature(jsonb)'::regprocedure
   AND NOT prosecdef AND provolatile='i') AS target_matches \gset
\if :target_matches
GRANT EXECUTE ON FUNCTION socai2.baseline_input_freshness(uuid,uuid) TO :"reader_role";
GRANT EXECUTE ON FUNCTION socai2.task_feedback_signature(jsonb) TO :"reader_role";
COMMIT;
\else
ROLLBACK;
DO $failure$ BEGIN RAISE EXCEPTION 'reader_freshness_target_mismatch'; END $failure$;
\endif
