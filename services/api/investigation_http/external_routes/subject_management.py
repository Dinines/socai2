"""Explicit human-only writes for the existing alert and incident read API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from investigation_http.contracts import (
    Actor,
    AlertFeedback,
    AlertFeedbackBatch,
    AlertManagementBatch,
    AlertManagementUpdate,
    IncidentManagementBatch,
    IncidentManagementUpdate,
    SelectedSubject,
    StoreError,
    SubjectBatchReceipt,
    SubjectMutationReceipt,
)
from investigation_http.dependencies import CurrentUser, require_permission
from investigation_http.dependencies import subject_service as get_service
from investigation_http.ports import SubjectManagement

User = Annotated[CurrentUser, Depends(require_permission("alerts:write"))]
Service = Annotated[SubjectManagement, Depends(get_service)]
router = APIRouter(tags=["socai2-subject-management"])


async def apply(
    service, user, kind, targets, changes, operation_key, *, feedback=False
):
    if user.workload_service:
        raise HTTPException(403, "subject_user_actor_required")
    try:
        return await service.apply(
            user.tenant_id,
            kind,
            targets,
            changes,
            operation_key,
            Actor(user_id=user.user_id, name=user.email),
            feedback=feedback,
        )
    except StoreError as exc:
        raise HTTPException(exc.status, exc.code) from None


@router.post("/alerts/feedback-batch", response_model=SubjectBatchReceipt)
async def feedback_batch(body: AlertFeedbackBatch, user: User, service: Service):
    return await apply(
        service,
        user,
        "alerts",
        body.items,
        body.feedback,
        body.operation_key,
        feedback=True,
    )


@router.post("/alerts/management-batch", response_model=SubjectBatchReceipt)
async def manage_alerts(body: AlertManagementBatch, user: User, service: Service):
    return await apply(
        service, user, "alerts", body.items, body.changes, body.operation_key
    )


@router.post("/incidents/management-batch", response_model=SubjectBatchReceipt)
async def manage_incidents(body: IncidentManagementBatch, user: User, service: Service):
    return await apply(
        service, user, "incidents", body.items, body.changes, body.operation_key
    )


@router.post("/alerts/{alert_id}/feedback", response_model=SubjectMutationReceipt)
async def feedback(alert_id: UUID, body: AlertFeedback, user: User, service: Service):
    result = await apply(
        service,
        user,
        "alerts",
        [SelectedSubject(id=alert_id, expected_row_version=body.expected_row_version)],
        body,
        body.operation_key,
        feedback=True,
    )
    return result.items[0]


@router.patch("/alerts/{alert_id}/management", response_model=SubjectMutationReceipt)
async def manage_alert(
    alert_id: UUID, body: AlertManagementUpdate, user: User, service: Service
):
    result = await apply(
        service,
        user,
        "alerts",
        [SelectedSubject(id=alert_id, expected_row_version=body.expected_row_version)],
        body,
        body.operation_key,
    )
    return result.items[0]


@router.patch(
    "/incidents/{incident_id}/management", response_model=SubjectMutationReceipt
)
async def manage_incident(
    incident_id: UUID, body: IncidentManagementUpdate, user: User, service: Service
):
    result = await apply(
        service,
        user,
        "incidents",
        [
            SelectedSubject(
                id=incident_id, expected_row_version=body.expected_row_version
            )
        ],
        body,
        body.operation_key,
    )
    return result.items[0]
