"""Read the explicitly scoped, non-login Spirit Hub owner projections."""
import os
from pathlib import Path
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator
from sqlalchemy import func, or_, select

from app.models.tenant import User

from .baseline_contracts import Contract
from .baseline_store import StoreError

USERS = User.__table__
OWNER_PROJECTION_KEY = "socai2_owner_projection"


class OwnerDirectoryScope(Contract):
    tenant_id: UUID
    user_ids: tuple[UUID, ...] = Field(min_length=1)

    @classmethod
    def load(cls):
        path = Path(os.environ.get("SOCAI2_OWNER_DIRECTORY_PROFILE_FILE", ""))
        if not path.is_absolute():
            raise StoreError("owner_directory_profile_required", 503)
        try:
            return cls.model_validate_json(path.read_bytes())
        except (OSError, ValueError):
            raise StoreError("owner_directory_profile_invalid", 503) from None


class OwnerDirectoryQuery(Contract):
    q: str | None = Field(default=None, max_length=200)
    user_id: UUID | None = None
    offset: int = Field(default=0, ge=0, le=100000)
    limit: int = Field(default=50, ge=1, le=200)

    @field_validator("q")
    @classmethod
    def normalize_search(cls, value):
        return (value.strip() or None) if value is not None else None


class OwnerOption(Contract):
    id: UUID
    username: str
    display_name: str


class OwnerDirectoryPage(Contract):
    items: list[OwnerOption]
    total: int
    offset: int
    limit: int
    next_offset: int | None
    observed_at: AwareDatetime


async def read_owner_directory(store, scope, query):
    projection = USERS.c.preferences[OWNER_PROJECTION_KEY]
    display = projection["display_name"].astext
    predicates = list(store.where(USERS, USERS.c.tenant_id == scope.tenant_id, USERS.c.id.in_(scope.user_ids),
        USERS.c.is_active.is_(False), projection["provider"].astext == "spirithub",
        func.jsonb_typeof(projection["display_name"]) == "string"))
    if query.user_id is not None:
        predicates.append(USERS.c.id == query.user_id)
    if query.q:
        search = func.lower(query.q)
        predicates.append(or_(func.strpos(func.lower(USERS.c.username), search) > 0,
                              func.strpos(func.lower(display), search) > 0))
    total = (await store.db.execute(select(func.count()).select_from(USERS).where(*predicates))).scalar_one()
    rows = (await store.db.execute(select(USERS.c.id, USERS.c.username, display.label("display_name"))
        .where(*predicates).order_by(func.lower(display), USERS.c.id).offset(query.offset).limit(query.limit))).mappings().all()
    next_offset = query.offset + len(rows)
    return OwnerDirectoryPage(items=[OwnerOption.model_validate(row) for row in rows], total=total,
        offset=query.offset, limit=query.limit, next_offset=next_offset if next_offset < total else None,
        observed_at=await store.now())
