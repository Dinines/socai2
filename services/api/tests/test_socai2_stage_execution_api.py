"""New A/I HTTP uses real synthetic PG and an unavailable model substitute."""
import asyncio
import traceback
from uuid import UUID, uuid4

from app.api.v1.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import socai2_stage_execution as api
from app.models import socai2 as m
from app.socai2.baseline_store import A, R
from app.socai2.stage_results import StageResultService
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.services import ExecutionBackend
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import async_sessionmaker

T, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)


class UnavailableModel:
    provider, model = "synthetic", "disabled"

    async def configure(self, service, tenant):
        return False


async def run_checks(engine, record, only=None):
    class Service(StageResultService):
        async def execute_alert(self, *args, **kwargs):
            return await super().execute_alert(*args, **kwargs, gateway=UnavailableModel())

        async def execute_incident(self, *args, **kwargs):
            return await super().execute_incident(*args, **kwargs, gateway=UnavailableModel())

    service = Service(async_sessionmaker(engine, expire_on_commit=False))
    principal = CurrentUser(USER, T, "admin", "synthetic@example.invalid", scopes=["alerts:read", "alerts:write"])
    app = FastAPI()
    app.include_router(api.router, prefix="/api/v1")
    async def user():
        return principal
    app.dependency_overrides[get_current_user] = user
    backend = ExecutionBackend(service.sessions)
    backend._execution = service  # Model substitute stays behind the external use-case port.
    app.dependency_overrides[api.get_execution_service] = lambda: backend

    async def fixture():
        aid, iid = uuid4(), uuid4()
        async with service.transaction(T) as store:
            await store.db.execute(insert(A).values(id=aid, tenant_id=T, source_namespace="http-stage-fixture",
                source_identity_key=str(aid), title="synthetic manually triggered A"))
            await store.db.execute(insert(m.Incidents.__table__).values(id=iid, tenant_id=T,
                source_namespace="http-stage-fixture", source_incident_id=str(iid), title="synthetic I"))
            await store.db.execute(insert(m.IncidentAlerts.__table__).values(id=uuid4(), tenant_id=T, alert_id=aid,
                incident_id=iid, membership_source="fusion", correlation_basis={}, basis_version="fixture", source_operation_id=uuid4()))
        return aid, iid

    async def test_stage_http_actor_persistence_replay_and_no_baseline():
        aid, iid = await fixture()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
            for path in [f"alerts/{aid}/analyze", f"incidents/{iid}/diagnose"]:
                body = {"operation_key": str(uuid4())}
                response = await client.post("/api/v1/socai2/"+path, json=body)
                assert response.status_code == 200, response.text
                result = response.json()
                assert result["run"]["state"] == "failed" and result["run"]["requested_by"] == str(USER)
                replay = await client.post("/api/v1/socai2/"+path, json=body)
                assert replay.status_code == 200 and replay.json() == result
            async with service.transaction(T, readonly=True) as store:
                runs = (await store.db.execute(select(R).where(R.c.tenant_id == T,
                    (R.c.alert_id == aid) | (R.c.incident_id == iid)))).mappings().all()
                assert len(runs) == 2 and all(row["case_id"] is None for row in runs)

    async def test_stage_http_permission_scope_and_request_boundaries():
        nonlocal principal
        aid, _ = await fixture()
        path = f"/api/v1/socai2/alerts/{aid}/analyze"
        body = {"operation_key": str(uuid4())}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
            principal = CurrentUser(USER, T, "viewer", "synthetic@example.invalid", scopes=["alerts:read"])
            assert (await client.post(path, json=body)).status_code == 403
            principal = CurrentUser(USER, T, "admin", "synthetic@example.invalid", scopes=["alerts:write"])
            for key,value in [("tenant_id", str(OTHER)), ("max_tokens", 90000), ("requested_by", str(uuid4()))]:
                assert (await client.post(path, json={**body,key:value})).status_code == 422
            principal = CurrentUser(USER, OTHER, "admin", "synthetic@example.invalid", scopes=["alerts:write"])
            response = await client.post(path, json=body)
            assert response.status_code == 403 and response.json()["detail"] == "stage_actor_not_in_tenant"
            principal = CurrentUser(USER, T, "admin", "synthetic@example.invalid", scopes=["alerts:write"])
            assert (await client.post("/api/v1/socai2/alerts/"+str(uuid4())+"/analyze", json=body)).status_code == 404

    for check in [test_stage_http_actor_persistence_replay_and_no_baseline, test_stage_http_permission_scope_and_request_boundaries]:
        if only is not None and check.__name__ not in only:
            continue
        try:
            await asyncio.wait_for(check(), 120)
            record(check.__name__, True)
        except Exception:  # noqa: BLE001 -- retain original synthetic result
            record(check.__name__, False, traceback.format_exc())
