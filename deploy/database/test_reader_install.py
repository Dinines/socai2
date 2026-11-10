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


@pytest.mark.parametrize("change", [{"environment": {}}, {"transport": ""}, {"psql_argv": ["psql"]}])
def test_missing_connection_never_uses_libpq_defaults(tmp_path, change):
    import tomllib
    raw = tomllib.loads((install_reader.HERE / "reader-install.example.toml").read_text())
    raw.update(change)
    path = tmp_path / "profile.toml"
    path.write_text("\n".join(f"{k} = {json.dumps(v)}" for k, v in raw.items() if k != "environment")
                    + "\n[environment]\n" + "\n".join(f"{k} = {json.dumps(v)}" for k, v in raw["environment"].items()))
    with pytest.raises(ValueError):
        install_reader.load_profile(path)


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
