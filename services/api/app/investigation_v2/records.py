"""Bounded network source records, separate from the legacy aggregate tools.

The API applies authenticated tenant/global bounds. Investigation Run/question
scope admission belongs to the trusted caller; this module does not invent it.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import json
import re
import time
from typing import Any
from uuid import UUID, uuid4

from app.db.clickhouse import LakeQueryNotConfiguredError, execute_lake_query

NAMESPACE = "clickhouse.aisoc.raw_events"
MAX_ROWS = 50
BODY_PREFIX_BYTES = 8192
TOTAL_BODY_BYTES = 256 * 1024
_ARGUMENTS = frozenset({"hostname", "source_ip", "dest_ip", "dst_port", "protocol", "start", "end", "limit"})
_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_FIELDS = ("event_id", "tenant_id", "event_time", "class_uid", "category_uid", "activity_id",
           "action", "outcome", "src_hostname", "source_ip", "dest_ip", "dst_port", "protocol", "connector_type")
_BODY_FIELDS = tuple(f"{name}_{suffix}" for name in ("raw", "ocsf") for suffix in ("sha256", "bytes", "prefix_base64"))
RESULT_COLUMNS = (*_FIELDS, *_BODY_FIELDS, "duplicate_count")
_PROJECTION = [*_FIELDS]
for _column, _prefix in (("raw_payload", "raw"), ("ocsf_json", "ocsf")):
    _PROJECTION.extend((f"lower(hex(SHA256({_column}))) AS {_prefix}_sha256",
                        f"length({_column}) AS {_prefix}_bytes",
                        f"base64Encode(substring({_column}, 1, {BODY_PREFIX_BYTES})) AS {_prefix}_prefix_base64"))
# Group before LIMIT: repeated physical copies cannot conceal a distinct version
# behind a physical-row cap. Full body hashes participate in the grouping.
SQL = f"""SELECT {', '.join(_PROJECTION)}, count() AS duplicate_count
FROM aisoc.raw_events
WHERE tenant_id = %(tenant_id)s AND class_uid = 4001
  AND src_hostname = %(hostname)s AND source_ip = toIPv6(%(source_ip)s)
  AND dest_ip = toIPv6(%(dest_ip)s) AND dst_port = %(dst_port)s AND protocol = %(protocol)s
  AND event_time >= toDateTime64(%(start)s, 6, 'UTC')
  AND event_time < toDateTime64(%(end)s, 6, 'UTC')
