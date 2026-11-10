"""Configured lookup validation and real page reads against isolated V1.2 databases."""

import asyncio
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from app.models import socai2 as m
from app.socai2.baseline_store import StoreError
from app.socai2.page_reader import PageReadService
from app.socai2.read_sources import ReadSources, lookup_error
from sqlalchemy import insert, text, update
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

SOURCES = {"assets": "public.assets", "owners": "public.users"}


@pytest.mark.parametrize("name", ['public.users; SELECT 1', 'public."users"', 'users', 'public.users()'])
def test_request_text_cannot_become_a_relation(name):
    with pytest.raises(ValueError, match="identifier_invalid"):
        ReadSources.from_config({**SOURCES, "owners": name})


@pytest.mark.parametrize(("state", "code"), [("42501", "read_dependency_permission_denied"),
    ("42P01", "read_dependency_missing"), ("42883", "read_dependency_missing"), ("42703", "read_dependency_schema_mismatch")])
def test_operational_errors_are_sanitized(state, code):
    original = RuntimeError("private source data and credentials")
    original.sqlstate = state
    with pytest.raises(StoreError) as caught:
        lookup_error(DBAPIError("SELECT secret", {}, original))
    assert caught.value.status == 503 and caught.value.code == code
    assert "private" not in str(caught.value)


@pytest.mark.parametrize("key", ["fresh_database", "upgrade_database"])
def test_real_page_asset_owner_and_wrong_tenant_reads(key):
    path = os.environ.get("SOCAI2_READER_TEST_CONFIG")
    if not path:
        pytest.skip("explicit isolated PG profile required")
    asyncio.run(page_reads(json.loads(Path(path).read_text()), key))


async def page_reads(cfg, key):
    from app.api.v1.deps import CurrentUser, get_current_user
    from app.api.v1.endpoints import socai2_pages as api
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    url = URL.create("postgresql+psycopg", username=cfg["admin"], password=Path(cfg["password_file"]).read_text(),
                     host=cfg["host"], port=cfg["port"], database=cfg[key], query={"sslmode": "disable"})
    admin = create_async_engine(url)
    reader = create_async_engine(url, connect_args={"options": "-c role=" + cfg["reader"]})
    tenant, other = UUID(int=1), UUID(int=2)
    aid, mid, oid, other_aid = uuid4(), uuid4(), uuid4(), uuid4()
    try:
        async with admin.begin() as conn:
            for alert_id, t in ((aid, tenant), (other_aid, other)):
                await conn.execute(insert(m.Alerts).values(id=alert_id, tenant_id=t, source_namespace="v1.2-synthetic",
                    source_identity_key=str(alert_id), title="synthetic read dependency", owner_id=t, assignment_state="assigned"))
            await conn.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=tenant, alert_id=aid, revision=1,
                raw_json={"host": "synthetic-host"}, detection={}, source_scope={}, retention={}, material_state="complete"))
            await conn.execute(update(m.Alerts).where(m.Alerts.id == aid).values(latest_material_id=mid))
            await conn.execute(insert(m.AlertObjects).values(id=oid, tenant_id=tenant, alert_id=aid, material_id=mid,
                object_key="host:synthetic-host", namespace="v1.2-synthetic", object_type="host", source_type="source",
                object_role="entity", raw_value="synthetic-host", normalized_value="synthetic-host", source_path="$.raw_json.host", attributes={}))
        async with reader.connect() as conn:
            assert (await conn.execute(text("SELECT current_user"))).scalar_one() == cfg["reader"]
            assert all(r["ready"] for r in await ReadSources.from_config(SOURCES).check(conn))
        sessions = async_sessionmaker(reader, expire_on_commit=False)
        service = PageReadService(sessions, read_sources=SOURCES)
        app = FastAPI()
        app.include_router(api.router, prefix="/api/v1")
        principal = CurrentUser(tenant, tenant, "analyst", "synthetic@test.invalid", scopes=["alerts:read", "cases:read"])
        app.dependency_overrides[get_current_user] = lambda: principal
        app.dependency_overrides[api.get_service] = lambda: service
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
            response = await client.get(f"/api/v1/socai2/alerts/{aid}")
            assert response.status_code == 200, response.text
            assert "synthetic owner " + str(tenant) in response.text
            assert "SECRET-SYNTHETIC" not in response.text
            response = await client.get(f"/api/v1/socai2/alerts/{aid}/records/assets?tenant_id={other}", headers={"X-Tenant-ID": str(other)})
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["total"] == 1 and data["items"][0]["asset_id"] == str(tenant)
            assert data["items"][0]["object_id"] == str(oid)
            assert (await client.get(f"/api/v1/socai2/alerts/{other_aid}")).status_code == 404
            # A real denied public read becomes a 503, not an empty asset list/500.
            async with admin.begin() as conn:
                await conn.execute(text(f'REVOKE SELECT ON public.assets FROM "{cfg["reader"]}"'))
            denied = await client.get(f"/api/v1/socai2/alerts/{aid}/records/assets")
            assert denied.status_code == 503 and denied.json()["detail"] == "read_dependency_permission_denied"
            async with admin.begin() as conn:
                await conn.execute(text(f'GRANT SELECT ON public.assets TO "{cfg["reader"]}"'))
    finally:
        await reader.dispose()
        await admin.dispose()
