-- AiSOC ClickHouse init: raw events + metrics
-- Runs at container start via /docker-entrypoint-initdb.d

CREATE DATABASE IF NOT EXISTS aisoc;

-- ──────────────────────────────────────────────────────────────────────────────
-- Raw OCSF events.
--
-- Reference new-install DDL, generated from app/db/lake_columns_v1.json and
-- deploy/aisoc21/lake-storage-3b/storage.example.json. Runtime migrations and
-- purge MUST select the matching AISOC_LAKE_STORAGE_POLICY_FILE explicitly.
-- For another database/policy use python -m app.scripts.lake_schema --profile
-- <file> --output <sql>; do not edit only this reference TTL or column list.
-- 005_lake_ingress_v1 upgrades existing 48-column installations without backfill.
-- New configured mappings expire by ingest_time; legacy rows keep event_time.
CREATE TABLE IF NOT EXISTS aisoc.raw_events (
    event_id UUID DEFAULT generateUUIDv4(),
    tenant_id UUID,
    event_time DateTime64(3, 'UTC'),
    ingest_time DateTime64(3, 'UTC') DEFAULT now64(),
    class_uid UInt32,
    category_uid UInt32,
    severity_id UInt8,
    severity String,
    activity_id UInt32,
    source_ip IPv6,
    dest_ip IPv6,
    src_port UInt16,
    dst_port UInt16,
    protocol String,
    src_hostname String,
    dst_hostname String,
    user_name String,
    process_name String,
    file_path String,
    hash_sha256 String,
    connector_type String,
    raw_payload String CODEC(ZSTD(3)),
    ocsf_json String CODEC(ZSTD(3)),
    mitre_techniques Array(String),
    mitre_tactics Array(String),
    iocs Array(String),
    actor_kind LowCardinality(String) DEFAULT '',
    actor_kind_source String DEFAULT '',
    actor_id String DEFAULT '',
    actor_on_behalf_of String DEFAULT '',
    action String DEFAULT '',
    resource_type String DEFAULT '',
    resource_id String DEFAULT '',
    resource_owner String DEFAULT '',
    src_country_code LowCardinality(String) DEFAULT '',
    src_asn UInt32 DEFAULT 0,
    src_as_org String DEFAULT '',
    src_reputation Float32 DEFAULT 0,
    src_reputation_known UInt8 DEFAULT 0,
    client_family LowCardinality(String) DEFAULT '',
    client_version String DEFAULT '',
    client_category LowCardinality(String) DEFAULT '',
    client_raw String DEFAULT '',
    outcome LowCardinality(String) DEFAULT '',
    session_id String DEFAULT '',
    session_key String DEFAULT '',
    session_key_kind LowCardinality(String) DEFAULT '',
    session_originating_human String DEFAULT '',
    source_namespace LowCardinality(String) DEFAULT '',
    source_event_id String DEFAULT '',
    source_version String DEFAULT '',
    is_alert Nullable(UInt8) DEFAULT NULL,
    device_hostname String DEFAULT '',
    device_ip Nullable(IPv6) DEFAULT NULL,
    event_time_source LowCardinality(String) DEFAULT 'unknown',
    parse_status LowCardinality(String) DEFAULT 'unknown',
    mapping_version LowCardinality(String) DEFAULT '',
    kafka_cluster LowCardinality(String) DEFAULT '',
    kafka_topic LowCardinality(String) DEFAULT '',
    kafka_partition Nullable(Int32) DEFAULT NULL,
    kafka_offset Nullable(Int64) DEFAULT NULL,
    kafka_timestamp Nullable(DateTime64(3, 'UTC')) DEFAULT NULL,
    INDEX idx_hash hash_sha256 TYPE bloom_filter(0.01) GRANULARITY 4,
    INDEX idx_user user_name TYPE bloom_filter(0.01) GRANULARITY 4,
    INDEX idx_src_host src_hostname TYPE bloom_filter(0.01) GRANULARITY 4,
    INDEX idx_iocs iocs TYPE bloom_filter(0.01) GRANULARITY 4,
    INDEX idx_techniques mitre_techniques TYPE bloom_filter(0.01) GRANULARITY 4,
    INDEX idx_action action TYPE bloom_filter(0.01) GRANULARITY 4,
    INDEX idx_resource_id resource_id TYPE bloom_filter(0.01) GRANULARITY 4,
    INDEX idx_session_id session_id TYPE bloom_filter(0.01) GRANULARITY 4,
    CONSTRAINT lake_is_alert_bool CHECK isNull(is_alert) OR is_alert IN (0, 1),
    CONSTRAINT lake_partition_nonnegative CHECK isNull(kafka_partition) OR kafka_partition >= 0,
    CONSTRAINT lake_offset_nonnegative CHECK isNull(kafka_offset) OR kafka_offset >= 0)
ENGINE = ReplacingMergeTree(ingest_time)
PARTITION BY (toYYYYMM(event_time), tenant_id)
ORDER BY (tenant_id, event_time, class_uid, event_id)
TTL if(mapping_version IN ('spirithub-ocsf-lake-v1'), toDateTime(ingest_time) + toIntervalDay(400), toDateTime(event_time) + toIntervalDay(400))
SETTINGS index_granularity = 8192;

-- ──────────────────────────────────────────────────────────────────────────────
-- Alert metrics for dashboards
-- ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS aisoc.alert_metrics (
    ts              DateTime DEFAULT now(),
    tenant_id       UUID,
    severity        String,
    connector_type  String,
    mitre_tactic    String,
    count           UInt64,
    avg_score       Float32
) ENGINE = SummingMergeTree(count)
PARTITION BY toYYYYMM(ts)
ORDER BY (tenant_id, toStartOfHour(ts), severity, connector_type, mitre_tactic)
TTL ts + INTERVAL 365 DAY;

-- ──────────────────────────────────────────────────────────────────────────────
-- IOC lookup table (append-only enrichment cache)
-- ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS aisoc.ioc_enrichments (
    ioc_value       String,
    ioc_type        String,
    tenant_id       UUID,
    malicious       UInt8,
    confidence      Float32,
    sources         Array(String),
    tags            Array(String),
    country         String,
    asn             UInt32,
    enriched_at     DateTime64(3, 'UTC') DEFAULT now64()
) ENGINE = ReplacingMergeTree(enriched_at)
ORDER BY (ioc_value, ioc_type, tenant_id)
TTL toDateTime(enriched_at) + INTERVAL 30 DAY;
