"""HTTP dependency assembly. Routes receive use cases, never database sessions."""

from fastapi import Request

from investigation_http.adapters import services
from investigation_http.adapters.identity import CurrentUser, require_permission
from investigation_http.errors import provide

__all__ = [
    "CurrentUser",
    "analysis_service",
    "attachment_service",
    "case_service",
    "comment_service",
    "execution_service",
    "export_service",
    "grouping_service",
    "page_service",
    "require_case_enabled",
    "require_permission",
    "subject_service",
    "task_service",
]


async def case_service(request: Request):
    return provide(services.cases, request.method)


async def comment_service(request: Request):
    return provide(services.comments, request.method)


async def attachment_service(request: Request):
    return provide(services.attachments, request.method)


async def task_service(request: Request):
    return provide(services.tasks, request.method)


def page_service():
    return provide(services.pages)


def analysis_service():
    return provide(services.analysis)


def subject_service():
    return provide(services.subjects)


def execution_service():
    return provide(services.execution)


def require_case_enabled():
    return provide(services.require_case_enabled)


def export_service():
    return provide(services.exports)


def grouping_service():
    return provide(services.grouping)
