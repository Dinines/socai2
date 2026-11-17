"""Ensure the former aggregate registration cannot expose synchronous execution."""
from uuid import UUID

from app.api.v1.endpoints import socai2_stage_execution
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_retired_stage_router_has_no_synchronous_bypass():
    app = FastAPI()
    app.include_router(socai2_stage_execution.router, prefix="/api/v1")
    assert not app.openapi()["paths"]
    with TestClient(app) as client:
        for path in ("alerts", "incidents"):
            suffix = "analyze" if path == "alerts" else "diagnose"
            response = client.post(f"/api/v1/socai2/{path}/{UUID(int=1)}/{suffix}",
                                   json={"operation_key": str(UUID(int=2))})
            assert response.status_code == 404
