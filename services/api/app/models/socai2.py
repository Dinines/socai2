"""Generated socai2 ORM. Explicit opt-in; does not switch existing writers."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID as PyUUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKeyConstraint,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, CHAR, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Socai2Base(DeclarativeBase):
    pass

class Alerts(Socai2Base):
    __tablename__ = 'alerts'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_namespace: Mapped[str] = mapped_column(Text, nullable=False)
    source_alert_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    vendor_alert_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    connector_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    connector_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_vendor: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_identity_key: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_time: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    event_time_source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    first_seen_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    source_updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    business_updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    handling_status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'new'"))
    disposition: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    assignment_state: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unassigned'"))
    owner_source_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'::text[]"))
    priority_value: Mapped[Decimal | None] = mapped_column(Numeric(5,2), nullable=True)
    priority_state: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'not_provided'"))
    priority_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority_basis: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    closed_by: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reopened_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    latest_material_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    latest_triage_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    latest_feedback_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    row_version: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text('1'))
    latest_explanation_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'source_namespace', 'source_identity_key', name='alerts_source_identity'),
        CheckConstraint('length(btrim("source_namespace")) > 0', name='alerts_source_namespace_nonblank'),
        CheckConstraint('length(btrim("source_identity_key")) > 0', name='alerts_source_identity_key_nonblank'),
        CheckConstraint('length(btrim("title")) > 0', name='alerts_title_nonblank'),
        CheckConstraint('"severity" IN (\'info\',\'low\',\'medium\',\'high\',\'critical\')', name='alerts_severity_enum'),
        CheckConstraint('"event_time_source" IN (\'source\',\'derived_source\',\'unknown\')', name='alerts_event_time_source_enum'),
        CheckConstraint('"handling_status" IN (\'new\',\'in_progress\',\'completed\',\'unknown\')', name='alerts_handling_status_enum'),
        CheckConstraint('"disposition" IN (\'true_positive\',\'false_positive\',\'benign\',\'needs_review\')', name='alerts_disposition_enum'),
        CheckConstraint('"assignment_state" IN (\'unassigned\',\'assigned\',\'unresolved\')', name='alerts_assignment_state_enum'),
        CheckConstraint('"priority_state" IN (\'not_provided\',\'not_computed\',\'disabled\',\'failed\',\'available\',\'legacy_unverified\')', name='alerts_priority_state_enum'),
        CheckConstraint('jsonb_typeof("priority_basis") = \'object\'', name='alerts_priority_basis_json_type'),
        CheckConstraint('"row_version" > 0', name='alerts_row_version_range'),
        CheckConstraint("(assignment_state='assigned') = (owner_id IS NOT NULL)", name='alerts_assignment'),
        CheckConstraint("assignment_state <> 'unresolved' OR nullif(btrim(owner_source_value),'') IS NOT NULL", name='alerts_unresolved_owner'),
        CheckConstraint("(priority_state='available' AND priority_value IS NOT NULL AND priority_value BETWEEN 0 AND 100 AND nullif(btrim(priority_source),'') IS NOT NULL) OR (priority_state<>'available' AND priority_value IS NULL)", name='alerts_priority'),
        CheckConstraint("(event_time_source='unknown') = (event_time IS NULL)", name='alerts_event_time'),
        CheckConstraint('first_seen_at IS NULL OR last_seen_at IS NULL OR first_seen_at<=last_seen_at', name='alerts_time_order'),
        ForeignKeyConstraint(['tenant_id', 'latest_material_id'], ['socai2.alert_materials.tenant_id', 'socai2.alert_materials.id'], name='alerts_latest_material_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'latest_triage_id'], ['socai2.alert_assessments.tenant_id', 'socai2.alert_assessments.id'], name='alerts_latest_triage_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'latest_feedback_id'], ['socai2.alert_assessments.tenant_id', 'socai2.alert_assessments.id'], name='alerts_latest_feedback_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'latest_explanation_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.id'], name='alerts_latest_explanation_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'id', 'latest_material_id'], ['socai2.alert_materials.tenant_id', 'socai2.alert_materials.alert_id', 'socai2.alert_materials.id'], name='alerts_latest_material_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'id', 'latest_triage_id'], ['socai2.alert_assessments.tenant_id', 'socai2.alert_assessments.alert_id', 'socai2.alert_assessments.id'], name='alerts_latest_triage_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'id', 'latest_feedback_id'], ['socai2.alert_assessments.tenant_id', 'socai2.alert_assessments.alert_id', 'socai2.alert_assessments.id'], name='alerts_latest_feedback_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'id', 'latest_explanation_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.alert_id', 'socai2.artifacts.id'], name='alerts_latest_explanation_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class AlertMaterials(Socai2Base):
    __tablename__ = 'alert_materials'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alert_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    received_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    source_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    ocsf_json: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    detection: Mapped[object] = mapped_column(JSONB, nullable=False)
    enrichment: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    source_scope: Mapped[object] = mapped_column(JSONB, nullable=False)
    material_state: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    retention: Mapped[object] = mapped_column(JSONB, nullable=False)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'alert_id', 'id', name='alert_materials_scope_key_0'),
        UniqueConstraint('tenant_id', 'alert_id', 'revision', name='alert_materials_business_key'),
        CheckConstraint('"revision" > 0', name='alert_materials_revision_range'),
        CheckConstraint('jsonb_typeof("detection") = \'object\'', name='alert_materials_detection_json_type'),
        CheckConstraint('jsonb_typeof("enrichment") = \'object\'', name='alert_materials_enrichment_json_type'),
        CheckConstraint('jsonb_typeof("source_scope") = \'object\'', name='alert_materials_source_scope_json_type'),
        CheckConstraint('"material_state" IN (\'complete\',\'truncated\',\'summary_only\',\'unavailable\')', name='alert_materials_material_state_enum'),
        CheckConstraint('"sha256" ~ \'^[0-9a-f]{64}$\'', name='alert_materials_sha256_sha'),
        CheckConstraint('jsonb_typeof("retention") = \'object\'', name='alert_materials_retention_json_type'),
        ForeignKeyConstraint(['tenant_id', 'alert_id'], ['socai2.alerts.tenant_id', 'socai2.alerts.id'], name='alert_materials_alert_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class AlertSourceRefs(Socai2Base):
    __tablename__ = 'alert_source_refs'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alert_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    material_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_namespace: Mapped[str] = mapped_column(Text, nullable=False)
    source_event_id: Mapped[str] = mapped_column(Text, nullable=False)
    relation_kind: Mapped[str] = mapped_column(Text, nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    source_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'material_id', 'source_namespace', 'source_event_id', 'relation_kind', name='alert_source_refs_business_key'),
        CheckConstraint('length(btrim("source_namespace")) > 0', name='alert_source_refs_source_namespace_nonblank'),
        CheckConstraint('"relation_kind" IN (\'source_event\',\'threshold_candidate\',\'sequence_candidate\',\'related_record\')', name='alert_source_refs_relation_kind_enum'),
        ForeignKeyConstraint(['tenant_id', 'alert_id'], ['socai2.alerts.tenant_id', 'socai2.alerts.id'], name='alert_source_refs_alert_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'material_id'], ['socai2.alert_materials.tenant_id', 'socai2.alert_materials.id'], name='alert_source_refs_material_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'alert_id', 'material_id'], ['socai2.alert_materials.tenant_id', 'socai2.alert_materials.alert_id', 'socai2.alert_materials.id'], name='alert_source_refs_material_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class AlertObjects(Socai2Base):
    __tablename__ = 'alert_objects'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alert_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    material_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    object_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    object_role: Mapped[str] = mapped_column(Text, nullable=False)
    namespace: Mapped[str] = mapped_column(Text, nullable=False)
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[str] = mapped_column(Text, nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    attributes: Mapped[object] = mapped_column(JSONB, nullable=False)
    asset_match_state: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'not_checked'"))
    asset_ref: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    match_basis: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'material_id', 'object_key', 'source_path', name='alert_objects_business_key'),
        CheckConstraint('length(btrim("object_key")) > 0', name='alert_objects_object_key_nonblank'),
        CheckConstraint('"object_type" IN (\'host\',\'user\',\'ip\',\'domain\',\'url\',\'file\',\'hash\',\'process\',\'email\',\'application\',\'cloud_resource\',\'technique\',\'other\')', name='alert_objects_object_type_enum'),
        CheckConstraint('"object_role" IN (\'entity\',\'ioc\',\'both\')', name='alert_objects_object_role_enum'),
        CheckConstraint('length(btrim("namespace")) > 0', name='alert_objects_namespace_nonblank'),
        CheckConstraint('length(btrim("raw_value")) > 0', name='alert_objects_raw_value_nonblank'),
        CheckConstraint('length(btrim("normalized_value")) > 0', name='alert_objects_normalized_value_nonblank'),
        CheckConstraint('jsonb_typeof("attributes") = \'object\'', name='alert_objects_attributes_json_type'),
        CheckConstraint('"asset_match_state" IN (\'matched\',\'ambiguous\',\'not_found\',\'not_checked\')', name='alert_objects_asset_match_state_enum'),
        CheckConstraint('jsonb_typeof("asset_ref") = \'object\'', name='alert_objects_asset_ref_json_type'),
        CheckConstraint('jsonb_typeof("match_basis") = \'object\'', name='alert_objects_match_basis_json_type'),
        CheckConstraint("object_type<>'other' OR nullif(btrim(source_type),'') IS NOT NULL", name='alert_objects_other_type'),
        CheckConstraint("asset_match_state<>'matched' OR (asset_ref IS NOT NULL AND match_basis IS NOT NULL)", name='alert_objects_asset_match'),
        ForeignKeyConstraint(['tenant_id', 'alert_id'], ['socai2.alerts.tenant_id', 'socai2.alerts.id'], name='alert_objects_alert_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'material_id'], ['socai2.alert_materials.tenant_id', 'socai2.alert_materials.id'], name='alert_objects_material_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'alert_id', 'material_id'], ['socai2.alert_materials.tenant_id', 'socai2.alert_materials.alert_id', 'socai2.alert_materials.id'], name='alert_objects_material_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class AlertAssessments(Socai2Base):
    __tablename__ = 'alert_assessments'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alert_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    input_material_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_run_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    legacy_execution_ref: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    verdict: Mapped[str | None] = mapped_column(Text, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(6,5), nullable=True)
    score_state: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'not_provided'"))
    recommendations: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    producer: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[object] = mapped_column(JSONB, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    operation_key: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'alert_id', 'id', name='alert_assessments_scope_key_0'),
        UniqueConstraint('tenant_id', 'operation_key', name='alert_assessments_business_key'),
        CheckConstraint('"kind" IN (\'triage\',\'human_feedback\')', name='alert_assessments_kind_enum'),
        CheckConstraint('jsonb_typeof("legacy_execution_ref") = \'object\'', name='alert_assessments_legacy_execution_ref_json_type'),
        CheckConstraint('"verdict" IN (\'true_positive\',\'false_positive\',\'benign\',\'needs_review\')', name='alert_assessments_verdict_enum'),
        CheckConstraint('"score_state" IN (\'not_provided\',\'not_computed\',\'disabled\',\'failed\',\'available\',\'legacy_unverified\')', name='alert_assessments_score_state_enum'),
        CheckConstraint('jsonb_typeof("recommendations") = \'array\'', name='alert_assessments_recommendations_json_type'),
        CheckConstraint('jsonb_typeof("actor") = \'object\'', name='alert_assessments_actor_json_type'),
        CheckConstraint('length(btrim("operation_key")) > 0', name='alert_assessments_operation_key_nonblank'),
        CheckConstraint("(score_state='available' AND confidence IS NOT NULL AND confidence BETWEEN 0 AND 1) OR (score_state<>'available' AND confidence IS NULL)", name='alert_assessments_confidence'),
        CheckConstraint("kind<>'human_feedback' OR confidence IS NULL", name='alert_assessments_human_no_score'),
        ForeignKeyConstraint(['tenant_id', 'alert_id'], ['socai2.alerts.tenant_id', 'socai2.alerts.id'], name='alert_assessments_alert_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'input_material_id'], ['socai2.alert_materials.tenant_id', 'socai2.alert_materials.id'], name='alert_assessments_input_material_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'source_run_id'], ['socai2.runs.tenant_id', 'socai2.runs.id'], name='alert_assessments_source_run_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'alert_id', 'input_material_id'], ['socai2.alert_materials.tenant_id', 'socai2.alert_materials.alert_id', 'socai2.alert_materials.id'], name='alert_assessments_input_material_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'alert_id', 'source_run_id'], ['socai2.runs.tenant_id', 'socai2.runs.alert_id', 'socai2.runs.id'], name='alert_assessments_source_run_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class Incidents(Socai2Base):
    __tablename__ = 'incidents'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_namespace: Mapped[str] = mapped_column(Text, nullable=False)
    source_incident_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    handling_status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'new'"))
    owner_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    assignment_state: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unassigned'"))
    owner_source_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'::text[]"))
    severity_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity_override_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    severity_override_by: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    priority_value: Mapped[Decimal | None] = mapped_column(Numeric(5,2), nullable=True)
    priority_state: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'not_provided'"))
    priority_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority_basis: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    resolved_by: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reopened_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    business_updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    latest_diagnosis_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    row_version: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text('1'))
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'source_namespace', 'source_incident_id', name='incidents_source_identity'),
        CheckConstraint('length(btrim("source_namespace")) > 0', name='incidents_source_namespace_nonblank'),
        CheckConstraint('length(btrim("source_incident_id")) > 0', name='incidents_source_incident_id_nonblank'),
        CheckConstraint('length(btrim("title")) > 0', name='incidents_title_nonblank'),
        CheckConstraint('"handling_status" IN (\'new\',\'in_progress\',\'resolved\',\'unknown\')', name='incidents_handling_status_enum'),
        CheckConstraint('"assignment_state" IN (\'unassigned\',\'assigned\',\'unresolved\')', name='incidents_assignment_state_enum'),
        CheckConstraint('"severity_override" IN (\'info\',\'low\',\'medium\',\'high\',\'critical\')', name='incidents_severity_override_enum'),
        CheckConstraint('"priority_state" IN (\'not_provided\',\'not_computed\',\'disabled\',\'failed\',\'available\',\'legacy_unverified\')', name='incidents_priority_state_enum'),
        CheckConstraint('jsonb_typeof("priority_basis") = \'object\'', name='incidents_priority_basis_json_type'),
        CheckConstraint('"row_version" > 0', name='incidents_row_version_range'),
        CheckConstraint("(assignment_state='assigned') = (owner_id IS NOT NULL)", name='incidents_assignment'),
        CheckConstraint("assignment_state <> 'unresolved' OR nullif(btrim(owner_source_value),'') IS NOT NULL", name='incidents_unresolved_owner'),
        CheckConstraint("(priority_state='available' AND priority_value IS NOT NULL AND priority_value BETWEEN 0 AND 100 AND nullif(btrim(priority_source),'') IS NOT NULL) OR (priority_state<>'available' AND priority_value IS NULL)", name='incidents_priority'),
        CheckConstraint("(severity_override IS NULL AND severity_override_reason IS NULL AND severity_override_at IS NULL AND severity_override_by IS NULL) OR (severity_override IS NOT NULL AND nullif(btrim(severity_override_reason),'') IS NOT NULL AND severity_override_at IS NOT NULL AND severity_override_by IS NOT NULL)", name='incidents_severity_override'),
        ForeignKeyConstraint(['tenant_id', 'latest_diagnosis_id'], ['socai2.incident_diagnoses.tenant_id', 'socai2.incident_diagnoses.id'], name='incidents_latest_diagnosis_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'id', 'latest_diagnosis_id'], ['socai2.incident_diagnoses.tenant_id', 'socai2.incident_diagnoses.incident_id', 'socai2.incident_diagnoses.id'], name='incidents_latest_diagnosis_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class IncidentAlerts(Socai2Base):
    __tablename__ = 'incident_alerts'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    incident_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alert_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    linked_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    membership_source: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_basis: Mapped[object] = mapped_column(JSONB, nullable=False)
    basis_version: Mapped[str] = mapped_column(Text, nullable=False)
    source_operation_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'alert_id', name='incident_alerts_business_key'),
        CheckConstraint('"membership_source" IN (\'fusion\',\'manual\',\'incident_link\',\'move\',\'legacy\')', name='incident_alerts_membership_source_enum'),
        CheckConstraint('jsonb_typeof("correlation_basis") = \'object\'', name='incident_alerts_correlation_basis_json_type'),
        ForeignKeyConstraint(['tenant_id', 'incident_id'], ['socai2.incidents.tenant_id', 'socai2.incidents.id'], name='incident_alerts_incident_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'alert_id'], ['socai2.alerts.tenant_id', 'socai2.alerts.id'], name='incident_alerts_alert_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class IncidentDiagnoses(Socai2Base):
    __tablename__ = 'incident_diagnoses'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    incident_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_run_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    open_questions: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    input_artifact_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    producer: Mapped[str] = mapped_column(Text, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    error: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'incident_id', 'id', name='incident_diagnoses_scope_key_0'),
        UniqueConstraint('tenant_id', 'incident_id', 'revision', name='incident_diagnoses_business_key'),
        UniqueConstraint('tenant_id', 'source_run_id', name='incident_diagnoses_run_key'),
        CheckConstraint('"revision" > 0', name='incident_diagnoses_revision_range'),
        CheckConstraint('"state" IN (\'running\',\'completed\',\'failed\',\'cancelled\',\'unknown\')', name='incident_diagnoses_state_enum'),
        CheckConstraint('jsonb_typeof("diagnosis") = \'object\'', name='incident_diagnoses_diagnosis_json_type'),
        CheckConstraint('jsonb_typeof("open_questions") = \'array\'', name='incident_diagnoses_open_questions_json_type'),
        CheckConstraint('"source_fingerprint" ~ \'^[0-9a-f]{64}$\'', name='incident_diagnoses_source_fingerprint_sha'),
        CheckConstraint('jsonb_typeof("error") = \'object\'', name='incident_diagnoses_error_json_type'),
        ForeignKeyConstraint(['tenant_id', 'incident_id'], ['socai2.incidents.tenant_id', 'socai2.incidents.id'], name='incident_diagnoses_incident_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'source_run_id'], ['socai2.runs.tenant_id', 'socai2.runs.id'], name='incident_diagnoses_source_run_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'input_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.id'], name='incident_diagnoses_input_artifact_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'incident_id', 'source_run_id'], ['socai2.runs.tenant_id', 'socai2.runs.incident_id', 'socai2.runs.id'], name='incident_diagnoses_source_run_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'incident_id', 'input_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.incident_id', 'socai2.artifacts.id'], name='incident_diagnoses_input_artifact_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class Cases(Socai2Base):
    __tablename__ = 'cases'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # Added by incremental migration 124; migration 123 remains a fixed baseline.
    source_namespace: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    handling_status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'new'"))
    severity: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    assignment_state: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unassigned'"))
    owner_source_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'::text[]"))
    priority_value: Mapped[Decimal | None] = mapped_column(Numeric(5,2), nullable=True)
    priority_state: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'not_provided'"))
    priority_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority_basis: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    scope_revision: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text('0'))
    current_assessment_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    classification: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    current_evidence_artifact_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    created_by: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    business_updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    resolved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    resolved_by: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reopened_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    row_version: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text('1'))
    legacy_ref: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        CheckConstraint('length(btrim("title")) > 0', name='cases_title_nonblank'),
        CheckConstraint("classification IN ('true_positive','informational','false_positive')", name='cases_classification_enum'),
        ForeignKeyConstraint(['tenant_id', 'id', 'current_evidence_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.case_id', 'socai2.artifacts.id'], name='cases_current_evidence_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        CheckConstraint('"handling_status" IN (\'new\',\'in_progress\',\'resolved\',\'unknown\')', name='cases_handling_status_enum'),
        CheckConstraint('"severity" IN (\'info\',\'low\',\'medium\',\'high\',\'critical\')', name='cases_severity_enum'),
        CheckConstraint('"assignment_state" IN (\'unassigned\',\'assigned\',\'unresolved\')', name='cases_assignment_state_enum'),
        CheckConstraint('"priority_state" IN (\'not_provided\',\'not_computed\',\'disabled\',\'failed\',\'available\',\'legacy_unverified\')', name='cases_priority_state_enum'),
        CheckConstraint('jsonb_typeof("priority_basis") = \'object\'', name='cases_priority_basis_json_type'),
        CheckConstraint('"scope_revision" >= 0', name='cases_scope_revision_range'),
        CheckConstraint('"row_version" > 0', name='cases_row_version_range'),
        CheckConstraint('jsonb_typeof("legacy_ref") = \'object\'', name='cases_legacy_ref_json_type'),
        CheckConstraint("(assignment_state='assigned') = (owner_id IS NOT NULL)", name='cases_assignment'),
        CheckConstraint("assignment_state <> 'unresolved' OR nullif(btrim(owner_source_value),'') IS NOT NULL", name='cases_unresolved_owner'),
        CheckConstraint("(priority_state='available' AND priority_value IS NOT NULL AND priority_value BETWEEN 0 AND 100 AND nullif(btrim(priority_source),'') IS NOT NULL) OR (priority_state<>'available' AND priority_value IS NULL)", name='cases_priority'),
        ForeignKeyConstraint(['tenant_id', 'current_assessment_id'], ['socai2.case_assessments.tenant_id', 'socai2.case_assessments.id'], name='cases_current_assessment_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'id', 'current_assessment_id'], ['socai2.case_assessments.tenant_id', 'socai2.case_assessments.case_id', 'socai2.case_assessments.id'], name='cases_current_assessment_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class CaseAlerts(Socai2Base):
    __tablename__ = 'case_alerts'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alert_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    added_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    added_by: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    membership_source: Mapped[str] = mapped_column(Text, nullable=False)
    source_operation_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'case_id', 'alert_id', name='case_alerts_business_key'),
        CheckConstraint('"membership_source" IN (\'fusion\',\'manual\',\'incident_link\',\'move\',\'legacy\')', name='case_alerts_membership_source_enum'),
        ForeignKeyConstraint(['tenant_id', 'case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='case_alerts_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'alert_id'], ['socai2.alerts.tenant_id', 'socai2.alerts.id'], name='case_alerts_alert_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class CaseIncidents(Socai2Base):
    __tablename__ = 'case_incidents'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    incident_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    linked_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    linked_by: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_operation_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'case_id', 'incident_id', name='case_incidents_business_key'),
        ForeignKeyConstraint(['tenant_id', 'case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='case_incidents_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'incident_id'], ['socai2.incidents.tenant_id', 'socai2.incidents.id'], name='case_incidents_incident_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class CaseAssessments(Socai2Base):
    __tablename__ = 'case_assessments'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    conclusion: Mapped[str] = mapped_column(Text, nullable=False)
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    validity: Mapped[str] = mapped_column(Text, nullable=False)
    scope_revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    formed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    adopted_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    adopted_by: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor: Mapped[object] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    operation_key: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'case_id', 'id', name='case_assessments_scope_key_0'),
        UniqueConstraint('tenant_id', 'case_id', 'revision', name='case_assessments_business_key'),
        UniqueConstraint('tenant_id', 'operation_key', name='case_assessments_operation_key'),
        CheckConstraint('"revision" > 0', name='case_assessments_revision_range'),
        CheckConstraint('"origin" IN (\'model\',\'human\',\'system\',\'legacy\')', name='case_assessments_origin_enum'),
        CheckConstraint('"validity" IN (\'not_checked\',\'accepted\',\'rejected\',\'system_only\',\'legacy_unverified\')', name='case_assessments_validity_enum'),
        CheckConstraint('"scope_revision" >= 0', name='case_assessments_scope_revision_range'),
        CheckConstraint('jsonb_typeof("actor") = \'object\'', name='case_assessments_actor_json_type'),
        CheckConstraint('length(btrim("operation_key")) > 0', name='case_assessments_operation_key_nonblank'),
        ForeignKeyConstraint(['tenant_id', 'case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='case_assessments_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class CaseAssessmentSources(Socai2Base):
    __tablename__ = 'case_assessment_sources'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assessment_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    result_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    task_revision_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    artifact_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        CheckConstraint('num_nonnulls(result_id,task_revision_id,artifact_id)=1', name='case_assessment_sources_one_source'),
        ForeignKeyConstraint(['tenant_id', 'case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='case_assessment_sources_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'assessment_id'], ['socai2.case_assessments.tenant_id', 'socai2.case_assessments.id'], name='case_assessment_sources_assessment_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'result_id'], ['socai2.results.tenant_id', 'socai2.results.id'], name='case_assessment_sources_result_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'task_revision_id'], ['socai2.task_revisions.tenant_id', 'socai2.task_revisions.id'], name='case_assessment_sources_task_revision_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.id'], name='case_assessment_sources_artifact_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'assessment_id'], ['socai2.case_assessments.tenant_id', 'socai2.case_assessments.case_id', 'socai2.case_assessments.id'], name='case_assessment_sources_assessment_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'result_id'], ['socai2.results.tenant_id', 'socai2.results.case_id', 'socai2.results.id'], name='case_assessment_sources_result_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'task_revision_id'], ['socai2.task_revisions.tenant_id', 'socai2.task_revisions.case_id', 'socai2.task_revisions.id'], name='case_assessment_sources_task_revision_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.case_id', 'socai2.artifacts.id'], name='case_assessment_sources_artifact_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class CaseAssessmentMembers(Socai2Base):
    __tablename__ = 'case_assessment_members'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assessment_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alert_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    coverage_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'assessment_id', 'alert_id', name='case_assessment_members_business_key'),
        ForeignKeyConstraint(['tenant_id', 'case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='case_assessment_members_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'assessment_id'], ['socai2.case_assessments.tenant_id', 'socai2.case_assessments.id'], name='case_assessment_members_assessment_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'alert_id'], ['socai2.alerts.tenant_id', 'socai2.alerts.id'], name='case_assessment_members_alert_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'assessment_id'], ['socai2.case_assessments.tenant_id', 'socai2.case_assessments.case_id', 'socai2.case_assessments.id'], name='case_assessment_members_assessment_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class Runs(Socai2Base):
    __tablename__ = 'runs'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    alert_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    incident_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    case_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    trigger: Mapped[str] = mapped_column(Text, nullable=False)
    scope_revision: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    scope_updated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    scope_kind: Mapped[str | None] = mapped_column(Text, nullable=True)
    window_start: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    operation_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    retry_of_run_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    comparison_result_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    input_artifact_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    executor_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    requested_by: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    stop_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    stop_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_state: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'none'"))
    limits: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    row_version: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text('1'))
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'case_id', 'id', name='runs_scope_key_0'),
        UniqueConstraint('tenant_id', 'alert_id', 'id', name='runs_scope_key_1'),
        UniqueConstraint('tenant_id', 'incident_id', 'id', name='runs_scope_key_2'),
        CheckConstraint('"kind" IN (\'alert_basic\',\'incident_diagnosis\',\'baseline\',\'ai_question\')', name='runs_kind_enum'),
        CheckConstraint('length(btrim("title")) > 0', name='runs_title_nonblank'),
        CheckConstraint('length(btrim("purpose")) > 0', name='runs_purpose_nonblank'),
        CheckConstraint('"trigger" IN (\'ingested\',\'refresh\',\'case_created\',\'members_changed\',\'manual\',\'question\',\'retry\')', name='runs_trigger_enum'),
        CheckConstraint('"scope_revision" >= 0', name='runs_scope_revision_range'),
        CheckConstraint('"scope_kind" IN (\'whole_case\',\'selected_alerts\',\'explicit_objects\')', name='runs_scope_kind_enum'),
        CheckConstraint('"state" IN (\'pending_update\',\'running\',\'unknown\',\'completed\',\'failed\',\'cancelled\')', name='runs_state_enum'),
        CheckConstraint('length(btrim("operation_key")) > 0', name='runs_operation_key_nonblank'),
        CheckConstraint('"request_hash" ~ \'^[0-9a-f]{64}$\'', name='runs_request_hash_sha'),
        CheckConstraint('"delivery_state" IN (\'none\',\'partial\',\'complete\',\'unknown\')', name='runs_delivery_state_enum'),
        CheckConstraint('jsonb_typeof("limits") = \'object\'', name='runs_limits_json_type'),
        CheckConstraint('"row_version" > 0', name='runs_row_version_range'),
        CheckConstraint('num_nonnulls(alert_id,incident_id,case_id)=1', name='runs_one_parent'),
        CheckConstraint("(kind='alert_basic' AND alert_id IS NOT NULL) OR (kind='incident_diagnosis' AND incident_id IS NOT NULL) OR (kind IN ('baseline','ai_question') AND case_id IS NOT NULL)", name='runs_kind_parent'),
        CheckConstraint('(case_id IS NULL AND scope_revision IS NULL AND scope_kind IS NULL) OR (case_id IS NOT NULL AND scope_revision IS NOT NULL AND scope_kind IS NOT NULL)', name='runs_case_scope'),
        CheckConstraint("kind<>'baseline' OR scope_kind='whole_case'", name='runs_baseline_whole'),
        CheckConstraint("state<>'pending_update' OR (kind='baseline' AND started_at IS NULL AND ended_at IS NULL AND input_artifact_id IS NULL AND operation_key IS NULL AND request_hash IS NULL)", name='runs_pending_baseline'),
        CheckConstraint("state NOT IN ('running','unknown','completed','failed') OR (started_at IS NOT NULL AND input_artifact_id IS NOT NULL AND executor_version IS NOT NULL AND operation_key IS NOT NULL AND request_hash IS NOT NULL)", name='runs_start_fields'),
        CheckConstraint("(state IN ('completed','failed','cancelled')) = (ended_at IS NOT NULL)", name='runs_end_fields'),
        CheckConstraint('ended_at IS NULL OR started_at IS NULL OR ended_at>=started_at', name='runs_time_order'),
        CheckConstraint('(window_start IS NULL AND window_end IS NULL) OR (window_start IS NOT NULL AND window_end IS NOT NULL AND window_start<=window_end)', name='runs_window'),
        CheckConstraint('(operation_key IS NULL)=(request_hash IS NULL)', name='runs_request_pair'),
        CheckConstraint('retry_of_run_id IS DISTINCT FROM id', name='runs_retry_self'),
        ForeignKeyConstraint(['tenant_id', 'alert_id'], ['socai2.alerts.tenant_id', 'socai2.alerts.id'], name='runs_alert_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'incident_id'], ['socai2.incidents.tenant_id', 'socai2.incidents.id'], name='runs_incident_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='runs_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'retry_of_run_id'], ['socai2.runs.tenant_id', 'socai2.runs.id'], name='runs_retry_of_run_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'comparison_result_id'], ['socai2.results.tenant_id', 'socai2.results.id'], name='runs_comparison_result_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'input_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.id'], name='runs_input_artifact_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'comparison_result_id'], ['socai2.results.tenant_id', 'socai2.results.case_id', 'socai2.results.id'], name='runs_comparison_result_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'id', 'input_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.run_id', 'socai2.artifacts.id'], name='runs_input_artifact_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class RunMembers(Socai2Base):
    __tablename__ = 'run_members'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    run_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alert_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    material_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    triage_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    feedback_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    read_state: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'not_read'"))
    analysis_state: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'not_analyzed'"))
    omission_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'case_id', 'run_id', 'alert_id', name='run_members_scope_key_0'),
        UniqueConstraint('tenant_id', 'run_id', 'alert_id', name='run_members_business_key'),
        CheckConstraint('"read_state" IN (\'not_read\',\'read\',\'missing\',\'denied\',\'failed\')', name='run_members_read_state_enum'),
        CheckConstraint('"analysis_state" IN (\'not_analyzed\',\'analyzed\',\'unresolved\',\'excluded\')', name='run_members_analysis_state_enum'),
        CheckConstraint("read_state<>'read' OR material_id IS NOT NULL", name='run_members_read_material'),
        ForeignKeyConstraint(['tenant_id', 'run_id'], ['socai2.runs.tenant_id', 'socai2.runs.id'], name='run_members_run_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='run_members_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'alert_id'], ['socai2.alerts.tenant_id', 'socai2.alerts.id'], name='run_members_alert_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'material_id'], ['socai2.alert_materials.tenant_id', 'socai2.alert_materials.id'], name='run_members_material_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'triage_id'], ['socai2.alert_assessments.tenant_id', 'socai2.alert_assessments.id'], name='run_members_triage_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'feedback_id'], ['socai2.alert_assessments.tenant_id', 'socai2.alert_assessments.id'], name='run_members_feedback_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'run_id'], ['socai2.runs.tenant_id', 'socai2.runs.case_id', 'socai2.runs.id'], name='run_members_run_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'alert_id', 'material_id'], ['socai2.alert_materials.tenant_id', 'socai2.alert_materials.alert_id', 'socai2.alert_materials.id'], name='run_members_material_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'alert_id', 'triage_id'], ['socai2.alert_assessments.tenant_id', 'socai2.alert_assessments.alert_id', 'socai2.alert_assessments.id'], name='run_members_triage_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'alert_id', 'feedback_id'], ['socai2.alert_assessments.tenant_id', 'socai2.alert_assessments.alert_id', 'socai2.alert_assessments.id'], name='run_members_feedback_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class RunSteps(Socai2Base):
    __tablename__ = 'run_steps'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    run_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    parent_step_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    retry_of_step_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    stage_code: Mapped[str] = mapped_column(Text, nullable=False)
    question_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    implementation_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    input_artifact_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    output_artifact_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reused_artifact_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actual_args: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    returned_rows: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    usage: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'run_id', 'id', name='run_steps_scope_key_0'),
        UniqueConstraint('tenant_id', 'run_id', 'seq', name='run_steps_business_key'),
        CheckConstraint('"seq" > 0', name='run_steps_seq_range'),
        CheckConstraint('"kind" IN (\'stage\',\'model\',\'tool\',\'graph\',\'render\')', name='run_steps_kind_enum'),
        CheckConstraint('"state" IN (\'planned\',\'running\',\'completed\',\'failed\',\'timeout\',\'cancelled\',\'skipped\',\'unknown\')', name='run_steps_state_enum'),
        CheckConstraint('jsonb_typeof("actual_args") = \'object\'', name='run_steps_actual_args_json_type'),
        CheckConstraint('"returned_rows" >= 0', name='run_steps_returned_rows_range'),
        CheckConstraint('jsonb_typeof("usage") = \'object\'', name='run_steps_usage_json_type'),
        CheckConstraint('jsonb_typeof("error") = \'object\'', name='run_steps_error_json_type'),
        CheckConstraint('parent_step_id IS DISTINCT FROM id AND retry_of_step_id IS DISTINCT FROM id', name='run_steps_not_self'),
        CheckConstraint('ended_at IS NULL OR started_at IS NULL OR ended_at>=started_at', name='run_steps_time_order'),
        CheckConstraint("returned_rows IS NULL OR (kind='tool' AND state='completed' AND returned_rows>=0)", name='run_steps_query_rows'),
        CheckConstraint("kind<>'stage' OR usage IS NULL", name='run_steps_no_parent_cost'),
        ForeignKeyConstraint(['tenant_id', 'run_id'], ['socai2.runs.tenant_id', 'socai2.runs.id'], name='run_steps_run_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'parent_step_id'], ['socai2.run_steps.tenant_id', 'socai2.run_steps.id'], name='run_steps_parent_step_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'retry_of_step_id'], ['socai2.run_steps.tenant_id', 'socai2.run_steps.id'], name='run_steps_retry_of_step_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'input_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.id'], name='run_steps_input_artifact_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'output_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.id'], name='run_steps_output_artifact_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'reused_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.id'], name='run_steps_reused_artifact_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'run_id', 'parent_step_id'], ['socai2.run_steps.tenant_id', 'socai2.run_steps.run_id', 'socai2.run_steps.id'], name='run_steps_parent_step_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'run_id', 'retry_of_step_id'], ['socai2.run_steps.tenant_id', 'socai2.run_steps.run_id', 'socai2.run_steps.id'], name='run_steps_retry_of_step_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'run_id', 'input_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.run_id', 'socai2.artifacts.id'], name='run_steps_input_artifact_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'run_id', 'output_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.run_id', 'socai2.artifacts.id'], name='run_steps_output_artifact_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class Artifacts(Socai2Base):
    __tablename__ = 'artifacts'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alert_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    incident_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    case_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    run_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    step_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    content_json: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    blob_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    sha256: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    event_time: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    material_state: Mapped[str] = mapped_column(Text, nullable=False)
    source_refs: Mapped[object] = mapped_column(JSONB, nullable=False)
    retention: Mapped[object] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'case_id', 'id', name='artifacts_scope_key_0'),
        UniqueConstraint('tenant_id', 'alert_id', 'id', name='artifacts_scope_key_1'),
        UniqueConstraint('tenant_id', 'incident_id', 'id', name='artifacts_scope_key_2'),
        UniqueConstraint('tenant_id', 'run_id', 'id', name='artifacts_scope_key_3'),
        CheckConstraint('"kind" IN (\'input_snapshot\',\'model_request\',\'model_response\',\'tool_request\',\'tool_response\',\'domain_analysis\',\'deep_analysis\',\'attack_chain\',\'attack_path\',\'alert_graph\',\'report_json\',\'report_markdown\',\'attachment\',\'source_snapshot\',\'handoff\',\'query_plan\',\'alert_explanation\',\'case_evidence_index\')', name='artifacts_kind_enum'),
        CheckConstraint('"sha256" ~ \'^[0-9a-f]{64}$\'', name='artifacts_sha256_sha'),
        CheckConstraint('"size_bytes" >= 0', name='artifacts_size_bytes_range'),
        CheckConstraint('"material_state" IN (\'complete\',\'truncated\',\'summary_only\',\'unavailable\')', name='artifacts_material_state_enum'),
        CheckConstraint('jsonb_typeof("source_refs") = \'array\'', name='artifacts_source_refs_json_type'),
        CheckConstraint('jsonb_typeof("retention") = \'object\'', name='artifacts_retention_json_type'),
        CheckConstraint('num_nonnulls(alert_id,incident_id,case_id)=1', name='artifacts_one_parent'),
        CheckConstraint("num_nonnulls(content_json,content_text,blob_ref)=1 OR (material_state='unavailable' AND num_nonnulls(content_json,content_text,blob_ref)=0 AND nullif(retention->>'reason','') IS NOT NULL)", name='artifacts_content'),
        CheckConstraint('step_id IS NULL OR run_id IS NOT NULL', name='artifacts_step_has_run'),
        ForeignKeyConstraint(['tenant_id', 'alert_id'], ['socai2.alerts.tenant_id', 'socai2.alerts.id'], name='artifacts_alert_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'incident_id'], ['socai2.incidents.tenant_id', 'socai2.incidents.id'], name='artifacts_incident_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='artifacts_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'run_id'], ['socai2.runs.tenant_id', 'socai2.runs.id'], name='artifacts_run_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'step_id'], ['socai2.run_steps.tenant_id', 'socai2.run_steps.id'], name='artifacts_step_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'run_id', 'step_id'], ['socai2.run_steps.tenant_id', 'socai2.run_steps.run_id', 'socai2.run_steps.id'], name='artifacts_step_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'run_id'], ['socai2.runs.tenant_id', 'socai2.runs.case_id', 'socai2.runs.id'], name='artifacts_run_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'alert_id', 'run_id'], ['socai2.runs.tenant_id', 'socai2.runs.alert_id', 'socai2.runs.id'], name='artifacts_run_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'incident_id', 'run_id'], ['socai2.runs.tenant_id', 'socai2.runs.incident_id', 'socai2.runs.id'], name='artifacts_run_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class Results(Socai2Base):
    __tablename__ = 'results'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_run_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_answer_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion_state: Mapped[str] = mapped_column(Text, nullable=False)
    conclusion_origin: Mapped[str] = mapped_column(Text, nullable=False)
    validation_state: Mapped[str] = mapped_column(Text, nullable=False)
    closing_note: Mapped[str] = mapped_column(Text, nullable=False)
    findings: Mapped[object] = mapped_column(JSONB, nullable=False)
    questions: Mapped[object] = mapped_column(JSONB, nullable=False)
    recommendations: Mapped[object] = mapped_column(JSONB, nullable=False)
    comparison_result_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    change_kind: Mapped[str] = mapped_column(Text, nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    case_impact: Mapped[object] = mapped_column(JSONB, nullable=False)
    input_artifact_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    graph_artifact_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    report_artifact_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    supersedes_result_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    delivery_state: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    saved_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    saved_by: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    operation_key: Mapped[str] = mapped_column(Text, nullable=False)
    edited_fields: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'::text[]"))
    edit_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'case_id', 'id', name='results_scope_key_0'),
        UniqueConstraint('tenant_id', 'case_id', 'source_run_id', 'id', name='results_scope_key_1'),
        UniqueConstraint('tenant_id', 'operation_key', name='results_business_key'),
        CheckConstraint('"kind" IN (\'baseline\',\'ai_saved\')', name='results_kind_enum'),
        CheckConstraint('length(btrim("title")) > 0', name='results_title_nonblank'),
        CheckConstraint('length(btrim("purpose")) > 0', name='results_purpose_nonblank'),
        CheckConstraint('"conclusion_state" IN (\'supported\',\'uncertain\',\'unavailable\')', name='results_conclusion_state_enum'),
        CheckConstraint('"conclusion_origin" IN (\'model\',\'human\',\'system\',\'legacy\')', name='results_conclusion_origin_enum'),
        CheckConstraint('"validation_state" IN (\'not_checked\',\'accepted\',\'rejected\',\'system_only\',\'legacy_unverified\')', name='results_validation_state_enum'),
        CheckConstraint('jsonb_typeof("findings") = \'array\'', name='results_findings_json_type'),
        CheckConstraint('jsonb_typeof("questions") = \'array\'', name='results_questions_json_type'),
        CheckConstraint('jsonb_typeof("recommendations") = \'array\'', name='results_recommendations_json_type'),
        CheckConstraint('"change_kind" IN (\'initial\',\'unchanged\',\'expanded\',\'revised\',\'withdrawn\',\'not_comparable\')', name='results_change_kind_enum'),
        CheckConstraint('jsonb_typeof("case_impact") = \'object\'', name='results_case_impact_json_type'),
        CheckConstraint('"delivery_state" IN (\'none\',\'partial\',\'complete\',\'unknown\')', name='results_delivery_state_enum'),
        CheckConstraint('length(btrim("operation_key")) > 0', name='results_operation_key_nonblank'),
        CheckConstraint("(kind='ai_saved')=(source_answer_id IS NOT NULL)", name='results_answer_kind'),
        CheckConstraint("(conclusion_state='unavailable' AND conclusion IS NULL) OR (conclusion_state<>'unavailable' AND nullif(btrim(conclusion),'') IS NOT NULL)", name='results_conclusion'),
        CheckConstraint('comparison_result_id IS DISTINCT FROM id AND supersedes_result_id IS DISTINCT FROM id', name='results_comparison_self'),
        CheckConstraint("change_kind<>'initial' OR comparison_result_id IS NULL", name='results_initial_comparison'),
        CheckConstraint("NOT ('conclusion'=ANY(edited_fields)) OR conclusion_origin='human'", name='results_human_edit'),
        ForeignKeyConstraint(['tenant_id', 'case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='results_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'source_run_id'], ['socai2.runs.tenant_id', 'socai2.runs.id'], name='results_source_run_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'source_answer_id'], ['socai2.messages.tenant_id', 'socai2.messages.id'], name='results_source_answer_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'comparison_result_id'], ['socai2.results.tenant_id', 'socai2.results.id'], name='results_comparison_result_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'input_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.id'], name='results_input_artifact_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'graph_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.id'], name='results_graph_artifact_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'report_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.id'], name='results_report_artifact_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'supersedes_result_id'], ['socai2.results.tenant_id', 'socai2.results.id'], name='results_supersedes_result_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'source_run_id'], ['socai2.runs.tenant_id', 'socai2.runs.case_id', 'socai2.runs.id'], name='results_source_run_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'comparison_result_id'], ['socai2.results.tenant_id', 'socai2.results.case_id', 'socai2.results.id'], name='results_comparison_result_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'supersedes_result_id'], ['socai2.results.tenant_id', 'socai2.results.case_id', 'socai2.results.id'], name='results_supersedes_result_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'source_answer_id'], ['socai2.messages.tenant_id', 'socai2.messages.case_id', 'socai2.messages.id'], name='results_source_answer_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'input_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.case_id', 'socai2.artifacts.id'], name='results_input_artifact_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'graph_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.case_id', 'socai2.artifacts.id'], name='results_graph_artifact_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'report_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.case_id', 'socai2.artifacts.id'], name='results_report_artifact_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class ResultMembers(Socai2Base):
    __tablename__ = 'result_members'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    result_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    run_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alert_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assessment_state: Mapped[str] = mapped_column(Text, nullable=False)
    conclusion_covered: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_refs: Mapped[object] = mapped_column(JSONB, nullable=False)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'result_id', 'alert_id', name='result_members_business_key'),
        CheckConstraint('"assessment_state" IN (\'not_analyzed\',\'analyzed\',\'unresolved\',\'excluded\')', name='result_members_assessment_state_enum'),
        CheckConstraint('jsonb_typeof("evidence_refs") = \'array\'', name='result_members_evidence_refs_json_type'),
        CheckConstraint("NOT conclusion_covered OR assessment_state IN ('analyzed','unresolved')", name='result_members_coverage'),
        ForeignKeyConstraint(['tenant_id', 'case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='result_members_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'result_id'], ['socai2.results.tenant_id', 'socai2.results.id'], name='result_members_result_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'run_id'], ['socai2.runs.tenant_id', 'socai2.runs.id'], name='result_members_run_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'alert_id'], ['socai2.alerts.tenant_id', 'socai2.alerts.id'], name='result_members_alert_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'run_id', 'result_id'], ['socai2.results.tenant_id', 'socai2.results.case_id', 'socai2.results.source_run_id', 'socai2.results.id'], name='result_members_result_run_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'run_id', 'alert_id'], ['socai2.run_members.tenant_id', 'socai2.run_members.case_id', 'socai2.run_members.run_id', 'socai2.run_members.alert_id'], name='result_members_run_member_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class Tasks(Socai2Base):
    __tablename__ = 'tasks'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    current_revision_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    origin_result_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    origin_finding_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    created_by: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    row_version: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text('1'))
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'case_id', 'id', name='tasks_scope_key_0'),
        CheckConstraint('"row_version" > 0', name='tasks_row_version_range'),
        CheckConstraint('origin_finding_id IS NULL OR origin_result_id IS NOT NULL', name='tasks_finding_source'),
        ForeignKeyConstraint(['tenant_id', 'case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='tasks_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'current_revision_id'], ['socai2.task_revisions.tenant_id', 'socai2.task_revisions.id'], name='tasks_current_revision_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'origin_result_id'], ['socai2.results.tenant_id', 'socai2.results.id'], name='tasks_origin_result_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'id', 'current_revision_id'], ['socai2.task_revisions.tenant_id', 'socai2.task_revisions.case_id', 'socai2.task_revisions.task_id', 'socai2.task_revisions.id'], name='tasks_current_revision_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'origin_result_id'], ['socai2.results.tenant_id', 'socai2.results.case_id', 'socai2.results.id'], name='tasks_origin_result_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class TaskRevisions(Socai2Base):
    __tablename__ = 'task_revisions'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    task_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_scope: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    source_refs: Mapped[object] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    completed_by: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    changed_by: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'case_id', 'task_id', 'id', name='task_revisions_scope_key_0'),
        UniqueConstraint('tenant_id', 'case_id', 'id', name='task_revisions_scope_key_1'),
        UniqueConstraint('tenant_id', 'task_id', 'revision', name='task_revisions_business_key'),
        CheckConstraint('"revision" > 0', name='task_revisions_revision_range'),
        CheckConstraint('length(btrim("title")) > 0', name='task_revisions_title_nonblank'),
        CheckConstraint('"state" IN (\'not_started\',\'in_progress\',\'completed\',\'cancelled\')', name='task_revisions_state_enum'),
        CheckConstraint('jsonb_typeof("result_scope") = \'object\'', name='task_revisions_result_scope_json_type'),
        CheckConstraint('jsonb_typeof("source_refs") = \'array\'', name='task_revisions_source_refs_json_type'),
        CheckConstraint("state<>'completed' OR (nullif(btrim(result_text),'') IS NOT NULL AND result_scope IS NOT NULL AND completed_at IS NOT NULL AND completed_by IS NOT NULL)", name='task_revisions_completed_feedback'),
        CheckConstraint('(completed_at IS NULL)=(completed_by IS NULL)', name='task_revisions_completion_pair'),
        ForeignKeyConstraint(['tenant_id', 'case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='task_revisions_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'task_id'], ['socai2.tasks.tenant_id', 'socai2.tasks.id'], name='task_revisions_task_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'task_id'], ['socai2.tasks.tenant_id', 'socai2.tasks.case_id', 'socai2.tasks.id'], name='task_revisions_task_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class Conversations(Socai2Base):
    __tablename__ = 'conversations'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    row_version: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text('1'))
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'case_id', 'id', name='conversations_scope_key_0'),
        CheckConstraint('length(btrim("title")) > 0', name='conversations_title_nonblank'),
        CheckConstraint('"row_version" > 0', name='conversations_row_version_range'),
        ForeignKeyConstraint(['tenant_id', 'case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='conversations_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class Messages(Socai2Base):
    __tablename__ = 'messages'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    conversation_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    in_reply_to: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_run_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    input_artifact_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_refs: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    client_request_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    answered_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    error: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        UniqueConstraint('tenant_id', 'case_id', 'conversation_id', 'id', name='messages_scope_key_0'),
        UniqueConstraint('tenant_id', 'case_id', 'id', name='messages_scope_key_1'),
        UniqueConstraint('tenant_id', 'conversation_id', 'sequence', name='messages_business_key'),
        UniqueConstraint('tenant_id', 'conversation_id', 'client_request_key', name='messages_request_key'),
        CheckConstraint('"sequence" > 0', name='messages_sequence_range'),
        CheckConstraint('"role" IN (\'user\',\'assistant\')', name='messages_role_enum'),
        CheckConstraint('"state" IN (\'accepted\',\'running\',\'completed\',\'failed\',\'cancelled\',\'unknown\')', name='messages_state_enum'),
        CheckConstraint('jsonb_typeof("source_refs") = \'array\'', name='messages_source_refs_json_type'),
        CheckConstraint('length(btrim("client_request_key")) > 0', name='messages_client_request_key_nonblank'),
        CheckConstraint('jsonb_typeof("error") = \'object\'', name='messages_error_json_type'),
        CheckConstraint('in_reply_to IS DISTINCT FROM id', name='messages_not_self'),
        CheckConstraint("role<>'user' OR nullif(btrim(content),'') IS NOT NULL", name='messages_user_text'),
        CheckConstraint("role<>'assistant' OR state<>'completed' OR (nullif(btrim(content),'') IS NOT NULL AND source_run_id IS NOT NULL AND input_artifact_id IS NOT NULL AND answered_at IS NOT NULL)", name='messages_answer_fields'),
        ForeignKeyConstraint(['tenant_id', 'case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='messages_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'conversation_id'], ['socai2.conversations.tenant_id', 'socai2.conversations.id'], name='messages_conversation_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'in_reply_to'], ['socai2.messages.tenant_id', 'socai2.messages.id'], name='messages_in_reply_to_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'source_run_id'], ['socai2.runs.tenant_id', 'socai2.runs.id'], name='messages_source_run_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'input_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.id'], name='messages_input_artifact_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'conversation_id'], ['socai2.conversations.tenant_id', 'socai2.conversations.case_id', 'socai2.conversations.id'], name='messages_conversation_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'conversation_id', 'in_reply_to'], ['socai2.messages.tenant_id', 'socai2.messages.case_id', 'socai2.messages.conversation_id', 'socai2.messages.id'], name='messages_in_reply_to_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'source_run_id'], ['socai2.runs.tenant_id', 'socai2.runs.case_id', 'socai2.runs.id'], name='messages_source_run_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'input_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.case_id', 'socai2.artifacts.id'], name='messages_input_artifact_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class Activities(Socai2Base):
    __tablename__ = 'activities'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    operation_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor: Mapped[object] = mapped_column(JSONB, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    subject_alert_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    subject_incident_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    subject_case_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[object] = mapped_column(JSONB, nullable=False)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        CheckConstraint('jsonb_typeof("actor") = \'object\'', name='activities_actor_json_type'),
        CheckConstraint('jsonb_typeof("detail") = \'object\'', name='activities_detail_json_type'),
        CheckConstraint('num_nonnulls(subject_alert_id,subject_incident_id,subject_case_id)=1', name='activities_one_subject'),
        ForeignKeyConstraint(['tenant_id', 'subject_alert_id'], ['socai2.alerts.tenant_id', 'socai2.alerts.id'], name='activities_subject_alert_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'subject_incident_id'], ['socai2.incidents.tenant_id', 'socai2.incidents.id'], name='activities_subject_incident_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'subject_case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='activities_subject_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class ActivityTargets(Socai2Base):
    __tablename__ = 'activity_targets'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    activity_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alert_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    incident_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    case_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    task_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    run_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    result_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    comment_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    before_value: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    after_value: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    result_state: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        CheckConstraint('jsonb_typeof("before_value") = \'object\'', name='activity_targets_before_value_json_type'),
        CheckConstraint('jsonb_typeof("after_value") = \'object\'', name='activity_targets_after_value_json_type'),
        CheckConstraint('"result_state" IN (\'succeeded\',\'failed\',\'skipped\')', name='activity_targets_result_state_enum'),
        CheckConstraint('num_nonnulls(alert_id,incident_id,case_id,task_id,run_id,result_id,comment_id)=1', name='activity_targets_one_target'),
        ForeignKeyConstraint(['tenant_id', 'activity_id'], ['socai2.activities.tenant_id', 'socai2.activities.id'], name='activity_targets_activity_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'alert_id'], ['socai2.alerts.tenant_id', 'socai2.alerts.id'], name='activity_targets_alert_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'incident_id'], ['socai2.incidents.tenant_id', 'socai2.incidents.id'], name='activity_targets_incident_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='activity_targets_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'task_id'], ['socai2.tasks.tenant_id', 'socai2.tasks.id'], name='activity_targets_task_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'run_id'], ['socai2.runs.tenant_id', 'socai2.runs.id'], name='activity_targets_run_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'result_id'], ['socai2.results.tenant_id', 'socai2.results.id'], name='activity_targets_result_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'comment_id'], ['socai2.comments.tenant_id', 'socai2.comments.id'], name='activity_targets_comment_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class Comments(Socai2Base):
    __tablename__ = 'comments'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alert_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    incident_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    case_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    author_name_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    edited_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    edited_by: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    row_version: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text('1'))
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        CheckConstraint('length(btrim("body")) > 0', name='comments_body_nonblank'),
        CheckConstraint('"row_version" > 0', name='comments_row_version_range'),
        CheckConstraint('num_nonnulls(alert_id,incident_id,case_id)=1', name='comments_one_parent'),
        ForeignKeyConstraint(['tenant_id', 'alert_id'], ['socai2.alerts.tenant_id', 'socai2.alerts.id'], name='comments_alert_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'incident_id'], ['socai2.incidents.tenant_id', 'socai2.incidents.id'], name='comments_incident_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='comments_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

class ResponseLinks(Socai2Base):
    __tablename__ = 'response_links'
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alert_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    incident_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    case_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    result_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    proposal_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    legacy_proposal_ref: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    external_namespace: Mapped[str] = mapped_column(Text, nullable=False)
    approval_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text('transaction_timestamp()'))
    receipt_artifact_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id'),
        CheckConstraint('jsonb_typeof("legacy_proposal_ref") = \'object\'', name='response_links_legacy_proposal_ref_json_type'),
        CheckConstraint('num_nonnulls(alert_id,incident_id,case_id)=1', name='response_links_one_parent'),
        CheckConstraint('(result_id IS NOT NULL AND proposal_id IS NOT NULL AND legacy_proposal_ref IS NULL) OR (result_id IS NULL AND proposal_id IS NULL AND legacy_proposal_ref IS NOT NULL)', name='response_links_source'),
        CheckConstraint('approval_id IS NOT NULL OR action_id IS NOT NULL', name='response_links_has_target'),
        ForeignKeyConstraint(['tenant_id', 'alert_id'], ['socai2.alerts.tenant_id', 'socai2.alerts.id'], name='response_links_alert_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'incident_id'], ['socai2.incidents.tenant_id', 'socai2.incidents.id'], name='response_links_incident_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id'], ['socai2.cases.tenant_id', 'socai2.cases.id'], name='response_links_case_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'result_id'], ['socai2.results.tenant_id', 'socai2.results.id'], name='response_links_result_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'receipt_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.id'], name='response_links_receipt_artifact_id_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'result_id'], ['socai2.results.tenant_id', 'socai2.results.case_id', 'socai2.results.id'], name='response_links_result_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'case_id', 'receipt_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.case_id', 'socai2.artifacts.id'], name='response_links_receipt_artifact_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'alert_id', 'receipt_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.alert_id', 'socai2.artifacts.id'], name='response_links_receipt_artifact_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['tenant_id', 'incident_id', 'receipt_artifact_id'], ['socai2.artifacts.tenant_id', 'socai2.artifacts.incident_id', 'socai2.artifacts.id'], name='response_links_receipt_artifact_id_scope_fk', ondelete='RESTRICT', deferrable=True, initially='DEFERRED'),
        {'schema': 'socai2'},
    )

