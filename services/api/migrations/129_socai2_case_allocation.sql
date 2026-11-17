-- Additive Case allocation only; no legacy backfill and no Run mutation.
DO $preflight$
BEGIN
  IF current_database() IS DISTINCT FROM current_setting('socai2.migration.expected_database', true)
     OR NOT EXISTS (SELECT FROM public.aisoc_schema_migrations WHERE name='128_socai2_analysis_lifecycle.sql') THEN
    RAISE EXCEPTION 'case_allocation_migration_target_mismatch';
  END IF;
  PERFORM pg_advisory_xact_lock(hashtext('socai2'), hashtext('schema-initialization'));
END $preflight$;
ALTER TABLE socai2.cases ADD COLUMN IF NOT EXISTS continuation_root_case_id uuid,
  ADD COLUMN IF NOT EXISTS previous_case_id uuid, ADD COLUMN IF NOT EXISTS receiving_case_id uuid;
ALTER TABLE socai2.incidents ADD COLUMN IF NOT EXISTS active_case_id uuid;
DO $constraints$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_continuation_root_fk') THEN
    ALTER TABLE socai2.cases
      ADD CONSTRAINT cases_continuation_root_fk FOREIGN KEY (tenant_id,continuation_root_case_id) REFERENCES socai2.cases(tenant_id,id) DEFERRABLE INITIALLY DEFERRED,
      ADD CONSTRAINT cases_previous_fk FOREIGN KEY (tenant_id,previous_case_id) REFERENCES socai2.cases(tenant_id,id) DEFERRABLE INITIALLY DEFERRED,
      ADD CONSTRAINT cases_receiving_fk FOREIGN KEY (tenant_id,receiving_case_id) REFERENCES socai2.cases(tenant_id,id) DEFERRABLE INITIALLY DEFERRED;
    ALTER TABLE socai2.incidents ADD CONSTRAINT incidents_active_case_link_fk
      FOREIGN KEY (tenant_id,active_case_id,id) REFERENCES socai2.case_incidents(tenant_id,case_id,incident_id)
      DEFERRABLE INITIALLY DEFERRED;
  END IF;
END $constraints$;
CREATE INDEX IF NOT EXISTS cases_continuation_root ON socai2.cases(tenant_id,continuation_root_case_id);
CREATE INDEX IF NOT EXISTS cases_previous ON socai2.cases(tenant_id,previous_case_id);
CREATE INDEX IF NOT EXISTS incidents_active_case ON socai2.incidents(tenant_id,active_case_id);

CREATE OR REPLACE FUNCTION socai2.guard_case_continuation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP='UPDATE' AND (NEW.continuation_root_case_id IS DISTINCT FROM OLD.continuation_root_case_id
      OR NEW.previous_case_id IS DISTINCT FROM OLD.previous_case_id) THEN
    RAISE EXCEPTION 'case_continuation_identity_immutable' USING ERRCODE='23514';
  END IF;
  IF NEW.continuation_root_case_id IS NULL THEN
    IF NEW.previous_case_id IS NOT NULL OR NEW.receiving_case_id IS NOT NULL THEN
      RAISE EXCEPTION 'case_continuation_root_required' USING ERRCODE='23514';
    END IF;
  ELSIF NEW.continuation_root_case_id=NEW.id THEN
    IF NEW.previous_case_id IS NOT NULL OR NEW.receiving_case_id IS NULL THEN
      RAISE EXCEPTION 'case_continuation_root_invalid' USING ERRCODE='23514';
    END IF;
    IF NEW.receiving_case_id<>NEW.id AND NOT EXISTS (SELECT FROM socai2.cases c WHERE c.tenant_id=NEW.tenant_id
        AND c.id=NEW.receiving_case_id AND c.continuation_root_case_id=NEW.id) THEN
      RAISE EXCEPTION 'case_receiving_chain_mismatch' USING ERRCODE='23514';
    END IF;
  ELSE
    IF NEW.receiving_case_id IS NOT NULL OR NEW.previous_case_id IS NULL OR NEW.previous_case_id=NEW.id
        OR NOT EXISTS (SELECT FROM socai2.cases c WHERE c.tenant_id=NEW.tenant_id
          AND c.id=NEW.previous_case_id AND c.continuation_root_case_id=NEW.continuation_root_case_id)
        OR NOT EXISTS (SELECT FROM socai2.cases c WHERE c.tenant_id=NEW.tenant_id
          AND c.id=NEW.continuation_root_case_id AND c.continuation_root_case_id=c.id) THEN
      RAISE EXCEPTION 'case_continuation_predecessor_invalid' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS cases_continuation_guard ON socai2.cases;
CREATE TRIGGER cases_continuation_guard BEFORE INSERT OR UPDATE OF continuation_root_case_id,previous_case_id,receiving_case_id
  ON socai2.cases FOR EACH ROW EXECUTE FUNCTION socai2.guard_case_continuation();

CREATE TABLE IF NOT EXISTS socai2.case_alert_exclusions (
  tenant_id uuid NOT NULL REFERENCES public.tenants(id), case_id uuid NOT NULL, alert_id uuid NOT NULL,
  excluded_at timestamptz NOT NULL, excluded_by uuid REFERENCES public.users(id), operation_key uuid NOT NULL,
  PRIMARY KEY (tenant_id,case_id,alert_id),
  FOREIGN KEY (tenant_id,case_id) REFERENCES socai2.cases(tenant_id,id),
  FOREIGN KEY (tenant_id,alert_id) REFERENCES socai2.alerts(tenant_id,id)
);
ALTER TABLE socai2.case_alert_exclusions ENABLE ROW LEVEL SECURITY;
ALTER TABLE socai2.case_alert_exclusions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_scope ON socai2.case_alert_exclusions;
CREATE POLICY tenant_scope ON socai2.case_alert_exclusions USING (tenant_id=public.current_tenant_id())
  WITH CHECK (tenant_id=public.current_tenant_id());
INSERT INTO public.aisoc_schema_migrations(name) VALUES ('129_socai2_case_allocation.sql') ON CONFLICT (name) DO NOTHING;
