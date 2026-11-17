"""Meaningful deployment checks. Set SOCAI2_READER_TEST_CONFIG for isolated PG tests."""

import json
import os
import subprocess
from pathlib import Path

import install_reader
import pytest


def test_one_increment_is_shared_by_new_and_existing_installs():
    increment = install_reader.render("reader_public_lookups_20261107.sql")
    for entry in ("init_socai2_v1_2_reader.sql", "upgrade_socai2_v1_2_reader.sql"):
        body = install_reader.render(entry)
        assert body.count(increment) == 1
        assert "reader_freshness_target_mismatch" in body
        assert "verified_socai2_v1_2_reader" in body
    with pytest.raises(ValueError, match="invalid_sql_include"):
        install_reader.render("../../secret.sql")


def test_password_profile_runs_without_inherited_certificate_configuration(monkeypatch):
    from types import SimpleNamespace
    cfg = install_reader.load_profile(install_reader.HERE / "reader-install.example.toml")
    assert cfg["environment"]["PGSSLMODE"] == "require"
    monkeypatch.setenv("PGSSLROOTCERT", "/missing/old-ca.crt")
    monkeypatch.setenv("PGSSLCERT", "/missing/old-client.crt")
    monkeypatch.setenv("PGSSLKEY", "/missing/old-client.key")
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(install_reader.subprocess, "run", run)
    assert install_reader.execute(cfg, "verify").returncode == 0
    command, kwargs = calls[0]
    assert command[command.index("-d") + 1] == cfg["database"]
    assert kwargs["env"]["PGSSLMODE"] == "require"
    assert not {"PGSSLROOTCERT", "PGSSLCERT", "PGSSLKEY"} & kwargs["env"].keys()


@pytest.mark.parametrize("change", [{"environment": {}}, {"transport": ""}, {"psql_argv": ["psql"]}])
def test_missing_connection_never_uses_libpq_defaults(tmp_path, change):
    import tomllib
    raw = tomllib.loads((install_reader.HERE / "reader-install.example.toml").read_text())
    raw.update(change)
    path = tmp_path / "profile.toml"
    sections = {"environment", "cleanup", "analysis", "analysis_ingress"}
    body = "\n".join(f"{k} = {json.dumps(v)}" for k, v in raw.items() if k not in sections)
    for key in sections:
        if key in raw:
            body += f"\n[{key}]\n" + "\n".join(f"{k} = {json.dumps(v)}" for k, v in raw[key].items())
    path.write_text(body)
    with pytest.raises(ValueError):
        install_reader.load_profile(path)


def test_lifecycle_new_and_upgrade_share_guarded_increment():
    increment = install_reader.render(install_reader.ANALYSIS_MIGRATION)
    for entry in ("analysis_lifecycle.sql", "init_socai2_current.sql", "init_socai2_current_reader.sql"):
        body = install_reader.render(entry)
        assert body.count(increment) == 1
        assert "socai2.migration.expected_database" in body
        assert ":'analysis_lock_timeout'" in body and ":'analysis_statement_timeout'" in body
    cfg = install_reader.load_profile(install_reader.HERE / "reader-install.example.toml")
    cfg.pop("analysis")
    with pytest.raises(ValueError, match="analysis_migration_configuration_required"):
        install_reader.execute(cfg, "analysis-lifecycle")


def test_initial_task_ingress_requires_explicit_role_and_same_new_install_grants():
    grants = install_reader.render("analysis_ingress_access.sql")
    assert install_reader.render("init_socai2_current_reader.sql").count(grants) == 1
    assert "GRANT SELECT,INSERT ON socai2.analysis_tasks,socai2.analysis_subject_state" in grants
    cfg = install_reader.load_profile(install_reader.HERE / "reader-install.example.toml")
    cfg.pop("analysis_ingress")
    with pytest.raises(ValueError, match="analysis_ingress_configuration_required"):
        install_reader.execute(cfg, "analysis-ingress")


