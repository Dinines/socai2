"""Scoped fixed SQL for lake search, material lookup and C4 v2 reads."""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from .lake_hostname import hostname_key, supported_hostname
from .lake_query_contracts import (
    LakeMaterial,
    LakeReadError,
    LakeRecordRef,
    LakeSearchResult,
)

MAPPING = "spirithub-ocsf-lake-v1"
SUMMARY_FIELDS = ("event_id", "tenant_id", "event_time", "ingest_time", "class_uid", "source_namespace", "source_event_id",
    "source_version", "mapping_version", "event_time_source", "parse_status", "is_alert", "device_hostname", "device_ip",
    "src_hostname", "source_ip", "dst_hostname", "dest_ip")
EVIDENCE_FIELDS = (*SUMMARY_FIELDS, "process_name", "src_port", "dst_port", "protocol", "file_path", "hash_sha256", "user_name",
    "action", "outcome", "session_id", "session_key", "session_key_kind", "session_originating_human", "ocsf_json", "raw_payload")
ROLE_COLUMNS = {("device", "hostname"): "device_hostname", ("device", "ip"): "device_ip",
    ("source", "hostname"): "src_hostname", ("source", "ip"): "source_ip",
    ("destination", "hostname"): "dst_hostname", ("destination", "ip"): "dest_ip",
    ("legacy_host", "hostname"): "src_hostname"}
LIMITATIONS = ["object_time_match_not_causality_or_alert_membership", "empty_query_is_not_counterevidence",
              "current_versions_not_a_concurrent_write_snapshot", "coverage_and_collection_completeness_unknown"]


def fail(code, state="failed", status=422):
    raise LakeReadError(code, state, status)


def stamp(value):
    value = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(value, datetime):
        fail("invalid_lake_time")
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def canonical_ip(value):
    ip = ipaddress.ip_address(value)
    return str(ip.ipv4_mapped or ip) if isinstance(ip, ipaddress.IPv6Address) else str(ip)


def selector_value(selector):
    value = selector.value
    if selector.kind == "hostname":
        if not supported_hostname(value):
            fail("unsupported_lake_hostname")
        return hostname_key(value)
    try:
        value = canonical_ip(value)
        if ipaddress.ip_address(value).is_unspecified:
            raise ValueError
    except ValueError:
        fail("invalid_lake_ip")
    return value


def display_ip(value):
    if value is None:
        return None
    value = canonical_ip(value)
    return None if ipaddress.ip_address(value).is_unspecified else value


@dataclass(frozen=True)
class LakeQueryProfile:
    database: str
    scopes: tuple[dict, ...]
    default_page_size: int
    max_page_size: int
    max_window_seconds: int
    max_result_bytes: int
    transport: dict
    digest: str

    @classmethod
    def load(cls, path, *, database):
        try:
            raw = Path(path).read_bytes()
            data = json.loads(raw)
            if set(data) != {"version", "database", "scopes", "default_page_size", "max_page_size", "max_window_seconds", "max_result_bytes", "transport"}:
                raise ValueError
            if data.pop("version") != "socai2.lake-query.v1" or data["database"] != database or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", database):
                raise ValueError
            for name in ("default_page_size", "max_page_size", "max_window_seconds", "max_result_bytes"):
                if type(data[name]) is not int or data[name] <= 0:
                    raise ValueError
            if data["default_page_size"] > data["max_page_size"] or not isinstance(data["scopes"], list) or not data["scopes"]:
                raise ValueError
            scopes = []
            for scope in data["scopes"]:
                if set(scope) != {"tenant_id", "source_namespace", "mapping_version"}:
                    raise ValueError
                tenant = str(UUID(scope["tenant_id"]))
                source, mapping = scope["source_namespace"], scope["mapping_version"]
                if (not isinstance(source, str) or len(source) > 512 or mapping not in {MAPPING, ""}
                        or bool(source.strip()) != bool(mapping) or {**scope, "tenant_id": tenant} in scopes):
                    raise ValueError
                scopes.append({**scope, "tenant_id": tenant})
            transport = data["transport"]
            if set(transport) != {"query_timeout_seconds", "connect_timeout_seconds", "send_receive_timeout_seconds", "close_timeout_seconds"}:
                raise ValueError
            if any(type(v) not in {int, float} or not 0 < v < float("inf") for v in transport.values()) or transport["query_timeout_seconds"] < 1:
                raise ValueError
            return cls(**{**data, "scopes": tuple(scopes)}, digest=hashlib.sha256(raw).hexdigest())
        except (ValueError, TypeError, OSError, KeyError, AttributeError):
            fail("lake_query_profile_invalid", "unavailable", 503)

    def require_scope(self, tenant, source, mapping):
        scope = {"tenant_id": str(UUID(str(tenant))), "source_namespace": source, "mapping_version": mapping}
        if scope not in self.scopes:
            fail("lake_query_scope_not_configured")
        return scope


