-- Additive creation state only. No UPDATE/backfill of existing subjects.
DO $preflight$
BEGIN
  IF current_database() IS DISTINCT FROM current_setting('socai2.migration.expected_database', true)
     OR to_regclass('socai2.case_alert_exclusions') IS NULL THEN
    RAISE EXCEPTION 'subject_risk_migration_target_mismatch';
  END IF;
  PERFORM pg_advisory_xact_lock(hashtext('socai2'), hashtext('schema-initialization'));
END $preflight$;

ALTER TABLE socai2.incidents ADD COLUMN IF NOT EXISTS severity text;
ALTER TABLE socai2.incidents ADD COLUMN IF NOT EXISTS severity_source text;
ALTER TABLE socai2.incidents ADD COLUMN IF NOT EXISTS risk_metadata jsonb;
ALTER TABLE socai2.cases ADD COLUMN IF NOT EXISTS risk_metadata jsonb;
DO $constraints$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_severity_enum') THEN
    ALTER TABLE socai2.incidents ADD CONSTRAINT incidents_severity_enum
      CHECK (severity IN ('info','low','medium','high','critical'));
  END IF;
  IF NOT EXISTS (SELECT FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_risk_metadata_object') THEN
    ALTER TABLE socai2.incidents ADD CONSTRAINT incidents_risk_metadata_object CHECK (jsonb_typeof(risk_metadata)='object');
  END IF;
  IF NOT EXISTS (SELECT FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_risk_metadata_object') THEN
    ALTER TABLE socai2.cases ADD CONSTRAINT cases_risk_metadata_object CHECK (jsonb_typeof(risk_metadata)='object');
  END IF;
END $constraints$;

-- Shared by native Fusion and API creation, under the caller's transaction/RLS.
-- No SECURITY DEFINER, dynamic SQL, model I/O or configuration defaults.
CREATE OR REPLACE FUNCTION socai2.initialize_subject_risk(
  p_tenant uuid, p_kind text, p_subject uuid, p_policy jsonb,
  p_manual_level text DEFAULT NULL, p_actor uuid DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE
  levels text[] := ARRAY['info','low','medium','high','critical'];
  saved jsonb; members jsonb; initial_level text; initial_source text;
  effective text; source text; score numeric; result jsonb; now_at timestamptz;
BEGIN
  IF p_tenant IS DISTINCT FROM public.current_tenant_id() OR p_kind NOT IN ('incident','case') OR p_kind IS NULL THEN
    RAISE EXCEPTION 'subject_risk_scope_invalid';
  END IF;
  IF p_kind='incident' THEN
    SELECT risk_metadata INTO saved FROM socai2.incidents WHERE tenant_id=p_tenant AND id=p_subject FOR UPDATE;
  ELSE
    SELECT risk_metadata INTO saved FROM socai2.cases WHERE tenant_id=p_tenant AND id=p_subject FOR UPDATE;
  END IF;
  IF NOT FOUND THEN RAISE EXCEPTION 'subject_risk_subject_missing'; END IF;
  IF saved IS NOT NULL THEN RETURN saved; END IF;
  IF p_policy IS NULL OR jsonb_typeof(p_policy)<>'object'
     OR p_policy->>'schema_version' IS DISTINCT FROM 'socai2.subject-risk-policy.v1'
     OR jsonb_typeof(p_policy->'version') IS DISTINCT FROM 'string'
     OR coalesce(btrim(p_policy->>'version'),'')=''
     OR NOT coalesce(p_policy->>'unknown_initial_severity'=ANY(levels),false)
     OR jsonb_typeof(p_policy->'priority_by_severity') IS DISTINCT FROM 'object' THEN
    RAISE EXCEPTION 'subject_risk_policy_invalid';
  END IF;
  IF (SELECT array_agg(key ORDER BY key) FROM jsonb_object_keys(p_policy) key)
       IS DISTINCT FROM ARRAY['priority_by_severity','schema_version','unknown_initial_severity','version']
     OR (SELECT array_agg(key ORDER BY key) FROM jsonb_object_keys(p_policy->'priority_by_severity') key)
       IS DISTINCT FROM ARRAY['critical','high','info','low','medium'] THEN
    RAISE EXCEPTION 'subject_risk_policy_invalid';
  END IF;
  FOR initial_level IN SELECT unnest(levels) LOOP
    IF jsonb_typeof(p_policy->'priority_by_severity'->initial_level) IS DISTINCT FROM 'number' THEN
      RAISE EXCEPTION 'subject_risk_priority_invalid';
    END IF;
    score := (p_policy->'priority_by_severity'->>initial_level)::numeric;
    IF score<0 OR score>100 OR score<>trunc(score) THEN RAISE EXCEPTION 'subject_risk_priority_invalid'; END IF;
  END LOOP;
  IF p_manual_level IS NOT NULL AND (p_kind<>'case' OR NOT p_manual_level=ANY(levels)
      OR p_actor IS NULL OR NOT EXISTS (SELECT FROM public.users WHERE tenant_id=p_tenant AND id=p_actor)) THEN
    RAISE EXCEPTION 'subject_risk_manual_creation_invalid';
  END IF;
  SELECT coalesce(jsonb_agg(jsonb_build_object('alert_id',a.id,'material_id',a.latest_material_id,
      'material_revision',m.revision,'severity',a.severity) ORDER BY a.id),'[]'::jsonb),
      levels[max(array_position(levels,a.severity))]
    INTO members, initial_level
    FROM socai2.alerts a LEFT JOIN socai2.alert_materials m
      ON m.tenant_id=a.tenant_id AND m.alert_id=a.id AND m.id=a.latest_material_id
    WHERE a.tenant_id=p_tenant AND a.id IN (
      SELECT alert_id FROM socai2.incident_alerts WHERE p_kind='incident' AND tenant_id=p_tenant AND incident_id=p_subject
      UNION ALL
      SELECT alert_id FROM socai2.case_alerts WHERE p_kind='case' AND tenant_id=p_tenant AND case_id=p_subject);
  initial_source := CASE WHEN initial_level IS NULL THEN 'initial_policy' ELSE 'member_max' END;
  initial_level := coalesce(initial_level,p_policy->>'unknown_initial_severity');
  effective := coalesce(p_manual_level,initial_level);
  source := CASE WHEN p_manual_level IS NOT NULL THEN 'manual' ELSE initial_source END;
  score := (p_policy->'priority_by_severity'->>effective)::numeric;
  now_at := clock_timestamp();
  result := jsonb_build_object('schema_version','socai2.subject-risk.v1','policy',p_policy,
    'initial',jsonb_build_object('level',initial_level,'source',initial_source,'members',members,
      'evaluated_at',now_at,'reason_code',CASE WHEN initial_source='member_max' THEN 'highest_known_member' ELSE 'source_severity_missing' END),
    'current',jsonb_build_object('level',effective,'source',source,'updated_at',now_at,'actor_id',CASE WHEN p_manual_level IS NULL THEN NULL ELSE p_actor END,
      'reason_code',CASE WHEN p_manual_level IS NOT NULL THEN 'explicit_creation_request' ELSE 'initial_rule' END),
    'system_priority',jsonb_build_object('value',score,'severity',effective,'computed_at',now_at,'mapping_version',p_policy->>'version'),
    'manual_severity_revision',CASE WHEN p_manual_level IS NULL THEN 0 ELSE 1 END);
  IF p_kind='incident' THEN
    UPDATE socai2.incidents SET severity=effective,severity_source=source,risk_metadata=result,
      priority_value=score,priority_state='available',priority_source='severity_mapping',priority_basis=result->'system_priority'
      WHERE tenant_id=p_tenant AND id=p_subject;
  ELSE
    UPDATE socai2.cases SET severity=effective,severity_source=source,risk_metadata=result,
      priority_value=score,priority_state='available',priority_source='severity_mapping',priority_basis=result->'system_priority'
      WHERE tenant_id=p_tenant AND id=p_subject;
  END IF;
  RETURN result;
END $$;
REVOKE ALL ON FUNCTION socai2.initialize_subject_risk(uuid,text,uuid,jsonb,text,uuid) FROM PUBLIC;
INSERT INTO public.aisoc_schema_migrations(name) VALUES ('132_socai2_subject_risk.sql') ON CONFLICT DO NOTHING;
