-- Existing formal support tables only; no schema/RLS/data change.
\set ON_ERROR_STOP on
BEGIN;
SELECT current_database()=:'expected_database' AND EXISTS(SELECT FROM pg_roles WHERE rolname=:'ingress_role' AND NOT(rolsuper OR rolbypassrls)) AS ready \gset
\if :ready
SELECT set_config('lock_timeout', :'lock_timeout', true);
SELECT set_config('statement_timeout', :'statement_timeout', true);
GRANT SELECT,INSERT,UPDATE ON public.sessions,public.aisoc_ai_assets TO :"ingress_role";
GRANT SELECT,INSERT ON public.aisoc_dead_letters TO :"ingress_role";
GRANT SELECT(id,tenant_id) ON public.connectors TO :"ingress_role";
COMMIT;
\else
ROLLBACK;
\quit 3
\endif
