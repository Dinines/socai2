"""Explicit Case/H writer pool, separate from the general API connection."""
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.database import _normalize_async_pg_url
from app.socai2.baseline_store import StoreError

_runtime = None


def get_case_write_sessions():
    """Called by async route dependencies; pool creation performs no database IO."""
    global _runtime
    configured = settings.SOCAI2_CASE_DATABASE_URL.get_secret_value().strip()
    if not configured:
        raise StoreError("case_write_database_not_configured", 503)
    if _runtime is not None:
        if _runtime[0] != configured:
            raise StoreError("case_write_database_configuration_changed", 503)
        return _runtime[2]
    try:
        normalized, connect_args = _normalize_async_pg_url(configured)
        url = make_url(normalized)
        if (url.drivername not in {"postgresql+asyncpg", "postgresql+psycopg", "postgresql+psycopg_async"}
                or not all((url.host, url.port, url.username, url.database))):
            raise ValueError("explicit PostgreSQL target required")
        engine = create_async_engine(url, connect_args=connect_args,
            pool_size=settings.DATABASE_POOL_SIZE, max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True, pool_recycle=settings.DATABASE_POOL_RECYCLE_SECONDS,
            echo=settings.DEBUG)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
    except (ArgumentError, ValueError, TypeError, ImportError):
        # A malformed URL may contain credentials; never propagate its raw error.
        raise StoreError("case_write_database_configuration_invalid", 503) from None
    _runtime = (configured, engine, sessions)
    return sessions


async def close_case_database():
    global _runtime
    current, _runtime = _runtime, None
    if current is not None:
        await current[1].dispose()
