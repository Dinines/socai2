-- Fresh reader installation plus explicitly configured current-schema cleanup.
\set ON_ERROR_STOP on
\ir init_socai2_v1_2_reader.sql
\ir remove_unused_graph_table.sql
\ir analysis_lifecycle.sql
\ir case_allocation.sql
\ir subject_risk.sql
\ir analysis_task_times.sql
\ir business_verdict.sql
\if :{?analysis_ingress_role}
\ir analysis_ingress_access.sql
\ir lake_alert_receipts.sql
\ir lake_alert_deliveries.sql
\endif
\ir verify_socai2_v1_2_reader.sql
