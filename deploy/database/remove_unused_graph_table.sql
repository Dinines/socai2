-- Run only for an explicitly selected/authorized database after reader rollout.
-- psql -v expected_database=<database> -v cleanup_lock_timeout=3s
--      -v cleanup_statement_timeout=30s -f remove_unused_graph_table.sql
\set ON_ERROR_STOP on
BEGIN;
SELECT set_config('socai2.cleanup.expected_database', :'expected_database', true);
SELECT set_config('lock_timeout', :'cleanup_lock_timeout', true);
SELECT set_config('statement_timeout', :'cleanup_statement_timeout', true);
\ir ../../services/api/migrations/127_socai2_remove_unused_graph_table.sql
COMMIT;
