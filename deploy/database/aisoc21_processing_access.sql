-- Installed exactly once in the same transaction as the approved V1 schema.
-- Existing application identities do not gain access to the new investigation records.
REVOKE ALL ON SCHEMA socai2 FROM aisoc_app, PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA socai2 FROM aisoc_app, PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA socai2 FROM aisoc_app, PUBLIC;
GRANT CONNECT ON DATABASE aisoc TO socai2_prod_processor, socai2_prod_reader, socai2_prod_ingress;
GRANT USAGE ON SCHEMA socai2 TO socai2_prod_processor, socai2_prod_reader, socai2_prod_ingress;
GRANT SELECT ON ALL TABLES IN SCHEMA socai2 TO socai2_prod_reader;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA socai2 TO socai2_prod_processor;
REVOKE UPDATE,DELETE ON socai2.alert_materials,socai2.alert_source_refs,socai2.alert_objects,
    socai2.alert_assessments,socai2.case_assessments,socai2.case_assessment_sources,
    socai2.case_assessment_members,socai2.artifacts,socai2.results,socai2.result_members,
    socai2.task_revisions,socai2.activities,socai2.activity_targets,socai2.response_links
    FROM socai2_prod_processor;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA socai2 TO socai2_prod_processor;
GRANT SELECT ON public.tenants,public.users,public.api_keys,public.connectors,public.tenant_llm_credentials,
    public.assets,public.threat_intel_iocs,public.user_risk_profiles,public.insider_indicators,
    public.roles,public.permissions,public.role_permissions,public.user_roles,public.privilege_grants,
    public.permission_conditions,public.aisoc_kb_documents TO socai2_prod_processor;
GRANT UPDATE(last_used_at) ON public.api_keys TO socai2_prod_processor;
GRANT SELECT(id,tenant_id) ON public.connectors TO socai2_prod_ingress;
GRANT SELECT,INSERT ON socai2.alerts,socai2.alert_materials,socai2.alert_source_refs,socai2.alert_objects,
    socai2.artifacts,socai2.incidents,socai2.incident_alerts TO socai2_prod_ingress;
GRANT UPDATE(latest_material_id,source_updated_at,business_updated_at,row_version,first_seen_at,last_seen_at)
    ON socai2.alerts TO socai2_prod_ingress;
GRANT UPDATE(business_updated_at,row_version) ON socai2.incidents TO socai2_prod_ingress;

CREATE SCHEMA socai2_ops AUTHORIZATION aisoc;
REVOKE ALL ON SCHEMA socai2_ops FROM PUBLIC;
CREATE FUNCTION socai2_ops.prod_alert_sources(p_tenant uuid,p_subject uuid,p_by_incident boolean)
RETURNS TABLE(id uuid,tenant_id uuid,source_incident_id text,snapshot jsonb)
LANGUAGE sql STABLE STRICT SECURITY DEFINER SET search_path=pg_catalog AS $source$
    SELECT a.id,a.tenant_id,a.enrichment_data#>>'{socai2_fusion,incident_id}',
           a.enrichment_data#>'{socai2_fusion,delivery_snapshot}'
    FROM public.alerts AS a
    WHERE p_tenant=public.current_tenant_id() AND a.tenant_id=p_tenant
      AND CASE WHEN p_by_incident THEN a.enrichment_data#>>'{socai2_fusion,incident_id}'=p_subject::text
               ELSE a.id=p_subject END
$source$;
REVOKE ALL ON FUNCTION socai2_ops.prod_alert_sources(uuid,uuid,boolean) FROM PUBLIC;
GRANT USAGE ON SCHEMA socai2_ops TO socai2_prod_ingress;
GRANT EXECUTE ON FUNCTION socai2_ops.prod_alert_sources(uuid,uuid,boolean) TO socai2_prod_ingress;
