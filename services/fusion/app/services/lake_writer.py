"""Write normalized OCSF events into the ClickHouse event lake (Phase A1).

The reality audit found the central SIEM gap: ingest publishes normalized OCSF
events to Kafka and fusion promotes a subset into Postgres alerts, but
**nothing populated the ClickHouse ``aisoc.raw_events`` lake** — the table and
its read API (``/api/v1/lake/sql``) existed with no writer, so every hunt/query
ran against an empty warehouse.

The historical ``write_event`` path below has those fail-soft buffer semantics.
The explicit ``write_ocsf_batch`` entry added in lake 3c instead saves original
bare records synchronously and returns receipts only after INSERT confirmation.
The explicit lake consumer uses those receipts for partition commits (lake 3d).

This module closes that gap. Fusion already deserializes every ``aisoc.raw_events``
Kafka message (for promotion), so it is the natural place to also archive each
event into the lake. Archival is independent of the promotion decision: a
Medium-severity event that is (correctly) not promoted to an alert must still be
queryable in the lake.

Design constraints (mirroring ``AlertSink``):

* **Fail-soft.** A ClickHouse outage must degrade to "events still flow through
  Kafka/fusion, lake archival is dropped for the outage window" — never crash
  the consumer. A failed flush drops that batch (best-effort archival) rather
  than growing an unbounded in-memory buffer.
* **Batched.** ClickHouse is happiest with bulk inserts, so events are buffered
  and flushed by size (``batch_size``) or age (``batch_max_age_seconds``); the
  consumer calls :meth:`flush_if_stale` each loop and :meth:`flush` on stop.
* **At-least-once with a deterministic ``event_id``.** MergeTree does not
  deduplicate, so a Kafka replay can produce a duplicate lake row. Each row
  carries the ingest event id (when it is a valid UUID) so downstream queries
  can ``argMax``/``LIMIT 1 BY event_id`` if exact-once is required. The Phase A1
  gate asserts *queryability* (``count >= 1``), not exact-once.

``clickhouse-driver`` is synchronous, so every insert is dispatched to a worker
thread via :func:`asyncio.to_thread` to keep the fusion event loop responsive.
If the driver is not installed (some dev images), the writer disables itself at
construction and logs once, rather than failing fusion import.
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

from app.services.event_schema import resolve_source_event_id
from app.services.lake_ingress import (
    NEW_COLUMNS,
    IngressProfile,
    KafkaPosition,
    adapt_ocsf,
    datetime_milliseconds,
)
from app.services.lake_material import bounded_material
from app.services.received_fields import activity_block, received_time, source_labels

logger = structlog.get_logger()

# Column order for the INSERT — must match ``_row`` and the ClickHouse schema in
# ``services/api/clickhouse/001_init.sql``.
_COLUMNS = (
    "event_id",
    "tenant_id",
    "event_time",
    "class_uid",
    "category_uid",
    "severity_id",
    "severity",
    "activity_id",
    "source_ip",
    "dest_ip",
    "src_port",
    "dst_port",
    "protocol",
    "src_hostname",
    "dst_hostname",
    "user_name",
    "process_name",
    "file_path",
    "hash_sha256",
    "connector_type",
    "raw_payload",
    "ocsf_json",
    "mitre_techniques",
    "mitre_tactics",
    "iocs",
    # The activity projection ingest builds on every event (depth plan 2.2).
    # These are columns and not only `ocsf_json` because a hunt that has to
    # JSONExtract out of a ZSTD blob cannot use an index.
    "actor_kind",
    "actor_kind_source",
    "actor_id",
    "actor_on_behalf_of",
    "action",
    "resource_type",
    "resource_id",
    "resource_owner",
    "src_country_code",
    "src_asn",
    "src_as_org",
    "src_reputation",
    "src_reputation_known",
    "client_family",
    "client_version",
    "client_category",
    "client_raw",
    "outcome",
    # Sessions per principal (depth plan 2.4). `session_id` is the same
    # deterministic uuid the Postgres row and the graph node carry, so a hunt
    # can join the three without any of them having coordinated at write time.
    # `session_key_kind` rides along because a query that counts events per
    # session means something different for a vendor session than for a
    # derived one, and a hunter who cannot see which they have will mix them.
    "session_id",
    "session_key",
    "session_key_kind",
    "session_originating_human",
)

_INSERT_SQL = f"INSERT INTO aisoc.raw_events ({', '.join(_COLUMNS)}) VALUES"
_DEFAULT_ID_COLUMNS = tuple(column for column in _COLUMNS if column != "event_id")
_INSERT_DEFAULT_ID_SQL = f"INSERT INTO aisoc.raw_events ({', '.join(_DEFAULT_ID_COLUMNS)}) VALUES"
_INGRESS_COLUMNS = (*_COLUMNS, *NEW_COLUMNS)

# ClickHouse IPv6 columns reject empty/invalid strings; "::" is the safe null.
_NULL_IP = "::"


def _get(obj: Any, *path: str) -> Any:
    cur: Any = obj
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_str(value: Any) -> str:
    return value if isinstance(value, str) else ("" if value is None else str(value))


def _as_dict(value: Any) -> dict[str, Any]:
    """A nested object, or an empty one — never None.

    Sibling of `_as_str` and `_as_int` above, for the same reason: the
    projection reads an envelope a connector shaped, so any level of it can
    be missing or be the wrong type.
    """
    return value if isinstance(value, dict) else {}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_ip(value: Any) -> str:
    """Normalise to a valid IP string; '::' when absent/invalid.

    Kept as a string in the row dict (readable, serialisable); converted to an
    ``ipaddress`` object only at insert time by :func:`_to_ip_obj`.
    """
    if not isinstance(value, str) or not value.strip():
        return _NULL_IP
    candidate = value.strip()
    try:
        ipaddress.ip_address(candidate)
        return candidate
    except ValueError:
        return _NULL_IP


def _to_ip_obj(value: str) -> ipaddress.IPv6Address:
    """Bind an IPv6-typed ClickHouse column.

    The column is ``IPv6``, so an IPv4 address must be mapped to its
    IPv4-mapped IPv6 form (``::ffff:a.b.c.d``); the driver rejects a bare
    ``IPv4Address``. Invalid input -> the null IPv6 ``::``.
    """
    try:
        addr = ipaddress.ip_address(value)
    except ValueError:
        return ipaddress.IPv6Address(_NULL_IP)
    if isinstance(addr, ipaddress.IPv4Address):
        return ipaddress.IPv6Address("::ffff:" + str(addr))
    return addr


def _insert_rows(client, sql, group, *, millisecond_dates=False):
    rows = []
    for row in group:
        out = {k: v for k, v in row.items() if not (k == "event_id" and v is None)}
        out["source_ip"] = _to_ip_obj(row["source_ip"])
        out["dest_ip"] = _to_ip_obj(row["dest_ip"])
        if millisecond_dates:
            out["device_ip"] = _to_ip_obj(row["device_ip"]) if row["device_ip"] is not None else None
            # DateTime64(3) native driver integers are raw millisecond ticks.
            # Avoid datetime.timestamp() float/negative-epoch rounding.
            for column in ("event_time", "kafka_timestamp"):
                if row[column] is not None:
                    out[column] = datetime_milliseconds(row[column])
        rows.append(out)
    kwargs = {"settings": {"async_insert": 0}} if millisecond_dates else {}
    client.execute(sql, rows, types_check=True, **kwargs)


@dataclass(frozen=True)
class LakeWriteReceipt:
    event_id: str
    source_version: str
    parse_status: str
    position: KafkaPosition
    issues: tuple[str, ...]
    persisted: bool = True


class LakePersistenceError(RuntimeError):
    """No success receipt; an attempted INSERT may already have reached the server."""

    def __init__(self, outcome: str, cause_type: str):
        self.outcome = outcome
        self.cause_type = cause_type
        super().__init__(f"lake ingress persistence {outcome}: {cause_type}")


async def _settled_thread(call, *args, **kwargs):
    """Cancellation must not release the connection lock before native I/O ends."""
    task = asyncio.create_task(asyncio.to_thread(call, *args, **kwargs))
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
        except Exception:  # noqa: BLE001 - retrieve the original result below
            break
    if cancelled:
        # Retrieve a possible native error without leaking query/body contents.
        if not task.cancelled():
            task.exception()
        raise asyncio.CancelledError
    return task.result()


def _tenant_uuid(message: dict[str, Any], ocsf: dict[str, Any]) -> str | None:
    raw = message.get("tenant_id") or ocsf.get("tenant_uid")
    try:
        return str(uuid.UUID(str(raw)))
    except (TypeError, ValueError):
        return None


def _event_time(ocsf: dict[str, Any]) -> datetime:
    """Return a naive-UTC ``datetime`` for the ClickHouse DateTime64 column.

    clickhouse-driver maps a Python ``datetime`` (not a string) onto DateTime64;
    a bad/absent timestamp falls back to now().
    """
    raw = ocsf.get("time")
    if isinstance(raw, str) and raw.strip():
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt.astimezone(UTC).replace(tzinfo=None)
        except ValueError:
            pass
    return datetime.now(UTC).replace(tzinfo=None)


def _first_hash(ocsf: dict[str, Any]) -> str:
    def sha256(value):
        return value if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) else ""

    fps = _get(ocsf, "file", "fingerprints")
    if isinstance(fps, list):
        for fp in fps:
            if isinstance(fp, dict) and str(fp.get("algorithm", "")).upper().replace("-", "") == "SHA256":
                value = sha256(fp.get("value"))
                if value:
                    return value
    return sha256(ocsf.get("hash_sha256"))


def _mitre(ocsf: dict[str, Any]) -> tuple[list[str], list[str]]:
    techniques: list[str] = []
    tactics: list[str] = []
    block = ocsf.get("mitre_attck")
    if isinstance(block, list):
        for entry in block:
            if not isinstance(entry, dict):
                continue
            tid = entry.get("technique_id")
            if isinstance(tid, str) and tid and tid not in techniques:
                techniques.append(tid)
            for name in entry.get("tactic_names") or []:
                if isinstance(name, str) and name and name not in tactics:
                    tactics.append(name)
    return techniques, tactics


def _iocs(ocsf: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for value in (
        _get(ocsf, "src_endpoint", "ip"),
        _get(ocsf, "dst_endpoint", "ip"),
        _first_hash(ocsf),
    ):
        if isinstance(value, str) and value.strip():
            out.append(value.strip())
    fingerprints = _get(ocsf, "file", "fingerprints")
    for fingerprint in fingerprints if isinstance(fingerprints, list) else []:
        value = fingerprint.get("value") if isinstance(fingerprint, dict) else None
        if isinstance(value, str) and value.strip() and value.strip() not in out:
            out.append(value.strip())
    return out


def _activity_columns(ocsf: dict[str, Any]) -> dict[str, Any]:
    """Flatten the activity projection ingest put on the event.

    Every value is defaulted rather than left absent: ClickHouse's column
    order is positional at insert time, so a row missing one key would shift
    every column after it. An event from before depth plan 2.2, or from a
    replayed topic, has no ``activity`` block at all and must still insert.

    ``src_reputation_known`` is carried separately from the score because a
    clean verdict and an unreachable enrichment service both produce 0.0, and
    collapsing them would let a broken enrichment path read as a quiet estate.
    """
    act = _as_dict(ocsf.get("activity"))
    actor = _as_dict(act.get("actor"))
    resource = _as_dict(act.get("resource"))
    location = _as_dict(act.get("location"))
    client = _as_dict(location.get("client"))

    return {
        "actor_kind": _as_str(actor.get("kind")),
        "actor_kind_source": _as_str(actor.get("kind_source")),
        "actor_id": _as_str(actor.get("id")),
        "actor_on_behalf_of": _as_str(actor.get("on_behalf_of")),
        "action": _as_str(act.get("action")),
        "resource_type": _as_str(resource.get("type")),
        "resource_id": _as_str(resource.get("id") or resource.get("name")),
        "resource_owner": _as_str(resource.get("owner")),
        "src_country_code": _as_str(location.get("country_code")),
        "src_asn": _as_int(location.get("asn")),
        "src_as_org": _as_str(location.get("as_org")),
        "src_reputation": _as_float(location.get("reputation")),
        "src_reputation_known": 1 if location.get("reputation_known") else 0,
        "client_family": _as_str(client.get("family")),
        "client_version": _as_str(client.get("version")),
        "client_category": _as_str(client.get("category")),
        "client_raw": _as_str(client.get("raw"))[:1024],
        "outcome": _as_str(act.get("outcome")),
        **_session_columns(act),
    }


def _session_columns(act: dict[str, Any]) -> dict[str, Any]:
    """Flatten the session block, defaulting every key for the same reason.

    `session_id` is stamped onto the event by the fusion consumer after the
    Postgres upsert and before this writer runs. An event that reached the
    lake without going through that step — a replay, or a deployment with the
    alert sink off — carries the vendor key and kind but an empty id, which is
    the honest record: the grouping is known, the row it joins to is not.
    """
    session = _as_dict(act.get("session"))
    return {
        "session_id": _as_str(session.get("id")),
        "session_key": _as_str(session.get("key"))[:512],
        "session_key_kind": _as_str(session.get("key_kind")),
        "session_originating_human": _as_str(session.get("originating_human")),
    }


def event_to_row(message: dict[str, Any]) -> dict[str, Any] | None:
    """Map an ingest NormalizedEvent envelope to a ClickHouse row dict.

    Returns ``None`` when the message has no OCSF body or no UUID tenant — such
    messages are handled (dead-lettered) elsewhere and must not reach the lake.
    """
    ocsf = message.get("ocsf_event")
    if not isinstance(ocsf, dict):
        return None
    tenant = _tenant_uuid(message, ocsf)
    if tenant is None:
        return None

    tactics, techniques = source_labels(ocsf)
    connector_type = _as_str(_get(ocsf, "metadata", "product", "name")) or _as_str(message.get("connector_type"))
    activity, activity_source = activity_block(message)
    event_time, time_source = received_time(message, ocsf)
    raw_payload, raw_metadata = bounded_material(ocsf.get("raw_data"), 65536)
    # Original OCSF fields stay at their established JSON paths when complete.
    # Envelope activity is retained separately so its origin is explicit.
    material = {**ocsf, "_socai2_storage": {"raw_payload": raw_metadata,
                "event_time_source": time_source, "event_time_fallback": event_time is None,
                "activity_source": activity_source,
                **({"envelope_activity": message["activity"]} if activity_source.startswith("activity") else {})}}
    ocsf_json, _ = bounded_material(material, 262144, structured=True)

    row: dict[str, Any] = {
        "tenant_id": tenant,
        "event_time": (event_time or datetime.now(UTC)).replace(tzinfo=None),
        "class_uid": _as_int(ocsf.get("class_uid")),
        "category_uid": _as_int(ocsf.get("category_uid")),
        "severity_id": _as_int(ocsf.get("severity_id")),
        "severity": _as_str(ocsf.get("severity")),
        "activity_id": _as_int(ocsf.get("activity_id")),
        "source_ip": _as_ip(_get(ocsf, "src_endpoint", "ip")),
        "dest_ip": _as_ip(_get(ocsf, "dst_endpoint", "ip")),
        "src_port": _as_int(_get(ocsf, "src_endpoint", "port")),
        "dst_port": _as_int(_get(ocsf, "dst_endpoint", "port")),
        "protocol": _as_str(ocsf.get("protocol") or _get(ocsf, "connection_info", "protocol_name")),
        "src_hostname": _as_str(_get(ocsf, "device", "name") or _get(ocsf, "src_endpoint", "hostname")),
        "dst_hostname": _as_str(_get(ocsf, "dst_endpoint", "hostname")),
        "user_name": _as_str(_get(ocsf, "actor", "user", "name")),
        "process_name": _as_str(_get(ocsf, "process", "name")),
        "file_path": _as_str(_get(ocsf, "file", "path")),
        "hash_sha256": _first_hash(ocsf),
        "connector_type": connector_type,
        "raw_payload": raw_payload,
        "ocsf_json": ocsf_json,
        "mitre_techniques": techniques,
        "mitre_tactics": tactics,
        "iocs": _iocs(ocsf),
        **_activity_columns({"activity": activity}),
    }

    # Only set a deterministic event_id when the ingest id is a real UUID;
    # otherwise let ClickHouse default generateUUIDv4().
    raw_id = resolve_source_event_id(message, ocsf)
    try:
        row["event_id"] = str(uuid.UUID(str(raw_id)))
    except (TypeError, ValueError):
        row["event_id"] = None
    return row


class LakeWriter:
    """Batched, fail-soft ClickHouse writer for the ``aisoc.raw_events`` lake."""

    def __init__(
        self,
        *,
        host: str,
        port: int = 9000,
        database: str = "aisoc",
        user: str = "default",
        password: str = "",
        batch_size: int = 100,
        batch_max_age_seconds: float = 2.0,
        ingress_profile: IngressProfile | None = None,
        connect_timeout_seconds: float = 10.0,
        send_receive_timeout_seconds: float = 300.0,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", database):
            raise ValueError("invalid_clickhouse_database")
        self._host = host
        self._port = port
        self._database = database
        if ingress_profile is not None and ingress_profile.database != database:
            raise ValueError("ingress profile/database mismatch")
        self._ingress_profile = ingress_profile
        self._connect_timeout = connect_timeout_seconds
        self._send_receive_timeout = send_receive_timeout_seconds
        if min(connect_timeout_seconds, send_receive_timeout_seconds) <= 0:
            raise ValueError("ClickHouse timeouts must be positive")
        self._ingress_insert_sql = f"INSERT INTO {database}.raw_events ({', '.join(_INGRESS_COLUMNS)}) VALUES"
        self._insert_lock = asyncio.Lock()
        self._insert_sql = _INSERT_SQL.replace("aisoc.raw_events", f"{database}.raw_events")
        self._insert_default_id_sql = _INSERT_DEFAULT_ID_SQL.replace("aisoc.raw_events", f"{database}.raw_events")
        self._user = user
        self._password = password
        self._batch_size = max(1, batch_size)
        self._batch_max_age = batch_max_age_seconds
        self._client: Any | None = None
        self._buffer: list[dict[str, Any]] = []
        self._buffer_started_at: float = 0.0
        self._disabled = False
        self.rows_written = 0
        # Rows discarded from the local buffer without a confirmed insert.
        # An INSERT error does not prove the server stored none of those rows.
        self.rows_dropped = 0
        self.flush_failures = 0

    async def start(self) -> None:
        if self._disabled:
            return
        try:
            from clickhouse_driver import Client  # noqa: PLC0415

            self._client = Client(
                host=self._host,
                port=self._port,
                database=self._database,
                user=self._user,
                password=self._password or "",
                connect_timeout=self._connect_timeout,
                send_receive_timeout=self._send_receive_timeout,
            )
            logger.info("lake_writer.started", host=self._host, database=self._database)
        except ImportError:
            self._disabled = True
            logger.warning("lake_writer.disabled_no_driver")
        except Exception as exc:  # noqa: BLE001 — degrade, never crash the worker
            self._disabled = True
            logger.error("lake_writer.connect_failed", error=str(exc))

    async def stop(self) -> None:
        await self.flush()
        if self._client is not None:
            try:
                async with self._insert_lock:
                    await _settled_thread(self._client.disconnect)
            except Exception as exc:  # noqa: BLE001
                logger.warning("lake_writer.disconnect_failed", error=str(exc))
            self._client = None

    async def write_ocsf_batch(self, records: list[tuple[bytes | None, KafkaPosition]]) -> tuple[LakeWriteReceipt, ...]:
        """Persist explicit bare records without the legacy buffer or preview.

        This is an internal save boundary. Kafka scheduling and offset commits
        are not performed here. Errors/unknown outcomes are not auto-retried.
        """
        if self._ingress_profile is None:
            raise ValueError("bare OCSF ingress profile is not configured")
        adapted = [adapt_ocsf(body, profile=self._ingress_profile, position=position) for body, position in records]
        if not adapted:
            return ()
        async with self._insert_lock:
            if self._disabled or self._client is None:
                raise LakePersistenceError("not_attempted", "client_unavailable")
            try:
                await _settled_thread(_insert_rows, self._client, self._ingress_insert_sql,
                                        [record.row for record in adapted], millisecond_dates=True)
            except Exception as exc:  # noqa: BLE001 - no original/query text in the public error
                self.flush_failures += 1
                raise LakePersistenceError("unknown", type(exc).__name__) from None
        self.rows_written += len(adapted)
        return tuple(LakeWriteReceipt(record.row["event_id"], record.row["source_version"], record.row["parse_status"], position, record.issues)
                     for record, (_, position) in zip(adapted, records, strict=True))

    @property
    def ingress_profile(self) -> IngressProfile | None:
        return self._ingress_profile

    async def check_ingress_ready(self) -> None:
        """Read-only startup gate; actual schema/cleanup rollout remains a release prerequisite."""
        if self._ingress_profile is None:
            raise ValueError("bare OCSF ingress profile is not configured")
        async with self._insert_lock:
            if self._disabled or self._client is None:
                raise LakePersistenceError("not_attempted", "client_unavailable")
            try:
                rows = await _settled_thread(self._client.execute,
                    f"SELECT migration_id FROM {self._database}._migrations WHERE migration_id = %(id)s",
                    {"id": "005_lake_ingress_v1"})
                if not rows:
                    raise ValueError("migration_missing")
                # Resolves the real named columns without reading business rows.
                await _settled_thread(self._client.execute,
                    f"SELECT {', '.join(_INGRESS_COLUMNS)}, ingest_time FROM {self._database}.raw_events LIMIT 0")
            except Exception as exc:  # noqa: BLE001 - safe structural startup error
                raise LakePersistenceError("not_attempted", type(exc).__name__) from None

    async def inspect_ocsf_batch(self, records: list[tuple[bytes | None, KafkaPosition]]) -> tuple[str, ...]:
        """Diagnostic readback only. Neither a retry nor permission to commit.

        Look for stable identity AND both complete stored materials. A missing
        row is 'not_observed', not proof that a server-side INSERT cannot finish.
        """
        import hashlib

        if self._ingress_profile is None:
            raise ValueError("bare OCSF ingress profile is not configured")
        rows = [adapt_ocsf(body, profile=self._ingress_profile, position=pos).row for body, pos in records]
        if not rows:
            return ()
        async with self._insert_lock:
            if self._disabled or self._client is None:
                return tuple("unknown" for _ in rows)
            try:
                found = await _settled_thread(self._client.execute,
                    f"SELECT event_id, source_version, hex(SHA256(ocsf_json)), hex(SHA256(raw_payload)) "
                    f"FROM {self._database}.raw_events WHERE tenant_id = %(tenant)s "
                    "AND source_namespace = %(source)s AND mapping_version = %(mapping)s AND event_id IN %(ids)s",
                    {"tenant": self._ingress_profile.tenant_id, "source": self._ingress_profile.source_namespace,
                     "mapping": self._ingress_profile.mapping_version, "ids": tuple(row["event_id"] for row in rows)})
            except Exception:  # noqa: BLE001 - query failure is an unknown observation
                return tuple("unknown" for _ in rows)
        saved = {(str(event_id), version, ocsf_hash, raw_hash) for event_id, version, ocsf_hash, raw_hash in found}
        return tuple("present" if (row["event_id"], row["source_version"],
                     hashlib.sha256(row["ocsf_json"].encode()).hexdigest().upper(),
                     hashlib.sha256(row["raw_payload"].encode()).hexdigest().upper()) in saved else "not_observed"
                     for row in rows)

    async def write_event(self, message: dict[str, Any]) -> bool:
        """Return True if accepted into the buffer or a triggered insert succeeded.

        True for a pending buffer is not a persistence receipt; use rows_written.
        A triggered flush failure returns False. No retry is performed here.
        """
        if self._disabled or self._client is None:
            return False
        row = event_to_row(message)
        if row is None:
            return False
        if not self._buffer:
            self._buffer_started_at = time.monotonic()
        self._buffer.append(row)
        if len(self._buffer) >= self._batch_size:
            return await self.flush()
        return True

    async def flush_if_stale(self) -> None:
        if self._buffer and (time.monotonic() - self._buffer_started_at) >= self._batch_max_age:
            await self.flush()

    async def flush(self) -> bool:
        if not self._buffer:
            return True
        if self._disabled:
            return False
        batch = self._buffer
        self._buffer = []
        client = self._client
        if client is None:
            self.rows_dropped += len(batch)
            self.flush_failures += 1
            return False

        succeeded = True
        groups = (
            (self._insert_sql, [row for row in batch if row["event_id"] is not None]),
            (self._insert_default_id_sql, [row for row in batch if row["event_id"] is None]),
        )
        for sql, group in groups:
            if not group:
                continue
            try:
                async with self._insert_lock:
                    await _settled_thread(_insert_rows, client, sql, group)
                self.rows_written += len(group)
            except Exception as exc:  # noqa: BLE001 — retain the existing fail-soft policy
                succeeded = False
                self.rows_dropped += len(group)
                logger.error("lake_writer.flush_failed", error=str(exc), dropped=len(group))
        if not succeeded:
            self.flush_failures += 1
        return succeeded

    def metrics(self) -> dict[str, int]:
        return {
            "rows_written": self.rows_written,
            "rows_dropped": self.rows_dropped,
            "flush_failures": self.flush_failures,
            "buffered": len(self._buffer),
        }
