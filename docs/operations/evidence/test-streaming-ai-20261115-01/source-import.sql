\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE source_fixture(plan jsonb NOT NULL) ON COMMIT DROP;
INSERT INTO source_fixture VALUES (:'source_plan'::jsonb);
DO $$
DECLARE p jsonb; a jsonb;
BEGIN
 SELECT plan INTO STRICT p FROM source_fixture;
 a := p->'asset';
 IF current_database() <> p#>>'{target,database}'
    OR current_user <> p#>>'{target,installer_role}'
    OR a->>'tenant_id' <> p#>>'{target,tenant_id}'
    OR a->>'asset_type' <> 'host'
    OR (a#>>'{metadata,synthetic}')::boolean IS DISTINCT FROM true
    OR a#>>'{metadata,batch_id}' <> p->>'batch_id'
    OR NOT (a->'tags' @> '["synthetic"]'::jsonb)
    OR p#>'{threat_intel,insert_rows}' <> '[]'::jsonb
    OR p#>'{history,insert_rows}' <> '[]'::jsonb
 THEN RAISE EXCEPTION 'source_fixture_target_or_scope_mismatch'; END IF;
 IF NOT EXISTS (SELECT 1 FROM public.tenants WHERE id=(a->>'tenant_id')::uuid)
 THEN RAISE EXCEPTION 'source_fixture_tenant_missing'; END IF;
 IF EXISTS (SELECT 1 FROM public.assets
   WHERE id=(a->>'id')::uuid OR (tenant_id=(a->>'tenant_id')::uuid
    AND (lower(name)=lower(a->>'name')
      OR ip_addresses && ARRAY(SELECT jsonb_array_elements_text(a->'ip_addresses')))))
 THEN RAISE EXCEPTION 'source_fixture_already_present_or_collision_no_overwrite'; END IF;
END $$;
INSERT INTO public.assets(id,tenant_id,asset_type,name,ip_addresses,criticality,tags,metadata,
 first_seen,last_seen,created_at,updated_at)
 SELECT (a->>'id')::uuid,(a->>'tenant_id')::uuid,a->>'asset_type',a->>'name',
  ARRAY(SELECT jsonb_array_elements_text(a->'ip_addresses')),a->>'criticality',
  ARRAY(SELECT jsonb_array_elements_text(a->'tags')),a->'metadata',
  statement_timestamp(),statement_timestamp(),statement_timestamp(),statement_timestamp()
 FROM (SELECT plan->'asset' a FROM source_fixture) input;
SELECT jsonb_build_object('database',current_database(),'role',current_user,
 'captured_at',clock_timestamp(),'operation','insert_one_synthetic_asset',
 'record',to_jsonb(a)) FROM public.assets a,source_fixture f
 WHERE a.id=(f.plan#>>'{asset,id}')::uuid AND a.tenant_id=(f.plan#>>'{target,tenant_id}')::uuid;
COMMIT;
