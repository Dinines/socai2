-- Additive page data only. Existing results, materials and migrations stay intact.
BEGIN;
ALTER TABLE socai2.cases ADD COLUMN IF NOT EXISTS classification text;
ALTER TABLE socai2.cases ADD COLUMN IF NOT EXISTS due_at timestamptz;
ALTER TABLE socai2.cases ADD COLUMN IF NOT EXISTS current_evidence_artifact_id uuid;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_classification_enum') THEN
  ALTER TABLE socai2.cases ADD CONSTRAINT cases_classification_enum
   CHECK (classification IN ('true_positive','informational','false_positive'));
 END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_current_evidence_scope_fk') THEN
  ALTER TABLE socai2.cases ADD CONSTRAINT cases_current_evidence_scope_fk
   FOREIGN KEY(tenant_id,id,current_evidence_artifact_id)
   REFERENCES socai2.artifacts(tenant_id,case_id,id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $$;
ALTER TABLE socai2.artifacts DROP CONSTRAINT artifacts_kind_enum;
ALTER TABLE socai2.artifacts ADD CONSTRAINT artifacts_kind_enum CHECK (kind IN
 ('input_snapshot','model_request','model_response','tool_request','tool_response',
  'domain_analysis','deep_analysis','attack_chain','attack_path','alert_graph',
  'report_json','report_markdown','attachment','source_snapshot','handoff','query_plan',
  'alert_explanation','case_evidence_index'));
CREATE OR REPLACE FUNCTION socai2.check_case_evidence_pointer() RETURNS trigger
 LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.current_evidence_artifact_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM socai2.artifacts a WHERE a.tenant_id=NEW.tenant_id AND a.case_id=NEW.id
   AND a.id=NEW.current_evidence_artifact_id AND a.kind='case_evidence_index'
   AND a.schema_version='socai2.case-evidence.v1' AND jsonb_typeof(a.content_json)='object'
 ) THEN RAISE EXCEPTION 'case_evidence_pointer_invalid' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS cases_evidence_pointer ON socai2.cases;
CREATE CONSTRAINT TRIGGER cases_evidence_pointer
 AFTER INSERT OR UPDATE ON socai2.cases DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION socai2.check_case_evidence_pointer();
COMMENT ON COLUMN socai2.cases.classification IS 'Explicit Case management classification; NULL means not set';
COMMENT ON COLUMN socai2.cases.due_at IS 'Optional Case deadline; independent of tasks and execution budgets';
COMMENT ON COLUMN socai2.cases.current_evidence_artifact_id IS 'Selected immutable case_evidence_index; NULL means not recorded';
COMMIT;
