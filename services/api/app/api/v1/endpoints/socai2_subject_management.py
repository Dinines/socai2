"""Explicit human-only writes for the existing alert and incident read API."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.deps import CurrentUser, require_permission
from app.core.config import settings
from app.db.case_database import get_case_write_sessions
from app.socai2.baseline_contracts import Actor
from app.socai2.baseline_store import StoreError
from app.socai2.subject_management import SubjectManagementService
from app.socai2.subject_management_contracts import (
    AlertFeedback,
    AlertFeedbackBatch,
    AlertManagementBatch,
    AlertManagementUpdate,
    IncidentManagementBatch,
    IncidentManagementUpdate,
    SelectedSubject,
    SubjectBatchReceipt,
    SubjectMutationReceipt,
)


def get_service():
    if not settings.SOCAI2_CASE_API_ENABLED:
        raise HTTPException(503, "socai2_subject_write_not_enabled")
    try:
        return SubjectManagementService(get_case_write_sessions())
    except StoreError as exc:
        raise HTTPException(exc.status, exc.code) from None


User = Annotated[CurrentUser, Depends(require_permission("alerts:write"))]
Service = Annotated[SubjectManagementService, Depends(get_service)]
router = APIRouter(tags=["socai2-subject-management"])


async def apply(service, user, kind, targets, changes, operation_key, *, feedback=False):
    if user.workload_service:
        raise HTTPException(403, "subject_user_actor_required")
    try:
        return await service.apply(user.tenant_id, kind, targets, changes, operation_key,
            Actor(user_id=user.user_id, name=user.email), feedback=feedback)
    except StoreError as exc:
        raise HTTPException(exc.status, exc.code) from None


@router.post("/alerts/feedback-batch", response_model=SubjectBatchReceipt)
async def feedback_batch(body: AlertFeedbackBatch, user: User, service: Service):
    return await apply(service, user, "alerts", body.items, body.feedback, body.operation_key, feedback=True)


@router.post("/alerts/management-batch", response_model=SubjectBatchReceipt)
async def manage_alerts(body: AlertManagementBatch, user: User, service: Service):
    return await apply(service, user, "alerts", body.items, body.changes, body.operation_key)


@router.post("/incidents/management-batch", response_model=SubjectBatchReceipt)
async def manage_incidents(body: IncidentManagementBatch, user: User, service: Service):
    return await apply(service, user, "incidents", body.items, body.changes, body.operation_key)


@router.post("/alerts/{alert_id}/feedback", response_model=SubjectMutationReceipt)
async def feedback(alert_id: UUID, body: AlertFeedback, user: User, service: Service):
    result = await apply(service, user, "alerts", [SelectedSubject(id=alert_id,
        expected_row_version=body.expected_row_version)], body, body.operation_key, feedback=True)
    return result.items[0]


@router.patch("/alerts/{alert_id}/management", response_model=SubjectMutationReceipt)
async def manage_alert(alert_id: UUID, body: AlertManagementUpdate, user: User, service: Service):
    result = await apply(service, user, "alerts", [SelectedSubject(id=alert_id,
        expected_row_version=body.expected_row_version)], body, body.operation_key)
    return result.items[0]


@router.patch("/incidents/{incident_id}/management", response_model=SubjectMutationReceipt)
async def manage_incident(incident_id: UUID, body: IncidentManagementUpdate, user: User, service: Service):
    result = await apply(service, user, "incidents", [SelectedSubject(id=incident_id,
        expected_row_version=body.expected_row_version)], body, body.operation_key)
    return result.items[0]
