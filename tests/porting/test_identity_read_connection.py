"""The identity GET cannot enable the global graph or bootstrap shared schema."""
import json
from pathlib import Path

import pytest
from app.db import neo4j as graph


def config_file(tmp_path, monkeypatch, **overrides):
    value = {"uri": "bolt://graph.test:7687", "username": "unit", "password": "unit-only", "database": "neo4j"}
    value.update(overrides)
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(value)); path.chmod(0o600)
    monkeypatch.setenv('AISOC_IDENTITY_GRAPH_CONFIG_FILE', str(path))
    return path


@pytest.mark.parametrize('failure', ['missing', 'unreadable', 'invalid_json', 'bad_fields', 'broad_mode', 'uri_credentials', 'database'])
def test_unusable_config_does_not_fall_back_to_global_driver(tmp_path, monkeypatch, failure):
    path = config_file(tmp_path, monkeypatch)
    if failure == 'missing': monkeypatch.delenv('AISOC_IDENTITY_GRAPH_CONFIG_FILE')
    elif failure == 'unreadable': path.unlink()
    elif failure == 'invalid_json': path.write_text('{')
    elif failure == 'bad_fields': path.write_text(json.dumps({'uri': 'bolt://graph.test'}))
    elif failure == 'broad_mode': path.chmod(0o644)
    elif failure == 'uri_credentials': config_file(tmp_path, monkeypatch, uri='bolt://unit:must-not-leak@graph.test')
    elif failure == 'database': config_file(tmp_path, monkeypatch, database='system')
    sentinel = object(); monkeypatch.setattr(graph, '_driver', sentinel)
    with pytest.raises(graph.IdentityGraphNotConfigured, match='configuration is unavailable') as exc:
        graph._identity_read_config()
    assert graph._driver is sentinel
    assert 'must-not-leak' not in str(exc.value) and 'unit-only' not in str(exc.value)


@pytest.mark.asyncio
@pytest.mark.parametrize('body_fails', [False, True])
async def test_session_is_read_only_no_schema_and_always_closes(tmp_path, monkeypatch, body_fails):
    config_file(tmp_path, monkeypatch); events=[]; sentinel=object()
    monkeypatch.setattr(graph, '_driver', sentinel)
    async def forbidden(): raise AssertionError('Global graph initialization/schema must never run')
    monkeypatch.setattr(graph, 'init_neo4j', forbidden); monkeypatch.setattr(graph, '_create_schema', forbidden)
    class Session:
        async def __aenter__(self): events.append('session_open'); return self
        async def __aexit__(self, *args): events.append('session_closed')
    session=Session()
    class Driver:
        async def __aenter__(self): events.append('driver_open'); return self
        async def __aexit__(self, *args): events.append('driver_closed')
        def session(self, **kwargs):
            assert kwargs == {'database':'neo4j', 'default_access_mode':graph.READ_ACCESS}
            return session
    def create(uri, **kwargs):
        assert uri=='bolt://graph.test:7687' and kwargs['auth']==('unit','unit-only')
        assert kwargs['max_transaction_retry_time']==0
        return Driver()
    monkeypatch.setattr(graph.AsyncGraphDatabase, 'driver', create)
    if body_fails:
        with pytest.raises(RuntimeError, match='probe-only'):
            async with graph.get_identity_read_session(): raise RuntimeError('probe-only')
    else:
        async with graph.get_identity_read_session() as found: assert found is session
    assert events == ['driver_open','session_open','session_closed','driver_closed']
    assert graph._driver is sentinel
