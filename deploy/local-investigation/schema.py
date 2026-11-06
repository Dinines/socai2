"""Generate only the public dependencies and current socai2 migrations."""
import os
import sys

from config import API_ROLE, DATABASE, FUSION_ROLE, LAKE, ROOT

SUPPORT_TABLES = {"tenants", "users", "api_keys", "connectors", "tenant_llm_credentials", "assets", "threat_intel_iocs",
    "user_risk_profiles", "insider_indicators", "roles", "permissions", "role_permissions", "user_roles",
    "privilege_grants", "permission_conditions"}
CONTEXT_TABLES = {"assets", "threat_intel_iocs", "user_risk_profiles", "insider_indicators", "aisoc_kb_documents",
                  "connectors", "tenant_llm_credentials"}
HISTORY_TABLES = {"alert_materials", "alert_source_refs", "alert_objects", "alert_assessments", "case_assessments",
    "case_assessment_sources", "case_assessment_members", "artifacts", "results", "result_members", "task_revisions",
    "activities", "activity_targets", "response_links"}
FUSION_TABLES = {"alerts", "alert_materials", "alert_source_refs", "alert_objects", "artifacts", "incidents", "incident_alerts"}
MIGRATIONS = ["123_socai2_page_data_model.sql", "124_socai2_case_source_binding.sql", "125_socai2_baseline_input_freshness.sql", "126_socai2_case_page_data.sql"]


def support_schema():
    sys.path.insert(0, str(ROOT / "services/api"))
    # Avoid discovering an unrelated workspace .env when importing metadata.
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://metadata:metadata@127.0.0.1:1/metadata"
    import app.models.enterprise_iam
    import app.models.rbac  # noqa: F401 -- register required tables only
    from app.models import Base
    from sqlalchemy.dialects.postgresql import dialect
    from sqlalchemy.schema import CreateIndex, CreateTable, sort_tables
    tables = [Base.metadata.tables[name] for name in sorted(SUPPORT_TABLES)]
    assert all(fk.column.table.name in SUPPORT_TABLES for t in tables for fk in t.foreign_keys)
    ddl = ["BEGIN;", "CREATE EXTENSION IF NOT EXISTS pgcrypto;",
        "CREATE TABLE IF NOT EXISTS public.aisoc_schema_migrations(name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());",
        "CREATE OR REPLACE FUNCTION public.current_tenant_id() RETURNS uuid LANGUAGE sql STABLE AS $$ SELECT nullif(current_setting('app.current_tenant_id',true),'')::uuid $$;"]
    for table in sort_tables(tables):
        ddl.append(str(CreateTable(table, if_not_exists=True).compile(dialect=dialect())) + ";")
        ddl.extend(str(CreateIndex(i, if_not_exists=True).compile(dialect=dialect())) + ";" for i in sorted(table.indexes, key=lambda i: i.name))
    ddl.append((ROOT / "services/api/migrations/016_knowledge_base.sql").read_text())
    return "\n".join([*ddl, "COMMIT;"])


def grants_schema():
    statements = ["REVOKE CREATE ON SCHEMA public FROM PUBLIC;",
        "REVOKE ALL ON SCHEMA socai2 FROM PUBLIC;", "REVOKE ALL ON ALL FUNCTIONS IN SCHEMA socai2 FROM PUBLIC;"]
    for role in (API_ROLE, FUSION_ROLE):
        statements.extend([f"GRANT CONNECT ON DATABASE {DATABASE} TO {role};",
            f"GRANT USAGE ON SCHEMA public,socai2 TO {role};",
            f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA socai2 TO {role};"])
    statements.extend([f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {API_ROLE};",
        f"GRANT UPDATE(last_used_at) ON public.api_keys TO {API_ROLE};",
        f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA socai2 TO {API_ROLE};"])
    for name in sorted(HISTORY_TABLES):
        statements.append(f"REVOKE UPDATE,DELETE ON socai2.{name} FROM {API_ROLE};")
    statements.append(f"GRANT SELECT(id,tenant_id) ON public.connectors TO {FUSION_ROLE};")
    for name in sorted(FUSION_TABLES):
        statements.append(f"GRANT SELECT,INSERT ON socai2.{name} TO {FUSION_ROLE};")
    statements.extend([
        f"GRANT UPDATE(latest_material_id,source_updated_at,business_updated_at,row_version,first_seen_at,last_seen_at) ON socai2.alerts TO {FUSION_ROLE};",
        f"GRANT UPDATE(business_updated_at,row_version) ON socai2.incidents TO {FUSION_ROLE};",
    ])
    for name in sorted(CONTEXT_TABLES):
        statements.extend([f"ALTER TABLE public.{name} ENABLE ROW LEVEL SECURITY;",
            f"ALTER TABLE public.{name} FORCE ROW LEVEL SECURITY;", f"DROP POLICY IF EXISTS local_tenant_scope ON public.{name};",
            f"CREATE POLICY local_tenant_scope ON public.{name} USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());"])
    return "\n".join(["BEGIN;", *statements, "COMMIT;"])


def lake_schema():
    source = (ROOT / "services/api/clickhouse/001_init.sql").read_text()
    start = source.index("CREATE TABLE IF NOT EXISTS aisoc.raw_events")
    marker = "SETTINGS index_granularity = 8192;"
    end = source.index(marker, start) + len(marker)
    return "CREATE DATABASE IF NOT EXISTS " + LAKE + ";\n" + source[start:end].replace("aisoc.raw_events", LAKE + ".raw_events")
