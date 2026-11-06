# Generated from the reviewed data contract.
from enum import StrEnum

class Severity(StrEnum):
    INFO = 'info'
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'

class AlertStatus(StrEnum):
    NEW = 'new'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    UNKNOWN = 'unknown'

class WorkStatus(StrEnum):
    NEW = 'new'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'
    UNKNOWN = 'unknown'

class Disposition(StrEnum):
    TRUE_POSITIVE = 'true_positive'
    FALSE_POSITIVE = 'false_positive'
    BENIGN = 'benign'
    NEEDS_REVIEW = 'needs_review'

class AssignmentState(StrEnum):
    UNASSIGNED = 'unassigned'
    ASSIGNED = 'assigned'
    UNRESOLVED = 'unresolved'

class ScoreState(StrEnum):
    NOT_PROVIDED = 'not_provided'
    NOT_COMPUTED = 'not_computed'
    DISABLED = 'disabled'
    FAILED = 'failed'
    AVAILABLE = 'available'
    LEGACY_UNVERIFIED = 'legacy_unverified'

class TimeSource(StrEnum):
    SOURCE = 'source'
    DERIVED_SOURCE = 'derived_source'
    UNKNOWN = 'unknown'

class RunKind(StrEnum):
    ALERT_BASIC = 'alert_basic'
    INCIDENT_DIAGNOSIS = 'incident_diagnosis'
    BASELINE = 'baseline'
    AI_QUESTION = 'ai_question'

class RunState(StrEnum):
    PENDING_UPDATE = 'pending_update'
    RUNNING = 'running'
    UNKNOWN = 'unknown'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

class RunTrigger(StrEnum):
    INGESTED = 'ingested'
    REFRESH = 'refresh'
    CASE_CREATED = 'case_created'
    MEMBERS_CHANGED = 'members_changed'
    MANUAL = 'manual'
    QUESTION = 'question'
    RETRY = 'retry'

class Delivery(StrEnum):
    NONE = 'none'
    PARTIAL = 'partial'
    COMPLETE = 'complete'
    UNKNOWN = 'unknown'

class StepKind(StrEnum):
    STAGE = 'stage'
    MODEL = 'model'
    TOOL = 'tool'
    GRAPH = 'graph'
    RENDER = 'render'

class StepState(StrEnum):
    PLANNED = 'planned'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    TIMEOUT = 'timeout'
    CANCELLED = 'cancelled'
    SKIPPED = 'skipped'
    UNKNOWN = 'unknown'

class ReadState(StrEnum):
    NOT_READ = 'not_read'
    READ = 'read'
    MISSING = 'missing'
    DENIED = 'denied'
    FAILED = 'failed'

class AnalysisState(StrEnum):
    NOT_ANALYZED = 'not_analyzed'
    ANALYZED = 'analyzed'
    UNRESOLVED = 'unresolved'
    EXCLUDED = 'excluded'

class ResultKind(StrEnum):
    BASELINE = 'baseline'
    AI_SAVED = 'ai_saved'

class Origin(StrEnum):
    MODEL = 'model'
    HUMAN = 'human'
    SYSTEM = 'system'
    LEGACY = 'legacy'

class Validation(StrEnum):
    NOT_CHECKED = 'not_checked'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    SYSTEM_ONLY = 'system_only'
    LEGACY_UNVERIFIED = 'legacy_unverified'

class ConclusionState(StrEnum):
    SUPPORTED = 'supported'
    UNCERTAIN = 'uncertain'
    UNAVAILABLE = 'unavailable'

class TaskState(StrEnum):
    NOT_STARTED = 'not_started'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

class MessageRole(StrEnum):
    USER = 'user'
    ASSISTANT = 'assistant'

class MessageState(StrEnum):
    ACCEPTED = 'accepted'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    UNKNOWN = 'unknown'

class ActorType(StrEnum):
    USER = 'user'
    SERVICE = 'service'
    MODEL = 'model'
    LEGACY_UNKNOWN = 'legacy_unknown'

class ObjectType(StrEnum):
    HOST = 'host'
    USER = 'user'
    IP = 'ip'
    DOMAIN = 'domain'
    URL = 'url'
    FILE = 'file'
    HASH = 'hash'
    PROCESS = 'process'
    EMAIL = 'email'
    APPLICATION = 'application'
    CLOUD_RESOURCE = 'cloud_resource'
    TECHNIQUE = 'technique'
    OTHER = 'other'

class ObjectRole(StrEnum):
    ENTITY = 'entity'
    IOC = 'ioc'
    BOTH = 'both'

class AssetMatch(StrEnum):
    MATCHED = 'matched'
    AMBIGUOUS = 'ambiguous'
    NOT_FOUND = 'not_found'
    NOT_CHECKED = 'not_checked'

class RefKind(StrEnum):
    SOURCE_EVENT = 'source_event'
    THRESHOLD_CANDIDATE = 'threshold_candidate'
    SEQUENCE_CANDIDATE = 'sequence_candidate'
    RELATED_RECORD = 'related_record'