def active_profile():
    from app.core.config import settings
    if not settings.SOCAI2_LAKE_QUERY_PROFILE_FILE:
        fail("lake_query_profile_required", "unavailable", 503)
    return LakeQueryProfile.load(settings.SOCAI2_LAKE_QUERY_PROFILE_FILE, database=settings.CLICKHOUSE_DATABASE)


def normalize_rows(rows):
    output = []
    for row in rows:
        out = dict(row)
        for name in ("event_id", "tenant_id"):
            if name in out:
                out[name] = str(out[name])
        for name in ("event_time", "ingest_time"):
            if name in out:
                out[name] = stamp(out[name]).isoformat()
        for name in ("device_ip", "source_ip", "dest_ip"):
            if name in out and out[name] is not None:
                out[name] = str(out[name])
        output.append(out)
    return output


def base_sql(profile, fields):
    columns = ", ".join(fields)
    # Filter objects and windows after deduplication: an old retry must not
    # reappear just because its ingest_time fell inside the requested window.
    return f"""SELECT {columns} FROM (
 SELECT {columns}, row_number() OVER (PARTITION BY tenant_id,event_time,class_uid,event_id
 ORDER BY ingest_time DESC,kafka_topic DESC,kafka_partition DESC,kafka_offset DESC) AS source_rank
 FROM {profile.database}.raw_events WHERE tenant_id=%(tenant_id)s
 AND source_namespace=%(source_namespace)s AND mapping_version=%(mapping_version)s
) WHERE source_rank=1"""


def search_sql(profile, tenant, query, *, full=False):
    scope = profile.require_scope(tenant, query.source_namespace, query.mapping_version)
    legacy = not query.mapping_version
    column = ROLE_COLUMNS.get((query.selector.role, query.selector.kind)) if query.selector else None
    if query.selector and (column is None or query.selector.role == "legacy_host" and not legacy):
        fail("unsupported_lake_object_role")
    if query.selector and legacy and (query.selector.role == "device" or (query.selector.kind == "hostname" and query.selector.role == "source")):
        fail("legacy_object_role_unavailable")
    if (query.time_basis == "legacy_event" and not legacy) or (query.time_basis == "event" and legacy):
        fail("incompatible_lake_time_basis")
    start, end = query.start.astimezone(UTC), query.end.astimezone(UTC)
    if not 0 < (end - start).total_seconds() <= profile.max_window_seconds:
        fail("invalid_lake_time_window")
    limit = query.limit if query.limit is not None else profile.default_page_size
    if not 1 <= limit <= profile.max_page_size:
        fail("invalid_lake_page_size")
    classes = query.class_uids
    if classes is not None and (not classes or any(type(v) is not int or not 0 <= v <= 2**32-1 for v in classes)):
        fail("invalid_lake_class_filter")
    value = selector_value(query.selector) if query.selector else None
    effective = {**query.model_dump(mode="json", exclude={"cursor", "limit"}), "selector": {**query.selector.model_dump(), "value": value} if query.selector else None,
                 "profile": profile.digest, "tenant": str(tenant)}
    fingerprint = hashlib.sha256(json.dumps(effective, sort_keys=True).encode()).hexdigest()
    time_column = "ingest_time" if query.time_basis == "ingest" else "event_time"
    sql = base_sql(profile, EVIDENCE_FIELDS if full else SUMMARY_FIELDS)
    sql += f" AND {time_column}>=toDateTime64(%(start)s,6,'UTC') AND {time_column}<toDateTime64(%(end)s,6,'UTC')"
    if query.time_basis == "event":
        sql += " AND event_time_source='ocsf_time_ms'"
    if query.selector:
        sql += f" AND lower({column})=%(value)s" if query.selector.kind == "hostname" else f" AND {column}=toIPv6(%(value)s)"
    if classes is not None:
        sql += " AND class_uid IN %(classes)s"
    bound = {**scope, "start": start.strftime("%Y-%m-%d %H:%M:%S.%f"), "end": end.strftime("%Y-%m-%d %H:%M:%S.%f"),
             "value": value, "classes": tuple(sorted(set(classes or []))), "fetch_limit": limit+1}
    if query.cursor:
        try:
            cursor = json.loads(base64.urlsafe_b64decode(query.cursor.encode()))
            if set(cursor) != {"query", "key"} or cursor["query"] != fingerprint or len(cursor["key"]) != 4:
                raise ValueError
            when, occurred, cls, eid = cursor["key"]
            if type(cls) is not int or not 0 <= cls < 2**32:
                raise ValueError
            bound.update(after_time=stamp(when).strftime("%Y-%m-%d %H:%M:%S.%f"),
                         after_event=stamp(occurred).strftime("%Y-%m-%d %H:%M:%S.%f"), after_class=cls, after_id=str(UUID(eid)))
        except (ValueError, TypeError, KeyError, UnicodeError):
            fail("invalid_lake_cursor")
        sql += f" AND ({time_column},event_time,class_uid,event_id) > (toDateTime64(%(after_time)s,6,'UTC'),toDateTime64(%(after_event)s,6,'UTC'),%(after_class)s,toUUID(%(after_id)s))"
    sql += f" ORDER BY {time_column},event_time,class_uid,event_id LIMIT %(fetch_limit)s"
    return sql, bound, limit, fingerprint, time_column


