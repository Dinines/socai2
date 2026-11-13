"""Reuse existing identity contracts; no second authentication implementation."""

from app.api.v1.deps import CurrentUser, require_permission
from app.api.v1.endpoints.auth import router as login_router

__all__ = ["CurrentUser", "login_router", "require_permission"]
