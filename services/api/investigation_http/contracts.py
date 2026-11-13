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
    "AlertManagementBatch",
    "AlertManagementUpdate",
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
    "Classification",
    "ContentView",
    "Contract",
    "EvidencePublish",
    "ExecuteStage",
    "HistoryPage",
    "IncidentManagementBatch",
    "IncidentManagementUpdate",
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