def record_ref(row):
    return {name: row[name] for name in LakeRecordRef.model_fields}


def validate_search_rows(rows, profile, tenant, query, *, full=False):
    _, _, limit, _, clock = search_sql(profile, tenant, query, full=full)
    if len(rows) > limit + 1:
        fail("lake_result_limit_mismatch", status=502)
    seen = set()
    for row in rows:
        if set(row) != set(EVIDENCE_FIELDS if full else SUMMARY_FIELDS):
            fail("lake_column_contract_mismatch", status=502)
        key = (row["event_time"], row["class_uid"], row["event_id"])
        matched = True
        if query.selector:
            column = ROLE_COLUMNS[(query.selector.role, query.selector.kind)]
            matched = (isinstance(row[column], str) and hostname_key(row[column]) == selector_value(query.selector) if query.selector.kind == "hostname"
                       else row[column] is not None and canonical_ip(row[column]) == selector_value(query.selector))
        if (row["tenant_id"] != str(tenant) or row["source_namespace"] != query.source_namespace or row["mapping_version"] != query.mapping_version
                or not matched or not query.start <= stamp(row[clock]) < query.end or key in seen
                or query.time_basis == "event" and row["event_time_source"] != "ocsf_time_ms"
                or query.class_uids is not None and row["class_uid"] not in query.class_uids):
            fail("lake_row_outside_bound_scope", status=502)
        seen.add(key)


