-- Run with a role allowed to read the selected tenant. Parameters are supplied
-- by the caller: psql -v tenant_id=<uuid> -v case_id=<uuid> -f this-file.sql
-- Read-only diagnostics; validated counts come from CasePageData, not raw JSON.
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT set_config('app.current_tenant_id', :'tenant_id', true);

-- Management values and the exact adopted judgment; never latest Run fallback.
SELECT c.id, c.row_version, c.classification, c.due_at, c.scope_revision,
       c.current_assessment_id, c.current_evidence_artifact_id,
       a.conclusion AS determination, a.origin, a.validity,
       a.formed_at, a.adopted_at, a.scope_revision AS assessment_scope_revision
FROM socai2.cases c
LEFT JOIN socai2.case_assessments a
  ON (a.tenant_id,a.case_id,a.id)=(c.tenant_id,c.id,c.current_assessment_id)
WHERE c.tenant_id=:'tenant_id'::uuid AND c.id=:'case_id'::uuid;

SELECT s.* FROM socai2.case_assessment_sources s
JOIN socai2.cases c ON (c.tenant_id,c.id,c.current_assessment_id)=(s.tenant_id,s.case_id,s.assessment_id)
WHERE c.tenant_id=:'tenant_id'::uuid AND c.id=:'case_id'::uuid ORDER BY s.id;

SELECT m.* FROM socai2.case_assessment_members m
JOIN socai2.cases c ON (c.tenant_id,c.id,c.current_assessment_id)=(m.tenant_id,m.case_id,m.assessment_id)
WHERE c.tenant_id=:'tenant_id'::uuid AND c.id=:'case_id'::uuid ORDER BY m.alert_id;

-- Both selected version and immutable history. SHA/source checks are performed
-- by the shared Python reader before producing evidence_count/threat_count.
SELECT f.id, f.id=c.current_evidence_artifact_id AS is_current,
       f.schema_version, f.captured_at, f.sha256, f.content_json
FROM socai2.artifacts f
JOIN socai2.cases c ON (c.tenant_id,c.id)=(f.tenant_id,f.case_id)
WHERE c.tenant_id=:'tenant_id'::uuid AND c.id=:'case_id'::uuid
  AND f.kind='case_evidence_index'
ORDER BY f.captured_at, f.id;

-- Exact source references and roles are in these original entries.
SELECT f.id AS index_id, entry->>'evidence_id' AS evidence_id,
       entry->'alert_ids' AS member_scope, entry->'object_keys' AS object_keys,
       entry->'source_refs' AS source_refs, entry->>'verdict' AS verdict,
       entry->'verdict_sources' AS verdict_sources, entry->'threat' AS threat,
       entry->'remediation' AS remediation, entry->>'state' AS state
FROM socai2.cases c
JOIN socai2.artifacts f ON (f.tenant_id,f.case_id,f.id)=(c.tenant_id,c.id,c.current_evidence_artifact_id)
CROSS JOIN LATERAL jsonb_array_elements(f.content_json->'entries') entry
WHERE c.tenant_id=:'tenant_id'::uuid AND c.id=:'case_id'::uuid;

-- Original Alert material is retained independently from the evidence index.
SELECT a.id AS alert_id, m.id AS material_id, m.revision, m.raw_json, m.ocsf_json,
       m.detection, m.source_scope, m.retention
FROM socai2.case_alerts ca
JOIN socai2.alerts a ON (a.tenant_id,a.id)=(ca.tenant_id,ca.alert_id)
JOIN socai2.alert_materials m ON (m.tenant_id,m.alert_id)=(a.tenant_id,a.id)
WHERE ca.tenant_id=:'tenant_id'::uuid AND ca.case_id=:'case_id'::uuid
ORDER BY a.id,m.revision;
ROLLBACK;
