-- F2: incident overview text is independent of live Alert/triage data.
CREATE TABLE IF NOT EXISTS fusion_incident_summaries (
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    incident_id UUID NOT NULL,
    summary_text TEXT,
    generated_at TIMESTAMPTZ,
    source_updated_at TIMESTAMPTZ,
    source_fingerprint VARCHAR(64),
    source_refs JSONB,
    model VARCHAR(200),
    last_attempt_at TIMESTAMPTZ,
    last_error VARCHAR(80),
    last_usage JSONB,
    PRIMARY KEY (tenant_id, incident_id)
);

ALTER TABLE fusion_incident_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE fusion_incident_summaries FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON fusion_incident_summaries;
CREATE POLICY tenant_isolation ON fusion_incident_summaries
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aisoc_app') THEN
        GRANT SELECT, INSERT, UPDATE ON fusion_incident_summaries TO aisoc_app;
    END IF;
END $$;
