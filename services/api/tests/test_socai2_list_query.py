"""Direct HTTP rejection checks, without database/model substitution for success."""
from uuid import UUID

import pytest
from app.api.v1.deps import CurrentUser, get_current_user
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from investigation_http.external_routes import cases, pages


@pytest.mark.asyncio
async def test_invalid_list_query_returns_json_422_before_business_call():
    app = FastAPI()
    app.include_router(cases.router, prefix="/api/v1")
    app.include_router(pages.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        UUID(int=3), UUID(int=1), "viewer", "list-check@example.invalid", scopes=["cases:read", "alerts:read"])
    app.dependency_overrides[cases.get_service] = lambda: object()
    app.dependency_overrides[pages.get_service] = lambda: object()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
        for kind in ("alerts", "incidents", "cases"):
            for params in (
                {"time_from": "2026-11-13T10:00:00"},
                {"time_from": "2026-11-13T10:00:00Z", "time_to": "2026-11-13T10:00:00Z"},
                {"time_from": "2026-11-13T11:00:00Z", "time_to": "2026-11-13T10:00:00Z"},
                {"sort_by": "invalid"},
            ):
                result = await client.get("/api/v1/socai2/" + kind, params=params)
                assert result.status_code == 422, result.text
                assert isinstance(result.json()["detail"], list)
        for kind in ("alerts", "incidents"):
            for extra in ({"q": "title"}, {"cursor": "anything"}, {"sort_order": "desc"}):
                result = await client.get("/api/v1/socai2/" + kind,
                    params={"before_id": str(UUID(int=1)), **extra})
                assert result.status_code == 422 and result.json()["detail"]
