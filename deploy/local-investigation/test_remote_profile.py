"""Isolation, strict TLS, driver compatibility and read-service authentication."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from remote_profile import ROOT, SECRET_ENV_KEYS, load_profile
from sqlalchemy.engine import make_url


@pytest.fixture
def configuration(tmp_path):
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    ca = private / "ca.crt"
    ca.write_text("offline test CA placeholder")
    secrets = private / "secrets.json"
    secrets.write_text(json.dumps({"database_password": "test/p@ss%word", "access_token": "test-access-token-" * 4,
                                   "environment": {key: "test-secret-value-" * 4 for key in SECRET_ENV_KEYS}}))
    secrets.chmod(0o600)
    template = (Path(__file__).parent / "remote-profile.example.toml").read_text()
    template = template.replace('".local/conda-envs/socai2/bin/python"', json.dumps(sys.executable))
    template = template.replace('".local/remote-21/private/secrets.json"', json.dumps(str(secrets)))
    template = template.replace('".local/remote-21/private/socai2-ca.crt"', json.dumps(str(ca)))
    target = tmp_path / "profile.toml"
    target.write_text(template)
    return target, secrets


def test_explicit_values_and_secret_encoding_are_preserved(configuration, monkeypatch):
    path, _ = configuration
    path.write_text(path.read_text().replace('name = "aisoc"', 'name = "chosen_database"').replace("port = 25432", "port = 25439"))
    monkeypatch.setenv("DATABASE_URL", "postgresql://wrong:wrong@wrong/wrong")
    monkeypatch.setenv("OPENAI_API_KEY", "not-this-process")
    profile = load_profile(path)
    url = make_url(profile.environment()["DATABASE_URL"])
    assert (url.database, url.port, url.password) == ("chosen_database", 25439, "test/p@ss%word")
    assert url.query["sslmode"] == "verify-full"
    assert url.host != url.query["hostaddr"]
    assert "OPENAI_API_KEY" not in profile.environment()
    assert profile.environment()["SOCAI2_INVESTIGATION_POLICY"] == str(ROOT / "deploy/local-investigation/investigation-policy.toml")
    assert "test/p@ss%word" not in repr(profile)


@pytest.mark.parametrize(("before", "after"), [
    ('sslmode = "verify-full"', 'sslmode = "require"'),
    ('host = "127.0.0.1"', 'host = "0.0.0.0"'),
    ('permissions = ["alerts:read", "cases:read"]', 'permissions = ["cases:write"]'),
    ('AISOC_DEV_AUTH_BYPASS = "false"', 'AISOC_DEV_AUTH_BYPASS = "true"'),
    ('SOCAI2_STAGE_EXECUTION_ENABLED = "false"', 'SOCAI2_STAGE_EXECUTION_ENABLED = "true"'),
])
def test_profile_rejects_unsafe_modes(configuration, before, after):
    path, _ = configuration
    assert before in path.read_text()
    path.write_text(path.read_text().replace(before, after))
    with pytest.raises(ValueError):
        load_profile(path)


def test_missing_identity_never_falls_back(configuration):
    path, _ = configuration
    path.write_text(path.read_text().replace('name = "aisoc"\n', ""))
    with pytest.raises(KeyError):
        load_profile(path)


def test_private_file_permissions_are_enforced(configuration):
    path, secrets = configuration
    secrets.chmod(0o644)
    with pytest.raises(ValueError, match="owner_only"):
        load_profile(path)


def run_isolated(profile, code):
    result = subprocess.run([str(ROOT / profile.config["python"]), "-B", "-c", code],
                            env=profile.environment(), cwd=profile.path.parent, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_actual_async_dialect_keeps_tls_and_legacy_asyncpg(configuration):
    pytest.importorskip("psycopg")
    profile = load_profile(configuration[0])
    run_isolated(profile, """
from app.db import database as db
from sqlalchemy.engine import make_url
assert db.engine.dialect.driver == 'psycopg' and db.engine.dialect.is_async
assert db._connect_args == {}
args, kwargs = db.engine.sync_engine.dialect.create_connect_args(make_url(db._normalized_url))
assert kwargs['sslmode'] == 'verify-full' and kwargs['hostaddr'] == '127.0.0.1'
assert kwargs['options'].startswith('-c default_transaction_read_only=on ')
assert 'ssl' not in kwargs and 'command_timeout' not in kwargs and 'timeout' not in kwargs
url, args = db._normalize_async_pg_url('postgres://u:p@host/d?sslmode=disable&channel_binding=require')
assert url == 'postgresql+asyncpg://u:p@host/d' and args == {'ssl': False}
url, args = db._normalize_async_pg_url('postgresql://u:p@host/d?sslmode=verify-full')
assert url.startswith('postgresql+asyncpg://') and args == {'ssl': 'verify-full'}
""")


def test_http_authentication_scope_and_mutations_without_database(configuration):
    pytest.importorskip("psycopg")
    profile = load_profile(configuration[0])
    run_isolated(profile, """
import os
from fastapi import Depends
from fastapi.testclient import TestClient
from app.api.v1.deps import get_current_user
import remote_readonly_api as module
from app.socai2_main import configured_database_name
os.environ['SOCAI2_SERVICE_DATABASE_NAME'] = 'aisoc'
try:
    configured_database_name()
except RuntimeError:
    pass
else:
    raise AssertionError('standalone writer target must be explicitly configured')
def unexpected_connection(*args, **kwargs):
    raise AssertionError('authentication or mutation reached the database')
type(module.engine).connect = unexpected_connection
@module.app.get('/scope-probe')
def probe(user=Depends(get_current_user)):
    return {'tenant':str(user.tenant_id),'scopes':user.scopes,'service':user.workload_service}
client = TestClient(module.app)
token = module.profile.secrets['access_token']
headers = {'Authorization':'Bearer '+token}
assert client.get('/api/v1/socai2/cases').status_code == 401
assert client.get('/scope-probe', headers={'Authorization':'Bearer invalid'}).status_code == 401
assert client.post('/api/v1/socai2/cases',headers=headers,json={}).status_code == 405
assert client.patch('/api/v1/socai2/cases/irrelevant',headers=headers,json={}).status_code == 405
assert client.delete('/api/v1/socai2/cases/irrelevant',headers=headers).status_code == 405
response = client.get('/scope-probe?tenant_id=another',headers={**headers,'X-Tenant-ID':'another'})
assert response.status_code == 200
assert response.json() == {'tenant':module.profile.config['api']['tenant_id'],
                          'scopes':['alerts:read','cases:read'],'service':module.profile.config['name']}
assert all(set(operations) <= {'get'} for operations in module.app.openapi()['paths'].values())
""")