def test_native_fusion_support_preserves_source_tables_without_legacy_alert_store():
    sql = install_reader.render(install_reader.ENTRIES["fusion-support"])
    sources = install_reader.HERE.parent.parent / "services/api/migrations"
    assert (sources / "053_dead_letters.sql").read_text() in sql
    assert (sources / "110_ai_assets.sql").read_text().split("DO $$")[0] in sql
    sessions = (sources / "102_sessions.sql").read_text()
    assert sessions.split("-- The alert side. Additive:")[0] in sql
    policy = sessions[sessions.index("-- Written out rather than looped"):]
    policy = policy[:policy.index("    IF EXISTS")] + "END\n$$;\n"
    assert policy in sql
    assert "aisoc_app" not in sql
    assert "REVOKE" not in sql
    assert "ALTER TABLE alerts" not in sql
    assert "CREATE TABLE IF NOT EXISTS alerts" not in sql
    assert "fusion_support_target_invalid" in sql
    cfg = install_reader.load_profile(install_reader.HERE / "reader-install.example.toml")
    cfg.pop("analysis_ingress")
    with pytest.raises(ValueError, match="analysis_ingress_configuration_required"):
        install_reader.execute(cfg, "fusion-support")


@pytest.fixture(scope="module")
def config():
    path = os.environ.get("SOCAI2_READER_TEST_CONFIG")
    if not path:
        pytest.skip("explicit isolated PG profile required")
    return json.loads(Path(path).read_text())


def profile(cfg, database):
    return {"database": database, "admin_role": cfg["admin"], "function_owner": cfg["owner"],
            "reader_role": cfg["reader"], "timeout_seconds": cfg["timeout_seconds"],
            "transport": "docker_socket",
            "psql_argv": [cfg["docker"], "--context", cfg["docker_context"], "exec", "-i", cfg["container"], "psql", "-XwAtq"], "environment": {}}


def sql(cfg, db, body, *, expected=0):
    result = subprocess.run([cfg["docker"], "--context", cfg["docker_context"], "exec", "-i", cfg["container"], "psql", "-XwAtq",
                             "-U", cfg["admin"], "-d", db, "-v", "ON_ERROR_STOP=1"],
                            input=body, capture_output=True, text=True, timeout=cfg["timeout_seconds"], check=False)
    assert (result.returncode == 0) == (expected == 0), result.stderr
    return result


@pytest.fixture(scope="module")
def installed(config):
    cfg = config
    role, owner = cfg["reader"], cfg["owner"]
    # Identifiers are the same validated configuration accepted by the installer.
    for db in (cfg["fresh_database"], cfg["upgrade_database"]):
        p = Path(cfg["state_root"]) / (db + ".toml")
        raw = profile(cfg, db)
        body = "\n".join(f"{k} = {json.dumps(v)}" for k, v in raw.items() if k != "environment") + "\n[environment]\n"
        p.write_text(body)
        install_reader.load_profile(p)
    sql(cfg, cfg["admin"], f'CREATE ROLE "{owner}" NOLOGIN NOSUPERUSER NOBYPASSRLS;\n'
        f'CREATE ROLE "{role}" LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;\n'
        + "\n".join(f'CREATE DATABASE "{db}" OWNER "{owner}";' for db in (cfg["fresh_database"], cfg["upgrade_database"])))
    # Two entry paths: fresh 1.2; exact original V1 + its original reader grants, then upgrade.
    fresh = install_reader.execute(profile(cfg, cfg["fresh_database"]), "initialize")
    assert fresh.returncode == 0, fresh.stderr
    old = f'SET ROLE "{owner}";\n' + install_reader.render("init_socai2_v1.sql") + '\nRESET ROLE;\n'
    old += f'GRANT USAGE ON SCHEMA socai2 TO "{role}"; GRANT SELECT ON ALL TABLES IN SCHEMA socai2 TO "{role}";'
    old += f'ALTER ROLE "{role}" IN DATABASE "{cfg["upgrade_database"]}" SET default_transaction_read_only=on;'
    sql(cfg, cfg["upgrade_database"], old)
    before = sql(cfg, cfg["upgrade_database"], catalog()).stdout
    upgrade = install_reader.execute(profile(cfg, cfg["upgrade_database"]), "upgrade")
    assert upgrade.returncode == 0, upgrade.stderr
    assert before == sql(cfg, cfg["upgrade_database"], catalog()).stdout, "upgrade changed tables/columns/RLS"
    for db in (cfg["fresh_database"], cfg["upgrade_database"]):
        check = install_reader.execute(profile(cfg, db), "verify")
        assert check.returncode == 0, check.stderr
        seed(cfg, db)
    return cfg


def catalog():
    return """SELECT jsonb_agg(jsonb_build_array(n.nspname,c.relname,c.relrowsecurity,c.relforcerowsecurity,
        (SELECT jsonb_agg(to_jsonb(a) ORDER BY a.attnum) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0),
        (SELECT jsonb_agg(to_jsonb(p) ORDER BY p.polname) FROM pg_policy p WHERE p.polrelid=c.oid)) ORDER BY n.nspname,c.relname)
        FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid
        WHERE n.nspname IN ('socai2','public') AND c.relkind='r';"""


