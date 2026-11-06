-- socai2 investigation database V1 (2026-11-06). Standalone psql script.
-- Run as the schema owner on a new, dedicated UTF-8 PostgreSQL 16 database:
--   psql -X -d your_investigation_db -f init_socai2_v1.sql
-- Sources: processing-20261106-r3 support.sql and repository migrations 123-126.
-- Includes public dependencies, migration ledger and socai2 objects. No case,
-- tenant or credential seeds. Configure runtime identities/grants separately.
-- Migration 123 applies its original ACLs if aisoc_app exists on the cluster.
-- A complete V1 is checked without replay. A partial installation is rejected.
\set ON_ERROR_STOP on
\encoding UTF8
BEGIN ISOLATION LEVEL READ COMMITTED;
SET LOCAL search_path = pg_catalog;
SELECT pg_advisory_xact_lock(hashtext('socai2'), hashtext('schema-initialization'));
DO $preflight$
BEGIN
    IF current_database() IN ('postgres', 'template0', 'template1')
       OR current_setting('server_version_num')::integer / 10000 <> 16
       OR current_setting('server_encoding') <> 'UTF8' THEN
        RAISE EXCEPTION 'Use a dedicated UTF-8 database on PostgreSQL 16';
    END IF;
    IF to_regnamespace('socai2') IS NULL THEN
        IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname NOT IN ('public', 'information_schema')
                   AND left(nspname, 3) <> 'pg_')
           OR EXISTS (SELECT 1 FROM pg_depend WHERE refclassid = 'pg_namespace'::regclass
                      AND refobjid = 'public'::regnamespace)
           OR EXISTS (SELECT 1 FROM pg_extension WHERE extname <> 'plpgsql') THEN
            RAISE EXCEPTION 'Initialization requires a new empty database; found existing objects';
        END IF;
    ELSIF to_regclass('public.aisoc_schema_migrations') IS NULL THEN
        RAISE EXCEPTION 'Existing socai2 schema has no migration ledger';
    END IF;
END
$preflight$;
SELECT to_regnamespace('socai2') IS NULL AS fresh_install \gset
\if :fresh_install
SET LOCAL search_path = public, pg_catalog;

-- schema/support.sql (original SHA-256 2fa1b4c0749824fffe0bd3aeabf56fbaf5b2bc58ff2bafea3a1d85c68d559112)
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS public.aisoc_schema_migrations(name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());
CREATE OR REPLACE FUNCTION public.current_tenant_id() RETURNS uuid LANGUAGE sql STABLE AS $$ SELECT nullif(current_setting('app.current_tenant_id',true),'')::uuid $$;

