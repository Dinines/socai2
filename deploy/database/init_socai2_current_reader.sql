-- Fresh reader installation plus explicitly configured current-schema cleanup.
\set ON_ERROR_STOP on
\ir init_socai2_v1_2_reader.sql
\ir remove_unused_graph_table.sql
\ir verify_socai2_v1_2_reader.sql
