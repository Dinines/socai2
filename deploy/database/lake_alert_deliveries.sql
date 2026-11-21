\set ON_ERROR_STOP on
BEGIN;
SELECT set_config('socai2.migration.expected_database', :'expected_database', true);
SELECT set_config('lock_timeout', :'analysis_lock_timeout', true);
SELECT set_config('statement_timeout', :'analysis_statement_timeout', true);
\ir ../../services/api/migrations/131_socai2_lake_alert_deliveries.sql
GRANT USAGE ON SCHEMA socai2 TO :"analysis_ingress_role";
GRANT SELECT,INSERT,UPDATE ON socai2.lake_alert_deliveries,socai2.lake_alert_delivery_attempts TO :"analysis_ingress_role";
GRANT SELECT ON socai2.lake_alert_deliveries,socai2.lake_alert_delivery_attempts TO :"reader_role";
COMMIT;
