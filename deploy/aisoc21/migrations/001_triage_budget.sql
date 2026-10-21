-- Project-local additive migration; the fixed 134 upstream migrations stay intact.
SET ROLE aisoc;
BEGIN;
CREATE TABLE socai2_triage_budget_reservations (
    run_id UUID PRIMARY KEY REFERENCES investigation_runs(id),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    policy_sha256 VARCHAR(64) NOT NULL,
    charged_tokens INTEGER NOT NULL CHECK (charged_tokens > 0),
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    request_started_at TIMESTAMPTZ,
    settled_at TIMESTAMPTZ,
    outcome VARCHAR(20) NOT NULL DEFAULT 'reserved'
        CHECK (outcome IN ('reserved', 'responded', 'no_request')),
    observed_tokens INTEGER CHECK (observed_tokens >= 0),
    CHECK ((outcome = 'reserved' AND settled_at IS NULL) OR
           (outcome <> 'reserved' AND settled_at IS NOT NULL)),
    CHECK (outcome <> 'responded' OR request_started_at IS NOT NULL)
);
CREATE INDEX socai2_triage_budget_window ON socai2_triage_budget_reservations(tenant_id, reserved_at);
CREATE INDEX socai2_triage_budget_unsettled ON socai2_triage_budget_reservations(tenant_id) WHERE settled_at IS NULL;
ALTER TABLE socai2_triage_budget_reservations ENABLE ROW LEVEL SECURITY;
ALTER TABLE socai2_triage_budget_reservations FORCE ROW LEVEL SECURITY;
CREATE POLICY socai2_triage_budget_tenant ON socai2_triage_budget_reservations
    USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
GRANT SELECT, INSERT, UPDATE ON socai2_triage_budget_reservations TO aisoc_app;
CREATE FUNCTION socai2_triage_budget_immutable() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'triage budget reservations cannot be deleted';
    END IF;
    IF ROW(NEW.run_id,NEW.tenant_id,NEW.policy_sha256,NEW.charged_tokens,NEW.reserved_at)
       IS DISTINCT FROM ROW(OLD.run_id,OLD.tenant_id,OLD.policy_sha256,OLD.charged_tokens,OLD.reserved_at)
       OR OLD.settled_at IS NOT NULL
       OR (OLD.request_started_at IS NOT NULL AND NEW.request_started_at IS DISTINCT FROM OLD.request_started_at) THEN
        RAISE EXCEPTION 'triage budget charge or settled result is immutable';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER socai2_triage_budget_immutable BEFORE UPDATE OR DELETE ON socai2_triage_budget_reservations
    FOR EACH ROW EXECUTE FUNCTION socai2_triage_budget_immutable();
COMMIT;
