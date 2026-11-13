"""Bind external use cases to the existing investigation core, without HTTP calls.

Only this adapter knows concrete services, database factories and feature flags.
Internal workers continue to call the core directly and never import this package.
"""

from uuid import uuid5

from app.core.config import settings
from app.db.case_database import get_case_write_sessions
from app.db.database import AsyncSessionLocal
from app.socai2.baseline_store import StoreError
from app.socai2.case_management import manage_case, read_management
from app.socai2.case_service import CaseService
from app.socai2.grouping_summary import GroupingSummaryService
from app.socai2.human_task_service import HumanTaskService
from app.socai2.list_export import ListExportService
from app.socai2.page_reader import PageReadService
from app.socai2.stage_reader import StageReadService
from app.socai2.stage_results import StageResultService
from app.socai2.subject_management import SubjectManagementService

from investigation_http.ports import (
    AnalysisReads,
    CaseOperations,
    PageReads,
    StageExecution,
    SubjectManagement,
    TaskOperations,
)


class CaseBackend(CaseService):
    async def read_management(self, tenant_id, case_id):
        return await read_management(self, tenant_id, case_id)

    async def manage_case(self, tenant_id, case_id, request, actor, *, action):
        return await manage_case(
            self, tenant_id, case_id, request, actor, action=action
        )


class ExecutionBackend:
    def __init__(self, sessions):
        self._execution = StageResultService(sessions)
        self._reader = StageReadService(sessions)

    async def execute(self, tenant_id, kind, identity, operation_key, *, requested_by):
        action = (
            self._execution.execute_alert
            if kind == "alert_basic"
            else self._execution.execute_incident
        )
        await action(tenant_id, identity, operation_key, requested_by=requested_by)
        run_id = uuid5(tenant_id, "socai2.stage:" + str(operation_key))
        return await self._reader.read_entry(tenant_id, kind, identity, run_id)


def require_case_enabled():
    if not settings.SOCAI2_CASE_API_ENABLED:
        raise StoreError("socai2_case_api_not_enabled", 503)


def case_sessions(method):
    if not (
        settings.SOCAI2_CASE_API_ENABLED
        or method == "GET"
        and settings.SOCAI2_PAGE_READ_ENABLED
    ):
        raise StoreError("socai2_case_api_not_enabled", 503)
    return AsyncSessionLocal if method == "GET" else get_case_write_sessions()


def cases(method) -> CaseOperations:
    return CaseBackend(case_sessions(method))


def tasks(method) -> TaskOperations:
    return HumanTaskService(case_sessions(method))


def pages() -> PageReads:
    if not settings.SOCAI2_PAGE_READ_ENABLED:
        raise StoreError("socai2_page_read_not_enabled", 503)
    return PageReadService(AsyncSessionLocal)


def analysis() -> AnalysisReads:
    if not settings.SOCAI2_ANALYSIS_READ_ENABLED:
        raise StoreError("socai2_analysis_read_not_enabled", 503)
    return StageReadService(AsyncSessionLocal)


def subjects() -> SubjectManagement:
    if not settings.SOCAI2_CASE_API_ENABLED:
        raise StoreError("socai2_subject_write_not_enabled", 503)
    return SubjectManagementService(get_case_write_sessions())


def execution() -> StageExecution:
    if not settings.SOCAI2_STAGE_EXECUTION_ENABLED:
        raise StoreError("socai2_stage_execution_not_enabled", 503)
    return ExecutionBackend(get_case_write_sessions())


class ExportBackend(ListExportService):
    async def read(self, tenant, kind, query):
        if kind == "cases":
            case_sessions("GET")
        elif not settings.SOCAI2_PAGE_READ_ENABLED:
            raise StoreError("socai2_page_read_not_enabled", 503)
        return await super().read(tenant, kind, query)


def exports():
    return ExportBackend(AsyncSessionLocal)


def grouping():
    if not settings.SOCAI2_PAGE_READ_ENABLED:
        raise StoreError("socai2_page_read_not_enabled", 503)
    return GroupingSummaryService(AsyncSessionLocal)
