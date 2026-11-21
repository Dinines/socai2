-- Internal ingestion receipt only; frozen V1 alert/material/HTTP fields are unchanged.
DO $preflight$
BEGIN
  IF current_database() IS DISTINCT FROM current_setting('socai2.migration.expected_database', true)
     OR to_regclass('socai2.analysis_tasks') IS NULL THEN
    RAISE EXCEPTION 'lake_receipt_migration_target_mismatch';
  END IF;
  PERFORM pg_advisory_xact_lock(hashtext('socai2'), hashtext('schema-initialization'));
END $preflight$;

CREATE TABLE IF NOT EXISTS socai2.lake_alert_receipts (
  source_subject_id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES public.tenants(id),
  source_event_id text NOT NULL CHECK (btrim(source_event_id) <> ''),
  source_namespace text NOT NULL CHECK (btrim(source_namespace) <> ''),
  lake_database text NOT NULL CHECK (btrim(lake_database) <> ''),
  source_version text NOT NULL CHECK (btrim(source_version) <> ''),
  alert_id uuid NOT NULL, material_id uuid NOT NULL,
  lake_ref jsonb NOT NULL CHECK (jsonb_typeof(lake_ref)='object'),
  received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (tenant_id,alert_id),
  FOREIGN KEY (tenant_id,alert_id) REFERENCES socai2.alerts(tenant_id,id)
    DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (tenant_id,alert_id,material_id) REFERENCES socai2.alert_materials(tenant_id,alert_id,id)
    DEFERRABLE INITIALLY DEFERRED
);
COMMENT ON TABLE socai2.lake_alert_receipts IS
  'Committed immutable global source identity -> first alert/material and exact lake reference; not an analysis outcome';
ALTER TABLE socai2.lake_alert_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE socai2.lake_alert_receipts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_scope ON socai2.lake_alert_receipts;
CREATE POLICY tenant_scope ON socai2.lake_alert_receipts
  USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());
CREATE OR REPLACE FUNCTION socai2.reject_lake_receipt_mutation() RETURNS trigger
  LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable_lake_alert_receipt'; END $$;
DROP TRIGGER IF EXISTS lake_receipt_immutable ON socai2.lake_alert_receipts;
CREATE TRIGGER lake_receipt_immutable BEFORE UPDATE OR DELETE ON socai2.lake_alert_receipts
  FOR EACH ROW EXECUTE FUNCTION socai2.reject_lake_receipt_mutation();
INSERT INTO public.aisoc_schema_migrations(name) VALUES ('130_socai2_lake_alert_receipts.sql') ON CONFLICT DO NOTHING;
