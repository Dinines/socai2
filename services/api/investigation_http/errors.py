"""The transport boundary translates existing application errors exactly once."""

from fastapi import HTTPException
from pydantic import ValidationError

from investigation_http.contracts import Actor, StoreError


def query_input(model, **values):
    try:
        return model(**values)
    except ValidationError as exc:
        raise HTTPException(422, exc.errors(include_context=False, include_url=False, include_input=False)) from None


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
