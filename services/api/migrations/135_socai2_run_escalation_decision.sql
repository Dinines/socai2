-- Record the decision made by a completed automatic alert triage Run.
DO $preflight$
BEGIN
  IF current_database() IS DISTINCT FROM current_setting('socai2.migration.expected_database', true)
     OR to_regclass('public.aisoc_schema_migrations') IS NULL THEN
    RAISE EXCEPTION 'run_escalation_decision_migration_target_mismatch';
  END IF;
  PERFORM pg_advisory_xact_lock(hashtext('socai2'), hashtext('schema-initialization'));
  IF NOT EXISTS (SELECT FROM public.aisoc_schema_migrations WHERE name='134_socai2_business_verdict.sql') THEN
    RAISE EXCEPTION 'run_escalation_decision_migration_baseline_missing';
  END IF;
END $preflight$;

ALTER TABLE socai2.runs ADD COLUMN IF NOT EXISTS escalation_decision text;

DO $constraints$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_constraint WHERE conrelid='socai2.runs'::regclass
                 AND conname='runs_escalation_decision') THEN
    ALTER TABLE socai2.runs ADD CONSTRAINT runs_escalation_decision CHECK (
      escalation_decision IS NULL OR (escalation_decision='not_escalated' AND kind='alert_basic'
        AND state='completed' AND delivery_state='complete' AND requested_by IS NULL));
  END IF;
END $constraints$;

-- Allow the decision in the terminal update while retaining the frozen-input
-- and immutable-terminal-run checks from the original guard.
CREATE OR REPLACE FUNCTION socai2.guard_run() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
DECLARE current_scope bigint;
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'run history cannot be deleted' USING ERRCODE='23514';
 END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.kind='baseline' AND NEW.state<>'pending_update' THEN
   RAISE EXCEPTION 'baseline must be created pending, then claimed atomically' USING ERRCODE='23514';
  END IF;
 ELSE
  IF ROW(NEW.id,NEW.tenant_id,NEW.kind,NEW.case_id,NEW.alert_id,NEW.incident_id)
     IS DISTINCT FROM ROW(OLD.id,OLD.tenant_id,OLD.kind,OLD.case_id,OLD.alert_id,OLD.incident_id) THEN
   RAISE EXCEPTION 'run identity and parent are immutable' USING ERRCODE='23514';
  END IF;
  IF OLD.state IN ('completed','failed','cancelled') THEN
   RAISE EXCEPTION 'terminal run is immutable' USING ERRCODE='23514';
  END IF;
  IF OLD.state='pending_update' AND NEW.state NOT IN ('pending_update','running','cancelled')
     OR OLD.state='running' AND NEW.state NOT IN ('running','unknown','completed','failed','cancelled')
     OR OLD.state='unknown' AND NEW.state NOT IN ('unknown','completed','failed','cancelled') THEN
   RAISE EXCEPTION 'invalid run state transition' USING ERRCODE='23514';
  END IF;
  IF OLD.state<>'pending_update' AND
     (to_jsonb(NEW)-ARRAY['state','ended_at','stop_reason','stop_detail',
                            'delivery_state','escalation_decision','row_version'])
      IS DISTINCT FROM
     (to_jsonb(OLD)-ARRAY['state','ended_at','stop_reason','stop_detail',
                            'delivery_state','escalation_decision','row_version']) THEN
   RAISE EXCEPTION 'claimed run input is frozen' USING ERRCODE='23514';
  END IF;
 END IF;
 IF NEW.kind='baseline' AND NEW.state='running' AND TG_OP='UPDATE' AND OLD.state='pending_update' THEN
  -- API acquires Case then Run before this UPDATE; this lock also protects direct SQL writers.
  SELECT scope_revision INTO current_scope FROM socai2.cases
   WHERE tenant_id=NEW.tenant_id AND id=NEW.case_id FOR UPDATE;
  IF NOT FOUND OR current_scope<>NEW.scope_revision THEN
   RAISE EXCEPTION 'case scope changed before claim' USING ERRCODE='23514';
  END IF;
  IF NOT EXISTS(SELECT 1 FROM socai2.run_members WHERE tenant_id=NEW.tenant_id AND run_id=NEW.id) THEN
   RAISE EXCEPTION 'cannot claim empty baseline' USING ERRCODE='23514';
  END IF;
  IF EXISTS(
   (SELECT alert_id FROM socai2.case_alerts WHERE tenant_id=NEW.tenant_id AND case_id=NEW.case_id
    EXCEPT SELECT alert_id FROM socai2.run_members WHERE tenant_id=NEW.tenant_id AND run_id=NEW.id)
   UNION ALL
   (SELECT alert_id FROM socai2.run_members WHERE tenant_id=NEW.tenant_id AND run_id=NEW.id
    EXCEPT SELECT alert_id FROM socai2.case_alerts WHERE tenant_id=NEW.tenant_id AND case_id=NEW.case_id)
  ) THEN RAISE EXCEPTION 'baseline must cover complete current case' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $fn$;

INSERT INTO public.aisoc_schema_migrations(name)
VALUES ('135_socai2_run_escalation_decision.sql') ON CONFLICT (name) DO NOTHING;
