-- Case membership changes maintain a real, not-yet-started baseline Run.
-- The Case row is locked by INSERT/UPDATE before this AFTER trigger runs.
-- Starting a baseline must take the same Case -> Run lock order.
ALTER TABLE investigation_runs ADD COLUMN IF NOT EXISTS investigation_kind VARCHAR(30);
ALTER TABLE investigation_runs ADD COLUMN IF NOT EXISTS scope_revision INTEGER NOT NULL DEFAULT 0;
ALTER TABLE investigation_runs ADD COLUMN IF NOT EXISTS scope_updated_at TIMESTAMPTZ;
ALTER TABLE investigation_runs ALTER COLUMN started_at DROP NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS investigation_one_pending_baseline
    ON investigation_runs (tenant_id, case_id)
    WHERE investigation_kind = 'baseline' AND status = 'pending_update';

-- Claiming is committed before execution begins. Even a future queued worker
-- must reserve the sole active slot before handing work to the executor.
CREATE UNIQUE INDEX IF NOT EXISTS investigation_one_active_baseline
    ON investigation_runs (tenant_id, case_id)
    WHERE investigation_kind = 'baseline'
      AND status IN ('queued', 'running', 'unknown', 'awaiting_human');

CREATE OR REPLACE FUNCTION maintain_case_pending_baseline()
RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE
    before_ids UUID[];
    after_ids UUID[];
    base_ids UUID[];
    added_ids UUID[];
    removed_ids UUID[];
    pending public.investigation_runs%ROWTYPE;
    baseline JSONB;
    stamp TIMESTAMPTZ := clock_timestamp();
BEGIN
    -- Unowned historical Cases cannot acquire a tenant-owned execution.
    IF NEW.tenant_id IS NULL THEN RETURN NEW; END IF;
    SELECT COALESCE(array_agg(DISTINCT x ORDER BY x), '{}'::UUID[])
      INTO after_ids FROM unnest(NEW.alert_ids) AS x WHERE x IS NOT NULL;
    IF TG_OP = 'INSERT' THEN
        before_ids := '{}'::UUID[];
    ELSE
        SELECT COALESCE(array_agg(DISTINCT x ORDER BY x), '{}'::UUID[])
          INTO before_ids FROM unnest(OLD.alert_ids) AS x WHERE x IS NOT NULL;
    END IF;
    IF before_ids = after_ids THEN RETURN NEW; END IF;

    SELECT * INTO pending FROM public.investigation_runs
      WHERE tenant_id = NEW.tenant_id AND case_id = NEW.id::TEXT
        AND investigation_kind = 'baseline' AND status = 'pending_update'
      FOR UPDATE;
    IF FOUND THEN
        SELECT COALESCE(array_agg(x::UUID ORDER BY x::UUID), '{}'::UUID[])
          INTO base_ids FROM jsonb_array_elements_text(
              pending.raw_alert->'baseline'->'initial_member_ids') AS x;
        baseline := pending.raw_alert->'baseline';
    ELSE
        base_ids := before_ids;
        baseline := jsonb_build_object(
            'schema', 'case.baseline.v1', 'initial_member_ids', to_jsonb(base_ids),
            'requested_at', stamp, 'trigger', CASE WHEN TG_OP = 'INSERT'
                THEN 'case_created' ELSE 'members_changed' END);
    END IF;
    SELECT COALESCE(array_agg(x ORDER BY x), '{}'::UUID[]) INTO added_ids
      FROM unnest(after_ids) AS x WHERE NOT (x = ANY(base_ids));
    SELECT COALESCE(array_agg(x ORDER BY x), '{}'::UUID[]) INTO removed_ids
      FROM unnest(base_ids) AS x WHERE NOT (x = ANY(after_ids));
    baseline := baseline || jsonb_build_object(
        'added_member_ids', to_jsonb(added_ids), 'removed_member_ids', to_jsonb(removed_ids),
        'updated_at', stamp);

    IF pending.id IS NULL THEN
        INSERT INTO public.investigation_runs
            (id, tenant_id, case_id, alert_summary, raw_alert, status,
             investigation_kind, scope_revision, scope_updated_at, started_at, created_at)
        VALUES (gen_random_uuid(), NEW.tenant_id, NEW.id::TEXT, NEW.title,
            jsonb_build_object('analysis_profile', 'case_analysis.v1', 'baseline', baseline,
                'scope', jsonb_build_object('all_member_ids', to_jsonb(after_ids),
                    'selected_member_ids', to_jsonb(after_ids), 'read_member_ids', '[]'::JSONB)),
            'pending_update', 'baseline', 1, stamp, NULL, stamp);
    ELSE
        UPDATE public.investigation_runs SET
            alert_summary = NEW.title,
            raw_alert = pending.raw_alert || jsonb_build_object('baseline', baseline,
                'scope', jsonb_build_object('all_member_ids', to_jsonb(after_ids),
                    'selected_member_ids', to_jsonb(after_ids), 'read_member_ids', '[]'::JSONB)),
            scope_revision = pending.scope_revision + 1, scope_updated_at = stamp
          WHERE id = pending.id AND tenant_id = NEW.tenant_id AND status = 'pending_update';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS case_pending_baseline ON aisoc_cases;
CREATE TRIGGER case_pending_baseline
    AFTER INSERT OR UPDATE OF alert_ids ON aisoc_cases
    FOR EACH ROW EXECUTE FUNCTION maintain_case_pending_baseline();

-- A started baseline's scope and provenance cannot be revised in place.
CREATE OR REPLACE FUNCTION freeze_started_baseline_scope()
RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
    IF OLD.investigation_kind = 'baseline' AND OLD.status <> 'pending_update' AND (
        NEW.status = 'pending_update' OR
        NEW.investigation_kind IS DISTINCT FROM OLD.investigation_kind OR
        NEW.tenant_id IS DISTINCT FROM OLD.tenant_id OR NEW.case_id IS DISTINCT FROM OLD.case_id OR
        NEW.scope_revision IS DISTINCT FROM OLD.scope_revision OR
        NEW.scope_updated_at IS DISTINCT FROM OLD.scope_updated_at OR
        NEW.raw_alert->'scope' IS DISTINCT FROM OLD.raw_alert->'scope' OR
        NEW.raw_alert->'baseline' IS DISTINCT FROM OLD.raw_alert->'baseline'
    ) THEN
        RAISE EXCEPTION 'started_baseline_scope_is_immutable';
    END IF;
    RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS started_baseline_scope_immutable ON investigation_runs;
CREATE TRIGGER started_baseline_scope_immutable BEFORE UPDATE ON investigation_runs
    FOR EACH ROW EXECUTE FUNCTION freeze_started_baseline_scope();
