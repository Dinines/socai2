-- F4: persist member selection and Case change receipt in one transaction.
CREATE TABLE IF NOT EXISTS investigation_case_links (
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    operation_key UUID NOT NULL,
    link_id UUID NOT NULL UNIQUE,
    case_id UUID NOT NULL REFERENCES aisoc_cases(id),
    selected_member_ids UUID[] NOT NULL,
    source_incident_ids UUID[] NOT NULL,
    intent JSONB NOT NULL,
    receipt JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, operation_key)
);
CREATE INDEX IF NOT EXISTS investigation_case_links_history
    ON investigation_case_links (tenant_id, created_at DESC, link_id DESC);
CREATE INDEX IF NOT EXISTS investigation_case_links_incidents
    ON investigation_case_links USING GIN (source_incident_ids);
CREATE INDEX IF NOT EXISTS investigation_case_links_alerts
    ON investigation_case_links USING GIN (selected_member_ids);

ALTER TABLE investigation_case_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE investigation_case_links FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON investigation_case_links;
CREATE POLICY tenant_isolation ON investigation_case_links
    USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aisoc_app') THEN
        GRANT SELECT, INSERT ON investigation_case_links TO aisoc_app;
    END IF;
END $$;
