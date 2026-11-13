"""The production read surface must work while Case writes remain disabled."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from app.api.v1.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import socai2_cases, socai2_tasks
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters import services as backends


@pytest.mark.asyncio
@pytest.mark.parametrize(('page_enabled', 'case_enabled', 'status'),
                         [(True, False, 200), (False, False, 503), (False, True, 200)])
async def test_case_and_task_get_flags_preserve_write_and_identity_boundaries(monkeypatch, page_enabled, case_enabled, status):
    tenant, user, case = UUID(int=1), UUID(int=3), UUID(int=4)
    principal = CurrentUser(user, tenant, 'analyst', 'synthetic@test.invalid', scopes=['cases:read', 'cases:write'])
    queue = {'items': [], 'total': 0, 'next_cursor': None,
             'metrics': {'awaiting_assignment': 0, 'in_progress': 0, 'high_severity': 0, 'awaiting_human': 0}}
    service = SimpleNamespace(read_cases=AsyncMock(return_value=queue),
                              list=AsyncMock(return_value={'items': [], 'total': 0, 'next_offset': None}),
                              create=AsyncMock(), write=AsyncMock())
    monkeypatch.setattr(backends.settings, 'SOCAI2_PAGE_READ_ENABLED', page_enabled)
    monkeypatch.setattr(backends.settings, 'SOCAI2_CASE_API_ENABLED', case_enabled)
    monkeypatch.setattr(backends, 'CaseBackend', lambda _: service)
    monkeypatch.setattr(backends, 'HumanTaskService', lambda _: service)
    app = FastAPI()
    for router in (socai2_cases.router, socai2_tasks.router):
        app.include_router(router, prefix='/api/v1')
    app.dependency_overrides[get_current_user] = lambda: principal
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/v1/socai2/cases')
        assert response.status_code == status
        response = await client.get(f'/api/v1/socai2/cases/{case}/tasks')
        assert response.status_code == status
        if status == 200:
            assert service.read_cases.await_args.args[0] == tenant
            assert service.list.await_args.args == (tenant, case)
        if not case_enabled:
            body = {'operation_key': str(UUID(int=5)), 'title': 'Synthetic', 'alert_ids': [str(UUID(int=6))]}
            assert (await client.post('/api/v1/socai2/cases', json=body)).status_code == 503
            assert (await client.post(f'/api/v1/socai2/cases/{case}/tasks', json={})).status_code == 503
            service.create.assert_not_awaited()
            service.write.assert_not_awaited()
        principal.scopes = ['alerts:read']
        assert (await client.get('/api/v1/socai2/cases')).status_code == 403
        assert (await client.get(f'/api/v1/socai2/cases/{case}/tasks')).status_code == 403
