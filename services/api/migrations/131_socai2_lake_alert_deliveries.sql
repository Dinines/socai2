-- Durable, ordered lake-to-alert work; no frozen V1 or public HTTP changes.
DO $preflight$
BEGIN
  IF current_database() IS DISTINCT FROM current_setting('socai2.migration.expected_database', true)
     OR to_regclass('socai2.lake_alert_receipts') IS NULL THEN
    RAISE EXCEPTION 'lake_delivery_migration_target_mismatch';
  END IF;
  PERFORM pg_advisory_xact_lock(hashtext('socai2'), hashtext('schema-initialization'));
END $preflight$;

CREATE TABLE IF NOT EXISTS socai2.lake_alert_deliveries (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES public.tenants(id),
  lake_database text NOT NULL,
  source_namespace text NOT NULL,
  mapping_version text NOT NULL,
  lake_ref jsonb NOT NULL CHECK (jsonb_typeof(lake_ref)='object'),
  binding_digest text NOT NULL,
  decision jsonb NOT NULL CHECK (jsonb_typeof(decision)='object'),
  source_subject_id uuid,
  state text NOT NULL CHECK (state IN ('pending','receiving','failed','unknown','held','delivered','lake_only','review')),
  reason text,
  attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count>=0),
  alert_id uuid,
  material_id uuid,
  confirmed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (tenant_id,id),
  FOREIGN KEY (tenant_id,alert_id,material_id) REFERENCES socai2.alert_materials(tenant_id,alert_id,id),
  CHECK ((state='delivered')=(confirmed_at IS NOT NULL)),
  CHECK ((state='delivered')=(alert_id IS NOT NULL AND material_id IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS lake_alert_delivery_head ON socai2.lake_alert_deliveries
  (tenant_id,lake_database,source_namespace,mapping_version,created_at,id)
  WHERE state IN ('pending','receiving','failed','unknown','held');

CREATE TABLE IF NOT EXISTS socai2.lake_alert_delivery_attempts (
  tenant_id uuid NOT NULL,
  delivery_id uuid NOT NULL,
  attempt_no integer NOT NULL CHECK (attempt_no>0),
  started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  ended_at timestamptz,
  outcome text NOT NULL CHECK (outcome IN ('receiving','created','duplicate','recovered','failed','unknown','held')),
  reason text,
  receipt jsonb CHECK (receipt IS NULL OR jsonb_typeof(receipt)='object'),
  PRIMARY KEY (delivery_id,attempt_no),
  FOREIGN KEY (tenant_id,delivery_id) REFERENCES socai2.lake_alert_deliveries(tenant_id,id),
  CHECK ((outcome='receiving')=(ended_at IS NULL))
);

ALTER TABLE socai2.lake_alert_deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE socai2.lake_alert_deliveries FORCE ROW LEVEL SECURITY;
ALTER TABLE socai2.lake_alert_delivery_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE socai2.lake_alert_delivery_attempts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_scope ON socai2.lake_alert_deliveries;
CREATE POLICY tenant_scope ON socai2.lake_alert_deliveries
  USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());
DROP POLICY IF EXISTS tenant_scope ON socai2.lake_alert_delivery_attempts;
CREATE POLICY tenant_scope ON socai2.lake_alert_delivery_attempts
  USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

CREATE OR REPLACE FUNCTION socai2.guard_lake_delivery() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP='DELETE' THEN RAISE EXCEPTION 'lake_delivery_history_required'; END IF;
  IF TG_OP='UPDATE' AND (OLD.state='delivered' OR
     ROW(NEW.id,NEW.tenant_id,NEW.lake_database,NEW.source_namespace,NEW.mapping_version,NEW.lake_ref,
         NEW.binding_digest,NEW.decision,NEW.source_subject_id,NEW.created_at) IS DISTINCT FROM
     ROW(OLD.id,OLD.tenant_id,OLD.lake_database,OLD.source_namespace,OLD.mapping_version,OLD.lake_ref,
         OLD.binding_digest,OLD.decision,OLD.source_subject_id,OLD.created_at)) THEN
    RAISE EXCEPTION 'lake_delivery_identity_or_confirmation_immutable';
  END IF;
  IF NEW.state='delivered' AND NOT EXISTS (
    SELECT FROM socai2.lake_alert_receipts r
      WHERE r.tenant_id=NEW.tenant_id AND r.source_subject_id=NEW.source_subject_id
        AND r.lake_database=NEW.lake_database AND r.source_namespace=NEW.source_namespace
        AND r.source_version=NEW.lake_ref->>'source_version'
        AND r.alert_id=NEW.alert_id AND r.material_id=NEW.material_id
  ) THEN RAISE EXCEPTION 'lake_delivery_requires_committed_receipt'; END IF;
  RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS lake_delivery_guard ON socai2.lake_alert_deliveries;
CREATE TRIGGER lake_delivery_guard BEFORE INSERT OR UPDATE OR DELETE ON socai2.lake_alert_deliveries
  FOR EACH ROW EXECUTE FUNCTION socai2.guard_lake_delivery();

CREATE OR REPLACE FUNCTION socai2.guard_lake_delivery_attempt() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP='DELETE' THEN RAISE EXCEPTION 'lake_delivery_attempt_history_required'; END IF;
  IF TG_OP='UPDATE' AND (OLD.ended_at IS NOT NULL OR
      ROW(NEW.tenant_id,NEW.delivery_id,NEW.attempt_no,NEW.started_at) IS DISTINCT FROM
      ROW(OLD.tenant_id,OLD.delivery_id,OLD.attempt_no,OLD.started_at)) THEN
    RAISE EXCEPTION 'lake_delivery_attempt_immutable';
  END IF;
  RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS lake_delivery_attempt_guard ON socai2.lake_alert_delivery_attempts;
CREATE TRIGGER lake_delivery_attempt_guard BEFORE UPDATE OR DELETE ON socai2.lake_alert_delivery_attempts
  FOR EACH ROW EXECUTE FUNCTION socai2.guard_lake_delivery_attempt();
INSERT INTO public.aisoc_schema_migrations(name) VALUES ('131_socai2_lake_alert_deliveries.sql') ON CONFLICT DO NOTHING;
