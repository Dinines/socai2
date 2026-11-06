"""Local pilot only. Resolve the authenticated tenant's model in the serving API process."""
from app.api.v1.endpoints.socai2_cases import ReadUser, Service
from app.socai2.baseline_analysis_model import TenantChatGateway
from app.socai2_main import app as investigation_api
from backend_profile import ModelProfileMismatch, freeze
from config import TENANT
from fastapi import FastAPI, HTTPException
from starlette.types import Receive, Scope, Send

PROFILE_PATH = "/api/v1/socai2/validation/model-profile"
probe = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)


@probe.get(PROFILE_PATH)
async def model_profile(user: ReadUser, service: Service):
    if str(user.tenant_id) != TENANT:
        raise HTTPException(403, "pilot_tenant_required")
    gateway = TenantChatGateway()
    try:
        configured = await gateway.configure(service, user.tenant_id)
    except Exception:  # noqa: BLE001 -- suppress resolver details at this HTTP boundary
        # Provider configuration errors can include internal connection details.
        raise HTTPException(503, "pilot_model_configuration_unavailable") from None
    if not configured:
        raise HTTPException(503, "pilot_model_configuration_unavailable")
    try:
        return freeze({
            "OPENAI_MODEL": gateway.model,
            "OPENAI_BASE_URL": gateway.config.base_url,
            "SOCAI2_MODEL_PROTOCOL": gateway.provider,
            "SOCAI2_MODEL_SCHEMA_PROFILE": gateway.schema_profile,
        }, backend="deployed")
    except ModelProfileMismatch:
        raise HTTPException(409, "pilot_deployed_model_profile_mismatch") from None


async def app(scope: Scope, receive: Receive, send: Send):
    # All ordinary traffic and the complete ASGI lifespan stay with the original app.
    if scope["type"] == "http" and scope["path"] == PROFILE_PATH:
        await probe(scope, receive, send)
    else:
        await investigation_api(scope, receive, send)
