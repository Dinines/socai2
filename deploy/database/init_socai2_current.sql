-- New dedicated database only. Frozen V1 followed by the same guarded increment.
\set ON_ERROR_STOP on
SELECT current_database() = :'expected_database' AS current_target_matches \gset
\if :current_target_matches
\ir init_socai2_v1.sql
\ir remove_unused_graph_table.sql
\ir analysis_lifecycle.sql
\ir case_allocation.sql
\ir subject_risk.sql
\ir analysis_task_times.sql
\ir business_verdict.sql
\if :{?analysis_ingress_role}
\ir lake_alert_receipts.sql
\ir lake_alert_deliveries.sql
\endif
\else
DO $failure$ BEGIN RAISE EXCEPTION 'current_install_target_mismatch'; END $failure$;
\endif