GROUP BY {', '.join((*_FIELDS, *_BODY_FIELDS))}
ORDER BY event_time, event_id, {', '.join(name for name in (*_FIELDS, *_BODY_FIELDS) if name not in {'event_time', 'event_id'})}
LIMIT %(fetch_limit)s"""


@dataclass
class ActivityRecordsResult:
    status: str
    query_receipt: dict[str, Any]
    rows: list[dict[str, Any]] = field(default_factory=list)
    truncated: bool = False
    reason: str | None = None
    tool: str = "activity_records"

    @property
    def available(self) -> bool:
        return self.status in {"ok", "empty"}

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def as_dict(self) -> dict[str, Any]:
        result = {"tool": self.tool, "status": self.status, "available": self.available,
                  "rows": self.rows, "row_count": self.row_count, "truncated": self.truncated,
                  "query_receipt": self.query_receipt}
        if self.reason:
            result["reason"] = self.reason
        return result


def _check(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def _time(value: Any) -> datetime:
    _check(isinstance(value, str) and bool(_TIME.fullmatch(value)), "absolute_timezone_time_required")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _ip(value: Any) -> str:
    address = ipaddress.ip_address(str(value))
    return str(address.ipv4_mapped or address) if isinstance(address, ipaddress.IPv6Address) else str(address)


def _parameters(tenant_id: UUID | str, args: dict[str, Any]) -> dict[str, Any]:
    _check(set(args) == _ARGUMENTS, "required_arguments_or_unknown_fields")
    tenant = str(UUID(str(tenant_id)))
    _check(isinstance(args["hostname"], str) and 0 < len(args["hostname"].encode("utf-8")) <= 255
           and bool(args["hostname"].strip()), "invalid_hostname")
    _check(isinstance(args["source_ip"], str) and isinstance(args["dest_ip"], str), "invalid_ip_type")
    source_ip, dest_ip = _ip(args["source_ip"]), _ip(args["dest_ip"])
    _check(type(args["dst_port"]) is int and 1 <= args["dst_port"] <= 65535, "invalid_port")
    _check(isinstance(args["protocol"], str) and bool(re.fullmatch(r"[A-Za-z0-9_-]{1,32}", args["protocol"])), "invalid_protocol")
    start, end = _time(args["start"]), _time(args["end"])
    _check(start < end and end - start <= timedelta(hours=24), "window_outside_24_hour_bound")
    _check(type(args["limit"]) is int and 1 <= args["limit"] <= MAX_ROWS, "limit_outside_1_to_50")
    return {**args, "tenant_id": tenant, "source_ip": source_ip, "dest_ip": dest_ip, "start": _iso(start), "end": _iso(end)}


def _body(row: dict[str, Any], prefix: str, budget: int) -> dict[str, Any]:
    digest, original = row[f"{prefix}_sha256"], row[f"{prefix}_bytes"]
    _check(isinstance(digest, str) and bool(_HASH.fullmatch(digest)), "invalid_source_hash")
    _check(type(original) is int and original >= 0, "invalid_source_byte_count")
    data = base64.b64decode(row[f"{prefix}_prefix_base64"], validate=True)
    _check(len(data) == min(original, BODY_PREFIX_BYTES), "invalid_database_prefix_length")
    if original <= BODY_PREFIX_BYTES:
        _check(hashlib.sha256(data).hexdigest() == digest, "complete_source_hash_mismatch")
    retained = data[:budget]
    try:
        text = retained.decode("utf-8")
    except UnicodeDecodeError as exc:
        # Only an incomplete final code point may be trimmed; interior invalid
        # UTF-8 is a malformed source response, never silently deleted.
        if exc.reason != "unexpected end of data" or exc.end != len(retained):
            raise
        retained = retained[:exc.start]
        text = retained.decode("utf-8")
    result = {"sha256": digest, "original_bytes": original, "text": text,
              "retained_bytes": len(retained), "truncated": len(retained) < original}
    if result["truncated"]:
        result["truncation_reason"] = "response_body_budget" if budget < BODY_PREFIX_BYTES else "database_body_prefix"
    return result


def _record(row: dict[str, Any], params: dict[str, Any], budget: int) -> dict[str, Any]:
    result = {key: row[key] for key in _FIELDS}
    result.update(namespace=NAMESPACE, tenant_id=str(UUID(str(row["tenant_id"]))), event_id=str(UUID(str(row["event_id"]))),
                  source_ip=_ip(row["source_ip"]), dest_ip=_ip(row["dest_ip"]))
    when = row["event_time"]
    _check(isinstance(when, datetime), "invalid_source_time")
    when = when.replace(tzinfo=timezone.utc) if when.tzinfo is None else when.astimezone(timezone.utc)
    result["event_time"] = _iso(when)
    _check(result["tenant_id"] == params["tenant_id"] and result["class_uid"] == 4001
           and result["src_hostname"] == params["hostname"] and result["source_ip"] == params["source_ip"]
           and result["dest_ip"] == params["dest_ip"] and result["dst_port"] == params["dst_port"]
           and result["protocol"] == params["protocol"] and _time(params["start"]) <= when < _time(params["end"]),
           "returned_record_outside_query_scope")
    _check(all(isinstance(row[key], str) for key in ("action", "outcome", "connector_type")), "invalid_source_text_field")
    result["outcome_provided"] = bool(row["outcome"])
    result["outcome"] = row["outcome"] or "unknown"
    raw = _body(row, "raw", min(BODY_PREFIX_BYTES, budget))
    ocsf = _body(row, "ocsf", min(BODY_PREFIX_BYTES, budget - raw["retained_bytes"]))
    # Fingerprint complete projected content, independent of retained prefixes,
    # duplicate count, result ordering and this response's remaining budget.
    fingerprint = {**result, "raw_payload": {key: raw[key] for key in ("sha256", "original_bytes")},
                   "ocsf_json": {key: ocsf[key] for key in ("sha256", "original_bytes")}}
    result["content_hash"] = hashlib.sha256(json.dumps(fingerprint, sort_keys=True, ensure_ascii=False,
                                                       separators=(",", ":")).encode("utf-8")).hexdigest()
    _check(type(row["duplicate_count"]) is int and row["duplicate_count"] >= 1, "invalid_duplicate_count")
    result.update(raw_payload=raw, ocsf_json=ocsf, duplicate_count=row["duplicate_count"])
    return result


async def activity_records(tenant_id: UUID | str, **args: Any) -> ActivityRecordsResult:
    """Arguments contain filters only; tenant is supplied by authenticated dispatch."""
    started = datetime.now(timezone.utc)
    receipt: dict[str, Any] = {"namespace": NAMESPACE, "started_at": _iso(started),
                               "query_id": None, "executed": False,
                               "scope_authority": "authenticated_tenant_and_api_bounds; Run/question admission is caller-owned"}
    try:
        params = _parameters(tenant_id, args)
    except (ValueError, TypeError, OverflowError):
        receipt.update(status="rejected", finished_at=_iso(datetime.now(timezone.utc)), returned_count=0)
        return ActivityRecordsResult("rejected", receipt, reason="invalid_or_unsupported_arguments")
    query_id = str(uuid4())
    receipt.update(parameters=params, query_id=query_id, executed=True,
                   window_bounds="start_inclusive_end_exclusive", class_uid=4001,
                   limit_basis="distinct_projected_content_versions", per_record_body_bytes=2 * BODY_PREFIX_BYTES,
                   total_body_bytes_limit=TOTAL_BODY_BYTES)
    bindings = {key: value for key, value in params.items() if key != "limit"}
    bindings.update(start=_time(params["start"]).strftime("%Y-%m-%d %H:%M:%S.%f"),
                    end=_time(params["end"]).strftime("%Y-%m-%d %H:%M:%S.%f"), fetch_limit=params["limit"] + 1)
    tick = time.monotonic()
    try:
        response = await execute_lake_query(SQL, params=bindings, query_id=query_id, timeout_seconds=5,
                                            extra_settings={"readonly": 1, "max_execution_time": 5,
                                                            "max_memory_usage": 256 * 1024 * 1024,
                                                            "max_threads": 2, "max_result_rows": MAX_ROWS + 1,
                                                            "result_overflow_mode": "throw"})
    except Exception as exc:
        code = getattr(exc, "code", None) or getattr(exc.__cause__, "code", None)
        unavailable = isinstance(exc, (LakeQueryNotConfiguredError, ConnectionError)) or code in {47, 60}
        status = "unavailable" if unavailable else "error"
        receipt.update(status=status, finished_at=_iso(datetime.now(timezone.utc)), returned_count=0,
                       elapsed_ms=round((time.monotonic() - tick) * 1000), error={"class": type(exc).__name__})
        if type(code) is int:
            receipt["error"]["code"] = code
        return ActivityRecordsResult(status, receipt, reason="source_unavailable" if unavailable else "lake_query_failed")
    try:
        _check(tuple(response.columns) == RESULT_COLUMNS, "unexpected_source_columns")
        _check(len(response.rows) <= params["limit"] + 1, "source_exceeded_fetch_bound")
        projected = [dict(zip(RESULT_COLUMNS, values, strict=True)) for values in response.rows]
        truncated = len(projected) > params["limit"]
        rows, remaining = [], TOTAL_BODY_BYTES
        for row in projected[:params["limit"]]:
            record = _record(row, params, remaining)
            remaining -= record["raw_payload"]["retained_bytes"] + record["ocsf_json"]["retained_bytes"]
            rows.append(record)
        versions: dict[str, set[str]] = {}
        # Include the one observed sentinel version in conflict detection even
        # when its body cannot be delivered under the requested row limit.
        for row in projected:
            record = _record(row, params, 0)
            versions.setdefault(record["event_id"], set()).add(record["content_hash"])
        for record in rows:
            hashes = sorted(versions[record["event_id"]])
            record.update(identity_state="conflict" if len(hashes) > 1 else "single_version_observed",
                          conflict_version_hashes=hashes if len(hashes) > 1 else [])
        status = "ok" if rows else "empty"
        receipt.update(status=status, finished_at=_iso(datetime.now(timezone.utc)),
                       elapsed_ms=getattr(response, "elapsed_ms", round((time.monotonic() - tick) * 1000)),
                       returned_count=len(rows), database_version_rows_returned=len(projected),
                       physical_rows_represented=sum(row["duplicate_count"] for row in rows),
                       database_physical_rows_represented=sum(row["duplicate_count"] for row in projected),
                       distinct_matching_versions=None if truncated else len(projected), rows_truncated=truncated,
                       retained_body_bytes=TOTAL_BODY_BYTES - remaining,
                       body_truncated=any(row[key]["truncated"] for row in rows for key in ("raw_payload", "ocsf_json")),
                       coverage="bounded query only; absence is not proof of no activity; no global identity completeness")
        return ActivityRecordsResult(status, receipt, rows, truncated)
    except (ValueError, TypeError, KeyError, UnicodeError):
        receipt.update(status="error", finished_at=_iso(datetime.now(timezone.utc)), returned_count=0,
                       elapsed_ms=round((time.monotonic() - tick) * 1000))
        return ActivityRecordsResult("error", receipt, reason="invalid_source_response")
