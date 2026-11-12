-- Existing installation: allow the selected processing identity to save immutable
-- historical cards. Required psql variables: expected_database, processing_role.
\set ON_ERROR_STOP on
SELECT current_database() = :'expected_database' AS correct_database \gset
\if :correct_database
BEGIN;
GRANT INSERT ON public.aisoc_kb_documents TO :"processing_role";
SELECT 1 / (has_table_privilege(:'processing_role', 'public.aisoc_kb_documents', 'SELECT')
    AND has_table_privilege(:'processing_role', 'public.aisoc_kb_documents', 'INSERT'))::integer;
COMMIT;
\else
\echo 'Wrong database for historical knowledge access'
\quit 3
\endif