def seed(cfg, db):
    # Explicit synthetic rows; these never reach the formal database or a model.
    sql(cfg, db, """
        INSERT INTO public.tenants(id,name,slug,plan,is_active,settings,limits,created_at,updated_at)
        SELECT id,'synthetic tenant',id::text,'test',true,'{}','{}',now(),now()
        FROM unnest(ARRAY['00000000-0000-0000-0000-000000000001'::uuid,'00000000-0000-0000-0000-000000000002'::uuid]) id;
        INSERT INTO public.assets(id,tenant_id,name,asset_type,criticality,ip_addresses,tags,last_seen,first_seen,metadata,created_at,updated_at)
        SELECT id,id,'synthetic-host','host','medium',ARRAY['192.0.2.10'],ARRAY['synthetic'],now(),now(),'{}',now(),now() FROM public.tenants;
        INSERT INTO public.users(id,tenant_id,email,username,hashed_password,role,is_active,is_verified,preferences,created_at,updated_at)
        SELECT id,id,id::text||'@test.invalid','synthetic owner '||id::text,'SECRET-SYNTHETIC-DO-NOT-EXPOSE','analyst',true,true,'{}',now(),now() FROM public.tenants;
        ALTER TABLE public.assets ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.assets FORCE ROW LEVEL SECURITY;
        CREATE POLICY synthetic_public_asset_policy ON public.assets USING
          (tenant_id=public.current_tenant_id() OR public.current_tenant_id() IS NULL);
        """)


def test_both_install_paths_have_same_reader_capabilities(installed):
    cfg = installed
    body = """SELECT jsonb_build_array(
        has_table_privilege(current_user,'public.assets','SELECT'),
        has_table_privilege(current_user,'public.users','SELECT'),
        has_function_privilege(current_user,'socai2.baseline_input_freshness(uuid,uuid)','EXECUTE'),
        has_function_privilege(current_user,'socai2.task_feedback_signature(jsonb)','EXECUTE'));"""
    for key in ("fresh_database", "upgrade_database"):
        result = sql(cfg, cfg[key], f'SET ROLE "{cfg["reader"]}";' + body)
        assert json.loads(result.stdout) == [True, True, True, True]


@pytest.mark.parametrize("database_key", ["fresh_database", "upgrade_database"])
def test_lookup_read_and_existing_schema_not_reset(installed, database_key):
    cfg = installed
    db, role = cfg[database_key], cfg["reader"]
    prefix = f'BEGIN READ ONLY; SET LOCAL ROLE "{role}";\n'
    select = "SELECT name FROM public.assets WHERE tenant_id=public.current_tenant_id(); SELECT username FROM public.users WHERE tenant_id=public.current_tenant_id();"
    for suffix in ("1", "2"):
        tenant = "00000000-0000-0000-0000-00000000000" + suffix
        result = sql(cfg, db, prefix + f"SET LOCAL app.current_tenant_id='{tenant}';" + select + "ROLLBACK;")
        assert result.stdout.splitlines() == ["synthetic-host", "synthetic owner " + tenant]
    for denied in ("DELETE FROM public.assets", "DELETE FROM socai2.alerts"):
        sql(cfg, db, prefix + denied + ";ROLLBACK;", expected=1)
    before = sql(cfg, db, catalog()).stdout
    assert install_reader.execute(profile(cfg, db), "initialize").returncode != 0
    assert sql(cfg, db, catalog()).stdout == before
    # Grants are safe to repeat; this never replays V1 or creates helper functions.
    assert install_reader.execute(profile(cfg, db), "upgrade").returncode == 0


def test_case_allocation_upgrade_and_new_install_share_increment():
    increment = install_reader.render(install_reader.CASE_MIGRATION)
    for entry in ('case_allocation.sql', 'init_socai2_current.sql', 'init_socai2_current_reader.sql'):
        body = install_reader.render(entry)
        assert body.count(increment) == 1
        assert 'case_allocation_migration_target_mismatch' in body
        assert 'incidents_active_case_link_fk' in body
        assert 'GRANT SELECT ON socai2.case_alert_exclusions' in body
    cfg = install_reader.load_profile(install_reader.HERE / 'reader-install.example.toml')
    cfg.pop('analysis')
    with pytest.raises(ValueError, match='analysis_migration_configuration_required'):
        install_reader.execute(cfg, 'case-allocation')
