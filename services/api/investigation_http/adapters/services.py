"""Bind external use cases to the existing investigation core, without HTTP calls.

Only this adapter knows concrete services, database factories and feature flags.
Internal workers continue to call the core directly and never import this package.
"""

from app.core.config import settings
from app.db.case_database import get_case_write_sessions
from app.db.database import AsyncSessionLocal
from app.socai2.alert_hosts import AlertHostService
from app.socai2.alert_review import AlertReviewService
from app.socai2.baseline_store import StoreError
from app.socai2.case_attachments import CaseAttachmentService
from app.socai2.case_comments import CaseCommentService
from app.socai2.case_management import manage_case, read_management
from app.socai2.case_service import CaseService
from app.socai2.exploration import ExplorationService
from app.socai2.exploration_state import ExplorationStateService
from app.socai2.grouping_summary import GroupingSummaryService
from app.socai2.human_task_service import HumanTaskService
from app.socai2.list_export import ListExportService
from app.socai2.page_reader import PageReadService
from app.socai2.stage_reader import StageReadService
from app.socai2.subject_management import SubjectManagementService

from investigation_http.adapters.analysis_submissions import AnalysisSubmissionBackend
from investigation_http.adapters.analysis_tasks import AnalysisTaskBackend
from investigation_http.adapters.case_allocation import (
    allocation_call,
    allocation_urls,
    member_change_urls,
    related_case_urls,
)
from investigation_http.adapters.case_investigations import CaseInvestigationBackend
from investigation_http.adapters.case_story import CaseStoryBackend
from investigation_http.adapters.run_directory import RunDirectoryBackend
from investigation_http.adapters.run_records import RunRecordBackend
from investigation_http.ports import (
    AnalysisReads,
    CaseOperations,
    PageReads,
    SubjectManagement,
    TaskOperations,
)


def lake_reads():
    from investigation_http.adapters.lake import LakeReadBackend
    return LakeReadBackend()


class CaseBackend(CaseService):
    async def create_case(self, tenant_id, request, *, actor):
        receipt = await allocation_call(super().create_case(tenant_id, request, actor=actor))
        return allocation_urls(receipt)

    async def associate(self, tenant_id, case_id, request, *, actor):
        receipt = await allocation_call(super().associate(tenant_id, case_id, request, actor=actor))
        return allocation_urls(receipt)

    async def change_members(self, tenant_id, case_id, request, *, actor):
        receipt = await allocation_call(super().change_members(tenant_id, case_id, request, actor=actor))
        return member_change_urls(receipt)

    async def move_members(self, tenant_id, case_id, request, *, actor):
        receipt = await allocation_call(super().move_members(tenant_id, case_id, request, actor=actor))
        return member_change_urls(receipt)

    async def read_related_cases(self, tenant_id, case_id, *, limit=None, cursor=None):
        page = await allocation_call(super().read_related_cases(tenant_id, case_id, limit=limit, cursor=cursor))
        return related_case_urls(page)

    async def read_management(self, tenant_id, case_id):
        return await read_management(self, tenant_id, case_id)

    async def manage_case(self, tenant_id, case_id, request, actor, *, action):
        return await manage_case(
            self, tenant_id, case_id, request, actor, action=action
        )


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


def comments(method):
    return CaseCommentService(case_sessions(method))


def attachments(method):
    return CaseAttachmentService(case_sessions(method))


def story():
    return CaseStoryBackend(case_sessions("GET"))


def case_investigation_history():
    return CaseInvestigationBackend(case_sessions("GET"))


def exploration():
    return ExplorationService(case_sessions("GET"))


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


def run_records():
    if not settings.SOCAI2_ANALYSIS_READ_ENABLED:
        raise StoreError("service_unavailable", 503)
    return RunRecordBackend(AsyncSessionLocal)


def run_directory():
    if not settings.SOCAI2_ANALYSIS_READ_ENABLED:
        raise StoreError("service_unavailable", 503)
    return RunDirectoryBackend(AsyncSessionLocal)


def analysis_tasks():
    if not settings.SOCAI2_ANALYSIS_READ_ENABLED:
        raise StoreError("service_unavailable", 503)
    return AnalysisTaskBackend(AsyncSessionLocal)


def analysis_submissions():
    return AnalysisSubmissionBackend(case_sessions("POST"))


def subjects() -> SubjectManagement:
    if not settings.SOCAI2_CASE_API_ENABLED:
        raise StoreError("socai2_subject_write_not_enabled", 503)
    return SubjectManagementService(get_case_write_sessions())


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


def exploration_state(method):
    return ExplorationStateService(case_sessions(method))


def alert_review():
    if not settings.SOCAI2_PAGE_READ_ENABLED:
        raise StoreError("socai2_page_read_not_enabled", 503)
    return AlertReviewService(AsyncSessionLocal)


def alert_hosts():
    if not settings.SOCAI2_PAGE_READ_ENABLED:
        raise StoreError("socai2_page_read_not_enabled", 503)
    return AlertHostService(AsyncSessionLocal)
