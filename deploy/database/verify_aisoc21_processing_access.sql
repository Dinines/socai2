-- Validation runs both after first installation and on subsequent deployments.
DO $verify$
DECLARE
  item record;
  role_name name;
  immutable_tables text[] := ARRAY['alert_materials','alert_source_refs','alert_objects','alert_assessments',
    'case_assessments','case_assessment_sources','case_assessment_members','artifacts','results','result_members',
    'task_revisions','activities','activity_targets','response_links'];
BEGIN
  IF (SELECT count(*) FROM pg_roles WHERE rolname IN ('socai2_prod_reader','socai2_prod_processor',
    'socai2_prod_ingress') AND rolcanlogin AND NOT (rolsuper OR rolinherit OR rolcreatedb OR rolcreaterole
    OR rolreplication OR rolbypassrls) AND shobj_description(oid,'pg_authid')='socai2:production:v1') <> 3
  THEN RAISE EXCEPTION 'Production runtime identities do not match this installation'; END IF;
  IF (SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname='socai2') <> 'aisoc'
    OR has_schema_privilege('aisoc_app','socai2','USAGE')
    OR to_regprocedure('socai2_ops.prod_alert_sources(uuid,uuid,boolean)') IS NULL
    OR NOT has_function_privilege('socai2_prod_ingress','socai2_ops.prod_alert_sources(uuid,uuid,boolean)','EXECUTE')
    OR has_function_privilege('socai2_prod_reader','socai2_ops.prod_alert_sources(uuid,uuid,boolean)','EXECUTE')
  THEN RAISE EXCEPTION 'Unexpected schema owner, integration permissions or source function'; END IF;
  FOREACH role_name IN ARRAY ARRAY['socai2_prod_reader','socai2_prod_processor','socai2_prod_ingress']::name[]
  LOOP
    IF has_schema_privilege(role_name,'socai2','CREATE') OR has_schema_privilege(role_name,'public','CREATE')
       OR EXISTS (SELECT FROM pg_auth_members WHERE member=role_name::regrole)
       OR EXISTS (SELECT FROM pg_class c WHERE c.relnamespace='public'::regnamespace
         AND c.relkind IN ('r','p') AND (c.relname LIKE '%alert%' OR c.relname LIKE '%incident%')
         AND (has_any_column_privilege(role_name,c.oid,'INSERT,UPDATE') OR has_table_privilege(role_name,c.oid,'DELETE,TRUNCATE')))
    THEN RAISE EXCEPTION 'Excessive existing-table privileges on %',role_name; END IF;
  END LOOP;
  FOR item IN SELECT relname,oid FROM pg_class WHERE relnamespace='socai2'::regnamespace AND relkind='r' LOOP
    IF NOT has_table_privilege('socai2_prod_reader',item.oid,'SELECT')
       OR has_any_column_privilege('socai2_prod_reader',item.oid,'INSERT,UPDATE')
       OR has_table_privilege('socai2_prod_reader',item.oid,'DELETE,TRUNCATE,TRIGGER')
       OR NOT has_table_privilege('socai2_prod_processor',item.oid,'INSERT')
       OR (item.relname=ANY(immutable_tables) AND has_table_privilege('socai2_prod_processor',item.oid,'UPDATE,DELETE'))
    THEN RAISE EXCEPTION 'Unexpected V1 ACL on %',item.relname; END IF;
  END LOOP;
END $verify$;
