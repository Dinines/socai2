-- PostgreSQL 16. Read only the processing schema's catalog, never business rows.
-- psql -XAtq -v ON_ERROR_STOP=1 -f read_socai2_v1_catalog.sql
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL search_path = pg_catalog;
WITH relations AS (
    SELECT c.* FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'socai2' AND c.relkind IN ('r', 'p')
), objects(section, name, definition) AS (
    SELECT 'tables', relname::text,
           jsonb_build_array(relkind, relpersistence, relrowsecurity, relforcerowsecurity)
    FROM relations
    UNION ALL
    SELECT 'columns', r.relname || '.' || a.attname,
           jsonb_build_array(a.attnum, format_type(a.atttypid, a.atttypmod),
               NOT a.attnotnull, pg_get_expr(d.adbin, d.adrelid), a.attidentity, a.attgenerated)
    FROM relations r JOIN pg_attribute a ON a.attrelid = r.oid
    LEFT JOIN pg_attrdef d ON d.adrelid = r.oid AND d.adnum = a.attnum
    WHERE a.attnum > 0 AND NOT a.attisdropped
    UNION ALL
    SELECT 'constraints', r.relname || '.' || c.conname,
           jsonb_build_array(pg_get_constraintdef(c.oid), c.convalidated)
    FROM relations r JOIN pg_constraint c ON c.conrelid = r.oid
    UNION ALL
    SELECT 'indexes', r.relname || '.' || i.relname,
           jsonb_build_array(pg_get_indexdef(x.indexrelid), x.indisvalid, x.indisready)
    FROM relations r JOIN pg_index x ON x.indrelid = r.oid
    JOIN pg_class i ON i.oid = x.indexrelid
    UNION ALL
    SELECT 'policies', r.relname || '.' || p.polname,
           jsonb_build_array(p.polcmd, p.polpermissive, ARRAY(
               SELECT CASE WHEN role_id = 0 THEN 'PUBLIC' ELSE pg_get_userbyid(role_id)::text END
               FROM unnest(p.polroles) role_id ORDER BY 1),
               pg_get_expr(p.polqual, r.oid), pg_get_expr(p.polwithcheck, r.oid))
    FROM relations r JOIN pg_policy p ON p.polrelid = r.oid
    UNION ALL
    SELECT 'triggers', r.relname || '.' || t.tgname,
           jsonb_build_array(pg_get_triggerdef(t.oid), t.tgenabled)
    FROM relations r JOIN pg_trigger t ON t.tgrelid = r.oid WHERE NOT t.tgisinternal
    UNION ALL
    SELECT 'functions', p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')',
           to_jsonb(replace(pg_get_functiondef(p.oid), E'\r\n', E'\n'))
    FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname = 'socai2'
), sections AS (
    SELECT section, jsonb_object_agg(name, definition) AS objects FROM objects GROUP BY section
)
SELECT jsonb_build_object(
    'database', current_database(),
    'server_version', current_setting('server_version'),
    'objects', (SELECT jsonb_object_agg(section, objects) FROM sections),
    'fingerprints', (SELECT jsonb_object_agg(section, encode(sha256(convert_to(objects::text,'UTF8')),'hex'))
                     FROM sections)
);
ROLLBACK;
