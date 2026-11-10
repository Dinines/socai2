-- V1 + V1.2 read dependencies on a NEW dedicated database only.
-- This does not install processor/Fusion roles or seed business/credential data.
-- Provision a restricted LOGIN reader role first through deployment secrets.
-- Run as the deployment administrator; schema ownership is explicit.
\set ON_ERROR_STOP on
SELECT current_database() = :'expected_database'
 AND EXISTS (SELECT FROM pg_roles WHERE rolname=:'function_owner')
 AND to_regnamespace('socai2') IS NULL
 AND EXISTS (SELECT FROM pg_roles WHERE rolname=:'reader_role'
   AND rolcanlogin AND NOT (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb))
 AS fresh_target_matches \gset
\if :fresh_target_matches
SET ROLE :"function_owner";
\ir init_socai2_v1.sql
RESET ROLE;
BEGIN;
GRANT CONNECT ON DATABASE :"expected_database" TO :"reader_role";
GRANT USAGE ON SCHEMA socai2 TO :"reader_role";
-- Exactly the frozen V1 tables at initialization, not a default grant on future tables.
GRANT SELECT ON ALL TABLES IN SCHEMA socai2 TO :"reader_role";
ALTER ROLE :"reader_role" IN DATABASE :"expected_database" SET default_transaction_read_only=on;
COMMIT;
\ir upgrade_socai2_v1_2_reader.sql
\else
DO $failure$ BEGIN RAISE EXCEPTION 'reader_v1_2_requires_fresh_database_and_explicit_owner'; END $failure$;
\endif
