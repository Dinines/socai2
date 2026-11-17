-- Match the existing processing role's function access in this new database only.
\set ON_ERROR_STOP on
SELECT current_database()=:'expected_database' AS target_matches \gset
\if :target_matches
BEGIN;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA socai2 TO :"processor";
COMMIT;
SELECT current_database(), :'processor',
       has_function_privilege(:'processor','socai2.auto_adopt_baseline_result(uuid,uuid)','EXECUTE');
\else
DO $failure$ BEGIN RAISE EXCEPTION 'wrong_local_database'; END $failure$;
\endif
