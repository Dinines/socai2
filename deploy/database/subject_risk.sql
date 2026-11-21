\set ON_ERROR_STOP on
BEGIN;
SELECT set_config('socai2.migration.expected_database', :'expected_database', true);
SELECT set_config('lock_timeout', :'analysis_lock_timeout', true);
SELECT set_config('statement_timeout', :'analysis_statement_timeout', true);
\ir ../../services/api/migrations/132_socai2_subject_risk.sql
GRANT EXECUTE ON FUNCTION socai2.initialize_subject_risk(uuid,text,uuid,jsonb,text,uuid) TO :"analysis_writer_role";
\if :{?analysis_ingress_role}
GRANT EXECUTE ON FUNCTION socai2.initialize_subject_risk(uuid,text,uuid,jsonb,text,uuid) TO :"analysis_ingress_role";
\endif
COMMIT;
