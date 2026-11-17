-- Functional access and base identity for the explicitly selected NEW candidate only.
\set ON_ERROR_STOP on
BEGIN;
SELECT current_database()=:'expected_database'
 AND current_database() <> 'aisoc'
 AND NOT EXISTS(SELECT FROM public.tenants)
 AND NOT EXISTS(SELECT FROM public.users)
 AND NOT EXISTS(SELECT FROM socai2.runs)
 AS candidate_empty \gset
\if :candidate_empty
REVOKE ALL ON SCHEMA socai2 FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA socai2 FROM PUBLIC;
SELECT EXISTS(SELECT FROM pg_roles WHERE rolname='aisoc_app') AS legacy_role_exists \gset
\if :legacy_role_exists
REVOKE ALL ON SCHEMA socai2 FROM aisoc_app;
REVOKE ALL ON ALL TABLES IN SCHEMA socai2 FROM aisoc_app;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA socai2 FROM aisoc_app;
\endif
GRANT CONNECT ON DATABASE :"expected_database" TO :"reader_role", :"analysis_writer_role";
GRANT USAGE ON SCHEMA public, socai2 TO :"reader_role", :"analysis_writer_role";
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA socai2 TO :"analysis_writer_role";
REVOKE UPDATE,DELETE ON socai2.alert_materials,socai2.alert_source_refs,socai2.alert_objects,
    socai2.alert_assessments,socai2.case_assessments,socai2.case_assessment_sources,
    socai2.case_assessment_members,socai2.artifacts,socai2.results,socai2.result_members,
    socai2.task_revisions,socai2.activities,socai2.activity_targets,socai2.response_links
    FROM :"analysis_writer_role";
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA socai2 TO :"analysis_writer_role";
GRANT SELECT ON public.tenants,public.users,public.api_keys,public.connectors,public.tenant_llm_credentials,
    public.assets,public.threat_intel_iocs,public.user_risk_profiles,public.insider_indicators,
    public.roles,public.permissions,public.role_permissions,public.user_roles,public.privilege_grants,
    public.permission_conditions,public.aisoc_kb_documents TO :"analysis_writer_role";
GRANT INSERT ON public.aisoc_kb_documents TO :"analysis_writer_role";
GRANT UPDATE(last_used_at) ON public.api_keys TO :"analysis_writer_role";
INSERT INTO public.tenants(id,name,slug,plan,is_active,settings,limits,created_at,updated_at)
VALUES (:'tenant_id'::uuid,:'candidate_id',:'candidate_id','test',true,'{}','{}',now(),now());
INSERT INTO public.users(id,tenant_id,email,username,hashed_password,role,is_active,is_verified,
                         preferences,created_at,updated_at)
VALUES (:'actor_id'::uuid,:'tenant_id'::uuid,:'actor_email',:'actor_name','!disabled',
        'analyst',true,true,'{}',now(),now());
COMMIT;
\else
ROLLBACK;
DO $failure$ BEGIN RAISE EXCEPTION 'candidate_identity_seed_requires_new_empty_target'; END $failure$;
\endif
