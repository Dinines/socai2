"""Frozen public business DTOs plus HTTP-only request bodies. No persistence/execution.

Business DTOs remain shared with callers that execute without HTTP.
"""

from uuid import UUID

from app.socai2.baseline_contracts import (
    Actor,
    Contract,
    Start,
)
from app.socai2.baseline_store import (
    StoreError,
)
from app.socai2.case_ai_contracts import (
    AdoptCaseAIResult,
    AIUnavailable,
    AskCaseAI,
    SaveCaseAIAnswer,
)
from app.socai2.case_contracts import (
    ArtifactContent,
    AssociationReceipt,
    AssociationRequest,
    BaselinePreparation,
    CaseCreate,
    CaseDetail,
    CaseMetric,
    CaseQueuePage,
    CaseQueueQuery,
    HistoryPage,
    MemberChange,
    MoveMembers,
    MoveReceipt,
    MutationReceipt,
    PrepareBaseline,
    ResultDetail,
    RunDetail,
)
from app.socai2.case_data_contracts import (
    CaseDataReceipt,
    CaseDataUpdate,
    CasePageData,
    Classification,
    EvidencePublish,
)
from app.socai2.case_management_contracts import (
    CaseCloseRequest,
    CaseLifecycleRequest,
    CaseManagementReceipt,
    CaseManagementUpdate,
    CaseManagementView,
)
from app.socai2.enums import (
    AlertStatus,
    AssignmentState,
    Severity,
    WorkStatus,
)
from app.socai2.human_task_contracts import (
    TaskCreate,
    TaskEdit,
    TaskMutation,
    TaskPage,
    TaskRevisionPage,
    TaskRevisionView,
    TaskView,
)
from app.socai2.list_query_contracts import (
    AlertListQuery,
    AlertSort,
    CaseSort,
    IncidentListQuery,
    IncidentSort,
    SortOrder,
)
from app.socai2.page_contracts import (
    ContentView,
    RecordPage,
    Section,
    Subject,
    SubjectPage,
    SubjectView,
    TraceView,
)
from app.socai2.stage_read_contracts import (
    StageEntry,
    StagePage,
)
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


class ExecuteStage(Contract):
    operation_key: UUID


__all__ = [
    "AIUnavailable",
    "Actor",
    "AdoptCaseAIResult",
    "AlertFeedback",
    "AlertFeedbackBatch",
    "AlertListQuery",
    "AlertManagementBatch",
    "AlertManagementUpdate",
    "AlertSort",
    "AlertStatus",
    "ArtifactContent",
    "AskCaseAI",
    "AssignmentState",
    "AssociationReceipt",
    "AssociationRequest",
    "BaselinePreparation",
    "CaseCloseRequest",
    "CaseCreate",
    "CaseDataReceipt",
    "CaseDataUpdate",
    "CaseDetail",
    "CaseLifecycleRequest",
    "CaseManagementReceipt",
    "CaseManagementUpdate",
    "CaseManagementView",
    "CaseMetric",
    "CasePageData",
    "CaseQueuePage",
    "CaseQueueQuery",
    "CaseSort",
    "Classification",
    "ContentView",
    "Contract",
    "EvidencePublish",
    "ExecuteStage",
    "HistoryPage",
    "IncidentListQuery",
    "IncidentManagementBatch",
    "IncidentManagementUpdate",
    "IncidentSort",
    "MemberChange",
    "MoveMembers",
    "MoveReceipt",
    "MutationReceipt",
    "PrepareBaseline",
    "RecordPage",
    "ResultDetail",
    "RunDetail",
    "SaveCaseAIAnswer",
    "Section",
    "SelectedSubject",
    "Severity",
    "SortOrder",
    "StageEntry",
    "StagePage",
    "Start",
    "StoreError",
    "Subject",
    "SubjectBatchReceipt",
    "SubjectMutationReceipt",
    "SubjectPage",
    "SubjectView",
    "TaskCreate",
    "TaskEdit",
    "TaskMutation",
    "TaskPage",
    "TaskRevisionPage",
    "TaskRevisionView",
    "TaskView",
    "TraceView",
    "WorkStatus",
]

# Existing public facts and read-only export payload for the CSV boundary.
from app.socai2.case_contracts import CaseView
from app.socai2.page_contracts import AlertFacts, IncidentFacts

__all__ += ["AlertFacts", "CaseView", "IncidentFacts"]

from app.socai2.grouping_contracts import GroupingQuery, GroupingSummary

__all__ += ["GroupingQuery", "GroupingSummary"]

from app.socai2.case_comment_contracts import (
    CaseCommentCreate,
    CaseCommentPage,
    CaseCommentView,
)

__all__ += ["CaseCommentCreate", "CaseCommentPage", "CaseCommentView"]
