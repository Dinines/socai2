-- 3a contract SQL reference; implemented by 005_lake_ingress_v1 in 3b.
-- Validated in isolated 23.8 test databases only; formal lake not migrated.
-- Deployment uses app.db.lake_schema with an explicit storage profile.
-- __LAKE_DATABASE__ is a validated identifier rendered from an explicit profile.
-- Preserve existing rows, ORDER BY, PARTITION BY, engine and existing column types.
-- 3b new-install/profile/purge are synchronized; writer/query work remains 3c-3f.

ALTER TABLE __LAKE_DATABASE__.raw_events ADD COLUMN IF NOT EXISTS source_namespace LowCardinality(String) DEFAULT '';
ALTER TABLE __LAKE_DATABASE__.raw_events ADD COLUMN IF NOT EXISTS source_event_id String DEFAULT '';
ALTER TABLE __LAKE_DATABASE__.raw_events ADD COLUMN IF NOT EXISTS source_version String DEFAULT '';
ALTER TABLE __LAKE_DATABASE__.raw_events ADD COLUMN IF NOT EXISTS is_alert Nullable(UInt8) DEFAULT NULL;
ALTER TABLE __LAKE_DATABASE__.raw_events ADD COLUMN IF NOT EXISTS device_hostname String DEFAULT '';
ALTER TABLE __LAKE_DATABASE__.raw_events ADD COLUMN IF NOT EXISTS device_ip Nullable(IPv6) DEFAULT NULL;
ALTER TABLE __LAKE_DATABASE__.raw_events ADD COLUMN IF NOT EXISTS event_time_source LowCardinality(String) DEFAULT 'unknown';
ALTER TABLE __LAKE_DATABASE__.raw_events ADD COLUMN IF NOT EXISTS parse_status LowCardinality(String) DEFAULT 'unknown';
ALTER TABLE __LAKE_DATABASE__.raw_events ADD COLUMN IF NOT EXISTS mapping_version LowCardinality(String) DEFAULT '';
ALTER TABLE __LAKE_DATABASE__.raw_events ADD COLUMN IF NOT EXISTS kafka_cluster LowCardinality(String) DEFAULT '';
ALTER TABLE __LAKE_DATABASE__.raw_events ADD COLUMN IF NOT EXISTS kafka_topic LowCardinality(String) DEFAULT '';
ALTER TABLE __LAKE_DATABASE__.raw_events ADD COLUMN IF NOT EXISTS kafka_partition Nullable(Int32) DEFAULT NULL;
ALTER TABLE __LAKE_DATABASE__.raw_events ADD COLUMN IF NOT EXISTS kafka_offset Nullable(Int64) DEFAULT NULL;
ALTER TABLE __LAKE_DATABASE__.raw_events ADD COLUMN IF NOT EXISTS kafka_timestamp Nullable(DateTime64(3, 'UTC')) DEFAULT NULL;

-- Constraints are compatible with legacy defaults; no MATERIALIZE COLUMN/INDEX or history UPDATE.
ALTER TABLE __LAKE_DATABASE__.raw_events ADD CONSTRAINT IF NOT EXISTS lake_is_alert_bool CHECK isNull(is_alert) OR is_alert IN (0, 1);
ALTER TABLE __LAKE_DATABASE__.raw_events ADD CONSTRAINT IF NOT EXISTS lake_partition_nonnegative CHECK isNull(kafka_partition) OR kafka_partition >= 0;
ALTER TABLE __LAKE_DATABASE__.raw_events ADD CONSTRAINT IF NOT EXISTS lake_offset_nonnegative CHECK isNull(kafka_offset) OR kafka_offset >= 0;

-- TTL is rendered from profile; preserve the legacy branch. Coordinate purge SQL BEFORE enabling ingress.
ALTER TABLE __LAKE_DATABASE__.raw_events MODIFY TTL
    if(mapping_version IN (__INGEST_MAPPING_VERSIONS__),
       toDateTime(ingest_time) + toIntervalDay(__INGEST_RETENTION_DAYS__),
       toDateTime(event_time) + toIntervalDay(__LEGACY_RETENTION_DAYS__))
SETTINGS materialize_ttl_after_modify = 0;
