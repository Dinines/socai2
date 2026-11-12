BEGIN READ ONLY;
WITH retained AS (
 SELECT n.nspname,c.relname,c.oid,c.relowner,c.relacl,c.relrowsecurity,c.relforcerowsecurity,
  (SELECT jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull) ORDER BY a.attnum)
   FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped) AS columns,
  (SELECT jsonb_agg(pg_get_constraintdef(x.oid) ORDER BY x.conname) FROM pg_constraint x WHERE x.conrelid=c.oid) AS constraints,
  (SELECT jsonb_agg(pg_get_indexdef(i.indexrelid) ORDER BY i.indexrelid) FROM pg_index i WHERE i.indrelid=c.oid) AS indexes
 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%'
 AND n.nspname NOT LIKE 'pg_temp%' AND c.relkind IN ('r','p')
 AND NOT (n.nspname='socai2' AND c.relname='graph_explorations')
)
SELECT jsonb_build_object('database',current_database(),'role',current_user,
 'retained_catalog_sha256',encode(sha256(convert_to((SELECT jsonb_agg(to_jsonb(t) ORDER BY nspname,relname)::text FROM retained t),'UTF8')),'hex'),
 'retained_table_count',(SELECT count(*) FROM retained),
 'socai2_tables',(SELECT count(*) FROM pg_class WHERE relnamespace='socai2'::regnamespace AND relkind='r'),
 'socai2_columns',(SELECT count(*) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid WHERE c.relnamespace='socai2'::regnamespace AND c.relkind='r' AND a.attnum>0 AND NOT a.attisdropped),
 'graph_exists',to_regclass('socai2.graph_explorations') IS NOT NULL,
 'cleanup_recorded',EXISTS(SELECT FROM public.aisoc_schema_migrations WHERE name='127_socai2_remove_unused_graph_table.sql'),
 'alerts',(SELECT count(*) FROM socai2.alerts),'cases',(SELECT count(*) FROM socai2.cases),
 'runs',(SELECT count(*) FROM socai2.runs),'artifacts',(SELECT count(*) FROM socai2.artifacts));
ROLLBACK;
