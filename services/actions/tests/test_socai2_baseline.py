"""Live dispatch and approval routes stay unavailable in the scoped baseline."""
from fastapi import FastAPI
from app.api.router import router as legacy
from app.api.live_actions_router import router as live
from app.core.scoped_baseline import apply_scope
from fastapi.testclient import TestClient


def test_only_dry_run_is_published_and_still_requires_auth(monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setenv('AISOC_SCOPED_BASELINE','1')
    monkeypatch.setenv('AISOC_ACTIONS_SERVICE_TOKEN','test-baseline-token')
    monkeypatch.setenv('AISOC_DEV_MODE','false')
    get_settings.cache_clear()
    app=FastAPI();app.include_router(legacy,prefix='/api/v1');app.include_router(live,prefix='/api/v1')
    apply_scope(app,'actions')
    client=TestClient(app)
    assert client.post('/api/v1/live-actions/dry-run',json={}).status_code==401
    for path in ['/api/v1/live-actions/dispatch','/api/v1/actions','/api/v1/actions/test/approve']:
        assert client.post(path,json={},headers={'Authorization':'Bearer test-baseline-token'}).status_code==404
    get_settings.cache_clear()
