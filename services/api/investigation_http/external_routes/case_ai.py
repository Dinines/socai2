"""Reserved Q routes. No Case lookup, execution, or persistence is connected."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from investigation_http.contracts import (
    AIUnavailable,
    AskCaseAI,
    SaveCaseAIAnswer,
)
from investigation_http.dependencies import (
    CurrentUser,
    require_case_enabled,
    require_permission,
)

WriteUser = Annotated[CurrentUser, Depends(require_permission("cases:write"))]


def reserved_user(user: WriteUser) -> CurrentUser:
    require_case_enabled()
    if user.workload_service:
        raise HTTPException(403, "case_user_actor_required")
    return user


User = Annotated[CurrentUser, Depends(reserved_user)]
router = APIRouter(
    prefix="/socai2/cases",
    tags=["socai2-case-ai-reserved"],
    responses={
        403: {"description": "Case write permission and a user actor are required"},
        503: {"description": "socai2 Case API is disabled"},
    },
)


@router.post(
    "/{case_id}/ai/messages",
    status_code=501,
    response_model=AIUnavailable,
    summary="Reserved: send a Case AI question (not implemented)",
)
async def ask(case_id: UUID, body: AskCaseAI, user: User):
    return AIUnavailable()


@router.post(
    "/{case_id}/ai/messages/{message_id}/save",
    status_code=501,
    response_model=AIUnavailable,
    summary="Reserved: save an AI answer as an investigation result (not implemented)",
)
async def save(case_id: UUID, message_id: UUID, body: SaveCaseAIAnswer, user: User):
    return AIUnavailable()
