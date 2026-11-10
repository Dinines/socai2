-- Existing application identity: enable the existing A/I read endpoints.
-- Parameters are provided by the selected deployment profile. This does not
-- change table definitions, RLS, ownership, role attributes, or write grants.
\set ON_ERROR_STOP on
BEGIN;
SELECT current_database() = :'expected_database'
 AND EXISTS (SELECT FROM pg_roles WHERE rolname=:'reader_role'
   AND rolcanlogin AND NOT (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb))
 AND (SELECT count(*)=29 AND bool_and(relrowsecurity AND relforcerowsecurity)
      FROM pg_class WHERE relnamespace='socai2'::regnamespace AND relkind='r')
 AS application_reader_target_matches \gset
\if :application_reader_target_matches
GRANT USAGE ON SCHEMA socai2 TO :"reader_role";
GRANT SELECT ON ALL TABLES IN SCHEMA socai2 TO :"reader_role";
COMMIT;
\ir reader_freshness_access_20261107.sql
\ir reader_public_lookups_20261107.sql
\ir verify_socai2_v1_2_reader.sql
\else
ROLLBACK;
DO $failure$ BEGIN RAISE EXCEPTION 'application_reader_target_mismatch'; END $failure$;
\endif
