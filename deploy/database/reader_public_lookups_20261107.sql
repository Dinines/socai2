-- V1.2 development read access, explicitly authorized by the project owner.
-- Required psql variables come from the selected deployment profile.
-- No new functions, business writes, table definitions or RLS changes.
\set ON_ERROR_STOP on
BEGIN;
SELECT current_database() = :'expected_database'
 AND EXISTS (SELECT FROM pg_roles WHERE rolname=:'reader_role'
   AND rolcanlogin AND NOT (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb))
 AS target_matches \gset
\if :target_matches
GRANT SELECT ON public.assets, public.users TO :"reader_role";
COMMIT;
\else
ROLLBACK;
DO $failure$ BEGIN RAISE EXCEPTION 'reader_public_lookup_target_mismatch'; END $failure$;
\endif
