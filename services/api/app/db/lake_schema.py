"""Lake 3b schema and retention policy, selected explicitly for one database."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

_SCHEMA = json.loads(Path(__file__).with_name("lake_columns_v1.json").read_text())
COLUMNS = tuple(tuple(column) for column in _SCHEMA["columns"])
NEW_COLUMNS = COLUMNS[48:]
CONSTRAINTS = {
    "lake_is_alert_bool": "isNull(is_alert) OR is_alert IN (0, 1)",
    "lake_partition_nonnegative": "isNull(kafka_partition) OR kafka_partition >= 0",
    "lake_offset_nonnegative": "isNull(kafka_offset) OR kafka_offset >= 0",
}


def sql_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


@dataclass(frozen=True)
class LakeStoragePolicy:
    database: str
    ingest_mapping_versions: tuple[str, ...]
    ingest_days: int
    legacy_days: int

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", self.database):
            raise ValueError("invalid lake database identifier")
        if not isinstance(self.ingest_mapping_versions, tuple) or not self.ingest_mapping_versions:
            raise ValueError("ingest_mapping_versions must explicitly name at least one mapping")
        if any(not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", v) for v in self.ingest_mapping_versions):
            raise ValueError("invalid ingest mapping version")
        if len(set(self.ingest_mapping_versions)) != len(self.ingest_mapping_versions):
            raise ValueError("duplicate ingest mapping version")
        if any(type(days) is not int or not 1 <= days <= 3650 for days in (self.ingest_days, self.legacy_days)):
            raise ValueError("retention days must be integers in 1..3650")

    @property
    def table(self) -> str:
        return f"{self.database}.raw_events"

    @property
    def mapping_predicate(self) -> str:
        return "mapping_version IN (" + ", ".join(map(sql_string, self.ingest_mapping_versions)) + ")"

    @property
    def ttl(self) -> str:
        return (
            f"if({self.mapping_predicate}, toDateTime(ingest_time) + toIntervalDay({self.ingest_days}), "
            f"toDateTime(event_time) + toIntervalDay({self.legacy_days}))"
        )

    def purge_predicate(self, tenant_id: uuid.UUID, legacy_days: int) -> str:
        days = max(1, min(self.legacy_days, int(legacy_days)))
        return (
            f"tenant_id = '{uuid.UUID(str(tenant_id))}' AND if({self.mapping_predicate}, "
            f"ingest_time < now() - INTERVAL {self.ingest_days} DAY, "
            f"event_time < now() - INTERVAL {days} DAY)"
        )


def load_policy(path: str | Path, *, database: str | None = None) -> LakeStoragePolicy:
    if not path:
        raise ValueError("AISOC_LAKE_STORAGE_POLICY_FILE must explicitly select a storage profile")
    body = json.loads(Path(path).read_text())
    if set(body) != {"database", "retention"} or set(body["retention"]) != {"ingest_mapping_versions", "ingest_days", "legacy_days"}:
        raise ValueError("unexpected or missing lake storage profile fields")
    retention = body["retention"]
    if not isinstance(retention["ingest_mapping_versions"], list):
        raise TypeError("ingest_mapping_versions must be a list")
    policy = LakeStoragePolicy(body["database"], tuple(retention["ingest_mapping_versions"]), retention["ingest_days"], retention["legacy_days"])
    if database is not None and policy.database != database:
        raise ValueError("lake storage profile database differs from CLICKHOUSE_DATABASE")
    return policy


def configured_policy() -> LakeStoragePolicy:
    from app.core.config import settings

    return load_policy(settings.AISOC_LAKE_STORAGE_POLICY_FILE, database=settings.CLICKHOUSE_DATABASE)


def column_definition(column: tuple[str, ...]) -> str:
    name, kind, default, codec = column
    return f"{name} {kind}" + (f" DEFAULT {default}" if default else "") + (f" CODEC{codec}" if codec else "")


def migration_statements(policy: LakeStoragePolicy) -> tuple[str, ...]:
    return (
        *(f"ALTER TABLE {policy.table} ADD COLUMN IF NOT EXISTS {column_definition(c)}" for c in NEW_COLUMNS),
        *(f"ALTER TABLE {policy.table} ADD CONSTRAINT IF NOT EXISTS {name} CHECK {expr}" for name, expr in CONSTRAINTS.items()),
        f"ALTER TABLE {policy.table} MODIFY TTL {policy.ttl} SETTINGS materialize_ttl_after_modify = 0",
    )


def create_table_sql(policy: LakeStoragePolicy) -> str:
    definitions = [column_definition(c) for c in COLUMNS]
    definitions.extend(_SCHEMA["indexes"])
    definitions.extend(f"CONSTRAINT {name} CHECK {expr}" for name, expr in CONSTRAINTS.items())
    return (
        f"CREATE TABLE IF NOT EXISTS {policy.table} (\n    " + ",\n    ".join(definitions)
        + ")\nENGINE = ReplacingMergeTree(ingest_time)\n"
        "PARTITION BY (toYYYYMM(event_time), tenant_id)\n"
        "ORDER BY (tenant_id, event_time, class_uid, event_id)\n"
        f"TTL {policy.ttl}\nSETTINGS index_granularity = 8192;\n"
    )
