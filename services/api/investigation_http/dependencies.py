"""HTTP dependency assembly. Routes receive use cases, never database sessions."""

from fastapi import HTTPException, Request

from investigation_http.adapters import services
from investigation_http.adapters.identity import CurrentUser, require_permission
from investigation_http.contracts import StoreError
from investigation_http.errors import provide, record_error
from investigation_http.lake_contracts import LakeReadError

__all__ = [
    "CurrentUser",
    "analysis_service",
    "attachment_service",
    "case_investigation_history_service",
    "case_service",
    "comment_service",
    "exploration_service",
    "export_service",
    "grouping_service",
    "page_service",
    "require_case_enabled",
    "require_permission",
    "story_service",
    "subject_service",
    "task_service",
]


async def case_service(request: Request):
    return provide(services.cases, request.method)


async def comment_service(request: Request):
    return provide(services.comments, request.method)


async def attachment_service(request: Request):
    return provide(services.attachments, request.method)


def story_service():
    return provide(services.story)


def case_investigation_history_service():
    try:
        return services.case_investigation_history()
    except StoreError as exc:
        raise record_error(exc.code, exc.status) from exc


def exploration_service():
    return provide(services.exploration)


async def task_service(request: Request):
    return provide(services.tasks, request.method)


def page_service():
    return provide(services.pages)


def analysis_service():
    return provide(services.analysis)


def subject_service():
    return provide(services.subjects)


def require_case_enabled():
    return provide(services.require_case_enabled)


def export_service():
    return provide(services.exports)


def grouping_service():
    return provide(services.grouping)


async def exploration_state_service(request: Request):
    return provide(services.exploration_state, request.method)


def alert_review_service():
    return provide(services.alert_review)


def alert_host_service():
    return provide(services.alert_hosts)


def run_record_service():
    try:
        return services.run_records()
    except StoreError as exc:
        raise record_error("service_unavailable", 503) from exc


def lake_read_service():
    try:
        return services.lake_reads()
    except LakeReadError as exc:
        raise HTTPException(exc.status, {"code": exc.code, "state": exc.state}) from None


def run_directory_service():
    try:
        return services.run_directory()
    except StoreError as exc:
        raise record_error("service_unavailable", 503) from exc


def analysis_task_service():
    try:
        return services.analysis_tasks()
    except StoreError as exc:
        raise record_error("service_unavailable", 503) from exc


def analysis_submission_service():
    try:
        return services.analysis_submissions()
    except StoreError as exc:
        raise record_error("service_unavailable", 503) from exc