class MembershipSource(StrEnum):
    FUSION = 'fusion'
    MANUAL = 'manual'
    INCIDENT_LINK = 'incident_link'
    MOVE = 'move'
    LEGACY = 'legacy'

class MaterialState(StrEnum):
    COMPLETE = 'complete'
    TRUNCATED = 'truncated'
    SUMMARY_ONLY = 'summary_only'
    UNAVAILABLE = 'unavailable'

class DiagnosisState(StrEnum):
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    UNKNOWN = 'unknown'

class ChangeKind(StrEnum):
    INITIAL = 'initial'
    UNCHANGED = 'unchanged'
    EXPANDED = 'expanded'
    REVISED = 'revised'
    WITHDRAWN = 'withdrawn'
    NOT_COMPARABLE = 'not_comparable'

class ApprovalRequirement(StrEnum):
    REQUIRED = 'required'
    NOT_REQUIRED = 'not_required'
    UNKNOWN = 'unknown'

class ActivityResult(StrEnum):
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    SKIPPED = 'skipped'

class ArtifactKind(StrEnum):
    INPUT_SNAPSHOT = 'input_snapshot'
    MODEL_REQUEST = 'model_request'
    MODEL_RESPONSE = 'model_response'
    TOOL_REQUEST = 'tool_request'
    TOOL_RESPONSE = 'tool_response'
    DOMAIN_ANALYSIS = 'domain_analysis'
    DEEP_ANALYSIS = 'deep_analysis'
    ATTACK_CHAIN = 'attack_chain'
    ATTACK_PATH = 'attack_path'
    ALERT_GRAPH = 'alert_graph'
    REPORT_JSON = 'report_json'
    REPORT_MARKDOWN = 'report_markdown'
    ATTACHMENT = 'attachment'
    SOURCE_SNAPSHOT = 'source_snapshot'
    HANDOFF = 'handoff'
    QUERY_PLAN = 'query_plan'
    ALERT_EXPLANATION = 'alert_explanation'
    CASE_EVIDENCE_INDEX = 'case_evidence_index'

class AssessmentKind(StrEnum):
    TRIAGE = 'triage'
    HUMAN_FEEDBACK = 'human_feedback'

class ScopeKind(StrEnum):
    WHOLE_CASE = 'whole_case'
    SELECTED_ALERTS = 'selected_alerts'
    EXPLICIT_OBJECTS = 'explicit_objects'

class CaseClassification(StrEnum):
    TRUE_POSITIVE = 'true_positive'
    INFORMATIONAL = 'informational'
    FALSE_POSITIVE = 'false_positive'

ENUM_VALUES = {
    'severity': tuple(v.value for v in Severity),
    'alert_status': tuple(v.value for v in AlertStatus),
    'work_status': tuple(v.value for v in WorkStatus),
    'disposition': tuple(v.value for v in Disposition),
    'assignment_state': tuple(v.value for v in AssignmentState),
    'score_state': tuple(v.value for v in ScoreState),
    'time_source': tuple(v.value for v in TimeSource),
    'run_kind': tuple(v.value for v in RunKind),
    'run_state': tuple(v.value for v in RunState),
    'run_trigger': tuple(v.value for v in RunTrigger),
    'delivery': tuple(v.value for v in Delivery),
    'step_kind': tuple(v.value for v in StepKind),
    'step_state': tuple(v.value for v in StepState),
    'read_state': tuple(v.value for v in ReadState),
    'analysis_state': tuple(v.value for v in AnalysisState),
    'result_kind': tuple(v.value for v in ResultKind),
    'origin': tuple(v.value for v in Origin),
    'validation': tuple(v.value for v in Validation),
    'conclusion_state': tuple(v.value for v in ConclusionState),
    'task_state': tuple(v.value for v in TaskState),
    'message_role': tuple(v.value for v in MessageRole),
    'message_state': tuple(v.value for v in MessageState),
    'actor_type': tuple(v.value for v in ActorType),
    'object_type': tuple(v.value for v in ObjectType),
    'object_role': tuple(v.value for v in ObjectRole),
    'asset_match': tuple(v.value for v in AssetMatch),
    'ref_kind': tuple(v.value for v in RefKind),
    'membership_source': tuple(v.value for v in MembershipSource),
    'material_state': tuple(v.value for v in MaterialState),
    'diagnosis_state': tuple(v.value for v in DiagnosisState),
    'change_kind': tuple(v.value for v in ChangeKind),
    'approval_requirement': tuple(v.value for v in ApprovalRequirement),
    'activity_result': tuple(v.value for v in ActivityResult),
    'artifact_kind': tuple(v.value for v in ArtifactKind),
    'assessment_kind': tuple(v.value for v in AssessmentKind),
    'scope_kind': tuple(v.value for v in ScopeKind),
    'case_classification': tuple(v.value for v in CaseClassification),
}
