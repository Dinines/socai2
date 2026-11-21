\set ON_ERROR_STOP on
BEGIN;
SELECT set_config('socai2.migration.expected_database', :'expected_database', true);
SELECT set_config('lock_timeout', :'analysis_lock_timeout', true);
SELECT set_config('statement_timeout', :'analysis_statement_timeout', true);
\ir ../../services/api/migrations/134_socai2_business_verdict.sql
COMMIT;
