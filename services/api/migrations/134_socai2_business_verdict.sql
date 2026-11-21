-- SF04: nullable model verdict on the original diagnosis and Case Result.
DO $preflight$
BEGIN
  IF current_database() IS DISTINCT FROM current_setting('socai2.migration.expected_database', true)
     OR to_regclass('public.aisoc_schema_migrations') IS NULL THEN
    RAISE EXCEPTION 'business_verdict_migration_target_mismatch';
  END IF;
  PERFORM pg_advisory_xact_lock(hashtext('socai2'), hashtext('schema-initialization'));
  IF NOT EXISTS (SELECT FROM public.aisoc_schema_migrations WHERE name='126_socai2_case_page_data.sql') THEN
    RAISE EXCEPTION 'business_verdict_migration_baseline_missing';
  END IF;
END $preflight$;

ALTER TABLE socai2.incident_diagnoses ADD COLUMN IF NOT EXISTS business_verdict text;
ALTER TABLE socai2.results ADD COLUMN IF NOT EXISTS business_verdict text;

DO $constraints$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_constraint WHERE conrelid='socai2.incident_diagnoses'::regclass
                 AND conname='incident_diagnoses_business_verdict') THEN
    ALTER TABLE socai2.incident_diagnoses ADD CONSTRAINT incident_diagnoses_business_verdict CHECK (
      business_verdict IS NULL OR (business_verdict IN ('malicious','benign','false_positive','needs_review')
        AND state='completed' AND (diagnosis->>'validation_state') IS NOT DISTINCT FROM 'accepted'));
  END IF;
  IF NOT EXISTS (SELECT FROM pg_constraint WHERE conrelid='socai2.results'::regclass
                 AND conname='results_business_verdict') THEN
    ALTER TABLE socai2.results ADD CONSTRAINT results_business_verdict CHECK (
      business_verdict IS NULL OR (business_verdict IN ('malicious','benign','false_positive','needs_review')
        AND kind='baseline' AND conclusion_origin='model' AND validation_state='accepted'
        AND conclusion_state IN ('supported','uncertain')));
  END IF;
END $constraints$;

INSERT INTO public.aisoc_schema_migrations(name) VALUES ('134_socai2_business_verdict.sql') ON CONFLICT (name) DO NOTHING;
