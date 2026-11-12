-- Explicitly authorized cleanup; caller supplies target and transaction/time limits.
-- V1 migrations 123-126 and all retained tables/data stay unchanged.
DO $cleanup$
DECLARE
  target regclass := to_regclass('socai2.graph_explorations');
  actual text[];
  expected constant text[] := ARRAY[
    'id:uuid:true','tenant_id:uuid:true','case_id:uuid:true',
    'base_result_id:uuid:false','base_graph_artifact_id:uuid:false',
    'base_input_artifact_id:uuid:true','graph_state:jsonb:true',
    'created_at:timestamp with time zone:true','created_by:uuid:true',
    'updated_at:timestamp with time zone:true','updated_by:uuid:true','row_version:bigint:true'];
BEGIN
  IF current_database() IS DISTINCT FROM current_setting('socai2.cleanup.expected_database', true)
     OR current_setting('server_version_num')::integer / 10000 <> 16
     OR to_regclass('public.aisoc_schema_migrations') IS NULL THEN
    RAISE EXCEPTION 'cleanup_target_or_baseline_mismatch';
  END IF;
  PERFORM pg_advisory_xact_lock(hashtext('socai2'), hashtext('schema-initialization'));
  IF NOT EXISTS (SELECT FROM public.aisoc_schema_migrations WHERE name='123_socai2_page_data_model.sql') THEN
    RAISE EXCEPTION 'cleanup_creation_baseline_missing';
  END IF;
  IF target IS NULL THEN
    IF NOT EXISTS (SELECT FROM public.aisoc_schema_migrations
                   WHERE name='127_socai2_remove_unused_graph_table.sql') THEN
      RAISE EXCEPTION 'cleanup_table_missing_without_receipt';
    END IF;
    RETURN;
  END IF;
  IF EXISTS (SELECT FROM public.aisoc_schema_migrations
             WHERE name='127_socai2_remove_unused_graph_table.sql') THEN
    RAISE EXCEPTION 'cleanup_table_recreated_after_migration';
  END IF;
  LOCK TABLE socai2.graph_explorations IN ACCESS EXCLUSIVE MODE;
  -- Prevent RLS from hiding rows during the emptiness check. Non-bypass users
  -- get an error rather than an incorrect empty result on a FORCE RLS table.
  PERFORM set_config('row_security', 'off', true);
  SELECT array_agg(attname || ':' || format_type(atttypid,atttypmod) || ':' || attnotnull ORDER BY attnum)
    INTO actual FROM pg_attribute WHERE attrelid=target AND attnum>0 AND NOT attisdropped;
  IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'cleanup_table_shape_mismatch'; END IF;
  IF EXISTS (SELECT FROM socai2.graph_explorations) THEN
    RAISE EXCEPTION 'cleanup_table_contains_data';
  END IF;
  IF EXISTS (SELECT FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
             WHERE n.nspname NOT IN ('pg_catalog','information_schema')
               AND p.prosrc LIKE '%graph_explorations%') THEN
    RAISE EXCEPTION 'cleanup_function_reference_exists';
  END IF;
  DROP TABLE socai2.graph_explorations RESTRICT;
  INSERT INTO public.aisoc_schema_migrations(name) VALUES ('127_socai2_remove_unused_graph_table.sql');
END
$cleanup$;
