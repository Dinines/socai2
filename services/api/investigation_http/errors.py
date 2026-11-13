"""The transport boundary translates existing application errors exactly once."""

from fastapi import HTTPException

from investigation_http.contracts import Actor, StoreError


def actor(user):
    if user.workload_service:
        raise HTTPException(403, "case_user_actor_required")
    return Actor(user_id=user.user_id, name=user.email)


async def invoke(call):
    try:
        return await call
    except StoreError as exc:
        raise HTTPException(exc.status, exc.code) from None


def provide(factory, *args):
    try:
        return factory(*args)
    except StoreError as exc:
        raise HTTPException(exc.status, exc.code) from None