CREATE TABLE IF NOT EXISTS permissions (
	id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	description TEXT, 
	category VARCHAR(100), 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;

CREATE TABLE IF NOT EXISTS tenants (
	id UUID NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	slug VARCHAR(100) NOT NULL, 
	plan VARCHAR(50) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	settings JSONB NOT NULL, 
	limits JSONB NOT NULL, 
	parent_tenant_id UUID, 
	mssp_role VARCHAR(50), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(parent_tenant_id) REFERENCES tenants (id)
)

;
CREATE INDEX IF NOT EXISTS ix_tenants_parent_tenant_id ON tenants (parent_tenant_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_tenants_slug ON tenants (slug);

CREATE TABLE IF NOT EXISTS assets (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	asset_type VARCHAR(50) NOT NULL, 
	name VARCHAR(512) NOT NULL, 
	fqdn VARCHAR(512), 
	ip_addresses TEXT[], 
	cloud_provider VARCHAR(50), 
	cloud_region VARCHAR(100), 
	cloud_account VARCHAR(255), 
	os VARCHAR(100), 
	os_version VARCHAR(100), 
	criticality VARCHAR(20) NOT NULL, 
	tags TEXT[], 
	owner_email VARCHAR(255), 
	last_seen TIMESTAMP WITH TIME ZONE NOT NULL, 
	first_seen TIMESTAMP WITH TIME ZONE NOT NULL, 
	metadata JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;

CREATE TABLE IF NOT EXISTS connectors (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	connector_type VARCHAR(100) NOT NULL, 
	category VARCHAR(50) NOT NULL, 
	is_enabled BOOLEAN NOT NULL, 
	auth_config JSONB NOT NULL, 
	connector_config JSONB NOT NULL, 
	health_status VARCHAR(20) NOT NULL, 
	last_health_check TIMESTAMP WITH TIME ZONE, 
	last_sync TIMESTAMP WITH TIME ZONE, 
	events_ingested INTEGER NOT NULL, 
	events_dropped INTEGER NOT NULL, 
	error_count INTEGER NOT NULL, 
	schema_fingerprint TEXT, 
	last_schema_drift_at TIMESTAMP WITH TIME ZONE, 
	last_drift_details JSONB, 
	last_event_at TIMESTAMP WITH TIME ZONE, 
	last_event_kind VARCHAR(50), 
	ingest_token VARCHAR(80), 
	oauth_provisioned BOOLEAN NOT NULL, 
	oauth_refresh_failures INTEGER NOT NULL, 
	oauth_last_refresh_at TIMESTAMP WITH TIME ZONE, 
	last_outage_at TIMESTAMP WITH TIME ZONE, 
	last_backfill_at TIMESTAMP WITH TIME ZONE, 
	allowed_capabilities JSONB, 
	tags JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	UNIQUE (ingest_token)
)

;
CREATE INDEX IF NOT EXISTS ix_connectors_connector_type ON connectors (connector_type);
CREATE INDEX IF NOT EXISTS ix_connectors_tenant_id ON connectors (tenant_id);

CREATE TABLE IF NOT EXISTS permission_conditions (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	permission TEXT NOT NULL, 
	role TEXT, 
	condition JSONB NOT NULL, 
	description TEXT, 
	enabled BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX IF NOT EXISTS ix_permission_conditions_tenant_id ON permission_conditions (tenant_id);

CREATE TABLE IF NOT EXISTS roles (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	label TEXT, 
	description TEXT, 
	is_system BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_roles_tenant_name UNIQUE (tenant_id, name), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX IF NOT EXISTS ix_roles_tenant_id ON roles (tenant_id);

CREATE TABLE IF NOT EXISTS tenant_llm_credentials (
	tenant_id UUID NOT NULL, 
	provider VARCHAR(40) NOT NULL, 
	base_url TEXT, 
	model VARCHAR(120), 
	api_key_vault TEXT, 
	settings JSONB NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_rotated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (tenant_id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;

CREATE TABLE IF NOT EXISTS threat_intel_iocs (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	ioc_type VARCHAR(50) NOT NULL, 
	value TEXT NOT NULL, 
	confidence INTEGER NOT NULL, 
	severity VARCHAR(20) NOT NULL, 
	tlp VARCHAR(10) NOT NULL, 
	threat_actor VARCHAR(255), 
	campaign VARCHAR(255), 
	malware_family VARCHAR(255), 
	tags TEXT[], 
	source VARCHAR(100) NOT NULL, 
	source_ref TEXT, 
	first_seen TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_seen TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	is_active BOOLEAN NOT NULL, 
	false_positive BOOLEAN NOT NULL, 
	linked_alerts UUID[], 
	context JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;

CREATE TABLE IF NOT EXISTS users (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	username VARCHAR(100) NOT NULL, 
	hashed_password VARCHAR(255) NOT NULL, 
	role VARCHAR(50) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	is_verified BOOLEAN NOT NULL, 
	last_login TIMESTAMP WITH TIME ZONE, 
	sessions_revoked_at TIMESTAMP WITH TIME ZONE, 
	preferences JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
)

;
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE INDEX IF NOT EXISTS ix_users_tenant_id ON users (tenant_id);

CREATE TABLE IF NOT EXISTS api_keys (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	user_id UUID, 
	name VARCHAR(255) NOT NULL, 
	key_prefix VARCHAR(20) NOT NULL, 
	hashed_key VARCHAR(255) NOT NULL, 
	scopes JSONB NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	last_used_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;
CREATE INDEX IF NOT EXISTS ix_api_keys_hashed_key ON api_keys (hashed_key);
CREATE INDEX IF NOT EXISTS ix_api_keys_tenant_id ON api_keys (tenant_id);

CREATE TABLE IF NOT EXISTS privilege_grants (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	permissions TEXT[] NOT NULL, 
	justification TEXT NOT NULL, 
	approved_by_id UUID, 
	granted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	case_id UUID, 
	alert_id UUID, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(approved_by_id) REFERENCES users (id) ON DELETE SET NULL
)

;
CREATE INDEX IF NOT EXISTS ix_privilege_grants_tenant_id ON privilege_grants (tenant_id);
CREATE INDEX IF NOT EXISTS ix_privilege_grants_user_id ON privilege_grants (user_id);

CREATE TABLE IF NOT EXISTS role_permissions (
	role_id UUID NOT NULL, 
	permission_id UUID NOT NULL, 
	PRIMARY KEY (role_id, permission_id), 
	FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE, 
	FOREIGN KEY(permission_id) REFERENCES permissions (id) ON DELETE CASCADE
)

;

CREATE TABLE IF NOT EXISTS user_risk_profiles (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	user_id UUID, 
	external_user_ref VARCHAR(255), 
	risk_score FLOAT NOT NULL, 
	risk_tier VARCHAR(20) NOT NULL, 
	failed_auth_24h INTEGER NOT NULL, 
	off_hours_events_7d INTEGER NOT NULL, 
	data_staging_score FLOAT NOT NULL, 
	peer_anomaly_score FLOAT NOT NULL, 
	privilege_delta INTEGER NOT NULL, 
	is_watchlisted BOOLEAN NOT NULL, 
	watchlist_reason TEXT, 
	watchlisted_at TIMESTAMP WITH TIME ZONE, 
	watchlisted_by UUID, 
	last_evaluated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(watchlisted_by) REFERENCES users (id) ON DELETE SET NULL
)

;

CREATE TABLE IF NOT EXISTS user_roles (
	user_id UUID NOT NULL, 
	role_id UUID NOT NULL, 
	assigned_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	assigned_by UUID, 
	PRIMARY KEY (user_id, role_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE, 
	FOREIGN KEY(assigned_by) REFERENCES users (id) ON DELETE SET NULL
)

;

CREATE TABLE IF NOT EXISTS insider_indicators (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	profile_id UUID NOT NULL, 
	indicator_type VARCHAR(100) NOT NULL, 
	severity VARCHAR(20) NOT NULL, 
	description TEXT NOT NULL, 
	source_alert_id UUID, 
	evidence JSONB NOT NULL, 
	occurred_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	acknowledged_by UUID, 
	acknowledged_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	FOREIGN KEY(profile_id) REFERENCES user_risk_profiles (id) ON DELETE CASCADE, 
	FOREIGN KEY(acknowledged_by) REFERENCES users (id) ON DELETE SET NULL
)

;
-- Migration 016: Knowledge-base + RAG over org docs/runbooks
-- Stores indexed document chunks for retrieval-augmented generation.

CREATE TABLE IF NOT EXISTS aisoc_kb_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID,
    title           TEXT NOT NULL,
    source_url      TEXT,
    doc_kind        TEXT NOT NULL DEFAULT 'runbook'
                        CHECK (doc_kind IN ('runbook','policy','playbook','sop','wiki','other')),
    content         TEXT NOT NULL,
    -- chunk metadata (if chunked at ingest)
    chunk_index     INT DEFAULT 0,
    chunk_total     INT DEFAULT 1,
    -- simple keyword tags for pre-filter
    tags            TEXT[] DEFAULT ARRAY[]::TEXT[],
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      TEXT
);

CREATE INDEX IF NOT EXISTS idx_aisoc_kb_tenant  ON aisoc_kb_documents (tenant_id);
CREATE INDEX IF NOT EXISTS idx_aisoc_kb_kind    ON aisoc_kb_documents (doc_kind);
-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_aisoc_kb_fts     ON aisoc_kb_documents USING gin(to_tsvector('english', content));

-- schema/123_socai2_page_data_model.sql (original SHA-256 ceb9a68012f84d6558cd0f75aa67b4047ae6245e1be64e79dd9b86587b8579da)
-- Generated from socai2-data-contract-20261103.json; do not edit by hand.

-- D01: incident override; D02: valid baseline auto-adoption; D03: AI may run concurrently.

-- New namespace only. No legacy backfill or runtime writer switch. Requires migrations 002/061.



CREATE SCHEMA IF NOT EXISTS socai2;

REVOKE ALL ON SCHEMA socai2 FROM PUBLIC;

CREATE TABLE IF NOT EXISTS socai2."alerts" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "source_namespace" text NOT NULL,
    "source_alert_id" text,
    "vendor_alert_id" text,
    "connector_id" uuid,
    "connector_type" text,
    "original_vendor" text,
    "source_identity_key" text NOT NULL,
    "title" text NOT NULL,
    "description" text,
    "category" text,
    "severity" text,
    "severity_raw" text,
    "event_time" timestamptz,
    "event_time_source" text NOT NULL DEFAULT 'unknown',
    "first_seen_at" timestamptz,
    "last_seen_at" timestamptz,
    "ingested_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "source_updated_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "business_updated_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "handling_status" text NOT NULL DEFAULT 'new',
    "disposition" text,
    "owner_id" uuid,
    "assignment_state" text NOT NULL DEFAULT 'unassigned',
    "owner_source_value" text,
    "assigned_at" timestamptz,
    "tags" text[] NOT NULL DEFAULT '{}'::text[],
    "priority_value" numeric(5,2),
    "priority_state" text NOT NULL DEFAULT 'not_provided',
    "priority_source" text,
    "priority_basis" jsonb,
    "closed_at" timestamptz,
    "closed_by" uuid,
    "reopened_at" timestamptz,
    "latest_material_id" uuid,
    "latest_triage_id" uuid,
    "latest_feedback_id" uuid,
    "row_version" bigint NOT NULL DEFAULT 1,
    "latest_explanation_id" uuid,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."alerts"."source_namespace" IS '来源系统命名空间，不是原厂名称';

COMMENT ON COLUMN socai2."alerts"."source_alert_id" IS '接入来源编号；允许非UUID';

COMMENT ON COLUMN socai2."alerts"."vendor_alert_id" IS '厂商原始告警编号；与接入编号分开';

COMMENT ON COLUMN socai2."alerts"."connector_id" IS '已有连接器引用，同租户校验';

COMMENT ON COLUMN socai2."alerts"."connector_type" IS '接入类型原值，不代替original_vendor';

COMMENT ON COLUMN socai2."alerts"."original_vendor" IS '明确原厂，未知NULL';

COMMENT ON COLUMN socai2."alerts"."source_identity_key" IS 'Fusion已计算稳定身份键；与namespace组成幂等键';

COMMENT ON COLUMN socai2."alerts"."title" IS '接收到的标题；未知来源用显式缺失显示，不编造内容';

COMMENT ON COLUMN socai2."alerts"."description" IS '来源说明；人工补充用评论';

COMMENT ON COLUMN socai2."alerts"."category" IS '来源类别，不拿判定替代';

COMMENT ON COLUMN socai2."alerts"."severity" IS '当前来源严重程度';

COMMENT ON COLUMN socai2."alerts"."severity_raw" IS '未映射来源等级原文';

COMMENT ON COLUMN socai2."alerts"."event_time" IS '真实发生时间';

COMMENT ON COLUMN socai2."alerts"."event_time_source" IS '发生时间依据';

COMMENT ON COLUMN socai2."alerts"."first_seen_at" IS '已收到材料中首次活动时间';

COMMENT ON COLUMN socai2."alerts"."last_seen_at" IS '已收到材料中末次活动时间';

COMMENT ON COLUMN socai2."alerts"."ingested_at" IS '首次接收时间';

COMMENT ON COLUMN socai2."alerts"."source_updated_at" IS '本地保存新材料的时间';

COMMENT ON COLUMN socai2."alerts"."business_updated_at" IS '实际业务字段变更时间；GET不更新';

COMMENT ON COLUMN socai2."alerts"."handling_status" IS '业务处理状态';

COMMENT ON COLUMN socai2."alerts"."disposition" IS '当前采用判定；与latest反馈或分诊配套';

COMMENT ON COLUMN socai2."alerts"."owner_id" IS 'public.users.id';

COMMENT ON COLUMN socai2."alerts"."assignment_state" IS '分配状态';

COMMENT ON COLUMN socai2."alerts"."owner_source_value" IS 'unresolved时原负责人值';

COMMENT ON COLUMN socai2."alerts"."assigned_at" IS '最近分配操作时间';

COMMENT ON COLUMN socai2."alerts"."tags" IS '业务标签；资产标签从库存读取';

COMMENT ON COLUMN socai2."alerts"."priority_value" IS '已有优先级0到100，不以分诊分数填充';

COMMENT ON COLUMN socai2."alerts"."priority_state" IS '优先级评分状态';

COMMENT ON COLUMN socai2."alerts"."priority_source" IS '评分生产者/模型版本';

COMMENT ON COLUMN socai2."alerts"."priority_basis" IS '评分来源依据；无值不造理由';

COMMENT ON COLUMN socai2."alerts"."closed_at" IS '当前完成周期关闭时间；重开后置空，旧值在活动中';

COMMENT ON COLUMN socai2."alerts"."closed_by" IS '明确用户关闭人；自动关闭记录活动服务身份';

COMMENT ON COLUMN socai2."alerts"."reopened_at" IS '最近明确重开时间';

COMMENT ON COLUMN socai2."alerts"."latest_material_id" IS '同告警最新有效材料';

COMMENT ON COLUMN socai2."alerts"."latest_triage_id" IS '同告警kind=triage记录';

COMMENT ON COLUMN socai2."alerts"."latest_feedback_id" IS '同告警kind=human_feedback记录';

COMMENT ON COLUMN socai2."alerts"."row_version" IS '管理乐观锁；每次实际写入+1';

COMMENT ON COLUMN socai2."alerts"."latest_explanation_id" IS '同告警kind=alert_explanation的有效Explain材料；GET不生成并写业务时钟';

CREATE TABLE IF NOT EXISTS socai2."alert_materials" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "alert_id" uuid NOT NULL,
    "revision" bigint NOT NULL,
    "received_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "source_version" text,
    "raw_text" text,
    "raw_json" jsonb,
    "ocsf_json" jsonb,
    "detection" jsonb NOT NULL,
    "enrichment" jsonb,
    "source_scope" jsonb NOT NULL,
    "material_state" text NOT NULL,
    "sha256" char(64),
    "retention" jsonb NOT NULL,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."alert_materials"."alert_id" IS '所属告警';

COMMENT ON COLUMN socai2."alert_materials"."revision" IS '同告警材料版本，从1开始';

COMMENT ON COLUMN socai2."alert_materials"."received_at" IS '接收时间';

COMMENT ON COLUMN socai2."alert_materials"."source_version" IS '输入已有源版本，未知NULL';

COMMENT ON COLUMN socai2."alert_materials"."raw_text" IS '原始字符串，保留原文';

COMMENT ON COLUMN socai2."alert_materials"."raw_json" IS '合法JSON输入';

COMMENT ON COLUMN socai2."alert_materials"."ocsf_json" IS '收到的OCSF原值';

COMMENT ON COLUMN socai2."alert_materials"."detection" IS '规则、ATT&CK与来源检测评分合同';

COMMENT ON COLUMN socai2."alert_materials"."enrichment" IS '已收到富化；来源及时间';

COMMENT ON COLUMN socai2."alert_materials"."source_scope" IS '来源引用范围、数量、截断和完整性';

COMMENT ON COLUMN socai2."alert_materials"."material_state" IS '原件留存状态';

COMMENT ON COLUMN socai2."alert_materials"."sha256" IS '已留存字节哈希；原大小/原hash另在retention';

COMMENT ON COLUMN socai2."alert_materials"."retention" IS '字节数、保存形式、截断及原因';

CREATE TABLE IF NOT EXISTS socai2."alert_source_refs" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "alert_id" uuid NOT NULL,
    "material_id" uuid NOT NULL,
    "source_namespace" text NOT NULL,
    "source_event_id" text NOT NULL,
    "relation_kind" text NOT NULL,
    "observed_at" timestamptz,
    "source_path" text,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."alert_source_refs"."alert_id" IS '归属告警';

COMMENT ON COLUMN socai2."alert_source_refs"."material_id" IS '在哪版材料中接收到';

COMMENT ON COLUMN socai2."alert_source_refs"."source_namespace" IS '湖/数据源标识';

COMMENT ON COLUMN socai2."alert_source_refs"."source_event_id" IS '原始事件ID，有效UUID只规范表示，不拒绝其他文本';

COMMENT ON COLUMN socai2."alert_source_refs"."relation_kind" IS '来源参与方式';

COMMENT ON COLUMN socai2."alert_source_refs"."observed_at" IS '源事件时间';

COMMENT ON COLUMN socai2."alert_source_refs"."source_path" IS '材料字段路径';

CREATE TABLE IF NOT EXISTS socai2."alert_objects" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "alert_id" uuid NOT NULL,
    "material_id" uuid NOT NULL,
    "object_key" text NOT NULL,
    "object_type" text NOT NULL,
    "source_type" text,
    "object_role" text NOT NULL,
    "namespace" text NOT NULL,
    "raw_value" text NOT NULL,
    "normalized_value" text NOT NULL,
    "source_path" text NOT NULL,
    "attributes" jsonb NOT NULL,
    "asset_match_state" text NOT NULL DEFAULT 'not_checked',
    "asset_ref" jsonb,
    "match_basis" jsonb,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."alert_objects"."alert_id" IS '来源告警';

COMMENT ON COLUMN socai2."alert_objects"."material_id" IS '来源材料版本';

COMMENT ON COLUMN socai2."alert_objects"."object_key" IS 'type+namespace+normalized值计算的稳定键';

COMMENT ON COLUMN socai2."alert_objects"."object_type" IS '有类型的对象';

COMMENT ON COLUMN socai2."alert_objects"."source_type" IS '来源原类型；other必有';

COMMENT ON COLUMN socai2."alert_objects"."object_role" IS '实体或IOC';

COMMENT ON COLUMN socai2."alert_objects"."namespace" IS '主机域/账号域/算法等身份边界';

COMMENT ON COLUMN socai2."alert_objects"."raw_value" IS '原对象值';

COMMENT ON COLUMN socai2."alert_objects"."normalized_value" IS '按明确类型规则规范；不跨类型合并';

COMMENT ON COLUMN socai2."alert_objects"."source_path" IS '来源材料字段路径';

COMMENT ON COLUMN socai2."alert_objects"."attributes" IS '进程/端点/哈希等类型化已收属性';

COMMENT ON COLUMN socai2."alert_objects"."asset_match_state" IS '当时库存匹配状态';

COMMENT ON COLUMN socai2."alert_objects"."asset_ref" IS '已有库存的类型化引用';

COMMENT ON COLUMN socai2."alert_objects"."match_basis" IS '匹配依据及时间快照';

CREATE TABLE IF NOT EXISTS socai2."alert_assessments" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "alert_id" uuid NOT NULL,
    "kind" text NOT NULL,
    "input_material_id" uuid,
    "source_run_id" uuid,
    "legacy_execution_ref" jsonb,
    "verdict" text,
    "rationale" text,
    "confidence" numeric(6,5),
    "score_state" text NOT NULL DEFAULT 'not_provided',
    "recommendations" jsonb,
    "producer" text NOT NULL,
    "actor" jsonb NOT NULL,
    "assessed_at" timestamptz NOT NULL,
    "operation_key" text NOT NULL,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."alert_assessments"."alert_id" IS '所属告警';

COMMENT ON COLUMN socai2."alert_assessments"."kind" IS '分诊或人工反馈';

COMMENT ON COLUMN socai2."alert_assessments"."input_material_id" IS '判断依据的材料版；旧未知NULL';

COMMENT ON COLUMN socai2."alert_assessments"."source_run_id" IS '新alert_basic执行；与此告警一致';

COMMENT ON COLUMN socai2."alert_assessments"."legacy_execution_ref" IS '旧执行稳定引用，不能冒充新Run';

COMMENT ON COLUMN socai2."alert_assessments"."verdict" IS '同次判定';

COMMENT ON COLUMN socai2."alert_assessments"."rationale" IS '同次理由，历史缺失NULL';

COMMENT ON COLUMN socai2."alert_assessments"."confidence" IS '分诊置信度0..1，页面可乘100显示；人工无评分';

COMMENT ON COLUMN socai2."alert_assessments"."score_state" IS '计算状态';

COMMENT ON COLUMN socai2."alert_assessments"."recommendations" IS '同次建议，不与新人工判断拼接';

COMMENT ON COLUMN socai2."alert_assessments"."producer" IS '生产者及版本';

COMMENT ON COLUMN socai2."alert_assessments"."actor" IS '实际操作者/服务身份';

COMMENT ON COLUMN socai2."alert_assessments"."assessed_at" IS '判断发生时间';

COMMENT ON COLUMN socai2."alert_assessments"."operation_key" IS '本判断幂等键';

CREATE TABLE IF NOT EXISTS socai2."incidents" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "source_namespace" text NOT NULL,
    "source_incident_id" text NOT NULL,
    "title" text NOT NULL,
    "description" text,
    "handling_status" text NOT NULL DEFAULT 'new',
    "owner_id" uuid,
    "assignment_state" text NOT NULL DEFAULT 'unassigned',
    "owner_source_value" text,
    "assigned_at" timestamptz,
    "tags" text[] NOT NULL DEFAULT '{}'::text[],
    "severity_override" text,
    "severity_override_reason" text,
    "severity_override_at" timestamptz,
    "severity_override_by" uuid,
    "priority_value" numeric(5,2),
    "priority_state" text NOT NULL DEFAULT 'not_provided',
    "priority_source" text,
    "priority_basis" jsonb,
    "resolution_note" text,
    "resolved_at" timestamptz,
    "resolved_by" uuid,
    "reopened_at" timestamptz,
    "created_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "business_updated_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "latest_diagnosis_id" uuid,
    "row_version" bigint NOT NULL DEFAULT 1,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."incidents"."source_namespace" IS 'Fusion实例/来源命名空间';

COMMENT ON COLUMN socai2."incidents"."source_incident_id" IS '来源事件ID，兼容原有文本键';

COMMENT ON COLUMN socai2."incidents"."title" IS '事件自身标题';

COMMENT ON COLUMN socai2."incidents"."description" IS '事件自身说明，非第一条成员标题';

COMMENT ON COLUMN socai2."incidents"."handling_status" IS '事件业务处理状态';

COMMENT ON COLUMN socai2."incidents"."owner_id" IS '当前明确负责人';

COMMENT ON COLUMN socai2."incidents"."assignment_state" IS '未分配/已分配/原值未解析';

COMMENT ON COLUMN socai2."incidents"."owner_source_value" IS '未解析来源负责人';

COMMENT ON COLUMN socai2."incidents"."assigned_at" IS '最近改派时间';

COMMENT ON COLUMN socai2."incidents"."tags" IS '事件业务标签，成员资产标签另外派生';

COMMENT ON COLUMN socai2."incidents"."severity_override" IS '人工事件覆盖等级；NULL=采用成员最高；不改成员';

COMMENT ON COLUMN socai2."incidents"."severity_override_reason" IS '人工覆盖依据';

COMMENT ON COLUMN socai2."incidents"."severity_override_at" IS '覆盖设置时间';

COMMENT ON COLUMN socai2."incidents"."severity_override_by" IS '覆盖人';

COMMENT ON COLUMN socai2."incidents"."priority_value" IS '已有优先级0..100';

COMMENT ON COLUMN socai2."incidents"."priority_state" IS '无来源不合成';

COMMENT ON COLUMN socai2."incidents"."priority_source" IS '已有评分生产者';

COMMENT ON COLUMN socai2."incidents"."priority_basis" IS '评分依据';

COMMENT ON COLUMN socai2."incidents"."resolution_note" IS '事件解决说明，人工解决必填';

COMMENT ON COLUMN socai2."incidents"."resolved_at" IS '当前解决周期时间';

COMMENT ON COLUMN socai2."incidents"."resolved_by" IS '解决人';

COMMENT ON COLUMN socai2."incidents"."reopened_at" IS '最近明确重开时间';

COMMENT ON COLUMN socai2."incidents"."created_at" IS '事件首次持久化时间';

COMMENT ON COLUMN socai2."incidents"."business_updated_at" IS '自身管理或成员关联变动；移除最后成员仍更新';

COMMENT ON COLUMN socai2."incidents"."latest_diagnosis_id" IS '同事件最新成功诊断；失败尝试不能覆盖';

COMMENT ON COLUMN socai2."incidents"."row_version" IS '管理/范围写入乐观版本';

CREATE TABLE IF NOT EXISTS socai2."incident_alerts" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "incident_id" uuid NOT NULL,
    "alert_id" uuid NOT NULL,
    "linked_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "membership_source" text NOT NULL,
    "correlation_basis" jsonb NOT NULL,
    "basis_version" text NOT NULL,
    "source_operation_id" uuid NOT NULL,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."incident_alerts"."incident_id" IS '事件';

COMMENT ON COLUMN socai2."incident_alerts"."alert_id" IS '当前成员';

COMMENT ON COLUMN socai2."incident_alerts"."linked_at" IS '加入时间';

COMMENT ON COLUMN socai2."incident_alerts"."membership_source" IS '成员产生方式';

COMMENT ON COLUMN socai2."incident_alerts"."correlation_basis" IS '实际规则、对象类型、值、窗口及候选关系';

COMMENT ON COLUMN socai2."incident_alerts"."basis_version" IS '归并算法/合同版本';

COMMENT ON COLUMN socai2."incident_alerts"."source_operation_id" IS '和活动同操作ID';

CREATE TABLE IF NOT EXISTS socai2."incident_diagnoses" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "incident_id" uuid NOT NULL,
    "source_run_id" uuid NOT NULL,
    "revision" bigint NOT NULL,
    "state" text NOT NULL,
    "summary" text,
    "diagnosis" jsonb,
    "open_questions" jsonb,
    "input_artifact_id" uuid NOT NULL,
    "source_fingerprint" char(64) NOT NULL,
    "producer" text NOT NULL,
    "requested_at" timestamptz NOT NULL,
    "generated_at" timestamptz,
    "error" jsonb,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."incident_diagnoses"."incident_id" IS '事件';

COMMENT ON COLUMN socai2."incident_diagnoses"."source_run_id" IS 'incident_diagnosis执行，同事件';

COMMENT ON COLUMN socai2."incident_diagnoses"."revision" IS '同事件尝试版本';

COMMENT ON COLUMN socai2."incident_diagnoses"."state" IS '生成尝试状态';

COMMENT ON COLUMN socai2."incident_diagnoses"."summary" IS '有效概况正文，失败不伪造';

COMMENT ON COLUMN socai2."incident_diagnoses"."diagnosis" IS '诊断、证据和限制';

COMMENT ON COLUMN socai2."incident_diagnoses"."open_questions" IS '待核问题';

COMMENT ON COLUMN socai2."incident_diagnoses"."input_artifact_id" IS '冻结成员/分诊/来源材料快照';

COMMENT ON COLUMN socai2."incident_diagnoses"."source_fingerprint" IS '实际输入指纹';

COMMENT ON COLUMN socai2."incident_diagnoses"."producer" IS '实现和版本';

COMMENT ON COLUMN socai2."incident_diagnoses"."requested_at" IS '尝试时间';

COMMENT ON COLUMN socai2."incident_diagnoses"."generated_at" IS '成功时间';

COMMENT ON COLUMN socai2."incident_diagnoses"."error" IS '失败原因；无报错NULL';

CREATE TABLE IF NOT EXISTS socai2."cases" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "title" text NOT NULL,
    "description" text,
    "handling_status" text NOT NULL DEFAULT 'new',
    "severity" text,
    "severity_source" text,
    "owner_id" uuid,
    "assignment_state" text NOT NULL DEFAULT 'unassigned',
    "owner_source_value" text,
    "assigned_at" timestamptz,
    "tags" text[] NOT NULL DEFAULT '{}'::text[],
    "priority_value" numeric(5,2),
    "priority_state" text NOT NULL DEFAULT 'not_provided',
    "priority_source" text,
    "priority_basis" jsonb,
    "scope_revision" bigint NOT NULL DEFAULT 0,
    "current_assessment_id" uuid,
    "created_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "created_by" uuid,
    "business_updated_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "resolved_at" timestamptz,
    "resolved_by" uuid,
    "resolution_note" text,
    "reopened_at" timestamptz,
    "row_version" bigint NOT NULL DEFAULT 1,
    "legacy_ref" jsonb,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."cases"."title" IS '名称';

COMMENT ON COLUMN socai2."cases"."description" IS '案情说明';

COMMENT ON COLUMN socai2."cases"."handling_status" IS '业务状态';

COMMENT ON COLUMN socai2."cases"."severity" IS '当前明确案件等级';

COMMENT ON COLUMN socai2."cases"."severity_source" IS '手动设置或明确汇总规则，不从置信度猜';

COMMENT ON COLUMN socai2."cases"."owner_id" IS '当前负责人';

COMMENT ON COLUMN socai2."cases"."assignment_state" IS '分配状态';

COMMENT ON COLUMN socai2."cases"."owner_source_value" IS '历史未解析负责人';

COMMENT ON COLUMN socai2."cases"."assigned_at" IS '最近分配时间';

COMMENT ON COLUMN socai2."cases"."tags" IS '案件标签';

COMMENT ON COLUMN socai2."cases"."priority_value" IS '已有优先级';

COMMENT ON COLUMN socai2."cases"."priority_state" IS '评分状态';

COMMENT ON COLUMN socai2."cases"."priority_source" IS '评分生产者';

COMMENT ON COLUMN socai2."cases"."priority_basis" IS '已有依据';

COMMENT ON COLUMN socai2."cases"."scope_revision" IS '仅当前告警成员真实变动+1';

COMMENT ON COLUMN socai2."cases"."current_assessment_id" IS '已明确采用版本；不等于最新Run';

COMMENT ON COLUMN socai2."cases"."created_at" IS '创建时间';

COMMENT ON COLUMN socai2."cases"."created_by" IS '创建人，服务创建见活动';

COMMENT ON COLUMN socai2."cases"."business_updated_at" IS '案件业务变化';

COMMENT ON COLUMN socai2."cases"."resolved_at" IS '当前解决周期时间';

COMMENT ON COLUMN socai2."cases"."resolved_by" IS '明确解决人';

COMMENT ON COLUMN socai2."cases"."resolution_note" IS '解决说明，不擅自添加必填要求';

COMMENT ON COLUMN socai2."cases"."reopened_at" IS '最近重开';

COMMENT ON COLUMN socai2."cases"."row_version" IS '乐观版本';

COMMENT ON COLUMN socai2."cases"."legacy_ref" IS '导入时原Case命名空间/文本ID';

CREATE TABLE IF NOT EXISTS socai2."case_alerts" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "case_id" uuid NOT NULL,
    "alert_id" uuid NOT NULL,
    "added_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "added_by" uuid,
    "membership_source" text NOT NULL,
    "source_operation_id" uuid NOT NULL,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."case_alerts"."case_id" IS '当前Case';

COMMENT ON COLUMN socai2."case_alerts"."alert_id" IS '当前正式成员';

COMMENT ON COLUMN socai2."case_alerts"."added_at" IS '加入时间';

COMMENT ON COLUMN socai2."case_alerts"."added_by" IS '明确操作人';

COMMENT ON COLUMN socai2."case_alerts"."membership_source" IS '加入来源';

COMMENT ON COLUMN socai2."case_alerts"."source_operation_id" IS '批量实际操作';

CREATE TABLE IF NOT EXISTS socai2."case_incidents" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "case_id" uuid NOT NULL,
    "incident_id" uuid NOT NULL,
    "linked_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "linked_by" uuid,
    "source_operation_id" uuid NOT NULL,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."case_incidents"."case_id" IS 'Case';

COMMENT ON COLUMN socai2."case_incidents"."incident_id" IS '显式关联事件';

COMMENT ON COLUMN socai2."case_incidents"."linked_at" IS '关联时间';

COMMENT ON COLUMN socai2."case_incidents"."linked_by" IS '操作者';

COMMENT ON COLUMN socai2."case_incidents"."source_operation_id" IS '操作ID';

CREATE TABLE IF NOT EXISTS socai2."case_assessments" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "case_id" uuid NOT NULL,
    "revision" bigint NOT NULL,
    "conclusion" text NOT NULL,
    "origin" text NOT NULL,
    "validity" text NOT NULL,
    "scope_revision" bigint NOT NULL,
    "formed_at" timestamptz NOT NULL,
    "adopted_at" timestamptz NOT NULL,
    "adopted_by" uuid,
    "actor" jsonb NOT NULL,
    "reason" text,
    "operation_key" text NOT NULL,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."case_assessments"."case_id" IS '案件';

COMMENT ON COLUMN socai2."case_assessments"."revision" IS '案件判断版本';

COMMENT ON COLUMN socai2."case_assessments"."conclusion" IS '明确采用的判断';

COMMENT ON COLUMN socai2."case_assessments"."origin" IS 'model/human/legacy，system交接不得采用为有效结论';

COMMENT ON COLUMN socai2."case_assessments"."validity" IS '采用时有效性；不代表绝对事实证明';

COMMENT ON COLUMN socai2."case_assessments"."scope_revision" IS '采用时Case范围版本';

COMMENT ON COLUMN socai2."case_assessments"."formed_at" IS '判断形成时间';

COMMENT ON COLUMN socai2."case_assessments"."adopted_at" IS '采用时间';

COMMENT ON COLUMN socai2."case_assessments"."adopted_by" IS '人工采用时用户；基础结果自动采用NULL，actor明确service';

COMMENT ON COLUMN socai2."case_assessments"."actor" IS '真实采用主体；baseline自动采用记录service';

COMMENT ON COLUMN socai2."case_assessments"."reason" IS '采用/修改理由';

COMMENT ON COLUMN socai2."case_assessments"."operation_key" IS '同一次采用幂等键';

CREATE TABLE IF NOT EXISTS socai2."case_assessment_sources" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "case_id" uuid NOT NULL,
    "assessment_id" uuid NOT NULL,
    "result_id" uuid,
    "task_revision_id" uuid,
    "artifact_id" uuid,
    "source_note" text,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."case_assessment_sources"."case_id" IS '用于父案复合FK';

COMMENT ON COLUMN socai2."case_assessment_sources"."assessment_id" IS '采用判断';

COMMENT ON COLUMN socai2."case_assessment_sources"."result_id" IS '具体正式结果版本';

COMMENT ON COLUMN socai2."case_assessment_sources"."task_revision_id" IS '具体人工事实版本';

COMMENT ON COLUMN socai2."case_assessment_sources"."artifact_id" IS '同案其他具体材料';

COMMENT ON COLUMN socai2."case_assessment_sources"."source_note" IS '此来源被采用的部分';

CREATE TABLE IF NOT EXISTS socai2."case_assessment_members" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "case_id" uuid NOT NULL,
    "assessment_id" uuid NOT NULL,
    "alert_id" uuid NOT NULL,
    "coverage_note" text,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."case_assessment_members"."case_id" IS '同案约束';

COMMENT ON COLUMN socai2."case_assessment_members"."assessment_id" IS '采用判断';

COMMENT ON COLUMN socai2."case_assessment_members"."alert_id" IS '判断明确覆盖的告警';

COMMENT ON COLUMN socai2."case_assessment_members"."coverage_note" IS '范围限制；覆盖不是全告警都恶意';

CREATE TABLE IF NOT EXISTS socai2."runs" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "kind" text NOT NULL,
    "alert_id" uuid,
    "incident_id" uuid,
    "case_id" uuid,
    "title" text NOT NULL,
    "purpose" text NOT NULL,
    "trigger" text NOT NULL,
    "scope_revision" bigint,
    "scope_updated_at" timestamptz,
    "scope_kind" text,
    "window_start" timestamptz,
    "window_end" timestamptz,
    "state" text NOT NULL,
    "operation_key" text,
    "request_hash" char(64),
    "retry_of_run_id" uuid,
    "comparison_result_id" uuid,
    "input_artifact_id" uuid,
    "executor_version" text,
    "requested_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "requested_by" uuid,
    "started_at" timestamptz,
    "ended_at" timestamptz,
    "stop_reason" text,
    "stop_detail" text,
    "delivery_state" text NOT NULL DEFAULT 'none',
    "limits" jsonb,
    "row_version" bigint NOT NULL DEFAULT 1,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."runs"."kind" IS '四机器流程明确区分';

COMMENT ON COLUMN socai2."runs"."alert_id" IS 'alert_basic归属';

COMMENT ON COLUMN socai2."runs"."incident_id" IS 'incident_diagnosis归属';

COMMENT ON COLUMN socai2."runs"."case_id" IS 'baseline/ai_question归属';

COMMENT ON COLUMN socai2."runs"."title" IS '本次执行名称，pending随范围更新';

COMMENT ON COLUMN socai2."runs"."purpose" IS '本轮目标/提问';

COMMENT ON COLUMN socai2."runs"."trigger" IS '触发原因';

COMMENT ON COLUMN socai2."runs"."scope_revision" IS 'Case成员版本；非Case NULL';

COMMENT ON COLUMN socai2."runs"."scope_updated_at" IS 'pending最近合并范围时间';

COMMENT ON COLUMN socai2."runs"."scope_kind" IS 'baseline whole_case，AI可选范围；其他流程NULL';

COMMENT ON COLUMN socai2."runs"."window_start" IS '固定绝对查询起点；不适用NULL';

COMMENT ON COLUMN socai2."runs"."window_end" IS '固定绝对查询终点；成对出现';

COMMENT ON COLUMN socai2."runs"."state" IS '记录/执行状态';

COMMENT ON COLUMN socai2."runs"."operation_key" IS '实际执行请求幂等键，pending尚未领取可NULL';

COMMENT ON COLUMN socai2."runs"."request_hash" IS '规范请求指纹，与幂等键配对';

COMMENT ON COLUMN socai2."runs"."retry_of_run_id" IS '显式重试指向旧已结束Run，不重写旧Run';

COMMENT ON COLUMN socai2."runs"."comparison_result_id" IS '领取时固定的同案比较基线，可跨成员范围';

COMMENT ON COLUMN socai2."runs"."input_artifact_id" IS '领取前NULL；提交running前冻结本地输入';

COMMENT ON COLUMN socai2."runs"."executor_version" IS '实际执行版本，pending NULL';

COMMENT ON COLUMN socai2."runs"."requested_at" IS '记录创建/首次请求';

COMMENT ON COLUMN socai2."runs"."requested_by" IS '真实请求人';

COMMENT ON COLUMN socai2."runs"."started_at" IS 'running领取事务时间';

COMMENT ON COLUMN socai2."runs"."ended_at" IS '终态时间；unknown未确认结束NULL';

COMMENT ON COLUMN socai2."runs"."stop_reason" IS '稳定原因码；不强用人类结论代替';

COMMENT ON COLUMN socai2."runs"."stop_detail" IS '可读原因';

COMMENT ON COLUMN socai2."runs"."delivery_state" IS '实际产物交付';

COMMENT ON COLUMN socai2."runs"."limits" IS '启动时预算和查询限额快照';

COMMENT ON COLUMN socai2."runs"."row_version" IS '执行状态条件更新版本';

CREATE TABLE IF NOT EXISTS socai2."run_members" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "run_id" uuid NOT NULL,
    "case_id" uuid NOT NULL,
    "alert_id" uuid NOT NULL,
    "material_id" uuid,
    "triage_id" uuid,
    "feedback_id" uuid,
    "read_state" text NOT NULL DEFAULT 'not_read',
    "analysis_state" text NOT NULL DEFAULT 'not_analyzed',
    "omission_reason" text,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."run_members"."run_id" IS 'Case执行；非Case成员快照存输入工件';

COMMENT ON COLUMN socai2."run_members"."case_id" IS '同案FK';

COMMENT ON COLUMN socai2."run_members"."alert_id" IS '本轮约定成员';

COMMENT ON COLUMN socai2."run_members"."material_id" IS '领取选择的材料版；确实缺失NULL并标read状态';

COMMENT ON COLUMN socai2."run_members"."triage_id" IS '同告警同次分诊';

COMMENT ON COLUMN socai2."run_members"."feedback_id" IS '同告警当时人工反馈';

COMMENT ON COLUMN socai2."run_members"."read_state" IS '实际读到材料';

COMMENT ON COLUMN socai2."run_members"."analysis_state" IS '实际分析状态';

COMMENT ON COLUMN socai2."run_members"."omission_reason" IS '缺失/失败/排除的具体原因';

CREATE TABLE IF NOT EXISTS socai2."run_steps" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "run_id" uuid NOT NULL,
    "seq" bigint NOT NULL,
    "parent_step_id" uuid,
    "retry_of_step_id" uuid,
    "kind" text NOT NULL,
    "stage_code" text NOT NULL,
    "question_id" text,
    "state" text NOT NULL,
    "name" text NOT NULL,
    "provider" text,
    "implementation_version" text,
    "started_at" timestamptz,
    "ended_at" timestamptz,
    "input_artifact_id" uuid,
    "output_artifact_id" uuid,
    "reused_artifact_id" uuid,
    "actual_args" jsonb,
    "returned_rows" bigint,
    "usage" jsonb,
    "error" jsonb,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."run_steps"."run_id" IS '实际执行';

COMMENT ON COLUMN socai2."run_steps"."seq" IS '同Run显示顺序';

COMMENT ON COLUMN socai2."run_steps"."parent_step_id" IS '同Run父阶段；不是跨Run复用';

COMMENT ON COLUMN socai2."run_steps"."retry_of_step_id" IS '同Run失败调用的重试';

COMMENT ON COLUMN socai2."run_steps"."kind" IS 'stage/model/tool/graph/render';

COMMENT ON COLUMN socai2."run_steps"."stage_code" IS 'A1/I1/C1..C6/Q1等版本化阶段码';

COMMENT ON COLUMN socai2."run_steps"."question_id" IS '输入计划中稳定问题ID';

COMMENT ON COLUMN socai2."run_steps"."state" IS '实际状态';

COMMENT ON COLUMN socai2."run_steps"."name" IS '阶段、模型或工具实际名称';

COMMENT ON COLUMN socai2."run_steps"."provider" IS '模型/工具提供者';

COMMENT ON COLUMN socai2."run_steps"."implementation_version" IS '工具合同/模型版本';

COMMENT ON COLUMN socai2."run_steps"."started_at" IS '真实开始';

COMMENT ON COLUMN socai2."run_steps"."ended_at" IS '真实完成';

COMMENT ON COLUMN socai2."run_steps"."input_artifact_id" IS '实际输入/参数原件';

COMMENT ON COLUMN socai2."run_steps"."output_artifact_id" IS '实际输出原件';

COMMENT ON COLUMN socai2."run_steps"."reused_artifact_id" IS '明确复用旧材料，不记为新外部调用';

COMMENT ON COLUMN socai2."run_steps"."actual_args" IS '类型化查询范围/时间/上限及具体参数';

COMMENT ON COLUMN socai2."run_steps"."returned_rows" IS '成功查询实际返回行数；未知/失败不填0';

COMMENT ON COLUMN socai2."run_steps"."usage" IS '模型真实tokens/费用与已知状态；非调用父阶段NULL';

COMMENT ON COLUMN socai2."run_steps"."error" IS '实际错误';

CREATE TABLE IF NOT EXISTS socai2."artifacts" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "alert_id" uuid,
    "incident_id" uuid,
    "case_id" uuid,
    "run_id" uuid,
    "step_id" uuid,
    "kind" text NOT NULL,
    "schema_version" text NOT NULL,
    "content_json" jsonb,
    "content_text" text,
    "blob_ref" text,
    "mime_type" text NOT NULL,
    "file_name" text,
    "sha256" char(64),
    "size_bytes" bigint,
    "captured_at" timestamptz NOT NULL,
    "event_time" timestamptz,
    "material_state" text NOT NULL,
    "source_refs" jsonb NOT NULL,
    "retention" jsonb NOT NULL,
    "created_by" uuid,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."artifacts"."alert_id" IS '非Case告警材料归属';

COMMENT ON COLUMN socai2."artifacts"."incident_id" IS '非Case事件材料归属';

COMMENT ON COLUMN socai2."artifacts"."case_id" IS 'Case材料归属';

COMMENT ON COLUMN socai2."artifacts"."run_id" IS '存在时必须与其父对象一致';

COMMENT ON COLUMN socai2."artifacts"."step_id" IS '实际产生步骤，须属于run_id';

COMMENT ON COLUMN socai2."artifacts"."kind" IS '材料类别';

COMMENT ON COLUMN socai2."artifacts"."schema_version" IS '结构合同版本';

COMMENT ON COLUMN socai2."artifacts"."content_json" IS '结构化保存内容';

COMMENT ON COLUMN socai2."artifacts"."content_text" IS '原始文本/Markdown';

COMMENT ON COLUMN socai2."artifacts"."blob_ref" IS '受控内部对象存储键，不是任意远端URL';

COMMENT ON COLUMN socai2."artifacts"."mime_type" IS '实际内容类型';

COMMENT ON COLUMN socai2."artifacts"."file_name" IS '附件显示名，不作路径';

COMMENT ON COLUMN socai2."artifacts"."sha256" IS '已留存规范字节哈希';

COMMENT ON COLUMN socai2."artifacts"."size_bytes" IS '已留存字节数';

COMMENT ON COLUMN socai2."artifacts"."captured_at" IS '记录取得时间';

COMMENT ON COLUMN socai2."artifacts"."event_time" IS '材料中的发生时间，未知NULL';

COMMENT ON COLUMN socai2."artifacts"."material_state" IS '完整/截断/摘要/不可用';

COMMENT ON COLUMN socai2."artifacts"."source_refs" IS '来源和原材料引用；可为空数组但明确是无来源记录';

COMMENT ON COLUMN socai2."artifacts"."retention" IS '原件大小/原hash/保存大小/截断范围';

COMMENT ON COLUMN socai2."artifacts"."created_by" IS '人工上传人；自动来源由Run/Step明确';

CREATE TABLE IF NOT EXISTS socai2."results" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "case_id" uuid NOT NULL,
    "kind" text NOT NULL,
    "source_run_id" uuid NOT NULL,
    "source_answer_id" uuid,
    "title" text NOT NULL,
    "purpose" text NOT NULL,
    "conclusion" text,
    "conclusion_state" text NOT NULL,
    "conclusion_origin" text NOT NULL,
    "validation_state" text NOT NULL,
    "closing_note" text NOT NULL,
    "findings" jsonb NOT NULL,
    "questions" jsonb NOT NULL,
    "recommendations" jsonb NOT NULL,
    "comparison_result_id" uuid,
    "change_kind" text NOT NULL,
    "change_summary" text,
    "case_impact" jsonb NOT NULL,
    "input_artifact_id" uuid NOT NULL,
    "graph_artifact_id" uuid,
    "report_artifact_id" uuid,
    "supersedes_result_id" uuid,
    "delivery_state" text NOT NULL,
    "created_at" timestamptz NOT NULL,
    "saved_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "saved_by" uuid,
    "operation_key" text NOT NULL,
    "edited_fields" text[] NOT NULL DEFAULT '{}'::text[],
    "edit_note" text,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."results"."case_id" IS '案件';

COMMENT ON COLUMN socai2."results"."kind" IS 'baseline/ai_saved';

COMMENT ON COLUMN socai2."results"."source_run_id" IS '实际来源执行，同Case';

COMMENT ON COLUMN socai2."results"."source_answer_id" IS 'AI保存必有，baseline NULL';

COMMENT ON COLUMN socai2."results"."title" IS '正式记录标题；AI保存可自定义';

COMMENT ON COLUMN socai2."results"."purpose" IS '本轮目标';

COMMENT ON COLUMN socai2."results"."conclusion" IS '有效/不确定结论；无结论NULL';

COMMENT ON COLUMN socai2."results"."conclusion_state" IS '有依据/未决/无法给出';

COMMENT ON COLUMN socai2."results"."conclusion_origin" IS '模型/人工/系统来源';

COMMENT ON COLUMN socai2."results"."validation_state" IS '程序采用或拒绝状态';

COMMENT ON COLUMN socai2."results"."closing_note" IS '每轮收尾说明，系统失败交接也有';

COMMENT ON COLUMN socai2."results"."findings" IS '稳定条目ID、依据、反证和限制';

COMMENT ON COLUMN socai2."results"."questions" IS '本轮问题/答案/缺口';

COMMENT ON COLUMN socai2."results"."recommendations" IS '建议含稳定proposal_id、目标、理由及审批要求';

COMMENT ON COLUMN socai2."results"."comparison_result_id" IS '明确同案已有结果；首次NULL';

COMMENT ON COLUMN socai2."results"."change_kind" IS '比较类型';

COMMENT ON COLUMN socai2."results"."change_summary" IS '相比基线输入/证据/判断变化';

COMMENT ON COLUMN socai2."results"."case_impact" IS '作用范围、可调整认识、不能推广处';

COMMENT ON COLUMN socai2."results"."input_artifact_id" IS '实际当时输入';

COMMENT ON COLUMN socai2."results"."graph_artifact_id" IS '本轮图，无图NULL；不借另一轮冒充';

COMMENT ON COLUMN socai2."results"."report_artifact_id" IS '同版报告，无报告NULL';

COMMENT ON COLUMN socai2."results"."supersedes_result_id" IS '明确修订另建版本，不能自指或跨案';

COMMENT ON COLUMN socai2."results"."delivery_state" IS '正式交付完整性';

COMMENT ON COLUMN socai2."results"."created_at" IS '执行产物形成时间';

COMMENT ON COLUMN socai2."results"."saved_at" IS '正式保存时间；AI保存与答复时间不同';

COMMENT ON COLUMN socai2."results"."saved_by" IS '明确AI保存人；baseline由服务保存';

COMMENT ON COLUMN socai2."results"."operation_key" IS '正式保存请求幂等键';

COMMENT ON COLUMN socai2."results"."edited_fields" IS '保存AI答案时用户改过的字段名；正文修改须origin=human且重新校验；原消息不改';

COMMENT ON COLUMN socai2."results"."edit_note" IS '可选修改说明，不强制增加页面输入';

CREATE TABLE IF NOT EXISTS socai2."result_members" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "case_id" uuid NOT NULL,
    "result_id" uuid NOT NULL,
    "run_id" uuid NOT NULL,
    "alert_id" uuid NOT NULL,
    "assessment_state" text NOT NULL,
    "conclusion_covered" boolean NOT NULL DEFAULT false,
    "assessment" text,
    "limitations" text,
    "evidence_refs" jsonb NOT NULL,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."result_members"."case_id" IS '父案校验';

COMMENT ON COLUMN socai2."result_members"."result_id" IS '正式结果';

COMMENT ON COLUMN socai2."result_members"."run_id" IS '与result.source_run一致';

COMMENT ON COLUMN socai2."result_members"."alert_id" IS '来自本轮run_members';

COMMENT ON COLUMN socai2."result_members"."assessment_state" IS '实际逐成员分析状态';

COMMENT ON COLUMN socai2."result_members"."conclusion_covered" IS '结论明确适用，不代表恶意';

COMMENT ON COLUMN socai2."result_members"."assessment" IS '本成员发现或未决说明';

COMMENT ON COLUMN socai2."result_members"."limitations" IS '限制';

COMMENT ON COLUMN socai2."result_members"."evidence_refs" IS '明确材料及行/字段定位';

CREATE TABLE IF NOT EXISTS socai2."tasks" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "case_id" uuid NOT NULL,
    "current_revision_id" uuid NOT NULL,
    "origin_result_id" uuid,
    "origin_finding_id" text,
    "created_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "created_by" uuid,
    "updated_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "row_version" bigint NOT NULL DEFAULT 1,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."tasks"."case_id" IS '所属Case';

COMMENT ON COLUMN socai2."tasks"."current_revision_id" IS '当前完整版本；延迟FK同事务插入';

COMMENT ON COLUMN socai2."tasks"."origin_result_id" IS '同Case引出事项的结果';

COMMENT ON COLUMN socai2."tasks"."origin_finding_id" IS '该结果findings中的稳定条目ID';

COMMENT ON COLUMN socai2."tasks"."created_at" IS '任务创建';

COMMENT ON COLUMN socai2."tasks"."created_by" IS '创建者';

COMMENT ON COLUMN socai2."tasks"."updated_at" IS '最新实际编辑';

COMMENT ON COLUMN socai2."tasks"."row_version" IS '防旧表单覆盖';

CREATE TABLE IF NOT EXISTS socai2."task_revisions" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "case_id" uuid NOT NULL,
    "task_id" uuid NOT NULL,
    "revision" bigint NOT NULL,
    "title" text NOT NULL,
    "description" text,
    "assignee_id" uuid,
    "due_at" timestamptz,
    "state" text NOT NULL,
    "result_text" text,
    "result_scope" jsonb,
    "source_refs" jsonb NOT NULL DEFAULT '[]'::jsonb,
    "completed_at" timestamptz,
    "completed_by" uuid,
    "changed_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "changed_by" uuid NOT NULL,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."task_revisions"."case_id" IS '同案FK';

COMMENT ON COLUMN socai2."task_revisions"."task_id" IS '事项';

COMMENT ON COLUMN socai2."task_revisions"."revision" IS '从1开始，每次有效编辑+1';

COMMENT ON COLUMN socai2."task_revisions"."title" IS '任务事项，非空';

COMMENT ON COLUMN socai2."task_revisions"."description" IS '工作说明';

COMMENT ON COLUMN socai2."task_revisions"."assignee_id" IS '同租户可选负责人，NULL未分配';

COMMENT ON COLUMN socai2."task_revisions"."due_at" IS '截止时间，可空';

COMMENT ON COLUMN socai2."task_revisions"."state" IS '四种人工状态';

COMMENT ON COLUMN socai2."task_revisions"."result_text" IS '事实反馈，completed必填非空';

COMMENT ON COLUMN socai2."task_revisions"."result_scope" IS '确认范围；完成时须明确，如未知部分写limitations';

COMMENT ON COLUMN socai2."task_revisions"."source_refs" IS '可选资料，不强制上传';

COMMENT ON COLUMN socai2."task_revisions"."completed_at" IS '本次进入完成状态的真实时间';

COMMENT ON COLUMN socai2."task_revisions"."completed_by" IS '本次实际完成人，不是assignee';

COMMENT ON COLUMN socai2."task_revisions"."changed_at" IS '版本编辑时间';

COMMENT ON COLUMN socai2."task_revisions"."changed_by" IS '实际编辑人';

CREATE TABLE IF NOT EXISTS socai2."conversations" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "case_id" uuid NOT NULL,
    "title" text,
    "created_by" uuid NOT NULL,
    "created_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "updated_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "row_version" bigint NOT NULL DEFAULT 1,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."conversations"."case_id" IS '明确案件上下文';

COMMENT ON COLUMN socai2."conversations"."title" IS '会话标题';

COMMENT ON COLUMN socai2."conversations"."created_by" IS '发起用户';

COMMENT ON COLUMN socai2."conversations"."created_at" IS '创建';

COMMENT ON COLUMN socai2."conversations"."updated_at" IS '有真实消息或标题变化时更新';

COMMENT ON COLUMN socai2."conversations"."row_version" IS '标题编辑版本';

CREATE TABLE IF NOT EXISTS socai2."messages" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "case_id" uuid NOT NULL,
    "conversation_id" uuid NOT NULL,
    "sequence" bigint NOT NULL,
    "role" text NOT NULL,
    "content" text,
    "state" text NOT NULL,
    "in_reply_to" uuid,
    "source_run_id" uuid,
    "input_artifact_id" uuid,
    "source_refs" jsonb,
    "client_request_key" text NOT NULL,
    "created_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "answered_at" timestamptz,
    "error" jsonb,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."messages"."case_id" IS '显式同案约束';

COMMENT ON COLUMN socai2."messages"."conversation_id" IS '会话';

COMMENT ON COLUMN socai2."messages"."sequence" IS '同会话顺序';

COMMENT ON COLUMN socai2."messages"."role" IS 'user或assistant';

COMMENT ON COLUMN socai2."messages"."content" IS '真实问题/答复；失败且无答复NULL';

COMMENT ON COLUMN socai2."messages"."state" IS '收取/答复状态';

COMMENT ON COLUMN socai2."messages"."in_reply_to" IS 'assistant指具体用户问题；同会话';

COMMENT ON COLUMN socai2."messages"."source_run_id" IS '真实ai_question执行；用户消息NULL';

COMMENT ON COLUMN socai2."messages"."input_artifact_id" IS 'assistant实际输入；不能保存时重新读取';

COMMENT ON COLUMN socai2."messages"."source_refs" IS '实际引用；无结果NULL';

COMMENT ON COLUMN socai2."messages"."client_request_key" IS '发送/答复去重键，客户端重发不重复执行';

COMMENT ON COLUMN socai2."messages"."created_at" IS '发送/占位时间';

COMMENT ON COLUMN socai2."messages"."answered_at" IS '实际回答完成';

COMMENT ON COLUMN socai2."messages"."error" IS '调用失败状态';

CREATE TABLE IF NOT EXISTS socai2."graph_explorations" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "case_id" uuid NOT NULL,
    "base_result_id" uuid,
    "base_graph_artifact_id" uuid,
    "base_input_artifact_id" uuid NOT NULL,
    "graph_state" jsonb NOT NULL,
    "created_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "created_by" uuid NOT NULL,
    "updated_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "updated_by" uuid NOT NULL,
    "row_version" bigint NOT NULL DEFAULT 1,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."graph_explorations"."case_id" IS '所属案';

COMMENT ON COLUMN socai2."graph_explorations"."base_result_id" IS '明确起始调查结果';

COMMENT ON COLUMN socai2."graph_explorations"."base_graph_artifact_id" IS '该结果图；无图不借其他Run';

COMMENT ON COLUMN socai2."graph_explorations"."base_input_artifact_id" IS '起点成员/证据快照，包含无基础结果时的起点';

COMMENT ON COLUMN socai2."graph_explorations"."graph_state" IS '节点、边、展开/选择/布局和来源';

COMMENT ON COLUMN socai2."graph_explorations"."created_at" IS '首次保存';

COMMENT ON COLUMN socai2."graph_explorations"."created_by" IS '创建人';

COMMENT ON COLUMN socai2."graph_explorations"."updated_at" IS '实际保存';

COMMENT ON COLUMN socai2."graph_explorations"."updated_by" IS '最近保存人';

COMMENT ON COLUMN socai2."graph_explorations"."row_version" IS '画布并发编辑';

CREATE TABLE IF NOT EXISTS socai2."activities" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "operation_id" uuid NOT NULL,
    "actor" jsonb NOT NULL,
    "action" text NOT NULL,
    "subject_alert_id" uuid,
    "subject_incident_id" uuid,
    "subject_case_id" uuid,
    "occurred_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "summary" text NOT NULL,
    "detail" jsonb NOT NULL,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."activities"."operation_id" IS '一次批量操作分组，所有目标同ID';

COMMENT ON COLUMN socai2."activities"."actor" IS '真实人/服务身份和名称快照';

COMMENT ON COLUMN socai2."activities"."action" IS '受版本控制业务动作码，见action_registry合同';

COMMENT ON COLUMN socai2."activities"."subject_alert_id" IS '主对象告警';

COMMENT ON COLUMN socai2."activities"."subject_incident_id" IS '主对象事件';

COMMENT ON COLUMN socai2."activities"."subject_case_id" IS '主对象Case';

COMMENT ON COLUMN socai2."activities"."occurred_at" IS '实际操作时间';

COMMENT ON COLUMN socai2."activities"."summary" IS '可读操作摘要，不能替代结构目标';

COMMENT ON COLUMN socai2."activities"."detail" IS '请求原因和未完成原因，不复制完整原件';

CREATE TABLE IF NOT EXISTS socai2."activity_targets" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "activity_id" uuid NOT NULL,
    "alert_id" uuid,
    "incident_id" uuid,
    "case_id" uuid,
    "task_id" uuid,
    "run_id" uuid,
    "result_id" uuid,
    "comment_id" uuid,
    "before_value" jsonb,
    "after_value" jsonb,
    "result_state" text NOT NULL,
    "reason" text,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."activity_targets"."activity_id" IS '所属实际活动';

COMMENT ON COLUMN socai2."activity_targets"."alert_id" IS '被处理告警';

COMMENT ON COLUMN socai2."activity_targets"."incident_id" IS '被处理事件';

COMMENT ON COLUMN socai2."activity_targets"."case_id" IS '被处理Case';

COMMENT ON COLUMN socai2."activity_targets"."task_id" IS '被处理任务';

COMMENT ON COLUMN socai2."activity_targets"."run_id" IS '被操作执行';

COMMENT ON COLUMN socai2."activity_targets"."result_id" IS '被采用/保存结果';

COMMENT ON COLUMN socai2."activity_targets"."comment_id" IS '评论';

COMMENT ON COLUMN socai2."activity_targets"."before_value" IS '相关变更字段前值；新建NULL';

COMMENT ON COLUMN socai2."activity_targets"."after_value" IS '相关变更字段后值；移除NULL';

COMMENT ON COLUMN socai2."activity_targets"."result_state" IS '实际成功/跳过/失败';

COMMENT ON COLUMN socai2."activity_targets"."reason" IS '跳过/失败原因';

CREATE TABLE IF NOT EXISTS socai2."comments" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "alert_id" uuid,
    "incident_id" uuid,
    "case_id" uuid,
    "body" text NOT NULL,
    "author_id" uuid NOT NULL,
    "author_name_snapshot" text NOT NULL,
    "created_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "edited_at" timestamptz,
    "edited_by" uuid,
    "row_version" bigint NOT NULL DEFAULT 1,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."comments"."alert_id" IS '所属告警';

COMMENT ON COLUMN socai2."comments"."incident_id" IS '所属事件';

COMMENT ON COLUMN socai2."comments"."case_id" IS '所属Case';

COMMENT ON COLUMN socai2."comments"."body" IS '普通评论非空';

COMMENT ON COLUMN socai2."comments"."author_id" IS '实际作者';

COMMENT ON COLUMN socai2."comments"."author_name_snapshot" IS '当时显示名';

COMMENT ON COLUMN socai2."comments"."created_at" IS '创建';

COMMENT ON COLUMN socai2."comments"."edited_at" IS '实际编辑时间';

COMMENT ON COLUMN socai2."comments"."edited_by" IS '实际编辑人';

COMMENT ON COLUMN socai2."comments"."row_version" IS '并发编辑';

CREATE TABLE IF NOT EXISTS socai2."response_links" (
    "id" uuid NOT NULL,
    "tenant_id" uuid NOT NULL,
    "alert_id" uuid,
    "incident_id" uuid,
    "case_id" uuid,
    "result_id" uuid,
    "proposal_id" text,
    "legacy_proposal_ref" jsonb,
    "external_namespace" text NOT NULL,
    "approval_id" text,
    "action_id" text,
    "linked_at" timestamptz NOT NULL DEFAULT transaction_timestamp(),
    "receipt_artifact_id" uuid,
    PRIMARY KEY ("id"),
    UNIQUE ("tenant_id","id"),
    FOREIGN KEY ("tenant_id") REFERENCES public.tenants(id) ON DELETE RESTRICT
);

COMMENT ON COLUMN socai2."response_links"."alert_id" IS '告警所属来源';

COMMENT ON COLUMN socai2."response_links"."incident_id" IS '事件所属来源';

COMMENT ON COLUMN socai2."response_links"."case_id" IS 'Case所属来源';

COMMENT ON COLUMN socai2."response_links"."result_id" IS '正式结果建议';

COMMENT ON COLUMN socai2."response_links"."proposal_id" IS 'recommendations中稳定ID；需result_id';

COMMENT ON COLUMN socai2."response_links"."legacy_proposal_ref" IS '没有新result时已有建议/执行来源';

COMMENT ON COLUMN socai2."response_links"."external_namespace" IS '已有审批执行服务命名空间';

COMMENT ON COLUMN socai2."response_links"."approval_id" IS '真实审批ID，不强转UUID';

COMMENT ON COLUMN socai2."response_links"."action_id" IS '真实动作ID，批准不等于执行';

COMMENT ON COLUMN socai2."response_links"."linked_at" IS '关系建立';

COMMENT ON COLUMN socai2."response_links"."receipt_artifact_id" IS '已有实际回执快照，同归属';

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_materials'::regclass AND conname='alert_materials_scope_key_0') THEN
 ALTER TABLE socai2."alert_materials" ADD CONSTRAINT "alert_materials_scope_key_0" UNIQUE ("tenant_id","alert_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_materials'::regclass AND conname='alert_materials_business_key') THEN
 ALTER TABLE socai2."alert_materials" ADD CONSTRAINT "alert_materials_business_key" UNIQUE ("tenant_id","alert_id","revision");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_assessments'::regclass AND conname='alert_assessments_scope_key_0') THEN
 ALTER TABLE socai2."alert_assessments" ADD CONSTRAINT "alert_assessments_scope_key_0" UNIQUE ("tenant_id","alert_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_assessments'::regclass AND conname='alert_assessments_business_key') THEN
 ALTER TABLE socai2."alert_assessments" ADD CONSTRAINT "alert_assessments_business_key" UNIQUE ("tenant_id","operation_key");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_diagnoses'::regclass AND conname='incident_diagnoses_scope_key_0') THEN
 ALTER TABLE socai2."incident_diagnoses" ADD CONSTRAINT "incident_diagnoses_scope_key_0" UNIQUE ("tenant_id","incident_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_diagnoses'::regclass AND conname='incident_diagnoses_business_key') THEN
 ALTER TABLE socai2."incident_diagnoses" ADD CONSTRAINT "incident_diagnoses_business_key" UNIQUE ("tenant_id","incident_id","revision");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_diagnoses'::regclass AND conname='incident_diagnoses_run_key') THEN
 ALTER TABLE socai2."incident_diagnoses" ADD CONSTRAINT "incident_diagnoses_run_key" UNIQUE ("tenant_id","source_run_id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessments'::regclass AND conname='case_assessments_scope_key_0') THEN
 ALTER TABLE socai2."case_assessments" ADD CONSTRAINT "case_assessments_scope_key_0" UNIQUE ("tenant_id","case_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessments'::regclass AND conname='case_assessments_business_key') THEN
 ALTER TABLE socai2."case_assessments" ADD CONSTRAINT "case_assessments_business_key" UNIQUE ("tenant_id","case_id","revision");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessments'::regclass AND conname='case_assessments_operation_key') THEN
 ALTER TABLE socai2."case_assessments" ADD CONSTRAINT "case_assessments_operation_key" UNIQUE ("tenant_id","operation_key");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.task_revisions'::regclass AND conname='task_revisions_scope_key_0') THEN
 ALTER TABLE socai2."task_revisions" ADD CONSTRAINT "task_revisions_scope_key_0" UNIQUE ("tenant_id","case_id","task_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.task_revisions'::regclass AND conname='task_revisions_scope_key_1') THEN
 ALTER TABLE socai2."task_revisions" ADD CONSTRAINT "task_revisions_scope_key_1" UNIQUE ("tenant_id","case_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.task_revisions'::regclass AND conname='task_revisions_business_key') THEN
 ALTER TABLE socai2."task_revisions" ADD CONSTRAINT "task_revisions_business_key" UNIQUE ("tenant_id","task_id","revision");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.tasks'::regclass AND conname='tasks_scope_key_0') THEN
 ALTER TABLE socai2."tasks" ADD CONSTRAINT "tasks_scope_key_0" UNIQUE ("tenant_id","case_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_scope_key_0') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_scope_key_0" UNIQUE ("tenant_id","case_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_scope_key_1') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_scope_key_1" UNIQUE ("tenant_id","alert_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_scope_key_2') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_scope_key_2" UNIQUE ("tenant_id","incident_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_members'::regclass AND conname='run_members_scope_key_0') THEN
 ALTER TABLE socai2."run_members" ADD CONSTRAINT "run_members_scope_key_0" UNIQUE ("tenant_id","case_id","run_id","alert_id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_members'::regclass AND conname='run_members_business_key') THEN
 ALTER TABLE socai2."run_members" ADD CONSTRAINT "run_members_business_key" UNIQUE ("tenant_id","run_id","alert_id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_scope_key_0') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_scope_key_0" UNIQUE ("tenant_id","run_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_business_key') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_business_key" UNIQUE ("tenant_id","run_id","seq");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_scope_key_0') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_scope_key_0" UNIQUE ("tenant_id","case_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_scope_key_1') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_scope_key_1" UNIQUE ("tenant_id","alert_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_scope_key_2') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_scope_key_2" UNIQUE ("tenant_id","incident_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_scope_key_3') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_scope_key_3" UNIQUE ("tenant_id","run_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_scope_key_0') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_scope_key_0" UNIQUE ("tenant_id","case_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_scope_key_1') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_scope_key_1" UNIQUE ("tenant_id","case_id","source_run_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_business_key') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_business_key" UNIQUE ("tenant_id","operation_key");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.conversations'::regclass AND conname='conversations_scope_key_0') THEN
 ALTER TABLE socai2."conversations" ADD CONSTRAINT "conversations_scope_key_0" UNIQUE ("tenant_id","case_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_scope_key_0') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_scope_key_0" UNIQUE ("tenant_id","case_id","conversation_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_scope_key_1') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_scope_key_1" UNIQUE ("tenant_id","case_id","id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_business_key') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_business_key" UNIQUE ("tenant_id","conversation_id","sequence");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_request_key') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_request_key" UNIQUE ("tenant_id","conversation_id","client_request_key");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_source_identity') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_source_identity" UNIQUE ("tenant_id","source_namespace","source_identity_key");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_source_identity') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_source_identity" UNIQUE ("tenant_id","source_namespace","source_incident_id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_source_refs'::regclass AND conname='alert_source_refs_business_key') THEN
 ALTER TABLE socai2."alert_source_refs" ADD CONSTRAINT "alert_source_refs_business_key" UNIQUE ("tenant_id","material_id","source_namespace","source_event_id","relation_kind");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_objects'::regclass AND conname='alert_objects_business_key') THEN
 ALTER TABLE socai2."alert_objects" ADD CONSTRAINT "alert_objects_business_key" UNIQUE ("tenant_id","material_id","object_key","source_path");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_alerts'::regclass AND conname='incident_alerts_business_key') THEN
 ALTER TABLE socai2."incident_alerts" ADD CONSTRAINT "incident_alerts_business_key" UNIQUE ("tenant_id","alert_id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_alerts'::regclass AND conname='case_alerts_business_key') THEN
 ALTER TABLE socai2."case_alerts" ADD CONSTRAINT "case_alerts_business_key" UNIQUE ("tenant_id","case_id","alert_id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_incidents'::regclass AND conname='case_incidents_business_key') THEN
 ALTER TABLE socai2."case_incidents" ADD CONSTRAINT "case_incidents_business_key" UNIQUE ("tenant_id","case_id","incident_id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessment_members'::regclass AND conname='case_assessment_members_business_key') THEN
 ALTER TABLE socai2."case_assessment_members" ADD CONSTRAINT "case_assessment_members_business_key" UNIQUE ("tenant_id","assessment_id","alert_id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.result_members'::regclass AND conname='result_members_business_key') THEN
 ALTER TABLE socai2."result_members" ADD CONSTRAINT "result_members_business_key" UNIQUE ("tenant_id","result_id","alert_id");
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_source_namespace_nonblank') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_source_namespace_nonblank" CHECK (length(btrim("source_namespace")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_source_identity_key_nonblank') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_source_identity_key_nonblank" CHECK (length(btrim("source_identity_key")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_title_nonblank') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_title_nonblank" CHECK (length(btrim("title")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_severity_enum') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_severity_enum" CHECK ("severity" IN ('info','low','medium','high','critical'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_event_time_source_enum') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_event_time_source_enum" CHECK ("event_time_source" IN ('source','derived_source','unknown'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_handling_status_enum') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_handling_status_enum" CHECK ("handling_status" IN ('new','in_progress','completed','unknown'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_disposition_enum') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_disposition_enum" CHECK ("disposition" IN ('true_positive','false_positive','benign','needs_review'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_assignment_state_enum') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_assignment_state_enum" CHECK ("assignment_state" IN ('unassigned','assigned','unresolved'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_priority_state_enum') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_priority_state_enum" CHECK ("priority_state" IN ('not_provided','not_computed','disabled','failed','available','legacy_unverified'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_priority_basis_json_type') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_priority_basis_json_type" CHECK (jsonb_typeof("priority_basis") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_row_version_range') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_row_version_range" CHECK ("row_version" > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_assignment') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_assignment" CHECK ((assignment_state='assigned') = (owner_id IS NOT NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_unresolved_owner') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_unresolved_owner" CHECK (assignment_state <> 'unresolved' OR nullif(btrim(owner_source_value),'') IS NOT NULL);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_priority') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_priority" CHECK ((priority_state='available' AND priority_value IS NOT NULL AND priority_value BETWEEN 0 AND 100 AND nullif(btrim(priority_source),'') IS NOT NULL) OR (priority_state<>'available' AND priority_value IS NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_event_time') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_event_time" CHECK ((event_time_source='unknown') = (event_time IS NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_time_order') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_time_order" CHECK (first_seen_at IS NULL OR last_seen_at IS NULL OR first_seen_at<=last_seen_at);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_materials'::regclass AND conname='alert_materials_revision_range') THEN
 ALTER TABLE socai2."alert_materials" ADD CONSTRAINT "alert_materials_revision_range" CHECK ("revision" > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_materials'::regclass AND conname='alert_materials_detection_json_type') THEN
 ALTER TABLE socai2."alert_materials" ADD CONSTRAINT "alert_materials_detection_json_type" CHECK (jsonb_typeof("detection") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_materials'::regclass AND conname='alert_materials_enrichment_json_type') THEN
 ALTER TABLE socai2."alert_materials" ADD CONSTRAINT "alert_materials_enrichment_json_type" CHECK (jsonb_typeof("enrichment") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_materials'::regclass AND conname='alert_materials_source_scope_json_type') THEN
 ALTER TABLE socai2."alert_materials" ADD CONSTRAINT "alert_materials_source_scope_json_type" CHECK (jsonb_typeof("source_scope") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_materials'::regclass AND conname='alert_materials_material_state_enum') THEN
 ALTER TABLE socai2."alert_materials" ADD CONSTRAINT "alert_materials_material_state_enum" CHECK ("material_state" IN ('complete','truncated','summary_only','unavailable'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_materials'::regclass AND conname='alert_materials_sha256_sha') THEN
 ALTER TABLE socai2."alert_materials" ADD CONSTRAINT "alert_materials_sha256_sha" CHECK ("sha256" ~ '^[0-9a-f]{64}$');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_materials'::regclass AND conname='alert_materials_retention_json_type') THEN
 ALTER TABLE socai2."alert_materials" ADD CONSTRAINT "alert_materials_retention_json_type" CHECK (jsonb_typeof("retention") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_source_refs'::regclass AND conname='alert_source_refs_source_namespace_nonblank') THEN
 ALTER TABLE socai2."alert_source_refs" ADD CONSTRAINT "alert_source_refs_source_namespace_nonblank" CHECK (length(btrim("source_namespace")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_source_refs'::regclass AND conname='alert_source_refs_relation_kind_enum') THEN
 ALTER TABLE socai2."alert_source_refs" ADD CONSTRAINT "alert_source_refs_relation_kind_enum" CHECK ("relation_kind" IN ('source_event','threshold_candidate','sequence_candidate','related_record'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_objects'::regclass AND conname='alert_objects_object_key_nonblank') THEN
 ALTER TABLE socai2."alert_objects" ADD CONSTRAINT "alert_objects_object_key_nonblank" CHECK (length(btrim("object_key")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_objects'::regclass AND conname='alert_objects_object_type_enum') THEN
 ALTER TABLE socai2."alert_objects" ADD CONSTRAINT "alert_objects_object_type_enum" CHECK ("object_type" IN ('host','user','ip','domain','url','file','hash','process','email','application','cloud_resource','technique','other'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_objects'::regclass AND conname='alert_objects_object_role_enum') THEN
 ALTER TABLE socai2."alert_objects" ADD CONSTRAINT "alert_objects_object_role_enum" CHECK ("object_role" IN ('entity','ioc','both'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_objects'::regclass AND conname='alert_objects_namespace_nonblank') THEN
 ALTER TABLE socai2."alert_objects" ADD CONSTRAINT "alert_objects_namespace_nonblank" CHECK (length(btrim("namespace")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_objects'::regclass AND conname='alert_objects_raw_value_nonblank') THEN
 ALTER TABLE socai2."alert_objects" ADD CONSTRAINT "alert_objects_raw_value_nonblank" CHECK (length(btrim("raw_value")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_objects'::regclass AND conname='alert_objects_normalized_value_nonblank') THEN
 ALTER TABLE socai2."alert_objects" ADD CONSTRAINT "alert_objects_normalized_value_nonblank" CHECK (length(btrim("normalized_value")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_objects'::regclass AND conname='alert_objects_attributes_json_type') THEN
 ALTER TABLE socai2."alert_objects" ADD CONSTRAINT "alert_objects_attributes_json_type" CHECK (jsonb_typeof("attributes") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_objects'::regclass AND conname='alert_objects_asset_match_state_enum') THEN
 ALTER TABLE socai2."alert_objects" ADD CONSTRAINT "alert_objects_asset_match_state_enum" CHECK ("asset_match_state" IN ('matched','ambiguous','not_found','not_checked'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_objects'::regclass AND conname='alert_objects_asset_ref_json_type') THEN
 ALTER TABLE socai2."alert_objects" ADD CONSTRAINT "alert_objects_asset_ref_json_type" CHECK (jsonb_typeof("asset_ref") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_objects'::regclass AND conname='alert_objects_match_basis_json_type') THEN
 ALTER TABLE socai2."alert_objects" ADD CONSTRAINT "alert_objects_match_basis_json_type" CHECK (jsonb_typeof("match_basis") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_objects'::regclass AND conname='alert_objects_other_type') THEN
 ALTER TABLE socai2."alert_objects" ADD CONSTRAINT "alert_objects_other_type" CHECK (object_type<>'other' OR nullif(btrim(source_type),'') IS NOT NULL);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_objects'::regclass AND conname='alert_objects_asset_match') THEN
 ALTER TABLE socai2."alert_objects" ADD CONSTRAINT "alert_objects_asset_match" CHECK (asset_match_state<>'matched' OR (asset_ref IS NOT NULL AND match_basis IS NOT NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_assessments'::regclass AND conname='alert_assessments_kind_enum') THEN
 ALTER TABLE socai2."alert_assessments" ADD CONSTRAINT "alert_assessments_kind_enum" CHECK ("kind" IN ('triage','human_feedback'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_assessments'::regclass AND conname='alert_assessments_legacy_execution_ref_json_type') THEN
 ALTER TABLE socai2."alert_assessments" ADD CONSTRAINT "alert_assessments_legacy_execution_ref_json_type" CHECK (jsonb_typeof("legacy_execution_ref") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_assessments'::regclass AND conname='alert_assessments_verdict_enum') THEN
 ALTER TABLE socai2."alert_assessments" ADD CONSTRAINT "alert_assessments_verdict_enum" CHECK ("verdict" IN ('true_positive','false_positive','benign','needs_review'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_assessments'::regclass AND conname='alert_assessments_score_state_enum') THEN
 ALTER TABLE socai2."alert_assessments" ADD CONSTRAINT "alert_assessments_score_state_enum" CHECK ("score_state" IN ('not_provided','not_computed','disabled','failed','available','legacy_unverified'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_assessments'::regclass AND conname='alert_assessments_recommendations_json_type') THEN
 ALTER TABLE socai2."alert_assessments" ADD CONSTRAINT "alert_assessments_recommendations_json_type" CHECK (jsonb_typeof("recommendations") = 'array');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_assessments'::regclass AND conname='alert_assessments_actor_json_type') THEN
 ALTER TABLE socai2."alert_assessments" ADD CONSTRAINT "alert_assessments_actor_json_type" CHECK (jsonb_typeof("actor") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_assessments'::regclass AND conname='alert_assessments_operation_key_nonblank') THEN
 ALTER TABLE socai2."alert_assessments" ADD CONSTRAINT "alert_assessments_operation_key_nonblank" CHECK (length(btrim("operation_key")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_assessments'::regclass AND conname='alert_assessments_confidence') THEN
 ALTER TABLE socai2."alert_assessments" ADD CONSTRAINT "alert_assessments_confidence" CHECK ((score_state='available' AND confidence IS NOT NULL AND confidence BETWEEN 0 AND 1) OR (score_state<>'available' AND confidence IS NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_assessments'::regclass AND conname='alert_assessments_human_no_score') THEN
 ALTER TABLE socai2."alert_assessments" ADD CONSTRAINT "alert_assessments_human_no_score" CHECK (kind<>'human_feedback' OR confidence IS NULL);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_source_namespace_nonblank') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_source_namespace_nonblank" CHECK (length(btrim("source_namespace")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_source_incident_id_nonblank') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_source_incident_id_nonblank" CHECK (length(btrim("source_incident_id")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_title_nonblank') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_title_nonblank" CHECK (length(btrim("title")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_handling_status_enum') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_handling_status_enum" CHECK ("handling_status" IN ('new','in_progress','resolved','unknown'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_assignment_state_enum') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_assignment_state_enum" CHECK ("assignment_state" IN ('unassigned','assigned','unresolved'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_severity_override_enum') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_severity_override_enum" CHECK ("severity_override" IN ('info','low','medium','high','critical'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_priority_state_enum') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_priority_state_enum" CHECK ("priority_state" IN ('not_provided','not_computed','disabled','failed','available','legacy_unverified'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_priority_basis_json_type') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_priority_basis_json_type" CHECK (jsonb_typeof("priority_basis") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_row_version_range') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_row_version_range" CHECK ("row_version" > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_assignment') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_assignment" CHECK ((assignment_state='assigned') = (owner_id IS NOT NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_unresolved_owner') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_unresolved_owner" CHECK (assignment_state <> 'unresolved' OR nullif(btrim(owner_source_value),'') IS NOT NULL);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_priority') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_priority" CHECK ((priority_state='available' AND priority_value IS NOT NULL AND priority_value BETWEEN 0 AND 100 AND nullif(btrim(priority_source),'') IS NOT NULL) OR (priority_state<>'available' AND priority_value IS NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_severity_override') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_severity_override" CHECK ((severity_override IS NULL AND severity_override_reason IS NULL AND severity_override_at IS NULL AND severity_override_by IS NULL) OR (severity_override IS NOT NULL AND nullif(btrim(severity_override_reason),'') IS NOT NULL AND severity_override_at IS NOT NULL AND severity_override_by IS NOT NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_alerts'::regclass AND conname='incident_alerts_membership_source_enum') THEN
 ALTER TABLE socai2."incident_alerts" ADD CONSTRAINT "incident_alerts_membership_source_enum" CHECK ("membership_source" IN ('fusion','manual','incident_link','move','legacy'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_alerts'::regclass AND conname='incident_alerts_correlation_basis_json_type') THEN
 ALTER TABLE socai2."incident_alerts" ADD CONSTRAINT "incident_alerts_correlation_basis_json_type" CHECK (jsonb_typeof("correlation_basis") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_diagnoses'::regclass AND conname='incident_diagnoses_revision_range') THEN
 ALTER TABLE socai2."incident_diagnoses" ADD CONSTRAINT "incident_diagnoses_revision_range" CHECK ("revision" > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_diagnoses'::regclass AND conname='incident_diagnoses_state_enum') THEN
 ALTER TABLE socai2."incident_diagnoses" ADD CONSTRAINT "incident_diagnoses_state_enum" CHECK ("state" IN ('running','completed','failed','cancelled','unknown'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_diagnoses'::regclass AND conname='incident_diagnoses_diagnosis_json_type') THEN
 ALTER TABLE socai2."incident_diagnoses" ADD CONSTRAINT "incident_diagnoses_diagnosis_json_type" CHECK (jsonb_typeof("diagnosis") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_diagnoses'::regclass AND conname='incident_diagnoses_open_questions_json_type') THEN
 ALTER TABLE socai2."incident_diagnoses" ADD CONSTRAINT "incident_diagnoses_open_questions_json_type" CHECK (jsonb_typeof("open_questions") = 'array');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_diagnoses'::regclass AND conname='incident_diagnoses_source_fingerprint_sha') THEN
 ALTER TABLE socai2."incident_diagnoses" ADD CONSTRAINT "incident_diagnoses_source_fingerprint_sha" CHECK ("source_fingerprint" ~ '^[0-9a-f]{64}$');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_diagnoses'::regclass AND conname='incident_diagnoses_error_json_type') THEN
 ALTER TABLE socai2."incident_diagnoses" ADD CONSTRAINT "incident_diagnoses_error_json_type" CHECK (jsonb_typeof("error") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_title_nonblank') THEN
 ALTER TABLE socai2."cases" ADD CONSTRAINT "cases_title_nonblank" CHECK (length(btrim("title")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_handling_status_enum') THEN
 ALTER TABLE socai2."cases" ADD CONSTRAINT "cases_handling_status_enum" CHECK ("handling_status" IN ('new','in_progress','resolved','unknown'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_severity_enum') THEN
 ALTER TABLE socai2."cases" ADD CONSTRAINT "cases_severity_enum" CHECK ("severity" IN ('info','low','medium','high','critical'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_assignment_state_enum') THEN
 ALTER TABLE socai2."cases" ADD CONSTRAINT "cases_assignment_state_enum" CHECK ("assignment_state" IN ('unassigned','assigned','unresolved'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_priority_state_enum') THEN
 ALTER TABLE socai2."cases" ADD CONSTRAINT "cases_priority_state_enum" CHECK ("priority_state" IN ('not_provided','not_computed','disabled','failed','available','legacy_unverified'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_priority_basis_json_type') THEN
 ALTER TABLE socai2."cases" ADD CONSTRAINT "cases_priority_basis_json_type" CHECK (jsonb_typeof("priority_basis") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_scope_revision_range') THEN
 ALTER TABLE socai2."cases" ADD CONSTRAINT "cases_scope_revision_range" CHECK ("scope_revision" >= 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_row_version_range') THEN
 ALTER TABLE socai2."cases" ADD CONSTRAINT "cases_row_version_range" CHECK ("row_version" > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_legacy_ref_json_type') THEN
 ALTER TABLE socai2."cases" ADD CONSTRAINT "cases_legacy_ref_json_type" CHECK (jsonb_typeof("legacy_ref") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_assignment') THEN
 ALTER TABLE socai2."cases" ADD CONSTRAINT "cases_assignment" CHECK ((assignment_state='assigned') = (owner_id IS NOT NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_unresolved_owner') THEN
 ALTER TABLE socai2."cases" ADD CONSTRAINT "cases_unresolved_owner" CHECK (assignment_state <> 'unresolved' OR nullif(btrim(owner_source_value),'') IS NOT NULL);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_priority') THEN
 ALTER TABLE socai2."cases" ADD CONSTRAINT "cases_priority" CHECK ((priority_state='available' AND priority_value IS NOT NULL AND priority_value BETWEEN 0 AND 100 AND nullif(btrim(priority_source),'') IS NOT NULL) OR (priority_state<>'available' AND priority_value IS NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_alerts'::regclass AND conname='case_alerts_membership_source_enum') THEN
 ALTER TABLE socai2."case_alerts" ADD CONSTRAINT "case_alerts_membership_source_enum" CHECK ("membership_source" IN ('fusion','manual','incident_link','move','legacy'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessments'::regclass AND conname='case_assessments_revision_range') THEN
 ALTER TABLE socai2."case_assessments" ADD CONSTRAINT "case_assessments_revision_range" CHECK ("revision" > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessments'::regclass AND conname='case_assessments_origin_enum') THEN
 ALTER TABLE socai2."case_assessments" ADD CONSTRAINT "case_assessments_origin_enum" CHECK ("origin" IN ('model','human','system','legacy'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessments'::regclass AND conname='case_assessments_validity_enum') THEN
 ALTER TABLE socai2."case_assessments" ADD CONSTRAINT "case_assessments_validity_enum" CHECK ("validity" IN ('not_checked','accepted','rejected','system_only','legacy_unverified'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessments'::regclass AND conname='case_assessments_scope_revision_range') THEN
 ALTER TABLE socai2."case_assessments" ADD CONSTRAINT "case_assessments_scope_revision_range" CHECK ("scope_revision" >= 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessments'::regclass AND conname='case_assessments_actor_json_type') THEN
 ALTER TABLE socai2."case_assessments" ADD CONSTRAINT "case_assessments_actor_json_type" CHECK (jsonb_typeof("actor") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessments'::regclass AND conname='case_assessments_operation_key_nonblank') THEN
 ALTER TABLE socai2."case_assessments" ADD CONSTRAINT "case_assessments_operation_key_nonblank" CHECK (length(btrim("operation_key")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_kind_enum') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_kind_enum" CHECK ("kind" IN ('alert_basic','incident_diagnosis','baseline','ai_question'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_title_nonblank') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_title_nonblank" CHECK (length(btrim("title")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_purpose_nonblank') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_purpose_nonblank" CHECK (length(btrim("purpose")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_trigger_enum') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_trigger_enum" CHECK ("trigger" IN ('ingested','refresh','case_created','members_changed','manual','question','retry'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_scope_revision_range') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_scope_revision_range" CHECK ("scope_revision" >= 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_scope_kind_enum') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_scope_kind_enum" CHECK ("scope_kind" IN ('whole_case','selected_alerts','explicit_objects'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_state_enum') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_state_enum" CHECK ("state" IN ('pending_update','running','unknown','completed','failed','cancelled'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_operation_key_nonblank') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_operation_key_nonblank" CHECK (length(btrim("operation_key")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_request_hash_sha') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_request_hash_sha" CHECK ("request_hash" ~ '^[0-9a-f]{64}$');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_delivery_state_enum') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_delivery_state_enum" CHECK ("delivery_state" IN ('none','partial','complete','unknown'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_limits_json_type') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_limits_json_type" CHECK (jsonb_typeof("limits") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_row_version_range') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_row_version_range" CHECK ("row_version" > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_one_parent') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_one_parent" CHECK (num_nonnulls(alert_id,incident_id,case_id)=1);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_kind_parent') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_kind_parent" CHECK ((kind='alert_basic' AND alert_id IS NOT NULL) OR (kind='incident_diagnosis' AND incident_id IS NOT NULL) OR (kind IN ('baseline','ai_question') AND case_id IS NOT NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_case_scope') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_case_scope" CHECK ((case_id IS NULL AND scope_revision IS NULL AND scope_kind IS NULL) OR (case_id IS NOT NULL AND scope_revision IS NOT NULL AND scope_kind IS NOT NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_baseline_whole') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_baseline_whole" CHECK (kind<>'baseline' OR scope_kind='whole_case');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_pending_baseline') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_pending_baseline" CHECK (state<>'pending_update' OR (kind='baseline' AND started_at IS NULL AND ended_at IS NULL AND input_artifact_id IS NULL AND operation_key IS NULL AND request_hash IS NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_start_fields') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_start_fields" CHECK (state NOT IN ('running','unknown','completed','failed') OR (started_at IS NOT NULL AND input_artifact_id IS NOT NULL AND executor_version IS NOT NULL AND operation_key IS NOT NULL AND request_hash IS NOT NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_end_fields') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_end_fields" CHECK ((state IN ('completed','failed','cancelled')) = (ended_at IS NOT NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_time_order') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_time_order" CHECK (ended_at IS NULL OR started_at IS NULL OR ended_at>=started_at);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_window') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_window" CHECK ((window_start IS NULL AND window_end IS NULL) OR (window_start IS NOT NULL AND window_end IS NOT NULL AND window_start<=window_end));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_request_pair') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_request_pair" CHECK ((operation_key IS NULL)=(request_hash IS NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_retry_self') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_retry_self" CHECK (retry_of_run_id IS DISTINCT FROM id);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_members'::regclass AND conname='run_members_read_state_enum') THEN
 ALTER TABLE socai2."run_members" ADD CONSTRAINT "run_members_read_state_enum" CHECK ("read_state" IN ('not_read','read','missing','denied','failed'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_members'::regclass AND conname='run_members_analysis_state_enum') THEN
 ALTER TABLE socai2."run_members" ADD CONSTRAINT "run_members_analysis_state_enum" CHECK ("analysis_state" IN ('not_analyzed','analyzed','unresolved','excluded'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_members'::regclass AND conname='run_members_read_material') THEN
 ALTER TABLE socai2."run_members" ADD CONSTRAINT "run_members_read_material" CHECK (read_state<>'read' OR material_id IS NOT NULL);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_seq_range') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_seq_range" CHECK ("seq" > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_kind_enum') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_kind_enum" CHECK ("kind" IN ('stage','model','tool','graph','render'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_state_enum') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_state_enum" CHECK ("state" IN ('planned','running','completed','failed','timeout','cancelled','skipped','unknown'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_actual_args_json_type') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_actual_args_json_type" CHECK (jsonb_typeof("actual_args") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_returned_rows_range') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_returned_rows_range" CHECK ("returned_rows" >= 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_usage_json_type') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_usage_json_type" CHECK (jsonb_typeof("usage") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_error_json_type') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_error_json_type" CHECK (jsonb_typeof("error") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_not_self') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_not_self" CHECK (parent_step_id IS DISTINCT FROM id AND retry_of_step_id IS DISTINCT FROM id);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_time_order') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_time_order" CHECK (ended_at IS NULL OR started_at IS NULL OR ended_at>=started_at);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_query_rows') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_query_rows" CHECK (returned_rows IS NULL OR (kind='tool' AND state='completed' AND returned_rows>=0));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_no_parent_cost') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_no_parent_cost" CHECK (kind<>'stage' OR usage IS NULL);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_kind_enum') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_kind_enum" CHECK ("kind" IN ('input_snapshot','model_request','model_response','tool_request','tool_response','domain_analysis','deep_analysis','attack_chain','attack_path','alert_graph','report_json','report_markdown','attachment','source_snapshot','handoff','query_plan','alert_explanation'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_sha256_sha') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_sha256_sha" CHECK ("sha256" ~ '^[0-9a-f]{64}$');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_size_bytes_range') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_size_bytes_range" CHECK ("size_bytes" >= 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_material_state_enum') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_material_state_enum" CHECK ("material_state" IN ('complete','truncated','summary_only','unavailable'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_source_refs_json_type') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_source_refs_json_type" CHECK (jsonb_typeof("source_refs") = 'array');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_retention_json_type') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_retention_json_type" CHECK (jsonb_typeof("retention") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_one_parent') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_one_parent" CHECK (num_nonnulls(alert_id,incident_id,case_id)=1);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_content') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_content" CHECK (num_nonnulls(content_json,content_text,blob_ref)=1 OR (material_state='unavailable' AND num_nonnulls(content_json,content_text,blob_ref)=0 AND nullif(retention->>'reason','') IS NOT NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_step_has_run') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_step_has_run" CHECK (step_id IS NULL OR run_id IS NOT NULL);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_kind_enum') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_kind_enum" CHECK ("kind" IN ('baseline','ai_saved'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_title_nonblank') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_title_nonblank" CHECK (length(btrim("title")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_purpose_nonblank') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_purpose_nonblank" CHECK (length(btrim("purpose")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_conclusion_state_enum') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_conclusion_state_enum" CHECK ("conclusion_state" IN ('supported','uncertain','unavailable'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_conclusion_origin_enum') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_conclusion_origin_enum" CHECK ("conclusion_origin" IN ('model','human','system','legacy'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_validation_state_enum') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_validation_state_enum" CHECK ("validation_state" IN ('not_checked','accepted','rejected','system_only','legacy_unverified'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_findings_json_type') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_findings_json_type" CHECK (jsonb_typeof("findings") = 'array');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_questions_json_type') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_questions_json_type" CHECK (jsonb_typeof("questions") = 'array');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_recommendations_json_type') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_recommendations_json_type" CHECK (jsonb_typeof("recommendations") = 'array');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_change_kind_enum') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_change_kind_enum" CHECK ("change_kind" IN ('initial','unchanged','expanded','revised','withdrawn','not_comparable'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_case_impact_json_type') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_case_impact_json_type" CHECK (jsonb_typeof("case_impact") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_delivery_state_enum') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_delivery_state_enum" CHECK ("delivery_state" IN ('none','partial','complete','unknown'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_operation_key_nonblank') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_operation_key_nonblank" CHECK (length(btrim("operation_key")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_answer_kind') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_answer_kind" CHECK ((kind='ai_saved')=(source_answer_id IS NOT NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_conclusion') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_conclusion" CHECK ((conclusion_state='unavailable' AND conclusion IS NULL) OR (conclusion_state<>'unavailable' AND nullif(btrim(conclusion),'') IS NOT NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_comparison_self') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_comparison_self" CHECK (comparison_result_id IS DISTINCT FROM id AND supersedes_result_id IS DISTINCT FROM id);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_initial_comparison') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_initial_comparison" CHECK (change_kind<>'initial' OR comparison_result_id IS NULL);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_human_edit') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_human_edit" CHECK (NOT ('conclusion'=ANY(edited_fields)) OR conclusion_origin='human');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.result_members'::regclass AND conname='result_members_assessment_state_enum') THEN
 ALTER TABLE socai2."result_members" ADD CONSTRAINT "result_members_assessment_state_enum" CHECK ("assessment_state" IN ('not_analyzed','analyzed','unresolved','excluded'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.result_members'::regclass AND conname='result_members_evidence_refs_json_type') THEN
 ALTER TABLE socai2."result_members" ADD CONSTRAINT "result_members_evidence_refs_json_type" CHECK (jsonb_typeof("evidence_refs") = 'array');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.result_members'::regclass AND conname='result_members_coverage') THEN
 ALTER TABLE socai2."result_members" ADD CONSTRAINT "result_members_coverage" CHECK (NOT conclusion_covered OR assessment_state IN ('analyzed','unresolved'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.tasks'::regclass AND conname='tasks_row_version_range') THEN
 ALTER TABLE socai2."tasks" ADD CONSTRAINT "tasks_row_version_range" CHECK ("row_version" > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.tasks'::regclass AND conname='tasks_finding_source') THEN
 ALTER TABLE socai2."tasks" ADD CONSTRAINT "tasks_finding_source" CHECK (origin_finding_id IS NULL OR origin_result_id IS NOT NULL);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.task_revisions'::regclass AND conname='task_revisions_revision_range') THEN
 ALTER TABLE socai2."task_revisions" ADD CONSTRAINT "task_revisions_revision_range" CHECK ("revision" > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.task_revisions'::regclass AND conname='task_revisions_title_nonblank') THEN
 ALTER TABLE socai2."task_revisions" ADD CONSTRAINT "task_revisions_title_nonblank" CHECK (length(btrim("title")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.task_revisions'::regclass AND conname='task_revisions_state_enum') THEN
 ALTER TABLE socai2."task_revisions" ADD CONSTRAINT "task_revisions_state_enum" CHECK ("state" IN ('not_started','in_progress','completed','cancelled'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.task_revisions'::regclass AND conname='task_revisions_result_scope_json_type') THEN
 ALTER TABLE socai2."task_revisions" ADD CONSTRAINT "task_revisions_result_scope_json_type" CHECK (jsonb_typeof("result_scope") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.task_revisions'::regclass AND conname='task_revisions_source_refs_json_type') THEN
 ALTER TABLE socai2."task_revisions" ADD CONSTRAINT "task_revisions_source_refs_json_type" CHECK (jsonb_typeof("source_refs") = 'array');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.task_revisions'::regclass AND conname='task_revisions_completed_feedback') THEN
 ALTER TABLE socai2."task_revisions" ADD CONSTRAINT "task_revisions_completed_feedback" CHECK (state<>'completed' OR (nullif(btrim(result_text),'') IS NOT NULL AND result_scope IS NOT NULL AND completed_at IS NOT NULL AND completed_by IS NOT NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.task_revisions'::regclass AND conname='task_revisions_completion_pair') THEN
 ALTER TABLE socai2."task_revisions" ADD CONSTRAINT "task_revisions_completion_pair" CHECK ((completed_at IS NULL)=(completed_by IS NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.conversations'::regclass AND conname='conversations_title_nonblank') THEN
 ALTER TABLE socai2."conversations" ADD CONSTRAINT "conversations_title_nonblank" CHECK (length(btrim("title")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.conversations'::regclass AND conname='conversations_row_version_range') THEN
 ALTER TABLE socai2."conversations" ADD CONSTRAINT "conversations_row_version_range" CHECK ("row_version" > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_sequence_range') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_sequence_range" CHECK ("sequence" > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_role_enum') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_role_enum" CHECK ("role" IN ('user','assistant'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_state_enum') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_state_enum" CHECK ("state" IN ('accepted','running','completed','failed','cancelled','unknown'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_source_refs_json_type') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_source_refs_json_type" CHECK (jsonb_typeof("source_refs") = 'array');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_client_request_key_nonblank') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_client_request_key_nonblank" CHECK (length(btrim("client_request_key")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_error_json_type') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_error_json_type" CHECK (jsonb_typeof("error") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_not_self') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_not_self" CHECK (in_reply_to IS DISTINCT FROM id);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_user_text') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_user_text" CHECK (role<>'user' OR nullif(btrim(content),'') IS NOT NULL);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_answer_fields') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_answer_fields" CHECK (role<>'assistant' OR state<>'completed' OR (nullif(btrim(content),'') IS NOT NULL AND source_run_id IS NOT NULL AND input_artifact_id IS NOT NULL AND answered_at IS NOT NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.graph_explorations'::regclass AND conname='graph_explorations_graph_state_json_type') THEN
 ALTER TABLE socai2."graph_explorations" ADD CONSTRAINT "graph_explorations_graph_state_json_type" CHECK (jsonb_typeof("graph_state") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.graph_explorations'::regclass AND conname='graph_explorations_row_version_range') THEN
 ALTER TABLE socai2."graph_explorations" ADD CONSTRAINT "graph_explorations_row_version_range" CHECK ("row_version" > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activities'::regclass AND conname='activities_actor_json_type') THEN
 ALTER TABLE socai2."activities" ADD CONSTRAINT "activities_actor_json_type" CHECK (jsonb_typeof("actor") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activities'::regclass AND conname='activities_detail_json_type') THEN
 ALTER TABLE socai2."activities" ADD CONSTRAINT "activities_detail_json_type" CHECK (jsonb_typeof("detail") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activities'::regclass AND conname='activities_one_subject') THEN
 ALTER TABLE socai2."activities" ADD CONSTRAINT "activities_one_subject" CHECK (num_nonnulls(subject_alert_id,subject_incident_id,subject_case_id)=1);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activity_targets'::regclass AND conname='activity_targets_before_value_json_type') THEN
 ALTER TABLE socai2."activity_targets" ADD CONSTRAINT "activity_targets_before_value_json_type" CHECK (jsonb_typeof("before_value") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activity_targets'::regclass AND conname='activity_targets_after_value_json_type') THEN
 ALTER TABLE socai2."activity_targets" ADD CONSTRAINT "activity_targets_after_value_json_type" CHECK (jsonb_typeof("after_value") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activity_targets'::regclass AND conname='activity_targets_result_state_enum') THEN
 ALTER TABLE socai2."activity_targets" ADD CONSTRAINT "activity_targets_result_state_enum" CHECK ("result_state" IN ('succeeded','failed','skipped'));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activity_targets'::regclass AND conname='activity_targets_one_target') THEN
 ALTER TABLE socai2."activity_targets" ADD CONSTRAINT "activity_targets_one_target" CHECK (num_nonnulls(alert_id,incident_id,case_id,task_id,run_id,result_id,comment_id)=1);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.comments'::regclass AND conname='comments_body_nonblank') THEN
 ALTER TABLE socai2."comments" ADD CONSTRAINT "comments_body_nonblank" CHECK (length(btrim("body")) > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.comments'::regclass AND conname='comments_row_version_range') THEN
 ALTER TABLE socai2."comments" ADD CONSTRAINT "comments_row_version_range" CHECK ("row_version" > 0);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.comments'::regclass AND conname='comments_one_parent') THEN
 ALTER TABLE socai2."comments" ADD CONSTRAINT "comments_one_parent" CHECK (num_nonnulls(alert_id,incident_id,case_id)=1);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.response_links'::regclass AND conname='response_links_legacy_proposal_ref_json_type') THEN
 ALTER TABLE socai2."response_links" ADD CONSTRAINT "response_links_legacy_proposal_ref_json_type" CHECK (jsonb_typeof("legacy_proposal_ref") = 'object');
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.response_links'::regclass AND conname='response_links_one_parent') THEN
 ALTER TABLE socai2."response_links" ADD CONSTRAINT "response_links_one_parent" CHECK (num_nonnulls(alert_id,incident_id,case_id)=1);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.response_links'::regclass AND conname='response_links_source') THEN
 ALTER TABLE socai2."response_links" ADD CONSTRAINT "response_links_source" CHECK ((result_id IS NOT NULL AND proposal_id IS NOT NULL AND legacy_proposal_ref IS NULL) OR (result_id IS NULL AND proposal_id IS NULL AND legacy_proposal_ref IS NOT NULL));
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.response_links'::regclass AND conname='response_links_has_target') THEN
 ALTER TABLE socai2."response_links" ADD CONSTRAINT "response_links_has_target" CHECK (approval_id IS NOT NULL OR action_id IS NOT NULL);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessment_sources'::regclass AND conname='case_assessment_sources_one_source') THEN
 ALTER TABLE socai2."case_assessment_sources" ADD CONSTRAINT "case_assessment_sources_one_source" CHECK (num_nonnulls(result_id,task_revision_id,artifact_id)=1);
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_connector_fk') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_connector_fk" FOREIGN KEY ("connector_id") REFERENCES public."connectors" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_owner_id_user_fk') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_owner_id_user_fk" FOREIGN KEY ("owner_id") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_closed_by_user_fk') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_closed_by_user_fk" FOREIGN KEY ("closed_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_latest_material_id_fk') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_latest_material_id_fk" FOREIGN KEY ("tenant_id","latest_material_id") REFERENCES socai2."alert_materials" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_latest_triage_id_fk') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_latest_triage_id_fk" FOREIGN KEY ("tenant_id","latest_triage_id") REFERENCES socai2."alert_assessments" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_latest_feedback_id_fk') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_latest_feedback_id_fk" FOREIGN KEY ("tenant_id","latest_feedback_id") REFERENCES socai2."alert_assessments" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_latest_explanation_id_fk') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_latest_explanation_id_fk" FOREIGN KEY ("tenant_id","latest_explanation_id") REFERENCES socai2."artifacts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_latest_material_id_scope_fk') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_latest_material_id_scope_fk" FOREIGN KEY ("tenant_id","id","latest_material_id") REFERENCES socai2."alert_materials" ("tenant_id","alert_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_latest_triage_id_scope_fk') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_latest_triage_id_scope_fk" FOREIGN KEY ("tenant_id","id","latest_triage_id") REFERENCES socai2."alert_assessments" ("tenant_id","alert_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_latest_feedback_id_scope_fk') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_latest_feedback_id_scope_fk" FOREIGN KEY ("tenant_id","id","latest_feedback_id") REFERENCES socai2."alert_assessments" ("tenant_id","alert_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alerts'::regclass AND conname='alerts_latest_explanation_id_scope_fk') THEN
 ALTER TABLE socai2."alerts" ADD CONSTRAINT "alerts_latest_explanation_id_scope_fk" FOREIGN KEY ("tenant_id","id","latest_explanation_id") REFERENCES socai2."artifacts" ("tenant_id","alert_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_materials'::regclass AND conname='alert_materials_alert_id_fk') THEN
 ALTER TABLE socai2."alert_materials" ADD CONSTRAINT "alert_materials_alert_id_fk" FOREIGN KEY ("tenant_id","alert_id") REFERENCES socai2."alerts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_source_refs'::regclass AND conname='alert_source_refs_alert_id_fk') THEN
 ALTER TABLE socai2."alert_source_refs" ADD CONSTRAINT "alert_source_refs_alert_id_fk" FOREIGN KEY ("tenant_id","alert_id") REFERENCES socai2."alerts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_source_refs'::regclass AND conname='alert_source_refs_material_id_fk') THEN
 ALTER TABLE socai2."alert_source_refs" ADD CONSTRAINT "alert_source_refs_material_id_fk" FOREIGN KEY ("tenant_id","material_id") REFERENCES socai2."alert_materials" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_source_refs'::regclass AND conname='alert_source_refs_material_id_scope_fk') THEN
 ALTER TABLE socai2."alert_source_refs" ADD CONSTRAINT "alert_source_refs_material_id_scope_fk" FOREIGN KEY ("tenant_id","alert_id","material_id") REFERENCES socai2."alert_materials" ("tenant_id","alert_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_objects'::regclass AND conname='alert_objects_alert_id_fk') THEN
 ALTER TABLE socai2."alert_objects" ADD CONSTRAINT "alert_objects_alert_id_fk" FOREIGN KEY ("tenant_id","alert_id") REFERENCES socai2."alerts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_objects'::regclass AND conname='alert_objects_material_id_fk') THEN
 ALTER TABLE socai2."alert_objects" ADD CONSTRAINT "alert_objects_material_id_fk" FOREIGN KEY ("tenant_id","material_id") REFERENCES socai2."alert_materials" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_objects'::regclass AND conname='alert_objects_material_id_scope_fk') THEN
 ALTER TABLE socai2."alert_objects" ADD CONSTRAINT "alert_objects_material_id_scope_fk" FOREIGN KEY ("tenant_id","alert_id","material_id") REFERENCES socai2."alert_materials" ("tenant_id","alert_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_assessments'::regclass AND conname='alert_assessments_alert_id_fk') THEN
 ALTER TABLE socai2."alert_assessments" ADD CONSTRAINT "alert_assessments_alert_id_fk" FOREIGN KEY ("tenant_id","alert_id") REFERENCES socai2."alerts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_assessments'::regclass AND conname='alert_assessments_input_material_id_fk') THEN
 ALTER TABLE socai2."alert_assessments" ADD CONSTRAINT "alert_assessments_input_material_id_fk" FOREIGN KEY ("tenant_id","input_material_id") REFERENCES socai2."alert_materials" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_assessments'::regclass AND conname='alert_assessments_source_run_id_fk') THEN
 ALTER TABLE socai2."alert_assessments" ADD CONSTRAINT "alert_assessments_source_run_id_fk" FOREIGN KEY ("tenant_id","source_run_id") REFERENCES socai2."runs" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_assessments'::regclass AND conname='alert_assessments_input_material_id_scope_fk') THEN
 ALTER TABLE socai2."alert_assessments" ADD CONSTRAINT "alert_assessments_input_material_id_scope_fk" FOREIGN KEY ("tenant_id","alert_id","input_material_id") REFERENCES socai2."alert_materials" ("tenant_id","alert_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.alert_assessments'::regclass AND conname='alert_assessments_source_run_id_scope_fk') THEN
 ALTER TABLE socai2."alert_assessments" ADD CONSTRAINT "alert_assessments_source_run_id_scope_fk" FOREIGN KEY ("tenant_id","alert_id","source_run_id") REFERENCES socai2."runs" ("tenant_id","alert_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_owner_id_user_fk') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_owner_id_user_fk" FOREIGN KEY ("owner_id") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_severity_override_by_user_fk') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_severity_override_by_user_fk" FOREIGN KEY ("severity_override_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_resolved_by_user_fk') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_resolved_by_user_fk" FOREIGN KEY ("resolved_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_latest_diagnosis_id_fk') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_latest_diagnosis_id_fk" FOREIGN KEY ("tenant_id","latest_diagnosis_id") REFERENCES socai2."incident_diagnoses" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incidents'::regclass AND conname='incidents_latest_diagnosis_id_scope_fk') THEN
 ALTER TABLE socai2."incidents" ADD CONSTRAINT "incidents_latest_diagnosis_id_scope_fk" FOREIGN KEY ("tenant_id","id","latest_diagnosis_id") REFERENCES socai2."incident_diagnoses" ("tenant_id","incident_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_alerts'::regclass AND conname='incident_alerts_incident_id_fk') THEN
 ALTER TABLE socai2."incident_alerts" ADD CONSTRAINT "incident_alerts_incident_id_fk" FOREIGN KEY ("tenant_id","incident_id") REFERENCES socai2."incidents" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_alerts'::regclass AND conname='incident_alerts_alert_id_fk') THEN
 ALTER TABLE socai2."incident_alerts" ADD CONSTRAINT "incident_alerts_alert_id_fk" FOREIGN KEY ("tenant_id","alert_id") REFERENCES socai2."alerts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_diagnoses'::regclass AND conname='incident_diagnoses_incident_id_fk') THEN
 ALTER TABLE socai2."incident_diagnoses" ADD CONSTRAINT "incident_diagnoses_incident_id_fk" FOREIGN KEY ("tenant_id","incident_id") REFERENCES socai2."incidents" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_diagnoses'::regclass AND conname='incident_diagnoses_source_run_id_fk') THEN
 ALTER TABLE socai2."incident_diagnoses" ADD CONSTRAINT "incident_diagnoses_source_run_id_fk" FOREIGN KEY ("tenant_id","source_run_id") REFERENCES socai2."runs" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_diagnoses'::regclass AND conname='incident_diagnoses_input_artifact_id_fk') THEN
 ALTER TABLE socai2."incident_diagnoses" ADD CONSTRAINT "incident_diagnoses_input_artifact_id_fk" FOREIGN KEY ("tenant_id","input_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_diagnoses'::regclass AND conname='incident_diagnoses_source_run_id_scope_fk') THEN
 ALTER TABLE socai2."incident_diagnoses" ADD CONSTRAINT "incident_diagnoses_source_run_id_scope_fk" FOREIGN KEY ("tenant_id","incident_id","source_run_id") REFERENCES socai2."runs" ("tenant_id","incident_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.incident_diagnoses'::regclass AND conname='incident_diagnoses_input_artifact_id_scope_fk') THEN
 ALTER TABLE socai2."incident_diagnoses" ADD CONSTRAINT "incident_diagnoses_input_artifact_id_scope_fk" FOREIGN KEY ("tenant_id","incident_id","input_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","incident_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_owner_id_user_fk') THEN
 ALTER TABLE socai2."cases" ADD CONSTRAINT "cases_owner_id_user_fk" FOREIGN KEY ("owner_id") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_current_assessment_id_fk') THEN
 ALTER TABLE socai2."cases" ADD CONSTRAINT "cases_current_assessment_id_fk" FOREIGN KEY ("tenant_id","current_assessment_id") REFERENCES socai2."case_assessments" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_created_by_user_fk') THEN
 ALTER TABLE socai2."cases" ADD CONSTRAINT "cases_created_by_user_fk" FOREIGN KEY ("created_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_resolved_by_user_fk') THEN
 ALTER TABLE socai2."cases" ADD CONSTRAINT "cases_resolved_by_user_fk" FOREIGN KEY ("resolved_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_current_assessment_id_scope_fk') THEN
 ALTER TABLE socai2."cases" ADD CONSTRAINT "cases_current_assessment_id_scope_fk" FOREIGN KEY ("tenant_id","id","current_assessment_id") REFERENCES socai2."case_assessments" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_alerts'::regclass AND conname='case_alerts_case_id_fk') THEN
 ALTER TABLE socai2."case_alerts" ADD CONSTRAINT "case_alerts_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_alerts'::regclass AND conname='case_alerts_alert_id_fk') THEN
 ALTER TABLE socai2."case_alerts" ADD CONSTRAINT "case_alerts_alert_id_fk" FOREIGN KEY ("tenant_id","alert_id") REFERENCES socai2."alerts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_alerts'::regclass AND conname='case_alerts_added_by_user_fk') THEN
 ALTER TABLE socai2."case_alerts" ADD CONSTRAINT "case_alerts_added_by_user_fk" FOREIGN KEY ("added_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_incidents'::regclass AND conname='case_incidents_case_id_fk') THEN
 ALTER TABLE socai2."case_incidents" ADD CONSTRAINT "case_incidents_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_incidents'::regclass AND conname='case_incidents_incident_id_fk') THEN
 ALTER TABLE socai2."case_incidents" ADD CONSTRAINT "case_incidents_incident_id_fk" FOREIGN KEY ("tenant_id","incident_id") REFERENCES socai2."incidents" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_incidents'::regclass AND conname='case_incidents_linked_by_user_fk') THEN
 ALTER TABLE socai2."case_incidents" ADD CONSTRAINT "case_incidents_linked_by_user_fk" FOREIGN KEY ("linked_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessments'::regclass AND conname='case_assessments_case_id_fk') THEN
 ALTER TABLE socai2."case_assessments" ADD CONSTRAINT "case_assessments_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessments'::regclass AND conname='case_assessments_adopted_by_user_fk') THEN
 ALTER TABLE socai2."case_assessments" ADD CONSTRAINT "case_assessments_adopted_by_user_fk" FOREIGN KEY ("adopted_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessment_sources'::regclass AND conname='case_assessment_sources_case_id_fk') THEN
 ALTER TABLE socai2."case_assessment_sources" ADD CONSTRAINT "case_assessment_sources_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessment_sources'::regclass AND conname='case_assessment_sources_assessment_id_fk') THEN
 ALTER TABLE socai2."case_assessment_sources" ADD CONSTRAINT "case_assessment_sources_assessment_id_fk" FOREIGN KEY ("tenant_id","assessment_id") REFERENCES socai2."case_assessments" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessment_sources'::regclass AND conname='case_assessment_sources_result_id_fk') THEN
 ALTER TABLE socai2."case_assessment_sources" ADD CONSTRAINT "case_assessment_sources_result_id_fk" FOREIGN KEY ("tenant_id","result_id") REFERENCES socai2."results" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessment_sources'::regclass AND conname='case_assessment_sources_task_revision_id_fk') THEN
 ALTER TABLE socai2."case_assessment_sources" ADD CONSTRAINT "case_assessment_sources_task_revision_id_fk" FOREIGN KEY ("tenant_id","task_revision_id") REFERENCES socai2."task_revisions" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessment_sources'::regclass AND conname='case_assessment_sources_artifact_id_fk') THEN
 ALTER TABLE socai2."case_assessment_sources" ADD CONSTRAINT "case_assessment_sources_artifact_id_fk" FOREIGN KEY ("tenant_id","artifact_id") REFERENCES socai2."artifacts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessment_sources'::regclass AND conname='case_assessment_sources_assessment_id_scope_fk') THEN
 ALTER TABLE socai2."case_assessment_sources" ADD CONSTRAINT "case_assessment_sources_assessment_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","assessment_id") REFERENCES socai2."case_assessments" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessment_sources'::regclass AND conname='case_assessment_sources_result_id_scope_fk') THEN
 ALTER TABLE socai2."case_assessment_sources" ADD CONSTRAINT "case_assessment_sources_result_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","result_id") REFERENCES socai2."results" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessment_sources'::regclass AND conname='case_assessment_sources_task_revision_id_scope_fk') THEN
 ALTER TABLE socai2."case_assessment_sources" ADD CONSTRAINT "case_assessment_sources_task_revision_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","task_revision_id") REFERENCES socai2."task_revisions" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessment_sources'::regclass AND conname='case_assessment_sources_artifact_id_scope_fk') THEN
 ALTER TABLE socai2."case_assessment_sources" ADD CONSTRAINT "case_assessment_sources_artifact_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","artifact_id") REFERENCES socai2."artifacts" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessment_members'::regclass AND conname='case_assessment_members_case_id_fk') THEN
 ALTER TABLE socai2."case_assessment_members" ADD CONSTRAINT "case_assessment_members_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessment_members'::regclass AND conname='case_assessment_members_assessment_id_fk') THEN
 ALTER TABLE socai2."case_assessment_members" ADD CONSTRAINT "case_assessment_members_assessment_id_fk" FOREIGN KEY ("tenant_id","assessment_id") REFERENCES socai2."case_assessments" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessment_members'::regclass AND conname='case_assessment_members_alert_id_fk') THEN
 ALTER TABLE socai2."case_assessment_members" ADD CONSTRAINT "case_assessment_members_alert_id_fk" FOREIGN KEY ("tenant_id","alert_id") REFERENCES socai2."alerts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.case_assessment_members'::regclass AND conname='case_assessment_members_assessment_id_scope_fk') THEN
 ALTER TABLE socai2."case_assessment_members" ADD CONSTRAINT "case_assessment_members_assessment_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","assessment_id") REFERENCES socai2."case_assessments" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_alert_id_fk') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_alert_id_fk" FOREIGN KEY ("tenant_id","alert_id") REFERENCES socai2."alerts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_incident_id_fk') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_incident_id_fk" FOREIGN KEY ("tenant_id","incident_id") REFERENCES socai2."incidents" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_case_id_fk') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_retry_of_run_id_fk') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_retry_of_run_id_fk" FOREIGN KEY ("tenant_id","retry_of_run_id") REFERENCES socai2."runs" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_comparison_result_id_fk') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_comparison_result_id_fk" FOREIGN KEY ("tenant_id","comparison_result_id") REFERENCES socai2."results" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_input_artifact_id_fk') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_input_artifact_id_fk" FOREIGN KEY ("tenant_id","input_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_requested_by_user_fk') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_requested_by_user_fk" FOREIGN KEY ("requested_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_comparison_result_id_scope_fk') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_comparison_result_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","comparison_result_id") REFERENCES socai2."results" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.runs'::regclass AND conname='runs_input_artifact_id_scope_fk') THEN
 ALTER TABLE socai2."runs" ADD CONSTRAINT "runs_input_artifact_id_scope_fk" FOREIGN KEY ("tenant_id","id","input_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","run_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_members'::regclass AND conname='run_members_run_id_fk') THEN
 ALTER TABLE socai2."run_members" ADD CONSTRAINT "run_members_run_id_fk" FOREIGN KEY ("tenant_id","run_id") REFERENCES socai2."runs" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_members'::regclass AND conname='run_members_case_id_fk') THEN
 ALTER TABLE socai2."run_members" ADD CONSTRAINT "run_members_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_members'::regclass AND conname='run_members_alert_id_fk') THEN
 ALTER TABLE socai2."run_members" ADD CONSTRAINT "run_members_alert_id_fk" FOREIGN KEY ("tenant_id","alert_id") REFERENCES socai2."alerts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_members'::regclass AND conname='run_members_material_id_fk') THEN
 ALTER TABLE socai2."run_members" ADD CONSTRAINT "run_members_material_id_fk" FOREIGN KEY ("tenant_id","material_id") REFERENCES socai2."alert_materials" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_members'::regclass AND conname='run_members_triage_id_fk') THEN
 ALTER TABLE socai2."run_members" ADD CONSTRAINT "run_members_triage_id_fk" FOREIGN KEY ("tenant_id","triage_id") REFERENCES socai2."alert_assessments" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_members'::regclass AND conname='run_members_feedback_id_fk') THEN
 ALTER TABLE socai2."run_members" ADD CONSTRAINT "run_members_feedback_id_fk" FOREIGN KEY ("tenant_id","feedback_id") REFERENCES socai2."alert_assessments" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_members'::regclass AND conname='run_members_run_id_scope_fk') THEN
 ALTER TABLE socai2."run_members" ADD CONSTRAINT "run_members_run_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","run_id") REFERENCES socai2."runs" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_members'::regclass AND conname='run_members_material_id_scope_fk') THEN
 ALTER TABLE socai2."run_members" ADD CONSTRAINT "run_members_material_id_scope_fk" FOREIGN KEY ("tenant_id","alert_id","material_id") REFERENCES socai2."alert_materials" ("tenant_id","alert_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_members'::regclass AND conname='run_members_triage_id_scope_fk') THEN
 ALTER TABLE socai2."run_members" ADD CONSTRAINT "run_members_triage_id_scope_fk" FOREIGN KEY ("tenant_id","alert_id","triage_id") REFERENCES socai2."alert_assessments" ("tenant_id","alert_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_members'::regclass AND conname='run_members_feedback_id_scope_fk') THEN
 ALTER TABLE socai2."run_members" ADD CONSTRAINT "run_members_feedback_id_scope_fk" FOREIGN KEY ("tenant_id","alert_id","feedback_id") REFERENCES socai2."alert_assessments" ("tenant_id","alert_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_run_id_fk') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_run_id_fk" FOREIGN KEY ("tenant_id","run_id") REFERENCES socai2."runs" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_parent_step_id_fk') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_parent_step_id_fk" FOREIGN KEY ("tenant_id","parent_step_id") REFERENCES socai2."run_steps" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_retry_of_step_id_fk') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_retry_of_step_id_fk" FOREIGN KEY ("tenant_id","retry_of_step_id") REFERENCES socai2."run_steps" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_input_artifact_id_fk') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_input_artifact_id_fk" FOREIGN KEY ("tenant_id","input_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_output_artifact_id_fk') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_output_artifact_id_fk" FOREIGN KEY ("tenant_id","output_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_reused_artifact_id_fk') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_reused_artifact_id_fk" FOREIGN KEY ("tenant_id","reused_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_parent_step_id_scope_fk') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_parent_step_id_scope_fk" FOREIGN KEY ("tenant_id","run_id","parent_step_id") REFERENCES socai2."run_steps" ("tenant_id","run_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_retry_of_step_id_scope_fk') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_retry_of_step_id_scope_fk" FOREIGN KEY ("tenant_id","run_id","retry_of_step_id") REFERENCES socai2."run_steps" ("tenant_id","run_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_input_artifact_id_scope_fk') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_input_artifact_id_scope_fk" FOREIGN KEY ("tenant_id","run_id","input_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","run_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.run_steps'::regclass AND conname='run_steps_output_artifact_id_scope_fk') THEN
 ALTER TABLE socai2."run_steps" ADD CONSTRAINT "run_steps_output_artifact_id_scope_fk" FOREIGN KEY ("tenant_id","run_id","output_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","run_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_alert_id_fk') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_alert_id_fk" FOREIGN KEY ("tenant_id","alert_id") REFERENCES socai2."alerts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_incident_id_fk') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_incident_id_fk" FOREIGN KEY ("tenant_id","incident_id") REFERENCES socai2."incidents" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_case_id_fk') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_run_id_fk') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_run_id_fk" FOREIGN KEY ("tenant_id","run_id") REFERENCES socai2."runs" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_step_id_fk') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_step_id_fk" FOREIGN KEY ("tenant_id","step_id") REFERENCES socai2."run_steps" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_created_by_user_fk') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_created_by_user_fk" FOREIGN KEY ("created_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_step_id_scope_fk') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_step_id_scope_fk" FOREIGN KEY ("tenant_id","run_id","step_id") REFERENCES socai2."run_steps" ("tenant_id","run_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_run_id_scope_fk') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_run_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","run_id") REFERENCES socai2."runs" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_run_id_scope_fk') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_run_id_scope_fk" FOREIGN KEY ("tenant_id","alert_id","run_id") REFERENCES socai2."runs" ("tenant_id","alert_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.artifacts'::regclass AND conname='artifacts_run_id_scope_fk') THEN
 ALTER TABLE socai2."artifacts" ADD CONSTRAINT "artifacts_run_id_scope_fk" FOREIGN KEY ("tenant_id","incident_id","run_id") REFERENCES socai2."runs" ("tenant_id","incident_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_case_id_fk') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_source_run_id_fk') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_source_run_id_fk" FOREIGN KEY ("tenant_id","source_run_id") REFERENCES socai2."runs" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_source_answer_id_fk') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_source_answer_id_fk" FOREIGN KEY ("tenant_id","source_answer_id") REFERENCES socai2."messages" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_comparison_result_id_fk') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_comparison_result_id_fk" FOREIGN KEY ("tenant_id","comparison_result_id") REFERENCES socai2."results" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_input_artifact_id_fk') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_input_artifact_id_fk" FOREIGN KEY ("tenant_id","input_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_graph_artifact_id_fk') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_graph_artifact_id_fk" FOREIGN KEY ("tenant_id","graph_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_report_artifact_id_fk') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_report_artifact_id_fk" FOREIGN KEY ("tenant_id","report_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_supersedes_result_id_fk') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_supersedes_result_id_fk" FOREIGN KEY ("tenant_id","supersedes_result_id") REFERENCES socai2."results" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_saved_by_user_fk') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_saved_by_user_fk" FOREIGN KEY ("saved_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_source_run_id_scope_fk') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_source_run_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","source_run_id") REFERENCES socai2."runs" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_comparison_result_id_scope_fk') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_comparison_result_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","comparison_result_id") REFERENCES socai2."results" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_supersedes_result_id_scope_fk') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_supersedes_result_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","supersedes_result_id") REFERENCES socai2."results" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_source_answer_id_scope_fk') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_source_answer_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","source_answer_id") REFERENCES socai2."messages" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_input_artifact_id_scope_fk') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_input_artifact_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","input_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_graph_artifact_id_scope_fk') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_graph_artifact_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","graph_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.results'::regclass AND conname='results_report_artifact_id_scope_fk') THEN
 ALTER TABLE socai2."results" ADD CONSTRAINT "results_report_artifact_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","report_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.result_members'::regclass AND conname='result_members_case_id_fk') THEN
 ALTER TABLE socai2."result_members" ADD CONSTRAINT "result_members_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.result_members'::regclass AND conname='result_members_result_id_fk') THEN
 ALTER TABLE socai2."result_members" ADD CONSTRAINT "result_members_result_id_fk" FOREIGN KEY ("tenant_id","result_id") REFERENCES socai2."results" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.result_members'::regclass AND conname='result_members_run_id_fk') THEN
 ALTER TABLE socai2."result_members" ADD CONSTRAINT "result_members_run_id_fk" FOREIGN KEY ("tenant_id","run_id") REFERENCES socai2."runs" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.result_members'::regclass AND conname='result_members_alert_id_fk') THEN
 ALTER TABLE socai2."result_members" ADD CONSTRAINT "result_members_alert_id_fk" FOREIGN KEY ("tenant_id","alert_id") REFERENCES socai2."alerts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.result_members'::regclass AND conname='result_members_result_run_fk') THEN
 ALTER TABLE socai2."result_members" ADD CONSTRAINT "result_members_result_run_fk" FOREIGN KEY ("tenant_id","case_id","run_id","result_id") REFERENCES socai2."results" ("tenant_id","case_id","source_run_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.result_members'::regclass AND conname='result_members_run_member_fk') THEN
 ALTER TABLE socai2."result_members" ADD CONSTRAINT "result_members_run_member_fk" FOREIGN KEY ("tenant_id","case_id","run_id","alert_id") REFERENCES socai2."run_members" ("tenant_id","case_id","run_id","alert_id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.tasks'::regclass AND conname='tasks_case_id_fk') THEN
 ALTER TABLE socai2."tasks" ADD CONSTRAINT "tasks_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.tasks'::regclass AND conname='tasks_current_revision_id_fk') THEN
 ALTER TABLE socai2."tasks" ADD CONSTRAINT "tasks_current_revision_id_fk" FOREIGN KEY ("tenant_id","current_revision_id") REFERENCES socai2."task_revisions" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.tasks'::regclass AND conname='tasks_origin_result_id_fk') THEN
 ALTER TABLE socai2."tasks" ADD CONSTRAINT "tasks_origin_result_id_fk" FOREIGN KEY ("tenant_id","origin_result_id") REFERENCES socai2."results" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.tasks'::regclass AND conname='tasks_created_by_user_fk') THEN
 ALTER TABLE socai2."tasks" ADD CONSTRAINT "tasks_created_by_user_fk" FOREIGN KEY ("created_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.tasks'::regclass AND conname='tasks_current_revision_id_scope_fk') THEN
 ALTER TABLE socai2."tasks" ADD CONSTRAINT "tasks_current_revision_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","id","current_revision_id") REFERENCES socai2."task_revisions" ("tenant_id","case_id","task_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.tasks'::regclass AND conname='tasks_origin_result_id_scope_fk') THEN
 ALTER TABLE socai2."tasks" ADD CONSTRAINT "tasks_origin_result_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","origin_result_id") REFERENCES socai2."results" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.task_revisions'::regclass AND conname='task_revisions_case_id_fk') THEN
 ALTER TABLE socai2."task_revisions" ADD CONSTRAINT "task_revisions_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.task_revisions'::regclass AND conname='task_revisions_task_id_fk') THEN
 ALTER TABLE socai2."task_revisions" ADD CONSTRAINT "task_revisions_task_id_fk" FOREIGN KEY ("tenant_id","task_id") REFERENCES socai2."tasks" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.task_revisions'::regclass AND conname='task_revisions_assignee_id_user_fk') THEN
 ALTER TABLE socai2."task_revisions" ADD CONSTRAINT "task_revisions_assignee_id_user_fk" FOREIGN KEY ("assignee_id") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.task_revisions'::regclass AND conname='task_revisions_completed_by_user_fk') THEN
 ALTER TABLE socai2."task_revisions" ADD CONSTRAINT "task_revisions_completed_by_user_fk" FOREIGN KEY ("completed_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.task_revisions'::regclass AND conname='task_revisions_changed_by_user_fk') THEN
 ALTER TABLE socai2."task_revisions" ADD CONSTRAINT "task_revisions_changed_by_user_fk" FOREIGN KEY ("changed_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.task_revisions'::regclass AND conname='task_revisions_task_id_scope_fk') THEN
 ALTER TABLE socai2."task_revisions" ADD CONSTRAINT "task_revisions_task_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","task_id") REFERENCES socai2."tasks" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.conversations'::regclass AND conname='conversations_case_id_fk') THEN
 ALTER TABLE socai2."conversations" ADD CONSTRAINT "conversations_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.conversations'::regclass AND conname='conversations_created_by_user_fk') THEN
 ALTER TABLE socai2."conversations" ADD CONSTRAINT "conversations_created_by_user_fk" FOREIGN KEY ("created_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_case_id_fk') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_conversation_id_fk') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_conversation_id_fk" FOREIGN KEY ("tenant_id","conversation_id") REFERENCES socai2."conversations" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_in_reply_to_fk') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_in_reply_to_fk" FOREIGN KEY ("tenant_id","in_reply_to") REFERENCES socai2."messages" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_source_run_id_fk') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_source_run_id_fk" FOREIGN KEY ("tenant_id","source_run_id") REFERENCES socai2."runs" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_input_artifact_id_fk') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_input_artifact_id_fk" FOREIGN KEY ("tenant_id","input_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_conversation_id_scope_fk') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_conversation_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","conversation_id") REFERENCES socai2."conversations" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_in_reply_to_scope_fk') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_in_reply_to_scope_fk" FOREIGN KEY ("tenant_id","case_id","conversation_id","in_reply_to") REFERENCES socai2."messages" ("tenant_id","case_id","conversation_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_source_run_id_scope_fk') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_source_run_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","source_run_id") REFERENCES socai2."runs" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.messages'::regclass AND conname='messages_input_artifact_id_scope_fk') THEN
 ALTER TABLE socai2."messages" ADD CONSTRAINT "messages_input_artifact_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","input_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.graph_explorations'::regclass AND conname='graph_explorations_case_id_fk') THEN
 ALTER TABLE socai2."graph_explorations" ADD CONSTRAINT "graph_explorations_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.graph_explorations'::regclass AND conname='graph_explorations_base_result_id_fk') THEN
 ALTER TABLE socai2."graph_explorations" ADD CONSTRAINT "graph_explorations_base_result_id_fk" FOREIGN KEY ("tenant_id","base_result_id") REFERENCES socai2."results" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.graph_explorations'::regclass AND conname='graph_explorations_base_graph_artifact_id_fk') THEN
 ALTER TABLE socai2."graph_explorations" ADD CONSTRAINT "graph_explorations_base_graph_artifact_id_fk" FOREIGN KEY ("tenant_id","base_graph_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.graph_explorations'::regclass AND conname='graph_explorations_base_input_artifact_id_fk') THEN
 ALTER TABLE socai2."graph_explorations" ADD CONSTRAINT "graph_explorations_base_input_artifact_id_fk" FOREIGN KEY ("tenant_id","base_input_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.graph_explorations'::regclass AND conname='graph_explorations_created_by_user_fk') THEN
 ALTER TABLE socai2."graph_explorations" ADD CONSTRAINT "graph_explorations_created_by_user_fk" FOREIGN KEY ("created_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.graph_explorations'::regclass AND conname='graph_explorations_updated_by_user_fk') THEN
 ALTER TABLE socai2."graph_explorations" ADD CONSTRAINT "graph_explorations_updated_by_user_fk" FOREIGN KEY ("updated_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.graph_explorations'::regclass AND conname='graph_explorations_base_result_id_scope_fk') THEN
 ALTER TABLE socai2."graph_explorations" ADD CONSTRAINT "graph_explorations_base_result_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","base_result_id") REFERENCES socai2."results" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.graph_explorations'::regclass AND conname='graph_explorations_base_graph_artifact_id_scope_fk') THEN
 ALTER TABLE socai2."graph_explorations" ADD CONSTRAINT "graph_explorations_base_graph_artifact_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","base_graph_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.graph_explorations'::regclass AND conname='graph_explorations_base_input_artifact_id_scope_fk') THEN
 ALTER TABLE socai2."graph_explorations" ADD CONSTRAINT "graph_explorations_base_input_artifact_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","base_input_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activities'::regclass AND conname='activities_subject_alert_id_fk') THEN
 ALTER TABLE socai2."activities" ADD CONSTRAINT "activities_subject_alert_id_fk" FOREIGN KEY ("tenant_id","subject_alert_id") REFERENCES socai2."alerts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activities'::regclass AND conname='activities_subject_incident_id_fk') THEN
 ALTER TABLE socai2."activities" ADD CONSTRAINT "activities_subject_incident_id_fk" FOREIGN KEY ("tenant_id","subject_incident_id") REFERENCES socai2."incidents" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activities'::regclass AND conname='activities_subject_case_id_fk') THEN
 ALTER TABLE socai2."activities" ADD CONSTRAINT "activities_subject_case_id_fk" FOREIGN KEY ("tenant_id","subject_case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activity_targets'::regclass AND conname='activity_targets_activity_id_fk') THEN
 ALTER TABLE socai2."activity_targets" ADD CONSTRAINT "activity_targets_activity_id_fk" FOREIGN KEY ("tenant_id","activity_id") REFERENCES socai2."activities" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activity_targets'::regclass AND conname='activity_targets_alert_id_fk') THEN
 ALTER TABLE socai2."activity_targets" ADD CONSTRAINT "activity_targets_alert_id_fk" FOREIGN KEY ("tenant_id","alert_id") REFERENCES socai2."alerts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activity_targets'::regclass AND conname='activity_targets_incident_id_fk') THEN
 ALTER TABLE socai2."activity_targets" ADD CONSTRAINT "activity_targets_incident_id_fk" FOREIGN KEY ("tenant_id","incident_id") REFERENCES socai2."incidents" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activity_targets'::regclass AND conname='activity_targets_case_id_fk') THEN
 ALTER TABLE socai2."activity_targets" ADD CONSTRAINT "activity_targets_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activity_targets'::regclass AND conname='activity_targets_task_id_fk') THEN
 ALTER TABLE socai2."activity_targets" ADD CONSTRAINT "activity_targets_task_id_fk" FOREIGN KEY ("tenant_id","task_id") REFERENCES socai2."tasks" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activity_targets'::regclass AND conname='activity_targets_run_id_fk') THEN
 ALTER TABLE socai2."activity_targets" ADD CONSTRAINT "activity_targets_run_id_fk" FOREIGN KEY ("tenant_id","run_id") REFERENCES socai2."runs" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activity_targets'::regclass AND conname='activity_targets_result_id_fk') THEN
 ALTER TABLE socai2."activity_targets" ADD CONSTRAINT "activity_targets_result_id_fk" FOREIGN KEY ("tenant_id","result_id") REFERENCES socai2."results" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.activity_targets'::regclass AND conname='activity_targets_comment_id_fk') THEN
 ALTER TABLE socai2."activity_targets" ADD CONSTRAINT "activity_targets_comment_id_fk" FOREIGN KEY ("tenant_id","comment_id") REFERENCES socai2."comments" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.comments'::regclass AND conname='comments_alert_id_fk') THEN
 ALTER TABLE socai2."comments" ADD CONSTRAINT "comments_alert_id_fk" FOREIGN KEY ("tenant_id","alert_id") REFERENCES socai2."alerts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.comments'::regclass AND conname='comments_incident_id_fk') THEN
 ALTER TABLE socai2."comments" ADD CONSTRAINT "comments_incident_id_fk" FOREIGN KEY ("tenant_id","incident_id") REFERENCES socai2."incidents" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.comments'::regclass AND conname='comments_case_id_fk') THEN
 ALTER TABLE socai2."comments" ADD CONSTRAINT "comments_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.comments'::regclass AND conname='comments_author_id_user_fk') THEN
 ALTER TABLE socai2."comments" ADD CONSTRAINT "comments_author_id_user_fk" FOREIGN KEY ("author_id") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.comments'::regclass AND conname='comments_edited_by_user_fk') THEN
 ALTER TABLE socai2."comments" ADD CONSTRAINT "comments_edited_by_user_fk" FOREIGN KEY ("edited_by") REFERENCES public."users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.response_links'::regclass AND conname='response_links_alert_id_fk') THEN
 ALTER TABLE socai2."response_links" ADD CONSTRAINT "response_links_alert_id_fk" FOREIGN KEY ("tenant_id","alert_id") REFERENCES socai2."alerts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.response_links'::regclass AND conname='response_links_incident_id_fk') THEN
 ALTER TABLE socai2."response_links" ADD CONSTRAINT "response_links_incident_id_fk" FOREIGN KEY ("tenant_id","incident_id") REFERENCES socai2."incidents" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.response_links'::regclass AND conname='response_links_case_id_fk') THEN
 ALTER TABLE socai2."response_links" ADD CONSTRAINT "response_links_case_id_fk" FOREIGN KEY ("tenant_id","case_id") REFERENCES socai2."cases" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.response_links'::regclass AND conname='response_links_result_id_fk') THEN
 ALTER TABLE socai2."response_links" ADD CONSTRAINT "response_links_result_id_fk" FOREIGN KEY ("tenant_id","result_id") REFERENCES socai2."results" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.response_links'::regclass AND conname='response_links_receipt_artifact_id_fk') THEN
 ALTER TABLE socai2."response_links" ADD CONSTRAINT "response_links_receipt_artifact_id_fk" FOREIGN KEY ("tenant_id","receipt_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.response_links'::regclass AND conname='response_links_result_id_scope_fk') THEN
 ALTER TABLE socai2."response_links" ADD CONSTRAINT "response_links_result_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","result_id") REFERENCES socai2."results" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.response_links'::regclass AND conname='response_links_receipt_artifact_id_scope_fk') THEN
 ALTER TABLE socai2."response_links" ADD CONSTRAINT "response_links_receipt_artifact_id_scope_fk" FOREIGN KEY ("tenant_id","case_id","receipt_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","case_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.response_links'::regclass AND conname='response_links_receipt_artifact_id_scope_fk') THEN
 ALTER TABLE socai2."response_links" ADD CONSTRAINT "response_links_receipt_artifact_id_scope_fk" FOREIGN KEY ("tenant_id","alert_id","receipt_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","alert_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

DO $migration$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.response_links'::regclass AND conname='response_links_receipt_artifact_id_scope_fk') THEN
 ALTER TABLE socai2."response_links" ADD CONSTRAINT "response_links_receipt_artifact_id_scope_fk" FOREIGN KEY ("tenant_id","incident_id","receipt_artifact_id") REFERENCES socai2."artifacts" ("tenant_id","incident_id","id") ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $migration$;

CREATE UNIQUE INDEX IF NOT EXISTS "activity_targets_alert_id_once" ON socai2."activity_targets" (tenant_id,activity_id,alert_id) WHERE alert_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "activity_targets_incident_id_once" ON socai2."activity_targets" (tenant_id,activity_id,incident_id) WHERE incident_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "activity_targets_case_id_once" ON socai2."activity_targets" (tenant_id,activity_id,case_id) WHERE case_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "activity_targets_task_id_once" ON socai2."activity_targets" (tenant_id,activity_id,task_id) WHERE task_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "activity_targets_run_id_once" ON socai2."activity_targets" (tenant_id,activity_id,run_id) WHERE run_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "activity_targets_result_id_once" ON socai2."activity_targets" (tenant_id,activity_id,result_id) WHERE result_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "activity_targets_comment_id_once" ON socai2."activity_targets" (tenant_id,activity_id,comment_id) WHERE comment_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "case_assessment_sources_result_id_once" ON socai2."case_assessment_sources" (tenant_id,assessment_id,result_id) WHERE result_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "case_assessment_sources_task_revision_id_once" ON socai2."case_assessment_sources" (tenant_id,assessment_id,task_revision_id) WHERE task_revision_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "case_assessment_sources_artifact_id_once" ON socai2."case_assessment_sources" (tenant_id,assessment_id,artifact_id) WHERE artifact_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "runs_request_once" ON socai2."runs" (tenant_id,kind,operation_key) WHERE operation_key IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "runs_one_pending_baseline" ON socai2."runs" (tenant_id,case_id) WHERE kind='baseline' AND state='pending_update';

CREATE UNIQUE INDEX IF NOT EXISTS "runs_one_active_baseline" ON socai2."runs" (tenant_id,case_id) WHERE kind='baseline' AND state IN ('running','unknown');

CREATE UNIQUE INDEX IF NOT EXISTS "results_baseline_root" ON socai2."results" (tenant_id,source_run_id) WHERE kind='baseline' AND supersedes_result_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "results_answer_root" ON socai2."results" (tenant_id,source_answer_id) WHERE kind='ai_saved' AND supersedes_result_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "results_single_revision" ON socai2."results" (tenant_id,supersedes_result_id) WHERE supersedes_result_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "response_links_approval_id_proposal_once" ON socai2."response_links" (tenant_id,result_id,proposal_id,external_namespace,approval_id) WHERE result_id IS NOT NULL AND approval_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "response_links_action_id_proposal_once" ON socai2."response_links" (tenant_id,result_id,proposal_id,external_namespace,action_id) WHERE result_id IS NOT NULL AND action_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS "alerts_read_0" ON socai2."alerts" (tenant_id,event_time DESC,id);

CREATE INDEX IF NOT EXISTS "alerts_read_1" ON socai2."alerts" (tenant_id,handling_status,event_time DESC,id);

CREATE INDEX IF NOT EXISTS "alerts_read_2" ON socai2."alerts" (tenant_id,severity,event_time DESC,id);

CREATE INDEX IF NOT EXISTS "alerts_read_3" ON socai2."alerts" (tenant_id,owner_id,event_time DESC,id);

CREATE INDEX IF NOT EXISTS "incidents_read_0" ON socai2."incidents" (tenant_id,business_updated_at DESC,id);

CREATE INDEX IF NOT EXISTS "incidents_read_1" ON socai2."incidents" (tenant_id,handling_status,business_updated_at DESC,id);

CREATE INDEX IF NOT EXISTS "case_alerts_read_0" ON socai2."case_alerts" (tenant_id,alert_id,case_id);

CREATE INDEX IF NOT EXISTS "case_incidents_read_0" ON socai2."case_incidents" (tenant_id,incident_id,case_id);

CREATE INDEX IF NOT EXISTS "runs_read_0" ON socai2."runs" (tenant_id,case_id,requested_at DESC,id);

CREATE INDEX IF NOT EXISTS "runs_read_1" ON socai2."runs" (tenant_id,alert_id,requested_at DESC,id);

CREATE INDEX IF NOT EXISTS "runs_read_2" ON socai2."runs" (tenant_id,incident_id,requested_at DESC,id);

CREATE INDEX IF NOT EXISTS "results_read_0" ON socai2."results" (tenant_id,case_id,saved_at DESC,id);

CREATE INDEX IF NOT EXISTS "task_revisions_read_0" ON socai2."task_revisions" (tenant_id,case_id,state,due_at);

CREATE INDEX IF NOT EXISTS "artifacts_read_0" ON socai2."artifacts" (tenant_id,run_id,kind,captured_at,id);

CREATE INDEX IF NOT EXISTS "artifacts_read_1" ON socai2."artifacts" (tenant_id,case_id,kind,captured_at,id);

CREATE INDEX IF NOT EXISTS "alert_objects_read_0" ON socai2."alert_objects" (tenant_id,object_type,normalized_value,alert_id);

CREATE INDEX IF NOT EXISTS "alert_objects_read_1" ON socai2."alert_objects" (tenant_id,material_id);

CREATE INDEX IF NOT EXISTS "incident_alerts_read_0" ON socai2."incident_alerts" (tenant_id,incident_id,alert_id);

CREATE INDEX IF NOT EXISTS "activities_read_0" ON socai2."activities" (tenant_id,subject_case_id,occurred_at DESC,id);

CREATE INDEX IF NOT EXISTS "activities_read_1" ON socai2."activities" (tenant_id,subject_incident_id,occurred_at DESC,id);

CREATE INDEX IF NOT EXISTS "activities_read_2" ON socai2."activities" (tenant_id,subject_alert_id,occurred_at DESC,id);

CREATE INDEX IF NOT EXISTS "activity_targets_alert_id_lookup" ON socai2."activity_targets" (tenant_id,alert_id,activity_id) WHERE alert_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS "activity_targets_incident_id_lookup" ON socai2."activity_targets" (tenant_id,incident_id,activity_id) WHERE incident_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS "activity_targets_case_id_lookup" ON socai2."activity_targets" (tenant_id,case_id,activity_id) WHERE case_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS "activity_targets_task_id_lookup" ON socai2."activity_targets" (tenant_id,task_id,activity_id) WHERE task_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS "activity_targets_run_id_lookup" ON socai2."activity_targets" (tenant_id,run_id,activity_id) WHERE run_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS "activity_targets_result_id_lookup" ON socai2."activity_targets" (tenant_id,result_id,activity_id) WHERE result_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS "activity_targets_comment_id_lookup" ON socai2."activity_targets" (tenant_id,comment_id,activity_id) WHERE comment_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS "comments_alert_id_lookup" ON socai2."comments" (tenant_id,alert_id,created_at,id) WHERE alert_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS "comments_incident_id_lookup" ON socai2."comments" (tenant_id,incident_id,created_at,id) WHERE incident_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS "comments_case_id_lookup" ON socai2."comments" (tenant_id,case_id,created_at,id) WHERE case_id IS NOT NULL;

-- Included by the generated migration inside its transaction.
CREATE OR REPLACE FUNCTION socai2.guard_identity() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
BEGIN
 IF NEW.id IS DISTINCT FROM OLD.id OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id THEN
  RAISE EXCEPTION 'socai2 identity is immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $fn$;

CREATE OR REPLACE FUNCTION socai2.reject_history_mutation() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
BEGIN
 RAISE EXCEPTION 'socai2 history is append-only: %',TG_TABLE_NAME USING ERRCODE='23514';
END $fn$;

CREATE OR REPLACE FUNCTION socai2.guard_terminal_record() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
BEGIN
 IF TG_OP='DELETE' OR OLD.state IN ('completed','failed','timeout','cancelled','skipped') THEN
  RAISE EXCEPTION 'socai2 terminal record is immutable' USING ERRCODE='23514';
 END IF;
 IF NEW.id IS DISTINCT FROM OLD.id OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id THEN
  RAISE EXCEPTION 'socai2 identity is immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $fn$;

CREATE OR REPLACE FUNCTION socai2.guard_run() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
DECLARE current_scope bigint;
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'run history cannot be deleted' USING ERRCODE='23514';
 END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.kind='baseline' AND NEW.state<>'pending_update' THEN
   RAISE EXCEPTION 'baseline must be created pending, then claimed atomically' USING ERRCODE='23514';
  END IF;
 ELSE
  IF ROW(NEW.id,NEW.tenant_id,NEW.kind,NEW.case_id,NEW.alert_id,NEW.incident_id)
     IS DISTINCT FROM ROW(OLD.id,OLD.tenant_id,OLD.kind,OLD.case_id,OLD.alert_id,OLD.incident_id) THEN
   RAISE EXCEPTION 'run identity and parent are immutable' USING ERRCODE='23514';
  END IF;
  IF OLD.state IN ('completed','failed','cancelled') THEN
   RAISE EXCEPTION 'terminal run is immutable' USING ERRCODE='23514';
  END IF;
  IF OLD.state='pending_update' AND NEW.state NOT IN ('pending_update','running','cancelled')
     OR OLD.state='running' AND NEW.state NOT IN ('running','unknown','completed','failed','cancelled')
     OR OLD.state='unknown' AND NEW.state NOT IN ('unknown','completed','failed','cancelled') THEN
   RAISE EXCEPTION 'invalid run state transition' USING ERRCODE='23514';
  END IF;
  IF OLD.state<>'pending_update' AND
     (to_jsonb(NEW)-ARRAY['state','ended_at','stop_reason','stop_detail','delivery_state','row_version'])
      IS DISTINCT FROM
     (to_jsonb(OLD)-ARRAY['state','ended_at','stop_reason','stop_detail','delivery_state','row_version']) THEN
   RAISE EXCEPTION 'claimed run input is frozen' USING ERRCODE='23514';
  END IF;
 END IF;
 IF NEW.kind='baseline' AND NEW.state='running' AND TG_OP='UPDATE' AND OLD.state='pending_update' THEN
  -- API acquires Case then Run before this UPDATE; this lock also protects direct SQL writers.
  SELECT scope_revision INTO current_scope FROM socai2.cases
   WHERE tenant_id=NEW.tenant_id AND id=NEW.case_id FOR UPDATE;
  IF NOT FOUND OR current_scope<>NEW.scope_revision THEN
   RAISE EXCEPTION 'case scope changed before claim' USING ERRCODE='23514';
  END IF;
  IF NOT EXISTS(SELECT 1 FROM socai2.run_members WHERE tenant_id=NEW.tenant_id AND run_id=NEW.id) THEN
   RAISE EXCEPTION 'cannot claim empty baseline' USING ERRCODE='23514';
  END IF;
  IF EXISTS(
   (SELECT alert_id FROM socai2.case_alerts WHERE tenant_id=NEW.tenant_id AND case_id=NEW.case_id
    EXCEPT SELECT alert_id FROM socai2.run_members WHERE tenant_id=NEW.tenant_id AND run_id=NEW.id)
   UNION ALL
   (SELECT alert_id FROM socai2.run_members WHERE tenant_id=NEW.tenant_id AND run_id=NEW.id
    EXCEPT SELECT alert_id FROM socai2.case_alerts WHERE tenant_id=NEW.tenant_id AND case_id=NEW.case_id)
  ) THEN RAISE EXCEPTION 'baseline must cover complete current case' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $fn$;

CREATE OR REPLACE FUNCTION socai2.lock_case_membership() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
DECLARE cid uuid; tid uuid;
BEGIN
 IF TG_OP='UPDATE' AND ROW(NEW.case_id,NEW.alert_id) IS DISTINCT FROM ROW(OLD.case_id,OLD.alert_id) THEN
  RAISE EXCEPTION 'change membership using delete+insert under sorted Case locks' USING ERRCODE='23514';
 END IF;
 IF TG_OP='DELETE' THEN cid:=OLD.case_id;tid:=OLD.tenant_id;
 ELSE cid:=NEW.case_id;tid:=NEW.tenant_id; END IF;
 PERFORM 1 FROM socai2.cases WHERE tenant_id=tid AND id=cid FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'case not found in tenant' USING ERRCODE='23503'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $fn$;

CREATE OR REPLACE FUNCTION socai2.guard_run_member() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
DECLARE parent_state text; rid uuid; tid uuid;
BEGIN
 IF TG_OP='DELETE' THEN rid:=OLD.run_id;tid:=OLD.tenant_id; ELSE rid:=NEW.run_id;tid:=NEW.tenant_id; END IF;
 SELECT state INTO parent_state FROM socai2.runs WHERE tenant_id=tid AND id=rid FOR UPDATE;
 IF NOT FOUND THEN
  -- Preallocated AI Run identity: children, parent and input publish in one transaction.
  -- The deferred FK and member_creation_scope trigger prevent a different transaction
  -- from appending members to a concurrently-created, already-frozen Run.
  IF TG_OP='INSERT' THEN RETURN NEW; END IF;
  RAISE EXCEPTION 'run not found' USING ERRCODE='23503';
 END IF;
 IF TG_OP='UPDATE' AND ROW(NEW.run_id,NEW.case_id,NEW.alert_id,NEW.id,NEW.tenant_id)
   IS DISTINCT FROM ROW(OLD.run_id,OLD.case_id,OLD.alert_id,OLD.id,OLD.tenant_id) THEN
  RAISE EXCEPTION 'member identity cannot be reassigned' USING ERRCODE='23514';
 END IF;
 IF parent_state<>'pending_update' THEN
  IF TG_OP<>'UPDATE' THEN RAISE EXCEPTION 'claimed member set is frozen' USING ERRCODE='23514'; END IF;
  IF parent_state NOT IN ('running','unknown') OR
    (to_jsonb(NEW)-ARRAY['read_state','analysis_state','omission_reason'])
     IS DISTINCT FROM
    (to_jsonb(OLD)-ARRAY['read_state','analysis_state','omission_reason']) THEN
   RAISE EXCEPTION 'claimed member source is frozen' USING ERRCODE='23514';
  END IF;
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $fn$;

CREATE OR REPLACE FUNCTION socai2.check_new_member_transaction() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
DECLARE st text; parent_xid text; member_xid text;
BEGIN
 SELECT state,xmin::text INTO st,parent_xid FROM socai2.runs WHERE tenant_id=NEW.tenant_id AND id=NEW.run_id;
 IF NOT FOUND THEN RAISE EXCEPTION 'member Run missing at commit' USING ERRCODE='23503'; END IF;
 SELECT xmin::text INTO member_xid FROM socai2.run_members WHERE tenant_id=NEW.tenant_id AND id=NEW.id;
 IF NOT FOUND THEN RETURN NULL; END IF;
 IF st<>'pending_update' AND parent_xid IS DISTINCT FROM member_xid THEN
  RAISE EXCEPTION 'new members of a frozen Run must publish with its creation/claim transaction' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $fn$;

-- Cross-parent equality and result kind cannot be expressed by a nullable FK alone.
-- Deferral permits the artifact / Run / message insert order inside one publication transaction.
CREATE OR REPLACE FUNCTION socai2.check_publication_scope() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
DECLARE r socai2.runs%ROWTYPE; a socai2.artifacts%ROWTYPE; m socai2.messages%ROWTYPE;
BEGIN
 IF TG_TABLE_NAME='artifacts' THEN
  IF NEW.run_id IS NOT NULL THEN
  SELECT * INTO r FROM socai2.runs WHERE tenant_id=NEW.tenant_id AND id=NEW.run_id;
  IF NOT FOUND OR ROW(NEW.alert_id,NEW.incident_id,NEW.case_id)
       IS DISTINCT FROM ROW(r.alert_id,r.incident_id,r.case_id) THEN
   RAISE EXCEPTION 'artifact parent differs from Run' USING ERRCODE='23514';
  END IF;
  END IF;
 ELSIF TG_TABLE_NAME='results' THEN
  SELECT * INTO r FROM socai2.runs WHERE tenant_id=NEW.tenant_id AND id=NEW.source_run_id;
  IF NOT FOUND OR r.case_id IS DISTINCT FROM NEW.case_id OR r.state NOT IN ('completed','failed','cancelled') OR
     (NEW.kind='baseline' AND r.kind<>'baseline') OR (NEW.kind='ai_saved' AND r.kind<>'ai_question') THEN
   RAISE EXCEPTION 'result has invalid source Run' USING ERRCODE='23514';
  END IF;
  IF NEW.input_artifact_id IS DISTINCT FROM r.input_artifact_id THEN
   RAISE EXCEPTION 'result must preserve actual Run input' USING ERRCODE='23514';
  END IF;
  IF NEW.kind='ai_saved' THEN
   SELECT * INTO m FROM socai2.messages WHERE tenant_id=NEW.tenant_id AND id=NEW.source_answer_id;
   IF NOT FOUND OR m.role<>'assistant' OR m.state<>'completed' OR m.source_run_id IS DISTINCT FROM NEW.source_run_id
      OR m.input_artifact_id IS DISTINCT FROM NEW.input_artifact_id THEN
    RAISE EXCEPTION 'saved answer must reference its actual completed message' USING ERRCODE='23514';
   END IF;
  END IF;
  FOR a IN SELECT * FROM socai2.artifacts WHERE tenant_id=NEW.tenant_id AND id IN (NEW.graph_artifact_id,NEW.report_artifact_id) LOOP
   IF a.run_id IS DISTINCT FROM NEW.source_run_id THEN
    RAISE EXCEPTION 'result graph/report must belong to source Run' USING ERRCODE='23514';
   END IF;
  END LOOP;
 ELSIF TG_TABLE_NAME='messages' THEN
  IF NEW.source_run_id IS NOT NULL THEN
  SELECT * INTO r FROM socai2.runs WHERE tenant_id=NEW.tenant_id AND id=NEW.source_run_id;
  IF NOT FOUND OR r.kind<>'ai_question' OR r.case_id IS DISTINCT FROM NEW.case_id THEN
   RAISE EXCEPTION 'message must reference a same-Case AI Run' USING ERRCODE='23514';
  END IF;
  END IF;
 END IF;
 RETURN NULL;
END $fn$;

-- Optional explicit publication step for the new backend; no old writer calls this automatically.
-- AI results are deliberately ineligible. Manual AI adoption remains a separate authorized action.
CREATE OR REPLACE FUNCTION socai2.auto_adopt_baseline_result(p_tenant uuid,p_result uuid)
RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
DECLARE res socai2.results%ROWTYPE; run socai2.runs%ROWTYPE; cas socai2.cases%ROWTYPE;
 cur socai2.case_assessments%ROWTYPE; prior_id uuid; next_id uuid:=gen_random_uuid();
 act_id uuid:=gen_random_uuid(); op_id uuid:=gen_random_uuid(); ts timestamptz:=clock_timestamp();
 next_revision bigint; svc jsonb;
BEGIN
 IF p_tenant IS DISTINCT FROM public.current_tenant_id() OR p_tenant IS NULL THEN
  RAISE EXCEPTION 'explicit tenant context required' USING ERRCODE='42501';
 END IF;
 SELECT * INTO res FROM socai2.results WHERE tenant_id=p_tenant AND id=p_result;
 IF NOT FOUND THEN RAISE EXCEPTION 'result not found' USING ERRCODE='23503'; END IF;
 SELECT * INTO cas FROM socai2.cases WHERE tenant_id=p_tenant AND id=res.case_id FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'case not found' USING ERRCODE='23503'; END IF;
 SELECT a.id INTO prior_id FROM socai2.case_assessments a
  JOIN socai2.case_assessment_sources s ON s.tenant_id=a.tenant_id AND s.assessment_id=a.id
  WHERE a.tenant_id=p_tenant AND a.case_id=cas.id AND s.result_id=res.id
    AND a.operation_key='baseline-auto:'||res.id::text LIMIT 1;
 IF FOUND THEN RETURN jsonb_build_object('state','already_adopted','assessment_id',prior_id); END IF;
 SELECT * INTO run FROM socai2.runs WHERE tenant_id=p_tenant AND id=res.source_run_id;
 IF NOT FOUND OR res.kind<>'baseline' OR run.kind<>'baseline' OR run.state<>'completed'
    OR res.validation_state<>'accepted' OR res.conclusion_origin<>'model'
    OR res.conclusion_state='unavailable' OR nullif(btrim(res.conclusion),'') IS NULL THEN
  RETURN jsonb_build_object('state','not_eligible');
 END IF;
 IF run.case_id IS DISTINCT FROM cas.id OR run.scope_revision IS DISTINCT FROM cas.scope_revision THEN
  RETURN jsonb_build_object('state','stale_scope');
 END IF;
 IF EXISTS(
  (SELECT alert_id FROM socai2.case_alerts WHERE tenant_id=p_tenant AND case_id=cas.id
   EXCEPT SELECT alert_id FROM socai2.run_members WHERE tenant_id=p_tenant AND run_id=run.id)
  UNION ALL
  (SELECT alert_id FROM socai2.run_members WHERE tenant_id=p_tenant AND run_id=run.id
   EXCEPT SELECT alert_id FROM socai2.case_alerts WHERE tenant_id=p_tenant AND case_id=cas.id)
 ) THEN RETURN jsonb_build_object('state','stale_scope'); END IF;
 SELECT * INTO cur FROM socai2.case_assessments WHERE tenant_id=p_tenant AND id=cas.current_assessment_id;
 IF FOUND AND cur.adopted_at>=run.started_at THEN RETURN jsonb_build_object('state','newer_assessment'); END IF;
 IF NOT EXISTS(SELECT 1 FROM socai2.result_members WHERE tenant_id=p_tenant AND result_id=res.id
   AND conclusion_covered AND assessment_state IN ('analyzed','unresolved')) THEN
  RETURN jsonb_build_object('state','no_conclusion_coverage');
 END IF;
 -- Every promised member must have a delivery record, including explicit unresolved limitations.
 IF EXISTS(SELECT alert_id FROM socai2.run_members WHERE tenant_id=p_tenant AND run_id=run.id
  EXCEPT SELECT alert_id FROM socai2.result_members WHERE tenant_id=p_tenant AND result_id=res.id) THEN
  RETURN jsonb_build_object('state','missing_member_delivery');
 END IF;
 SELECT coalesce(max(revision),0)+1 INTO next_revision FROM socai2.case_assessments WHERE tenant_id=p_tenant AND case_id=cas.id;
 svc:=jsonb_build_object('type','service','user_id',NULL,'name_snapshot','基础调查结果自动采用',
  'service_name','socai2.baseline-publication','service_version','v1');
 INSERT INTO socai2.case_assessments(id,tenant_id,case_id,revision,conclusion,origin,validity,scope_revision,formed_at,adopted_at,actor,operation_key)
 VALUES(next_id,p_tenant,cas.id,next_revision,res.conclusion,'model','accepted',run.scope_revision,res.created_at,ts,svc,'baseline-auto:'||res.id::text);
 INSERT INTO socai2.case_assessment_sources(id,tenant_id,case_id,assessment_id,result_id)
 VALUES(gen_random_uuid(),p_tenant,cas.id,next_id,res.id);
 INSERT INTO socai2.case_assessment_members(id,tenant_id,case_id,assessment_id,alert_id,coverage_note)
 SELECT gen_random_uuid(),p_tenant,cas.id,next_id,alert_id,limitations FROM socai2.result_members
 WHERE tenant_id=p_tenant AND result_id=res.id AND conclusion_covered;
 UPDATE socai2.cases SET current_assessment_id=next_id,row_version=row_version+1,business_updated_at=ts
 WHERE tenant_id=p_tenant AND id=cas.id;
 INSERT INTO socai2.activities(id,tenant_id,operation_id,actor,action,subject_case_id,occurred_at,summary,detail)
 VALUES(act_id,p_tenant,op_id,svc,'case.assessment_adopted',cas.id,ts,'有效基础调查结果自动更新案件判断',
  jsonb_build_object('schema_version','activity.v1','reason',NULL,'request_key','baseline-auto:'||res.id::text,
   'source','baseline_publication','expected_version',cas.row_version,'actual_version',cas.row_version+1,'notes',jsonb_build_array()));
 INSERT INTO socai2.activity_targets(id,tenant_id,activity_id,case_id,before_value,after_value,result_state)
 VALUES(gen_random_uuid(),p_tenant,act_id,cas.id,jsonb_build_object('current_assessment_id',cas.current_assessment_id),
  jsonb_build_object('current_assessment_id',next_id),'succeeded');
 INSERT INTO socai2.activity_targets(id,tenant_id,activity_id,result_id,before_value,after_value,result_state)
 VALUES(gen_random_uuid(),p_tenant,act_id,res.id,NULL,jsonb_build_object('adopted_assessment_id',next_id),'succeeded');
 RETURN jsonb_build_object('state','adopted','assessment_id',next_id);
END $fn$;

DO $triggers$
DECLARE n text;
BEGIN
 FOR n IN SELECT tablename FROM pg_tables WHERE schemaname='socai2' LOOP
  EXECUTE format('DROP TRIGGER IF EXISTS identity_immutable ON socai2.%I',n);
  EXECUTE format('CREATE TRIGGER identity_immutable BEFORE UPDATE ON socai2.%I FOR EACH ROW EXECUTE FUNCTION socai2.guard_identity()',n);
 END LOOP;
 FOREACH n IN ARRAY ARRAY['alert_materials','alert_source_refs','alert_objects','alert_assessments',
  'case_assessments','case_assessment_sources','case_assessment_members','artifacts','results','result_members',
  'task_revisions','activities','activity_targets','response_links'] LOOP
  EXECUTE format('DROP TRIGGER IF EXISTS history_immutable ON socai2.%I',n);
  EXECUTE format('CREATE TRIGGER history_immutable BEFORE UPDATE OR DELETE ON socai2.%I FOR EACH ROW EXECUTE FUNCTION socai2.reject_history_mutation()',n);
 END LOOP;
 FOREACH n IN ARRAY ARRAY['run_steps','incident_diagnoses','messages'] LOOP
  EXECUTE format('DROP TRIGGER IF EXISTS terminal_immutable ON socai2.%I',n);
  EXECUTE format('CREATE TRIGGER terminal_immutable BEFORE UPDATE OR DELETE ON socai2.%I FOR EACH ROW EXECUTE FUNCTION socai2.guard_terminal_record()',n);
 END LOOP;
END $triggers$;
DROP TRIGGER IF EXISTS run_guard ON socai2.runs;
CREATE TRIGGER run_guard BEFORE INSERT OR UPDATE OR DELETE ON socai2.runs FOR EACH ROW EXECUTE FUNCTION socai2.guard_run();
DROP TRIGGER IF EXISTS member_guard ON socai2.run_members;
CREATE TRIGGER member_guard BEFORE INSERT OR UPDATE OR DELETE ON socai2.run_members FOR EACH ROW EXECUTE FUNCTION socai2.guard_run_member();
DROP TRIGGER IF EXISTS member_creation_scope ON socai2.run_members;
CREATE CONSTRAINT TRIGGER member_creation_scope AFTER INSERT ON socai2.run_members DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION socai2.check_new_member_transaction();
DROP TRIGGER IF EXISTS case_membership_lock ON socai2.case_alerts;
CREATE TRIGGER case_membership_lock BEFORE INSERT OR UPDATE OR DELETE ON socai2.case_alerts FOR EACH ROW EXECUTE FUNCTION socai2.lock_case_membership();
DO $publication$
DECLARE n text;
BEGIN
 FOREACH n IN ARRAY ARRAY['artifacts','results','messages'] LOOP
  EXECUTE format('DROP TRIGGER IF EXISTS publication_scope ON socai2.%I',n);
  EXECUTE format('CREATE CONSTRAINT TRIGGER publication_scope AFTER INSERT OR UPDATE ON socai2.%I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION socai2.check_publication_scope()',n);
 END LOOP;
END $publication$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA socai2 FROM PUBLIC;
DO $functions$
BEGIN
 IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN
  GRANT EXECUTE ON FUNCTION socai2.auto_adopt_baseline_result(uuid,uuid) TO aisoc_app;
 END IF;
END $functions$;


ALTER TABLE socai2."alerts" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."alerts" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."alerts";

CREATE POLICY tenant_scope ON socai2."alerts" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."alert_materials" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."alert_materials" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."alert_materials";

CREATE POLICY tenant_scope ON socai2."alert_materials" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."alert_source_refs" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."alert_source_refs" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."alert_source_refs";

CREATE POLICY tenant_scope ON socai2."alert_source_refs" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."alert_objects" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."alert_objects" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."alert_objects";

CREATE POLICY tenant_scope ON socai2."alert_objects" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."alert_assessments" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."alert_assessments" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."alert_assessments";

CREATE POLICY tenant_scope ON socai2."alert_assessments" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."incidents" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."incidents" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."incidents";

CREATE POLICY tenant_scope ON socai2."incidents" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."incident_alerts" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."incident_alerts" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."incident_alerts";

CREATE POLICY tenant_scope ON socai2."incident_alerts" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."incident_diagnoses" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."incident_diagnoses" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."incident_diagnoses";

CREATE POLICY tenant_scope ON socai2."incident_diagnoses" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."cases" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."cases" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."cases";

CREATE POLICY tenant_scope ON socai2."cases" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."case_alerts" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."case_alerts" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."case_alerts";

CREATE POLICY tenant_scope ON socai2."case_alerts" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."case_incidents" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."case_incidents" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."case_incidents";

CREATE POLICY tenant_scope ON socai2."case_incidents" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."case_assessments" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."case_assessments" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."case_assessments";

CREATE POLICY tenant_scope ON socai2."case_assessments" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."case_assessment_sources" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."case_assessment_sources" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."case_assessment_sources";

CREATE POLICY tenant_scope ON socai2."case_assessment_sources" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."case_assessment_members" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."case_assessment_members" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."case_assessment_members";

CREATE POLICY tenant_scope ON socai2."case_assessment_members" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."runs" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."runs" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."runs";

CREATE POLICY tenant_scope ON socai2."runs" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."run_members" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."run_members" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."run_members";

CREATE POLICY tenant_scope ON socai2."run_members" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."run_steps" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."run_steps" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."run_steps";

CREATE POLICY tenant_scope ON socai2."run_steps" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."artifacts" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."artifacts" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."artifacts";

CREATE POLICY tenant_scope ON socai2."artifacts" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."results" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."results" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."results";

CREATE POLICY tenant_scope ON socai2."results" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."result_members" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."result_members" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."result_members";

CREATE POLICY tenant_scope ON socai2."result_members" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."tasks" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."tasks" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."tasks";

CREATE POLICY tenant_scope ON socai2."tasks" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."task_revisions" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."task_revisions" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."task_revisions";

CREATE POLICY tenant_scope ON socai2."task_revisions" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."conversations" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."conversations" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."conversations";

CREATE POLICY tenant_scope ON socai2."conversations" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."messages" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."messages" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."messages";

CREATE POLICY tenant_scope ON socai2."messages" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."graph_explorations" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."graph_explorations" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."graph_explorations";

CREATE POLICY tenant_scope ON socai2."graph_explorations" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."activities" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."activities" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."activities";

CREATE POLICY tenant_scope ON socai2."activities" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."activity_targets" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."activity_targets" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."activity_targets";

CREATE POLICY tenant_scope ON socai2."activity_targets" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."comments" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."comments" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."comments";

CREATE POLICY tenant_scope ON socai2."comments" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

ALTER TABLE socai2."response_links" ENABLE ROW LEVEL SECURITY;

ALTER TABLE socai2."response_links" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_scope ON socai2."response_links";

CREATE POLICY tenant_scope ON socai2."response_links" USING (tenant_id=public.current_tenant_id()) WITH CHECK (tenant_id=public.current_tenant_id());

DO $grants$ BEGIN
 IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN
 GRANT USAGE ON SCHEMA socai2 TO aisoc_app;
 GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA socai2 TO aisoc_app;
 REVOKE TRUNCATE,REFERENCES,TRIGGER ON ALL TABLES IN SCHEMA socai2 FROM aisoc_app;
 END IF;
END $grants$;

DO $grants$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN REVOKE UPDATE,DELETE ON socai2."alert_materials" FROM aisoc_app; END IF; END $grants$;

DO $grants$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN REVOKE UPDATE,DELETE ON socai2."alert_source_refs" FROM aisoc_app; END IF; END $grants$;

DO $grants$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN REVOKE UPDATE,DELETE ON socai2."alert_objects" FROM aisoc_app; END IF; END $grants$;

DO $grants$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN REVOKE UPDATE,DELETE ON socai2."alert_assessments" FROM aisoc_app; END IF; END $grants$;

DO $grants$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN REVOKE UPDATE,DELETE ON socai2."case_assessments" FROM aisoc_app; END IF; END $grants$;

DO $grants$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN REVOKE UPDATE,DELETE ON socai2."case_assessment_sources" FROM aisoc_app; END IF; END $grants$;

DO $grants$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN REVOKE UPDATE,DELETE ON socai2."case_assessment_members" FROM aisoc_app; END IF; END $grants$;

DO $grants$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN REVOKE UPDATE,DELETE ON socai2."artifacts" FROM aisoc_app; END IF; END $grants$;

DO $grants$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN REVOKE UPDATE,DELETE ON socai2."results" FROM aisoc_app; END IF; END $grants$;

DO $grants$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN REVOKE UPDATE,DELETE ON socai2."result_members" FROM aisoc_app; END IF; END $grants$;

DO $grants$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN REVOKE UPDATE,DELETE ON socai2."task_revisions" FROM aisoc_app; END IF; END $grants$;

DO $grants$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN REVOKE UPDATE,DELETE ON socai2."activities" FROM aisoc_app; END IF; END $grants$;

DO $grants$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN REVOKE UPDATE,DELETE ON socai2."activity_targets" FROM aisoc_app; END IF; END $grants$;

DO $grants$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='aisoc_app') THEN REVOKE UPDATE,DELETE ON socai2."response_links" FROM aisoc_app; END IF; END $grants$;

INSERT INTO public.aisoc_schema_migrations(name) VALUES ('123_socai2_page_data_model.sql') ON CONFLICT DO NOTHING;

-- schema/124_socai2_case_source_binding.sql (original SHA-256 9e63d49879fb726fd5b160d676732c2cbab637b1322c49f463dea99d6ca5632d)
-- Incremental change: keep migration 123 and frozen Run inputs unchanged.

ALTER TABLE socai2.cases ADD COLUMN IF NOT EXISTS source_namespace text;
COMMENT ON COLUMN socai2.cases.source_namespace IS
 'Fixed data identity namespace; not a vendor, connector, or inferred source environment. NULL means unverified legacy scope.';

-- Only unambiguous recorded relationships qualify. Include removed members,
-- even when their pending Run was refreshed before it ever started.
WITH recorded AS (
 SELECT ca.tenant_id,ca.case_id,a.source_namespace FROM socai2.case_alerts ca
 JOIN socai2.alerts a ON a.tenant_id=ca.tenant_id AND a.id=ca.alert_id
 UNION ALL
 SELECT rm.tenant_id,rm.case_id,a.source_namespace FROM socai2.run_members rm
 JOIN socai2.alerts a ON a.tenant_id=rm.tenant_id AND a.id=rm.alert_id WHERE rm.case_id IS NOT NULL
 UNION ALL
 SELECT ci.tenant_id,ci.case_id,i.source_namespace FROM socai2.case_incidents ci
 JOIN socai2.incidents i ON i.tenant_id=ci.tenant_id AND i.id=ci.incident_id
 UNION ALL
 SELECT act.tenant_id,act.subject_case_id,a.source_namespace FROM socai2.activities act
 JOIN socai2.activity_targets t ON t.tenant_id=act.tenant_id AND t.activity_id=act.id
 JOIN socai2.alerts a ON a.tenant_id=t.tenant_id AND a.id=t.alert_id
 WHERE act.action='case_members_changed' AND act.subject_case_id IS NOT NULL
), unambiguous AS (
 SELECT tenant_id,case_id,min(source_namespace) AS namespace FROM recorded
 GROUP BY tenant_id,case_id HAVING count(DISTINCT source_namespace)=1
 AND bool_and(source_namespace IS NOT NULL AND btrim(source_namespace)<>'')
)
UPDATE socai2.cases c SET source_namespace=u.namespace FROM unambiguous u
WHERE c.tenant_id=u.tenant_id AND c.id=u.case_id AND c.source_namespace IS NULL;

CREATE OR REPLACE FUNCTION socai2.keep_case_source_binding() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN
 IF NEW.source_namespace IS NOT NULL AND btrim(NEW.source_namespace)='' THEN
   RAISE EXCEPTION 'case source namespace must not be blank' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' AND OLD.source_namespace IS NOT NULL
    AND NEW.source_namespace IS DISTINCT FROM OLD.source_namespace THEN
   RAISE EXCEPTION 'case source namespace is immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS cases_keep_source_binding ON socai2.cases;
CREATE TRIGGER cases_keep_source_binding BEFORE INSERT OR UPDATE OF source_namespace
ON socai2.cases FOR EACH ROW EXECUTE FUNCTION socai2.keep_case_source_binding();

INSERT INTO public.aisoc_schema_migrations(name) VALUES ('124_socai2_case_source_binding.sql');

-- schema/125_socai2_baseline_input_freshness.sql (original SHA-256 262bc3343d7751b36b9c3ee69046ed858533dd8fc7ecf58c4a24f8e714d5473f)
-- Current-input checks use the existing immutable C1 snapshot. No new tables.

CREATE OR REPLACE FUNCTION socai2.task_feedback_signature(v jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,socai2 AS $fn$
 SELECT CASE WHEN v->>'state'='completed' AND nullif(btrim(v->>'result_text'),'') IS NOT NULL THEN
 jsonb_build_object('result_text',v->'result_text','result_scope',v->'result_scope',
   'source_refs',v->'source_refs','completed_at',v->'completed_at','completed_by',v->'completed_by') END
$fn$;

CREATE OR REPLACE FUNCTION socai2.baseline_input_freshness(p_tenant uuid,p_run uuid)
RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog,socai2 AS $fn$
 WITH r AS MATERIALIZED (
   SELECT * FROM socai2.runs WHERE tenant_id=p_tenant AND id=p_run AND kind='baseline'
 ), frozen AS MATERIALIZED (
   SELECT f.content_json AS body FROM socai2.artifacts f JOIN r ON r.id=f.run_id AND r.case_id=f.case_id
   WHERE f.tenant_id=p_tenant AND f.kind='source_snapshot' AND f.material_state='complete'
     AND f.schema_version='socai2.baseline-context.v1'
   ORDER BY f.captured_at,f.id LIMIT 1
 ), incident_ids AS (
   SELECT ci.incident_id FROM socai2.case_incidents ci JOIN r ON ci.case_id=r.case_id WHERE ci.tenant_id=p_tenant
   UNION SELECT ia.incident_id FROM socai2.incident_alerts ia JOIN socai2.case_alerts ca
     ON ca.tenant_id=ia.tenant_id AND ca.alert_id=ia.alert_id JOIN r ON ca.case_id=r.case_id WHERE ca.tenant_id=p_tenant
 ), live_incidents AS (
   SELECT coalesce(jsonb_object_agg(i.id::text,jsonb_build_object('diagnosis_id',i.latest_diagnosis_id,
     'member_ids',(SELECT coalesce(jsonb_agg(ia.alert_id ORDER BY ia.alert_id),'[]'::jsonb)
       FROM socai2.incident_alerts ia WHERE ia.tenant_id=p_tenant AND ia.incident_id=i.id))),'{}'::jsonb) AS value
   FROM socai2.incidents i JOIN incident_ids k ON k.incident_id=i.id WHERE i.tenant_id=p_tenant
 ), old_incidents AS (
   SELECT coalesce(jsonb_object_agg(k,jsonb_build_object('diagnosis_id',v->'incident'->'latest_diagnosis_id',
     'member_ids',v->'member_ids')),'{}'::jsonb) AS value
   FROM frozen, LATERAL jsonb_each(body->'incidents') e(k,v)
 ), live_tasks AS (
   SELECT coalesce(jsonb_object_agg(t.id::text,socai2.task_feedback_signature(to_jsonb(v)))
     FILTER(WHERE socai2.task_feedback_signature(to_jsonb(v)) IS NOT NULL),'{}'::jsonb) AS value
   FROM socai2.tasks t JOIN r ON t.case_id=r.case_id JOIN socai2.task_revisions v
     ON v.tenant_id=t.tenant_id AND v.task_id=t.id AND v.id=t.current_revision_id WHERE t.tenant_id=p_tenant
 ), old_tasks AS (
   SELECT coalesce(jsonb_object_agg(k,socai2.task_feedback_signature(v->'revision'))
     FILTER(WHERE socai2.task_feedback_signature(v->'revision') IS NOT NULL),'{}'::jsonb) AS value
   FROM frozen, LATERAL jsonb_each(body->'tasks') e(k,v)
 ), checks AS (
   SELECT array_remove(ARRAY[
     CASE WHEN NOT EXISTS(SELECT 1 FROM frozen WHERE body->>'schema_version'='socai2.baseline-context.v1')
       THEN 'frozen_context_unavailable' END,
     CASE WHEN EXISTS(SELECT 1 FROM r JOIN socai2.cases c ON c.tenant_id=r.tenant_id AND c.id=r.case_id
         WHERE r.scope_revision IS DISTINCT FROM c.scope_revision)
       OR EXISTS((SELECT ca.alert_id FROM socai2.case_alerts ca JOIN r ON r.case_id=ca.case_id WHERE ca.tenant_id=p_tenant
          EXCEPT SELECT rm.alert_id FROM socai2.run_members rm JOIN r ON r.id=rm.run_id WHERE rm.tenant_id=p_tenant)
         UNION ALL (SELECT rm.alert_id FROM socai2.run_members rm JOIN r ON r.id=rm.run_id WHERE rm.tenant_id=p_tenant
          EXCEPT SELECT ca.alert_id FROM socai2.case_alerts ca JOIN r ON r.case_id=ca.case_id WHERE ca.tenant_id=p_tenant))
       THEN 'scope_changed' END,
     CASE WHEN EXISTS(SELECT 1 FROM socai2.run_members rm JOIN r ON r.id=rm.run_id
       JOIN socai2.alerts a ON a.tenant_id=rm.tenant_id AND a.id=rm.alert_id WHERE rm.tenant_id=p_tenant
       AND (a.latest_material_id IS DISTINCT FROM rm.material_id OR a.latest_triage_id IS DISTINCT FROM rm.triage_id
         OR a.latest_feedback_id IS DISTINCT FROM rm.feedback_id)) THEN 'member_versions_changed' END,
     CASE WHEN (SELECT value FROM live_incidents) IS DISTINCT FROM (SELECT value FROM old_incidents)
       THEN 'incident_context_changed' END,
     CASE WHEN (SELECT value FROM live_tasks) IS DISTINCT FROM (SELECT value FROM old_tasks)
       THEN 'human_feedback_changed' END
   ]::text[],NULL) AS reasons
 ) SELECT jsonb_build_object('state',CASE WHEN NOT EXISTS(SELECT 1 FROM r) OR 'frozen_context_unavailable'=ANY(reasons)
       THEN 'unverified' WHEN cardinality(reasons)>0 THEN 'stale' ELSE 'current' END,
     'reasons',to_jsonb(reasons)) FROM checks
$fn$;

CREATE OR REPLACE FUNCTION socai2.auto_adopt_baseline_result(p_tenant uuid,p_result uuid)
RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog,socai2 AS $fn$
DECLARE res socai2.results%ROWTYPE; run socai2.runs%ROWTYPE; cas socai2.cases%ROWTYPE;
 cur socai2.case_assessments%ROWTYPE; prior_id uuid; next_id uuid:=gen_random_uuid();
 act_id uuid:=gen_random_uuid(); op_id uuid:=gen_random_uuid(); ts timestamptz:=clock_timestamp();
 next_revision bigint; svc jsonb; freshness jsonb;
BEGIN
 IF p_tenant IS DISTINCT FROM public.current_tenant_id() OR p_tenant IS NULL THEN
  RAISE EXCEPTION 'explicit tenant context required' USING ERRCODE='42501';
 END IF;
 SELECT * INTO res FROM socai2.results WHERE tenant_id=p_tenant AND id=p_result;
 IF NOT FOUND THEN RAISE EXCEPTION 'result not found' USING ERRCODE='23503'; END IF;
 SELECT * INTO cas FROM socai2.cases WHERE tenant_id=p_tenant AND id=res.case_id FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'case not found' USING ERRCODE='23503'; END IF;
 SELECT a.id INTO prior_id FROM socai2.case_assessments a
  JOIN socai2.case_assessment_sources s ON s.tenant_id=a.tenant_id AND s.assessment_id=a.id
  WHERE a.tenant_id=p_tenant AND a.case_id=cas.id AND s.result_id=res.id
    AND a.operation_key='baseline-auto:'||res.id::text LIMIT 1;
 IF FOUND THEN RETURN jsonb_build_object('state','already_adopted','assessment_id',prior_id); END IF;
 SELECT * INTO run FROM socai2.runs WHERE tenant_id=p_tenant AND id=res.source_run_id;
 IF NOT FOUND OR res.kind<>'baseline' OR run.kind<>'baseline' OR run.state<>'completed'
    OR res.validation_state<>'accepted' OR res.conclusion_origin<>'model'
    OR res.conclusion_state='unavailable' OR nullif(btrim(res.conclusion),'') IS NULL THEN
  RETURN jsonb_build_object('state','not_eligible');
 END IF;
 IF run.case_id IS DISTINCT FROM cas.id OR run.scope_revision IS DISTINCT FROM cas.scope_revision THEN
  RETURN jsonb_build_object('state','stale_scope');
 END IF;
 IF EXISTS(
  (SELECT alert_id FROM socai2.case_alerts WHERE tenant_id=p_tenant AND case_id=cas.id
   EXCEPT SELECT alert_id FROM socai2.run_members WHERE tenant_id=p_tenant AND run_id=run.id)
  UNION ALL
  (SELECT alert_id FROM socai2.run_members WHERE tenant_id=p_tenant AND run_id=run.id
   EXCEPT SELECT alert_id FROM socai2.case_alerts WHERE tenant_id=p_tenant AND case_id=cas.id)
 ) THEN RETURN jsonb_build_object('state','stale_scope'); END IF;
 freshness:=socai2.baseline_input_freshness(p_tenant,run.id);
 IF freshness->>'state'<>'current' THEN
  RETURN jsonb_build_object('state','stale_input','input_freshness',freshness);
 END IF;
 SELECT * INTO cur FROM socai2.case_assessments WHERE tenant_id=p_tenant AND id=cas.current_assessment_id;
 IF FOUND AND cur.adopted_at>=run.started_at THEN RETURN jsonb_build_object('state','newer_assessment'); END IF;
 IF NOT EXISTS(SELECT 1 FROM socai2.result_members WHERE tenant_id=p_tenant AND result_id=res.id
   AND conclusion_covered AND assessment_state IN ('analyzed','unresolved')) THEN
  RETURN jsonb_build_object('state','no_conclusion_coverage');
 END IF;
 -- Every promised member must have a delivery record, including explicit unresolved limitations.
 IF EXISTS(SELECT alert_id FROM socai2.run_members WHERE tenant_id=p_tenant AND run_id=run.id
  EXCEPT SELECT alert_id FROM socai2.result_members WHERE tenant_id=p_tenant AND result_id=res.id) THEN
  RETURN jsonb_build_object('state','missing_member_delivery');
 END IF;
 SELECT coalesce(max(revision),0)+1 INTO next_revision FROM socai2.case_assessments WHERE tenant_id=p_tenant AND case_id=cas.id;
 svc:=jsonb_build_object('type','service','user_id',NULL,'name_snapshot','基础调查结果自动采用',
  'service_name','socai2.baseline-publication','service_version','v1');
 INSERT INTO socai2.case_assessments(id,tenant_id,case_id,revision,conclusion,origin,validity,scope_revision,formed_at,adopted_at,actor,operation_key)
 VALUES(next_id,p_tenant,cas.id,next_revision,res.conclusion,'model','accepted',run.scope_revision,res.created_at,ts,svc,'baseline-auto:'||res.id::text);
 INSERT INTO socai2.case_assessment_sources(id,tenant_id,case_id,assessment_id,result_id)
 VALUES(gen_random_uuid(),p_tenant,cas.id,next_id,res.id);
 INSERT INTO socai2.case_assessment_members(id,tenant_id,case_id,assessment_id,alert_id,coverage_note)
 SELECT gen_random_uuid(),p_tenant,cas.id,next_id,alert_id,limitations FROM socai2.result_members
 WHERE tenant_id=p_tenant AND result_id=res.id AND conclusion_covered;
 UPDATE socai2.cases SET current_assessment_id=next_id,row_version=row_version+1,business_updated_at=ts
 WHERE tenant_id=p_tenant AND id=cas.id;
 INSERT INTO socai2.activities(id,tenant_id,operation_id,actor,action,subject_case_id,occurred_at,summary,detail)
 VALUES(act_id,p_tenant,op_id,svc,'case.assessment_adopted',cas.id,ts,'有效基础调查结果自动更新案件判断',
  jsonb_build_object('schema_version','activity.v1','reason',NULL,'request_key','baseline-auto:'||res.id::text,
   'source','baseline_publication','expected_version',cas.row_version,'actual_version',cas.row_version+1,'notes',jsonb_build_array()));
 INSERT INTO socai2.activity_targets(id,tenant_id,activity_id,case_id,before_value,after_value,result_state)
 VALUES(gen_random_uuid(),p_tenant,act_id,cas.id,jsonb_build_object('current_assessment_id',cas.current_assessment_id),
  jsonb_build_object('current_assessment_id',next_id),'succeeded');
 INSERT INTO socai2.activity_targets(id,tenant_id,activity_id,result_id,before_value,after_value,result_state)
 VALUES(gen_random_uuid(),p_tenant,act_id,res.id,NULL,jsonb_build_object('adopted_assessment_id',next_id),'succeeded');
 RETURN jsonb_build_object('state','adopted','assessment_id',next_id);
END $fn$;

INSERT INTO public.aisoc_schema_migrations(name) VALUES ('125_socai2_baseline_input_freshness.sql');

-- schema/126_socai2_case_page_data.sql (original SHA-256 c211409066fd51938ab88614f1cd9dec47f360a894b1091ab9daefc9c7db8597)
-- Additive page data only. Existing results, materials and migrations stay intact.

ALTER TABLE socai2.cases ADD COLUMN IF NOT EXISTS classification text;
ALTER TABLE socai2.cases ADD COLUMN IF NOT EXISTS due_at timestamptz;
ALTER TABLE socai2.cases ADD COLUMN IF NOT EXISTS current_evidence_artifact_id uuid;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_classification_enum') THEN
  ALTER TABLE socai2.cases ADD CONSTRAINT cases_classification_enum
   CHECK (classification IN ('true_positive','informational','false_positive'));
 END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='socai2.cases'::regclass AND conname='cases_current_evidence_scope_fk') THEN
  ALTER TABLE socai2.cases ADD CONSTRAINT cases_current_evidence_scope_fk
   FOREIGN KEY(tenant_id,id,current_evidence_artifact_id)
   REFERENCES socai2.artifacts(tenant_id,case_id,id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
 END IF;
END $$;
ALTER TABLE socai2.artifacts DROP CONSTRAINT artifacts_kind_enum;
ALTER TABLE socai2.artifacts ADD CONSTRAINT artifacts_kind_enum CHECK (kind IN
 ('input_snapshot','model_request','model_response','tool_request','tool_response',
  'domain_analysis','deep_analysis','attack_chain','attack_path','alert_graph',
  'report_json','report_markdown','attachment','source_snapshot','handoff','query_plan',
  'alert_explanation','case_evidence_index'));
CREATE OR REPLACE FUNCTION socai2.check_case_evidence_pointer() RETURNS trigger
 LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.current_evidence_artifact_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM socai2.artifacts a WHERE a.tenant_id=NEW.tenant_id AND a.case_id=NEW.id
   AND a.id=NEW.current_evidence_artifact_id AND a.kind='case_evidence_index'
   AND a.schema_version='socai2.case-evidence.v1' AND jsonb_typeof(a.content_json)='object'
 ) THEN RAISE EXCEPTION 'case_evidence_pointer_invalid' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS cases_evidence_pointer ON socai2.cases;
CREATE CONSTRAINT TRIGGER cases_evidence_pointer
 AFTER INSERT OR UPDATE ON socai2.cases DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION socai2.check_case_evidence_pointer();
COMMENT ON COLUMN socai2.cases.classification IS 'Explicit Case management classification; NULL means not set';
COMMENT ON COLUMN socai2.cases.due_at IS 'Optional Case deadline; independent of tasks and execution budgets';
COMMENT ON COLUMN socai2.cases.current_evidence_artifact_id IS 'Selected immutable case_evidence_index; NULL means not recorded';

INSERT INTO public.aisoc_schema_migrations(name) VALUES ('126_socai2_case_page_data.sql');

\endif
SET LOCAL search_path = pg_catalog;
DO $ledger$
BEGIN
    IF (SELECT array_agg(name::text ORDER BY name) FROM public.aisoc_schema_migrations
        WHERE position('_socai2_' IN name) > 0) IS DISTINCT FROM ARRAY['123_socai2_page_data_model.sql',
            '124_socai2_case_source_binding.sql',
            '125_socai2_baseline_input_freshness.sql',
            '126_socai2_case_page_data.sql']::text[] THEN
        RAISE EXCEPTION 'Expected exactly the V1 socai2 migration entries 123 through 126';
    END IF;
END
$ledger$;

-- Verify the catalog against the 21 handoff baseline before committing.
WITH relations AS (
    SELECT c.* FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'socai2' AND c.relkind IN ('r', 'p')
), objects(section, name, definition) AS (
    SELECT 'tables', relname::text,
           jsonb_build_array(relkind, relpersistence, relrowsecurity, relforcerowsecurity)
    FROM relations
    UNION ALL
    SELECT 'columns', r.relname || '.' || a.attname,
           jsonb_build_array(a.attnum, format_type(a.atttypid, a.atttypmod),
               NOT a.attnotnull, pg_get_expr(d.adbin, d.adrelid), a.attidentity, a.attgenerated)
    FROM relations r JOIN pg_attribute a ON a.attrelid = r.oid
    LEFT JOIN pg_attrdef d ON d.adrelid = r.oid AND d.adnum = a.attnum
    WHERE a.attnum > 0 AND NOT a.attisdropped
    UNION ALL
    SELECT 'constraints', r.relname || '.' || c.conname,
           jsonb_build_array(pg_get_constraintdef(c.oid), c.convalidated)
    FROM relations r JOIN pg_constraint c ON c.conrelid = r.oid
    UNION ALL
    SELECT 'indexes', r.relname || '.' || i.relname,
           jsonb_build_array(pg_get_indexdef(x.indexrelid), x.indisvalid, x.indisready)
    FROM relations r JOIN pg_index x ON x.indrelid = r.oid
    JOIN pg_class i ON i.oid = x.indexrelid
    UNION ALL
    SELECT 'policies', r.relname || '.' || p.polname,
           jsonb_build_array(p.polcmd, p.polpermissive, ARRAY(
               SELECT CASE WHEN role_id = 0 THEN 'PUBLIC' ELSE pg_get_userbyid(role_id)::text END
               FROM unnest(p.polroles) role_id ORDER BY 1),
               pg_get_expr(p.polqual, r.oid), pg_get_expr(p.polwithcheck, r.oid))
    FROM relations r JOIN pg_policy p ON p.polrelid = r.oid
    UNION ALL
    SELECT 'triggers', r.relname || '.' || t.tgname,
           jsonb_build_array(pg_get_triggerdef(t.oid), t.tgenabled)
    FROM relations r JOIN pg_trigger t ON t.tgrelid = r.oid WHERE NOT t.tgisinternal
    UNION ALL
    SELECT 'functions', p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')',
           to_jsonb(replace(pg_get_functiondef(p.oid), E'\r\n', E'\n'))
    FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname = 'socai2'
), sections AS (
    SELECT section, jsonb_object_agg(name, definition) AS objects FROM objects GROUP BY section
)
SELECT jsonb_object_agg(section, encode(sha256(convert_to(objects::text, 'UTF8')), 'hex'))
       = '{
    "columns": "13a82869e532a203aa2232a6f695a7e824f477be0bd2932cf11ec41d13485195",
    "constraints": "f00d085b8c977136604cbeb2d69fe60d87c5affd755852b8ab89858df4e6ef5d",
    "functions": "350f7811cf2dec787616f5ff9fe2f6e7f22f53cb221a6b566096e19225702fba",
    "indexes": "528d04c8ac6a6d742dc6a24b5381f77b60ece06262c351ef3c88ebca2d86592a",
    "policies": "2ea53648654909d5a69302239d57b9c720da1fea7785d602d73730f243edea8f",
    "tables": "a6a027dc9cf7d6a0443f0d2ad7f667a0cb8cc9a3d8184170ae499a3ab8f6326a",
    "triggers": "156a26a12d4fd881e7a4b44cee504be117c1a8a1d4685ed78ccf56bf4e791d0f"
}'::jsonb AS verified FROM sections \gset
\if :verified
COMMIT;
\if :fresh_install
\echo Initialized socai2 V1 (29 tables, 462 columns).
\else
\echo Verified existing socai2 V1 (29 tables, 462 columns). No migrations replayed.
\endif
\else
DO $$ BEGIN RAISE EXCEPTION 'The socai2 catalog differs from V1; transaction aborted'; END $$;
\endif
