"""Trusted business context for this app; legacy app dependencies stay intact."""

import json
import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from uuid import UUID

from app.api.v1.deps import CurrentUser
from app.api.v1.deps import require_permission as legacy_permission
from fastapi import Request

_legacy_dependencies = set()


@cache
def require_permission(permission):
    # These same routers are imported by the legacy main API. Only the
    # independent application's assembly replaces their dependencies.
    dependency = legacy_permission(permission)
    _legacy_dependencies.add(dependency)
    return dependency


@dataclass(frozen=True)
class BusinessContext:
    tenant_id: UUID
    user_id: UUID
    email: str  # Existing Actor adapter uses this slot as the recorded name.
    workload_service: None = None

    def require_permission(self, permission):
        # Compatibility with the one inline legacy record-section check.
        # This is a configured business context, never an authenticated user.
        return None


def load_context():
    try:
        path = Path(os.environ["SOCAI2_HTTP_CONTEXT_FILE"])
        if not path.is_absolute():
            raise ValueError("absolute context path required")
        values = json.loads(path.read_text())
        if set(values) != {"tenant_id", "actor_id", "actor_name"}:
            raise ValueError("context keys differ")
        name = values["actor_name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("recorded name required")
        return BusinessContext(UUID(values["tenant_id"]), UUID(values["actor_id"]), name)
    except (KeyError, OSError, ValueError, TypeError):
        raise RuntimeError("socai2_http_business_context_configuration_required") from None


def business_context(request: Request) -> BusinessContext:
    return request.app.state.business_context


def configure_trusted_access(app):
    for dependency in _legacy_dependencies:
        app.dependency_overrides[dependency] = business_context
    original_openapi = app.openapi

    def openapi():
        schema = original_openapi()
        schema.pop("security", None)
        schema.get("components", {}).pop("securitySchemes", None)
        for methods in schema["paths"].values():
            for operation in methods.values():
                if isinstance(operation, dict):
                    operation.pop("security", None)
                    for code in ("401", "403"):
                        operation.get("responses", {}).pop(code, None)
        return schema

    app.openapi = openapi


__all__ = ["CurrentUser", "configure_trusted_access", "load_context", "require_permission"]