class LakeQueries:
    def __init__(self, profile, execute=None):
        self.profile, self.execute = profile, execute

    async def rows(self, sql, params, *, row_limit, query_id=None, timeout=None):
        from app.db.clickhouse import (
            LakeQueryError,
            LakeQueryNotConfiguredError,
            execute_lake_query,
        )
        from app.db.clickhouse_owned import LakeQueryInterrupted, LakeQueryRejected
        try:
            result = await (self.execute or execute_lake_query)(sql, params=params, query_id=query_id or str(uuid4()),
                timeout_seconds=min(timeout if timeout is not None else self.profile.transport["query_timeout_seconds"], self.profile.transport["query_timeout_seconds"]),
                owned_policy=self.profile.transport,
                extra_settings={"readonly": 2, "max_result_rows": row_limit, "max_result_bytes": self.profile.max_result_bytes, "result_overflow_mode": "throw"})
        except LakeQueryInterrupted as exc:
            received = normalize_rows([dict(zip(exc.columns, row, strict=True)) for row in exc.rows])
            raise LakeReadError("lake_query_interrupted", "unknown", 504, received) from None
        except LakeQueryNotConfiguredError:
            fail("lake_not_configured", "unavailable", 503)
        except (LakeQueryRejected, LakeQueryError):
            fail("lake_query_failed", status=502)
        try:
            names = [c["name"] if isinstance(c, dict) else c for c in result.columns]
            if len(names) != len(set(names)):
                raise ValueError
            return normalize_rows([dict(zip(names, row, strict=True)) for row in result.rows])
        except (ValueError, TypeError, KeyError):
            fail("lake_column_contract_mismatch", status=502)

    async def evidence(self, tenant, query, *, query_id=None, timeout=None):
        sql, params, limit, _, _ = search_sql(self.profile, tenant, query, full=True)
        rows = await self.rows(sql, params, row_limit=limit+1, query_id=query_id, timeout=timeout)
        validate_search_rows(rows, self.profile, tenant, query, full=True)
        return rows

    async def search(self, tenant, query):
        sql, params, limit, fingerprint, clock = search_sql(self.profile, tenant, query)
        rows = await self.rows(sql, params, row_limit=limit+1)
        validate_search_rows(rows, self.profile, tenant, query)
        more = len(rows) > limit
        rows = rows[:limit]
        cursor = None
        if more:
            last = rows[-1]
            cursor = base64.urlsafe_b64encode(json.dumps({"query": fingerprint,
                "key": [last[clock], last["event_time"], last["class_uid"], last["event_id"]]}, separators=(",", ":")).encode()).decode()
        items = []
        for row in rows:
            item = {name: row[name] for name in ("ingest_time", "event_time_source", "parse_status", "source_event_id", "is_alert",
                                                "device_hostname", "device_ip", "src_hostname", "source_ip", "dst_hostname", "dest_ip")}
            item.update(record_ref=record_ref(row))
            for name in ("device_ip", "source_ip", "dest_ip"):
                item[name] = display_ip(item[name])
            items.append(item)
        limitations = [*LIMITATIONS, *(["legacy_source_host_role_and_event_time_unverified"] if not query.mapping_version else [])]
        return LakeSearchResult(items=items, next_cursor=cursor, has_more=more, time_basis=query.time_basis,
                                selector=query.selector, limitations=limitations)

    async def material(self, tenant, ref):
        scope = self.profile.require_scope(tenant, ref.source_namespace, ref.mapping_version)
        fields = (*SUMMARY_FIELDS, "ocsf_json", "raw_payload")
        sql = base_sql(self.profile, fields) + " AND event_id=%(id)s AND source_version=%(version)s AND event_time=toDateTime64(%(time)s,6,'UTC') AND class_uid=%(class)s LIMIT 2"
        params = {**scope, "id": str(ref.event_id), "version": ref.source_version,
                  "time": ref.event_time.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S.%f"), "class": ref.class_uid}
        rows = await self.rows(sql, params, row_limit=2)
        if not rows:
            fail("lake_material_not_found", "not_found", 404)
        if len(rows) != 1 or set(rows[0]) != set(fields):
            fail("lake_material_ambiguous", status=502)
        row = rows[0]
        if row["tenant_id"] != str(tenant) or LakeRecordRef(**record_ref(row)) != ref:
            fail("lake_material_reference_mismatch", status=502)
        completeness, encoding = "complete", {"invalid_utf8": "base64", "tombstone": "tombstone"}.get(row["parse_status"], "utf8")
        if not ref.mapping_version:
            completeness, encoding = "legacy_unverified", "legacy_unspecified"
            try:
                obj = json.loads(row["ocsf_json"])
                if isinstance(obj, dict) and (obj.get("_socai2_storage", {}).get("truncated") or obj.get("_socai2_storage", {}).get("raw_payload", {}).get("truncated")):
                    completeness = "preview"
            except (ValueError, TypeError, AttributeError):
                pass
        return LakeMaterial(record_ref=ref, parse_status=row["parse_status"], event_time_source=row["event_time_source"],
                            completeness=completeness, raw_payload_encoding=encoding, ocsf_json=row["ocsf_json"], raw_payload=row["raw_payload"])
