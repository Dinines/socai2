-- V1.2 read dependencies, for an existing approved V1 installation.
-- Public SELECT authorized for development; see the active OpenSpec record.
-- Required psql variables: expected_database, reader_role, function_owner.
-- The same increments are used by init_socai2_v1_2_reader.sql.
\set ON_ERROR_STOP on
\ir reader_freshness_access_20261107.sql
\ir reader_public_lookups_20261107.sql
\ir verify_socai2_v1_2_reader.sql
